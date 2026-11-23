"""Menu and CLI glue for the OpenAI-compatible test server (nimlab.server).

Used by the testbed's main menu (Test server, server runs in the background
while the testbed is open), by `python3 -m nimlab serve ...` and by the
launcher (`./start.sh serve`, menu O).
"""

import os
import re
import sys
import time
from getpass import getpass

from . import colors as C, roles as R
from . import server as S, tunnel as TN
from .core import load_api_key, mask, sanitize_key

SETTING_HELP = ("model <name> | port <n> | lan on|off | log on|off | "
                "console on|off | cors <origin|*> | prefix <text> | chunk <words per stream chunk> | tools deny|allow | "
                "system append|ignore | trace off|field|content | media url|data | media-auth link|key | "
                "media-hours <n> | attach-chars <n> | call on|off | memory.<key> <value> (see ./start.sh memory)")


def _on(v):
    v = str(v).strip().lower()
    if v in ("on", "yes", "y", "true", "1"):
        return True
    if v in ("off", "no", "n", "false", "0"):
        return False
    raise ValueError(f"expected on or off, got {v!r}")


def apply_setting(s, name, *values):
    """Change one setting in place. Returns a short description; raises
    ValueError on a bad name or value."""
    name = (name or "").lower()
    if not values:
        raise ValueError("missing value. Settings: " + SETTING_HELP)
    v = values[0]
    if name == "port":
        p = int(v)
        if not 1024 <= p <= 65535:
            raise ValueError("port must be 1024-65535 (Android does not let apps use lower ports)")
        s["port"] = p
        return f"port {p}"
    if name == "lan":
        S.set_lan(s, _on(v))
        return "LAN access on (bind 0.0.0.0)" if s["lan"] else "localhost only (bind 127.0.0.1)"
    if name == "log":
        s["log_requests"] = _on(v)
        return f"request log {'on' if s['log_requests'] else 'off'}"
    if name == "console":
        s["log_to_console"] = _on(v)
        return f"console log {'on' if s['log_to_console'] else 'off'}"
    if name == "cors":
        s["cors_origin"] = v.strip() or "*"
        return f"CORS origin {s['cors_origin']}"
    if name == "prefix":
        s["model_prefix"] = v.strip() or "testbed-"
        return f"model prefix {s['model_prefix']}"
    if name == "tools":
        v = v.strip().lower()
        if v not in ("deny", "allow"):
            raise ValueError("tools takes deny or allow")
        s["agent_tool_calls"] = v
        return ("agent tool calls that need confirmation run unasked" if v == "allow"
                else "agent tool calls that need confirmation are refused")
    if name == "chunk":
        s["stream_chunk_words"] = max(1, int(v))
        return f"{s['stream_chunk_words']} word(s) per stream chunk"
    if name == "model":
        n = v.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/\-]{0,63}", n):
            raise ValueError("model name: letters, digits and . _ : / - (up to 64)")
        s["model_name"] = n
        return f"model name {n} (the one model that serves the whole stack)"
    if name in ("roles", "expose"):
        # v3.7.2: one endpoint, one model name; there is nothing to expose
        raise ValueError(f"'{name}' is gone in 3.7.2: the endpoint always serves one model name "
                         f"({S.main_model(s)}) that wraps every role. Benchmark a role with the benchmark tools "
                         "and check routing with the route trace in the terminal.")
    ent = s.setdefault("entity", {})
    choices = {"system": ("client_system", ("append", "ignore")), "trace": ("trace", ("off", "field", "content")),
               "media": ("media", ("url", "data")), "media-auth": ("media_auth", ("link", "key")),
               "media_auth": ("media_auth", ("link", "key"))}
    if name in choices:
        key, ok = choices[name]
        val = v.strip().lower()
        if val not in ok:
            raise ValueError(f"{name} takes {' or '.join(ok)}")
        ent[key] = val
        return f"{name} {val}"
    if name in ("media-hours", "media_hours", "attach-chars", "attach_chars", "pdf-pages", "pdf_pages"):
        key = {"media": "media_ttl_hours", "attac": "attach_max_chars", "pdf-p": "pdf_ocr_pages",
               "pdf_p": "pdf_ocr_pages"}[name[:5]]
        n = int(v)
        if n < 1:
            raise ValueError(f"{name} must be 1 or more")
        ent[key] = n
        return f"{key} {n}"
    if name == "call":
        ent["call_page"] = _on(v)
        return f"call page {'on' if ent['call_page'] else 'off'}"
    raise ValueError(f"unknown setting {name!r}. Settings: {SETTING_HELP}")


def settings_lines(s):
    es = dict(S.default_settings()["entity"], **(s.get("entity") or {}))
    return [f"  Model:           {S.main_model(s)}  (the whole stack as one entity)",
            f"  Port:            {s.get('port')}",
            f"  Access:          {'LAN (same Wi-Fi), bind 0.0.0.0' if s.get('lan') else 'this phone only (127.0.0.1)'}",
            f"  API key:         {mask(s.get('api_key'))}  (made {str(s.get('key_created_at'))[:19]})",
            f"  Model prefix:    {s.get('model_prefix')}",
            f"  App system msg:  {es['client_system']} (soul.md and the persona prompt always stay)",
            f"  Stack trace:     {es['trace']}   Media: {es['media']}, auth {es['media_auth']}, kept "
            f"{es['media_ttl_hours']} h   Attach cap: {es['attach_max_chars']} chars",
            f"  Call page:       {'on' if es.get('call_page', True) else 'off'}",
            f"  Request log:     {'on' if s.get('log_requests', True) else 'off'} (data/{S.LOG_FILE}); "
            f"console {'on' if s.get('log_to_console', True) else 'off'}",
            f"  CORS origin:     {s.get('cors_origin')}",
            f"  Stream chunks:   {s.get('stream_chunk_words')} word(s)",
            f"  Agent tools:     {s.get('agent_tool_calls')} (tool calls that would need your confirmation)"]


def models_lines(ent, s, models=None):
    models = models if models is not None else S.exposed_models(ent, s)
    out = []
    for m in models.values():
        out.append(f"  {m['id']:<44} {m['type']:<20} {m['target'][:70]}")
    unset = S.unset_roles(ent, s)
    if unset:
        out.append("  Roles not set (that name cannot do these yet): " + ", ".join(R.label(k) for k in unset))
    return out or ["  (none)"]


def ensure_nvidia_key():
    key = load_api_key()
    if key:
        return True
    if not sys.stdin.isatty():
        print("[!] NVIDIA_API_KEY is not set; model-backed roles will fail. Set it in ./start.sh: Keys & MCP.",
              file=sys.stderr)
        return False
    key = sanitize_key(getpass("Paste NVIDIA API key (used only for NVIDIA calls, never shown to clients): "))
    if key:
        os.environ["NVIDIA_API_KEY"] = key
        return True
    return False


def run_self_test(srv=None, base=None, key=None, out=print, make_entity=None, settings=None, full=True):
    """Self-test against a running server; with none running, start one on
    a free port for the test and stop it after. full=False skips the heavy
    live media checks (setup does that unless setup_full_self_test is on).
    A check that fails never raises: its row says why."""
    temp = None
    s = srv.settings if srv else (settings or S.load_settings())
    if srv is not None and srv.running:
        base = srv.local_base()
    elif base is None:
        if S.already_running(s.get("port")):
            base = f"http://127.0.0.1:{s.get('port')}/v1"
        else:
            ent = make_entity() if make_entity else None
            if ent is None:
                out("  Server is not running and no testbed is loaded to start one.")
                return []
            temp = S.TestServer(ent, s, port=0, host="127.0.0.1", quiet=True).start()
            base = temp.local_base()
            out(f"  (started a temporary server on {base} for the test)")
    out(f"Self-test against {base}")
    soul = None
    try:
        if srv is not None and getattr(srv, "app", None) is not None:
            soul = srv.app.ent.soul
        elif temp is not None:
            soul = temp.app.ent.soul
        else:
            soul = S.config.load_soul()
    except Exception:  # noqa: BLE001 - the identity check just compares less
        soul = None
    try:
        rows = S.self_test(base, key or s["api_key"], out=out, soul_name=S.unified.soul_name(soul or ""),
                           full=full, timeout=float(s.get("self_test_timeout_sec") or 90),
                           heavy_timeout=float(s.get("self_test_heavy_timeout_sec") or 240))
    except Exception as e:  # noqa: BLE001 - never a traceback in setup
        bid = S._bug_note("servemenu.run_self_test", e)
        out(f"  The self-test itself broke: {type(e).__name__}: {e}{bid}")
        rows = [("self-test", "FAIL", f"{type(e).__name__}: {e}{bid}", 0)]
    finally:
        if temp:
            temp.stop()
    out("Result: " + S.test_summary(rows))
    for line in S.failure_summary(rows):
        out("  " + line)
    return rows


def start_tunnel(srv, inp, out):
    if not srv or not srv.running:
        out("Start the server first.")
        return None
    if not S.Tunnel.available():
        out("cloudflared is not installed. Install it in Termux with:")
        out(f"    {S.TUNNEL_INSTALL}")
        out("then come back here. (Any other tunnel works too, pointed at "
            f"http://127.0.0.1:{srv.bound_port}.)")
        return None
    out("[!] " + S.TUNNEL_WARNING)
    if inp("Start a public tunnel? (y/N): ").strip().lower() != "y":
        return None
    t = S.Tunnel(srv.bound_port)
    out("Starting cloudflared (can take up to 40 seconds)...")
    try:
        url = t.start()
    except (RuntimeError, OSError) as e:
        out(f"Tunnel failed: {e}")
        return None
    srv.tunnel = t
    srv.app.public_url = url
    out(f"Public base URL: {url}/v1")
    out("The API key is still required on every request.")
    return url


def run_menu(ent, inp=input, out=print, state=None, save_fn=None):
    """Interactive server menu. `state` (a dict) keeps the server across
    calls so it stays up while the caller (the testbed) runs."""
    state = state if state is not None else {}
    s = S.load_settings()
    srv = state.get("server")
    if srv is not None:
        s = srv.settings
    while True:
        running = bool(srv and srv.running)
        out("\n" + C.header("OPENAI-COMPATIBLE TEST SERVER") + "  " +
            (C.ok(f"[running, port {srv.bound_port}]") if running else C.dim("[stopped]")))
        out(C.rule(50))
        tunnel = f"on: {srv.app.public_url}" if running and srv.app.public_url else "cloudflared"
        for title, rows in (("Server", (("1", "Stop the server" if running else "Start the server", ""),
                                         ("2", "Connection details", "URL, key, model names"),
                                         ("3", "Public tunnel", tunnel))),
                            ("Check", (("4", "Self-test", "calls it like a UI"), ("5", "Request log", ""))),
                            ("Setup", (("6", "Exposed models", ""), ("7", "Settings", "port, LAN, log, CORS"),
                                       ("8", "New API key", ""), ("9", "Config for UIs", "Open WebUI, ...")))):
            out(C.section(title))
            for k, name, extra in rows:
                out(C.entry(k, name, extra))
        out(C.entry(0, "Back" + (" (server keeps running)" if running else "")))
        c = inp("\nSelection: ").strip()
        if c == "1":
            if running:
                srv.stop()
                out("Server stopped.")
            else:
                try:
                    srv = S.TestServer(ent, s, quiet=True).start()
                    state["server"] = srv
                    out(srv.block())
                    out("Requests are not printed here (they would mix with the testbed); see option 5.")
                except OSError as e:
                    srv = None
                    out(f"Could not start on {s.get('bind')}:{s.get('port')}: {e}. Change the port in settings.")
        elif c == "2":
            models = S.exposed_models(ent, s)
            block = S.connection_block(s, models, srv.bound_port if running else None,
                                       srv.app.public_url if running else None, running=running)
            out(block)
            if S.shutil.which("termux-clipboard-set") and inp("Copy to clipboard? (y/N): ").strip().lower() == "y":
                out("Copied." if S.copy_to_clipboard(block) else "Copy failed.")
        elif c == "4":
            run_self_test(srv if running else None, out=out, make_entity=lambda: ent)
        elif c == "5":
            rows = S.read_log(30)
            out("Last requests (time, status, method, path, model, latency):")
            for line in S.format_log(rows, color=C.enabled()) or ["  (empty)"]:
                out("  " + line)
            out("Summary of the whole log: " + S.log_summary(S.read_log(0)))
        elif c == "6":
            for line in models_lines(ent, s):
                out(line)
        elif c == "7":
            for line in settings_lines(s):
                out(line)
            out("To change one, type it as: " + SETTING_HELP)
            raw = inp("Setting (Enter to keep all): ").strip()
            if raw:
                parts = raw.split()
                try:
                    old = (s.get("port"), s.get("bind"))
                    out("Set: " + apply_setting(s, parts[0], *parts[1:]))
                    S.save_settings(s)
                    if parts[0].lower() == "lan" and s.get("lan"):
                        out("[!] Anyone on the same Wi-Fi who has the key can now use your NVIDIA quota.")
                    if running and old != (s.get("port"), s.get("bind")):
                        if inp("Restart the server now to apply? (Y/n): ").strip().lower() != "n":
                            srv.stop()
                            try:
                                srv = S.TestServer(ent, s, quiet=True).start()
                                state["server"] = srv
                                out(srv.block())
                            except OSError as e:
                                srv = None
                                out(f"Could not restart: {e}")
                except ValueError as e:
                    out(f"Not changed: {e}")
        elif c == "8":
            if inp("Make a new key? The old one stops working at once. (y/N): ").strip().lower() == "y":
                S.regenerate_key(s)
                out(f"New API key: {s['api_key']}")
        elif c == "3":
            if running and srv.tunnel:
                if inp("Stop the public tunnel? (y/N): ").strip().lower() == "y":
                    srv.tunnel.stop()
                    srv.tunnel = None
                    srv.app.public_url = None
                    out("Tunnel stopped.")
            else:
                start_tunnel(srv if running else None, inp, out)
        elif c == "9":
            out(S.ui_configs(s, S.exposed_models(ent, s), srv.bound_port if running else None,
                             srv.app.public_url if running else None))
        elif c == "0" or c == "":
            return srv


# ---------------------------------------------------------------------------
# CLI: python3 -m nimlab serve [action]
# ---------------------------------------------------------------------------
def cmd_serve(args):
    try:
        sys.stdout.reconfigure(line_buffering=True)   # the request log shows at once, also when piped
    except (AttributeError, ValueError):
        pass
    s = S.load_settings()
    action = args.action or "start"
    if args.port:
        s["port"] = int(args.port)
    if args.lan is not None:
        S.set_lan(s, args.lan)
    if args.no_log:
        s["log_requests"] = False
    if args.save:
        S.save_settings(s)

    def entity():
        from .entity import Entity
        ensure_nvidia_key()
        return Entity(log=lambda *a: print(*a, file=sys.stderr))

    if action == "info":
        models = S.exposed_models(entity_readonly(), s)
        print(S.connection_block(s, models, running=S.already_running(s.get("port"))))
        return 0
    if action == "ui":
        print(S.ui_configs(s, S.exposed_models(entity_readonly(), s)))
        return 0
    if action == "log":
        rows = S.read_log(args.limit or 50)
        for line in S.format_log(rows, color=C.enabled()) or ["(empty)"]:
            print(line)
        print("Summary: " + S.log_summary(S.read_log(0)))
        return 0
    if action == "tunnel":
        return cmd_tunnel(args, s)
    if action == "regen-key":
        S.regenerate_key(s)
        print(f"New API key: {s['api_key']}")
        print("A server that is already running picks it up after a restart.")
        return 0
    if action == "settings":
        if args.values and str(args.values[0]).lower().startswith("memory"):
            # serve settings memory.<key> <value>: long-term memory lives in
            # config_cluster.json (memory_settings), shared with the testbed
            from . import memmenu
            v = list(args.values)
            if v[0].lower() == "memory" and len(v) > 1:
                v = ["memory." + v[1]] + v[2:]
            try:
                ms = memmenu.load_ms()
                print("Set: " + memmenu.apply_setting(ms, *v))
                memmenu.save_ms(ms)
            except ValueError as e:
                print(f"Not changed: {e}")
                return 2
            print("A running server picks it up after a restart. `./start.sh memory test` checks it.")
            return 0
        if args.values:
            try:
                print("Set: " + apply_setting(s, *args.values))
            except ValueError as e:
                print(f"Not changed: {e}")
                return 2
            S.save_settings(s)
        for line in settings_lines(s):
            print(line)
        return 0
    if action == "models":
        for line in models_lines(entity_readonly(), s):
            print(line)
        return 0
    if action == "test":
        vals = [str(v).lower() for v in (getattr(args, "values", None) or [])]
        full = bool(getattr(args, "full", False)) or "quick" not in vals
        rows = run_self_test(base=None, out=print, make_entity=entity, settings=s, full=full)
        return 0 if rows and not any(r[1] == "FAIL" for r in rows) else 1
    if action == "menu":
        state = {}
        try:
            run_menu(entity(), state=state)
        except (KeyboardInterrupt, EOFError):
            print()
        finally:
            if state.get("server"):
                state["server"].stop()
        return 0
    # start (foreground)
    # 3.7.1: exit codes the service supervisor understands, so a held port
    # no longer crash-loops serve with code 1 every few seconds
    owner = S.port_owner(s.get("port"))
    if owner == "nimlab":
        print(f"A Nim Lab test server is already running on port {s.get('port')} (another copy: a second "
              "service/supervisor or a `serve start` in another session). Not starting a second one. "
              "`nimlab service status` lists stray copies; use another port with --port.")
        return 75
    if owner == "other":
        print(f"[config] Port {s.get('port')} is held by another program (not Nim Lab). Free it or choose "
              "another port: nimlab serve settings port <n>")
        return 78
    srv = S.TestServer(entity(), s)
    try:
        srv.start(background=True)
    except OSError as e:
        print(f"[config] Could not start on {srv.host}:{srv.port}: {e}")
        return 78 if "in use" in str(e).lower() or getattr(e, "errno", None) in (98, 48, 13) else 1
    keeper = None
    t = TN.settings_of(s)
    if args.tunnel or (t["mode"] != "off" and t.get("auto_start")):
        mode = t["mode"] if t["mode"] != "off" else "quick"
        tset = dict(t, mode=mode)
        print(f"Starting the {mode} tunnel (cloudflared, up to 40 seconds)...")
        keeper = TN.Keeper(srv.bound_port, tset, warn=lambda m: print(m, file=sys.stderr, flush=True),
                           on_url=lambda u: setattr(srv.app, "public_url", u))
        if keeper.start():
            print("[!] " + S.TUNNEL_WARNING)
    print(srv.block())
    if s.get("lan"):
        print("[!] LAN access is on: anyone on this Wi-Fi with the key can use your NVIDIA quota.")
    print("Serving. Requests are listed below. Press Ctrl-C to stop.")
    try:
        while srv.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if keeper:
            keeper.stop()
        srv.stop()
    return 0


def tunnel_lines(s):
    t = TN.settings_of(s)
    st = TN.read_status()
    n = t["named"]
    lines = [f"Mode       : {t['mode']}" + ("" if t["mode"] == "off" else
                                             f"   (auto-start with serve: {'on' if t['auto_start'] else 'off'})")]
    if t["mode"] == "named":
        if n.get("method") == "token":
            tok = TN.load_token()
            lines.append(f"Named      : token {TN.mask(tok)} in {TN.token_path()}"
                         + (f"   mode {oct(TN.file_mode(TN.token_path()) or 0)[2:]}" if tok else ""))
        else:
            lines.append(f"Named      : tunnel {n.get('tunnel') or '?'}, credentials {n.get('credentials_file') or '?'}")
        lines.append(f"Hostname   : {n.get('hostname') or '(set in the Cloudflare dashboard)'}")
        for p in TN.check_named(n):
            lines.append(f"[!] {p}")
    exe = TN.find_cloudflared()
    lines.append(f"cloudflared: {exe or 'not installed (serve tunnel install)'}")
    if st:
        lines.append(f"Last run   : {st.get('state', '?')} {st.get('url') or ''}".rstrip()
                     + (f"  ({st['last_error']})" if st.get("last_error") and st.get("state") != "up" else ""))
    return lines


def cmd_tunnel(args, s):
    """serve tunnel [status|quick|named|off|auto on|off|install|token-delete]"""
    from getpass import getpass
    v = list(args.values or [])
    sub = v.pop(0) if v else "status"
    t = TN.settings_of(s)
    if sub == "status":
        for ln in tunnel_lines(s):
            print(ln)
        return 0
    if sub == "install":
        ok, msg = TN.install_cloudflared()
        print(("[ok] cloudflared: " if ok else "[x] ") + msg)
        return 0 if ok else 1
    if sub == "off":
        t["mode"] = "off"
        S.save_settings(s)
        print("[ok] Tunnel off: the server stays local" + (" (and LAN)" if s.get("lan") else "") + ".")
        return 0
    if sub == "auto":
        if not v or v[0] not in ("on", "off"):
            print("usage: serve tunnel auto on|off")
            return 2
        t["auto_start"] = v[0] == "on"
        S.save_settings(s)
        print(f"[ok] Tunnel auto-start with serve: {v[0]}")
        return 0
    if sub == "token-delete":
        print("[ok] Deleted the saved tunnel token." if TN.delete_token() else "No saved token.")
        return 0
    if sub == "quick":
        t["mode"] = "quick"
    elif sub == "named":
        n = t["named"]
        if args.token or (not v and not args.credentials and n.get("method") != "config"):
            tok = getpass("Tunnel token (hidden; from Zero Trust > Networks > Tunnels): ") \
                if sys.stdin.isatty() else sys.stdin.readline()
            if tok.strip():
                try:
                    TN.save_token(tok)
                except ValueError as e:
                    print(f"[x] {e}")
                    return 2
                print(f"[ok] Token saved to {TN.token_path()} (mode 600).")
            n["method"] = "token"
        else:
            n["method"] = "config"
            if v:
                n["tunnel"] = v[0]
            if args.credentials:
                n["credentials_file"] = os.path.expanduser(args.credentials)
        if args.hostname:
            n["hostname"] = args.hostname.removeprefix("https://").rstrip("/")
        t["mode"] = "named"
        probs = TN.check_named(n)
        for p in probs:
            print(f"[!] {p}")
        if n["method"] == "config" and not probs:
            print(f"[ok] cloudflared config: {TN.write_config_yml(n, s.get('port', 8765))}")
        if n["method"] == "token":
            print(f"    In the Cloudflare dashboard, the tunnel's public hostname must point to "
                  f"http://localhost:{s.get('port', 8765)}")
    else:
        print("usage: serve tunnel status|quick|named|off|auto on|off|install|token-delete")
        return 2
    if args.auto is not None:
        t["auto_start"] = args.auto
    S.save_settings(s)
    print(f"[ok] Tunnel mode: {t['mode']}. Auto-start with serve: {'on' if t['auto_start'] else 'off'}"
          + ("" if t["auto_start"] else " (start it with: serve start --tunnel)") + ".")
    print("    The server's API key is required on every request, so the public URL alone lets nobody in.")
    if not TN.find_cloudflared():
        print("[!] cloudflared is not installed yet: serve tunnel install")
    return 0


def entity_readonly():
    """An Entity for listing models only: no key prompt, no memory."""
    from .entity import Entity
    return Entity(memory=False, log=lambda *a: None)
