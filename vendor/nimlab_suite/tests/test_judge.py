import json
import os
import random
import re
import tempfile
import unittest
from unittest import mock

from nimlab import battery, judge
from nimlab.api import ModelResult
from nimlab.assets import OCR_TEXT, ocr_png, vision_png


class MetricTests(unittest.TestCase):
    def test_cer(self):
        self.assertEqual(judge.cer("HELLO", "hello"), 0.0)
        self.assertEqual(judge.cer("ABCD", "ABXD"), 0.25)
        self.assertEqual(judge.cer(OCR_TEXT, "```\n" + OCR_TEXT.lower() + "\n```"), 0.0)
        self.assertGreater(judge.cer("ABC", ""), 0.99)

    def test_recall_and_mrr(self):
        ids = ["b", "a", "c"]
        self.assertEqual(judge.recall_at_k(ids, "a", 1), 0.0)
        self.assertEqual(judge.recall_at_k(ids, "a", 3), 1.0)
        self.assertEqual(judge.reciprocal_rank(ids, "a"), 0.5)
        self.assertEqual(judge.reciprocal_rank(ids, "z"), 0.0)

    def test_answer_matching(self):
        self.assertTrue(judge.answer_matches("5 cents", ["5"]))
        self.assertTrue(judge.answer_matches("**Friday**", ["friday"]))
        self.assertTrue(judge.answer_matches("There are 3 red squares.", ["3"]))
        self.assertFalse(judge.answer_matches("10 cents", ["5"]))
        self.assertFalse(judge.answer_matches("$0.10", ["0.05"]))
        self.assertEqual(judge.extract_final("work...\nFINAL: 42"), "42")
        self.assertEqual(judge.extract_final("Final answer - Friday"), "Friday")

    def test_constraints(self):
        self.assertTrue(judge.check_constraint("- a\n- b\n- c", {"type": "bullet_count", "value": 3}))
        self.assertFalse(judge.check_constraint("Intro:\n- a\n- b\n- c", {"type": "bullet_count", "value": 3}))
        self.assertTrue(judge.check_constraint('{"city": "Paris", "country": "France"}',
                                               {"type": "json_keys", "value": ["city", "country"]}))
        self.assertFalse(judge.check_constraint("```json\n{}\n```", {"type": "json_keys", "value": ["city"]}))
        self.assertTrue(judge.check_constraint("one two", {"type": "max_words", "value": 2}))

    def test_fact_retention(self):
        facts = [["march 10", "mar 10"], ["marco"], ["2,000", "2000"]]
        self.assertAlmostEqual(judge.fact_retention("Launch moved to Mar 10; Marco fixes it.", facts), 2 / 3)


class CodeRunnerTests(unittest.TestCase):
    item = battery.CODING[2]  # dedupe

    def test_correct_code_passes(self):
        code = "def dedupe(items):\n    seen = set()\n    return [x for x in items if not (x in seen or seen.add(x))]\n"
        r = judge.run_code_tests(code, self.item["entry"], self.item["tests"], timeout=10)
        self.assertEqual((r["passed"], r["total"], r["error"]), (3, 3, None))

    def test_wrong_code_partial(self):
        r = judge.run_code_tests("def dedupe(items):\n    return sorted(set(items))\n", "dedupe", self.item["tests"])
        self.assertLess(r["passed"], 3)

    def test_dangerous_code_blocked_before_running(self):
        for code in ("import os\ndef dedupe(x): os.system('id')", "def dedupe(x): return __import__('os')",
                     "def dedupe(x): return open('/etc/passwd').read()", "from subprocess import run"):
            r = judge.run_code_tests(code, "dedupe", self.item["tests"])
            self.assertIn("blocked", r["error"], code)

    def test_timeout(self):
        r = judge.run_code_tests("def dedupe(x):\n    while True:\n        pass\n", "dedupe", self.item["tests"], timeout=2)
        self.assertEqual(r["passed"], 0)
        self.assertTrue("timed out" in r["error"] or r["error"])

    def test_no_keys_in_child_env(self):
        code = "def dedupe(x):\n    return x\n"
        with mock.patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-should-not-leak"}):
            with mock.patch("subprocess.run", wraps=judge.subprocess.run) as run:
                judge.run_code_tests(code, "dedupe", self.item["tests"])
                env = run.call_args.kwargs["env"]
        self.assertNotIn("NVIDIA_API_KEY", env)

    def test_extract_code(self):
        self.assertEqual(judge.extract_code("text\n```python\ndef f(): pass\n```\nmore"), "def f(): pass")


class ScoringTests(unittest.TestCase):
    rubric = judge.CHAT_RUBRIC

    def full(self, v):
        return {c: v for c in self.rubric}

    def test_parse_strict(self):
        text = "```json\n" + json.dumps({"A": self.full(8), "B": self.full(11), "C": {"helpfulness": 5}}) + "\n```"
        parsed = judge.parse_judge_scores(text, ["A", "B", "C"], self.rubric)
        self.assertEqual(list(parsed), ["A"])  # out-of-range and incomplete are dropped
        self.assertEqual(judge.parse_judge_scores("no json here", ["A"], self.rubric), {})
        bools = {"A": {c: True for c in self.rubric}}
        self.assertEqual(judge.parse_judge_scores(json.dumps(bools), ["A"], self.rubric), {})

    def test_weighted_score_bounds(self):
        self.assertEqual(judge.weighted_score(self.full(10), self.rubric), 1.0)
        self.assertEqual(judge.weighted_score(self.full(1), self.rubric), 0.0)

    def test_anonymize_shuffles_and_maps(self):
        items = [(f"m{i}", f"text{i}") for i in range(6)]
        mapping, shown = judge.anonymize(items, random.Random(1))
        self.assertEqual(sorted(mapping.values()), sorted(k for k, _ in items))
        self.assertEqual([lbl for lbl, _ in shown], list("ABCDEF"))
        self.assertNotEqual([mapping[lbl] for lbl, _ in shown], [k for k, _ in items])

    def test_redact_model_names(self):
        out = judge.redact_model_names("As Llama-4 by Meta and Gemma, I think", ["poolside/laguna-xs.2"])
        self.assertNotIn("Llama", out)
        self.assertNotIn("Meta", out)
        self.assertNotIn("Gemma", out)
        self.assertIn("[model]", judge.redact_model_names("I am Laguna", ["poolside/laguna-xs.2"]))

    def test_judge_batch_excludes_self_and_hides_names(self):
        prompts = []

        class FakeClient:
            def chat(self, model, messages, **kw):
                prompt = messages[-1]["content"]
                prompts.append((model, prompt))
                labels = re.findall(r"=== RESPONSE ([A-Z]) ", prompt)
                # score by content: the 'good' answer gets 9s, others 3s
                body = {}
                for lbl in labels:
                    seg = prompt.split(f"=== RESPONSE {lbl} ")[1].split("<<<")[1].split(">>>")[0]
                    body[lbl] = {c: (9 if "good" in seg else 3) for c in judge.CHAT_RUBRIC}
                return ModelResult(True, text=json.dumps(body))

        outputs = {"judge1": ("judge1", "good answer from vendor/judge1"), "x": ("x", "bad answer"),
                   "y": ("y", "good answer")}
        per, crit, errs = judge.judge_batch(FakeClient(), ["judge1", "judge2"], "task", outputs, self.rubric,
                                            random.Random(0), repeats=2)
        self.assertEqual(errs, [])
        self.assertEqual(len(per["judge1"]), 2)   # only judge2 scored it (x2 repeats)
        self.assertEqual(len(per["x"]), 4)
        for model, prompt in prompts:
            self.assertNotIn("vendor/judge1", prompt)  # model names redacted
        judge1_prompts = [p for m, p in prompts if m == "judge1"]
        self.assertTrue(all("good answer from" not in p for p in judge1_prompts))
        self.assertGreater(sum(per["y"]) / len(per["y"]), sum(per["x"]) / len(per["x"]))

    def test_composite_ranks_quality_then_speed(self):
        rows = [{"model": "slow_good", "objective": 1.0, "judge": 0.9, "median_latency_sec": 10.0, "status": "ok"},
                {"model": "fast_bad", "objective": 0.2, "judge": 0.3, "median_latency_sec": 1.0, "status": "ok"},
                {"model": "dead", "objective": None, "judge": None, "median_latency_sec": None, "status": "failed"}]
        out = judge.composite(rows, {"objective": 0.5, "judge": 0.5})
        self.assertEqual([r["model"] for r in out], ["slow_good", "fast_bad", "dead"])
        self.assertEqual(out[-1]["score"], 0.0)
        self.assertLessEqual(out[0]["score"], 100)


class FakeNim:
    """Deterministic stand-in for NimClient used by the rankers."""

    def chat(self, model, messages, **kw):
        prompt = messages[-1]["content"]
        if messages[0]["content"] == judge.JUDGE_SYSTEM:
            labels = re.findall(r"=== RESPONSE ([A-Z]) ", prompt)
            rubric_keys = re.findall(r'^- "(\w+)"', prompt, flags=re.M)
            return ModelResult(True, text=json.dumps({lbl: {k: 7 for k in rubric_keys} for lbl in labels}))
        if model == "broken":
            return ModelResult(False, error="timeout: timed out")
        if "FINAL:" in prompt:
            ans = {"bat": "5 cents", "machines": "5", "Wednesday": "Friday", "2, 6": "42", "sheep": "9"}
            final = next((v for k, v in ans.items() if k in prompt), "?") if model == "smart" else "7"
            return ModelResult(True, text=f"reasoning\nFINAL: {final}", latency=1.0, usage={"completion_tokens": 20})
        if "dedupe" in prompt:
            return ModelResult(True, text="```python\ndef dedupe(items):\n    out=[]\n    for x in items:\n        if x not in out: out.append(x)\n    return out\n```", latency=1.0)
        return ModelResult(True, text="- a\n- b\n- c", latency=0.5)

    def vision(self, model, url, q, **kw):
        if model == "eyes":
            return ModelResult(True, text={"red": "3", "color": "Blue.", "shape": "triangle", "number": "42"}[
                next(k for k in ("red", "color", "shape", "number") if k in q)], latency=0.4)
        return ModelResult(True, text="I see a picture", latency=0.2)

    def ocr(self, model, url, **kw):
        return ModelResult(True, text=OCR_TEXT if model == "reader" else "NVIDIA TEST", latency=0.3)

    def embed(self, model, texts, input_type=None):
        # "good" model: one-hot by document id, queries map to their relevant doc
        ids = [d["id"] for d in battery.EMBED_DOCS]
        rel = {q["q"]: q["relevant"] for q in battery.EMBED_QUERIES}
        doc_by_text = {d["text"]: d["id"] for d in battery.EMBED_DOCS}
        vecs = []
        for t in texts:
            target = doc_by_text.get(t) or rel.get(t)
            if model != "good_embed":
                target = ids[0]
            vecs.append([1.0 if i == target else 0.01 for i in ids])
        return ModelResult(True, data=vecs, latency=0.1)

    def tts(self, text, voice=None, **kw):
        import io
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes(b"\x00\x00" * 22050)
        return ModelResult(True, data=buf.getvalue(), latency=0.5 if voice.endswith("Aria") else 1.5)


class RankerTests(unittest.TestCase):
    def ranker(self):
        return judge.Ranker(client=FakeNim(), judges=["judgeA"], seed=7, log=lambda *a: None)

    def test_reasoning_ranking(self):
        rows = judge.composite(self.ranker().rank_deep_reasoning(["dumb", "smart", "broken"]), judge.BLEND["deep_reasoning"])
        self.assertEqual(rows[0]["model"], "smart")
        self.assertEqual(rows[0]["correct"], "5/5")
        self.assertEqual(next(r for r in rows if r["model"] == "broken")["status"], "failed")

    def test_vision_ocr_embeddings_tts(self):
        r = self.ranker()
        v = judge.composite(r.rank_vision(["blind", "eyes"]), judge.BLEND["vision"])
        self.assertEqual((v[0]["model"], v[0]["correct"]), ("eyes", "4/4"))
        o = judge.composite(r.rank_ocr(["reader", "skimmer"]), judge.BLEND["ocr"])
        self.assertEqual((o[0]["model"], o[0]["cer"]), ("reader", 0.0))
        e = judge.composite(r.rank_embeddings(["bad_embed", "good_embed"]), judge.BLEND["embeddings"])
        self.assertEqual((e[0]["model"], e[0]["recall_at_1"]), ("good_embed", 1.0))
        t = judge.composite(r.rank_tts(["X.Jason", "X.Aria"]), judge.BLEND["tts"], speed_key="rtf")
        self.assertEqual(t[0]["model"], "X.Aria")

    def test_full_rank_and_apply(self):
        r = self.ranker()
        overrides = {"chat": ["c1", "c2"], "deep_reasoning": ["smart", "dumb"], "coding": ["coder"],
                     "vision": ["eyes", "blind"], "ocr": ["reader"], "embeddings": ["good_embed", "bad_embed"],
                     "compactor": ["c1"]}
        r.settings["candidate_overrides"] = overrides
        r.cluster = {"roles": {}, "voice_settings": {"voice_profiles": ["X.Aria", "X.Jason"]}}
        live = {m: {"status": "LIVE_200", "kind": "chat"} for ms in overrides.values() for m in ms}
        with mock.patch.object(judge, "load_live_fleet", return_value=live):
            board = r.rank()
        self.assertEqual(board["types"]["deep_reasoning"]["winner"], "smart")
        self.assertEqual(board["types"]["coding"]["candidates"][0]["tests_passed"], "3/13")  # only dedupe is answered correctly by the fake
        self.assertIn("DEEP_REASONING", judge.format_leaderboard(board))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config_cluster.json")
            with open(path, "w") as f:
                json.dump({"roles": {"deep_reasoning": "dumb", "main_brain": "keep"}, "other": 1}, f)
            changes = judge.apply_winners(board, path=path, types=["deep_reasoning", "embeddings"])
            with open(path) as f:
                cfg = json.load(f)
        # v3.2: old keys are migrated (deep_reasoning -> reasoning, main_brain -> persona)
        self.assertEqual(cfg["roles"]["reasoning"]["model"], "smart")
        self.assertEqual(cfg["roles"]["reasoning"]["backend"], "model")
        self.assertEqual(cfg["roles"]["embedding"]["model"], "good_embed")
        self.assertEqual(cfg["roles"]["persona"]["model"], "keep")  # types filter respected
        self.assertNotIn("deep_reasoning", cfg["roles"])
        self.assertEqual(cfg["other"], 1)
        self.assertEqual(len(changes), 2)

    def test_entity_judge(self):
        class FakeEntity:
            def __init__(self, roles):
                self.roles = {"persona": roles.get("persona", "base"), "reasoning": "d", "coding": "c"}

            def respond(self, role, history, **kw):
                if self.roles["persona"] == "flaky" and role == "coding":
                    return ModelResult(False, error="x"), []
                return ModelResult(True, text="Sharp answer.", latency=1.0), []

        report = judge.judge_entity(combos=[{"name": "a", "roles": {}}, {"name": "b", "roles": {"main_brain": "flaky"}}],  # old key still works
                                    judges=["j"], repeats=1, seed=1, client=FakeNim(), log=lambda *a: None,
                                    entity_factory=FakeEntity)
        names = [r["combo"] for r in report["combos"]]
        self.assertEqual(names, ["a", "b"])  # failures lower the score via completeness
        self.assertEqual(report["combos"][1]["failures"], 1)
        self.assertIn("in_character", report["combos"][0]["rubric"])
        self.assertIn("Combo", judge.format_entity(report))


class AssetTests(unittest.TestCase):
    def test_pngs_are_valid(self):
        for data in (vision_png(), ocr_png()):
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertIn(b"IEND", data[-12:])


if __name__ == "__main__":
    unittest.main()
