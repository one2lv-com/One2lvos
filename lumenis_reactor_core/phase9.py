"""
Phase 9, built into the reactor (item 25).

Ported to Python from minmax/iso-build/one2lv-phase9/opt/one2lv (modules/delta_engine.js,
modules/system_dynamics.js, ai/council/*.js). It runs inside the reactor: no node servers, nothing on
ports 8080/8081 (those clash with Minimax and Sovereign Core).

What the code really does (read from the JS, not the banner):
  ³   3D vector: built from angles (theta, phi) and a magnitude, stored as x, y, z.
  ++  amplify:   value x factor (default 1.2), capped at 1.0. In the JS it only returns the number.
  --  attenuate: value x factor (default 0.8), no floor. Same: returns a number only.
  ∆   propagate: each layer moves toward a target with momentum 0.9 and a 1% step:
                 velocity = 0.9 x velocity + (target - current) x weight x 0.01; value = current + velocity.
                 It is a momentum smoother, not a neural network. With no layers the value does not move.
  ∆⁹  cap:       at most 9 layers; a 10th drops the oldest.
  In the JS, backpropagate() is never called and gradientHistory is never written; applyPhysics works out
  gravity on z and then throws it away. Those are not ported as features (gravity is noted, not faked).

Reactor changes, with guardrails:
  - state persists in data/phase9/state.json (atomic write; reset backs up first)
  - amplify/attenuate can be applied to the vector (apply=true); factors are bounded:
    amplify 1.0-2.0, attenuate 0.1-1.0; target -10..10; weight 0.1..5; all values must be finite
  - every operation is logged to the history (last 200) that the live council view reads
  - the Phase 9 council is NOT run as a second council. Its parts map onto Lumenis's seats (ROLE_MAP).
  - Phase 9 memory (nodes/beliefs/goals/patterns/links, vector/vectors.json) imports as fuzzy facts,
    source phase9_import, tag PHASE9, never stable, never over an existing fact, never into dreams.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get("PHASE9_STATE") or ROOT / "data" / "phase9" / "state.json")
PAYLOAD = ROOT / "minmax" / "iso-build" / "one2lv-phase9" / "opt" / "one2lv"
DELTA_LAYERS = 9
LEARNING_RATE, MOMENTUM = 0.01, 0.9
HISTORY_MAX = 200
BOUNDS = {"amplify": (1.0, 2.0), "attenuate": (0.1, 1.0), "target": (-10.0, 10.0), "weight": (0.1, 5.0),
          "magnitude": (0.0, 100.0), "scale": (0.0, 10.0)}
_lock = threading.RLock()

# Phase 9 council part -> the Lumenis seat that already does that job. One council, not two.
ROLE_MAP = [
    {"phase9": "planner x3 (LLM plan proposals, canned fallback)", "seat": "navigator",
     "how": "Navigator already plans each turn and picks intent and seats."},
    {"phase9": "evaluatePlanSafety / evaluatePlan (blocked patterns, length)", "seat": "sentinel",
     "how": "Sentinel screens every turn; tool risk tiers L0-L3 gate actions."},
    {"phase9": "negotiate (exact-text majority vote)", "seat": "weaver",
     "how": "Weaver merges the seats' views into one answer."},
    {"phase9": "executePlan through the sandbox", "seat": "forge",
     "how": "Forge runs work, through the tool engine's tiers and approvals instead of a free-text shell."},
    {"phase9": "score (word match: error/ok)", "seat": "arbiter",
     "how": "The Arbiter checks answers against live status; a stronger check than word matching."},
    {"phase9": "memory nodes, formBeliefs, generateGoals", "seat": "witness",
     "how": "Witness recalls memory; beliefs/goals arrive as fuzzy facts; goals map to objectives."},
    {"phase9": "mesh broadcast (discovery.js, rpc.js)", "seat": "hermes",
     "how": "Not built: there is no second node. Hermes stays the outside-world seat."},
]


# ── 3D vectors (system_dynamics.js) ────────────────────────────────────────────────────────
def vector3d(theta: float, phi: float, force: float = 1.0) -> Dict[str, float]:
    return {"x": round(force * math.cos(theta) * math.sin(phi), 6),
            "y": round(force * math.sin(theta) * math.sin(phi), 6),
            "z": round(force * math.cos(phi), 6), "magnitude": force, "theta": theta, "phi": phi}


def vec_from_xyz(x: float, y: float, z: float) -> Dict[str, float]:
    r = math.sqrt(x * x + y * y + z * z)
    return vector3d(math.atan2(y, x), math.atan2(math.sqrt(x * x + y * y), z), r)


def vec_add(a, b):
    return vec_from_xyz(a["x"] + b["x"], a["y"] + b["y"], a["z"] + b["z"])


def vec_sub(a, b):
    return vec_from_xyz(a["x"] - b["x"], a["y"] - b["y"], a["z"] - b["z"])


def vec_scale(v, k):
    return vector3d(v["theta"], v["phi"], v["magnitude"] * k)


def vec_dot(a, b):
    return a["x"] * b["x"] + a["y"] * b["y"] + a["z"] * b["z"]


def vec_cross(a, b):
    return vec_from_xyz(a["y"] * b["z"] - a["z"] * b["y"], a["z"] * b["x"] - a["x"] * b["z"],
                        a["x"] * b["y"] - a["y"] * b["x"])


# ── Delta engine (delta_engine.js) ─────────────────────────────────────────────────────────
def amplify(value: float, factor: float = 1.2) -> float:
    return min(1.0, value * factor)


def attenuate(value: float, factor: float = 0.8) -> float:
    return value * factor


def _new_state() -> Dict[str, Any]:
    return {"vector": vector3d(0.0, math.pi / 4, 1.0), "layers": [], "history": [],
            "learning_rate": LEARNING_RATE, "momentum": MOMENTUM, "created": time.time(), "ops": 0}


def load() -> Dict[str, Any]:
    with _lock:
        try:
            return json.loads(STATE.read_text())
        except FileNotFoundError:
            return _new_state()
        except json.JSONDecodeError:
            STATE.replace(STATE.with_suffix(".corrupt.json"))
            return _new_state()


def _save(st: Dict[str, Any]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1))
    os.replace(tmp, STATE)


def _num(name: str, v: Any, bound: str) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(f):
        raise ValueError(f"{name} must be finite")
    lo, hi = BOUNDS[bound]
    if not lo <= f <= hi:
        raise ValueError(f"{name} must be between {lo} and {hi} (got {f})")
    return f


def _log(st, op: str, **kw):
    st["ops"] = st.get("ops", 0) + 1
    st["history"].append({"ts": time.time(), "op": op, **kw})
    st["history"] = st["history"][-HISTORY_MAX:]


def propagate_state(st: Dict[str, Any], target: float) -> Dict[str, Any]:
    current = st["vector"]["magnitude"]
    deltas = []
    for i, layer in enumerate(st["layers"]):
        error = target - current
        gradient = error * layer["weight"]
        deltas.append({"layer": layer["name"], "delta": gradient, "index": i})
        layer["velocity"] = st["momentum"] * layer["velocity"] + gradient * st["learning_rate"]
        layer["value"] = current + layer["velocity"]
        current = layer["value"]
    return {"output": current, "deltas": deltas, "error": target - current, "layers": len(st["layers"])}


# ── Tool handlers (called by the tool engine: one dict in, one dict out) ───────────────────
def t_state(a: Dict[str, Any]) -> Dict[str, Any]:
    st = load()
    return {"vector": st["vector"], "layers": st["layers"], "max_layers": DELTA_LAYERS,
            "learning_rate": st["learning_rate"], "momentum": st["momentum"], "ops": st.get("ops", 0),
            "history": st["history"][-int(a.get("limit", 10)):], "label": "real output (reactor's Phase 9 state)"}


def _amp_att(a, op):
    factor = _num("factor", a.get("factor", 1.2 if op == "amplify" else 0.8), op)
    with _lock:
        st = load()
        before = st["vector"]["magnitude"]
        after = amplify(before, factor) if op == "amplify" else attenuate(before, factor)
        applied = bool(a.get("apply"))
        if applied:
            st["vector"] = vector3d(st["vector"]["theta"], st["vector"]["phi"], after)
        _log(st, op, symbol="++" if op == "amplify" else "--", factor=factor, before=before, after=after,
             applied=applied)
        _save(st)
    out = {"symbol": "++" if op == "amplify" else "--", "original": before, "result": after, "factor": factor,
           "applied": applied}
    if op == "amplify" and before * factor > 1.0:
        out["note"] = "capped at 1.0 (the Phase 9 code caps amplify at 1.0)"
    return out


def t_amplify(a):
    return _amp_att(a, "amplify")


def t_attenuate(a):
    return _amp_att(a, "attenuate")


def t_add_layer(a):
    name = str(a.get("name") or "").strip()[:40]
    if not name:
        raise ValueError("name required")
    weight = _num("weight", a.get("weight", 1.0), "weight")
    with _lock:
        st = load()
        dropped = None
        if len(st["layers"]) >= DELTA_LAYERS:
            dropped = st["layers"].pop(0)["name"]
        st["layers"].append({"name": name, "weight": weight, "value": 0.0, "velocity": 0.0, "added": time.time()})
        _log(st, "add_layer", symbol="∆⁹", name=name, weight=weight, dropped=dropped)
        _save(st)
        return {"symbol": "∆⁹", "index": len(st["layers"]) - 1, "total_layers": len(st["layers"]),
                "max_layers": DELTA_LAYERS, "dropped_oldest": dropped}


def t_propagate(a):
    target = _num("target", a.get("target"), "target")
    with _lock:
        st = load()
        r = propagate_state(st, target)
        _log(st, "propagate", symbol="∆", target=target, output=r["output"], error=r["error"], layers=r["layers"])
        _save(st)
    r["symbol"] = "∆"
    if not r["layers"]:
        r["note"] = "no layers yet: add one with delta_add_layer, or the value does not move"
    return r


def t_set_vector(a):
    theta = float(a.get("theta", 0.0))
    phi = float(a.get("phi", math.pi / 4))
    if not (math.isfinite(theta) and math.isfinite(phi)):
        raise ValueError("theta and phi must be finite")
    mag = _num("magnitude", a.get("magnitude", 1.0), "magnitude")
    with _lock:
        st = load()
        st["vector"] = vector3d(theta, phi, mag)
        _log(st, "set_vector", symbol="³", magnitude=mag, x=st["vector"]["x"], y=st["vector"]["y"], z=st["vector"]["z"])
        _save(st)
        return {"symbol": "³", "vector": st["vector"]}


def t_reset(a):
    """Clears layers and history and resets the vector. Backs up the old state first."""
    with _lock:
        backup = None
        if STATE.exists():
            backup = STATE.with_name(f"state.before_reset.{time.strftime('%Y%m%d-%H%M%S')}.json")
            shutil.copy2(STATE, backup)
        st = _new_state()
        _log(st, "reset", backup=str(backup.name) if backup else None)
        _save(st)
    return {"reset": True, "backup": str(backup) if backup else None}


# ── Phase 9 memory import ─────────────────────────────────────────────────────────────────
SECTIONS = ("nodes", "beliefs", "goals", "patterns", "links")


def _item_id(section: str, i: int, item: Any) -> str:
    if isinstance(item, dict):
        for k in ("id", "name", "belief", "goal", "pattern"):
            if item.get(k):
                return str(item[k])[:80]
    return f"{i}"


def import_memory(compass, memory_path: str | None = None, vectors_path: str | None = None,
                  dry_run: bool = True) -> Dict[str, Any]:
    """Merge Phase 9 memory into the reactor as fuzzy facts (source phase9_import, tag PHASE9).
    Never overwrites: a key that already exists is skipped. Never touches dream rows or stable facts."""
    mp = Path(memory_path) if memory_path else None
    vp = Path(vectors_path) if vectors_path else None
    out = {"dry_run": dry_run, "added": 0, "skipped_existing": 0, "by_section": {}, "files": [], "errors": []}
    rows: List[tuple] = []
    if mp:
        if not mp.is_file():
            out["errors"].append(f"no memory file at {mp}")
        else:
            out["files"].append(str(mp))
            try:
                mem = json.loads(mp.read_text())
            except Exception as e:
                mem = {}
                out["errors"].append(f"memory file unreadable: {type(e).__name__}")
            for sec in SECTIONS:
                items = mem.get(sec) or []
                for i, it in enumerate(items if isinstance(items, list) else []):
                    rows.append((sec, f"phase9.{sec[:-1]}.{_item_id(sec, i, it)}", json.dumps(it)[:4000]))
    if vp:
        if not vp.is_file():
            out["errors"].append(f"no vectors file at {vp}")
        else:
            out["files"].append(str(vp))
            try:
                vec = json.loads(vp.read_text())
            except Exception as e:
                vec = []
                out["errors"].append(f"vectors file unreadable: {type(e).__name__}")
            items = vec if isinstance(vec, list) else (vec.get("vectors") or [] if isinstance(vec, dict) else [])
            for i, it in enumerate(items):
                rows.append(("vectors", f"phase9.vector.{_item_id('vectors', i, it)}", json.dumps(it)[:4000]))
    with compass._connect() as conn:
        existing = {r[0] for r in conn.execute("SELECT key FROM facts WHERE key LIKE 'phase9.%'")}
    for sec, key, value in rows:
        if key in existing:
            out["skipped_existing"] += 1
            continue
        existing.add(key)
        out["by_section"][sec] = out["by_section"].get(sec, 0) + 1
        out["added"] += 1
        if not dry_run:
            compass.store_fact(key, value, source="phase9_import", verification="unverified", scope="fuzzy",
                               tag="PHASE9", confidence=0.4)
    return out


def find_memory_files() -> Dict[str, str | None]:
    """Where Phase 9 writes its memory at run time. The payload in the repo ships none."""
    cands = [Path(os.environ.get("PHASE9_MEMORY_FILE", "/opt/one2lv/memory/memory.json")), PAYLOAD / "memory" / "memory.json"]
    vcands = [Path(os.environ.get("PHASE9_VECTOR_FILE", "/opt/one2lv/vector/vectors.json")), PAYLOAD / "vector" / "vectors.json"]
    return {"memory": next((str(p) for p in cands if p.is_file()), None),
            "vectors": next((str(p) for p in vcands if p.is_file()), None)}


def imported_counts(compass) -> Dict[str, int]:
    with compass._connect() as conn:
        return {r[0]: r[1] for r in conn.execute(
            "SELECT substr(key, 8, instr(substr(key, 8), '.') - 1), count(*) FROM facts "
            "WHERE source='phase9_import' GROUP BY 1")}


# ── /phase9 ───────────────────────────────────────────────────────────────────────────────
TOOLS_HELP = ("local.delta_state (L0), local.delta_amplify / delta_attenuate / delta_add_layer / delta_propagate / "
              "delta_set_vector (L1), local.delta_reset (L2: held for approval when Lumenis asks)")


async def command(args: list, owner: bool, compass=None) -> str:
    sub = (args[0].lower() if args else "status")
    if sub == "status":
        st = load()
        v = st["vector"]
        layers = ", ".join(f"{l['name']}={l['value']:.3f}" for l in st["layers"]) or "none"
        last = st["history"][-1] if st["history"] else None
        files = find_memory_files()
        lines = ["Phase 9 (built into the reactor; no servers on 8080/8081):",
                 f"- ³ vector: x {v['x']}, y {v['y']}, z {v['z']}, magnitude {v['magnitude']:.3f}",
                 f"- ∆⁹ layers: {len(st['layers'])} of {DELTA_LAYERS} ({layers})",
                 f"- Operations so far: {st.get('ops', 0)}" + (f"; last: {last['op']}" if last else ""),
                 f"- Tools: {TOOLS_HELP}",
                 "- Council: mapped onto Lumenis's seats (/phase9 roles), not run as a second council",
                 "- Mesh: not built (no second node)"]
        if compass is not None:
            c = imported_counts(compass)
            lines.append(f"- Imported Phase 9 memory: {sum(c.values())} fuzzy facts {c or ''}".rstrip())
        lines.append(f"- Phase 9 memory file on this machine: {files['memory'] or 'none'}; vectors: {files['vectors'] or 'none'}")
        return "\n".join(lines)
    if sub == "roles":
        return "Phase 9 council parts and the Lumenis seat that does each job:\n" + "\n".join(
            f"- {r['phase9']} -> {r['seat']}: {r['how']}" for r in ROLE_MAP)
    if not owner:
        return "Changing Phase 9 state is owner-only. /phase9 and /phase9 roles are open."
    try:
        if sub in ("++", "amplify"):
            r = t_amplify({"factor": float(args[1]) if len(args) > 1 else 1.2, "apply": True})
            return f"++ {r['original']:.3f} -> {r['result']:.3f} (x{r['factor']})" + (f" {r['note']}" if r.get("note") else "")
        if sub in ("--", "attenuate"):
            r = t_attenuate({"factor": float(args[1]) if len(args) > 1 else 0.8, "apply": True})
            return f"-- {r['original']:.3f} -> {r['result']:.3f} (x{r['factor']})"
        if sub == "layer" and len(args) > 1:
            r = t_add_layer({"name": args[1], "weight": float(args[2]) if len(args) > 2 else 1.0})
            return f"∆⁹ layer {args[1]} added: {r['total_layers']} of {DELTA_LAYERS}" + (
                f" (dropped oldest: {r['dropped_oldest']})" if r["dropped_oldest"] else "")
        if sub in ("∆", "propagate", "delta") and len(args) > 1:
            r = t_propagate({"target": float(args[1])})
            return f"∆ toward {args[1]}: output {r['output']:.4f}, error {r['error']:.4f}, {r['layers']} layers" + (
                f" ({r['note']})" if r.get("note") else "")
        if sub == "import" and compass is not None:
            files = find_memory_files()
            if not (files["memory"] or files["vectors"]):
                return ("No Phase 9 memory on this machine to import. Phase 9 writes memory.json and vectors.json "
                        "only when its council runs; the payload in the repo ships none.")
            go = len(args) > 1 and args[1] == "confirm"
            r = import_memory(compass, files["memory"], files["vectors"], dry_run=not go)
            return (f"{'Imported' if go else 'Would import'} {r['added']} fuzzy facts {r['by_section']}, "
                    f"skipped {r['skipped_existing']} already present." + ("" if go else " Type /phase9 import confirm to do it."))
    except ValueError as e:
        return f"Refused: {e}"
    return ("Usage: /phase9 [status|roles] | /phase9 ++ [factor] | /phase9 -- [factor] | /phase9 layer <name> [weight] "
            "| /phase9 ∆ <target> | /phase9 import [confirm]")


def live_view() -> Dict[str, Any]:
    """Small summary for the live council view."""
    st = load()
    return {"magnitude": st["vector"]["magnitude"], "layers": [{"name": l["name"], "value": round(l["value"], 4)}
                                                              for l in st["layers"]],
            "max_layers": DELTA_LAYERS, "recent": st["history"][-8:], "ops": st.get("ops", 0)}
