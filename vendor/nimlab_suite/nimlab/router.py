"""Endpoint registry router and fleet classification.

The routing rules (gateways, static routes, prefix rules, NVCF fallbacks,
per-model overrides) live in data/endpoints.json under "routing"; the
current 200 OK fleet in data/models_verified.json. Both are read through
nimlab.store.
"""

import os

from . import config, store


class NvidiaRouter:
    def __init__(self, registry=None, registry_path=None):
        if registry is None and registry_path:
            if not os.path.exists(registry_path):
                raise FileNotFoundError(f"Missing registry: {registry_path}")
            registry = config.load_json(registry_path, None)
            if not isinstance(registry, dict):
                raise ValueError(f"Registry is not valid JSON: {registry_path}")
            registry = registry.get("routing", registry)  # an endpoints.json works too
        if registry is None:
            registry = store.routing()
        self.reg = registry

    @property
    def gateways(self):
        return self.reg.get("gateways", {})

    def gateway(self, name, default=""):
        return self.gateways.get(name, default).rstrip("/")

    @staticmethod
    def parse_model(model_id):
        mid = model_id.strip("/")
        if "/" in mid:
            publisher, name = mid.split("/", 1)
        else:
            publisher, name = "nvidia", mid
        return publisher, name

    def resolve(self, model_id, kind="chat"):
        """Returns {"url", "method", "kind", "is_nvcf"[, "hint"]}."""
        m_lower = model_id.lower()
        gateways = self.gateways

        override = self.reg.get("explicit_model_overrides", {}).get(model_id)
        if override and override.get("url"):
            # written by the spec sweep from the model's own OpenAPI spec
            out = {"url": override["url"], "method": override.get("method", "POST"),
                   "kind": override.get("kind", kind), "is_nvcf": "nvcf.nvidia.com" in override["url"]}
            for k in ("content_type", "function_id", "api_model_id"):
                if override.get(k):
                    out[k] = override[k]
            return out
        if override:
            base = gateways[override["gateway"]]
            return {"url": f"{base.rstrip('/')}{override['path']}", "method": override.get("method", "POST"),
                    "kind": override.get("kind", kind), "is_nvcf": False}

        for kw in self.reg.get("nvcf_fallbacks", []):
            if kw in m_lower and "magpie" not in m_lower:
                return {"url": gateways.get("nvcf_grpc", ""), "method": "gRPC", "kind": "nvcf_speech",
                        "is_nvcf": True,
                        "hint": f"Model '{model_id}' requires NVCF gRPC (grpc.nvcf.nvidia.com:443) "
                                f"or an NVCF function invocation ID."}

        publisher, name = self.parse_model(model_id)
        for rule in self.reg.get("dynamic_prefix_rules", []):
            if kind == rule["pattern"] or any(k in m_lower for k in rule.get("keywords", [])):
                base = gateways[rule["gateway"]]
                return {"url": f"{base.rstrip('/')}{rule['prefix']}/{publisher}/{name}", "method": "POST",
                        "kind": rule["kind"], "is_nvcf": False}

        route = self.reg.get("static_routes", {}).get(kind)
        if route:
            base = gateways[route["gateway"]]
            return {"url": f"{base.rstrip('/')}{route['path']}", "method": route.get("method", "POST"),
                    "kind": kind, "is_nvcf": False}

        return {"url": f"{gateways['integrate'].rstrip('/')}/chat/completions", "method": "POST",
                "kind": "chat", "is_nvcf": False}


# ---------------------------------------------------------------------------
# Model classification
# ---------------------------------------------------------------------------
VISION_HINTS = ("vision", "-vl-", "-vl", "vl-", "vlm", "vila", "neva", "kosmos", "omni",
                "qwen2-vl", "qwen2.5-vl")
OCR_HINTS = ("parse", "ocr", "docling", "document")
NON_CHAT_HINTS = ("guard", "safety", "translate", "parse", "embed", "rerank", "magpie", "tts", "parakeet",
                  "canary", "riva", "whisper")


def classify_hint(model):
    """Human label used by the playground's catalog view."""
    m = model.lower()
    if any(x in m for x in ("magpie", "riva", "speech", "tts", "fastpitch")):
        return "Audio TTS (Text-to-Speech)"
    if any(x in m for x in ("parakeet", "canary", "whisper", "asr")):
        return "Audio ASR (Speech-to-Text Transcription)"
    if any(x in m for x in ("rerank", "reranker")):
        return "Ranking / Rerank"
    if any(x in m for x in ("embed", "nvclip")):
        return "Embeddings"
    if any(x in m for x in OCR_HINTS):
        return "Document / OCR"
    if any(x in m for x in ("flux", "stable-diffusion", "sdxl", "imagen", "image-gen")):
        return "Image Generation"
    if any(x in m for x in VISION_HINTS):
        return "Multimodal Vision (Image + Text)"
    return "Language / Chat Completion"


def model_types(model_id, kind, catalog_kind=None):
    """Judge types a live model is a candidate for, from its id, sweep kind
    and (when known) the discovery catalog's kind."""
    m = model_id.lower()
    kind = (kind or "").lower()
    types = set()
    ck = (catalog_kind or "").lower()
    if ck in ("safety", "translation", "biology", "simulation", "rerank", "asr", "video", "image_gen", "cv"):
        return types
    if ck == "embedding":
        return {"embeddings"}
    if ck == "tts":
        return {"tts"}
    if ck == "ocr":
        return {"ocr", "vision"} if kind == "vision" else {"ocr"}
    if kind in ("rerank", "audio_asr", "image_gen", "vision_task", "video", "other", "completions"):
        return types
    if kind == "document":
        types.add("ocr")
        return types
    if kind.startswith("embed") or "embed" in m:
        types.add("embeddings")
        return types
    if kind in ("audio_tts",) or "magpie" in m or "tts" in m:
        types.add("tts")
        return types
    is_vision = kind == "vision" or any(h in m for h in VISION_HINTS)
    is_ocr = any(h in m for h in OCR_HINTS)
    if is_vision:
        types.update(("vision", "ocr"))
    if is_ocr:
        types.add("ocr")
    if kind in ("chat", "chat_stream", "vision", "") and not any(h in m for h in NON_CHAT_HINTS):
        types.update(("chat", "deep_reasoning", "coding", "compactor"))
    return types


def load_live_fleet(path=None):
    """{model_id: entry} of the current 200 OK fleet (data/models_verified.json).
    path reads another file instead: a models_verified.json or a pre-3.1
    verified-endpoints file."""
    if path is None:
        return store.verified_models()
    data = config.load_json(path, {}) or {}
    if isinstance(data.get("models"), dict):
        data = data["models"]
    live = {}
    for model_id, entry in data.items():
        if isinstance(entry, dict) and str(entry.get("status", "")).upper() in ("LIVE_200", "200", "OK"):
            live[model_id] = entry
    return live


def candidates_by_type(fleet=None, overrides=None):
    """{type: [model_id, ...]} built from the live fleet, with optional
    per-type overrides from judge_settings.candidate_overrides."""
    fleet = load_live_fleet() if fleet is None else fleet
    cat = None
    if any(not e.get("catalog_kind") for e in fleet.values()):
        from . import catalog  # older sweep entries: take the kind from the discovered models
        cat = catalog.load_catalog()
    out = {t: [] for t in ("chat", "deep_reasoning", "coding", "vision", "ocr", "embeddings", "compactor", "tts")}
    for model_id in sorted(fleet):
        entry = fleet[model_id]
        ck = entry.get("catalog_kind")
        if not ck and cat:
            from . import catalog
            ck = catalog.kind_of(model_id, cat)
        for t in model_types(model_id, entry.get("kind"), ck):
            out.setdefault(t, []).append(model_id)
    for t, models in (overrides or {}).items():
        if isinstance(models, list) and models:
            # overrides narrow the field; models without a 200 test are left out
            out[t] = [m for m in models if m in fleet]
    return out
