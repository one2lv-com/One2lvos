"""Keep safety / guard / classifier models out of the reactor's chat seats.

The owner does not want a safety model answering in the Lumenis reactor core (2026-11-16).
Models such as nvidia/llama-3.1-nemoguard-8b-topic-control or ...-content-safety are classifiers:
they either return a verdict instead of an answer or fail (HTTP 500 on 2026-11-16), so every call
to them fell through to the fallback model. This module is dependency-free so both the reactor and
update_nvidia_models.py (run by startos.sh) can use the same rule.
"""
from __future__ import annotations

import os
import re

# Names that mark a model as a guard, safety classifier or non-chat model.
SAFETY_RE = re.compile(
    r"(guard|safety|safeguard|content-?safe|topic-?control|jailbreak|shield|moderat|"
    r"reward|\bpii\b|-pii|detector|classif|aegis)", re.I)
# Models that are not chat models at all (embedding, retrieval, speech, image generation ...).
NON_CHAT_RE = re.compile(
    r"(embed|rerank|retriever|parse|translate|\bclip\b|-clip|tts|asr|whisper|riva|fastpitch|"
    r"cosmos|calibrat|ocdr|ocr|nv-grounding|stable-diffusion|flux|sdxl|starcoder|deplot|kosmos)", re.I)

# Working chat models measured live on the owner's NVIDIA key, 2026-11-16 (one short request each):
# bolt-e4b 0.6 s, ultra-550b 1.0 s, super-vl-120b 1.3 s, nano-omni-reasoning 1.3 s, lightning-30b 2.2 s.
DEFAULT_PRIMARY = "nvidia/nemotron-3.5-super-vl-120b-a12b"
DEFAULT_SECONDARY = "nvidia/nemotron-3-ultra-550b-a55b"
DEFAULT_REASONING = "nvidia/nemotron-3.5-lightning-30b-a3b"
DEFAULT_FAST = "nvidia/nemotron-3.5-bolt-e4b"


def is_safety_model(model_id: str | None) -> bool:
    return bool(model_id) and bool(SAFETY_RE.search(model_id))


def is_chat_candidate(model_id: str | None) -> bool:
    """True for a model that may answer chat in a seat (not a guard, not a non-chat model)."""
    return bool(model_id) and not SAFETY_RE.search(model_id) and not NON_CHAT_RE.search(model_id)


def chat_model(value: str | None, default: str) -> str:
    """Return value unless it is empty or a safety/non-chat model; then the default."""
    v = (value or "").strip()
    if v and is_chat_candidate(v):
        return v
    return default


def env_chat_model(name: str, default: str) -> str:
    return chat_model(os.environ.get(name), default)
