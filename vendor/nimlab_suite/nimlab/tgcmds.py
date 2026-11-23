"""Telegram slash commands (3.8.0; carried over from the interim patch).

Hooked into TelegramConnector.handle() just before the /start-/help check.
handle() returns True when it answered the command, False to fall through
(/reset, /id and plain chat stay with telegram.py).

Everything except /start, /help and /new is owner-only. Commands that run
the nimlab CLI do it in a background thread so a slow one never blocks the
poller. /jobs and /heartbeat (status) answer in-process from the scheduler's
files; `/heartbeat run` starts one heartbeat in the background and sends its
report when it ends. Commands in the BotFather menu that are not built yet
answer with the version they arrive in, instead of going to Quill as chat.

/autoplay (3.8.0) plays Quill's Telegram voice replies on the phone's own
speaker as well (termux-media-player, else play-audio), so you don't have to
tap play in Telegram. telegram.py calls autoplay() right after sendVoice; it
never raises and never delays the reply.

The full rollout (setMyCommands on start, inline mode, buttons) is 3.8.1.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import threading

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
MAX_CHARS = 3500
GREETING = "Hi! Send text, a photo or a voice note. Quill answers."

# command -> (description, argv builder, timeout seconds); None = handled in code
COMMANDS = {
    "/status": ("System & endpoint health", None, 60),
    "/test": ("Run checks (doctor: memory, prompts, MCP)", lambda a: ["doctor"], 180),
    "/health": ("Health check (read-only doctor): /health or /health full", None, 240),
    "/roles": ("Show the 16-role model stack", lambda a: ["roles"], 30),
    "/recall": ("Search memory: /recall <words>", lambda a: ["memory", "recall", *a.split()], 60),
    "/mcp": ("MCP server & tool status", lambda a: ["mcp", "show"], 30),
    "/tunnel": ("Tunnel status & public URL", lambda a: ["serve", "tunnel", "status"], 30),
    "/jobs": ("Scheduler jobs: next run, last result", None, 30),
    "/heartbeat": ("Heartbeat status; /heartbeat run starts one now", None, 900),
    "/bugs": ("Recent errors with bug IDs", lambda a: ["bugs", "list", "--limit", "10"], 30),
    "/logs": ("Tail the service log", lambda a: ["service", "logs", "--lines", "30"], 30),
    "/autoplay": ("Play voice replies on the phone speaker: /autoplay [on|off|status]", None, 10),
}
# 3.8.1: built in nimlab.tgui (the "arriving in 3.8.1" commands)
UI_COMMANDS = {
    "/model": "Exposed model and primary; owner: /model primary <id> | /model name <name>",
    "/remember": "Save a memory: /remember <text>",
    "/voice": "Spoken replies to voice notes: /voice [on|off]",
    "/service": "Service status; /service restart (asks first)",
    "/cancel": "Stop the reply in progress",
}
PLANNED = {}
HELP_ORDER = ["/status", "/health", "/test", "/model", "/roles", "/recall", "/remember", "/mcp", "/tunnel", "/jobs",
              "/heartbeat", "/voice", "/autoplay", "/bugs", "/logs", "/service", "/cancel"]
OPEN = ("/start", "/help", "/new", "/model", "/remember", "/cancel")   # not owner-only (3.8.1)


def help_text(owner=True):
    lines = [GREETING, "", "Commands:"]
    for c in HELP_ORDER:
        if not owner and c not in OPEN:
            continue
        desc = COMMANDS[c][0] if c in COMMANDS else UI_COMMANDS[c]
        lines.append(f"{c} - {desc}")
    lines += ["/new - Reset conversation context", "/id - Show your Telegram ID", "/help - This list"]
    if owner:
        lines += ["", "Inline: type @<bot name> and a question in any chat."]
    return "\n".join(lines)


def _botfather():
    from . import tgui
    return list(tgui.MENU)


# The command menu (README "Telegram commands"). 3.8.1: the bot registers it
# itself with setMyCommands on start (nimlab.tgui.MENU), so BotFather
# /setcommands is not needed; this text is for pasting by hand if wanted.
BOTFATHER = _botfather()


def botfather_text():
    return "\n".join(f"{c} - {d}" for c, d in BOTFATHER)


# -- /autoplay ---------------------------------------------------------------
AUTOPLAY_FILE = os.path.join(PROJECT, "data", "tg_autoplay.json")
AUTOPLAY_AUDIO = os.path.join(PROJECT, "data", "tg_autoplay_last")
PLAYERS = ("termux-media-player", "play-audio")
_play_lock = threading.Lock()


def _termux():
    from .shortcut import is_termux
    return is_termux()


def autoplay_on(path=None):
    try:
        with open(path or AUTOPLAY_FILE, encoding="utf-8") as f:
            return bool((json.load(f) or {}).get("on"))
    except (OSError, ValueError, AttributeError):
        return False


def set_autoplay(on, path=None):
    path = path or AUTOPLAY_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"on": bool(on)}, f)
    os.replace(tmp, path)


def player():
    """The first audio player on PATH (termux-media-player, then play-audio), or None."""
    for p in PLAYERS:
        if shutil.which(p):
            return p
    return None


def _play_cmds(p, path):
    if p == "termux-media-player":
        return [([p, "stop"], 15), ([p, "play", path], 30)]
    return [([p, path], 600)]


def autoplay(data, ext=".wav", log=print, spawn=None, run=None):
    """Play a voice reply that was just sent to Telegram on this phone's
    speaker, when /autoplay is on. Returns quickly (playing happens on a
    background thread) and never raises: a missing player, an unwritable
    file or a player that fails is logged, and the reply already went out.
    -> what it did: 'off', 'empty', 'not termux', 'no player' or 'playing'."""
    try:
        if not autoplay_on():
            return "off"
        if not data:
            return "empty"
        if not _termux():
            # 3.8.5: on the VPS, hand the reply to the active phone over the audio bus
            from . import audiobus
            try:
                ev = audiobus.publish(data, fmt=str(ext).lstrip("."), source="telegram", agent="quill")
                log(f"[telegram] autoplay: relayed to phone '{ev['target']}' ({ev['ext']}, {ev['bytes']} bytes)")
                return "relayed"
            except audiobus.BusError as e:
                log(f"[telegram] autoplay is on, but no phone took it: {e.message}")
                return "no device"
        p = player()
        if not p:
            log("[telegram] autoplay is on but no player was found (pkg install termux-api, plus the Termux:API app)")
            return "no player"
        path = AUTOPLAY_AUDIO + (ext if str(ext).startswith(".") else "." + str(ext))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        run = run or (lambda cmd, timeout: subprocess.run(cmd, capture_output=True, timeout=timeout))

        def play():
            with _play_lock:   # one reply at a time; a newer one waits instead of talking over it
                try:
                    for cmd, timeout in _play_cmds(p, path):
                        run(cmd, timeout)
                except Exception as e:  # noqa: BLE001
                    log(f"[telegram] autoplay failed: {type(e).__name__}: {e}")
        (spawn or _spawn)(play)
        return "playing"
    except Exception as e:  # noqa: BLE001 - never break the voice reply
        try:
            log(f"[telegram] autoplay failed: {type(e).__name__}: {e}")
        except Exception:  # noqa: BLE001
            pass
        return "error"


def autoplay_command(conn, arg):
    """The reply to /autoplay [on|off|status] (no argument toggles)."""
    arg = (arg or "").strip().lower()
    if arg in ("on", "off"):
        new = arg == "on"
    elif arg in ("", "toggle"):
        new = not autoplay_on()
    elif arg == "status":
        new = None
    else:
        return "Usage: /autoplay [on|off|status] (no argument switches it)"
    if new is not None:
        set_autoplay(new)
    on = autoplay_on()
    lines = [f"Autoplay is {'on' if on else 'off'}."]
    if on:
        if not _termux():
            from . import audiobus
            a = audiobus.active()
            st = audiobus.device_state(a) if a else None
            if st:
                lines.append(f"Voice replies are relayed to phone '{a}' over the audio bus ("
                             + ("connected" if st["online"] else "not connected right now: start nimbridge there")
                             + ").")
            else:
                lines.append("No phone is active on the audio bus, so nothing will play. "
                             "Start nimbridge on a phone (nimlab audio add NAME on the server first).")
        elif not player():
            lines.append("No player found: pkg install termux-api (and install the Termux:API app). "
                         "play-audio works as well.")
        else:
            lines.append(f"Voice replies will also play on the phone speaker ({player()}).")
        if not (getattr(conn, "t", None) or {}).get("voice_replies"):
            lines.append("Voice replies are off, so there's nothing to play yet: "
                         "nimlab telegram voice on (spoken replies to voice notes).")
    return "\n".join(lines)


def _cut(out):
    out = ANSI.sub("", str(out or "")).strip() or "(no output)"
    if len(out) > MAX_CHARS:
        out = out[:MAX_CHARS] + "\n... (cut; run it in the terminal for the rest)"
    return out


def run_cli(args, timeout):
    env = dict(os.environ, NIMLAB_COLOR="0", NO_COLOR="1")
    try:
        r = subprocess.run([sys.executable, "-m", "nimlab", *args], cwd=PROJECT, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (("\n" + r.stderr) if r.stderr.strip() else "")
    except subprocess.TimeoutExpired:
        out = f"(timed out after {timeout} s)"
    except Exception as e:  # noqa: BLE001
        out = f"(could not run: {type(e).__name__}: {e})"
    return _cut(out)


def _spawn(fn):
    threading.Thread(target=fn, daemon=True, name="tgcmd").start()


def health_args(arg=""):
    """/health: the quick read-only doctor; /health full adds the memory round
    trip and the MCP check. Never --fix: repairs are the terminal's."""
    full = (arg or "").strip().lower() in ("full", "all", "memory")
    return ["doctor", "--json"] + ([] if full else ["--quick"])


def health_text(raw):
    """doctor --json output -> a short plain-text report (no colors)."""
    import json as _json
    try:
        start = raw.index("{")
        rep = _json.loads(raw[start:raw.rindex("}") + 1])
    except (ValueError, TypeError):
        return "Health check: could not read the doctor output.\n" + _cut(raw)[:800]
    n = rep.get("summary") or {}
    head = ("Healthy" if rep.get("ok") and not n.get("warn") else ("Working, with warnings" if rep.get("ok")
            else "Needs attention"))
    lines = [f"{head}: {n.get('ok', 0)} ok, {n.get('warn', 0)} warnings, {n.get('fail', 0)} problems "
             f"(v{rep.get('version', '?')})"]
    last = None
    for c in rep.get("checks") or []:
        if c.get("status") == "ok" and c.get("section") not in ("processes", "telegram", "scheduler", "memory", "fallbacks"):
            continue
        if c.get("section") != last:
            lines.append("")
            lines.append(c.get("title") or c.get("section"))
            last = c.get("section")
        mark = {"ok": "OK", "warn": "!", "fail": "X"}.get(c.get("status"), "?")
        lines.append(f"  {mark} {c.get('message')}" + (f" -> {c['fix']}" if c.get("fix") else ""))
    if rep.get("repairs_available"):
        lines.append("")
        lines.append(f"{rep['repairs_available']} safe repair(s) available. Run them in the terminal: "
                     "./start.sh > Health & repair > Repair.")
    return _cut("\n".join(lines))


def _health(arg=""):
    env = dict(os.environ, NIMLAB_COLOR="0", NO_COLOR="1")
    try:
        r = subprocess.run([sys.executable, "-m", "nimlab", *health_args(arg)], cwd=PROJECT, env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=240)
        return health_text(r.stdout or "")
    except subprocess.TimeoutExpired:
        return "Health check timed out after 240 s."
    except Exception as e:  # noqa: BLE001
        return f"Health check could not run: {type(e).__name__}: {e}"


def _status():
    return run_cli(["service", "status"], 60) + "\n\n" + run_cli(["serve", "tunnel", "status"], 30)


def jobs_text():
    from . import jobscli, schedule as S, scheduler as SC
    jobscli._tz()
    jobs = SC.load_jobs()
    lines = [f"Jobs ({len(jobs)}), times in {S.timezone_name()}:"]
    for n in sorted(jobs, key=lambda n: (n != SC.HEARTBEAT, n)):
        j = jobs[n]
        st = j.get("state") or {}
        state = "on" if j.get("enabled") else ("BROKEN" if st.get("state") == "BROKEN" else "off")
        nxt = S.fmt(st.get("next_run")) if st.get("next_run") else "-"
        lines.append(f"[{state}] {n}: {S.describe(j.get('schedule', ''))}; next {nxt}; last "
                     f"{st.get('last_status') or '-'}" + (f" (bug {st['last_bug']})" if st.get("last_bug") and
                                                          st.get("last_status") != "SUCCEEDED" else ""))
        if j.get("action_type") == "quill_task" and isinstance(j.get("action"), dict):
            lines.append("    tools: " + (", ".join(j["action"].get("tools") or []) or "any"))
    lines.append(SC.status_line())
    return _cut("\n".join(lines))


def jobs_sub(conn, uid, args):
    """/jobs tools  and  /jobs freetime tool_a,tool_b (owner): v3.8.3."""
    from . import scheduler as SC
    parts = args.split(None, 1)
    sub = parts[0].lower()
    if not conn.is_owner(uid):
        return "Only the owner can do that."
    if sub == "tools":
        tools = SC.live_mcp_tools()
        return _cut(f"MCP tools on the server now ({len(tools)}):\n" +
                    "\n".join(f"{i}) {t.get('name')}" for i, t in enumerate(tools, 1)) +
                    "\n\nMake a Free time job: /jobs freetime name_a,name_b")
    if sub in ("freetime", "free-time"):
        names = SC._split_tools(parts[1] if len(parts) > 1 else "")
        if not names:
            return "Usage: /jobs freetime tool_a,tool_b   (list them with /jobs tools)"
        live = {t.get("name") for t in SC.live_mcp_tools()}
        unknown = [n for n in names if n not in live]
        if unknown:
            return "Not on the MCP server now: " + ", ".join(unknown) + ". See /jobs tools."
        j = SC.create_job(SC.free_time_template(names), who=f"telegram:{uid}", source="telegram")
        hint = SC.not_running_hint() if j.get("enabled") else ""
        return (f"Created {j['name']}: every hour Quill picks one of {', '.join(names)}, plays with it and "
                f"reports here." + (f"\n{hint}" if hint else ""))
    return "Usage: /jobs, /jobs tools, /jobs freetime tool_a,tool_b"


def heartbeat_text():
    from . import heartbeat as HB, jobscli
    jobscli._tz()
    return _cut("\n".join(HB.status_lines()))


def handle(conn, chat_id, uid, cmd, text):
    if cmd in ("/start", "/help"):
        conn.send(chat_id, help_text(owner=conn.is_owner(uid)))
        return True
    if cmd == "/new":
        conn.history.pop(chat_id, None)
        conn.send(chat_id, "Cleared this chat's history (long-term memory is kept).")
        return True
    if cmd not in COMMANDS and cmd not in UI_COMMANDS:
        return False
    if cmd not in OPEN and not conn.is_owner(uid):
        conn.send(chat_id, "That command is for the owner only.")
        return True
    parts = text.split(None, 1)
    args = parts[1].strip() if len(parts) > 1 else ""
    if cmd in UI_COMMANDS:                     # 3.8.1
        from . import tgui
        if cmd == "/model":
            tgui.model_command(conn, chat_id, uid, args)
        elif cmd == "/remember":
            tgui.remember_command(conn, chat_id, uid, args)
        elif cmd == "/voice":
            tgui.voice_command(conn, chat_id, uid, args)
        elif cmd == "/service":
            tgui.service_command(conn, chat_id, uid, args)
        elif cmd == "/cancel":
            tgui.cancel_command(conn, chat_id, uid)
        return True
    _desc, build, timeout = COMMANDS[cmd]
    if cmd == "/recall" and not args:
        conn.send(chat_id, "Usage: /recall <words to search for>")
        return True
    if cmd == "/jobs":
        if args.strip():
            conn.send(chat_id, _safe(lambda: jobs_sub(conn, uid, args.strip())))
        else:
            conn.send(chat_id, _safe(jobs_text))
        return True
    if cmd == "/autoplay":
        conn.send(chat_id, _safe(lambda: autoplay_command(conn, args)))
        return True
    if cmd == "/heartbeat":
        sub = args.split()[0].lower() if args else "status"
        if sub in ("", "status"):
            try:                                # 3.8.1: buttons to run one and switch suggested actions
                from . import tgui
                kb = tgui.heartbeat_keyboard(conn, uid)
            except Exception as e:  # noqa: BLE001
                conn.log(f"[telegram] heartbeat buttons: {e}")
                kb = None
            conn.send(chat_id, _safe(heartbeat_text), markup=kb)
            return True
        if sub not in ("run", "run-now"):
            conn.send(chat_id, "Usage: /heartbeat (status) or /heartbeat run")
            return True
        build = lambda a: ["heartbeat", "run-now"]  # noqa: E731
        conn.send(chat_id, "Running a heartbeat now; the report follows when it ends...")

        def hb():
            try:
                conn.send(chat_id, run_cli(build(args), timeout))
            except Exception as e:  # noqa: BLE001
                _fail(conn, chat_id, cmd, e)
        _spawn(hb)
        return True

    def work():
        try:
            out = _status() if cmd == "/status" else (_health(args) if cmd == "/health" else
                                                       run_cli(build(args), timeout))
            conn.send(chat_id, out)
        except Exception as e:  # noqa: BLE001 - never kill the poller
            _fail(conn, chat_id, cmd, e)

    if timeout > 30:
        conn.send(chat_id, f"Running {cmd}...")
    _spawn(work)
    return True


def _safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return f"(could not read it: {type(e).__name__}: {e})"


def _fail(conn, chat_id, cmd, e):
    try:
        conn.send(chat_id, f"{cmd} failed: {type(e).__name__}: {e}")
    except Exception:  # noqa: BLE001
        pass
