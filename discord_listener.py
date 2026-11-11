#!/usr/bin/env python3
"""
One2lvOS Discord chat listener for Lumenis.

Watches one channel (DISCORD_CHANNEL_ID) for messages that start with "!lumenis"
(optionally "!lumenis <text>") or that @mention the bot, sends the text through the
live reactor's council chat socket (ws://127.0.0.1:8000/ws, the same path the app's
chat uses) and replies in the channel with his answer.

  * The owner (DISCORD_OWNER_ID, matched by user ID) gets full Lumenis.
  * Everyone else gets the reactor's guest mode (no Hermes/external services, no
    shared files, no tool engine, no private memory recall, no auto-learning).
  * Other bots (and this bot) are ignored. Per-user rate limits apply.
  * Every message it posts sets allowed_mentions so it can never ping @everyone,
    @here, roles or other users; only the author of the triggering message is
    reply-pinged.
  * It posts nothing unprompted.

Secrets come from .env (DISCORD_BOT_TOKEN); none are in this file.

Usage:
  python3 discord_listener.py                      # run the listener (one gateway connection)
  python3 discord_listener.py --dry-run "hello" [--as owner|guest]
        # push a simulated message through the same handler to the reactor, print the
        # reply chunks, post nothing to Discord
"""
import argparse
import asyncio
import fcntl
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
import websockets
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

REACTOR = os.environ.get("O2_REACTOR", "http://127.0.0.1:8000")
REACTOR_WS = REACTOR.replace("http", "ws", 1) + "/ws"
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", "0") or 0)
OWNER_ID = int(os.environ.get("DISCORD_OWNER_ID", "0") or 0)
SESSIONS_FILE = ROOT / "data" / "discord_sessions.json"
LOCK_FILE = "/tmp/o2_discord_listener.lock"

REPLY_TIMEOUT = 320          # seconds to wait for the council's final answer
MAX_INPUT = 2000             # characters of the user's message sent to the reactor
DISCORD_LIMIT = 1990         # Discord allows 2000 per message; keep a little margin
MAX_PARALLEL = 2             # council chats running at once from Discord

# (max messages, window seconds)
OWNER_LIMITS = [(30, 600)]
GUEST_LIMITS = [(5, 600), (20, 3600)]
ALL_GUESTS_LIMIT = (40, 3600)

THINKING_EMOJI = "\U0001F440"   # eyes

log = logging.getLogger("discord_listener")


# ── Parsing ──────────────────────────────────────────────────────────────────
_PREFIX = re.compile(r"^\s*!lumenis\b[\s:,]*", re.I)


def parse_request(content: str, bot_id: int | None):
    """Return the text addressed to Lumenis, "" if addressed with no text, or None."""
    if content is None:
        return None
    text = None
    m = _PREFIX.match(content)
    if m:
        text = content[m.end():]
    elif bot_id and re.search(rf"<@!?{bot_id}>", content):
        text = re.sub(r"[ \t]{2,}", " ", re.sub(rf"<@!?{bot_id}>", " ", content))
    if text is None:
        return None
    text = text.strip()
    # The owner writes "!lumenis <whats up?>": drop one pair of wrapping angle brackets,
    # but leave Discord mentions/emoji/links (<@123>, <:x:1>, <https://..>) alone.
    if text.startswith("<") and text.endswith(">") and not re.match(r"^<(@|#|:|a:|https?://|t:)", text):
        text = text[1:-1].strip()
    return text[:MAX_INPUT]


def split_reply(text: str, limit: int = DISCORD_LIMIT):
    """Split text into Discord-sized pieces, preferring paragraph, line, then word breaks."""
    text = (text or "").strip()
    parts = []
    while len(text) > limit:
        cut = -1
        for sep in ("\n\n", "\n", " "):
            cut = text.rfind(sep, int(limit * 0.5), limit)
            if cut > 0:
                break
        if cut <= 0:
            cut = limit
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts


# ── Rate limiting ────────────────────────────────────────────────────────────
class RateLimiter:
    def __init__(self):
        self.users = defaultdict(deque)
        self.guests = deque()

    @staticmethod
    def _trim(q, window, now):
        while q and now - q[0] > window:
            q.popleft()

    def check(self, user_id: int, guest: bool):
        """Return None if allowed (and record it), else a short reason."""
        now = time.time()
        q = self.users[user_id]
        limits = GUEST_LIMITS if guest else OWNER_LIMITS
        longest = max(w for _, w in limits)
        self._trim(q, longest, now)
        for n, window in limits:
            if sum(1 for t in q if now - t <= window) >= n:
                return f"you've hit the limit of {n} messages per {window // 60} minutes, try again a bit later"
        if guest:
            n, window = ALL_GUESTS_LIMIT
            self._trim(self.guests, window, now)
            if len(self.guests) >= n:
                return "Lumenis is busy with guests right now, try again in a few minutes"
            self.guests.append(now)
        q.append(now)
        return None


# ── Sessions (one reactor conversation per Discord user) ─────────────────────
def _load_sessions():
    try:
        return json.loads(SESSIONS_FILE.read_text())
    except Exception:
        return {}


def _save_sessions(d):
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SESSIONS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1))
    os.replace(tmp, SESSIONS_FILE)


# ── Listener state for the reactor's live status (no secrets) ────────────────
STATE_FILE = Path(__file__).resolve().parent / "data" / "discord_listener_state.json"


def _write_state(**kv):
    try:
        st = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
        st.update(kv)
        STATE_FILE.parent.mkdir(exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=1))
        tmp.replace(STATE_FILE)
    except Exception as e:
        log.warning("could not write listener state: %s", type(e).__name__)


# ── The reactor call (shared by the live listener and --dry-run) ─────────────
async def ask_lumenis(user_id: int, name: str, text: str, guest: bool, on_chunk=None, key_prefix: str = ""):
    """Send one message through the reactor's council chat socket. Returns (reply, meta).
    Raises RuntimeError with a short reason on failure."""
    sessions = _load_sessions()
    key = key_prefix + (("guest:" if guest else "owner:") + str(user_id))
    session_id = sessions.get(key)
    out = {"action": "chat", "message": text, "session_id": session_id}
    if guest:
        out["guest"] = True
        out["guest_name"] = f"discord:{name}"[:40]
    else:
        # The owner is decided by Discord user ID (DISCORD_OWNER_ID): the channel's identity signal.
        out["identity"] = "discord_owner"
    chunks, meta = [], {}
    try:
        async with websockets.connect(REACTOR_WS, max_size=None, ping_interval=None, open_timeout=15) as ws:
            if not session_id:
                title = (f"Discord guest: {name}" if guest else f"Discord: {name}")[:60]
                await ws.send(json.dumps({"action": "new_session", "title": title}))
            else:
                await ws.send(json.dumps(out))
            sent = bool(session_id)
            deadline = time.time() + REPLY_TIMEOUT
            while True:
                left = deadline - time.time()
                if left <= 0:
                    raise RuntimeError(f"the council gave no final answer within {REPLY_TIMEOUT} s")
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=min(left, 30))
                except asyncio.TimeoutError:
                    continue
                m = json.loads(raw)
                t = m.get("type")
                if t == "ping":
                    await ws.send(json.dumps({"action": "ping"}))
                elif t == "session_created" and m.get("session_id"):
                    session_id = m["session_id"]
                    sessions = _load_sessions()
                    sessions[key] = session_id
                    _save_sessions(sessions)
                    if not sent:
                        out["session_id"] = session_id
                        await ws.send(json.dumps(out))
                        sent = True
                elif t == "response_chunk":
                    chunks.append(m.get("text", ""))
                    if on_chunk:
                        on_chunk(m.get("text", ""))
                elif t == "error":
                    raise RuntimeError(m.get("message") or "the reactor reported an error with no message "
                                       "(most likely a model timeout)")
                elif t == "processing_done":
                    meta = m.get("meta") or {}
                    break
    except RuntimeError:
        raise
    except (OSError, websockets.exceptions.WebSocketException, asyncio.TimeoutError) as e:
        raise RuntimeError(f"couldn't reach the reactor ({type(e).__name__})")

    reply = "".join(chunks).strip()
    # The reactor saves the final answer; prefer that copy when it is there.
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{REACTOR}/api/sessions/{session_id}/history")
            hist = r.json() if r.status_code == 200 else []
        if isinstance(hist, list) and hist and hist[-1].get("role") == "assistant" and hist[-1].get("content"):
            reply = str(hist[-1]["content"]).strip()
    except Exception:
        pass
    if not reply:
        raise RuntimeError("the council finished but returned an empty answer")
    return reply, meta


# ── Discord side ─────────────────────────────────────────────────────────────
def run_bot():
    import discord

    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        log.error("DISCORD_BOT_TOKEN missing from .env")
        sys.exit(2)
    if not CHANNEL_ID:
        log.error("DISCORD_CHANNEL_ID missing from .env")
        sys.exit(2)
    if not OWNER_ID:
        log.warning("DISCORD_OWNER_ID not set: everyone, including the owner, gets guest mode")

    intents = discord.Intents.default()
    intents.message_content = True
    # Never ping @everyone/@here, roles or other users; only reply-ping the author.
    no_pings = discord.AllowedMentions(everyone=False, roles=False, users=False, replied_user=True)
    client = discord.Client(intents=intents, allowed_mentions=no_pings)
    limiter = RateLimiter()
    in_flight = set()
    parallel = asyncio.Semaphore(MAX_PARALLEL)

    async def send_reply(message, text):
        parts = split_reply(text)
        first = True
        for p in parts:
            if first:
                try:
                    await message.reply(p, allowed_mentions=no_pings, mention_author=True)
                except discord.HTTPException:
                    await message.channel.send(p, allowed_mentions=no_pings)
                first = False
            else:
                await message.channel.send(p, allowed_mentions=no_pings)
        return len(parts)

    @client.event
    async def on_ready():
        _write_state(connected_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
        log.info("connected as %s (%s); watching channel %s; owner %s",
                 client.user, client.user.id, CHANNEL_ID, OWNER_ID or "none")

    @client.event
    async def on_message(message):
        if message.author.bot or (client.user and message.author.id == client.user.id):
            return
        if message.guild is None or message.channel.id != CHANNEL_ID:
            return
        text = parse_request(message.content, client.user.id if client.user else None)
        if text is None:
            return
        uid = message.author.id
        guest = uid != OWNER_ID
        who = f"{message.author} ({uid}, {'guest' if guest else 'owner'})"
        if not text:
            await send_reply(message, "Say something after `!lumenis`, like `!lumenis what's up?`")
            return
        if uid in in_flight:
            await send_reply(message, "Lumenis is still answering your last message, give him a moment.")
            log.info("busy for %s", who)
            return
        why = limiter.check(uid, guest)
        if why:
            log.info("rate limited %s: %s", who, why)
            await send_reply(message, f"Slow down a little: {why}.")
            return

        in_flight.add(uid)
        log.info("message from %s: %r", who, text[:200])
        started = time.time()
        reacted = False
        try:
            try:
                await message.add_reaction(THINKING_EMOJI)
                reacted = True
            except discord.HTTPException:
                pass
            async with parallel:
                async with message.channel.typing():
                    try:
                        reply, meta = await ask_lumenis(uid, message.author.name, text, guest)
                    except RuntimeError as e:
                        log.warning("no answer for %s: %s", who, e)
                        await send_reply(message, f"Lumenis couldn't answer this time: {e}.")
                        return
            n = await send_reply(message, reply)
            _write_state(last_post_ok_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
            log.info("replied to %s in %.0f s (%d chars, %d message%s, seats=%s, guest_mode=%s)",
                     who, time.time() - started, len(reply), n, "" if n == 1 else "s",
                     meta.get("seats_activated"), meta.get("guest_mode"))
        except Exception:
            log.exception("handler failed for %s", who)
        finally:
            in_flight.discard(uid)
            if reacted:
                try:
                    await message.remove_reaction(THINKING_EMOJI, client.user)
                except Exception:
                    pass

    client.run(token, log_handler=None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", metavar="MESSAGE",
                    help='simulate a Discord message (e.g. "!lumenis hello") through the handler; posts nothing')
    ap.add_argument("--as", dest="as_", choices=["owner", "guest"], default="owner")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        stream=sys.stdout)
    logging.getLogger("discord").setLevel(logging.INFO)

    if args.dry_run is not None:
        uid = OWNER_ID if args.as_ == "owner" else 1
        text = parse_request(args.dry_run, None)
        print(f"parsed: {text!r}  as={args.as_}  guest={uid != OWNER_ID}")
        if not text:
            print("not addressed to Lumenis (or empty); nothing sent")
            return
        t0 = time.time()
        reply, meta = asyncio.run(ask_lumenis(uid, "dry-run-" + args.as_, text, uid != OWNER_ID, key_prefix="dryrun:"))
        parts = split_reply(reply)
        print(f"--- reply in {time.time() - t0:.0f} s, {len(reply)} chars, {len(parts)} Discord message(s), meta={meta}")
        for i, p in enumerate(parts, 1):
            print(f"[{i}/{len(parts)}] {p}")
        return

    # Only one gateway connection: a second copy exits straight away.
    lock = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log.info("another discord_listener is already running; exiting")
        return
    run_bot()


if __name__ == "__main__":
    main()
