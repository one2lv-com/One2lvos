"""Interactive role menus for the testbed: hot-swap, MCP tool backends,
voice clone, test a role. input_fn/out are injectable so tests can drive
them; save_fn persists the cluster config."""

import os

from . import picker, rolemcp, roles as R, store, voiceclone

CLONE_DIRS = ("/storage/emulated/0/Download", "/storage/emulated/0/Recordings", "/storage/emulated/0/Music",
              "/storage/emulated/0/Documents", "/storage/emulated/0/Voice Recorder",
              "/storage/emulated/0/Sounds", "~/storage/downloads", "~/storage/shared/Recordings")


def _ask(input_fn, prompt):
    try:
        return (input_fn(prompt) or "").strip()
    except EOFError:
        return ""


def support_tag(key):
    d = R.BY_KEY.get(key)
    if not d or d.support == R.YES:
        return ""
    return "  {NVIDIA API: not available}" if d.support == R.NO else "  {NVIDIA API: partial}"


def role_lines(roles, verified=None, numbered=True):
    """One line per role: display name, backend, target, flags."""
    verified = set(verified or [])
    lines = []
    for i, key in enumerate(R.ROLE_KEYS, 1):
        v = roles.get(key)
        desc = R.describe(v)
        flags = []
        m = R.model_of(v)
        if m and verified and m not in verified:
            flags.append("not 200-tested")
        ct = R.clone_text(v) if key == "tts" else ""
        if ct:
            flags.append(ct)
        tail = ("  (" + "; ".join(flags) + ")") if flags else ""
        num = f"{i:>2}. " if numbered else "- "
        lines.append(f"  {num}{R.label(key):<56} {desc}{tail}{support_tag(key)}")
    return lines


def model_lists():
    verified = store.verified_ids()
    discovered = sorted(set(store.load(store.DISCOVERED)["models"]) | set(verified), key=str.lower)
    return verified, discovered


def pick_role(input_fn, out, title="Role #"):
    sel = _ask(input_fn, f"\n{title} (Enter to return): ")
    if sel.isdigit() and 1 <= int(sel) <= len(R.ROLE_KEYS):
        return R.ROLE_KEYS[int(sel) - 1]
    if sel in R.BY_KEY:
        return sel
    return None


# ---------------------------------------------------------------------------
# Model backend
# ---------------------------------------------------------------------------
def choose_model(key, input_fn=input, out=print, verified=None, discovered=None, kinds=None, infos=None):
    """Returns (model_id or None, cancelled: bool). Suited models first."""
    if verified is None or discovered is None:
        verified, discovered = model_lists()
    if kinds is None:
        kinds, infos = R.kinds_from_store()
    d = R.BY_KEY[key]
    available, scope = picker.choose_list(verified, discovered, input_fn=input_fn, out=out,
                                          title=f"Models for {d.name}:")
    suited, possible, other = R.candidates(key, available, kinds, infos)
    order = suited + possible
    out(f"\nSelect a model for [{d.name}]")
    if d.note:
        out(f"  {d.note}")
    if not available:
        out("  (empty list: run discover and the 200 sweep, launcher options D and 2)")
    n = 0
    if suited:
        out(f"  Suited ({len(suited)}):")
        for m in suited:
            n += 1
            out(f"   {n:>3}. {m}")
    else:
        out("  Suited: none in this list" + (" (NVIDIA hosts none)" if d.support == R.NO else ""))
    if possible:
        out(f"  Also possible ({len(possible)}):")
        for m in possible:
            n += 1
            out(f"   {n:>3}. {m}")
    if other:
        out(f"  Other models: {len(other)} hidden (type 'a' to show them)")
    while True:
        sel = _ask(input_fn, "\nModel # / model ID / 'a' all / '-' unset / Enter cancel: ")
        if sel.lower() == "a" and other:
            for m in other:
                n += 1
                out(f"   {n:>3}. {m}")
            order = order + other
            other = []
            continue
        break
    if not sel:
        return None, True
    if sel == "-":
        return None, False
    full = order + other
    if sel.isdigit() and 1 <= int(sel) <= len(order):
        new = order[int(sel) - 1]
    elif sel in full or (scope == picker.ALL and "/" in sel):
        new = sel
    else:
        out(f"\n'{sel}' hasn't passed the 200 test. Pick 2 (All discovered) to assign it anyway; role unchanged.")
        return None, True
    note = picker.unverified_note(new, verified)
    if note:
        out("\n" + note)
    if new not in suited:
        out(f"Note: {new} is not a typical {d.name}; it is set anyway.")
    return new, False


# ---------------------------------------------------------------------------
# MCP backend
# ---------------------------------------------------------------------------
def show_arg_map(tool, arg_map, out):
    props, required = rolemcp._props(tool)
    if not arg_map:
        out("  (no inputs mapped)")
    for inp, arg in arg_map.items():
        t = (props.get(rolemcp._arg_name(arg)) or {}).get("type", "?")
        out(f"    {inp:<16} -> {arg} ({t})")
    miss = rolemcp.unmapped_required(tool, arg_map)
    if miss:
        out(f"  Warning: required tool arguments not mapped: {', '.join(miss)}")


def edit_arg_map(key, tool, arg_map, input_fn, out):
    props, _ = rolemcp._props(tool)
    out(f"  Tool arguments: {', '.join(props) or '(none)'}")
    out("  For each role input type the tool argument name. Enter keeps it, '-' drops it.\n"
        "  Add :path, :base64 or :dataurl to force how a file is sent (e.g. image:base64).")
    new = dict(arg_map)
    for inp in rolemcp.ROLE_INPUTS.get(key, ["text"]):
        cur = new.get(inp, "")
        ans = _ask(input_fn, f"    {inp} [{cur or 'unmapped'}]: ")
        if ans == "-":
            new.pop(inp, None)
        elif ans:
            name = rolemcp._arg_name(ans)
            if props and name not in props:
                out(f"    '{name}' is not one of the tool's arguments; kept {cur or 'unmapped'}")
                continue
            new[inp] = ans
    return new


def choose_mcp_tool(entity, key, input_fn=input, out=print):
    """Returns (tool_name, arg_map) or (None, None) when cancelled or the
    server is unreachable (the role is then left as it was)."""
    tools, err = entity.list_role_tools()
    if err:
        out(f"\nMCP server unreachable: {err}\nRole setting unchanged.")
        return None, None
    if not tools:
        out("\nThe MCP server lists no tools. Role setting unchanged.")
        return None, None
    out(f"\nTools on the MCP server ({len(tools)}):")
    for i, t in enumerate(tools, 1):
        desc = " ".join(str(t.get("description") or "").split())
        out(f"  {i:>3}. {t['name']}: {desc[:70]}")
    sel = _ask(input_fn, "\nTool # or name (Enter cancel): ")
    tool = None
    if sel.isdigit() and 1 <= int(sel) <= len(tools):
        tool = tools[int(sel) - 1]
    else:
        tool = next((t for t in tools if t["name"] == sel), None)
    if tool is None:
        if sel:
            out("No such tool. Role setting unchanged.")
        return None, None
    arg_map = rolemcp.auto_arg_map(key, tool)
    out(f"\nInput mapping for {tool['name']} (auto):")
    show_arg_map(tool, arg_map, out)
    if _ask(input_fn, "Edit the mapping? [y/N]: ").lower().startswith("y"):
        arg_map = edit_arg_map(key, tool, arg_map, input_fn, out)
        out("Mapping now:")
        show_arg_map(tool, arg_map, out)
    allowed = entity.mcp_settings.get("allowed_tools") or []
    if "*" not in allowed and tool["name"] not in allowed:
        out("Note: role tools run without the chat allowlist and y/N prompt, because you picked this tool here.")
    return tool["name"], arg_map


# ---------------------------------------------------------------------------
# Voice clone
# ---------------------------------------------------------------------------
def find_audio_files(dirs=CLONE_DIRS, limit=20, extra=()):
    found = []
    for d in list(extra) + list(dirs):
        d = os.path.expanduser(d)
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            p = os.path.join(d, n)
            if n.lower().endswith(voiceclone.AUDIO_EXTS) and os.path.isfile(p):
                try:
                    found.append((os.path.getmtime(p), p))
                except OSError:
                    pass
    seen, out = set(), []
    for _, p in sorted(found, reverse=True):
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:limit]


def clone_info(entity):
    """(supported, settings_or_reason) for the current TTS role."""
    sp = entity.spec("tts")
    if sp["backend"] == R.MCP:
        if not sp.get("tool"):
            return False, "no MCP tool picked for the TTS role"
        if "reference_audio" in (sp.get("arg_map") or {}):
            return True, {"field": sp["arg_map"]["reference_audio"], "transport": "mcp",
                          "needs_transcript": False, "mcp": True}
        tool = None
        tools, err = entity.list_role_tools()
        if not err:
            tool = next((t for t in tools if t["name"] == sp["tool"]), None)
        auto = rolemcp.auto_arg_map("tts", tool) if tool else {}
        if "reference_audio" in auto:
            return True, {"field": auto["reference_audio"], "transport": "mcp", "needs_transcript": False,
                          "mcp": True, "auto_map": auto}
        return False, f"the MCP tool {sp['tool']} has no reference-audio argument"
    model = sp.get("model")
    if not model:
        return False, "the TTS role has no model"
    sup = R.clone_support(model)
    if not sup:
        return False, (f"{model} doesn't support voice cloning; a zero-shot model such as "
                       "nvidia/magpie-tts-zeroshot does")
    return True, sup


def attach_voice_clone(entity, input_fn=input, out=print, save_fn=None, search_dirs=CLONE_DIRS):
    ok, info = clone_info(entity)
    if not ok:
        out(f"\nVoice cloning isn't available: {info}.")
        return False
    roles = entity.cluster["roles"]
    sp = R.normalize(roles.get("tts"), "tts")
    cur = (sp.get("voice_clone") or {}).get("path")
    out(f"\nVoice clone reference clip (sent as {info['field']}). "
        "Best: 3-10 s of clean speech, WAV 16-bit mono, 22.05 kHz or higher.")
    if cur:
        out(f"Current: {cur}")
    files = find_audio_files(search_dirs, extra=[os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "samples")])
    for i, p in enumerate(files, 1):
        out(f"  {i:>2}. {p}")
    raw = _ask(input_fn, "File # or full path (e.g. /storage/emulated/0/Download/me.wav), '-' remove, "
                         "Enter cancel: ")
    if not raw:
        return False
    if raw == "-":
        sp.pop("voice_clone", None)
        roles["tts"] = sp
        if save_fn:
            save_fn()
        out("Voice clone removed.")
        return True
    if raw.isdigit() and 1 <= int(raw) <= len(files):
        raw = files[int(raw) - 1]
    try:
        path, data, meta = voiceclone.prepare(raw)
    except voiceclone.CloneError as e:
        out(f"Can't use that clip: {e}. Voice clone unchanged.")
        return False
    for n in meta["notes"]:
        out(f"  - {n}")
    out(f"  Clip OK: {meta['seconds']} s at {meta['rate']} Hz ({meta['bytes'] // 1024} KB as sent).")
    transcript = ""
    if info.get("needs_transcript"):
        while not transcript:
            transcript = _ask(input_fn, "This model needs the exact words spoken in the clip. Transcript: ")
            if not transcript:
                out("A transcript is required for this model (Ctrl-C to cancel).")
    elif info.get("mcp") and "reference_text" in (sp.get("arg_map") or info.get("auto_map") or {}):
        transcript = _ask(input_fn, "The tool takes a transcript of the clip (optional, Enter to skip): ")
    vc = {"path": path, "seconds": meta["seconds"]}
    if transcript:
        vc["transcript"] = transcript
    sp["voice_clone"] = vc
    if info.get("auto_map") and not sp.get("arg_map"):
        sp["arg_map"] = info["auto_map"]
    roles["tts"] = sp
    if save_fn:
        save_fn()
    out(f"Saved. TTS role: {R.describe(sp)} (cloned voice: {os.path.basename(path)})")
    return True


# ---------------------------------------------------------------------------
# Hot-swap one role
# ---------------------------------------------------------------------------
def configure_role(entity, key, input_fn=input, out=print, save_fn=None, model_args=None):
    """Change one role's backend. Returns True when the config changed."""
    roles = entity.cluster.setdefault("roles", {})
    d = R.BY_KEY[key]
    out(f"\n[{d.name}] now: {R.describe(roles.get(key))}" +
        (f"  ({R.clone_text(roles.get(key))})" if key == "tts" and R.clone_text(roles.get(key)) else ""))
    if d.support != R.YES:
        out(f"  {d.note}")
    extra = "  4. Voice clone reference clip" if key == "tts" else ""
    ans = _ask(input_fn, f"Backend: 1. Model endpoint  2. MCP tool  3. Unset{extra}  [Enter = keep]: ")
    if ans == "1":
        model, cancelled = choose_model(key, input_fn, out, **(model_args or {}))
        if cancelled:
            out("Role unchanged.")
            return False
        endpoint = None
        if model and d.support != R.YES:
            endpoint = _ask(input_fn, "Custom endpoint URL (Enter = automatic): ") or None
            if endpoint and not endpoint.startswith("https://") and not endpoint.startswith("http://"):
                out("Not a URL; using automatic routing.")
                endpoint = None
        R.set_model(roles, key, model, endpoint)
        if save_fn:
            save_fn()
        out(f"Updated {d.name} -> {R.describe(roles[key])}")
        if key == "tts" and model:
            ok, info = clone_info(entity)
            if ok:
                if _ask(input_fn, "This model can clone a voice. Attach a reference clip now? [y/N]: ").lower() \
                        .startswith("y"):
                    attach_voice_clone(entity, input_fn, out, save_fn)
            else:
                if roles[key].get("voice_clone"):
                    roles[key].pop("voice_clone", None)
                out(f"Voice cloning: not offered ({info}).")
        return True
    if ans == "2":
        tool, arg_map = choose_mcp_tool(entity, key, input_fn, out)
        if not tool:
            return False
        R.set_mcp(roles, key, tool, arg_map)
        if save_fn:
            save_fn()
        out(f"Updated {d.name} -> {R.describe(roles[key])}")
        if key == "tts" and "reference_audio" in arg_map:
            if _ask(input_fn, "The tool takes reference audio. Attach a voice clone clip now? [y/N]: ").lower() \
                    .startswith("y"):
                attach_voice_clone(entity, input_fn, out, save_fn)
        return True
    if ans == "3":
        R.set_model(roles, key, None)
        if save_fn:
            save_fn()
        out(f"{d.name} is now unset.")
        return True
    if ans == "4" and key == "tts":
        return attach_voice_clone(entity, input_fn, out, save_fn)
    return False


# ---------------------------------------------------------------------------
# Test a role
# ---------------------------------------------------------------------------
def format_test(key, res):
    status = "PASS" if res["ok"] else "FAIL"
    lines = [f"  {R.label(key)}: {status}  backend={res['backend']}  target={res['target']}",
             f"  HTTP {res.get('status') or '-'}  latency {res.get('latency', 0):.2f}s"]
    if res.get("voice_clone"):
        lines.append(f"  cloned voice: {os.path.basename(res['voice_clone'])}")
    if res["ok"]:
        lines.append(f"  {res.get('summary') or '(no text)'}")
    else:
        lines.append(f"  error: {res.get('error')}")
    return lines


def test_role_menu(entity, input_fn=input, out=print):
    for line in role_lines(entity.roles, numbered=True):
        out(line)
    key = pick_role(input_fn, out, "Role # to test")
    if not key:
        return None
    media = None
    if key == "video":
        media = voiceclone.clean_path(_ask(input_fn, "Video file path or URL for the probe: ")) or None
    elif key in ("asr", "omni_audio", "vision", "ocr", "chart_parser"):
        raw = _ask(input_fn, "File for the probe (Enter = built-in sample): ")
        media = voiceclone.clean_path(raw) if raw else None
    out(f"\nTesting {R.label(key)} ...")
    res = entity.test_role(key, media)
    for line in format_test(key, res):
        out(line)
    return res
