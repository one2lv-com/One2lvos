"""Per-stage timing and time caps (v3.7.1).

A voice turn (and any request the server answers) runs inside a
`Tracker`: every model call the entity makes (run_role) and every named
step (audio conversion, memory recall, memory store, playback...) adds a
stage with its milliseconds, so a slow turn says *where* the time went,
e.g. `convert 0.4s | asr 2.1s | recall 0.3s | persona 41.0s | tts 3.2s`.

While a tracker is active its live state (the stage running right now and
for how long) is visible to other threads through `inflight()`, which is
what the server's GET /v1/testbed/inflight shows and what the self-test
reads when one of its checks times out ("still running: persona on
meta/llama-... for 118 s").

`time_cap(seconds)` bounds every HTTP call and gRPC call made by the same
thread inside it (the voice call uses it so one slow model can't hold a
turn for minutes); calls already shorter keep their own timeout.

Everything here is thread-local and costs nothing when no tracker or cap
is active.
"""

import contextlib
import itertools
import threading
import time

_local = threading.local()
_live = {}                 # tracker id -> Tracker (only while active)
_live_lock = threading.Lock()
_ids = itertools.count(1)


class Tracker:
    """Collects stages for one turn/request."""

    def __init__(self, label="", request_id=None):
        self.id = next(_ids)
        self.label = label
        self.request_id = request_id
        self.t0 = time.monotonic()
        self.wall0 = time.time()
        self.stages = []          # [{"stage", "ms", "ok", "target", "note"}]
        self.current = None       # (stage, target, started monotonic)
        self.net = []             # 3.7.2: one row per HTTP call (see note_http)
        self._lock = threading.Lock()

    # -- recording --------------------------------------------------------
    def begin(self, stage, target=None):
        with self._lock:
            prev = self.current
            self.current = (stage, target, time.monotonic())
        return prev

    def end(self, stage, ok=True, target=None, note=None, started=None, restore=None):
        now = time.monotonic()
        with self._lock:
            cur = self.current
            t = started if started is not None else (cur[2] if cur and cur[0] == stage else now)
            row = {"stage": stage, "ms": int((now - t) * 1000), "ok": bool(ok)}
            if target or (cur and cur[1]):
                row["target"] = target or cur[1]
            if note:
                row["note"] = str(note)[:200]
            self.stages.append(row)
            self.current = restore
        return row

    def add(self, stage, ms, ok=True, target=None, note=None):
        with self._lock:
            row = {"stage": stage, "ms": int(ms), "ok": bool(ok)}
            if target:
                row["target"] = target
            if note:
                row["note"] = str(note)[:200]
            self.stages.append(row)
        return row

    # -- reading ----------------------------------------------------------
    def add_net(self, row):
        with self._lock:
            row = dict(row)
            if self.current and "stage" not in row:
                row["stage"] = self.current[0]
            self.net.append(row)
        return row

    def elapsed_ms(self):
        return int((time.monotonic() - self.t0) * 1000)

    def summary(self):
        """{stage: total ms} in first-seen order (a role called twice adds up)."""
        out = {}
        with self._lock:
            for r in self.stages:
                out[r["stage"]] = out.get(r["stage"], 0) + r["ms"]
        return out

    def snapshot(self):
        with self._lock:
            cur = self.current
            return {"id": self.id, "label": self.label, "request_id": self.request_id,
                    "elapsed_ms": self.elapsed_ms(),
                    "running": ({"stage": cur[0], "target": cur[1], "ms": int((time.monotonic() - cur[2]) * 1000)}
                                if cur else None),
                    "done": [dict(r) for r in self.stages]}

    def slowest(self):
        s = self.summary()
        return max(s.items(), key=lambda kv: kv[1]) if s else (None, 0)


def current():
    """The tracker of this thread, or None."""
    return getattr(_local, "tracker", None)


@contextlib.contextmanager
def track(label="", request_id=None):
    """Run the block with a new tracker, visible in inflight() while it
    runs. A worker thread joins its parent's tracker with adopt()."""
    tr = Tracker(label, request_id)
    prev = getattr(_local, "tracker", None)
    _local.tracker = tr
    with _live_lock:
        _live[tr.id] = tr
    try:
        yield tr
    finally:
        _local.tracker = prev
        with _live_lock:
            _live.pop(tr.id, None)


@contextlib.contextmanager
def stage(name, target=None):
    """Time a named step on this thread's tracker (no-op without one).
    The block can set box['ok']=False / box['note'] to mark the result."""
    tr = current()
    box = {"ok": True, "note": None}
    if tr is None:
        yield box
        return
    started = time.monotonic()
    prev = tr.begin(name, target)
    try:
        yield box
    except BaseException:
        tr.end(name, ok=False, target=target, note=box.get("note"), started=started, restore=prev)
        raise
    tr.end(name, ok=box.get("ok", True), target=target, note=box.get("note"), started=started, restore=prev)


def note_http(method, url, sent, status, first_ms, total_ms, received, attempts=1, stream=False, error=None):
    """3.7.2: record one HTTP exchange on this thread's tracker (no-op
    without one): bytes sent, time to the first byte of the answer (the
    status line and headers), total time, bytes received. The router
    benchmark reads these to split API time from routing overhead."""
    tr = current()
    if tr is None:
        return None
    try:
        import urllib.parse
        u = urllib.parse.urlsplit(url or "")
        where = f"{u.netloc}{u.path}"
    except ValueError:
        where = str(url)[:120]
    row = {"method": method, "url": where[:160], "sent": int(sent or 0), "status": status,
           "first_ms": None if first_ms is None else int(first_ms), "total_ms": int(total_ms or 0),
           "received": int(received or 0), "attempts": attempts}
    if stream:
        row["stream"] = True
    if error:
        row["error"] = str(error)[:120]
    return tr.add_net(row)


def inflight():
    """Snapshots of every active tracker (other threads included)."""
    with _live_lock:
        trs = list(_live.values())
    return [t.snapshot() for t in trs]


# ---------------------------------------------------------------------------
# Time caps
# ---------------------------------------------------------------------------
def cap():
    """The time cap of this thread in seconds, or None."""
    return getattr(_local, "cap", None)


@contextlib.contextmanager
def time_cap(seconds):
    prev = getattr(_local, "cap", None)
    try:
        v = float(seconds) if seconds else None
    except (TypeError, ValueError):
        v = None
    _local.cap = min(v, prev) if (v and prev) else (v or prev)
    try:
        yield _local.cap
    finally:
        _local.cap = prev


def capped(timeout, default=None):
    """A call's timeout under this thread's cap."""
    t = timeout if timeout is not None else default
    c = cap()
    if c is None:
        return t
    return c if t is None else min(float(t), c)


def carry():
    """(tracker, cap) of this thread, to hand to a worker thread."""
    return current(), cap()


@contextlib.contextmanager
def adopt(state):
    """In a worker thread: use the tracker and cap carried from its parent."""
    tr, c = state if state else (None, None)
    prev_t, prev_c = getattr(_local, "tracker", None), getattr(_local, "cap", None)
    _local.tracker, _local.cap = tr, c
    try:
        yield
    finally:
        _local.tracker, _local.cap = prev_t, prev_c


class Timeout(Exception):
    """A bounded call ran past its time."""


def bounded(fn, timeout, what="call"):
    """Run fn() with a hard time limit (for clients with no timeout of
    their own, such as the Riva gRPC helpers). The worker thread is a
    daemon: when it overruns, the caller moves on with Timeout and the
    late answer is dropped."""
    if not timeout:
        return fn()
    box = {}
    state = carry()

    def work():
        with adopt(state):
            try:
                box["v"] = fn()
            except BaseException as e:  # noqa: BLE001 - re-raised in the caller
                box["e"] = e
    th = threading.Thread(target=work, name=f"bounded-{what}", daemon=True)
    th.start()
    th.join(float(timeout))
    if th.is_alive():
        raise Timeout(f"{what} took longer than {float(timeout):.0f}s")
    if "e" in box:
        raise box["e"]
    return box.get("v")


def fmt_stages(stages, total_ms=None):
    """{stage: ms} -> 'asr 2.1s | persona 41.0s | total 44.0s'."""
    bits = [f"{k} {v / 1000:.1f}s" for k, v in (stages or {}).items()]
    if total_ms is not None:
        bits.append(f"total {total_ms / 1000:.1f}s")
    return " | ".join(bits)
