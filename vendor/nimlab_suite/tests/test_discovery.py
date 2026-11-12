"""Offline tests for discovery (catalog), spec extraction and the spec sweep.

Fixtures in tests/fixtures are real pages saved from build.nvidia.com,
docs.api.nvidia.com and the NGC catalog search API on 2026-11-11.
"""

import gzip
import json
import os
import tempfile
import unittest

from nimlab import catalog, spec, sweep
from nimlab.core import HttpClient
from nimlab.scrape import PoliteFetcher

from tests.fakes import FakeOpener, FakeResponse, http_error, timeout_error

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    path = os.path.join(FIX, name)
    if name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def page(name):
    return spec.extract_build_page(fixture(f"build_{name}.html.gz"))


class SlugTests(unittest.TestCase):
    def test_slug_to_api_id(self):
        self.assertEqual(spec.slug_to_api_id("moonshotai", "kimi-k3_1-pro"), "moonshotai/kimi-k3.1-pro")
        self.assertEqual(spec.slug_to_api_id(None, "black-forest-labs/flux_1-schnell"),
                         "black-forest-labs/flux.1-schnell")
        self.assertEqual(spec.slug_to_api_id("NVIDIA", "parakeet-ctc-1_1b-asr"), "nvidia/parakeet-ctc-1.1b-asr")

    def test_api_id_to_slug_round_trip(self):
        self.assertEqual(spec.api_id_to_slug("moonshotai/kimi-k3.1-pro"), ("moonshotai", "kimi-k3_1-pro"))
        for mid in ("moonshotai/kimi-k3.1-pro", "meta/llama-3.3-70b-instruct", "nvidia/nemotron-3-embed-1b"):
            pub, slug = spec.api_id_to_slug(mid)
            self.assertEqual(spec.slug_to_api_id(pub, slug), mid)

    def test_slug_candidates_and_docs_slug(self):
        pub, slugs = spec.slug_candidates("z-ai/glm-5.3-flash")
        self.assertEqual(pub, "z-ai")
        self.assertEqual(slugs[0], "glm-5_3-flash")
        self.assertIn("glm-5-3-flash", slugs)  # the site really uses this one
        self.assertEqual(spec.docs_reference_slug("moonshotai/kimi-k3.1-pro"), "moonshotai-kimi-k3_1-pro")

    def test_match_key_ignores_separators(self):
        self.assertEqual(spec.match_key("z-ai/glm-5.3-flash"), spec.match_key("Z-AI/glm-5-3-flash"))
        self.assertEqual(spec.match_key("z-ai/glm-5_3-flash"), spec.match_key("z-ai/glm-5.3-flash"))
        self.assertNotEqual(spec.match_key("meta/llama-3.1-8b"), spec.match_key("meta/llama-3.1-70b"))


class SpecExtractionTests(unittest.TestCase):
    def test_chat_page_full_spec(self):
        info = page("moonshotai_kimi-k3_1-pro")
        self.assertTrue(info["found"])
        self.assertEqual(info["openapi"]["servers"][0]["url"], "https://integrate.api.nvidia.com/v1")
        self.assertIn("/chat/completions", info["openapi"]["paths"])
        self.assertEqual(spec.model_id_from_spec(info["openapi"]), "moonshotai/kimi-k3.1-pro")
        self.assertEqual(info["api_docs_url"], "https://docs.api.nvidia.com/nim/reference/moonshotai-kimi-k3_1-pro")
        self.assertIsNone(info["deprecation"])
        plans, notes = spec.derive_plans(info)
        self.assertEqual(plans[0]["url"], "https://integrate.api.nvidia.com/v1/chat/completions")
        body = plans[0]["body"]
        self.assertEqual(body["model"], "moonshotai/kimi-k3.1-pro")
        self.assertEqual(body["messages"], [{"role": "user", "content": "Hi"}])
        self.assertEqual(body["max_tokens"], 8)
        self.assertFalse(body["stream"])

    def test_dotted_id_from_dashed_slug(self):
        info = page("z-ai_glm-5-3-flash")
        self.assertEqual(spec.model_id_from_spec(info["openapi"]), "z-ai/glm-5.3-flash")

    def test_deprecation_notice(self):
        info = page("01-ai_yi-large")
        self.assertTrue(info["found"])
        self.assertEqual(info["deprecation"]["support_ends"], "2025-07-24")
        self.assertTrue(sweep._is_retired({"deprecation": info["deprecation"]}, today="2026-11-11"))
        self.assertFalse(sweep._is_retired({"deprecation": info["deprecation"]}, today="2025-07-01"))

    def test_ai_api_cv_route_and_nvcf_fallback(self):
        info = page("baidu_paddleocr")
        plans, _ = spec.derive_plans(info, "baidu/paddleocr")
        self.assertEqual(plans[0]["url"], "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr")
        self.assertEqual(plans[0]["kind"], "ocr")
        self.assertTrue(plans[1]["url"].startswith(spec.NVCF_PEXEC))
        self.assertEqual(plans[1]["transport"], "nvcf_http")
        content = plans[0]["body"]["messages"][0]["content"][0]
        self.assertEqual(content["type"], "image_url")
        self.assertTrue(content["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_genai_route(self):
        info = page("black-forest-labs_flux_1-schnell")
        plans, _ = spec.derive_plans(info)
        self.assertEqual(plans[0]["url"], "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell")
        self.assertEqual(plans[0]["kind"], "image_gen")
        self.assertIn("prompt", plans[0]["body"])

    def test_embedding_route(self):
        plans, _ = spec.derive_plans(page("nvidia_nemotron-3-embed-1b"))
        self.assertEqual(plans[0]["url"], "https://integrate.api.nvidia.com/v1/embeddings")
        self.assertEqual(plans[0]["body"]["input_type"], "query")
        self.assertEqual(plans[0]["body"]["model"], "nvidia/nemotron-3-embed-1b")

    def test_magpie_nvcf_http_from_usage(self):
        info = page("nvidia_magpie-tts-multilingual")
        self.assertIsNone(info["openapi"])
        self.assertEqual(info["function_id"], "877104f7-e885-42b9-8de8-f6e4c6303969")
        self.assertIn("/v1/audio/synthesize", info["nvcf_http_paths"])
        plans, notes = spec.derive_plans(info, "nvidia/magpie-tts-multilingual")
        self.assertEqual(plans[0]["url"],
                         "https://877104f7-e885-42b9-8de8-f6e4c6303969.invocation.api.nvcf.nvidia.com/v1/audio/synthesize")
        self.assertEqual(plans[0]["content_type"], "multipart/form-data")
        self.assertEqual(plans[0]["kind"], "tts")
        self.assertTrue(plans[0]["probe_get"].endswith("/v1/audio/list_voices"))

    def test_asr_nvcf_http(self):
        plans, _ = spec.derive_plans(page("nvidia_parakeet-ctc-1_1b-asr"))
        self.assertEqual(plans[0]["kind"], "asr")
        self.assertTrue(plans[0]["url"].endswith("/v1/audio/transcriptions"))

    def test_grpc_only(self):
        info = page("nvidia_body-pose")
        plans, notes = spec.derive_plans(info)
        self.assertEqual(plans, [])
        self.assertTrue(notes.get("grpc_only"))

    def test_not_found_page(self):
        info = page("not_found")
        self.assertFalse(info["found"])
        self.assertTrue(info["not_found"])

    def test_missing_pieces_never_raise(self):
        for html in ("", "<html></html>", '<script>self.__next_f.push([1,"{\\"spec\\":{broken"])</script>',
                     '<script>self.__next_f.push([1,"\\"spec\\":{\\"artifactName\\":\\"x\\"}"])</script>'):
            info = spec.extract_build_page(html)
            plans, notes = spec.derive_plans(info)
            self.assertEqual(plans, [])

    def test_docs_page_and_sidebar(self):
        html = fixture("docs_moonshotai-kimi-k3_1-pro.html.gz")
        docs = catalog.parse_docs_sidebar(html)
        self.assertGreater(len(docs), 100)
        kimi = next(d for d in docs if d["id"] == "moonshotai/kimi-k3.1-pro")
        self.assertEqual(kimi["docs_slug"], "moonshotai-kimi-k3_1-pro")
        self.assertEqual(kimi["infer_slug"], "moonshotai-kimi-k3_1-pro-infer")
        self.assertTrue(all(" " not in d["id"] for d in docs))
        self.assertFalse(spec.extract_docs_page("<html>no props</html>")["found"])

    def test_normalize_server(self):
        self.assertEqual(spec.normalize_server("climate.api.nvidia.com/v1"), "https://climate.api.nvidia.com/v1")
        self.assertIsNone(spec.normalize_server("http://localhost:8000"))
        self.assertIsNone(spec.normalize_server("https://evil.example.com/v1"))
        self.assertEqual(spec.normalize_server("https://integrate.api.nvidia.com/v1"), spec.INTEGRATE)

    def test_error_hint_redacts_keys(self):
        hint = spec.error_hint(json.dumps({"detail": "bad key nvapi-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"}))
        self.assertNotIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ123456", hint)

    def test_tiny_png_is_valid(self):
        import base64
        import zlib
        raw = base64.b64decode(spec.TINY_PNG_DATA_URI.split(",", 1)[1])
        self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertIn(b"IEND", raw)
        self.assertGreater(len(zlib.compress(raw)), 0)


class NgcSpecTests(unittest.TestCase):
    def ngc(self, slug):
        return spec.extract_ngc_spec(fixture(f"ngcspec_{slug}.json.gz"))

    def test_chat(self):
        info = self.ngc("kimi-k3_1-pro")
        self.assertEqual(info["inference_path"], "/v1/chat/completions")
        plans, _ = spec.derive_plans(info)
        self.assertEqual(plans[0]["url"], "https://integrate.api.nvidia.com/v1/chat/completions")
        self.assertEqual(plans[0]["model"], "moonshotai/kimi-k3.1-pro")

    def test_grpc_flag_from_inference_path(self):
        info = self.ngc("body-pose")
        self.assertTrue(info["grpc"])
        self.assertTrue(spec.derive_plans(info)[1].get("grpc_only"))

    def test_speech_http_over_grpc_function(self):
        plans, notes = spec.derive_plans(self.ngc("magpie-tts-multilingual"))
        self.assertTrue(plans[0]["url"].endswith(".invocation.api.nvcf.nvidia.com/v1/audio/synthesize"))
        self.assertFalse(notes.get("grpc_only"))

    def test_cv_and_deprecation_and_not_found(self):
        plans, _ = spec.derive_plans(self.ngc("paddleocr"), "baidu/paddleocr")
        self.assertEqual(plans[0]["url"], "https://ai.api.nvidia.com/v1/cv/baidu/paddleocr")
        self.assertEqual(self.ngc("yi-large")["deprecation"]["support_ends"], "2025-07-24")
        nf = self.ngc("does-not-exist-xyz")
        self.assertTrue(nf["not_found"])
        self.assertFalse(nf["found"])

    def test_bad_input(self):
        for body in (None, "", "not json", "[]", {"requestStatus": {}}, {"artifactName": "x", "openAPISpec": "{bad"}):
            info = spec.extract_ngc_spec(body)
            self.assertEqual(spec.derive_plans(info)[0], [])


class CatalogParseTests(unittest.TestCase):
    def test_search_params_from_models_page(self):
        params = catalog.search_params_from_models_page(fixture("build_models_page.html.gz"))
        self.assertIsNotNone(params)
        fields = {f["field"]: f["value"] for f in params["filters"]}
        self.assertEqual(fields.get("orgName"), catalog.SITE_ORG)
        self.assertEqual(fields.get("resourceType"), "endpoint")
        self.assertEqual(params["pageSize"], 100)
        self.assertIn("%22orgName%22", catalog.search_url(params, 1))

    def test_parse_search_page_skips_scored_group(self):
        body = json.loads(fixture("ngc_search_page1.json"))
        res, pages, total = catalog.parse_search_page(body)
        self.assertGreater(len(res), 0)
        self.assertGreater(total, 100)
        dup = {"results": [{"groupValue": "ENDPOINT", "resources": [{"resourceId": "a"}]},
                           {"groupValue": "_scored", "resources": [{"resourceId": "a"}]}]}
        self.assertEqual(len(catalog.parse_search_page(dup)[0]), 1)
        self.assertEqual(catalog.parse_search_page(None), ([], 0, 0))

    def test_site_entry_fields(self):
        body = json.loads(fixture("ngc_search_page1.json"))
        res, _, _ = catalog.parse_search_page(body)
        entries = [catalog.site_entry(r) for r in res]
        entries = [e for e in entries if e]
        self.assertTrue(all("/" in e["id"] and e["page_url"].startswith("https://build.nvidia.com/") for e in entries))
        rec = {"resourceId": "qc69jvmznzxy/kimi-k3_1-pro", "name": "kimi-k3_1-pro", "displayName": "kimi-k3.1-pro",
               "labels": [{"key": "publisher", "values": ["moonshotai"]},
                          {"key": "general", "values": ["Free Endpoint", "Multimodal"],
                           "unresolvedValues": ["playgroundtype_chat"]}],
               "attributes": [{"key": "DEPRECATION", "value": "12/1/2026"}]}
        e = catalog.site_entry(rec)
        self.assertEqual(e["id"], "moonshotai/kimi-k3.1-pro")
        self.assertEqual(e["playground_type"], "chat")
        self.assertEqual(e["deprecation_date"], "2026-12-01")
        self.assertTrue(e["free_endpoint"])
        self.assertIsNone(catalog.site_entry({"name": "test-endpoint-foo", "labels": []}))

    def test_sitemap(self):
        pairs = catalog.parse_sitemap(fixture("build_sitemap.xml.gz"))
        self.assertIn(("moonshotai", "kimi-k3_1-pro"), pairs)
        self.assertFalse(any(p in catalog.NON_MODEL_SEGMENTS for p, _ in pairs))

    def test_docs_sitemap_fallback(self):
        xml = ("<urlset><url><loc>https://docs.api.nvidia.com/nim/reference/meta-llama-3_3-70b-instruct-infer</loc></url>"
               "<url><loc>https://docs.api.nvidia.com/nim/reference/meta-llama-3_3-70b-instruct</loc></url></urlset>")
        self.assertEqual(catalog.parse_docs_sitemap(xml), ["meta-llama-3_3-70b-instruct"])

    def test_classify_kind(self):
        self.assertEqual(catalog.classify_kind("nvidia/magpie-tts-multilingual"), "tts")
        self.assertEqual(catalog.classify_kind("nvidia/parakeet-ctc-1.1b-asr"), "asr")
        self.assertEqual(catalog.classify_kind("nvidia/nemotron-3-embed-1b"), "embedding")
        self.assertEqual(catalog.classify_kind("nvidia/llama-nemotron-rerank-vl-1b-v2"), "rerank")
        self.assertEqual(catalog.classify_kind("baidu/paddleocr"), "ocr")
        self.assertEqual(catalog.classify_kind("black-forest-labs/flux.1-schnell"), "image_gen")
        self.assertEqual(catalog.classify_kind("meta/llama-3.2-90b-vision-instruct"), "vision")
        self.assertEqual(catalog.classify_kind("vendor/new-model", ["Multimodal"]), "vision")
        self.assertEqual(catalog.classify_kind("vendor/new-model", ["Chat"], playground_type="chat"), "chat")
        self.assertEqual(catalog.classify_kind("vendor/x", docs_category="Retrieval"), "embedding")
        self.assertEqual(catalog.classify_kind("moonshotai/kimi-k3.1-pro"), "chat")


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.site = [
            {"id": "moonshotai/kimi-k3.1-pro", "publisher": "moonshotai", "slug": "kimi-k3_1-pro",
             "page_url": "https://build.nvidia.com/moonshotai/kimi-k3_1-pro", "labels": ["Chat"],
             "playground_type": "chat"},
            {"id": "z-ai/glm-5-3-flash", "publisher": "z-ai", "slug": "glm-5-3-flash",
             "page_url": "https://build.nvidia.com/z-ai/glm-5-3-flash"},
            {"id": "google/diffusiongemma-26b-a4b-it", "publisher": "google", "slug": "diffusiongemma-26b-a4b-it",
             "page_url": "https://build.nvidia.com/google/diffusiongemma-26b-a4b-it",
             "deprecation_date": "2026-12-01"},
            {"id": "meta/old-model", "publisher": "meta", "slug": "old-model", "page_url": "x",
             "deprecation_date": "2026-01-05"},
        ]
        self.docs = [{"id": "z-ai/glm-5.3-flash", "docs_slug": "z-ai-glm-5_3-flash",
                      "infer_slug": "z-ai-glm-5_3-flash-infer", "category": "Large Language Models",
                      "deprecated": False, "hidden": False},
                     {"id": "nvidia/nv-embedqa-e5-v5", "docs_slug": "nvidia-nv-embedqa-e5-v5",
                      "infer_slug": "nvidia-nv-embedqa-e5-v5-infer", "category": "Retrieval",
                      "deprecated": False, "hidden": False}]
        self.key = ["moonshotai/kimi-k3.1-pro", "01-ai/yi-large", "nvidia/nv-embedqa-e5-v5"]

    def test_merge_sources_and_flags(self):
        cat = catalog.merge(self.site, [("z-ai", "glm-5-3-flash")], self.docs, None, self.key, "key",
                            today="2026-11-11")
        by_id = {e["id"]: e for e in cat.values()}
        glm = by_id["z-ai/glm-5.3-flash"]  # docs keeps the dots the slug lost
        self.assertEqual(sorted(glm["sources"]), ["docs", "site", "sitemap"])
        self.assertIn("on_site_not_in_key", glm["flags"])
        self.assertEqual(glm["docs_infer_url"], catalog.DOCS_REF + "z-ai-glm-5_3-flash-infer")
        kimi = by_id["moonshotai/kimi-k3.1-pro"]
        self.assertEqual(sorted(kimi["sources"]), ["key", "site"])
        self.assertEqual(kimi["flags"], [])
        yi = by_id["01-ai/yi-large"]
        self.assertEqual(yi["status"], "unlisted")
        self.assertIn("in_key_not_on_site", yi["flags"])
        self.assertEqual(yi["page_url_guess"], "https://build.nvidia.com/01-ai/yi-large")
        self.assertEqual(by_id["google/diffusiongemma-26b-a4b-it"]["status"], "deprecated")
        self.assertEqual(by_id["meta/old-model"]["status"], "retired")
        self.assertEqual(by_id["nvidia/nv-embedqa-e5-v5"]["kind"], "embedding")
        s = catalog.summarize(cat)
        self.assertEqual(s["total"], 6)
        self.assertEqual(s["on_site"], 4)
        self.assertEqual(s["in_key_list"], 3)
        self.assertEqual(s["retired"], 1)

    def test_key_id_wins(self):
        cat = catalog.merge([{"id": "z-ai/glm-5-3-flash", "publisher": "z-ai", "slug": "glm-5-3-flash"}], [],
                            [], None, ["z-ai/glm-5.3-flash"], "key")
        self.assertEqual([e["id"] for e in cat.values()], ["z-ai/glm-5.3-flash"])

    def test_without_key_list_no_key_flags(self):
        cat = catalog.merge(self.site, [], self.docs, None, None)
        self.assertFalse(any("on_site_not_in_key" in e["flags"] for e in cat.values()))
        self.assertTrue(all("in_key_list" not in e for e in cat.values()))

    def test_sitemap_only_when_search_failed(self):
        cat = catalog.merge([], [("moonshotai", "kimi-k3_1-pro")], [], None, None)
        e = list(cat.values())[0]
        self.assertEqual(e["id"], "moonshotai/kimi-k3.1-pro")
        self.assertEqual(e["status"], "active")

    def test_model_ids_filters(self):
        cat = catalog.merge(self.site, [], self.docs, None, self.key, "key", today="2026-11-11")
        doc = {"models": {e["id"]: e for e in cat.values()}}
        ids = catalog.model_ids(doc)
        self.assertNotIn("meta/old-model", ids)
        self.assertIn("meta/old-model", catalog.model_ids(doc, include_retired=True))
        self.assertEqual(catalog.model_ids(doc, kinds=["embedding"]), ["nvidia/nv-embedqa-e5-v5"])
        self.assertEqual(catalog.kind_of("z-ai/glm-5-3-flash", doc), "chat")


class FetcherTests(unittest.TestCase):
    def test_cache_ttl_and_pacing(self):
        with tempfile.TemporaryDirectory() as d:
            opener = FakeOpener([FakeResponse("<html>a</html>", headers={"Content-Type": "text/html"}),
                                 FakeResponse("<html>b</html>", headers={"Content-Type": "text/html"})])
            sleeps, now = [], [100.0]
            f = PoliteFetcher(http=HttpClient(opener=opener, retries=0), cache_dir=d, ttl_sec=3600,
                              sleep=lambda s: sleeps.append(s), clock=lambda: now[0])
            r1 = f.get("https://build.nvidia.com/a/b")
            r2 = f.get("https://build.nvidia.com/a/b")  # served from cache
            self.assertEqual(r1.text, "<html>a</html>")
            self.assertTrue(r2.from_cache)
            f.get("https://build.nvidia.com/a/c", store=False)
            self.assertEqual(len(opener.requests), 2)
            self.assertAlmostEqual(sleeps[0], 10.0)  # build.nvidia.com crawl delay
            self.assertIn("Mozilla", opener.header(0, "User-Agent"))
            self.assertIsNone(opener.header(0, "Authorization"))
            self.assertEqual(len(os.listdir(d)), 1)  # store=False was not cached

    def test_stale_cache_used_when_fetch_fails(self):
        with tempfile.TemporaryDirectory() as d:
            opener = FakeOpener([FakeResponse("old"), http_error(503), http_error(503)])
            f = PoliteFetcher(http=HttpClient(opener=opener, retries=0), cache_dir=d, ttl_sec=0,
                              sleep=lambda s: None)
            f.get("https://api.ngc.nvidia.com/x")
            r = f.get("https://api.ngc.nvidia.com/x")
            self.assertEqual(r.text, "old")
            self.assertTrue(r.from_cache)

    def test_offline_mode(self):
        f = PoliteFetcher(http=HttpClient(opener=FakeOpener([])), cache_dir="", offline=True)
        self.assertFalse(f.get("https://build.nvidia.com/x/y").ok)


class ClassifyTests(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(sweep.classify(200)[0], sweep.LIVE)
        self.assertEqual(sweep.classify(202)[0], sweep.LIVE)
        st, reason = sweep.classify(422, body_text=json.dumps({"detail": "field required: messages"}))
        self.assertEqual(st, sweep.PAYLOAD)
        self.assertIn("messages", reason)
        self.assertEqual(sweep.classify(401)[0], sweep.AUTH)
        self.assertEqual(sweep.classify(403, body_text='{"detail":"Forbidden"}')[0], sweep.AUTH)
        self.assertEqual(sweep.classify(404, body_text='{"detail":"Function not found for account"}')[0],
                         sweep.AUTH)
        self.assertEqual(sweep.classify(404)[0], sweep.RETIRED)
        self.assertEqual(sweep.classify(410)[0], sweep.RETIRED)
        self.assertEqual(sweep.classify(429)[0], sweep.RATE)
        self.assertEqual(sweep.classify(500)[0], sweep.SERVER)
        self.assertEqual(sweep.classify(None, "timeout")[0], sweep.SERVER)

    def test_best_outcome(self):
        o = sweep.best_outcome([{"status": sweep.RETIRED}, {"status": sweep.PAYLOAD}, {"status": sweep.AUTH}])
        self.assertEqual(o["status"], sweep.PAYLOAD)
        self.assertIsNone(sweep.best_outcome([]))


KEY = "nvapi-TESTKEY0000000000000000000000000000000000000000000000000000"


class ProbeTests(unittest.TestCase):
    """The authenticated probes, with a mocked HTTP layer (no live key)."""

    def plan_doc(self, name, model_id):
        info = page(name)
        plans, notes = spec.derive_plans(info, model_id)
        return {"model_id": model_id, "plans": plans, "notes": notes, "deprecation": info["deprecation"],
                "page_url": "https://build.nvidia.com/x", "spec_source": "page", "function_id": info["function_id"]}

    def prober(self, script):
        opener = FakeOpener(script)
        return sweep.Prober(api_key=KEY, http=HttpClient(opener=opener, retries=0, sleep=lambda s: None)), opener

    def test_live_chat_probe_uses_spec_request(self):
        prober, opener = self.prober([FakeResponse({"choices": [{"message": {"content": "Hi"}}]})])
        e = sweep.evaluate(self.plan_doc("moonshotai_kimi-k3_1-pro", "moonshotai/kimi-k3.1-pro"), prober)
        self.assertEqual(e["status"], sweep.LIVE)
        self.assertEqual(e["url"], "https://integrate.api.nvidia.com/v1/chat/completions")
        self.assertEqual(opener.body(0)["model"], "moonshotai/kimi-k3.1-pro")
        self.assertEqual(opener.header(0, "Authorization"), "Bearer " + KEY)
        self.assertNotIn(KEY, json.dumps(e))

    def test_payload_rejection_retries_with_page_example(self):
        doc = self.plan_doc("baidu_paddleocr", "baidu/paddleocr")
        doc["plans"][0]["alt_body"] = {"input": [{"type": "image_url", "url": spec.TINY_PNG_DATA_URI}]}
        prober, opener = self.prober([http_error(422, b'{"detail":"bad messages"}'), FakeResponse({"data": []})])
        e = sweep.evaluate(doc, prober)
        self.assertEqual(e["status"], sweep.LIVE)
        self.assertEqual(e["payload_used"], "example")
        self.assertIn("input", opener.body(1))

    def test_entitlement(self):
        prober, _ = self.prober([http_error(403, b'{"detail":"Forbidden"}'), http_error(403)])
        e = sweep.evaluate(self.plan_doc("baidu_paddleocr", "baidu/paddleocr"), prober)
        self.assertEqual(e["status"], sweep.AUTH)

    def test_retired_from_page_notice(self):
        prober, _ = self.prober([http_error(404, b'{"detail":"Not found"}')])
        e = sweep.evaluate(self.plan_doc("01-ai_yi-large", "01-ai/yi-large"), prober, today="2026-11-11")
        self.assertEqual(e["status"], sweep.RETIRED)
        self.assertEqual(e["deprecation"]["support_ends"], "2025-07-24")

    def test_magpie_multipart_with_function_id(self):
        prober, opener = self.prober([FakeResponse(b"RIFF....", headers={"Content-Type": "audio/wav"})])
        e = sweep.evaluate(self.plan_doc("nvidia_magpie-tts-multilingual", "nvidia/magpie-tts-multilingual"), prober)
        self.assertEqual(e["status"], sweep.LIVE)
        self.assertEqual(e["kind"], "audio_tts")
        self.assertIn("multipart/form-data", opener.header(0, "Content-Type"))
        self.assertEqual(opener.header(0, "function-id"), "877104f7-e885-42b9-8de8-f6e4c6303969")
        self.assertIn(b'name="voice"', opener.requests[0]["data"])

    def test_grpc_only_not_probed(self):
        prober, opener = self.prober([])
        e = sweep.evaluate(self.plan_doc("nvidia_body-pose", "nvidia/body-pose"), prober)
        self.assertEqual(e["status"], sweep.GRPC)
        self.assertEqual(opener.requests, [])

    def test_timeout(self):
        prober, _ = self.prober([timeout_error()])
        e = sweep.evaluate(self.plan_doc("nvidia_nemotron-3-embed-1b", "nvidia/nemotron-3-embed-1b"), prober)
        self.assertEqual(e["status"], sweep.SERVER)

    def test_no_spec_falls_back_to_guess_and_marks_retired(self):
        doc = {"model_id": "adept/fuyu-8b", "plans": [], "notes": {}, "page_status": 404,
               "catalog_kind": "vision", "catalog_status": "unlisted"}
        router = sweep.NvidiaRouter(registry={"gateways": {"integrate": spec.INTEGRATE, "ai_api": spec.AI_API}})
        opener = FakeOpener([http_error(404), http_error(404), http_error(404)])
        prober = sweep.Prober(api_key=KEY, http=HttpClient(opener=opener, retries=0), router=router)
        e = sweep.evaluate(doc, prober)
        self.assertEqual(e["status"], sweep.RETIRED)
        self.assertGreaterEqual(len(opener.requests), 1)

    def test_plan_only_marks_retired_from_notice(self):
        e = sweep.evaluate(self.plan_doc("01-ai_yi-large", "01-ai/yi-large"), None, probe=False, today="2026-11-11")
        self.assertEqual(e["status"], sweep.RETIRED)
        self.assertIn("2025-07-24", e["reason"])

    def test_live_past_end_date_stays_live(self):
        prober, _ = self.prober([FakeResponse({"choices": []})])
        e = sweep.evaluate(self.plan_doc("01-ai_yi-large", "01-ai/yi-large"), prober, today="2026-11-11")
        self.assertEqual(e["status"], sweep.LIVE)
        self.assertIn("announced end", e["reason"])

    def test_no_key_is_plan_only(self):
        e = sweep.evaluate(self.plan_doc("moonshotai_kimi-k3_1-pro", "moonshotai/kimi-k3.1-pro"),
                           sweep.Prober(api_key=""), probe=True)
        self.assertEqual(e["status"], sweep.PLANNED)


class ResolverAndWriteTests(unittest.TestCase):
    def test_resolver_prefers_ngc_spec(self):
        body = fixture("ngcspec_kimi-k3_1-pro.json.gz")
        opener = FakeOpener([FakeResponse(body, headers={"Content-Type": "application/json"})])
        f = PoliteFetcher(http=HttpClient(opener=opener, retries=0), cache_dir="", sleep=lambda s: None)
        cat = {"models": {"moonshotai/kimi-k3.1-pro": {"id": "moonshotai/kimi-k3.1-pro", "slug": "kimi-k3_1-pro"}}}
        doc = sweep.SpecResolver(f, cat, cache_dir="").resolve("moonshotai/kimi-k3.1-pro")
        self.assertEqual(doc["spec_via"], "ngc_spec")
        self.assertEqual(opener.requests[0]["url"],
                         "https://api.ngc.nvidia.com/v2/endpoints/qc69jvmznzxy/kimi-k3_1-pro/spec")
        self.assertEqual(len(opener.requests), 1)

    def test_resolver_uses_page_then_caches_spec(self):
        html = fixture("build_moonshotai_kimi-k3_1-pro.html.gz")
        with tempfile.TemporaryDirectory() as d:
            # spec API down (503), so the page HTML is read instead
            opener = FakeOpener([http_error(503), FakeResponse(html, headers={"Content-Type": "text/html"})])
            f = PoliteFetcher(http=HttpClient(opener=opener, retries=0), cache_dir="", sleep=lambda s: None)
            cat = {"models": {"moonshotai/kimi-k3.1-pro": {"id": "moonshotai/kimi-k3.1-pro", "kind": "chat",
                                                           "slug": "kimi-k3_1-pro", "page_url": "https://build.nvidia.com/moonshotai/kimi-k3_1-pro"}}}
            r = sweep.SpecResolver(f, cat, cache_dir=d)
            doc = r.resolve("moonshotai/kimi-k3.1-pro")
            self.assertEqual(doc["spec_source"], "page")
            self.assertEqual(doc["spec_via"], "page_html")
            self.assertEqual(doc["api_model_id"], "moonshotai/kimi-k3.1-pro")
            again = r.resolve("moonshotai/kimi-k3.1-pro")  # from the spec cache, no request
            self.assertEqual(again["plans"][0]["url"], doc["plans"][0]["url"])
            self.assertEqual(len(opener.requests), 2)
            with open(os.path.join(d, os.listdir(d)[0]), encoding="utf-8") as fh:
                cached = fh.read()
            self.assertNotIn("self.__next_f", cached)  # raw HTML is not kept

    def test_resolver_falls_back_to_docs(self):
        docs_html = '<script id="ssr-props" type="application/x-ssr-props">' + json.dumps({"document": {"api": {"schema": {
            "servers": [{"url": "https://integrate.api.nvidia.com/v1"}],
            "paths": {"/chat/completions": {"post": {"requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "required": ["model", "messages"],
                "properties": {"model": {"type": "string", "default": "acme/old-1.0"},
                               "messages": {"type": "array"}}}}}}}}}}}}}) + "</script>"
        # both NGC spec slugs 404 -> page HTML skipped -> docs reference
        opener = FakeOpener([http_error(404), http_error(404), FakeResponse(docs_html, headers={"Content-Type": "text/html"})])
        f = PoliteFetcher(http=HttpClient(opener=opener, retries=0), cache_dir="", sleep=lambda s: None)
        doc = sweep.SpecResolver(f, None, cache_dir="").resolve("acme/old-1.0")
        self.assertEqual(doc["spec_source"], "docs")
        self.assertEqual(doc["plans"][0]["body"]["model"], "acme/old-1.0")
        self.assertIn("docs.api.nvidia.com/nim/reference/acme-old-1_0-infer", opener.requests[2]["url"])

    def test_write_results_updates_verified_and_router(self):
        from nimlab import store
        from tests.helpers import fresh_store
        with fresh_store():
            ver = store.load(store.VERIFIED)
            ver["models"]["meta/keep"] = {"status": "LIVE_200", "url": "u", "verified_at": "2026-01-01T00:00:00"}
            store.save(store.VERIFIED, ver)
            results = {
                "nvidia/magpie-tts-multilingual": {"status": sweep.LIVE, "route_source": "page", "method": "POST",
                                                   "url": "https://f.invocation.api.nvcf.nvidia.com/v1/audio/synthesize",
                                                   "kind": "audio_tts", "function_id": "f",
                                                   "content_type": "multipart/form-data"},
                "meta/keep": {"status": sweep.PLANNED},
                "01-ai/yi-large": {"status": sweep.RETIRED},
            }
            st = sweep.write_results(results)
            v = store.verified_models()
            self.assertEqual(v["meta/keep"]["status"], "LIVE_200")  # not dropped by a plan-only entry
            self.assertIn("nvidia/magpie-tts-multilingual", v)
            self.assertNotIn("01-ai/yi-large", v)
            self.assertEqual(store.probe_results()["01-ai/yi-large"]["status"], sweep.RETIRED)
            self.assertEqual(st["overrides"], 1)
            router = sweep.NvidiaRouter()
            route = router.resolve("nvidia/magpie-tts-multilingual", "tts")
            self.assertEqual(route["url"], "https://f.invocation.api.nvcf.nvidia.com/v1/audio/synthesize")
            self.assertEqual(route["function_id"], "f")

    def test_write_results_keys_by_api_id(self):
        from nimlab import store
        from tests.helpers import fresh_store
        with fresh_store():
            res = {"z-ai/glm-5-3-flash": {"status": sweep.LIVE, "api_model_id": "z-ai/glm-5.3-flash",
                                           "url": spec.INTEGRATE + "/chat/completions", "kind": "chat",
                                           "route_source": "page"}}
            sweep.write_results(res)
            v = store.verified_models()
            self.assertEqual(list(v), ["z-ai/glm-5.3-flash"])
            self.assertEqual(v["z-ai/glm-5.3-flash"]["catalog_id"], "z-ai/glm-5-3-flash")

    def test_fleet_types_use_catalog_kind(self):
        from nimlab.router import model_types
        self.assertEqual(model_types("nvidia/nemotron-3-content-safety", "chat", "safety"), set())
        self.assertEqual(model_types("baidu/paddleocr", "document", "ocr"), {"ocr"})
        self.assertIn("chat", model_types("moonshotai/kimi-k3.1-pro", "vision", "chat"))


if __name__ == "__main__":
    unittest.main()
