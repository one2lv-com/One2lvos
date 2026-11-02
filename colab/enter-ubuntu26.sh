#!/usr/bin/env bash
# Login shell in the One2lvOS Ubuntu 26 root. ttyd runs this once per browser terminal.
#   O2_ROOT (default /opt/ubuntu26), O2_USER (default one2lv), O2_SHELL_AS=user|root
ROOT="${O2_ROOT:-/opt/ubuntu26}"
USERNAME="${O2_USER:-one2lv}"
AS="${O2_SHELL_AS:-user}"
MODE="$(cat "$ROOT/.o2-mode" 2>/dev/null || echo chroot)"
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

ENVV=(/usr/bin/env -i TERM="${TERM:-xterm-256color}" LANG=C.UTF-8 COLORTERM=truecolor
      PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin)
if [ "$AS" = root ]; then CMD=(/bin/bash --login); ENVV+=(HOME=/root)
else CMD=(/bin/su - "$USERNAME"); fi

if [ "$MODE" = chroot ]; then
  # Re-bind anything a Colab restart of the shell dropped.
  for d in proc sys dev dev/pts; do
    mountpoint -q "$ROOT/$d" || { [ "$d" = proc ] && $SUDO mount -t proc proc "$ROOT/proc" 2>/dev/null; } \
      || $SUDO mount --bind "/$d" "$ROOT/$d" 2>/dev/null
  done
  exec $SUDO chroot "$ROOT" "${ENVV[@]}" "${CMD[@]}"
else
  # proot fallback (no chroot/mount allowed): a root shell only; su to other users does not work under proot.
  exec "${ENVV[@]}" HOME=/root proot -0 -r "$ROOT" -b /proc -b /sys -b /dev -b /dev/pts -w /root /bin/bash --login
fi
