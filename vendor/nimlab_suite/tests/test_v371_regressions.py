"""3.7.1 regression checks added in the final pass: automatic memory on
every channel, the setup self-test retry/continue and bug IDs, the MCP
startup counts, and the bug log's cap, expiry and redaction."""

import gzip
import io
import json
import os
import time
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import bugs, mcp, unified
from nimlab import server as S
from nimlab.memory import MemoryCore
from tests import test_ltm as TL
from tests.helpers import fresh_store


# ---------------------------------------------------------------------------
# (d) automatic recall before the persona, store after the reply, same scope
# ---------------------------------------------------------------------------
class MemoryOnEveryChannel(unittest.TestCase):
    def setUp(self):
        from tests import test_entity as TE
        self.case = TE.EntityCase("run")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.dir = TL.tmpdir(self)
        self.case.ent.cluster.setdefault("memory_settings", {})["similarity_threshold"] = 0.2
        self.case.ent.memory = MemoryCore(None, "", settings=TL.lt(backend="local", local={"directory": self.dir}),
                                          embedder=TL.FnEmbedder())
        self.ent = self.case.ent

    def prompt(self):
        return json.dumps(self.case.persona_msgs())

    def count(self):
        return self.ent.memory.count()

    def test_terminal_chat_turn_stores_then_recalls(self):
        out = self.ent.turn("Remember that my dog is called Pixel", [])
        self.assertTrue(out["result"].ok)
        self.assertEqual(self.count(), 1)                 # stored right after the reply
        self.ent.turn("what is my dog Pixel called?", [])
        self.assertIn("my dog is called Pixel", self.prompt())   # recalled before the persona

    def test_voice_turn_stores_after_reply_and_recalls(self):
        mind = unified.Mind(self.ent)
        res = mind.run("Remember that my bike is a red Bianchi", [], [], defer_store=True)
        self.assertTrue(res["ok"], res.get("error"))
        self.assertEqual(self.count(), 0)                 # not before the reply is played
        res["finish"]()
        self.assertEqual(self.count(), 1)
        mind.run("which bike do I have, the Bianchi?", [], [], defer_store=True)
        self.assertIn("red Bianchi", self.prompt())

    def test_telegram_endpoint_and_terminal_share_one_scope(self):
        c = self.case
        j = c.ask("Remember that my boat is named Tern", user="telegram:1111")   # what the Telegram bot sends
        self.assertEqual(j["testbed"]["memory"]["stored"], 1, j["testbed"])
        self.ent.memory.settings["auto_store"] = False      # keep the store to that one memory
        c.ask("what is my boat Tern called?")                                     # a plain endpoint client
        self.assertIn("my boat is named Tern", self.prompt())
        self.ent.turn("tell me my boat name, Tern", [])                         # the terminal chat
        self.assertIn("my boat is named Tern", self.prompt())
        unified.Mind(self.ent).run("say my boat name Tern", [], [], defer_store=True)   # a voice call
        self.assertIn("my boat is named Tern", self.prompt())
        self.assertEqual(self.count(), 1)

    def test_auto_store_off_is_respected_on_every_channel(self):
        self.ent.memory.settings["auto_store"] = False
        self.ent.turn("Remember that my car is green", [])
        res = unified.Mind(self.ent).run("Remember my car is green", [], [], defer_store=True)
        if callable(res.get("finish")):
            res["finish"]()
        self.case.ask("Remember that my car is green", user="telegram:1111")
        self.assertEqual(self.count(), 0)


# ---------------------------------------------------------------------------
# (a) self-test: wording, bug IDs, retry/continue in setup
# ---------------------------------------------------------------------------
class SelfTestWording(unittest.TestCase):
    def setUp(self):
        cm = fresh_store()
        cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        bugs.configure({})
        self.addCleanup(bugs.configure, None)

    def test_slow_model_is_not_blamed_on_the_port(self):
        rows = [("GET /v1/models", "PASS", "1 model", 5),
                ("identity comes from soul.md", "FAIL", "timed out after 90 s waiting for a reply", 90000)]
        lines = S.failure_summary(rows)
        text = "\n".join(lines)
        self.assertNotIn("port", text.lower())
        self.assertIn("too slow", text)
        self.assertRegex(lines[0], r"identity comes from soul\.md: timed out .*\(bug B-[0-9A-F]+")

    def test_heavy_only_failure_says_setup_can_go_on(self):
        heavy = sorted(S.HEAVY_CHECKS)[0]
        rows = [("GET /v1/models", "PASS", "", 5), (heavy, "FAIL", "timed out after 240 s waiting for a reply", 1)]
        text = "\n".join(S.failure_summary(rows))
        self.assertIn("not the port", text)
        self.assertIn("Setup can go on", text)
        self.assertTrue(bugs.list_bugs(), "the failed check got no bug record")

    def test_unreachable_server_mentions_port(self):
        rows = [("GET /v1/models", "FAIL", "could not connect (Connection refused)", 1)]
        self.assertIn("port", "\n".join(S.failure_summary(rows)))


class SetupRetryContinue(unittest.TestCase):
    def setUp(self):
        cm = fresh_store()
        cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)

    def run_step(self, answers, results):
        from tests import test_wizard as TW
        seq = iter(results)
        calls = []

        def cli(argv, timeout=900, input_text=None, show=True):
            calls.append(" ".join(argv))
            return next(seq)
        w, fio, _cli, _ = TW.make([True] + answers, cli=cli)
        w.server_test()
        return calls, fio

    def test_retry_then_pass(self):
        calls, _ = self.run_step(["retry"], [(1, "FAIL"), (0, "ok")])
        self.assertEqual(calls, ["serve test quick", "serve test quick"])

    def test_continue_after_failure(self):
        calls, fio = self.run_step(["continue"], [(1, "FAIL")])
        self.assertEqual(calls, ["serve test quick"])
        self.assertIn("Setup goes on", fio.text)


# ---------------------------------------------------------------------------
# (c) MCP: exposed vs allowed counts at startup
# ---------------------------------------------------------------------------
class McpStartupCounts(unittest.TestCase):
    """3.7.3: '[MCP] N tools from URL, all available'; local overrides noted."""
    TOOLS = [{"name": n, "description": ""} for n in
             ("charlie_mem", "maya_mem", "web_search_exa", "send_gmail_message", "terminal")]

    def test_all_available_by_default(self):
        p = mcp.ToolPolicy.from_settings({"allowed_tools": [], "own_memory_tool": "charlie_mem"}, agent="Charlie")
        line = mcp.exposure_line(self.TOOLS, p, "https://example.test/mcp")
        self.assertTrue(line.startswith("[MCP] 5 tools from https://example.test/mcp, all available"), line)
        self.assertNotIn("blocked", line)
        self.assertNotIn("maya_mem", line)       # no per-tool list in the summary

    def test_local_overrides_are_noted(self):
        p = mcp.ToolPolicy.from_settings({"blocked_tools": ["terminal"]}, agent="Charlie")
        line = mcp.exposure_line(self.TOOLS, p, "https://example.test/mcp")
        self.assertIn("[MCP] 5 tools from https://example.test/mcp: 4 available, 1 left out by local overrides", line)
        self.assertIn("blocked_tools: terminal", line)


# ---------------------------------------------------------------------------
# (f) bug log: size cap, two-week expiry, redaction
# ---------------------------------------------------------------------------
class BugLogRetention(unittest.TestCase):
    def setUp(self):
        cm = fresh_store()
        cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        self.addCleanup(bugs.configure, None)

    def test_defaults(self):
        self.assertEqual(bugs.DEFAULTS["max_mb"], 5)
        self.assertEqual(bugs.DEFAULTS["keep_days"], 14)

    def test_size_cap_holds(self):
        bugs.configure({"max_mb": 0.25, "compress": False, "max_event_kb": 64})
        cap = 0.25 * 1024 * 1024
        for i in range(400):
            bugs.record("server_error", f"boom {i} " + "x" * 3000, where=f"/v1/r{i % 7}")
        self.assertLessEqual(bugs.total_bytes(), cap)
        self.assertTrue(bugs.list_bugs())          # still recording

    def test_one_event_is_cut(self):
        bugs.configure({"max_event_kb": 4})
        bugs.record("upstream_error", "big", upstream="y" * 50000)
        with open(os.path.join(bugs.bug_dir(), bugs.EVENTS), encoding="utf-8") as f:
            line = f.readline()
        self.assertLess(len(line.encode()), 4 * 1024 + 512)
        self.assertIn("(cut)", line)

    def test_two_week_expiry(self):
        bugs.configure({"keep_days": 14})
        bid = bugs.record("timeout", "slow", where="x")
        old = os.path.join(bugs.bug_dir(), bugs.ARCHIVE_PREFIX + "20000101-000000-0.jsonl.gz")
        with gzip.open(old, "wb") as f:
            f.write(b'{"id": "B-OLD"}\n')
        fifteen = time.time() - 15 * 86400
        os.utime(old, (fifteen, fifteen))
        done = bugs.enforce(now=time.time())
        self.assertEqual(done["expired"], 1)
        self.assertFalse(os.path.exists(old))
        self.assertIn(bid, [r["id"] for r in bugs.list_bugs()])
        done = bugs.enforce(now=time.time() + 15 * 86400)        # the row itself ages out too
        self.assertEqual(done["rows_dropped"], 1)
        self.assertEqual(bugs.list_bugs(), [])

    def test_redaction(self):
        bugs.configure({})
        tg = "123456789:" + "A" * 35
        nv = "nvapi-" + "k" * 40
        bugs.record("internal", f"failed with key {nv}", upstream='{"password": "Sup3rSecret", "x": 1}',
                    context={"url": f"https://api.telegram.org/bot{tg}/getUpdates",
                             "dsn": "https://scott:tiger99@db.example.com/ords", "q": "api_key=abcdef123"})
        with open(os.path.join(bugs.bug_dir(), bugs.EVENTS), encoding="utf-8") as f:
            text = f.read()
        for secret in (tg, nv, "Sup3rSecret", "tiger99", "abcdef123"):
            self.assertNotIn(secret, text)
        self.assertIn("scott:****@", text)

    def test_record_never_raises(self):
        bugs.configure({})
        with mock.patch.object(bugs, "_save_index", side_effect=OSError("disk full")):
            self.assertTrue(bugs.record("internal", "x"))


class VersionEverywhere(unittest.TestCase):
    def test_version_is_386_everywhere(self):
        import nimlab
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertEqual(nimlab.__version__, "3.8.6")
        with open(os.path.join(root, "CHANGES.md"), encoding="utf-8") as f:
            first = next(l for l in f if l.startswith("## "))
        self.assertEqual(first.strip(), "## v3.8.6")
        self.assertEqual(S.VERSION, "3.8.6")
        with open(os.path.join(root, "start.sh"), encoding="utf-8") as f:
            self.assertNotRegex(f.read(), r"3\.[0-6]\.\d+|3\.7\.\d+\b")   # start.sh reads the version from Python


if __name__ == "__main__":
    unittest.main()
