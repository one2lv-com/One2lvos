"""Shared restart lock for One2lvOS supervisors (watchdog.py and autonomis-agent.py).

Two supervisors watch the same machine:
  * watchdog.py owns the Lumenis reactor (port 8000);
  * autonomis-agent.py watches the other services and the bridge tunnel.
Before either one stops or starts a service it must hold that service's restart lock. The lock is an
flock on logs/restart-<service>.lock (released by the kernel if the holder dies), plus a stamp written
after each restart, so the other supervisor also stays away while the fresh copy is still coming up.

    with restart_lock("lumenis-reactor", holder="watchdog") as got:
        if got: ...restart...

watchdog_running() tells Autonomis whether the watchdog is alive (it holds logs/watchdog.lock); while it is,
Autonomis never touches the reactor.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import time
from pathlib import Path

try:
    import fcntl
except ImportError:  # not POSIX
    fcntl = None

LOG_DIR = Path(os.environ.get("ONE2LV_LOCK_DIR") or (Path(__file__).resolve().parent / "logs"))
REACTOR_SERVICE = "lumenis-reactor"
DEFAULT_GRACE_S = 60.0


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:60]


def lock_path(service: str) -> Path:
    return LOG_DIR / f"restart-{_safe(service)}.lock"


def stamp_path(service: str) -> Path:
    return LOG_DIR / f"restart-{_safe(service)}.last.json"


def last_restart(service: str) -> dict:
    try:
        return json.loads(stamp_path(service).read_text())
    except (OSError, ValueError):
        return {}


def recently_restarted_by_other(service: str, holder: str, within_s: float = DEFAULT_GRACE_S) -> dict | None:
    """The other supervisor restarted this service less than within_s ago: return its stamp."""
    st = last_restart(service)
    if st and st.get("holder") != holder and time.time() - float(st.get("at", 0)) < within_s:
        return st
    return None


@contextlib.contextmanager
def restart_lock(service: str, holder: str, grace_s: float = DEFAULT_GRACE_S):
    """Yield True when this holder may restart the service now, else False (never blocks)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if recently_restarted_by_other(service, holder, grace_s):
        yield False
        return
    fh = open(lock_path(service), "a+")
    got = True
    if fcntl is not None:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            got = False
    try:
        if got:
            fh.seek(0)
            fh.truncate()
            fh.write(json.dumps({"holder": holder, "pid": os.getpid(), "since": time.time()}))
            fh.flush()
        yield got
        if got:
            tmp = stamp_path(service).with_suffix(".tmp")
            tmp.write_text(json.dumps({"holder": holder, "pid": os.getpid(), "at": time.time()}))
            os.replace(tmp, stamp_path(service))
    finally:
        if got and fcntl is not None:
            with contextlib.suppress(OSError):
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


def watchdog_running() -> bool:
    """True while a watchdog.py process holds logs/watchdog.lock."""
    p = LOG_DIR / "watchdog.lock"
    if fcntl is None or not p.exists():
        return False
    try:
        with open(p, "a+") as fh:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return True
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            return False
    except OSError:
        return False
