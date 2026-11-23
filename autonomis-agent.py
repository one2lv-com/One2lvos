#!/usr/bin/env python3
"""
Autonomis - autonomous monitor, restarter and installer for One2lvOS.

Runs as a daemon. Every cycle it:

  1. checks the runtime (apt packages, pip requirements, npm installs, the
     cloudflared binary) and repairs what is missing - this is what makes the
     stack survive a container rebuild;
  2. health-checks every service and restarts only the ones that are down.
     Restarts are limited: each service has an exponential backoff, a cap on
     attempts, and a cool-off period once the cap is hit. Before a restart,
     any old copy of the service (the process on its port, or one running
     the same command) is stopped, so a restart never leaves duplicates;
  3. makes sure the public bridge tunnel is alive (a live cloudflared
     process, not just a pid number in a file) and the published URL answers;
  4. when a service keeps failing, asks an LLM (LM Studio, OpenAI-compatible)
     what to do and runs the reply if it is on the command allowlist;
  5. posts a note to Discord when something needs attention.

Everything is driven by autonomis-config.json. The repo root is detected from
this file's location, so the agent works on any machine the repo is cloned to.

Usage:
    python3 autonomis-agent.py            # run in the foreground
    python3 autonomis-agent.py --status   # one report, no changes
    python3 autonomis-agent.py --once     # one repair pass, then exit
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
# Shared with watchdog.py: only one supervisor restarts a service at a time (service_lock.py).
from service_lock import (REACTOR_SERVICE, restart_in_progress, restart_lock,  # noqa: E402
                          watchdog_running)


def _load_core_module(name: str):
    """lumenis_reactor_core/<name>.py, loaded by path (no reactor package import, no heavy deps)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        f"_{name}", REPO_ROOT / "lumenis_reactor_core" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


command_tiers = _load_core_module("command_tiers")
model_guard = _load_core_module("model_guard")
REACTOR_URL = os.environ.get("ONE2LV_REACTOR_URL", "http://127.0.0.1:8000")
CONFIG_PATH = REPO_ROOT / "autonomis-config.json"
LOG_DIR = REPO_ROOT / "logs"
PID_FILE = LOG_DIR / "autonomis.pid"
LOCK_FILE = LOG_DIR / "autonomis.lock"
STATE_FILE = LOG_DIR / "autonomis_state.json"
# The tunnel is started by start-tunnel.sh (the named "one2lvos" tunnel), which
# writes logs/cloudflared.pid. bridge_tunnel.sh never existed in this repo.
TUNNEL_SCRIPT = REPO_ROOT / "start-tunnel.sh"
TUNNEL_PID_FILE = LOG_DIR / "cloudflared.pid"
TUNNEL_LOG_FILE = LOG_DIR / "cloudflared.log"
TUNNEL_URL_FILE = LOG_DIR / "bridge_tunnel.url"
BRIDGE_PORT = 8095

_RUNNING = True

# Children this agent started, by pid. Kept so they can be reaped: without a
# wait() a child that exits stays a zombie, and a zombie still answers
# os.kill(pid, 0) - which made dead services look alive.
_CHILDREN: dict[int, subprocess.Popen] = {}


def clear_stale_bytecode() -> int:
    """Drop stale .pyc caches and return how many were removed.

    The repo lives on a network filesystem where mtime granularity makes
    Python's bytecode-cache invalidation unreliable: an edited file can keep
    running its old .pyc, so a fix appears to do nothing. Clearing the caches
    removes that whole class of confusion. The venv and node_modules are left
    alone.
    """
    removed = 0
    for cache in REPO_ROOT.glob("**/__pycache__"):
        parts = cache.parts
        if ".venv" in parts or "node_modules" in parts:
            continue
        for pyc in cache.glob("*.pyc"):
            try:
                pyc.unlink()
                removed += 1
            except OSError:
                pass
    return removed


# ── logging ──────────────────────────────────────────────────────────────────
def log(level: str, message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"{stamp} [{level:<7}] {message}"
    print(line, flush=True)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / "autonomis.log", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # pragma: no cover - config is shipped with the repo
        log("ERROR", f"cannot read {CONFIG_PATH}: {exc}")
        return {}


def load_env() -> None:
    """Load .env into os.environ without overriding what is already set."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        with open(env_path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


# ── MCP tool bridge ──────────────────────────────────────────────────────────
class MCPBridge:
    """Discovers and runs the repo's MCP-style tools.

    The tools in tools/ are classes with methods (ShellTool.run,
    MemoryTool.write_section, ...), not standalone scripts - so they are
    imported and their methods called, rather than executed as subprocesses.
    """

    def __init__(self, tools_dir: Path):
        self.tools_dir = tools_dir
        self.tools: dict[str, dict] = {}
        self.errors: dict[str, str] = {}

    def discover(self) -> dict[str, dict]:
        self.tools, self.errors = {}, {}
        if not self.tools_dir.is_dir():
            return self.tools
        for path in sorted(self.tools_dir.glob("*.py")):
            if path.stem.startswith("_"):
                continue
            name = path.stem.replace("_tool", "")
            self.tools[name] = {"name": name, "path": str(path), "module": None}
        return self.tools

    def _load(self, name: str):
        """Import a tool module and return (module, class) for it."""
        entry = self.tools.get(name)
        if not entry:
            raise KeyError(f"unknown tool: {name}")
        if entry.get("module") is not None:
            return entry["module"]
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            f"autonomis_tool_{name}", entry["path"]
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # The class is named after the file in CamelCase (shell_tool.py ->
        # ShellTool). Fall back to the first usable class defined in the module
        # - excluding Enums, which are not tools and raise on construction.
        cls = None
        camel = "".join(p.title() for p in name.split("_")) + "Tool"
        cls = getattr(module, camel, None)
        if cls is None:
            import enum

            candidates = [
                attr for attr in vars(module).values()
                if isinstance(attr, type)
                and attr.__module__ == module.__name__
                and not issubclass(attr, enum.Enum)
            ]
            stem = "".join(p.title() for p in name.split("_"))
            for wanted in (stem, stem + "Tool"):
                for cand in candidates:
                    if cand.__name__ == wanted:
                        cls = cand
                        break
                if cls is not None:
                    break
            if cls is None:
                for cand in candidates:
                    if cand.__name__.endswith("Tool"):
                        cls = cand
                        break
            if cls is None and candidates:
                cls = candidates[0]
        if cls is None:
            raise RuntimeError(f"no tool class found in {entry['path']}")

        instance = cls()
        entry["module"] = (module, instance)
        return entry["module"]

    def run(self, name: str, method: str, **kwargs) -> dict:
        """Call a tool method and normalise the result."""
        try:
            _, instance = self._load(name)
        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}

        fn = getattr(instance, method, None)
        if not callable(fn):
            methods = [m for m in dir(instance) if not m.startswith("_") and callable(getattr(instance, m))]
            return {"success": False, "error": f"no method '{method}'", "available": methods}
        try:
            result = fn(**kwargs)
        except Exception as exc:
            return {"success": False, "error": f"{type(exc).__name__}: {exc}"}
        return {"success": True, "result": result}

    def describe(self) -> list[dict]:
        out = []
        for name, entry in sorted(self.tools.items()):
            methods = []
            try:
                _, instance = self._load(name)
                methods = [
                    m for m in dir(instance)
                    if not m.startswith("_") and callable(getattr(instance, m, None))
                ]
            except Exception as exc:
                self.errors[name] = str(exc)
            out.append({"name": name, "path": entry["path"], "methods": methods})
        return out


# ── service registry ─────────────────────────────────────────────────────────
def service_registry() -> list[dict]:
    """The real services of this repo, with the commands that start them.

    Besides the start command, each entry says:
      match  - how to recognise an already-running copy of the service, so it
               can be stopped before a restart ("script": the file it runs, or
               "args" + "cwd" for module-style commands like uvicorn main:app);
      health - what a healthy answer looks like ("expect_status": "2xx" or
               "lt500", and optional "json" keys that must be present, with an
               exact value when one is given).
    """
    py = str(REPO_ROOT / ".venv" / "bin" / "python3")
    if not os.path.exists(py):
        py = "python3"
    bind = os.environ.get("ONE2LV_BIND_HOST", "127.0.0.1")
    # Health checks go to the bind address when it is a specific address;
    # for a wildcard bind (or the default) loopback answers.
    host = bind if bind not in ("", "0.0.0.0", "::", "[::]") else "127.0.0.1"
    services = [
        {
            "name": "lumenis-reactor",
            "port": 8000,
            "path": "/api/status",
            "cmd": [py, "-m", "uvicorn", "lumenis-main:app", "--host", bind, "--port", "8000"],
            "cwd": REPO_ROOT,
            "log": "reactor.log",
            "match": {"args": ["lumenis-main:app"], "cwd": REPO_ROOT},
            # /api/status returns {"reactor": ..., "nvidia": ..., ...}
            "health": {"expect_status": "2xx", "json": {"reactor": None}},
        },
        {
            "name": "ai-lobby",
            "port": 8006,
            "path": "/",
            "cmd": [py, str(REPO_ROOT / "ai_lobby.py")],
            "cwd": REPO_ROOT,
            "log": "lobby.log",
            "match": {"script": REPO_ROOT / "ai_lobby.py"},
            "health": {"expect_status": "lt500"},
        },
        {
            "name": "sovereign-core",
            "port": 8081,
            "path": "/",
            "cmd": [py, "-m", "uvicorn", "main:app", "--host", bind, "--port", "8081"],
            "cwd": REPO_ROOT / "sovereign-agentic-core",
            "log": "sovereign-core.log",
            "match": {"args": ["main:app"], "cwd": REPO_ROOT / "sovereign-agentic-core"},
            "health": {"expect_status": "lt500"},
        },
        {
            "name": "ai-arcade-mcp",
            "port": 8003,
            "path": "/",
            "cmd": [py, str(REPO_ROOT / "ai-arcade" / "server.py"), "--host", bind, "--port", "8003"],
            "cwd": REPO_ROOT,
            "log": "ai-arcade.log",
            "env": {"PYTHONPATH": str(REPO_ROOT / "ai-arcade")},
            "match": {"script": REPO_ROOT / "ai-arcade" / "server.py"},
            "health": {"expect_status": "lt500"},
        },
        {
            "name": "network-service",
            "port": 3003,
            "path": "/",
            "cmd": ["node", str(REPO_ROOT / "server" / "network-api.js")],
            "cwd": REPO_ROOT,
            "log": "network.log",
            "env": {"NETWORK_API_PORT": "3003"},
            "match": {"script": REPO_ROOT / "server" / "network-api.js"},
            "health": {"expect_status": "lt500"},
        },
        {
            "name": "public-bridge",
            "port": BRIDGE_PORT,
            "path": "/v1/health",
            "cmd": [py, str(REPO_ROOT / "public_bridge.py")],
            "cwd": REPO_ROOT,
            "log": "public_bridge.log",
            "match": {"script": REPO_ROOT / "public_bridge.py"},
            # /v1/health returns {"bridge": "ok", "reactor_up": ..., ...}
            "health": {"expect_status": "2xx", "json": {"bridge": "ok"}},
        },
        {
            "name": "aetherix",
            "port": 9003,
            "path": "/health",
            "cmd": [py, "server.py"],
            "cwd": REPO_ROOT / "Aetherix",
            "log": "aetherix.log",
            "match": {"script": REPO_ROOT / "Aetherix" / "server.py"},
            # /health returns {"status": "ok", "system": "Aetherix", ...}
            "health": {"expect_status": "2xx", "json": {"status": "ok"}},
        },
        {
            "name": "minimax",
            "port": 8080,
            "path": "/",
            "cmd": ["node", "index.js"],
            "cwd": REPO_ROOT / "minimax",
            "log": "minimax.log",
            "match": {"script": REPO_ROOT / "minimax" / "index.js"},
            "health": {"expect_status": "lt500"},
        },
        {
            "name": "webdav",
            "port": 8090,
            "path": "/",
            "cmd": [py, str(REPO_ROOT / "webdav_server.py")],
            "cwd": REPO_ROOT,
            "log": "webdav.log",
            "match": {"script": REPO_ROOT / "webdav_server.py"},
            "health": {"expect_status": "lt500"},
        },
    ]
    for svc in services:
        svc.setdefault("host", host)
    return services


# ── health checks ────────────────────────────────────────────────────────────
# A check returns {"state": ..., "detail": ...} where state is
#   "ok"   - answered the way the service's health spec expects;
#   "down" - nothing is listening on the port (connection refused);
#   "bad"  - something is listening but the answer is wrong: a 5xx, a timeout,
#            a body that is not the expected JSON. A "bad" service is restarted
#            only after several checks in a row, because restarting means
#            killing a process that is at least partly alive.
def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def evaluate_response(status: int, body: bytes, spec: dict) -> tuple[bool, str]:
    """Judge an HTTP answer against a health spec. Returns (ok, detail)."""
    expect = spec.get("expect_status", "lt500")
    if expect == "2xx" and not 200 <= status < 300:
        return False, f"HTTP {status}, expected 2xx"
    if expect == "lt500" and status >= 500:
        return False, f"HTTP {status} (server error)"
    wanted = spec.get("json")
    if wanted:
        try:
            data = json.loads(body.decode("utf-8", errors="replace"))
        except ValueError:
            return False, f"HTTP {status} but the body is not JSON"
        if not isinstance(data, dict):
            return False, f"HTTP {status} but the JSON is not an object"
        for key, value in wanted.items():
            if key not in data:
                return False, f"HTTP {status} but JSON has no '{key}'"
            if value is not None and data[key] != value:
                return False, f"HTTP {status} but '{key}' is {data[key]!r}, expected {value!r}"
    return True, f"HTTP {status}"


def check_service(svc: dict, timeout: float = 5) -> dict:
    host = svc.get("host", "127.0.0.1")
    url = f"http://{host}:{svc['port']}{svc['path']}"
    spec = svc.get("health") or {"expect_status": "lt500"}
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            status, body = resp.status, resp.read(65536)
    except urllib.error.HTTPError as exc:
        # A 4xx/5xx still has a status worth judging.
        status = exc.code
        try:
            body = exc.read(65536)
        except Exception:
            body = b""
    except Exception as exc:
        if not port_open(host, svc["port"]):
            return {"state": "down", "detail": f"nothing listening on {host}:{svc['port']}"}
        return {"state": "bad", "detail": f"listening but no valid answer: "
                                           f"{type(exc).__name__}: {exc}"}
    ok, detail = evaluate_response(status, body, spec)
    return {"state": "ok" if ok else "bad", "detail": detail}


def http_ok(port: int, path: str, timeout: int = 5) -> bool:
    """Kept for callers of the old helper: True when the port answers HTTP
    without a server error. The daemon itself uses check_service()."""
    svc = {"port": port, "path": path, "health": {"expect_status": "lt500"}}
    return check_service(svc, timeout)["state"] == "ok"


# ── process inspection (reads /proc; needs no extra tools) ───────────────────
def _proc_cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [p.decode(errors="replace") for p in raw.split(b"\0") if p]


def _proc_stat_fields(pid: int) -> list[str]:
    """Fields of /proc/<pid>/stat after the command name: [state, ppid, ...]."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return []
    return stat.rsplit(")", 1)[-1].split()


def _proc_cwd(pid: int) -> str | None:
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return None


def _iter_pids():
    try:
        entries = os.listdir("/proc")
    except OSError:
        return
    for entry in entries:
        if entry.isdigit():
            yield int(entry)


def reap_children() -> None:
    """Collect exit statuses of children that have finished (no zombies)."""
    for pid, proc in list(_CHILDREN.items()):
        if proc.poll() is not None:
            _CHILDREN.pop(pid, None)


def pid_alive(pid: int | None) -> bool:
    """True for a running process; False for a missing pid or a zombie."""
    if not pid or pid <= 0:
        return False
    reap_children()
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass  # exists, owned by another user
    fields = _proc_stat_fields(pid)
    if not fields:
        # No procfs entry: trust kill(0) only where there is no /proc at all.
        return not Path("/proc/self").exists()
    return fields[0] not in ("Z", "X")


def _protected_pids() -> set[int]:
    """This agent and its ancestors: never stopped, whatever matches."""
    protected = {os.getpid()}
    pid = os.getpid()
    for _ in range(64):
        fields = _proc_stat_fields(pid)
        if len(fields) < 2:
            break
        try:
            pid = int(fields[1])
        except ValueError:
            break
        if pid <= 1:
            break
        protected.add(pid)
    return protected


def _listening_inodes(port: int) -> set[str]:
    inodes: set[str] = set()
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = Path(table).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            parts = line.split()
            if len(parts) < 10 or parts[3] != "0A":  # 0A = LISTEN
                continue
            try:
                local_port = int(parts[1].rsplit(":", 1)[1], 16)
            except (IndexError, ValueError):
                continue
            if local_port == port and parts[9] != "0":
                inodes.add(parts[9])
    return inodes


def pids_listening_on(port: int) -> set[int]:
    """Pids of the processes that hold a listening socket on this TCP port."""
    inodes = _listening_inodes(port)
    if not inodes:
        return set()
    wanted = {f"socket:[{i}]" for i in inodes}
    found: set[int] = set()
    for pid in _iter_pids():
        try:
            fds = os.listdir(f"/proc/{pid}/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(f"/proc/{pid}/fd/{fd}") in wanted:
                    found.add(pid)
                    break
            except OSError:
                continue
    return found


def process_matches(pid: int, svc: dict) -> bool:
    """Does this process run the service's command (see service_registry)?"""
    match = svc.get("match") or {}
    args = _proc_cmdline(pid)
    if not args:
        return False
    cwd = _proc_cwd(pid)
    script = match.get("script")
    if script:
        target = os.path.realpath(str(script))
        for arg in args[1:]:
            if arg.startswith("-"):
                continue
            path = arg if os.path.isabs(arg) else os.path.join(cwd or "/", arg)
            if os.path.realpath(path) == target:
                return True
        return False
    tokens = match.get("args") or []
    if tokens and all(t in args for t in tokens):
        want_cwd = match.get("cwd")
        if want_cwd is None:
            return True
        return cwd is not None and os.path.realpath(cwd) == os.path.realpath(str(want_cwd))
    return False


def service_pids(svc: dict, tracked: int | None = None) -> set[int]:
    """Every live copy of a service: the pid we started, whatever holds its
    port, and any process running its command."""
    pids: set[int] = set()
    if tracked and pid_alive(tracked):
        pids.add(tracked)
    if svc.get("port"):
        pids |= pids_listening_on(svc["port"])
    if svc.get("match"):
        for pid in _iter_pids():
            if process_matches(pid, svc):
                pids.add(pid)
    return {p for p in pids if pid_alive(p)} - _protected_pids()


def _send_signal(pid: int, sig: int) -> None:
    """Signal a process; a group leader gets the whole group, so workers and
    helpers it started (uvicorn workers, Xvfb, ...) go with it."""
    try:
        pgid = os.getpgid(pid)
        if pgid == pid and pgid != os.getpgid(0):
            os.killpg(pgid, sig)
        else:
            os.kill(pid, sig)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        log("WARN", f"no permission to signal pid {pid}: {exc}")


def stop_processes(pids, name: str, timeout: float = 10.0) -> list[int]:
    """SIGTERM, wait up to `timeout`, then SIGKILL what is left.
    Returns the pids that were signalled."""
    protected = _protected_pids()
    targets = sorted(p for p in set(pids) if p not in protected and pid_alive(p))
    if not targets:
        return []
    log("INFO", f"{name}: stopping old process(es) {targets} before restart")
    for pid in targets:
        _send_signal(pid, signal.SIGTERM)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(pid_alive(p) for p in targets):
            break
        time.sleep(0.25)
    left = [p for p in targets if pid_alive(p)]
    if left:
        log("WARN", f"{name}: {left} ignored SIGTERM for {timeout:.0f}s - SIGKILL")
        for pid in left:
            _send_signal(pid, signal.SIGKILL)
        deadline = time.time() + 5
        while time.time() < deadline and any(pid_alive(p) for p in left):
            time.sleep(0.25)
        still = [p for p in left if pid_alive(p)]
        if still:
            log("ERROR", f"{name}: could not stop {still}")
    return targets


def wait_port_free(port: int, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _listening_inodes(port):
            return True
        time.sleep(0.25)
    return not _listening_inodes(port)


# ── ARIA (desktop app, no port) ──────────────────────────────────────────────
def aria_pids() -> set[int]:
    """ARIA is a desktop app with no health endpoint - match main.py by cwd."""
    aria_dir = os.path.realpath(str(REPO_ROOT / "aria"))
    found: set[int] = set()
    for pid in _iter_pids():
        args = _proc_cmdline(pid)
        if not any(re.search(r"(^|/)main\.py$", a) for a in args):
            continue
        cwd = _proc_cwd(pid)
        if cwd and os.path.realpath(cwd) == aria_dir and pid_alive(pid):
            found.add(pid)
    return found - _protected_pids()


def aria_running() -> bool:
    return bool(aria_pids())


# ── bridge tunnel ────────────────────────────────────────────────────────────
def _is_cloudflared(pid: int) -> bool:
    args = _proc_cmdline(pid)
    if args and os.path.basename(args[0]).startswith("cloudflared"):
        return True
    try:
        return os.path.basename(os.readlink(f"/proc/{pid}/exe")).startswith("cloudflared")
    except OSError:
        return False


def _read_tunnel_pid() -> int | None:
    try:
        return int(TUNNEL_PID_FILE.read_text().strip())
    except (OSError, ValueError):
        return None


def tunnel_pids() -> set[int]:
    """cloudflared processes running a named tunnel ("cloudflared tunnel ... run"), the
    kind start-tunnel.sh starts. Quick tunnels (--url ...) are someone else's and never match."""
    found: set[int] = set()
    for pid in _iter_pids():
        if not _is_cloudflared(pid):
            continue
        args = _proc_cmdline(pid)
        if "tunnel" in args and "run" in args and "--url" not in args and pid_alive(pid):
            found.add(pid)
    return found


def tunnel_log_diagnosis() -> str | None:
    """Explain a tunnel that will not stay up, from the end of cloudflared.log."""
    try:
        tail = TUNNEL_LOG_FILE.read_text(errors="replace")[-4000:]
    except OSError:
        return None
    if "edge discovery" in tail and ("DNS query failed" in tail or "lookup" in tail):
        return ("this machine cannot resolve Cloudflare's tunnel servers "
                "(_v2-origintunneld._tcp.argotunnel.com); a network/DNS block, "
                "not a script problem")
    if "Unauthorized" in tail or "invalid token" in tail.lower():
        return "Cloudflare rejected CLOUDFLARE_TUNNEL_TOKEN"
    return None


def _metrics_addr(pid: int) -> str | None:
    args = _proc_cmdline(pid)
    for i, arg in enumerate(args):
        if arg == "--metrics" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--metrics="):
            return arg.split("=", 1)[1]
    return None


def tunnel_health(check_public: bool = True, timeout: float = 10,
                  bridge_ok: bool = True) -> dict:
    """Is the Cloudflare tunnel (start-tunnel.sh) really up?

    The pid file alone is not trusted: the pid must be alive, not a zombie,
    and actually be cloudflared (a reused pid is caught). A cloudflared running
    a named tunnel is found even when the pid file is stale or missing.
    When cloudflared runs with --metrics, its /ready endpoint must say it has
    an edge connection. When the local bridge is healthy, the published URL
    must answer /v1/health too.
    """
    result: dict = {"healthy": False, "state": "down", "pid": None,
                    "pids": [], "pid_file": None, "detail": ""}
    file_pid = _read_tunnel_pid()
    result["pid_file"] = file_pid
    file_ok = bool(file_pid) and pid_alive(file_pid) and _is_cloudflared(file_pid)
    procs = tunnel_pids()
    live = set(procs)
    if file_ok:
        live.add(file_pid)
    result["pids"] = sorted(live)
    if not live:
        if file_pid is None:
            result["detail"] = "no pid file and no cloudflared tunnel running"
        else:
            result["detail"] = (f"pid file says {file_pid}, which is not a running "
                                f"cloudflared (stale pid)")
        why = tunnel_log_diagnosis()
        if why:
            result["detail"] += f"; {why}"
        return result
    pid = file_pid if file_ok else min(live)
    result["pid"] = pid
    notes = []
    if not file_ok:
        notes.append(f"pid file stale ({file_pid}); found cloudflared {pid}")
    if len(live) > 1:
        notes.append(f"{len(live)} tunnel processes: {sorted(live)}")

    addr = _metrics_addr(pid)
    if addr:
        try:
            with urllib.request.urlopen(f"http://{addr}/ready", timeout=5) as resp:
                ready = resp.status == 200
        except Exception:
            ready = False
        if not ready:
            result.update(state="bad", detail="; ".join(
                notes + [f"cloudflared {pid} reports no edge connection ({addr}/ready)"]))
            return result

    url = None
    try:
        url = TUNNEL_URL_FILE.read_text().strip() or None
    except OSError:
        pass
    result["public_url"] = url
    if check_public and url and bridge_ok:
        public = check_service_url(url.rstrip("/") + "/v1/health",
                                   {"expect_status": "2xx", "json": {"bridge": "ok"}},
                                   timeout)
        result["public"] = public
        if not public["ok"]:
            result.update(state="bad", detail="; ".join(
                notes + [f"published URL does not answer: {public['detail']}"]))
            return result
    result.update(healthy=True, state="ok",
                  detail="; ".join(notes) or f"cloudflared {pid} running")
    return result


def check_service_url(url: str, spec: dict, timeout: float) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Autonomis"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, body = resp.status, resp.read(65536)
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            body = exc.read(65536)
        except Exception:
            body = b""
    except Exception as exc:
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
    ok, detail = evaluate_response(status, body, spec)
    return {"ok": ok, "detail": detail}


def tunnel_running() -> bool:
    """Kept for callers of the old helper: a live cloudflared for the bridge
    (no public-URL check)."""
    return tunnel_health(check_public=False)["healthy"]


# ── process control ──────────────────────────────────────────────────────────
def spawn(service: dict) -> int:
    log_path = LOG_DIR / service["log"]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(service.get("env", {}))
    with open(log_path, "a", encoding="utf-8") as out:
        proc = subprocess.Popen(
            service["cmd"], cwd=str(service["cwd"]), env=env,
            stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    _CHILDREN[proc.pid] = proc
    return proc.pid


def tail(path: Path, lines: int = 12) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(content[-lines:])
    except OSError:
        return "(no log)"


# ── runtime / installation ───────────────────────────────────────────────────
def apt_available() -> bool:
    return shutil.which("apt-get") is not None


def ensure_runtime(config: dict) -> list[str]:
    """Repair the runtime. Returns a list of actions taken."""
    actions: list[str] = []
    inst = config.get("installation", {})
    if not inst.get("auto_install_dependencies", True):
        return actions

    # 1. apt packages (xvfb/libmtdev1 are needed for ARIA and are lost on a
    #    container rebuild, along with the apt package lists).
    packages = inst.get("apt_packages") or []
    missing = []
    for pkg in packages:
        if shutil.which(pkg) or (pkg == "xvfb" and shutil.which("Xvfb")):
            continue
        if pkg == "libmtdev1":
            # A library, not a binary: check the shared object.
            if subprocess.run(["ldconfig", "-p"], capture_output=True, text=True
                              ).stdout.count("libmtdev.so") > 0:
                continue
        missing.append(pkg)
    if missing and apt_available():
        if inst.get("apt_update_before_install", True):
            subprocess.run(["apt-get", "update", "-qq"], capture_output=True, timeout=300)
        cmd = ["apt-get", "install", "-y", "-qq", *missing]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if res.returncode == 0:
            actions.append(f"apt-get install {' '.join(missing)}")
            log("INFO", f"installed apt packages: {', '.join(missing)}")
        else:
            log("WARN", f"apt-get install {missing} failed: {res.stderr.strip()[:200]}")

    # 2. Python dependencies, into the project venv.
    venv_py = REPO_ROOT / ".venv" / "bin" / "python3"
    if inst.get("pip_install", True) and venv_py.exists():
        req = REPO_ROOT / "requirements.txt"
        if req.exists():
            check = subprocess.run(
                [str(venv_py), "-c",
                 "import fastapi,uvicorn,anthropic,sse_starlette,chess,websockets"],
                capture_output=True, timeout=120,
            )
            if check.returncode != 0:
                log("INFO", "python dependencies incomplete - installing")
                res = subprocess.run(
                    [str(venv_py), "-m", "pip", "install", "-q",
                     "--index-url", "https://pypi.org/simple/", "-r", str(req)],
                    capture_output=True, text=True, timeout=900,
                )
                if res.returncode == 0:
                    actions.append("pip install -r requirements.txt")
                    log("INFO", "installed python requirements")
                else:
                    log("WARN", f"pip install failed: {res.stderr.strip()[:200]}")

    # 3. Node dependencies.
    if inst.get("npm_install", True) and shutil.which("npm"):
        for rel in (".", "minimax"):
            folder = REPO_ROOT / rel
            if not (folder / "package.json").exists():
                continue
            if not (folder / "node_modules").exists():
                log("INFO", f"node modules missing in {rel} - npm install")
                res = subprocess.run(
                    ["npm", "install", "--no-audit", "--no-fund"],
                    cwd=str(folder), capture_output=True, text=True, timeout=900,
                )
                if res.returncode == 0:
                    actions.append(f"npm install ({rel})")
                    log("INFO", f"installed node modules in {rel}")
                else:
                    log("WARN", f"npm install failed in {rel}: {res.stderr.strip()[:200]}")

    # 4. cloudflared, kept in the workspace so it survives a container rebuild.
    if not (shutil.which("cloudflared") or (REPO_ROOT / "bin" / "cloudflared").exists()):
        log("WARN", "cloudflared is missing - the public bridge cannot be published")

    return actions


# ── LLM consultation ─────────────────────────────────────────────────────────
class AIConsultant:
    """Asks an LLM what to do when a service keeps failing.

    Degrades cleanly: if the provider is unreachable or out of credits the
    agent logs it once and carries on with the deterministic behaviour.
    """

    def __init__(self, config: dict):
        self.cfg = config.get("ai_consultation", {})
        self.enabled = bool(self.cfg.get("enabled", True))
        self.base_url = self.cfg.get("base_url", "https://integrate.api.nvidia.com/v1").rstrip("/")
        self.model = self.cfg.get("model", "nvidia/nemotron-3.5-lightning-30b-a3b")
        self.fallback_models = list(self.cfg.get("fallback_models", []))
        self.timeout = int(self.cfg.get("timeout_seconds", 90))
        self.max_tokens = int(self.cfg.get("max_tokens", 1024))
        self.disable_thinking = bool(self.cfg.get("disable_thinking", True))
        self.allowlist = self.cfg.get("command_allowlist", [])
        self.denylist = list(self.cfg.get("command_denylist", []))
        self.last_call = 0.0
        self.unavailable_reason: str | None = None

    def _api_key(self) -> str:
        var = self.cfg.get("api_key_env", "NVIDIA_API_KEY")
        return os.environ.get(var, "")

    def _complete(self, model: str, question: str) -> dict:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content":
                    "You are a Linux operations assistant for a One2lvOS deployment. "
                    "Answer with one single shell command and nothing else - no prose, "
                    "no markdown fences, no explanation. The command must repair the "
                    "problem described. "
                    "Rules: never delete, remove, move or overwrite files or data, and "
                    "never run a destructive command (rm, rmdir, mv, dd, mkfs, shred). "
                    "Prefer restarting the service, installing a missing dependency, or "
                    "creating a missing directory."},
                {"role": "user", "content": question},
            ],
            "max_tokens": self.max_tokens,
        }
        # Nemotron reasoning models spend the token budget on a thinking trace
        # and can return content=null. Turning thinking off gives a clean
        # answer; the reasoning_content fallback covers models that ignore it.
        if self.disable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self._api_key()}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode())
        message = (data.get("choices") or [{}])[0].get("message") or {}
        text = message.get("content")
        if text is None:
            text = message.get("reasoning_content") or ""
        return {"ok": True, "text": text or "", "model": model}

    def ask(self, question: str) -> dict:
        if not self.enabled:
            return {"ok": False, "error": "AI consultation disabled"}
        if not self._api_key():
            return {"ok": False,
                    "error": f"no API key in {self.cfg.get('api_key_env')}"}

        # Try the configured model, then the fallbacks - a model that has been
        # retired must not take the whole consultation path down with it.
        last_error = None
        for model in [self.model, *self.fallback_models]:
            try:
                answer = self._complete(model, question)
                self.unavailable_reason = None
                return answer
            except urllib.error.HTTPError as exc:
                body = exc.read().decode(errors="replace")[:200]
                last_error = f"HTTP {exc.code} for {model}: {body}"
            except Exception as exc:
                last_error = f"{type(exc).__name__} for {model}: {exc}"
        self.unavailable_reason = last_error
        return {"ok": False, "error": last_error}

    def propose_command(self, question: str) -> dict:
        """Ask for a command and validate it against the allowlist."""
        answer = self.ask(question)
        if not answer.get("ok"):
            return answer
        text = answer.get("text") or ""
        # Strip markdown fences the model may still add.
        text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
        if not text:
            return {"ok": False, "error": "empty reply"}
        # Only the first line is considered.
        command = text.splitlines()[0].strip()
        if not self.allowlist:
            return {"ok": True, "command": command, "allowed": False,
                    "error": "no allowlist configured"}

        # Second layer: a destructive command is refused even when it happens
        # to start with an allowed prefix.
        for denied in self.denylist:
            if denied in command:
                return {"ok": True, "command": command, "allowed": False,
                        "error": f"command contains a denied operation: {denied}"}

        # Validate each segment of a compound command separately, so a
        # legitimate "cd somewhere && npm install" is judged on its parts
        # rather than rejected because the first word is "cd".
        segments = [s.strip() for s in re.split(r"&&|\|\||;|\|", command) if s.strip()]
        for segment in segments:
            if not any(segment.startswith(prefix) for prefix in self.allowlist):
                return {"ok": True, "command": command, "allowed": False,
                        "error": f"segment not on the allowlist: {segment!r}"}
        return {"ok": True, "command": command, "allowed": True, "raw": text,
                "segments": segments}


def engine_call(tool: str, args: dict, timeout: float = 150.0) -> dict:
    """POST one tool call to the reactor's tool engine as caller 'autonomis' (L2+ is held for One2lv)."""
    url = f"{REACTOR_URL}/engine/call/{tool}?as_caller=autonomis"
    req = urllib.request.Request(url, data=json.dumps(args).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode() or "{}")
        except Exception:
            return {"ok": False, "status": exc.code, "error": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"ok": False, "status": 0, "error": f"reactor unreachable: {type(exc).__name__}: {exc}"}


def nimlab_call(tool: str, args: dict | None = None, timeout: float = 150.0) -> dict:
    """Run one nimlab.<tool> (the NVIDIA lab suite inside the reactor) as caller 'autonomis'.

    The reactor's tool engine applies the L0-L3 tiers (L0-L1 run, L2-L3 are held for One2lv) and
    nimlab_tools' own gate (NVIDIA hosts only, call budget, rate limit, no safety models). Autonomis
    adds two checks before the call: no safety/guard/classifier model named in the arguments, and no
    call while another supervisor holds the reactor's restart lock (service_lock.py)."""
    args = dict(args or {})
    named = [args.get("model"), args.get("judge"), *(args.get("models") or [])]
    bad = next((m for m in named if isinstance(m, str) and model_guard.is_safety_model(m)), None)
    if bad:
        return {"ok": False, "refused": True,
                "error": f"{bad} is a safety/guard model; the reactor never uses one"}
    if restart_in_progress(REACTOR_SERVICE, holder="autonomis"):
        return {"ok": False, "skipped": True,
                "error": "the reactor is being restarted (shared restart lock); nimlab not called"}
    return engine_call(f"nimlab.{tool}", args, timeout=timeout)


def run_allowed_command(command: str, bridge: MCPBridge | None, allowlist: list[str],
                        denylist: list[str] | None = None) -> dict:
    """Run an AI-proposed command through the reactor's L0-L3 approval levels.

    The command must match the allowlist and no denylist entry. Its tier comes from command_tiers.classify();
    the reactor's tool engine runs L0-L1 and holds L2-L3 for One2lv's approval (L3 needs a second
    confirmation). When the reactor is down, nothing above L0 runs; L0 (read-only) runs locally."""
    command = (command or "").strip()
    if not any(command.startswith(prefix) for prefix in allowlist):
        return {"success": False, "error": "command not on the allowlist"}
    if any(bad in command for bad in (denylist or [])):
        return {"success": False, "error": "command matches the denylist"}
    tier, why = command_tiers.classify(command)
    out = engine_call(f"local.supervisor_cmd_l{tier}", {"command": command})
    if out.get("held_for_approval"):
        log("WARN", f"L{tier} command held for One2lv's approval ({out.get('approval_id')}): {command} - {why}")
        return {"success": False, "held": True, "tier": f"L{tier}", "approval_id": out.get("approval_id"),
                "error": out.get("error")}
    if out.get("status") == 0:  # reactor unreachable
        if tier == 0:
            res = command_tiers.run_argv(command, timeout=120)
            return {"success": res.get("ok", False), "tier": "L0", "local": True, **res}
        return {"success": False, "tier": f"L{tier}", "error": out.get("error") + " - not run above L0"}
    result = out.get("result") if isinstance(out.get("result"), dict) else {}
    return {"success": bool(out.get("ok")) and bool(result.get("ok", True)), "tier": f"L{tier}",
            "result": result, "error": out.get("error")}


# ── notifications ────────────────────────────────────────────────────────────
def notify_discord(message: str, config: dict) -> bool:
    notif = config.get("notifications", {})
    if not notif.get("discord_enabled", True):
        return False
    url = os.environ.get(notif.get("discord_webhook_env", "DISCORD_WEBHOOK_URL"), "")
    if not url:
        return False
    payload = json.dumps({"content": message[:1900]}).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        log("WARN", f"discord notification failed: {type(exc).__name__}: {exc}")
        return False


# ── restart policy ───────────────────────────────────────────────────────────
class RestartPolicy:
    """Per-service restart limits, backoff and startup grace.

    Config (all optional; defaults in brackets):
      monitoring.max_restart_attempts      restarts per round [5]
      services.restart_backoff_seconds     first backoff, doubled per attempt [5]
      services.max_backoff_seconds         backoff cap [300]
      services.give_up_seconds             pause after a full round fails [1800]
      services.startup_grace_seconds       time a fresh start gets to come up [40]
      services.stable_after_seconds        healthy this long resets the count [300]
      services.failed_checks_before_restart  "bad" (listening but wrong answer)
                                           checks in a row before a restart [2];
                                           "down" restarts on the first check
    """

    def __init__(self, config: dict):
        mon = config.get("monitoring", {})
        svc = config.get("services", {})
        self.max_attempts = max(1, int(mon.get("max_restart_attempts", 5)))
        self.base_backoff = max(0.0, float(svc.get("restart_backoff_seconds", 5)))
        self.max_backoff = max(self.base_backoff, float(svc.get("max_backoff_seconds", 300)))
        self.give_up_seconds = max(0, int(svc.get("give_up_seconds", 1800)))
        self.grace = max(0.0, float(svc.get("startup_grace_seconds", 40)))
        self.stable_after = max(0.0, float(svc.get("stable_after_seconds", 300)))
        self.bad_threshold = max(1, int(svc.get("failed_checks_before_restart", 2)))
        self.state: dict[str, dict] = {}

    def _get(self, name: str) -> dict:
        return self.state.setdefault(name, {
            "attempts": 0, "next_at": 0.0, "last_start": 0.0, "start_ok": False,
            "suspended_until": 0.0, "notified": False, "pid": None,
            "bad_checks": 0, "healthy_since": None,
        })

    def attempts(self, name: str) -> int:
        return self._get(name)["attempts"]

    def pid(self, name: str) -> int | None:
        return self._get(name)["pid"]

    def healthy(self, name: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        st = self._get(name)
        st["bad_checks"] = 0
        if st["healthy_since"] is None:
            st["healthy_since"] = now
        if st["attempts"] and now - st["healthy_since"] >= self.stable_after:
            log("INFO", f"{name}: healthy for {int(now - st['healthy_since'])}s - "
                        f"restart counter reset")
            st.update(attempts=0, next_at=0.0, suspended_until=0.0, notified=False)

    def allow(self, name: str, state: str, bad_threshold: int | None = None,
              now: float | None = None) -> tuple[bool, str, bool]:
        """May this failing service be restarted now?
        Returns (allowed, reason, gave_up_just_now)."""
        now = time.time() if now is None else now
        st = self._get(name)
        st["healthy_since"] = None
        st["bad_checks"] += 1
        if state == "bad":
            need = max(1, bad_threshold or self.bad_threshold)
            if st["bad_checks"] < need:
                return (False, f"answering wrongly; restart after {need} failed checks "
                               f"in a row ({st['bad_checks']}/{need})", False)

        # A fresh start gets time to come up - unless its process already died.
        if st["last_start"] and st["start_ok"] and now - st["last_start"] < self.grace:
            if st["pid"] is None or pid_alive(st["pid"]):
                return (False, f"starting (started {int(now - st['last_start'])}s ago, "
                               f"grace {int(self.grace)}s)", False)

        if st["attempts"] >= self.max_attempts:
            if now < st["suspended_until"]:
                newly = not st["notified"]
                st["notified"] = True
                return (False, f"restart limit reached ({self.max_attempts} attempts); "
                               f"next try in {int(st['suspended_until'] - now)}s", newly)
            log("INFO", f"{name}: cool-off over - allowing a new round of restarts")
            st.update(attempts=0, next_at=0.0, notified=False)

        if now < st["next_at"]:
            return False, f"backoff: next restart in {int(st['next_at'] - now) + 1}s", False
        return True, "", False

    def record_restart(self, name: str, pid: int | None, started: bool,
                       now: float | None = None) -> None:
        now = time.time() if now is None else now
        st = self._get(name)
        st["attempts"] += 1
        st.update(last_start=now, pid=pid, start_ok=started, bad_checks=0)
        delay = min(self.base_backoff * (2 ** (st["attempts"] - 1)), self.max_backoff)
        st["next_at"] = now + delay
        if st["attempts"] >= self.max_attempts:
            st["suspended_until"] = now + self.give_up_seconds

    def save(self) -> None:
        def iso(t):
            return (datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")
                    if t else None)
        out = {}
        for name, st in self.state.items():
            out[name] = {"attempts": st["attempts"], "max_attempts": self.max_attempts,
                         "pid": st["pid"], "last_start": iso(st["last_start"]),
                         "next_restart_not_before": iso(st["next_at"]),
                         "paused_until": iso(st["suspended_until"])
                         if st["attempts"] >= self.max_attempts else None}
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            tmp = STATE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(out, indent=2))
            tmp.replace(STATE_FILE)
        except OSError:
            pass

    @staticmethod
    def load_saved() -> dict:
        try:
            return json.loads(STATE_FILE.read_text())
        except (OSError, ValueError):
            return {}


# ── the main loop ────────────────────────────────────────────────────────────
class Autonomis:
    def __init__(self):
        load_env()
        self.config = load_config()
        self.bridge = MCPBridge(REPO_ROOT / self.config.get("mcp_integration", {})
                                .get("tools_directory", "tools"))
        self.ai = AIConsultant(self.config)
        self.services = service_registry()
        self.failures: dict[str, int] = {}
        self.actions_taken = 0
        self.policy = RestartPolicy(self.config)
        self._installs_done = False

    # -- one cycle -------------------------------------------------------
    def cycle(self) -> dict:
        report = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "actions": [], "restarts": [], "unhealthy": [], "skipped": []}
        reap_children()

        mon = self.config.get("monitoring", {})
        # Installs run once, in the first cycle after start (installation.check_on_startup), never again.
        inst = self.config.get("installation", {})
        if (not self._installs_done and mon.get("enabled", True) and inst.get("check_on_startup", True)
                and not self.config.get("_skip_installs")):
            report["actions"] = ensure_runtime(self.config)
        self._installs_done = True

        svc_cfg = self.config.get("services", {})
        timeout = float(svc_cfg.get("health_check_timeout", 5))
        auto_restart = bool(svc_cfg.get("auto_restart", True))
        bridge_ok = True

        watchdog_alive = watchdog_running()
        for svc in self.services:
            name = svc["name"]
            if name == REACTOR_SERVICE and watchdog_alive:
                # watchdog.py owns the reactor; Autonomis only looks.
                report.setdefault("owned_by_watchdog", []).append(name)
                continue
            health = check_service(svc, timeout)
            if name == "public-bridge":
                bridge_ok = health["state"] == "ok"
            if health["state"] == "ok":
                self.failures.pop(name, None)
                self.policy.healthy(name)
                continue
            report["unhealthy"].append(name)
            count = self.failures.get(name, 0) + 1
            self.failures[name] = count
            self._maybe_restart(
                name, health, report, auto_restart,
                start=lambda s=svc: self._restart_service(s),
                what=f"{name} on :{svc['port']}")

        # ARIA - Kivy desktop app, checked by process. Off unless aria.monitor is true: it needs a display
        # (Xvfb on this machine) and start-aria.sh never existed, so every restart used to fail.
        aria_cfg = self.config.get("aria", {})
        if not aria_cfg.get("monitor", False):
            pass
        elif aria_running():
            self.policy.healthy("aria")
        else:
            report["unhealthy"].append("aria")
            self._maybe_restart(
                "aria", {"state": "down", "detail": "no aria/main.py process"},
                report, auto_restart, start=self._restart_aria, what="aria")

        # Public tunnel.
        tun_cfg = self.config.get("tunnel", {})
        tunnel = tunnel_health(check_public=bool(tun_cfg.get("public_check", True)),
                               timeout=float(tun_cfg.get("public_check_timeout", 10)),
                               bridge_ok=bridge_ok)
        report["tunnel"] = {k: tunnel.get(k) for k in ("state", "pid", "pids", "detail")}
        if tunnel["healthy"]:
            self._tidy_tunnel(tunnel)
            self.policy.healthy("bridge-tunnel")
        else:
            report["unhealthy"].append("bridge-tunnel")
            self._maybe_restart(
                "bridge-tunnel", tunnel, report, auto_restart,
                start=lambda t=tunnel: self._restart_tunnel(t),
                what="public bridge tunnel",
                bad_threshold=int(tun_cfg.get("failed_checks_before_restart", 3)))

        # nimlab: read-only status (L0, no NVIDIA request) through the reactor's tool engine.
        if self.config.get("nimlab", {}).get("monitor"):
            out = nimlab_call("status", timeout=timeout * 4)
            res = out.get("result") if isinstance(out.get("result"), dict) else {}
            report["nimlab"] = {"ok": bool(out.get("ok")), "suite": res.get("suite"),
                                "key_present": (res.get("key") or {}).get("present"),
                                "error": out.get("error")}
            # A down reactor is already reported above; flag nimlab only when the reactor answered.
            if not out.get("ok") and not out.get("skipped") and out.get("status") != 0:
                report["unhealthy"].append("nimlab")

        # Ask the LLM about anything that keeps failing.
        report["ai"] = self.consult(report["unhealthy"])
        self.policy.save()
        return report

    # -- restart handling ------------------------------------------------
    def _maybe_restart(self, name: str, health: dict, report: dict,
                       auto_restart: bool, start, what: str,
                       bad_threshold: int | None = None) -> None:
        """Restart a failing service if the restart policy allows it now."""
        state, detail = health.get("state", "down"), health.get("detail", "")
        allowed, why, gave_up = self.policy.allow(name, state, bad_threshold)
        if gave_up:
            log("ERROR", f"{name}: still {state} after {self.policy.max_attempts} restarts - "
                         f"no more restarts for {self.policy.give_up_seconds}s "
                         f"unless it recovers on its own")
            notify_discord(
                f"Autonomis: {name} was restarted {self.policy.max_attempts} times and is "
                f"still {state} ({detail}). Restarts paused for "
                f"{self.policy.give_up_seconds // 60} min.\n"
                f"```{tail(LOG_DIR / self._log_name(name), 8)[-1200:]}```",
                self.config)
        if not allowed:
            report["skipped"].append({"service": name, "reason": why})
            log("INFO" if why.startswith("starting") else "WARN",
                f"{what} is {state} ({detail}) - not restarting: {why}")
            return
        if not auto_restart:
            report["skipped"].append({"service": name, "reason": "auto_restart is off"})
            log("WARN", f"{what} is {state} ({detail}) - auto_restart is off")
            return
        attempt = self.policy.attempts(name) + 1
        log("WARN", f"{what} is {state} ({detail}) - restarting "
                    f"(attempt {attempt}/{self.policy.max_attempts})")
        pid, started = None, False
        with restart_lock(name, holder="autonomis") as got:
            if not got:
                report["skipped"].append({"service": name, "reason": "another supervisor holds the restart lock"})
                log("INFO", f"{what}: another supervisor is restarting it - skipped")
                return
            try:
                pid = start()
                started = True
                self.actions_taken += 1
                report["restarts"].append({"service": name, "pid": pid})
            except Exception as exc:
                log("ERROR", f"{name} failed to start: {type(exc).__name__}: {exc}")
        # A failed start counts as an attempt too, so it backs off as well.
        self.policy.record_restart(name, pid, started)

    def _log_name(self, name: str) -> str:
        svc = next((s for s in self.services if s["name"] == name), None)
        if svc:
            return svc["log"]
        return {"bridge-tunnel": "cloudflared.log", "aria": "aria.log"}.get(name, "autonomis.log")

    def _stop_timeout(self) -> float:
        return float(self.config.get("services", {}).get("stop_timeout_seconds", 10))

    def _restart_service(self, svc: dict) -> int:
        """Stop every old copy of the service, wait for its port, then start."""
        old = service_pids(svc, self.policy.pid(svc["name"]))
        stop_processes(old, svc["name"], self._stop_timeout())
        if svc.get("port") and not wait_port_free(svc["port"], 5):
            holders = pids_listening_on(svc["port"])
            raise RuntimeError(
                f"port {svc['port']} is still in use"
                + (f" by {sorted(holders)}" if holders else
                   " by a process this user cannot see")
                + " - not starting a second copy")
        return spawn(svc)

    def _restart_aria(self) -> int | None:
        """Start aria/main.py the way startos.sh does (start-aria.sh does not exist)."""
        stop_processes(aria_pids(), "aria", self._stop_timeout())
        main = REPO_ROOT / "aria" / "main.py"
        if not main.exists():
            raise RuntimeError("aria/main.py not found")
        py = str(REPO_ROOT / ".venv" / "bin" / "python3") if (REPO_ROOT / ".venv" / "bin" / "python3").exists() \
            else (shutil.which("python3") or "python3")
        cmd = [py, "main.py"]
        if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
            cmd = ["xvfb-run", "-a", *cmd]
        return spawn({"name": "aria", "cmd": cmd, "cwd": REPO_ROOT / "aria", "log": "aria.log"})

    def _tunnel_pids_to_stop(self, tunnel: dict) -> set[int]:
        pids = set(tunnel_pids())
        file_pid = _read_tunnel_pid()
        # The pid file is only trusted when it really is cloudflared - a
        # stale number may belong to an unrelated process by now.
        if file_pid and pid_alive(file_pid) and _is_cloudflared(file_pid):
            pids.add(file_pid)
        return pids - _protected_pids()

    def _restart_tunnel(self, tunnel: dict) -> int | None:
        stop_processes(self._tunnel_pids_to_stop(tunnel), "bridge-tunnel",
                       self._stop_timeout())
        if not TUNNEL_SCRIPT.exists():
            raise RuntimeError(f"{TUNNEL_SCRIPT.name} is missing")
        res = subprocess.run(["bash", str(TUNNEL_SCRIPT)],
                             capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            raise RuntimeError(f"{TUNNEL_SCRIPT.name} exited {res.returncode}: "
                               f"{(res.stderr or res.stdout).strip()[-200:]}")
        after = tunnel_health(check_public=False)
        if not after["healthy"]:
            log("WARN", f"{TUNNEL_SCRIPT.name} ran but no live tunnel: {after['detail']}")
        return after.get("pid")

    def _tidy_tunnel(self, tunnel: dict) -> None:
        """Tunnel is up: fix a stale pid file and stop extra copies."""
        pid = tunnel.get("pid")
        if not pid:
            return
        if tunnel.get("pid_file") != pid:
            try:
                TUNNEL_PID_FILE.write_text(str(pid))
                log("INFO", f"bridge tunnel pid file was stale "
                            f"({tunnel.get('pid_file')}) - now {pid}")
            except OSError as exc:
                log("WARN", f"cannot update {TUNNEL_PID_FILE}: {exc}")
        extras = [p for p in tunnel.get("pids", []) if p != pid]
        if extras:
            stop_processes(extras, "bridge-tunnel (duplicates)", self._stop_timeout())

    def consult(self, unhealthy: list[str]) -> dict | None:
        mon = self.config.get("monitoring", {})
        threshold = int(mon.get("failure_threshold_before_ai", 3))
        cooldown = int(mon.get("ai_consultation_cooldown_seconds", 300))
        persistent = [n for n in unhealthy if self.failures.get(n, 0) >= threshold]
        if not persistent or not self.ai.enabled:
            return None
        now = time.time()
        if now - self.ai.last_call < cooldown:
            return {"skipped": "cooldown"}
        self.ai.last_call = now

        service = next((s for s in self.services if s["name"] == persistent[0]), None)
        if not service:
            return None
        excerpt = tail(LOG_DIR / service["log"], 12)
        question = (
            f"Service '{service['name']}' on port {service['port']} is down and keeps "
            f"failing to start. It is started with:\n"
            f"  {' '.join(service['cmd'])}\n"
            f"Last log lines:\n{excerpt}\n"
            "Reply with one shell command that repairs it."
        )
        proposal = self.ai.propose_command(question)
        if not proposal.get("ok"):
            log("WARN", f"AI consultation unavailable: {proposal.get('error')}")
            return {"ok": False, "error": proposal.get("error")}
        if not proposal.get("allowed"):
            log("WARN", f"AI proposed a command that is not on the allowlist, ignoring: "
                        f"{proposal.get('command')}")
            return {"ok": True, "allowed": False, "command": proposal.get("command")}
        command = proposal["command"]
        log("INFO", f"AI proposed: {command}")
        outcome = run_allowed_command(
            command, self.bridge, self.ai.allowlist, self.ai.denylist)
        if outcome.get("success"):
            log("INFO", "AI-proposed command executed")
        else:
            log("ERROR", f"AI-proposed command failed: {outcome.get('error')}")
        return {"ok": True, "command": command, "executed": outcome}

    # -- reporting -------------------------------------------------------
    def status(self) -> dict:
        services = []
        saved = RestartPolicy.load_saved()
        timeout = float(self.config.get("services", {}).get("health_check_timeout", 5))
        bridge_ok = True
        for svc in self.services:
            health = check_service(svc, timeout)
            if svc["name"] == "public-bridge":
                bridge_ok = health["state"] == "ok"
            services.append({
                "name": svc["name"], "port": svc["port"],
                "healthy": health["state"] == "ok",
                "state": health["state"], "detail": health["detail"],
                "failures": self.failures.get(svc["name"], 0),
                "restart_state": saved.get(svc["name"]),
            })
        services.append({"name": "aria (desktop)", "port": None,
                         "healthy": aria_running(), "failures": 0,
                         "restart_state": saved.get("aria")})
        tun_cfg = self.config.get("tunnel", {})
        tunnel = tunnel_health(check_public=bool(tun_cfg.get("public_check", True)),
                               timeout=float(tun_cfg.get("public_check_timeout", 10)),
                               bridge_ok=bridge_ok)
        services.append({"name": "bridge-tunnel", "port": BRIDGE_PORT,
                         "healthy": tunnel["healthy"], "state": tunnel["state"],
                         "detail": tunnel["detail"], "pid": tunnel["pid"],
                         "failures": 0, "restart_state": saved.get("bridge-tunnel")})
        url_file = TUNNEL_URL_FILE
        return {
            "agent": self.config.get("agent_name", "Autonomis"),
            "version": self.config.get("version"),
            "repo_root": str(REPO_ROOT),
            "public_url": url_file.read_text().strip() if url_file.exists() else None,
            "services": services,
            "healthy": sum(1 for s in services if s["healthy"]),
            "total": len(services),
            "mcp_tools": [t["name"] for t in self.bridge.describe()],
            "ai": {"enabled": self.ai.enabled, "model": self.ai.model,
                   "unavailable": self.ai.unavailable_reason},
        }


def acquire_single_instance_lock():
    """Take logs/autonomis.lock; return the open file, or None if another
    Autonomis holds it."""
    try:
        import fcntl
    except ImportError:  # not POSIX - fall back to no lock
        return open(os.devnull, "w")
    fh = open(LOCK_FILE, "a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        other = "?"
        try:
            other = PID_FILE.read_text().strip() or "?"
        except OSError:
            pass
        log("ERROR", f"another Autonomis agent is already running (pid {other}) - "
                     f"not starting a second one")
        return None
    fh.seek(0)
    fh.truncate()
    fh.write(str(os.getpid()))
    fh.flush()
    return fh


def _handle_signal(signum, _frame):
    global _RUNNING
    log("INFO", f"received signal {signum} - shutting down")
    _RUNNING = False


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomis - One2lvOS autonomous monitor")
    parser.add_argument("--once", action="store_true",
                        help="run a single repair pass and exit")
    parser.add_argument("--status", action="store_true",
                        help="print a status report and exit")
    parser.add_argument("--interval", type=int, default=None,
                        help="override the check interval in seconds")
    parser.add_argument("--no-bytecode-clean", action="store_true",
                        help="skip clearing stale .pyc caches")
    parser.add_argument("--nimlab", metavar="TOOL",
                        help="run one nimlab.<TOOL> through the reactor's L0-L3 tiers, print the result, exit")
    parser.add_argument("--nimlab-args", metavar="JSON", default="{}",
                        help="JSON arguments for --nimlab")
    args = parser.parse_args()

    if args.nimlab:
        load_env()
        out = nimlab_call(args.nimlab, json.loads(args.nimlab_args))
        print(json.dumps(out, indent=2, default=str))
        return 0 if out.get("ok") else 1

    if not args.no_bytecode_clean:
        removed = clear_stale_bytecode()
        if removed:
            log("INFO", f"cleared {removed} stale bytecode cache file(s)")

    load_env()
    agent = Autonomis()

    if args.status:
        print(json.dumps(agent.status(), indent=2))
        return 0

    interval = args.interval or int(
        agent.config.get("monitoring", {}).get("check_interval_seconds", 30))

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    # One agent at a time: two agents would each see a service down and each
    # start a copy. The lock is released by the kernel when the process ends,
    # so a crash never leaves it stuck (unlike a bare pid file).
    lock_fh = acquire_single_instance_lock()
    if lock_fh is None:
        return 1
    PID_FILE.write_text(str(os.getpid()))
    log("INFO", f"=== {agent.config.get('agent_name', 'Autonomis')} agent start === "
                f"(every {interval}s, pid {os.getpid()})")
    log("INFO", f"repo root: {REPO_ROOT}")

    try:
        if args.once:
            agent.cycle()
            return 0
        while _RUNNING:
            try:
                report = agent.cycle()
                if report["restarts"] or report["actions"]:
                    log("INFO", f"cycle: {len(report['restarts'])} restart(s), "
                                f"{len(report['actions'])} install action(s)")
            except Exception as exc:
                log("ERROR", f"cycle failed: {type(exc).__name__}: {exc}")
            for _ in range(interval):
                if not _RUNNING:
                    break
                time.sleep(1)
    finally:
        try:
            # Only remove the pid file if it is still ours.
            if PID_FILE.read_text().strip() == str(os.getpid()):
                PID_FILE.unlink()
        except OSError:
            pass
        lock_fh.close()
        log("INFO", "autonomis agent stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
