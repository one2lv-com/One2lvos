#!/usr/bin/env python3
"""NVIDIA NIM Dynamic Multi-Modal Fleet Benchmark Suite.

Automatically queries nvidia_verified_endpoints.json or nvidia_inventory.json,
partitions all confirmed live models into their functional types, and benchmarks
all models of each type in a single, comprehensive evaluation run.
Zero third-party dependencies.
"""

import json
import os
import sys
import time

from nimlab import config
from nimlab.api import image_to_data_url, save_wav, wav_duration
from nimlab.core import HttpClient, build_multipart, load_api_key, redact, sanitize_key
from nimlab.memory import cosine_similarity  # noqa: F401  (re-exported for older scripts)
from nimlab import store
from nimlab.router import load_live_fleet, model_types

API_KEY = load_api_key()
INTEGRATE_URL = "https://integrate.api.nvidia.com/v1"
AI_API_URL = "https://ai.api.nvidia.com/v1"

BENCHMARK_OUTPUT = store.path(store.BENCHMARK)  # data/benchmark_latest.json
DEFAULT_TEST_IMAGE = "/storage/emulated/0/image.png"
BUNDLED_TEST_IMAGE = os.path.join(config.PROJECT_DIR, "assets", "vision_test.png")

# Hardcoded fallback list matching your verified sweep in case JSON files are missing/empty
FALLBACK_21_FLEET = [
    ("nvidia/nemotron-3.5-embed-8b", "embeddings_typed"),
    ("nvidia/nemotron-3.5-embed-1b", "embeddings_typed"),
    ("nvidia/nemotron-3-embed-1b", "embeddings"),
    ("nvidia/llama-nemotron-embed-vl-1b-v2", "embeddings_typed"),
    ("meta/llama-3.2-90b-vision-instruct", "vision"),
    ("nvidia/nemotron-3.5-super-vl-120b-a12b", "vision"),
    ("google/diffusiongemma-26b-a4b-it", "vision"),
    ("poolside/laguna-xs-2.1", "chat"),
    ("nvidia/nemotron-3.5-lightning-30b-a3b", "chat"),
    ("nvidia/nemotron-3.5-bolt-e4b", "chat"),
    ("nvidia/nemotron-parse-2.0", "chat"),
    ("meta/llama-guard-4-12b", "chat"),
    ("nvidia/llama-3.1-nemotron-safety-guard-8b-v3", "chat"),
    ("nvidia/riva-translate-4b-instruct-v2", "chat"),
    ("mistralai/mistral-large-4-1t-a52b", "chat"),
    ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "chat"),
    ("nvidia/nemotron-3-ultra-550b-a55b", "chat"),
    ("meta/muse-glimmer-30b", "chat"),
    ("stepfun-ai/step-5-preview", "chat"),
    ("minimaxai/minimax-m3.1-flash", "chat"),
    ("google/gemma-4-31b-it", "chat"),
]

# NVCF Host for hosted Magpie TTS Multilingual
MAGPIE_NVCF_HOST = "https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation.api.nvcf.nvidia.com"

VOICE_PROFILES = [
    ("Magpie Aria (Female)", f"{MAGPIE_NVCF_HOST}/v1/audio/synthesize", "Magpie-Multilingual.EN-US.Aria"),
    ("Magpie Jason (Male)", f"{MAGPIE_NVCF_HOST}/v1/audio/synthesize", "Magpie-Multilingual.EN-US.Jason"),
]


def check_auth():
    global API_KEY
    if not API_KEY:
        from getpass import getpass
        API_KEY = sanitize_key(getpass("Enter NVIDIA API Key (or set NVIDIA_API_KEY in shell): "))
        if not API_KEY:
            sys.exit("API Key required.")


def _http(timeout):
    return HttpClient(timeout=timeout, retries=1, backoff=1.5)


def post_json(url, payload, timeout=60):
    """Returns (status, parsed_json_or_text, latency) via the shared client."""
    res = _http(timeout).post_json(url, payload, {"Authorization": f"Bearer {API_KEY}"})
    if res.status is None:
        return None, redact(res.error or ""), res.latency
    parsed = res.json()
    return res.status, (parsed if parsed is not None else redact(res.text)), res.latency


def partition_fleet(with_others=False):
    """Discover and categorize all working models with fallback tolerance.
    with_others=True also returns every live model that fits none of the
    three scored tracks (safety, translate, OCR/parse, rerank, CV, image
    generation, speech...) so the smoke track can test it."""
    embeddings = []
    vision = []
    reasoning = []
    others = []

    # The verified 200 OK fleet (data/models_verified.json), classified by nimlab.router
    for model_id, details in load_live_fleet().items():
        kind = details.get("kind", "") or ""
        url = details.get("url")
        types = model_types(model_id, kind, details.get("catalog_kind"))
        if "embeddings" in types and url:
            embeddings.append((model_id, url, kind if kind.startswith("embed") else "embeddings_typed"))
        elif "vision" in types and url and "chat/completions" in url:
            vision.append((model_id, url, "vision"))
        elif "chat" in types and url and "chat/completions" in url:
            reasoning.append((model_id, url, "chat"))
        else:
            others.append((model_id, details))

    # Only models that passed the 200 test are benchmarked: no inventory or
    # hardcoded fallback lists.
    if not (embeddings or vision or reasoning or others):
        print("[!] No 200-tested models in nvidia_verified_endpoints.json yet.")
        print("    Run the 200 Health & Fallback Sweep first (launcher option 2).")

    # De-duplicate
    embeddings = list({x[0]: x for x in embeddings}.values())
    vision = list({x[0]: x for x in vision}.values())
    reasoning = list({x[0]: x for x in reasoning}.values())

    if with_others:
        return embeddings, vision, reasoning, others
    return embeddings, vision, reasoning


# =====================================================================
# TRACK 5: ENDPOINT SMOKE TEST (every live model the scored tracks skip)
# =====================================================================
def _smoke_plan(model, entry):
    """Re-probe plan from a verified entry: its URL, method, content type,
    function id and saved request, or a minimal request for its kind."""
    from nimlab import spec
    kind = (entry.get("kind") or "chat").lower()
    ctype = entry.get("content_type") or "application/json"
    api_model = entry.get("api_model_id") or model
    body = entry.get("request_template")
    if ctype == "multipart/form-data":
        kind = "asr" if ("asr" in kind or "transcri" in entry.get("url", "")) else "tts"
    elif body is None:
        if kind in ("rerank", "ranking"):
            body = {"model": api_model, "query": {"text": "probe"}, "passages": [{"text": "sample"}]}
        elif kind == "audio_tts":
            body = {"model": api_model, "input": "test", "voice": "Magpie-Multilingual.EN-US.Aria",
                    "response_format": "wav"}
        elif kind.startswith("embed"):
            body = {"model": api_model, "input": ["probe"], "input_type": "query", "encoding_format": "float"}
        elif "chat/completions" in entry.get("url", "") or kind in ("chat", "vision", "chat_stream"):
            body = spec.build_minimal_request({}, {}, "chat", api_model)
        elif kind == "image_gen":
            body = {"prompt": "sample", "cfg_scale": 3.0, "steps": 5}
    return {"url": entry["url"], "method": entry.get("method", "POST"), "content_type": ctype, "kind": kind,
            "model": api_model, "body": body, "alt_body": None, "function_id": entry.get("function_id"),
            "transport": entry.get("transport") or "rest", "source": "verified", "path": None}


def run_smoke_benchmarks(other_models, prober=None):
    print("\n" + "=" * 70)
    print(f"  ENDPOINT SMOKE TEST: {len(other_models)} live models outside the scored tracks")
    print("  (safety, translate, OCR/parse, rerank, CV, image generation, speech...)")
    print("=" * 70)
    if prober is None:
        from nimlab import sweep as spec_sweep
        prober = spec_sweep.Prober(api_key=API_KEY, timeout=45)
    results = []
    for model, entry in other_models:
        if not entry.get("url"):
            results.append({"model": model, "kind": entry.get("kind"), "status": "NO_URL",
                            "reason": "verified entry has no URL"})
            print(f"  {model:<44} [skipped: no URL in verified entry]")
            continue
        plan = _smoke_plan(model, entry)
        o = prober.probe_plan(plan)
        r = {"model": model, "kind": entry.get("kind"), "catalog_kind": entry.get("catalog_kind"),
             "url": entry["url"], "status": o["status"], "http_status": o.get("http_status"),
             "latency_sec": o.get("latency_sec"), "reason": redact(o.get("reason") or "")}
        results.append(r)
        tag = "200 OK" if o["status"] == "LIVE_200" else o["status"]
        print(f"  {model:<44} {tag:<24} {r['latency_sec']}s")
    return results


def coverage_line(embed_models, vision_models, reasoning_models, other_models):
    total = len(embed_models) + len(vision_models) + len(reasoning_models) + len(other_models)
    return (f"Live endpoints: {total} = {len(reasoning_models)} reasoning + {len(vision_models)} vision + "
            f"{len(embed_models)} embedding + {len(other_models)} smoke-tested")


# =====================================================================
# TRACK 1: EMBEDDINGS & RECALL@1 BENCHMARK
# =====================================================================
def run_embedding_benchmarks(embed_models):
    print("\n" + "=" * 70)
    print("      TRACK 1: EMBEDDINGS & RECALL@1 BENCHMARK (ALL DETECTED)")
    print("=" * 70)
    if not embed_models:
        print("No embedding models available.")
        return []

    print(f"Testing {len(embed_models)} embedding models:\n")
    for m, _, _ in embed_models:
        print(f"  • {m}")
    print()

    passages = [
        "The Mojave Desert features an extreme arid ecosystem characterized by creosote bush and Joshua trees.",
        "A 12-volt DC solar electrical setup requires a charge controller, deep-cycle battery bank, and low-gauge copper wiring.",
        "FastAPI provides asynchronous execution using ASGI routers and Pydantic request models.",
        "Autonomous database cognitive architectures utilize vector embeddings to store agent memory states directly in tables.",
        "High-performance audio processing filter chains rely on FFmpeg and psychoacoustic mastering algorithms.",
    ]
    needle_index = 3
    query = "How do autonomous database engines persist synaptic cognitive memories?"

    results = []

    for model, url, kind in embed_models:
        target_url = url or f"{INTEGRATE_URL}/embeddings"
        print(f"--> MODEL: {model}")

        p_payload = {
            "model": model,
            "input": passages,
            "encoding_format": "float",
            "input_type": "passage"
        }

        # 1. Try with asymmetric input_type
        p_payload["input_type"] = "passage"
        status, p_res, p_time = post_json(target_url, p_payload)

        # 2. If rejected because input_type is forbidden/unknown, retry without it
        if status != 200:
            err_str = str(p_res).lower()
            if "extra" in err_str or "unexpected" in err_str or "unrecognized" in err_str:
                p_payload.pop("input_type", None)
                status, p_res, p_time = post_json(target_url, p_payload)

        if status != 200 or not isinstance(p_res, dict) or "data" not in p_res:
            print(f"    [!] Failed embedding passages ({status}): {p_res}")
            results.append({"model": model, "status": "FAILED", "stage": "passage"})
            continue

        passage_vectors = [item["embedding"] for item in p_res["data"]]

        q_payload = {
            "model": model,
            "input": [query],
            "encoding_format": "float"
        }
        if "input_type" in p_payload:
            q_payload["input_type"] = "query"
        status, q_res, q_time = post_json(target_url, q_payload)
        if status != 200 and "unexpected" in str(q_res).lower():
            q_payload.pop("input_type", None)
            status, q_res, q_time = post_json(target_url, q_payload)
            if status != 200:
                print(f"    [!] Failed embedding query ({status}): {q_res}")
                results.append({"model": model, "status": "FAILED", "stage": "query"})
                continue

        query_vector = q_res["data"][0]["embedding"]
        dims = len(query_vector)

        scores = [cosine_similarity(query_vector, pv) for pv in passage_vectors]
        ranked = sorted(list(enumerate(scores)), key=lambda x: x[1], reverse=True)
        top_idx, top_score = ranked[0]
        recalled = (top_idx == needle_index)

        print(f"    Dims: {dims} | Passage Latency: {p_time}s | Query Latency: {q_time}s")
        print(f"    Top Match: Passage #{top_idx + 1} (Score: {top_score:.4f})")
        print(f"    Recall@1:  {'[PASS] Exact Needle Match' if recalled else '[FAIL] Wrong Passage'}")

        results.append({
            "model": model,
            "dimensions": dims,
            "passage_latency_sec": p_time,
            "query_latency_sec": q_time,
            "top_match_index": top_idx,
            "top_match_score": top_score,
            "recall_pass": recalled,
        })
        print("-" * 70)

    return results


# =====================================================================
# TRACK 2: MULTI-VLM PERSPECTIVE SHOOTOUT
# =====================================================================
def run_vision_benchmarks(vision_models):
    print("\n" + "=" * 70)
    print("      TRACK 2: MULTI-VLM VISUAL PERSPECTIVE (ALL DETECTED)")
    print("=" * 70)
    if not vision_models:
        print("No vision models available.")
        return []

    print(f"Testing {len(vision_models)} vision models:\n")
    for m, _, _ in vision_models:
        print(f"  • {m}")
    print()

    default_img = DEFAULT_TEST_IMAGE if os.path.isfile(DEFAULT_TEST_IMAGE) else BUNDLED_TEST_IMAGE
    img_path = input(f"Enter path to image [{default_img}]: ").strip() or default_img
    data_url = image_to_data_url(img_path)
    if not data_url:
        print(f"File not found: {img_path}")
        return []

    prompt = (
        "Examine this image with forensic precision: describe primary objects, text/symbols, "
        "spatial layout, background context, and color palette. Conclude in under 80 words."
    )

    results = []

    for model, url, _ in vision_models:
        target_url = url or f"{INTEGRATE_URL}/chat/completions"
        print(f"--> MODEL: {model}")

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "max_tokens": 256,
            "temperature": 0.2,
            "stream": False,
        }

        status, res, latency = post_json(target_url, payload, timeout=90)
        if status == 200 and isinstance(res, dict):
            msg = res.get("choices", [{}])[0].get("message", {})
            content = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            usage = res.get("usage", {})
            tokens = usage.get("completion_tokens", len(content.split()))
            tps = round(tokens / latency, 2) if latency > 0 else "N/A"

            print(f"    Status: 200 OK | Latency: {latency}s | Tokens: {tokens} (~{tps} tok/s)")
            print("    Analysis:")
            for l in content.split("\n"):
                if l.strip():
                    print(f"      {l}")

            results.append({
                "model": model,
                "latency_sec": latency,
                "tokens": tokens,
                "tokens_per_sec": tps,
                "output_sample": content[:250],
            })
        else:
            print(f"    [!] Failed ({status} in {latency}s): {res}")
            results.append({"model": model, "status": "FAILED", "error": str(res)[:100]})
        print("-" * 70)

    return results


# =====================================================================
# TRACK 3: REASONING & INSTRUCT LLM SHOOTOUT
# =====================================================================
def run_reasoning_benchmarks(reasoning_models):
    print("\n" + "=" * 70)
    print("      TRACK 3: REASONING & INSTRUCT LLM SHOOTOUT (ALL DETECTED)")
    print("=" * 70)
    if not reasoning_models:
        print("No reasoning models available.")
        return []

    print(f"Testing {len(reasoning_models)} chat/reasoning models:\n")
    for m, _, _ in reasoning_models:
        print(f"  • {m}")
    print()

    prompt = (
        "Solve this step-by-step: A farmer has to cross a river with a fox, a goose, and a bag of grain. "
        "The boat holds only the farmer and one item. If left alone, fox eats goose, goose eats grain. "
        "List the shortest sequence of trips to get all three safely across. State total trips at the end."
    )

    results = []

    # Filter out specialized utility models that are not general reasoning agents
    eval_models = [m for m in reasoning_models if not any(x in m[0].lower() for x in ("guard", "translate", "parse"))]

    for model, url, _ in eval_models:
        target_url = url or f"{INTEGRATE_URL}/chat/completions"
        print(f"--> MODEL: {model}")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a precise, logical reasoning engine. Be concise."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "temperature": 0.1,
            "stream": False,
        }

        status, res, latency = post_json(target_url, payload, timeout=90)
        if status == 200 and isinstance(res, dict):
            choice = res["choices"][0]["message"]
            content = (choice.get("content") or choice.get("reasoning_content") or "").strip()
            usage = res.get("usage", {})
            tokens = usage.get("completion_tokens", len(content.split()))
            tps = round(tokens / latency, 2) if latency > 0 else "N/A"

            c_lower = content.lower()
            correct = any(x in c_lower for x in ("7 trips", "seven trips", "7 crossings", "seven crossings", "total trips: 7", "total: 7"))

            print(f"    Status: 200 OK | Latency: {latency}s | Tokens: {tokens} ({tps} tok/s)")
            print(f"    Logic Evaluation: {'[PASS] 7 Trips Identified' if correct else '[CHECK] Verify Reasoning'}")
            print("    Sample Output:")
            for l in content.strip().split("\n")[:4]:
                print(f"      {l}")
            if len(content.strip().split("\n")) > 4:
                print("      ...")

            results.append({
                "model": model,
                "latency_sec": latency,
                "tokens": tokens,
                "tokens_per_sec": tps,
                "logic_pass": correct,
            })
        else:
            print(f"    [!] Failed ({status} in {latency}s): {str(res)[:100]}")
            results.append({"model": model, "status": "FAILED", "error": str(res)[:100]})
        print("-" * 70)

    return results


# =====================================================================
# TRACK 4: VOICE PROFILE SYNTHESIS BENCHMARK
# =====================================================================
def post_multipart_form(url, fields, timeout=30):
    """Returns (status, body_bytes_or_error, latency) via the shared client."""
    body, ctype = build_multipart(fields)
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": ctype, "Accept": "audio/wav, application/json"}
    res = _http(timeout).request("POST", url, body, headers)
    if res.status is None:
        return None, redact(res.error or ""), res.latency
    return res.status, res.body, res.latency


def run_voice_benchmarks():
    print("\n" + "=" * 70)
    print("      TRACK 4: VOICE PROFILE SYNTHESIS & RTF BENCHMARK")
    print("=" * 70)

    test_phrase = "Sovereign Neural System online. Audio telemetry nominal, neural synaptic buffers initialized."
    print(f"Testing {len(VOICE_PROFILES)} voice endpoints / profiles:")
    print(f"Test Phrase: '{test_phrase}'\n")

    results = []

    for label, url, voice in VOICE_PROFILES:
        print(f"--> PROFILE: {label} [{voice}]")
        fields = {
            "text": test_phrase,
            "language": "en-US",
            "voice": voice,
            "encoding": "LINEAR_PCM",
        }

        status, raw_bytes, latency = post_multipart_form(url, fields, timeout=35)

        if status == 200 and isinstance(raw_bytes, (bytes, bytearray)) and len(raw_bytes) > 200:
            out_name = save_wav(raw_bytes, f"bench_{voice.split('.')[-1].lower()}")

            size_bytes = len(raw_bytes)
            # real duration from the WAV header (falls back to 22.05kHz/16-bit mono)
            est_seconds = round(wav_duration(raw_bytes), 2)
            rtf = round(latency / est_seconds, 3) if est_seconds > 0 else "N/A"

            print(f"    Status: 200 OK | Latency: {latency}s")
            print(f"    Audio Output: {out_name} ({round(size_bytes/1024, 1)} KB, ~{est_seconds}s)")
            print(f"    Real-Time Factor (RTF): {rtf} (<1.0 is faster than real-time)")

            results.append({
                "profile": label,
                "voice": voice,
                "latency_sec": latency,
                "size_kb": round(size_bytes/1024, 1),
                "duration_sec": est_seconds,
                "rtf": rtf,
            })
        else:
            err_peek = raw_bytes.decode("utf-8", errors="replace")[:150] if isinstance(raw_bytes, (bytes, bytearray)) else str(raw_bytes)[:150]
            print(f"    [!] HTTP {status} ({latency}s): {err_peek}")
        print("-" * 70)

    return results


def print_summary_table(embed_res, vision_res, reasoning_res, voice_res, smoke_res=None):
    print("\n" + "#" * 70)
    print("                     FLEET BENCHMARK SUMMARY")
    print("#" * 70)

    if reasoning_res:
        print("\n[ REASONING / INSTRUCT LLMs ]")
        print(f"{'Model':<44} | {'Latency':<8} | {'Tokens':<6} | {'Tok/s':<7} | {'Logic'}")
        print("-" * 76)
        for r in sorted([x for x in reasoning_res if "tokens_per_sec" in x], key=lambda x: x["latency_sec"]):
            logic = "PASS" if r.get("logic_pass") else "FAIL"
            print(f"{r['model']:<44} | {r['latency_sec']:>6}s | {r['tokens']:>6} | {str(r['tokens_per_sec']):>7} | {logic}")

    if embed_res:
        print("\n[ EMBEDDING & RETRIEVAL ]")
        print(f"{'Model':<44} | {'Dims':<5} | {'Passage':<8} | {'Query':<8} | {'Recall@1'}")
        print("-" * 76)
        for r in embed_res:
            if "dimensions" in r:
                rec = "PASS" if r.get("recall_pass") else "FAIL"
                print(f"{r['model']:<44} | {r['dimensions']:<5} | {r['passage_latency_sec']:>6}s | {r['query_latency_sec']:>6}s | {rec}")

    if vision_res:
        print("\n[ MULTIMODAL VISION ]")
        print(f"{'Model':<44} | {'Latency':<8} | {'Tokens':<6} | {'Tok/s'}")
        print("-" * 68)
        for r in vision_res:
            if "latency_sec" in r:
                print(f"{r['model']:<44} | {r['latency_sec']:>6}s | {r['tokens']:>6} | {str(r['tokens_per_sec']):>6}")

    if voice_res:
        print("\n[ VOICE SYNTHESIS ]")
        print(f"{'Profile':<30} | {'Latency':<8} | {'Duration':<8} | {'RTF'}")
        print("-" * 60)
        for r in voice_res:
            print(f"{r['profile']:<30} | {r['latency_sec']:>6}s | ~{r['duration_sec']:>5}s | {r['rtf']}")

    if smoke_res:
        print("\n[ ENDPOINT SMOKE TEST: OTHER LIVE MODELS ]")
        print(f"{'Model':<44} | {'Kind':<10} | {'Status':<24} | {'Latency'}")
        print("-" * 90)
        for r in smoke_res:
            kind = str(r.get("catalog_kind") or r.get("kind") or "")[:10]
            print(f"{r['model']:<44} | {kind:<10} | {r['status']:<24} | {r.get('latency_sec')}s")

    print("\n" + "#" * 70)


def save_track(track, rows):
    """A single-track run replaces that track in the latest benchmark and
    keeps the other tracks from the last run."""
    if rows is None:
        return
    report = dict(store.latest_benchmark() or {})
    report.pop("schema", None)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report[track] = rows
    report.setdefault("track_times", {})[track] = now
    report["timestamp"] = now
    report["last_run"] = track
    store.save_benchmark(report)
    print(f"\nSaved the {track} results to: {BENCHMARK_OUTPUT}")


def main():
    check_auth()
    embed_models, vision_models, reasoning_models, other_models = partition_fleet(with_others=True)

    while True:
        os.system("clear" if os.name != "nt" else "cls")
        print("=" * 70)
        print("         NVIDIA NIM DYNAMIC MULTI-MODAL BENCHMARK SUITE")
        print("=" * 70)
        print("Fleet Active in Suite:")
        print(f"  • Embedding Models : {len(embed_models)}")
        print(f"  • Vision Models    : {len(vision_models)}")
        print(f"  • Reasoning Models : {len(reasoning_models)}")
        print(f"  • Other Live Models: {len(other_models)}  (smoke-tested: safety, OCR, rerank, CV, speech...)")
        print(f"  • Voice Profiles   : {len(VOICE_PROFILES)}")
        print(f"  {coverage_line(embed_models, vision_models, reasoning_models, other_models)}")
        print("-" * 70)
        print("  1. Benchmark All Embedding Models (Recall@1 & Dims)")
        print("  2. Benchmark All Vision Models (Perspective & Throughput)")
        print("  3. Benchmark All Reasoning/LLM Models (Logic & TPS)")
        print("  4. Benchmark All Voice Profiles (RTF & Synthesis)")
        print("  5. RUN COMPLETE FLEET BENCHMARK (All Types In One Run)")
        print("  6. Smoke-Test All Other Live Models (status & latency)")
        print("  0. Exit")

        choice = input("\nSelect suite: ").strip()

        if choice == "1":
            save_track("embeddings", run_embedding_benchmarks(embed_models))
            input("\nPress Enter to continue...")
        elif choice == "2":
            save_track("vision", run_vision_benchmarks(vision_models))
            input("\nPress Enter to continue...")
        elif choice == "3":
            save_track("reasoning", run_reasoning_benchmarks(reasoning_models))
            input("\nPress Enter to continue...")
        elif choice == "4":
            save_track("voice", run_voice_benchmarks())
            input("\nPress Enter to continue...")
        elif choice == "5":
            e_res = run_embedding_benchmarks(embed_models)
            v_res = run_vision_benchmarks(vision_models)
            r_res = run_reasoning_benchmarks(reasoning_models)
            vo_res = run_voice_benchmarks()
            s_res = run_smoke_benchmarks(other_models)

            print_summary_table(e_res, v_res, r_res, vo_res, s_res)

            report = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "embeddings": e_res,
                "vision": v_res,
                "reasoning": r_res,
                "voice": vo_res,
                "other_smoke": s_res,
                "coverage": coverage_line(embed_models, vision_models, reasoning_models, other_models),
            }
            store.save_benchmark(report)
            print(f"\nSaved full benchmark telemetry matrix to: {BENCHMARK_OUTPUT}")
            input("\nPress Enter to continue...")
        elif choice == "6":
            save_track("other_smoke", run_smoke_benchmarks(other_models))
            input("\nPress Enter to continue...")
        elif choice == "0":
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited.")
        sys.exit(0)
