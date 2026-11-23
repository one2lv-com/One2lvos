"""The keep-running service on Termux, systemd and the built-in supervisor.
Everything goes to a temp PREFIX/HOME and a fake command runner: no real
sv, systemctl, pkg or background process is touched."""

import io
import os
import stat
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import config, service as SV
from tests.sandbox import all_text, lab

KEY = "nvapi-" + "s" * 40


class FakeRun:
    def __init__(self, results=None):
        self.calls = []
        self.results = results or {}

    def __call__(self, cmd):
        self.calls.append(" ".join(cmd))
        for prefix, res in self.results.items():
            if " ".join(cmd).startswith(prefix):
                return res
        return 0, ""


def which_all(name):
    return "/fake/bin/" + name


def which_none(name):
    return None


class Base(unittest.TestCase):
    termux = False

    def setUp(self):
        self._lab = lab(termux=self.termux)
        self.lab = self._lab.__enter__()
        os.environ["NVIDIA_API_KEY"] = KEY        # a key in the environment must never reach a service file
        os.environ["USER"] = "vin"

    def tearDown(self):
        self._lab.__exit__(None, None, None)

    def mgr(self, backend, run=None, which=which_all):
        return SV.Manager(backend=backend, env=dict(os.environ), run=run or FakeRun(), which=which)

    def assert_no_secret(self, *roots):
        for r in roots:
            self.assertNotIn(KEY, all_text(r))


class TermuxService(Base):
    termux = True

    def test_auto_picks_termux(self):
        self.assertEqual(SV.pick_backend("auto", dict(os.environ), which_all), "termux")

    def test_install_writes_runit_files_and_enables(self):
        run = FakeRun()
        m = self.mgr("termux", run)
        ok, lines = m.install()
        self.assertTrue(ok, lines)
        d = SV.termux_service_dir(m.env)
        self.assertTrue(d.startswith(os.environ["PREFIX"]))
        with open(os.path.join(d, "run")) as f:
            run_text = f.read()
        self.assertTrue(run_text.startswith(f"#!{os.environ['PREFIX']}/bin/sh"))
        self.assertIn("service run", run_text)
        self.assertIn(os.path.join(os.environ["PREFIX"], "bin", "bash"), run_text)
        self.assertTrue(os.access(os.path.join(d, "run"), os.X_OK))
        self.assertIn("svlogd", open(os.path.join(d, "log", "run")).read())
        self.assertEqual(run.calls, ["sv status nimlab", "sv-enable nimlab"])
        self.assertEqual(SV.settings()["backend"], "termux")
        self.assertTrue(m.installed())
        self.assert_no_secret(os.environ["PREFIX"], self.lab.proj)

    def test_install_gets_termux_services_when_missing(self):
        run = FakeRun()
        ok, lines = self.mgr("termux", run, which_none).install()
        self.assertTrue(ok)
        self.assertEqual(run.calls[0], "pkg install -y termux-services")
        self.assertIn("Close Termux completely", "\n".join(lines))
        run2 = FakeRun({"pkg install": (100, "E: unable to fetch")})
        ok, lines = self.mgr("termux", run2, which_none).install()
        self.assertFalse(ok)
        self.assertIn("pkg install termux-services failed", lines[-1])

    def test_boot_script_takes_wake_lock(self):
        m = self.mgr("termux")
        ok, lines = m.install(boot=True)
        bp = SV.boot_path(m.env)
        self.assertTrue(bp.startswith(os.path.join(self.lab.home, ".termux", "boot")))
        with open(bp) as f:
            text = f.read()
        self.assertIn("termux-wake-lock", text)
        self.assertEqual(stat.S_IMODE(os.stat(bp).st_mode), 0o700)
        self.assertIn("battery optimisation", "\n".join(lines))
        self.assertIn("service start", SV.boot_script("builtin", m.env))

    def test_status_start_stop_remove(self):
        run = FakeRun({"sv status": (0, "run: nimlab: (pid 123) 45s")})
        m = self.mgr("termux", run)
        m.install(boot=True)
        self.assertTrue(m.running())
        lines = SV.status_lines(m)
        self.assertIn("backend    : termux", lines)
        self.assertIn("installed  : yes", lines)
        self.assertTrue(any(ln.startswith("boot       : on") for ln in lines))
        self.assertEqual(m.start()[0], True)
        self.assertEqual(m.restart()[0], True)
        ok, lines = m.remove()
        self.assertTrue(ok)
        for c in ("sv up nimlab", "sv restart nimlab", "sv down nimlab", "sv-disable nimlab"):
            self.assertIn(c, run.calls)
        self.assertFalse(os.path.exists(SV.termux_service_dir(m.env)))
        self.assertFalse(os.path.exists(SV.boot_path(m.env)))
        self.assertFalse(m.installed())

    def test_sv_failure_reported(self):
        m = self.mgr("termux", FakeRun({"sv up": (1, "fail: nimlab: unable to change to service directory")}))
        ok, lines = m.start()
        self.assertFalse(ok)
        self.assertIn("sv up failed", lines[0])


class SystemdService(Base):
    def test_auto_picks_systemd_when_user_bus_works(self):
        run = mock.Mock(return_value=types.SimpleNamespace(returncode=0))
        self.assertEqual(SV.pick_backend("auto", {}, which_all, run), "systemd")
        run = mock.Mock(return_value=types.SimpleNamespace(returncode=1))
        self.assertEqual(SV.pick_backend("auto", {}, which_all, run), "builtin")
        self.assertEqual(SV.pick_backend("auto", {}, which_none), "builtin")

    def test_install_writes_unit_and_enables(self):
        run = FakeRun()
        m = self.mgr("systemd", run)
        ok, lines = m.install()
        self.assertTrue(ok, lines)
        p = SV.unit_path(m.env)
        self.assertEqual(p, os.path.join(self.lab.home, ".config", "systemd", "user", "nimlab.service"))
        with open(p) as f:
            unit = f.read()
        for bit in ("Restart=on-failure", "ExecStart=/bin/bash", "service run", f"WorkingDirectory={config.PROJECT_DIR}",
                    "WantedBy=default.target"):
            self.assertIn(bit, unit)
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o644)
        self.assertEqual(run.calls, ["systemctl --user daemon-reload", "systemctl --user enable --now nimlab",
                                     "loginctl show-user vin -p Linger"])   # 3.7.4: checks linger
        self.assertIn("sudo loginctl enable-linger vin", "\n".join(lines))
        self.assert_no_secret(self.lab.home, self.lab.proj)
        self.assertNotIn("NVIDIA_API_KEY", unit)

    def test_enable_failure_stops_install(self):
        m = self.mgr("systemd", FakeRun({"systemctl --user enable": (1, "Failed to connect to bus")}))
        ok, lines = m.install()
        self.assertFalse(ok)
        self.assertIn("Failed to connect to bus", lines[-1])

    def test_status_and_remove(self):
        run = FakeRun({"systemctl --user is-active": (0, "active")})
        m = self.mgr("systemd", run)
        m.install()
        self.assertTrue(m.running())
        self.assertIn("running (systemd)", SV.brief(m))
        ok, lines = m.remove()
        self.assertIn("systemctl --user disable --now nimlab", run.calls)
        self.assertFalse(os.path.exists(SV.unit_path(m.env)))
        self.assertEqual(SV.brief(m), "not set up")

    def test_boot_off_termux_explains(self):
        self.assertIn("linger", self.mgr("systemd").enable_boot()[0])
        self.assertIn("cron", self.mgr("builtin").enable_boot()[0])


class BuiltinService(Base):
    def fake_popen(self, alive=True):
        test = self

        class P:
            pid = 4242
            returncode = None

            def __init__(self, cmd, **kw):
                test.started = cmd
                if alive:
                    with open(SV.pid_path(), "w") as f:
                        f.write(str(os.getpid()))
                else:
                    self.returncode = 2

            def poll(self):
                return self.returncode
        return P

    def test_start_status_stop_without_real_process(self):
        m = self.mgr("builtin")
        with mock.patch.object(SV.subprocess, "Popen", self.fake_popen()), mock.patch.object(SV.time, "sleep"):
            ok, lines = m.install()
        self.assertTrue(ok, lines)
        self.assertEqual(self.started[-2:], ["service", "run"])
        self.assertTrue(m.installed())
        self.assertTrue(m.running())
        self.assertIn("Already running", m.start()[1][0])
        killed = []

        def fake_kill(pid, sig):
            if sig:
                killed.append(pid)
                os.unlink(SV.pid_path())
            elif not os.path.exists(SV.pid_path()):
                raise ProcessLookupError
        with mock.patch.object(SV.os, "kill", fake_kill), mock.patch.object(SV.time, "sleep"):
            ok, lines = m.stop()
        self.assertEqual(killed, [os.getpid()])
        self.assertIn("[ok] Stopped", lines[0])
        self.assertEqual(m.stop()[1], ["Not running."])

    def test_supervisor_exiting_at_once(self):
        m = self.mgr("builtin")
        with mock.patch.object(SV.subprocess, "Popen", self.fake_popen(alive=False)), \
                mock.patch.object(SV.time, "sleep"):
            ok, lines = m.start()
        self.assertFalse(ok)
        self.assertIn("exited at once (code 2)", lines[0])

    def test_supervisor_backoff_and_crash_loop(self):
        t = [1000.0]
        sup = SV.Supervisor(cmds={"serve": ["x"]}, log=SV.RotatingLog(SV.log_path()), clock=lambda: t[0],
                            env={}, wake=False, crash_limit=4, crash_window=120, cooldown=300)
        delays = [sup.handle_exit("serve", 1) for _ in range(3)]
        self.assertEqual(delays, [2, 4, 8])
        self.assertEqual(sup.handle_exit("serve", 1), 300)
        st = SV.read_state()
        self.assertEqual(st["restarts"], 4)
        self.assertEqual(st["crash_loop"]["child"], "serve")
        t[0] += 1000                        # old crashes fall out of the window
        self.assertEqual(sup.handle_exit("serve", 0), 2)
        self.assertIn("crash loop", SV.log_tail())

    def test_supervisor_restarts_child(self):
        class Child:
            n = 0

            def __init__(self, cmd, **kw):
                Child.n += 1
                self.pid = 100 + Child.n
                self.stdout = io.StringIO(f"hello from run {Child.n} key={KEY}\n")
                self.code = 1 if Child.n == 1 else None

            def poll(self):
                return self.code

            def terminate(self):
                self.code = -15

            def wait(self, timeout=None):
                return self.code
        t = [0.0]

        def sleep(s):
            t[0] += 5
        sup = SV.Supervisor(cmds={"serve": ["x"]}, popen=Child, sleep=sleep, clock=lambda: t[0], env={}, wake=False)
        sup.run(max_loops=4)
        self.assertEqual(Child.n, 2)
        st = SV.read_state()
        self.assertEqual((st["restarts"], st["running"]), (1, False))
        log = SV.log_tail()
        self.assertIn("serve exited with code 1; restarting in 2 s", log)
        self.assertNotIn(KEY, log)          # secrets are scrubbed from the log

    def test_log_rotates(self):
        lg = SV.RotatingLog(os.path.join(self.lab.data, "r.log"), max_bytes=100, keep=2)
        for i in range(40):
            lg.write(f"line {i} " + "x" * 20)
        names = sorted(os.listdir(self.lab.data))
        self.assertIn("r.log.1", names)
        self.assertIn("r.log.2", names)
        self.assertNotIn("r.log.3", names)

    def test_runtime_env_reads_key_file_at_run_time(self):
        del os.environ["NVIDIA_API_KEY"]
        with open(self.lab.env_file, "w") as f:
            f.write(f"export NVIDIA_API_KEY='{KEY}'\n")
        with mock.patch("nimlab.core.load_api_key", return_value=None, create=True):
            env = SV.runtime_env()
        self.assertEqual(env["NVIDIA_API_KEY"], KEY)
        self.assertEqual(env["NIMLAB_SERVICE"], "1")

    def test_cli_status_telegram_and_logs(self):
        def call(**kw):
            args = types.SimpleNamespace(action="status", backend="builtin", boot=False, value=None, lines=None)
            for k, v in kw.items():
                setattr(args, k, v)
            out = io.StringIO()
            with redirect_stdout(out):
                code = SV.cmd_service(args)
            return code, out.getvalue()
        code, out = call()
        self.assertEqual(code, 0)
        self.assertIn("backend    : builtin", out)
        self.assertIn("installed  : no", out)
        self.assertEqual(call(action="telegram", value="on")[0], 0)
        self.assertTrue(SV.settings()["telegram"])
        self.assertIn("telegram", SV.child_commands())
        self.assertEqual(call(action="telegram", value="maybe")[0], 2)
        self.assertIn("no log yet", call(action="logs")[1])
        self.assertEqual(call(action="brief")[0], 1)


if __name__ == "__main__":
    unittest.main()
