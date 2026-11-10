"""Live check of the tool engine against the real sfcompute server, through a throwaway FastAPI app
(the engine router only), so the running reactor is not touched. Read-only server calls only."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from lumenis_reactor_core import tool_engine as te  # noqa: E402

app = FastAPI()
app.include_router(te.router)
c = TestClient(app)
out = []


def show(label, r, keep=600):
    try:
        body = r.json()
    except Exception:
        body = r.text
    s = json.dumps(body, default=str)
    out.append((label, r.status_code))
    print(f"\n== {label}: HTTP {r.status_code}\n{s[:keep]}")
    return body


b = show("POST /engine/learn (real pull)", c.post("/engine/learn"), 900)
show("GET /engine/status", c.get("/engine/status"), 900)
show("GET /engine/tools/list_nodes (architecture from disk)", c.get("/engine/tools/list_nodes"), 1200)
show("POST /engine/call/sfcompute.list_nodes (real read)", c.post("/engine/call/sfcompute.list_nodes", json={}), 900)
show("same again (cache)", c.post("/engine/call/sfcompute.list_nodes", json={}), 300)
show("POST /engine/call/sfcompute.get_billing (real read)", c.post("/engine/call/sfcompute.get_billing", json={}), 900)
show("POST /engine/call/sfcompute.create_node (must be refused)", c.post("/engine/call/sfcompute.create_node", json={}), 500)
show("POST /engine/call/sfcompute.buy_credits (must be refused)", c.post("/engine/call/sfcompute.buy_credits", json={}), 500)
m = show("POST /engine/call/local.open_mission (∆| body)",
         c.post("/engine/call/local.open_mission", content="∆|title=Tool engine live check|goal=prove the engine runs".encode()), 500)
mid = (m.get("result") or {}).get("mission_id", "")
show("POST local.post_update", c.post("/engine/call/local.post_update", json={"mission_id": mid, "text": "live check ran"}), 400)
show("POST local.finish_mission", c.post("/engine/call/local.finish_mission", json={"mission_id": mid, "result": {"live_check": "passed"}}), 400)
show("POST local.query_metrics", c.post("/engine/call/local.query_metrics", json={}), 700)
show("GET /engine/tools?kind=local", c.get("/engine/tools?kind=local"), 300)
show("POST local.list_audit_events", c.post("/engine/call/local.list_audit_events", json={"limit": 5}), 700)
print("\nSUMMARY", out)
