#!/bin/bash
# ONE2LVOS Sovereign Architecture - Unified Shutdown Script

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛑 Shutting down ONE2LVOS Sovereign Architecture..."

# Stop PM2 processes
pm2 delete all 2>/dev/null || true

# Watchdog first, so it does not restart the reactor while we stop it
pkill -f "watchdog.py" 2>/dev/null || true

# Python services
pkill -f "uvicorn lumenis-main" 2>/dev/null || true
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "ai_lobby.py" 2>/dev/null || true
pkill -f "ai-arcade/server.py" 2>/dev/null || true
pkill -f "onworks_keepalive" 2>/dev/null || true
pkill -9 -f "python3 main.py" 2>/dev/null || true
for pid in $(pgrep -f "server.py" || true); do
    if [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$ROOT_DIR/Aetherix" ]; then
        kill "$pid" 2>/dev/null || true
    fi
done

# Node services
pkill -f "webdav_keepalive.sh" 2>/dev/null || true
pkill -f "bridge_keepalive.sh" 2>/dev/null || true
pkill -f "public_bridge.py" 2>/dev/null || true
pkill -f "discord_keepalive.sh" 2>/dev/null || true
pkill -f "discord_listener.py" 2>/dev/null || true
pkill -f "webdav_server.py" 2>/dev/null || true
pkill -f "network-api.js" 2>/dev/null || true
pkill -f "minimax.*index.js" 2>/dev/null || true
for pid in $(pgrep -f "node " || true); do
    case "$(readlink "/proc/$pid/cwd" 2>/dev/null)" in
        "$ROOT_DIR"|"$ROOT_DIR"/*) kill "$pid" 2>/dev/null || true ;;
    esac
done

# Stop Cloudflare Tunnel connector
pkill -f "cloudflared tunnel" 2>/dev/null || true

echo "✅ All processes terminated"
echo ""
echo "To restart: ./startos.sh"
