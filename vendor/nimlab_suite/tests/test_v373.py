"""3.7.3: MCP tools open by default, auth style saved and shown, endpoint forms.

The MCP server's admin console decides which tools an endpoint exposes; the
lab filters nothing unless the optional local overrides say so. No network.
"""

import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock

from nimlab import cli, config, mcp, mcpkey, wizard
from tests.sandbox import FakeIO, lab

MCP_KEY = "mcpk-" + "z" * 32


def real_cli(argv, timeout=900, input_text=None, show=True):
    """The wizard's CLI hook, run in-process against the sandboxed config."""
    buf = io.StringIO()
    stdin = io.StringIO(input_text or "")
    with redirect_stdout(buf), redirect_stderr(io.StringIO()), mock.patch("sys.stdin", stdin), \
            mock.patch("getpass.getpass", side_effect=lambda *a, **k: (input_text or "").strip()):
        try:
            rc = cli.main(list(argv))
        except SystemExit as e:
            rc = e.code or 0
    return rc or 0, buf.getvalue()


class AuthStyleSavedAndShown(unittest.TestCase):
    """3.7.2 bug: picking '2) Authorization: Bearer' printed 'Auth style set to
    bearer' but the After line said 'auth x-api-key'. The choice was saved to
    mcp_settings.auth.style; the summary (and the step's default) read a
    top-level auth_style that is never written."""

    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        self.addCleanup(self._lab.__exit__, None, None, None)
        self.seen = []

        def fake_test(settings, http=None):
            self.seen.append(json.loads(json.dumps(settings)))
            return {"ok": True, "url": settings.get("url"), "tools": 0, "names": [], "tool_defs": [], "server": "fake",
                    "protocol": "", "auth_error": False, "error": "", "key_source": "saved"}
        p = mock.patch.object(mcpkey, "test_connection", side_effect=fake_test)
        p.start()
        self.addCleanup(p.stop)

    def run_step(self, style, header=None, rerun=False):
        answers = ["https://svn-dev.online/mcp-quill", "" if rerun else MCP_KEY, None if rerun else style]
        if style == "header" and not rerun:
            answers.append(header)
        fio = FakeIO(answers)
        w = wizard.Wizard(io=fio, cli=real_cli, sh=mock.Mock(return_value=0),
                          key_check=mock.Mock(return_value=(True, "ok")), env={})
        w.do_mcp()
        return w, fio

    def test_each_style_is_saved_and_shown(self):
        for style, shown, header in (("bearer", "auth bearer", None), ("x-api-key", "auth x-api-key", None),
                                     ("header", "auth header X-Quill-Key", "X-Quill-Key"),
                                     ("none", "auth none", None)):
            with self.subTest(style=style):
                w, fio = self.run_step(style, header)
                saved = config.load_cluster_config()["mcp_settings"]
                self.assertEqual(saved["auth"]["style"], style)
                if header:
                    self.assertEqual(saved["auth"]["header_name"], header)
                ok, summary = w.st_mcp()
                self.assertIn(shown, summary)
                self.assertIn("url https://svn-dev.online/mcp-quill", summary)

    def test_rerun_keeps_bearer(self):
        """Pressing Enter at the style question on a rerun keeps bearer (3.7.2's
        default read the missing auth_style and reset it to x-api-key)."""
        self.run_step("bearer")
        w, _ = self.run_step("bearer", rerun=True)
        self.assertEqual(config.load_cluster_config()["mcp_settings"]["auth"]["style"], "bearer")
        self.assertIn("auth bearer", w.st_mcp()[1])

    def test_connection_test_uses_the_chosen_style(self):
        self.run_step("bearer")
        self.assertTrue(self.seen, "the step ran no connection test")
        settings = self.seen[-1]
        self.assertEqual(settings["auth"]["style"], "bearer")
        h = mcp.MCPClient(settings)._headers()
        self.assertEqual(h.get("Authorization"), "Bearer " + MCP_KEY)
        self.assertNotIn("X-API-Key", h)

        self.run_step("header", "X-Quill-Key")
        h = mcp.MCPClient(self.seen[-1])._headers()
        self.assertEqual(h.get("X-Quill-Key"), MCP_KEY)
        self.assertNotIn("Authorization", h)


class ConfigMigration(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        self.addCleanup(self._lab.__exit__, None, None, None)

    def test_old_372_config_loads_and_drops_confirm_risky(self):
        raw = json.load(open(self.lab.cluster))
        ms = raw["mcp_settings"]
        ms.pop("blocked_tools", None)
        ms.update(confirm_risky_tools=True, confirm_tool_calls=True, allowed_tools=[])
        json.dump(raw, open(self.lab.cluster, "w"))
        with redirect_stderr(io.StringIO()), mock.patch.dict("os.environ", {"NIMLAB_CONFIG_READONLY": ""}):
            cfg = config.load_cluster_config()
        m = cfg["mcp_settings"]
        self.assertNotIn("confirm_risky_tools", json.load(open(self.lab.cluster))["mcp_settings"])
        self.assertFalse(m["confirm_tool_calls"])
        self.assertEqual(m["blocked_tools"], [])
        pol = mcp.ToolPolicy.from_settings(m, agent="Quill")
        self.assertTrue(pol.is_allowed("terminal"))
        self.assertTrue(pol.is_allowed("charlie_mem"))

    def test_star_and_empty_both_mean_all(self):
        for allowed in ([], ["*"], "*", None):
            pol = mcp.ToolPolicy.from_settings({"allowed_tools": allowed})
            self.assertTrue(pol.wildcard, allowed)
            self.assertTrue(pol.is_allowed("anything_at_all"))

    def test_defaults(self):
        m = config.DEFAULT_CLUSTER["mcp_settings"]
        self.assertEqual(m["allowed_tools"], [])
        self.assertEqual(m["blocked_tools"], [])
        self.assertFalse(m["confirm_tool_calls"])
        self.assertNotIn("confirm_risky_tools", m)
        shipped = json.load(open(config.CLUSTER_CONFIG))["mcp_settings"]
        self.assertEqual(shipped["blocked_tools"], [])
        self.assertFalse(shipped["confirm_tool_calls"])
        self.assertNotIn("confirm_risky_tools", shipped)


class SummaryAndTools(unittest.TestCase):
    TOOLS = [{"name": n, "description": ""} for n in ("quill_mem", "charlie_mem", "terminal")]

    def test_policy_lines_short_by_default_full_on_request(self):
        from nimlab import mcpmenu
        s = {"url": "https://svn-dev.online/mcp-quill", "own_memory_tool": "quill_mem"}
        short = "\n".join(mcpmenu.policy_lines(s, self.TOOLS, agent="Quill"))
        self.assertIn("[MCP] 3 tools from https://svn-dev.online/mcp-quill, all available", short)
        self.assertNotIn("charlie_mem", short.replace("like charlie_mem", ""))
        self.assertIn("nimlab mcp tools", short)
        full = "\n".join(mcpmenu.policy_lines(s, self.TOOLS, agent="Quill", full_list=True))
        for n in ("quill_mem", "charlie_mem", "terminal"):
            self.assertIn(n, full)

    def test_mcp_tools_command_exists(self):
        p = cli.build_parser()
        self.assertEqual(p.parse_args(["mcp", "tools"]).action, "tools")
        self.assertTrue(p.parse_args(["mcp", "test", "-v"]).verbose)

    def test_environment_does_not_disown_listed_mem_tools(self):
        from nimlab import environment
        src = open(environment.__file__).read()
        self.assertNotIn("(*_mem) are not yours", src)


if __name__ == "__main__":
    unittest.main()
