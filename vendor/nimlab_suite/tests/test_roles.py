"""v3.2: the 16 roles, migration, candidate filters, routing, reranker,
MCP-tool backends and voice cloning. Offline: every network call goes to a
fake (tests/fakes.py)."""

import base64
import io
import json
import os
import tempfile
import unittest
import wave
from unittest import mock

from nimlab import config, intent, rolemcp, rolemenu, roles as R, voiceclone
from nimlab.api import NimClient
from nimlab.core import HttpClient
from nimlab.entity import Entity, parse_safety
from nimlab.mcp import MCPClient
from nimlab.memory import MemoryCore
from tests.fakes import FakeMCPServer, FakeResponse, RouteOpener, make_wav

OLD_ROLES = {
    "main_brain": "poolside/laguna-xs-2.1",
    "deep_reasoning": "mistralai/mistral-large-4-1t-a52b",
    "coding_agent": "google/gemma-4-31b-it",
    "vision": "nvidia/nemotron-3.5-super-vl-120b-a12b",
    "ocr_document": "nvidia/nemotron-parse-2.0",
    "embedding": "nvidia/llama-nemotron-embed-vl-1b-v2",
    "compactor": "nvidia/nemotron-3.5-bolt-e4b",
    "my_custom_role": "someone/custom-model",
}
FLEET_KINDS = {
    "nvidia/nemotron-3.5-bolt-e4b": "chat",
    "poolside/laguna-xs-2.1": "chat",
    "google/deplot": "vision",
    "nvidia/llama-nemotron-rerank-1b-v2": "rerank",
    "black-forest-labs/flux.1-dev": "image_gen",
    "nvidia/magpie-tts-zeroshot": "tts",
    "nvidia/llama-3.1-nemoguard-8b-content-safety": "safety",
    "nvidia/cosmos-reason2-8b": "chat",
    "nvidia/parakeet-ctc-1.1b-asr": "asr",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": "vision",
    "meta/llama-3.2-11b-vision-instruct": "vision",
}


def tmpdir(test):
    d = tempfile.TemporaryDirectory()
    test.addCleanup(d.cleanup)
    return d.name


def make_entity(test, roles, opener=None, mcp_server=None, mcp_enabled=False, extra=None):
    """An Entity on fakes: model calls go to `opener`, the MCP server is
    `mcp_server`, outputs go to a temp output/, memory to a temp file."""
    out = tmpdir(test)
    p = mock.patch.object(config, "OUTPUT_DIR", out)
    p.start()
    test.addCleanup(p.stop)
    cluster = config.deep_merge(config.DEFAULT_CLUSTER, {"roles": roles})
    cluster["mcp_settings"] = dict(cluster.get("mcp_settings", {}), url="https://mcp.test/mcp",
                                   enabled=mcp_enabled, allowed_tools=[], confirm_tool_calls=False)
    for k, v in (extra or {}).items():
        cluster[k] = config.deep_merge(cluster.get(k, {}), v)
    client = NimClient(api_key="nvapi-test", cluster=cluster, http=HttpClient(opener=opener or RouteOpener([])))
    role_mcp = None
    if mcp_server is not None:
        role_mcp = MCPClient(cluster["mcp_settings"], http=HttpClient(opener=mcp_server, retries=0), env={})
    ent = Entity(cluster=cluster, prompts={}, soul="soul", client=client, memory=False, log=lambda *a: None,
                 role_mcp=role_mcp, fetch=lambda url: b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 300)
    ent.memory = MemoryCore(client, R.model_of(roles.get("embedding")) or "",
                            path=os.path.join(tmpdir(test), "mem.json"), embed_fn=ent._embed_fn())
    return ent, out


# ---------------------------------------------------------------------------
class TestRoleDefinitions(unittest.TestCase):
    def test_sixteen_roles_with_display_names(self):
        self.assertEqual(len(R.ROLE_KEYS), 16)
        names = [d.name for d in R.ROLE_DEFS]
        for n in ("Intent Router / Fast Dispatcher", "Conversational Persona LLM",
                  "Agentic Long-Context & Reasoning Model", "Dedicated Coding & Tool-Calling Model",
                  "Multimodal Vision-Language Model (VLM)", "Document & Structured OCR Model",
                  "Chart & Plot Parser", "Video & Temporal Understanding Model",
                  "Automatic Speech Recognition (ASR / STT)",
                  "Omni-Modal Audio-Language Model (Music & Ambient Audio)", "Neural Text-to-Speech (TTS)",
                  "Text-to-Image Generation Model", "Audio / Music Generation Model",
                  "Dense Text & Multimodal Embedding Model", "Semantic Reranker Model",
                  "Translation & Guardrail Model"):
            self.assertIn(n, names)

    def test_unservable_role_says_so(self):
        self.assertEqual(R.BY_KEY["audio_gen"].support, R.NO)
        self.assertIn("MCP", R.BY_KEY["audio_gen"].note)
        self.assertIn("not available", rolemenu.support_tag("audio_gen"))
        self.assertEqual(rolemenu.support_tag("persona"), "")

    def test_plain_string_is_a_model_backend(self):
        v = R.normalize("a/b", "persona")
        self.assertEqual((v["backend"], v["model"], v["label"]), ("model", "a/b", "Conversational Persona LLM"))
        self.assertEqual(R.model_of("a/b"), "a/b")
        self.assertFalse(R.is_set(None))
        self.assertFalse(R.is_set({"backend": "mcp", "tool": None}))
        self.assertTrue(R.is_set({"backend": "mcp", "tool": "t"}))
        self.assertIsNone(R.model_of({"backend": "mcp", "tool": "t"}))
        self.assertEqual(R.describe({"backend": "mcp", "tool": "t"}), "[MCP] t")
        self.assertEqual(R.describe("a/b"), "[model] a/b")
        self.assertEqual(R.describe(None), "(unset)")


class TestMigration(unittest.TestCase):
    def test_old_roles_map_to_new_keys(self):
        new, changes = R.migrate_roles(OLD_ROLES)
        self.assertEqual(R.model_of(new["persona"]), "poolside/laguna-xs-2.1")
        self.assertEqual(R.model_of(new["reasoning"]), "mistralai/mistral-large-4-1t-a52b")
        self.assertEqual(R.model_of(new["coding"]), "google/gemma-4-31b-it")
        self.assertEqual(R.model_of(new["vision"]), "nvidia/nemotron-3.5-super-vl-120b-a12b")
        self.assertEqual(R.model_of(new["ocr"]), "nvidia/nemotron-parse-2.0")
        self.assertEqual(R.model_of(new["embedding"]), "nvidia/llama-nemotron-embed-vl-1b-v2")
        for old in ("main_brain", "deep_reasoning", "coding_agent", "ocr_document"):
            self.assertNotIn(old, new)
        # unmappable keys are kept untouched
        self.assertEqual(new["compactor"], "nvidia/nemotron-3.5-bolt-e4b")
        self.assertEqual(new["my_custom_role"], "someone/custom-model")
        self.assertTrue(all(k in new for k in R.ROLE_KEYS))
        self.assertTrue(any("main_brain -> persona" in c for c in changes))

    def test_missing_roles_default_from_verified_fleet_else_unset(self):
        fleet = list(FLEET_KINDS)
        new, _ = R.migrate_roles(OLD_ROLES, fleet, FLEET_KINDS)
        self.assertEqual(R.model_of(new["chart_parser"]), "google/deplot")
        self.assertEqual(R.model_of(new["reranker"]), "nvidia/llama-nemotron-rerank-1b-v2")
        self.assertEqual(R.model_of(new["image_gen"]), "black-forest-labs/flux.1-dev")
        self.assertEqual(R.model_of(new["tts"]), "nvidia/magpie-tts-zeroshot")
        self.assertEqual(R.model_of(new["guard_translate"]), "nvidia/llama-3.1-nemoguard-8b-content-safety")
        self.assertEqual(R.model_of(new["asr"]), "nvidia/parakeet-ctc-1.1b-asr")
        self.assertEqual(R.model_of(new["video"]), "nvidia/cosmos-reason2-8b")
        self.assertEqual(R.model_of(new["intent_router"]), "nvidia/nemotron-3.5-bolt-e4b")  # = compactor
        self.assertIsNone(R.model_of(new["audio_gen"]))                                       # none hosted
        bare, _ = R.migrate_roles(OLD_ROLES)                                                  # no fleet
        self.assertIsNone(R.model_of(bare["reranker"]))

    def test_explicit_new_key_wins_and_unset_stays_unset(self):
        new, _ = R.migrate_roles({"main_brain": "old/m", "persona": "new/m", "reranker": None},
                                 list(FLEET_KINDS), FLEET_KINDS)
        self.assertEqual(R.model_of(new["persona"]), "new/m")
        self.assertEqual(new["main_brain"], "old/m")          # kept, not lost
        self.assertIsNone(R.model_of(new["reranker"]))       # user's null respected

    def test_idempotent_and_mcp_roles_survive(self):
        once, _ = R.migrate_roles(OLD_ROLES, list(FLEET_KINDS), FLEET_KINDS)
        once["tts"] = {"label": "x", "backend": "mcp", "tool": "speak", "arg_map": {"text": "input"},
                       "voice_clone": {"path": "/a.wav"}}
        twice, _ = R.migrate_roles(once, list(FLEET_KINDS), FLEET_KINDS)
        self.assertEqual(once, twice)
        self.assertFalse(R.needs_migration(twice))
        self.assertTrue(R.needs_migration(OLD_ROLES))

    def test_load_cluster_config_rewrites_old_file_once_with_backup(self):
        d = tmpdir(self)
        path = os.path.join(d, "config_cluster.json")
        with open(path, "w") as f:
            json.dump({"roles": OLD_ROLES, "voice_settings": {"voice_name": "Magpie-Multilingual.EN-US.Jason"},
                       "judge_settings": {"entity_combos": [{"name": "a", "roles": {"main_brain": "x/y"}}]}}, f)
        env = {"NIMLAB_DATA_DIR": os.path.join(d, "data")}
        with mock.patch.dict(os.environ, env), mock.patch.dict(os.environ, {"NIMLAB_CONFIG_READONLY": ""}):
            with mock.patch("sys.stderr", io.StringIO()):
                cfg = config.load_cluster_config(path)
            with open(path) as f:
                saved = json.load(f)
            self.assertEqual(R.model_of(saved["roles"]["persona"]), "poolside/laguna-xs-2.1")
            self.assertEqual(saved["voice_settings"]["voice_name"], "Magpie-Multilingual.EN-US.Jason")
            self.assertEqual(saved["judge_settings"]["entity_combos"][0]["roles"], {"persona": "x/y"})
            self.assertEqual(R.model_of(cfg["roles"]["reasoning"]), "mistralai/mistral-large-4-1t-a52b")
            backups = os.listdir(os.path.join(d, "data", "legacy"))
            self.assertEqual(len(backups), 1)
            mtime = os.path.getmtime(path)
            config.load_cluster_config(path)          # second load: nothing to migrate, no rewrite
            self.assertEqual(os.path.getmtime(path), mtime)
            self.assertEqual(len(os.listdir(os.path.join(d, "data", "legacy"))), 1)

    def test_readonly_env_never_writes(self):
        d = tmpdir(self)
        path = os.path.join(d, "c.json")
        with open(path, "w") as f:
            json.dump({"roles": OLD_ROLES}, f)
        with mock.patch.dict(os.environ, {"NIMLAB_CONFIG_READONLY": "1", "NIMLAB_DATA_DIR": d}):
            cfg = config.load_cluster_config(path)
        self.assertIn("persona", cfg["roles"])
        with open(path) as f:
            self.assertIn("main_brain", json.load(f)["roles"])

    def test_prompts_migrate(self):
        new, changed = config.migrate_prompts({"main_brain": "P", "ocr_document": "O"})
        self.assertTrue(changed)
        self.assertEqual(new["persona"], "P")
        self.assertEqual(new["ocr"], "O")
        self.assertIn("chart_parser", new)
        self.assertNotIn("main_brain", new)

    def test_starter_config_has_all_roles(self):
        from nimlab import defaults
        for k in R.ROLE_KEYS:
            self.assertIn(k, defaults.STARTER_CLUSTER["roles"])
            self.assertEqual(defaults.STARTER_CLUSTER["roles"][k]["label"], R.label(k))


class TestCandidates(unittest.TestCase):
    def tiers(self, key, models=None):
        return R.candidates(key, models or list(FLEET_KINDS), FLEET_KINDS)

    def test_chart_parser_prefers_chart_models_then_vlms(self):
        s, p, o = self.tiers("chart_parser")
        self.assertEqual(s, ["google/deplot"])
        self.assertIn("meta/llama-3.2-11b-vision-instruct", p)
        self.assertIn("poolside/laguna-xs-2.1", o)

    def test_each_category_filter(self):
        cases = {
            "reranker": "nvidia/llama-nemotron-rerank-1b-v2",
            "image_gen": "black-forest-labs/flux.1-dev",
            "tts": "nvidia/magpie-tts-zeroshot",
            "asr": "nvidia/parakeet-ctc-1.1b-asr",
            "video": "nvidia/cosmos-reason2-8b",
            "omni_audio": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "guard_translate": "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "intent_router": "nvidia/nemotron-3.5-bolt-e4b",
            "vision": "meta/llama-3.2-11b-vision-instruct",
        }
        for key, model in cases.items():
            s, _, _ = self.tiers(key)
            self.assertIn(model, s, key)
        self.assertNotIn("google/deplot", self.tiers("vision")[0])        # chart model is not a general VLM
        self.assertNotIn("nvidia/magpie-tts-zeroshot", self.tiers("omni_audio")[0])
        self.assertNotIn("nvidia/llama-3.1-nemoguard-8b-content-safety", self.tiers("persona")[0])
        self.assertEqual(self.tiers("audio_gen")[0], [])

    def test_unknown_kind_uses_router_types(self):
        s, p, _ = R.candidates("embedding", ["nvidia/nv-embedqa-e5-v5", "meta/llama-3.1-8b-instruct"], {})
        self.assertIn("nvidia/nv-embedqa-e5-v5", s)

    def test_menu_shows_suited_first_and_keeps_list_prompt(self):
        verified = ["poolside/laguna-xs-2.1", "google/deplot", "meta/llama-3.2-11b-vision-instruct"]
        discovered = verified + ["nvidia/nemotron-graphic-elements-v1"]
        out = []
        answers = iter(["", "1"])          # Enter = verified list, then pick #1
        model, cancelled = rolemenu.choose_model("chart_parser", lambda p: next(answers), out.append,
                                                 verified, discovered, FLEET_KINDS, {})
        text = "\n".join(out)
        self.assertIn("Verified 200 OK (3)", text)
        self.assertIn("All discovered (4)", text)
        self.assertLess(text.index("google/deplot"), text.index("meta/llama-3.2-11b-vision-instruct"))
        self.assertEqual((model, cancelled), ("google/deplot", False))

    def test_menu_unverified_note_and_unset(self):
        verified = ["google/deplot"]
        discovered = verified + ["nvidia/nemotron-graphic-elements-v1"]
        out = []
        answers = iter(["2", "2"])
        model, _ = rolemenu.choose_model("chart_parser", lambda p: next(answers), out.append,
                                         verified, discovered, {}, {})
        self.assertEqual(model, "nvidia/nemotron-graphic-elements-v1")
        self.assertTrue(any("hasn't passed the 200 OK test" in o for o in out))
        answers = iter(["", "-"])
        self.assertEqual(rolemenu.choose_model("chart_parser", lambda p: next(answers), out.append,
                                               verified, discovered, {}, {}), (None, False))


class TestRouting(unittest.TestCase):
    ALL = set(R.ROLE_KEYS)

    def r(self, text, setroles=None, ask=None, files=()):
        s = self.ALL if setroles is None else set(setroles)
        return intent.route(text, lambda k: k in s, ask_fn=ask, exists=lambda p: p in files)

    def test_media_routes(self):
        self.assertEqual(self.r("what's in /a/b.png", files=["/a/b.png"])["role"], "vision")
        self.assertEqual(self.r("read the text in /a/b.jpg", files=["/a/b.jpg"])["role"], "ocr")
        self.assertEqual(self.r("what does this chart show /a/c.png", files=["/a/c.png"])["role"], "chart_parser")
        self.assertEqual(self.r("summarize https://x.test/clip.mp4")["role"], "video")
        self.assertEqual(self.r("https://youtu.be/abc what happens")["role"], "video")
        self.assertEqual(self.r("/m/voice.wav", files=["/m/voice.wav"])["role"], "asr")
        self.assertEqual(self.r("what genre is this song /m/s.mp3", files=["/m/s.mp3"])["role"], "omni_audio")
        rt = self.r("what's in /a/b.png", files=["/a/b.png"])
        self.assertEqual(rt["media"], [("image", "/a/b.png")])
        self.assertNotIn("/a/b.png", rt["text"])

    def test_missing_file_is_not_media(self):
        self.assertEqual(self.r("what's in /nope.png", setroles={"persona", "vision"})["role"], "persona")

    def test_fallbacks_when_roles_unset(self):
        self.assertEqual(self.r("the chart /a/c.png", {"persona", "vision"}, files=["/a/c.png"])["role"], "vision")
        self.assertEqual(self.r("clip.mp4 https://x.test/clip.mp4", {"persona", "vision"})["role"], "vision")
        self.assertEqual(self.r("fix this python bug", {"persona"})["role"], "persona")

    def test_keyword_routes(self):
        self.assertEqual(self.r("fix this python function")["role"], "coding")
        self.assertEqual(self.r("think step by step about the architecture trade-offs")["role"], "reasoning")
        self.assertEqual(self.r("draw an image of a fox")["role"], "image_gen")
        self.assertEqual(self.r("compose a short piano melody")["role"], "audio_gen")
        self.assertEqual(self.r("translate good night into French")["role"], "guard_translate")
        self.assertEqual(self.r("hey how was your day")["role"], "persona")

    def test_intent_router_model_decides(self):
        prompts = []

        def ask(p):
            prompts.append(p)
            return "reasoning"
        rt = self.r("hey how was your day", ask=ask)
        self.assertEqual((rt["role"], rt["via"]), ("reasoning", "router"))
        self.assertIn("- coding:", prompts[0])
        rt = self.r("hello", setroles={"persona", "coding"}, ask=lambda p: "I'd say image_gen")
        self.assertEqual(rt["role"], "persona")    # image_gen not set, so not offered or accepted
        rt = self.r("fix python", ask=lambda p: None)
        self.assertEqual((rt["role"], rt["via"]), ("coding", "rules"))

    def test_parse_label(self):
        self.assertEqual(intent.parse_label("Label: coding.", ["persona", "coding"]), "coding")
        self.assertIsNone(intent.parse_label("no idea", ["persona", "coding"]))


def chat_reply(text):
    return {"choices": [{"message": {"content": text}}], "usage": {"completion_tokens": 3}}


class TestEntityTurns(unittest.TestCase):
    def test_turn_goes_to_routed_role_model(self):
        calls = []

        def chat(req):
            body = json.loads(req.data)
            calls.append(body["model"])
            if body["model"] == "r/router":
                return chat_reply("coding")
            return chat_reply(f"answer from {body['model']}")
        opener = RouteOpener([("chat/completions", chat)])
        roles = {"intent_router": "r/router", "persona": "p/persona", "coding": "c/coder"}
        ent, _ = make_entity(self, roles, opener)
        hist = []
        out = ent.turn("please help", hist)
        self.assertEqual(out["route"]["role"], "coding")
        self.assertEqual(calls, ["r/router", "c/coder"])
        self.assertEqual(out["result"].text, "answer from c/coder")
        self.assertEqual(hist[-1]["content"], "answer from c/coder")

    def test_image_turn_runs_vision_then_persona(self):
        models = []

        def chat(req):
            body = json.loads(req.data)
            models.append(body["model"])
            return chat_reply("a red square" if body["model"] == "v/vlm" else "Nice square!")
        img = os.path.join(tmpdir(self), "pic.png")
        with open(img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"0" * 50)
        ent, _ = make_entity(self, {"persona": "p/persona", "vision": "v/vlm"}, RouteOpener([("chat/", chat)]))
        out = ent.turn(f"what is this {img}", [])
        self.assertEqual(out["route"]["role"], "vision")
        self.assertEqual(models, ["v/vlm", "p/persona"])
        self.assertEqual(out["pre"].text, "a red square")
        self.assertEqual(out["result"].text, "Nice square!")

    def test_guard_blocks_unsafe_input(self):
        def chat(req):
            body = json.loads(req.data)
            if "guard" in body["model"]:
                return chat_reply('{"User Safety": "unsafe", "Safety Categories": "Violence"}')
            return chat_reply("should not run")
        ent, _ = make_entity(self, {"persona": "p/x", "guard_translate": "nvidia/nemoguard"},
                             RouteOpener([("chat/", chat)]), extra={"guard_settings": {"check_input": True}})
        out = ent.turn("bad stuff", [])
        self.assertIn("Violence", out["blocked"])
        self.assertIsNone(out["result"])

    def test_parse_safety(self):
        self.assertEqual(parse_safety('{"User Safety": "safe"}')[0], True)
        self.assertEqual(parse_safety("UNSAFE: weapons")[0], False)
        self.assertIsNone(parse_safety("hmm")[0])

    def test_unset_role_reports_cleanly(self):
        ent, _ = make_entity(self, {"persona": "p/x"})
        r = ent.run_role("reranker", query="q", passages=["a"])
        self.assertFalse(r.ok)
        self.assertIn("not set", r.error)

    def test_image_gen_and_rerank_models(self):
        png = b"\x89PNG\r\n\x1a\n" + b"1" * 40
        opener = RouteOpener([
            ("/genai/", lambda req: {"artifacts": [{"base64": base64.b64encode(png).decode()}]}),
            ("/reranking", lambda req: {"rankings": [{"index": 1, "logit": 5.0}, {"index": 0, "logit": -2.0},
                                                     {"index": 2, "logit": -9.0}]}),
        ])
        ent, out = make_entity(self, {"image_gen": "black-forest-labs/flux.1-dev",
                                      "reranker": "nvidia/llama-nemotron-rerank-1b-v2"}, opener)
        r = ent.run_role("image_gen", prompt="a cube")
        self.assertTrue(r.ok, r.error)
        self.assertTrue(r.files[0].startswith(out) and r.files[0].endswith(".png"))
        res = ent.test_role("reranker")
        self.assertTrue(res["ok"], res)
        self.assertIn("correct", res["summary"])
        rr = [q for q in opener.requests if "reranking" in q["url"]][0]
        self.assertIn("/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking", rr["url"])

    def test_test_role_reports_status_and_latency(self):
        ent, _ = make_entity(self, {"persona": "p/x"},
                             RouteOpener([("chat/", lambda req: FakeResponse({"detail": "nope"}, status=404))]))
        res = ent.test_role("persona")
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], 404)
        self.assertIn("latency", res)
        self.assertIn("FAIL", "\n".join(rolemenu.format_test("persona", res)))


class TestReranker(unittest.TestCase):
    def mem(self, vectors):
        class C:
            def embed(self, model, texts, input_type=None, url=None):
                from nimlab.api import ModelResult
                return ModelResult(True, data=[vectors[texts[0]]])
        m = MemoryCore(C(), "e/m", path=os.path.join(tmpdir(self), "m.json"))
        return m

    def test_rerank_reorders_and_cuts_to_top_k(self):
        vecs = {"q": [1, 0], "a": [0.99, 0.1], "b": [0.9, 0.3], "c": [0.8, 0.5], "d": [0.7, 0.7]}
        m = self.mem(vecs)
        for t in "abcd":
            m.store(t)
        hits, info = m.recall_reranked("q", top_k=2, threshold=0.1, candidates=4,
                                       rerank_fn=lambda q, ps: [(ps.index("d"), 9.0), (ps.index("c"), 5.0)])
        self.assertEqual([h[1] for h in hits], ["d", "c"])
        self.assertEqual(info, {"reranked": True, "pool": 4})

    def test_rerank_failure_falls_back_to_cosine(self):
        vecs = {"q": [1, 0], "a": [0.99, 0.1], "b": [0.5, 0.5]}
        m = self.mem(vecs)
        m.store("a")
        m.store("b")

        def boom(q, ps):
            raise RuntimeError("HTTP 500")
        hits, info = m.recall_reranked("q", top_k=1, threshold=0.1, rerank_fn=boom)
        self.assertEqual([h[1] for h in hits], ["a"])
        self.assertFalse(info["reranked"])
        self.assertIn("500", info["reason"])
        self.assertEqual(m.recall_reranked("q", 1, 0.1)[1], {"reranked": False})

    def test_entity_recall_uses_reranker_role(self):
        def embed(req):
            text = json.loads(req.data)["input"][0]
            return {"data": [{"embedding": {"q": [1, 0], "alpha": [0.99, 0.1], "beta": [0.9, 0.4]}[text]}]}
        opener = RouteOpener([("embeddings", embed),
                              ("reranking", lambda req: {"rankings": [{"index": 1, "logit": 3}, {"index": 0, "logit": 1}]})])
        ent, _ = make_entity(self, {"embedding": "e/m", "reranker": "nvidia/rr"}, opener,
                             extra={"memory_settings": {"recall_top_k": 1, "similarity_threshold": 0.1}})
        ent.memory.store("alpha")
        ent.memory.store("beta")
        hits, info = ent.recall("q")
        self.assertTrue(info["reranked"])
        self.assertEqual(hits[0][1], "beta")


# ---------------------------------------------------------------------------
TOOLS = [
    {"name": "speak", "description": "Text to speech with an optional voice sample",
     "inputSchema": {"type": "object", "required": ["input"],
                     "properties": {"input": {"type": "string"}, "speaker_wav": {"type": "string",
                                                                                "description": "base64 WAV"},
                                    "voice": {"type": "string"}}}},
    {"name": "describe_image", "description": "Describe an image",
     "inputSchema": {"type": "object", "required": ["image_url"],
                     "properties": {"image_url": {"type": "string", "format": "uri"},
                                    "question": {"type": "string"}}}},
    {"name": "rank_docs", "description": "Rerank documents",
     "inputSchema": {"type": "object", "required": ["query", "documents"],
                     "properties": {"query": {"type": "string"},
                                    "documents": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "make_song", "description": "Generate music",
     "inputSchema": {"type": "object", "required": ["prompt"],
                     "properties": {"prompt": {"type": "string"}, "seconds": {"type": "integer"}}}},
    {"name": "transcribe", "description": "Speech to text from a local path",
     "inputSchema": {"type": "object", "required": ["audio_path"],
                     "properties": {"audio_path": {"type": "string"}, "language": {"type": "string"}}}},
]


class TestMCPRoleBackend(unittest.TestCase):
    def server(self, handlers=None, down=False):
        return FakeMCPServer(TOOLS, handlers or {}, down=down)

    def test_auto_arg_map(self):
        t = {x["name"]: x for x in TOOLS}
        self.assertEqual(rolemcp.auto_arg_map("tts", t["speak"]),
                         {"text": "input", "voice": "voice", "reference_audio": "speaker_wav"})
        self.assertEqual(rolemcp.auto_arg_map("vision", t["describe_image"]),
                         {"image": "image_url", "prompt": "question"})
        self.assertEqual(rolemcp.auto_arg_map("reranker", t["rank_docs"]),
                         {"query": "query", "passages": "documents"})
        self.assertEqual(rolemcp.auto_arg_map("audio_gen", t["make_song"]),
                         {"prompt": "prompt", "duration": "seconds"})
        self.assertEqual(rolemcp.auto_arg_map("asr", t["transcribe"]),
                         {"audio": "audio_path", "language": "language"})
        self.assertEqual(rolemcp.unmapped_required(t["rank_docs"], {"query": "query"}), ["documents"])

    def test_build_arguments_encodes_files(self):
        d = tmpdir(self)
        img = os.path.join(d, "a.png")
        with open(img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nxx")
        t = {x["name"]: x for x in TOOLS}
        a = rolemcp.build_arguments(t["describe_image"], {"image": "image_url"}, {"image": img})
        self.assertTrue(a["image_url"].startswith("data:image/png;base64,"))
        a = rolemcp.build_arguments(t["speak"], {"reference_audio": "speaker_wav"}, {"reference_audio": img})
        self.assertEqual(base64.b64decode(a["speaker_wav"])[:4], b"\x89PNG")      # plain base64 per description
        a = rolemcp.build_arguments(t["transcribe"], {"audio": "audio_path"}, {"audio": img})
        self.assertEqual(a["audio_path"], img)                                  # *_path gets the path
        a = rolemcp.build_arguments(t["describe_image"], {"image": "image_url:base64"}, {"image": img})
        self.assertNotIn("data:", a["image_url"])                               # forced encoding
        a = rolemcp.build_arguments(t["make_song"], {"prompt": "prompt", "duration": "seconds"},
                                    {"prompt": "lofi", "duration": "7"})
        self.assertEqual(a, {"prompt": "lofi", "seconds": 7})
        with self.assertRaises(ValueError):
            rolemcp.build_arguments(t["describe_image"], {"image": "image_url"}, {"image": "/no/such.png"})

    def test_menu_lists_tools_picks_and_maps(self):
        srv = self.server()
        ent, _ = make_entity(self, {"persona": "p/x"}, mcp_server=srv)
        saved = []
        out = []
        answers = iter(["2", "3", ""])   # backend MCP, tool #3 (rank_docs), keep auto mapping
        changed = rolemenu.configure_role(ent, "reranker", lambda p: next(answers), out.append,
                                          save_fn=lambda: saved.append(1))
        self.assertTrue(changed)
        self.assertEqual(saved, [1])
        text = "\n".join(out)
        self.assertIn("speak: Text to speech", text)
        self.assertIn("rank_docs: Rerank documents", text)
        self.assertEqual(ent.roles["reranker"]["backend"], "mcp")
        self.assertEqual(ent.roles["reranker"]["tool"], "rank_docs")
        self.assertEqual(ent.roles["reranker"]["arg_map"], {"query": "query", "passages": "documents"})
        self.assertIn("[MCP] rank_docs", "\n".join(rolemenu.role_lines(ent.roles)))

    def test_menu_edit_mapping(self):
        ent, _ = make_entity(self, {}, mcp_server=self.server())
        answers = iter(["2", "describe_image", "y", "image_url:base64", "-"])
        rolemenu.configure_role(ent, "vision", lambda p: next(answers), lambda *a: None)
        self.assertEqual(ent.roles["vision"]["arg_map"], {"image": "image_url:base64"})

    def test_unreachable_server_leaves_role_untouched(self):
        ent, _ = make_entity(self, {"reranker": "nvidia/rr"}, mcp_server=self.server(down=True))
        before = json.dumps(ent.roles, sort_keys=True)
        out = []
        answers = iter(["2"])
        changed = rolemenu.configure_role(ent, "reranker", lambda p: next(answers), out.append,
                                          save_fn=lambda: self.fail("must not save"))
        self.assertFalse(changed)
        self.assertTrue(any("unreachable" in o for o in out))
        self.assertEqual(json.dumps(ent.roles, sort_keys=True), before)

    def test_calls_mcp_tool_for_reranker_in_recall(self):
        srv = self.server({"rank_docs": lambda a: {"content": [{"type": "text", "text": json.dumps(
            {"results": [{"index": 1, "relevance_score": 0.9}, {"index": 0, "relevance_score": 0.1}]})}]}})
        ent, _ = make_entity(self, {"reranker": {"backend": "mcp", "tool": "rank_docs",
                                                 "arg_map": {"query": "query", "passages": "documents"}}},
                             mcp_server=srv)
        r = ent.run_role("reranker", query="capital?", passages=["Berlin", "Paris"])
        self.assertTrue(r.ok, r.error)
        self.assertEqual(r.data[0][0], 1)
        self.assertEqual(srv.calls, [("rank_docs", {"query": "capital?", "documents": ["Berlin", "Paris"]})])

    def test_mcp_tts_saves_base64_audio_and_sends_clone(self):
        wav = make_wav(1.0)
        srv = self.server({"speak": lambda a: {"content": [
            {"type": "audio", "mimeType": "audio/wav", "data": base64.b64encode(wav).decode()}]}})
        clip = os.path.join(tmpdir(self), "me.wav")
        with open(clip, "wb") as f:
            f.write(make_wav(4.0))
        roles = {"tts": {"backend": "mcp", "tool": "speak", "arg_map": {"text": "input",
                                                                        "reference_audio": "speaker_wav"},
                         "voice_clone": {"path": clip}}}
        ent, out = make_entity(self, roles, mcp_server=srv)
        path, r = ent.synthesize_voice("hello", play=False)
        self.assertTrue(r.ok, r.error)
        self.assertTrue(path.startswith(out) and path.endswith(".wav"))
        with open(path, "rb") as f:
            self.assertEqual(f.read(), wav)
        name, args = srv.calls[0]
        self.assertEqual(args["input"], "hello")
        self.assertEqual(base64.b64decode(args["speaker_wav"])[:4], b"RIFF")

    def test_mcp_audio_gen_url_result_is_downloaded(self):
        srv = self.server({"make_song": lambda a: {"content": [
            {"type": "text", "text": "Done: https://cdn.test/out/song.wav"}]}})
        ent, out = make_entity(self, {"audio_gen": {"backend": "mcp", "tool": "make_song", "arg_map": {}}},
                               mcp_server=srv)
        r = ent.run_role("audio_gen", prompt="lofi beat", duration=5)
        self.assertTrue(r.ok, r.error)
        self.assertTrue(r.files[0].endswith(".wav"))
        self.assertEqual(srv.calls[0][1], {"prompt": "lofi beat", "seconds": 5})   # auto map at call time

    def test_mcp_tool_error_and_missing_tool(self):
        srv = self.server({"describe_image": lambda a: {"isError": True,
                                                        "content": [{"type": "text", "text": "bad image"}]}})
        ent, _ = make_entity(self, {"vision": {"backend": "mcp", "tool": "describe_image",
                                               "arg_map": {"image": "image_url"}},
                                    "ocr": {"backend": "mcp", "tool": "gone", "arg_map": {}}}, mcp_server=srv)
        r = ent.run_role("vision", image="https://x.test/a.png")
        self.assertFalse(r.ok)
        self.assertIn("bad image", r.error)
        r = ent.run_role("ocr", image="https://x.test/a.png")
        self.assertIn("no longer lists", r.error)

    def test_test_role_uses_mcp_and_unreachable_is_reported(self):
        srv = self.server({"transcribe": lambda a: {"content": [{"type": "text", "text": "hello world"}]}})
        ent, _ = make_entity(self, {"asr": {"backend": "mcp", "tool": "transcribe",
                                            "arg_map": {"audio": "audio_path"}}}, mcp_server=srv)
        res = ent.test_role("asr")
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["backend"], "mcp")
        self.assertEqual(res["summary"], "hello world")
        self.assertTrue(srv.calls[0][1]["audio_path"].endswith("magpie_aria_sample.wav"))
        ent2, _ = make_entity(self, {"asr": {"backend": "mcp", "tool": "transcribe", "arg_map": {}}},
                              mcp_server=self.server(down=True))
        res = ent2.test_role("asr")
        self.assertFalse(res["ok"])
        self.assertIn("MCP server", res["error"])

    def test_routed_turn_through_mcp_role(self):
        srv = self.server({"describe_image": lambda a: {"content": [{"type": "text", "text": "a cat"}]}})
        img = os.path.join(tmpdir(self), "c.png")
        with open(img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        ent, _ = make_entity(self, {"persona": "p/x", "vision": {"backend": "mcp", "tool": "describe_image",
                                                                 "arg_map": {"image": "image_url",
                                                                             "prompt": "question"}}},
                             RouteOpener([("chat/", lambda req: chat_reply("It's a cat!"))]), mcp_server=srv)
        out = ent.turn(f"what animal {img}", [])
        self.assertEqual(out["pre"].text, "a cat")
        self.assertEqual(out["result"].text, "It's a cat!")
        self.assertEqual(srv.calls[0][1]["question"], "what animal")

    def test_extract_variants(self):
        png = b"\x89PNG\r\n\x1a\n" + b"z" * 300
        d = tmpdir(self)
        with mock.patch.object(config, "OUTPUT_DIR", d):
            text, files, _ = rolemcp.extract({"content": [{"type": "text", "text": json.dumps(
                {"image_base64": base64.b64encode(png).decode()})}]}, prefix="t")
            self.assertTrue(files and files[0].endswith(".png"))
            _, files, _ = rolemcp.extract({"content": [{"type": "resource", "resource": {
                "uri": "x", "mimeType": "audio/wav", "blob": base64.b64encode(make_wav(0.1)).decode()}}]})
            self.assertTrue(files[0].endswith(".wav"))

    def test_parsers(self):
        self.assertEqual(rolemcp.parse_vector("[0.1, 2]"), [0.1, 2.0])
        self.assertEqual(rolemcp.parse_vector('{"embedding": [1, 2]}'), [1.0, 2.0])
        self.assertIsNone(rolemcp.parse_vector("no"))
        self.assertEqual(rolemcp.parse_rankings("[2, 0, 1]", 3)[0][0], 2)
        self.assertIsNone(rolemcp.parse_rankings("{}", 3))


# ---------------------------------------------------------------------------
class TestVoiceClone(unittest.TestCase):
    def clip(self, name="me.wav", **kw):
        p = os.path.join(tmpdir(self), name)
        with open(p, "wb") as f:
            f.write(make_wav(**kw))
        return p

    def test_clean_path_handles_typed_paths(self):
        p = self.clip("my voice.wav")
        self.assertEqual(voiceclone.clean_path(f"  '{p}'\t"), p)
        self.assertEqual(voiceclone.clean_path(p.replace(" ", "\\ ")), p)
        self.assertEqual(voiceclone.clean_path("file://" + p.replace(" ", "%20")), p)

    def test_prepare_accepts_and_normalises(self):
        path, data, info = voiceclone.prepare(self.clip(seconds=4.0))
        self.assertEqual(info["rate"], 22050)
        self.assertEqual(info["notes"], [])
        _, data, info = voiceclone.prepare(self.clip(seconds=12.0, rate=16000, channels=2))
        with wave.open(io.BytesIO(data)) as w:
            self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, 22050))
            self.assertAlmostEqual(w.getnframes() / 22050, 10.0, delta=0.05)
        self.assertEqual(len(info["notes"]), 3)    # mono, resampled, trimmed

    def test_prepare_rejects_bad_clips(self):
        with self.assertRaisesRegex(voiceclone.CloneError, "not found"):
            voiceclone.prepare("/storage/emulated/0/Download/none.wav")
        with self.assertRaisesRegex(voiceclone.CloneError, "at least"):
            voiceclone.prepare(self.clip(seconds=1.0))
        p = os.path.join(tmpdir(self), "notes.txt")
        with open(p, "w") as f:
            f.write("x")
        with self.assertRaisesRegex(voiceclone.CloneError, "not an audio format"):
            voiceclone.prepare(p)
        p = os.path.join(tmpdir(self), "a.mp3")
        with open(p, "wb") as f:
            f.write(b"ID3" + b"\x00" * 100)
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(voiceclone.CloneError, "ffmpeg"):
                voiceclone.prepare(p)

    def test_clone_support(self):
        self.assertIsNotNone(R.clone_support("nvidia/magpie-tts-zeroshot"))
        self.assertTrue(R.clone_support("nvidia/magpie-tts-flow")["needs_transcript"])
        self.assertIsNone(R.clone_support("nvidia/magpie-tts-multilingual"))

    def test_not_offered_for_non_cloning_model(self):
        ent, _ = make_entity(self, {"tts": "nvidia/magpie-tts-multilingual"})
        out = []
        self.assertFalse(rolemenu.attach_voice_clone(ent, lambda p: self.fail("must not ask"), out.append))
        self.assertIn("doesn't support voice cloning", out[0])

    def test_attach_and_synthesize_with_multipart_audio_prompt(self):
        seen = {}

        def synth(req):
            seen["url"] = req.full_url
            seen["body"] = req.data
            return FakeResponse(make_wav(1.0))
        opener = RouteOpener([("/v1/audio/synthesize", synth)])
        ent, out = make_entity(self, {"tts": "nvidia/magpie-tts-zeroshot"}, opener)
        clip = self.clip("sevin.wav", seconds=5.0)
        saved = []
        answers = iter([clip])
        ok = rolemenu.attach_voice_clone(ent, lambda p: next(answers), lambda *a: None,
                                         save_fn=lambda: saved.append(1), search_dirs=())
        self.assertTrue(ok)
        self.assertEqual(ent.roles["tts"]["voice_clone"]["path"], clip)
        self.assertEqual(R.clone_text(ent.roles["tts"]), "cloned voice: sevin.wav")
        self.assertIn("cloned voice: sevin.wav", "\n".join(rolemenu.role_lines(ent.roles)))
        res = ent.test_role("tts")
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["voice_clone"], clip)
        self.assertIn("55cf67bf-600f-4b04-8eac-12ed39537a08.invocation.api.nvcf.nvidia.com", seen["url"])
        body = seen["body"]
        self.assertIn(b'name="audio_prompt"; filename="sevin.wav"', body)
        self.assertIn(b"RIFF", body)
        self.assertIn(b"Magpie-ZeroShot-Multilingual", body)

    def test_flow_model_asks_for_transcript(self):
        ent, _ = make_entity(self, {"tts": "nvidia/magpie-tts-flow"})
        clip = self.clip(seconds=4.0)
        answers = iter([clip, "", "This is my voice."])
        rolemenu.attach_voice_clone(ent, lambda p: next(answers), lambda *a: None, search_dirs=())
        self.assertEqual(ent.roles["tts"]["voice_clone"]["transcript"], "This is my voice.")

    def test_bad_clip_leaves_setting_unchanged(self):
        ent, _ = make_entity(self, {"tts": "nvidia/magpie-tts-zeroshot"})
        answers = iter(["/storage/emulated/0/nothing.wav"])
        out = []
        self.assertFalse(rolemenu.attach_voice_clone(ent, lambda p: next(answers), out.append, search_dirs=()))
        self.assertNotIn("voice_clone", R.normalize(ent.roles["tts"]))
        self.assertTrue(any("not found" in o for o in out))

    def test_mcp_tts_without_reference_arg_is_not_offered(self):
        tools = [{"name": "say", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}}]
        ent, _ = make_entity(self, {"tts": {"backend": "mcp", "tool": "say", "arg_map": {"text": "text"}}},
                             mcp_server=FakeMCPServer(tools))
        ok, why = rolemenu.clone_info(ent)
        self.assertFalse(ok)
        self.assertIn("no reference-audio argument", why)

    def test_switching_tts_model_drops_clone_when_unsupported(self):
        roles = {"tts": {"backend": "model", "model": "nvidia/magpie-tts-zeroshot",
                         "voice_clone": {"path": "/x.wav"}}}
        R.set_model(roles, "tts", "nvidia/magpie-tts-zeroshot")
        self.assertIn("voice_clone", roles["tts"])
        R.set_model(roles, "tts", "nvidia/magpie-tts-multilingual")
        self.assertNotIn("voice_clone", roles["tts"])


class TestJudgeRoleKeys(unittest.TestCase):
    def test_type_to_role_uses_new_keys(self):
        from nimlab import judge
        for t, role in judge.TYPE_TO_ROLE.items():
            self.assertTrue(role in R.BY_KEY or role in R.EXTRA_ROLES, role)
        self.assertEqual(judge.TYPE_TO_ROLE["chat"], "persona")

    def test_apply_skips_mcp_backed_roles(self):
        from nimlab import judge
        d = tmpdir(self)
        path = os.path.join(d, "c.json")
        with open(path, "w") as f:
            json.dump({"roles": {"persona": {"backend": "mcp", "tool": "chat"}, "vision": "old/v"}}, f)
        board = {"types": {"chat": {"winner": "new/chat"}, "vision": {"winner": "new/v"}}}
        changes = judge.apply_winners(board, path=path)
        with open(path) as f:
            cfg = json.load(f)
        self.assertEqual(cfg["roles"]["persona"]["backend"], "mcp")
        self.assertEqual(cfg["roles"]["vision"]["model"], "new/v")
        self.assertEqual([c[0] for c in changes], ["vision"])


if __name__ == "__main__":
    unittest.main()
