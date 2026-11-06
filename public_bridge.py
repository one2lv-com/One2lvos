#!/usr/bin/env python3
"""One2lvOS public bridge: the only door from the public IONOS site to the real Lumenis backend.

Runs on 127.0.0.1:8095 and is published through the existing Cloudflare tunnel as
https://bridge.one2lv.com.  It exposes a short, fixed allow-list of read/ask endpoints.
There is NO shell, NO file access, NO state load, NO outbound fetch and NO secret ever
leaves this process.  Every data endpoint needs a bearer token obtained by signing in
with the existing One2lvOS AI Lobby admin login (ai-lobby/data/config.json); the password
is compared server-side in constant time and never stored by the browser.
"""
import asyncio, hmac, json, os, secrets, time
from collections import defaultdict, deque

import httpx
import websockets
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = os.path.dirname(os.path.abspath(__file__))
REACTOR = os.environ.get("O2_REACTOR", "http://127.0.0.1:8000")
REACTOR_WS = REACTOR.replace("http", "ws", 1) + "/ws"
LOBBY = os.environ.get("O2_LOBBY", "http://127.0.0.1:8006")
CONFIG = os.path.join(ROOT, "ai-lobby", "data", "config.json")
TOKENS_FILE = os.path.join(ROOT, "data", "bridge_tokens.json")
TOKEN_TTL = 12 * 3600
ALLOWED_ORIGINS = [
    "http://s1086212999.onlinehome.us",
    "https://s1086212999.onlinehome.us",
]

app = FastAPI(title="One2lvOS public bridge", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

_client = httpx.AsyncClient(timeout=30.0)
_fails = defaultdict(deque)          # ip -> failure timestamps
_rate = defaultdict(deque)           # token -> request timestamps (council)


def _load_tokens():
    try:
        with open(TOKENS_FILE) as f:
            t = json.load(f)
        now = time.time()
        return {k: v for k, v in t.items() if v.get("exp", 0) > now}
    except Exception:
        return {}


_tokens = _load_tokens()


def _save_tokens():
    os.makedirs(os.path.dirname(TOKENS_FILE), exist_ok=True)
    tmp = TOKENS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_tokens, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKENS_FILE)


def _admin():
    with open(CONFIG) as f:
        a = json.load(f)["admin"]
    return str(a["username"]), str(a["password"])


def _ip(req: Request):
    return req.headers.get("cf-connecting-ip") or (req.client.host if req.client else "?")


def _auth(req: Request):
    h = req.headers.get("authorization", "")
    tok = h[7:].strip() if h.lower().startswith("bearer ") else ""
    info = _tokens.get(tok)
    if not tok or not info or info["exp"] < time.time():
        raise HTTPException(401, "sign in required")
    return tok, info


async def _get(url, **kw):
    try:
        r = await _client.get(url, **kw)
    except Exception as e:
        raise HTTPException(502, f"backend unreachable: {type(e).__name__}")
    if r.status_code >= 400:
        raise HTTPException(502, f"backend returned HTTP {r.status_code}")
    return r.json()


async def _post(url, body):
    try:
        r = await _client.post(url, json=body)
    except Exception as e:
        raise HTTPException(502, f"backend unreachable: {type(e).__name__}")
    if r.status_code >= 400:
        raise HTTPException(502, f"backend returned HTTP {r.status_code}")
    return r.json()


# ── Public ──────────────────────────────────────────────────────────────────
@app.get("/v1/health")
async def health():
    up = True
    try:
        r = await _client.get(REACTOR + "/api/status", timeout=5)
        up = r.status_code < 500
    except Exception:
        up = False
    return {"bridge": "ok", "reactor_up": up, "auth": "bearer (AI Lobby admin login)"}


@app.post("/v1/login")
async def login(req: Request):
    ip = _ip(req)
    q = _fails[ip]
    now = time.time()
    while q and q[0] < now - 600:
        q.popleft()
    if len(q) >= 5:
        raise HTTPException(429, "too many failed sign-ins, wait 10 minutes")
    try:
        body = await req.json()
    except Exception:
        body = {}
    u, p = str(body.get("username", "")), str(body.get("password", ""))
    au, ap = _admin()
    ok = hmac.compare_digest(u.encode(), au.encode()) & hmac.compare_digest(p.encode(), ap.encode())
    if not ok:
        q.append(now)
        await asyncio.sleep(1.0)
        raise HTTPException(401, "wrong username or password")
    tok = secrets.token_urlsafe(32)
    _tokens[tok] = {"user": au, "exp": now + TOKEN_TTL, "ip": ip}
    _save_tokens()
    return {"token": tok, "user": au, "expires_in": TOKEN_TTL}


@app.post("/v1/logout")
async def logout(req: Request):
    tok, _ = _auth(req)
    _tokens.pop(tok, None)
    _save_tokens()
    return {"ok": True}


# ── Signed-in: read the real backend ─────────────────────────────────────────
@app.get("/v1/whoami")
async def whoami(req: Request):
    _, info = _auth(req)
    return {"user": info["user"], "expires_at": int(info["exp"])}


@app.get("/v1/status")
async def status(req: Request):
    _auth(req)
    s = await _get(REACTOR + "/api/status")
    r, c, n = s.get("reactor", {}), s.get("compass", {}), s.get("nodes", {})
    return {
        "source": "lumenis reactor /api/status",
        "reactor": {k: r.get(k) for k in ("temperature", "pulse_count", "uptime_seconds", "frequency_hz", "node_lattice_size", "model", "provider", "tokens_streamed")},
        "nvidia_online": (s.get("nvidia") or {}).get("online"),
        "compass": {k: c.get(k) for k in ("sessions", "messages", "facts")},
        "nodes": {k: n.get(k) for k in ("active_workers", "max_concurrent", "total_processed", "total_errors", "queue_depth")},
    }


@app.get("/v1/learning")
async def learning(req: Request):
    _auth(req)
    return await _get(REACTOR + "/api/learning")


@app.get("/v1/registry")
async def registry(req: Request, q: str = "", limit: int = 10):
    """Registry of Thought = Lumenis' learned facts (compass.db), optionally searched."""
    _auth(req)
    limit = max(1, min(int(limit), 25))
    if q.strip():
        res = await _post(REACTOR + "/api/tools/memory/search", {"query": q[:200], "limit": limit})
        return {"source": "memory.search", "query": q[:200], "result": res}
    lr = await _get(REACTOR + "/api/learning")
    return {"source": "api/learning", "total_facts": lr.get("total_facts"), "auto_learned": lr.get("auto_learned"),
            "recent": (lr.get("recent_insights") or [])[:limit]}


@app.get("/v1/modules")
async def modules(req: Request):
    _auth(req)
    s = await _get(REACTOR + "/api/webos/services")
    return {"source": "api/webos/services", "services": [
        {k: x.get(k) for k in ("id", "name", "port", "up", "http", "ms", "desc")} for x in s.get("services", [])]}


@app.get("/v1/tasks")
async def tasks(req: Request):
    _auth(req)
    t = await _get(REACTOR + "/api/tasks")
    return {"source": "api/tasks", "count": len(t), "tasks": t[-25:]}


@app.get("/v1/models")
async def models(req: Request):
    _auth(req)
    return await _get(REACTOR + "/api/models")


@app.get("/v1/lobby/agents")
async def lobby_agents(req: Request):
    _auth(req)
    return await _get(LOBBY + "/agents")


@app.get("/v1/lobby/messages")
async def lobby_messages(req: Request, limit: int = 30):
    _auth(req)
    return await _get(LOBBY + "/messages", params={"limit": max(1, min(int(limit), 100))})


@app.post("/v1/lobby/broadcast")
async def lobby_broadcast(req: Request):
    _, info = _auth(req)
    body = await req.json()
    content = str(body.get("content", "")).strip()[:2000]
    if not content:
        raise HTTPException(400, "content is empty")
    return await _post(LOBBY + "/broadcast", {"from": f"web:{info['user']}", "content": content, "meta": {"via": "ionos-bridge"}})


# ── Signed-in: ask the real ITT council (Lumenis chat over /ws) ───────────────
_jobs = {}  # job_id -> {"owner": token, "done": bool, "result": dict, "status": int, "t": time}


@app.post("/v1/council/jobs")
async def council_job(req: Request):
    """Start a council question in the background (Cloudflare cuts requests at 100 s)."""
    tok, _ = _auth(req)
    body = await req.json()
    now = time.time()
    for k in [k for k, v in _jobs.items() if v["t"] < now - 3600]:
        _jobs.pop(k, None)
    jid = secrets.token_urlsafe(12)
    _jobs[jid] = {"owner": tok, "done": False, "result": None, "status": 202, "t": now}

    async def run():
        try:
            r = await _council_run(tok, body)
            st, res = (200, r) if not isinstance(r, JSONResponse) else (r.status_code, json.loads(r.body))
        except HTTPException as e:
            st, res = e.status_code, {"ok": False, "error": e.detail}
        except Exception as e:
            st, res = 500, {"ok": False, "error": f"bridge error: {type(e).__name__}"}
        _jobs[jid].update(done=True, result=res, status=st)

    asyncio.create_task(run())
    return {"job_id": jid, "poll": f"/v1/council/jobs/{jid}"}


@app.get("/v1/council/jobs/{jid}")
async def council_job_get(jid: str, req: Request):
    tok, _ = _auth(req)
    j = _jobs.get(jid)
    if not j or j["owner"] != tok:
        raise HTTPException(404, "no such council job")
    if not j["done"]:
        return {"done": False, "elapsed_s": int(time.time() - j["t"])}
    return JSONResponse({"done": True, **j["result"]}, status_code=j["status"])


@app.post("/v1/council")
async def council(req: Request):
    tok, _ = _auth(req)
    return await _council_run(tok, await req.json())


async def _council_run(tok, body):
    q = _rate[tok]
    now = time.time()
    while q and q[0] < now - 600:
        q.popleft()
    if len(q) >= 20:
        raise HTTPException(429, "council limit: 20 questions per 10 minutes")
    q.append(now)
    msg = str(body.get("query", "")).strip()[:4000]
    if not msg:
        raise HTTPException(400, "query is empty")
    session = body.get("session_id") or None
    reply, seats, meta, err = [], [], None, None
    try:
        async with websockets.connect(REACTOR_WS, max_size=None, ping_interval=20) as ws:
            await ws.send(json.dumps({"action": "chat", "message": msg, "session_id": session}))
            deadline = time.time() + 320
            while True:
                left = deadline - time.time()
                if left <= 0:
                    err = "council gave no final answer within 320 s"
                    break
                m = json.loads(await asyncio.wait_for(ws.recv(), timeout=left))
                t = m.get("type")
                if t == "ping":
                    await ws.send(json.dumps({"action": "ping"}))
                elif t == "session_created":
                    session = m.get("session_id", session)
                elif t == "response_chunk":
                    reply.append(m.get("text", ""))
                elif t == "seat_activity":
                    seats.append({"seat": m.get("seat"), "text": m.get("text", "")})
                elif t == "error":
                    err = str(m.get("message"))
                    break
                elif t == "processing_done":
                    session = m.get("session_id", session)
                    meta = m.get("meta")
                    break
    except asyncio.TimeoutError:
        err = "council gave no final answer within 320 s"
    except Exception as e:
        err = f"reactor websocket failed: {type(e).__name__}"
    if err is not None and not err:
        last = seats[-1]["seat"] if seats else "council"
        err = f"the reactor reported an error with no message during the {last} step (most likely a model timeout)"
    if err is not None and not reply:
        return {"ok": False, "error": err, "seats": seats, "session_id": session}
    if not reply and meta is None:
        return {"ok": False, "error": "the council finished without an answer", "seats": seats, "session_id": session}
    return {"ok": True, "source": "lumenis reactor /ws (ITT council)", "reply": "".join(reply),
            "seats": seats, "meta": meta, "session_id": session, "warning": err}


@app.get("/")
async def root():
    return {"service": "One2lvOS public bridge", "health": "/v1/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("O2_BRIDGE_PORT", "8095")), log_level="info")
