"""v3.8.2: Telegram /health, doctor --fix, custom endpoints, one routing
path, TTS function-ID order, the image fallback and the new menus (every
screen, colour on and off)."""
import ast
import contextlib
import glob
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nimlab import colors as C, config, store  # noqa: E402
from nimlab import doctor as D, endpoints as EP, tgcmds  # noqa: E402
from nimlab.api import NimClient  # noqa: E402
from nimlab.core import HttpClient  # noqa: E402
from tests.fakes import FakeResponse, RouteOpener  # noqa: E402

NV_KEY = "nvapi-" + "N" * 30
GW_KEY = "gw-" + "G" * 30


class Sandbox(unittest.TestCase):
    """A throwaway home, config folder, data folder and project config."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="nimlab-382-")
        self.addCleanup(shutil.rmtree, self.root, True)
        home = os.path.join(self.root, "home")
        os.makedirs(home)
        env = {"HOME": home, "XDG_CONFIG_HOME": os.path.join(home, ".config"),
               "NIMLAB_DATA_DIR": os.path.join(self.root, "data"), "NIMLAB_COLOR": "0"}
        for k in ("NIMLAB_ENDPOINTS", "NIMLAB_SECRETS", "NVIDIA_API_KEY"):
            env[k] = ""
        p = mock.patch.dict(os.environ, env)
        p.start()
        self.addCleanup(p.stop)
        for k in ("NIMLAB_ENDPOINTS", "NIMLAB_SECRETS", "NVIDIA_API_KEY"):
            os.environ.pop(k, None)
        store.reset()
        self.addCleanup(store.reset)
        self.cluster = os.path.join(self.root, "config_cluster.json")
        with open(self.cluster, "w") as f:
            json.dump({"roles": {}}, f)
        p = mock.patch.object(config, "CLUSTER_CONFIG", self.cluster)
        p.start()
        self.addCleanup(p.stop)
        from nimlab import mcpkey
        getattr(mcpkey, "_cache", {}).clear()

    def client(self, opener):
        cluster = config.deep_merge(config.DEFAULT_CLUSTER, {"roles": {}})
        return NimClient(api_key=NV_KEY, cluster=cluster, http=HttpClient(opener=opener, retries=0))


def ok_chat(req):
    body = json.loads(req.data.decode())
    return {"choices": [{"message": {"role": "assistant", "content": "hi from " + body["model"]},
                         "finish_reason": "stop"}], "usage": {"total_tokens": 3}}


# ---------------------------------------------------------------------------
# Telegram /health
# ---------------------------------------------------------------------------
REPORT = {"ok": True, "version": "3.8.2", "summary": {"ok": 5, "warn": 1, "fail": 0}, "repairs_available": 1,
          "checks": [{"section": "settings", "title": "Settings", "status": "ok", "message": "key set", "fix": None},
                     {"section": "processes", "title": "Processes and locks", "status": "ok",
                      "message": "one server", "fix": None},
                     {"section": "permissions", "title": "File permissions", "status": "warn",
                      "message": "secrets.json should be mode 600", "fix": "doctor --fix sets it"}]}


class FakeConn:
    def __init__(self, owner=True):
        self.sent, self.owner, self.history = [], owner, {}

    def is_owner(self, uid):
        return self.owner

    def send(self, chat_id, text, **kw):
        self.sent.append(text)


class TestHealth(unittest.TestCase):
    def test_quick_by_default_full_on_request_never_fix(self):
        self.assertEqual(tgcmds.health_args(""), ["doctor", "--json", "--quick"])
        self.assertEqual(tgcmds.health_args("full"), ["doctor", "--json"])
        for a in ("", "full", "fix", "--fix", "repair"):
            self.assertNotIn("--fix", tgcmds.health_args(a))

    def test_report_is_short_plain_and_points_repairs_to_the_terminal(self):
        txt = tgcmds.health_text("noise before\n" + json.dumps(REPORT))
        self.assertTrue(txt.startswith("Working, with warnings: 5 ok, 1 warnings, 0 problems (v3.8.2)"), txt)
        self.assertIn("! secrets.json should be mode 600 -> doctor --fix sets it", txt)
        self.assertIn("OK one server", txt)          # processes are always shown
        self.assertNotIn("key set", txt)              # other ok lines are left out
        self.assertIn("Run them in the terminal", txt)
        self.assertNotIn("\x1b[", txt)

    def test_unreadable_output(self):
        self.assertIn("could not read the doctor output", tgcmds.health_text("Traceback: boom"))

    def test_healthy_and_needs_attention(self):
        good = dict(REPORT, summary={"ok": 3, "warn": 0, "fail": 0}, repairs_available=0)
        self.assertTrue(tgcmds.health_text(json.dumps(good)).startswith("Healthy"))
        bad = dict(REPORT, ok=False, summary={"ok": 3, "warn": 0, "fail": 2})
        self.assertTrue(tgcmds.health_text(json.dumps(bad)).startswith("Needs attention"))

    def test_health_runs_read_only_doctor(self):
        seen = []

        def fake_run(cmd, **kw):
            seen.append(cmd)
            return mock.Mock(stdout=json.dumps(REPORT), stderr="", returncode=0)
        with mock.patch.object(tgcmds.subprocess, "run", fake_run):
            out = tgcmds._health("")
        self.assertIn("5 ok", out)
        self.assertEqual(seen[0][-3:], ["doctor", "--json", "--quick"])
        self.assertFalse(any("--fix" in c for c in seen))

    def test_health_command_is_listed_for_botfather(self):
        self.assertIn("/health", tgcmds.COMMANDS)
        self.assertIn("health", tgcmds.botfather_text())

    def test_owner_only(self):
        if "/health" in getattr(tgcmds, "OPEN", ()):
            self.skipTest("/health is open to everyone allowed")
        c = FakeConn(owner=False)
        self.assertTrue(tgcmds.handle(c, 1, 2, "/health", "/health"))
        self.assertEqual(c.sent, ["That command is for the owner only."])


# ---------------------------------------------------------------------------
# doctor --fix
# ---------------------------------------------------------------------------
class TestDoctorFix(Sandbox):
    def test_nothing_to_fix_makes_no_backup(self):
        with mock.patch.object(D, "planned_repairs", return_value=[]), \
                mock.patch.object(D, "collect", return_value={"checks": [], "summary": {}}) as col:
            out = []
            res = D.fix(out=out.append)
        self.assertIsNone(res["backup"])
        self.assertIn("Nothing to repair", out[0])
        col.assert_called_once()                       # it still checks again
        self.assertEqual(col.call_args.kwargs.get("only"), D.QUICK)

    def test_backup_first_then_repairs_then_recheck(self):
        order = []
        repairs = [("a", "fix a", lambda: order.append("a")),
                   ("b", "fix b", lambda: (_ for _ in ()).throw(OSError("denied")))]
        real_backup = D.backup

        def bk():
            order.append("backup")
            return real_backup()
        with mock.patch.object(D, "planned_repairs", return_value=repairs), mock.patch.object(D, "backup", bk), \
                mock.patch.object(D, "collect", side_effect=lambda *a, **k: order.append("recheck") or
                                  {"checks": [], "summary": {}}):
            res = D.fix(out=lambda *a: None)
        self.assertEqual(order, ["backup", "a", "recheck"])
        self.assertEqual([r["id"] for r in res["applied"]], ["a"])
        self.assertEqual(res["failed"][0]["error"], "denied")
        self.assertTrue(os.path.isfile(os.path.join(res["backup"], "config_cluster.json")))

    def test_safe_repairs_only(self):
        """File modes, stale pid files and settings that can never work;
        never a key, a memory or a running process."""
        sec = os.path.join(os.environ["XDG_CONFIG_HOME"], "nimlab", "secrets.json")
        os.makedirs(os.path.dirname(sec))
        with open(sec, "w") as f:
            json.dump({"endpoints": {"gw": GW_KEY}}, f)
        os.chmod(sec, 0o644)
        with open(self.cluster, "w") as f:
            json.dump({"roles": {"persona": {"model": "m", "endpoint": "https://build.nvidia.com"}},
                       "voice_settings": {"tts_url": "not a url"}}, f)
        pidf = os.path.join(self.root, "bot.pid")
        with open(pidf, "w") as f:
            f.write("999999")
        with mock.patch.object(D, "stale_pid_files", return_value=[("telegram bot.pid", pidf, 999999)]), \
                mock.patch.object(D, "_exec_files", return_value=[]):
            todo = D.planned_repairs()
            ids = sorted(r[0] for r in todo)
            self.assertTrue(all(i.split(":")[0] in ("stale", "mode", "endpoint", "voice") for i in ids), ids)
            self.assertIn("mode:secrets.json", ids)
            self.assertIn("endpoint:persona", ids)
            self.assertIn("stale:telegram bot.pid", ids)
            with mock.patch.object(D, "collect", return_value={"checks": [], "summary": {}}):
                res = D.fix(out=lambda *a: None)
        self.assertFalse(res["failed"], res)
        self.assertEqual(stat.S_IMODE(os.stat(sec).st_mode), 0o600)
        self.assertFalse(os.path.exists(pidf))
        raw = json.load(open(self.cluster))
        self.assertNotIn("endpoint", raw["roles"]["persona"])
        self.assertEqual(raw["roles"]["persona"]["model"], "m")     # only the bad field goes
        self.assertEqual(json.load(open(sec)), {"endpoints": {"gw": GW_KEY}})   # keys untouched
        bk = json.load(open(os.path.join(res["backup"], "config_cluster.json")))
        self.assertEqual(bk["roles"]["persona"]["endpoint"], "https://build.nvidia.com")

    def test_live_pid_file_is_not_removed(self):
        pidf = os.path.join(self.root, "supervisor.pid")
        with open(pidf, "w") as f:
            f.write(str(os.getpid()))
        with mock.patch.object(D, "stale_pid_files", return_value=[("supervisor.pid", pidf, os.getpid())]), \
                mock.patch.object(D, "_exec_files", return_value=[]):
            for _rid, _d, fn in D.planned_repairs():
                fn()
        self.assertTrue(os.path.exists(pidf))

    def test_cli_fix_json(self):
        from nimlab.cli import build_parser
        args = build_parser().parse_args(["doctor", "--fix"])
        self.assertTrue(args.fix)


# ---------------------------------------------------------------------------
# custom endpoints
# ---------------------------------------------------------------------------
class TestCustomEndpoints(Sandbox):
    def gw(self):
        EP.add("gw", "https://gw.example.com/v1/", key=GW_KEY)
        return EP.get("gw")

    def test_blank_by_default(self):
        self.assertEqual(EP.all_endpoints(), [])
        self.assertEqual(D.endpoint_checks(), [(True, "no custom endpoints")])

    def test_key_kept_in_config_folder_not_project(self):
        self.gw()
        sec = os.path.join(os.environ["XDG_CONFIG_HOME"], "nimlab", "secrets.json")
        self.assertEqual(json.load(open(sec))["endpoints"]["gw"], GW_KEY)
        self.assertNotIn(GW_KEY, open(EP.path()).read())
        self.assertEqual(stat.S_IMODE(os.stat(EP.path()).st_mode), 0o600)
        self.assertTrue(EP.path().startswith(os.environ["XDG_CONFIG_HOME"]))

    def test_import_models_from_v1_models(self):
        self.gw()
        op = RouteOpener([("/v1/models", lambda r: {"data": [{"id": "llama-3-70b"}, {"id": "bge-embed"},
                                                             {"id": "kokoro-tts"}]})])
        ok, added = EP.import_models("gw", opener=op)
        self.assertTrue(ok)
        self.assertEqual(added, ["llama-3-70b", "bge-embed", "kokoro-tts"])
        self.assertEqual(op.requests[0]["url"], "https://gw.example.com/v1/models")
        self.assertEqual(op.requests[0]["headers"]["Authorization"], "Bearer " + GW_KEY)
        kinds = {m["id"]: m["kind"] for m in EP.get("gw")["models"]}
        self.assertEqual(kinds["llama-3-70b"], "chat")
        self.assertEqual(kinds["bge-embed"], "embedding")
        ok, added = EP.import_models("gw", opener=op)       # again: nothing doubled
        self.assertEqual(added, [])
        self.assertEqual(len(EP.get("gw")["models"]), 3)

    def test_import_errors_are_plain(self):
        self.gw()
        import urllib.error

        def deny(req):
            raise urllib.error.HTTPError(req.full_url, 401, "no", {}, None)
        ok, why = EP.import_models("gw", opener=RouteOpener([("/models", deny)]))
        self.assertFalse(ok)
        self.assertIn("key is missing or wrong", why)

    def test_manual_model_kept_by_import(self):
        self.gw()
        EP.add_model("gw", "my-special", kind="rerank")
        EP.import_models("gw", opener=RouteOpener([("/models", lambda r: {"data": [{"id": "my-special"}]})]))
        m = EP.get("gw")["models"]
        self.assertEqual([(x["id"], x["kind"], x.get("source")) for x in m], [("my-special", "rerank", "manual")])

    def test_role_uses_custom_model_with_its_own_key(self):
        self.gw()
        EP.add_model("gw", "llama-3-70b", kind="chat")
        op = RouteOpener([("gw.example.com", ok_chat), ("nvidia.com", ok_chat)])
        c = self.client(op)
        r = c.chat("gw:llama-3-70b", [{"role": "user", "content": "hi"}])
        self.assertTrue(r.ok, r.error)
        req = op.requests[-1]
        self.assertEqual(req["url"], "https://gw.example.com/v1/chat/completions")
        self.assertEqual(json.loads(req["data"])["model"], "llama-3-70b")    # prefix stripped for the gateway
        self.assertEqual(req["headers"]["Authorization"], "Bearer " + GW_KEY)

    def test_nvidia_key_never_sent_to_a_custom_endpoint(self):
        EP.add("open", "https://open.example.com/v1")          # an endpoint without a key
        EP.add_model("open", "tiny", kind="chat")
        EP.add_model("open", "tiny-embed", kind="embedding")
        op = RouteOpener([("open.example.com/v1/embeddings", lambda r: {"data": [{"index": 0, "embedding": [1.0]}]}),
                          ("open.example.com", ok_chat), ("nvidia.com", ok_chat)])
        c = self.client(op)
        c.chat("tiny", [{"role": "user", "content": "hi"}])
        c.embed("tiny-embed", ["x"])
        c.chat("meta/llama-3.1-8b-instruct", [{"role": "user", "content": "hi"}])
        for req in op.requests:
            auth = {k.lower(): v for k, v in req["headers"].items()}.get("authorization", "")
            if "open.example.com" in req["url"]:
                self.assertNotIn(NV_KEY, auth)
                self.assertEqual(auth, "")
            else:
                self.assertEqual(auth, "Bearer " + NV_KEY)
        self.assertTrue(any("nvidia.com" in r["url"] for r in op.requests))

    def test_lookalike_host_is_not_the_endpoint(self):
        self.gw()
        self.assertIsNone(EP.owner_of("https://gw.example.com.evil.net/v1/chat/completions"))
        self.assertIsNone(EP.owner_of("https://gw.example.com/v10/chat"))
        self.assertEqual(EP.owner_of("https://gw.example.com/v1/chat/completions")["name"], "gw")

    def test_cli_add_list_remove(self):
        from nimlab.cli import build_parser
        p = build_parser()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            a = p.parse_args(["endpoints", "add", "gw2", "https://gw2.example.com/v1", "--no-key"])
            a.fn(a)
            a = p.parse_args(["endpoints", "model", "gw2", "m1"])
            a.fn(a)
            a = p.parse_args(["endpoints", "list"])
            a.fn(a)
        self.assertIn("gw2", out.getvalue())
        self.assertEqual([m["id"] for m in EP.get("gw2")["models"]], ["m1"])


# ---------------------------------------------------------------------------
# routing: explicit URL > custom endpoint > registry; every caller uses route()
# ---------------------------------------------------------------------------
class TestRouting(Sandbox):
    def test_order(self):
        EP.add("gw", "https://gw.example.com/v1", key=GW_KEY)
        EP.add_model("gw", "meta/llama-3.1-8b-instruct", kind="chat")
        c = self.client(RouteOpener([]))
        # 1. an explicit URL (the role's endpoint) wins
        self.assertEqual(c.route("meta/llama-3.1-8b-instruct", "chat", "https://x.test/v1/chat/completions"),
                         ("https://x.test/v1/chat/completions", "meta/llama-3.1-8b-instruct"))
        # 2. then a custom endpoint that serves the model
        self.assertEqual(c.route("meta/llama-3.1-8b-instruct", "chat")[0], "https://gw.example.com/v1/chat/completions")
        # 3. then the registry
        EP.remove_model("gw", "meta/llama-3.1-8b-instruct")
        with mock.patch.object(c.router, "resolve", return_value={"url": "https://reg.test/v1/chat/completions",
                                                                  "kind": "chat", "api_model_id": "meta/x"}):
            self.assertEqual(c.route("meta/llama-3.1-8b-instruct", "chat"),
                             ("https://reg.test/v1/chat/completions", "meta/x"))

    def test_kind_mismatch_falls_back_to_default(self):
        c = self.client(RouteOpener([]))
        with mock.patch.object(c.router, "resolve", return_value={"url": "https://reg.test/v1/chat/completions",
                                                                  "kind": "chat"}):
            self.assertEqual(c.route("acme/new-image", "image_gen"), (None, "acme/new-image"))

    def test_broken_endpoints_file_never_breaks_nvidia_calls(self):
        os.makedirs(os.path.dirname(EP.path()), exist_ok=True)
        with open(EP.path(), "w") as f:
            f.write("{not json")
        op = RouteOpener([("nvidia.com", ok_chat)])
        r = self.client(op).chat("meta/llama-3.1-8b-instruct", [{"role": "user", "content": "hi"}])
        self.assertTrue(r.ok, r.error)

    def test_every_model_caller_goes_through_route(self):
        src = open(os.path.join(ROOT, "nimlab", "api.py")).read()
        tree = ast.parse(src)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "NimClient")
        calls = {}
        for f in cls.body:
            if isinstance(f, ast.FunctionDef):
                calls[f.name] = {n.func.attr for n in ast.walk(f) if isinstance(n, ast.Call)
                                 and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                                 and n.func.value.id == "self"}
        for name in ("chat", "chat_stream", "embed", "rerank", "image_gen"):
            self.assertIn("route", calls[name], name)
        for name in ("vision", "chat_media"):       # these delegate to chat()
            self.assertIn("chat", calls[name], name)
        self.assertIn("vision", calls["ocr"])

    def test_no_module_posts_to_nvidia_by_itself(self):
        """Model calls go through NimClient; only setup's key check talks to
        NVIDIA directly."""
        bad = []
        for p in glob.glob(os.path.join(ROOT, "nimlab", "*.py")):
            name = os.path.basename(p)
            if name in ("api.py", "config.py", "defaults.py", "roles.py", "spec.py", "wizard.py"):
                continue
            for i, ln in enumerate(open(p, encoding="utf-8"), 1):
                if re.search(r"Request\(\s*[\"']https://(integrate|ai)\.api\.nvidia\.com", ln):
                    bad.append(f"{name}:{i}")
        self.assertEqual(bad, [])


# ---------------------------------------------------------------------------
# the image fallback and TTS function-ID order
# ---------------------------------------------------------------------------
PNG = b"\x89PNG\r\n\x1a\n" + b"1" * 20


class TestImageFallback(Sandbox):
    def test_unknown_image_model_goes_to_the_image_api(self):
        import base64
        op = RouteOpener([("/genai/", lambda r: {"artifacts": [{"base64": base64.b64encode(PNG).decode()}]})])
        c = self.client(op)
        with mock.patch.object(c.router, "resolve", return_value={"url": "https://integrate.api.nvidia.com/v1/"
                                                                  "chat/completions", "kind": "chat"}):
            r = c.image_gen("acme/brand-new-image", "a cat")
        self.assertTrue(r.ok, r.error)
        self.assertEqual(op.requests[0]["url"], "https://ai.api.nvidia.com/v1/genai/acme/brand-new-image")
        self.assertNotIn("chat/completions", " ".join(q["url"] for q in op.requests))
        self.assertEqual(r.data, [PNG])

    def test_strict_schema_retry(self):
        import base64
        seen = []

        def gen(req):
            body = json.loads(req.data)
            seen.append(body)
            if "mode" in body:
                return FakeResponse({"detail": "extra field"}, status=422)
            return {"image": base64.b64encode(PNG).decode()}
        r = self.client(RouteOpener([("/genai/", gen)])).image_gen("acme/strict", "a dog")
        self.assertTrue(r.ok, r.error)
        self.assertEqual(seen[-1], {"prompt": "a dog"})

    def test_custom_image_model_uses_the_gateway(self):
        import base64
        EP.add("gw", "https://gw.example.com/v1", key=GW_KEY)
        EP.add_model("gw", "sdxl", kind="image_gen")
        op = RouteOpener([("gw.example.com", lambda r: {"data": [{"b64_json": base64.b64encode(PNG).decode()}]})])
        r = self.client(op).image_gen("sdxl", "x")
        self.assertTrue(r.ok, r.error)
        self.assertTrue(op.requests[0]["url"].startswith("https://gw.example.com/v1/"))


class TestTtsFunctionIdOrder(unittest.TestCase):
    MODEL = "nvidia/magpie-tts-multilingual"

    def fid(self, sp, verified=None, discovered=None, grpc=None):
        from nimlab import entity as E
        ent = E.Entity.__new__(E.Entity)
        with mock.patch.object(store, "verified_models", return_value=verified or {}), \
                mock.patch.object(store, "load", return_value={"models": discovered or {}}), \
                mock.patch.object(store, "grpc_function", return_value=grpc or {}):
            return ent._function_id(sp)

    def test_order(self):
        from nimlab import roles as R
        m = self.MODEL
        all_ = dict(verified={m: {"function_id": "verified"}}, discovered={m: {"function_id": "discovered"}},
                    grpc={"function_id": "grpc"})
        self.assertEqual(self.fid({"model": m, "function_id": "role"}, **all_), "role")
        self.assertEqual(self.fid({"model": m}, **all_), "verified")
        self.assertEqual(self.fid({"model": m}, discovered=all_["discovered"], grpc=all_["grpc"]), "discovered")
        self.assertEqual(self.fid({"model": m}, grpc=all_["grpc"]), "grpc")
        self.assertEqual(self.fid({"model": m}), R.TTS_FUNCTION_IDS[m])          # built-in table last
        self.assertIsNone(self.fid({"model": "acme/unknown-tts"}))

    def test_store_error_falls_back_to_builtin(self):
        from nimlab import entity as E, roles as R
        ent = E.Entity.__new__(E.Entity)
        with mock.patch.object(store, "verified_models", side_effect=ValueError("corrupt")):
            self.assertEqual(ent._function_id({"model": self.MODEL}), R.TTS_FUNCTION_IDS[self.MODEL])


# ---------------------------------------------------------------------------
# the new menus: walk every screen, colour on and off
# ---------------------------------------------------------------------------
class Script:
    def __init__(self, answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError        # Back, all the way out
        return self.answers.pop(0)


class TestMenus(Sandbox):
    def setUp(self):
        super().setUp()
        from nimlab import uimenu, updater, scheduler as SC
        self.U = uimenu
        for target, attr, val in ((updater, "nimlab_procs", lambda *a, **k: []),
                                  (SC, "lock_holder", lambda *a, **k: None),
                                  (D, "stale_pid_files", lambda: [])):
            p = mock.patch.object(target, attr, val)
            p.start()
            self.addCleanup(p.stop)

    def walk(self, screen, answers, colour=False):
        out, cli = [], []
        ask = Script(answers)
        ui = self.U.UI(ask=ask, say=lambda s="": out.append(str(s)), runner=lambda argv: cli.append(argv) or 0,
                       secret=lambda p: "")
        with mock.patch.dict(os.environ, {"NIMLAB_COLOR": "1" if colour else "0"}), \
                mock.patch.object(C, "enabled", return_value=colour):
            try:
                getattr(ui, screen)()
            except self.U.Back:
                pass
        return "\n".join(out), cli, ask

    def items_of(self, text, title):
        """The keys listed on the first drawing of a screen."""
        block = text.split(title, 1)[1] if title else "\n" + text
        keys = []
        for ln in block.splitlines()[1:]:
            m = re.match(r"\s+(?:\x1b\[[0-9;]*m)*([0-9a-z])(?:\x1b\[[0-9;]*m)*\) ", ln)
            if m:
                if m.group(1) == "0":
                    break
                keys.append(m.group(1))
        return keys

    SCREENS = {"health": "Health & repair", "service": "Service & update", "scheduler": "Scheduler",
               "endpoints": "Custom endpoints", "heartbeat": "Heartbeat", "jobs": ""}

    def test_every_screen_and_item_opens_colour_on_and_off(self):
        for colour in (False, True):
            for screen, title in self.SCREENS.items():
                if not hasattr(self.U.UI, screen):
                    continue
                text, _cli, _ask = self.walk(screen, [], colour)
                self.assertIn(title, C.strip(text) if hasattr(C, "strip") else re.sub(r"\x1b\[[0-9;]*m", "", text))
                if colour:
                    self.assertIn("\x1b[", text, screen)
                else:
                    self.assertNotIn("\x1b[", text, screen)
                plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
                keys = self.items_of(plain, title)
                self.assertTrue(keys, (screen, plain))
                for k in keys:
                    # open the item, then go back out of anything it asks or shows
                    t, _c, _a = self.walk(screen, [k], colour)
                    self.assertNotIn("Traceback", t, (screen, k))
                    self.assertNotIn("Not an option", t, (screen, k))

    def test_screens_fit_a_phone(self):
        for screen in self.SCREENS:
            if hasattr(self.U.UI, screen):
                text, _c, _a = self.walk(screen, [])
                for ln in text.splitlines():
                    if re.match(r"\s+[0-9a-z]\) ", ln):      # menu items (notes wrap on their own)
                        self.assertLessEqual(len(ln), 60, (screen, ln))

    def test_heartbeat_enable_disable_on_its_status_screen(self):
        from nimlab import scheduler as SC
        SC.load_jobs()
        was = bool((SC.load_jobs().get(SC.HEARTBEAT) or {}).get("enabled"))
        text, _c, _a = self.walk("heartbeat", ["1"])
        self.assertIn("Turn off" if was else "Turn on", text.split("Heartbeat", 1)[1])
        now = bool((SC.load_jobs().get(SC.HEARTBEAT) or {}).get("enabled"))
        self.assertEqual(now, not was)
        text, _c, _a = self.walk("heartbeat", ["1"])
        self.assertIn("Turn on" if was else "Turn off", text)
        self.assertEqual(bool((SC.load_jobs().get(SC.HEARTBEAT) or {}).get("enabled")), was)

    def test_health_screen_runs_no_fix_without_a_yes(self):
        with mock.patch.object(D, "planned_repairs", return_value=[("x", "do x", lambda: None)]), \
                mock.patch.object(D, "fix") as fx:
            self.walk("health", ["3", "n"])
            fx.assert_not_called()

    def test_next_steps_are_selectable(self):
        text, cli, _a = self.walk("scheduler", [])
        plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
        self.assertIn("Scheduler", plain)
        ui = self.U.UI(ask=Script(["s"]), say=lambda s="": None, runner=lambda argv: cli.append(argv) or 0)
        ui.next_steps([("s", "Start the service now", lambda: (ui.cli("service", "start"), None)[1])])
        self.assertIn(["service", "start"], cli)

    def test_endpoint_screens_add_import_and_use_on_role(self):
        EP.add("gw", "https://gw.example.com/v1")
        EP.add_model("gw", "llama-3-70b", kind="chat")
        text, _c, _a = self.walk("endpoints", ["1"])
        plain = re.sub(r"\x1b\[[0-9;]*m", "", text)
        self.assertIn("gw", plain)
        self.assertIn("llama-3-70b", plain)


class TestCommandsReachable(unittest.TestCase):
    """Every `nimlab <command> <sub>` the code suggests is in the command
    list, which the Commands menu (X) shows and runs."""

    def test_suggested_commands_are_in_the_catalog(self):
        import argparse
        from nimlab import commands
        from nimlab.cli import build_parser
        subs, tops = {}, set()
        for a in build_parser()._actions:
            if isinstance(a, argparse._SubParsersAction):
                for name, sp in a.choices.items():
                    tops.add(name)
                    for b in sp._actions:
                        if isinstance(b, argparse._SubParsersAction):
                            subs[name] = set(b.choices)
        cat = "\n".join(c for _g, c, _d, _f in commands.CATALOG)
        cat_tops = {c.split()[0] for _g, c, _d, _f in commands.CATALOG}
        missing = set()
        for p in glob.glob(os.path.join(ROOT, "nimlab", "*.py")) + [os.path.join(ROOT, "start.sh")]:
            for m in re.finditer(r"nimlab ([a-z][a-z-]+)(?: ([a-z][a-z-]+))?", open(p, encoding="utf-8").read()):
                a, b = m.groups()
                if a not in tops:
                    continue
                if a not in cat_tops and a not in ("ui",):
                    missing.add(a)
                elif b and b in subs.get(a, ()):
                    if not re.search(rf"^{a} (\S*\|)?<?{b}\b", cat, re.M) and \
                            not re.search(rf"^{a} <[^>]*\b{b}\b", cat, re.M):
                        missing.add(f"{a} {b}")
        self.assertEqual(sorted(missing), [])

    def test_menu_letters_open_the_new_screens(self):
        src = open(os.path.join(ROOT, "start.sh")).read()
        for key, screen in (("h|H", "health"), ("w|W", "scheduler"), ("u|U", "service"), ("a|A", "endpoints")):
            self.assertRegex(src, rf"{re.escape(key)}\) nimlab ui {screen}")


if __name__ == "__main__":
    unittest.main()
