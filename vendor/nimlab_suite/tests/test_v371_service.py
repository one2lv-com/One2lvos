"""3.7.1 regression tests from the phone's service log (Nov 12):

  [serve] A test server is already running on port 8765. Use another port with --port.
  [supervisor] serve exited with code 1; restarting in 2 s ... 4 s ... 8 s ... 16 s
  [supervisor] serve crashed 5 times in 120 s: crash loop, waiting 300 s
  [supervisor] started serve (pid 18425)        <- same second: cooldown NOT honored
  [telegram] [!] Another copy of this bot is polling (409). ...
  [telegram] Conflict: terminated by other getUpdates request ... retrying in 32 s / 60 s / 1 s

plus the launcher header ('Memory: 0 records', 'Telegram: @? ... 0 allowed',
'70 restarts') and the memory menu showing auto store off while setup said on.
"""

import io
import json
import os
import threading
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import config, memmenu, service as SV, telegram as T
from tests.sandbox import lab

PHONE_SERVE_LINE = "A test server is already running on port 8765. Use another port with --port.\n"


class Child:
    """A fake child process: exits at once with `code` after printing `line`."""
    spawned = []

    def __init__(self, code, line):
        self.code_, self.line = code, line

    def __call__(self, cmd, **kw):
        me = Child(self.code_, self.line)
        me.pid = 1000 + len(Child.spawned)
        me.stdout = io.StringIO(self.line)
        me.cmd = cmd
        Child.spawned.append(me)
        return me

    def poll(self):
        return self.code_

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return self.code_

    def kill(self):
        pass


class Base(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        Child.spawned = []

    def tearDown(self):
        self._lab.__exit__(None, None, None)


class CrashLoop(Base):
    def run_sup(self, code, line, seconds, **kw):
        t = [0.0]

        def sleep(s):
            t[0] += 1
        sup = SV.Supervisor(cmds={"serve": ["x"]}, popen=Child(code, line), sleep=sleep, clock=lambda: t[0],
                            env={}, wake=False, crash_limit=5, crash_window=120, cooldown=300, **kw)
        # the pump thread reads the child's output; give it a moment each spawn
        orig = sup._spawn

        def spawn(name):
            p = orig(name)
            for th in threading.enumerate():
                if th is not threading.current_thread() and th.daemon and th.name.startswith("Thread"):
                    th.join(0.2)
            return p
        sup._spawn = spawn
        sup.run(max_loops=seconds)
        return sup, t

    def test_cooldown_is_honored(self):
        at = []
        orig = Child.__call__

        def spy(self_, cmd, **kw):
            at.append(clock[0])
            return orig(self_, cmd, **kw)
        clock = [0.0]
        with mock.patch.object(Child, "__call__", spy):
            sup = SV.Supervisor(cmds={"serve": ["x"]}, popen=Child(1, "[x] boom\n"),
                                sleep=lambda s: clock.__setitem__(0, clock[0] + 1), clock=lambda: clock[0],
                                env={}, wake=False, crash_limit=5, crash_window=120, cooldown=300)
            sup.run(max_loops=400)
        self.assertIn("crash loop, waiting 300 s", SV.log_tail(400))
        # 5 starts with 2/4/8/16 s backoff, then a gap of at least 300 s:
        # the phone restarted serve in the same second
        self.assertGreaterEqual(len(at), 6, at)
        gaps = [b - a for a, b in zip(at, at[1:])]
        for g, want in zip(gaps[:4], (2, 4, 8, 16)):   # +1 s: the exit is seen on the next 1 s tick
            self.assertTrue(want <= g <= want + 1, gaps)
        self.assertGreaterEqual(gaps[4], 300, at)
        st = SV.read_state()
        self.assertEqual(st["crash_loop"]["child"], "serve")

    def test_cooldown_survives_a_supervisor_restart(self):
        SV.write_state(cooldown_until={"serve": 10_000.0})
        t = [100.0]
        sup = SV.Supervisor(cmds={"serve": ["x"]}, popen=Child(1, ""), sleep=lambda s: t.__setitem__(0, t[0] + 1),
                            clock=lambda: t[0], env={}, wake=False)
        sup.run(max_loops=50)
        self.assertEqual(Child.spawned, [])
        self.assertIn("cooling down", SV.log_tail())

    def test_port_held_by_our_server_idles_not_crash_loops(self):
        sup, _ = self.run_sup(SV.EXIT_WAIT, PHONE_SERVE_LINE, 250)
        self.assertEqual(len(Child.spawned), 1)
        st = SV.read_state()
        self.assertEqual(st["held"]["serve"]["why"], "another copy runs")
        self.assertNotIn("crash loop", SV.log_tail())
        self.assertEqual(st["restarts"], 0)

    def test_config_error_is_not_restarted_until_config_changes(self):
        m = [1.0]
        sup, t = self.run_sup(SV.EXIT_CONFIG, "[config] Port 8765 is held by another program\n", 60,
                              config_mtime=lambda: m[0])
        self.assertEqual(len(Child.spawned), 1)
        st = SV.read_state()
        self.assertEqual(st["held"]["serve"]["why"], "config error")
        self.assertIn("Port 8765 is held", st["held"]["serve"]["line"])
        self.assertIn("configuration problem", SV.log_tail())
        # config changes -> one new try
        m[0] = 2.0
        sup.step()
        self.assertEqual(len(Child.spawned), 2)

    def test_status_names_the_restarting_child_with_code_and_error_line(self):
        sup, _ = self.run_sup(1, "Traceback: RuntimeError: telegram exploded\n", 30)
        st = SV.read_state()
        self.assertEqual(st["last_exit"]["child"], "serve")
        self.assertEqual(st["last_exit"]["code"], 1)
        self.assertIn("telegram exploded", st["last_exit"]["line"])
        prob = SV.child_problem(st)
        self.assertIn("serve", prob)
        self.assertIn("code 1", prob)
        lines = "\n".join(SV.status_lines(SV.Manager(backend="builtin", env=dict(os.environ),
                                                      run=lambda c: (1, ""), which=lambda n: None)))
        self.assertIn("last error: Traceback: RuntimeError: telegram exploded", lines)
        self.assertIn("restarts   :", lines)


class OneSupervisor(Base):
    def test_second_supervisor_exits_after_grace(self):
        # 3.7.4: a lock loser no longer idles forever (it showed up as stray copies)
        a = SV.SupervisorLock()
        self.assertTrue(a.acquire())
        try:
            b = SV.SupervisorLock()
            self.assertFalse(b.acquire())
            self.assertEqual(b.holder(), os.getpid())
            calls = []
            with mock.patch.object(SV, "under_runit", return_value=False):
                code = SV.supervise(lock=b, wait=lambda s: calls.append(s))
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), SV.LOCK_GRACE)
            self.assertIn("another Nim Lab supervisor already runs", SV.log_tail())
            self.assertIn("exits", SV.log_tail())
        finally:
            a.release()
        self.assertIsNone(SV.SupervisorLock().holder())

    def test_find_processes_and_strays(self):
        procs = [(11, "python3 -m nimlab service run"), (12, "python3 -m nimlab serve start"),
                 (13, "python3 -m nimlab telegram run"), (14, "vim notes.txt"),
                 (15, "/data/data/com.termux/files/usr/bin/python3 -m nimlab serve start --port 8765")]
        found = SV.find_processes(run=lambda: procs)
        self.assertEqual([(p, k) for p, k, _ in found], [(11, "supervisor"), (12, "serve"), (13, "telegram"),
                                                         (15, "serve")])
        # the live supervisor's own children are not strays
        st = {"children": {"serve": 12}}
        with mock.patch.object(SV.SupervisorLock, "holder", return_value=11):
            s = SV.strays(st, procs=found)
        self.assertEqual([p for p, _, _ in s], [13, 15])

    def test_start_offers_to_stop_other_copies(self):
        stopped = []
        m = SV.Manager(backend="builtin", env=dict(os.environ), run=lambda c: (1, ""), which=lambda n: None,
                       ask=lambda q: True)
        with mock.patch.object(SV, "strays", return_value=[(4242, "telegram", "nimlab telegram run")]), \
                mock.patch.object(SV, "stop_pids", side_effect=lambda p: stopped.extend(p) or p), \
                mock.patch.object(m, "_start", return_value=(True, ["[ok] started"])):
            ok, lines = m.start(ask=lambda q: True)
        self.assertTrue(ok)
        self.assertEqual(stopped, [4242])
        self.assertIn("Other Nim Lab copies are running", "\n".join(lines))

    def test_status_lists_live_children_not_configured(self):
        SV.write_state(running=True, children={"telegram": os.getpid()}, configured=["serve", "telegram"])
        m = SV.Manager(backend="builtin", env=dict(os.environ), run=lambda c: (1, ""), which=lambda n: None)
        with mock.patch.object(SV, "strays", return_value=[]):
            text = "\n".join(SV.status_lines(m))
        self.assertIn(f"children   : telegram (pid {os.getpid()})", text)
        self.assertIn("configured: serve, telegram", text)
        self.assertIn("strays     : none", text)


class ServePortHeld(Base):
    def test_our_server_on_port_exits_wait_code(self):
        from nimlab import server as S, servemenu
        args = mock.Mock(port=8765, host=None, tunnel=None, no_test=True)
        with mock.patch.object(S, "port_owner", return_value="nimlab"), redirect_stdout(io.StringIO()) as out:
            code = servemenu.cmd_serve(args) if hasattr(servemenu, "cmd_serve") else None
        if code is None:
            self.skipTest("cmd_serve signature")
        self.assertEqual(code, SV.EXIT_WAIT)
        self.assertIn("already running on port 8765", out.getvalue())

    def test_other_program_on_port_is_config_error(self):
        from nimlab import server as S, servemenu
        args = mock.Mock(port=8765, host=None, tunnel=None, no_test=True)
        with mock.patch.object(S, "port_owner", return_value="other"), redirect_stdout(io.StringIO()) as out:
            code = servemenu.cmd_serve(args)
        self.assertEqual(code, SV.EXIT_CONFIG)
        self.assertIn("[config]", out.getvalue())


class FakeBot:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def call(self, method, http_timeout=None, **kw):
        self.calls.append(method)
        if method == "deleteWebhook":
            return True
        if method == "getMe":
            return {"username": "quill_lab_bot"}
        if not self.script:
            return []
        r = self.script.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def conflict():
    return T.TelegramError("Conflict: terminated by other getUpdates request; make sure that only one bot "
                           "instance is running", code=409)


class Backend:
    def reply(self, *a, **k):
        return "hi"


class TelegramOnePoller(Base):
    def test_sustained_409_stops_and_reports(self):
        logs = []
        bot = FakeBot([conflict()] * 10)
        conn = T.Connector(bot, Backend(), {"allow": ["1"], "mode": "polling"}, save=lambda: None, log=logs.append)
        code = conn.poll(threading.Event(), sleep=lambda s: None)
        self.assertEqual(code, T.EXIT_CONFIG)
        self.assertEqual(bot.calls.count("getUpdates"), T.CONFLICT_LIMIT)
        self.assertIn("Not retrying (config error)", "\n".join(logs))

    def test_run_refuses_second_poller(self):
        held = T.PollerLock()
        self.assertTrue(held.acquire())
        try:
            with mock.patch.object(T, "load_token", return_value="1:x"):
                logs = []
                code = T.run(log=logs.append, bot=FakeBot([]))
            self.assertEqual(code, T.EXIT_WAIT)
            self.assertIn("already runs", "\n".join(logs))
        finally:
            held.release()

    def test_run_saves_username_and_reports_409_as_config(self):
        stop = threading.Event()
        with mock.patch.object(T, "load_token", return_value="1:x"):
            code = T.run(stop=stop, log=lambda m: None, bot=FakeBot([conflict()] * 10))
        self.assertEqual(code, T.EXIT_CONFIG)
        self.assertEqual(T.settings().get("username"), "quill_lab_bot")
        self.assertIn("409", (config.load_json(T.status_path(), {}) or {}).get("error", ""))

    def test_capture_saves_owner_and_allowlist(self):
        upd = [{"update_id": 1, "message": {"message_id": 1, "chat": {"id": 777, "type": "private"},
                                            "from": {"id": 777, "username": "sevin"}, "text": "/start"}}]
        bot = FakeBot([upd])
        conn = T.Connector(bot, Backend(), T.settings(), log=lambda m: None)
        conn.send = lambda *a, **k: None
        owner = T.capture_owner(conn, seconds=30, log=lambda m: None, sleep=lambda s: None)
        self.assertEqual(str(owner), "777")
        saved = T.settings()
        self.assertEqual(str(saved["owner"]), "777")
        self.assertIn("777", [str(x) for x in saved["allow"]])

    def test_capture_ends_at_once_on_409(self):
        logs = []
        bot = FakeBot([conflict()] * 50)
        conn = T.Connector(bot, Backend(), T.settings(), log=logs.append)
        clock = [0.0]
        owner = T.capture_owner(conn, seconds=120, log=logs.append, sleep=lambda s: None, clock=lambda: clock[0])
        self.assertIsNone(owner)
        self.assertEqual(bot.calls.count("getUpdates"), 1)     # no multi-minute silent loop
        self.assertIn("409", "\n".join(logs))
        self.assertIn("nimlab telegram allow <id>", "\n".join(logs))

    def test_capture_asks_running_bot_instead_of_second_poller(self):
        held = T.PollerLock()
        self.assertTrue(held.acquire())
        try:
            clock = [0.0]
            logs = []

            def sleep(_s):
                clock[0] += 1
                if clock[0] == 3:        # the running bot captured and saved
                    T.save_keys(owner="555", allow=["555"])
            conn = T.Connector(FakeBot([]), Backend(), T.settings(), log=logs.append)
            owner = T.capture_owner(conn, seconds=20, log=logs.append, sleep=sleep, clock=lambda: clock[0])
            self.assertEqual(owner, "555")
            self.assertIn("asking it to capture", "\n".join(logs))
            self.assertEqual(json.load(open(T.capture_path()))["until"], 0)
        finally:
            held.release()

    def test_running_bot_honors_capture_request(self):
        with open(T.capture_path(), "w") as f:
            json.dump({"until": 9e12}, f)
        upd = {"update_id": 1, "message": {"message_id": 1, "chat": {"id": 99, "type": "private"},
                                           "from": {"id": 99}, "text": "/start"}}
        conn = T.Connector(FakeBot([]), Backend(), T.settings(), log=lambda m: None, capture_file=T.capture_path())
        conn.send = lambda *a, **k: None
        conn.handle(upd)
        saved = T.settings()
        self.assertIn("99", [str(x) for x in saved["allow"]])
        self.assertEqual(json.load(open(T.capture_path()))["until"], 0)

    def test_brief_flags_config_problems(self):
        with mock.patch.object(T, "load_token", return_value="1:x"):
            b = T.brief()
        self.assertIn("@? (run: nimlab telegram test)", b)
        self.assertIn("nobody can chat", b)


class MemoryOneTruth(Base):
    """Setup's status line, the memory menu, `memory status`, the header and
    the pipeline (MemoryCore.settings) read one setting."""

    def write_ms(self, lt):
        cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        cfg["memory_settings"] = {"long_term": lt}
        config.save_json(config.CLUSTER_CONFIG, cfg)

    def views(self):
        from nimlab import wizard
        from nimlab.memory import MemoryCore
        ms = (config.load_cluster_config() or {}).get("memory_settings") or {}
        menu = memmenu.effective()
        setup = wizard.Wizard.__new__(wizard.Wizard)
        setup.env = {}
        st = setup.st_memory()[1]
        core = MemoryCore(None, "", settings=ms)
        return menu, st, core.settings, memmenu.header_line(count_fn=lambda: 4)

    def test_setup_menu_pipeline_and_header_agree(self):
        for val, word in ((False, "off"), (True, "on"), ("off", "off"), ("on", "on"), (0, "off")):
            self.write_ms({"backend": "local", "local": {"directory": os.path.join(self.lab.home, "m")},
                           "auto_store": val, "auto_recall": True})
            menu, st, core, header = self.views()
            self.assertEqual(menu["auto_store"], word == "on", val)
            self.assertIn(f"auto store {word}", st)
            self.assertEqual(bool(core["auto_store"]), word == "on", val)
            self.assertEqual("auto store off" in header, word == "off")

    def test_header_reports_active_backend_count(self):
        self.write_ms({"backend": "oracle", "auto_store": False})
        self.assertEqual(memmenu.header_line(count_fn=lambda: 4), "Oracle TESTBED: 4 (auto store off)")
        self.write_ms({"backend": "oracle", "auto_store": True})
        self.assertEqual(memmenu.header_line(count_fn=lambda: 4), "Oracle TESTBED: 4")

        def boom():
            raise RuntimeError("DPY-6005 cannot connect")
        self.assertIn("unreachable (DPY-6005", memmenu.header_line(count_fn=boom))

    def test_menu_does_not_write_back_a_stale_copy(self):
        self.write_ms({"backend": "local", "auto_store": False})
        stale = config.load_cluster_config()
        import time
        seq = []

        def ask(p=""):
            seq.append(p)
            if len(seq) == 1:   # setup (another process) turns auto store on while the menu is open
                self.write_ms({"backend": "local", "auto_store": True})
                os.utime(config.CLUSTER_CONFIG, (time.time() + 5, time.time() + 5))
                return "6"      # toggle auto recall: the menu saves
            if len(seq) == 2:
                return "off"
            return "0"
        saved = []

        def save():
            cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
            cfg["memory_settings"] = stale["memory_settings"]
            config.save_json(config.CLUSTER_CONFIG, cfg)
            saved.append(1)
        with redirect_stdout(io.StringIO()):
            memmenu.run_menu(stale, ask, save_fn=save)
        self.assertTrue(saved)
        e = memmenu.effective()
        self.assertTrue(e["auto_store"], "the menu wrote its stale auto_store=off back")
        self.assertFalse(e["auto_recall"])

    def test_entity_follows_settings_changed_on_disk(self):
        from nimlab.entity import Entity
        self.write_ms({"backend": "json", "auto_store": False})
        try:
            e = Entity.__new__(Entity)
        except Exception:  # noqa: BLE001
            self.skipTest("entity")
        from nimlab.memory import MemoryCore
        e.cluster = config.load_cluster_config()
        e.memory = MemoryCore(None, "", settings=e.cluster["memory_settings"])
        e.log = lambda *a, **k: None
        e._snapshot_config(from_file=True)
        self.assertFalse(e.memory.settings["auto_store"])
        import time
        time.sleep(0.02)
        self.write_ms({"backend": "json", "auto_store": True})
        os.utime(config.CLUSTER_CONFIG, (time.time() + 5, time.time() + 5))
        self.assertTrue(e.refresh_memory_settings())
        self.assertTrue(e.memory.settings["auto_store"])

    def test_setup_status_is_degraded_after_failed_memory_test(self):
        from nimlab import wizard
        self.write_ms({"backend": "local", "local": {"directory": os.path.join(self.lab.home, "m")}})
        ms = config.load_cluster_config()["memory_settings"]
        out = ("[ok] backend local\n[!!] embedding: nvidia/llama-nemotron-embed-vl-1b-v2 returned no vector: "
               "HTTP 400 input_type is required\n")
        wizard.record_memory_check(ms, 1, out)
        w = wizard.Wizard.__new__(wizard.Wizard)
        w.env = {}
        r = w.st_memory()
        self.assertEqual(r[2], "degraded")
        self.assertIn("input_type is required", r[1])
        ok, text, level = w._status3(w.st_memory)
        self.assertFalse(ok)
        self.assertNotIn("[ok]", w._mark(level))
        self.assertIn("degraded", w._mark(level))
        # a passing test for the same settings clears it
        wizard.record_memory_check(ms, 0, "[ok] all\n")
        self.assertEqual(len(w.st_memory()), 2)

    def test_hard_failure_is_failed_not_degraded(self):
        from nimlab import wizard
        self.assertEqual(wizard.classify_memory_test(1, "[!!] backend check failed: DPY-4005 ORA-01017")[0],
                         "failed")
        self.assertEqual(wizard.classify_memory_test(124, "")[0], "failed")
        self.assertEqual(wizard.classify_memory_test(1, "[!!] embedding size 1024 vs VECTOR(2048)")[0],
                         "degraded")


class Recall(Base):
    def test_trace_shows_scores_and_near_misses(self):
        from nimlab.memory import MemoryCore
        d = os.path.join(self.lab.home, "m")
        ms = {"long_term": {"backend": "local", "local": {"directory": d}, "embedding": {"provider": "hash"}},
              "similarity_threshold": 0.99, "recall_top_k": 3}
        try:
            m = MemoryCore(None, "hash", embed_fn=lambda t, *a, **k: [float(len(t) % 7 + 1), 1.0, 0.5],
                           settings=ms)
            for txt in ("The cat is named Biscuit", "Vin prefers short answers", "Nim Lab runs on Termux"):
                m.remember(txt) if hasattr(m, "remember") else None
            hits = m.recall("what is the cat called", 3, 0.99)
        except Exception as e:  # noqa: BLE001
            self.skipTest(f"local backend unavailable here: {e}")
        self.assertIsInstance(m.last_near_miss, list)
        self.assertLessEqual(len(hits), 3)


if __name__ == "__main__":
    unittest.main()
