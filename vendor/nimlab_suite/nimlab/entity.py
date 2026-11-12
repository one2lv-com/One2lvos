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
import time

from . import config, intent, rolemcp, roles as R
from .api import (ModelResult, NimClient, OCR_PROMPT, file_to_data_url, image_to_data_url, play_audio, save_bytes,
                  save_wav)
from .mcp import MCPClient, MCPError, ToolPolicy, run_tool_loop, tools_prompt
from .memory import MemoryCore, is_error_text

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
        self.memory = MemoryCore(self.client, self._embed_label(), embed_fn=self._embed_fn()) if memory else None

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

    def reload(self):
        self.cluster = config.load_cluster_config()
        self.prompts = config.load_prompts()
        self.soul = config.load_soul()
        self.client.cluster = self.cluster
        self._build_mcp()
        if self.memory is not None:
            self.memory.embed_model = self._embed_label()
            self.memory.embed_fn = self._embed_fn()

    def policy(self):
        s = self.mcp_settings
        return ToolPolicy(s.get("allowed_tools"), bool(s.get("confirm_tool_calls", True)), self.confirm_fn)

    # -- MCP --------------------------------------------------------------
    def refresh_tools(self):
        """initialize + tools/list for the chat tool loop ([] on failure)."""
        self.tools_error = None
        if not self.mcp:
            return []
        try:
            return self.mcp.list_tools()
        except MCPError as e:
            self.tools_error = str(e)
            return []

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

    def build_system_prompt(self, role="persona", with_tools=True):
        role = R.LEGACY_MAP.get(role, role) if role not in R.BY_KEY else role
        tools_desc = ""
        if with_tools and self.mcp and self.mcp.tools:
            tools_desc = tools_prompt(self.mcp.tools, self.mcp_settings.get("allowed_tools"))
        return (f"=== SOUL / IDENTITY SPECIFICATION ===\n{self.soul}\n\n"
                f"=== FUNCTION ROLE: {R.label(role).upper()} ===\n{self.role_prompt(role)}{tools_desc}")

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
        try:
            return handler(key, sp, inp)
        except (OSError, ValueError) as e:
            return ModelResult(False, error=str(e))

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
                                max_tokens=inp.get("max_tokens", 1024), url=self._url(sp))

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
        if sp.get("function_id"):
            return sp["function_id"]
        try:
            from . import store
            rec = store.verified_models().get(sp.get("model")) or {}
            if rec.get("function_id"):
                return rec["function_id"]
            ent = (store.load(store.DISCOVERED).get("models") or {}).get(sp.get("model")) or {}
            return ent.get("function_id") or R.TTS_FUNCTION_IDS.get(sp.get("model"))
        except Exception:
            return R.TTS_FUNCTION_IDS.get(sp.get("model"))

    def _m_asr(self, key, sp, inp):
        path = inp.get("audio", "")
        if not os.path.isfile(path):
            return ModelResult(False, error=f"audio not found: {path}")
        with open(path, "rb") as f:
            data = f.read()
        return self.client.asr(data, os.path.basename(path), url=self._url(sp), function_id=self._function_id(sp),
                               language=inp.get("language") or self.cluster.get("voice_settings", {}).get("language",
                                                                                                      "en-US"),
                               model=sp["model"])

    def tts_url_for(self, sp):
        if sp.get("endpoint"):
            return sp["endpoint"]
        fid = R.TTS_FUNCTION_IDS.get(sp.get("model")) or (R.CLONE_MODELS.get(sp.get("model"), {}).get("function_id"))
        if fid is None:
            fid = self._function_id(sp)
        if fid:
            return self.client.nvcf_url(fid, "/v1/audio/synthesize")
        return self.client.tts_url()

    def _m_tts(self, key, sp, inp):
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
        if task == "check":
            msgs = [{"role": "user", "content": inp.get("text", "")}]
            if inp.get("reply"):
                msgs.append({"role": "assistant", "content": inp["reply"]})
            return self.client.chat(sp["model"], msgs, 0.0, 128, url=self._url(sp))
        target = inp.get("target_language") or self.cluster.get("guard_settings", {}).get("translate_target", "English")
        msgs = [{"role": "system", "content": self.role_prompt("guard_translate")},
                {"role": "user", "content": f"Translate the following text to {target}. Reply with the translation "
                                            f"only.\n\n{inp.get('text', '')}"}]
        return self.client.chat(sp["model"], msgs, 0.1, 1024, url=self._url(sp))

    # -- convenience wrappers (testbed commands, judge) --------------------
    def chat_step(self, role, messages, temperature=0.7, max_tokens=1024, with_tools=True):
        return self.run_role(role, messages=messages, temperature=temperature, max_tokens=max_tokens,
                             with_tools=with_tools)

    def respond(self, role, history, temperature=0.7, max_tokens=1024, use_tools=True):
        """One user turn (already appended to history), with the bounded tool
        loop when MCP is enabled. Steps that follow a tool result go to the
        coding/tool-calling role when it is set. Returns (result, trace)."""
        last = {}
        calls = {"n": 0}

        def chat_fn(hist):
            use = role
            if calls["n"] > 0 and self.is_set("coding"):
                use = "coding"
            calls["n"] += 1
            r = self.chat_step(use, hist, temperature, max_tokens, with_tools=use_tools)
            last["r"] = r
            last["role"] = use
            return (r.text if r.ok else ""), r.ok

        if use_tools and self.mcp and self.mcp.tools:
            s = self.mcp_settings
            reply, trace = run_tool_loop(chat_fn, history, self.mcp, self.policy(),
                                         max_steps=int(s.get("max_tool_steps", 4)),
                                         max_calls_per_step=int(s.get("max_calls_per_step", 3)),
                                         max_result_chars=int(s.get("max_result_chars", 8000)),
                                         log=self.log)
            result = last["r"]
            if result.ok:
                result.text = reply
            return result, trace
        chat_fn(history)
        return last["r"], []

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

    def recall(self, query):
        """(hits, info): embedding recall of the top candidates, reranked to
        top-k by the reranker role when it is set."""
        if self.memory is None:
            return [], {"reranked": False}
        ms = self.cluster.get("memory_settings", {})
        return self.memory.recall_reranked(query, top_k=ms.get("recall_top_k", 3),
                                           threshold=ms.get("similarity_threshold", 0.45),
                                           rerank_fn=self.rerank_fn(), candidates=ms.get("rerank_candidates", 10))

    def recall_block(self, query):
        hits, _ = self.recall(query)
        if not hits:
            return ""
        return "\n[RECALLED SEMANTIC MEMORY]:\n" + "\n".join(f"- {h[1]}" for h in hits) + "\n"

    def remember_turn(self, user_text, result, role):
        """Store a turn only when the reply succeeded and is not an error."""
        if self.memory is None or not result.ok or is_error_text(result.text):
            return None
        return self.memory.store(f"User: {user_text} | Assistant: {result.text}", metadata={"role": role})

    # -- routing ------------------------------------------------------------
    def _ask_router(self, prompt):
        r = self.run_role("intent_router", text=prompt, system=self.role_prompt("intent_router"),
                          temperature=0.0, max_tokens=12)
        return r.text if r.ok else None

    def route_turn(self, text):
        use = self.cluster.get("routing_settings", {}).get("use_intent_router", True) and self.is_set("intent_router")
        return intent.route(text, self.is_set, ask_fn=self._ask_router if use else None)

    def turn(self, text, history, role=None, media=None):
        """One chat turn end to end. role/media force a route (slash commands).

        Returns dict(route, pre, result, trace, files, blocked). `pre` is the
        media role's result when one ran first; `result` is the final reply
        (None when blocked or when a media step failed)."""
        if role:
            rt = {"role": role, "reason": "command", "media": media or [], "text": text, "via": "command"}
        else:
            rt = self.route_turn(text)
        out = {"route": rt, "pre": None, "result": None, "trace": [], "files": [], "blocked": None}
        gs = self.cluster.get("guard_settings", {})
        if gs.get("check_input") and self.is_set("guard_translate"):
            ok, why = self.guard_check(text)
            if not ok and gs.get("block_on_unsafe", True):
                out["blocked"] = f"input blocked by guard: {why}"
                return out
        role = rt["role"]
        body = rt["text"]
        if role in ("image_gen", "audio_gen"):
            out["result"] = self.run_role(role, prompt=body)
            out["files"] = out["result"].files
            return out
        if role == "guard_translate":
            out["result"] = self.translate(body)
            return out
        if role in MEDIA_ROLES:
            ref = rt["media"][0][1] if rt["media"] else body
            field = {"video": "video", "asr": "audio", "omni_audio": "audio"}.get(role, "image")
            pre = self.run_role(role, **{field: ref, "prompt": body if rt["media"] else None})
            out["pre"] = pre
            if not pre.ok:
                return out
            name = os.path.basename(ref) if not ref.startswith("data:") else "the attachment"
            if role == "asr":
                body = pre.text if not body or body == ref else f"{body}\n\n(Voice message transcript: {pre.text})"
            else:
                body = (f"{R.label(role)} output for {name}:\n{pre.text}\n\nUser: {body or 'Tell me about it.'}")
            role = "persona"
        if role not in TEXT_ROLES or not self.is_set(role):
            role = "persona"
        block = self.recall_block(body)
        history.append({"role": "user", "content": f"{block}\nUser Input: {body}" if block else body})
        result, trace = self.respond(role, history)
        out["trace"] = trace
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
        self.remember_turn(body, result, role)
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
