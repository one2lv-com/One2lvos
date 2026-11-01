"""
Lumenis Reactor Core - aiohttp version (offline compatible)
============================================================
Modified to use aiohttp instead of httpx for environments without internet access.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import AsyncIterator

import aiohttp

# ─── Constants ───────────────────────────────────────────────────────────────
THERMAL_BASELINE = 0.18
PULSE_INTERVAL_MS = 73
NODE_COUNT = 144_382

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_PRIMARY_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"
NVIDIA_SECONDARY_MODEL = "google/gemma-4-31b-it"

@dataclass
class ReactorStatus:
    temperature: float = THERMAL_BASELINE
    pulse_count: int = 0
    uptime_seconds: float = 0.0
    active_nodes: int = 0
    last_pulse: float = field(default_factory=time.time)
    frequency_hz: float = 1000 / PULSE_INTERVAL_MS


class LumenisReactor:
    """Reactor Core using aiohttp for offline compatibility."""

    def __init__(self):
        self.api_key = os.environ.get("NVIDIA_API_KEY", "")
        self.model = NVIDIA_PRIMARY_MODEL
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
        """Stream response using aiohttp instead of httpx."""
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            "temperature": THERMAL_BASELINE,
            "top_p": 0.95,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(NVIDIA_API_URL, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    if not line_str.startswith("data: "):
                        continue
                    data = line_str[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        text = delta.get("content", "")
                        if text:
                            self._call_count += 1
                            yield text
                    except Exception:
                        continue

    async def call(
        self,
        messages: list[dict],
        system: str,
        max_tokens: int = 2048,
    ) -> str:
        """Single non-streaming call."""
        parts = []
        try:
            async for chunk in self.stream_response(messages, system, max_tokens):
                parts.append(chunk)
        except Exception as e:
            return f"[LumenisReactor error: {e}]"
        return "".join(parts)

    def get_status(self) -> dict:
        return {
            "temperature": self.status.temperature,
            "pulse_count": self.status.pulse_count,
            "uptime_seconds": round(self.status.uptime_seconds, 2),
            "active_nodes": self.status.active_nodes,
            "frequency_hz": round(self.status.frequency_hz, 2),
            "node_lattice_size": NODE_COUNT,
            "model": self.model,
            "tokens_streamed": self._call_count,
            "powered_by": "NVIDIA (aiohttp)",
        }


class NvidiaReactor:
    """Secondary reactor using aiohttp."""

    def __init__(self):
        self.api_key = os.environ.get("NVIDIA_API_KEY", "")
        self.model = NVIDIA_SECONDARY_MODEL
        self._call_count = 0
        self._error_count = 0

    async def stream_response(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream tokens using aiohttp."""
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": max_tokens,
            "temperature": 1.00,
            "top_p": 0.95,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": True},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        in_thinking = False
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(NVIDIA_API_URL, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    if not line_str.startswith("data: "):
                        continue
                    data = line_str[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]

                        if delta.get("reasoning_content"):
                            in_thinking = True
                            continue
                        if in_thinking and delta.get("content"):
                            in_thinking = False

                        text = delta.get("content", "")
                        if text:
                            self._call_count += 1
                            yield text
                    except Exception:
                        continue

    async def call(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Non-streaming call."""
        parts = []
        try:
            async for chunk in self.stream_response(messages, system, max_tokens):
                parts.append(chunk)
        except Exception as e:
            self._error_count += 1
            return f"[NvidiaReactor error: {e}]"
        return "".join(parts)

    def get_status(self) -> dict:
        return {
            "model": self.model,
            "tokens_streamed": self._call_count,
            "errors": self._error_count,
            "online": bool(self.api_key),
        }
