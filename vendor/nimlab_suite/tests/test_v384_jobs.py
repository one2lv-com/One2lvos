"""v3.8.4: scheduled jobs with a tool list get no fixed tool-step cap (only
their own tools, runaway guards instead); a user message, an email alert or
another job interrupts a repeating job, which ends and hands where it left
off to that job's next run (a choice for Free time, automatic for a job that
does one thing). Offline: every network call goes to a fake."""

import json
import time
import unittest
from unittest import mock

from nimlab import interrupts as IN, jobguard as JG, mcp as M, scheduler as SC, selfadmin as SA
from tests.fakes import FakeMCPServer
from tests.test_v383 import TOOLS, DataDir, entity, live_mcp


def call(name, **args):
    return '<tool_call>' + json.dumps({"name": name, "arguments": args}) + '</tool_call>'


class Policy:
    def approve(self, call, tool=None):
        return True, ""


class Box:
    """A minimal MCP box for run_tool_loop."""

    def __init__(self, names=("beat_lab",), fail=()):
        self.defs = {t["name"]: t for t in TOOLS}
        self.names = set(names)
        self.fail = set(fail)
        self.calls = []

    def tool(self, n):
        return self.defs.get(n)

    def call_tool(self, n, args):
        self.calls.append((n, args))
        if n in self.fail:
            return {"isError": True, "content": [{"type": "text", "text": "broken"}]}
        return {"content": [{"type": "text", "text": f"{n} ok {json.dumps(args)}"}]}


def guard(**kw):
    kw.setdefault("cfg", {"min_step_gap_sec": 0, "model_backoff_sec": 0})
    kw.setdefault("sleep", lambda s: None)
    return JG.JobGuard(**kw)


class TestJobGuard(unittest.TestCase):
    def test_same_failing_call_stops_the_loop(self):
        g = guard()
        self.assertIsNone(g.after_call("beat_lab", {"a": 1}, "error"))
        self.assertIsNone(g.after_call("beat_lab", {"a": 1}, "error"))
        why = g.after_call("beat_lab", {"a": 1}, "error")
        self.assertIn("same failing call", why)
        self.assertEqual(g.stopped["kind"], "runaway")

    def test_identical_results_stop_but_different_calls_do_not(self):
        g = guard()
        for i in range(20):
            self.assertIsNone(g.after_call("beat_lab", {"i": i}, "ok", f"r{i}"))
        for _ in range(3):
            self.assertIsNone(g.after_call("beat_lab", {"x": 1}, "ok", "same"))
        self.assertIn("identical result", g.after_call("beat_lab", {"x": 1}, "ok", "same"))

    def test_failures_in_a_row(self):
        g = guard()
        for i in range(5):
            self.assertIsNone(g.after_call("t", {"i": i}, "rejected"))
        self.assertIn("in a row", g.after_call("t", {"i": 9}, "failed"))

    def test_model_backoff_doubles_then_gives_up(self):
        slept = []
        g = JG.JobGuard(cfg={"model_backoff_sec": 1, "model_retry_max": 3}, sleep=slept.append,
                        mono=iter([0] + [i * 0.5 for i in range(1, 400)]).__next__)
        self.assertTrue(g.model_failed(1))
        self.assertTrue(g.model_failed(2))
        self.assertTrue(g.model_failed(3))
        self.assertFalse(g.model_failed(4))
        self.assertEqual(g.stopped["kind"], "model")
        self.assertTrue(slept)

    def test_deadline_wraps_up_before_the_timeout(self):
        t = [0.0]
        g = JG.JobGuard(timeout=600, mono=lambda: t[0], cfg={"wrap_up_sec": 60})
        t[0] = 530
        self.assertIsNone(g.check())
        t[0] = 541
        self.assertIn("nearly up", g.check())
        self.assertEqual(g.stopped["kind"], "deadline")

    def test_settings_from_cluster(self):
        s = JG.settings({"scheduler_settings": {"job_guard": {"same_failing_call_max": 5, "bogus": 1}}})
        self.assertEqual(s["same_failing_call_max"], 5)
        self.assertNotIn("bogus", s)


class TestToolLoop(unittest.TestCase):
    def loop(self, replies, g=None, max_steps=None, box=None, final="wrapped up"):
        box = box or Box()
        replies = list(replies)
        seen = []

        def chat(h):
            seen.append(list(h))
            r = replies.pop(0) if replies else "done"
            return (r, True) if not isinstance(r, tuple) else r
        out, trace = M.run_tool_loop(chat, [{"role": "user", "content": "go"}], box, Policy(),
                                     max_steps=max_steps, log=lambda *a: None,
                                     final_fn=lambda h: (final, True), guard=g)
        return out, trace, box, seen

    def test_no_cap_runs_more_than_four_steps(self):
        out, trace, box, _ = self.loop([call("beat_lab", n=i) for i in range(9)] + ["Made nine beats."],
                                       g=guard())
        self.assertEqual(out, "Made nine beats.")
        self.assertEqual(len(box.calls), 9)

    def test_normal_chat_cap_unchanged(self):
        out, trace, box, _ = self.loop([call("beat_lab", n=i) for i in range(9)], max_steps=4)
        self.assertEqual(len(box.calls), 4)
        self.assertEqual(trace[-1]["stopped"], "max_steps")

    def test_runaway_same_failing_call_ends_with_an_answer(self):
        out, trace, box, _ = self.loop([call("beat_lab", a=1)] * 20, g=guard(), box=Box(fail={"beat_lab"}))
        self.assertEqual(len(box.calls), 3)
        self.assertEqual(out, "wrapped up")
        self.assertEqual(trace[-1]["stopped"], "runaway")

    def test_interrupt_ends_without_another_model_call(self):
        hit = {"n": 0}

        def fake_interrupt(t0, name):
            hit["n"] += 1
            return {"kind": IN.USER, "source": "/chat/completions", "ts": t0 + 1} if hit["n"] > 4 else None
        g = guard(interruptible=True, interrupt_fn=fake_interrupt)
        finals = []
        box = Box()
        replies = [call("beat_lab", n=i) for i in range(30)]
        out, trace = M.run_tool_loop(lambda h: (replies.pop(0), True), [{"role": "user", "content": "go"}], box,
                                     Policy(), max_steps=None, log=lambda *a: None,
                                     final_fn=lambda h: finals.append(1) or ("x", True), guard=g)
        self.assertIn("Stopped early", out)
        self.assertEqual(g.stopped["kind"], "interrupted")
        self.assertEqual(finals, [])
        self.assertLess(len(box.calls), 5)
        self.assertIn("You called beat_lab", g.progress)

    def test_model_429_backs_off_then_continues(self):
        g = guard()
        out, _, box, seen = self.loop([("rate limited", False), ("rate limited", False), call("beat_lab"),
                                       "ok"], g=g)
        self.assertEqual(out, "ok")
        self.assertEqual(box.calls, [("beat_lab", {})])

    def test_model_storm_gives_up(self):
        g = guard(cfg={"min_step_gap_sec": 0, "model_backoff_sec": 0, "model_retry_max": 2})
        out, _, box, seen = self.loop([("429", False)] * 10, g=g)
        self.assertEqual(len(seen), 3)
        self.assertEqual(g.stopped["kind"], "model")


class TestScopedBox(DataDir):
    def test_offers_and_load_tools_refuse_tools_outside_the_job(self):
        srv = FakeMCPServer(TOOLS)
        ent, _ = entity(self, ["x"])
        live_mcp(ent, srv)
        ent.ensure_tools(force=True)
        with SA.identity(admin=True, who="t", source="scheduler"), SA.task_tools(["beat_lab"], True):
            box = SA.ToolBox(ent, ent.mcp)
        self.assertTrue(box.offers("beat_lab"))
        self.assertTrue(box.offers(M.LOAD_TOOLS))
        self.assertFalse(box.offers("terminal"))
        text, err, loaded = M.load_tools_result(box, {"names": ["terminal", "beat_lab"]})
        self.assertEqual(loaded, ["beat_lab"])
        self.assertIn("not one of this job's tools", text)
        r = box.call_tool("terminal", {})
        self.assertTrue(r.get("isError"))
        self.assertNotIn("terminal", [n for n, _ in srv.calls])


class TestQuillTaskJobs(DataDir):
    def ctx(self, script):
        srv = FakeMCPServer(TOOLS)
        ent, model = entity(self, script)
        live_mcp(ent, srv)
        ent.cluster.setdefault("scheduler_settings", {})["job_guard"] = {"min_step_gap_sec": 0}
        c = SC.LiveContext()
        c._ent = ent
        return c, srv, model

    JOB = {"name": "free-time", "schedule": "FREQ=HOURLY;BYMINUTE=0"}
    FT = {"prompt": "free time", "tools": ["beat_lab", "generate_creative_art"], "only": True,
          "require_tool": True}

    def test_more_than_four_tool_steps_in_a_job(self):
        c, srv, _ = self.ctx([call("beat_lab", n=i) for i in range(7)] + ["Seven beats."])
        r = SC.run_task(dict(self.FT), c, "free-time", 600, job=self.JOB)
        self.assertTrue(r.ok, r.output)
        self.assertEqual(len([n for n, _ in srv.calls if n == "beat_lab"]), 7)
        self.assertIn("Seven beats.", r.output)

    def test_out_of_list_tool_refused_in_unlimited_job(self):
        c, srv, _ = self.ctx([call("terminal"), call("beat_lab", n=1), "done"])
        r = SC.run_task(dict(self.FT), c, "free-time", 600, job=self.JOB)
        self.assertNotIn("terminal", [n for n, _ in srv.calls])
        self.assertTrue(r.ok, r.output)

    def test_unlimited_can_be_switched_off(self):
        c, srv, _ = self.ctx([call("beat_lab", n=i) for i in range(9)] + ["x", "y"])
        c._ent.cluster["scheduler_settings"]["unlimited_job_tools"] = False
        SC.run_task(dict(self.FT), c, "free-time", 600, job=self.JOB)
        self.assertLessEqual(len(srv.calls), int(c._ent.mcp_settings.get("max_tool_steps", 4)))

    def interrupting(self, n_before, then="Back to it.", **extra):
        """A script whose model marks a user message after n_before tool steps."""
        steps = {"n": 0}

        def step(body):
            steps["n"] += 1
            if steps["n"] == n_before + 1:
                time.sleep(0.01)
                IN.mark(IN.USER, "/chat/completions")
            return call("beat_lab", n=steps["n"])
        return [step] * (n_before + 1) + [then]

    def test_interrupted_free_time_ends_saves_and_next_run_offers_a_choice(self):
        c, srv, model = self.ctx(self.interrupting(3))
        r = SC.run_task(dict(self.FT), c, "free-time", 600, job=self.JOB)
        self.assertTrue(r.ok, r.output)
        self.assertIn("Ended early: SeVin sent Quill a message", r.output)
        self.assertEqual(r.data["stopped"]["kind"], "interrupted")
        n_calls = len(model.calls)
        left = IN.load_leftover("free-time")
        self.assertIn("You called beat_lab", left["progress"])
        # next run: told where it left off, with the choice
        c2, srv2, model2 = self.ctx([call("generate_creative_art"), "Drew instead."])
        r2 = SC.run_task(dict(self.FT), c2, "free-time", 600, job=self.JOB)
        self.assertTrue(r2.ok, r2.output)
        first = json.dumps(model2.calls[0]["messages"])
        self.assertIn("LAST TIME THIS JOB WAS INTERRUPTED", first)
        self.assertIn("it's your choice", first)
        self.assertIsNone(IN.load_leftover("free-time"))     # finished normally: cleared
        self.assertTrue(n_calls >= 4)

    def test_one_function_job_continues_automatically(self):
        job = {"name": "beats", "schedule": "FREQ=HOURLY;BYMINUTE=5"}
        a = {"prompt": "make beats", "tools": ["beat_lab"], "only": True, "require_tool": False}
        c, _, _ = self.ctx(self.interrupting(2))
        SC.run_task(dict(a), c, "beats", 600, job=job)
        self.assertIsNotNone(IN.load_leftover("beats"))
        c2, _, model2 = self.ctx(["Finished."])
        SC.run_task(dict(a), c2, "beats", 600, job=job)
        first = json.dumps(model2.calls[0]["messages"])
        self.assertIn("Continue it from where you stopped", first)
        self.assertNotIn("your choice", first)

    def test_own_start_and_earlier_marks_do_not_interrupt(self):
        IN.mark(IN.USER, "/chat/completions")
        time.sleep(0.01)
        IN.mark(IN.JOB, "free-time")
        c, srv, _ = self.ctx([call("beat_lab", n=i) for i in range(5)] + ["All done."])
        r = SC.run_task(dict(self.FT), c, "free-time", 600, job=self.JOB)
        self.assertNotIn("stopped", r.data)
        self.assertIn("All done.", r.output)

    def test_another_job_starting_interrupts(self):
        c, _, _ = self.ctx([call("beat_lab", n=1),
                            lambda b: (IN.mark(IN.JOB, "heartbeat"), call("beat_lab", n=2))[1], "nope"])
        time.sleep(0.01)
        r = SC.run_task(dict(self.FT), c, "free-time", 600, job=self.JOB)
        self.assertIn("the scheduled job heartbeat started", r.output)

    def test_one_off_jobs_are_not_interruptible(self):
        job = {"name": "gmail-alert-1", "schedule": "at 2026-11-14 05:00"}
        a = {"prompt": "reply", "tools": ["beat_lab"], "only": True, "require_tool": False}
        c, srv, _ = self.ctx([call("beat_lab", n=1), lambda b: (IN.mark(IN.USER, "x"), call("beat_lab", n=2))[1],
                              call("beat_lab", n=3), "Replied."])
        r = SC.run_task(dict(a), c, "gmail-alert-1", 600, job=job)
        self.assertIn("Replied.", r.output)
        self.assertEqual(len(srv.calls), 3)

    def test_check_task_keeps_an_explicit_interruptible(self):
        self.assertTrue(SC.check_task({"prompt": "p", "tools": ["a"], "interruptible": True})["interruptible"])
        self.assertFalse(SC.check_task({"prompt": "p", "tools": ["a"], "interruptible": False})["interruptible"])
        self.assertNotIn("interruptible", SC.check_task({"prompt": "p", "tools": ["a"]}))

    def test_free_time_template(self):
        spec = SC.free_time_template(["beat_lab", "generate_creative_art"])
        self.assertTrue(spec["action"]["interruptible"])
        self.assertEqual(spec["timeout_sec"], 1800)
        self.assertIn("BYMINUTE=0", spec["schedule"])


class TestSchedulerMarks(DataDir):
    def test_job_start_marks_and_interrupted_run_without_links_goes_to_log(self):
        class Ctx:
            pass
        res = SC.ActionResult(True, "Ended early", data={"interrupted": "x"})
        with mock.patch.object(SC, "run_action", return_value=res), \
                mock.patch("nimlab.routing.deliver", return_value=["log: ok"]) as deliver:
            SC.create_job({"name": "ft", "schedule": "FREQ=HOURLY;BYMINUTE=0", "action_type": "quill_task",
                           "action": {"prompt": "p", "tools": ["a"]}, "result_to": "telegram"},
                          who="cli", source="cli")
            s = SC.Scheduler(ctx=Ctx(), log=lambda *a: None)
            s.run_now("ft")
        self.assertTrue(any(m.get("source") == "ft" for m in IN.marks()))
        self.assertEqual(deliver.call_args[0][0]["dest"], "log")


class TestServerMarks(unittest.TestCase):
    def test_user_paths(self):
        from nimlab import server
        self.assertIn("/chat/completions", server.USER_PATHS)
        with mock.patch.object(IN, "mark") as m:
            server._mark_user("/chat/completions")
        m.assert_called_once_with(IN.USER, "/chat/completions")


if __name__ == "__main__":
    unittest.main()


from tests.test_v380 import LabCase  # noqa: E402
from nimlab import heartbeat as HB  # noqa: E402


class TestHeartbeatInterrupts(LabCase):
    def test_interrupted_heartbeat_carries_its_actions_to_the_next_one(self):
        answer = json.dumps({"decisions": [{"name": "health-check", "decision": "take"},
                                           {"name": "memory-digest", "decision": "take"}], "summary": "s"})
        state = {"interrupt": True}

        def fn(prompt):
            if prompt.startswith("HEARTBEAT."):
                if state["interrupt"]:
                    time.sleep(0.01)
                    IN.mark(IN.USER, "/chat/completions")
                return True, "```json\n" + answer + "\n```"
            return True, "did " + prompt.split("'")[1]
        self.ctx.quill_fn = fn
        r = SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        self.assertTrue(r.ok, r.output)
        self.assertEqual(r.data["undone"], ["health-check", "memory-digest"])
        self.assertIn("interrupted", HB.last_report()["summary"])
        # the next heartbeat takes them first, automatically, and they are not up for a new decision
        state["interrupt"] = False
        self.ctx.quill_calls.clear()
        time.sleep(0.01)
        r2 = SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        self.assertTrue(r2.ok, r2.output)
        d = HB.last_report()["decisions"]
        carried = [x["name"] for x in d if x.get("carried")]
        self.assertEqual(carried, ["health-check", "memory-digest"])
        decision = [c for w, c in self.ctx.quill_calls if c.startswith("HEARTBEAT.")][0]
        self.assertNotIn("- memory-digest (", decision)
        self.assertIsNone(IN.load_leftover("heartbeat"))


class TestNoRetry(unittest.TestCase):
    def test_auth_errors_are_not_retried(self):
        n = []
        g = guard()
        out, _ = M.run_tool_loop(lambda h: n.append(1) or ("HTTP 401: Unauthorized access", False),
                                 [{"role": "user", "content": "go"}], Box(), Policy(), max_steps=None,
                                 log=lambda *a: None, guard=g)
        self.assertEqual(len(n), 1)
        self.assertIn("401", out)
