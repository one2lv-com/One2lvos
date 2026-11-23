"""`nimlab jobs`, `nimlab heartbeat`, `nimlab scheduler` and the launcher's
Scheduler menu (v3.8.0)."""

import json
import sys

from . import heartbeat as HB
from . import routing
from . import schedule as S
from . import scheduler as SC

JOB_ACTIONS = ["list", "show", "create", "edit", "run", "enable", "disable", "delete", "history", "next", "audit",
               "tools", "free-time"]
HB_ACTIONS = ["status", "run-now", "enable", "disable", "schedule", "actions", "reports", "set"]
ACT_SUB = ["list", "show", "add", "edit", "remove", "enable", "disable"]
HB_SETTINGS = ("max_actions", "token_budget", "time_budget_sec", "escalate_failures_to", "context_chars")


def _out(*a, **k):
    """print() for the jobs / heartbeat / scheduler commands: coloured on a
    terminal like the older screens (3.8.1), unchanged when colour is off."""
    from . import paint
    k.pop("flush", None)
    paint.out(" ".join(str(x) for x in a))


def paint_kv(ln):
    from . import paint
    return paint.auto(ln)


def job_screen(j, num=None):
    """job_line laid out for the terminal: one line when it fits the screen,
    else two (name and type, then next / last / schedule), coloured."""
    from . import colors as C, paint
    line = job_line(j)
    if num is not None:
        line = f"{num:>3})" + line[1:]
    w = C.screen_width()
    if not C.enabled() or len(line) <= w:
        return [paint.job_line(line)]
    st = j.get("state") or {}
    state = "on " if j.get("enabled") else ("BRK" if st.get("state") == "BROKEN" else "off")
    head = (f"{num:>3})" if num is not None else " ") + f" [{state}] {j['name']} ({j['action_type']})"
    nxt = S.fmt(st.get("next_run")) if st.get("next_run") else "-"
    tail = f"       next {nxt}  last {st.get('last_status') or '-'}  {S.describe(j['schedule'])}"
    import re
    tail = re.sub(r"\b(next|last)\b", lambda m: C.dim(m.group(1)), paint.status_line(tail[:w]))
    return [paint.job_line(head[:w]), tail]


def action_screen(x, num=None):
    from . import colors as C, paint
    line = action_line(x)
    if num is not None:
        line = f"{num:>3})" + line[1:]
    w = C.screen_width()
    if not C.enabled() or len(line) <= w:
        return [paint.job_line(line)]
    head = (f"{num:>3})" if num is not None else " ") + \
        f" [{'on ' if x.get('enabled') else 'off'}] p{x.get('priority')} {x['name']} -> " \
        f"{routing.describe(x.get('result_to'))}"
    tail = "       " + (x.get("instruction", "") or "")
    return [paint.job_line(head[:w]), C.dim(tail[:w])]


def _short(d, n=70):
    d = " ".join(str(d or "").split())
    return d if len(d) <= n else d[:n - 1] + "…"


def pick_tools(q, say, tools, chosen=None, page_size=10):
    """Numbered, paged multi-select over the live MCP tool list.
    Type numbers (1,3,5-7) to toggle, n/p to page, /word to filter,
    a to clear the filter, d when done, b to cancel. -> [names] or None."""
    from . import colors as C
    names = [t.get("name") for t in tools if t.get("name")]
    desc = {t.get("name"): t.get("description") for t in tools}
    chosen = [n for n in (chosen or [])]
    flt, page = "", 0
    while True:
        view = [n for n in names if flt.lower() in (n + " " + str(desc.get(n) or "")).lower()]
        pages = max(1, (len(view) + page_size - 1) // page_size)
        page = min(max(page, 0), pages - 1)
        say("")
        say(C.header(f"PICK TOOLS  page {page + 1}/{pages}" + (f"  filter '{flt}'" if flt else "")))
        for i in range(page * page_size, min(len(view), (page + 1) * page_size)):
            n = view[i]
            mark = "[x]" if n in chosen else "[ ]"
            say(f"  {i + 1:>3}) {mark} {n}  {C.dim(_short(desc.get(n), 50))}")
        if not view:
            say("  (no tools match)")
        say("  chosen: " + (", ".join(chosen) or "none"))
        c = q("Numbers to toggle (1,3,5-7)  n) next  p) prev  /word) filter  a) all  d) done  b) cancel: ")
        if c is None or c in ("b", "q"):
            return None
        if c in ("d", ""):
            return chosen
        if c == "n":
            page += 1
        elif c == "p":
            page -= 1
        elif c == "a":
            flt, page = "", 0
        elif c.startswith("/"):
            flt, page = c[1:].strip(), 0
        else:
            for part in c.replace(" ", "").split(","):
                lo, _, hi = part.partition("-")
                if not lo.isdigit() or (hi and not hi.isdigit()):
                    continue
                for k in range(int(lo), int(hi or lo) + 1):
                    if 1 <= k <= len(view):
                        n = view[k - 1]
                        if n in chosen:
                            chosen.remove(n)
                        else:
                            chosen.append(n)


def _new_task(q, say, name=None, sched=None, template=False):
    """Scheduler menu: a prompt task with tools, step by step."""
    from . import colors as C
    try:
        tools = SC.live_mcp_tools()
    except SC.JobError as e:
        say(f"[x] {e}")
        return None
    if not tools:
        say("[x] The MCP server offers no tools right now. Turn some on in its admin console.")
        return None
    if template:
        say(C.dim("Free time: every hour Quill picks one of the tools you choose, plays with it and tells you "
                  "what it did."))
    name = name or q(f"Name [{'free-time' if template else ''}]: ") or ("free-time" if template else "")
    if not name:
        return None
    if not template and not sched:
        say("Schedule: FREQ=HOURLY;INTERVAL=1, FREQ=DAILY;BYHOUR=7, '*/30 * * * *' or 'at 2026-11-14 07:00'.")
        sched = q("Schedule: ")
        why = S.validate(sched or "")
        if why:
            say(f"[x] {why}")
            return None
    say("Choose the tools for this job:")
    picked = pick_tools(q, say, tools)
    if picked is None:
        say("Cancelled.")
        return None
    if template:
        spec = SC.free_time_template(picked, name=name)
        if not picked:
            say("[x] pick at least one tool for Free time")
            return None
    else:
        prompt = q("Prompt (what Quill should do): ")
        if not prompt:
            return None
        say(C.entry(1, "Only these tools", "(default)", pad=20))
        say(C.entry(2, "Any tool", "these preferred", pad=20))
        only = (q("Tool access [1]: ") or "1") != "2"
        req = (q("Fail the run if Quill calls no tool? [y/N] ") or "").lower() in ("y", "yes")
        spec = {"name": name, "schedule": sched, "action_type": "quill_task",
                "action": {"prompt": prompt, "tools": picked, "only": only, "require_tool": req}}
    dest = q(f"Result to (telegram, memory, log, none) [{'telegram' if template else 'log'}]: ")
    if dest:
        spec["result_to"] = dest
    elif not template:
        spec["result_to"] = None
    j = SC.create_job(spec, who="menu", source="cli")
    say(f"[ok] created {j['name']}: {S.describe(j['schedule'])}; tools {', '.join(picked) or 'any'}; "
        f"next run {S.fmt(j['state'].get('next_run'))}")
    hint = SC.not_running_hint() if j.get("enabled") else ""
    if hint:
        say("    " + hint)
    return j


def _tz():
    try:
        S.set_timezone(SC.settings().get("timezone") or "")
    except S.ScheduleError as e:
        _out(f"[!] {e}")


def job_line(j):
    st = j.get("state") or {}
    state = "on " if j.get("enabled") else ("BRK" if st.get("state") == "BROKEN" else "off")
    nxt = S.fmt(st.get("next_run")) if st.get("next_run") else "-"
    last = f"{st.get('last_status') or '-'}"
    return f"  [{state}] {j['name']:<22} {j['action_type']:<14} next {nxt:<16} last {last:<9} {S.describe(j['schedule'])}"


def show_lines(j):
    st = j.get("state") or {}
    act = j.get("action")
    act_s = json.dumps(act, ensure_ascii=False) if isinstance(act, (dict, list)) else str(act or "-")
    if j.get("action_type") == "quill_task" and isinstance(act, dict):
        act_s = SC.task_brief(act)
    out = [f"{j['name']}: {j.get('description') or ''}".rstrip(": "),
           f"  enabled      : {'yes' if j.get('enabled') else 'no'} (state {st.get('state') or '-'}"
           + (f": {st['state_reason']}" if st.get("state_reason") else "") + ")",
           f"  schedule     : {j['schedule']}  ({S.describe(j['schedule'])})",
           f"  next run     : {S.fmt(st.get('next_run'), True)} ({S.ago(st.get('next_run'))})" if st.get("next_run")
           else "  next run     : -",
           f"  action       : {j['action_type']}: {act_s[:300]}",
           f"  result to    : {routing.describe(j.get('result_to'))}",
           f"  start / end  : {S.fmt(j.get('start_date'))} / {S.fmt(j.get('end_date'))}",
           f"  limits       : max_runs {j.get('max_runs') or '-'}, max_failures {j.get('max_failures') or '-'}, "
           f"timeout {j.get('timeout_sec') or 'default'} s, max_concurrent {j.get('max_concurrent', 1)}, "
           f"overlap {j.get('overlap')}, catchup {j.get('catchup') or 'default'}",
           f"  retries      : {j.get('retry_count', 0)} (backoff {j.get('retry_backoff_sec', 30)} s, doubling)",
           f"  runs         : {st.get('run_count', 0)} ({st.get('failure_count', 0)} failed); last "
           f"{S.fmt(st.get('last_run'))} {st.get('last_status') or ''}"
           + (f" bug {st['last_bug']}" if st.get("last_bug") and st.get("last_status") != "SUCCEEDED" else ""),
           f"  owner        : {j.get('owner')} (made by {j.get('created_by')})"]
    return out


def run_line(r):
    out = SC._first(r.get("output"))
    return (f"  {S.fmt(r.get('start'))}  {r.get('job', ''):<18} {r.get('status', ''):<9} "
            f"{int(r.get('duration_ms') or 0) / 1000:>6.1f} s  {r.get('trigger', '')}"
            + (f" #{r['attempt']}" if (r.get("attempt") or 1) > 1 else "")
            + (f"  bug {r['bug']}" if r.get("bug") else "") + (f"  {out[:90]}" if out else ""))


def spec_from_args(a, partial=False):
    m = {"schedule": a.schedule, "action_type": a.type, "action": a.do, "description": a.description,
         "result_to": a.result_to, "retry_count": a.retries, "retry_backoff_sec": a.backoff,
         "timeout_sec": a.timeout, "max_runs": a.max_runs, "max_failures": a.max_failures,
         "start_date": a.start, "end_date": a.end, "overlap": a.overlap, "catchup": a.catchup,
         "max_concurrent": a.max_concurrent, "owner": a.owner}
    if a.disabled:
        m["enabled"] = False
    elif a.enabled:
        m["enabled"] = True
    m = {k: v for k, v in m.items() if v is not None}
    if a.json:
        try:
            m.update(json.loads(a.json))
        except ValueError as e:
            raise SC.JobError(f"--json is not JSON ({e})") from None
    task = task_from_args(a, m)
    if task is not None:
        m["action"] = task
        m.setdefault("action_type", "quill_task")
    if not partial:
        m.setdefault("action_type", "quill_prompt")
    return m


def task_from_args(a, m, existing=None):
    """--tools / --any-tool / --only-tools / --require-tool for quill_task.
    On edit the job's current task is the base. -> dict or None."""
    tools = getattr(a, "tools", None)
    flags = {"only": False if getattr(a, "any_tool", False) else (True if getattr(a, "only_tools", False) else None),
             "require_tool": True if getattr(a, "require_tool", False) else
             (False if getattr(a, "no_require_tool", False) else None)}
    is_task = m.get("action_type") == "quill_task" or tools is not None or any(v is not None for v in flags.values())
    if not is_task:
        return None
    base = {}
    if existing is None and getattr(a, "name", None) and getattr(a, "action", "") == "edit":
        try:
            cur = SC.get_job(a.name)
            if cur.get("action_type") == "quill_task" and isinstance(cur.get("action"), dict):
                base = dict(cur["action"])
        except SC.JobError:
            pass
    act = m.get("action")
    if isinstance(act, dict):
        base.update(act)
    elif isinstance(act, str) and act.strip():
        if act.strip().startswith("{"):
            base.update(SC.check_task(act))
        else:
            base["prompt"] = act.strip()
    if tools is not None:
        base["tools"] = SC._split_tools(tools)
    for k, v in flags.items():
        if v is not None:
            base[k] = v
    return base


def _confirm(a, q):
    if getattr(a, "yes", False) or not sys.stdin.isatty():
        return True
    return input(f"{q} [y/N] ").strip().lower() in ("y", "yes")


def cmd_jobs(a):
    _tz()
    act = a.action
    try:
        if act == "list":
            jobs = SC.load_jobs()
            _out(f"Jobs ({len(jobs)}), times in {S.timezone_name()}:")
            for n in sorted(jobs, key=lambda n: (n != SC.HEARTBEAT, n)):
                for ln in job_screen(jobs[n]):
                    print(ln)
            _out("  " + SC.status_line())
            return 0
        if act == "audit":
            for r in SC.audit_tail(a.n or 20, a.name):
                _out(f"  {r.get('at')}  {r.get('who')} via {r.get('source')}: {r.get('op')} {r.get('kind')} "
                      f"{r.get('name')}  {json.dumps(r.get('before'), default=str)[:80]} -> "
                      f"{json.dumps(r.get('after'), default=str)[:80]}")
            return 0
        if act == "history":
            rows = SC.history(a.name, a.n or 20, a.status)
            if not rows:
                _out("(no runs yet)")
            for r in rows:
                _out(run_line(r))
            return 0
        if act == "tools":
            tools = SC.live_mcp_tools()
            _out(f"MCP tools the server offers now ({len(tools)}); pick them with --tools a,b:")
            for i, t in enumerate(tools, 1):
                _out(f"  {i:>3}) {t.get('name')}  {_short(t.get('description'))}")
            return 0
        if act == "free-time":
            tools = SC._split_tools(getattr(a, "tools", None))
            if not tools:
                _out("usage: nimlab jobs free-time [name] --tools tool_a,tool_b [--result-to telegram]"
                     "  (see: nimlab jobs tools)")
                return 2
            spec = SC.free_time_template(tools, name=a.name or "free-time")
            if a.result_to:
                spec["result_to"] = a.result_to
            if a.schedule:
                spec["schedule"] = a.schedule
            j = SC.create_job(spec, who="cli", source="cli")
            _out(f"[ok] created {j['name']}: {S.describe(j['schedule'])}, tools {', '.join(tools)}; next run "
                 f"{S.fmt(j['state'].get('next_run'))}")
            hint = SC.not_running_hint() if j.get("enabled") else ""
            if hint:
                _out("    " + hint)
            return 0
        if not a.name:
            _out(f"usage: nimlab jobs {act} <name>")
            return 2
        if act == "show":
            from . import colors as C
            for i, ln in enumerate(show_lines(SC.get_job(a.name))):
                print(C.section(ln) if i == 0 and C.enabled() else paint_kv(ln))
            _out("  recent runs:")
            for r in SC.history(a.name, 5):
                _out("  " + run_line(r))
            return 0
        if act == "next":
            nx = SC.next_runs(a.name, a.n or 5)
            _out(f"{a.name}: " + (", ".join(S.fmt(t) for t in nx) if nx else "no runs ahead (disabled or ended)"))
            return 0
        if act == "create":
            spec = spec_from_args(a)
            spec["name"] = a.name
            j = SC.create_job(spec, who="cli", source="cli")
            _out(f"[ok] created {j['name']}: {S.describe(j['schedule'])}; next run "
                  f"{S.fmt(j['state'].get('next_run'))}")
            hint = SC.not_running_hint() if j.get("enabled") else ""
            if hint:
                _out("    " + hint)
            return 0
        if act == "edit":
            j = SC.update_job(a.name, spec_from_args(a, partial=True), who="cli", source="cli")
            _out(f"[ok] {j['name']} changed; next run {S.fmt(j['state'].get('next_run'))}")
            return 0
        if act in ("enable", "disable"):
            j = SC.set_enabled(a.name, act == "enable", who="cli", source="cli")
            _out(f"[ok] {a.name} {act}d" + (f"; next run {S.fmt(j['state'].get('next_run'))}"
                                             if j.get("enabled") else ""))
            return 0
        if act == "delete":
            if not _confirm(a, f"Delete job {a.name} (its run history stays)?"):
                _out("Not deleted.")
                return 1
            SC.delete_job(a.name, who="cli", source="cli")
            _out(f"[ok] deleted {a.name}")
            return 0
        if act == "run":
            _out(f"Running {a.name} now ...")
            r = SC.Scheduler(log=print).run_now(a.name)
            if r:
                _out(run_line(r))
                if r.get("output"):
                    _out(r["output"])
                if r.get("routed"):
                    _out("result: " + ", ".join(r["routed"]))
            return 0 if r and r.get("status") == "SUCCEEDED" else 1
    except SC.JobError as e:
        _out(f"[x] {e}")
        return 2
    return 2


def action_line(x):
    return (f"  [{'on ' if x.get('enabled') else 'off'}] p{x.get('priority')} {x['name']:<18} -> "
            f"{routing.describe(x.get('result_to')):<28} {x.get('instruction', '')[:70]}")


def cmd_heartbeat(a):
    _tz()
    act = a.action
    try:
        if act == "status":
            for ln in HB.status_lines():
                _out(ln)
            return 0
        if act in ("enable", "disable"):
            j = SC.set_enabled(SC.HEARTBEAT, act == "enable", who="cli", source="cli")
            _out(f"[ok] heartbeat {act}d" + (f" ({S.describe(j['schedule'])}); next "
                                              f"{S.fmt(j['state'].get('next_run'))}" if j.get("enabled") else ""))
            if j.get("enabled") and SC.not_running_hint():
                _out("    " + SC.not_running_hint())
            return 0
        if act == "schedule":
            if not a.rest:
                _out('usage: nimlab heartbeat schedule "FREQ=MINUTELY;INTERVAL=30"   (or a cron like "*/30 * * * *")')
                return 2
            j = SC.update_job(SC.HEARTBEAT, {"schedule": " ".join(a.rest)}, who="cli", source="cli")
            _out(f"[ok] heartbeat: {S.describe(j['schedule'])}; next {S.fmt(j['state'].get('next_run'))}")
            return 0
        if act == "run-now":
            _out("Heartbeat now (Quill decides; this sends real requests) ...")
            r = SC.Scheduler(log=lambda *x: None).run_now(SC.HEARTBEAT)
            _out((r or {}).get("output") or "(no report)")
            return 0 if r and r.get("status") == "SUCCEEDED" else 1
        if act == "reports":
            for rep in HB.reports(a.n or 5):
                _out(f"{rep.get('at')}:")
                for ln in HB.report_text(rep).splitlines():
                    _out("  " + ln)
            return 0
        if act == "set":
            if len(a.rest) != 2 or a.rest[0] not in HB_SETTINGS:
                _out(f"usage: nimlab heartbeat set <{'|'.join(HB_SETTINGS)}> <value>")
                return 2
            k, v = a.rest
            from . import config
            doc = config.load_json(config.CLUSTER_CONFIG, {}) or {}
            hs = doc.setdefault("heartbeat_settings", {})
            hs[k] = v if k == "escalate_failures_to" else int(v)
            if k == "escalate_failures_to" and v not in ("", "telegram", "memory", "log"):
                _out("[x] escalate_failures_to: telegram, memory, log or ''")
                return 2
            config.save_json(config.CLUSTER_CONFIG, doc)
            _out(f"[ok] heartbeat_settings.{k} = {hs[k]}")
            return 0
        if act == "actions":
            return cmd_actions(a)
    except (SC.JobError, ValueError) as e:
        _out(f"[x] {e}")
        return 2
    return 2


def cmd_actions(a):
    sub = (a.rest[0] if a.rest else "list").lower()
    name = a.rest[1] if len(a.rest) > 1 else None
    if sub not in ACT_SUB:
        _out(f"usage: nimlab heartbeat actions {'|'.join(ACT_SUB)} [name] [--instruction ...]")
        return 2
    if sub == "list":
        acts = HB.load_actions()
        _out(f"Suggested actions ({len(acts)}):")
        for x in sorted(acts, key=lambda x: (x.get("priority", 3), x["name"])):
            for ln in action_screen(x):
                print(ln)
        return 0
    if not name:
        _out(f"usage: nimlab heartbeat actions {sub} <name>")
        return 2
    fields = {"instruction": a.instruction, "condition": a.condition, "priority": a.priority,
              "result_to": a.result_to, "run": a.run}
    fields = {k: v for k, v in fields.items() if v is not None}
    if sub == "show":
        x = HB.get_action(name)
        for k in ("name", "instruction", "condition", "priority", "enabled", "run", "created_by"):
            _out(f"  {k:<12}: {x.get(k)}")
        _out(f"  {'result_to':<12}: {routing.describe(x.get('result_to'))}")
        return 0
    if sub == "add":
        x = HB.add_action(dict(fields, name=name), who="cli", source="cli")
        _out("[ok] added\n" + action_line(x))
        return 0
    if sub in ("enable", "disable"):
        fields = {"enabled": sub == "enable"}
    if sub in ("edit", "enable", "disable"):
        x = HB.edit_action(name, fields, who="cli", source="cli")
        _out("[ok] changed\n" + action_line(x))
        return 0
    if sub == "remove":
        if not _confirm(a, f"Remove suggested action {name}?"):
            _out("Not removed.")
            return 1
        HB.remove_action(name, who="cli", source="cli")
        _out(f"[ok] removed {name}")
        return 0
    return 2


def cmd_scheduler(a):
    _tz()
    if a.action == "run":
        from . import config
        return SC.run_forever(log=lambda m: print(f"{config.timestamp()} {m}", flush=True))
    if a.action == "status":
        _out(SC.status_line())
        for ok, msg in SC.doctor_lines():
            _out(("  [ok] " if ok is True else "  [!]  ") + msg)
        return 0
    if a.action == "menu":
        return menu()
    return 2


def add_parsers(sub):
    p = sub.add_parser("jobs", help="Scheduler jobs (like Oracle DBMS_SCHEDULER): list, create, run, history")
    p.add_argument("action", nargs="?", default="list", choices=JOB_ACTIONS)
    p.add_argument("name", nargs="?", help="the job name")
    p.add_argument("--schedule", help='FREQ=MINUTELY;INTERVAL=30 | "*/30 * * * *" | "at 2026-11-14 07:00"')
    p.add_argument("--type", choices=SC.USER_ACTION_TYPES, help="action type (default quill_prompt)")
    p.add_argument("--do", help="the action: a prompt, a command, test names, '<tool> <json args>', or chain JSON")
    p.add_argument("--description")
    p.add_argument("--tools", help="quill_task: the MCP tools for the job, comma-separated (see: nimlab jobs tools)")
    p.add_argument("--any-tool", action="store_true", help="quill_task: Quill may use any tool (these preferred)")
    p.add_argument("--only-tools", action="store_true", help="quill_task: only the picked tools (the default)")
    p.add_argument("--require-tool", action="store_true",
                   help="quill_task: the run fails if Quill calls no tool")
    p.add_argument("--no-require-tool", action="store_true", help="quill_task: turn --require-tool off")
    p.add_argument("--result-to", help="telegram | memory | log | none | mcp_tool:<tool>, optionally "
                                       ":only_on_failure or :only_if_notable")
    p.add_argument("--retries", type=int)
    p.add_argument("--backoff", type=int, help="seconds before the first retry (doubles each time)")
    p.add_argument("--timeout", type=int, help="seconds")
    p.add_argument("--max-runs", type=int)
    p.add_argument("--max-failures", type=int, help="disable (BROKEN) after this many failures in a row")
    p.add_argument("--start", help="start date, local: YYYY-MM-DD HH:MM")
    p.add_argument("--end", help="end date, local: YYYY-MM-DD HH:MM")
    p.add_argument("--overlap", choices=SC.OVERLAP)
    p.add_argument("--catchup", choices=SC.CATCHUP)
    p.add_argument("--max-concurrent", type=int)
    p.add_argument("--owner")
    p.add_argument("--json", help="any job fields as JSON")
    p.add_argument("--enabled", action="store_true")
    p.add_argument("--disabled", action="store_true", help="create it disabled")
    p.add_argument("--status", help="history: only SUCCEEDED, FAILED, TIMED_OUT, SKIPPED or MISSED")
    p.add_argument("-n", type=int, help="history / next / audit: how many")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_jobs)

    p = sub.add_parser("heartbeat", help="The heartbeat: Quill wakes up and takes the suggested actions worth doing")
    p.add_argument("action", nargs="?", default="status", choices=HB_ACTIONS)
    p.add_argument("rest", nargs="*", help="schedule: the schedule; actions: list|show|add|edit|remove|enable|"
                                           "disable [name]; set: <setting> <value>")
    p.add_argument("--instruction", help="actions add/edit: what to do")
    p.add_argument("--condition", help="actions add/edit: when it is worth doing")
    p.add_argument("--priority", type=int, help="actions add/edit: 1 (first) to 9")
    p.add_argument("--result-to", help="actions add/edit: telegram | memory | log | none | mcp_tool:<tool>[:when]")
    p.add_argument("--run", help='actions add/edit: run directly instead of a Quill turn, e.g. "test service,tunnel"')
    p.add_argument("-n", type=int, help="reports: how many")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_heartbeat)

    p = sub.add_parser("scheduler", help="The job scheduler process (the service runs it) and its status")
    p.add_argument("action", nargs="?", default="status", choices=["status", "run", "menu"])
    p.set_defaults(fn=cmd_scheduler)


# ---------------------------------------------------------------------------
# the launcher's Scheduler menu
# ---------------------------------------------------------------------------
def menu(ask=input, say=print):
    from . import colors as C, paint
    _tz()
    say = paint.wrap_say(say)

    def q(p, default=""):
        try:
            v = ask(paint.ask(paint.keys(p)))
        except EOFError:
            return None
        return (v if v is not None else default).strip()
    while True:
        say("")
        say(C.header("SCHEDULER"))
        say(C.rule(min(50, C.screen_width())))
        st = SC.status_line()
        if C.enabled():
            import textwrap
            for ln in textwrap.wrap(st, C.screen_width() - 2):
                say("  " + ln)
        else:
            say("  " + st)
        say(C.section("Jobs"))
        say(C.entry(1, "Jobs", "list, run, enable", pad=20))
        say(C.entry(2, "Run history", "last 25 runs", pad=20))
        say(C.entry(5, "New job", "", pad=20))
        say(C.entry(7, "Prompt task + tools", "pick the MCP tools", pad=20))
        say(C.entry(8, "Free time job", "ready-made, hourly", pad=20))
        say(C.entry(6, "Audit", "changes to jobs and actions", pad=20))
        say(C.section("Heartbeat"))
        say(C.entry(3, "Heartbeat", "on / off, run now", pad=20))
        say(C.entry(4, "Suggested actions", "what Quill may do", pad=20))
        say(C.entry(0, "Back"))
        c = q("\nSelection: ")
        if c in (None, "", "b", "q", "0"):
            return 0
        try:
            if c == "1":
                _jobs_menu(q, say)
            elif c == "2":
                rows = SC.history(n=25)
                for r in rows or [{"output": "(no runs yet)"}]:
                    say(run_line(r) if r.get("job") else "  (no runs yet)")
            elif c == "3":
                _hb_menu(q, say)
            elif c == "4":
                _actions_menu(q, say)
            elif c == "5":
                _new_job(q, say)
            elif c == "7":
                _after_create(q, say, _new_task(q, say))
            elif c == "8":
                _after_create(q, say, _new_task(q, say, template=True))
            elif c == "6":
                for r in SC.audit_tail(20):
                    say(f"  {r.get('at')}  {r.get('who')} via {r.get('source')}: {r.get('op')} {r.get('kind')} "
                        f"{r.get('name')}")
        except SC.JobError as e:
            say(f"[x] {e}")


def _jobs_menu(q, say):
    from . import colors as C
    while True:
        jobs = SC.load_jobs()
        names = sorted(jobs, key=lambda n: (n != SC.HEARTBEAT, n))
        say("")
        say(C.header("JOBS"))
        for i, n in enumerate(names, 1):
            for ln in job_screen(jobs[n], i):
                say(ln)
        c = q("Job number (b = back): ")
        if c in (None, "", "b", "q"):
            return
        if not (c.isdigit() and 1 <= int(c) <= len(names)):
            continue
        n = names[int(c) - 1]
        for ln in show_lines(jobs[n]):
            say(ln)
        a = q("r) run now  e) enable  d) disable  h) history  x) next runs  del) delete  b) back: ")
        if a == "r":
            r = SC.Scheduler(log=say).run_now(n)
            if r:
                say(run_line(r))
                say(r.get("output") or "")
        elif a in ("e", "d"):
            SC.set_enabled(n, a == "e", who="menu", source="cli")
            say(f"[ok] {n} {'enabled' if a == 'e' else 'disabled'}")
        elif a == "h":
            for r in SC.history(n, 15):
                say(run_line(r))
        elif a == "x":
            say(", ".join(S.fmt(t) for t in SC.next_runs(n, 5)) or "no runs ahead")
        elif a == "del":
            if (q(f"Delete {n}? [y/N] ") or "").lower() in ("y", "yes"):
                SC.delete_job(n, who="menu", source="cli")
                say(f"[ok] deleted {n}")


def _after_create(q, say, j):
    """Next steps on the result screen: run it now or go back."""
    if not j:
        return
    c = q("r) run it now  b) back: ")
    if c == "r":
        r = SC.Scheduler(log=say).run_now(j["name"])
        if r:
            say(run_line(r))
            say(r.get("output") or "")


def _new_job(q, say):
    name = q("Name (letters, digits, - _ .): ")
    if not name:
        return
    say("Schedule: an Oracle calendar string (FREQ=MINUTELY;INTERVAL=30, FREQ=DAILY;BYHOUR=7), a cron")
    say("('*/30 * * * *') or a one-off ('at 2026-11-14 07:00').")
    sched = q("Schedule: ")
    why = S.validate(sched or "")
    if why:
        say(f"[x] {why}")
        return
    say(f"   {S.describe(sched)}")
    say("Type: " + ", ".join(f"{i}) {t}" for i, t in enumerate(SC.USER_ACTION_TYPES, 1)))
    t = q("Type [1]: ") or "1"
    at = SC.USER_ACTION_TYPES[int(t) - 1] if t.isdigit() and 1 <= int(t) <= len(SC.USER_ACTION_TYPES) else t
    if at == "quill_task":
        _new_task(q, say, name=name, sched=sched)
        return
    hint = {"quill_prompt": "the prompt for Quill", "quill_task": "the prompt for Quill", "nimlab_command": "a nimlab command, e.g. test service",
            "test": "test names, e.g. service,tunnel", "mcp_tool": "<tool> <json args>",
            "shell": "the shell command", "chain": "chain JSON (see the README)"}.get(at, "the action")
    action = q(f"Action ({hint}): ")
    dest = q("Result to (telegram, memory, log, none, mcp_tool:<tool>; add :only_on_failure or :only_if_notable)"
             " [default]: ")
    j = SC.create_job({"name": name, "schedule": sched, "action_type": at, "action": action,
                       "result_to": dest or None}, who="menu", source="cli")
    say(f"[ok] created {name}; next run {S.fmt(j['state'].get('next_run'))}")


def _hb_menu(q, say):
    from . import colors as C, paint
    while True:
        say("")
        say(C.header("HEARTBEAT"))
        for ln in paint.heartbeat_lines(HB.status_lines()):
            say(ln)
        c = q("e) enable  d) disable  s) schedule  r) run now  l) last reports  b) back: ")
        if c in (None, "", "b", "q"):
            return
        if c in ("e", "d"):
            SC.set_enabled(SC.HEARTBEAT, c == "e", who="menu", source="cli")
        elif c == "s":
            v = q("New schedule (e.g. FREQ=MINUTELY;INTERVAL=30 or */15 * * * *): ")
            if v:
                SC.update_job(SC.HEARTBEAT, {"schedule": v}, who="menu", source="cli")
        elif c == "r":
            r = SC.Scheduler(log=lambda *x: None).run_now(SC.HEARTBEAT)
            say((r or {}).get("output") or "(no report)")
        elif c == "l":
            for rep in HB.reports(3):
                say(f"{rep.get('at')}:")
                for ln in paint.heartbeat_lines(["  " + x for x in HB.report_text(rep).splitlines()]):
                    say(ln)


def _actions_menu(q, say):
    from . import colors as C
    while True:
        acts = sorted(HB.load_actions(), key=lambda x: (x.get("priority", 3), x["name"]))
        say("")
        say(C.header("SUGGESTED ACTIONS"))
        for i, x in enumerate(acts, 1):
            for ln in action_screen(x, i):
                say(ln)
        c = q("Number to change, a) add, b) back: ")
        if c in (None, "", "b", "q"):
            return
        if c == "a":
            name = q("Name: ")
            instr = q("What to do (instruction): ")
            cond = q("When it is worth doing (condition): ")
            prio = q("Priority 1-9 [3]: ") or "3"
            dest = q("Result to [log]: ") or "log"
            if name and instr:
                HB.add_action({"name": name, "instruction": instr, "condition": cond, "priority": prio,
                               "result_to": dest}, who="menu", source="cli")
                say("[ok] added")
            continue
        if not (c.isdigit() and 1 <= int(c) <= len(acts)):
            continue
        x = acts[int(c) - 1]
        a = q(f"{x['name']}: e) enable  d) disable  i) instruction  c) condition  p) priority  r) result to  "
              "del) remove: ")
        ch = {}
        if a in ("e", "d"):
            ch = {"enabled": a == "e"}
        elif a == "i":
            ch = {"instruction": q("Instruction: ")}
        elif a == "c":
            ch = {"condition": q("Condition: ")}
        elif a == "p":
            ch = {"priority": q("Priority 1-9: ")}
        elif a == "r":
            ch = {"result_to": q("Result to: ")}
        elif a == "del":
            if (q(f"Remove {x['name']}? [y/N] ") or "").lower() in ("y", "yes"):
                HB.remove_action(x["name"], who="menu", source="cli")
            continue
        if ch and all(v not in (None, "") for v in ch.values()):
            HB.edit_action(x["name"], ch, who="menu", source="cli")
