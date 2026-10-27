#!/usr/bin/env python3
"""
Initialize working_snapshots table in compass.db
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "compass.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create working_snapshots table
cursor.execute("""
CREATE TABLE IF NOT EXISTS working_snapshots (
    id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    is_auto INTEGER DEFAULT 0
)
""")

conn.commit()
conn.close()

print("✅ working_snapshots table created in compass.db")
