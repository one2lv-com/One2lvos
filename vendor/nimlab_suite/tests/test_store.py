"""Data stores (nimlab.store): fresh start, migration, sync rules, picker."""

import io
import json
import os
import unittest
from unittest import mock

from nimlab import config, picker, store
from tests.helpers import fresh_store

CHAT = "https://integrate.api.nvidia.com/v1/chat/completions"
NEW_URL = "https://ai.api.nvidia.com/v1/genai/acme/brand-new-model"


def live(url=CHAT, **kw):
    return dict({"status": store.LIVE, "url": url, "method": "POST", "kind": "chat", "latency_sec": 0.5,
                 "http_status": 200, "checked_at": "2026-11-11T10:00:00"}, **kw)


def failed(status="NO_WORKING_REST_ENDPOINT", **kw):
    return dict({"status": status, "reason": "404 on every route", "checked_at": "2026-11-11T11:00:00"}, **kw)


class FreshStartTest(unittest.TestCase):
    def test_missing_files_are_created_with_valid_structure(self):
        with fresh_store():
            store.ensure_all()
            for name in store.DEFAULTS:
                p = store.path(name)
                self.assertTrue(os.path.exists(p), name)
                with open(p, encoding="utf-8") as f:
                    json.load(f)
            self.assertTrue(os.path.exists(store.path(store.TEST_HISTORY)))
            eps = store.load(store.ENDPOINTS)
            self.assertIn("gateways", eps["routing"])  # router works on a fresh unzip
            self.assertIn(store.endpoint_key(CHAT), eps["endpoints"])
            self.assertEqual(store.verified_ids(), [])
            self.assertIsNone(store.discovered())

    def test_store_deleted_mid_run_is_recreated(self):
        with fresh_store():
            store.ensure_all()
            os.remove(store.path(store.VERIFIED))
            self.assertEqual(store.load(store.VERIFIED)["models"], {})
            self.assertTrue(os.path.exists(store.path(store.VERIFIED)))

    def test_corrupt_store_is_moved_aside_not_lost(self):
        with fresh_store():
            store.ensure_all()
            with open(store.path(store.PROBES), "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertEqual(store.load(store.PROBES)["models"], {})
            corrupt = os.path.join(store.data_dir(), "legacy", "corrupt")
            self.assertEqual(len(os.listdir(corrupt)), 1)

    def test_missing_keys_are_filled(self):
        with fresh_store():
            store.ensure_all()
            with open(store.path(store.VERIFIED), "w", encoding="utf-8") as f:
                f.write('{"models": {}}')
            self.assertEqual(store.load(store.VERIFIED)["dropped"], {})

    def test_config_files_created_when_missing(self):
        with fresh_store() as root:
            cl, sp = os.path.join(root, "config_cluster.json"), os.path.join(root, "config_system_prompts.json")
            with mock.patch.object(config, "CLUSTER_CONFIG", cl), mock.patch.object(config, "SYSTEM_PROMPTS", sp):
                config.ensure_config_files()
                self.assertIn("roles", config.load_json(cl, {}))
                self.assertTrue(config.load_json(sp, None))

    def test_router_and_fleet_work_on_empty_store(self):
        from nimlab.router import NvidiaRouter, load_live_fleet
        with fresh_store():
            self.assertEqual(load_live_fleet(), {})
            route = NvidiaRouter().resolve("meta/llama-3.3-70b-instruct", "chat")
            self.assertEqual(route["url"], CHAT)


class MigrationTest(unittest.TestCase):
    def _write_legacy(self, root):
        os.makedirs(os.path.join(root, "output"), exist_ok=True)

        def put(rel, data):
            with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
                json.dump(data, f)
        reg = json.loads(json.dumps(store.defaults.ROUTING))
        reg["explicit_model_overrides"]["acme/special"] = {"url": NEW_URL, "method": "POST", "kind": "image_gen",
                                                          "source": "spec_sweep"}
        put("nvidia_endpoint_registry.json", reg)
        put("nvidia_endpoints_matrix.json", {"candidate_routes": [
            {"kind": "custom", "url": "https://ai.api.nvidia.com/v1/custom/route", "method": "POST"}]})
        put("nvidia_inventory.json", {"models": ["meta/llama-a", "key/only-model"], "updated_at": "2026-11-10"})
        put("nvidia_catalog.json", {"generated_at": "2026-11-10T00:00:00", "sources": {"site": "ok"},
                                    "models": {"meta/llama-a": {"id": "meta/llama-a", "kind": "chat",
                                                                "sources": ["site", "key"], "status": "active"},
                                               "old/retired-one": {"id": "old/retired-one", "kind": "chat",
                                                                   "sources": ["site"], "status": "retired"}}})
        put("nvidia_verified_endpoints.json", {"meta/llama-a": live(), "broken/model": failed()})
        put("output/benchmark_results.json", {"timestamp": "2026-11-09T12:00:00",
                                              "reasoning": [{"model": "meta/llama-a", "logic_pass": True}]})
        put("output/memory_store.json", [{"id": "m1", "text": "hello"}])
        put("output/leaderboard.json", {"roles": {"core": []}})

    def test_migration_builds_stores_and_backs_up(self):
        with fresh_store() as root:
            self._write_legacy(root)
            store.ensure_all()  # first run migrates automatically
            for n in store.LEGACY_ROOT_FILES:
                self.assertFalse(os.path.exists(os.path.join(root, n)), n)
            backups = [d for d in os.listdir(os.path.join(store.data_dir(), "legacy")) if d[0].isdigit()]
            self.assertEqual(len(backups), 1)
            self.assertTrue(os.path.exists(os.path.join(store.data_dir(), "legacy", backups[0],
                                                        "nvidia_verified_endpoints.json")))
            self.assertEqual(store.verified_ids(), ["meta/llama-a"])
            self.assertEqual(store.probe_results()["broken/model"]["status"], "NO_WORKING_REST_ENDPOINT")
            disc = store.load(store.DISCOVERED)
            self.assertIn("key/only-model", disc["models"])  # key inventory merged
            self.assertEqual(disc["models"]["old/retired-one"]["status"], "retired")
            self.assertEqual(store.key_list(), ["key/only-model", "meta/llama-a"])
            eps = store.load(store.ENDPOINTS)
            self.assertIn("acme/special", eps["routing"]["explicit_model_overrides"])
            self.assertIn(store.endpoint_key(NEW_URL), eps["endpoints"])
            self.assertIn(store.endpoint_key("https://ai.api.nvidia.com/v1/custom/route"), eps["endpoints"])
            self.assertIn("meta/llama-a", eps["endpoints"][store.endpoint_key(CHAT)]["models"])
            self.assertEqual(store.latest_benchmark()["timestamp"], "2026-11-09T12:00:00")
            self.assertEqual(len(store.load(store.BENCH_HISTORY)["runs"]), 1)
            self.assertEqual(store.load(store.MEMORY)[0]["id"], "m1")
            self.assertEqual(store.load(store.LEADERBOARD), {"roles": {"core": []}})

    def test_second_migration_merges_and_loses_nothing(self):
        with fresh_store() as root:
            self._write_legacy(root)
            store.ensure_all()
            store.apply_results({"new/after": live()})  # data gathered after the first migration
            self._write_legacy(root)  # old files come back (e.g. an old zip unpacked over)
            store.reset()
            store.ensure_all()
            self.assertEqual(set(store.verified_ids()), {"meta/llama-a", "new/after"})
            self.assertEqual(len(store.load(store.MEMORY)), 1)  # no duplicate memories


class EndpointRegistryTest(unittest.TestCase):
    def test_new_url_from_sweep_is_added(self):
        with fresh_store():
            st = store.apply_results({"acme/brand-new-model": live(NEW_URL, kind="image_gen", route_source="page",
                                                                   content_type="application/json")})
            rec = store.load(store.ENDPOINTS)["endpoints"][store.endpoint_key(NEW_URL)]
            self.assertEqual(st["endpoints_added"], 1)
            self.assertEqual(rec["models"], ["acme/brand-new-model"])
            self.assertEqual(rec["host"], "ai.api.nvidia.com")
            self.assertIn("spec", rec["sources"])
            self.assertEqual(rec["last_result"]["status"], store.LIVE)
            self.assertEqual(rec["first_seen"], rec["last_seen"])

    def test_known_url_gets_last_seen_updated(self):
        with fresh_store():
            store.apply_results({"a/one": live(NEW_URL)}, at="2026-11-01T00:00:00")
            st = store.apply_results({"b/two": live(NEW_URL)}, at="2026-11-11T00:00:00")
            rec = store.load(store.ENDPOINTS)["endpoints"][store.endpoint_key(NEW_URL)]
            self.assertEqual(st["endpoints_added"], 0)
            self.assertEqual(rec["last_seen"], "2026-11-11T00:00:00")
            self.assertLess(rec["first_seen"], rec["last_seen"])
            self.assertIn("a/one", rec["models"])
            self.assertIn("b/two", rec["models"])

    def test_spec_endpoints_recorded_even_on_plan_only(self):
        with fresh_store():
            plan = {"url": NEW_URL, "method": "POST", "kind": "image_gen"}
            store.apply_results({"acme/m": {"status": "SPEC_FOUND_NOT_PROBED", "spec_plans": [plan]}}, probed=False)
            self.assertIn(store.endpoint_key(NEW_URL), store.load(store.ENDPOINTS)["endpoints"])
            self.assertEqual(store.probe_results(), {})

    def test_guessed_404_url_is_not_added_but_existing_url_records_result(self):
        with fresh_store():
            guess = "https://ai.api.nvidia.com/v1/guess/nope"
            store.apply_results({"x/y": failed(tried=[
                {"url": guess, "method": "POST", "status": "NOT_FOUND", "http_status": 404},
                {"url": CHAT, "method": "POST", "status": "BAD_REQUEST", "http_status": 400}])})
            eps = store.load(store.ENDPOINTS)["endpoints"]
            self.assertNotIn(store.endpoint_key(guess), eps)
            self.assertEqual(eps[store.endpoint_key(CHAT)]["last_result"]["http_status"], 400)

    def test_unused_endpoint_goes_stale_and_comes_back(self):
        with fresh_store():
            store.apply_results({"acme/gone": live(NEW_URL, route_source="page")}, at="2026-11-01T00:00:00")
            # full sweep later; acme/gone is no longer discovered and not swept
            st = store.apply_results({"a/one": live()}, complete=True, known={"a/one"}, at="2026-11-11T00:00:00")
            eps = store.load(store.ENDPOINTS)
            self.assertEqual(st["endpoints_staled"], 1)
            self.assertIn(store.endpoint_key(NEW_URL), eps["stale"])
            self.assertEqual(eps["stale"][store.endpoint_key(NEW_URL)]["former_models"], ["acme/gone"])
            self.assertIn(store.endpoint_key(CHAT), eps["endpoints"])  # seed routes never go stale
            store.apply_results({"acme/gone": live(NEW_URL)}, at="2026-11-12T00:00:00")
            eps = store.load(store.ENDPOINTS)
            self.assertIn(store.endpoint_key(NEW_URL), eps["endpoints"])
            self.assertNotIn(store.endpoint_key(NEW_URL), eps["stale"])

    def test_partial_sweep_never_stales(self):
        with fresh_store():
            store.apply_results({"acme/gone": live(NEW_URL)})
            st = store.apply_results({"a/one": live()}, complete=False, known={"a/one"})
            self.assertEqual(st["endpoints_staled"], 0)
            self.assertIn(store.endpoint_key(NEW_URL), store.load(store.ENDPOINTS)["endpoints"])

    def test_api_key_never_written(self):
        key = "nvapi-" + "A" * 40
        with fresh_store(), mock.patch.dict(os.environ, {"NVIDIA_API_KEY": key}):
            store.apply_results({"a/one": failed("AUTH_OR_ENTITLEMENT", reason=f"401 for Bearer {key}"),
                                 "b/two": live(request_template={"headers": {"Authorization": "Bearer " + key}})})
            for name in (store.PROBES, store.VERIFIED, store.ENDPOINTS):
                with open(store.path(name), encoding="utf-8") as f:
                    self.assertNotIn(key, f.read(), name)


class VerifiedMembershipTest(unittest.TestCase):
    def test_pass_adds_fail_removes(self):
        with fresh_store():
            st = store.apply_results({"a/one": live()})
            self.assertEqual(st["verified_added"], ["a/one"])
            self.assertEqual(store.verified_ids(), ["a/one"])
            st = store.apply_results({"a/one": failed()})
            self.assertEqual(st["verified_dropped"], ["a/one"])
            ver = store.load(store.VERIFIED)
            self.assertEqual(ver["models"], {})
            self.assertEqual(ver["dropped"]["a/one"]["last_result"]["status"], "NO_WORKING_REST_ENDPOINT")
            self.assertIn("failed", ver["dropped"]["a/one"]["dropped_reason"])
            hist = store.probe_results()["a/one"]["history"]
            self.assertEqual(hist[0]["status"], store.LIVE)  # the earlier pass is in the history
            store.apply_results({"a/one": live()})  # passes again: back in, out of dropped
            ver = store.load(store.VERIFIED)
            self.assertIn("a/one", ver["models"])
            self.assertNotIn("a/one", ver["dropped"])

    def test_verified_record_has_endpoint_template_latency(self):
        with fresh_store():
            store.apply_results({"a/one": live(payload_used="chat", request_template={"messages": []},
                                               checked_by="spec_sweep")})
            r = store.verified_models()["a/one"]
            for f in ("url", "method", "request_template", "latency_sec", "verified_at", "verified_by"):
                self.assertIn(f, r)

    def test_inconclusive_results_change_nothing(self):
        with fresh_store():
            store.apply_results({"a/one": live()})
            store.apply_results({"a/one": {"status": "RATE_LIMITED"}})
            store.apply_results({"a/one": {"status": "SPEC_FOUND_NOT_PROBED"}})
            self.assertEqual(store.verified_ids(), ["a/one"])

    def test_partial_run_only_syncs_what_it_covered(self):
        with fresh_store():
            store.apply_results({"a/one": live(), "b/two": live()})
            store.apply_results({"c/three": failed()}, complete=False, known={"c/three"})
            self.assertEqual(store.verified_ids(), ["a/one", "b/two"])

    def test_complete_run_removes_models_no_longer_known(self):
        with fresh_store():
            store.apply_results({"a/one": live(), "b/two": live(), "c/old": live()})
            # full sweep: b/two still discovered but not in results (e.g. retired filter) stays;
            # c/old is gone from discovery and the run
            st = store.apply_results({"a/one": live()}, complete=True, known={"a/one", "b/two"})
            self.assertEqual(store.verified_ids(), ["a/one", "b/two"])
            self.assertEqual(st["verified_dropped"], ["c/old"])
            self.assertIn("c/old", store.load(store.PROBES)["archived"])

    def test_outage_drops_nothing(self):
        with fresh_store():
            store.apply_results({"a/one": live(), "b/two": live()})
            st = store.apply_results({"a/one": failed("AUTH_OR_ENTITLEMENT"),
                                      "b/two": failed("TIMEOUT_OR_SERVER_ERROR")}, complete=True, known=set())
            self.assertTrue(st["outage"])
            self.assertEqual(store.verified_ids(), ["a/one", "b/two"])

    def test_api_id_replaces_catalog_id(self):
        with fresh_store():
            store.apply_results({"z/glm-5-3": live()})
            store.apply_results({"z/glm-5-3": live(api_model_id="z/glm-5.3")})
            self.assertEqual(store.verified_ids(), ["z/glm-5.3"])


class DiscoveredSyncTest(unittest.TestCase):
    def _doc(self, models):
        return {"generated_at": "t", "sources": {}, "models": {
            m: {"id": m, "kind": "chat", "sources": list(src), "status": "active"} for m, src in models.items()}}

    def test_new_added_missing_removed_within_covered_sources(self):
        with fresh_store():
            store.sync_discovered(self._doc({"a/site": ["site"], "b/both": ["site", "key"], "c/key": ["key"]}),
                                  ["site", "key"], at="2026-11-01")
            # site read fine, the key call failed: c/key and b/both's key tag are kept
            st = store.sync_discovered(self._doc({"d/new": ["site"]}), ["site"], at="2026-11-11")
            doc = store.load(store.DISCOVERED)
            self.assertEqual(st["added"], ["d/new"])
            self.assertEqual(sorted(st["removed"]), ["a/site"])
            self.assertEqual(sorted(doc["models"]), ["b/both", "c/key", "d/new"])
            self.assertEqual(doc["models"]["b/both"]["sources"], ["key"])
            self.assertIn("a/site", doc["removed"])
            self.assertIn("site", doc["removed"]["a/site"]["removed_reason"])
            self.assertEqual(doc["summary"]["total"], 3)

    def test_offline_run_removes_nothing(self):
        with fresh_store():
            store.sync_discovered(self._doc({"a/one": ["site"], "b/two": ["docs"]}), ["site", "docs"])
            st = store.sync_discovered(self._doc({}), [])
            self.assertEqual(st["removed"], [])
            self.assertEqual(len(store.load(store.DISCOVERED)["models"]), 2)

    def test_removed_model_comes_back_with_first_seen(self):
        with fresh_store():
            store.sync_discovered(self._doc({"a/one": ["site"]}), ["site"], at="2026-10-01")
            store.sync_discovered(self._doc({}), ["site"], at="2026-10-05")
            st = store.sync_discovered(self._doc({"a/one": ["site"]}), ["site"], at="2026-11-11")
            doc = store.load(store.DISCOVERED)
            self.assertEqual(st["returned"], ["a/one"])
            self.assertEqual(doc["models"]["a/one"]["first_seen"], "2026-10-01")
            self.assertEqual(doc["removed"], {})

    def test_key_list_adds_unknown_models(self):
        with fresh_store():
            store.save_key_list(["k/one", "k/two"])
            self.assertEqual(sorted(store.load(store.DISCOVERED)["models"]), ["k/one", "k/two"])
            self.assertEqual(store.key_list(), ["k/one", "k/two"])

    def test_discover_marks_partial_site_as_not_covered(self):
        from nimlab import catalog
        doc = {"covered_sources": ["site", "docs"]}
        with fresh_store(), mock.patch.object(store, "sync_discovered", return_value={}) as sd:
            catalog.save_catalog(doc, offline=True)
            sd.assert_called_with(doc, [])
            catalog.save_catalog(doc)
            sd.assert_called_with(doc, ["site", "docs"])


class BenchmarkStoreTest(unittest.TestCase):
    def test_latest_and_history(self):
        with fresh_store():
            for i in range(store.BENCH_HISTORY_MAX + 2):
                store.save_benchmark({"timestamp": f"2026-11-{i + 1:02d}", "reasoning": [{"logic_pass": True}]})
            self.assertEqual(store.latest_benchmark()["timestamp"], "2026-11-12")
            runs = store.load(store.BENCH_HISTORY)["runs"]
            self.assertEqual(len(runs), store.BENCH_HISTORY_MAX)
            self.assertEqual(runs[0]["reasoning"], {"rows": 1, "ok": 1})

    def test_single_track_keeps_other_tracks(self):
        import nvidia_benchmark_suite as bs
        with fresh_store():
            store.save_benchmark({"timestamp": "2026-11-01", "vision": [{"model": "v"}]})
            with mock.patch("sys.stdout", new=io.StringIO()):
                bs.save_track("reasoning", [{"model": "r", "logic_pass": True}])
            b = store.latest_benchmark()
            self.assertEqual(b["vision"], [{"model": "v"}])
            self.assertEqual(b["reasoning"][0]["model"], "r")


class ListChoicePromptTest(unittest.TestCase):
    def ask(self, answer, verified=("a/1", "a/2"), allm=("a/1", "a/2", "b/3")):
        out = []
        res = picker.choose_list(verified, allm, input_fn=lambda _p: answer, out=out.append)
        return res, "\n".join(out)

    def test_prompt_shows_counts(self):
        _, text = self.ask("")
        self.assertIn("1. Verified 200 OK (2)  2. All discovered (3)", text)

    def test_default_is_verified(self):
        (models, scope), _ = self.ask("")
        self.assertEqual(scope, picker.VERIFIED)
        self.assertEqual(models, ["a/1", "a/2"])

    def test_choice_two_gives_full_list(self):
        (models, scope), _ = self.ask("2")
        self.assertEqual(scope, picker.ALL)
        self.assertEqual(models, ["a/1", "a/2", "b/3"])

    def test_empty_verified_defaults_to_full(self):
        (models, scope), text = self.ask("", verified=())
        self.assertEqual(scope, picker.ALL)
        self.assertIn("no model has passed", text)

    def test_eof_takes_default(self):
        def eof(_p):
            raise EOFError
        models, scope = picker.choose_list(["a"], ["a", "b"], input_fn=eof, out=lambda *_: None)
        self.assertEqual(scope, picker.VERIFIED)

    def test_unverified_note(self):
        self.assertEqual(picker.unverified_note("a/1", ["a/1"]), "")
        self.assertIn("hasn't passed the 200 OK test", picker.unverified_note("b/3", ["a/1"]))

    def test_playground_menu_asks_and_allows_unverified(self):
        import nvidia_playground as pg
        with mock.patch.object(pg, "MODELS", ["a/1"]), mock.patch.object(pg, "ALL_MODELS", ["a/1", "b/3"]), \
                mock.patch("builtins.input", side_effect=["2"]), mock.patch("sys.stdout", new=io.StringIO()) as out:
            self.assertEqual(pg.pick_list(), ["a/1", "b/3"])
            self.assertIn("Verified 200 OK (1)  2. All discovered (2)", out.getvalue())
        with mock.patch.object(pg, "MODELS", ["a/1"]), mock.patch("time.sleep"), \
                mock.patch("sys.stdout", new=io.StringIO()) as out:
            pg.note_if_unverified("b/3")
            self.assertIn("hasn't passed the 200 OK test", out.getvalue())

    def test_every_model_menu_uses_the_prompt(self):
        import inspect
        import nvidia_playground as pg
        src = inspect.getsource(pg.main)
        for call in ("list_models(pick_list())", "choose_model(pick_list())", "compare_models(pick_list())"):
            self.assertIn(call, src)
        self.assertIn("note_if_unverified(model)", inspect.getsource(pg.interactive_model_test))
        import orchestrator_testbed as ot
        self.assertIn("picker.choose_list", inspect.getsource(ot.swap_models_menu))


class DataCommandTest(unittest.TestCase):
    def test_overview_and_views(self):
        from nimlab import cli
        with fresh_store():
            store.apply_results({"a/one": live(), "b/two": failed()})
            for argv in (["data"], ["data", "show", "verified"], ["data", "show", "failed"], ["data", "paths"]):
                with mock.patch("sys.stdout", new=io.StringIO()) as out:
                    self.assertEqual(cli.main(argv), 0)
            for v in store.VIEWS:
                store.view(v)
            self.assertEqual([r[0] for r in store.view("failed")], ["b/two"])
            self.assertEqual([r[0] for r in store.view("verified")], ["a/one"])
            self.assertIn("memory.json", out.getvalue())


if __name__ == "__main__":
    unittest.main()
