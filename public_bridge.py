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
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
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
    "https://one2lvos.vercel.app",      # Vercel-hosted One2lvOS desktop
    "https://localhost",                # One2lvOS Desktop APK (Capacitor Android WebView)
    "http://localhost",
    "capacitor://localhost",
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


def _auth(req: Request, guest_ok: bool = False):
    h = req.headers.get("authorization", "")
    tok = h[7:].strip() if h.lower().startswith("bearer ") else ""
    info = _tokens.get(tok)
    if not tok or not info or info["exp"] < time.time():
        raise HTTPException(401, "sign in required")
    if info.get("scope", "admin") != "admin" and not guest_ok:
        raise HTTPException(403, "guest access only covers chatting with Lumenis")
    return tok, info


# ── Guest (shared app) access ───────────────────────────────────────────────────────────────
# An app key (stored here only as a SHA-256 hash) lets a shared copy of the One2lvOS app
# get a chat-only guest token.  Guest tokens can ONLY use the live chat socket, and the
# reactor runs their messages in guest mode: no Hermes/external services (Gmail, Drive...),
# no shared folder, no tool engine, no IONOS checks, no auto-learning into his facts.
# Revoke a key by setting "revoked": true in data/bridge_app_keys.json (read on every login).
APP_KEYS_FILE = os.path.join(ROOT, "data", "bridge_app_keys.json")
GUEST_TTL = 30 * 24 * 3600
_guest_ip = defaultdict(deque)     # ip -> guest chat timestamps
_guest_all = deque()               # all guest chat timestamps
_logins_ip = defaultdict(deque)    # ip -> guest token issues
_guest_ok_cache = {"t": 0.0, "ok": False}


def _app_keys():
    try:
        with open(APP_KEYS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _trim(q, window, now):
    while q and q[0] < now - window:
        q.popleft()


async def _reactor_guest_ready():
    now = time.time()
    if now - _guest_ok_cache["t"] < 60:
        return _guest_ok_cache["ok"]
    ok = False
    try:
        r = await _client.get(REACTOR + "/api/guest_mode", timeout=5)
        ok = r.status_code == 200 and r.json().get("supported") is True
    except Exception:
        ok = False
    _guest_ok_cache.update(t=now, ok=ok)
    return ok


@app.post("/v1/app-login")
async def app_login(req: Request):
    import hashlib
    ip = _ip(req)
    now = time.time()
    q = _fails[ip]
    _trim(q, 600, now)
    if len(q) >= 5:
        raise HTTPException(429, "too many failed sign-ins, wait 10 minutes")
    try:
        body = await req.json()
    except Exception:
        body = {}
    key = str(body.get("app_key", "")).strip()
    entry = _app_keys().get(hashlib.sha256(key.encode()).hexdigest()) if key else None
    if not entry or entry.get("revoked"):
        q.append(now)
        await asyncio.sleep(1.0)
        raise HTTPException(401, "this app's access key is not valid any more")
    lq = _logins_ip[ip]
    _trim(lq, 3600, now)
    if len(lq) >= 20:
        raise HTTPException(429, "too many new guest sign-ins from this network, try again later")
    lq.append(now)
    device = str(body.get("device", ""))[:40] or "guest"
    tok = secrets.token_urlsafe(32)
    _tokens[tok] = {"user": f"guest:{device}", "scope": "guest", "app": entry.get("name", "app"),
                    "exp": now + GUEST_TTL, "ip": ip, "sessions": []}
    _save_tokens()
    return {"token": tok, "user": f"guest:{device}", "scope": "guest", "expires_in": GUEST_TTL}


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
    tok, _ = _auth(req, guest_ok=True)
    _tokens.pop(tok, None)
    _save_tokens()
    return {"ok": True}


# ── Signed-in: read the real backend ─────────────────────────────────────────
@app.get("/v1/whoami")
async def whoami(req: Request):
    _, info = _auth(req, guest_ok=True)
    return {"user": info["user"], "scope": info.get("scope", "admin"), "expires_at": int(info["exp"])}


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
        async with websockets.connect(REACTOR_WS, max_size=None, ping_interval=None, open_timeout=15) as ws:
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


# ── Signed-in: live Lumenis chat, streamed over a WebSocket ─────────────────
# wss://bridge.one2lv.com/v1/live
# 1. client sends {"action":"auth","token":"<bearer token from /v1/login>"} within 15 s
# 2. client sends {"action":"chat","message":"...","session_id":<id or null>}
# 3. bridge relays only the council's chat events from the reactor in real time:
#    session_created, processing_start, seat_activity, response_chunk, processing_done, error
# Nothing else from the reactor socket (recall/store_fact/state) is reachable through here.
_LIVE_TYPES = {"session_created", "processing_start", "seat_activity", "response_chunk", "processing_done", "error"}


@app.websocket("/v1/live")
async def live(ws: WebSocket):
    origin = ws.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        await ws.close(code=4403)
        return
    await ws.accept()
    try:
        first = json.loads(await asyncio.wait_for(ws.receive_text(), timeout=15))
    except Exception:
        await ws.close(code=4401)
        return
    tok = str(first.get("token", "")) if first.get("action") == "auth" else ""
    info = _tokens.get(tok)
    if not tok or not info or info["exp"] < time.time():
        await ws.send_json({"type": "auth_failed", "message": "sign in required"})
        await ws.close(code=4401)
        return
    guest = info.get("scope", "admin") != "admin"
    await ws.send_json({"type": "ready", "user": info["user"], "scope": "guest" if guest else "owner",
                        "source": "lumenis reactor /ws (ITT council)"})

    busy = False

    async def relay(body):
        nonlocal busy
        msg = str(body.get("message", "")).strip()[:4000]
        session = body.get("session_id") or None
        if guest and session not in info.get("sessions", []):
            session = None  # guests only continue their own conversations
        try:
            async with websockets.connect(REACTOR_WS, max_size=None, ping_interval=None, open_timeout=15) as rws:
                out = {"action": "chat", "message": msg, "session_id": session}
                if guest:
                    out["guest"] = True
                    out["guest_name"] = info["user"]
                await rws.send(json.dumps(out))
                deadline = time.time() + 320
                while True:
                    left = deadline - time.time()
                    if left <= 0:
                        await ws.send_json({"type": "error", "message": "council gave no final answer within 320 s"})
                        break
                    try:
                        raw = await asyncio.wait_for(rws.recv(), timeout=min(left, 15))
                    except asyncio.TimeoutError:
                        # keep the public socket (Cloudflare, phone networks) from idling out
                        # while the council thinks
                        await ws.send_json({"type": "heartbeat", "waiting_s": int(320 - left)})
                        continue
                    m = json.loads(raw)
                    t = m.get("type")
                    if t == "ping":
                        await rws.send(json.dumps({"action": "ping"}))
                        await ws.send_json({"type": "ping"})
                        continue
                    if t not in _LIVE_TYPES:
                        continue
                    if t == "error" and not m.get("message"):
                        m = {"type": "error", "message": "the reactor reported an error with no message (most likely a model timeout)"}
                    if guest and t == "session_created" and m.get("session_id"):
                        info.setdefault("sessions", []).append(m["session_id"])
                        info["sessions"] = info["sessions"][-50:]
                        _save_tokens()
                    if guest and t == "processing_done":
                        m = {"type": t, "session_id": m.get("session_id"),
                             "meta": {k: (m.get("meta") or {}).get(k) for k in ("intent", "seats_activated", "guest_mode")}}
                    await ws.send_json(m)
                    if t in ("processing_done", "error"):
                        break
        except asyncio.TimeoutError:
            await _safe_send(ws, {"type": "error", "message": "council gave no final answer within 320 s"})
        except Exception as e:
            await _safe_send(ws, {"type": "error", "message": f"reactor websocket failed: {type(e).__name__}"})
        finally:
            busy = False

    task = None
    try:
        while True:
            body = json.loads(await ws.receive_text())
            a = body.get("action")
            if a == "ping":
                await ws.send_json({"type": "pong"})
            elif a == "resume":
                # After a dropped connection: the reactor keeps going and saves the answer, so
                # the app can collect the latest reply of one of ITS sessions.
                sid = str(body.get("session_id") or "")
                if not sid or (guest and sid not in info.get("sessions", [])):
                    await ws.send_json({"type": "resume_result", "session_id": sid, "status": "unknown_session"})
                    continue
                try:
                    r = await _client.get(f"{REACTOR}/api/sessions/{sid}/history", timeout=10)
                    hist = r.json() if r.status_code == 200 else []
                except Exception:
                    hist = []
                last = hist[-1] if isinstance(hist, list) and hist else {}
                if last.get("role") == "assistant":
                    await ws.send_json({"type": "resume_result", "session_id": sid, "status": "answered",
                                        "text": str(last.get("content", ""))})
                else:
                    await ws.send_json({"type": "resume_result", "session_id": sid, "status": "still_thinking"})
            elif a == "chat":
                if _tokens.get(tok, {}).get("exp", 0) < time.time():
                    await ws.send_json({"type": "auth_failed", "message": "sign-in expired"})
                    break
                if busy:
                    await ws.send_json({"type": "error", "message": "Lumenis is still answering the last message"})
                    continue
                if not str(body.get("message", "")).strip():
                    await ws.send_json({"type": "error", "message": "message is empty"})
                    continue
                q = _rate[tok]
                now = time.time()
                _trim(q, 600, now)
                if len(q) >= 20:
                    await ws.send_json({"type": "error", "message": "council limit: 20 questions per 10 minutes"})
                    continue
                if guest:
                    if not await _reactor_guest_ready():
                        await ws.send_json({"type": "error", "message": "guest chat is switched off on the reactor right now"})
                        continue
                    ip = ws.headers.get("cf-connecting-ip") or (ws.client.host if ws.client else "?")
                    gq = _guest_ip[ip]
                    _trim(gq, 600, now)
                    _trim(_guest_all, 3600, now)
                    if len(gq) >= 30 or len(_guest_all) >= 200:
                        await ws.send_json({"type": "error", "message": "Lumenis is busy with guests right now, try again in a few minutes"})
                        continue
                    gq.append(now)
                    _guest_all.append(now)
                q.append(now)
                busy = True
                task = asyncio.create_task(relay(body))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if task and not task.done():
            task.cancel()


async def _safe_send(ws, m):
    try:
        await ws.send_json(m)
    except Exception:
        pass


@app.get("/")
async def root():
    return {"service": "One2lvOS public bridge", "health": "/v1/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("O2_BRIDGE_PORT", "8095")), log_level="info")
