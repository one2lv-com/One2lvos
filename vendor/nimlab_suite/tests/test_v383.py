"""v3.8.3: MCP tools on every channel, quill_task jobs (prompt + picked
tools, Free time template), model fallbacks (429 / 503 incl. NVIDIA's
"content safety screening" body), failed steps in traces and bug records,
and a paced setup sweep. Offline: every network call goes to a fake."""

import json
import os
import tempfile
import unittest
from unittest import mock

from nimlab import config, environment as ENV, fallback as FB, scheduler as SC, selfadmin as SA
from nimlab.api import ModelResult
from nimlab.core import HttpClient, RateLimiter, sweep_rpm
from nimlab.mcp import MCPClient
from tests.fakes import FakeMCPServer, FakeResponse, RouteOpener, chat_body, http_error
from tests.test_roles import make_entity

SAFETY_503 = "content safety screening is temporarily unavailable"
TOOLS = [{"name": "beat_lab", "description": "make a beat", "inputSchema": {"type": "object"}},
         {"name": "generate_creative_art", "description": "draw", "inputSchema": {"type": "object"}},
         {"name": "terminal", "description": "run a shell", "inputSchema": {"type": "object"}}]
CALL = '<tool_call>{"name": "%s", "arguments": {}}</tool_call>'


def tmp(test):
    d = tempfile.TemporaryDirectory()
    test.addCleanup(d.cleanup)
    return d.name


class ScriptedModel:
    """chat/completions answers: a list of str (reply), int (HTTP error
    status, body SAFETY_503 for 503) or callables(body)->str. Records the
    model and messages of every request."""

    def __init__(self, script, by_model=None):
        self.script = list(script)
        self.by_model = by_model or {}
        self.calls = []

    def __call__(self, req):
        body = json.loads(req.data.decode())
        self.calls.append(body)
        model = body.get("model")
        if model in self.by_model:
            item = self.by_model[model]
            item = item.pop(0) if isinstance(item, list) else item
        else:
            item = self.script.pop(0) if self.script else "done"
        if callable(item):
            item = item(body)
        if isinstance(item, int):
            msg = SAFETY_503 if item == 503 else f"error {item}"
            return http_error(item, json.dumps({"error": {"message": msg}}).encode())
        return FakeResponse(chat_body(item))


def live_mcp(ent, server):
    """Give an Entity a never-loaded MCP client on a fake server (as a fresh
    process would have)."""
    ent.cluster["mcp_settings"] = dict(ent.cluster.get("mcp_settings") or {}, enabled=True,
                                       url="https://mcp.test/mcp")
    ent.mcp = MCPClient(ent.mcp_settings, http=HttpClient(opener=server, retries=0), env={})
    ent._tools_at = ent._tools_err_at = None
    ent._tools_stale = False
    ent.tools_error = None
    return ent


def entity(test, script=None, roles=None, by_model=None, extra=None):
    model = ScriptedModel(script or [], by_model)
    ent, _ = make_entity(test, roles or {"persona": "p/persona"},
                         opener=RouteOpener([("chat/completions", model)]), extra=extra)
    ent.client.http._sleep = lambda s: None
    return ent, model


class DataDir(unittest.TestCase):
    def setUp(self):
        self.data = tmp(self)
        p = mock.patch.dict(os.environ, {"NIMLAB_DATA_DIR": self.data, "NIMLAB_COLOR": "0"})
        p.start()
        self.addCleanup(p.stop)
        FB.reset()
        self.addCleanup(FB.reset)


# ---------------------------------------------------------------------------
# 1. MCP tools load on first use, on every channel
# ---------------------------------------------------------------------------
class TestToolsOnEveryChannel(DataDir):
    def first_turn(self, channel, admin=True):
        srv = FakeMCPServer(TOOLS)
        ent, model = entity(self, [CALL % "beat_lab", "I made a beat."])
        live_mcp(ent, srv)
        self.assertEqual(ent.mcp.tools, [])          # nothing loaded yet: a fresh process
        with SA.identity(admin=admin, who="t", source=channel), ENV.channel(channel):
            out = ent.turn("play with a tool", [])
        self.assertTrue(out["result"].ok, out)
        self.assertIn(("beat_lab", {}), srv.calls, channel)
        self.assertEqual(out["result"].text, "I made a beat.")
        self.assertTrue(any(t.get("name") == "beat_lab" for t in out["trace"]))
        return ent, srv

    def test_terminal(self):
        self.first_turn("terminal")

    def test_telegram_owner(self):
        self.first_turn("telegram")

    def test_telegram_non_owner_without_coding_role(self):
        self.first_turn("telegram", admin=False)

    def test_voice(self):
        self.first_turn("voice")

    def test_server(self):
        self.first_turn("api")

    def test_scheduler_quill_prompt(self):
        srv = FakeMCPServer(TOOLS)
        ent, _ = entity(self, [CALL % "beat_lab", "Beat made."])
        live_mcp(ent, srv)
        ctx = SC.LiveContext()
        ctx._ent = ent
        ok, text = ctx.quill("FREE TIME: pick a tool")
        self.assertTrue(ok, text)
        self.assertEqual(text, "Beat made.")
        self.assertIn(("beat_lab", {}), srv.calls)

    def test_heartbeat(self):
        from nimlab import heartbeat as HB
        srv = FakeMCPServer(TOOLS)
        ent, _ = entity(self, [CALL % "beat_lab", "Checked in."])
        live_mcp(ent, srv)
        ctx = SC.LiveContext()
        ctx._ent = ent
        # the heartbeat's own turns go through ctx.quill, as the scheduler's do
        ok, _ = ctx.quill("heartbeat: review suggested actions", who="heartbeat")
        self.assertTrue(ok)
        self.assertIn(("beat_lab", {}), srv.calls)
        self.assertTrue(hasattr(HB, "run") or hasattr(HB, "Heartbeat"))

    def test_server_path_unified(self):
        from nimlab import unified
        srv = FakeMCPServer(TOOLS)
        ent, _ = entity(self, [CALL % "beat_lab", "Done via server."])
        live_mcp(ent, srv)
        with SA.identity(admin=True, who="owner", source="telegram"), ENV.channel("telegram"):
            res = unified.Mind(ent).run("play")
        self.assertEqual(res.get("text"), "Done via server.", res)
        self.assertIn(("beat_lab", {}), srv.calls)
        self.assertTrue(any(t.get("role") == "mcp_tool" and t.get("target") == "beat_lab" and t.get("ok")
                            for t in res["trace"]))

    def test_cached_then_refreshed_after_ttl_and_error(self):
        srv = FakeMCPServer(TOOLS)
        ent, _ = entity(self)
        live_mcp(ent, srv)
        ent.ensure_tools()
        ent.ensure_tools()
        n_lists = srv.requests.count("https://mcp.test/mcp")
        ent.ensure_tools()
        self.assertEqual(srv.requests.count("https://mcp.test/mcp"), n_lists)    # cached
        ent.mark_tools_stale()
        ent.ensure_tools()
        self.assertGreater(srv.requests.count("https://mcp.test/mcp"), n_lists)  # refreshed after an error
        ent._tools_at -= 10_000
        before = len(srv.requests)
        ent.ensure_tools()
        self.assertGreater(len(srv.requests), before)                           # refreshed after the TTL

    def test_down_server_keeps_error_for_doctor_and_does_not_retry_every_turn(self):
        srv = FakeMCPServer(TOOLS, down=True)
        ent, _ = entity(self)
        live_mcp(ent, srv)
        self.assertEqual(ent.ensure_tools(), [])
        self.assertIn("refused", ent.tools_error or "")
        n = len(srv.requests)
        ent.ensure_tools()
        self.assertEqual(len(srv.requests), n)
        st = ent.tools_status()
        self.assertEqual((st["enabled"], st["count"]), (True, 0))
        self.assertTrue(st["error"])

    def test_concurrent_first_use_lists_once(self):
        import threading
        srv = FakeMCPServer(TOOLS)
        ent, _ = entity(self)
        live_mcp(ent, srv)
        ts = [threading.Thread(target=ent.ensure_tools) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(len(ent.mcp.tools), 3)
        self.assertLessEqual(srv.requests.count("https://mcp.test/mcp"), 3)   # init + initialized + list, once

    def test_coding_role_non_admin_gets_no_persona_tools_but_scheduler_does(self):
        srv = FakeMCPServer(TOOLS)
        ent, _ = entity(self, roles={"persona": "p/persona", "coding": "c/coder"})
        live_mcp(ent, srv)
        with SA.identity(admin=False, who="guest", source="telegram"), ENV.channel("telegram"):
            self.assertFalse(ent.persona_tools())
        with SA.identity(admin=True, who="scheduler:x", source="scheduler"), ENV.channel("scheduler"):
            self.assertTrue(ent.persona_tools())
        with SA.identity(admin=False, who="guest", source="telegram"), ENV.channel("telegram"), \
                SA.task_tools(["beat_lab"]):
            self.assertTrue(ent.persona_tools())


# ---------------------------------------------------------------------------
# 2. quill_task: a prompt with picked MCP tools
# ---------------------------------------------------------------------------
class TestQuillTask(DataDir):
    def ctx(self, script, tools=TOOLS):
        srv = FakeMCPServer(tools)
        ent, model = entity(self, script)
        live_mcp(ent, srv)
        c = SC.LiveContext()
        c._ent = ent
        return c, srv, model

    def test_check_task_forms(self):
        a = SC.check_task({"prompt": "play", "tools": "beat_lab, generate_creative_art"})
        self.assertEqual(a, {"prompt": "play", "tools": ["beat_lab", "generate_creative_art"], "only": True,
                             "require_tool": False})
        self.assertEqual(SC.check_task(json.dumps({"prompt": "p", "only": False}))["tools"], [])
        with self.assertRaises(SC.JobError):
            SC.check_task({"prompt": "p"})                  # only these tools, but none picked
        with self.assertRaises(SC.JobError):
            SC.check_task({"tools": ["a"]})
        with self.assertRaises(SC.JobError):
            SC.check_task({"prompt": "p", "tools": ["bad name;rm"]})
        self.assertIn("quill_task", SC.USER_ACTION_TYPES)

    def test_only_the_picked_tools_are_offered_and_callable(self):
        c, srv, model = self.ctx([CALL % "terminal", CALL % "beat_lab", "Made a beat."])
        r = SC.run_task({"prompt": "play", "tools": ["beat_lab"], "only": True, "require_tool": False}, c)
        self.assertTrue(r.ok, r.output)
        self.assertNotIn("terminal", [n for n, _ in srv.calls])     # refused: not one of the job's tools
        self.assertIn(("beat_lab", {}), srv.calls)
        system = model.calls[0]["messages"][0]["content"]
        self.assertIn("beat_lab", system)
        self.assertNotIn("generate_creative_art", system)
        self.assertNotIn("run a shell", system)
        self.assertIn("Tools called:", r.output)
        self.assertIn("- beat_lab: ok", r.output)
        self.assertIn("- terminal: ", r.output)
        names = [x["name"] for x in r.data["tools_called"]]
        self.assertEqual(names, ["terminal", "beat_lab"])

    def test_any_tool_mode_allows_others(self):
        c, srv, _ = self.ctx([CALL % "terminal", "Ran it."])
        r = SC.run_task({"prompt": "do", "tools": ["beat_lab"], "only": False, "require_tool": False}, c)
        self.assertTrue(r.ok, r.output)
        self.assertIn(("terminal", {}), srv.calls)

    def test_must_call_a_tool_fails_when_none_called(self):
        c, _, _ = self.ctx(["I just thought about it."])
        r = SC.run_task({"prompt": "play", "tools": ["beat_lab"], "only": True, "require_tool": True}, c)
        self.assertFalse(r.ok)
        self.assertIn("requires at least one tool call", r.output)

    def test_must_call_a_tool_passes_when_called(self):
        c, _, _ = self.ctx([CALL % "beat_lab", "Beat."])
        r = SC.run_task({"prompt": "play", "tools": ["beat_lab"], "only": True, "require_tool": True}, c)
        self.assertTrue(r.ok, r.output)

    def test_missing_tools_are_reported_and_all_missing_fails(self):
        c, _, _ = self.ctx([CALL % "beat_lab", "ok"])
        r = SC.run_task({"prompt": "p", "tools": ["beat_lab", "gone_tool"], "only": True,
                         "require_tool": False}, c)
        self.assertTrue(r.ok)
        self.assertIn("gone_tool", r.output)
        c2, _, _ = self.ctx(["x"])
        r2 = SC.run_task({"prompt": "p", "tools": ["gone_tool"], "only": True, "require_tool": False}, c2)
        self.assertFalse(r2.ok)
        self.assertIn("MCP admin console", r2.output)

    def test_failing_tool_is_reported(self):
        srv = FakeMCPServer(TOOLS, handlers={"beat_lab": lambda a: {"isError": True,
                                                                     "content": [{"type": "text",
                                                                                  "text": "no drums"}]}})
        ent, _ = entity(self, [CALL % "beat_lab", "It broke."])
        live_mcp(ent, srv)
        c = SC.LiveContext()
        c._ent = ent
        r = SC.run_task({"prompt": "p", "tools": ["beat_lab"], "only": True, "require_tool": True}, c)
        self.assertIn("- beat_lab: the tool returned an error", r.output)

    def test_free_time_template_is_a_valid_hourly_job(self):
        spec = SC.free_time_template(["beat_lab", "generate_creative_art"])
        j = SC.create_job(spec, who="cli", source="cli")
        self.assertEqual(j["action_type"], "quill_task")
        self.assertEqual(j["action"]["tools"], ["beat_lab", "generate_creative_art"])
        self.assertTrue(j["action"]["require_tool"])
        self.assertIn("HOURLY", j["schedule"])
        self.assertEqual(j["result_to"]["dest"], "telegram")

    def test_scheduler_runs_a_quill_task_job_end_to_end(self):
        c, srv, _ = self.ctx([CALL % "generate_creative_art", "Drew a fox."])
        SC.create_job(SC.free_time_template(["generate_creative_art"], result_to="log"), who="cli", source="cli")
        s = SC.Scheduler(ctx=c, log=lambda *a: None)
        rec = s.run_now("free-time")
        self.assertEqual(rec["status"], "SUCCEEDED", rec)
        self.assertIn("Drew a fox.", rec["output"])
        self.assertIn("generate_creative_art: ok", rec["output"])
        self.assertIn(("generate_creative_art", {}), srv.calls)

    def test_cli_create_with_tools(self):
        from nimlab import cli, jobscli
        out = []
        with mock.patch.object(jobscli, "_out", out.append):
            rc = cli.main(["jobs", "create", "fun", "--schedule", "FREQ=HOURLY;INTERVAL=1", "--do", "play a game",
                           "--tools", "beat_lab,generate_creative_art", "--require-tool"])
        self.assertEqual(rc, 0, out)
        j = SC.get_job("fun")
        self.assertEqual(j["action_type"], "quill_task")
        self.assertEqual(j["action"], {"prompt": "play a game", "tools": ["beat_lab", "generate_creative_art"],
                                       "only": True, "require_tool": True})

    def test_menu_picker_pages_and_multiselects(self):
        from nimlab import jobscli
        many = [{"name": f"tool_{i:02d}", "description": "d"} for i in range(1, 24)]
        answers = iter(["1,3", "n", "12", "/tool_2", "1", "d"])
        out = []
        picked = jobscli.pick_tools(lambda p: next(answers), out.append, many)
        self.assertEqual(picked, ["tool_01", "tool_03", "tool_12", "tool_20"])
        self.assertTrue(any("page 1/3" in x for x in out))
        self.assertTrue(any("page 2/3" in x for x in out))

    def test_menu_free_time_from_live_tools(self):
        from nimlab import jobscli
        answers = iter(["", "1,2", "d", ""])
        out = []
        with mock.patch.object(SC, "live_mcp_tools", return_value=TOOLS):
            j = jobscli._new_task(lambda p: next(answers), out.append, template=True)
        self.assertEqual(j["name"], "free-time")
        self.assertEqual(j["action"]["tools"], ["beat_lab", "generate_creative_art"])
        self.assertEqual(j["result_to"]["dest"], "telegram")

    def test_selfadmin_job_create_accepts_quill_task(self):
        j = SC.create_job({"name": "sa-task", "schedule": "FREQ=DAILY;BYHOUR=7", "action_type": "quill_task",
                           "action": {"prompt": "draw", "tools": ["generate_creative_art"]}},
                          who="quill", source="selfadmin")
        self.assertEqual(j["action"]["tools"], ["generate_creative_art"])


class TestTelegramJobs(DataDir):
    class Conn:
        def __init__(self, owner=True):
            self.owner, self.sent = owner, []

        def is_owner(self, uid):
            return self.owner

        def send(self, chat_id, text, markup=None):
            self.sent.append(text)

        def log(self, *a):
            pass

    def test_freetime_and_tools_and_listing(self):
        from nimlab import tgcmds
        c = self.Conn()
        with mock.patch.object(SC, "live_mcp_tools", return_value=TOOLS):
            tgcmds.handle(c, 1, 1, "/jobs", "/jobs tools")
            self.assertIn("1) beat_lab", c.sent[-1])
            tgcmds.handle(c, 1, 1, "/jobs", "/jobs freetime beat_lab,generate_creative_art")
            self.assertIn("Created free-time", c.sent[-1])
            tgcmds.handle(c, 1, 1, "/jobs", "/jobs freetime nope")
            self.assertIn("Not on the MCP server now: nope", c.sent[-1])
        j = SC.get_job("free-time")
        self.assertEqual(j["action"]["tools"], ["beat_lab", "generate_creative_art"])
        tgcmds.handle(c, 1, 1, "/jobs", "/jobs")
        self.assertIn("tools: beat_lab, generate_creative_art", c.sent[-1])

    def test_non_owner_cannot_create(self):
        from nimlab import tgcmds
        c = self.Conn(owner=False)
        tgcmds.handle(c, 1, 2, "/jobs", "/jobs freetime beat_lab")
        self.assertIn("owner", c.sent[-1])


# ---------------------------------------------------------------------------
# 3a. fallbacks
# ---------------------------------------------------------------------------
ROLES_FB = {"persona": {"backend": "model", "model": "p/persona", "fallbacks": ["s/second", "s/third"]},
            "reasoning": "r/reasoner"}


class TestFallbacks(DataDir):
    def test_trigger_statuses(self):
        for st in (429, 500, 502, 503, 504):
            self.assertTrue(FB.should_fall_back(ModelResult(False, error="x", status=st)), st)
        self.assertTrue(FB.should_fall_back(ModelResult(False, error=f"HTTP 503: {SAFETY_503}", status=503)))
        self.assertTrue(FB.should_fall_back(ModelResult(False, error="timed out", status=None)))
        for st in (400, 401, 403, 404, 422):
            self.assertFalse(FB.should_fall_back(ModelResult(False, error="x", status=st)), st)
        self.assertFalse(FB.should_fall_back(ModelResult(True, text="ok")))

    def test_safety_503_falls_back_to_reasoning_with_persona_prompt(self):
        ent, model = entity(self, roles=ROLES_FB, by_model={"p/persona": 503, "r/reasoner": "Hi from reasoning."})
        out = ent.turn("hello", [])
        r = out["result"]
        self.assertTrue(r.ok, r.error)
        self.assertEqual(r.text, "Hi from reasoning.")
        self.assertEqual(r.fallback["model"], "r/reasoner")
        fb_call = [c for c in model.calls if c["model"] == "r/reasoner"][0]
        p_call = [c for c in model.calls if c["model"] == "p/persona"][0]
        self.assertEqual(fb_call["messages"][0], p_call["messages"][0])     # same persona prompt + soul
        self.assertEqual(r.tried[0]["status"], 503)
        self.assertIn(SAFETY_503, r.tried[0]["body"])
        n, last = FB.summary()
        self.assertEqual((n, last["from_model"], last["to_model"]), (1, "p/persona", "r/reasoner"))

    def test_then_secondary_list_in_order(self):
        ent, model = entity(self, roles=ROLES_FB, by_model={"p/persona": 429, "r/reasoner": 503,
                                                            "s/second": 502, "s/third": "third answered"})
        r = ent.turn("hello", [])["result"]
        self.assertEqual(r.text, "third answered")
        order = []
        for c in model.calls:
            if c["model"] not in order:
                order.append(c["model"])
        self.assertEqual(order, ["p/persona", "r/reasoner", "s/second", "s/third"])
        self.assertEqual(r.tried[0]["attempts"], 3)        # the HTTP client's own retries came first
        self.assertEqual([t["kind"] for t in r.tried], ["primary", "reasoning", "secondary", "secondary"])

    def test_cooldown_skips_primary_then_returns(self):
        ent, model = entity(self, roles=ROLES_FB, by_model={"p/persona": 503, "r/reasoner": "fb"})
        self.assertEqual(ent.turn("a", [])["result"].text, "fb")
        n = len([c for c in model.calls if c["model"] == "p/persona"])
        self.assertEqual(ent.turn("b", [])["result"].text, "fb")         # cooling: primary not tried
        self.assertEqual(len([c for c in model.calls if c["model"] == "p/persona"]), n)
        self.assertTrue(FB.cooldowns().get("persona"))
        FB.reset()                                                       # cooldown over
        model.by_model["p/persona"] = "primary back"
        self.assertEqual(ent.turn("c", [])["result"].text, "primary back")

    def test_reasoning_content_is_stripped(self):
        msgs = [{"role": "assistant", "content": "a", "reasoning_content": "secret thinking"}]
        self.assertEqual(FB.strip_reasoning(msgs), [{"role": "assistant", "content": "a"}])

    def test_bad_request_does_not_fall_back(self):
        ent, model = entity(self, roles=ROLES_FB, by_model={"p/persona": 400})
        r = ent.turn("hello", [])["result"]
        self.assertFalse(r.ok)
        self.assertEqual([c["model"] for c in model.calls], ["p/persona"])

    def test_all_fail_plain_words(self):
        ent, _ = entity(self, roles=ROLES_FB, by_model={"p/persona": 503, "r/reasoner": 503, "s/second": 429,
                                                        "s/third": 503})
        r = ent.turn("hello", [])["result"]
        self.assertFalse(r.ok)
        msg = r.plain_error
        self.assertTrue(msg.startswith("NVIDIA's model was unavailable"), msg)
        self.assertIn(SAFETY_503, msg)
        self.assertIn("p/persona, r/reasoner, s/second and s/third", msg)
        self.assertNotIn("502", msg)

    def test_telegram_shows_plain_words_not_server_502(self):
        from nimlab import telegram
        e = RuntimeError("server 502: NVIDIA's model was unavailable (HTTP 503: " + SAFETY_503 +
                         "). I tried p/persona and r/reasoner; none of them answered. Try again in a minute.")
        txt = telegram.error_text(e)
        self.assertTrue(txt.startswith("NVIDIA's model was unavailable"), txt)
        self.assertNotIn("server 502", txt)
        self.assertIn("Sorry, something went wrong on my side", telegram.error_text(RuntimeError("boom")))

    def test_roles_menu_sets_secondary_list(self):
        from nimlab import rolemenu
        ent, _ = entity(self, roles={"persona": "p/persona", "reasoning": "r/reasoner"})
        answers = iter(["1", "1", "s/a, s/b", "3", "120", ""])
        out = []
        rolemenu.fallback_menu(ent, lambda p: next(answers), out.append)
        self.assertEqual(ent.roles["persona"]["fallbacks"], ["s/a", "s/b"])
        self.assertEqual(ent.cluster["routing_settings"]["fallback_cooldown_sec"], 120)
        self.assertEqual([d["model"] for _, d in ent.fallback_chain("persona")], ["r/reasoner", "s/a", "s/b"])
        self.assertTrue(any("r/reasoner" in x for x in out))

    def test_doctor_and_health_show_fallbacks(self):
        from nimlab import doctor
        ent, _ = entity(self, roles=ROLES_FB, by_model={"p/persona": 503, "r/reasoner": "ok"})
        ent.turn("x", [])
        rows = doctor.fallback_checks(ent)
        text = " ".join(str(m) for _, m in rows)
        self.assertIn("r/reasoner (reasoning)", text)
        self.assertIn("1 fallback(s) in the last 24 h", text)
        self.assertIn("fallbacks", doctor.QUICK)
        ent2, _ = entity(self, roles={"persona": "p/persona"})
        self.assertEqual(doctor.fallback_checks(ent2)[0][0], "warn")


# ---------------------------------------------------------------------------
# failed steps in the trace and the bug record (B-894BF1)
# ---------------------------------------------------------------------------
class TestFailedStepRecorded(DataDir):
    def test_persona_failure_in_trace_with_model_host_status_body(self):
        from nimlab import unified
        ent, _ = entity(self, roles={"persona": "p/persona"}, by_model={"p/persona": 503})
        res = unified.Mind(ent).run("hi")
        self.assertFalse(res.get("text"))
        row = [t for t in res["trace"] if t.get("role") == "persona" and not t.get("ok")][0]
        self.assertEqual(row["model"], "p/persona")
        self.assertEqual(row["status"], 503)
        self.assertIn("integrate.api.nvidia.com", row["host"])
        self.assertIn(SAFETY_503, row["body"])
        self.assertNotIn("nvapi", json.dumps(res["trace"]))
        self.assertTrue(res["error"].startswith("NVIDIA's model was unavailable"), res["error"])

    def test_bug_record_names_persona_target_and_upstream_host(self):
        from nimlab import bugs, unified
        ent, _ = entity(self, roles=ROLES_FB, by_model={"p/persona": 503, "r/reasoner": 503, "s/second": 503,
                                                        "s/third": 503})
        res = unified.Mind(ent).run("hi")
        keys = ("role", "label", "why", "ok", "ms", "target", "error", "model", "host", "status", "body",
                "attempts", "fallbacks")
        bug_trace = [{k: t.get(k) for k in keys if k in t} for t in res["trace"]]
        bid = bugs.record("upstream_error", res["error"], where="/v1/chat/completions", trace=bug_trace,
                          upstream=res.get("upstream"))
        self.assertTrue(bid)
        blob = ""
        for root, _, files in os.walk(self.data):
            for f in files:
                with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                    t = fh.read()
                if bid in t and '"trace"' in t:
                    blob += t
        self.assertTrue(blob, "the bug event was not written")
        self.assertIn("p/persona", blob)
        self.assertIn("integrate.api.nvidia.com", blob)
        self.assertIn("503", blob)
        first = [t for t in bug_trace if t.get("role") == "persona" and not t.get("ok")][0]
        self.assertEqual(first["fallbacks"], ["r/reasoner", "s/second", "s/third"])

    def test_host_of_never_keeps_query_or_credentials(self):
        self.assertEqual(FB.host_of("https://user:pw@gw.example.com:8443/v1/chat?key=abc"),
                         "gw.example.com:8443/v1/chat")


# ---------------------------------------------------------------------------
# 3b. paced sweep
# ---------------------------------------------------------------------------
class TestPacing(unittest.TestCase):
    def test_limiter_spaces_requests(self):
        t = [0.0]
        slept = []
        lim = RateLimiter(30, clock=lambda: t[0], sleep=lambda d: (slept.append(d), t.__setitem__(0, t[0] + d)))
        for _ in range(4):
            lim.wait()
        self.assertEqual(slept, [2.0, 2.0, 2.0])

    def test_retry_after_pauses_everyone(self):
        t = [100.0]
        slept = []
        lim = RateLimiter(60, clock=lambda: t[0], sleep=lambda d: slept.append(d))
        lim.wait()
        res = type("R", (), {"status": 429, "headers": {"retry-after": "7"}})()
        lim.note(res)
        lim.wait()
        self.assertAlmostEqual(slept[-1], 7.0)
        self.assertEqual(lim.pauses, 1)

    def test_rpm_setting_and_off(self):
        with mock.patch.dict(os.environ, {"NIMLAB_SWEEP_RPM": ""}):
            self.assertEqual(sweep_rpm({}), 30.0)
            self.assertEqual(sweep_rpm({"probe_rpm": 35}), 35.0)
        with mock.patch.dict(os.environ, {"NIMLAB_SWEEP_RPM": "0"}):
            self.assertEqual(RateLimiter(sweep_rpm({})).wait(), 0.0)

    def test_prober_is_paced(self):
        from nimlab import sweep
        slept = []
        lim = RateLimiter(30, clock=lambda: 0.0, sleep=slept.append)
        opener = RouteOpener([("chat", lambda r: FakeResponse(chat_body("ok")))])
        p = sweep.Prober(api_key="nvapi-x", http=HttpClient(opener=opener, retries=0), limiter=lim)
        plan = {"url": "https://integrate.api.nvidia.com/v1/chat/completions", "body": {"model": "m"}}
        for _ in range(3):
            p.probe_plan(plan)
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual(slept, [2.0, 4.0])      # a frozen clock: each waits behind the one before


if __name__ == "__main__":
    unittest.main()
