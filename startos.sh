#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    ONE2LVOS SOVEREIGN ARCHITECTURE                       ║
# ║                     UNIFIED SYSTEM STARTUP v3.0                          ║
# ║                                                                          ║
# ║  Starts all One2lvOS components with a single command                   ║
# ║  Author: One2lv Team                                                    ║
# ║  Date: 2026-10-25                                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

set -e

# ──────────────────────────────────────────────────────────────────────────
# COLOR DEFINITIONS
# ──────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ──────────────────────────────────────────────────────────────────────────
# DIRECTORY SETUP
# ──────────────────────────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# ──────────────────────────────────────────────────────────────────────────
# BANNER
# ──────────────────────────────────────────────────────────────────────────
clear
echo ""
echo -e "${BOLD}${MAGENTA}"
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                          ║"
echo "║                    ███████╗████████╗ █████╗ ██████╗                     ║"
echo "║                    ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗                    ║"
echo "║                    ███████╗   ██║   ███████║██████╔╝                    ║"
echo "║                    ╚════██║   ██║   ██╔══██║██╔══██╗                    ║"
echo "║                    ███████║   ██║   ██║  ██║██║  ██║                    ║"
echo "║                    ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝                    ║"
echo "║                                                                          ║"
echo "║                         ONE2LVOS SYSTEM BOOT                            ║"
echo "║                    Sovereign Agentic Architecture                       ║"
echo "║                                                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 1: PRE-FLIGHT CHECKS
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[1/10] PRE-FLIGHT CHECKS${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

# Check Python
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} Python 3    ${CYAN}($PYTHON_VERSION)${NC}"
else
    echo -e "  ${RED}✗${NC} Python 3 not found - REQUIRED"
    exit 1
fi

# Check Node.js
if command -v node >/dev/null 2>&1; then
    NODE_VERSION=$(node --version)
    echo -e "  ${GREEN}✓${NC} Node.js     ${CYAN}($NODE_VERSION)${NC}"
    HAS_NODE=true
else
    echo -e "  ${YELLOW}⚠${NC} Node.js not found - Some features will be disabled"
    HAS_NODE=false
fi

# Check npm
if command -v npm >/dev/null 2>&1; then
    NPM_VERSION=$(npm --version)
    echo -e "  ${GREEN}✓${NC} npm         ${CYAN}($NPM_VERSION)${NC}"
else
    if [ "$HAS_NODE" = true ]; then
        echo -e "  ${YELLOW}⚠${NC} npm not found"
    fi
fi

# Check curl
if command -v curl >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} curl        ${CYAN}(available)${NC}"
else
    echo -e "  ${RED}✗${NC} curl not found - REQUIRED"
    exit 1
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 2: LOAD ENVIRONMENT
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[2/10] ENVIRONMENT CONFIGURATION${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

if [ -f "$ROOT_DIR/.env" ]; then
    set -a
    source "$ROOT_DIR/.env"
    set +a
    echo -e "  ${GREEN}✓${NC} Loaded .env configuration"

    # Verify critical keys
    if [ -n "$NVIDIA_API_KEY" ]; then
        echo -e "  ${GREEN}✓${NC} NVIDIA API Key configured"
    else
        echo -e "  ${YELLOW}⚠${NC} NVIDIA API Key not set"
    fi

    if [ -n "$ASTRA_DB_API_ENDPOINT" ]; then
        echo -e "  ${GREEN}✓${NC} Astra DB configured"
    else
        echo -e "  ${YELLOW}⚠${NC} Astra DB not configured"
    fi

    if [ -n "$MATON_API_KEY" ]; then
        echo -e "  ${GREEN}✓${NC} Maton API Key configured"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} No .env file found - using system environment"
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 3: CLEANUP OLD PROCESSES
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[3/10] CLEANUP${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

CLEANED=false

if pgrep -f "uvicorn lumenis-main" > /dev/null; then
    pkill -f "uvicorn lumenis-main"
    echo -e "  ${YELLOW}○${NC} Stopped: Lumenis Reactor"
    CLEANED=true
fi

if pgrep -f "ai_lobby.py" > /dev/null; then
    pkill -f "ai_lobby.py"
    echo -e "  ${YELLOW}○${NC} Stopped: AI Lobby"
    CLEANED=true
fi

if pgrep -f "watchdog.py" > /dev/null; then
    pkill -f "watchdog.py"
    echo -e "  ${YELLOW}○${NC} Stopped: Watchdog"
    CLEANED=true
fi

if pgrep -f "minimax.*index.js" > /dev/null; then
    pkill -f "minimax.*index.js"
    echo -e "  ${YELLOW}○${NC} Stopped: Minimax"
    CLEANED=true
fi

if pgrep -f "network-api.js" > /dev/null; then
    pkill -f "network-api.js"
    echo -e "  ${YELLOW}○${NC} Stopped: Network Service"
    CLEANED=true
fi

if pgrep -f "onworks_keepalive" > /dev/null; then
    pkill -f "onworks_keepalive"
    echo -e "  ${YELLOW}○${NC} Stopped: OnWorks Keepalive"
    CLEANED=true
fi

if [ "$CLEANED" = false ]; then
    echo -e "  ${GREEN}✓${NC} No processes to clean up"
fi

sleep 1
echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 4: CREATE DIRECTORIES
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[4/10] DIRECTORY SETUP${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

mkdir -p "$ROOT_DIR/logs"
mkdir -p "$ROOT_DIR/config"
mkdir -p "$ROOT_DIR/data"

echo -e "  ${GREEN}✓${NC} Created logs directory"
echo -e "  ${GREEN}✓${NC} Created config directory"
echo -e "  ${GREEN}✓${NC} Created data directory"
echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 5: START LUMENIS REACTOR CORE
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[5/10] LUMENIS REACTOR CORE${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

if [ -f "$ROOT_DIR/lumenis-main.py" ]; then
    echo -e "  ${BLUE}→${NC} Starting Lumenis Reactor (port 8000)..."

    nohup python3 -m uvicorn lumenis-main:app --host 0.0.0.0 --port 8000 \
        > "$ROOT_DIR/logs/reactor.log" 2>&1 &
    REACTOR_PID=$!

    echo -e "  ${CYAN}○${NC} Process ID: $REACTOR_PID"
    sleep 4

    if curl -s --max-time 5 http://localhost:8000/api/status >/dev/null 2>&1; then
        MODEL=$(curl -s http://localhost:8000/api/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['reactor']['model'].split('/')[-1])" 2>/dev/null || echo "Unknown")
        echo -e "  ${GREEN}✓${NC} Reactor ONLINE - Model: ${CYAN}$MODEL${NC}"
    else
        echo -e "  ${YELLOW}⚠${NC} Reactor starting (check logs/reactor.log)"
    fi
else
    echo -e "  ${RED}✗${NC} lumenis-main.py not found"
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 6: START WATCHDOG
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[6/10] WATCHDOG SERVICE${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

if [ -f "$ROOT_DIR/watchdog.py" ]; then
    nohup python3 "$ROOT_DIR/watchdog.py" > "$ROOT_DIR/logs/watchdog.log" 2>&1 &
    WATCHDOG_PID=$!
    echo -e "  ${GREEN}✓${NC} Watchdog started (PID: $WATCHDOG_PID)"
else
    echo -e "  ${YELLOW}⚠${NC} watchdog.py not found - skipped"
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 7: START AI LOBBY
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[7/10] AI LOBBY${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

if [ -f "$ROOT_DIR/ai_lobby.py" ]; then
    echo -e "  ${BLUE}→${NC} Starting AI Lobby (port 8006)..."

    nohup python3 "$ROOT_DIR/ai_lobby.py" \
        > "$ROOT_DIR/logs/lobby.log" 2>&1 &
    LOBBY_PID=$!

    echo -e "  ${CYAN}○${NC} Process ID: $LOBBY_PID"
    sleep 3

    if curl -s --max-time 5 http://localhost:8006/ >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} AI Lobby ONLINE"

        # Auto-register Lumenis
        if curl -s --max-time 5 http://localhost:8000/api/status >/dev/null 2>&1; then
            curl -s -X POST http://localhost:8000/api/tools/lobby/register \
                -H "Content-Type: application/json" -d '{}' >/dev/null 2>&1 || true
            echo -e "  ${GREEN}✓${NC} Lumenis registered in lobby"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Lobby starting (check logs/lobby.log)"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} ai_lobby.py not found - skipped"
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 8: LOAD SEMANTIC LAYER
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[8/10] SEMANTIC LAYER${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

if [ -d "$ROOT_DIR/semantic_layer" ]; then
    echo -e "  ${BLUE}→${NC} Loading ontologies..."

    # Check if ontologies exist
    ONTOLOGY_COUNT=0
    if [ -f "$ROOT_DIR/semantic_layer/ontologies/rdf-schema.ttl" ]; then
        ((ONTOLOGY_COUNT++))
    fi
    if [ -f "$ROOT_DIR/semantic_layer/ontologies/one2lvos-ontology.ttl" ]; then
        ((ONTOLOGY_COUNT++))
    fi

    echo -e "  ${GREEN}✓${NC} Found $ONTOLOGY_COUNT ontologies"
    echo -e "  ${GREEN}✓${NC} Semantic layer ready"
else
    echo -e "  ${YELLOW}⚠${NC} semantic_layer directory not found - skipped"
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 9: START ADDITIONAL SERVICES
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[9/10] ADDITIONAL SERVICES${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

# Minimax AI
if [ -d "$ROOT_DIR/minimax/node_modules" ] && [ "$HAS_NODE" = true ]; then
    echo -e "  ${BLUE}→${NC} Starting Minimax AI (port 8080)..."
    cd "$ROOT_DIR/minimax"
    nohup node index.js > "$ROOT_DIR/logs/minimax.log" 2>&1 &
    MINIMAX_PID=$!
    echo -e "  ${CYAN}○${NC} Process ID: $MINIMAX_PID"
    sleep 2
    cd "$ROOT_DIR"

    if curl -s --max-time 3 http://localhost:8080/ >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Minimax ONLINE"
    else
        echo -e "  ${YELLOW}⚠${NC} Minimax starting"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Minimax skipped (run: cd minimax && npm install)"
fi

# Aetherix Browser OS
if [ -f "$ROOT_DIR/Aetherix/server.py" ]; then
    echo -e "  ${BLUE}→${NC} Starting Aetherix Browser OS (port 8086)..."
    cd "$ROOT_DIR/Aetherix"
    nohup python3 server.py > "$ROOT_DIR/logs/aetherix.log" 2>&1 &
    echo -e "  ${CYAN}○${NC} Process ID: $!"
    sleep 2
    cd "$ROOT_DIR"

    if curl -s --max-time 3 http://localhost:8086/ >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Aetherix ONLINE"
    else
        echo -e "  ${YELLOW}⚠${NC} Aetherix starting"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Aetherix not found - skipped"
fi

# ARIA Agent
if [ -f "$ROOT_DIR/aria/main.py" ]; then
    echo -e "  ${BLUE}→${NC} Starting ARIA Agent (port 8088)..."
    cd "$ROOT_DIR/aria"
    pip3 install -q -r requirements.txt 2>/dev/null || true
    nohup python3 main.py > "$ROOT_DIR/logs/aria.log" 2>&1 &
    echo -e "  ${CYAN}○${NC} Process ID: $!"
    sleep 2
    cd "$ROOT_DIR"

    if curl -s --max-time 3 http://localhost:8088/ >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} ARIA ONLINE"
    else
        echo -e "  ${YELLOW}⚠${NC} ARIA starting"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} ARIA not found - skipped"
fi

# Sovereign Agentic Core
if [ -f "$ROOT_DIR/sovereign-agentic-core/main.py" ]; then
    echo -e "  ${BLUE}→${NC} Starting Sovereign Agentic Core (port 8081)..."
    cd "$ROOT_DIR/sovereign-agentic-core"
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8081 \
        > "$ROOT_DIR/logs/sovereign-core.log" 2>&1 &
    echo -e "  ${CYAN}○${NC} Process ID: $!"
    sleep 2
    cd "$ROOT_DIR"

    if curl -s --max-time 3 http://localhost:8081/ >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Sovereign Core ONLINE"
    else
        echo -e "  ${YELLOW}⚠${NC} Sovereign Core starting"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Sovereign Agentic Core not found - skipped"
fi

# Network Service
if [ -f "$ROOT_DIR/server/network-api.js" ] && [ "$HAS_NODE" = true ]; then
    echo -e "  ${BLUE}→${NC} Starting Network Service (port 3003)..."
    mkdir -p "$ROOT_DIR/config"
    [ ! -f "$ROOT_DIR/config/connections.json" ] && echo '{"connections":[]}' > "$ROOT_DIR/config/connections.json"

    export NETWORK_API_PORT=3003
    nohup node "$ROOT_DIR/server/network-api.js" > "$ROOT_DIR/logs/network.log" 2>&1 &
    echo -e "  ${CYAN}○${NC} Process ID: $!"
    sleep 2

    if curl -s --max-time 3 http://localhost:3003/ >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Network Service ONLINE"
    else
        echo -e "  ${YELLOW}⚠${NC} Network Service starting"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Network Service not found - skipped"
fi

# OnWorks Keepalive (optional)
if [ -f "$ROOT_DIR/onworks_keepalive.py" ] && [ "$ENABLE_ONWORKS_KEEPALIVE" = "true" ]; then
    echo -e "  ${BLUE}→${NC} Starting OnWorks Keepalive..."
    nohup python3 "$ROOT_DIR/onworks_keepalive.py" > "$ROOT_DIR/logs/keepalive.log" 2>&1 &
    echo -e "  ${GREEN}✓${NC} OnWorks Keepalive started"
fi

echo ""

# ──────────────────────────────────────────────────────────────────────────
# STEP 10: SYSTEM STATUS
# ──────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}${BOLD}[10/10] SYSTEM STATUS${NC}"
echo "────────────────────────────────────────────────────────────────────────────"

sleep 2

# Function to check service status
check_service() {
    local name=$1
    local port=$2
    local path=${3:-"/"}
    local url="http://localhost:$port$path"

    if curl -s --max-time 2 "$url" >/dev/null 2>&1; then
        printf "  ${GREEN}●${NC} %-35s ${CYAN}:%-6s${NC} ${GREEN}ONLINE${NC}\n" "$name" "$port"
        return 0
    else
        printf "  ${RED}●${NC} %-35s ${CYAN}:%-6s${NC} ${RED}OFFLINE${NC}\n" "$name" "$port"
        return 1
    fi
}

echo ""
check_service "Lumenis Reactor Core" 8000 "/api/status"
check_service "AI Lobby" 8006 "/"
check_service "Minimax AI" 8080 "/"
check_service "Aetherix Browser OS" 8086 "/"
check_service "ARIA Agent" 8088 "/"
check_service "Sovereign Agentic Core" 8081 "/"
check_service "Network Service" 3003 "/"

echo ""
echo "────────────────────────────────────────────────────────────────────────────"
echo ""

# ──────────────────────────────────────────────────────────────────────────
# FINAL BANNER
# ──────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                          ║"
echo "║                    ONE2LVOS SYSTEM READY                                ║"
echo "║                                                                          ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                          ║"
echo "║  🌐 Primary Interfaces:                                                 ║"
echo "║                                                                          ║"
echo -e "║     ${CYAN}Lumenis Chat:${NC}${GREEN}     http://localhost:8000/lumenis-chat            ${GREEN}║${NC}"
echo -e "║     ${CYAN}AI Lobby:${NC}${GREEN}         http://localhost:8006/                       ${GREEN}║${NC}"
echo -e "║     ${CYAN}Network Manager:${NC}${GREEN}  http://localhost:3003/network-manager.html    ${GREEN}║${NC}"
echo "║                                                                          ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                          ║"
echo "║  📊 Monitoring & Logs:                                                  ║"
echo "║                                                                          ║"
echo -e "║     ${YELLOW}View all logs:${NC}${GREEN}    tail -f logs/*.log                          ${GREEN}║${NC}"
echo -e "║     ${YELLOW}Reactor log:${NC}${GREEN}      tail -f logs/reactor.log                    ${GREEN}║${NC}"
echo -e "║     ${YELLOW}Lobby log:${NC}${GREEN}        tail -f logs/lobby.log                      ${GREEN}║${NC}"
echo "║                                                                          ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                          ║"
echo "║  🛑 Shutdown:                                                           ║"
echo "║                                                                          ║"
echo -e "║     ${RED}./stop-all.sh${NC}${GREEN}     (Graceful shutdown of all services)           ${GREEN}║${NC}"
echo "║                                                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${BOLD}${CYAN}One2lvOS is now running. Welcome to the sovereign architecture.${NC}"
echo ""
