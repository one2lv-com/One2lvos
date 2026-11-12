import unittest
from unittest import mock

import nvidia_benchmark_suite as b

I = "https://integrate.api.nvidia.com/v1"
FLEET = {
    "acme/chat-1": {"status": "LIVE_200", "kind": "chat", "url": f"{I}/chat/completions"},
    "acme/model-vl": {"status": "LIVE_200", "kind": "vision", "url": f"{I}/chat/completions"},
    "acme/embed-1b": {"status": "LIVE_200", "kind": "embeddings", "url": f"{I}/embeddings"},
    "meta/llama-guard-4-12b": {"status": "LIVE_200", "kind": "chat", "url": f"{I}/chat/completions"},
    "nvidia/rerank-qa": {"status": "LIVE_200", "kind": "rerank", "url": "https://ai.api.nvidia.com/v1/retrieval/nvidia/rerank"},
    "acme/flux": {"status": "LIVE_200", "kind": "image_gen", "catalog_kind": "image_gen",
                  "url": "https://ai.api.nvidia.com/v1/genai/acme/flux", "request_template": {"prompt": "x"}},
    "nvidia/magpie-tts-multilingual": {"status": "LIVE_200", "kind": "tts", "content_type": "multipart/form-data",
                                       "function_id": "fid",
                                       "url": "https://fid.invocation.api.nvcf.nvidia.com/v1/audio/synthesize"},
    "acme/dead": {"status": "RETIRED_OR_DEPRECATED"},
}


class FakeProber:
    def __init__(self):
        self.plans = []

    def probe_plan(self, plan, deprecated=False, retired=False):
        self.plans.append(plan)
        return {"status": "LIVE_200", "reason": "", "http_status": 200, "latency_sec": 0.2}


class CoverageTest(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(b, "load_live_fleet", lambda path=None: {k: v for k, v in FLEET.items()
                                                                      if v["status"] == "LIVE_200"})
        p.start()
        self.addCleanup(p.stop)

    def test_every_live_model_lands_in_a_track(self):
        e, v, r, o = b.partition_fleet(with_others=True)
        names = [x[0] for x in e + v + r] + [m for m, _ in o]
        live = [k for k, x in FLEET.items() if x["status"] == "LIVE_200"]
        self.assertEqual(sorted(names), sorted(live))
        self.assertIn("7 = ", b.coverage_line(e, v, r, o))
        self.assertEqual(len(b.partition_fleet()), 3)  # old callers unchanged

    def test_smoke_reprobes_with_saved_route(self):
        _, _, _, o = b.partition_fleet(with_others=True)
        fp = FakeProber()
        res = b.run_smoke_benchmarks(o, prober=fp)
        self.assertTrue(all(x["status"] == "LIVE_200" for x in res))
        by = {p["model"]: p for p in fp.plans}
        self.assertEqual(by["nvidia/magpie-tts-multilingual"]["kind"], "tts")
        self.assertEqual(by["nvidia/magpie-tts-multilingual"]["function_id"], "fid")
        self.assertEqual(by["acme/flux"]["body"], {"prompt": "x"})
        self.assertIn("passages", by["nvidia/rerank-qa"]["body"])
        self.assertIn("messages", by["meta/llama-guard-4-12b"]["body"])


if __name__ == "__main__":
    unittest.main()
