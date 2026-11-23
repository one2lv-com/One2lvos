"""v3.7.0 routing: the reasoning role only for long-context or multi-step
turns, the route and its reason in the trace, accurate failure reports, and
fix offers that an admin can accept (applied with snapshot + audit)."""

import base64
import json
import os
import shutil
import socket
import tempfile
import unittest
from unittest import mock

from nimlab import config, fixes as FX, intent, roles as R, selfadmin as SA
from tests.fakes import make_wav
from tests.test_entity import EntityCase

CASUAL = "Let's see if this voice message is working now."
ANALYSIS = ("Analyze the trade-offs between keeping the memory store in Oracle and keeping it local, "
            "step by step, and give me a migration plan.")


def route(text, ask=None, rs=None, context_chars=0):
    return intent.route(text, lambda k: True, ask_fn=ask, exists=lambda p: False, context_chars=context_chars,
                        rs=rs)


class GateRules(unittest.TestCase):
    def test_casual_turns_skip_router_and_reasoning(self):
        asked = []
        for t in (CASUAL, "hey how are you", "what's the capital of France?", "is the server up?",
                  "thanks, that worked"):
            rt = route(t, ask=lambda p: asked.append(p) or "reasoning")
            self.assertEqual((rt["role"], rt["via"]), ("persona", "fast"), t)
            self.assertIn("no router or reasoning call", rt["reason"])
        self.assertEqual(asked, [])
        # "plan" makes the router look, but the gate still keeps reasoning out of plain chat
        rt = route("for some reason my plan app is weird lol", ask=lambda p: "reasoning")
        self.assertEqual((rt["role"], rt["via"]), ("persona", "router"))

    def test_router_saying_reasoning_is_gated_for_normal_conversation(self):
        text = " ".join(["so yesterday I was telling my friend about the lab and"] * 3)   # > chat_max_words
        rt = route(text, ask=lambda p: "reasoning")
        self.assertEqual((rt["role"], rt["via"]), ("persona", "router"))
        self.assertIn("no reasoning call", rt["reason"])
        self.assertIn("normal conversation", rt["gate"])

    def test_analysis_and_planning_use_reasoning(self):
        rt = route(ANALYSIS, ask=lambda p: "reasoning")
        self.assertEqual(rt["role"], "reasoning")
        self.assertIn("asks for deep reasoning", rt["reason"])
        self.assertEqual(route("think deeply about whether 1001 is prime")["role"], "reasoning")
        self.assertEqual(route("Is 17 prime? Think it through.")["role"], "reasoning")

    def test_long_input_uses_reasoning(self):
        rt = route("what do you make of this?", ask=lambda p: "reasoning", context_chars=9000)
        self.assertEqual(rt["role"], "reasoning")
        self.assertIn("long input", rt["reason"])
        rt = route("what do you make of this?", ask=lambda p: "reasoning", context_chars=9000,
                   rs={"reasoning_min_chars": 20000})
        self.assertEqual(rt["role"], "persona")

    def test_settings_switch_the_gate_off(self):
        rs = {"reasoning_gate": False, "chat_fast_path": False}
        rt = route("hey how are you", ask=lambda p: "reasoning", rs=rs)
        self.assertEqual((rt["role"], rt["via"]), ("reasoning", "router"))
        rs = {"reasoning_keywords": False}
        self.assertEqual(route(ANALYSIS, ask=lambda p: "reasoning", rs=rs)["role"], "persona")
        self.assertEqual(intent.gate_settings({"reasoning_min_chars": 10, "junk": 1})["reasoning_min_chars"], 10)

    def test_coding_and_media_unaffected(self):
        self.assertEqual(route("fix this python function")["role"], "coding")
        self.assertEqual(route("draw an image of a fox")["role"], "image_gen")

    def test_defaults_in_config(self):
        rs = config.DEFAULT_CLUSTER["routing_settings"]
        for k in intent.REASONING_DEFAULTS:
            self.assertIn(k, rs)


class FixSuggestions(unittest.TestCase):
    def setUp(self):
        p = mock.patch("nimlab.rolemenu.model_lists",
                       return_value=(["mistralai/mistral-large-4-1t-a52b", "nvidia/fast-reasoner",
                                      "deepseek-ai/other-reasoner"], []))
        p.start()
        self.addCleanup(p.stop)
        q = mock.patch.object(R, "candidates", side_effect=lambda role, models: (list(models), [], []))
        q.start()
        self.addCleanup(q.stop)

    def test_timeout_offers_lower_timeout_and_faster_model(self):
        fx, manual = FX.suggest("reasoning", "mistralai/mistral-large-4-1t-a52b", "timed out", 61.0,
                                {"http_settings": {"timeout_sec": 60}})
        self.assertEqual(fx[0]["args"], {"section": "http_settings", "key": "timeout_sec", "value": 20})
        self.assertIn("from 60s to 20s", fx[0]["what"])
        models = [f["args"]["model"] for f in fx if f["tool"] == "self_set_role"]
        self.assertEqual(models, ["nvidia/fast-reasoner", "deepseek-ai/other-reasoner"])   # never the one that failed

    def test_other_errors(self):
        fx, _ = FX.suggest("asr", "nvidia/parakeet-ctc-1.1b-asr", "no function ID yet: ./start.sh grpc refresh")
        self.assertEqual(fx, [{"tool": "self_run", "args": {"action": "grpc_refresh"},
                               "what": "refresh the gRPC function IDs (for nvidia/parakeet-ctc-1.1b-asr)"}])
        fx, manual = FX.suggest("asr", "x", "ffmpeg not found: pkg install ffmpeg")
        self.assertEqual(fx, [])
        self.assertIn("pkg install ffmpeg", manual[0])
        fx, manual = FX.suggest("memory", None, "DPY-6005: cannot connect to database", 0,
                                {"memory_settings": {"backend": "oracle"}})
        self.assertEqual(fx[0]["args"], {"key": "backend", "value": "local"})
        fx, manual = FX.suggest("vision", "a/b", "HTTP 401 Unauthorized")
        self.assertIn("NVIDIA key", manual[0])
        fx, _ = FX.suggest("vision", "a/b", "HTTP 503 Service Unavailable")
        self.assertEqual(fx[0]["tool"], "self_set_role")
        fx, _ = FX.suggest("mcp", "weather", "connection refused")
        self.assertEqual(fx[0]["args"], {"action": "mcp_test"})

    def test_offer_text(self):
        fx = [{"tool": "self_run", "args": {}, "what": "do a thing"}]
        admin = FX.offer_text(fx, [], True, ["fix1234"])
        self.assertIn("[fix1234] do a thing", admin)
        self.assertIn("can be undone", admin)
        self.assertIn("self_apply_fix", admin)
        self.assertNotIn("self_apply_fix", FX.offer_text(fx, [], False))
        self.assertFalse(FX.enabled({"self_admin": {"fix_suggestions": False}}))


class EntityRouting(EntityCase):
    def setUp(self):
        super().setUp()
        self.cfgdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.cfgdir, True)
        cluster = os.path.join(self.cfgdir, "config_cluster.json")
        prompts = os.path.join(self.cfgdir, "config_system_prompts.json")
        with open(cluster, "w") as f:
            json.dump(self.ent.cluster, f)
        with open(prompts, "w") as f:
            json.dump({}, f)
        for p in (mock.patch.object(config, "CLUSTER_CONFIG", cluster),
                  mock.patch.object(config, "SYSTEM_PROMPTS", prompts),
                  mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.cfgdir, "NIMLAB_CONFIG_READONLY": "1"}),
                  mock.patch("nimlab.rolemenu.model_lists", return_value=(["nvidia/fast-reasoner"], [])),
                  mock.patch.object(R, "candidates", side_effect=lambda role, models: (list(models), [], []))):
            p.start()
            self.addCleanup(p.stop)
        SA._fixes.clear()
        SA._pending.clear()
        self.backend.route = "reasoning"      # the router would pick reasoning for everything

    def voice(self, transcript, **headers):
        self.backend.asr_text = transcript
        body = {"model": "testbed", "messages": [{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": base64.b64encode(make_wav(1.0)).decode(),
                                                    "format": "wav"}}]}]}
        st, _, raw = self.call("/v1/chat/completions", body, headers=headers)
        j = json.loads(raw)
        self.assertEqual(st, 200, j)
        return j

    def test_casual_voice_turn_never_touches_reasoning(self):
        j = self.voice(CASUAL)
        self.assertNotIn("deepseek/reason-model", self.backend.models())
        self.assertNotIn("meta/router-model", self.backend.models())     # fast path: no router call either
        self.assertEqual(self.backend.models()[-1], "meta/persona-model")
        self.assertIn("asr", self.trace_roles(j))
        self.assertNotIn("reasoning", self.trace_roles(j))
        self.assertEqual(j["testbed"]["via"], "fast")
        self.assertIn("quick conversation", j["testbed"]["route_reason"])

    def test_long_analysis_task_uses_reasoning(self):
        j = self.ask(ANALYSIS)
        models = self.backend.models()
        self.assertIn("meta/router-model", models)
        self.assertIn("deepseek/reason-model", models)
        self.assertEqual(models[-1], "meta/persona-model")
        self.assertIn("reasoning", self.trace_roles(j))
        self.assertIn("asks for deep reasoning", j["testbed"]["route_reason"])

    def fail_reasoning(self):
        real = self.backend.chat

        def chat(req):
            if json.loads(req.data.decode())["model"] == "deepseek/reason-model":
                self.backend.chats.append(json.loads(req.data.decode()))
                return socket.timeout("timed out")
            return real(req)
        self.backend.opener.routes[0] = ("/chat/completions", chat)

    def test_failed_ability_is_reported_accurately_without_fix_for_non_admin(self):
        self.fail_reasoning()
        j = self.ask(ANALYSIS)
        note = self.persona_msgs()[-1]["content"]
        self.assertIn("Reasoning Model ability ([model] deepseek/reason-model) timed out", note)
        self.assertIn("naming it as the agentic long-context & reasoning model timing out", note)
        self.assertIn("not the user's message failing", note)
        self.assertIn("Answer the user's actual message", note)
        self.assertNotIn("self_apply_fix", note)
        self.assertIn("don't offer to change settings", note)
        self.assertEqual(SA._fixes, {})
        failed = [t for t in j["testbed_trace"] if t["role"] == "reasoning"]
        self.assertFalse(failed[0]["ok"])
        self.assertEqual(self.backend.models()[-1], "meta/persona-model")

    def test_admin_gets_fix_offer_and_yes_applies_it_with_snapshot(self):
        key = SA.new_admin_key()
        self.fail_reasoning()
        self.call("/v1/chat/completions", {"model": "testbed", "messages": [{"role": "user", "content": ANALYSIS}]},
                  key=key, headers={"X-Testbed-User": "vin"})
        note = self.persona_msgs()[-1]["content"]
        self.assertIn("self_apply_fix", note)
        self.assertIn("lower the model timeout from", note)
        self.assertIn("switch reasoning to nvidia/fast-reasoner (verified)", note)
        self.assertIn("can be undone", note)
        fid = next(k for k, v in SA._fixes.items() if v["args"].get("key") == "timeout_sec")
        self.assertEqual(SA._fixes[fid]["who"], "vin")
        # nothing has changed yet
        self.assertEqual(config.load_json(config.CLUSTER_CONFIG, {})["http_settings"].get("timeout_sec"),
                         self.ent.cluster["http_settings"].get("timeout_sec"))
        # same request: refused (the user hasn't said yes yet)
        SA._local.ident = SA.Identity(True, "vin", "api-key", SA._fixes[fid]["request"])
        box = SA.ToolBox(self.ent)
        self.assertIn("Ask the user first", box.call_tool("self_apply_fix", {"fix_id": fid})["content"][0]["text"])
        # someone else: refused
        SA.set_request(True, "mallory", "api-key")
        self.assertIn("someone else", box.call_tool("self_apply_fix", {"fix_id": fid})["content"][0]["text"])
        # the admin says yes in the next message
        SA.set_request(True, "vin", "api-key")
        snaps = len(os.listdir(SA._dir("snapshots")))
        res = box.call_tool("self_apply_fix", {"fix_id": fid})
        self.assertFalse(res.get("isError"), res)
        self.assertIn("Applied: lower the model timeout", res["content"][0]["text"])
        self.assertIn("undo", res["content"][0]["text"].lower())
        self.assertEqual(config.load_json(config.CLUSTER_CONFIG, {})["http_settings"]["timeout_sec"], 20)
        self.assertEqual(len(os.listdir(SA._dir("snapshots"))), snaps + 1)
        tools = [a["tool"] for a in SA.audit_tail(10)]
        self.assertIn("offer_fix", tools)
        self.assertIn("self_apply_fix", tools)
        self.assertEqual(SA.undo()["label"], "set http_settings.timeout_sec")
        self.assertNotEqual(config.load_json(config.CLUSTER_CONFIG, {})["http_settings"].get("timeout_sec"), 20)
        self.assertIn("No such fix", box.call_tool("self_apply_fix", {"fix_id": fid})["content"][0]["text"])

    def test_non_admin_cannot_apply_a_fix(self):
        SA.set_request(True, "vin", "api-key")
        ids = SA.offer_fixes([{"tool": "self_run", "args": {"action": "grpc_refresh"}, "what": "refresh"}])
        SA.set_request(False, "vin", "api-key")
        res = SA.ToolBox(self.ent).call_tool("self_apply_fix", {"fix_id": ids[0]})
        self.assertTrue(res["isError"])
        self.assertIn(ids[0], SA._fixes)        # still pending, nothing applied
        self.assertEqual(SA.offer_fixes([{"tool": "self_run", "args": {}, "what": "x"}]), [])   # non-admin

    def test_fix_suggestions_off(self):
        cfg = config.load_json(config.CLUSTER_CONFIG, {})
        cfg.setdefault("self_admin", {})["fix_suggestions"] = False
        config.save_json(config.CLUSTER_CONFIG, cfg)
        self.ent.cluster.setdefault("self_admin", {})["fix_suggestions"] = False
        SA.set_request(True, "vin", "api-key")
        self.assertEqual(SA.offer_fixes([{"tool": "self_run", "args": {}, "what": "x"}]), [])
        self.fail_reasoning()
        self.ask(ANALYSIS)
        self.assertNotIn("self_apply_fix", self.persona_msgs()[-1]["content"])


if __name__ == "__main__":
    unittest.main()
