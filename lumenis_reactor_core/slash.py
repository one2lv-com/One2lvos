"""
Slash commands (item 9 + the /ai-lobby skill). Handled by the reactor itself, before the council, so they
work the same in lumenis-chat, Discord ("!lumenis /status") and KAI (the phone runs this same reactor code).
They are instant, use no model, and answer from real checks only.

  /help                       list of commands
  /soul                       the soul rules (layer L0)
  /memory [words]             memory layers, or recall by words (stable first, scope shown)
  /memory compile [dry]       run the compile loop                         (owner)
  /memory verify <fact_id>    mark one fact stable / owner_verified        (owner)
  /skills                     loaded skills with tier and guardrails, and any refused skill files
  /status                     live status from real checks                 (owner)
  /approvals                  tool calls held for approval                 (owner)
  /approve <id> [code] | /deny <id>                                         (owner)
  /ai-lobby [status|agents|rooms|start|broadcast <text>]                    (status for all; start, broadcast owner)
  /revert [tags|preview [tag]|confirm <code>|undo <branch>]                (owner, lumenis-chat only)
  /coach, /match, /drill      gaming coach (see gaming.py)

Owner = not a guest, and the channel says so: the Discord owner ID, Cloudflare Access sign-in on the tunnel,
or a connection from this machine. Typed claims never count.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import httpx

from . import soul as _soul

REPO = Path(__file__).resolve().parent.parent
LOBBY = os.environ.get("O2_LOBBY_URL", "http://127.0.0.1:8006")
OWNER_ONLY = {"/status", "/approvals", "/approve", "/deny", "/revert"}
COMMANDS = ("/help", "/soul", "/memory", "/skills", "/status", "/approvals", "/approve", "/deny",
            "/ai-lobby", "/revert", "/coach", "/match", "/drill")


def is_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(t == c or t.startswith(c + " ") for c in COMMANDS)


def owner_from_ws(ws_headers, msg: dict) -> bool:
    """Owner decision for one chat message, from channel signals only."""
    if msg.get("guest") is True:
        return False
    h = ws_headers or {}
    via_tunnel = bool(h.get("cf-connecting-ip"))
    signed_in = bool(h.get("cf-access-jwt-assertion") or h.get("cf-access-authenticated-user-email"))
    if msg.get("identity") == "discord_owner":
        return not via_tunnel          # the Discord listener runs on this machine
    return signed_in if via_tunnel else True


def _fmt(d) -> str:
    return json.dumps(d, indent=1, default=str)


async def _lobby_get(path: str, timeout: float = 5.0):
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.get(LOBBY + path)
        r.raise_for_status()
        return r.json()


async def lobby_status() -> dict:
    try:
        s = await _lobby_get("/status")
        return {"up": True, **s}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:   # an older lobby without /status
            a = await _lobby_get("/agents")
            return {"up": True, "agents": a.get("count"), "note": "older lobby code (no /status)"}
        return {"up": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"up": False, "error": type(e).__name__}


async def lobby_start() -> dict:
    """Start ai_lobby.py the way startos.sh does, only if nothing answers on 8006."""
    st = await lobby_status()
    if st.get("up"):
        return {"started": False, "already_running": True, "status": st}
    py = REPO / ".venv" / "bin" / "python3"
    logf = open(REPO / "logs" / "ai_lobby.log", "a") if (REPO / "logs").is_dir() else subprocess.DEVNULL
    subprocess.Popen([str(py if py.exists() else sys.executable), str(REPO / "ai_lobby.py")], cwd=str(REPO),
                     stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(20):
        await asyncio.sleep(1)
        st = await lobby_status()
        if st.get("up"):
            return {"started": True, "status": st}
    return {"started": False, "error": "launched ai_lobby.py but port 8006 did not answer within 20 s; "
            "see logs/ai_lobby.log"}


async def lobby_broadcast(text: str) -> dict:
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.post(LOBBY + "/broadcast", json={"from": "one2lv", "content": text})
        return {"status": r.status_code, **(r.json() if r.headers.get("content-type", "").startswith(
            "application/json") else {})}


async def _ai_lobby(args: list, owner: bool) -> str:
    sub = (args[0].lower() if args else "status")
    if sub == "status":
        st = await lobby_status()
        if not st.get("up"):
            return (f"AI Lobby (port 8006): DOWN ({st.get('error')})." +
                    (" Type /ai-lobby start to start it." if owner else ""))
        return (f"AI Lobby (port 8006): UP. {st.get('agents')} agents registered in the code "
                f"(not 29); health check: {st.get('agents_by_status')}. Rooms: {st.get('rooms')}, sockets open: "
                f"{st.get('sockets_open')}, messages stored: {st.get('messages_stored')}.\n"
                f"By system: {st.get('agents_by_system')}")
    if sub == "agents":
        a = await _lobby_get("/agents")
        lines = [f"{a['count']} agents ({a.get('online', '?')} online by health check):"]
        lines += [f"- {x['id']} ({x.get('system')}): {x.get('status', '?')}" for x in a["agents"]]
        return "\n".join(lines)
    if sub == "rooms":
        r = await _lobby_get("/rooms")
        return "\n".join([f"{r['count']} rooms:"] + [f"- #{x['room']}: {len(x['members'])} members, "
                          f"{x['sockets_open']} sockets, {x['messages_stored']} messages" for x in r["rooms"]])
    if not owner:
        return "Starting the lobby and broadcasting are owner-only."
    if sub == "start":
        out = await lobby_start()
        if out.get("already_running"):
            return "The AI Lobby is already running on port 8006; nothing started."
        return "AI Lobby started on port 8006." if out.get("started") else f"Not started: {out.get('error')}"
    if sub == "broadcast":
        text = " ".join(args[1:]).strip()
        if not text:
            return "Usage: /ai-lobby broadcast <message>"
        out = await lobby_broadcast(text)
        return (f"Broadcast sent to the lobby (message {out.get('message', {}).get('id')})."
                if out.get("broadcast") else f"Broadcast refused: HTTP {out.get('status')} {out.get('detail', '')}")
    return "Usage: /ai-lobby [status|agents|rooms|start|broadcast <message>]"


async def _revert(args: list, channel: str) -> str:
    from . import revert as rv
    if channel != "lumenis-chat":
        return "Revert is only offered in your lumenis-chat (owner), not here."
    sub = args[0].lower() if args else "preview"
    if sub == "tags":
        t = rv.known_good()
        return "Known-good tags:\n" + ("\n".join(f"- {x['tag']} ({x['commit']}, {x['date']})" for x in t)
                                      or "none yet (tools/tag_known_good.sh makes them after every test passes)")
    if sub == "preview":
        p = rv.preview(args[1] if len(args) > 1 else None)
        if not p["ok"]:
            return "Revert not possible: " + p["error"]
        return (f"Revert preview: {p['current']} -> {p['target']}. Undoes {p['commits_undone_count']} commits:\n"
                + "\n".join("- " + c for c in p["commits_undone"][:15]) + "\n" + "\n".join(p["files"][-6:])
                + f"\n{p['how']}.\nTo go ahead, type: /revert confirm {p['confirm_code']} (10 minutes).")
    if sub == "confirm" and len(args) > 1:
        out = rv.run(args[1])
        if not out["ok"]:
            return "Nothing was changed: " + out["error"]
        return (f"Reverted to {out['reverted_to']} as new commit {out['new_commit']}. Backup branch "
                f"{out['backup_branch']} and bundle {out['backup_bundle']}. Restart the reactor (./startos.sh) to "
                f"run the reverted code. Undo: {out['undo']}")
    if sub == "undo" and len(args) > 1:
        out = rv.undo(args[1])
        return (f"Restored {out['restored_from']} as commit {out['new_commit']}; restart the reactor."
                if out["ok"] else "Nothing was changed: " + out["error"])
    return "Usage: /revert [tags | preview [tag] | confirm <code> | undo <backup-branch>]"


async def handle(text: str, owner: bool, compass=None, channel: str = "chat") -> Optional[str]:
    """Answer a slash command, or None when the text is not one."""
    if not is_command(text):
        return None
    parts = text.strip().split()
    cmd, args = parts[0].lower(), parts[1:]
    if cmd in OWNER_ONLY and not owner:
        return f"{cmd} is owner-only."
    try:
        if cmd == "/help":
            return ("Commands: /soul, /memory [words], /skills, /ai-lobby [status|agents|rooms]"
                    + (", /status, /memory compile, /memory verify <id>, /approvals, /approve <id> [code], "
                       "/deny <id>, /ai-lobby start|broadcast <text>, /revert (lumenis-chat only), /coach, "
                       "/match, /drill" if owner else ""))
        if cmd == "/soul":
            return ("Soul rules (layer L0, memory_layers/SOUL.md" + ("" if _soul.loaded() else ", FILE MISSING: "
                    "fallback rules") + "):\n" + _soul.rules())
        if cmd == "/skills":
            from . import skills
            r = skills.load_all()
            lines = [f"{len(r['loaded'])} skills loaded:"]
            lines += [f"- {s['name']} v{s['version']} ({s['risk_tier']}): {s['description']} Guardrails: "
                      f"{', '.join(s['guardrails'])}" for s in r["loaded"]]
            if r["refused"]:
                lines.append(f"{len(r['refused'])} skill files refused:")
                lines += [f"- {x['file']}: {'; '.join(x['errors'])}" for x in r["refused"]]
            return "\n".join(lines)
        if cmd == "/memory":
            from . import memory_hub as hub
            if args and args[0].lower() == "compile":
                if not owner:
                    return "/memory compile is owner-only."
                rep = hub.compile(compass, dry_run=len(args) > 1 and args[1].lower().startswith("dry"))
                return ("Compile loop" + (" (dry run, nothing changed)" if rep["dry_run"] else "") +
                        f": expired {rep['expired']}, canonical facts {rep['canonical_count']}. Layers: "
                        f"{rep['layers']}")
            if args and args[0].lower() == "verify":
                if len(args) < 2:
                    return "Usage: /memory verify <fact_id>"
                out = compass.promote_fact(args[1], by_owner=owner)
                return (f"Fact {args[1]} is now stable (owner_verified)." if out["ok"] else
                        "Not verified: " + out["error"])
            if not args:
                return (f"Memory layers (active/expired): {compass.layer_stats()}. Dreams are kept in the dream "
                        f"store, separate from these.")
            if not owner:
                return "Memory recall by command is owner-only."
            facts = compass.recall_facts(" ".join(args)[:100], limit=8)
            if not facts:
                return "Nothing in memory matches that."
            return "\n".join(f"- [{f.get('scope') or 'fuzzy'}] {f['key']}: {str(f['value'])[:200]} "
                             f"({f.get('verification')}, id {f.get('id')})" for f in facts)
        if cmd == "/status":
            from . import live_status as ls
            snap = await ls.snapshot()
            return ls.block(snap)
        if cmd in ("/approvals", "/approve", "/deny"):
            from . import tool_engine as te
            if cmd == "/approvals":
                rows = te.list_approvals("pending") + te.list_approvals("confirm")
                return ("\n".join(f"- {r['id']}: {r['tool']} ({r['tier']}, from {r['caller']}, {r['created']}) "
                                  f"args {r['args'][:120]}" for r in rows) or "No tool calls are waiting.")
            if not args:
                return f"Usage: {cmd} <approval id>" + (" [code]" if cmd == "/approve" else "")
            out = await te.decide_approval(args[0], cmd == "/approve", by_owner=owner,
                                           confirm_code=args[1] if len(args) > 1 else None)
            if out.get("decision") == "confirm_needed":
                return f"{args[0]} is L3 (destructive). To run it, type: /approve {args[0]} {out['confirm_code']}"
            if not out.get("ok") and not out.get("ran"):
                return "Not done: " + str(out.get("error"))
            if out.get("decision") == "denied":
                return f"Denied {args[0]}; nothing ran."
            r = out.get("result", {})
            return (f"Approved {args[0]}: {r.get('tool')} ran, ok={r.get('ok')}, status {r.get('status')}.\n"
                    + str(r.get("result") if r.get("ok") else r.get("error"))[:1500])
        if cmd == "/ai-lobby":
            return await _ai_lobby(args, owner)
        if cmd == "/revert":
            return await _revert(args, channel)
        if cmd in ("/coach", "/match", "/drill"):
            from . import gaming
            return await gaming.command(cmd, args, owner)
    except Exception as e:
        return f"{cmd} failed: {type(e).__name__}: {str(e)[:200]}"
    return None
