"""Guided setup: `nimlab setup` (or S in the launcher).

Walks through every setup step in order, one question at a time, sized for
a phone screen. Each step shows its status first, can be skipped, and shows
the status again afterwards; `nimlab setup <step>` runs one step alone.

Steps: deps, shortcut, key, mcp, grpc, memory, roles, server, telegram,
selfadmin. The server step covers the endpoint settings, the public tunnel
(none / Cloudflare quick tunnel / an existing named tunnel) and keeping it
running as a service.

Secrets (keys, tokens, passwords) are read with hidden input, written only
to private files (mode 600) and never printed or logged.
"""

import getpass
import json
import os
import re
import shutil
import subprocess
import time
import sys
import urllib.error
import urllib.request

from . import config, setupflow, store

MARK = "setup_state.json"


# ---------------------------------------------------------------------------
# input / output (tests pass a fake)
# ---------------------------------------------------------------------------
class IO:
    def say(self, text=""):
        print(text, flush=True)

    def ask(self, prompt, default=""):
        d = f" [{default}]" if default not in ("", None) else ""
        try:
            v = input(f"{prompt}{d}: ").strip()
        except EOFError:
            raise KeyboardInterrupt from None
        return v if v else str(default or "")

    def secret(self, prompt):
        try:
            return getpass.getpass(f"{prompt} (hidden): ").strip()
        except EOFError:
            raise KeyboardInterrupt from None

    def choose(self, prompt, options, default=None):
        """options: list of (key, label). Returns the key."""
        self.say(prompt)
        for i, (k, label) in enumerate(options, 1):
            self.say(f"  {i}) {label}")
        keys = [k for k, _ in options]
        dflt = str(keys.index(default) + 1) if default in keys else ""
        while True:
            v = self.ask("Choose", dflt).lower()
            if v.isdigit() and 1 <= int(v) <= len(options):
                return keys[int(v) - 1]
            if v in keys:
                return v
            self.say("  Type one of the numbers above.")

    def yes(self, prompt, default=True):
        v = self.ask(f"{prompt} (y/n)", "y" if default else "n").lower()
        return v.startswith("y")


def run_cli(argv, timeout=900, input_text=None, show=True, quiet_note=20):
    """Run `python -m nimlab ...`; returns (code, output). Output is shown
    as it arrives when show is true.

    3.7.1: the output is read on a thread, so `timeout` really ends the step
    (before, the stdout loop waited for the child forever and the timeout
    only began after it closed its output: the Telegram step hung). A step
    that prints nothing for `quiet_note` seconds says it is still working."""
    import queue
    import threading
    env = dict(os.environ, NIMLAB_COLOR="0")
    p = subprocess.Popen([sys.executable, "-m", "nimlab", *argv], cwd=config.PROJECT_DIR, env=env, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL)
    if input_text is not None:
        p.stdin.write(input_text)
        p.stdin.close()
    q = queue.Queue()

    def pump():
        try:
            for line in p.stdout:
                q.put(line)
        finally:
            q.put(None)

    threading.Thread(target=pump, daemon=True).start()
    out = []
    t0 = last = time.monotonic()
    try:
        return _pump_loop(p, q, out, argv, timeout, show, quiet_note, t0, last)
    except KeyboardInterrupt:
        # 3.7.2: Ctrl+C stops this step only; setup goes on with the next one
        p.kill()
        msg = f"(stopped with Ctrl+C: nimlab {' '.join(argv[:2])}; what it finished is kept)"
        if show:
            print("\n    " + msg, flush=True)
        return 130, "".join(out) + "\n" + msg


def _pump_loop(p, q, out, argv, timeout, show, quiet_note, t0, last):
    import queue
    while True:
        left = timeout - (time.monotonic() - t0)
        if left <= 0:
            p.kill()
            msg = f"(timed out after {int(timeout)} s: nimlab {' '.join(argv[:2])})"
            if show:
                print("    " + msg, flush=True)
            return 124, "".join(out) + "\n" + msg
        try:
            line = q.get(timeout=min(1.0, left))
        except queue.Empty:
            # the command ended but something it started (a background
            # service) still holds the output pipe: stop reading, do not
            # wait for the timeout
            if p.poll() is not None and time.monotonic() - last >= 2:
                break
            if show and quiet_note and time.monotonic() - last >= quiet_note:
                print(f"    ... still working ({int(time.monotonic() - t0)} s, Ctrl+C stops this step)", flush=True)
                last = time.monotonic()
            continue
        if line is None:
            break
        out.append(line)
        last = time.monotonic()
        if show:
            print("    " + line.rstrip(), flush=True)
    try:
        p.wait(timeout=max(1, timeout - (time.monotonic() - t0)))
    except subprocess.TimeoutExpired:
        p.kill()
        return 124, "".join(out) + "\n(timed out)"
    return p.returncode, "".join(out)


def run_sh(cmd, timeout=1800):
    """A system command with its output shown; returns the exit code."""
    print("    $ " + " ".join(cmd), flush=True)
    try:
        return subprocess.run(cmd, timeout=timeout).returncode
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"    {e}")
        return 127


def is_termux(env=None):
    from .shortcut import is_termux as t
    return t(env)


def role_embed_model():
    try:
        r = (cluster().get("roles") or {}).get("embedding")
        return (r.get("model") if isinstance(r, dict) else r) or ""
    except Exception:  # noqa: BLE001
        return ""


def _check_path():
    from . import store
    return os.path.join(store.data_dir(), "setup_memory_check.json")


def _ms_fingerprint(ms):
    import hashlib
    from . import ltm
    lt = ltm.settings_from(ms or {})
    keep = {"backend": lt.get("backend"), "embedding": lt.get("embedding"), "oracle": {
        k: v for k, v in (lt.get("oracle") or {}).items() if "pass" not in k}}
    return hashlib.sha256(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()[:16]


def classify_memory_test(code, out):
    """-> (level, reason) from `memory test` output. failed = no store at
    all (connection, credentials, tables); degraded = connected, but turns
    are not embedded (queued, keyword recall only) or the sizes differ."""
    bad = [ln.strip() for ln in (out or "").splitlines() if "[!!]" in ln]
    if code == 0 and not bad:
        return "ok", "passed"
    if not bad:
        return "failed", f"exit code {code}" + (" (timed out)" if code == 124 else "")
    first = bad[0].split("[!!]", 1)[-1].strip()
    hard = ("backend ", "backend check failed", "connect", "ORA-", "DPY-", "credentials", "login",
            "no such table", "does not exist")
    level = "failed" if any(h.lower() in first.lower() for h in hard) and not first.startswith("embedding") \
        else "degraded"
    more = f" (+{len(bad) - 1} more)" if len(bad) > 1 else ""
    return level, first[:220] + more


def record_memory_check(ms, code, out):
    level, why = classify_memory_test(code, out)
    try:
        os.makedirs(os.path.dirname(_check_path()), exist_ok=True)
        config.save_json(_check_path(), {"level": level, "reason": why, "fp": _ms_fingerprint(ms),
                                         "at": config.timestamp()})
    except Exception:  # noqa: BLE001 - status only
        pass
    return level, why


def memory_check_state(ms):
    """The last memory test setup ran for THESE memory settings, or None."""
    try:
        d = config.load_json(_check_path(), {}) or {}
    except Exception:  # noqa: BLE001
        return None
    if not d or d.get("fp") != _ms_fingerprint(ms):
        return None
    return d.get("level") or "failed", d.get("reason") or ""


# ---------------------------------------------------------------------------
# plain-words explanations
# ---------------------------------------------------------------------------
ORACLE_HINTS = [
    (r"ORA-01017", "The user name or password is wrong. Check the MEM password (it is case-sensitive)."),
    (r"ORA-12506|ORA-12505|\bACL\b|access control list",
     "The database refused this network. In the OCI console, open the Autonomous Database > Network > "
     "Access control list and add this device's public IP (or use a wallet connection)."),
    (r"ORA-12541|ORA-12543|ORA-12170|timed out|DPY-6005|DPY-4011",
     "Could not reach the database. Check the connection string, that the database is running (not "
     "stopped), the access list, and your internet connection."),
    (r"ORA-28759|wallet|DPY-4027|DPY-6000|ewallet|cwallet",
     "The wallet could not be used. Check the folder (it must hold tnsnames.ora and ewallet.pem) and the "
     "wallet password."),
    (r"ORA-12154|DPY-4000|could not resolve|TNS:could not",
     "The connection name was not found. With a wallet, use an alias from tnsnames.ora, such as "
     "svnbraindb_high."),
    (r"No module named 'oracledb'|oracledb is not installed|pip install oracledb",
     "The oracledb Python package is missing. Run step 1 (Install dependencies) or: pip install oracledb"),
    (r"ORA-01031|insufficient privileges",
     "MEM does not have the privilege for this (CREATE TABLE / CREATE INDEX). An admin has to grant it."),
    (r"ORA-00955|already exists", "The tables already exist; that is fine."),
    (r"cryptography", "The cryptography package is missing; on Termux run: pkg install python-cryptography"),
]


def explain_oracle(output):
    for rx, text in ORACLE_HINTS:
        if re.search(rx, output or "", re.I):
            return text
    return ""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def cluster():
    return config.load_cluster_config()


def raw_cluster():
    return config.load_json(config.CLUSTER_CONFIG, {}) or {}


def save_raw(cfg):
    config.save_json(config.CLUSTER_CONFIG, cfg)


def has_module(name):
    import importlib.util
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def check_nvidia_key(key, http=None):
    """(ok, message): one tiny request to NVIDIA's API with the key."""
    body = json.dumps({"model": "meta/llama-3.1-8b-instruct", "messages": [{"role": "user", "content": "hi"}],
                       "max_tokens": 1}).encode()
    req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        if http:
            status = http(req)
        else:
            with urllib.request.urlopen(req, timeout=30) as r:
                status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    except (OSError, urllib.error.URLError) as e:
        return None, f"could not reach NVIDIA ({e}); the key was not checked"
    if status in (401, 403):
        return False, f"NVIDIA refused the key (HTTP {status})"
    return True, f"NVIDIA accepted the key (HTTP {status})"


def nvidia_key_saved():
    from .cli import ENV_FILE
    return os.path.exists(ENV_FILE)


# ---------------------------------------------------------------------------
# the wizard
# ---------------------------------------------------------------------------
class Wizard:
    def __init__(self, io=None, cli=run_cli, sh=run_sh, key_check=check_nvidia_key, env=None, mcp_tools=None):
        self.io = io or IO()
        self.cli, self.sh, self.key_check = cli, sh, key_check
        self.env = os.environ if env is None else env
        self.mcp_tools = mcp_tools or (lambda: setupflow.mcp_tools(cluster()))
        # 3.7.2 order (SeVin): key first, then everything the key can see,
        # its function IDs and specs, the 200 OK test, MCP, roles, the rest
        self.steps = [
            ("key", "NVIDIA API key", self.st_key, self.do_key),
            ("discover", "Discover models (API catalog + build.nvidia.com)", self.st_discover, self.do_discover),
            ("functions", "Function IDs and specs (build.nvidia.com pages)", self.st_functions, self.do_functions),
            ("sweep", "200 OK test (which models answer)", self.st_sweep, self.do_sweep),
            ("mcp", "MCP server (tools)", self.st_mcp, self.do_mcp),
            ("roles", "Model stack (roles)", self.st_roles, self.do_roles),
            ("grpc", "gRPC function IDs (review)", self.st_grpc, self.do_grpc),
            ("memory", "Long-term memory", self.st_memory, self.do_memory),
            ("server", "Endpoint server, tunnel and service", self.st_server, self.do_server),
            ("telegram", "Telegram bot", self.st_telegram, self.do_telegram),
            ("selfadmin", "Self-admin (testbed can change its own setup)", self.st_selfadmin, self.do_selfadmin),
            # 3.8.6: optional, last so the earlier step numbers stay put
            ("audio", "Phone audio bridge (optional)", self.st_audio, self.do_audio),
        ]
        # done inside step 1 (after the key), and runnable on their own
        self.extra_steps = [
            ("deps", "Install dependencies", self.st_deps, self.do_deps),
            ("shortcut", "The 'nimlab' shortcut", self.st_shortcut, self.do_shortcut),
        ]
        self.results = {}

    say = property(lambda self: self.io.say)

    # -- flow -----------------------------------------------------------
    def step_keys(self):
        return [k for k, *_ in self.steps]

    def all_steps(self):
        return self.steps + self.extra_steps

    def step_no(self, key):
        return self.step_keys().index(key) + 1

    def offer_step(self, key, why):
        """Say why plainly, offer to run the earlier step `key` now.
        -> True when it ran."""
        title = next(t for k, t, *_ in self.steps if k == key)
        self.say(f"[!] {why}: run step {self.step_no(key)} ({title}).")
        if self.io.yes(f"Run step {self.step_no(key)} ({title}) now?", True):
            do = next(d for k, _t, _s, d in self.steps if k == key)
            do()
            return True
        return False

    def run(self, only=None):
        steps = [s for s in self.all_steps() if s[0] in only] if only else list(self.steps)
        n = len(steps)
        try:
            for i, (key, title, st, do) in enumerate(steps, 1):
                if not self.run_step(i, n, key, title, st, do, ask=not only):
                    break
        except KeyboardInterrupt:
            self.say("\nSetup stopped. Run it again any time: nimlab setup")
        mark_done()
        try:
            self.summary()
        except (KeyboardInterrupt, EOFError):
            pass
        except Exception as e:  # noqa: BLE001 - the summary never keeps the launcher from its menu
            self.say(f"[!] Could not show the summary: {type(e).__name__}: {e}")
        return 0

    def run_step(self, i, n, key, title, st, do, ask=True):
        self.say("")
        self.say(f"== Step {i}/{n}: {title} ==")
        ok, text, level = self._status3(st)
        self.say(f"Now: {self._mark(level, before=True)}{text}")
        first = True
        while True:
            if ask and first:   # "Run this step again?" -> yes goes straight back in
                c = self.io.choose("What now?", [("run", (self.RERUN.get(key, "Set up / change")) if ok
                                                  else "Set up"),
                                                 ("skip", "Skip"), ("quit", "Quit setup")],
                                   "skip" if ok else "run")
                if c == "quit":
                    return False
                if c == "skip":
                    self.results[key] = (ok, text, level)
                    return True
            first = False
            try:
                do()
            except KeyboardInterrupt:
                raise
            except Exception as e:  # noqa: BLE001 - one step failing never ends setup
                self.say(f"[x] This step failed: {type(e).__name__}: {e}")
            ok, text, level = self._status3(st)
            self.say(f"After: {self._mark(level)}{text}")
            self.results[key] = (ok, text, level)
            if key in self.LOOPS_ITSELF or not self.io.yes("Run this step again?", False):
                return True

    RERUN = {"discover": "Run discovery again (refresh)", "functions": "Read the pages again (refresh)",
             "sweep": "Run the 200 OK test again", "audio": "Set up a phone for audio now"}
    LOOPS_ITSELF = {"audio"}   # it asks "Register another phone?" itself

    @staticmethod
    def _mark(level, before=False):
        """[ok] only for a step that passed; a degraded or failed check never
        prints [ok] (3.7.1: memory showed After: [ok] beside a [!!] test)."""
        return {"ok": "[ok] ", "degraded": "[!] degraded: ", "failed": "[x] failed: "}.get(
            level, "[ ] " if before else "[!] ")

    def _status(self, fn):
        ok, text, _lvl = self._status3(fn)
        return ok, text

    def _status3(self, fn):
        """-> (ok, text, level); level ok | degraded | failed | todo. A
        status function may return (ok, text) or (ok, text, level)."""
        try:
            r = fn()
        except Exception as e:  # noqa: BLE001
            return False, f"unknown ({e})", "failed"
        if len(r) >= 3:
            ok, text, level = r[0], r[1], r[2]
        else:
            ok, text = r
            level = "ok" if ok else "todo"
        return bool(ok) and level == "ok", text, level

    def summary(self):
        self.say("")
        self.say("== Setup summary ==")
        todo = []
        for key, title, st, _do in self.steps + [x for x in self.extra_steps if not self._status(x[2])[0]]:
            # 3.7.4: every line is read again now, from the saved config, not
            # from the step's cached result (the phone's summary said MCP auth
            # x-api-key while config_cluster.json had bearer). The cached
            # result is only the fallback when reading the status fails.
            ok, text, level = self._status3(st)
            r = self.results.get(key)
            if text.startswith("unknown (") and r:
                ok, text, level = r if len(r) == 3 else (r[0], r[1], "ok" if r[0] else "todo")
            self.say(f"{self._mark(level, before=True)}{title}: {text}")
            if not ok:
                todo.append(key)
        try:
            from . import configlint
            for line in configlint.lines(raw_cluster()):
                self.say("[!] " + line)
        except Exception:  # noqa: BLE001 - the lint never breaks the summary
            pass
        if todo:
            self.say("Left to do: " + ", ".join(todo) + ". Run one: nimlab setup <step>")
        else:
            self.say("Everything is set up.")

    # -- 1 deps -----------------------------------------------------------
    def st_deps(self):
        need = {"riva.client": "nvidia-riva-client", "grpc": "grpcio", "oracledb": "oracledb",
                "cryptography": "cryptography"}
        missing = [pkg for mod, pkg in need.items() if not has_module(mod)]
        if not shutil.which("ffmpeg"):
            missing.append("ffmpeg")
        return (not missing), ("all installed" if not missing else "missing: " + ", ".join(missing))

    def do_deps(self):
        py = sys.executable
        if is_termux(self.env):
            self.say("Termux: system packages first (pip cannot build grpcio or cryptography here).")
            if self.sh(["pkg", "install", "-y", "python-grpcio", "ffmpeg", "python-cryptography"]) != 0:
                self.say("[!] pkg install failed; pip will try, but grpcio/cryptography may not build.")
        from . import hostenv
        if hostenv.externally_managed():
            # 3.7.4: PEP 668 (Ubuntu 23.04+, Debian 12). start.sh makes a venv
            # and installs there; never --break-system-packages.
            from .shortcut import start_script
            self.say("This Python is managed by the system (PEP 668): installing into a venv instead.")
            if self.sh(["bash", start_script(), "install"]) == 0:
                self.say("[ok] Done. Quit and run ./start.sh again so the lab runs from the venv.")
            else:
                self.say("[!] The venv install failed (see above). Needs: " + hostenv.install_hint("venv", hostenv.detect()))
            return
        req = os.path.join(config.PROJECT_DIR, "requirements.txt")
        self.say("Python packages from requirements.txt...")
        if self.sh([py, "-m", "pip", "install", "--prefer-binary", "--upgrade", "-r", req]) != 0:
            self.say("[!] pip failed for requirements.txt (see above).")
        self.say("oracledb (for Oracle memory)...")
        if self.sh([py, "-m", "pip", "install", "--prefer-binary", "--upgrade", "oracledb"]) != 0:
            self.say("[!] pip could not install oracledb. Oracle memory will not work until it does.")
        info = hostenv.detect()
        if hostenv.low_memory(info):
            self.say(f"[!] {info['mem_mb']} MB RAM and no swap. Add a swapfile so pip and the 200 OK test "
                     "don't run out of memory:")
            for ln in hostenv.SWAP_CMDS.splitlines():
                self.say("    " + ln)

    # -- 2 shortcut -------------------------------------------------------
    def st_shortcut(self):
        p = shutil.which("nimlab", path=self.env.get("PATH"))
        return bool(p), (p or "not installed")

    def do_shortcut(self):
        code, out = self.cli(["shortcut", "install"])
        if code == 0:
            self.say("Open a new terminal (or run: hash -r) and type nimlab from any folder.")

    # -- 3 NVIDIA key -----------------------------------------------------
    def st_key(self):
        from . import core
        k = core.load_api_key(self.env)
        if k:
            return True, core.mask(k) + (" (saved)" if nvidia_key_saved() else " (this session only)")
        return (nvidia_key_saved(), "saved in ~/.nimlab_env" if nvidia_key_saved() else "not set")

    def do_key(self):
        from . import core
        self.say("Get a key at build.nvidia.com (it starts with nvapi-).")
        k = core.sanitize_key(self.io.secret("NVIDIA API key"))
        if not k:
            self.say("No key entered; nothing changed.")
            return
        if not k.startswith("nvapi-"):
            self.say("[!] That does not start with nvapi-; check you copied the whole key.")
        os.environ["NVIDIA_API_KEY"] = k
        how = self.io.choose("Keep it?", [("save", "Save it (~/.nimlab_env, only you can read it)"),
                                          ("session", "Only for this session")], "save")
        if how == "save":
            from .cli import cmd_persist_key
            import argparse
            cmd_persist_key(argparse.Namespace(env_file=None, bashrc=None))
        ok, msg = self.key_check(k)
        self.say(("[ok] " if ok else "[!] " if ok is None else "[x] ") + msg)
        self.prereqs()

    def prereqs(self):
        """3.7.2: dependencies and the shortcut happen right after the key,
        quietly, so the key is always the first thing setup asks for."""
        ok, text = self._status(self.st_deps)
        if not ok:
            self.say(f"Installing what the lab needs ({text})...")
            self.do_deps()
        ok, _ = self._status(self.st_shortcut)
        if not ok:
            code, _out = self.cli(["shortcut", "install"], show=False)
            self.say("[ok] The 'nimlab' shortcut is installed (open a new terminal or run: hash -r)." if code == 0
                     else "[!] Could not install the 'nimlab' shortcut; run: nimlab setup shortcut")

    def have_key(self):
        from . import core
        return bool(core.load_api_key(self.env))

    # -- 2 discover -------------------------------------------------------
    def st_discover(self):
        n = len(setupflow.discovered_ids())
        return n > 0, (f"{n} models known (API catalog + build.nvidia.com)" if n else "no models discovered yet")

    def do_discover(self):
        argv = ["discover"]
        if not self.have_key():
            if not self.offer_step("key", "No NVIDIA key yet, so the key's own model list cannot be read"):
                self.say("Discovering from build.nvidia.com and the docs only (no key).")
                argv.append("--no-key")
        lim = setupflow.DISCOVER_LIMIT
        self.say(f"Reading the API catalog and build.nvidia.com (progress below; up to {lim // 60} minutes, "
                 "Ctrl+C stops this step and keeps what it found)...")
        code, _out = self.cli(argv, timeout=lim)
        n = len(setupflow.discovered_ids())
        if n:
            self.say(f"[ok] {n} models known.")
        elif code == 124:
            self.say("[!] Discovery ran out of time before it saved anything. Run it again: nimlab setup discover")
        else:
            self.say("[x] Discovery saved no models (the output above says why).")

    # -- 3 function IDs and specs ------------------------------------------
    def st_functions(self):
        specs = setupflow.spec_count()
        known, with_id = setupflow.grpc_counts()
        if not specs or not setupflow.discovered_ids() or not setupflow.functions_done():
            return False, "not read for this install yet" + (f" ({specs} spec pages shipped)" if specs else "")
        return True, f"{specs} model specs read, {with_id} of {known} gRPC-only models have a function ID"

    def do_functions(self):
        if not setupflow.discovered_ids():
            if not self.offer_step("discover", "No models discovered yet, so there are no pages to read"):
                return
            if not setupflow.discovered_ids():
                self.say("[!] Still no models discovered; skipping the pages for now.")
                return
        lim = setupflow.SPECS_LIMIT
        self.say("Reading each model's build.nvidia.com page and spec (endpoints, gRPC-only marks, function "
                 f"IDs, samples). No test requests yet. Up to {lim // 60} minutes, Ctrl+C keeps what it read...")
        self.cli(["sweep", "--plan-only", "--time-limit", str(lim)], timeout=lim + 120)
        self.cli(["grpc", "fill"], timeout=600)
        known, with_id = setupflow.grpc_counts()
        setupflow.mark_functions_done(setupflow.spec_count(), known, with_id)
        self.say(f"Specs read: {setupflow.spec_count()}. gRPC-only models: {known}, with a function ID: {with_id}.")

    # -- 4 the 200 OK sweep --------------------------------------------------
    def st_sweep(self):
        v = len(setupflow.verified_ids())
        probed, grpc = setupflow.probe_counts()
        if not probed:
            return False, "not run yet (roles, gRPC and memory use its results)"
        return v > 0, f"{v} models answered 200 OK, {probed} tested, {grpc} gRPC-only"

    def do_sweep(self):
        if not setupflow.discovered_ids():
            if not self.offer_step("discover", "No models discovered yet, so there is nothing to test"):
                return
        if not self.have_key():
            if not self.offer_step("key", "No NVIDIA key yet; the 200 OK test sends real requests with it"):
                return
        full, fast = setupflow.SWEEP_LIMIT // 60, setupflow.SWEEP_FAST_LIMIT // 60
        self.say("The 200 OK test sends one small request to each model and keeps the ones that answer. Roles, "
                 "gRPC and memory are built from its results (models_verified.json, probe_results.json).")
        c = self.io.choose("Run it now?", [
            ("full", f"Full test: every model (up to {full} minutes)"),
            ("fast", f"Faster: only models on build.nvidia.com, shorter waits (up to {fast} minutes)"),
            ("skip", "Skip for now (later steps will have no verified models; run: nimlab setup sweep)")], "full")
        if c == "skip":
            return
        lim = setupflow.SWEEP_LIMIT if c == "full" else setupflow.SWEEP_FAST_LIMIT
        argv = ["sweep", "--time-limit", str(lim)] + (["--fast", "--site-only"] if c == "fast" else [])
        self.cli(argv, timeout=lim + 300)
        st = self.st_sweep()
        self.say(("[ok] " if st[0] else "[!] ") + st[1])

    # -- 4 MCP ------------------------------------------------------------
    def st_mcp(self):
        from . import mcpkey, mcpmenu
        m = mcpmenu.saved_settings()          # read from the file now (3.7.4)
        src = "env MCP_API_KEY" if self.env.get("MCP_API_KEY") else ("saved" if mcpkey.saved_key() else "")
        url = m.get("url") or ""
        style, header = mcpmenu.saved_style(m)
        shown = f"header {header}" if style == "header" else style
        ok = bool(url) and (bool(src) or style == "none")
        return ok, f"url {url or 'not set'}, key {src or 'not set'}, auth {shown}"

    def do_mcp(self):
        from . import mcpmenu
        m = mcpmenu.saved_settings()
        style0, header0 = mcpmenu.saved_style(m)
        auth = {"style": style0, "header_name": header0}
        self.say("Tool access is set in the MCP server's admin console: every tool the endpoint lists is available "
                 "here. Use your agent's own endpoint if the server has one, e.g. https://svn-dev.online/mcp-quill "
                 "or https://svn-dev.online/mcp/quill.")
        url = self.io.ask("MCP server URL (https://.../mcp, .../mcp-<agent> or .../mcp/<agent>)", m.get("url") or "")
        if url:
            self.cli(["mcp", "set-url", url, "--no-test"])
        key = self.io.secret("MCP API key (Enter keeps the current one)")
        if key:
            self.cli(["mcp", "set-key", "--save", "--no-test"], input_text=key + "\n", show=False)
            self.say("[ok] MCP key saved (outside the project folder, owner-only).")
        style = self.io.choose("How does the server want the key?",
                               [("x-api-key", "X-API-Key header"), ("bearer", "Authorization: Bearer"),
                                ("header", "Another header name"), ("none", "No key")],
                               (auth.get("style") or "x-api-key").lower())
        argv = ["mcp", "auth", style]
        if style == "header":
            argv.append(self.io.ask("Header name", auth.get("header_name") or "X-API-Key"))
        self.cli(argv)
        self.say("Testing the MCP server...")
        code, out = self.cli(["mcp", "test"])
        if code != 0:
            if "401" in out or "403" in out:
                self.say("In plain words: the server refused the key. Check the key and the auth style.")
            elif "resolve" in out.lower() or "refused" in out.lower() or "timed out" in out.lower():
                self.say("In plain words: the server could not be reached. Check the URL and that it is up.")

    # -- 5 gRPC -----------------------------------------------------------
    def st_grpc(self):
        known, with_id = setupflow.grpc_counts()
        if not known:
            return False, "no gRPC-only models known yet (steps 3 and 4 find them)"
        return with_id == known, f"{with_id} of {known} gRPC-only models have a function ID"

    def do_grpc(self):
        """3.7.2: steps 3 and 4 already collected the IDs; this one reports
        them and lets the user fill or edit what is missing."""
        known, with_id = setupflow.grpc_counts()
        if not known:
            self.say("[!] No gRPC models known yet. That is missing data, not a key or network problem.")
            c = self.io.choose("Find them now?", [
                ("functions", f"Read the model pages (step {self.step_no('functions')}, no test requests)"),
                ("sweep", f"Run the 200 OK test (step {self.step_no('sweep')})"),
                ("skip", "Skip")], "functions")
            if c == "skip":
                return
            dict((k, d) for k, _t, _s, d in self.steps)[c]()
            known, with_id = setupflow.grpc_counts()
            if not known:
                self.say("[!] Still no gRPC-only models found; nothing to set here.")
                return
        self.cli(["grpc", "list"])
        if with_id < known and self.io.yes("Look up the missing function IDs from the model pages now?", True):
            self.cli(["grpc", "fill"], timeout=600)
        while True:
            c = self.io.choose("gRPC function IDs:", [("done", "Looks right"), ("check", "Check them (gRPC calls)"),
                                                      ("set", "Paste an ID for one model")], "done")
            if c == "done":
                return
            if c == "check":
                self.cli(["grpc", "check"])
                continue
            model = self.io.ask("Model id (Enter to cancel)")
            fid = self.io.ask("Function ID (from the model's \"Try API\" sample)") if model else ""
            if model and fid:
                self.cli(["grpc", "set", model, fid])

    # -- 6 memory ---------------------------------------------------------
    def st_memory(self):
        from . import memmenu
        ms = cluster().get("memory_settings", {})
        e = memmenu.effective(ms)
        st = memmenu.short_status(ms)
        if e["backend"] == "off":
            return True, st
        if e["configured"] == "oracle":
            cf = os.path.expanduser(e["lt"]["oracle"]["credentials_file"])
            if not os.path.exists(cf) and not self.env.get("NIMLAB_ORACLE_PASSWORD"):
                return False, st + "; credentials file missing", "failed"
        if e["configured"] == "ords":
            from .ltm_ords import load_credentials, missing_credentials
            try:
                miss = missing_credentials(load_credentials(e["lt"].get("ords") or {}, self.env)[0])
            except Exception as ex:  # noqa: BLE001
                miss = [str(ex)]
            if miss:
                return False, st + "; ORDS login missing: " + ", ".join(miss), "failed"
        chk = memory_check_state(ms)
        if chk:
            level, why = chk
            if level != "ok":
                return False, f"{st}; memory test: {why}", level
        return True, st

    def do_memory(self):
        from . import ltm
        ms = cluster().get("memory_settings", {})
        lt = ltm.settings_from(ms)
        b = self.io.choose("Where should long-term memory live?",
                           [("oracle", "Oracle database (shared with your other agents)"),
                            ("ords", "Oracle database over HTTPS (ORDS REST, no wallet or driver)"),
                            ("local", "A local folder"), ("off", "Off")],
                           lt.get("backend") if lt.get("backend") in ("oracle", "ords", "local", "off") else "oracle")
        if b == "off":
            self.cli(["memory", "use", "off"])
            return
        if b == "local":
            d = self.io.ask("Folder", (lt.get("local") or {}).get("directory") or
                            os.path.join(os.path.expanduser("~"), "nimlab-memory"))
            self.cli(["memory", "use", "local", os.path.expanduser(d)])
        elif b == "ords":
            self.ords_creds(lt.get("ords") or {})
            self.cli(["memory", "use", "ords"])
            self.profile_name(lt["oracle"])
        else:
            self.oracle_creds(lt["oracle"]["credentials_file"])
            self.cli(["memory", "use", "oracle"])
            self.profile_name(lt["oracle"])
        self.embedding()
        self.auto_switches()
        self.say("Testing memory...")
        code, out = self.cli(["memory", "test"])
        record_memory_check(cluster().get("memory_settings", {}), code, out)
        hint = explain_oracle(out) if b in ("oracle", "ords") else ""
        if hint:
            self.say("In plain words: " + hint)
        if code != 0:
            chk = memory_check_state(cluster().get("memory_settings", {})) or ("failed", "see above")
            self.say(f"[!] The memory test did not pass ({chk[0]}): {chk[1]}")
            return
        if b in ("oracle", "ords") and self.io.yes("Create the memory tables in MEM now (memory setup)?", True):
            code, out = self.cli(["memory", "setup"])
            hint = explain_oracle(out)
            if hint:
                self.say("In plain words: " + hint)

    def auto_switches(self):
        """3.7.1: ask about auto store and auto recall explicitly and write
        them with `memory set`, the same setting the menu and every channel
        read (memory_settings.long_term in config_cluster.json)."""
        from . import memmenu
        e = memmenu.effective(cluster().get("memory_settings", {}))
        st = self.io.yes("Store each conversation turn in long-term memory automatically (auto store)? "
                         f"Now: {'on' if e['auto_store'] else 'off'}", True)
        rc = self.io.yes("Recall related memories before each reply (auto recall)? "
                         f"Now: {'on' if e['auto_recall'] else 'off'}", True)
        self.cli(["memory", "set", "auto_store", "on" if st else "off"])
        self.cli(["memory", "set", "auto_recall", "on" if rc else "off"])

    def profile_name(self, o):
        """Optional custom name for this entity's memory profile. Default
        TESTBED (tables MEM.TESTBED_MEMORIES / TESTBED_META). Other agents'
        names are protected."""
        from . import memmenu
        cur = (o.get("profile_id") or "TESTBED").upper()
        self.say(f"Memory profile: {cur} (tables MEM.{(o.get('table_prefix') or 'TESTBED').upper()}_MEMORIES and "
                 "_META). You can give this agent its own name instead.")
        if not self.io.yes("Use a custom name for the memory profile?", False):
            return cur
        while True:
            name = self.io.ask("Profile name (letters, digits, _)", cur).strip().upper()
            if not name or name == cur:
                return cur
            why = memmenu.profile_name_problem(name)
            if not why:
                break
            self.say("Not that name: " + why + ".")
        self.cli(["memory", "set", "oracle.table_prefix", name])
        self.cli(["memory", "set", "oracle.profile_id", name])
        self.say(f"Memory profile: {name} (MEM.{name}_MEMORIES / {name}_META). Run memory setup to create the tables. "
                 f"If you give the agent its own MCP memory tool, name it {name.lower()}_mem so both point at one "
                 "profile.")
        return name

    def ords_creds(self, od):
        """The ORDS URL and login, saved outside the project (mode 600); the
        password or client secret is typed hidden."""
        from .ltm_ords import DEFAULT_CREDENTIALS, check_url, save_credentials
        path = os.path.expanduser(od.get("credentials_file") or DEFAULT_CREDENTIALS)
        old = config.load_json(path, {}) if os.path.exists(path) else {}
        if old and not self.io.yes(f"{path} exists. Replace it?", False):
            return
        self.say("ORDS: the schema's REST root, e.g. https://<host>/ords/mem (REST-enable the MEM schema and allow "
                 "REST-Enabled SQL first).")
        while True:
            url = self.io.ask("ORDS schema URL", old.get("base_url") or od.get("base_url") or "").strip().rstrip("/")
            bad = check_url(url)
            if not bad:
                break
            self.say("[!] " + bad)
        auth = self.io.choose("How does it sign in?",
                              [("basic", "Database user and password (basic)"),
                               ("oauth", "OAuth client id and secret (client credentials)")],
                              old.get("auth") or od.get("auth") or "basic")
        values = {"base_url": url, "auth": auth}
        if auth == "basic":
            values["user"] = self.io.ask("Database user", old.get("user") or "MEM")
            pw = self.io.secret(f"Password for {values['user']}")
            while not pw:
                pw = self.io.secret("The password cannot be empty. Password")
            values["password"] = pw
        else:
            values["client_id"] = self.io.ask("OAuth client id", old.get("client_id") or "")
            sec = self.io.secret("OAuth client secret")
            while not sec:
                sec = self.io.secret("The secret cannot be empty. Client secret")
            values["client_secret"] = sec
        save_credentials(path, values)
        self.cli(["memory", "set", "ords.base_url", url])
        self.cli(["memory", "set", "ords.auth", auth])
        self.say(f"Saved {path} (mode 600). The secret is not in config_cluster.json.")

    def oracle_creds(self, path):
        from .tunnel import write_private
        path = os.path.expanduser(path or "~/.config/nimlab/oracle_mem.json")
        old = config.load_json(path, {}) if os.path.exists(path) else {}
        if old and not self.io.yes(f"{path} exists. Replace it?", False):
            return
        user = self.io.ask("Database user", old.get("user") or "MEM")
        pw = self.io.secret(f"Password for {user}")
        while not pw:
            pw = self.io.secret("The password cannot be empty. Password")
        kind = self.io.choose("How do you connect?",
                              [("tls", "TLS connection string, no wallet (needs the database's access list "
                                       "to include this device's IP)"),
                               ("wallet", "Wallet folder (mTLS)")],
                              "wallet" if old.get("wallet_dir") else "tls")
        creds = {"user": user, "password": pw, "dsn": "", "wallet_dir": "", "wallet_password": ""}
        if kind == "tls":
            self.say("Paste the TLS connection string from OCI > Autonomous Database > Database connection "
                     "(TLS, not mTLS). It starts with (description= .")
            creds["dsn"] = self.io.ask("Connection string", old.get("dsn") if not old.get("wallet_dir") else "")
            self.say("Note: a TLS connection without a wallet only works when the database's access control "
                     "list (OCI > Network) includes this device's public IP.")
        else:
            w = os.path.expanduser(self.io.ask("Wallet folder (unzipped, with tnsnames.ora)",
                                               old.get("wallet_dir") or "~/wallet"))
            if not os.path.isfile(os.path.join(w, "tnsnames.ora")):
                self.say(f"[!] No tnsnames.ora in {w}; check the folder (unzip the wallet first).")
            aliases = []
            try:
                with open(os.path.join(w, "tnsnames.ora"), encoding="utf-8", errors="replace") as f:
                    aliases = re.findall(r"^\s*([A-Za-z0-9_]+)\s*=", f.read(), re.M)
            except OSError:
                pass
            if aliases:
                self.say("Aliases in the wallet: " + ", ".join(aliases))
            dflt = next((a for a in aliases if a.lower().endswith("_high")), aliases[0] if aliases else
                        "svnbraindb_high")
            creds["dsn"] = self.io.ask("Connection alias", old.get("dsn") if old.get("wallet_dir") else dflt)
            creds["wallet_dir"] = w
            creds["config_dir"] = w
            creds["wallet_password"] = self.io.secret("Wallet password (Enter if none)")
        write_private(path, json.dumps(creds, indent=2) + "\n")
        self.say(f"[ok] Wrote {path} (mode 600). The password is not shown or logged.")

    def embedding(self):
        """3.7.1: offer a known-working text embedding model whose size
        matches the memory table (MEM.<PROFILE>_MEMORIES is VECTOR(2048)).
        The memory test right after measures the real size and says so when
        it does not match."""
        from . import ltm
        role = role_embed_model()
        rec = ltm.RECOMMENDED_EMBED
        info = ltm.KNOWN_EMBED.get(rec, {})
        role_note = ltm.KNOWN_EMBED.get(role, {}).get("note", "")
        from . import roles as R
        kinds, _infos = R.kinds_from_store()
        verified = [r for r in setupflow.embed_options(setupflow.verified_ids(), kinds) if r[0] != rec][:6]
        if not setupflow.verified_ids():
            self.say(f"(No 200 OK results yet, so only the known models are offered; step "
                     f"{self.step_no('sweep')} adds the embedding models your key can reach.)")
        opts = [("recommended", f"{rec} ({info.get('dims')} dimensions, matches the VECTOR(2048) table; "
                                "text retrieval, needs input_type, recommended)")]
        opts += [(f"v{i}", f"{m} (passed 200 OK; {note})") for i, (m, _d, note) in enumerate(verified)]
        opts += [
                ("role", f"Use the embedding role's model ({role or 'not set'})" +
                 (f": {role_note}" if role_note else "")),
                ("nvidia", "Another NVIDIA embedding model by name (`nimlab memory embed models` lists them)"),
                ("keep", "Keep the current setting")]
        dflt = "role" if role and role not in ltm.KNOWN_BAD_EMBED else "recommended"
        c = self.io.choose("Embeddings (turn text into vectors for recall):", opts, dflt)
        if c.startswith("v") and c[1:].isdigit():
            self.cli(["memory", "embed", "nvidia", verified[int(c[1:])][0]])
        elif c == "recommended":
            self.cli(["memory", "embed", "nvidia", rec])
        elif c == "role":
            self.cli(["memory", "embed", "role"])
        elif c == "nvidia":
            m = self.io.ask("Model", rec)
            self.cli(["memory", "embed", "nvidia", m])

    # -- 7 roles ----------------------------------------------------------
    def st_roles(self):
        from . import roles as R
        c = cluster()
        n = sum(1 for d in R.ROLE_DEFS if R.is_set(c.get("roles", {}).get(d.key)))
        return n > 0 and R.is_set(c.get("roles", {}).get("persona")), f"{n}/{len(R.ROLE_DEFS)} roles set"

    def role_suggestions(self):
        from . import roles as R
        kinds, infos = R.kinds_from_store()
        verified = sorted(set(setupflow.verified_ids()) | set(R.grpc_ids_readonly()), key=str.lower)
        tools, err = self.mcp_tools()
        if err:
            self.say(f"(MCP tools not offered: {err})")
        return setupflow.suggest(raw_cluster().get("roles") or {}, verified, kinds, infos, tools), tools, verified

    def do_roles(self):
        """3.7.2: built from the 200 OK list and the MCP tools: one suggestion
        per role, then accept them all, change one, or keep the current ones."""
        if not setupflow.verified_ids():
            if not self.offer_step("sweep", "No models have passed the 200 OK test yet, so there is nothing "
                                            "verified to suggest"):
                self.say("Showing the current roles only; run step "
                         f"{self.step_no('sweep')} later for suggestions.")
                self.cli(["roles", "show"])
                return
        sugg, tools, verified = self.role_suggestions()
        while True:
            self.say(f"Suggestions from {len(verified)} verified models and {len(tools)} MCP tools:")
            for i, r in enumerate(sugg, 1):
                same = r["pick"] == r["current"]
                self.say(f"  {i:>2}. {r['name']:<22} now {setupflow.describe(r['current'])}" +
                         ("" if same or not r["pick"] else f"  ->  {setupflow.describe(r['pick'])}") +
                         f"  ({r['why']})")
            c = self.io.choose("Roles:", [("accept", "Accept all suggestions"), ("one", "Change one role"),
                                          ("keep", "Keep the current roles")], "accept")
            if c == "keep":
                return
            if c == "accept":
                raw = raw_cluster()
                changed = [setupflow.apply_choice(raw, r["key"], r["pick"], tools) for r in sugg
                           if r["pick"] and r["pick"] != r["current"]]
                if changed:
                    save_raw(raw)
                    self.say("[ok] Set " + "; ".join(changed))
                else:
                    self.say("[ok] Every role already matches its suggestion.")
                return
            n = self.io.ask(f"Role number (1-{len(sugg)}, Enter to go back)")
            if not str(n).isdigit() or not 1 <= int(n) <= len(sugg):
                continue
            r = sugg[int(n) - 1]
            opts = r["options"][:30]
            if not opts:
                self.say(f"Nothing verified suits {r['name']} yet; type a model id or go back.")
            for j, (b, v, note) in enumerate(opts, 1):
                self.say(f"    {j:>2}. {setupflow.describe((b, v))}  [{note}]")
            pick = self.io.ask("Number, or a model id (Enter to go back)")
            if not pick:
                continue
            choice = opts[int(pick) - 1][:2] if str(pick).isdigit() and 1 <= int(pick) <= len(opts) \
                else ("model", pick.strip())
            r["pick"], r["why"] = choice, "your choice"

    # -- 8 server, tunnel, service -----------------------------------------
    def st_server(self):
        from . import server as S, tunnel, service
        s = S.load_settings()
        t = tunnel.settings_of(s)
        svc = service.brief()
        return True, (f"port {s.get('port')}, {'LAN' if s.get('lan') else 'local'}, model "
                      f"{s.get('model_name') or 'testbed'}, tunnel {tunnel.describe(t)}, service {svc}")

    def do_server(self):
        self.server_settings()
        from . import configlint
        for line in configlint.lines(raw_cluster()):
            self.say("[!] " + line)
        self.server_test()
        self.tunnel_step()
        self.service_step()

    def server_settings(self):
        from . import server as S, core
        s = S.load_settings()
        lan = self.io.choose("Bind address: who can reach the server directly?",
                             [("local", "Only this device (127.0.0.1)"), ("lan", "Same Wi-Fi too (0.0.0.0)")],
                             "lan" if s.get("lan") else "local")
        s["lan"] = lan == "lan"
        s["bind"] = "0.0.0.0" if s["lan"] else "127.0.0.1"
        port = self.io.ask("Port", s.get("port", 8765))
        if str(port).isdigit() and 1024 <= int(port) <= 65535:
            s["port"] = int(port)
        else:
            self.say("[!] Not a port between 1024 and 65535; kept " + str(s.get("port")))
        name = self.io.ask("Model name clients use", s.get("model_name") or "testbed")
        if re.fullmatch(r"[A-Za-z0-9._:/-]{1,64}", name):
            s["model_name"] = name
        else:
            self.say("[!] Use letters, digits and . _ : / - only; kept " + str(s.get("model_name")))
        k = s.get("api_key") or ""
        self.say(f"Endpoint API key: {core.mask(k) if k else 'none'}. Clients must send it; it is always required.")
        c = self.io.choose("API key:", [("keep", "Keep it"), ("new", "Make a new random key"),
                                        ("own", "Type my own (hidden)")], "keep" if k else "new")
        if c == "new":
            s["api_key"] = S.new_key()
            s["key_created_at"] = config.timestamp()
            self.say("[ok] New key made. See it with: nimlab serve info (it is not printed here).")
        elif c == "own":
            own = self.io.secret("Endpoint API key (at least 16 characters)")
            if len(own) >= 16:
                s["api_key"] = own
                s["key_created_at"] = config.timestamp()
            else:
                self.say("[!] Too short; kept the old key.")
        cors = self.io.ask("Allowed browser origin (CORS): * for any, or one origin like https://chat.example.com",
                           s.get("cors_origin") or "*")
        s["cors_origin"] = cors.strip() or "*"
        words = self.io.ask("Streaming: words per streamed chunk (1-20)", s.get("stream_chunk_words", 3))
        if str(words).isdigit() and 1 <= int(words) <= 20:
            s["stream_chunk_words"] = int(words)
        ent = s.setdefault("entity", {})
        ent["trace"] = self.io.choose("Routing trace in replies:", [("off", "Off"), ("field", "As a JSON field"),
                                                                    ("content", "Also under the reply text")],
                                      ent.get("trace", "field"))
        s["agent_tool_calls"] = "allow" if self.io.yes(
            "Run MCP tool calls for remote clients without asking (when confirmation is on)?",
            s.get("agent_tool_calls") == "allow") else "deny"
        s["log_requests"] = self.io.yes("Keep a request log?", bool(s.get("log_requests", True)))
        S.save_settings(s)
        self.say("[ok] Server settings saved.")

    def server_test(self):
        if self.io.yes("Test the server locally now (/v1/models)?", True):
            from . import server as S
            full = bool(S.load_settings().get("setup_full_self_test"))
            # setup runs the basic checks; the heavy live media checks are
            # `nimlab serve test --full` (or setup_full_self_test on)
            while True:
                code, out = self.cli(["serve", "test"] + (["--full"] if full else ["quick"]))
                if code == 0:
                    return
                c = self.io.choose("Some self-test checks failed (the summary above says which and why).",
                                   [("continue", "Continue setup (run `nimlab serve test` later)"),
                                    ("retry", "Retry the test now (a role may have been waking up)")],
                                   "continue")
                if c != "retry":
                    self.say("Setup goes on; run `nimlab serve test` again once the roles are awake.")
                    return

    def tunnel_step(self):
        from . import server as S, tunnel
        s = S.load_settings()
        t = tunnel.settings_of(s)
        c = self.io.choose("Make the endpoint reachable from the internet?",
                           [("off", "No, local only"),
                            ("quick", "Cloudflare quick tunnel (random trycloudflare.com URL, no account)"),
                            ("named", "My own Cloudflare tunnel (token, or tunnel ID + credentials file)")],
                           t["mode"])
        if c == "off":
            self.cli(["serve", "tunnel", "off"])
            return
        if not tunnel.find_cloudflared(self.env):
            if self.io.yes("cloudflared is not installed. Install it now?", True):
                self.cli(["serve", "tunnel", "install"])
        self.say("The endpoint becomes public: its API key stays required on every request (strongly "
                 "recommended; it cannot be turned off).")
        if c == "quick":
            self.cli(["serve", "tunnel", "quick"])
        else:
            how = self.io.choose("Which kind?", [("token", "Tunnel token (Zero Trust > Networks > Tunnels)"),
                                                 ("config", "Tunnel ID or name + credentials JSON file")],
                                 t["named"].get("method", "token"))
            host = self.io.ask("Public hostname (e.g. lab.example.com)", t["named"].get("hostname") or "")
            argv = ["serve", "tunnel", "named"]
            if how == "token":
                tok = self.io.secret("Tunnel token")
                argv.append("--token")
                if host:
                    argv += ["--hostname", host]
                self.cli(argv, input_text=(tok + "\n") if tok else "\n", show=True)
            else:
                tid = self.io.ask("Tunnel ID or name", t["named"].get("tunnel") or "")
                cred = self.io.ask("Credentials file", t["named"].get("credentials_file") or
                                   ("~/.cloudflared/" + tid + ".json" if tid else ""))
                argv += [tid, "--credentials", cred] + (["--hostname", host] if host else [])
                self.cli(argv)
        auto = self.io.yes("Start the tunnel automatically with the server?", True)
        self.cli(["serve", "tunnel", "auto", "on" if auto else "off"])

    def service_step(self):
        from . import service
        mgr = service.Manager()
        self.say(f"Keep it running: a background service restarts the server (and tunnel) if it crashes. "
                 f"Here that uses: {mgr.backend}.")
        holder = service.SupervisorLock().holder()
        if holder and mgr.installed():
            # 3.7.4: runit already started it; installing again would start a second copy
            self.say(f"[ok] The service already runs (supervisor pid {holder}, {mgr.backend}). It picks up later "
                     "setup changes (Telegram, server) by itself.")
            c = self.io.choose("Background service:", [("skip", "Keep it as it is"), ("remove", "Remove it")],
                               "skip")
        else:
            c = self.io.choose("Background service:", [("install", "Install and start it"), ("skip", "Not now")]
                               + ([("remove", "Remove it")] if mgr.installed() else []),
                               "skip" if mgr.installed() else "install")
        if c == "skip":
            return
        if c == "remove":
            self.cli(["service", "remove"])
            return
        argv = ["service", "install"]
        if is_termux(self.env) and self.io.yes("Start it when the phone boots (Termux:Boot)?", True):
            argv.append("--boot")
        self.cli(argv)

    # -- 9 telegram -------------------------------------------------------
    def st_telegram(self):
        from . import telegram
        b = telegram.brief()
        return b != "not set up" and bool(telegram.settings().get("allow")), b

    def do_telegram(self):
        from . import telegram, service
        if not self.io.yes("Connect a Telegram bot? (make one with @BotFather: /newbot)", True):
            return
        if telegram.load_token() and not self.io.yes("A bot token is saved. Replace it?", False):
            code, _ = self.cli(["telegram", "test"])
        else:
            tok = self.io.secret("Bot token from @BotFather")
            if not tok:
                return
            code, _ = self.cli(["telegram", "set-token"], input_text=tok + "\n")
        if code != 0:
            self.say("In plain words: Telegram did not accept the token; copy it again from @BotFather.")
            return
        t = telegram.settings()
        if not t.get("allow") or self.io.yes("Capture your Telegram ID again (send /start to the bot)?", False):
            how = self.io.choose("Add yourself to the bot's allowlist:",
                                 [("capture", "Capture: I send /start to the bot now (up to 2 minutes, shows "
                                              "progress, Ctrl+C stops)"),
                                  ("manual", "Type my numeric Telegram ID (the bot answers /id with it)"),
                                  ("skip", "Skip for now")], "capture")
            code = 1
            if how == "capture":
                code, out = self.cli(["telegram", "allow", "--capture", "120"], timeout=150)
                if "409" in out:
                    self.say("In plain words: another program polls this bot (an older Nim Lab service or "
                             "copy, another phone or PC), so Telegram hands the messages to it, not to setup. "
                             "`nimlab service status` lists stray copies; `nimlab service cleanup` stops them.")
            if how == "manual" or (how == "capture" and code != 0 and
                                   self.io.yes("Type your Telegram ID by hand instead?", True)):
                uid = self.io.ask("Your numeric Telegram ID (send /id to the bot to see it)", "").strip()
                if uid:
                    self.cli(["telegram", "allow", uid])
            t = telegram.settings()
            self.say(f"Saved: bot @{t.get('username') or '?'}, allowlist {', '.join(map(str, t['allow'])) or '(empty)'}"
                     + (f", owner {t['owner']}" if t.get("owner") else ""))
        mode = self.io.choose("How should the bot get messages?",
                              [("polling", "Polling (works anywhere, no public URL)"),
                               ("webhook", "Webhook through the Cloudflare tunnel")], t.get("mode", "polling"))
        self.cli(["telegram", "mode", mode])
        if mode == "webhook":
            from . import server as S, tunnel
            if tunnel.settings_of(S.load_settings())["mode"] == "off":
                self.say("[!] Webhook mode needs a tunnel: set one in the server step.")
        v = self.io.yes("Answer voice notes with a voice note too?", bool(t.get("voice_replies")))
        self.cli(["telegram", "voice", "on" if v else "off"])
        if self.io.yes("Run the bot inside the background service (auto-restart)?", True):
            self.cli(["service", "telegram", "on"])
            if service.SupervisorLock().holder():
                # 3.7.4: the running supervisor watches config_cluster.json and
                # starts the bot itself; a restart is not needed
                self.say("[ok] The running service starts the bot within a few seconds "
                         "(check: nimlab service status).")
            elif service.Manager().installed():
                self.cli(["service", "start"])
            else:
                self.say("Install the service in the server step for it to start.")

    # -- 10 self-admin ----------------------------------------------------
    # -- 12 phone audio bridge (3.8.6, optional) ---------------------------
    def st_audio(self):
        from . import audiosetup
        return audiosetup.status()

    def do_audio(self):
        from . import audiosetup
        audiosetup.flow(self.io)

    def st_selfadmin(self):
        from . import selfadmin
        sa = selfadmin.settings(raw_cluster())
        return True, (f"{'on' if sa['enabled'] else 'off'}, shell {'on' if sa['shell'] else 'off'}, admin key "
                      f"{'made' if selfadmin.load_admin_key() else 'not made'}")

    def do_selfadmin(self):
        from . import selfadmin
        sa = selfadmin.settings(raw_cluster())
        on = self.io.yes("Let the testbed inspect and change its own setup (admins only, every change "
                         "undoable and logged)?", sa["enabled"])
        self.cli(["selfadmin", "on" if on else "off"])
        if not on:
            return
        sh = self.io.yes("Also allow shell commands and code edits inside the project folder (asks you each "
                         "time)?", sa["shell"])
        self.cli(["selfadmin", "shell", "on" if sh else "off"])
        if not selfadmin.load_admin_key() and self.io.yes("Make an admin key for remote clients (and the "
                                                          "Telegram owner)?", True):
            selfadmin.new_admin_key()
            self.say(f"[ok] Admin key saved to {selfadmin.admin_key_path()} (mode 600). Not shown here; "
                     "read it from that file when a client needs it.")


# ---------------------------------------------------------------------------
# first-run marker and CLI
# ---------------------------------------------------------------------------
def mark_path():
    return store.path(MARK)


def mark_done():
    try:
        config.save_json(mark_path(), {"offered_at": config.timestamp()})
    except OSError:
        pass


def first_run():
    return not os.path.exists(mark_path())


ALIASES = {"dependencies": "deps", "install": "deps", "nvidia": "key", "api-key": "key", "memory": "memory",
           "catalog": "discover", "discovery": "discover", "specs": "functions", "function-ids": "functions",
           "functionids": "functions", "pages": "functions", "200": "sweep", "200ok": "sweep", "probe": "sweep",
           "verify": "sweep", "roles": "roles",
           "ltm": "memory", "models": "roles", "stack": "roles", "serve": "server", "endpoint": "server",
           "tunnel": "server", "service": "server", "bot": "telegram", "admin": "selfadmin",
           "self-admin": "selfadmin", "phone": "audio", "phones": "audio", "nimbridge": "audio",
           "bridge": "audio"}


def cmd_setup(args):
    w = Wizard()
    step = (args.step or "").lower()
    if step == "first-run":
        return 0 if first_run() else 1
    if step == "skip-first-run":
        mark_done()
        return 0
    if step == "list":
        for i, (k, title, st, _d) in enumerate(w.steps, 1):
            ok, text = w._status(st)
            print(f"{i:>2}. {k:<10} {'[ok]' if ok else '[  ]'} {title}: {text}")
        for k, title, st, _d in w.extra_steps:
            ok, text = w._status(st)
            print(f"    {k:<10} {'[ok]' if ok else '[  ]'} {title} (done with step 1): {text}")
        return 0
    if step == "tunnel":
        try:
            w.tunnel_step()
        except KeyboardInterrupt:
            print()
        return 0
    if step == "service":
        try:
            w.service_step()
        except KeyboardInterrupt:
            print()
        return 0
    if step:
        key = ALIASES.get(step, step)
        if step.isdigit() and 1 <= int(step) <= len(w.steps):
            key = w.steps[int(step) - 1][0]
        if key not in [k for k, *_ in w.all_steps()]:
            print(f"No step '{step}'. Steps: {', '.join(w.step_keys())} (or deps, shortcut, tunnel, service, list)")
            return 2
        return w.run(only=[key])
    return w.run()
