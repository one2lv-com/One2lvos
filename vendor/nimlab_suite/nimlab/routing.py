"""Result routing for jobs and heartbeat actions (v3.8.0).

Each job and each suggested action names where its result goes:

  {"dest": "telegram" | "memory" | "log" | "mcp_tool" | "none",
   "when": "always" | "only_on_failure" | "only_if_notable",
   "tool": "<mcp tool>", "args": {...},          # dest mcp_tool only
   "escalate_on_failure": "telegram" | ...}       # optional second place

  telegram   a message to the Telegram owner
  memory     stored through the memory pipeline (kind 'scheduler')
  log        a line in data/scheduler/results.log (the run history keeps the
             output either way)
  mcp_tool   an MCP tool, e.g. a mail tool. In args, {text}, {subject},
             {job}, {status} and {bug} are filled in.
  none       nothing beyond the run history

'only_if_notable' sends when the run failed, when the action called its
result notable (a failed test, a heartbeat that took an action), or when
the output differs from the last successful run's output.

A short form is accepted anywhere: "telegram", "memory:only_if_notable",
"mcp_tool:mail_send", "log".
"""

import json
import time

DESTS = ("telegram", "memory", "log", "mcp_tool", "none")
WHEN = ("always", "only_on_failure", "only_if_notable")


class RouteError(ValueError):
    pass


def default_for(action_type):
    if action_type in ("test", "nimlab_command", "shell", "chain"):
        return {"dest": "telegram", "when": "only_on_failure"}
    return {"dest": "log", "when": "always"}


def parse_short(text):
    t = str(text or "").strip()
    if not t:
        return {}
    if t.startswith("{"):
        try:
            return json.loads(t)
        except ValueError as e:
            raise RouteError(f"result_to is not JSON ({e})") from None
    parts = [p.strip() for p in t.split(":")]
    out = {"dest": parts[0].lower()}
    for p in parts[1:]:
        if p.lower() in WHEN:
            out["when"] = p.lower()
        elif out["dest"] == "mcp_tool" and p:
            out["tool"] = p
        elif p:
            raise RouteError(f"result_to: {p!r} is not one of {', '.join(WHEN)}")
    return out


def normalize(spec, default=None):
    """-> a clean routing dict. Raises scheduler.JobError on a bad one."""
    from .scheduler import JobError
    try:
        r = parse_short(spec) if isinstance(spec, str) else dict(spec or {})
    except RouteError as e:
        raise JobError(str(e)) from None
    if not r:
        r = dict(default or {"dest": "log", "when": "always"})
    dest = str(r.get("dest") or "log").lower()
    if dest not in DESTS:
        raise JobError(f"result_to dest must be one of {', '.join(DESTS)}")
    when = str(r.get("when") or "always").lower()
    if when not in WHEN:
        raise JobError(f"result_to when must be one of {', '.join(WHEN)}")
    out = {"dest": dest, "when": when}
    if dest == "mcp_tool":
        if not str(r.get("tool") or "").strip():
            raise JobError("result_to mcp_tool needs a tool name, e.g. mcp_tool:charlie_mail")
        out["tool"] = str(r["tool"]).strip()
        args = r.get("args") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError as e:
                raise JobError(f"result_to args are not JSON ({e})") from None
        if not isinstance(args, dict):
            raise JobError("result_to args must be a JSON object")
        out["args"] = args
    esc = r.get("escalate_on_failure")
    if esc:
        esc = str(esc).lower()
        if esc not in DESTS or esc in ("none", "mcp_tool"):
            raise JobError("escalate_on_failure must be telegram, memory or log")
        out["escalate_on_failure"] = esc
    return out


def describe(r):
    if not r:
        return "log"
    s = r.get("dest", "log")
    if s == "mcp_tool":
        s += f" {r.get('tool')}"
    if r.get("when", "always") != "always":
        s += f" ({r['when'].replace('_', ' ')})"
    if r.get("escalate_on_failure"):
        s += f", failures also to {r['escalate_on_failure']}"
    return s


def should_send(when, ok, notable):
    if when == "only_on_failure":
        return not ok
    if when == "only_if_notable":
        return (not ok) or bool(notable)
    return True


def message(job_name, status, text, bug=None, title=None):
    head = title or f"[Nim Lab] {job_name}: {status}" + (f" (bug {bug})" if bug else "")
    body = str(text or "").strip()
    if len(body) > 3000:
        body = body[:3000] + " ..."
    return head + ("\n" + body if body else "")


def _fill(obj, vals):
    if isinstance(obj, str):
        out = obj
        for k, v in vals.items():
            out = out.replace("{" + k + "}", str(v if v is not None else ""))
        return out
    if isinstance(obj, dict):
        return {k: _fill(v, vals) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fill(v, vals) for v in obj]
    return obj


def send_to(dest, r, job_name, status, text, bug, ctx, clock=time.time, title=None):
    """Deliver to one destination. -> 'dest: ok' / 'dest: failed (why)'."""
    from . import scheduler as SC
    msg = message(job_name, status, text, bug, title)
    try:
        if dest == "none":
            return "none"
        if dest == "log":
            with open(SC._p("results.log"), "a", encoding="utf-8") as f:
                f.write(f"{SC.S.fmt(clock())} {msg}\n---\n")
            return "log: ok"
        if dest == "telegram":
            ok, why = ctx.telegram(msg)
            return "telegram: ok" if ok else f"telegram: failed ({why})"
        if dest == "memory":
            ok, why = ctx.memory_store(msg, {"source": "scheduler", "job": job_name, "status": status})
            return "memory: ok" if ok else f"memory: failed ({why})"
        if dest == "mcp_tool":
            vals = {"text": msg, "subject": msg.splitlines()[0], "job": job_name, "status": status, "bug": bug}
            args = _fill((r or {}).get("args") or {"text": "{text}"}, vals)
            ok, why = ctx.mcp_call(r.get("tool"), args)
            return f"mcp_tool {r.get('tool')}: ok" if ok else f"mcp_tool {r.get('tool')}: failed ({str(why)[:120]})"
    except Exception as e:  # noqa: BLE001 - routing never breaks a run
        return f"{dest}: failed ({type(e).__name__}: {str(e)[:120]})"
    return f"{dest}: unknown"


def deliver(r, job, status, text, notable, bug, ctx, clock=time.time, title=None):
    """Route one result. -> the list of deliveries made. A telegram or
    mcp_tool delivery that fails falls back to the log, so nothing is lost."""
    r = r or {"dest": "log", "when": "always"}
    ok = status == "SUCCEEDED"
    name = (job or {}).get("name", "job")
    out = []
    if should_send(r.get("when", "always"), ok, notable):
        res = send_to(r.get("dest", "log"), r, name, status, text, bug, ctx, clock, title)
        out.append(res)
        if "failed" in res and r.get("dest") != "log":
            out.append(send_to("log", r, name, status, f"(could not deliver to {r.get('dest')}: {res})\n{text}",
                               bug, ctx, clock, title))
    esc = r.get("escalate_on_failure")
    if not ok and esc and esc != r.get("dest"):
        out.append("escalated " + send_to(esc, r, name, status, text, bug, ctx, clock, title))
    return out
