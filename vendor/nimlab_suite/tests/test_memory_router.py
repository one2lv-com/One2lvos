import json
import os
import tempfile
import unittest

from nimlab import router
from nimlab.api import ModelResult
from nimlab.memory import MemoryCore, clean_records, is_error_text


class FakeEmbed:
    def __init__(self, ok=True):
        self.ok = ok

    def embed(self, model, texts, input_type=None):
        if not self.ok:
            return ModelResult(False, error="timeout")
        t = texts[0].lower()
        return ModelResult(True, data=[[1.0 if "cat" in t else 0.0, 1.0 if "dog" in t else 0.0, 0.1]])


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "mem.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_error_detection(self):
        for t in ("[ERROR None]: The read operation timed out", "[VISION ERROR 500]: x",
                  "User: hi | Assistant: [ERROR 429]: rate limited", "", None):
            self.assertTrue(is_error_text(t), t)
        self.assertFalse(is_error_text("User: hi | Assistant: The error was in line 3."))

    def test_existing_error_records_dropped_on_load(self):
        raw = [{"id": 1, "timestamp": "t", "text": "User: x | Assistant: [ERROR None]: timed out", "vector": [1]},
               {"id": 2, "timestamp": "t", "text": "User: cat | Assistant: meow", "vector": [1, 0, 0]}]
        with open(self.path, "w") as f:
            json.dump(raw, f)
        m = MemoryCore(FakeEmbed(), "e", path=self.path)
        self.assertEqual(len(m.memories), 1)
        self.assertTrue(m.memories[0]["id"].startswith("mem_"))
        with open(self.path) as f:
            self.assertEqual(len(json.load(f)), 1)  # rewritten on disk

    def test_store_rejects_errors_and_failed_embeddings(self):
        m = MemoryCore(FakeEmbed(), "e", path=self.path)
        self.assertIsNone(m.store("[ERROR None]: The read operation timed out"))
        self.assertIsNone(MemoryCore(FakeEmbed(ok=False), "e", path=self.path).store("cat"))
        self.assertEqual(m.memories, [])

    def test_ids_unique_after_delete(self):
        m = MemoryCore(FakeEmbed(), "e", path=self.path)
        a, b = m.store("cat one"), m.store("dog two")
        m.delete(a)
        c = m.store("cat three")
        self.assertEqual(len({b, c}), 2)
        self.assertNotEqual(a, c)
        self.assertEqual(len({r["id"] for r in m.memories}), len(m.memories))

    def test_recall_skips_other_embedding_models(self):
        m = MemoryCore(FakeEmbed(), "e", path=self.path)
        m.store("cat facts")
        m.memories.append({"id": "x", "timestamp": "t", "text": "cat from other", "embed_model": "other",
                           "vector": [1.0, 0.0, 0.1]})
        hits = m.recall("cat", top_k=5, threshold=0.1)
        self.assertEqual([h[1] for h in hits], ["cat facts"])
        self.assertEqual(m.incompatible_count(), 1)

    def test_clean_records_dedupes_ids(self):
        out = clean_records([{"id": "a", "text": "ok", "vector": [1]}, {"id": "a", "text": "ok2", "vector": [1]}])
        self.assertEqual(len({r["id"] for r in out}), 2)


class RouterTests(unittest.TestCase):
    def test_model_types(self):
        self.assertEqual(router.model_types("nvidia/llama-nemotron-embed-vl-1b-v2", "embeddings_typed"), {"embeddings"})
        self.assertIn("vision", router.model_types("meta/llama-3.2-11b-vision-instruct", "chat"))
        self.assertIn("ocr", router.model_types("nvidia/nemotron-parse", "chat"))
        self.assertNotIn("chat", router.model_types("nvidia/nemotron-parse", "chat"))
        self.assertNotIn("chat", router.model_types("meta/llama-guard-4-12b", "chat"))
        self.assertIn("coding", router.model_types("google/gemma-4-31b-it", "chat"))

    def test_candidates_from_verified_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "v.json")
            with open(p, "w") as f:
                json.dump({"a/chat-model": {"status": "LIVE_200", "kind": "chat"},
                           "a/embed-model": {"status": "LIVE_200", "kind": "embeddings_typed"},
                           "a/dead": {"status": "NO_WORKING_REST_ENDPOINT"}}, f)
            c = router.candidates_by_type(router.load_live_fleet(p),
                                          overrides={"coding": ["x/override", "a/chat-model"]})
        self.assertEqual(c["chat"], ["a/chat-model"])
        self.assertEqual(c["embeddings"], ["a/embed-model"])
        # an override narrows the field but can't add a model without a 200 test
        self.assertEqual(c["coding"], ["a/chat-model"])
        self.assertNotIn("a/dead", sum(c.values(), []))

    def test_registry_resolve(self):
        r = router.NvidiaRouter()
        self.assertTrue(r.resolve("meta/llama-3.3-70b-instruct")["url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
