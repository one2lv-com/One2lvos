"""The lab's data stores: one module owns every data path, load and save.

Everything the lab learns lives in data/ (override with NIMLAB_DATA_DIR):

  endpoints.json          every known endpoint URL + the router's rules
  models_discovered.json  every model from build.nvidia.com, docs and the key
  models_verified.json    only models whose last test answered 200 OK
  benchmark_latest.json   the most recent benchmark run
  benchmark_history.json  short summaries of the last runs
  probe_results.json      the last test result of every model ever probed
  judge_leaderboard.json  judge rankings per role
  judge_entity_scores.json  judge scores for role combinations
  memory.json             the entity's vector memory
  test_history.jsonl      the playground's single-test log
  legacy/                 the pre-3.1 files, moved here by the migration

A missing store is created with a valid empty structure the first time it
is read; a corrupt one is moved to legacy/ and recreated. All writes are
atomic (config.save_json). Nothing here ever stores the API key: entries are
URLs, statuses and request templates, and every free-text reason passes
through core.redact.

Sync rule (see README "Data files"): new results add what is new and remove
what a run covered but no longer found. A run only removes within what it
actually checked, and every removed record is kept in that store's archive
section (removed / dropped / stale / archived).
"""

import copy
import json
import os
import shutil
import sys
import threading
import time

from . import config, defaults
from .core import redact

SCHEMA = 1

ENDPOINTS = "endpoints.json"
DISCOVERED = "models_discovered.json"
VERIFIED = "models_verified.json"
BENCHMARK = "benchmark_latest.json"
BENCH_HISTORY = "benchmark_history.json"
PROBES = "probe_results.json"
LEADERBOARD = "judge_leaderboard.json"
ENTITY_SCORES = "judge_entity_scores.json"
MEMORY = "memory.json"
TEST_HISTORY = "test_history.jsonl"
LEGACY_DIR = "legacy"

LIVE = "LIVE_200"
# results that say nothing about whether the model works right now: they
# never add to or remove from the verified list
INCONCLUSIVE = {"SPEC_FOUND_NOT_PROBED", "NO_SPEC_FOUND", "RATE_LIMITED"}
# failures that can come from the phone's side (bad key, no network)
OUTAGE = {"AUTH_OR_ENTITLEMENT", "TIMEOUT_OR_SERVER_ERROR"}
# endpoints from these sources are the routing base, never marked stale
SEED_SOURCES = {"registry", "matrix", "override"}
PROBE_HISTORY = 5
BENCH_HISTORY_MAX = 10

_lock = threading.RLock()
_ready_for = None  # data dir the migration check last ran for


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def data_dir():
    return os.environ.get("NIMLAB_DATA_DIR") or os.path.join(config.PROJECT_DIR, "data")


def project_root():
    """Folder that holds the pre-3.1 files: the data folder's parent."""
    return os.path.dirname(os.path.abspath(data_dir()))


def path(name):
    d = data_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def now():
    return config.timestamp()


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
def _seed_endpoints(doc, at=None):
    """Add every concrete URL the routing rules and route matrix name."""
    routing = doc.get("routing") or {}
    gw = routing.get("gateways") or {}
    for kind, r in (routing.get("static_routes") or {}).items():
        base = gw.get(r.get("gateway", ""), "")
        if base and r.get("path"):
            record_endpoint(doc, base.rstrip("/") + r["path"], r.get("method", "POST"), kind=kind,
                            source="registry", at=at, touch=False)
    for mid, o in (routing.get("explicit_model_overrides") or {}).items():
        url = o.get("url")
        if not url and o.get("gateway") in gw and o.get("path"):
            url = gw[o["gateway"]].rstrip("/") + o["path"]
        if url:
            src = "spec" if o.get("source") == "spec_sweep" else "override"
            record_endpoint(doc, url, o.get("method", "POST"), content_type=o.get("content_type"),
                            kind=o.get("kind"), function_id=o.get("function_id"), model=mid, source=src,
                            at=at, touch=False)
    for r in doc.get("candidate_routes") or []:
        if r.get("url"):
            record_endpoint(doc, r["url"], r.get("method", "POST"), kind=r.get("kind"), source="matrix",
                            at=at, touch=False)
    return doc


def default_endpoints():
    doc = {"schema": SCHEMA, "updated_at": None,
           "routing": copy.deepcopy(defaults.ROUTING),
           "candidate_routes": copy.deepcopy(defaults.CANDIDATE_ROUTES),
           "endpoints": {}, "stale": {}, "last_sync": None}
    return _seed_endpoints(doc)


def empty_summary():
    return {"total": 0, "on_site": 0, "in_docs": 0, "in_key_list": 0, "on_site_not_in_key": 0,
            "in_key_not_on_site": 0, "deprecated": 0, "retired": 0, "unlisted": 0, "kinds": {}}


def default_discovered():
    return {"schema": SCHEMA, "generated_at": None, "sources": {}, "source_counts": {}, "errors": {},
            "summary": empty_summary(), "key_list": {"models": [], "updated_at": None, "source": None},
            "last_sync": None, "models": {}, "removed": {}}


def default_verified():
    return {"schema": SCHEMA, "updated_at": None, "last_sync": None, "models": {}, "dropped": {}}


def default_probes():
    return {"schema": SCHEMA, "updated_at": None, "models": {}, "archived": {}}


DEFAULTS = {
    ENDPOINTS: (default_endpoints, dict),
    DISCOVERED: (default_discovered, dict),
    VERIFIED: (default_verified, dict),
    BENCHMARK: (lambda: {"schema": SCHEMA, "timestamp": None}, dict),
    BENCH_HISTORY: (lambda: {"schema": SCHEMA, "runs": []}, dict),
    PROBES: (default_probes, dict),
    LEADERBOARD: (dict, dict),
    ENTITY_SCORES: (dict, dict),
    MEMORY: (list, list),
}
# keys a dict store must have; missing ones are filled from the default
REQUIRED = {ENDPOINTS: ("routing", "endpoints", "stale", "candidate_routes"),
            DISCOVERED: ("models", "removed", "key_list", "summary"),
            VERIFIED: ("models", "dropped"), PROBES: ("models", "archived"), BENCH_HISTORY: ("runs",)}


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------
def ensure_all():
    """Migrate pre-3.1 files if any are present, then create every missing
    store. Safe to call often; does the work once per data folder."""
    global _ready_for
    d = os.path.abspath(data_dir())
    if _ready_for == d:
        return
    with _lock:
        if _ready_for == d:
            return
        _ready_for = d  # set first: migrate() itself loads stores
        try:
            if legacy_files():
                migrate(log=lambda m: print(m, file=sys.stderr))
            if os.path.abspath(project_root()) == os.path.abspath(config.PROJECT_DIR):
                config.ensure_config_files()
            for name in DEFAULTS:
                if not os.path.exists(path(name)):
                    config.save_json(path(name), DEFAULTS[name][0]())
            th = path(TEST_HISTORY)
            if not os.path.exists(th):
                open(th, "a", encoding="utf-8").close()
        except BaseException:
            _ready_for = None
            raise


def reset():
    """Forget the per-process migration check (tests change NIMLAB_DATA_DIR)."""
    global _ready_for
    _ready_for = None


def load(name):
    ensure_all()
    return _load_raw(name)


def _load_raw(name):
    p = path(name)
    factory, typ = DEFAULTS[name]
    if not os.path.exists(p):
        data = factory()
        config.save_json(p, data)
        return data
    data = config.load_json(p, None)
    if not isinstance(data, typ):
        _quarantine(p)
        data = factory()
        config.save_json(p, data)
        return data
    if isinstance(data, dict):
        base = None
        for k in REQUIRED.get(name, ()):
            if k not in data:
                base = base or factory()
                data[k] = base[k]
    return data


def save(name, data):
    if isinstance(data, dict) and name not in (LEADERBOARD, ENTITY_SCORES):
        data.setdefault("schema", SCHEMA)
        if "updated_at" in data or name in (ENDPOINTS, VERIFIED, PROBES):
            data["updated_at"] = now()
    _write(path(name), data)


def _write(p, data):
    """Atomic write with a last guard: no API key (the live one or anything
    key-shaped) ever lands in a store."""
    text = json.dumps(data, ensure_ascii=False)
    clean = redact(text)
    if clean != text:
        data = json.loads(clean)
    config.save_json(p, data)


def _quarantine(p):
    """Move an unreadable store aside instead of overwriting it."""
    dest = os.path.join(data_dir(), LEGACY_DIR, "corrupt")
    os.makedirs(dest, exist_ok=True)
    try:
        shutil.move(p, os.path.join(dest, f"{time.strftime('%Y%m%d-%H%M%S')}_{os.path.basename(p)}"))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Endpoint registry
# ---------------------------------------------------------------------------
def endpoint_key(url, method="POST"):
    return f"{(method or 'POST').upper()} {url}"


def _host(url):
    rest = url.split("://", 1)[-1]
    return rest.split("/", 1)[0]


def record_endpoint(doc, url, method="POST", content_type=None, kind=None, function_id=None, model=None,
                    source="sweep", result=None, at=None, touch=True):
    """Add a URL to the registry, or update it. Returns 'added', 'updated'
    or 'revived' (it was stale and has been seen again)."""
    if not url or not isinstance(url, str) or "://" not in url and not url.startswith("grpc"):
        return None
    at = at or now()
    key = endpoint_key(url, method)
    active, stale = doc.setdefault("endpoints", {}), doc.setdefault("stale", {})
    state = "updated"
    if key in stale:
        rec = stale.pop(key)
        rec.pop("stale_since", None)
        rec.pop("stale_reason", None)
        active[key] = rec
        state = "revived"
    rec = active.get(key)
    if rec is None:
        rec = active[key] = {"url": url, "method": (method or "POST").upper(), "content_type": None,
                             "host": _host(url), "kind": None, "function_id": None, "models": [],
                             "sources": [], "first_seen": at, "last_seen": at, "last_result": None}
        state = "added"
    elif touch:
        rec["last_seen"] = at
    for f, v in (("content_type", content_type), ("kind", kind), ("function_id", function_id)):
        if v and not rec.get(f):
            rec[f] = v
    if "nvcf.nvidia.com" in url and "gateway" not in rec:
        rec["gateway"] = "nvcf"
    if source and source not in rec["sources"]:
        rec["sources"].append(source)
    if model:
        if model not in rec["models"]:
            rec["models"].append(model)
            rec["models"].sort(key=str.lower)
        former = rec.get("former_models") or []
        if model in former:
            former.remove(model)
    if result:
        rec["last_result"] = {k: v for k, v in result.items() if v is not None}
    return state


def routing():
    """The router's rules (gateways, static routes, prefix rules, NVCF
    fallbacks, per-model overrides), as NvidiaRouter expects them."""
    r = load(ENDPOINTS).get("routing")
    return r if isinstance(r, dict) and r.get("gateways") else copy.deepcopy(defaults.ROUTING)


def candidate_routes():
    return load(ENDPOINTS).get("candidate_routes") or []


def endpoint_models():
    """Every model id the registry associates with an endpoint or override."""
    doc = load(ENDPOINTS)
    ids = set((doc.get("routing") or {}).get("explicit_model_overrides") or {})
    for rec in doc["endpoints"].values():
        ids.update(rec.get("models") or [])
    return sorted(ids, key=str.lower)


# ---------------------------------------------------------------------------
# Discovered models
# ---------------------------------------------------------------------------
def _source_family(s):
    return "key" if s in ("key", "key_cache") else s


def discovered(include_empty=False):
    """The discovered-models document (catalog shape), or None when no
    discovery has run yet (unless include_empty)."""
    doc = load(DISCOVERED)
    if not include_empty and not doc.get("models"):
        return None
    return doc


def key_list():
    kl = load(DISCOVERED).get("key_list") or {}
    return list(kl.get("models") or [])


def save_key_list(models, source="key"):
    """Store the key's /v1/models list and add any model it names that
    discovery has not seen yet."""
    with _lock:
        doc = load(DISCOVERED)
        at = now()
        ids = sorted({m for m in models if isinstance(m, str) and m.strip()}, key=str.lower)
        doc["key_list"] = {"models": ids, "updated_at": at, "source": source}
        from . import spec
        known = {spec.match_key(m) for m in doc["models"]}
        for mid in ids:
            if spec.match_key(mid) in known:
                e = next(v for k, v in doc["models"].items() if spec.match_key(k) == spec.match_key(mid))
                if source not in e.setdefault("sources", []):
                    e["sources"].append(source)
                e["in_key_list"] = True
                e["last_seen"] = at
                continue
            pub, _, name = mid.partition("/")
            doc["models"][mid] = {"id": mid, "publisher": pub, "name": name, "kind": None, "sources": [source],
                                  "status": "active", "flags": [], "in_key_list": True,
                                  "first_seen": at, "last_seen": at}
            doc["removed"].pop(mid, None)
        _resummarize(doc)
        save(DISCOVERED, doc)
    return ids


def _resummarize(doc):
    from . import catalog
    for e in doc["models"].values():
        if not e.get("kind"):
            e["kind"] = catalog.classify_kind(e["id"], e.get("labels"), e.get("docs_category"),
                                              e.get("playground_type"))
        e.setdefault("status", "active")
        e.setdefault("sources", [])
        e.setdefault("flags", [])
    doc["models"] = dict(sorted(doc["models"].items(), key=lambda kv: kv[0].lower()))
    doc["summary"] = catalog.summarize(doc["models"]) if doc["models"] else empty_summary()


def sync_discovered(new_doc, covered, at=None):
    """Merge a fresh discovery into the store.

    covered: source families this run read successfully ('site', 'sitemap',
    'docs', 'key'). A model missing from the new data loses only the covered
    sources; it is removed (to 'removed') only when no source still lists it.
    An empty covered set (everything offline) adds but never removes.
    Returns stats."""
    from . import spec
    at = at or now()
    covered = {_source_family(s) for s in covered or ()}
    with _lock:
        doc = load(DISCOVERED)
        old = doc["models"]
        old_by_key = {spec.match_key(k): k for k in old}
        removed_by_key = {spec.match_key(k): k for k in doc["removed"]}
        out, stats = {}, {"added": [], "returned": [], "removed": [], "kept_unchecked": [], "updated": 0}
        seen_old = set()
        for mid, e in (new_doc.get("models") or {}).items():
            e = dict(e)
            k = spec.match_key(mid)
            prev = old.get(old_by_key[k]) if k in old_by_key else None
            if prev is not None:
                seen_old.add(old_by_key[k])
                e["first_seen"] = prev.get("first_seen") or at
                carry = [s for s in prev.get("sources") or [] if _source_family(s) not in covered
                         and s not in e.get("sources", [])]
                e["sources"] = list(e.get("sources") or []) + carry
                stats["updated"] += 1
            elif k in removed_by_key:
                back = doc["removed"].pop(removed_by_key[k])
                e["first_seen"] = back.get("first_seen") or at
                stats["returned"].append(mid)
            else:
                e["first_seen"] = at
                stats["added"].append(mid)
            e["last_seen"] = at
            out[mid] = e
        for mid, prev in old.items():
            if mid in seen_old:
                continue
            remaining = [s for s in prev.get("sources") or [] if _source_family(s) not in covered]
            if remaining:
                out[mid] = dict(prev, sources=remaining)
                stats["kept_unchecked"].append(mid)
            else:
                gone = sorted({_source_family(s) for s in prev.get("sources") or []}) or ["(none)"]
                doc["removed"][mid] = dict(prev, removed_at=at,
                                           removed_reason="no longer listed by " + ", ".join(gone))
                stats["removed"].append(mid)
        doc["models"] = out
        for f in ("generated_at", "sources", "source_counts", "errors"):
            if f in new_doc:
                doc[f] = new_doc[f]
        doc["last_sync"] = {"at": at, "covered_sources": sorted(covered),
                            **{k: (len(v) if isinstance(v, list) else v) for k, v in stats.items()}}
        _resummarize(doc)
        save(DISCOVERED, doc)
    return stats


# ---------------------------------------------------------------------------
# Verified 200 models, probe results, endpoint sync
# ---------------------------------------------------------------------------
VERIFIED_FIELDS = ("url", "method", "content_type", "kind", "function_id", "api_model_id", "catalog_id",
                   "catalog_kind", "request_template", "latency_sec", "http_status", "payload_used",
                   "route_source", "transport", "page_url", "docs_url", "spec_source", "deprecation", "reason")


def verified_models():
    """{model_id: record} of the current 200 OK fleet."""
    return dict(load(VERIFIED)["models"])


def verified_ids():
    return sorted(load(VERIFIED)["models"], key=str.lower)


def _verified_record(e, sweep, prev=None, at=None):
    rec = {k: e[k] for k in VERIFIED_FIELDS if e.get(k) is not None}
    rec["status"] = LIVE
    rec["verified_at"] = e.get("checked_at") or at or now()
    rec["verified_by"] = e.get("checked_by") or sweep
    rec["first_verified"] = (prev or {}).get("first_verified") or rec["verified_at"]
    if "reason" in rec:
        rec["reason"] = redact(rec["reason"])
    return rec


def _brief(e, sweep):
    return {k: v for k, v in {"status": e.get("status"), "http_status": e.get("http_status"),
                              "url": e.get("url"), "latency_sec": e.get("latency_sec"),
                              "reason": redact(e.get("reason") or "")[:200] or None,
                              "at": e.get("checked_at"), "sweep": e.get("checked_by") or sweep}.items()
            if v is not None}


def _keyed_results(results):
    """Key results by the id the API accepts (the spec's model id) when it
    differs from the catalog id, so router, fleet and judge send that id."""
    out = {}
    for mid, e in results.items():
        api_id = e.get("api_model_id")
        if api_id and api_id != mid and e.get("status") in (LIVE, "NEEDS_DIFFERENT_PAYLOAD"):
            out[api_id] = dict(e, catalog_id=mid)
        else:
            out[mid] = e
    return out


def known_models():
    """Every model the lab knows: discovered + registry + verified."""
    ids = set(load(DISCOVERED)["models"]) | set(endpoint_models()) | set(load(VERIFIED)["models"])
    return ids


def apply_results(results, sweep="spec_sweep", complete=False, at=None, known=None, probed=True):
    """Fold one sweep's per-model results into every store.

    - probe_results.json: each model's latest result (+ a short history).
    - models_verified.json: a 200 adds/updates the model; a conclusive
      failure moves it to 'dropped' with its last result. With complete=True
      (the run swept the whole default list) a verified model that is no
      longer known anywhere (not discovered, not in the registry, not in
      this run) is dropped too; one the run merely skipped is left alone.
    - endpoints.json: every spec endpoint, working URL and non-404 probed URL
      is added or refreshed; spec-derived routes become router overrides.
      With complete=True, sweep-found endpoints that no model uses any more
      move to 'stale'.
    probed=False (a plan-only pass): only the endpoint registry changes.
    Returns stats."""
    at = at or now()
    results = _keyed_results(results)
    if not probed:
        complete = False
    stats = {"verified_added": [], "verified_kept": 0, "verified_dropped": [], "endpoints_added": 0,
             "endpoints_revived": 0, "endpoints_staled": 0, "overrides": 0, "outage": False}
    conclusive = [str(e.get("status")) for e in results.values() if e.get("status") not in INCONCLUSIVE]
    # nothing answered and every failure is auth/timeout: that is the key or
    # the network, not the models, so this run drops nothing
    outage = bool(conclusive) and LIVE not in conclusive and all(c in OUTAGE for c in conclusive)
    stats["outage"] = outage
    if outage:
        complete = False
    with _lock:
        ver, probes, eps = load(VERIFIED), load(PROBES), load(ENDPOINTS)
        vmodels, dropped = ver["models"], ver["dropped"]
        covered = set(results)
        covered.update(e["catalog_id"] for e in results.values() if e.get("catalog_id"))
        seen_for = {}  # endpoint key -> models this run tied to it

        def note(state):
            if state == "added":
                stats["endpoints_added"] += 1
            elif state == "revived":
                stats["endpoints_revived"] += 1

        for mid, e in results.items():
            status = str(e.get("status") or "")
            _record_result_endpoints(eps, mid, e, status, at, seen_for, note, stats)
            if not probed:
                continue
            # --- probe history
            prev = probes["models"].get(mid) or probes["archived"].pop(mid, None) or {}
            hist = list(prev.get("history") or [])
            if status in ("SPEC_FOUND_NOT_PROBED", "NO_SPEC_FOUND"):
                if prev:
                    probes["models"][mid] = prev  # a plan-only entry never overwrites a real result
            else:
                if prev.get("status"):
                    hist.insert(0, _brief(prev, prev.get("sweep")))
                rec = {k: v for k, v in e.items() if k not in ("tried", "spec_plans")}
                if rec.get("reason"):
                    rec["reason"] = redact(rec["reason"])
                rec["sweep"] = e.get("checked_by") or sweep
                rec["history"] = hist[:PROBE_HISTORY]
                probes["models"][mid] = rec
            # --- verified membership
            if status in INCONCLUSIVE or (outage and status in OUTAGE):
                if mid in vmodels and status != "SPEC_FOUND_NOT_PROBED" and status != "NO_SPEC_FOUND":
                    vmodels[mid]["last_check"] = {"status": status, "at": e.get("checked_at") or at}
                if mid in vmodels:
                    stats["verified_kept"] += 1
                continue
            if status == LIVE:
                if mid not in vmodels:
                    stats["verified_added"].append(mid)
                prior = vmodels.get(mid) or dropped.get(mid)
                vmodels[mid] = _verified_record(e, sweep, prior, at)
                dropped.pop(mid, None)
                if e.get("catalog_id") and e["catalog_id"] in vmodels and e["catalog_id"] != mid:
                    vmodels.pop(e["catalog_id"])  # now keyed by the API id
            else:
                for vid in [v for v, r in vmodels.items() if v == mid or r.get("catalog_id") == mid]:
                    _drop(ver, vid, f"failed {sweep}: {status}", e, at)
                    stats["verified_dropped"].append(vid)

        if complete:
            from . import spec
            if known is None:
                known = set(load(DISCOVERED)["models"]) | set(endpoint_models())
            alive = {spec.match_key(m) for m in set(known) | covered}

            def gone(mid, rec=None):
                return spec.match_key(mid) not in alive and \
                    spec.match_key((rec or {}).get("catalog_id") or mid) not in alive

            for vid in list(vmodels):
                if gone(vid, vmodels[vid]):
                    _drop(ver, vid, f"no longer discovered or swept (full {sweep})", None, at)
                    stats["verified_dropped"].append(vid)
            for mid in list(probes["models"]):
                if gone(mid, probes["models"][mid]):
                    probes["archived"][mid] = dict(probes["models"].pop(mid), archived_at=at,
                                                   archived_reason=f"no longer discovered (full {sweep})")
            live_urls = {r.get("url") for r in vmodels.values()}
            stats["endpoints_staled"] = _stale_unused(eps, alive, live_urls, at, sweep)

        ver["last_sync"] = {"at": at, "sweep": sweep, "complete": bool(complete), "models_covered": len(covered),
                            "added": len(stats["verified_added"]), "dropped": len(stats["verified_dropped"])}
        eps["last_sync"] = {"at": at, "sweep": sweep, "complete": bool(complete),
                            "added": stats["endpoints_added"], "revived": stats["endpoints_revived"],
                            "staled": stats["endpoints_staled"]}
        ver["models"] = dict(sorted(vmodels.items(), key=lambda kv: kv[0].lower()))
        probes["models"] = dict(sorted(probes["models"].items(), key=lambda kv: kv[0].lower()))
        save(VERIFIED, ver)
        save(PROBES, probes)
        save(ENDPOINTS, eps)
    return stats


def _record_result_endpoints(eps, mid, e, status, at, seen_for, note, stats):
    """Endpoints one result names: every spec plan, every probed URL that
    exists (not 404/410), the result's own URL. A working spec route also
    becomes a router override."""
    def tie(url, method):
        seen_for.setdefault(endpoint_key(url, method), set()).add(mid)

    for p in e.get("spec_plans") or []:
        note(record_endpoint(eps, p.get("url"), p.get("method", "POST"), p.get("content_type"), p.get("kind"),
                             p.get("function_id"), model=mid, source="spec", at=at))
        tie(p.get("url"), p.get("method"))
    for t in e.get("tried") or []:
        url = t.get("url")
        key = endpoint_key(url, t.get("method"))
        known = key in eps["endpoints"] or key in eps["stale"]
        if not known and t.get("http_status") in (None, 404, 410):
            continue  # a guessed URL that does not exist is not an endpoint
        res = {"status": t.get("status"), "http_status": t.get("http_status"), "model": mid, "at": at}
        note(record_endpoint(eps, url, t.get("method", "POST"), t.get("content_type"), t.get("kind"),
                             t.get("function_id"), source="probe", result=res, at=at))
    url = e.get("url")
    if not url:
        return
    from_spec = e.get("route_source") in ("page", "docs")
    works = status in (LIVE, "NEEDS_DIFFERENT_PAYLOAD")
    if not (works or from_spec or status == "GRPC_NVCF_ONLY"):
        return
    res = None
    if status not in INCONCLUSIVE and status != "GRPC_NVCF_ONLY":
        res = {"status": status, "http_status": e.get("http_status"), "model": mid, "at": at,
               "latency_sec": e.get("latency_sec")}
    src = "spec" if from_spec else ("probe" if status == "GRPC_NVCF_ONLY" else "sweep")
    note(record_endpoint(eps, url, e.get("method", "POST"), e.get("content_type"), e.get("kind"),
                         e.get("function_id"), model=mid, source=src, result=res, at=at))
    tie(url, e.get("method"))
    if works and from_spec:
        ov = eps["routing"].setdefault("explicit_model_overrides", {})
        new = {"url": url, "method": e.get("method", "POST"), "kind": e.get("kind"),
               "content_type": e.get("content_type"), "source": "spec_sweep"}
        if e.get("function_id"):
            new["function_id"] = e["function_id"]
        if ov.get(mid) != new:
            ov[mid] = new
            stats["overrides"] += 1


def _drop(ver, vid, reason, result, at):
    rec = ver["models"].pop(vid)
    ver["dropped"][vid] = dict(rec, dropped_at=at, dropped_reason=redact(reason),
                               last_result=_brief(result, None) if result else None)


def _stale_unused(eps, alive, live_urls, at, sweep):
    """After a complete sweep, move an endpoint found by sweeps or specs to
    'stale' when no known model uses it any more (its models left
    discovery) or when this run probed it and it answered 404/410 with no
    verified model on it. Seed routes (registry, matrix, overrides) stay.
    The record keeps its models (unlinked ones in former_models) and comes
    back the moment anything sees it again."""
    from . import spec
    n = 0
    for key in list(eps["endpoints"]):
        rec = eps["endpoints"][key]
        if SEED_SOURCES & set(rec.get("sources") or []):
            continue
        models = rec.get("models") or []
        keep = [m for m in models if spec.match_key(m) in alive]
        lost = [m for m in models if m not in keep]
        if lost:
            rec["former_models"] = sorted(set(rec.get("former_models") or []) | set(lost), key=str.lower)
            rec["models"] = keep
        lr = rec.get("last_result") or {}
        gone = lr.get("at") == at and lr.get("http_status") in (404, 410) and rec["url"] not in live_urls
        reason = None
        if not keep and rec.get("last_seen") != at:
            reason = f"no known model uses it after the full {sweep}"
        elif gone:
            reason = f"answered {lr.get('http_status')} in the full {sweep}"
        if reason:
            rec["stale_since"] = at
            rec["stale_reason"] = reason
            eps["stale"][key] = eps["endpoints"].pop(key)
            n += 1
    return n


def probe_results():
    return dict(load(PROBES)["models"])


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------
def _bench_summary(report):
    s = {"timestamp": report.get("timestamp"), "coverage": report.get("coverage")}
    for track in ("embeddings", "vision", "reasoning", "voice", "other_smoke"):
        rows = report.get(track) or []
        ok = sum(1 for r in rows if isinstance(r, dict) and not r.get("error")
                 and (r.get("logic_pass", r.get("recall_pass", r.get("ok", True))) is not False))
        s[track] = {"rows": len(rows), "ok": ok}
    return s


def save_benchmark(report):
    """Write the latest run and push its summary onto the short history."""
    with _lock:
        doc = dict(report, schema=SCHEMA)
        _write(path(BENCHMARK), doc)
        hist = load(BENCH_HISTORY)
        runs = [r for r in hist["runs"] if r.get("timestamp") != report.get("timestamp")]
        hist["runs"] = ([_bench_summary(report)] + runs)[:BENCH_HISTORY_MAX]
        save(BENCH_HISTORY, hist)
    return path(BENCHMARK)


def latest_benchmark():
    b = load(BENCHMARK)
    return b if b.get("timestamp") else None


# ---------------------------------------------------------------------------
# Migration from the pre-3.1 files
# ---------------------------------------------------------------------------
LEGACY_ROOT_FILES = ("nvidia_endpoint_registry.json", "nvidia_endpoints_matrix.json", "nvidia_inventory.json",
                     "nvidia_catalog.json", "nvidia_verified_endpoints.json")
LEGACY_OUTPUT_FILES = ("spec_sweep_results.json", "benchmark_results.json", "leaderboard.json",
                       "entity_scores.json", "memory_store.json", "nvidia_playground_history.jsonl")


def legacy_files():
    """{relative name: absolute path} of pre-3.1 files still in place."""
    root = project_root()
    found = {}
    for n in LEGACY_ROOT_FILES:
        p = os.path.join(root, n)
        if os.path.isfile(p):
            found[n] = p
    for n in LEGACY_OUTPUT_FILES:
        p = os.path.join(root, "output", n)
        if os.path.isfile(p):
            found["output/" + n] = p
    return found


def _newer(a, b):
    """True when timestamp a is later than b (missing counts as oldest)."""
    return str(a or "") > str(b or "")


def migrate(log=None):
    """Build the stores from the pre-3.1 files, then move those files to
    data/legacy/<time>/. Merges into stores that already exist (newer data
    wins), so running it twice never loses anything. Returns a report."""
    found = legacy_files()
    if not found:
        return None
    log = log or (lambda *_: None)
    at = now()
    rep = {"at": at, "files": sorted(found), "counts": {}}
    with _lock:
        eps, disc = _load_raw(ENDPOINTS), _load_raw(DISCOVERED)
        ver, probes = _load_raw(VERIFIED), _load_raw(PROBES)
        L = {n: config.load_json(p, None) for n, p in found.items() if n.endswith(".json")}

        reg = L.get("nvidia_endpoint_registry.json")
        if isinstance(reg, dict):
            r = eps["routing"]
            for k, v in reg.items():
                if k == "explicit_model_overrides":
                    ov = r.setdefault(k, {})
                    for mid, o in (v or {}).items():
                        ov.setdefault(mid, o)
                elif isinstance(v, dict) and isinstance(r.get(k), dict):
                    for kk, vv in v.items():
                        r[k].setdefault(kk, vv)
                elif k not in r or k == "version":
                    r[k] = v
            rep["counts"]["overrides"] = len(r.get("explicit_model_overrides") or {})
        mat = L.get("nvidia_endpoints_matrix.json")
        if isinstance(mat, dict):
            have = {(c.get("url") or c.get("template"), c.get("kind")) for c in eps["candidate_routes"]}
            for c in mat.get("candidate_routes") or []:
                if (c.get("url") or c.get("template"), c.get("kind")) not in have:
                    eps["candidate_routes"].append(c)
            rep["counts"]["candidate_routes"] = len(eps["candidate_routes"])
        _seed_endpoints(eps, at)

        cat = L.get("nvidia_catalog.json")
        if isinstance(cat, dict) and isinstance(cat.get("models"), dict):
            stamp = cat.get("generated_at") or at
            for mid, e in cat["models"].items():
                if mid not in disc["models"]:
                    disc["models"][mid] = dict(e, first_seen=e.get("first_seen") or stamp,
                                               last_seen=e.get("last_seen") or stamp)
            if _newer(stamp, disc.get("generated_at")):
                for f in ("generated_at", "sources", "source_counts", "errors"):
                    if f in cat:
                        disc[f] = cat[f]
            rep["counts"]["catalog_models"] = len(cat["models"])
        inv = L.get("nvidia_inventory.json")
        if inv:
            from . import catalog
            ids = catalog.parse_key_models(inv)
            stamp = inv.get("updated_at") if isinstance(inv, dict) else None
            kl = disc["key_list"]
            if ids and (not kl.get("models") or _newer(stamp, kl.get("updated_at"))):
                disc["key_list"] = {"models": ids, "updated_at": stamp or at, "source": "key_cache"}
            from . import spec
            known = {spec.match_key(m) for m in disc["models"]}
            for mid in ids:
                if spec.match_key(mid) not in known:
                    pub, _, name = mid.partition("/")
                    disc["models"][mid] = {"id": mid, "publisher": pub, "name": name, "kind": None,
                                           "sources": ["key_cache"], "status": "active", "flags": [],
                                           "in_key_list": True, "first_seen": stamp or at,
                                           "last_seen": stamp or at}
            rep["counts"]["key_models"] = len(ids)
        if disc["models"]:
            _resummarize(disc)

        # verified file (all statuses) and the last spec sweep's full results
        merged = {}
        sw = L.get("output/spec_sweep_results.json")
        if isinstance(sw, dict) and isinstance(sw.get("results"), dict):
            # every spec endpoint the last spec sweep found, probed or not
            noop = lambda *_: None  # noqa: E731
            for mid, e in sw["results"].items():
                if isinstance(e, dict):
                    _record_result_endpoints(eps, mid, e, str(e.get("status") or ""), e.get("checked_at") or at,
                                             {}, noop, {"overrides": 0})
            if sw.get("probed"):
                merged.update(sw["results"])
        vf = L.get("nvidia_verified_endpoints.json")
        if isinstance(vf, dict):
            for mid, e in vf.items():
                if isinstance(e, dict) and (mid not in merged or _newer(e.get("checked_at"), merged[mid].get("checked_at"))):
                    merged[mid] = e
        live = 0
        for mid, e in merged.items():
            if not isinstance(e, dict):
                continue
            e = dict(e)
            st = str(e.get("status") or "")
            if st.upper() in ("LIVE_200", "200", "OK"):
                e["status"] = st = LIVE
            cur = probes["models"].get(mid)
            if cur is None or _newer(e.get("checked_at"), cur.get("checked_at")):
                rec = dict(e, sweep=e.get("checked_by") or "legacy", history=(cur or {}).get("history", []))
                probes["models"][mid] = rec
            if e.get("url") and st in (LIVE, "NEEDS_DIFFERENT_PAYLOAD"):
                record_endpoint(eps, e["url"], e.get("method", "POST"), e.get("content_type"), e.get("kind"),
                                e.get("function_id"), model=mid,
                                source="spec" if e.get("route_source") in ("page", "docs") else "sweep",
                                result={"status": st, "http_status": e.get("http_status"), "model": mid,
                                        "at": e.get("checked_at")}, at=e.get("checked_at") or at)
            vcur = ver["models"].get(mid)
            if st == LIVE:
                if vcur is None or _newer(e.get("checked_at"), vcur.get("verified_at")):
                    ver["models"][mid] = _verified_record(e, e.get("checked_by") or "legacy", vcur, at)
                    ver["dropped"].pop(mid, None)
                live += 1
            elif st not in INCONCLUSIVE and vcur and _newer(e.get("checked_at"), vcur.get("verified_at")):
                _drop(ver, mid, f"legacy result: {st}", e, at)
        rep["counts"]["probe_results"] = len(merged)
        rep["counts"]["verified_200"] = live

        save(ENDPOINTS, eps)
        save(DISCOVERED, disc)
        save(VERIFIED, ver)
        save(PROBES, probes)

        bench = L.get("output/benchmark_results.json")
        if isinstance(bench, dict) and bench:
            cur = _load_raw(BENCHMARK)
            if _newer(bench.get("timestamp") or at, cur.get("timestamp")):
                save_benchmark(dict(bench, timestamp=bench.get("timestamp") or at))
            else:
                hist = _load_raw(BENCH_HISTORY)
                hist["runs"] = (hist["runs"] + [_bench_summary(bench)])[:BENCH_HISTORY_MAX]
                save(BENCH_HISTORY, hist)
            rep["counts"]["benchmark"] = 1
        for old, new in (("output/leaderboard.json", LEADERBOARD), ("output/entity_scores.json", ENTITY_SCORES)):
            v = L.get(old)
            if v and not _load_raw(new):
                _write(path(new), v)
        mem = L.get("output/memory_store.json")
        if isinstance(mem, list) and mem:
            cur = _load_raw(MEMORY)
            ids = {r.get("id") for r in cur if isinstance(r, dict)}
            cur += [r for r in mem if isinstance(r, dict) and (r.get("id") is None or r.get("id") not in ids)]
            _write(path(MEMORY), cur)
            rep["counts"]["memories"] = len(mem)
        hp = found.get("output/nvidia_playground_history.jsonl")
        if hp:
            with open(hp, "r", encoding="utf-8", errors="replace") as src, \
                    open(path(TEST_HISTORY), "a", encoding="utf-8") as dst:
                for line in src:
                    if line.strip():
                        dst.write(redact(line.rstrip("\n")) + "\n")

        # back up, then clear the old files from where the tools looked
        dest = os.path.join(data_dir(), LEGACY_DIR, time.strftime("%Y%m%d-%H%M%S"))
        n = 1
        while os.path.exists(dest):
            n += 1
            dest = os.path.join(data_dir(), LEGACY_DIR, time.strftime("%Y%m%d-%H%M%S") + f"-{n}")
        for rel, p in found.items():
            target = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(p, target)
        rep["backup"] = dest
        logp = os.path.join(data_dir(), LEGACY_DIR, "migrations.json")
        runs = config.load_json(logp, []) or []
        runs.append(rep)
        config.save_json(logp, runs)
    log(f"Migrated {len(found)} pre-3.1 data file(s) into {data_dir()} (backup: {dest})")
    return rep


# ---------------------------------------------------------------------------
# Overview (python3 -m nimlab data)
# ---------------------------------------------------------------------------
def overview():
    ensure_all()
    eps, disc, ver, probes = load(ENDPOINTS), load(DISCOVERED), load(VERIFIED), load(PROBES)
    status = {}
    for e in disc["models"].values():
        status[e.get("status", "active")] = status.get(e.get("status", "active"), 0) + 1
    tested = set(probes["models"])
    failed = [m for m, e in probes["models"].items() if e.get("status") != LIVE and m not in ver["models"]]
    return {
        "data_dir": data_dir(),
        "endpoints": len(eps["endpoints"]), "endpoints_stale": len(eps["stale"]),
        "discovered": len(disc["models"]), "discovered_removed": len(disc["removed"]), "status": status,
        "key_list": len((disc.get("key_list") or {}).get("models") or []),
        "verified": len(ver["models"]), "verified_dropped": len(ver["dropped"]),
        "probed": len(tested), "failed": len(failed),
        "untested": len([m for m in disc["models"] if m not in tested and m not in ver["models"]]),
        "benchmark": (latest_benchmark() or {}).get("timestamp"),
        "benchmark_runs": len(load(BENCH_HISTORY)["runs"]),
        "memories": len(load(MEMORY)),
    }


def view(name):
    """Rows (id, detail) for one list, for `nimlab data show <name>`."""
    ensure_all()
    disc, ver, probes, eps = load(DISCOVERED), load(VERIFIED), load(PROBES), load(ENDPOINTS)
    if name == "endpoints":
        return [(r["url"], f"{r['method']:<5} {str(r.get('kind') or '-'):<12} models {len(r.get('models') or [])}  "
                           f"{','.join(r.get('sources') or [])}  last {str(r.get('last_seen'))[:10]}")
                for r in eps["endpoints"].values()]
    if name == "stale":
        return [(r["url"], f"stale since {str(r.get('stale_since'))[:10]}: {r.get('stale_reason')}")
                for r in eps["stale"].values()]
    if name == "discovered":
        return [(m, f"{str(e.get('kind')):<11} {e.get('status', 'active'):<10} {','.join(e.get('sources') or [])}")
                for m, e in disc["models"].items()]
    if name in ("retired", "deprecated", "unlisted"):
        return [(m, f"{e.get('kind')}  {e.get('deprecation_date') or ''}")
                for m, e in disc["models"].items() if e.get("status") == name]
    if name == "removed":
        return [(m, f"{str(e.get('removed_at'))[:10]} {e.get('removed_reason')}") for m, e in disc["removed"].items()]
    if name == "verified":
        return [(m, f"{str(e.get('kind')):<14} {e.get('latency_sec', '?')}s  {e.get('verified_by')} "
                    f"{str(e.get('verified_at'))[:10]}") for m, e in ver["models"].items()]
    if name == "dropped":
        return [(m, f"{str(e.get('dropped_at'))[:10]} {e.get('dropped_reason')}") for m, e in ver["dropped"].items()]
    if name == "failed":
        return [(m, f"{e.get('status')}  {str(e.get('reason') or '')[:70]}") for m, e in probes["models"].items()
                if e.get("status") != LIVE and m not in ver["models"]]
    if name == "untested":
        tested = set(probes["models"]) | set(ver["models"])
        return [(m, f"{e.get('kind')}  {e.get('status', 'active')}") for m, e in disc["models"].items()
                if m not in tested]
    if name == "key":
        return [(m, "") for m in (disc.get("key_list") or {}).get("models") or []]
    if name == "benchmarks":
        return [(r.get("timestamp") or "?", json.dumps({k: v for k, v in r.items() if k not in ("timestamp", "coverage")}))
                for r in load(BENCH_HISTORY)["runs"]]
    raise KeyError(name)


VIEWS = ("endpoints", "stale", "discovered", "retired", "deprecated", "unlisted", "removed", "key", "verified",
         "dropped", "failed", "untested", "benchmarks")
