"""`./update.sh` / `nimlab update` (3.8.2): run it after unzipping a release
over the installed folder.

What it does, in order, and why:

1. Takes a lock (data/service/update.lock, flock: a crashed update never
   blocks the next one), so two updates never fight.
2. Stops the thing that restarts Nim Lab FIRST: termux-services (`sv down`),
   the systemd user or system unit (`systemctl stop`), then the built-in
   supervisor (SIGTERM, then it gets up to 40 seconds to stop its children
   itself). Killing children while the supervisor still runs only makes it
   start new ones: that is why `service cleanup` used to need two or three
   runs.
3. Stops every Nim Lab process that is left (supervisor, serve, telegram,
   scheduler, and the cloudflared that our tunnel started), only processes of
   this user whose command line is a Nim Lab one, never this updater or its
   parents. SIGTERM, a bounded wait, then SIGKILL only after checking the
   pid still runs the same command (pids get reused). If new copies keep
   appearing it says what starts them and stops without restarting.
4. Removes stale pid files (only when the pid is dead).
5. Starts the service once, through the backend that is installed.
6. Health check: one supervisor, one copy of each part, /health and
   /v1/models answer with the server key, one Telegram poller, and the same
   pids a few seconds later (no crash loop). Prints GOOD TO GO only when
   every check passed.

Unzipping is not atomic: files are replaced one by one, and a script run
afterwards cannot protect the unzip itself. If a running server ever picks up
a half-written file, run `./update.sh --stop` before unzipping, then
`./update.sh` after. Nothing in data/ or ~/.config/nimlab is touched.
"""

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

from . import config

SUPERVISOR_WAIT = 40     # the supervisor stops up to three children, 10 s each
CHILD_WAIT = 12
CLEAN_ROUNDS = 3
HEALTH_WAIT = 60
STABLE_WAIT = 4
KINDS = ("supervisor", "serve", "telegram", "scheduler", "tunnel")


# ---------------------------------------------------------------------------
# the system, behind one object so tests can fake it
# ---------------------------------------------------------------------------
class Host:
    def __init__(self):
        self.me = os.getpid()

    def procs(self):
        """[(pid, ppid, uid, cmdline)] from /proc."""
        out = []
        try:
            names = os.listdir("/proc")
        except OSError:
            return out
        for d in names:
            if not d.isdigit():
                continue
            pid = int(d)
            try:
                with open(f"/proc/{d}/cmdline", "rb") as f:
                    cmd = f.read().replace(b"\0", b" ").decode("utf-8", "replace").strip()
                with open(f"/proc/{d}/stat") as f:
                    ppid = int(f.read().rsplit(")", 1)[1].split()[1])
                uid = os.stat(f"/proc/{d}").st_uid
            except (OSError, ValueError, IndexError):
                continue
            if cmd:
                out.append((pid, ppid, uid, cmd))
        return out

    def kill(self, pid, sig):
        os.kill(pid, sig)

    def run(self, cmd, timeout=60):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout + r.stderr).strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return 127, str(e)

    def which(self, name):
        import shutil
        return shutil.which(name)

    def exists(self, path):
        return os.path.exists(path)

    def sleep(self, s):
        time.sleep(s)

    def now(self):
        return time.monotonic()

    def http(self, url, key=None, timeout=5):
        h = {"User-Agent": "nimlab-update"}
        if key:
            h["Authorization"] = f"Bearer {key}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def uid(self):
        return os.geteuid() if hasattr(os, "geteuid") else 0


# ---------------------------------------------------------------------------
# which processes are ours
# ---------------------------------------------------------------------------
def kind_of(cmd, tunnel_pid=None, pid=None):
    """'supervisor' | 'serve' | 'telegram' | 'scheduler' | 'tunnel' | None."""
    words = cmd.replace("/", " ").split()
    if "nimlab" in words or "start.sh" in words:
        if "service" in words and "run" in words:
            return "supervisor"
        if "serve" in words and "start" in words:
            return "serve"
        if "telegram" in words and "run" in words:
            return "telegram"
        if "scheduler" in words and "run" in words:
            return "scheduler"
    if tunnel_pid and pid == tunnel_pid and "cloudflared" in cmd:
        return "tunnel"
    return None


def allowed_uids(host, env=None):
    """This user; under sudo also the user who ran sudo (the service runs as them)."""
    env = os.environ if env is None else env
    uids = {host.uid()}
    if host.uid() == 0 and str(env.get("SUDO_UID", "")).isdigit():
        uids.add(int(env["SUDO_UID"]))
    return uids


def ancestors(host, table=None):
    """This updater and every parent of it (never stopped)."""
    table = table if table is not None else host.procs()
    parent = {p: pp for p, pp, _u, _c in table}
    out, cur = set(), host.me
    for _ in range(64):
        out.add(cur)
        cur = parent.get(cur)
        if not cur or cur in out:
            break
    return out


def tunnel_pid():
    try:
        from . import tunnel
        st = tunnel.read_status()
        return int(st.get("pid") or 0) or None
    except Exception:  # noqa: BLE001 - no tunnel status is fine
        return None


def nimlab_procs(host, env=None, tpid=None):
    """[(pid, ppid, kind, cmd)] for Nim Lab processes we may stop."""
    table = host.procs()
    skip = ancestors(host, table)
    uids = allowed_uids(host, env)
    out = []
    for pid, ppid, uid, cmd in table:
        if pid in skip or uid not in uids:
            continue
        k = kind_of(cmd, tpid, pid)
        if k:
            out.append((pid, ppid, k, cmd[:200]))
    return out


# ---------------------------------------------------------------------------
# the updater
# ---------------------------------------------------------------------------
class UpdateError(Exception):
    pass


class Updater:
    def __init__(self, host=None, mgr=None, out=print, env=None, service_mod=None):
        from . import service as S
        self.S = service_mod or S
        self.host = host or Host()
        self.env = os.environ if env is None else env
        self.mgr = mgr
        self.out = out
        self.tpid = None
        self.had_supervisor = False  # a supervisor ran before: start it again
        self.stopped = []

    # -- helpers --------------------------------------------------------
    def say(self, s=""):
        self.out(s)

    def manager(self):
        if self.mgr is None:
            self.mgr = self.S.Manager(env=self.env)
        return self.mgr

    def backends(self):
        """Respawners that are installed here: ['termux', 'systemd-user', 'systemd-system', 'builtin']."""
        S, h, out = self.S, self.host, []
        if h.which("sv") and h.exists(os.path.join(S.termux_service_dir(self.env), "run")):
            out.append("termux")
        if h.which("systemctl"):
            if h.exists(S.unit_path(self.env)):
                out.append("systemd-user")
            if h.exists(S.SYSTEM_UNIT_PATH):
                out.append("systemd-system")
        out.append("builtin")
        return out

    def _systemctl(self, *args, system=False):
        if not system:
            return self.host.run(["systemctl", "--user", *args])
        if self.host.uid() == 0:
            return self.host.run(["systemctl", *args])
        return self.host.run(["sudo", "-n", "systemctl", *args])

    def procs(self):
        return nimlab_procs(self.host, self.env, self.tpid)

    def wait_gone(self, pids, seconds):
        end = self.host.now() + seconds
        left = set(pids)
        while left and self.host.now() < end:
            live = {p for p, *_ in self.procs()}
            left &= live
            if left:
                self.host.sleep(0.5)
        return left

    # -- 1. stop the respawners ---------------------------------------
    def disable_respawners(self):
        S = self.S
        for b in self.backends():
            if b == "termux":
                code, txt = self.host.run(["sv", "down", S.NAME])
                if code != 0:
                    raise UpdateError(f"sv down nimlab failed: {txt[-200:]}. Try: sv down nimlab, then run ./update.sh again.")
                self.say("  [ok] termux-services: auto-restart is off (sv down nimlab)")
            elif b in ("systemd-user", "systemd-system"):
                system = b == "systemd-system"
                code, txt = self._systemctl("stop", S.NAME, system=system)
                if code != 0:
                    if system:
                        raise UpdateError("The system-wide service needs root to stop: run sudo systemctl stop nimlab, "
                                          "then ./update.sh again (or: sudo ./update.sh).")
                    raise UpdateError(f"systemctl --user stop nimlab failed: {txt[-200:]}")
                self.say(f"  [ok] systemd ({'system' if system else 'user'} unit): stopped")
            elif b == "builtin":
                pid = self._pidfile_pid()
                if pid:
                    self._term([pid])
                    left = self.wait_gone([pid], SUPERVISOR_WAIT)
                    if left:
                        self._kill_verified(left)
                    self.say(f"  [ok] built-in supervisor stopped (pid {pid})")
        # any other supervisor (a second copy, one started by hand)
        sups = [p for p, _pp, k, _c in self.procs() if k == "supervisor"]
        if sups:
            self._term(sups)
            left = self.wait_gone(sups, SUPERVISOR_WAIT)
            if left:
                self._kill_verified(left)
            self.say(f"  [ok] stopped {len(sups)} more supervisor process(es)")

    def _pidfile_pid(self):
        try:
            pid = int(open(self.S.pid_path()).read().strip())
        except (OSError, ValueError):
            return None
        for p, _pp, k, _c in self.procs():
            if p == pid and k == "supervisor":
                return pid
        return None

    def _term(self, pids):
        for pid in pids:
            try:
                self.host.kill(pid, signal.SIGTERM)
                self.stopped.append(pid)
            except OSError:
                pass

    def _kill_verified(self, pids):
        """SIGKILL only pids that still run a Nim Lab command (pid reuse)."""
        cur = {p: k for p, _pp, k, _c in self.procs()}
        for pid in pids:
            if pid in cur:
                try:
                    self.host.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

    # -- 2. stop what is left -----------------------------------------
    def clean(self):
        seen = set()
        for rnd in range(1, CLEAN_ROUNDS + 1):
            found = self.procs()
            if not found:
                return True
            new = [f for f in found if f[0] not in seen]
            if rnd > 1 and new:
                parents = {pp for _p, pp, _k, _c in new}
                self.say(f"  [!] {len(new)} new Nim Lab process(es) appeared (started by pid "
                         f"{', '.join(str(p) for p in sorted(parents))})")
            seen |= {f[0] for f in found}
            sups = [p for p, _pp, k, _c in found if k == "supervisor"]
            rest = [p for p, _pp, k, _c in found if k != "supervisor"]
            if sups:
                self._term(sups)
                self._kill_verified(self.wait_gone(sups, SUPERVISOR_WAIT))
            if rest:
                self._term(rest)
                self._kill_verified(self.wait_gone(rest, CHILD_WAIT))
            self.host.sleep(1.0)
        left = self.procs()
        if left:
            lines = [f"    pid {p} (parent {pp}) {k}: {c[:100]}" for p, pp, k, c in left]
            raise UpdateError("Nim Lab processes keep coming back after " + str(CLEAN_ROUNDS) +
                              " rounds, so something outside Nim Lab restarts them:\n" + "\n".join(lines) +
                              "\n  Check: sv status nimlab; systemctl --user status nimlab; crontab -l; "
                              "~/.termux/boot/. Nothing was restarted.")
        return True

    def clear_stale(self):
        S, removed = self.S, []
        p = S.pid_path()
        try:
            pid = int(open(p).read().strip())
        except (OSError, ValueError):
            pid = None
        if pid is not None and not any(x[0] == pid for x in self.procs()):
            try:
                os.remove(p)
                removed.append("supervisor.pid")
            except OSError:
                pass
        try:
            S.write_state(running=False, children={}, cooldown_until={}, held={})
        except Exception:  # noqa: BLE001
            pass
        try:
            from . import tunnel
            st = tunnel.read_status()
            if st.get("pid") and not any(x[0] == st.get("pid") for x in self.procs()):
                tunnel.write_status(state="stopped", pid=None)
        except Exception:  # noqa: BLE001
            pass
        return removed

    # -- 3. start ------------------------------------------------------
    def start(self):
        bs = self.backends()
        S = self.S
        if "termux" in bs:
            code, txt = self.host.run(["sv", "up", S.NAME])
            return code == 0, "sv up nimlab" + ("" if code == 0 else f": {txt[-200:]}")
        if "systemd-system" in bs:
            code, txt = self._systemctl("start", S.NAME, system=True)
            return code == 0, "systemctl start nimlab" + ("" if code == 0 else f": {txt[-200:]}")
        if "systemd-user" in bs:
            code, txt = self._systemctl("start", S.NAME)
            return code == 0, "systemctl --user start nimlab" + ("" if code == 0 else f": {txt[-200:]}")
        if S.settings().get("backend") == "builtin" or self.had_supervisor:
            mgr = self.manager()
            mgr.backend = "builtin"
            ok, lines = mgr._start()
            return ok, " ".join(lines)
        return None, "no background service is installed"

    # -- 4. health -----------------------------------------------------
    def expected(self):
        S = self.S
        sv = S.settings()
        want = {"supervisor", "serve"}
        if sv.get("telegram"):
            want.add("telegram")
        if sv.get("scheduler", True):
            want.add("scheduler")
        return want

    def health(self, wait=HEALTH_WAIT):
        """-> (ok, [(ok, text)]). Waits up to `wait` seconds for the parts."""
        end = self.host.now() + wait
        rows = []
        while True:
            rows = self.health_rows()
            if all(ok for ok, _t in rows) or self.host.now() >= end:
                break
            self.host.sleep(2)
        if all(ok for ok, _t in rows):
            before = {(p, k) for p, _pp, k, _c in self.procs()}
            self.host.sleep(STABLE_WAIT)
            after = {(p, k) for p, _pp, k, _c in self.procs()}
            same = before == after
            rows.append((same, "stable: the same processes " + str(STABLE_WAIT) + " s later" if same else
                         "not stable: processes changed within a few seconds (a part is crash-looping; "
                         "see nimlab service logs)"))
        return all(ok for ok, _t in rows), rows

    def health_rows(self):
        found = self.procs()
        count = {k: sum(1 for _p, _pp, kk, _c in found if kk == k) for k in KINDS}
        rows = []
        for k in ("supervisor", "serve", "telegram", "scheduler"):
            if k in self.expected():
                n = count[k]
                rows.append((n == 1, f"{k}: {'running' if n == 1 else ('not running' if n == 0 else f'{n} copies')}"))
            elif count[k]:
                rows.append((False, f"{k}: {count[k]} running but it is turned off"))
        rows += endpoint_rows(self.host)
        return rows

    # -- the whole run -------------------------------------------------
    def run(self, stop_only=False, start=True, wait=HEALTH_WAIT):
        from . import __version__
        lock = UpdateLock()
        holder = lock.acquire()
        if holder is not True:
            self.say(f"[x] Another update is running (pid {holder}). Wait for it to finish.")
            return 2
        try:
            self.say(f"Nim Lab update -> v{__version__} in {config.PROJECT_DIR}")
            self.tpid = tunnel_pid()
            self.had_supervisor = any(k == "supervisor" for _p, _pp, k, _c in self.procs())
            self.say("1. Stopping auto-restart and the service")
            self.disable_respawners()
            self.say("2. Stopping leftover Nim Lab processes")
            n0 = len(self.procs())
            self.clean()
            self.say(f"  [ok] none left ({n0} were still running)" if n0 else "  [ok] none left")
            removed = self.clear_stale()
            if removed:
                self.say("  [ok] removed stale " + ", ".join(removed))
            notes = deps_note()
            for n in notes:
                self.say("  [!] " + n)
            record(version=__version__, result="stopped" if stop_only else "cleaned")
            if stop_only:
                self.say("\nStopped. Unzip the release now, then run ./update.sh to start it again.")
                return 0
            if not start:
                self.say("\nCleaned; not started (--no-start).")
                return 0
            self.say("3. Starting")
            ok, how = self.start()
            if ok is None:
                self.say("  [ok] No background service is installed, so nothing was started.")
                self.say("\nUpdated. Start it from the menu (./start.sh) or install the service: nimlab service install")
                record(version=__version__, result="updated, no service")
                return 0
            if not ok:
                self.say(f"  [x] {how}")
                self.say("\nNOT STARTED. Look at: nimlab service logs")
                record(version=__version__, result="start failed")
                return 1
            self.say(f"  [ok] {how}")
            self.say("4. Health check (up to a minute)")
            good, rows = self.health(wait)
            for ok_, text in rows:
                self.say(("  [ok] " if ok_ else "  [x]  ") + text)
            if good:
                self.say("\nGOOD TO GO. Nim Lab v" + __version__ + " is running.")
            else:
                self.say("\nNOT HEALTHY: see the [x] lines above. Next: nimlab service logs, then nimlab doctor "
                         "(or the Health menu: ./start.sh, then 7).")
            record(version=__version__, result="healthy" if good else "unhealthy")
            return 0 if good else 1
        except UpdateError as e:
            self.say(f"  [x] {e}")
            self.say("\nUPDATE STOPPED. Nothing was restarted.")
            record(result="failed", error=str(e)[:300])
            return 1
        finally:
            lock.release()


def endpoint_rows(host, srv=None):
    """The local server answers /health and /v1/models with its own key."""
    try:
        from . import server as S
        srv = srv or S.load_settings()
    except Exception as e:  # noqa: BLE001
        return [(False, f"server settings unreadable: {e}")]
    port = srv.get("port") or 8765
    base = f"http://127.0.0.1:{port}"
    code = host.http(base + "/health")
    rows = [(code == 200, f"server answers on port {port}" if code == 200 else
             f"server does not answer on port {port} (" + (f"HTTP {code}" if code else "no connection") + ")")]
    if code == 200:
        code = host.http(base + "/v1/models", srv.get("api_key") or "")
        rows.append((code == 200, "/v1/models with the server key: 200" if code == 200 else
                     f"/v1/models with the server key: {code or 'no answer'}"))
    return rows


# ---------------------------------------------------------------------------
# lock, record, deps
# ---------------------------------------------------------------------------
class UpdateLock:
    def __init__(self, path=None):
        from . import service as S
        self.path = path or os.path.join(S.state_dir(), "update.lock")
        self.f = None

    def acquire(self):
        """True, or the pid that holds it."""
        import fcntl
        f = open(self.path, "a+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.seek(0)
            holder = f.read().strip() or "?"
            f.close()
            return holder
        f.seek(0)
        f.truncate()
        f.write(str(os.getpid()))
        f.flush()
        self.f = f
        return True

    def release(self):
        if self.f:
            import fcntl
            try:
                fcntl.flock(self.f, fcntl.LOCK_UN)
            finally:
                self.f.close()
                self.f = None


def record_path():
    from . import service as S
    return os.path.join(S.state_dir(), "update.json")


def read_record():
    d = config.load_json(record_path(), None)
    return d if isinstance(d, dict) else {}


def record(**kw):
    d = read_record()
    d.update(kw, at=config.timestamp())
    if "error" not in kw:
        d.pop("error", None)
    try:
        with open(record_path(), "w") as f:
            json.dump(d, f, indent=2)
    except OSError:
        pass


def req_hash():
    try:
        with open(os.path.join(config.PROJECT_DIR, "requirements.txt"), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return ""


def deps_note():
    """A note when requirements.txt changed since the last update."""
    h, old = req_hash(), read_record().get("requirements")
    record(requirements=h)
    if old and h and old != h:
        return ["requirements.txt changed in this release: run ./start.sh install once to add the new packages."]
    return []


def cmd_update(args):
    u = Updater()
    return u.run(stop_only=getattr(args, "stop", False), start=not getattr(args, "no_start", False),
                 wait=getattr(args, "wait", None) or HEALTH_WAIT)


def add_parser(sub):
    p = sub.add_parser("update", help="After unzipping a release: stop, clean up, restart once, health check")
    p.add_argument("--stop", action="store_true", help="Only stop and clean up (run before unzipping)")
    p.add_argument("--no-start", action="store_true", help="Clean up but do not start the service")
    p.add_argument("--wait", type=int, default=None, help="Seconds to wait for the health check (default 60)")
    p.set_defaults(fn=cmd_update)
    return p


if __name__ == "__main__":
    sys.exit(cmd_update(None))
