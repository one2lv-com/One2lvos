#!/usr/bin/env bash
# Keeps the One2lvOS public bridge (127.0.0.1:8095) running. One copy only (flock).
cd "$(dirname "$(readlink -f "$0")")" || exit 1
PY=.venv/bin/python3; [ -x "$PY" ] || PY=python3
mkdir -p logs
exec 9>/tmp/o2_bridge_keepalive.lock
flock -n 9 || exit 0
while true; do
  if ! curl -s -m 5 -o /dev/null http://127.0.0.1:8095/v1/health; then
    if ! ss -ltn | grep -q '127.0.0.1:8095 '; then
      echo "$(date -Is) bridge down, starting" >> logs/bridge_keepalive.log
      setsid nohup "$PY" public_bridge.py >> logs/public_bridge.log 2>&1 < /dev/null &
    fi
  fi
  sleep 30
done
