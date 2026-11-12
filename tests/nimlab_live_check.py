"""Live check of the nimlab tools through the tool engine's real HTTP routes, without touching the running
reactor: mounts only the tool-engine router on 127.0.0.1:8011, loads the reactor's .env (values never
printed), makes a handful of small NVIDIA calls, writes tests/nimlab_live_results.json, then exits.
Run: .venv/bin/python3 tests/nimlab_live_check.py
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lumenis_reactor_core import tool_engine as te  # noqa: E402

PORT = int(os.getenv("NIMLAB_CHECK_PORT", "8011"))
app = FastAPI()
app.include_router(te.router)
srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
threading.Thread(target=srv.run, daemon=True).start()
for _ in range(50):
    if srv.started:
        break
    time.sleep(0.1)

B = f"http://127.0.0.1:{PORT}"
CHAT_MODEL = os.getenv("NIMLAB_CHECK_MODEL", "meta/llama-3.1-8b-instruct")
steps = [
    ("GET", "/engine/tools?kind=nimlab", None),
    ("GET", "/engine/tools/nimlab.rank", None),
    ("POST", "/engine/call/nimlab.status", {}),
    ("POST", "/engine/call/nimlab.list_models", {"list": "verified", "limit": 3}),
    ("POST", "/engine/call/nimlab.route", {"model": CHAT_MODEL}),
    ("POST", "/engine/call/nimlab.key_models", {"q": "nemotron", "limit": 5}),
    ("POST", "/engine/call/nimlab.probe", {"model": CHAT_MODEL}),
    ("POST", "/engine/call/nimlab.chat", {"model": CHAT_MODEL, "prompt": "In five words, what is a reactor core?",
                                         "max_tokens": 24, "temperature": 0.2}),
    ("POST", "/engine/call/nimlab.embed", {"model": "nvidia/nv-embedqa-e5-v5", "texts": ["Lumenis"], "input_type": "query"}),
    ("POST", "/engine/call/nimlab.tts", {"text": "Lumenis online.", "voice": "Magpie-Multilingual.EN-US.Aria"}),
    ("POST", "/engine/call/nimlab.sweep", {}),
    ("POST", "/engine/call/nimlab.chat", {"model": CHAT_MODEL}),
]
key_vals = [v for k, v in os.environ.items() if "KEY" in k or "TOKEN" in k or "SECRET" in k]
out = []
with httpx.Client(timeout=180) as c:
    for method, path, body in steps:
        t0 = time.time()
        r = c.request(method, B + path, json=body) if method == "POST" else c.get(B + path)
        j = r.json()
        text = json.dumps(j)
        leaked = any(v and len(v) > 12 and v in text for v in key_vals)
        res = j.get("result", j) if isinstance(j, dict) else j
        brief = {"call": f"{method} {path}", "http": r.status_code, "seconds": round(time.time() - t0, 2),
                 "ok": j.get("ok", r.status_code == 200) if isinstance(j, dict) else None, "secret_in_reply": leaked}
        if isinstance(res, dict):
            for k in ("count", "text", "status", "latency_s", "http_requests", "hosts", "answered", "dims", "bytes",
                      "duration_s", "file", "artifact", "key", "error", "models", "level", "route", "verified"):
                if k in res:
                    brief[k] = res[k]
            if "stores" in res:
                brief["stores"] = {k: res["stores"].get(k) for k in ("endpoints", "discovered", "verified", "failed", "untested")}
            if "tools" in res and isinstance(res["tools"], list):
                brief["tools"] = [t["name"] for t in res["tools"]]
        if isinstance(j, dict) and not j.get("ok", True):
            brief["error"] = j.get("error")
        out.append(brief)
        print(json.dumps(brief)[:400])
(ROOT / "tests" / "nimlab_live_results.json").write_text(json.dumps(
    {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "port": PORT, "results": out}, indent=1))
srv.should_exit = True
time.sleep(0.5)
