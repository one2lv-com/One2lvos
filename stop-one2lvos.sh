#!/bin/bash
# One2lvOS Shutdown Script

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}           ONE2LVOS SHUTDOWN SEQUENCE                          ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Stop Lumenis Reactor
echo -e "${YELLOW}Stopping Lumenis Reactor Core...${NC}"
if pgrep -f "lumenis-main.py" > /dev/null || pgrep -f "lumenis_reactor" > /dev/null; then
    pkill -f "lumenis-main.py" 2>/dev/null || true
    pkill -f "lumenis_reactor" 2>/dev/null || true
    echo -e "${GREEN}✓ Lumenis Reactor stopped${NC}"
else
    echo -e "${YELLOW}○ Lumenis Reactor was not running${NC}"
fi

# Stop Node.js services
echo -e "${YELLOW}Stopping Node.js services...${NC}"
if pgrep -f "node.*server.js" > /dev/null; then
    pkill -f "node.*server.js" 2>/dev/null || true
    echo -e "${GREEN}✓ Node.js services stopped${NC}"
else
    echo -e "${YELLOW}○ Node.js services were not running${NC}"
fi

# Wait for processes to terminate
sleep 2

# Verify shutdown
REMAINING=$(ps aux | grep -E "lumenis|One2lvos" | grep -v grep | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All One2lvOS services stopped successfully${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠ Warning: $REMAINING process(es) still running${NC}"
    echo -e "${YELLOW}Run: ps aux | grep -E 'lumenis|One2lvos' | grep -v grep${NC}"
fi

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
