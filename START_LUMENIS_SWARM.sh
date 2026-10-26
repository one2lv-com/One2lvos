#!/usr/bin/env bash
set -euo pipefail

echo "═══════════════════════════════════════════════════════════════════"
echo "🧠 LUMENIS REACTOR CORE + SWARM EXECUTION LAYER"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for required environment variables
if [ -z "${NVIDIA_API_KEY:-}" ]; then
    echo "⚠️  Warning: NVIDIA_API_KEY not set"
    echo "   Some features may not work without API key"
    echo ""
fi

# Ensure swarm directories exist
mkdir -p lumenis_reactor_core/swarm/workers
mkdir -p lumenis_reactor_core/swarm/tasks
mkdir -p lumenis_reactor_core/swarm/runtime

echo "✓ Swarm directories initialized"
echo ""

# Check for existing processes
if pgrep -f "lumenis-main" > /dev/null; then
    echo "⚠️  Lumenis server already running"
    echo "   Kill existing process? (y/n)"
    read -r response
    if [ "$response" = "y" ]; then
        pkill -f "lumenis-main" || true
        sleep 2
    else
        echo "   Aborting"
        exit 1
    fi
fi

echo "🚀 Starting Lumenis Reactor Core with Swarm..."
echo ""
echo "   Layers:"
echo "     L0: Reactor Core - Thermal baseline 0.18°C, 73ms heartbeat"
echo "     L1: Memory - FluxCompass (SQLite vector memory)"
echo "     L2: Council - ITT (Seven specialized agent seats)"
echo "     L3: Execution - VanguardNodePool (async parallel tasks)"
echo "     L4: Integration - MatonBridge (external API gateway)"
echo "     L5: Swarm - Distributed execution layer (5 workers)"
echo ""
echo "   API Endpoints:"
echo "     http://localhost:8000          - Main interface"
echo "     http://localhost:8000/hud      - Cyberpunk HUD"
echo "     http://localhost:8000/swarm-hud - Swarm visualization"
echo "     http://localhost:8000/api/status - System status"
echo "     http://localhost:8000/api/swarm/status - Swarm status"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Start the server
python3 lumenis-main-with-swarm.py

# Cleanup on exit
trap 'echo ""; echo "🛑 Shutting down Lumenis Reactor + Swarm..."; pkill -f "worker_node.py" || true; echo "✓ Shutdown complete"' EXIT
