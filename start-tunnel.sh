#!/bin/bash
# Starts the Cloudflare Tunnel connector (tunnel "one2lvos") that serves
# one2lv.com -> AI Lobby (http://localhost:8006), behind Cloudflare Access.
# Reads CLOUDFLARE_TUNNEL_TOKEN from .env. Never commit the token.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ] && [ -f "$ROOT_DIR/.env" ]; then
    CLOUDFLARE_TUNNEL_TOKEN=$(grep -E '^CLOUDFLARE_TUNNEL_TOKEN=' "$ROOT_DIR/.env" | tail -1 | cut -d= -f2-)
fi

if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
    echo "CLOUDFLARE_TUNNEL_TOKEN not set - tunnel skipped"
    exit 0
fi

CLOUDFLARED="$(command -v cloudflared || echo "$HOME/.local/bin/cloudflared")"
if [ ! -x "$CLOUDFLARED" ]; then
    echo "cloudflared not installed - tunnel skipped"
    exit 0
fi

mkdir -p "$ROOT_DIR/logs"
pkill -f "cloudflared tunnel .*run" 2>/dev/null || true
sleep 1

# Pass the token through the environment so it never shows in `ps`.
TUNNEL_TOKEN="$CLOUDFLARE_TUNNEL_TOKEN" nohup "$CLOUDFLARED" tunnel --no-autoupdate run \
    > "$ROOT_DIR/logs/cloudflared.log" 2>&1 &
echo $! > "$ROOT_DIR/logs/cloudflared.pid"
echo "cloudflared started (PID $(cat "$ROOT_DIR/logs/cloudflared.pid"))"
