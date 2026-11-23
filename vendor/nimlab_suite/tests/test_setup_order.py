"""3.7.2 first-run setup order (SeVin): key -> discover -> function IDs and
specs -> 200 OK sweep -> MCP -> roles -> everything else. Fake CLI, temp
HOME, no network."""

import io
import json
import os
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import config, configlint, doctor, setupflow, store, sweep, wizard
from tests.sandbox import FakeIO, lab
from tests.test_wizard import FakeCLI, FakeMgr, KEY, make

FID = "12345678-1111-2222-3333-444455556666"


def seed_discovered(*ids):
    store.save(store.DISCOVERED, {"models": {m: {"kind": k} for m, k in ids}})


def seed_verified(*ids):
    doc = store.load(store.VERIFIED)
    doc["models"] = {m: {"status": "LIVE", "catalog_kind": k} for m, k in ids}
    store.save(store.VERIFIED, doc)
    probes = store.load(store.PROBES)
    probes["models"] = {m: {"status": "LIVE"} for m, _k in ids}
    store.save(store.PROBES, probes)


class Base(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        for target, kw in (("nimlab.service.brief", {"return_value": "not set up"}),
                           ("nimlab.service.Manager", {"new": FakeMgr})):
            p = mock.patch(target, **kw)
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self._lab.__exit__(None, None, None)


class OrderTests(Base):
    def test_key_is_the_first_question_and_deps_come_after_it(self):
        events = []
        w, fio, cli, sh = make(["run", KEY, "save", False, "quit"], env={})
        w.key_check.side_effect = lambda k: events.append("key") or (True, "NVIDIA accepted the key")
        sh.side_effect = lambda *a, **k: events.append("deps") or 0
        with mock.patch.object(w, "st_deps", return_value=(False, "missing: grpcio")), \
                redirect_stdout(io.StringIO()):
            w.run()
        self.assertIn("== Step 1/12: NVIDIA API key ==", fio.text)
        self.assertEqual(fio.prompts[:2], ["What now?", "NVIDIA API key"])
        self.assertEqual(events[0], "key")
        self.assertIn("deps", events)
        self.assertIn("shortcut install", cli.argvs())

    def test_discover_then_functions_then_sweep_run_the_right_commands(self):
        w, fio, cli, _ = make([], env={"NVIDIA_API_KEY": KEY})
        w.do_discover()
        self.assertEqual(cli.calls[0][0], ["discover"])
        seed_discovered(("meta/llama-3.1-8b-instruct", "chat"))
        w.do_functions()
        self.assertEqual(cli.argvs()[1:3], [f"sweep --plan-only --time-limit {setupflow.SPECS_LIMIT}",
                                            "grpc fill"])
        w2, fio2, cli2, _ = make(["fast"], env={"NVIDIA_API_KEY": KEY})
        w2.do_sweep()
        self.assertEqual(cli2.argvs(), [f"sweep --time-limit {setupflow.SWEEP_FAST_LIMIT} --fast --site-only"])
        self.assertIn("Roles, gRPC and memory are built from its results", fio2.text)
        w3, fio3, cli3, _ = make(["skip"], env={"NVIDIA_API_KEY": KEY})
        w3.do_sweep()
        self.assertEqual(cli3.calls, [])

    def test_discover_without_a_key_offers_step_1_then_reads_the_site(self):
        w, fio, cli, _ = make([False], env={})
        w.do_discover()
        self.assertIn("No NVIDIA key yet", fio.text)
        self.assertIn("run step 1", fio.text)
        self.assertEqual(cli.calls[0][0], ["discover", "--no-key"])

    def test_steps_name_the_missing_earlier_step_never_the_key(self):
        for step, need in (("do_functions", "step 2"), ("do_sweep", "step 2"), ("do_roles", "step 4")):
            w, fio, cli, _ = make([False], env={"NVIDIA_API_KEY": KEY})
            getattr(w, step)()
            self.assertIn(f"run {need}", fio.text, step)
            self.assertNotIn("check the NVIDIA key", fio.text)
            self.assertNotIn("internet", fio.text)

    def test_missing_data_offer_runs_the_earlier_step(self):
        w, fio, cli, _ = make([True], env={"NVIDIA_API_KEY": KEY})
        w.do_functions()          # yes: run step 2 (discover) now; the fake saves nothing
        self.assertEqual(cli.calls[0][0], ["discover"])
        self.assertIn("Still no models discovered", fio.text)

    def test_shipped_spec_pages_do_not_count_as_step_3_done(self):
        d = sweep.spec_cache_dir()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "x.json"), "w") as f:
            json.dump({"model_id": "a/b"}, f)
        w, fio, cli, _ = make([], env={"NVIDIA_API_KEY": KEY})
        ok, text = w.st_functions()
        self.assertFalse(ok)
        self.assertIn("1 spec pages shipped", text)
        seed_discovered(("a/b", "chat"))
        w.do_functions()
        self.assertTrue(w.st_functions()[0])

    def test_existing_install_is_not_forced_through_discovery(self):
        seed_discovered(("meta/llama-3.1-8b-instruct", "chat"))
        w, fio, cli, _ = make(["skip"])
        ok, text = w.st_discover()
        self.assertTrue(ok)
        prompts = []
        orig = fio.choose
        fio.choose = lambda p, o, d=None: prompts.append((o, d)) or orig(p, o, d)
        w.run(only=None) if False else w.run_step(2, 11, "discover", "Discover", w.st_discover, w.do_discover)
        opts, dflt = prompts[0]
        self.assertEqual(dflt, "skip")
        self.assertIn("Run discovery again (refresh)", dict(opts)["run"])
        self.assertEqual(cli.calls, [])

    def test_ctrl_c_in_a_long_step_stops_only_that_step(self):
        with mock.patch.object(wizard, "_pump_loop", side_effect=KeyboardInterrupt), \
                mock.patch.object(wizard.subprocess, "Popen") as po, redirect_stdout(io.StringIO()):
            po.return_value.stdout = io.StringIO("")
            code, out = wizard.run_cli(["sweep"], timeout=5)
        self.assertEqual(code, 130)
        self.assertIn("stopped with Ctrl+C", out)
        po.return_value.kill.assert_called_once()


class RolesTests(Base):
    VER = (("meta/llama-3.3-70b-instruct", "chat"), ("nvidia/llama-3.2-nv-embedqa-1b-v2", "embedding"),
           ("meta/llama-3.2-11b-vision-instruct", "vision"))
    TOOLS = [{"name": "tts_speak", "description": "Speak text aloud",
              "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}},
             {"name": "web_search", "description": "Search the web"}]

    def wiz(self, answers):
        seed_verified(*self.VER)
        return make(answers) if False else (
            wizard.Wizard(io=FakeIO(answers), cli=FakeCLI(), sh=mock.Mock(return_value=0),
                          key_check=mock.Mock(return_value=(True, "ok")), mcp_tools=lambda: (self.TOOLS, None)))

    def test_suggestions_come_from_the_verified_list_and_mcp_tools(self):
        seed_verified(*self.VER)
        sugg = {r["key"]: r for r in setupflow.suggest({}, [m for m, _ in self.VER],
                                                      {m: k for m, k in self.VER}, {}, self.TOOLS)}
        self.assertEqual(len(sugg), 16)
        self.assertEqual(sugg["embedding"]["pick"], ("model", "nvidia/llama-3.2-nv-embedqa-1b-v2"))
        self.assertEqual(sugg["vision"]["pick"], ("model", "meta/llama-3.2-11b-vision-instruct"))
        self.assertEqual(sugg["tts"]["pick"], ("mcp", "tts_speak"))
        self.assertTrue(sugg["persona"]["options"])            # always something to choose from
        # a current verified choice is kept
        cur = setupflow.suggest({"persona": {"model": "meta/llama-3.3-70b-instruct"}},
                                [m for m, _ in self.VER], {m: k for m, k in self.VER}, {}, self.TOOLS)
        self.assertIn("current model", cur[1]["why"] if cur[1]["key"] == "persona" else
                      next(r for r in cur if r["key"] == "persona")["why"])

    def test_accept_all_writes_the_suggestions(self):
        w = self.wiz(["accept"])
        w.do_roles()
        roles = config.load_json(config.CLUSTER_CONFIG, {})["roles"]
        self.assertEqual(roles["embedding"]["model"], "nvidia/llama-3.2-nv-embedqa-1b-v2")
        self.assertEqual((roles["tts"]["backend"], roles["tts"]["tool"]), ("mcp", "tts_speak"))
        self.assertIn("Suggestions from 3 verified models and 2 MCP tools", w.io.text)

    def test_change_one_then_accept_and_keep(self):
        w = self.wiz(["one", "2", "meta/llama-3.3-70b-instruct", "accept"])
        w.do_roles()
        self.assertIn("your choice", w.io.text)
        before = json.dumps(config.load_json(config.CLUSTER_CONFIG, {}).get("roles"), sort_keys=True)
        w2 = self.wiz(["keep"])
        w2.do_roles()
        self.assertEqual(before, json.dumps(config.load_json(config.CLUSTER_CONFIG, {}).get("roles"), sort_keys=True))

    def test_memory_offers_verified_embedding_models_with_their_size(self):
        opts = setupflow.embed_options(["nvidia/llama-3.2-nv-embedqa-1b-v2", "nvidia/nv-embed-v1",
                                        "meta/llama-3.3-70b-instruct"],
                                       {"nvidia/nv-embed-v1": "embedding",
                                        "nvidia/llama-3.2-nv-embedqa-1b-v2": "embedding"})
        self.assertEqual(opts[0][0], "nvidia/llama-3.2-nv-embedqa-1b-v2")
        self.assertIn("matches the memory table", opts[0][2])
        self.assertNotIn("meta/llama-3.3-70b-instruct", [o[0] for o in opts])


class SweepAndGrpcTests(Base):
    def test_sweep_time_limit_keeps_what_it_did_not_reach(self):
        class R:
            def resolve(self, mid, use_cache=True):
                return {"model_id": mid, "plans": [], "notes": {}}
        logs = []
        with mock.patch("time.monotonic", side_effect=[0, 0, 0, 999] + [999] * 50):
            res = sweep.run(["a/1", "b/2", "c/3"], R(), None, probe=False, log=logs.append, time_limit=5)
        self.assertLess(len(res), 3)
        self.assertTrue(any("Time limit" in ln and "not checked" in ln for ln in logs))

    def test_fill_grpc_ids_from_the_spec_cache(self):
        from nimlab import cli
        d = sweep.spec_cache_dir()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "x.json"), "w") as f:
            json.dump({"model_id": "nvidia/parakeet-ctc-1.1b-asr", "function_id": FID,
                       "notes": {"grpc_only": True}}, f)
        store.save(store.PROBES, {"models": {"nvidia/magpie-tts-multilingual": {"status": "GRPC_NVCF_ONLY"}}})
        logs = []
        n, with_id, missing = cli.fill_grpc_ids(fetch=False, log=logs.append)
        self.assertEqual((n, with_id, missing), (2, 1, ["nvidia/magpie-tts-multilingual"]))
        self.assertIn("1 of 2 gRPC-only models have one", logs[0])
        self.assertIn("nimlab grpc set", logs[1])

    def test_grpc_refresh_with_nothing_known_blames_missing_data(self):
        from nimlab import cli
        with redirect_stdout(io.StringIO()) as out:
            code = cli.main(["grpc", "refresh"])
        self.assertEqual(code, 3)
        self.assertIn("missing data, not a key or network problem", out.getvalue())
        self.assertIn("nimlab setup functions", out.getvalue())


class LintTests(Base):
    def test_homepage_tts_url_and_bare_url_roles_are_flagged(self):
        c = {"voice_settings": {"tts_url": "https://nvidia.com"},
             "roles": {"persona": {"model": "https://build.nvidia.com/meta/llama"},
                       "vision": {"model": "meta/llama-3.2-11b-vision-instruct",
                                  "fallbacks": ["https://example.com/v1", "meta/ok-model"]}}}
        found = configlint.find_problems(c)
        where = [f[0] for f in found]
        self.assertEqual(where, ["voice_settings.tts_url", "roles.persona", "roles.vision.fallback"])
        self.assertIn("website homepage", found[0][1])
        ok = {"voice_settings": {"tts_url": "https://ai.api.nvidia.com/v1/audio/synthesize"},
              "roles": {"persona": {"model": "meta/llama-3.3-70b-instruct"}}}
        self.assertEqual(configlint.find_problems(ok), [])

    def test_doctor_and_setup_summary_show_them(self):
        rows = doctor.settings_checks(types.SimpleNamespace(cluster={"voice_settings": {"tts_url": "https://nvidia.com/"}}))
        self.assertFalse(rows[0][0])
        self.assertIn("voice_settings.tts_url", rows[0][1])
        raw = config.load_json(config.CLUSTER_CONFIG, {})
        raw.setdefault("voice_settings", {})["tts_url"] = "https://nvidia.com"
        config.save_json(config.CLUSTER_CONFIG, raw)
        w, fio, *_ = make([])
        w.summary()
        self.assertIn("voice_settings.tts_url: https://nvidia.com is a website homepage", fio.text)


if __name__ == "__main__":
    unittest.main()
