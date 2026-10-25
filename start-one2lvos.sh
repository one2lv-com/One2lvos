#!/bin/bash
# One2lvOS Unified Startup Script
# Optimized for restricted environments (no root/sudo required)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

ROOT_DIR="$HOME/One2lvos"
LOG_DIR="$ROOT_DIR/logs"

# Create log directory
mkdir -p "$LOG_DIR"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           ONE2LVOS UNIFIED STARTUP SEQUENCE                   ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if services are already running
if pgrep -f "lumenis-main.py" > /dev/null || pgrep -f "lumenis_reactor" > /dev/null; then
    echo -e "${YELLOW}⚠ Lumenis Reactor already running. Stopping first...${NC}"
    pkill -f "lumenis-main.py" 2>/dev/null || true
    pkill -f "lumenis_reactor" 2>/dev/null || true
    sleep 2
fi

cd "$ROOT_DIR"

# Check .env file
echo -e "${CYAN}[1/5] Configuration Check${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}  .env not found, creating from .env.master...${NC}"
    if [ -f ".env.master" ]; then
        cp .env.master .env
        echo -e "${GREEN}  ✓ .env created${NC}"
    else
        echo -e "${RED}  ✗ .env.master not found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}  ✓ .env file exists${NC}"
fi
echo ""

# Install Python dependencies
echo -e "${CYAN}[2/5] Installing Python Dependencies${NC}"
pip install -q -r requirements.txt 2>&1 | tee "$LOG_DIR/pip-install.log" | grep -E "Successfully|Requirement|ERROR" || true
echo -e "${GREEN}  ✓ Python packages ready${NC}"
echo ""

# Install Node.js dependencies (if needed)
echo -e "${CYAN}[3/5] Installing Node.js Dependencies${NC}"
if [ ! -d "node_modules" ]; then
    npm install --silent 2>&1 | tee "$LOG_DIR/npm-install.log"
    echo -e "${GREEN}  ✓ Node modules installed${NC}"
else
    echo -e "${GREEN}  ✓ Node modules already installed${NC}"
fi
echo ""

# Start Lumenis Reactor Core (Python backend)
echo -e "${CYAN}[4/5] Starting Lumenis Reactor Core${NC}"
cd "$ROOT_DIR"
nohup python3 lumenis-main.py > "$LOG_DIR/lumenis-reactor.log" 2>&1 &
LUMENIS_PID=$!
echo -e "${GREEN}  ✓ Lumenis Reactor started (PID: $LUMENIS_PID)${NC}"
echo -e "${YELLOW}  Log: $LOG_DIR/lumenis-reactor.log${NC}"
echo ""

# Wait for Lumenis to be ready
echo -e "${CYAN}  Waiting for Lumenis Reactor to initialize...${NC}"
sleep 5

# Check if Lumenis is responding
for i in {1..10}; do
    if curl -s http://localhost:3002/health > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Lumenis Reactor is responding${NC}"
        break
    elif [ $i -eq 10 ]; then
        echo -e "${RED}  ✗ Lumenis Reactor failed to start${NC}"
        echo -e "${YELLOW}  Check log: tail -f $LOG_DIR/lumenis-reactor.log${NC}"
        exit 1
    else
        echo -e "${YELLOW}  Attempt $i/10...${NC}"
        sleep 2
    fi
done
echo ""

# Start Node.js Frontend Gateway
echo -e "${CYAN}[5/5] Starting Frontend Gateway${NC}"
cd "$ROOT_DIR/lumenis_reactor_core"
nohup node server.js > "$LOG_DIR/frontend-gateway.log" 2>&1 &
GATEWAY_PID=$!
echo -e "${GREEN}  ✓ Frontend Gateway started (PID: $GATEWAY_PID)${NC}"
echo -e "${YELLOW}  Log: $LOG_DIR/frontend-gateway.log${NC}"
echo ""

# Wait for gateway to be ready
sleep 3

# Final verification
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ ONE2LVOS SUCCESSFULLY STARTED${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${MAGENTA}Access Points:${NC}"
echo -e "  ${GREEN}Lumenis Chat UI:${NC}       http://localhost:9000"
echo -e "  ${GREEN}Reactor Core API:${NC}      http://localhost:3002"
echo -e "  ${GREEN}Frontend Gateway:${NC}      http://localhost:9000"
echo ""
echo -e "${MAGENTA}Process IDs:${NC}"
echo -e "  Lumenis Reactor: $LUMENIS_PID"
echo -e "  Frontend Gateway: $GATEWAY_PID"
echo ""
echo -e "${MAGENTA}Logs:${NC}"
echo -e "  ${YELLOW}tail -f $LOG_DIR/lumenis-reactor.log${NC}"
echo -e "  ${YELLOW}tail -f $LOG_DIR/frontend-gateway.log${NC}"
echo ""
echo -e "${MAGENTA}To stop:${NC}"
echo -e "  ${YELLOW}./stop-one2lvos.sh${NC}"
echo ""
