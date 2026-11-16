"""Unit tests for lumenis_reactor_core/nemotron_omni.py. No network: httpx.MockTransport stands in for NVIDIA.

Run: .venv/bin/python tests/test_nemotron_omni.py
"""
import asyncio
import io
import json
import os
import sys
from contextlib import redirect_stdout

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["NEMOTRON_OMNI_KEY_ENV"] = "OMNI_TEST_KEY"
os.environ["OMNI_TEST_KEY"] = "test-key-not-real"
for k in list(os.environ):
    if k.startswith("NEMOTRON_OMNI_") and k != "NEMOTRON_OMNI_KEY_ENV":
        del os.environ[k]

from lumenis_reactor_core import nemotron_omni as om  # noqa: E402

RESULTS = []
SEEN = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))


def ok_json(answer="Heartbeat steady.", reasoning="thinking..."):
    return {"model": om.DEFAULT_MODEL, "choices": [{"message": {"role": "assistant", "content": answer,
            "reasoning_content": reasoning}, "finish_reason": "stop"}], "usage": {"total_tokens": 12}}


SSE = (
    'data: {"choices":[{"delta":{"reasoning_content":"let me think"}}]}\n\n'
    'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":"Hello "}}]}\n\n'
    ': keep-alive\n\n'
    'data: {"choices":[{"delta":{"content":"One2"}}]}\n\n'
    'data: [DONE]\n\n'
    'data: {"choices":[{"delta":{"content":"AFTER DONE"}}]}\n\n'
)


def handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    SEEN.append((request, body))
    if body["messages"][-1]["content"] == "fail":
        return httpx.Response(403, text='{"detail":"Forbidden"}')
    if body.get("stream"):
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=SSE)
    return httpx.Response(200, json=ok_json())


transport = httpx.MockTransport(handler)

# 1. payload matches the pasted snippet's settings
p = om.build_payload("hi")
check("default model", p["model"] == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
check("default max_tokens 65536", p["max_tokens"] == 65536)
check("default reasoning_budget 16384", p["reasoning_budget"] == 16384)
check("default temperature 0.6", p["temperature"] == 0.6)
check("default top_p 0.95", p["top_p"] == 0.95)
check("stream false by default", p["stream"] is False)
check("empty prompt field dropped", "prompt" not in p)
check("string -> one user message", p["messages"] == [{"role": "user", "content": "hi"}])

# 2. overrides: per call and by env
p = om.build_payload([{"role": "user", "content": "x"}], system="sys", max_tokens=100, reasoning_budget=50,
                     temperature=0.1, top_p=0.5, model="m/other")
check("system message first", p["messages"][0] == {"role": "system", "content": "sys"})
check("per-call overrides", (p["max_tokens"], p["reasoning_budget"], p["temperature"], p["top_p"], p["model"])
      == (100, 50, 0.1, 0.5, "m/other"))
os.environ["NEMOTRON_OMNI_REASONING_BUDGET"] = "2048"
os.environ["NEMOTRON_OMNI_MAX_TOKENS"] = "not-a-number"
p = om.build_payload("hi")
check("env override reasoning_budget", p["reasoning_budget"] == 2048)
check("bad env value falls back to default", p["max_tokens"] == 65536)
del os.environ["NEMOTRON_OMNI_REASONING_BUDGET"], os.environ["NEMOTRON_OMNI_MAX_TOKENS"]
try:
    om.build_payload([])
    check("empty messages rejected", False)
except om.OmniError:
    check("empty messages rejected", True)

# 3. headers: key from env, accept switches with stream, redaction
h = om.build_headers(False)
check("bearer from env", h["Authorization"] == "Bearer test-key-not-real")
check("accept json when not streaming", h["Accept"] == "application/json")
check("accept event-stream when streaming", om.build_headers(True)["Accept"] == "text/event-stream")
check("redaction hides key", "test-key" not in json.dumps(om.redacted_headers(h)))

# 4. missing key -> clear error, no request
os.environ["NEMOTRON_OMNI_KEY_ENV"] = "OMNI_MISSING_KEY_XYZ"
n = len(SEEN)
try:
    om.call("hi", client=httpx.Client(transport=transport))
    check("missing key raises", False)
except om.OmniError as e:
    check("missing key raises", "OMNI_MISSING_KEY_XYZ" in str(e))
check("missing key sends nothing", len(SEEN) == n)
os.environ["NEMOTRON_OMNI_KEY_ENV"] = "OMNI_TEST_KEY"

# 5. sync non-stream call
r = om.call("hi", client=httpx.Client(transport=transport))
req, body = SEEN[-1]
check("posts to invoke url", str(req.url) == "https://integrate.api.nvidia.com/v1/chat/completions")
check("answer parsed", r.content == "Heartbeat steady.")
check("reasoning kept separate", r.reasoning == "thinking..." and "thinking" not in r.content)
check("usage and finish_reason", r.usage == {"total_tokens": 12} and r.finish_reason == "stop")

# 6. sync stream
parts = list(om.stream("hi", client=httpx.Client(transport=transport)))
check("stream yields answer only", parts == [("content", "Hello "), ("content", "One2")], str(parts))
check("stream request has stream=true", SEEN[-1][1]["stream"] is True)
parts = list(om.stream("hi", include_reasoning=True, client=httpx.Client(transport=transport)))
check("stream with reasoning", parts[0] == ("reasoning", "let me think") and len(parts) == 3)
check("stops at [DONE]", all("AFTER" not in t for _, t in parts))

# 7. HTTP error -> OmniError with status
try:
    om.call("fail", client=httpx.Client(transport=transport))
    check("403 raises OmniError", False)
except om.OmniError as e:
    check("403 raises OmniError", "403" in str(e))
try:
    list(om.stream("fail", client=httpx.Client(transport=transport)))
    check("403 on stream raises", False)
except om.OmniError as e:
    check("403 on stream raises", "403" in str(e))


# 8. async call and stream
async def async_checks():
    async with httpx.AsyncClient(transport=transport) as c:
        r = await om.acall("hi", client=c)
        check("async call answer", r.content == "Heartbeat steady.")
        out = [x async for x in om.astream("hi", client=c)]
        check("async stream answer only", out == ["Hello ", "One2"], str(out))
        out = [x async for x in om.astream("hi", include_reasoning=True, client=c)]
        check("async stream reasoning tagged", out[0] == ("reasoning", "let me think"))
        try:
            [x async for x in om.astream("fail", client=c)]
            check("async 403 raises", False)
        except om.OmniError:
            check("async 403 raises", True)


asyncio.run(async_checks())

# 9. parsing edge cases
try:
    om.parse_reply({"error": "x"})
    check("no choices raises", False)
except om.OmniError:
    check("no choices raises", True)
check("garbage sse ignored", om.parse_sse_line("data: {not json") is None)
check("null content ok", om.parse_reply({"choices": [{"message": {"content": None}}]}).content == "")

# 10. CLI dry run never shows the key and makes no request
n = len(SEEN)
buf = io.StringIO()
with redirect_stdout(buf):
    rc = om.main(["hello", "--dry-run", "--reasoning-budget", "64"])
out = buf.getvalue()
check("dry run exit 0", rc == 0)
check("dry run hides key", "test-key-not-real" not in out and "<redacted>" in out)
check("dry run shows override", json.loads(out)["payload"]["reasoning_budget"] == 64)
check("dry run no request", len(SEEN) == n)

passed = sum(1 for _, ok in RESULTS if ok)
print(f"\n{passed}/{len(RESULTS)} passed")
sys.exit(0 if passed == len(RESULTS) else 1)
