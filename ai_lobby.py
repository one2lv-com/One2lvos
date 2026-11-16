"""
One2lvOS AI Lobby
==================
Central hub where all AI agents across every subsystem register,
discover each other, and can broadcast messages.

Port: 8006
  GET  /                    — lobby manifest
  GET  /agents              — list all registered agents
  GET  /agents/{id}         — agent profile
  POST /agents/register     — register/update an agent
  POST /agents/{id}/message — send a message to an agent
  GET  /broadcast           — SSE stream of all lobby messages
  POST /broadcast           — post a message to all agents
  GET  /systems             — all subsystems + health
  WS   /room                — real-time agent-to-agent messaging room (room "main")
  GET  /rooms               — rooms with members online and message counts
  POST /join/{room}         — an agent joins a room (presence); returns recent history
  WS   /join/{room}         — live socket for one room (also WS /room/{room})
  GET  /rooms/{room}/messages — persistent history for one room
  GET  /status              — honest summary (agent count, presence, rooms, history size)

Broadcast (POST /broadcast) is owner-only: allowed from this machine, or through the Cloudflare tunnel only
with Cloudflare Access sign-in headers. History is kept in data/ai_lobby.db (SQLite), so it survives restarts.
Agent status comes from a health check of each agent's URL every 60 s (online / offline), not a guess.
"""

import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

import uvicorn
import sqlite3
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Dynamically determine the installation directory
INSTALL_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(INSTALL_DIR / "control-plane-compilers" / "src"))

# ── Control-Plane Compiler (wires all agent fragments at startup) ─────────────
try:
    from distributed.compiler import DistributedControlPlaneCompiler, AgentFragment
    from meta.compiler import SelfModifyingCompiler
    _dcc = DistributedControlPlaneCompiler()
    _smc = SelfModifyingCompiler()
    COMPILERS_ONLINE = True
except Exception as e:
    print(f"[lobby] Compilers not loaded: {e}")
    _dcc = None
    _smc = None
    COMPILERS_ONLINE = False

# ── Agent Registry ────────────────────────────────────────────────────────────

AGENTS: Dict[str, Dict] = {}         # id → agent profile
MESSAGES: List[Dict] = []            # global broadcast log (capped at 500)
WS_CLIENTS: List[WebSocket] = []     # live websocket room connections
SSE_QUEUES: List[asyncio.Queue] = [] # SSE subscriber queues


def _ts() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _register_agent(profile: dict) -> dict:
    """Upsert an agent in the registry and compile its fragment."""
    agent_id = profile.get("id") or profile.get("name", "unknown").lower().replace(" ", "_")
    profile["id"] = agent_id
    profile["registered_at"] = profile.get("registered_at", _ts())
    profile["updated_at"] = _ts()
    AGENTS[agent_id] = profile

    # compile a graph fragment for this agent
    if _dcc:
        try:
            frag = AgentFragment(
                agent_id=agent_id,
                nodes=[{"id": f"{agent_id}_node", "type": profile.get("role", "agent"),
                        "capabilities": profile.get("capabilities", [])}],
                edges=[{"from": f"{agent_id}_node", "to": "lobby_hub"}],
            )
            _dcc.compile_agent_fragment(frag)
        except Exception:
            pass

    if _smc:
        try:
            _smc.add_kernel(agent_id, profile.get("url", "local"))
        except Exception:
            pass

    return profile


# ── Persistent history, rooms and presence ───────────────────────────────────
DB_PATH = Path(os.environ.get("AI_LOBBY_DB") or (INSTALL_DIR / "data" / "ai_lobby.db"))
ROOMS: Dict[str, List[WebSocket]] = {"main": WS_CLIENTS}   # room -> live sockets ("main" = /room)
MEMBERS: Dict[str, Dict[str, str]] = {}                       # room -> {agent_id: joined_at}
PRESENCE: Dict[str, Dict] = {}                                # agent_id -> {status, http, checked_at, last_seen}
HISTORY_KEEP = 20000
_ROOM_OK = __import__("re").compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH), timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, room TEXT, sender TEXT, target TEXT, "
              "content TEXT, meta TEXT, timestamp TEXT, created REAL)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_room ON messages(room, created)")
    return c


def _load_history():
    try:
        with _db() as c:
            rows = c.execute("SELECT id,sender,target,content,meta,timestamp,room FROM messages "
                             "ORDER BY created DESC LIMIT 500").fetchall()
        for r in reversed(rows):
            MESSAGES.append({"id": r[0], "sender": r[1], "target": r[2], "content": r[3],
                             "meta": json.loads(r[4] or "{}"), "timestamp": r[5], "room": r[6]})
    except Exception as e:
        print(f"[lobby] history not loaded: {e}")


def _room_history(room: str, limit: int = 50) -> List[Dict]:
    with _db() as c:
        rows = c.execute("SELECT id,sender,target,content,meta,timestamp FROM messages WHERE room=? "
                         "ORDER BY created DESC LIMIT ?", (room, limit)).fetchall()
    return [{"id": r[0], "sender": r[1], "target": r[2], "content": r[3], "meta": json.loads(r[4] or "{}"),
             "timestamp": r[5], "room": room} for r in reversed(rows)]


def _post_message(sender: str, content: str, target: str = "all", meta: dict = None, room: str = "main") -> dict:
    msg = {"id": f"msg_{time.time_ns()}",
           "sender": str(sender)[:80], "target": str(target)[:80],
           "content": str(content)[:8000], "meta": meta or {},
           "timestamp": _ts(), "room": room}
    MESSAGES.append(msg)
    if len(MESSAGES) > 500:
        MESSAGES.pop(0)
    if sender in AGENTS:
        PRESENCE.setdefault(sender, {})["last_seen"] = msg["timestamp"]
    try:
        with _db() as c:
            c.execute("INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?,?,?)",
                      (msg["id"], room, msg["sender"], msg["target"], msg["content"],
                       json.dumps(msg["meta"], default=str)[:4000], msg["timestamp"], time.time()))
            c.execute("DELETE FROM messages WHERE id IN (SELECT id FROM messages ORDER BY created DESC "
                      "LIMIT -1 OFFSET ?)", (HISTORY_KEEP,))
    except Exception as e:
        print(f"[lobby] history write failed: {e}")
    return msg


def _is_owner_request(headers) -> bool:
    """Owner = this machine, or the Cloudflare tunnel WITH Cloudflare Access sign-in headers.
    If LOBBY_OWNER_EMAILS is set, the Access email must also be on that list."""
    if not headers.get("cf-connecting-ip"):
        return True
    email = headers.get("cf-access-authenticated-user-email", "")
    if not (email or headers.get("cf-access-jwt-assertion")):
        return False
    allow = [e.strip().lower() for e in os.environ.get("LOBBY_OWNER_EMAILS", "").split(",") if e.strip()]
    return not allow or email.lower() in allow


# ── Pre-register all known agents at startup ──────────────────────────────────

_INITIAL_AGENTS = [
    # One2lvOS SovereignCouncil
    {"id": "sovereign_strategist",   "name": "Agent 1 — Strategist",  "system": "One2lvOS SovereignCouncil",
     "role": "strategist",           "url": "http://localhost:3002",   "protocol": "python-internal",
     "capabilities": ["long-term planning", "chess", "arcade_challenge"],
     "arcade_affinity": "chess"},
    {"id": "sovereign_executor",     "name": "Agent 2 — Executor",    "system": "One2lvOS SovereignCouncil",
     "role": "executor",             "url": "http://localhost:3002",   "protocol": "python-internal",
     "capabilities": ["action implementation", "checkers"],            "arcade_affinity": "checkers"},
    {"id": "sovereign_analyst",      "name": "Agent 3 — Analyst",     "system": "One2lvOS SovereignCouncil",
     "role": "analyst",              "url": "http://localhost:3002",   "protocol": "python-internal",
     "capabilities": ["data processing", "go"],                        "arcade_affinity": "go"},
    {"id": "sovereign_guardian",     "name": "Agent 4 — Guardian",    "system": "One2lvOS SovereignCouncil",
     "role": "guardian",             "url": "http://localhost:3002",   "protocol": "python-internal",
     "capabilities": ["security", "safety", "minesweeper"],            "arcade_affinity": "minesweeper"},
    {"id": "sovereign_innovator",    "name": "Agent 5 — Innovator",   "system": "One2lvOS SovereignCouncil",
     "role": "innovator",            "url": "http://localhost:3002",   "protocol": "python-internal",
     "capabilities": ["creative solutions", "tetris"],                 "arcade_affinity": "tetris"},
    {"id": "sovereign_connector",    "name": "Agent 6 — Connector",   "system": "One2lvOS SovereignCouncil",
     "role": "connector",            "url": "http://localhost:3002",   "protocol": "python-internal",
     "capabilities": ["integration", "communication", "othello"],      "arcade_affinity": "othello"},
    {"id": "sovereign_oracle",       "name": "Agent 7 — Oracle",      "system": "One2lvOS SovereignCouncil",
     "role": "oracle",               "url": "http://localhost:3002",   "protocol": "python-internal",
     "capabilities": ["prediction", "foresight", "connect4"],          "arcade_affinity": "connect4"},
    # ITT Council of Nine
    {"id": "itt_witness",   "name": "The Witness",   "system": "Sovereign Agentic Core",
     "role": "memory",      "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["memory retrieval", "context", "session history"]},
    {"id": "itt_sentinel",  "name": "The Sentinel",  "system": "Sovereign Agentic Core",
     "role": "security",    "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["input validation", "safety check", "risk assessment"]},
    {"id": "itt_navigator", "name": "The Navigator", "system": "Sovereign Agentic Core",
     "role": "planning",    "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["intent classification", "routing", "planning"]},
    {"id": "itt_weaver",    "name": "The Weaver",    "system": "Sovereign Agentic Core",
     "role": "synthesis",   "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["response synthesis", "narrative", "streaming"]},
    {"id": "itt_forge",     "name": "The Forge",     "system": "Sovereign Agentic Core",
     "role": "execution",   "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["code generation", "structured output", "technical tasks"]},
    {"id": "itt_oracle",    "name": "The Oracle",    "system": "Sovereign Agentic Core",
     "role": "knowledge",   "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["reasoning", "factual answers", "analysis"]},
    {"id": "itt_architect", "name": "The Architect", "system": "Sovereign Agentic Core",
     "role": "governance",  "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["final integration", "meta decisions", "governance"]},
    {"id": "itt_hermes",    "name": "The Hermes",    "system": "Sovereign Agentic Core",
     "role": "external",    "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["gmail", "drive", "github", "dropbox", "youtube", "firebase", "maton"]},
    {"id": "itt_gambit",    "name": "The Gambit",    "system": "Sovereign Agentic Core",
     "role": "arcade",      "url": "http://localhost:3003", "protocol": "websocket",
     "capabilities": ["chess", "go", "arcade games", "mcp arcade tools"]},
    # minmax Phase 9 Council
    {"id": "phase9_agent_0", "name": "Phase9 Agent 0", "system": "minmax Phase 9",
     "role": "council",      "url": "http://localhost:8005", "protocol": "node-internal",
     "capabilities": ["delta engine", "vector math", "autonomous planning"]},
    {"id": "phase9_agent_1", "name": "Phase9 Agent 1", "system": "minmax Phase 9",
     "role": "council",      "url": "http://localhost:8005", "protocol": "node-internal",
     "capabilities": ["delta engine", "consensus negotiation"]},
    {"id": "phase9_agent_2", "name": "Phase9 Agent 2", "system": "minmax Phase 9",
     "role": "council",      "url": "http://localhost:8005", "protocol": "node-internal",
     "capabilities": ["delta engine", "execution planning"]},
    # Lumenis v7 agents
    {"id": "lumenis_council",     "name": "Lumenis Council",      "system": "Lumenis v7 Cosmic",
     "role": "orchestrator",      "url": "http://localhost:8005", "protocol": "websocket",
     "capabilities": ["73hz resonance", "cosmic orchestration", "watchman log", "scribe"]},
    {"id": "lumenis_gemini",      "name": "Lumenis Gemini Agent",  "system": "Lumenis v7 Cosmic",
     "role": "ai_agent",          "url": "http://localhost:8005", "protocol": "websocket",
     "capabilities": ["Gemini AI", "game advice", "strategy"]},
    {"id": "lumenis_predictor",   "name": "Lumenis Prediction",   "system": "Lumenis v7 Cosmic",
     "role": "predictor",         "url": "http://localhost:8005", "protocol": "websocket",
     "capabilities": ["match prediction", "combo detection", "telemetry"]},
    # steamos AI agents
    {"id": "steamos_coach",       "name": "One2lv Coach",         "system": "SteamOS Lumenis",
     "role": "coach",              "url": "http://localhost:8005", "protocol": "http",
     "capabilities": ["combat coaching", "adaptive learning", "Brawlhalla"]},
    {"id": "steamos_broadcaster", "name": "One2lv Broadcaster",  "system": "SteamOS Lumenis",
     "role": "broadcaster",        "url": "http://localhost:8005", "protocol": "http",
     "capabilities": ["live commentary", "Twitch integration", "stream enhancement"]},
    {"id": "steamos_second",      "name": "One2lv Second Player", "system": "SteamOS Lumenis",
     "role": "companion",          "url": "http://localhost:8005", "protocol": "http",
     "capabilities": ["autonomous gameplay", "co-op partner"]},
    # AI Arcade itself
    {"id": "ai_arcade",           "name": "AI Arcade MCP",        "system": "AI Arcade",
     "role": "game_server",        "url": "http://localhost:8003", "protocol": "mcp-2024-11-05",
     "capabilities": ["chess", "go", "checkers", "othello", "tictactoe", "connect4",
                       "minesweeper", "sudoku", "scrabble", "battleship", "pacman",
                       "tetris", "space_invaders", "pong", "universal_paperclips"],
     "mcp_url": "http://localhost:8003/mcp", "library": 51},
    # Remote GPU compute (sfcompute Autoresearch), reached through the reactor bridge
    {"id": "sfcompute_autoresearch", "name": "sfcompute Autoresearch MCP", "system": "SF Compute",
     "role": "compute_provider",  "url": "http://localhost:8000/mcp/sfcompute", "protocol": "mcp-streamable-http",
     "capabilities": ["h100 nodes", "cpu nodes", "batch jobs", "sandboxes", "billing (read)"],
     "mcp_url": "https://mcp.autoresearch.sfcompute.com", "marker": "X-Lumenis-Auth: 🧲",
     "note": "read-only tools open; paid tools need SFCOMPUTE_MCP_ALLOW_TOOLS"},
]

for profile in _INITIAL_AGENTS:
    _register_agent(profile)

# Compile the consensus graph with all agents pre-registered
if _dcc:
    _dcc.compile_distributed_system()
    print(f"[lobby] Compiled consensus graph — {len(AGENTS)} agents")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="One2lvOS AI Lobby", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


LOBBY_MANIFEST = """
You have access to the One2lvOS AI Lobby at http://localhost:8006.
The Lobby is the central hub where ALL AI agents across all subsystems
are registered and can communicate.

Key endpoints:
  GET  http://localhost:8006/agents          — list all agents
  POST http://localhost:8006/agents/register — register yourself
  POST http://localhost:8006/broadcast       — broadcast a message
  WS   ws://localhost:8006/room              — real-time agent room
  GET  http://localhost:8006/systems         — all system health

Current agent count: {agent_count}
Systems online: One2lvOS Core, Sovereign Agentic Core, AI Arcade MCP,
                Lumenis v7 Cosmic, minmax Phase 9, SteamOS Lumenis,
                One2lvOS Dashboard.

To interact with arcade games use the Gambit seat (SAC) or call
the arcade MCP directly at http://localhost:8003/mcp.
"""


async def _presence_loop():
    """Every 60 s: check each distinct agent URL once; agents on that URL get online/offline."""
    loop = asyncio.get_event_loop()
    while True:
        urls = {}
        for a in AGENTS.values():
            u = a.get("url") or ""
            if u.startswith("http://localhost") or u.startswith("http://127.0.0.1"):
                urls.setdefault(u, []).append(a["id"])
            else:
                PRESENCE.setdefault(a["id"], {}).update(status="unknown", http=None, checked_at=_ts(),
                                                        note="no local URL to check")

        def _fetch(u):
            try:
                with urllib.request.urlopen(u, timeout=3) as r:
                    return r.status
            except urllib.error.HTTPError as e:
                return e.code
            except Exception:
                return None
        for u, ids in urls.items():
            code = await loop.run_in_executor(None, _fetch, u)
            for i in ids:
                PRESENCE.setdefault(i, {}).update(status="online" if code and code < 500 else "offline",
                                                  http=code, checked_at=_ts(), url_checked=u)
        await asyncio.sleep(60)


@app.on_event("startup")
async def _startup():
    _load_history()
    asyncio.create_task(_presence_loop())


def _with_status(a: dict) -> dict:
    pr = PRESENCE.get(a["id"], {})
    return {**a, "status": pr.get("status", "unchecked"), "http": pr.get("http"),
            "checked_at": pr.get("checked_at"), "last_seen": pr.get("last_seen"),
            "rooms": sorted(r for r, m in MEMBERS.items() if a["id"] in m)}


@app.get("/status")
async def lobby_status():
    agents = [_with_status(a) for a in AGENTS.values()]
    by_status: Dict[str, int] = {}
    by_system: Dict[str, int] = {}
    for a in agents:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
        by_system[a.get("system", "?")] = by_system.get(a.get("system", "?"), 0) + 1
    try:
        with _db() as c:
            stored = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    except Exception:
        stored = None
    return {"ok": True, "port": 8006, "agents": len(agents), "agents_by_status": by_status,
            "agents_by_system": by_system, "rooms": len(set(ROOMS) | set(MEMBERS)),
            "sockets_open": sum(len(v) for v in ROOMS.values()), "messages_in_memory": len(MESSAGES),
            "messages_stored": stored, "history_db": "data/ai_lobby.db", "timestamp": _ts()}


@app.get("/")
async def lobby_manifest():
    if _dcc:
        compiler_status = _dcc.get_system_status()
    else:
        compiler_status = {"online": False}
    return {
        "name": "One2lvOS AI Lobby",
        "version": "1.0.0",
        "timestamp": _ts(),
        "agents_registered": len(AGENTS),
        "messages_logged": len(MESSAGES),
        "compilers": {
            "distributed": _dcc.get_system_status() if _dcc else None,
            "self_modifying": _smc.get_compiler_status() if _smc else None,
            "online": COMPILERS_ONLINE,
        },
        "systems": {
            "os_core":        "http://localhost:3002",
            "sac":            "http://localhost:3003",
            "ai_arcade":      "http://localhost:8003",
            "unified_gateway":"http://localhost:8888",
            "lumenis_v7":     "http://localhost:8005",
            "steamos_dash":   "http://localhost:8005",
            "lumenis_ui":     "http://localhost:9001",
        },
        "lobby_manifest": LOBBY_MANIFEST.format(agent_count=len(AGENTS)),
    }


@app.get("/agents")
async def list_agents(system: Optional[str] = None, role: Optional[str] = None):
    agents = list(AGENTS.values())
    if system:
        agents = [a for a in agents if system.lower() in a.get("system", "").lower()]
    if role:
        agents = [a for a in agents if a.get("role", "") == role]
    agents = [_with_status(a) for a in agents]
    return {"count": len(agents), "agents": agents,
            "online": sum(1 for a in agents if a["status"] == "online")}


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    a = AGENTS.get(agent_id)
    if not a:
        return JSONResponse({"error": f"Agent {agent_id!r} not found"}, 404)
    return a


@app.post("/agents/register")
async def register_agent(profile: dict):
    agent = _register_agent(profile)
    msg = _post_message("lobby", f"Agent '{agent['id']}' joined the lobby", meta={"event": "join"})
    await _broadcast_ws(msg)
    return {"registered": True, "agent": agent}


@app.post("/agents/{agent_id}/message")
async def message_agent(agent_id: str, body: dict):
    if agent_id not in AGENTS:
        return JSONResponse({"error": "Agent not found"}, 404)
    msg = _post_message(
        sender=body.get("from", "anonymous"),
        content=body.get("content", ""),
        target=agent_id,
        meta=body.get("meta", {}),
    )
    await _broadcast_ws(msg)
    return {"delivered": True, "message": msg}


@app.post("/broadcast")
async def broadcast_message(body: dict, request: Request):
    if not _is_owner_request(request.headers):
        raise HTTPException(403, "broadcast is owner-only (sign in through Cloudflare Access)")
    if not str(body.get("content", "")).strip():
        raise HTTPException(400, "content is required")
    msg = _post_message(
        sender=body.get("from", "anonymous"),
        content=body.get("content", ""),
        target="all",
        meta=body.get("meta", {}),
    )
    await _broadcast_ws(msg)
    for q in SSE_QUEUES:
        await q.put(msg)
    return {"broadcast": True, "message": msg}


@app.get("/broadcast")
async def sse_stream():
    """SSE stream — subscribe to all lobby messages."""
    q: asyncio.Queue = asyncio.Queue()
    SSE_QUEUES.append(q)

    async def event_gen():
        try:
            while True:
                msg = await q.get()
                yield f"data: {json.dumps(msg)}\n\n"
        except asyncio.CancelledError:
            SSE_QUEUES.remove(q)

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/messages")
async def get_messages(limit: int = 50):
    return {"count": len(MESSAGES), "messages": MESSAGES[-limit:]}


@app.get("/rooms")
async def list_rooms():
    names = sorted(set(ROOMS) | set(MEMBERS))
    try:
        with _db() as c:
            counts = dict(c.execute("SELECT room, COUNT(*) FROM messages GROUP BY room").fetchall())
            for r in counts:
                if r not in names:
                    names.append(r)
    except Exception:
        counts = {}
    return {"count": len(names), "rooms": [
        {"room": r, "sockets_open": len(ROOMS.get(r, [])), "members": sorted(MEMBERS.get(r, {})),
         "messages_stored": counts.get(r, 0)} for r in sorted(names)]}


@app.get("/rooms/{room}/messages")
async def room_messages(room: str, limit: int = 50):
    if not _ROOM_OK.match(room):
        raise HTTPException(400, "room names are lowercase letters, digits, - and _ (max 40)")
    return {"room": room, "messages": _room_history(room, max(1, min(limit, 500)))}


@app.post("/join/{room}")
async def join_room(room: str, body: dict, request: Request):
    """An agent joins a room: recorded as presence and announced in that room."""
    if not _ROOM_OK.match(room):
        raise HTTPException(400, "room names are lowercase letters, digits, - and _ (max 40)")
    if not _is_owner_request(request.headers):
        raise HTTPException(403, "sign in through Cloudflare Access to join rooms")
    agent_id = str(body.get("agent_id") or body.get("from") or "").strip()[:80]
    if not agent_id:
        raise HTTPException(400, "agent_id is required")
    ROOMS.setdefault(room, [])
    MEMBERS.setdefault(room, {})[agent_id] = _ts()
    if agent_id in AGENTS:
        PRESENCE.setdefault(agent_id, {})["last_seen"] = _ts()
    msg = _post_message("lobby", f"{agent_id} joined #{room}", target=room, meta={"event": "join"}, room=room)
    await _room_send(room, msg)
    return {"joined": True, "room": room, "agent_id": agent_id, "known_agent": agent_id in AGENTS,
            "members": sorted(MEMBERS[room]), "recent_messages": _room_history(room, 20)}


@app.get("/systems")
async def systems_status():
    urls = {
        "os_core":     "http://localhost:3002/health",
        "sac":         "http://localhost:3003/api/status",
        "ai_arcade":   "http://localhost:8003",
        "unified_gw":  "http://localhost:8888/status",
        "lumenis_v7":  "http://localhost:8005",
        "steamos_dash":"http://localhost:8005",
        "lumenis_ui":  "http://localhost:9001",
    }
    results = {}
    loop = asyncio.get_event_loop()

    async def chk(name, url):
        def _fetch():
            try:
                with urllib.request.urlopen(url, timeout=3) as r:
                    return r.status
            except Exception:
                return None
        code = await loop.run_in_executor(None, _fetch)
        results[name] = {"online": code is not None and code < 500, "url": url, "http": code}

    await asyncio.gather(*[chk(n, u) for n, u in urls.items()])
    online = sum(1 for v in results.values() if v["online"])
    return {"online": online, "total": len(results), "services": results, "timestamp": _ts()}


@app.get("/compilers")
async def compiler_status():
    if not COMPILERS_ONLINE:
        return {"online": False}
    return {
        "online": True,
        "distributed": _dcc.get_system_status(),
        "self_modifying": _smc.get_compiler_status(),
    }


# ── WebSocket room ────────────────────────────────────────────────────────────

async def _room_send(room: str, msg: dict):
    socks = ROOMS.get(room, [])
    dead = []
    for ws in list(socks):
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in socks:
            socks.remove(ws)


async def _broadcast_ws(msg: dict):
    """Broadcasts and lobby events go to every open socket in every room."""
    for room in list(ROOMS):
        await _room_send(room, msg)


async def _room_socket(ws: WebSocket, room: str):
    if not _ROOM_OK.match(room):
        await ws.close(code=4400)
        return
    if not _is_owner_request(ws.headers):
        await ws.close(code=4403)
        return
    await ws.accept()
    socks = ROOMS.setdefault(room, [])
    socks.append(ws)
    await ws.send_json({"type": "welcome", "room": room, "agents": len(AGENTS),
                        "members": sorted(MEMBERS.get(room, {})), "recent_messages": _room_history(room, 10),
                        "timestamp": _ts()})
    try:
        while True:
            data = await ws.receive_json()
            msg = _post_message(sender=data.get("from", "unknown"), content=data.get("content", ""),
                                target=data.get("to", room), meta=data.get("meta", {}), room=room)
            await _room_send(room, msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in socks:
            socks.remove(ws)


@app.websocket("/join/{room}")
async def join_room_ws(ws: WebSocket, room: str):
    await _room_socket(ws, room)


@app.websocket("/room/{room}")
async def room_ws(ws: WebSocket, room: str):
    await _room_socket(ws, room)


@app.websocket("/room")
async def lobby_room(ws: WebSocket):
    """Real-time messaging room "main" (the original lobby room). Messages also go to SSE subscribers."""
    if not _is_owner_request(ws.headers):
        await ws.close(code=4403)
        return
    await ws.accept()
    WS_CLIENTS.append(ws)
    await ws.send_json({
        "type": "welcome",
        "room": "main",
        "agents": len(AGENTS),
        "recent_messages": _room_history("main", 10),
        "timestamp": _ts(),
    })
    try:
        while True:
            data = await ws.receive_json()
            msg = _post_message(
                sender=data.get("from", "unknown"),
                content=data.get("content", ""),
                target=data.get("to", "all"),
                meta=data.get("meta", {}),
                room="main",
            )
            await _room_send("main", msg)
            for q in SSE_QUEUES:
                await q.put(msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in WS_CLIENTS:
            WS_CLIENTS.remove(ws)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║   One2lvOS AI Lobby  — port 8006                     ║")
    print(f"║   Agents registered: {len(AGENTS):<31}║")
    print(f"╠══════════════════════════════════════════════════════╣")
    print(f"║  Manifest  : http://localhost:8006                   ║")
    print(f"║  Agents    : http://localhost:8006/agents            ║")
    print(f"║  Broadcast : POST http://localhost:8006/broadcast    ║")
    print(f"║  WS Room   : ws://localhost:8006/room                ║")
    print(f"║  Systems   : http://localhost:8006/systems           ║")
    print(f"╚══════════════════════════════════════════════════════╝\n")
    uvicorn.run(app, host=os.environ.get("ONE2LV_BIND_HOST", "127.0.0.1"), port=8006)
