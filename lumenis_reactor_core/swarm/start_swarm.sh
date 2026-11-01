#!/usr/bin/env bash
set -euo pipefail

echo "🧠 ACTIVATING SWARM EXECUTION LAYER..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure directories exist
mkdir -p workers
mkdir -p tasks
mkdir -p runtime

# Kill any existing swarm processes
pkill -f "worker_node.py" || true
pkill -f "task_pulse.py" || true
pkill -f "swarm_monitor.py" || true

echo "📁 Directories ready"
echo "🧠 Launching swarm components..."

# Start 3 worker nodes in background
python3 worker_node.py &
WORKER1_PID=$!
echo "  ✓ Worker 1 started (PID: $WORKER1_PID)"

sleep 0.5

python3 worker_node.py &
WORKER2_PID=$!
echo "  ✓ Worker 2 started (PID: $WORKER2_PID)"

sleep 0.5

python3 worker_node.py &
WORKER3_PID=$!
echo "  ✓ Worker 3 started (PID: $WORKER3_PID)"

sleep 1

# Start task pulse generator
python3 task_pulse.py &
PULSE_PID=$!
echo "  ✓ Task Pulse started (PID: $PULSE_PID)"

sleep 1

# Start monitor in foreground
echo ""
echo "🚀 SWARM EXECUTION LAYER ACTIVE"
echo "   Workers: 3"
echo "   Pulse: Active"
echo "   Monitor: Starting..."
echo ""

# Trap cleanup
cleanup() {
    echo ""
    echo "🛑 Shutting down swarm..."
    kill $WORKER1_PID $WORKER2_PID $WORKER3_PID $PULSE_PID 2>/dev/null || true
    echo "✓ Swarm offline"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Run monitor
python3 swarm_monitor.py

cleanup
