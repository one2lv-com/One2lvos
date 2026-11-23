"""v3.5: the MCP server URL / API key / auth screen. The key is saved in a
600 file outside the project, the env var wins, and the key never shows
up in config files, logs, output or server replies."""
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from nimlab import config, mcpkey, mcpmenu
from nimlab.core import HttpClient, mask
from nimlab.mcp import auth_headers
from tests.fakes import FakeMCPServer, FakeResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = "mcp-secret-KEY-1234567890abcdefWXYZ"
KEY2 = "mcp-other-KEY-0987654321zyxwvuQRST"


class KeyCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nimlab_sec_")
        self.path = os.path.join(self.dir, "cfg", "nimlab", "secrets.json")
        e = {k: v for k, v in os.environ.items() if k not in ("MCP_API_KEY", "MY_MCP_KEY")}
        e["NIMLAB_SECRETS"] = self.path
        p = mock.patch.dict(os.environ, e, clear=True)
        p.start()
        self.addCleanup(p.stop)
        mcpkey._session.clear()
        self.addCleanup(mcpkey._session.clear)


class AuthServer(FakeMCPServer):
    """FakeMCPServer that wants header <name>: <key> (or Bearer)."""

    def __init__(self, tools, key, header="X-API-Key", bearer=False):
        super().__init__(tools)
        self.key, self.header_name, self.bearer = key, header, bearer
        self.seen = []

    def __call__(self, req, timeout=None):
        h = {k.lower(): v for k, v in req.header_items()}
        self.seen.append(h)
        want = ("authorization", f"Bearer {self.key}") if self.bearer else (self.header_name.lower(), self.key)
        if h.get(want[0]) != want[1]:
            return FakeResponse({"error": "unauthorized"}, status=401)
        return super().__call__(req, timeout)


TOOLS = [{"name": "search", "description": "s", "inputSchema": {}},
         {"name": "charlie_mem", "description": "m", "inputSchema": {}}]


def http_for(server):
    return HttpClient(timeout=5, retries=0, opener=server, sleep=lambda x: None)


class TestSavedKey(KeyCase):
    def test_secrets_path_is_outside_the_project(self):
        os.environ.pop("NIMLAB_SECRETS")
        with mock.patch.dict(os.environ, {"HOME": self.dir}):
            os.environ.pop("XDG_CONFIG_HOME", None)
            p = mcpkey.secrets_path()
        self.assertEqual(p, os.path.join(self.dir, ".config", "nimlab", "secrets.json"))
        self.assertFalse(os.path.abspath(p).startswith(ROOT + os.sep))

    def test_save_load_delete(self):
        self.assertEqual(mcpkey.saved_key(), "")
        self.assertEqual(mcpkey.resolve(), ("", "none"))
        mcpkey.save_key(KEY + "\n")
        self.assertEqual(mcpkey.saved_key(), KEY)
        self.assertEqual(mcpkey.resolve(), (KEY, "saved"))
        # replace
        mcpkey.save_key(KEY2)
        self.assertEqual(mcpkey.resolve(), (KEY2, "saved"))
        self.assertTrue(mcpkey.delete_key())
        self.assertFalse(os.path.exists(self.path))
        self.assertFalse(mcpkey.delete_key())
        self.assertEqual(mcpkey.resolve(), ("", "none"))

    def test_file_and_folder_permissions(self):
        mcpkey.save_key(KEY)
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(self.path)).st_mode), 0o700)
        # a loose file made by hand is tightened on the next save
        os.chmod(self.path, 0o644)
        mcpkey.save_key(KEY2)
        self.assertEqual(mcpkey.file_mode(), 0o600)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_keys_per_env_name_and_other_entries_survive(self):
        mcpkey.save_key(KEY)
        mcpkey.save_key(KEY2, {"key_env": "MY_MCP_KEY"})
        self.assertEqual(mcpkey.saved_key(), KEY)
        self.assertEqual(mcpkey.saved_key({"key_env": "MY_MCP_KEY"}), KEY2)
        mcpkey.delete_key()
        self.assertTrue(os.path.exists(self.path))
        self.assertEqual(mcpkey.saved_key({"key_env": "MY_MCP_KEY"}), KEY2)

    def test_empty_key_is_refused(self):
        with self.assertRaises(ValueError):
            mcpkey.save_key("  \n")
        self.assertFalse(os.path.exists(self.path))


class TestSourceOrder(KeyCase):
    def test_env_wins_over_saved_and_session_wins_over_both(self):
        mcpkey.save_key(KEY)
        os.environ["MCP_API_KEY"] = KEY2
        self.assertEqual(mcpkey.resolve(), (KEY2, "env"))
        mcpkey.set_session_key("typed-session-key-000000")
        self.assertEqual(mcpkey.resolve()[1], "session")
        mcpkey.clear_session_key()
        self.assertEqual(mcpkey.resolve()[1], "env")
        del os.environ["MCP_API_KEY"]
        self.assertEqual(mcpkey.resolve(), (KEY, "saved"))

    def test_configured_key_env(self):
        auth = {"key_env": "MY_MCP_KEY"}
        mcpkey.save_key(KEY, auth)
        os.environ["MCP_API_KEY"] = KEY2          # a different variable: not used
        self.assertEqual(mcpkey.resolve(auth), (KEY, "saved"))
        os.environ["MY_MCP_KEY"] = KEY2
        self.assertEqual(mcpkey.resolve(auth), (KEY2, "env"))

    def test_source_text_never_shows_the_key(self):
        mcpkey.save_key(KEY)
        text, src = mcpkey.source_text()
        self.assertEqual(src, "saved")
        self.assertNotIn(KEY, text)
        self.assertIn(mask(KEY), text)
        self.assertIn(self.path, text)
        os.environ["MCP_API_KEY"] = KEY2
        text, src = mcpkey.source_text()
        self.assertIn("$MCP_API_KEY", text)
        self.assertNotIn(KEY2, text)

    def test_headers_use_the_resolved_key(self):
        mcpkey.save_key(KEY)
        self.assertEqual(auth_headers({"style": "x-api-key"}), {"X-API-Key": KEY})
        self.assertEqual(auth_headers({"style": "bearer"}), {"Authorization": f"Bearer {KEY}"})
        self.assertEqual(auth_headers({"style": "header", "header_name": "X-MCP-Key"}), {"X-MCP-Key": KEY})
        self.assertEqual(auth_headers({"style": "none"}), {})


class TestConnectionTest(KeyCase):
    def settings(self, **auth):
        return {"url": "https://mcp.example/mcp", "auth": dict({"style": "x-api-key"}, **auth)}

    def test_ok_lists_tools(self):
        mcpkey.save_key(KEY)
        srv = AuthServer(TOOLS, KEY)
        res = mcpkey.test_connection(self.settings(), http=http_for(srv))
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["tools"], 2)
        self.assertEqual(res["names"], ["search", "charlie_mem"])
        self.assertEqual(res["server"], "fake-mcp")
        self.assertEqual(res["key_source"], "saved")
        lines = "\n".join(mcpkey.describe_test(res))
        self.assertIn("2 tools", lines)
        self.assertIn("charlie_mem", lines)

    def test_bearer_and_custom_header(self):
        mcpkey.save_key(KEY)
        res = mcpkey.test_connection(self.settings(style="bearer"), http=http_for(AuthServer(TOOLS, KEY, bearer=True)))
        self.assertTrue(res["ok"], res)
        res = mcpkey.test_connection(self.settings(style="header", header_name="X-MCP-Key"),
                                     http=http_for(AuthServer(TOOLS, KEY, header="X-MCP-Key")))
        self.assertTrue(res["ok"], res)

    def test_auth_error_is_clear_and_has_no_key(self):
        mcpkey.save_key(KEY2)
        res = mcpkey.test_connection(self.settings(), http=http_for(AuthServer(TOOLS, KEY)))
        self.assertFalse(res["ok"])
        self.assertTrue(res["auth_error"], res)
        lines = "\n".join(mcpkey.describe_test(res))
        self.assertIn("Auth error", lines)
        self.assertIn("saved key was refused", lines)
        self.assertNotIn(KEY2, lines + json.dumps(res))

    def test_no_key_and_wrong_style(self):
        res = mcpkey.test_connection(self.settings(), http=http_for(AuthServer(TOOLS, KEY)))
        self.assertTrue(res["auth_error"])
        self.assertIn("No key is set", "\n".join(mcpkey.describe_test(res)))
        mcpkey.save_key(KEY)
        res = mcpkey.test_connection(self.settings(style="bearer"), http=http_for(AuthServer(TOOLS, KEY)))
        self.assertTrue(res["auth_error"])
        self.assertIn("auth style", "\n".join(mcpkey.describe_test(res)))

    def test_unreachable_and_no_url(self):
        res = mcpkey.test_connection(self.settings(), http=http_for(FakeMCPServer(TOOLS, down=True)))
        self.assertFalse(res["ok"])
        self.assertFalse(res["auth_error"])
        self.assertIn("Could not connect", mcpkey.describe_test(res)[0])
        res = mcpkey.test_connection({"url": ""})
        self.assertEqual(res["error"], "no MCP URL set")


class TestMenu(KeyCase):
    def run_menu(self, answers, keys=(), settings=None, srv=None):
        settings = settings if settings is not None else {"url": "https://mcp.example/mcp", "enabled": True}
        inputs, keys = list(answers), list(keys)
        out = []
        saved = []
        mcpmenu.run_menu(settings, input_fn=lambda p="": inputs.pop(0), out=out.append,
                         getpass_fn=lambda p="": keys.pop(0), save_fn=lambda: saved.append(json.dumps(settings)),
                         http=http_for(srv or AuthServer(TOOLS, KEY)))
        return settings, "\n".join(map(str, out)), saved

    def test_set_key_saved_then_tested_masked(self):
        settings, out, saved = self.run_menu(["2", "1", "", "0"], keys=[KEY])
        self.assertEqual(mcpkey.resolve(), (KEY, "saved"))
        self.assertIn(mask(KEY), out)
        self.assertIn("[ok] Connected", out)
        self.assertIn("2 tools", out)
        self.assertNotIn(KEY, out)
        self.assertNotIn(KEY, "".join(saved))
        self.assertEqual(mcpkey.file_mode(), 0o600)

    def test_session_only_key_is_not_written(self):
        settings, out, saved = self.run_menu(["2", "2", "", "0"], keys=[KEY])
        self.assertEqual(mcpkey.resolve(), (KEY, "session"))
        self.assertFalse(os.path.exists(self.path))
        self.assertIn("this session only", out)
        self.assertNotIn(KEY, out + "".join(saved))

    def test_env_override_is_reported(self):
        os.environ["MCP_API_KEY"] = KEY
        settings, out, _ = self.run_menu(["2", "1", "", "0"], keys=[KEY2])
        self.assertIn("still wins over the saved key", out)
        self.assertEqual(mcpkey.resolve()[1], "env")
        self.assertIn("from $MCP_API_KEY", out)

    def test_delete_and_empty_entry(self):
        mcpkey.save_key(KEY)
        _, out, _ = self.run_menu(["3", "", "2", "0"], keys=[""])
        self.assertIn("Saved MCP key deleted", out)
        self.assertIn("No key entered", out)
        self.assertEqual(mcpkey.resolve(), ("", "none"))

    def test_url_and_auth_style(self):
        mcpkey.save_key(KEY)
        settings, out, saved = self.run_menu(
            ["1", "ftp://nope", "1", "https://other.example/mcp", "", "4", "3", "X-MCP-Key", "", "0"],
            srv=AuthServer(TOOLS, KEY, header="X-MCP-Key"))
        self.assertIn("must start with http", out)
        self.assertEqual(settings["url"], "https://other.example/mcp")
        self.assertEqual(settings["auth"]["style"], "header")
        self.assertEqual(settings["auth"]["header_name"], "X-MCP-Key")
        self.assertIn("[ok] Connected", out)
        self.assertTrue(saved)
        self.assertNotIn(KEY, "".join(saved))
        for bad in ("bad header", "a:b"):
            self.assertTrue(mcpmenu.set_style({}, "header", bad))
        self.assertTrue(mcpmenu.set_style({}, "basic"))
        s = {}
        self.assertEqual(mcpmenu.set_style(s, "bearer"), "")
        self.assertEqual(s["auth"]["style"], "bearer")

    def test_test_option(self):
        mcpkey.save_key(KEY2)
        _, out, _ = self.run_menu(["5", "", "0"])
        self.assertIn("Auth error", out)
        self.assertNotIn(KEY2, out)


class TestKeyNeverLeaks(KeyCase):
    def test_cli_mcp_commands_never_print_or_store_the_key(self):
        from tests.helpers import fresh_store
        from nimlab import cli
        with fresh_store() as root:
            mcpkey.save_key(KEY)
            e = dict(os.environ)
            runs = []
            for args in (["mcp", "show"], ["mcp", "key-source"], ["status", "key"]):
                r = subprocess.run([sys.executable, "-m", "nimlab"] + args, cwd=ROOT, env=e, capture_output=True,
                                   text=True, timeout=60)
                runs.append(r.stdout + r.stderr)
            # the key on the command line is refused
            r = subprocess.run([sys.executable, "-m", "nimlab", "mcp", "set-key", KEY], cwd=ROOT, env=e,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 2)
            runs.append(r.stdout + r.stderr)
            # commands that save settings, against a throwaway config file
            cfg = os.path.join(root, "config_cluster.json")
            with open(os.path.join(ROOT, "config_cluster.json"), encoding="utf-8") as f:
                original = f.read()
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(original)
            buf = io.StringIO()
            with mock.patch.object(config, "CLUSTER_CONFIG", cfg), mock.patch.object(sys, "stdout", buf):
                self.assertEqual(cli.main(["mcp", "auth", "bearer"]), 0)
                self.assertEqual(cli.main(["mcp", "set-url", "https://127.0.0.1:9/mcp", "--no-test"]), 0)
                self.assertEqual(cli.main(["mcp", "show"]), 0)
                mcpkey.set_session_key(KEY2)
                cli.main(["mcp", "show"])
            runs.append(buf.getvalue())
            joined = "\n".join(runs)
            self.assertNotIn(KEY, joined)
            self.assertNotIn(KEY2, joined)
            self.assertIn(mask(KEY), joined)
            with open(cfg, encoding="utf-8") as f:
                doc = json.load(f)
            self.assertEqual(doc["mcp_settings"]["url"], "https://127.0.0.1:9/mcp")
            self.assertEqual(doc["mcp_settings"]["auth"]["style"], "bearer")
            # the project's own config was not touched
            with open(os.path.join(ROOT, "config_cluster.json"), encoding="utf-8") as f:
                self.assertEqual(f.read(), original)
            # nothing on disk in the data folder or the configs has the key
            for base in (root,):
                for dirpath, dirs, files in os.walk(base):
                    for fn in files:
                        with open(os.path.join(dirpath, fn), "rb") as f:
                            data = f.read()
                        self.assertNotIn(KEY.encode(), data, fn)
                        self.assertNotIn(KEY2.encode(), data, fn)

    def test_redact_knows_saved_and_session_keys(self):
        from nimlab.core import redact
        mcpkey.save_key(KEY)
        mcpkey.set_session_key(KEY2)
        text = redact(f"failed with header {KEY} and {KEY2}")
        self.assertNotIn(KEY, text)
        self.assertNotIn(KEY2, text)

    def test_server_replies_and_log_never_carry_the_key(self):
        from tests.test_server import ServerCase, wait_log
        from nimlab import server as S

        class Case(ServerCase):
            def runTest(self):
                pass
        mcpkey.save_key(KEY)
        case = Case()
        case.setUp()
        try:
            case.settings["log_to_console"] = True
            err = io.StringIO()
            with mock.patch.object(sys, "stderr", err):
                bodies = [case.call("/models")[2],
                          case.call("/chat/completions", {"model": "testbed",
                                                          "messages": [{"role": "user", "content": "hi"}]})[2],
                          case.call("/models", key="sk-testbed-wrongwrongwrongwrong")[2]]
                wait_log(3)
            for b in bodies:
                self.assertNotIn(KEY.encode(), b)
            with open(S.log_path(), encoding="utf-8") as f:
                self.assertNotIn(KEY, f.read())
            self.assertNotIn(KEY, err.getvalue())
        finally:
            for fn, args, kw in reversed(case._cleanups):
                fn(*args, **kw)
            case._cleanups.clear()


if __name__ == "__main__":
    unittest.main()
