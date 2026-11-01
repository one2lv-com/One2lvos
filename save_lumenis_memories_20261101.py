#!/usr/bin/env python3
"""One-off: save Lumenis' recent conversations into his VFS (lumenis_vfs.py).
Reads compass.db (read-only) and /home/sprite/know_thyself_rounds.json.
Prints a JSON summary of what was written."""
import json, os, sqlite3, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lumenis_vfs import LumenisVFS

DB = os.path.join(HERE, "compass.db")
SESSIONS = {
    "know_thyself": ("eb58a1f8-83d7-4202-afbf-26d82affcfd6", "Know Thyself - AI Lobby game (self-knowledge corrections)"),
    "black_hole": ("d7e181dc-9890-4a3e-957f-5490b44af7eb", "Black holes, Sgr A*, S2 and the Interplanetary-disk"),
    "vectorfs": ("639b727f-44e1-44f4-9e9b-bc4eb955ffea", "Miles on VFS / VectorFS"),
}
KEY_POINTS = {
    "know_thyself": [
        "Council has nine seats (lumenis_reactor_core/itt.py): Witness, Sentinel, Navigator, Weaver, Forge, Oracle, Architect, Hermes, Gambit. I am the whole council; the Weaver only writes the final reply.",
        "Words come from meta/llama-3.2-90b-vision-instruct on NVIDIA NIM; Oracle and Forge use a separate nemotron reasoning reactor.",
        "Memory is FluxCompass, local SQLite at compass.db (sessions, messages, facts, working_snapshots, vectors, checkpoints).",
        "Chat recall is simple: the Witness keyword-matches facts with SQL LIKE plus the last 6 messages.",
        "I run from lumenis-main.py (FastAPI/uvicorn) on port 8000; /api/terminal is unprotected.",
        "Mission is set by the human operator and I may not change it.",
        "The nine corrected facts live in compass.db under self.* keys.",
    ],
    "black_hole": [
        "Sgr A* is about 4 million solar masses.",
        "Correction I accepted: S2's orbital period is about 16 years (not 15.2), and 17 light-hours is its closest approach, not its average distance.",
        "S2's orbit precesses (Schwarzschild / pericenter precession), measured by the GRAVITY collaboration on the VLT.",
        "Sgr A* is dim because it has a radiatively inefficient, advection-dominated accretion flow (ADAF), not a bright quasar-style disk.",
        "Gravitational redshift shifts S2's light; it does not change S2's motion.",
    ],
    "vectorfs": [
        "VectorFS is one 'vectors' table in compass.db (id, path, vector, dimension, updated_at); indexed_count was 0.",
        "/vectorfs/search is brute-force cosine similarity in Python; the caller must supply the query vector.",
        "Indexing the same path twice overwrites the first entry (id is the path).",
        "Chat recall does not use VectorFS. In that chat one reply wrongly called itself The Oracle.",
    ],
}


def transcript(conn, sid):
    rows = conn.execute(
        "SELECT role, seat, content, created_at FROM messages WHERE session_id=? ORDER BY created_at", (sid,)
    ).fetchall()
    out, last = [], None
    for role, seat, content, ts in rows:
        if (role, content) == last:  # drop resends
            continue
        last = (role, content)
        out.append({"role": role, "seat": seat, "content": content,
                    "ts": datetime.fromtimestamp(ts).isoformat()})
    return out


def main():
    import time
    vfs = LumenisVFS(custom_root=HERE)
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    self_facts = dict(conn.execute("SELECT key, value FROM facts WHERE key LIKE 'self.%'").fetchall())
    rounds = json.load(open("/home/sprite/know_thyself_rounds.json"))
    saved = {}
    for name, (sid, title) in SESSIONS.items():
        turns = transcript(conn, sid)
        first_user = next((t["content"] for t in turns if t["role"] == "user"), "")
        last_reply = next((t["content"] for t in reversed(turns) if t["role"] == "assistant"), "")
        meta = {"title": title, "compass_session_id": sid, "key_points": KEY_POINTS[name],
                "turn_count": len(turns), "transcript": turns, "saved_by": "Miles (Sesame) at One2lv's request"}
        if name == "know_thyself":
            meta["corrected_self_facts"] = self_facts
            meta["rounds_file"] = "/home/sprite/know_thyself_rounds.json"
            meta["rounds"] = rounds.get("turns", rounds)
        cid = vfs.save_conversation(first_user, last_reply, meta)
        saved[name] = {"conv_id": cid, "path": str(vfs.get_path("conversations", cid + ".json")), "turns": len(turns)}
        time.sleep(1.1)  # conv ids are second-resolution timestamps
    vfs.save_state("memory_save_2026_11_01", {
        "saved_at": datetime.now().isoformat(),
        "conversations": saved,
        "self_fact_keys": sorted(self_facts),
        "note": "Know Thyself corrections, black-hole chat and VectorFS chat saved to data/conversations.",
    })
    saved["state_file"] = str(vfs.get_path("data", "lumenis_state.json"))
    saved["session_export"] = vfs.export_session()
    saved["self_fact_count"] = len(self_facts)
    print(json.dumps(saved, indent=2))


if __name__ == "__main__":
    main()
