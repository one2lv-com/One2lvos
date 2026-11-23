"""Fix suggestions after a failure (v3.7.0).

When an ability, role, the memory store or MCP fails, the testbed reports it
accurately and, for an admin, offers a concrete fix it can make itself with
its self-admin tools: lower a timeout, switch a role to a verified model,
refresh a gRPC function ID, switch memory to the local store. A fix is only
offered here; it is applied by `self_apply_fix` after the admin says yes in a
later message, through the normal self-admin path (snapshot, undo, audit).

Each suggestion: {"tool": self-admin tool, "args": {...}, "what": one line
for the user}. A failure no self-admin tool can fix gets a `manual` hint
instead (for example `pkg install ffmpeg`, or a key to check), never a tool.
"""

import re

TIMEOUT_RX = re.compile(r"timed? ?out|timeout|read operation timed out", re.I)
FUNC_ID_RX = re.compile(r"function[ _-]?id|grpc refresh|no nvcf function|function .* not found|"
                        r"FAILED_PRECONDITION|NOT_FOUND.*function", re.I)
FFMPEG_RX = re.compile(r"ffmpeg", re.I)
AUTH_RX = re.compile(r"\b(401|403)\b|unauthori[sz]ed|forbidden|permission denied|PERMISSION_DENIED|"
                     r"UNAUTHENTICATED|invalid api key|bad key", re.I)
NOT_FOUND_RX = re.compile(r"\b404\b|model .*not found|not found for account|unknown model|does not exist", re.I)
BAD_REQ_RX = re.compile(r"\b(400|422)\b|bad request|unprocessable", re.I)
SERVER_RX = re.compile(r"\b5\d\d\b|bad gateway|service unavailable|internal server error|UNAVAILABLE", re.I)
UNREACH_RX = re.compile(r"unreachable|connection refused|could not connect|cannot connect|name or service not "
                        r"known|ORA-12\d\d\d|DPY-6\d\d\d|DPY-4011|network|offline|no route", re.I)
GRPC_ROLES = {"asr", "tts", "guard_translate"}
DEFAULT_TIMEOUT = 60


def enabled(cluster):
    return bool((cluster or {}).get("self_admin", {}).get("fix_suggestions", True))


def _verified_for(role, current, limit=2):
    """Up to `limit` verified (200-tested) models suited to the role, not the
    one that just failed. Empty when the catalog can't be read."""
    try:
        from . import roles as R, rolemenu
        verified, _ = rolemenu.model_lists()
        suited, possible, _other = R.candidates(role, verified)
    except Exception:  # noqa: BLE001 - no catalog: no switch to offer
        return []
    out = [m for m in suited + possible if m != current]
    return out[:limit]


def _switch(role, current, why):
    return [{"tool": "self_set_role", "args": {"role": role, "model": m},
             "what": f"switch {role} to {m} (verified){why}"} for m in _verified_for(role, current)]


def suggest(role, target, error, latency=0.0, cluster=None):
    """-> (fixes, manual). role: the role key ('memory' and 'mcp' work too);
    target: the model or tool that failed; error: the error text."""
    err = str(error or "")
    cluster = cluster or {}
    fixes, manual = [], []
    if role == "memory":
        if (cluster.get("memory_settings", {}).get("backend") or "auto") != "local":
            fixes.append({"tool": "self_memory_set", "args": {"key": "backend", "value": "local"},
                          "what": "switch long-term memory to the local store for now (Oracle stays set up)"})
        fixes.append({"tool": "self_run", "args": {"action": "memory_test"}, "what": "run the memory test"})
        if AUTH_RX.search(err) or "ORA-01017" in err:
            manual.append("check the MEM user name and password in ~/.config/nimlab/oracle_mem.json")
        return fixes, manual
    if role == "mcp":
        fixes.append({"tool": "self_run", "args": {"action": "mcp_test"}, "what": "run the MCP test"})
        if AUTH_RX.search(err):
            manual.append("check the MCP key (`nimlab mcp set-key`)")
        return fixes, manual
    if FFMPEG_RX.search(err) and re.search(r"not found|missing|install|no such", err, re.I):
        manual.append("install ffmpeg (`pkg install ffmpeg` on Termux, your package manager elsewhere)")
        return fixes, manual
    if FUNC_ID_RX.search(err) or (role in GRPC_ROLES and NOT_FOUND_RX.search(err) and "grpc" in err.lower()):
        fixes.append({"tool": "self_run", "args": {"action": "grpc_refresh"},
                      "what": f"refresh the gRPC function IDs{f' (for {target})' if target else ''}"})
        return fixes, manual
    if AUTH_RX.search(err):
        manual.append("check the NVIDIA key (`nimlab setup key`); keys aren't changed through chat")
        fixes += _switch(role, target, "")[:1]
        return fixes, manual
    if TIMEOUT_RX.search(err):
        now = int(cluster.get("http_settings", {}).get("timeout_sec") or DEFAULT_TIMEOUT)
        lower = 20 if now > 20 else max(5, now // 2)
        if lower < now:
            fixes.append({"tool": "self_set_setting",
                          "args": {"section": "http_settings", "key": "timeout_sec", "value": lower},
                          "what": f"lower the model timeout from {now}s to {lower}s"})
        if role == "reasoning":
            rs = cluster.get("routing_settings", {})
            if rs.get("reasoning_gate") is False:
                fixes.append({"tool": "self_set_setting",
                              "args": {"section": "routing_settings", "key": "reasoning_gate", "value": True},
                              "what": "turn the reasoning gate back on, so only long or analysis tasks use it"})
        fixes += _switch(role, target, " that may answer faster")
        return fixes, manual
    if NOT_FOUND_RX.search(err) or SERVER_RX.search(err) or BAD_REQ_RX.search(err):
        if role in GRPC_ROLES and BAD_REQ_RX.search(err):
            fixes.append({"tool": "self_run", "args": {"action": "grpc_refresh"},
                          "what": "refresh the gRPC function IDs (this model may need gRPC)"})
        fixes += _switch(role, target, "")
        return fixes, manual
    if UNREACH_RX.search(err):
        fixes += _switch(role, target, "")[:1]
        manual.append("check the network connection")
    return fixes, manual


def offer_text(fixes, manual, admin, ids=None):
    """The persona's instructions for offering the fixes."""
    lines = []
    if fixes and admin:
        opts = "; ".join(f"[{i}] {f['what']}" for i, f in zip(ids or range(1, len(fixes) + 1), fixes))
        lines.append("You can fix this yourself if the user agrees. Offer these as a short question: " + opts +
                     ". Say it can be undone. Change nothing now. Only if the user says yes in their next message, "
                     "call self_apply_fix with the fix_id of the option they chose.")
    elif fixes:
        lines.append("Just report it; the user can't change the setup from here, so don't offer to change "
                     "settings.")
    if manual:
        lines.append("Something the user can do: " + "; ".join(manual) + ".")
    return " ".join(lines)
