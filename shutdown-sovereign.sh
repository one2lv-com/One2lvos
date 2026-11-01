#!/bin/bash
# Graceful shutdown script for ONE2LVOS Sovereign Architecture

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/∆Gemini_Root∆"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Initiating Sovereign Architecture Shutdown...${NC}"

# Read PIDs if available
if [ -f "$ROOT_DIR/.core.pid" ]; then
    CORE_PID=$(cat "$ROOT_DIR/.core.pid")
    kill $CORE_PID 2>/dev/null && echo -e "${GREEN}✅ Lumenis Reactor Core stopped (PID: $CORE_PID)${NC}"
    rm "$ROOT_DIR/.core.pid"
fi

if [ -f "$ROOT_DIR/.ui.pid" ]; then
    UI_PID=$(cat "$ROOT_DIR/.ui.pid")
    kill $UI_PID 2>/dev/null && echo -e "${GREEN}✅ Infinity Glasses HUD stopped (PID: $UI_PID)${NC}"
    rm "$ROOT_DIR/.ui.pid"
fi

# Fallback: kill all python and node processes
pkill -9 python3 2>/dev/null
pkill -9 node 2>/dev/null

echo -e "${GREEN}✅ Sovereign Architecture shutdown complete${NC}"
