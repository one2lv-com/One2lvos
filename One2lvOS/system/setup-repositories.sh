#!/bin/bash
# One2lvOS Repository Setup Script
# Configures Debian Trixie + SteamOS repositories
# Generated: 2026-09-08

set -e

echo "=========================================="
echo "One2lvOS Repository Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script must be run as root or with sudo"
    echo "Usage: sudo ./setup-repositories.sh"
    exit 1
fi

# Backup existing sources.list
if [ -f /etc/apt/sources.list ]; then
    echo "📦 Backing up existing sources.list..."
    cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d-%H%M%S)
    echo "✅ Backup created"
fi

# Copy One2lvOS sources configuration
echo ""
echo "📝 Installing One2lvOS repository configuration..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/apt-sources.list" ]; then
    cp "$SCRIPT_DIR/apt-sources.list" /etc/apt/sources.list
    echo "✅ Repository configuration installed"
else
    echo "❌ Error: apt-sources.list not found in $SCRIPT_DIR"
    exit 1
fi

# Add Steam GPG key
echo ""
echo "🔑 Adding Steam repository GPG key..."
if command -v wget &> /dev/null; then
    wget -qO - https://repo.steampowered.com/steam/archive/stable/steam.gpg | apt-key add - 2>/dev/null || true
    echo "✅ Steam GPG key added"
else
    echo "⚠️  wget not found, skipping GPG key (install wget and run again)"
fi

# Update package lists
echo ""
echo "🔄 Updating package lists..."
apt update

echo ""
echo "=========================================="
echo "✅ Repository Setup Complete!"
echo "=========================================="
echo ""
echo "Available repositories:"
echo "  ✓ Debian Trixie (main, contrib, non-free)"
echo "  ✓ Debian Security Updates"
echo "  ✓ Debian Stable Updates"
echo "  ✓ SteamOS (brewmaster)"
echo ""
echo "Next steps:"
echo "  1. Update system: sudo apt upgrade"
echo "  2. Install Steam: sudo apt install steam"
echo "  3. Install gaming tools: sudo apt install gamemode mangohud"
echo ""
echo "To restore previous configuration:"
echo "  sudo cp /etc/apt/sources.list.backup.* /etc/apt/sources.list"
echo ""
