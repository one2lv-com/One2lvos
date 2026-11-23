"""Model fallbacks (v3.8.3).

When a text role's model can't answer after the HTTP client's own retries
(429, any 5xx including NVIDIA's "content safety screening is temporarily
unavailable" 503, a timeout or a dropped connection), the same step is tried
on other models with the same role's prompt and soul:

  1. the reasoning role's model (persona only; routing_settings.
     fallback_to_reasoning, default on), its thinking stripped;
  2. the role's own secondary list, roles.<role>.fallbacks, in order
     (set in the roles menu: R, then F);

Once a fallback has answered, the primary model rests for a cooldown
(routing_settings.fallback_cooldown_sec, default 300 s) and the step starts
at the fallbacks; after the cooldown the primary is tried first again.

Every attempt is recorded (role, model, upstream host, HTTP status, a short
upstream body, retries) on the result, in the turn's trace and bug record,
and fallbacks are logged to data/fallbacks.jsonl for /health and doctor.
No keys are ever recorded: a URL keeps only its host and path.
"""

import json
import os
import re
import threading
import time
import urllib.parse

TRIGGER_STATUSES = (408, 425, 429, 500, 502, 503, 504)
LOG_NAME = "fallbacks.jsonl"
LOG_KEEP = 200
DEFAULT_COOLDOWN = 300.0

_lock = threading.Lock()
_cool = {}      # role -> monotonic time the primary may be tried again


def settings(cluster):
    rs = (cluster or {}).get("routing_settings", {}) or {}
    try:
        cd = float(rs.get("fallback_cooldown_sec", DEFAULT_COOLDOWN))
    except (TypeError, ValueError):
        cd = DEFAULT_COOLDOWN
    return {"enabled": rs.get("fallback_enabled", True) is not False,
            "to_reasoning": rs.get("fallback_to_reasoning", True) is not False,
            "cooldown": max(0.0, cd)}


def should_fall_back(r):
    """A failed ModelResult that another model may answer: rate limited, any
    5xx (whatever the body says), a timeout or a dropped connection. Not a
    4xx that means the request or the key is wrong, and not an unset role."""
    if r is None or getattr(r, "ok", False):
        return False
    st = getattr(r, "status", None)
    if isinstance(st, int) and (st in TRIGGER_STATUSES or 500 <= st <= 599):
        return True
    err = str(getattr(r, "error", "") or "").lower()
    if "is not set" in err or "not found:" in err:
        return False
    if st is None:
        return bool(re.search(r"timed? ?out|timeout|connection|refused|reset|unreachable|temporar|"
                              r"name or service|network|eof|ssl", err)) or not err
    return False


def host_of(url):
    """host + path of a URL, never a query string or credentials."""
    if not url:
        return None
    try:
        u = urllib.parse.urlsplit(str(url))
        host = u.hostname or ""
        if u.port:
            host += f":{u.port}"
        return (host + (u.path or ""))[:160] or None
    except ValueError:
        return None


def short_body(r, n=200):
    raw = getattr(r, "raw", None)
    txt = None
    if isinstance(raw, dict):
        e = raw.get("error")
        if isinstance(e, dict):
            txt = e.get("message")
        elif isinstance(e, str):
            txt = e
        txt = txt or raw.get("detail") or raw.get("message")
    if not txt:
        txt = getattr(r, "error", None)
    txt = " ".join(str(txt or "").split())
    from .core import redact
    return redact(txt)[:n] or None


def attempt_row(role, kind, model, url, r, retries=None):
    """One attempt for traces and bug records (key-free)."""
    row = {"role": role, "kind": kind, "model": model, "host": host_of(url),
           "ok": bool(getattr(r, "ok", False)), "status": getattr(r, "status", None),
           "ms": int((getattr(r, "latency", 0) or 0) * 1000)}
    if retries is not None:
        row["attempts"] = retries
    if not row["ok"]:
        row["body"] = short_body(r)
    return row


def cooling(role, now=None):
    now = time.monotonic() if now is None else now
    with _lock:
        until = _cool.get(role)
        if until is None:
            return False
        if now >= until:
            _cool.pop(role, None)
            return False
        return True


def start_cooldown(role, seconds):
    if seconds <= 0:
        return
    with _lock:
        _cool[role] = time.monotonic() + seconds


def reset():
    """Forget every cooldown (tests, and `nimlab doctor --fix`)."""
    with _lock:
        _cool.clear()


def cooldowns():
    now = time.monotonic()
    with _lock:
        return {k: round(v - now) for k, v in _cool.items() if v > now}


def secondary_list(spec):
    """roles.<role>.fallbacks -> [{model, url?}] (strings are model ids)."""
    out = []
    for f in (spec or {}).get("fallbacks") or []:
        if isinstance(f, str) and f.strip():
            out.append({"model": f.strip()})
        elif isinstance(f, dict) and str(f.get("model") or "").strip():
            d = {"model": str(f["model"]).strip()}
            if f.get("url"):
                d["url"] = str(f["url"]).strip()
            out.append(d)
    return out


def strip_reasoning(messages):
    """The fallback gets the conversation without any model's thinking."""
    out = []
    for m in messages or []:
        if isinstance(m, dict) and ("reasoning_content" in m or "reasoning" in m):
            m = {k: v for k, v in m.items() if k not in ("reasoning_content", "reasoning")}
        out.append(m)
    return out


# -- the log /health and doctor read -------------------------------------
def _log_path():
    from . import store
    return os.path.join(store.data_dir(), LOG_NAME)


def log_event(ev):
    """Append one fallback event (key-free) and keep the last LOG_KEEP."""
    from . import config
    ev = dict(ev, at=config.timestamp())
    p = _log_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with _lock:
            lines = []
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    lines = f.read().splitlines()[-(LOG_KEEP - 1):]
            lines.append(json.dumps(ev, ensure_ascii=False))
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            os.replace(tmp, p)
    except OSError:
        pass
    return ev


def recent(n=20, since_sec=None):
    p = _log_path()
    try:
        with open(p, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f.read().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []
    if since_sec is not None:
        from datetime import datetime, timezone
        cut = time.time() - since_sec
        keep = []
        for r in rows:
            try:
                t = datetime.fromisoformat(str(r.get("at")).replace("Z", "+00:00"))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                if t.timestamp() >= cut:
                    keep.append(r)
            except ValueError:
                continue
        rows = keep
    return rows[-n:]


def summary(hours=24):
    """For /health and doctor: (count in the last `hours`, last event or None)."""
    rows = recent(LOG_KEEP, since_sec=hours * 3600)
    return len(rows), (rows[-1] if rows else None)


def describe_event(ev):
    if not ev:
        return ""
    a = ev.get("from_model") or "?"
    b = ev.get("to_model")
    why = ev.get("status") or "no status"
    if b:
        return f"{ev.get('role')}: {a} failed ({why}), answered by {b}"
    return f"{ev.get('role')}: {a} failed ({why}), every fallback failed too"


# -- plain words for the user when every model failed ---------------------
def plain_failure(attempts, nvidia_host="nvidia.com"):
    """'NVIDIA's model was unavailable (HTTP 503: content safety screening is
    temporarily unavailable). I tried x and y.' -> str, or None without attempts."""
    rows = [a for a in attempts or [] if not a.get("ok")]
    if not rows:
        return None
    first = rows[0]
    host = first.get("host") or ""
    who = "NVIDIA's model" if (not host or nvidia_host in host) else f"The model at {host.split('/')[0]}"
    st = first.get("status")
    if st == 429:
        what = "was busy (rate limited)"
    elif isinstance(st, int) and 500 <= st <= 599:
        what = "was unavailable"
    elif st in (408, 425) or "time" in str(first.get("body") or "").lower():
        what = "took too long to answer"
    else:
        what = "couldn't be reached"
    detail = first.get("body") or ""
    detail = re.sub(r"^HTTP \d+:\s*", "", detail)
    why = f" (HTTP {st}: {detail})" if isinstance(st, int) and detail else (f" ({detail})" if detail else "")
    tried = []
    for a in rows:
        if a.get("model") and a["model"] not in tried:
            tried.append(a["model"])
    if len(tried) > 1:
        names = ", ".join(tried[:-1]) + " and " + tried[-1]
        tail = f" I tried {names}; none of them answered. Try again in a minute."
    else:
        tail = f" I tried {tried[0] if tried else 'it'} and no fallback model is set (roles menu: R, then F). " \
               "Try again in a minute."
    return f"{who} {what}{why}.{tail}"
