#!/usr/bin/env bash
# Keeps the Lumenis Discord chat listener running. One copy only (flock), so only one
# Discord gateway connection; restarts it if it crashes, with a growing pause if it
# keeps failing quickly.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
PY=.venv/bin/python3; [ -x "$PY" ] || PY=python3
mkdir -p logs
exec 9>/tmp/o2_discord_keepalive.lock
flock -n 9 || exit 0
pause=10
while true; do
  start=$(date +%s)
  echo "$(date -Is) starting discord_listener" >> logs/discord_keepalive.log
  "$PY" -u discord_listener.py >> logs/discord_listener.log 2>&1 < /dev/null 9>&-
  code=$?
  echo "$(date -Is) discord_listener exited ($code)" >> logs/discord_keepalive.log
  if [ $(( $(date +%s) - start )) -gt 300 ]; then pause=10; else pause=$(( pause * 2 > 600 ? 600 : pause * 2 )); fi
  sleep "$pause"
done
