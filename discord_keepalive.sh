#!/usr/bin/env bash
# Keeps the Lumenis Discord chat listener running. One copy only (flock), so only one
# Discord gateway connection; restarts it if it crashes, with a growing pause if it
# keeps failing quickly.
#
# On this sprite it runs as the sprite service "discord-listener" (see startos.sh). A running
# service keeps the sprite from pausing; a pause froze the whole machine and made Discord drop
# the bot's session ("stopped responding to the gateway" / "session has been invalidated").
# A stop signal (service stop, stop-all.sh) also stops the listener it started.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
PY=.venv/bin/python3; [ -x "$PY" ] || PY=python3
mkdir -p logs
exec 9>/tmp/o2_discord_keepalive.lock
flock -n 9 || exit 0
child=
trap 'echo "$(date -Is) keepalive stopping" >> logs/discord_keepalive.log; [ -n "$child" ] && kill -TERM "$child" 2>/dev/null && wait "$child" 2>/dev/null; exit 0' TERM INT HUP
pause=10
while true; do
  start=$(date +%s)
  echo "$(date -Is) starting discord_listener" >> logs/discord_keepalive.log
  "$PY" -u discord_listener.py >> logs/discord_listener.log 2>&1 < /dev/null 9>&- &
  child=$!
  wait "$child"
  code=$?
  child=
  echo "$(date -Is) discord_listener exited ($code)" >> logs/discord_keepalive.log
  if [ $(( $(date +%s) - start )) -gt 300 ]; then pause=10; else pause=$(( pause * 2 > 600 ? 600 : pause * 2 )); fi
  sleep "$pause"
done
