#!/usr/bin/env python3
"""Re-embed every document in the Astra vector collection with the current embedding model.

Why: nvidia/nemotron-3-embed-1b reached end of life on 2026-11-23 (HTTP 410), so the
28 stored vectors were made by a model that no longer exists and new query vectors come
from nvidia/nemotron-3.5-embed-1b. Vectors from two models are not comparable, so each
document's $vector is rebuilt from its own stored text.

Usage: .venv/bin/python reembed_astra_vectors.py [--dry-run]
Reads .env for ASTRA_* and NVIDIA_API_KEY. Prints counts only, never keys.
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _load_env():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def main(dry: bool) -> int:
    _load_env()
    from lumenis_reactor_core import astra_vectors as av
    c = av._cfg()
    docs, state = [], None
    while True:
        opts = {"pageState": state} if state else {}
        r = await av._astra(c["collection"], {"find": {"filter": {}, "projection": {"text": 1, "model": 1}, "options": opts}})
        if not r["ok"]:
            print("find failed:", r["error"])
            return 1
        data = r["data"].get("data", {})
        docs += data.get("documents", [])
        state = data.get("nextPageState")
        if not state:
            break
    print(f"{len(docs)} documents in {c['collection']}")
    done = skipped = failed = 0
    for d in docs:
        text = d.get("text") or ""
        if not text.strip():
            skipped += 1
            continue
        if dry:
            continue
        v = await av._vector_for(text, "passage")
        if not v["ok"]:
            failed += 1
            print("embed failed for", d["_id"], v["error"])
            continue
        u = await av._astra(c["collection"], {"updateOne": {"filter": {"_id": d["_id"]},
                                                             "update": {"$set": {"$vector": v["vector"], "model": v["model"]}}}})
        if u["ok"] and u["data"].get("status", {}).get("modifiedCount", 0) >= 0:
            done += 1
        else:
            failed += 1
            print("update failed for", d["_id"], u.get("error"))
    print(f"re-embedded={done} skipped_no_text={skipped} failed={failed} model={c['model']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--dry-run" in sys.argv)))
