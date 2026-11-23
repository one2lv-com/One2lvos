"""Bug log (v3.7.1): one place that records what went wrong, grouped.

Every error the server answers with a 5xx, every internal exception, a
self-test check that times out or can't connect, and every voice-call
stage that fails is recorded here with a short bug ID such as B-3F9A1C.
The same problem happening again does not add a new bug: it bumps the
count and the 'last seen' time of the one it matches, so a flood of the
same timeout stays one line in `nimlab bugs list`.

What a record holds: where it happened, the HTTP status, the upstream
(NVIDIA) error text, the full internal routing trace of the turn (which
roles ran, how long each took, which one failed), per-stage timings and
the Python stack trace. Secrets are removed before anything is written:
known keys, anything key-shaped (nvapi-, sk-, nvcf-), Bearer and Basic
auth values, Telegram bot tokens, passwords and client secrets in JSON or
URLs.

Files (in the data folder, bugs/): index.json (one row per bug ID with
counts) and events.jsonl (one line per occurrence). Retention keeps the
folder small on a phone: events.jsonl is gzip-rotated when it passes a
slice of the cap, archives older than keep_days are deleted, and the
whole folder is held under max_mb by deleting the oldest archives first.
Settings live in server_settings.json under "bugs" (see README, Settings
reference).

Commands: nimlab bugs list | show <id> | tail [-n N] | status | prune |
clear (clear asks first).
"""

import gzip
import hashlib
import json
import os
import re
import shutil
import threading
import time
import traceback
from datetime import datetime, timezone

from . import config
from .core import redact as _core_redact

DIR_NAME = "bugs"
INDEX = "index.json"
EVENTS = "events.jsonl"
ARCHIVE_PREFIX = "events-"

DEFAULTS = {
    "enabled": True,               # record bugs at all
    "max_mb": 5,                   # whole bugs/ folder cap (index + live file + archives)
    "keep_days": 14,               # archives and bug rows not seen for this long are deleted
    "compress": True,              # gzip a full events.jsonl instead of keeping it as plain text
    "max_event_kb": 64,            # one occurrence is cut to this size (long traces, big upstream bodies)
    "trace_in_request_log": True,   # copy the short routing trace into each request-log line
}

_lock = threading.RLock()
_settings_override = None


# ---------------------------------------------------------------------------
# Settings and paths
# ---------------------------------------------------------------------------
def settings():
    """The bug-log settings: server_settings.json "bugs" over DEFAULTS."""
    if _settings_override is not None:
        return dict(DEFAULTS, **_settings_override)
    raw = {}
    try:
        from . import store
        p = store.path("server_settings.json")
        doc = config.load_json(p, None) if os.path.exists(p) else None
        if isinstance(doc, dict) and isinstance(doc.get("bugs"), dict):
            raw = doc["bugs"]
    except Exception:  # noqa: BLE001 - the bug log never breaks the caller
        raw = {}
    out = dict(DEFAULTS)
    out.update({k: v for k, v in raw.items() if k in DEFAULTS})
    return out


def configure(over=None):
    """Tests and the server set settings directly (None: read the file)."""
    global _settings_override
    _settings_override = dict(over) if over is not None else None


def bug_dir():
    from . import store
    d = os.path.join(store.data_dir(), DIR_NAME)
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------
# no \b at the start: inside a bot URL the token follows "bot" (.../bot123:ABC.../getUpdates)
_TG_TOKEN = re.compile(r"(?<!\d)\d{6,12}:[A-Za-z0-9_\-]{30,}(?![A-Za-z0-9_\-])")
_BASIC = re.compile(r"(?i)(basic\s+)[A-Za-z0-9+/=]{8,}")
_JSON_SECRET = re.compile(r'(?i)("(?:password|passwd|pwd|secret|client_secret|token|access_token|api_key|apikey|'
                          r'key|authorization|bot_token)"\s*:\s*")([^"]{3,})(")')
_KV_SECRET = re.compile(r"(?i)\b(password|passwd|pwd|client_secret|access_token|api_key|apikey|token|key)=([^&\s'\"]{3,})")
_URL_CRED = re.compile(r"(?i)(https?://)([^/\s:@]+):([^/\s@]+)@")


def redact(text):
    """core.redact plus the shapes a bug record can carry."""
    if not isinstance(text, str) or not text:
        return text
    extra = []
    try:
        from . import ltm_ords
        extra = ltm_ords.known_secrets()
    except Exception:  # noqa: BLE001
        extra = []
    text = _core_redact(text, extra)
    text = _TG_TOKEN.sub("[telegram-token]", text)
    text = _BASIC.sub(r"\1****", text)
    text = _JSON_SECRET.sub(r"\1****\3", text)
    text = _KV_SECRET.sub(r"\1=****", text)
    text = _URL_CRED.sub(r"\1\2:****@", text)
    return text


def _clean(obj, depth=0):
    """Redact every string in a JSON-able structure."""
    if depth > 8:
        return "..."
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            ks = str(k)
            if re.search(r"(?i)^(password|passwd|secret|client_secret|api_key|apikey|token|bot_token|authorization)$",
                         ks):
                out[ks] = "****"
            else:
                out[ks] = _clean(v, depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return [_clean(v, depth + 1) for v in obj]
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    return redact(str(obj))


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------
_NUM = re.compile(r"\b(?:\d+(?:\.\d+)?|[0-9a-f]{8,})\b", re.I)


def signature(kind, where, message, exc=None):
    """What makes two occurrences 'the same bug': the kind, where it
    happened, the message with numbers/ids taken out, and the innermost
    frame of the stack trace (file:function)."""
    frame = ""
    if exc is not None and exc.__traceback__ is not None:
        tb = traceback.extract_tb(exc.__traceback__)
        if tb:
            last = tb[-1]
            frame = f"{os.path.basename(last.filename)}:{last.name}"
        frame = f"{type(exc).__name__}@{frame}"
    msg = _NUM.sub("#", (message or "").lower())[:160]
    return f"{kind}|{where}|{msg}|{frame}"


def bug_id(sig):
    return "B-" + hashlib.sha1(sig.encode("utf-8")).hexdigest()[:6].upper()


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_index():
    p = os.path.join(bug_dir(), INDEX)
    try:
        with open(p, "r", encoding="utf-8") as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_index(idx):
    p = os.path.join(bug_dir(), INDEX)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def record(kind, message, where="", status=None, upstream=None, trace=None, stages=None, exc=None,
           request_id=None, model=None, context=None):
    """Record one occurrence. -> the bug ID (also when the bug log is off:
    the ID is still useful to the client), or None when even that fails.

    kind: short class (server_error, upstream_error, timeout, connect,
    self_test, voice_stage, telegram, internal). where: route or step.
    upstream: the provider's error text. trace: the routing trace list.
    stages: {stage: ms} timings. exc: an exception (its stack is kept)."""
    try:
        sig = signature(kind, where, message, exc)
        bid = bug_id(sig)
    except Exception:  # noqa: BLE001
        return None
    s = settings()
    if not s.get("enabled", True):
        return bid
    try:
        stack = None
        if exc is not None:
            stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-8000:]
        ev = {"ts": _now(), "id": bid, "kind": kind, "where": where, "status": status,
              "message": (message or "")[:2000], "request_id": request_id, "model": model}
        if upstream:
            ev["upstream"] = str(upstream)[:4000]
        if trace:
            ev["trace"] = trace
        if stages:
            ev["stages_ms"] = stages
        if stack:
            ev["stack"] = stack
        if context:
            ev["context"] = context
        ev = _clean(ev)
        line = json.dumps(ev, ensure_ascii=False, default=str)
        cap = int(float(s.get("max_event_kb") or 64) * 1024)
        if len(line.encode("utf-8")) > cap:
            for k in ("context", "stack", "upstream", "trace"):
                if k in ev and len(line.encode("utf-8")) > cap:
                    ev[k] = str(ev[k])[: max(200, cap // 4)] + " ...(cut)"
                    line = json.dumps(ev, ensure_ascii=False, default=str)
        with _lock:
            idx = _load_index()
            row = idx.get(bid)
            if row is None:
                row = {"id": bid, "kind": kind, "where": where, "title": ev["message"][:160],
                       "status": status, "first": ev["ts"], "count": 0}
            row["count"] = int(row.get("count") or 0) + 1
            row["last"] = ev["ts"]
            row["last_request"] = request_id
            if status is not None:
                row["status"] = status
            idx[bid] = row
            with open(os.path.join(bug_dir(), EVENTS), "a", encoding="utf-8") as f:
                f.write(line + "\n")
            _save_index(idx)
            enforce(s)
    except Exception:  # noqa: BLE001 - recording a bug must never raise
        pass
    return bid


def record_exception(exc, where="", kind="internal", **kw):
    return record(kind, f"{type(exc).__name__}: {exc}", where=where, exc=exc, **kw)


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------
def _files():
    d = bug_dir()
    out = []
    for n in os.listdir(d):
        p = os.path.join(d, n)
        if os.path.isfile(p):
            out.append((n, p, os.path.getsize(p), os.path.getmtime(p)))
    return out


def total_bytes():
    return sum(f[2] for f in _files())


def _archives():
    return sorted((f for f in _files() if f[0].startswith(ARCHIVE_PREFIX)), key=lambda f: f[3])


def rotate(s=None):
    """Move events.jsonl aside (gzip when compress is on)."""
    s = s or settings()
    d = bug_dir()
    live = os.path.join(d, EVENTS)
    if not os.path.exists(live) or os.path.getsize(live) == 0:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    if s.get("compress", True):
        dst = os.path.join(d, f"{ARCHIVE_PREFIX}{stamp}.jsonl.gz")
        with open(live, "rb") as fi, gzip.open(dst, "wb", compresslevel=6) as fo:
            shutil.copyfileobj(fi, fo)
    else:
        dst = os.path.join(d, f"{ARCHIVE_PREFIX}{stamp}.jsonl")
        shutil.copyfile(live, dst)
    open(live, "w").close()
    return dst


def enforce(s=None, now=None):
    """Apply the retention rules. -> dict of what was done."""
    s = s or settings()
    now = now or time.time()
    done = {"rotated": None, "expired": 0, "trimmed": 0, "rows_dropped": 0}
    with _lock:
        cap = max(0.1, float(s.get("max_mb") or 5)) * 1024 * 1024
        live = os.path.join(bug_dir(), EVENTS)
        # the live file is rotated at a quarter of the cap, so archives hold history
        if os.path.exists(live) and os.path.getsize(live) > cap / 4:
            done["rotated"] = rotate(s)
        keep = float(s.get("keep_days") or 14) * 86400
        for n, p, size, mt in _archives():
            if now - mt > keep:
                os.remove(p)
                done["expired"] += 1
        while total_bytes() > cap:
            arch = _archives()
            if not arch:
                break
            os.remove(arch[0][1])
            done["trimmed"] += 1
        if total_bytes() > cap and os.path.exists(live):
            # one huge live file and nothing left to drop: keep its newest half
            with open(live, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            with open(live, "w", encoding="utf-8") as f:
                f.writelines(lines[len(lines) // 2:])
            done["trimmed"] += 1
        idx = _load_index()
        cut = now - keep
        drop = [k for k, r in idx.items() if _ts(r.get("last")) and _ts(r.get("last")) < cut]
        for k in drop:
            idx.pop(k, None)
        if drop:
            _save_index(idx)
            done["rows_dropped"] = len(drop)
    return done


def _ts(iso):
    try:
        return datetime.fromisoformat(str(iso)).timestamp()
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def list_bugs(limit=50):
    rows = sorted(_load_index().values(), key=lambda r: r.get("last") or "", reverse=True)
    return rows[:limit] if limit else rows


def _iter_events(include_archives=True):
    d = bug_dir()
    paths = []
    if include_archives:
        paths += [p for _, p, _, _ in _archives()]
    paths.append(os.path.join(d, EVENTS))
    for p in paths:
        if not os.path.exists(p):
            continue
        opener = gzip.open if p.endswith(".gz") else open
        try:
            with opener(p, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        yield json.loads(line)
                    except ValueError:
                        continue
        except OSError:
            continue


def events(bid=None, limit=20):
    out = [e for e in _iter_events() if bid is None or e.get("id") == bid]
    return out[-limit:] if limit else out


def find(bid):
    bid = (bid or "").strip().upper()
    if bid and not bid.startswith("B-"):
        bid = "B-" + bid
    return _load_index().get(bid), bid


def status():
    s = settings()
    files = _files()
    arch = [f for f in files if f[0].startswith(ARCHIVE_PREFIX)]
    idx = _load_index()
    return {"enabled": bool(s.get("enabled", True)), "folder": bug_dir(), "bugs": len(idx),
            "occurrences": sum(int(r.get("count") or 0) for r in idx.values()),
            "bytes": sum(f[2] for f in files), "cap_bytes": int(float(s.get("max_mb") or 5) * 1024 * 1024),
            "archives": len(arch), "keep_days": s.get("keep_days"), "compress": s.get("compress")}


def clear():
    with _lock:
        d = bug_dir()
        for n, p, _, _ in _files():
            os.remove(p)
        return d


def _size(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} MB"


def format_row(r):
    return (f"{r.get('id')}  x{r.get('count', 1):<4} {str(r.get('last') or '')[:19]:<19}  "
            f"{(r.get('kind') or ''):<14} {(r.get('where') or '')[:28]:<28} {r.get('title') or ''}")


# ---------------------------------------------------------------------------
# CLI: nimlab bugs ...
# ---------------------------------------------------------------------------
def cmd_bugs(args, out=print, input_fn=input):
    act = getattr(args, "action", None) or "list"
    if act == "list":
        rows = list_bugs(getattr(args, "limit", 50) or 50)
        if not rows:
            out("No bugs recorded.")
            return 0
        out("ID        count last seen (UTC)     kind           where                        what")
        for r in rows:
            out(format_row(r))
        out("\nDetails: nimlab bugs show <ID>")
        return 0
    if act == "show":
        row, bid = find(getattr(args, "bug", "") or "")
        if not row:
            out(f"No bug {bid or '(no ID given)'}. See: nimlab bugs list")
            return 1
        out(format_row(row))
        out(f"first seen {row.get('first')}, last seen {row.get('last')}, {row.get('count')} time(s)")
        evs = events(bid, limit=int(getattr(args, "n", 1) or 1))
        if not evs:
            out("(the occurrences of this bug were already rotated out)")
        for ev in evs:
            out("\n" + json.dumps(ev, ensure_ascii=False, indent=2))
        return 0
    if act == "tail":
        for ev in events(limit=int(getattr(args, "n", 10) or 10)):
            stages = ev.get("stages_ms")
            extra = ("  stages: " + ", ".join(f"{k} {v / 1000:.1f}s" for k, v in stages.items())) if stages else ""
            out(f"{str(ev.get('ts'))[:19]}  {ev.get('id')}  {ev.get('kind')}  {ev.get('where')}  "
                f"{(ev.get('message') or '')[:160]}{extra}")
        return 0
    if act == "status":
        st = status()
        out(f"Bug log: {'on' if st['enabled'] else 'OFF'}  ({st['folder']})")
        out(f"  {st['bugs']} bug(s), {st['occurrences']} occurrence(s)")
        out(f"  size {_size(st['bytes'])} of {_size(st['cap_bytes'])} cap, {st['archives']} archive(s), "
            f"kept {st['keep_days']} days, compress {'on' if st['compress'] else 'off'}")
        return 0
    if act == "prune":
        d = enforce()
        out(f"Pruned: rotated {'yes' if d['rotated'] else 'no'}, {d['expired']} expired, {d['trimmed']} trimmed, "
            f"{d['rows_dropped']} old bug row(s) dropped.")
        return 0
    if act == "clear":
        if not getattr(args, "yes", False):
            try:
                a = input_fn("Delete every recorded bug? [y/N] ").strip().lower()
            except EOFError:
                a = ""
            if a not in ("y", "yes"):
                out("Kept.")
                return 0
        clear()
        out("Bug log cleared.")
        return 0
    out("usage: nimlab bugs list|show <ID>|tail [-n N]|status|prune|clear")
    return 2
