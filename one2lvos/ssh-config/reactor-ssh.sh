#!/bin/bash
# ============================================================================
# ONE2LVOS - SSH EMBEDDED PATH FOR LUMENIS REACTOR CORE
# ============================================================================
# Secure SSH tunnel configuration for remote Reactor Core access

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
echo "║       🔐 ONE2LVOS SSH EMBEDDED PATH - REACTOR CORE                  ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Configuration
SSH_CONFIG_DIR="$HOME/.ssh"
REACTOR_SSH_DIR="$(dirname "$0")"
REACTOR_HOST="${REACTOR_HOST:-reactor.one2lv.local}"
REACTOR_PORT="${REACTOR_PORT:-8100}"
SSH_PORT="${SSH_PORT:-22}"
SSH_USER="${SSH_USER:-one2lv}"

# Create SSH config directory if not exists
mkdir -p "$SSH_CONFIG_DIR"
chmod 700 "$SSH_CONFIG_DIR"

echo -e "${CYAN}📋 Configuration:${NC}"
echo "   Reactor Host: $REACTOR_HOST"
echo "   Reactor Port: $REACTOR_PORT"
echo "   SSH Port: $SSH_PORT"
echo "   SSH User: $SSH_USER"
echo ""

# Generate SSH key if not exists
if [ ! -f "$SSH_CONFIG_DIR/one2lv_reactor_rsa" ]; then
    echo -e "${YELLOW}🔑 Generating SSH key pair...${NC}"
    ssh-keygen -t rsa -b 4096 -f "$SSH_CONFIG_DIR/one2lv_reactor_rsa" -N "" -C "one2lv-reactor-core"
    echo -e "${GREEN}✅ SSH key pair generated${NC}"
else
    echo -e "${GREEN}✅ SSH key pair already exists${NC}"
fi

# Create SSH config entry
echo -e "${CYAN}⚙️  Configuring SSH...${NC}"

SSH_CONFIG="$SSH_CONFIG_DIR/config"
CONFIG_ENTRY="
# One2lvOS Reactor Core SSH Configuration
Host reactor-core
    HostName $REACTOR_HOST
    User $SSH_USER
    Port $SSH_PORT
    IdentityFile ~/.ssh/one2lv_reactor_rsa
    ServerAliveInterval 60
    ServerAliveCountMax 3
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

Host reactor-tunnel
    HostName $REACTOR_HOST
    User $SSH_USER
    Port $SSH_PORT
    IdentityFile ~/.ssh/one2lv_reactor_rsa
    LocalForward 8100 localhost:8100
    LocalForward 4000 localhost:4000
    LocalForward 8787 localhost:8787
    LocalForward 5353 localhost:5353
    ServerAliveInterval 60
    ServerAliveCountMax 3
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
"

# Check if config already has reactor entry
if grep -q "Host reactor-core" "$SSH_CONFIG" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  SSH config already has reactor entry, skipping...${NC}"
else
    echo "$CONFIG_ENTRY" >> "$SSH_CONFIG"
    chmod 600 "$SSH_CONFIG"
    echo -e "${GREEN}✅ SSH config updated${NC}"
fi

# Display public key
echo ""
echo -e "${CYAN}🔑 Public Key (add to remote server):${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────────────${NC}"
cat "$SSH_CONFIG_DIR/one2lv_reactor_rsa.pub"
echo -e "${YELLOW}─────────────────────────────────────────────────────────────────────${NC}"
echo ""

echo -e "${CYAN}📝 Usage:${NC}"
echo ""
echo -e "${GREEN}1. Direct SSH Connection:${NC}"
echo "   ssh reactor-core"
echo ""
echo -e "${GREEN}2. SSH Tunnel (Port Forwarding):${NC}"
echo "   ssh -N -f reactor-tunnel"
echo "   This forwards:"
echo "     - Reactor Core API (8100)"
echo "     - UI Server (4000)"
echo "     - AI Lobby (8787)"
echo "     - DNS Gateway (5353)"
echo ""
echo -e "${GREEN}3. Copy public key to remote:${NC}"
echo "   ssh-copy-id -i ~/.ssh/one2lv_reactor_rsa.pub $SSH_USER@$REACTOR_HOST"
echo ""
echo -e "${GREEN}4. Test connection:${NC}"
echo "   ssh -T reactor-core"
echo ""

echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                  SSH CONFIGURATION COMPLETE                          ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════╝${NC}"
