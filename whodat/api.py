"""HTTP face of Who Dat. Mounted by the reactor at /whodat and by `python3 -m whodat serve`.

  GET  /whodat              registry info (no secrets)
  POST /whodat/challenge    "Who Dat?"  {subject_id, purpose}  or  ∆|subject_id=sys_...|purpose=boot
  POST /whodat/respond      "Whose Data?" {challenge_id, system_id, whose_data, signature}
  GET  /whodat/secrets      Authorization: Bearer wdt_...   [?names=A,B]
  POST /whodat/admin        owner-signed {payload, signature}: enroll / revoke / put / delete / list / audit
  POST /whodat/owners       self-registration with proof of key possession (only if WHODAT_OPEN_REGISTRATION=1)

The 🧲 X-Lumenis-Auth header is accepted and ignored: it is a marker, not a credential.
Nothing here ever trusts what a caller (Lumenis included) says about itself; only
signatures from enrolled keys count.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import core
from .core import Registry, WhoDatError

router = APIRouter(prefix="/whodat", tags=["whodat"])

_registry: Registry | None = None
_registry_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)
RATE_PER_MIN = int(os.getenv("WHODAT_RATE_PER_MIN", "60"))
NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


def set_registry(reg: Registry | None) -> None:
    """For tests and for embedding: use this registry instead of the one under WHODAT_HOME."""
    global _registry
    _registry = reg


def get_registry() -> Registry:
    global _registry
    with _registry_lock:
        if _registry is None:
            db = core.default_home() / "registry.db"
            if not db.exists():
                raise core.NotFound("no Who Dat registry on this host (run: python3 -m whodat init)")
            _registry = Registry(db, core.load_root_key())   # vault stays locked if no root key
        return _registry


def open_registration() -> bool:
    return os.getenv("WHODAT_OPEN_REGISTRATION", "0") == "1"


def _err(e: WhoDatError) -> JSONResponse:
    return JSONResponse({"ok": False, "detail": e.detail}, status_code=e.status, headers=NO_STORE)


def _limited(request: Request) -> bool:
    ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")
    now = time.monotonic()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_PER_MIN:
        return True
    q.append(now)
    return False


async def _body(request: Request) -> dict:
    raw = (await request.body()).decode("utf-8", "replace").strip()
    if len(raw) > 64 * 1024 + 4096:
        raise core.BadRequest("body too large")
    if raw.startswith(("∆|", "Δ|")):                 # Lumenis delta-pipe framing
        out = {}
        for part in raw[2:].split("|"):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
        return out
    try:
        body = json.loads(raw or "{}")
    except json.JSONDecodeError:
        raise core.BadRequest("body must be JSON or a ∆|key=value string")
    if not isinstance(body, dict):
        raise core.BadRequest("body must be a JSON object")
    return body


@router.get("")
async def whodat_info():
    try:
        reg = get_registry()
        return JSONResponse({"ok": True, "protocol": core.PROTOCOL, "question": "Who Dat?",
                             "registry_id": reg.registry_id,
                             "vault": "unlocked" if reg.vault_unlocked else "locked",
                             "open_registration": open_registration()}, headers=NO_STORE)
    except WhoDatError as e:
        return _err(e)


@router.post("/challenge")
async def whodat_challenge(request: Request):
    if _limited(request):
        return JSONResponse({"ok": False, "detail": "slow down"}, status_code=429)
    try:
        b = await _body(request)
        subject = b.get("subject_id") or b.get("system_id")
        purpose = b.get("purpose") or "boot"
        if purpose == "register_owner" and not open_registration():
            raise core.Forbidden("self-registration is turned off on this registry")
        return JSONResponse(get_registry().issue_challenge(subject, purpose), headers=NO_STORE)
    except WhoDatError as e:
        return _err(e)


@router.post("/respond")
async def whodat_respond(request: Request):
    if _limited(request):
        return JSONResponse({"ok": False, "detail": "slow down"}, status_code=429)
    try:
        b = await _body(request)
        res = get_registry().respond(b.get("challenge_id"), b.get("system_id"),
                                     b.get("whose_data") or {}, b.get("signature") or "")
        return JSONResponse(res, headers=NO_STORE)
    except WhoDatError as e:
        return _err(e)


@router.get("/secrets")
async def whodat_secrets(request: Request, names: str = ""):
    if _limited(request):
        return JSONResponse({"ok": False, "detail": "slow down"}, status_code=429)
    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    try:
        wanted = [n for n in names.split(",") if n] or None
        out = get_registry().fetch_secrets(token, wanted)
        return JSONResponse({"ok": True, "secrets": out}, headers=NO_STORE)
    except WhoDatError as e:
        return _err(e)


@router.post("/admin")
async def whodat_admin(request: Request):
    if _limited(request):
        return JSONResponse({"ok": False, "detail": "slow down"}, status_code=429)
    try:
        return JSONResponse(get_registry().admin(await _body(request)), headers=NO_STORE)
    except WhoDatError as e:
        return _err(e)


@router.post("/owners")
async def whodat_register(request: Request):
    if _limited(request):
        return JSONResponse({"ok": False, "detail": "slow down"}, status_code=429)
    try:
        if not open_registration():
            raise core.Forbidden("self-registration is turned off on this registry")
        b = await _body(request)
        owner_id = get_registry().register_owner(b.get("email", ""), b.get("public_key", ""),
                                                 b.get("challenge_id", ""), b.get("signature", ""))
        return JSONResponse({"ok": True, "owner_id": owner_id}, headers=NO_STORE)
    except WhoDatError as e:
        return _err(e)


REGISTRY_ENTRIES = [
    {"id": "whodat.status", "label": "Who Dat: Registry Status", "method": "GET", "path": "/whodat",
     "category": "Identity", "icon": "🧲", "params": []},
]


def create_app():
    from fastapi import FastAPI
    app = FastAPI(title="Who Dat registry", docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(router)
    return app
