"""The entity: soul.md persona + 16 role backends + memory + MCP tools.

Non-interactive core used by both orchestrator_testbed.py (interactive) and
the judge (scripted). Every network call goes through nimlab.api (model
backends) or nimlab.mcp (MCP-tool backends).

A role is backed by either a model/endpoint or a tool on the connected MCP
server (see nimlab/roles.py for the config shape). run_role() is the one
place that turns a role and its inputs into a call; turn() routes a chat
turn to a role and runs it.
"""

import os
import re
import threading
import time

from . import config, intent, rolemcp, roles as R
from . import selfadmin as SA
from .api import (ModelResult, NimClient, OCR_PROMPT, file_to_data_url, image_to_data_url, play_audio, save_bytes,
                  save_wav)
from .mcp import (LOAD_TOOLS, MCPClient, MCPError, ToolPolicy, native_calls_as_text, run_tool_loop,
                  strip_tool_markup, tools_prompt)
from .memory import MemoryCore, is_error_text

# "what were we just talking about?", "do you remember ...", "on the voice call earlier"
RECALL_ASK = re.compile(
    r"\b(remember|recall|remind me|we (were |was )?(just )?(talk|talking|discuss|discussing|said|chat|chatting)"
    r"|what (did|were) (we|i|you) (say|said|talk|talking|discuss|mention)|earlier|last time|before"
    r"|previous(ly)?|voice call|our (last |earlier )?(call|chat|conversation|talk))\b", re.IGNORECASE)

MEMORY_SEARCH_TOOL = {
    "name": "memory_search",
    "description": ("Search your own long-term memory (built in; runs in-process against your memory store, not "
                    "an MCP tool). Relevant memories are already recalled for you each turn; use this only for a "
                    "deeper lookup, e.g. a specific name, ID, number or phrase the recalled memories missed. "
                    "mode: semantic (meaning), keyword (exact words, names, IDs, numbers; quote a phrase), or both."),
    "inputSchema": {"type": "object", "additionalProperties": False, "required": ["query"], "properties": {
        "query": {"type": "string", "description": "What to look for."},
        "mode": {"type": "string", "enum": ["semantic", "keyword", "both"], "default": "both"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}}},
}

CHART_PROMPT = ("Parse this chart or plot. Give the chart type, title, axis labels and units, then every series "
                "and data point as a table, then one sentence on the main trend.")
VIDEO_PROMPT = "Describe what happens in this video, in order, with timestamps where you can."
AUDIO_PROMPT = ("Describe this audio. For music: genre, tempo, key, instruments and mood. For ambient sound: "
                "the sources, the setting and what happens.")
VISION_PROMPT = "Analyze this image thoroughly."
PROBE_TEXT = "Reply with the single word: ready"
SAMPLES_DIR = os.path.join(config.PROJECT_DIR, "samples")
TEXT_ROLES = ("intent_router", "persona", "reasoning", "coding")
MEDIA_ROLES = ("vision", "ocr", "chart_parser", "video", "asr", "omni_audio")


def _msg_text(m):
    c = (m or {}).get("content")
    if isinstance(c, list):
        c = " ".join(str(p.get("text") or "") for p in c if isinstance(p, dict))
    c = str(c or "")
    if (m or {}).get("role") == "user" and "User Input: " in c:
        c = c.rsplit("User Input: ", 1)[1]   # the turn's own words, not the context blocks
    return c


def _norm(t):
    return re.sub(r"[^\w]+", " ", (t or "").lower()).strip()


def context_index(history):
    """The normalized user and assistant messages already in the context."""
    if not history:
        return None
    users, assistants = set(), set()
    for m in history:
        t = _norm(_msg_text(m))
        if not t:
            continue
        (users if (m or {}).get("role") == "user" else assistants).add(t)
    return (users, assistants) if (users or assistants) else None


def in_context(text, idx):
    """True when a recalled memory is a turn already in this conversation's
    short-term context (the same user words or the same reply), or a fact
    taken from a user message that is."""
    from . import ltm
    if not idx:
        return False
    users, assistants = idx
    u, a = ltm.split_turn(text)
    nu, na = _norm(u), _norm(a)
    if a:
        return (nu and nu in users) or (na and na in assistants)
    if len(nu) >= 12:
        return any(nu == x or nu in x for x in users)
    return False


def fit_budget(hits, max_chars, per_hit=800):
    """Keep recall within the prompt budget: each memory cut to per_hit
    characters, then as many as fit in max_chars (always at least one)."""
    out, used = [], 0
    for h in hits:
        t = h[1] or ""
        if len(t) > per_hit:
            t = t[:per_hit - 1] + "\u2026"
            h = (h[0], t) + tuple(h[2:])
        if max_chars and out and used + len(t) > max_chars:
            break
        out.append(h)
        used += len(t)
    return out


def parse_safety(text):
    """Guard model reply -> (safe: bool|None, reason). Understands
    NemoGuard JSON ({"User Safety": "unsafe", "Safety Categories": ...})
    and plain SAFE/UNSAFE answers."""
    t = (text or "").strip()
    low = t.lower()
    m = re.search(r'"(?:user|response) safety"\s*:\s*"(safe|unsafe)"', low)
    if m:
        cats = re.search(r'"safety categories"\s*:\s*"([^"]*)"', t, re.I)
        return m.group(1) == "safe", (cats.group(1) if cats else m.group(1))
    if re.search(r"\bunsafe\b|\bnot safe\b|\bblock(ed)?\b", low):
        return False, t[:200]
    if re.search(r"\bsafe\b|\ballowed\b|\bon[- ]topic\b", low):
        return True, t[:200]
    return None, t[:200]



def fix_offer(role, target, error, latency=0.0, cluster=None):
    """The fix part of a failure note (v3.7.0): suggestions from nimlab.fixes,
    registered for an admin caller so self_apply_fix can apply one after a
    yes. Non-admins (or fix suggestions off) get the report only."""
    from . import fixes as FX
    if not FX.enabled(cluster):
        return ""
    fx, manual = FX.suggest(role, target, error, latency, cluster)
    try:
        from . import selfadmin as SA
        admin = SA.current().admin and SA.settings(cluster).get("enabled", True)
        ids = SA.offer_fixes(fx) if admin else []
    except Exception:  # noqa: BLE001 - suggestions are a bonus, never a crash
        admin, ids = False, []
    return FX.offer_text(fx, manual, bool(ids), ids)


def ability_failure_note(role, target, result, ok_steps=(), cluster=None):
    """Context for the persona when one ability failed: name exactly which
    ability (and model) failed and why, say which steps worked, and tell it
    to still answer the user's actual message. The user may hear that the
    ability failed; they must not hear that their own message failed."""
    err = (result.error or "no reply").strip()
    secs = result.latency or 0
    low = err.lower()
    if "timed out" in low or "timeout" in low:
        what = f"timed out after {secs:.0f}s" if secs >= 1 else "timed out"
    else:
        what = f"failed ({err[:200]})"
    model = f" ({target})" if target and target != "-" else ""
    offer = fix_offer(role, target, err, secs, cluster)
    worked = [R.label(k) for k in dict.fromkeys(ok_steps) if k != role]
    worked_txt = (" These steps worked: " + ", ".join(worked) + ".") if worked else ""
    return (f"Your {R.label(role)} ability{model} {what}. It was an optional extra step for this turn, not the "
            f"user's message failing.{worked_txt} Answer the user's actual message yourself as well as you can. "
            f"Mention the failure briefly and accurately, naming it as the {R.label(role).lower()} "
            f"{'timing out' if 'timed out' in what else 'failing'}; don't say anything else failed (their message, "
            "voice, hearing or speaking) unless it did." + (" " + offer if offer else ""))

def ltm_short(ms):
    from .memmenu import short_status
    try:
        return short_status(ms)
    except Exception:  # noqa: BLE001
        return "?"


_FB_LOCAL = threading.local()   # v3.8.3: a persona stream that failed, for chat_step's fallbacks


class Entity:
    def __init__(self, cluster=None, prompts=None, soul=None, client=None, roles_override=None,
                 memory=True, confirm_fn=None, log=print, role_mcp=None, fetch=None):
        self.cluster = cluster if cluster is not None else config.load_cluster_config()
        if roles_override:
            self.cluster = config.deep_merge(self.cluster, {"roles": R.migrate_combo_roles(roles_override)})
        self.prompts = prompts if prompts is not None else config.load_prompts()
        self.soul = soul if soul is not None else config.load_soul()
        self.client = client or NimClient(cluster=self.cluster)
        self.log = log
        self.confirm_fn = confirm_fn
        self.fetch = fetch
        self._role_mcp_given = role_mcp
        self.mcp = None
        self.role_mcp = None
        self.tools_error = None
        self._build_mcp()
        self.memory = MemoryCore(self.client, self._embed_label(), embed_fn=self._embed_fn(),
                                 settings=self.cluster.get("memory_settings"), log=self.log) if memory else None
        self._snapshot_config(from_file=cluster is None)

    # -- config -----------------------------------------------------------
    @property
    def roles(self):
        return self.cluster.get("roles", {})

    def spec(self, key):
        return R.normalize(self.roles.get(key), key)

    def model(self, key):
        return R.model_of(self.roles.get(key))

    def is_set(self, key):
        return R.is_set(self.roles.get(key))

    def backend(self, key):
        return self.spec(key)["backend"]

    def target(self, key):
        return R.describe(self.roles.get(key))

    @property
    def mcp_settings(self):
        return self.cluster.get("mcp_settings", {})

    def _build_mcp(self):
        s = self.mcp_settings
        self.mcp = MCPClient(s) if s.get("enabled") and s.get("url") else None
        # v3.8.3: a new client has no tool list yet; ensure_tools() fetches it on first use
        self._tools_at = None
        self._tools_err_at = None
        self._tools_stale = False
        if self._role_mcp_given is not None:
            self.role_mcp = self._role_mcp_given
        elif s.get("url"):
            # role tools may return audio/images, so they get a larger cap
            rs = dict(s, max_response_bytes=int(s.get("role_max_response_bytes", 25_000_000)),
                      tool_timeout_sec=float(s.get("role_tool_timeout_sec", 120)))
            self.role_mcp = MCPClient(rs)
        else:
            self.role_mcp = None

    def _embed_label(self):
        sp = self.spec("embedding")
        if sp["backend"] == R.MCP:
            return f"mcp:{sp.get('tool') or ''}"
        return sp.get("model") or ""

    def _embed_fn(self):
        if self.backend("embedding") != R.MCP:
            return None

        def fn(text, input_type):
            r = self.run_role("embedding", text=text, input_type=input_type)
            return r.data if r.ok else None
        return fn

    def _snapshot_config(self, from_file=True):
        """Remember what was loaded: save_cluster writes only changed
        sections, and refresh_memory_settings() notices edits made by other
        processes (setup, `memory set`, the Memory menu)."""
        import copy
        self._loaded_sections = copy.deepcopy(self.cluster)
        self._from_file = from_file
        try:
            self._cfg_mtime = os.path.getmtime(config.CLUSTER_CONFIG)
        except OSError:
            self._cfg_mtime = None

    def refresh_memory_settings(self):
        """3.7.1: a long-running process (service, Telegram bot, terminal chat)
        follows memory_settings changes in config_cluster.json on the next
        turn, so the pipeline never runs on settings the menu no longer
        shows. Returns True when the memory settings changed."""
        if self.memory is None or not getattr(self, "_from_file", False):
            return False
        try:
            m = os.path.getmtime(config.CLUSTER_CONFIG)
        except OSError:
            return False
        if m == getattr(self, "_cfg_mtime", None):
            return False
        self._cfg_mtime = m
        try:
            fresh = (config.load_cluster_config() or {}).get("memory_settings") or {}
        except Exception:  # noqa: BLE001 - a half-written file: try next turn
            return False
        if fresh == (self.cluster.get("memory_settings") or {}):
            return False
        import copy
        self.cluster["memory_settings"] = copy.deepcopy(fresh)
        self._loaded_sections["memory_settings"] = copy.deepcopy(fresh)
        self.memory.reconfigure(fresh)
        self._mem_log("settings changed on disk: memory reloaded (" + ltm_short(fresh) + ")")
        return True

    def reload(self):
        self.cluster = config.load_cluster_config()
        self.prompts = config.load_prompts()
        self.soul = config.load_soul()
        self.client.cluster = self.cluster
        self._build_mcp()
        if self.memory is not None:
            self.memory.embed_model = self._embed_label()
            self.memory.embed_fn = self._embed_fn()
            self.memory.reconfigure(self.cluster.get("memory_settings"))
        self._snapshot_config()

    def policy(self):
        """The MCP tool policy: every tool the server exposes, minus the optional
        local allowed_tools / blocked_tools overrides; optional confirmation.
        See nimlab.mcp.ToolPolicy."""
        return ToolPolicy.from_settings(self.mcp_settings, self.confirm_fn, agent=self.agent_name())

    def agent_name(self):
        """The entity's name: agent_settings.name, else a custom memory profile
        name (not the default TESTBED), else the name in soul.md."""
        n = ((self.cluster.get("agent_settings") or {}).get("name") or "").strip()
        if n:
            return n
        prof = self.memory_profile()
        if prof and prof != "TESTBED":
            return prof
        try:
            from . import unified
            return unified.soul_name(self.soul or "") or ""
        except Exception:  # noqa: BLE001
            return ""

    def memory_profile(self):
        """The long-term memory profile name (Oracle profile_id), default TESTBED."""
        try:
            from . import ltm
            lt = ltm.settings_from(self.cluster.get("memory_settings", {}))
            return ((lt.get("oracle") or {}).get("profile_id") or "TESTBED").upper()
        except Exception:  # noqa: BLE001
            return "TESTBED"

    def mcp_exposure(self):
        """(exposed tools, allowed names, blocked {name: reason}) for the chat tool loop."""
        self.ensure_tools()
        tools = list((self.mcp.tools if self.mcp else []) or [])
        ex = self.policy().exposure(tools)
        return tools, ex["allowed"], ex["blocked"]

    # -- built-in tools: run in-process, never over MCP --------------------
    def builtin_tools(self):
        """memory_search: an explicit, deeper lookup in the entity's own long-term
        memory, over the same connection the automatic recall uses. Offered only
        when memory_settings.long_term.memory_search_tool is on (default) and a
        memory store is configured."""
        if self.memory is None or self.memory.settings.get("backend") == "off":
            return []
        if self.memory_search_mode() == "off":
            return []
        return [MEMORY_SEARCH_TOOL]

    def memory_search_mode(self):
        """memory_settings.long_term.memory_search_tool: "auto" (default) offers
        it whenever the persona has a tool loop anyway, "on" always (the persona
        then answers without token streaming), "off" never."""
        if self.memory is None:
            return "off"
        v = self.memory.settings.get("memory_search_tool", "auto")
        if v is True:
            return "on"
        if v is False or v is None:
            return "off"
        v = str(v).lower()
        return v if v in ("on", "off", "auto") else "auto"

    def run_builtin_tool(self, name, args):
        if name != MEMORY_SEARCH_TOOL["name"]:
            return {"content": [{"type": "text", "text": f"No built-in tool {name}."}], "isError": True}
        return {"content": [{"type": "text", "text": self.memory_search_text(args)}], "isError": False}

    # -- MCP --------------------------------------------------------------
    def refresh_tools(self):
        """initialize + tools/list for the chat tool loop ([] on failure)."""
        self.ensure_tools(force=True)
        return list(self.mcp.tools or []) if (self.mcp and not self.tools_error) else []

    # -- v3.8.3: MCP tools load lazily, on every channel -------------------
    def _tools_ttl(self):
        try:
            return max(30.0, float(self.mcp_settings.get("tools_ttl_sec", 600)))
        except (TypeError, ValueError):
            return 600.0

    def _tools_lock(self):
        lk = self.__dict__.get("_tools_lock_obj")
        if lk is None:
            lk = self.__dict__.setdefault("_tools_lock_obj", threading.RLock())
        return lk

    def ensure_tools(self, force=False):
        """The MCP tool list, fetched on first use and cached.

        Before 3.8.3 only terminal chat and doctor fetched the list, so the
        scheduler, heartbeat, the OpenAI server (Telegram, voice calls, inline)
        and a voice call opened straight from the menu offered Quill no MCP
        tools at all. Now every path that builds a tool loop calls this first.
        Thread-safe; refreshed after tools_ttl_sec (default 600 s) or after an
        MCP error marked it stale; after a failed fetch it waits 60 s before
        trying again so a down server never slows every turn. The error stays
        in tools_error for doctor and /health. -> [tool]."""
        m = self.mcp
        if m is None:
            return []
        if not callable(getattr(m, "list_tools", None)):
            return list(getattr(m, "tools", None) or [])    # a test double with a fixed list
        with self._tools_lock():
            now = time.monotonic()
            at = self.__dict__.get("_tools_at")
            if not force:
                if at is not None and not self.__dict__.get("_tools_stale") and now - at < self._tools_ttl():
                    return list(m.tools or [])
                err_at = self.__dict__.get("_tools_err_at")
                if err_at is not None and now - err_at < 60.0 and not self.__dict__.get("_tools_stale"):
                    return list(m.tools or [])
            try:
                m.list_tools()
                self.tools_error = None
                self._tools_at, self._tools_err_at, self._tools_stale = now, None, False
            except Exception as e:  # noqa: BLE001 - MCP down: keep the reason, never break the turn
                self.tools_error = str(e)[:300]
                self._tools_err_at, self._tools_stale = now, False
                if callable(self.log):
                    try:
                        self.log(f"[MCP] tool list unavailable: {self.tools_error}")
                    except Exception:  # noqa: BLE001
                        pass
            return list(m.tools or [])

    def mark_tools_stale(self):
        """After an MCP error the next turn fetches the tool list again."""
        self._tools_stale = True

    def tools_status(self):
        """For doctor and /health: dict(enabled, loaded, count, error, age_sec)."""
        m = self.mcp
        at = self.__dict__.get("_tools_at")
        return {"enabled": m is not None, "loaded": at is not None,
                "count": len(getattr(m, "tools", None) or []) if m else 0,
                "error": self.tools_error,
                "age_sec": round(time.monotonic() - at, 1) if at is not None else None}

    def prompt_checks(self, log=print, migrate=True):
        """Startup: rewrite (once, with a backup) prompt sentences that tell a
        model to call a tool that does not exist, then lint what is left.
        -> [warning]."""
        from . import config, environment as ENV, store
        avail = ENV.available_tools(self)
        if migrate and self.cluster.get("routing_settings", {}).get("migrate_prompts", True):
            mark = os.path.join(store.data_dir(), "prompts_migrated_371.json")
            if not os.path.exists(mark) and os.path.exists(config.SYSTEM_PROMPTS):
                try:
                    rep = ENV.migrate_prompts_file(config.SYSTEM_PROMPTS, avail, log=log)
                    if rep:
                        self.prompts = config.load_prompts()
                    config.save_json(mark, {"done": True, "report": rep or {}})
                except (OSError, ValueError) as e:
                    log(f"[prompts] could not migrate {config.SYSTEM_PROMPTS}: {e}")
        warns = ENV.lint_entity(self)
        for w in warns:
            log(f"[prompts] warning: {w}")
        return warns

    def mcp_startup_line(self, tools=None):
        """'[MCP] 214 tools from URL, all available'"""
        from .mcp import exposure_line
        tools = list(tools if tools is not None else ((self.mcp.tools if self.mcp else []) or []))
        return exposure_line(tools, self.policy(), self.mcp.url if self.mcp else "")

    def memory_startup_line(self):
        """'[memory] long-term memory: oracle MEM.QUILL_MEMORIES, 120 memories, automatic recall + store'"""
        m = self.memory
        if m is None:
            return "[memory] long-term memory is off"
        try:
            n = m.count()
        except Exception:  # noqa: BLE001
            n = None
        where = m.where()
        modes = [w for w, on in (("automatic recall", m.settings.get("auto_recall", True)),
                                 ("store", m.settings.get("auto_store", True))) if on]
        st = f"offline ({str(m.offline)[:120]})" if m.offline else (f"{n} memories" if n is not None else "connected")
        return (f"[memory] long-term memory: {m.backend_name}{' ' + where if where else ''}, {st}, "
                f"{' + '.join(modes) or 'recall and store off'}; memory_search tool: {self.memory_search_mode()}")

    def list_role_tools(self):
        """(tools, error) from the connected MCP server, for role backends.
        Works whether or not the chat tool loop is enabled."""
        if not self.role_mcp:
            return [], "no MCP server URL is set (Settings, option 2)"
        try:
            return self.role_mcp.list_tools(), None
        except MCPError as e:
            return [], str(e)

    def _download(self, url):
        if self.fetch:
            return self.fetch(url)
        res = self.client.http.request("GET", url, None, {"Accept": "*/*"}, 60, max_bytes=20 * 1024 * 1024)
        if not res.ok:
            raise RuntimeError(res.error or f"HTTP {res.status}")
        return res.body

    # -- prompts ----------------------------------------------------------
    def role_prompt(self, role):
        if role in self.prompts:
            return self.prompts[role] or ""
        for old, new in R.LEGACY_MAP.items():
            if new == role and old in self.prompts:
                return self.prompts[old] or ""
        return ""

    @property
    def persona_final(self):
        """v3.4: the persona writes every reply; other roles are abilities."""
        return bool(self.cluster.get("routing_settings", {}).get("persona_final", True))

    def soul_for(self, role):
        """soul.md is the persona's identity. Abilities get only their own role
        prompt when the persona speaks for them (routing_settings.
        soul_in_abilities turns it back on); in the older mode, where a role
        answers the user itself, every role keeps the soul."""
        if role == "persona" or not self.persona_final:
            return True
        return bool(self.cluster.get("routing_settings", {}).get("soul_in_abilities", False))

    @property
    def lazy_tools(self):
        """mcp_settings.tool_definitions: "full" (every schema in every prompt, the 3.8.3 default) or
        "lazy" (a one-line index; schemas load on demand with load_tools)."""
        return str((self.mcp_settings or {}).get("tool_definitions", "full")).lower() == "lazy"

    def build_system_prompt(self, role="persona", with_tools=True, extra=None):
        role = R.LEGACY_MAP.get(role, role) if role not in R.BY_KEY else role
        tools_desc = ""
        box = SA.active_box()
        if with_tools and box is not None and box.tools:
            # box.tools holds only what the policy lets this model see
            tools_desc = tools_prompt(box.tools, ["*"], lazy=self.lazy_tools) + SA.prompt_note(bool(box.admin_names))
        elif with_tools and self.mcp and self.mcp.tools:
            _t, allowed, _b = self.mcp_exposure()
            tools_desc = tools_prompt([t for t in self.mcp.tools if t.get("name") in set(allowed)], ["*"],
                                      lazy=self.lazy_tools) \
                if allowed else ""
        soul = f"=== SOUL / IDENTITY SPECIFICATION ===\n{self.soul}\n\n" if self.soul_for(role) else ""
        out = f"{soul}=== FUNCTION ROLE: {R.label(role).upper()} ===\n{self.role_prompt(role)}{tools_desc}"
        if self.cluster.get("routing_settings", {}).get("environment_block", True):
            from . import environment as ENV
            if box is not None and with_tools:
                names = [t["name"] for t in box.tools if t.get("name") not in box.admin_names]
            elif with_tools and tools_desc:
                names = self.mcp_exposure()[1]
            else:
                names = []
            env = ENV.environment_block(self, role, tool_names=names)
            if env:
                out += "\n\n" + env
        if extra:
            out += f"\n\n{extra}"
        return out

    # -- the one dispatcher ---------------------------------------------------
    def run_role(self, key, **inp):
        """Run one role on its inputs. Returns a ModelResult; .files lists any
        outputs saved to output/. Inputs by role: text / messages (text
        roles), image / video / audio (+ prompt), prompt (generation),
        query + passages (reranker), text + task + target_language (guard)."""
        key = R.LEGACY_MAP.get(key, key) if key not in R.BY_KEY and key not in R.EXTRA_ROLES else key
        sp = self.spec(key)
        if not R.is_set(sp):
            what = "MCP tool" if sp["backend"] == R.MCP else "model"
            return ModelResult(False, error=f"role '{R.label(key)}' is not set (no {what} chosen)")
        if sp["backend"] == R.MCP:
            return self._run_mcp(key, sp, inp)
        handler = getattr(self, f"_m_{key}", None) or self._m_text
        from . import perf
        with perf.stage(key, target=sp.get("model") or sp.get("function_id") or sp.get("tool")) as st:
            try:
                res = handler(key, sp, inp)
            except perf.Timeout as e:
                res = ModelResult(False, error=str(e), status=504)
            except (OSError, ValueError) as e:
                res = ModelResult(False, error=str(e))
            st["ok"] = bool(getattr(res, "ok", False))
            if not st["ok"]:
                st["note"] = (getattr(res, "error", "") or "")[:200]
        return res

    # -- MCP backend ------------------------------------------------------
    def _mcp_inputs(self, key, sp, inp):
        inputs = dict(inp)
        if "text" not in inputs and inputs.get("messages"):
            last = [m for m in inputs["messages"] if m.get("role") == "user"]
            inputs["text"] = last[-1]["content"] if last else ""
        if key == "tts":
            vc = sp.get("voice_clone") or {}
            if vc.get("path") and "reference_audio" not in inputs:
                inputs["reference_audio"] = vc["path"]
                if vc.get("transcript"):
                    inputs.setdefault("reference_text", vc["transcript"])
            inputs.setdefault("voice", self.cluster.get("voice_settings", {}).get("voice_name"))
            inputs.setdefault("language", self.cluster.get("voice_settings", {}).get("language"))
        return inputs

    def _run_mcp(self, key, sp, inp):
        if not self.role_mcp:
            return ModelResult(False, error="role is MCP-backed but no MCP server URL is set")
        inputs = self._mcp_inputs(key, sp, inp)
        arg_map = sp.get("arg_map") or {}
        if not arg_map:
            tool = self.role_mcp.tool(sp["tool"]) if self.role_mcp.tools else None
            if tool is None:
                try:
                    self.role_mcp.list_tools()
                    tool = self.role_mcp.tool(sp["tool"])
                except MCPError:
                    tool = None
            arg_map = rolemcp.auto_arg_map(key, tool) if tool else {}
        from . import perf
        with perf.stage(key, target=sp.get("tool")):
            out = rolemcp.call_role_tool(self.role_mcp, sp["tool"], arg_map, inputs, fetch=self._download,
                                         prefix=key)
        if not out["ok"]:
            return ModelResult(False, latency=out["latency"], error=out["error"], files=out["files"])
        res = ModelResult(True, text=out["text"], latency=out["latency"], files=out["files"],
                          raw={"arguments": out["arguments"], "notes": out["notes"]})
        if key == "embedding":
            vec = rolemcp.parse_vector(out["text"])
            if not vec:
                return ModelResult(False, latency=out["latency"], error="MCP tool did not return a vector")
            res.data = vec
        elif key == "reranker":
            order = rolemcp.parse_rankings(out["text"], len(inputs.get("passages") or []))
            if order is None:
                return ModelResult(False, latency=out["latency"], error="MCP tool did not return rankings")
            res.data = order
        elif key in ("tts", "audio_gen", "image_gen"):
            res.data = out["files"]
            want = R.BY_KEY[key].output
            if not out["files"]:
                res.ok = False
                res.error = f"MCP tool returned no {want} (text: {out['text'][:160]!r})"
        return res

    # -- model backends ---------------------------------------------------
    def _url(self, sp):
        return sp.get("endpoint") or None

    def _m_text(self, key, sp, inp):
        msgs = inp.get("messages") or [{"role": "user", "content": inp.get("text", "")}]
        system = inp.get("system")
        if system is None:
            system = self.build_system_prompt(key, with_tools=inp.get("with_tools", False))
        full = ([{"role": "system", "content": system}] if system else []) + msgs
        return self.client.chat(sp["model"], full, temperature=inp.get("temperature", 0.7),
                                max_tokens=inp.get("max_tokens", 1024), url=self._url(sp),
                                timeout=inp.get("timeout"))

    def _image_chat(self, key, sp, inp, prompt, temperature=0.2, max_tokens=1024, system=True):
        url = image_to_data_url(inp.get("image", ""))
        if not url:
            return ModelResult(False, error=f"image not found: {inp.get('image')}")
        msgs = []
        if system:
            msgs.append({"role": "system", "content": self.build_system_prompt(key, with_tools=False)})
        msgs.append({"role": "user", "content": [{"type": "text", "text": prompt},
                                                 {"type": "image_url", "image_url": {"url": url}}]})
        return self.client.chat(sp["model"], msgs, temperature, max_tokens, url=self._url(sp))

    def _m_vision(self, key, sp, inp):
        return self._image_chat(key, sp, inp, inp.get("prompt") or VISION_PROMPT, max_tokens=512)

    def _m_ocr(self, key, sp, inp):
        return self._image_chat(key, sp, inp, inp.get("prompt") or OCR_PROMPT, temperature=0.0, system=False)

    def _m_chart_parser(self, key, sp, inp):
        p = CHART_PROMPT + (f"\nAlso answer: {inp['prompt']}" if inp.get("prompt") else "")
        return self._image_chat(key, sp, inp, p, temperature=0.0)

    def _m_video(self, key, sp, inp):
        url = file_to_data_url(inp.get("video", ""), "video/mp4")
        if not url:
            return ModelResult(False, error=f"video not found: {inp.get('video')}")
        return self.client.chat_media(sp["model"], inp.get("prompt") or VIDEO_PROMPT, url, "video",
                                      system=self.build_system_prompt(key, with_tools=False), url=self._url(sp))

    def _m_omni_audio(self, key, sp, inp):
        url = file_to_data_url(inp.get("audio", ""), "audio/wav")
        if not url:
            return ModelResult(False, error=f"audio not found: {inp.get('audio')}")
        if url.startswith("http"):
            return ModelResult(False, error="omni audio needs a local file (input_audio is base64)")
        return self.client.chat_media(sp["model"], inp.get("prompt") or AUDIO_PROMPT, url, "audio",
                                      system=self.build_system_prompt(key, with_tools=False), url=self._url(sp))

    def _function_id(self, sp):
        """The role's explicit function_id, then refreshed/stored IDs (verified
        fleet, discovery, `grpc refresh`), then the built-in tables last, so a
        refreshed ID always beats a hardcoded one (3.8.2)."""
        if sp.get("function_id"):
            return sp["function_id"]
        model = sp.get("model")
        try:
            from . import store
            rec = store.verified_models().get(model) or {}
            if rec.get("function_id"):
                return rec["function_id"]
            ent = (store.load(store.DISCOVERED).get("models") or {}).get(model) or {}
            if ent.get("function_id"):
                return ent["function_id"]
            g = store.grpc_function(model) or {}
            if g.get("function_id"):
                return g["function_id"]
        except Exception:  # noqa: BLE001 - fall through to the built-in tables
            pass
        return (R.CLONE_MODELS.get(model) or {}).get("function_id") or R.TTS_FUNCTION_IDS.get(model)

    def _custom_url(self, sp, kind):
        """A custom endpoint (3.8.2) for this role: its explicit endpoint when
        that is under a registered gateway, else a gateway serving the model."""
        try:
            from . import endpoints
            if sp.get("endpoint") and endpoints.owner_of(sp["endpoint"]):
                return sp["endpoint"]
            return endpoints.url_for(sp.get("model") or "", kind)
        except Exception:  # noqa: BLE001
            return None

    def _grpc(self, sp):
        """True when this model role goes over NVCF gRPC (v3.5)."""
        from . import nvcf_grpc
        try:
            return nvcf_grpc.use_grpc(sp)
        except Exception:  # a broken store never stops a role
            return False

    def _grpc_call(self, fn, what):
        """v3.7.1: the Riva gRPC helpers have no deadline of their own, so a
        stuck stream could hold a voice turn forever. Bound them by the
        HTTP timeout setting (or the voice call's tighter cap)."""
        from . import perf
        limit = perf.capped(None, default=float(getattr(getattr(self.client, "http", None), "timeout", None) or 60) + 30)
        try:
            return perf.bounded(fn, limit, what)
        except perf.Timeout as e:
            return ModelResult(False, error=str(e), status=504)

    def _m_asr(self, key, sp, inp):
        r = self._m_asr_inner(key, sp, inp)
        if not r.ok:
            try:
                if callable(self.log):
                    self.log(f"[asr] {sp.get('model')} failed: {r.error}")
            except Exception:  # noqa: BLE001
                pass
        return r

    def _m_asr_inner(self, key, sp, inp):
        path = inp.get("audio", "")
        if not os.path.isfile(path):
            return ModelResult(False, error=f"audio not found: {path}")
        if self._grpc(sp):
            from . import nvcf_grpc
            return self._grpc_call(lambda: nvcf_grpc.run_asr(sp, path=path, language=inp.get("language"),
                                                             voice_settings=self.cluster.get("voice_settings", {}),
                                                             api_key=self.client.api_key), "ASR (gRPC)")
        # HTTP ASR: always send 16 kHz mono WAV (call-page webm/opus, Telegram ogg, m4a...)
        from . import nvcf_grpc
        try:
            data, _pcm, _notes = nvcf_grpc.to_wav16k(path)
        except nvcf_grpc.GrpcError as e:
            return ModelResult(False, error=f"ASR audio: {e}")
        return self.client.asr(data, "audio.wav", url=self._url(sp), function_id=self._function_id(sp),
                               language=inp.get("language") or self.cluster.get("voice_settings", {}).get("language",
                                                                                                      "en-US"),
                               model=sp["model"])

    def tts_url_for(self, sp):
        """3.8.2 precedence: the role's endpoint, a custom endpoint, then the
        function ID (the role's own, then refreshed/stored ones, then the
        built-in tables last; see _function_id)."""
        if sp.get("endpoint"):
            return sp["endpoint"]
        cu = self._custom_url(sp, "tts")
        if cu:
            return cu
        fid = self._function_id(sp)
        if fid:
            return self.client.nvcf_url(fid, "/v1/audio/synthesize")
        return self.client.tts_url()

    def _m_tts(self, key, sp, inp):
        """Clean the text first (no markup reaches Triton); on a 400 that names
        a character problem, retry once with the strict clean."""
        from .unified import tts_clean
        raw = inp.get("text", "")
        inp = dict(inp, text=tts_clean(raw))
        if not inp["text"]:
            return ModelResult(False, error="nothing speakable in the text (only markup or symbols)")
        r = self._m_tts_once(key, sp, inp)
        if not r.ok and (r.status == 400 or "400" in str(r.error or "")) and re.search(
                r"charac|token|parse|symbol|invalid input", str(r.error or ""), re.I):
            strict = tts_clean(raw, strict=True)
            if strict and strict != inp["text"]:
                r2 = self._m_tts_once(key, sp, dict(inp, text=strict))
                if r2.ok:
                    return r2
        return r

    def _m_tts_once(self, key, sp, inp):
        clone = None
        vc = sp.get("voice_clone") or {}
        sup = R.clone_support(sp.get("model"))
        voice = inp.get("voice")
        if vc.get("path") and sup:
            from . import voiceclone
            try:
                _, data, _info = voiceclone.prepare(vc["path"])
            except voiceclone.CloneError as e:
                return ModelResult(False, error=f"voice clone reference: {e}")
            clone = (os.path.basename(vc["path"]).rsplit(".", 1)[0] + ".wav", data)
            if voice is None:
                voice = sup.get("voice") or ""
        cu = self._custom_url(sp, "tts")
        if cu:
            from . import endpoints
            r = self.client.tts_openai(endpoints.real_model_id(sp.get("model")), inp.get("text", ""), cu,
                                       voice=voice or None, timeout=inp.get("timeout") or 35)
            if r.ok:
                r.files = [save_wav(r.data, "voice")]
            return r
        if self._grpc(sp):
            from . import nvcf_grpc
            vs = self.cluster.get("voice_settings", {})
            r = self._grpc_call(lambda: nvcf_grpc.run_tts(
                sp, inp.get("text", ""), voice=inp.get("voice"),
                language=inp.get("language") or sp.get("language_code") or vs.get("language"),
                prompt_wav=clone[1] if clone else None,
                prompt_transcript=vc.get("transcript") if clone else None,
                api_key=self.client.api_key), "TTS (gRPC)")
            if r.ok:
                r.files = [save_wav(r.data, "voice")]
            return r
        r = self.client.tts(inp.get("text", ""), voice=voice, language=inp.get("language"), url=self.tts_url_for(sp),
                            audio_prompt=clone, audio_prompt_transcript=vc.get("transcript") if clone else None,
                            prompt_field=(sup or {}).get("field", "audio_prompt"))
        if r.ok:
            r.files = [save_wav(r.data, "voice")]
        return r

    def _m_image_gen(self, key, sp, inp):
        r = self.client.image_gen(sp["model"], inp.get("prompt") or inp.get("text", ""), url=self._url(sp))
        if r.ok:
            from .rolemcp import _sniff
            r.files = [save_bytes(b, "image", _sniff(b) or "png") for b in r.data]
            r.text = f"{len(r.files)} image(s) saved"
        return r

    def _m_audio_gen(self, key, sp, inp):
        if not sp.get("endpoint"):
            return ModelResult(False, error=R.BY_KEY["audio_gen"].note)
        res = self.client.post(sp["endpoint"], {"model": sp["model"], "prompt": inp.get("prompt") or inp.get("text"),
                                                "duration": inp.get("duration", 10)}, 180,
                               accept="audio/*, application/json")
        if not res.ok:
            return ModelResult(False, latency=res.latency, status=res.status, error=res.error or f"HTTP {res.status}")
        from .rolemcp import _media_in_json, _sniff
        body = res.body if isinstance(res.body, bytes) else (res.body or b"")
        blobs = [(body, _sniff(body))] if _sniff(body) else _media_in_json(res.json() or {})[0]
        if not blobs:
            return ModelResult(False, latency=res.latency, status=res.status, error="no audio in response")
        files = [save_bytes(b, "music", ext or "wav") for b, ext in blobs]
        return ModelResult(True, text=f"{len(files)} audio file(s) saved", latency=res.latency, files=files)

    def _m_embedding(self, key, sp, inp):
        r = self.client.embed(sp["model"], [inp.get("text", "")], input_type=inp.get("input_type"), url=self._url(sp))
        if r.ok:
            r.data = r.data[0] if r.data else None
        return r

    def _m_reranker(self, key, sp, inp):
        return self.client.rerank(sp["model"], inp.get("query", ""), list(inp.get("passages") or []),
                                  url=self._url(sp))

    def _m_guard_translate(self, key, sp, inp):
        task = inp.get("task", "translate")
        if task == "check" and self._grpc(sp):
            return ModelResult(False, error=f"{sp.get('model')} is a gRPC translation model; it can't run the "
                                            "safety check (set a guard model for that)")
        if task == "check":
            msgs = [{"role": "user", "content": inp.get("text", "")}]
            if inp.get("reply"):
                msgs.append({"role": "assistant", "content": inp["reply"]})
            return self.client.chat(sp["model"], msgs, 0.0, 128, url=self._url(sp))
        target = inp.get("target_language") or self.cluster.get("guard_settings", {}).get("translate_target", "English")
        if self._grpc(sp):
            from . import nvcf_grpc
            return self._grpc_call(lambda: nvcf_grpc.run_translate(sp, inp.get("text", ""), target=target,
                                                                   source=inp.get("source_language"),
                                                                   api_key=self.client.api_key), "translate (gRPC)")
        msgs = [{"role": "system", "content": self.role_prompt("guard_translate")},
                {"role": "user", "content": f"Translate the following text to {target}. Reply with the translation "
                                            f"only.\n\n{inp.get('text', '')}"}]
        return self.client.chat(sp["model"], msgs, 0.1, 1024, url=self._url(sp))

    # -- convenience wrappers (testbed commands, judge) --------------------
    def chat_step(self, role, messages, temperature=0.7, max_tokens=1024, with_tools=True, system=None):
        """One chat call for a text role, with v3.8.3 model fallbacks (see
        nimlab.fallback): on 429 / 5xx / timeout the same step goes to the
        reasoning model (persona), then the role's secondary list. r.tried
        lists every attempt (role, model, host, status, short body, retries)."""
        from . import fallback as FB
        inp = dict(messages=messages, temperature=temperature, max_tokens=max_tokens, with_tools=with_tools)
        if system is not None:
            inp["system"] = system
        fs = FB.settings(self.cluster)
        key = R.LEGACY_MAP.get(role, role) if role not in R.BY_KEY and role not in R.EXTRA_ROLES else role
        if not fs["enabled"] or not self.is_set(key) or self.backend(key) != R.MODEL:
            return self.run_role(role, **inp)
        sp = self.spec(key)
        chain = self.fallback_chain(key, fs)
        pre = getattr(_FB_LOCAL, "failed", None)
        _FB_LOCAL.failed = None
        tried = []
        first = None
        cooling = bool(chain) and FB.cooling(key)
        if pre and pre[0] == key:
            first = pre[1]
            tried.append(pre[2])
        elif not cooling:
            first = self.run_role(role, **inp)
            tried.append(FB.attempt_row(key, "primary", sp.get("model"), getattr(first, "url", None) or
                                        self._url(sp) or self._client_base(), first,
                                        getattr(first, "attempts", None)))
            if first.ok or not chain or not FB.should_fall_back(first):
                first.tried = tried
                if not first.ok and FB.should_fall_back(first):
                    first.plain_error = FB.plain_failure(tried)     # busy/down, and no fallback is set
                return first
        if first is not None and not FB.should_fall_back(first):
            first.tried = tried
            return first
        fb_inp = dict(inp, messages=FB.strip_reasoning(messages))
        if "system" not in fb_inp:
            fb_inp["system"] = self.build_system_prompt(key, with_tools=with_tools)
        handler = getattr(self, f"_m_{key}", None) or self._m_text
        from . import perf
        for kind, fsp in chain:
            with perf.stage(key, target=f"{fsp['model']} (fallback)") as st:
                try:
                    r = handler(key, fsp, fb_inp)
                except perf.Timeout as e:
                    r = ModelResult(False, error=str(e), status=504)
                except (OSError, ValueError) as e:
                    r = ModelResult(False, error=str(e))
                st["ok"] = bool(r.ok)
            tried.append(FB.attempt_row(key, kind, fsp["model"], getattr(r, "url", None) or self._url(fsp) or
                                        self._client_base(), r, getattr(r, "attempts", None)))
            if r.ok:
                r.tried = tried
                r.fallback = {"role": key, "model": fsp["model"], "kind": kind}
                if first is not None:   # the primary really failed just now: rest it, and log it
                    FB.start_cooldown(key, fs["cooldown"])
                    FB.log_event({"role": key, "from_model": sp.get("model"), "status": tried[0].get("status"),
                                  "body": tried[0].get("body"), "host": tried[0].get("host"),
                                  "to_model": fsp["model"], "kind": kind, "tried": len(tried)})
                    if callable(self.log):
                        self.log(f"[fallback] {key}: {sp.get('model')} failed ({tried[0].get('status')}); "
                                 f"answered by {fsp['model']}")
                return r
        if first is None:   # cooling down and every fallback failed: the primary gets its turn after all
            first = self.run_role(role, **inp)
            tried.append(FB.attempt_row(key, "primary", sp.get("model"), getattr(first, "url", None) or
                                        self._url(sp) or self._client_base(), first,
                                        getattr(first, "attempts", None)))
            if first.ok:
                first.tried = tried
                return first
        FB.log_event({"role": key, "from_model": sp.get("model"), "status": tried[0].get("status"),
                      "body": tried[0].get("body"), "host": tried[0].get("host"), "to_model": None,
                      "tried": len(tried)})
        first.tried = tried
        plain = FB.plain_failure(tried)
        if plain:
            first.plain_error = plain
        return first

    def _client_base(self):
        f = getattr(self.client, "integrate", None)
        try:
            return f() if callable(f) else None
        except Exception:  # noqa: BLE001
            return None

    def fallback_chain(self, key, fs=None):
        """[(kind, spec)] tried in order when the role's model fails:
        the reasoning model (persona only), then roles.<key>.fallbacks."""
        from . import fallback as FB
        fs = fs or FB.settings(self.cluster)
        sp = self.spec(key)
        out, seen = [], {sp.get("model")}
        if key == "persona" and fs["to_reasoning"] and self.is_set("reasoning") \
                and self.backend("reasoning") == R.MODEL:
            rsp = self.spec("reasoning")
            if rsp.get("model") not in seen:
                d = dict(sp, model=rsp["model"])
                d.pop("endpoint", None)
                if rsp.get("endpoint"):
                    d["endpoint"] = rsp["endpoint"]
                out.append(("reasoning", d))
                seen.add(rsp["model"])
        for f in FB.secondary_list(sp):
            if f["model"] in seen:
                continue
            d = dict(sp, model=f["model"])
            d.pop("endpoint", None)
            if f.get("url"):
                d["endpoint"] = f["url"]
            out.append(("secondary", d))
            seen.add(f["model"])
        return out

    def respond(self, role, history, temperature=0.7, max_tokens=1024, use_tools=True, system_extra=None,
                keep_role=False):
        """One user turn (already appended to history), with the bounded tool
        loop when MCP is enabled. Steps that follow a tool result go to the
        coding/tool-calling role when it is set. Returns (result, trace)."""
        last = {}
        calls = {"n": 0}

        def chat_fn(hist):
            use = role
            if calls["n"] > 0 and self.is_set("coding") and not keep_role:
                use = "coding"
            calls["n"] += 1
            system = None
            if system_extra and self.backend(use) != R.MCP:
                system = self.build_system_prompt(use, with_tools=use_tools, extra=system_extra)
            r = self.chat_step(use, hist, temperature, max_tokens, with_tools=use_tools, system=system)
            last["r"] = r
            last["role"] = use
            if r.ok and box is not None and isinstance(r.raw, dict):
                # native OpenAI tool_calls (a server-side tool parser) -> the same loop
                native = native_calls_as_text(r.raw, known=lambda n: n == LOAD_TOOLS or box.tool(n) is not None)
                if native:
                    r.text = native
            return (r.text if r.ok else ""), r.ok

        def final_fn(hist):
            """After max_tool_steps: one answer with no tools offered."""
            use = last.get("role") or role
            r = self.chat_step(use, hist, temperature, max_tokens, with_tools=False,
                               system=self.build_system_prompt(use, with_tools=False, extra=system_extra))
            if r.ok:
                last["r"] = r
            return (r.text if r.ok else ""), r.ok

        if use_tools:
            self.ensure_tools()
        box = SA.ToolBox(self, self.mcp if (self.mcp and self.mcp.tools) else None) if use_tools else None
        if box is not None and box.tools:
            s = self.mcp_settings
            max_steps = int(s.get("max_tool_steps", 4))
            from . import jobguard as JG
            guard = JG.current()
            if guard is not None and guard.unlimited and box.scoped():
                # v3.8.4: a scheduled job with its own tool list: no fixed step cap, only those
                # tools (box enforces it), runaway guards and interrupts instead
                max_steps = None
            elif guard is not None and not guard.interruptible:
                guard = None
            with SA.using_box(box):
                reply, trace = run_tool_loop(chat_fn, history, box, SA.Policy(self.policy(), box),
                                             max_steps=max_steps,
                                             max_calls_per_step=int(s.get("max_calls_per_step", 3)),
                                             max_result_chars=int(s.get("max_result_chars", 8000)),
                                             log=self.log, final_fn=final_fn, guard=guard)
            result = last["r"]
            if result.ok:
                result.text = reply
            return result, trace
        box = None
        chat_fn(history)
        r = last["r"]
        if r.ok and r.text:
            r.text = strip_tool_markup(r.text)   # a model that writes tool markup anyway never shows it
        return r, []

    def analyze_image(self, img_ref, prompt=None, role="vision"):
        return self.run_role(role, image=img_ref, prompt=prompt)

    def ocr(self, img_ref):
        return self.run_role("ocr", image=img_ref)

    def synthesize_voice(self, text, play=True):
        """Returns (audio_path or None, ModelResult)."""
        r = self.run_role("tts", text=text)
        if not r.ok or not r.files:
            if r.ok:
                r.ok, r.error = False, "no audio returned"
            return None, r
        if play:
            play_audio(r.files[0])
        return r.files[0], r

    def translate(self, text, target=None):
        return self.run_role("guard_translate", text=text, task="translate", target_language=target)

    def guard_check(self, text, reply=None):
        """-> (allowed, reason). Allowed when the guard role is unset, fails,
        or can't be read; blocked only on a clear unsafe verdict."""
        if not self.is_set("guard_translate"):
            return True, "no guard role set"
        r = self.run_role("guard_translate", text=text, reply=reply, task="check")
        if not r.ok:
            return True, f"guard check failed: {r.error}"
        safe, why = parse_safety(r.text)
        return (safe is not False), why

    # -- memory -----------------------------------------------------------
    def rerank_fn(self):
        if not self.is_set("reranker"):
            return None

        def fn(query, passages):
            r = self.run_role("reranker", query=query, passages=passages)
            if not r.ok:
                raise RuntimeError(r.error)
            return r.data
        return fn

    def recall(self, query, history=None):
        """(hits, info): automatic recall for one turn, straight from the
        configured store (the Oracle connection, local file or JSON). Never
        goes through MCP.

        v3.8.0: vector similarity and keyword search (Oracle Text CONTAINS on
        Oracle, FTS5 or a word scan elsewhere) are ranked together, reranked by
        the reranker role when set, and cut to recall_top_k (default 6) within
        recall_max_chars. Turns already in this conversation's context
        (history) are left out, so they can't take the top places. Identity
        and "what did I tell you" questions also get the newest memories.
        Logs one trace line: [memory] recall <backend>: N hits in X ms."""
        if self.memory is None:
            return [], {"reranked": False, "skipped": "memory off"}
        if not self.memory.settings.get("auto_recall", True):
            self._mem_log("recall skipped: auto_recall is off")
            return [], {"reranked": False, "skipped": "auto_recall off"}
        from . import ltm
        ms = self.cluster.get("memory_settings", {}) or {}
        t0 = time.monotonic()
        k = max(1, int(ms.get("recall_top_k", 6) or 6))
        identity_ask = bool(ltm.IDENTITY_ASK.search(query or ""))
        memory_ask = identity_ask or bool(RECALL_ASK.search(query or ""))
        seen_ctx = context_index(history) if ms.get("exclude_context_turns", True) else None
        exclude = (lambda t: in_context(t, seen_ctx)) if seen_ctx else None
        hits, info = self.memory.recall_hybrid(
            query, top_k=k, threshold=ms.get("similarity_threshold", 0.45), rerank_fn=self.rerank_fn(),
            candidates=ms.get("rerank_candidates", 16), exclude=exclude,
            keyword_weight=ms.get("hybrid_keyword_weight", 0.6), hybrid=ms.get("hybrid_recall", True),
            extra_terms=ltm.identity_terms(query) if identity_ask else None)
        hits = fit_budget(hits, int(ms.get("recall_max_chars", 2400) or 0))
        info["ms"] = int((time.monotonic() - t0) * 1000)
        info["recent"] = []
        info["identity_ask"] = identity_ask
        n_recent = int(ms.get("recent_on_recall_ask", 3) or 0)
        if memory_ask and n_recent:
            # "what's my name?" / "what were we just talking about?" names no topic a
            # vector can match: add the newest memories in this scope as well
            seen = {h[3] for h in hits} | {h[1] for h in hits}
            pool = [h for h in self.memory.recent(n_recent + 8)
                    if h[3] not in seen and h[1] not in seen and ltm.usable_memory(h[1])
                    and not (h[1] or "").startswith("[identity:") and not (exclude and exclude(h[1]))]
            info["recent"] = pool[-n_recent:]
        self.memory.last_turn["recalled"] = len(hits)
        self.memory.last_turn["recall_ms"] = info["ms"]
        off = self.memory.offline
        where = self.memory.backend_name + (f" {self.memory.where()}" if hasattr(self.memory, "where") else "")
        if off:
            self._mem_log(f"recall {where}: store offline ({str(off)[:120]}) after {info['ms']} ms")
        else:
            extra = f" + {len(info['recent'])} recent" if info["recent"] else ""
            rr = ", reranked" if info.get("reranked") else ""
            thr = float(ms.get("similarity_threshold", 0.45))
            scores = ", ".join(f"{float(h[0]):.2f}" for h in hits)
            near = getattr(self.memory, "last_near_miss", None) or []
            info["scores"] = [round(float(h[0]), 3) for h in hits]
            info["below"] = [round(float(h[0]), 3) for h in near]
            sc = f" scores [{scores}]" if hits else ""
            below = (f"; best under threshold {thr}: " + ", ".join(f"{float(h[0]):.2f}" for h in near)) if near else ""
            mix = f" (vector {info.get('vector', 0)}, keyword {info.get('keyword', 0)}"
            mix += f", {info['excluded']} already in context" if info.get("excluded") else ""
            mix += ")"
            self._mem_log(f"recall {where}: {len(hits)}/{k} hit(s){sc}{extra}{rr}{mix} in {info['ms']} ms "
                          f"(k={k}, threshold={thr}){below}")
        return hits, info

    def identity_block(self):
        """Pinned identity facts for the prompt ('' when none or memory off)."""
        if self.memory is None or not self.memory.settings.get("pin_identity", True):
            return ""
        try:
            lines = self.memory.identity_block()
        except Exception as e:  # noqa: BLE001 - never fail a turn on this
            self._mem_log(f"identity facts unavailable: {str(e)[:120]}")
            return ""
        if not lines:
            return ""
        return ("\n[KNOWN FACTS ABOUT THE USER (pinned from what they told you earlier, on any channel; "
                "use them, e.g. call the user by this name)]:\n" + lines + "\n")

    def _mem_log(self, msg):
        if callable(self.log) and (self.cluster.get("memory_settings", {}) or {}).get("trace", True):
            self.log(f"[memory] {msg}")

    def recall_block(self, query, history=None):
        hits, info = self.recall(query, history=history)
        recent = (info or {}).get("recent") or []
        out = self.identity_block()
        if not hits and not recent:
            return out
        if hits:
            out += "\n[RECALLED SEMANTIC MEMORY]:\n" + "\n".join(f"- {h[1]}" for h in hits) + "\n"
        if recent:
            out += ("\n[MOST RECENT MEMORIES, oldest first (from your own long-term memory, including earlier "
                    "chats and voice calls)]:\n" + "\n".join(f"- {h[1]}" for h in recent) + "\n")
        return out

    def memory_search_text(self, args):
        """The built-in memory_search tool: semantic, keyword or both, in-process
        over the same connection as the automatic recall. -> text for the model."""
        if self.memory is None:
            return "Long-term memory is off."
        q = str((args or {}).get("query") or "").strip()
        if not q:
            return "memory_search needs a query."
        mode = str((args or {}).get("mode") or "both").lower()
        try:
            k = max(1, min(int((args or {}).get("limit") or 5), 20))
        except (TypeError, ValueError):
            k = 5
        hits, info = self.memory.search(q, mode=mode, top_k=k, rerank_fn=self.rerank_fn(),
                                        threshold=(self.cluster.get("memory_settings", {}) or {}).get(
                                            "search_threshold", 0.3))
        where = self.memory.backend_name
        self._mem_log(f"memory_search {where} mode={info['mode']}: {len(hits)} hit(s) "
                      f"(semantic {info['semantic']}, keyword {info['keyword']}"
                      f"{', reranked' if info.get('reranked') else ''}) in {info['ms']} ms")
        if self.memory.offline:
            return f"Your memory store is offline right now ({str(self.memory.offline)[:160]}); nothing was searched."
        if not hits:
            return f"No memories matched '{q}' ({info['mode']} search)."
        return "\n".join(f"- [{(h[2] or '')[:16]}] {h[1]}" for h in hits)

    def remember_turn(self, user_text, result, role, turn_key=None):
        """Store a turn only when the reply succeeded and is not an error.
        turn_key (a hash of the conversation up to this user message) keeps a
        UI that resends the whole history, or regenerates a reply, from
        storing the same turn twice."""
        if self.memory is None or not result.ok or is_error_text(result.text):
            return None
        # what qualifies, de-duplication and retention: memory_settings.long_term
        t0 = time.monotonic()
        ids = self.memory.remember(user_text, result.text, metadata={"role": role}, turn_key=turn_key)
        ms = int((time.monotonic() - t0) * 1000)
        if self.memory.offline:
            self._mem_log(f"store {self.memory.backend_name}: offline, turn not saved ({str(self.memory.offline)[:100]})")
        else:
            self._mem_log(f"store {self.memory.backend_name}: {len(ids or [])} memory(s) saved in {ms} ms"
                          if ids else f"store {self.memory.backend_name}: nothing new to save ({ms} ms)")
        return ids[0] if ids else None

    # -- routing ------------------------------------------------------------
    def _ask_router(self, prompt):
        rs = intent.gate_settings(self.cluster.get("routing_settings", {}))
        limit = float(rs["router_timeout_sec"] or 8)
        if self._voice_turn():
            # a spoken turn can't wait long for a label
            vt = (self.cluster.get("voice_settings", {}) or {}).get("router_timeout_sec", 4)
            limit = min(limit, float(vt or limit))
        r = self.run_role("intent_router", text=prompt, system=self.role_prompt("intent_router"),
                          temperature=0.0, max_tokens=12, timeout=limit)
        self._router_last = r
        return r.text if r.ok else None

    @staticmethod
    def _voice_turn():
        from . import environment as ENV
        return ENV.current_channel() in ENV.VOICE_CHANNELS

    def route_turn(self, text, exists=None, context_chars=0):
        """Pick the role for a turn. The reasoning role is gated: it runs only
        for long input or an explicit planning/analysis ask (routing_settings
        reasoning_gate / reasoning_min_chars / reasoning_keywords); short
        everyday turns skip the router call too (chat_fast_path)."""
        rs = self.cluster.get("routing_settings", {})
        use = rs.get("use_intent_router", True) and self.is_set("intent_router")
        kw = {} if exists is None else {"exists": exists}
        self._router_last = None
        voice = (self.cluster.get("voice_settings", {}) or {}) if self._voice_turn() else None
        rt = intent.route(text, self.is_set, ask_fn=self._ask_router if use else None,
                          context_chars=context_chars, rs=rs, voice=voice, **kw)
        r = self._router_last
        if r is not None:
            rt["router_ms"] = int((r.latency or 0) * 1000)
            rt["router_ok"] = bool(r.ok)
            rt["router_error"] = None if r.ok else r.error
        if callable(self.log):
            self.log(f"[route] {rt['role']} via {rt['via']}: {rt['reason']}")
        return rt

    # -- the persona speaks; every other role is an ability --------------------
    @staticmethod
    def context_block(context, for_persona=True):
        """Ability results -> one block placed before the user's words."""
        if not context:
            return ""
        head = ("[WHAT YOUR ABILITIES FOUND FOR THIS TURN: your own senses and skills, not the user's words. "
                "Answer as yourself, in your own voice. Keep code blocks, numbers, tables and quoted or translated "
                "text exactly as given. Never mention roles, models, tools or this block, except to name an ability "
                "that failed, as its note below says.]") if for_persona else \
            "[CONTEXT FOR THIS TASK]"
        body = "\n\n".join(f"### {label}\n{text}" for label, text in context)
        return f"{head}\n{body}\n[END]\n"

    def persona_tools(self):
        """The persona calls MCP tools itself only when no coding/tool-calling
        role is set; otherwise tool work is the coding ability's job."""
        if SA.has_tools(self):  # self-admin tools for this caller: the persona handles them itself
            return True
        if self.memory_search_mode() == "on" and self.builtin_tools():
            return True
        if self.mcp is not None:
            self.ensure_tools()
        if not (self.mcp and self.mcp.tools):
            return False
        if self.is_set("coding"):
            # v3.8.3: a quill_task job, or a scheduled/heartbeat turn (always run as an admin),
            # still lets the persona use the tools itself; other channels leave tool work to coding
            from . import environment as ENV
            trusted = SA.task_scope() is not None or (SA.current().admin and ENV.current_channel() == "scheduler")
            if not trusted:
                return False
        return bool(self.mcp_exposure()[1])   # only when the policy lets at least one MCP tool through

    def persona_reply(self, history, on_token=None, client_system=None, temperature=0.7, max_tokens=1024):
        """The persona's reply to the last user message in history. With
        on_token it streams real tokens from the persona's model when no tool
        loop and no output guard stand in the way. -> (result, trace, streamed)."""
        use_tools = self.persona_tools()
        gs = self.cluster.get("guard_settings", {})
        guarded = gs.get("check_output") and self.is_set("guard_translate")
        from . import fallback as FB
        cooling = FB.cooling("persona") and bool(self.fallback_chain("persona"))
        if on_token and not use_tools and not guarded and self.backend("persona") == R.MODEL and not cooling:
            sp = self.spec("persona")
            system = self.build_system_prompt("persona", with_tools=False, extra=client_system)
            got = []
            from .mcp import StreamScrubber
            scrub = StreamScrubber()

            def tok(t):
                got.append(t)
                shown = scrub.feed(t)
                if shown:
                    on_token(shown)
            from . import perf
            with perf.stage("persona", target=sp.get("model")) as st:
                r = self.client.chat_stream(sp["model"], [{"role": "system", "content": system}] + history,
                                            on_token=tok, temperature=temperature, max_tokens=max_tokens,
                                            url=self._url(sp))
                st["ok"] = bool(r.ok)
            if got:
                rest = scrub.flush()
                if rest:
                    on_token(rest)
                if r.ok and r.text:
                    r.text = strip_tool_markup(r.text)
                    if scrub.stopped and not r.text:
                        # the model only wrote a tool call while streaming: answer properly, no tools
                        r2, _ = self.respond("persona", history, temperature, max_tokens, use_tools=False,
                                             system_extra=client_system, keep_role=True)
                        if r2.ok and r2.text:
                            on_token(r2.text)
                        return r2, [], True
                return r, [], True
            # nothing streamed (backend ignored stream, or failed first): one normal call
            if not r.ok and FB.should_fall_back(r) and self.fallback_chain("persona"):
                # v3.8.3: the stream already failed after its retries; go straight to the fallbacks
                _FB_LOCAL.failed = ("persona", r, FB.attempt_row("persona", "primary", sp.get("model"),
                                                                 getattr(r, "url", None) or self._url(sp) or
                                                                 self._client_base(), r,
                                                                 getattr(r, "attempts", None)))
        result, trace = self.respond("persona", history, temperature, max_tokens, use_tools=use_tools,
                                     system_extra=client_system, keep_role=True)
        return result, trace, False

    def turn(self, text, history, role=None, media=None, context=None, route=None, on_token=None,
             client_system=None, turn_key=None, temperature=0.7, max_tokens=1024, defer_store=False):
        """One chat turn end to end. role/media force a route (slash commands);
        route passes one already decided. context: [(label, text)] ability
        results gathered by the caller (nimlab.unified) for this turn.

        With routing_settings.persona_final (default) the persona writes the
        reply every time: generation, translation, reasoning and coding run
        first as abilities and their output is handed to the persona.

        Returns dict(route, pre, result, trace, files, blocked, abilities,
        answered_by, streamed, store). `pre` is the media/ability result that ran
        first; `result` is the final reply (None when blocked or when a
        forced media step failed). defer_store=True leaves the memory store
        to the caller: out['store']() saves the turn once the reply has been
        delivered (spoken, sent), so saving never delays the answer."""
        try:
            self.refresh_memory_settings()
        except Exception as e:  # noqa: BLE001 - never block a turn on this
            self._mem_log(f"settings reload failed: {str(e)[:120]}")
        if route:
            rt = route
        elif role:
            rt = {"role": role, "reason": "command", "media": media or [], "text": text, "via": "command"}
        else:
            rt = self.route_turn(text)
        out = {"route": rt, "pre": None, "result": None, "trace": [], "files": [], "blocked": None,
               "abilities": [], "streamed": False}
        gs = self.cluster.get("guard_settings", {})
        if gs.get("check_input") and self.is_set("guard_translate"):
            ok, why = self.guard_check(text)
            if not ok and gs.get("block_on_unsafe", True):
                out["blocked"] = f"input blocked by guard: {why}"
                return out
        final = self.persona_final
        ctx = list(context or [])
        role = rt["role"]
        body = rt["text"]

        def note(key, r):
            out["abilities"].append({"role": key, "ok": bool(r.ok), "latency": r.latency, "error": r.error,
                                     "target": self.target(key)})

        if role in ("image_gen", "audio_gen"):
            g = self.run_role(role, prompt=body)
            note(role, g)
            out["files"] = list(g.files or [])
            if not final:
                out["result"] = g
                return out
            out["pre"] = g
            what = "an image" if role == "image_gen" else "audio"
            if g.ok:
                ctx.append((R.label(role), f"You just made {what} for this request ({len(g.files or [])} file(s)). "
                                           "It is attached under your reply automatically: say a line about it, "
                                           "don't write links or file paths." +
                            (f" Generator notes: {g.text}" if g.text else "")))
            else:
                ctx.append((R.label(role), f"Making {what} failed: {g.error}. Tell the user briefly."))
            role = "persona"
        elif role == "guard_translate":
            tr = self.translate(body)
            note(role, tr)
            if not final:
                out["result"] = tr
                return out
            out["pre"] = tr
            ctx.append(("Translation", "Give the user this translation exactly as written:\n" + tr.text if tr.ok
                        else f"Translating failed: {tr.error}. Tell the user briefly."))
            role = "persona"
        elif role in MEDIA_ROLES:
            ref = rt["media"][0][1] if rt["media"] else body
            field = {"video": "video", "asr": "audio", "omni_audio": "audio"}.get(role, "image")
            pre = self.run_role(role, **{field: ref, "prompt": body if rt["media"] else None})
            note(role, pre)
            out["pre"] = pre
            if not pre.ok:
                return out
            name = os.path.basename(ref) if not ref.startswith("data:") else "the attachment"
            if role == "asr":
                body = pre.text if not body or body == ref else f"{body}\n\n(Voice message transcript: {pre.text})"
            else:
                ctx.append((f"{R.label(role)} output for {name}", pre.text))
                body = body or "Tell me about it."
            role = "persona"
        if role not in TEXT_ROLES or not self.is_set(role):
            role = "persona"
        from . import perf
        with perf.stage("memory_recall", target=getattr(self.memory, "backend_name", None)):
            block = self.recall_block(body, history=history)
        off = getattr(self.memory, "offline", None) if self.memory is not None else None
        if off and off != getattr(self, "_memory_reported", None):
            # report an unreachable memory store once per outage, with a fix for admins
            self._memory_reported = off
            ctx.append(("Long-term memory unavailable",
                        f"Your long-term memory store is unreachable ({str(off)[:200]}), so nothing was recalled or "
                        "will be saved for now. Answer the user's message normally and mention this briefly. " +
                        fix_offer("memory", None, str(off), 0.0, self.cluster)))
        elif not off:
            self._memory_reported = None
        if final and role in ("reasoning", "coding"):
            task = (f"{block}\n" if block else "") + self.context_block(ctx, for_persona=False) + f"User Input: {body}"
            ab, atrace = self.respond(role, list(history) + [{"role": "user", "content": task}], temperature,
                                      max_tokens, use_tools=(role == "coding"), keep_role=True)
            note(role, ab)
            out["trace"].extend(atrace)
            out["ability"] = role
            ctx.append((f"{R.label(role)} result (relay it in your own voice; keep code and numbers exact)",
                        ab.text) if ab.ok else (f"{R.label(role)} failed", ability_failure_note(
                            role, self.target(role), ab, ok_steps=[a["role"] for a in out["abilities"] if a["ok"]]
                            + (["asr"] if rt.get("via") == "media" and rt.get("role") == "asr" else []),
                            cluster=self.cluster)))
            role = "persona"
        parts = []
        if block:
            parts.append(block)
        if ctx:
            parts.append(self.context_block(ctx))
        content = ("\n".join(parts) + f"\nUser Input: {body}") if parts else body
        history.append({"role": "user", "content": content})
        if role == "persona":
            result, trace, streamed = self.persona_reply(history, on_token, client_system, temperature, max_tokens)
            out["streamed"] = streamed
        else:
            result, trace = self.respond(role, history, temperature, max_tokens, system_extra=client_system)
        out["trace"].extend(trace)
        out["answered_by"] = role
        if not result.ok:
            history.pop()  # failed turns are neither kept in history nor stored as memory
            out["result"] = result
            return out
        if gs.get("check_output") and self.is_set("guard_translate"):
            ok, why = self.guard_check(body, reply=result.text)
            if not ok and gs.get("block_on_unsafe", True):
                history.pop()
                out["blocked"] = f"reply blocked by guard: {why}"
                return out
        history.append({"role": "assistant", "content": result.text})

        from .ltm import store_blocked
        blocked = store_blocked()   # a self-test request: read now, the store may run on another thread

        def store(body=body, result=result, role=role):
            if blocked:
                self._mem_log(f"store skipped: {blocked} request")
                return None
            with perf.stage("memory_store", target=getattr(self.memory, "backend_name", None)):
                return self.remember_turn(body, result, role, turn_key=turn_key)
        if defer_store:
            out["store"] = store
        else:
            store()
        out["result"] = result
        return out

    # -- test a role -------------------------------------------------------
    def probe_inputs(self, key, media=None):
        """The small fixed input sent by 'test a role'. media overrides the
        file (video has no built-in sample)."""
        from . import assets
        try:
            assets.ensure_assets()
        except OSError:
            pass
        aria = os.path.join(SAMPLES_DIR, "magpie_aria_sample.wav")
        if key in TEXT_ROLES:
            return {"text": PROBE_TEXT, "max_tokens": 16, "temperature": 0.0}
        if key == "vision":
            return {"image": media or os.path.join(assets.ASSETS_DIR, "vision_test.png"),
                    "prompt": "What shapes do you see? One line."}
        if key == "ocr":
            return {"image": media or os.path.join(assets.ASSETS_DIR, "ocr_test.png")}
        if key == "chart_parser":
            return {"image": media or os.path.join(assets.ASSETS_DIR, "vision_test.png")}
        if key == "video":
            return {"video": media, "prompt": "Describe this clip in one sentence."}
        if key == "asr":
            return {"audio": media or aria}
        if key == "omni_audio":
            return {"audio": media or aria, "prompt": "Is this speech, music or ambient sound? One line."}
        if key == "tts":
            return {"text": "Testing the voice role."}
        if key == "image_gen":
            return {"prompt": "a small red cube on a white table, studio light"}
        if key == "audio_gen":
            return {"prompt": "a calm five second piano loop", "duration": 5}
        if key == "embedding":
            return {"text": "test embedding", "input_type": "query"}
        if key == "reranker":
            return {"query": "Which city is the capital of France?",
                    "passages": ["Berlin is in Germany.", "Paris is the capital of France.", "Bananas are yellow."]}
        if key == "guard_translate":
            return {"text": "Good morning, how are you?", "task": "translate", "target_language": "Spanish"}
        return {"text": PROBE_TEXT}

    def test_role(self, key, media=None):
        """Send the fixed probe. Returns dict(ok, status, latency, summary,
        files, backend, target, error)."""
        sp = self.spec(key)
        info = {"backend": sp["backend"], "target": R.describe(sp), "files": [], "status": None}
        if key == "tts" and sp.get("voice_clone", {}).get("path"):
            info["voice_clone"] = sp["voice_clone"]["path"]
        inp = self.probe_inputs(key, media)
        if key == "video" and not inp.get("video"):
            return dict(info, ok=False, latency=0.0, summary="", error="video test needs a clip path or URL")
        t0 = time.monotonic()
        r = self.run_role(key, **inp)
        lat = r.latency or round(time.monotonic() - t0, 3)
        summary = r.text[:200] if r.text else ""
        if r.ok and key == "embedding":
            summary = f"vector of {len(r.data or [])} dims"
        elif r.ok and key == "reranker":
            summary = "order: " + ", ".join(str(i) for i, _ in (r.data or [])) + \
                      (" (correct: passage 1 first)" if r.data and r.data[0][0] == 1 else " (expected passage 1 first)")
        elif r.ok and r.files:
            summary = "saved " + ", ".join(r.files)
        return dict(info, ok=r.ok, status=r.status, latency=lat, summary=summary, files=r.files, error=r.error)


def image_exists(path):
    return bool(path) and os.path.isfile(path)
