#!/usr/bin/env bash
# One2lvOS project tree setup
#
# Scripts now find the project root on their own (the folder they live in, or
# ONE2LVOS_ROOT if you set it), so no fixed install path, symlink or sudo is
# needed. This script only makes sure the runtime folders exist.
set -euo pipefail

ONE2LVOS_ROOT="${ONE2LVOS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

mkdir -p "$ONE2LVOS_ROOT/logs" "$ONE2LVOS_ROOT/data"

echo "One2lvOS project root: $ONE2LVOS_ROOT"
echo "Runtime folders ready: logs/, data/"
