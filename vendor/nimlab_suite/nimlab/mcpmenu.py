"""MCP server screen: URL, API key, auth style and a connection test,
shared by the testbed settings, the launcher and `python3 -m nimlab mcp`.

The key is typed with hidden input and only ever shown masked. It is used
for this session only or saved by nimlab.mcpkey outside the project folder;
it is never written to config_cluster.json.
"""

import getpass as _getpass

from . import colors as C, config, mcpkey
from .core import mask, sanitize_key

STYLES = ("x-api-key", "bearer", "header", "none")


def _ask(input_fn, text):
    try:
        return (input_fn(text if input_fn is C.cinput else C.ask(text)) or "").strip()
    except EOFError:
        return ""
    finally:
        C.done_input()


def auth_of(settings):
    auth = settings.setdefault("auth", {})
    auth.setdefault("style", "x-api-key")
    auth.setdefault("header_name", "X-API-Key")
    auth.setdefault("key_env", mcpkey.DEFAULT_ENV)
    return auth


def saved_settings():
    """mcp_settings as saved in config_cluster.json right now, over the
    defaults. Read fresh on every call: no summary line may show a cached
    auth style (3.7.4)."""
    raw = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    try:
        merged = dict(config.load_cluster_config().get("mcp_settings") or {})
    except Exception:  # noqa: BLE001
        merged = {}
    saved = raw.get("mcp_settings") if isinstance(raw.get("mcp_settings"), dict) else {}
    out = dict(merged, **saved)
    if not isinstance(out.get("auth"), dict) and isinstance(saved.get("auth"), str):
        out["auth"] = {"style": saved["auth"]}
    return out


def saved_style(settings=None):
    """-> (style, header_name) from the saved settings. Accepts the forms
    older versions wrote: auth {style}, auth as a plain string, auth_style."""
    m = saved_settings() if settings is None else settings
    a = m.get("auth")
    if isinstance(a, dict):
        style, header = a.get("style"), a.get("header_name")
    elif isinstance(a, str):
        style, header = a, None
    else:
        style, header = None, None
    style = str(style or m.get("auth_style") or "x-api-key").strip().lower()
    if style in ("authorization", "authorization: bearer", "bearer token"):
        style = "bearer"
    return style, header or "X-API-Key"


def style_text(auth):
    s = auth.get("style") or "x-api-key"
    if s == "bearer":
        return "bearer (Authorization: Bearer <key>)"
    if s == "none":
        return "none (no key sent)"
    return f"{s} (header {auth.get('header_name') or 'X-API-Key'})"


def valid_url(url):
    u = (url or "").strip()
    return u.startswith(("http://", "https://")) and len(u) > len("https://")


def set_url(settings, url):
    """Set the URL. Returns an error text, or '' when set."""
    u = (url or "").strip()
    if not valid_url(u):
        return "The URL must start with http:// or https://"
    settings["url"] = u
    return ""


def set_style(settings, style, header_name=None):
    """Set the auth style. Returns an error text, or '' when set."""
    style = (style or "").strip().lower()
    if style in ("x-api-key", "xapikey", "x_api_key"):
        style = "x-api-key"
    if style not in STYLES:
        return f"Auth style must be one of: {', '.join(STYLES)}"
    auth = auth_of(settings)
    auth["style"] = style
    if style == "header":
        name = (header_name or "").strip()
        if not name or any(ch in name for ch in " :\r\n"):
            return "A custom header needs a name without spaces or ':' (e.g. X-MCP-Key)"
        auth["header_name"] = name
    elif style == "x-api-key":
        auth["header_name"] = "X-API-Key"
    return ""


def status_lines(settings):
    auth = auth_of(settings)
    text, src = mcpkey.source_text(auth)
    url = settings.get("url") or ""
    key_col = {"none": C.warn, "env": C.info, "saved": C.ok, "session": C.value}[src]
    return [
        f"  {C.label('Server URL  :')} {C.url(url) if url else C.warn('(not set)')}",
        f"  {C.label('API key     :')} {key_col(text)}",
        f"  {C.label('Auth style  :')} {C.value(style_text(auth))}",
        f"  {C.label('Chat tools  :')} {C.onoff(settings.get('enabled'), 'on', 'off')}"
        f"{C.dim('  (role tools use the URL even when chat tools are off)')}",
    ]


def show_test(settings, out, http=None, full_list=False):
    """Connect, list the tools and print the one-line summary (3.7.3: every
    exposed tool is available unless a local override says otherwise).
    full_list=True adds one line per tool (`nimlab mcp tools`, `mcp test -v`)."""
    out(C.dim("  Testing the connection..."))
    res = mcpkey.test_connection(settings, http=http)
    for line in mcpkey.describe_test(res):
        out(C.note(line, "ok" if res["ok"] else "err"))
    if res["ok"]:
        for line in policy_lines(settings, res.get("tool_defs") or [], full_list=full_list):
            out(line)
    return res


def choose_dedicated(settings, input_fn, out, http=None):
    """Switch the MCP URL to a per-agent endpoint and test it. -> changed."""
    agent = agent_name() or "quill"
    cur = settings.get("url") or ""
    guess = cur.rstrip("/") + "-" + agent.lower() if cur and agent.lower() not in cur.lower() else cur
    out(C.dim("  Your agent's own endpoint, e.g. https://svn-dev.online/mcp-quill or https://svn-dev.online/mcp/quill. "
              "Its tools are the ones you switched on for it in the MCP server's admin console."))
    u = _ask(input_fn, f"Dedicated endpoint URL [{guess}]: ") or guess
    if not u:
        return False
    old = dict(settings)
    e = set_url(settings, u)
    if e:
        out(C.err("  " + e))
        return False
    settings["dedicated_endpoint"] = True
    out(C.ok("  URL set to ") + C.url(settings["url"]) + C.dim(" (dedicated endpoint)"))
    res = show_test(settings, out, http=http)
    if not res["ok"]:
        keep = _ask(input_fn, "The test failed. Keep this URL anyway? [y/N]: ").lower().startswith("y")
        if not keep:
            settings.clear()
            settings.update(old)
            out(C.dim("  Kept the old URL."))
            return False
    return True


def edit_allowlist(settings, input_fn, out):
    """Optional local overrides: allowed_tools, blocked_tools and
    own_memory_tool. -> changed. (3.7.3: tool access is set in the MCP
    server's admin console; these only narrow it further on this phone.)"""
    cur = ", ".join(settings.get("allowed_tools") or []) or "(empty: every tool the server exposes)"
    blk = ", ".join(settings.get("blocked_tools") or []) or "(empty)"
    out(C.dim("  Tool access is set in the MCP server's admin console: every tool the endpoint lists is "
              "available. These are optional local overrides."))
    out(C.dim(f"  allowed_tools now: {cur}"))
    out(C.dim(f"  blocked_tools now: {blk}"))
    changed = False
    v = _ask(input_fn, "Allowed tools (comma-separated = only these, * or - = every exposed tool, Enter = keep): ")
    if v:
        settings["allowed_tools"] = [] if v.strip() in ("-", "*") else [x.strip() for x in v.split(",") if x.strip()]
        changed = True
    b = _ask(input_fn, "Blocked tools (comma-separated, - = none, Enter = keep): ")
    if b:
        settings["blocked_tools"] = [] if b.strip() == "-" else [x.strip() for x in b.split(",") if x.strip()]
        changed = True
    own = _ask(input_fn, f"Own MCP memory tool [{settings.get('own_memory_tool') or 'none'}] (- = none): ")
    if own:
        settings["own_memory_tool"] = "" if own.strip() == "-" else own.strip()
        changed = True
    return changed


def agent_name():
    """agent_settings.name, else a custom memory profile, else soul.md's name."""
    from . import config, ltm, unified
    try:
        c = config.load_cluster_config()
    except Exception:  # noqa: BLE001
        c = {}
    n = ((c.get("agent_settings") or {}).get("name") or "").strip()
    if n:
        return n
    try:
        prof = ((ltm.settings_from(c.get("memory_settings", {})).get("oracle") or {}).get("profile_id") or "").upper()
    except Exception:  # noqa: BLE001
        prof = ""
    if prof and prof != "TESTBED":
        return prof
    try:
        return unified.soul_name(config.load_soul() or "") or ""
    except Exception:  # noqa: BLE001
        return ""


def check_memory_tool_schema(tool):
    """The own MCP memory tool must take an action with recall (and log) and a
    query, like charlie_mem. -> [problem] ([] when it fits)."""
    sch = (tool or {}).get("inputSchema") or {}
    props = sch.get("properties") or {}
    probs = []
    act = props.get("action") or {}
    enum = act.get("enum") or []
    if "action" not in props:
        probs.append("no 'action' argument")
    elif enum and "recall" not in enum:
        probs.append("'action' has no 'recall'")
    if "query" not in props:
        probs.append("no 'query' argument")
    return probs


def policy_lines(settings, tools, agent=None, full_list=False):
    """The one-line summary ('[MCP] N tools from URL, all available'), the
    own memory tool check and, with full_list, one line per tool."""
    from .mcp import ToolPolicy, exposure_line
    agent = agent if agent is not None else agent_name()
    pol = ToolPolicy.from_settings(settings, agent=agent)
    lines = [C.dim("  " + exposure_line(tools, pol, settings.get("url")))]
    if pol.dedicated and agent:
        lines.append(C.dim(f"  {agent}'s own endpoint: the tools are the ones switched on for it in the MCP "
                           "server's admin console."))
    if full_list:
        for t in tools:
            why = pol.why_blocked(t)
            lines.append(("  " + C.ok("available ") if why is None else "  " + C.dim("left out  ")) + C.value(t["name"])
                         + ("" if why is None else C.dim(f"  ({why})")))
    elif tools:
        lines.append(C.dim("  One line per tool: nimlab mcp tools"))
    own = pol.own
    if own:
        tool = next((t for t in tools if t.get("name") == own), None)
        if tool is None:
            lines.append(C.warn(f"  own_memory_tool {own} is not in this server's tool list yet."))
        else:
            probs = check_memory_tool_schema(tool)
            lines.append(C.warn(f"  own_memory_tool {own}: schema looks different ({'; '.join(probs)}).") if probs
                         else C.ok(f"  own_memory_tool {own}: schema has action + query (like charlie_mem)."))
    return lines


def enter_key(settings, input_fn, out, getpass_fn=None, save=None):
    """Ask for the key with hidden input; save it or keep it for this
    session. save: None asks, True saves, False = session only.
    Returns 'saved', 'session' or '' (nothing entered)."""
    auth = auth_of(settings)
    gp = getpass_fn or _getpass.getpass
    try:
        key = sanitize_key(gp("MCP API key (hidden, Enter to cancel): "))
    except EOFError:
        key = ""
    if not key:
        out(C.warn("  No key entered; nothing changed."))
        return ""
    out(f"  {C.label('Key:')} {C.key(mask(key))}")
    if save is None:
        out("  " + C.item(1, "Save it for future runs", extra=f"  ({mcpkey.secrets_path()}, private file)"))
        out("  " + C.item(2, "Use it for this session only"))
        save = _ask(input_fn, "Choice [1]: ") != "2"
    if save:
        path = mcpkey.save_key(key, auth)
        mcpkey.clear_session_key(auth)
        out(C.ok("  Saved") + C.dim(" to ") + C.path(path) + C.dim(" (permissions 600, outside the project folder)."))
        how = "saved"
    else:
        mcpkey.set_session_key(key, auth)
        out(C.ok("  Using it for this session only") + C.dim("; it is not written anywhere."))
        how = "session"
    env_name = auth.get("key_env") or mcpkey.DEFAULT_ENV
    _, src = mcpkey.resolve(auth)
    if how == "saved" and src == "env":
        out(C.warn(f"  Note: ${env_name} is set in the environment and still wins over the saved key."))
    return how


def delete_saved(settings, out):
    auth = auth_of(settings)
    if mcpkey.delete_key(auth):
        out(C.ok("  Saved MCP key deleted."))
        return True
    out(C.warn("  There was no saved MCP key."))
    return False


def choose_style(settings, input_fn, out):
    auth = auth_of(settings)
    out("  " + C.item(1, "x-api-key", extra="  (header X-API-Key: <key>)"))
    out("  " + C.item(2, "bearer", extra="     (Authorization: Bearer <key>)"))
    out("  " + C.item(3, "custom header name"))
    out("  " + C.item(4, "none", extra="       (no key sent)"))
    sel = _ask(input_fn, f"Auth style [{auth.get('style')}]: ").lower()
    pick = {"1": "x-api-key", "2": "bearer", "3": "header", "4": "none"}.get(sel, sel)
    if not pick:
        return False
    name = None
    if pick == "header":
        name = _ask(input_fn, f"Header name [{auth.get('header_name') or 'X-API-Key'}]: ") or \
            auth.get("header_name") or "X-API-Key"
    e = set_style(settings, pick, name)
    if e:
        out(C.err("  " + e))
        return False
    out(C.ok("  Auth style set to ") + C.value(style_text(auth)))
    return True


def run_menu(settings, input_fn=input, out=print, getpass_fn=None, save_fn=None, http=None, header_fn=None):
    """The MCP server screen. settings is the mcp_settings dict (changed in
    place); save_fn() persists it (the key is never part of it)."""
    auth_of(settings)
    while True:
        if header_fn:
            header_fn("MCP SERVER: URL, API KEY, AUTH")
        else:
            out("\n" + C.header("MCP SERVER: URL, API KEY, AUTH"))
            out(C.rule())
        for line in status_lines(settings):
            out(line)
        out(C.rule(50))
        _, src = mcpkey.resolve(settings["auth"])
        out("  " + C.item(1, "Set MCP server URL"))
        out("  " + C.item(2, "Set / replace MCP API key", extra="  (hidden input)"))
        out("  " + C.item(3, "Delete the saved MCP key"))
        out("  " + C.item(4, "Auth style", extra="  (x-api-key / bearer / custom header)"))
        out("  " + C.item(5, "Test the connection", extra="  (connect + list tools)"))
        out("  " + C.item(6, "Turn chat tools " + ("off" if settings.get("enabled") else "on")))
        out("  " + C.item(8, "Use a dedicated agent endpoint", extra="  (e.g. .../mcp-quill or .../mcp/quill)"))
        out("  " + C.item(9, "Local tool overrides / own memory tool", extra="  (optional; empty = all tools)"))
        if src == "session":
            out("  " + C.item(7, "Forget the session-only key"))
        out("  " + C.item(0, "Back"))
        c = _ask(input_fn, "\nSelection: ")
        changed = False
        if c == "1":
            u = _ask(input_fn, f"New MCP URL [{settings.get('url') or ''}]: ")
            if u:
                e = set_url(settings, u)
                if e:
                    out(C.err("  " + e))
                else:
                    out(C.ok("  URL set to ") + C.url(settings["url"]))
                    changed = True
        elif c == "2":
            changed = bool(enter_key(settings, input_fn, out, getpass_fn))
        elif c == "3":
            changed = delete_saved(settings, out)
        elif c == "4":
            changed = choose_style(settings, input_fn, out)
        elif c == "5":
            show_test(settings, out, http=http)
            _ask(input_fn, "\nPress Enter to continue...")
        elif c == "8":
            changed = choose_dedicated(settings, input_fn, out, http=http)
        elif c == "9":
            changed = edit_allowlist(settings, input_fn, out)
        elif c == "6":
            settings["enabled"] = not settings.get("enabled")
            out(C.ok("  Chat tools ") + C.onoff(settings["enabled"], "on", "off"))
            if save_fn:
                save_fn()
        elif c == "7" and src == "session":
            mcpkey.clear_session_key(settings["auth"])
            out(C.ok("  Session key forgotten."))
            changed = True
        elif c in ("0", "q", ""):
            if save_fn:
                save_fn()
            return
        if changed:
            if save_fn:
                save_fn()
            if settings.get("url"):
                show_test(settings, out, http=http)
            _ask(input_fn, "\nPress Enter to continue...")
