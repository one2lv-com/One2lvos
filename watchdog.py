#!/usr/bin/env python3
"""
One2lvOS Watchdog
=================
Monitors the Lumenis Reactor Core (127.0.0.1:8000) and restarts it only when
it is really down.

How it decides:
  * Health check = GET http://127.0.0.1:<port>/api/status (not "localhost",
    so it never wanders off to ::1).
  * Port free (nothing listening)          -> reactor is down, start it now.
  * Port held, /api/status answers 200     -> healthy, whoever started it.
  * Port held, /api/status fails           -> count it. Only after
    FAIL_THRESHOLD failures in a row (a busy council can stall the event loop
    for a while) is the reactor treated as hung: the process holding the port
    is stopped (only if it is a lumenis-main uvicorn), and a fresh copy is
    started once the port is free.
  * It never launches a second copy while the port is taken.
  * If a copy it launched exits, it re-checks the port before doing anything,
    so a failed duplicate ("address already in use") no longer loops forever.
  * Only one watchdog can run at a time (lock file), and restarts back off
    when they keep failing.

The reactor runs in its own session, so restarting the watchdog does not take
the reactor down.

Usage:
    nohup python3 watchdog.py > logs/watchdog.log 2>&1 &

Env:
    PORT                    reactor port (default 8000)
    ONE2LV_BIND_HOST        bind/check host (default 127.0.0.1)
    WATCHDOG_INTERVAL       seconds between checks (default 30)
    WATCHDOG_TIMEOUT        health-check timeout in seconds (default 15)
    WATCHDOG_FAILS          consecutive failures before a hung reactor is
                            restarted (default 3)
"""

import fcntl
import json
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR   = Path(__file__).resolve().parent
COMPASS_DB = os.environ.get("COMPASS_DB", str(ROOT_DIR / "compass.db"))
LOG_FILE   = ROOT_DIR / "logs" / "watchdog.log"
LOCK_FILE  = ROOT_DIR / "logs" / "watchdog.lock"

REACTOR_HOST   = os.environ.get("ONE2LV_BIND_HOST", "127.0.0.1")
CHECK_HOST     = "127.0.0.1" if REACTOR_HOST in ("0.0.0.0", "", "localhost") else REACTOR_HOST
REACTOR_PORT   = int(os.environ.get("PORT", 8000))
# Use the project venv when there is one, whatever python started the watchdog
_VENV_PY       = ROOT_DIR / ".venv" / "bin" / "python3"
REACTOR_PYTHON = os.environ.get("REACTOR_PYTHON") or (str(_VENV_PY) if _VENV_PY.exists() else sys.executable)
REACTOR_CMD    = [
    REACTOR_PYTHON, "-m", "uvicorn", "lumenis-main:app",
    "--host", REACTOR_HOST, "--port", str(REACTOR_PORT)
]
REACTOR_MARKER = "lumenis-main"   # only processes whose cmdline has this get stopped

CHECK_INTERVAL = int(os.environ.get("WATCHDOG_INTERVAL", 30))
HTTP_TIMEOUT   = float(os.environ.get("WATCHDOG_TIMEOUT", 15))
FAIL_THRESHOLD = int(os.environ.get("WATCHDOG_FAILS", 3))
STARTUP_WAIT   = 90    # max seconds to wait for a new reactor to answer
PING_EVERY     = 20    # log/store a heartbeat every N healthy checks
MAX_BACKOFF    = 600   # cap on the wait between failed restarts

_reactor_proc = None
_running      = True
_lock_fh      = None


# ── logging ──────────────────────────────────────────────────────────────────

def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stdout_is_logfile() -> bool:
    """True when stdout is already redirected into LOG_FILE (nohup ... > log)."""
    try:
        a, b = os.fstat(sys.stdout.fileno()), os.stat(LOG_FILE)
        return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)
    except Exception:
        return False


def log(msg: str):
    line = f"[{ts()}] {msg}"
    if _stdout_is_logfile():
        print(line, flush=True)          # one copy, via the redirect
        return
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── compass.db fact logging ───────────────────────────────────────────────────

def store_fact(key: str, value: str):
    try:
        conn = sqlite3.connect(COMPASS_DB, timeout=5)
        conn.execute(
            "INSERT OR REPLACE INTO facts (id, key, value, source, created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), key, value, "watchdog", time.time())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"compass.db write error: {e}")


# ── single instance ───────────────────────────────────────────────────────────

def acquire_lock() -> bool:
    global _lock_fh
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    _lock_fh = open(LOCK_FILE, "a+")
    try:
        fcntl.flock(_lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    _lock_fh.seek(0)
    _lock_fh.truncate()
    _lock_fh.write(str(os.getpid()))
    _lock_fh.flush()
    return True


# ── reactor probes ────────────────────────────────────────────────────────────

def port_in_use() -> bool:
    """Is anything accepting connections on the reactor port?"""
    try:
        with socket.create_connection((CHECK_HOST, REACTOR_PORT), timeout=3):
            return True
    except OSError:
        return False


def reactor_healthy() -> bool:
    try:
        req = urllib.request.Request(
            f"http://{CHECK_HOST}:{REACTOR_PORT}/api/status",
            headers={"User-Agent": "One2lvOS-Watchdog/2.0"}
        )
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return r.status == 200
    except Exception:
        return False


def port_owner_pids() -> list:
    """PIDs of processes holding a LISTEN socket on the reactor port (via /proc)."""
    inodes = set()
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(table) as f:
                next(f)
                for row in f:
                    parts = row.split()
                    local, state, inode = parts[1], parts[3], parts[9]
                    if state == "0A" and int(local.rsplit(":", 1)[1], 16) == REACTOR_PORT:
                        inodes.add(inode)
        except Exception:
            pass
    pids = []
    if not inodes:
        return pids
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                target = os.readlink(f"/proc/{pid}/fd/{fd}")
                if target.startswith("socket:[") and target[8:-1] in inodes:
                    pids.append(int(pid))
                    break
        except Exception:
            continue
    return pids


def cmdline(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().replace(b"\0", b" ").decode(errors="replace").strip()
    except Exception:
        return ""


# ── reactor start / stop ──────────────────────────────────────────────────────

def start_reactor():
    """Start a reactor, but never while the port is taken."""
    if port_in_use():
        log(f"Port {REACTOR_PORT} already in use — not starting a second reactor")
        return None
    log(f"Starting reactor: {' '.join(REACTOR_CMD)}")
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    log_path = ROOT_DIR / "logs" / "reactor.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as lf:
        proc = subprocess.Popen(
            REACTOR_CMD,
            cwd=str(ROOT_DIR),
            env=env,
            stdout=lf,
            stderr=lf,
            start_new_session=True,   # survives a watchdog restart
        )
    log(f"Reactor started — PID {proc.pid}")
    return proc


def wait_until_healthy(proc, limit=STARTUP_WAIT) -> bool:
    deadline = time.time() + limit
    while time.time() < deadline and _running:
        if proc is not None and proc.poll() is not None:
            return False
        if reactor_healthy():
            return True
        time.sleep(2)
    return False


def stop_hung_reactor() -> bool:
    """Stop whatever lumenis-main process holds the port. True if the port is free after."""
    pids = port_owner_pids()
    targets = [p for p in pids if REACTOR_MARKER in cmdline(p)]
    others = [p for p in pids if p not in targets]
    if others:
        log(f"Port {REACTOR_PORT} is held by a non-reactor process {others} — leaving it alone")
        return False
    for p in targets:
        log(f"Stopping hung reactor PID {p}")
        try:
            os.kill(p, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + 15
    while time.time() < deadline and port_in_use():
        time.sleep(1)
    if port_in_use():
        for p in targets:
            try:
                os.kill(p, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(2)
    if _reactor_proc is not None:
        _reactor_proc.poll()   # reap if it was ours
    return not port_in_use()


# ── graceful shutdown ─────────────────────────────────────────────────────────

def handle_signal(sig, frame):
    global _running
    log(f"Watchdog received signal {sig} — exiting (reactor left running)")
    _running = False
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT,  handle_signal)


# ── main loop ─────────────────────────────────────────────────────────────────

def restart(reason: str, restart_count: int):
    global _reactor_proc
    store_fact(
        f"watchdog.restart.{int(time.time())}",
        json.dumps({"ts": ts(), "reason": reason, "count": restart_count})
    )
    _reactor_proc = start_reactor()
    if _reactor_proc is None:
        return port_in_use() and reactor_healthy()
    ok = wait_until_healthy(_reactor_proc)
    if ok:
        log(f"Reactor healthy again — PID {_reactor_proc.pid}")
    else:
        code = _reactor_proc.poll()
        log(f"Reactor did not come up (exit code {code})")
    return ok


def main():
    global _reactor_proc

    if not acquire_lock():
        print(f"[{ts()}] Another watchdog already holds {LOCK_FILE} — exiting", flush=True)
        sys.exit(0)

    log("=== ONE2LVOS WATCHDOG START ===")
    log(f"Monitoring reactor on {CHECK_HOST}:{REACTOR_PORT} every {CHECK_INTERVAL}s "
        f"(timeout {HTTP_TIMEOUT:g}s, restart after {FAIL_THRESHOLD} failed checks if hung)")
    store_fact("watchdog.start", json.dumps({"ts": ts(), "port": REACTOR_PORT}))

    if reactor_healthy():
        log(f"Reactor already alive (PID {port_owner_pids() or '?'}) — monitoring only")
    elif port_in_use():
        log("Port is taken but reactor not answering yet — will keep checking")
    else:
        log("Reactor not running on startup — starting now")
        restart("not_running_on_start", 0)

    restart_count = 0
    fails = 0
    backoff = 0
    healthy_checks = 0

    while _running:
        time.sleep(CHECK_INTERVAL + backoff)

        # Reap a copy we launched that has exited, then judge by the port.
        if _reactor_proc is not None and _reactor_proc.poll() is not None:
            log(f"Reactor PID {_reactor_proc.pid} we launched exited (code {_reactor_proc.returncode})")
            _reactor_proc = None

        if not port_in_use():
            fails = 0
            restart_count += 1
            log(f"Nothing listening on port {REACTOR_PORT} — reactor is down, restarting")
            ok = restart("port_closed", restart_count)
            backoff = 0 if ok else min(MAX_BACKOFF, max(30, backoff * 2))
            continue

        if reactor_healthy():
            if fails:
                log(f"Reactor answering again after {fails} failed check(s)")
            fails = 0
            backoff = 0
            healthy_checks += 1
            if healthy_checks % PING_EVERY == 1:
                log(f"Reactor alive (restarts: {restart_count})")
                store_fact("watchdog.ping", json.dumps({"ts": ts(), "alive": True, "restarts": restart_count}))
            continue

        fails += 1
        log(f"Reactor port open but /api/status failed ({fails}/{FAIL_THRESHOLD})")
        if fails < FAIL_THRESHOLD:
            continue

        log("Reactor hung — restarting it")
        fails = 0
        restart_count += 1
        if not stop_hung_reactor():
            log("Could not free the port — will try again later")
            backoff = min(MAX_BACKOFF, max(30, backoff * 2))
            continue
        ok = restart("hung", restart_count)
        backoff = 0 if ok else min(MAX_BACKOFF, max(30, backoff * 2))


if __name__ == "__main__":
    main()
