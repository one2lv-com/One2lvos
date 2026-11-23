"""The machine Nim Lab runs on (3.7.4): Termux on a phone, or a Linux VPS
such as an Oracle Cloud Always Free VM.Standard.E2.1.Micro (x86_64, 1 GB RAM)
with Ubuntu or Oracle Linux.

detect() reads /etc/os-release, /proc/meminfo, the Python install and a few
commands; every input can be passed in, so tests run with mocked platforms.
checks() turns that into (level, message, fix) rows for `nimlab doctor`,
`nimlab platform`, setup and the Tests menu. Nothing here changes the system.
"""

import os
import shutil
import subprocess
import sys
import sysconfig

LOW_RAM_MB = 1536        # under this, with no swap, warn (a 1 GB VPS)

CLOUDFLARE_PKG_DOCS = "https://pkg.cloudflare.com/index.html"
APT_CLOUDFLARED = (
    "sudo mkdir -p --mode=0755 /usr/share/keyrings\n"
    "curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg "
    ">/dev/null\n"
    "echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' "
    "| sudo tee /etc/apt/sources.list.d/cloudflared.list\n"
    "sudo apt-get update && sudo apt-get install cloudflared")
DNF_CLOUDFLARED = (
    "curl -fsSl https://pkg.cloudflare.com/cloudflared.repo | sudo tee /etc/yum.repos.d/cloudflared.repo\n"
    "sudo dnf install cloudflared")
SWAP_CMDS = (
    "sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile\n"
    "echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab")


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def parse_os_release(text):
    out = {}
    for line in (text or "").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def parse_meminfo(text):
    """-> (total_mb, swap_mb); None when unknown."""
    vals = {}
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            try:
                vals[parts[0][:-1]] = int(parts[1]) // 1024
            except ValueError:
                pass
    return vals.get("MemTotal"), vals.get("SwapTotal")


def externally_managed(stdlib=None, prefix=None, base_prefix=None):
    """PEP 668: the system Python refuses pip installs (Ubuntu 23.04+, Debian
    12). False inside a venv, where pip is fine."""
    prefix = sys.prefix if prefix is None else prefix
    base_prefix = getattr(sys, "base_prefix", sys.prefix) if base_prefix is None else base_prefix
    if prefix != base_prefix:
        return False
    stdlib = stdlib or sysconfig.get_paths().get("stdlib") or ""
    return os.path.isfile(os.path.join(stdlib, "EXTERNALLY-MANAGED"))


def in_venv(prefix=None, base_prefix=None):
    prefix = sys.prefix if prefix is None else prefix
    base_prefix = getattr(sys, "base_prefix", sys.prefix) if base_prefix is None else base_prefix
    return prefix != base_prefix


def _linger(user, run, exists):
    if not user:
        return None
    if exists(f"/var/lib/systemd/linger/{user}"):
        return True
    try:
        r = run(["loginctl", "show-user", user, "-p", "Linger"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and "Linger=" in (r.stdout or ""):
            return r.stdout.strip().endswith("yes")
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False


def detect(env=None, os_release=None, meminfo=None, which=shutil.which, exists=os.path.exists, euid=None,
           run=subprocess.run, cpu_count=None, machine=None, py_version=None, pep668=None, venv=None):
    """-> dict describing this machine. Every input can be faked."""
    env = os.environ if env is None else env
    termux = bool(env.get("TERMUX_VERSION")) or "com.termux" in env.get("PREFIX", "")
    osr = parse_os_release(_read("/etc/os-release") if os_release is None else os_release)
    os_id = "termux" if termux else (osr.get("ID") or "linux").lower()
    like = (osr.get("ID_LIKE") or "").lower().split()
    fam = {os_id, *like}
    if termux:
        pm = "pkg"
    elif fam & {"debian", "ubuntu"}:
        pm = "apt"
    elif fam & {"rhel", "fedora", "centos", "ol", "amzn"}:
        pm = "dnf" if which("dnf") or not which("yum") else "yum"
    else:
        pm = "apt" if which("apt-get") else ("dnf" if which("dnf") else None)
    total, swap = parse_meminfo(_read("/proc/meminfo") if meminfo is None else meminfo)
    uid = os.geteuid() if euid is None and hasattr(os, "geteuid") else (euid or 0)
    user = env.get("USER") or env.get("LOGNAME") or ""
    systemd = (not termux) and (exists("/run/systemd/system") or bool(which("systemctl")))
    import platform as _pf
    return {
        "termux": termux,
        "os_id": os_id,
        "os_name": "Termux (Android)" if termux else (osr.get("PRETTY_NAME") or osr.get("NAME") or "Linux"),
        "family": "termux" if termux else ("debian" if pm == "apt" else ("rhel" if pm in ("dnf", "yum")
                                                                           else "other")),
        "pkg": pm,
        "machine": machine or _pf.machine(),
        "python": py_version or ".".join(str(x) for x in sys.version_info[:3]),
        "venv": in_venv() if venv is None else venv,
        "pep668": externally_managed() if pep668 is None else pep668,
        "ffmpeg": which("ffmpeg"),
        "cloudflared": which("cloudflared"),
        "termux_api": bool(which("termux-microphone-record")),
        "systemd": systemd,
        "linger": _linger(user, run, exists) if systemd and uid != 0 else None,
        "root": uid == 0 and not termux,
        "user": user,
        "mem_mb": total,
        "swap_mb": swap,
        "cpus": cpu_count if cpu_count is not None else (os.cpu_count() or 1),
    }


# ---------------------------------------------------------------------------
# hints
# ---------------------------------------------------------------------------
def install_hint(tool, info):
    """The install command for a system tool on this platform."""
    pm = info.get("pkg")
    osid = info.get("os_id")
    if tool == "venv":
        return {"apt": "sudo apt-get install -y python3-venv python3-pip",
                "dnf": "sudo dnf install -y python3-pip   (venv is part of python3 on Oracle Linux)",
                "yum": "sudo yum install -y python3-pip",
                "pkg": "pkg install python"}.get(pm, "install python3-venv with your package manager")
    if tool == "ffmpeg":
        if pm == "pkg":
            return "pkg install ffmpeg"
        if pm == "apt":
            return "sudo apt-get install -y ffmpeg"
        if pm in ("dnf", "yum"):
            if osid == "ol":
                return ("Oracle Linux has no ffmpeg in its base repos: enable EPEL and RPM Fusion (free), "
                        "then sudo dnf install -y ffmpeg")
            return f"sudo {pm} install -y ffmpeg (needs EPEL and RPM Fusion free on RHEL-like systems)"
        return "install ffmpeg with your package manager"
    if tool == "cloudflared":
        if pm == "pkg":
            return "pkg install cloudflared   (or: nimlab serve tunnel install)"
        base = "nimlab serve tunnel install downloads it from Cloudflare's releases, or use Cloudflare's package repo"
        if pm == "apt":
            return f"{base}:\n{APT_CLOUDFLARED}"
        if pm in ("dnf", "yum"):
            return f"{base}:\n{DNF_CLOUDFLARED.replace('dnf', pm)}"
        return f"{base} ({CLOUDFLARE_PKG_DOCS})"
    return ""


def cloudflared_missing_message(info=None):
    info = info or detect()
    return ("cloudflared is not installed, so the public tunnel cannot start (the server still works locally). "
            "Install it: " + install_hint("cloudflared", info))


def low_memory(info):
    m, s = info.get("mem_mb"), info.get("swap_mb")
    return bool(m) and m < LOW_RAM_MB and not s


def workers(requested=3, info=None):
    """Parallel probes for the 200 OK test / discovery, scaled to the box: a
    1 GB VPS with 1-2 CPUs gets 2, under 768 MB gets 1. Never more than asked."""
    info = info or detect()
    n = max(1, int(requested or 1))
    m = info.get("mem_mb") or 0
    cpus = info.get("cpus") or 1
    cap = n
    if m and m < 768:
        cap = 1
    elif m and m < LOW_RAM_MB:
        cap = 2
    if not info.get("termux"):
        cap = min(cap, max(2, cpus * 2))
    return max(1, min(n, cap))


def checks(info=None):
    """-> [(level, message, fix)] with level ok | warn | fail | info."""
    i = info or detect()
    rows = []
    rows.append(("info", f"{i['os_name']}, {i['machine']}, {i['cpus']} CPU, Python {i['python']}", ""))
    major, minor = (int(x) for x in i["python"].split(".")[:2])
    rows.append((("ok" if (major, minor) >= (3, 9) else "fail"), f"Python {i['python']}"
                 + ("" if (major, minor) >= (3, 9) else " is too old (3.9 or newer)"),
                 "" if (major, minor) >= (3, 9) else install_hint("venv", i)))
    if i["venv"]:
        rows.append(("ok", f"Python packages go into a venv ({sys.prefix})", ""))
    elif i["pep668"]:
        rows.append(("warn", "The system Python is externally managed (PEP 668): pip refuses to install here",
                     "./start.sh install makes a venv (.venv in the project) and uses it; needs: "
                     + install_hint("venv", i)))
    else:
        rows.append(("ok", "pip can install packages for this Python", ""))
    rows.append((("ok" if i["ffmpeg"] else "warn"),
                 "ffmpeg found" if i["ffmpeg"] else "ffmpeg is missing (voice notes are converted with it)",
                 "" if i["ffmpeg"] else install_hint("ffmpeg", i)))
    from . import tunnel
    cf = i["cloudflared"] or tunnel.find_cloudflared()
    rows.append((("ok" if cf else "warn"),
                 f"cloudflared found ({cf})" if cf else "cloudflared is missing (needed only for the public tunnel)",
                 "" if cf else install_hint("cloudflared", i)))
    if i["termux"]:
        rows.append((("ok" if i["termux_api"] else "warn"),
                     "Termux:API found (terminal voice call)" if i["termux_api"] else
                     "Termux:API is missing: the terminal voice call needs it",
                     "" if i["termux_api"] else "pkg install termux-api, plus the Termux:API app"))
    else:
        rows.append(("info", "Not Termux: the terminal voice call and the battery settings are off here. "
                     "Telegram voice notes still work.", ""))
        if i["root"]:
            rows.append(("warn", "Running as root", "Use a regular user: sudo adduser nimlab, then run Nim Lab as "
                         "that user (the service is a systemd user unit)"))
        if i["systemd"] and i["linger"] is False:
            rows.append(("warn", "systemd linger is off: the service stops when you log out and does not start at boot",
                         f"loginctl enable-linger {i['user'] or '$USER'}   (may need sudo)"))
        elif i["systemd"] and i["linger"]:
            rows.append(("ok", "systemd linger is on (the user service survives logout and starts at boot)", ""))
        elif not i["systemd"]:
            rows.append(("info", "No systemd: the built-in supervisor runs the service (no start at boot)", ""))
    m, s = i.get("mem_mb"), i.get("swap_mb")
    if m:
        if low_memory(i):
            rows.append(("warn", f"{m} MB RAM and no swap: pip installs and the 200 OK test can run out of memory",
                         "add a 2 GB swapfile:\n" + SWAP_CMDS))
        else:
            rows.append(("ok", f"{m} MB RAM, {s or 0} MB swap", ""))
    return rows


def lines(info=None):
    out = []
    for level, msg, fix in checks(info):
        tag = {"ok": "[ok]", "warn": "[!] ", "fail": "[x] ", "info": "    "}[level]
        out.append(f"{tag} {msg}")
        for ln in (fix or "").splitlines():
            out.append(f"       {ln}")
    return out


NETWORK_NOTE = ("On Oracle Cloud an open port needs two changes: an ingress rule in the VCN security list and "
                "the instance firewall (Ubuntu images ship iptables rules that only allow port 22). The Cloudflare "
                "tunnel (quick or named) needs neither: the server stays on 127.0.0.1 and cloudflared connects out.")


def cmd_platform(args):
    from . import colors as C, paint
    if C.enabled():
        print(C.header("PLATFORM"))
    for ln in paint.platform_lines(lines()):
        print(ln)
    if not detect()["termux"]:
        print()
        print((C.label("Network:") + " " + C.dim(NETWORK_NOTE)) if C.enabled() else "Network: " + NETWORK_NOTE)
    return 0


def add_parser(sub):
    p = sub.add_parser("platform", help="this machine: OS, Python, venv, ffmpeg, cloudflared, RAM/swap, linger")
    p.set_defaults(fn=cmd_platform)
