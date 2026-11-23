"""Telegram rollout (v3.8.1): the command menu, inline keyboards, inline mode
and the commands that were "arriving in 3.8.1" (/model, /remember, /voice,
/service, /cancel).

- register_commands(): setMyCommands on bot start, so BotFather /setcommands
  is not needed. The default scope gets the commands anyone allowed can use;
  the owner's private chat gets the full list (the same list as the README).
- Buttons: every inline button carries a short one-time token ("nl:<token>")
  that maps to the action, the person allowed to press it and an expiry.
  Pressing it answers the callback_query, re-checks the person and runs the
  action. Confirmations (/service restart, /model switches) expire after ten
  minutes; heartbeat buttons after a day. Tokens live in the bot process: a
  restart expires them.
- Inline mode (@bot query in any chat): owner only unless
  telegram_settings.inline is "allowlist". Quill gets inline_timeout seconds
  (default 8); a slower answer offers to continue in the private chat.
"""

import json
import secrets
import threading
import time

ALLOWED_UPDATES = ["message", "edited_message", "callback_query", "inline_query"]

# The command menu, in the README's order (README "Telegram commands").
MENU = [
    ("start", "Hello and the command list"),
    ("status", "System & endpoint health"),
    ("health", "Health check (read-only)"),
    ("test", "Run checks (doctor)"),
    ("model", "Exposed model and primary"),
    ("roles", "Show the role model stack"),
    ("recall", "Search memory"),
    ("remember", "Save a memory"),
    ("mcp", "MCP server & tool status"),
    ("tunnel", "Tunnel status & public URL"),
    ("jobs", "Scheduler jobs"),
    ("heartbeat", "Heartbeat status or run one"),
    ("voice", "Spoken replies on or off"),
    ("autoplay", "Play voice replies on the phone speaker"),
    ("bugs", "Recent errors with bug IDs"),
    ("logs", "Tail the service log"),
    ("service", "Service status or restart"),
    ("new", "Reset conversation context"),
    ("cancel", "Stop the reply in progress"),
    ("help", "List the commands"),
]
# shown to everyone (default scope); the rest are owner-only
OPEN_MENU = ("start", "model", "remember", "new", "cancel", "help")

CONFIRM_TTL = 600
BUTTON_TTL = 86400
MAX_TOKENS = 200


def _t(conn):
    return getattr(conn, "t", None) or {}


# -- command menu --------------------------------------------------------------
def menu_commands(owner=True):
    return [{"command": c, "description": d} for c, d in MENU if owner or c in OPEN_MENU]


def register_commands(bot, t=None, log=print):
    """setMyCommands for the default scope and the owner's chat. Never
    raises (the bot runs without a menu if Telegram refuses). -> what it did."""
    t = t or {}
    if t.get("set_commands", True) is False:
        return "off"
    done = []
    try:
        bot.call("setMyCommands", commands=menu_commands(owner=False), scope={"type": "default"})
        done.append("default")
        owner = t.get("owner")
        if owner not in (None, "") and str(owner).lstrip("-").isdigit():
            bot.call("setMyCommands", commands=menu_commands(owner=True),
                     scope={"type": "chat", "chat_id": int(owner)})
            done.append("owner")
        log(f"[ok] Telegram command menu set ({' + '.join(done)}; {len(MENU)} commands for the owner)")
        return "+".join(done)
    except Exception as e:  # noqa: BLE001 - a menu is a nicety, never a reason to stop
        log(f"[telegram] setMyCommands failed: {e}")
        return "failed"


# -- buttons ---------------------------------------------------------------------
def _store(conn):
    st = getattr(conn, "_buttons", None)
    if st is None:
        st = conn._buttons = {}
    return st


def token(conn, uid, action, args=None, ttl=CONFIRM_TTL, clock=time.time, group=None):
    st = _store(conn)
    now = clock()
    for k in [k for k, v in st.items() if v["exp"] < now]:
        st.pop(k, None)
    while len(st) >= MAX_TOKENS:
        st.pop(next(iter(st)))
    tok = secrets.token_hex(5)
    st[tok] = {"uid": str(uid), "action": action, "args": args or {}, "exp": now + ttl, "group": group or tok}
    return "nl:" + tok


def button(conn, uid, text, action, args=None, ttl=CONFIRM_TTL, group=None):
    return {"text": text, "callback_data": token(conn, uid, action, args, ttl, group=group)}


def keyboard(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def confirm(conn, chat_id, uid, question, action, args=None, yes="Yes"):
    """A question with Yes / Cancel buttons; only `uid` may press them."""
    g = secrets.token_hex(4)          # Yes and Cancel go together: pressing one ends both
    kb = keyboard([[button(conn, uid, yes, action, args, group=g), button(conn, uid, "Cancel", "dismiss", group=g)]])
    conn.send(chat_id, question, markup=kb)


def _answer(conn, cq, text="", alert=False):
    try:
        conn.bot.call("answerCallbackQuery", callback_query_id=cq["id"], text=text[:190] or None,
                      show_alert=alert or None, http_timeout=10)
    except Exception as e:  # noqa: BLE001
        conn.log(f"[telegram] answerCallbackQuery: {e}")


def _edit(conn, cq, text, markup=None):
    """Replace the button message's text (the buttons go away unless a new
    markup is given). Falls back to a new message."""
    m = cq.get("message") or {}
    chat_id = (m.get("chat") or {}).get("id")
    try:
        conn.bot.call("editMessageText", chat_id=chat_id, message_id=m.get("message_id"), text=text[:4000],
                      reply_markup=markup, http_timeout=15)
    except Exception:  # noqa: BLE001
        if chat_id is not None:
            conn.send(chat_id, text, markup=markup)


def handle_callback(conn, cq):
    """One callback_query (a button press)."""
    uid = (cq.get("from") or {}).get("id")
    m = cq.get("message") or {}
    chat_id = (m.get("chat") or {}).get("id", uid)
    data = cq.get("data") or ""
    if not conn.allowed(uid, chat_id):
        conn.log(f"[telegram] ignored a button press from {uid} (not on the allowlist)")
        return _answer(conn, cq, "This bot is private.")
    st = _store(conn)
    rec = st.get(data[3:]) if data.startswith("nl:") else None
    if not rec or rec["exp"] < time.time():
        st.pop(data[3:], None)
        return _answer(conn, cq, "That button has expired. Send the command again.", alert=True)
    if rec["uid"] != str(uid):
        return _answer(conn, cq, "That button is not yours.", alert=True)
    act, args = rec["action"], rec["args"]
    if act not in ("hb_toggle", "hb_run"):    # confirmations are one-time; heartbeat buttons stay
        for k in [k for k, v in st.items() if v.get("group") == rec.get("group") or k == data[3:]]:
            st.pop(k, None)
    fn = ACTIONS.get(act)
    if not fn:
        return _answer(conn, cq, "Unknown button.")
    try:
        fn(conn, cq, chat_id, uid, args)
    except Exception as e:  # noqa: BLE001 - a button never stops the poller
        conn.log(f"[telegram] button {act} failed: {type(e).__name__}: {e}")
        _answer(conn, cq, f"Failed: {type(e).__name__}")
        conn.send(chat_id, f"That failed: {type(e).__name__}: {e}")


def _act_dismiss(conn, cq, chat_id, uid, args):
    _answer(conn, cq, "Cancelled")
    _edit(conn, cq, "Cancelled. Nothing was changed.")


# -- /service ----------------------------------------------------------------------
def service_command(conn, chat_id, uid, args):
    from . import tgcmds
    sub = (args.split()[0].lower() if args else "status")
    if sub == "status":
        tgcmds._spawn(lambda: conn.send(chat_id, tgcmds.run_cli(["service", "status"], 60)))
        return
    if sub == "restart":
        confirm(conn, chat_id, uid, "Restart the background service? The endpoint and this bot drop for a few "
                                    "seconds.", "service_restart", yes="Restart")
        return
    conn.send(chat_id, "Usage: /service (status) or /service restart")


def _act_service_restart(conn, cq, chat_id, uid, args):
    from . import tgcmds
    _answer(conn, cq, "Restarting")
    _edit(conn, cq, "Restarting the service in 2 seconds. I'll be back in a few seconds.")
    # answer first, then restart: the restart ends this very process
    restart_later(lambda: tgcmds.run_cli(["service", "restart"], 60))


def restart_later(fn, delay=2.0):
    threading.Timer(delay, fn).start()


# -- /voice ------------------------------------------------------------------------
def voice_command(conn, chat_id, uid, args):
    from . import telegram as TG
    arg = (args or "").strip().lower()
    t = conn.t
    if arg in ("on", "off"):
        new = arg == "on"
    elif arg in ("", "toggle"):
        new = not t.get("voice_replies")
    elif arg == "status":
        new = None
    else:
        conn.send(chat_id, "Usage: /voice [on|off|status] (no argument switches it)")
        return
    if new is not None:
        t["voice_replies"] = new
        try:
            TG.save_keys(voice_replies=new)
        except Exception as e:  # noqa: BLE001
            conn.log(f"[telegram] could not save voice_replies: {e}")
    on = bool(t.get("voice_replies"))
    conn.send(chat_id, f"Spoken replies are {'on' if on else 'off'}." +
              (" When you send a voice note, Quill answers with one." if on else
               " Quill answers voice notes in text."))


# -- /cancel -----------------------------------------------------------------------
def cancel_command(conn, chat_id, uid):
    ev = (getattr(conn, "inflight", None) or {}).get(chat_id)
    if ev is None or ev.is_set():
        conn.send(chat_id, "Nothing to stop: no reply is in progress.")
        return
    ev.set()
    conn.log(f"[telegram] /cancel: stopped the reply in chat {chat_id}")
    conn.send(chat_id, "Stopped. That reply won't be sent.")


# -- /remember ---------------------------------------------------------------------
def remember_command(conn, chat_id, uid, args):
    from . import tgcmds
    text = (args or "").strip()
    if not text:
        conn.send(chat_id, "Usage: /remember <something Quill should remember>")
        return
    if len(text) > 2000:
        conn.send(chat_id, "That's too long to remember in one go (2000 characters at most).")
        return
    argv = ["memory", "add", "--", "--user", f"telegram:{uid}", text]
    tgcmds._spawn(lambda: conn.send(chat_id, tgcmds.run_cli(argv, 90)))


# -- /model ------------------------------------------------------------------------
def model_text():
    from . import config, roles as R, server as S
    s = S.load_settings()
    cl = config.load_cluster_config()
    roles = cl.get("roles") or {}
    lines = [f"Exposed model: {S.main_model(s)} (one name for the whole stack)",
             f"Primary (persona role): {R.describe(roles.get('persona')) or '-'}"]
    for k in ("reasoning", "vision", "asr", "tts"):
        if roles.get(k):
            lines.append(f"  {k}: {R.describe(roles.get(k))}")
    return "\n".join(lines)


def model_command(conn, chat_id, uid, args):
    from . import tgcmds
    parts = (args or "").split()
    if not parts:
        out = tgcmds._safe(model_text)
        if conn.is_owner(uid) and _t(conn).get("model_switch", True):
            out += "\n\nSwitch: /model primary <model id> or /model name <exposed name>"
        conn.send(chat_id, out)
        return
    if not conn.is_owner(uid):
        conn.send(chat_id, "Only the owner can switch the model.")
        return
    if not _t(conn).get("model_switch", True):
        conn.send(chat_id, "Switching the model from Telegram is off (telegram_settings.model_switch).")
        return
    what, value = parts[0].lower(), " ".join(parts[1:]).strip()
    if what not in ("primary", "name") or not value:
        conn.send(chat_id, "Usage: /model primary <model id> or /model name <exposed name>")
        return
    if what == "primary":
        from . import selfadmin
        ok, why = selfadmin.check_role("persona", value)
        if not ok:
            conn.send(chat_id, why)
            return
        confirm(conn, chat_id, uid, f"Make {value} the primary (persona) model?", "model_primary",
                {"model": value}, yes="Switch")
        return
    import re
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}", value):
        conn.send(chat_id, "An exposed name uses letters, digits, dots, dashes, colons or underscores (64 at most).")
        return
    confirm(conn, chat_id, uid, f"Expose the stack as '{value}'? Apps that call the old name need the new one "
                                "after the server restarts.", "model_name", {"name": value}, yes="Rename")


def _act_model_primary(conn, cq, chat_id, uid, args):
    from . import selfadmin
    selfadmin.snapshot("telegram /model primary")
    ok, msg = selfadmin.set_role("persona", args["model"])
    selfadmin.audit("telegram_model", {"primary": args["model"]}, ok, msg,
                    selfadmin.Identity(True, f"telegram:{uid}", "telegram"))
    _answer(conn, cq, "Done" if ok else "Not changed")
    _edit(conn, cq, msg + (" It applies to the next message." if ok else ""))


def _act_model_name(conn, cq, chat_id, uid, args):
    from . import selfadmin, server as S
    selfadmin.snapshot("telegram /model name")
    s = S.load_settings()
    old = S.main_model(s)
    s["model_name"] = args["name"]
    S.save_settings(s)
    msg = f"Changed the exposed model name: {old} -> {args['name']} (applies when the server restarts: /service restart)."
    selfadmin.audit("telegram_model", {"model_name": args["name"]}, True, msg,
                    selfadmin.Identity(True, f"telegram:{uid}", "telegram"))
    _answer(conn, cq, "Done")
    _edit(conn, cq, msg)


# -- heartbeat buttons ---------------------------------------------------------------
def heartbeat_keyboard(conn, uid):
    from . import heartbeat as HB
    rows = [[button(conn, uid, "Run a heartbeat now", "hb_run", ttl=BUTTON_TTL)]]
    acts = sorted(HB.load_actions(), key=lambda x: (x.get("priority", 3), x["name"]))
    for x in acts[:12]:
        on = bool(x.get("enabled"))
        label = f"{x['name']}: {'on' if on else 'off'} (tap to turn {'off' if on else 'on'})"
        rows.append([button(conn, uid, label[:60], "hb_toggle", {"name": x["name"]}, ttl=BUTTON_TTL)])
    return keyboard(rows)


def _act_hb_run(conn, cq, chat_id, uid, args):
    from . import tgcmds
    _answer(conn, cq, "Running a heartbeat")
    conn.send(chat_id, "Running a heartbeat now; the report follows when it ends...")
    tgcmds._spawn(lambda: conn.send(chat_id, tgcmds.run_cli(["heartbeat", "run-now"], 900)))


def _act_hb_toggle(conn, cq, chat_id, uid, args):
    from . import heartbeat as HB, tgcmds
    a = HB.get_action(args["name"])
    if not a:
        return _answer(conn, cq, f"No suggested action named {args['name']} any more.", alert=True)
    new = not bool(a.get("enabled"))
    HB.edit_action(args["name"], {"enabled": new}, who=f"telegram:{uid}", source="telegram")
    _answer(conn, cq, f"{args['name']} is {'on' if new else 'off'}")
    _edit(conn, cq, tgcmds._safe(tgcmds.heartbeat_text), markup=heartbeat_keyboard(conn, uid))


ACTIONS = {
    "dismiss": _act_dismiss,
    "service_restart": _act_service_restart,
    "model_primary": _act_model_primary,
    "model_name": _act_model_name,
    "hb_run": _act_hb_run,
    "hb_toggle": _act_hb_toggle,
}


# -- inline mode -----------------------------------------------------------------------
def inline_allowed(conn, uid):
    mode = str(_t(conn).get("inline", "owner")).lower()
    if mode in ("off", "false", "0"):
        return False
    if mode == "allowlist":
        return conn.allowed(uid, uid)
    return conn.is_owner(uid)


def _article(rid, title, text, desc=""):
    return {"type": "article", "id": rid, "title": title[:64], "description": desc[:120] or None,
            "input_message_content": {"message_text": text[:4096]}}


def handle_inline(conn, iq, run=None):
    """One inline_query: answer within inline_timeout seconds, always."""
    uid = (iq.get("from") or {}).get("id")
    q = (iq.get("query") or "").strip()
    params = {"inline_query_id": iq.get("id"), "cache_time": 0, "is_personal": True}
    chat_btn = {"text": "Open the chat with Quill", "start_parameter": "inline"}
    if not inline_allowed(conn, uid):
        conn.log(f"[telegram] inline query from {uid} refused (inline is owner-only)")
        return _answer_inline(conn, params, [])
    if not q:
        return _answer_inline(conn, params, [], button=chat_btn)
    timeout = float(_t(conn).get("inline_timeout", 8) or 8)
    box = {}

    def ask():
        try:
            box["reply"] = conn.backend.chat([{"role": "user", "content": q}], f"telegram:{uid}",
                                             admin=False)
        except Exception as e:  # noqa: BLE001
            box["error"] = e
    (run or _run_with_deadline)(ask, timeout)
    if "reply" in box and box["reply"]:
        reply = str(box["reply"]).strip()
        first = reply.splitlines()[0] if reply else ""
        results = [_article("quill", "Quill: " + q, reply, first)]
    else:
        why = "Quill needs longer than a moment for that" if "error" not in box else "Quill could not answer"
        results = [_article("ask", "Send the question", q, why + "; this posts your question as it is.")]
    return _answer_inline(conn, params, results, button=chat_btn if "reply" not in box else None)


def _run_with_deadline(fn, timeout):
    th = threading.Thread(target=fn, daemon=True, name="tg-inline")
    th.start()
    th.join(timeout)


def _answer_inline(conn, params, results, button=None):
    try:
        conn.bot.call("answerInlineQuery", results=results, button=button, http_timeout=15, **params)
    except Exception as e:  # noqa: BLE001
        conn.log(f"[telegram] answerInlineQuery: {e}")
    return results


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False)
