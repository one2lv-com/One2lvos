"""
sfcompute Autoresearch MCP bridge for One2lvOS (Lumenis hook)
=============================================================
Remote MCP server: https://mcp.autoresearch.sfcompute.com  ("Autoresearch" by SF Compute)
  - On-demand H100 / CPU nodes, batch jobs, sandboxes, billed per minute from prepaid credit.
  - Transport: MCP Streamable HTTP (JSON-RPC 2.0, JSON or SSE answers, Mcp-Session-Id).
  - Auth: OAuth 2.1 bearer token from https://auth.givemeanode.com (device-code flow
    supported) or an org service token. Without a token every call answers 401.

As specified by Lumenis (session "sfcompute MCP integration", 2026-11-05):
  - every outbound request carries the Lumenis marker header  X-Lumenis-Auth: 🧲
  - upstream speaks JSON-RPC; the One2lvOS side also accepts the delta-pipe body
    "∆|key=value|key=value" and translates it to a JSON-RPC tools/call
  - routes: GET /mcp/sfcompute, POST /mcp/sfcompute/{tool}
  - token from env SFCOMPUTE_MCP_TOKEN
  - tools that spend money stay blocked unless One2lv allows them

Policy: read-only tools (get_*, list_*, query_*, search_*, or readOnlyHint) are allowed.
Everything else (create_node, run_command, submit_job, buy_credits, delete_*, ...) is
refused unless named in SFCOMPUTE_MCP_ALLOW_TOOLS (comma list) in .env.

Routes (mounted on the Lumenis reactor, port 8000):
  GET  /mcp/sfcompute               status: url, marker, token present, upstream answer
  GET  /mcp/sfcompute/tools         tools/list (name, description, allowed?)
  POST /mcp/sfcompute/{tool}        tools/call; JSON object or ∆|key=value body
  POST /mcp/sfcompute               tools/call with the tool named in the body (tool=...)
  POST /mcp/sfcompute/login/start   begin device-code sign-in; returns the code + URL to approve
  POST /mcp/sfcompute/login/poll    finish it; stores the token (never returned)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

MCP_URL = os.getenv("SFCOMPUTE_MCP_URL", "https://mcp.autoresearch.sfcompute.com").rstrip("/")
PROTOCOL_VERSION = "2025-06-18"
MARKER_HEADER = os.getenv("LUMENIS_MARKER_HEADER", "X-Lumenis-Auth")
MARKER_VALUE = os.getenv("LUMENIS_MARKER_VALUE", "🧲")
TOKEN_FILE = Path(os.getenv("SFCOMPUTE_MCP_TOKEN_FILE",
                            str(Path.home() / ".config" / "one2lvos" / "sfcompute_token.json")))
READ_PREFIXES = ("get_", "list_", "query_", "search_")
# Read-only by name, but touches secrets: kept behind the allow list too.
ALWAYS_ASK = {"list_secrets"}
CLIENT_INFO = {"name": "One2lvOS-Lumenis", "version": "1.0"}

router = APIRouter(tags=["sfcompute-mcp"])


# ── Lumenis marker + delta pipe ──────────────────────────────────────────────

def marker_headers() -> Dict[bytes, bytes]:
    """The 🧲 marker on every outbound request. Bytes, because the value is not ASCII."""
    return {MARKER_HEADER.encode(): MARKER_VALUE.encode("utf-8")}


def parse_delta_pipe(text: str) -> Dict[str, Any]:
    """'∆|tool=get_billing|workspace=main|limit=5' -> {'tool': 'get_billing', ...}.
    Values that parse as JSON (numbers, true/false, objects) are decoded."""
    s = text.strip()
    for prefix in ("∆|", "Δ|"):  # U+2206 and U+0394
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    else:
        raise ValueError("delta-pipe body must start with ∆|")
    out: Dict[str, Any] = {}
    for part in s.split("|"):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"delta-pipe segment without '=': {part!r}")
        k, v = part.split("=", 1)
        k, v = k.strip(), v.strip()
        try:
            out[k] = json.loads(v)
        except Exception:
            out[k] = v
    return out


# ── Token handling (value never logged or returned) ──────────────────────────

def _load_token_file() -> Dict[str, Any]:
    try:
        return json.loads(TOKEN_FILE.read_text())
    except Exception:
        return {}


def _save_token_file(data: Dict[str, Any]) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = TOKEN_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    os.chmod(tmp, 0o600)
    tmp.replace(TOKEN_FILE)


async def _auth_meta(client: httpx.AsyncClient) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    prm = (await client.get(f"{MCP_URL}/.well-known/oauth-protected-resource",
                            headers=marker_headers())).json()
    issuer = prm["authorization_servers"][0].rstrip("/")
    asm = (await client.get(f"{issuer}/.well-known/oauth-authorization-server",
                            headers=marker_headers())).json()
    return prm, asm


async def _refresh(client: httpx.AsyncClient, tok: Dict[str, Any]) -> Optional[str]:
    if not tok.get("refresh_token"):
        return None
    prm, asm = await _auth_meta(client)
    r = await client.post(asm["token_endpoint"], headers=marker_headers(), data={
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
        "client_id": tok.get("client_id") or prm.get("device_client_id"),
    })
    if r.status_code != 200:
        return None
    _store_token_response(r.json(), tok.get("client_id") or prm.get("device_client_id"), tok)
    return _load_token_file().get("access_token")


def _store_token_response(resp: Dict[str, Any], client_id: str, old: Optional[Dict[str, Any]] = None) -> None:
    data = {
        "access_token": resp["access_token"],
        "refresh_token": resp.get("refresh_token") or (old or {}).get("refresh_token"),
        "expires_at": time.time() + int(resp.get("expires_in", 3600)) - 60,
        "client_id": client_id,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    _save_token_file(data)


async def get_token(client: httpx.AsyncClient, force_refresh: bool = False) -> Tuple[Optional[str], str]:
    """Returns (token, source). Env SFCOMPUTE_MCP_TOKEN (or GMN_TOKEN) wins; else the
    device-flow token file, refreshed when it has expired."""
    env = os.getenv("SFCOMPUTE_MCP_TOKEN") or os.getenv("GMN_TOKEN")
    if env and not force_refresh:
        return env, "env"
    tok = _load_token_file()
    if not tok:
        return (env, "env") if env else (None, "none")
    if force_refresh or time.time() >= float(tok.get("expires_at", 0)):
        fresh = await _refresh(client, tok)
        return (fresh, "token_file(refreshed)") if fresh else (None, "token_file(expired)")
    return tok.get("access_token"), "token_file"


# ── MCP Streamable HTTP client ───────────────────────────────────────────────

class MCPError(Exception):
    def __init__(self, status: int, detail: Any):
        super().__init__(str(detail))
        self.status, self.detail = status, detail


def _parse_rpc(resp: httpx.Response, want_id: Any) -> Dict[str, Any]:
    ctype = resp.headers.get("content-type", "")
    if "text/event-stream" in ctype:
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                try:
                    msg = json.loads(line[5:].strip())
                except Exception:
                    continue
                if msg.get("id") == want_id:
                    return msg
        raise MCPError(502, "no JSON-RPC answer in event stream")
    return resp.json()


class SfcomputeMCP:
    def __init__(self, token: str, client: httpx.AsyncClient):
        self.token, self.client = token, client
        self.session_id: Optional[str] = None
        self._id = 0

    def _headers(self) -> Dict[bytes, bytes]:
        h = marker_headers()
        h[b"Authorization"] = f"Bearer {self.token}".encode()
        h[b"Content-Type"] = b"application/json"
        h[b"Accept"] = b"application/json, text/event-stream"
        h[b"MCP-Protocol-Version"] = PROTOCOL_VERSION.encode()
        if self.session_id:
            h[b"Mcp-Session-Id"] = self.session_id.encode()
        return h

    async def _rpc(self, method: str, params: Optional[dict] = None, notify: bool = False) -> Any:
        body: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            self._id += 1
            body["id"] = self._id
        r = await self.client.post(MCP_URL, headers=self._headers(), content=json.dumps(body))
        if r.status_code in (401, 403):
            raise MCPError(r.status_code, {"error": "unauthorized", "www-authenticate": r.headers.get("www-authenticate")})
        if notify:
            return None
        if r.status_code >= 400:
            raise MCPError(r.status_code, r.text[:500])
        sid = r.headers.get("mcp-session-id")
        if sid:
            self.session_id = sid
        msg = _parse_rpc(r, body["id"])
        if "error" in msg:
            raise MCPError(502, msg["error"])
        return msg.get("result")

    async def initialize(self) -> Dict[str, Any]:
        res = await self._rpc("initialize", {"protocolVersion": PROTOCOL_VERSION,
                                             "capabilities": {}, "clientInfo": CLIENT_INFO})
        await self._rpc("notifications/initialized", notify=True)
        return res

    async def list_tools(self) -> list:
        tools, cursor = [], None
        while True:
            res = await self._rpc("tools/list", {"cursor": cursor} if cursor else {})
            tools += res.get("tools", [])
            cursor = res.get("nextCursor")
            if not cursor:
                return tools

    async def call_tool(self, name: str, arguments: dict) -> Any:
        return await self._rpc("tools/call", {"name": name, "arguments": arguments})


async def _session(client: httpx.AsyncClient) -> Tuple[SfcomputeMCP, Dict[str, Any]]:
    token, source = await get_token(client)
    if not token:
        raise MCPError(401, {"error": "no_token",
                             "fix": "POST /mcp/sfcompute/login/start, approve the code, then POST /mcp/sfcompute/login/poll; "
                                    "or set SFCOMPUTE_MCP_TOKEN in .env to an Autoresearch org service token"})
    mcp = SfcomputeMCP(token, client)
    try:
        info = await mcp.initialize()
    except MCPError as e:
        if e.status == 401 and source.startswith("token_file"):
            token, source = await get_token(client, force_refresh=True)
            if not token:
                raise
            mcp = SfcomputeMCP(token, client)
            info = await mcp.initialize()
        else:
            raise
    info = dict(info or {})
    info["_token_source"] = source
    return mcp, info


# ── Policy ───────────────────────────────────────────────────────────────────

def _allow_list() -> set:
    return {t.strip() for t in os.getenv("SFCOMPUTE_MCP_ALLOW_TOOLS", "").split(",") if t.strip()}


def tool_allowed(name: str, annotations: Optional[dict] = None) -> bool:
    if name in _allow_list():
        return True
    if name in ALWAYS_ASK:
        return False
    if (annotations or {}).get("readOnlyHint") is True:
        return True
    return name.startswith(READ_PREFIXES)


# ── Routes ───────────────────────────────────────────────────────────────────

def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))


def _err(e: Exception) -> JSONResponse:
    if isinstance(e, MCPError):
        return JSONResponse({"ok": False, "status": e.status, "detail": e.detail}, status_code=e.status)
    return JSONResponse({"ok": False, "status": 502, "detail": f"{type(e).__name__}: {e}"}, status_code=502)


@router.get("/mcp/sfcompute")
async def sfcompute_status():
    async with _client() as c:
        token, source = await get_token(c)
        out: Dict[str, Any] = {
            "server": MCP_URL, "name": "Autoresearch (SF Compute)", "transport": "streamable-http",
            "marker_header": f"{MARKER_HEADER}: {MARKER_VALUE}", "delta_pipe": "accepted on POST bodies (∆|key=value)",
            "token_present": bool(token), "token_source": source,
            "allow_extra_tools": sorted(_allow_list()),
        }
        if not token:
            r = await c.get(MCP_URL, headers=marker_headers())
            out["upstream"] = {"http_status": r.status_code, "www-authenticate": r.headers.get("www-authenticate")}
            out["next_step"] = "sign in: POST /mcp/sfcompute/login/start"
            return JSONResponse(out)
        try:
            _, info = await _session(c)
            out["upstream"] = {"initialized": True, "serverInfo": info.get("serverInfo"),
                               "protocolVersion": info.get("protocolVersion")}
        except Exception as e:
            out["upstream"] = {"initialized": False, "error": getattr(e, "detail", str(e))}
        return JSONResponse(out)


@router.get("/mcp/sfcompute/tools")
async def sfcompute_tools():
    async with _client() as c:
        try:
            mcp, _ = await _session(c)
            tools = await mcp.list_tools()
        except Exception as e:
            return _err(e)
    rows = [{"name": t["name"], "allowed": tool_allowed(t["name"], t.get("annotations")),
             "description": (t.get("description") or "")[:300]} for t in tools]
    return JSONResponse({"ok": True, "count": len(rows), "tools": rows})


async def _read_args(request: Request) -> Dict[str, Any]:
    raw = (await request.body()).decode("utf-8", "replace").strip()
    if not raw:
        return {}
    if raw.startswith(("∆|", "Δ|")):
        return parse_delta_pipe(raw)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object or a ∆|key=value string")
    if isinstance(data.get("arguments"), dict):
        args = dict(data["arguments"])
        if "tool" in data:
            args["tool"] = data["tool"]
        return args
    return data


async def _call(tool: str, args: Dict[str, Any]) -> JSONResponse:
    args = {k: v for k, v in args.items() if k != "tool"}
    async with _client() as c:
        try:
            mcp, _ = await _session(c)
            tools = {t["name"]: t for t in await mcp.list_tools()}
            if tool not in tools:
                return JSONResponse({"ok": False, "status": 404, "detail": f"no tool named {tool!r}"}, status_code=404)
            if not tool_allowed(tool, tools[tool].get("annotations")):
                return JSONResponse({"ok": False, "status": 403, "detail":
                                     f"{tool} " + ("touches stored secrets" if tool in ALWAYS_ASK else "can start, change or delete paid compute") +
                                     "; blocked until One2lv adds it to "
                                     f"SFCOMPUTE_MCP_ALLOW_TOOLS in .env"}, status_code=403)
            result = await mcp.call_tool(tool, args)
        except Exception as e:
            return _err(e)
    return JSONResponse({"ok": not (result or {}).get("isError", False), "tool": tool, "result": result})


@router.post("/mcp/sfcompute/login/start")
async def sfcompute_login_start():
    async with _client() as c:
        try:
            prm, asm = await _auth_meta(c)
            client_id = prm["device_client_id"]
            r = await c.post(asm["device_authorization_endpoint"], headers=marker_headers(), data={
                "client_id": client_id, "scope": "openid profile email offline_access",
                "resource": prm.get("resource", MCP_URL)})
            d = r.json()
        except Exception as e:
            return _err(e)
    if r.status_code != 200:
        return JSONResponse({"ok": False, "status": r.status_code, "detail": d}, status_code=502)
    pending = {"device_code": d["device_code"], "client_id": client_id,
               "interval": d.get("interval", 5), "expires_at": time.time() + int(d.get("expires_in", 600))}
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    p = TOKEN_FILE.with_name("sfcompute_device_pending.json")
    p.write_text(json.dumps(pending)); os.chmod(p, 0o600)
    asyncio.get_running_loop().create_task(_auto_poll(pending))
    return JSONResponse({"ok": True, "user_code": d.get("user_code"),
                         "verification_uri": d.get("verification_uri"),
                         "verification_uri_complete": d.get("verification_uri_complete"),
                         "expires_in": d.get("expires_in"), "next": "approve, then POST /mcp/sfcompute/login/poll"})


async def _auto_poll(pending: Dict[str, Any]) -> None:
    """Poll the token endpoint in the background until the code is approved or expires,
    so the sign-in never depends on someone calling /login/poll in time."""
    interval = max(int(pending.get("interval", 5)), 3)
    p = TOKEN_FILE.with_name("sfcompute_device_pending.json")
    async with _client() as c:
        try:
            _, asm = await _auth_meta(c)
        except Exception:
            return
        while time.time() < pending["expires_at"]:
            await asyncio.sleep(interval)
            try:
                r = await c.post(asm["token_endpoint"], headers=marker_headers(), data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": pending["device_code"], "client_id": pending["client_id"]})
                d = r.json()
            except Exception:
                continue
            if r.status_code == 200 and d.get("access_token"):
                _store_token_response(d, pending["client_id"])
                p.unlink(missing_ok=True)
                print("🧲 sfcompute MCP: device sign-in complete, token stored")
                return
            err = d.get("error")
            if err == "slow_down":
                interval += 5
            elif err != "authorization_pending":
                print(f"🧲 sfcompute MCP: device sign-in ended: {err}")
                return


@router.post("/mcp/sfcompute/login/poll")
async def sfcompute_login_poll():
    p = TOKEN_FILE.with_name("sfcompute_device_pending.json")
    if _load_token_file().get("access_token") and not p.exists():
        return JSONResponse({"ok": True, "signed_in": True, "token_saved_to": str(TOKEN_FILE)})
    try:
        pending = json.loads(p.read_text())
    except Exception:
        return JSONResponse({"ok": False, "detail": "no sign-in pending; POST /mcp/sfcompute/login/start"}, status_code=400)
    async with _client() as c:
        try:
            _, asm = await _auth_meta(c)
            r = await c.post(asm["token_endpoint"], headers=marker_headers(), data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": pending["device_code"], "client_id": pending["client_id"]})
            d = r.json()
        except Exception as e:
            return _err(e)
    if r.status_code == 200 and d.get("access_token"):
        _store_token_response(d, pending["client_id"])
        p.unlink(missing_ok=True)
        return JSONResponse({"ok": True, "signed_in": True, "token_saved_to": str(TOKEN_FILE)})
    return JSONResponse({"ok": False, "signed_in": False, "detail": d.get("error", d)}, status_code=202 if d.get("error") in ("authorization_pending", "slow_down") else 400)


@router.post("/mcp/sfcompute/{tool}")
async def sfcompute_call(tool: str, request: Request):
    try:
        args = await _read_args(request)
    except Exception as e:
        return JSONResponse({"ok": False, "status": 400, "detail": str(e)}, status_code=400)
    return await _call(tool, args)


@router.post("/mcp/sfcompute")
async def sfcompute_call_named(request: Request):
    try:
        args = await _read_args(request)
    except Exception as e:
        return JSONResponse({"ok": False, "status": 400, "detail": str(e)}, status_code=400)
    tool = args.get("tool")
    if not tool:
        return JSONResponse({"ok": False, "status": 400, "detail": "name the tool: ∆|tool=get_billing or {\"tool\": ...}"}, status_code=400)
    return await _call(tool, args)


# ── Registry entries for the Lumenis tool registry ───────────────────────────

REGISTRY_ENTRIES = [
    {"id": "sfcompute.status", "label": "sfcompute MCP: Status", "method": "GET", "path": "/mcp/sfcompute",
     "category": "Compute", "icon": "🧲", "params": []},
    {"id": "sfcompute.tools", "label": "sfcompute MCP: List Tools", "method": "GET", "path": "/mcp/sfcompute/tools",
     "category": "Compute", "icon": "🧲", "params": []},
    {"id": "sfcompute.call", "label": "sfcompute MCP: Call Tool (JSON or ∆|)", "method": "POST",
     "path": "/mcp/sfcompute/{tool}", "category": "Compute", "icon": "🧲", "params": ["tool", "arguments"]},
]
