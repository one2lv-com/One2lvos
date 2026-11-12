"""The 16 testbed roles: definitions, config migration and candidate filters.

Each role in config_cluster.json is stored as a dict:

    {"label": "Conversational Persona LLM", "backend": "model",
     "model": "poolside/laguna-xs-2.1", "endpoint": null}
    {"label": "...", "backend": "mcp", "tool": "tts_speak",
     "arg_map": {"text": "input"}}

A plain string is still accepted everywhere and means a model backend
(that is how roles were stored up to v3.1). A role with model null is
unset. The TTS role may also carry "voice_clone": {"path", "transcript"}.

This module is pure: no network, no prompts. The interactive menus live in
orchestrator_testbed.py and the calls in nimlab/entity.py.
"""

import re

MODEL = "model"
MCP = "mcp"

# support levels for "can NVIDIA's hosted API serve this role here?"
YES = "yes"
PARTIAL = "partial"
NO = "no"


def _rx(s):
    return re.compile(s, re.I) if s else None


class RoleDef:
    def __init__(self, key, name, input_kind, kinds=(), match=None, extra=None, exclude=None, fallback=(),
                 support=YES, note="", prompt_key=None, command=None, output="text", match_on="text"):
        self.key = key
        self.name = name
        self.input_kind = input_kind      # what the role is given (drives MCP arg mapping)
        self.kinds = tuple(kinds)         # catalog kinds that suit the role
        self.match = _rx(match)           # when set, a model of a suited kind must also match it
        self.extra = _rx(extra)           # id/label match that suits the role whatever the kind
        self.exclude = _rx(exclude)       # never "suited" (still "possible" via fallback kinds)
        self.fallback = tuple(fallback)   # kinds that are possible but not ideal
        self.support = support
        self.note = note
        self.prompt_key = prompt_key or key
        self.command = command
        self.output = output              # text | audio | image
        self.match_on = match_on          # "text" = id + catalog labels, "id" = model id only


SMALL = r"nano|mini|small|flash|lite|bolt|instant|haiku|tiny|e2b|e4b|(?<![\d.])[0-9](\.[0-9])?b(?![a-z0-9])"
REASON = (r"reason|think|\br1\b|qwq|ultra|magistral|gpt-oss|405b|253b|235b|480b|550b|-1t-|long context|"
          r"agentic")
CODE = r"coder|codestral|devstral|starcoder|coding|code|tool use|tool calling|function calling|agentic|poolside|laguna"
NOT_TEXT = r"guard|safety|translate|nmt|rerank|embed|reward|calibration|parse|ocr|paligemma|clip|detect"

ROLE_DEFS = [
    RoleDef("intent_router", "Intent Router / Fast Dispatcher", "text", kinds=("chat",), match=SMALL,
            match_on="id", exclude=NOT_TEXT + r"|coder", fallback=("chat", "vision"),
            note="Decides which role handles each chat turn. Unset: slash commands and simple rules route instead."),
    RoleDef("persona", "Conversational Persona LLM", "text", kinds=("chat",),
            exclude=NOT_TEXT + r"|coder|codestral", fallback=("chat", "vision"),
            note="Normal chat in the soul.md persona."),
    RoleDef("reasoning", "Agentic Long-Context & Reasoning Model", "text", kinds=("chat", "vision"), match=REASON,
            exclude=NOT_TEXT, fallback=("chat", "vision"), command="/deep"),
    RoleDef("coding", "Dedicated Coding & Tool-Calling Model", "text", kinds=("chat", "vision"), match=CODE,
            exclude=NOT_TEXT, fallback=("chat", "vision"), command="/code",
            note="Also runs the MCP tool steps of a turn."),
    RoleDef("vision", "Multimodal Vision-Language Model (VLM)", "image", kinds=("vision",),
            exclude=r"ocr|parse|deplot|graphic-elements|page-elements|table-structure|detect|clip|embed|"
                    r"rerank|segment|grounding",
            fallback=("vision",), command="/image"),
    RoleDef("ocr", "Document & Structured OCR Model", "image", kinds=("ocr",),
            extra=r"ocr|nemotron-parse|nemoretriever-parse|paddle|docling|table-structure|page-elements",
            exclude=r"embed|rerank", fallback=("vision",), command="/ocr"),
    RoleDef("chart_parser", "Chart & Plot Parser", "image", extra=r"deplot|chart|graphic-elements|plot",
            exclude=r"embed|rerank", fallback=("vision", "ocr"), command="/chart",
            note="Chart/plot images. A general VLM is the fallback when no chart model is set."),
    RoleDef("video", "Video & Temporal Understanding Model", "video",
            extra=r"cosmos-reason|cosmos3-nano-reasoner|video-understand|vila|omni|video-?llm|qwen.*-vl",
            exclude=r"detect|lipsync|eyecontact|relighting|bnr|vsr|animate|predict|transfer|speaker|synthetic|"
                    r"embed|rerank",
            fallback=("vision",), support=PARTIAL, command="/video",
            note="Sends the clip as a video_url part on chat/completions. Only models that accept video "
                 "input answer (Cosmos Reason style); untested live."),
    RoleDef("asr", "Automatic Speech Recognition (ASR / STT)", "audio", kinds=("asr",),
            extra=r"parakeet|canary|whisper|-asr|asr-|transcri", fallback=(), support=PARTIAL,
            command="/listen",
            note="Hosted ASR is mostly gRPC. HTTP works when the model has an NVCF function id "
                 "(POST /v1/audio/transcriptions) or you set an endpoint, or use an MCP tool."),
    RoleDef("omni_audio", "Omni-Modal Audio-Language Model (Music & Ambient Audio)", "audio",
            extra=r"omni|phi-4-multimodal|gemma-3n|audio-?flamingo|qwen.*audio|audio-?language|audio-?llm",
            exclude=r"tts|magpie|studiovoice|bnr|asr|parakeet|canary|whisper|embed|rerank",
            fallback=(), support=PARTIAL, command="/audio",
            note="Sends audio as an input_audio part on chat/completions; only omni models that accept "
                 "audio answer. Untested live."),
    RoleDef("tts", "Neural Text-to-Speech (TTS)", "text", kinds=("tts",),
            extra=r"magpie-tts|fastpitch|chatterbox|-tts\b|tts-", exclude=r"studiovoice", fallback=("tts",),
            support=YES, command="/say", output="audio",
            note="Spoken replies (auto TTS) and /say. Magpie over NVCF HTTP; voice cloning on zero-shot models."),
    RoleDef("image_gen", "Text-to-Image Generation Model", "prompt", kinds=("image_gen",),
            extra=r"flux|stable-diffusion|sdxl|sana|qwen-image|imagen", exclude=r"trellis|edit|kontext",
            fallback=("image_gen",), command="/imagine", output="image",
            note="Saves PNGs to output/. Uses the ai.api.nvidia.com genai route."),
    RoleDef("audio_gen", "Audio / Music Generation Model", "prompt",
            extra=r"music|fugatto|audiogen|musicgen|sound-?gen|stable-audio|audio-?gen|tango|riffusion|audioldm",
            exclude=r"tts|magpie|asr", fallback=(), support=NO, command="/compose", output="audio",
            note="NVIDIA's hosted API has no audio/music generation model (discover found none). "
                 "Back this role with an MCP tool or set a custom endpoint."),
    RoleDef("embedding", "Dense Text & Multimodal Embedding Model", "text", kinds=("embedding",),
            extra=r"embed|nvclip|\be5-|bge-", exclude=r"rerank", fallback=("embedding",),
            note="Vector memory (store and recall)."),
    RoleDef("reranker", "Semantic Reranker Model", "query_passages", kinds=("rerank",), extra=r"rerank",
            fallback=(), note="Reranks the top-k memory hits before they reach the persona."),
    RoleDef("guard_translate", "Translation & Guardrail Model", "text", kinds=("safety", "translation"),
            extra=r"guard|safety|translate|nmt|jailbreak|topic-control", fallback=("chat",),
            command="/translate",
            note="Optional input/output safety check (Settings) and /translate."),
]

ROLE_KEYS = [d.key for d in ROLE_DEFS]
BY_KEY = {d.key: d for d in ROLE_DEFS}

# roles kept outside the 16 (still used internally)
EXTRA_ROLES = {"compactor": "History Compactor (internal)"}

# old role key -> new role key
LEGACY_MAP = {
    "main_brain": "persona", "main": "persona", "chat": "persona", "brain": "persona",
    "deep_reasoning": "reasoning", "reasoner": "reasoning", "thinker": "reasoning",
    "coding_agent": "coding", "coder": "coding", "code": "coding", "tool_calling": "coding",
    "vlm": "vision",
    "ocr_document": "ocr", "document": "ocr", "ocr_model": "ocr",
    "chart": "chart_parser", "chart_plot": "chart_parser",
    "video_understanding": "video",
    "stt": "asr", "speech_to_text": "asr", "transcriber": "asr",
    "audio": "omni_audio", "audio_language": "omni_audio",
    "voice_tts": "tts", "voice": "tts", "text_to_speech": "tts",
    "image": "image_gen", "text_to_image": "image_gen", "image_generation": "image_gen",
    "music": "audio_gen", "music_gen": "audio_gen", "audio_generation": "audio_gen",
    "embed": "embedding", "embeddings": "embedding",
    "rerank": "reranker", "ranker": "reranker",
    "guard": "guard_translate", "guardrail": "guard_translate", "safety": "guard_translate",
    "translate": "guard_translate", "translation": "guard_translate",
    "router": "intent_router", "dispatcher": "intent_router", "fast_router": "intent_router",
}


# ---------------------------------------------------------------------------
# Role values
# ---------------------------------------------------------------------------
def label(key):
    d = BY_KEY.get(key)
    return d.name if d else EXTRA_ROLES.get(key, key)


def normalize(value, key=None):
    """Any stored role value -> a dict with backend/model/tool fields."""
    if isinstance(value, dict):
        out = dict(value)
        backend = out.get("backend") or (MCP if out.get("tool") else MODEL)
        out["backend"] = backend if backend in (MODEL, MCP) else MODEL
    elif isinstance(value, str) and value.strip():
        out = {"backend": MODEL, "model": value.strip()}
    else:
        out = {"backend": MODEL, "model": None}
    if key:
        out.setdefault("label", label(key))
    if out["backend"] == MODEL:
        out.setdefault("model", None)
    else:
        out.setdefault("tool", None)
        out.setdefault("arg_map", {})
    return out


def model_of(value):
    """The model id of a model-backed role, else None (unset or MCP)."""
    v = normalize(value)
    return v.get("model") if v["backend"] == MODEL else None


def is_set(value):
    v = normalize(value)
    return bool(v.get("model") if v["backend"] == MODEL else v.get("tool"))


def role_models(roles):
    """{role_key: model_id} for model-backed, set roles (what the judge and
    the status header compare against)."""
    out = {}
    for k, v in (roles or {}).items():
        m = model_of(v)
        if m:
            out[k] = m
    return out


def describe(value):
    """Short one-line text for menus: 'model: x', 'MCP tool: y', '(unset)'."""
    v = normalize(value)
    if v["backend"] == MCP:
        return f"[MCP] {v['tool']}" if v.get("tool") else "[MCP] (no tool picked)"
    if not v.get("model"):
        return "(unset)"
    s = f"[model] {v['model']}"
    if v.get("endpoint"):
        s += f" @ {v['endpoint']}"
    return s


def clone_text(value):
    vc = normalize(value).get("voice_clone") or {}
    if vc.get("path"):
        import os
        return f"cloned voice: {os.path.basename(vc['path'])}"
    return ""


def set_model(roles, key, model, endpoint=None):
    """Point a role at a model (None = unset). Keeps the label and, for the
    same model, its voice clone."""
    old = normalize(roles.get(key), key)
    new = {"label": old.get("label") or label(key), "backend": MODEL, "model": model or None}
    if endpoint:
        new["endpoint"] = endpoint
    if key == "tts" and old.get("voice_clone") and old.get("model") == model:
        new["voice_clone"] = old["voice_clone"]
    roles[key] = new
    return new


def set_mcp(roles, key, tool, arg_map=None):
    old = normalize(roles.get(key), key)
    new = {"label": old.get("label") or label(key), "backend": MCP, "tool": tool, "arg_map": dict(arg_map or {})}
    if key == "tts" and old.get("voice_clone"):
        new["voice_clone"] = old["voice_clone"]
    roles[key] = new
    return new


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------
def migrate_roles(roles, fleet=None, kinds=None):
    """Old role dict -> the 16 role keys (plus kept extras).

    * old keys map to their new category (main_brain -> persona, ...);
      an explicit new key wins over a mapped old one
    * keys that map nowhere are kept as they are (compactor and custom ones)
    * missing categories get a default from the verified fleet (best suited
      model) when there is one, else stay unset; a key the user already set
      to null stays unset
    * plain strings become {"backend": "model", ...} dicts with a label

    fleet: verified model ids (list); kinds: {model_id: catalog kind}.
    Returns (new_roles, changes) where changes lists human-readable lines.
    """
    roles = dict(roles or {})
    out, changes = {}, []
    for k in ROLE_KEYS:                      # explicit new keys first
        if k in roles:
            out[k] = normalize(roles[k], k)
    for old, val in roles.items():
        if old in BY_KEY:
            continue
        new = LEGACY_MAP.get(old)
        if new and new not in out:
            out[new] = normalize(val, new)
            changes.append(f"{old} -> {new} ({describe(val)})")
        elif new:
            out[old] = val                   # keep: the new key was already set
            changes.append(f"{old} kept as is ({new} was already set)")
        else:
            out[old] = val                   # unmappable: keep untouched
    fleet = list(fleet or [])
    for k in ROLE_KEYS:
        if k in out:
            continue
        pick = None
        if fleet:
            if k == "intent_router" and model_of(out.get("compactor")) in fleet:
                pick = model_of(out.get("compactor"))
            else:
                tiers = candidates(k, fleet, kinds or {})
                pick = tiers[0][0] if tiers[0] else None
        out[k] = normalize(pick, k)
        changes.append(f"{k} created: {describe(pick)}" + (" (from the verified fleet)" if pick else ""))
    ordered = {k: out[k] for k in ROLE_KEYS}
    for k, v in out.items():
        if k not in ordered:
            ordered[k] = v
    return ordered, changes


def needs_migration(roles, fleet=None, kinds=None):
    """True when migrate_roles would change anything (it is idempotent)."""
    new, _ = migrate_roles(roles, fleet, kinds)
    return new != dict(roles or {})


def migrate_combo_roles(combo_roles):
    """Judge entity_combos use role keys too."""
    out = {}
    for k, v in (combo_roles or {}).items():
        out[LEGACY_MAP.get(k, k) if k not in BY_KEY else k] = v
    return out


# ---------------------------------------------------------------------------
# Candidate filters
# ---------------------------------------------------------------------------
def _text(mid, info):
    labels = " ".join(info.get("labels") or []) if isinstance(info, dict) else ""
    return f"{mid} {labels}"


def fit(key, model_id, kind=None, info=None):
    """2 = suited, 1 = possible, 0 = not for this role."""
    d = BY_KEY[key]
    kind = (kind or "").lower()
    text = _text(model_id, info or {})
    excluded = bool(d.exclude and d.exclude.search(model_id))
    if not excluded:
        if d.extra and d.extra.search(text):
            return 2
        if kind and kind in d.kinds and (d.match is None or d.match.search(model_id if d.match_on == "id" else text)):
            return 2
    if kind and kind in d.fallback and not excluded:
        return 1
    if not kind and d.fallback:
        from .router import model_types
        if any(t in d.fallback for t in _types_as_kinds(model_types(model_id, None))):
            return 1
    return 0


def _types_as_kinds(types):
    m = {"chat": "chat", "reasoning": "chat", "code": "chat", "vision": "vision", "ocr": "ocr",
         "embedding": "embedding", "tts": "tts"}
    return {m[t] for t in types if t in m}


def candidates(key, models, kinds=None, infos=None):
    """Split a model list for one role: (suited, possible, other), each in
    the input order. kinds: {model_id: kind}; infos: {model_id: catalog
    entry} for labels. Unknown kinds fall back to router.model_types."""
    kinds, infos = kinds or {}, infos or {}
    tiers = ([], [], [])
    for m in models:
        kind = kinds.get(m)
        if not kind:
            from .router import model_types
            k = _types_as_kinds(model_types(m, None))
            kind = "chat" if "chat" in k else (sorted(k)[0] if k else None)
        f = fit(key, m, kind, infos.get(m))
        tiers[2 - f].append(m)
    return tiers


def _read_data(name):
    """Read a data/ file without creating anything (no migration, no mkdir)."""
    import json
    import os
    from . import store
    p = os.path.join(store.data_dir(), name)
    try:
        with open(p, "r", encoding="utf-8") as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def kinds_from_store():
    """({model_id: kind}, {model_id: catalog entry}) from the discovered and
    verified lists in data/. Read-only: never creates or migrates files."""
    from . import store
    kinds, infos = {}, {}
    for mid, e in (_read_data(store.DISCOVERED).get("models") or {}).items():
        if isinstance(e, dict):
            infos[mid] = e
            if e.get("kind"):
                kinds[mid] = e["kind"]
    for mid, rec in (_read_data(store.VERIFIED).get("models") or {}).items():
        if not isinstance(rec, dict):
            continue
        k = rec.get("catalog_kind") or kinds.get(mid) or rec.get("kind")
        if k:
            kinds[mid] = {"audio_tts": "tts", "nvcf_speech": "asr"}.get(k, k)
    return kinds, infos


def verified_ids_readonly():
    from . import store
    return list((_read_data(store.VERIFIED).get("models") or {}).keys())


# ---------------------------------------------------------------------------
# Voice cloning
# ---------------------------------------------------------------------------
# Documented in NVIDIA's TTS NIM HTTP reference: POST /v1/audio/synthesize,
# multipart field audio_prompt (16-bit mono WAV, 22.05 kHz or higher, 3-10 s),
# audio_prompt_transcript accepted but unused by current models.
CLONE_MODELS = {
    "nvidia/magpie-tts-zeroshot": {"field": "audio_prompt", "transport": "multipart",
                                   "voice": "Magpie-ZeroShot-Multilingual", "needs_transcript": False,
                                   "function_id": "55cf67bf-600f-4b04-8eac-12ed39537a08"},
    "nvidia/magpie-tts-flow": {"field": "audio_prompt", "transport": "multipart",
                               "voice": "Magpie-Flow", "needs_transcript": True},
}
TTS_FUNCTION_IDS = {
    "nvidia/magpie-tts-multilingual": "877104f7-e885-42b9-8de8-f6e4c6303969",
    "nvidia/magpie-tts-zeroshot": "55cf67bf-600f-4b04-8eac-12ed39537a08",
}


def clone_support(model, spec_text=""):
    """Clone settings for a TTS model, or None when it can't clone.
    Known models first; otherwise a zero-shot/flow id or a spec that
    mentions audio_prompt counts."""
    if not model:
        return None
    m = model.lower()
    if m in CLONE_MODELS:
        return dict(CLONE_MODELS[m])
    if re.search(r"zero-?shot|tts-flow", m) or "audio_prompt" in (spec_text or ""):
        return {"field": "audio_prompt", "transport": "multipart", "voice": None,
                "needs_transcript": "flow" in m or "audio_prompt_transcript\" is required" in (spec_text or "")}
    return None
