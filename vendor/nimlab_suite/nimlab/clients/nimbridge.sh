#!/data/data/com.termux/files/usr/bin/bash
# nimbridge 1.1 - Nim Lab audio bridge for Termux.
# Plays Nim Lab audio (Quill's Telegram voice replies, the SSH voice call,
# anything an agent publishes) on this phone's speaker through Termux:API,
# and lends this phone's mic to the voice call only when you allow it.
# Each phone has its own name and token. Only the ACTIVE phone gets audio.
set -u
VER=1.1
CONF_DIR="$HOME/.config/nimbridge"
CONF="$CONF_DIR/config"
RUN="$HOME/.cache/nimbridge"
Q="$RUN/queue"
LOG="$RUN/nimbridge.log"
PIDF="$RUN/nimbridge.pid"
REC="$RUN/recording"
NID=nimbridge
mkdir -p "$CONF_DIR" "$Q"
chmod 700 "$CONF_DIR" "$RUN" 2>/dev/null

say() { printf '%s\n' "$*"; }
log() { printf '%s %s\n' "$(date '+%m-%d %H:%M:%S')" "$*" >> "$LOG"; }
die() { say "nimbridge: $*" >&2; exit 1; }

load() {
  [ -f "$CONF" ] || die "not set up yet. Run: nimbridge setup"
  . "$CONF"
  : "${URL:?}" "${DEVICE:?}" "${TOKEN:?}"; MIC="${MIC:-off}"
  API="${URL%/}/v1/audio/bus"
}

# curl with the token kept off the command line (ps can't see it)
api() {  # api METHOD PATH [curl args...]
  local m=$1 p=$2; shift 2
  curl -sS -X "$m" -K - "$@" "$API$p" <<CFG
header = "Authorization: Bearer $TOKEN"
CFG
}

save() {
  umask 077
  printf 'URL=%q\nDEVICE=%q\nTOKEN=%q\nMIC=%q\n' "$URL" "$DEVICE" "$TOKEN" "$MIC" > "$CONF"
  chmod 600 "$CONF"
}

running() { [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }

# ---------------------------------------------------------------- playback
player_stop() { termux-media-player stop </dev/null >/dev/null 2>&1; }

play_file() {  # play_file FILE DURATION_MS : returns when done, or when the mic starts
  local f=$1 dur=${2:-0} t=0 cap info
  termux-media-player play "$f" </dev/null >/dev/null 2>&1 || { log "player failed on $f"; return; }
  cap=$(( dur > 0 ? dur / 100 + 15 : 6000 ))   # tenths of a second
  while [ "$t" -lt "$cap" ]; do
    sleep 0.2; t=$((t + 2))
    if [ -f "$REC" ]; then player_stop; return; fi
    if [ "$t" -ge 15 ] && [ $((t % 5)) -eq 0 ]; then
      info=$(termux-media-player info </dev/null 2>/dev/null)
      case "$info" in *Playing*) ;; *) return ;; esac
    fi
  done
}

player_loop() {  # plays queued clips one at a time; never while the mic is on
  local f
  while :; do
    if [ -f "$REC" ]; then sleep 0.3; continue; fi
    f=$(ls "$Q" 2>/dev/null | grep -v -e '\.ms$' -e '\.part$' | sort | head -n 1)
    if [ -z "$f" ]; then sleep 0.3; continue; fi
    play_file "$Q/$f" "$(cat "$Q/$f.ms" 2>/dev/null || echo 0)"
    rm -f "$Q/$f" "$Q/$f.ms"
  done
}

# ---------------------------------------------------------------- mic
mic_on_notice() {
  termux-notification --id "$NID-mic" --title "Nim Lab is using your mic" \
    --content "$1" --ongoing --priority high >/dev/null 2>&1
  termux-toast -s "Nim Lab mic ON" >/dev/null 2>&1 &
}
mic_off_notice() { termux-notification-remove "$NID-mic" >/dev/null 2>&1; }

rec_begin() {  # rec_begin FILE MAXSEC : stops playback first so the speaker isn't recorded
  touch "$REC"; player_stop; sleep 0.3
  rm -f "$1"
  termux-microphone-record -q </dev/null >/dev/null 2>&1
  termux-microphone-record -f "$1" -e aac -l "${2:-120}" </dev/null >/dev/null 2>&1
}
rec_end() { termux-microphone-record -q </dev/null >/dev/null 2>&1; sleep 0.6; rm -f "$REC"; mic_off_notice; }

# ---------------------------------------------------------------- events
handle() {  # one event as compact JSON
  local ev=$1 type req clip ext ms f
  type=$(jq -r '.type' <<<"$ev")
  case "$type" in
    play)
      clip=$(jq -r '.clip' <<<"$ev"); ext=$(jq -r '.ext' <<<"$ev"); ms=$(jq -r '.duration_ms // 0' <<<"$ev")
      f="$Q/$(jq -r '.seq' <<<"$ev" | xargs printf '%012d').$ext"
      if api GET "/clips/$clip" --max-time 60 -o "$f.part" -f; then
        echo "$ms" > "$f.ms"; mv "$f.part" "$f"
        log "play $(jq -r '.source' <<<"$ev") $ext ${ms}ms"
      else rm -f "$f.part"; log "clip $clip download failed"; fi ;;
    stop)
      rm -f "$Q"/*; player_stop; log "stop" ;;
    record_start)
      req=$(jq -r '.req' <<<"$ev")
      if [ "$MIC" != on ]; then
        api POST /ack -H 'Content-Type: application/json' --max-time 15 \
          -d "{\"req\":\"$req\",\"state\":\"error\",\"error\":\"mic is off on phone $DEVICE (nimbridge mic on)\"}" >/dev/null
        log "mic request refused (mic off)"; return
      fi
      mic_on_notice "Voice call is listening. Press Enter in the call to send."
      if rec_begin "$RUN/call-$req.m4a" "$(jq -r '.max_sec // 120' <<<"$ev")"; then
        api POST /ack -H 'Content-Type: application/json' --max-time 15 -d "{\"req\":\"$req\",\"state\":\"recording\"}" >/dev/null
        log "mic on for voice call"
      else
        rec_end
        api POST /ack -H 'Content-Type: application/json' --max-time 15 \
          -d "{\"req\":\"$req\",\"state\":\"error\",\"error\":\"termux-microphone-record failed (mic permission for Termux:API?)\"}" >/dev/null
      fi ;;
    record_stop)
      req=$(jq -r '.req' <<<"$ev"); f="$RUN/call-$req.m4a"
      rec_end
      if [ -s "$f" ]; then
        api POST "/upload?req=$req" -H 'Content-Type: audio/mp4' --data-binary "@$f" --max-time 60 -f >/dev/null \
          && log "mic clip sent ($(wc -c < "$f") bytes)" || log "mic upload failed"
      else log "mic clip empty"; fi
      rm -f "$f" ;;
    record_cancel)
      rec_end; rm -f "$RUN"/call-*.m4a; log "mic cancelled" ;;
  esac
}

listen() {
  load
  local since=-1 back=2 code body micq=0 cpid=""
  [ "$MIC" = on ] && micq=1
  log "bridge $VER up as $DEVICE (mic $MIC)"
  termux-wake-lock >/dev/null 2>&1
  termux-notification --id "$NID" --title "Nim Lab bridge: $DEVICE" --ongoing \
    --content "Plays Nim Lab audio here. Mic for calls: $MIC" \
    --button1 "Stop" --button1-action "nimbridge stop" >/dev/null 2>&1
  [ "${NO_ACTIVATE:-0}" = 1 ] || api POST /activate --max-time 20 >/dev/null 2>&1
  player_loop &
  local ppid=$!
  trap 'kill $ppid $cpid 2>/dev/null; player_stop; rec_end; termux-notification-remove "$NID" >/dev/null 2>&1; termux-wake-unlock >/dev/null 2>&1; log "bridge down"; exit 0' TERM INT HUP
  while :; do
    # curl runs in the background so 'nimbridge stop' ends the bridge at once
    api GET "/events?since=$since&wait=25&mic=$micq&client=nimbridge-$VER" --max-time 45 \
      -o "$RUN/ev.json" -w '%{http_code}' > "$RUN/ev.code" 2>/dev/null &
    cpid=$!; wait "$cpid"; cpid=""
    code=$(cat "$RUN/ev.code" 2>/dev/null); body=$(cat "$RUN/ev.json" 2>/dev/null); rm -f "$RUN/ev.json"
    if [ "$code" = 200 ]; then
      back=2
      since=$(jq -r '.head' <<<"$body")
      while IFS= read -r ev; do [ -n "$ev" ] && handle "$ev"; done < <(jq -c '.events[]' <<<"$body")
    elif [ "$code" = 401 ]; then
      log "token refused: this phone was removed or re-added on the server. Run nimbridge setup."
      termux-notification --id "$NID" --title "Nim Lab bridge stopped" --content "Token refused: run nimbridge setup" >/dev/null 2>&1
      kill $ppid 2>/dev/null; exit 1
    else
      log "server not reachable (HTTP ${code:-none}); retry in ${back}s"
      sleep "$back"; back=$(( back < 30 ? back * 2 : 30 ))
    fi
  done
}

# ---------------------------------------------------------------- commands
cmd_setup() {
  local u d t m
  command -v jq >/dev/null && command -v termux-media-player >/dev/null || die "run: pkg install -y curl jq termux-api (and install the Termux:API app)"
  [ -f "$CONF" ] && . "$CONF"
  read -r -p "Nim Lab URL [${URL:-https://nim.svn-dev.online}]: " u; URL=${u:-${URL:-https://nim.svn-dev.online}}
  read -r -p "This phone's name, as added on the server [${DEVICE:-}]: " d; DEVICE=${d:-${DEVICE:-}}
  [ -n "$DEVICE" ] || die "a name is needed (on the VPS: nimlab audio add NAME)"
  read -r -s -p "Token for $DEVICE (from 'nimlab audio add $DEVICE'; input hidden): " t; say
  TOKEN=${t:-${TOKEN:-}}
  [ -n "$TOKEN" ] || die "a token is needed"
  read -r -p "Let voice calls use this phone's mic when you press Enter in the call? [y/N]: " m
  case "$m" in y|Y|yes) MIC=on ;; *) MIC=off ;; esac
  API="${URL%/}/v1/audio/bus"
  check_server && save && say "Saved."
  mic_permission
  cmd_restart
}

check_server() {  # the token works -> 0; else says why and exits
  local r; r=$(api GET /me --max-time 20 -w '\n%{http_code}')
  case "${r##*$'\n'}" in
    200) say "Server knows this phone as '$(jq -r .name <<<"${r%$'\n'*}")'. Mic for calls: $MIC." ;;
    401) die "the server refused that token. Check the name and token (nimlab audio add $DEVICE prints a new one)." ;;
    *) die "couldn't reach $URL (HTTP ${r##*$'\n'})." ;;
  esac
}

mic_permission() {  # Android asks once; allow it for Termux:API
  [ "$MIC" = on ] || return 0
  say "Asking Android for mic permission once (allow it for Termux:API)..."
  termux-microphone-record -f "$RUN/permcheck.m4a" -l 1 </dev/null >/dev/null 2>&1; sleep 2
  termux-microphone-record -q </dev/null >/dev/null 2>&1; rm -f "$RUN/permcheck.m4a"
}

cmd_init() {  # no prompts: the config was written for this phone by 'nimlab audio setup'
  command -v jq >/dev/null && command -v termux-media-player >/dev/null || die "run: pkg install -y curl jq termux-api (and install the Termux:API app)"
  load
  check_server
  mic_permission
  cmd_restart
}

cmd_start() {
  load
  if running; then say "Already running as '$DEVICE'."; [ "${NO_ACTIVATE:-0}" = 1 ] || cmd_use; return; fi
  : > "$LOG.tmp"; tail -n 300 "$LOG" 2>/dev/null > "$LOG.tmp"; mv "$LOG.tmp" "$LOG"
  rm -f "$REC" "$Q"/*
  nohup "$0" __listen >> "$LOG" 2>&1 &
  echo $! > "$PIDF"
  sleep 1
  running && say "Bridge started on '$DEVICE'$([ "${NO_ACTIVATE:-0}" = 1 ] || echo ', now the active phone'). Mic for calls: $MIC." || die "it didn't start; see: nimbridge logs"
}

cmd_stop() {
  if running; then kill "$(cat "$PIDF")" 2>/dev/null; sleep 1; fi
  rm -f "$PIDF" "$REC"; player_stop; mic_off_notice
  termux-notification-remove "$NID" >/dev/null 2>&1; termux-wake-unlock >/dev/null 2>&1
  say "Bridge stopped."
}

cmd_restart() { cmd_stop >/dev/null; cmd_start; }

cmd_use() {
  load
  local r; r=$(api POST /activate --max-time 20) || die "server not reachable"
  say "Active phone: $(jq -r .active <<<"$r")"
}

cmd_release() { load; api POST /release --max-time 20 >/dev/null && say "This phone is no longer active."; }

cmd_status() {
  load
  say "nimbridge $VER  phone: $DEVICE  server: $URL  mic for calls: $MIC"
  running && say "bridge: running (pid $(cat "$PIDF"))" || say "bridge: stopped"
  local r; r=$(api GET /me --max-time 15 -w '\n%{http_code}')
  if [ "${r##*$'\n'}" = 200 ]; then
    jq -r '"server sees it: " + (if .online then "online" else "offline" end) + ", " + (if .active then "ACTIVE (audio comes here)" else "not active (nimbridge use)" end)' <<<"${r%$'\n'*}"
  else say "server: not reachable or token refused (HTTP ${r##*$'\n'})"; fi
}

cmd_mic() {
  load
  case "${1:-}" in on|off) MIC=$1; save; say "Mic for calls: $MIC."; running && cmd_restart ;; *) say "Mic for calls: $MIC (nimbridge mic on|off)" ;; esac
}

cmd_talk() {  # push-to-talk to the lab's main entity (Quill) straight from this phone
  load
  local f="$RUN/talk.m4a" k r clip ext
  say "Talk to Nim Lab from '$DEVICE'. Enter = start/stop recording, q = quit."
  while :; do
    read -r -p "[Enter to talk, q to quit] " k; [ "$k" = q ] && break
    mic_on_notice "Push-to-talk is recording. Press Enter in Termux to send."
    rec_begin "$f" 120 || { rec_end; say "Recording failed (mic permission for Termux:API?)"; continue; }
    read -r -p "Recording... Enter to send " k
    rec_end
    [ -s "$f" ] || { say "Nothing recorded."; continue; }
    touch "$REC"   # hold other clips while the reply plays
    say "Thinking..."
    r=$(api POST /talk -H 'Content-Type: audio/mp4' --data-binary "@$f" --max-time 180 -w '\n%{http_code}')
    if [ "${r##*$'\n'}" != 200 ]; then rm -f "$REC"; say "Server error: $(jq -r '.error.message // .' <<<"${r%$'\n'*}" 2>/dev/null)"; continue; fi
    r=${r%$'\n'*}
    say "You: $(jq -r '.transcript // "?"' <<<"$r")"
    say "Reply: $(jq -r '.text // ""' <<<"$r")"
    clip=$(jq -r '.clip // empty' <<<"$r"); ext=$(jq -r '.ext // "wav"' <<<"$r")
    rm -f "$REC"
    if [ -n "$clip" ] && api GET "/clips/$clip" --max-time 60 -f -o "$RUN/reply.$ext"; then
      play_file "$RUN/reply.$ext" "$(jq -r '.duration_ms // 0' <<<"$r")"
    else say "(no audio: $(jq -r '.tts_error // "no voice for this reply"' <<<"$r"))"; fi
  done
  rm -f "$f" "$REC"
}

cmd_boot() {  # start on phone boot with the Termux:Boot app
  mkdir -p "$HOME/.termux/boot"
  printf '#!/data/data/com.termux/files/usr/bin/sh\ntermux-wake-lock\nNO_ACTIVATE=1 nimbridge start\n' > "$HOME/.termux/boot/nimbridge"
  chmod 700 "$HOME/.termux/boot/nimbridge"
  say "Starts at boot now (needs the Termux:Boot app). At boot it connects without taking over as the active phone."
}

case "${1:-help}" in
  setup) cmd_setup ;;
  init) cmd_init ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_restart ;;
  status) cmd_status ;;
  use) cmd_use ;;
  release) cmd_release ;;
  mic) cmd_mic "${2:-}" ;;
  talk) cmd_talk ;;
  logs) tail -n "${2:-40}" "$LOG" 2>/dev/null ;;
  boot) cmd_boot ;;
  __listen) listen ;;
  *) say "nimbridge $VER: setup | init | start | stop | restart | status | use | release | mic on|off | talk | logs | boot" ;;
esac
