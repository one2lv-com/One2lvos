"""Model discovery beyond the API key.

The key's /v1/models list is only part of the picture: build.nvidia.com
shows models (speech, CV, image generation, partner models, new releases)
that never appear there, and the key list still carries models the site has
retired. `discover` merges four public sources into one catalog:

  site     The NGC catalog search API that build.nvidia.com/models itself
           calls (api.ngc.nvidia.com/v2/search/catalog/resources/ENDPOINT,
           org qc69jvmznzxy). JSON, paginated, no key. The query is read
           from the live /models page when possible so it matches the site.
  sitemap  build.nvidia.com/sitemap.xml: a fallback list of model pages and
           the publisher for entries whose search record has none.
  docs     docs.api.nvidia.com/nim/reference sidebar: 'publisher / model.id'
           titles (exact API ids with dots), category, deprecated flag.
           Fallback: the docs sitemap's '*-infer' pages.
  key      The key's /v1/models, or the last synced nvidia_inventory.json.

The result is cached to nvidia_catalog.json and used by the spec sweep, the
playground's model list and the judge's candidate kinds.
"""

import json
import re
import urllib.parse
from datetime import date, datetime, timezone

from . import config, spec

SITE_ORG = "qc69jvmznzxy"
NGC_SEARCH = "https://api.ngc.nvidia.com/v2/search/catalog/resources/ENDPOINT"
BUILD = "https://build.nvidia.com"
MODELS_PAGE = BUILD + "/models"
BUILD_SITEMAP = BUILD + "/sitemap.xml"
DOCS_INDEX = "https://docs.api.nvidia.com/nim/reference/models-1"
DOCS_SITEMAP = "https://docs.api.nvidia.com/sitemap.xml"
DOCS_REF = "https://docs.api.nvidia.com/nim/reference/"

# First path segments of build.nvidia.com URLs that are not publishers.
NON_MODEL_SEGMENTS = {"playbooks", "explore", "blueprints", "skills", "spaces", "models", "settings",
                      "search", "docs", "_next", "api", "legal", "nim"}

DEFAULT_SEARCH_PARAMS = {
    "query": "*:*", "page": 0, "pageSize": 100, "groupBy": "resourceType",
    "filters": [{"field": "orgName", "value": SITE_ORG},
                {"field": "label", "value": '-("blueprint")'},
                {"field": "resourceType", "value": "endpoint"}],
    "orderBy": [{"field": "nameSort", "value": "ASC"}, {"field": "resourceId", "value": "ASC"}],
}

KINDS = ("chat", "vision", "embedding", "rerank", "ocr", "tts", "asr", "translation", "image_gen",
         "video", "cv", "safety", "biology", "simulation", "other")


# ---------------------------------------------------------------------------
# Kind classification
# ---------------------------------------------------------------------------
_NAME_RULES = [
    ("tts", ("magpie-tts", "tts", "fastpitch", "chatterbox", "studiovoice")),
    ("asr", ("parakeet", "canary", "whisper", "-asr", "conformer")),
    ("translation", ("translate", "nmt", "megatron-1b-nmt")),
    ("rerank", ("rerank", "reranking")),
    ("embedding", ("embed", "nvclip", "arctic-embed", "bge-")),
    ("ocr", ("ocr", "parse", "table-structure", "page-elements", "graphic-elements", "deplot", "docling")),
    ("safety", ("guard", "jailbreak", "safety", "content-safety", "topic-control")),
    ("image_gen", ("flux", "stable-diffusion", "sdxl", "qwen-image", "trellis", "image-edit")),
    ("video", ("cosmos-transfer", "cosmos-predict", "wan2", "lipsync", "vsr", "relighting", "eyecontact",
               "synthetic-video", "active-speaker", "bnr")),
    ("biology", ("evo2", "boltz", "diffdock", "proteinmpnn", "rfdiffusion", "rfd4", "openfold", "genmol",
                 "molmim", "msa-search", "esm", "alphafold")),
    ("simulation", ("fourcastnet", "corrdiff", "cuopt", "fluent", "star-ccm", "spectre", "fidelity", "aodt",
                    "kumo")),
    ("cv", ("body-pose", "bevformer", "sparsedrive", "streampetr", "grounding-dino", "detector")),
    ("vision", ("vision", "-vl", "vl-", "vlm", "vila", "neva", "paligemma", "kosmos", "fuyu", "omni",
                "cosmos-reason", "cosmos3-nano", "phi-4-multimodal", "llava")),
]

_LABEL_RULES = [
    ("tts", ("text-to-speech", "tts")),
    ("asr", ("asr", "automatic speech recognition", "speech-to-text")),
    ("translation", ("neural machine translation", "translation", "automatic speech translation")),
    ("ocr", ("table extraction", "ocr", "document")),
    ("rerank", ("reranking", "rerank")),
    ("embedding", ("embedding", "embeddings")),
    ("image_gen", ("text-to-image", "image editing", "image generation", "text-to-3d")),
    ("video", ("video", "broadcast")),
    ("biology", ("biology", "chemistry", "dna generation", "protein", "drug discovery")),
    ("simulation", ("aerodynamics", "climate", "weather", "route optimization", "simulation")),
    ("cv", ("object detection", "pose", "autonomous vehicles")),
    ("vision", ("multimodal", "vision", "image-to-text", "visual question answering")),
    ("chat", ("chat", "reasoning", "code generation", "agentic coding", "long context")),
]

_DOCS_CATEGORY = {"large language models": "chat", "retrieval": "embedding", "visual models": "vision",
                  "multimodal": "vision", "healthcare": "biology", "route optimization": "simulation",
                  "climate simulation": "simulation", "speech": "asr"}


def classify_kind(model_id, labels=None, docs_category=None, playground_type=None):
    """One kind from KINDS. Name rules first (most specific), then site
    labels, then the docs category; chat is the default."""
    m = (model_id or "").lower()
    for kind, hints in _NAME_RULES:
        if any(h in m for h in hints):
            if kind == "rerank" and "-vl" in m:
                return "rerank"
            return kind
    low = [str(x).lower() for x in labels or []]
    if playground_type == "chat" and not any("multimodal" in x for x in low):
        return "chat"
    for kind, hints in _LABEL_RULES:
        if any(h == x or h in x for x in low for h in hints):
            return kind
    cat = (docs_category or "").strip().lower()
    if cat in _DOCS_CATEGORY:
        if cat == "retrieval" and "rerank" in m:
            return "rerank"
        return _DOCS_CATEGORY[cat]
    return "chat"


# ---------------------------------------------------------------------------
# Source parsers (pure, unit-tested on saved pages)
# ---------------------------------------------------------------------------
def search_params_from_models_page(html):
    """The exact search query build.nvidia.com/models sends, or None."""
    stream = spec.rsc_text(html)
    m = re.search(r'"searchResult":\{"params":', stream)
    if not m:
        return None
    try:
        params, _ = json.JSONDecoder().raw_decode(stream, m.end())
    except ValueError:
        return None
    if not isinstance(params, dict) or not isinstance(params.get("filters"), list):
        return None
    keep = {k: params[k] for k in ("query", "filters", "orderBy", "groupBy", "queryFields") if k in params}
    keep["page"], keep["pageSize"] = 0, 100
    return keep


def search_url(params, page):
    q = dict(params)
    q["page"] = page
    q.pop("scoredSize", None)
    return NGC_SEARCH + "?q=" + urllib.parse.quote(json.dumps(q, separators=(",", ":")))


def parse_search_page(body):
    """(resources, page_total, result_total) from one NGC search response.
    The '_scored' group repeats resources from the other groups: skipped."""
    if not isinstance(body, dict):
        return [], 0, 0
    res = []
    for group in body.get("results") or []:
        if not isinstance(group, dict) or group.get("groupValue") == "_scored":
            continue
        res.extend(r for r in group.get("resources") or [] if isinstance(r, dict))
    return res, int(body.get("resultPageTotal") or 0), int(body.get("resultTotal") or 0)


def _labels(resource, key):
    for lab in resource.get("labels") or []:
        if isinstance(lab, dict) and lab.get("key") == key:
            return [str(v) for v in lab.get("values") or []], [str(v) for v in lab.get("unresolvedValues") or []]
    return [], []


def _attrs(resource):
    out = {}
    for a in resource.get("attributes") or []:
        if isinstance(a, dict) and "key" in a:
            out[a["key"]] = a.get("value")
    return out


def _us_date(value):
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", str(value or "").strip())
    if not m:
        return None
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"


def site_entry(resource, sitemap_publishers=None):
    """Catalog fields from one build.nvidia.com search record, or None."""
    slug = resource.get("name") or (resource.get("resourceId") or "").split("/")[-1]
    if not slug or re.match(r"^test[-_.]endpoint", slug, re.I):
        return None
    pubs, _ = _labels(resource, "publisher")
    publisher = (pubs[0] if pubs else (sitemap_publishers or {}).get(slug) or "nvidia").strip().lower()
    general, unresolved = _labels(resource, "general")
    attrs = _attrs(resource)
    display = (resource.get("displayName") or "").strip()
    if display and " " not in display and spec.match_key(display) == spec.match_key(slug):
        api_id = f"{publisher}/{display}"
    else:
        api_id = spec.slug_to_api_id(publisher, slug)
    pg_type = next((u.split("_", 1)[1] for u in unresolved if u.startswith("playgroundtype_")), None)
    return {
        "id": api_id,
        "publisher": publisher,
        "slug": slug,
        "display_name": display or slug,
        "page_url": spec.build_page_url(publisher, slug),
        "labels": [g for g in general if g],
        "playground_type": pg_type,
        # AVAILABLE tracks the downloadable NIM, not the hosted API: models with
        # AVAILABLE=false still serve millions of API calls a month.
        "downloadable": str(attrs.get("AVAILABLE", "")).lower() == "true" or "Download Available" in general,
        "preview": str(attrs.get("PREVIEW", "false")).lower() == "true",
        "deprecation_date": _us_date(attrs.get("DEPRECATION")),
        "free_endpoint": "Free Endpoint" in general,
        "api_invocations_last_month": _int(attrs.get("lastMonthApiInvocationCount")),
        "updated": resource.get("dateModified"),
    }


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_sitemap(xml):
    """[(publisher, slug)] model-page candidates from build.nvidia.com/sitemap.xml."""
    out, seen = [], set()
    for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml or ""):
        m = re.match(r"^https://build\.nvidia\.com/([^/?#]+)/([^/?#]+)/?$", loc)
        if not m or m.group(1).lower() in NON_MODEL_SEGMENTS:
            continue
        key = (m.group(1).lower(), m.group(2))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def parse_docs_sidebar(html):
    """[{id, docs_slug, infer_slug, category, deprecated, hidden}] from any
    docs.api.nvidia.com reference page (the sidebar ships in ssr-props)."""
    props = spec.docs_ssr_props(html)
    if not props or not isinstance(props.get("sidebar"), list):
        return []
    out = []
    for cat in props["sidebar"]:
        if not isinstance(cat, dict):
            continue
        category = cat.get("title") or ""
        for page in cat.get("pages") or []:
            if not isinstance(page, dict):
                continue
            title = page.get("title") or ""
            if " / " not in title:
                continue
            pub, name = [p.strip() for p in title.split(" / ", 1)]
            name = name.replace(" ", "")
            pub = _docs_publisher(pub, name, page.get("slug") or "")
            children = [c for c in page.get("pages") or [] if isinstance(c, dict)]
            infer = next((c.get("slug") for c in children if str(c.get("slug", "")).endswith("-infer")),
                         children[0].get("slug") if children else None)
            out.append({"id": f"{pub}/{name}", "docs_slug": page.get("slug"),
                        "infer_slug": infer, "category": category,
                        "deprecated": bool(page.get("deprecated")), "hidden": bool(page.get("hidden"))})
    return out


def _docs_publisher(title_pub, name, docs_slug):
    """Publisher id for a docs title: 'Moonshot AI' -> 'moonshotai' is read
    from the page slug ('moonshotai-kimi-k2_6') when it ends with the model."""
    slug = docs_slug.lower()
    plain = re.sub(r"[^a-z0-9-]+", "", title_pub.strip().lower().replace(" ", ""))
    if plain and slug.startswith(plain + "-"):
        return plain
    tail = "-" + name.replace(".", "_").lower()
    for suffix in (tail, "-" + name.lower(), "-" + name.replace(".", "-").lower()):
        if slug.endswith(suffix) and len(slug) > len(suffix):
            return slug[: -len(suffix)]
    return re.sub(r"\s+", "-", title_pub.strip().lower())


def parse_docs_sitemap(xml):
    """Fallback docs list: [docs_slug] of '/nim/reference/<slug>-infer' pages."""
    slugs = re.findall(r"<loc>\s*https://docs\.api\.nvidia\.com/nim/reference/([^<\s]+?)-infer\s*</loc>", xml or "")
    return sorted(set(slugs))


def parse_key_models(body):
    raw = body.get("data", body.get("models", [])) if isinstance(body, dict) else body
    out = []
    for item in raw or []:
        mid = item.get("id") or item.get("model") if isinstance(item, dict) else item
        if isinstance(mid, str) and mid.strip():
            out.append(mid.strip())
    return sorted(set(out), key=str.lower)


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------
def _today():
    return date.today().isoformat()


def merge(site=None, sitemap=None, docs=None, docs_sitemap=None, key_models=None, key_source=None,
          today=None):
    """Merge source lists into {match_key: entry}. Pure function.

    site:         [site_entry dicts]
    sitemap:      [(publisher, slug)]
    docs:         [parse_docs_sidebar dicts]
    docs_sitemap: [docs slugs]  (only used when docs is empty)
    key_models:   [api ids] or None when no key list is known
    """
    today = today or _today()
    cat = {}

    def entry_for(api_id):
        k = spec.match_key(api_id)
        if k not in cat:
            pub, _, name = api_id.partition("/")
            cat[k] = {"id": api_id, "publisher": pub, "name": name, "slug": None, "page_url": None,
                      "docs_url": None, "docs_infer_url": None, "display_name": None, "kind": None,
                      "sources": [], "labels": [], "playground_type": None, "docs_category": None,
                      "downloadable": None, "preview": None, "deprecation_date": None,
                      "docs_deprecated": False, "status": "active", "flags": []}
        return cat[k]

    def add_source(e, s):
        if s not in e["sources"]:
            e["sources"].append(s)

    for s in site or []:
        e = entry_for(s["id"])
        for f in ("publisher", "slug", "page_url", "display_name", "labels", "playground_type", "downloadable",
                  "preview", "deprecation_date", "free_endpoint", "api_invocations_last_month", "updated"):
            if s.get(f) is not None:
                e[f] = s[f]
        add_source(e, "site")

    for pub, slug in sitemap or []:
        k = spec.match_key(f"{pub}/{slug}")
        if k in cat:
            add_source(cat[k], "sitemap")
            cat[k]["slug"] = cat[k]["slug"] or slug
            cat[k]["page_url"] = cat[k]["page_url"] or spec.build_page_url(pub, slug)
        elif not site:
            # the search API failed: the sitemap alone stands in for the site
            # (it also lists blueprints, which the sweep will find have no API)
            e = entry_for(spec.slug_to_api_id(pub, slug))
            e["slug"], e["page_url"] = slug, spec.build_page_url(pub, slug)
            add_source(e, "sitemap")

    docs = docs or []
    if not docs and docs_sitemap:
        known = {spec.docs_reference_slug(e["id"]): e for e in cat.values()}
        for ds in docs_sitemap:
            e = known.get(ds)
            if e is None:
                continue  # a docs slug alone cannot be split into publisher/model reliably
            e["docs_url"] = DOCS_REF + ds
            e["docs_infer_url"] = DOCS_REF + ds + "-infer"
            add_source(e, "docs")
    for d in docs:
        e = entry_for(d["id"])
        if "site" not in e["sources"]:
            e["id"] = d["id"]
        elif e["id"] != d["id"] and spec.match_key(e["id"]) == spec.match_key(d["id"]) and "." in d["id"]:
            e["id"] = d["id"]  # docs titles keep the dots the slug lost
        e["docs_url"] = DOCS_REF + d["docs_slug"] if d.get("docs_slug") else e["docs_url"]
        e["docs_infer_url"] = DOCS_REF + d["infer_slug"] if d.get("infer_slug") else e["docs_infer_url"]
        e["docs_category"] = d.get("category")
        e["docs_deprecated"] = bool(d.get("deprecated"))
        add_source(e, "docs")

    key_set = None
    if key_models is not None:
        key_set = {spec.match_key(m): m for m in key_models}
        for k, mid in key_set.items():
            e = entry_for(mid)
            e["id"] = mid  # the key's id is the one the API accepts
            add_source(e, key_source or "key")

    for e in cat.values():
        e["publisher"], _, e["name"] = e["id"].partition("/")
        e["kind"] = classify_kind(e["id"], e.get("labels"), e.get("docs_category"), e.get("playground_type"))
        if not e.get("page_url"):
            pub, slug = spec.api_id_to_slug(e["id"])
            e["page_url_guess"] = spec.build_page_url(pub, slug)
        on_site = "site" in e["sources"] or ("sitemap" in e["sources"] and not site)
        flags = []
        dep = e.get("deprecation_date")
        # pages say "deprecated on D; no longer supported after D+1"
        if dep and dep < today:
            e["status"] = "retired"
        elif dep or e.get("docs_deprecated"):
            e["status"] = "deprecated"
        elif not on_site and (site or sitemap):
            e["status"] = "unlisted"
        if e["status"] in ("deprecated", "retired"):
            flags.append(e["status"])
        if key_set is not None:
            in_key = spec.match_key(e["id"]) in key_set
            e["in_key_list"] = in_key
            if on_site and not in_key:
                flags.append("on_site_not_in_key")
            if in_key and not on_site and (site or sitemap):
                flags.append("in_key_not_on_site")
        e["flags"] = flags
    return cat


def summarize(cat):
    entries = list(cat.values()) if isinstance(cat, dict) else list(cat)
    count = lambda pred: sum(1 for e in entries if pred(e))
    kinds = {}
    for e in entries:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return {
        "total": len(entries),
        "on_site": count(lambda e: "site" in e["sources"]),
        "in_docs": count(lambda e: "docs" in e["sources"]),
        "in_key_list": count(lambda e: e.get("in_key_list")),
        "on_site_not_in_key": count(lambda e: "on_site_not_in_key" in e["flags"]),
        "in_key_not_on_site": count(lambda e: "in_key_not_on_site" in e["flags"]),
        "deprecated": count(lambda e: e["status"] == "deprecated"),
        "retired": count(lambda e: e["status"] == "retired"),
        "unlisted": count(lambda e: e["status"] == "unlisted"),
        "kinds": dict(sorted(kinds.items(), key=lambda kv: -kv[1])),
    }


# ---------------------------------------------------------------------------
# Live discovery
# ---------------------------------------------------------------------------
def fetch_site(fetcher, log=print, use_cache=True):
    """Site models via the NGC search API, with the site's own query."""
    params = None
    page = fetcher.get(MODELS_PAGE, use_cache=use_cache)
    if page.ok:
        params = search_params_from_models_page(page.text)
    if not params:
        log("  (could not read the query from build.nvidia.com/models; using the built-in query)")
        params = dict(DEFAULT_SEARCH_PARAMS)
    resources, total, pages, n = [], 0, 1, 0
    while n < pages and n < 20:
        res = fetcher.get(search_url(params, n), use_cache=use_cache, accept="application/json")
        body = res.json() if res.ok else None
        if body is None:
            log(f"  site search page {n} failed: {res.error or res.status}")
            break
        items, pages, total = parse_search_page(body)
        resources.extend(items)
        n += 1
    seen, uniq = set(), []
    for r in resources:
        rid = r.get("resourceId")
        if rid and rid not in seen:
            seen.add(rid)
            uniq.append(r)
    return uniq, total


def load_key_models(api=None, inventory_path=None, log=print):
    """(models, source) from the live key, else the key list saved in
    data/models_discovered.json ('key_cache'). inventory_path reads a
    pre-3.1 nvidia_inventory.json instead of the store."""
    from . import store
    if api is not None and getattr(api, "api_key", None):
        res = api.list_models()
        models = getattr(res, "data", None) if getattr(res, "ok", False) else None
        if isinstance(models, list) and models:
            ids = parse_key_models({"data": models})
            store.save_key_list(ids, "key")
            return ids, "key"
        log("  key /v1/models failed; using the saved key list")
    if inventory_path:
        ids = parse_key_models(config.load_json(inventory_path, None) or [])
    else:
        ids = store.key_list()
    if ids:
        return ids, "key_cache"
    return None, None


def discover(fetcher, api=None, log=print, use_cache=True, inventory_path=None):
    """Fetch every source and return the catalog document (not yet saved)."""
    errors = {}
    log("Site catalog (the search build.nvidia.com/models uses)...")
    try:
        resources, site_total = fetch_site(fetcher, log, use_cache)
    except Exception as e:  # never let one source sink the others
        resources, site_total, errors["site"] = [], 0, str(e)
    log(f"  {len(resources)} records (site says {site_total})")

    log("build.nvidia.com sitemap...")
    sm = fetcher.get(BUILD_SITEMAP, use_cache=use_cache, accept="application/xml,text/xml")
    sitemap = parse_sitemap(sm.text) if sm.ok else []
    if not sm.ok:
        errors["sitemap"] = sm.error
    log(f"  {len(sitemap)} model-like pages")
    sitemap_pubs = {slug: pub for pub, slug in sitemap}
    site = [e for e in (site_entry(r, sitemap_pubs) for r in resources) if e]

    log("docs.api.nvidia.com reference index...")
    dp = fetcher.get(DOCS_INDEX, use_cache=use_cache)
    docs = parse_docs_sidebar(dp.text) if dp.ok else []
    docs_sm = []
    if not docs:
        errors["docs"] = dp.error or "sidebar not found"
        ds = fetcher.get(DOCS_SITEMAP, use_cache=use_cache, accept="application/xml,text/xml")
        docs_sm = parse_docs_sitemap(ds.text) if ds.ok else []
    log(f"  {len(docs) or len(docs_sm)} documented models")

    key_models, key_src = load_key_models(api, inventory_path, log)
    log(f"Key list: {len(key_models) if key_models else 0} models ({key_src or 'none available'})")

    if site_total and len(resources) < site_total:
        errors.setdefault("site", f"partial: {len(resources)} of {site_total} records")
    cat = merge(site, sitemap, docs, docs_sm, key_models, key_src)
    # sources this run read completely: only these may remove models in the
    # sync (nimlab.store.sync_discovered). Cached pages count as read; an
    # --offline run (use_cache only) removes nothing.
    covered = []
    if site and "site" not in errors:
        covered.append("site")
    if sitemap and "sitemap" not in errors:
        covered.append("sitemap")
    if docs:
        covered.append("docs")
    if key_src == "key":
        covered.append("key")
    doc = {
        "covered_sources": covered,
        "generated_at": config.timestamp(),
        "sources": {"site": NGC_SEARCH + f" (org {SITE_ORG})", "sitemap": BUILD_SITEMAP,
                    "docs": DOCS_INDEX, "key": key_src},
        "source_counts": {"site": len(site), "site_reported_total": site_total, "sitemap": len(sitemap),
                          "docs": len(docs) or len(docs_sm), "key": len(key_models or [])},
        "errors": errors,
        "summary": summarize(cat),
        "models": dict(sorted(((e["id"], e) for e in cat.values()), key=lambda kv: kv[0].lower())),
    }
    return doc


# ---------------------------------------------------------------------------
# Cache access for the other tools
# ---------------------------------------------------------------------------
def load_catalog(path=None):
    """The discovered-models document (data/models_discovered.json), or None
    before the first discovery. path reads another catalog-shaped file."""
    if path is None:
        from . import store
        return store.discovered()
    data = config.load_json(path, None)
    return data if isinstance(data, dict) and isinstance(data.get("models"), dict) else None


def save_catalog(doc, offline=False):
    """Sync a fresh discovery into data/models_discovered.json: new models
    are added, models the covered sources no longer list are moved to
    'removed'. Returns the sync stats."""
    from . import store
    covered = [] if offline else doc.get("covered_sources") or []
    return store.sync_discovered(doc, covered)


def catalog_age_days(doc):
    try:
        ts = datetime.fromisoformat(doc["generated_at"])
        return (datetime.now(timezone.utc) - ts).total_seconds() / 86400
    except (KeyError, TypeError, ValueError):
        return None


def model_ids(doc=None, include_retired=False, include_unlisted=True, kinds=None):
    """Model ids from the cached catalog for sweeps and pickers."""
    doc = doc if doc is not None else load_catalog()
    if not doc:
        return []
    out = []
    for mid, e in doc["models"].items():
        if not include_retired and e.get("status") == "retired":
            continue
        if not include_unlisted and e.get("status") == "unlisted":
            continue
        if kinds and e.get("kind") not in kinds:
            continue
        out.append(mid)
    return sorted(out, key=str.lower)


def kind_of(model_id, doc=None):
    doc = doc if doc is not None else load_catalog()
    if not doc:
        return None
    e = doc["models"].get(model_id)
    if e is None:
        k = spec.match_key(model_id)
        e = next((v for v in doc["models"].values() if spec.match_key(v["id"]) == k), None)
    return e.get("kind") if e else None


def format_table(doc, flag=None, limit=None):
    rows = []
    for mid, e in doc["models"].items():
        if flag and flag not in e.get("flags", []) and e.get("status") != flag:
            continue
        src = ",".join(s.replace("key_cache", "key*") for s in e["sources"])
        fl = ",".join(e.get("flags") or [])
        rows.append(f"  {mid:<52} {e['kind']:<11} {e['status']:<11} {src:<22} {fl}")
    if limit:
        rows = rows[:limit]
    return "\n".join(rows)
