import unittest
from unittest import mock

import nvidia_playground as pg
from nimlab import sweep

MATRIX = [
    {"name": "chat", "url": "https://integrate.api.nvidia.com/v1/chat/completions", "kind": "chat"},
    {"name": "emb", "url": "https://integrate.api.nvidia.com/v1/embeddings", "kind": "embeddings"},
    {"name": "cv", "template": "https://ai.api.nvidia.com/v1/cv/{publisher}/{name}", "kind": "cv"},
]
SPEC_URL = "https://ai.api.nvidia.com/v1/genai/acme/new-model"


def outcome(status, http):
    return {"status": status, "reason": f"http {http}", "http_status": http, "latency_sec": 0.1,
            "payload": "schema", "request_keys": []}


class FakeProber:
    api_key = "nvapi-should-not-leak"

    def __init__(self, answers):
        self.answers = answers  # url -> (status, http); default 404
        self.calls = []

    def probe_plan(self, plan, deprecated=False, retired=False):
        self.calls.append(plan)
        st, http = self.answers.get(plan["url"], (sweep.RETIRED, 404))
        return outcome(st, http)


class FakeResolver:
    def __init__(self, doc):
        self.doc = doc
        self.calls = 0

    def resolve(self, model_id, use_cache=True):
        self.calls += 1
        return dict(self.doc, model_id=model_id)


def spec_doc(plans=None, **kw):
    d = {"model_id": "acme/new-model", "api_model_id": "acme/new-model", "plans": plans or [], "notes": {},
         "spec_source": "page" if plans else None, "page_status": 200}
    d.update(kw)
    return d


SPEC_PLAN = {"url": SPEC_URL, "method": "POST", "content_type": "application/json", "kind": "image_gen",
             "model": "acme/new-model", "body": {"prompt": "x"}, "alt_body": None, "transport": "rest",
             "source": "page", "function_id": None, "path": "/genai/acme/new-model"}


class RegisteredPlansTest(unittest.TestCase):
    def test_verified_entry_first_then_matrix_deduped(self):
        v = {"url": "https://example.invalid/v1/custom", "kind": "chat", "status": "LIVE_200"}
        plans = pg.registered_plans("acme/new-model", pg.TINY_IMAGE_DATA_URI, MATRIX, v)
        self.assertEqual(plans[0]["url"], v["url"])
        self.assertEqual(plans[0]["source"], "verified_json")
        urls = [(p["kind"], p["url"]) for p in plans]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertIn("https://integrate.api.nvidia.com/v1/embeddings", [p["url"] for p in plans])
        # cv template has no classic payload, so it is left to the spec stage
        self.assertNotIn("https://ai.api.nvidia.com/v1/cv/acme/new-model", [p["url"] for p in plans])

    def test_multipart_override_becomes_tts_form(self):
        v = {"url": "https://fid.invocation.api.nvcf.nvidia.com/v1/audio/synthesize", "kind": "audio_tts",
             "content_type": "multipart/form-data", "function_id": "fid"}
        p = pg.registered_plans("nvidia/magpie-tts-multilingual", pg.TINY_IMAGE_DATA_URI, [], v)[0]
        self.assertEqual(p["kind"], "tts")
        self.assertEqual(p["function_id"], "fid")


class ProbeSingleModelTest(unittest.TestCase):
    def test_registered_live_skips_spec(self):
        prober = FakeProber({"https://integrate.api.nvidia.com/v1/chat/completions": (sweep.LIVE, 200)})
        resolver = FakeResolver(spec_doc([SPEC_PLAN]))
        e = pg.probe_single_model("acme/new-model", pg.TINY_IMAGE_DATA_URI, MATRIX, prober, resolver)
        self.assertEqual(e["status"], sweep.LIVE)
        self.assertEqual(resolver.calls, 0)

    def test_falls_back_to_scraped_spec(self):
        prober = FakeProber({SPEC_URL: (sweep.LIVE, 200)})
        resolver = FakeResolver(spec_doc([SPEC_PLAN]))
        e = pg.probe_single_model("acme/new-model", pg.TINY_IMAGE_DATA_URI, MATRIX, prober, resolver)
        self.assertEqual(resolver.calls, 1)
        self.assertEqual(e["status"], sweep.LIVE)
        self.assertEqual(e["url"], SPEC_URL)
        self.assertIn("scraped spec", e["reason"])
        self.assertEqual(prober.calls[-1]["url"], SPEC_URL)

    def test_no_spec_keeps_most_informative_failure(self):
        prober = FakeProber({"https://integrate.api.nvidia.com/v1/chat/completions": (sweep.AUTH, 403)})
        e = pg.probe_single_model("acme/new-model", pg.TINY_IMAGE_DATA_URI, MATRIX, prober,
                                  FakeResolver(spec_doc()))
        self.assertEqual(e["status"], sweep.AUTH)
        self.assertNotIn("nvapi-should-not-leak", str(e))

    def test_retired_page_and_spec_check_off(self):
        prober = FakeProber({})
        e = pg.probe_single_model("acme/old", pg.TINY_IMAGE_DATA_URI, MATRIX, prober,
                                  FakeResolver(spec_doc(catalog_status="retired")))
        self.assertEqual(e["status"], sweep.RETIRED)
        e = pg.probe_single_model("acme/old", pg.TINY_IMAGE_DATA_URI, MATRIX, prober, None)
        self.assertIn("spec check off", e["reason"])

    def test_grpc_speech(self):
        e = pg.probe_single_model("nvidia/parakeet-ctc-1.1b-asr", pg.TINY_IMAGE_DATA_URI, [], FakeProber({}), None)
        self.assertEqual(e["status"], sweep.GRPC)


class ModelListTest(unittest.TestCase):
    def test_adds_models_registered_in_json(self):
        from nimlab import store
        from tests.helpers import fresh_store
        with fresh_store():
            ver = store.load(store.VERIFIED)
            ver["models"] = {"a/one": {"status": "LIVE_200"}, "b/two": {"status": "LIVE_200"}}
            store.save(store.VERIFIED, ver)
            eps = store.load(store.ENDPOINTS)
            eps["routing"]["explicit_model_overrides"] = {"c/three": {}, "a/one": {}}
            store.save(store.ENDPOINTS, eps)
            with mock.patch.object(pg, "ALL_MODELS", ["a/one"]):
                ids = pg.sweep_model_list()
            for m in ("a/one", "b/two", "c/three"):
                self.assertIn(m, ids)
            self.assertEqual(len(ids), len(set(ids)))


class LiveOnlyListsTest(unittest.TestCase):
    def test_lists_show_only_200_tested(self):
        from nimlab import store
        from tests.helpers import fresh_store
        with fresh_store():
            store.apply_results({"a/live": {"status": "LIVE_200", "url": "https://x/v1/chat/completions"},
                                 "b/dead": {"status": "NO_WORKING_REST_ENDPOINT"},
                                 "c/auth": {"status": "AUTH_OR_ENTITLEMENT"}})
            self.assertEqual(pg.live_models(), ["a/live"])

    def test_sweep_still_probes_every_known_model(self):
        from tests.helpers import fresh_store
        with fresh_store():
            with mock.patch.object(pg, "MODELS", ["a/live"]), \
                    mock.patch.object(pg, "ALL_MODELS", ["a/live", "b/new", "c/untested"]):
                ids = pg.sweep_model_list()
            for m in ("a/live", "b/new", "c/untested"):  # plus the registry's seeded models
                self.assertIn(m, ids)

    def test_benchmark_has_no_untested_fallback(self):
        import nvidia_benchmark_suite as b
        with mock.patch.object(b, "load_live_fleet", return_value={}):
            e, v, r, o = b.partition_fleet(with_others=True)
        self.assertEqual((e, v, r, o), ([], [], [], []))


if __name__ == "__main__":
    unittest.main()
