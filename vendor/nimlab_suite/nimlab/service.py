"""Keep the endpoint running: a supervised background service.

`nimlab service run` is the supervisor. It starts `nimlab serve start`
(with the tunnel when one is set to auto-start) and, when the Telegram bot
is set to run with the service, `nimlab telegram run`, writes their output
to a rotating log, and restarts a child that exits with a growing delay
(2 s, 4 s, ... 60 s). Five crashes inside two minutes count as a crash
loop: it waits five minutes, then tries again. On Termux it holds
`termux-wake-lock` while it runs.

What starts the supervisor (`nimlab service install`):
    termux    termux-services (runit): $PREFIX/var/service/nimlab/run,
              sv-enable, sv up / down. Start on boot with Termux:Boot
              (~/.termux/boot/nimlab).
    systemd   a user unit ~/.config/systemd/user/nimlab.service with
              Restart=on-failure and a growing RestartSec.
    builtin   anywhere: the supervisor itself in the background (nohup),
              PID file data/service/supervisor.pid.

No service file holds a secret: the NVIDIA key is read from ~/.nimlab_env
and the other keys from ~/.config/nimlab/ when the service starts.
"""

import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time

from . import config, store

NAME = "nimlab"
BACKENDS = ("termux", "systemd", "builtin")
LOG_MAX = 1_000_000
LOG_KEEP = 5
CRASH_WINDOW = 120
CRASH_LIMIT = 5
COOLDOWN = 300
MAX_DELAY = 60
EXIT_WAIT = 75        # another copy already does this child's job: idle, look again later
EXIT_CONFIG = 78      # a configuration problem: do not restart until the config changes
WAIT_RECHECK = 300
CONFIG_RECHECK = 600


def env_of(env=None):
    return os.environ if env is None else env


def home(env=None):
    e = env_of(env)
    return e.get("HOME") or os.path.expanduser("~")


def is_termux(env=None):
    from .shortcut import is_termux as t
    return t(env)


def state_dir():
    d = os.path.join(store.data_dir(), "service")
    os.makedirs(d, exist_ok=True)
    return d


def state_path():
    return os.path.join(state_dir(), "state.json")


def pid_path():
    return os.path.join(state_dir(), "supervisor.pid")


def log_path():
    return os.path.join(state_dir(), "service.log")


def read_state():
    st = config.load_json(state_path(), None)
    return st if isinstance(st, dict) else {}


def write_state(**kw):
    st = read_state()
    st.update(kw)
    try:
        config.save_json(state_path(), st)
    except OSError:
        pass
    return st


def settings(cluster=None):
    c = config.load_cluster_config() if cluster is None else cluster
    sv = c.setdefault("service_settings", {})
    sv.setdefault("backend", "auto")
    sv.setdefault("telegram", False)
    sv.setdefault("scheduler", True)            # 3.8.0: run the job scheduler as a child
    sv.setdefault("wake_lock", is_termux())     # battery wake lock: Termux only (3.7.4)
    return sv


def save_settings(sv):
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    cfg["service_settings"] = sv
    config.save_json(config.CLUSTER_CONFIG, cfg)


# ---------------------------------------------------------------------------
# rotating log
# ---------------------------------------------------------------------------
class RotatingLog:
    def __init__(self, path, max_bytes=LOG_MAX, keep=LOG_KEEP):
        self.path, self.max, self.keep = path, max_bytes, keep
        self.lock = threading.Lock()

    def _rotate(self):
        for i in range(self.keep - 1, 0, -1):
            src = f"{self.path}.{i}"
            if os.path.exists(src):
                os.replace(src, f"{self.path}.{i + 1}")
        if os.path.exists(self.path):
            os.replace(self.path, f"{self.path}.1")
        extra = f"{self.path}.{self.keep + 1}"
        if os.path.exists(extra):
            os.unlink(extra)

    def write(self, line, tag=""):
        from .selfadmin import scrub
        line = scrub(line.rstrip("\n"))
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            try:
                if os.path.exists(self.path) and os.path.getsize(self.path) > self.max:
                    self._rotate()
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(f"{stamp} {tag}{line}\n")
            except OSError:
                pass


def log_tail(n=40):
    try:
        with open(log_path(), encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# the supervisor
# ---------------------------------------------------------------------------
def child_commands(cluster=None):
    py = sys.executable
    cmds = {"serve": [py, "-m", "nimlab", "serve", "start"]}
    if settings(cluster).get("telegram"):
        cmds["telegram"] = [py, "-m", "nimlab", "telegram", "run"]
    # 3.8.0: the job scheduler (heartbeat and jobs) runs next to serve and telegram
    if settings(cluster).get("scheduler", True):
        cmds["scheduler"] = [py, "-m", "nimlab", "scheduler", "run"]
    return cmds


def runtime_env():
    """The children's environment: secrets come from the private files at
    run time (~/.nimlab_env for the NVIDIA key), never from a service file."""
    env = dict(os.environ)
    env["NIMLAB_COLOR"] = "0"
    env["NIMLAB_SERVICE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    try:
        from . import core
        k = core.load_api_key() if hasattr(core, "load_api_key") else None
        if k and not env.get("NVIDIA_API_KEY"):
            env["NVIDIA_API_KEY"] = k
    except Exception:  # noqa: BLE001
        pass
    if not env.get("NVIDIA_API_KEY"):
        try:
            with open(os.path.join(home(), ".nimlab_env"), encoding="utf-8") as f:
                for line in f:
                    line = line.strip().removeprefix("export ")
                    if line.startswith(("NVIDIA_API_KEY=", "NGC_API_KEY=")):
                        env[line.split("=", 1)[0]] = line.split("=", 1)[1].strip().strip("'\"")
        except OSError:
            pass
    return env


class SupervisorLock:
    """Only one supervisor per data folder (3.7.1). The phone ran two at
    once (termux-services and the built-in one): one held port 8765 and
    polled Telegram, the other crash-looped serve and restarted it during
    the first one's cooldown. flock is released by the kernel when the
    process dies, so a stale pid file never blocks a start."""

    def __init__(self, path=None):
        self.path = path or os.path.join(state_dir(), "supervisor.lock")
        self.f = None

    def acquire(self):
        import fcntl
        f = open(self.path, "a+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False
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

    def holder(self):
        """pid holding the lock, or None when no supervisor runs."""
        if self.f:
            return os.getpid()
        if self.acquire():
            self.release()
            return None
        try:
            return int(open(self.path).read().strip() or 0) or -1
        except (OSError, ValueError):
            return -1


ERROR_WORDS = ("[x]", "[!]", "[config]", "error", "Error", "failed", "Traceback", "refused", "Conflict",
               "already running", "timed out", "denied", "Exception")


class Supervisor:
    def __init__(self, cmds=None, log=None, popen=subprocess.Popen, sleep=time.sleep, clock=time.time,
                 crash_window=CRASH_WINDOW, crash_limit=CRASH_LIMIT, cooldown=COOLDOWN, max_delay=MAX_DELAY,
                 env=None, wake=None, config_mtime=None, commands_fn=None):
        # 3.7.4: with no fixed cmds the supervisor follows config_cluster.json,
        # so a child turned on after it started (Telegram set up after the
        # service step) starts without a restart, and one turned off stops.
        self.commands_fn = commands_fn or (None if cmds else child_commands)
        self.cmds = cmds or self.commands_fn()
        self.log = log or RotatingLog(log_path())
        self.popen, self.sleep, self.clock = popen, sleep, clock
        self.window, self.limit, self.cooldown, self.max_delay = crash_window, crash_limit, cooldown, max_delay
        self.env = env or runtime_env()
        self.wake = wake if wake is not None else is_termux()
        self.stop_event = threading.Event()
        self.procs = {}
        self.restarts = {k: 0 for k in self.cmds}
        self.crashes = {k: [] for k in self.cmds}
        self.last_line = {k: "" for k in self.cmds}     # last error-looking output line per child
        self.held = {}                                   # child -> {"why", "code", "line", "until"}
        self.wait_until = {}
        self.config_mtime = config_mtime or _config_mtime
        self._seen_mtime = self.config_mtime()
        self.parent_gone = lambda: False

    def reconcile(self):
        """Start children newly configured, stop ones no longer configured.
        Runs when config_cluster.json changed. -> (added, removed)."""
        if not self.commands_fn:
            return [], []
        m = self.config_mtime()
        if m == self._seen_mtime:
            return [], []
        self._seen_mtime = m
        try:
            want = self.commands_fn()
        except Exception as e:  # noqa: BLE001 - a half-written config must not stop the supervisor
            self.log.write(f"could not read the configuration ({type(e).__name__}); keeping the current children",
                           "[supervisor] ")
            return [], []
        added = [k for k in want if k not in self.cmds]
        removed = [k for k in self.cmds if k not in want]
        for name in removed:
            p = self.procs.pop(name, None)
            if p is not None and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill()
            for d in (self.cmds, self.restarts, self.crashes, self.last_line, self.held, self.wait_until):
                d.pop(name, None)
            self.log.write(f"configuration changed: {name} is no longer configured; stopped it", "[supervisor] ")
        for name in added:
            self.cmds[name] = want[name]
            self.restarts[name] = 0
            self.crashes[name] = []
            self.last_line[name] = ""
            self.wait_until[name] = 0
            self.log.write(f"configuration changed: {name} is now configured; starting it", "[supervisor] ")
        if added or removed:
            self._save()
        return added, removed

    def _pump(self, name, proc):
        for line in proc.stdout:
            self.log.write(line, f"[{name}] ")
            t = line.strip()
            if t and any(w in t for w in ERROR_WORDS):
                from .selfadmin import scrub
                self.last_line[name] = scrub(t)[:240]

    def _spawn(self, name):
        p = self.popen(self.cmds[name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                       text=True, bufsize=1, env=self.env, cwd=config.PROJECT_DIR)
        self.procs[name] = p
        self.held.pop(name, None)
        threading.Thread(target=self._pump, args=(name, p), daemon=True).start()
        self.log.write(f"started {name} (pid {p.pid})", "[supervisor] ")
        self._save()
        return p

    def _save(self, **kw):
        live = {k: p.pid for k, p in self.procs.items() if p is not None and p.poll() is None}
        write_state(supervisor_pid=os.getpid(), children=live, configured=list(self.cmds),
                    restarts=sum(self.restarts.values()), restarts_by_child=dict(self.restarts),
                    held={k: dict(v) for k, v in self.held.items()},
                    cooldown_until={k: v for k, v in self.wait_until.items() if v > self.clock()}, **kw)

    def _wake(self, on):
        if not self.wake:
            return
        exe = shutil.which("termux-wake-lock" if on else "termux-wake-unlock")
        if exe:
            try:
                subprocess.run([exe], timeout=10, capture_output=True)
            except (OSError, subprocess.TimeoutExpired):
                pass

    def delay_for(self, name):
        n = len(self.crashes[name])
        return min(self.max_delay, 2 ** max(1, n))

    def handle_exit(self, name, code):
        """A child exited: returns the seconds to wait before restarting it
        (None = do not restart until the configuration changes)."""
        now = self.clock()
        line = self.last_line.get(name, "")
        self.last_line[name] = ""
        last = {"child": name, "code": code, "at": config.timestamp(), "line": line}
        if code == EXIT_CONFIG:
            self.held[name] = {"why": "config error", "code": code, "line": line, "at": config.timestamp(),
                               "mtime": self.config_mtime()}
            self.log.write(f"{name} stopped with a configuration problem (code {code}): {line or 'see above'}. "
                           "Not restarting it until the configuration changes (or: nimlab service restart).",
                           "[supervisor] ")
            self._save(last_exit=last)
            return None
        if code == EXIT_WAIT:
            self.held[name] = {"why": "another copy runs", "code": code, "line": line, "at": config.timestamp()}
            self.log.write(f"{name}: another copy already runs ({line or 'see above'}); idle, looking again in "
                           f"{WAIT_RECHECK} s. nimlab service status lists stray copies.", "[supervisor] ")
            self._save(last_exit=last)
            return WAIT_RECHECK
        c = [t for t in self.crashes[name] if now - t < self.window] + [now]
        self.crashes[name] = c
        self.restarts[name] += 1
        if len(c) >= self.limit:
            self.log.write(f"{name} crashed {len(c)} times in {self.window} s: crash loop, waiting "
                           f"{self.cooldown} s (last: code {code}{': ' + line if line else ''})", "[supervisor] ")
            self.crashes[name] = []
            self.held[name] = {"why": "crash loop", "code": code, "line": line, "at": config.timestamp(),
                               "until": now + self.cooldown}
            self._save(last_exit=last, crash_loop={"child": name, "at": config.timestamp(), "code": code,
                                                   "line": line, "until": now + self.cooldown})
            return self.cooldown
        d = self.delay_for(name)
        self.log.write(f"{name} exited with code {code}; restarting in {d} s", "[supervisor] ")
        self._save(last_exit=last)
        return d

    def step(self):
        """One pass: reap exited children, start the ones whose wait is over.
        A child held for a config error starts again only when
        config_cluster.json changed (or after CONFIG_RECHECK)."""
        now = self.clock()
        self.reconcile()
        for name in list(self.cmds):
            p = self.procs.get(name)
            if p is not None:
                code = p.poll()
                if code is None:
                    continue
                self.procs[name] = None
                d = self.handle_exit(name, code)
                self.wait_until[name] = float("inf") if d is None else now + d
                self._save()
                continue
            h = self.held.get(name) or {}
            if self.wait_until.get(name, 0) == float("inf"):
                changed = h.get("mtime") != self.config_mtime()
                if changed or now - h.get("t", now) > CONFIG_RECHECK:
                    self.log.write(f"configuration changed: starting {name} again", "[supervisor] ")
                    self.wait_until[name] = 0
                else:
                    h.setdefault("t", now)
                    continue
            if now >= self.wait_until.get(name, 0):
                self._spawn(name)

    def run(self, max_loops=None):
        prev = read_state()
        # a cooldown survives a supervisor restart (runit restarts us at once)
        for k, until in (prev.get("cooldown_until") or {}).items():
            if k in self.cmds and until > self.clock():
                self.wait_until[k] = until
                self.log.write(f"{k} is cooling down after a crash loop: next start in "
                               f"{int(until - self.clock())} s", "[supervisor] ")
        write_state(started_at=config.timestamp(), started_ts=time.time(), restarts=0, crash_loop=None,
                    last_exit=None, running=True, held={})
        self._wake(True)
        try:
            loops = 0
            while not self.stop_event.is_set():
                loops += 1
                if max_loops and loops > max_loops:
                    break
                self.step()
                if self.parent_gone():
                    self.log.write("the runit wrapper that started this supervisor is gone; stopping so runit's "
                                   "new copy takes over", "[supervisor] ")
                    break
                self.sleep(1)
        finally:
            self.shutdown()

    def shutdown(self):
        for name, p in list(self.procs.items()):
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill()
        self.procs = {}
        self._wake(False)
        write_state(running=False, stopped_at=config.timestamp(), children={},
                    cooldown_until={k: v for k, v in self.wait_until.items() if v != float("inf") and
                                    v > self.clock()})


def _config_mtime():
    try:
        return os.path.getmtime(config.CLUSTER_CONFIG)
    except OSError:
        return None


LOCK_GRACE = 8          # seconds a lock loser waits for a stopping supervisor
LOCK_BACKOFF = 60       # extra wait under runit before exiting (slow respawn)
EXIT_LOCKED = 0         # a lock loser is not an error


def under_runit(env=None, ppid=None):
    """True when runit (termux-services) runs this supervisor: its run file
    sets NIMLAB_RUNIT=1, or the parent process is runsv."""
    e = env_of(env)
    if e.get("NIMLAB_RUNIT") == "1":
        return True
    try:
        pp = ppid or os.getppid()
        with open(f"/proc/{pp}/comm") as f:
            name = f.read().strip()
        if name == "runsv":
            return True
        if name in ("bash", "sh"):           # start.sh between runsv and python
            with open(f"/proc/{pp}/stat") as f:
                gpp = int(f.read().rsplit(")", 1)[1].split()[1])
            with open(f"/proc/{gpp}/comm") as f:
                return f.read().strip() == "runsv"
    except (OSError, ValueError, IndexError):
        pass
    return False


def _told_recently(window=3600, clock=time.time):
    """Log the 'another supervisor runs' line at most once an hour."""
    p = os.path.join(state_dir(), "lock_loser.json")
    now = clock()
    last = config.load_json(p, {}) or {}
    if isinstance(last, dict) and last.get("at") is not None and now - float(last["at"]) < window:
        return True
    try:
        config.save_json(p, {"at": now})
    except OSError:
        pass
    return False


def supervise(lock=None, wait=time.sleep):
    lock = lock or SupervisorLock()
    log = RotatingLog(log_path())
    stopping = threading.Event()

    def stop(_sig, _frm):
        stopping.set()
    for sig in ("SIGTERM", "SIGINT", "SIGHUP"):
        if hasattr(signal, sig):
            signal.signal(getattr(signal, sig), stop)
    # 3.7.4: a supervisor that cannot get the lock exits instead of idling
    # forever. The phone showed three idle extras after setup (one through
    # the runit wrapper). It waits LOCK_GRACE seconds first, so a restart
    # where the old one is still shutting down works; under runit it then
    # waits LOCK_BACKOFF more before exiting, so runit's respawn is slow and
    # the log gets one line, not a tight loop.
    waited = 0
    while not lock.acquire():
        if stopping.is_set():
            return 0
        if waited >= LOCK_GRACE:
            holder = lock.holder()
            if not _told_recently():
                log.write(f"another Nim Lab supervisor already runs (pid {holder}); this one (pid {os.getpid()}) "
                          "exits. Only one runs at a time: nimlab service status", "[supervisor] ")
            if under_runit():
                waited = 0
                while waited < LOCK_BACKOFF and not stopping.is_set():
                    wait(1)
                    waited += 1
                    if waited % 5 == 0 and not lock.holder():
                        break           # the other one stopped: take over at once
                if not stopping.is_set() and lock.acquire():
                    break
            return EXIT_LOCKED if not under_runit() else 0
        wait(1)
        waited += 1
    sup = Supervisor()
    if stopping.is_set():
        lock.release()
        return 0
    signal.signal(signal.SIGTERM, lambda *_: sup.stop_event.set())
    signal.signal(signal.SIGINT, lambda *_: sup.stop_event.set())
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, lambda *_: sup.stop_event.set())
    with open(pid_path(), "w") as f:
        f.write(str(os.getpid()))
    if under_runit():
        # runit signals its direct child; if a wrapper shell died and left us
        # behind, stop instead of holding the lock as an orphan
        parent = os.getppid()
        sup.parent_gone = lambda: os.getppid() != parent
    try:
        sup.run()
    finally:
        try:
            if open(pid_path()).read().strip() == str(os.getpid()):
                os.unlink(pid_path())
        except OSError:
            pass
        lock.release()
    return 0


# ---------------------------------------------------------------------------
# stray copies
# ---------------------------------------------------------------------------
STRAY_PATTERNS = (("supervisor", ("nimlab", "service", "run")), ("serve", ("nimlab", "serve", "start")),
                  ("telegram", ("nimlab", "telegram", "run")), ("scheduler", ("nimlab", "scheduler", "run")))


def find_processes(run=None):
    """Every Nim Lab supervisor / serve / telegram-run process on this
    device: [(pid, kind, cmdline)]. Reads /proc (no pgrep needed)."""
    out = []
    me = os.getpid()
    if run is not None:
        lines = run()
    else:
        lines = []
        try:
            for d in os.listdir("/proc"):
                if not d.isdigit() or int(d) == me:
                    continue
                try:
                    with open(f"/proc/{d}/cmdline", "rb") as f:
                        cmd = f.read().replace(b"\0", b" ").decode("utf-8", "replace").strip()
                except OSError:
                    continue
                if cmd:
                    lines.append((int(d), cmd))
        except OSError:
            return out
    for pid, cmd in lines:
        words = cmd.replace("/", " ").split()
        for kind, pat in STRAY_PATTERNS:
            if all(w in words for w in pat) or (kind == "supervisor" and "start.sh" in cmd and
                                                 "service run" in cmd):
                out.append((pid, kind, cmd[:160]))
                break
    return out


def strays(st=None, procs=None):
    """Processes that are not the running supervisor or its children."""
    st = st if st is not None else read_state()
    holder = SupervisorLock().holder()
    mine = {holder} | set((st.get("children") or {}).values()) if holder else set()
    procs = find_processes() if procs is None else procs
    out = []
    for pid, kind, cmd in procs:
        if pid in mine:
            continue
        # the runit wrapper (start.sh service run) of the running supervisor
        if kind == "supervisor" and holder and _is_ancestor(pid, holder):
            continue
        out.append((pid, kind, cmd))
    return out


def _is_ancestor(pid, child):
    try:
        cur = child
        for _ in range(8):
            with open(f"/proc/{cur}/stat") as f:
                ppid = int(f.read().rsplit(")", 1)[1].split()[1])
            if ppid == pid:
                return True
            if ppid <= 1:
                return False
            cur = ppid
    except (OSError, ValueError, IndexError):
        return False
    return False


def stop_pids(pids, kill=os.kill, sleep=time.sleep, wait=15):
    done = []
    for pid in pids:
        try:
            kill(pid, signal.SIGTERM)
            done.append(pid)
        except OSError:
            pass
    # 3.8.2: wait (bounded) for them to exit before SIGKILL. A supervisor
    # needs several seconds to stop its own children; killing it after 1.5 s
    # orphaned them, which is why cleanup used to need two or three runs.
    left = list(done)
    for _ in range(int(wait / 0.5)):
        if not left:
            break
        sleep(0.5)
        still = []
        for pid in left:
            try:
                kill(pid, 0)
                still.append(pid)
            except OSError:
                pass
        left = still
    for pid in left:
        try:
            kill(pid, signal.SIGKILL)
        except OSError:
            pass
    return done


# ---------------------------------------------------------------------------
# backends
# ---------------------------------------------------------------------------
def start_cmd(env=None):
    """How a service file starts the supervisor (paths only, no secrets)."""
    from .shortcut import start_script
    e = env_of(env)
    bash = os.path.join(e["PREFIX"], "bin", "bash") if is_termux(e) and e.get("PREFIX") else "/bin/bash"
    return [bash, start_script(), "service", "run"]


def pick_backend(want="auto", env=None, which=shutil.which, run=subprocess.run):
    e = env_of(env)
    if want in BACKENDS:
        return want
    if is_termux(e):
        return "termux"
    if which("systemctl"):
        try:
            r = run(["systemctl", "--user", "show-environment"], capture_output=True, timeout=10)
            if r.returncode == 0:
                return "systemd"
        except (OSError, subprocess.TimeoutExpired):
            pass
    return "builtin"


def termux_service_dir(env=None):
    e = env_of(env)
    return os.path.join(e.get("PREFIX", "/data/data/com.termux/files/usr"), "var", "service", NAME)


def termux_files(env=None):
    e = env_of(env)
    sh = os.path.join(e.get("PREFIX", "/data/data/com.termux/files/usr"), "bin", "sh")
    cmd = " ".join(shlex.quote(x) for x in start_cmd(e))
    logdir = os.path.join(state_dir(), "runit")
    return {
        "run": (f"#!{sh}\n# nimlab service (runit). No secrets here: they are read at run time.\nexec 2>&1\n"
                f"export NIMLAB_RUNIT=1\nexec {cmd}\n"),
        "log/run": f"#!{sh}\nmkdir -p {shlex.quote(logdir)}\nexec svlogd -tt {shlex.quote(logdir)}\n",
    }


def boot_script(backend, env=None):
    e = env_of(env)
    sh = os.path.join(e.get("PREFIX", "/data/data/com.termux/files/usr"), "bin", "sh")
    if backend == "termux":
        body = "termux-wake-lock\n. \"$PREFIX/etc/profile\"\n"   # starts runsvdir, which starts nimlab
    else:
        from .shortcut import start_script
        body = f"termux-wake-lock\nbash {shlex.quote(start_script())} service start\n"
    return f"#!{sh}\n# Termux:Boot: start the nimlab service when the phone starts.\n{body}"


def boot_path(env=None):
    return os.path.join(home(env), ".termux", "boot", NAME)


def systemd_unit(env=None):
    cmd = " ".join(shlex.quote(x) for x in start_cmd(env))
    return ("[Unit]\n"
            "Description=NVIDIA NIM test lab endpoint (nimlab serve, tunnel, Telegram)\n"
            "After=network-online.target\n"
            "Wants=network-online.target\n"
            "StartLimitIntervalSec=600\n"
            "StartLimitBurst=10\n\n"
            "[Service]\n"
            "Type=simple\n"
            f"WorkingDirectory={config.PROJECT_DIR}\n"
            f"ExecStart={cmd}\n"
            "Restart=on-failure\n"
            "RestartSec=5\n"
            "RestartSteps=5\n"
            "RestartMaxDelaySec=120\n"
            "KillMode=mixed\n"
            "TimeoutStopSec=20\n"
            "Environment=NIMLAB_COLOR=0\n\n"
            "[Install]\n"
            "WantedBy=default.target\n")


SYSTEM_UNIT_PATH = "/etc/systemd/system/nimlab.service"


def _euid():
    return os.geteuid() if hasattr(os, "geteuid") else 1


def linger_on(user, run):
    """True when systemd linger is on for user (run is Manager.run-like)."""
    if not user or user == "$USER":
        return False
    if os.path.exists(f"/var/lib/systemd/linger/{user}"):
        return True
    code, out = run("loginctl", "show-user", user, "-p", "Linger")
    return code == 0 and out.strip().endswith("yes")


def system_unit(user, env=None):
    """A system-wide unit (sudo nimlab service install --system) that runs
    the supervisor as a regular user. Needs no linger."""
    text = systemd_unit(env)
    text = text.replace("[Service]\n", f"[Service]\nUser={user}\nEnvironment=HOME={os.path.expanduser('~' + user)}\n", 1)
    return text.replace("WantedBy=default.target", "WantedBy=multi-user.target")


def install_system(run, env=None, path=None):
    """-> (ok, lines). Writes /etc/systemd/system/nimlab.service for the user
    who ran sudo, then enables and starts it."""
    e = env_of(env)
    user = e.get("SUDO_USER")
    if _euid() != 0 or not user or user == "root":
        return False, ["[x] --system needs sudo from a regular user: sudo nimlab service install --system "
                       "(the unit runs as that user, never as root)"]
    p = path or SYSTEM_UNIT_PATH
    _write(p, system_unit(user, e), 0o644)
    lines = [f"[ok] System unit: {p} (runs as {user})"]
    for cmd in (("systemctl", "daemon-reload"), ("systemctl", "enable", "--now", NAME)):
        code, out = run(*cmd)
        if code != 0:
            return False, lines + [f"[x] {' '.join(cmd)} failed: {out[-300:]}"]
    lines.append("[ok] Enabled and started; it starts at boot. Logs: sudo journalctl -u nimlab -f. "
                 "Do not also install the user unit.")
    return True, lines


def unit_path(env=None):
    e = env_of(env)
    base = e.get("XDG_CONFIG_HOME") or os.path.join(home(e), ".config")
    return os.path.join(base, "systemd", "user", f"{NAME}.service")


def _write(path, text, mode=0o755):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(path, mode)


class Manager:
    """install / remove / start / stop / restart / status for one backend.
    `run` runs a command and returns (code, output); tests pass a fake."""

    def __init__(self, backend=None, env=None, run=None, which=shutil.which, ask=None):
        self.ask = ask
        self.env = env_of(env)
        self.which = which
        self._run = run or self._real_run
        sv = settings()
        self.backend = pick_backend(backend or sv.get("backend", "auto"), self.env, which)

    @staticmethod
    def _real_run(cmd, timeout=60):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout + r.stderr).strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return 127, str(e)

    def run(self, *cmd):
        return self._run(list(cmd))

    # -- install / remove ----------------------------------------------
    def install(self, boot=False):
        lines = []
        b = self.backend
        found = self.others()
        if found:
            lines.append("[!] Other Nim Lab copies are running:")
            lines += [f"    pid {pid or '-'}  {kind}: {what}" for pid, kind, what in found]
            if self.ask and self.ask("Stop them before installing?"):
                lines += self.cleanup(found)
            else:
                lines.append("    Stop them with: nimlab service cleanup")
        if b == "termux":
            if not self.which("sv") or not self.which("sv-enable"):
                lines.append("Installing termux-services: pkg install -y termux-services")
                code, out = self.run("pkg", "install", "-y", "termux-services")
                if code != 0:
                    return False, lines + [f"[x] pkg install termux-services failed: {out[-300:]}"]
                lines.append("[!] Close Termux completely (exit in every session) and open it again once, so the "
                             "service daemon starts. Then run: nimlab service start")
            d = termux_service_dir(self.env)
            for rel, text in termux_files(self.env).items():
                _write(os.path.join(d, rel), text)
            lines.append(f"[ok] Service files: {d}/run and log/run")
            code, out = self.run("sv", "status", NAME)
            if code == 0 and out.startswith("run:"):
                # already enabled and running under runit: nothing to start (3.7.4)
                lines.append("[ok] Already enabled and running under termux-services (sv status: run); "
                             "it picks up the new service files on its next restart.")
                sv = settings()
                sv["backend"] = b
                save_settings(sv)
                return True, lines + (self.enable_boot() if boot else [])
            code, out = self.run("sv-enable", NAME)
            lines.append("[ok] Enabled (sv-enable nimlab); it starts now and whenever Termux starts." if code == 0
                         else f"[!] sv-enable did not work yet ({out[-200:] or code}); after reopening Termux "
                              "run: nimlab service start")
        elif b == "systemd":
            if _euid() == 0:
                lines.append("[!] Running as root. Nim Lab is meant to run as a regular user (sudo adduser nimlab, "
                             "then run it as that user). For a system-wide unit that runs as a regular user, "
                             "run: sudo nimlab service install --system")
            p = unit_path(self.env)
            _write(p, systemd_unit(self.env), 0o644)
            lines.append(f"[ok] Unit file: {p}")
            for cmd in (("systemctl", "--user", "daemon-reload"), ("systemctl", "--user", "enable", "--now", NAME)):
                code, out = self.run(*cmd)
                if code != 0:
                    return False, lines + [f"[x] {' '.join(cmd)} failed: {out[-300:]}"]
            lines.append("[ok] Enabled and started (systemctl --user enable --now nimlab).")
            user = self.env.get("USER") or "$USER"
            if not linger_on(user, self.run):
                lines.append("[!] IMPORTANT on a VPS: a systemd user service stops when you log out and does not "
                             "start at boot until you turn on linger:")
                lines.append(f"      sudo loginctl enable-linger {user}")
            else:
                lines.append("[ok] Linger is on: it keeps running after you log out and starts at boot.")
        else:
            ok, msg = self.start(ask=self.ask)
            lines += msg
            if not ok:
                return False, lines
            lines.append("[ok] Running with the built-in supervisor. It does not start by itself after a reboot"
                         + (" unless you turn on start-on-boot (Termux:Boot)." if is_termux(self.env) else "."))
        sv = settings()
        sv["backend"] = b
        save_settings(sv)
        if boot:
            lines += self.enable_boot()
        return True, lines

    def enable_boot(self):
        if not is_termux(self.env):
            if self.backend == "systemd":
                return ["Start on boot: systemd starts it at login; add linger for boot (see above)."]
            return ["[!] Start on boot here needs systemd or cron (@reboot bash <folder>/start.sh service start)."]
        _write(boot_path(self.env), boot_script(self.backend, self.env), 0o700)
        return [f"[ok] Start on boot: {boot_path(self.env)}",
                "    Install the Termux:Boot app (F-Droid, same source as Termux) and open it once.",
                "    In Android settings, turn off battery optimisation for Termux (and Termux:Boot), or Android "
                "will stop it."]

    def remove(self):
        lines = []
        self.stop()
        b = self.backend
        if b == "termux":
            self.run("sv-disable", NAME)
            d = termux_service_dir(self.env)
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
                lines.append(f"[ok] Removed {d}")
        elif b == "systemd":
            self.run("systemctl", "--user", "disable", "--now", NAME)
            p = unit_path(self.env)
            if os.path.exists(p):
                os.unlink(p)
                self.run("systemctl", "--user", "daemon-reload")
                lines.append(f"[ok] Removed {p}")
        bp = boot_path(self.env)
        if os.path.exists(bp):
            os.unlink(bp)
            lines.append(f"[ok] Removed the boot script {bp}")
        return True, lines or ["[ok] Service stopped; nothing else was installed."]

    # -- start / stop ----------------------------------------------------
    def builtin_pid(self):
        try:
            pid = int(open(pid_path()).read().strip())
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            return None

    def others(self):
        """Another supervisor or stray serve / telegram copies, as lines.
        termux-services and the built-in supervisor must never both run."""
        found = []
        b = self.backend
        if b != "builtin" and self.builtin_pid():
            found.append((self.builtin_pid(), "supervisor", "built-in supervisor (supervisor.pid)"))
        if b == "builtin" and self.which("sv") and os.path.isfile(os.path.join(termux_service_dir(self.env), "run")):
            code, out = self.run("sv", "status", NAME)
            if code == 0 and out.startswith("run:"):
                found.append((None, "termux", "termux-services runs nimlab (sv status: run)"))
        for pid, kind, cmd in strays():
            if not any(pid == f[0] for f in found):
                found.append((pid, kind, cmd))
        return found

    def cleanup(self, found=None):
        if found is None:
            # 3.8.2: the full sequence (auto-restart off first, then every Nim
            # Lab process, bounded waits), the same one ./update.sh runs.
            from . import updater
            lines = []
            u = updater.Updater(mgr=self, out=lines.append, env=self.env)
            try:
                u.tpid = updater.tunnel_pid()
                n = len(u.procs())
                u.disable_respawners()
                u.clean()
                u.clear_stale()
                lines.append(f"[ok] Stopped {n} Nim Lab process(es); none left." if n else "[ok] No Nim Lab processes left.")
                lines.append("    Start it again with: nimlab service start (or ./update.sh to start and health-check)")
            except updater.UpdateError as e:
                lines.append(f"[x] {e}")
            return [ln.strip() for ln in lines]
        lines = []
        for pid, kind, what in found:
            if kind == "termux":
                self.run("sv", "down", NAME)
                lines.append("[ok] Stopped termux-services nimlab (sv down nimlab)")
        pids = [pid for pid, kind, _ in found if pid and pid > 0]
        for pid in stop_pids(pids):
            lines.append(f"[ok] Stopped pid {pid}")
        return lines or ["No other Nim Lab copies found."]

    def start(self, ask=None):
        """ask(question) -> bool lets an interactive start offer to stop an
        existing supervisor / stray copy first; without it they are listed."""
        found = self.others()
        pre = []
        if found:
            pre = ["[!] Other Nim Lab copies are running (two pollers or servers fight over the port and Telegram):"]
            pre += [f"    pid {pid or '-'}  {kind}: {what}" for pid, kind, what in found]
            if ask and ask("Stop them first?"):
                pre += self.cleanup(found)
            else:
                pre.append("    Stop them with: nimlab service cleanup")
        ok, lines = self._start()
        return ok, pre + lines

    def _start(self):
        b = self.backend
        if b == "termux":
            code, out = self.run("sv", "up", NAME)
            return code == 0, ["[ok] Started (sv up nimlab)." if code == 0 else f"[x] sv up failed: {out[-300:]}"]
        if b == "systemd":
            code, out = self.run("systemctl", "--user", "start", NAME)
            return code == 0, ["[ok] Started." if code == 0 else f"[x] {out[-300:]}"]
        if self.builtin_pid():
            return True, [f"[ok] Already running (pid {self.builtin_pid()})."]
        holder = SupervisorLock().holder()
        if holder:
            return True, [f"[ok] A supervisor already runs (pid {holder}); not starting a second one."]
        logf = open(os.path.join(state_dir(), "supervisor.out"), "a")
        p = subprocess.Popen(start_cmd(self.env), stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             start_new_session=True, cwd=config.PROJECT_DIR)
        for _ in range(30):
            time.sleep(0.2)
            if self.builtin_pid() or p.poll() is not None:
                break
        if p.poll() is not None:
            return False, [f"[x] The supervisor exited at once (code {p.returncode}); see {logf.name}"]
        return True, [f"[ok] Started the built-in supervisor (pid {p.pid}). Log: {log_path()}"]

    def stop(self):
        b = self.backend
        if b == "termux":
            code, out = self.run("sv", "down", NAME)
            return code == 0, ["[ok] Stopped (sv down nimlab)." if code == 0 else f"[!] {out[-300:]}"]
        if b == "systemd":
            code, out = self.run("systemctl", "--user", "stop", NAME)
            return code == 0, ["[ok] Stopped." if code == 0 else f"[!] {out[-300:]}"]
        pid = self.builtin_pid()
        if not pid:
            return True, ["Not running."]
        os.kill(pid, signal.SIGTERM)
        for _ in range(60):
            time.sleep(0.25)
            if not self.builtin_pid():
                break
        return True, [f"[ok] Stopped (pid {pid})."]

    def restart(self):
        write_state(cooldown_until={}, held={})   # a manual restart retries at once
        if self.backend == "termux":
            code, out = self.run("sv", "restart", NAME)
            return code == 0, ["[ok] Restarted." if code == 0 else f"[x] {out[-300:]}"]
        if self.backend == "systemd":
            code, out = self.run("systemctl", "--user", "restart", NAME)
            return code == 0, ["[ok] Restarted." if code == 0 else f"[x] {out[-300:]}"]
        a = self.stop()[1]
        ok, b = self._start()
        return ok, a + b

    def installed(self):
        if self.backend == "termux":
            return os.path.isfile(os.path.join(termux_service_dir(self.env), "run"))
        if self.backend == "systemd":
            return os.path.isfile(unit_path(self.env))
        return settings().get("backend") == "builtin" or bool(self.builtin_pid())

    def running(self):
        if self.backend == "termux":
            code, out = self.run("sv", "status", NAME)
            return code == 0 and out.startswith("run:")
        if self.backend == "systemd":
            code, out = self.run("systemctl", "--user", "is-active", NAME)
            return out.strip() == "active"
        return bool(self.builtin_pid())


def uptime_text(st):
    ts = st.get("started_ts")
    if not ts or not st.get("running"):
        return ""
    s = int(time.time() - ts)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    return (f"{d}d " if d else "") + (f"{h}h " if h or d else "") + f"{m}m"


def child_problem(st=None):
    """The child that is restarting or held, as one short phrase, e.g.
    'serve crash loop (code 1: A test server is already running ...)'."""
    st = st if st is not None else read_state()
    held = st.get("held") or {}
    for name, h in held.items():
        line = (h.get("line") or "")[:90]
        return f"{name} {h.get('why', 'held')} (code {h.get('code')}{': ' + line if line else ''})"
    le = st.get("last_exit") or {}
    by = st.get("restarts_by_child") or {}
    if le and by.get(le.get("child"), 0) >= 3:
        line = (le.get("line") or "")[:90]
        return f"{le['child']} restarting (last code {le.get('code')}{': ' + line if line else ''})"
    return ""


def brief(mgr=None):
    """One line for the dashboard and self_status."""
    from . import tunnel
    try:
        mgr = mgr or Manager()
        if not mgr.installed():
            return "not set up"
        up = mgr.running()
    except Exception:  # noqa: BLE001
        return "?"
    st = read_state()
    parts = [f"{'running' if up else 'stopped'} ({mgr.backend})"]
    if up and uptime_text(st):
        parts.append("up " + uptime_text(st))
    r = int(st.get("restarts") or 0)
    if r:
        parts.append(f"{r} restart{'s' if r != 1 else ''}")
    prob = child_problem(st)
    if prob:
        parts.append(prob)
    try:
        n = len(strays(st))
        if n:
            parts.append(f"{n} stray cop{'y' if n == 1 else 'ies'} (nimlab service status)")
    except Exception:  # noqa: BLE001
        pass
    tb = tunnel.brief()
    if tb:
        parts.append(tb)
    return ", ".join(parts)


def status_lines(mgr):
    from . import tunnel
    st = read_state()
    inst = mgr.installed()
    up = mgr.running() if inst else False
    live = st.get("children") or {} if st.get("running") else {}
    alive = {}
    for k, pid in live.items():
        try:
            os.kill(int(pid), 0)
            alive[k] = pid
        except (OSError, ValueError, TypeError):
            pass
    by = st.get("restarts_by_child") or {}
    le = st.get("last_exit") or {}
    lines = [f"backend    : {mgr.backend}", f"installed  : {'yes' if inst else 'no (nimlab service install)'}",
             f"running    : {'yes' if up else 'no'}" + (f", up {uptime_text(st)}" if up and uptime_text(st) else "")
             + (f" (supervisor pid {st['supervisor_pid']})" if up and st.get("supervisor_pid") else ""),
             f"restarts   : {int(st.get('restarts') or 0)}" +
             (" (" + ", ".join(f"{k} {v}" for k, v in by.items() if v) + ")" if any(by.values()) else ""),
             f"children   : " + (", ".join(f"{k} (pid {v})" for k, v in alive.items()) or "none running") +
             f"   configured: {', '.join(st.get('configured') or child_commands())}"]
    if le:
        lines.append(f"last exit  : {le.get('child')} code {le.get('code')} at {le.get('at')}")
        if le.get("line"):
            lines.append(f"  last error: {le['line'][:200]}")
    for name, h in (st.get("held") or {}).items():
        extra = ""
        if h.get("why") == "crash loop" and h.get("until"):
            extra = f", next try in {max(0, int(h['until'] - time.time()))} s"
        elif h.get("why") == "config error":
            extra = ", not restarted until the configuration changes (or: nimlab service restart)"
        lines.append(f"[!] {name}: {h.get('why')} (code {h.get('code')}){extra}")
        if h.get("line"):
            lines.append(f"    {h['line'][:200]}")
    try:
        sl = strays(st)
    except Exception:  # noqa: BLE001
        sl = []
    if sl:
        lines.append(f"[!] stray copies ({len(sl)}): two pollers or servers fight over the port and Telegram")
        lines += [f"    pid {pid}  {kind}: {cmd}" for pid, kind, cmd in sl]
        lines.append("    Stop them: nimlab service cleanup")
    else:
        lines.append("strays     : none")
    tb = tunnel.brief()
    lines.append(f"public URL : {tb or 'none (tunnel off)'}")
    try:
        from . import scheduler as SC
        lines.append(f"scheduler  : {SC.status_line()}")
    except Exception as e:  # noqa: BLE001
        lines.append(f"scheduler  : status unavailable ({type(e).__name__})")
    lines.append(f"log        : {log_path()}")
    if mgr.backend == "termux" and is_termux(mgr.env):
        lines.append(f"boot       : {'on' if os.path.exists(boot_path(mgr.env)) else 'off'} (Termux:Boot)")
    return lines


def cmd_service(args):
    act = args.action
    if act == "run":
        return supervise()
    ask = None
    if sys.stdin.isatty() and act in ("start", "install"):
        def ask(q):
            return input(f"{q} [Y/n] ").strip().lower() in ("", "y", "yes")
    mgr = Manager(backend=args.backend, ask=ask)
    if act == "cleanup":
        for ln in mgr.cleanup():
            print(ln)
        return 0
    if act == "status":
        for ln in status_lines(mgr):
            print(ln)
        return 0
    if act == "brief":
        b = brief(mgr)
        print(b)
        return 0 if b not in ("not set up", "?") else 1
    if act == "logs":
        n = args.lines or 40
        print(log_tail(n) or f"(no log yet: {log_path()})", end="")
        return 0
    if act in ("telegram", "scheduler"):
        v = (args.value or "").lower()
        if v not in ("on", "off"):
            print(f"usage: service {act} on|off")
            return 2
        sv = settings()
        sv[act] = v == "on"
        save_settings(sv)
        what = "Telegram bot" if act == "telegram" else "Job scheduler (heartbeat and jobs)"
        print(f"[ok] {what} runs with the service: {v} (the service picks it up within a minute)")
        return 0
    if act == "boot":
        for ln in mgr.enable_boot():
            print(ln)
        return 0
    if act == "install" and getattr(args, "system", False):
        ok, lines = install_system(mgr.run, mgr.env)
        print("\n".join(lines))
        return 0 if ok else 1
    fn = {"install": lambda: mgr.install(boot=args.boot), "remove": mgr.remove, "start": mgr.start,
          "stop": mgr.stop, "restart": mgr.restart}[act]
    ok, lines = fn()
    for ln in lines:
        print(ln)
    return 0 if ok else 1
