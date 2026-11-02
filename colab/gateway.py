#!/usr/bin/env python3
"""
One2lvOS Colab gateway.

One public port in front of everything the Colab notebook starts:

  /login            password page (the password comes from Colab secrets or a prompt)
  /                 -> /desktop
  /terminal/...     -> ttyd (real Ubuntu 26 shell), HTTP and WebSocket
  /colab/...        -> files in this folder (the desktop add-on script)
  everything else   -> the Lumenis reactor (desktop, lumenis-chat, /ws, /api/...)

Every path except /login needs the session cookie, WebSockets included, so the
public tunnel URL never exposes the shell or the reactor without the password.

Environment:
  O2_GATEWAY_PASSWORD  required
  O2_GATEWAY_HOST      default 127.0.0.1
  O2_GATEWAY_PORT      default 8090
  O2_REACTOR_URL       default http://127.0.0.1:8000
  O2_TTYD_URL          default http://127.0.0.1:7681
"""

import asyncio
import hmac
import html
import os
import secrets
import time
from pathlib import Path

import aiohttp
from aiohttp import web, WSMsgType

HERE = Path(__file__).resolve().parent
PASSWORD = os.environ.get("O2_GATEWAY_PASSWORD", "")
HOST = os.environ.get("O2_GATEWAY_HOST", "127.0.0.1")
PORT = int(os.environ.get("O2_GATEWAY_PORT", "8090"))
REACTOR = os.environ.get("O2_REACTOR_URL", "http://127.0.0.1:8000").rstrip("/")
TTYD = os.environ.get("O2_TTYD_URL", "http://127.0.0.1:7681").rstrip("/")
COOKIE = "o2_colab"
SESSION_TTL = 12 * 3600

_sessions: dict[str, float] = {}
_fail: dict[str, list[float]] = {}

HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
       "transfer-encoding", "upgrade", "host", "content-length", "content-encoding"}
DESKTOP_PATHS = {"/desktop", "/os", "/webos"}
ADDON_TAG = '<script src="/colab/o2-colab.js"></script>'

LOGIN_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>One2lvOS · Colab</title>
<style>body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:radial-gradient(circle at 30% 20%,#1b0b3a,#05020c);font-family:system-ui,sans-serif;color:#ccd6f6}
form{background:#0e0620;border:1px solid rgba(0,240,255,.25);border-radius:14px;padding:28px 30px;width:300px;
box-shadow:0 0 40px rgba(0,240,255,.12)}h1{margin:0 0 4px;font-size:1.1rem;letter-spacing:4px;color:#00f0ff}
p{margin:0 0 18px;font-size:.75rem;color:#5a6a88}input{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;
border:1px solid rgba(0,240,255,.25);background:#07030f;color:#fff;margin-bottom:12px}
button{width:100%;padding:10px;border:0;border-radius:8px;background:#00b8c4;color:#04121a;font-weight:700;cursor:pointer}
.err{color:#ff6b8b;font-size:.75rem;margin-bottom:10px}</style></head><body>
<form method="post" action="/login"><h1>ONE2LVOS</h1><p>Colab desktop · Ubuntu 26 terminal · Lumenis</p>
%ERR%<input type="password" name="password" placeholder="Desktop password" autofocus autocomplete="current-password">
<input type="hidden" name="next" value="%NEXT%"><button type="submit">Enter</button></form></body></html>"""


def _client_ip(request: web.Request) -> str:
    return (request.headers.get("cf-connecting-ip")
            or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.remote or "?"))


def _authed(request: web.Request) -> bool:
    tok = request.cookies.get(COOKIE, "")
    exp = _sessions.get(tok)
    if not exp:
        return False
    if exp < time.time():
        _sessions.pop(tok, None)
        return False
    return True


def _login_page(err: str = "", nxt: str = "/desktop") -> web.Response:
    body = LOGIN_PAGE.replace("%ERR%", f'<div class="err">{html.escape(err)}</div>' if err else "")
    body = body.replace("%NEXT%", html.escape(nxt, quote=True))
    return web.Response(text=body, content_type="text/html", headers={"Cache-Control": "no-store"})


async def login_get(request: web.Request):
    if _authed(request):
        raise web.HTTPFound("/desktop")
    return _login_page(nxt=request.query.get("next", "/desktop"))


async def login_post(request: web.Request):
    ip = _client_ip(request)
    now = time.time()
    recent = [t for t in _fail.get(ip, []) if now - t < 300]
    _fail[ip] = recent
    if len(recent) >= 8:
        return _login_page("Too many attempts. Wait five minutes.")
    data = await request.post()
    pw = str(data.get("password", ""))
    nxt = str(data.get("next", "/desktop"))
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = "/desktop"
    if not PASSWORD or not hmac.compare_digest(pw.encode(), PASSWORD.encode()):
        recent.append(now)
        await asyncio.sleep(1.0)
        return _login_page("Wrong password.", nxt)
    tok = secrets.token_urlsafe(32)
    _sessions[tok] = now + SESSION_TTL
    resp = web.HTTPFound(nxt)
    secure = request.headers.get("x-forwarded-proto", request.scheme) == "https"
    resp.set_cookie(COOKIE, tok, max_age=SESSION_TTL, httponly=True, samesite="Lax", secure=secure, path="/")
    raise resp


async def logout(request: web.Request):
    _sessions.pop(request.cookies.get(COOKIE, ""), None)
    resp = web.HTTPFound("/login")
    resp.del_cookie(COOKIE, path="/")
    raise resp


async def health(request: web.Request):
    return web.json_response({"ok": True, "service": "one2lvos-colab-gateway"})


def _target(path: str) -> str:
    return TTYD if (path == "/terminal" or path.startswith("/terminal/")) else REACTOR


async def _ws_proxy(request: web.Request, upstream: str) -> web.WebSocketResponse:
    protos = [p.strip() for p in request.headers.get("Sec-WebSocket-Protocol", "").split(",") if p.strip()]
    ws_server = web.WebSocketResponse(protocols=protos, max_msg_size=0, autoping=True)
    await ws_server.prepare(request)
    url = upstream.replace("http://", "ws://", 1).replace("https://", "wss://", 1) + request.path_qs
    # The gateway's cookie stays here. Upstreams check Origin against their own host: present the local one.
    headers = {"Origin": upstream}
    if "User-Agent" in request.headers:
        headers["User-Agent"] = request.headers["User-Agent"]
    session = request.app["http"]
    try:
        async with session.ws_connect(url, protocols=protos, headers=headers, max_msg_size=0,
                                      autoping=True, heartbeat=None) as ws_client:
            async def up():
                async for m in ws_server:
                    if m.type == WSMsgType.TEXT:
                        await ws_client.send_str(m.data)
                    elif m.type == WSMsgType.BINARY:
                        await ws_client.send_bytes(m.data)
                    elif m.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break
                await ws_client.close()

            async def down():
                async for m in ws_client:
                    if m.type == WSMsgType.TEXT:
                        await ws_server.send_str(m.data)
                    elif m.type == WSMsgType.BINARY:
                        await ws_server.send_bytes(m.data)
                    elif m.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                        break
                await ws_server.close()

            tasks = [asyncio.create_task(up()), asyncio.create_task(down())]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
    except Exception as e:  # upstream down
        if not ws_server.closed:
            await ws_server.close(code=1011, message=f"upstream: {type(e).__name__}".encode()[:120])
    return ws_server


async def proxy(request: web.Request):
    path = request.path
    if path == "/":
        raise web.HTTPFound("/desktop")
    is_ws = request.headers.get("Upgrade", "").lower() == "websocket"
    if not _authed(request):
        if is_ws or path.startswith("/api/"):
            return web.json_response({"error": "login required"}, status=401)
        raise web.HTTPFound("/login?next=" + aiohttp.helpers.quote(request.path_qs, safe="/?=&"))

    if path == "/terminal":
        raise web.HTTPFound("/terminal/")
    if path.startswith("/colab/"):
        f = (HERE / path[len("/colab/"):]).resolve()
        if HERE in f.parents and f.is_file() and f.suffix in (".js", ".css", ".html"):
            return web.FileResponse(f, headers={"Cache-Control": "no-cache"})
        raise web.HTTPNotFound()

    upstream = _target(path)
    if is_ws:
        return await _ws_proxy(request, upstream)

    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP and k.lower() != "cookie"}
    headers["X-Forwarded-Proto"] = request.headers.get("x-forwarded-proto", request.scheme)
    headers["X-Forwarded-Host"] = request.host
    body = await request.read()
    session = request.app["http"]
    try:
        async with session.request(request.method, upstream + request.path_qs, headers=headers,
                                   data=body if body else None, allow_redirects=False) as r:
            payload = await r.read()
            out_headers = {k: v for k, v in r.headers.items() if k.lower() not in HOP}
            ctype = r.headers.get("content-type", "")
            if path in DESKTOP_PATHS and "text/html" in ctype and r.status == 200:
                text = payload.decode("utf-8", errors="replace")
                if ADDON_TAG not in text:
                    marker = '<script src="/static/webos/o2-webos.js"></script>'
                    text = text.replace(marker, ADDON_TAG + "\n    " + marker, 1) if marker in text \
                        else text.replace("</body>", ADDON_TAG + "\n</body>", 1)
                payload = text.encode("utf-8")
                out_headers["Cache-Control"] = "no-cache"
            return web.Response(status=r.status, body=payload, headers=out_headers)
    except aiohttp.ClientConnectorError:
        name = "terminal (ttyd)" if upstream == TTYD else "Lumenis reactor"
        return web.Response(status=502, text=f"One2lvOS Colab: the {name} is not running yet.")


async def _on_startup(app):
    app["http"] = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, sock_connect=5),
                                        auto_decompress=True)


async def _on_cleanup(app):
    await app["http"].close()


def make_app() -> web.Application:
    app = web.Application(client_max_size=64 * 1024 * 1024)
    app.router.add_get("/login", login_get)
    app.router.add_post("/login", login_post)
    app.router.add_get("/logout", logout)
    app.router.add_get("/_gateway/health", health)
    app.router.add_route("*", "/{tail:.*}", proxy)
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
    return app


if __name__ == "__main__":
    if not PASSWORD:
        raise SystemExit("O2_GATEWAY_PASSWORD is not set")
    print(f"One2lvOS Colab gateway on http://{HOST}:{PORT}  reactor={REACTOR}  ttyd={TTYD}", flush=True)
    web.run_app(make_app(), host=HOST, port=PORT, print=None, access_log=None)
