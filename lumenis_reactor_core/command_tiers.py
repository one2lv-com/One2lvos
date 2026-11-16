"""Risk tiers (L0-L3) for shell commands that a supervisor (Autonomis) or its AI adviser wants to run.

Same scale as the reactor's tool engine (tool_engine.tier_of):
  L0  read-only look      (ps, ss, df, free, tail of a log, git status, curl GET to localhost ...)   runs
  L1  small local change  (mkdir, ln -s, git fetch, chmod +x on a repo script)                     runs, logged
  L2  service or package  (pip/apt/npm install, pkill, bash <repo script>.sh, systemctl restart)   held for One2lv
  L3  destructive/unknown (rm, mv, dd, sudo, git push/reset, pipes, redirects, anything unlisted)  held + 2nd confirm
Commands never pass through a shell: they are split with shlex and run as an argument list, so shell syntax
(| ; && > $( ` ) is L3 by definition. Dependency-free: autonomis-agent.py loads this file by path.
"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SHELL_SYNTAX = re.compile(r"[|;&<>`]|\$\(|\$\{|\n")
_SECRET_PATH = re.compile(r"(\.env|token|secret|passw|\.pem|\.key\b|id_rsa|id_ed25519|credential|vault|keys?_?pack)", re.I)
_DESTRUCTIVE = {"rm", "rmdir", "mv", "dd", "mkfs", "shred", "truncate", "sudo", "su", "reboot", "shutdown",
                "halt", "poweroff", "kill", "killall", "chown", "crontab", "iptables", "ufw", "passwd", "useradd",
                "userdel", "mount", "umount", "fdisk", "parted", "wget", "scp", "rsync", "ssh", "sftp", "nc",
                "python", "python3", "node", "perl", "ruby", "sh", "zsh", "eval", "exec", "source", "tee"}
_READ_ONLY = {"ps", "ss", "netstat", "df", "du", "free", "uptime", "ls", "pgrep", "which", "whoami", "id",
              "uname", "date", "hostname", "nproc", "lsof", "stat", "wc", "cat", "tail", "head", "grep", "journalctl"}
_FILE_READERS = {"cat", "tail", "head", "grep", "stat", "wc", "ls", "du"}


def split(command: str) -> list[str] | None:
    try:
        return shlex.split(command)
    except ValueError:
        return None


def _inside_repo(path: str) -> bool:
    p = Path(path) if os.path.isabs(path) else REPO_ROOT / path
    try:
        p.resolve().relative_to(REPO_ROOT)
        return True
    except (ValueError, OSError):
        return False


def classify(command: str) -> tuple[int, str]:
    """Return (tier, reason) for a command string."""
    command = (command or "").strip()
    if not command:
        return 3, "empty command"
    if _SHELL_SYNTAX.search(command):
        return 3, "shell syntax (pipe, redirect, chaining or substitution)"
    argv = split(command)
    if not argv:
        return 3, "cannot be parsed"
    if any(_SECRET_PATH.search(a) for a in argv[1:]):
        return 3, "touches a secret file"
    prog = os.path.basename(argv[0])
    args = argv[1:]
    if prog == "cd":
        return 3, "cd does nothing without a shell"
    if prog in ("pip", "pip3") or (prog.startswith("python") and args[:2] == ["-m", "pip"]):
        if "install" in args or "uninstall" in args:
            return (3, "pip uninstall") if "uninstall" in args else (2, "package install")
        return (0, "pip read") if args[:1] in (["list"], ["show"], ["check"]) or args[2:3] in (["list"], ["check"]) else (3, "pip command")
    if prog in ("apt", "apt-get"):
        return (2, "package install") if args[:1] == ["install"] or "install" in args else (3, "apt command")
    if prog == "npm":
        return (2, "package install") if args[:1] in (["install"], ["ci"], ["i"]) else (
            (0, "npm read") if args[:1] == ["ls"] else (3, "npm command"))
    if prog in ("pkill", "systemctl", "service"):
        if prog == "systemctl" and args[:1] in (["status"], ["is-active"], ["list-units"]):
            return 0, "service status"
        return 2, "stops or restarts a service"
    if prog == "bash":
        if len(args) == 1 and args[0].endswith(".sh") and _inside_repo(args[0]):
            return 2, "runs a repo script"
        return 3, "bash outside a single repo script"
    if prog == "git":
        sub = args[:1]
        if sub in (["status"], ["log"], ["diff"], ["show"], ["branch"], ["remote"], ["rev-parse"]):
            return 0, "git read"
        if sub == ["fetch"]:
            return 1, "git fetch"
        if sub in (["pull"], ["checkout"], ["switch"], ["stash"], ["commit"], ["merge"]):
            return 2, "changes the working copy"
        return 3, "git push/reset/clean or other"
    if prog == "mkdir":
        return (1, "creates a folder in the repo") if args and all(_inside_repo(a) for a in args if not a.startswith("-")) else (2, "creates a folder outside the repo")
    if prog == "ln":
        targets = [a for a in args if not a.startswith("-")]
        return (1, "symlink in the repo") if "-s" in args and targets and _inside_repo(targets[-1]) else (2, "link outside the repo")
    if prog == "chmod":
        mode = args[0] if args else ""
        files = args[1:]
        if mode in ("+x", "u+x", "755") and files and all(_inside_repo(f) for f in files):
            return 1, "makes a repo script executable"
        return 3, "permission change"
    if prog == "curl":
        bad = {"-X", "--request", "-d", "--data", "--data-raw", "--data-binary", "-F", "--form", "-T",
               "--upload-file", "-o", "--output", "-O"}
        urls = [a for a in args if a.startswith("http")]
        if not (set(args) & bad) and urls and all(re.match(r"https?://(127\.0\.0\.1|localhost)(:\d+)?(/|$)", u) for u in urls):
            return 0, "local GET"
        return 3, "network request"
    if prog in _READ_ONLY:
        if prog in _FILE_READERS:
            files = [a for a in args if not a.startswith("-")]
            if prog == "grep":
                files = files[1:]
            if not all(_inside_repo(f) or f.startswith("/proc/") for f in files):
                return 3, "reads outside the repo"
        return 0, "read-only"
    if prog in _DESTRUCTIVE:
        return 3, f"{prog} is destructive or runs arbitrary code"
    return 3, "not a known command"


def run_argv(command: str, timeout: float = 120.0) -> dict:
    """Run a command without a shell, in the repo folder. Returns code and output tails."""
    import subprocess

    argv = split(command) or []
    if not argv:
        return {"ok": False, "error": "cannot be parsed"}
    try:
        res = subprocess.run(argv, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout,
                             stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return {"ok": False, "error": f"{argv[0]}: not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timed out after {timeout:.0f}s"}
    return {"ok": res.returncode == 0, "exit_code": res.returncode,
            "stdout": res.stdout[-2000:], "stderr": res.stderr[-1000:]}
