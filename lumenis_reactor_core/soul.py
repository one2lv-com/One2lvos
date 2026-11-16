"""
Soul layer (L0) and layer citation (items 1 and 4).

rules_block()  the RULES section of memory_layers/SOUL.md, re-read when the file changes. It is loaded into
               every answer next to HONESTY_RULES; the Arbiter truth check still runs after.
cite(layers)   one short line saying where an answer came from (soul, live status, stable memory, fuzzy
               memory, dream, skill/tool, external). Built from what the reactor actually used this turn,
               not from what the model says it used.
"""
from __future__ import annotations

import re
from pathlib import Path

SOUL_PATH = Path(__file__).resolve().parent.parent / "memory_layers" / "SOUL.md"
_cache = {"mtime": None, "text": "", "rules": ""}
_FALLBACK = ("1. Never make up events. 2. Say when memory is missing. 3. Never call unverified claims fact. "
             "4. Show errors instead of hiding them. 5. Tool calls are logged before they run.")
CITE_PREFIX = "\n\n— Sources: "
_CITE_RE = re.compile(r"\n*— Sources: [^\n]*\s*$")


def _load():
    try:
        m = SOUL_PATH.stat().st_mtime
    except OSError:
        _cache.update(mtime=None, text="", rules=_FALLBACK)
        return
    if m == _cache["mtime"]:
        return
    text = SOUL_PATH.read_text(encoding="utf-8")
    mm = re.search(r"^## RULES\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    _cache.update(mtime=m, text=text, rules=(mm.group(1).strip() if mm else _FALLBACK))


def rules() -> str:
    _load()
    return _cache["rules"]


def full_text() -> str:
    _load()
    return _cache["text"] or ("SOUL.md missing; fallback rules:\n" + _FALLBACK)


def loaded() -> bool:
    _load()
    return _cache["mtime"] is not None


def rules_block() -> str:
    return ("SOUL RULES (layer L0, from SOUL.md; always in force, alongside the honesty rules):\n" + rules())


_ORDER = ["soul", "live status", "stable memory", "fuzzy memory", "vector memory", "dream", "skill",
          "tool", "arcade", "external"]


def memory_layers(facts) -> list:
    """Map recalled fact rows to the layers they belong to."""
    out = []
    for f in facts or []:
        sc = (f.get("scope") if isinstance(f, dict) else None) or "fuzzy"
        out.append("stable memory" if sc == "stable" else "fuzzy memory")
    return out


def cite(layers) -> str:
    seen = []
    for l in layers:
        if l and l not in seen:
            seen.append(l)
    seen.sort(key=lambda x: _ORDER.index(x) if x in _ORDER else 99)
    return CITE_PREFIX + " · ".join(seen)


def strip_cite(text: str) -> str:
    return _CITE_RE.sub("", text or "")
