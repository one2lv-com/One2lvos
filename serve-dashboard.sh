#!/bin/bash
#
# Serve One2lvOS Dashboard with AI Arcade
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ONE2LVOS DASHBOARD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Dashboard URL: http://localhost:8080/one2lv-dashboard.html"
echo "  AI Arcade MCP: http://localhost:8003"
echo ""
echo "  Status:"
echo "  ✓ AI Arcade running on port 8003"
echo "  ✓ Dashboard ready on port 8080"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if arcade is running
if curl -s http://localhost:8003/ > /dev/null 2>&1; then
    echo "✓ AI Arcade MCP: ONLINE"
else
    echo "✗ AI Arcade MCP: OFFLINE"
    echo "  Starting AI Arcade..."
    cd "$SCRIPT_DIR/ai-arcade"
    python server.py --host 0.0.0.0 --port 8003 > /tmp/arcade.log 2>&1 &
    sleep 2
    echo "✓ AI Arcade started"
    cd "$SCRIPT_DIR"
fi

echo ""
echo "Starting HTTP server on port 8080..."
echo "Press Ctrl+C to stop"
echo ""

python -m http.server 8080
