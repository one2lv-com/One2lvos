"""Measure NVIDIA chat models for the fast path: time to first token and total, 3 tries each.
Reads NVIDIA_API_KEY from .env; never prints it."""
import asyncio, json, os, sys, time
from pathlib import Path
import httpx

for line in (Path(__file__).parent.parent / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))
KEY = os.environ["NVIDIA_API_KEY"]
URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODELS = sys.argv[1:] or [
    "meta/llama-3.3-70b-instruct", "meta/llama-3.1-8b-instruct", "meta/llama-4-maverick-17b-128e-instruct",
    "meta/llama-4-scout-17b-16e-instruct", "meta/llama-3.2-90b-vision-instruct", "mistralai/mistral-small-24b-instruct",
]
SYS = "You are Lumenis, a warm, curious AI. Answer in two or three sentences."
Q = "Hey Lumenis, how's it going? What's on your mind today?"


async def once(c, model):
    t0 = time.time(); first = None; n = 0
    try:
        async with c.stream("POST", URL, headers={"Authorization": f"Bearer {KEY}", "Accept": "text/event-stream"},
                            json={"model": model, "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": Q}],
                                  "max_tokens": 200, "temperature": 0.5, "stream": True}) as r:
            if r.status_code != 200:
                return f"HTTP {r.status_code}"
            async for line in r.aiter_lines():
                if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                    try:
                        d = json.loads(line[6:])["choices"][0]["delta"].get("content")
                    except Exception:
                        d = None
                    if d:
                        n += len(d)
                        if first is None:
                            first = time.time() - t0
        return f"first {first:.2f}s total {time.time()-t0:.2f}s ({n} chars)" if first else "no content"
    except Exception as e:
        return f"{type(e).__name__}"


async def main():
    async with httpx.AsyncClient(timeout=60) as c:
        for m in MODELS:
            res = [await once(c, m) for _ in range(3)]
            print(m, "|", " ; ".join(res), flush=True)

asyncio.run(main())
