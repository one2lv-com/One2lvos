"""v3.7.1 regression tests for the embedding fixes: input_type retry rules
(never retried without a field the model says is required), the model's own
error text in the memory test, the pending queue with keyword search, and
the vector-size check against the table."""

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from nimlab import api, ltm
from nimlab.memory import MemoryCore
from tests.fakes import FakeResponse, http_error
from tests.test_core import NimClientTests
from tests.test_ltm import FnEmbedder, bag_vec, lt

OK = {"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]}


class TestInputTypeRetryRules(NimClientTests):
    """NimClient.embed: which 400/422 replies are retried, and with what."""

    def test_input_type_always_sent_with_truncate_and_float(self):
        c, op = self.make([FakeResponse(OK)])
        r = c.embed("nvidia/llama-3.2-nv-embedqa-1b-v2", ["hi"], input_type="passage")
        self.assertTrue(r.ok)
        body = (op.body(0))
        self.assertEqual((body["input_type"], body["truncate"], body["encoding_format"]), ("passage", "END", "float"))
        self.assertEqual(len(op.requests), 1)

    def test_required_input_type_is_never_dropped(self):
        err = b'{"detail": "input_type is required for model llama-nemotron-embed-vl-1b-v2, invalid request"}'
        c, op = self.make([http_error(400, err), FakeResponse(OK)])
        r = c.embed("nvidia/llama-nemotron-embed-vl-1b-v2", ["hi"], input_type="query")
        self.assertFalse(r.ok)
        self.assertEqual(len(op.requests), 1)                 # no retry at all
        self.assertIn("HTTP 400", r.error)
        self.assertIn("input_type is required", r.error)      # the model's own words

    def test_unknown_input_type_is_retried_once_without_it(self):
        c, op = self.make([http_error(422, b'{"error": "Extra inputs are not permitted: input_type"}'),
                           FakeResponse(OK)])
        r = c.embed("some/plain-embedder", ["hi"], input_type="query")
        self.assertTrue(r.ok)
        self.assertEqual(len(op.requests), 2)
        self.assertNotIn("input_type", (op.body(1)))
        self.assertIn("truncate", (op.body(1)))     # only the named field is dropped

    def test_unknown_truncate_dropped_but_input_type_kept(self):
        c, op = self.make([http_error(400, b'{"error": "unexpected field truncate"}'), FakeResponse(OK)])
        self.assertTrue(c.embed("m", ["hi"], input_type="passage").ok)
        b1 = (op.body(1))
        self.assertNotIn("truncate", b1)
        self.assertEqual(b1["input_type"], "passage")

    def test_failed_retry_keeps_the_first_error(self):
        c, op = self.make([http_error(400, b'{"error": "unknown field input_type"}'),
                           http_error(500, b'{"error": "model crashed"}')])
        r = c.embed("m", ["hi"], input_type="query")
        self.assertFalse(r.ok)
        self.assertEqual(len(op.requests), 2)
        self.assertIn("unknown field input_type", r.error)
        self.assertIn("retried without input_type", r.error)
        self.assertIn("model crashed", r.error)

    def test_unrelated_400_is_not_retried(self):
        c, op = self.make([http_error(400, b'{"error": "input too long"}'), FakeResponse(OK)])
        r = c.embed("m", ["hi"], input_type="query")
        self.assertFalse(r.ok)
        self.assertEqual(len(op.requests), 1)
        self.assertIn("input too long", r.error)

    def test_empty_embedding_is_an_error_with_the_body(self):
        c, _ = self.make([FakeResponse({"data": [{"index": 0, "embedding": []}]})])
        r = c.embed("m", ["hi"], input_type="query")
        self.assertFalse(r.ok)
        self.assertIn("no embedding", r.error)


class MemCase(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p = mock.patch.dict(os.environ, {"NIMLAB_DATA_DIR": d})
        p.start()
        self.addCleanup(p.stop)
        self.dir = d

    def core(self, emb, **kw):
        s = lt(backend="local", local={"directory": os.path.join(self.dir, "ltm")}, embedding={"provider": "role"},
               **kw)
        return MemoryCore(None, "x", settings=s["long_term"] | {"auto_store": True}, embedder=emb)


class ErrEmbedder(FnEmbedder):
    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def embed(self, text, input_type):
        self.calls.append((text, input_type))
        if self.msg:
            raise ltm.EmbedError(self.msg)
        return self.fn(text)


class TestMemoryTestErrorText(MemCase):
    def test_memory_test_shows_status_and_model_text(self):
        emb = ErrEmbedder("NVIDIA nvidia/llama-nemotron-embed-vl-1b-v2: HTTP 400: input_type is required")
        emb.label = "nvidia/llama-nemotron-embed-vl-1b-v2"
        m = self.core(emb)
        rows = m.test()
        bad = [msg for ok, msg in rows if not ok]
        self.assertTrue(bad)
        self.assertIn("HTTP 400", bad[0])
        self.assertIn("input_type is required", bad[0])
        self.assertIn("input_type=query", bad[0])
        self.assertNotIn("no vector", bad[0])

    def test_memory_test_sends_query_and_passage(self):
        emb = ErrEmbedder(None)
        m = self.core(emb)
        rows = m.test()
        self.assertTrue(all(ok for ok, _ in rows), rows)
        self.assertEqual([c[1] for c in emb.calls], ["query", "passage"])

    def test_nvidia_embedder_error_reaches_the_test(self):
        class Client:
            def embed(self, model, texts, input_type=None, url=None, timeout=None):
                return api.ModelResult(False, error="HTTP 400: input_type is required", status=400)
        emb = ltm.NvidiaEmbedder({"model": "nvidia/llama-nemotron-embed-vl-1b-v2"}, Client())
        with self.assertRaises(ltm.EmbedError) as cm:
            emb.embed("x", "query")
        self.assertIn("HTTP 400: input_type is required", str(cm.exception))


class TestPendingQueue(MemCase):
    def test_failed_embedding_queues_turn_and_keyword_finds_it(self):
        emb = ErrEmbedder("HTTP 503: model loading")
        m = self.core(emb)
        self.assertIsNone(m.store("User: my locker code is LK-4471 | Assistant: saved", turn_key="k1"))
        q = m.pending()
        self.assertEqual(len(q), 1)
        self.assertIn("model loading", json.dumps(q[0]))
        hits = m.keyword("LK-4471")
        self.assertTrue(hits and "LK-4471" in hits[0][1])
        self.assertTrue(any(not ok and "1 turn(s) wait" in msg for ok, msg in m.test()))
        # the same turn is not queued twice
        m.store("User: my locker code is LK-4471 | Assistant: saved", turn_key="k1")
        self.assertEqual(len(m.pending()), 1)
        emb.msg = None
        self.assertEqual(m.embed_pending(), (1, 0))
        self.assertEqual(m.pending(), [])
        self.assertTrue(m.recall("locker code", threshold=-1))

    def test_queue_drains_on_next_good_store(self):
        emb = ErrEmbedder("HTTP 500")
        m = self.core(emb)
        m.store("User: first fact alpha | Assistant: ok", turn_key="a")
        self.assertEqual(len(m.pending()), 1)
        emb.msg = None
        m.store("User: second fact beta | Assistant: ok", turn_key="b")
        self.assertEqual(m.pending(), [])


class TestSizeMismatch(MemCase):
    def test_wrong_size_is_queued_and_explained(self):
        emb = FnEmbedder(fn=lambda t: bag_vec(t, 4))
        m = self.core(emb)
        with mock.patch.object(type(m), "table_dims", return_value=2048):
            self.assertIsNone(m.store("User: the wifi is Zebra-5 | Assistant: ok", turn_key="w"))
            self.assertEqual(len(m.pending()), 1)
            self.assertIn("VECTOR(2048)", m.last_error)
            self.assertIn("4 dimensions", m.last_error)
            rows = m.test()
            msg = [msg for ok, msg in rows if not ok and "VECTOR(2048)" in msg]
            self.assertTrue(msg)
            self.assertIn("nimlab memory embed models", msg[0])
            self.assertIn("nimlab memory reembed --recreate", msg[0])
            # still wrong: embed-pending keeps it waiting
            self.assertEqual(m.embed_pending(), (0, 1))
        self.assertEqual(m.embed_pending(), (1, 0))       # any size accepted again

    def test_named_commands_exist(self):
        from nimlab import cli
        p = cli.build_parser()
        for argv in (["memory", "embed", "models"], ["memory", "reembed", "--recreate"],
                     ["memory", "embed-pending"], ["memory", "pending"]):
            p.parse_args(argv)


if __name__ == "__main__":
    unittest.main()
