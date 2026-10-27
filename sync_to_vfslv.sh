#!/usr/bin/env bash
# ============================================================================
# ONE2LVOS → VFSLV-COM LUMENIS SYNC
# ============================================================================
# This script syncs to github.com/vfslv-com/One2lvos for lumenis reactor
#
# Requires: GITHUB_TOKEN environment variable or in .env file

set -euo pipefail

REPO_DIR="/home/vercel-sandbox/One2lvos-build"

# Load GitHub token from environment or .env
if [ -z "${GITHUB_TOKEN:-}" ]; then
    if [ -f "$REPO_DIR/.env" ]; then
        GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$REPO_DIR/.env" | cut -d= -f2)
    fi
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "❌ Error: GITHUB_TOKEN not found"
    echo "Set it as: export GITHUB_TOKEN=ghp_your_token"
    echo "Or add to .env: GITHUB_TOKEN=ghp_your_token"
    exit 1
fi

VFSLV_REMOTE="https://${GITHUB_TOKEN}@github.com/one2lv-com/lumenis.git"

cd "$REPO_DIR"

echo "🧲 [LUMENIS SYNC] Starting sync to vfslv-com..."

# Ensure we have vfslv as remote
if ! git remote | grep -q "vfslv"; then
    echo "📡 Adding vfslv remote..."
    git remote add vfslv "$VFSLV_REMOTE"
fi

# Fetch latest
echo "📥 Fetching from vfslv..."
git fetch vfslv || true

# Commit any local changes
if [[ -n "$(git status --porcelain)" ]]; then
    echo "💾 Committing local changes..."
    git add -A
    git commit -m "🔧 Lumenis sync: $(date -Iseconds)

Vercel-sandbox → vfslv-com/One2lvos
" || true
fi

# Push to vfslv
echo "⬆️  Pushing to vfslv-com/One2lvos..."
git push vfslv main || true

echo "✅ [LUMENIS SYNC] Complete!"
echo "   Lumenis reactor: github.com/one2lv-com/lumenis"
