"""
IONOS webspace diagnostics bridge for the Lumenis Reactor (Hermes seat).

- run_check(check): calls the read-only PHP diagnostics API on the IONOS webspace
  (http://s1086212999.onlinehome.us/diagnostics/api.php) with the X-Diag-Token header.
  The token is IONOS_DIAG_TOKEN in /home/sprite/One2lvos/.env (git-ignored).
- sftp_check(): real SFTP key login via /home/sprite/bin/ionos_sftp.sh list, and records
  the result on the webspace (/.diag_private/last_sftp_check.json) so the dashboard's
  "SFTP Connect Test" can show the last reactor login.
- summarize(): short human-readable lines for the Weaver.
Read-only on the server except for that one status file. No secrets are returned.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
SFTP_SCRIPT = os.path.expanduser("~/bin/ionos_sftp.sh")
SSH_KEY = os.path.expanduser("~/.ssh/ionos_webspace")
DEFAULT_URL = "http://s1086212999.onlinehome.us/diagnostics/api.php"
DASHBOARD_URL = "http://s1086212999.onlinehome.us/diagnostics/"

def _sftp_target() -> str:
    # user@host for the IONOS SFTP login; kept in .env (IONOS_SFTP_TARGET), not in the repo
    return _env("IONOS_SFTP_TARGET")


CHECKS = ("ping", "env", "htaccess", "dns", "index", "http", "ssl", "sftp", "recent", "all")


def _env(name: str, default: str = "") -> str:
    v = os.environ.get(name)
    if v:
        return v
    try:
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return default


def run_check(check: str = "all", timeout: int = 60) -> dict:
    check = (check or "all").lower().strip()
    if check not in CHECKS:
        return {"ok": False, "error": f"unknown check '{check}'", "checks": list(CHECKS)}
    if check == "sftp":
        # PHP port probe + a real key login from the reactor
        login = sftp_check()
        php = _call("sftp", timeout)
        if php.get("ok"):
            php["data"]["last_reactor_login"] = login
        else:
            php = {"ok": login["ok"], "action": "sftp", "data": {"last_reactor_login": login}, "php_error": php.get("error")}
        return php
    return _call(check, timeout)


def _call(check: str, timeout: int) -> dict:
    token = _env("IONOS_DIAG_TOKEN")
    url = _env("IONOS_DIAG_URL", DEFAULT_URL)
    if not token:
        return {"ok": False, "error": "IONOS_DIAG_TOKEN is not set in .env"}
    req = urllib.request.Request(
        f"{url}?action={check}",
        headers={"X-Diag-Token": token, "User-Agent": "Lumenis-Reactor/IONOS-Diag"},
    )
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode())
        except Exception:
            data = {"ok": False}
        data.setdefault("error", f"HTTP {e.code}")
        data["http_status"] = e.code
    except Exception as e:
        data = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    data["round_trip_ms"] = int((time.time() - t) * 1000)
    return data


def sftp_check(record: bool = True) -> dict:
    """Real SFTP login with the reactor's SSH key: list /one2lvos."""
    t = time.time()
    try:
        p = subprocess.run([SFTP_SCRIPT, "list", "/one2lvos"], capture_output=True, text=True, timeout=45)
        ok = p.returncode == 0
        entries = [l for l in p.stdout.splitlines() if l.strip() and not l.startswith("total")]
        names = [l.split()[-1] for l in entries if len(l.split()) >= 9]
        names = [n for n in names if n.rstrip("/").rsplit("/", 1)[-1] not in (".", "..")]
        detail = f"listed /one2lvos: {len(names)} entries" if ok else (p.stderr.strip().splitlines() or ["login failed"])[-1][:200]
    except Exception as e:
        ok, names, detail = False, [], f"{type(e).__name__}: {e}"
    res = {
        "ok": ok,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "latency_ms": int((time.time() - t) * 1000),
        "method": "SFTP, SSH key (ed25519)",
        "detail": detail,
        "entries": names[:40],
    }
    if record:
        res["recorded"] = _record(res)
    return res


def _record(res: dict) -> bool:
    """Write the last login result to /.diag_private/last_sftp_check.json (not web-served)."""
    try:
        slim = {k: res[k] for k in ("ok", "checked_at", "latency_ms", "method", "detail")}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(slim, f)
            tmp = f.name
        p = subprocess.run(
            ["sftp", "-i", SSH_KEY, "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
             "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=20", "-b", "-", _sftp_target()],
            input=f'put "{tmp}" "/.diag_private/last_sftp_check.json"\n', capture_output=True, text=True, timeout=45,
        )
        os.unlink(tmp)
        return p.returncode == 0
    except Exception:
        return False


# ── Summaries for the council ────────────────────────────────────────────────────────────────────

def _sum_env(d):
    return [f"PHP {d['php_version']} ({d['sapi']}) on {d['server_software']}; web folder {d['web_root']} has "
            f"{d['web_files']} files, {d['web_size']}; plan storage unlimited"]


def _sum_http(d):
    out = []
    for p in d["probes"]:
        s = p["error"] or f"HTTP {p['status']}"
        out.append(f"{p['url']} -> {s} in {p['latency_ms']} ms" + (f" (redirect to {p['location']})" if p.get("location") else ""))
    return out


def _sum_ssl(d):
    out = []
    for t in d["targets"]:
        if not t["connects"]:
            out.append(f"SSL {t['host']}: NONE - {t['error']}")
        else:
            c = t.get("certificate") or {}
            out.append(f"SSL {t['host']}: cert {c.get('subject_cn')} from {c.get('issuer')}, valid to "
                       f"{(c.get('valid_to') or '')[:10]}, {'valid' if t.get('valid_for_host') else 'NOT valid'} for host")
    return out


def _sum_dns(d):
    out = [f"{h}: " + (", ".join(r["a"]) or "no A record") for h, r in d["hosts"].items()]
    out.append("NS: " + ", ".join(d["ns"]))
    out.append("MX: " + ", ".join(m["host"] for m in d["mx"]))
    return out


def _sum_index(d):
    return [f"{f['file']}: " + (f"{f['bytes']} bytes, modified {f['modified']}" if f["exists"] else "missing") for f in d["files"]]


def _sum_htaccess(d):
    return [f"{f['file']}: " + (f"{f['bytes']} bytes" if f["exists"] else "not present") for f in d["files"]]


def _sum_sftp(d):
    out = []
    p = d.get("port_22")
    if p:
        out.append(f"SSH port 22: {'reachable, ' + str(p['banner']) if p['reachable'] else 'unreachable'}")
    l = d.get("last_reactor_login")
    if l:
        out.append(f"SFTP key login from reactor: {'OK' if l['ok'] else 'FAILED'} ({l['detail']}, {l['latency_ms']} ms)")
    return out


def _sum_recent(d):
    return [f"{f['modified'][:19]} {f['file']}" for f in d["files"][:8]]


_SUM = {"env": _sum_env, "http": _sum_http, "ssl": _sum_ssl, "dns": _sum_dns, "index": _sum_index,
        "htaccess": _sum_htaccess, "sftp": _sum_sftp, "recent": _sum_recent}


def summarize(result: dict) -> str:
    if not result.get("ok") and "data" not in result:
        return f"IONOS diagnostics FAILED: {result.get('error')}"
    action, data = result.get("action", "?"), result.get("data", {})
    lines = [f"IONOS diagnostics ({action}) - live results from the server, dashboard {DASHBOARD_URL}"]
    try:
        if action == "all":
            for k in ("env", "http", "ssl", "dns", "index", "htaccess", "sftp"):
                if k in data:
                    lines += [f"- {x}" for x in _SUM[k](data[k])]
        elif action in _SUM:
            lines += [f"- {x}" for x in _SUM[action](data)]
        elif action == "ping":
            lines.append(f"- pong, server time {data.get('server_time')}, {result.get('round_trip_ms')} ms")
    except Exception as e:
        lines.append(f"- (summary error {e}); raw: {json.dumps(data)[:1500]}")
    return "\n".join(lines)


def full_diagnostic() -> dict:
    """Everything: PHP 'all' plus a real SFTP login."""
    res = _call("all", 90)
    login = sftp_check()
    if res.get("ok"):
        res["data"].setdefault("sftp", {})["last_reactor_login"] = login
    else:
        res["sftp_login"] = login
    return res
