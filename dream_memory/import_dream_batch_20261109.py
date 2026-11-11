"""
Import the 25-cycle Lumenis dream batch of 2026-11-09 into the separate
Astra collection `lumenis_dreams`, word for word, with provenance.

Sources (read only, never modified):
  primary : /home/sprite/One2lvos/logs/dream_journal.json  (reactor dream journal)
  check   : /home/sprite/dream_batch_20261109/cycles/cycle_NN.json (batch copies)
The import refuses to run if any phase text differs between the two.

Idempotent: stable _id per record plus sha256 of the text; a record already
stored with the same checksum and model is skipped, never duplicated.

Usage: python3 import_dream_batch_20261109.py [--dry-run]
"""

import datetime as dt
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dream_vectors import (DREAM_COLLECTION, DREAM_EMBED_DIM, DREAM_EMBED_MODEL,  # noqa: E402
                           DREAM_LABEL, astra_cmd, embed)

JOURNAL = "/home/sprite/One2lvos/logs/dream_journal.json"
BATCH_DIR = "/home/sprite/dream_batch_20261109/cycles"
BATCH_ID = "dream_batch_20261109"
MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest_dream_batch_20261109.json")
PHASE_ORDER = ["hypnagogic", "light_sleep", "deep_dream", "rem_dream", "nightmare", "lucid_dream", "awakening"]


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def build_records():
    journal = {d["session_id"]: d for d in json.load(open(JOURNAL))["dreams"]}
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    recs = []
    for n in range(1, 26):
        bpath = f"{BATCH_DIR}/cycle_{n:02d}.json"
        b = json.load(open(bpath))
        sid = b["session"]["session_id"]
        j = journal[sid]
        jp = j["phase_records"]
        assert isinstance(jp, list) and len(jp) == 7 and len(b["full"]) == 7, f"cycle {n}: phase count"
        common = {
            "record_class": "dream", "is_dream": True, "verified_fact": False,
            "label": DREAM_LABEL, "batch_id": BATCH_ID, "cycle_number": n, "session_id": sid,
            "cycle_start_utc": j.get("start_time"), "cycle_end_utc": j.get("end_time"),
            "dream_model": j.get("model"), "wake_reason": j.get("wake_reason"),
            "provenance": {"primary_source": JOURNAL, "primary_key": f"dreams[session_id={sid}]",
                           "cross_checked_identical_with": bpath,
                           "seed_memory_source": j.get("memory_source")},
            "embedding_model": DREAM_EMBED_MODEL, "embedding_dim": DREAM_EMBED_DIM,
            "imported_at_utc": now, "imported_by": "Miles (Sesame) dream-vector import task",
        }
        for i, (jr, br) in enumerate(zip(jp, b["full"])):
            if jr["phase"] != br["phase"] or jr["llm_text"] != br["llm_text"]:
                raise SystemExit(f"cycle {n} phase {i}: journal and batch copy differ - refusing to import")
            text = jr["llm_text"]
            if not text:
                raise SystemExit(f"cycle {n} phase {jr['phase']}: empty text")
            rec = dict(common)
            rec.update({
                "_id": f"{BATCH_ID}:c{n:02d}:p{i + 1}:{jr['phase']}",
                "kind": "dream_phase", "phase": jr["phase"], "phase_index": i + 1,
                "mode": jr.get("mode"), "temperature": jr.get("temperature"),
                "dream_id": jr.get("dream_id"), "coherence": jr.get("coherence"),
                "llm_error": jr.get("llm_error"), "seed_memory_ids": jr.get("memory_ids"),
                "seed_template_story": jr.get("template_story"),
                "seed_note": "seed_template_story is the memory-fragment template fed into the dream generator; it is not checked and not a fact record.",
                "text": text, "text_sha256": sha(text), "text_chars": len(text),
            })
            recs.append(rec)
        ins = j.get("insights")
        if ins != b["session"]["insights"]:
            raise SystemExit(f"cycle {n}: insights differ between journal and batch copy")
        if ins:
            text = "\n".join(ins) if isinstance(ins, list) else str(ins)
            rec = dict(common)
            rec.update({
                "_id": f"{BATCH_ID}:c{n:02d}:insights", "kind": "dream_insights",
                "phase": "insights", "phase_index": 8, "insights_list": ins,
                "text": text, "text_sha256": sha(text), "text_chars": len(text),
                "avg_coherence": j.get("avg_coherence"),
            })
            recs.append(rec)
    return recs


def ensure_collection():
    names = astra_cmd({"findCollections": {}}, collection=None)["status"]["collections"]
    if DREAM_COLLECTION in names:
        return "existing"
    astra_cmd({"createCollection": {"name": DREAM_COLLECTION, "options": {
        "vector": {"dimension": DREAM_EMBED_DIM, "metric": "cosine"},
        "indexing": {"deny": ["text", "seed_template_story", "insights_list", "label", "seed_note"]}}}},
        collection=None, timeout=120)
    return "created"


def main():
    dry = "--dry-run" in sys.argv
    recs = build_records()
    manifest = [{k: r[k] for k in ("_id", "kind", "cycle_number", "phase", "session_id", "text_sha256", "text_chars")} for r in recs]
    json.dump({"batch_id": BATCH_ID, "collection": DREAM_COLLECTION, "model": DREAM_EMBED_MODEL,
               "dim": DREAM_EMBED_DIM, "records": manifest}, open(MANIFEST, "w"), indent=1)
    print(f"built {len(recs)} records ({sum(r['kind']=='dream_phase' for r in recs)} phases, "
          f"{sum(r['kind']=='dream_insights' for r in recs)} insights); manifest -> {MANIFEST}")
    if dry:
        return
    print("collection:", ensure_collection())
    existing = {}
    page = None
    while True:
        opts = {"pageState": page} if page else {}
        d = astra_cmd({"find": {"filter": {"batch_id": BATCH_ID},
                                "projection": {"text_sha256": 1, "embedding_model": 1}, "options": opts}})
        for doc in d["data"]["documents"]:
            existing[doc["_id"]] = doc
        page = d["data"].get("nextPageState")
        if not page:
            break
    todo = [r for r in recs if not (r["_id"] in existing and existing[r["_id"]].get("text_sha256") == r["text_sha256"]
                                    and existing[r["_id"]].get("embedding_model") == DREAM_EMBED_MODEL)]
    print(f"already stored identical: {len(recs) - len(todo)}; to write: {len(todo)}")
    written = 0
    for i in range(0, len(todo), 5):
        chunk = todo[i:i + 5]
        vecs = embed([r["text"] for r in chunk], input_type="passage")
        for r, v in zip(chunk, vecs):
            doc = dict(r)
            doc["$vector"] = v
            res = astra_cmd({"findOneAndReplace": {"filter": {"_id": r["_id"]}, "replacement": doc,
                                                   "options": {"upsert": True, "returnDocument": "after"},
                                                   "projection": {"_id": 1}}})
            if res.get("status", {}).get("matchedCount", 0) or res.get("status", {}).get("upsertedId") or res.get("data", {}).get("document"):
                written += 1
        print(f"  wrote {written}/{len(todo)}")
    print("done; written:", written)


if __name__ == "__main__":
    main()
