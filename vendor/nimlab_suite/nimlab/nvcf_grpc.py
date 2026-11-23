"""NVCF gRPC transport for the Riva models (v3.5).

Some models on build.nvidia.com have no REST route: the page's "Try API"
sample talks gRPC to grpc.nvcf.nvidia.com:443 with two metadata headers,

    function-id:   <the model's NVCF function id>
    authorization: Bearer <NVIDIA_API_KEY>

using NVIDIA's own Python client (pip install nvidia-riva-client). This
module is that path for the lab: ASR (offline and streaming), TTS (with the
zero-shot voice-clone prompt) and text translation (NMT).

Function ids are data, never code: they live per model in
data/endpoints.json (section grpc_functions, via nimlab.store) and come from
the model's NGC endpoint spec, the record build.nvidia.com renders its page
and "Try API" commands from, or from the user (grpc set). `grpc refresh`
fetches them again when one goes stale.

The riva client is imported lazily (_riva) so the lab still runs without
it; tests swap in fake stubs there.
"""

import io
import os
import re
import shutil
import subprocess
import tempfile
import time
import wave

URI = "grpc.nvcf.nvidia.com:443"
ASR_RATE = 16000
TTS_RATE = 22050          # talk.py's default output rate
CHUNK_FRAMES = 1600       # transcribe_file.py's default chunk (0.1 s at 16 kHz)
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
INSTALL_HINT = "pip install nvidia-riva-client (the launcher's install step does this: ./start.sh install)"

# kinds this client can drive; other gRPC-only models (Maxine video/audio
# effects) have their own protos and are listed but not called
RIVA_KINDS = ("asr", "tts", "nmt")
_KIND_WORDS = (("nmt", ("nmt", "translate")),
               ("asr", ("asr", "parakeet", "canary", "conformer", "whisper", "speech-recognition")),
               ("tts", ("tts", "magpie", "fastpitch", "chatterbox", "hifigan")))

# language names the translate role may be given -> NMT codes
LANG_CODES = {"english": "en", "german": "de", "spanish": "es", "french": "fr", "italian": "it",
              "portuguese": "pt", "russian": "ru", "chinese": "zh", "japanese": "ja", "korean": "ko",
              "arabic": "ar", "hindi": "hi", "dutch": "nl", "polish": "pl", "turkish": "tr",
              "vietnamese": "vi", "czech": "cs", "swedish": "sv", "danish": "da", "finnish": "fi",
              "greek": "el", "hungarian": "hu", "romanian": "ro", "ukrainian": "uk", "thai": "th",
              "indonesian": "id", "norwegian": "no", "bulgarian": "bg", "hebrew": "he"}


class GrpcError(Exception):
    pass


class Unavailable(GrpcError):
    """nvidia-riva-client (or grpcio) is not installed."""


# ---------------------------------------------------------------------------
# the client library (lazy; tests replace _riva)
# ---------------------------------------------------------------------------
def _riva():
    try:
        import riva.client as rc  # noqa: WPS433
    except Exception as e:  # ImportError, or a broken grpcio wheel
        raise Unavailable(f"nvidia-riva-client isn't installed ({type(e).__name__}): {INSTALL_HINT}")
    return rc


def available():
    """(ok, detail): whether the riva client can be imported."""
    try:
        rc = _riva()
    except Unavailable as e:
        return False, str(e)
    ver = getattr(rc, "__version__", None)
    if not ver:
        try:
            from importlib.metadata import version
            ver = version("nvidia-riva-client")
        except Exception:
            ver = "installed"
    return True, f"nvidia-riva-client {ver}"


# ---------------------------------------------------------------------------
# what a model is
# ---------------------------------------------------------------------------
def sample_from_usage(usage):
    """The "Try API" sample on a model's page -> the settings it uses:
    {script, mode, kind, language_code, voice}. Empty dict when there is
    no Riva sample. Parsed, not guessed: only what the command says."""
    usage = usage or ""
    m = re.search(r"scripts/(asr|tts|nmt)/(\w+)\.py", usage)
    if not m:
        return {}
    folder, script = m.group(1), m.group(2)
    i = m.start()
    cmd = usage[i:i + 1200].split("```")[0]
    out = {"script": f"{folder}/{script}.py", "kind": folder}
    if folder == "asr":
        out["mode"] = "offline" if "offline" in script else "streaming"
    lang = re.search(r"--language-code\s+\"?([A-Za-z]{2,3}(?:-[A-Za-z]{2,4})?)\"?", cmd)
    if lang:
        out["language_code"] = lang.group(1)
    voice = re.search(r"--voice\s+\"([^\"]+)\"", cmd) or re.search(r"--voice\s+(\S+)", cmd)
    if voice and not voice.group(1).startswith("<"):
        out["voice"] = voice.group(1).strip("'\"")
    if folder == "nmt":
        src = re.search(r"--source-language-code\s+(\S+)", cmd)
        tgt = re.search(r"--target-language-code\s+(\S+)", cmd)
        if src:
            out["source_language"] = src.group(1)
        if tgt:
            out["target_language"] = tgt.group(1)
    return out


def kind_of(model, rec=None):
    """asr / tts / nmt / other for a gRPC model."""
    rec = rec or {}
    k = rec.get("kind") or (rec.get("sample") or {}).get("kind")
    if k in RIVA_KINDS:
        return k
    m = (model or "").lower()
    for kind, words in _KIND_WORDS:
        if any(w in m for w in words):
            return kind
    return k or "other"


def valid_function_id(fid):
    return bool(fid) and bool(UUID.match(str(fid).strip()))


def record(model):
    """The stored gRPC record for a model ({} when none)."""
    from . import store
    return store.grpc_function(model) or {}


def function_id(model, sp=None):
    """Function id to send: the role's own (a pasted override), else the
    one stored for the model in data/endpoints.json."""
    if sp and sp.get("grpc_function_id"):
        return sp["grpc_function_id"]
    return record(model).get("function_id")


def is_grpc_model(model):
    from . import store
    return bool(model) and store.is_grpc_model(model)


RIVA_ASR_RX = re.compile(r"(^|/)(parakeet|canary|conformer)", re.I)
HOSTED_RX = re.compile(r"https?://[^/]*(nvidia\.com|nvcf|api\.nvcf)", re.I)


def is_riva_asr(model):
    """Riva speech-recognition models on build.nvidia.com: they are served
    over NVCF gRPC only (their HTTP route answers 400)."""
    return bool(model) and bool(RIVA_ASR_RX.search(model))


def use_grpc(sp):
    """Should this role spec go over gRPC?
    - transport 'grpc' / 'http' in the role always wins;
    - Riva ASR models (parakeet*, canary*, conformer*) default to gRPC, also
      when the scan has not marked them yet and also with a hosted NVIDIA
      endpoint set; only an endpoint of your own (a local NIM) keeps HTTP;
    - an explicit endpoint means HTTP for everything else;
    - otherwise a model the scan or the user marked gRPC-only goes over gRPC."""
    t = (sp.get("transport") or "").lower()
    if t == "grpc":
        return True
    if t in ("http", "rest"):
        return False
    model = sp.get("model")
    ep = sp.get("endpoint") or ""
    if is_riva_asr(model) and (not ep or HOSTED_RX.match(ep)):
        return True
    if ep:
        return False
    return is_grpc_model(model)


# ---------------------------------------------------------------------------
# audio
# ---------------------------------------------------------------------------
def _downsample(samples, src, dst):
    """Box-filter then linear resample (stdlib). Good enough for speech."""
    import array
    if src == dst or not samples:
        return samples
    if src > dst:
        f = src / dst
        width = max(1, int(round(f)))
        if width > 1:
            sm = array.array("h")
            acc, q = 0, []
            for s in samples:
                q.append(s)
                acc += s
                if len(q) > width:
                    acc -= q.pop(0)
                sm.append(int(acc / len(q)))
            samples = sm
    from .voiceclone import _resample
    return _resample(samples, src, dst)


def to_wav16k(path=None, data=None):
    """Any audio -> (16-bit mono 16 kHz WAV bytes, raw PCM bytes, notes).
    WAV is converted in pure Python; other formats need ffmpeg."""
    from . import voiceclone as vc
    notes = []
    if data is None:
        if not path or not os.path.isfile(path):
            raise GrpcError(f"audio not found: {path}")
        with open(path, "rb") as f:
            data = f.read()
    if not data:
        raise GrpcError("the audio is empty")
    is_wav = data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    parsed = None
    if is_wav:
        try:
            with wave.open(io.BytesIO(data)) as w:
                parsed = (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype(),
                          w.readframes(w.getnframes()))
        except (wave.Error, EOFError):
            parsed = None
    if parsed is None or parsed[3] != "NONE":
        data = _ffmpeg16k(path, data)
        notes.append("converted to 16 kHz mono WAV with ffmpeg")
        with wave.open(io.BytesIO(data)) as w:
            parsed = (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype(),
                      w.readframes(w.getnframes()))
    ch, width, rate, _comp, frames = parsed
    if ch == 1 and width == 2 and rate == ASR_RATE:
        return data, frames, notes
    try:
        samples = vc._pcm_to_mono16(frames, width, ch)
    except vc.CloneError as e:
        raise GrpcError(str(e))
    if rate != ASR_RATE:
        samples = _downsample(samples, rate, ASR_RATE)
        notes.append(f"resampled {rate} Hz to {ASR_RATE} Hz")
    if ch != 1 or width != 2:
        notes.append(f"converted {ch}-channel {width * 8}-bit audio to 16-bit mono")
    wav = vc._wav_bytes(samples, ASR_RATE)
    with wave.open(io.BytesIO(wav)) as w:
        pcm = w.readframes(w.getnframes())
    return wav, pcm, notes


def _ffmpeg16k(path, data):
    ff = shutil.which("ffmpeg")
    if not ff:
        raise GrpcError("this audio isn't plain PCM WAV and ffmpeg isn't installed to convert it "
                        "(Termux: pkg install ffmpeg)")
    tmp = None
    try:
        if not path:
            fd, tmp = tempfile.mkstemp(suffix=".audio")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            path = tmp
        p = subprocess.run([ff, "-v", "error", "-i", path, "-ac", "1", "-ar", str(ASR_RATE),
                            "-sample_fmt", "s16", "-f", "wav", "-"], capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise GrpcError(f"ffmpeg failed: {e}")
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass
    if p.returncode != 0 or len(p.stdout) < 100:
        raise GrpcError("ffmpeg could not read the audio: " + p.stderr.decode("utf-8", "replace")[:200])
    return p.stdout


def pcm_to_wav(pcm, rate):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(rate))
        w.writeframes(pcm)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# the client
# ---------------------------------------------------------------------------
def _rpc_text(e):
    """A gRPC error -> (code name, details), key-free."""
    code = None
    try:
        c = e.code()
        code = getattr(c, "name", None) or str(c)
    except Exception:
        pass
    try:
        details = e.details()
    except Exception:
        details = str(e)
    from .core import redact
    return code, redact(str(details or ""))[:400]


def stale_hint(model, code, details):
    """What to do about an error that points at the function id."""
    d = (details or "").lower()
    if code in ("NOT_FOUND", "PERMISSION_DENIED", "UNAUTHENTICATED", "INVALID_ARGUMENT") and \
            ("function" in d or "not found" in d or code == "NOT_FOUND"):
        return (f"the function ID may be stale: run ./start.sh grpc refresh {model} "
                f"(or paste a new one: ./start.sh grpc set {model} <function-id>)")
    if code in ("UNAUTHENTICATED", "PERMISSION_DENIED"):
        # NVCF answers a bad key and an unknown function the same way
        return (f"check NVIDIA_API_KEY; if the key works for other models, the function ID may be stale: "
                f"./start.sh grpc refresh {model}")
    return ""


class GrpcClient:
    """One per process is enough; it keeps one channel per function id."""

    def __init__(self, api_key=None, uri=None, riva=None):
        self._key = api_key
        self.uri = uri or URI
        self._rc = riva
        self._auth = {}

    @property
    def rc(self):
        return self._rc if self._rc is not None else _riva()

    @property
    def api_key(self):
        if self._key:
            return self._key
        from .core import load_api_key
        return load_api_key()

    def metadata(self, fid):
        return [["function-id", fid], ["authorization", f"Bearer {self.api_key}"]]

    def auth(self, fid):
        if not valid_function_id(fid):
            raise GrpcError(f"not a function ID: {fid!r} (expected a UUID like "
                            "b0e8b4a5-217c-40b7-9b96-17d84e666317)")
        if not self.api_key:
            raise GrpcError("no NVIDIA_API_KEY set")
        k = (fid, self.api_key, id(self.rc))
        if k not in self._auth:
            self._auth[k] = self.rc.Auth(None, True, self.uri, self.metadata(fid))
        return self._auth[k]

    # -- ASR ----------------------------------------------------------------
    def recognition_config(self, language_code, custom=None, model=""):
        rc = self.rc
        cfg = rc.RecognitionConfig(encoding=rc.AudioEncoding.LINEAR_PCM, sample_rate_hertz=ASR_RATE,
                                   language_code=language_code, max_alternatives=1,
                                   enable_automatic_punctuation=True, audio_channel_count=1,
                                   verbatim_transcripts=False)
        if model:
            cfg.model = model
        if custom:
            rc.add_custom_configuration_to_config(cfg, custom)
        return cfg

    def asr(self, fid, wav, pcm, language_code="en-US", mode="offline", custom=None):
        """-> (transcript, mode used). offline sends the whole WAV the way
        transcribe_file_offline.py does; streaming sends 0.1 s PCM chunks
        the way transcribe_file.py does. A mode the function refuses
        (UNIMPLEMENTED / INVALID_ARGUMENT) is retried once in the other."""
        auth = self.auth(fid)
        svc = self.rc.ASRService(auth)
        order = ["streaming", "offline"] if mode == "streaming" else ["offline", "streaming"]
        first_err = None
        for i, m in enumerate(order):
            try:
                if m == "offline":
                    resp = svc.offline_recognize(wav, self.recognition_config(language_code, custom))
                    return _join_results(getattr(resp, "results", []) or []), m
                scfg = self.rc.StreamingRecognitionConfig(config=self.recognition_config(language_code, custom),
                                                          interim_results=False)
                step = CHUNK_FRAMES * 2
                chunks = (pcm[j:j + step] for j in range(0, len(pcm), step))
                parts = []
                for resp in svc.streaming_response_generator(audio_chunks=chunks, streaming_config=scfg):
                    parts.extend(r for r in (getattr(resp, "results", []) or [])
                                 if getattr(r, "is_final", True))
                return _join_results(parts), m
            except Exception as e:  # grpc.RpcError (or a fake of it)
                code, _ = _rpc_text(e)
                if first_err is None:
                    first_err = e
                if i == 0 and code in ("UNIMPLEMENTED", "INVALID_ARGUMENT"):
                    continue
                raise first_err if code in ("UNIMPLEMENTED", "INVALID_ARGUMENT") else e
        raise first_err  # pragma: no cover

    # -- TTS ----------------------------------------------------------------
    def tts(self, fid, text, voice=None, language_code="en-US", sample_rate=TTS_RATE, prompt_wav=None,
            prompt_transcript=None, quality=20):
        """-> WAV bytes. prompt_wav: zero-shot reference clip (WAV bytes)."""
        auth = self.auth(fid)
        svc = self.rc.SpeechSynthesisService(auth)
        kw = {"voice_name": voice or None, "language_code": language_code,
              "encoding": self.rc.AudioEncoding.LINEAR_PCM, "sample_rate_hz": int(sample_rate)}
        tmp = None
        try:
            if prompt_wav:
                import pathlib
                fd, tmp = tempfile.mkstemp(suffix=".wav", prefix="nimlab_prompt_")
                with os.fdopen(fd, "wb") as f:
                    f.write(prompt_wav)
                kw["zero_shot_audio_prompt_file"] = pathlib.Path(tmp)  # riva calls .open('rb') on it
                kw["zero_shot_quality"] = int(quality)
                if prompt_transcript:
                    kw["zero_shot_transcript"] = prompt_transcript
            resp = svc.synthesize(text, **kw)
        finally:
            if tmp:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        audio = getattr(resp, "audio", b"") or b""
        if not audio:
            raise GrpcError("the TTS function returned no audio")
        if audio[:4] == b"RIFF":
            return audio
        return pcm_to_wav(audio, sample_rate)

    def voices(self, fid):
        """Voice names the TTS function offers (GetRivaSynthesisConfig)."""
        auth = self.auth(fid)
        svc = self.rc.SpeechSynthesisService(auth)
        req = self.rc.proto.riva_tts_pb2.RivaSynthesisConfigRequest()
        resp = svc.stub.GetRivaSynthesisConfig(req, metadata=auth.get_auth_metadata())
        out = []
        for mc in getattr(resp, "model_config", []) or []:
            params = getattr(mc, "parameters", {}) or {}
            name = params.get("voice_name") if hasattr(params, "get") else None
            subs = params.get("subvoices", "") if hasattr(params, "get") else ""
            if name:
                if subs:
                    out.extend(f"{name}.{s.split(':')[0]}" for s in subs.split(",") if s)
                else:
                    out.append(name)
        return sorted(set(out))

    # -- NMT ----------------------------------------------------------------
    def translate(self, fid, texts, source, target, model=""):
        auth = self.auth(fid)
        cli = self.rc.NeuralMachineTranslationClient(auth)
        resp = cli.translate(list(texts), model, source, target)
        return [getattr(t, "text", "") for t in getattr(resp, "translations", []) or []]

    # -- check --------------------------------------------------------------
    def check(self, fid, kind):
        """A cheap call that proves the id and key work: the function's
        config RPC. -> (ok, latency, detail)."""
        t0 = time.time()
        try:
            auth = self.auth(fid)
            md = auth.get_auth_metadata()
            if kind == "asr":
                svc = self.rc.ASRService(auth)
                req = self.rc.proto.riva_asr_pb2.RivaSpeechRecognitionConfigRequest()
                resp = svc.stub.GetRivaSpeechRecognitionConfig(req, metadata=md)
                n = len(getattr(resp, "model_config", []) or [])
                detail = f"{n} ASR model config(s)"
            elif kind == "tts":
                svc = self.rc.SpeechSynthesisService(auth)
                req = self.rc.proto.riva_tts_pb2.RivaSynthesisConfigRequest()
                resp = svc.stub.GetRivaSynthesisConfig(req, metadata=md)
                n = len(getattr(resp, "model_config", []) or [])
                detail = f"{n} voice config(s)"
            elif kind == "nmt":
                resp = self.rc.NeuralMachineTranslationClient(auth).get_config("")
                n = len(getattr(resp, "languages", {}) or {})
                detail = f"{n} language model(s)"
            else:
                return False, 0.0, "no Riva client for this model type (it has its own gRPC protos)"
            return True, round(time.time() - t0, 2), detail
        except Unavailable:
            raise
        except GrpcError as e:
            return False, round(time.time() - t0, 2), str(e)
        except Exception as e:
            code, details = _rpc_text(e)
            return False, round(time.time() - t0, 2), f"{code or type(e).__name__}: {details}"


def _join_results(results):
    out = []
    for r in results:
        alts = getattr(r, "alternatives", []) or []
        if alts:
            t = (getattr(alts[0], "transcript", "") or "").strip()
            if t:
                out.append(t)
    return " ".join(out).strip()


_shared = {}


def client(api_key=None):
    """Shared client (channels are reused across calls)."""
    k = api_key or ""
    if k not in _shared:
        _shared[k] = GrpcClient(api_key=api_key)
    return _shared[k]


# ---------------------------------------------------------------------------
# role calls (what Entity uses); every one returns an api.ModelResult
# ---------------------------------------------------------------------------
def _result(ok, **kw):
    from .api import ModelResult
    return ModelResult(ok, **kw)


def _fail(model, e, t0, what):
    if isinstance(e, Unavailable):
        return _result(False, error=str(e), latency=round(time.time() - t0, 3))
    if isinstance(e, GrpcError):
        return _result(False, error=f"{what} over NVCF gRPC: {e}", latency=round(time.time() - t0, 3))
    code, details = _rpc_text(e)
    hint = stale_hint(model, code, details)
    msg = f"{what} over NVCF gRPC failed: {code or type(e).__name__}: {details}" + (f" ({hint})" if hint else "")
    from . import store
    try:
        store.note_grpc_check(model, False, msg[:300])
    except Exception:
        pass
    return _result(False, error=msg, latency=round(time.time() - t0, 3))


def _auto_id(model, sp):
    """No function ID yet: fetch it once from the model's NGC spec (no key
    needed). NIMLAB_GRPC_AUTOFETCH=0 turns this off. -> id or None."""
    if os.environ.get("NIMLAB_GRPC_AUTOFETCH", "1") == "0" or (model or "") in _auto_tried:
        return None
    _auto_tried.add(model or "")
    try:
        ok, _msg = refresh(model)
    except Exception:
        return None
    return function_id(model, sp) if ok else None


_auto_tried = set()


def _need_id(model, what):
    return _result(False, error=(f"{model} is gRPC-only and has no function ID yet. Get it with "
                                 f"./start.sh grpc refresh {model}, or paste it: ./start.sh grpc set {model} "
                                 "<function-id> (testbed: option 10)"))


def asr_language(sp, rec, inp_language=None, voice_settings=None):
    """request > role language_code > the model's own sample > the voice
    settings' language > en-US."""
    return (inp_language or sp.get("language_code") or rec.get("language_code")
            or (rec.get("sample") or {}).get("language_code") or (voice_settings or {}).get("language") or "en-US")


def run_asr(sp, path=None, data=None, language=None, voice_settings=None, api_key=None, cli=None):
    model = sp.get("model")
    t0 = time.time()
    fid = function_id(model, sp) or _auto_id(model, sp)
    if not fid:
        return _need_id(model, "ASR")
    rec = record(model)
    lang = asr_language(sp, rec, language, voice_settings)
    mode = sp.get("asr_mode") or rec.get("mode") or (rec.get("sample") or {}).get("mode") or "offline"
    try:
        wav, pcm, notes = to_wav16k(path, data)
        c = cli or client(api_key)
        text, used = c.asr(fid, wav, pcm, language_code=lang, mode=mode,
                           custom=sp.get("asr_custom_configuration"))
    except Exception as e:
        return _fail(model, e, t0, "ASR")
    lat = round(time.time() - t0, 3)
    from . import store
    try:
        store.note_grpc_check(model, True, f"ASR {used}, {lang}", latency=lat, mode=used if used != mode else None)
    except Exception:
        pass
    return _result(True, text=text, latency=lat,
                   raw={"transport": "nvcf_grpc", "mode": used, "language_code": lang, "notes": notes})


def run_tts(sp, text, voice=None, language=None, prompt_wav=None, prompt_transcript=None, api_key=None, cli=None):
    model = sp.get("model")
    t0 = time.time()
    fid = function_id(model, sp) or _auto_id(model, sp)
    if not fid:
        return _need_id(model, "TTS")
    rec = record(model)
    sample = rec.get("sample") or {}
    if voice is None:
        voice = sp.get("voice") or (None if prompt_wav else sample.get("voice"))
    lang = language or sp.get("language_code") or rec.get("language_code") or sample.get("language_code") or "en-US"
    rate = int(sp.get("sample_rate_hz") or TTS_RATE)
    try:
        c = cli or client(api_key)
        wav = c.tts(fid, text, voice=voice, language_code=lang, sample_rate=rate, prompt_wav=prompt_wav,
                    prompt_transcript=prompt_transcript)
    except Exception as e:
        return _fail(model, e, t0, "TTS")
    lat = round(time.time() - t0, 3)
    from . import store
    try:
        store.note_grpc_check(model, True, "TTS" + (" (cloned voice)" if prompt_wav else ""), latency=lat)
    except Exception:
        pass
    return _result(True, data=wav, latency=lat,
                   raw={"transport": "nvcf_grpc", "voice": voice, "language_code": lang,
                        "cloned": bool(prompt_wav)})


def lang_code(name, default="en"):
    n = (name or "").strip()
    if not n:
        return default
    if re.match(r"^[A-Za-z]{2,3}(-[A-Za-z]{2,4})?$", n):
        return n
    return LANG_CODES.get(n.lower(), default)


def run_translate(sp, text, target=None, source=None, api_key=None, cli=None):
    model = sp.get("model")
    t0 = time.time()
    fid = function_id(model, sp) or _auto_id(model, sp)
    if not fid:
        return _need_id(model, "translation")
    sample = record(model).get("sample") or {}
    src = lang_code(source or sp.get("source_language") or sample.get("source_language") or "en")
    tgt = lang_code(target or sp.get("target_language") or "English")
    try:
        c = cli or client(api_key)
        out = c.translate(fid, [text], src, tgt, model=sp.get("nmt_model", ""))
    except Exception as e:
        return _fail(model, e, t0, "translation")
    return _result(True, text=" ".join(out).strip(), latency=round(time.time() - t0, 3),
                   raw={"transport": "nvcf_grpc", "source": src, "target": tgt})


# ---------------------------------------------------------------------------
# finding function ids (never invented: NGC spec / page / user)
# ---------------------------------------------------------------------------
def fetch_spec(model, fetcher=None):
    """The model's NGC endpoint spec (what build.nvidia.com renders its
    page and "Try API" commands from). -> {function_id, sample, page_url,
    grpc} or None when no slug answered."""
    from . import spec
    from .sweep import SpecResolver
    if fetcher is None:
        from .scrape import PoliteFetcher
        fetcher = PoliteFetcher(ttl_sec=0, host_delays={"api.ngc.nvidia.com": 0.5, "build.nvidia.com": 2.0})
    res_ = SpecResolver(fetcher, cache_dir="")
    slugs = []
    for sl in res_.slugs(model):  # NGC spec slugs are lower case (nvidia/LipSync -> lipsync)
        for v in (sl, sl.lower()):
            if v not in slugs:
                slugs.append(v)
    for slug in slugs:
        res = fetcher.get(spec.ngc_spec_url(slug), store=False, accept="application/json")
        if not getattr(res, "ok", False):
            continue
        info = spec.extract_ngc_spec(res.text)
        if info.get("found") and info.get("function_id"):
            pub = model.split("/", 1)[0] if "/" in model else "nvidia"
            return {"function_id": info["function_id"], "sample": sample_from_usage(info.get("usage")),
                    "grpc": bool(info.get("grpc")), "page_url": spec.build_page_url(pub, slug),
                    "source": "ngc_spec"}
    return None


def refresh(model, fetcher=None, log=print):
    """Fetch the model's function id again and store it. -> (ok, message)."""
    from . import store
    old = record(model).get("function_id")
    try:
        got = fetch_spec(model, fetcher)
    except Exception as e:
        return False, f"{model}: could not fetch its spec ({type(e).__name__}: {e})"
    if not got:
        return False, (f"{model}: no function ID on its NGC spec or page. Copy it from the \"Try API\" "
                       f"sample on build.nvidia.com and run: ./start.sh grpc set {model} <function-id>")
    store.set_grpc_function(model, got["function_id"], source=got["source"], kind=kind_of(model, got),
                            sample=got["sample"], page_url=got["page_url"])
    if old and old != got["function_id"]:
        return True, f"{model}: function ID changed {old} -> {got['function_id']}"
    return True, f"{model}: {got['function_id']}" + (" (unchanged)" if old else " (new)")


def seed_from_spec_cache(cache_dir=None):
    """Fold function ids the spec sweep already cached (output/cache/specs)
    into data/endpoints.json for every gRPC-only model. -> count added."""
    import json
    from . import store
    from .sweep import spec_cache_dir
    d = cache_dir or spec_cache_dir()
    n = 0
    try:
        names = os.listdir(d)
    except OSError:
        return 0
    for name in sorted(names):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, name), "r", encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, ValueError):
            continue
        notes = doc.get("notes") or {}
        mid, fid = doc.get("model_id"), doc.get("function_id")
        if not (mid and notes.get("grpc_only") and valid_function_id(fid)):
            continue
        rec = store.grpc_function(mid) or {}
        if rec.get("function_id"):
            continue
        store.set_grpc_function(mid, fid, source="spec_cache", kind=kind_of(mid, {"sample": notes.get("grpc_sample")}),
                                sample=notes.get("grpc_sample"), page_url=doc.get("page_url"))
        n += 1
    return n


def rows():
    """Every known gRPC-only model with what the lab knows about it."""
    from . import store
    out = []
    for mid in store.grpc_model_ids():
        rec = store.grpc_function(mid) or {}
        out.append({"model": mid, "kind": kind_of(mid, rec), "function_id": rec.get("function_id"),
                    "source": rec.get("source"), "last_check": rec.get("last_check"),
                    "language_code": rec.get("language_code") or (rec.get("sample") or {}).get("language_code"),
                    "mode": rec.get("mode") or (rec.get("sample") or {}).get("mode"),
                    "spec_function_id": rec.get("spec_function_id")})
    return out


def usable_label(model, rec=None):
    """The scan's word for a gRPC-only model."""
    rec = rec if rec is not None else record(model)
    kind = kind_of(model, rec)
    fid = rec.get("function_id")
    if kind not in RIVA_KINDS:
        return f"gRPC ({kind}; own protos, not driven by the lab)" + ("" if fid else ", no function ID")
    if fid:
        return f"USABLE via NVCF gRPC ({kind.upper()}, function {fid[:8]}…)"
    return f"USABLE via NVCF gRPC ({kind.upper()}) once a function ID is set: ./start.sh grpc set {model} <id>"


