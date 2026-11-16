"""NVIDIA Nemotron 3 Nano Omni (reasoning) client for the Lumenis reactor.

Built from the request snippet the owner pasted on 2026-11-15 (invoke URL, headers, payload, stream or not),
with three changes:
    - the API key is read from the environment (.env), never written in code;
    - every payload setting can be overridden per call or by env variable;
    - the reply is parsed: the final answer (`content`) is kept apart from the model's thinking
      (`reasoning_content`), so the reasoning never leaks into what Lumenis says.
The snippet's empty "prompt": "" field is dropped; chat/completions takes `messages`.

Use from Python
    from lumenis_reactor_core.nemotron_omni import call, acall, astream
    r = call("Explain the reactor heartbeat in one line")            # sync, returns OmniReply
    r = await acall([{"role": "user", "content": "..."}])         # async
    async for piece in astream("..."): ...                         # async stream, answer text only

Use from the shell (repo root)
    .venv/bin/python -m lumenis_reactor_core.nemotron_omni "your prompt"            # one call
    .venv/bin/python -m lumenis_reactor_core.nemotron_omni "your prompt" --stream   # print as it streams
    .venv/bin/python -m lumenis_reactor_core.nemotron_omni "your prompt" --dry-run  # show payload, no call

Env (all optional except the key)
    NVIDIA_API_KEY                  key used by default
    NEMOTRON_OMNI_KEY_ENV           name of a different env variable to take the key from
    NEMOTRON_OMNI_URL               default https://integrate.api.nvidia.com/v1/chat/completions
    NEMOTRON_OMNI_MODEL             default nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
    NEMOTRON_OMNI_MAX_TOKENS        default 65536
    NEMOTRON_OMNI_REASONING_BUDGET  default 16384
    NEMOTRON_OMNI_TEMPERATURE       default 0.6
    NEMOTRON_OMNI_TOP_P             default 0.95
    NEMOTRON_OMNI_TIMEOUT_S         default 300
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Iterator

import httpx

DEFAULT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
DEFAULTS = {
    "max_tokens": 65536,
    "reasoning_budget": 16384,
    "temperature": 0.6,
    "top_p": 0.95,
}
REPO_ROOT = Path(__file__).resolve().parent.parent


class OmniError(RuntimeError):
    pass


@dataclass
class OmniReply:
    content: str
    reasoning: str = ""
    model: str = ""
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
    raw: dict | None = None


# ── configuration ───────────────────────────────────────────────────────────────────────────────
def _load_dotenv_if_needed(key_env: str) -> None:
    """Fill the key from the repo .env only when the process environment does not have it
    (the reactor already loads .env; this is for running the module on its own)."""
    if os.environ.get(key_env):
        return
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key_env:
            os.environ[key_env] = v.strip().strip('"').strip("'")
            return


def key_env_name() -> str:
    return os.environ.get("NEMOTRON_OMNI_KEY_ENV", "NVIDIA_API_KEY")


def get_api_key() -> str:
    name = key_env_name()
    _load_dotenv_if_needed(name)
    key = os.environ.get(name, "").strip()
    if not key:
        raise OmniError(f"{name} is not set (add it to .env)")
    return key


def _num(env: str, default, cast):
    raw = os.environ.get(env, "").strip()
    try:
        return cast(raw) if raw else default
    except ValueError:
        return default


def settings() -> dict:
    return {
        "url": os.environ.get("NEMOTRON_OMNI_URL", DEFAULT_URL),
        "model": os.environ.get("NEMOTRON_OMNI_MODEL", DEFAULT_MODEL),
        "max_tokens": _num("NEMOTRON_OMNI_MAX_TOKENS", DEFAULTS["max_tokens"], int),
        "reasoning_budget": _num("NEMOTRON_OMNI_REASONING_BUDGET", DEFAULTS["reasoning_budget"], int),
        "temperature": _num("NEMOTRON_OMNI_TEMPERATURE", DEFAULTS["temperature"], float),
        "top_p": _num("NEMOTRON_OMNI_TOP_P", DEFAULTS["top_p"], float),
        "timeout": _num("NEMOTRON_OMNI_TIMEOUT_S", 300.0, float),
    }


# ── request building ────────────────────────────────────────────────────────────────────────────
def build_messages(prompt_or_messages, system: str = "") -> list[dict]:
    if isinstance(prompt_or_messages, str):
        messages = [{"role": "user", "content": prompt_or_messages}]
    else:
        messages = [dict(m) for m in prompt_or_messages]
    if not messages:
        raise OmniError("no messages to send")
    if system:
        messages = [{"role": "system", "content": system}] + messages
    return messages


def build_payload(prompt_or_messages, *, system: str = "", stream: bool = False, model: str | None = None,
                  max_tokens: int | None = None, reasoning_budget: int | None = None,
                  temperature: float | None = None, top_p: float | None = None, **extra) -> dict:
    s = settings()
    payload = {
        "messages": build_messages(prompt_or_messages, system),
        "model": model or s["model"],
        "max_tokens": s["max_tokens"] if max_tokens is None else max_tokens,
        "reasoning_budget": s["reasoning_budget"] if reasoning_budget is None else reasoning_budget,
        "stream": bool(stream),
        "temperature": s["temperature"] if temperature is None else temperature,
        "top_p": s["top_p"] if top_p is None else top_p,
    }
    payload.update(extra)
    return payload


def build_headers(stream: bool = False, key: str | None = None) -> dict:
    return {
        "Authorization": f"Bearer {key if key is not None else get_api_key()}",
        "Accept": "text/event-stream" if stream else "application/json",
        "Content-Type": "application/json",
    }


def redacted_headers(headers: dict) -> dict:
    return {k: ("Bearer <redacted>" if k.lower() == "authorization" else v) for k, v in headers.items()}


# ── response parsing ────────────────────────────────────────────────────────────────────────────
def parse_reply(data: dict) -> OmniReply:
    if not isinstance(data, dict) or not data.get("choices"):
        raise OmniError(f"unexpected response: {str(data)[:300]}")
    choice = data["choices"][0]
    msg = choice.get("message") or {}
    return OmniReply(
        content=(msg.get("content") or "").strip(),
        reasoning=(msg.get("reasoning_content") or msg.get("reasoning") or "").strip(),
        model=data.get("model", ""),
        finish_reason=choice.get("finish_reason"),
        usage=data.get("usage") or {},
        raw=data,
    )


def parse_sse_line(line: str) -> tuple[str, str] | None:
    """One SSE line -> (kind, text) with kind 'content' or 'reasoning'; None for anything else.
    Returns ('done', '') on [DONE]."""
    line = line.strip()
    if not line.startswith("data:"):
        return None
    data = line[5:].strip()
    if data == "[DONE]":
        return ("done", "")
    try:
        delta = json.loads(data)["choices"][0].get("delta") or {}
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    if delta.get("content"):
        return ("content", delta["content"])
    r = delta.get("reasoning_content") or delta.get("reasoning")
    if r:
        return ("reasoning", r)
    return None


def _raise_for(resp: httpx.Response) -> None:
    if resp.status_code >= 400:
        try:
            body = resp.text[:300]
        except Exception:
            body = ""
        raise OmniError(f"NVIDIA API HTTP {resp.status_code}: {body}")


# ── sync calls ──────────────────────────────────────────────────────────────────────────────────
def call(prompt_or_messages, *, system: str = "", client: httpx.Client | None = None, **opts) -> OmniReply:
    """Non-streaming call. Returns the final answer with the reasoning kept separate."""
    s = settings()
    payload = build_payload(prompt_or_messages, system=system, stream=False, **opts)
    own = client is None
    client = client or httpx.Client(timeout=s["timeout"])
    try:
        resp = client.post(s["url"], headers=build_headers(False), json=payload)
        _raise_for(resp)
        return parse_reply(resp.json())
    finally:
        if own:
            client.close()


def stream(prompt_or_messages, *, system: str = "", include_reasoning: bool = False,
           client: httpx.Client | None = None, **opts) -> Iterator[tuple[str, str]]:
    """Streaming call. Yields (kind, text); reasoning pieces only when include_reasoning=True."""
    s = settings()
    payload = build_payload(prompt_or_messages, system=system, stream=True, **opts)
    own = client is None
    client = client or httpx.Client(timeout=s["timeout"])
    try:
        with client.stream("POST", s["url"], headers=build_headers(True), json=payload) as resp:
            if resp.status_code >= 400:
                resp.read()
                _raise_for(resp)
            for line in resp.iter_lines():
                item = parse_sse_line(line)
                if item is None:
                    continue
                if item[0] == "done":
                    break
                if item[0] == "content" or include_reasoning:
                    yield item
    finally:
        if own:
            client.close()


# ── async calls (for the reactor / FastAPI) ─────────────────────────────────────────────────────
async def acall(prompt_or_messages, *, system: str = "", client: httpx.AsyncClient | None = None,
                **opts) -> OmniReply:
    s = settings()
    payload = build_payload(prompt_or_messages, system=system, stream=False, **opts)
    own = client is None
    client = client or httpx.AsyncClient(timeout=s["timeout"])
    try:
        resp = await client.post(s["url"], headers=build_headers(False), json=payload)
        _raise_for(resp)
        return parse_reply(resp.json())
    finally:
        if own:
            await client.aclose()


async def astream(prompt_or_messages, *, system: str = "", include_reasoning: bool = False,
                  client: httpx.AsyncClient | None = None, **opts) -> AsyncIterator[str]:
    """Async stream of answer text. With include_reasoning=True, reasoning pieces are yielded too,
    wrapped as ('reasoning', text) tuples so callers cannot mix them up with the answer."""
    s = settings()
    payload = build_payload(prompt_or_messages, system=system, stream=True, **opts)
    own = client is None
    client = client or httpx.AsyncClient(timeout=s["timeout"])
    try:
        async with client.stream("POST", s["url"], headers=build_headers(True), json=payload) as resp:
            if resp.status_code >= 400:
                await resp.aread()
                _raise_for(resp)
            async for line in resp.aiter_lines():
                item = parse_sse_line(line)
                if item is None:
                    continue
                if item[0] == "done":
                    break
                if item[0] == "content":
                    yield item[1]
                elif include_reasoning:
                    yield item
    finally:
        if own:
            await client.aclose()


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Call NVIDIA Nemotron 3 Nano Omni (reasoning).")
    ap.add_argument("prompt", nargs="?", default="", help="user message (or read from stdin)")
    ap.add_argument("--system", default="")
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--show-reasoning", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the request (key redacted), call nothing")
    ap.add_argument("--model")
    ap.add_argument("--max-tokens", type=int)
    ap.add_argument("--reasoning-budget", type=int)
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--top-p", type=float)
    a = ap.parse_args(argv)

    prompt = a.prompt or (sys.stdin.read() if not sys.stdin.isatty() else "")
    if not prompt.strip():
        ap.error("give a prompt")
    opts = {k: v for k, v in {"model": a.model, "max_tokens": a.max_tokens,
                              "reasoning_budget": a.reasoning_budget, "temperature": a.temperature,
                              "top_p": a.top_p}.items() if v is not None}

    if a.dry_run:
        try:
            headers = redacted_headers(build_headers(a.stream))
            key_state = "set"
        except OmniError as e:
            headers = redacted_headers(build_headers(a.stream, key=""))
            key_state = str(e)
        print(json.dumps({"url": settings()["url"], "key": f"{key_env_name()}: {key_state}",
                          "headers": headers,
                          "payload": build_payload(prompt, system=a.system, stream=a.stream, **opts)}, indent=2))
        return 0

    try:
        if a.stream:
            in_reasoning = False
            for kind, text in stream(prompt, system=a.system, include_reasoning=a.show_reasoning, **opts):
                if kind == "reasoning" and not in_reasoning:
                    print("[reasoning] ", end="")
                    in_reasoning = True
                elif kind == "content" and in_reasoning:
                    print("\n[answer] ", end="")
                    in_reasoning = False
                print(text, end="", flush=True)
            print()
        else:
            r = call(prompt, system=a.system, **opts)
            if a.show_reasoning and r.reasoning:
                print("[reasoning]", r.reasoning, "\n")
            print(r.content or f"[no final answer; finish_reason={r.finish_reason}]")
            if r.usage:
                print(f"\n[model {r.model}, usage {r.usage}]", file=sys.stderr)
    except (OmniError, httpx.HTTPError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
