"""v3.8.4 interrupts: what ends an interruptible scheduled job (Free time).

SeVin's rule: a message from him (Telegram, the endpoint, a voice call), a
Gmail watchdog alert and any other scheduled job interrupt whatever Quill is
still doing in Free time. The interrupted job ends; it does not resume.

The server (user turns) and the scheduler (job starts) run in different
processes, so the marks are small files under data/scheduler/interrupts:

    user.json         the last user request the server received
    job-<name>.json   the last start of each scheduled job

A running job asks since(t0, own=name): the newest mark newer than its own
start, ignoring its own job's mark.
"""
import json
import os
import re
import time

USER = "user"
JOB = "job"


def _dir():
    from . import store
    d = os.path.join(store.data_dir(), "scheduler", "interrupts")
    os.makedirs(d, exist_ok=True)
    return d


def _safe(name):
    return re.sub(r"[^A-Za-z0-9_.\-]", "_", str(name or "job"))[:120] or "job"


def mark(kind, source="", clock=time.time):
    """Record an interrupt: kind USER (source = the request path) or JOB
    (source = the job's name). Never raises: a failed mark must not break a
    user turn or a job."""
    try:
        fn = "user.json" if kind == USER else f"job-{_safe(source)}.json"
        path = os.path.join(_dir(), fn)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"kind": kind, "source": str(source or "")[:200], "ts": clock()}, f)
        os.replace(tmp, path)
        return True
    except Exception:  # noqa: BLE001
        return False


def marks():
    out = []
    try:
        names = os.listdir(_dir())
    except OSError:
        return out
    for fn in names:
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(_dir(), fn), encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, dict) and isinstance(m.get("ts"), (int, float)):
                out.append(m)
        except (OSError, ValueError):
            continue
    return out


def since(t0, own=None):
    """The newest interrupt after t0 (wall clock) that is not this job's own
    start. -> dict(kind, source, ts) or None."""
    best = None
    for m in marks():
        if m["ts"] <= t0:
            continue
        if m.get("kind") == JOB and own is not None and m.get("source") == str(own):
            continue
        if best is None or m["ts"] > best["ts"]:
            best = m
    return best


def describe(m):
    """Words for the run report."""
    if not m:
        return ""
    if m.get("kind") == USER:
        return "SeVin sent Quill a message"
    src = str(m.get("source") or "another job")
    if src.startswith("gmail-alert"):
        return f"an email alert ({src}) started"
    return f"the scheduled job {src} started"


# ---------------------------------------------------------------------------
# leftovers: where an interrupted job left off, for that job's next run
# ---------------------------------------------------------------------------
def _left_path(name):
    d = os.path.join(_dir(), "leftover")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{_safe(name)}.json")


def save_leftover(name, data, clock=time.time):
    """Keep where job `name` left off when it was interrupted. data: a dict
    (reason, progress text, links, undone actions ...)."""
    try:
        rec = dict(data or {}, job=str(name), saved_ts=clock())
        path = _left_path(name)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except Exception:  # noqa: BLE001
        return False


def load_leftover(name):
    try:
        with open(_left_path(name), encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def clear_leftover(name):
    try:
        os.remove(_left_path(name))
        return True
    except OSError:
        return False
