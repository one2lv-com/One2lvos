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
        # 3.7.1: the ACTIVE long-term backend's count (it counted the local
        # short-term file data/memory.json, so the header said 0 while
        # Oracle held 4)
        from . import memmenu
        print(memmenu.header_line(count_fn=memmenu.active_count))
    elif args.field in ("catalog", "discovered"):
        print(len(store.load(store.DISCOVERED)["models"]))
    elif args.field == "endpoints":
        print(len(store.load(store.ENDPOINTS)["endpoints"]))
    elif args.field == "roles":
        for line in role_summary(compact=True):
            print(line)
    elif args.field == "color":
        from . import colors
        sys.__stdout__.write(colors.shell_line() + "\n")
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
        from .rolemenu import grpc_flag
        g = grpc_flag(v.get("model")) if v["backend"] == R.MODEL and v.get("model") else ""
        if g:
            flags.append(g)
        elif v["backend"] == R.MODEL and v.get("model") and verified and v["model"] not in verified:
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
        verified = sorted(set(store.verified_ids()) | set(R.grpc_ids_readonly()), key=str.lower)
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
# grpc (v3.5): NVCF gRPC models and their function ids
# ---------------------------------------------------------------------------
def _grpc_model_arg(name):
    """A model id from a full id, a unique part of one, or a list number."""
    from . import nvcf_grpc
    ids = [r["model"] for r in nvcf_grpc.rows()]
    if not name:
        return None
    if name.isdigit() and 1 <= int(name) <= len(ids):
        return ids[int(name) - 1]
    if name in ids or "/" in name:
        return name
    hits = [m for m in ids if name.lower() in m.lower()]
    return hits[0] if len(hits) == 1 else name


def grpc_lines(rows=None):
    from . import colors as C, nvcf_grpc
    rows = nvcf_grpc.rows() if rows is None else rows
    out = []
    for i, r in enumerate(rows, 1):
        fid = r["function_id"] or "(no function ID)"
        bits = [r["kind"].upper()]
        if r.get("language_code"):
            bits.append(r["language_code"])
        if r.get("mode"):
            bits.append(r["mode"])
        if r.get("source"):
            bits.append(f"from {r['source']}")
        chk = r.get("last_check") or {}
        if chk:
            bits.append(("last call ok" if chk.get("ok") else "last call FAILED") + f" {str(chk.get('at', ''))[:16]}")
        if r.get("spec_function_id"):
            bits.append(f"spec now says {r['spec_function_id']}: grpc refresh")
        line = f"  {i:>2}. {r['model']:<44} {fid}  ({'; '.join(bits)})"
        if C.enabled():
            col = C.err if not r["function_id"] or (chk and not chk.get("ok")) else C.ok
            name = f"{r['model']:<44}"
            line = f"  {i:>2}. {C.model(name)} {col(fid)}  {C.dim('(' + '; '.join(bits) + ')')}"
        out.append(line)
    return out


def cmd_grpc(args):
    from . import nvcf_grpc, store
    a = args.action
    if a == "menu":
        from . import colors as C, grpcmenu
        try:
            grpcmenu.run_menu(C.read, print)
        except (KeyboardInterrupt, EOFError):
            print()
        return 0
    model = _grpc_model_arg(args.model)
    if a == "list":
        n = nvcf_grpc.seed_from_spec_cache()
        rows = nvcf_grpc.rows()
        ok, detail = nvcf_grpc.available()
        print(f"NVCF gRPC models ({len(rows)}), endpoint {nvcf_grpc.URI}; client: {detail if ok else 'NOT installed'}")
        if n:
            print(f"(added {n} function ID(s) from the sweep's spec cache)")
        for line in grpc_lines(rows):
            print(line)
        if not rows:
            print("  none yet: run the 200 sweep (launcher option 2) or ./start.sh sweep")
        missing = [r["model"] for r in rows if not r["function_id"]]
        if missing:
            print(f"\n{len(missing)} without a function ID: ./start.sh grpc refresh, or paste one: "
                  "./start.sh grpc set <model> <function-id>")
        return 0
    if a == "set":
        if not model or not args.value:
            print("usage: grpc set <model> <function-id>")
            return 2
        try:
            rec = store.set_grpc_function(model, args.value, source="user", kind=nvcf_grpc.kind_of(model))
        except ValueError as e:
            print(f"[x] {e}")
            return 2
        print(f"[ok] {model}: function ID {rec['function_id']} saved to data/endpoints.json")
        return 0
    if a == "clear":
        if not model:
            print("usage: grpc clear <model>")
            return 2
        print(f"[ok] {model}: function ID cleared" if store.clear_grpc_function(model) else f"{model}: nothing stored")
        return 0
    if a == "fill":
        n, with_id, missing = fill_grpc_ids(fetch=True)
        if not n:
            print("No gRPC models known yet. That is missing data, not a key or network problem: read the model "
                  "specs first (nimlab setup functions) or run the 200 OK sweep (nimlab setup sweep).")
            return 3
        return 0
    if a == "refresh":
        targets = [model] if model else [r["model"] for r in nvcf_grpc.rows()]
        if not targets:
            print("No gRPC models known yet. That is missing data, not a key or network problem: read the model "
                  "specs first (nimlab setup functions) or run the 200 OK sweep (nimlab setup sweep), or name one: "
                  "grpc refresh <model>")
            return 3
        bad = 0
        for m in targets:
            if not model and (nvcf_grpc.record(m).get("source") in store.GRPC_USER_SOURCES) and not args.force:
                print(f"  {m}: kept your pasted ID (use --force to replace it)")
                continue
            ok, msg = nvcf_grpc.refresh(m)
            bad += 0 if ok else 1
            print(("  [ok] " if ok else "  [x] ") + msg)
        return 1 if bad and model else 0
    if a == "lang":
        if not model:
            print("usage: grpc lang <model> <language-code|->  (e.g. es-US, de-DE, multi)")
            return 2
        v = None if args.value in (None, "-", "") else args.value
        store.update_grpc_settings(model, language_code=v)
        print(f"[ok] {model}: language_code {v or '(model default)'}")
        return 0
    if a == "mode":
        if not model or args.value not in ("offline", "streaming", "-"):
            print("usage: grpc mode <model> offline|streaming|-")
            return 2
        store.update_grpc_settings(model, mode=None if args.value == "-" else args.value)
        print(f"[ok] {model}: ASR mode {args.value}")
        return 0
    if a == "check":
        ok, detail = nvcf_grpc.available()
        if not ok:
            print(f"[x] {detail}")
            return 1
        if not load_api_key():
            print("NVIDIA_API_KEY is not set.")
            return 1
        targets = [model] if model else [r["model"] for r in nvcf_grpc.rows()
                                         if r["function_id"] and r["kind"] in nvcf_grpc.RIVA_KINDS]
        cli = nvcf_grpc.client()
        bad = 0
        for m in targets:
            fid = nvcf_grpc.function_id(m)
            if not fid:
                print(f"  [x] {m}: no function ID")
                bad += 1
                continue
            good, lat, det = cli.check(fid, nvcf_grpc.kind_of(m, nvcf_grpc.record(m)))
            store.note_grpc_check(m, good, det, latency=lat)
            hint = "" if good else nvcf_grpc.stale_hint(m, det.split(":")[0], det)
            print(f"  {'[ok]' if good else '[x] '} {m}: {det} ({lat}s)" + (f"\n       {hint}" if hint else ""))
            bad += 0 if good else 1
        return 1 if bad else 0
    if a in ("asr", "tts"):
        return _grpc_try(a, model, args)
    print("actions: list, set, clear, refresh, lang, mode, check, asr, tts")
    return 2


def _grpc_try(kind, model, args):
    """grpc asr <model> <audio> / grpc tts <model> "text" [--clip ref.wav]."""
    from . import nvcf_grpc
    from .api import play_audio, save_wav
    if not model or not args.value:
        print("usage: grpc asr <model> <audio-file> [--lang xx-XX]  |  grpc tts <model> \"text\" [--voice V] "
              "[--clip ref.wav] [--transcript T]")
        return 2
    sp = {"model": model}
    if args.lang:
        sp["language_code"] = args.lang
    if kind == "asr":
        r = nvcf_grpc.run_asr(sp, path=args.value)
        if not r.ok:
            print(f"[x] {r.error}")
            return 1
        raw = r.raw or {}
        print(f"[ok] {r.latency}s, {raw.get('mode')}, {raw.get('language_code')}"
              + (f"; {', '.join(raw['notes'])}" if raw.get("notes") else ""))
        print(r.text or "(empty transcript)")
        return 0
    prompt = None
    if args.clip:
        from . import voiceclone
        try:
            _, prompt, _info = voiceclone.prepare(args.clip)
        except voiceclone.CloneError as e:
            print(f"[x] reference clip: {e}")
            return 1
    r = nvcf_grpc.run_tts(sp, args.value, voice=args.voice, language=args.lang, prompt_wav=prompt,
                          prompt_transcript=args.transcript)
    if not r.ok:
        print(f"[x] {r.error}")
        return 1
    path = save_wav(r.data, "grpc_tts")
    print(f"[ok] {path} in {r.latency}s" + (" (cloned voice)" if prompt else ""))
    if not args.no_play:
        play_audio(path)
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
    limit = getattr(args, "time_limit", None)
    results = sweep.run(ids, resolver, prober, probe, workers=int(settings.get("probe_workers", 3)),
                        use_cache=not args.refresh, time_limit=limit)
    if len(results) < len(ids):
        complete = False    # a run cut short by its time limit never drops what it did not reach
    print("\nResult classes:")
    for k, v in sweep.summarize(results).items():
        print(f"  {k:<26} {v}")
    if args.no_write:
        print("\n--no-write: the data stores were not changed.")
        return 0
    st = sweep.write_results(results, complete=complete and probe, probed=probe)
    print_sync(st, probe, complete)
    fill_grpc_ids(fetch=not args.offline)
    return 0


def fill_grpc_ids(fetch=True, log=print):
    """3.7.2: give every gRPC-only model a function ID: first from the spec
    pages already cached, then (fetch=True) from each missing model's NGC
    spec or page. IDs the user pasted are never replaced. -> (known, with_id,
    missing list)."""
    from . import nvcf_grpc
    try:
        added = nvcf_grpc.seed_from_spec_cache()
    except Exception:  # noqa: BLE001 - a broken cache never stops the sweep
        added = 0
    missing = [r["model"] for r in nvcf_grpc.rows() if not r.get("function_id")]
    found = 0
    if fetch:
        for m in list(missing):
            try:
                ok, _msg = nvcf_grpc.refresh(m, log=lambda *_: None)
            except Exception:  # noqa: BLE001
                ok = False
            if ok:
                found += 1
                missing.remove(m)
    rows = nvcf_grpc.rows()
    with_id = sum(1 for r in rows if r.get("function_id"))
    if rows:
        log(f"gRPC function IDs: {with_id} of {len(rows)} gRPC-only models have one"
            + (f" ({added + found} filled in now)" if added + found else "") + ".")
        if missing:
            log("  Still without one (paste it from the model's \"Try API\" sample: nimlab grpc set <model> <id>): "
                + ", ".join(missing[:8]) + (f" (+{len(missing) - 8} more)" if len(missing) > 8 else ""))
    return len(rows), with_id, missing


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
    try:
        from . import nvcf_grpc
        rows = [r for r in nvcf_grpc.rows()]
        riva = [r for r in rows if r["kind"] in nvcf_grpc.RIVA_KINDS]
        if rows:
            with_id = sum(1 for r in riva if r["function_id"])
            print(f"  NVCF gRPC: {len(riva)} Riva model(s) usable over gRPC ({with_id} with a function ID), "
                  f"{len(rows) - len(riva)} other gRPC-only; see ./start.sh grpc list")
    except Exception:  # the summary never fails the sweep
        pass
    if not probe:
        print("  Plan-only run: spec endpoints were recorded; the verified list was not changed.")
    elif not complete:
        print("  Partial run: only the models it tested were added or dropped.")


def cmd_serve(args):
    from .servemenu import cmd_serve as run
    return run(args)


# ---------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m nimlab", description="NVIDIA NIM test lab tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="print one status value (for the launcher header)")
    s.add_argument("field", choices=["key", "live", "inventory", "memory", "catalog", "discovered", "endpoints",
                                     "roles", "color"])
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

    s = sub.add_parser("serve", help="OpenAI-compatible test server for the testbed's roles and agent")
    s.add_argument("action", nargs="?", default="start",
                   choices=["start", "info", "test", "log", "models", "ui", "regen-key", "settings", "menu", "tunnel"])
    s.add_argument("values", nargs="*", help="settings: <name> <value>, e.g. 'port 9000' or 'lan on' | "
                   "tunnel status|quick|named [<id-or-name>]|off|auto on|off|install|token-delete")
    s.add_argument("--full", action="store_true", help="test: also the heavy live media checks (default for "
                   "`serve test`; `serve test quick` skips them)")
    s.add_argument("--token", action="store_true", help="tunnel named: read a tunnel token (hidden)")
    s.add_argument("--credentials", help="tunnel named: the tunnel's credentials JSON file")
    s.add_argument("--hostname", help="tunnel named: the public hostname routed to the server")
    s.add_argument("--auto", dest="auto", action="store_true", default=None,
                   help="tunnel quick|named: also start the tunnel with every 'serve start'")
    s.add_argument("--no-auto", dest="auto", action="store_false", help="tunnel: do not auto-start it")
    s.add_argument("--port", type=int)
    s.add_argument("--lan", dest="lan", action="store_true", default=None, help="bind 0.0.0.0 (same Wi-Fi)")
    s.add_argument("--local", dest="lan", action="store_false", help="bind 127.0.0.1 only")
    s.add_argument("--tunnel", action="store_true", help="also start a cloudflared public tunnel")
    s.add_argument("--no-log", action="store_true", help="do not write the request log this run")
    s.add_argument("--save", action="store_true", help="keep --port/--lan/--local for next time")
    s.add_argument("--limit", type=int, help="log: lines to show (default 50)")
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("mcp", help="MCP server: URL, API key (hidden, saved outside the project), auth, test")
    s.add_argument("action", nargs="?", default="show",
                   choices=["show", "menu", "set-url", "set-key", "delete-key", "auth", "test", "tools", "key-source"])
    s.add_argument("values", nargs="*", help="set-url <url> | auth <x-api-key|bearer|header|none> [header-name]")
    s.add_argument("--session", action="store_true", help="set-key: use for this command only, do not save")
    s.add_argument("--save", action="store_true", help="set-key: save without asking")
    s.add_argument("--no-test", action="store_true", help="set-url/set-key: skip the connection test")
    s.add_argument("-v", "--verbose", action="store_true", help="test: one line per tool (same as 'mcp tools')")
    s.set_defaults(fn=cmd_mcp)

    from . import routerbench
    routerbench.add_parser(sub)
    s = sub.add_parser("doctor", help="check memory (write + recall through the DB connection), prompts and MCP tools")
    s.add_argument("--no-mcp", action="store_true", help="skip the MCP server check")
    s.add_argument("--json", action="store_true", help="print the results as JSON (for the Telegram /health command and scripts)")
    s.add_argument("--fix", action="store_true", help="run the safe repairs (backs up the settings first, then checks again)")
    s.add_argument("--quick", action="store_true", help="skip the memory round trip, MCP and platform checks")
    s.set_defaults(fn=lambda a: __import__("nimlab.doctor", fromlist=["cmd_doctor"]).cmd_doctor(a))

    s = sub.add_parser("memory", help="long-term memory: backend (json/local/oracle/ords), embedding connection, test")
    s.add_argument("action", nargs="?", default="show",
                   choices=["show", "set", "use", "embed", "test", "setup", "list", "recall", "identity", "forget",
                            "prune", "add",
                            "sql", "creds", "load-onnx", "menu", "status", "embed-pending", "flush-queue",
                            "reembed", "pending", "ords"])
    s.add_argument("values", nargs="*", help="add <text> [--user ID] | set <name> <value> | use auto|off|json|local [dir]|oracle [schema]|"
                   "ords [url] | ords [show|login]: the HTTPS (ORDS) login, saved outside the project | "
                   "embed role|nvidia|openai <url> <model> [dims]|ollama <model> [url]|st [model]|oracle <model>"
                   "|models | embed-pending (alias flush-queue): store queued turns | pending: list them | "
                   "reembed [--recreate] [--yes]: embed stored memories again with the current model")
    s.add_argument("--recreate", action="store_true", help="reembed: back up, drop and recreate the table at the "
                   "embedder's size")
    s.add_argument("--yes", "-y", action="store_true", help="reembed --recreate: don't ask")
    s.set_defaults(fn=lambda a: __import__("nimlab.memmenu", fromlist=["cmd_memory"]).cmd_memory(a))

    s = sub.add_parser("setup", help="guided setup: every step in order, or one: setup <step> (setup list)")
    s.add_argument("step", nargs="?", default="", help="key|discover|functions|sweep|mcp|roles|grpc|memory|server|"
                   "telegram|selfadmin|deps|shortcut|tunnel|service|list")
    s.set_defaults(fn=lambda a: __import__("nimlab.wizard", fromlist=["cmd_setup"]).cmd_setup(a))

    s = sub.add_parser("service", help="keep the server (+tunnel, +Telegram) running, restart on crash")
    s.add_argument("action", nargs="?", default="status",
                   choices=["install", "remove", "start", "stop", "restart", "status", "logs", "run", "brief",
                            "boot", "telegram", "scheduler", "cleanup"])
    s.add_argument("value", nargs="?", help="telegram|scheduler on|off")
    s.add_argument("--backend", choices=["auto", "termux", "systemd", "builtin"])
    s.add_argument("--boot", action="store_true", help="install: also start on boot (Termux:Boot)")
    s.add_argument("--system", action="store_true",
                   help="install: a system-wide systemd unit run as the sudo user (sudo nimlab service install --system)")
    s.add_argument("--lines", type=int, help="logs: lines to show (default 40)")
    s.set_defaults(fn=lambda a: __import__("nimlab.service", fromlist=["cmd_service"]).cmd_service(a))

    s = sub.add_parser("telegram", help="Telegram bot connector (token from @BotFather)")
    s.add_argument("action", nargs="?", default="status",
                   choices=["set-token", "test", "allow", "status", "start", "stop", "run", "mode", "voice",
                            "refusal"])
    s.add_argument("values", nargs="*", help="allow <id>... | mode polling|webhook | voice on|off | "
                   "refusal polite|ignore")
    s.add_argument("--capture", action="store_true", help="allow: wait for /start and make that person the owner")
    s.add_argument("--remove", action="store_true", help="allow: remove the IDs instead")
    s.set_defaults(fn=lambda a: __import__("nimlab.telegram", fromlist=["cmd_telegram"]).cmd_telegram(a))

    s = sub.add_parser("bugs", help="bug log: grouped errors with short bug IDs (list, show, tail, status)")
    s.add_argument("action", nargs="?", default="list", choices=["list", "show", "tail", "status", "prune", "clear"])
    s.add_argument("bug", nargs="?", default="", help="show: the bug ID (B-3F9A1C or 3F9A1C)")
    s.add_argument("-n", type=int, default=None, help="tail: lines (default 10); show: occurrences (default 1)")
    s.add_argument("--limit", type=int, default=50, help="list: rows (default 50)")
    s.add_argument("--yes", action="store_true", help="clear: don't ask")
    s.set_defaults(fn=lambda a: __import__("nimlab.bugs", fromlist=["cmd_bugs"]).cmd_bugs(a))

    s = sub.add_parser("selfadmin", help="let the testbed inspect/change its own setup (admins only)")
    s.add_argument("action", nargs="?", default="status",
                   choices=["status", "on", "off", "shell", "others-read", "fixes", "admin-key", "undo",
                            "audit"])
    s.add_argument("values", nargs="*", help="shell on|off | others-read on|off | fixes on|off | audit [n]")
    s.set_defaults(fn=lambda a: __import__("nimlab.selfadmin", fromlist=["cmd_selfadmin"]).cmd_selfadmin(a))

    sub.add_parser("colors", aliases=["colours"], help="preview the terminal colours").set_defaults(fn=cmd_colors)

    s = sub.add_parser("shortcut", help="install a 'nimlab' command that runs start.sh from any folder")
    s.add_argument("action", nargs="?", default="install", choices=["install", "remove", "status"])
    s.add_argument("name", nargs="?", help="command name (default nimlab)")
    s.add_argument("--force", action="store_true", help="install: replace a same-named file this lab did not make")
    s.add_argument("--dir", help="folder for the command (default $PREFIX/bin on Termux, else ~/.local/bin)")
    s.set_defaults(fn=lambda a: __import__("nimlab.shortcut", fromlist=["cmd_shortcut"]).cmd_shortcut(a))

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
    s.add_argument("--time-limit", type=float, help="stop after this many seconds (models not reached are "
                   "left for the next run, never dropped)")
    s.set_defaults(fn=cmd_sweep)

    s = sub.add_parser("tts", help="Magpie TTS; text from --text or stdin")
    s.add_argument("--voice", default=None)
    s.add_argument("--text", default=None)
    s.add_argument("--no-play", action="store_true")
    s.set_defaults(fn=cmd_tts)

    s = sub.add_parser("grpc", help="NVCF gRPC models (Riva ASR/TTS/NMT): function IDs, language, check, try")
    s.add_argument("action", nargs="?", default="list",
                   choices=["list", "set", "clear", "refresh", "fill", "lang", "mode", "check", "asr", "tts", "menu"])
    s.add_argument("model", nargs="?", help="model id, part of one, or its number in grpc list")
    s.add_argument("value", nargs="?", help="set: function ID; lang: code; mode: offline|streaming; "
                                           "asr: audio file; tts: text")
    s.add_argument("--force", action="store_true", help="refresh: also replace IDs you pasted")
    s.add_argument("--lang", help="asr/tts: language code, e.g. es-US")
    s.add_argument("--voice", help="tts: voice name")
    s.add_argument("--clip", help="tts: zero-shot reference clip (voice cloning)")
    s.add_argument("--transcript", help="tts: what the clip says (flow models)")
    s.add_argument("--no-play", action="store_true")
    s.set_defaults(fn=cmd_grpc)

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
    # 3.7.4: the cheat sheet, the symptom guide, the Tests menu and the platform check
    from . import commands, hostenv, systests
    commands.add_parsers(sub)
    systests.add_parser(sub)
    hostenv.add_parser(sub)
    # 3.8.0: scheduler jobs and the heartbeat
    from . import jobscli
    jobscli.add_parsers(sub)
    # 3.8.2: ./update.sh after unzipping a release
    from . import updater
    updater.add_parser(sub)
    from . import uimenu, endpoints
    uimenu.add_parser(sub)
    endpoints.add_parser(sub)
    from . import audiobus
    audiobus.add_parser(sub)
    return p


def _mcp_settings_io():
    from . import config
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    merged = config.load_cluster_config().get("mcp_settings", {})
    settings = dict(merged, **(cfg.get("mcp_settings") or {}))
    settings.setdefault("auth", dict(merged.get("auth") or {}))

    def save():
        doc = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        clean = dict(settings)
        clean.pop("api_key", None)
        doc["mcp_settings"] = clean
        config.save_json(config.CLUSTER_CONFIG, doc)
    return settings, save


def cmd_mcp(args):
    """MCP server URL, API key (hidden, saved outside the project), auth
    style and a connection test."""
    from . import colors as C, mcpkey, mcpmenu
    settings, save = _mcp_settings_io()
    a = args.action
    vals = list(args.values or [])
    if a == "menu":
        mcpmenu.run_menu(settings, input, print, save_fn=save)
        return 0
    if a == "show":
        print(C.header("MCP SERVER"))
        for line in mcpmenu.status_lines(settings):
            print(line)
        return 0
    if a == "set-url":
        url = vals[0] if vals else input(C.ask("MCP server URL: "))
        e = mcpmenu.set_url(settings, url)
        if e:
            print(C.err(e))
            return 2
        save()
        print(C.ok("URL set to ") + C.url(settings["url"]))
        return 0 if args.no_test else (0 if mcpmenu.show_test(settings, print)["ok"] else 1)
    if a == "set-key":
        if vals:
            print(C.err("Don't put the key on the command line (it lands in shell history). "
                        "Run 'mcp set-key' and type it at the hidden prompt."))
            return 2
        how = mcpmenu.enter_key(settings, input, print, save=False if args.session else (True if args.save else None))
        if not how:
            return 1
        if how == "session":
            print(C.warn("A session-only key ends with this command; use the testbed or the launcher menu "
                         "to keep one for a whole session."))
        return 0 if args.no_test or not settings.get("url") else \
            (0 if mcpmenu.show_test(settings, print)["ok"] else 1)
    if a == "delete-key":
        return 0 if mcpmenu.delete_saved(settings, print) else 1
    if a == "auth":
        if not vals:
            if not mcpmenu.choose_style(settings, input, print):
                return 1
        else:
            e = mcpmenu.set_style(settings, vals[0], vals[1] if len(vals) > 1 else None)
            if e:
                print(C.err(e))
                return 2
            print(C.ok("Auth style set to ") + C.value(mcpmenu.style_text(settings["auth"])))
        save()
        return 0
    if a == "test":
        return 0 if mcpmenu.show_test(settings, print, full_list=bool(getattr(args, "verbose", False)))["ok"] else 1
    if a == "tools":
        return 0 if mcpmenu.show_test(settings, print, full_list=True)["ok"] else 1
    if a == "key-source":
        print(mcpkey.source_text(settings.get("auth"))[0])
        return 0
    return 2


def cmd_colors(args):
    """Show the palette, the role colours and the current colour setting."""
    from . import colors as C, roles as R
    pol, dep = C.policy(), C.depth()
    on = C.enabled()
    print(C.header("TERMINAL COLOURS"))
    print(f"  {C.label('setting:')} {C.value(pol)}  {C.label('depth:')} {C.value(str(dep))}"
          f"  {C.label('colour now:')} {C.onoff(on, 'on', 'off')}")
    print(C.hint("  Turn off: NIMLAB_COLOR=0, NO_COLOR=1, --no-color, or ui_settings.color=off. "
                 "Depth: NIMLAB_COLOR_DEPTH=24|256|16."))
    print(C.rule())
    print(C.section("Roles"))
    for i, d in enumerate(R.ROLE_DEFS, 1):
        print("  " + C.paint(f"{i:>2}.", C.role_rgb(d.key), "bold") + " " + C.role(d.key, d.name))
    print(C.section("Statuses"))
    print("  " + "  ".join([C.status("PASS"), C.status("FAIL"), C.status("SKIP"), C.http(200), C.http(301),
                            C.http(404), C.http(503), C.latency("0.4s"), C.latency("2.5s"), C.latency("7s"),
                            C.latency("15s")]))
    print(C.section("Values"))
    print(f"  {C.model('meta/llama-3.3-70b-instruct')}  {C.url('http://127.0.0.1:8765/v1')}  "
          f"{C.key('sk-...a1b2')}  {C.path('output/tts_1.wav')}  {C.value('0.35')}  {C.hint('a hint')}")
    print(C.section("Chat"))
    print(f"  {C.you('YOU >')} {C.you_text('what is in this picture?')}")
    print(f"  {C.entity('QUILL')} {C.dim('[')}{C.role('vision', 'Vision')}{C.dim(']')} {C.dim('(')}"
          f"{C.latency('1.2s')}{C.dim(')')}: {C.reply('A cat on a windowsill.')}")
    for i in range(1, 9):
        print("  " + C.item(i, f"menu entry {i}", extra="  (hint)"))
    return 0


def main(argv=None):
    from . import colors
    argv = colors.apply_flags(list(sys.argv[1:] if argv is None else argv))
    colors.install()
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args) or 0
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
