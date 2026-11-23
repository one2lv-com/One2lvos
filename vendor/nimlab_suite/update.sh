#!/usr/bin/env bash
# Nim Lab updater (3.8.2). Unzip a new release over this folder, then run:
#
#     bash update.sh          stop auto-restart, stop every Nim Lab process,
#                             start the service once, health check
#     bash update.sh --stop   only stop and clean up (optional, before unzipping)
#     bash update.sh --no-start   clean up, do not start
#
# It only touches Nim Lab's own processes. data/ and ~/.config/nimlab
# (keys, settings, memory) are never changed.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod 0755 "$DIR/start.sh" "$DIR/update.sh" 2>/dev/null || true
exec bash "$DIR/start.sh" update "$@"
