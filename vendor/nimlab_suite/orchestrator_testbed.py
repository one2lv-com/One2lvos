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

from nimlab import config
from nimlab.core import load_api_key, mask, sanitize_key
from nimlab.entity import Entity
from nimlab import rolemenu, roles as R, store, voiceclone


def print_header(title):
    os.system("clear" if os.name != "nt" else "cls")
    print("=" * 70)
    print("       NVIDIA NIM MULTI-MODEL COGNITIVE ORCHESTRATOR TESTBED")
    print("=" * 70)
    print(title)
    print("-" * 70)


def save_cluster(orch):
    """Persist config_cluster.json without any secrets in it."""
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    for section in ("roles", "voice_settings", "mcp_settings", "memory_settings", "guard_settings",
                    "routing_settings"):
        if section in orch.cluster:
            cfg[section] = orch.cluster[section]
    cfg.get("mcp_settings", {}).pop("api_key", None)
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
            print("  Other keys kept as they are: " + ", ".join(f"{k}={R.describe(orch.roles[k])}" for k in extra))
        key = rolemenu.pick_role(input, print, "Role # to change")
        if not key:
            return
        # choose_model() asks picker.choose_list for Verified (N) / All discovered (M)
        rolemenu.configure_role(orch, key, input, print, save_fn=lambda: save_cluster(orch))
        input("\nPress Enter to continue...")


def test_role_menu(orch):
    print_header("TEST A ROLE (small fixed probe)")
    rolemenu.test_role_menu(orch, input, print)
    input("\nPress Enter to return...")


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
  /roles  /tools  /clear  /exit"""

MEDIA_COMMANDS = {"/image": ("vision", "image"), "/ocr": ("ocr", "image"), "/chart": ("chart_parser", "image"),
                  "/video": ("video", "video"), "/listen": ("asr", "audio"), "/audio": ("omni_audio", "audio")}


def _show_files(files):
    for f in files or []:
        print(f"  saved: {f}")


def _media_arg(rest):
    parts = rest.split(" ", 1)
    ref = voiceclone.clean_path(parts[0]) if parts[0] else ""
    return ref, (parts[1].strip() if len(parts) > 1 else "")


def _print_turn(orch, out):
    rt = out["route"]
    if orch.cluster.get("routing_settings", {}).get("show_route", True):
        print(f"[route -> {R.label(rt['role'])} | {orch.target(rt['role'])} | {rt['reason']}]")
    if out["blocked"]:
        print(f"[BLOCKED] {out['blocked']}")
        return None
    pre = out["pre"]
    if pre is not None:
        tag = R.label(rt["role"]).upper()
        print(f"\n{tag} ({pre.latency}s):\n{pre.text if pre.ok else '[failed] ' + str(pre.error)}")
        _show_files(pre.files)
    r = out["result"]
    if r is None:
        return None
    if not r.ok:
        print(f"\n[ERROR] {r.error}")
        return None
    who = out.get("answered_by")
    trace = out.get("trace") or []
    if who:
        print(f"\nQUILL [{R.label(who)}] ({r.latency}s | {r.usage.get('completion_tokens', 'N/A')} tokens"
              f"{' | ' + str(len(trace)) + ' tool calls' if trace else ''}):\n{r.text}")
    else:
        print(f"\n{R.label(rt['role']).upper()} ({r.latency}s):\n{r.text}")
    _show_files(r.files)
    return r if who else None


def test_chat_session(orch):
    print_header("INTERACTIVE COGNITIVE CHAT SESSION")
    print(HELP)
    history = []
    if orch.mcp:
        tools = orch.refresh_tools()
        print(f"\n[MCP] {len(tools)} tools from {orch.mcp.url}" if not orch.tools_error
              else f"\n[MCP] unavailable: {orch.tools_error}")

    while True:
        try:
            user_input = input("\nYOU > ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        cmd, _, rest = user_input.partition(" ")
        rest = rest.strip()
        if cmd == "/exit":
            break
        if cmd == "/clear":
            history = []
            print("[Turn history cleared.]")
            continue
        if cmd == "/roles":
            for line in rolemenu.role_lines(orch.roles, store.verified_ids()):
                print(line)
            continue
        if cmd == "/remember" and rest:
            mem_id = orch.memory.store(rest, metadata={"source": "manual_entry"})
            print(f"[Stored as {mem_id}]" if mem_id else "[Not stored: empty, error text, or embedding failed]")
            continue
        if cmd == "/recall" and rest:
            hits, info = orch.recall(rest)
            how = f"reranked by {orch.target('reranker')}" if info.get("reranked") else \
                ("cosine order" + (f"; rerank skipped: {info['reason']}" if info.get("reason") else ""))
            print(f"\n[Vector Recall Results for '{rest}' ({how})]:")
            if not hits:
                print("  No memories above similarity threshold.")
            for rank, (sim, txt, ts, rid) in enumerate(hits, 1):
                print(f"  #{rank} [sim: {sim:.4f}] {txt} (from {ts}, {rid})")
            skipped = orch.memory.incompatible_count()
            if skipped:
                print(f"  ({skipped} records from a different embedding model were skipped)")
            continue
        if cmd == "/forget" and rest:
            print("[Deleted]" if orch.memory.delete(rest) else "[No such record]")
            continue
        if cmd == "/tools":
            if not orch.mcp:
                print("[MCP chat tools disabled or no URL set. See Settings.]")
                continue
            tools = orch.refresh_tools()
            if orch.tools_error:
                print(f"[MCP error] {orch.tools_error}")
                continue
            allowed = orch.mcp_settings.get("allowed_tools") or []
            print(f"\n[MCP] server: {orch.mcp.server_info.get('name', '?')} | protocol {orch.mcp.negotiated_protocol}")
            for t in tools:
                flag = "ALLOWED" if ("*" in allowed or t["name"] in allowed) else "blocked"
                print(f"  [{flag:^7}] {t['name']}: {t.get('description', 'No desc')[:80]}")
            if not allowed:
                print("  No tools allowlisted: add names to mcp_settings.allowed_tools in config_cluster.json.")
            continue
        if cmd == "/route" and rest:
            rt = orch.route_turn(rest)
            print(f"[{R.label(rt['role'])} | {orch.target(rt['role'])} | via {rt['via']}: {rt['reason']}]")
            continue
        if cmd == "/check" and rest:
            ok, why = orch.guard_check(rest)
            print(f"[guard: {'allowed' if ok else 'BLOCKED'}] {why}")
            continue
        if cmd == "/say" and rest:
            path, r = orch.synthesize_voice(rest)
            print(f"[TTS -> {path} in {r.latency}s]" if path else f"[TTS failed: {r.error}]")
            continue
        if cmd == "/translate" and rest:
            target = None
            m = re.match(r"^([A-Za-z][A-Za-z -]{1,24}):\s*(.+)$", rest)
            if m:
                target, rest = m.group(1).strip(), m.group(2)
            r = orch.translate(rest, target)
            print(f"\nTRANSLATION ({r.latency}s):\n{r.text}" if r.ok else f"[translate failed: {r.error}]")
            continue
        if cmd in ("/imagine", "/compose") and rest:
            role = "image_gen" if cmd == "/imagine" else "audio_gen"
            print(f"[{R.label(role)} -> {orch.target(role)} ...]")
            r = orch.run_role(role, prompt=rest)
            if r.ok:
                print(f"[{r.text or 'done'} in {r.latency}s]")
                _show_files(r.files)
            else:
                print(f"[{R.label(role)} failed: {r.error}]")
            continue

        role, media = None, None
        text = user_input
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
            path, r = orch.synthesize_voice(result.text[:250])
            print(f"[TTS -> {path} in {r.latency}s]" if path else f"[TTS failed: {r.error}]")


def _toggle(d, key):
    d[key] = not d.get(key)


def settings_menu(orch):
    while True:
        c = orch.cluster
        mcp, voice, mem = c["mcp_settings"], c["voice_settings"], c["memory_settings"]
        guard = c.setdefault("guard_settings", {})
        routing = c.setdefault("routing_settings", {})
        auth = mcp.get("auth", {})
        key_env = auth.get("key_env", "MCP_API_KEY")
        print_header("CLUSTER ORCHESTRATION SETTINGS")
        print(f" 1. Toggle MCP Integration      : {mcp.get('enabled')}")
        print(f" 2. Set MCP Server URL          : {mcp.get('url')}")
        print(f" 3. MCP Auth Style              : {auth.get('style')} (header {auth.get('header_name')}, "
              f"key from ${key_env}: {mask(sanitize_key(os.environ.get(key_env, '')))})")
        print(f" 4. MCP Allowed Tools           : {mcp.get('allowed_tools') or '[none]'}")
        print(f" 5. Confirm Each Tool Call      : {mcp.get('confirm_tool_calls')}")
        print(f" 6. Max Tool Steps per Turn     : {mcp.get('max_tool_steps')}")
        print(f" 7. Toggle Auto Voice TTS       : {voice.get('auto_tts')}")
        print(f" 8. Set Voice Profile Name      : {voice.get('voice_name')}")
        print(f" 9. Memory Recall Top-K         : {mem.get('recall_top_k')}")
        print(f"10. Memory Similarity Threshold : {mem.get('similarity_threshold')}")
        print(f"11. Rerank Candidate Pool       : {mem.get('rerank_candidates', 10)}"
              f" (reranker: {orch.target('reranker')})")
        print(f"12. Guard Check User Input      : {guard.get('check_input', False)}")
        print(f"13. Guard Check Replies         : {guard.get('check_output', False)}"
              f" (guard: {orch.target('guard_translate')})")
        print(f"14. Default Translate Target    : {guard.get('translate_target', 'English')}")
        print(f"15. Use Intent Router Model     : {routing.get('use_intent_router', True)}"
              f" (router: {orch.target('intent_router')})")
        print(f"16. Show Route of Each Turn     : {routing.get('show_route', True)}")
        print("Role tools (MCP backends) use the URL in 2 even when 1 is off; the chat allowlist is for 1.")
        print(" 0. Return")
        choice = input("\nSelect setting: ").strip()
        if choice == "1":
            _toggle(mcp, "enabled")
        elif choice == "2":
            u = input("New MCP URL: ").strip()
            if u:
                mcp["url"] = u
        elif choice == "3":
            s = input("Auth style [x-api-key / bearer / header / none]: ").strip().lower()
            if s in ("x-api-key", "bearer", "header", "none"):
                auth["style"] = s
                if s == "header":
                    auth["header_name"] = input("Header name: ").strip() or "X-API-Key"
                elif s == "x-api-key":
                    auth["header_name"] = "X-API-Key"
                mcp["auth"] = auth
            print(f"The key itself is never stored in config. Export it: export {key_env}=...")
            time.sleep(1.5)
        elif choice == "4":
            raw = input("Comma-separated tool names ('*' = all advertised, blank = none): ").strip()
            mcp["allowed_tools"] = [t.strip() for t in raw.split(",") if t.strip()]
        elif choice == "5":
            _toggle(mcp, "confirm_tool_calls")
        elif choice == "6":
            try:
                mcp["max_tool_steps"] = max(0, min(20, int(input("Max steps [0-20]: "))))
            except ValueError:
                pass
        elif choice == "7":
            _toggle(voice, "auto_tts")
        elif choice == "8":
            vn = input("Voice Profile [Magpie-Multilingual.EN-US.Aria]: ").strip()
            if vn:
                voice["voice_name"] = vn
        elif choice == "9":
            try:
                mem["recall_top_k"] = max(1, min(10, int(input("Top-K [1-10]: "))))
            except ValueError:
                pass
        elif choice == "10":
            try:
                mem["similarity_threshold"] = max(0.0, min(1.0, float(input("Threshold [0.1-0.9]: "))))
            except ValueError:
                pass
        elif choice == "11":
            try:
                mem["rerank_candidates"] = max(1, min(50, int(input("Candidates to rerank [1-50]: "))))
            except ValueError:
                pass
        elif choice == "12":
            _toggle(guard, "check_input")
        elif choice == "13":
            _toggle(guard, "check_output")
        elif choice == "14":
            t = input("Target language [English]: ").strip()
            if t:
                guard["translate_target"] = t
        elif choice == "15":
            _toggle(routing, "use_intent_router")
        elif choice == "16":
            _toggle(routing, "show_route")
        elif choice == "0":
            save_cluster(orch)
            return
        save_cluster(orch)


def main():
    key = load_api_key()
    if not key:
        key = sanitize_key(getpass("Paste NVIDIA API key: "))
        if not key:
            sys.exit("API key required.")
        os.environ["NVIDIA_API_KEY"] = key  # this process only

    orch = Entity()
    while True:
        print_header("MAIN MENU")
        print("Active Role Allocation (16 categories):")
        for line in rolemenu.role_lines(orch.roles, store.verified_ids(), numbered=False):
            print(line)
        print(f"\nMCP Enabled: {orch.mcp_settings.get('enabled')} | Vector Records: {len(orch.memory.memories)}")
        print("-" * 70)
        print("  1. Enter Interactive Multimodal Chat Session")
        print("  2. Hot-Swap Cluster Roles (model endpoint or MCP tool)")
        print("  3. View Role System Prompts")
        print("  4. View Active soul.md Persona")
        print("  5. Cluster & MCP Settings")
        print("  6. Test a Role (fixed probe: status + latency)")
        print("  7. Voice Clone Reference Clip (TTS role)")
        print("  0. Exit")
        c = input("\nSelection: ").strip()
        if c == "1":
            test_chat_session(orch)
        elif c == "2":
            swap_models_menu(orch)
        elif c == "3":
            print_header("ROLE SYSTEM PROMPTS")
            for rk, p in orch.prompts.items():
                if p:
                    print(f"[{R.label(rk).upper()}]:\n{p}\n")
            input("Press Enter to return...")
        elif c == "4":
            print_header("SOUL SPECIFICATION (soul.md)")
            print(orch.soul)
            input("\nPress Enter to return...")
        elif c == "5":
            settings_menu(orch)
        elif c == "6":
            test_role_menu(orch)
        elif c == "7":
            print_header("VOICE CLONE (TTS role)")
            rolemenu.attach_voice_clone(orch, input, print, save_fn=lambda: save_cluster(orch))
            input("\nPress Enter to return...")
        elif c == "0":
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited.")
        sys.exit(0)
