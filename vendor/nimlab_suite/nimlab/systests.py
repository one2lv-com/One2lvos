"""The Tests menu (3.7.4): one test per part of the lab.

`nimlab test` lists them, `nimlab test <name>` runs one, `nimlab test all`
runs everything and prints a pass / fail table. The launcher's main menu has
the same list under Tests. Each test reuses the lab's own checks (memory
roundtrip, the server self-test, the gRPC check, the tunnel test, ...)
through a small context object (Live), so tests/test_v374_systests.py runs
every one of them against fakes.

A result is pass / fail / skip with a reason, the time it took, a bug ID on
failure (from the bug log) and what to do next. Tests marked live send real
requests on your NVIDIA key. Every run is saved to data/test_history.jsonl.
"""

import json
import os
import tempfile
import time

PASS, FAIL, SKIP = "pass", "fail", "skip"
HISTORY_FILE = "test_history.jsonl"
HISTORY_KEEP = 300


class Result:
    def __init__(self, status, detail="", fix="", rows=None):
        self.status, self.detail, self.fix = status, detail, fix
        self.rows = rows or []          # [(ok, message)] sub-checks
        self.ms = 0
        self.bug = None


def ok(detail, rows=None):
    return Result(PASS, detail, rows=rows)


def fail(detail, fix="", rows=None):
    return Result(FAIL, detail, fix, rows)


def skip(detail, fix=""):
    return Result(SKIP, detail, fix)


def from_rows(rows, what, fix=""):
    rows = [(bool(a), str(b)) for a, b in rows]
    if not rows:
        return skip(f"{what}: nothing to check")
    bad = [m for a, m in rows if not a]
    return (fail(bad[0], fix, rows) if bad else ok(rows[-1][1] if len(rows) == 1 else
                                                    f"{what}: {len(rows)} checks passed", rows))


class Test:
    def __init__(self, name, title, fn, live=False, symptom=None, fix=""):
        self.name, self.title, self.fn = name, title, fn
        self.live, self.symptom, self.fix = live, symptom, fix


# ---------------------------------------------------------------------------
# the context: everything a test touches goes through here (fakes replace it)
# ---------------------------------------------------------------------------
class Live:
    def __init__(self, log=None):
        self._ent = None
        self._roundtrip = None
        self.log = log or (lambda *a: None)

    def host(self):
        from . import hostenv
        return hostenv.detect()

    def host_checks(self):
        from . import hostenv
        return hostenv.checks()

    def key(self):
        from .core import load_api_key
        return load_api_key()

    def entity(self):
        if self._ent is None:
            from .entity import Entity
            self._ent = Entity(log=lambda *a: None)
        return self._ent

    def list_models(self):
        return self.entity().client.list_models()

    def roles_set(self):
        ent = self.entity()
        return [k for k in ("router", "persona") if ent.is_set(k)]

    def role_ping(self, role):
        ent = self.entity()
        return ent.chat_step(role, [{"role": "user", "content": "Reply with the single word: ok"}],
                             temperature=0, max_tokens=8, with_tools=False)

    def grpc_rows(self):
        from . import nvcf_grpc, store
        good, detail = nvcf_grpc.available()
        if not good:
            return None, detail
        targets = [r["model"] for r in nvcf_grpc.rows() if r["function_id"] and r["kind"] in nvcf_grpc.RIVA_KINDS]
        if not targets:
            return [], "no gRPC speech models with a function ID"
        cli = nvcf_grpc.client()
        rows = []
        for m in targets:
            g, lat, det = cli.check(nvcf_grpc.function_id(m), nvcf_grpc.kind_of(m, nvcf_grpc.record(m)))
            store.note_grpc_check(m, g, det, latency=lat)
            rows.append((g, f"{m}: {det} ({lat}s)"))
        return rows, ""

    def is_set(self, role):
        return self.entity().is_set(role)

    def tts(self):
        path, r = self.entity().synthesize_voice("This is a Nim Lab test.", play=False)
        return path, r

    def asr(self):
        from . import server as S
        fd, p = tempfile.mkstemp(prefix="nimlab_test_", suffix=".wav")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(S.test_wav())
            return self.entity().run_role("asr", audio=p)
        finally:
            try:
                os.unlink(p)
            except OSError:
                pass

    def embed(self):
        return self.entity().memory.embed("Nim Lab embedding test", "query")

    def memory(self):
        return self.entity().memory

    def memory_backend_rows(self):
        m = self.memory()
        if m.settings.get("backend") == "off":
            return None
        if m.backend is None:
            m._connect()
        if m.backend is None:
            return [(False, f"backend {m.settings.get('backend')}: {m.offline}")]
        return [(True, f"connected: {m.backend_name}")] + list(m.backend.test())

    def memory_roundtrip(self):
        if self._roundtrip is None:
            m = self.memory()
            if m.settings.get("backend") == "off":
                self._roundtrip = []
            else:
                self._roundtrip = m.roundtrip()
        return self._roundtrip

    def mcp(self):
        return self.entity().mcp

    def server_rows(self):
        from . import servemenu
        return servemenu.run_self_test(out=lambda *a: None, make_entity=self.entity, full=False)

    def tunnel(self, chat=False):
        from . import commands
        return commands.tunnel_test(chat=chat)

    def tunnel_mode(self):
        from . import server as S, tunnel
        return tunnel.settings_of(S.load_settings()).get("mode") or "off"

    def telegram(self):
        from . import service, telegram as T
        tok = T.load_token()
        t = T.settings()
        info = {"token": bool(tok), "owner": t.get("owner"), "allow": list(t.get("allow") or []),
                "pollers": [p for p in service.find_processes() if p[1] == "telegram"],
                "lock": T.PollerLock().holder(), "me": None, "error": None,
                "in_service": bool(service.settings().get("telegram"))}
        if tok:
            try:
                info["me"] = T.Bot(tok).call("getMe")
            except Exception as e:  # noqa: BLE001
                info["error"] = str(e)
        return info

    def service(self):
        from . import service as SV
        st = SV.read_state()
        holder = SV.SupervisorLock().holder()
        return {"holder": holder, "children": sorted((st.get("children") or {}).keys()) if holder else [],
                "want": sorted(SV.child_commands().keys()), "strays": SV.strays(),
                "installed": SV.Manager().installed(), "backend": SV.Manager().backend}

    def scheduler(self):
        from . import scheduler as SC
        return {"jobs": SC.load_jobs(), "holder": SC.lock_holder()}

    def selfadmin(self):
        from . import config, selfadmin as SA
        sa = SA.settings(config.load_json(config.CLUSTER_CONFIG, {}) or {})
        return {"enabled": bool(sa.get("enabled")), "shell": bool(sa.get("shell")),
                "key": bool(SA.load_admin_key()), "dir": SA._dir()}

    def bug_dir(self):
        from . import bugs
        return bugs.bug_dir(), bool(bugs.settings().get("enabled", True))

    def config_problems(self):
        from . import config, configlint
        out = []
        for p in (config.CLUSTER_CONFIG,):
            try:
                with open(p, encoding="utf-8") as f:
                    json.load(f)
            except FileNotFoundError:
                out.append(f"{os.path.basename(p)} is missing")
            except ValueError as e:
                out.append(f"{os.path.basename(p)} is not valid JSON: {e}")
        if not out:
            out += configlint.lines(config.load_cluster_config())
        return out

    def route(self, text):
        return self.entity().route_turn(text)


# ---------------------------------------------------------------------------
# the tests
# ---------------------------------------------------------------------------
def t_platform(ctx):
    rows = ctx.host_checks()
    bad = [m + (f" -> {f.splitlines()[0]}" if f else "") for lv, m, f in rows if lv == "fail"]
    warn = [m for lv, m, f in rows if lv == "warn"]
    sub = [(lv != "fail", m) for lv, m, f in rows if lv != "info"]
    if bad:
        return fail(bad[0], "nimlab platform", sub)
    return ok(f"{len(sub)} checks, {len(warn)} warning(s)" + (f": {warn[0]}" if warn else ""), sub)


def t_key(ctx):
    k = ctx.key()
    if not k:
        return fail("no NVIDIA key found", "nimlab setup key, then nimlab persist-key")
    if not k.startswith("nvapi-"):
        return fail("the key does not start with nvapi-", "nimlab setup key")
    return ok(f"key found (nvapi-...{k[-4:]})")


def t_catalog(ctx):
    if not ctx.key():
        return skip("no NVIDIA key", "nimlab setup key")
    r = ctx.list_models()
    if not r.ok:
        return fail(f"model catalog: {r.error}", "nimlab test key; check the internet connection")
    n = len((r.data or {}).get("data") or []) if isinstance(r.data, dict) else 0
    return ok(f"catalog reachable: {n} models ({int((r.latency or 0) * 1000)} ms)")


def t_roles(ctx):
    if not ctx.key():
        return skip("no NVIDIA key", "nimlab setup key")
    roles = ctx.roles_set()
    if not roles:
        return skip("no router or persona role set", "nimlab setup roles")
    rows = []
    for role in roles:
        r = ctx.role_ping(role)
        rows.append((bool(r.ok), f"{role}: " + (f"answered in {int((r.latency or 0) * 1000)} ms" if r.ok
                                                 else f"{r.error}")))
    return from_rows(rows, "roles", "nimlab roles; nimlab setup roles")


def t_grpc(ctx):
    if not ctx.key():
        return skip("no NVIDIA key", "nimlab setup key")
    rows, why = ctx.grpc_rows()
    if rows is None:
        return skip(why, "nimlab setup deps (installs nvidia-riva-client)")
    if not rows:
        return skip(why, "nimlab grpc fill")
    return from_rows(rows, "gRPC function IDs", "nimlab grpc list, then nimlab grpc fill")


def t_tts(ctx):
    if not ctx.key():
        return skip("no NVIDIA key", "nimlab setup key")
    if not ctx.is_set("tts"):
        return skip("the TTS role is not set", "nimlab setup roles")
    path, r = ctx.tts()
    if not path:
        return fail(f"speech: {r.error}", "nimlab grpc check; nimlab roles")
    return ok(f"spoke a test line ({int((r.latency or 0) * 1000)} ms)")


def t_asr(ctx):
    if not ctx.key():
        return skip("no NVIDIA key", "nimlab setup key")
    if not ctx.is_set("asr"):
        return skip("the ASR role is not set", "nimlab setup roles")
    r = ctx.asr()
    if not r.ok:
        return fail(f"transcription: {r.error}", "nimlab grpc check; nimlab roles")
    return ok(f"transcribed a synthetic tone ({int((r.latency or 0) * 1000)} ms"
              + (f", heard {r.text[:40]!r})" if r.text else ", no words, as expected)"))


def t_embeddings(ctx):
    m = ctx.memory()
    if m.settings.get("backend") == "off":
        return skip("long-term memory is off", "nimlab memory setup")
    t0 = time.monotonic()
    try:
        vec = ctx.embed()
    except Exception as e:  # noqa: BLE001
        return fail(f"embedding: {e}", "nimlab memory embed <provider> <model>")
    if not vec:
        return fail("the embedder returned no vector", "nimlab memory embed <provider> <model>")
    return ok(f"{len(vec)} dimensions in {int((time.monotonic() - t0) * 1000)} ms")


def t_memory_backend(ctx):
    rows = ctx.memory_backend_rows()
    if rows is None:
        return skip("long-term memory is off", "nimlab memory setup")
    return from_rows(rows, "memory backend", "nimlab memory status; nimlab memory setup")


def t_memory_write(ctx):
    rows = ctx.memory_roundtrip()
    if not rows:
        return skip("long-term memory is off", "nimlab memory setup")
    first = rows[0]
    cleanup = [r for r in rows if "remove" in r[1]]
    sub = [first] + cleanup
    return from_rows(sub, "memory write", "nimlab memory test")


def t_memory_recall(ctx):
    rows = ctx.memory_roundtrip()
    if not rows:
        return skip("long-term memory is off", "nimlab memory setup")
    return from_rows(rows, "memory recall", "nimlab memory pending; nimlab memory embed-pending")


SAFE_TOOLS = ("whoami", "get_me", "list_tools", "get_system_stats", "hf_whoami", "ping")


def t_mcp(ctx):
    c = ctx.mcp()
    if c is None:
        return skip("MCP is off or has no URL", "nimlab setup mcp")
    t0 = time.monotonic()
    try:
        tools = c.list_tools()
    except Exception as e:  # noqa: BLE001
        return fail(f"connect: {e}", "nimlab mcp show; nimlab mcp auth bearer; nimlab mcp set-key")
    rows = [(True, f"connected and listed {len(tools)} tools in {int((time.monotonic() - t0) * 1000)} ms")]
    if not tools:
        return fail("connected, but the server lists 0 tools", "turn tools on in the MCP admin console", rows)
    names = [t.get("name") for t in tools if isinstance(t, dict)]
    pick = next((n for s in SAFE_TOOLS for n in names if n and (n == s or n.endswith("__" + s))), None)
    if pick:
        try:
            c.call_tool(pick, {})
            rows.append((True, f"called {pick} (read-only)"))
        except Exception as e:  # noqa: BLE001
            rows.append((False, f"calling {pick}: {e}"))
    else:
        rows.append((True, "no known read-only tool to call; listing worked"))
    return from_rows(rows, "MCP", "nimlab mcp test")


def t_server(ctx):
    if not ctx.key():
        return skip("no NVIDIA key", "nimlab setup key")
    rows = ctx.server_rows()
    if not rows:
        return fail("the self-test ran no checks", "nimlab serve test")
    sub = [(st != "FAIL", f"{name}: {st}" + (f" ({det})" if det and st == "FAIL" else ""))
           for name, st, det, *_ in rows]
    return from_rows(sub, "server self-test", "nimlab serve test; nimlab bugs list")


def t_tunnel(ctx):
    if ctx.tunnel_mode() == "off":
        r = ctx.tunnel()
        if not r.get("url"):
            return skip("the tunnel is off", "nimlab serve tunnel quick")
    else:
        r = ctx.tunnel()
    if r["ok"]:
        return ok(r["verdict"])
    return fail(r["verdict"], "nimlab serve tunnel status; nimlab service restart")


def t_telegram(ctx):
    i = ctx.telegram()
    if not i["token"]:
        return skip("no bot token", "nimlab telegram set-token")
    rows = []
    rows.append((i["me"] is not None, f"getMe: @{(i['me'] or {}).get('username')}" if i["me"]
                 else f"getMe failed: {i['error']}"))
    n = len(i["pollers"])
    rows.append((n == 1, "one poller running" if n == 1 else (
        "no poller running" if n == 0 else f"{n} pollers running (duplicate replies)")))
    rows.append((bool(i["owner"]), f"owner set ({i['owner']})" if i["owner"] else "no owner yet"))
    fix = ("nimlab service cleanup; nimlab telegram status" if n > 1 else
           "nimlab telegram allow --capture" if not i["owner"] else
           "nimlab service telegram on (or nimlab telegram start)" if n == 0 else "nimlab telegram test")
    return from_rows(rows, "Telegram", fix)


def t_service(ctx):
    s = ctx.service()
    if not s["holder"]:
        if s["strays"]:
            return fail(f"no supervisor, but {len(s['strays'])} stray process(es)", "nimlab service cleanup")
        return skip("the service is not running", "nimlab service start" if s["installed"]
                    else "nimlab service install")
    rows = [(True, f"supervisor running (pid {s['holder']}, {s['backend']})")]
    rows.append((s["children"] == s["want"], f"children {', '.join(s['children']) or 'none'}"
                 + ("" if s["children"] == s["want"] else f"; the config wants {', '.join(s['want'])}")))
    rows.append((not s["strays"], "no stray copies" if not s["strays"] else
                 f"{len(s['strays'])} stray copies (pids {', '.join(str(p[0]) for p in s['strays'])})"))
    return from_rows(rows, "service", "nimlab service cleanup; nimlab service restart")


def t_scheduler(ctx):
    """3.8.0: every job's schedule parses and has a next run, no broken
    jobs, and the scheduler runs when jobs are enabled."""
    fn = getattr(ctx, "scheduler", None)
    if fn is not None:
        info = fn()
    else:
        from . import scheduler as SC
        info = {"jobs": SC.load_jobs(), "holder": SC.lock_holder()}
    from . import schedule as S
    jobs = info["jobs"]
    on = {n: j for n, j in jobs.items() if j.get("enabled")}
    rows = []
    for n, j in sorted(jobs.items()):
        why = S.validate(j.get("schedule", ""))
        if why:
            rows.append((False, f"{n}: {why}"))
            continue
        st = j.get("state") or {}
        if st.get("state") == "BROKEN":
            rows.append((False, f"{n}: broken after {st.get('failures_in_a_row')} failures in a row "
                                f"(last bug {st.get('last_bug') or '-'})"))
        elif n in on:
            nxt = S.next_run(j["schedule"], anchor=j.get("start_date") or j.get("created_at"),
                             start=j.get("start_date"), end=j.get("end_date"))
            rows.append((True, f"{n}: next run {S.fmt(nxt)}" if nxt else f"{n}: no more runs"))
    if on:
        rows.append((bool(info["holder"]), f"scheduler running (pid {info['holder']})" if info["holder"] else
                     f"{len(on)} jobs enabled but the scheduler is not running"))
    elif not rows:
        return skip("no jobs enabled (the heartbeat is off)", "nimlab heartbeat enable")
    return from_rows(rows, "scheduler", "nimlab jobs list; nimlab service start")


def t_selfadmin(ctx):
    s = ctx.selfadmin()
    if not s["enabled"]:
        return skip("self-admin is off", "nimlab selfadmin on")
    rows = [(True, "self-admin on" + (", shell on" if s["shell"] else "")),
            (s["key"], "admin key made" if s["key"] else "no admin key")]
    try:
        p = os.path.join(s["dir"], ".write_test")
        with open(p, "w") as f:
            f.write("x")
        os.unlink(p)
        rows.append((True, "audit folder writable"))
    except OSError as e:
        rows.append((False, f"audit folder not writable: {e}"))
    return from_rows(rows, "self-admin", "nimlab selfadmin admin-key")


def t_buglog(ctx):
    d, enabled = ctx.bug_dir()
    if not enabled:
        return skip("the bug log is off", "bug_log_settings.enabled in config_cluster.json")
    try:
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, ".write_test")
        with open(p, "w") as f:
            f.write("x")
        os.unlink(p)
    except OSError as e:
        return fail(f"bug log folder not writable: {e}", "check the data folder's permissions")
    return ok(f"bug log writable ({d})")


def t_config(ctx):
    probs = ctx.config_problems()
    if probs:
        return fail(probs[0], "nimlab doctor", [(False, p) for p in probs])
    return ok("config_cluster.json parses; speech URLs and role models look right")


def t_router(ctx):
    if not ctx.key():
        return skip("no NVIDIA key", "nimlab setup key")
    t0 = time.monotonic()
    rt = ctx.route("Compare two ways to cache API responses and recommend one.")
    ms = int((time.monotonic() - t0) * 1000)
    if not rt or not rt.get("role"):
        return fail("the router returned no role", "nimlab bench router --runs 1")
    if rt.get("router_ok") is False:
        return fail(f"router call failed: {rt.get('router_error')} (fell back to {rt['role']})",
                    "nimlab roles; nimlab bench router --runs 1")
    return ok(f"routed to {rt['role']} via {rt.get('via')} in {ms} ms")


TESTS = [
    Test("platform", "Platform: Python, venv, ffmpeg, cloudflared, linger, RAM/swap", t_platform),
    Test("key", "NVIDIA key present", t_key),
    Test("catalog", "Model catalog reachable", t_catalog, live=True),
    Test("roles", "Router and persona roles answer (one short call each)", t_roles, live=True),
    Test("grpc", "gRPC function IDs (ASR/TTS check)", t_grpc, live=True, symptom="grpc"),
    Test("tts", "Speech: speak a test line", t_tts, live=True, symptom="grpc"),
    Test("asr", "Transcription: a synthetic tone", t_asr, live=True, symptom="grpc"),
    Test("embeddings", "Embeddings: one vector", t_embeddings, live=True, symptom="memory"),
    Test("memory-backend", "Memory backend connection (Oracle, ORDS or local)", t_memory_backend,
         symptom="memory"),
    Test("memory-write", "Memory write (and clean up)", t_memory_write, live=True, symptom="memory"),
    Test("memory-recall", "Memory recall: write a marker, recall it, clean up", t_memory_recall, live=True,
         symptom="memory"),
    Test("mcp", "MCP: connect, list tools, one read-only call", t_mcp, symptom="mcp"),
    Test("server", "Local server self-test through the one model name", t_server, live=True,
         symptom="selftest"),
    Test("tunnel", "Tunnel: /v1/models through the public URL with the server key", t_tunnel, symptom="tunnel"),
    Test("telegram", "Telegram: getMe, exactly one poller, owner set", t_telegram, symptom="telegram-twice"),
    Test("service", "Service: supervisor running, children match the config, no strays", t_service,
         symptom="stray-copies"),
    Test("scheduler", "Scheduler: jobs parse, next runs, scheduler running", t_scheduler, symptom="scheduler"),
    Test("selfadmin", "Self-admin: key and audit folder", t_selfadmin),
    Test("buglog", "Bug log writable", t_buglog),
    Test("config", "Config lint", t_config),
    Test("router", "Router: one turn through the real pipeline", t_router, live=True),
]
BY_NAME = {t.name: t for t in TESTS}
ALIASES = {"memory": "memory-recall", "recall": "memory-recall", "write": "memory-write",
           "backend": "memory-backend", "embed": "embeddings", "models": "catalog", "bugs": "buglog",
           "lint": "config", "serve": "server", "supervisor": "service", "tg": "telegram", "speech": "tts"}


def find(name):
    n = (name or "").strip().lower()
    return BY_NAME.get(n) or BY_NAME.get(ALIASES.get(n, ""))


def run_one(test, ctx=None, record_bug=True):
    ctx = ctx or Live()
    t0 = time.monotonic()
    try:
        r = test.fn(ctx)
    except Exception as e:  # noqa: BLE001 - a broken test is a failed test, never a traceback
        r = fail(f"the test broke: {type(e).__name__}: {str(e)[:200]}", test.fix)
    r.ms = int((time.monotonic() - t0) * 1000)
    if r.status == FAIL:
        if not r.fix:
            r.fix = test.fix
        if test.symptom and "troubleshoot" not in r.fix:
            r.fix = (r.fix + "; " if r.fix else "") + f"see: nimlab troubleshoot {test.symptom}"
        if record_bug:
            try:
                from . import bugs
                r.bug = bugs.record("test", f"test {test.name}: {r.detail}", where=f"systests.{test.name}")
            except Exception:  # noqa: BLE001
                r.bug = None
    return r


def history_path():
    from . import store
    return os.path.join(store.data_dir(), HISTORY_FILE)


def save_history(results, when=None):
    """Append one run ({name: Result}) to data/test_history.jsonl."""
    try:
        p = history_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        row = {"at": when or time.strftime("%Y-%m-%d %H:%M:%S"),
               "results": {n: {"status": r.status, "detail": r.detail[:300], "ms": r.ms, "bug": r.bug}
                           for n, r in results.items()}}
        lines = []
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                lines = f.read().splitlines()[-(HISTORY_KEEP - 1):]
        lines.append(json.dumps(row))
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except OSError:
        return False


def load_history(limit=10):
    try:
        with open(history_path(), encoding="utf-8") as f:
            rows = [json.loads(x) for x in f.read().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []
    return rows[-limit:]


TAGS = {PASS: "PASS", FAIL: "FAIL", SKIP: "skip"}


def result_lines(test, r):
    out = [f"[{TAGS[r.status]}] {test.name:<15} {r.ms:>6} ms  {r.detail}"]
    if r.status == FAIL:
        if r.bug:
            out.append(f"       bug ID: {r.bug} (nimlab bugs show {r.bug})")
        if r.fix:
            out.append(f"       next: {r.fix}")
    elif r.status == SKIP and r.fix:
        out.append(f"       to enable: {r.fix}")
    return out


def table(results, width=72):
    """The pass / fail table. width trims the detail column so the table
    fits a phone screen (the terminal passes screen_width())."""
    width = max(40, int(width or 72))
    keep = max(8, min(60, width - 34))
    out = [f"{'test':<15} {'result':<6} {'time':>8}  detail", "-" * width]
    for t in TESTS:
        r = results.get(t.name)
        if r is None:
            continue
        out.append(f"{t.name:<15} {TAGS[r.status]:<6} {r.ms:>6}ms  {r.detail[:keep]}")
    n = {s: sum(1 for r in results.values() if r.status == s) for s in (PASS, FAIL, SKIP)}
    out.append("-" * width)
    out.append(f"{n[PASS]} passed, {n[FAIL]} failed, {n[SKIP]} skipped")
    return out


def run_all(ctx=None, out=print, names=None, color=False):
    """Run the tests. color=True only from the terminal paths (menu, CLI):
    the lines are coloured there and stay plain everywhere else."""
    from . import colors as C, paint
    ctx = ctx or Live()
    results = {}
    for t in TESTS:
        if names and t.name not in names:
            continue
        head = f"... {t.name}{' (real requests)' if t.live else ''}"
        out(C.dim(head) if color else head)
        r = run_one(t, ctx)
        results[t.name] = r
        lines = result_lines(t, r)
        for ln in (paint.result_lines(lines) if color else lines):
            out(ln)
    out("")
    if color:
        for ln in paint.table_lines(table(results, width=min(72, C.screen_width()))):
            out(ln)
    else:
        for ln in table(results):
            out(ln)
    save_history(results)
    return results


def list_lines():
    out = ["Tests (nimlab test <name>, or nimlab test all). * = sends real requests on your NVIDIA key."]
    for i, t in enumerate(TESTS, 1):
        out.append(f"  {i:>2}) {t.name:<15}{'*' if t.live else ' '} {t.title}")
    return out


def _result_block(t, r, color=False):
    lines = result_lines(t, r) + [f"       {'ok' if a else 'x '} {m}" for a, m in r.rows]
    if color:
        from . import paint
        return paint.result_lines(lines)
    return lines


def list_screen():
    """The test list as menu entries (colour on a terminal, 3.8.1)."""
    from . import colors as C
    out = []
    for i, t in enumerate(TESTS, 1):
        mark = C.warn("*") if t.live else " "
        if C.enabled():
            room = max(10, C.screen_width() - 23)
            title = t.title if len(t.title) <= room else t.title[:room - 1].rstrip() + "~"
            out.append(C.entry(i, f"{t.name:<15}", "", pad=0).rstrip() + mark + " " + C.dim(title))
        else:
            out.append(f"  {i:>2}) {t.name:<15}{'*' if t.live else ' '} {t.title}")
    return out


def menu(ask=input, say=print, ctx=None):
    from . import colors as C, paint
    while True:
        say("")
        say(C.header("TESTS"))
        say(C.rule(min(50, C.screen_width())))
        say(C.section("One per part of the lab"))
        for ln in list_screen():
            say(ln)
        say(C.section("More"))
        say(C.entry("a", "Run all", "with a pass / fail table", pad=16))
        say(C.entry("h", "Last runs", "saved history", pad=16))
        say(C.entry(0, "Back"))
        say("  " + C.warn("*") + C.dim(" = sends real requests on your NVIDIA key"))
        try:
            c = (ask(paint.ask("\nRun which? ")) or "b").strip().lower()
        except EOFError:
            c = "b"
        if c in ("b", "q", "0", ""):
            return 0
        if c == "a":
            run_all(ctx, say, color=True)
        elif c == "h":
            for ln in history_lines():
                say(paint.summary(ln))
        else:
            t = TESTS[int(c) - 1] if c.isdigit() and 1 <= int(c) <= len(TESTS) else find(c)
            if not t:
                continue
            r = run_one(t, ctx or Live())
            for ln in _result_block(t, r, color=True):
                say(ln)
            if t.name == "tunnel" and r.status == PASS:
                a = (ask(paint.ask("Also send one short chat turn through the tunnel (one real request)? [y/N]: ")) or "")
                if a.strip().lower() in ("y", "yes"):
                    from . import commands
                    for ln in commands.tunnel_screen(commands.tunnel_test(chat=True))[2:]:
                        say(ln)
            save_history({t.name: r})
        try:
            ask(paint.ask("Press Enter to go back to the tests "))
        except EOFError:
            return 0


def history_lines(limit=10):
    rows = load_history(limit)
    if not rows:
        return ["No test runs saved yet."]
    out = []
    for row in rows:
        res = row.get("results") or {}
        n = {s: sum(1 for v in res.values() if v.get("status") == s) for s in (PASS, FAIL, SKIP)}
        failed = [k for k, v in res.items() if v.get("status") == FAIL]
        out.append(f"{row.get('at')}: {n[PASS]} passed, {n[FAIL]} failed, {n[SKIP]} skipped"
                   + (f" (failed: {', '.join(failed)})" if failed else ""))
    return out


def cmd_test(args):
    name = (getattr(args, "name", None) or "").strip()
    if getattr(args, "menu", False):
        return menu()
    from . import colors as C, paint
    if not name:
        lines = list_lines()
        print(C.section(lines[0]) if C.enabled() else lines[0])
        print("\n".join(list_screen()))
        return 0
    if name == "history":
        print("\n".join(paint.summary(ln) for ln in history_lines()))
        return 0
    if name == "all":
        res = run_all(color=True)
        return 1 if any(r.status == FAIL for r in res.values()) else 0
    t = find(name)
    if not t:
        print(f"No test '{name}'. Tests: {', '.join(BY_NAME)}")
        return 2
    r = run_one(t)
    for ln in _result_block(t, r, color=True):
        print(ln)
    if t.name == "tunnel" and r.status == PASS and getattr(args, "chat", False):
        from . import commands
        print("\n".join(commands.tunnel_screen(commands.tunnel_test(chat=True))[2:]))
    save_history({t.name: r})
    return 1 if r.status == FAIL else 0


def add_parser(sub):
    p = sub.add_parser("test", help="Tests: one per part of the lab (test, test <name>, test all)")
    p.add_argument("name", nargs="?", help="a test name, all, or history")
    p.add_argument("--chat", action="store_true", help="tunnel: also send one chat turn through it")
    p.add_argument("--menu", action="store_true", help="the interactive menu (the launcher uses this)")
    p.set_defaults(fn=cmd_test)
