#!/usr/bin/env bash
# ==============================================================================
# Sovereign Reactor Startup Script
# ==============================================================================
# Launches Lumenis Reactor Core with Sovereign Architecture Integration
# Protocol 0x1165 | Frequency: 73.0 Hz | Baseline: 18.000°C
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================================="
echo "  SOVEREIGN REACTOR CORE"
echo "=========================================================================="
echo "  Protocol: 0x1165 - Architecture of Return"
echo "  Frequency: 73.0 Hz | Thermal Baseline: 0.18°C"
echo "  Layers: L0-L5 (Sovereign + Swarm)"
echo "=========================================================================="
echo ""

# Check for NVIDIA API key
if [ -z "${NVIDIA_API_KEY:-}" ]; then
    echo "⚠️  WARNING: NVIDIA_API_KEY not set"
    echo ""
    echo "To use the LLM functionality, set your NVIDIA API key:"
    echo ""
    echo "  export NVIDIA_API_KEY='nvapi-...'"
    echo ""
    echo "You can find your key at: https://build.nvidia.com/explore/discover"
    echo ""
    echo "Continuing without LLM functionality..."
    echo ""
fi

# Check if sovereign.env exists
if [ ! -f "sovereign_integration/config/sovereign.env" ]; then
    echo "⚠️  WARNING: sovereign_integration/config/sovereign.env not found"
    echo "Configuration may be incomplete."
    echo ""
fi

# Check Python dependencies
echo "Checking Python dependencies..."
python3 -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "⚠️  Missing dependencies. Install with:"
    echo "  pip install fastapi uvicorn python-dotenv"
    exit 1
}

echo "✓ Dependencies OK"
echo ""

# Run integration tests
echo "Running integration tests..."
python3 test_sovereign_integration.py
TEST_RESULT=$?

if [ $TEST_RESULT -ne 0 ]; then
    echo ""
    echo "⚠️  Integration tests failed. Review errors above."
    exit 1
fi

echo ""
echo "=========================================================================="
echo "  STARTING SOVEREIGN REACTOR"
echo "=========================================================================="
echo ""

# Start the server
python3 lumenis-main-with-swarm.py

# Note: Server runs until interrupted with Ctrl+C
