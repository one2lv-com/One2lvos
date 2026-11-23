"""The MCP server API key: where it comes from, saving it safely, and a
quick connection test.

Where the key comes from (first that has one wins):
  1. a key typed in for this session only (kept in memory, never written)
  2. the environment variable named in mcp_settings.auth.key_env
     (default MCP_API_KEY)
  3. the saved key in ~/.config/nimlab/secrets.json

The saved file lives outside the project folder, so zips, backups and git
never pick it up, and it is created with permissions 600 (directory 700).
NIMLAB_SECRETS overrides its path. The key is never written to
config_cluster.json, logs or any output; only mask() of it is shown.
"""

import json
import os
import stat

from .core import mask, sanitize_key

DEFAULT_ENV = "MCP_API_KEY"
_session = {}          # key_env -> key typed in for this session only


def secrets_path():
    p = os.environ.get("NIMLAB_SECRETS")
    if p:
        return os.path.expanduser(p)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "nimlab", "secrets.json")


def _key_env(auth):
    return (auth or {}).get("key_env") or DEFAULT_ENV


_cache = {}


def _read():
    path = secrets_path()
    try:
        mtime = os.stat(path).st_mtime_ns
    except OSError:
        return {}
    hit = _cache.get(path)
    if hit and hit[0] == mtime:
        return json.loads(hit[1])
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        data = json.loads(raw)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    _cache[path] = (mtime, json.dumps(data))
    return data


def _write(data):
    path = secrets_path()
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, mode=0o700, exist_ok=True)
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    _cache.pop(path, None)


def saved_key(auth=None):
    return sanitize_key(str((_read().get("mcp") or {}).get(_key_env(auth), "")))


def save_key(key, auth=None):
    """Save the key for future runs (600 file outside the project)."""
    key = sanitize_key(key)
    if not key:
        raise ValueError("empty key")
    data = _read()
    data.setdefault("mcp", {})[_key_env(auth)] = key
    _write(data)
    return secrets_path()


def delete_key(auth=None):
    """Delete the saved key (and the file when nothing else is in it).
    Returns True when there was one."""
    data = _read()
    mcp = data.get("mcp") or {}
    if _key_env(auth) not in mcp:
        return False
    mcp.pop(_key_env(auth))
    if not mcp:
        data.pop("mcp", None)
    if data:
        _write(data)
    else:
        try:
            os.unlink(secrets_path())
        except OSError:
            pass
    return True


def set_session_key(key, auth=None):
    key = sanitize_key(key)
    if key:
        _session[_key_env(auth)] = key
    else:
        _session.pop(_key_env(auth), None)


def clear_session_key(auth=None):
    _session.pop(_key_env(auth), None)


def resolve(auth=None, env=None):
    """(key, source) where source is 'session', 'env', 'saved' or 'none'."""
    env = os.environ if env is None else env
    name = _key_env(auth)
    if _session.get(name):
        return _session[name], "session"
    k = sanitize_key(env.get(name, ""))
    if k:
        return k, "env"
    k = saved_key(auth)
    if k:
        return k, "saved"
    return "", "none"


def source_text(auth=None, env=None):
    """'nvapi-...abcd (from $MCP_API_KEY)' style description, never the key."""
    key, src = resolve(auth, env)
    name = _key_env(auth)
    where = {"session": "typed in, this session only", "env": f"from ${name}",
             "saved": f"saved in {secrets_path()}", "none": f"not set (${name} or a saved key)"}[src]
    return (f"{mask(key)} ({where})" if key else where), src


def file_mode(path=None):
    try:
        return stat.S_IMODE(os.stat(path or secrets_path()).st_mode)
    except OSError:
        return None


def known_keys():
    """Every MCP key this process could send (for redaction)."""
    keys = list(_session.values())
    keys += [sanitize_key(str(v)) for v in (_read().get("mcp") or {}).values()]
    return [k for k in keys if k]


# ---------------------------------------------------------------------------
# Connection test
# ---------------------------------------------------------------------------
def test_connection(settings, http=None):
    """Connect to the MCP server, initialize and list tools.

    Returns {ok, url, tools, names, server, protocol, auth_error, error,
    key_source}. Never raises; the error text has secrets removed."""
    from .core import redact
    from .mcp import MCPClient
    settings = dict(settings or {})
    _, src = resolve(settings.get("auth"))
    out = {"ok": False, "url": (settings.get("url") or "").strip(), "tools": 0, "names": [], "server": "",
           "protocol": "", "auth_error": False, "error": "", "key_source": src}
    if not out["url"]:
        out["error"] = "no MCP URL set"
        return out
    try:
        client = MCPClient(settings, http=http)
        tools = client.list_tools()
        out.update(ok=True, tools=len(tools), names=[t.get("name", "?") for t in tools], tool_defs=tools,
                   server=str(client.server_info.get("name", "")), protocol=str(client.negotiated_protocol or ""))
    except Exception as e:  # noqa: BLE001 - a test reports, it never crashes the menu
        msg = redact(str(e), known_keys())
        out["error"] = msg
        out["auth_error"] = "auth rejected" in msg or "HTTP 401" in msg or "HTTP 403" in msg
    return out


def describe_test(res):
    """Plain lines for a test_connection() result."""
    if res["ok"]:
        names = ", ".join(res["names"][:8]) + (" ..." if len(res["names"]) > 8 else "")
        lines = [f"[ok] Connected to {res['url']}",
                 f"     server {res['server'] or '?'} | protocol {res['protocol'] or '?'} | {res['tools']} tools"]
        if names:
            lines.append(f"     tools: {names}")
        return lines
    if res["auth_error"]:
        how = {"none": "No key is set: set one with 'Set / replace MCP API key'.",
               "session": "The key typed in for this session was refused.",
               "env": "The key from the environment variable was refused.",
               "saved": "The saved key was refused."}[res["key_source"]]
        return [f"[x] Auth error at {res['url']}: {res['error']}",
                f"    {how} Also check the auth style (x-api-key / bearer / custom header)."]
    return [f"[x] Could not connect to {res['url'] or '(no URL)'}: {res['error']}"]
