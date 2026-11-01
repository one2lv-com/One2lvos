#!/bin/bash
# Aether-Lumenis OS Launcher
# Unified startup script for the Sovereign Cognitive Operating System

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

ROOT_DIR="$HOME/One2lvos"
cd "$ROOT_DIR"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}║       ⚡ AETHER-LUMENIS OS v2.0 - TRINITY LAUNCHER ⚡        ║${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python: $PYTHON_VERSION"

# Check if script exists
if [ ! -f "aether_lumenis_os.py" ]; then
    echo -e "${RED}✗${NC} aether_lumenis_os.py not found!"
    exit 1
fi
echo -e "${GREEN}✓${NC} Aether-Lumenis OS: Found"

echo ""
echo -e "${MAGENTA}[System Components]${NC}"
echo -e "  • O2PNG State Capsule Protocol (v1.0)"
echo -e "  • LSB Steganographic Bootloader"
echo -e "  • Lumenis Cognitive Reactor"
echo -e "  • Sovereign Multi-Agent Council"
echo -e "  • Interplanetary VFS & VectorFS"
echo -e "  • Aetherix Terminal Shell"
echo ""

echo -e "${YELLOW}Starting Aether-Lumenis OS...${NC}"
echo ""

# Launch OS
python3 aether_lumenis_os.py

echo ""
echo -e "${GREEN}✓ Aether-Lumenis OS terminated gracefully${NC}"
