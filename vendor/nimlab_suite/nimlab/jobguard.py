"""v3.8.4 job guard: no fixed tool-step cap for scheduled jobs with a tool
list, with guards against true runaway loops instead.

run_tool_loop calls the guard:
  check()              before every model call and every tool call; a
                       string back means stop now (interrupted / time up)
  after_call(...)      after every tool call; a string back means stop
                       (the same failing call over and over, a loop of
                       identical calls with identical results, a long run
                       of failures)
  model_failed(n)      a model step failed (429 storm, 5xx): sleep a
                       growing backoff and -> True to try again, False to
                       give up

Why a stop happened is kept in .stopped = {"kind", "reason"} with kind
one of interrupted, deadline, runaway, model.
"""
import hashlib
import json
import threading
import time

DEFAULTS = {
    "same_failing_call_max": 3,     # identical call (tool + arguments) that failed this many times
    "same_result_max": 4,           # identical call returning the identical result this many times
    "failures_in_a_row_max": 6,     # any failed/refused calls in a row
    "model_retry_max": 3,           # failed model steps in a row before giving up
    "model_backoff_sec": 20,        # first backoff; doubles each time (20, 40, 80)
    "min_step_gap_sec": 2,          # at least this long between model calls
    "wrap_up_sec": 60,              # stop this long before the job's timeout to write the answer
}


def settings(cluster=None):
    s = dict(DEFAULTS)
    got = ((cluster or {}).get("scheduler_settings") or {}).get("job_guard") or {}
    for k, v in got.items():
        if k in s and isinstance(v, (int, float)) and v >= 0:
            s[k] = v
    return s


def _sig(name, args):
    try:
        a = json.dumps(args or {}, sort_keys=True, default=str)
    except (TypeError, ValueError):
        a = repr(args)
    return f"{name}|{a}"


class JobGuard:
    def __init__(self, name="job", timeout=0, interruptible=False, unlimited=True, cfg=None,
                 clock=time.time, mono=time.monotonic, sleep=None, interrupt_fn=None):
        self.name = name
        self.cfg = dict(DEFAULTS, **(cfg or {}))
        self.clock, self.mono = clock, mono
        self.t0 = clock()
        self.m0 = mono()
        self.timeout = float(timeout or 0)
        self.interruptible = bool(interruptible)
        self.unlimited = bool(unlimited)
        self.cancelled = threading.Event()
        self._sleep = sleep or (lambda s: self.cancelled.wait(s))
        self._interrupt_fn = interrupt_fn
        self.stopped = None
        self.progress = ""
        self.fails = {}
        self.results = {}
        self.fail_run = 0
        self.last_model = None
        self.steps = 0
        self.calls = 0

    # -- helpers ----------------------------------------------------------
    def deadline_left(self):
        if not self.timeout:
            return None
        wrap = min(float(self.cfg["wrap_up_sec"]), self.timeout * 0.2)
        return self.timeout - wrap - (self.mono() - self.m0)

    def _stop(self, kind, reason):
        if self.stopped is None:
            self.stopped = {"kind": kind, "reason": reason}
        return self.stopped["reason"]

    def interrupt(self):
        """-> the interrupt mark (dict) when this job was interrupted, else None."""
        if not self.interruptible:
            return None
        if self._interrupt_fn is not None:
            return self._interrupt_fn(self.t0, self.name)
        from . import interrupts
        return interrupts.since(self.t0, own=self.name)

    # -- the hooks run_tool_loop calls -------------------------------------
    def check(self):
        if self.stopped is not None:
            return self.stopped["reason"]
        if self.cancelled.is_set():
            return self._stop("deadline", "the job was cancelled (its time ran out)")
        m = self.interrupt()
        if m:
            from . import interrupts
            self.stopped = {"kind": "interrupted", "reason": interrupts.describe(m), "mark": m}
            return self.stopped["reason"]
        left = self.deadline_left()
        if left is not None and left <= 0:
            return self._stop("deadline", f"the job's time ({int(self.timeout)} s) is nearly up")
        return None

    def before_model(self):
        """Pace model calls on the free endpoint. -> stop reason or None."""
        why = self.check()
        if why:
            return why
        gap = float(self.cfg["min_step_gap_sec"])
        if self.last_model is not None and gap > 0:
            wait = gap - (self.mono() - self.last_model)
            if wait > 0:
                self._sleep(wait)
        self.last_model = self.mono()
        self.steps += 1
        return self.check()

    def after_call(self, name, args, outcome, text=""):
        self.calls += 1
        sig = _sig(name, args)
        bad = outcome in ("error", "failed", "rejected")
        if bad:
            self.fail_run += 1
            self.fails[sig] = self.fails.get(sig, 0) + 1
            if self.fails[sig] >= int(self.cfg["same_failing_call_max"]):
                return self._stop("runaway", f"the same failing call to {name} was repeated "
                                             f"{self.fails[sig]} times")
            if self.fail_run >= int(self.cfg["failures_in_a_row_max"]):
                return self._stop("runaway", f"{self.fail_run} tool calls in a row failed or were refused")
            return None
        self.fail_run = 0
        h = hashlib.sha256(str(text or "").encode("utf-8", "replace")).hexdigest()[:16]
        key = (sig, h)
        self.results[key] = self.results.get(key, 0) + 1
        if self.results[key] >= int(self.cfg["same_result_max"]):
            return self._stop("runaway", f"the identical call to {name} returned the identical result "
                                         f"{self.results[key]} times")
        return None

    def model_failed(self, n):
        """n = failed model steps in a row so far (1, 2, ...)."""
        if n > int(self.cfg["model_retry_max"]):
            self._stop("model", f"the model endpoint failed {n} times in a row (backed off and gave up)")
            return False
        wait = float(self.cfg["model_backoff_sec"]) * (2 ** (n - 1))
        left = self.deadline_left()
        if left is not None and left < wait:
            self._stop("model", "the model endpoint kept failing and the job's time is nearly up")
            return False
        end = self.mono() + wait
        while self.mono() < end:     # sleep in slices so an interrupt still ends the job promptly
            if self.check():
                return False
            self._sleep(min(2.0, max(0.0, end - self.mono())))
        return self.check() is None


# ---------------------------------------------------------------------------
# the guard for this thread's scheduled run
# ---------------------------------------------------------------------------
_local = threading.local()


def current():
    return getattr(_local, "guard", None)


class using:
    def __init__(self, guard):
        self.guard = guard

    def __enter__(self):
        self.prev = getattr(_local, "guard", None)
        _local.guard = self.guard
        return self.guard

    def __exit__(self, *exc):
        _local.guard = self.prev
        return False
