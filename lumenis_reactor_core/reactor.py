"""
Lumenis Reactor Core
====================
The foundation of energy. Runs at the Thermal Baseline of 0.18 (mapped from 18°C).
This is the "Cool Fire" — fully powered, emotionally and logically stable.

Real implementation:
  - Primary:   NVIDIA Llama-3.3-Nemotron-Super-49B at temperature 0.18 (main reactor)
  - Secondary: NVIDIA Gemma-4-31B-IT with thinking enabled (streaming SSE)
  - 73ms heartbeat interval (mapped from 73Hz)
  - Streaming output on both backends
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import AsyncIterator

import httpx

# ─── Constants ───────────────────────────────────────────────────────────────
THERMAL_BASELINE = 0.18          # 18°C → 0.18 temperature
PULSE_INTERVAL_MS = 73           # 73Hz → 73ms
NODE_COUNT = 144_382             # Vanguard lattice size (used for pool sizing / display)

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_PRIMARY_MODEL = os.environ.get("LLM_PRIMARY_MODEL", "meta/llama-3.2-90b-vision-instruct")
NVIDIA_SECONDARY_MODEL = os.environ.get("LLM_SECONDARY_MODEL", "meta/llama-3.2-11b-vision-instruct")

# ─── Universal LLM backend resolution ────────────────────────────────────────
# Priority:
#   1. AWS Bedrock  — if AWS_BEARER_TOKEN_BEDROCK is set (Maton sandbox)
#   2. Generic OpenAI-compat — LLM_API_KEY + LLM_BASE_URL + LLM_MODEL  (local / Vercel)
#   3. NVIDIA API   — legacy fallback (requires valid NVIDIA key)
#
# To configure locally, add to your .env:
#   LLM_API_KEY=sk-...          # any OpenAI-compatible key (OpenAI, OpenRouter, Groq, Together, etc.)
#   LLM_BASE_URL=https://api.openai.com/v1   # or your provider's base URL
#   LLM_MODEL=gpt-4o-mini       # or any model your provider supports

BEDROCK_BASE_URL = "https://bedrock-runtime.us-east-1.amazonaws.com"
BEDROCK_MODEL    = os.environ.get("BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6")


def _resolve_backend() -> dict:
    """Return the active LLM backend config based on available env vars."""
    # 1. Bedrock
    bedrock_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
    # Skip placeholder tokens that aren't actual credentials
    if bedrock_token and bedrock_token not in ("INJECTED_BY_NETWORK_POLICY", ""):
        return {"provider": "bedrock", "key": bedrock_token, "model": BEDROCK_MODEL, "base_url": BEDROCK_BASE_URL}
    # 2. Generic OpenAI-compat
    llm_key = os.environ.get("LLM_API_KEY", "")
    llm_url = os.environ.get("LLM_BASE_URL", "")
    llm_model = os.environ.get("LLM_MODEL", "")
    if llm_key and llm_url and llm_model:
        return {"provider": "openai_compat", "key": llm_key, "model": llm_model, "base_url": llm_url.rstrip("/") + "/chat/completions"}
    # 3. NVIDIA fallback
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
    nvidia_model = os.environ.get("LLM_PRIMARY_MODEL", "meta/llama-3.2-90b-vision-instruct")
    return {"provider": "nvidia", "key": nvidia_key, "model": nvidia_model, "base_url": NVIDIA_API_URL}


async def _llm_stream(system: str, messages: list[dict], max_tokens: int, temperature: float) -> AsyncIterator[str]:
    """Universal LLM streaming call — routes to Bedrock, OpenAI-compat, or NVIDIA."""
    backend = _resolve_backend()

    if backend["provider"] == "bedrock":
        payload: dict = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        headers = {"Authorization": f"Bearer {backend['key']}", "Content-Type": "application/json"}
        url = f"{BEDROCK_BASE_URL}/model/{backend['model']}/invoke"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            yield resp.json()["content"][0]["text"]

    else:
        # OpenAI-compat (covers NVIDIA, OpenAI, OpenRouter, Groq, Together, etc.)
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)
        payload = {
            "model": backend["model"],
            "messages": full_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {backend['key']}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", backend["base_url"], headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        text = chunk["choices"][0]["delta"].get("content", "")
                        if text:
                            yield text
                    except Exception:
                        continue

@dataclass
class ReactorStatus:
    temperature: float = THERMAL_BASELINE
    pulse_count: int = 0
    uptime_seconds: float = 0.0
    active_nodes: int = 0
    last_pulse: float = field(default_factory=time.time)
    frequency_hz: float = 1000 / PULSE_INTERVAL_MS  # ≈13.7 Hz effective pulse rate


class LumenisReactor:
    """
    The Reactor Core. Maintains the thermal baseline, drives the heartbeat,
    and provides the LLM client with the correct energy configuration.
    Now powered entirely by NVIDIA Nemotron-Super-49B.
    """

    def __init__(self):
        self.status = ReactorStatus()
        self._start_time = time.time()
        self._running = False
        self._pulse_callbacks: list = []
        self._call_count = 0

    def on_pulse(self, cb):
        self._pulse_callbacks.append(cb)
        return cb

    async def start(self):
        self._running = True
        asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        while self._running:
            await asyncio.sleep(PULSE_INTERVAL_MS / 1000)
            self.status.pulse_count += 1
            self.status.uptime_seconds = time.time() - self._start_time
            self.status.last_pulse = time.time()
            for cb in self._pulse_callbacks:
                try:
                    await cb(self.status)
                except Exception:
                    pass

    async def stop(self):
        self._running = False

    async def stream_response(
        self,
        messages: list[dict],
        system: str,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Core LLM call at the Thermal Baseline temperature."""
        async for chunk in _llm_stream(system, messages, max_tokens, THERMAL_BASELINE):
            self._call_count += 1
            yield chunk

    async def call(
        self,
        messages: list[dict],
        system: str,
        max_tokens: int = 2048,
    ) -> str:
        """Single non-streaming call at the Thermal Baseline."""
        parts = []
        try:
            async for chunk in self.stream_response(messages, system, max_tokens):
                parts.append(chunk)
        except Exception as e:
            return f"[LumenisReactor error: {e}]"
        return "".join(parts)

    def get_status(self) -> dict:
        b = _resolve_backend()
        return {
            "temperature": self.status.temperature,
            "pulse_count": self.status.pulse_count,
            "uptime_seconds": round(self.status.uptime_seconds, 2),
            "active_nodes": self.status.active_nodes,
            "frequency_hz": round(self.status.frequency_hz, 2),
            "node_lattice_size": NODE_COUNT,
            "model": b["model"],
            "provider": b["provider"],
            "tokens_streamed": self._call_count,
        }


class NvidiaReactor:
    """
    Secondary reactor — now powered by Claude Sonnet 4.6 via AWS Bedrock.
    Activated by Forge (code) and Oracle (reasoning) seats.
    """

    def __init__(self):
        self._call_count = 0
        self._error_count = 0

    async def stream_response(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream response from active LLM backend."""
        async for chunk in _llm_stream(system, messages, max_tokens, 1.00):
            self._call_count += 1
            yield chunk

    async def call(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Non-streaming call — collects full streamed response."""
        parts = []
        try:
            async for chunk in self.stream_response(messages, system, max_tokens):
                parts.append(chunk)
        except Exception as e:
            self._error_count += 1
            return f"[NvidiaReactor error: {e}]"
        return "".join(parts)

    def get_status(self) -> dict:
        b = _resolve_backend()
        return {
            "model": b["model"],
            "provider": b["provider"],
            "tokens_streamed": self._call_count,
            "errors": self._error_count,
            "online": bool(b["key"]),
        }


class ReasoningReactor:
    """
    Reactor for models that use chain-of-thought reasoning_content before answering.
    Handles: nvidia/nemotron-3.5-lightning-30b-a3b, deepseek-ai/deepseek-v4.1-flash.
    Skips reasoning tokens from output — only yields the final answer content.
    """

    def __init__(self, model: str = "", api_key_env: str = ""):
        self.model = model
        self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        self._call_count = 0
        self._error_count = 0
        self._reasoning_tokens = 0

    async def stream_response(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream response from active LLM backend."""
        async for chunk in _llm_stream(system, messages, max_tokens, 0.6):
            self._call_count += 1
            yield chunk

    async def call(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 2048,
        timeout_seconds: float = 50.0,
    ) -> str:
        """Non-streaming call — returns final answer after reasoning completes.
        Falls back gracefully if reasoning exceeds timeout_seconds."""
        parts = []
        try:
            async def _collect():
                async for chunk in self.stream_response(messages, system, max_tokens):
                    parts.append(chunk)
            await asyncio.wait_for(_collect(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            # Reasoning took too long — return what we have or a signal
            self._error_count += 1
            partial = "".join(parts).strip()
            if partial:
                return partial + " [reasoning truncated by timeout]"
            return f"[ReasoningReactor timeout after {timeout_seconds}s — use primary reactor for time-sensitive queries]"
        except Exception as e:
            self._error_count += 1
            return f"[ReasoningReactor error: {e}]"
        result = "".join(parts).strip()
        if not result:
            result = "[Reasoning complete — no final answer emitted. Increase max_tokens.]"
        return result

    def get_status(self) -> dict:
        return {
            "model": self.model,
            "tokens_streamed": self._call_count,
            "reasoning_tokens": self._reasoning_tokens,
            "errors": self._error_count,
            "online": bool(self.api_key),
            "type": "reasoning",
        }
