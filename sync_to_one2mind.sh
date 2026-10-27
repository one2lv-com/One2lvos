#!/usr/bin/env bash
# ============================================================================
# ONE2LVOS → ONE2MIND CONTINUOUS SYNC
# ============================================================================
# This script syncs One2lvos-build to github.com/one2mind
# Run as: ./sync_to_one2mind.sh
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

ONE2MIND_REMOTE="https://${GITHUB_TOKEN}@github.com/one2lv-com/one2mind.git"

cd "$REPO_DIR"

echo "🌊 [ONE2MIND SYNC] Starting sync..."

# Ensure we have one2mind as remote
if ! git remote | grep -q "one2mind"; then
    echo "📡 Adding one2mind remote..."
    git remote add one2mind "$ONE2MIND_REMOTE"
fi

# Fetch latest from origin and one2mind
echo "📥 Fetching from remotes..."
git fetch origin || true
git fetch one2mind || true

# Commit any local changes
if [[ -n "$(git status --porcelain)" ]]; then
    echo "💾 Committing local changes..."
    git add -A
    git commit -m "🔄 Auto-sync: $(date -Iseconds)

Vercel-sandbox sync to one2mind
" || true
fi

# Push to origin (one2lv-com)
echo "⬆️  Pushing to one2lv-com/One2lvos..."
git push origin main || true

# Push to one2mind
echo "⬆️  Pushing to one2mind/One2lvos..."
git push one2mind main --force || true

echo "✅ [ONE2MIND SYNC] Complete!"
echo "   one2lv-com: github.com/one2lv-com/One2lvos"
echo "   one2mind:   github.com/one2lv-com/one2mind"
