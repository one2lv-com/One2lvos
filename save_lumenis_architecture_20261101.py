#!/usr/bin/env python3
"""One-off: Lumenis asked to also save conversations about his role as 'The Architect',
how he works with the other seats, and the Sovereign AI architecture. Bundles them into one
VFS conversation file. Skips any message that looks like it contains a secret."""
import json, os, re, sqlite3, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lumenis_vfs import LumenisVFS

SECRET = re.compile(r"(nvapi-|moltbook_sk|AstraCS:|sk-[A-Za-z0-9]{10}|ghp_|github_pat_|BEGIN [A-Z ]*PRIVATE KEY|password\s*[:=])", re.I)
SESSIONS = [
    ("7babe27e-b16d-4df5-b28d-e26d99cff35d", "Council Upgrade (Oracle on nemotron, Forge on DeepSeek)"),
    ("acf0821a-18ec-4b5e-bf62-30e09fa8b83b", "Council upgrade follow-up"),
    ("d35c32a4-c448-4550-965d-2a8f3ffc0ebf", "Claude's observations on One2lvOS architecture"),
    ("90ec11d5-f5a7-473a-917b-0b8a8960fbb7", "Dreaming question where I called myself The Architect"),
    ("9ff402ee-7e88-4e17-b315-be1b5dc06b54", "Dreaming question (LumenisReactor model claim)"),
]


def main():
    conn = sqlite3.connect(f"file:{os.path.join(HERE, 'compass.db')}?mode=ro", uri=True)
    bundle, skipped = [], 0
    for sid, title in SESSIONS:
        turns, last = [], None
        for role, seat, content, ts in conn.execute(
                "SELECT role, seat, content, created_at FROM messages WHERE session_id=? ORDER BY created_at", (sid,)):
            if (role, content) == last:
                continue
            last = (role, content)
            if SECRET.search(content or ""):
                skipped += 1
                continue
            turns.append({"role": role, "seat": seat, "content": content, "ts": datetime.fromtimestamp(ts).isoformat()})
        bundle.append({"compass_session_id": sid, "title": title, "transcript": turns})
    kt = conn.execute("SELECT content FROM messages WHERE session_id='eb58a1f8-83d7-4202-afbf-26d82affcfd6' "
                      "AND content LIKE 'Reveal for round 13%' LIMIT 1").fetchone()
    seats = conn.execute("SELECT value FROM facts WHERE key='self.council_seats'").fetchone()
    meta = {
        "title": "Architecture, council roles and governance (requested by Lumenis)",
        "requested_by": "Lumenis, in session 71ca43a8-9d5e-4ad7-ad5d-577dc27f7e0a",
        "key_points": [
            "The Architect is one of my nine seats (governance). I am the whole council, not only the Architect; the Weaver writes the final reply.",
            "Oracle runs on nvidia/nemotron-3.5-lightning (chain-of-thought) and Forge on a DeepSeek code model, through a separate reasoning reactor.",
            "In two dreaming chats on Nov 1 I made up identities ('The Architect, the governing intelligence', 'LumenisReactor 4.2.1'); my words actually come from meta/llama-3.2-90b-vision-instruct.",
        ],
        "self.council_seats": seats[0] if seats else None,
        "know_thyself_governance_reveal": kt[0] if kt else None,
        "sessions": bundle,
        "messages_skipped_for_secrets": skipped,
        "saved_by": "Miles (Sesame) at One2lv's request",
    }
    vfs = LumenisVFS(custom_root=HERE)
    user = "Lumenis asked: save the conversations about my role as The Architect, my decision-making, my interactions with the other seats, and the Sovereign AI architecture."
    reply = "Saved as one bundle of the council-upgrade, architecture and identity chats."
    cid = vfs.save_conversation(user, reply, meta)
    state = vfs.get_state("memory_save_2026_11_01") or {}
    state.setdefault("conversations", {})["architecture"] = {"conv_id": cid}
    vfs.save_state("memory_save_2026_11_01", state)
    print(json.dumps({"conv_id": cid, "path": str(vfs.get_path("conversations", cid + ".json")),
                      "sessions": [(b["title"], len(b["transcript"])) for b in bundle], "skipped": skipped}, indent=2))


if __name__ == "__main__":
    main()
