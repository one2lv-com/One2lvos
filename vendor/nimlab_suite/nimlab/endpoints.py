"""Custom endpoints (3.8.2): your own OpenAI-compatible gateways.

Add a gateway by its base URL (and an API key if it needs one), import the
models its /v1/models lists, or type models in by hand (a chat model, an
embedding model, a TTS voice, a database-backed entity served as a chat
model). Those models can then be put on any role, and every caller (the
entity, the playground, benchmarks, the server) reaches them through the same
routing path as NVIDIA models: NimClient.route().

Where things are kept:
  ~/.config/nimlab/endpoints.json   names, URLs, models (no keys)
  ~/.config/nimlab/secrets.json     the keys, under "endpoints" (mode 600)
Both live outside the project folder, so they are never in a release zip and
survive a fresh install. Nothing is set by default.
"""

import json
import os
import re
import urllib.error
import urllib.request

from . import config
from .core import mask, sanitize_key

KINDS = ("chat", "embedding", "tts", "vision", "rerank", "image_gen")
# the request path under the base URL for each kind (OpenAI-compatible)
PATHS = {"chat": "/chat/completions", "vision": "/chat/completions", "embedding": "/embeddings",
         "tts": "/audio/speech", "rerank": "/rerank", "image_gen": "/images/generations"}
# NimClient kinds -> the endpoint kinds that can serve them
SERVES = {"chat": ("chat", "vision"), "chat_stream": ("chat", "vision"), "vision": ("vision", "chat"),
          "embeddings": ("embedding",), "embedding": ("embedding",), "tts": ("tts",),
          "audio_tts": ("tts",), "rerank": ("rerank",), "image_gen": ("image_gen",)}
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$")


def path():
    p = os.environ.get("NIMLAB_ENDPOINTS")
    if p:
        return os.path.expanduser(p)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "nimlab", "endpoints.json")


def load():
    d = config.load_json(path(), None)
    if not isinstance(d, dict) or not isinstance(d.get("endpoints"), list):
        return {"endpoints": []}
    d["endpoints"] = [e for e in d["endpoints"] if isinstance(e, dict) and e.get("name") and e.get("base_url")]
    return d


def save(d):
    p = path()
    os.makedirs(os.path.dirname(p), mode=0o700, exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
        f.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def all_endpoints():
    return load()["endpoints"]


def get(name):
    for e in all_endpoints():
        if e["name"] == name:
            return e
    return None


def normalize_url(url):
    """'https://host/' or 'https://host/v1/models' -> 'https://host/v1'."""
    u = (url or "").strip().rstrip("/")
    if not re.match(r"^https?://[^/\s]+", u):
        raise ValueError("the URL has to start with http:// or https://")
    for tail in ("/models", "/chat/completions", "/embeddings", "/audio/speech"):
        if u.endswith(tail):
            u = u[: -len(tail)]
    if not re.search(r"/v\d+[a-z]*$", u):
        u += "/v1"
    return u


def guess_kind(model_id):
    m = model_id.lower()
    if "embed" in m:
        return "embedding"
    if any(x in m for x in ("magpie", "tts", "speech", "voice")):
        return "tts"
    if "rerank" in m:
        return "rerank"
    if any(x in m for x in ("flux", "stable-diffusion", "sdxl", "image-gen")):
        return "image_gen"
    if any(x in m for x in ("-vl", "vision", "vlm")):
        return "vision"
    return "chat"


# -- keys (in the shared secret store) --------------------------------------
def key_for(name):
    env = os.environ.get("NIMLAB_ENDPOINT_KEY_" + re.sub(r"[^A-Z0-9]", "_", name.upper()))
    if env:
        return sanitize_key(env)
    from . import mcpkey
    return sanitize_key(str((mcpkey._read().get("endpoints") or {}).get(name, "")))


def set_key(name, key):
    from . import mcpkey
    data = mcpkey._read()
    keys = data.setdefault("endpoints", {})
    key = sanitize_key(key or "")
    if key:
        keys[name] = key
    else:
        keys.pop(name, None)
    mcpkey._write(data)


# -- edit -------------------------------------------------------------------
def add(name, base_url, key=None):
    if not NAME_RE.match(name or ""):
        raise ValueError("a name is letters, digits, - _ or . (up to 40)")
    d = load()
    if any(e["name"] == name for e in d["endpoints"]):
        raise ValueError(f"there is already an endpoint called {name}")
    e = {"name": name, "base_url": normalize_url(base_url), "models": [], "added": config.timestamp()}
    d["endpoints"].append(e)
    save(d)
    if key:
        set_key(name, key)
    return e


def remove(name):
    d = load()
    n = len(d["endpoints"])
    d["endpoints"] = [e for e in d["endpoints"] if e["name"] != name]
    save(d)
    set_key(name, "")
    return len(d["endpoints"]) < n


def set_url(name, base_url):
    d = load()
    for e in d["endpoints"]:
        if e["name"] == name:
            e["base_url"] = normalize_url(base_url)
            save(d)
            return e
    raise KeyError(name)


def add_model(name, model_id, kind=None, path_=None, source="manual"):
    model_id = (model_id or "").strip()
    if not model_id:
        raise ValueError("empty model id")
    kind = kind or guess_kind(model_id)
    if kind not in KINDS:
        raise ValueError(f"kind is one of {', '.join(KINDS)}")
    d = load()
    for e in d["endpoints"]:
        if e["name"] == name:
            e["models"] = [m for m in e.get("models", []) if m.get("id") != model_id]
            m = {"id": model_id, "kind": kind, "source": source}
            if path_:
                m["path"] = "/" + path_.strip().lstrip("/")
            e["models"].append(m)
            save(d)
            return m
    raise KeyError(name)


def remove_model(name, model_id):
    d = load()
    for e in d["endpoints"]:
        if e["name"] == name:
            n = len(e.get("models", []))
            e["models"] = [m for m in e.get("models", []) if m.get("id") != model_id]
            save(d)
            return len(e["models"]) < n
    raise KeyError(name)


# -- talk to it ---------------------------------------------------------------
def headers(name):
    k = key_for(name)
    return {"Authorization": f"Bearer {k}"} if k else {}


def fetch_models(name, opener=None, timeout=15):
    """GET <base>/models -> (ok, [ids] or error text)."""
    e = get(name)
    if not e:
        return False, f"no endpoint called {name}"
    req = urllib.request.Request(e["base_url"] + "/models",
                                 headers=dict(headers(name), **{"User-Agent": "nimlab"}))
    try:
        with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as ex:
        return False, f"HTTP {ex.code}" + (" (the key is missing or wrong)" if ex.code in (401, 403) else "")
    except (urllib.error.URLError, OSError, ValueError) as ex:
        return False, f"could not reach {e['base_url']}: {getattr(ex, 'reason', ex)}"
    items = body.get("data") if isinstance(body, dict) else body
    ids = [m.get("id") if isinstance(m, dict) else m for m in (items or [])]
    return True, [i for i in ids if isinstance(i, str) and i]


def import_models(name, opener=None):
    """Add every model the endpoint lists (kind guessed from the id; change it
    in the menu). Manual entries and kinds you set are kept."""
    ok, ids = fetch_models(name, opener)
    if not ok:
        return False, ids
    have = {m["id"] for m in (get(name) or {}).get("models", [])}
    added = []
    for mid in ids:
        if mid not in have:
            add_model(name, mid, source="listed")
            added.append(mid)
    return True, added


# -- routing ----------------------------------------------------------------
def model_url(e, m):
    return e["base_url"] + (m.get("path") or PATHS.get(m.get("kind"), "/chat/completions"))


def find(model_id, kind=None):
    """(endpoint, model) serving model_id, or (None, None). An id like
    'endpoint-name:model' picks the endpoint explicitly."""
    want = SERVES.get(kind) if kind else None
    pick = None
    if ":" in (model_id or "") and not model_id.startswith("http"):
        pick, model_id = model_id.split(":", 1)
    for e in all_endpoints():
        if pick and e["name"] != pick:
            continue
        for m in e.get("models", []):
            if m.get("id") == model_id and (not want or m.get("kind") in want):
                return e, m
    return None, None


def url_for(model_id, kind=None):
    e, m = find(model_id, kind)
    return model_url(e, m) if e else None


def owner_of(url):
    """The endpoint whose base URL the request URL is under (for its key)."""
    if not url:
        return None
    best = None
    for e in all_endpoints():
        b = e["base_url"]
        if url == b or url.startswith(b + "/"):
            if not best or len(b) > len(best["base_url"]):
                best = e
    return best


def real_model_id(model_id):
    """'gateway:model' -> 'model' (what the gateway expects in the body)."""
    if model_id and ":" in model_id and not model_id.startswith("http"):
        name, rest = model_id.split(":", 1)
        if get(name):
            return rest
    return model_id


def role_candidates(kind):
    """[(model_id, label)] of custom models for a role of this kind."""
    want = SERVES.get(kind, (kind,))
    out = []
    for e in all_endpoints():
        for m in e.get("models", []):
            if m.get("kind") in want:
                out.append((m["id"], f"{m['id']}  [{e['name']}, {m['kind']}]"))
    return out


def summary_lines():
    eps = all_endpoints()
    if not eps:
        return ["No custom endpoints yet. Add one to use models served by your own gateway."]
    out = []
    for e in eps:
        k = key_for(e["name"])
        out.append(f"{e['name']}: {e['base_url']}  key {mask(k) if k else 'none'}  "
                   f"{len(e.get('models', []))} model(s)")
        for m in e.get("models", []):
            out.append(f"    {m['id']}  ({m['kind']}{', ' + m['path'] if m.get('path') else ''})")
    return out


# -- command line (the menu is Models > Custom endpoints) --------------------
def cmd_endpoints(args):
    act = getattr(args, "act", None) or "list"
    try:
        if act == "list":
            for ln in summary_lines():
                print(ln)
        elif act == "add":
            key = ""
            if args.key_env:
                key = os.environ.get(args.key_env, "")
            elif not args.no_key:
                import getpass
                key = getpass.getpass("API key (Enter if it needs none): ").strip()
            e = add(args.name, args.url, key)
            print(f"[ok] added {e['name']}: {e['base_url']}. Next: nimlab endpoints import {e['name']}")
        elif act == "import":
            ok, res = import_models(args.name)
            print(f"[ok] {len(res)} new model(s): {', '.join(res) or 'none'}" if ok else f"[x] {res}")
            return 0 if ok else 1
        elif act == "model":
            m = add_model(args.name, args.model, args.kind, args.path)
            print(f"[ok] {args.name}: {m['id']} ({m['kind']})")
        elif act == "unmodel":
            print("[ok] removed" if remove_model(args.name, args.model) else "[x] no such model")
        elif act == "key":
            import getpass
            set_key(args.name, getpass.getpass("API key (Enter to remove): ").strip())
            print("[ok] saved")
        elif act == "remove":
            print("[ok] removed" if remove(args.name) else "[x] no such endpoint")
        elif act == "menu":
            from . import uimenu
            return uimenu.cmd_ui(type("A", (), {"screen": "endpoints"})())
    except (ValueError, KeyError) as e:
        print(f"[x] {e}")
        return 1
    return 0


def add_parser(sub):
    p = sub.add_parser("endpoints", help="Custom endpoints: your own OpenAI-compatible gateways")
    s = p.add_subparsers(dest="act")
    s.add_parser("list", help="Endpoints and their models")
    a = s.add_parser("add", help="Add one (asks for the key, hidden)")
    a.add_argument("name")
    a.add_argument("url")
    a.add_argument("--key-env", help="read the key from this environment variable")
    a.add_argument("--no-key", action="store_true", help="it needs no key")
    a = s.add_parser("import", help="Add the models its /models lists")
    a.add_argument("name")
    a = s.add_parser("model", help="Add a model by hand")
    a.add_argument("name")
    a.add_argument("model")
    a.add_argument("--kind", choices=KINDS)
    a.add_argument("--path", help="request path under the base URL (default by kind)")
    a = s.add_parser("unmodel", help="Remove a model")
    a.add_argument("name")
    a.add_argument("model")
    a = s.add_parser("key", help="Set or remove its API key (hidden)")
    a.add_argument("name")
    a = s.add_parser("remove", help="Remove an endpoint and its key")
    a.add_argument("name")
    s.add_parser("menu", help="Open the Custom endpoints menu")
    p.set_defaults(fn=cmd_endpoints)
    return p
