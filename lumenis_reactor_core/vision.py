"""Lumenis live vision: user-shared screen or stream -> sampled frames -> NVIDIA hosted VLM -> observations.

What this is
    A per-frame pipeline. The owner starts a session (browser screen share at /vision, or a stream URL that
    ffmpeg can pull: RTSP/RTMP/SRT/HLS/HTTP). Frames are sampled at a bounded rate, re-encoded, and sent one
    at a time to an NVIDIA-hosted vision-language model on integrate.api.nvidia.com. Each answer becomes an
    observation with timestamps, freshness, model, confidence and what the model said it could not tell.

What this is not
    - Not the NVIDIA VSS blueprint (that needs a self-hosted GPU deployment; see docs/LUMENIS_VISION.md).
    - Not game telemetry. A frame shows pixels only: hitboxes, cooldowns, frame data, inputs and hidden
      timers are NOT visible and the model is told to say so rather than guess.
    - Not covert. Nothing captures unless the owner starts a session; sessions expire; no frame is written
      to disk (only the text observations, under data/vision/).

Interface for other parts of the reactor (e.g. Discord voice)
    GET  /api/vision/status                     session + counters + latest observation
    GET  /api/vision/latest?since=<id>          observations newer than id (poll every ~1-2 s)
    GET  /api/vision/events                     Server-Sent Events, one JSON observation per event
    In-process: vision.latest(), vision.prompt_block(), vision.subscribe()
    Each observation has a short `callout` (or null) meant to be spoken, and `fresh_s` (age in seconds).
    Speak only callouts with fresh_s under a few seconds; drop stale ones.
"""
from __future__ import annotations

import asyncio
import base64
import io
import ipaddress
import json
import os
import re
import shutil
import socket
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse

# ── configuration (env overrides) ────────────────────────────────────────────────────────────
NIM_URL = os.getenv("LUMENIS_VISION_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
MODEL = os.getenv("LUMENIS_VISION_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")   # ~2-3 s/frame
FALLBACK_MODEL = os.getenv("LUMENIS_VISION_FALLBACK_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
MIN_INTERVAL_S = float(os.getenv("LUMENIS_VISION_MIN_INTERVAL_S", "1.5"))   # floor between model calls
DEFAULT_INTERVAL_S = float(os.getenv("LUMENIS_VISION_INTERVAL_S", "3"))
MAX_CALLS_PER_MIN = int(os.getenv("LUMENIS_VISION_MAX_PER_MIN", "20"))
MAX_SESSION_MIN = int(os.getenv("LUMENIS_VISION_MAX_SESSION_MIN", "120"))
IDLE_TIMEOUT_S = int(os.getenv("LUMENIS_VISION_IDLE_S", "90"))              # browser: no frames -> stop
MAX_FRAME_BYTES = 4 * 1024 * 1024
MAX_SIDE = 1280                       # frames are downscaled to this before inference
MAX_INPUT_SIDE = 8192
CALL_TIMEOUT_S = 25.0
STALE_S = 30                          # observations older than this are not given to the council
ALLOW_LOCAL_STREAMS = os.getenv("LUMENIS_VISION_ALLOW_LOCAL", "0") == "1"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "vision"
STREAM_SCHEMES = {"rtsp", "rtsps", "rtmp", "rtmps", "srt", "http", "https"}

HIDDEN_INFO = ("hitboxes, hurtboxes, cooldowns, frame data, inputs, exact damage numbers unless shown on screen, "
               "and anything off-screen")

SYSTEM_PROMPT = (
    "You are the eyes of Lumenis, looking at ONE still frame from a screen the owner chose to share. "
    "Report only what is visible in this frame. Do not guess player names, stocks, damage, timers or items that "
    f"you cannot read clearly. You CANNOT see {HIDDEN_INFO}; never claim them. A single frame has no motion, so "
    "do not describe moves as happening unless the pose or effect makes it obvious, and say it is a guess. "
    "Answer with ONLY a JSON object, no prose, with keys: "
    '"scene" (one of gameplay, menu, loading, results, not_game, unclear), '
    '"game" (name only if clearly identifiable from the frame, else null), '
    '"summary" (one plain sentence), '
    '"players" (list of short strings, one per visible fighter: position on screen and anything readable), '
    '"hud" (object: timer, stocks, damage - exact text you can read, else null), '
    '"events" (list of short strings: visible things like a fighter off-stage, a weapon on the ground, a KO splash), '
    '"callout" (at most 8 words a teammate could act on, ONLY if the frame clearly supports it, else null), '
    '"confidence" (low, medium or high), '
    '"cannot_tell" (list of short strings: what you could not determine).'
)


# ── state ───────────────────────────────────────────────────────────────────────────────────────
@dataclass
class Session:
    id: str
    source: str                      # "browser" | "stream"
    label: str
    game: str | None
    interval_s: float
    started_ts: float
    expires_ts: float
    url_host: str | None = None      # stream sessions: host only (never the full URL, it may hold a key)
    last_frame_ts: float = 0.0
    frames_in: int = 0
    frames_dropped: int = 0          # replaced by a newer frame before analysis (backpressure)
    frames_rejected: int = 0
    analyzed: int = 0
    errors: int = 0
    last_error: str | None = None
    ended_ts: float | None = None
    end_reason: str | None = None

    def public(self) -> dict:
        now = time.time()
        return {
            "id": self.id, "source": self.source, "label": self.label, "game": self.game,
            "interval_s": self.interval_s, "url_host": self.url_host,
            "started_at": _iso(self.started_ts), "expires_at": _iso(self.expires_ts),
            "active": self.ended_ts is None,
            "ended_at": _iso(self.ended_ts) if self.ended_ts else None, "end_reason": self.end_reason,
            "last_frame_age_s": round(now - self.last_frame_ts, 1) if self.last_frame_ts else None,
            "frames_in": self.frames_in, "frames_dropped": self.frames_dropped,
            "frames_rejected": self.frames_rejected, "analyzed": self.analyzed,
            "errors": self.errors, "last_error": self.last_error,
        }


@dataclass
class _Frame:
    jpeg: bytes
    captured_ts: float               # when the frame was captured (client clock for browser, server for stream)
    received_ts: float               # when the reactor got it
    width: int
    height: int


@dataclass
class _State:
    session: Session | None = None
    pending: _Frame | None = None
    new_frame: asyncio.Event = field(default_factory=asyncio.Event)
    worker: asyncio.Task | None = None
    puller: asyncio.Task | None = None
    ffmpeg: asyncio.subprocess.Process | None = None
    observations: deque = field(default_factory=lambda: deque(maxlen=100))
    call_times: deque = field(default_factory=lambda: deque(maxlen=200))
    subscribers: set = field(default_factory=set)
    seq: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_S = _State()


def _iso(ts: float | None) -> str | None:
    if not ts:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + f".{int((ts % 1) * 1000):03d}Z"


def _key() -> str:
    return os.getenv("LUMENIS_VISION_KEY") or os.getenv("NVIDIA_API_KEY") or ""


# ── frame validation / normalisation ────────────────────────────────────────────────────────────
def normalize_frame(raw: bytes) -> tuple[bytes, int, int]:
    """Validate an uploaded image and re-encode it as a bounded JPEG. Raises ValueError with a clear reason."""
    if not raw:
        raise ValueError("empty frame")
    if len(raw) > MAX_FRAME_BYTES:
        raise ValueError(f"frame too large ({len(raw)} bytes; limit {MAX_FRAME_BYTES})")
    if not (raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n"
            or (raw[:4] == b"RIFF" and raw[8:12] == b"WEBP")):
        raise ValueError("not a JPEG, PNG or WebP image")
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = MAX_INPUT_SIDE * MAX_INPUT_SIDE
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.width > MAX_INPUT_SIDE or im.height > MAX_INPUT_SIDE or im.width < 32 or im.height < 32:
                raise ValueError(f"frame size {im.width}x{im.height} out of range")
            im = im.convert("RGB")
            im.thumbnail((MAX_SIDE, MAX_SIDE))
            out = io.BytesIO()
            im.save(out, "JPEG", quality=80)      # re-encode: drops metadata and any trailing payload
            return out.getvalue(), im.width, im.height
    except ValueError:
        raise
    except Exception as e:  # PIL decode errors, decompression bombs
        raise ValueError(f"could not decode image ({type(e).__name__})")


def validate_stream_url(url: str) -> str:
    """Allow only network video URLs ffmpeg should pull; block files, odd protocols and internal addresses."""
    url = (url or "").strip()
    if not url or len(url) > 1000 or any(c.isspace() for c in url) or url.startswith("-"):
        raise ValueError("stream URL missing or malformed")
    p = urlparse(url)
    if p.scheme.lower() not in STREAM_SCHEMES:
        raise ValueError(f"unsupported scheme '{p.scheme}' (allowed: {', '.join(sorted(STREAM_SCHEMES))})")
    host = p.hostname
    if not host:
        raise ValueError("stream URL has no host")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise ValueError(f"cannot resolve host '{host}'")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
            raise ValueError("stream host resolves to a blocked address")
        if (ip.is_loopback or ip.is_private) and not ALLOW_LOCAL_STREAMS:
            raise ValueError("stream host is a local/private address (set LUMENIS_VISION_ALLOW_LOCAL=1 to allow)")
    return url


def _ffmpeg_bin() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


# ── model call ──────────────────────────────────────────────────────────────────────────────────
def _parse_json(text: str) -> dict | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


async def _call_vlm(client: httpx.AsyncClient, jpeg: bytes, game: str | None, model: str) -> tuple[dict, dict]:
    hint = (f" The owner says the game is probably {game}; still report only what you see." if game else "")
    body = {
        "model": model, "temperature": 0.1, "max_tokens": 450,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Frame:" + hint},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}},
            ]},
        ],
    }
    r = await client.post(NIM_URL, json=body, timeout=CALL_TIMEOUT_S,
                          headers={"Authorization": f"Bearer {_key()}", "Accept": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"{model} HTTP {r.status_code}: {r.text[:160]}")
    d = r.json()
    text = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    parsed = _parse_json(text)
    if parsed is None:
        raise RuntimeError(f"{model} returned no JSON ({text[:120]!r})")
    return parsed, d.get("usage") or {}


def _clean(parsed: dict) -> dict:
    def s(v, n=240):
        return str(v).strip()[:n] if v not in (None, "", "null") else None

    def item(x):
        if isinstance(x, dict):  # some models answer {"position": ..., "readable": ...}
            return ": ".join(str(val).strip() for val in x.values() if val not in (None, ""))
        return str(x).strip()

    def lst(v, n=8):
        return [item(x)[:160] for x in v if item(x)][:n] if isinstance(v, list) else []

    hud = parsed.get("hud") if isinstance(parsed.get("hud"), dict) else {}
    conf = str(parsed.get("confidence", "low")).lower()
    scene = str(parsed.get("scene", "unclear")).lower()
    return {
        "scene": scene if scene in {"gameplay", "menu", "loading", "results", "not_game", "unclear"} else "unclear",
        "game": s(parsed.get("game"), 60),
        "summary": s(parsed.get("summary")) or "(no summary)",
        "players": lst(parsed.get("players")),
        "hud": {k: s(hud.get(k), 60) for k in ("timer", "stocks", "damage")},
        "events": lst(parsed.get("events")),
        "callout": s(parsed.get("callout"), 80),
        "confidence": conf if conf in {"low", "medium", "high"} else "low",
        "cannot_tell": lst(parsed.get("cannot_tell")),
    }


# ── observations ────────────────────────────────────────────────────────────────────────────────
def _with_age(o: dict) -> dict:
    o = dict(o)
    o["fresh_s"] = round(time.time() - o["captured_ts"], 1)
    return o


def latest(since: int = 0, limit: int = 20) -> list[dict]:
    return [_with_age(o) for o in list(_S.observations) if o["id"] > since][-limit:]


async def subscribe():
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _S.subscribers.add(q)
    try:
        while True:
            yield await q.get()
    finally:
        _S.subscribers.discard(q)


def _publish(o: dict) -> None:
    _S.observations.append(o)
    for q in list(_S.subscribers):
        if q.full():
            try:
                q.get_nowait()          # slow consumer: drop its oldest, never block the pipeline
            except Exception:
                pass
        q.put_nowait(o)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "observations.jsonl", "a") as f:
            f.write(json.dumps(o) + "\n")
    except Exception:
        pass


def prompt_block() -> str:
    """Text for the council's status block. Visual observations are labelled as such, never as facts."""
    sess = _S.session
    if not sess or sess.ended_ts:
        return ("- Live vision: OFF - no screen share or stream is running, so you cannot see any game or screen right "
                "now. Do not describe what is on screen.")
    fresh = [o for o in _S.observations if o["session"] == sess.id and time.time() - o["captured_ts"] <= STALE_S]
    head = (f"- Live vision: ON ({sess.source}, {sess.label}; started {_iso(sess.started_ts)}). Lines below are a vision "
            f"model's reading of single frames: observations, NOT verified facts. You cannot see {HIDDEN_INFO}. "
            "Say 'from the screen' and give the age when you use them.")
    if not fresh:
        return head + "\n  (no frame analysed in the last 30 s - say you have nothing current from the screen)"
    lines = [head]
    for o in fresh[-3:]:
        age = int(time.time() - o["captured_ts"])
        extra = "; ".join(o["events"][:3])
        hud = ", ".join(f"{k} {v}" for k, v in o["hud"].items() if v)
        lines.append(f"  - [{age}s old, {o['confidence']} confidence, {o['scene']}] {o['summary']}"
                     + (f" HUD: {hud}." if hud else "") + (f" Events: {extra}." if extra else "")
                     + (f" Unsure: {'; '.join(o['cannot_tell'][:2])}." if o["cannot_tell"] else ""))
    return "\n".join(lines)


# ── worker: one model call in flight, newest frame wins ─────────────────────────────────────────
async def _worker(sess: Session) -> None:
    backoff = 0.0
    last_call = 0.0
    async with httpx.AsyncClient() as client:
        while _S.session is sess and sess.ended_ts is None:
            try:
                await asyncio.wait_for(_S.new_frame.wait(), timeout=5)
            except asyncio.TimeoutError:
                _check_expiry(sess)
                continue
            _S.new_frame.clear()
            # rate limits: session interval, global floor, per-minute cap, error backoff
            wait = max(sess.interval_s, MIN_INTERVAL_S) - (time.time() - last_call)
            now = time.time()
            while _S.call_times and now - _S.call_times[0] > 60:
                _S.call_times.popleft()
            if len(_S.call_times) >= MAX_CALLS_PER_MIN:
                wait = max(wait, 60 - (now - _S.call_times[0]))
            wait = max(wait, backoff)
            end = time.time() + wait
            while time.time() < end and _S.session is sess and sess.ended_ts is None:
                await asyncio.sleep(min(1.0, max(0.0, end - time.time())))   # interruptible: stop/idle seen within 1 s
                _check_expiry(sess)
            frame, _S.pending = _S.pending, None
            if frame is None or _S.session is not sess or sess.ended_ts:
                continue
            last_call = time.time()
            _S.call_times.append(last_call)
            model = MODEL
            try:
                try:
                    parsed, usage = await _call_vlm(client, frame.jpeg, sess.game, model)
                except Exception as first:
                    if not FALLBACK_MODEL or FALLBACK_MODEL == MODEL:
                        raise
                    model = FALLBACK_MODEL
                    sess.last_error = f"primary failed, used fallback: {(str(first) or type(first).__name__)[:120]}"
                    parsed, usage = await _call_vlm(client, frame.jpeg, sess.game, model)
                done = time.time()
                _S.seq += 1
                obs = {
                    "id": _S.seq, "session": sess.id, "source": sess.source, "label": sess.label,
                    "kind": "visual_observation", "verified": False, "model": model,
                    "captured_ts": frame.captured_ts, "captured_at": _iso(frame.captured_ts),
                    "received_at": _iso(frame.received_ts), "analyzed_at": _iso(done),
                    "inference_s": round(done - last_call, 2),
                    "end_to_end_s": round(done - frame.captured_ts, 2),
                    "queue_s": round(last_call - frame.received_ts, 2),
                    "frame_size": f"{frame.width}x{frame.height}",
                    "tokens": usage.get("total_tokens"),
                    **_clean(parsed),
                }
                sess.analyzed += 1
                backoff = 0.0
                _publish(obs)
            except Exception as e:
                sess.errors += 1
                sess.last_error = (str(e) or type(e).__name__)[:200]
                backoff = min(30.0, max(2.0, backoff * 2))
            _check_expiry(sess)


def _check_expiry(sess: Session) -> None:
    now = time.time()
    if sess.ended_ts:
        return
    if now > sess.expires_ts:
        asyncio.get_running_loop().create_task(stop_session("expired (max session length)"))
    elif sess.source == "browser" and now - (sess.last_frame_ts or sess.started_ts) > IDLE_TIMEOUT_S:
        asyncio.get_running_loop().create_task(stop_session(f"no frames for {IDLE_TIMEOUT_S}s"))


# ── intake ──────────────────────────────────────────────────────────────────────────────────────
def _accept(sess: Session, jpeg: bytes, w: int, h: int, captured_ts: float) -> None:
    now = time.time()
    # clamp client clocks: no future frames, nothing older than 60 s counts as live
    if not captured_ts or captured_ts > now + 2 or captured_ts < now - 60:
        captured_ts = now
    if _S.pending is not None:
        sess.frames_dropped += 1
    _S.pending = _Frame(jpeg, captured_ts, now, w, h)
    sess.frames_in += 1
    sess.last_frame_ts = now
    _S.new_frame.set()


async def submit_frame(session_id: str, raw: bytes, captured_ts: float | None) -> dict:
    sess = _S.session
    if not sess or sess.ended_ts or sess.id != session_id:
        raise HTTPException(409, "no active vision session with that id (start one first)")
    if sess.source != "browser":
        raise HTTPException(409, "this session pulls a stream; it does not take uploaded frames")
    try:
        jpeg, w, h = await asyncio.to_thread(normalize_frame, raw)
    except ValueError as e:
        sess.frames_rejected += 1
        raise HTTPException(400, f"frame rejected: {e}")
    _accept(sess, jpeg, w, h, captured_ts or 0)
    return {"accepted": True, "frame_size": f"{w}x{h}", "frames_in": sess.frames_in,
            "frames_dropped": sess.frames_dropped}


async def _pull_stream(sess: Session, url: str) -> None:
    """ffmpeg pulls the stream and emits one JPEG per interval on stdout; we split on JPEG markers."""
    exe = _ffmpeg_bin()
    fps = 1.0 / max(sess.interval_s, MIN_INTERVAL_S)
    args = [exe, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-protocol_whitelist", "rtsp,rtsps,rtmp,rtmps,srt,udp,rtp,tcp,tls,http,https,hls,crypto,httpproxy",
            "-rw_timeout", "15000000"]
    if url.startswith(("rtsp", "rtsps")):
        args += ["-rtsp_transport", "tcp"]
    args += ["-fflags", "nobuffer", "-i", url, "-an",
             "-vf", f"fps={fps:.4f},scale='min({MAX_SIDE},iw)':-2",
             "-q:v", "5", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"]
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.PIPE)
    _S.ffmpeg = proc
    buf = b""
    try:
        while _S.session is sess and sess.ended_ts is None:
            chunk = await proc.stdout.read(65536)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 3 * MAX_FRAME_BYTES:
                buf = buf[-MAX_FRAME_BYTES:]
            while True:
                s = buf.find(b"\xff\xd8")
                e = buf.find(b"\xff\xd9", s + 2) if s >= 0 else -1
                if s < 0 or e < 0:
                    break
                jpeg, buf = buf[s:e + 2], buf[e + 2:]
                try:
                    jpeg, w, h = await asyncio.to_thread(normalize_frame, jpeg)
                except ValueError:
                    sess.frames_rejected += 1
                    continue
                _accept(sess, jpeg, w, h, time.time())
        err = (await proc.stderr.read())[-300:].decode("utf-8", "replace").strip() if proc.stderr else ""
        if sess.ended_ts is None:
            sess.last_error = ("stream ended" + (f": {err}" if err else ""))[:200]
            await stop_session("stream ended or could not be read")
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()


# ── session control ─────────────────────────────────────────────────────────────────────────────
async def start_session(source: str, label: str = "", game: str | None = None, interval_s: float | None = None,
                        max_minutes: int | None = None, url: str | None = None) -> Session:
    if not _key():
        raise HTTPException(503, "no NVIDIA API key configured for vision")
    if source not in ("browser", "stream"):
        raise HTTPException(400, "source must be 'browser' or 'stream'")
    interval = max(MIN_INTERVAL_S, min(float(interval_s or DEFAULT_INTERVAL_S), 60.0))
    minutes = max(1, min(int(max_minutes or MAX_SESSION_MIN), MAX_SESSION_MIN))
    game = (re.sub(r"[^\w .:'&-]", "", game)[:40] or None) if game else None
    label = re.sub(r"[^\w .:'&#-]", "", label or "")[:60] or ("screen share" if source == "browser" else "stream")
    host = None
    if source == "stream":
        if not _ffmpeg_bin():
            raise HTTPException(503, "ffmpeg is not installed on the reactor host")
        try:
            url = await asyncio.to_thread(validate_stream_url, url or "")
        except ValueError as e:
            raise HTTPException(400, str(e))
        host = urlparse(url).hostname
    async with _S.lock:
        if _S.session and not _S.session.ended_ts:
            await stop_session("replaced by a new session", _locked=True)
        now = time.time()
        sess = Session(id=uuid.uuid4().hex[:12], source=source, label=label, game=game, interval_s=interval,
                       started_ts=now, expires_ts=now + minutes * 60, url_host=host)
        _S.session, _S.pending = sess, None
        _S.new_frame.clear()
        _S.worker = asyncio.create_task(_worker(sess))
        if source == "stream":
            _S.puller = asyncio.create_task(_pull_stream(sess, url))
    return sess


async def stop_session(reason: str = "stopped by owner", _locked: bool = False) -> Session | None:
    sess = _S.session
    if not sess or sess.ended_ts:
        return sess
    sess.ended_ts, sess.end_reason = time.time(), reason
    _S.pending = None
    _S.new_frame.set()                     # wake the worker so it exits
    if _S.ffmpeg and _S.ffmpeg.returncode is None:
        try:
            _S.ffmpeg.kill()
        except ProcessLookupError:
            pass
    return sess


def status() -> dict:
    sess = _S.session
    obs = list(_S.observations)
    return {
        "session": sess.public() if sess else None,
        "model": MODEL, "fallback_model": FALLBACK_MODEL, "backend": NIM_URL,
        "limits": {"min_interval_s": MIN_INTERVAL_S, "max_calls_per_min": MAX_CALLS_PER_MIN,
                   "max_session_min": MAX_SESSION_MIN, "idle_timeout_s": IDLE_TIMEOUT_S,
                   "max_frame_bytes": MAX_FRAME_BYTES, "analysed_frame_max_side": MAX_SIDE},
        "ffmpeg": bool(_ffmpeg_bin()),
        "latest": _with_age(obs[-1]) if obs else None,
        "cannot_see": HIDDEN_INFO,
    }


# ── HTTP routes ─────────────────────────────────────────────────────────────────────────────────
router = APIRouter()
_PAGE = Path(__file__).resolve().parent.parent / "static" / "vision.html"


@router.get("/vision", response_class=HTMLResponse)
async def vision_page():
    return HTMLResponse(_PAGE.read_text() if _PAGE.exists() else "<h1>vision page missing</h1>")


@router.post("/api/vision/session/start")
async def api_start(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    sess = await start_session(source=str(body.get("source", "browser")), label=str(body.get("label", "")),
                               game=body.get("game"), interval_s=body.get("interval_s"),
                               max_minutes=body.get("max_minutes"), url=body.get("url"))
    return {"ok": True, "session": sess.public()}


@router.post("/api/vision/session/stop")
async def api_stop():
    sess = await stop_session("stopped by owner")
    return {"ok": True, "session": sess.public() if sess else None}


@router.post("/api/vision/frame")
async def api_frame(request: Request):
    sid = request.headers.get("x-vision-session", "")
    try:
        cap = float(request.headers.get("x-captured-at", "0")) / 1000.0
    except ValueError:
        cap = 0.0
    clen = int(request.headers.get("content-length") or 0)
    if clen > MAX_FRAME_BYTES:
        raise HTTPException(413, "frame too large")
    raw = await request.body()
    return await submit_frame(sid, raw, cap)


@router.get("/api/vision/status")
async def api_status():
    return status()


@router.get("/api/vision/latest")
async def api_latest(since: int = 0, limit: int = 20):
    return {"observations": latest(since, max(1, min(limit, 100))),
            "session_active": bool(_S.session and not _S.session.ended_ts)}


@router.get("/api/vision/events")
async def api_events():
    async def gen():
        yield ": connected\n\n"
        async for o in subscribe():
            yield f"data: {json.dumps(_with_age(o))}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
