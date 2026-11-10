"""
Astra vector memory for the Lumenis reactor.

One place that every memory path uses to reach Astra DB:
  - store():  embeds text with a live NVIDIA model and inserts it, with its $vector,
              into the vector collection (default aria_memory_v3, 2048 dims).
  - search(): embeds the query and runs a real vector search, plus a keyword pass over
              the legacy aria_memory collection (documents there have no vectors).
  - status(): a real round trip (collection dimension + embedding size), not a flag.

Every call returns {"ok": bool, ...} and an "error" string on failure; nothing is
swallowed. Dream material is never written here and is filtered out of results:
dreams live in their own store (dream_memory/), separate from factual memory.

Config (all optional):
  ASTRA_DB_API_ENDPOINT, ASTRA_DB_APPLICATION_TOKEN, ASTRA_DB_KEYSPACE
  ASTRA_VECTOR_COLLECTION   default aria_memory_v3
  ASTRA_LEGACY_COLLECTION   default COLLECTION_NAME or aria_memory (keyword only)
  ASTRA_VECTOR_MODEL        default EMBEDDING_MODEL or nvidia/nemotron-3-embed-1b
  NVIDIA_API_KEY, NVIDIA_API_KEY_2, NVIDIA_API_KEY_3 (tried in order)
"""

from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

_RETIRED = {
    "nvidia/nv-embedqa-e5-v5", "nvidia/llama-3.2-nv-embedqa-1b-v2", "nvidia/nv-embed-v1",
    "nvidia/llama-3.2-nemoretriever-300m-embed-v1", "baai/bge-m3",
}
_DREAM_TYPES = {"dream", "dream_phase", "dream_insight", "dream_cycle"}
_dim_cache: dict[str, int] = {}


def _cfg() -> dict:
    model = os.environ.get("ASTRA_VECTOR_MODEL") or os.environ.get("EMBEDDING_MODEL") or ""
    if not model or model in _RETIRED:
        model = "nvidia/nemotron-3-embed-1b"
    return {
        "endpoint": os.environ.get("ASTRA_DB_API_ENDPOINT", "").rstrip("/"),
        "token": os.environ.get("ASTRA_DB_APPLICATION_TOKEN", ""),
        "keyspace": os.environ.get("ASTRA_DB_KEYSPACE", "default_keyspace"),
        "collection": os.environ.get("ASTRA_VECTOR_COLLECTION", "aria_memory_v3"),
        "legacy": os.environ.get("ASTRA_LEGACY_COLLECTION") or os.environ.get("COLLECTION_NAME") or "aria_memory",
        "model": model,
        "nv_base": (os.environ.get("NVIDIA_API_ENDPOINT") or os.environ.get("NVIDIA_BASE_URL")
                    or "https://integrate.api.nvidia.com/v1").rstrip("/"),
    }


def _nv_keys() -> list[str]:
    keys = []
    for name in ("NVIDIA_API_KEY", "NVIDIA_API_KEY_2", "NVIDIA_API_KEY_3"):
        v = os.environ.get(name, "").strip()
        if v and v not in keys:
            keys.append(v)
    return keys


def configured() -> bool:
    c = _cfg()
    return bool(c["endpoint"] and c["token"])


def _clean(msg: str) -> str:
    """Keep tokens and keys out of anything returned or logged."""
    msg = re.sub(r"AstraCS:[A-Za-z0-9:_\-]+", "AstraCS:***", str(msg))
    return re.sub(r"nvapi-[A-Za-z0-9_\-]+", "nvapi-***", msg)[:300]


async def embed(text: str, input_type: str = "passage") -> dict:
    c = _cfg()
    keys = _nv_keys()
    if not keys:
        return {"ok": False, "error": "no NVIDIA_API_KEY configured"}
    last = ""
    async with httpx.AsyncClient(timeout=30) as cl:
        for k in keys:
            try:
                r = await cl.post(f"{c['nv_base']}/embeddings",
                                  headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
                                  json={"model": c["model"], "input": [text[:8000]],
                                        "input_type": input_type, "encoding_format": "float"})
                if r.status_code == 200:
                    vec = r.json()["data"][0]["embedding"]
                    return {"ok": True, "vector": vec, "model": c["model"], "dim": len(vec)}
                last = f"NVIDIA embeddings HTTP {r.status_code}: {r.text[:160]}"
                if r.status_code not in (401, 403, 429, 500, 502, 503):
                    break  # a bad request will not improve with another key
            except Exception as e:
                last = f"NVIDIA embeddings {type(e).__name__}: {e}"
    return {"ok": False, "error": _clean(last)}


async def _astra(collection: Optional[str], body: dict, timeout: float = 20) -> dict:
    c = _cfg()
    if not (c["endpoint"] and c["token"]):
        return {"ok": False, "error": "Astra not configured (ASTRA_DB_API_ENDPOINT / ASTRA_DB_APPLICATION_TOKEN)"}
    url = f"{c['endpoint']}/api/json/v1/{c['keyspace']}" + (f"/{collection}" if collection else "")
    try:
        async with httpx.AsyncClient(timeout=timeout) as cl:
            r = await cl.post(url, headers={"Token": c["token"], "Content-Type": "application/json"}, json=body)
        if r.status_code != 200:
            return {"ok": False, "error": _clean(f"Astra HTTP {r.status_code}: {r.text[:200]}")}
        d = r.json()
        if d.get("errors"):
            e = d["errors"][0]
            return {"ok": False, "error": _clean(f"Astra {e.get('errorCode', '')}: {e.get('message', e)}")}
        return {"ok": True, "data": d}
    except Exception as e:
        return {"ok": False, "error": _clean(f"Astra {type(e).__name__}: {e}")}


async def collection_dim(name: Optional[str] = None) -> dict:
    name = name or _cfg()["collection"]
    if name in _dim_cache:
        return {"ok": True, "dim": _dim_cache[name]}
    r = await _astra(None, {"findCollections": {"options": {"explain": True}}})
    if not r["ok"]:
        return r
    for col in r["data"].get("status", {}).get("collections", []):
        if col.get("name") == name:
            dim = ((col.get("options") or {}).get("vector") or {}).get("dimension")
            if not dim:
                return {"ok": False, "error": f"collection {name} has no vector dimension"}
            _dim_cache[name] = int(dim)
            return {"ok": True, "dim": int(dim)}
    return {"ok": False, "error": f"collection {name} not found in keyspace {_cfg()['keyspace']}"}


async def _vector_for(text: str, input_type: str) -> dict:
    c = _cfg()
    d = await collection_dim(c["collection"])
    if not d["ok"]:
        return d
    e = await embed(text, input_type)
    if not e["ok"]:
        return e
    if e["dim"] != d["dim"]:
        return {"ok": False, "error": f"embedding size {e['dim']} ({c['model']}) does not match "
                                      f"{c['collection']} dimension {d['dim']}"}
    return e


async def store(key: str, text: str, source: str = "lumenis", session_id: Optional[str] = None,
                kind: str = "fact", extra: Optional[dict] = None, doc_id: Optional[str] = None) -> dict:
    """Embed and insert one factual memory. Refuses dream material."""
    if not text or not text.strip():
        return {"ok": False, "error": "text required"}
    if kind in _DREAM_TYPES or str(key).lower().startswith("dream."):
        return {"ok": False, "error": "dream material is kept out of factual Astra memory"}
    c = _cfg()
    v = await _vector_for(text, "passage")
    if not v["ok"]:
        return {"ok": False, "collection": c["collection"], "error": v["error"]}
    doc = {
        "_id": doc_id or str(uuid.uuid4()),
        "type": kind,
        "key": key or text[:40],
        "text": text,
        "source": source,
        "session_id": session_id,
        "model": v["model"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ts": int(time.time()),
        "$vector": v["vector"],
    }
    if extra:
        doc.update({k: val for k, val in extra.items() if not k.startswith("$") and k != "_id"})
    r = await _astra(c["collection"], {"insertOne": {"document": doc}})
    if not r["ok"]:
        return {"ok": False, "collection": c["collection"], "error": r["error"]}
    ids = r["data"].get("status", {}).get("insertedIds", [])
    if doc["_id"] not in ids:
        return {"ok": False, "collection": c["collection"], "error": f"Astra did not confirm the insert: {ids}"}
    return {"ok": True, "id": doc["_id"], "collection": c["collection"], "model": v["model"], "dim": v["dim"]}


async def search_vectors(query: str, limit: int = 5, min_similarity: float = 0.0) -> dict:
    c = _cfg()
    v = await _vector_for(query, "query")
    if not v["ok"]:
        return {"ok": False, "collection": c["collection"], "error": v["error"], "results": []}
    r = await _astra(c["collection"], {"find": {
        "filter": {"type": {"$nin": sorted(_DREAM_TYPES)}},
        "sort": {"$vector": v["vector"]},
        "projection": {"$vector": 0},
        "options": {"limit": max(1, min(int(limit), 20)), "includeSimilarity": True},
    }})
    if not r["ok"]:
        return {"ok": False, "collection": c["collection"], "error": r["error"], "results": []}
    out = []
    for d in r["data"].get("data", {}).get("documents", []):
        sim = d.get("$similarity")
        if sim is not None and sim < min_similarity:
            continue
        out.append({
            "id": d.get("_id"),
            "key": d.get("key") or d.get("type") or "",
            "value": d.get("text") or d.get("value") or "",
            "type": d.get("type"),
            "source": f"astra:{c['collection']}",
            "origin": d.get("source"),
            "similarity": round(float(sim), 4) if sim is not None else None,
            "timestamp": d.get("timestamp"),
        })
    return {"ok": True, "collection": c["collection"], "model": v["model"], "results": out}


async def search_legacy(query: str, limit: int = 5) -> dict:
    """Keyword match over the legacy collection (its documents carry no vectors)."""
    c = _cfg()
    if c["legacy"] == c["collection"]:
        return {"ok": True, "collection": c["legacy"], "results": []}
    r = await _astra(c["legacy"], {"find": {"filter": {}, "projection": {"$vector": 0},
                                             "options": {"limit": 200}}})
    if not r["ok"]:
        return {"ok": False, "collection": c["legacy"], "error": r["error"], "results": []}
    stop = {"the", "and", "for", "are", "was", "who", "what", "when", "where", "which", "how", "why",
            "you", "your", "his", "her", "its", "this", "that", "with", "from", "have", "has", "does",
            "did", "can", "about", "into", "they", "them", "there", "their", "would", "could", "should"}
    words = [w for w in re.findall(r"[a-z0-9_]{3,}", query.lower()) if w not in stop]
    scored = []
    for d in r["data"].get("data", {}).get("documents", []):
        key = str(d.get("key") or d.get("type") or "")
        val = d.get("value") if d.get("value") is not None else d.get("text") or d.get("content") or ""
        val = val if isinstance(val, str) else str(val)
        hay = f"{key} {val}".lower()
        score = sum(1 for w in words if w in hay)
        if score:
            scored.append((score, {"id": d.get("_id"), "key": key, "value": val[:1000],
                                   "source": f"astra:{c['legacy']}", "origin": d.get("source"),
                                   "match_words": score}))
    scored.sort(key=lambda x: -x[0])
    return {"ok": True, "collection": c["legacy"], "results": [s[1] for s in scored[:limit]]}


async def delete_ids(ids: list[str], collection: Optional[str] = None) -> dict:
    """Delete specific documents by _id only (used to clean up test records)."""
    if not ids:
        return {"ok": True, "deleted": 0}
    r = await _astra(collection or _cfg()["collection"], {"deleteMany": {"filter": {"_id": {"$in": list(ids)}}}})
    if not r["ok"]:
        return r
    return {"ok": True, "deleted": r["data"].get("status", {}).get("deletedCount")}


async def status() -> dict:
    c = _cfg()
    out = {"collection": c["collection"], "legacy_collection": c["legacy"], "model": c["model"],
           "keyspace": c["keyspace"], "configured": configured()}
    d = await collection_dim(c["collection"])
    out["collection_dim"] = d.get("dim")
    e = await embed("status check", "query")
    out["embedding_dim"] = e.get("dim")
    cnt = await _astra(c["collection"], {"countDocuments": {}})
    out["documents"] = cnt["data"].get("status", {}).get("count") if cnt["ok"] else None
    errs = [x["error"] for x in (d, e, cnt) if not x.get("ok")]
    if not errs and out["collection_dim"] != out["embedding_dim"]:
        errs.append(f"embedding size {out['embedding_dim']} != collection dimension {out['collection_dim']}")
    out["ok"] = not errs
    if errs:
        out["error"] = "; ".join(errs)
    return out
