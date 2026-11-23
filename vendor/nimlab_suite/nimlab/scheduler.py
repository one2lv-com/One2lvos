"""The Nim Lab scheduler (v3.8.0): jobs modeled on Oracle DBMS_SCHEDULER.

A job is a named, scheduled action with a run history:

  name, description          unique name (letters, digits, - _ .), a note
  schedule                   calendar string, 5-field cron or 'at <time>'
                             (see nimlab.schedule)
  action_type, action        quill_prompt | nimlab_command | test | mcp_tool |
                             shell | chain | heartbeat (the built-in job)
  enabled                    a disabled job keeps its history and its slot
  start_date, end_date       local times; nothing runs outside them
  max_runs, max_failures     stop (disable) after this many runs / failures
                             in a row; 0 = no limit
  retry_count, retry_backoff_sec   a failed run is retried after backoff,
                             doubling each time (30 s, 60 s, 120 s ...)
  timeout_sec                a run that takes longer is TIMED_OUT
  max_concurrent, overlap    how many runs of this job at once (default 1);
                             overlap skip (default) records a SKIPPED run,
                             queue runs it as soon as the current one ends
  catchup                    after downtime: one (default) runs once for all
                             missed times, none skips them, all runs each one
                             (capped by scheduler_settings.catchup_max)
  result_to                  where the result goes: {dest, when, tool, args,
                             escalate_on_failure}; see nimlab.routing
  owner, created_by          who owns it and who made it (cli, quill, setup)

Files (data/scheduler/): jobs.json (definitions + state), runs.jsonl (run
history, pruned by age and count), audit.jsonl (every change, with the
before and after), results.log (results routed to log), scheduler.lock
(held by the one running scheduler).

Exactly one scheduler runs: `nimlab scheduler run` takes an exclusive lock
on scheduler.lock and exits with code 75 (the service waits and checks
again) when another copy holds it. A run marks itself in jobs.json before it
starts, so a second process could not start the same run either.
"""

import contextlib
import hashlib
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import threading
import time

from . import config
from . import schedule as S

try:
    import fcntl
except ImportError:  # pragma: no cover - not on Linux/Termux
    fcntl = None

ACTION_TYPES = ("quill_prompt", "quill_task", "nimlab_command", "test", "mcp_tool", "shell", "chain", "heartbeat")
USER_ACTION_TYPES = ACTION_TYPES[:-1]
OVERLAP = ("skip", "queue")
CATCHUP = ("one", "none", "all")
STATUSES = ("SUCCEEDED", "FAILED", "TIMED_OUT", "SKIPPED", "MISSED")
NAME_RX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,59}$")
EXIT_WAIT = 75
EXIT_CONFIG = 78
HEARTBEAT = "heartbeat"
# commands a job may never run: they would stop the scheduler itself or wipe the lab
DENY_COMMANDS = (("service", "stop"), ("service", "restart"), ("service", "uninstall"), ("scheduler", "run"),
                 ("reset",), ("service", "run"), ("telegram", "run"), ("serve",))

DEFAULTS = {
    "enabled": True,            # the service starts the scheduler child
    "tick_sec": 20,             # how often due jobs are checked
    "timezone": "",             # IANA name; empty = the system zone
    "catchup": "one",           # default for new jobs
    "catchup_max": 5,           # catchup=all runs at most this many missed times
    "max_parallel": 2,          # runs at once across all jobs (a 1 GB box: keep it small)
    "default_timeout_sec": 600,
    "history_days": 30,
    "history_max": 2000,
    "output_chars": 1500,       # output kept per run
    # v3.8.4: a quill_task job with its own tool list (only=true) has no fixed tool-step cap;
    # false puts mcp_settings.max_tool_steps back on those jobs too
    "unlimited_job_tools": True,
    # job_guard: the runaway guards for those jobs (see nimlab.jobguard.DEFAULTS)
}
JOB_DEFAULTS = {
    "description": "", "enabled": True, "start_date": None, "end_date": None, "max_runs": 0,
    "max_failures": 0, "retry_count": 0, "retry_backoff_sec": 30, "timeout_sec": 0, "max_concurrent": 1,
    "overlap": "skip", "catchup": None, "result_to": None, "owner": "admin", "created_by": "cli",
}
EDITABLE = ("description", "schedule", "action_type", "action", "enabled", "start_date", "end_date", "max_runs",
            "max_failures", "retry_count", "retry_backoff_sec", "timeout_sec", "max_concurrent", "overlap",
            "catchup", "result_to", "owner")


class JobError(ValueError):
    """A job definition or change that cannot be accepted; says why."""


# ---------------------------------------------------------------------------
# settings and files
# ---------------------------------------------------------------------------
def settings(cluster=None):
    c = config.load_cluster_config() if cluster is None else cluster
    s = c.setdefault("scheduler_settings", {})
    for k, v in DEFAULTS.items():
        s.setdefault(k, v)
    return s


def sched_dir():
    from . import store
    d = os.path.join(store.data_dir(), "scheduler")
    os.makedirs(d, exist_ok=True)
    return d


def _p(name):
    return os.path.join(sched_dir(), name)


_tlock = threading.RLock()


@contextlib.contextmanager
def _locked(name="jobs.lock"):
    """Cross-process (flock) and cross-thread lock for read-modify-write."""
    with _tlock:
        f = open(_p(name), "a+")
        try:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl:
                with contextlib.suppress(OSError):
                    fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        # a damaged file is kept aside, never silently replaced
        with contextlib.suppress(OSError):
            os.replace(path, path + f".bad-{int(time.time())}")
        return default


def _write_json(path, data):
    tmp = f"{path}.tmp{os.getpid()}.{threading.get_ident()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _append(name, rec):
    with open(_p(name), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def _tail(name, n=None):
    try:
        with open(_p(name), encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    out = []
    for ln in (lines if n is None else lines[-n:]):
        with contextlib.suppress(ValueError):
            out.append(json.loads(ln))
    return out


def now():
    return time.time()


def _ts(t=None):
    return S.fmt(now() if t is None else t) if t != 0 else "-"


# ---------------------------------------------------------------------------
# the job store
# ---------------------------------------------------------------------------
def _doc():
    d = _read_json(_p("jobs.json"), None)
    if not isinstance(d, dict) or not isinstance(d.get("jobs"), dict):
        d = {"version": 1, "jobs": {}}
    for name, j in list(d["jobs"].items()):
        if not isinstance(j, dict):
            d["jobs"].pop(name)
            continue
        j.setdefault("state", {})
    if HEARTBEAT not in d["jobs"]:
        d["jobs"][HEARTBEAT] = builtin_heartbeat()
    return d


def builtin_heartbeat():
    t = now()
    return {"name": HEARTBEAT, "description": "Wake Quill to review the suggested actions and take the ones "
            "worth doing (built in)", "schedule": "FREQ=MINUTELY;INTERVAL=30", "action_type": "heartbeat",
            "action": "", **JOB_DEFAULTS, "enabled": False, "created_by": "builtin", "builtin": True,
            "timeout_sec": 900, "result_to": {"dest": "log", "when": "always"},
            "created_at": t, "updated_at": t, "state": {}}


def load_jobs():
    with _locked():
        return _doc()["jobs"]


def get_job(name):
    j = load_jobs().get(name)
    if j is None:
        raise JobError(f"no job named {name!r}; see: nimlab jobs list")
    return j


@contextlib.contextmanager
def _mutate():
    with _locked():
        d = _doc()
        yield d["jobs"]
        _write_json(_p("jobs.json"), d)


def _public(j):
    return {k: v for k, v in j.items() if k != "state"}


def audit(op, kind, name, before, after, who=None, source=None):
    """Every change to a job or a suggested action, with who asked."""
    try:
        from . import selfadmin
        ident = selfadmin.current()
        who = who or ident.who
        source = source or ident.source
        scrub = selfadmin.scrub
    except Exception:  # noqa: BLE001
        scrub = str
    rec = {"at": config.timestamp(), "who": who or "cli", "source": source or "cli", "op": op, "kind": kind,
           "name": name, "before": before, "after": after}
    try:
        rec = json.loads(scrub(json.dumps(rec, ensure_ascii=False, default=str)))
    except Exception:  # noqa: BLE001
        pass
    _append("audit.jsonl", rec)
    return rec


def audit_tail(n=20, name=None):
    rows = _tail("audit.jsonl")
    if name:
        rows = [r for r in rows if r.get("name") == name]
    return rows[-n:]


def _to_epoch(v, field):
    if v in (None, "", 0):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return S.parse_local(v)
    except S.ScheduleError as e:
        raise JobError(f"{field}: {e}") from None


def _int(v, field, lo=0, hi=10 ** 7):
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise JobError(f"{field} must be a whole number") from None
    if not lo <= n <= hi:
        raise JobError(f"{field} must be between {lo} and {hi}")
    return n


def _bool(v):
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on", "y")
    return bool(v)


def normalize(job, sa_shell=None, existing=None):
    """Validate and fill in a job. -> a clean dict, or raises JobError."""
    from . import routing
    j = {**JOB_DEFAULTS, **{k: v for k, v in (job or {}).items() if v is not None or k in ("end_date",)}}
    name = str(j.get("name") or "").strip()
    if not NAME_RX.match(name):
        raise JobError("the name needs letters, digits, - _ or . (up to 60, starting with a letter or digit)")
    j["name"] = name
    why = S.validate(j.get("schedule", ""))
    if why:
        raise JobError(f"schedule: {why}")
    j["schedule"] = str(j["schedule"]).strip()
    at = str(j.get("action_type") or "").strip().lower()
    builtin = bool((existing or {}).get("builtin") or j.get("builtin"))
    if at not in (ACTION_TYPES if builtin else USER_ACTION_TYPES):
        raise JobError(f"action_type must be one of {', '.join(USER_ACTION_TYPES)}")
    j["action_type"] = at
    j["action"] = check_action(at, j.get("action"), sa_shell)
    j["enabled"] = _bool(j["enabled"])
    j["start_date"] = _to_epoch(j.get("start_date"), "start_date")
    j["end_date"] = _to_epoch(j.get("end_date"), "end_date")
    if j["start_date"] and j["end_date"] and j["end_date"] <= j["start_date"]:
        raise JobError("end_date must be after start_date")
    for k, hi in (("max_runs", 10 ** 6), ("max_failures", 1000), ("retry_count", 10),
                  ("retry_backoff_sec", 86400), ("timeout_sec", 86400)):
        j[k] = _int(j.get(k) or 0, k, 0, hi)
    j["max_concurrent"] = _int(j.get("max_concurrent") or 1, "max_concurrent", 1, 5)
    j["overlap"] = str(j.get("overlap") or "skip").lower()
    if j["overlap"] not in OVERLAP:
        raise JobError(f"overlap must be one of {', '.join(OVERLAP)}")
    if j.get("catchup") not in (None, ""):
        j["catchup"] = str(j["catchup"]).lower()
        if j["catchup"] not in CATCHUP:
            raise JobError(f"catchup must be one of {', '.join(CATCHUP)}")
    else:
        j["catchup"] = None
    j["result_to"] = routing.normalize(j.get("result_to"), default=routing.default_for(at))
    j["owner"] = str(j.get("owner") or "admin")[:40]
    j["created_by"] = str(j.get("created_by") or "cli")[:80]
    if builtin:
        j["builtin"] = True
    return j


def _shell_on():
    try:
        from . import selfadmin
        return bool(selfadmin.settings().get("shell"))
    except Exception:  # noqa: BLE001
        return False


def _split_tools(v):
    if isinstance(v, (list, tuple)):
        items = v
    else:
        items = re.split(r"[,\s]+", str(v or "").strip())
    out = []
    for t in items:
        t = str(t).strip()
        if t and t not in out:
            out.append(t)
    return out


def check_task(action):
    """quill_task (v3.8.3): a prompt plus the MCP tools picked for the job.
    -> {"prompt", "tools": [names], "only": bool, "require_tool": bool}.
    A plain string is the prompt; JSON gives every field."""
    a = action
    if isinstance(a, str):
        t = a.strip()
        if t.startswith("{"):
            try:
                a = json.loads(t)
            except ValueError as e:
                raise JobError(f"quill_task: the action is not JSON ({e})") from None
        else:
            a = {"prompt": t}
    if not isinstance(a, dict):
        raise JobError("quill_task needs a prompt and a list of tools")
    prompt = str(a.get("prompt") or "").strip()
    if not prompt:
        raise JobError("quill_task needs a prompt: what Quill should do")
    tools = _split_tools(a.get("tools"))
    only = _bool(a.get("only", True))
    if only and not tools:
        raise JobError("quill_task: pick at least one MCP tool, or let Quill use any tool (only=false)")
    for t in tools:
        if not re.match(r"^[A-Za-z0-9_.:\-]{1,128}$", t):
            raise JobError(f"quill_task: {t!r} is not a tool name")
    out = {"prompt": prompt, "tools": tools, "only": only, "require_tool": _bool(a.get("require_tool", False))}
    if "interruptible" in a:
        # v3.8.4: a user message, an email alert or any other job starting ends this job; unset means
        # a repeating job is interruptible and a one-off job (an email alert) is not
        out["interruptible"] = _bool(a.get("interruptible"))
    return out


def task_brief(a):
    """One line for menus and /jobs."""
    a = a if isinstance(a, dict) else {}
    mode = "only these" if a.get("only", True) else "any tool, these preferred"
    req = ", must call one" if a.get("require_tool") else ""
    req += {True: ", interruptible", False: ", not interruptible"}.get(a.get("interruptible"), "")
    tools = ", ".join(a.get("tools") or []) or "(none)"
    return f"{str(a.get('prompt') or '')[:60]} | tools: {tools} ({mode}{req})"


FREE_TIME_PROMPT = ("It's your free time. Pick one of your tools that looks fun right now, play with it for a "
                    "bit (call it at least once), then tell me in a few lines what you picked, what you did "
                    "with it and how it went.")


def free_time_template(tools, name="free-time", result_to="telegram"):
    """The ready-made "Free time" job: hourly, Quill picks one of the chosen
    (entertainment) tools, plays with it and says what it did."""
    tools = _split_tools(tools)
    return {"name": name, "description": "Free time: Quill picks one of the chosen tools and plays with it",
            "schedule": "FREQ=HOURLY;BYMINUTE=0", "action_type": "quill_task",
            "action": {"prompt": FREE_TIME_PROMPT, "tools": tools, "only": True, "require_tool": True,
                       "interruptible": True},
            "timeout_sec": 1800, "result_to": {"dest": result_to, "when": "always"}}


def live_mcp_tools():
    """The tool list the MCP server offers right now (the admin console's
    toggles decide it). -> [{name, description, ...}]. Raises JobError."""
    from . import config
    from .mcp import MCPClient
    cfg = config.load_cluster_config() or {}
    s = cfg.get("mcp_settings", {}) or {}
    if not (s.get("enabled") and s.get("url")):
        raise JobError("MCP is not set up (menu M, or nimlab setup mcp)")
    try:
        return list(MCPClient(s).list_tools() or [])
    except Exception as e:  # noqa: BLE001
        raise JobError(f"could not load the MCP tool list: {str(e)[:200]}") from None


def check_action(at, action, sa_shell=None, depth=0):
    """Validate one action of a type. -> the cleaned action."""
    if at == "heartbeat":
        return ""
    if at in ("quill_prompt", "shell", "nimlab_command"):
        a = str(action or "").strip()
        if not a:
            raise JobError(f"{at} needs an action: " + {"quill_prompt": "the prompt to send Quill",
                                                        "shell": "the shell command",
                                                        "nimlab_command": "a nimlab command, e.g. 'test service'"}[at])
        if at == "shell" and not (_shell_on() if sa_shell is None else sa_shell):
            raise JobError("shell jobs need self-admin shell on (nimlab selfadmin shell on)")
        if at == "nimlab_command":
            argv = command_argv(a)
            for deny in DENY_COMMANDS:
                if tuple(argv[:len(deny)]) == deny:
                    raise JobError(f"'nimlab {' '.join(deny)}' can't run as a job (it would stop the scheduler "
                                   "or the lab)")
            return " ".join(shlex.quote(x) for x in argv)
        return a
    if at == "quill_task":
        return check_task(action)
    if at == "test":
        from . import systests
        names = action if isinstance(action, list) else re.split(r"[,\s]+", str(action or "").strip())
        names = [n for n in (str(x).strip() for x in names) if n]
        if not names:
            raise JobError("test needs one or more test names, e.g. 'service,tunnel' (see: nimlab test)")
        out = []
        for n in names:
            if n == "all":
                out.append("all")
                continue
            t = systests.find(n)
            if not t:
                raise JobError(f"no test {n!r}; tests: {', '.join(systests.BY_NAME)}")
            out.append(t.name)
        return out
    if at == "mcp_tool":
        a = action
        if isinstance(a, str):
            a = a.strip()
            try:
                a = json.loads(a) if a.startswith("{") else {"tool": a.split(None, 1)[0],
                                                             "args": json.loads(a.split(None, 1)[1])
                                                             if len(a.split(None, 1)) > 1 else {}}
            except ValueError as e:
                raise JobError(f"mcp_tool: the args are not JSON ({e})") from None
        if not isinstance(a, dict) or not str(a.get("tool") or "").strip():
            raise JobError('mcp_tool needs {"tool": "<name>", "args": {...}} or "<tool> <json args>"')
        args = a.get("args") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError as e:
                raise JobError(f"mcp_tool: the args are not JSON ({e})") from None
        if not isinstance(args, dict):
            raise JobError("mcp_tool: args must be a JSON object")
        return {"tool": str(a["tool"]).strip(), "args": args}
    if at == "chain":
        return check_chain(action, sa_shell, depth)
    raise JobError(f"unknown action_type {at}")


def check_chain(action, sa_shell=None, depth=0):
    """A chain: {"steps": [{name, type, action, on_success, on_failure}]}.
    on_success defaults to the next step, on_failure to END (the chain
    fails). A step may name any step, or END."""
    if depth > 2:
        raise JobError("chains can nest at most 3 deep")
    a = action
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except ValueError as e:
            raise JobError(f"chain: not JSON ({e})") from None
    if isinstance(a, list):
        a = {"steps": a}
    steps = (a or {}).get("steps") if isinstance(a, dict) else None
    if not isinstance(steps, list) or not steps:
        raise JobError('chain needs {"steps": [{"name": ..., "type": ..., "action": ...}, ...]}')
    if len(steps) > 20:
        raise JobError("a chain can have at most 20 steps")
    names, out = set(), []
    for i, st in enumerate(steps):
        if not isinstance(st, dict):
            raise JobError(f"chain step {i + 1} is not an object")
        n = str(st.get("name") or f"step{i + 1}")
        if not NAME_RX.match(n) or n.upper() == "END" or n in names:
            raise JobError(f"chain step name {n!r} is not valid or is used twice")
        names.add(n)
        t = str(st.get("type") or st.get("action_type") or "").lower()
        if t not in USER_ACTION_TYPES:
            raise JobError(f"chain step {n}: type must be one of {', '.join(USER_ACTION_TYPES)}")
        out.append({"name": n, "type": t, "action": check_action(t, st.get("action"), sa_shell, depth + 1),
                    "on_success": st.get("on_success"), "on_failure": st.get("on_failure")})
    for i, st in enumerate(out):
        if st["on_success"] in (None, ""):
            st["on_success"] = out[i + 1]["name"] if i + 1 < len(out) else "END"
        if st["on_failure"] in (None, ""):
            st["on_failure"] = "END"
        for k in ("on_success", "on_failure"):
            if st[k] != "END" and st[k] not in names:
                raise JobError(f"chain step {st['name']}: {k} names no step ({st[k]})")
    return {"steps": out}


def command_argv(text):
    argv = shlex.split(str(text))
    if argv and argv[0] == "nimlab":
        argv = argv[1:]
    if not argv:
        raise JobError("empty nimlab command")
    return argv


def create_job(spec, who=None, source=None, sa_shell=None):
    spec = dict(spec or {})
    spec.setdefault("created_by", who or "cli")
    j = normalize(spec, sa_shell)
    if j["action_type"] == "heartbeat":
        raise JobError("there is one heartbeat job, built in: change it with nimlab heartbeat")
    t = now()
    with _mutate() as jobs:
        if j["name"] in jobs:
            raise JobError(f"a job named {j['name']} already exists (edit it, or pick another name)")
        j["created_at"] = j["updated_at"] = t
        j["state"] = {}
        _plan(j, t)
        jobs[j["name"]] = j
    audit("create", "job", j["name"], None, _public(j), who, source)
    return j


def update_job(name, changes, who=None, source=None, sa_shell=None):
    changes = {k: v for k, v in (changes or {}).items() if k in EDITABLE}
    if not changes:
        raise JobError(f"nothing to change; editable fields: {', '.join(EDITABLE)}")
    with _mutate() as jobs:
        if name not in jobs:
            raise JobError(f"no job named {name!r}")
        old = jobs[name]
        if old.get("builtin") and "action_type" in changes and changes["action_type"] != old["action_type"]:
            raise JobError("the built-in heartbeat job keeps its action type")
        merged = {**_public(old), **changes}
        j = normalize(merged, sa_shell, existing=old)
        j["created_at"] = old.get("created_at")
        j["updated_at"] = now()
        j["state"] = dict(old.get("state") or {})
        if any(k in changes for k in ("schedule", "start_date", "end_date", "enabled")):
            j["state"].pop("next_run", None)
            if changes.get("enabled") and j["state"].get("state") in ("COMPLETED", "BROKEN"):
                j["state"]["state"] = "SCHEDULED"
                j["state"]["failures_in_a_row"] = 0
            _plan(j, now())
        jobs[name] = j
    audit("edit" if set(changes) != {"enabled"} else ("enable" if j["enabled"] else "disable"), "job", name,
          {k: old.get(k) for k in changes}, {k: j.get(k) for k in changes}, who, source)
    return j


def set_enabled(name, on, who=None, source=None):
    return update_job(name, {"enabled": bool(on)}, who, source)


def delete_job(name, who=None, source=None):
    with _mutate() as jobs:
        if name not in jobs:
            raise JobError(f"no job named {name!r}")
        if jobs[name].get("builtin"):
            raise JobError("the heartbeat job is built in: disable it instead (nimlab heartbeat disable)")
        old = jobs.pop(name)
    audit("delete", "job", name, _public(old), None, who, source)
    return old


def _plan(j, t):
    """Fill state.next_run from the schedule."""
    st = j.setdefault("state", {})
    if not j.get("enabled"):
        st["next_run"] = None
        st.setdefault("state", "DISABLED")
        if st["state"] == "SCHEDULED":
            st["state"] = "DISABLED"
        return
    try:
        st["next_run"] = S.next_run(j["schedule"], t, anchor=j.get("start_date") or j.get("created_at") or t,
                                    start=j.get("start_date"), end=j.get("end_date"))
    except S.ScheduleError:
        st["next_run"] = None
    if st.get("state") in (None, "DISABLED"):
        st["state"] = "SCHEDULED"
    if st["next_run"] is None and st.get("state") == "SCHEDULED":
        st["state"] = "COMPLETED"


def next_runs(name, count=5):
    j = get_job(name)
    if not j.get("enabled"):
        return []
    return S.upcoming(j["schedule"], count, after=now(), anchor=j.get("start_date") or j.get("created_at"),
                      start=j.get("start_date"), end=j.get("end_date"))


# ---------------------------------------------------------------------------
# run history
# ---------------------------------------------------------------------------
def history(name=None, n=20, status=None):
    rows = _tail("runs.jsonl")
    if name:
        rows = [r for r in rows if r.get("job") == name]
    if status:
        rows = [r for r in rows if r.get("status") == status.upper()]
    return rows[-n:]


def prune_history(cluster=None, t=None):
    s = settings(cluster)
    t = now() if t is None else t
    keep_after = t - float(s.get("history_days") or 30) * 86400
    with _locked("runs.lock"):
        rows = _tail("runs.jsonl")
        kept = [r for r in rows if float(r.get("start") or 0) >= keep_after]
        kept = kept[-int(s.get("history_max") or 2000):]
        if len(kept) != len(rows):
            tmp = _p("runs.jsonl.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                for r in kept:
                    f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            os.replace(tmp, _p("runs.jsonl"))
        return len(rows) - len(kept)


def _record_run(rec):
    with _locked("runs.lock"):
        _append("runs.jsonl", rec)


# ---------------------------------------------------------------------------
# what an action can touch (the live context; tests pass a fake)
# ---------------------------------------------------------------------------
class ActionResult:
    def __init__(self, ok, output="", notable=None, data=None, timed_out=False):
        self.ok, self.output, self.notable, self.data = bool(ok), str(output or ""), notable, data
        self.timed_out = timed_out


class LiveContext:
    """Real effects: Quill, the CLI, MCP, the tests, Telegram, memory."""

    def __init__(self, log=None):
        self._ent = None
        self._ent_lock = threading.Lock()
        self.log = log or (lambda *a: None)

    def entity(self):
        with self._ent_lock:
            if self._ent is None:
                from .entity import Entity
                self._ent = Entity(log=lambda *a: None)
            return self._ent

    def quill(self, prompt, who="scheduler", max_tokens=1024, timeout=None, use_tools=True):
        """One turn through the same pipeline as chat (router, persona,
        memory recall and store, tools). -> (ok, text)."""
        from . import environment as ENV, perf, selfadmin
        ent = self.entity()
        with selfadmin.identity(admin=True, who=who, source="scheduler"), ENV.channel("scheduler"), \
                perf.time_cap(timeout):
            out = ent.turn(prompt, [], max_tokens=max_tokens)
        if out.get("blocked"):
            return False, out["blocked"]
        r = out.get("result")
        if r is None or not getattr(r, "ok", False):
            return False, (getattr(r, "error", None) or "no reply")
        return True, getattr(r, "text", "") or ""

    def quill_task(self, a, who="scheduler", max_tokens=1024, timeout=None, guard=None):
        """quill_task: one persona turn with only the job's MCP tools offered
        (or any tool when only is false). -> dict(ok, text, error, trace,
        present, missing)."""
        from . import environment as ENV, perf, selfadmin
        ent = self.entity()
        if ent.mcp is None:
            return {"ok": False, "error": "MCP is not set up (menu M, or nimlab setup mcp); the task needs its tools"}
        live = [t.get("name") for t in ent.ensure_tools()]
        want = list(a.get("tools") or [])
        present = [t for t in want if t in live]
        missing = [t for t in want if t not in live]
        if not live and ent.tools_error:
            return {"ok": False, "error": f"the MCP tool list could not be loaded: {ent.tools_error}",
                    "missing": missing}
        if a.get("only", True) and not present:
            return {"ok": False, "missing": missing,
                    "error": "none of this job's tools are on the MCP server now: " + ", ".join(want) +
                             ". Turn them on in the MCP admin console, or edit the job's tools."}
        from . import jobguard as JG
        unlimited = bool(guard is not None and guard.unlimited and a.get("only", True))
        with selfadmin.identity(admin=True, who=who, source="scheduler"), ENV.channel("scheduler"), \
                perf.time_cap(timeout), selfadmin.task_tools(present if a.get("only", True) else want,
                                                             a.get("only", True)), JG.using(guard):
            out = ent.turn(task_prompt(a, present, unlimited=unlimited), [], role="persona", max_tokens=max_tokens)
        res = {"trace": out.get("trace") or [], "present": present, "missing": missing}
        if out.get("blocked"):
            return dict(res, ok=False, error=out["blocked"])
        r = out.get("result")
        if r is None or not getattr(r, "ok", False):
            return dict(res, ok=False, error=getattr(r, "error", None) or "no reply")
        return dict(res, ok=True, text=getattr(r, "text", "") or "")

    def cli(self, argv, timeout=600):
        env = dict(os.environ, NIMLAB_COLOR="0", NIMLAB_FROM_SCHEDULER="1")
        try:
            r = subprocess.run([sys.executable, "-m", "nimlab", *argv], cwd=config.PROJECT_DIR,
                               capture_output=True, text=True, timeout=timeout or None, env=env,
                               stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return None, f"timed out after {timeout} s"
        out = (r.stdout + ("\n" + r.stderr if r.stderr.strip() else "")).strip()
        return r.returncode == 0, out[-6000:]

    def shell(self, command, timeout=60):
        if not _shell_on():
            return False, "self-admin shell is off (nimlab selfadmin shell on); the job did not run"
        try:
            r = subprocess.run(["bash", "-c", command], cwd=config.PROJECT_DIR, capture_output=True, text=True,
                               timeout=timeout or None, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return None, f"timed out after {timeout} s"
        out = (r.stdout + ("\n" + r.stderr if r.stderr.strip() else "")).strip()
        return r.returncode == 0, f"exit {r.returncode}\n{out[-6000:]}"

    def mcp_call(self, tool, args):
        ent = self.entity()
        if ent.mcp is None:
            raise RuntimeError("MCP is not set up (nimlab setup mcp)")
        res = ent.mcp.call_tool(tool, args or {})
        text = " ".join(c.get("text", "") for c in (res or {}).get("content") or [] if isinstance(c, dict))
        return not (res or {}).get("isError"), text or json.dumps(res, default=str)[:2000]

    def tests(self, names):
        from . import systests
        todo = list(systests.BY_NAME) if "all" in names else names
        rows, results = [], {}
        for n in todo:
            t = systests.find(n)
            r = systests.run_one(t)
            results[t.name] = r
            rows.append((t.name, r.status, r.detail, r.bug))
        with contextlib.suppress(Exception):
            systests.save_history(results)
        return rows

    def telegram(self, text):
        from . import telegram as TG
        tok = TG.load_token()
        owner = TG.settings().get("owner")
        if not tok or not owner:
            return False, "Telegram has no bot token or no owner yet (nimlab telegram allow --capture)"
        bot = TG.Bot(tok)
        for piece in TG.split_text(text):
            bot.call("sendMessage", chat_id=owner, text=piece)
        return True, "sent to the owner"

    def memory_store(self, text, meta=None):
        ent = self.entity()
        mem = getattr(ent, "memory", None)
        if mem is None:
            return False, "memory is off"
        rid = mem.store(text, metadata=meta or {}, kind="scheduler")
        return (rid is not None), (f"stored (id {rid})" if rid is not None else "not stored (duplicate, "
                                                                                 "or the store is offline)")

    def bug(self, kind, message, where):
        from . import bugs
        return bugs.record(kind, message, where=where)


# ---------------------------------------------------------------------------
# running actions
# ---------------------------------------------------------------------------
def _with_timeout(fn, timeout):
    """Run fn() in a thread. -> (finished, value or exception). A run that
    does not finish in time is reported TIMED_OUT; its thread is left to end
    on its own (Python cannot kill it) and still counts as running."""
    box = {}

    def work():
        try:
            box["v"] = fn()
        except BaseException as e:  # noqa: BLE001 - reported as the run's failure
            box["e"] = e
    th = threading.Thread(target=work, daemon=True, name="nimlab-job")
    th.start()
    th.join(timeout if timeout and timeout > 0 else None)
    if th.is_alive():
        return False, th
    if "e" in box:
        raise box["e"]
    return True, box.get("v")


def run_action(at, action, ctx, job=None, timeout=0, depth=0):
    """Run one action. -> ActionResult (never raises)."""
    name = (job or {}).get("name", "adhoc")
    try:
        if at == "quill_prompt":
            def go():
                return ctx.quill(action, who=f"scheduler:{name}", timeout=timeout or None)
            done, v = _with_timeout(go, timeout)
            if not done:
                return ActionResult(False, f"Quill did not answer within {timeout} s", timed_out=True)
            ok, text = v
            return ActionResult(ok, text)
        if at == "quill_task":
            return run_task(action, ctx, name, timeout, job=job)
        if at == "nimlab_command":
            ok, out = ctx.cli(command_argv(action), timeout=timeout or 600)
            if ok is None:
                return ActionResult(False, out, timed_out=True)
            return ActionResult(ok, out)
        if at == "shell":
            ok, out = ctx.shell(action, timeout=timeout or 60)
            if ok is None:
                return ActionResult(False, out, timed_out=True)
            return ActionResult(ok, out)
        if at == "test":
            names = action if isinstance(action, list) else [action]
            done, rows = _with_timeout(lambda: ctx.tests(names), timeout)
            if not done:
                return ActionResult(False, f"the tests did not finish within {timeout} s", timed_out=True)
            failed = [r for r in rows if r[1] == "FAIL"]
            lines = [f"{r[1]:<4} {r[0]}: {r[2]}" + (f" (bug {r[3]})" if len(r) > 3 and r[3] else "") for r in rows]
            head = (f"{len(failed)} of {len(rows)} tests failed" if failed else
                    f"{len(rows)} test{'s' if len(rows) != 1 else ''}: none failed")
            return ActionResult(not failed, head + "\n" + "\n".join(lines), notable=bool(failed) or None,
                                data={"rows": [list(r) for r in rows]})
        if at == "mcp_tool":
            a = action if isinstance(action, dict) else check_action("mcp_tool", action)
            done, v = _with_timeout(lambda: ctx.mcp_call(a["tool"], a.get("args") or {}), timeout)
            if not done:
                return ActionResult(False, f"{a['tool']} did not answer within {timeout} s", timed_out=True)
            ok, text = v
            return ActionResult(ok, text)
        if at == "chain":
            return run_chain(action, ctx, job, timeout, depth)
        if at == "heartbeat":
            from . import heartbeat
            return heartbeat.run(ctx, job or {}, timeout=timeout)
        return ActionResult(False, f"unknown action type {at}")
    except Exception as e:  # noqa: BLE001 - an action error is a failed run, never a crash
        return ActionResult(False, f"{type(e).__name__}: {str(e)[:500]}")


def task_prompt(a, present, unlimited=False):
    """The job prompt plus a note naming the tools Quill was given."""
    names = present if a.get("only", True) else (present or [])
    note = ""
    if names:
        note = ("\n\n[JOB TOOLS] For this task you have these MCP tools: " + ", ".join(names) + ". "
                + ("Call them with the tool-call format from your instructions. " if a.get("only", True) else
                   "Prefer these; any other tool you have is allowed too. ")
                + ("You must call at least one of them before you answer. " if a.get("require_tool") else "")
                + "Afterwards say which tool you used and what happened.")
        if a.get("only", True) and unlimited:
            note += (" There is no fixed limit on tool calls in this job: keep using these tools for as long as "
                     "you like, then answer.")
            if a.get("interruptible"):
                note += (" If SeVin messages you, an email arrives or another scheduled job starts, this job "
                         "ends where you are, so share anything you make as soon as you have its link.")
    return a["prompt"] + note


def _tool_report(trace):
    """-> (calls [{name, outcome, latency_sec, reason}], lines)."""
    calls, lines = [], []
    for e in trace or []:
        if not e.get("name"):
            continue
        c = {"name": e["name"], "outcome": e.get("outcome") or "?", "latency_sec": e.get("latency_sec"),
             "reason": e.get("reason")}
        calls.append(c)
        how = {"ok": "ok", "error": "the tool returned an error", "failed": "the call failed",
               "rejected": "not run"}.get(c["outcome"], c["outcome"])
        extra = f" in {c['latency_sec']} s" if c["latency_sec"] is not None else ""
        why = f": {str(c['reason'])[:120]}" if c.get("reason") else ""
        lines.append(f"- {c['name']}: {how}{extra}{why}")
    return calls, lines


def run_task(action, ctx, name="adhoc", timeout=0, job=None):
    """quill_task: Quill gets the prompt and only the picked MCP tools (or any
    tool, with these preferred) and may call them in the tool loop. The run
    report lists every tool call and how it went. -> ActionResult."""
    a = action if isinstance(action, dict) else check_task(action)
    fn = getattr(ctx, "quill_task", None)
    if not callable(fn):
        return ActionResult(False, "this scheduler context can't run quill_task jobs")
    from . import interrupts
    guard = _job_guard(a, ctx, name, timeout, job)
    kw = {"who": f"scheduler:{name}", "timeout": timeout or None}
    if guard is not None and _takes(fn, "guard"):
        kw["guard"] = guard
    left = interrupts.load_leftover(name) if guard is not None and guard.interruptible else None
    run_a = dict(a, prompt=a["prompt"] + leftover_note(left, a)) if left else a
    done, v = _with_timeout(lambda: fn(run_a, **kw), timeout)
    if not done:
        if guard is not None:
            guard.cancelled.set()      # the abandoned thread ends at its next step instead of looping on
        return ActionResult(False, f"Quill did not finish the task within {timeout} s", timed_out=True)
    v = v or {}
    present, missing = list(v.get("present") or []), list(v.get("missing") or [])
    calls, lines = _tool_report(v.get("trace"))
    # load_tools only fetches definitions (lazy tool mode): it does not count as using a tool
    ran = [c for c in calls if c["outcome"] in ("ok", "error", "failed") and c["name"] != "load_tools"]
    data = {"tools_called": calls, "tools_offered": present, "tools_missing": missing}
    stopped = dict(guard.stopped) if guard is not None and guard.stopped else None
    if stopped:
        stopped.pop("mark", None)
        data["stopped"] = stopped
        if stopped.get("kind") == "interrupted":
            data["interrupted"] = stopped.get("reason")
    links = []
    for e in v.get("trace") or []:
        for u in e.get("links") or []:
            if u not in links:
                links.append(u)
    if links:
        data["links"] = links[:10]
    if left:
        data["picked_up"] = {"saved_ts": left.get("saved_ts"), "auto": not job_has_choices(a)}
    if stopped and stopped.get("kind") == "interrupted":
        progress = getattr(guard, "progress", "") or ""
        if not progress.strip() and left:
            progress = left.get("progress") or ""      # interrupted before doing anything new: keep the old
        interrupts.save_leftover(name, {"reason": stopped.get("reason"), "progress": progress,
                                        "links": links[:10] or list((left or {}).get("links") or []),
                                        "interrupted_at": config.timestamp()})
        data["leftover_saved"] = True
    elif v.get("ok") and left:
        interrupts.clear_leftover(name)                # finished normally: start fresh next time
        data["leftover_cleared"] = True
    if v.get("error") and not v.get("ok"):
        out = v["error"]
        if stopped:
            out += f"\n\nStopped: {stopped.get('reason')}"
        if lines:
            out += "\n\nTools called:\n" + "\n".join(lines)
        return ActionResult(False, out, data=data)
    text = str(v.get("text") or "").strip()
    tail = []
    if stopped and stopped.get("kind") == "interrupted":
        text = (f"Ended early: {stopped.get('reason')}, so Quill stopped here. It does not resume now; where he "
                f"left off is handed back at the next {name} run"
                + (" (he chooses whether to pick it up)." if job_has_choices(a) else " (he continues it).")
                + ("\nThings Quill made before stopping:\n" + "\n".join(f"- {u}" for u in links[:10])
                   if links else ""))
    elif stopped:
        tail.append(f"Stopped by the job guard: {stopped.get('reason')}.")
    tail.append("Tools called:\n" + "\n".join(lines) if lines else "Tools called: none")
    if missing:
        tail.append("Not on the MCP server now (not offered): " + ", ".join(missing))
    ok = bool(v.get("ok"))
    if ok and a.get("require_tool") and not ran and not (stopped and stopped.get("kind") == "interrupted"):
        ok = False
        tail.insert(0, "FAILED: the job requires at least one tool call and Quill called none.")
    return ActionResult(ok, (text + "\n\n" if text else "") + "\n".join(tail), data=data,
                        notable=(not ok) or None)


def _takes(fn, kw):
    import inspect
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    return kw in sig.parameters or any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())


def job_has_choices(a):
    """Free time and the like: several tools to choose from (or any tool).
    A job with one tool (or none) does one thing."""
    return (not a.get("only", True)) or len(a.get("tools") or []) > 1


def job_repeats(job):
    try:
        return S.parse(str((job or {}).get("schedule") or ""))["kind"] != "once"
    except Exception:  # noqa: BLE001
        return False


def leftover_note(left, a):
    """The words that hand an interrupted run back to the job's next run.
    Several options (Free time): Quill chooses whether to pick it back up.
    One function: he continues it, no choice."""
    when = str(left.get("interrupted_at") or "")
    why = str(left.get("reason") or "it was interrupted")
    prog = str(left.get("progress") or "").strip() or "(nothing was recorded beyond the job starting)"
    links = left.get("links") or []
    head = (f"\n\nLAST TIME THIS JOB WAS INTERRUPTED{(' at ' + when) if when else ''} ({why}) before you "
            f"finished. Where you left off:\n{prog}")
    if links:
        head += "\nLinks you had made: " + ", ".join(links[:5])
    if job_has_choices(a):
        return head + ("\nYou can pick that back up where you stopped, or do something else with these tools; "
                       "it's your choice. Say which you chose.")
    return head + "\nContinue it from where you stopped (do not start over), then finish the job."


def _job_guard(a, ctx, name, timeout, job=None):
    """v3.8.4: the guard for one quill_task run, or None. A job with its own
    tool list gets no fixed tool-step cap (scheduler_settings.unlimited_job_tools)
    with runaway guards instead; an interruptible job (Free time) ends when a
    user message, an email alert or another job interrupts it."""
    from . import jobguard as JG
    try:
        cluster = (getattr(ctx, "entity", None) and ctx.entity().cluster) or {}
    except Exception:  # noqa: BLE001
        cluster = {}
    sset = dict(DEFAULTS, **((cluster or {}).get("scheduler_settings") or {}))
    unlimited = bool(sset.get("unlimited_job_tools", True)) and bool(a.get("only", True))
    if "interruptible" in a:
        interruptible = bool(a.get("interruptible"))
    else:
        interruptible = job_repeats(job)
    if not unlimited and not interruptible:
        return None
    return JG.JobGuard(name=name, timeout=timeout, interruptible=interruptible, unlimited=unlimited,
                       cfg=JG.settings(cluster))


def run_chain(action, ctx, job=None, timeout=0, depth=0):
    steps = (action or {}).get("steps") or []
    by = {s["name"]: s for s in steps}
    t0 = time.monotonic()
    cur = steps[0]["name"] if steps else "END"
    lines, ran, last_ok, visits = [], [], True, 0
    failed_unhandled = False
    while cur != "END" and visits < 50:
        visits += 1
        st = by[cur]
        left = (timeout - (time.monotonic() - t0)) if timeout else 0
        if timeout and left <= 0:
            lines.append(f"{cur}: not run, the chain's time is up")
            return ActionResult(False, "\n".join(lines), timed_out=True, data={"steps": ran})
        r = run_action(st["type"], st["action"], ctx, job, timeout=int(left) if timeout else 0, depth=depth + 1)
        ran.append({"step": cur, "ok": r.ok, "timed_out": r.timed_out})
        first = (r.output.strip().splitlines() or [""])[0][:200]
        lines.append(f"{cur}: {'SUCCEEDED' if r.ok else ('TIMED_OUT' if r.timed_out else 'FAILED')} {first}")
        last_ok = r.ok
        nxt = st["on_success"] if r.ok else st["on_failure"]
        failed_unhandled = (not r.ok) and nxt == "END"
        cur = nxt
    if visits >= 50:
        lines.append("stopped after 50 steps (a loop in on_success / on_failure?)")
        return ActionResult(False, "\n".join(lines), data={"steps": ran})
    ok = last_ok or not failed_unhandled
    head = f"chain {'SUCCEEDED' if ok else 'FAILED'} after {len(ran)} step{'s' if len(ran) != 1 else ''}"
    return ActionResult(ok, head + "\n" + "\n".join(lines), notable=(not ok) or any(not x["ok"] for x in ran),
                        data={"steps": ran})


# ---------------------------------------------------------------------------
# the scheduler
# ---------------------------------------------------------------------------
class Scheduler:
    """tick() starts what is due. Runs go to worker threads (threaded=True)
    or run inline (tests). One Scheduler per box: see acquire_lock()."""

    def __init__(self, ctx=None, cluster=None, clock=now, threaded=True, log=None):
        self.ctx = ctx or LiveContext()
        self.cluster = cluster
        self.clock = clock
        self.threaded = threaded
        self.log = log or (lambda *a: None)
        self.running = {}            # run_id -> (job name, thread)
        self._lock = threading.Lock()
        self.started = False
        self.last_prune = 0

    def cfg(self):
        return settings(self.cluster)

    # -- one tick ---------------------------------------------------------
    def tick(self):
        t = self.clock()
        s = self.cfg()
        due = []
        with _mutate() as jobs:
            for name, j in jobs.items():
                st = j.setdefault("state", {})
                self._reap(name, st)
                if not j.get("enabled"):
                    continue
                if j.get("end_date") and t > j["end_date"]:
                    self._finish(j, st, "COMPLETED", "end_date passed")
                    continue
                if "next_run" not in st:
                    _plan(j, t)
                due += self._due(j, st, t, s)
            for name, trigger, attempt in due:
                st = jobs[name]["state"]
                st.setdefault("running", []).append({"run_id": None, "since": t, "pid": os.getpid(),
                                                     "trigger": trigger})
        started = []
        for name, trigger, attempt in due:
            started.append(self._start(name, trigger, attempt))
        if t - self.last_prune > 3600:
            self.last_prune = t
            with contextlib.suppress(Exception):
                prune_history(self.cluster, t)
        return started

    def _reap(self, name, st):
        """Drop 'running' marks whose run is no longer alive (this process
        restarted, or another process died mid-run)."""
        keep = []
        for r in st.get("running") or []:
            rid = r.get("run_id")
            if r.get("pid") == os.getpid():
                with self._lock:
                    alive = rid in self.running and self.running[rid][1].is_alive() if rid else True
            else:
                alive = _pid_alive(r.get("pid"))
            if alive:
                keep.append(r)
        st["running"] = keep

    def _busy(self):
        with self._lock:
            return sum(1 for _, th in self.running.values() if th.is_alive())

    def _due(self, j, st, t, s):
        out = []
        name = j["name"]
        n_running = len(st.get("running") or [])
        free = max(0, int(s.get("max_parallel") or 2) - self._busy())
        # a retry that is due
        if st.get("retry_at") and st["retry_at"] <= t:
            if n_running < j.get("max_concurrent", 1) and free:
                out.append((name, "retry", int(st.get("retry_attempt") or 2)))
                st["retry_at"] = None
            return out
        # queued runs (overlap=queue, catchup=all)
        if st.get("queued") and n_running < j.get("max_concurrent", 1) and free:
            st["queued"] -= 1
            return [(name, "queued", 1)]
        nr = st.get("next_run")
        if nr is None or nr > t:
            return out
        anchor = j.get("start_date") or j.get("created_at") or nr
        missed = 1 + S.runs_between(j["schedule"], nr, t, anchor=anchor, start=j.get("start_date"),
                                    end=j.get("end_date"))
        late = t - nr
        grace = max(120, 3 * float(s.get("tick_sec") or 20))
        policy = j.get("catchup") or s.get("catchup") or "one"
        trigger = "schedule"
        if late > grace:
            trigger = "catchup"
            if policy == "none":
                self._skip(j, st, t, "MISSED", f"missed {missed} run{'s' if missed != 1 else ''} while the "
                                               "scheduler was down (catchup=none)")
                _plan(j, t)
                return out
        if n_running >= j.get("max_concurrent", 1):
            if j.get("overlap") == "queue":
                st["queued"] = min(1, int(st.get("queued") or 0) + 1)
            else:
                self._skip(j, st, t, "SKIPPED", "the previous run is still going (overlap=skip)")
            _plan(j, t)
            return out
        if not free:
            return out                  # the box is busy: try again next tick, keep next_run
        out.append((name, trigger, 1))
        if trigger == "catchup" and policy == "all" and missed > 1:
            st["queued"] = min(int(s.get("catchup_max") or 5), missed) - 1
        _plan(j, t)
        if j["schedule"] and S.kind_of(j["schedule"]) == "once":
            st["next_run"] = None
        return out

    def _skip(self, j, st, t, status, why):
        rec = {"run_id": _run_id(j["name"], t), "job": j["name"], "start": t, "end": t, "duration_ms": 0,
               "status": status, "trigger": "schedule", "attempt": 0, "output": why, "bug": None,
               "routed": []}
        _record_run(rec)
        st["last_status"] = status
        self.log(f"[scheduler] {j['name']}: {status} - {why}")

    def _finish(self, j, st, state, why):
        j["enabled"] = False
        st["state"] = state
        st["next_run"] = None
        st["state_reason"] = why
        self.log(f"[scheduler] {j['name']}: {state} ({why})")

    def _start(self, name, trigger, attempt):
        rid = _run_id(name, self.clock())
        with _mutate() as jobs:
            st = jobs[name]["state"]
            for r in st.get("running") or []:
                if r.get("run_id") is None and r.get("pid") == os.getpid():
                    r["run_id"] = rid
                    break
            job = dict(jobs[name])
        if self.threaded:
            th = threading.Thread(target=self._execute, args=(job, trigger, attempt, rid), daemon=True,
                                  name=f"job-{name}")
            with self._lock:
                self.running[rid] = (name, th)
            th.start()
        else:
            done = threading.Event()
            done.set()
            with self._lock:
                self.running[rid] = (name, _Done())
            self._execute(job, trigger, attempt, rid)
        return rid

    # -- one run ------------------------------------------------------------
    def _execute(self, job, trigger, attempt, rid):
        from . import routing
        name = job["name"]
        s = self.cfg()
        t0 = self.clock()
        m0 = time.monotonic()
        timeout = int(job.get("timeout_sec") or s.get("default_timeout_sec") or 600)
        self.log(f"[scheduler] {name}: start ({trigger}{'' if attempt <= 1 else f', attempt {attempt}'})")
        from . import interrupts
        interrupts.mark(interrupts.JOB, name)   # v3.8.4: any job starting ends a running Free time
        res = run_action(job["action_type"], job["action"], self.ctx, job, timeout=timeout)
        dur = int((time.monotonic() - m0) * 1000)
        status = "SUCCEEDED" if res.ok else ("TIMED_OUT" if res.timed_out else "FAILED")
        out_text = res.output.strip()
        h = hashlib.sha256(_normal(out_text).encode("utf-8", "replace")).hexdigest()[:16]
        with _locked():
            prev = (_doc()["jobs"].get(name) or {}).get("state") or {}
        notable = res.notable if res.notable is not None else (not res.ok or h != prev.get("last_output_hash"))
        retry_left = (not res.ok) and attempt <= int(job.get("retry_count") or 0)
        bug = None
        if not res.ok:
            with contextlib.suppress(Exception):
                bug = self.ctx.bug("scheduler", f"job {name} {status}: {_first(out_text)}", f"scheduler.{name}")
        routed = []
        if not retry_left:
            route = job.get("result_to")
            if res.ok and (res.data or {}).get("interrupted") and not (res.data or {}).get("links"):
                # v3.8.4: an interrupted Free time that made nothing to share stays in the log, so
                # SeVin's chat isn't cluttered while he's talking to Quill
                route = {"dest": "log", "when": "always"}
            routed = routing.deliver(route, job, status, out_text, notable, bug, self.ctx,
                                     clock=self.clock)
        rec = {"run_id": rid, "job": name, "start": t0, "end": t0 + dur / 1000.0, "duration_ms": dur,
               "status": status, "trigger": trigger, "attempt": attempt,
               "output": _redact(out_text)[:int(s.get("output_chars") or 1500)], "bug": bug,
               "notable": bool(notable), "routed": routed}
        if res.data and job["action_type"] == "heartbeat":
            rec["report_id"] = (res.data or {}).get("report_id")
        _record_run(rec)
        with _mutate() as jobs:
            j = jobs.get(name)
            if j is not None:
                st = j.setdefault("state", {})
                st["running"] = [r for r in st.get("running") or [] if r.get("run_id") != rid]
                st["last_run"] = t0
                st["last_status"] = status
                st["last_duration_ms"] = dur
                st["run_count"] = int(st.get("run_count") or 0) + 1
                if res.ok:
                    st["failures_in_a_row"] = 0
                    st["last_output_hash"] = h
                else:
                    st["failure_count"] = int(st.get("failure_count") or 0) + 1
                    st["failures_in_a_row"] = int(st.get("failures_in_a_row") or 0) + 1
                    st["last_bug"] = bug
                if retry_left:
                    back = int(job.get("retry_backoff_sec") or 30) * (2 ** (attempt - 1))
                    st["retry_at"] = self.clock() + back
                    st["retry_attempt"] = attempt + 1
                else:
                    st["retry_at"] = None
                    st["retry_attempt"] = None
                if job.get("max_runs") and st["run_count"] >= job["max_runs"] and not retry_left:
                    self._finish(j, st, "COMPLETED", f"reached max_runs {job['max_runs']}")
                elif job.get("max_failures") and st["failures_in_a_row"] >= job["max_failures"] and not retry_left:
                    self._finish(j, st, "BROKEN", f"{st['failures_in_a_row']} failures in a row "
                                                   f"(max_failures {job['max_failures']})")
                elif S.kind_of(j["schedule"]) == "once" and not retry_left and not st.get("queued"):
                    if trigger != "manual":
                        self._finish(j, st, "COMPLETED", "one-off job ran")
        with self._lock:
            self.running.pop(rid, None)
        self.log(f"[scheduler] {name}: {status} in {dur} ms" + (f" (bug {bug})" if bug else "")
                 + (f"; retry {attempt + 1} later" if retry_left else ""))
        return rec

    def run_now(self, name, wait=True):
        """Run a job once now (CLI 'jobs run', Quill's self_jobs run). Obeys
        max_concurrent; ignores enabled and the schedule."""
        with _mutate() as jobs:
            if name not in jobs:
                raise JobError(f"no job named {name!r}")
            st = jobs[name].setdefault("state", {})
            self._reap(name, st)
            if len(st.get("running") or []) >= jobs[name].get("max_concurrent", 1):
                raise JobError(f"{name} is already running (max_concurrent "
                               f"{jobs[name].get('max_concurrent', 1)})")
            st.setdefault("running", []).append({"run_id": None, "since": self.clock(), "pid": os.getpid(),
                                                 "trigger": "manual"})
        if wait:
            keep, self.threaded = self.threaded, False
            try:
                rid = self._start(name, "manual", 1)
            finally:
                self.threaded = keep
            return next((r for r in reversed(history(name, 5)) if r.get("run_id") == rid), None)
        return self._start(name, "manual", 1)

    # -- the loop -------------------------------------------------------------
    def loop(self, stop=None, max_ticks=None):
        stop = stop or threading.Event()
        s = self.cfg()
        with contextlib.suppress(S.ScheduleError):
            S.set_timezone(s.get("timezone") or "")
        self.started = True
        n = 0
        while not stop.is_set():
            try:
                self.tick()
            except Exception as e:  # noqa: BLE001 - a bad tick is logged, the loop goes on
                self.log(f"[scheduler] tick failed: {type(e).__name__}: {e}")
                with contextlib.suppress(Exception):
                    self.ctx.bug("scheduler", f"tick failed: {type(e).__name__}: {e}", "scheduler.tick")
            n += 1
            if max_ticks and n >= max_ticks:
                break
            stop.wait(max(1.0, float(self.cfg().get("tick_sec") or 20)))
        return n


class _Done:
    def is_alive(self):
        return True     # inline: alive until _execute pops it


def _run_id(name, t):
    return f"{name}-{time.strftime('%Y%m%d%H%M%S', time.localtime(t))}-{secrets.token_hex(2)}"


def _first(text):
    return (str(text or "").strip().splitlines() or [""])[0][:200]


def _normal(text):
    """Output without times and numbers that change every run, for the
    'did anything change' (only_if_notable) comparison."""
    t = re.sub(r"\d+(\.\d+)?\s*(ms|s|sec|min|%)\b", "#", str(text))
    t = re.sub(r"\d{4}-\d\d-\d\d[ T]\d\d:\d\d(:\d\d)?", "#", t)
    return re.sub(r"\b(pid|id)\s*\d+", r"\1 #", t)


def _redact(text):
    try:
        from . import bugs
        return bugs.redact(text)
    except Exception:  # noqa: BLE001
        return text


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# one scheduler per box
# ---------------------------------------------------------------------------
class Lock:
    def __init__(self, path=None):
        self.path = path or _p("scheduler.lock")
        self.f = None

    def acquire(self):
        """-> True when this process is now the one scheduler."""
        self.f = open(self.path, "a+")
        if fcntl is None:
            return True
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.f.close()
            self.f = None
            return False
        self.f.seek(0)
        self.f.truncate()
        self.f.write(json.dumps({"pid": os.getpid(), "since": now()}))
        self.f.flush()
        return True

    def release(self):
        if self.f:
            with contextlib.suppress(OSError):
                if fcntl:
                    fcntl.flock(self.f, fcntl.LOCK_UN)
                self.f.close()
            self.f = None


def lock_holder():
    """-> the pid of the running scheduler, or None."""
    p = _p("scheduler.lock")
    if not os.path.exists(p) or fcntl is None:
        return None
    with open(p, "a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.seek(0)
            try:
                return int(json.loads(f.read() or "{}").get("pid") or 0) or -1
            except ValueError:
                return -1
        fcntl.flock(f, fcntl.LOCK_UN)
        return None


def run_forever(log=print, stop=None, ctx=None):
    """`nimlab scheduler run`: the service's scheduler child."""
    s = settings()
    if not s.get("enabled", True):
        log("[scheduler] scheduler_settings.enabled is false; not starting")
        return EXIT_CONFIG
    lk = Lock()
    if not lk.acquire():
        log(f"[scheduler] another scheduler is running (pid {lock_holder()}); this copy exits")
        return EXIT_WAIT
    try:
        sch = Scheduler(ctx=ctx, log=log)
        jobs = load_jobs()
        on = [n for n, j in jobs.items() if j.get("enabled")]
        log(f"[scheduler] running: {len(jobs)} jobs, {len(on)} enabled"
            + (f" ({', '.join(on[:8])})" if on else "") + f"; checks every {s.get('tick_sec')} s")
        sch.loop(stop)
    finally:
        lk.release()
    return 0


# ---------------------------------------------------------------------------
# status lines (CLI, menus, doctor, the heartbeat context)
# ---------------------------------------------------------------------------
def summary(t=None):
    t = now() if t is None else t
    jobs = load_jobs()
    on = {n: j for n, j in jobs.items() if j.get("enabled")}
    nxt = sorted((j["state"].get("next_run"), n) for n, j in on.items() if j["state"].get("next_run"))
    recent = history(n=200)
    since = t - 86400
    fails = [r for r in recent if r.get("status") in ("FAILED", "TIMED_OUT") and float(r.get("start") or 0) >= since]
    return {"jobs": len(jobs), "enabled": len(on), "holder": lock_holder(),
            "next": nxt[0] if nxt else None, "failures_24h": len(fails),
            "heartbeat": bool((jobs.get(HEARTBEAT) or {}).get("enabled")),
            "broken": [n for n, j in jobs.items() if j["state"].get("state") == "BROKEN"]}


def not_running_hint():
    """'' when jobs will fire; else why not and what to do (3.8.2: creating a
    job or turning the heartbeat on used to say nothing when no scheduler ran,
    so nothing ever fired)."""
    if lock_holder():
        return ""
    if not settings().get("enabled", True):
        return "The scheduler is turned off, so jobs will not run. Turn it on: Scheduler menu > Scheduler on/off."
    try:
        from . import service as SV
        if not SV.settings().get("scheduler", True):
            return "The service does not run the scheduler. Turn it on: Scheduler menu > Scheduler on/off."
    except Exception:  # noqa: BLE001
        pass
    return ("The scheduler is not running, so jobs will not run yet. It runs inside the background service: "
            "Scheduler menu > Scheduler on/off starts it (or: nimlab service start).")


def status_line():
    s = summary()
    who = f"running (pid {s['holder']})" if s["holder"] else "not running"
    nxt = f"; next: {s['next'][1]} {S.ago(s['next'][0])}" if s["next"] else ""
    return (f"scheduler {who}; {s['enabled']}/{s['jobs']} jobs enabled; heartbeat "
            f"{'on' if s['heartbeat'] else 'off'}{nxt}; {s['failures_24h']} failed runs in 24 h")


def doctor_lines():
    """[(ok, message)] for nimlab doctor."""
    rows = []
    try:
        s = settings()
        jobs = load_jobs()
    except Exception as e:  # noqa: BLE001
        return [(False, f"scheduler: can't read the jobs ({e})")]
    if s.get("timezone"):
        try:
            S.set_timezone(s["timezone"])
            rows.append((True, f"scheduler time zone {s['timezone']}"))
        except S.ScheduleError as e:
            rows.append((False, f"scheduler: {e}"))
    bad = []
    for n, j in jobs.items():
        why = S.validate(j.get("schedule", ""))
        if why:
            bad.append(f"{n}: {why}")
        if j.get("action_type") == "shell" and j.get("enabled") and not _shell_on():
            bad.append(f"{n}: a shell job, but self-admin shell is off (it will fail)")
    rows.append((not bad, "scheduler jobs look right" if not bad else "scheduler: " + "; ".join(bad[:3])))
    broken = [n for n, j in jobs.items() if (j.get("state") or {}).get("state") == "BROKEN"]
    if broken:
        rows.append((False, f"broken jobs (too many failures, now disabled): {', '.join(broken)}; "
                            "see nimlab jobs history <name>, then nimlab jobs enable <name>"))
    on = [n for n, j in jobs.items() if j.get("enabled")]
    holder = lock_holder()
    if on and not holder:
        rows.append(("warn", f"{len(on)} jobs enabled but the scheduler is not running "
                            "(nimlab service start; or scheduler_settings.enabled)"))
    elif holder:
        rows.append((True, f"scheduler running (pid {holder}), {len(on)} jobs enabled"))
    return rows
