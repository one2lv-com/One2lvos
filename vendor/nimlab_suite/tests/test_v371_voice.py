"""v3.7.1 voice turns: per-stage timing, the voice fast route, short
timeouts, memory saved after the reply, TTS input cleaning and the text
fallback when speaking fails."""

import json
import os
import unittest

from nimlab import bugs, intent, perf, unified, voicecall
from nimlab import environment as ENV
from tests.fakes import http_error
from tests.test_entity import EntityCase, FakeDevice


class Events:
    def __init__(self):
        self.log = []


class OrderDevice(FakeDevice):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def play(self, path):
        self.events.log.append("play")
        super().play(path)


class VoiceCase(EntityCase):
    def call(self, keys, device=None):
        lines = []
        it = iter(keys)
        n = voicecall.run_call(self.ent, input_fn=lambda p="": next(it), out=lines.append,
                               device=device or FakeDevice())
        return n, "\n".join(lines)

    def stage_lines(self, text):
        return [ln for ln in text.splitlines() if ln.strip().startswith("[record")]


class TestVoiceStages(VoiceCase):
    def test_every_stage_is_timed_and_router_skipped_on_casual_turn(self):
        n, text = self.call(["", "", "q"])
        self.assertEqual(n, 1)
        line = self.stage_lines(text)[0]
        for name in ("record", "convert", "ASR", "router skipped", "recall", "persona", "TTS", "play", "store",
                     "total"):
            self.assertIn(name, line)
        self.assertEqual(self.backend.by("meta/router-model"), [])          # no router call
        self.assertEqual(self.backend.by("deepseek/reason-model"), [])      # no reasoning call
        self.assertIn("via voice", text)

    def test_voice_turn_that_asks_for_code_still_uses_the_router(self):
        self.backend.asr_text = "write a python function that reverses a string"
        self.backend.route = "coding"
        n, text = self.call(["", "", "q"])
        self.assertEqual(n, 1)
        self.assertEqual(len(self.backend.by("meta/router-model")), 1)
        self.assertIn("router", self.stage_lines(text)[0])
        self.assertNotIn("router skipped", self.stage_lines(text)[0])

    def test_fast_route_can_be_turned_off(self):
        self.ent.cluster.setdefault("voice_settings", {})["fast_route"] = False
        self.backend.asr_text = "please write me a long poem about the sea and the stars tonight"
        self.call(["", "", "q"])
        self.assertEqual(len(self.backend.by("meta/router-model")), 1)
        self.ent.cluster["voice_settings"]["fast_route"] = True
        self.call(["", "", "q"])
        self.assertEqual(len(self.backend.by("meta/router-model")), 1)   # fast route: no new router call

    def test_stage_line_merges_and_hides_nested_embedding(self):
        stages = [{"stage": "asr", "ms": 1200, "ok": True}, {"stage": "embedding", "ms": 300, "ok": True},
                  {"stage": "memory_recall", "ms": 400, "ok": True}, {"stage": "persona", "ms": 2000, "ok": True},
                  {"stage": "persona", "ms": 500, "ok": True}, {"stage": "tts", "ms": 900, "ok": False}]
        line = voicecall.stage_line(stages, 6000, skipped=["intent_router"])
        self.assertEqual(line, "[ASR 1.2s | router skipped | recall 0.4s | persona 2.5s | TTS FAILED 0.9s | "
                               "total 6.0s]")


class TestVoiceStoreAfterReply(VoiceCase):
    def test_memory_is_saved_after_playback_starts(self):
        ev = Events()
        real = self.ent.remember_turn

        def remember(*a, **kw):
            ev.log.append("store")
            return real(*a, **kw)
        self.ent.remember_turn = remember
        self.call(["", "", "q"], device=OrderDevice(ev))
        self.assertEqual(ev.log, ["play", "store"])

    def test_mind_run_defers_store_only_when_asked(self):
        calls = []
        self.ent.remember_turn = lambda *a, **kw: calls.append(a[0])
        mind = unified.Mind(self.ent)
        res = mind.run("hello there", [], [], defer_store=True)
        self.assertTrue(res["ok"])
        self.assertEqual(calls, [])
        res["finish"]()
        self.assertEqual(calls, ["hello there"])
        res = mind.run("hello again", [], [])
        self.assertNotIn("finish", res)
        self.assertEqual(calls, ["hello there", "hello again"])


class TestVoiceTimeouts(VoiceCase):
    def test_turn_calls_are_capped(self):
        seen = []
        self.ent.cluster.setdefault("voice_settings", {})["turn_timeout_sec"] = 7
        orig = self.backend.opener.__class__.__call__

        def spy(op, req, timeout=None):
            seen.append(timeout)
            return orig(op, req, timeout=timeout)
        self.backend.opener.__class__.__call__ = spy
        try:
            self.call(["", "", "q"])
        finally:
            self.backend.opener.__class__.__call__ = orig
        self.assertTrue(seen)
        self.assertTrue(all(t is not None and t <= 7 for t in seen), seen)

    def test_voice_router_timeout_is_short(self):
        self.ent.cluster.setdefault("voice_settings", {})["fast_route"] = False
        got = {}
        real = self.ent.run_role

        def run_role(key, **inp):
            if key == "intent_router":
                got["timeout"] = inp.get("timeout")
            return real(key, **inp)
        self.ent.run_role = run_role
        with ENV.channel("voice"):
            self.ent.route_turn("please write me a long poem about the sea and the stars tonight")
        self.assertEqual(got["timeout"], 4.0)
        got.clear()
        self.ent.route_turn("please write me a long poem about the sea and the stars tonight")
        self.assertEqual(got["timeout"], 8.0)

    def test_slow_turn_goes_to_bug_log_with_stages(self):
        self.ent.cluster.setdefault("voice_settings", {})["slow_turn_sec"] = 0.000001
        n, text = self.call(["", "", "q"])
        self.assertIn("(logged as B-", text)
        rows = bugs.list_bugs()
        self.assertTrue(rows)
        ev = bugs.events(rows[0]["id"])[-1]
        self.assertEqual(ev["kind"], "voice_slow")
        self.assertIn("persona", ev["stages_ms"])
        self.assertIn("memory_store", ev["stages_ms"])


class TestVoiceTTS(VoiceCase):
    def test_tts_failure_falls_back_to_text_and_still_saves(self):
        calls = []
        real = self.ent.remember_turn
        self.ent.remember_turn = lambda *a, **kw: (calls.append(1), real(*a, **kw))[1]
        self.backend.opener.routes.insert(0, ("/audio/synthesize", lambda req: http_error(
            400, b'{"error": "multichar start character but not an end character"}')))
        dev = FakeDevice()
        n, text = self.call(["", "", "q"], device=dev)
        self.assertEqual(n, 1)
        self.assertEqual(dev.played, [])
        self.assertIn("QUILL > I'm Quill", text)
        self.assertIn("couldn't be spoken", text)
        self.assertIn("TTS FAILED", text)
        self.assertEqual(calls, [1])

    def test_text_sent_to_tts_is_clean(self):
        sent = []

        def tts(req):
            sent.append(req.data)
            from tests.fakes import FakeResponse, make_wav
            return FakeResponse(make_wav(0.2))
        self.backend.opener.routes.insert(0, ("/audio/synthesize", tts))
        r = self.ent.run_role("tts", text=unified.speakable(
            "Sure ]<]minimax[>[ thing <tool_call>{\"name\": \"x\"}</tool_call> (open <|im_end|> \"quote", 1500))
        self.assertTrue(r.ok)
        body = b"".join(sent).decode("utf-8", "replace")
        for bad in ("]<]", "minimax", "tool_call", "<|", "(", '\\"quote'):
            self.assertNotIn(bad, body)


class TestTTSClean(unittest.TestCase):
    def test_template_tokens_and_unbalanced_brackets(self):
        cases = {
            "Sure! ]<]minimax[>[ here [it is": "Sure! here it is",
            "Hi <tool_call>{\"name\":\"x\"}</tool_call> there (ok": "Hi there ok",
            "a (b) c) d \"e": "a (b) c d e",
            "<|im_start|>assistant hi there<|im_end|>": "hi there",
            "Say \"hello\" now": "Say \"hello\" now",
            "<|channel|>final<|message|>Done.": "Done.",
        }
        for raw, want in cases.items():
            self.assertEqual(unified.speakable(raw), want, raw)

    def test_strict_keeps_plain_text(self):
        self.assertEqual(unified.tts_clean("Rate: 5\u2605 \u00b7 ok", strict=True), "Rate: 5 ok")


class TestVoiceCasual(unittest.TestCase):
    def test_casual_and_not(self):
        self.assertTrue(intent.is_voice_casual("hey how was your day, can you help me remember the plants")[0])
        self.assertFalse(intent.is_voice_casual("write a python script to rename files")[0])
        self.assertFalse(intent.is_voice_casual("think it through step by step please")[0])
        self.assertFalse(intent.is_voice_casual("draw a picture of a cat")[0])
        self.assertFalse(intent.is_voice_casual(" ".join(["word"] * 61))[0])
        self.assertFalse(intent.is_voice_casual("hello", {"fast_route": False})[0])

    def test_route_with_voice(self):
        rt = intent.route("so what do you think about that", lambda k: True, ask_fn=lambda p: "coding",
                          voice={}, rs={})
        self.assertEqual((rt["role"], rt["via"]), ("persona", "voice"))
        rt = intent.route("so what do you think about that, explain it", lambda k: True,
                          ask_fn=lambda p: "coding", rs={})
        self.assertEqual(rt["via"], "router")


if __name__ == "__main__":
    unittest.main()
