"""Public tunnels for the test server, with cloudflared.

Modes (server_settings.json -> "tunnel"):
    off     local only (or LAN), the default
    quick   a random https://<words>.trycloudflare.com URL:
            cloudflared tunnel --url http://127.0.0.1:<port>
    named   an existing Cloudflare tunnel, either
              token:  cloudflared tunnel run, with the token from the
                      dashboard (saved in ~/.config/nimlab/cloudflared_token,
                      mode 600; passed in the TUNNEL_TOKEN environment
                      variable, never on the command line or in a log), or
              config: a tunnel ID or name, its credentials JSON file and the
                      public hostname; a cloudflared config.yml routing that
                      hostname to the local port is written for it.

`auto_start` starts the tunnel with `serve start` (and the service). When
cloudflared exits, the server keeps running: the exit is reported, and
`serve start` tries again with a growing delay.

The server always requires its API key, so a public URL alone lets nobody
in. The status (mode, URL, state) is kept in data/tunnel_status.json for
the dashboard.
"""

import json
import os
import platform
import re
import shutil
import stat
import subprocess
import threading
import time
import urllib.request

from . import config, store

MODES = ("off", "quick", "named")
QUICK_RX = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
NAMED_UP_RX = re.compile(r"Registered tunnel connection|Connection [0-9a-f-]+ registered", re.I)
TOKEN_RX = re.compile(r"^[A-Za-z0-9_\-=+/.]{40,}$")
HOST_RX = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.I)
STATUS_FILE = "tunnel_status.json"
RELEASE_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"
ARCHES = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64",
          "armv7l": "arm", "armv8l": "arm", "armv6l": "arm", "i686": "386", "i386": "386"}


def defaults():
    return {"tool": "cloudflared", "mode": "off", "auto_start": False,
            "named": {"method": "token", "tunnel": "", "credentials_file": "", "hostname": ""}}


def settings_of(server_settings):
    """The tunnel block of the server settings, every field filled in."""
    t = server_settings.setdefault("tunnel", {})
    for k, v in defaults().items():
        if k not in t:
            t[k] = json.loads(json.dumps(v))
        elif isinstance(v, dict) and isinstance(t[k], dict):
            for k2, v2 in v.items():
                t[k].setdefault(k2, v2)
    if t.get("mode") not in MODES:
        t["mode"] = "off"
    return t


# ---------------------------------------------------------------------------
# private files
# ---------------------------------------------------------------------------
def config_dir(env=None):
    env = os.environ if env is None else env
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME") or os.path.expanduser("~"), ".config")
    return os.path.join(base, "nimlab")


def token_path(env=None):
    env = os.environ if env is None else env
    return os.path.expanduser(env.get("NIMLAB_CLOUDFLARED_TOKEN_FILE") or
                              os.path.join(config_dir(env), "cloudflared_token"))


def write_private(path, text):
    """Write a file only its owner can read (mode 600), atomically."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def clean_token(token):
    return re.sub(r"\s+", "", token or "").removeprefix("--token").strip()


def save_token(token, env=None):
    token = clean_token(token)
    if "cloudflared" in token or "service install" in token:
        raise ValueError("Paste only the token, not the whole install command.")
    if not TOKEN_RX.match(token):
        raise ValueError("That does not look like a tunnel token (a long string from the Cloudflare dashboard).")
    write_private(token_path(env), token + "\n")
    return token


def load_token(env=None):
    env = os.environ if env is None else env
    if env.get("TUNNEL_TOKEN"):
        return env["TUNNEL_TOKEN"].strip()
    try:
        with open(token_path(env), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def delete_token(env=None):
    try:
        os.unlink(token_path(env))
        return True
    except OSError:
        return False


def mask(token):
    return ("..." + token[-4:]) if token else "(none)"


def config_yml_path(env=None):
    return os.path.join(config_dir(env), "cloudflared", "config.yml")


def config_yml(tunnel, credentials_file, hostname, port):
    """cloudflared config for a named tunnel: the hostname goes to the local
    port, anything else gets a 404. No secrets in it, only the path of the
    credentials file."""
    return (f"# Written by nimlab (serve tunnel named). Routes {hostname} to the test server.\n"
            f"tunnel: {tunnel}\n"
            f"credentials-file: {credentials_file}\n"
            f"ingress:\n"
            f"  - hostname: {hostname}\n"
            f"    service: http://127.0.0.1:{int(port)}\n"
            f"  - service: http_status:404\n")


def write_config_yml(named, port, env=None):
    p = config_yml_path(env)
    write_private(p, config_yml(named["tunnel"], os.path.expanduser(named["credentials_file"]),
                                named["hostname"], port))
    return p


def check_named(named, env=None):
    """Problems with a named-tunnel setup, in plain words (empty = fine)."""
    probs = []
    if named.get("method") == "token":
        if not load_token(env):
            probs.append("no tunnel token saved (serve tunnel named --token)")
    else:
        if not named.get("tunnel"):
            probs.append("no tunnel ID or name")
        cf = os.path.expanduser(named.get("credentials_file") or "")
        if not cf:
            probs.append("no credentials file (the <tunnel-id>.json from 'cloudflared tunnel create')")
        elif not os.path.isfile(cf):
            probs.append(f"credentials file {cf} not found")
        if not named.get("hostname"):
            probs.append("no public hostname")
    h = named.get("hostname")
    if h and not HOST_RX.match(h):
        probs.append(f"'{h}' is not a hostname (e.g. lab.example.com, without https://)")
    return probs


# ---------------------------------------------------------------------------
# status file
# ---------------------------------------------------------------------------
def status_path():
    return store.path(STATUS_FILE)


def read_status():
    st = config.load_json(status_path(), None)
    return st if isinstance(st, dict) else {}


def write_status(**fields):
    st = read_status()
    st.update(fields)
    st["updated_at"] = config.timestamp()
    try:
        config.save_json(status_path(), st)
    except OSError:
        pass
    return st


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def brief(st=None):
    """One line for the dashboard: 'quick https://... (up)', or ''."""
    st = read_status() if st is None else st
    if not st or st.get("mode") in (None, "off"):
        return ""
    up = st.get("state") == "up" and _pid_alive(st.get("pid"))
    url = st.get("url") or ""
    if up:
        return f"{st['mode']} {url}".strip()
    state = st.get("state") or "down"
    return f"{st['mode']} {url} ({'stopped' if state == 'up' else state})".replace("  ", " ")

def describe(tsettings, st=None):
    """The real tunnel state for summaries (3.7.4): the configured mode,
    whether a tunnel is running now and its current URL. The setup summary
    said 'tunnel off' while a quick tunnel was running and reachable.
    -> 'off', 'quick, running https://x.trycloudflare.com',
       'off (but a quick tunnel is running: https://...)', 'named, not running'."""
    st = read_status() if st is None else st
    mode = (tsettings or {}).get("mode") or "off"
    run_mode = (st or {}).get("mode")
    up = bool(st) and st.get("state") == "up" and _pid_alive(st.get("pid"))
    url = (st or {}).get("url") or ""
    if up and run_mode and run_mode != mode:
        return f"{mode} (but a {run_mode} tunnel is running{': ' + url if url else ''})"
    if mode == "off":
        return "off"
    if up:
        return f"{mode}, running{' ' + url if url else ''}"
    state = (st or {}).get("state")
    why = "stopped" if state == "up" else (state or "not running")
    return f"{mode}, {why}" + (f" (last URL {url})" if url and mode == "quick" else "")


# ---------------------------------------------------------------------------
# cloudflared itself
# ---------------------------------------------------------------------------
def find_cloudflared(env=None):
    env = os.environ if env is None else env
    exe = env.get("NIMLAB_CLOUDFLARED")
    if exe:
        return exe if os.path.isfile(exe) else None
    found = shutil.which("cloudflared", path=env.get("PATH"))
    if found:
        return found
    local = os.path.join(env.get("HOME") or os.path.expanduser("~"), ".local", "bin", "cloudflared")
    return local if os.path.isfile(local) and os.access(local, os.X_OK) else None


def is_termux(env=None):
    from .shortcut import is_termux as _t
    return _t(env)


def install_cloudflared(env=None, run=subprocess.run, download=None, machine=None, log=print):
    """Install cloudflared: `pkg install cloudflared` on Termux, else the
    official Linux binary from Cloudflare's GitHub releases into
    ~/.local/bin. Returns (ok, path or message)."""
    env = os.environ if env is None else env
    have = find_cloudflared(env)
    if have:
        return True, have
    if is_termux(env):
        log("Installing cloudflared: pkg install -y cloudflared")
        r = run(["pkg", "install", "-y", "cloudflared"])
        exe = find_cloudflared(env)
        if getattr(r, "returncode", 1) == 0 and exe:
            return True, exe
        return False, "pkg install cloudflared failed; run it yourself and look at its message."
    arch = ARCHES.get((machine or platform.machine()).lower())
    if not arch:
        return False, f"no cloudflared build for {machine or platform.machine()}; see developers.cloudflare.com"
    url = RELEASE_URL.format(arch=arch)
    dest_dir = os.path.join(env.get("HOME") or os.path.expanduser("~"), ".local", "bin")
    dest = os.path.join(dest_dir, "cloudflared")
    log(f"Downloading cloudflared from {url}")
    try:
        os.makedirs(dest_dir, exist_ok=True)
        data = (download or _download)(url)
        if len(data) < 1_000_000 or not data.startswith(b"\x7fELF"):
            return False, "the download is not a Linux program; try again later"
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o755)
        os.replace(tmp, dest)
    except OSError as e:
        return False, f"download failed: {e}"
    return True, dest


def _download(url, timeout=120):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


class CloudflaredTunnel:
    """One cloudflared process for the server's port. start() waits until it
    is up and returns the public URL; an exit later calls on_exit(code, tail)
    from a background thread (the server is not touched)."""

    def __init__(self, port, tsettings=None, mode=None, exe=None, env=None, on_exit=None, popen=subprocess.Popen,
                 config_env=None):
        self.port = int(port)
        self.t = settings_of({"tunnel": dict(tsettings or {})})
        self.mode = mode or (self.t["mode"] if self.t["mode"] != "off" else "quick")
        self.env = dict(os.environ if env is None else env)
        self.config_env = config_env if config_env is not None else self.env
        self.exe = exe or find_cloudflared(self.env)
        self.on_exit = on_exit
        self.popen = popen
        self.proc = None
        self.url = None
        self.output = []
        self.secret = ""
        self._stopping = False
        self._up = threading.Event()

    @property
    def alive(self):
        return bool(self.proc) and self.proc.poll() is None

    def command(self):
        base = [self.exe, "tunnel", "--no-autoupdate"]
        if self.mode == "quick":
            return base + ["--url", f"http://127.0.0.1:{self.port}"], {}
        named = self.t["named"]
        probs = check_named(named, self.config_env)
        if probs:
            raise RuntimeError("named tunnel not ready: " + "; ".join(probs))
        if named.get("method") == "token":
            self.secret = load_token(self.config_env)
            return base + ["run"], {"TUNNEL_TOKEN": self.secret}
        yml = write_config_yml(named, self.port, self.config_env)
        return base + ["--config", yml, "run", named["tunnel"]], {}

    def _scrub(self, line):
        return line.replace(self.secret, "***") if self.secret else line

    def start(self, wait=40):
        if not self.exe:
            try:
                from . import hostenv
                msg = hostenv.cloudflared_missing_message()
            except Exception:  # noqa: BLE001 - the hint must never hide the real problem
                msg = "cloudflared is not installed (serve tunnel install, or on Termux: pkg install cloudflared)"
            raise RuntimeError(msg)
        cmd, extra = self.command()
        env = dict(self.env, **extra)
        self.proc = self.popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               text=True, bufsize=1, env=env)
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        self._up.wait(wait)
        if not self.url:
            self.stop()
            self._thread.join(2)       # let the reader finish its last lines and status before we report
            tail = " | ".join(self.output[-3:])
            raise RuntimeError("cloudflared did not come up" + (f": {tail}" if tail else ""))
        write_status(mode=self.mode, url=self.url, state="up", pid=self.proc.pid, started_at=config.timestamp(),
                     port=self.port, last_error=None)
        return self.url

    def _reader(self):
        proc = self.proc
        for raw in proc.stdout:
            line = self._scrub(raw.rstrip())
            self.output.append(line)
            del self.output[:-50]
            if not self.url:
                if self.mode == "quick":
                    m = QUICK_RX.search(line)
                    if m:
                        self.url = m.group(0)
                elif NAMED_UP_RX.search(line):
                    self.url = "https://" + (self.t["named"].get("hostname") or "(hostname set in Cloudflare)")
                if self.url:
                    self._up.set()
        code = proc.wait()
        try:
            proc.stdout.close()
        except (OSError, AttributeError):
            pass
        self._up.set()
        if self._stopping:
            return
        tail = " | ".join(self.output[-3:])
        write_status(state="exited", exit_code=code, last_error=tail[:300] or None, pid=None)
        if self.url and self.on_exit:
            try:
                self.on_exit(code, tail)
            except Exception:  # noqa: BLE001 - a callback never takes the server down
                pass

    def stop(self):
        self._stopping = True
        p = self.proc
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        if self.url:
            write_status(state="stopped", pid=None)
        self.proc = None


class Keeper:
    """Keeps a tunnel up next to a running server: starts it, and when
    cloudflared exits, warns and starts it again after 10 s, 30 s, 60 s, ...
    (at most `tries` times in a row). Never raises into the server."""

    DELAYS = (10, 30, 60, 120, 300)

    def __init__(self, port, tsettings, warn=print, factory=None, tries=5, sleep=time.sleep, on_url=None):
        self.port, self.t, self.warn = port, tsettings, warn
        self.factory = factory or (lambda on_exit: CloudflaredTunnel(port, tsettings, on_exit=on_exit))
        self.tries, self.sleep, self.on_url = tries, sleep, on_url
        self.tunnel = None
        self.failures = 0
        self._stop = threading.Event()

    def start(self):
        try:
            self.tunnel = self.factory(self._exited)
            url = self.tunnel.start()
            self.failures = 0
            if self.on_url:
                self.on_url(url)
            return url
        except (RuntimeError, OSError) as e:
            write_status(mode=self.t.get("mode"), state="failed", last_error=str(e)[:300], pid=None)
            self.warn(f"[!] Tunnel did not start: {e}. The server keeps running without it.")
            return None

    def _exited(self, code, tail):
        if self._stop.is_set():
            return
        self.warn(f"[!] cloudflared exited (code {code}). The server keeps running; the public URL is down."
                  + (f" Last output: {tail}" if tail else ""))
        if self.on_url:
            self.on_url(None)
        threading.Thread(target=self._retry, daemon=True).start()

    def _retry(self):
        while not self._stop.is_set() and self.failures < self.tries:
            delay = self.DELAYS[min(self.failures, len(self.DELAYS) - 1)]
            self.failures += 1
            self.warn(f"    Trying the tunnel again in {delay} s ({self.failures}/{self.tries}).")
            self.sleep(delay)
            if self._stop.is_set():
                return
            if self.start():
                self.warn(f"[ok] Tunnel back up: {self.tunnel.url}")
                return
        if self.failures >= self.tries:
            self.warn("[!] Gave up on the tunnel; restart the server to try again.")

    def stop(self):
        self._stop.set()
        if self.tunnel:
            self.tunnel.stop()


def file_mode(path):
    try:
        return stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return None
