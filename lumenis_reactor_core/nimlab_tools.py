"""
nimlab tools: One2lv's NVIDIA lab suite as Lumenis tools
=========================================================
The suite (vendor/nimlab_suite, plain stdlib Python) is imported in-process and exposed through the tool
engine as the `nimlab.` namespace. engine.dispatch validates arguments, traces every call and handles
errors; this module adds the suite-specific guards:

  levels   local_read    reads the suite's data stores on this disk; no network, no key
           nvidia_call   one small NVIDIA request (probe, chat, embed, vision, ocr, rerank, tts, key list)
           nvidia_batch  a bounded ranking run: at most 3 named models, hard call budget
           refused       listed so Lumenis can see them, never run from here: sweeps, discovery, image
                         generation (Image app only), voice cloning, role/config changes, the MCP bridge
  gate     every outbound HTTP attempt passes one gate: host must be nvidia.com or a subdomain, each tool
           call has a hard budget of attempts, and all nimlab tools share NIMLAB_CALLS_PER_MIN (default 30)
  key      read from the environment at call time (NIMLAB_KEY_VAR, default NVIDIA_API_KEY), handed to the
           suite's client for that call only, never returned, logged or stored
  files    vision/ocr read images only from the suite's test assets, data/inbox, data/nimlab/output,
           data/vision and the WebDAV share; never a file whose name could hold a secret; 5 MB max
  state    the suite's stores, config and WAVs live in data/nimlab/ (gitignored)
  switch   NIMLAB_TOOLS=0 turns the namespace off (every call answers 503)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import threading
import time
import urllib.parse
from collections import deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
SUITE_DIR = ROOT / "vendor" / "nimlab_suite"
STATE_DIR = Path(os.getenv("NIMLAB_STATE_DIR", str(ROOT / "data" / "nimlab")))
SUITE_VERSION = "3.2.0"

CALLS_PER_MIN = int(os.getenv("NIMLAB_CALLS_PER_MIN", "30"))
RANK_MAX_CALLS = int(os.getenv("NIMLAB_RANK_MAX_CALLS", "60"))
HTTP_TIMEOUT = int(os.getenv("NIMLAB_HTTP_TIMEOUT", "60"))
TOOL_TIMEOUT = int(os.getenv("NIMLAB_TOOL_TIMEOUT", "120"))
RANK_TIMEOUT = int(os.getenv("NIMLAB_RANK_TIMEOUT", "600"))
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TEXT_OUT = 8000
ALLOWED_HOST_SUFFIX = "nvidia.com"

SECRET_NAME_RE = re.compile(r"(\.env|token|secret|passw|\.pem|\.key$|id_rsa|id_ed25519|credential|vault)", re.I)
REDACT_RE = re.compile(r"(nvapi-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,}|sk-[A-Za-z0-9_\-]{16,})")

_lock = threading.Lock()
_calls: deque = deque()
_ready = False
_mods: Dict[str, Any] = {}


class NimlabError(Exception):
    def __init__(self, msg: str, status: int = 400, **extra):
        super().__init__(msg)
        self.status = status
        self.extra = extra


def enabled() -> bool:
    return os.getenv("NIMLAB_TOOLS", "1").strip().lower() not in ("0", "false", "off", "no")


def key_var() -> str:
    return os.getenv("NIMLAB_KEY_VAR", "NVIDIA_API_KEY").strip() or "NVIDIA_API_KEY"


def _key() -> str:
    return (os.getenv(key_var()) or "").strip()


def _rel(p: Path) -> str:
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def _redact(text: Any) -> str:
    s = text if isinstance(text, str) else json.dumps(text, default=str)
    k = _key()
    if k and len(k) > 8:
        s = s.replace(k, "[redacted]")
    return REDACT_RE.sub("[redacted]", s)


# ── Loading the suite (state under data/nimlab, never in the repo folder) ─────────────────────

def _load():
    """Import the vendored suite with its data, output and config pointed at data/nimlab."""
    global _ready
    if _ready:
        return _mods
    with _lock:
        if _ready:
            return _mods
        if not (SUITE_DIR / "nimlab" / "__init__.py").is_file():
            raise NimlabError(f"suite not found at {SUITE_DIR}", 503)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        data_dir = STATE_DIR / "data"
        if not data_dir.exists():
            # first run: hand the suite its pre-3.1 registry files; its own migration builds the stores
            # from them and moves the copies into data/nimlab/data/legacy/
            seed = SUITE_DIR / "seed"
            for f in seed.glob("*.json"):
                shutil.copyfile(f, STATE_DIR / f.name)
            if (seed / "output").is_dir():
                (STATE_DIR / "output").mkdir(exist_ok=True)
                for f in (seed / "output").glob("*.json"):
                    shutil.copyfile(f, STATE_DIR / "output" / f.name)
        os.environ["NIMLAB_DATA_DIR"] = str(data_dir)
        os.environ["NIMLAB_OUTPUT_DIR"] = str(STATE_DIR / "output")
        if str(SUITE_DIR) not in sys.path:
            sys.path.insert(0, str(SUITE_DIR))
        from nimlab import config, store  # noqa: E402
        cfg_path = str(STATE_DIR / "config_cluster.json")
        config.CLUSTER_CONFIG = cfg_path
        config.SYSTEM_PROMPTS = str(STATE_DIR / "config_system_prompts.json")
        config.load_cluster_config.__defaults__ = (cfg_path,)
        config.OUTPUT_DIR = str(STATE_DIR / "output")
        store.ensure_all()
        config.ensure_config_files()
        from nimlab import api, router, judge, battery  # noqa: E402
        _mods.update(config=config, store=store, api=api, router=router, judge=judge, battery=battery)
        _ready = True
        return _mods


# ── The gate: host allow-list, per-call budget, shared rate limit ─────────────────────────────

class _Budget:
    def __init__(self, limit: int, wait_s: float = 0.0):
        # wait_s > 0 (ranking only): wait for a rate slot instead of failing, up to wait_s in total
        self.limit, self.used, self.hosts, self.wait_s = limit, 0, set(), wait_s


def _take_rate_slot(budget: Optional["_Budget"] = None) -> None:
    while True:
        now = time.time()
        with _lock:
            while _calls and now - _calls[0] > 60:
                _calls.popleft()
            if len(_calls) < CALLS_PER_MIN:
                _calls.append(now)
                return
            wait = 60 - (now - _calls[0]) + 0.05
        if budget is None or budget.wait_s < wait:
            raise NimlabError(f"nimlab rate limit: {CALLS_PER_MIN} NVIDIA requests a minute; retry in {wait:.0f}s",
                              429, retry_after_s=round(wait))
        budget.wait_s -= wait
        time.sleep(wait)


def host_allowed(url: str) -> bool:
    u = urllib.parse.urlparse(url)
    h = (u.hostname or "").lower()
    return u.scheme == "https" and (h == ALLOWED_HOST_SUFFIX or h.endswith("." + ALLOWED_HOST_SUFFIX))


def _gated(inner: Callable, budget: _Budget) -> Callable:
    def opener(req, timeout=None):
        url = getattr(req, "full_url", str(req))
        if not host_allowed(url):
            raise NimlabError(f"refused: {urllib.parse.urlparse(url).hostname} is not an NVIDIA host", 403)
        if budget.used >= budget.limit:
            raise NimlabError(f"call budget for this tool ({budget.limit} requests) used up", 429)
        _take_rate_slot(budget)
        budget.used += 1
        budget.hosts.add(urllib.parse.urlparse(url).hostname)
        return inner(req, timeout=timeout)
    return opener


_test_opener: Optional[Callable] = None  # tests put a fake transport here; the gate still wraps it


def _client(budget: _Budget, need_key: bool = True):
    m = _load()
    key = _key()
    if need_key and not key:
        raise NimlabError(f"no NVIDIA key in the reactor environment ({key_var()} is empty)", 503)
    cluster = m["config"].load_cluster_config()
    from nimlab.core import HttpClient
    import urllib.request
    http = HttpClient(timeout=HTTP_TIMEOUT, retries=1, backoff=1.5,
                      opener=_gated(_test_opener or urllib.request.urlopen, budget))
    return m["api"].NimClient(api_key=key, http=http, cluster=cluster)


def _result(r, budget: _Budget, **extra) -> Dict[str, Any]:
    out = {"ok": bool(r.ok), "status": r.status, "latency_s": round(r.latency or 0, 3),
           "http_requests": budget.used, "hosts": sorted(h for h in budget.hosts if h)}
    if r.usage:
        out["usage"] = r.usage
    if r.ok and r.text:
        out["text"] = _redact(r.text)[:MAX_TEXT_OUT]
        out["truncated"] = len(r.text) > MAX_TEXT_OUT
    if not r.ok:
        out["error"] = _redact(str(r.error))[:800]
    out.update(extra)
    return out


def _raise_if_failed(out: Dict[str, Any]) -> Dict[str, Any]:
    if not out["ok"]:
        code = out.get("status") or 502
        raise NimlabError(f"NVIDIA answered {out.get('status') or 'no response'}: {out.get('error')}",
                          code if isinstance(code, int) and 400 <= code < 600 else 502, detail=out)
    return out


# ── Files the vision tools may read ───────────────────────────────────────────────────────────

def image_roots() -> List[Path]:
    return [SUITE_DIR / "assets", ROOT / "data" / "inbox", STATE_DIR / "output", ROOT / "data" / "vision",
            Path(os.path.realpath(os.environ.get("WEBDAV_ROOT", str(ROOT / "webdav_root"))))]


def _image(path: str) -> str:
    p = Path(path)
    if not p.is_absolute():
        cand = [ROOT / p, SUITE_DIR / p, SUITE_DIR / "assets" / p]
        p = next((c for c in cand if c.exists()), ROOT / p)
    real = Path(os.path.realpath(p))
    if not any(str(real).startswith(os.path.realpath(r) + os.sep) for r in image_roots()):
        raise NimlabError("images are read only from the suite's assets/, data/inbox, data/nimlab/output, "
                          "data/vision or the WebDAV share", 403)
    if SECRET_NAME_RE.search(real.name):
        raise NimlabError(f"{real.name} could hold a secret; refused", 403)
    if not real.is_file():
        raise NimlabError(f"no file at {path}", 404)
    if real.stat().st_size > MAX_IMAGE_BYTES:
        raise NimlabError("image is over 5 MB", 400)
    if not real.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        raise NimlabError("only .png, .jpg, .jpeg, .webp or .gif images", 400)
    return _load()["api"].image_to_data_url(str(real))


# ── Handlers ──────────────────────────────────────────────────────────────────────────────────

VIEWS = ("verified", "discovered", "failed", "untested", "dropped", "retired", "deprecated", "unlisted",
         "removed", "key", "endpoints", "stale", "benchmarks")
RANK_TYPES = ("chat", "deep_reasoning", "coding", "vision", "ocr", "embeddings", "compactor")


def h_status(a):
    m = _load()
    ov = m["store"].overview()
    ov["data_dir"] = _rel(Path(ov["data_dir"]))
    with _lock:
        used = len([t for t in _calls if time.time() - t <= 60])
    return {"suite": f"nimlab {SUITE_VERSION}", "suite_dir": _rel(SUITE_DIR),
            "key": {"variable": key_var(), "present": bool(_key())}, "stores": ov,
            "rate_limit": {"nvidia_requests_per_min": CALLS_PER_MIN, "used_last_min": used},
            "note": "store counts come from the suite's own files on this disk; 'verified' means the last "
                    "recorded test answered 200, not that the model answers right now"}


def h_capabilities(a):
    rows = {"allowed": [], "refused": []}
    for name, (_, level, _, desc) in TOOLS.items():
        (rows["refused"] if level == "refused" else rows["allowed"]).append(
            {"name": f"nimlab.{name}", "level": level, "description": desc})
    rows["limits"] = {"nvidia_requests_per_min": CALLS_PER_MIN, "per_call_budget": {"nvidia_call": 2,
                      "nvidia_batch": RANK_MAX_CALLS}, "rank_max_models": 3, "http_timeout_s": HTTP_TIMEOUT,
                      "tool_timeout_s": TOOL_TIMEOUT, "rank_timeout_s": RANK_TIMEOUT,
                      "hosts": f"https, {ALLOWED_HOST_SUFFIX} and its subdomains only",
                      "image_roots": [str(r) for r in image_roots()], "max_image_mb": MAX_IMAGE_BYTES // 2**20}
    return rows


def h_list_models(a):
    m = _load()
    which = a.get("list", "verified")
    rows = m["store"].view(which)
    q = (a.get("q") or "").lower()
    if q:
        rows = [r for r in rows if q in (str(r[0]) + " " + str(r[1])).lower()]
    lim = int(a.get("limit", 50))
    return {"list": which, "count": len(rows), "shown": min(lim, len(rows)),
            "rows": [{"id": i, "detail": " ".join(str(d).split())} for i, d in rows[:lim]]}


def h_route(a):
    m = _load()
    r = m["router"].NvidiaRouter().resolve(a["model"], a.get("kind", "chat"))
    ver = m["store"].verified_models().get(a["model"])
    return {"model": a["model"], "route": r, "verified": bool(ver),
            "last_verified": {k: ver.get(k) for k in ("verified_at", "latency_sec", "endpoint", "kind")} if ver else None,
            "source": "the suite's routing rules on disk; nothing was sent"}


def h_fleet(a):
    m = _load()
    cands = m["router"].candidates_by_type()
    t = a.get("type")
    if t:
        return {"type": t, "models": cands.get(t, []), "count": len(cands.get(t, []))}
    return {"types": {k: {"count": len(v), "models": v[:25]} for k, v in cands.items()},
            "note": "from the 200 OK fleet the suite last recorded"}


def h_benchmark_report(a):
    m = _load()
    latest = m["store"].latest_benchmark()
    hist = m["store"].load(m["store"].BENCH_HISTORY).get("runs", [])
    return {"latest": latest or None, "history": hist[-10:],
            "note": None if latest else "no benchmark recorded in the suite's stores yet"}


def h_leaderboard(a):
    m = _load()
    board = m["store"].load(m["store"].LEADERBOARD) or {}
    runs = []
    p = STATE_DIR / "rank_runs.jsonl"
    if p.exists():
        runs = [json.loads(x) for x in p.read_text().splitlines()[-int(a.get("limit", 5)):] if x.strip()]
    return {"judge_leaderboard": board or None, "recent_rank_runs": runs}


def h_voices(a):
    m = _load()
    vs = m["config"].load_cluster_config().get("voice_settings", {})
    return {"voice_profiles": vs.get("voice_profiles"), "tts_url_host": urllib.parse.urlparse(
        os.environ.get("NIMLAB_TTS_URL") or vs.get("tts_url") or m["api"].DEFAULT_TTS_URL).hostname,
            "note": "Magpie voices take the form Magpie-Multilingual.EN-US.<Name>[.<Emotion>]"}


def h_key_models(a):
    b = _Budget(2)
    c = _client(b)
    r = c.list_models()
    out = _result(r, b)
    if r.ok:
        ids = sorted(str(x.get("id")) for x in r.data)
        q = (a.get("q") or "").lower()
        ids = [i for i in ids if q in i.lower()] if q else ids
        lim = int(a.get("limit", 100))
        out.update(count=len(ids), models=ids[:lim])
    return _raise_if_failed(out)


def h_probe(a):
    """One minimal request to see whether a model answers on this key right now."""
    b = _Budget(2)
    c = _client(b)
    kind = a.get("kind", "chat")
    model = a["model"]
    if kind == "embedding":
        r = c.embed(model, ["ping"], input_type="query")
        extra = {"dims": len(r.data[0]) if r.ok and r.data else None}
    else:
        r = c.chat(model, [{"role": "user", "content": "Reply with the single word OK."}],
                   temperature=0.0, max_tokens=8)
        extra = {}
    out = _result(r, b, model=model, kind=kind, answered=bool(r.ok), **extra)
    return out  # a failed probe is a result, not an engine error


def h_chat(a):
    b = _Budget(2)
    c = _client(b)
    msgs = ([{"role": "system", "content": a["system"]}] if a.get("system") else []) + \
           [{"role": "user", "content": a["prompt"]}]
    r = c.chat(a["model"], msgs, temperature=float(a.get("temperature", 0.5)), max_tokens=int(a.get("max_tokens", 512)))
    return _raise_if_failed(_result(r, b, model=a["model"]))


def h_embed(a):
    b = _Budget(3)
    c = _client(b)
    r = c.embed(a["model"], a["texts"], input_type=a.get("input_type"))
    extra = {"model": a["model"]}
    if r.ok:
        vecs = r.data or []
        extra.update(count=len(vecs), dims=len(vecs[0]) if vecs else 0)
        if a.get("return_vectors"):
            extra["vectors"] = vecs
        else:
            extra["preview"] = [[round(x, 5) for x in v[:6]] for v in vecs]
    return _raise_if_failed(_result(r, b, **extra))


def h_vision(a, ocr=False):
    b = _Budget(2)
    img = _image(a["image_path"])
    c = _client(b)
    if ocr:
        r = c.ocr(a["model"], img)
    else:
        r = c.vision(a["model"], img, a.get("prompt") or "Describe this image.", max_tokens=int(a.get("max_tokens", 512)))
    return _raise_if_failed(_result(r, b, model=a["model"], image=a["image_path"],
                                    note="a model's reading of the image, not a verified fact"))


def h_ocr(a):
    return h_vision(a, ocr=True)


def h_rerank(a):
    b = _Budget(2)
    c = _client(b)
    r = c.rerank(a["model"], a["query"], a["passages"])
    extra = {"model": a["model"]}
    if r.ok:
        extra["ranking"] = [{"index": i, "score": round(s, 4), "passage": a["passages"][i][:160]}
                            for i, s in r.data if 0 <= i < len(a["passages"])]
    return _raise_if_failed(_result(r, b, **extra))


_artifact_sink: Optional[Callable[[Path, str], Dict[str, Any]]] = None


def set_artifact_sink(fn: Callable[[Path, str], Dict[str, Any]]) -> None:
    global _artifact_sink
    _artifact_sink = fn


def h_tts(a):
    m = _load()
    b = _Budget(2)
    c = _client(b)
    voice = a.get("voice") or "Magpie-Multilingual.EN-US.Aria"
    r = c.tts(a["text"], voice=voice, language=a.get("language"))
    out = _result(r, b, voice=voice)
    if r.ok:
        data = r.data or b""
        if not m["api"].is_wav(data):
            raise NimlabError("TTS answered but the body is not a WAV", 502)
        (STATE_DIR / "output").mkdir(parents=True, exist_ok=True)
        name = f"tts_{time.strftime('%Y%m%d_%H%M%S')}_{voice.split('.')[-1].lower()}.wav"
        p = STATE_DIR / "output" / name
        p.write_bytes(data)
        out.update(bytes=len(data), duration_s=round(m["api"].wav_duration(data), 2), file=_rel(p))
        if _artifact_sink:
            out["artifact"] = _artifact_sink(p, f"nimlab.tts {voice}: {a['text'][:80]}")
    return _raise_if_failed(out)


def h_rank(a):
    """Rank up to 3 named models on the suite's fixed battery for one type (judge model scores too)."""
    m = _load()
    t, models = a["type"], list(dict.fromkeys(a["models"]))
    b = _Budget(RANK_MAX_CALLS, wait_s=RANK_TIMEOUT * 0.6)
    c = _client(b)
    ranker = m["judge"].Ranker(client=c, log=lambda *x: None)
    if a.get("judge"):
        ranker.judges = [a["judge"]]
    rows = getattr(ranker, f"rank_{t}")(models)
    rows = m["judge"].composite(rows, m["judge"].BLEND[t])
    winner = next((r["model"] for r in rows if r.get("status") == "ok" and (r.get("score") or 0) > 0), None)
    run = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "type": t, "models": models, "judges": ranker.judges,
           "winner": winner, "http_requests": b.used, "rows": json.loads(_redact(rows))}
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "rank_runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(run, default=str) + "\n")
    run["note"] = ("saved to data/nimlab/rank_runs.jsonl; the suite's own leaderboard and role settings "
                   "were not changed")
    return run


def _refused(why: str) -> Callable:
    def h(a):
        raise NimlabError(why, 403)
    return h


# ── Schemas and the table the engine reads ────────────────────────────────────────────────────

def _obj(props: dict, required: list = ()) -> dict:
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


_MODEL = {"type": "string", "minLength": 3, "maxLength": 160, "pattern": r"^[A-Za-z0-9._/:\-]+$"}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 500}
_Q = {"type": "string", "maxLength": 120}
_IMG = {"type": "string", "minLength": 1, "maxLength": 500}

# name: (handler, level, input schema, description)
TOOLS: Dict[str, tuple] = {
    "status": (h_status, "local_read", _obj({}), "Suite version, whether the NVIDIA key is present (never its value), "
               "data-store counts (endpoints, discovered, verified, failed, untested), rate limit use."),
    "capabilities": (h_capabilities, "local_read", _obj({}), "What nimlab tools may run, what is refused, and the limits."),
    "list_models": (h_list_models, "local_read", _obj({"list": {"type": "string", "enum": list(VIEWS)}, "q": _Q,
                                                       "limit": _LIMIT}),
                    "One of the suite's recorded lists (verified 200 OK models by default; discovered, failed, "
                    "untested, endpoints, ...). From disk; nothing is sent."),
    "route": (h_route, "local_read", _obj({"model": _MODEL, "kind": {"type": "string", "enum": [
        "chat", "vision", "embedding", "rerank", "ocr", "tts", "asr", "image", "video"]}}, ["model"]),
              "Which NVIDIA endpoint the suite's router would use for a model, and its last recorded test."),
    "fleet": (h_fleet, "local_read", _obj({"type": {"type": "string", "enum": list(RANK_TYPES) + ["tts"]}}),
              "Recorded 200 OK models grouped by job type (chat, deep_reasoning, coding, vision, ocr, ...)."),
    "benchmark_report": (h_benchmark_report, "local_read", _obj({}),
                         "The latest recorded benchmark run and the last 10 run summaries."),
    "leaderboard": (h_leaderboard, "local_read", _obj({"limit": {"type": "integer", "minimum": 1, "maximum": 20}}),
                    "The suite's judge leaderboard and recent nimlab.rank runs."),
    "voices": (h_voices, "local_read", _obj({}), "Magpie TTS voice profiles the suite knows."),
    "key_models": (h_key_models, "nvidia_call", _obj({"q": _Q, "limit": _LIMIT}),
                   "Ask NVIDIA which models this key lists right now (one GET /v1/models)."),
    "probe": (h_probe, "nvidia_call", _obj({"model": _MODEL, "kind": {"type": "string", "enum": ["chat", "embedding"]}},
                                           ["model"]),
              "One tiny request (8 tokens, or one embedding) to see whether a model answers on this key now."),
    "chat": (h_chat, "nvidia_call", _obj({"model": _MODEL, "prompt": {"type": "string", "minLength": 1, "maxLength": 8000},
                                          "system": {"type": "string", "maxLength": 4000},
                                          "max_tokens": {"type": "integer", "minimum": 1, "maximum": 1024},
                                          "temperature": {"type": "number", "minimum": 0, "maximum": 1.5}},
                                         ["model", "prompt"]),
             "One chat completion from a named NVIDIA model (max 1024 tokens)."),
    "embed": (h_embed, "nvidia_call", _obj({"model": _MODEL, "texts": {"type": "array", "minItems": 1, "maxItems": 16,
                                                                      "items": {"type": "string", "minLength": 1,
                                                                                "maxLength": 4000}},
                                            "input_type": {"type": "string", "enum": ["query", "passage"]},
                                            "return_vectors": {"type": "boolean"}}, ["model", "texts"]),
              "Embed up to 16 texts with a named NVIDIA embedding model."),
    "vision": (h_vision, "nvidia_call", _obj({"model": _MODEL, "image_path": _IMG,
                                              "prompt": {"type": "string", "maxLength": 2000},
                                              "max_tokens": {"type": "integer", "minimum": 1, "maximum": 1024}},
                                             ["model", "image_path"]),
               "Ask a vision model about a local image (suite assets, data/inbox, data/vision, WebDAV share). "
               "Analysis only; never generates images."),
    "ocr": (h_ocr, "nvidia_call", _obj({"model": _MODEL, "image_path": _IMG}, ["model", "image_path"]),
            "Read the text in a local image with a vision/OCR model."),
    "rerank": (h_rerank, "nvidia_call", _obj({"model": _MODEL, "query": {"type": "string", "minLength": 1, "maxLength": 2000},
                                              "passages": {"type": "array", "minItems": 1, "maxItems": 20,
                                                           "items": {"type": "string", "minLength": 1, "maxLength": 4000}}},
                                             ["model", "query", "passages"]),
               "Rank up to 20 passages against a query with a named NVIDIA reranker."),
    "tts": (h_tts, "nvidia_call", _obj({"text": {"type": "string", "minLength": 1, "maxLength": 500},
                                        "voice": {"type": "string", "maxLength": 120, "pattern": r"^Magpie-[A-Za-z0-9.\-]+$"},
                                        "language": {"type": "string", "maxLength": 12}}, ["text"]),
            "Speak up to 500 characters with Magpie TTS; saves a WAV in data/nimlab/output and the artifact store."),
    "rank": (h_rank, "nvidia_batch", _obj({"type": {"type": "string", "enum": list(RANK_TYPES)},
                                          "models": {"type": "array", "minItems": 1, "maxItems": 3, "items": _MODEL},
                                          "judge": _MODEL}, ["type", "models"]),
             f"Score 1-3 named models on the suite's fixed test battery for one job type, with a judge model; "
             f"hard cap {RANK_MAX_CALLS} NVIDIA requests. Saves the run; changes no settings."),
    "sweep": (_refused("sweeps probe hundreds of models; One2lv runs them himself with ./start.sh sweep200"),
              "refused", _obj({}), "Refused here: the 200 health sweep / spec sweep over the whole catalog."),
    "discover": (_refused("discovery scrapes build.nvidia.com, its sitemap and docs; run ./start.sh discover by hand"),
                 "refused", _obj({}), "Refused here: catalog discovery from NVIDIA's public pages."),
    "image_gen": (_refused("image generation goes through the Image app only, never this suite or this machine"),
                  "refused", _obj({}), "Refused: image or video generation."),
    "voice_clone": (_refused("zero-shot voice cloning is not exposed to Lumenis"), "refused", _obj({}),
                    "Refused: voice cloning from a reference clip."),
    "judge_apply": (_refused("changing the suite's role models is One2lv's call; run ./start.sh judge apply"),
                    "refused", _obj({}), "Refused: writing judge winners into the suite's role settings."),
    "mcp_bridge": (_refused("the suite's MCP bridge points at external infrastructure; not wired into the reactor"),
                   "refused", _obj({}), "Refused: the suite's MCP tool loop."),
}

TIMEOUTS = {"local_read": 30, "nvidia_call": TOOL_TIMEOUT, "nvidia_batch": RANK_TIMEOUT, "refused": 5}


def list_rows() -> List[Dict[str, Any]]:
    return [{"name": f"nimlab.{n}", "kind": "nimlab" if lvl != "refused" else "refused", "level": lvl,
             "description": d} for n, (_, lvl, _, d) in TOOLS.items()]


def describe(bare: str) -> Dict[str, Any]:
    if bare not in TOOLS:
        raise KeyError(f"no nimlab tool {bare!r}")
    _, lvl, schema, desc = TOOLS[bare]
    runs = {"local_read": "on this machine from the suite's data stores; nothing is sent",
            "nvidia_call": "one small request to NVIDIA's API (nvidia.com hosts only) with the reactor's key",
            "nvidia_batch": f"a bounded run of NVIDIA requests (cap {RANK_MAX_CALLS})",
            "refused": "never from the reactor"}[lvl]
    return {"name": f"nimlab.{bare}", "kind": "nimlab" if lvl != "refused" else "refused", "level": lvl,
            "description": desc, "inputSchema": schema, "runs": runs, "timeout_s": TIMEOUTS[lvl]}


def summary() -> Dict[str, Any]:
    levels: Dict[str, int] = {}
    for _, lvl, _, _ in TOOLS.values():
        levels[lvl] = levels.get(lvl, 0) + 1
    return {"enabled": enabled(), "suite": f"nimlab {SUITE_VERSION}", "suite_present": (SUITE_DIR / "nimlab").is_dir(),
            "tools": len(TOOLS), "levels": levels, "key_present": bool(_key()), "key_variable": key_var(),
            "nvidia_requests_per_min": CALLS_PER_MIN}
