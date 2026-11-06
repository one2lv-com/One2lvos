#!/bin/bash
# Who Dat boot hook - sourced by startos.sh after .env is loaded.
#
#  First boot on a new installation:
#    if there is no identity yet and ONE2LVOS_OWNER_EMAIL is set (or you are at a
#    terminal and type your email), this installation generates its OWN keys:
#    an owner key, a system key, a vault root key and a local registry.
#    Nothing from anyone else's install is reused.
#  Every boot after that:
#    the system answers "Who Dat?" with a signature from its own key, and the keys
#    you stored in your vault are exported into this shell for the services.
#    Variables already set (for example from .env) are left alone.
#    If the handshake fails, nothing is exported and the boot carries on with .env.
#
#  WHODAT_BOOT=0   skip all of this
#  python3 -m whodat --help   for everything else

whodat_boot() {
    [ "${WHODAT_BOOT:-auto}" = "0" ] && { echo "  ⏭  Who Dat: skipped (WHODAT_BOOT=0)"; return 0; }
    local root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
    local py="${WHODAT_PYTHON:-python3}"
    local home="${WHODAT_HOME:-$HOME/.config/one2lvos/whodat}"
    local log="$root/logs/whodat-boot.log"
    mkdir -p "$root/logs" 2>/dev/null || true

    if ! (cd "$root" && "$py" -c "import whodat" 2>/dev/null); then
        echo "  ⚠  Who Dat: python package missing (pip install -r requirements.txt) - skipped"
        return 0
    fi

    if [ ! -f "$home/identity/identity.json" ]; then
        local email="${ONE2LVOS_OWNER_EMAIL:-}"
        if [ -z "$email" ] && [ -t 0 ] && [ -t 1 ]; then
            echo "  Who Dat: this installation has no keys yet."
            read -r -p "  Enter your email to generate them (Enter to skip): " email || email=""
        fi
        if [ -z "$email" ]; then
            echo "  ⏭  Who Dat: no identity yet. Set ONE2LVOS_OWNER_EMAIL or run: python3 -m whodat init --email you@example.com"
            return 0
        fi
        if (cd "$root" && "$py" -m whodat init --email "$email" ${WHODAT_REGISTRY_URL:+--registry-url "$WHODAT_REGISTRY_URL"}) >>"$log" 2>&1; then
            echo "  ✓ Who Dat: generated this installation's keys for $email (details: logs/whodat-boot.log)"
            echo "    Add your own API keys:  python3 -m whodat secret put NVIDIA_API_KEY   (or: secret import .env)"
        else
            echo "  ⚠  Who Dat: key generation failed - see logs/whodat-boot.log"
            return 0
        fi
    fi

    local out rc=0
    out="$(cd "$root" && "$py" -m whodat boot-env --only-unset 2>>"$log")" || rc=$?
    if [ "$rc" = "0" ] && [ -n "$out" ]; then
        eval "$out"
        echo "  ✓ Who Dat: handshake verified; keys loaded from your vault: ${WHODAT_LOADED_COUNT:-0}"
    else
        echo "  ⚠  Who Dat: handshake failed - no vault keys loaded (see logs/whodat-boot.log)"
    fi
    unset out
    return 0
}
