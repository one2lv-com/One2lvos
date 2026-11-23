"""Council swarm: split a multi-part chat message into independent parts and answer them in parallel.

This is the real, LLM-backed swarm for the council's chat path. It follows the same three steps as ARIA's
SwarmCoordinator (aria/swarm/coordinator.py: decompose -> run in parallel -> combine), but runs inside the
reactor's event loop on the council's own seats, so each seat answers with its own model and the browser or
Discord never needs a key. (The WorkerNode / TaskPulse classes next to this file are a file-queue simulation
with random sleeps; they make no model calls and are not used here.)

Flow, for each lumenis-chat message:
  1. worth_trying(): short or single-ask messages never reach the swarm (they keep the fast path).
  2. decompose(): one small call on the routing model, run *at the same time* as Sentinel and Navigator, so
     it adds no wait. It returns 1-4 parts, each tagged with the seat that should answer it.
  3. If there are 2+ parts and the message is eligible (no tools, memory, dreams, identity or system
     questions: those keep the full council), run(): every part goes to its seat concurrently
     (asyncio.gather), each with its own time limit.
  4. The answers are combined in order, each under the seat (and model) that wrote it.

Switch off with LUMENIS_SWARM=0.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Awaitable, Callable

SWARM_SEATS = ("oracle", "forge", "weaver", "architect")
GUEST_SEATS = ("oracle", "forge", "weaver")
MAX_PARTS = 4
PART_TIMEOUT_S = float(os.getenv("LUMENIS_SWARM_PART_TIMEOUT", "45"))
RETRY_TIMEOUT_S = float(os.getenv("LUMENIS_SWARM_RETRY_TIMEOUT", "25"))
FALLBACK_SEAT = "weaver"   # primary chat model; answers a part when its own seat returned no answer
# A seat reply that is a backend error or an empty-answer marker, never an answer.
# ("[Reasoning complete — no final answer emitted...]" = a reasoning model spent its whole token budget
# thinking; seen live on Oracle/Lightning 2026-11-16.)
_NOT_AN_ANSWER = re.compile(r"^\[(ReasoningReactor|LumenisReactor|NvidiaReactor|Reasoning complete)")
DECOMPOSE_TIMEOUT_S = float(os.getenv("LUMENIS_SWARM_DECOMPOSE_TIMEOUT", "12"))

SEAT_TITLES = {"oracle": "Oracle", "forge": "Forge", "weaver": "Weaver", "architect": "Architect"}

DECOMPOSE_SYSTEM = """You split a chat message into independent parts for a council of AI seats.
Return ONLY JSON: {"parts": [{"task": "<one self-contained request>", "seat": "<seat>"}]}
Rules:
- Only split when the message holds two or more SEPARATE requests that can each be answered on their own.
  One question, one request, or one request with details = exactly one part (copy the message as the task).
- At most 4 parts. Keep each task's wording close to the user's; include any detail it needs.
- Seats: "oracle" = facts, explanations, analysis, advice, game strategy; "forge" = code, commands,
  technical or computer steps and checklists; "weaver" = creative writing (poems, stories), casual chat;
  "architect" = how a software system should be designed."""

_MULTI_HINT = re.compile(
    r"(\b(and|also|plus|then|another|second|third|both)\b|[,;:]|\?.*\?|\b(two|three|four|2|3|4) (things|parts|questions)\b|"
    r"(^|\n)\s*(\d+[.)]|[-*•]) )", re.I)


def enabled() -> bool:
    return os.getenv("LUMENIS_SWARM", "1") != "0"


def worth_trying(message: str) -> bool:
    """Cheap local check: only longer messages with a sign of several asks go to the decomposer."""
    words = len((message or "").split())
    return words >= 14 and bool(_MULTI_HINT.search(message or ""))


def parse_parts(raw: str, guest: bool = False) -> list[dict]:
    """Parse the decomposer's JSON into [{'task','seat'}]; anything malformed means 'do not split'."""
    raw = (raw or "").strip()
    a, b = raw.find("{"), raw.rfind("}")
    if a < 0 or b <= a:
        return []
    try:
        data = json.loads(raw[a:b + 1])
    except Exception:
        return []
    parts = data.get("parts") if isinstance(data, dict) else None
    if not isinstance(parts, list):
        return []
    allowed = GUEST_SEATS if guest else SWARM_SEATS
    out = []
    for p in parts[:MAX_PARTS]:
        if not isinstance(p, dict):
            continue
        task = str(p.get("task", "")).strip()
        seat = str(p.get("seat", "")).strip().lower()
        if not task:
            continue
        out.append({"task": task[:1200], "seat": seat if seat in allowed else "oracle"})
    return out


async def decompose(message: str, call: Callable[..., Awaitable[str]], model: str, guest: bool = False) -> list[dict]:
    """One small routing-model call. Returns the parts, or [] on any failure (= no swarm)."""
    try:
        raw = await asyncio.wait_for(
            call(DECOMPOSE_SYSTEM, [{"role": "user", "content": message[:3000]}], max_tokens=400,
                 temperature=0.0, model=model), timeout=DECOMPOSE_TIMEOUT_S)
    except Exception:
        return []
    return parse_parts(raw, guest=guest)


async def run(parts: list[dict], message: str, call_seat: Callable[..., Awaitable[str]],
              seat_model: Callable[[str], str], notify: Callable[[str, str], Awaitable[None]],
              context: str = "") -> dict:
    """Answer every part on its own seat at the same time. Returns the combined text and timings."""
    t0 = time.monotonic()

    async def one(i: int, part: dict) -> dict:
        seat = part["seat"]
        await notify(seat, f"Swarm part {i + 1}/{len(parts)} [{seat_model(seat).split('/')[-1]}]...")
        ts = time.monotonic()
        extra = (f"This is part {i + 1} of {len(parts)} of a longer message; other seats answer the other parts "
                 f"at the same time. Answer ONLY this part, completely but concisely, in plain prose or a short "
                 f"list. Do not greet, do not mention the other parts or the council.\n\nFull message for "
                 f"context:\n{message[:2000]}" + (f"\n\n{context}" if context else ""))
        timed_out = False
        try:
            # "complex" = the largest token budget, so reasoning seats (Oracle, Forge) have room to answer
            text = await asyncio.wait_for(call_seat(seat, part["task"], extra, "complex"), timeout=PART_TIMEOUT_S)
            ok = _is_answer(text)
        except asyncio.TimeoutError:
            text, ok, timed_out = f"(The {SEAT_TITLES.get(seat, seat)} seat did not answer within {PART_TIMEOUT_S:.0f} s.)", False, True
        except Exception as e:
            text, ok = f"(The {SEAT_TITLES.get(seat, seat)} seat failed: {type(e).__name__}.)", False
        answered_by = seat
        if not ok and not timed_out and seat != FALLBACK_SEAT:
            # One retry on the primary model, so a raw error or empty-answer marker never reaches the reply.
            await notify(seat, f"✗ no answer for part {i + 1}; handing it to {SEAT_TITLES[FALLBACK_SEAT]}")
            try:
                retry = await asyncio.wait_for(call_seat(FALLBACK_SEAT, part["task"], extra, "medium"),
                                               timeout=RETRY_TIMEOUT_S)
                if _is_answer(retry):
                    text, ok, answered_by = retry, True, FALLBACK_SEAT
            except Exception:
                pass
            if not ok:
                text = f"(The {SEAT_TITLES.get(seat, seat)} seat returned no answer for this part.)"
        secs = round(time.monotonic() - ts, 2)
        await notify(seat, ("✓" if ok else "✗") + f" part {i + 1} in {secs}s"
                     + (f" (answered by {SEAT_TITLES[answered_by]})" if answered_by != seat else ""))
        return {"part": i + 1, "seat": answered_by, "assigned_seat": seat, "model": seat_model(answered_by),
                "task": part["task"], "text": text.strip(), "ok": ok, "seconds": secs}

    results = await asyncio.gather(*(one(i, p) for i, p in enumerate(parts)))
    return {"results": list(results), "parallel_s": round(time.monotonic() - t0, 2),
            "text": combine(list(results))}


def _is_answer(text: Optional[str]) -> bool:
    t = (text or "").strip()
    return bool(t) and not _NOT_AN_ANSWER.match(t)


def combine(results: list[dict]) -> str:
    """One reply, in the user's order, each part under the seat that wrote it."""
    blocks = []
    for r in results:
        title = SEAT_TITLES.get(r["seat"], r["seat"].title())
        blocks.append(f"**{title}** ({r['model'].split('/')[-1]}) on \"{_short(r['task'])}\":\n{r['text']}")
    return "\n\n".join(blocks)


def _short(task: str, n: int = 70) -> str:
    task = " ".join(task.split())
    return task if len(task) <= n else task[: n - 1].rstrip() + "…"
