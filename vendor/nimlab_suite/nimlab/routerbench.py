"""3.7.2 router benchmark: time the testbed's own turn pipeline.

Every prompt goes through the exact code the testbed uses, with no
separate path:
- chat mode: a text turn is `Entity.turn(text, history)`, as testbed chat
  sends it; a turn with a file is `attach.run_with_files` (unified.Mind),
  as testbed chat sends a turn with an attachment;
- call mode (--call): `unified.Mind.run(..., want_audio=True,
  defer_store=True)` on the "voice" channel under the call's turn time
  cap, then the memory store after the reply, as a voice call does. (A
  call turn starts from your recorded voice; here the text prompts are
  sent as text, and the audio prompt as the recording.)

So the same intent router, keyword and media fast paths, persona, role
calls through the NVIDIA API, memory recall and memory store run.

Per turn it records: the route chosen and the expected one, the router
decision time (0 when a fast path decided), every HTTP call (bytes sent,
time to the first byte, total time, bytes received), memory recall/store
time, and the end-to-end time, split into NVIDIA API time, memory time and
the pipeline's own overhead (prompts, local work). Router time is the
intent router's decision, its own NVIDIA call included; 0 when a keyword
or media fast path decided.
"""

import json
import os
import statistics
import tempfile
import time

from . import config, perf, store

LATEST = "router_bench_latest.json"

# (id, route group, prompt, attachment kind or None, expected roles)
PROMPTS = (
    ("casual", "chat", "Hey, how's your evening going?", None, ("persona",)),
    ("reasoning", "reasoning", "Think it through step by step: I have 3 phones charging at 15 W, 25 W and 45 W from "
     "one 60 W charger. Which two can charge at full speed together, and why?", None, ("reasoning",)),
    ("coding", "coding", "Write a Python function that splits a CSV line with quoted fields, plus one test.",
     None, ("coding",)),
    ("tool", "tool", "Use your tools: look up what time it is in Tokyo right now.", None,
     ("persona", "coding", "reasoning")),
    ("vision", "image", "What's in this picture?", "vision", ("vision",)),
    ("ocr", "image", "Read the text in this screenshot.", "ocr", ("ocr",)),
    ("chart", "image", "What does this chart show? Describe the plot.", "chart", ("chart_parser",)),
    ("asr", "audio", "Transcribe this voice message.", "speech", ("asr",)),
    ("memory", "memory", "What do you remember about my Nim Lab project?", None, ("persona",)),
    ("spoken", "tts", "Say a one-line hello, out loud.", None, ("persona",)),
)


def prompt_set(only=None, extra=()):
    rows = [dict(id=i, group=g, text=t, attach=a, expect=e) for i, g, t, a, e in PROMPTS]
    if only:
        want = {w.strip() for w in only}
        rows = [r for r in rows if r["id"] in want or r["group"] in want]
    for n, text in enumerate(extra or (), 1):
        rows.append(dict(id=f"user{n}", group="user", text=text, attach=None, expect=()))
    return rows


def _attachment(kind, tmp):
    from . import assets, server, unified
    if kind in ("vision", "chart"):
        data, name, mime = assets.vision_png(), f"{kind}.png", "image/png"
    elif kind == "ocr":
        data, name, mime = assets.ocr_png(), "screenshot.png", "image/png"
    else:
        sample = os.path.join(config.PROJECT_DIR, "samples", "magpie_aria_sample.wav")
        try:
            with open(sample, "rb") as f:
                data = f.read()
        except OSError:
            data = server.test_wav(1.0)
        name, mime = "voice message.wav", "audio/wav"
    path = os.path.join(tmp, name)
    with open(path, "wb") as f:
        f.write(data)
    return unified.Part("image" if mime.startswith("image") else "audio", path=path, mime=mime, name=name)


def _silent(*_a, **_k):
    return None


def run_turn(ent, p, call=False, tmp=None):
    """One prompt through the testbed pipeline. -> a row of timings."""
    from . import attach, environment as ENV, unified
    parts = [_attachment(p["attach"], tmp)] if p.get("attach") else []
    vs = (ent.cluster.get("voice_settings") or {}) if call else {}
    old_log = getattr(ent, "log", None)
    ent.log = None                                        # keep the route line out of the table
    t0 = time.monotonic()
    err = None
    route = via = None
    router_ms = 0
    with perf.track("router bench") as tr:
        try:
            if call:
                with ENV.channel("voice"), perf.time_cap(vs.get("turn_timeout_sec")):
                    res = unified.Mind(ent).run(p["text"], parts, [], want_audio=ent.is_set("tts"),
                                                defer_store=True)
                    fin = res.get("finish")
                    if callable(fin):
                        fin()
                route, via = res.get("route"), res.get("via")
                router_ms = sum(t.get("ms") or 0 for t in res.get("trace") or [] if t.get("role") == "intent_router")
                ok, err = bool(res.get("ok")), res.get("error")
                tts = any(t.get("role") == "tts" for t in res.get("trace") or [])
            elif parts:
                res = attach.run_with_files(ent, p["text"], parts, [], out=_silent)
                route, via = res.get("route"), res.get("via")
                router_ms = sum(t.get("ms") or 0 for t in res.get("trace") or [] if t.get("role") == "intent_router")
                ok, err, tts = bool(res.get("ok")), res.get("error"), False
            else:
                out = ent.turn(p["text"], [])
                rt = out.get("route") or {}
                route, via = rt.get("role"), rt.get("via")
                router_ms = rt.get("router_ms") or 0
                r = out.get("result")
                ok = bool(r is not None and r.ok)
                err = None if ok else (getattr(r, "error", None) or "no reply")
                tts = False
        except Exception as e:  # noqa: BLE001 - one failed turn is a row, not the end of the run
            ok, err, tts = False, f"{type(e).__name__}: {e}", False
        finally:
            ent.log = old_log
    total = int((time.monotonic() - t0) * 1000)
    stages = tr.summary()
    mem_ms = stages.get("memory_recall", 0) + stages.get("memory_store", 0)
    calls = [dict(c) for c in tr.net]
    # the router's decision (its own NVIDIA call included) is routing, not role API time
    router_ms = max(int(router_ms or 0), stages.get("intent_router", 0))
    api_calls = [c for c in calls if not str(c.get("stage", "")).startswith("memory")
                 and c.get("stage") != "intent_router"]
    api_ms = sum(c["total_ms"] for c in api_calls)
    # role stages with no HTTP rows (gRPC speech, MCP tools) are API time too
    http_stages = {c.get("stage") for c in api_calls}
    other_api = sum(ms for k, ms in stages.items() if k not in http_stages and not k.startswith("memory")
                    and k not in ("convert", "record", "play", "intent_router"))
    api_ms += other_api
    expect = tuple(p.get("expect") or ())
    tts = tts or "tts" in stages
    if p["id"] == "spoken" and call:
        hit = tts and (route in expect)
    else:
        hit = (route in expect) if expect else None
    return {"id": p["id"], "group": p["group"], "ok": ok, "error": (str(err)[:160] if err else None),
            "route": route, "via": via, "expect": list(expect), "hit": hit, "total_ms": total,
            "router_ms": int(router_ms), "api_ms": int(api_ms), "memory_ms": int(mem_ms),
            "memory_recall_ms": stages.get("memory_recall", 0), "memory_store_ms": stages.get("memory_store", 0),
            "overhead_ms": max(0, total - int(router_ms) - int(api_ms) - int(mem_ms)), "stages": stages,
            "calls": calls}


def pct(values, q):
    v = sorted(values)
    if not v:
        return None
    k = max(0, min(len(v) - 1, int(round(q / 100.0 * len(v) + 0.5)) - 1))
    return v[k]


def aggregate(rows, key):
    groups = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)
    out = {}
    for g, rs in groups.items():
        hits = [r["hit"] for r in rs if r["hit"] is not None]
        out[g] = {"turns": len(rs), "ok": sum(1 for r in rs if r["ok"]),
                  "accuracy": (round(sum(hits) / len(hits), 3) if hits else None),
                  "routes": sorted({str(r["route"]) for r in rs})}
        for f in ("total_ms", "router_ms", "api_ms", "memory_ms", "overhead_ms"):
            vals = [r[f] for r in rs]
            out[g][f] = {"median": int(statistics.median(vals)), "p95": pct(vals, 95)}
        firsts = [c["first_ms"] for r in rs for c in r["calls"] if c.get("first_ms") is not None]
        out[g]["first_byte_ms"] = {"median": int(statistics.median(firsts)) if firsts else None,
                                   "p95": pct(firsts, 95)}
        out[g]["sent_bytes"] = int(statistics.median([sum(c["sent"] for c in r["calls"]) for r in rs]))
        out[g]["received_bytes"] = int(statistics.median([sum(c["received"] for c in r["calls"]) for r in rs]))
    return out


def direct(ent, rows, runs=1):
    """The same models called straight (one role call: no router, no
    persona pass, no memory), for the overhead comparison. Text turns only.
    -> {prompt id: {role, median_ms}}."""
    out = {}
    seen = {}
    for r in rows:
        role = r["route"] if r["route"] in ("persona", "reasoning", "coding") else None
        if not role or r["group"] in ("image", "audio") or r["id"] in seen:
            continue
        seen[r["id"]] = role
    for pid, role in seen.items():
        text = next(r["text"] for r in rows if r["id"] == pid)
        times = []
        for _ in range(max(1, runs)):
            t0 = time.monotonic()
            res = ent.run_role(role, text=text)
            if getattr(res, "ok", False):
                times.append(int((time.monotonic() - t0) * 1000))
        if times:
            out[pid] = {"role": role, "model": ent.target(role), "median_ms": int(statistics.median(times))}
    return out


def run(ent, runs=3, call=False, only=None, extra=(), compare=False, out=print):
    prompts = prompt_set(only, extra)
    if not prompts:
        raise ValueError("no prompts match; ids: " + ", ".join(p[0] for p in PROMPTS))
    rows = []
    tmp = tempfile.mkdtemp(prefix="nimlab_rbench_")
    try:
        for n in range(1, max(1, int(runs)) + 1):
            for p in prompts:
                r = run_turn(ent, p, call=call, tmp=tmp)
                r["run"] = n
                r["text"] = p["text"]
                rows.append(r)
                out(line(r, n, runs))
    finally:
        for f in os.listdir(tmp):
            try:
                os.unlink(os.path.join(tmp, f))
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
    report = {"kind": "router", "timestamp": config.timestamp(), "mode": "call" if call else "chat",
              "runs": int(runs), "prompts": [p["id"] for p in prompts],
              "by_prompt": aggregate(rows, "id"), "by_route": aggregate(rows, "group"), "turns": rows}
    hits = [r["hit"] for r in rows if r["hit"] is not None]
    report["accuracy"] = round(sum(hits) / len(hits), 3) if hits else None
    report["median_total_ms"] = int(statistics.median([r["total_ms"] for r in rows]))
    if compare:
        report["direct"] = direct(ent, rows, runs=1)
    save(report)
    return report


def line(r, n, runs):
    mark = "ok " if r["hit"] else "MISS" if r["hit"] is False else "-  "
    tail = f"  error: {r['error']}" if r["error"] else ""
    return (f"  [{n}/{runs}] {r['id']:<9} {mark:<4} route {str(r['route']):<13} via {str(r['via'] or '-'):<9} "
            f"total {r['total_ms'] / 1000:6.2f}s  router {r['router_ms'] / 1000:5.2f}s  api {r['api_ms'] / 1000:6.2f}s  "
            f"memory {r['memory_ms'] / 1000:5.2f}s  overhead {r['overhead_ms'] / 1000:5.2f}s{tail}")


def report_lines(rep):
    def s(ms):
        return "-" if ms is None else f"{ms / 1000:.2f}s"
    acc = rep.get("accuracy")
    out = [f"Router benchmark ({rep.get('mode')} mode, {rep.get('runs')} run(s), {rep.get('timestamp')})",
           f"Routing accuracy: {'-' if acc is None else f'{acc * 100:.0f}%'}   median turn: "
           f"{s(rep.get('median_total_ms'))}",
           f"{'prompt':<10} {'route':<14} {'acc':>4} {'total med/p95':>15} {'router':>7} {'API med':>8} "
           f"{'1st byte':>8} {'memory':>7} {'overhead':>8} {'sent/recv':>13}"]
    for pid, a in (rep.get("by_prompt") or {}).items():
        accp = "-" if a["accuracy"] is None else f"{a['accuracy'] * 100:.0f}%"
        out.append(f"{pid:<10} {','.join(a['routes'])[:14]:<14} {accp:>4} "
                   f"{s(a['total_ms']['median']) + '/' + s(a['total_ms']['p95']):>15} {s(a['router_ms']['median']):>7} "
                   f"{s(a['api_ms']['median']):>8} {s(a['first_byte_ms']['median']):>8} "
                   f"{s(a['memory_ms']['median']):>7} {s(a['overhead_ms']['median']):>8} "
                   f"{_kb(a['sent_bytes']) + '/' + _kb(a['received_bytes']):>13}")
    out.append("By route:")
    for g, a in (rep.get("by_route") or {}).items():
        accp = "-" if a["accuracy"] is None else f"{a['accuracy'] * 100:.0f}%"
        out.append(f"  {g:<10} median {s(a['total_ms']['median'])}, p95 {s(a['total_ms']['p95'])}, accuracy {accp}, "
                   f"API {s(a['api_ms']['median'])}, overhead {s(a['overhead_ms']['median'])}")
    misses = [r for r in rep.get("turns") or [] if r.get("hit") is False]
    for r in misses[:8]:
        out.append(f"  miss: {r['id']} went to {r['route']} (via {r['via']}), expected {' or '.join(r['expect'])}")
    d = rep.get("direct") or {}
    if d:
        out.append("Direct model calls (same model, no router/persona/memory) vs the full turn:")
        for pid, x in d.items():
            full = (rep["by_prompt"].get(pid) or {}).get("total_ms", {}).get("median")
            extra = f", the full turn adds {s(full - x['median_ms'])}" if full is not None else ""
            out.append(f"  {pid:<10} {x['model']}: direct {s(x['median_ms'])}{extra}")
    out.append("router = the intent router's decision (0 when a fast path decided); API = the NVIDIA calls it "
               "routed to (HTTP, gRPC, MCP); overhead = prompts and local work (total minus router, API and memory).")
    return out


def _kb(n):
    return f"{n / 1024:.0f}K" if n >= 1024 else f"{n}B"


def save(report):
    """Latest run in data/router_bench_latest.json, a summary on the
    benchmark history (kind 'router')."""
    config.save_json(store.path(LATEST), report)
    store.add_history_run({"timestamp": report["timestamp"], "kind": "router", "mode": report["mode"],
                           "runs": report["runs"], "accuracy": report.get("accuracy"),
                           "median_total_ms": report.get("median_total_ms"),
                           "routes": {g: {"median_ms": a["total_ms"]["median"], "p95_ms": a["total_ms"]["p95"],
                                          "accuracy": a["accuracy"]} for g, a in report["by_route"].items()}})


def latest():
    try:
        with open(store.path(LATEST), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def cmd_bench(args):
    """nimlab bench router [--runs N] [--call] [--only ids] [--prompt TEXT]... [--compare] [--show]"""
    if args.show:
        rep = latest()
        if not rep:
            print("No router benchmark yet: nimlab bench router")
            return 1
        print("\n".join(report_lines(rep)))
        return 0
    from .entity import Entity
    from .core import load_api_key
    if not load_api_key():
        print("No NVIDIA key yet: the benchmark sends real turns. Set it with: nimlab setup key")
        return 2
    ent = Entity(log=lambda *a: None)
    runs = max(1, int(args.runs or 3))
    print(f"Router benchmark: {runs} run(s), {'call' if args.call else 'chat'} mode, through the testbed's own "
          "turn pipeline (router, fast paths, persona, role calls, memory)...")
    try:
        rep = run(ent, runs=runs, call=args.call, only=(args.only.split(",") if args.only else None),
                  extra=args.prompt or (), compare=args.compare)
    except ValueError as e:
        print(f"[x] {e}")
        return 2
    print()
    print("\n".join(report_lines(rep)))
    print(f"Saved to data/{LATEST} and the benchmark history.")
    return 0


def add_parser(sub):
    s = sub.add_parser("bench", help="benchmarks that drive the testbed itself (router: the chat/call pipeline)")
    s.add_argument("what", choices=["router"], help="router: time routing plus the NVIDIA calls it makes")
    s.add_argument("--runs", type=int, default=3, help="repeat each prompt N times (median/p95 per route)")
    s.add_argument("--call", action="store_true", help="call mode: the voice-call pipeline with a spoken reply")
    s.add_argument("--only", help="comma-separated prompt ids or routes (" + ",".join(p[0] for p in PROMPTS) + ")")
    s.add_argument("--prompt", action="append", help="add your own prompt (repeatable)")
    s.add_argument("--compare", action="store_true", help="also call the same models directly to show the overhead")
    s.add_argument("--show", action="store_true", help="show the last router benchmark")
    s.set_defaults(fn=cmd_bench)
