"""3.7.2 router benchmark: it drives the testbed's own turn pipeline (fake
NVIDIA), records routing vs API time per turn, aggregates per route, and
saves to the benchmark history."""

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import perf, routerbench as RB, store
from tests.helpers import fresh_store
from tests.test_entity import Backend, ROLES, SOUL
from tests.test_roles import make_entity


class RouterBench(unittest.TestCase):
    def setUp(self):
        cm = fresh_store()
        cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        self.backend = Backend()
        self.ent, _ = make_entity(self, dict(ROLES), self.backend.opener)
        self.ent.soul = SOUL

    def test_chat_turn_uses_entity_turn_and_records_calls(self):
        self.backend.route = "reasoning"
        with mock.patch.object(self.ent, "turn", wraps=self.ent.turn) as turn:
            row = RB.run_turn(self.ent, RB.prompt_set(["reasoning"])[0])
        turn.assert_called_once()                     # the same entry point testbed chat uses
        self.assertTrue(row["ok"], row)
        self.assertEqual(row["route"], "reasoning")
        self.assertTrue(row["hit"])
        models = [c["url"] for c in row["calls"]]
        self.assertTrue(any("chat/completions" in u for u in models))
        for c in row["calls"]:
            self.assertGreater(c["sent"], 0)
            self.assertIsNotNone(c["first_ms"])
            self.assertGreaterEqual(c["total_ms"], c["first_ms"])
        self.assertEqual(row["total_ms"] >= row["api_ms"], True)
        self.assertEqual(row["overhead_ms"],
                         max(0, row["total_ms"] - row["router_ms"] - row["api_ms"] - row["memory_ms"]))
        self.assertEqual(row["via"], "router")
        self.assertIn("intent_router", {c.get("stage") for c in row["calls"]})   # the router's own call is timed
        self.assertIn("meta/router-model", self.backend.models())     # the real intent router ran

    def test_wrong_route_is_a_miss(self):
        self.backend.route = "persona"
        row = RB.run_turn(self.ent, RB.prompt_set(["coding"])[0])
        self.assertFalse(row["hit"])

    def test_image_turn_goes_through_the_attachment_pipeline(self):
        from nimlab import attach
        with mock.patch.object(attach, "run_with_files", wraps=attach.run_with_files) as rwf:
            row = RB.run_turn(self.ent, RB.prompt_set(["vision"])[0], tmp=self._tmp())
        rwf.assert_called_once()
        self.assertTrue(row["ok"], row)
        self.assertIn("meta/vision-model", self.backend.models())

    def test_call_mode_uses_the_voice_pipeline(self):
        from nimlab import unified
        with mock.patch.object(unified.Mind, "run", autospec=True, side_effect=unified.Mind.run) as run:
            row = RB.run_turn(self.ent, RB.prompt_set(["spoken"])[0], call=True, tmp=self._tmp())
        kw = run.call_args.kwargs
        self.assertTrue(kw["defer_store"])
        self.assertTrue(kw["want_audio"])
        self.assertTrue(row["ok"], row)

    def test_run_aggregates_median_p95_and_saves_history(self):
        self.backend.route = "coding"
        lines = []
        rep = RB.run(self.ent, runs=3, only=["coding", "casual"], extra=["my own prompt"], compare=True,
                     out=lines.append)
        self.assertEqual(len(rep["turns"]), 9)
        a = rep["by_prompt"]["coding"]
        self.assertEqual(a["turns"], 3)
        self.assertEqual(a["accuracy"], 1.0)
        self.assertLessEqual(a["total_ms"]["median"], a["total_ms"]["p95"])
        self.assertIn("user", rep["by_route"])
        self.assertIn("coding", rep["direct"])
        hist = store.load(store.BENCH_HISTORY)["runs"]
        self.assertEqual(hist[0]["kind"], "router")
        self.assertEqual(RB.latest()["runs"], 3)
        text = "\n".join(RB.report_lines(rep))
        self.assertIn("Routing accuracy", text)
        self.assertIn("Direct model calls", text)
        self.assertIn("overhead", text)

    def test_percentile(self):
        self.assertEqual(RB.pct([1, 2, 3, 4, 100], 95), 100)
        self.assertEqual(RB.pct([5], 95), 5)
        self.assertIsNone(RB.pct([], 95))

    def test_note_http_is_a_noop_outside_a_tracked_turn(self):
        self.assertIsNone(perf.note_http("POST", "https://x/y", 10, 200, 1, 2, 3))
        with perf.track("t") as tr:
            perf.note_http("POST", "https://x/y", 10, 200, 1, 2, 3)
        self.assertEqual(tr.net[0]["sent"], 10)

    def test_cli_show_and_no_key(self):
        from nimlab import cli
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["bench", "router", "--show"]), 1)
        self.assertIn("No router benchmark yet", out.getvalue())
        with mock.patch("nimlab.core.load_api_key", return_value=None), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(["bench", "router"]), 2)
        self.assertIn("nimlab setup key", out.getvalue())

    def _tmp(self):
        import tempfile
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        return d


if __name__ == "__main__":
    unittest.main()
