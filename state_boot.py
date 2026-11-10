#!/usr/bin/env python3
"""
State boot: save exact copies of reactor files inside a PNG, and boot back to them.
=====================================================================================
The PNG uses the same LSB format as the reactor's /api/state/save and /api/state/load
(32-bit big-endian length, then the bytes, one bit in the low bit of each R, G, B value),
so /api/state/load can read the JSON back out of it too.

What goes in: each named file's bytes (base64) with its sha256, plus the list of named
files that did not exist yet, so a restore can take a newer file out of the way.
Keys and .env are refused: a state boot never carries secrets.

  python3 state_boot.py save  --label before-tool-engine  lumenis-main.py lumenis_reactor_core/itt.py ...
  python3 state_boot.py list
  python3 state_boot.py verify snapshots/state_boot/<file>.png
  python3 state_boot.py restore snapshots/state_boot/<file>.png [--dry-run] [--restart]

Restore first saves the current state as an automatic "pre-restore" PNG, so a restore
can itself be undone. Files the snapshot says were absent are moved to
snapshots/state_boot/quarantine/<time>/, never deleted. --restart restarts only the
reactor (port 8000), the same way startos.sh starts it.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
BOOT_DIR = ROOT / "snapshots" / "state_boot"
FORMAT = "one2lvos-state-boot/1"
REFUSE = (".env", "token", "secret", ".pem", ".key", "id_rsa", "id_ed25519")


# ── PNG LSB codec (compatible with /api/state/save + /api/state/load) ──────────

def encode_png(data: bytes) -> bytes:
    n = len(data)
    bits = np.unpackbits(np.frombuffer(n.to_bytes(4, "big") + data, dtype=np.uint8))
    pixels_need = (len(bits) + 2) // 3 + 4
    side = max(120, int(pixels_need ** 0.5) + 2)
    rng = np.random.default_rng(0x4C554D)
    base = np.array([20, 6, 40], dtype=np.int16)
    px = np.clip(base + rng.integers(-8, 9, size=(side * side, 3)), 0, 255).astype(np.uint8)
    flat = px.reshape(-1)
    flat[: len(bits)] = (flat[: len(bits)] & 0xFE) | bits
    img = Image.fromarray(flat.reshape(side, side, 3), "RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def decode_png(png: bytes) -> bytes:
    flat = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), dtype=np.uint8).reshape(-1)
    n = int.from_bytes(np.packbits(flat[:32] & 1).tobytes(), "big")
    if not (0 < n <= (len(flat) - 32) // 8):
        raise ValueError("not a state-boot PNG (bad length header)")
    return np.packbits(flat[32: 32 + n * 8] & 1).tobytes()


# ── Save / list / verify / restore ───────────────────────────────────────────

def _rel(p: str) -> str:
    path = (ROOT / p).resolve() if not os.path.isabs(p) else Path(p).resolve()
    rel = path.relative_to(ROOT)  # raises outside the repo root
    low = str(rel).lower()
    if any(r in low for r in REFUSE):
        raise ValueError(f"refused (could hold secrets): {rel}")
    return str(rel)


def _git_head() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def save(label: str, files: list[str], note: str = "") -> dict:
    rels = sorted({_rel(f) for f in files})
    state = {"format": FORMAT, "label": label, "note": note, "created_at": time.time(),
             "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "git_head": _git_head(),
             "files": {}, "absent": []}
    for rel in rels:
        p = ROOT / rel
        if not p.exists():
            state["absent"].append(rel)
            continue
        raw = p.read_bytes()
        state["files"][rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw),
                               "mode": p.stat().st_mode & 0o777, "b64": base64.b64encode(raw).decode()}
    payload = json.dumps(state, separators=(",", ":")).encode()
    png = encode_png(payload)
    BOOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in label)[:60]
    out = BOOT_DIR / f"{stamp}_{safe}.png"
    out.write_bytes(png)
    if decode_png(out.read_bytes()) != payload:  # read it back before calling it saved
        out.unlink()
        raise RuntimeError("PNG read-back did not match; nothing saved")
    manifest = {k: v for k, v in state.items() if k != "files"}
    manifest["files"] = {k: {"sha256": v["sha256"], "size": v["size"]} for k, v in state["files"].items()}
    manifest["png"] = str(out.relative_to(ROOT))
    manifest["png_sha256"] = hashlib.sha256(png).hexdigest()
    out.with_suffix(".json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load_state(png_path: str) -> dict:
    state = json.loads(decode_png(Path(png_path).read_bytes()))
    if state.get("format") != FORMAT:
        raise ValueError(f"unknown format {state.get('format')!r}")
    return state


def verify(png_path: str) -> dict:
    state = load_state(png_path)
    report = {"label": state["label"], "created": state["created"], "git_head": state["git_head"],
              "files": {}, "absent_at_save": state["absent"], "ok": True}
    for rel, f in state["files"].items():
        raw = base64.b64decode(f["b64"])
        inside = hashlib.sha256(raw).hexdigest() == f["sha256"]
        cur = ROOT / rel
        now = hashlib.sha256(cur.read_bytes()).hexdigest() if cur.exists() else None
        report["files"][rel] = {"snapshot_intact": inside, "same_as_disk_now": now == f["sha256"]}
        report["ok"] &= inside
    for rel in state["absent"]:
        report["files"][rel] = {"absent_at_save": True, "exists_now": (ROOT / rel).exists()}
    return report


def _reactor_pids() -> list:
    pids = []
    for d in Path("/proc").iterdir():
        if d.name.isdigit():
            try:
                cmd = (d / "cmdline").read_bytes().split(b"\0")
            except Exception:
                continue
            if len(cmd) > 3 and cmd[0].endswith(b"python3") and cmd[1:4] == [b"-m", b"uvicorn", b"lumenis-main:app"]:
                pids.append(int(d.name))
    return pids


def _dotenv() -> dict:
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip().removeprefix("export ").strip()] = v.strip().strip('"').strip("'")
    return env


def restart_reactor() -> str:
    """Stop the reactor on :8000 and start it again exactly as startos.sh does, with the same
    environment the running reactor had (keys come from that environment, never from the PNG)."""
    pids = _reactor_pids()
    env = None
    for pid in pids:
        try:
            raw = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
            env = dict(x.decode(errors="replace").split("=", 1) for x in raw if b"=" in x)
            break
        except Exception:
            pass
    if env is None:
        env = {**os.environ, **_dotenv()}
    for pid in pids:
        try:
            os.kill(pid, 15)
        except ProcessLookupError:
            pass
    for _ in range(20):
        if not _reactor_pids():
            break
        time.sleep(0.5)
    venv = ROOT / ".venv"
    if venv.exists():
        env["VIRTUAL_ENV"] = str(venv)
        env["PATH"] = f"{venv / 'bin'}:{env.get('PATH', '')}"
    host = env.get("ONE2LV_BIND_HOST", "127.0.0.1")
    (ROOT / "logs").mkdir(exist_ok=True)
    log = open(ROOT / "logs" / "reactor.log", "ab")
    subprocess.Popen(["python3", "-m", "uvicorn", "lumenis-main:app", "--host", host, "--port", "8000"],
                     cwd=str(ROOT), env=env, stdout=log, stderr=log, start_new_session=True)
    for _ in range(60):
        time.sleep(2)
        try:
            code = subprocess.run(["curl", "-s", "-m", "3", "-o", "/dev/null", "-w", "%{http_code}",
                                   "http://127.0.0.1:8000/"], capture_output=True, text=True).stdout
            if code == "200":
                return "reactor up (200)"
        except Exception:
            pass
    return "reactor did not answer 200 within 120s; check logs/reactor.log"


def restore(png_path: str, dry_run: bool = False, restart: bool = False) -> dict:
    state = load_state(png_path)
    plan = {"write": [], "unchanged": [], "quarantine": []}
    for rel, f in state["files"].items():
        raw = base64.b64decode(f["b64"])
        if hashlib.sha256(raw).hexdigest() != f["sha256"]:
            raise RuntimeError(f"snapshot copy of {rel} is damaged; nothing restored")
        cur = ROOT / rel
        same = cur.exists() and hashlib.sha256(cur.read_bytes()).hexdigest() == f["sha256"]
        plan["unchanged" if same else "write"].append(rel)
    plan["quarantine"] = [rel for rel in state["absent"] if (ROOT / rel).exists()]
    if dry_run:
        return {"dry_run": True, **plan}
    touched = plan["write"] + plan["quarantine"]
    pre = save(f"pre-restore-of-{state['label']}", touched or list(state["files"]),
               note=f"automatic, before restoring {Path(png_path).name}") if touched else None
    qdir = BOOT_DIR / "quarantine" / time.strftime("%Y%m%d_%H%M%S")
    for rel in plan["quarantine"]:
        dst = qdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ROOT / rel), str(dst))
    for rel in plan["write"]:
        f = state["files"][rel]
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".state_boot_tmp")
        tmp.write_bytes(base64.b64decode(f["b64"]))
        os.chmod(tmp, f.get("mode", 0o644))
        tmp.replace(dst)
    out = {"restored_from": str(png_path), **plan,
           "undo_with": pre["png"] if pre else None,
           "quarantine_dir": str(qdir.relative_to(ROOT)) if plan["quarantine"] else None}
    if restart and touched:
        out["restart"] = restart_reactor()
    return out


def list_boots() -> list:
    rows = []
    for m in sorted(BOOT_DIR.glob("*.json"), reverse=True):
        try:
            d = json.loads(m.read_text())
            rows.append({"png": d["png"], "label": d["label"], "created": d["created"],
                         "files": len(d["files"]), "absent": len(d["absent"])})
        except Exception:
            pass
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save"); s.add_argument("--label", required=True); s.add_argument("--note", default="")
    s.add_argument("files", nargs="+")
    sub.add_parser("list")
    v = sub.add_parser("verify"); v.add_argument("png")
    r = sub.add_parser("restore"); r.add_argument("png"); r.add_argument("--dry-run", action="store_true")
    r.add_argument("--restart", action="store_true")
    a = ap.parse_args()
    if a.cmd == "save":
        res = save(a.label, a.files, a.note)
    elif a.cmd == "list":
        res = list_boots()
    elif a.cmd == "verify":
        res = verify(a.png)
    else:
        res = restore(a.png, a.dry_run, a.restart)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
