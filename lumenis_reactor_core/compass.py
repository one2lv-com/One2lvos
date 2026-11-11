"""
Flux Compass — The Anchor of Polarity
======================================
Prevents energy leakage (context drift) by keeping all state grounded
in a persistent local SQLite database. This is the "singular polarity"
anchor — every session traces back here.

Real implementation:
  - SQLite for durable memory (conversations, facts, sessions)
  - Per-session context windows
  - Fact extraction and recall
  - Toroidal logic: all queries flow through the compass and return enriched
"""

import sqlite3
import json
import time
import uuid
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "compass.db"


class FluxCompass:
    """
    The persistent state anchor. All memory flows through here.
    Think of it as the local filesystem root that keeps the AI grounded
    rather than floating stateless in the cloud.
    """

    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id          TEXT PRIMARY KEY,
                    created_at  REAL NOT NULL,
                    updated_at  REAL NOT NULL,
                    title       TEXT,
                    metadata    TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id          TEXT PRIMARY KEY,
                    session_id  TEXT NOT NULL,
                    role        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    seat        TEXT,
                    created_at  REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS facts (
                    id          TEXT PRIMARY KEY,
                    session_id  TEXT,
                    key         TEXT NOT NULL,
                    value       TEXT NOT NULL,
                    source      TEXT,
                    created_at  REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS objectives (
                    id          TEXT PRIMARY KEY,
                    title       TEXT NOT NULL,
                    description TEXT,
                    status      TEXT NOT NULL DEFAULT 'active',
                    priority    INTEGER NOT NULL DEFAULT 5,
                    created_at  REAL NOT NULL,
                    updated_at  REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_facts_key
                    ON facts(key);
            """)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(facts)")}
            if "confidence" not in cols:
                conn.execute("ALTER TABLE facts ADD COLUMN confidence REAL")
            if "verification" not in cols:
                conn.execute("ALTER TABLE facts ADD COLUMN verification TEXT")
            # Older rows: label by source so nothing old reads as verified.
            for src, (ver, conf) in self._SOURCE_VERIFICATION.items():
                conn.execute("UPDATE facts SET verification=?, confidence=? WHERE verification IS NULL AND source=?",
                             (ver, conf, src))
            conn.execute("UPDATE facts SET verification='unverified', confidence=0.5 WHERE verification IS NULL")

    def relabel_old_auto_facts(self) -> dict:
        """One-off cleanup: older auto-learned rows that are really dreams or plans/promises get
        verification 'dream' or 'plan', which keeps them out of recall_facts (nothing is deleted)."""
        out = {"dream": 0, "plan": 0}
        with self._connect() as conn:
            rows = conn.execute("SELECT id, key, value FROM facts WHERE source IN ('auto_learn','auto_insight') "
                                "AND verification='unverified'").fetchall()
            for r in rows:
                tag = "dream" if (self._DREAM_RE.search(r["value"]) or self._DREAM_RE.search(r["key"])) else (
                    "plan" if self._PLAN_RE.search(r["value"]) else None)
                if tag:
                    conn.execute("UPDATE facts SET verification=?, confidence=0.1 WHERE id=?", (tag, r["id"]))
                    out[tag] += 1
        return out

    # ── Sessions ──────────────────────────────────────────────────────────────

    def create_session(self, title: str = "Unnamed Session") -> str:
        sid = str(uuid.uuid4())
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?)",
                (sid, now, now, title, "{}"),
            )
        return sid

    def get_session(self, session_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_sessions(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Messages ──────────────────────────────────────────────────────────────

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        seat: Optional[str] = None,
    ) -> str:
        mid = str(uuid.uuid4())
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages VALUES (?,?,?,?,?,?)",
                (mid, session_id, role, content, seat, now),
            )
            conn.execute(
                "UPDATE sessions SET updated_at=? WHERE id=?",
                (now, session_id),
            )
        return mid

    def get_history(
        self, session_id: str, limit: int = 40
    ) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT role, content, seat, created_at
                   FROM messages WHERE session_id=?
                   ORDER BY created_at DESC LIMIT ?""",
                (session_id, limit),
            ).fetchall()
            # Return in chronological order for LLM context
            return [dict(r) for r in reversed(rows)]

    def get_llm_history(self, session_id: str, limit: int = 20) -> list[dict]:
        """Return message history in the format the LLM expects."""
        history = self.get_history(session_id, limit)
        return [
            {"role": m["role"], "content": m["content"]}
            for m in history
            if m["role"] in ("user", "assistant")
        ]

    # ── Facts (long-term memory) ──────────────────────────────────────────────

    # Verification status for every stored fact (Lumenis priority 1: facts carry
    # source, confidence, timestamp and verification status).
    #   tool_verified - written by a real check/tool result
    #   user_stated   - the user said it (true as a statement, not independently checked)
    #   unverified    - Lumenis's own words; never treat as confirmed
    _SOURCE_VERIFICATION = {
        "trigger_engine": ("tool_verified", 0.9), "tool_engine": ("tool_verified", 0.9),
        "user_stated": ("user_stated", 0.7), "api_facts": ("user_stated", 0.6),
        "ws_store_fact": ("user_stated", 0.6), "lumenis_tool": ("unverified", 0.5),
        "auto_learn": ("unverified", 0.3), "auto_insight": ("unverified", 0.3),
    }

    def store_fact(
        self,
        key: str,
        value: str,
        session_id: Optional[str] = None,
        source: Optional[str] = None,
        confidence: Optional[float] = None,
        verification: Optional[str] = None,
    ) -> str:
        fid = str(uuid.uuid4())
        dv, dc = self._SOURCE_VERIFICATION.get(source or "", ("unverified", 0.5))
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO facts (id, session_id, key, value, source, created_at, confidence, verification) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (fid, session_id, key, value, source, time.time(),
                 dc if confidence is None else float(confidence), verification or dv),
            )
        return fid

    def add_objective(self, title: str, description: str = "", status: str = "proposed", priority: int = 5) -> str:
        """Plans, promises and intentions go here, never into facts."""
        oid = f"obj_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO objectives (id,title,description,status,priority,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?)", (oid, title[:200], description[:1000], status, priority, now, now))
        return oid

    def recall_facts(self, query: str, limit: int = 5) -> list[dict]:
        """Simple keyword recall from the fact store."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT key, value, source, created_at, confidence, verification FROM facts
                   WHERE (key LIKE ? OR value LIKE ?)
                     AND COALESCE(verification,'') NOT IN ('plan', 'dream')
                   ORDER BY created_at DESC LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_facts(self, session_id: Optional[str] = None) -> list[dict]:
        with self._connect() as conn:
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM facts WHERE session_id=? ORDER BY created_at DESC",
                    (session_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM facts ORDER BY created_at DESC LIMIT 50"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        with self._connect() as conn:
            sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        return {
            "sessions": sessions,
            "messages": messages,
            "facts": facts,
            "db_path": str(self.db_path),
        }

    # ── Frontier #4: Autonomous Learning Loop ────────────────────────────────
    # Plans, promises and intentions: these go to objectives, never to facts.
    _PLAN_RE = __import__("re").compile(
        r"\b(i will|i'll|we will|we'll|i am going to|i'm going to|going to|will (?:now |soon )?(?:begin|start|run|"
        r"implement|audit|fix|build|deploy|create|add|review|investigate|monitor|track)|i plan|we plan|plan to|planned|"
        r"promise|commit to|intend|next step|todo|to-do|should|must|recommend|priority|roadmap|let's|let us|"
        r"i can (?:begin|start)|ready to)\b", __import__("re").I)
    # Dream material stays in the dream store only.
    _DREAM_RE = __import__("re").compile(
        r"\b(dream|dreamt|dreamed|dreaming|astral|vision i had|in the dream|reverie|clockwork bird)", __import__("re").I)

    def _route_learned(self, key: str, text: str, session_id) -> str:
        """Store one learned item in the right place. Returns 'fact', 'objective' or 'skipped'."""
        if self._DREAM_RE.search(text) or self._DREAM_RE.search(key):
            return "skipped"
        if self._PLAN_RE.search(text):
            self.add_objective(title=text[:120], status="proposed",
                               description=f"Auto-captured from Lumenis's reply (session {session_id}). "
                                           f"A plan or promise, NOT done or verified: {text[:600]}")
            return "objective"
        self.store_fact(key, text, session_id=session_id, source="auto_learn",
                        confidence=0.3, verification="unverified")
        return "fact"

    def auto_learn(self, response_text: str, session_id=None) -> int:
        """
        Extract insights from council responses.
        - plans / promises / intentions  -> objectives (status 'proposed')
        - dream material                 -> not stored here (dream store only)
        - everything else                -> facts with source 'auto_learn', confidence 0.3,
                                            verification 'unverified' (it is Lumenis's own words)
        Returns the number of items stored.
        """
        import re
        learned = 0
        patterns = [
            r'\*\*([^*]+)\*\*[:\s—–-]+([^\n]{20,200})',   # **Title**: description
            r'^\d+\.\s+\*\*([^*]+)\*\*[:\s—–-]+([^\n]{20,150})',  # 1. **Title**: desc
        ]
        for pat in patterns:
            for m in re.finditer(pat, response_text, re.MULTILINE):
                key = 'learn.' + re.sub(r'\s+', '_', m.group(1).strip().lower())[:40]
                val = m.group(2).strip()[:250]
                if not self.recall_facts(key):
                    if self._route_learned(key, val, session_id) != "skipped":
                        learned += 1
        action_words = ['must', 'should', 'critical', 'essential', 'recommend', 'next step', 'frontier']
        for sent in re.split(r'[.!?]\s+', response_text):
            if len(sent) > 40 and any(w in sent.lower() for w in action_words):
                key = 'insight.' + str(int(time.time()))[-6:]
                if not self.recall_facts(sent[:30]):
                    if self._route_learned(key, sent.strip()[:250], session_id) != "skipped":
                        learned += 1
                    if learned >= 5:  # cap per response
                        break
        return learned

    def get_learning_trajectory(self):
        """Return learning metrics for the autonomous loop."""
        with self._connect() as conn:
            total_facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
            auto_facts = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE source IN ('auto_learn','auto_insight')"
            ).fetchone()[0]
            recent = conn.execute(
                "SELECT key, value, created_at FROM facts ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
        return {
            "total_facts": total_facts,
            "auto_learned": auto_facts,
            "learning_ratio": round(auto_facts / max(1, total_facts), 2),
            "recent_insights": [dict(r) for r in recent],
        }
