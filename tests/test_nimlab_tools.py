"""Offline tests for the nimlab.* tools in the tool engine.

No network: every HTTP attempt goes through the real nimlab gate into a fake transport, so the host
allow-list, call budgets and rate limit are the production code. State lives in temp dirs.
Run: python3 tests/test_nimlab_tools.py
"""
import asyncio
import io
import json
import os
import struct
import sys
import tempfile
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["TOOL_ENGINE_DIR"] = tempfile.mkdtemp(prefix="engine_test_")
os.environ["NIMLAB_STATE_DIR"] = tempfile.mkdtemp(prefix="nimlab_test_")
os.environ["NIMLAB_CALLS_PER_MIN"] = "6"
FAKE_KEY = "nvapi-TESTONLY" + "x" * 40  # fake; proves the key never leaves in a result
os.environ["NIMLAB_KEY_VAR"] = "NIMLAB_TEST_KEY"
os.environ["NIMLAB_TEST_KEY"] = FAKE_KEY

from lumenis_reactor_core import tool_engine as te  # noqa: E402
from lumenis_reactor_core import nimlab_tools as nim  # noqa: E402

results = []


def check(name, cond, info=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{str(info)[:300]}]" if info and not cond else ""))


def wav(seconds=0.5, rate=22050):
    n = int(seconds * rate)
    data = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + b"data" + struct.pack("<I", len(data)) + data)


class Resp:
    def __init__(self, body, status=200, ctype="application/json"):
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.status = status
        self.headers = {"Content-Type": ctype}

    def read(self, n=-1):
        return self.body

    def getcode(self):
        return self.status

    def close(self):
        pass


class Fake:
    def __init__(self):
        self.seen = []
        self.fail_401 = False

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.seen.append((url, dict(req.header_items())))
        if self.fail_401:
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, io.BytesIO(b'{"detail":"bad key"}'))
        if url.endswith("/models"):
            return Resp({"data": [{"id": "meta/llama-3.1-8b-instruct"}, {"id": "nvidia/nv-embedqa-e5-v5"}]})
        if url.endswith("/chat/completions"):
            body = json.loads(req.data)
            return Resp({"choices": [{"message": {"content": "OK from " + body["model"]}}],
                         "usage": {"prompt_tokens": 5, "completion_tokens": 2}})
        if url.endswith("/embeddings"):
            body = json.loads(req.data)
            return Resp({"data": [{"index": i, "embedding": [0.1, 0.2, 0.3, 0.4]} for i, _ in enumerate(body["input"])]})
        if "rank" in url:
            return Resp({"rankings": [{"index": 1, "logit": 3.2}, {"index": 0, "logit": -1.0}]})
        if "audio/synthesize" in url:
            return Resp(wav(), ctype="audio/wav")
        return Resp({"detail": "not found"}, 404)


fake = Fake()
nim._test_opener = fake


async def d(name, args=None):
    return await te.dispatch(name, args or {}, caller="test")


async def run():
    # registration and discovery
    rows = te.list_tools(kind=None)
    names = {r["name"] for r in rows}
    check("nimlab tools listed by engine.list", {"nimlab.status", "nimlab.chat", "nimlab.rank", "nimlab.sweep"} <= names)
    r = await d("engine.list", {"kind": "nimlab"})
    check("engine.list kind=nimlab", r["ok"] and r["result"]["count"] == sum(
        1 for v in nim.TOOLS.values() if v[1] != "refused"), r)
    r = await d("engine.describe", {"name": "nimlab.chat"})
    check("describe gives schema + level", r["ok"] and r["result"]["level"] == "nvidia_call"
          and "prompt" in r["result"]["inputSchema"]["properties"], r)
    st = te.status()
    check("engine status carries nimlab summary", st["nimlab"]["tools"] == len(nim.TOOLS) and st["nimlab"]["key_present"], st.get("nimlab"))

    # local reads (suite stores built from the seed on first use)
    r = await d("nimlab.status")
    s = r.get("result", {})
    check("status runs and builds stores from seed", r["ok"] and s["stores"]["endpoints"] > 0, r)
    check("status never returns the key", FAKE_KEY not in json.dumps(r) and s["key"] == {"variable": "NIMLAB_TEST_KEY", "present": True}, s.get("key"))
    check("suite state lives in NIMLAB_STATE_DIR", (nim.STATE_DIR / "data").is_dir()
          and not (nim.SUITE_DIR / "data").exists() and not (nim.SUITE_DIR / "config_cluster.json").exists())
    r = await d("nimlab.list_models", {"list": "verified", "limit": 5})
    check("list_models verified", r["ok"] and r["result"]["count"] > 0 and len(r["result"]["rows"]) <= 5, r)
    r = await d("nimlab.route", {"model": "meta/llama-3.1-8b-instruct"})
    check("route resolves to an nvidia.com URL", r["ok"] and "nvidia.com" in json.dumps(r["result"]["route"]), r)
    for t in ("fleet", "benchmark_report", "leaderboard", "voices", "capabilities"):
        r = await d(f"nimlab.{t}")
        check(f"{t} runs offline", r["ok"], r)
    check("no HTTP during local reads", fake.seen == [], fake.seen)

    # validation
    r = await d("nimlab.chat", {"model": "x/y"})
    check("missing prompt -> 422", r["status"] == 422, r)
    r = await d("nimlab.chat", {"model": "bad model; rm -rf", "prompt": "hi"})
    check("model id pattern enforced -> 422", r["status"] == 422, r)
    r = await d("nimlab.rank", {"type": "chat", "models": ["a/b", "c/d", "e/f", "g/h"]})
    check("rank over 3 models -> 422", r["status"] == 422, r)
    r = await d("nimlab.chat", {"model": "a/b", "prompt": "hi", "api_key": "x"})
    check("extra args refused -> 422", r["status"] == 422, r)
    check("no HTTP for invalid calls", fake.seen == [], fake.seen)

    # one-request tools through the gate
    r = await d("nimlab.chat", {"model": "meta/llama-3.1-8b-instruct", "prompt": "say OK", "max_tokens": 8})
    check("chat returns the model text", r["ok"] and r["result"]["text"] == "OK from meta/llama-3.1-8b-instruct"
          and r["source"] == "remote" and r["result"]["http_requests"] == 1, r)
    url, hdrs = fake.seen[-1]
    check("key sent only in the Authorization header", hdrs.get("Authorization") == f"Bearer {FAKE_KEY}"
          and FAKE_KEY not in json.dumps(r), url)
    r = await d("nimlab.embed", {"model": "nvidia/nv-embedqa-e5-v5", "texts": ["a", "b"], "input_type": "query"})
    check("embed gives count + dims", r["ok"] and r["result"]["count"] == 2 and r["result"]["dims"] == 4, r)
    r = await d("nimlab.key_models", {"q": "llama"})
    check("key_models filters", r["ok"] and r["result"]["models"] == ["meta/llama-3.1-8b-instruct"], r)
    r = await d("nimlab.rerank", {"model": "nvidia/nv-rerankqa-mistral-4b-v3", "query": "q", "passages": ["p0", "p1"]})
    check("rerank orders passages", r["ok"] and r["result"]["ranking"][0]["index"] == 1, r)
    r = await d("nimlab.tts", {"text": "Lumenis online.", "voice": "Magpie-Multilingual.EN-US.Aria"})
    res = r.get("result", {})
    check("tts saves a WAV + artifact", r["ok"] and Path(res["file"]).is_file() and res["bytes"] > 200
          and res["artifact"]["artifact_id"].startswith("a_") and res["duration_s"] == 0.5, r)

    # rate limit (6/min in this test): 5 requests used so far
    r = await d("nimlab.probe", {"model": "meta/llama-3.1-8b-instruct"})
    check("probe answers", r["ok"] and r["result"]["answered"], r)
    r = await d("nimlab.probe", {"model": "meta/llama-3.1-8b-instruct"})
    check("7th request in a minute -> 429 with retry_after", r["status"] == 429 and r.get("retry_after_s", 0) > 0, r)
    nim._calls.clear()

    # host allow-list and budget, straight at the gate
    import urllib.request
    gate = nim._gated(fake, nim._Budget(1))
    try:
        gate(urllib.request.Request("https://svn-dev.online/mcp"))
        check("non-NVIDIA host refused", False)
    except nim.NimlabError as e:
        check("non-NVIDIA host refused", e.status == 403)
    for u in ("http://integrate.api.nvidia.com/v1/models", "https://nvidia.com.evil.example/x",
              "https://evilnvidia.com/x"):
        check(f"refused {u}", not nim.host_allowed(u))
    check("allowed subdomain", nim.host_allowed("https://877104f7.invocation.api.nvcf.nvidia.com/v1/audio/synthesize"))
    gate(urllib.request.Request("https://integrate.api.nvidia.com/v1/models"))
    try:
        gate(urllib.request.Request("https://integrate.api.nvidia.com/v1/models"))
        check("budget exhausted -> refused", False)
    except nim.NimlabError as e:
        check("budget exhausted -> refused", e.status == 429)
    nim._calls.clear()

    # NVIDIA errors are reported, not hidden
    fake.fail_401 = True
    r = await d("nimlab.chat", {"model": "meta/llama-3.1-8b-instruct", "prompt": "hi"})
    check("401 from NVIDIA surfaces as failed call", not r["ok"] and r["status"] == 401 and FAKE_KEY not in json.dumps(r), r)
    r = await d("nimlab.probe", {"model": "meta/llama-3.1-8b-instruct"})
    check("failed probe is a result with answered=false", r["ok"] and r["result"]["answered"] is False, r)
    fake.fail_401 = False
    nim._calls.clear()

    # image files: allowed roots only
    assets = sorted(p for p in (nim.SUITE_DIR / "assets").rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    if assets:
        r = await d("nimlab.vision", {"model": "meta/llama-3.2-11b-vision-instruct",
                                      "image_path": str(assets[0].relative_to(ROOT)), "prompt": "what is this"})
        check("vision on a suite asset", r["ok"] and r["result"]["text"].startswith("OK from"), r)
    else:
        check("suite has a test image asset", False)
    r = await d("nimlab.vision", {"model": "a/b", "image_path": "/etc/passwd"})
    check("image outside allowed roots -> 403", r["status"] == 403, r)
    r = await d("nimlab.ocr", {"model": "a/b", "image_path": ".env"})
    check(".env as image -> 403", r["status"] == 403, r)

    # bounded ranking with the suite's real judge code (fake transport)
    nim._calls.clear()
    r = await d("nimlab.rank", {"type": "chat", "models": ["meta/llama-3.1-8b-instruct"], "judge": "meta/llama-3.1-8b-instruct"})
    res = r.get("result", {})
    check("rank runs within its budget and is saved", r["ok"] and 0 < res["http_requests"] <= nim.RANK_MAX_CALLS
          and (nim.STATE_DIR / "rank_runs.jsonl").is_file(), r)
    r = await d("nimlab.leaderboard")
    check("leaderboard shows the rank run", r["ok"] and len(r["result"]["recent_rank_runs"]) == 1, r)
    nim._calls.clear()

    # refused tools never touch the network
    before = len(fake.seen)
    for t in ("sweep", "discover", "image_gen", "voice_clone", "judge_apply", "mcp_bridge"):
        r = await d(f"nimlab.{t}")
        check(f"{t} refused 403", r["status"] == 403 and r["kind"] == "refused", r)
    check("refused tools sent nothing", len(fake.seen) == before)
    r = await d("nimlab.nope")
    check("unknown nimlab tool -> 404", r["status"] == 404, r)

    # kill switch and missing key
    os.environ["NIMLAB_TOOLS"] = "0"
    r = await d("nimlab.status")
    check("NIMLAB_TOOLS=0 -> 503", r["status"] == 503, r)
    os.environ.pop("NIMLAB_TOOLS")
    os.environ["NIMLAB_TEST_KEY"] = ""
    r = await d("nimlab.chat", {"model": "a/b", "prompt": "hi"})
    check("no key -> 503, nothing sent", r["status"] == 503 and len(fake.seen) == before, r)
    os.environ["NIMLAB_TEST_KEY"] = FAKE_KEY

    # traces never hold the key
    rows = te._rows("SELECT args, error FROM traces WHERE tool LIKE 'nimlab.%'")
    check("traces recorded, no key in them", rows and FAKE_KEY not in json.dumps(rows), len(rows))


asyncio.run(run())
passed = sum(1 for _, ok in results if ok)
print(f"\n{passed}/{len(results)} passed")
sys.exit(0 if passed == len(results) else 1)
