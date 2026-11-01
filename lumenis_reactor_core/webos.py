"""
One2lvOS WebOS shell support for the Lumenis Reactor.

Serves one2lvos-desktop.html as the installed WebOS desktop and gives it
same-origin access to every One2lvOS service:

  GET  /desktop, /os, /webos     -> the WebOS desktop (os.<domain>/ redirects here)
  GET  /api/webos/services       -> live up/down for every service, checked from the VM
  ANY  /svc/{service}/{path}     -> reverse proxy to the service on 127.0.0.1. Each service's
                                    site is a sub-page here; HTML gets a small shim so its
                                    absolute /api, fetch and WebSocket calls stay under /svc/<id>
  WS   /svc/{service}/{path}     -> WebSocket proxy to the service

Each service also has its own direct hostname (<sub>.<domain>) on the tunnel.
Everything sits behind Cloudflare Access (Owner Only). The reactor itself binds to the VM,
so nothing here is reachable except through the tunnel and Access.
"""

import asyncio
import os
import re
import time

import httpx
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP_FILE = os.path.join(ROOT, "one2lvos-desktop.html")
PUBLIC_DOMAIN = os.environ.get("O2_PUBLIC_DOMAIN", "one2lv.com")

# Every One2lvOS service. `sub` is its direct hostname under PUBLIC_DOMAIN (behind Access),
# `ui` the page its window opens, `health` the local check, `kind` html or json.
SERVICES = [
    {"id": "reactor", "name": "Lumenis Reactor Core", "port": 8000, "health": "/api/status",
     "sub": "lumenis", "ui": "/lumenis-chat", "kind": "html", "icon": "fas fa-atom", "color": "text-cyan-400",
     "desc": "ITT Council chat, terminal, memory, checkpoints, VectorFS, IONOS diagnostics"},
    {"id": "lobby", "name": "AI Lobby", "port": 8006, "health": "/agents",
     "sub": "lobby", "ui": "/agents", "kind": "json", "icon": "fas fa-satellite-dish", "color": "text-purple-400",
     "desc": "Agent registry, systems, messages and compilers (also on one2lv.com)"},
    {"id": "minimax", "name": "Minimax Core API", "port": 8080, "health": "/health",
     "sub": "minimax", "ui": "/health", "kind": "json", "icon": "fas fa-robot", "color": "text-emerald-400",
     "desc": "Coaching, commentary and broadcaster API"},
    {"id": "network", "name": "Network Manager", "port": 3003, "health": "/api/network/connections",
     "sub": "network", "ui": "/network-manager.html", "kind": "html", "icon": "fas fa-network-wired",
     "color": "text-teal-400", "desc": "Connections and network tests"},
    {"id": "core", "name": "Sovereign Agentic Core", "port": 8081, "health": "/api/status",
     "sub": "core", "ui": "/", "kind": "html", "icon": "fas fa-crown", "color": "text-amber-400",
     "desc": "Sovereign core reactor and council"},
    {"id": "arcade", "name": "AI Arcade MCP", "port": 8003, "health": "/",
     "sub": "arcade", "ui": "/", "kind": "json", "icon": "fas fa-chess-knight", "color": "text-pink-400",
     "desc": "MCP game server (chess and more), MCP endpoint at /mcp"},
    {"id": "aetherix", "name": "Aetherix Terminal", "port": 9003, "health": "/health",
     "sub": "aetherix", "ui": "/", "kind": "html", "icon": "fas fa-satellite", "color": "text-sky-400",
     "desc": "Aetherix master terminal and sanctuary"},
]
# Services the desktop knows about that are not installed on this host.
NOT_INSTALLED = [
    {"id": "witness", "name": "Minimax Witness Proxy", "port": 3001},
    {"id": "oscore", "name": "One2lvOS Core (Node)", "port": 3002},
    {"id": "steamos", "name": "SteamOS / Lumenis v7", "port": 8005},
    {"id": "gateway", "name": "Unified Gateway", "port": 8888},
    {"id": "lumenisos", "name": "LumenisOS API", "port": 9002},
    {"id": "spaceui", "name": "Lumenis Space Agent UI", "port": 9001},
]
_BY_ID = {s["id"]: s for s in SERVICES}
_NI_BY_ID = {s["id"]: s for s in NOT_INSTALLED}

_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
        "transfer-encoding", "upgrade", "host", "content-length", "content-encoding"}
# Same-origin only: framing blocks and cookies from the services are not passed on.
_DROP_RESP = _HOP | {"set-cookie", "x-frame-options", "strict-transport-security"}
_ATTR = re.compile(r"""((?:src|href|action)\s*=\s*["'])/(?!/|svc/)""", re.I)

router = APIRouter()
_client = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=3.0), follow_redirects=False)
    return _client


def _base(request: Request) -> str:
    host = request.headers.get("host", "127.0.0.1:8000")
    proto = request.headers.get("x-forwarded-proto") or ("https" if host.endswith(PUBLIC_DOMAIN) else "http")
    return f"{proto}://{host}"


def _ui_path(s) -> str:
    return s["ui"] if s["id"] == "reactor" else f"/svc/{s['id']}{s['ui']}"


def _shim(sid: str) -> str:
    """Keeps a proxied page's absolute same-origin calls under /svc/<sid>."""
    return (
        "<script>(function(){var P='/svc/%s',O=location.origin;"
        "function fx(u){try{var s=(u&&u.href)?u.href:u;if(typeof s!=='string')return u;var x=new URL(s,location.href);"
        "if(x.host===location.host&&x.pathname!==P&&x.pathname.indexOf(P+'/')!==0){x.pathname=P+x.pathname;return x.href}"
        "return s}catch(e){return u}}"
        "var F=window.fetch;window.fetch=function(i,o){if(typeof Request!=='undefined'&&i instanceof Request)"
        "{i=new Request(fx(i.url),i)}else{i=fx(i)}return F.call(this,i,o)};"
        "var XO=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u)"
        "{arguments[1]=fx(u);return XO.apply(this,arguments)};"
        "var W=window.WebSocket;function NW(u,p){u=fx(u);return p===undefined?new W(u):new W(u,p)}"
        "NW.prototype=W.prototype;['CONNECTING','OPEN','CLOSING','CLOSED'].forEach(function(k){NW[k]=W[k]});"
        "window.WebSocket=NW;"
        "if(window.EventSource){var E=window.EventSource;var NE=function(u,c){return new E(fx(u),c)};"
        "NE.prototype=E.prototype;window.EventSource=NE}"
        "})();</script>" % sid)


# ── Desktop ──────────────────────────────────────────────────────────────────
@router.get("/desktop")
@router.get("/os")
@router.get("/webos")
async def webos_desktop():
    return FileResponse(DESKTOP_FILE, media_type="text/html", headers={"Cache-Control": "no-cache"})


# ── Service status ────────────────────────────────────────────────────────────
async def _check(s):
    t0 = time.monotonic()
    try:
        r = await _http().get(f"http://127.0.0.1:{s['port']}{s['health']}", timeout=3.0)
        return {"up": r.status_code < 500, "http": r.status_code, "ms": int((time.monotonic() - t0) * 1000)}
    except Exception as e:
        return {"up": False, "http": None, "ms": None, "error": type(e).__name__}


@router.get("/api/webos/services")
async def webos_services(request: Request):
    base = _base(request)
    results = await asyncio.gather(*[_check(s) for s in SERVICES])
    out = []
    for s, r in zip(SERVICES, results):
        out.append({
            **{k: s[k] for k in ("id", "name", "port", "icon", "color", "desc", "kind")},
            **r,
            "ui_path": _ui_path(s),
            "ui_url": base + _ui_path(s),
            "proxy": "" if s["id"] == "reactor" else f"/svc/{s['id']}",
            "direct_url": f"https://{s['sub']}.{PUBLIC_DOMAIN}{s['ui']}",
        })
    return JSONResponse({
        "ok": True, "checked_at": time.time(), "base": base, "services": out,
        "not_installed": NOT_INSTALLED, "up": sum(1 for o in out if o["up"]), "total": len(out),
    }, headers={"Cache-Control": "no-store"})


# ── Same-origin proxy: each service's site as a sub-page ──────────────────────────────
@router.api_route("/svc/{sid}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@router.api_route("/svc/{sid}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def webos_proxy(sid: str, request: Request, path: str = ""):
    if sid in _NI_BY_ID:
        ni = _NI_BY_ID[sid]
        msg = f"{ni['name']} (port {ni['port']}) is not installed on this host."
        if "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(
                "<!doctype html><body style='background:#07030f;color:#94a3b8;font-family:system-ui;"
                "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
                f"<div>{msg}</div></body>", status_code=503)
        return JSONResponse({"ok": False, "service": sid, "error": msg}, status_code=503)
    s = _BY_ID.get(sid)
    if not s or sid == "reactor":
        return JSONResponse({"ok": False, "error": f"unknown service '{sid}'"}, status_code=404)
    if not path and request.method == "GET" and not request.url.path.endswith("/"):
        return RedirectResponse(f"/svc/{sid}/", status_code=307)

    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in _HOP and not k.lower().startswith("cf-") and k.lower() != "cookie"}
    try:
        r = await _http().request(request.method, f"http://127.0.0.1:{s['port']}/{path}",
                                  params=request.query_params, headers=headers, content=await request.body())
    except Exception as e:
        return JSONResponse({"ok": False, "service": sid,
                             "error": f"{s['name']} is offline ({type(e).__name__})"}, status_code=503)

    resp_headers = {k: v for k, v in r.headers.items() if k.lower() not in _DROP_RESP}
    loc = r.headers.get("location")
    if loc and loc.startswith("/") and not loc.startswith("//") and not loc.startswith(f"/svc/{sid}"):
        resp_headers = {k: v for k, v in resp_headers.items() if k.lower() != "location"}
        resp_headers["location"] = f"/svc/{sid}{loc}"
    content = r.content
    if "text/html" in r.headers.get("content-type", "") and content:
        html = content.decode(r.encoding or "utf-8", errors="replace")
        html = _ATTR.sub(lambda m: m.group(1) + f"/svc/{sid}/", html)
        m = re.search(r"<head[^>]*>", html, re.I)
        shim = _shim(sid)
        html = html[:m.end()] + shim + html[m.end():] if m else shim + html
        content = html.encode("utf-8")
        resp_headers = {k: v for k, v in resp_headers.items() if k.lower() != "content-type"}
        resp_headers["content-type"] = "text/html; charset=utf-8"
    return Response(content=content, status_code=r.status_code, headers=resp_headers)


@router.websocket("/svc/{sid}/{path:path}")
async def webos_ws_proxy(ws: WebSocket, sid: str, path: str = ""):
    import websockets
    s = _BY_ID.get(sid)
    if not s or sid == "reactor":
        await ws.close(code=4404)
        return
    await ws.accept()
    url = f"ws://127.0.0.1:{s['port']}/{path}" + (f"?{ws.url.query}" if ws.url.query else "")
    try:
        async with websockets.connect(url, max_size=None, open_timeout=5) as upstream:
            async def down():
                async for m in upstream:
                    if isinstance(m, bytes):
                        await ws.send_bytes(m)
                    else:
                        await ws.send_text(m)

            async def up():
                while True:
                    m = await ws.receive()
                    if m.get("type") == "websocket.disconnect":
                        break
                    if m.get("text") is not None:
                        await upstream.send(m["text"])
                    elif m.get("bytes") is not None:
                        await upstream.send(m["bytes"])

            tasks = [asyncio.create_task(down()), asyncio.create_task(up())]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in tasks:
                t.cancel()
    except Exception:
        pass
    try:
        await ws.close()
    except Exception:
        pass


# ── os.<domain>: / opens the desktop ───────────────────────────────────────────────
async def os_host_redirect(request: Request, call_next):
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if request.url.path == "/" and host.startswith("os."):
        return RedirectResponse("/desktop", status_code=302)
    return await call_next(request)
