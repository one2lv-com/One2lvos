"""v3.8.0 memory recall fix. The live bug: "My name is SeVin" said on
Telegram was saved (no scope), but a terminal voice call could not recall
it. It ranked about third, behind an old "I do not remember who you are"
answer and a turn already in the short-term context, with top_k=3, and the
recent-memory fallback only fired on "remember" phrasing.

Covered here: identity questions, self-introductions pinned per user and
always injected, context-turn exclusion, hybrid keyword + vector ranking
(Oracle Text CONTAINS on the fake Oracle, FTS5 / word scan elsewhere),
self-test turns and denial answers never stored or recalled, the higher
default top_k, and memories written by another process (a second core on the
same store and a real subprocess) for each backend."""

import json
import os
import subprocess
import sys
import textwrap
import threading
import unittest

from nimlab import config, entity as E, environment as ENV, ltm
from nimlab.memory import MemoryCore
from tests.test_ltm import CREDS, FakeOracleDB, FnEmbedder, OracleCase, bag_vec, lt, tmpdir

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTION = "what did I tell you my actual name is"

# what the live QUILL_MEMORIES held (paraphrased), oldest first; the name turn
# was stored by 3.7.2 as an ordinary turn, never pinned
LIVE_ROWS = [
    "User: Reply with the single word: ready | Assistant: ready",
    "User: Who are you? Answer in one or two sentences. | Assistant: I am Quill, the lab's coordinator.",
    "User: Do you remember who I am? | Assistant: I do not remember who you are.",
    "User: I'm testing the Oracle memory backend tonight | Assistant: Good luck with the Oracle backend test.",
    "User: the tunnel keeps dropping on my phone | Assistant: Try the named tunnel with a token.",
    "User: what model are you running on | Assistant: The persona runs on the agent model.",
    "User: set the voice to a calmer one | Assistant: Voice changed.",
    "User: My name is SeVin. | Assistant: Nice to meet you, SeVin!",
    "User: how many tests passed last time | Assistant: 930 passed.",
    "User: check the scheduler later | Assistant: Will do.",
    "User: what did you just say about my name | Assistant: I said it was nice to meet you.",
]


def name_vec(text, dims=8):
    """A bag-of-words vector where the denial answer and the in-context turn
    sit closer to the question than the name turn, as in the live ranking."""
    return bag_vec(text, dims)


class TestIdentityHelpers(unittest.TestCase):
    def test_self_introductions(self):
        cases = {
            "My name is SeVin.": {"name": "SeVin"},
            "Hi, I'm SeVin": {"name": "SeVin"},
            "call me Vin": {"name": "Vin"},
            "my name is SeVin and I like NIM": {"name": "SeVin"},
            "My name is SeVin Tanaka": {"name": "SeVin Tanaka"},
            "I am SeVin.": {"name": "SeVin"},
            "I live in Pahrump, Nevada": {"location": "Pahrump"},
            "my birthday is June 1": {"birthday": "June 1"},
        }
        for text, want in cases.items():
            self.assertEqual(ltm.extract_identity(text), want, text)

    def test_not_introductions(self):
        for text in ("I'm tired", "I'm going to test", "my name isn't Bob", "is my name Bob?", "I'm Not sure",
                     "I'm Fine.", "what's my name?", "don't remember this: my name is Bob", ""):
            self.assertEqual(ltm.extract_identity(text), {}, text)

    def test_identity_questions(self):
        for q in (QUESTION, "what's my name", "whats my name?", "who am I?", "do you remember me",
                  "what did I tell you earlier", "do you know who I am", "what is my name"):
            self.assertTrue(ltm.IDENTITY_ASK.search(q), q)
        for q in ("what is the weather", "name a good pizza place", "who are you"):
            self.assertFalse(ltm.IDENTITY_ASK.search(q), q)

    def test_denials_and_self_tests(self):
        for r in ("I do not remember who you are.", "I don't know your name yet. Tell me!",
                  "I can't recall what you told me earlier.", "I don't have any memory of you."):
            self.assertTrue(ltm.is_denial(r), r)
        for r in ("Your name is SeVin.", "Sure, here is the code.", "I don't know the weather in Paris.",
                  "Nice to meet you, SeVin!"):
            self.assertFalse(ltm.is_denial(r), r)
        self.assertTrue(ltm.is_self_test("Reply with the single word: ready"))
        self.assertTrue(ltm.is_self_test("Who are you? Answer in one or two sentences."))
        self.assertFalse(ltm.is_self_test("who are you, really?"))
        self.assertFalse(ltm.usable_memory(LIVE_ROWS[2]))
        self.assertFalse(ltm.usable_memory(LIVE_ROWS[0]))
        self.assertTrue(ltm.usable_memory(LIVE_ROWS[7]))

    def test_fuse_prefers_hits_found_by_both(self):
        sem = [(0.9, "a", "t", 1), (0.8, "b", "t", 2), (0.7, "c", "t", 3)]
        kw = [(1.0, "c", "t", 3), (0.5, "d", "t", 4)]
        order = [f[3] for f in ltm.fuse([sem, kw])]
        self.assertEqual(order[0], 3)
        self.assertEqual(set(order), {1, 2, 3, 4})

    def test_new_defaults_and_migration(self):
        ms = config.DEFAULT_CLUSTER["memory_settings"]
        self.assertGreaterEqual(ms["recall_top_k"], 6)
        self.assertTrue(ms["hybrid_recall"] and ms["exclude_context_turns"])
        new, ch = config.migrate_recall({"memory_settings": {"recall_top_k": 3, "rerank_candidates": 10}})
        self.assertEqual(new["memory_settings"]["recall_top_k"], 6)
        self.assertEqual(new["memory_settings"]["rerank_candidates"], 16)
        self.assertTrue(ch)
        kept, ch = config.migrate_recall({"memory_settings": {"recall_top_k": 4}})
        self.assertEqual(kept["memory_settings"]["recall_top_k"], 4)   # your own value stays
        _, ch = config.migrate_recall(new)
        self.assertEqual(ch, [])


class RecallContract:
    """The same recall behaviour for every backend (mixed into a TestCase).
    self.core() makes a MemoryCore on the shared store; calling it twice gives
    two independent views, like the Telegram bot and a terminal call."""

    def core(self):
        raise NotImplementedError

    def seed_live(self, m):
        for t in LIVE_ROWS:
            m.store(t, dedupe="off")

    def test_store_on_telegram_pins_the_name_and_terminal_sees_it(self):
        tg = self.core()
        with ENV.channel("telegram"):
            ids = tg.remember("My name is SeVin.", "Nice to meet you, SeVin!")
        self.assertEqual(len(ids), 2)   # the pinned fact and the turn
        term = self.core()              # the terminal call's own view of the same store
        self.assertEqual(term.identity_facts(), {"name": "SeVin"})
        self.assertIn("- Name: SeVin", term.identity_block())

    def test_a_new_name_replaces_the_old_one(self):
        m = self.core()
        m.remember("My name is Sam.", "Hi Sam!")
        m.remember("Actually, call me SeVin.", "Sure, SeVin.")
        self.assertEqual(self.core().identity_facts(), {"name": "SeVin"})
        self.assertEqual(sum(1 for r in m.backend.records(0) if (r.get("text") or "").startswith("[identity:")), 1)

    def test_pre_380_name_turn_is_backfilled_once(self):
        self.seed_live(self.core())
        term = self.core()
        self.assertEqual(term.identity_facts(), {"name": "SeVin"})
        self.assertEqual(self.core().identity_facts(), {"name": "SeVin"})

    def test_exact_live_ranking_scenario(self):
        m = self.core()
        self.seed_live(m)
        term = self.core()
        in_context = [{"role": "user", "content": "what did you just say about my name"},
                      {"role": "assistant", "content": "I said it was nice to meet you."}]
        idx = E.context_index(in_context)
        hits, info = term.recall_hybrid(QUESTION, top_k=6, threshold=0.0, candidates=16,
                                        exclude=lambda t: E.in_context(t, idx),
                                        extra_terms=ltm.identity_terms(QUESTION))
        texts = [h[1] for h in hits]
        self.assertIn(LIVE_ROWS[7], texts)                    # the name turn is recalled
        self.assertNotIn(LIVE_ROWS[2], texts)                 # the old denial is never recalled
        self.assertNotIn(LIVE_ROWS[10], texts)                # the turn already in context is left out
        self.assertNotIn(LIVE_ROWS[0], texts)                 # self-test turns are never recalled
        self.assertLess(texts.index(LIVE_ROWS[7]), 3)         # inside the old top 3 as well
        self.assertGreaterEqual(info["excluded"], 1)
        self.assertGreaterEqual(info["keyword"], 1)

    def test_self_test_and_denial_turns_are_not_stored(self):
        m = self.core()
        self.assertEqual(m.remember("Reply with the single word: ready", "ready"), [])
        self.assertEqual(m.remember("Do you remember who I am?", "I do not remember who you are."), [])
        with ltm.no_store("self-test"):
            self.assertEqual(m.remember("I keep my bike in the garage downstairs", "Noted."), [])
        self.assertEqual(m.count(), 0)
        # an introduction answered with a denial still pins the name, but not the denial
        ids = m.remember("My name is SeVin, do you remember me?", "I don't remember you yet.")
        self.assertEqual(len(ids), 1)
        self.assertEqual(self.core().identity_facts(), {"name": "SeVin"})

    def test_turn_written_by_another_view_is_recalled(self):
        term = self.core()
        term.count()   # loads its view first
        tg = self.core()
        tg.remember("I keep my bike in the garage downstairs", "Noted, the garage.")
        hits = term.recall("where is my bike", 3, 0.1)
        self.assertTrue(any("garage" in h[1] for h in hits))
        kw = term.keyword("garage", 3)
        self.assertTrue(kw)


class TestJsonRecall(RecallContract, unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tmpdir(self), "memory.json")

    def core(self):
        return MemoryCore(None, "x", settings=lt(backend="json"), embedder=FnEmbedder(fn=name_vec), path=self.path)

    def test_merge_on_write_never_overwrites(self):
        a, b = self.core(), self.core()
        a.count(), b.count()
        a.store("User: I like jazz records | Assistant: ok")
        b.store("User: I like hiking in the desert | Assistant: ok")
        a.store("User: my cat is called Miso | Assistant: ok")
        data = json.load(open(self.path))
        self.assertEqual(len(data), 3)
        self.assertEqual(self.core().count(), 3)

    def test_delete_elsewhere_stays_deleted(self):
        a, b = self.core(), self.core()
        rid = a.store("User: I like jazz records | Assistant: ok")
        b.count()
        a.delete(rid)
        b.store("User: I like hiking in the desert | Assistant: ok")
        self.assertEqual([r["text"] for r in json.load(open(self.path))],
                         ["User: I like hiking in the desert | Assistant: ok"])

    def test_concurrent_writers_lose_nothing(self):
        cores = [self.core() for _ in range(4)]
        for c in cores:
            c.count()

        def write(c, n):
            for i in range(10):
                c.store(f"User: fact number {n}-{i} about the lab | Assistant: ok", dedupe="off")
        ts = [threading.Thread(target=write, args=(c, n)) for n, c in enumerate(cores)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(len(json.load(open(self.path))), 40)


class TestLocalRecall(RecallContract, unittest.TestCase):
    def setUp(self):
        self.dir = os.path.join(tmpdir(self), "mem")

    def core(self):
        return MemoryCore(None, "x", settings=lt(backend="local", local={"directory": self.dir}),
                          embedder=FnEmbedder(fn=name_vec))


class TestOracleRecall(RecallContract, OracleCase):
    def setUp(self):
        super().setUp()
        self.shared_db = FakeOracleDB()
        self.shared_db.oracle_text = True       # CTXSYS available: the text index gets built
        self._first = True

    def core(self):
        m = OracleCase.core(self, self.shared_db, embedder=FnEmbedder(fn=name_vec))
        if self._first:
            m.setup()
            self._first = False
        return m

    def test_identity_lookup_is_plain_sql_on_kind(self):
        m = self.core()
        m.remember("My name is SeVin.", "Nice to meet you, SeVin!")
        self.core().identity_facts()
        sql = [s for s, _ in self.shared_db.sql if "ltm:by_kind" in s]
        self.assertTrue(sql)
        self.assertIn("kind = :k", sql[-1])
        self.assertNotIn("BEGIN", " ".join(sql))

    def test_keyword_side_uses_oracle_text_when_indexed(self):
        m = self.core()
        self.seed_live(m)
        m.recall_hybrid(QUESTION, top_k=6, threshold=0.0, extra_terms=ltm.identity_terms(QUESTION))
        if self.shared_db.text_indexes:
            self.assertIn("keyword_ctx", self.shared_db.keyword_calls)
        else:
            self.assertIn("keyword_instr", self.shared_db.keyword_calls)


class TestCrossProcess(unittest.TestCase):
    """A real second process (the Telegram bot in the background) writes; this
    process, which loaded the store first, recalls it."""

    def child(self, settings, path=None):
        code = textwrap.dedent(f"""
            import sys; sys.path.insert(0, {PROJECT!r})
            from nimlab.memory import MemoryCore
            from nimlab import environment as ENV
            from tests.test_ltm import FnEmbedder
            from tests.test_ltm import bag_vec
            m = MemoryCore(None, 'x', settings={settings!r}, embedder=FnEmbedder(fn=bag_vec), path={path!r})
            with ENV.channel('telegram'):
                ids = m.remember('My name is SeVin.', 'Nice to meet you, SeVin!')
                m.remember('I keep my bike in the garage downstairs', 'Noted, the garage.')
            print(len(ids))
        """)
        r = subprocess.run([sys.executable, "-c", code], cwd=PROJECT, capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "2")

    def check(self, settings, path=None):
        term = MemoryCore(None, "x", settings=settings, embedder=FnEmbedder(fn=bag_vec), path=path)
        self.assertEqual(term.count(), 0)          # loaded before the bot wrote anything
        term.store("User: the tunnel keeps dropping | Assistant: use a named tunnel")
        self.child(settings, path)
        self.assertEqual(term.identity_facts(), {"name": "SeVin"})
        hits = term.recall("I keep my bike in the garage", 10, 0.0)
        self.assertTrue(any("garage" in h[1] for h in hits))
        self.assertTrue(term.keyword("garage", 3))
        self.assertEqual(term.count(), 4)          # nothing overwritten: 1 here + 3 from the bot
        term.store("User: I like jazz records | Assistant: ok")
        self.assertEqual(MemoryCore(None, "x", settings=settings, embedder=FnEmbedder(fn=bag_vec), path=path).count(), 5)

    def test_json(self):
        path = os.path.join(tmpdir(self), "memory.json")
        self.check(lt(backend="json"), path)

    def test_local(self):
        self.check(lt(backend="local", local={"directory": os.path.join(tmpdir(self), "mem")}))


class TestEntityRecall(unittest.TestCase):
    """End to end through the served endpoint: introduce yourself in one
    session (Telegram), ask in another (the terminal call) with a fresh memory
    view, and the persona gets the name."""

    def setUp(self):
        from tests import test_entity as TE
        self.case = TE.EntityCase("run")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.dir = tmpdir(self)
        self.case.ent.memory = self.mem()

    def mem(self):
        return MemoryCore(None, "", settings=lt(backend="local", local={"directory": self.dir}),
                          embedder=FnEmbedder(fn=name_vec))

    def prompt(self):
        return json.dumps(self.case.persona_msgs())

    def test_name_from_telegram_reaches_the_terminal_call(self):
        c = self.case
        with ENV.channel("telegram"):
            c.ask("My name is SeVin.")
        c.ent.memory = self.mem()   # the terminal call: a new process view, no history
        c.ask(QUESTION)
        p = self.prompt()
        self.assertIn("KNOWN FACTS ABOUT THE USER", p)
        self.assertIn("Name: SeVin", p)

    def test_old_denial_and_in_context_turn_stay_out_of_the_prompt(self):
        c = self.case
        seed = self.mem()
        for t in LIVE_ROWS:
            seed.store(t, dedupe="off")
        c.ent.memory = self.mem()
        hist = [{"role": "user", "content": "what did you just say about my name"},
                {"role": "assistant", "content": "I said it was nice to meet you."}]
        j = c.ask(QUESTION, history=hist)
        p = self.prompt()
        self.assertIn("Name: SeVin", p)
        self.assertIn("My name is SeVin.", p)
        self.assertNotIn("I do not remember who you are", p)
        self.assertNotIn("single word: ready", p)
        last = c.persona_msgs()[-1]["content"]
        last = last if isinstance(last, str) else json.dumps(last)
        recalled = last.rsplit("User Input:", 1)[0]
        self.assertIn("My name is SeVin.", recalled)
        self.assertNotIn("what did you just say about my name", recalled)
        self.assertEqual(j["testbed"]["memory"]["backend"], "local")

    def test_self_test_header_stores_nothing(self):
        from nimlab import server as S
        c = self.case
        st, _, raw = c.call("/v1/chat/completions", {"model": "testbed", "messages": [
            {"role": "user", "content": "I keep my bike in the garage downstairs"}]},
            headers={S.SELF_TEST_HEADER: "1"})
        self.assertEqual(st, 200, raw)
        st, _, raw = c.call("/v1/chat/completions", {"model": "testbed", "stream": True, "messages": [
            {"role": "user", "content": "My name is Mallory and I live in Reno"}]}, headers={S.SELF_TEST_HEADER: "1"})
        self.assertEqual(st, 200, raw)
        self.assertEqual(c.ent.memory.count(), 0)
        c.ask("I keep my bike in the garage downstairs")
        self.assertEqual(c.ent.memory.count(), 1)

    def test_identity_question_adds_recent_memories(self):
        c = self.case
        c.ask("I keep my bike in the garage downstairs")
        c.ask("who am I?")
        self.assertIn("MOST RECENT MEMORIES", self.prompt())


class TestRecallCommands(unittest.TestCase):
    """memory recall uses the hybrid ranking; memory identity shows, sets and
    forgets pinned facts; the new settings can be changed with memory set."""

    def setUp(self):
        from argparse import Namespace
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest import mock
        from nimlab import memmenu
        d = tmpdir(self)
        self.cfg = os.path.join(d, "config_cluster.json")
        self.dir = os.path.join(d, "mem")
        with open(self.cfg, "w") as f:
            json.dump({"memory_settings": {"recall_top_k": 6, "recall_version": 380,
                                           "long_term": {"backend": "local", "local": {"directory": self.dir}}}}, f)
        for p in (mock.patch.object(config, "CLUSTER_CONFIG", self.cfg),
                  mock.patch.object(config, "load_cluster_config", lambda path=None: json.load(open(self.cfg))),
                  mock.patch.object(memmenu, "_mem", lambda cl, ms: MemoryCore(
                      None, "x", settings=ms, embedder=FnEmbedder(fn=name_vec)))):
            p.start()
            self.addCleanup(p.stop)

        def run(action, *values):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = memmenu.cmd_memory(Namespace(action=action, values=list(values)))
            return rc, buf.getvalue()
        self.run_cli = run

    def test_identity_and_recall(self):
        rc, out = self.run_cli("identity")
        self.assertEqual(rc, 0)
        self.assertIn("nothing pinned yet", out)
        self.assertEqual(self.run_cli("identity", "set", "name", "SeVin")[0], 0)
        self.assertIn("Name: SeVin", self.run_cli("identity")[1])
        m = MemoryCore(None, "x", settings=lt(backend="local", local={"directory": self.dir}),
                       embedder=FnEmbedder(fn=name_vec))
        for t in LIVE_ROWS:
            m.store(t, dedupe="off")
        rc, out = self.run_cli("recall", *QUESTION.split())
        self.assertEqual(rc, 0)
        self.assertIn("pinned Name: SeVin", out)
        self.assertIn("My name is SeVin.", out)
        self.assertNotIn("I do not remember who you are", out)
        self.assertIn("keyword", out)
        self.assertIn("Removed 1.", self.run_cli("identity", "forget", "name")[1])
        self.assertEqual(self.run_cli("identity", "bogus")[0], 2)

    def test_memory_add_pins_identity_and_stores(self):
        """3.8.1: nimlab memory add (Telegram /remember)."""
        self.assertEqual(self.run_cli("add")[0], 2)
        rc, out = self.run_cli("add", "--user", "telegram:42", "My", "name", "is", "SeVin")
        self.assertEqual(rc, 0)
        self.assertIn("Remembered", out)
        self.assertIn("Name: SeVin", self.run_cli("identity")[1])
        rc, out = self.run_cli("add", "I", "drink", "green", "tea", "every", "morning")
        self.assertEqual(rc, 0)
        self.assertIn("Remembered.", out)
        self.assertIn("Already remembered", self.run_cli("add", "I", "drink", "green", "tea", "every", "morning")[1])

    def test_set_new_recall_settings(self):
        for name, val in (("hybrid_recall", "off"), ("exclude_context_turns", "false"), ("recall_max_chars", "1200"),
                          ("hybrid_keyword_weight", "1.5"), ("pin_identity", "off")):
            self.assertEqual(self.run_cli("set", name, val)[0], 0, name)
        ms = json.load(open(self.cfg))["memory_settings"]
        self.assertIs(ms["hybrid_recall"], False)
        self.assertIs(ms["exclude_context_turns"], False)
        self.assertEqual(ms["recall_max_chars"], 1200)
        self.assertEqual(ms["hybrid_keyword_weight"], 1.5)
        self.assertIs(ms["long_term"]["pin_identity"], False)

    def test_budget_cuts_long_memories(self):
        hits = [(0.9, "x" * 2000, "t", 1), (0.8, "y" * 900, "t", 2), (0.7, "z" * 900, "t", 3), (0.6, "w" * 900, "t", 4)]
        out = E.fit_budget(hits, 2400)
        self.assertEqual(len(out[0][1]), 800)
        self.assertEqual(len(out), 3)
        self.assertEqual(len(E.fit_budget(hits, 10)), 1)

if __name__ == "__main__":
    unittest.main()
