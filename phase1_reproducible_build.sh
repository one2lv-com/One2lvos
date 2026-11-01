#!/bin/bash
# Phase 1: Reproducible Build Implementation
# ==========================================

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          PHASE 1: REPRODUCIBLE BUILD                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

BUILD_ID=$(date +%s)
BUILD_DIR="build_${BUILD_ID}"
ARTIFACT_NAME="One2lv_Unified_OS_v1.0.2"

# Create clean build directory
echo "[BUILD] Creating clean build directory..."
mkdir -p "$BUILD_DIR"

# Copy source with deterministic ordering
echo "[BUILD] Copying source files..."
find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.md" -o -name "*.json" \
  -o -name "*.txt" -o -name "Dockerfile" \) \
  ! -path "./$BUILD_DIR/*" \
  ! -path "./.git/*" \
  ! -path "./__pycache__/*" \
  ! -path "*/build_*/*" \
  | sort | while read file; do
    target="$BUILD_DIR/$file"
    mkdir -p "$(dirname "$target")"
    cp "$file" "$target"
done

# Set deterministic timestamps
echo "[BUILD] Setting deterministic timestamps..."
find "$BUILD_DIR" -exec touch -t 202608200000 {} \;

# Create tarball with reproducible settings
echo "[BUILD] Creating reproducible tarball..."
tar --sort=name \
    --mtime='2026-08-20 00:00:00' \
    --owner=0 --group=0 --numeric-owner \
    -czf "${ARTIFACT_NAME}.tar.gz" \
    -C "$BUILD_DIR" .

# Generate checksum
CHECKSUM=$(sha256sum "${ARTIFACT_NAME}.tar.gz" | awk '{print $1}')
echo "[BUILD] ✓ Artifact created: ${ARTIFACT_NAME}.tar.gz"
echo "[BUILD] ✓ SHA-256: $CHECKSUM"

# Save build metadata
cat > "${ARTIFACT_NAME}_build.json" << METADATA
{
  "artifact": "${ARTIFACT_NAME}.tar.gz",
  "sha256": "$CHECKSUM",
  "build_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "build_id": "$BUILD_ID",
  "builder": "$(whoami)@$(hostname)",
  "platform": "$(uname -s) $(uname -m)",
  "reproducible": true
}
METADATA

echo ""
echo "✅ Reproducible build complete"
echo "   Artifact: ${ARTIFACT_NAME}.tar.gz"
echo "   Checksum: $CHECKSUM"

# Clean up build directory
rm -rf "$BUILD_DIR"
