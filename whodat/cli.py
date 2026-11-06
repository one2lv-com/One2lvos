"""python3 -m whodat <command>

Set up this installation (anyone can do this on their own copy):
  init --email you@example.com          generate this installation's keys and its own registry + vault
  init --email you@x.com --registry-url https://host   join someone's shared registry instead

Keys you add yourself (third-party API keys: NVIDIA, GitHub, Supabase ...):
  secret put NAME                       prompts for the value (never typed on the command line)
  secret import path/to/.env            import YOUR OWN .env into YOUR vault
  secret list | secret delete NAME

Identity:
  status | handshake | keygen --out FILE | enroll --public-key K --label L [--scope A,B] | revoke SYSTEM_ID
  systems | audit [--limit N]

Boot:
  boot-env [--only-unset]               handshake, then print `export NAME='value'` lines for eval

Registry host operator:
  owner add --email E --public-key K | owner disable OWNER_ID | owner list | serve [--host H --port P]

Release safety:
  dist-check PATH [--env FILE ...]      fail if PATH (dir, .tar.gz, .zip) holds keys or any value from FILE
"""

from __future__ import annotations

import argparse
import getpass
import io
import json
import os
import re
import shlex
import sys
import tarfile
import time
import zipfile
from pathlib import Path

from . import core
from .client import (HttpTransport, Identity, LocalTransport, collect_whose_data, handshake,
                     open_local_registry, register_owner_remote, signed_admin, transport_for)
from .core import NAME_RE, Registry, WhoDatError, generate_private_key, public_key_b64


def _out(obj) -> None:
    print(json.dumps(obj, indent=2))


def _err(msg: str) -> None:
    print(f"whodat: {msg}", file=sys.stderr)


def parse_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines, optional `export`, optional single/double quotes. No expansion."""
    out: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if not NAME_RE.match(k):
            continue
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        else:
            v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
        out[k] = v
    return out


# ── init (the system key generator) ─────────────────────────────────────────────────

def cmd_init(a) -> int:
    ident = Identity()
    if ident.exists:
        m = ident.meta()
        _err(f"this installation already has an identity ({m['system_id']}, owner {m.get('email')}). "
             f"Nothing was changed. Keys live in {ident.dir}")
        return 1
    email = (a.email or "").strip()
    if not core.EMAIL_RE.match(email):
        _err("give a valid email address with --email (it labels your keys; it is not a password)")
        return 2
    for p in (ident.system_key_path, ident.owner_key_path):
        if p.exists():
            _err(f"{p} already exists but identity.json does not; refusing to overwrite a key. Move it aside first.")
            return 1
    passphrase = Identity._passphrase()
    owner_key, system_key = generate_private_key(), generate_private_key()
    owner_pub, system_pub = public_key_b64(owner_key), public_key_b64(system_key)
    label = a.label or os.uname().nodename[:60]

    if a.registry_url:
        transport = HttpTransport(a.registry_url)
        info = transport.info()
        registry_id = info["registry_id"]
        core.save_private_key(ident.owner_key_path, owner_key, passphrase)
        core.save_private_key(ident.system_key_path, system_key, passphrase)
        if info.get("open_registration"):
            owner_id = register_owner_remote(transport, owner_key, email)
        else:
            owner_id = core.owner_id_for(owner_pub)
            ident.write_meta({"protocol": core.PROTOCOL, "email": email, "label": label,
                              "registry_id": registry_id, "registry_url": a.registry_url,
                              "owner_id": owner_id, "system_id": core.system_id_for(system_pub),
                              "enrolled": False, "created_at": int(time.time())})
            print("Keys generated. That registry does not take self-registration, so its operator must add you:")
            print(f"  python3 -m whodat owner add --email {shlex.quote(email)} --public-key {owner_pub}")
            print("Then run here:  python3 -m whodat enroll --self")
            return 0
    else:
        home = ident.home
        db = home / "registry.db"
        if db.exists():
            _err(f"a registry already exists at {db} but this machine has no identity; use `owner add` + `enroll`")
            return 1
        root_path = core.default_root_key_file()
        created_root = False
        if os.getenv("WHODAT_ROOT_KEY") is None and not root_path.exists():
            core.create_root_key(root_path)
            created_root = True
        root = core.load_root_key()
        if root is None:
            _err("no root key available")
            return 1
        reg = Registry.create(db, root)
        transport = LocalTransport(reg)
        registry_id = reg.registry_id
        core.save_private_key(ident.owner_key_path, owner_key, passphrase)
        core.save_private_key(ident.system_key_path, system_key, passphrase)
        owner_id = reg.create_owner(email, owner_pub, via="local-init")
        if created_root:
            print(f"Root key (vault master key) created: {root_path}")
            print("  Back it up somewhere other than this machine. Without it the vault cannot be opened.")

    res = transport.admin(signed_admin(owner_key, owner_id, registry_id, "enroll_system",
                                       {"public_key": system_pub, "label": label, "scope": ["*"]}))
    ident.write_meta({"protocol": core.PROTOCOL, "email": email, "label": label, "registry_id": registry_id,
                      "registry_url": a.registry_url or "", "owner_id": owner_id,
                      "system_id": res["system_id"], "enrolled": True, "enrolled_at": int(time.time()),
                      "system_fingerprint": core.fingerprint(system_pub),
                      "owner_fingerprint": core.fingerprint(owner_pub)})
    print(f"Who Dat identity created for {email}")
    print(f"  owner   {owner_id}  {core.fingerprint(owner_pub)}")
    print(f"  system  {res['system_id']}  {core.fingerprint(system_pub)}")
    print(f"  keys    {ident.dir} (0600{', passphrase-encrypted' if passphrase else ''})")
    print("Next: add your own API keys with `python3 -m whodat secret put NAME` or `secret import .env`.")
    return 0


def _owner_ctx(a):
    ident = Identity()
    m = ident.meta()
    return ident, m, transport_for(ident, getattr(a, "registry_url", None))


def _admin(a, op: str, params: dict) -> dict:
    ident, m, t = _owner_ctx(a)
    return t.admin(signed_admin(ident.owner_key(), m["owner_id"], m["registry_id"], op, params))


def cmd_enroll(a) -> int:
    ident = Identity()
    m = ident.meta()
    if a.self:
        pub = public_key_b64(ident.system_key())
        label = m.get("label", "system")
    else:
        if not a.public_key:
            _err("give --public-key (from `whodat keygen` on the other machine) or --self")
            return 2
        pub, label = a.public_key, a.label or "system"
    scope = [s.strip() for s in (a.scope or "*").split(",") if s.strip()]
    res = _admin(a, "enroll_system", {"public_key": pub, "label": label, "scope": scope})
    if a.self:
        m.update({"enrolled": True, "enrolled_at": int(time.time()), "system_id": res["system_id"]})
        ident.write_meta(m)
    _out(res)
    return 0


def cmd_revoke(a) -> int:
    _out(_admin(a, "revoke_system", {"system_id": a.system_id}))
    return 0


def cmd_systems(a) -> int:
    _out(_admin(a, "list_systems", {}))
    return 0


def cmd_audit(a) -> int:
    _out(_admin(a, "audit", {"limit": a.limit}))
    return 0


def cmd_secret(a) -> int:
    if a.action == "list":
        _out(_admin(a, "list_secrets", {}))
    elif a.action == "delete":
        _out(_admin(a, "delete_secret", {"name": a.name}))
    elif a.action == "put":
        if not a.name:
            _err("secret put NAME")
            return 2
        if a.from_env:
            value = os.environ.get(a.from_env)
            if value is None:
                _err(f"${a.from_env} is not set")
                return 2
        elif not sys.stdin.isatty():
            value = sys.stdin.read().rstrip("\n")
        else:
            value = getpass.getpass(f"Value for {a.name} (hidden): ")
        res = _admin(a, "put_secret", {"name": a.name, "value": value})
        print(f"stored {res['name']} (version {res['version']})")
    elif a.action == "import":
        if not a.name:
            _err("secret import PATH_TO_ENV_FILE")
            return 2
        values = parse_env_file(Path(a.name))
        only = {s for s in (a.only or "").split(",") if s}
        stored = []
        for k, v in values.items():
            if (only and k not in only) or not v or k.startswith("WHODAT_"):
                continue
            _admin(a, "put_secret", {"name": k, "value": v})
            stored.append(k)
        print(f"imported {len(stored)} keys into your vault: {', '.join(stored) or '(none)'}")
    return 0


def cmd_status(a) -> int:
    ident = Identity()
    out = {"home": str(ident.home), "identity": None, "local_registry": None}
    if ident.exists:
        m = ident.meta()
        out["identity"] = {k: m.get(k) for k in ("email", "label", "owner_id", "system_id", "registry_id",
                                                "registry_url", "enrolled", "system_fingerprint")}
        out["identity"]["has_owner_key"] = ident.owner_key_path.exists()
    db = ident.home / "registry.db"
    if db.exists():
        try:
            reg = Registry(db, core.load_root_key())
            out["local_registry"] = reg.status()
        except WhoDatError as e:
            out["local_registry"] = {"error": e.detail}
    out["root_key"] = ("env WHODAT_ROOT_KEY" if os.getenv("WHODAT_ROOT_KEY")
                       else (str(core.default_root_key_file()) if core.default_root_key_file().exists() else "missing"))
    _out(out)
    return 0


def _do_handshake(a):
    ident = Identity()
    m = ident.meta()
    t = transport_for(ident, getattr(a, "registry_url", None))
    sess = handshake(t, ident.system_key(), m["system_id"], collect_whose_data(m))
    return ident, m, t, sess


def cmd_handshake(a) -> int:
    _, m, t, sess = _do_handshake(a)
    names = sorted(t.secrets(sess["session_token"]))
    _out({"ok": True, "system_id": sess["system_id"], "owner_id": sess["owner_id"],
          "session_expires_at": sess["expires_at"], "scope": sess["scope"],
          "keys_available": len(names), "key_names": names})
    return 0


def cmd_boot_env(a) -> int:
    """Prints nothing on stdout unless the whole handshake succeeded (fail closed)."""
    try:
        _, m, t, sess = _do_handshake(a)
        values = t.secrets(sess["session_token"])
    except Exception as e:  # noqa: BLE001 - any failure means no keys
        _err(f"handshake failed, no keys loaded: {getattr(e, 'detail', e)}")
        return 1
    lines, loaded = [], 0
    for k in sorted(values):
        if not NAME_RE.match(k) or k.startswith("WHODAT_"):
            continue
        if a.only_unset and os.environ.get(k):
            continue
        lines.append(f"export {k}={shlex.quote(values[k])}")
        loaded += 1
    lines.append(f"export WHODAT_LOADED_COUNT={loaded}")
    sys.stdout.write("\n".join(lines) + "\n")
    _err(f"Who Dat handshake ok for {m['system_id']}; {loaded} keys exported")
    return 0


def cmd_keygen(a) -> int:
    out = Path(a.out)
    key = generate_private_key()
    core.save_private_key(out, key, Identity._passphrase())
    pub = public_key_b64(key)
    _out({"key_file": str(out), "public_key": pub, "system_id": core.system_id_for(pub),
          "fingerprint": core.fingerprint(pub),
          "next": f"on the owner's machine: python3 -m whodat enroll --public-key {pub} --label NAME"})
    return 0


def cmd_owner(a) -> int:
    reg = open_local_registry()
    if a.action == "add":
        _out({"ok": True, "owner_id": reg.create_owner(a.email, a.public_key, via="operator")})
    elif a.action == "disable":
        reg.set_owner_status(a.owner_id, False)
        _out({"ok": True, "owner_id": a.owner_id, "status": "disabled"})
    elif a.action == "enable":
        reg.set_owner_status(a.owner_id, True)
        _out({"ok": True, "owner_id": a.owner_id, "status": "active"})
    else:
        _out(reg.list_owners())
    return 0


def cmd_serve(a) -> int:
    import uvicorn
    from .api import create_app
    uvicorn.run(create_app(), host=a.host, port=a.port, log_level="warning")
    return 0


# ── dist-check ─────────────────────────────────────────────────────────────────────────

KEY_MARKERS = (b"-----BEGIN PRIVATE KEY-----", b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
               b"-----BEGIN OPENSSH PRIVATE KEY-----", b"-----BEGIN RSA PRIVATE KEY-----",
               b"-----BEGIN EC PRIVATE KEY-----")
STATE_NAMES = {"registry.db", "whodat-root.key", "identity.json", "system.key", "owner.key",
               ".env", "sfcompute_token.json"}
PLACEHOLDER = re.compile(r"^(your[_-]|changeme|xxx|example|<|\$\{|replace|todo|none|null|true|false|\d+$)", re.I)


def _iter_files(path: Path):
    if path.is_dir():
        for p in sorted(path.rglob("*")):
            if p.is_file() and ".git" not in p.relative_to(path).parts:
                try:
                    yield str(p.relative_to(path)), p.read_bytes()
                except OSError:
                    continue
    elif tarfile.is_tarfile(path):
        with tarfile.open(path) as tf:
            for m in tf.getmembers():
                if m.isfile():
                    f = tf.extractfile(m)
                    if f:
                        yield m.name, f.read()
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for n in zf.namelist():
                if not n.endswith("/"):
                    yield n, zf.read(n)
    else:
        yield path.name, path.read_bytes()


def dist_check(path: Path, env_files: list[Path], min_len: int = 12) -> list[dict]:
    needles: dict[bytes, str] = {}
    for ef in env_files:
        for k, v in parse_env_file(ef).items():
            if len(v) >= min_len and not PLACEHOLDER.match(v):
                needles[v.encode()] = k
    hits = []
    for name, data in _iter_files(Path(path)):
        base = name.rsplit("/", 1)[-1]
        if base in STATE_NAMES:
            hits.append({"file": name, "finding": f"key/state file '{base}' must not be distributed"})
        for mk in KEY_MARKERS:
            if mk in data:
                hits.append({"file": name, "finding": "private key block"})
                break
        for needle, var in needles.items():
            if needle in data:
                hits.append({"file": name, "finding": f"contains the value of {var}"})
    return hits


def cmd_dist_check(a) -> int:
    envs = [Path(e) for e in (a.env or [])]
    hits = dist_check(Path(a.path), envs)
    _out({"path": a.path, "env_files_checked": [str(e) for e in envs], "findings": hits, "clean": not hits})
    return 1 if hits else 0


# ── argparse ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python3 -m whodat", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("--email", required=True); s.add_argument("--label")
    s.add_argument("--registry-url"); s.set_defaults(fn=cmd_init)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("handshake"); s.add_argument("--registry-url"); s.set_defaults(fn=cmd_handshake)
    s = sub.add_parser("boot-env"); s.add_argument("--registry-url"); s.add_argument("--only-unset", action="store_true")
    s.set_defaults(fn=cmd_boot_env)
    s = sub.add_parser("keygen"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_keygen)
    s = sub.add_parser("enroll"); s.add_argument("--public-key"); s.add_argument("--label"); s.add_argument("--scope")
    s.add_argument("--self", action="store_true"); s.add_argument("--registry-url"); s.set_defaults(fn=cmd_enroll)
    s = sub.add_parser("revoke"); s.add_argument("system_id"); s.add_argument("--registry-url"); s.set_defaults(fn=cmd_revoke)
    s = sub.add_parser("systems"); s.add_argument("--registry-url"); s.set_defaults(fn=cmd_systems)
    s = sub.add_parser("audit"); s.add_argument("--limit", type=int, default=50); s.add_argument("--registry-url")
    s.set_defaults(fn=cmd_audit)
    s = sub.add_parser("secret"); s.add_argument("action", choices=["put", "list", "delete", "import"])
    s.add_argument("name", nargs="?"); s.add_argument("--from-env"); s.add_argument("--only")
    s.add_argument("--registry-url"); s.set_defaults(fn=cmd_secret)
    s = sub.add_parser("owner"); s.add_argument("action", choices=["add", "disable", "enable", "list"])
    s.add_argument("owner_id", nargs="?"); s.add_argument("--email"); s.add_argument("--public-key")
    s.set_defaults(fn=cmd_owner)
    s = sub.add_parser("serve"); s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=8097)
    s.set_defaults(fn=cmd_serve)
    s = sub.add_parser("dist-check"); s.add_argument("path"); s.add_argument("--env", action="append")
    s.set_defaults(fn=cmd_dist_check)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return a.fn(a)
    except WhoDatError as e:
        _err(e.detail)
        return 1


if __name__ == "__main__":
    sys.exit(main())
