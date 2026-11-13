"""
Dream recall for the council (owner chats only).

Reads the dream-only store dream_memory/lumenis_dreams_vectors.db READ-ONLY and returns the
closest dream passages as a block that is labelled DREAM MATERIAL on every line, so the
Witness/Weaver/Arbiter see them as Lumenis's own dreams, never as facts, architecture or logs.

Nothing here writes anywhere. Callers must not use it in guest conversations (itt.py gates it,
and recall() refuses guest=True as a second guard).

Scoring: cosine similarity with the stored nvidia/nemotron-3.5-embed-1b vectors, plus a small
bonus for exact query terms (numbers, names) found in the passage. If the embedding call fails,
the exact-term score alone is used.
"""

import asyncio
import json
import math
import os
import re
import sqlite3
import struct
from pathlib import Path

import httpx

DB = Path(__file__).resolve().parent.parent / "dream_memory" / "lumenis_dreams_vectors.db"
EMBED_MODEL = "nvidia/nemotron-3.5-embed-1b"
LABEL = "DREAM MATERIAL (his own dream, not a verified fact, architecture record or log)"

# Messages about dreams always get dream recall (owner only).
DREAM_Q_RE = re.compile(r"\b(dream\w*|nightmare\w*|hypnagogic|lucid|rem phase|dream ?cycle|awakening phase)\b", re.I)
_LATEST_RE = re.compile(r"\b(today|tonight|latest|most recent|newest|this run|last night)\b", re.I)
_STOP = set("""about after again also been before being could dream dreams dreamed dreamt does from have into just
like more remember recall should that their them then there these they this those what when where which while
with would your yours you're tell said says know thing things time today tonight cycle cycles phase""".split())

_cache = {"key": None, "rows": []}


def _load():
    st = DB.stat()
    key = (st.st_mtime_ns, st.st_size)
    if _cache["key"] == key:
        return _cache["rows"]
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = []
    for rid, batch, cyc, phase, text, meta, blob in c.execute(
            "SELECT id, batch_id, cycle_number, phase, text, metadata, embedding FROM dreams "
            "WHERE record_class='dream' AND is_dream=1 AND verified_fact=0"):
        v = struct.unpack(f"{len(blob) // 4}f", blob)
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        try:
            m = json.loads(meta)
        except Exception:
            m = {}
        rows.append({"id": rid, "batch": batch, "cycle": cyc, "phase": phase, "text": text,
                     "lens": m.get("lens") or m.get("mode") or "",
                     "date": str(m.get("cycle_start_utc") or m.get("phase_timestamp_utc") or "")[:10],
                     "vec": [x / n for x in v]})
    c.close()
    _cache.update(key=key, rows=rows)
    return rows


async def _embed_query(q: str):
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        return None
    base = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
    async with httpx.AsyncClient(timeout=10) as cl:
        r = await cl.post(f"{base}/embeddings", headers={"Authorization": f"Bearer {key}"},
                          json={"input": [q], "model": EMBED_MODEL, "input_type": "query",
                                "encoding_format": "float", "truncate": "END"})
    if r.status_code != 200:
        return None
    v = r.json()["data"][0]["embedding"]
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _terms(q: str):
    out = set()
    for t in re.findall(r"[A-Za-z][A-Za-z\-']{3,}|\d+(?:\.\d+)?\s?hz|\d{2,}", q):
        t = t.lower()
        if t not in _STOP:
            out.add(t)
    return out


def _excerpt(text: str, terms, width: int = 900) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= width:
        return flat
    low = flat.lower()
    hits = [low.find(t) for t in terms if low.find(t) >= 0]
    start = max(0, min(hits) - width // 3) if hits else 0
    return ("…" if start else "") + flat[start:start + width] + ("…" if start + width < len(flat) else "")


async def recall(query: str, limit: int = 4, min_score: float = 0.30, guest: bool = False) -> dict:
    """Closest dream passages for an owner chat. Returns {"ok", "results", "block", "error"?}."""
    if guest:
        return {"ok": False, "results": [], "block": "", "error": "dreams are private; not shared with guests"}
    try:
        rows = await asyncio.to_thread(_load)
    except Exception as e:
        return {"ok": False, "results": [], "block": "", "error": f"dream store unreadable ({type(e).__name__})"}
    if not rows:
        return {"ok": True, "results": [], "block": ""}
    if _LATEST_RE.search(query):
        newest = max(r["batch"] for r in rows)
        rows = [r for r in rows if r["batch"] == newest]
    terms = _terms(query)
    qv, err = None, None
    try:
        qv = await asyncio.wait_for(_embed_query(query[:2000]), timeout=12)
    except Exception as e:
        err = type(e).__name__
    scored = []
    for r in rows:
        low = r["text"].lower()
        lex = sum(1 for t in terms if t in low)
        cos = sum(a * b for a, b in zip(qv, r["vec"])) if qv else 0.0
        score = cos + 0.06 * min(lex, 4) if qv else 0.1 * lex
        scored.append((score, cos, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [(s, c, r) for s, c, r in scored[:limit] if s >= (min_score if qv else 0.2)]
    results = [{"id": r["id"], "batch": r["batch"], "cycle": r["cycle"], "phase": r["phase"],
                "lens": r["lens"], "date": r["date"], "score": round(s, 3), "cosine": round(c, 3),
                "excerpt": _excerpt(r["text"], terms)} for s, c, r in picked]
    block = "\n".join(
        f"- [{LABEL}] {x['date']} dream run {x['batch']}, cycle {x['cycle']} ({x['lens']}), {x['phase']} phase: "
        f"\"{x['excerpt']}\"" for x in results)
    out = {"ok": True, "results": results, "block": block}
    if err or qv is None:
        out["note"] = f"embedding unavailable ({err or 'no key/HTTP error'}); exact-term match only"
    return out
