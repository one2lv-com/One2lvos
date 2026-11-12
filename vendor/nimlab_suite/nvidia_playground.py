#!/usr/bin/env python3
"""NVIDIA NIM interactive playground with task-specific payload presets.

Supports chat (streaming & non-streaming), embeddings, ranking, vision,
TTS/ASR audio, image gen, catalog syncing, model inspection, and
automated 200 health-check fallback sweep driven by an external JSON matrix.
Zero third-party dependencies.
"""

import base64
import json
import os
import sys
import time
from getpass import getpass

from nimlab import catalog, config
from nimlab import sweep as spec_sweep
from nimlab.api import NimClient, image_to_data_url, play_audio, save_wav
from nimlab.core import HttpClient, iter_sse, load_api_key, mask, redact, sanitize_key
from nimlab import picker, store
from nimlab.router import NvidiaRouter, classify_hint

ROUTER = NvidiaRouter()

# all lab data is in data/ and goes through nimlab.store
HISTORY = store.path(store.TEST_HISTORY)
BASE_URL = "https://integrate.api.nvidia.com/v1"
AI_API = "https://ai.api.nvidia.com/v1"

TINY_IMAGE_DATA_URI = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

API_KEY = ""
BASE = BASE_URL
TIMEOUT = 180
MODELS = []      # verified 200 OK models (data/models_verified.json)
ALL_MODELS = []  # every discovered model (data/models_discovered.json + key list)


def timestamp():
    return config.timestamp()


def http():
    """Shared client; rebuilt from the current TIMEOUT setting. One retry on 429/5xx."""
    return HttpClient(timeout=TIMEOUT, retries=1, backoff=1.5)


def auth():
    return {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}


def load_candidate_matrix():
    """Route templates the 200 sweep tries (data/endpoints.json)."""
    return store.candidate_routes()


def fetch_remote_catalog(base_url, api_key):
    url = f"{base_url.rstrip('/')}/models"
    res = HttpClient(timeout=30, retries=1).get(url, {"Authorization": f"Bearer {api_key}"})
    body = res.json() if res.ok else None
    if body is None:
        print(f"\nFailed to fetch models from {url}: {res.describe()}")
        return []
    raw = body.get("data", []) if isinstance(body, dict) else body
    models = sorted(
        {item.get("id", "").strip() for item in raw if isinstance(item, dict) and item.get("id")},
        key=str.lower
    )
    store.save_key_list(models, "key")
    print(f"\nSynced {len(models)} key models into {os.path.basename(store.path(store.DISCOVERED))}")
    return models


def load_models():
    """The full discovered list: every model in data/models_discovered.json
    (build.nvidia.com, docs and the key), plus the key list and verified
    models. With discovery_settings.playground_uses_catalog off, the key
    list only."""
    settings = config.load_cluster_config().get("discovery_settings", {}) or {}
    raw = list(store.key_list())
    if settings.get("playground_uses_catalog", True):
        doc = catalog.load_catalog()
        if doc:
            raw += list(doc["models"])
    raw += store.verified_ids()
    models, seen = [], set()
    for mid in raw:
        mid = str(mid or "").strip()
        if mid and mid not in seen:
            seen.add(mid)
            models.append(mid)
    return sorted(models, key=str.lower)


def live_models():
    """Models that passed the 200 test (data/models_verified.json)."""
    return store.verified_ids()


def model_statuses():
    """{model: 'retired'|'deprecated'} from discovery."""
    doc = catalog.load_catalog() or {}
    return {m: e.get("status") for m, e in (doc.get("models") or {}).items()
            if e.get("status") in ("retired", "deprecated")}


def pick_list(title="Which model list?"):
    """Ask once per menu entry: verified 200 OK (default) or all discovered."""
    models, scope = picker.choose_list(MODELS, ALL_MODELS, title=title)
    return models


def note_if_unverified(model):
    msg = picker.unverified_note(model, MODELS)
    if msg:
        print("\n" + msg)
        time.sleep(1.0)


def refresh_models():
    global MODELS, ALL_MODELS
    ALL_MODELS = load_models() or ALL_MODELS
    MODELS = live_models()


def save_history(record):
    line = redact(json.dumps(record, ensure_ascii=False))
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pause():
    input("\nPress Enter to continue...")


def header(title):
    os.system("clear" if os.name != "nt" else "cls")
    print("=" * 66)
    print("              NVIDIA NIM MODEL PLAYGROUND")
    print("=" * 66)
    print(title)
    print("-" * 66)


def choose_model(models=None):
    models = MODELS if models is None else models
    while True:
        header("MODEL SELECTION")
        print(f"Available models: {len(models)}" + ("" if models is MODELS else " (all discovered)"))
        print("\nSearch by model name, or enter a model number.")
        print("Enter q to return.\n")

        term = input("Search / selection: ").strip()
        if term.lower() == "q":
            return None

        if term.isdigit():
            index = int(term) - 1
            if 0 <= index < len(models):
                return models[index]

        matches = [m for m in models if term.lower() in m.lower()]
        if not matches:
            print("\nNo matching models.")
            pause()
            continue

        print()
        for i, model in enumerate(matches, 1):
            print(f"{i:>3}. [{classify_hint(model)}] {model}")

        selection = input("\nSelect result number, or Enter to search again: ").strip()
        if selection.isdigit():
            index = int(selection) - 1
            if 0 <= index < len(matches):
                return matches[index]


def list_models(models=None):
    models = MODELS if models is None else models
    tags = model_statuses() if models is not MODELS else {}
    while True:
        header("MODEL CATALOG")
        for i, model in enumerate(models, 1):
            tag = tags.get(model, "")
            print(f"{i:>3}. [{classify_hint(model):<15}] {model}" + (f"  [{tag}]" if tag else ""))

        print("\nEnter a model number to select it.")
        print("Enter s to search, q to return.")

        choice = input("\nSelection: ").strip().lower()
        if choice == "q":
            return None
        if choice == "s":
            model = choose_model(models)
            if model:
                return model
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(models):
                return models[index]


def endpoint_menu():
    options = [
        ("Chat Completions (Streaming)", "chat_stream"),
        ("Chat Completions (Buffered)", "chat"),
        ("Vision Chat (image + text)", "vision"),
        ("Audio TTS (Text-to-Speech)", "audio_tts"),
        ("Audio ASR (Speech-to-Text)", "audio_asr"),
        ("Embeddings", "embeddings"),
        ("Embeddings + input_type", "embeddings_typed"),
        ("Ranking (integrate /v1/ranking)", "ranking"),
        ("Rerank (ai.api retrieval path)", "rerank"),
        ("Image generation (genai)", "image_gen"),
        ("Custom endpoint + JSON", "custom"),
    ]

    print("\nAPI OPERATION / PAYLOAD PRESET")
    for i, (name, kind) in enumerate(options, 1):
        print(f"  {i:>2}. {name:<36} [kind: {kind}]")

    while True:
        choice = input("\nChoose operation: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                name, kind = options[idx]
                return name, kind
        print("Invalid selection.")


def resolve_image_ref(ref):
    url = image_to_data_url(ref)
    if url is None and (ref or "").strip():
        print(f"Not a readable file or URL: {ref}")
    return url


def default_path_for(kind, model):
    res = ROUTER.resolve(model, kind=kind)
    if res.get("is_nvcf"):
        print(f"\n[!] NOTICE: {res.get('hint')}")
    return res["url"]


def request_api_stream(url, payload):
    payload["stream"] = True
    headers = dict(auth(), **{"Content-Type": "application/json", "Accept": "text/event-stream"})
    start = time.monotonic()
    res = http().request("POST", url, json.dumps(payload).encode("utf-8"), headers, stream=True)
    if not res.ok:
        return {"http_code": res.status, "latency": res.latency, "body": None, "raw": redact(res.text or res.error or "")}
    collected_tokens = []
    print("\nMODEL OUTPUT (streaming):\n")
    resp = res.body
    try:
        for ev in iter_sse(resp):
            content = ev["data"].strip()
            if content == "[DONE]":
                break
            try:
                chunk = json.loads(content)
            except ValueError:
                continue
            delta = (chunk.get("choices") or [{}])[0].get("delta", {})
            tok = delta.get("content") or delta.get("reasoning_content") or ""
            if tok:
                sys.stdout.write(tok)
                sys.stdout.flush()
                collected_tokens.append(tok)
    except Exception as e:
        print(f"\n[stream interrupted: {redact(str(e))}]")
    finally:
        resp.close()
    print("\n")
    return {
        "http_code": res.status,
        "latency": round(time.monotonic() - start, 3),
        "body": {"choices": [{"message": {"content": "".join(collected_tokens)}}]},
        "raw": "".join(collected_tokens),
    }


def request_api(url, payload, timeout=None):
    res = http().post_json(url, payload, auth(), timeout=timeout or TIMEOUT)
    raw = res.text if res.status is not None else (res.error or "")
    return {"http_code": res.status, "latency": res.latency, "body": res.json(), "raw": redact(raw)}


def extract_text(kind, body):
    if not isinstance(body, dict):
        return None

    if kind in ("chat", "chat_stream", "vision"):
        try:
            msg = body["choices"][0]["message"]
            return msg.get("content") or msg.get("reasoning_content") or str(msg)
        except Exception:
            return None

    if kind in ("embeddings", "embeddings_typed"):
        try:
            return f"Embedding returned: {len(body['data'][0]['embedding'])} dimensions"
        except Exception:
            return None

    if kind in ("ranking", "rerank"):
        for key in ("rankings", "results", "data"):
            if key in body:
                return json.dumps(body[key], indent=2)[:4000]
        return json.dumps(body, indent=2)[:4000]

    if kind == "audio_asr":
        return body.get("text") or body.get("transcript") or json.dumps(body, indent=2)

    return json.dumps(body, indent=2)[:4000]


def print_response(result, kind):
    print("\n" + "=" * 66)
    print("                    API RESPONSE")
    print("=" * 66)
    code = result["http_code"]
    print(f"HTTP status: {code if code is not None else 'NO RESPONSE'}")
    print(f"Latency:     {result['latency']} seconds")

    body = result["body"]
    text = extract_text(kind, body)

    if 200 <= (code or 0) < 300:
        if text:
            print("\nMODEL OUTPUT:\n")
            print(text)
        else:
            print("\nRAW RESPONSE:\n")
            print(result["raw"][:10000])
    else:
        print("\nREQUEST ERROR (Details from NVIDIA):\n")
        print(result["raw"])
    print("\n" + "=" * 66)


def run_test(model, operation, url, payload, kind):
    print("\nMODEL:    ", model)
    print("OPERATION:", operation)
    print("ENDPOINT: ", url)
    print("\nSending request...")

    if kind == "chat_stream":
        result = request_api_stream(url, payload)
        if result["http_code"] != 200:
            print_response(result, kind)
    else:
        result = request_api(url, payload)
        print_response(result, kind)

    save_history({
        "timestamp": timestamp(),
        "model": model,
        "operation": operation,
        "kind": kind,
        "endpoint": url,
        "payload": payload,
        "http_code": result["http_code"],
        "latency_seconds": result["latency"],
        "response": result["body"],
        "raw_response": result["raw"][:12000],
    })
    return result


def build_payload(kind, model, **kwargs):
    prompt = kwargs.get("prompt", "")
    system_prompt = kwargs.get("system_prompt", "You are a helpful assistant.")
    max_tokens = kwargs.get("max_tokens", 512)
    temperature = kwargs.get("temperature", 0.7)
    image_url = kwargs.get("image_url")
    query = kwargs.get("query", prompt)
    passages = kwargs.get("passages") or []

    if kind in ("chat", "chat_stream"):
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt or "ping"},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": (kind == "chat_stream"),
        }

    if kind == "vision":
        if not image_url:
            image_url = TINY_IMAGE_DATA_URI
        content = [
            {"type": "text", "text": prompt or "Describe this image in one word."},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
        return {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

    if kind == "embeddings":
        return {
            "model": model,
            "input": [prompt or "probe"],
            "encoding_format": "float",
        }

    if kind == "embeddings_typed":
        return {
            "model": model,
            "input": [prompt or "probe"],
            "input_type": kwargs.get("input_type", "query"),
            "encoding_format": "float",
        }

    if kind in ("ranking", "rerank"):
        if not passages:
            passages = ["Test passage A", "Test passage B"]
        return {
            "model": model,
            "query": {"text": query or "probe"},
            "passages": [{"text": p} for p in passages],
        }

    if kind == "image_gen":
        return {
            "prompt": prompt or "a green leaf, white background",
            "cfg_scale": float(kwargs.get("cfg_scale", 3.5)),
            "steps": int(kwargs.get("steps", 10)),
        }

    return None


def _primary_kind(model):
    hint = classify_hint(model)
    if "Vision" in hint:
        return "vision"
    if "Audio TTS" in hint:
        return "audio_tts"
    if "Embeddings" in hint:
        return "embeddings"
    if "Ranking" in hint:
        return "ranking"
    if "Image Generation" in hint:
        return "image_gen"
    return "chat"


def _probe_payload(kind, model, test_image_url):
    """Smallest request the classic sweep sends for a route kind (None = can't build one)."""
    if kind == "vision":
        return {
            "model": model,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Describe image in 1 word."},
                {"type": "image_url", "image_url": {"url": test_image_url}},
            ]}],
            "max_tokens": 5, "temperature": 0.1, "stream": False,
        }
    if kind in ("chat", "chat_stream"):
        return {"model": model, "messages": [{"role": "user", "content": "1"}],
                "max_tokens": 1, "temperature": 0.1, "stream": False}
    if kind == "completions":
        return {"model": model, "prompt": "1", "max_tokens": 1}
    if kind == "embeddings":
        return {"model": model, "input": ["probe"], "encoding_format": "float"}
    if kind == "embeddings_typed":
        return {"model": model, "input": ["probe"], "input_type": "query", "encoding_format": "float"}
    if kind in ("ranking", "rerank"):
        return {"model": model, "query": {"text": "probe"}, "passages": [{"text": "sample"}]}
    if kind == "audio_tts":
        return {"model": model, "input": "test", "voice": "Magpie-Multilingual.EN-US.Aria", "response_format": "wav"}
    if kind == "image_gen":
        return {"prompt": "sample", "cfg_scale": 3.0, "steps": 5}
    return None


def registered_plans(model, test_image_url, candidate_routes, verified_entry=None):
    """Every endpoint the data stores know for this model, most specific first:
    1) its entry in models_verified.json, 2) the router rules in
    endpoints.json (explicit override, prefix rule or static route), 3) the
    default path for its kind, 4) every candidate route in endpoints.json."""
    pub, name = ROUTER.parse_model(model)
    primary = _primary_kind(model)
    raw = []
    v = verified_entry or {}
    if v.get("url"):
        raw.append({"url": v["url"], "kind": v.get("kind") or primary, "method": v.get("method", "POST"),
                    "content_type": v.get("content_type"), "function_id": v.get("function_id"),
                    "body": v.get("request_template"), "model": v.get("api_model_id") or model,
                    "source": "verified_json"})
    try:
        r = ROUTER.resolve(model, primary)
        if r.get("method") != "gRPC" and r.get("url"):
            raw.append({"url": r["url"], "kind": r.get("kind") or primary, "method": r.get("method", "POST"),
                        "content_type": r.get("content_type"), "function_id": r.get("function_id"),
                        "model": r.get("api_model_id") or model, "source": "registry_json"})
    except (KeyError, ValueError):
        pass
    raw.append({"url": default_path_for(primary, model), "kind": primary, "source": "default"})
    for entry in candidate_routes:
        if "url" in entry:
            url = entry["url"]
        elif "template" in entry:
            url = entry["template"].format(publisher=pub, name=name)
        else:
            continue
        raw.append({"url": url, "kind": entry.get("kind", "chat"), "method": entry.get("method", "POST"),
                    "source": "matrix_json"})

    plans, seen = [], set()
    for p in raw:
        url, kind = p.get("url"), p.get("kind")
        if not url or (kind, url) in seen:
            continue
        seen.add((kind, url))
        mdl = p.get("model") or model
        ctype = p.get("content_type") or "application/json"
        body = p.get("body")
        if ctype == "multipart/form-data":
            # NVCF speech: the prober builds the form; it keys on tts / asr
            kind = "asr" if ("asr" in str(kind) or "transcri" in url) else "tts"
        elif body is None and p.get("method", "POST") != "GET":
            body = _probe_payload(kind, mdl, test_image_url)
            if body is None:
                continue
        plans.append({"url": url, "method": p.get("method", "POST"), "content_type": ctype, "kind": kind,
                      "model": mdl, "body": body, "alt_body": None, "transport": "rest",
                      "source": p["source"], "function_id": p.get("function_id"), "path": None})
    return plans


def _entry_from(status, reason, plan=None, outcome=None):
    e = {"status": status, "reason": redact(reason or ""), "checked_at": config.timestamp(),
         "checked_by": "200_sweep"}
    if plan:
        e.update({"url": plan["url"], "method": plan.get("method", "POST"), "kind": plan["kind"],
                  "content_type": plan.get("content_type"), "route_source": plan.get("source"),
                  "request_template": plan.get("body"), "function_id": plan.get("function_id")})
        if plan.get("model"):
            e["api_model_id"] = plan["model"]
    if outcome:
        e.update({"http_status": outcome.get("http_status"), "latency_sec": outcome.get("latency_sec")})
    return {k: v for k, v in e.items() if v is not None}


def probe_single_model(model, test_image_url, candidate_routes, prober, resolver=None, verified_entry=None):
    """Stage 1: every registered endpoint from the JSON files.
    Stage 2 (only if none answered 200): the model's scraped spec, fetched
    from NGC / build.nvidia.com / docs when it is not cached yet."""
    outcomes = []
    for plan in registered_plans(model, test_image_url, candidate_routes, verified_entry):
        o = prober.probe_plan(plan)
        outcomes.append((o, plan))
        if o["status"] == spec_sweep.LIVE:
            return _with_tried(_entry_from(spec_sweep.LIVE, "registered endpoint", plan, o), outcomes)
    result = _probe_stage2(model, outcomes, resolver, prober)
    return _with_tried(result, outcomes)


def _with_tried(entry, outcomes):
    """Attach the URLs stage 1 probed, so the endpoint registry records any
    that exist (anything that did not answer 404/410)."""
    tried = list(entry.get("tried") or [])
    for o, p in outcomes:
        tried.append({"url": p.get("url"), "method": p.get("method", "POST"), "content_type": p.get("content_type"),
                      "kind": p.get("kind"), "function_id": p.get("function_id"),
                      "status": o.get("status"), "http_status": o.get("http_status")})
    if tried:
        entry["tried"] = tried
    return entry


def _probe_stage2(model, outcomes, resolver, prober):

    doc = None
    if resolver is not None:
        try:
            doc = resolver.resolve(model)
        except Exception as e:  # one broken page must not stop the sweep
            doc = {"model_id": model, "plans": [], "notes": {}, "error": redact(str(e))}
    if doc and doc.get("plans"):
        e = spec_sweep.evaluate(doc, prober, probe=True)
        e["checked_by"] = "200_sweep"
        if e.get("status") == spec_sweep.LIVE:
            e["reason"] = ("registered endpoints failed; scraped spec works. " + e.get("reason", "")).strip()
        return e

    notes = (doc or {}).get("notes") or {}
    best = spec_sweep.best_outcome([o for o, _ in outcomes])
    plan = next((p for o, p in outcomes if o is best), None)
    if notes.get("grpc_only") or any(k in model.lower() for k in ("parakeet", "canary", "riva", "fastpitch")):
        return dict(_entry_from(spec_sweep.GRPC, "gRPC only (grpc.nvcf.nvidia.com:443)"),
                    url="grpc.nvcf.nvidia.com:443", kind="nvcf_grpc")
    if doc and spec_sweep._is_retired(doc):
        return _entry_from(spec_sweep.RETIRED, "retired per page/catalog", None, best)
    if notes.get("no_hosted_api"):
        return _entry_from(spec_sweep.NO_API, "page has no hosted API (download/self-host only)", None, best)
    if best is None:
        return _entry_from(spec_sweep.NO_REST, "no registered endpoint could be built and no spec found")
    if doc and doc.get("page_status") == 404 and all(o["http_status"] in (404, 410) for o, _ in outcomes):
        return _entry_from(spec_sweep.RETIRED, "page gone and every registered endpoint 404/410", None, best)
    status = best["status"] if best["status"] in (spec_sweep.AUTH, spec_sweep.SERVER, spec_sweep.RATE,
                                                  spec_sweep.PAYLOAD) else spec_sweep.NO_REST
    src = "no spec found" if resolver is not None else "spec check off"
    return _entry_from(status, f"registered endpoints failed ({src}): {best.get('reason', '')}", plan, best)


def sweep_model_list():
    """Every discovered model (retired ones only when the discovery setting
    says so) plus every model the endpoint registry or verified list names."""
    from nimlab.cli import _discovery_settings, sweep_ids
    settings = _discovery_settings()
    ids = sweep_ids(catalog.load_catalog(), include_retired=settings.get("include_retired_in_sweep", False))
    seen = set(ids)
    for m in ALL_MODELS:  # key-only models when playground_uses_catalog is off
        if m not in seen:
            seen.add(m)
            ids.append(m)
    return ids


def _yes(prompt, default=True):
    ans = input(prompt).strip().lower()
    return default if not ans else ans.startswith("y")


def run_200_sweep(interactive=True):
    header("FULL CATALOG 200 HEALTH & FALLBACK SWEEP")
    candidate_routes = load_candidate_matrix()
    models = sweep_model_list()
    verified_before = store.verified_models()
    print(f"Total models to probe: {len(models)} (all discovered + endpoint registry + verified)")
    print(f"Loaded {len(candidate_routes)} candidate routes from {store.path(store.ENDPOINTS)}")

    test_image_url = TINY_IMAGE_DATA_URI
    use_spec, fetch_new = True, True
    if interactive:
        print("\nFor multimodal/vision models, please provide a test image.")
        print("Provide local image path, public URL, or press Enter for built-in test pixel.")
        raw_img = input("\nImage file / URL [default: 1x1 test gif]: ").strip()
        if raw_img:
            test_image_url = resolve_image_ref(raw_img)
            if not test_image_url:
                print("Could not resolve image file. Falling back to built-in test pixel.")
                test_image_url = TINY_IMAGE_DATA_URI
            else:
                print("Vision test image loaded successfully.")
        use_spec = _yes("\nWhen registered endpoints fail, check the model's scraped API spec? [Y/n]: ")
        if use_spec:
            fetch_new = _yes("Fetch specs that aren't cached yet? (paced, slower) [Y/n]: ")

    from types import SimpleNamespace
    from nimlab.cli import _discovery_settings, _fetcher
    settings = _discovery_settings()
    resolver = None
    if use_spec:
        resolver = spec_sweep.SpecResolver(_fetcher(SimpleNamespace(fast=False, offline=not fetch_new), settings),
                                           catalog.load_catalog(),
                                           ttl_sec=float(settings.get("spec_ttl_hours", 72)) * 3600)
    prober = spec_sweep.Prober(api_key=API_KEY, timeout=14)

    print("\nStage 1: every registered endpoint (verified JSON, registry, default, matrix).")
    if use_spec:
        print("Stage 2: if none answer 200, the model's scraped spec" + (" (fetched if needed)." if fetch_new else " (cache only)."))
    print("-" * 66)

    results = {}
    finished = False
    try:
        for idx, model in enumerate(models, 1):
            sys.stdout.write(f"[{idx:3}/{len(models)}] {model:<40} ")
            sys.stdout.flush()
            e = probe_single_model(model, test_image_url, candidate_routes, prober, resolver,
                                   verified_before.get(model))
            results[model] = e
            st = e["status"]
            if st == spec_sweep.LIVE:
                via = "spec" if e.get("route_source") not in ("verified_json", "registry_json", "default", "matrix_json") else e.get("route_source")
                print(f"-> 200 OK  ({e.get('kind')} @ {e.get('latency_sec')}s, via {via})")
            elif st == spec_sweep.GRPC:
                print("-> [NVCF gRPC ONLY]")
            else:
                print(f"-> [{st}] {e.get('reason', '')[:60]}")
        finished = True
    except KeyboardInterrupt:
        print(f"\n\nStopped after {len(results)} of {len(models)} models; saving what was tested "
              "(nothing it did not reach is dropped).")

    from nimlab.cli import print_sync
    sync = spec_sweep.write_results(results, complete=finished, sweep="200_sweep")
    counts = spec_sweep.summarize(results)
    from_spec = sum(1 for e in results.values() if e["status"] == spec_sweep.LIVE
                    and e.get("route_source") not in ("verified_json", "registry_json", "default", "matrix_json"))
    print("-" * 66)
    print("SWEEP SUMMARY:")
    for k, v in counts.items():
        print(f"  {k:<26} {v}")
    print(f"  Rescued by scraped spec   {from_spec}")
    print_sync(sync, probe=True, complete=finished)
    if interactive:
        pause()
    return results


def inspect_model_metadata(model):
    header("MODEL DEFINITION & METADATA")
    print("Target Model:", model)
    print("Detected Architecture:", classify_hint(model))
    url = f"{BASE.rstrip('/')}/models"

    print(f"\nQuerying {url} for model details...")
    res = HttpClient(timeout=15, retries=1).get(url, auth())
    data = res.json() if res.ok else None
    if isinstance(data, dict):
        matched = next((m for m in data.get("data", []) if isinstance(m, dict) and m.get("id") == model), None)
        if matched:
            print("\nDetailed NIM Specification:")
            print(json.dumps(matched, indent=2))
        else:
            print(f"\nModel ID '{model}' not explicitly detailed in standard data array.")
            print(f"Category: {classify_hint(model)}")
    else:
        print(f"\nCould not fetch remote metadata: {res.describe()}")
        print(f"Fallback Classification: {classify_hint(model)}")
    pause()


def generate_openai_snippet(model):
    header("OPENAI CLIENT DROP-IN")
    # The key is never printed: the snippet reads it from the environment.
    snippet = f"""import os
from openai import OpenAI

client = OpenAI(
    base_url="{BASE}",
    api_key=os.environ["NVIDIA_API_KEY"],
)

response = client.chat.completions.create(
    model="{model}",
    messages=[
        {{"role": "system", "content": "You are a helpful assistant."}},
        {{"role": "user", "content": "Hello!"}}
    ],
    temperature=0.7,
    max_tokens=512,
    stream=True
)

for chunk in response:
    content = chunk.choices[0].delta.content or ""
    print(content, end="", flush=True)
print()
"""
    print(snippet)
    pause()


def interactive_model_test(model):
    note_if_unverified(model)
    header("SINGLE MODEL TEST")
    print("Selected:", model)
    print("Category:", classify_hint(model))
    entry = (catalog.load_catalog() or {}).get("models", {}).get(model)
    if entry:
        print(f"Catalog:  kind {entry.get('kind')}, {entry.get('status')}, sources {', '.join(entry.get('sources', []))}")
    verified = store.verified_models().get(model) or store.probe_results().get(model)
    if isinstance(verified, dict) and verified.get("url"):
        print(f"Sweep:    {verified.get('status')} {verified.get('method', 'POST')} {verified['url']}")

    operation, kind = endpoint_menu()
    url = default_path_for(kind, model)

    if kind == "custom":
        url = input("Enter full URL: ").strip()
        print("Enter raw JSON payload (end with blank line):")
        lines = []
        while True:
            l = input()
            if not l.strip() and lines:
                break
            if l.strip():
                lines.append(l)
        try:
            payload = json.loads("\n".join(lines).replace("$MODEL", model))
        except Exception as e:
            print(f"Invalid JSON: {e}")
            pause()
            return
        run_test(model, operation, url, payload, kind)
        pause()
        return

    if kind == "audio_tts":
        text = input("\nText to synthesize: ").strip() or "Synthesizing voice through NVIDIA NIM speech architecture."
        voice = input("Voice name [Magpie-Multilingual.EN-US.Aria]: ").strip() or "Magpie-Multilingual.EN-US.Aria"
        if "magpie" in model.lower():
            # Magpie only answers on its NVCF function (multipart); use the shared client.
            client = NimClient(api_key=API_KEY)
            print(f"\nSending to NVCF Magpie endpoint ({client.tts_url()})...")
            r = client.tts(text, voice=voice)
            if r.ok:
                out_file = save_wav(r.data, "tts_output")
                print(f"\nSaved audio output to: {out_file} ({r.latency}s)")
                play_audio(out_file)
            else:
                print(f"\nTTS failed: {r.error}")
            save_history({"timestamp": timestamp(), "model": model, "operation": operation, "kind": kind,
                          "endpoint": client.tts_url(), "payload": {"text": text, "voice": voice},
                          "http_code": r.status, "latency_seconds": r.latency, "response": None,
                          "raw_response": "" if r.ok else (r.error or "")})
            pause()
            return
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "wav"
        }
        res = run_test(model, operation, url, payload, kind)
        if res.get("body") and "audio" in res["body"]:
            out_file = save_wav(base64.b64decode(res["body"]["audio"]), "tts_output")
            print(f"\nSaved audio output to: {out_file}")
        pause()
        return

    if kind == "audio_asr":
        audio_path = input("\nPath to audio file (.wav/.mp3): ").strip()
        if not os.path.isfile(audio_path):
            print("File not found.")
            pause()
            return
        with open(audio_path, "rb") as f:
            encoded_audio = base64.b64encode(f.read()).decode("ascii")
        payload = {
            "model": model,
            "audio": encoded_audio,
            "encoding": "LINEAR16",
        }
        run_test(model, operation, url, payload, kind)
        pause()
        return

    if kind in ("embeddings", "embeddings_typed"):
        text = input("\nText to embed: ").strip() or "NVIDIA endpoint connectivity test"
        input_type = input("input_type [query]: ").strip() or "query" if kind == "embeddings_typed" else None
        payload = {"model": model, "input": [text], "encoding_format": "float"}
        if input_type:
            payload["input_type"] = input_type
        run_test(model, operation, url, payload, kind)
        pause()
        return

    if kind in ("ranking", "rerank"):
        query = input("\nQuery text: ").strip() or "What is the memory bandwidth of H100?"
        print("Passages (one per line, empty line to finish; Enter twice for defaults):")
        passages = []
        while True:
            line = input()
            if not line.strip():
                break
            passages.append(line.strip())
        payload = build_payload(kind, model, query=query, passages=passages)
        run_test(model, operation, url, payload, kind)
        pause()
        return

    if kind == "image_gen":
        prompt = input("\nImage prompt: ").strip() or "a red cube on a white table, studio lighting"
        try:
            cfg = float(input("cfg_scale [3.5]: ").strip() or "3.5")
            steps = int(input("steps [20]: ").strip() or "20")
        except ValueError:
            print("Invalid cfg/steps.")
            pause()
            return
        payload = build_payload(kind, model, prompt=prompt, cfg_scale=cfg, steps=steps)
        run_test(model, operation, url, payload, kind)
        pause()
        return

    if kind == "vision":
        img_ref = input("\nImage file path or URL: ").strip()
        image_url = resolve_image_ref(img_ref)
        if not image_url:
            pause()
            return
        prompt = input("Prompt [Describe this image.]: ").strip() or "Describe this image."
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]}
            ],
            "max_tokens": 512,
            "stream": False,
        }
        run_test(model, operation, url, payload, kind)
        pause()
        return

    # Chat loop
    print("\nEnter your prompt (/exit to quit, /snippet for python code).")
    messages = []
    while True:
        prompt = input("\nYOU > ").strip()
        if not prompt:
            continue
        if prompt == "/exit":
            break
        if prompt == "/snippet":
            generate_openai_snippet(model)
            continue

        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": "You are a helpful assistant."}] + messages,
            "max_tokens": 1024,
            "temperature": 0.7,
            "stream": (kind == "chat_stream"),
        }
        res = run_test(model, operation, url, payload, kind)
        reply = extract_text("chat", res.get("body"))
        if reply:
            messages.append({"role": "assistant", "content": reply})


def compare_models(models=None):
    models = MODELS if models is None else models
    header("COMPARE MULTIPLE MODELS")
    print("Enter model IDs or numbers, comma-separated.\n")
    for i, model in enumerate(models, 1):
        print(f"{i:>3}. {model}")

    raw = input("\nModels: ").strip()
    if not raw:
        return

    selected = []
    for item in raw.split(","):
        item = item.strip()
        if item.isdigit():
            index = int(item) - 1
            if 0 <= index < len(models):
                selected.append(models[index])
        else:
            match = next((m for m in models if m.lower() == item.lower()), None)
            if match:
                selected.append(match)

    selected = list(dict.fromkeys(selected))
    if not selected:
        print("No valid models selected.")
        pause()
        return

    operation, kind = endpoint_menu()
    prompt = input("\nShared prompt: ").strip()
    if not prompt:
        return

    for model in selected:
        note_if_unverified(model)
        print("\n\n" + "#" * 66)
        print("MODEL:", model)
        print("#" * 66)
        url = default_path_for(kind, model)
        payload = build_payload(kind, model, prompt=prompt)
        run_test(model, operation, url, payload, kind)

    pause()


def show_history():
    header("RECENT TEST HISTORY")
    if not os.path.exists(HISTORY):
        print("No test history yet.")
        pause()
        return

    records = []
    with open(HISTORY, encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except Exception:
                pass

    for record in records[-30:]:
        print("-" * 66)
        print("Time:     ", record.get("timestamp"))
        print("Model:    ", record.get("model"))
        print("Operation:", record.get("operation"))
        print("Endpoint: ", record.get("endpoint"))
        print("HTTP:     ", record.get("http_code"))
        print("Latency:  ", record.get("latency_seconds"))
    pause()


def settings():
    global BASE, TIMEOUT
    while True:
        header("SETTINGS & INVENTORY SYNC")
        print("Current API base:", BASE)
        print("Timeout:         ", TIMEOUT, "seconds")
        print("Verified 200 OK: ", len(MODELS), f"(of {len(ALL_MODELS)} discovered)")
        print("\n1. Sync inventory from NIM API (/v1/models)")
        print("2. Change API base URL")
        print("3. Change timeout")
        print("4. Return")

        choice = input("\nSelection: ").strip()
        if choice == "1":
            new_models = fetch_remote_catalog(BASE, API_KEY)
            if new_models:
                refresh_models()
                print("Synced. New models are in the full discovered list; run the 200 sweep to verify them.")
            pause()
        elif choice == "2":
            val = input("New base URL: ").strip()
            if val.startswith(("https://", "http://")):
                BASE = val.rstrip("/")
                print("Updated.")
                pause()
        elif choice == "3":
            try:
                TIMEOUT = int(input("Timeout seconds: "))
            except ValueError:
                pass
        elif choice == "4":
            return


def main(argv=None):
    global API_KEY, MODELS, ALL_MODELS
    import argparse
    ap = argparse.ArgumentParser(description="NVIDIA NIM playground")
    ap.add_argument("--sweep", action="store_true", help="run the 200 health & fallback sweep and exit")
    args = ap.parse_args(argv)

    header("INITIALIZATION")
    API_KEY = load_api_key()
    if not API_KEY:
        API_KEY = sanitize_key(getpass("Paste NVIDIA API key (or set NVIDIA_API_KEY in shell): "))
    if not API_KEY:
        sys.exit("No API key supplied.")
    print(f"Using key {mask(API_KEY)}")

    ALL_MODELS = load_models()
    if not ALL_MODELS:
        print("\nNo discovered models yet. Fetching the key's model list from NVIDIA NIM...")
        ALL_MODELS = fetch_remote_catalog(BASE, API_KEY)
        if not ALL_MODELS:
            sys.exit("Failed to load or fetch model catalog.")
    MODELS = live_models()

    if args.sweep:
        run_200_sweep()
        return

    while True:
        header("MAIN MENU")
        print(f"Verified 200 OK: {len(MODELS)}   All discovered: {len(ALL_MODELS)}")
        if not MODELS:
            print("No model has passed the 200 test yet: run option 5 first.")
        print(f"API base:      {BASE}")
        print()
        print("  1. Browse model catalog & hints")
        print("  2. Search and select a model")
        print("  3. Test model (Chat, Vision, Audio TTS/ASR, Embeddings)")
        print("  4. Inspect model metadata / definition")
        print("  5. Run endpoint sweep (200 Health & Fallback, or spec-driven)")
        print("  6. Compare multiple models")
        print("  7. Generate OpenAI Python snippet")
        print("  8. View recent test history")
        print("  9. Settings & Sync /v1/models")
        print("  D. Discover models from build.nvidia.com + docs (beyond the key list)")
        print("  0. Exit")

        choice = input("\nChoose: ").strip()
        if choice == "1":
            m = list_models(pick_list())
            if m:
                interactive_model_test(m)
        elif choice == "2":
            m = choose_model(pick_list())
            if m:
                interactive_model_test(m)
        elif choice == "3":
            m = choose_model(pick_list())
            if m:
                interactive_model_test(m)
        elif choice == "4":
            m = choose_model(pick_list())
            if m:
                inspect_model_metadata(m)
        elif choice == "5":
            print("\n  1. 200 Health & Fallback Sweep (registered endpoints, then scraped spec)")
            print("  2. Spec-driven sweep (reads each model's spec)")
            sub = input("Choose [1]: ").strip() or "1"
            if sub == "2":
                from nimlab import cli
                cli.main(["sweep"])
                refresh_models()
            else:
                run_200_sweep()
                refresh_models()
        elif choice in ("d", "D"):
            from nimlab import cli
            cli.main(["discover"])
            refresh_models()
            pause()
        elif choice == "6":
            compare_models(pick_list())
        elif choice == "7":
            m = choose_model(pick_list())
            if m:
                generate_openai_snippet(m)
        elif choice == "8":
            show_history()
        elif choice == "9":
            settings()
        elif choice == "0":
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited.")
        sys.exit(0)
