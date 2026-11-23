"""3.7.2 first-run setup: the data each step needs and the role suggestions.

Order (SeVin): key -> discover (API catalog + build.nvidia.com) -> function
IDs and specs -> 200 OK sweep -> MCP -> roles -> everything else.

Every later step reads what an earlier one wrote. When that data is missing
the step says so in plain words ("no models discovered yet: run step 2")
and offers to run the earlier step; it never blames the key or the
internet for missing data.
"""

import os

from . import store

# time limits (seconds) for the long first-run steps
DISCOVER_LIMIT = 20 * 60
SPECS_LIMIT = 25 * 60
SWEEP_LIMIT = 45 * 60
SWEEP_FAST_LIMIT = 12 * 60

# the table the memory backends write to
MEMORY_TABLE_DIMS = 2048


# ---------------------------------------------------------------------------
# What earlier steps left behind
# ---------------------------------------------------------------------------
def discovered_ids():
    try:
        return sorted((store.load(store.DISCOVERED) or {}).get("models") or {}, key=str.lower)
    except Exception:  # noqa: BLE001 - a broken file reads as no data
        return []


def spec_count():
    from .sweep import spec_cache_dir
    try:
        return sum(1 for n in os.listdir(spec_cache_dir()) if n.endswith(".json"))
    except OSError:
        return 0


FUNCTIONS_MARK = "functions_pass.json"


def functions_done():
    """True once step 3 ran on this install (or a sweep did: it reads the
    same pages). The spec pages shipped in the zip do not count."""
    if os.path.exists(store.path(FUNCTIONS_MARK)):
        return True
    return probe_counts()[0] > 0


def mark_functions_done(specs, known, with_id):
    from . import config
    config.save_json(store.path(FUNCTIONS_MARK), {"at": config.timestamp(), "specs": specs,
                                                  "grpc_only": known, "with_function_id": with_id})


def verified_ids():
    try:
        return sorted(store.verified_ids(), key=str.lower)
    except Exception:  # noqa: BLE001
        return []


def probe_counts():
    """-> (models probed, gRPC-only marks)."""
    try:
        probes = (store.load(store.PROBES) or {}).get("models") or {}
    except Exception:  # noqa: BLE001
        return 0, 0
    grpc = sum(1 for v in probes.values() if isinstance(v, dict) and v.get("status") == "GRPC_NVCF_ONLY")
    return len(probes), grpc


def grpc_counts():
    """-> (gRPC-only models known, how many have a function ID)."""
    from . import nvcf_grpc
    try:
        rows = nvcf_grpc.rows()
    except Exception:  # noqa: BLE001
        return 0, 0
    return len(rows), sum(1 for r in rows if r.get("function_id"))


# ---------------------------------------------------------------------------
# Role suggestions
# ---------------------------------------------------------------------------
# words in an MCP tool's name or description that suit an MCP-backed role
MCP_WORDS = {
    "tts": ("tts", "speak", "speech", "voice"),
    "asr": ("asr", "transcri", "speech_to_text", "stt"),
    "image_gen": ("image_gen", "generate_image", "text_to_image", "flux", "draw", "creative_art"),
    "audio_gen": ("audio_gen", "music", "beat", "sound"),
    "video": ("video",),
    "ocr": ("ocr",),
    "vision": ("vision", "analyze_image", "describe_image"),
}


def _tool_text(tool):
    return f"{tool.get('name', '')} {tool.get('description', '')}".lower()


def mcp_matches(role, tools):
    """MCP tools whose name/description suits an MCP-capable role."""
    from .rolemcp import ROLE_INPUTS
    if role not in ROLE_INPUTS:
        return []
    words = MCP_WORDS.get(role, ())
    return [t["name"] for t in tools or [] if t.get("name") and any(w in _tool_text(t) for w in words)]


def current_of(roles, key):
    """('model', id) | ('mcp', tool) | (None, None) for a role's current value."""
    from . import roles as R
    v = R.normalize((roles or {}).get(key), key)
    if v.get("backend") == R.MCP and v.get("tool"):
        return "mcp", v["tool"]
    m = R.model_of(v)
    return ("model", m) if m else (None, None)


def suggest(roles, verified, kinds=None, infos=None, tools=None, discovered=None):
    """One suggestion per role, built from the 200 OK list and MCP tools.

    -> [{key, name, current: (backend, value), pick: (backend, value) or
    None, why, options: [(backend, value, note)]}]. The pick keeps a current
    choice that still works (a verified model, or an MCP tool the server
    still offers), else the first suited verified model, else a matching MCP
    tool, else a possible verified model. options lists every suited and
    possible verified model plus matching MCP tools, so there is always
    something to choose from when the sweep found anything."""
    from . import roles as R
    verified = list(verified or [])
    vset = set(verified)
    tool_names = {t.get("name") for t in tools or []}
    out = []
    for d in R.ROLE_DEFS:
        suited, possible, _ = R.candidates(d.key, verified, kinds, infos)
        mcp = mcp_matches(d.key, tools)
        cur = current_of(roles, d.key)
        options = [("model", m, "suited") for m in suited] + [("model", m, "possible") for m in possible] + \
                  [("mcp", t, "MCP tool") for t in mcp]
        pick, why = None, ""
        if cur[0] == "model" and cur[1] in vset:
            pick, why = cur, "current model, passed the 200 OK test"
        elif cur[0] == "mcp" and cur[1] in tool_names:
            pick, why = cur, "current MCP tool, still on the server"
        elif suited:
            pick, why = ("model", suited[0]), "suited and passed the 200 OK test"
        elif mcp:
            pick, why = ("mcp", mcp[0]), "MCP tool for this role"
        elif possible:
            pick, why = ("model", possible[0]), "could work (passed 200 OK, not a typical fit)"
        elif cur[0]:
            pick, why = cur, "kept: nothing verified suits this role"
        else:
            why = "nothing verified suits this role yet"
        out.append({"key": d.key, "name": d.name, "current": cur, "pick": pick, "why": why, "options": options})
    return out


def describe(choice):
    if not choice or not choice[0]:
        return "(not set)"
    return ("MCP " + choice[1]) if choice[0] == "mcp" else choice[1]


def apply_choice(raw_cluster, key, choice, tools=None):
    """Write one role choice into a raw config_cluster dict. -> message."""
    from . import roles as R, rolemcp
    roles = raw_cluster.setdefault("roles", {})
    backend, value = choice
    if backend == "mcp":
        tool = next((t for t in tools or [] if t.get("name") == value), {"name": value})
        try:
            arg_map = rolemcp.auto_arg_map(key, tool)
        except Exception:  # noqa: BLE001 - the arg map can be edited later
            arg_map = {}
        R.set_mcp(roles, key, value, arg_map)
        return f"{R.label(key)}: MCP tool {value}"
    R.set_model(roles, key, value)
    return f"{R.label(key)}: {value}"


# ---------------------------------------------------------------------------
# Embedding models for memory
# ---------------------------------------------------------------------------
def embed_options(verified, kinds=None):
    """Verified embedding models with what the lab knows of their size:
    -> [(model, dims or None, note)], the ones that match the memory table
    first."""
    from . import ltm, roles as R
    suited, possible, _ = R.candidates("embedding", list(verified or []), kinds, None)
    out = []
    for m in suited + [p for p in possible if "embed" in p.lower()]:
        if m in ltm.KNOWN_BAD_EMBED:
            continue
        info = ltm.KNOWN_EMBED.get(m, {})
        dims = info.get("dims")
        if dims == MEMORY_TABLE_DIMS:
            note = f"{dims} dimensions, matches the memory table"
        elif dims:
            note = f"{dims} dimensions: does NOT match the VECTOR({MEMORY_TABLE_DIMS}) table"
        else:
            note = "size not known yet: `nimlab memory test` measures it"
        out.append((m, dims, note))
    out.sort(key=lambda r: (r[1] != MEMORY_TABLE_DIMS, r[1] is None))
    return out


def mcp_tools(cluster):
    """(tools, error) from the MCP server in mcp_settings, for role picks."""
    s = (cluster or {}).get("mcp_settings") or {}
    if not s.get("url"):
        return [], "no MCP server URL is set (step 5)"
    try:
        from .mcp import MCPClient
        return MCPClient(dict(s, tool_timeout_sec=20)).list_tools(), None
    except Exception as e:  # noqa: BLE001 - roles still work without MCP
        return [], f"{type(e).__name__}: {e}"
