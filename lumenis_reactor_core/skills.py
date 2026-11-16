"""
Skill format and guardrails (items 6 and 8).

Each skill is skills/<name>.md with a YAML front matter block:
    name, version, description, triggers[], tools[], risk_tier (L0-L3), guardrails[]
load_all() reads and validates every file. A skill is refused (not loaded) when:
  - a required field is missing, or the name does not match the file name
  - risk_tier is not L0-L3, or is LOWER than the highest real tier of the tools it lists
    (checked against tool_engine.tier_of, so a skill cannot hide a destructive tool behind "L0")
  - it names a guardrail the reactor does not know (a typo would otherwise silently drop a guard)
Guardrails are enforced where the work happens (memory, tool engine, lobby, revert); this module is the
registry that says which ones each skill promises.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
REQUIRED = ("name", "version", "description", "triggers", "tools", "risk_tier", "guardrails")
TIERS = ("L0", "L1", "L2", "L3")
GUARDRAILS = {
    "read_only": "changes nothing",
    "raw_values": "results reach the council as raw numbers, labelled real output",
    "keys_scrubbed": "key-like strings are redacted from args and results",
    "owner_only": "only One2lv (Cloudflare Access / Discord owner ID / local machine) can use it",
    "owner_only_broadcast": "broadcasting to the lobby is owner-only",
    "two_step_confirm": "L3 actions need a second confirmation code",
    "backup_first": "a backup is made before anything changes",
    "lumenis_chat_only": "only offered in the owner's lumenis-chat",
    "no_canonical_without_owner": "outside results never go straight into canonical (stable) memory",
    "dreams_stay_dreams": "dream material is never stored or recalled as fact",
    "temporary_never_promoted": "temporary memory expires and is never promoted",
    "cost_limited": "per-hour call and cost limits apply",
    "nvidia_hosts_only": "only NVIDIA's API hosts are contacted",
    "refused_tools_stay_refused": "tools on the refused list never run",
    "export_roots_only": "file export reads only from allowed folders",
    "local_port_only": "only touches the local lobby on port 8006",
    "honest_agent_count": "reports the agents the code really has",
    "vision_lag_no_live_play": "no live game inputs: vision lags 2-4 s",
    "seats_attributed": "every part of a swarm reply names the seat and model that wrote it",
    "no_shell_syntax": "commands run without a shell; pipes, redirects and chaining are L3",
    "not_built_yet": "the skill is a planned capability: no reactor code performs it yet",
}
_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _tool_tier(tool: str) -> int:
    """Real tier of a tool name. Tool-engine names are checked against the engine; others are
    reactor-internal actions with fixed tiers."""
    internal = {"compass.recall_facts": 0, "compass.store_fact": 1, "memory_hub.compile": 1, "soul.rules": 0,
                "live_status.snapshot": 0, "lobby.status": 0, "lobby.start": 2, "lobby.broadcast": 2,
                "git.revert_to_known_good": 3, "gaming.coach": 0, "gaming.match": 0, "gaming.drill": 1,
                "council.oracle": 0, "council.forge": 0, "council.swarm": 0, "hermes.maton_bridge": 2,
                "skills.write": 2, "tools.write": 3}
    if tool in internal:
        return internal[tool]
    if tool.endswith(".*"):
        return 3
    try:
        from . import tool_engine as te
        return te.tier_of(tool)
    except Exception:
        return 3


def parse(path: Path) -> Dict:
    import yaml
    m = _FM.match(path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError("no front matter")
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("front matter is not a mapping")
    return data


def validate(data: Dict, file_stem: str) -> List[str]:
    errs = [f"missing {k}" for k in REQUIRED if k not in data or data[k] in (None, "", [])]
    if errs:
        return errs
    if data["name"] != file_stem:
        errs.append(f"name {data['name']!r} does not match file {file_stem!r}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(data["version"])):
        errs.append("version must look like 1.0.0")
    tier = str(data["risk_tier"])
    if tier not in TIERS:
        errs.append(f"risk_tier {tier!r} is not L0-L3")
    else:
        worst = max((_tool_tier(t) for t in data["tools"]), default=0)
        if TIERS.index(tier) < worst:
            errs.append(f"risk_tier {tier} is lower than its tools' highest tier L{worst}")
    unknown = [g for g in data["guardrails"] if g not in GUARDRAILS]
    if unknown:
        errs.append(f"unknown guardrails: {unknown}")
    return errs


def load_all(directory: Path = SKILLS_DIR) -> Dict[str, List[Dict]]:
    loaded, refused = [], []
    for f in sorted(directory.glob("*.md")):
        try:
            d = parse(f)
            errs = validate(d, f.stem)
        except Exception as e:
            d, errs = {}, [f"unreadable: {e}"]
        if errs:
            refused.append({"file": f.name, "errors": errs})
        else:
            loaded.append({k: d[k] for k in REQUIRED})
    return {"loaded": loaded, "refused": refused}


def match(text: str) -> List[str]:
    t = (text or "").lower()
    return [s["name"] for s in load_all()["loaded"] if any(str(tr).lower() in t for tr in s["triggers"])]
