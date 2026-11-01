#!/usr/bin/env bash
# Install the One2lvOS systemd units for this machine.
# The project root is detected from where this script lives, so the repo can be
# cloned anywhere. Run as the user who should own the services:
#   bash systemd/install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ONE2LVOS_ROOT="${ONE2LVOS_ROOT:-$(dirname "$SCRIPT_DIR")}"
ONE2LVOS_USER="${ONE2LVOS_USER:-$(id -un)}"

mkdir -p "$ONE2LVOS_ROOT/logs"

for unit in "$SCRIPT_DIR"/*.service; do
  name="$(basename "$unit")"
  tmp="$(mktemp)"
  sed -e "s#@ONE2LVOS_ROOT@#$ONE2LVOS_ROOT#g" -e "s#@ONE2LVOS_USER@#$ONE2LVOS_USER#g" "$unit" > "$tmp"
  sudo install -m 644 "$tmp" "/etc/systemd/system/$name"
  rm -f "$tmp"
  echo "Installed $name (root: $ONE2LVOS_ROOT, user: $ONE2LVOS_USER)"
done

sudo systemctl daemon-reload
echo "Enable with: sudo systemctl enable --now maton-security-monitor lumenis-security-heartbeat"
