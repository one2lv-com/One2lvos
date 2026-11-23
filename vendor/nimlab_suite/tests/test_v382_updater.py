"""3.8.2 ./update.sh: stop auto-restart, clean up only Nim Lab, start once,
health check. A fake host stands in for /proc, kill, sv/systemctl and HTTP:
nothing real is stopped or started."""

import os
import signal
import subprocess
import unittest
from unittest import mock

from nimlab import service as SV, updater as U
from tests.sandbox import lab

ME = 5000
UID = 1000


class FakeHost:
    """Processes as {pid: [ppid, uid, cmd]}. `respawn` maps a supervisor pid to
    the children it starts again when one is killed while it runs."""

    def __init__(self, procs, tools=("sv",), files=(), http=None, sv_runs=None):
        self.p = {pid: list(v) for pid, v in procs.items()}
        self.p.setdefault(ME, [4999, UID, "python3 -m nimlab update"])
        self.p.setdefault(4999, [1, UID, "bash update.sh"])
        self.me = ME
        self.tools = set(tools)
        self.files = set(files)
        self.http_map = http or {}
        self.calls = []
        self.kills = []
        self.t = 0.0
        self.next_pid = 9000
        self.respawn = {}          # supervisor pid -> list of kinds to restart
        self.sv_respawns = sv_runs  # runit restarts the supervisor while not `sv down`
        self.sv_down = False
        self.ignore_term = set()
        self.started = []

    # Host API
    def procs(self):
        return [(pid, v[0], v[1], v[2]) for pid, v in self.p.items()]

    def kill(self, pid, sig):
        if pid not in self.p:
            raise ProcessLookupError(pid)
        self.kills.append((pid, sig))
        if sig == signal.SIGTERM and pid in self.ignore_term:
            return
        cmd = self.p.pop(pid)[2]
        # a running supervisor restarts a killed child
        for sup, kinds in self.respawn.items():
            if sup in self.p and sup != pid and U.kind_of(cmd) in kinds:
                self._spawn(sup, cmd)
        # runit restarts the supervisor unless it was taken down
        if self.sv_respawns and U.kind_of(cmd) == "supervisor" and not self.sv_down:
            self._spawn(1, cmd)
        # a stopping supervisor takes its children with it
        if U.kind_of(cmd) == "supervisor" and sig == signal.SIGTERM:
            for c in [c for c, v in self.p.items() if v[0] == pid]:
                self.p.pop(c)

    def _spawn(self, ppid, cmd):
        self.next_pid += 1
        self.p[self.next_pid] = [ppid, UID, cmd]
        return self.next_pid

    def run(self, cmd, timeout=60):
        self.calls.append(" ".join(cmd))
        if cmd[:2] == ["sv", "down"]:
            self.sv_down = True
        if cmd[:2] == ["sv", "up"]:
            self.sv_down = False
            self.started.append("sv")
            sup = self._spawn(1, "bash start.sh service run")
            self._spawn(sup, "python3 -m nimlab serve start --quiet")
            self._spawn(sup, "python3 -m nimlab scheduler run")
        return 0, ""

    def which(self, name):
        return "/bin/" + name if name in self.tools else None

    def exists(self, path):
        return any(path.endswith(f) for f in self.files)

    def sleep(self, s):
        self.t += s

    def now(self):
        return self.t

    def http(self, url, key=None, timeout=5):
        for k, v in self.http_map.items():
            if url.endswith(k):
                return v
        return None

    def uid(self):
        return UID


RUNNING = {
    100: [1, UID, "bash /home/u/nvidia_nim_test_lab/start.sh service run"],
    101: [100, UID, "python3 -m nimlab serve start --quiet"],
    102: [100, UID, "python3 -m nimlab scheduler run"],
    # a duplicate from an earlier overlay, orphaned
    200: [1, UID, "python3 -m nimlab serve start --quiet"],
    201: [1, UID, "python3 -m nimlab telegram run"],
    # unrelated work in Termux: never touched
    300: [1, UID, "python3 my_bot.py"],
    301: [1, UID, "python3 -m http.server 8000"],
    302: [1, 0, "python3 -m nimlab serve start"],        # another user's
    303: [1, UID, "vim nimlab/service.py"],
}
HEALTHY = {"/health": 200, "/v1/models": 200}


class KindOf(unittest.TestCase):
    def test_kinds(self):
        k = U.kind_of
        self.assertEqual(k("bash /x/start.sh service run"), "supervisor")
        self.assertEqual(k("/usr/bin/python3 -m nimlab serve start --quiet"), "serve")
        self.assertEqual(k("python3 -m nimlab telegram run"), "telegram")
        self.assertEqual(k("python3 -m nimlab scheduler run"), "scheduler")
        for cmd in ("python3 my_bot.py", "python3 -m nimlab update", "python3 -m nimlab service cleanup",
                    "vim nimlab/service.py", "cloudflared tunnel run", "python3 -m http.server"):
            self.assertIsNone(k(cmd), cmd)
        self.assertEqual(k("cloudflared tunnel --url x", 77, 77), "tunnel")
        self.assertIsNone(k("cloudflared tunnel --url x", 77, 78))


class Run(unittest.TestCase):
    def make(self, host, tg=False, backend="auto"):
        sv = SV.settings()
        sv.update(telegram=tg, backend=backend)
        SV.save_settings(sv)
        out = []
        return U.Updater(host=host, out=out.append, mgr=mock.Mock(), env=os.environ), out

    def test_termux_respawning_supervisor_one_run(self):
        with lab(termux=True):
            h = FakeHost(RUNNING, tools=("sv",), files=("service/nimlab/run",), http=HEALTHY, sv_runs=True)
            h.respawn[100] = ("serve", "scheduler", "telegram")
            u, out = self.make(h)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                code = u.run()
            text = "\n".join(out)
            self.assertEqual(code, 0, text)
            self.assertIn("GOOD TO GO", text)
            # sv down came before any kill, and sv up exactly once
            self.assertEqual(h.calls[0], "sv down nimlab")
            self.assertEqual(h.calls.count("sv up nimlab"), 1)
            # unrelated, other-user and our own processes untouched
            for pid in (300, 301, 302, 303, ME, 4999):
                self.assertIn(pid, h.p)
                self.assertNotIn(pid, [p for p, _s in h.kills])
            kinds = sorted(U.kind_of(v[2]) for v in h.p.values() if U.kind_of(v[2]) and v[1] == UID)
            self.assertEqual(kinds, ["scheduler", "serve", "supervisor"])

    def test_repeated_invocation_is_idempotent(self):
        with lab(termux=True):
            h = FakeHost(RUNNING, tools=("sv",), files=("service/nimlab/run",), http=HEALTHY, sv_runs=True)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                for _ in range(3):
                    u, out = self.make(h)
                    self.assertEqual(u.run(), 0, "\n".join(out))
            kinds = [U.kind_of(v[2]) for v in h.p.values() if U.kind_of(v[2]) and v[1] == UID]
            self.assertEqual(sorted(kinds), ["scheduler", "serve", "supervisor"])

    def test_builtin_supervisor_stops_first_and_restarts(self):
        with lab():
            h = FakeHost(RUNNING, tools=(), http=HEALTHY)
            h.respawn[100] = ("serve", "scheduler")
            u, out = self.make(h, backend="builtin")

            def start():
                sup = h._spawn(1, "bash start.sh service run")
                h._spawn(sup, "python3 -m nimlab serve start --quiet")
                h._spawn(sup, "python3 -m nimlab scheduler run")
                return True, ["[ok] Started the built-in supervisor"]
            u.mgr._start.side_effect = start
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                self.assertEqual(u.run(), 0, "\n".join(out))
            first_kill = h.kills[0][0]
            self.assertEqual(first_kill, 100, "the supervisor is stopped before its children")
            u.mgr._start.assert_called_once()

    def test_outside_respawner_fails_without_restart(self):
        with lab():
            h = FakeHost(RUNNING, tools=(), http=HEALTHY)
            real_kill = h.kill

            def kill(pid, sig):    # something outside Nim Lab restarts serve
                real_kill(pid, sig)
                if U.kind_of("python3 -m nimlab serve start") and pid in (101, 200) or pid > 9000:
                    h._spawn(1, "python3 -m nimlab serve start --quiet")
            h.kill = kill
            u, out = self.make(h)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                code = u.run()
            text = "\n".join(out)
            self.assertEqual(code, 1)
            self.assertIn("keep coming back", text)
            self.assertIn("Nothing was restarted", text)
            self.assertNotIn("GOOD TO GO", text)
            u.mgr._start.assert_not_called()

    def test_sigterm_ignored_gets_verified_sigkill(self):
        with lab():
            h = FakeHost({400: [1, UID, "python3 -m nimlab telegram run"]}, tools=())
            h.ignore_term.add(400)
            u, out = self.make(h)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                self.assertEqual(u.run(stop_only=True), 0, "\n".join(out))
            self.assertIn((400, signal.SIGKILL), h.kills)
            self.assertNotIn(400, h.p)

    def test_health_failure_is_not_good_to_go(self):
        with lab(termux=True):
            h = FakeHost(RUNNING, tools=("sv",), files=("service/nimlab/run",),
                         http={"/health": None}, sv_runs=True)
            u, out = self.make(h)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                code = u.run(wait=4)
            text = "\n".join(out)
            self.assertEqual(code, 1)
            self.assertIn("NOT HEALTHY", text)
            self.assertIn("does not answer", text)
            self.assertNotIn("GOOD TO GO", text)

    def test_missing_telegram_poller_is_reported(self):
        with lab(termux=True):
            h = FakeHost({}, tools=("sv",), files=("service/nimlab/run",), http=HEALTHY)
            u, out = self.make(h, tg=True)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                self.assertEqual(u.run(wait=4), 1)
            self.assertIn("telegram: not running", "\n".join(out))

    def test_start_failure(self):
        with lab(termux=True):
            h = FakeHost({}, tools=("sv",), files=("service/nimlab/run",), http=HEALTHY)
            real = h.run
            h.run = lambda cmd, timeout=60: (1, "fail: down") if cmd[:2] == ["sv", "up"] else real(cmd)
            u, out = self.make(h)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                self.assertEqual(u.run(), 1)
            self.assertIn("NOT STARTED", "\n".join(out))

    def test_systemd_system_unit_needs_root(self):
        with lab():
            h = FakeHost({}, tools=("systemctl",), files=("/etc/systemd/system/nimlab.service",))
            real = h.run
            h.run = lambda cmd, timeout=60: (1, "a password is required") if cmd[0] == "sudo" else real(cmd)
            u, out = self.make(h)
            self.assertEqual(u.run(), 1)
            self.assertIn("sudo systemctl stop nimlab", "\n".join(out))

    def test_no_service_installed_just_cleans(self):
        with lab():
            h = FakeHost({201: [1, UID, "python3 -m nimlab telegram run"]}, tools=())
            u, out = self.make(h)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                self.assertEqual(u.run(), 0)
            self.assertNotIn(201, h.p)
            self.assertIn("No background service is installed", "\n".join(out))

    def test_concurrent_update_refused(self):
        with lab():
            held = U.UpdateLock()
            self.assertIs(held.acquire(), True)
            try:
                h = FakeHost({}, tools=())
                u, out = self.make(h)
                self.assertEqual(u.run(), 2)
                self.assertIn("Another update is running", "\n".join(out))
            finally:
                held.release()
            self.assertIs(U.UpdateLock().acquire(), True)   # released: a crashed holder never blocks

    def test_stale_pidfile_removed_only_when_dead(self):
        with lab():
            with open(SV.pid_path(), "w") as f:
                f.write("424242")
            h = FakeHost({}, tools=())
            u, out = self.make(h)
            self.assertIn("supervisor.pid", u.clear_stale())
            self.assertFalse(os.path.exists(SV.pid_path()))
            with open(SV.pid_path(), "w") as f:
                f.write("100")
            h.p[100] = [1, UID, "bash start.sh service run"]
            self.assertEqual(u.clear_stale(), [])
            self.assertTrue(os.path.exists(SV.pid_path()))

    def test_config_and_secrets_untouched(self):
        with lab(termux=True) as ns:
            cfg = os.path.join(ns.home, ".config", "nimlab")
            os.makedirs(cfg, exist_ok=True)
            with open(os.path.join(cfg, "secrets.json"), "w") as f:
                f.write('{"k": "v"}')
            before = {p: open(os.path.join(cfg, p)).read() for p in os.listdir(cfg)}
            h = FakeHost(RUNNING, tools=("sv",), files=("service/nimlab/run",), http=HEALTHY, sv_runs=True)
            u, out = self.make(h)
            with mock.patch.object(U, "tunnel_pid", return_value=None):
                u.run()
            self.assertEqual(before, {p: open(os.path.join(cfg, p)).read() for p in os.listdir(cfg)})


class StopPids(unittest.TestCase):
    def test_waits_for_exit_before_sigkill(self):
        alive = {1: 3}           # exits after three polls
        sent = []

        def kill(pid, sig):
            sent.append((pid, sig))
            if sig == 0:
                alive[pid] -= 1
                if alive[pid] <= 0:
                    raise ProcessLookupError
        SV.stop_pids([1], kill=kill, sleep=lambda s: None)
        self.assertNotIn((1, signal.SIGKILL), sent)


class Script(unittest.TestCase):
    def test_update_sh(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        p = os.path.join(root, "update.sh")
        self.assertTrue(os.access(p, os.X_OK))
        self.assertEqual(subprocess.run(["bash", "-n", p]).returncode, 0)
        text = open(p).read()
        self.assertIn("start.sh\" update", text)
        self.assertNotIn("pkill", text)
        self.assertNotIn("killall", text)


if __name__ == "__main__":
    unittest.main()
