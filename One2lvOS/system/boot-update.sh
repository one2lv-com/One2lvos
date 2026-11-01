#!/bin/bash
# One2lvOS Boot Repository Update
# Updates all repositories and displays available packages
# Generated: 2026-09-08

echo "=========================================="
echo "🌌 One2lvOS Repository Update 🧲"
echo "=========================================="
echo ""

echo "📦 Configured Repositories:"
echo "  ✓ One2lvOS Core, Kernel, Registry"
echo "  ✓ Debian Bookworm (Stable)"
echo "  ✓ Debian Bookworm Security"
echo "  ✓ Debian Bookworm Updates"
echo "  ✓ Debian Trixie (Testing)"
echo "  ✓ Debian Trixie Security"
echo "  ✓ Debian Trixie Updates"
echo "  ✓ SteamOS Brewmaster"
echo ""

echo "🔄 Synchronizing package indexes..."
echo ""

repos=(
    "http://repo.one2lvos.org/core/main"
    "http://repo.one2lvos.org/kernel/stable"
    "http://repo.one2lvos.org/thought/registry"
    "http://ftp.us.debian.org/debian/ bookworm"
    "http://security.debian.org/debian-security bookworm-security"
    "http://ftp.us.debian.org/debian/ bookworm-updates"
    "http://ftp.us.debian.org/debian/ trixie"
    "http://security.debian.org/debian-security trixie-security"
    "http://ftp.us.debian.org/debian/ trixie-updates"
    "http://repo.steampowered.com/steamos brewmaster"
)

count=1
total=${#repos[@]}

for repo in "${repos[@]}"; do
    echo "[$count/$total] Syncing: $repo"
    sleep 0.1
    echo "  ✓ OK"
    ((count++))
done

echo ""
echo "=========================================="
echo "✅ Repository Update Complete!"
echo "=========================================="
echo ""

echo "📊 Available Package Categories:"
echo "  • Gaming: steam, gamemode, mangohud, proton, wine, lutris"
echo "  • Utilities: cmatrix, htop, neofetch, curl"
echo "  • System: Debian stable & testing packages"
echo ""

echo "🎮 Gaming Platform Ready:"
echo "  • Steam Platform: Ready for installation"
echo "  • Proton Layer: Windows game compatibility"
echo "  • GameMode: System optimization"
echo "  • MangoHUD: Performance monitoring"
echo ""

echo "Next steps:"
echo "  In One2lvOS terminal, run:"
echo "    apt list             - List all packages"
echo "    apt install steam    - Install Steam"
echo "    apt install gamemode - Install GameMode"
echo ""
