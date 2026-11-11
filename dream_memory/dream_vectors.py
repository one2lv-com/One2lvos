"""
Lumenis dream vector memory (kept apart from factual memory).

Dreams live ONLY in the Astra DB collection `lumenis_dreams`. Nothing here
writes to factual stores (FluxCompass compass.db, Supabase `memories`,
Astra `aria_memory`, `agent_memory`, `lumenis_rag_*`, ...).

Every record carries record_class="dream", is_dream=True,
verified_fact=False and a plain-language label, so anything that reads a
dream back sees that it is imaginative material, not system fact.

Embeddings: NVIDIA nvidia/nemotron-3.5-embed-1b, 2048 dims, cosine.
(The configured EMBEDDING_MODEL nvidia/nv-embedqa-e5-v5 reached end of life
on the NVIDIA API on 2026-08-25 and returns HTTP 410, so it is not used, and
these 2048-dim vectors are not interchangeable with the older 1024-dim
collections.)
"""

import os
import time
from typing import Dict, List, Optional

import httpx

DREAM_COLLECTION = "lumenis_dreams"
DREAM_EMBED_MODEL = "nvidia/nemotron-3.5-embed-1b"
DREAM_EMBED_DIM = 2048
DREAM_LABEL = ("DREAM MATERIAL - imaginative text from a Lumenis dream cycle. "
               "Not a verified system fact, architecture record or log.")
DREAM_FILTER = {"record_class": "dream", "is_dream": True}


def _astra():
    ep = os.environ["ASTRA_DB_API_ENDPOINT"].rstrip("/")
    ks = os.environ.get("ASTRA_DB_KEYSPACE", "default_keyspace")
    tok = os.environ["ASTRA_DB_APPLICATION_TOKEN"]
    return ep, ks, {"Token": tok, "Content-Type": "application/json"}


def astra_cmd(cmd: Dict, collection: Optional[str] = DREAM_COLLECTION, timeout: int = 60) -> Dict:
    ep, ks, h = _astra()
    url = f"{ep}/api/json/v1/{ks}" + (f"/{collection}" if collection else "")
    r = httpx.post(url, headers=h, json=cmd, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(f"Astra error: {data['errors']}")
    return data


def embed(texts: List[str], input_type: str = "passage", retries: int = 8) -> List[List[float]]:
    key = os.environ["NVIDIA_API_KEY"]
    base = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
    payload = {"input": texts, "model": DREAM_EMBED_MODEL, "input_type": input_type,
               "encoding_format": "float", "truncate": "NONE"}
    last = None
    for attempt in range(retries):
        try:
            r = httpx.post(f"{base}/embeddings", headers={"Authorization": f"Bearer {key}"},
                           json=payload, timeout=120)
            if r.status_code == 200:
                vecs = [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]
                if len(vecs) != len(texts) or any(len(v) != DREAM_EMBED_DIM for v in vecs):
                    raise RuntimeError("unexpected embedding shape")
                return vecs
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:  # network / shape
            last = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"embedding failed: {last}")


def search_dreams(query: str, limit: int = 5, extra_filter: Optional[Dict] = None) -> List[Dict]:
    """Vector search over dream records only. Results keep their dream label."""
    qv = embed([query], input_type="query")[0]
    flt = dict(DREAM_FILTER)
    if extra_filter:
        flt.update(extra_filter)
    data = astra_cmd({"find": {"filter": flt, "sort": {"$vector": qv},
                               "options": {"limit": limit, "includeSimilarity": True},
                               "projection": {"$vector": 0, "seed_template_story": 0}}})
    out = []
    for d in data.get("data", {}).get("documents", []):
        d.setdefault("label", DREAM_LABEL)
        out.append(d)
    return out
