"""Project paths and JSON config helpers.

All paths resolve relative to the project folder, not the current working
directory, so every tool can be launched from anywhere.
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.environ.get("NIMLAB_OUTPUT_DIR") or os.path.join(PROJECT_DIR, "output")

CLUSTER_CONFIG = os.path.join(PROJECT_DIR, "config_cluster.json")
SYSTEM_PROMPTS = os.path.join(PROJECT_DIR, "config_system_prompts.json")
SOUL_FILE = os.path.join(PROJECT_DIR, "soul.md")
# Data stores (endpoints, discovered/verified models, benchmarks, judge,
# memory) live in data/ and are owned by nimlab.store, the single source of
# truth for their paths and load/save. output/ holds generated files only
# (WAVs, report exports, page/spec caches).


def output_path(name):
    """Path for a generated file (WAVs, history, memory, reports)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, name)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    """Atomic write: a crash mid-write never leaves a half-written file."""
    folder = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_soul(path=SOUL_FILE):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "You are an autonomous cognitive entity."


# Defaults merged under whatever config_cluster.json holds, so older configs
# keep working and every new option has a documented value.
DEFAULT_CLUSTER = {
    "roles": {},
    "http_settings": {"timeout_sec": 60, "retries": 2, "backoff_sec": 1.5},
    "voice_settings": {
        "voice_name": "Magpie-Multilingual.EN-US.Aria",
        "auto_tts": False,
        "language": "en-US",
        "tts_url": "https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation.api.nvcf.nvidia.com/v1/audio/synthesize",
        "voice_profiles": ["Magpie-Multilingual.EN-US.Aria", "Magpie-Multilingual.EN-US.Jason"],
    },
    "mcp_settings": {
        "enabled": False,
        "url": "",
        "auth": {"style": "x-api-key", "header_name": "X-API-Key", "key_env": "MCP_API_KEY"},
        "protocol_version": "2025-06-18",
        "allowed_tools": [],
        "confirm_tool_calls": True,
        "max_tool_steps": 4,
        "max_calls_per_step": 3,
        "tool_timeout_sec": 20,
        "max_result_chars": 8000,
        "max_response_bytes": 1000000,
    },
    "memory_settings": {"recall_top_k": 3, "similarity_threshold": 0.45, "rerank_candidates": 10},
    "guard_settings": {"check_input": False, "check_output": False, "block_on_unsafe": True,
                       "translate_target": "English"},
    "routing_settings": {"use_intent_router": True, "show_route": True},
    "discovery_settings": {
        "page_ttl_hours": 72,
        "spec_ttl_hours": 72,
        "probe_workers": 3,
        "probe_timeout_sec": 20,
        "host_delays_sec": {"build.nvidia.com": 10, "docs.api.nvidia.com": 3, "api.ngc.nvidia.com": 1},
        "include_retired_in_sweep": False,
        "playground_uses_catalog": True,
    },
    "judge_settings": {
        "judges": ["mistralai/mistral-large-4-1t-a52b", "nvidia/nemotron-3-ultra-550b-a55b"],
        "repeats": 1,
        "judge_temperature": 0.0,
        "max_candidates_per_type": 16,
        "execute_generated_code": True,
        "code_timeout_sec": 10,
        "entity_combos": [],
        "candidate_overrides": {},
    },
}


def deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def ensure_config_files():
    """Write the starter config_cluster.json / config_system_prompts.json
    when they are missing, so a fresh unzip starts cleanly."""
    from . import defaults
    for path, data in ((CLUSTER_CONFIG, defaults.STARTER_CLUSTER), (SYSTEM_PROMPTS, defaults.STARTER_PROMPTS)):
        if not os.path.exists(path):
            try:
                save_json(path, data)
            except OSError:
                pass


def migrate_prompts(data):
    """Old prompt keys (main_brain, ...) -> the role keys; missing role
    prompts get the starter text. Returns (new_dict, changed)."""
    from . import defaults
    from .roles import LEGACY_MAP
    out = dict(data or {})
    changed = False
    for old, new in LEGACY_MAP.items():
        if old in out and new not in out:
            out[new] = out.pop(old)
            changed = True
    for k, v in defaults.STARTER_PROMPTS.items():
        if k not in out:
            out[k] = v
            changed = True
    return out, changed


def load_prompts():
    ensure_config_files()
    data = load_json(SYSTEM_PROMPTS, {}) or {}
    data = data if isinstance(data, dict) else {}
    new, changed = migrate_prompts(data)
    if changed:
        try:
            save_json(SYSTEM_PROMPTS, new)
        except OSError:
            pass
    return new


def _fleet_and_kinds():
    try:
        from .roles import kinds_from_store, verified_ids_readonly
        kinds, _ = kinds_from_store()
        return verified_ids_readonly(), kinds
    except Exception:  # a broken data/ file must never stop the config loading
        return [], {}


def migrate_cluster(raw, fleet=None, kinds=None):
    """Old cluster dict -> v3.2 roles (and judge combos). Returns
    (new_dict, changes); changes is empty when nothing moved."""
    from .roles import migrate_roles, migrate_combo_roles
    raw = dict(raw or {})
    roles, changes = migrate_roles(raw.get("roles") or {}, fleet, kinds)
    if roles != (raw.get("roles") or {}):
        raw["roles"] = roles
    else:
        changes = []
    js = raw.get("judge_settings")
    if isinstance(js, dict) and isinstance(js.get("entity_combos"), list):
        combos = []
        for c in js["entity_combos"]:
            if isinstance(c, dict):
                c = dict(c, roles=migrate_combo_roles(c.get("roles")))
            combos.append(c)
        if combos != js["entity_combos"]:
            raw["judge_settings"] = dict(js, entity_combos=combos)
            changes.append("judge entity_combos role keys renamed")
    return raw, changes


def load_cluster_config(path=CLUSTER_CONFIG):
    """Load config_cluster.json under the defaults. Roles saved by v3.1 or
    older are migrated to the 16 role keys and written back once, with the
    old file copied to data/legacy/ first."""
    if path == CLUSTER_CONFIG:
        ensure_config_files()
    raw = load_json(path, {}) or {}
    raw = raw if isinstance(raw, dict) else {}
    fleet, kinds = _fleet_and_kinds() if path == CLUSTER_CONFIG else ([], {})
    new, changes = migrate_cluster(raw, fleet, kinds)
    if changes and os.path.exists(path) and not os.environ.get("NIMLAB_CONFIG_READONLY"):
        try:
            from . import store
            legacy = os.path.join(store.data_dir(), "legacy")
            os.makedirs(legacy, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            save_json(os.path.join(legacy, f"config_cluster.pre-v3.2.{stamp}.json"), raw)
            save_json(path, new)
            print("[config] roles migrated to the 16 categories: " + "; ".join(changes[:6])
                  + (f" (+{len(changes) - 6} more)" if len(changes) > 6 else ""), file=sys.stderr)
        except OSError:
            pass
    return deep_merge(DEFAULT_CLUSTER, new)
