"""The guided setup (nimlab setup): scripted answers, a fake CLI, temp HOME.
No real subprocess, network, Oracle, cloudflared or service is used."""

import io
import json
import os
import stat
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import server as S, store, wizard
from tests.sandbox import FakeIO, all_text, lab

KEY = "nvapi-" + "k" * 40
PW = "Sup3r-Secret-Oracle-PW"
TG = "123456789:" + "A" * 35
TUN = "eyJ" + "t" * 60


class FakeCLI:
    def __init__(self, results=None):
        self.calls = []
        self.results = results or {}

    def __call__(self, argv, timeout=900, input_text=None, show=True):
        self.calls.append((list(argv), input_text))
        for prefix, res in self.results.items():
            if " ".join(argv).startswith(prefix):
                return res
        return 0, "ok"

    def argvs(self):
        return [" ".join(a) for a, _ in self.calls]


class FakeMgr:
    backend = "builtin"

    def __init__(self, *a, **k):
        pass

    def installed(self):
        return False


def make(answers, cli=None, env=None, key_ok=(True, "NVIDIA accepted the key (HTTP 200)")):
    fio = FakeIO(answers)
    cli = cli or FakeCLI()
    sh = mock.Mock(return_value=0)
    w = wizard.Wizard(io=fio, cli=cli, sh=sh, key_check=mock.Mock(return_value=key_ok), env=env)
    return w, fio, cli, sh


class WizardTests(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        p = mock.patch("nimlab.service.brief", return_value="not set up")
        p.start()
        self.addCleanup(p.stop)
        p2 = mock.patch("nimlab.service.Manager", FakeMgr)
        p2.start()
        self.addCleanup(p2.stop)

    def tearDown(self):
        self._lab.__exit__(None, None, None)

    def test_steps_in_the_372_order(self):
        w, *_ = make([])
        self.assertEqual(w.step_keys(), ["key", "discover", "functions", "sweep", "mcp", "roles", "grpc",
                                         "memory", "server", "telegram", "selfadmin", "audio"])   # 3.8.6: audio last
        self.assertEqual([k for k, *_ in w.extra_steps], ["deps", "shortcut"])

    def test_skip_everything_shows_status_and_summary_and_marks_done(self):
        w, fio, cli, sh = make(["skip"] * 12)
        self.assertTrue(wizard.first_run())
        w.run()
        self.assertEqual(cli.calls, [])
        sh.assert_not_called()
        for i in range(1, 13):
            self.assertIn(f"== Step {i}/12:", fio.text)
        self.assertEqual(fio.text.count("Now: "), 12)
        self.assertIn("== Setup summary ==", fio.text)
        self.assertEqual(set(w.results), set(w.step_keys()))
        self.assertFalse(wizard.first_run())

    def test_quit_stops_and_still_summarises(self):
        w, fio, cli, _ = make(["skip", "quit"])
        w.run()
        self.assertIn("== Step 2/12:", fio.text)
        self.assertNotIn("== Step 3/12:", fio.text)
        self.assertIn("== Setup summary ==", fio.text)
        self.assertIn("Left to do:", fio.text)

    def test_ctrl_d_mid_step_ends_cleanly(self):
        w, fio, *_ = make(["run"])        # then the script runs out -> KeyboardInterrupt
        self.assertEqual(w.run(only=None), 0)
        self.assertIn("Setup stopped", fio.text)
        self.assertIn("== Setup summary ==", fio.text)

    def test_failing_step_does_not_end_setup(self):
        w, fio, *_ = make(["run", False, "skip"])
        w.steps[0] = ("deps", "Install dependencies", w.st_deps, mock.Mock(side_effect=ValueError("boom")))
        w.steps = w.steps[:2]
        w.run()
        self.assertIn("[x] This step failed: ValueError: boom", fio.text)
        self.assertIn("== Step 2/2:", fio.text)
        self.assertIn("After: ", fio.text)

    def test_rerun_a_step(self):
        w, fio, *_ = make(["run", True, False])
        do = mock.Mock()
        w.steps = [("deps", "Install dependencies", lambda: (True, "fine"), do)]
        w.run()
        self.assertEqual(do.call_count, 2)

    def test_deps_on_termux_uses_pkg_first(self):
        w, fio, cli, sh = make([], env={"TERMUX_VERSION": "1", "PREFIX": "/data/data/com.termux/files/usr"})
        w.do_deps()
        first = sh.call_args_list[0][0][0]
        self.assertEqual(first[:3], ["pkg", "install", "-y"])
        self.assertIn("python-grpcio", first)
        self.assertTrue(any("oracledb" in c[0][0] for c in sh.call_args_list))

    def test_deps_elsewhere_skips_pkg(self):
        w, fio, cli, sh = make([], env={})
        w.do_deps()
        self.assertFalse(any(c[0][0][0] == "pkg" for c in sh.call_args_list))

    def test_key_saved_private_and_never_shown(self):
        w, fio, cli, _ = make([KEY, "save"])
        with redirect_stdout(io.StringIO()) as out:
            w.do_key()
        self.assertTrue(os.path.exists(self.lab.env_file))
        self.assertEqual(stat.S_IMODE(os.stat(self.lab.env_file).st_mode), 0o600)
        with open(self.lab.env_file) as f:
            self.assertIn(KEY, f.read())
        w.key_check.assert_called_once_with(KEY)
        self.assertNotIn(KEY, fio.text + out.getvalue())
        self.assertIn("[ok] NVIDIA accepted the key", fio.text)
        ok, text = w.st_key()
        self.assertTrue(ok)
        self.assertNotIn(KEY, text)

    def test_key_refused_is_reported(self):
        w, fio, *_ = make([KEY, "session"], key_ok=(False, "NVIDIA refused the key (HTTP 401)"))
        w.do_key()
        self.assertIn("[x] NVIDIA refused the key", fio.text)
        self.assertFalse(os.path.exists(self.lab.env_file))

    def test_key_check_against_fake_http(self):
        self.assertEqual(wizard.check_nvidia_key(KEY, http=lambda r: 200)[0], True)
        self.assertEqual(wizard.check_nvidia_key(KEY, http=lambda r: 401)[0], False)

    def test_mcp_key_goes_through_stdin_not_argv(self):
        cli = FakeCLI({"mcp test": (1, "HTTP 401 Unauthorized")})
        w, fio, cli, _ = make(["https://mcp.example.com/mcp", "mcp-secret-key-123456", "bearer"], cli=cli)
        w.do_mcp()
        self.assertIn("mcp set-url https://mcp.example.com/mcp --no-test", cli.argvs())
        setkey = [c for c in cli.calls if c[0][:2] == ["mcp", "set-key"]][0]
        self.assertEqual(setkey[1], "mcp-secret-key-123456\n")
        self.assertFalse(any("mcp-secret-key-123456" in a for a in cli.argvs()))
        self.assertIn("mcp auth bearer", cli.argvs())
        self.assertIn("refused the key", fio.text)

    def test_grpc_on_a_fresh_install_says_data_is_missing_not_the_key(self):
        # 3.7.1 bug: "No gRPC models known yet" then "check the NVIDIA key"
        w, fio, cli, _ = make(["skip"])
        w.do_grpc()
        self.assertIn("No gRPC models known yet", fio.text)
        self.assertIn("missing data, not a key or network problem", fio.text)
        self.assertNotIn("NVIDIA key", fio.text)
        self.assertNotIn("internet", fio.text)
        self.assertEqual(cli.calls, [])
        # offered: read the pages (step 3) first
        w2, fio2, cli2, _ = make(["functions", False])
        w2.do_grpc()
        self.assertIn("No models discovered yet", fio2.text)
        self.assertIn("run step 2", fio2.text)

    def test_grpc_with_known_models_reports_and_fills_missing(self):
        store.set_grpc_function("nvidia/parakeet-ctc-1.1b-asr", "0" * 8 + "-1111-2222-3333-" + "4" * 12,
                                source="spec_cache")
        store.save(store.PROBES, {"models": {"nvidia/magpie-tts-multilingual": {"status": "GRPC_NVCF_ONLY"}}})
        w, fio, cli, _ = make([True, "done"])
        ok, text = w.st_grpc()
        self.assertIn("gRPC-only", text)
        w.do_grpc()
        self.assertEqual(cli.argvs()[:2], ["grpc list", "grpc fill"])

    def test_memory_oracle_tls_writes_private_creds(self):
        cred = os.path.join(self.lab.home, ".config", "nimlab", "oracle_mem.json")
        dsn = "(description=(address=(protocol=tcps)(port=1522)(host=adb.example.com)))"
        w, fio, cli, _ = make(["oracle", "MEM", PW, "tls", dsn, False, "role", True, True, True])
        with mock.patch.object(w, "oracle_creds", wraps=lambda p: wizard.Wizard.oracle_creds(w, cred)):
            w.do_memory()
        self.assertEqual(stat.S_IMODE(os.stat(cred).st_mode), 0o600)
        with open(cred) as f:
            data = json.load(f)
        self.assertEqual((data["user"], data["password"], data["dsn"], data["wallet_dir"]), ("MEM", PW, dsn, ""))
        self.assertEqual(cli.argvs(), ["memory use oracle", "memory embed role", "memory set auto_store on",
                                       "memory set auto_recall on", "memory test", "memory setup"])
        self.assertNotIn(PW, fio.text)
        self.assertFalse(any(PW in a or PW in (i or "") for a, i in [(" ".join(x), y) for x, y in cli.calls]))
        self.assertIn("access control", fio.text)

    def test_memory_oracle_wallet_finds_alias(self):
        wallet = os.path.join(self.lab.home, "wallet")
        os.makedirs(wallet)
        with open(os.path.join(wallet, "tnsnames.ora"), "w") as f:
            f.write("mydb_high = (description=...)\nmydb_low = (description=...)\n")
        cred = os.path.join(self.lab.home, ".config", "nimlab", "oracle_mem.json")
        w, fio, cli, _ = make(["MEM", PW, "wallet", wallet, None, ""])
        w.oracle_creds(cred)
        with open(cred) as f:
            data = json.load(f)
        self.assertEqual(data["dsn"], "mydb_high")
        self.assertEqual(data["wallet_dir"], wallet)
        self.assertIn("Aliases in the wallet: mydb_high, mydb_low", fio.text)

    def test_memory_oracle_error_explained(self):
        cli = FakeCLI({"memory test": (1, "DPY-4005 ORA-01017: invalid username/password")})
        cred = os.path.join(self.lab.home, ".config", "nimlab", "oracle_mem.json")
        w, fio, cli, _ = make(["oracle", "MEM", PW, "tls", "(description=x)", False, "keep", True, True], cli=cli)
        with mock.patch.object(w, "oracle_creds", wraps=lambda p: wizard.Wizard.oracle_creds(w, cred)):
            w.do_memory()
        self.assertIn("user name or password is wrong", fio.text)
        self.assertNotIn("memory setup", cli.argvs())

    def test_memory_custom_profile_name(self):
        cred = os.path.join(self.lab.home, ".config", "nimlab", "oracle_mem.json")
        # first try another agent's name (refused), then a free one
        w, fio, cli, _ = make(["oracle", "MEM", PW, "tls", "(description=x)", True, "charlie", "quill",
                               "role", True, True, True])
        with mock.patch.object(w, "oracle_creds", wraps=lambda p: wizard.Wizard.oracle_creds(w, cred)):
            w.do_memory()
        self.assertIn("protected", fio.text)
        self.assertIn("memory set oracle.table_prefix QUILL", cli.argvs())
        self.assertIn("memory set oracle.profile_id QUILL", cli.argvs())
        self.assertNotIn("memory set oracle.table_prefix CHARLIE", cli.argvs())
        self.assertLess(cli.argvs().index("memory set oracle.profile_id QUILL"), cli.argvs().index("memory setup"))

    def test_memory_profile_default_stays_testbed(self):
        cred = os.path.join(self.lab.home, ".config", "nimlab", "oracle_mem.json")
        w, fio, cli, _ = make(["oracle", "MEM", PW, "tls", "(description=x)", False, "role", True, True, True])
        with mock.patch.object(w, "oracle_creds", wraps=lambda p: wizard.Wizard.oracle_creds(w, cred)):
            w.do_memory()
        self.assertIn("Memory profile: TESTBED", fio.text)
        self.assertFalse([a for a in cli.argvs() if "profile_id" in a or "table_prefix" in a])

    def test_explain_oracle_hints(self):
        self.assertIn("access control list", wizard.explain_oracle("ORA-12506: TNS:listener rejected").lower())
        self.assertIn("pip install oracledb", wizard.explain_oracle("No module named 'oracledb'"))
        self.assertEqual(wizard.explain_oracle("all good"), "")
        # "oracle" contains the letters a-c-l: it must not read as an access-list problem
        self.assertEqual(wizard.explain_oracle("connected to oracle as MEM"), "")

    def test_memory_local_and_off(self):
        w, fio, cli, _ = make(["local", "~/mem", "keep", False, True])
        w.do_memory()
        self.assertEqual(cli.argvs()[0], f"memory use local {os.path.join(self.lab.home, 'mem')}")
        w2, fio2, cli2, _ = make(["off"])
        w2.do_memory()
        self.assertEqual(cli2.argvs(), ["memory use off"])

    def test_server_settings_saved(self):
        w, fio, cli, _ = make(["lan", "9100", "labmodel", "new", "https://chat.example.com", "5", "content",
                               False, True])
        w.server_settings()
        s = S.load_settings()
        self.assertEqual((s["lan"], s["bind"], s["port"], s["model_name"]), (True, "0.0.0.0", 9100, "labmodel"))
        self.assertEqual((s["cors_origin"], s["stream_chunk_words"], s["entity"]["trace"]),
                         ("https://chat.example.com", 5, "content"))
        self.assertEqual(s["agent_tool_calls"], "deny")
        self.assertTrue(s["api_key"])
        self.assertNotIn(s["api_key"], fio.text)

    def test_server_settings_reject_bad_values(self):
        before = S.load_settings()
        w, fio, *_ = make(["local", "80", "bad name!", "own", "short", "*", "99", "off", True, False])
        w.server_settings()
        s = S.load_settings()
        self.assertEqual(s["port"], before["port"])
        self.assertEqual(s["model_name"], before.get("model_name"))
        self.assertEqual(s["api_key"], before["api_key"])
        self.assertIn("Too short", fio.text)

    def test_tunnel_named_token_goes_through_stdin(self):
        w, fio, cli, _ = make(["named", "token", "lab.example.com", TUN, True],
                              env={"PATH": "/nonexistent", "HOME": self.lab.home})
        with mock.patch("nimlab.tunnel.find_cloudflared", return_value="/fake/cloudflared"):
            w.tunnel_step()
        named = [c for c in cli.calls if c[0][:3] == ["serve", "tunnel", "named"]][0]
        self.assertEqual(named[0], ["serve", "tunnel", "named", "--token", "--hostname", "lab.example.com"])
        self.assertEqual(named[1], TUN + "\n")
        self.assertFalse(any(TUN in a for a in cli.argvs()))
        self.assertIn("serve tunnel auto on", cli.argvs())
        self.assertNotIn(TUN, fio.text)

    def test_tunnel_quick_offers_install(self):
        w, fio, cli, _ = make(["quick", True, False])
        with mock.patch("nimlab.tunnel.find_cloudflared", return_value=None):
            w.tunnel_step()
        self.assertEqual(cli.argvs(), ["serve tunnel install", "serve tunnel quick", "serve tunnel auto off"])

    def test_tunnel_named_config(self):
        w, fio, cli, _ = make(["named", "config", "lab.example.com", "my-tunnel", "~/.cloudflared/x.json", True])
        with mock.patch("nimlab.tunnel.find_cloudflared", return_value="/fake/cloudflared"):
            w.tunnel_step()
        self.assertIn("serve tunnel named my-tunnel --credentials ~/.cloudflared/x.json --hostname lab.example.com",
                      cli.argvs())

    def test_service_step_boot_on_termux(self):
        w, fio, cli, _ = make(["install", True], env={"TERMUX_VERSION": "1"})
        w.service_step()
        self.assertEqual(cli.argvs(), ["service install --boot"])
        w2, fio2, cli2, _ = make(["install"], env={})
        w2.service_step()
        self.assertEqual(cli2.argvs(), ["service install"])

    def test_telegram_token_through_stdin(self):
        w, fio, cli, _ = make([True, TG, "capture", "polling", False, False])
        w.do_telegram()
        st = [c for c in cli.calls if c[0] == ["telegram", "set-token"]][0]
        self.assertEqual(st[1], TG + "\n")
        self.assertFalse(any(TG in a for a in cli.argvs()))
        self.assertIn("telegram allow --capture 120", cli.argvs())
        self.assertIn("telegram mode polling", cli.argvs())
        self.assertIn("telegram voice off", cli.argvs())

    def test_telegram_capture_409_explained_then_manual_id(self):
        """3.7.1: the capture step ends at once on a 409 (another poller),
        explains it, and offers to type the ID by hand; the ID is saved."""
        cli = FakeCLI({"telegram allow": (1, "[!] Another copy of this bot is polling (409).")})
        w, fio, cli, _ = make([True, TG, "capture", True, "123456789", "polling", False, False], cli=cli)
        w.do_telegram()
        self.assertIn("another program polls this bot", fio.text)
        self.assertIn("telegram allow 123456789", cli.argvs())
        cap = [c for c in cli.calls if c[0][:3] == ["telegram", "allow", "--capture"]][0]
        self.assertEqual(cap[0][3], "120")      # bounded wait

    def test_telegram_skip_capture(self):
        w, fio, cli, _ = make([True, TG, "skip", "polling", False, False])
        w.do_telegram()
        self.assertFalse([a for a in cli.argvs() if a.startswith("telegram allow")])

    def test_telegram_bad_token_stops(self):
        cli = FakeCLI({"telegram set-token": (1, "[x] Telegram did not accept the token")})
        w, fio, cli, _ = make([True, TG], cli=cli)
        w.do_telegram()
        self.assertEqual(cli.argvs(), ["telegram set-token"])
        self.assertIn("did not accept the token", fio.text)

    def test_selfadmin_makes_private_admin_key(self):
        w, fio, cli, _ = make([True, False, True])
        w.do_selfadmin()
        from nimlab import selfadmin
        k = selfadmin.load_admin_key()
        self.assertTrue(k.startswith("nimlab-admin-"))
        self.assertEqual(stat.S_IMODE(os.stat(selfadmin.admin_key_path()).st_mode), 0o600)
        self.assertNotIn(k, fio.text)
        self.assertEqual(cli.argvs(), ["selfadmin on", "selfadmin shell off"])

    def test_no_secret_lands_in_data_or_config(self):
        cred = os.path.join(self.lab.home, ".config", "nimlab", "oracle_mem.json")
        w, fio, cli, _ = make(["MEM", PW, "tls", "(description=x)"])
        w.oracle_creds(cred)
        self.assertNotIn(PW, all_text(self.lab.data) + all_text(self.lab.proj))

    def test_cmd_setup_list_unknown_and_first_run_flags(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(wizard.cmd_setup(types.SimpleNamespace(step="list")), 0)
        lines = [ln for ln in out.getvalue().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 14)            # 12 steps + deps and shortcut (done with step 1)
        self.assertTrue(lines[0].lstrip().startswith("1. key"))
        self.assertTrue(lines[1].lstrip().startswith("2. discover"))
        self.assertTrue(lines[3].lstrip().startswith("4. sweep"))
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(wizard.cmd_setup(types.SimpleNamespace(step="nope")), 2)
        self.assertIn("No step 'nope'", out.getvalue())
        self.assertEqual(wizard.cmd_setup(types.SimpleNamespace(step="first-run")), 0)
        self.assertEqual(wizard.cmd_setup(types.SimpleNamespace(step="skip-first-run")), 0)
        self.assertEqual(wizard.cmd_setup(types.SimpleNamespace(step="first-run")), 1)
        self.assertTrue(os.path.exists(os.path.join(store.data_dir(), wizard.MARK)))

    def test_single_step_by_name_alias_and_number(self):
        for step, key in (("ltm", "memory"), ("1", "key"), ("3", "functions"), ("bot", "telegram"),
                          ("deps", "deps"), ("shortcut", "shortcut"), ("200", "sweep"), ("specs", "functions"),
                          ("discover", "discover"), ("grpc", "grpc"), ("6", "roles"), ("mcp", "mcp")):
            with mock.patch.object(wizard.Wizard, "run", return_value=0) as run:
                wizard.cmd_setup(types.SimpleNamespace(step=step))
            run.assert_called_once_with(only=[key])

    def test_single_step_runs_without_menu(self):
        w, fio, cli, _ = make([False])
        do = mock.Mock()
        w.steps = [("grpc", "gRPC", lambda: (False, "none"), do)]
        w.run(only=["grpc"])
        do.assert_called_once()
        self.assertNotIn("What now?", fio.prompts)


if __name__ == "__main__":
    unittest.main()


class RunCliTests(unittest.TestCase):
    def test_background_child_holding_pipe_does_not_hang_setup(self):
        """3.7.1: `service install` starts a background process; when it keeps
        the output pipe open, run_cli still returns once the command ended."""
        import subprocess
        import time as _t
        real = subprocess.Popen

        def fake_popen(cmd, **kw):
            return real(["bash", "-c", "(sleep 30 &); echo installed; exit 0"], **{**kw, "cwd": None})
        t0 = _t.monotonic()
        with mock.patch.object(wizard.subprocess, "Popen", fake_popen), redirect_stdout(io.StringIO()):
            code, out = wizard.run_cli(["service", "install"], timeout=25)
        self.assertEqual(code, 0)
        self.assertIn("installed", out)
        self.assertLess(_t.monotonic() - t0, 10)
