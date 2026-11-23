"""Self-admin tools: admin-only gating, masked secrets, snapshot + undo,
confirmation in a later message, and the audit log. Temp config only; the
CLI jobs (_run_cli) are faked, so no subprocess or service is started."""

import io
import json
import os
import stat
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import config, selfadmin as SA, server as S
from tests.sandbox import lab

NVKEY = "nvapi-" + "q" * 40


class FakeEntity:
    def __init__(self):
        self.reloads = 0
        self.cluster = config.load_cluster_config()

    def reload(self):
        self.reloads += 1
        self.cluster = config.load_cluster_config()


class FakeMCP:
    tools = [{"name": "weather", "description": "w", "inputSchema": {}}]

    def __init__(self):
        self.calls = []

    def call_tool(self, name, args):
        self.calls.append((name, args))
        return {"content": [{"type": "text", "text": "sunny"}], "isError": False}


def text(res):
    return res["content"][0]["text"]


class SelfAdminTests(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        os.environ["NVIDIA_API_KEY"] = NVKEY
        SA.clear_request()
        SA._pending.clear()
        self.cli = mock.patch.object(SA, "_run_cli", side_effect=lambda argv, timeout=300: (True, "ran " + " ".join(argv)))
        self.run_cli = self.cli.start()
        self.entity = FakeEntity()

    def tearDown(self):
        self.cli.stop()
        SA.clear_request()
        self._lab.__exit__(None, None, None)

    def box(self, admin, who="vin", mcp=None):
        SA.set_request(admin, who, "test")
        return SA.ToolBox(self.entity, mcp=mcp)

    def next_message(self, admin=True, who="vin"):
        SA.set_request(admin, who, "test")   # a new request id, as a new chat turn has

    # -- gating ------------------------------------------------------------
    def test_non_admin_gets_no_tools_and_is_refused(self):
        mcp = FakeMCP()
        b = self.box(False, "stranger", mcp)
        self.assertEqual(b.admin_names, set())
        self.assertEqual([t["name"] for t in b.tools], ["weather"])
        res = b.call_tool("self_set_role", {"role": "chat", "model": "x"})
        self.assertTrue(res["isError"])
        self.assertIn("only for the testbed's admins", text(res))
        self.assertEqual(mcp.calls, [])                       # never forwarded to MCP
        self.assertEqual(SA.audit_tail()[-1]["result"][:7], "refused")
        self.assertEqual(text(b.call_tool("weather", {})), "sunny")
        self.assertTrue(self.box(False).call_tool("nope", {})["isError"])   # no MCP: an error, not a crash

    def test_others_read_gives_read_tools_only(self):
        cfg = config.load_json(config.CLUSTER_CONFIG, {})
        cfg.setdefault("self_admin", {})["others_read"] = True
        config.save_json(config.CLUSTER_CONFIG, cfg)
        self.entity.reload()
        b = self.box(False)
        self.assertEqual(b.admin_names, set(SA.READ_TOOLS))
        self.assertTrue(b.call_tool("self_undo", {})["isError"])

    def test_admin_gets_write_tools_shell_only_when_on(self):
        b = self.box(True)
        self.assertTrue(set(SA.WRITE_TOOLS) <= b.admin_names)
        self.assertFalse(set(SA.SHELL_TOOLS) & b.admin_names)
        cfg = config.load_json(config.CLUSTER_CONFIG, {})
        cfg.setdefault("self_admin", {})["shell"] = True
        config.save_json(config.CLUSTER_CONFIG, cfg)
        self.entity.reload()
        self.assertTrue(set(SA.SHELL_TOOLS) <= self.box(True).admin_names)

    def test_disabled_means_no_tools_even_for_admin(self):
        cfg = config.load_json(config.CLUSTER_CONFIG, {})
        cfg.setdefault("self_admin", {})["enabled"] = False
        config.save_json(config.CLUSTER_CONFIG, cfg)
        self.entity.reload()
        self.assertEqual(self.box(True).admin_names, set())

    def test_box_built_for_admin_refuses_a_non_admin_call(self):
        b = self.box(True)
        self.next_message(admin=False, who="someone")
        res = b.call_tool("self_set_prompt", {"role": "chat", "text": "x"})
        self.assertTrue(res["isError"])
        self.assertEqual(SA.audit_tail()[-1]["who"], "someone")

    def test_server_admin_key_vs_normal_key(self):
        SA.new_admin_key()
        self.assertEqual(stat.S_IMODE(os.stat(SA.admin_key_path()).st_mode), 0o600)
        app = types.SimpleNamespace(settings={"api_key": "user-key-123456"})
        S.TestbedApp.check_key(app, {"Authorization": f"Bearer {SA.load_admin_key()}", "X-Testbed-User": "vin"})
        self.assertEqual((SA.current().admin, SA.current().who), (True, "vin"))
        S.TestbedApp.check_key(app, {"Authorization": "Bearer user-key-123456"})
        self.assertFalse(SA.current().admin)
        with self.assertRaises(S.ApiError):
            S.TestbedApp.check_key(app, {"Authorization": "Bearer nimlab-admin-wrong"})
        self.assertFalse(SA.is_admin_key(""))

    def test_terminal_is_admin(self):
        SA.set_local_admin()
        self.assertTrue(SA.current().admin)
        self.assertEqual(SA.current().source, "terminal")

    # -- secrets -----------------------------------------------------------
    def test_config_and_status_mask_secrets(self):
        cfg = config.load_json(config.CLUSTER_CONFIG, {})
        cfg.setdefault("mcp_settings", {})["auth_value"] = "mcp-very-secret-value"
        cfg["mcp_settings"]["max_tokens"] = 512
        config.save_json(config.CLUSTER_CONFIG, cfg)
        b = self.box(True)
        out = text(b.call_tool("self_get_config", {"section": "mcp_settings"}))
        self.assertNotIn("mcp-very-secret-value", out)
        self.assertIn("***alue", out)
        self.assertIn("512", out)
        self.assertNotIn(NVKEY, text(b.call_tool("self_status", {})))

    def test_scrub_catches_env_and_file_secrets(self):
        with open(self.lab.env_file, "w") as f:
            f.write("export OTHER_KEY='file-secret-abcdef12345'\n")
        out = SA.scrub(f"key {NVKEY} and file-secret-abcdef12345 and nvapi-{'z' * 30}")
        self.assertNotIn(NVKEY, out)
        self.assertNotIn("file-secret-abcdef12345", out)
        self.assertNotIn("z" * 30, out)

    def test_secrets_cannot_be_set_through_chat(self):
        b = self.box(True)
        res = b.call_tool("self_set_setting", {"section": "mcp_settings", "key": "api_key", "value": "x"})
        self.assertIn("Secrets are not set through chat", text(res))
        res = b.call_tool("self_server_set", {"key": "api_key", "value": "x"})
        self.assertTrue(res["isError"])
        res = b.call_tool("self_set_setting", {"section": "self_admin", "key": "shell", "value": True})
        self.assertIn("only be changed in setup or the CLI", text(res))

    def test_audit_masks_args_and_results(self):
        b = self.box(True)
        role = sorted(config.load_prompts())[0]
        b.call_tool("self_set_prompt", {"role": role, "text": f"use {NVKEY}"})
        with open(os.path.join(SA._dir(), "audit.jsonl")) as f:
            raw = f.read()
        self.assertNotIn(NVKEY, raw)
        rec = SA.audit_tail()[-1]
        self.assertEqual((rec["who"], rec["tool"], rec["ok"]), ("vin", "self_set_prompt", True))
        self.assertEqual(len(SA.audit_tail()), 1)        # read tools are not audited
        b.call_tool("self_status", {})
        self.assertEqual(len(SA.audit_tail()), 1)

    # -- snapshot + undo --------------------------------------------------
    def test_set_prompt_then_undo_restores_file(self):
        with open(config.SYSTEM_PROMPTS) as f:
            before = f.read()
        role = sorted(config.load_prompts())[0]
        b = self.box(True)
        res = b.call_tool("self_set_prompt", {"role": role, "text": "Be brief."})
        self.assertIn(f"Replaced the {role} prompt", text(res))
        self.assertIn("undo the last change", text(res))
        self.assertEqual(config.load_json(config.SYSTEM_PROMPTS, {})[role], "Be brief.")
        self.assertEqual(self.entity.reloads, 1)
        res = b.call_tool("self_undo", {})
        self.assertIn(f"Undid: set prompt {role}", text(res))
        with open(config.SYSTEM_PROMPTS) as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(text(b.call_tool("self_undo", {})), "Nothing to undo.")

    def test_server_setting_undo(self):
        before = S.load_settings().get("model_name")
        b = self.box(True)
        b.call_tool("self_server_set", {"key": "model_name", "value": "labby"})
        self.assertEqual(S.load_settings()["model_name"], "labby")
        SA.undo()
        self.assertEqual(S.load_settings().get("model_name"), before)
        res = b.call_tool("self_server_set", {"key": "lan", "value": True})
        self.assertIn("CONFIRMATION NEEDED", text(res))

    def test_set_role_checks_catalog(self):
        b = self.box(True)
        with mock.patch("nimlab.rolemenu.model_lists", return_value=(["meta/llama-3.3-70b-instruct"],
                                                                     ["meta/llama-3.3-70b-instruct", "x/new"])):
            res = b.call_tool("self_set_role", {"role": "nonsense", "model": "x/new"})
            self.assertIn("Unknown role", text(res))
            from nimlab import roles as R
            key = R.ROLE_DEFS[0].key
            res = b.call_tool("self_set_role", {"role": key, "model": "llama-3.3"})
            self.assertIn("Did you mean: meta/llama-3.3-70b-instruct", text(res))
            res = b.call_tool("self_set_role", {"role": key, "model": "x/new"})
            self.assertIn(f"Changed role {key}", text(res))
            self.assertIn("not 200-verified", text(res))
        self.assertEqual(config.load_json(config.CLUSTER_CONFIG, {})["roles"][key]["model"], "x/new")
        SA.undo()
        self.assertNotEqual(config.load_json(config.CLUSTER_CONFIG, {})["roles"].get(key, {}).get("model"), "x/new")

    def test_snapshots_are_capped(self):
        for i in range(SA.SNAP_KEEP + 5):
            SA.snapshot(f"s{i}")
        self.assertEqual(len(os.listdir(SA._dir("snapshots"))), SA.SNAP_KEEP)

    # -- confirmation ------------------------------------------------------
    def test_risky_action_needs_yes_in_a_later_message(self):
        b = self.box(True)
        res = b.call_tool("self_service", {"action": "stop"})
        self.assertIn("CONFIRMATION NEEDED", text(res))
        code = text(res).split('confirm_code="')[1].split('"')[0]
        self.run_cli.assert_not_called()
        same = b.call_tool("self_service", {"action": "stop", "confirm_code": code})
        self.assertIn("has to confirm in a new message", text(same))
        self.run_cli.assert_not_called()
        self.next_message()
        other = b.call_tool("self_service", {"action": "restart", "confirm_code": code})
        self.assertIn("different action", text(other))
        ok = b.call_tool("self_service", {"action": "stop", "confirm_code": code})
        self.assertFalse(ok["isError"])
        self.run_cli.assert_called_once_with(["service", "stop"], 60)
        again = b.call_tool("self_service", {"action": "stop", "confirm_code": code})   # a code works once
        self.assertIn("CONFIRMATION NEEDED", text(again))

    def test_confirmation_belongs_to_the_asker_and_expires(self):
        b = self.box(True, "vin")
        code = text(b.call_tool("self_tunnel", {"action": "off"})).split('confirm_code="')[1].split('"')[0]
        self.next_message(who="mallory")
        self.assertIn("different action", text(b.call_tool("self_tunnel", {"action": "off", "confirm_code": code})))
        self.next_message(who="vin")
        SA._pending[code]["at"] -= SA.PENDING_TTL + 1
        self.assertIn("expired", text(b.call_tool("self_tunnel", {"action": "off", "confirm_code": code})))

    def test_risky_setting_needs_confirmation_plain_one_does_not(self):
        cfg = config.load_json(config.CLUSTER_CONFIG, {})
        sec = next(k for k, v in cfg.items() if isinstance(v, dict) and k != "self_admin" and k != "roles")
        b = self.box(True)
        res = b.call_tool("self_set_setting", {"section": sec, "key": "enabled", "value": "false"})
        self.assertIn("CONFIRMATION NEEDED", text(res))
        res = b.call_tool("self_set_setting", {"section": sec, "key": "note_field", "value": "7"})
        self.assertIn(f"Changed {sec}.note_field", text(res))
        self.assertEqual(config.load_json(config.CLUSTER_CONFIG, {})[sec]["note_field"], 7)

    def test_restart_answers_first(self):
        b = self.box(True)
        code = text(b.call_tool("self_service", {"action": "restart"})).split('confirm_code="')[1].split('"')[0]
        self.next_message()
        with mock.patch.object(SA.threading, "Timer") as timer:
            res = b.call_tool("self_service", {"action": "restart", "confirm_code": code})
        self.assertIn("Restarting the service in 2 seconds", text(res))
        timer.assert_called_once()
        self.run_cli.assert_not_called()

    def test_run_and_status_service_need_no_confirmation(self):
        b = self.box(True)
        self.assertIn("ran grpc check", text(b.call_tool("self_run", {"action": "grpc_check"})))
        self.assertIn("ran service status", text(b.call_tool("self_service", {"action": "status"})))

    # -- shell -------------------------------------------------------------
    def test_shell_refuses_outside_paths_and_needs_confirmation(self):
        cfg = config.load_json(config.CLUSTER_CONFIG, {})
        cfg.setdefault("self_admin", {})["shell"] = True
        config.save_json(config.CLUSTER_CONFIG, cfg)
        self.entity.reload()
        b = self.box(True)
        for bad in ("cat /etc/passwd", "cat ../x", "cat ~/.nimlab_env", "printenv", "curl http://x"):
            self.assertIn("Refused", text(b.call_tool("self_shell", {"command": bad})), bad)
        self.assertIn("CONFIRMATION NEEDED", text(b.call_tool("self_shell", {"command": "ls nimlab"})))
        self.assertIn("Refused", text(b.call_tool("self_edit_file", {"path": "../x", "old": "a", "new": "b"})))

    # -- CLI ---------------------------------------------------------------
    def test_cli(self):
        def call(action, *values):
            out = io.StringIO()
            with redirect_stdout(out):
                code = SA.cmd_selfadmin(types.SimpleNamespace(action=action, values=list(values)))
            return code, out.getvalue()
        self.assertEqual(call("shell", "on")[0], 0)
        self.assertTrue(SA.settings(config.load_json(config.CLUSTER_CONFIG, {}))["shell"])
        self.assertEqual(call("shell")[0], 2)
        code, out = call("admin-key")
        k = SA.load_admin_key()
        self.assertIn(k, out)                                   # shown once, on purpose
        code, out = call("status")
        self.assertNotIn(k, out)
        self.assertIn("***" + k[-4:], out)
        self.assertIn("Nothing to undo", call("undo")[1])
        self.assertEqual(call("audit")[0], 0)
        self.assertEqual(call("off")[0], 0)
        self.assertFalse(SA.settings(config.load_json(config.CLUSTER_CONFIG, {}))["enabled"])


if __name__ == "__main__":
    unittest.main()
