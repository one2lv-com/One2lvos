#!/usr/bin/env bash
# ==============================================================================
# NVIDIA NIM TEST LAB - LAUNCHER & TUI DASHBOARD
# ==============================================================================
# This script contains no inline Python. Every action calls a real module
# (python3 -m nimlab <command> or one of the lab scripts) and passes data via
# argv, stdin or environment variables, so keys and typed text are never
# spliced into source code.
#
# Usage:  ./start.sh             interactive dashboard
#         ./start.sh <command>   run one nimlab command and exit
#                                (e.g. ./start.sh fleet, ./start.sh judge show)
# ==============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PY="${PYTHON:-python3}"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Accept NGC_API_KEY as the NVIDIA key for this session.
if [ -z "${NVIDIA_API_KEY:-}" ] && [ -n "${NGC_API_KEY:-}" ]; then
    export NVIDIA_API_KEY="$NGC_API_KEY"
fi

C_RESET=$'\033[0m'
C_BOLD=$'\033[1m'
C_CYAN=$'\033[36m'
C_GREEN=$'\033[32m'
C_YELLOW=$'\033[33m'
C_RED=$'\033[31m'
C_BLUE=$'\033[34m'
RULE="======================================================================"
THIN="----------------------------------------------------------------------"

nimlab() {
    "$PY" -m nimlab "$@"
}

# Non-interactive mode: pass straight through to the CLI.
if [ "$#" -gt 0 ]; then
    case "$1" in
        -h|--help)
            sed -n '2,13p' "$0"
            nimlab --help
            exit 0
            ;;
        sweep200|200)
            # Classic 200 Health & Fallback Sweep (route guessing, writes the verified fleet).
            "$PY" nvidia_playground.py --sweep
            exit $?
            ;;
        *)
            nimlab "$@"
            exit $?
            ;;
    esac
fi

banner() {
    clear
    printf '%s%s%s\n' "$C_CYAN$C_BOLD" "$RULE" "$C_RESET"
    printf '%s%*s%s\n' "$C_CYAN$C_BOLD" $(( (70 + ${#1}) / 2 )) "$1" "$C_RESET"
    printf '%s%s%s\n' "$C_CYAN$C_BOLD" "$RULE" "$C_RESET"
}

draw_header() {
    banner "NVIDIA NIM TEST LAB DASHBOARD"
    local key live inv mem cat_n eps
    if key="$(nimlab status key 2>/dev/null)"; then
        printf ' Active Key : %s%s%s\n' "$C_GREEN" "$key" "$C_RESET"
    else
        printf ' Active Key : %s[NOT SET] (option 8 to configure)%s\n' "$C_RED" "$C_RESET"
    fi
    live="$(nimlab status live 2>/dev/null || echo 0)"
    if [ "${live:-0}" -gt 0 ] 2>/dev/null; then
        printf ' Verified   : %s%s models pass 200 OK (data/models_verified.json)%s\n' "$C_GREEN" "$live" "$C_RESET"
    else
        inv="$(nimlab status discovered 2>/dev/null || echo 0)"
        if [ "${inv:-0}" -gt 0 ] 2>/dev/null; then
            printf ' Verified   : %snone yet, %s discovered (run the sweep, option 2)%s\n' "$C_YELLOW" "$inv" "$C_RESET"
        else
            printf ' Verified   : %snone yet (option D, then option 2)%s\n' "$C_RED" "$C_RESET"
        fi
    fi
    cat_n="$(nimlab status discovered 2>/dev/null || echo 0)"
    if [ "${cat_n:-0}" -gt 0 ] 2>/dev/null; then
        printf ' Discovered : %s%s models (site + docs + key)%s\n' "$C_GREEN" "$cat_n" "$C_RESET"
    else
        printf ' Discovered : %snot built yet (option D)%s\n' "$C_YELLOW" "$C_RESET"
    fi
    eps="$(nimlab status endpoints 2>/dev/null || echo 0)"
    printf ' Endpoints  : %s%s known endpoint URLs%s\n' "$C_BLUE" "$eps" "$C_RESET"
    mem="$(nimlab status memory 2>/dev/null || echo 0)"
    printf ' Memory DB  : %s%s records in vector store%s\n' "$C_BLUE" "$mem" "$C_RESET"
    if [ -n "${MCP_API_KEY:-}" ]; then
        printf ' MCP Key    : %sset (MCP_API_KEY)%s\n' "$C_GREEN" "$C_RESET"
    else
        printf ' MCP Key    : %snot set (MCP_API_KEY)%s\n' "$C_YELLOW" "$C_RESET"
    fi
    printf ' Roles      : %s#  category                       backend target%s\n' "$C_BOLD" "$C_RESET"
    local line
    while IFS= read -r line; do
        case "$line" in
            *" ----- "*) printf '   %s%s%s\n' "$C_YELLOW" "$line" "$C_RESET" ;;
            *" MCP   "*) printf '   %s%s%s\n' "$C_BLUE" "$line" "$C_RESET" ;;
            *) printf '   %s\n' "$line" ;;
        esac
    done < <(nimlab status roles 2>/dev/null)
    printf '%s%s%s\n' "$C_CYAN" "$THIN" "$C_RESET"
}

pause() {
    echo ""
    read -r -p "Press Enter to return to menu..." _
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
    printf '\n%s[!] NVIDIA_API_KEY is not set in the shell.%s\n' "$C_YELLOW" "$C_RESET"
    if read_key_into_env "Paste NVIDIA API key: "; then
        printf '%s[ok] Key exported for this session.%s\n' "$C_GREEN" "$C_RESET"
        return 0
    fi
    printf '%s[x] No key provided. Operation aborted.%s\n' "$C_RED" "$C_RESET"
    pause
    return 1
}

view_verified_fleet() {
    banner "VERIFIED 200 ENDPOINTS FLEET"
    nimlab fleet
    pause
}

data_menu() {
    banner "DATA STORES & LISTS (data/)"
    nimlab data
    echo ""
    echo "  1. Endpoints (active)           7. Verified 200 OK models"
    echo "  2. Endpoints (stale)            8. Dropped from verified (with last result)"
    echo "  3. All discovered models        9. Failing models (last result)"
    echo "  4. Retired / deprecated         10. Never tested"
    echo "  5. Removed from discovery       11. Benchmark history"
    echo "  6. Key /v1/models list          12. Re-run migration of old files"
    echo "  0. Return"
    local c
    read -r -p "Selection: " c
    case "$c" in
        1) nimlab data show endpoints ;;
        2) nimlab data show stale ;;
        3) nimlab data show discovered ;;
        4) nimlab data show retired; nimlab data show deprecated ;;
        5) nimlab data show removed ;;
        6) nimlab data show key ;;
        7) nimlab data show verified ;;
        8) nimlab data show dropped ;;
        9) nimlab data show failed ;;
        10) nimlab data show untested ;;
        11) nimlab data show benchmarks ;;
        12) nimlab data migrate ;;
        *) return 0 ;;
    esac
    pause
}

view_benchmark_report() {
    banner "LATEST BENCHMARK REPORT"
    nimlab report
    pause
}

quick_voice_synth() {
    banner "DIRECT MAGPIE VOICE SYNTHESIZER"
    ensure_key || return
    local phrase v_choice voice
    printf '\nEnter phrase to speak (or press Enter for default):\n'
    read -r -p "Phrase: " phrase
    printf '\nChoose Voice Profile:\n'
    echo "  1. Aria (Female) - Magpie-Multilingual.EN-US.Aria"
    echo "  2. Jason (Male)  - Magpie-Multilingual.EN-US.Jason"
    read -r -p "Select [1/2]: " v_choice
    voice="Magpie-Multilingual.EN-US.Aria"
    if [ "$v_choice" = "2" ]; then
        voice="Magpie-Multilingual.EN-US.Jason"
    fi
    printf '\n%sSending synthesis request to NVCF gateway...%s\n' "$C_YELLOW" "$C_RESET"
    # The phrase goes over stdin: any characters are safe.
    printf '%s' "$phrase" | nimlab tts --voice "$voice"
    pause
}

discover_menu() {
    banner "MODEL DISCOVERY (build.nvidia.com + docs + key)"
    echo "  1. Discover / refresh             (public pages, no key needed; syncs data/models_discovered.json)"
    echo "  2. Show the discovered models"
    echo "  3. List models on the site but missing from the key's list"
    echo "  4. List deprecated / retired models"
    echo "  0. Return"
    local c
    read -r -p "Selection: " c
    case "$c" in
        1) nimlab discover ;;
        2) nimlab discover --show ;;
        3) nimlab discover --show --flag on_site_not_in_key ;;
        4) nimlab discover --show --flag deprecated; nimlab discover --show --flag retired ;;
        *) return 0 ;;
    esac
    pause
}

sweep_menu() {
    banner "ENDPOINT SWEEP"
    echo "  1. Spec-driven sweep              (reads each model's page, probes the exact endpoint)"
    echo "  2. Spec-driven, selected kinds    (e.g. chat,vision,embedding)"
    echo "  3. Plan only                      (read specs, no API calls)"
    echo "  4. 200 Health & Fallback Sweep   (registered endpoints, then scraped spec)"
    echo "  0. Return"
    local c kinds
    read -r -p "Selection: " c
    case "$c" in
        1) ensure_key && nimlab sweep ;;
        2)
            read -r -p "Kinds: " kinds
            [ -n "$kinds" ] && ensure_key && nimlab sweep --kinds "$kinds"
            ;;
        3) nimlab sweep --plan-only ;;
        4) ensure_key && "$PY" nvidia_playground.py --sweep ;;
        *) return 0 ;;
    esac
    pause
}

judge_menu() {
    while true; do
        banner "JUDGE: MODEL LEADERBOARDS & ENTITY SCORING"
        echo "  1. Rank all model types           (chat, reasoning, coding, vision, OCR, embeddings, compactor, TTS)"
        echo "  2. Rank selected types            (comma list)"
        echo "  3. Score the entity vs soul.md    (current roles, or judge_settings.entity_combos)"
        echo "  4. Show latest leaderboards"
        echo "  5. Write winners into config_cluster.json (asks first)"
        echo "  0. Return"
        local c types
        read -r -p "Selection: " c
        case "$c" in
            1) ensure_key && nimlab judge rank; pause ;;
            2)
                read -r -p "Types (e.g. chat,coding,embeddings): " types
                if [ -n "$types" ]; then
                    ensure_key && nimlab judge rank --types "$types"
                fi
                pause
                ;;
            3) ensure_key && nimlab judge entity; pause ;;
            4) nimlab judge show; pause ;;
            5) nimlab judge apply; pause ;;
            *) return ;;
        esac
    done
}

manage_env() {
    banner "ENVIRONMENT & KEY SETTINGS"
    local shown k_choice
    shown="$(nimlab status key 2>/dev/null || echo '[NOT SET]')"
    printf 'Current NVIDIA_API_KEY: %s\n\n' "$shown"
    echo "  1. Enter / Update API Key (this session)"
    echo "  2. Persist API Key to ~/.nimlab_env (owner-only file, sourced from ~/.bashrc)"
    echo "  3. Clear Active Key and remove the persisted copy"
    echo "  0. Return"
    echo ""
    read -r -p "Selection: " k_choice
    case "$k_choice" in
        1)
            if read_key_into_env "Paste new NVIDIA API Key: "; then
                printf '%s[ok] NVIDIA_API_KEY updated in this session.%s\n' "$C_GREEN" "$C_RESET"
            fi
            pause
            ;;
        2)
            if [ -z "${NVIDIA_API_KEY:-}" ]; then
                printf '%s[!] No key active to persist. Set the key first.%s\n' "$C_RED" "$C_RESET"
            else
                nimlab persist-key
            fi
            pause
            ;;
        3)
            unset NVIDIA_API_KEY NGC_API_KEY
            nimlab forget-key
            printf '%s[!] Key cleared from this session.%s\n' "$C_YELLOW" "$C_RESET"
            pause
            ;;
        *)
            return
            ;;
    esac
}

roles_menu() {
    local role
    while true; do
        banner "ROLES (16 CATEGORIES)"
        nimlab roles show
        echo ""
        echo "  Change a role in the Entity Orchestrator Testbed (option 4, then 2)."
        echo "  c. Candidates for one role    m. Migrate old role keys now    0. Return"
        local sel
        read -r -p "Select: " sel || return
        case "$sel" in
            c|C)
                read -r -p "Role key (e.g. chart_parser, reranker): " role || return
                nimlab roles candidates "$role" --scope all
                pause
                ;;
            m|M) nimlab roles migrate; pause ;;
            *) return ;;
        esac
    done
}

# ==============================================================================
# MAIN TUI LOOP
# ==============================================================================
while true; do
    draw_header
    printf '%sPRIMARY WORKFLOW SUITES:%s\n' "$C_BOLD" "$C_RESET"
    printf '  %s1.%s NVIDIA Model Playground        (interactive single / compare / inspect)\n' "$C_CYAN" "$C_RESET"
    printf '  %s2.%s 200 Health & Fallback Sweep    (registered endpoints, then scraped spec)\n' "$C_CYAN" "$C_RESET"
    printf '  %sS.%s Spec-Driven Sweep              (reads each model spec, probes the exact endpoint)\n' "$C_CYAN" "$C_RESET"
    printf '  %s3.%s Multi-Modal Benchmark Suite    (embed recall, vision, LLM logic, RTF)\n' "$C_CYAN" "$C_RESET"
    printf '  %s4.%s Entity Orchestrator Testbed    (persona chat, vector memory, MCP tools)\n' "$C_CYAN" "$C_RESET"
    printf '  %s9.%s Judge                          (per-role leaderboards, entity scoring)\n' "$C_CYAN" "$C_RESET"
    printf '  %sD.%s Discover Models                (build.nvidia.com catalog beyond the key list)\n' "$C_CYAN" "$C_RESET"
    echo ""
    printf '%sFLEET INSPECTION & UTILITIES:%s\n' "$C_BOLD" "$C_RESET"
    printf '  %s5.%s View Verified 200 Fleet Matrix\n' "$C_CYAN" "$C_RESET"
    printf '  %s6.%s View Latest Benchmark Report\n' "$C_CYAN" "$C_RESET"
    printf '  %s7.%s Quick Magpie Voice Synthesizer\n' "$C_CYAN" "$C_RESET"
    printf '  %s8.%s API Key & Shell Settings\n' "$C_CYAN" "$C_RESET"
    printf '  %sL.%s Data Stores & Lists            (endpoints, discovered, verified, history)\n' "$C_CYAN" "$C_RESET"
    printf '  %sR.%s Roles                          (16 categories: backends, candidates)\n' "$C_CYAN" "$C_RESET"
    echo ""
    printf '  %s0.%s Exit\n' "$C_RED" "$C_RESET"
    printf '%s%s%s\n' "$C_CYAN" "$THIN" "$C_RESET"
    read -r -p "Enter selection [0-9, S, D, L, R]: " choice || exit 0

    case "$choice" in
        1) ensure_key && "$PY" nvidia_playground.py ;;
        2) ensure_key && "$PY" nvidia_playground.py --sweep; pause ;;
        s|S) sweep_menu ;;
        3) ensure_key && "$PY" nvidia_benchmark_suite.py ;;
        4) ensure_key && "$PY" orchestrator_testbed.py ;;
        5) view_verified_fleet ;;
        6) view_benchmark_report ;;
        7) quick_voice_synth ;;
        8) manage_env ;;
        9) judge_menu ;;
        d|D) discover_menu ;;
        l|L) data_menu ;;
        r|R) roles_menu ;;
        0)
            clear
            printf '%sExiting NVIDIA NIM test lab.%s\n\n' "$C_GREEN" "$C_RESET"
            exit 0
            ;;
        *)
            printf '%sInvalid option.%s\n' "$C_RED" "$C_RESET"
            sleep 0.8
            ;;
    esac
done
