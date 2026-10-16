#!/bin/bash
# ============================================================================
# ONE2LVOS REACTOR CORE WITH DNS GATEWAY - STARTUP SCRIPT
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${MAGENTA}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║       🌐 ONE2LVOS REACTOR CORE WITH DNS GATEWAY                     ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Navigate to project directory
cd "$(dirname "$0")"

echo -e "${CYAN}🔧 [1/4] Checking environment...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Environment configured${NC}"

echo ""
echo -e "${CYAN}🔍 [2/4] Testing DNS Gateway...${NC}"
python3 core/dns_gateway.py
echo ""

echo -e "${CYAN}⚡ [3/4] Starting Reactor Core with DNS Gateway...${NC}"
PORT=${PORT:-8000}

# Kill any existing process on the port
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $PORT in use, cleaning up...${NC}"
    kill -9 $(lsof -t -i:$PORT) 2>/dev/null || true
    sleep 1
fi

echo -e "${GREEN}🚀 Launching Reactor Core on port $PORT...${NC}"
nohup python3 core/reactor_core.py > logs/reactor_core.log 2>&1 &
REACTOR_PID=$!

# Wait for service to start
echo -e "${CYAN}⏳ Waiting for services to initialize...${NC}"
sleep 3

echo ""
echo -e "${CYAN}🏥 [4/4] Health Check...${NC}"
if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Reactor Core: ONLINE${NC}"
else
    echo -e "${RED}❌ Reactor Core: FAILED TO START${NC}"
    echo -e "${YELLOW}Check logs: tail -f logs/reactor_core.log${NC}"
    exit 1
fi

echo ""
echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║         🎉 ONE2LVOS REACTOR CORE - OPERATIONAL 🎉                   ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📡 REACTOR CORE API${NC}"
echo -e "   → http://localhost:$PORT"
echo ""
echo -e "${GREEN}🌐 DNS GATEWAY ENDPOINTS${NC}"
echo -e "   → List Domains:        http://localhost:$PORT/dns/list"
echo -e "   → Resolve Domain:      http://localhost:$PORT/dns/resolve/{domain}"
echo -e "   → Register Service:    http://localhost:$PORT/dns/register"
echo -e "   → Gateway Status:      http://localhost:$PORT/dns/status"
echo -e "   → Export Hosts File:   http://localhost:$PORT/dns/hosts"
echo ""
echo -e "${GREEN}🧠 MEMORY & AI ENDPOINTS${NC}"
echo -e "   → Chat with AI:        POST http://localhost:$PORT/chat"
echo -e "   → Store Memory:        POST http://localhost:$PORT/memory/store"
echo -e "   → Recall Memory:       POST http://localhost:$PORT/memory/recall"
echo ""
echo -e "${GREEN}🔍 SERVICE DISCOVERY${NC}"
echo -e "   → List Services:       http://localhost:$PORT/services"
echo -e "   → Health Check:        http://localhost:$PORT/health"
echo ""
echo -e "${CYAN}💾 LOGS${NC}"
echo -e "   → Reactor Core:        tail -f logs/reactor_core.log"
echo ""
echo -e "${YELLOW}⏹️  STOP SERVICES${NC}"
echo -e "   → Kill reactor:        kill $REACTOR_PID"
echo -e "   → Kill all:            pkill -9 python3 && pkill -9 node"
echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════${NC}"
