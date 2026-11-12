"""
Live status snapshot for Lumenis.

Every council turn gets a short block built from REAL checks of the systems Lumenis
talks about (Discord, Supabase, Astra, Twitch, NVIDIA, tool engine, Who Dat, dream store).
He must describe the system from this block, not from his persona or old memories.

The snapshot is cached (TTL 60 s) and refreshed in the background by the reactor, so a
chat turn only reads the cache and never waits on these checks. Every check is read-only:
nothing is posted, written or bought. Keys are read from the environment and never
appear in the snapshot.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from pathlib import Path

import httpx

TTL = float(os.getenv("LUMENIS_STATUS_TTL", "60"))
ROOT = Path(__file__).resolve().parent.parent
LISTENER_STATE = ROOT / "data" / "discord_listener_state.json"
DREAM_DB = ROOT / "dream_memory" / "lumenis_dreams_vectors.db"

_cache: dict = {"at": 0.0, "snap": None}
_lock = asyncio.Lock()


def _env(k: str) -> str:
    return (os.environ.get(k) or "").strip().strip('"')


def _ok(state: str, detail: str) -> dict:
    return {"state": state, "detail": detail}


# ── individual checks (each returns {"state": up|down|partial|unknown|none, "detail": str}) ──

async def _discord(c: httpx.AsyncClient) -> dict:
    tok, ch = _env("DISCORD_BOT_TOKEN"), _env("DISCORD_CHANNEL_ID")
    if not tok or not ch:
        return _ok("down", "DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID not set")
    r = await c.get(f"https://discord.com/api/v10/channels/{ch}/messages?limit=1",
                    headers={"Authorization": f"Bot {tok}"})
    read = "works" if r.status_code == 200 else f"FAILS (HTTP {r.status_code})"
    post = "UNTESTED (no successful post recorded)"
    listener = "no listener state file"
    try:
        st = json.loads(LISTENER_STATE.read_text())
        if st.get("last_post_ok_at"):
            post = f"works (last successful reply by the listener at {st['last_post_ok_at']})"
        listener = f"listener last connected {st.get('connected_at', 'never')}"
    except Exception:
        pass
    state = "partial" if r.status_code == 200 else "down"
    if r.status_code == 200 and post.startswith("works"):
        state = "up"
    return _ok(state, f"read channel: {read}; post: {post}; {listener}")


async def _discord_voice(c: httpx.AsyncClient) -> dict:
    """Discord voice (discord_voice.py): what the listener reports, never more."""
    try:
        st = json.loads(LISTENER_STATE.read_text())
    except Exception:
        return _ok("unknown", "no listener state file")
    if not st.get("voice_available"):
        return _ok("down", "voice code not loaded in the running listener")
    where = (f"in voice channel '{st.get('voice_channel')}', "
             f"{'listening to the owner only' if st.get('voice_listening') else 'not listening (deafened)'}"
             if st.get("voice_connected") else "not in a voice channel (owner types '!lumenis join')")
    spoke = (f"last spoke in Discord at {st['voice_last_spoke_at']}" if st.get("voice_last_spoke_at")
             else "speaking in Discord UNTESTED (never done yet)")
    heard = (f"last heard the owner at {st['voice_last_heard_at']}" if st.get("voice_last_heard_at")
             else "hearing in Discord UNTESTED (never done yet)")
    state = "up" if st.get("voice_last_spoke_at") and st.get("voice_last_heard_at") else "partial"
    return _ok(state, f"installed (Magpie TTS + Parakeet ASR tested locally, owner-only, on command); {where}; "
                      f"{spoke}; {heard}")


async def _supabase(c: httpx.AsyncClient) -> dict:
    url, key = _env("SUPABASE_URL").rstrip("/"), _env("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return _ok("down", "SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
    ref = url.split("//")[-1].split(".")[0]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Prefer": "count=exact", "Range": "0-0"}
    parts, bad = [], 0
    for t in ("memories", "reactor_memory", "lumenis_dreams"):
        r = await c.get(f"{url}/rest/v1/{t}?select=*&limit=1", headers=h)
        if r.status_code in (200, 206):
            n = (r.headers.get("content-range") or "*/?").split("/")[-1]
            parts.append(f"{t}: {n} rows")
        elif r.status_code == 404:
            parts.append(f"{t}: table does NOT exist")
        else:
            bad += 1
            parts.append(f"{t}: read FAILS (HTTP {r.status_code})")
    state = "down" if bad == 3 else ("partial" if bad else "up")
    return _ok(state, f"project {ref}, service-key reads: " + "; ".join(parts))


async def _astra(c: httpx.AsyncClient) -> dict:
    try:
        from . import astra_vectors as av
    except Exception as e:
        return _ok("down", f"astra module not loaded ({type(e).__name__})")
    if not av.configured():
        return _ok("down", "Astra not configured")
    cfg = av._cfg()
    r = await av._astra(cfg["collection"], {"countDocuments": {}}, timeout=10)
    if not r.get("ok"):
        return _ok("down", f"collection {cfg['collection']}: count FAILS ({str(r.get('error'))[:120]})")
    st = r["data"].get("status", {})
    n = st.get("count")
    more = " or more (count capped by Astra)" if st.get("moreData") else ""
    return _ok("up", f"collection {cfg['collection']} reachable, {n}{more} documents")


async def _twitch(c: httpx.AsyncClient) -> dict:
    tok = _env("TWITCH_OAUTH_TOKEN").replace("oauth:", "")
    code = "no Twitch code is loaded in the reactor"
    if not tok:
        return _ok("down", f"no TWITCH_OAUTH_TOKEN; {code}")
    r = await c.get("https://id.twitch.tv/oauth2/validate", headers={"Authorization": f"OAuth {tok}"})
    if r.status_code == 200:
        return _ok("partial", f"token valid; {code}, so Twitch chat is NOT connected")
    return _ok("down", f"token INVALID (HTTP {r.status_code}); {code}")


_nv_cache: dict = {"at": 0.0, "res": None}


async def _nvidia(c: httpx.AsyncClient) -> dict:
    """A 1-token chat call on the fast model (the model list answers 200 even for a fake key, so it
    proves nothing). Cached for 5 minutes to keep calls low."""
    key = _env("NVIDIA_API_KEY")
    if not key:
        return _ok("down", "NVIDIA_API_KEY not set")
    if _nv_cache["res"] and time.time() - _nv_cache["at"] < 300:
        return _nv_cache["res"]
    fast = _env("LUMENIS_ROUTE_MODEL") or "nvidia/nemotron-3.5-bolt-e4b"   # cheapest real call
    model = _env("LLM_PRIMARY_MODEL") or "default"
    r = await c.post("https://integrate.api.nvidia.com/v1/chat/completions",
                     headers={"Authorization": f"Bearer {key}"},
                     json={"model": fast, "messages": [{"role": "user", "content": "ok"}], "max_tokens": 1})
    if r.status_code == 200:
        res = _ok("up", f"key answered a real 1-token call on {fast}; council model {model}; fast-path model "
                        f"{_env('LUMENIS_FAST_MODEL') or 'nvidia/nemotron-3-ultra-550b-a55b'}; routing model {fast}")
    else:
        res = _ok("down", f"1-token call on {fast} FAILS (HTTP {r.status_code})")
    _nv_cache.update(at=time.time(), res=res)
    return res


async def _tool_engine(c: httpx.AsyncClient) -> dict:
    try:
        from . import tool_engine as te
        cat = te.load_catalog() or {}
        n = len(cat.get("tools", []))
        return _ok("up" if n else "partial",
                   f"loaded; {n} tools in the learned catalog (local tools run here; sfcompute tools are read-only)")
    except Exception as e:
        return _ok("down", f"not loaded ({type(e).__name__})")


async def _whodat(c: httpx.AsyncClient) -> dict:
    try:
        from whodat.api import get_registry
        reg = get_registry()
        return _ok("up", f"registry present, vault {'unlocked' if reg.vault_unlocked else 'locked'}; "
                         "identity is only verified by a signed Who Dat handshake, never by what someone types")
    except Exception as e:
        return _ok("down", f"registry not available ({type(e).__name__})")


async def _dreams(c: httpx.AsyncClient) -> dict:
    if not DREAM_DB.exists():
        return _ok("none", "local dream store not found")
    try:
        con = sqlite3.connect(f"file:{DREAM_DB}?mode=ro", uri=True, timeout=3)
        n = con.execute("SELECT COUNT(*) FROM dreams").fetchone()[0]
        con.close()
        return _ok("up", f"local dream-only store has {n} records (dreams, not facts)")
    except Exception as e:
        return _ok("partial", f"dream store unreadable ({type(e).__name__})")


CHECKS = {
    "Discord": _discord, "Discord voice": _discord_voice, "Supabase": _supabase, "Astra memory": _astra, "Twitch": _twitch,
    "NVIDIA": _nvidia, "Tool engine": _tool_engine, "Who Dat": _whodat, "Dream store": _dreams,
}
STATIC = {
    "SF Compute GPU": _ok("none", "not checked in this block; no GPU job has been started from here. The tool engine "
                              "can list SF Compute nodes (read-only) when asked"),
}


async def _run(name, fn, c) -> tuple[str, dict]:
    try:
        return name, await asyncio.wait_for(fn(c), timeout=12)
    except asyncio.TimeoutError:
        return name, _ok("unknown", "check timed out")
    except Exception as e:
        return name, _ok("unknown", f"check failed ({type(e).__name__})")


async def refresh() -> dict:
    t0 = time.time()
    async with httpx.AsyncClient(timeout=10) as c:
        res = await asyncio.gather(*(_run(n, f, c) for n, f in CHECKS.items()))
    try:
        from zoneinfo import ZoneInfo
        from datetime import datetime
        stamp = datetime.now(ZoneInfo(os.getenv("LUMENIS_TZ", "America/Los_Angeles"))).strftime("%Y-%m-%d %I:%M:%S %p %Z")
    except Exception:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    snap = {"checked_at": stamp, "checked_ts": time.time(),
            "took_s": round(time.time() - t0, 1), "systems": dict(res) | STATIC}
    _cache.update(at=time.time(), snap=snap)
    return snap


async def snapshot(max_age: float = TTL, wait: bool = True) -> dict | None:
    """Cached snapshot. If stale, refresh (once, under a lock). With wait=False a stale
    snapshot is returned at once and the refresh runs in the background."""
    snap = _cache["snap"]
    if snap and time.time() - _cache["at"] < max_age:
        return snap
    if not wait and snap:
        if not _lock.locked():
            asyncio.create_task(_locked_refresh())
        return snap
    return await _locked_refresh()


async def _locked_refresh() -> dict:
    async with _lock:
        if _cache["snap"] and time.time() - _cache["at"] < 5:
            return _cache["snap"]
        return await refresh()


async def background_loop(period: float = 50.0):
    while True:
        try:
            await _locked_refresh()
        except Exception as e:  # never let the loop die
            print(f"⚠ live status refresh failed: {type(e).__name__}")
        await asyncio.sleep(period)


def block(snap: dict | None, identity: str = "") -> str:
    """Text block injected into the council's prompts."""
    if not snap:
        return ("LIVE STATUS: unavailable this turn (checks have not run). Say you can't confirm the state "
                "of any system right now.")
    age = int(time.time() - snap["checked_ts"])
    lines = [f"LIVE STATUS (real checks at {snap['checked_at']}, {age}s ago; this is the ONLY source for "
             f"what is up, down or untested):"]
    for name, s in snap["systems"].items():
        lines.append(f"- {name}: {s['state'].upper()} - {s['detail']}")
    if identity:
        lines.append(f"- Identity of the person in THIS chat: {identity}")
    return "\n".join(lines)
