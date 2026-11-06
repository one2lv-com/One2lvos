#!/usr/bin/env bash
# Keeps the One2lvOS WebDAV server (127.0.0.1:8090) and the Network Manager API
# (127.0.0.1:3003) that the desktop uses for file access running. One copy only (flock).
cd "$(dirname "$(readlink -f "$0")")" || exit 1
PY=.venv/bin/python3; [ -x "$PY" ] || PY=python3
mkdir -p logs
exec 9>/tmp/o2_webdav_keepalive.lock
flock -n 9 || exit 0
mkdir -p logs
while true; do
  if ! ss -ltn | grep -q '127.0.0.1:8090 '; then
    echo "$(date -Is) webdav down, starting" >> logs/webdav_keepalive.log
    setsid nohup "$PY" webdav_server.py >> logs/webdav.log 2>&1 < /dev/null &
    sleep 3
  fi
  if ! ss -ltn | grep -q '127.0.0.1:3003 '; then
    echo "$(date -Is) network api down, starting" >> logs/webdav_keepalive.log
    NETWORK_API_PORT=3003 setsid nohup node server/network-api.js >> logs/network.log 2>&1 < /dev/null &
  fi
  sleep 30
done
