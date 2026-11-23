"""The heartbeat (v3.8.0): Quill wakes up on a schedule, looks at a list of
suggested actions and the lab's fresh state, decides which actions are worth
taking, takes them through its normal tools, and writes a report.

The heartbeat is the built-in scheduler job 'heartbeat' (disabled until
setup or `nimlab heartbeat enable` turns it on; every 30 minutes by default,
change it with `nimlab heartbeat schedule "FREQ=HOURLY"`).

One heartbeat:
  1. Context: the last test run, service / tunnel / MCP / memory state,
     failures and bug IDs since the last heartbeat, new memories, and the
     previous heartbeat's decisions.
  2. Decide: one Quill turn gets the context and the enabled suggested
     actions and answers with JSON: take or skip each, with a short reason,
     and optionally a different result destination.
  3. Act: each action Quill took runs, highest priority first, up to
     heartbeat_settings.max_actions and within the token and time budget.
     An action with a 'run' (a scheduler action such as a test) runs that
     directly; any other action is a Quill turn with its instruction, through
     the same pipeline as chat (memory and tools included).
  4. Route: each result goes to the action's destination. Quill may pick
     another one (in its decision, or with a 'ROUTE: telegram' line in the
     action's result), and a failed action is escalated to
     heartbeat_settings.escalate_failures_to. The report says when either
     happened.
  5. Report: data/scheduler/heartbeat_reports.jsonl, one per heartbeat:
     each action taken or skipped with its reason, where its result went,
     and the budget used.

Suggested actions live in data/scheduler/suggested_actions.json:
  name, instruction (what to do), condition (when it is worth doing),
  priority (1 = first), enabled, result_to (see nimlab.routing), and an
  optional run: {"type": "test", "action": "service,tunnel"}.
"""

import contextlib
import json
import re
import time

from . import config
from . import routing
from . import scheduler as SC

DEFAULTS = {
    "max_actions": 3,              # actions taken per heartbeat, at most
    "token_budget": 6000,          # rough tokens (characters / 4) per heartbeat, prompts and replies
    "time_budget_sec": 600,        # no new action starts after this
    "escalate_failures_to": "telegram",   # a failed action's result also goes here ('' = off)
    "context_chars": 3500,         # the fresh-context block, at most
    "report_keep": 300,            # reports kept
    "decision_max_tokens": 700,
}
DEFAULT_ACTIONS = [
    {"name": "health-check", "priority": 1, "enabled": True,
     "instruction": "Run the service, tunnel and MCP tests.",
     "condition": "Worth it when the last test run is older than 2 hours, or when the context shows a failure, "
                  "a new bug or the service, tunnel or MCP down.",
     "run": {"type": "test", "action": ["service", "tunnel", "mcp"]},
     "result_to": {"dest": "telegram", "when": "only_on_failure"}},
    {"name": "bug-review", "priority": 2, "enabled": True,
     "instruction": "Look at the bug IDs that are new since the last heartbeat. Say in a few lines which ones "
                    "repeat, what they have in common and the one fix most worth trying first.",
     "condition": "Only when there are new bugs since the last heartbeat.",
     "result_to": {"dest": "memory", "when": "only_if_notable"}},
    {"name": "tunnel-recover", "priority": 2, "enabled": True,
     "instruction": "The public tunnel looks down. Check it with self_tunnel status and, if it is down, start "
                    "it again with self_tunnel quick. Say whether it is up now and its URL.",
     "condition": "Only when the context shows the tunnel enabled but not answering.",
     "result_to": {"dest": "telegram", "when": "always"}},
    {"name": "memory-digest", "priority": 3, "enabled": True,
     "instruction": "Write a short digest (three lines at most) of the new memories since the last heartbeat: "
                    "what the owner worked on and anything left open.",
     "condition": "Only when there are 5 or more new memories since the last heartbeat.",
     "result_to": {"dest": "memory", "when": "always"}},
]
ACTION_FIELDS = ("instruction", "condition", "priority", "enabled", "result_to", "run")


def settings(cluster=None):
    c = config.load_cluster_config() if cluster is None else cluster
    s = c.setdefault("heartbeat_settings", {})
    for k, v in DEFAULTS.items():
        s.setdefault(k, v)
    return s


# ---------------------------------------------------------------------------
# suggested actions
# ---------------------------------------------------------------------------
def _path():
    return SC._p("suggested_actions.json")


def load_actions():
    with SC._locked("actions.lock"):
        d = SC._read_json(_path(), None)
        if d is None:
            d = {"version": 1, "actions": [dict(a, created_by="builtin") for a in DEFAULT_ACTIONS]}
            SC._write_json(_path(), d)
        return [a for a in d.get("actions") or [] if isinstance(a, dict)]


def _save(actions):
    SC._write_json(_path(), {"version": 1, "actions": actions})


def get_action(name):
    a = next((x for x in load_actions() if x.get("name") == name), None)
    if a is None:
        raise SC.JobError(f"no suggested action named {name!r}; see: nimlab heartbeat actions list")
    return a


def normalize_action(a):
    name = str(a.get("name") or "").strip()
    if not SC.NAME_RX.match(name):
        raise SC.JobError("the action name needs letters, digits, - _ or . (up to 60)")
    instr = str(a.get("instruction") or "").strip()
    run = a.get("run")
    if isinstance(run, str) and run.strip():
        try:
            run = json.loads(run)
        except ValueError:
            t, _, rest = run.strip().partition(" ")
            run = {"type": t, "action": rest}
    if run:
        t = str(run.get("type") or "").lower()
        if t not in SC.USER_ACTION_TYPES or t == "quill_prompt":
            raise SC.JobError("run.type must be one of nimlab_command, test, mcp_tool, shell, chain "
                              "(for a Quill instruction, leave run out)")
        run = {"type": t, "action": SC.check_action(t, run.get("action"))}
    else:
        run = None
    if not instr and not run:
        raise SC.JobError("a suggested action needs an instruction (what to do)")
    try:
        prio = int(a.get("priority") or 3)
    except (TypeError, ValueError):
        raise SC.JobError("priority must be a whole number, 1 (first) to 9") from None
    if not 1 <= prio <= 9:
        raise SC.JobError("priority must be 1 (first) to 9")
    return {"name": name, "instruction": instr or f"Run {run['type']}: {run['action']}",
            "condition": str(a.get("condition") or "").strip(), "priority": prio,
            "enabled": SC._bool(a.get("enabled", True)), "result_to": routing.normalize(a.get("result_to")),
            "run": run, "created_by": str(a.get("created_by") or "cli")[:80],
            "updated_at": config.timestamp()}


def add_action(spec, who=None, source=None):
    a = normalize_action(dict(spec, created_by=spec.get("created_by") or who or "cli"))
    with SC._locked("actions.lock"):
        acts = SC._read_json(_path(), {"actions": []}).get("actions") or []
        if any(x.get("name") == a["name"] for x in acts):
            raise SC.JobError(f"a suggested action named {a['name']} already exists")
        acts.append(a)
        _save(acts)
    SC.audit("create", "action", a["name"], None, a, who, source)
    return a


def edit_action(name, changes, who=None, source=None):
    changes = {k: v for k, v in (changes or {}).items() if k in ACTION_FIELDS}
    if not changes:
        raise SC.JobError(f"nothing to change; fields: {', '.join(ACTION_FIELDS)}")
    load_actions()
    with SC._locked("actions.lock"):
        acts = SC._read_json(_path(), {"actions": []}).get("actions") or []
        i = next((k for k, x in enumerate(acts) if x.get("name") == name), None)
        if i is None:
            raise SC.JobError(f"no suggested action named {name!r}")
        old = acts[i]
        new = normalize_action({**old, **changes})
        new["created_by"] = old.get("created_by", "cli")
        acts[i] = new
        _save(acts)
    SC.audit("edit", "action", name, {k: old.get(k) for k in changes}, {k: new.get(k) for k in changes},
             who, source)
    return new


def remove_action(name, who=None, source=None):
    load_actions()
    with SC._locked("actions.lock"):
        acts = SC._read_json(_path(), {"actions": []}).get("actions") or []
        old = next((x for x in acts if x.get("name") == name), None)
        if old is None:
            raise SC.JobError(f"no suggested action named {name!r}")
        _save([x for x in acts if x.get("name") != name])
    SC.audit("delete", "action", name, old, None, who, source)
    return old


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------
def reports(n=10):
    return SC._tail("heartbeat_reports.jsonl", n)


def last_report():
    r = reports(1)
    return r[-1] if r else None


def _save_report(rep, keep):
    with SC._locked("reports.lock"):
        SC._append("heartbeat_reports.jsonl", rep)
        rows = SC._tail("heartbeat_reports.jsonl")
        if len(rows) > keep:
            tmp = SC._p("heartbeat_reports.jsonl.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                for r in rows[-keep:]:
                    f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            import os
            os.replace(tmp, SC._p("heartbeat_reports.jsonl"))


# ---------------------------------------------------------------------------
# fresh context
# ---------------------------------------------------------------------------
def live_context(since):
    """What Quill sees at each heartbeat. Every part is best effort: a part
    that cannot be read says so instead of breaking the heartbeat."""
    from . import systests
    ctx, live = {}, systests.Live()

    def part(key, fn):
        try:
            ctx[key] = fn()
        except Exception as e:  # noqa: BLE001
            ctx[key] = f"unavailable ({type(e).__name__}: {str(e)[:100]})"

    def tests():
        rows = systests.load_history(1)
        if not rows:
            return "no test runs saved yet"
        r = rows[-1]
        res = r.get("results") or {}
        return {"at": r.get("at"), "failed": [k for k, v in res.items() if v.get("status") == "FAIL"],
                "passed": [k for k, v in res.items() if v.get("status") == "PASS"]}

    def service():
        s = live.service()
        return {"supervisor": bool(s.get("holder")), "children": s.get("children"), "want": s.get("want"),
                "strays": len(s.get("strays") or [])}

    def tunnel():
        return live.tunnel_mode()

    def mcp():
        c = config.load_cluster_config().get("mcp_settings") or {}
        return {"enabled": bool(c.get("enabled")), "url": c.get("url") or ""}

    def memory():
        m = (config.load_cluster_config().get("memory_settings") or {})
        return {"backend": m.get("backend"), "auto_store": m.get("auto_store"), "auto_recall": m.get("auto_recall")}

    def bugs():
        from . import bugs as B
        since_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(since))
        rows = [b for b in B.list_bugs(100) if str(b.get("last") or "")[:19] >= since_iso]
        return [{"id": b.get("id"), "kind": b.get("kind"), "where": b.get("where"), "count": b.get("count"),
                 "message": str(b.get("message") or "")[:160]} for b in rows[:10]]

    def jobs():
        rows = [r for r in SC.history(n=300) if float(r.get("start") or 0) >= since and r.get("job") != SC.HEARTBEAT]
        failed = [{"job": r["job"], "status": r["status"], "bug": r.get("bug"), "output": SC._first(r.get("output"))}
                  for r in rows if r.get("status") in ("FAILED", "TIMED_OUT")]
        return {"runs": len(rows), "failed": failed[-8:]}

    def memories():
        ent = live.entity()
        mem = getattr(ent, "memory", None)
        if mem is None:
            return "memory is off"
        new = []
        for _, text, ts, _id in mem.recent(15):
            try:
                t = SC.S.parse_local(str(ts)) if ts else 0
            except Exception:  # noqa: BLE001
                t = 0
            if t >= since:
                new.append(str(text)[:160])
        return {"new": len(new), "latest": new[-5:]}

    for k, fn in (("tests", tests), ("service", service), ("tunnel", tunnel), ("mcp", mcp), ("memory", memory),
                  ("bugs_since_last", bugs), ("jobs_since_last", jobs), ("memories_since_last", memories)):
        part(k, fn)
    return ctx


def _ctx_block(c, limit):
    s = json.dumps(c, ensure_ascii=False, default=str, indent=1)
    return s if len(s) <= limit else s[:limit] + " ...(cut)"


def decision_prompt(context, actions, previous, s, now_text):
    lines = [
        "HEARTBEAT. This is a scheduled wake-up, not a message from the owner. Decide which suggested actions "
        "are worth taking right now, based on each action's condition and the fresh context. Do not call any "
        "tools in this step and do not take the actions yet: only decide.",
        f"Time: {now_text}. You may take at most {s['max_actions']} action(s).",
        "", "SUGGESTED ACTIONS (priority 1 = first):"]
    for a in actions:
        lines.append(f"- {a['name']} (priority {a['priority']}, result to {routing.describe(a.get('result_to'))}): "
                     f"{a['instruction']}" + (f" | Worth doing: {a['condition']}" if a.get("condition") else ""))
    lines += ["", "FRESH CONTEXT:", _ctx_block(context, int(s.get("context_chars") or 3500))]
    if previous:
        lines += ["", f"PREVIOUS HEARTBEAT ({previous.get('at')}): " + "; ".join(
            f"{d.get('name')}: {d.get('decision')}" + (f" ({d.get('reason')})" if d.get("reason") else "")
            for d in previous.get("decisions") or [])[:900]]
    lines += ["", "Answer with ONLY one JSON object, no other text:",
              '{"decisions": [{"name": "<action>", "decision": "take" or "skip", "reason": "<short reason>", '
              '"result_to": "<optional: telegram|memory|log|none, only to send the result somewhere other than '
              'the default>"}], "summary": "<one line>"}',
              "Include every action. Take an action only when its condition holds."]
    return "\n".join(lines)


_JSON = re.compile(r"\{.*\}", re.S)


def parse_decisions(text):
    """Quill's JSON answer -> (decisions, summary), or raises ValueError."""
    t = str(text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    m = _JSON.search(t)
    if not m:
        raise ValueError("no JSON object in Quill's answer")
    blob = m.group(0)
    for end in range(len(blob), 0, -1):          # tolerate trailing chatter after the object
        if blob[end - 1] != "}":
            continue
        try:
            d = json.loads(blob[:end])
            break
        except ValueError:
            continue
    else:
        raise ValueError("Quill's answer is not valid JSON")
    decs = d.get("decisions") if isinstance(d, dict) else None
    if not isinstance(decs, list):
        raise ValueError("the JSON has no 'decisions' list")
    return [x for x in decs if isinstance(x, dict)], str(d.get("summary") or "")[:300]


_ROUTE = re.compile(r"^\s*ROUTE:\s*(telegram|memory|log|none)\s*$", re.I | re.M)


def _tokens(*texts):
    return sum(len(str(t or "")) for t in texts) // 4


def run(ctx, job, timeout=0, clock=time.time):
    """One heartbeat. -> scheduler.ActionResult with the report."""
    s = settings()
    t_start = time.monotonic()
    budget_s = min(float(s.get("time_budget_sec") or 600), float(timeout) if timeout else 1e9)
    tok_budget = int(s.get("token_budget") or 6000)
    max_actions = int(s.get("max_actions") or 3)
    prev = last_report()
    since = float((prev or {}).get("at_ts") or (clock() - 1800))
    actions = sorted((a for a in load_actions() if a.get("enabled")), key=lambda a: (a.get("priority", 3),
                                                                                    a.get("name")))
    rep = {"at": config.timestamp(), "at_ts": clock(), "report_id": f"hb-{int(clock())}", "decisions": [],
           "summary": "", "budget": {"max_actions": max_actions, "token_budget": tok_budget,
                                       "time_budget_sec": budget_s}}
    if not actions:
        rep["summary"] = "no suggested actions are enabled"
        _save_report(rep, int(s.get("report_keep") or 300))
        return SC.ActionResult(True, "heartbeat: no suggested actions are enabled", notable=False,
                               data={"report_id": rep["report_id"]})
    # v3.8.4: a user message, an email alert or another job starting interrupts the heartbeat between its
    # steps; actions it had chosen but not done are taken first, automatically, at the next heartbeat
    from . import interrupts
    jname = (job or {}).get("name") or SC.HEARTBEAT
    t0 = clock()

    def interrupted():
        m = interrupts.since(t0, own=jname)
        return interrupts.describe(m) if m else None

    left = interrupts.load_leftover(jname)
    carried = [str(n) for n in ((left or {}).get("undone") or [])]
    get_ctx = getattr(ctx, "hb_context", None) or live_context
    try:
        context = get_ctx(since)
    except Exception as e:  # noqa: BLE001
        context = {"error": f"context unavailable: {type(e).__name__}: {e}"}
    by_name = {a["name"]: a for a in actions}
    taken = 0
    any_fail = False
    used = 0
    done_names = set()

    def stop_for(why, undone):
        undone = [n for n in undone if n not in done_names]
        interrupts.save_leftover(jname, {"reason": why, "undone": undone, "interrupted_at": config.timestamp(),
                                         "progress": "Chosen but not done yet: " + (", ".join(undone) or "none")})
        rep["summary"] = (rep.get("summary") or "") + f" [interrupted: {why}; " \
            f"{', '.join(undone) or 'nothing'} carried to the next heartbeat]"
        rep["interrupted"] = why
        rep["budget"].update(actions_taken=taken, tokens_used=used,
                             elapsed_sec=round(time.monotonic() - t_start, 1))
        _save_report(rep, int(s.get("report_keep") or 300))
        return SC.ActionResult(True, report_text(rep), notable=False,
                               data={"report_id": rep["report_id"], "interrupted": why, "undone": undone})

    # 1. what the last heartbeat chose and could not finish: continued automatically, no new decision
    for i, n in enumerate(carried):
        a = by_name.get(n)
        if a is None:
            continue
        why = interrupted()
        if why:
            return stop_for(why, carried[i:])
        if taken >= max_actions:
            break
        taken += 1
        d = {"decision": "take", "reason": f"interrupted last time ({(left or {}).get('reason') or 'interrupted'}); "
                                           "continuing it"}
        entry = {"name": n, "decision": "take", "reason": d["reason"], "carried": True,
                 "default_dest": routing.describe(a.get("result_to"))}
        entry.update(_take(a, d, ctx, s, budget_s - (time.monotonic() - t_start), clock))
        used += entry.pop("_tokens", 0)
        any_fail = any_fail or not entry["ok"]
        rep["decisions"].append(entry)
        done_names.add(n)
    why = interrupted()
    if why:
        return stop_for(why, [])
    prompt = decision_prompt(context, [a for a in actions if a["name"] not in done_names], prev, s,
                             SC.S.fmt(clock(), with_zone=True))
    ok, answer = ctx.quill(prompt, who="heartbeat", max_tokens=int(s.get("decision_max_tokens") or 700),
                           timeout=max(30, budget_s))
    used += _tokens(prompt, answer)
    if not ok:
        rep["summary"] = f"Quill could not decide: {SC._first(answer)}"
        rep["budget"]["tokens_used"] = used
        _save_report(rep, int(s.get("report_keep") or 300))
        return SC.ActionResult(False, rep["summary"], data={"report_id": rep["report_id"]})
    try:
        decs, summ = parse_decisions(answer)
    except ValueError as e:
        rep["summary"] = f"Quill's decision could not be read ({e})"
        rep["raw"] = str(answer)[:600]
        rep["budget"]["tokens_used"] = used
        _save_report(rep, int(s.get("report_keep") or 300))
        return SC.ActionResult(False, rep["summary"] + ": " + SC._first(answer), data={"report_id": rep["report_id"]})
    rep["summary"] = summ
    chosen = {}
    for d in decs:
        n = str(d.get("name") or "")
        if n in by_name and n not in chosen:
            chosen[n] = d
    order = [a for a in actions if a["name"] not in done_names]
    wanted = [a["name"] for a in order if str((chosen.get(a["name"]) or {}).get("decision") or "").lower()
              in ("take", "yes", "run", "do")]
    for a in order:                        # priority order, not the order Quill listed them in
        d = chosen.get(a["name"]) or {"decision": "skip", "reason": "Quill did not mention it"}
        if a["name"] in wanted:
            why = interrupted()
            if why:
                return stop_for(why, wanted[wanted.index(a["name"]):])
        entry = {"name": a["name"], "decision": "skip", "reason": str(d.get("reason") or "")[:200],
                 "default_dest": routing.describe(a.get("result_to"))}
        want = str(d.get("decision") or "").lower() in ("take", "yes", "run", "do")
        if want and taken >= max_actions:
            entry["reason"] = f"over the limit of {max_actions} action(s) per heartbeat"
        elif want and time.monotonic() - t_start >= budget_s:
            entry["reason"] = f"out of time (budget {int(budget_s)} s)"
        elif want and used >= tok_budget:
            entry["reason"] = f"out of tokens (budget about {tok_budget})"
        elif want:
            taken += 1
            entry["decision"] = "take"
            entry.update(_take(a, d, ctx, s, budget_s - (time.monotonic() - t_start), clock))
            used += entry.pop("_tokens", 0)
            any_fail = any_fail or not entry["ok"]
            done_names.add(a["name"])
        rep["decisions"].append(entry)
    if left:
        interrupts.clear_leftover(jname)     # finished normally: nothing carried over any more
    rep["budget"].update(actions_taken=taken, tokens_used=used, elapsed_sec=round(time.monotonic() - t_start, 1))
    _save_report(rep, int(s.get("report_keep") or 300))
    text = report_text(rep)
    return SC.ActionResult(True, text, notable=taken > 0 or any_fail,
                           data={"report_id": rep["report_id"], "failed_actions": any_fail})


def _take(a, d, ctx, s, left, clock):
    """Run one chosen action and route its result. -> report fields."""
    left = max(10, int(left))
    toks = 0
    if a.get("run"):
        r = SC.run_action(a["run"]["type"], a["run"]["action"], ctx, {"name": f"heartbeat:{a['name']}"},
                          timeout=left)
        ok, out, notable = r.ok, r.output, r.notable
    else:
        prompt = (f"HEARTBEAT ACTION '{a['name']}'. You decided this is worth doing now"
                  + (f" ({d.get('reason')})" if d.get("reason") else "") + f". Do it with your normal tools:\n"
                  f"{a['instruction']}\n\nThen reply with the result in a few lines for the owner. If the outcome "
                  "calls for a different place than the default "
                  f"({routing.describe(a.get('result_to'))}), end with one line: ROUTE: telegram | memory | log | none")
        done, v = SC._with_timeout(lambda: ctx.quill(prompt, who=f"heartbeat:{a['name']}", timeout=left), left)
        if not done:
            ok, out = False, f"Quill did not finish within {left} s"
        else:
            ok, out = v
        notable = None
        toks = _tokens(prompt, out)
    out = str(out or "")
    r = dict(a.get("result_to") or {"dest": "log", "when": "always"})
    why_dest = ""
    over = str(d.get("result_to") or "").lower().strip()
    m = _ROUTE.search(out)
    if m:
        over = m.group(1).lower()
        out = _ROUTE.sub("", out).strip()
    if over in ("telegram", "memory", "log", "none") and over != r.get("dest"):
        why_dest = f"Quill chose {over} instead of {r.get('dest')}"
        r = {"dest": over, "when": "always"}
    esc = (s.get("escalate_failures_to") or "").lower()
    status = "SUCCEEDED" if ok else "FAILED"
    if not ok and esc in ("telegram", "memory", "log") and esc != r.get("dest"):
        r["escalate_on_failure"] = esc
    routed = routing.deliver(r, {"name": f"heartbeat:{a['name']}"}, status, out,
                             notable if notable is not None else True, None, ctx, clock=clock,
                             title=f"[Nim Lab] heartbeat: {a['name']} {'done' if ok else 'FAILED'}")
    escalated = [x for x in routed if x.startswith("escalated")]
    return {"ok": ok, "output": SC._redact(out)[:600], "routed": routed, "dest": r.get("dest"),
            "dest_changed": why_dest, "escalated": (f"failed, so also sent to {esc}" if escalated else ""),
            "_tokens": toks}


def report_text(rep):
    took = [d for d in rep["decisions"] if d["decision"] == "take"]
    lines = [f"heartbeat: took {len(took)}, skipped {len(rep['decisions']) - len(took)}"
             + (f" - {rep['summary']}" if rep.get("summary") else "")]
    for d in rep["decisions"]:
        if d["decision"] == "take":
            extra = "; ".join(x for x in (d.get("dest_changed"), d.get("escalated")) if x)
            lines.append(f"  took {d['name']}: {'ok' if d.get('ok') else 'FAILED'}, result to "
                         f"{', '.join(d.get('routed') or []) or 'nowhere (condition not met)'}"
                         + (f" ({extra})" if extra else "") + (f" - {d['reason']}" if d.get("reason") else ""))
        else:
            lines.append(f"  skipped {d['name']}: {d.get('reason') or '-'}")
    b = rep.get("budget") or {}
    lines.append(f"  budget: {b.get('actions_taken', 0)}/{b.get('max_actions')} actions, about "
                 f"{b.get('tokens_used', 0)}/{b.get('token_budget')} tokens, {b.get('elapsed_sec', 0)} s")
    return "\n".join(lines)


def status_lines():
    with contextlib.suppress(Exception):
        j = SC.load_jobs().get(SC.HEARTBEAT) or {}
        st = j.get("state") or {}
        s = settings()
        acts = load_actions()
        out = [f"Heartbeat: {'ON' if j.get('enabled') else 'off'}, {SC.S.describe(j.get('schedule', ''))} "
               f"({j.get('schedule')})",
               f"  next: {SC.S.fmt(st.get('next_run'))} ({SC.S.ago(st.get('next_run'))})" if st.get("next_run")
               else "  next: - (enable it: nimlab heartbeat enable)",
               f"  last: {SC.S.fmt(st.get('last_run'))} {st.get('last_status') or ''}".rstrip(),
               f"  limits: {s['max_actions']} actions, about {s['token_budget']} tokens, {s['time_budget_sec']} s; "
               f"failures escalate to {s.get('escalate_failures_to') or 'nowhere'}",
               f"  suggested actions: {sum(1 for a in acts if a.get('enabled'))} enabled of {len(acts)}"]
        rep = last_report()
        if rep:
            out.append("  last report:")
            out += ["    " + ln for ln in report_text(rep).splitlines()]
        return out
    return ["Heartbeat: status unavailable"]
