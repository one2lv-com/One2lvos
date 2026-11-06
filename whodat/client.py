"""Who Dat client side: this installation's identity, and talking to a registry.

Two transports with the same methods:
  LocalTransport  the registry database is on this machine (default, single-owner
                  install). No server, no reactor, no Lumenis needed: this is what
                  lets the system get its keys at boot before anything else runs.
  HttpTransport   a registry served by `python3 -m whodat serve` or by the reactor's
                  /whodat routes. Plain http is refused except to loopback.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import core
from .core import (DOMAIN_ADMIN, DOMAIN_REGISTER, DOMAIN_RESPONSE, Registry, WhoDatError, b64e,
                   load_private_key, public_key_b64, sign)


# ── identity on disk ────────────────────────────────────────────────────────────────

class Identity:
    """<home>/identity/{system.key, owner.key, identity.json}. Keys are 0600 PKCS8 PEM,
    optionally passphrase-encrypted (WHODAT_KEY_PASSPHRASE)."""

    def __init__(self, home: Path | None = None):
        self.home = Path(home or core.default_home())
        self.dir = self.home / "identity"
        self.meta_path = self.dir / "identity.json"
        self.system_key_path = self.dir / "system.key"
        self.owner_key_path = self.dir / "owner.key"

    @property
    def exists(self) -> bool:
        return self.meta_path.exists()

    def meta(self) -> dict:
        if not self.exists:
            raise WhoDatError(f"no Who Dat identity at {self.dir} (run: python3 -m whodat init --email you@example.com)")
        return json.loads(self.meta_path.read_text())

    @staticmethod
    def _passphrase() -> bytes | None:
        p = os.getenv("WHODAT_KEY_PASSPHRASE")
        return p.encode() if p else None

    def system_key(self):
        return load_private_key(self.system_key_path, self._passphrase())

    def owner_key(self):
        if not self.owner_key_path.exists():
            raise WhoDatError("this machine has no owner key (it can boot, but not enroll, revoke or write keys)")
        return load_private_key(self.owner_key_path, self._passphrase())

    def write_meta(self, meta: dict) -> None:
        tmp = self.meta_path.with_suffix(".tmp")
        if tmp.exists():
            tmp.unlink()
        core.write_private_file(tmp, (json.dumps(meta, indent=2) + "\n").encode())
        os.replace(tmp, self.meta_path)


def collect_whose_data(identity_meta: dict | None = None) -> dict:
    """'Whose Data?': what this machine says about itself and where it came from.
    It is signed and logged by the registry, but it is a claim, not a credential:
    anyone can copy a hostname. Only the signature authenticates."""
    data = {"hostname": socket.gethostname()[:100],
            "platform": f"{platform.system()} {platform.machine()}",
            "software": "One2lvOS", "time": int(time.time())}
    try:
        mid = Path("/etc/machine-id").read_text().strip()
        if mid:
            data["machine_id_sha256"] = hashlib.sha256(("whodat|" + mid).encode()).hexdigest()
    except OSError:
        pass
    try:
        root = Path(__file__).resolve().parent.parent
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, timeout=3).stdout.strip()
        if commit:
            data["git_commit"] = commit
    except Exception:
        pass
    if identity_meta:
        data["provenance"] = {"owner_email": identity_meta.get("email", ""),
                              "label": identity_meta.get("label", ""),
                              "enrolled_at": str(identity_meta.get("enrolled_at", ""))}
    return data


# ── transports ──────────────────────────────────────────────────────────────────────

class LocalTransport:
    def __init__(self, registry: Registry):
        self.reg = registry

    def info(self) -> dict:
        return {"registry_id": self.reg.registry_id, "protocol": core.PROTOCOL}

    def challenge(self, subject_id: str, purpose: str = "boot") -> dict:
        return self.reg.issue_challenge(subject_id, purpose)

    def respond(self, challenge_id, system_id, whose_data, signature) -> dict:
        return self.reg.respond(challenge_id, system_id, whose_data, signature)

    def secrets(self, token: str, names=None) -> dict:
        return self.reg.fetch_secrets(token, names)

    def admin(self, envelope: dict) -> dict:
        return self.reg.admin(envelope)

    def register_owner(self, email, public_key, challenge_id, signature) -> str:
        return self.reg.register_owner(email, public_key, challenge_id, signature)


def _is_loopback(host: str) -> bool:
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class HttpTransport:
    def __init__(self, base_url: str, timeout: float = 15.0):
        u = urllib.parse.urlparse(base_url.rstrip("/"))
        if u.scheme not in ("http", "https") or not u.hostname:
            raise WhoDatError("registry URL must be http(s)://host[:port]")
        if u.scheme == "http" and not _is_loopback(u.hostname) and os.getenv("WHODAT_ALLOW_INSECURE_HTTP") != "1":
            raise WhoDatError("refusing plain http to a non-loopback registry: keys would cross the network unencrypted")
        self.base = base_url.rstrip("/")
        if not self.base.endswith("/whodat"):
            self.base += "/whodat"
        self.timeout = timeout

    def _call(self, method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode()).get("detail", "")
            except Exception:
                detail = ""
            err = WhoDatError(f"registry answered {e.code}: {detail or e.reason}")
            err.status = e.code
            raise err from None
        except urllib.error.URLError as e:
            raise WhoDatError(f"cannot reach registry: {e.reason}") from None

    def info(self) -> dict:
        return self._call("GET", "")

    def challenge(self, subject_id: str, purpose: str = "boot") -> dict:
        return self._call("POST", "/challenge", {"subject_id": subject_id, "purpose": purpose})

    def respond(self, challenge_id, system_id, whose_data, signature) -> dict:
        return self._call("POST", "/respond", {"challenge_id": challenge_id, "system_id": system_id,
                                               "whose_data": whose_data, "signature": signature})

    def secrets(self, token: str, names=None) -> dict:
        q = "" if not names else "?names=" + urllib.parse.quote(",".join(names))
        return self._call("GET", "/secrets" + q, token=token).get("secrets", {})

    def admin(self, envelope: dict) -> dict:
        return self._call("POST", "/admin", envelope)

    def register_owner(self, email, public_key, challenge_id, signature) -> str:
        return self._call("POST", "/owners", {"email": email, "public_key": public_key,
                                              "challenge_id": challenge_id, "signature": signature})["owner_id"]


# ── flows ────────────────────────────────────────────────────────────────────────

def handshake(transport, system_key, system_id: str, whose_data: dict) -> dict:
    """Who Dat? -> signed Whose Data -> short-lived session token."""
    ch = transport.challenge(system_id, "boot")
    payload = Registry.response_payload(ch["registry_id"], ch, system_id, whose_data)
    sig = sign(system_key, DOMAIN_RESPONSE, payload)
    return transport.respond(ch["challenge_id"], system_id, whose_data, sig)


def signed_admin(owner_key, owner_id: str, registry_id: str, op: str, params: dict) -> dict:
    payload = Registry.admin_payload(registry_id, owner_id, op, params, int(time.time()), b64e(os.urandom(18)))
    return {"payload": payload, "signature": sign(owner_key, DOMAIN_ADMIN, payload)}


def register_owner_remote(transport, owner_key, email: str) -> str:
    pub = public_key_b64(owner_key)
    owner_id = core.owner_id_for(pub)
    ch = transport.challenge(owner_id, "register_owner")
    payload = Registry.register_payload(ch["registry_id"], ch, owner_id, email.strip(), pub)
    return transport.register_owner(email.strip(), pub, ch["challenge_id"], sign(owner_key, DOMAIN_REGISTER, payload))


def open_local_registry(home: Path | None = None) -> Registry:
    home = Path(home or core.default_home())
    return Registry(home / "registry.db", core.load_root_key())


# Result of the last in-process load (names only, never values). Read by GET /whodat.
LAST_LOAD: dict = {"attempted": False}


def load_into_environ(only_unset: bool = True, home: Path | None = None, environ=None) -> dict:
    """The reactor's own Who Dat step: answer "Who Dat?" with this installation's system key,
    and on a verified handshake put the owner's vault keys into the process environment.

    Fail closed: any failure (no identity, revoked system, wrong/missing root key, registry down,
    forged or copied identity) loads nothing and leaves the environment exactly as it was.
    Never raises. Returns and records a status with key NAMES only.
    """
    env = os.environ if environ is None else environ
    status = {"attempted": True, "ok": False, "loaded": [], "skipped_already_set": [], "at": int(time.time())}
    try:
        if env.get("WHODAT_BOOT", "auto") == "0":
            status.update(attempted=False, reason="disabled (WHODAT_BOOT=0)")
        else:
            ident = Identity(home)
            if not ident.exists:
                status["reason"] = "no identity on this installation (run: python3 -m whodat init --email ...)"
            else:
                m = ident.meta()
                t = transport_for(ident)
                sess = handshake(t, ident.system_key(), m["system_id"], collect_whose_data(m))
                values = t.secrets(sess["session_token"])
                staged = {}
                for k in sorted(values):
                    if not core.NAME_RE.match(k) or k.startswith("WHODAT_"):
                        continue
                    if only_unset and env.get(k):
                        status["skipped_already_set"].append(k)
                        continue
                    staged[k] = values[k]
                env.update(staged)          # all-or-nothing: only after the whole handshake succeeded
                status.update(ok=True, system_id=sess.get("system_id"), loaded=sorted(staged))
    except Exception as e:  # noqa: BLE001 - any failure means no keys
        status.update(ok=False, loaded=[], reason=f"handshake failed, no keys loaded: {type(e).__name__}")
    LAST_LOAD.clear()
    LAST_LOAD.update(status)
    return dict(status)


def transport_for(identity: Identity, registry_url: str | None = None):
    url = registry_url or os.getenv("WHODAT_REGISTRY_URL") or identity.meta().get("registry_url") or ""
    if url:
        return HttpTransport(url)
    return LocalTransport(open_local_registry(identity.home))
