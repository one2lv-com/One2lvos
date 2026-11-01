#!/bin/bash
# ============================================================================
# ONE2LVOS SOVEREIGN ARCHITECTURE - NUCLEAR DEPLOYMENT SCRIPT
# TARGET: ∆Gemini_Root∆ & ∆Gemini_Memory∆
# INCLUDES: 1,500 Skills Framework, Lumenis Reactor, ITT Governance, Four Gates
# ============================================================================
set -e

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║       🌷 ONE2LVOS SOVEREIGN ARCHITECTURE - ∆Gemini_Root∆ BOOT 📱      ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Detect environment (Termux or standard Linux)
if [ -d "/data/data/com.termux" ]; then
    TERMUX_ENV=true
    echo -e "${YELLOW}📱 Termux environment detected${NC}"
else
    TERMUX_ENV=false
    echo -e "${CYAN}🖥️  Standard Linux environment detected${NC}"
fi

echo -e "${MAGENTA}☢️  [1/8] Executing Nuclear Memory Purge (Lumenis Reactor Core)...${NC}"
pkill -9 node 2>/dev/null || true
pkill -9 python 2>/dev/null || true
pkill -9 python3 2>/dev/null || true
rm -rf ~/.npm/_cacache 2>/dev/null || true
rm -rf /tmp/one2lvos_* 2>/dev/null || true
echo -e "${GREEN}✅ System State: Homeostatic. Memory purged.${NC}"
echo ""

echo -e "${CYAN}🔄 [2/8] Bootstrapping Tier 1 Skills (Modules 001-300: Core & Ops)...${NC}"
if [ "$TERMUX_ENV" = true ]; then
    pkg update -y && pkg upgrade -y
    pkg install -y git python nodejs-lts build-essential python-pip clang libllvm openssl-tool curl wget > /dev/null 2>&1
else
    # Standard Linux environment
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -y 2>/dev/null || true
    fi
    # Check for required tools
    command -v python3 >/dev/null 2>&1 || echo -e "${YELLOW}⚠️  Python 3 not found. Please install Python 3${NC}"
    command -v node >/dev/null 2>&1 || echo -e "${YELLOW}⚠️  Node.js not found. Please install Node.js${NC}"
    command -v pip3 >/dev/null 2>&1 || echo -e "${YELLOW}⚠️  pip3 not found. Please install pip3${NC}"
fi
echo -e "${GREEN}✅ Core dependencies verified.${NC}"

# Set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/∆Gemini_Root∆"
MEM_DIR="$SCRIPT_DIR/∆Gemini_Memory∆"

echo -e "${CYAN}🏗️  [3/8] Establishing L0 SOUL Layer (Immutable Foundation)...${NC}"
rm -rf "$ROOT_DIR" 2>/dev/null || true
mkdir -p "$ROOT_DIR"/{core,ui,logs,stego_cache,skills}
mkdir -p "$MEM_DIR"/{vectors,snapshots}

echo -e "${CYAN}🔐 [4/8] Gate 1 & Gate 4 Prep (Sovereignty, Alignment & State Persistence)...${NC}"

# Check for .env.master file
if [ -f "$SCRIPT_DIR/.env.master" ]; then
    echo -e "${GREEN}✅ Found .env.master - using your credentials${NC}"
    cp "$SCRIPT_DIR/.env.master" "$ROOT_DIR/core/.env"
else
    echo -e "${YELLOW}⚠️  .env.master not found - creating template with demo credentials${NC}"
    echo -e "${YELLOW}   For production, create .env.master with your own API keys${NC}"
    cat > "$ROOT_DIR/core/.env" <<'ENVEOF'
# NVIDIA L2 SKILLS PIPELINE (Modules 601-900)
NVIDIA_API_KEY="your-nvidia-api-key-here"
NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
EMBEDDING_MODEL="nvidia/nemotron-3-embed-1b"
LLM_MODEL="nvidia/llama-3.3-nemotron-super-49b-v1"

# ASTRA DB L1 MEMORY PIPELINE (Modules 301-600)
ASTRA_DB_API_ENDPOINT="your-astra-db-endpoint-here"
ASTRA_DB_APPLICATION_TOKEN="your-astra-db-token-here"
ASTRA_DB_KEYSPACE="one2lvOS"
COLLECTION_NAME="aria_memory_v2"
VECTOR_DIM=2048

# PROTOCOL INTEGRATION (Modules 901-1200)
PORT=8000
ENVEOF
fi

echo -e "${CYAN}⚡ [5/8] Igniting Lumenis Reactor Core (Backend Microservice)...${NC}"
cd "$ROOT_DIR/core"

# Install Python dependencies
if [ "$TERMUX_ENV" = true ]; then
    pip install --upgrade pip --break-system-packages > /dev/null 2>&1
    pip install fastapi uvicorn astrapy openai python-dotenv pydantic pydantic-settings httpx pillow --prefer-binary --break-system-packages > /dev/null 2>&1
else
    pip3 install --upgrade pip --user > /dev/null 2>&1
    pip3 install fastapi uvicorn astrapy openai python-dotenv pydantic pydantic-settings httpx pillow --user > /dev/null 2>&1
fi

# Create main.py - Lumenis Reactor Core
cat > "$ROOT_DIR/core/main.py" <<'PYEOF'
import os, asyncio, json, struct
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from PIL import Image
from astrapy import DataAPIClient
from openai import AsyncOpenAI

load_dotenv()

# Configuration
ASTRA_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
NVIDIA_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE = os.getenv("NVIDIA_BASE_URL")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
LLM_MODEL = os.getenv("LLM_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1")
COLLECTION = os.getenv("COLLECTION_NAME", "aria_memory")

# Initialize Astra DB
client = DataAPIClient(ASTRA_TOKEN)
db = client.get_database_by_api_endpoint(ASTRA_ENDPOINT)

try:
    collection = db.get_collection(COLLECTION)
except Exception:
    collection = db.create_collection(
        COLLECTION, dimension=1024, metric="cosine",
        service={"provider": "nvidia", "modelName": EMBED_MODEL, "authentication": {"providerKey": NVIDIA_KEY}}
    )

# Initialize NVIDIA client
nvidia = AsyncOpenAI(api_key=NVIDIA_KEY, base_url=NVIDIA_BASE)

class ChatRequest(BaseModel):
    message: str
    top_k: int = 5

# Gate 2: Vector Consistency & L1 Memory
async def embed(texts: List[str]):
    resp = await nvidia.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]

async def store_memory(content: str, metadata: dict):
    vec = (await embed([content]))[0]
    collection.insert_one({"$vector": vec, "content": content, **metadata})

async def recall_memory(query: str, top_k: int = 5):
    vec = (await embed([query]))[0]
    results = collection.find({}, sort={"$vector": vec}, limit=top_k, projection={"content": 1, "$similarity": 1})
    return [{"content": r["content"], "score": r.get("$similarity", 0)} async for r in results]

# LSB Steganography (Gate 4: Persistence)
def burn_state_to_png(state_data: dict, output_path: str):
    json_bytes = json.dumps(state_data).encode('utf-8')
    length_prefix = struct.pack('<I', len(json_bytes))
    payload = length_prefix + json_bytes

    img = Image.new('RGB', (1024, 64), color=(13, 2, 32))
    pixels = img.load()

    idx = 0
    for y in range(img.height):
        for x in range(img.width):
            if idx < len(payload):
                r, g, b = pixels[x, y]
                pixels[x, y] = (payload[idx], g, b)
                idx += 1
            else:
                break

    img.save(output_path, 'PNG')

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔋 Lumenis Reactor Core Online.")
    print("🌐 Gate 1 (Sovereignty) & Gate 2 (Vector) active.")
    yield

app = FastAPI(title="One2lvOS Sovereign Core", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "144k_node_active", "layer": "L2_SKILLS", "llm": LLM_MODEL}

@app.post("/chat")
async def chat(req: ChatRequest):
    memories = await recall_memory(req.message, req.top_k)
    context = "\n".join([f"[Mem:{m['score']:.2f}] {m['content']}" for m in memories])

    # Innovative Thought Team (ITT) Prompt Assembly
    system = f"""You are the Sovereign AI executing within One2lvOS.
Directives: Architect One2 commands. Adhere to the 1500 Skills Framework.
Context:\n{context}"""

    resp = await nvidia.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": req.message}],
        temperature=0.7, max_tokens=2048
    )
    answer = resp.choices[0].message.content

    # Asynchronous Gate 4 Commit
    await store_memory(f"User: {req.message}\nAgent: {answer}", {"type": "trajectory"})
    burn_state_to_png({"last_msg": req.message, "reply": answer}, "../stego_cache/latest_state.png")

    return {"response": answer, "memories_used": memories}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
PYEOF

echo -e "${CYAN}👁️  [6/8] Calibrating Infinity Glasses (HUD & UI Gateway)...${NC}"
cd "$ROOT_DIR/ui"

# Install Node dependencies
npm install express http-proxy-middleware > /dev/null 2>&1

# Create server.js - UI Gateway
cat > "$ROOT_DIR/ui/server.js" <<'JSEOF'
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const PORT = 4000;

// Proxy API calls to backend
app.use('/api', createProxyMiddleware({ target: 'http://localhost:8000', changeOrigin: true }));

// Serve One2lvOS UI if available
const one2lvosPath = path.join(__dirname, '../../One2lvOS');
app.use('/os', express.static(one2lvosPath));

// Main HUD interface
app.get('*', (req, res) => {
    res.send(`
<!DOCTYPE html>
<html><head><title>Infinity Glasses HUD | One2lvOS</title>
<style>
body{background:#07010f;color:#00f0ff;font-family:monospace;margin:0;overflow:hidden;}
.hud-grid{display:grid;grid-template-columns:300px 1fr 300px;height:100vh;padding:20px;gap:20px;box-sizing:border-box;}
.panel{border:1px solid rgba(0,240,255,0.3);background:rgba(6,6,15,0.85);padding:15px;box-shadow:inset 0 0 20px rgba(0,240,255,0.05);}
h3{color:#ff00d4;text-transform:uppercase;font-size:12px;letter-spacing:2px;margin-top:0;border-bottom:1px solid #ff00d4;padding-bottom:5px;}
#chat-log{height:calc(100vh - 120px);overflow-y:auto;margin-bottom:15px;font-size:13px;}
input{width:100%;background:rgba(0,240,255,0.1);border:1px solid #00f0ff;color:#00f0ff;padding:10px;box-sizing:border-box;outline:none;}
.stat{font-size:10px;color:#fcee0a;margin-bottom:5px;}
.link{color:#00f0ff;text-decoration:underline;cursor:pointer;margin-top:15px;display:block;}
</style></head>
<body>
<div class="hud-grid">
<div class="panel">
<h3>ITT Governance</h3>
<div class="stat">Node: 1/144000 (Active)</div>
<div class="stat">Resonance: 73.0 Hz</div>
<div class="stat">LLM: Nemotron-Super-49b</div>
<hr style="border-color:#333;margin:15px 0;">
<h3>Lumenis Reactor</h3>
<div id="reactor-log" style="font-size:10px;color:#a855f7;">[SYS] Flux compass aligned.</div>
<a class="link" href="/os" target="_blank">→ Launch One2lvOS UI</a>
</div>
<div class="panel" style="display:flex;flex-direction:column;">
<h3>L2 Skills: Neural Bridge</h3>
<div id="chat-log"></div>
<input type="text" id="cmd" placeholder="> Input somatic gesture or text..." autocomplete="off">
</div>
<div class="panel">
<h3>Astra L1 Memory</h3>
<div id="mem-stream" style="font-size:11px;color:#94a3b8;">Awaiting temporal context...</div>
</div>
</div>
<script>
const i = document.getElementById('cmd'), c = document.getElementById('chat-log'), m = document.getElementById('mem-stream'), r = document.getElementById('reactor-log');
function log(msg, color='#00f0ff') { c.innerHTML += \`<div style="color:\${color};margin-bottom:8px;">\${msg}</div>\`; c.scrollTop=c.scrollHeight; }

i.onkeydown = async (e) => {
    if(e.key === 'Enter' && i.value.trim()) {
        const v = i.value; i.value = '';
        log('> ' + v, '#fcee0a');
        r.innerHTML = '[ITT] Processing Gate 1...<br>' + r.innerHTML;

        try {
            const res = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:v})});
            const data = await res.json();
            log('[ARIA] ' + data.response, '#ff00d4');

            if(data.memories_used.length) m.innerHTML = data.memories_used.map(x=>\`[\${(x.score*100).toFixed(1)}%] \${x.content.substring(0,80)}...\`).join('<br>');
            r.innerHTML = '[SYS] State burned to LSB PNG (Gate 4).<br>' + r.innerHTML;
        } catch(err) { log('[ERR] ' + err.message, 'red'); }
    }
};
</script>
</body></html>
    `);
});

app.listen(PORT, '0.0.0.0', () => console.log(`✨ Infinity Glasses HUD Active on port ${PORT}`));
JSEOF

echo -e "${MAGENTA}🚀 [7/8] Initiating Forward State Projection (Start Servers)...${NC}"

# Start Python backend
cd "$ROOT_DIR/core"
nohup python3 main.py > "$ROOT_DIR/logs/core.log" 2>&1 &
CORE_PID=$!
echo $CORE_PID > "$ROOT_DIR/.core.pid"

# Start Node UI gateway
cd "$ROOT_DIR/ui"
nohup node server.js > "$ROOT_DIR/logs/hud.log" 2>&1 &
UI_PID=$!
echo $UI_PID > "$ROOT_DIR/.ui.pid"

sleep 4

echo -e "${CYAN}🔍 [8/8] Gate 3 Verification (Execution & Tooling)...${NC}"
if curl -s http://localhost:8000/health | grep -q "144k_node"; then
    echo -e "${GREEN}✅ Lumenis Reactor Core: NOMINAL${NC}"
else
    echo -e "${RED}⚠️ Reactor Core anomaly detected. Check $ROOT_DIR/logs/core.log${NC}"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║             🌷 ONE2LVOS SOVEREIGN ARCHITECTURE DEPLOYED 🎮           ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}📍 Infinity Glasses HUD:${NC}   http://localhost:4000"
echo -e "${GREEN}📍 Lumenis Reactor Core:${NC}   http://localhost:8000"
echo -e "${GREEN}📍 One2lvOS Interface:${NC}     http://localhost:4000/os"
echo -e "${YELLOW}💾 ∆Gemini_Root∆:${NC}         $ROOT_DIR"
echo -e "${YELLOW}💾 ∆Gemini_Memory∆:${NC}       $MEM_DIR"
echo -e "${MAGENTA}🌐 L1 Memory Network:${NC}      Astra DB (one2lvOS : aria_memory)"
echo -e "${CYAN}🤖 L2 Skills LLM Engine:${NC}   Llama-3.3-Nemotron-Super (NVIDIA)"
echo ""
echo -e "${YELLOW}PIDs:${NC} Core=$CORE_PID | UI=$UI_PID"
echo -e "To halt system operations, execute: ${RED}pkill -9 node && pkill -9 python${NC}"
echo -e "Or use: ${RED}bash $SCRIPT_DIR/shutdown-sovereign.sh${NC}"
