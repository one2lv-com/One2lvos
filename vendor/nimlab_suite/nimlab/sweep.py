"""Spec-driven endpoint sweep.

For each model: read its build.nvidia.com page (or docs.api.nvidia.com
reference) once, extract the embedded OpenAPI spec, derive the exact URL,
method and request shape, then probe that endpoint with the API key using a
minimal valid request. Route guessing is only a fallback for models with no
spec at all.

Phase 1 (plans) needs no key and is paced politely. Spec sources, in order:
  1. api.ngc.nvidia.com/v2/endpoints/qc69jvmznzxy/<slug>/spec: the JSON
     record build.nvidia.com renders each model page from (OpenAPI spec,
     NVCF function id, nvcfInferencePath, usage samples, deprecation notice).
     About 20-50 KB per model instead of ~1 MB of HTML.
  2. the build.nvidia.com page HTML (same spec embedded in the RSC stream),
     only when the spec API fails for a reason other than 404.
  3. the docs.api.nvidia.com '<publisher>-<slug>-infer' reference page.
Extracted plans are cached under output/cache/specs with a TTL (raw pages
are not kept). Phase 2 (probes) runs a few workers in parallel against
the API hosts.

Results go to nvidia_verified_endpoints.json (the file the router, fleet
table and judge read) and, for spec-derived routes, to
explicit_model_overrides in nvidia_endpoint_registry.json.
"""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

from . import catalog, config, spec
from .core import HttpClient, build_multipart, load_api_key, redact
from .router import NvidiaRouter

# Result classes ------------------------------------------------------------
LIVE = "LIVE_200"
PAYLOAD = "NEEDS_DIFFERENT_PAYLOAD"
AUTH = "AUTH_OR_ENTITLEMENT"
RETIRED = "RETIRED_OR_DEPRECATED"
GRPC = "GRPC_NVCF_ONLY"
SERVER = "TIMEOUT_OR_SERVER_ERROR"
RATE = "RATE_LIMITED"
NO_REST = "NO_WORKING_REST_ENDPOINT"
NO_API = "NO_HOSTED_API"
PLANNED = "SPEC_FOUND_NOT_PROBED"
NO_SPEC = "NO_SPEC_FOUND"

STATUSES = (LIVE, PAYLOAD, AUTH, RETIRED, GRPC, SERVER, RATE, NO_REST, NO_API, PLANNED, NO_SPEC)

# Router kinds used elsewhere in nimlab (judge / fleet / playground)
ROUTER_KIND = {"chat": "chat", "vision": "vision", "completions": "completions", "embeddings": "embeddings",
               "rerank": "rerank", "image_gen": "image_gen", "tts": "audio_tts", "asr": "audio_asr",
               "cv": "vision_task", "ocr": "document", "other": "other"}

SPEC_DIR = os.path.join("cache", "specs")

KIND_FROM_CATALOG = {"embedding": "embeddings", "ocr": "ocr", "cv": "cv", "vision": "cv", "image_gen": "image_gen",
                     "tts": "tts", "asr": "asr", "rerank": "rerank", "video": "cv"}


def spec_cache_dir():
    return config.output_path(SPEC_DIR)


def _safe_name(model_id):
    return re.sub(r"[^A-Za-z0-9._-]+", "__", model_id)[:150] + ".json"


# ---------------------------------------------------------------------------
# Phase 1: plans
# ---------------------------------------------------------------------------
class SpecResolver:
    """Finds and caches the endpoint plan for a model id.
    cache_dir: None for the default (output/cache/specs), "" for no cache."""

    def __init__(self, fetcher, catalog_doc=None, cache_dir=None, ttl_sec=72 * 3600, log=None):
        self.fetcher = fetcher
        self.catalog = catalog_doc or {"models": {}}
        self.cache_dir = cache_dir if cache_dir is not None else spec_cache_dir()
        self.ttl = ttl_sec
        self.log = log or (lambda m: None)

    def _entry(self, model_id):
        models = self.catalog.get("models", {})
        if model_id in models:
            return models[model_id]
        k = spec.match_key(model_id)
        return next((e for e in models.values() if spec.match_key(e.get("id", "")) == k), {})

    def _cached(self, model_id):
        if not self.cache_dir:
            return None
        try:
            with open(os.path.join(self.cache_dir, _safe_name(model_id)), "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return None
        if data.get("model_id") != model_id or time.time() - data.get("fetched_at", 0) > self.ttl:
            return None
        return data

    def _store(self, data):
        if not self.cache_dir:
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, _safe_name(data["model_id"]))
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(path + ".tmp", path)

    def page_urls(self, model_id):
        e = self._entry(model_id)
        urls = []
        if e.get("page_url"):
            urls.append(e["page_url"])
        publisher, slugs = spec.slug_candidates(model_id)
        for s in slugs:
            u = spec.build_page_url(publisher, s)
            if u not in urls:
                urls.append(u)
        # only try guesses when the site does not know the model
        return urls[:1] if e.get("page_url") else urls[:2]

    def slugs(self, model_id):
        e = self._entry(model_id)
        if e.get("slug"):
            return [e["slug"]]
        return spec.slug_candidates(model_id)[1][:2]

    def docs_urls(self, model_id):
        e = self._entry(model_id)
        urls = [e["docs_infer_url"]] if e.get("docs_infer_url") else []
        guess = catalog.DOCS_REF + spec.docs_reference_slug(model_id) + "-infer"
        if guess not in urls:
            urls.append(guess)
        return urls

    def resolve(self, model_id, use_cache=True):
        """Plan document for one model:
        {model_id, api_model_id, page_url, page_status, docs_url, deprecation,
         function_id, plans, notes, spec_source, fetched_at}"""
        if use_cache:
            hit = self._cached(model_id)
            if hit:
                return hit
        e = self._entry(model_id)
        doc = {"model_id": model_id, "api_model_id": None, "page_url": None, "page_status": None,
               "docs_url": None, "deprecation": None, "function_id": None, "plans": [], "notes": {},
               "spec_source": None, "catalog_kind": e.get("kind"), "catalog_status": e.get("status"),
               "fetched_at": time.time()}
        info = None
        ngc_gone = True  # every NGC spec lookup answered 404
        # 1) NGC endpoint spec JSON: the data build.nvidia.com renders its page from
        for slug in self.slugs(model_id):
            res = self.fetcher.get(spec.ngc_spec_url(slug), store=False, accept="application/json")
            if res.status != 404:
                ngc_gone = False
            if not res.ok:
                continue
            got = spec.extract_ngc_spec(res.text)
            if got["found"]:
                info = got
                doc["page_url"] = spec.build_page_url(model_id.split("/", 1)[0] if "/" in model_id else "nvidia", slug)
                doc["page_status"] = 200
                doc["spec_via"] = "ngc_spec"
                break
        if ngc_gone and not info:
            doc["page_status"] = 404
        # 2) the model page HTML (embedded spec in the RSC stream), only when the
        #    spec API itself failed: the page is rendered from the same record
        for url in ([] if info or ngc_gone else self.page_urls(model_id)):
            res = self.fetcher.get(url, store=False)
            doc["page_status"] = res.status
            if not res.ok:
                continue
            got = spec.extract_build_page(res.text)
            if got["found"]:
                info, doc["page_url"], doc["spec_via"] = got, url, "page_html"
                break
            if got["not_found"]:
                doc["page_status"] = 404
        if info:
            doc["deprecation"] = info.get("deprecation")
            doc["function_id"] = info.get("function_id")
            doc["docs_url"] = info.get("api_docs_url")
            plans, notes = spec.derive_plans(info, model_id, "page")
            for p in plans:  # a path the spec cannot place (e.g. /v1/infer) takes the catalog kind
                if p["kind"] == "other" and e.get("kind") in KIND_FROM_CATALOG:
                    p["kind"] = KIND_FROM_CATALOG[e["kind"]]
            if plans:
                doc["spec_source"] = "page"
            doc["plans"], doc["notes"] = plans, notes
        # 3) docs.api.nvidia.com reference, when neither had a usable spec
        if not doc["plans"] and not doc["notes"].get("grpc_only"):
            for url in self.docs_urls(model_id):
                res = self.fetcher.get(url, store=False)
                if not res.ok:
                    continue
                got = spec.extract_docs_page(res.text)
                if got["found"]:
                    merged = dict(info or {}, openapi=got["openapi"], found=True)
                    plans, notes = spec.derive_plans(merged, model_id, "docs")
                    if plans:
                        doc["plans"], doc["notes"], doc["spec_source"] = plans, notes, "docs"
                        doc["docs_url"] = url
                        break
        doc["api_model_id"] = next((p["model"] for p in doc["plans"] if p.get("model")), None)
        self._store(doc)
        return doc


# ---------------------------------------------------------------------------
# Phase 2: probes and classification
# ---------------------------------------------------------------------------
_ENTITLEMENT = re.compile(r"not found for account|not entitled|no access|forbidden|unauthori[sz]ed|"
                          r"authentication|authorization failed|invalid api key|expired", re.I)
_RETIRED_TEXT = re.compile(r"deprecated|retired|end of life|no longer (available|supported)|sunset", re.I)


def classify(status, error_kind=None, body_text="", deprecated=False, retired=False):
    """(result_class, reason) for one probe outcome."""
    hint = spec.error_hint(body_text) if body_text else ""
    if error_kind in ("timeout", "network") or status is None:
        return SERVER, f"{error_kind or 'no response'}"
    if 200 <= status < 300:
        return LIVE, "202 accepted (NVCF async)" if status == 202 else ""
    if status in (400, 405, 415, 422):
        return PAYLOAD, hint or f"HTTP {status}"
    if status in (401, 403):
        return AUTH, hint or f"HTTP {status}"
    if status in (404, 410):
        if retired or deprecated or _RETIRED_TEXT.search(body_text or ""):
            return RETIRED, hint or f"HTTP {status}"
        if "not found for account" in (body_text or "").lower():
            return AUTH, hint
        return RETIRED, hint or f"HTTP {status}"
    if status == 429:
        return RATE, hint or "HTTP 429"
    if status >= 500:
        return SERVER, hint or f"HTTP {status}"
    return PAYLOAD, hint or f"HTTP {status}"


_RANK = {LIVE: 0, PAYLOAD: 1, RATE: 2, SERVER: 3, AUTH: 4, RETIRED: 5}


def best_outcome(outcomes):
    """Pick the most informative outcome from several probe attempts."""
    if not outcomes:
        return None
    return sorted(outcomes, key=lambda o: _RANK.get(o["status"], 9))[0]


class Prober:
    def __init__(self, api_key=None, http=None, timeout=20, router=None):
        self.api_key = api_key if api_key is not None else load_api_key()
        self.http = http or HttpClient(timeout=timeout, retries=1, backoff=2.0, max_bytes=2 * 1024 * 1024)
        self.timeout = timeout
        self._router = router

    @property
    def router(self):
        if self._router is None:
            try:
                self._router = NvidiaRouter()
            except (FileNotFoundError, ValueError):
                self._router = NvidiaRouter(registry={"gateways": {"integrate": spec.INTEGRATE,
                                                                   "ai_api": spec.AI_API}})
        return self._router

    def _headers(self, accept="application/json"):
        h = {"Accept": accept, "User-Agent": "nimlab-sweep/3"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _send(self, plan, body):
        url, method = plan["url"], plan.get("method", "POST")
        if method == "GET":
            return self.http.request("GET", url, None, self._headers(), self.timeout)
        if plan.get("content_type") == "multipart/form-data":
            data, ctype = build_multipart(spec.multipart_fields(plan))
            h = self._headers("application/json, audio/*")
            h["Content-Type"] = ctype
            if plan.get("function_id"):
                h["function-id"] = plan["function_id"]
            return self.http.request("POST", url, data, h, self.timeout)
        h = self._headers("application/json")
        h["Content-Type"] = "application/json"
        return self.http.request(method, url, json.dumps(body or {}).encode("utf-8"), h, self.timeout)

    def probe_plan(self, plan, deprecated=False, retired=False):
        """Probe one plan: schema-built body first, then the page example
        when the first one is rejected as a bad payload."""
        tries = [("schema", plan.get("body"))]
        if plan.get("alt_body") and plan.get("alt_body") != plan.get("body"):
            tries.append(("example", plan["alt_body"]))
        outcomes = []
        for label, body in tries:
            if body is None and plan.get("content_type") != "multipart/form-data" and plan.get("method") != "GET":
                continue
            res = self._send(plan, body)
            status, reason = classify(res.status, res.error_kind if not res.ok else None,
                                      res.text if not res.ok else "", deprecated, retired)
            outcomes.append({"status": status, "reason": reason, "http_status": res.status,
                             "latency_sec": res.latency, "payload": label,
                             "request_keys": sorted((body or {}).keys()) if isinstance(body, dict) else []})
            if status != PAYLOAD:
                break
        if plan.get("probe_get") and (not outcomes or outcomes[-1]["status"] == PAYLOAD):
            res = self.http.request("GET", plan["probe_get"], None, self._headers(), self.timeout)
            status, reason = classify(res.status, res.error_kind if not res.ok else None,
                                      res.text if not res.ok else "", deprecated, retired)
            if status == LIVE:
                reason = "function reachable (list_voices); synthesize payload rejected" if outcomes else reason
                status = PAYLOAD if outcomes else LIVE
            outcomes.append({"status": status, "reason": reason, "http_status": res.status,
                             "latency_sec": res.latency, "payload": "get", "request_keys": []})
        return best_outcome(outcomes) or {"status": NO_REST, "reason": "no request could be built",
                                          "http_status": None, "latency_sec": None, "payload": None,
                                          "request_keys": []}

    def guess_plans(self, model_id, catalog_kind=None):
        """Old-style route guesses for models with no spec (max 3)."""
        publisher, name = NvidiaRouter.parse_model(model_id)
        rk = {"embedding": "embeddings", "rerank": "rerank", "vision": "vision", "ocr": "retrieval",
              "image_gen": "genai", "cv": "cv"}.get(catalog_kind or "", "chat")
        guesses, seen = [], set()
        try:
            r = self.router.resolve(model_id, rk)
            if r.get("method") != "gRPC":
                guesses.append((r["url"], r["kind"]))
        except (KeyError, ValueError):
            pass
        integrate = spec.INTEGRATE
        if catalog_kind == "embedding":
            guesses.append((f"{integrate}/embeddings", "embeddings"))
        elif catalog_kind in ("cv", "ocr", "image_gen", "video", "biology", "simulation"):
            guesses.append((f"{spec.AI_API}/cv/{publisher}/{name}", "cv"))
        guesses.append((f"{integrate}/chat/completions", "chat"))
        out = []
        for url, kind in guesses:
            if url in seen:
                continue
            seen.add(url)
            k = {"embeddings": "embeddings", "vision": "vision"}.get(kind, "chat" if url.endswith("/chat/completions") else kind)
            body = spec.build_minimal_request({}, {}, "chat" if url.endswith("/chat/completions") else k, model_id)
            if k == "embeddings":
                body = spec.build_minimal_request({}, {}, "embeddings", model_id)
                body["input_type"] = "query"
            out.append({"url": url, "method": "POST", "content_type": "application/json",
                        "kind": "chat" if url.endswith("/chat/completions") else k, "model": model_id,
                        "body": body, "alt_body": None, "transport": "rest", "source": "guess",
                        "function_id": None, "path": None})
        return out[:3]


def _is_retired(plan_doc, today=None):
    dep = (plan_doc.get("deprecation") or {})
    today = today or time.strftime("%Y-%m-%d")
    ends = dep.get("support_ends") or dep.get("deprecated_on")
    return bool(ends and ends < today) or plan_doc.get("catalog_status") == "retired"


def _tried(plan, outcome):
    return {"url": plan.get("url"), "method": plan.get("method", "POST"), "content_type": plan.get("content_type"),
            "kind": ROUTER_KIND.get(plan.get("kind"), plan.get("kind")), "function_id": plan.get("function_id"),
            "status": outcome.get("status"), "http_status": outcome.get("http_status")}


def evaluate(plan_doc, prober=None, probe=True, today=None):
    """Verified-endpoint entry for one model from its plan document."""
    deprecated = bool(plan_doc.get("deprecation")) or plan_doc.get("catalog_status") == "deprecated"
    retired = _is_retired(plan_doc, today)
    plans = plan_doc.get("plans") or []
    notes = plan_doc.get("notes") or {}
    base = {"checked_at": config.timestamp(), "page_url": plan_doc.get("page_url"),
            "docs_url": plan_doc.get("docs_url"), "spec_source": plan_doc.get("spec_source"),
            "catalog_kind": plan_doc.get("catalog_kind"), "deprecation": plan_doc.get("deprecation"),
            "function_id": plan_doc.get("function_id"), "api_model_id": plan_doc.get("api_model_id")}
    # every endpoint the spec names and every URL probed: the endpoint
    # registry (nimlab.store) records them, the verified list does not
    spec_plans = [{k: p.get(k) for k in ("url", "method", "content_type", "kind", "function_id") if p.get(k)}
                  for p in plans if p.get("url") and p.get("source") in ("page", "docs")]
    tried = []

    def entry(status, reason="", plan=None, outcome=None):
        e = dict(base, status=status, reason=redact(reason or ""))
        if spec_plans:
            e["spec_plans"] = spec_plans
        if tried:
            e["tried"] = list(tried)
        if plan:
            e.update({"url": plan["url"], "method": plan.get("method", "POST"),
                      "content_type": plan.get("content_type"), "kind": ROUTER_KIND.get(plan["kind"], plan["kind"]),
                      "transport": plan.get("transport"), "route_source": plan.get("source"),
                      "request_template": plan.get("body"), "function_id": plan.get("function_id") or base["function_id"]})
            if plan.get("model"):
                e["api_model_id"] = plan["model"]
        if outcome:
            e.update({"http_status": outcome.get("http_status"), "latency_sec": outcome.get("latency_sec"),
                      "payload_used": outcome.get("payload")})
        return {k: v for k, v in e.items() if v is not None}

    if notes.get("grpc_only"):
        return entry(GRPC, "page documents gRPC only (grpc.nvcf.nvidia.com:443)")
    if not plans:
        if retired:
            return entry(RETIRED, "retired per page/catalog")
        if plan_doc.get("page_status") == 404 and plan_doc.get("catalog_status") in (None, "unlisted"):
            if not probe:
                return entry(RETIRED, "page gone (404) and not listed on the site")
        if notes.get("no_hosted_api") and not probe:
            return entry(NO_API, "page has no hosted API (download/self-host only)")
        if not probe:
            return entry(NO_SPEC, "no spec on page or docs")
    end = (plan_doc.get("deprecation") or {}).get("support_ends")
    if not probe:
        if retired:
            return entry(RETIRED, f"page says support ended {end}" if end else "retired per catalog", plans[0])
        return entry(PLANNED, "", plans[0])
    if not prober or not prober.api_key:
        return entry(PLANNED, "no API key", plans[0] if plans else None)

    outcomes = []
    for plan in plans:
        o = prober.probe_plan(plan, deprecated, retired)
        outcomes.append((o, plan))
        tried.append(_tried(plan, o))
        if o["status"] == LIVE:
            break
    if not plans:
        for plan in prober.guess_plans(plan_doc["model_id"], plan_doc.get("catalog_kind")):
            o = prober.probe_plan(plan, deprecated, retired)
            outcomes.append((o, plan))
            tried.append(_tried(plan, o))
            if o["status"] == LIVE:
                break
        best = best_outcome([o for o, _ in outcomes])
        plan = next(p for o, p in outcomes if o is best) if best else None
        if best is None:
            return entry(NO_REST, "no spec and no route guess")
        if best["status"] == LIVE:
            return entry(LIVE, "route guessed (no spec found)", plan, best)
        if best["status"] == RETIRED or all(o["http_status"] in (404, 410) for o, _ in outcomes):
            return entry(RETIRED, "no spec; every guessed route 404/410" + (" (page gone)" if plan_doc.get("page_status") == 404 else ""),
                         None, best)
        if notes.get("no_hosted_api"):
            return entry(NO_API, "page has no hosted API; guesses failed: " + best["reason"], None, best)
        return entry(best["status"] if best["status"] in (AUTH, SERVER, RATE) else NO_REST,
                     "no spec; " + best["reason"], plan, best)
    best = best_outcome([o for o, _ in outcomes])
    plan = next(p for o, p in outcomes if o is best)
    reason = best["reason"]
    status = best["status"]
    if status == LIVE and retired:
        reason = (reason + "; " if reason else "") + f"still answers after its announced end ({end})"
    elif status == LIVE and deprecated:
        reason = (reason + "; " if reason else "") + f"live, deprecated (support ends {end})"
    elif retired and status in (PAYLOAD, AUTH, SERVER):
        reason = f"page says support ended {end}; probe: {status} {reason}".strip()
        status = RETIRED
    return entry(status, reason, plan, best)


# ---------------------------------------------------------------------------
# Writing results
# ---------------------------------------------------------------------------
def write_results(results, complete=False, sweep="spec_sweep", probed=True):
    """Fold the results into the data stores (nimlab.store.apply_results):
    probe history, the verified 200 list, the endpoint registry and router
    overrides. complete=True means the run covered the whole known model
    list, so verified models and endpoints it no longer found are moved to
    their archive sections. Returns the store's stats."""
    from . import store
    return store.apply_results(results, sweep=sweep, complete=complete, probed=probed)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def run(model_ids, resolver, prober=None, probe=True, workers=3, log=print, use_cache=True):
    """Resolve plans (sequential, paced by the fetcher), then probe in parallel."""
    plans = {}
    total = len(model_ids)
    for i, mid in enumerate(model_ids, 1):
        try:
            plans[mid] = resolver.resolve(mid, use_cache=use_cache)
        except Exception as e:  # one broken page must not stop the sweep
            plans[mid] = {"model_id": mid, "plans": [], "notes": {}, "error": redact(str(e))}
        p = plans[mid]
        src = p.get("spec_source") or ("grpc" if p.get("notes", {}).get("grpc_only") else "none")
        log(f"  [{i}/{total}] spec {src:<5} {mid}")
    results = {}

    def one(mid):
        try:
            return mid, evaluate(plans[mid], prober, probe)
        except Exception as e:
            return mid, {"status": SERVER, "reason": redact(f"probe crashed: {e}"), "checked_at": config.timestamp()}

    if probe and prober and prober.api_key:
        log(f"Probing {total} models with {workers} workers...")
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
        for mid, e in ex.map(one, model_ids):
            results[mid] = e
            if probe:
                log(f"  {e['status']:<24} {mid}  {e.get('reason', '')[:80]}")
    return results


def summarize(results):
    counts = {}
    for e in results.values():
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
