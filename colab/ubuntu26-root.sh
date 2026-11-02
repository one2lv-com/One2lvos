#!/usr/bin/env bash
# One2lvOS Colab: build (or refresh) a real Ubuntu 26 userland and point apt at Ubuntu 26 mirrors.
#
# Colab's own image is an older Ubuntu and its kernel/Python runtime can't be dist-upgraded in place
# without breaking the notebook, so Ubuntu 26 runs as a full root filesystem (official ubuntu-base
# tarball) entered with chroot (proot if chroot/mount are not allowed). apt, sudo and su inside it
# are the real Ubuntu 26 packages.
#
# Env:
#   O2_ROOT            where the root lives            (default /opt/ubuntu26)
#   O2_UBUNTU          26.04.1 | 26.04 | 26.10         (default 26.04.1)
#   O2_MIRROR          main archive mirror             (default http://archive.ubuntu.com/ubuntu/)
#   O2_SECURITY_MIRROR security mirror                 (default http://security.ubuntu.com/ubuntu/)
#   O2_USER            login user with sudo            (default one2lv)
#   O2_ROOT_PASSWORD   password for root (su) and the user; read from env, never printed
#   O2_UPGRADE         1 = apt full-upgrade during setup (default 1)
#   O2_EXTRA_PKGS      extra packages to install
set -euo pipefail

ROOT="${O2_ROOT:-/opt/ubuntu26}"
REL="${O2_UBUNTU:-26.04.1}"
MIRROR="${O2_MIRROR:-http://archive.ubuntu.com/ubuntu/}"
SECMIRROR="${O2_SECURITY_MIRROR:-http://security.ubuntu.com/ubuntu/}"
USERNAME="${O2_USER:-one2lv}"
UPGRADE="${O2_UPGRADE:-1}"
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

case "$REL" in
  26.04*) CODENAME=resolute; SERIES=26.04 ;;
  26.10*) CODENAME=stonking; SERIES=26.10 ;;
  *) echo "Unsupported release $REL (use 26.04.1, 26.04 or 26.10)"; exit 2 ;;
esac
BASEURL="https://cdimage.ubuntu.com/ubuntu-base/releases/${SERIES}/release"
TARBALL="ubuntu-base-${REL}-base-amd64.tar.gz"
CACHE="${O2_CACHE:-/tmp/.o2-cache}"
mkdir -p "$CACHE"
$SUDO mkdir -p "$ROOT"
# sudo and su need setuid bits: the root must not sit on a nosuid filesystem.
if [[ ",$(findmnt -n -o OPTIONS -T "$ROOT" 2>/dev/null || true)," == *,nosuid,* ]]; then
  echo "!! $ROOT is on a nosuid filesystem, so sudo/su would not work there. Set O2_ROOT elsewhere (for example /opt/ubuntu26)."
  exit 3
fi

echo "== Host: $(. /etc/os-release; echo "$PRETTY_NAME") · kernel $(uname -r)"
echo "== Target: Ubuntu ${REL} (${CODENAME}) at ${ROOT}"

# ── 1. Download + verify the official ubuntu-base tarball ─────────────────────
if [ ! -x "$ROOT/bin/bash" ]; then
  echo "== Downloading ${TARBALL}"
  curl -fsSL --retry 3 -o "$CACHE/SHA256SUMS" "$BASEURL/SHA256SUMS"
  [ -s "$CACHE/$TARBALL" ] || curl -fL --retry 3 --progress-bar -o "$CACHE/$TARBALL" "$BASEURL/$TARBALL"
  ( cd "$CACHE" && grep " \*\?${TARBALL}\$" SHA256SUMS | sed 's/ \*/  /' | sha256sum -c - )
  $SUDO tar -xzpf "$CACHE/$TARBALL" -C "$ROOT" --numeric-owner
else
  echo "== Root already present, refreshing it"
fi

# ── 2. Decide how to enter it: chroot (preferred) or proot ────────────────────
MODE=chroot
mountpt() { mountpoint -q "$1" 2>/dev/null; }
if ! { $SUDO mkdir -p "$ROOT/proc" && { mountpt "$ROOT/proc" || $SUDO mount -t proc proc "$ROOT/proc" 2>/dev/null || $SUDO mount --bind /proc "$ROOT/proc" 2>/dev/null; } \
       && $SUDO chroot "$ROOT" /bin/true 2>/dev/null; }; then
  MODE=proot
fi
if [ "$MODE" = chroot ]; then
  for d in sys dev dev/pts; do
    $SUDO mkdir -p "$ROOT/$d"
    mountpt "$ROOT/$d" || $SUDO mount --bind "/$d" "$ROOT/$d" 2>/dev/null || echo "   (could not bind /$d)"
  done
  $SUDO mkdir -p "$ROOT/dev/shm"
else
  echo "== chroot/mount not allowed here: using proot"
  command -v proot >/dev/null || $SUDO apt-get install -y -qq proot >/dev/null 2>&1 || {
    curl -fsSL -o /usr/local/bin/proot https://proot.gitlab.io/proot/bin/proot && chmod +x /usr/local/bin/proot; }
fi
echo "$MODE" | $SUDO tee "$ROOT/.o2-mode" >/dev/null

in_root() {  # run a command as root inside Ubuntu 26
  local env=(/usr/bin/env -i HOME=/root TERM=xterm-256color LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive
             PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin)
  if [ "$MODE" = chroot ]; then $SUDO chroot "$ROOT" "${env[@]}" /bin/bash -c "$1"
  # proot: set the environment on the host side (Ubuntu 26's multicall env refuses to run under proot).
  else "${env[@]}" proot -0 -r "$ROOT" -b /proc -b /sys -b /dev -b /dev/pts -w /root /bin/bash -c "$1"; fi
}

# ── 3. DNS + Ubuntu 26 mirrors ────────────────────────────────────────────────
$SUDO rm -f "$ROOT/etc/resolv.conf"
if grep -q '^nameserver' /etc/resolv.conf 2>/dev/null && ! grep -q '^nameserver 127\.' /etc/resolv.conf; then
  $SUDO cp /etc/resolv.conf "$ROOT/etc/resolv.conf"
else
  printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\n' | $SUDO tee "$ROOT/etc/resolv.conf" >/dev/null
fi
echo "one2lvos-colab" | $SUDO tee "$ROOT/etc/hostname" >/dev/null
grep -q one2lvos-colab "$ROOT/etc/hosts" 2>/dev/null || \
  printf '127.0.0.1 localhost\n127.0.1.1 one2lvos-colab\n::1 localhost ip6-localhost\n' | $SUDO tee "$ROOT/etc/hosts" >/dev/null

$SUDO tee "$ROOT/etc/apt/sources.list.d/ubuntu.sources" >/dev/null <<EOF
# Ubuntu ${REL} (${CODENAME}) mirrors, written by One2lvOS Colab
Types: deb
URIs: ${MIRROR}
Suites: ${CODENAME} ${CODENAME}-updates ${CODENAME}-backports
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: ${SECMIRROR}
Suites: ${CODENAME}-security
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
$SUDO rm -f "$ROOT/etc/apt/sources.list"
# Containers have no init: never try to start services from maintainer scripts.
printf '#!/bin/sh\nexit 101\n' | $SUDO tee "$ROOT/usr/sbin/policy-rc.d" >/dev/null
$SUDO chmod +x "$ROOT/usr/sbin/policy-rc.d"
printf 'APT::Get::Assume-Yes "true";\nDpkg::Options { "--force-confdef"; "--force-confold"; };\n' \
  | $SUDO tee "$ROOT/etc/apt/apt.conf.d/90one2lvos" >/dev/null

# ── 4. apt update / upgrade / base tools ──────────────────────────────────────
echo "== apt update (Ubuntu ${REL} mirrors)"
in_root "apt-get update"
if [ "$UPGRADE" = 1 ]; then
  echo "== apt full-upgrade"
  in_root "apt-get -y full-upgrade"
fi
PKGS="sudo passwd login bash-completion ca-certificates curl wget git nano vim-tiny less procps psmisc \
iproute2 iputils-ping net-tools htop tmux unzip xz-utils python3 python3-pip python3-venv locales tzdata \
software-properties-common gnupg lsb-release ${O2_EXTRA_PKGS:-}"
echo "== Installing base tools"
in_root "apt-get install -y --no-install-recommends $PKGS"
in_root "locale-gen en_US.UTF-8 >/dev/null 2>&1 || true"

# ── 5. User with sudo, root password for su ───────────────────────────────────
in_root "id -u $USERNAME >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo $USERNAME"
in_root "usermod -aG sudo $USERNAME"
printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\nDefaults !fqdn\n' "$USERNAME" | $SUDO tee "$ROOT/etc/sudoers.d/90-one2lvos" >/dev/null
$SUDO chmod 0440 "$ROOT/etc/sudoers.d/90-one2lvos"
if [ -n "${O2_ROOT_PASSWORD:-}" ]; then
  # chpasswd reads user:password from stdin, so the password never appears in a process list.
  printf 'root:%s\n%s:%s\n' "$O2_ROOT_PASSWORD" "$USERNAME" "$O2_ROOT_PASSWORD" | {
    if [ "$MODE" = chroot ]; then $SUDO chroot "$ROOT" /usr/sbin/chpasswd
    else proot -0 -r "$ROOT" /usr/sbin/chpasswd; fi; }
fi
$SUDO tee "$ROOT/etc/profile.d/one2lvos.sh" >/dev/null <<'EOF'
export LANG=C.UTF-8
if [ -n "$PS1" ] && [ -z "$O2_MOTD_SHOWN" ]; then
  export O2_MOTD_SHOWN=1
  . /etc/os-release
  printf '\033[1;36m One2lvOS · %s (%s) on Google Colab\033[0m\n' "$PRETTY_NAME" "$VERSION_CODENAME"
  printf ' sudo apt update · sudo apt upgrade · sudo su · su -   (kernel is Colab'"'"'s: %s)\n\n' "$(uname -r)"
fi
EOF

echo "== Done: $(in_root '. /etc/os-release; echo $PRETTY_NAME') via $MODE"
in_root "apt-get -s upgrade 2>/dev/null | grep -c '^Inst' | xargs -I{} echo '   packages still upgradable: {}'"
