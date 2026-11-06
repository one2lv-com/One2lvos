"""
One2lvOS voice proxy: speech-to-text and text-to-speech through the Gemini API,
with the API key kept on the server.

The desktop (o2-voice.js) calls these same-origin endpoints, so the Gemini key
never reaches the browser or the APK.

  GET  /api/voice/status      -> {"gemini": bool, "stt_model": ..., "tts_model": ...}
  POST /api/voice/transcribe  {"audio_b64": "...", "mime_type": "audio/webm"} -> {"text": "..."}
  POST /api/voice/speak       {"text": "...", "voice": "Kore"} -> audio/wav bytes

Key:   GEMINI_API_KEY (environment, or a GEMINI_API_KEY= line in One2lvos/.env).
Models (verified on ai.google.dev, Nov 2026):
  STT  gemini-4-argon        ("Gemini 4 Argon": audio in, text out; no Live API, no audio out)
  TTS  gemini-3.8-flash-tts  (Gemini TTS; Interactions API returns WAV, 24 kHz by default)
Override with GEMINI_STT_MODEL / GEMINI_TTS_MODEL / GEMINI_TTS_VOICE.

The reactor listens on 127.0.0.1 only; outside traffic arrives through the
Cloudflare tunnel, which is behind Cloudflare Access (owner only). These routes
refuse requests that come from anywhere but the local host.
"""
import base64
import os
import re
import time

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT, ".env")
API = "https://generativelanguage.googleapis.com/v1beta/interactions"

STT_MODEL = os.environ.get("GEMINI_STT_MODEL", "gemini-4-argon")
TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
TTS_VOICE = os.environ.get("GEMINI_TTS_VOICE", "Kore")

MAX_AUDIO_BYTES = 8 * 1024 * 1024     # well under the 20 MB inline limit
MAX_TTS_CHARS = 2500
ALLOWED_MIME = {"audio/webm", "audio/ogg", "audio/wav", "audio/mp3", "audio/mpeg",
                "audio/mp4", "audio/m4a", "audio/aac", "audio/flac", "audio/opus"}
_RATE = []          # timestamps of recent upstream calls
RATE_LIMIT = 40     # calls per minute, all routes together

TRANSCRIBE_PROMPT = (
    "Transcribe the speech in this audio exactly as spoken, in the language spoken. "
    "Output only the transcript text, with no labels, quotes or commentary. "
    "If there is no intelligible speech, output nothing."
)


def _key() -> str:
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        return k
    try:
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*(?:export\s+)?GEMINI_API_KEY\s*=\s*['\"]?([^'\"\s#]+)", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return ""


def _guard(request: Request):
    host = (request.client.host if request.client else "") or ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="voice proxy is local/tunnel only")
    now = time.time()
    while _RATE and now - _RATE[0] > 60:
        _RATE.pop(0)
    if len(_RATE) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="voice rate limit, try again in a minute")
    _RATE.append(now)


def _err(resp: httpx.Response) -> str:
    try:
        d = resp.json()
        e = d.get("error") if isinstance(d, dict) else None
        msg = (e.get("message") if isinstance(e, dict) else e) or d.get("detail") or ""
    except Exception:
        msg = resp.text[:200]
    return f"Gemini {resp.status_code}: {str(msg)[:300]}"


def _outputs(data: dict, kind: str):
    out = []
    for step in (data.get("steps") or []):
        if step.get("type") != "model_output":
            continue
        for c in (step.get("content") or []):
            if c.get("type") == kind:
                out.append(c)
    if not out and kind == "text" and isinstance(data.get("output_text"), str):
        out.append({"type": "text", "text": data["output_text"]})
    return out


_client = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
    return _client


@router.get("/api/voice/status")
async def voice_status():
    return {"gemini": bool(_key()), "stt_model": STT_MODEL, "tts_model": TTS_MODEL, "voice": TTS_VOICE}


@router.post("/api/voice/transcribe")
async def voice_transcribe(request: Request):
    _guard(request)
    key = _key()
    if not key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not set on the reactor")
    body = await request.json()
    b64 = str(body.get("audio_b64") or "")
    mime = str(body.get("mime_type") or "audio/webm").split(";")[0].strip().lower()
    if mime not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"unsupported audio type {mime}")
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="audio_b64 is not valid base64")
    if not raw:
        raise HTTPException(status_code=400, detail="empty audio")
    if len(raw) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="audio clip too long")
    payload = {
        "model": STT_MODEL,
        "input": [
            {"type": "text", "text": TRANSCRIBE_PROMPT},
            {"type": "audio", "data": b64, "mime_type": mime},
        ],
        "generation_config": {"thinking_level": "low", "max_output_tokens": 2048},
    }
    r = await _http().post(API, json=payload, headers={"x-goog-api-key": key})
    if r.status_code != 200:
        return JSONResponse({"error": _err(r)}, status_code=502)
    text = "".join(c.get("text", "") for c in _outputs(r.json(), "text")).strip()
    return {"text": text, "model": STT_MODEL}


@router.post("/api/voice/speak")
async def voice_speak(request: Request):
    _guard(request)
    key = _key()
    if not key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not set on the reactor")
    body = await request.json()
    text = str(body.get("text") or "").strip()[:MAX_TTS_CHARS]
    voice = re.sub(r"[^A-Za-z]", "", str(body.get("voice") or TTS_VOICE))[:32] or TTS_VOICE
    if not text:
        raise HTTPException(status_code=400, detail="no text")
    payload = {
        "model": TTS_MODEL,
        "input": [{"type": "user_input", "content": [{"type": "text", "text": text}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }
    r = await _http().post(API, json=payload, headers={"x-goog-api-key": key})
    if r.status_code != 200:
        return JSONResponse({"error": _err(r)}, status_code=502)
    audio = _outputs(r.json(), "audio")
    if not audio or not audio[-1].get("data"):
        return JSONResponse({"error": "Gemini returned no audio"}, status_code=502)
    wav = base64.b64decode(audio[-1]["data"])
    mime = audio[-1].get("mime_type") or "audio/wav"
    return Response(content=wav, media_type=mime, headers={"Cache-Control": "no-store"})
