"""
Local, separate vector store for Lumenis dream records.

File: One2lvos/dream_memory/lumenis_dreams_vectors.db (SQLite), its own file,
never compass.db or any factual store. Table `dreams` only accepts rows labelled
as dreams (CHECK constraints). Vectors: nvidia/nemotron-3.5-embed-1b, 2048-dim
float32, cosine search done in Python over dream rows only.

Usage:
  python3 local_dream_store.py import      # idempotent import of the 2026-11-09 batch
  python3 local_dream_store.py search "query" [k]
  python3 local_dream_store.py verify
"""

import json
import math
import os
import sqlite3
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dream_vectors import DREAM_EMBED_DIM, DREAM_EMBED_MODEL, DREAM_LABEL, embed  # noqa: E402
import import_dream_batch_20261109 as batch  # noqa: E402

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lumenis_dreams_vectors.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS dreams (
  id TEXT PRIMARY KEY,
  record_class TEXT NOT NULL DEFAULT 'dream' CHECK (record_class = 'dream'),
  is_dream INTEGER NOT NULL DEFAULT 1 CHECK (is_dream = 1),
  verified_fact INTEGER NOT NULL DEFAULT 0 CHECK (verified_fact = 0),
  label TEXT NOT NULL,
  batch_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  cycle_number INTEGER NOT NULL,
  phase TEXT NOT NULL,
  phase_index INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  text TEXT NOT NULL,
  text_sha256 TEXT NOT NULL,
  text_chars INTEGER NOT NULL,
  metadata TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_dim INTEGER NOT NULL,
  embedding BLOB NOT NULL,
  imported_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dreams_batch ON dreams(batch_id, cycle_number, phase_index);
"""

META_KEYS = ("cycle_start_utc", "cycle_end_utc", "dream_model", "wake_reason", "provenance", "mode",
             "temperature", "dream_id", "coherence", "llm_error", "seed_memory_ids", "seed_template_story",
             "seed_note", "insights_list", "avg_coherence", "imported_by")


def conn():
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    return c


def pack(v):
    return struct.pack(f"{len(v)}f", *v)


def unpack(b):
    return struct.unpack(f"{len(b) // 4}f", b)


def do_import():
    recs = batch.build_records()
    c = conn()
    have = {r[0]: (r[1], r[2]) for r in c.execute("SELECT id, text_sha256, embedding_model FROM dreams")}
    todo = [r for r in recs if have.get(r["_id"]) != (r["text_sha256"], DREAM_EMBED_MODEL)]
    print(f"records {len(recs)}; already stored identical {len(recs) - len(todo)}; to write {len(todo)}")
    failed = []
    for i in range(0, len(todo), 5):
        chunk = todo[i:i + 5]
        pairs = []
        for r in chunk:
            try:
                pairs.append((r, embed([r["text"]], input_type="passage")[0]))
            except Exception as e:
                failed.append(r["_id"])
                print("  embed failed:", r["_id"], str(e)[:120])
        for r, v in pairs:
            meta = {k: r.get(k) for k in META_KEYS if k in r}
            c.execute("""INSERT OR REPLACE INTO dreams (id,label,batch_id,kind,cycle_number,phase,phase_index,
                         session_id,text,text_sha256,text_chars,metadata,embedding_model,embedding_dim,embedding,imported_at)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (r["_id"], DREAM_LABEL, r["batch_id"], r["kind"], r["cycle_number"], r["phase"],
                       r["phase_index"], r["session_id"], r["text"], r["text_sha256"], r["text_chars"],
                       json.dumps(meta, ensure_ascii=False), DREAM_EMBED_MODEL, len(v), pack(v), r["imported_at_utc"]))
        c.commit()
        print(f"  processed {min(i + 5, len(todo))}/{len(todo)}")
    c.close()
    print("failed:", len(failed), failed)


def search(query, k=5):
    q = embed([query], input_type="query")[0]
    qn = math.sqrt(sum(x * x for x in q))
    c = conn()
    out = []
    for rid, cyc, ph, text, blob in c.execute(
            "SELECT id, cycle_number, phase, text, embedding FROM dreams WHERE record_class='dream' AND is_dream=1"):
        v = unpack(blob)
        s = sum(a * b for a, b in zip(q, v)) / (qn * math.sqrt(sum(x * x for x in v)))
        out.append((s, rid, cyc, ph, text))
    c.close()
    out.sort(reverse=True)
    return [{"similarity": round(s, 4), "id": rid, "cycle": cyc, "phase": ph, "label": DREAM_LABEL,
             "text": t} for s, rid, cyc, ph, t in out[:k]]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "import":
        do_import()
    elif cmd == "search":
        for r in search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 5):
            print(r["similarity"], r["id"], r["text"][:160].replace("\n", " "))
