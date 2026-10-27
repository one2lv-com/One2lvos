#!/usr/bin/env bash
# ============================================================================
# CONTINUOUS SYNC DAEMON
# ============================================================================
# Monitors changes and auto-syncs every 5 minutes
# Run as: nohup ./continuous_sync_daemon.sh > sync.log 2>&1 &

set -euo pipefail

REPO_DIR="/home/vercel-sandbox/One2lvos-build"
INTERVAL=300  # 5 minutes

echo "🌊 CONTINUOUS SYNC DAEMON STARTED"
echo "   Interval: ${INTERVAL}s (5 min)"
echo "   Targets: one2mind, vfslv-com"
echo ""

cd "$REPO_DIR"

while true; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 [$(date -Iseconds)] Sync cycle starting..."

    # Sync to one2mind
    if ./sync_to_one2mind.sh; then
        echo "✅ one2mind sync OK"
    else
        echo "⚠️  one2mind sync failed"
    fi

    sleep 2

    # Sync to vfslv
    if ./sync_to_vfslv.sh; then
        echo "✅ vfslv sync OK"
    else
        echo "⚠️  vfslv sync failed"
    fi

    echo "💤 Sleeping for ${INTERVAL}s..."
    echo ""
    sleep "$INTERVAL"
done
