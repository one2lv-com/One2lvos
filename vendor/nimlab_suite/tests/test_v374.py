"""3.7.4: Commands & troubleshooting, the Tests menu, the VPS platform
support and the fixes from SeVin's 3.7.3 fresh install."""

import io
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests import sandbox  # noqa: E402

from nimlab import commands, hostenv, systests  # noqa: E402
from nimlab import service as SV  # noqa: E402
from nimlab import tunnel  # noqa: E402
from nimlab.cli import build_parser  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = build_parser().parse_args(argv).fn(build_parser().parse_args(argv))
    return code, buf.getvalue()


# ---------------------------------------------------------------------------
# the command catalog
# ---------------------------------------------------------------------------
class CatalogTests(unittest.TestCase):
    def test_every_subcommand_and_action_is_listed(self):
        self.assertEqual(commands.missing(), [])
        # and the parser really has the 25 old subcommands plus the new ones
        subs = {c.split()[0] for c in commands.parser_commands()}
        for name in ("status", "roles", "persist-key", "forget-key", "fleet", "data", "report", "serve", "mcp",
                     "bench", "doctor", "memory", "setup", "service", "telegram", "bugs", "selfadmin", "colors",
                     "shortcut", "discover", "sweep", "tts", "grpc", "judge", "commands", "help", "troubleshoot",
                     "test", "platform"):
            self.assertIn(name, subs)

    def test_every_listed_command_parses(self):
        p = build_parser()
        bad = []
        for _g, cmd, _d, _f in commands.CATALOG:
            try:
                with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                    p.parse_args(commands.sample_argv(cmd))
            except SystemExit:
                bad.append(cmd)
        self.assertEqual(bad, [])

    def test_every_group_known_and_used(self):
        used = {g for g, *_ in commands.CATALOG}
        self.assertEqual(used, set(commands.GROUP_KEYS))
        for g, cmd, desc, flags in commands.CATALOG:
            self.assertTrue(desc and not desc.endswith("."), cmd)
            self.assertTrue(set(flags) <= set("cli"), cmd)

    def test_destructive_commands_ask_first(self):
        flags = {cmd: f for _g, cmd, _d, f in commands.CATALOG}
        for cmd in ("service cleanup", "service stop", "service remove", "forget-key", "mcp delete-key",
                    "memory forget <id>", "memory prune", "bugs clear", "serve regen-key", "selfadmin undo"):
            self.assertIn("c", flags[cmd], cmd)

    def test_symptom_steps_are_real_commands(self):
        have = commands.listed()
        self.assertEqual(len(commands.SYMPTOMS), 11)   # 3.8.0 added 'scheduler'
        for k, title, steps, note in commands.SYMPTOMS:
            self.assertTrue(steps, k)
            for cmd, _why in steps:
                w = commands._words(cmd)
                self.assertTrue(w[0] in have and (len(w) < 2 or f"{w[0]} {w[1]}" in have or w[0] in
                                                  ("memory", "test", "setup")), cmd)  # setup takes a step name
                build_parser().parse_args(commands.sample_argv(cmd))

    def test_cli_commands_and_help_alias(self):
        code, out = run_cli(["commands"])
        self.assertEqual(code, 0)
        for _k, title in commands.GROUPS:
            self.assertIn(f"== {title} ==", out)
        self.assertIn("nimlab service cleanup", out)
        code2, out2 = run_cli(["help"])
        self.assertEqual(out2, out)

    def test_cli_commands_one_area(self):
        code, out = run_cli(["commands", "telegram"])
        self.assertEqual(code, 0)
        self.assertIn("== Telegram ==", out)
        self.assertNotIn("== Memory ==", out)
        code, out = run_cli(["commands", "tunnel"])     # alias -> server and tunnel
        self.assertIn("serve tunnel status", out)
        code, out = run_cli(["commands", "nope"])
        self.assertEqual(code, 2)

    def test_cli_troubleshoot(self):
        code, out = run_cli(["troubleshoot"])
        self.assertEqual(code, 0)
        for _k, title, *_ in commands.SYMPTOMS:
            self.assertIn(title, out)
        code, out = run_cli(["troubleshoot", "tunnel"])
        self.assertIn("nimlab test tunnel", out)
        self.assertNotIn("Memory isn't recalling", out)
        self.assertEqual(run_cli(["troubleshoot", "zzz"])[0], 2)

    def test_readme_section_matches_the_generator(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            text = f.read()
        block = commands.readme_section(text)
        self.assertIsNotNone(block, "README has no generated Command reference")
        self.assertEqual(block.strip(), commands.render_markdown().strip(),
                         "README Command reference is stale: run python3 tools/update_readme_commands.py")
        self.assertIn("## Command reference", text)
        self.assertLess(text.index("(#command-reference)"), 3000, "point to it near the top")
        for t in systests.TESTS:
            self.assertIn(f"`{t.name}`", block)


class MenuTests(unittest.TestCase):
    def feed(self, answers):
        it = iter(answers)
        return lambda prompt="": next(it)

    def test_menu_runs_an_entry_and_returns_to_the_list(self):
        ran, said = [], []
        g = commands.GROUP_KEYS.index("mcp") + 1
        idx = [c for _g, c, _d, _f in commands.entries("mcp")].index("mcp test") + 1
        commands.menu(ask=self.feed([str(g), str(idx), "", "b", "b"]), say=said.append,
                      runner=lambda argv: ran.append(argv) or 0)
        self.assertEqual(ran, [["mcp", "test"]])
        self.assertTrue(any("$ nimlab mcp test" in s for s in said))
        # back at the list after running (3.8.1: the title is a colors.py header, plain 'MCP' without colour)
        self.assertEqual(sum(1 for s in said if s == "MCP"), 2)

    def test_destructive_entry_asks_and_no_means_not_run(self):
        ran, said = [], []
        code = commands.run_entry("service cleanup", "c", self.feed(["n"]), said.append,
                                  runner=lambda a: ran.append(a) or 0)
        self.assertIsNone(code)
        self.assertEqual(ran, [])
        code = commands.run_entry("service cleanup", "c", self.feed(["y"]), said.append,
                                  runner=lambda a: ran.append(a) or 0)
        self.assertEqual(ran, [["service", "cleanup"]])

    def test_argument_prompts(self):
        ran = []
        commands.run_entry("memory recall <query>", "", self.feed(["my cat"]), lambda s: None,
                           runner=lambda a: ran.append(a) or 0)
        self.assertEqual(ran, [["memory", "recall", "my cat"]])
        ran.clear()
        commands.run_entry("memory recall <query>", "", self.feed([""]), lambda s: None,
                           runner=lambda a: ran.append(a) or 0)
        self.assertEqual(ran, [])            # a required argument left empty cancels
        commands.run_entry("telegram refusal [<text>]", "", self.feed([""]), lambda s: None,
                           runner=lambda a: ran.append(a) or 0)
        self.assertEqual(ran, [["telegram", "refusal"]])

    def test_symptom_run_all_asks_before_each(self):
        ran = []
        n = commands.SYMPTOM_KEYS.index("stray-copies") + 1
        # a = run all: yes to status, skip cleanup, quit at restart
        commands.symptoms_menu(self.feed([str(n), "a", "y", "n", "q", "", "b", "b"]), lambda s: None,
                               runner=lambda a: ran.append(a) or 0)
        self.assertEqual(ran, [["service", "status"]])

    def test_start_sh_has_both_menu_options(self):
        with open(os.path.join(ROOT, "start.sh"), encoding="utf-8") as f:
            sh = f.read()
        self.assertIn('"Commands & troubleshooting"', sh)
        self.assertIn('"Tests"', sh)
        self.assertIn("nimlab commands --menu", sh)
        self.assertIn("nimlab test --menu", sh)


# ---------------------------------------------------------------------------
# the tunnel test
# ---------------------------------------------------------------------------
class TunnelTestTests(sandbox.SandboxCase if hasattr(sandbox, "SandboxCase") else unittest.TestCase):
    SRV = {"api_key": "sk-local-SECRET-123", "model_name": "quill", "tunnel": {"mode": "quick"}}
    ST = {"state": "up", "mode": "quick", "url": "https://abc.trycloudflare.com", "pid": os.getpid()}

    def run_with(self, http, chat=False):
        return commands.tunnel_test(chat=chat, http=http, srv=self.SRV, st=self.ST)

    def test_200_reports_the_model_and_never_prints_the_key(self):
        seen = []

        def http(url, key, body=None, timeout=20):
            seen.append((url, key))
            return 200, json.dumps({"data": [{"id": "quill"}]})
        r = self.run_with(http)
        self.assertTrue(r["ok"])
        self.assertEqual(r["model"], "quill")
        self.assertEqual(seen, [("https://abc.trycloudflare.com/v1/models", "sk-local-SECRET-123")])
        self.assertNotIn("SECRET", "\n".join(commands.tunnel_lines(r)))

    def test_401_530_1033_and_dns(self):
        r = self.run_with(lambda *a, **k: (401, "{}"))
        self.assertIn("rejected the key", r["verdict"])
        r = self.run_with(lambda *a, **k: (530, "error code: 1033"))
        self.assertIn("tunnel is down or the URL is stale", r["verdict"])
        r = self.run_with(lambda *a, **k: (404, "Error 1033 Argo Tunnel error"))
        self.assertIn("1033", r["verdict"])

        def dns(*a, **k):
            raise urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))
        r = self.run_with(dns)
        self.assertEqual(r["status"], "DNS")
        self.assertIn("stale", r["verdict"])

    def test_no_url(self):
        r = commands.tunnel_test(http=lambda *a: (200, ""), srv={"tunnel": {"mode": "off"}}, st={})
        self.assertFalse(r["ok"])
        self.assertIn("No tunnel URL", r["verdict"])

    def test_optional_chat(self):
        def http(url, key, body=None, timeout=20):
            if body is None:
                return 200, json.dumps({"data": [{"id": "quill"}]})
            self.assertEqual(body["model"], "quill")
            return 200, json.dumps({"choices": [{"message": {"content": "pong"}}]})
        r = self.run_with(http, chat=True)
        self.assertTrue(r["chat"]["ok"])
        self.assertEqual(r["chat"]["reply"], "pong")


# ---------------------------------------------------------------------------
# the Tests menu
# ---------------------------------------------------------------------------
class R:
    def __init__(self, ok=True, error="", text="", data=None, latency=0.1):
        self.ok, self.error, self.text, self.data, self.latency = ok, error, text, data, latency


class FakeMem:
    settings = {"backend": "local"}


class FakeMCP:
    def __init__(self, tools=None, fail=False):
        self.tools = tools if tools is not None else [{"name": "whoami"}, {"name": "delete_file"}]
        self.fail = fail
        self.called = []

    def list_tools(self):
        if self.fail:
            raise RuntimeError("401 Unauthorized")
        return self.tools

    def call_tool(self, name, args):
        self.called.append(name)
        return {"ok": True}


class FakeCtx:
    """Every Live method, healthy."""
    def __init__(self, **over):
        self.mcp_client = FakeMCP()
        for name, v in over.items():          # instance attributes win over the healthy methods
            setattr(self, name, v if callable(v) else (lambda *a, _v=v, **k: _v))

    def host_checks(self):
        return [("info", "Ubuntu", ""), ("ok", "Python 3.12", "")]

    def key(self):
        return "nvapi-test-abcd"

    def list_models(self):
        return R(data={"data": [{"id": "a"}, {"id": "b"}]})

    def roles_set(self):
        return ["router", "persona"]

    def role_ping(self, role):
        return R()

    def grpc_rows(self):
        return [(True, "riva-asr: ok (0.3s)")], ""

    def is_set(self, role):
        return True

    def tts(self):
        return "/tmp/x.wav", R()

    def asr(self):
        return R(text="")

    def embed(self):
        return [0.1] * 8

    def memory(self):
        return FakeMem()

    def memory_backend_rows(self):
        return [(True, "connected: local")]

    def memory_roundtrip(self):
        return [(True, "stored test memory"), (True, "recalled it by vector"), (True, "removed the test memory")]

    def mcp(self):
        return self.mcp_client

    def server_rows(self):
        return [("identity", "PASS", ""), ("chat", "PASS", "")]

    def tunnel(self, chat=False):
        return {"ok": True, "verdict": "200: the tunnel reaches the server; model quill.", "url": "https://x"}

    def tunnel_mode(self):
        return "quick"

    def telegram(self):
        return {"token": True, "owner": 42, "pollers": [(1, "telegram", "x")], "me": {"username": "quillbot"},
                "error": None}

    def service(self):
        return {"holder": 99, "children": ["serve", "telegram"], "want": ["serve", "telegram"], "strays": [],
                "installed": True, "backend": "termux"}

    def scheduler(self):                     # 3.8.0
        return {"jobs": {"heartbeat": {"name": "heartbeat", "schedule": "FREQ=MINUTELY;INTERVAL=30",
                                       "enabled": True, "state": {}}}, "holder": 99}

    def selfadmin(self):
        return {"enabled": True, "shell": False, "key": True, "dir": tempfile.gettempdir()}

    def bug_dir(self):
        return tempfile.gettempdir(), True

    def config_problems(self):
        return []

    def route(self, text):
        return {"role": "reasoning", "via": "router", "router_ok": True}


class SysTestsTests(unittest.TestCase):
    REQUIRED = ["platform", "key", "catalog", "roles", "grpc", "tts", "asr", "embeddings", "memory-backend",
                "memory-write", "memory-recall", "mcp", "server", "tunnel", "telegram", "service", "scheduler", "selfadmin",
                "buglog", "config", "router"]

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = mock.patch.object(systests, "history_path", lambda: os.path.join(self.tmp, "h.jsonl"))
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_every_required_test_is_registered(self):
        self.assertEqual([t.name for t in systests.TESTS], self.REQUIRED)
        for t in systests.TESTS:
            self.assertTrue(callable(t.fn) and t.title)
            if t.symptom:
                self.assertIn(t.symptom, commands.SYMPTOM_KEYS)
            self.assertTrue(hasattr(systests.Live, "key"))
        live = {t.name for t in systests.TESTS if t.live}
        self.assertTrue({"catalog", "roles", "router", "memory-recall", "tts", "asr"} <= live)
        self.assertFalse({"key", "config", "buglog", "service", "platform"} & live)

    def test_live_context_has_every_method_the_fake_has(self):
        for name in dir(FakeCtx):
            if not name.startswith("_"):
                self.assertTrue(hasattr(systests.Live, name), name)

    def test_every_test_passes_against_healthy_fakes(self):
        ctx = FakeCtx()
        for t in systests.TESTS:
            r = systests.run_one(t, ctx, record_bug=False)
            self.assertEqual(r.status, systests.PASS, f"{t.name}: {r.detail}")
            self.assertIsInstance(r.ms, int)
        self.assertEqual(ctx.mcp_client.called, ["whoami"])     # one harmless call, never delete_file

    def test_skips_say_why_and_how_to_enable(self):
        ctx = FakeCtx(key=None, mcp=None, tunnel_mode="off",
                      tunnel={"ok": False, "url": "", "verdict": "No tunnel URL"},
                      telegram={"token": False}, selfadmin={"enabled": False},
                      memory_backend_rows=None)
        for name in ("catalog", "roles", "router", "mcp", "tunnel", "telegram", "selfadmin", "memory-backend"):
            r = systests.run_one(systests.BY_NAME[name], ctx, record_bug=False)
            self.assertEqual(r.status, systests.SKIP, name)
            self.assertTrue(r.detail and r.fix, name)

    def test_failures_get_a_bug_id_and_next_step(self):
        ctx = FakeCtx(telegram={"token": True, "owner": 42, "me": {"username": "b"}, "error": None,
                                "pollers": [(1, "telegram", ""), (2, "telegram", "")]})
        with mock.patch("nimlab.bugs.record", return_value="B-1234") as rec:
            r = systests.run_one(systests.BY_NAME["telegram"], ctx)
        self.assertEqual(r.status, systests.FAIL)
        self.assertIn("2 pollers", r.detail)
        self.assertEqual(r.bug, "B-1234")
        self.assertIn("service cleanup", r.fix)
        self.assertIn("nimlab troubleshoot telegram-twice", r.fix)
        rec.assert_called_once()
        text = "\n".join(systests.result_lines(systests.BY_NAME["telegram"], r))
        self.assertIn("bug ID: B-1234", text)

    def test_service_test_catches_strays_and_missing_children(self):
        ctx = FakeCtx(service={"holder": 9, "children": ["serve"], "want": ["serve", "telegram"],
                               "strays": [(5, "supervisor", "x")], "installed": True, "backend": "termux"})
        r = systests.run_one(systests.BY_NAME["service"], ctx, record_bug=False)
        self.assertEqual(r.status, systests.FAIL)
        self.assertIn("the config wants serve, telegram", r.detail)
        self.assertEqual(sum(1 for a, _m in r.rows if not a), 2)

    def test_mcp_failure_and_broken_test(self):
        c = FakeCtx()
        c.mcp_client = FakeMCP(fail=True)
        r = systests.run_one(systests.BY_NAME["mcp"], c, record_bug=False)
        self.assertEqual(r.status, systests.FAIL)
        self.assertIn("401", r.detail)

        def boom():
            raise ValueError("kaput")
        r = systests.run_one(systests.BY_NAME["config"], FakeCtx(config_problems=boom), record_bug=False)
        self.assertEqual(r.status, systests.FAIL)
        self.assertIn("the test broke: ValueError", r.detail)

    def test_run_all_table_and_history(self):
        out = []
        with mock.patch("nimlab.bugs.record", return_value="B-9"):
            res = systests.run_all(FakeCtx(config_problems=["speech URL is a homepage"]), out.append)
        self.assertEqual(len(res), len(systests.TESTS))
        self.assertIn(f"{len(systests.TESTS) - 1} passed, 1 failed, 0 skipped", out)
        hist = systests.load_history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["results"]["config"]["status"], "fail")
        self.assertEqual(hist[0]["results"]["config"]["bug"], "B-9")
        self.assertIn("1 failed", systests.history_lines()[0])

    def test_cli_list_and_unknown(self):
        code, out = run_cli(["test"])
        self.assertEqual(code, 0)
        for t in systests.TESTS:
            self.assertIn(t.name, out)
        self.assertEqual(run_cli(["test", "nope"])[0], 2)
        self.assertIs(systests.find("recall"), systests.BY_NAME["memory-recall"])

    def test_cli_runs_one(self):
        with mock.patch.object(systests, "Live", FakeCtx):
            code, out = run_cli(["test", "key"])
        self.assertEqual(code, 0)
        self.assertIn("[PASS] key", out)
        self.assertEqual(len(systests.load_history()), 1)

    def test_menu(self):
        said = []
        answers = iter(["2", "", "a", "", "b"])
        systests.menu(lambda p="": next(answers), said.append, ctx=FakeCtx())
        self.assertTrue(any(s.startswith("[PASS] key") for s in said))
        self.assertTrue(any("passed, 0 failed" in s for s in said))


# ---------------------------------------------------------------------------
# 3.7.3 fresh-install fixes
# ---------------------------------------------------------------------------
class SupervisorFixTests(sandbox.SandboxCase if hasattr(sandbox, "SandboxCase") else unittest.TestCase):
    def test_supervisor_picks_up_a_newly_configured_child(self):
        want = {"serve": ["serve"]}
        mtime = [1.0]
        started = []

        class P:
            def __init__(self, name):
                self.name = name
                self.pid = 4242
                self.stdout = io.StringIO("")

            def poll(self):
                return None

            def terminate(self):
                started.append("stop " + self.name)

            def wait(self, timeout=None):
                return 0
        def popen(cmd, **_kw):
            name = cmd[0]                    # the fake commands are [name]
            started.append(name)
            return P(name)
        sup = SV.Supervisor(commands_fn=lambda: dict(want), config_mtime=lambda: mtime[0], popen=popen)
        sup.step()
        self.assertEqual(sorted(sup.cmds), ["serve"])
        want["telegram"] = ["telegram"]      # setup's Telegram step ran after the service step
        mtime[0] = 2.0
        sup.step()
        self.assertIn("telegram", sup.cmds)
        self.assertIn("telegram", started)
        self.assertIn("telegram is now configured", SV.log_tail())
        del want["telegram"]
        mtime[0] = 3.0
        sup.step()
        self.assertNotIn("telegram", sup.cmds)
        self.assertIn("stop telegram", started)

    def test_fixed_cmds_do_not_follow_the_config(self):
        sup = SV.Supervisor(cmds={"serve": ["x"]}, config_mtime=lambda: 5.0)
        self.assertEqual(sup.reconcile(), ([], []))

    def test_lock_loser_exits_under_runit_after_backoff(self):
        a = SV.SupervisorLock()
        self.assertTrue(a.acquire())
        try:
            waits = []
            with mock.patch.object(SV, "under_runit", return_value=True), \
                    mock.patch.object(SV, "LOCK_BACKOFF", 3):
                code = SV.supervise(lock=SV.SupervisorLock(), wait=lambda s: waits.append(s))
            self.assertEqual(code, 0)
            self.assertEqual(len(waits), SV.LOCK_GRACE + 3)    # slow respawn, not a tight loop
            self.assertEqual(SV.log_tail().count("another Nim Lab supervisor already runs"), 1)
        finally:
            a.release()

    def test_lock_loser_line_is_logged_once_an_hour(self):
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        env = mock.patch.dict(os.environ, {"NIMLAB_DATA_DIR": d})
        env.start()
        self.addCleanup(env.stop)
        self.assertFalse(SV._told_recently(clock=lambda: 1000.0))
        self.assertTrue(SV._told_recently(clock=lambda: 1500.0))
        self.assertFalse(SV._told_recently(clock=lambda: 1000.0 + 3700))

    def test_under_runit(self):
        self.assertTrue(SV.under_runit(env={"NIMLAB_RUNIT": "1"}))
        self.assertFalse(SV.under_runit(env={}, ppid=os.getpid()))

    def test_runit_run_file_marks_runit_and_start_sh_execs(self):
        files = SV.runit_files({"HOME": "/h", "PREFIX": "/data/data/com.termux/files/usr"}) \
            if hasattr(SV, "runit_files") else None
        src = open(os.path.join(ROOT, "nimlab", "service.py"), encoding="utf-8").read()
        self.assertIn("export NIMLAB_RUNIT=1", src)
        if files:
            self.assertIn("NIMLAB_RUNIT=1", files["run"])
        sh = open(os.path.join(ROOT, "start.sh"), encoding="utf-8").read()
        self.assertIn('exec "$PY" -m nimlab "$@"', sh)

    def test_termux_install_skips_when_already_running(self):
        calls = []

        def run(argv):
            a = tuple(argv)                  # Manager._run takes one list
            calls.append(" ".join(a))
            return (0, "run: nimlab: (pid 7) 100s") if a[:2] == ("sv", "status") else (0, "")
        m = SV.Manager(env={"PREFIX": os.path.join(self.tmp if hasattr(self, "tmp") else tempfile.mkdtemp(),
                                                  "com.termux", "usr"), "HOME": tempfile.mkdtemp(),
                            "TERMUX_VERSION": "0.118"}, run=run, which=lambda n: "/x/" + n)
        if m.backend != "termux":
            self.skipTest("termux-services not detected in this sandbox")
        ok_, lines = m.install()
        self.assertTrue(ok_)
        self.assertNotIn("sv-enable nimlab", calls)
        self.assertIn("Already enabled and running", "\n".join(lines))


class TunnelDescribeTests(unittest.TestCase):
    def test_states(self):
        me = os.getpid()
        self.assertEqual(tunnel.describe({"mode": "off"}, {}), "off")
        self.assertEqual(tunnel.describe({"mode": "quick"}, {"state": "up", "mode": "quick", "pid": me,
                                                           "url": "https://a.trycloudflare.com"}),
                         "quick, running https://a.trycloudflare.com")
        # the phone's case: settings said off, but a quick tunnel was running and reachable
        s = tunnel.describe({"mode": "off"}, {"state": "up", "mode": "quick", "pid": me,
                                              "url": "https://a.trycloudflare.com"})
        self.assertIn("quick tunnel is running: https://a.trycloudflare.com", s)
        self.assertEqual(tunnel.describe({"mode": "named"}, {}), "named, not running")
        self.assertEqual(tunnel.describe({"mode": "quick"}, {"state": "up", "mode": "quick", "pid": 2 ** 22 + 7}),
                         "quick, stopped")

    def test_setup_summary_uses_it(self):
        src = open(os.path.join(ROOT, "nimlab", "wizard.py"), encoding="utf-8").read()
        self.assertIn("tunnel {tunnel.describe(t)}", src)
        self.assertNotIn("tunnel {t['mode']}", src)


class McpAuthSummaryTests(unittest.TestCase):
    def test_saved_style_forms(self):
        from nimlab import mcpmenu
        self.assertEqual(mcpmenu.saved_style({"auth": {"style": "bearer"}}), ("bearer", "X-API-Key"))
        self.assertEqual(mcpmenu.saved_style({"auth": "Bearer"})[0], "bearer")
        self.assertEqual(mcpmenu.saved_style({"auth_style": "bearer"})[0], "bearer")
        self.assertEqual(mcpmenu.saved_style({"auth": {"style": "header", "header_name": "X-K"}}),
                         ("header", "X-K"))
        self.assertEqual(mcpmenu.saved_style({})[0], "x-api-key")

    def test_summary_ignores_a_stale_cached_result(self):
        from nimlab import wizard
        src = open(wizard.__file__, encoding="utf-8").read()
        self.assertIn("ok, text, level = self._status3(st)\n            r = self.results.get(key)", src)


# ---------------------------------------------------------------------------
# platforms
# ---------------------------------------------------------------------------
UBUNTU = 'PRETTY_NAME="Ubuntu 24.04.1 LTS"\nNAME="Ubuntu"\nID=ubuntu\nID_LIKE=debian\n'
OL = 'NAME="Oracle Linux Server"\nID="ol"\nID_LIKE="fedora"\nPRETTY_NAME="Oracle Linux Server 9.4"\n'
MEM_1G = "MemTotal:         981234 kB\nSwapTotal:             0 kB\n"
MEM_1G_SWAP = "MemTotal:         981234 kB\nSwapTotal:       2097148 kB\n"
MEM_8G = "MemTotal:        8000000 kB\nSwapTotal:             0 kB\n"


def detect(osr, mem, env=None, which=None, linger=False, euid=1000, pep668=False, venv=False, cpus=2):
    tools = which or {"apt-get", "systemctl", "loginctl"}
    return hostenv.detect(env=env or {"USER": "ubuntu"}, os_release=osr, meminfo=mem,
                          which=lambda n: f"/usr/bin/{n}" if n in tools else None,
                          exists=lambda p: p == "/run/systemd/system" or (linger and "linger" in p),
                          euid=euid, run=lambda *a, **k: subprocess.CompletedProcess(a, 1, "", ""),
                          cpu_count=cpus, machine="x86_64", py_version="3.12.3", pep668=pep668, venv=venv)


class PlatformTests(unittest.TestCase):
    def test_ubuntu_pep668_micro_vps(self):
        i = detect(UBUNTU, MEM_1G, pep668=True)
        self.assertEqual((i["os_id"], i["pkg"], i["family"]), ("ubuntu", "apt", "debian"))
        self.assertFalse(i["termux"])
        self.assertTrue(hostenv.low_memory(i))
        rows = hostenv.checks(i)
        text = "\n".join(f"{lv} {m} {f}" for lv, m, f in rows)
        self.assertIn("externally managed (PEP 668)", text)
        self.assertIn("python3-venv", text)
        self.assertIn("sudo apt-get install -y ffmpeg", text)
        self.assertIn("pkg.cloudflare.com/cloudflared any main", text)
        self.assertIn("loginctl enable-linger ubuntu", text)
        self.assertIn("fallocate -l 2G /swapfile", text)
        self.assertIn("terminal voice call and the battery settings are off", text)
        self.assertNotIn("break-system-packages", text)

    def test_oracle_linux(self):
        i = detect(OL, MEM_1G_SWAP, which={"dnf", "systemctl"}, linger=True)
        self.assertEqual((i["os_id"], i["pkg"], i["family"]), ("ol", "dnf", "rhel"))
        self.assertFalse(hostenv.low_memory(i))
        self.assertIn("EPEL", hostenv.install_hint("ffmpeg", i))
        self.assertIn("cloudflared.repo", hostenv.install_hint("cloudflared", i))
        self.assertIn("dnf", hostenv.install_hint("venv", i))
        text = "\n".join(m for _lv, m, _f in hostenv.checks(i))
        self.assertIn("linger is on", text)

    def test_termux(self):
        i = detect("", MEM_8G, env={"TERMUX_VERSION": "0.118", "PREFIX": "/data/data/com.termux/files/usr"},
                   which={"ffmpeg", "termux-microphone-record"})
        self.assertEqual((i["os_id"], i["pkg"]), ("termux", "pkg"))
        self.assertFalse(i["systemd"])
        self.assertEqual(hostenv.install_hint("ffmpeg", i), "pkg install ffmpeg")
        text = "\n".join(m for _lv, m, _f in hostenv.checks(i))
        self.assertIn("Termux:API found", text)
        self.assertNotIn("linger", text)

    def test_root_warning(self):
        i = detect(UBUNTU, MEM_8G, euid=0)
        self.assertTrue(i["root"])
        self.assertTrue(any("Running as root" in m for _lv, m, _f in hostenv.checks(i)))

    def test_workers_scale_to_the_box(self):
        self.assertEqual(hostenv.workers(3, detect(UBUNTU, MEM_1G, cpus=2)), 2)
        self.assertEqual(hostenv.workers(3, detect(UBUNTU, "MemTotal: 600000 kB\n", cpus=2)), 1)
        self.assertEqual(hostenv.workers(3, detect(UBUNTU, MEM_8G, cpus=4)), 3)
        self.assertEqual(hostenv.workers(8, detect(UBUNTU, MEM_8G, cpus=1)), 2)

    def test_externally_managed_marker(self):
        d = tempfile.mkdtemp()
        self.assertFalse(hostenv.externally_managed(stdlib=d, prefix="/usr", base_prefix="/usr"))
        open(os.path.join(d, "EXTERNALLY-MANAGED"), "w").close()
        self.assertTrue(hostenv.externally_managed(stdlib=d, prefix="/usr", base_prefix="/usr"))
        self.assertFalse(hostenv.externally_managed(stdlib=d, prefix="/venv", base_prefix="/usr"))

    def test_voice_call_off_termux(self):
        from nimlab import voicecall
        self.assertFalse(voicecall.on_termux({}))
        self.assertTrue(voicecall.on_termux({"TERMUX_VERSION": "1"}))
        out = []
        with mock.patch.object(voicecall, "on_termux", return_value=False):
            self.assertEqual(voicecall.run_call(None, out=out.append), 0)
        self.assertIn("needs Termux", "".join(out))

    def test_wake_lock_only_on_termux(self):
        with mock.patch.object(SV, "is_termux", return_value=False):
            src = open(SV.__file__, encoding="utf-8").read()
            self.assertIn('sv.setdefault("wake_lock", is_termux())', src)

    def test_doctor_has_platform_section(self):
        from nimlab import doctor
        rows = doctor.platform_checks(info=detect(UBUNTU, MEM_1G, pep668=True))
        self.assertTrue(any(ok == "warn" and "swap" in m for ok, m in rows))
        self.assertFalse(any(ok is False for ok, m in rows))   # warnings never fail the doctor

    def test_system_unit_runs_as_the_sudo_user(self):
        text = SV.system_unit("ubuntu", {"HOME": "/home/ubuntu"})
        self.assertIn("User=ubuntu", text)
        self.assertIn("WantedBy=multi-user.target", text)
        with mock.patch.object(SV, "_euid", return_value=1000):
            ok_, lines = SV.install_system(lambda *a: (0, ""), {"SUDO_USER": "ubuntu"})
        self.assertFalse(ok_)
        with mock.patch.object(SV, "_euid", return_value=0):
            ok_, lines = SV.install_system(lambda *a: (0, ""), {"SUDO_USER": "root"})
        self.assertFalse(ok_)
            # never as root
        p = os.path.join(tempfile.mkdtemp(), "nimlab.service")
        calls = []
        with mock.patch.object(SV, "_euid", return_value=0):
            ok_, lines = SV.install_system(lambda *a: calls.append(a) or (0, ""), {"SUDO_USER": "ubuntu",
                                                                                   "HOME": "/root"}, path=p)
        self.assertTrue(ok_)
        self.assertIn(("systemctl", "enable", "--now", "nimlab"), calls)
        self.assertIn("User=ubuntu", open(p).read())


class StartShVenvTests(unittest.TestCase):
    """start.sh install on a PEP 668 system: pip refuses, a venv is made and
    used; --break-system-packages is never passed."""

    def test_pep668_makes_and_uses_a_venv(self):
        if not os.path.exists("/bin/bash"):
            self.skipTest("no bash")
        d = tempfile.mkdtemp()
        proj = os.path.join(d, "lab")
        os.makedirs(proj)
        for f in ("start.sh", "requirements.txt"):
            with open(os.path.join(ROOT, f), encoding="utf-8") as a, open(os.path.join(proj, f), "w") as b:
                b.write(a.read())
        bindir = os.path.join(d, "bin")
        os.makedirs(bindir)
        log = os.path.join(d, "calls.log")
        fake_venv_py = ("#!/bin/bash\necho \"venv $*\" >> " + log + "\nexit 0\n")
        fake = ("#!/bin/bash\necho \"system $*\" >> " + log + "\n"
                "if [ \"$1 $2\" = \"-m venv\" ]; then mkdir -p \"$3/bin\"; cat > \"$3/bin/python\" <<'EOF'\n"
                + fake_venv_py + "EOF\nchmod +x \"$3/bin/python\"; exit 0; fi\n"
                "if [ \"$1 $2 $3\" = \"-m pip install\" ]; then echo 'error: externally-managed-environment' >&2; "
                "exit 1; fi\nexit 0\n")
        p = os.path.join(bindir, "python3")
        with open(p, "w") as f:
            f.write(fake)
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        env = {"PATH": bindir + ":/usr/bin:/bin", "HOME": d, "TERM": "dumb", "NO_COLOR": "1"}
        r = subprocess.run(["bash", os.path.join(proj, "start.sh"), "install"], env=env, capture_output=True,
                           text=True, timeout=60)
        out = r.stdout + r.stderr
        calls = open(log).read()
        self.assertIn("system -m venv " + os.path.join(proj, ".venv"), calls)
        self.assertIn("venv -m pip install --prefer-binary --upgrade -r", calls)
        self.assertIn("venv ready", out)
        self.assertNotIn("break-system-packages", calls + out)
        # next run picks the venv's python without being told
        open(log, "w").close()
        subprocess.run(["bash", os.path.join(proj, "start.sh"), "status", "key"], env=env, capture_output=True,
                       text=True, timeout=60)
        self.assertIn("venv -m nimlab status key", open(log).read())


class VersionTests(unittest.TestCase):
    def test_version_is_374(self):
        from nimlab import __version__
        self.assertEqual(__version__, "3.8.6")
        self.assertIn("## v3.7.4", open(os.path.join(ROOT, "CHANGES.md"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
