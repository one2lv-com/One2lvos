"""Desktop Integrations Hub backend (one2lvos-desktop.html -> "Integrations" window).

Owner-side only. The reactor listens on 127.0.0.1:8000; from outside it is reached only through
the Cloudflare tunnel hostnames os.one2lv.com / lumenis.one2lv.com, which sit behind Cloudflare
Access. The public guest bridge (bridge.one2lv.com, port 8095) does not proxy any of these routes.
As a second lock, a request that arrived through the tunnel without a Cloudflare Access assertion
is refused.

Everything reported here comes from a real check made at request time (or the reactor's own
live_status cache). Nothing is a canned success. Credentials stay in .env and never leave the
server.

Routes
  GET  /api/desktop/integrations        honest state of every integration the desktop shows
  GET  /api/desktop/discord/feed        latest messages in the Lumenis Discord channel (read only)
  GET  /api/desktop/ftp/list?path=      FTP server (127.0.0.1:2121), same shape as the WebDAV API
  GET  /api/desktop/ftp/get?path=
  PUT  /api/desktop/ftp/put?path=
  DELETE /api/desktop/ftp/delete?path=
  POST /api/desktop/ftp/mkdir   {path}
  POST /api/desktop/ftp/move    {from,to}
"""
from __future__ import annotations

import asyncio
import ftplib
import io
import json
import os
import posixpath
import socket
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
LISTENER_STATE = ROOT / "data" / "discord_listener_state.json"
REACTOR = "http://127.0.0.1:8000"
NETWORK_API = "http://127.0.0.1:3003/api/network"
FTP_HOST, FTP_PORT = "127.0.0.1", int(os.getenv("FTP_PORT", "2121"))
WEBDAV_PORT = int(os.getenv("WEBDAV_PORT", "8090"))
MAX_UPLOAD = 200 * 1024 * 1024

router = APIRouter()


# ── helpers ────────────────────────────────────────────────────────────────────
def _env() -> dict:
    out = {}
    try:
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    for k, v in os.environ.items():
        out.setdefault(k, v)
    return out


def _owner_gate(req: Request):
    """Refuse tunnel traffic that did not pass Cloudflare Access. Local calls (127.0.0.1) pass."""
    h = req.headers
    if h.get("cf-connecting-ip") and not (h.get("cf-access-jwt-assertion") or h.get("cf-access-authenticated-user-email")):
        raise HTTPException(403, "owner sign-in (Cloudflare Access) required")


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def _st(state: str, detail: str, **extra) -> dict:
    # state: up | partial | untested | pending | down | unknown
    return {"state": state, "detail": detail, **extra}


# ── FTP (ftplib in a worker thread) ────────────────────────────────────────────
def _ftp() -> ftplib.FTP:
    e = _env()
    if not e.get("FTP_PASS"):
        raise HTTPException(503, "FTP_PASS is not set in .env")
    f = ftplib.FTP()
    f.connect(FTP_HOST, FTP_PORT, timeout=10)
    f.login(e.get("FTP_USER", "one2lv"), e["FTP_PASS"])
    return f


def _clean(p: str | None) -> str:
    p = "/" + posixpath.normpath("/" + (p or "/").strip()).lstrip("/")
    if "\x00" in p:
        raise HTTPException(400, "bad path")
    return p


def _ftp_list(path: str) -> list:
    f = _ftp()
    try:
        items = []
        for name, facts in f.mlsd(path, facts=["type", "size", "modify"]):
            if name in (".", "..") or facts.get("type") in ("cdir", "pdir"):
                continue
            is_dir = facts.get("type") == "dir"
            mod = facts.get("modify", "")
            iso = (f"{mod[0:4]}-{mod[4:6]}-{mod[6:8]}T{mod[8:10]}:{mod[10:12]}:{mod[12:14]}Z" if len(mod) >= 14 else None)
            items.append({"name": name, "path": posixpath.join(path, name), "isDir": is_dir,
                          "size": 0 if is_dir else int(facts.get("size", 0) or 0),
                          "type": "directory" if is_dir else "file", "modified": iso})
        items.sort(key=lambda x: (not x["isDir"], x["name"].lower()))
        return items
    finally:
        try:
            f.quit()
        except Exception:
            pass


def _ftp_do(fn):
    f = _ftp()
    try:
        return fn(f)
    finally:
        try:
            f.quit()
        except Exception:
            pass


async def _run(fn, *a):
    try:
        return await asyncio.to_thread(fn, *a)
    except HTTPException:
        raise
    except ftplib.error_perm as e:
        raise HTTPException(400, f"FTP refused: {str(e)[:160]}")
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        raise HTTPException(503, f"FTP server not reachable on {FTP_HOST}:{FTP_PORT} ({type(e).__name__})")


@router.get("/api/desktop/ftp/list")
async def ftp_list(req: Request, path: str = "/"):
    _owner_gate(req)
    return await _run(_ftp_list, _clean(path))


@router.get("/api/desktop/ftp/get")
async def ftp_get(req: Request, path: str):
    _owner_gate(req)
    p = _clean(path)

    def go(f):
        buf = io.BytesIO()
        f.retrbinary("RETR " + p, buf.write)
        return buf.getvalue()
    data = await _run(_ftp_do, go)
    fname = (p.rsplit("/", 1)[-1] or "download").replace('"', "_")
    return Response(data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"', "X-Content-Type-Options": "nosniff"})


@router.put("/api/desktop/ftp/put")
async def ftp_put(req: Request, path: str):
    _owner_gate(req)
    p = _clean(path)
    body = await req.body()
    if len(body) > MAX_UPLOAD:
        raise HTTPException(413, "file too large (200 MB max)")
    await _run(_ftp_do, lambda f: f.storbinary("STOR " + p, io.BytesIO(body)))
    return {"success": True}


@router.delete("/api/desktop/ftp/delete")
async def ftp_delete(req: Request, path: str):
    _owner_gate(req)
    p = _clean(path)
    if p == "/":
        raise HTTPException(400, "refusing to delete the FTP root")

    def go(f):
        try:
            f.delete(p)
        except ftplib.error_perm:
            f.rmd(p)  # empty folders only
    await _run(_ftp_do, go)
    return {"success": True}


@router.post("/api/desktop/ftp/mkdir")
async def ftp_mkdir(req: Request):
    _owner_gate(req)
    p = _clean((await req.json()).get("path"))
    await _run(_ftp_do, lambda f: f.mkd(p))
    return {"success": True}


@router.post("/api/desktop/ftp/move")
async def ftp_move(req: Request):
    _owner_gate(req)
    b = await req.json()
    src, dst = _clean(b.get("from")), _clean(b.get("to"))
    await _run(_ftp_do, lambda f: f.rename(src, dst))
    return {"success": True}


# ── Discord feed (read only, bot token stays here) ─────────────────────────────
_feed_cache: dict = {"at": 0.0, "data": None}


@router.get("/api/desktop/discord/feed")
async def discord_feed(req: Request, limit: int = 25):
    _owner_gate(req)
    limit = max(1, min(int(limit), 50))
    now = time.time()
    if _feed_cache["data"] and now - _feed_cache["at"] < 8:
        return _feed_cache["data"]
    e = _env()
    tok, cid = e.get("DISCORD_BOT_TOKEN"), e.get("DISCORD_CHANNEL_ID")
    if not tok or not cid:
        raise HTTPException(503, "DISCORD_BOT_TOKEN / DISCORD_CHANNEL_ID missing from .env")
    h = {"Authorization": "Bot " + tok}
    async with httpx.AsyncClient(timeout=10) as c:
        ch = await c.get(f"https://discord.com/api/v10/channels/{cid}", headers=h)
        r = await c.get(f"https://discord.com/api/v10/channels/{cid}/messages", params={"limit": limit}, headers=h)
    if r.status_code != 200:
        return JSONResponse({"ok": False, "status": r.status_code,
                             "error": "Discord refused the read (bot lacks View Channel / Read Message History)"
                             if r.status_code == 403 else f"Discord returned HTTP {r.status_code}"}, status_code=502)
    chj = ch.json() if ch.status_code == 200 else {}
    msgs = []
    for m in r.json():
        a = m.get("author") or {}
        msgs.append({"id": m.get("id"), "at": m.get("timestamp"), "author": a.get("global_name") or a.get("username"),
                     "bot": bool(a.get("bot")), "content": (m.get("content") or "")[:1500],
                     "attachments": [x.get("filename") for x in m.get("attachments", [])][:5],
                     "embeds": len(m.get("embeds") or [])})
    data = {"ok": True, "channel": chj.get("name"), "guild_id": chj.get("guild_id"),
            "open_url": f"https://discord.com/channels/{chj.get('guild_id')}/{cid}" if chj.get("guild_id") else None,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "messages": msgs}
    _feed_cache.update(at=now, data=data)
    return data


# ── KAI 9000 / OpenAI-compatible access (owner only, shown on click) ──────────────────────────
@router.get("/api/desktop/kai_access")
async def kai_access(req: Request, reveal: int = 0):
    _owner_gate(req)
    f = ROOT / "data" / "secrets" / "kai_openai_key.txt"
    key = f.read_text().strip() if f.exists() else ""
    out = {"base_url": "https://bridge.one2lv.com/openai/v1", "model": "lumenis-council", "key_present": bool(key),
           "note": "Goes through the real reactor council, session history and memory recall; not a raw NVIDIA call."}
    if reveal and key:
        out["api_key"] = key
    return JSONResponse(out, headers={"Cache-Control": "no-store"})


# ── Integration states ─────────────────────────────────────────────────────────
async def _get_json(c, url, **kw):
    try:
        r = await c.get(url, **kw)
        return r.status_code, (r.json() if "json" in r.headers.get("content-type", "") else None)
    except Exception as e:
        return 0, {"error": type(e).__name__}


def _pgrep(pattern: str) -> bool:
    try:
        for p in Path("/proc").iterdir():
            if p.name.isdigit():
                try:
                    if pattern in (p / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "ignore"):
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


@router.get("/api/desktop/integrations")
async def integrations(req: Request):
    _owner_gate(req)
    e = _env()
    out: dict = {}
    async with httpx.AsyncClient(timeout=8) as c:
        (ls_code, live), (v_code, vision), (eng_code, tools), (net_code, conns), (gm_code, guest) = await asyncio.gather(
            _get_json(c, REACTOR + "/api/live_status"),
            _get_json(c, REACTOR + "/api/vision/status"),
            _get_json(c, REACTOR + "/engine/tools"),
            _get_json(c, NETWORK_API + "/connections"),
            _get_json(c, REACTOR + "/api/guest_mode"),
        )
    systems = (live or {}).get("systems", {}) if ls_code == 200 else {}

    # Discord text
    try:
        lst = json.loads(LISTENER_STATE.read_text())
    except Exception:
        lst = {}
    running = _pgrep("discord_listener.py")
    d = systems.get("Discord", {})
    out["discord_text"] = _st(
        ("up" if running and d.get("state") == "up" else "partial" if running else "down"),
        ("listener running" if running else "listener NOT running") + (f"; connected since {lst['connected_at']}" if lst.get("connected_at") else "")
        + (f"; live status: {d.get('detail')}" if d else ""),
        commands=["!lumenis <message>"])
    dv = systems.get("Discord voice", {})
    out["discord_voice"] = _st(
        "down" if not lst.get("voice_available") else ("up" if dv.get("state") == "up" else "untested"),
        dv.get("detail") or ("voice code loaded in the listener" if lst.get("voice_available") else "voice code not loaded"),
        connected=bool(lst.get("voice_connected")), listening=bool(lst.get("voice_listening")),
        commands=["!lumenis join", "!lumenis listen", "!lumenis stop", "!lumenis say <text>", "!lumenis voice", "!lumenis leave"],
        note="Commands are typed by you in Discord; the desktop cannot issue them for you.")

    # Twitch
    tw = systems.get("Twitch", {})
    chan = e.get("TWITCH_CHANNEL", "").strip().lstrip("#")
    out["twitch"] = _st(
        "partial" if chan else "down",
        (f"player embed for channel '{chan}' needs no token" if chan else "TWITCH_CHANNEL not set")
        + (f"; Twitch API: {tw.get('state')} ({tw.get('detail')})" if tw else ""),
        channel=chan or None, api_state=tw.get("state"))

    # Files: WebDAV + FTP
    builtin = next((x for x in (conns or []) if isinstance(x, dict) and x.get("id") == "one2lv-files"), None) if net_code == 200 else None
    wd_port = _port_open(WEBDAV_PORT)
    out["webdav"] = _st(
        "up" if wd_port and builtin and builtin.get("status") == "connected" else "partial" if wd_port else "down",
        f"WebDAV server {'listening' if wd_port else 'NOT listening'} on 127.0.0.1:{WEBDAV_PORT}; "
        + (f"Network Manager connection '{builtin.get('name')}' is {builtin.get('status')}" if builtin
           else f"Network Manager API {'answered but has no built-in connection' if net_code == 200 else 'not reachable'}"),
        connection_id="one2lv-files" if builtin else None, port=WEBDAV_PORT)
    ftp_port = _port_open(FTP_PORT)
    ftp_login = None
    if ftp_port and e.get("FTP_PASS"):
        try:
            await asyncio.to_thread(lambda: _ftp().quit())
            ftp_login = True
        except Exception:
            ftp_login = False
    out["ftp"] = _st(
        "up" if ftp_login else "partial" if ftp_port else "down",
        f"FTP server {'listening' if ftp_port else 'NOT listening'} on {FTP_HOST}:{FTP_PORT} (localhost only)"
        + ("; login with FTP_USER/FTP_PASS from .env works" if ftp_login else "; login FAILED" if ftp_login is False
           else "; FTP_PASS missing in .env" if not e.get("FTP_PASS") else ""),
        connection_id="one2lv-ftp", port=FTP_PORT)

    # Vision
    if v_code == 200 and isinstance(vision, dict):
        s = vision.get("session") or {}
        out["vision"] = _st("up" if s.get("active") else "partial",
                            (f"session '{s.get('label')}' active" if s.get("active") else
                             (f"no active session; last one analysed {s.get('analyzed', 0)} frames" if s else "no session yet"))
                            + f"; model {vision.get('model')}", page="/vision")
    else:
        out["vision"] = _st("pending", f"vision routes not loaded in the running reactor (HTTP {v_code})", page=None)

    # NVIDIA lab tools (nimlab.*) as the running tool engine sees them
    tl = (tools or {}).get("tools", []) if eng_code == 200 and isinstance(tools, dict) else []
    nim = [t.get("name") for t in tl if isinstance(t, dict) and str(t.get("name", "")).startswith("nimlab")]
    on_disk = (ROOT / "lumenis_reactor_core" / "nimlab_tools.py").exists()
    out["nimlab"] = _st(
        "up" if nim else ("pending" if on_disk else "down"),
        (f"{len(nim)} nimlab tools registered in the running tool engine" if nim else
         ("installed on disk but NOT loaded by the running reactor (needs a reactor restart)" if on_disk else "not installed")),
        tools=nim[:40])

    nv = systems.get("NVIDIA", {})
    out["nvidia"] = _st(nv.get("state", "unknown"), nv.get("detail", "no live status"))
    out["speech"] = _st("untested" if lst.get("voice_available") else "pending",
                        "Magpie TTS + Parakeet ASR on NVIDIA hosted gRPC, tested from the server; used by Discord voice")

    # How to reach things
    out["access"] = {
        "desktop": "https://os.one2lv.com/desktop",
        "chat": "https://os.one2lv.com/lumenis-chat",
        "council_page": "https://os.one2lv.com/",
        "gate": "Cloudflare Access (owner sign-in)",
        "guest_bridge": "https://bridge.one2lv.com (app login; guests get chat only)",
        "guest_mode_supported": bool((guest or {}).get("supported")) if gm_code == 200 else None,
    }
    return {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "live_status_at": (live or {}).get("checked_at"), "integrations": out}
