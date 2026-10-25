#!/bin/bash
# One2lvOS System Status Checker
# Works in restricted environments (no root/sudo required)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           ONE2LVOS SYSTEM STATUS REPORT                       ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Environment Info
echo -e "${MAGENTA}[1] Environment Information${NC}"
echo -e "  User: $(whoami) (UID=$(id -u))"
echo -e "  Hostname: $(hostname)"
echo -e "  Kernel: $(uname -s) $(uname -r)"
echo -e "  Architecture: $(uname -m)"
echo ""

# Required Software
echo -e "${MAGENTA}[2] Required Software${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "  ${GREEN}✓${NC} Python3: $PYTHON_VERSION"
else
    echo -e "  ${RED}✗${NC} Python3: NOT FOUND"
fi

if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    echo -e "  ${GREEN}✓${NC} Node.js: $NODE_VERSION"
else
    echo -e "  ${RED}✗${NC} Node.js: NOT FOUND"
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version 2>&1)
    echo -e "  ${GREEN}✓${NC} npm: v$NPM_VERSION"
else
    echo -e "  ${RED}✗${NC} npm: NOT FOUND"
fi

echo -e "  ${YELLOW}ℹ${NC}  nginx: NOT REQUIRED (using Node.js Express gateway)"
echo ""

# Check Running Services
echo -e "${MAGENTA}[3] Running Services${NC}"
LUMENIS_RUNNING=$(ps aux | grep -E "lumenis-main.py|lumenis_reactor" | grep -v grep | wc -l)
NODE_SERVICES=$(ps aux | grep -E "node.*One2lvos" | grep -v grep | wc -l)

if [ "$LUMENIS_RUNNING" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Lumenis Reactor Core: RUNNING ($LUMENIS_RUNNING process(es))"
else
    echo -e "  ${YELLOW}○${NC} Lumenis Reactor Core: STOPPED"
fi

if [ "$NODE_SERVICES" -gt 0 ]; then
    echo -e "  ${GREEN}✓${NC} Node.js Services: RUNNING ($NODE_SERVICES process(es))"
else
    echo -e "  ${YELLOW}○${NC} Node.js Services: STOPPED"
fi
echo ""

# Check Ports
echo -e "${MAGENTA}[4] Port Status${NC}"
for port in 3002 8000 8787 9000; do
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "  ${GREEN}✓${NC} Port $port: LISTENING"
    else
        echo -e "  ${YELLOW}○${NC} Port $port: FREE"
    fi
done
echo ""

# Check Configuration
echo -e "${MAGENTA}[5] Configuration Files${NC}"
if [ -f "$HOME/One2lvos/.env" ]; then
    echo -e "  ${GREEN}✓${NC} .env file exists"
else
    echo -e "  ${YELLOW}○${NC} .env file missing (use .env.master as template)"
fi

if [ -f "$HOME/One2lvos/.env.master" ]; then
    echo -e "  ${GREEN}✓${NC} .env.master template found"
fi
echo ""

# Check Dependencies
echo -e "${MAGENTA}[6] Python Dependencies${NC}"
if python3 -c "import fastapi" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} fastapi installed"
else
    echo -e "  ${RED}✗${NC} fastapi missing"
fi

if python3 -c "import openai" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} openai SDK installed"
else
    echo -e "  ${RED}✗${NC} openai SDK missing"
fi
echo ""

# Disk Usage
echo -e "${MAGENTA}[7] Disk Usage${NC}"
df -h $HOME | tail -1 | awk '{print "  Used: "$3" / "$2" ("$5" full)"}'
echo ""

# Summary
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
if [ "$LUMENIS_RUNNING" -gt 0 ] && [ "$NODE_SERVICES" -gt 0 ]; then
    echo -e "${GREEN}STATUS: All systems operational ✓${NC}"
else
    echo -e "${YELLOW}STATUS: Services need to be started${NC}"
    echo -e "${YELLOW}RUN: ./start-one2lvos.sh${NC}"
fi
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
