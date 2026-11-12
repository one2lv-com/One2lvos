"""NVIDIA model calls: chat, streaming chat, embeddings, vision, OCR, TTS,
rerank, image generation, ASR, and video/audio parts on chat.

Every call returns a ModelResult with the same shape, so callers never
have to guess whether they got text, an error string, or a dict.
"""

import base64
import io
import json
import mimetypes
import os
import time
import wave

from . import config
from .core import HttpClient, build_multipart, iter_sse, load_api_key, redact
from .router import NvidiaRouter

INTEGRATE = "https://integrate.api.nvidia.com/v1"
DEFAULT_TTS_URL = config.DEFAULT_CLUSTER["voice_settings"]["tts_url"]
OCR_PROMPT = ("Transcribe all text in this image exactly as written, line by line. "
              "Output only the transcribed text, no commentary.")


class ModelResult:
    """Outcome of one model call.

    ok       -> True only for a successful, usable answer
    text     -> model text (chat/vision/ocr); "" on failure
    data     -> parsed payload (embeddings list, audio bytes, raw JSON)
    usage    -> token usage dict when the API reports it
    latency  -> seconds
    error    -> key-free error description when ok is False
    """

    def __init__(self, ok, text="", data=None, usage=None, latency=0.0, error=None, status=None, raw=None,
                 files=None):
        self.ok = ok
        self.files = list(files or [])   # saved outputs (images, audio) when the call made any
        self.text = text or ""
        self.data = data
        self.usage = usage or {}
        self.latency = latency
        self.error = error
        self.status = status
        self.raw = raw

    @property
    def completion_tokens(self):
        tok = self.usage.get("completion_tokens")
        if isinstance(tok, int):
            return tok
        return len(self.text.split())  # rough fallback

    @property
    def tokens_per_sec(self):
        if not self.ok or self.latency <= 0:
            return None
        return round(self.completion_tokens / self.latency, 2)

    def __repr__(self):
        return f"ModelResult(ok={self.ok}, status={self.status}, latency={self.latency}, error={self.error!r})"


def _fail(res, prefix=""):
    return ModelResult(False, latency=res.latency, error=(prefix + res.describe()), status=res.status,
                       raw=res.json())


def image_to_data_url(path_or_url):
    """Local file -> data: URL. http(s)/data URLs pass through. None if unreadable."""
    ref = (path_or_url or "").strip()
    if not ref:
        return None
    if ref.startswith(("http://", "https://", "data:")):
        return ref
    if os.path.isfile(ref):
        mime = mimetypes.guess_type(ref)[0] or "image/png"
        with open(ref, "rb") as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode('ascii')}"
    return None


def bytes_to_data_url(data, mime="image/png"):
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def wav_duration(data):
    """Real duration of a WAV from its header; falls back to 22.05kHz/16-bit mono."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            frames, rate = w.getnframes(), w.getframerate()
            if rate > 0 and frames > 0:
                return round(frames / float(rate), 3)
    except (wave.Error, EOFError):
        pass
    return round(len(data) / 44100.0, 3)


def is_wav(data):
    return isinstance(data, (bytes, bytearray)) and len(data) > 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def _collect_text(obj, depth=0):
    """Pull 'text'/'markdown' strings out of nested tool-call arguments."""
    if depth > 6:
        return []
    if isinstance(obj, str):
        return [obj]
    out = []
    if isinstance(obj, dict):
        for k in ("text", "markdown", "content"):
            if isinstance(obj.get(k), str):
                out.append(obj[k])
        for v in obj.values():
            if isinstance(v, (list, dict)):
                out.extend(_collect_text(v, depth + 1))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_collect_text(v, depth + 1))
    return out


class NimClient:
    def __init__(self, api_key=None, http=None, router=None, cluster=None):
        self.cluster = cluster if cluster is not None else config.load_cluster_config()
        self.http = http or HttpClient.from_settings(self.cluster.get("http_settings"))
        self._router = router
        self._api_key = api_key

    # -- plumbing ---------------------------------------------------------
    @property
    def api_key(self):
        return self._api_key if self._api_key is not None else load_api_key()

    @api_key.setter
    def api_key(self, value):
        self._api_key = value

    @property
    def router(self):
        if self._router is None:
            self._router = NvidiaRouter()
        return self._router

    def auth_headers(self):
        key = self.api_key
        return {"Authorization": f"Bearer {key}"} if key else {}

    def integrate(self):
        try:
            return self.router.gateway("integrate", INTEGRATE) or INTEGRATE
        except (FileNotFoundError, ValueError):
            return INTEGRATE

    def post(self, url, payload, timeout=None, accept="application/json"):
        """Raw JSON POST with auth. Returns core.HttpResult."""
        return self.http.post_json(url, payload, self.auth_headers(), timeout, accept)

    def get(self, url, timeout=None):
        return self.http.get(url, self.auth_headers(), timeout)

    # -- catalog ----------------------------------------------------------
    def list_models(self, base=None, timeout=30):
        res = self.get(f"{(base or self.integrate()).rstrip('/')}/models", timeout)
        if not res.ok:
            return _fail(res)
        body = res.json()
        raw = body.get("data", []) if isinstance(body, dict) else (body or [])
        return ModelResult(True, data=[m for m in raw if isinstance(m, dict)], latency=res.latency, status=res.status)

    # -- chat -------------------------------------------------------------
    @staticmethod
    def _chat_text(body):
        try:
            msg = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            return None
        content = msg.get("content")
        if isinstance(content, list):  # some APIs return content parts
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        if not content:
            # document parsers (e.g. nemotron-parse) answer through tool_calls
            parts = []
            for tc in msg.get("tool_calls") or []:
                args = (tc.get("function") or {}).get("arguments") if isinstance(tc, dict) else None
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        parts.append(args)
                        continue
                parts.extend(_collect_text(args))
            content = "\n".join(p for p in parts if p)
        return content or msg.get("reasoning_content") or ""

    def chat(self, model, messages, temperature=0.7, max_tokens=1024, url=None, timeout=None, extra=None):
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, "stream": False}
        payload.update(extra or {})
        res = self.post(url or f"{self.integrate()}/chat/completions", payload, timeout)
        if not res.ok:
            return _fail(res)
        body = res.json()
        text = self._chat_text(body)
        if text is None:
            return ModelResult(False, latency=res.latency, status=res.status, raw=body,
                               error=f"unexpected response shape: {res.text[:200]}")
        return ModelResult(True, text=text, usage=body.get("usage") or {}, latency=res.latency,
                           status=res.status, raw=body)

    def chat_stream(self, model, messages, on_token=None, temperature=0.7, max_tokens=1024, url=None, timeout=None):
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, "stream": True}
        h = dict(self.auth_headers(), **{"Content-Type": "application/json", "Accept": "text/event-stream"})
        t0 = time.monotonic()
        res = self.http.request("POST", url or f"{self.integrate()}/chat/completions",
                                json.dumps(payload).encode("utf-8"), h, timeout, stream=True)
        if not res.ok:
            return _fail(res)
        tokens, usage = [], {}
        resp = res.body
        try:
            for ev in iter_sse(resp):
                if ev["data"].strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(ev["data"])
                except ValueError:
                    continue
                usage = chunk.get("usage") or usage
                choices = chunk.get("choices") or [{}]
                delta = choices[0].get("delta", {}) if choices else {}
                tok = delta.get("content") or delta.get("reasoning_content") or ""
                if tok:
                    tokens.append(tok)
                    if on_token:
                        on_token(tok)
        except Exception as e:  # network drop mid-stream
            return ModelResult(False, text="".join(tokens), latency=round(time.monotonic() - t0, 3),
                               error=redact(f"stream interrupted: {e}"), status=res.status)
        finally:
            resp.close()
        return ModelResult(True, text="".join(tokens), usage=usage, latency=round(time.monotonic() - t0, 3),
                           status=res.status)

    # -- vision / OCR -----------------------------------------------------
    def vision(self, model, image_url, prompt, system=None, temperature=0.2, max_tokens=512, timeout=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]})
        return self.chat(model, messages, temperature, max_tokens, timeout=timeout)

    def ocr(self, model, image_url, prompt=OCR_PROMPT, timeout=None):
        return self.vision(model, image_url, prompt, temperature=0.0, max_tokens=1024, timeout=timeout)

    # -- embeddings -------------------------------------------------------
    def embed(self, model, texts, input_type=None, url=None, timeout=None):
        """Embeds a list of texts. Retries once without input_type when the
        model rejects that field. data -> list of vectors."""
        url = url or f"{self.integrate()}/embeddings"
        payload = {"model": model, "input": list(texts), "encoding_format": "float"}
        if input_type:
            payload["input_type"] = input_type
        res = self.post(url, payload, timeout)
        if not res.ok and input_type and res.status in (400, 422):
            payload.pop("input_type", None)
            res = self.post(url, payload, timeout)
        if not res.ok:
            return _fail(res)
        body = res.json()
        try:
            items = sorted(body["data"], key=lambda d: d.get("index", 0))
            vectors = [d["embedding"] for d in items]
        except (KeyError, TypeError):
            return ModelResult(False, latency=res.latency, status=res.status,
                               error=f"unexpected embeddings shape: {res.text[:200]}")
        return ModelResult(True, data=vectors, usage=(body.get("usage") or {}), latency=res.latency,
                           status=res.status)

    # -- TTS (Magpie via NVCF multipart) -----------------------------------
    def tts_url(self):
        return (os.environ.get("NIMLAB_TTS_URL")
                or self.cluster.get("voice_settings", {}).get("tts_url")
                or DEFAULT_TTS_URL)

    def tts(self, text, voice=None, language=None, timeout=35, url=None, audio_prompt=None,
            audio_prompt_transcript=None, prompt_field="audio_prompt"):
        """data -> WAV bytes on success.

        audio_prompt: (filename, wav_bytes) of a reference clip for zero-shot
        voice cloning, sent as a multipart file part in prompt_field (the TTS
        NIM's documented field is audio_prompt)."""
        vs = self.cluster.get("voice_settings", {})
        fields = [
            ("text", text),
            ("language", language or vs.get("language", "en-US")),
            ("encoding", "LINEAR_PCM"),
        ]
        v = voice if voice is not None else vs.get("voice_name", "Magpie-Multilingual.EN-US.Aria")
        if v:
            fields.append(("voice", v))
        if audio_prompt:
            name, data = audio_prompt
            fields.append((prompt_field or "audio_prompt", (name, data, "audio/wav")))
            if audio_prompt_transcript:
                fields.append(("audio_prompt_transcript", audio_prompt_transcript))
        body, ctype = build_multipart(fields)
        h = dict(self.auth_headers(), **{"Content-Type": ctype, "Accept": "audio/wav, application/json"})
        res = self.http.request("POST", url or self.tts_url(), body, h, timeout)
        if not res.ok:
            return _fail(res)
        audio = res.body
        if len(audio) <= 200:
            return ModelResult(False, latency=res.latency, status=res.status,
                               error=f"empty or invalid audio ({len(audio)} bytes)")
        return ModelResult(True, data=audio, latency=res.latency, status=res.status)

    # -- media on chat/completions (video, audio) --------------------------
    def chat_media(self, model, prompt, media_url, media="video", system=None, max_tokens=512, timeout=None,
                   url=None):
        """Video: a video_url part. Audio: an input_audio part (base64 + format).
        Only models that accept that input on chat/completions answer."""
        if media == "video":
            part = {"type": "video_url", "video_url": {"url": media_url}}
        else:
            fmt, b64 = "wav", media_url
            if media_url.startswith("data:"):
                head, b64 = media_url.split(",", 1)
                fmt = head[5:].split(";")[0].split("/")[-1].replace("x-", "").replace("mpeg", "mp3") or "wav"
            part = {"type": "input_audio", "input_audio": {"data": b64, "format": fmt}}
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": [{"type": "text", "text": prompt}, part]})
        return self.chat(model, messages, 0.2, max_tokens, url=url, timeout=timeout or 120)

    # -- rerank -----------------------------------------------------------
    @staticmethod
    def rerank_url(model):
        pub, _, name = model.partition("/")
        return f"https://ai.api.nvidia.com/v1/retrieval/{pub}/{name.replace('.', '_')}/reranking"

    def rerank(self, model, query, passages, url=None, timeout=None):
        """data -> list of (index, score) best first."""
        payload = {"model": model, "query": {"text": query}, "passages": [{"text": p} for p in passages],
                   "truncate": "END"}
        res = self.post(url or self.rerank_url(model), payload, timeout)
        if not res.ok:
            return _fail(res)
        body = res.json() or {}
        ranks = body.get("rankings")
        if ranks is None and isinstance(body.get("data"), list):  # cohere/jina style
            ranks = [{"index": d.get("index"), "logit": d.get("relevance_score", d.get("score", 0))}
                     for d in body["data"]]
        if not isinstance(ranks, list):
            return ModelResult(False, latency=res.latency, status=res.status, raw=body,
                               error=f"unexpected rerank shape: {res.text[:200]}")
        out = []
        for r in ranks:
            try:
                out.append((int(r["index"]), float(r.get("logit", r.get("score", 0)))))
            except (KeyError, TypeError, ValueError):
                continue
        out.sort(key=lambda x: x[1], reverse=True)
        return ModelResult(True, data=out, latency=res.latency, status=res.status, raw=body)

    # -- image generation -------------------------------------------------
    def image_gen(self, model, prompt, url=None, timeout=120, extra=None):
        """data -> list of image bytes (PNG/JPEG) on success."""
        if not url:
            url = self.router.resolve(model, "image_gen").get("url")
        if not url or not url.startswith("http"):
            url = f"https://ai.api.nvidia.com/v1/genai/{model}"
        payload = {"prompt": prompt, "mode": "base", "seed": 0}
        payload.update(extra or {})
        res = self.post(url, payload, timeout)
        if not res.ok and res.status in (400, 422):
            res = self.post(url, {"prompt": prompt}, timeout)   # models with a stricter schema
        if not res.ok:
            return _fail(res)
        body = res.json() or {}
        images = []
        for a in body.get("artifacts") or []:
            if isinstance(a, dict) and a.get("base64"):
                images.append(a["base64"])
        for k in ("image", "b64_json"):
            if isinstance(body.get(k), str):
                images.append(body[k])
        for d in body.get("data") or []:
            if isinstance(d, dict) and d.get("b64_json"):
                images.append(d["b64_json"])
        out = []
        for b in images:
            try:
                out.append(base64.b64decode(b.split(",", 1)[-1]))
            except (ValueError, TypeError):
                pass
        if not out:
            return ModelResult(False, latency=res.latency, status=res.status, raw=body,
                               error=f"no image in response: {res.text[:200]}")
        return ModelResult(True, data=out, latency=res.latency, status=res.status)

    # -- ASR (NVCF HTTP) --------------------------------------------------
    @staticmethod
    def nvcf_url(function_id, path):
        return f"https://{function_id}.invocation.api.nvcf.nvidia.com{path}"

    def asr(self, audio, filename="audio.wav", url=None, function_id=None, language="en-US", model=None,
            timeout=120):
        """Speech to text over HTTP: POST multipart 'file' to
        /v1/audio/transcriptions on the model's NVCF function (or url)."""
        if not url:
            if not function_id:
                return ModelResult(False, error="no HTTP endpoint for this ASR model: set the role's endpoint "
                                                "or a function id (hosted ASR is otherwise gRPC only)")
            url = self.nvcf_url(function_id, "/v1/audio/transcriptions")
        fields = [("file", (filename, audio, mimetypes.guess_type(filename)[0] or "audio/wav")),
                  ("language", language)]
        if model:
            fields.append(("model", model))
        body, ctype = build_multipart(fields)
        h = dict(self.auth_headers(), **{"Content-Type": ctype, "Accept": "application/json"})
        res = self.http.request("POST", url, body, h, timeout)
        if not res.ok:
            return _fail(res)
        data = res.json()
        text = None
        if isinstance(data, dict):
            text = data.get("text")
            if text is None and isinstance(data.get("results"), list):
                text = " ".join(str(((r.get("alternatives") or [{}])[0]).get("transcript", ""))
                                for r in data["results"] if isinstance(r, dict)).strip()
        if text is None:
            return ModelResult(False, latency=res.latency, status=res.status,
                               error="unexpected transcription response")
        return ModelResult(True, text=text, latency=res.latency, status=res.status, raw=data)


def file_to_data_url(path, default_mime="application/octet-stream"):
    """Any local file -> data: URL (video/audio). http(s)/data pass through."""
    ref = (path or "").strip()
    if ref.startswith(("http://", "https://", "data:")):
        return ref
    if not os.path.isfile(ref):
        return None
    mime = mimetypes.guess_type(ref)[0] or default_mime
    with open(ref, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode('ascii')}"


def save_bytes(data, prefix, ext):
    path = config.output_path(f"{prefix}_{int(time.time() * 1000)}.{ext.lstrip('.')}")
    with open(path, "wb") as f:
        f.write(data)
    return path


def save_wav(data, prefix="voice"):
    path = config.output_path(f"{prefix}_{int(time.time() * 1000)}.wav")
    with open(path, "wb") as f:
        f.write(data)
    return path


def play_audio(path):
    """Play through termux-media-player (Android) or mpv if available."""
    import shutil
    import subprocess
    for player in (["termux-media-player", "play"], ["mpv", "--really-quiet"]):
        if shutil.which(player[0]):
            subprocess.run(player + [path], check=False)
            return player[0]
    return None
