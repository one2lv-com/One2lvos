"""v3.7.1: automatic semantic recall, the built-in memory_search tool
(semantic / keyword / both), keyword search on every backend (Oracle Text
CONTAINS or INSTR), the doctor round trip, the generated ENVIRONMENT block,
the prompt lint and migration, and memory profile name protection."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nimlab import config, environment as ENV, ltm, memmenu  # noqa: E402
from nimlab.memory import MemoryCore  # noqa: E402
from tests.test_ltm import FakeOracleDB, FnEmbedder, OracleCase, lt, tmpdir  # noqa: E402

FACTS = ["User: the bug ID for the self-test timeout is B-7Q2K9X | Assistant: noted",
         "User: my cat is called Miso | Assistant: lovely name",
         "User: on the voice call we planned Nim Lab 3.7.1 | Assistant: yes, the self-test fix first"]


def fill(m):
    for f in FACTS:
        assert m.store(f, dedupe="off"), m.offline


class SearchContract:
    def test_keyword_finds_exact_id_the_vector_misses(self):
        m = self.make()
        fill(m)
        kw = m.keyword("B-7Q2K9X")
        self.assertTrue(kw and "B-7Q2K9X" in kw[0][1], kw)

    def test_search_modes_merge_and_dedupe(self):
        m = self.make()
        fill(m)
        hits, info = m.search("Miso cat", mode="both", top_k=5)
        texts = [h[1] for h in hits]
        self.assertEqual(len(texts), len(set(texts)))          # no duplicates from the two searches
        self.assertTrue(any("Miso" in t for t in texts))
        self.assertGreaterEqual(info["semantic"], 1)
        self.assertGreaterEqual(info["keyword"], 1)
        _, info = m.search("Miso", mode="keyword")
        self.assertEqual(info["semantic"], 0)
        _, info = m.search("Miso", mode="semantic")
        self.assertEqual(info["keyword"], 0)

    def test_rerank_reorders(self):
        m = self.make()
        fill(m)
        hits, info = m.search("Assistant", mode="both", top_k=3,
                              rerank_fn=lambda q, docs: [(len(docs) - 1 - i, 1.0) for i in range(len(docs))])
        self.assertTrue(info["reranked"], (info, hits))

    def test_recent_newest_last(self):
        m = self.make()
        fill(m)
        r = m.recent(2)
        self.assertEqual(len(r), 2)
        self.assertIn("voice call", r[-1][1])

    def test_doctor_roundtrip_writes_recalls_and_cleans_up(self):
        m = self.make()
        fill(m)
        before = m.count()
        rows = m.roundtrip()
        self.assertTrue(all(ok for ok, _ in rows), rows)
        self.assertTrue(any("semantic recall" in msg for _, msg in rows))
        self.assertTrue(any("keyword search" in msg for _, msg in rows))
        self.assertEqual(m.count(), before)


class TestJsonSearch(SearchContract, unittest.TestCase):
    def make(self):
        d = tmpdir(self)
        return MemoryCore(None, "x", settings=lt(backend="json", json={"path": os.path.join(d, "m.json")}),
                          embedder=FnEmbedder())


class TestLocalSearch(SearchContract, unittest.TestCase):
    def make(self):
        d = tmpdir(self)
        return MemoryCore(None, "x", settings=lt(backend="local", local={"directory": d}), embedder=FnEmbedder())

    def test_local_uses_fts5_when_available(self):
        m = self.make()
        fill(m)
        self.assertIn(m.backend.keyword_mode(), ("sqlite FTS5 index", "sqlite LIKE"))


class TestOracleSearch(SearchContract, OracleCase):
    def make(self):
        return self.core()

    def test_instr_fallback_without_oracle_text(self):
        m = self.core()
        fill(m)
        m.keyword("B-7Q2K9X")
        self.assertEqual(self.db.keyword_calls[-1], "keyword_instr")
        self.assertEqual(m.backend.keyword_mode(), "INSTR scan")

    def test_contains_with_oracle_text_index(self):
        db = FakeOracleDB()
        db.oracle_text = True
        m = self.core(db=db)
        fill(m)                                        # first store runs setup, which makes the text index
        self.assertIn("TESTBED_MEM_TEXT_IX", db.text_indexes)
        hits = m.keyword("b-7q2k9x")
        self.assertEqual(db.keyword_calls[-1], "keyword_ctx")
        self.assertTrue(hits and "B-7Q2K9X" in hits[0][1])


class TestEntityRecallPipeline(unittest.TestCase):
    """The terminal chat, voice calls and the endpoint all go through
    Entity.turn -> recall_block (before the persona) -> remember_turn (after)."""

    def make(self):
        from nimlab.entity import Entity
        d = tmpdir(self)
        cl = config.load_cluster_config()
        cl["memory_settings"] = dict(cl.get("memory_settings", {}),
                                     long_term=dict(ltm.settings_from({}), backend="json",
                                                    json={"path": os.path.join(d, "m.json")}))
        logs = []
        ent = Entity(cluster=cl, memory=False, log=logs.append)
        ent.memory = MemoryCore(None, "x", settings=cl["memory_settings"], embedder=FnEmbedder())
        fill(ent.memory)
        return ent, logs

    def test_recall_logs_backend_hits_and_ms(self):
        ent, logs = self.make()
        block = ent.recall_block("what is my cat called? Miso")
        self.assertIn("RECALLED SEMANTIC MEMORY", block)
        line = [l for l in logs if l.startswith("[memory] recall")]
        self.assertTrue(line, logs)
        self.assertRegex(line[0], r"\[memory\] recall json .*: \d+(/\d+)? hit\(s\).* in \d+ ms")

    def test_what_were_we_talking_about_adds_recent(self):
        ent, logs = self.make()
        block = ent.recall_block("so you are able to recall what we just we talking about in the voice call?")
        self.assertIn("MOST RECENT MEMORIES", block)
        self.assertIn("3.7.1", block)

    def test_memory_search_tool_in_process(self):
        ent, logs = self.make()
        self.assertEqual([t["name"] for t in ent.builtin_tools()], ["memory_search"])
        out = ent.run_builtin_tool("memory_search", {"query": "B-7Q2K9X", "mode": "keyword"})
        self.assertIn("B-7Q2K9X", out["content"][0]["text"])
        self.assertTrue(any("memory_search json mode=keyword" in l for l in logs), logs)

    def test_environment_block(self):
        ent, _ = self.make()
        with ENV.channel("voice"):
            env = ENV.environment_block(ent, "persona", tool_names=["memory_search"])
        self.assertIn("Memory profile: TESTBED", env)
        self.assertIn("recalled before every reply", env)
        self.assertIn("memory_search", env)
        self.assertIn("No other tools exist", env)
        self.assertIn("voice rules win", env)
        self.assertIn("no lists", env)
        with ENV.channel("terminal"):
            env = ENV.environment_block(ent, "persona", tool_names=[])
        self.assertIn("You have no tools", env)
        self.assertEqual(ENV.environment_block(ent, "ocr"), "")

    def test_system_prompt_has_environment(self):
        ent, _ = self.make()
        sp = ent.build_system_prompt("persona", with_tools=False)
        self.assertIn("=== ENVIRONMENT", sp)


USER_PROMPTS = {
    "persona": ("You are Quill: dry precision, understated bibliophilic wit, short turns for Magpie TTS. Never "
                "read lists aloud. Address the user directly, and silently log durable facts and session "
                "summaries via quill_mem(action='log')."),
    "compactor": "Compress turns into dense bullets. Emit a MEM_LOG_PAYLOAD ready for quill_mem(action='log').",
    "reasoning": "Break problems down step by step. Plan and chain required MCP tool calls before answering.",
    "ocr": "Extract text exactly as printed.",
}


class TestPromptLintAndMigration(unittest.TestCase):
    def test_lint_names_missing_tools(self):
        w = ENV.lint_prompts(USER_PROMPTS, [])
        self.assertIn("persona mentions quill_mem, which is not an available tool", w)
        self.assertIn("compactor mentions quill_mem, which is not an available tool", w)
        self.assertTrue(any(x.startswith("reasoning tells the model to make tool calls") for x in w))
        self.assertEqual(ENV.lint_prompts({"persona": "Use quill_mem(action='recall') if needed."}, ["quill_mem"]),
                         [])

    def test_migration_keeps_voice_and_removes_stale_calls(self):
        new, rep = ENV.migrate_prompts(USER_PROMPTS, [])
        p = new["persona"]
        self.assertNotIn("quill_mem", p)
        self.assertIn("dry precision, understated bibliophilic wit, short turns for Magpie TTS", p)
        self.assertIn("Address the user directly", p)
        self.assertIn("happen automatically", p)
        self.assertNotIn("quill_mem", new["compactor"])
        self.assertIn("MEM_LOG_PAYLOAD", new["compactor"])
        self.assertNotIn("chain required MCP tool calls", new["reasoning"])
        self.assertEqual(new["ocr"], USER_PROMPTS["ocr"])
        self.assertNotIn("ocr", rep)
        self.assertEqual(ENV.lint_prompts(new, []), [])

    def test_migrate_file_backs_up(self):
        d = tmpdir(self)
        p = os.path.join(d, "config_system_prompts.json")
        json.dump(USER_PROMPTS, open(p, "w"))
        rep = ENV.migrate_prompts_file(p, [], log=None)
        self.assertTrue(os.path.exists(rep["backup"]))
        self.assertEqual(json.load(open(rep["backup"])), USER_PROMPTS)
        self.assertNotIn("quill_mem", json.dumps(json.load(open(p))))
        self.assertEqual(ENV.migrate_prompts_file(p, [], log=None), {})     # second run: nothing to do

    def test_shipped_prompts_are_clean(self):
        from nimlab import defaults
        self.assertEqual(ENV.lint_prompts(defaults.STARTER_PROMPTS, []), [])
        shipped = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                              "config_system_prompts.json")))
        self.assertEqual(ENV.lint_prompts(shipped, []), [])


class TestProfileNames(unittest.TestCase):
    def test_default_is_testbed(self):
        self.assertEqual(ltm.settings_from({})["oracle"]["profile_id"], "TESTBED")

    def test_other_agents_protected(self):
        for n in ("charlie", "MAYA", "miles", "Simone", "sys"):
            self.assertIn("protected", memmenu.profile_name_problem(n))
        self.assertIsNone(memmenu.profile_name_problem("QUILL"))
        self.assertIsNotNone(memmenu.profile_name_problem("9bad"))


if __name__ == "__main__":
    unittest.main()
