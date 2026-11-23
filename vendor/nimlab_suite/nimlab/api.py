"""NVIDIA model calls: chat, streaming chat, embeddings, vision, OCR, TTS,
rerank, image generation, ASR, and video/audio parts on chat.

Every call returns a ModelResult with the same shape, so callers never
have to guess whether they got text, an error string, or a dict.
"""

import base64
import io
import json
import mimetypes
import re
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


THINKING_ONLY_NOTE = ("(The model used its whole token budget thinking and gave no answer. Raise max tokens, "
                      "or use a non-reasoning model for this role.)")

_THINK_BLOCK = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.S | re.I)


def strip_thinking(text):
    """Remove a reasoning model's thinking from a finished reply."""
    if not text:
        return text or ""
    t = _THINK_BLOCK.sub("", text)
    low = t.lower()
    # an unterminated opening tag: everything after it is thinking
    m = re.search(r"<(think|thinking|reasoning)>", low)
    if m:
        t = t[:m.start()]
        low = t.lower()
    # a closing tag with no opening one (DeepSeek-R1 style): keep what follows
    m = None
    for m in re.finditer(r"</(think|thinking|reasoning)>", low):
        pass
    if m:
        t = t[m.end():]
    # gpt-oss harmony leaking into content
    i = t.find("assistantfinal")
    if i != -1 and t.lstrip().lower().startswith("analysis"):
        t = t[i + len("assistantfinal"):]
    return t.lstrip("\n") if t != text else t


class ThinkFilter:
    """Streaming version of strip_thinking: drops <think>...</think> spans,
    including tags split across chunks."""

    OPEN = ("<think>", "<thinking>", "<reasoning>")

    def __init__(self):
        self.buf = ""
        self.inside = None      # closing tag we wait for
        self.dropped = False
        self.saw_reasoning = False
        self.started = False

    def feed(self, s):
        if not s:
            return ""
        self.buf += s
        out = []
        while self.buf:
            low = self.buf.lower()
            if self.inside:
                j = low.find(self.inside)
                if j == -1:
                    keep = len(self.inside) - 1
                    self.buf = self.buf[-keep:] if len(self.buf) > keep else self.buf
                    self.dropped = True
                    break
                self.buf = self.buf[j + len(self.inside):]
                self.inside = None
                self.dropped = True
                continue
            hits = [(low.find(o), o) for o in self.OPEN if low.find(o) != -1]
            if hits:
                j, o = min(hits)
                out.append(self.buf[:j])
                self.buf = self.buf[j + len(o):]
                self.inside = "</" + o[1:]
                continue
            # hold back a possible partial opening tag at the end
            k = self.buf.rfind("<")
            if k != -1 and any(o.startswith(low[k:]) for o in self.OPEN):
                out.append(self.buf[:k])
                self.buf = self.buf[k:]
            else:
                out.append(self.buf)
                self.buf = ""
            break
        text = "".join(out)
        if not self.started:
            text = text.lstrip("\n") if self.dropped else text
            if text:
                self.started = True
        return text

    def flush(self):
        if self.inside:
            self.buf = ""
            return ""
        t, self.buf = self.buf, ""
        return t


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
        self.url = None          # v3.8.3: the upstream URL a failure came from
        self.attempts = None     # HTTP attempts (1 + retries)
        self.tried = []          # v3.8.3: every model tried for this step, fallbacks included

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
    r = ModelResult(False, latency=res.latency, error=(prefix + res.describe()), status=res.status,
                    raw=res.json())
    r.url = getattr(res, "url", None)               # v3.8.3: for the trace/bug record (host only is kept)
    r.attempts = getattr(res, "attempts", None)
    return r


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

    def headers_for(self, url):
        """The key for this URL: a custom endpoint's own key (3.8.2) when the
        URL is under one, else the NVIDIA key. The NVIDIA key never goes to a
        custom endpoint."""
        try:
            from . import endpoints
            e = endpoints.owner_of(url)
        except Exception:  # noqa: BLE001 - a broken endpoints file never breaks NVIDIA calls
            e = None
        if e:
            return endpoints.headers(e["name"])
        return self.auth_headers()

    # one routing path for every caller (3.8.2): an explicit URL (the role's
    # endpoint), then a custom endpoint that serves the model, then the
    # endpoint registry (spec sweep overrides, prefix rules, static routes).
    ROUTE_OK = {"chat": ("chat", "chat_stream", "vision"),
                "embeddings": ("embeddings", "embeddings_typed", "embeddings_retrieval"),
                "image_gen": ("image_gen",), "rerank": ("rerank", "ranking", "rerank_classic"),
                "audio_tts": ("audio_tts",)}

    def route(self, model, kind="chat", url=None):
        """-> (url or None, body model id). None: use the caller's default."""
        try:
            from . import endpoints
            if url:
                return url, endpoints.real_model_id(model)
            e, m = endpoints.find(model, kind)
            if e:
                return endpoints.model_url(e, m), m["id"]
        except Exception:  # noqa: BLE001
            if url:
                return url, model
        try:
            r = self.router.resolve(model, kind) or {}
        except Exception:  # noqa: BLE001 - a broken registry never stops a call
            r = {}
        u = r.get("url") or ""
        if u.startswith("http") and r.get("kind") in self.ROUTE_OK.get(kind, (kind,)):
            return u, r.get("api_model_id") or model
        return None, model

    def post(self, url, payload, timeout=None, accept="application/json"):
        """Raw JSON POST with auth. Returns core.HttpResult."""
        return self.http.post_json(url, payload, self.headers_for(url), timeout, accept)

    def get(self, url, timeout=None):
        return self.http.get(url, self.headers_for(url), timeout)

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
        """The answer text only. A reasoning model's thinking (reasoning_content /
        reasoning, inline <think> blocks, gpt-oss 'analysis...assistantfinal')
        is never returned as the answer. When the model spent its whole budget
        thinking, a short note says so instead."""
        text = NimClient._chat_text_raw(body)
        if text is None:
            return None
        clean = strip_thinking(text)
        if clean.strip():
            return clean
        try:
            ch = body["choices"][0]
            msg = ch.get("message") or {}
        except (KeyError, IndexError, TypeError, AttributeError):
            return clean
        thought = msg.get("reasoning_content") or msg.get("reasoning") or (text if text.strip() else "")
        if thought:
            return THINKING_ONLY_NOTE
        return clean

    @staticmethod
    def _chat_text_raw(body):
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
        return content or ""

    def model_params(self, model):
        """Extra request fields for one chat model from cluster model_params (Quill latency fix,
        3.8.4 candidate), e.g. {"minimaxai/minimax-m3.1-flash": {"reasoning_effort": "low"}}.
        Applies wherever the model is used: persona, fallbacks, scheduler jobs."""
        mp = (self.cluster or {}).get("model_params") or {}
        got = mp.get(model) if isinstance(mp, dict) else None
        return dict(got) if isinstance(got, dict) else {}

    def chat(self, model, messages, temperature=0.7, max_tokens=1024, url=None, timeout=None, extra=None):
        params = self.model_params(model)
        url, model = self.route(model, "chat", url)
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, "stream": False}
        payload.update(params)
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
        params = self.model_params(model)
        url, model = self.route(model, "chat", url)
        url = url or f"{self.integrate()}/chat/completions"
        payload = {"model": model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, "stream": True}
        payload.update(params)
        h = dict(self.headers_for(url), **{"Content-Type": "application/json", "Accept": "text/event-stream"})
        t0 = time.monotonic()
        res = self.http.request("POST", url or f"{self.integrate()}/chat/completions",
                                json.dumps(payload).encode("utf-8"), h, timeout, stream=True)
        if not res.ok:
            return _fail(res)
        tokens, usage = [], {}
        thinking = ThinkFilter()
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
                if delta.get("reasoning_content") or delta.get("reasoning"):
                    thinking.saw_reasoning = True
                tok = thinking.feed(delta.get("content") or "")
                if tok:
                    tokens.append(tok)
                    if on_token:
                        on_token(tok)
        except Exception as e:  # network drop mid-stream
            return ModelResult(False, text="".join(tokens), latency=round(time.monotonic() - t0, 3),
                               error=redact(f"stream interrupted: {e}"), status=res.status)
        finally:
            resp.close()
        tail = thinking.flush()
        if tail:
            tokens.append(tail)
            if on_token:
                on_token(tail)
        text = "".join(tokens)
        if not text.strip() and (thinking.saw_reasoning or thinking.dropped):
            text = THINKING_ONLY_NOTE
            if on_token:
                on_token(text)
        return ModelResult(True, text=text, usage=usage, latency=round(time.monotonic() - t0, 3),
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
    def embed(self, model, texts, input_type=None, url=None, timeout=None, truncate="END", dimensions=None):
        """Embeds a list of texts. data -> list of vectors.

        input_type ("query" to search, "passage" to store) is sent always:
        NVIDIA's retrieval and VL embedders (llama-nemotron-embed-vl-1b-v2,
        llama-3.2-nv-embedqa-1b-v2, nv-embedqa-e5-v5) require it. The call
        is retried without it only when the model says it does not know the
        field, never when it says the field is required; the error keeps
        the first HTTP status and body (v3.7.1). truncate END keeps long
        turns under the model's token limit instead of a 400."""
        url, model = self.route(model, "embeddings", url)
        url = url or f"{self.integrate()}/embeddings"
        payload = {"model": model, "input": list(texts), "encoding_format": "float"}
        if input_type:
            payload["input_type"] = input_type
        if truncate:
            payload["truncate"] = truncate
        if dimensions:
            payload["dimensions"] = int(dimensions)
        res = self.post(url, payload, timeout)
        first = None
        if not res.ok and res.status in (400, 422):
            low = (res.text or "").lower()
            drop = [f for f in ("truncate", "dimensions", "input_type") if f in payload and f in low
                    and not ("required" in low and f == "input_type")
                    and any(w in low for w in ("extra", "not permitted", "unexpected", "unknown", "unrecognized",
                                               "not supported", "unsupported", "invalid", "not allowed"))]
            if drop:
                first = res
                for f in drop:
                    payload.pop(f, None)
                res = self.post(url, payload, timeout)
        if not res.ok:
            err = _fail(res)
            if first is not None:
                err.error = f"{first.describe()}; retried without {', '.join(drop)}: {err.error}"
            return err
        body = res.json()
        try:
            items = sorted(body["data"], key=lambda d: d.get("index", 0))
            vectors = [d["embedding"] for d in items]
        except (KeyError, TypeError, AttributeError):
            return ModelResult(False, latency=res.latency, status=res.status,
                               error=f"HTTP {res.status}: unexpected embeddings shape: {(res.text or '')[:200]}")
        if vectors and isinstance(vectors[0], str):
            import base64
            import struct
            dec = []
            for v in vectors:
                raw = base64.b64decode(v)
                dec.append(list(struct.unpack(f"<{len(raw) // 4}f", raw)))
            vectors = dec
        if not vectors or not vectors[0]:
            return ModelResult(False, latency=res.latency, status=res.status,
                               error=f"HTTP {res.status}: the response has no embedding: {(res.text or '')[:200]}")
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
        url = url or self.tts_url()
        h = dict(self.headers_for(url), **{"Content-Type": ctype, "Accept": "audio/wav, application/json"})
        res = self.http.request("POST", url, body, h, timeout)
        if not res.ok:
            return _fail(res)
        audio = res.body
        if len(audio) <= 200:
            return ModelResult(False, latency=res.latency, status=res.status,
                               error=f"empty or invalid audio ({len(audio)} bytes)")
        return ModelResult(True, data=audio, latency=res.latency, status=res.status)

    def tts_openai(self, model, text, url, voice=None, timeout=35):
        """OpenAI-style /audio/speech (custom gateways, 3.8.2): JSON in, WAV out."""
        payload = {"model": model, "input": text, "response_format": "wav"}
        if voice:
            payload["voice"] = voice
        res = self.post(url, payload, timeout, accept="audio/wav, audio/*, application/json")
        if not res.ok:
            return _fail(res)
        audio = res.body
        if len(audio) <= 200 or audio[:1] in (b"{", b"["):
            return ModelResult(False, latency=res.latency, status=res.status,
                               error=f"no audio in the answer ({len(audio)} bytes): {res.text[:150]}")
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
        url, payload["model"] = self.route(model, "rerank", url)
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
        url, _m = self.route(model, "image_gen", url)
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
        h = dict(self.headers_for(url), **{"Content-Type": ctype, "Accept": "application/json"})
        res = self.http.request("POST", url, body, h, timeout)
        if not res.ok:
            hint = (" (this Riva model is served over NVCF gRPC only: set the role's transport to grpc, "
                    "or run: ./start.sh grpc refresh " + str(model) + ")") if res.status == 400 and model and \
                re.search(r"parakeet|canary|conformer", str(model), re.I) else ""
            r = _fail(res, "NVIDIA ASR ")
            r.error = (r.error or "") + hint
            return r
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


PLAY_TIMEOUT = float(os.environ.get("NIMLAB_PLAY_TIMEOUT", "120") or 120)


def play_audio(path):
    """Play through termux-media-player (Android) or mpv if available."""
    import shutil
    import subprocess
    for player in (["termux-media-player", "play"], ["mpv", "--really-quiet"]):
        if shutil.which(player[0]):
            try:
                # a player that never returns must not hang a call or a script
                subprocess.run(player + [path], check=False, timeout=PLAY_TIMEOUT)
            except subprocess.TimeoutExpired:
                pass
            return player[0]
    try:   # 3.8.5: headless (VPS): the active phone plays it
        from . import audiobus
        if audiobus.remote_ready():
            with open(path, "rb") as f:
                audiobus.publish(f.read(), fmt=os.path.splitext(path)[1].lstrip("."), source="play_audio")
            return "nimbridge"
    except Exception:  # noqa: BLE001 - playing is best effort
        pass
    return None
