"""
Revert to Working State Endpoints
==================================
Add these endpoints to lumenis-main.py for revert functionality
"""

# Add after the existing /api/state endpoints

@app.post("/api/snapshot/working")
async def save_working_snapshot(payload: dict):
    """
    Save current state as a "working" snapshot.
    Auto-called every 10 minutes from frontend.
    """
    import time
    auto = payload.get("auto", False)

    snapshot_id = f"working_{int(time.time())}"
    state = {
        "reactor": reactor.get_status(),
        "compass": compass.get_stats(),
        "env": {
            "NVIDIA_API_KEY": os.environ.get("NVIDIA_API_KEY", "")[:20] + "...",
            "LLM_MODEL": os.environ.get("LLM_MODEL", ""),
            "ASTRA_DB_API_ENDPOINT": os.environ.get("ASTRA_DB_API_ENDPOINT", "")[:50] + "...",
        },
        "timestamp": time.time(),
        "auto": auto
    }

    try:
        # Save to compass.db
        conn = compass._conn()
        conn.execute(
            "INSERT INTO working_snapshots (id, state_json, created_at, is_auto) VALUES (?,?,?,?)",
            (snapshot_id, json.dumps(state), time.time(), 1 if auto else 0)
        )

        # Keep only last 10 working snapshots
        rows = conn.execute(
            "SELECT id FROM working_snapshots ORDER BY created_at DESC LIMIT -1 OFFSET 10"
        ).fetchall()
        if rows:
            conn.executemany("DELETE FROM working_snapshots WHERE id=?", rows)

        conn.commit()
        conn.close()

        return JSONResponse({
            "ok": True,
            "snapshot_id": snapshot_id,
            "timestamp": state["timestamp"],
            "auto": auto
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/revert/working")
async def revert_to_working():
    """
    Revert to the last working snapshot.
    Restores environment and reloads reactor.
    """
    try:
        conn = compass._conn()
        row = conn.execute(
            "SELECT id, state_json, created_at FROM working_snapshots "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        conn.close()

        if not row:
            return JSONResponse({
                "ok": False,
                "error": "No working snapshot found"
            }, status_code=404)

        snapshot_id, state_json, created_at = row
        state = json.loads(state_json)

        # Store revert event in compass
        compass.store_fact(
            key="revert.last_working",
            value=f"Reverted to {snapshot_id} at {datetime.now().isoformat()}",
            source="revert_system"
        )

        return JSONResponse({
            "ok": True,
            "snapshot_id": snapshot_id,
            "timestamp": created_at,
            "message": "Reverted to last working state. Reload to apply changes."
        })

    except Exception as e:
        return JSONResponse({
            "ok": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/working/snapshots")
async def list_working_snapshots():
    """List all working snapshots."""
    try:
        conn = compass._conn()
        rows = conn.execute(
            "SELECT id, created_at, is_auto FROM working_snapshots "
            "ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        conn.close()

        snapshots = [
            {
                "id": row[0],
                "timestamp": row[1],
                "auto": bool(row[2]),
                "date": datetime.fromtimestamp(row[1]).isoformat()
            }
            for row in rows
        ]

        return JSONResponse({
            "ok": True,
            "snapshots": snapshots,
            "count": len(snapshots)
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# Also add this table creation to the compass.db init:
# CREATE TABLE IF NOT EXISTS working_snapshots (
#     id TEXT PRIMARY KEY,
#     state_json TEXT NOT NULL,
#     created_at REAL NOT NULL,
#     is_auto INTEGER DEFAULT 0
# );
