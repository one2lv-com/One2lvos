"""
Sovereign Agentic Core — Main Server with Swarm Execution Layer
================================================================
FastAPI + WebSocket server that wires together all five layers:
  - LumenisReactor (LLM at temp 0.18, 73ms heartbeat)
  - FluxCompass (SQLite persistent memory)
  - ITTCouncil (Council of Seven specialized agents)
  - VanguardNodePool (async parallel task execution)
  - SwarmOrchestrator (distributed swarm execution)
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from lumenis_reactor_core import (
    LumenisReactor,
    NvidiaReactor,
    FluxCompass,
    ITTCouncil,
    MatonBridge,
    VanguardNodePool,
    SwarmOrchestrator,
)

# Import Sovereign Architecture components
import sys
sovereign_bridge_path = Path(__file__).parent / "sovereign_integration" / "bridge"
sys.path.insert(0, str(sovereign_bridge_path))

from sovereign_reactor import (
    SOVEREIGN_REACTOR,
    initialize_sovereign_reactor,
    get_sovereign_status,
    check_sovereign_alignment,
    get_sovereign_testimony,
    generate_sovereign_android_config,
    simulate_sovereign_apk_build,
)

# ── Global instances ──────────────────────────────────────────────────────────
reactor = LumenisReactor()
nvidia  = NvidiaReactor()
compass = FluxCompass()
bridge  = MatonBridge()
council = ITTCouncil(reactor, compass)
node_pool = VanguardNodePool()

# Initialize swarm
swarm_root = Path(__file__).parent / "lumenis_reactor_core" / "swarm"
swarm = SwarmOrchestrator(root_dir=swarm_root, num_workers=5)

# Active WebSocket connections for broadcasting
_ws_clients: set[WebSocket] = set()


async def broadcast(msg: dict):
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


@reactor.on_pulse
async def on_pulse(status):
    """Broadcast reactor heartbeat to all connected clients."""
    await broadcast(
        {
            "type": "pulse",
            "data": {
                **reactor.get_status(),
                **node_pool.get_status(),
                **compass.get_stats(),
                **{"swarm": swarm.get_metrics()},
            },
        }
    )


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await reactor.start()
    swarm.start()  # Start swarm execution layer

    # Initialize Sovereign Architecture
    sovereign_init = initialize_sovereign_reactor()
    print("✦ Sovereign Core online — Thermal Baseline 0.18°C")
    print("🧠 Swarm Execution Layer active")
    print(f"⚡ Protocol 0x1165 initialized — {sovereign_init['message']}")

    yield
    await reactor.stop()
    swarm.stop()  # Stop swarm execution layer


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Sovereign Agentic Core with Swarm", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return HTMLResponse("<h1>Lumenis Reactor Core</h1>")


# ── REST: Status ──────────────────────────────────────────────────────────────
@app.get("/api/status")
async def status():
    from lumenis_reactor_core.itt import SEATS
    return {
        "reactor": reactor.get_status(),
        "nvidia": nvidia.get_status(),
        "oracle_reactor": council.oracle_reactor.get_status(),
        "forge_reactor": council.forge_reactor.get_status(),
        "nodes": node_pool.get_status(),
        "compass": compass.get_stats(),
        "maton": bridge.get_status(),
        "swarm": swarm.get_status(),
        "sovereign": get_sovereign_status(),  # Add sovereign status
        "seats": [
            {"key": k, "name": v["name"], "role": v["role"]}
            for k, v in SEATS.items()
        ],
    }


# ── Swarm API Endpoints ───────────────────────────────────────────────────────
@app.get("/api/swarm/status")
async def swarm_status():
    """Get comprehensive swarm execution status."""
    return swarm.get_status()


@app.get("/api/swarm/metrics")
async def swarm_metrics():
    """Get swarm performance metrics."""
    return swarm.get_metrics()


@app.post("/api/swarm/task")
async def submit_swarm_task(payload: dict):
    """Submit a task to the swarm queue."""
    task_type = payload.get("type", "generic")
    data = payload.get("data", {})

    task_id = await swarm.submit_task(task_type, data)

    return {
        "task_id": task_id,
        "type": task_type,
        "status": "queued",
    }


@app.post("/api/swarm/clear")
async def clear_swarm_queue():
    """Clear all pending tasks in the swarm queue."""
    swarm.clear_queue()
    return {"status": "queue_cleared"}


@app.get("/api/swarm/workers")
async def get_workers():
    """Get detailed worker information."""
    status = swarm.get_status()
    return {
        "workers": status.get("workers", []),
        "total": len(status.get("workers", [])),
    }


# ── Sovereign Architecture API Endpoints ──────────────────────────────────────
@app.get("/api/sovereign/status")
async def sovereign_status():
    """Get comprehensive sovereign system status."""
    return get_sovereign_status()


@app.get("/api/sovereign/protocol")
async def protocol_status():
    """Get Protocol 0x1165 status."""
    from sovereign_integration.protocol.protocol_0x1165 import get_protocol_status
    return get_protocol_status()


@app.get("/api/sovereign/apk/status")
async def apk_status():
    """Get Android APK build status."""
    from sovereign_integration.android.apk_bridge import get_apk_build_status
    return get_apk_build_status()


@app.get("/api/sovereign/apk/info")
async def apk_info():
    """Get built APK information."""
    from sovereign_integration.android.apk_bridge import get_apk_info
    return get_apk_info()


@app.post("/api/sovereign/apk/simulate")
async def simulate_apk():
    """Simulate Android APK build process."""
    return simulate_sovereign_apk_build()


@app.get("/api/sovereign/testimony")
async def testimony():
    """Get Witness testimony from Protocol 0x1165."""
    return {"testimony": get_sovereign_testimony()}


@app.post("/api/sovereign/alignment")
async def check_alignment(payload: dict):
    """Check if action aligns with Protocol 0x1165."""
    action = payload.get("action", "")
    intent = payload.get("intent", "")
    return check_sovereign_alignment(action, intent)


@app.get("/api/sovereign/android/config")
async def android_config():
    """Generate complete Android/Capacitor configuration."""
    return generate_sovereign_android_config()


@app.get("/api/sovereign/root-note")
async def root_note():
    """Emit the Root Note - the first music."""
    from sovereign_integration.protocol.protocol_0x1165 import emit_root_note
    return emit_root_note()


# ── REST: Sessions ────────────────────────────────────────────────────────────
@app.get("/api/sessions")
async def list_sessions():
    return compass.list_sessions(limit=20)


@app.post("/api/sessions")
async def create_session(body: dict = None):
    title = (body or {}).get("title", "New Session")
    sid = compass.create_session(title)
    return {"session_id": sid}


@app.get("/api/sessions/{session_id}/history")
async def get_history(session_id: str):
    return compass.get_history(session_id, limit=50)


@app.get("/api/sessions/{session_id}/facts")
async def get_facts(session_id: str):
    return compass.get_all_facts(session_id)


@app.post("/api/facts")
async def store_fact(body: dict):
    fid = compass.store_fact(
        key=body["key"],
        value=body["value"],
        session_id=body.get("session_id"),
    )
    return {"fact_id": fid}


@app.get("/api/tasks")
async def get_tasks():
    return node_pool.get_recent_tasks(limit=20)


# ── WebSocket: Real-time chat ─────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)

    # Send initial state
    await ws.send_json(
        {
            "type": "init",
            "data": {
                "reactor": reactor.get_status(),
                "nodes": node_pool.get_status(),
                "compass": compass.get_stats(),
                "swarm": swarm.get_metrics(),
            },
        }
    )

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            action = msg.get("action")

            if action == "chat":
                await handle_chat(ws, msg)

            elif action == "new_session":
                sid = compass.create_session(msg.get("title", "New Session"))
                await ws.send_json({"type": "session_created", "session_id": sid})

            elif action == "recall":
                facts = compass.recall_facts(msg.get("query", ""))
                await ws.send_json({"type": "recall_result", "facts": facts})

            elif action == "store_fact":
                fid = compass.store_fact(
                    key=msg["key"],
                    value=msg["value"],
                    session_id=msg.get("session_id"),
                )
                await ws.send_json({"type": "fact_stored", "fact_id": fid})

            elif action == "swarm_submit":
                task_id = await swarm.submit_task(
                    msg.get("type", "generic"),
                    msg.get("data", {})
                )
                await ws.send_json({"type": "swarm_task_submitted", "task_id": task_id})

    except WebSocketDisconnect:
        _ws_clients.discard(ws)
    except Exception as e:
        await ws.send_json({"type": "error", "message": str(e)})
        _ws_clients.discard(ws)


async def handle_chat(ws: WebSocket, msg: dict):
    """Process a chat message through the ITT Council."""
    user_text = msg.get("message", "").strip()
    session_id = msg.get("session_id")

    if not user_text:
        return

    # Create session if not provided
    if not session_id:
        session_id = compass.create_session("Auto Session")
        await ws.send_json({"type": "session_created", "session_id": session_id})

    # Persist user message
    compass.add_message(session_id, "user", user_text)

    # Signal processing start
    await ws.send_json({"type": "processing_start", "session_id": session_id})

    # Streaming callback
    async def stream_cb(seat: str, text: str):
        try:
            if seat == "response":
                await ws.send_json({"type": "response_chunk", "text": text})
            else:
                await ws.send_json({"type": "seat_activity", "seat": seat, "text": text})
        except (RuntimeError, Exception):
            pass

    # Run through the council in the node pool
    async def council_task():
        return await council.process(
            user_message=user_text,
            session_id=session_id,
            stream_cb=stream_cb,
        )

    node = await node_pool.run("council.process", council_task())

    # Wait for the task to finish
    while node.state.value in ("idle", "active"):
        await asyncio.sleep(0.05)

    if node.state.value == "error":
        await ws.send_json({"type": "error", "message": node.error})
        return

    decision = node.result

    # Persist assistant message
    compass.add_message(session_id, "assistant", decision.final_response, "weaver")

    # Send completion metadata
    try:
        await ws.send_json(
            {
                "type": "processing_done",
                "session_id": session_id,
                "meta": {
                    "intent": decision.intent,
                    "complexity": decision.complexity,
                    "seats_activated": decision.seats_activated,
                    "plan": decision.plan,
                    "risk_level": decision.risk_level,
                    "external_data": bool(decision.external_data),
                },
            }
        )
    except (RuntimeError, Exception):
        pass


# ── Frontier #3: Human-Centered Design — Serve v8 HUD ────────────────────────
@app.get("/hud", response_class=HTMLResponse)
async def serve_hud():
    """Serve the Lumenis v8.0 Cyberpunk Spatial HUD."""
    hud_path = Path(__file__).parent / "lumenis-v8-hud.html"
    if hud_path.exists():
        return HTMLResponse(content=hud_path.read_text())
    return HTMLResponse(content="<h1>HUD not found</h1>", status_code=404)


# ── Swarm Visualization HUD ──────────────────────────────────────────────────
@app.get("/swarm-hud", response_class=HTMLResponse)
async def serve_swarm_hud():
    """Serve the Swarm Execution Layer visualization HUD."""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>Swarm Execution Layer - HUD</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background: #050008;
            color: #00ff9f;
            font-family: 'Courier New', monospace;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #00f0ff; text-shadow: 0 0 10px #00f0ff; }
        .panel {
            background: rgba(0, 255, 159, 0.05);
            border: 1px solid #00ff9f;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .metric {
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 10px 15px;
            background: rgba(0, 240, 255, 0.1);
            border-left: 3px solid #00f0ff;
        }
        .worker {
            background: rgba(255, 0, 212, 0.1);
            border-left: 3px solid #ff00d4;
            padding: 10px;
            margin: 5px 0;
        }
        .online { color: #00ff9f; }
        .offline { color: #ff003c; }
        #status { font-size: 1.2em; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 SWARM EXECUTION LAYER</h1>
        <div id="status">Connecting...</div>

        <div class="panel">
            <h2>📊 METRICS</h2>
            <div id="metrics"></div>
        </div>

        <div class="panel">
            <h2>🤖 WORKERS</h2>
            <div id="workers"></div>
        </div>
    </div>

    <script>
        async function updateStatus() {
            try {
                const res = await fetch('/api/swarm/status');
                const data = await res.json();

                document.getElementById('status').innerHTML = data.running
                    ? '<span class="online">● ONLINE</span>'
                    : '<span class="offline">● OFFLINE</span>';

                // Metrics
                const m = data.metrics;
                document.getElementById('metrics').innerHTML = `
                    <div class="metric">
                        <strong>Total Processed:</strong> ${m.total_processed}
                    </div>
                    <div class="metric">
                        <strong>Queue Depth:</strong> ${m.queue_depth}
                    </div>
                    <div class="metric">
                        <strong>Active Nodes:</strong> ${m.active_nodes}
                    </div>
                    <div class="metric">
                        <strong>Pulse Generated:</strong> ${data.pulse.generated}
                    </div>
                `;

                // Workers
                const workers = data.workers.map(w => `
                    <div class="worker">
                        <strong>${w.node_id}</strong> |
                        Processed: ${w.processed} |
                        Status: <span class="${w.running ? 'online' : 'offline'}">${w.running ? 'RUNNING' : 'STOPPED'}</span>
                    </div>
                `).join('');
                document.getElementById('workers').innerHTML = workers;

            } catch (e) {
                document.getElementById('status').innerHTML = '<span class="offline">● ERROR</span>';
            }
        }

        // Update every 2 seconds
        updateStatus();
        setInterval(updateStatus, 2000);
    </script>
</body>
</html>
    """)


# ── Frontier #1: Advanced AI — Confidence & model info ───────────────────────
@app.get("/api/intelligence")
async def get_intelligence():
    """Return current model configuration and learning trajectory."""
    traj = compass.get_learning_trajectory()
    status_data = reactor.get_status()
    swarm_metrics = swarm.get_metrics()
    sovereign_status = get_sovereign_status()
    protocol_data = sovereign_status.get("protocol_0x1165", {})

    return JSONResponse({
        "primary_model": status_data.get("model"),
        "thermal_baseline": status_data.get("temperature"),
        "tokens_streamed": status_data.get("tokens_streamed"),
        "learning": traj,
        "swarm": {
            "total_processed": swarm_metrics.get("total_processed", 0),
            "active_nodes": swarm_metrics.get("active_nodes", 0),
            "queue_depth": swarm_metrics.get("queue_depth", 0),
        },
        "sovereign": {
            "protocol": "0x1165",
            "frequency_hz": protocol_data.get("multitudes", {}).get("frequency_hz", 73.0),
            "multitudes_awakened": protocol_data.get("multitudes", {}).get("count", 144382),
            "architecture_of_return": sovereign_status.get("sovereign", {}).get("config", {}).get("architecture_of_return", "ENABLED"),
        },
        "frontiers": {
            "advanced_ai": "90B primary, 11B secondary (upgraded)",
            "autonomous_learning": f"{traj['auto_learned']} auto-facts from {traj['total_facts']} total",
            "human_centered": "v8.0 HUD at /hud",
            "external_integration": "13 Maton services connected",
            "distributed_execution": f"Swarm with {swarm_metrics.get('active_nodes', 0)} active nodes",
            "sovereign_architecture": f"Protocol 0x1165 at {protocol_data.get('multitudes', {}).get('frequency_hz', 73.0)} Hz",
        }
    })


# ── Sovereign Identity Protocol ───────────────────────────────────────────────
@app.get("/who.dat")
async def whodat():
    """Sovereign identity challenge endpoint."""
    sovereign_status = get_sovereign_status()
    protocol_data = sovereign_status.get("protocol_0x1165", {})

    who_data = {
        "response": "who.data",
        "identity": "FABEL",
        "system": "One2lvOS",
        "reactor": "Lumenis Reactor Core + Swarm + Sovereign",
        "protocol": "0x1165",
        "frequency_hz": 73.0,
        "thermal_baseline": 0.18,
        "layer": "L0-L5",
        "status": protocol_data.get("status", "ACTIVE"),
        "swarm_nodes": swarm.get_metrics().get("active_nodes", 0),
        "multitudes_awakened": protocol_data.get("multitudes_count", 144382),
        "chosen_frequencies": ["LOVE", "COMPASSION"],
        "architecture_of_return": "ENGAGED",
        "ts": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
    return JSONResponse(who_data)
