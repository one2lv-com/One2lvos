#!/usr/bin/env bash
# ==============================================================================
# NVIDIA NIM TEST LAB - LAUNCHER & TUI DASHBOARD
# ==============================================================================
# This script contains no inline Python. Every action calls a real module
# (python3 -m nimlab <command> or one of the lab scripts) and passes data via
# argv, stdin or environment variables, so keys and typed text are never
# spliced into source code.
#
# Usage:  ./start.sh             interactive dashboard (menus: README "Menus")
#         ./start.sh <command>   run one nimlab command and exit
#                                (e.g. ./start.sh fleet, ./start.sh judge show)
#         ./start.sh serve       OpenAI-compatible test server (serve info,
#                                serve test, serve log, serve --lan ...)
#         ./start.sh mcp ...     MCP server URL / key / auth / test
#         ./start.sh install     install Python dependencies (requirements.txt,
#                                incl. nvidia-riva-client for NVCF gRPC models)
#         ./start.sh grpc ...    NVCF gRPC models: list / set / refresh / check
#         ./start.sh memory ...  long-term memory: use json|local|oracle, embed,
#                                test, setup (Oracle tables in MEM), set ...
#         ./start.sh shortcut    install a 'nimlab' command for any folder
#                                (shortcut status / remove / install <name>)
#         ./start.sh --no-color  dashboard without colours (also NO_COLOR=1)
# ==============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Python: $PYTHON if set, else the lab's venv when there is one (made by
# ./start.sh install where pip refuses the system Python, PEP 668), else
# python3. The shortcut and the service both run this script, so they use
# the same Python.
VENV_LOCAL="$SCRIPT_DIR/.venv"
VENV_SHARED="${XDG_DATA_HOME:-$HOME/.local/share}/nimlab/venv"
if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif [ -x "$VENV_LOCAL/bin/python" ]; then
    PY="$VENV_LOCAL/bin/python"
elif [ -x "$VENV_SHARED/bin/python" ]; then
    PY="$VENV_SHARED/bin/python"
else
    PY="python3"
fi
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Accept NGC_API_KEY as the NVIDIA key for this session.
if [ -z "${NVIDIA_API_KEY:-}" ] && [ -n "${NGC_API_KEY:-}" ]; then
    export NVIDIA_API_KEY="$NGC_API_KEY"
fi

RULE="======================================================================"
THIN="----------------------------------------------------------------------"

# ------------------------------------------------------------------------------
# Colours. Same rules as nimlab/colors.py: NIMLAB_COLOR=0/1 or --no-color /
# --color first, then NO_COLOR (off), FORCE_COLOR (on), ui_settings.color in
# config_cluster.json, else on only when stdout is a terminal. Truecolor in
# Termux / COLORTERM=truecolor, else 256 colours, else the 16 bright colours.
# ------------------------------------------------------------------------------
USE_COLOR=0
COLOR_DEPTH=16
C_RESET="" C_BOLD="" C_DIM="" C_OK="" C_WARN="" C_ERR="" C_VALUE="" C_LABEL="" C_ACCENT=""
C_HINT=""
MENU_NUM=() MENU_TXT=() ROLE_C=()

# fg R G B FALLBACK16 -> escape sequence for the current depth
fg() {
    local r=$1 g=$2 b=$3 basic=$4
    if [ "$COLOR_DEPTH" = 24 ]; then
        printf '\033[38;2;%d;%d;%dm' "$r" "$g" "$b"
    elif [ "$COLOR_DEPTH" = 256 ]; then
        local ir ig ib
        ir=$(( r < 48 ? 0 : (r < 115 ? 1 : (r - 35) / 40) ))
        ig=$(( g < 48 ? 0 : (g < 115 ? 1 : (g - 35) / 40) ))
        ib=$(( b < 48 ? 0 : (b < 115 ? 1 : (b - 35) / 40) ))
        printf '\033[38;5;%dm' $(( 16 + 36 * ir + 6 * ig + ib ))
    else
        printf '\033[%sm' "$basic"
    fi
}

# lighter tint of R G B (halfway to white)
fg_tint() {
    fg $(( ($1 + 255) / 2 )) $(( ($2 + 255) / 2 )) $(( ($3 + 255) / 2 )) "$4"
}

setup_colors() {
    local pol="auto" dep="16" a
    for a in "$@"; do
        case "$a" in
            --no-color|--no-colour) export NIMLAB_COLOR=0 ;;
            --color|--colour) export NIMLAB_COLOR=1 ;;
        esac
    done
    read -r pol dep < <(nimlab status color 2>/dev/null) || true
    case "$pol" in
        on) USE_COLOR=1 ;;
        off) USE_COLOR=0 ;;
        *) if [ -t 1 ]; then USE_COLOR=1; else USE_COLOR=0; fi ;;
    esac
    COLOR_DEPTH="${dep:-16}"
    [ "$USE_COLOR" = 1 ] || return 0
    C_RESET=$'\033[0m'
    C_BOLD=$'\033[1m'
    C_DIM="$(fg 140 144 160 90)"
    C_OK="$C_BOLD$(fg 80 250 123 92)"
    C_WARN="$(fg 255 210 70 93)"
    C_ERR="$C_BOLD$(fg 255 85 100 91)"
    C_VALUE="$C_BOLD$(fg 255 236 150 93)"
    C_LABEL="$C_BOLD$(fg 180 195 255 94)"
    C_ACCENT="$C_BOLD$(fg 255 120 220 95)"
    C_HINT="$(fg 165 160 190 37)"
    # menu numbers: a rainbow; each label in a lighter tint of its number
    local spec
    for spec in "255 95 135 91" "255 165 40 33" "255 230 70 93" "110 255 120 92" "0 235 220 96" \
                "100 175 255 94" "185 135 255 95" "255 115 245 35"; do
        # shellcheck disable=SC2086
        MENU_NUM+=("$C_BOLD$(fg $spec)")
        # shellcheck disable=SC2086
        MENU_TXT+=("$(fg_tint $spec)")
    done
    # one colour per role, same as nimlab/colors.py ROLE_RGB (order of the 16 roles)
    for spec in "255 145 0 33" "255 95 255 95" "185 145 255 95" "60 255 140 92" "70 175 255 94" \
                "255 222 90 93" "255 175 130 33" "255 95 95 91" "110 255 255 96" "215 120 255 35" \
                "255 150 185 95" "195 255 80 92" "0 225 190 36" "150 175 255 94" "235 230 150 93" \
                "255 120 150 91"; do
        # shellcheck disable=SC2086
        ROLE_C+=("$C_BOLD$(fg $spec)")
    done
}

# gradient TEXT: each character along cyan -> blue -> violet -> pink -> amber
gradient() {
    local text="$1" n i ch t seg f r g b out=""
    if [ "$USE_COLOR" != 1 ]; then
        printf '%s' "$text"
        return
    fi
    local -a SR=(0 70 190 255 255) SG=(255 170 110 90 175) SB=(200 255 255 190 60)
    n=${#text}
    for (( i = 0; i < n; i++ )); do
        ch="${text:i:1}"
        if [ "$ch" = " " ]; then
            out+=" "
            continue
        fi
        t=$(( n > 1 ? i * 4000 / (n - 1) : 0 ))
        seg=$(( t / 1000 ))
        [ "$seg" -ge 4 ] && seg=3
        f=$(( t - seg * 1000 ))
        r=$(( SR[seg] + (SR[seg + 1] - SR[seg]) * f / 1000 ))
        g=$(( SG[seg] + (SG[seg + 1] - SG[seg]) * f / 1000 ))
        b=$(( SB[seg] + (SB[seg + 1] - SB[seg]) * f / 1000 ))
        out+="$C_BOLD$(fg "$r" "$g" "$b" 96)$ch"
    done
    printf '%s%s' "$out" "$C_RESET"
}

# term_width: W = terminal columns, capped at 70 (the classic layout) and at
# least 36, so menus fit a phone screen in Termux. Re-read on every screen,
# so rotating the phone is picked up.
W=70
term_width() {
    local c="${COLUMNS:-}" _r
    if [ -z "$c" ] && [ -t 1 ]; then
        read -r _r c < <(stty size 2>/dev/null </dev/tty) || c=""
    fi
    case "$c" in ''|*[!0-9]*) c=70 ;; esac
    [ "$c" -gt 70 ] && c=70
    [ "$c" -lt 36 ] && c=36
    W="$c"
}

# rule [CHAR]: a full-width separator, a gradient line when colour is on
rule() {
    term_width
    local line="" i
    if [ "$USE_COLOR" = 1 ]; then
        for (( i = 0; i < W; i++ )); do line+="─"; done
        gradient "$line"
        echo ""
    else
        line="${1:-$THIN}"
        printf '%s\n' "${line:0:W}"
    fi
}

# item INDEX KEY LABEL [HINT]: one menu entry, number and label in their colour
item() {
    local i=$(( $1 % 8 )) key="$2" label="$3" hint="${4:-}"
    # the hint is dropped when it would wrap on a narrow screen
    if [ -n "$hint" ] && [ $(( 8 + 20 + ${#hint} )) -gt "$W" ]; then
        hint=""
    fi
    [ -n "$hint" ] && label="$(printf '%-20s' "$label")"
    if [ "$USE_COLOR" = 1 ]; then
        printf '  %s%2s.%s %s%s%s' "${MENU_NUM[$i]}" "$key" "$C_RESET" "${MENU_TXT[$i]}" "$label" "$C_RESET"
        [ -n "$hint" ] && printf ' %s%s%s' "$C_HINT" "$hint" "$C_RESET"
        echo ""
    else
        if [ -n "$hint" ]; then
            printf '  %2s. %s %s\n' "$key" "$label" "$hint"
        else
            printf '  %2s. %s\n' "$key" "$label"
        fi
    fi
}

# section TITLE
section() {
    if [ "$USE_COLOR" = 1 ]; then
        printf '%s▌%s %s\n' "$C_ACCENT" "$C_RESET" "$(gradient "$1")"
    else
        printf '%s\n' "$1"
    fi
}

# ask PROMPT VAR: read a menu choice with a coloured prompt
ask() {
    local __p="$1"
    if [ "$USE_COLOR" = 1 ]; then
        __p="$C_ACCENT$1$C_RESET$(fg 255 236 150 93)"
    fi
    read -r -p "$__p" "$2"
    local rc=$?
    printf '%s' "$C_RESET"
    return $rc
}

# captured output is parsed: never coloured
quiet() {
    NIMLAB_COLOR=0 nimlab "$@"
}

nimlab() {
    "$PY" -m nimlab "$@"
}

# Python dependencies. The lab itself is stdlib-only; requirements.txt adds
# nvidia-riva-client for the NVCF gRPC (Riva ASR / TTS / NMT) models. On
# Termux, grpcio comes from pkg (python-grpcio) because pip would have to
# compile it.
pkg_hint() {
    # the install command for a system package on this platform
    local what="$1" mgr=""
    if [ -n "${PREFIX:-}" ] && [ "${PREFIX#*com.termux}" != "$PREFIX" ]; then mgr=pkg
    elif command -v apt-get >/dev/null 2>&1; then mgr=apt
    elif command -v dnf >/dev/null 2>&1; then mgr=dnf
    elif command -v yum >/dev/null 2>&1; then mgr=yum
    fi
    case "$what:$mgr" in
        venv:apt) echo "sudo apt-get install -y python3-venv python3-pip" ;;
        venv:dnf|venv:yum) echo "sudo $mgr install -y python3-pip" ;;
        venv:pkg) echo "pkg install python" ;;
        ffmpeg:apt) echo "sudo apt-get install -y ffmpeg" ;;
        ffmpeg:dnf|ffmpeg:yum) echo "enable EPEL and RPM Fusion (free), then sudo $mgr install -y ffmpeg" ;;
        ffmpeg:pkg) echo "pkg install ffmpeg" ;;
        cloudflared:pkg) echo "pkg install cloudflared" ;;
        cloudflared:*) echo "nimlab serve tunnel install, or Cloudflare's package repo: https://pkg.cloudflare.com/index.html" ;;
        *) echo "install $what with your package manager" ;;
    esac
}

make_venv() {
    # PEP 668: the system Python refuses pip. Make a venv and use it from now
    # on. Never --break-system-packages.
    local dir="$VENV_LOCAL"
    if ! { [ -w "$SCRIPT_DIR" ] || [ -d "$VENV_LOCAL" ]; }; then dir="$VENV_SHARED"; fi
    echo "This Python is managed by the system (PEP 668), so pip installs into a venv: $dir"
    mkdir -p "$(dirname "$dir")"
    if ! python3 -m venv "$dir"; then
        echo "[x] Could not make a venv. Install venv support, then run ./start.sh install again:"
        echo "    $(pkg_hint venv)"
        return 1
    fi
    PY="$dir/bin/python"
    "$PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
    echo "[ok] venv ready. ./start.sh, the nimlab shortcut and the service use it from now on."
    return 0
}

pip_install() {
    # pip with wheels preferred (no source builds on a small VPS); on
    # "externally-managed-environment" make the venv once and retry there
    local out rc=0
    out="$("$PY" -m pip install --prefer-binary --upgrade "$@" 2>&1)" || rc=$?
    printf '%s\n' "$out" | tail -n 15
    if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "externally-managed-environment"; then
        make_venv || return 1
        rc=0
        "$PY" -m pip install --prefer-binary --upgrade "$@" || rc=$?
    elif [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q "No module named pip"; then
        echo "pip is missing for $PY. Install it: $(pkg_hint venv)"
    fi
    return "$rc"
}

install_deps() {
    local rc=0
    if [ -n "${PREFIX:-}" ] && [ "${PREFIX#*com.termux}" != "$PREFIX" ] && command -v pkg >/dev/null 2>&1; then
        # pip cannot build grpcio or cryptography on Termux: take them from pkg first
        echo "Termux: installing grpcio, ffmpeg and cryptography from pkg..."
        pkg install -y python-grpcio ffmpeg python-cryptography || echo "pkg install failed; pip will try to build them instead."
    fi
    echo "Installing Python packages from requirements.txt..."
    pip_install -r "$SCRIPT_DIR/requirements.txt" || rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "pip failed (exit $rc). Try: $PY -m pip install --prefer-binary nvidia-riva-client"
        return "$rc"
    fi
    nimlab grpc list >/dev/null 2>&1 || true
    "$PY" -c 'import riva.client' 2>/dev/null && echo "[ok] nvidia-riva-client is ready (NVCF gRPC models)."
    echo "Installing oracledb (Oracle long-term memory)..."
    pip_install oracledb || echo "pip could not install oracledb; Oracle memory needs it."
    command -v ffmpeg >/dev/null 2>&1 || echo "[!] ffmpeg is missing (voice notes need it): $(pkg_hint ffmpeg)"
    command -v cloudflared >/dev/null 2>&1 || [ -x "$HOME/.local/bin/cloudflared" ] || \
        echo "[i] cloudflared is not installed (only the public tunnel needs it): $(pkg_hint cloudflared)"
    return 0
}

# Non-interactive mode: pass straight through to the CLI.
if [ "$#" -gt 0 ]; then
    case "$1" in
        -h|--help)
            sed -n '2,23p' "$0"
            nimlab --help
            exit 0
            ;;
        install|deps)
            install_deps
            exit $?
            ;;
        sweep200|200)
            # Classic 200 Health & Fallback Sweep (route guessing, writes the verified fleet).
            "$PY" nvidia_playground.py --sweep
            exit $?
            ;;
        --no-color|--no-colour|--color|--colour)
            # a colour flag alone: set it and open the dashboard
            if [ "$#" -gt 1 ]; then
                exec "$PY" -m nimlab "$@"
            fi
            ;;
        *)
            # exec, not a child: runit (sv down / sv restart) signals this
            # process, and a child python would be orphaned and keep the
            # supervisor lock (the phone showed three stray supervisors).
            exec "$PY" -m nimlab "$@"
            ;;
    esac
fi

setup_colors "$@"

banner() {
    clear
    term_width
    local t="$1" inner="" pad i n=$(( W - 2 ))
    [ "${#t}" -gt "$n" ] && t="${t:0:n}"
    if [ "$USE_COLOR" = 1 ]; then
        for (( i = 0; i < n; i++ )); do inner+="═"; done
        gradient "╔${inner}╗"
        echo ""
        pad=$(( (n - ${#t}) / 2 ))
        printf '%s║%s%*s%s%*s%s║%s\n' "$(fg 0 255 200 96)" "$C_RESET" "$pad" "" "$(gradient "$t")" \
            $(( n - pad - ${#t} )) "" "$(fg 255 175 60 33)" "$C_RESET"
        gradient "╚${inner}╝"
        echo ""
        return
    fi
    printf '%s\n' "${RULE:0:W}"
    printf '%*s\n' $(( (W + ${#t}) / 2 )) "$t"
    printf '%s\n' "${RULE:0:W}"
}

# field LABEL VALUE-COLOUR TEXT
field() {
    printf ' %s%-11s%s%s %s%s%s\n' "$C_LABEL" "$1" "$C_RESET" "$C_DIM:$C_RESET" "$2" "$3" "$C_RESET"
}

# 3.8.6: the build version, read from its one home (nimlab/__init__.py) without starting Python
nimlab_version() {
    local v
    v="$(sed -n 's/^__version__ *= *["'"'"']\([^"'"'"']*\)["'"'"'].*/\1/p' "$SCRIPT_DIR/nimlab/__init__.py" 2>/dev/null | head -n 1)"
    printf '%s' "${v:-?}"
}

draw_header() {
    banner "NVIDIA NIM TEST LAB v$(nimlab_version)"
    local key live inv mem mcpk total unset
    if key="$(quiet status key 2>/dev/null)"; then
        field "NVIDIA key" "$C_OK" "$key"
    else
        field "NVIDIA key" "$C_ERR" "not set (7 Keys & MCP)"
    fi
    live="$(quiet status live 2>/dev/null || echo 0)"
    inv="$(quiet status discovered 2>/dev/null || echo 0)"
    if [ "${live:-0}" -gt 0 ] 2>/dev/null; then
        field "Models" "$C_OK" "$live verified$C_RESET$C_DIM, ${inv:-0} discovered"
    elif [ "${inv:-0}" -gt 0 ] 2>/dev/null; then
        field "Models" "$C_WARN" "$inv discovered, none verified (4)"
    else
        field "Models" "$C_ERR" "none yet (4 Discover & sweep)"
    fi
    total=0 unset=0
    while IFS= read -r line; do
        total=$(( total + 1 ))
        case "$line" in *" ----- "*) unset=$(( unset + 1 )) ;; esac
    done < <(quiet status roles 2>/dev/null)
    field "Roles" "$C_VALUE" "$(( total - unset ))/$total set$C_RESET$C_DIM (6)"
    mem="$(quiet status memory 2>/dev/null || echo '?')"
    field "Memory" "$C_VALUE" "$mem$C_RESET$C_DIM (8)"
    mcpk="$(quiet mcp key-source 2>/dev/null || echo 'not set')"
    case "$mcpk" in
        "not set"*) field "MCP key" "$C_WARN" "not set (7)" ;;
        *) field "MCP key" "$C_OK" "$mcpk" ;;
    esac
    if type -P "nimlab" >/dev/null 2>&1; then
        field "Shortcut" "$C_OK" "nimlab"
    fi
    local svc tg
    if svc="$(quiet service brief 2>/dev/null)"; then
        case "$svc" in
            running*) field "Service" "$C_OK" "$svc" ;;
            *) field "Service" "$C_WARN" "$svc" ;;
        esac
    fi
    tg="$(quiet telegram status 2>/dev/null | sed -n 's/^running *: //p')"
    case "$tg" in
        ""|"not set up") ;;
        *running*) field "Telegram" "$C_OK" "$tg" ;;
        *) field "Telegram" "$C_DIM" "$tg" ;;
    esac
    rule "$THIN"
}

pause() {
    echo ""
    ask "Press Enter to return to menu..." _
}

# Read a key without echo, strip CR/LF/quotes/surrounding spaces, export it.
read_key_into_env() {
    local prompt="$1" k
    read -r -s -p "$prompt" k
    echo ""
    k="${k//$'\r'/}"
    k="${k//$'\n'/}"
    k="${k//\"/}"
    k="${k//\'/}"
    k="${k#"${k%%[![:space:]]*}"}"
    k="${k%"${k##*[![:space:]]}"}"
    case "$k" in
        *[[:space:]]*|*'$'*|*'`'*|*';'*|*'('*|*')'*)
            # A key never has spaces or shell characters: this is a phrase or
            # a paste that went wrong. Refuse it rather than send it anywhere.
            printf '%s[x] That does not look like an API key (it has spaces or shell characters).%s\n' "$C_ERR" "$C_RESET"
            return 1 ;;
    esac
    if [ -n "$k" ]; then
        export NVIDIA_API_KEY="$k"
        return 0
    fi
    return 1
}

ensure_key() {
    if [ -n "${NVIDIA_API_KEY:-}" ]; then
        return 0
    fi
    printf '\n%s[!] NVIDIA_API_KEY is not set in the shell.%s\n' "$C_WARN" "$C_RESET"
    if read_key_into_env "Paste NVIDIA API key: "; then
        printf '%s[ok] Key exported for this session.%s\n' "$C_OK" "$C_RESET"
        return 0
    fi
    printf '%s[x] No key provided. Operation aborted.%s\n' "$C_ERR" "$C_RESET"
    pause
    return 1
}

# ==============================================================================
# MENUS. One screen per group, short enough for a phone: numbers 1-9 for
# options, 0 to go back, section headings inside each screen. Every option
# runs a nimlab command, so ./start.sh <command> does the same thing.
# ==============================================================================

# pick PROMPT VAR: read a selection; a closed input (Ctrl-D) returns 1
pick() {
    echo ""
    ask "${1:-Select: }" "$2"
}

view_verified_fleet() {
    banner "VERIFIED 200 FLEET"
    nimlab fleet
    pause
}

view_benchmark_report() {
    banner "LATEST BENCHMARK REPORT"
    nimlab report
    pause
}

quick_voice_synth() {
    banner "MAGPIE VOICE SYNTHESIZER"
    ensure_key || return
    local phrase v_choice voice
    printf '\nEnter phrase to speak (or press Enter for default):\n'
    ask "Phrase: " phrase
    printf '\nChoose Voice Profile:\n'
    item 1 1 "Aria (female)" "EN-US.Aria"
    item 2 2 "Jason (male)" "EN-US.Jason"
    ask "Select [1/2]: " v_choice
    voice="Magpie-Multilingual.EN-US.Aria"
    if [ "$v_choice" = "2" ]; then
        voice="Magpie-Multilingual.EN-US.Jason"
    fi
    printf '\n%sSending synthesis request to NVCF gateway...%s\n' "$C_WARN" "$C_RESET"
    # The phrase goes over stdin: any characters are safe.
    # With no terminal (a script or a test) nobody is listening: save the
    # file and skip the player, which could otherwise wait forever.
    if [ -t 1 ]; then
        printf '%s' "$phrase" | nimlab tts --voice "$voice"
    else
        printf '%s' "$phrase" | nimlab tts --voice "$voice" --no-play
    fi
    pause
}

# 4. Discover & sweep: find models, probe them, NVCF gRPC function IDs
models_menu() {
    local c kinds
    while true; do
        banner "DISCOVER & SWEEP"
        section "Discover"
        item 1 1 "Refresh the catalog" "no key needed"
        item 2 2 "Discovered models"
        item 3 3 "On site, not on key"
        item 4 4 "Deprecated / retired"
        section "Sweep"
        item 5 5 "Spec-driven sweep" "probes each spec"
        item 6 6 "Sweep some kinds" "e.g. chat,vision"
        item 7 7 "Plan only" "no API calls"
        item 0 8 "200 health sweep" "route fallback"
        section "NVCF gRPC"
        item 1 9 "gRPC models" "IDs, language, try"
        item 2 A "Custom endpoints" "your own gateway"
        item 0 0 "Back"
        pick "Select: " c || return 0
        case "$c" in
            a|A) nimlab ui endpoints || true ;;
            1) nimlab discover; pause ;;
            2) nimlab discover --show; pause ;;
            3) nimlab discover --show --flag on_site_not_in_key; pause ;;
            4) nimlab discover --show --flag deprecated; nimlab discover --show --flag retired; pause ;;
            5) ensure_key && nimlab sweep; pause ;;
            6) ask "Kinds: " kinds || continue
               [ -n "$kinds" ] && ensure_key && nimlab sweep --kinds "$kinds"
               pause ;;
            7) nimlab sweep --plan-only; pause ;;
            8) ensure_key && "$PY" nvidia_playground.py --sweep; pause ;;
            9) grpc_menu ;;
            *) return 0 ;;
        esac
    done
}

grpc_menu() {
    banner "NVCF gRPC MODELS"
    nimlab grpc menu
}

# 5. Benchmark & judge
bench_menu() {
    local c types runs
    while true; do
        banner "BENCHMARK & JUDGE"
        section "Benchmark"
        item 1 1 "Run the benchmarks" "embed, vision, LLM"
        item 2 2 "Latest report"
        item 3 3 "Verified 200 fleet"
        section "Judge"
        item 4 4 "Rank all types"
        item 5 5 "Rank some types" "e.g. chat,coding"
        item 6 6 "Score the entity" "vs soul.md"
        item 7 7 "Leaderboards"
        item 0 8 "Apply the winners" "asks first"
        section "Router (the testbed's own chat/call pipeline)"
        item 1 9 "Router benchmark: chat" "routing + NVIDIA time"
        item 2 10 "Router benchmark: call" "voice pipeline, spoken reply"
        item 3 11 "Last router benchmark"
        item 0 0 "Back"
        pick "Select: " c || return 0
        case "$c" in
            9|10) ask "Runs per prompt [3]: " runs || continue
               [ -z "$runs" ] && runs=3
               if [ "$c" = "10" ]; then ensure_key && nimlab bench router --runs "$runs" --call --compare
               else ensure_key && nimlab bench router --runs "$runs" --compare; fi
               pause ;;
            11) nimlab bench router --show; pause ;;
            1) ensure_key && "$PY" nvidia_benchmark_suite.py ;;
            2) view_benchmark_report ;;
            3) view_verified_fleet ;;
            4) ensure_key && nimlab judge rank; pause ;;
            5) ask "Types (e.g. chat,coding,embeddings): " types || continue
               [ -n "$types" ] && ensure_key && nimlab judge rank --types "$types"
               pause ;;
            6) ensure_key && nimlab judge entity; pause ;;
            7) nimlab judge show; pause ;;
            8) nimlab judge apply; pause ;;
            *) return 0 ;;
        esac
    done
}

# 6. Roles & data
roles_menu() {
    local c role
    while true; do
        banner "ROLES & DATA"
        printf '  %sChange a role: 1 Testbed, then 3 Roles.%s\n' "$C_HINT" "$C_RESET"
        section "Roles"
        item 1 1 "Show the 16 roles"
        item 2 2 "Candidates for one"
        item 3 3 "Migrate old keys"
        section "Data (data/)"
        item 4 4 "Data stores & lists" "endpoints, verified"
        item 0 0 "Back"
        pick "Select: " c || return 0
        case "$c" in
            1) banner "ROLES (16)"; nimlab roles show; pause ;;
            2) ask "Role key (e.g. chart_parser, reranker): " role || continue
               nimlab roles candidates "$role" --scope all
               pause ;;
            3) nimlab roles migrate; pause ;;
            4) data_menu ;;
            *) return 0 ;;
        esac
    done
}

data_menu() {
    local c
    while true; do
        banner "DATA STORES & LISTS"
        section "Endpoints"
        item 1 1 "Active"
        item 2 2 "Stale"
        section "Models"
        item 3 3 "All discovered"
        item 4 4 "Key /v1/models list"
        item 5 5 "Retired / deprecated"
        item 6 6 "Removed"
        section "Results"
        item 7 7 "Verified 200 OK"
        item 0 8 "Dropped" "with last result"
        item 1 9 "Failing" "last result"
        item 2 10 "Never tested"
        item 3 11 "Benchmark history"
        section "Files"
        item 4 12 "Summary of data/"
        item 5 13 "Migrate old files"
        item 0 0 "Back"
        pick "Select: " c || return 0
        case "$c" in
            1) nimlab data show endpoints ;;
            2) nimlab data show stale ;;
            3) nimlab data show discovered ;;
            4) nimlab data show key ;;
            5) nimlab data show retired; nimlab data show deprecated ;;
            6) nimlab data show removed ;;
            7) nimlab data show verified ;;
            8) nimlab data show dropped ;;
            9) nimlab data show failed ;;
            10) nimlab data show untested ;;
            11) nimlab data show benchmarks ;;
            12) nimlab data ;;
            13) nimlab data migrate ;;
            *) return 0 ;;
        esac
        pause
    done
}

# 3. OpenAI-compatible test server
serve_menu() {
    local c
    while true; do
        banner "TEST SERVER (OpenAI)"
        printf '  %sServes the testbed as one model to any OpenAI-compatible UI.%s\n' "$C_HINT" "$C_RESET"
        section "Start (Ctrl-C stops)"
        item 1 1 "This device only"
        item 2 2 "With LAN access" "same Wi-Fi"
        item 3 3 "With a public tunnel" "cloudflared"
        section "Use it"
        item 4 4 "Connection details" "URL, key, models"
        item 5 5 "Config for UIs" "Open WebUI, ..."
        item 6 6 "Self-test"
        item 7 7 "Request log"
        section "Setup"
        item 0 8 "Server settings" "models, port, CORS"
        item 1 9 "New API key"
        item 2 G "Guided server setup" "tunnel, service"
        item 3 T "Tunnel status"
        item 4 K "Keep running" "service status"
        item 5 L "Service log"
        item 6 B "Telegram bot"
        item 7 P "Phone audio bridge" "register a phone"
        item 0 0 "Back"
        pick "Select: " c || return 0
        case "$c" in
            g|G) nimlab setup server; pause ;;
            t|T) nimlab serve tunnel status; pause ;;
            k|K) nimlab service status; pause ;;
            l|L) nimlab service logs; pause ;;
            b|B) nimlab setup telegram; pause ;;
            p|P) nimlab audio setup; pause ;;
            1) ensure_key && nimlab serve start; pause ;;
            2) ensure_key && nimlab serve start --lan; pause ;;
            3) ensure_key && nimlab serve start --tunnel; pause ;;
            4) nimlab serve info; pause ;;
            5) nimlab serve ui; pause ;;
            6) ensure_key && nimlab serve test; pause ;;
            7) nimlab serve log; pause ;;
            8) ensure_key && nimlab serve menu ;;
            9) nimlab serve regen-key; pause ;;
            *) return 0 ;;
        esac
    done
}

# 7. Keys & MCP: the NVIDIA key and the MCP server in one place
keys_menu() {
    local c shown k
    while true; do
        banner "KEYS & MCP"
        if shown="$(quiet status key 2>/dev/null)"; then
            field "NVIDIA key" "$C_OK" "$shown"
        else
            field "NVIDIA key" "$C_WARN" "not set"
        fi
        nimlab mcp show 2>/dev/null | sed -n '2,4p'
        section "NVIDIA key"
        item 1 1 "Enter key" "this session"
        item 2 2 "Save key" "to ~/.nimlab_env"
        item 3 3 "Clear key" "and the saved copy"
        section "MCP server"
        item 4 4 "Server URL" "tests after"
        item 5 5 "Save API key" "hidden, private file"
        item 6 6 "Key for this run" "not saved"
        item 7 7 "Delete saved key"
        item 0 8 "Auth style" "x-api-key, bearer"
        item 1 9 "Test connection" "lists tools"
        item 0 0 "Back"
        pick "Select: " c || return 0
        case "$c" in
            1) if read_key_into_env "Paste new NVIDIA API Key: "; then
                   printf '%s[ok] NVIDIA_API_KEY updated in this session.%s\n' "$C_OK" "$C_RESET"
               fi
               pause ;;
            2) if [ -z "${NVIDIA_API_KEY:-}" ]; then
                   printf '%s[!] No key active to persist. Set the key first.%s\n' "$C_ERR" "$C_RESET"
               else
                   nimlab persist-key
               fi
               pause ;;
            3) unset NVIDIA_API_KEY NGC_API_KEY
               nimlab forget-key
               printf '%s[!] Key cleared from this session.%s\n' "$C_WARN" "$C_RESET"
               pause ;;
            4) nimlab mcp set-url; pause ;;
            5) nimlab mcp set-key --save; pause ;;
            6) read -r -s -p "MCP API key (hidden): " k
               echo ""
               k="${k//$'\r'/}"
               k="${k//$'\n'/}"
               if [ -n "$k" ]; then
                   export MCP_API_KEY="$k"
                   printf '%s[ok] MCP_API_KEY set for this launcher run (wins over a saved key).%s\n' \
                       "$C_OK" "$C_RESET"
                   nimlab mcp test
               fi
               k=""
               pause ;;
            7) nimlab mcp delete-key; pause ;;
            8) nimlab mcp auth; pause ;;
            9) nimlab mcp test; pause ;;
            *) return 0 ;;
        esac
    done
}

# 8. Long-term memory: one menu, the same one as testbed Settings -> Memory
memory_menu() {
    nimlab memory menu
}

colors_menu() {
    banner "TERMINAL COLOURS"
    nimlab colors
    echo ""
    printf '  %sOne run without colour: ./start.sh --no-color, NIMLAB_COLOR=0 or NO_COLOR=1.%s\n' \
        "$C_HINT" "$C_RESET"
    printf '  %sKeep a setting: 1 Testbed, 7 Settings, 6 Terminal colours (auto / on / off).%s\n' \
        "$C_HINT" "$C_RESET"
    pause
}

# 9. Tools: install, the nimlab shortcut, extras
tools_menu() {
    local c
    while true; do
        banner "TOOLS"
        section "Setup"
        item 1 1 "Install packages" "requirements.txt"
        item 2 2 "nimlab shortcut" "install / update"
        item 3 3 "Shortcut status"
        item 4 4 "Remove shortcut"
        section "Extras"
        item 5 5 "Voice synthesizer" "Magpie TTS"
        item 6 6 "Colours" "preview, on / off"
        item 0 0 "Back"
        pick "Select: " c || return 0
        case "$c" in
            1) install_deps; pause ;;
            2) nimlab shortcut install; pause ;;
            3) nimlab shortcut status; pause ;;
            4) nimlab shortcut remove; pause ;;
            5) quick_voice_synth ;;
            6) colors_menu ;;
            *) return 0 ;;
        esac
    done
}

# ==============================================================================
# MAIN MENU. The letter keys of earlier versions still work as shortcuts
# (D G B J L R O M K Y C V I N); they are not shown, to keep the menu short.
# 3.8.2: H is Health & repair (Commands moved to X), W the Scheduler and U
# Service & update are on the menu now.
# ==============================================================================
# First launch: offer the guided setup once.
# (NIMLAB_FIRST_RUN_TTY=1 lets the offline tests drive this with piped input.)
if { [ -t 0 ] || [ "${NIMLAB_FIRST_RUN_TTY:-0}" = 1 ]; } && quiet setup first-run >/dev/null 2>&1; then
    banner "NIM TEST LAB - FIRST RUN"
    echo "Welcome! Guided setup walks through every step, one question at a time"
    echo "(dependencies, key, MCP, gRPC, memory, models, server, Telegram)."
    echo "Each step can be skipped; run it again any time with S or: nimlab setup"
    echo ""
    ask "Start guided setup now? [Y/n] " _go
    case "${_go:-y}" in
        n|N|no) quiet setup skip-first-run >/dev/null 2>&1 || true ;;
        *) nimlab setup || true; pause ;;
    esac
    # always on to the main menu, whatever setup returned
fi

choice=""
while true; do
    draw_header
    section "Run"
    item 0 1 "Testbed" "chat, voice, roles"
    item 1 2 "Playground" "one / compare models"
    item 2 3 "Test server" "OpenAI-compatible"
    section "Models"
    item 3 4 "Discover & sweep" "catalog, probes, gRPC"
    item 4 5 "Benchmark & judge" "scores, leaderboards"
    item 5 6 "Roles & data" "16 roles, data/"
    item 6 A "Custom endpoints" "your own gateway"
    section "Background"
    item 7 U "Service & update" "start, stop, logs"
    item 8 W "Scheduler" "jobs, heartbeat"
    item 0 H "Health & repair" "check, fix"
    section "Setup"
    item 1 7 "Keys & MCP" "NVIDIA key, MCP"
    item 2 8 "Memory" "json / local / Oracle"
    item 3 9 "Tools" "install, shortcut"
    item 4 S "Guided setup" "step by step"
    item 5 F "Phone audio bridge" "register a phone"
    section "Help"
    item 6 E "Tests" "one per part, run all"
    item 7 X "Commands & troubleshooting" "by area, by symptom"
    item 0 0 "Exit"
    pick "Select [0-9]: " choice || exit 0

    case "$choice" in
        1|t|T) ensure_key && "$PY" orchestrator_testbed.py ;;
        2|p|P) ensure_key && "$PY" nvidia_playground.py ;;
        3|o|O) serve_menu ;;
        4|d|D) models_menu ;;
        s|S) nimlab setup; pause ;;
        f|F) nimlab audio setup; pause ;;   # 3.8.6: name, key, ready-to-paste Termux block
        h|H) nimlab ui health || true ;;
        x|X|"?") nimlab commands --menu || true ;;
        e|E) nimlab test --menu || true ;;
        w|W) nimlab ui scheduler || true ;;
        u|U) nimlab ui service || true ;;
        a|A) nimlab ui endpoints || true ;;
        5|b|B|j|J) bench_menu ;;
        6|r|R) roles_menu ;;
        7|m|M|k|K) keys_menu ;;
        8|y|Y) memory_menu ;;
        9) tools_menu ;;
        g|G) grpc_menu ;;
        l|L) data_menu ;;
        c|C) colors_menu ;;
        v|V) quick_voice_synth ;;
        i|I) install_deps; pause ;;
        n|N) nimlab shortcut install; pause ;;
        0|q|Q)
            clear
            printf '%sExiting NVIDIA NIM test lab.%s\n\n' "$C_OK" "$C_RESET"
            exit 0
            ;;
        *)
            printf '%sInvalid option.%s\n' "$C_ERR" "$C_RESET"
            sleep 0.8
            ;;
    esac
done
