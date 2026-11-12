"""Command-line entry point: `python3 -m nimlab <command>`.

start.sh calls these subcommands instead of embedding Python source in the
shell script. Data travels through argv, stdin and environment variables
only; nothing user-typed or secret is ever spliced into code.
"""

import argparse
import os
import shlex
import sys

from . import config, roles as R, store
from .core import key_source, load_api_key, mask

ENV_FILE = os.path.join(os.path.expanduser("~"), ".nimlab_env")
BASHRC = os.path.join(os.path.expanduser("~"), ".bashrc")
SOURCE_LINE = '[ -f "$HOME/.nimlab_env" ] && . "$HOME/.nimlab_env"  # nimlab'


# ---------------------------------------------------------------------------
# status / key
# ---------------------------------------------------------------------------
def cmd_status(args):
    if args.field == "key":
        key = load_api_key()
        print(f"{mask(key)} ({key_source()})" if key else "[NOT SET]")
        return 0 if key else 1
    if args.field == "live":
        from .router import load_live_fleet
        print(len(load_live_fleet()))
    elif args.field == "inventory":
        print(len(store.key_list()))
    elif args.field == "memory":
        print(len(store.load(store.MEMORY)))
    elif args.field in ("catalog", "discovered"):
        print(len(store.load(store.DISCOVERED)["models"]))
    elif args.field == "endpoints":
        print(len(store.load(store.ENDPOINTS)["endpoints"]))
    elif args.field == "roles":
        for line in role_summary(compact=True):
            print(line)
    return 0


def role_summary(compact=False, cluster=None):
    """Lines describing the 16 roles: display name, backend, target, flags."""
    cluster = cluster or config.load_cluster_config()
    roles = cluster.get("roles", {})
    verified = set(store.verified_ids())
    lines = []
    for i, key in enumerate(R.ROLE_KEYS, 1):
        v = R.normalize(roles.get(key), key)
        if not R.is_set(v):
            tag, target = "-----", "(unset)"
        elif v["backend"] == R.MCP:
            tag, target = "MCP  ", v["tool"]
        else:
            tag, target = "model", v["model"]
        flags = []
        if v["backend"] == R.MODEL and v.get("model") and verified and v["model"] not in verified:
            flags.append("not 200-tested")
        if key == "tts" and R.clone_text(v):
            flags.append(R.clone_text(v))
        d = R.BY_KEY[key]
        if d.support == R.NO:
            flags.append("no NVIDIA API")
        elif d.support == R.PARTIAL and not compact:
            flags.append("NVIDIA API partial")
        tail = f"  ({'; '.join(flags)})" if flags else ""
        if compact:
            name = d.name if len(d.name) <= 30 else d.name[:29] + "~"
            lines.append(f"{i:>2} {name:<30} {tag} {target}{tail}")
        else:
            lines.append(f"  {i:>2}. {d.name:<56} [{tag.strip()}] {target}{tail}")
            if v["backend"] == R.MCP and v.get("arg_map"):
                lines.append("        args: " + ", ".join(f"{a}->{b}" for a, b in v["arg_map"].items()))
            if v.get("endpoint"):
                lines.append(f"        endpoint: {v['endpoint']}")
    extra = [k for k in roles if k not in R.BY_KEY]
    if extra and not compact:
        lines.append("  Other role keys kept: " + ", ".join(f"{k} = {R.describe(roles[k])}" for k in extra))
    return lines


def cmd_roles(args):
    cluster = config.load_cluster_config()
    if args.action == "migrate":
        raw = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        new, changes = config.migrate_cluster(raw, *config._fleet_and_kinds())
        if changes:
            config.save_json(config.CLUSTER_CONFIG, new)
        print("\n".join(changes) if changes else "Roles already use the 16 categories; nothing to change.")
        return 0
    if args.action == "candidates":
        if not args.role or args.role not in R.BY_KEY:
            print("Give a role key: " + ", ".join(R.ROLE_KEYS))
            return 2
        kinds, infos = R.kinds_from_store()
        verified = store.verified_ids()
        pool = verified if args.scope == "verified" else sorted(set(store.load(store.DISCOVERED)["models"]) |
                                                               set(verified), key=str.lower)
        suited, possible, _ = R.candidates(args.role, pool, kinds, infos)
        d = R.BY_KEY[args.role]
        print(f"{d.name}: {len(suited)} suited, {len(possible)} possible of {len(pool)} {args.scope}")
        if d.note:
            print(f"  {d.note}")
        for m in suited:
            print(f"  + {m}")
        for m in possible:
            print(f"  ~ {m}")
        return 0
    print(f"ROLES (config_cluster.json, {len(R.ROLE_KEYS)} categories)")
    for line in role_summary(cluster=cluster):
        print(line)
    return 0


def cmd_persist_key(args):
    """Persist the key from the environment into ~/.nimlab_env (mode 600),
    sourced from ~/.bashrc. The key is read from the environment, never argv."""
    key = load_api_key()
    if not key:
        print("No NVIDIA_API_KEY / NGC_API_KEY in the environment.", file=sys.stderr)
        return 1
    env_file = args.env_file or ENV_FILE
    fd = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f"export NVIDIA_API_KEY={shlex.quote(key)}\n")
    os.chmod(env_file, 0o600)
    bashrc = args.bashrc or BASHRC
    lines = []
    if os.path.exists(bashrc):
        with open(bashrc, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    # drop legacy plain-text exports written by the old launcher
    kept = [ln for ln in lines if not ln.strip().startswith("export NVIDIA_API_KEY=")]
    if SOURCE_LINE not in kept:
        kept.append(SOURCE_LINE)
    with open(bashrc, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + "\n")
    print(f"Saved {mask(key)} to {env_file} (owner-only permissions); sourced from {bashrc}.")
    return 0


def cmd_forget_key(args):
    env_file = args.env_file or ENV_FILE
    if os.path.exists(env_file):
        os.remove(env_file)
    bashrc = args.bashrc or BASHRC
    if os.path.exists(bashrc):
        with open(bashrc, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        kept = [ln for ln in lines if ln != SOURCE_LINE and not ln.strip().startswith("export NVIDIA_API_KEY=")]
        with open(bashrc, "w", encoding="utf-8") as f:
            f.write("\n".join(kept) + ("\n" if kept else ""))
    print("Removed the persisted key.")
    return 0


# ---------------------------------------------------------------------------
# views
# ---------------------------------------------------------------------------
def cmd_fleet(args):
    from .router import load_live_fleet
    live = load_live_fleet()
    if not live:
        print("No verified 200 OK models yet (data/models_verified.json is empty).\n"
              "Run discover, then the sweep (launcher option 2).")
        return 0
    print(f"Total Live Models: {len(live)}\n")
    print(f"{'#':<3} | {'Model ID':<44} | {'Kind':<16} | Latency")
    print("-" * 78)
    for i, (m, v) in enumerate(sorted(live.items()), 1):
        lat = v.get("latency_sec", "N/A")
        print(f"{i:>3} | {m[:44]:<44} | {str(v.get('kind', 'chat'))[:16]:<16} | {lat}s")
    return 0


def cmd_data(args):
    if args.action == "migrate":
        store.reset()
        rep = store.migrate(log=print)
        store.ensure_all()
        print("Nothing to migrate: no pre-3.1 data files found." if rep is None else
              "Counts: " + ", ".join(f"{k} {v}" for k, v in rep["counts"].items()))
        return 0
    if args.action == "paths":
        for n in (store.ENDPOINTS, store.DISCOVERED, store.VERIFIED, store.BENCHMARK, store.BENCH_HISTORY,
                  store.PROBES, store.LEADERBOARD, store.ENTITY_SCORES, store.MEMORY, store.TEST_HISTORY):
            print(store.path(n))
        return 0
    if args.action == "show":
        if args.view not in store.VIEWS:
            print("Views: " + ", ".join(store.VIEWS))
            return 2
        rows = store.view(args.view)
        print(f"{args.view}: {len(rows)}")
        for mid, detail in rows[: args.limit or None]:
            print(f"  {mid:<60} {detail}")
        return 0
    o = store.overview()
    st = ", ".join(f"{k} {v}" for k, v in sorted(o["status"].items())) or "-"
    print(f"Data folder: {o['data_dir']}")
    print(f"  endpoints.json          {o['endpoints']} active endpoints, {o['endpoints_stale']} stale")
    print(f"  models_discovered.json  {o['discovered']} models ({st}); key list {o['key_list']}; "
          f"{o['discovered_removed']} removed")
    print(f"  models_verified.json    {o['verified']} verified 200 OK; {o['verified_dropped']} dropped")
    print(f"  probe_results.json      {o['probed']} probed, {o['failed']} failing, {o['untested']} never tested")
    print(f"  benchmark_latest.json   {o['benchmark'] or 'no run yet'}; history {o['benchmark_runs']} run(s)")
    print(f"  memory.json             {o['memories']} memories")
    print("Lists: python3 -m nimlab data show <" + "|".join(store.VIEWS) + ">")
    return 0


def cmd_report(args):
    b = store.latest_benchmark()
    if not isinstance(b, dict):
        print("No benchmark report yet. Run the benchmark suite first.")
        return 1
    print(f"Benchmark Generated: {b.get('timestamp', 'N/A')}\n")
    if b.get("reasoning"):
        print("[ REASONING / INSTRUCT LLMs ]")
        print(f"{'Model':<42} | {'Latency':<8} | {'Tokens':<6} | {'Tok/s':<7} | Logic")
        print("-" * 80)
        for r in b["reasoning"]:
            if "latency_sec" in r:
                print(f"{r['model'][:42]:<42} | {r.get('latency_sec', 0):>6}s | {r.get('tokens', 0):>6} | "
                      f"{str(r.get('tokens_per_sec', 'N/A')):>7} | {'PASS' if r.get('logic_pass') else 'FAIL'}")
    if b.get("embeddings"):
        print("\n[ EMBEDDING & RETRIEVAL ]")
        print(f"{'Model':<42} | {'Dims':<5} | {'Passage':<8} | {'Query':<8} | Recall@1")
        print("-" * 80)
        for r in b["embeddings"]:
            if "dimensions" in r:
                print(f"{r['model'][:42]:<42} | {r.get('dimensions', 0):>5} | {r.get('passage_latency_sec', 0):>6}s | "
                      f"{r.get('query_latency_sec', 0):>6}s | {'PASS' if r.get('recall_pass') else 'FAIL'}")
    if b.get("voice"):
        print("\n[ VOICE SYNTHESIS ]")
        print(f"{'Profile':<28} | {'Latency':<8} | {'Duration':<8} | RTF")
        print("-" * 60)
        for r in b["voice"]:
            if "latency_sec" in r and "duration_sec" in r:
                print(f"{r['profile'][:28]:<28} | {r['latency_sec']:>6}s | ~{r['duration_sec']:>5}s | {r['rtf']}")
    return 0


# ---------------------------------------------------------------------------
# tts
# ---------------------------------------------------------------------------
def cmd_tts(args):
    from .api import NimClient, play_audio, save_wav, wav_duration
    if not load_api_key():
        print("NVIDIA_API_KEY is not set.", file=sys.stderr)
        return 1
    text = args.text if args.text is not None else sys.stdin.read()
    text = text.strip() or "Sovereign Neural System online. Audio telemetry nominal."
    client = NimClient()
    r = client.tts(text, voice=args.voice)
    if not r.ok:
        print(f"[x] Synthesis error: {r.error}")
        return 1
    path = save_wav(r.data, f"magpie_{(args.voice or 'voice').split('.')[-1].lower()}")
    dur = wav_duration(r.data)
    rtf = round(r.latency / dur, 3) if dur else "n/a"
    print(f"[ok] Generated: {path} ({round(len(r.data) / 1024, 1)} KB, {dur}s) in {r.latency}s (RTF: {rtf})")
    if not args.no_play:
        player = play_audio(path)
        if not player:
            print("(no player found: install termux-api or mpv)")
    return 0


# ---------------------------------------------------------------------------
# judge
# ---------------------------------------------------------------------------
def _confirm(prompt, assume_yes=False):
    if assume_yes:
        return True
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _split(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def cmd_judge(args):
    from . import judge
    if args.action == "show":
        board = store.load(store.LEADERBOARD) or None
        ent = store.load(store.ENTITY_SCORES) or None
        if not board and not ent:
            print("No judge results yet. Run: python3 -m nimlab judge rank")
            return 1
        if board:
            print(judge.format_leaderboard(board))
        if ent:
            print("\n" + judge.format_entity(ent))
        return 0

    if args.action == "apply":
        board = store.load(store.LEADERBOARD) or None
        if not board:
            print("No leaderboard yet. Run: python3 -m nimlab judge rank")
            return 1
        cfg, _ = config.migrate_cluster(config.load_json(config.CLUSTER_CONFIG, {}) or {})
        roles = cfg.get("roles", {})
        wins = judge.winners_to_roles(board)
        types = _split(args.types)
        print("Proposed role changes:")
        pending = 0
        for t, e in board.get("types", {}).items():
            if types and t not in types or not e.get("winner"):
                continue
            role = judge.TYPE_TO_ROLE[t]
            if t != "tts" and R.normalize(roles.get(role))["backend"] == R.MCP:
                print(f"  {R.label(role):<40} {R.describe(roles.get(role))}  (MCP-backed: left as is)")
                continue
            cur = cfg.get("voice_settings", {}).get("voice_name") if t == "tts" else R.model_of(roles.get(role))
            new = e["winner"] if t == "tts" else wins.get(role)
            mark = "(unchanged)" if cur == new else ""
            pending += cur != new
            name = "TTS voice profile" if t == "tts" else R.label(role)
            print(f"  {name:<40} {cur or '-'}  ->  {new} {mark}")
        if not pending:
            print("Nothing to change.")
            return 0
        if not _confirm("Write these into config_cluster.json? [y/N]: ", args.yes):
            print("No changes written.")
            return 0
        changes = judge.apply_winners(board, types=types)
        print(f"Updated {len(changes)} setting(s) in config_cluster.json.")
        return 0

    if not load_api_key():
        print("NVIDIA_API_KEY is not set.", file=sys.stderr)
        return 1
    settings = {}
    if args.max_candidates:
        settings["max_candidates_per_type"] = args.max_candidates
    if args.repeats:
        settings["repeats"] = args.repeats
    if args.no_exec:
        settings["execute_generated_code"] = False

    if args.action == "rank":
        types = _split(args.types) or judge.ALL_TYPES
        bad = [t for t in types if t not in judge.TYPE_TO_ROLE]
        if bad:
            print(f"Unknown type(s): {bad}. Valid: {', '.join(judge.ALL_TYPES)}")
            return 2
        ranker = judge.Ranker(judges=_split(args.judges), settings=settings, seed=args.seed)
        print(f"Judges: {', '.join(ranker.judges) or '(none: objective metrics only)'} | seed {ranker.seed}")
        board = ranker.rank(types)
        store.save(store.LEADERBOARD, board)
        out = store.path(store.LEADERBOARD)
        print(f"\nSaved leaderboard: {out}")
        print("Write the winners into config_cluster.json with: python3 -m nimlab judge apply")
        return 0

    if args.action == "entity":
        combos = None
        if args.combos:
            combos = config.load_json(args.combos, None)
            if not isinstance(combos, list):
                print("--combos must be a JSON file holding a list of {name, roles}.")
                return 2
        report = judge.judge_entity(combos=combos, judges=_split(args.judges), repeats=args.repeats, seed=args.seed)
        store.save(store.ENTITY_SCORES, report)
        out = store.path(store.ENTITY_SCORES)
        print("\n" + judge.format_entity(report))
        print(f"\nSaved: {out}")
        return 0
    return 2


# ---------------------------------------------------------------------------
# discover / sweep
# ---------------------------------------------------------------------------
def _discovery_settings():
    return config.load_cluster_config().get("discovery_settings", {}) or {}


def _fetcher(args, settings):
    from .scrape import PoliteFetcher
    delays = settings.get("host_delays_sec") or {}
    if getattr(args, "fast", False):
        delays = {h: min(float(v), 2.0) for h, v in delays.items()} or {"build.nvidia.com": 2.0}
    return PoliteFetcher(ttl_sec=float(settings.get("page_ttl_hours", 72)) * 3600, host_delays=delays,
                         offline=getattr(args, "offline", False))


def cmd_discover(args):
    from . import catalog
    settings = _discovery_settings()
    if args.show:
        doc = catalog.load_catalog()
        if not doc:
            print("No discovered models yet. Run: python3 -m nimlab discover")
            return 1
        _print_catalog(doc, args.flag, args.limit)
        return 0
    api = None
    if not args.no_key and load_api_key():
        from .api import NimClient
        api = NimClient()
    doc = catalog.discover(_fetcher(args, settings), api=api, use_cache=not args.refresh)
    if not doc["models"]:
        print("Discovery found nothing (all sources failed). Errors:", doc["errors"])
        return 1
    stats = catalog.save_catalog(doc, offline=args.offline)
    _print_catalog(store.discovered() or doc, args.flag, args.limit)
    cov = ", ".join(doc.get("covered_sources") or []) if not args.offline else ""
    print(f"\nSynced into {store.path(store.DISCOVERED)}: {len(stats['added'])} new, "
          f"{len(stats['returned'])} back, {len(stats['removed'])} removed (kept in 'removed').")
    if cov:
        print(f"  Sources read completely this run (only these can remove models): {cov}")
    else:
        print("  No source was read completely (offline or all failed), so nothing was removed.")
    if stats["removed"]:
        print("  Removed: " + ", ".join(stats["removed"][:20]) + (" ..." if len(stats["removed"]) > 20 else ""))
    return 0


def _print_catalog(doc, flag=None, limit=None):
    from . import catalog
    s = doc["summary"]
    c = doc.get("source_counts", {})
    print(f"Discovered models {doc.get('generated_at', '?')}: {s['total']} models")
    print(f"  site (build.nvidia.com): {c.get('site', s['on_site'])}   docs: {c.get('docs', s['in_docs'])}   "
          f"key list: {c.get('key', s['in_key_list'])} ({doc.get('sources', {}).get('key') or 'none'})")
    print(f"  on site but not in key list: {s['on_site_not_in_key']}   in key list but not on site: "
          f"{s['in_key_not_on_site']}")
    print(f"  deprecated (still served, end date announced): {s['deprecated']}   retired: {s['retired']}   "
          f"not on the site (docs or key only): {s['unlisted']}")
    print("  kinds: " + ", ".join(f"{k} {v}" for k, v in s["kinds"].items()))
    if doc.get("errors"):
        print("  source errors: " + "; ".join(f"{k}: {v}" for k, v in doc["errors"].items()))
    if flag:
        print(f"\n{flag}:")
        print(catalog.format_table(doc, flag, limit) or "  (none)")


def cmd_sweep(args):
    from . import catalog, sweep
    settings = _discovery_settings()
    doc = catalog.load_catalog()
    kinds = [k.strip() for k in args.kinds.split(",")] if args.kinds else None
    if args.models:
        ids = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        ids = sweep_ids(doc, include_retired=args.include_retired or settings.get("include_retired_in_sweep"),
                        site_only=args.site_only, kinds=kinds)
        if not doc:
            print("No discovered models yet (run discover); sweeping the key list, registry and verified models.")
    if args.limit:
        ids = ids[: args.limit]
    # only a run over the whole default list may drop what it no longer finds
    complete = not (args.models or kinds or args.limit or args.site_only or args.offline)
    if not ids:
        print("No models to sweep.")
        return 1
    probe = not args.plan_only
    key = load_api_key()
    if probe and not key:
        print("No API key: running plan-only (specs are read, nothing is probed).")
        probe = False
    resolver = sweep.SpecResolver(_fetcher(args, settings), doc,
                                  ttl_sec=float(settings.get("spec_ttl_hours", 72)) * 3600)
    prober = sweep.Prober(timeout=float(settings.get("probe_timeout_sec", 20))) if probe else None
    print(f"Spec sweep: {len(ids)} models ({'probe' if probe else 'plan only'}). "
          f"Pages are paced (build.nvidia.com asks for 10 s between requests); cached specs are reused.")
    results = sweep.run(ids, resolver, prober, probe, workers=int(settings.get("probe_workers", 3)),
                        use_cache=not args.refresh)
    print("\nResult classes:")
    for k, v in sweep.summarize(results).items():
        print(f"  {k:<26} {v}")
    if args.no_write:
        print("\n--no-write: the data stores were not changed.")
        return 0
    st = sweep.write_results(results, complete=complete and probe, probed=probe)
    print_sync(st, probe, complete)
    return 0


def sweep_ids(doc=None, include_retired=False, site_only=False, kinds=None):
    """Default sweep list: every discovered model (retired ones only on
    request) + every model the endpoint registry names + every verified
    model, de-duplicated by match key."""
    from . import catalog, spec
    ids = catalog.model_ids(doc, include_retired=include_retired, include_unlisted=not site_only,
                            kinds=kinds) if doc else list(store.key_list())
    extra = store.endpoint_models() + store.verified_ids()
    if kinds:
        extra = [m for m in extra if (catalog.kind_of(m, doc) if doc else None) in kinds
                 or (store.verified_models().get(m) or {}).get("catalog_kind") in kinds]
    if site_only and doc:
        extra = [m for m in extra if m in doc["models"] and doc["models"][m].get("status") != "unlisted"]
    seen, out = set(), []
    for m in ids + extra:
        k = spec.match_key(m)
        if k not in seen:
            seen.add(k)
            out.append(m)
    return out


def print_sync(st, probe=True, complete=False):
    print(f"\nData stores updated ({store.data_dir()}):")
    print(f"  verified 200 OK: +{len(st['verified_added'])} added, -{len(st['verified_dropped'])} dropped "
          f"(now {len(store.verified_ids())})")
    print(f"  endpoints: +{st['endpoints_added']} new, {st['endpoints_revived']} back, "
          f"{st['endpoints_staled']} marked stale; {st['overrides']} router override(s) updated")
    if st.get("outage"):
        print("  Every probe failed with auth or timeout errors: that looks like the key or the network,\n"
              "  so no verified model was dropped. Check the key and connection, then sweep again.")
    if not probe:
        print("  Plan-only run: spec endpoints were recorded; the verified list was not changed.")
    elif not complete:
        print("  Partial run: only the models it tested were added or dropped.")


# ---------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m nimlab", description="NVIDIA NIM test lab tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="print one status value (for the launcher header)")
    s.add_argument("field", choices=["key", "live", "inventory", "memory", "catalog", "discovered", "endpoints",
                                     "roles"])
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("roles", help="show the 16 roles, list candidates for one, or migrate old role keys")
    s.add_argument("action", nargs="?", default="show", choices=["show", "candidates", "migrate"])
    s.add_argument("role", nargs="?", help="candidates: role key, e.g. chart_parser")
    s.add_argument("--scope", choices=["verified", "all"], default="all")
    s.set_defaults(fn=cmd_roles)

    for name, fn, hlp in (("persist-key", cmd_persist_key, "save the env key to ~/.nimlab_env (mode 600)"),
                          ("forget-key", cmd_forget_key, "remove the persisted key")):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("--env-file")
        s.add_argument("--bashrc")
        s.set_defaults(fn=fn)

    sub.add_parser("fleet", help="verified LIVE_200 fleet table").set_defaults(fn=cmd_fleet)

    s = sub.add_parser("data", help="data stores: overview, list views, migration")
    s.add_argument("action", nargs="?", default="overview", choices=["overview", "show", "migrate", "paths"])
    s.add_argument("view", nargs="?", help="show: " + ", ".join(store.VIEWS))
    s.add_argument("--limit", type=int)
    s.set_defaults(fn=cmd_data)
    sub.add_parser("report", help="latest benchmark report").set_defaults(fn=cmd_report)

    s = sub.add_parser("discover", help="build the merged model catalog (site + docs + key)")
    s.add_argument("--refresh", action="store_true", help="ignore cached pages")
    s.add_argument("--offline", action="store_true", help="use cached pages only")
    s.add_argument("--no-key", action="store_true", help="do not call /v1/models; use the saved key list")
    s.add_argument("--show", action="store_true", help="print the cached catalog without fetching")
    s.add_argument("--flag", help="list models with this flag/status, e.g. on_site_not_in_key, retired")
    s.add_argument("--limit", type=int)
    s.add_argument("--fast", action="store_true", help="shorter delays between page requests")
    s.set_defaults(fn=cmd_discover)

    s = sub.add_parser("sweep", help="spec-driven endpoint sweep from each model's page")
    s.add_argument("--models", help="comma list of model ids (default: the catalog)")
    s.add_argument("--kinds", help="comma list of catalog kinds, e.g. chat,vision,embedding")
    s.add_argument("--limit", type=int)
    s.add_argument("--plan-only", action="store_true", help="read specs only; no API calls")
    s.add_argument("--include-retired", action="store_true")
    s.add_argument("--site-only", action="store_true", help="skip models the site does not list")
    s.add_argument("--refresh", action="store_true", help="refetch pages even if specs are cached")
    s.add_argument("--offline", action="store_true")
    s.add_argument("--fast", action="store_true")
    s.add_argument("--no-write", action="store_true", help="do not update the data stores")
    s.set_defaults(fn=cmd_sweep)

    s = sub.add_parser("tts", help="Magpie TTS; text from --text or stdin")
    s.add_argument("--voice", default=None)
    s.add_argument("--text", default=None)
    s.add_argument("--no-play", action="store_true")
    s.set_defaults(fn=cmd_tts)

    s = sub.add_parser("judge", help="model ranking and entity scoring")
    s.add_argument("action", choices=["rank", "entity", "show", "apply"])
    s.add_argument("--types", help="comma list: " + ",".join(["chat", "deep_reasoning", "coding", "vision", "ocr",
                                                              "embeddings", "compactor", "tts"]))
    s.add_argument("--judges", help="comma list of judge model ids (overrides config)")
    s.add_argument("--repeats", type=int)
    s.add_argument("--seed", type=int)
    s.add_argument("--max-candidates", type=int)
    s.add_argument("--no-exec", action="store_true", help="do not run generated code")
    s.add_argument("--combos", help="entity: JSON file with [{name, roles}]")
    s.add_argument("--yes", action="store_true", help="apply: skip the confirmation prompt")
    s.set_defaults(fn=cmd_judge)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args) or 0
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
