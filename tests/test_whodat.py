"""Who Dat tests: run with  python3 -m pytest tests/test_whodat.py -q"""

import io
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from whodat import core  # noqa: E402
from whodat.client import (Identity, LocalTransport, collect_whose_data, handshake,  # noqa: E402
                           register_owner_remote, signed_admin)
from whodat.core import (AuthError, Conflict, DOMAIN_ADMIN, DOMAIN_RESPONSE, NotFound, Registry,  # noqa: E402
                         VaultLocked, generate_private_key, public_key_b64, sign, system_id_for)


class Clock:
    def __init__(self, t=1_800_000_000):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def env(tmp_path):
    clock = Clock()
    root = os.urandom(32)
    reg = Registry.create(tmp_path / "registry.db", root, now=clock)
    return reg, root, clock, tmp_path


def make_owner(reg, email="a@example.com"):
    k = generate_private_key()
    oid = reg.create_owner(email, public_key_b64(k))
    return k, oid


def admin(reg, okey, oid, op, params, ts=None, nonce=None):
    p = Registry.admin_payload(reg.registry_id, oid, op, params, ts if ts is not None else reg.now(),
                               nonce or core.b64e(os.urandom(18)))
    return reg.admin({"payload": p, "signature": sign(okey, DOMAIN_ADMIN, p)})


def enroll(reg, okey, oid, scope=("*",)):
    sk = generate_private_key()
    res = admin(reg, okey, oid, "enroll_system", {"public_key": public_key_b64(sk), "label": "t", "scope": list(scope)})
    return sk, res["system_id"]


def boot(reg, sk, sid, wd=None):
    return handshake(LocalTransport(reg), sk, sid, wd or {"hostname": "box"})


# ── happy path ──

def test_enrolled_system_gets_its_owners_keys(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "put_secret", {"name": "NVIDIA_API_KEY", "value": "nv-secret-123456"})
    sk, sid = enroll(reg, ok, oid)
    sess = boot(reg, sk, sid)
    assert sess["ok"] and sess["owner_id"] == oid
    assert reg.fetch_secrets(sess["session_token"]) == {"NVIDIA_API_KEY": "nv-secret-123456"}


# ── unauthorized identity ──

def test_unenrolled_key_with_copied_metadata_is_refused(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "put_secret", {"name": "K", "value": "v" * 20})
    real_sk, real_sid = enroll(reg, ok, oid)
    whose = collect_whose_data({"email": "a@example.com"})
    boot(reg, real_sk, real_sid, whose)
    # A stranger knows the protocol and copies the real machine's Whose Data exactly.
    stranger = generate_private_key()
    with pytest.raises(AuthError):
        boot(reg, stranger, system_id_for(public_key_b64(stranger)), whose)


def test_impersonating_enrolled_system_id_without_its_key_fails(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    _, sid = enroll(reg, ok, oid)
    attacker = generate_private_key()
    with pytest.raises(AuthError) as e:
        boot(reg, attacker, sid)
    assert "signature" in e.value.reason
    assert str(e.value) == "not authorized"            # outside sees no reason


def test_tampered_whose_data_after_signing_fails(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    sk, sid = enroll(reg, ok, oid)
    ch = reg.issue_challenge(sid)
    sig = sign(sk, DOMAIN_RESPONSE, Registry.response_payload(reg.registry_id, ch, sid, {"hostname": "a"}))
    with pytest.raises(AuthError):
        reg.respond(ch["challenge_id"], sid, {"hostname": "b"}, sig)


# ── replay / expiry ──

def test_replayed_response_is_refused(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    sk, sid = enroll(reg, ok, oid)
    ch = reg.issue_challenge(sid)
    wd = {"hostname": "box"}
    sig = sign(sk, DOMAIN_RESPONSE, Registry.response_payload(reg.registry_id, ch, sid, wd))
    assert reg.respond(ch["challenge_id"], sid, wd, sig)["ok"]
    with pytest.raises(AuthError) as e:
        reg.respond(ch["challenge_id"], sid, wd, sig)
    assert "replay" in e.value.reason


def test_failed_attempt_burns_the_challenge(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    sk, sid = enroll(reg, ok, oid)
    ch = reg.issue_challenge(sid)
    with pytest.raises(AuthError):
        reg.respond(ch["challenge_id"], sid, {}, core.b64e(b"\0" * 64))
    good = sign(sk, DOMAIN_RESPONSE, Registry.response_payload(reg.registry_id, ch, sid, {}))
    with pytest.raises(AuthError):
        reg.respond(ch["challenge_id"], sid, {}, good)


def test_expired_challenge_is_refused(env):
    reg, _, clock, _ = env
    ok, oid = make_owner(reg)
    sk, sid = enroll(reg, ok, oid)
    ch = reg.issue_challenge(sid)
    sig = sign(sk, DOMAIN_RESPONSE, Registry.response_payload(reg.registry_id, ch, sid, {}))
    clock.t += core.CHALLENGE_TTL + 1
    with pytest.raises(AuthError) as e:
        reg.respond(ch["challenge_id"], sid, {}, sig)
    assert "expired" in e.value.reason


def test_challenge_for_one_system_cannot_be_used_by_another(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    _, sid_a = enroll(reg, ok, oid)
    sk_b, sid_b = enroll(reg, ok, oid)
    ch = reg.issue_challenge(sid_a)
    sig = sign(sk_b, DOMAIN_RESPONSE, Registry.response_payload(reg.registry_id, ch, sid_b, {}))
    with pytest.raises(AuthError):
        reg.respond(ch["challenge_id"], sid_b, {}, sig)


def test_session_expires(env):
    reg, _, clock, _ = env
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "put_secret", {"name": "K", "value": "x"})
    sk, sid = enroll(reg, ok, oid)
    tok = boot(reg, sk, sid)["session_token"]
    clock.t += core.SESSION_TTL + 1
    with pytest.raises(AuthError):
        reg.fetch_secrets(tok)


def test_signature_for_another_registry_is_refused(env, tmp_path):
    reg, *_ = env
    other = Registry.create(tmp_path / "other.db", os.urandom(32), now=reg._now)
    ok, oid = make_owner(reg)
    sk, sid = enroll(reg, ok, oid)
    ch = reg.issue_challenge(sid)
    sig = sign(sk, DOMAIN_RESPONSE, Registry.response_payload(other.registry_id, ch, sid, {}))
    with pytest.raises(AuthError):
        reg.respond(ch["challenge_id"], sid, {}, sig)


# ── admin authorization ──

def test_admin_replay_stale_and_wrong_key_refused(env):
    reg, _, clock, _ = env
    ok, oid = make_owner(reg)
    p = Registry.admin_payload(reg.registry_id, oid, "list_secrets", {}, reg.now(), core.b64e(os.urandom(18)))
    env_ = {"payload": p, "signature": sign(ok, DOMAIN_ADMIN, p)}
    assert reg.admin(env_)["ok"]
    with pytest.raises(AuthError):                       # replay
        reg.admin(env_)
    with pytest.raises(AuthError):                       # stale timestamp
        admin(reg, ok, oid, "list_secrets", {}, ts=reg.now() - core.ADMIN_SKEW - 5)
    with pytest.raises(AuthError):                       # someone else's key
        admin(reg, generate_private_key(), oid, "list_secrets", {})


def test_boot_signature_cannot_be_reused_as_admin(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    p = Registry.admin_payload(reg.registry_id, oid, "list_secrets", {}, reg.now(), core.b64e(os.urandom(18)))
    wrong_domain = sign(ok, DOMAIN_RESPONSE, p)
    with pytest.raises(AuthError):
        reg.admin({"payload": p, "signature": wrong_domain})


def test_system_key_cannot_do_owner_admin(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    sk, sid = enroll(reg, ok, oid)
    with pytest.raises(AuthError):
        admin(reg, sk, oid, "put_secret", {"name": "X", "value": "y"})


# ── cross-owner isolation ──

def test_cross_owner_access_is_impossible(env):
    reg, *_ = env
    ka, a = make_owner(reg, "a@example.com")
    kb, b = make_owner(reg, "b@example.com")
    admin(reg, ka, a, "put_secret", {"name": "GITHUB_TOKEN", "value": "ghp_ownerA_only_value"})
    admin(reg, kb, b, "put_secret", {"name": "GITHUB_TOKEN", "value": "ghp_ownerB_only_value"})
    ska, sida = enroll(reg, ka, a)
    skb, sidb = enroll(reg, kb, b)
    assert reg.fetch_secrets(boot(reg, skb, sidb)["session_token"]) == {"GITHUB_TOKEN": "ghp_ownerB_only_value"}
    assert reg.fetch_secrets(boot(reg, ska, sida)["session_token"]) == {"GITHUB_TOKEN": "ghp_ownerA_only_value"}
    with pytest.raises(NotFound):                        # B cannot revoke A's system
        admin(reg, kb, b, "revoke_system", {"system_id": sida})
    with pytest.raises(Conflict):                        # B cannot adopt A's system key
        admin(reg, kb, b, "enroll_system", {"public_key": public_key_b64(ska), "scope": ["*"]})
    with pytest.raises(AuthError):                       # B cannot sign as A
        admin(reg, kb, a, "put_secret", {"name": "GITHUB_TOKEN", "value": "evil"})
    names_b = [s["name"] for s in admin(reg, kb, b, "list_secrets", {})["secrets"]]
    assert names_b == ["GITHUB_TOKEN"]
    assert reg.fetch_secrets(boot(reg, ska, sida)["session_token"])["GITHUB_TOKEN"] == "ghp_ownerA_only_value"


def test_ciphertext_moved_between_owners_does_not_decrypt(env):
    reg, root, clock, tmp = env
    ka, a = make_owner(reg, "a@example.com")
    kb, b = make_owner(reg, "b@example.com")
    admin(reg, ka, a, "put_secret", {"name": "K", "value": "A-secret-value"})
    admin(reg, kb, b, "put_secret", {"name": "K", "value": "B-secret-value"})
    db = sqlite3.connect(tmp / "registry.db")
    nonce, ct = db.execute("SELECT nonce, ciphertext FROM secrets WHERE owner_id=?", (a,)).fetchone()
    db.execute("UPDATE secrets SET nonce=?, ciphertext=?, version=1 WHERE owner_id=?", (nonce, ct, b))
    db.commit(); db.close()
    skb, sidb = enroll(reg, kb, b)
    with pytest.raises(VaultLocked):
        reg.fetch_secrets(boot(reg, skb, sidb)["session_token"])


def test_scope_limits_which_keys_a_system_gets(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "put_secret", {"name": "A", "value": "1"})
    admin(reg, ok, oid, "put_secret", {"name": "B", "value": "2"})
    sk, sid = enroll(reg, ok, oid, scope=["A"])
    assert reg.fetch_secrets(boot(reg, sk, sid)["session_token"]) == {"A": "1"}


# ── revocation ──

def test_revocation_blocks_new_handshakes_and_kills_live_sessions(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "put_secret", {"name": "K", "value": "v"})
    sk, sid = enroll(reg, ok, oid)
    tok = boot(reg, sk, sid)["session_token"]
    admin(reg, ok, oid, "revoke_system", {"system_id": sid})
    with pytest.raises(AuthError):
        reg.fetch_secrets(tok)
    with pytest.raises(AuthError):
        boot(reg, sk, sid)
    with pytest.raises(Conflict):                        # cannot quietly re-enroll a revoked key
        admin(reg, ok, oid, "enroll_system", {"public_key": public_key_b64(sk), "scope": ["*"]})


def test_disabled_owner_loses_access(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "put_secret", {"name": "K", "value": "v"})
    sk, sid = enroll(reg, ok, oid)
    tok = boot(reg, sk, sid)["session_token"]
    reg.set_owner_status(oid, False)
    with pytest.raises(AuthError):
        reg.fetch_secrets(tok)
    with pytest.raises(AuthError):
        boot(reg, sk, sid)


# ── persistence and fail-closed vault ──

def test_restart_persistence_and_fail_closed_root_key(env):
    reg, root, clock, tmp = env
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "put_secret", {"name": "K", "value": "persist-me-please"})
    sk, sid = enroll(reg, ok, oid)
    reg.close()

    reg2 = Registry(tmp / "registry.db", root, now=clock)          # "restart"
    assert reg2.fetch_secrets(boot(reg2, sk, sid)["session_token"]) == {"K": "persist-me-please"}
    reg2.close()

    with pytest.raises(VaultLocked):                                # wrong root key
        Registry(tmp / "registry.db", os.urandom(32), now=clock)

    reg3 = Registry(tmp / "registry.db", None, now=clock)           # no root key at all
    tok = boot(reg3, sk, sid)["session_token"]                      # identity still verifiable
    with pytest.raises(VaultLocked):
        reg3.fetch_secrets(tok)
    with pytest.raises(VaultLocked):
        admin(reg3, ok, oid, "put_secret", {"name": "X", "value": "y"})


def test_no_plaintext_secret_in_db_or_audit(env):
    reg, _, _, tmp = env
    ok, oid = make_owner(reg)
    value = "sk-PLAINTEXT-CANARY-9f8e7d6c"
    admin(reg, ok, oid, "put_secret", {"name": "CANARY", "value": value})
    sk, sid = enroll(reg, ok, oid)
    tok = boot(reg, sk, sid)["session_token"]
    reg.fetch_secrets(tok)
    reg._db.execute("PRAGMA wal_checkpoint(FULL)")
    for f in tmp.iterdir():
        assert value.encode() not in f.read_bytes(), f
        assert tok.encode() not in f.read_bytes(), f              # only token hashes stored
    events = admin(reg, ok, oid, "audit", {"limit": 500})["events"]
    assert value not in json.dumps(events)
    assert any(e["event"] == "secrets.fetch" and e["detail"]["names"] == ["CANARY"] for e in events)
    assert reg.verify_audit_chain()


def test_audit_chain_detects_tampering(env):
    reg, _, _, tmp = env
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "list_secrets", {})
    assert reg.verify_audit_chain()
    reg._db.execute("UPDATE audit SET outcome='ok' WHERE id=1")
    reg._db.execute("UPDATE audit SET detail='{}' WHERE id=2")
    assert not reg.verify_audit_chain()


def test_denials_are_audited_with_reason(env):
    reg, *_ = env
    ok, oid = make_owner(reg)
    _, sid = enroll(reg, ok, oid)
    with pytest.raises(AuthError):
        boot(reg, generate_private_key(), sid)
    rows = reg._db.execute("SELECT detail FROM audit WHERE event='whodat.respond' AND outcome='denied'").fetchall()
    assert rows and "signature" in json.loads(rows[-1][0])["reason"]


# ── HTTP API ──

@pytest.fixture
def api(env, monkeypatch):
    from fastapi.testclient import TestClient
    from whodat import api as wapi
    reg = env[0]
    wapi.set_registry(reg)
    wapi._hits.clear()
    yield TestClient(wapi.create_app()), reg, wapi
    wapi.set_registry(None)


def test_http_full_flow_with_delta_pipe_and_magnet_header(api):
    client, reg, _ = api
    ok, oid = make_owner(reg)
    admin(reg, ok, oid, "put_secret", {"name": "K", "value": "http-value"})
    sk, sid = enroll(reg, ok, oid)
    r = client.post("/whodat/challenge", content=f"∆|subject_id={sid}|purpose=boot".encode(),
                    headers={"X-Lumenis-Auth": "🧲".encode()})
    assert r.status_code == 200 and r.json()["question"] == "Who Dat?"
    ch = r.json()
    sig = sign(sk, DOMAIN_RESPONSE, Registry.response_payload(ch["registry_id"], ch, sid, {"hostname": "h"}))
    r = client.post("/whodat/respond", json={"challenge_id": ch["challenge_id"], "system_id": sid,
                                              "whose_data": {"hostname": "h"}, "signature": sig})
    assert r.status_code == 200
    tok = r.json()["session_token"]
    r = client.get("/whodat/secrets", headers={"Authorization": f"Bearer {tok}"})
    assert r.json()["secrets"] == {"K": "http-value"} and r.headers["cache-control"] == "no-store"
    assert client.get("/whodat/secrets").status_code == 401
    assert client.get("/whodat/secrets", headers={"Authorization": "Bearer wdt_forged"}).status_code == 401


def test_http_magnet_header_alone_grants_nothing(api):
    client, reg, _ = api
    ok, oid = make_owner(reg)
    _, sid = enroll(reg, ok, oid)
    ch = client.post("/whodat/challenge", json={"subject_id": sid}).json()
    r = client.post("/whodat/respond", headers={"X-Lumenis-Auth": "🧲".encode()},
                    json={"challenge_id": ch["challenge_id"], "system_id": sid,
                          "whose_data": {"claim": "I am Lumenis"}, "signature": "∆|trust-me"})
    assert r.status_code in (400, 401) and "session_token" not in r.text


def test_http_open_registration_off_by_default_and_requires_proof(api, monkeypatch):
    client, reg, wapi = api
    k = generate_private_key()
    oid = core.owner_id_for(public_key_b64(k))
    assert client.post("/whodat/challenge", json={"subject_id": oid, "purpose": "register_owner"}).status_code == 403
    assert client.post("/whodat/owners", json={}).status_code == 403
    monkeypatch.setenv("WHODAT_OPEN_REGISTRATION", "1")
    ch = client.post("/whodat/challenge", json={"subject_id": oid, "purpose": "register_owner"}).json()
    bad = client.post("/whodat/owners", json={"email": "n@example.com", "public_key": public_key_b64(k),
                                              "challenge_id": ch["challenge_id"], "signature": core.b64e(b"\0" * 64)})
    assert bad.status_code == 401
    from whodat import core as c
    ch = client.post("/whodat/challenge", json={"subject_id": oid, "purpose": "register_owner"}).json()
    payload = Registry.register_payload(ch["registry_id"], ch, oid, "n@example.com", public_key_b64(k))
    good = client.post("/whodat/owners", json={"email": "n@example.com", "public_key": public_key_b64(k),
                                               "challenge_id": ch["challenge_id"],
                                               "signature": sign(k, c.DOMAIN_REGISTER, payload)})
    assert good.status_code == 200 and good.json()["owner_id"] == oid


def test_http_rate_limit(api, monkeypatch):
    client, reg, wapi = api
    monkeypatch.setattr(wapi, "RATE_PER_MIN", 3)
    sid = "sys_" + "a" * 26
    codes = [client.post("/whodat/challenge", json={"subject_id": sid}).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]


# ── CLI: key generator, boot-env, dist-check ──

def run_cli(args, home, extra_env=None, stdin=None):
    e = {**os.environ, "WHODAT_HOME": str(home / "wd"), "WHODAT_ROOT_KEY_FILE": str(home / "root.key"),
         "PYTHONPATH": str(ROOT)}
    e.pop("WHODAT_ROOT_KEY", None); e.pop("WHODAT_REGISTRY_URL", None)
    e.update(extra_env or {})
    return subprocess.run([sys.executable, "-m", "whodat", *args], capture_output=True, text=True,
                          env=e, input=stdin, cwd=str(ROOT), timeout=60)


def test_cli_init_generates_own_keys_and_boot_env_is_safe(tmp_path):
    r = run_cli(["init", "--email", "new.user@example.com"], tmp_path)
    assert r.returncode == 0, r.stderr
    for f in ("wd/identity/system.key", "wd/identity/owner.key", "root.key", "wd/registry.db"):
        assert (tmp_path / f).stat().st_mode & 0o077 == 0, f
    assert run_cli(["init", "--email", "x@example.com"], tmp_path).returncode == 1   # never overwrites
    tricky = "a'b\"c $(touch /tmp/whodat_pwned) `id` ; rm -rf ~"
    r = run_cli(["secret", "put", "TRICKY_KEY"], tmp_path, stdin=tricky)
    assert r.returncode == 0, r.stderr
    r = run_cli(["boot-env"], tmp_path)
    assert r.returncode == 0, r.stderr
    shell = subprocess.run(["bash", "-c", r.stdout + '\nprintf "%s" "$TRICKY_KEY"'], capture_output=True, text=True)
    assert shell.stdout == tricky and not Path("/tmp/whodat_pwned").exists()
    assert "WHODAT_LOADED_COUNT=1" in r.stdout


def test_cli_two_installs_have_independent_keys(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert run_cli(["init", "--email", "a@example.com"], a).returncode == 0
    assert run_cli(["init", "--email", "b@example.com"], b).returncode == 0
    ma = json.loads((a / "wd/identity/identity.json").read_text())
    mb = json.loads((b / "wd/identity/identity.json").read_text())
    assert ma["system_id"] != mb["system_id"] and ma["registry_id"] != mb["registry_id"]
    assert (a / "root.key").read_bytes() != (b / "root.key").read_bytes()
    run_cli(["secret", "put", "K"], a, stdin="only-in-a")
    out_b = run_cli(["boot-env"], b).stdout
    assert "only-in-a" not in out_b and "WHODAT_LOADED_COUNT=0" in out_b


def test_cli_boot_env_fails_closed(tmp_path):
    assert run_cli(["init", "--email", "a@example.com"], tmp_path).returncode == 0
    run_cli(["secret", "put", "K"], tmp_path, stdin="value-123")
    (tmp_path / "root.key").rename(tmp_path / "root.key.away")      # root key gone
    r = run_cli(["boot-env"], tmp_path)
    assert r.returncode == 1 and r.stdout == "" and "no keys loaded" in r.stderr
    (tmp_path / "root.key.away").rename(tmp_path / "root.key")
    m = json.loads((tmp_path / "wd/identity/identity.json").read_text())
    assert run_cli(["revoke", m["system_id"]], tmp_path).returncode == 0
    r = run_cli(["boot-env"], tmp_path)
    assert r.returncode == 1 and r.stdout == ""


def test_cli_import_env_and_only_unset(tmp_path):
    assert run_cli(["init", "--email", "a@example.com"], tmp_path).returncode == 0
    envf = tmp_path / "mine.env"
    envf.write_text("# mine\nexport NVIDIA_API_KEY='nv-abc-123'\nGITHUB_TOKEN=\"ghp_x\"\nEMPTY=\n")
    r = run_cli(["secret", "import", str(envf)], tmp_path)
    assert "imported 2" in r.stdout, r.stderr
    r = run_cli(["boot-env", "--only-unset"], tmp_path, extra_env={"GITHUB_TOKEN": "from-dotenv"})
    assert "NVIDIA_API_KEY=nv-abc-123" in r.stdout and "GITHUB_TOKEN" not in r.stdout


def test_dist_check_finds_planted_secrets_and_keys(tmp_path):
    from whodat.cli import dist_check
    envf = tmp_path / "owner.env"
    envf.write_text("NVIDIA_API_KEY=nvapi-REAL-OWNER-VALUE-0001\nPORT=8000\nX=your_key_here_please\n")
    clean = tmp_path / "clean"; clean.mkdir()
    (clean / "app.py").write_text("KEY = os.getenv('NVIDIA_API_KEY')\n")
    assert dist_check(clean, [envf]) == []
    dirty = tmp_path / "dirty"; dirty.mkdir()
    (dirty / "cfg.js").write_text("const k='nvapi-REAL-OWNER-VALUE-0001'")
    k = generate_private_key()
    core.save_private_key(dirty / "id" / "stray.pem", k)
    hits = dist_check(dirty, [envf])
    assert {h["finding"] for h in hits} == {"contains the value of NVIDIA_API_KEY", "private key block"}
    assert all("nvapi-REAL" not in json.dumps(h) for h in hits)    # report names, never values
    tgz = tmp_path / "rel.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        tf.add(dirty, arcname="rel")
    assert len(dist_check(tgz, [envf])) == 2
