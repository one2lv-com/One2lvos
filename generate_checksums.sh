#!/bin/bash
# Generate SHA-256 checksums for all release artifacts

set -e

CHECKSUM_FILE="CHECKSUMS.txt"

echo "Generating SHA-256 checksums..."
echo "# One2lv Unified OS v1.0.1 - Release Artifacts" > $CHECKSUM_FILE
echo "# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> $CHECKSUM_FILE
echo "# Platform: $(uname -s) $(uname -m)" >> $CHECKSUM_FILE
echo "" >> $CHECKSUM_FILE

# Find all artifacts
find . -type f \( -name "*.tar.gz" -o -name "*.zip" -o -name "*.py" -o -name "*.sh" \) \
  ! -path "./.git/*" ! -path "./node_modules/*" ! -name "generate_checksums.sh" \
  -exec sha256sum {} \; | sort -k2 >> $CHECKSUM_FILE

echo "Checksums written to $CHECKSUM_FILE"
cat $CHECKSUM_FILE
