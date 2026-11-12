"""
Lumenis Tool Engine
===================
Pulls the sfcompute Autoresearch MCP tool catalog (name, description, input schema,
annotations) onto Lumenis' own disk, runs the tools that can really run on this machine
locally, wraps the read-only ones that only SF Compute can answer, and refuses the rest.

Tool names
  engine.status | engine.learn | engine.describe | engine.list | engine.validate |
  engine.catalog_versions | engine.rollback_catalog          engine housekeeping
  local.<name>       runs on this machine, never calls the server
  sfcompute.<name>   SF Compute's tool: read-only ones go through the bridge (validated,
                     cached, rate limited); paid / changing ones are refused unless One2lv
                     names them in SFCOMPUTE_MCP_ALLOW_TOOLS
  nimlab.<name>      One2lv's NVIDIA lab suite (vendor/nimlab_suite) via nimlab_tools.py:
                     local reads of its stores; single NVIDIA calls and bounded ranking
                     (nvidia.com only, rate limited, key from env); sweeps, discovery,
                     image generation, voice cloning and role changes refused.
                     Off switch: NIMLAB_TOOLS=0

Permission levels: local_read, local_write, remote_read are open; remote_write is refused
(spends money or changes paid machines). No shell: there is no local run_command.
Kill switch: ONE2LVOS_TOOL_ENGINE=0 (lumenis-main.py then does not mount the engine).

Routes (reactor, port 8000)
  GET  /engine/status
  GET  /engine/tools?kind=&q=          catalog with kinds and local equivalents
  GET  /engine/tools/{name}            one tool's architecture (from disk)
  POST /engine/learn                   pull the catalog from the server (keeps the old one)
  POST /engine/validate/{name}         check arguments against the stored schema
  POST /engine/call/{name}             run a tool; JSON or ∆|key=value body; ?fresh=true
  GET  /engine/artifacts/{id}/download
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import sqlite3
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from . import sfcompute_mcp as _sfc
from . import nimlab_tools as _nim

ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = Path(os.getenv("TOOL_ENGINE_DIR", str(ROOT / "data" / "tool_engine")))
CATALOG_DIR = ENGINE_DIR / "catalog"
CATALOG_FILE = CATALOG_DIR / "sfcompute.json"
ARTIFACT_DIR = ENGINE_DIR / "artifacts"
DB_FILE = ENGINE_DIR / "engine.db"

CACHE_TTL = int(os.getenv("TOOL_ENGINE_CACHE_TTL", "60"))
RATE_PER_MIN = int(os.getenv("TOOL_ENGINE_REMOTE_PER_MIN", "20"))
KEEP_CATALOG_VERSIONS = 20
MAX_EXPORT_BYTES = 50 * 1024 * 1024

# export_file may copy only from these folders, and never a file that could hold a secret
EXPORT_ROOTS = [ROOT / "logs", ROOT / "data" / "dreams", ROOT / "data" / "conversations", ROOT / "data" / "inbox",
                Path(os.path.realpath(os.environ.get("WEBDAV_ROOT", str(ROOT / "webdav_root"))))]
SECRET_NAME_RE = re.compile(r"(\.env|token|secret|passw|\.pem|\.key$|id_rsa|id_ed25519|credential|vault)", re.I)
REDACT_RE = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}|nvapi-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|"
    r"AstraCS:[A-Za-z0-9:]{10,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+|"
    r"(?i:(?:password|passwd|secret|token|api[_-]?key|authorization)[\"']?\s*[=:]\s*)[^\s,\"']+)")
SENSITIVE_ARG_RE = re.compile(r"(secret|token|password|passwd|api_?key|authorization)", re.I)

router = APIRouter(tags=["tool-engine"])
_lock = threading.Lock()
_remote_calls: deque = deque()
_fact_sink: Optional[Callable[[str, str], None]] = None


def set_fact_sink(fn: Callable[[str, str], None]) -> None:
    """lumenis-main.py passes a function that stores a fact in Compass memory."""
    global _fact_sink
    _fact_sink = fn


def _remember(key: str, value: str) -> None:
    if _fact_sink:
        try:
            _fact_sink(key, value)
        except Exception:
            pass


# ── Storage ───────────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (id TEXT PRIMARY KEY, title TEXT, goal TEXT, tags TEXT, status TEXT,
  result TEXT, verdict TEXT, created_at REAL, finished_at REAL);
CREATE TABLE IF NOT EXISTS updates (id INTEGER PRIMARY KEY AUTOINCREMENT, mission_id TEXT, kind TEXT, text TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS charts (mission_id TEXT, name TEXT, unit TEXT, points TEXT, saved_at REAL,
  PRIMARY KEY (mission_id, name));
CREATE TABLE IF NOT EXISTS artifacts (id TEXT PRIMARY KEY, mission_id TEXT, source_path TEXT, stored_name TEXT,
  size INTEGER, sha256 TEXT, note TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS traces (id TEXT PRIMARY KEY, tool TEXT, kind TEXT, level TEXT, source TEXT, ok INTEGER,
  status INTEGER, args TEXT, error TEXT, duration_ms INTEGER, caller TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, tool TEXT, result TEXT, saved_at REAL);
CREATE TABLE IF NOT EXISTS metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, sample TEXT, created_at REAL);
"""


def _db() -> sqlite3.Connection:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _rows(sql: str, args: tuple = ()) -> List[Dict[str, Any]]:
    with _lock, _db() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def _exec(sql: str, args: tuple = ()) -> int:
    with _lock, _db() as c:
        cur = c.execute(sql, args)
        return cur.rowcount


# ── Catalog (the learned architecture of every tool) ─────────────────────────────────────

_catalog_cache: Dict[str, Any] = {}


def load_catalog() -> Dict[str, Any]:
    if _catalog_cache.get("mtime") == (CATALOG_FILE.stat().st_mtime if CATALOG_FILE.exists() else None):
        return _catalog_cache.get("data") or {}
    data = json.loads(CATALOG_FILE.read_text()) if CATALOG_FILE.exists() else {}
    _catalog_cache.update(mtime=CATALOG_FILE.stat().st_mtime if CATALOG_FILE.exists() else None, data=data)
    return data


def _tool_map() -> Dict[str, Dict[str, Any]]:
    return {t["name"]: t for t in load_catalog().get("tools", [])}


def _catalog_hash(tools: list) -> str:
    return hashlib.sha256(json.dumps(sorted(tools, key=lambda t: t["name"]), sort_keys=True).encode()).hexdigest()


def catalog_versions() -> List[Dict[str, Any]]:
    out = []
    for f in sorted(CATALOG_DIR.glob("sfcompute.v*.json"), reverse=True):
        try:
            d = json.loads(f.read_text())
            out.append({"version_file": f.name, "learned_at": d.get("learned_at"), "count": d.get("count"),
                        "sha256": d.get("sha256")})
        except Exception:
            pass
    return out


async def learn() -> Dict[str, Any]:
    """Pull tools/list from the server and store it. The previous catalog is kept as a version."""
    _rate_check()
    async with _sfc._client() as c:
        mcp, info = await _sfc._session(c)
        tools = await mcp.list_tools()
    old = load_catalog()
    old_map = {t["name"]: t for t in old.get("tools", [])}
    new_map = {t["name"]: t for t in tools}
    digest = _catalog_hash(tools)
    data = {"server": _sfc.MCP_URL, "server_info": info.get("serverInfo"), "protocol": info.get("protocolVersion"),
            "learned_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "count": len(tools), "sha256": digest, "tools": tools}
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    if old and old.get("sha256") == digest:
        changed = False
    else:
        changed = True
        stamp = time.strftime("%Y%m%d_%H%M%S")
        (CATALOG_DIR / f"sfcompute.v{stamp}.json").write_text(json.dumps(data))
        tmp = CATALOG_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(CATALOG_FILE)
        for f in sorted(CATALOG_DIR.glob("sfcompute.v*.json"))[:-KEEP_CATALOG_VERSIONS]:
            f.unlink()
    kinds = summarize_kinds()
    diff = {"added": sorted(set(new_map) - set(old_map)), "removed": sorted(set(old_map) - set(new_map)),
            "changed": sorted(n for n in set(new_map) & set(old_map)
                              if json.dumps(new_map[n], sort_keys=True) != json.dumps(old_map[n], sort_keys=True))}
    _remember("tool_engine.catalog",
              f"Learned {len(tools)} sfcompute tool schemas at {data['learned_at']} (sha {digest[:12]}): "
              f"{kinds['remote_read']} read-only open, {kinds['remote_write']} refused, "
              f"{len(LOCAL_TOOLS)} local tools run on this machine.")
    return {"learned": len(tools), "changed": changed, "sha256": digest, "learned_at": data["learned_at"],
            "diff": diff if old else {"first_pull": True}, "kinds": kinds}


def rollback_catalog(version_file: Optional[str] = None) -> Dict[str, Any]:
    """Put an earlier pulled catalog back (default: the one before the current)."""
    versions = catalog_versions()
    cur = load_catalog().get("sha256")
    if version_file:
        pick = next((v for v in versions if v["version_file"] == version_file), None)
    else:
        pick = next((v for v in versions if v["sha256"] != cur), None)
    if not pick:
        raise ValueError("no earlier catalog version to roll back to")
    src = CATALOG_DIR / pick["version_file"]
    tmp = CATALOG_FILE.with_suffix(".tmp")
    shutil.copyfile(src, tmp)
    tmp.replace(CATALOG_FILE)
    return {"rolled_back_to": pick}


# ── Classification ────────────────────────────────────────────────────────────────────

WHY_REMOTE = [
    ("SF Compute account, billing or team data: only SF Compute holds it",
     ("billing", "usage", "credit", "limit", "referral", "org", "member", "team", "sso", "role", "invite",
      "retention", "domain_join", "auto_topup", "alerts", "workspace", "ticket", "secret", "connection")),
    ("evaluation / rollout ledger kept on SF Compute's platform",
     ("rollout", "evaluation", "verdict", "task", "sample", "qualify")),
    ("needs SF Compute hardware (H100 / CPU nodes, sandboxes, clusters, networks)",
     ("node", "cluster", "job", "sandbox", "command", "network", "snapshot", "port", "endpoint", "gpu", "scrape",
      "http_request", "file", "context", "import", "export", "storage")),
    ("state of SF Compute's own platform (its logs, metrics, traces, missions, shares)",
     ("log", "metric", "trace", "audit", "update", "mission", "chart", "artifact", "share")),
]


def why_remote(name: str) -> str:
    for reason, words in WHY_REMOTE:
        if any(w in name for w in words):
            return reason
    return "implemented on SF Compute's server"


def remote_level(name: str, tool: Optional[dict] = None) -> str:
    return "remote_read" if _sfc.tool_allowed(name, (tool or {}).get("annotations")) else "remote_write"


# ── Small JSON-Schema checker (the subset the catalog uses) ─────────────────────────────

_TYPES = {"string": str, "boolean": bool, "object": dict, "array": list, "null": type(None)}


def _type_ok(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    py = _TYPES.get(t)
    return True if py is None else isinstance(v, py)


def validate(schema: Dict[str, Any], value: Any, root: Optional[Dict[str, Any]] = None, path: str = "$") -> List[str]:
    root = root or schema
    errs: List[str] = []
    if not isinstance(schema, dict):
        return errs
    if "$ref" in schema:
        ref = schema["$ref"]
        node: Any = root
        for part in ref.lstrip("#/").split("/"):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        return validate(node, value, root, path)
    for key in ("anyOf", "oneOf"):
        if key in schema:
            if not any(not validate(s, value, root, path) for s in schema[key]):
                errs.append(f"{path}: does not match any allowed form")
            return errs
    if "allOf" in schema:
        for s in schema["allOf"]:
            errs += validate(s, value, root, path)
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, x) for x in types):
            return [f"{path}: expected {'/'.join(types)}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: must be one of {schema['enum']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: above maximum {schema['maximum']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}.{req}: required")
        for k, v in value.items():
            if k in props:
                errs += validate(props[k], v, root, f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}.{k}: not a parameter of this tool")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs += validate(schema["additionalProperties"], v, root, f"{path}.{k}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']} characters")
        if "pattern" in schema:
            try:
                if not re.search(schema["pattern"], value):
                    errs.append(f"{path}: does not match the allowed pattern")
            except re.error:
                pass
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path}: at most {schema['maxItems']} items")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, v in enumerate(value):
            errs += validate(schema["items"], v, root, f"{path}[{i}]")
    return errs


# ── Rate limiter (server calls only) ────────────────────────────────────────────────────

class RateLimited(Exception):
    def __init__(self, wait: float):
        super().__init__(f"rate limit: {RATE_PER_MIN} server calls a minute; retry in {wait:.0f}s")
        self.wait = wait


def _rate_check() -> None:
    now = time.time()
    with _lock:
        while _remote_calls and now - _remote_calls[0] > 60:
            _remote_calls.popleft()
        if len(_remote_calls) >= RATE_PER_MIN:
            raise RateLimited(60 - (now - _remote_calls[0]))
        _remote_calls.append(now)


# ── Local tools (run on this machine; never call the server) ──────────────────────────

def _now() -> float:
    return time.time()


def _iso(ts: Optional[float]) -> Optional[str]:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts)) if ts else None


def _mission(mid: str) -> Dict[str, Any]:
    rows = _rows("SELECT * FROM missions WHERE id=?", (mid,))
    if not rows:
        raise KeyError(f"no mission {mid!r}")
    m = rows[0]
    m["tags"] = json.loads(m["tags"] or "[]")
    m["result"] = json.loads(m["result"]) if m["result"] else None
    m["created"], m["finished"] = _iso(m["created_at"]), _iso(m["finished_at"])
    return m


def l_open_mission(a):
    mid = "m_" + uuid.uuid4().hex[:10]
    _exec("INSERT INTO missions (id,title,goal,tags,status,created_at) VALUES (?,?,?,?,?,?)",
          (mid, a["title"], a.get("goal", ""), json.dumps(a.get("tags", [])), "open", _now()))
    return {"mission_id": mid, "status": "open", "title": a["title"]}


def l_post_update(a):
    m = _mission(a["mission_id"])
    if m["status"] != "open":
        raise ValueError(f"mission {m['id']} is {m['status']}; updates go to open missions")
    _exec("INSERT INTO updates (mission_id,kind,text,created_at) VALUES (?,?,?,?)",
          (m["id"], a.get("kind", "note"), a["text"], _now()))
    n = _rows("SELECT COUNT(*) n FROM updates WHERE mission_id=?", (m["id"],))[0]["n"]
    return {"mission_id": m["id"], "posted": True, "updates": n}


def l_list_updates(a):
    lim = int(a.get("limit", 50))
    if a.get("mission_id"):
        rows = _rows("SELECT * FROM updates WHERE mission_id=? ORDER BY id DESC LIMIT ?", (a["mission_id"], lim))
    else:
        rows = _rows("SELECT * FROM updates ORDER BY id DESC LIMIT ?", (lim,))
    for r in rows:
        r["created"] = _iso(r.pop("created_at"))
    return {"updates": rows, "count": len(rows)}


def l_get_mission(a):
    m = _mission(a["mission_id"])
    m["updates"] = l_list_updates({"mission_id": m["id"], "limit": 200})["updates"]
    m["charts"] = [{"name": c["name"], "unit": c["unit"], "points": json.loads(c["points"])}
                   for c in _rows("SELECT * FROM charts WHERE mission_id=?", (m["id"],))]
    m["artifacts"] = [r["id"] for r in _rows("SELECT id FROM artifacts WHERE mission_id=?", (m["id"],))]
    return m


def l_list_missions(a):
    lim = int(a.get("limit", 50))
    if a.get("status"):
        rows = _rows("SELECT id,title,status,created_at,finished_at FROM missions WHERE status=? ORDER BY created_at DESC LIMIT ?",
                     (a["status"], lim))
    else:
        rows = _rows("SELECT id,title,status,created_at,finished_at FROM missions ORDER BY created_at DESC LIMIT ?", (lim,))
    for r in rows:
        r["created"], r["finished"] = _iso(r.pop("created_at")), _iso(r.pop("finished_at"))
    return {"missions": rows, "count": len(rows)}


def l_finish_mission(a):
    m = _mission(a["mission_id"])
    if m["status"] == "finished":
        raise ValueError(f"mission {m['id']} is already finished")
    _exec("UPDATE missions SET status='finished', result=?, verdict=?, finished_at=? WHERE id=?",
          (json.dumps(a["result"]), a.get("verdict", ""), _now(), m["id"]))
    return {"mission_id": m["id"], "status": "finished"}


def l_save_chart(a):
    _mission(a["mission_id"])
    _exec("INSERT OR REPLACE INTO charts (mission_id,name,unit,points,saved_at) VALUES (?,?,?,?,?)",
          (a["mission_id"], a["name"], a.get("unit", ""), json.dumps(a["points"]), _now()))
    return {"mission_id": a["mission_id"], "chart": a["name"], "points": len(a["points"])}


def l_delete_chart(a):
    n = _exec("DELETE FROM charts WHERE mission_id=? AND name=?", (a["mission_id"], a["name"]))
    if not n:
        raise KeyError(f"no chart {a['name']!r} on mission {a['mission_id']!r}")
    return {"deleted": a["name"]}


def _export_source(path: str) -> Path:
    p = Path(path)
    p = (ROOT / p) if not p.is_absolute() else p
    real = Path(os.path.realpath(p))
    if not any(str(real).startswith(str(Path(os.path.realpath(r))) + os.sep) for r in EXPORT_ROOTS):
        raise PermissionError("export_file copies only from logs/, data/dreams, data/conversations, data/inbox "
                              "or the WebDAV share")
    if SECRET_NAME_RE.search(real.name):
        raise PermissionError(f"{real.name} could hold a secret; refused")
    if not real.is_file():
        raise FileNotFoundError(f"no file at {path}")
    if real.stat().st_size > MAX_EXPORT_BYTES:
        raise ValueError(f"file is over {MAX_EXPORT_BYTES // (1024 * 1024)} MB")
    return real


def l_export_file(a):
    src = _export_source(a["path"])
    if a.get("mission_id"):
        _mission(a["mission_id"])
    aid = "a_" + uuid.uuid4().hex[:10]
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{aid}_{src.name}"
    shutil.copyfile(src, ARTIFACT_DIR / stored)
    raw = (ARTIFACT_DIR / stored).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    _exec("INSERT INTO artifacts (id,mission_id,source_path,stored_name,size,sha256,note,created_at) VALUES (?,?,?,?,?,?,?,?)",
          (aid, a.get("mission_id"), str(src), stored, len(raw), sha, a.get("note", ""), _now()))
    return {"artifact_id": aid, "size": len(raw), "sha256": sha, "download": f"/engine/artifacts/{aid}/download"}


def l_list_artifacts(a):
    lim = int(a.get("limit", 50))
    if a.get("mission_id"):
        rows = _rows("SELECT * FROM artifacts WHERE mission_id=? ORDER BY created_at DESC LIMIT ?", (a["mission_id"], lim))
    else:
        rows = _rows("SELECT * FROM artifacts ORDER BY created_at DESC LIMIT ?", (lim,))
    for r in rows:
        r["created"] = _iso(r.pop("created_at"))
        r["download"] = f"/engine/artifacts/{r['id']}/download"
    return {"artifacts": rows, "count": len(rows)}


def l_get_artifact(a):
    rows = _rows("SELECT * FROM artifacts WHERE id=?", (a["artifact_id"],))
    if not rows:
        raise KeyError(f"no artifact {a['artifact_id']!r}")
    r = rows[0]
    r["created"] = _iso(r.pop("created_at"))
    r["download"] = f"/engine/artifacts/{r['id']}/download"
    r["present"] = (ARTIFACT_DIR / r["stored_name"]).exists()
    return r


def store_artifact(src: Path, note: str = "", mission_id: Optional[str] = None) -> Dict[str, Any]:
    """Copy a file a tool produced (e.g. a nimlab.tts WAV) into the artifact store."""
    aid = "a_" + uuid.uuid4().hex[:10]
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{aid}_{src.name}"
    shutil.copyfile(src, ARTIFACT_DIR / stored)
    raw = (ARTIFACT_DIR / stored).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    _exec("INSERT INTO artifacts (id,mission_id,source_path,stored_name,size,sha256,note,created_at) VALUES (?,?,?,?,?,?,?,?)",
          (aid, mission_id, str(src), stored, len(raw), sha, note[:500], _now()))
    return {"artifact_id": aid, "size": len(raw), "download": f"/engine/artifacts/{aid}/download"}


_nim.set_artifact_sink(store_artifact)


def redact(text: str) -> str:
    return REDACT_RE.sub("[redacted]", text)


def l_query_logs(a):
    logs = ROOT / "logs"
    files = sorted(f.name for f in logs.glob("*.log")) if logs.exists() else []
    if not a.get("file"):
        return {"files": files, "hint": "pass file (one of these) and optionally contains, limit"}
    name = Path(a["file"]).name
    if name not in files:
        raise FileNotFoundError(f"no log {name!r}; logs are {files}")
    lim = min(int(a.get("limit", 100)), 500)
    needle = (a.get("contains") or "").lower()
    out: deque = deque(maxlen=lim)
    with open(logs / name, "r", errors="replace") as fh:
        for line in fh:
            if not needle or needle in line.lower():
                out.append(redact(line.rstrip("\n"))[:1000])
    return {"file": name, "lines": list(out), "count": len(out)}


SERVICE_PORTS = {8000: "reactor", 8081: "ai_lobby", 8090: "public_bridge", 8765: "webdav"}


def l_query_metrics(a):
    if a.get("history"):
        lim = min(int(a.get("limit", 50)), 500)
        rows = _rows("SELECT sample, created_at FROM metrics ORDER BY id DESC LIMIT ?", (lim,))
        return {"samples": [dict(json.loads(r["sample"]), at=_iso(r["created_at"])) for r in rows]}
    import psutil
    vm, du = psutil.virtual_memory(), psutil.disk_usage(str(ROOT))
    listening = set()
    try:
        for cn in psutil.net_connections(kind="inet"):
            if cn.status == psutil.CONN_LISTEN and cn.laddr:
                listening.add(cn.laddr.port)
    except Exception:
        pass
    sample = {"cpu_percent": psutil.cpu_percent(interval=0.3), "load_avg": list(os.getloadavg()),
              "mem_used_percent": vm.percent, "mem_available_mb": vm.available // (1024 * 1024),
              "disk_used_percent": du.percent, "disk_free_gb": round(du.free / 1e9, 2),
              "services": {name: (port in listening) for port, name in SERVICE_PORTS.items()},
              "engine_calls_last_hour": _rows("SELECT COUNT(*) n FROM traces WHERE created_at>?", (_now() - 3600,))[0]["n"]}
    _exec("INSERT INTO metrics (sample, created_at) VALUES (?,?)", (json.dumps(sample), _now()))
    _exec("DELETE FROM metrics WHERE id NOT IN (SELECT id FROM metrics ORDER BY id DESC LIMIT 5000)")
    return sample


def _trace_row(r):
    r["args"] = json.loads(r["args"] or "{}")
    r["ok"] = bool(r["ok"])
    r["created"] = _iso(r.pop("created_at"))
    return r


def l_search_traces(a):
    q, args = "SELECT * FROM traces WHERE 1=1", []
    if a.get("tool"):
        q += " AND tool LIKE ?"; args.append(f"%{a['tool']}%")
    if a.get("ok") is not None:
        q += " AND ok=?"; args.append(1 if a["ok"] else 0)
    if a.get("since_minutes"):
        q += " AND created_at>?"; args.append(_now() - 60 * float(a["since_minutes"]))
    q += " ORDER BY created_at DESC LIMIT ?"; args.append(min(int(a.get("limit", 50)), 500))
    rows = [_trace_row(r) for r in _rows(q, tuple(args))]
    return {"traces": rows, "count": len(rows)}


def l_get_trace(a):
    rows = _rows("SELECT * FROM traces WHERE id=?", (a["trace_id"],))
    if not rows:
        raise KeyError(f"no trace {a['trace_id']!r}")
    return _trace_row(rows[0])


def l_list_audit_events(a):
    """Writes, pulls, rollbacks and refusals: the calls that changed something or were stopped."""
    rows = _rows("SELECT * FROM traces WHERE level IN ('local_write','remote_write','engine_write') OR ok=0 "
                 "ORDER BY created_at DESC LIMIT ?", (min(int(a.get("limit", 50)), 500),))
    return {"events": [_trace_row(r) for r in rows], "count": len(rows)}


def _obj(props: dict, required: list = ()) -> dict:
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


_S, _I, _B = {"type": "string"}, {"type": "integer", "minimum": 1}, {"type": "boolean"}

# name: (handler, level, input schema, description, the sfcompute tool it mirrors)
LOCAL_TOOLS: Dict[str, tuple] = {
    "open_mission": (l_open_mission, "local_write", _obj({"title": _S, "goal": _S, "tags": {"type": "array", "items": _S}}, ["title"]),
                     "Open a mission in the local ledger."),
    "post_update": (l_post_update, "local_write", _obj({"mission_id": _S, "text": _S,
                                                       "kind": {"type": "string", "enum": ["note", "result", "blocker"]}},
                                                      ["mission_id", "text"]), "Post an update to an open mission."),
    "list_updates": (l_list_updates, "local_read", _obj({"mission_id": _S, "limit": _I}), "Updates, newest first."),
    "get_mission": (l_get_mission, "local_read", _obj({"mission_id": _S}, ["mission_id"]),
                    "A mission with its updates, charts and artifacts."),
    "list_missions": (l_list_missions, "local_read", _obj({"status": {"type": "string", "enum": ["open", "finished"]},
                                                          "limit": _I}), "Missions, newest first."),
    "finish_mission": (l_finish_mission, "local_write", _obj({"mission_id": _S, "result": {},
                                                             "verdict": _S}, ["mission_id", "result"]),
                       "Finish a mission with its result."),
    "save_chart": (l_save_chart, "local_write", _obj({"mission_id": _S, "name": _S, "unit": _S,
                                                     "points": {"type": "array", "items": {"type": "array"}}},
                                                    ["mission_id", "name", "points"]),
                   "Save (or replace) a chart of [x, y] points on a mission."),
    "delete_chart": (l_delete_chart, "local_write", _obj({"mission_id": _S, "name": _S}, ["mission_id", "name"]),
                     "Delete a chart from a mission."),
    "export_file": (l_export_file, "local_write", _obj({"path": _S, "mission_id": _S, "note": _S}, ["path"]),
                    "Copy a file from logs/, data/dreams, data/conversations, data/inbox or the WebDAV share "
                    "into the artifact store."),
    "list_artifacts": (l_list_artifacts, "local_read", _obj({"mission_id": _S, "limit": _I}), "Artifacts, newest first."),
    "get_artifact": (l_get_artifact, "local_read", _obj({"artifact_id": _S}, ["artifact_id"]), "One artifact's record."),
    "query_logs": (l_query_logs, "local_read", _obj({"file": _S, "contains": _S, "limit": _I}),
                   "Read this machine's reactor logs (keys scrubbed)."),
    "query_metrics": (l_query_metrics, "local_read", _obj({"history": _B, "limit": _I}),
                      "CPU, memory, disk, services up on this machine; history=true for past samples."),
    "search_traces": (l_search_traces, "local_read", _obj({"tool": _S, "ok": _B, "since_minutes": {"type": "number"},
                                                          "limit": _I}), "Search the engine's call log."),
    "get_trace": (l_get_trace, "local_read", _obj({"trace_id": _S}, ["trace_id"]), "One engine call by trace id."),
    "list_audit_events": (l_list_audit_events, "local_read", _obj({"limit": _I}),
                          "Engine calls that changed something or were refused."),
}


# ── Dispatcher ─────────────────────────────────────────────────────────────────────────────

def summarize_kinds() -> Dict[str, int]:
    tm = _tool_map()
    read = sum(1 for n, t in tm.items() if remote_level(n, t) == "remote_read")
    return {"catalog": len(tm), "remote_read": read, "remote_write": len(tm) - read, "local": len(LOCAL_TOOLS),
            "local_mirrors_of_server_tools": sum(1 for n in LOCAL_TOOLS if n in tm)}


def status() -> Dict[str, Any]:
    cat = load_catalog()
    with _lock:
        recent = len([t for t in _remote_calls if time.time() - t <= 60])
    return {"engine": "lumenis-tool-engine/1", "catalog_learned": bool(cat), "learned_at": cat.get("learned_at"),
            "catalog_sha256": cat.get("sha256"), "server": cat.get("server") or _sfc.MCP_URL,
            "kinds": summarize_kinds(), "catalog_versions": len(catalog_versions()),
            "rate_limit": {"server_calls_per_min": RATE_PER_MIN, "used_last_min": recent},
            "cache_ttl_s": CACHE_TTL, "allow_list": sorted(_sfc._allow_list()),
            "permissions": {"local_read": "open", "local_write": "open", "remote_read": "open",
                            "remote_write": "refused unless named in SFCOMPUTE_MCP_ALLOW_TOOLS",
                            "nimlab": "local_read open; nvidia_call/nvidia_batch rate limited, nvidia.com only; "
                                      "sweeps, discovery, image generation, voice cloning, role changes refused"},
            "shell": "none (no local run_command)",
            "nimlab": _nim.summary()}


def list_tools(kind: Optional[str] = None, q: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = []
    for name, (_, level, _, desc) in LOCAL_TOOLS.items():
        rows.append({"name": f"local.{name}", "kind": "local", "level": level, "description": desc,
                     "mirrors": f"sfcompute.{name}" if name in _tool_map() else None})
    rows += _nim.list_rows()
    for name, t in sorted(_tool_map().items()):
        lvl = remote_level(name, t)
        rows.append({"name": f"sfcompute.{name}", "kind": "remote_read" if lvl == "remote_read" else "refused",
                     "level": lvl, "description": (t.get("description") or "")[:240],
                     "local_equivalent": f"local.{name}" if name in LOCAL_TOOLS else None,
                     "why_remote": why_remote(name)})
    if kind:
        rows = [r for r in rows if r["kind"] == kind or r["level"] == kind]
    if q:
        rows = [r for r in rows if q.lower() in (r["name"] + " " + r["description"]).lower()]
    return rows


def describe(name: str) -> Dict[str, Any]:
    ns, _, bare = name.rpartition(".")
    ns = ns or "sfcompute"
    if ns == "local":
        if bare not in LOCAL_TOOLS:
            raise KeyError(f"no local tool {bare!r}")
        _, level, schema, desc = LOCAL_TOOLS[bare]
        return {"name": f"local.{bare}", "kind": "local", "level": level, "description": desc, "inputSchema": schema,
                "runs": "on this machine; never calls the server"}
    if ns == "nimlab":
        return _nim.describe(bare)
    t = _tool_map().get(bare)
    if not t:
        raise KeyError(f"no tool {bare!r} in the learned catalog" + ("" if load_catalog() else " (catalog not pulled yet: engine.learn)"))
    lvl = remote_level(bare, t)
    return {"name": f"sfcompute.{bare}", "kind": "remote_read" if lvl == "remote_read" else "refused", "level": lvl,
            "description": t.get("description"), "inputSchema": t.get("inputSchema"), "annotations": t.get("annotations"),
            "local_equivalent": f"local.{bare}" if bare in LOCAL_TOOLS else None, "why_remote": why_remote(bare),
            "runs": "on SF Compute's server through the bridge" if lvl == "remote_read"
                    else "refused: spends money or changes paid machines unless One2lv names it in SFCOMPUTE_MCP_ALLOW_TOOLS"}


def _safe_args(args: Dict[str, Any]) -> str:
    return redact(json.dumps({k: ("[redacted]" if SENSITIVE_ARG_RE.search(k) else v) for k, v in args.items()},
                             default=str))[:2000]


def _trace(tool, kind, level, source, ok, status_code, args, error, t0, caller) -> str:
    tid = "t_" + uuid.uuid4().hex[:12]
    try:
        _exec("INSERT INTO traces (id,tool,kind,level,source,ok,status,args,error,duration_ms,caller,created_at) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (tid, tool, kind, level, source, 1 if ok else 0, status_code, _safe_args(args), (error or "")[:1000],
               int((time.time() - t0) * 1000), caller, time.time()))
        _exec("DELETE FROM traces WHERE id NOT IN (SELECT id FROM traces ORDER BY created_at DESC LIMIT 20000)")
    except Exception:
        pass
    return tid


async def dispatch(name: str, args: Optional[Dict[str, Any]] = None, fresh: bool = False,
                   caller: str = "api") -> Dict[str, Any]:
    """Run one tool. Always answers {ok, tool, kind, level, source, status, result|error, trace_id}."""
    args = dict(args or {})
    args.pop("tool", None)
    t0 = time.time()
    ns, _, bare = name.strip().rpartition(".")
    ns = ns or "sfcompute"
    kind, level, source, code = "engine", "engine_read", "local", 200
    try:
        if ns == "engine":
            if bare == "status":
                result = status()
            elif bare == "learn":
                level, source = "engine_write", "remote"
                result = await learn()
            elif bare == "describe":
                result = describe(str(args.get("name") or args.get("tool_name") or args.get("of") or ""))
            elif bare == "list":
                rows = list_tools(args.get("kind"), args.get("q"))
                result = {"tools": rows, "count": len(rows)}
            elif bare == "validate":
                target = describe(str(args.get("name") or ""))
                errs = validate(target["inputSchema"] or {}, args.get("arguments") or {})
                result = {"tool": target["name"], "valid": not errs, "errors": errs}
            elif bare == "catalog_versions":
                result = {"current": load_catalog().get("sha256"), "versions": catalog_versions()}
            elif bare == "rollback_catalog":
                level = "engine_write"
                result = rollback_catalog(args.get("version_file"))
            else:
                raise KeyError(f"no engine tool {bare!r}")
        elif ns == "local":
            kind = "local"
            if bare not in LOCAL_TOOLS:
                raise KeyError(f"no local tool {bare!r}")
            fn, level, schema, _ = LOCAL_TOOLS[bare]
            errs = validate(schema, args)
            if errs:
                code = 422
                raise ValueError("invalid arguments: " + "; ".join(errs))
            result = await asyncio.to_thread(fn, args)
        elif ns == "nimlab":
            kind = "nimlab"
            if bare not in _nim.TOOLS:
                code = 404
                raise KeyError(f"no nimlab tool {bare!r}")
            fn, level, schema, _ = _nim.TOOLS[bare]
            if level == "refused":
                kind = "refused"
            if not _nim.enabled():
                code = 503
                raise RuntimeError("nimlab tools are switched off (NIMLAB_TOOLS=0)")
            errs = validate(schema, args)
            if errs:
                code = 422
                raise ValueError("invalid arguments: " + "; ".join(errs))
            source = "local" if level in ("local_read", "refused") else "remote"
            try:
                result = await asyncio.wait_for(asyncio.to_thread(fn, args), timeout=_nim.TIMEOUTS[level])
            except asyncio.TimeoutError:
                code = 504
                raise RuntimeError(f"nimlab.{bare} took longer than {_nim.TIMEOUTS[level]}s")
        elif ns == "sfcompute":
            tool = _tool_map().get(bare)
            if not tool:
                code = 404
                raise KeyError(f"no tool {bare!r} in the learned catalog" + ("" if load_catalog() else "; run engine.learn first"))
            level = remote_level(bare, tool)
            if level != "remote_read":
                kind, source, code = "refused", "refused", 403
                raise PermissionError(f"{bare} " + ("touches stored secrets" if bare in _sfc.ALWAYS_ASK else
                                      "can start, change, delete or pay for compute") +
                                      "; refused unless One2lv names it in SFCOMPUTE_MCP_ALLOW_TOOLS" +
                                      (f" (local.{bare} runs on this machine instead)" if bare in LOCAL_TOOLS else ""))
            kind = "remote_read"
            errs = validate(tool.get("inputSchema") or {}, args)
            if errs:
                code = 422
                raise ValueError("invalid arguments (checked locally, nothing sent): " + "; ".join(errs))
            key = hashlib.sha256((bare + json.dumps(args, sort_keys=True)).encode()).hexdigest()
            cached = None if fresh else _rows("SELECT result, saved_at FROM cache WHERE key=? AND saved_at>?",
                                              (key, time.time() - CACHE_TTL))
            if cached:
                source = "cache"
                result = json.loads(cached[0]["result"])
            else:
                source = "remote"
                _rate_check()
                async with _sfc._client() as c:
                    mcp, _ = await _sfc._session(c)
                    result = await mcp.call_tool(bare, args)
                if isinstance(result, dict) and result.get("isError"):
                    code = 502
                    raise RuntimeError("server answered with an error: " +
                                       json.dumps(result.get("content"), default=str)[:800])
                _exec("INSERT OR REPLACE INTO cache (key, tool, result, saved_at) VALUES (?,?,?,?)",
                      (key, bare, json.dumps(result, default=str), time.time()))
        else:
            code = 404
            raise KeyError(f"unknown namespace {ns!r}; use engine., local., nimlab. or sfcompute.")
        tid = _trace(name, kind, level, source, True, 200, args, None, t0, caller)
        return {"ok": True, "tool": name, "kind": kind, "level": level, "source": source, "status": 200,
                "result": result, "trace_id": tid}
    except Exception as e:
        if isinstance(e, RateLimited):
            code = 429
        elif isinstance(e, _sfc.MCPError):
            code = e.status
        elif isinstance(e, _nim.NimlabError):
            code = e.status
        elif isinstance(e, PermissionError) and code == 200:
            code = 403
        elif isinstance(e, KeyError) and code == 200:
            code = 404
        elif isinstance(e, (ValueError, FileNotFoundError)) and code == 200:
            code = 400
        elif code == 200:
            code = 500
        msg = getattr(e, "detail", None) or (e.args[0] if e.args else type(e).__name__)
        msg = msg if isinstance(msg, str) else json.dumps(msg, default=str)
        tid = _trace(name, kind, level, source, False, code, args, msg, t0, caller)
        out = {"ok": False, "tool": name, "kind": kind, "level": level, "source": source, "status": code,
               "error": msg, "trace_id": tid}
        if isinstance(e, RateLimited):
            out["retry_after_s"] = round(e.wait)
        if isinstance(e, _nim.NimlabError) and e.extra.get("retry_after_s") is not None:
            out["retry_after_s"] = e.extra["retry_after_s"]
        return out


def council_summary(results: List[Dict[str, Any]]) -> str:
    """Text block for the council: real tool output, trimmed."""
    parts = []
    for r in results:
        body = json.dumps(r.get("result") if r["ok"] else {"error": r.get("error")}, indent=1, default=str)
        if len(body) > 3000:
            body = body[:3000] + "\n... (truncated)"
        parts.append(f"[Tool engine — real tool output: {r['tool']} | kind {r['kind']} | source {r['source']} | "
                     f"{'ok' if r['ok'] else 'FAILED ' + str(r['status'])} | trace {r['trace_id']}]\n{body}")
    return "\n\n".join(parts)


# ── Routes ─────────────────────────────────────────────────────────────────────────────────

def _reply(out: Dict[str, Any]) -> JSONResponse:
    return JSONResponse(out, status_code=out.get("status", 200) if not out.get("ok") else 200)


async def _body(request: Request) -> Dict[str, Any]:
    raw = (await request.body()).decode("utf-8", "replace").strip()
    if not raw:
        return {}
    if raw.startswith(("∆|", "Δ|")):
        return _sfc.parse_delta_pipe(raw)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object or a ∆|key=value string")
    return dict(data["arguments"]) if isinstance(data.get("arguments"), dict) else data


@router.get("/engine/status")
async def r_status():
    return JSONResponse(status())


@router.get("/engine/tools")
async def r_tools(kind: Optional[str] = None, q: Optional[str] = None):
    rows = list_tools(kind, q)
    return JSONResponse({"count": len(rows), "tools": rows})


@router.get("/engine/tools/{name:path}")
async def r_describe(name: str):
    return _reply(await dispatch("engine.describe", {"name": name}, caller="http"))


@router.post("/engine/learn")
async def r_learn():
    return _reply(await dispatch("engine.learn", {}, caller="http"))


@router.post("/engine/validate/{name:path}")
async def r_validate(name: str, request: Request):
    try:
        args = await _body(request)
    except Exception as e:
        return JSONResponse({"ok": False, "status": 400, "error": str(e)}, status_code=400)
    return _reply(await dispatch("engine.validate", {"name": name, "arguments": args}, caller="http"))


@router.post("/engine/call/{name:path}")
async def r_call(name: str, request: Request, fresh: bool = False):
    try:
        args = await _body(request)
    except Exception as e:
        return JSONResponse({"ok": False, "status": 400, "error": str(e)}, status_code=400)
    return _reply(await dispatch(name, args, fresh=fresh, caller="http"))


@router.get("/engine/artifacts/{aid}/download")
async def r_download(aid: str):
    rows = _rows("SELECT stored_name FROM artifacts WHERE id=?", (aid,))
    if not rows or not (ARTIFACT_DIR / rows[0]["stored_name"]).exists():
        return JSONResponse({"ok": False, "status": 404, "error": f"no artifact {aid!r}"}, status_code=404)
    name = rows[0]["stored_name"]
    return FileResponse(ARTIFACT_DIR / name, filename=name.split("_", 2)[-1])


REGISTRY_ENTRIES = [
    {"id": "engine.status", "label": "Tool Engine: Status", "method": "GET", "path": "/engine/status",
     "category": "Tool Engine", "icon": "⚙️", "params": []},
    {"id": "engine.tools", "label": "Tool Engine: List Tools", "method": "GET", "path": "/engine/tools",
     "category": "Tool Engine", "icon": "⚙️", "params": ["kind", "q"]},
    {"id": "engine.describe", "label": "Tool Engine: Tool Architecture", "method": "GET", "path": "/engine/tools/{name}",
     "category": "Tool Engine", "icon": "⚙️", "params": ["name"]},
    {"id": "engine.learn", "label": "Tool Engine: Pull Catalog", "method": "POST", "path": "/engine/learn",
     "category": "Tool Engine", "icon": "⚙️", "params": []},
    {"id": "engine.call", "label": "Tool Engine: Run Tool (JSON or ∆|)", "method": "POST", "path": "/engine/call/{name}",
     "category": "Tool Engine", "icon": "⚙️", "params": ["name", "arguments", "fresh"]},
]
