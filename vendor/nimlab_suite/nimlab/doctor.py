"""`nimlab doctor` (v3.7.1): one command that checks the parts that break
quietly: the long-term memory connection (a real write + semantic recall +
keyword search through the wallet/DSN on this phone), the system prompts
(no instructions to call tools that don't exist), and the MCP tools the
persona would get.

3.8.2: every check is also a record ({section, id, status, message, fix,
repair}) so `nimlab doctor --json` gives the Telegram /health command and
scripts something to parse instead of colored text. `nimlab doctor --fix`
runs only the safe repairs (stale pid files whose owner is dead, file
permissions, settings that can never work), backs the settings up first and
checks again afterwards. It never stops a running process and never sends
anything to NVIDIA or your gateways."""
import json
import os
import shutil
import stat
import sys
import time

from . import colors as C


def memory_checks(ent):
    """[(ok, msg)] for the memory store, with a write/recall round trip."""
    m = ent.memory
    if m is None or (m.settings or {}).get("backend") == "off":
        return [(True, "long-term memory is off (nothing to check)")]
    out = [(not m.offline, ent.memory_startup_line().replace("[memory] ", ""))]
    if m.offline:
        return out
    try:
        out += m.roundtrip()
        if hasattr(m, "roundtrip_identity"):
            out += m.roundtrip_identity()
    except Exception as e:  # noqa: BLE001 - a check reports, it never crashes
        out.append((False, f"round trip failed: {type(e).__name__}: {e}"))
    return out


def prompt_checks(ent):
    from . import environment as ENV
    warns = ENV.lint_entity(ent)
    if not warns:
        return [(True, "system prompts name no tools that are missing")]
    return [(False, w) for w in warns]


def mcp_checks(ent):
    s = ent.mcp_settings or {}
    if not s.get("enabled") or not s.get("url"):
        return [(True, "MCP chat tools are off")]
    tools = ent.refresh_tools() if hasattr(ent, "refresh_tools") else []
    if getattr(ent, "tools_error", None):
        return [(False, f"MCP server unavailable: {ent.tools_error}")]
    from . import mcpmenu
    out = [(True, ent.mcp_startup_line(tools).replace("[MCP] ", "") +
            " (loaded on first use on every channel: terminal, Telegram, voice, server, scheduler, heartbeat)")]
    own = (s.get("own_memory_tool") or "").strip()
    if own:
        t = next((x for x in tools or [] if x.get("name") == own), None)
        if t is None:
            out.append((False, f"own_memory_tool {own} is not in the server's tool list"))
        else:
            probs = mcpmenu.check_memory_tool_schema(t)
            out.append((not probs, f"own_memory_tool {own}: " + ("; ".join(probs) if probs else "schema fits")))
    return out


def settings_checks(ent):
    """3.7.2: settings that look set but cannot work (a speech URL that is a
    website homepage, roles or fallbacks that are bare URLs)."""
    from . import configlint
    found = configlint.lines(getattr(ent, "cluster", None) or {})
    if not found:
        return [(True, "speech URLs and role models look like endpoints and model ids")]
    return [(False, line) for line in found]


def platform_checks(ent=None, info=None):
    """3.7.4: Python, venv, ffmpeg, cloudflared, linger, RAM/swap. Warnings
    show as [!] and do not fail the doctor; only a too-old Python does."""
    from . import hostenv
    rows = []
    for level, msg, fix in hostenv.checks(info):
        if level == "info":
            continue
        first = (fix or "").splitlines()
        tail = f" -> {first[0]}" if first else ""
        if len(first) > 1:
            tail += " (all commands: nimlab platform)"
        rows.append((True if level == "ok" else ("warn" if level == "warn" else False), msg + tail))
    return rows


def scheduler_checks(ent=None):
    """3.8.0: job schedules parse, shell jobs have shell on, no broken jobs,
    and the scheduler runs when jobs are enabled (a warning)."""
    from . import scheduler
    return scheduler.doctor_lines()


# ---------------------------------------------------------------------------
# 3.8.2 checks: processes and locks, the identity pin, config integrity,
# file permissions, custom endpoints
# ---------------------------------------------------------------------------
def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _pid_in(path):
    try:
        return int(open(path).read().strip() or 0) or None
    except (OSError, ValueError):
        return None


def stale_pid_files():
    """[(label, path, pid)] pid files whose process is gone."""
    from . import service as SV, telegram as TG
    out = []
    for label, path in (("supervisor.pid", SV.pid_path()), ("telegram bot.pid", TG.pid_path())):
        pid = _pid_in(path)
        if pid and not _alive(pid):
            out.append((label, path, pid))
    return out


def process_checks(ent=None):
    """One supervisor, one server, one Telegram poller, one scheduler."""
    from . import updater
    rows = []
    try:
        found = updater.nimlab_procs(updater.Host(), tpid=updater.tunnel_pid())
    except Exception as e:  # noqa: BLE001
        return [("warn", f"could not list processes: {e}")]
    count = {}
    for _p, _pp, k, _c in found:
        count[k] = count.get(k, 0) + 1
    dup = {k: n for k, n in count.items() if n > 1 and k != "tunnel"}
    if dup:
        rows.append((False, "duplicate copies running: " + ", ".join(f"{k} x{n}" for k, n in sorted(dup.items()))
                     + " -> run Clean restart (Health menu) or ./update.sh"))
    elif count:
        rows.append((True, "one copy of each running part: " + ", ".join(sorted(count))))
    else:
        rows.append((True, "no Nim Lab background processes are running"))
    for label, _path, pid in stale_pid_files():
        rows.append(("warn", f"{label} names pid {pid}, which is not running (stale) -> doctor --fix removes it"))
    return rows


def telegram_checks(ent=None):
    """The poller lock: free, held by one live poller, or stale (3.8.2)."""
    from . import telegram as TG
    from . import service as SV
    try:
        configured = bool(SV.settings().get("telegram")) or bool(TG.load_token())
    except Exception:  # noqa: BLE001
        configured = False
    try:
        st, pid, holders = TG.PollerLock().state() if os.path.exists(TG.lock_path()) else ("free", None, [])
    except (ImportError, OSError) as e:
        return [("warn", f"could not read the Telegram poller lock: {e}")]
    if st == "held":
        return [(True, f"Telegram poller lock held by pid {pid} (one poller)")]
    if st == "stale":
        who = ", ".join(f"pid {p}" for p, _c in holders) or "an unknown process"
        return [("warn", f"Telegram poller lock is stale: its owner (pid {pid or '?'}) is not a poller, "
                 f"but {who} still holds it -> start the bot again; it reclaims the lock "
                 "(Service & update > Clean restart)")]
    return [(True if not configured else "warn", "no Telegram poller is running" +
             (" -> start the service, or Telegram menu > Start the bot" if configured else ""))]


def identity_checks(ent):
    """3.8.2: pinned identity facts are on and readable (names only)."""
    m = getattr(ent, "memory", None)
    if m is None or (m.settings or {}).get("backend") == "off":
        return [(True, "identity pin: long-term memory is off")]
    if not (m.settings or {}).get("pin_identity", True):
        return [("warn", "identity pin is off: Quill won't keep your name across chats -> Memory settings")]
    try:
        facts = m.identity_facts() or {}
    except Exception as e:  # noqa: BLE001
        return [(False, f"identity pin: could not read the pinned facts ({e})")]
    if not facts:
        return [(True, "identity pin on; nothing pinned yet (say \"my name is ...\" once)")]
    return [(True, "identity pin on: " + ", ".join(sorted(facts)) + " pinned")]


def config_checks(ent=None):
    """config_cluster.json and the JSON files in data/ parse."""
    from . import config, store
    rows, bad = [], []
    for path in [config.CLUSTER_CONFIG, getattr(config, "SYSTEM_PROMPTS", "")] + \
            [os.path.join(store.data_dir(), n) for n in ("service.json", "scheduler_jobs.json")]:
        if not path or not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                json.load(f)
        except (OSError, ValueError) as e:
            bad.append(f"{os.path.basename(path)} ({str(e)[:60]})")
    rows.append((not bad, "settings files are valid JSON" if not bad else
                 "settings files that do not parse: " + "; ".join(bad) + " -> restore one from data/backups/"))
    return rows


def _private_files():
    from . import mcpkey, endpoints
    home = os.path.expanduser("~")
    return [p for p in (mcpkey.secrets_path() if hasattr(mcpkey, "secrets_path") else None,
                        endpoints.path(), os.path.join(home, ".nimlab_env")) if p]


def _exec_files():
    from . import config
    return [os.path.join(config.PROJECT_DIR, n) for n in ("start.sh", "update.sh")]


def permission_problems():
    """[(path, want_mode)] for files whose mode is wrong."""
    out = []
    for p in _private_files():
        if os.path.exists(p) and stat.S_IMODE(os.stat(p).st_mode) & 0o077:
            out.append((p, 0o600))
    for p in _exec_files():
        if os.path.exists(p) and not os.access(p, os.X_OK):
            out.append((p, 0o755))
    return out


def permission_checks(ent=None):
    probs = permission_problems()
    if not probs:
        return [(True, "key files are private (600) and start.sh/update.sh can run")]
    return [("warn", f"{os.path.basename(p)} should be mode {oct(m)[2:]} -> doctor --fix sets it") for p, m in probs]


def endpoint_checks(ent=None):
    from . import endpoints
    eps = endpoints.all_endpoints()
    if not eps:
        return [(True, "no custom endpoints")]
    rows = []
    for e in eps:
        n = len(e.get("models", []))
        rows.append((True if n else "warn", f"custom endpoint {e['name']}: {n} model(s)" +
                     ("" if n else " -> Models > Custom endpoints > Import its models")))
    return rows


def service_checks(ent=None):
    from . import updater
    rec = updater.read_record()
    if not rec:
        return [(True, "no update has been run with ./update.sh yet")]
    res = rec.get("result", "?")
    good = res in ("healthy", "updated, no service", "stopped", "cleaned")
    return [(True if good else "warn", f"last ./update.sh: {res} (v{rec.get('version', '?')}, {rec.get('at', '?')})")]


def fallback_checks(ent=None):
    """v3.8.3: model fallbacks: what is set, and what happened in the last 24 h."""
    from . import fallback as FB
    cluster = getattr(ent, "cluster", None) or {}
    fs = FB.settings(cluster)
    if not fs["enabled"]:
        return [("warn", "Model fallbacks are off (routing_settings.fallback_enabled)")]
    out = []
    chain = ent.fallback_chain("persona", fs) if hasattr(ent, "fallback_chain") and ent.is_set("persona") else []
    if chain:
        out.append((True, "Persona fallbacks: " + " then ".join(f"{d['model']} ({k})" for k, d in chain)
                    + f"; cooldown {int(fs['cooldown'])} s"))
    else:
        out.append(("warn", "No fallback model for the persona: a 429 or 503 from its model fails the reply "
                            "-> set the Reasoning role, or add fallbacks in the roles menu (R, then F)"))
    n, last = FB.summary(24)
    if n:
        out.append(("warn", f"{n} fallback(s) in the last 24 h; last: {FB.describe_event(last)} at {last.get('at')}"))
    else:
        out.append((True, "No fallbacks in the last 24 h"))
    return out


SECTIONS = [("settings", "Settings", settings_checks), ("config", "Config files", config_checks),
            ("memory", "Long-term memory", memory_checks), ("identity", "Identity pin", identity_checks),
            ("prompts", "System prompts", prompt_checks), ("processes", "Processes and locks", process_checks),
            ("telegram", "Telegram", telegram_checks), ("scheduler", "Scheduler", scheduler_checks),
            ("endpoints", "Custom endpoints", endpoint_checks), ("permissions", "File permissions", permission_checks),
            ("update", "Last update", service_checks), ("platform", "Platform", platform_checks),
            ("fallbacks", "Model fallbacks", fallback_checks), ("mcp", "MCP tools", mcp_checks)]
QUICK = ("settings", "config", "identity", "processes", "telegram", "scheduler", "endpoints", "permissions", "update",
         "fallbacks")


def collect(ent=None, mcp=True, memory=True, only=None):
    """-> {"ok": bool, "summary": {...}, "checks": [records]}."""
    if ent is None:
        from .entity import Entity
        ent = Entity(log=lambda *a: None)
    checks = []
    for sid, title, fn in SECTIONS:
        if only and sid not in only:
            continue
        if (sid == "mcp" and not mcp) or (sid == "memory" and not memory):
            continue
        try:
            rows = fn(ent)
        except Exception as e:  # noqa: BLE001 - a check reports, it never crashes
            rows = [(False, f"check failed: {type(e).__name__}: {e}")]
        for i, (ok, msg) in enumerate(rows):
            head, _, fix = msg.partition(" -> ")
            status = "warn" if ok == "warn" else ("ok" if ok else "fail")
            checks.append({"section": sid, "title": title, "id": f"{sid}.{i}", "status": status,
                           "message": head, "fix": fix or None,
                           "repair": "doctor --fix" if "doctor --fix" in fix else None})
    n = {k: sum(1 for c in checks if c["status"] == k) for k in ("ok", "warn", "fail")}
    from . import __version__
    return {"ok": n["fail"] == 0, "version": __version__, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "summary": n, "repairs_available": len(planned_repairs()), "checks": checks}


def print_report(rep, out=print):
    last = None
    for c in rep["checks"]:
        if c["section"] != last:
            out(C.section(c["title"]))
            last = c["section"]
        msg = c["message"] + (C.dim(" -> ") + C.hint(c["fix"]) if c["fix"] and C.enabled() else
                              (" -> " + c["fix"] if c["fix"] else ""))
        tag = {"ok": C.ok("[ok]  "), "warn": C.warn("[!]   "), "fail": C.err("[!!]  ")}[c["status"]]
        out("  " + tag + msg)


def run(ent=None, out=print, mcp=True):
    rep = collect(ent, mcp=mcp)
    print_report(rep, out)
    return rep["ok"]


# ---------------------------------------------------------------------------
# doctor --fix
# ---------------------------------------------------------------------------
def planned_repairs(ent_cluster=None):
    """[(id, description, fn)] safe repairs that apply right now."""
    out = []
    for label, path, pid in stale_pid_files():
        out.append((f"stale:{label}", f"remove {label} (pid {pid} is not running)",
                    lambda path=path, pid=pid: (not _alive(pid)) and os.path.exists(path) and os.remove(path)))
    for path, mode in permission_problems():
        out.append((f"mode:{os.path.basename(path)}", f"set {os.path.basename(path)} to mode {oct(mode)[2:]}",
                    lambda path=path, mode=mode: os.chmod(path, mode)))
    try:
        from . import config, configlint
        raw = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        roles = raw.get("roles") or {}
        for key, v in roles.items():
            if isinstance(v, dict) and v.get("endpoint") and configlint.is_homepage(v["endpoint"]):
                out.append((f"endpoint:{key}", f"clear roles.{key}.endpoint ({v['endpoint']} is a homepage, "
                            "not an API URL); the role goes back to normal routing", _clear_role_endpoint(key)))
        vs = raw.get("voice_settings") or {}
        for k in configlint.SPEECH_URL_KEYS:
            u = vs.get(k)
            if u and (configlint.is_homepage(u) or not configlint.is_url(u)):
                out.append((f"voice:{k}", f"remove voice_settings.{k} ({u!r} cannot work); the default is used",
                            _clear_voice_key(k)))
    except Exception:  # noqa: BLE001 - an unreadable config is reported by config_checks
        pass
    return out


def _edit_cluster(fn):
    from . import config
    raw = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    fn(raw)
    config.save_json(config.CLUSTER_CONFIG, raw)


def _clear_role_endpoint(key):
    return lambda: _edit_cluster(lambda raw: (raw.get("roles") or {}).get(key, {}).pop("endpoint", None))


def _clear_voice_key(k):
    return lambda: _edit_cluster(lambda raw: (raw.get("voice_settings") or {}).pop(k, None))


def backup():
    """Copy the settings files to data/backups/doctor-<time>/ -> the folder."""
    from . import config, store
    d = os.path.join(store.data_dir(), "backups", "doctor-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(d, exist_ok=True)
    for p in (config.CLUSTER_CONFIG, getattr(config, "SYSTEM_PROMPTS", ""),
              os.path.join(store.data_dir(), "service.json"), os.path.join(store.data_dir(), "scheduler_jobs.json")):
        if p and os.path.exists(p):
            shutil.copy2(p, d)
    return d


def fix(out=print, ent=None, recheck=True):
    """Run the safe repairs. -> {"backup", "applied", "failed", "after"}."""
    todo = planned_repairs()
    res = {"backup": None, "applied": [], "failed": [], "after": None}
    if not todo:
        out("Nothing to repair: no stale pid files, wrong file modes or settings that can never work.")
    else:
        res["backup"] = backup()
        out(f"Backed up the settings to {res['backup']}")
        for rid, desc, fn in todo:
            try:
                fn()
                res["applied"].append({"id": rid, "what": desc})
                out("  " + C.ok("[fixed] ") + desc)
            except Exception as e:  # noqa: BLE001
                res["failed"].append({"id": rid, "what": desc, "error": str(e)})
                out("  " + C.err("[failed] ") + f"{desc}: {e}")
    if recheck:
        out("")
        out("Checking again:")
        res["after"] = collect(ent, mcp=False, memory=False, only=QUICK)
        print_report(res["after"], out)
    return res


def cmd_doctor(args):
    as_json = getattr(args, "json", False)
    if not as_json:
        from .servemenu import ensure_nvidia_key
        try:
            ensure_nvidia_key()
        except SystemExit:
            raise
        except Exception:  # noqa: BLE001 - the memory check can still run with a local embedder
            pass
    if getattr(args, "fix", False):
        res = fix(out=(lambda *a: None) if as_json else print)
        if as_json:
            print(json.dumps(res, indent=2, default=str))
        return 0 if not res["failed"] and (res["after"] or {}).get("ok", True) else 1
    quick = getattr(args, "quick", False)
    rep = collect(mcp=not getattr(args, "no_mcp", False) and not quick, memory=not quick,
                  only=QUICK if quick else None)
    if as_json:
        print(json.dumps(rep, indent=2))
        return 0 if rep["ok"] else 1
    print_report(rep)
    print(C.ok("All checks passed.") if rep["ok"] else C.warn("Some checks need attention (see [!!] above)."))
    if rep["repairs_available"]:
        print(f"{rep['repairs_available']} safe repair(s) available: nimlab doctor --fix (or Health menu > Repair)")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(cmd_doctor(None))
