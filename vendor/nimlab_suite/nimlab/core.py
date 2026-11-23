"""HTTP client, key handling and error objects shared by every tool.

One place for: timeouts, retries with backoff, consistent result objects,
response-size caps, SSE parsing, multipart bodies, and key masking.
"""

import json
import os
import re
import secrets
import socket
import time
import urllib.error
import urllib.request

KEY_ENV_VARS = ("NVIDIA_API_KEY", "NGC_API_KEY")
RETRY_STATUSES = (429, 500, 502, 503, 504)
DEFAULT_MAX_BYTES = 64 * 1024 * 1024  # hard ceiling on any single response body


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------
def sanitize_key(value):
    """Strip whitespace, CR/LF and wrapping quotes from a pasted key."""
    if not value:
        return ""
    return value.strip().strip("'\"").strip()


def load_api_key(env=None):
    """NVIDIA key from NVIDIA_API_KEY, else NGC_API_KEY. Never from files."""
    env = os.environ if env is None else env
    for name in KEY_ENV_VARS:
        key = sanitize_key(env.get(name, ""))
        if key:
            return key
    return ""


def key_source(env=None):
    env = os.environ if env is None else env
    for name in KEY_ENV_VARS:
        if sanitize_key(env.get(name, "")):
            return name
    return None


def mask(secret):
    """Display form of a secret: known prefix plus last 4 chars only."""
    if not secret:
        return "[NOT SET]"
    if len(secret) < 16:
        return "****"
    prefix = "nvapi-" if secret.startswith("nvapi-") else ""
    return f"{prefix}...{secret[-4:]}"


def redact(text, secrets_list=None):
    """Remove any known secret (env keys plus extras) from a string."""
    if not isinstance(text, str) or not text:
        return text
    candidates = [load_api_key(), sanitize_key(os.environ.get("MCP_API_KEY", ""))]
    try:
        from .mcpkey import known_keys
        candidates += known_keys()
    except Exception:  # noqa: BLE001 - redaction never fails
        pass
    candidates += list(secrets_list or [])
    for s in candidates:
        if s and len(s) >= 8:
            text = text.replace(s, mask(s))
    # anything key-shaped, even a key we do not know (e.g. echoed by a server)
    text = _KEY_SHAPED.sub(lambda m: m.group(1) + "****", text)
    text = _BEARER.sub(r"\1****", text)
    return text


_KEY_SHAPED = re.compile(r"\b(nvapi-|sk-|nvcf-)[A-Za-z0-9_\-]{12,}")
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{12,}")


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------
def error_detail(text, limit=400):
    """The useful part of an error body: NVIDIA answers with JSON such as
    {"title": ..., "detail": ...}, {"error": {"message": ...}} or
    {"message": ...}; anything else is shown as it is (shortened)."""
    try:
        j = json.loads(text)
    except (ValueError, TypeError):
        j = None
    if isinstance(j, dict):
        e = j.get("error")
        parts = []
        if isinstance(e, dict):
            parts.append(str(e.get("message") or e.get("detail") or ""))
        elif isinstance(e, str):
            parts.append(e)
        for k in ("title", "detail", "message", "msg"):
            v = j.get(k)
            if isinstance(v, (str, int, float)) and str(v) not in parts:
                parts.append(str(v))
            elif isinstance(v, list) and v:      # FastAPI-style validation errors
                parts.append("; ".join(str(x.get("msg", x)) if isinstance(x, dict) else str(x) for x in v[:3]))
        msg = " - ".join(p for p in parts if p)
        if msg:
            return msg[:limit]
    t = (text or "").strip()
    return t[:limit] if t else "(empty body)"


class RateLimiter:
    """v3.8.3: paces calls to NVIDIA's API so a sweep stays under the free
    tier's per-minute limit. Thread-safe: every worker waits its turn, at
    most `rpm` requests a minute, evenly spaced. A 429's Retry-After pauses
    everyone until it has passed. rpm 0 or less turns pacing off."""

    def __init__(self, rpm=30, clock=time.monotonic, sleep=time.sleep):
        import threading
        self.rpm = float(rpm or 0)
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._next = 0.0
        self.waited = 0.0
        self.pauses = 0

    @property
    def interval(self):
        return 60.0 / self.rpm if self.rpm > 0 else 0.0

    def wait(self):
        if self.rpm <= 0:
            return 0.0
        with self._lock:
            now = self._clock()
            at = max(now, self._next)
            self._next = at + self.interval
        d = at - now
        if d > 0:
            self.waited += d
            self._sleep(d)
        return d

    def pause_for(self, seconds):
        """A 429 said wait: nobody sends before it has passed (capped at 120 s)."""
        try:
            sec = min(120.0, max(0.0, float(seconds)))
        except (TypeError, ValueError):
            return
        with self._lock:
            self._next = max(self._next, self._clock() + sec)
            self.pauses += 1

    def note(self, res):
        """Look at a response: a 429 pauses (Retry-After, else 10 s)."""
        if getattr(res, "status", None) == 429:
            ra = (getattr(res, "headers", None) or {}).get("retry-after")
            self.pause_for(ra if ra not in (None, "") else 10.0)


def sweep_rpm(settings=None):
    """Requests a minute for setup's 200-OK sweep and spec rebuild: env
    NIMLAB_SWEEP_RPM, then discovery_settings.probe_rpm, default 30."""
    v = os.environ.get("NIMLAB_SWEEP_RPM")
    if v in (None, ""):
        v = (settings or {}).get("probe_rpm", 30)
    try:
        return max(0.0, float(v))
    except (TypeError, ValueError):
        return 30.0


class HttpResult:
    """Uniform outcome of one HTTP exchange. Never raises for HTTP errors.

    error_kind is one of: None, "http", "timeout", "network", "too_large".
    """

    __slots__ = ("status", "body", "headers", "latency", "error_kind", "error", "url", "attempts")

    def __init__(self, status=None, body=b"", headers=None, latency=0.0,
                 error_kind=None, error=None, url="", attempts=1):
        self.status = status
        self.body = body if body is not None else b""
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.latency = latency
        self.error_kind = error_kind
        self.error = error
        self.url = url
        self.attempts = attempts

    @property
    def ok(self):
        return self.error_kind is None and self.status is not None and 200 <= self.status < 300

    @property
    def text(self):
        if isinstance(self.body, (bytes, bytearray)):
            return self.body.decode("utf-8", errors="replace")
        return str(self.body)

    def json(self):
        """Parsed JSON body, or None when the body is not JSON."""
        try:
            return json.loads(self.text)
        except ValueError:
            return None

    @property
    def content_type(self):
        return self.headers.get("content-type", "").split(";")[0].strip().lower()

    def describe(self):
        """Short, key-free description for logs and the terminal."""
        if self.ok:
            return f"HTTP {self.status} in {self.latency}s"
        if self.error_kind == "http":
            return redact(f"HTTP {self.status}: {error_detail(self.text)}")
        return redact(f"{self.error_kind}: {self.error}")

    def to_dict(self):
        return {
            "status": self.status,
            "ok": self.ok,
            "latency_sec": self.latency,
            "error_kind": self.error_kind,
            "error": redact(self.error) if self.error else None,
            "url": self.url,
            "attempts": self.attempts,
        }


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class HttpClient:
    """Small urllib wrapper with timeouts, retries and size caps.

    `opener` is injectable (a callable like urllib.request.urlopen) so the
    whole stack can be unit-tested without a network.
    """

    def __init__(self, timeout=60, retries=2, backoff=1.5, retry_on_timeout=False,
                 max_bytes=DEFAULT_MAX_BYTES, opener=None, sleep=time.sleep):
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.backoff = backoff
        self.retry_on_timeout = retry_on_timeout
        self.max_bytes = max_bytes
        self._open = opener or urllib.request.urlopen
        self._sleep = sleep

    @classmethod
    def from_settings(cls, settings, **kw):
        s = settings or {}
        return cls(timeout=s.get("timeout_sec", 60), retries=s.get("retries", 2),
                   backoff=s.get("backoff_sec", 1.5), **kw)

    def request(self, method, url, data=None, headers=None, timeout=None,
                max_bytes=None, stream=False):
        """Perform a request. With stream=True the open response is returned
        in result.body (caller must close it) on success."""
        timeout = self.timeout if timeout is None else timeout
        from . import perf  # v3.7.1: a voice call / self-test caps every call it makes
        timeout = perf.capped(timeout)
        max_bytes = self.max_bytes if max_bytes is None else max_bytes
        attempt = 0
        t0 = time.monotonic()
        first, res = self._request(method, url, data, headers, timeout, max_bytes, stream, attempt, t0, perf)
        try:   # 3.7.2: per-call timing for the router benchmark (no-op outside a tracked turn)
            perf.note_http(method, url, len(data or b""), res.status,
                           None if first is None else (first - t0) * 1000, res.latency * 1000,
                           0 if stream else len(res.body or b""), res.attempts, stream, res.error)
        except Exception:  # noqa: BLE001 - timing never breaks a call
            pass
        return res

    def _request(self, method, url, data, headers, timeout, max_bytes, stream, attempt, t0, perf):
        first = None
        while True:
            attempt += 1
            req = urllib.request.Request(url, data=data, headers=dict(headers or {}), method=method)
            try:
                resp = self._open(req, timeout=timeout)
                first = time.monotonic()
                hdrs = dict(resp.headers.items()) if getattr(resp, "headers", None) else {}
                status = getattr(resp, "status", None) or resp.getcode()
                if stream:
                    return first, HttpResult(status, resp, hdrs, round(time.monotonic() - t0, 3), url=url, attempts=attempt)
                try:
                    body = resp.read(max_bytes + 1)
                finally:
                    resp.close()
                if len(body) > max_bytes:
                    return first, HttpResult(status, body[:max_bytes], hdrs, round(time.monotonic() - t0, 3),
                                      "too_large", f"response exceeded {max_bytes} bytes", url, attempt)
                return first, HttpResult(status, body, hdrs, round(time.monotonic() - t0, 3), url=url, attempts=attempt)
            except urllib.error.HTTPError as e:
                first = time.monotonic()      # the server answered (with an error status)
                try:
                    body = e.read(min(max_bytes, 256 * 1024))
                except Exception:
                    body = b""
                hdrs = dict(e.headers.items()) if getattr(e, "headers", None) else {}
                result = HttpResult(e.code, body, hdrs, round(time.monotonic() - t0, 3),
                                    "http", f"HTTP {e.code}", url, attempt)
                if e.code in RETRY_STATUSES and attempt <= self.retries:
                    self._sleep(self._delay(attempt, hdrs))
                    continue
                return first, result
            except (socket.timeout, TimeoutError) as e:
                result = HttpResult(None, b"", {}, round(time.monotonic() - t0, 3),
                                    "timeout", str(e) or "timed out", url, attempt)
                if self.retry_on_timeout and attempt <= self.retries:
                    self._sleep(self._delay(attempt, {}))
                    continue
                return first, result
            except (urllib.error.URLError, ConnectionError, OSError) as e:
                reason = getattr(e, "reason", e)
                kind = "timeout" if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason) else "network"
                result = HttpResult(None, b"", {}, round(time.monotonic() - t0, 3), kind, str(reason), url, attempt)
                if attempt <= self.retries and (kind == "network" or self.retry_on_timeout):
                    self._sleep(self._delay(attempt, {}))
                    continue
                return first, result

    def _delay(self, attempt, headers):
        retry_after = {k.lower(): v for k, v in headers.items()}.get("retry-after")
        if retry_after:
            try:
                return min(30.0, float(retry_after))
            except ValueError:
                pass
        return min(30.0, self.backoff * (2 ** (attempt - 1)))

    def post_json(self, url, payload, headers=None, timeout=None, accept="application/json"):
        h = {"Content-Type": "application/json", "Accept": accept}
        h.update(headers or {})
        return self.request("POST", url, json.dumps(payload).encode("utf-8"), h, timeout)

    def get(self, url, headers=None, timeout=None):
        h = {"Accept": "application/json"}
        h.update(headers or {})
        return self.request("GET", url, None, h, timeout)


# ---------------------------------------------------------------------------
# Wire formats
# ---------------------------------------------------------------------------
def build_multipart(fields):
    """multipart/form-data body.

    fields: a dict or a list of (name, value) pairs. A value is text, or a
    (filename, bytes, content_type) tuple for a file part.
    Returns (body_bytes, content_type). The boundary is random so user text
    can never collide with it.
    """
    boundary = "----nimlab" + secrets.token_hex(16)
    parts = []
    items = fields.items() if isinstance(fields, dict) else fields
    clean = lambda v: str(v).replace('"', "%22").replace("\r", "").replace("\n", "")
    for name, value in items:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        if isinstance(value, tuple) and len(value) == 3:
            filename, data, ctype = value
            parts.append(f'Content-Disposition: form-data; name="{clean(name)}"; filename="{clean(filename)}"\r\n'
                         f"Content-Type: {clean(ctype)}\r\n\r\n".encode("utf-8"))
            parts.append(data if isinstance(data, bytes) else str(data).encode("utf-8"))
        else:
            parts.append(f'Content-Disposition: form-data; name="{clean(name)}"\r\n\r\n'.encode("utf-8"))
            parts.append(str(value).encode("utf-8"))
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def iter_sse(lines, deadline=None):
    """Parse Server-Sent Events from an iterable of byte/str lines.

    Yields dicts {"event": str, "data": str, "id": str|None}. Multi-line
    data fields are joined with newlines per the SSE spec. Stops at the
    optional monotonic deadline.
    """
    event, data, ev_id = "message", [], None
    for raw in lines:
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError("SSE stream exceeded its time limit")
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else raw
        line = line.rstrip("\r\n")
        if line == "":
            if data:
                yield {"event": event, "data": "\n".join(data), "id": ev_id}
            event, data, ev_id = "message", [], None
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "data":
            data.append(value)
        elif field == "event":
            event = value
        elif field == "id":
            ev_id = value
    if data:
        yield {"event": event, "data": "\n".join(data), "id": ev_id}
