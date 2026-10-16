#!/bin/bash
# ============================================================================
# ONE2LVOS - START ALL SERVICES
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

cd "$(dirname "$0")"

echo -e "${MAGENTA}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║       🚀 ONE2LVOS - STARTING ALL SERVICES                           ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Kill any existing processes
echo -e "${YELLOW}🔄 Cleaning up existing processes...${NC}"
pkill -9 -f "python3 core/reactor_core.py" 2>/dev/null || true
pkill -9 -f "node ui/server.js" 2>/dev/null || true
sleep 1

# Start Reactor Core
echo -e "${CYAN}🔋 [1/2] Starting Reactor Core...${NC}"
PORT=8100 python3 core/reactor_core.py > logs/reactor_core.log 2>&1 &
REACTOR_PID=$!
echo "   PID: $REACTOR_PID"
sleep 3

# Check Reactor Core
if curl -s http://localhost:8100/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Reactor Core: ONLINE${NC}"
else
    echo -e "${RED}❌ Reactor Core failed to start${NC}"
    exit 1
fi

# Start UI Server
echo -e "${CYAN}🌐 [2/2] Starting UI Server...${NC}"
cd ui
UI_PORT=4000 REACTOR_URL=http://localhost:8100 node server.js > ../logs/ui_server.log 2>&1 &
UI_PID=$!
echo "   PID: $UI_PID"
cd ..
sleep 2

# Check UI Server
if curl -s http://localhost:4000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ UI Server: ONLINE${NC}"
else
    echo -e "${RED}❌ UI Server failed to start${NC}"
fi

echo ""
echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                  🎉 ALL SERVICES ONLINE 🎉                           ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}📡 SERVICES${NC}"
echo "   🔋 Reactor Core API:  http://localhost:8100"
echo "   🌐 UI Dashboard:      http://localhost:4000"
echo "   🌐 DNS Gateway:       http://localhost:8100/dns/list"
echo "   🤖 AI Chat:           http://localhost:8100/chat (POST)"
echo ""

echo -e "${CYAN}💾 LOGS${NC}"
echo "   Reactor Core:  tail -f logs/reactor_core.log"
echo "   UI Server:     tail -f logs/ui_server.log"
echo ""

echo -e "${YELLOW}⏹️  STOP SERVICES${NC}"
echo "   Kill all:      pkill -9 python3 && pkill -9 node"
echo "   Reactor only:  kill $REACTOR_PID"
echo "   UI only:       kill $UI_PID"
echo ""

echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════════════${NC}"
