"""MemoryCore: small JSON vector store for the orchestrator testbed.

Fixes over the original:
  * error replies are never stored (and old error records are dropped on load)
  * record ids are random UUIDs, so deletions can never cause collisions
  * vectors carry the embedding model + dimension; recall skips records from a
    different model instead of silently comparing mismatched vectors
  * writes are atomic
"""

import math
import re
import uuid

from . import config

MEMORY_FILE = "memory.json"  # data/memory.json, path owned by nimlab.store
_ERROR_RE = re.compile(r"\[(?:[A-Z ]+ )?ERROR\b[^\]]*\]", re.IGNORECASE)


def is_error_text(text):
    """True for failed replies like '[ERROR None]: ...' or '[VISION ERROR 500]: ...'."""
    if not isinstance(text, str):
        return True
    t = text.strip()
    if not t:
        return True
    if _ERROR_RE.match(t):
        return True
    # turn records look like 'User: ... | Assistant: <reply>'
    _, sep, reply = t.partition("| Assistant:")
    return bool(sep) and bool(_ERROR_RE.match(reply.strip()))


def cosine_similarity(v1, v2):
    if len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def new_id():
    return "mem_" + uuid.uuid4().hex


def clean_records(records):
    """Drop error records and give every record a safe unique id."""
    out, seen = [], set()
    for r in records or []:
        if not isinstance(r, dict) or is_error_text(r.get("text", "")) or not r.get("vector"):
            continue
        rid = r.get("id")
        if not isinstance(rid, str) or rid in seen:
            r = dict(r, id=new_id())
        seen.add(r["id"])
        out.append(r)
    return out


class MemoryCore:
    def __init__(self, client, embed_model, path=None, embed_fn=None):
        self.client = client
        self.embed_model = embed_model
        # embed_fn(text, input_type) -> vector or None; set when the embedding
        # role is backed by an MCP tool (embed_model is then "mcp:<tool>")
        self.embed_fn = embed_fn
        if path is None:
            from . import store
            path = store.path(store.MEMORY)
            store.ensure_all()
        self.path = path
        raw = config.load_json(self.path, []) or []
        self.memories = clean_records(raw)
        if len(self.memories) != len(raw) or any(a is not b for a, b in zip(self.memories, raw)):
            self.save()

    def save(self):
        config.save_json(self.path, self.memories)

    def embed(self, text, input_type):
        if self.embed_fn is not None:
            return self.embed_fn(text, input_type)
        if not self.embed_model:
            return None
        res = self.client.embed(self.embed_model, [text], input_type=input_type)
        if res.ok and res.data:
            return res.data[0]
        return None

    def store(self, text, metadata=None):
        """Returns the new record id, or None when nothing was stored."""
        if not text or not text.strip() or is_error_text(text):
            return None
        vec = self.embed(text, "passage")
        if not vec:
            return None
        record = {
            "id": new_id(),
            "timestamp": config.timestamp(),
            "text": text.strip(),
            "embed_model": self.embed_model,
            "dims": len(vec),
            "vector": vec,
            "metadata": metadata or {},
        }
        self.memories.append(record)
        self.save()
        return record["id"]

    def delete(self, record_id):
        before = len(self.memories)
        self.memories = [m for m in self.memories if m["id"] != record_id]
        if len(self.memories) != before:
            self.save()
            return True
        return False

    def recall(self, query, top_k=3, threshold=0.4):
        """[(similarity, text, timestamp, id)] best first."""
        if not self.memories:
            return []
        q = self.embed(query, "query")
        if not q:
            return []
        ranked = []
        for item in self.memories:
            model = item.get("embed_model")
            if (model and model != self.embed_model) or len(item["vector"]) != len(q):
                continue  # vectors from another embedding model are not comparable
            sim = cosine_similarity(q, item["vector"])
            if sim >= threshold:
                ranked.append((sim, item["text"], item["timestamp"], item["id"]))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked[:top_k]

    def recall_reranked(self, query, top_k=3, threshold=0.4, rerank_fn=None, candidates=10):
        """Embedding recall widened to `candidates` hits, then reordered by
        rerank_fn(query, [texts]) -> [(index, score)] best first, and cut to
        top_k. Returns (hits, info) where info says whether the rerank ran.
        Without rerank_fn (or when it fails) this is plain recall()."""
        if rerank_fn is None:
            return self.recall(query, top_k, threshold), {"reranked": False}
        pool = self.recall(query, max(top_k, int(candidates or top_k)), threshold)
        if len(pool) <= 1:
            return pool[:top_k], {"reranked": False, "reason": "nothing to rerank"}
        try:
            order = rerank_fn(query, [h[1] for h in pool])
        except Exception as e:  # a reranker failure falls back to cosine order
            order, err = None, str(e)
        else:
            err = None
        if not order:
            return pool[:top_k], {"reranked": False, "reason": err or "reranker returned nothing"}
        seen, out = set(), []
        for idx, _score in order:
            if 0 <= idx < len(pool) and idx not in seen:
                seen.add(idx)
                out.append(pool[idx])
        return out[:top_k], {"reranked": True, "pool": len(pool)}

    def incompatible_count(self):
        return sum(1 for m in self.memories if m.get("embed_model") not in (None, self.embed_model))
