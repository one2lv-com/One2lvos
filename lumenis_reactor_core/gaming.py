"""
Gaming coach (items 10-12, as far as the recorded data allows).

Source of truth: data/vision/observations.jsonl, written by the vision feed (vision.py) from real frames
analysed by NVIDIA's Nemotron omni model. Nothing here watches live or presses buttons: vision runs
2-4 s behind, so live play as a second player is not possible with it.

  /match                    list recorded vision sessions
  /match <session>          post-match report: frames, scene, events seen, HUD values read, latency, and
                            what the model could not tell (its own cannot_tell lists)
  /coach [session]          coach notes from that session's recorded events (counted, not invented)
  /drill                    your drill log (e.g. Queen Nai bomb catches)          (owner)
  /drill <name> <count>     log one attempt, e.g. /drill bomb 7                   (owner)
"""
from __future__ import annotations

import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
OBS = ROOT / "data" / "vision" / "observations.jsonl"
DRILLS = ROOT / "data" / "gaming" / "drills.jsonl"
DRILL_GOALS = {"bomb": 10}


def _obs(path: Path = OBS) -> List[Dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def sessions(path: Path = OBS) -> List[Dict]:
    by: Dict[str, List[Dict]] = {}
    for r in _obs(path):
        by.setdefault(r.get("session") or "?", []).append(r)
    rows = []
    for sid, rs in by.items():
        rows.append({"session": sid, "frames": len(rs), "game": Counter(r.get("game") for r in rs).most_common(1)[0][0],
                     "label": rs[0].get("label"), "start": rs[0].get("captured_at"), "end": rs[-1].get("captured_at")})
    return sorted(rows, key=lambda r: r["start"] or "")


def match_report(session: str, path: Path = OBS) -> Dict:
    rs = [r for r in _obs(path) if (r.get("session") or "").startswith(session)]
    if not rs:
        return {"ok": False, "error": f"no recorded frames for session {session!r}"}
    events = Counter(e for r in rs for e in (r.get("events") or []))
    cannot = Counter(c for r in rs for c in (r.get("cannot_tell") or []))
    hud_read = Counter(k for r in rs for k, v in (r.get("hud") or {}).items() if v not in (None, "", []))
    lat = [r["end_to_end_s"] for r in rs if isinstance(r.get("end_to_end_s"), (int, float))]
    return {
        "ok": True, "session": rs[0].get("session"), "frames": len(rs), "game": rs[0].get("game"),
        "label": rs[0].get("label"), "from": rs[0].get("captured_at"), "to": rs[-1].get("captured_at"),
        "scenes": dict(Counter(r.get("scene") for r in rs)),
        "confidence": dict(Counter(r.get("confidence") for r in rs)),
        "top_events": events.most_common(8), "hud_fields_read": dict(hud_read),
        "callouts": [r["callout"] for r in rs if r.get("callout")][:6],
        "frames_with": {w: sum(1 for r in rs if any(any(x in e.lower() for x in ws) for e in (r.get("events") or [])))
                        for w, ws in (("bomb", ("bomb",)), ("edge", ("hanging", "ledge", "edge", "recover")))},
        "latency_s": ({"median": round(statistics.median(lat), 2), "max": round(max(lat), 2)} if lat else None),
        "model_could_not_tell": cannot.most_common(6), "verified": False,
        "note": "Readings are the vision model's, unverified; nothing was watched live."}


def coach_notes(rep: Dict) -> List[str]:
    """Notes that follow only from the counted readings."""
    notes = []
    n = rep["frames"]
    bombs = rep["frames_with"]["bomb"]
    if bombs:
        notes.append(f"Bombs showed up in {bombs} of {n} frames: good footage for your bomb-catch drill.")
    edge = rep["frames_with"]["edge"]
    if edge:
        notes.append(f"Edge or hanging moments in {edge} of {n} frames: check those clips for recovery timing.")
    if not rep["hud_fields_read"]:
        notes.append("The model read no damage, stocks or timer in any frame, so it can't judge trades or stock "
                     "leads yet. A larger, sharper capture of the HUD would fix that.")
    if rep.get("latency_s") and rep["latency_s"]["median"] > 1.0:
        notes.append(f"Vision ran {rep['latency_s']['median']} s behind (median), so tips are for after the "
                     f"match, not live.")
    if not notes:
        notes.append("Not enough in these readings for a specific tip.")
    return notes


def log_drill(name: str, count: int) -> Dict:
    DRILLS.parent.mkdir(parents=True, exist_ok=True)
    row = {"drill": name.lower(), "count": int(count), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with DRILLS.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return drill_stats(name)


def drill_stats(name: str = None) -> Dict:
    rows = []
    if DRILLS.is_file():
        rows = [json.loads(l) for l in DRILLS.read_text().splitlines() if l.strip()]
    out = {}
    for r in rows:
        if name and r["drill"] != name.lower():
            continue
        d = out.setdefault(r["drill"], {"attempts": 0, "best": 0, "last": None, "goal": DRILL_GOALS.get(r["drill"])})
        d["attempts"] += 1
        d["best"] = max(d["best"], r["count"])
        d["last"] = r["count"]
    return out


async def command(cmd: str, args: list, owner: bool) -> str:
    if not owner:
        return "The gaming coach is owner-only for now."
    if cmd == "/match":
        if not args:
            ss = sessions()
            return ("Recorded vision sessions:\n" + "\n".join(
                f"- {s['session']}: {s['frames']} frames of {s['game']} ({s['label']}), {s['start']}" for s in ss)
                + "\nType /match <session> for the report.") if ss else "No recorded vision sessions yet."
        r = match_report(args[0])
        if not r["ok"]:
            return r["error"]
        return (f"Match report {r['session']} ({r['game']}, {r['frames']} frames, {r['from']} to {r['to']}):\n"
                f"- Events seen: {', '.join(f'{k} x{v}' for k, v in r['top_events']) or 'none'}\n"
                f"- HUD values read: {r['hud_fields_read'] or 'none'}\n"
                f"- Model confidence: {r['confidence']}; latency {r['latency_s']}\n"
                f"- It could not tell: {', '.join(k for k, _ in r['model_could_not_tell'])}\n"
                f"Unverified vision readings; nothing was watched live.")
    if cmd == "/coach":
        ss = sessions()
        if not ss:
            return "No recorded matches to coach from yet."
        r = match_report(args[0] if args else ss[-1]["session"])
        if not r["ok"]:
            return r["error"]
        return f"Coach notes from {r['session']} ({r['frames']} frames):\n" + "\n".join("- " + n for n in coach_notes(r))
    if cmd == "/drill":
        if len(args) >= 2 and args[1].isdigit():
            st = log_drill(args[0], int(args[1]))[args[0].lower()]
            goal = f" Goal {st['goal']}." if st["goal"] else ""
            return f"Logged {args[0]} drill: {args[1]}. Best {st['best']} over {st['attempts']} attempts.{goal}"
        st = drill_stats(args[0] if args else None)
        if not st:
            return "No drills logged yet. Log one with /drill bomb 7."
        return "\n".join(f"- {k}: best {v['best']}, last {v['last']}, {v['attempts']} attempts"
                         + (f" (goal {v['goal']})" if v["goal"] else "") for k, v in st.items())
    return "Usage: /match [session], /coach [session], /drill [name count]"
