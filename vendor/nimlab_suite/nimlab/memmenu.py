"""Long-term memory settings: one set of functions behind the testbed menu
(settings -> 17), `./start.sh memory ...` and `./start.sh serve settings
memory.<key> <value>`. Everything lives in memory_settings in
config_cluster.json; no password or API key is ever written there."""

import copy
import getpass as _getpass
import json
import os
import time
import re

from . import colors as C
from . import config, ltm
from .ltm_oracle import ENV as ORACLE_ENV, FORBIDDEN_SCHEMAS, IDENT

TOP = {"k": "recall_top_k", "top_k": "recall_top_k", "recall_top_k": "recall_top_k",
       "threshold": "similarity_threshold", "similarity_threshold": "similarity_threshold",
       "rerank_candidates": "rerank_candidates", "recall_max_chars": "recall_max_chars",
       "hybrid_recall": "hybrid_recall", "exclude_context_turns": "exclude_context_turns",
       "hybrid_keyword_weight": "hybrid_keyword_weight"}
TOP_BOOLS = {"hybrid_recall", "exclude_context_turns"}
BOOLS = {"auto_store", "auto_recall", "embedding.send_dimensions", "oracle.register_profile", "pin_identity"}
INTS = {"min_chars": (0, 2000), "max_records": (0, 10_000_000), "max_chars": (0, 100_000),
        "retry_after_sec": (5, 86400), "embedding.dimensions": (0, 65535), "embedding.timeout_sec": (1, 600),
        "oracle.target_accuracy": (50, 100), "oracle.dims": (0, 65535), "oracle.connect_timeout_sec": (1, 300),
        "ords.timeout_sec": (1, 300),
        "recall_top_k": (1, 20), "rerank_candidates": (1, 50), "recall_max_chars": (0, 50_000),
        "identity_cache_sec": (0, 3600), "identity_backfill_scan": (0, 100_000)}
FLOATS = {"dedupe_threshold": (0.5, 1.0), "retention_days": (0, 36500), "similarity_threshold": (0.0, 1.0),
          "hybrid_keyword_weight": (0.0, 5.0)}
CHOICES = {"backend": ltm.BACKENDS, "scope": ltm.SCOPES, "store_mode": ltm.STORE_MODES, "dedupe": ltm.DEDUPE_MODES,
           "embedding.provider": ltm.PROVIDERS, "oracle.index": ("ivf", "hnsw", "none"),
           "oracle.distance": ("COSINE", "DOT", "EUCLIDEAN"), "ords.auth": ("basic", "oauth")}
TEXT = {"local.directory", "embedding.url", "embedding.model", "embedding.api_key_env", "embedding.query_prefix",
        "embedding.passage_prefix", "embedding.device", "oracle.schema", "oracle.table_prefix", "oracle.profile_id",
        "oracle.credentials_file", "oracle.user", "oracle.dsn", "oracle.config_dir", "oracle.wallet_dir",
        "oracle.onnx_model", "ords.base_url", "ords.user", "ords.client_id", "ords.credentials_file"}
HELP = ("backend (auto/off/json/local/oracle/ords), scope (shared/user), auto_store, auto_recall, store_mode, min_chars, dedupe, dedupe_threshold, k, threshold, "
        "rerank_candidates, hybrid_recall, hybrid_keyword_weight, exclude_context_turns, recall_max_chars, "
        "pin_identity, identity_cache_sec, identity_backfill_scan, retention_days, max_records, max_chars, retry_after_sec, local.directory, "
        "embedding.{provider,url,model,dimensions,send_dimensions,api_key_env,timeout_sec,query_prefix,"
        "passage_prefix,device}, oracle.{schema,table_prefix,profile_id,register_profile,credentials_file,user,dsn,"
        "config_dir,wallet_dir,index,distance,target_accuracy,onnx_model,dims}, "
        "ords.{base_url,auth,user,client_id,credentials_file,timeout_sec}")
CRED_TEMPLATE = {"user": "MEM", "password": "", "dsn": "", "wallet_dir": "", "wallet_password": ""}


# ---------------------------------------------------------------------------
def load_ms(cluster=None):
    if cluster is None:
        cluster = config.load_cluster_config()
    ms = cluster.setdefault("memory_settings", {})
    ms["long_term"] = ltm.settings_from(ms)
    return ms


def save_ms(ms):
    """Write memory_settings into config_cluster.json (secrets stripped)."""
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    out = copy.deepcopy(ms)
    out["long_term"] = ltm.strip_secrets(out.get("long_term") or {})
    cfg["memory_settings"] = out
    config.save_json(config.CLUSTER_CONFIG, cfg)


def _apply_diff(base, old, new):
    """base + (new - old), recursively over dicts."""
    out = copy.deepcopy(base)
    for k in set(old) | set(new):
        if k not in new:
            out.pop(k, None)
        elif isinstance(new.get(k), dict) and isinstance(old.get(k), dict) and isinstance(out.get(k), dict):
            out[k] = _apply_diff(out[k], old[k], new[k])
        elif old.get(k) != new.get(k):
            out[k] = copy.deepcopy(new[k])
    return out


def _mtime():
    try:
        return os.path.getmtime(config.CLUSTER_CONFIG)
    except OSError:
        return None


def _bool(v):
    s = str(v).strip().lower()
    if s in ("1", "on", "true", "yes", "y"):
        return True
    if s in ("0", "off", "false", "no", "n"):
        return False
    raise ValueError("use on or off")


# Names that belong to other agents on the shared MEM schema (their *_mem tools
# on the svn-dev MCP server) or to Oracle itself: never this entity's profile.
PROTECTED_PROFILES = {"CHARLIE", "MAYA", "MILES", "SIMONE", "VEGA", "RILL", "ECHO", "VIREO", "NEVTAN", "ONE2LV",
                      "MEM", "AGENT", "SYS", "SYSTEM", "ADMIN", "PUBLIC", "DUAL", "ORDS", "CTXSYS"}


def protected_profiles(extra=None):
    """The built-in list, plus memory_settings.long_term.protected_profiles."""
    out = set(PROTECTED_PROFILES)
    try:
        from . import ltm
        lt = ltm.settings_from(load_ms())
        out |= {str(x).upper() for x in (lt.get("protected_profiles") or [])}
    except Exception:  # noqa: BLE001
        pass
    out |= {str(x).upper() for x in (extra or [])}
    return out


def profile_name_problem(name, extra=None):
    """None when NAME may be this entity's memory profile, else why not."""
    n = (name or "").strip().upper()
    if not n:
        return "the name is empty"
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,23}", n):
        return "use 1-24 letters, digits or _, starting with a letter"
    if n in protected_profiles(extra):
        return f"{n} is another agent's (or Oracle's) memory profile and is protected"
    return None


def lt_on(ms, key):
    return bool(ltm.settings_from(ms).get(key, True))


def apply_setting(ms, name, *values):
    """Change one memory setting in place. Returns a short description;
    raises ValueError on a bad name or value."""
    name = (name or "").strip().lower()
    if name.startswith("memory."):
        name = name[len("memory."):]
    if not values:
        raise ValueError("missing value. Memory settings: " + HELP)
    v = " ".join(str(x) for x in values).strip()
    if name.split(".")[-1] in ltm.SECRET_KEYS or "password" in name:
        raise ValueError("passwords and keys are never stored in settings: set "
                         f"{ORACLE_ENV['password']} or put it in the credentials file (memory creds)")
    if name in TOP:
        key = TOP[name]
        if key in TOP_BOOLS:
            ms[key] = _bool(v)
        elif key in INTS:
            lo, hi = INTS[key]
            ms[key] = max(lo, min(hi, int(v)))
        else:
            lo, hi = FLOATS[key]
            ms[key] = max(lo, min(hi, float(v)))
        return f"{key} = {ms[key]}"
    lt = ms.setdefault("long_term", ltm.settings_from(ms))
    if name in BOOLS:
        val = _bool(v)
    elif name in INTS:
        lo, hi = INTS[name]
        val = max(lo, min(hi, int(v)))
    elif name in FLOATS:
        lo, hi = FLOATS[name]
        val = max(lo, min(hi, float(v)))
    elif name in CHOICES:
        opts = CHOICES[name]
        val = v.upper() if name == "oracle.distance" else v.lower()
        if name == "embedding.provider" and val in ("st", "sentence-transformers"):
            val = "sentence_transformers"
        if val not in opts:
            raise ValueError(f"{name} must be one of: {', '.join(opts)}")
    elif name in TEXT:
        val = "" if v in ("-", "''", '""') else v
        if name in ("oracle.schema", "oracle.table_prefix", "oracle.profile_id", "oracle.onnx_model") and val:
            if not IDENT.match(val):
                raise ValueError(f"{name} must be a plain Oracle name (letters, digits, _)")
            val = val.upper()
        if name in ("oracle.table_prefix", "oracle.profile_id") and val:
            why = profile_name_problem(val)
            if why:
                raise ValueError(f"{name}: {why}")
        if name == "oracle.schema" and val in FORBIDDEN_SCHEMAS:
            raise ValueError(f"the {val} schema is off limits for testbed memory (MEM is the default)")
        if name == "oracle.dsn" and "password" in val.lower():
            raise ValueError("put the password in the credentials file, not in the DSN")
        if name == "ords.base_url" and val:
            from .ltm_ords import check_url
            val = val.rstrip("/")
            if val.endswith("/_/sql"):
                val = val[:-len("/_/sql")]
            if "@" in val.split("//", 1)[-1].split("/", 1)[0]:
                raise ValueError("put the login in `memory ords login`, not in the URL")
            bad = check_url(val)
            if bad:
                raise ValueError(bad)
    else:
        raise ValueError(f"unknown memory setting {name!r}. Settings: " + HELP)
    node = lt
    parts = name.split(".")
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = val
    return f"{name} = {val!r}" if isinstance(val, str) else f"{name} = {val}"


def use_backend(ms, backend, arg=None):
    out = [apply_setting(ms, "backend", backend)]
    if backend == "local" and arg:
        out.append(apply_setting(ms, "local.directory", arg))
    if backend == "oracle" and arg:
        out.append(apply_setting(ms, "oracle.schema", arg))
    if backend == "ords" and arg:
        out.append(apply_setting(ms, "ords.base_url", arg))
    return out


def use_embedder(ms, provider, *args):
    p = {"st": "sentence_transformers", "sentence-transformers": "sentence_transformers",
         "local": "openai", "nim": "nvidia"}.get(provider.lower(), provider.lower())
    out = [apply_setting(ms, "embedding.provider", p)]
    a = list(args)
    if p == "openai":
        if len(a) < 2:
            raise ValueError("usage: memory embed openai <url> <model> [dimensions]")
        out.append(apply_setting(ms, "embedding.url", a[0]))
        out.append(apply_setting(ms, "embedding.model", a[1]))
        if len(a) > 2:
            out.append(apply_setting(ms, "embedding.dimensions", a[2]))
    elif p == "ollama":
        if not a:
            raise ValueError("usage: memory embed ollama <model> [url]")
        out.append(apply_setting(ms, "embedding.model", a[0]))
        out.append(apply_setting(ms, "embedding.url", a[1] if len(a) > 1 else ltm.DEFAULT_OLLAMA_URL))
    elif p in ("nvidia", "sentence_transformers"):
        out.append(apply_setting(ms, "embedding.model", a[0] if a else
                                 (ltm.DEFAULT_NV_EMBED if p == "nvidia" else ltm.DEFAULT_ST_MODEL)))
        out.append(apply_setting(ms, "embedding.url", "-"))
        if len(a) > 1:
            out.append(apply_setting(ms, "embedding.dimensions", a[1]))
    elif p == "oracle":
        if not a:
            raise ValueError("usage: memory embed oracle <ONNX model name in the database>")
        out.append(apply_setting(ms, "oracle.onnx_model", a[0]))
        if ms["long_term"].get("backend") not in ("oracle", "ords"):
            out.append(apply_setting(ms, "backend", "oracle"))
    return out


# ---------------------------------------------------------------------------
def effective(ms=None):
    """THE one reading of the memory settings (3.7.1). Setup's Now/After
    line, the memory menu, `memory status`, the launcher header and the
    chat pipeline (MemoryCore.settings) all come from ltm.settings_from on
    memory_settings in config_cluster.json, through this function, so they
    cannot disagree. ms None = read the file now (never a cached copy)."""
    if ms is None:
        ms = (config.load_cluster_config() or {}).get("memory_settings") or {}
    lt = ltm.settings_from(ms)
    b = ltm.resolve_backend(lt)
    o = lt.get("oracle") or {}
    return {"backend": b, "configured": lt.get("backend") or "auto",
            "auto_store": lt["auto_store"], "auto_recall": lt["auto_recall"],
            "store_mode": lt.get("store_mode"), "min_chars": lt.get("min_chars"),
            "k": ms.get("recall_top_k", 6), "threshold": ms.get("similarity_threshold", 0.45),
            "rerank_pool": ms.get("rerank_candidates", 16), "scope": lt.get("scope", "shared"),
            "embedding": (lt.get("embedding") or {}).get("provider"),
            "schema": o.get("schema", "MEM"), "profile": (o.get("profile_id") or "TESTBED").upper(),
            "table": f"{o.get('schema', 'MEM')}.{(o.get('table_prefix') or 'TESTBED').upper()}_MEMORIES",
            "lt": lt}


def short_status(ms):
    e = effective(ms)
    b = e["backend"]
    if b == "off":
        return "off"
    where = {"json": "json file", "local": "local dir", "oracle": f"Oracle {e['schema']}",
             "ords": f"Oracle {e['schema']} via ORDS"}.get(b, b)
    if e["configured"] == "auto":
        where = "auto: " + where
    return (f"{where}, {e['embedding']} embeddings, auto store {'on' if e['auto_store'] else 'off'}, "
            f"auto recall {'on' if e['auto_recall'] else 'off'}")


def active_count(timeout=8):
    """Count the active backend's records, quickly (header, status)."""
    import threading
    box = {}

    def run():
        from .memory import MemoryCore
        try:
            mem = MemoryCore(None, "", settings=(config.load_cluster_config() or {}).get("memory_settings"))
            if mem.backend is None:
                mem._connect()
            if mem.backend is None:
                box["e"] = RuntimeError(mem.offline or "offline")
            else:
                box["n"] = mem.backend.count()
        except Exception as e:  # noqa: BLE001
            box["e"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    if "n" in box:
        return box["n"]
    raise box.get("e") or TimeoutError(f"no answer in {timeout} s")


def header_line(ms=None, count_fn=None):
    """The launcher header's Memory field: the ACTIVE backend's count, e.g.
    'Oracle TESTBED: 4 (auto store off)'. count_fn() -> int or raises."""
    e = effective(ms)
    if e["backend"] == "off":
        return "off"
    name = {"oracle": f"Oracle {e['profile']}", "ords": f"Oracle {e['profile']} (ORDS)", "local": "local folder",
            "json": "json file"}.get(e["backend"], e["backend"])
    try:
        n = count_fn() if count_fn else "?"
    except Exception as ex:  # noqa: BLE001 - header must never fail
        n = "unreachable (" + str(ex).splitlines()[0][:60] + ")" if str(ex) else "unreachable"
    flags = []
    if not e["auto_store"]:
        flags.append("auto store off")
    if not e["auto_recall"]:
        flags.append("auto recall off")
    return f"{name}: {n}" + (f" ({', '.join(flags)})" if flags else "")


def setting_lines(ms):
    lt = ltm.settings_from(ms)
    e, o = lt["embedding"], lt["oracle"]
    yn = lambda b: C.onoff(b, "on", "off")  # noqa: E731
    rows = [("Storage", C.value(ltm.describe(lt))),
            ("Shared by clients", C.value(lt.get("scope", "shared"))
             + C.dim("  (shared: one memory for every UI on the endpoint; user: per OpenAI `user` / "
                     "X-Testbed-User)")),
            ("Auto store / auto recall", yn(effective(ms)["auto_store"]) + C.dim(" / ")
             + yn(effective(ms)["auto_recall"]) + C.dim(f"  ({os.path.basename(config.CLUSTER_CONFIG)})")),
            ("What qualifies", C.value(lt["store_mode"]) + C.dim(f" (min {lt['min_chars']} chars; all / salient / "
                                                                 "facts)")),
            ("De-duplication", C.value(lt["dedupe"]) + (C.dim(f" at {lt['dedupe_threshold']}")
                                                        if lt["dedupe"] == "semantic" else "")),
            ("Recall k / threshold", C.value(f"{ms.get('recall_top_k', 6)} / {ms.get('similarity_threshold', 0.45)}")
             + C.dim(f"  (rerank pool {ms.get('rerank_candidates', 16)})")),
            ("Retention", C.value((f"{lt['retention_days']:g} days unseen" if lt["retention_days"] else "keep forever")
                                  + (f", max {lt['max_records']}" if lt["max_records"] else ""))),
            ]
    if ltm.resolve_backend(lt) == "local":
        rows.append(("Local directory", C.value(ltm.local_dir(lt))))
    if e["provider"] in ("openai", "ollama", "nvidia", "sentence_transformers"):
        rows.append(("Embedding", C.value(f"{e['provider']} {e.get('model') or ''} {e.get('url') or ''}".strip())
                     + C.dim(f"  dims {e.get('dimensions') or 'auto'}")
                     + (C.dim(f"  key from ${e['api_key_env']}") if e.get("api_key_env") else "")))
    if lt["backend"] in ("oracle", "auto"):
        rows.append(("Oracle tables", C.value(f"{o['schema']}.{o['table_prefix']}_MEMORIES / _META")
                     + C.dim(f"  profile {o['profile_id']}  index {o['index']} {o['distance']}")))
        rows.append(("Oracle login", C.value(o.get("credentials_file") or "(env only)")
                     + C.dim("  or env " + ", ".join(ORACLE_ENV[k] for k in ("user", "password", "dsn")))))
    if lt["backend"] in ("ords", "auto"):
        if lt["backend"] == "ords":
            rows.append(("Oracle tables", C.value(f"{o['schema']}.{o['table_prefix']}_MEMORIES / _META")
                         + C.dim(f"  profile {o['profile_id']}  index {o['index']} {o['distance']}")))
        rows.extend(ords_lines(lt))
    return [f"  {C.label(f'{n:<26}')} {v}" for n, v in rows]


def _mem(cluster, ms):
    """A MemoryCore for these settings using the Embedding role."""
    from .entity import Entity
    cl = dict(cluster)
    cl["memory_settings"] = ms
    ent = Entity(cluster=cl, memory=False, log=lambda *a: None)
    from .memory import MemoryCore
    return MemoryCore(ent.client, ent._embed_label(), embed_fn=ent._embed_fn(), settings=ms,
                      log=lambda *a: None)


def embed_models_lines():
    out = [C.header("EMBEDDING MODELS") if hasattr(C, "header") else "EMBEDDING MODELS",
           "  The Oracle memory table is VECTOR(2048): use a model that returns 2048 dimensions, or recreate the",
           "  table (nimlab memory reembed --recreate). `nimlab memory test` measures the real size."]
    for m, d in ltm.KNOWN_EMBED.items():
        star = "  (recommended)" if m == ltm.RECOMMENDED_EMBED else ""
        out.append(f"  {m}: {d['dims']} dims, {d['kind']}{star}")
        out.append(f"      {d['note']}")
    out.append("  Use one: nimlab memory embed nvidia <model>")
    return out


def _reembed(mem, a, input_fn=None):
    """Embed every stored memory again with the current embedder. With
    --recreate the table is first backed up to a JSONL file, dropped and
    created at the new size (Oracle: VECTOR(n) is fixed)."""
    recreate = "--recreate" in a
    yes = "--yes" in a or "-y" in a
    if mem.backend is None:
        print(C.err(f"Memory store unavailable: {mem.offline or 'backend is off'}"))
        return 1
    try:
        recs = mem.backend.records(limit=0)
    except Exception as e:  # noqa: BLE001
        print(C.err(f"Could not read the stored memories: {e}"))
        return 1
    probe = mem.embed("re-embed size check", "passage")
    if not probe:
        print(C.err(f"The embedder {mem.label} returned no vector: {mem.last_error or 'no error text'}. "
                    "Fix the embedding first (nimlab memory test)."))
        return 1
    want = mem.table_dims()
    if want and len(probe) != want and not recreate:
        print(C.err(f"{mem.label} returns {len(probe)} dimensions; the table holds VECTOR({want}). Pick a "
                    f"{want}-dimension model (nimlab memory embed models) or run: nimlab memory reembed --recreate"))
        return 1
    print(f"{len(recs)} stored memories; embedder {mem.label} ({len(probe)} dimensions)"
          + (f"; the table will be recreated as VECTOR({len(probe)})" if recreate else ""))
    if recreate and not yes:
        ask = input_fn or input
        if ask("This drops and recreates the memory table (a backup file is written first). Type yes: ")\
                .strip().lower() != "yes":
            print("Not changed.")
            return 1
    if recreate:
        from . import store
        bk = os.path.join(store.data_dir(), f"memory_backup_{time.strftime('%Y%m%d_%H%M%S')}.jsonl")
        os.makedirs(os.path.dirname(bk), exist_ok=True)
        with open(bk, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps({k: v for k, v in r.items() if k != "vector"}, ensure_ascii=False,
                                   default=str) + "\n")
        os.chmod(bk, 0o600)
        print(C.ok(f"  backup: {bk}"))
        for d in mem.setup(recreate=True):
            print(C.ok("  " + d))
    done, failed = mem.reembed(recs, readd=recreate)
    print((C.ok if not failed else C.warn)(f"Re-embedded {done} of {len(recs)} memories" +
                                            (f"; {failed} failed ({mem.last_error})" if failed else "")))
    return 0 if not failed else 1


def test_lines(mem):
    rows = mem.test()
    return [("  " + (C.ok("[ok]  ") if ok else C.err("[!!]  ")) + msg) for ok, msg in rows], all(r[0] for r in rows)


def creds_init(path):
    path = os.path.expanduser(path)
    if os.path.exists(path):
        return f"{path} already exists (not changed)"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(CRED_TEMPLATE, f, indent=2)
    return f"wrote {path} (mode 600): fill in password and dsn (the TLS connect string, or a tnsnames alias + wallet_dir)"


# ---------------------------------------------------------------------------
def ords_lines(lt):
    """Rows for the ORDS backend: where, how it signs in, which secrets are
    found (never their values)."""
    from .ltm_ords import ENV as ORDS_ENV, load_credentials, missing_credentials
    od = lt.get("ords") or {}
    try:
        creds, notes = load_credentials(od)
    except Exception as e:  # noqa: BLE001
        creds, notes = {"auth": od.get("auth") or "basic"}, [str(e)]
    miss = missing_credentials(creds)
    rows = [("ORDS URL", C.value(creds.get("base_url") or "(not set)") + C.dim("  REST-Enabled SQL at <url>/_/sql")),
            ("ORDS sign-in", C.value(creds.get("auth"))
             + C.dim(f"  user {creds.get('user') or '-'}" if creds.get("auth") == "basic"
                     else f"  client {creds.get('client_id') or '-'}")
             + (C.warn("  missing: " + ", ".join(miss)) if miss else C.dim("  login found"))),
            ("ORDS credentials", C.value(od.get("credentials_file") or "(env only)")
             + C.dim("  or env " + ", ".join(ORDS_ENV[k] for k in ("base_url", "user", "password", "client_secret"))))]
    for n in notes:
        rows.append(("", C.warn(n)))
    return rows


def ords_login(ms, input_fn=None, getpass_fn=None, out=print):
    """Ask for the ORDS URL and login and save them in the credentials file
    outside the project (mode 600). The password / client secret is typed
    hidden and never shown or written to config_cluster.json. -> the path."""
    from .ltm_ords import DEFAULT_CREDENTIALS, check_url, save_credentials
    ask = input_fn or C.cinput
    gp = getpass_fn or _getpass.getpass
    lt = ms.setdefault("long_term", ltm.settings_from(ms))
    od = lt.setdefault("ords", dict(ltm.DEFAULTS["ords"]))
    url = ask(f"ORDS schema URL, e.g. https://host/ords/mem [{od.get('base_url') or ''}]: ").strip() \
        or od.get("base_url") or ""
    url = url.rstrip("/")
    if url.endswith("/_/sql"):
        url = url[:-len("/_/sql")]
    bad = check_url(url)
    if bad:
        raise ValueError(bad)
    auth = (ask(f"Sign in with basic (database user) or oauth (client credentials) [{od.get('auth') or 'basic'}]: ")
            .strip().lower() or od.get("auth") or "basic")
    if auth not in ("basic", "oauth"):
        raise ValueError("auth must be basic or oauth")
    values = {"base_url": url, "auth": auth}
    if auth == "basic":
        values["user"] = ask(f"Database user (the REST-enabled schema) [{od.get('user') or 'MEM'}]: ").strip() \
            or od.get("user") or "MEM"
        values["password"] = gp("Password (hidden, saved only in the credentials file): ")
    else:
        values["client_id"] = ask(f"OAuth client id [{od.get('client_id') or ''}]: ").strip() or od.get("client_id")
        values["client_secret"] = gp("OAuth client secret (hidden, saved only in the credentials file): ")
    path = save_credentials(od.get("credentials_file") or DEFAULT_CREDENTIALS, values)
    apply_setting(ms, "ords.base_url", url)
    apply_setting(ms, "ords.auth", auth)
    for k in ("user", "client_id"):
        if values.get(k):
            apply_setting(ms, f"ords.{k}", values[k])
    out(C.ok("Saved: ") + f"{path} (mode 600). The secret is not in config_cluster.json.")
    return path


def cmd_memory(args):
    """./start.sh memory [show|set|use|embed|test|setup|list|recall|identity|forget|prune|sql|creds|ords|load-onnx]"""
    cluster = config.load_cluster_config()
    act = args.action
    if act == "menu":
        try:
            run_menu(cluster, save_fn=lambda: save_ms(cluster["memory_settings"]))
        except (KeyboardInterrupt, EOFError):
            print()
        return 0
    ms = load_ms(cluster)
    a = list(args.values or [])
    if getattr(args, "recreate", False) and "--recreate" not in a:
        a.append("--recreate")
    if getattr(args, "yes", False) and "--yes" not in a:
        a.append("--yes")
    try:
        if act in ("set", "use", "embed"):
            if act == "set":
                if len(a) < 2:
                    raise ValueError("usage: memory set <name> <value>. Settings: " + HELP)
                done = [apply_setting(ms, a[0], *a[1:])]
            elif act == "use":
                if not a:
                    raise ValueError("usage: memory use auto|off|json|local [dir]|oracle [schema]|ords [url]")
                done = use_backend(ms, a[0].lower(), a[1] if len(a) > 1 else None)
            else:
                if not a:
                    raise ValueError("usage: memory embed role|nvidia [model]|openai <url> <model> [dims]|"
                                     "ollama <model> [url]|st [model]|oracle <onnx model>|models")
                if a[0] == "models":
                    for line in embed_models_lines():
                        print(line)
                    return 0
                done = use_embedder(ms, a[0], *a[1:])
            save_ms(ms)
            for d in done:
                print(C.ok("Set: ") + d)
            print(C.hint("Run `./start.sh memory test` to check the connection."))
            return 0
    except ValueError as e:
        print(C.err(f"Not changed: {e}"))
        return 2
    if act == "show":
        print(C.header("LONG-TERM MEMORY"))
        for line in setting_lines(ms):
            print(line)
        return 0
    if act == "sql":
        from .ltm_oracle import OracleBackend
        lt = ltm.settings_from(ms)
        b = OracleBackend.__new__(OracleBackend)
        o = lt["oracle"]
        b.o, b.schema, b.prefix = o, o["schema"].upper(), o["table_prefix"].upper()
        b.profile, b.index, b.distance = o["profile_id"].upper(), o["index"], o["distance"].upper()
        b.accuracy, b.onnx = int(o["target_accuracy"]), ""
        b._check_names()
        b.t_mem, b.t_meta, b.vidx = f"{b.schema}.{b.prefix}_MEMORIES", f"{b.schema}.{b.prefix}_META", \
            f"{b.prefix}_MEMORIES_VIDX"
        dims = int(a[0]) if a else int(o.get("dims") or lt["embedding"].get("dimensions") or 2048)
        for stmt in b.ddl(dims):
            print(stmt.split("*/ ", 1)[-1] + ";")
        return 0
    if act == "ords":
        sub = (a[0] if a else "show").lower()
        if sub == "login":
            try:
                ords_login(ms)
            except ValueError as e:
                print(C.err(f"Not changed: {e}"))
                return 2
            except (KeyboardInterrupt, EOFError):
                print()
                return 1
            save_ms(ms)
            print(C.hint("Then: ./start.sh memory use ords, ./start.sh memory setup (once), ./start.sh memory test"))
            return 0
        if sub == "show":
            print(C.header("LONG-TERM MEMORY: ORDS"))
            for n, v in ords_lines(ltm.settings_from(ms)):
                print(f"  {C.label(f'{n:<26}')} {v}")
            return 0
        print(C.err("usage: memory ords [show|login]"))
        return 2
    if act == "creds":
        path = ltm.settings_from(ms)["oracle"]["credentials_file"]
        if a and a[0] == "init":
            print(creds_init(path))
        else:
            print(f"Credentials file: {os.path.expanduser(path)}"
                  + (" (exists)" if os.path.exists(os.path.expanduser(path)) else " (missing: memory creds init)"))
            print("Keys: " + ", ".join(CRED_TEMPLATE) + ". Env vars override it: "
                  + ", ".join(ORACLE_ENV.values()) + ".")
        return 0
    mem = _mem(cluster, ms)
    if act == "test":
        print(C.header("LONG-TERM MEMORY: CONNECTION TEST"))
        lines, ok = test_lines(mem)
        for line in lines:
            print(line)
        try:   # setup's Memory status follows the latest test of these settings
            from .wizard import record_memory_check
            record_memory_check(ms, 0 if ok else 1, "\n".join(lines))
        except Exception:  # noqa: BLE001
            pass
        return 0 if ok else 1
    if act == "status":
        print(header_line(ms, count_fn=lambda: mem.backend.count() if mem.backend else
                          (_ for _ in ()).throw(RuntimeError(mem.offline or "offline"))))
        print("  " + short_status(ms))
        return 0
    if act == "pending":
        items = mem.pending()
        print(f"{len(items)} turn(s) wait for an embedding ({mem.pending_path()})")
        for it in items[-20:]:
            print(f"  {it.get('timestamp', '')}  {it.get('text', '')[:90]!r}  ({it.get('reason', '')[:80]})")
        return 0
    if act in ("embed-pending", "flush-queue"):
        n0 = len(mem.pending())
        if not n0:
            print(C.ok("No queued turns."))
            return 0
        stored, left = mem.embed_pending(limit=int(a[0]) if a and a[0].isdigit() else 500)
        print((C.ok if not left else C.warn)(f"Embedded and stored {stored} of {n0} queued turn(s); {left} still "
                                             "waiting" + (f" ({mem.last_error})" if left and mem.last_error else "")))
        return 0 if not left else 1
    if act == "reembed":
        return _reembed(mem, a)
    if mem.backend is None:
        print(C.err(f"Memory store unavailable: {mem.offline or 'backend is off'}"))
        return 1
    if act == "setup":
        try:
            for d in mem.setup(recreate=bool(a and a[0] == "--recreate")):
                print(C.ok("  " + d))
        except Exception as e:  # noqa: BLE001
            print(C.err(f"Setup failed: {e}"))
            return 1
        return 0
    if act == "add":
        # 3.8.1: /remember on Telegram; also pins "my name is ..." as an identity fact
        a = list(a)
        user = None
        if "--user" in a:
            i = a.index("--user")
            user = a[i + 1] if i + 1 < len(a) else None
            del a[i:i + 2]
        text = " ".join(a).strip()
        if not text:
            print(C.err("Usage: memory add <text> [--user ID]"))
            return 2
        md = {"source": "remember", "user": user} if user else {"source": "remember"}

        def _queued():
            try:
                return len(mem.pending())
            except Exception:  # noqa: BLE001
                return 0
        q0 = _queued()
        with mem.scoped(user):
            pinned = mem.pin_identity_from(text, metadata=md) if lt_on(ms, "pin_identity") else []
            rid = mem.store(text, metadata=md, kind="note", dedupe="exact")
        if rid or pinned:
            print(C.ok(f"Remembered ({len(pinned)} identity fact(s) pinned)." if pinned and not rid else
                       "Remembered." + (f" Pinned {len(pinned)} identity fact(s)." if pinned else "")))
            return 0
        if _queued() > q0:
            print(C.warn("Queued: it is saved and gets embedded when the embedding model answers."))
            return 0
        print(C.warn("Already remembered (or nothing to store)."
                     + (f" {mem.last_error}" if mem.last_error else "")))
        return 0
    if act == "list":
        recs = mem.backend.records(int(a[0]) if a else 20)
        for r in recs:
            print(f"  {C.dim(r['id'])} {C.dim((r.get('timestamp') or '')[:19])} {r['text'][:140]}")
        print(C.dim(f"  {mem.count()} memories in {mem.backend.where()}"))
        return 0
    if act == "recall":
        # 3.8.0: the same hybrid (vector + keyword) ranking a reply uses
        q = " ".join(a)
        ident = bool(ltm.IDENTITY_ASK.search(q))
        hits, info = mem.recall_hybrid(q, top_k=ms.get("recall_top_k", 6),
                                       threshold=ms.get("similarity_threshold", 0.45),
                                       candidates=ms.get("rerank_candidates", 16),
                                       keyword_weight=ms.get("hybrid_keyword_weight", 0.6),
                                       hybrid=ms.get("hybrid_recall", True),
                                       extra_terms=ltm.identity_terms(q) if ident else None)
        facts = mem.identity_facts() if lt_on(ms, "pin_identity") else {}
        for k, v in facts.items():
            print(f"  {C.value('pinned')} {ltm.IDENTITY_LABELS.get(k, k)}: {v}")
        for sim, text, ts, rid in hits:
            print(f"  {C.value(f'{sim:.3f}')} {text[:160]} {C.dim(rid)}")
        if not hits:
            print(C.dim("  nothing above the threshold" + (f" ({mem.offline})" if mem.offline else "")))
        print(C.dim(f"  vector {info.get('vector', 0)}, keyword {info.get('keyword', 0)}, "
                    f"skipped {info.get('dropped', 0)} (self-test, 'I don't remember' answers, pinned facts)"))
        return 0
    if act == "identity":
        # 3.8.0: pinned identity facts: identity | identity set <key> <value> | identity forget <key>
        if a and a[0] == "set" and len(a) >= 3:
            rid = mem.pin_identity(a[1].lower(), " ".join(a[2:]), metadata={"source": "cli"})
            print(C.ok("Pinned.") if rid else C.dim("Already pinned."))
            return 0
        if a and a[0] == "forget" and len(a) >= 2:
            n = 0
            for r in mem._identity_records():
                kv = ltm.parse_identity(r.get("text"))
                if kv and kv[0] == a[1].lower() and r.get("id") and not r.get("pending"):
                    n += bool(mem.delete(r["id"]))
            mem._ident_cache.clear()
            print(C.ok(f"Removed {n}.") if n else C.warn("Nothing pinned under that key."))
            return 0
        if a:
            print("usage: memory identity [set <name|birthday|location|pronouns> <value> | forget <key>]")
            return 2
        facts = mem.identity_facts()
        for k, v in facts.items():
            print(f"  {ltm.IDENTITY_LABELS.get(k, k)}: {v}")
        if not facts:
            print(C.dim("  nothing pinned yet (say \"my name is ...\" on any channel)"))
        return 0
    if act == "forget":
        if not a:
            print("usage: memory forget <id>")
            return 2
        print(C.ok("Deleted.") if mem.delete(a[0]) else C.warn("No such memory."))
        return 0
    if act == "prune":
        print(f"Dropped {mem.prune()} memories (retention {ltm.settings_from(ms)['retention_days']} days, "
              f"max {ltm.settings_from(ms)['max_records'] or 'none'}).")
        return 0
    if act == "load-onnx":
        if len(a) < 2 or not hasattr(mem.backend, "load_onnx_cloud"):
            print("usage (oracle backend): memory load-onnx <MODEL_NAME> <object storage URI> [credential]")
            return 2
        try:
            name = mem.backend.load_onnx_cloud(a[0], a[1], a[2] if len(a) > 2 else None)
        except Exception as e:  # noqa: BLE001
            print(C.err(f"Load failed: {e}"))
            return 1
        apply_setting(ms, "oracle.onnx_model", name)
        save_ms(ms)
        print(C.ok(f"Loaded {name}; `memory embed oracle {name}` uses it."))
        return 0
    print(f"unknown action {act}")
    return 2


# ---------------------------------------------------------------------------
MENU = (("Storage", (("1", "Backend", "off / json / local / oracle / ords"),
                     ("2", "Local folder", "default data/ltm"),
                     ("3", "Oracle connection", "schema, login, index"),
                     ("3o", "ORDS (HTTPS) connection", "URL, basic or OAuth login"),
                     ("4", "Embedding", "role / NVIDIA / OpenAI / Ollama / ST / ONNX"))),
        ("Behaviour", (("5", "Auto store", "on / off"), ("6", "Auto recall", "on / off"),
                       ("7", "What to save", "all / salient / facts"),
                       ("8", "De-duplication", "off / exact / semantic"),
                       ("9", "Recall", "top-k, threshold, rerank pool"),
                       ("10", "Retention", "days unseen, max records"),
                       ("11", "Shared or per user", ""))),
        ("Check", (("12", "Test connection", ""), ("13", "Set up Oracle", "tables in MEM"))))


def run_menu(cluster, input_fn=None, out=print, save_fn=None, header_fn=None, memory=None, getpass_fn=None):
    """Long-term memory menu (testbed Settings -> Memory, launcher Memory,
    ./start.sh memory menu). cluster['memory_settings'] is changed in
    place; save_fn() persists it and reloads the entity."""
    ask = input_fn or C.cinput
    seen = _mtime()
    while True:
        # 3.7.1: when another process changed config_cluster.json while this
        # menu is open (setup, `memory set`, the service's self-admin), show
        # and edit the file's memory_settings, never a stale copy that would
        # then be written back over them.
        now = _mtime()
        if now != seen and now is not None:
            fresh = (config.load_cluster_config() or {}).get("memory_settings")
            if isinstance(fresh, dict):
                cluster["memory_settings"] = copy.deepcopy(fresh)
        ms = load_ms(cluster)
        lt = ms["long_term"]
        before = copy.deepcopy(ms)
        if header_fn:
            header_fn("LONG-TERM MEMORY STORAGE")
        else:
            out("\n" + C.header("LONG-TERM MEMORY STORAGE"))
        for line in setting_lines(ms):
            out(line)
        if memory is not None:
            out("  " + C.dim(memory.status_line()))
        out(C.rule(50))
        for title, rows in MENU:
            out(C.section(title))
            for k, name, extra in rows:
                out(C.entry(k, name, extra))
        out(C.entry(0, "Back"))
        c = ask("\nSelection: ").strip().lower()
        c = {"t": "12", "s": "13"}.get(c, c)  # the old letter keys still work
        try:
            if c == "0" or c == "":
                return
            if c == "1":
                b = ask("Backend [auto/off/json/local/oracle/ords]: ").strip().lower()
                if b:
                    use_backend(ms, b)
                    if b in ("oracle", "auto", "ords"):
                        out(C.hint("Default: its own tables in the MEM schema (MEM.TESTBED_MEMORIES), profile "
                                   "TESTBED. Set the login in " + ("3o." if b == "ords" else "3.")))
            elif c == "4":
                p = ask("Provider [role/nvidia/openai/ollama/st/oracle]: ").strip().lower()
                if p in ("openai", "local"):
                    use_embedder(ms, "openai", ask("Base URL (e.g. http://127.0.0.1:11434/v1): ").strip(),
                                 ask("Model: ").strip(), ask("Dimensions (Enter = auto): ").strip() or "0")
                    env = ask("Env var holding its API key (Enter = none): ").strip()
                    apply_setting(ms, "embedding.api_key_env", env or "-")
                elif p == "ollama":
                    use_embedder(ms, "ollama", ask("Model [nomic-embed-text]: ").strip() or "nomic-embed-text",
                                 ask(f"URL [{ltm.DEFAULT_OLLAMA_URL}]: ").strip() or ltm.DEFAULT_OLLAMA_URL)
                elif p in ("nvidia", "st", "sentence_transformers"):
                    dflt = ltm.DEFAULT_NV_EMBED if p == "nvidia" else ltm.DEFAULT_ST_MODEL
                    use_embedder(ms, p, ask(f"Model [{dflt}]: ").strip() or dflt)
                elif p == "oracle":
                    use_embedder(ms, "oracle", ask("ONNX model name in the database: ").strip())
                elif p == "role":
                    use_embedder(ms, "role")
            elif c == "2":
                d = ask("Directory (Enter = data/ltm, - = default): ").strip()
                if d:
                    apply_setting(ms, "local.directory", d)
            elif c == "3":
                o = lt["oracle"]
                for key, label in (("schema", "Schema"), ("table_prefix", "Table prefix"), ("profile_id", "Profile id"),
                                   ("credentials_file", "Credentials file"), ("user", "User (or in the file)"),
                                   ("dsn", "DSN / TNS alias (or in the file)"), ("wallet_dir", "Wallet dir (mTLS)"),
                                   ("index", "Vector index ivf/hnsw/none")):
                    v = ask(f"{label} [{o.get(key) or ''}]: ").strip()
                    if v:
                        apply_setting(ms, f"oracle.{key}", v)
                out(C.hint(f"The password is never stored here: export {ORACLE_ENV['password']}=... or put it in "
                           f"{o.get('credentials_file')} (`./start.sh memory creds init` makes one, mode 600)."))
            elif c == "3o":
                ords_login(ms, input_fn=ask, getpass_fn=getpass_fn, out=out)
                if lt.get("backend") != "ords" and ask("Use ORDS for memory now? [Y/n]: ").strip().lower() \
                        in ("", "y", "yes"):
                    use_backend(ms, "ords")
            elif c in ("5", "6"):
                key = "auto_store" if c == "5" else "auto_recall"
                cur = ltm.as_bool(lt.get(key, True))
                v = ask(f"{'Auto store' if c == '5' else 'Auto recall'} is {'on' if cur else 'off'}. "
                        "on / off [keep]: ").strip()
                if v:
                    apply_setting(ms, key, v)
            elif c == "7":
                m = ask("all / salient / facts: ").strip()
                if m:
                    apply_setting(ms, "store_mode", m)
            elif c == "8":
                m = ask("off / exact / semantic: ").strip()
                if m:
                    apply_setting(ms, "dedupe", m)
                    if m == "semantic":
                        t = ask(f"Near-duplicate similarity [{lt['dedupe_threshold']}]: ").strip()
                        if t:
                            apply_setting(ms, "dedupe_threshold", t)
            elif c == "9":
                k = ask(f"Top-k [{ms.get('recall_top_k', 6)}]: ").strip()
                if k:
                    apply_setting(ms, "k", k)
                t = ask(f"Similarity threshold [{ms.get('similarity_threshold', 0.45)}]: ").strip()
                if t:
                    apply_setting(ms, "threshold", t)
                r = ask(f"Rerank candidate pool [{ms.get('rerank_candidates', 16)}]: ").strip()
                if r:
                    try:
                        ms["rerank_candidates"] = max(1, min(50, int(r)))
                    except ValueError:
                        out(C.warn("Rerank pool must be a whole number (1-50)."))
            elif c == "10":
                d = ask(f"Forget memories not seen for N days (0 = never) [{lt['retention_days']}]: ").strip()
                if d:
                    apply_setting(ms, "retention_days", d)
                m = ask(f"Keep at most N memories (0 = no cap) [{lt['max_records']}]: ").strip()
                if m:
                    apply_setting(ms, "max_records", m)
            elif c == "11":
                m = ask("shared (one memory for every client) / user (per client id): ").strip()
                if m:
                    apply_setting(ms, "scope", m)
            elif c in ("12", "13"):
                if save_fn:
                    save_fn()
                mem = memory if memory is not None else _mem(cluster, ms)
                mem.reconfigure(ms)
                if c == "12":
                    for line in test_lines(mem)[0]:
                        out(line)
                else:
                    for d in mem.setup():
                        out(C.ok("  " + d))
                ask("\nPress Enter to continue...")
                continue
        except (ValueError, RuntimeError) as e:
            out(C.err(f"  Not changed: {e}"))
            ask("Press Enter to continue...")
        except Exception as e:  # noqa: BLE001 - a backend failure must not leave the menu
            out(C.err(f"  {e}"))
            ask("Press Enter to continue...")
        if ms == before:
            continue            # nothing changed: write nothing
        now = _mtime()
        if now != seen and now is not None:
            # the file changed while the question was open: apply only what
            # this action changed on top of the file's current settings
            fresh = (config.load_cluster_config() or {}).get("memory_settings")
            if isinstance(fresh, dict):
                ms = _apply_diff(load_ms({"memory_settings": copy.deepcopy(fresh)}), before, ms)
        cluster["memory_settings"] = ms
        if save_fn:
            save_fn()
        seen = _mtime()
