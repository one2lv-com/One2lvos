"""Who Dat core: keys, challenge-response, enrollment, revocation, encrypted vault, audit.

Everything here is local and synchronous; the HTTP router (api.py), the client
(client.py) and the CLI (cli.py) all go through the same Registry methods, so the
checks are identical whether the handshake runs in-process at boot or over the
network.

Cryptography
  identity    Ed25519 keypairs generated on each installation (never shipped)
  handshake   32-byte random nonce, 60 s expiry, single use (atomic consume)
  signatures  domain-separated: b"whodat/1 response\\n", b"whodat/1 admin\\n",
              b"whodat/1 register\\n" + canonical JSON, so one kind can never be
              replayed as another
  vault       AES-256-GCM, per-owner key = HKDF-SHA256(root key, registry id, owner id),
              AAD binds owner + secret name + version; the root key lives outside
              the registry database and is provisioned separately
  audit       append-only table, SHA-256 hash chain, secret names only, never values
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets as _secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

PROTOCOL = "whodat/1"

CHALLENGE_TTL = int(os.getenv("WHODAT_CHALLENGE_TTL", "60"))
SESSION_TTL = int(os.getenv("WHODAT_SESSION_TTL", "300"))
ADMIN_SKEW = 120                    # seconds either side for signed admin requests
MAX_OPEN_CHALLENGES = 16            # unexpired, unused challenges per subject
MAX_SECRET_BYTES = 64 * 1024
MAX_SECRETS_PER_OWNER = 500
MAX_SYSTEMS_PER_OWNER = 64
MAX_WHOSE_DATA_BYTES = 8 * 1024

DOMAIN_RESPONSE = b"whodat/1 response\n"
DOMAIN_ADMIN = b"whodat/1 admin\n"
DOMAIN_REGISTER = b"whodat/1 register\n"

NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")     # env-var style: safe to export
SYSTEM_ID_RE = re.compile(r"^sys_[a-z2-7]{26}$")
OWNER_ID_RE = re.compile(r"^own_[a-z2-7]{26}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{1,63}$")


# ── errors ────────────────────────────────────────────────────────────────────

class WhoDatError(Exception):
    status = 400
    public = "bad request"

    def __init__(self, detail: str | None = None):
        super().__init__(detail or self.public)
        self.detail = detail or self.public


class BadRequest(WhoDatError):
    status = 400


class AuthError(WhoDatError):
    """Every identity failure looks the same from outside: unknown system, revoked,
    bad signature, replay, expired. The audit log keeps the real reason."""
    status = 401
    public = "not authorized"

    def __init__(self, reason: str = "not authorized"):
        super().__init__("not authorized")
        self.reason = reason


class Forbidden(WhoDatError):
    status = 403
    public = "forbidden"


class NotFound(WhoDatError):
    status = 404
    public = "not found"


class Conflict(WhoDatError):
    status = 409
    public = "conflict"


class TooMany(WhoDatError):
    status = 429
    public = "too many open challenges"


class VaultLocked(WhoDatError):
    """No root key, or the wrong one. The vault fails closed."""
    status = 503
    public = "vault locked: root key missing or wrong"


# ── encoding helpers ──────────────────────────────────────────────────────────

def b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64d(text: str) -> bytes:
    if not isinstance(text, str):
        raise BadRequest("expected base64 text")
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except Exception as exc:  # binascii.Error, ValueError
        raise BadRequest("invalid base64") from exc


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── keys ──────────────────────────────────────────────────────────────────────

def generate_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def public_raw(priv: Ed25519PrivateKey) -> bytes:
    return priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def public_key_b64(priv: Ed25519PrivateKey) -> str:
    return b64e(public_raw(priv))


def load_public_key(pub_b64: str) -> Ed25519PublicKey:
    raw = b64d(pub_b64)
    if len(raw) != 32:
        raise BadRequest("public key must be a 32-byte Ed25519 key")
    return Ed25519PublicKey.from_public_bytes(raw)


def _derive_id(prefix: str, label: bytes, pub_b64: str) -> str:
    raw = b64d(pub_b64)
    if len(raw) != 32:
        raise BadRequest("public key must be a 32-byte Ed25519 key")
    digest = hashlib.sha256(label + raw).digest()
    return prefix + base64.b32encode(digest).decode("ascii").lower()[:26]


def system_id_for(pub_b64: str) -> str:
    """A system's id is derived from its public key, so it cannot be claimed by another key."""
    return _derive_id("sys_", b"whodat-system|", pub_b64)


def owner_id_for(pub_b64: str) -> str:
    return _derive_id("own_", b"whodat-owner|", pub_b64)


def fingerprint(pub_b64: str) -> str:
    return "SHA256:" + sha256_hex(b64d(pub_b64))[:32]


def sign(priv: Ed25519PrivateKey, domain: bytes, payload: dict) -> str:
    return b64e(priv.sign(domain + canonical(payload)))


def verify(pub_b64: str, domain: bytes, payload: dict, signature_b64: str) -> bool:
    try:
        sig = b64d(signature_b64)
        if len(sig) != 64:
            return False
        load_public_key(pub_b64).verify(sig, domain + canonical(payload))
        return True
    except (InvalidSignature, WhoDatError, ValueError):
        return False


def _private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def write_private_file(path: Path, data: bytes) -> None:
    """Create a new 0600 file. Never overwrites: losing a key is not undoable."""
    path = Path(path)
    _private_dir(path.parent)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def check_private_perms(path: Path) -> None:
    if os.getenv("WHODAT_ALLOW_INSECURE_PERMS") == "1" or os.name != "posix":
        return
    mode = os.stat(path).st_mode & 0o777
    if mode & 0o077:
        raise WhoDatError(f"{path} is readable by other users (mode {oct(mode)}); run: chmod 600 {path}")


def save_private_key(path: Path, priv: Ed25519PrivateKey, passphrase: bytes | None = None) -> None:
    enc = (serialization.BestAvailableEncryption(passphrase) if passphrase
           else serialization.NoEncryption())
    pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, enc)
    write_private_file(Path(path), pem)


def load_private_key(path: Path, passphrase: bytes | None = None) -> Ed25519PrivateKey:
    path = Path(path)
    check_private_perms(path)
    key = serialization.load_pem_private_key(path.read_bytes(), password=passphrase)
    if not isinstance(key, Ed25519PrivateKey):
        raise WhoDatError(f"{path} is not an Ed25519 key")
    return key


# ── root key (vault master key, provisioned separately from the database) ──────

def default_home() -> Path:
    return Path(os.getenv("WHODAT_HOME") or (Path.home() / ".config" / "one2lvos" / "whodat")).expanduser()


def default_root_key_file() -> Path:
    # Deliberately NOT inside WHODAT_HOME: copying the registry folder must not carry the key.
    return Path(os.getenv("WHODAT_ROOT_KEY_FILE")
                or (Path.home() / ".config" / "one2lvos" / "whodat-root.key")).expanduser()


def create_root_key(path: Path | None = None) -> Path:
    path = Path(path or default_root_key_file())
    write_private_file(path, (b64e(os.urandom(32)) + "\n").encode())
    return path


def load_root_key(path: Path | None = None) -> bytes | None:
    """WHODAT_ROOT_KEY (base64, e.g. injected by a secret manager) wins over the file.
    Returns None when neither exists: the registry still answers Who Dat, but the vault stays locked."""
    env = os.getenv("WHODAT_ROOT_KEY")
    if env:
        key = b64d(env.strip())
    else:
        path = Path(path or default_root_key_file())
        if not path.exists():
            return None
        check_private_perms(path)
        key = b64d(path.read_text().strip())
    if len(key) != 32:
        raise VaultLocked("root key must be 32 bytes")
    return key


# ── registry ──────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS owners (
    owner_id TEXT PRIMARY KEY, email TEXT NOT NULL, public_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL, created_at INTEGER NOT NULL, created_via TEXT NOT NULL,
    disabled_at INTEGER);
CREATE TABLE IF NOT EXISTS systems (
    system_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES owners(owner_id),
    public_key TEXT NOT NULL UNIQUE, label TEXT NOT NULL, scope TEXT NOT NULL,
    status TEXT NOT NULL, enrolled_at INTEGER NOT NULL, revoked_at INTEGER,
    last_seen_at INTEGER, last_whose_data_sha256 TEXT);
CREATE TABLE IF NOT EXISTS challenges (
    challenge_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, purpose TEXT NOT NULL,
    nonce TEXT NOT NULL, issued_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
    used_at INTEGER);
CREATE INDEX IF NOT EXISTS challenges_subject ON challenges(subject_id);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY, system_id TEXT NOT NULL, owner_id TEXT NOT NULL,
    issued_at INTEGER NOT NULL, expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS admin_nonces (
    owner_id TEXT NOT NULL, nonce TEXT NOT NULL, ts INTEGER NOT NULL,
    PRIMARY KEY (owner_id, nonce));
CREATE TABLE IF NOT EXISTS secrets (
    owner_id TEXT NOT NULL REFERENCES owners(owner_id), name TEXT NOT NULL,
    version INTEGER NOT NULL, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
    PRIMARY KEY (owner_id, name));
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, event TEXT NOT NULL,
    outcome TEXT NOT NULL, owner_id TEXT, subject_id TEXT, detail TEXT NOT NULL,
    prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
"""


class Registry:
    """One Who Dat registry: owners, their enrolled systems, their encrypted keys."""

    def __init__(self, db_path: Path, root_key: bytes | None, now: Callable[[], float] = time.time):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise NotFound(f"no Who Dat registry at {self.db_path} (run: python3 -m whodat init)")
        self._now = now
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.db_path), check_same_thread=False,
                                   isolation_level=None, timeout=10)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)
        self.registry_id = self._meta("registry_id")
        if not self.registry_id:
            raise WhoDatError("registry database has no registry_id")
        self._root_key = None
        if root_key is not None:
            self.unlock(root_key)

    # ── setup ──
    @classmethod
    def create(cls, db_path: Path, root_key: bytes, now: Callable[[], float] = time.time) -> "Registry":
        db_path = Path(db_path)
        if db_path.exists():
            raise Conflict(f"a registry already exists at {db_path}")
        if len(root_key) != 32:
            raise BadRequest("root key must be 32 bytes")
        _private_dir(db_path.parent)
        fd = os.open(str(db_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        db = sqlite3.connect(str(db_path), isolation_level=None)
        db.executescript(SCHEMA)
        rid = "rid_" + b64e(os.urandom(12))
        db.execute("INSERT INTO meta VALUES ('registry_id', ?)", (rid,))
        db.execute("INSERT INTO meta VALUES ('root_check', ?)", (cls._root_check(root_key, rid),))
        db.execute("INSERT INTO meta VALUES ('created_at', ?)", (str(int(now())),))
        db.close()
        reg = cls(db_path, root_key, now=now)
        reg._audit("registry.create", "ok", None, None, {"registry_id": rid})
        return reg

    @staticmethod
    def _root_check(root_key: bytes, registry_id: str) -> str:
        return hmac.new(root_key, b"whodat-root-check|" + registry_id.encode(), hashlib.sha256).hexdigest()

    def unlock(self, root_key: bytes) -> None:
        expected = self._meta("root_check")
        if not expected or not hmac.compare_digest(expected, self._root_check(root_key, self.registry_id)):
            raise VaultLocked("wrong root key for this registry")
        self._root_key = root_key

    @property
    def vault_unlocked(self) -> bool:
        return self._root_key is not None

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # ── internals ──
    def now(self) -> int:
        return int(self._now())

    def _meta(self, key: str) -> str | None:
        row = self._db.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
        return row["v"] if row else None

    def _tx(self):
        reg = self

        class _T:
            def __enter__(self):
                reg._lock.acquire()
                reg._db.execute("BEGIN IMMEDIATE")
                return reg._db

            def __exit__(self, et, ev, tb):
                try:
                    reg._db.execute("COMMIT" if et is None or issubclass(et, WhoDatError) else "ROLLBACK")
                finally:
                    reg._lock.release()
                return False
        return _T()

    def _audit(self, event: str, outcome: str, owner_id: str | None, subject_id: str | None,
               detail: dict, db: sqlite3.Connection | None = None) -> None:
        def write(conn):
            prev = conn.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
            prev_hash = prev["hash"] if prev else "0" * 64
            ts = self.now()
            d = json.dumps(detail, sort_keys=True, ensure_ascii=False)
            h = sha256_hex(canonical([prev_hash, ts, event, outcome, owner_id, subject_id, d]))
            conn.execute("INSERT INTO audit (ts, event, outcome, owner_id, subject_id, detail, prev_hash, hash)"
                         " VALUES (?,?,?,?,?,?,?,?)", (ts, event, outcome, owner_id, subject_id, d, prev_hash, h))
        if db is not None:
            write(db)
        else:
            with self._tx() as conn:
                write(conn)

    def verify_audit_chain(self) -> bool:
        prev_hash = "0" * 64
        for r in self._db.execute("SELECT * FROM audit ORDER BY id"):
            h = sha256_hex(canonical([prev_hash, r["ts"], r["event"], r["outcome"], r["owner_id"],
                                      r["subject_id"], r["detail"]]))
            if r["prev_hash"] != prev_hash or r["hash"] != h:
                return False
            prev_hash = h
        return True

    def _purge(self, conn: sqlite3.Connection) -> None:
        now = self.now()
        conn.execute("DELETE FROM challenges WHERE expires_at < ?", (now - 3600,))
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.execute("DELETE FROM admin_nonces WHERE ts < ?", (now - 4 * ADMIN_SKEW,))

    def _owner(self, owner_id: str) -> sqlite3.Row | None:
        return self._db.execute("SELECT * FROM owners WHERE owner_id=?", (owner_id,)).fetchone()

    def _system(self, system_id: str) -> sqlite3.Row | None:
        return self._db.execute("SELECT * FROM systems WHERE system_id=?", (system_id,)).fetchone()

    # ── owners (operator = whoever holds the registry host; local CLI only) ──
    def create_owner(self, email: str, owner_public_key: str, via: str = "operator") -> str:
        email = (email or "").strip()
        if not EMAIL_RE.match(email):
            raise BadRequest("a valid email address is required (used as the owner's label)")
        owner_id = owner_id_for(owner_public_key)
        load_public_key(owner_public_key)
        with self._tx() as conn:
            if conn.execute("SELECT 1 FROM owners WHERE owner_id=?", (owner_id,)).fetchone():
                raise Conflict("owner key already registered")
            conn.execute("INSERT INTO owners VALUES (?,?,?,?,?,?,NULL)",
                         (owner_id, email, owner_public_key, "active", self.now(), via))
            self._audit("owner.create", "ok", owner_id, owner_id, {"email": email, "via": via}, conn)
        return owner_id

    def set_owner_status(self, owner_id: str, active: bool) -> None:
        with self._tx() as conn:
            if not conn.execute("SELECT 1 FROM owners WHERE owner_id=?", (owner_id,)).fetchone():
                raise NotFound("no such owner")
            conn.execute("UPDATE owners SET status=?, disabled_at=? WHERE owner_id=?",
                         ("active" if active else "disabled", None if active else self.now(), owner_id))
            if not active:
                conn.execute("DELETE FROM sessions WHERE owner_id=?", (owner_id,))
            self._audit("owner.enable" if active else "owner.disable", "ok", owner_id, owner_id, {}, conn)

    def list_owners(self) -> list[dict]:
        rows = self._db.execute("SELECT owner_id, email, status, created_at, created_via FROM owners").fetchall()
        return [dict(r) for r in rows]

    # ── Who Dat? (challenge) ──
    def issue_challenge(self, subject_id: str, purpose: str = "boot") -> dict:
        if purpose == "boot":
            if not isinstance(subject_id, str) or not SYSTEM_ID_RE.match(subject_id):
                raise BadRequest("system_id must look like sys_ followed by 26 characters")
        elif purpose == "register_owner":
            if not isinstance(subject_id, str) or not OWNER_ID_RE.match(subject_id):
                raise BadRequest("owner_id must look like own_ followed by 26 characters")
        else:
            raise BadRequest("purpose must be boot or register_owner")
        now = self.now()
        with self._tx() as conn:
            self._purge(conn)
            open_count = conn.execute(
                "SELECT COUNT(*) FROM challenges WHERE subject_id=? AND used_at IS NULL AND expires_at>=?",
                (subject_id, now)).fetchone()[0]
            if open_count >= MAX_OPEN_CHALLENGES:
                raise TooMany()
            ch = {"challenge_id": "chl_" + b64e(os.urandom(16)), "nonce": b64e(os.urandom(32)),
                  "issued_at": now, "expires_at": now + CHALLENGE_TTL}
            conn.execute("INSERT INTO challenges VALUES (?,?,?,?,?,?,NULL)",
                         (ch["challenge_id"], subject_id, purpose, ch["nonce"], now, ch["expires_at"]))
        # Issued for any well-formed id: whether a system is enrolled is not revealed here.
        return {"protocol": PROTOCOL, "question": "Who Dat?", "registry_id": self.registry_id,
                "subject_id": subject_id, "purpose": purpose, **ch}

    @staticmethod
    def response_payload(registry_id: str, challenge: dict, system_id: str, whose_data: dict) -> dict:
        """Exactly what a system signs to answer Who Dat. Shared by client and server."""
        return {"proto": PROTOCOL, "kind": "boot", "registry_id": registry_id,
                "challenge_id": challenge["challenge_id"], "nonce": challenge["nonce"],
                "expires_at": int(challenge["expires_at"]), "system_id": system_id,
                "purpose": "boot", "whose_data_sha256": sha256_hex(canonical(whose_data))}

    def _consume(self, conn, challenge_id: str, subject_id: str, purpose: str) -> sqlite3.Row:
        """Atomically burn the challenge. Burned before the signature is checked, so a
        failed attempt cannot be retried against the same nonce."""
        if not isinstance(challenge_id, str) or len(challenge_id) > 64:
            raise AuthError("malformed challenge id")
        now = self.now()
        row = conn.execute("SELECT * FROM challenges WHERE challenge_id=?", (challenge_id,)).fetchone()
        cur = conn.execute(
            "UPDATE challenges SET used_at=? WHERE challenge_id=? AND used_at IS NULL AND expires_at>=?"
            " AND subject_id=? AND purpose=?", (now, challenge_id, now, subject_id, purpose))
        if cur.rowcount != 1:
            if row is None:
                reason = "unknown challenge"
            elif row["used_at"] is not None:
                reason = "replay: challenge already used"
            elif row["expires_at"] < now:
                reason = "challenge expired"
            elif row["subject_id"] != subject_id:
                reason = "challenge issued to a different subject"
            else:
                reason = "challenge purpose mismatch"
            raise AuthError(reason)
        return row

    # ── Whose Data? (response) ──
    def respond(self, challenge_id: str, system_id: str, whose_data: dict, signature: str) -> dict:
        if not isinstance(whose_data, dict):
            raise BadRequest("whose_data must be an object")
        if len(canonical(whose_data)) > MAX_WHOSE_DATA_BYTES:
            raise BadRequest("whose_data too large")
        if not isinstance(system_id, str) or not SYSTEM_ID_RE.match(system_id):
            raise BadRequest("malformed system_id")
        summary = _whose_data_summary(whose_data)
        wd_hash = sha256_hex(canonical(whose_data))
        try:
            with self._tx() as conn:
                ch = self._consume(conn, challenge_id, system_id, "boot")
                sysrow = conn.execute("SELECT * FROM systems WHERE system_id=?", (system_id,)).fetchone()
                if sysrow is None:
                    raise AuthError("system not enrolled")
                if sysrow["status"] != "active":
                    raise AuthError("system revoked")
                owner = conn.execute("SELECT * FROM owners WHERE owner_id=?", (sysrow["owner_id"],)).fetchone()
                if owner is None or owner["status"] != "active":
                    raise AuthError("owner disabled")
                payload = self.response_payload(self.registry_id, dict(ch), system_id, whose_data)
                if not verify(sysrow["public_key"], DOMAIN_RESPONSE, payload, signature):
                    raise AuthError("bad signature (no proof of possession of the enrolled key)")
                token = "wdt_" + b64e(os.urandom(32))
                now = self.now()
                conn.execute("INSERT INTO sessions VALUES (?,?,?,?,?)",
                             (sha256_hex(token.encode()), system_id, owner["owner_id"], now, now + SESSION_TTL))
                conn.execute("UPDATE systems SET last_seen_at=?, last_whose_data_sha256=? WHERE system_id=?",
                             (now, wd_hash, system_id))
                self._audit("whodat.respond", "ok", owner["owner_id"], system_id,
                            {"whose_data_sha256": wd_hash, "whose_data": summary}, conn)
                return {"ok": True, "session_token": token, "expires_at": now + SESSION_TTL,
                        "system_id": system_id, "owner_id": owner["owner_id"],
                        "scope": json.loads(sysrow["scope"])}
        except AuthError as err:
            owner_id = None
            row = self._system(system_id)
            if row is not None:
                owner_id = row["owner_id"]
            self._audit("whodat.respond", "denied", owner_id, system_id,
                        {"reason": err.reason, "whose_data_sha256": wd_hash, "whose_data": summary})
            raise

    # ── sessions and secret retrieval ──
    def _session(self, token: str) -> sqlite3.Row:
        if not isinstance(token, str) or not token.startswith("wdt_") or len(token) > 80:
            raise AuthError("malformed session token")
        row = self._db.execute("SELECT * FROM sessions WHERE token_hash=?", (sha256_hex(token.encode()),)).fetchone()
        if row is None:
            raise AuthError("unknown or revoked session")
        if row["expires_at"] < self.now():
            raise AuthError("session expired")
        sysrow = self._system(row["system_id"])
        owner = self._owner(row["owner_id"])
        # Revocation bites immediately, even for sessions issued before it.
        if sysrow is None or sysrow["status"] != "active" or sysrow["owner_id"] != row["owner_id"]:
            raise AuthError("system revoked")
        if owner is None or owner["status"] != "active":
            raise AuthError("owner disabled")
        return row

    def fetch_secrets(self, token: str, names: Iterable[str] | None = None) -> dict[str, str]:
        try:
            sess = self._session(token)
        except AuthError as err:
            self._audit("secrets.fetch", "denied", None, None, {"reason": err.reason})
            raise
        if not self.vault_unlocked:
            self._audit("secrets.fetch", "denied", sess["owner_id"], sess["system_id"], {"reason": "vault locked"})
            raise VaultLocked()
        scope = json.loads(self._system(sess["system_id"])["scope"])
        wanted = None if names is None else {n for n in names if n}
        rows = self._db.execute("SELECT * FROM secrets WHERE owner_id=?", (sess["owner_id"],)).fetchall()
        out: dict[str, str] = {}
        for r in rows:
            if "*" not in scope and r["name"] not in scope:
                continue
            if wanted is not None and r["name"] not in wanted:
                continue
            out[r["name"]] = self._decrypt(sess["owner_id"], r)
        self._audit("secrets.fetch", "ok", sess["owner_id"], sess["system_id"], {"names": sorted(out)})
        return out

    # ── vault crypto ──
    def _owner_key(self, owner_id: str) -> bytes:
        if self._root_key is None:
            raise VaultLocked()
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=self.registry_id.encode(),
                    info=b"whodat/1 vault|" + owner_id.encode()).derive(self._root_key)

    @staticmethod
    def _aad(owner_id: str, name: str, version: int) -> bytes:
        return canonical({"o": owner_id, "n": name, "v": version})

    def _decrypt(self, owner_id: str, row: sqlite3.Row) -> str:
        try:
            pt = AESGCM(self._owner_key(owner_id)).decrypt(
                row["nonce"], row["ciphertext"], self._aad(owner_id, row["name"], row["version"]))
        except InvalidTag as exc:
            raise VaultLocked("a stored secret failed authentication (tampered or wrong root key)") from exc
        return pt.decode("utf-8")

    # ── owner-signed admin ──
    @staticmethod
    def admin_payload(registry_id: str, owner_id: str, op: str, params: dict, ts: int, nonce: str) -> dict:
        return {"proto": PROTOCOL, "kind": "admin", "registry_id": registry_id, "owner_id": owner_id,
                "op": op, "params": params, "ts": int(ts), "nonce": nonce}

    def admin(self, envelope: dict) -> dict:
        """Run one owner-signed operation. The owner key (not the system key, not a
        password, not Lumenis's say-so) is what authorizes enrolling, revoking and
        writing keys."""
        if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), dict):
            raise BadRequest("expected {payload, signature}")
        p = envelope["payload"]
        sig = envelope.get("signature", "")
        owner_id = p.get("owner_id")
        op = p.get("op")
        params = p.get("params") if isinstance(p.get("params"), dict) else None
        try:
            if params is None or not isinstance(op, str) or not isinstance(owner_id, str) \
                    or not OWNER_ID_RE.match(owner_id):
                raise AuthError("malformed admin payload")
            ts, nonce = p.get("ts"), p.get("nonce")
            if not isinstance(ts, int) or not isinstance(nonce, str) or not (16 <= len(nonce) <= 64):
                raise AuthError("malformed admin payload")
            rebuilt = self.admin_payload(self.registry_id, owner_id, op, params, ts, nonce)
            if rebuilt != p:
                raise AuthError("payload fields or registry id do not match")
            if abs(self.now() - ts) > ADMIN_SKEW:
                raise AuthError("admin request timestamp outside the allowed window")
            owner = self._owner(owner_id)
            if owner is None or owner["status"] != "active":
                raise AuthError("unknown or disabled owner")
            if not verify(owner["public_key"], DOMAIN_ADMIN, p, sig):
                raise AuthError("bad owner signature")
            with self._tx() as conn:
                self._purge(conn)
                try:
                    conn.execute("INSERT INTO admin_nonces VALUES (?,?,?)", (owner_id, nonce, ts))
                except sqlite3.IntegrityError:
                    raise AuthError("replay: admin nonce already used")
        except AuthError as err:
            self._audit("admin." + (op if isinstance(op, str) else "?")[:32], "denied",
                        owner_id if isinstance(owner_id, str) else None, None, {"reason": err.reason})
            raise
        handler = getattr(self, "_op_" + op, None) if re.match(r"^[a-z_]{1,32}$", op) else None
        if handler is None:
            raise BadRequest(f"unknown op {op!r}")
        return handler(owner_id, params)

    def _op_enroll_system(self, owner_id: str, params: dict) -> dict:
        pub = params.get("public_key")
        load_public_key(pub)
        label = str(params.get("label") or "system")[:80]
        scope = params.get("scope", ["*"])
        if not isinstance(scope, list) or not scope or not all(
                isinstance(s, str) and (s == "*" or NAME_RE.match(s)) for s in scope):
            raise BadRequest("scope must be a list of secret names, or [\"*\"]")
        system_id = system_id_for(pub)
        with self._tx() as conn:
            existing = conn.execute("SELECT * FROM systems WHERE system_id=?", (system_id,)).fetchone()
            if existing is not None:
                if existing["owner_id"] != owner_id:
                    self._audit("admin.enroll_system", "denied", owner_id, system_id,
                                {"reason": "key already enrolled by another owner"}, conn)
                    raise Conflict("that system key is already enrolled")
                if existing["status"] == "revoked":
                    raise Conflict("that system key was revoked; generate a new key")
                raise Conflict("system already enrolled")
            n = conn.execute("SELECT COUNT(*) FROM systems WHERE owner_id=? AND status='active'",
                             (owner_id,)).fetchone()[0]
            if n >= MAX_SYSTEMS_PER_OWNER:
                raise Forbidden("too many systems for this owner")
            conn.execute("INSERT INTO systems VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL)",
                         (system_id, owner_id, pub, label, json.dumps(sorted(set(scope))), "active", self.now()))
            self._audit("admin.enroll_system", "ok", owner_id, system_id,
                        {"label": label, "scope": sorted(set(scope)), "fingerprint": fingerprint(pub)}, conn)
        return {"ok": True, "system_id": system_id, "fingerprint": fingerprint(pub)}

    def _op_revoke_system(self, owner_id: str, params: dict) -> dict:
        system_id = params.get("system_id")
        with self._tx() as conn:
            row = conn.execute("SELECT * FROM systems WHERE system_id=?", (system_id,)).fetchone()
            if row is None or row["owner_id"] != owner_id:
                self._audit("admin.revoke_system", "denied", owner_id, system_id if isinstance(system_id, str) else None,
                            {"reason": "not this owner's system"}, conn)
                raise NotFound("no such system for this owner")
            conn.execute("UPDATE systems SET status='revoked', revoked_at=? WHERE system_id=?", (self.now(), system_id))
            killed = conn.execute("DELETE FROM sessions WHERE system_id=?", (system_id,)).rowcount
            self._audit("admin.revoke_system", "ok", owner_id, system_id, {"sessions_ended": killed}, conn)
        return {"ok": True, "system_id": system_id, "status": "revoked"}

    def _op_put_secret(self, owner_id: str, params: dict) -> dict:
        name, value = params.get("name"), params.get("value")
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise BadRequest("secret names are env-var style: letters, digits, underscore")
        if not isinstance(value, str) or len(value.encode()) > MAX_SECRET_BYTES:
            raise BadRequest("secret value must be text up to 64 KB")
        key = self._owner_key(owner_id)          # VaultLocked if no root key
        with self._tx() as conn:
            row = conn.execute("SELECT version FROM secrets WHERE owner_id=? AND name=?", (owner_id, name)).fetchone()
            if row is None:
                n = conn.execute("SELECT COUNT(*) FROM secrets WHERE owner_id=?", (owner_id,)).fetchone()[0]
                if n >= MAX_SECRETS_PER_OWNER:
                    raise Forbidden("too many secrets for this owner")
            version = 1 if row is None else row["version"] + 1
            nonce = os.urandom(12)
            ct = AESGCM(key).encrypt(nonce, value.encode("utf-8"), self._aad(owner_id, name, version))
            now = self.now()
            conn.execute("INSERT INTO secrets VALUES (?,?,?,?,?,?,?) ON CONFLICT(owner_id, name) DO UPDATE SET"
                         " version=excluded.version, nonce=excluded.nonce, ciphertext=excluded.ciphertext,"
                         " updated_at=excluded.updated_at", (owner_id, name, version, nonce, ct, now, now))
            self._audit("admin.put_secret", "ok", owner_id, None, {"name": name, "version": version}, conn)
        return {"ok": True, "name": name, "version": version}

    def _op_delete_secret(self, owner_id: str, params: dict) -> dict:
        name = params.get("name")
        with self._tx() as conn:
            n = conn.execute("DELETE FROM secrets WHERE owner_id=? AND name=?", (owner_id, name)).rowcount
            self._audit("admin.delete_secret", "ok" if n else "missing", owner_id, None, {"name": str(name)[:128]}, conn)
        if not n:
            raise NotFound("no such secret")
        return {"ok": True, "name": name, "deleted": True}

    def _op_list_secrets(self, owner_id: str, params: dict) -> dict:
        rows = self._db.execute("SELECT name, version, updated_at FROM secrets WHERE owner_id=? ORDER BY name",
                                (owner_id,)).fetchall()
        return {"ok": True, "secrets": [dict(r) for r in rows]}

    def _op_list_systems(self, owner_id: str, params: dict) -> dict:
        rows = self._db.execute("SELECT system_id, label, scope, status, enrolled_at, revoked_at, last_seen_at"
                                " FROM systems WHERE owner_id=? ORDER BY enrolled_at", (owner_id,)).fetchall()
        return {"ok": True, "systems": [{**dict(r), "scope": json.loads(r["scope"])} for r in rows]}

    def _op_audit(self, owner_id: str, params: dict) -> dict:
        limit = max(1, min(int(params.get("limit", 50)), 500))
        rows = self._db.execute("SELECT id, ts, event, outcome, subject_id, detail FROM audit WHERE owner_id=?"
                                " ORDER BY id DESC LIMIT ?", (owner_id, limit)).fetchall()
        return {"ok": True, "events": [{**dict(r), "detail": json.loads(r["detail"])} for r in rows]}

    # ── optional self-registration over the network (off unless WHODAT_OPEN_REGISTRATION=1) ──
    @staticmethod
    def register_payload(registry_id: str, challenge: dict, owner_id: str, email: str, public_key: str) -> dict:
        return {"proto": PROTOCOL, "kind": "register_owner", "registry_id": registry_id,
                "challenge_id": challenge["challenge_id"], "nonce": challenge["nonce"],
                "expires_at": int(challenge["expires_at"]), "owner_id": owner_id, "email": email,
                "public_key": public_key}

    def register_owner(self, email: str, public_key: str, challenge_id: str, signature: str) -> str:
        """Proof of possession of the new owner key is required. The email is a label:
        it is NOT verified and grants nothing by itself."""
        owner_id = owner_id_for(public_key)
        try:
            with self._tx() as conn:
                ch = self._consume(conn, challenge_id, owner_id, "register_owner")
                payload = self.register_payload(self.registry_id, dict(ch), owner_id, (email or "").strip(), public_key)
                if not verify(public_key, DOMAIN_REGISTER, payload, signature):
                    raise AuthError("bad registration signature")
        except AuthError as err:
            self._audit("owner.register", "denied", owner_id, owner_id, {"reason": err.reason})
            raise
        return self.create_owner(email, public_key, via="self-registration")

    # ── status (no secrets) ──
    def status(self) -> dict:
        q = lambda sql: self._db.execute(sql).fetchone()[0]  # noqa: E731
        return {"protocol": PROTOCOL, "registry_id": self.registry_id,
                "vault": "unlocked" if self.vault_unlocked else "locked",
                "owners": q("SELECT COUNT(*) FROM owners"),
                "systems_active": q("SELECT COUNT(*) FROM systems WHERE status='active'"),
                "systems_revoked": q("SELECT COUNT(*) FROM systems WHERE status='revoked'"),
                "secrets": q("SELECT COUNT(*) FROM secrets"),
                "audit_chain_ok": self.verify_audit_chain()}


def _whose_data_summary(whose_data: dict) -> dict:
    """What gets written to the audit log from a system's self-description: a few short
    string fields. It is logged as a claim, never trusted as proof."""
    out = {}
    for k in ("hostname", "platform", "software", "git_commit", "machine_id_sha256", "provenance"):
        v = whose_data.get(k)
        if isinstance(v, (str, int, float)):
            out[k] = str(v)[:200]
        elif isinstance(v, dict):
            out[k] = {str(a)[:40]: str(b)[:200] for a, b in list(v.items())[:8]}
    return out
