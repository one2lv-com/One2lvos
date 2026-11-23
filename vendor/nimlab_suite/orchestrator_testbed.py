#!/usr/bin/env python3
"""Interactive Multi-Model Orchestration & Parameter Testbed.

Runs a temporary persona (soul.md) on top of a configurable set of role
models, with vector memory and hardened MCP tool use. All networking,
memory and MCP logic lives in the shared nimlab package; this file is the
interactive front end only. Zero external package dependencies.
"""

import os
import re
import sys
import time
from getpass import getpass

from nimlab import selfadmin as SA
from nimlab import config
from nimlab.core import load_api_key, sanitize_key
from nimlab.entity import Entity
from nimlab import attach, colors as C, ltm, mcpkey, mcpmenu, memmenu, rolemenu, roles as R, servemenu, store, unified, voicecall, voiceclone


TITLE = "NVIDIA NIM MULTI-MODEL COGNITIVE ORCHESTRATOR TESTBED"
SHORT_TITLE = "NIM ORCHESTRATOR TESTBED"


def print_header(title):
    os.system("clear" if os.name != "nt" else "cls")
    w = C.screen_width()
    name = TITLE if w >= len(TITLE) + 4 else SHORT_TITLE
    if C.enabled():
        for line in C.box([C.gradient(name)], width=w):
            print(line)
        print(C.header(title))
        print(C.rule(w))
        return
    print("=" * w)
    print(name.center(w).rstrip())
    print("=" * w)
    print(title)
    print("-" * w)


def say(text, tone=None):
    """Print a status line, coloured by its tone on a terminal."""
    print(C.note(text, tone))


def pause(text="\nPress Enter to continue..."):
    input(C.prompt(text, "dim"))


def save_cluster(orch):
    """Persist config_cluster.json without any secrets in it. 3.7.1: only
    the sections this session changed are written (compared with what was
    loaded), so a section another process changed meanwhile (setup,
    `memory set`, the launcher's Memory menu) is not overwritten with this
    session's stale copy."""
    import copy
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    loaded = getattr(orch, "_loaded_sections", None)
    for section in ("roles", "voice_settings", "mcp_settings", "memory_settings", "guard_settings",
                    "routing_settings", "ui_settings"):
        if section not in orch.cluster:
            continue
        if isinstance(loaded, dict) and loaded.get(section) == orch.cluster[section]:
            continue
        cfg[section] = orch.cluster[section]
    cfg.get("mcp_settings", {}).pop("api_key", None)
    if isinstance(cfg.get("memory_settings", {}).get("long_term"), dict):
        cfg["memory_settings"]["long_term"] = ltm.strip_secrets(cfg["memory_settings"]["long_term"])
    config.save_json(config.CLUSTER_CONFIG, cfg)
    orch.reload()


def swap_models_menu(orch):
    """Hot-swap: pick one of the 16 roles, then a model endpoint (suited
    models first, via picker.choose_list) or an MCP tool, or unset it."""
    while True:
        print_header("HOT-SWAP ROLES (16 categories)")
        verified = store.verified_ids()
        for line in rolemenu.role_lines(orch.roles, verified):
            print(line)
        extra = [k for k in orch.roles if k not in R.BY_KEY]
        if extra:
            print(C.dim("  Other keys kept as they are: ") +
                  ", ".join(f"{C.role(k)}={C.model(R.describe(orch.roles[k]))}" for k in extra))
        print(C.entry("F", "Fallback models", "when a model is busy or down", pad=20))
        key = rolemenu.pick_role(C.cinput, print, "Role # to change, or F", extra={"f": "FALLBACKS"})
        if not key:
            return
        if key == "FALLBACKS":
            rolemenu.fallback_menu(orch, C.cinput, print, save_fn=lambda: save_cluster(orch), verified=verified)
            continue
        # choose_model() asks picker.choose_list for Verified (N) / All discovered (M)
        rolemenu.configure_role(orch, key, C.cinput, print, save_fn=lambda: save_cluster(orch))
        pause()


def test_role_menu(orch):
    print_header("TEST A ROLE (small fixed probe)")
    rolemenu.test_role_menu(orch, C.cinput, print)
    pause("\nPress Enter to return...")


HELP = """Plain text is routed by the Intent Router role (or rules when it is unset).
Attach media by typing a file path or URL in the message (image, video, audio).
Commands:
  /image <path> [prompt]   -> Vision (VLM)          /ocr <path>          -> Document OCR
  /chart <path> [question] -> Chart & Plot Parser   /video <path|url> [q] -> Video model
  /listen <audio>          -> ASR (speech to text)  /audio <file> [q]    -> Omni audio (music/ambient)
  /deep <prompt>           -> Reasoning model       /code <prompt>       -> Coding & tool-calling
  /say <text>              -> TTS to output/        /imagine <prompt>    -> Text-to-image to output/
  /compose <prompt>        -> Audio/music gen       /translate [lang:] <text> -> Translation
  /check <text>            -> Guardrail check       /route <text>        -> Show which role would answer
  /remember <text>  /recall <query>  /forget <id>   -> Vector memory (recall is reranked if set)
  /roles  /tools  /clear  /exit
""" + attach.ATTACH_HELP

_HELP_ROLES = {"Vision (VLM)": "vision", "Document OCR": "ocr", "Chart & Plot Parser": "chart_parser",
               "Video model": "video", "ASR (speech to text)": "asr", "Omni audio (music/ambient)": "omni_audio",
               "Reasoning model": "reasoning", "Coding & tool-calling": "coding", "TTS to output/": "tts",
               "Text-to-image to output/": "image_gen", "Audio/music gen": "audio_gen",
               "Translation": "guard_translate", "Guardrail check": "guard_translate",
               "Vector memory (recall is reranked if set)": "embedding", "Intent Router": "intent_router"}


def help_text():
    """HELP with each /command in its own colour and each role in the role's."""
    if not C.enabled():
        return HELP
    counter = iter(range(10 ** 6))
    alt = "|".join(re.escape(k) for k in sorted(_HELP_ROLES, key=len, reverse=True))

    def fix(line):
        if not line.startswith(" "):
            return C.section(line)
        line = re.sub(r"(?<![\w/])/[a-z]+", lambda m: C.paint(m.group(0), C.menu_rgb(next(counter)), "bold"), line)
        line = re.sub(r"(<[^>\x1b]+>|(?<!\x1b)\[[^\]\x1b]+\])", lambda m: C.hint(m.group(0)), line)
        line = re.sub(r"->", C.dim("->"), line)
        return re.sub(alt, lambda m: C.role(_HELP_ROLES[m.group(0)], m.group(0)), line)
    return "\n".join(fix(ln) for ln in HELP.split("\n"))


MEDIA_COMMANDS = {"/image": ("vision", "image"), "/ocr": ("ocr", "image"), "/chart": ("chart_parser", "image"),
                  "/video": ("video", "video"), "/listen": ("asr", "audio"), "/audio": ("omni_audio", "audio")}


def _show_files(files):
    for f in files or []:
        print(f"  {C.ok('saved:')} {C.path(f)}")


def _media_arg(rest):
    parts = rest.split(" ", 1)
    ref = voiceclone.clean_path(parts[0]) if parts[0] else ""
    return ref, (parts[1].strip() if len(parts) > 1 else "")


def _print_turn(orch, out):
    rt = out["route"]
    if orch.cluster.get("routing_settings", {}).get("show_route", True):
        print(route_line(rt["role"], orch.target(rt["role"]), rt["reason"]))
    if out["blocked"]:
        print(f"{C.err('[BLOCKED]')} {C.warn(out['blocked'])}")
        return None
    pre = out["pre"]
    if pre is not None:
        tag = C.role(rt["role"], R.label(rt["role"]).upper())
        body = C.paint(pre.text, C.tint(C.role_rgb(rt["role"]), 0.6)) if pre.ok else C.err("[failed] " + str(pre.error))
        print(f"\n{tag} {C.dim('(')}{C.latency(str(pre.latency) + 's')}{C.dim(')')}{C.dim(':')}\n{body}")
        _show_files(pre.files)
    r = out["result"]
    if r is None:
        return None
    if not r.ok:
        print(f"\n{C.err('[ERROR]')} {C.paint(r.error, 'err')}")
        return None
    who = out.get("answered_by")
    trace = out.get("trace") or []
    if who:
        name = (unified.soul_name(orch.soul) or 'Quill').upper()
        stats = (f"{C.dim('(')}{C.latency(str(r.latency) + 's')}{C.dim(' | ')}"
                 f"{C.paint(str(r.usage.get('completion_tokens', 'N/A')), 'number')}{C.dim(' tokens')}"
                 f"{C.dim(' | ') + C.paint(str(len(trace)), 'number') + C.dim(' tool calls') if trace else ''}"
                 f"{C.dim(')')}")
        print(f"\n{C.entity(name)} {C.dim('[')}{C.role(who, R.label(who))}{C.dim(']')} {stats}{C.dim(':')}"
              f"\n{C.reply(r.text)}")
    else:
        print(f"\n{C.role(rt['role'], R.label(rt['role']).upper())} {C.dim('(')}{C.latency(str(r.latency) + 's')}"
              f"{C.dim(')')}{C.dim(':')}\n{C.paint(r.text, C.tint(C.role_rgb(rt['role']), 0.6))}")
    _show_files(r.files)
    return r if who else None


def route_line(role, target, reason, via=None, prefix="route -> "):
    """'[route -> <role> | <model> | <reason>]', role in its colour, the rest dim."""
    if not C.enabled():
        mid = f"via {via}: {reason}" if via else reason
        return f"[{prefix}{R.label(role)} | {target} | {mid}]"
    sep = C.dim(" | ")
    mid = (C.dim(f"via {via}: ") if via else "") + C.hint(reason)
    return (C.dim("[" + prefix) + C.role(role, R.label(role)) + sep + C.model(target) + sep + mid + C.dim("]"))


def test_chat_session(orch):
    print_header("INTERACTIVE COGNITIVE CHAT SESSION")
    print(help_text())
    history = []
    pending = attach.Pending()
    name = (unified.soul_name(orch.soul) or "Quill").upper()
    if orch.mcp:
        tools = orch.refresh_tools()
        say("\n" + orch.mcp_startup_line(tools) if not orch.tools_error
            else f"\n[MCP] unavailable: {orch.tools_error}")
    if orch.memory is not None:
        say(orch.memory_startup_line())
    try:
        orch.prompt_checks(log=lambda m: say(m, "warn") if "warning" in m else say(m))
    except Exception as e:  # noqa: BLE001 - a lint never stops the chat
        say(f"[prompts] check skipped: {e}")

    while True:
        try:
            user_input = input(C.prompt("\nYOU > ", "you", "bold", typed="you_text")).strip()
        except EOFError:
            break
        finally:
            C.done_input()
        if not user_input:
            continue
        SA.set_local_admin()  # the person at this terminal owns the lab; one request per turn
        cmd, _, rest = user_input.partition(" ")
        rest = rest.strip()
        if cmd == "/exit":
            break
        if cmd == "/clear":
            history = []
            say("[Turn history cleared.]")
            continue
        if cmd == "/attach":
            attach.attach_command(pending, rest)
            continue
        if cmd == "/attached":
            print(C.hl("\n".join(pending.lines())) or C.warn("[nothing attached]"))
            continue
        if cmd == "/detach":
            pending.take()
            say("[attachments cleared]")
            continue
        if cmd == "/call":
            voicecall.run_call(orch)
            continue
        if cmd == "/roles":
            for line in rolemenu.role_lines(orch.roles, store.verified_ids()):
                print(line)
            continue
        if cmd == "/remember" and rest:
            mem_id = orch.memory.store(rest, metadata={"source": "manual_entry"})
            say(f"[Stored as {mem_id}]" if mem_id else "[Not stored: empty, error text, or embedding failed]")
            continue
        if cmd == "/recall" and rest:
            hits, info = orch.recall(rest)
            how = f"reranked by {orch.target('reranker')}" if info.get("reranked") else \
                ("cosine order" + (f"; rerank skipped: {info['reason']}" if info.get("reason") else ""))
            print(C.section(f"\n[Vector Recall Results for '{rest}'") + C.dim(f" ({how})") + C.section("]:"))
            if not hits:
                print(C.warn("  No memories above similarity threshold."))
            for rank, (sim, txt, ts, rid) in enumerate(hits, 1):
                print(f"  {C.paint('#' + str(rank), C.menu_rgb(rank), 'bold')} {C.dim('[sim: ')}"
                      f"{C.ok(f'{sim:.4f}') if sim >= 0.8 else C.value(f'{sim:.4f}')}{C.dim(']')} {txt} "
                      f"{C.dim(f'(from {ts}, {rid})')}")
            skipped = orch.memory.incompatible_count()
            if skipped:
                print(C.warn(f"  ({skipped} records from a different embedding model were skipped)"))
            continue
        if cmd == "/forget" and rest:
            say("[Deleted]" if orch.memory.delete(rest) else "[No such record]")
            continue
        if cmd == "/tools":
            if not orch.mcp:
                say("[MCP chat tools disabled or no URL set. See Settings.]", "warn")
                continue
            tools = orch.refresh_tools()
            if orch.tools_error:
                say(f"[MCP error] {orch.tools_error}", "err")
                continue
            pol = orch.policy()
            print(C.section("\n[MCP]") + C.dim(" server: ") + C.value(orch.mcp.server_info.get('name', '?')) +
                  C.dim(" | protocol ") + C.info(str(orch.mcp.negotiated_protocol)))
            print(C.dim(orch.mcp_startup_line(tools)))
            for i, t in enumerate(tools):
                why = pol.why_blocked(t)
                yes = why is None
                flag = f"{'OK' if yes else 'left out':^8}"
                print(f"  [{C.ok(flag) if yes else C.dim(flag)}] {C.paint(t['name'], C.menu_rgb(i), 'bold')}"
                      f"{C.dim(':')} {C.hint((t.get('description') or 'No desc')[:80] if yes else why)}")
            if not pol.exposure(tools)["allowed"]:
                say("  No tools available: the endpoint lists none, or the local allowed_tools / blocked_tools "
                    "overrides leave them all out (Settings > MCP > 9). Tool access is set in the MCP server's "
                    "admin console.", "warn")
            continue
        if cmd == "/route" and rest:
            rt = orch.route_turn(rest)
            print(route_line(rt["role"], orch.target(rt["role"]), rt["reason"], via=rt["via"], prefix=""))
            continue
        if cmd == "/check" and rest:
            ok, why = orch.guard_check(rest)
            print(f"[guard: {C.ok('allowed') if ok else C.err('BLOCKED')}] {C.hint(why) if why else why}")
            continue
        if cmd == "/say" and rest:
            path, r = orch.synthesize_voice(rest)
            say(f"[TTS -> {path} in {r.latency}s]" if path else f"[TTS failed: {r.error}]")
            continue
        if cmd == "/translate" and rest:
            target = None
            m = re.match(r"^([A-Za-z][A-Za-z -]{1,24}):\s*(.+)$", rest)
            if m:
                target, rest = m.group(1).strip(), m.group(2)
            r = orch.translate(rest, target)
            if r.ok:
                print(f"\n{C.role('guard_translate', 'TRANSLATION')} {C.dim('(')}{C.latency(str(r.latency) + 's')}"
                      f"{C.dim(')')}{C.dim(':')}\n{C.reply(r.text)}")
            else:
                say(f"[translate failed: {r.error}]")
            continue
        if cmd in ("/imagine", "/compose") and rest:
            role = "image_gen" if cmd == "/imagine" else "audio_gen"
            print(f"{C.dim('[')}{C.role(role, R.label(role))}{C.dim(' -> ')}{C.model(orch.target(role))}{C.dim(' ...]')}")
            r = orch.run_role(role, prompt=rest)
            if r.ok:
                say(f"[{r.text or 'done'} in {r.latency}s]", "ok")
                _show_files(r.files)
            else:
                say(f"[{R.label(role)} failed: {r.error}]", "err")
            continue

        role, media = None, None
        text = user_input
        if pending.parts or (cmd not in MEDIA_COMMANDS and not cmd.startswith("/") and attach.has_files(user_input)):
            res = attach.run_with_files(orch, user_input, pending.take(), history, name=name)
            if res.get("ok") and orch.cluster.get("voice_settings", {}).get("auto_tts") and orch.is_set("tts"):
                path, r = orch.synthesize_voice(unified.speakable(res["reply"], 250))
                say(f"[TTS -> {path} in {r.latency}s]" if path else f"[TTS failed: {r.error}]")
            continue
        if cmd in MEDIA_COMMANDS and rest:
            role, kind = MEDIA_COMMANDS[cmd]
            ref, question = _media_arg(rest)
            media, text = [(kind, ref)], question
        elif cmd == "/deep" and rest:
            role, text = "reasoning", rest
        elif cmd == "/code" and rest:
            role, text = "coding", rest
        out = orch.turn(text, history, role=role, media=media)
        result = _print_turn(orch, out)
        if result is not None and orch.cluster.get("voice_settings", {}).get("auto_tts") and orch.is_set("tts"):
            path, r = orch.synthesize_voice(unified.speakable(result.text, 250))
            say(f"[TTS -> {path} in {r.latency}s]" if path else
                f"[TTS failed: {r.error}. The reply above stays as text.]")


def _toggle(d, key):
    d[key] = not d.get(key)


def _ask_number(prompt, lo, hi, cast=int):
    try:
        return max(lo, min(hi, cast(C.cinput(prompt))))
    except ValueError:
        return None


def _set_number(d, key, prompt, lo, hi, cast=int):
    v = _ask_number(prompt, lo, hi, cast)
    if v is not None:
        d[key] = v


def _set_text(d, key, prompt):
    v = C.cinput(prompt).strip()
    if v:
        d[key] = v


def _onoff(v):
    return C.onoff(v, "on", "off")


def _via(role_key, short, orch):
    return C.dim("  ") + C.role(role_key, short, bold_=False) + C.dim(": ") + C.model(orch.target(role_key))


def _submenu(orch, title, rows_fn, hint=None):
    """One settings group: numbered rows of (label, value, action), 0 = back.
    Every change is saved at once."""
    while True:
        print_header(title)
        rows = rows_fn()
        for n, (name, val, _act) in enumerate(rows, 1):
            print(C.clip(C.entry(n, f"{name:<19}") + C.dim(": ") + val, C.screen_width()))
        if hint:
            print(C.hint("  " + hint))
        print(C.entry(0, "Back"))
        choice = C.read("\nSelect: ").strip()
        if choice in ("0", "", "q"):
            return
        if choice.isdigit() and 1 <= int(choice) <= len(rows):
            rows[int(choice) - 1][2]()
            save_cluster(orch)


def mcp_settings_menu(orch):
    def rows():
        mcp = orch.cluster["mcp_settings"]
        key_text, _src = mcpkey.source_text(mcp.get("auth", {}))
        tools = [t for t in (mcp.get("allowed_tools") or []) if t != "*"]
        blocked = mcp.get("blocked_tools") or []

        def server():
            mcpmenu.run_menu(mcp, C.cinput, print, save_fn=lambda: save_cluster(orch), header_fn=print_header)
            orch._build_mcp()
        return [
            ("Server, key, auth", (C.url(mcp["url"]) if mcp.get("url") else C.warn("URL not set")) +
             C.dim("  key ") + C.key(key_text), server),
            ("Tools in chat", _onoff(mcp.get("enabled")), lambda: _toggle(mcp, "enabled")),
            ("Only these tools", C.value(", ".join(tools)) if tools else C.ok("all the server exposes"),
             lambda: mcp.__setitem__("allowed_tools", [t.strip() for t in C.cinput(
                 "Comma-separated tool names to keep only those (blank or '*' = every exposed tool): ").split(",")
                 if t.strip() and t.strip() != "*"])),
            ("Blocked tools", C.value(", ".join(blocked)) if blocked else C.dim("none"),
             lambda: mcp.__setitem__("blocked_tools", [t.strip() for t in C.cinput(
                 "Comma-separated tool names never to offer (blank = none): ").split(",") if t.strip()])),
            ("Confirm each call", _onoff(mcp.get("confirm_tool_calls")), lambda: _toggle(mcp, "confirm_tool_calls")),
            ("Max steps per turn", C.value(str(mcp.get("max_tool_steps"))),
             lambda: _set_number(mcp, "max_tool_steps", "Max steps [0-20]: ", 0, 20)),
        ]
    _submenu(orch, "SETTINGS: MCP SERVER & TOOLS", rows,
             hint="Tool access is set in the MCP server's admin console; the two tool lists here are optional "
                  "local overrides. Role tools (MCP backends) use the server in 1 even when tools in chat are off.")


def voice_settings_menu(orch):
    def rows():
        voice = orch.cluster["voice_settings"]
        return [
            ("Speak replies (TTS)", _onoff(voice.get("auto_tts")), lambda: _toggle(voice, "auto_tts")),
            ("Voice profile", C.role("tts", str(voice.get("voice_name")), bold_=False),
             lambda: _set_text(voice, "voice_name", "Voice Profile [Magpie-Multilingual.EN-US.Aria]: ")),
        ]
    _submenu(orch, "SETTINGS: VOICE", rows, hint="Voice clone clip: main menu 5.")


def guard_settings_menu(orch):
    def rows():
        guard = orch.cluster.setdefault("guard_settings", {})
        return [
            ("Check user input", _onoff(guard.get("check_input", False)), lambda: _toggle(guard, "check_input")),
            ("Check replies", _onoff(guard.get("check_output", False)) + _via("guard_translate", "guard", orch),
             lambda: _toggle(guard, "check_output")),
            ("Translate target", C.value(str(guard.get("translate_target", "English"))),
             lambda: _set_text(guard, "translate_target", "Target language [English]: ")),
        ]
    _submenu(orch, "SETTINGS: GUARD & TRANSLATE", rows)


def routing_settings_menu(orch):
    def rows():
        routing = orch.cluster.setdefault("routing_settings", {})
        return [
            ("Intent router model", _onoff(routing.get("use_intent_router", True)) +
             _via("intent_router", "router", orch), lambda: _toggle(routing, "use_intent_router")),
            ("Show each route", _onoff(routing.get("show_route", True)), lambda: _toggle(routing, "show_route")),
        ]
    _submenu(orch, "SETTINGS: ROUTING", rows)


def settings_menu(orch):
    """Testbed settings, one group per line; each opens its own short menu."""
    while True:
        c = orch.cluster
        mcp, voice, mem = c["mcp_settings"], c["voice_settings"], c["memory_settings"]
        guard = c.setdefault("guard_settings", {})
        routing = c.setdefault("routing_settings", {})
        print_header("SETTINGS")
        rows = [
            ("MCP server & tools", C.dim("tools ") + _onoff(mcp.get("enabled")) + C.dim(", ") +
             (C.url(mcp["url"]) if mcp.get("url") else C.warn("URL not set"))),
            ("Voice", C.dim("speak ") + _onoff(voice.get("auto_tts")) + C.dim(", ") +
             C.role("tts", str(voice.get("voice_name") or "-").split(".")[-1], bold_=False)),
            ("Memory", C.value(memmenu.short_status(mem)) + C.dim(f", top-k {mem.get('recall_top_k', 3)}")),
            ("Guard & translate", C.dim("in ") + _onoff(guard.get("check_input", False)) + C.dim(", out ") +
             _onoff(guard.get("check_output", False)) + C.dim(", ") +
             C.value(str(guard.get("translate_target", "English")))),
            ("Routing", C.dim("router ") + _onoff(routing.get("use_intent_router", True)) + C.dim(", show ") +
             _onoff(routing.get("show_route", True))),
            ("Terminal colours", C.value(_color_setting(c)) + C.dim("  (auto / on / off)")),
        ]
        for n, (name, val) in enumerate(rows, 1):
            print(C.clip(C.entry(n, f"{name:<18}") + C.dim(": ") + val, C.screen_width()))
        print(C.entry(0, "Back"))
        choice = C.read("\nSelect: ").strip().lower()
        if choice == "1":
            mcp_settings_menu(orch)
        elif choice == "2":
            voice_settings_menu(orch)
        elif choice == "3":
            orch.refresh_memory_settings()   # 3.7.1: never edit a stale copy
            memmenu.run_menu(c, C.cinput, print, save_fn=lambda: save_cluster(orch), header_fn=print_header,
                             memory=getattr(orch, "memory", None))
        elif choice == "4":
            guard_settings_menu(orch)
        elif choice == "5":
            routing_settings_menu(orch)
        elif choice in ("6", "c"):
            nxt = {"auto": "on", "on": "off", "off": "auto"}[_color_setting(c)]
            c.setdefault("ui_settings", {})["color"] = nxt
            C.reload_config()
        elif choice in ("0", "", "q"):
            save_cluster(orch)
            return
        save_cluster(orch)


def _color_setting(cluster):
    v = str((cluster.get("ui_settings") or {}).get("color", "auto")).lower()
    return v if v in ("auto", "on", "off") else "auto"


def main():
    key = load_api_key()
    if not key:
        key = sanitize_key(getpass(C.prompt("Paste NVIDIA API key: ", "warn", "bold")))
        if not key:
            sys.exit("API key required.")
        os.environ["NVIDIA_API_KEY"] = key  # this process only

    orch = Entity()
    serve_state = {}
    try:
        _main_loop(orch, serve_state)
    finally:
        if serve_state.get("server"):
            serve_state["server"].stop()


def persona_menu(orch):
    while True:
        print_header("PERSONA & PROMPTS")
        print(C.entry(1, "soul.md persona"))
        print(C.entry(2, "Role system prompts"))
        print(C.entry(0, "Back"))
        c = C.read("\nSelect: ").strip()
        if c == "1":
            print_header("SOUL SPECIFICATION (soul.md)")
            print(C.colorize(orch.soul) if C.enabled() else orch.soul)
            pause("\nPress Enter to return...")
        elif c == "2":
            print_header("ROLE SYSTEM PROMPTS")
            for rk, p in orch.prompts.items():
                if p:
                    print(f"{C.role(rk, '[' + R.label(rk).upper() + ']')}{C.dim(':')}\n"
                          f"{C.paint(p, C.tint(C.role_rgb(rk), 0.7))}\n")
            pause("Press Enter to return...")
        else:
            return


# (section, number, label, hint): the testbed's main menu, most used first
MAIN_MENU = (("Chat", ((1, "Chat session", "text, images, files, /help"),
                       (2, "Live voice call", "mic -> ASR -> TTS" if voicecall.on_termux()
                        else "via your phone (nimbridge)"))),
             ("Roles & models", ((3, "Roles", "view and hot-swap the 16"),
                                 (4, "Test a role", "status + latency"),
                                 (5, "Voice clone clip", "TTS role"),
                                 (6, "NVCF gRPC models", "IDs, language, try"))),
             ("Setup", ((7, "Settings", "MCP, voice, memory, guard"),
                        (8, "Test server", "OpenAI-compatible"),
                        (9, "Persona & prompts", "soul.md, role prompts"))))


def roles_summary(roles):
    n = sum(1 for d in R.ROLE_DEFS if R.is_set(roles.get(d.key)))
    return n, len(R.ROLE_DEFS)


def _main_loop(orch, serve_state):
    while True:
        print_header("MAIN MENU")
        try:
            n_set, n_all = roles_summary(orch.roles)
            roles_txt = C.value(f"{n_set}/{n_all} set")
        except Exception:  # noqa: BLE001 - the summary never blocks the menu
            roles_txt = C.dim("?")
        print(f"{C.label('Roles:')} {roles_txt}{C.dim(' | ')}"
              f"{C.label('MCP:')} {_onoff(orch.mcp_settings.get('enabled'))}{C.dim(' | ')}"
              f"{C.label('Memory:')} {C.value(str(orch.memory.count()))}")
        srv = serve_state.get("server")
        running = C.ok(f" [running :{srv.bound_port}]") if srv and srv.running else ""
        for title, entries in MAIN_MENU:
            print(C.section(title))
            for n, name, extra in entries:
                print(C.entry(n, name, extra) + (running if n == 8 else ""))
        print(C.entry(0, "Exit"))
        c = C.read("\nSelection: ").strip()
        if c == "1":
            test_chat_session(orch)
        elif c == "2":
            print_header("LIVE VOICE CALL TEST")
            voicecall.run_call(orch)
            pause("\nPress Enter to return...")
        elif c == "3":
            swap_models_menu(orch)
        elif c == "4":
            test_role_menu(orch)
        elif c == "5":
            print_header("VOICE CLONE (TTS role)")
            rolemenu.attach_voice_clone(orch, C.cinput, print, save_fn=lambda: save_cluster(orch))
            pause("\nPress Enter to return...")
        elif c == "6":
            from nimlab import grpcmenu
            grpcmenu.run_menu(C.read, print, orch)
        elif c == "7":
            settings_menu(orch)
        elif c == "8":
            servemenu.run_menu(orch, C.cinput, print, state=serve_state)
        elif c == "9":
            persona_menu(orch)
        elif c == "0":
            break


if __name__ == "__main__":
    C.apply_flags(sys.argv)
    C.install()
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited.")
        sys.exit(0)
