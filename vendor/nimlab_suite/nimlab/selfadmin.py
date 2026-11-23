"""Self-administration: tools the testbed entity can call to look at and
change its own setup, from any client (terminal, the test server, the call
page, Telegram).

Who may use them
    admin      the local terminal (testbed chat), and server requests made
               with the endpoint's admin key (~/.config/nimlab/admin_key,
               `nimlab selfadmin admin-key`). The Telegram bot uses the admin
               key only for its owner.
    others     nothing by default; `self_admin.others_read: true` gives them
               the read-only tools.

Safety
    - Secrets are never returned: any field whose name looks like a key,
      token, password or secret is masked, and command output is scrubbed
      of the values of the known secrets.
    - Every change snapshots the config files first (data/selfadmin/
      snapshots); `self_undo` restores the last snapshot.
    - Risky actions (restart or stop the service, stopping or turning off
      the tunnel, deleting, turning auth off, shell and file edits) need a
      confirmation: the first call returns a code, the entity asks the user,
      and only a call in a LATER request with that code runs it.
    - Every admin action goes to data/selfadmin/audit.jsonl.
    - The shell and file-edit tools are off unless self_admin.shell is on,
      and only work inside the project folder.

Changes are written to the same files the CLI uses and the entity reloads
its config right away, so they apply live.
"""

import contextlib
import copy
import hmac
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import threading
import time

from . import config, store

SECRET_KEY_RX = re.compile(r"(api_?key|token|password|passwd|secret|credential|wallet_password|auth_value)", re.I)
NOT_SECRET = {"max_tokens", "max_tool_steps", "key_env", "token_count", "api_key_env", "tokens",
              "credentials_file", "auth_style", "header", "style"}
PENDING_TTL = 600
SNAP_KEEP = 30


def settings(cluster=None):
    c = config.load_cluster_config() if cluster is None else cluster
    sa = c.setdefault("self_admin", {})
    sa.setdefault("enabled", True)
    sa.setdefault("others_read", False)
    sa.setdefault("shell", False)
    sa.setdefault("fix_suggestions", True)   # offer a fix after a failure (admins only; applied after a yes)
    return sa


# ---------------------------------------------------------------------------
# identity of the current request (thread-local)
# ---------------------------------------------------------------------------
_local = threading.local()


class Identity:
    def __init__(self, admin=False, who="anonymous", source="api", request_id=None):
        self.admin, self.who, self.source = bool(admin), str(who)[:80], source
        self.request_id = request_id or secrets.token_hex(6)


def current():
    return getattr(_local, "ident", None) or Identity(False, "anonymous", "none")


@contextlib.contextmanager
def identity(admin=False, who="anonymous", source="api"):
    prev = getattr(_local, "ident", None)
    _local.ident = Identity(admin, who, source)
    try:
        yield _local.ident
    finally:
        _local.ident = prev


def active_box():
    return getattr(_local, "box", None)


@contextlib.contextmanager
def using_box(box):
    prev = getattr(_local, "box", None)
    _local.box = box
    try:
        yield box
    finally:
        _local.box = prev


class TaskScope:
    """v3.8.3 quill_task jobs: the MCP tools picked for this run.
    only=True offers just those (v3.8.4: memory_search only when listed); only=False offers every
    tool and names these as the ones to use. The MCP admin console still
    decides which tools exist: a picked tool the server no longer lists is
    simply not offered."""

    def __init__(self, names, only=True):
        self.names = [str(n).strip() for n in (names or []) if str(n).strip()]
        self.only = bool(only)

    def allows(self, name):
        return (not self.only) or name in self.names


def task_scope():
    return getattr(_local, "scope", None)


@contextlib.contextmanager
def task_tools(names, only=True):
    prev = getattr(_local, "scope", None)
    _local.scope = TaskScope(names, only)
    try:
        yield _local.scope
    finally:
        _local.scope = prev


def set_request(admin, who, source):
    """The server's auth check: who is asking, for this request's thread."""
    _local.ident = Identity(admin, who, source)


def clear_request():
    _local.ident = None


def set_local_admin():
    """The terminal testbed: the person at the keyboard owns the lab. Each
    call starts a new 'request' (the next chat turn)."""
    _local.ident = Identity(True, "terminal", "terminal")


# ---------------------------------------------------------------------------
# admin key (private file, 600)
# ---------------------------------------------------------------------------
def admin_key_path(env=None):
    from .tunnel import config_dir
    env = os.environ if env is None else env
    return env.get("NIMLAB_ADMIN_KEY_FILE") or os.path.join(config_dir(env), "admin_key")


def load_admin_key(env=None):
    try:
        with open(admin_key_path(env), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def new_admin_key(env=None):
    from .tunnel import write_private
    k = "nimlab-admin-" + secrets.token_urlsafe(24)
    write_private(admin_key_path(env), k + "\n")
    return k


def is_admin_key(given, env=None):
    k = load_admin_key(env)
    return bool(k and given) and hmac.compare_digest(given.encode(), k.encode())


# ---------------------------------------------------------------------------
# secrets: mask and scrub
# ---------------------------------------------------------------------------
def _mask(v):
    s = str(v)
    return "(empty)" if not s else ("***" + s[-4:] if len(s) > 8 else "***")


def masked(obj, key=None):
    if isinstance(obj, dict):
        return {k: masked(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [masked(v, key) for v in obj]
    if key and key not in NOT_SECRET and SECRET_KEY_RX.search(str(key)) and isinstance(obj, str) and obj:
        return _mask(obj)
    return obj


def known_secrets():
    out = []
    for name in ("NVIDIA_API_KEY", "NGC_API_KEY", "MCP_API_KEY", "TUNNEL_TOKEN", "NIMLAB_ORACLE_PASSWORD",
                 "TELEGRAM_BOT_TOKEN"):
        if os.environ.get(name):
            out.append(os.environ[name])
    try:
        from . import server as S
        out.append(S.load_settings().get("api_key") or "")
    except Exception:  # noqa: BLE001
        pass
    from . import tunnel
    out += [load_admin_key(), tunnel.load_token()]
    try:
        from . import telegram
        out.append(telegram.load_token())
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import mcpkey
        out.append(mcpkey.saved_key() or "")
    except Exception:  # noqa: BLE001
        pass
    try:
        with open(os.path.expanduser("~/.nimlab_env"), encoding="utf-8") as f:
            out += re.findall(r"=['\"]?([^'\"\s]{12,})", f.read())
    except OSError:
        pass
    return [s for s in out if s and len(s) >= 8]


def scrub(text, extra=()):
    text = str(text)
    for s in sorted(set(known_secrets()) | set(extra), key=len, reverse=True):
        text = text.replace(s, _mask(s))
    text = re.sub(r"nvapi-[A-Za-z0-9_\-]{20,}", lambda m: _mask(m.group(0)), text)
    return text


# ---------------------------------------------------------------------------
# snapshots, undo, audit
# ---------------------------------------------------------------------------
def _dir(*parts):
    d = os.path.join(store.data_dir(), "selfadmin", *parts)
    os.makedirs(d, exist_ok=True)
    return d


def tracked_files():
    from . import server as S
    return {"config_cluster.json": config.CLUSTER_CONFIG, "config_system_prompts.json": config.SYSTEM_PROMPTS,
            "server_settings.json": S.settings_path()}


def snapshot(label):
    snap = {"label": label, "at": config.timestamp(), "files": {}}
    for name, path in tracked_files().items():
        try:
            with open(path, encoding="utf-8") as f:
                snap["files"][name] = f.read()
        except OSError:
            snap["files"][name] = None
    d = _dir("snapshots")
    path = os.path.join(d, f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f)
    snaps = sorted(os.listdir(d))
    for old in snaps[:-SNAP_KEEP]:
        os.unlink(os.path.join(d, old))
    return path


def undo():
    d = _dir("snapshots")
    snaps = sorted(os.listdir(d))
    if not snaps:
        return None
    path = os.path.join(d, snaps[-1])
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    paths = tracked_files()
    for name, text in snap["files"].items():
        p = paths.get(name)
        if not p:
            continue
        if text is None:
            if os.path.exists(p):
                os.unlink(p)
        else:
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
    os.unlink(path)
    return snap


def audit(tool, args, ok, summary, ident=None):
    ident = ident or current()
    rec = {"at": config.timestamp(), "who": ident.who, "source": ident.source, "tool": tool,
           "args": json.loads(scrub(json.dumps(masked(args or {}), ensure_ascii=False))), "ok": bool(ok),
           "result": scrub(summary)[:500]}
    with open(os.path.join(_dir(), "audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def audit_tail(n=20):
    try:
        with open(os.path.join(_dir(), "audit.jsonl"), encoding="utf-8") as f:
            return [json.loads(x) for x in f.readlines()[-n:]]
    except (OSError, ValueError):
        return []


# ---------------------------------------------------------------------------
# confirmations: a code from one request, redeemed in a later one
# ---------------------------------------------------------------------------
_pending = {}


def _need_confirm(tool, args, what):
    ident = current()
    code = f"{secrets.randbelow(9000) + 1000}"
    _pending[code] = {"tool": tool, "args": {k: v for k, v in args.items() if k != "confirm_code"},
                      "who": ident.who, "request": ident.request_id, "at": time.time()}
    return (f"CONFIRMATION NEEDED, nothing was done yet. Ask the user: \"{what}. Reply yes to go ahead.\" "
            f"If they agree in their next message, call {tool} again with the same arguments and "
            f"confirm_code=\"{code}\". The code expires in 10 minutes.")


def _confirmed(tool, args):
    code = str(args.get("confirm_code") or "")
    p = _pending.get(code)
    if not p:
        return False, ""
    ident = current()
    if time.time() - p["at"] > PENDING_TTL:
        _pending.pop(code, None)
        return False, "That confirmation code expired; ask again."
    if p["tool"] != tool or p["who"] != ident.who or \
            p["args"] != {k: v for k, v in args.items() if k != "confirm_code"}:
        return False, "That confirmation code is for a different action."
    if p["request"] == ident.request_id:
        return False, ("The user has to confirm in a new message first: ask them, and call again after "
                       "they say yes.")
    _pending.pop(code, None)
    return True, ""


# fixes offered after a failure (nimlab.fixes): id -> the tool call, who it
# was offered to and in which request. Applied by self_apply_fix after the
# admin says yes in a later message.
_fixes = {}


def offer_fixes(fixes):
    """Register fixes for the current (admin) caller; -> their ids, or [] for
    a non-admin, when self-admin or fix suggestions are off."""
    ident = current()
    if not ident.admin or not fixes:
        return []
    sa = settings()
    if not sa.get("enabled", True) or not sa.get("fix_suggestions", True):
        return []
    now = time.time()
    for k in [k for k, v in _fixes.items() if now - v["at"] > PENDING_TTL]:
        _fixes.pop(k, None)
    ids = []
    for f in fixes:
        fid = f"fix{secrets.randbelow(9000) + 1000}"
        _fixes[fid] = {"tool": f["tool"], "args": dict(f["args"]), "what": f["what"], "who": ident.who,
                       "request": ident.request_id, "at": now}
        ids.append(fid)
    audit("offer_fix", {"fixes": [f["what"] for f in fixes]}, True, ", ".join(ids), ident)
    return ids


# ---------------------------------------------------------------------------
# the tools
# ---------------------------------------------------------------------------
def _schema(props=None, required=()):
    return {"type": "object", "properties": props or {}, "required": list(required), "additionalProperties": False}


S_STR = {"type": "string"}
CONFIRM = {"confirm_code": {"type": "string", "description": "only after the user confirmed"}}

READ_TOOLS = {
    "self_status": ("Your own setup at a glance: version, roles, memory, gRPC, MCP, server, tunnel, service, "
                    "Telegram, self-admin.", _schema()),
    "self_get_config": ("Read config_cluster.json (all sections, or one), secrets masked.",
                        _schema({"section": S_STR})),
    "self_get_roles": ("The 16 roles and the model or tool each uses.", _schema()),
    "self_get_prompts": ("System prompts (one role or all).", _schema({"role": S_STR})),
    "self_logs": ("Recent log lines: service, audit (admin actions), tunnel.",
                  _schema({"source": {"type": "string", "enum": ["service", "audit", "tunnel"]},
                           "lines": {"type": "integer"}}, ["source"])),
    "self_catalog": ("Search the model catalog (verified 200-OK and discovered models) by text.",
                     _schema({"query": S_STR, "verified_only": {"type": "boolean"}})),
}
WRITE_TOOLS = {
    "self_set_role": ("Set or swap the model a role uses (checked against the catalog).",
                      _schema({"role": S_STR, "model": S_STR}, ["role", "model"])),
    "self_set_setting": ("Change one setting in config_cluster.json: section (e.g. mcp_settings, voice_settings, "
                         "routing_settings, guard_settings, entity_settings), key, and a JSON value.",
                         _schema({"section": S_STR, "key": S_STR, "value": {}, **CONFIRM},
                                 ["section", "key", "value"])),
    "self_set_prompt": ("Replace a role's system prompt.", _schema({"role": S_STR, "text": S_STR}, ["role", "text"])),
    "self_memory_set": ("Change a long-term memory option (backend, scope, top_k, threshold, retention_days, "
                        "max_records, auto_store, auto_recall, save, dedupe, embed).",
                        _schema({"key": S_STR, "value": S_STR}, ["key", "value"])),
    "self_server_set": ("Change a test-server setting (port, lan, models, cors_origins, trace, agent_tool_calls).",
                        _schema({"key": S_STR, "value": {}, **CONFIRM}, ["key", "value"])),
    "self_run": ("Run a check or job: grpc_refresh, grpc_check, memory_test, mcp_test, serve_test, discover, "
                 "sweep_plan, sweep, roles_show.",
                 _schema({"action": {"type": "string", "enum": ["grpc_refresh", "grpc_check", "memory_test",
                                                                "mcp_test", "serve_test", "discover", "sweep_plan",
                                                                "sweep", "roles_show"]}}, ["action"])),
    "self_service": ("The background service: status, restart, stop, start.",
                     _schema({"action": {"type": "string", "enum": ["status", "start", "restart", "stop"]},
                              **CONFIRM}, ["action"])),
    "self_tunnel": ("The public tunnel: status, quick (random trycloudflare URL), off, auto_on, auto_off.",
                    _schema({"action": {"type": "string", "enum": ["status", "quick", "off", "auto_on",
                                                                   "auto_off"]}, **CONFIRM}, ["action"])),
    "self_jobs": ("Scheduler jobs (like Oracle DBMS_SCHEDULER): list, show, history, next, create, edit, enable, "
                  "disable, delete, run. Use when the owner asks to schedule something, e.g. 'check the tunnel "
                  "every 30 minutes' -> create name=tunnel-check, schedule='FREQ=MINUTELY;INTERVAL=30', "
                  "action_type=test, job_action='tunnel'. schedule: an Oracle calendar string (FREQ=DAILY;BYHOUR=7), "
                  "a 5-field cron or 'at YYYY-MM-DD HH:MM' (local time). action_type: quill_prompt (a prompt for "
                  "you), quill_task ({prompt, tools: [MCP tool names], only: true = only these tools / false = any, "
                  "require_tool: true = the run fails if no tool is called}; e.g. a 'free time' job), "
                  "nimlab_command, test (test names), mcp_tool ({tool, args}), shell, chain. result_to: "
                  "telegram, memory, log, none or mcp_tool:<tool>, optionally :only_on_failure or :only_if_notable. "
                  "The heartbeat is the job named 'heartbeat'. Delete needs confirmation.",
                  _schema({"action": {"type": "string", "enum": ["list", "show", "history", "next", "create",
                                                                 "edit", "enable", "disable", "delete", "run"]},
                           "name": S_STR, "schedule": S_STR, "action_type": S_STR, "job_action": {},
                           "description": S_STR, "result_to": {}, "changes": {"type": "object"}, **CONFIRM},
                          ["action"])),
    "self_heartbeat_actions": ("The heartbeat's suggested actions: list, show, add, edit, enable, disable, remove. "
                               "Each has name, instruction (what to do), condition (when it is worth doing), "
                               "priority (1 first), result_to (telegram, memory, log, none, mcp_tool:<tool>) and "
                               "an optional run ({type: test, action: 'service'}) to run directly.",
                               _schema({"action": {"type": "string", "enum": ["list", "show", "add", "edit",
                                                                              "enable", "disable", "remove"]},
                                        "name": S_STR, "instruction": S_STR, "condition": S_STR,
                                        "priority": {"type": "integer"}, "result_to": {}, "run": {},
                                        **CONFIRM}, ["action"])),
    "self_undo": ("Undo the last change made with these tools (restores the config snapshot).", _schema()),
    "self_apply_fix": ("Apply a fix you offered after a failure, only after the user said yes to it in a later "
                       "message. fix_id is the id given with the offer.", _schema({"fix_id": S_STR}, ["fix_id"])),
}
SHELL_TOOLS = {
    "self_shell": ("Run a shell command inside the project folder (60 s limit). Needs confirmation.",
                   _schema({"command": S_STR, **CONFIRM}, ["command"])),
    "self_edit_file": ("Replace text in a file inside the project folder. Needs confirmation.",
                       _schema({"path": S_STR, "old": S_STR, "new": S_STR, **CONFIRM}, ["path", "old", "new"])),
}
RISKY_SERVICE = {"restart", "stop"}
RISKY_TUNNEL = {"off", "auto_off"}
RISKY_SETTINGS = re.compile(r"(enabled|auth|confirm|allowed_tools|blocked_tools|guard|check_|self_admin|lan|cors|"
                            r"agent_tool_calls)", re.I)
BLOCKED_SECTIONS = {"self_admin"}   # changed only in setup / CLI, never by the entity itself


def has_tools(entity):
    sa = settings(entity.cluster)
    ident = current()
    return bool(sa.get("enabled")) and (ident.admin or bool(sa.get("others_read")))


def tool_defs(admin, sa):
    defs = {}
    if admin or sa.get("others_read"):
        defs.update(READ_TOOLS)
    if admin:
        defs.update(WRITE_TOOLS)
        if sa.get("shell"):
            defs.update(SHELL_TOOLS)
    return [{"name": n, "description": d, "inputSchema": s} for n, (d, s) in defs.items()]


def _text(t, err=False):
    return {"content": [{"type": "text", "text": scrub(t)}], "isError": bool(err)}


def _run_cli(argv, timeout=300):
    root = config.PROJECT_DIR
    env = {k: v for k, v in os.environ.items()}
    env["NIMLAB_COLOR"] = "0"
    try:
        r = subprocess.run([sys.executable, "-m", "nimlab", *argv], cwd=root, capture_output=True, text=True,
                           timeout=timeout, env=env, stdin=subprocess.DEVNULL)
        out = (r.stdout + ("\n" + r.stderr if r.stderr.strip() else "")).strip()
        return r.returncode == 0, out[-6000:]
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout} s"


RUN_MAP = {"grpc_refresh": ["grpc", "refresh"], "grpc_check": ["grpc", "check"], "memory_test": ["memory", "test"],
           "mcp_test": ["mcp", "test"], "serve_test": ["serve", "test"], "discover": ["discover"],
           "sweep_plan": ["sweep", "--plan-only"], "sweep": ["sweep"], "roles_show": ["roles", "show"]}


def check_role(key, model):
    from . import roles as R, rolemenu
    key = R.LEGACY_MAP.get(key, key)
    if key not in R.BY_KEY:
        return False, f"Unknown role '{key}'. Roles: {', '.join(d.key for d in R.ROLE_DEFS)}"
    verified, discovered = rolemenu.model_lists()
    if model not in discovered and model not in verified:
        close = [m for m in discovered if model.lower() in m.lower()][:8]
        return False, f"'{model}' is not in the catalog." + (f" Did you mean: {', '.join(close)}" if close
                                                             else " Run discover first.")
    return True, ""


def set_role(key, model):
    """Set a role to a catalog model in config_cluster.json; (ok, message)."""
    from . import roles as R, rolemenu
    ok, why = check_role(key, model)
    if not ok:
        return False, why
    key = R.LEGACY_MAP.get(key, key)
    verified, _ = rolemenu.model_lists()
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    old = R.describe(cfg.get("roles", {}).get(key))
    sp = R.normalize(cfg.setdefault("roles", {}).get(key), key)
    sp.update(backend=R.MODEL, model=model)
    sp.pop("tool", None)
    sp.pop("arg_map", None)
    cfg["roles"][key] = sp
    config.save_json(config.CLUSTER_CONFIG, cfg)
    note = "" if model in verified else " Note: it is discovered but not 200-verified yet."
    return True, f"Changed role {key}: {old} -> {model}.{note}"


class ToolBox:
    """MCP tools plus the self-admin tools, with the interface run_tool_loop
    expects (tools, tool(name), call_tool(name, args))."""

    def __init__(self, entity, mcp=None, allowed=None):
        self.entity, self.mcp = entity, mcp
        self.allowed = list(allowed or [])
        self.sa = settings(entity.cluster)
        ident = current()
        self.admin_defs = tool_defs(ident.admin, self.sa) if self.sa.get("enabled") else []
        self.scope = task_scope()
        if self.scope is not None and self.scope.only:
            self.admin_defs = []    # "only these tools": no self-admin tools either
        self.admin_names = {t["name"] for t in self.admin_defs}
        # every tool the server advertised (for clear refusals) and the ones
        # the policy lets the model see (v3.7.1: blocked tools are never shown)
        self.all_tools = list((mcp.tools if mcp else []) or []) + self.admin_defs
        pol = getattr(entity, "policy", None)
        pol = pol() if callable(pol) else None
        mcp_tools = list((mcp.tools if mcp else []) or [])
        if pol is not None and hasattr(pol, "why_blocked"):
            mcp_tools = [t for t in mcp_tools if pol.why_blocked(t) is None]
        if self.scope is not None and self.scope.only:
            mcp_tools = [t for t in mcp_tools if t.get("name") in self.scope.names]
        builtin = list(getattr(entity, "builtin_tools", lambda: [])())
        if self.scope is not None and self.scope.only:
            # v3.8.4: "only these tools" means only these: memory_search too, unless the job lists it
            builtin = [t for t in builtin if t.get("name") in self.scope.names]
        self.builtin_names = {t["name"] for t in builtin}
        self.tools = mcp_tools + builtin + self.admin_defs
        self.offered_names = {t.get("name") for t in self.tools}

    def tool(self, name):
        return next((t for t in self.tools + self.all_tools if t.get("name") == name), None)

    def scoped(self):
        return self.scope is not None and self.scope.only

    def offers(self, name):
        """v3.8.4: may this call run here? In a scheduled job with a tool list,
        only the job's own tools (and load_tools) may; elsewhere, unchanged."""
        if not self.scoped():
            return True
        from .mcp import LOAD_TOOLS
        return name in self.offered_names or name == LOAD_TOOLS

    def offered(self, name):
        """The definition load_tools may hand out: in a scoped job only the
        job's own tools; elsewhere, as tool()."""
        if not self.scoped():
            return self.tool(name)
        return next((t for t in self.tools if t.get("name") == name), None)

    def not_offered_reason(self, name):
        names = sorted(n for n in self.offered_names if n)
        return f"{name} is not one of this job's tools. Use one of: {', '.join(names) or '(none)'}"

    def call_tool(self, name, arguments):
        ident = current()
        args = dict(arguments or {})
        if self.scoped() and not self.offers(name):
            return _text(self.not_offered_reason(name) + ".", True)
        run_builtin = getattr(self.entity, "run_builtin_tool", None)
        if callable(run_builtin) and name in getattr(self, "builtin_names", ()):
            return run_builtin(name, args)
        if name not in self.admin_names:
            if name.startswith("self_") and (name in READ_TOOLS or name in WRITE_TOOLS or name in SHELL_TOOLS):
                # a self-admin tool this caller was not given: refuse, never pass it on to MCP
                if name in WRITE_TOOLS or name in SHELL_TOOLS:
                    audit(name, args, False, "refused: not an admin (or the tool is off)", ident)
                return _text(f"{name} is only for the testbed's admins (or it is turned off).", True)
            if self.mcp is None:
                return _text(f"No tool named {name}.", True)
            if self.scope is not None and not self.scope.allows(name):
                return _text(f"{name} is not one of this job's tools. Use one of: "
                             f"{', '.join(self.scope.names) or '(none)'}.", True)
            try:
                return self.mcp.call_tool(name, arguments)
            except Exception as e:  # noqa: BLE001 - MCP down: report it accurately, with a fix for admins
                mark = getattr(self.entity, "mark_tools_stale", None)
                if callable(mark):
                    mark()
                from .entity import fix_offer
                cl = getattr(self.entity, "cluster", None) or {}
                return _text(f"The MCP tool {name} failed: {e}. Answer the user's message without it and say "
                             f"briefly that the MCP tool call failed. " + fix_offer("mcp", name, str(e), 0.0, cl),
                             True)
        if (name in WRITE_TOOLS or name in SHELL_TOOLS) and not ident.admin:
            # the box was built for an admin but this call runs as someone else
            audit(name, args, False, "refused: not an admin", ident)
            return _text(f"{name} is only for the testbed's admins.", True)
        try:
            res = getattr(self, "_t_" + name[5:])(args)
        except Exception as e:  # noqa: BLE001 - a tool error is a tool result, never a crash
            res = _text(f"{name} failed: {type(e).__name__}: {e}", True)
        text = res["content"][0]["text"]
        if name in WRITE_TOOLS or name in SHELL_TOOLS:
            audit(name, args, not res.get("isError"), text, ident)
        return res

    # -- helpers --------------------------------------------------------
    def _changed(self, label, fn):
        """Snapshot, apply fn() -> message, reload the entity."""
        snapshot(label)
        msg = fn()
        try:
            self.entity.reload()
        except Exception as e:  # noqa: BLE001
            msg += f" (saved; live reload failed: {e}; restart to apply)"
        return _text(msg + " Say 'undo the last change' to roll it back.")

    def _cluster_file(self):
        return config.load_json(config.CLUSTER_CONFIG, {}) or {}

    # -- read -----------------------------------------------------------
    def _t_status(self, a):
        from . import __version__, tunnel
        from . import roles as R
        c = self.entity.cluster
        n_set = sum(1 for d in R.ROLE_DEFS if R.is_set(c.get("roles", {}).get(d.key)))
        lines = [f"NIM test lab v{__version__}", f"roles: {n_set}/{len(R.ROLE_DEFS)} set"]
        try:
            from . import memmenu
            lines.append("memory: " + memmenu.short_status(c.get("memory_settings", {})))
        except Exception:  # noqa: BLE001
            pass
        m = c.get("mcp_settings", {})
        lines.append(f"mcp: tools {'on' if m.get('enabled') else 'off'}, url {m.get('url') or 'not set'}")
        try:
            from . import server as S
            s = S.load_settings()
            t = tunnel.settings_of(s)
            lines.append(f"server: port {s.get('port')}, lan {'on' if s.get('lan') else 'off'}")
            lines.append(f"tunnel: mode {t['mode']}, auto {'on' if t['auto_start'] else 'off'}; "
                         f"{tunnel.brief() or 'not running'}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"server: ? ({e})")
        try:
            from . import service
            lines.append("service: " + service.brief())
        except Exception:  # noqa: BLE001
            pass
        try:
            from . import telegram
            lines.append("telegram: " + telegram.brief())
        except Exception:  # noqa: BLE001
            pass
        try:
            from . import nvcf_grpc
            rows = nvcf_grpc.rows()
            lines.append(f"grpc: {sum(1 for r in rows if r.get('function_id'))}/{len(rows)} models have an ID")
        except Exception:  # noqa: BLE001
            pass
        lines.append(f"self-admin: on, shell {'on' if self.sa.get('shell') else 'off'}")
        return _text("\n".join(lines))

    def _t_get_config(self, a):
        c = masked(self._cluster_file())
        sec = a.get("section")
        if sec:
            if sec not in c:
                return _text(f"No section '{sec}'. Sections: {', '.join(sorted(c))}", True)
            c = {sec: c[sec]}
        return _text(json.dumps(c, indent=1, ensure_ascii=False)[:7000])

    def _t_get_roles(self, a):
        from . import roles as R
        roles = self.entity.cluster.get("roles", {})
        return _text("\n".join(f"{d.key}: {R.describe(roles.get(d.key))}" for d in R.ROLE_DEFS))

    def _t_get_prompts(self, a):
        p = config.load_prompts()
        r = a.get("role")
        if r:
            return _text(p.get(r) or f"No prompt for '{r}'. Roles: {', '.join(sorted(p))}", not p.get(r))
        return _text(json.dumps(p, indent=1, ensure_ascii=False)[:7000])

    def _t_logs(self, a):
        n = max(1, min(200, int(a.get("lines") or 40)))
        src = a.get("source")
        if src == "audit":
            return _text("\n".join(json.dumps(r, ensure_ascii=False) for r in audit_tail(n)) or "(no admin actions)")
        if src == "tunnel":
            from . import tunnel
            return _text(json.dumps(tunnel.read_status(), indent=1))
        from . import service
        return _text(service.log_tail(n) or "(no service log yet)")

    def _t_catalog(self, a):
        from . import rolemenu
        verified, discovered = rolemenu.model_lists()
        pool = verified if a.get("verified_only") else discovered
        q = (a.get("query") or "").lower()
        hits = [m for m in pool if q in m.lower()][:60]
        vs = set(verified)
        return _text("\n".join(f"{m}{'  [verified]' if m in vs else ''}" for m in hits) or "no match")

    # -- write ----------------------------------------------------------
    def _t_apply_fix(self, a):
        fid = str(a.get("fix_id") or "").strip()
        f = _fixes.get(fid)
        ident = current()
        if not f:
            return _text("No such fix offer (it may have expired or been used). Nothing was changed.", True)
        if time.time() - f["at"] > PENDING_TTL:
            _fixes.pop(fid, None)
            return _text("That fix offer expired; nothing was changed.", True)
        if f["who"] != ident.who:
            return _text("That fix was offered to someone else; nothing was changed.", True)
        if f["request"] == ident.request_id:
            return _text("Ask the user first: apply the fix only after they say yes in their next message.", True)
        _fixes.pop(fid, None)
        args = dict(f["args"])
        tool = f["tool"]
        if tool in ("self_set_setting", "self_server_set", "self_service", "self_tunnel"):
            # the user's yes to this offer is the confirmation for a risky setting
            code = f"fx{secrets.token_hex(4)}"
            _pending[code] = {"tool": tool, "args": dict(args), "who": ident.who, "request": f["request"],
                              "at": time.time()}
            args["confirm_code"] = code
        res = getattr(self, "_t_" + tool[5:])(args)
        if not res.get("isError"):
            res = _text(f"Applied: {f['what']}. " + res["content"][0]["text"])
            if "undo" not in res["content"][0]["text"].lower():
                res["content"][0]["text"] += " Say 'undo the last change' to roll it back."
        return res

    def _t_set_role(self, a):
        key = a["role"].strip()
        ok, why = check_role(key, a["model"].strip())
        if not ok:
            return _text(why, True)

        def apply():
            return set_role(key, a["model"].strip())[1]
        return self._changed(f"set role {key}", apply)

    def _t_set_setting(self, a):
        sec, key, val = a["section"], a["key"], a["value"]
        if sec in BLOCKED_SECTIONS:
            return _text("Self-admin settings can only be changed in setup or the CLI, not by me.", True)
        if sec == "roles":
            return _text("Use self_set_role for roles.", True)
        if SECRET_KEY_RX.search(key) and key not in NOT_SECRET:
            return _text("Secrets are not set through chat; use the setup wizard or the CLI.", True)
        cfg = self._cluster_file()
        if sec not in cfg or not isinstance(cfg[sec], dict):
            return _text(f"No settings section '{sec}'. Sections: "
                         f"{', '.join(k for k, v in cfg.items() if isinstance(v, dict))}", True)
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except ValueError:
                pass
        old = cfg[sec].get(key, "(unset)")
        if RISKY_SETTINGS.search(f"{sec}.{key}"):
            ok, why = _confirmed("self_set_setting", a)
            if not ok:
                return _text(why or _need_confirm("self_set_setting", a, f"Change {sec}.{key} from "
                                                  f"{json.dumps(old)} to {json.dumps(val)}"), bool(why))

        def apply():
            c2 = self._cluster_file()
            c2[sec][key] = val
            config.save_json(config.CLUSTER_CONFIG, c2)
            return f"Changed {sec}.{key}: {json.dumps(old)} -> {json.dumps(val)}."
        return self._changed(f"set {sec}.{key}", apply)

    def _t_set_prompt(self, a):
        role, text = a["role"], a["text"]
        p = config.load_prompts()
        if role not in p:
            return _text(f"No prompt '{role}'. Prompts: {', '.join(sorted(p))}", True)
        old_len = len(p.get(role) or "")

        def apply():
            p2 = config.load_json(config.SYSTEM_PROMPTS, {}) or {}
            p2[role] = text
            config.save_json(config.SYSTEM_PROMPTS, p2)
            return f"Replaced the {role} prompt ({old_len} -> {len(text)} characters)."
        return self._changed(f"set prompt {role}", apply)

    def _t_memory_set(self, a):
        from . import memmenu
        key, val = a["key"], str(a["value"])
        if key in ("backend", "use"):
            argv = ["memory", "use", val]
        elif key == "embed":
            argv = ["memory", "embed", *shlex.split(val)]
        else:
            argv = ["memory", "set", key, val]
        snapshot(f"memory {key}")
        ok, out = _run_cli(argv, 60)
        try:
            self.entity.reload()
        except Exception:  # noqa: BLE001
            pass
        st = memmenu.short_status(config.load_cluster_config().get("memory_settings", {}))
        return _text((f"Memory {key} set to {val}. Now: {st}. " if ok else f"Not changed: ") + out[-1500:], not ok)

    def _t_server_set(self, a):
        from . import server as S
        key, val = a["key"], a["value"]
        if key in ("api_key", "tunnel") or SECRET_KEY_RX.search(key):
            return _text("Keys and the tunnel are not set this way (use self_tunnel or the CLI).", True)
        s = S.load_settings()
        if key not in s:
            return _text(f"No server setting '{key}'. Settings: {', '.join(k for k in s if k != 'api_key')}", True)
        old = s[key]
        if key in ("lan", "cors_origins", "agent_tool_calls", "port"):
            ok, why = _confirmed("self_server_set", a)
            if not ok:
                return _text(why or _need_confirm("self_server_set", a, f"Change the server's {key} from "
                                                  f"{json.dumps(old)} to {json.dumps(val)}"), bool(why))

        def apply():
            s2 = S.load_settings()
            s2[key] = val
            S.save_settings(s2)
            return f"Changed server {key}: {json.dumps(old)} -> {json.dumps(val)} (applies when the server restarts)."
        return self._changed(f"server {key}", apply)

    def _t_run(self, a):
        act = a["action"]
        ok, out = _run_cli(RUN_MAP[act], 900 if act == "sweep" else 300)
        return _text(f"{act}: {'done' if ok else 'failed'}\n{out}", not ok)

    def _t_service(self, a):
        act = a["action"]
        if act in RISKY_SERVICE:
            ok, why = _confirmed("self_service", a)
            if not ok:
                return _text(why or _need_confirm("self_service", a, f"{act.capitalize()} the background service "
                                                  "(the endpoint and this chat drop for a moment)"), bool(why))
        if act == "restart":
            # answer first, then restart: the restart ends this very process
            threading.Timer(2.0, lambda: _run_cli(["service", "restart"], 60)).start()
            return _text("Restarting the service in 2 seconds. I'll be back in a few seconds.")
        ok, out = _run_cli(["service", act], 60)
        return _text(out or act, not ok)

    def _t_tunnel(self, a):
        act = a["action"]
        if act in RISKY_TUNNEL:
            ok, why = _confirmed("self_tunnel", a)
            if not ok:
                return _text(why or _need_confirm("self_tunnel", a, "Turn the public tunnel off (the public URL "
                                                  "stops working after the next restart)"), bool(why))
        argv = {"status": ["serve", "tunnel", "status"], "quick": ["serve", "tunnel", "quick"],
                "off": ["serve", "tunnel", "off"], "auto_on": ["serve", "tunnel", "auto", "on"],
                "auto_off": ["serve", "tunnel", "auto", "off"]}[act]
        if act != "status":
            snapshot(f"tunnel {act}")
        ok, out = _run_cli(argv, 60)
        return _text(out, not ok)

    # -- 3.8.0: scheduler jobs and suggested actions ----------------------
    def _sched_guard(self, act, read):
        """Quill changes jobs only when someone asked: a scheduled turn (the
        heartbeat, a quill_prompt job) may read them but not change them."""
        ident = current()
        if act in read or ident.source != "scheduler":
            return None
        return _text("Jobs and suggested actions are changed only when the owner asks, not from a scheduled "
                     "run. Nothing was changed; mention it in your report instead.", True)

    def _t_jobs(self, a):
        from . import jobscli, scheduler as SC, schedule as S
        act = a["action"]
        no = self._sched_guard(act, ("list", "show", "history", "next"))
        if no:
            return no
        ident = current()
        who, src = f"quill (asked by {ident.who})", ident.source
        name = str(a.get("name") or "").strip()
        try:
            S.set_timezone(SC.settings().get("timezone") or "")
        except S.ScheduleError:
            pass
        try:
            if act == "list":
                jobs = SC.load_jobs()
                return _text("\n".join(jobscli.job_line(jobs[n]).strip() for n in sorted(jobs)) + "\n"
                             + SC.status_line())
            if not name:
                return _text("Say which job (name).", True)
            if act == "show":
                return _text("\n".join(jobscli.show_lines(SC.get_job(name))))
            if act == "history":
                return _text("\n".join(jobscli.run_line(r).strip() for r in SC.history(name, 10)) or "no runs yet")
            if act == "next":
                return _text(", ".join(S.fmt(t) for t in SC.next_runs(name, 5)) or "no runs ahead")
            if act == "create":
                spec = dict(a.get("changes") or {})
                spec.update({k: v for k, v in (("name", name), ("schedule", a.get("schedule")),
                                               ("action_type", a.get("action_type") or "quill_prompt"),
                                               ("action", a.get("job_action")), ("description", a.get("description")),
                                               ("result_to", a.get("result_to"))) if v not in (None, "")})
                spec["created_by"] = who
                j = SC.create_job(spec, who=who, source=src)
                return _text(f"Created job {name}: {S.describe(j['schedule'])}, {j['action_type']}; result to "
                             f"{__import__('nimlab.routing', fromlist=['x']).describe(j['result_to'])}; next run "
                             f"{S.fmt(j['state'].get('next_run'), True)}.")
            if act == "edit":
                ch = dict(a.get("changes") or {})
                for k, f in (("schedule", "schedule"), ("action_type", "action_type"), ("job_action", "action"),
                             ("description", "description"), ("result_to", "result_to")):
                    if a.get(k) not in (None, ""):
                        ch[f] = a[k]
                j = SC.update_job(name, ch, who=who, source=src)
                return _text(f"Changed {name} ({', '.join(ch)}); next run {S.fmt(j['state'].get('next_run'), True)}.")
            if act in ("enable", "disable"):
                j = SC.set_enabled(name, act == "enable", who=who, source=src)
                return _text(f"{name} {act}d" + (f"; next run {S.fmt(j['state'].get('next_run'), True)}."
                                                 if j.get("enabled") else "."))
            if act == "delete":
                ok, why = _confirmed("self_jobs", a)
                if not ok:
                    return _text(why or _need_confirm("self_jobs", a, f"Delete the job {name} (its history stays)"),
                                 bool(why))
                SC.delete_job(name, who=who, source=src)
                return _text(f"Deleted job {name}.")
            if act == "run":
                SC.audit("run", "job", name, None, {"manual": True}, who, src)
                r = SC.Scheduler(log=lambda *x: None).run_now(name)
                return _text(f"{name}: {(r or {}).get('status')}\n{(r or {}).get('output') or ''}"[:3000],
                             not r or r.get("status") != "SUCCEEDED")
        except SC.JobError as e:
            return _text(str(e), True)
        return _text(f"unknown action {act}", True)

    def _t_heartbeat_actions(self, a):
        from . import heartbeat as HB, jobscli, scheduler as SC
        act = a["action"]
        no = self._sched_guard(act, ("list", "show"))
        if no:
            return no
        ident = current()
        who, src = f"quill (asked by {ident.who})", ident.source
        name = str(a.get("name") or "").strip()
        fields = {k: a[k] for k in ("instruction", "condition", "priority", "result_to", "run")
                  if a.get(k) not in (None, "")}
        try:
            if act == "list":
                return _text("\n".join(jobscli.action_line(x).strip() for x in HB.load_actions()) or "none")
            if not name:
                return _text("Say which suggested action (name).", True)
            if act == "show":
                return _text(json.dumps(HB.get_action(name), ensure_ascii=False, default=str))
            if act == "add":
                x = HB.add_action(dict(fields, name=name), who=who, source=src)
                return _text("Added: " + jobscli.action_line(x).strip())
            if act in ("enable", "disable"):
                fields = {"enabled": act == "enable"}
            if act in ("edit", "enable", "disable"):
                x = HB.edit_action(name, fields, who=who, source=src)
                return _text("Changed: " + jobscli.action_line(x).strip())
            if act == "remove":
                ok, why = _confirmed("self_heartbeat_actions", a)
                if not ok:
                    return _text(why or _need_confirm("self_heartbeat_actions", a,
                                                      f"Remove the suggested action {name}"), bool(why))
                HB.remove_action(name, who=who, source=src)
                return _text(f"Removed {name}.")
        except SC.JobError as e:
            return _text(str(e), True)
        return _text(f"unknown action {act}", True)

    def _t_undo(self, a):
        snap = undo()
        if not snap:
            return _text("Nothing to undo.")
        try:
            self.entity.reload()
        except Exception:  # noqa: BLE001
            pass
        return _text(f"Undid: {snap['label']} (from {snap['at']}). The config is back as it was before it.")

    # -- shell (off by default) -----------------------------------------
    def _inside(self, path):
        root = os.path.realpath(config.PROJECT_DIR)
        p = os.path.realpath(os.path.join(root, path))
        return p if (p == root or p.startswith(root + os.sep)) else None

    def _t_shell(self, a):
        cmd = a["command"]
        bad = re.search(r"(^|[\s;|&(<>='\"])(~|/|\.\.)|\$HOME|\$\{?HOME|\.config|\.nimlab_env|\bsudo\b|"
                        r"\bcurl\b|\bwget\b|\bssh\b|\benv\b|\bprintenv\b|/proc", cmd)
        if bad:
            return _text("Refused: the shell tool only works inside the project folder with relative paths "
                         "(no absolute paths, .., ~, network tools or environment dumps).", True)
        ok, why = _confirmed("self_shell", a)
        if not ok:
            return _text(why or _need_confirm("self_shell", a, f"Run this command in the lab folder: {cmd}"),
                         bool(why))
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": config.PROJECT_DIR, "LANG": "C.UTF-8",
               "NIMLAB_COLOR": "0"}
        try:
            r = subprocess.run(["bash", "-c", cmd], cwd=config.PROJECT_DIR, capture_output=True, text=True,
                               timeout=60, env=env, stdin=subprocess.DEVNULL)
            out = (r.stdout + r.stderr)[-6000:]
            return _text(f"exit {r.returncode}\n{out}", r.returncode != 0)
        except subprocess.TimeoutExpired:
            return _text("timed out after 60 s", True)

    def _t_edit_file(self, a):
        p = self._inside(a["path"])
        if not p or "/.git/" in p or os.path.basename(p).startswith(".nimlab"):
            return _text("Refused: only files inside the project folder.", True)
        if not os.path.isfile(p):
            return _text(f"No file {a['path']}.", True)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        n = text.count(a["old"])
        if n != 1:
            return _text(f"The old text appears {n} times; it must appear exactly once.", True)
        ok, why = _confirmed("self_edit_file", a)
        if not ok:
            return _text(why or _need_confirm("self_edit_file", a, f"Edit {a['path']} "
                                              f"({len(a['old'])} characters replaced by {len(a['new'])})"), bool(why))
        bak = os.path.join(_dir("file_backups"), time.strftime("%Y%m%d-%H%M%S-") + os.path.basename(p))
        shutil.copy2(p, bak)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text.replace(a["old"], a["new"], 1))
        return _text(f"Edited {a['path']}. Backup: {os.path.relpath(bak, config.PROJECT_DIR)}. Code changes "
                     "apply after a restart.")


class Policy:
    """Self-admin tools are checked inside the ToolBox; MCP tools keep the
    MCP policy (every exposed tool, optional local overrides and confirmation)."""

    def __init__(self, base, box):
        self.base, self.box = base, box

    def approve(self, call, tool=None):
        if call.name in self.box.admin_names or call.name in getattr(self.box, "builtin_names", ()):
            return True, ""   # self-admin tools check themselves; built-in tools run in-process, read-only
        return self.base.approve(call, tool)


def prompt_note(admin):
    if not admin:
        return ""
    return ("\n\n[SELF-ADMIN] You can inspect and change your own setup with the self_* tools. Say exactly "
            "what you changed (old -> new). For actions that answer CONFIRMATION NEEDED, ask the user and "
            "wait for their yes in a new message. Never reveal keys, tokens or passwords.")


def cmd_selfadmin(args):
    """nimlab selfadmin status|on|off|shell on|off|others-read on|off|fixes on|off|admin-key|undo|audit"""
    v = list(args.values or [])
    act = args.action
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    sa = settings(cfg)
    if act == "status":
        print(f"self-admin  : {'on' if sa['enabled'] else 'off'}")
        print(f"shell/edit  : {'on' if sa['shell'] else 'off'} (project folder only, confirmation each time)")
        print(f"others read : {'on' if sa['others_read'] else 'off'}")
        print(f"fix offers  : {'on' if sa.get('fix_suggestions', True) else 'off'} (after a failure, offer a fix; "
              "applied only after an admin says yes)")
        k = load_admin_key()
        print(f"admin key   : {_mask(k) if k else 'not made (nimlab selfadmin admin-key)'}")
        print(f"audit log   : {os.path.join(_dir(), 'audit.jsonl')} ({len(audit_tail(10000))} entries)")
        print(f"snapshots   : {len(os.listdir(_dir('snapshots')))}")
        return 0
    if act in ("on", "off"):
        sa["enabled"] = act == "on"
    elif act in ("shell", "others-read", "fixes"):
        if not v or v[0] not in ("on", "off"):
            print(f"usage: selfadmin {act} on|off")
            return 2
        sa[{"shell": "shell", "others-read": "others_read", "fixes": "fix_suggestions"}[act]] = v[0] == "on"
    elif act == "admin-key":
        k = new_admin_key()
        print(f"New admin key saved to {admin_key_path()} (mode 600). Shown once:")
        print(k)
        print("Requests with this key (instead of the normal API key) may use the self-admin tools.")
        return 0
    elif act == "undo":
        snap = undo()
        print(f"Undid: {snap['label']} ({snap['at']})" if snap else "Nothing to undo.")
        return 0
    elif act == "audit":
        for r in audit_tail(int(v[0]) if v and v[0].isdigit() else 20):
            print(f"{r['at']}  {r['who']:<12} {r['tool']:<18} {'ok ' if r['ok'] else 'ERR'} {r['result'][:80]}")
        return 0
    cfg["self_admin"] = sa
    config.save_json(config.CLUSTER_CONFIG, cfg)
    print(f"[ok] self-admin {'on' if sa['enabled'] else 'off'}, shell {'on' if sa['shell'] else 'off'}, "
          f"others read {'on' if sa['others_read'] else 'off'}")
    return 0
