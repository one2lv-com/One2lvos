"""3.8.1 Telegram rollout: setMyCommands, /model, /remember, /voice, /service,
/cancel, inline keyboard buttons (callback_query) and inline mode."""

import json
import re
import threading
import time
import unittest
from unittest import mock

from tests.test_v380 import LabCase


class Tg381(LabCase):
    OWNER, OTHER, STRANGER = 1111, 2222, 3333

    def setUp(self):
        super().setUp()
        from nimlab import telegram as TG, tgcmds, tgui
        self.TG, self.tg, self.ui = TG, tgcmds, tgui
        self.calls, self.sent, self.cli = [], [], []
        self.reply = "quill reply"
        self.chat_gate = None

        class Api:
            def __call__(api, url, data, headers, timeout):
                method = url.rsplit("/", 1)[1]
                params = json.loads(data) if data else {}
                self.calls.append((method, params))
                if method == "sendMessage":
                    self.sent.append(re.sub(r"\\(.)", r"\1", params.get("text", "")))
                    return 200, json.dumps({"ok": True, "result": {"message_id": 1}}).encode()
                return 200, json.dumps({"ok": True, "result": True}).encode()

        class Backend:
            def chat(b, messages, user, admin=False):
                self.backend_calls.append((messages[-1]["content"], user, admin))
                if self.chat_gate:
                    self.chat_gate.wait(5)
                return self.reply
        self.backend_calls = []
        self.ts = {"allow": [self.OWNER, self.OTHER], "owner": self.OWNER}
        self.conn = TG.Connector(TG.Bot("123456789:AAE" + "x" * 32, http=Api()), Backend(), self.ts,
                                 save=lambda: None, log=lambda *a: None)
        for name, fn in (("_spawn", lambda f: f()),
                         ("run_cli", lambda args, timeout: self.cli.append(list(args)) or "cli: " + " ".join(args))):
            pm = mock.patch.object(tgcmds, name, fn)
            pm.start()
            self.addCleanup(pm.stop)
        pm = mock.patch.object(tgui, "restart_later", lambda fn, delay=2.0: fn())
        pm.start()
        self.addCleanup(pm.stop)

    # helpers
    def say(self, text, uid=None):
        uid = uid or self.OWNER
        self.sent.clear()
        self.calls.clear()
        self.conn.handle({"update_id": 1, "message": {"message_id": 5, "from": {"id": uid},
                                                       "chat": {"id": uid, "type": "private"}, "text": text}})
        return self.sent

    def buttons(self):
        """[(text, callback_data)] of the last message that had buttons."""
        for method, p in reversed(self.calls):
            kb = (p.get("reply_markup") or {}).get("inline_keyboard")
            if kb:
                return [(b["text"], b["callback_data"]) for row in kb for b in row]
        return []

    def press(self, data, uid=None):
        uid = uid or self.OWNER
        self.sent.clear()
        self.calls.clear()
        self.conn.handle({"update_id": 2, "callback_query": {
            "id": "cq1", "from": {"id": uid}, "data": data,
            "message": {"message_id": 9, "chat": {"id": uid, "type": "private"}}}})
        return self.calls

    def answered(self):
        return [p for m, p in self.calls if m == "answerCallbackQuery"]

    def edited(self):
        return [p["text"] for m, p in self.calls if m == "editMessageText"]


class CommandMenu(Tg381):
    def test_register_default_and_owner_scope(self):
        log = []
        self.assertEqual(self.ui.register_commands(self.conn.bot, self.ts, log=log.append), "default+owner")
        sets = [p for m, p in self.calls if m == "setMyCommands"]
        self.assertEqual(len(sets), 2)
        self.assertEqual(sets[0]["scope"], {"type": "default"})
        self.assertEqual(sets[1]["scope"], {"type": "chat", "chat_id": self.OWNER})
        owner_cmds = [c["command"] for c in sets[1]["commands"]]
        self.assertEqual(owner_cmds, ["start", "status", "health", "test", "model", "roles", "recall", "remember", "mcp",
                                      "tunnel", "jobs", "heartbeat", "voice", "autoplay", "bugs", "logs",
                                      "service", "new", "cancel", "help"])
        default = [c["command"] for c in sets[0]["commands"]]
        self.assertNotIn("service", default)
        self.assertIn("remember", default)
        self.assertIn("[ok] Telegram command menu set", log[0])

    def test_menu_matches_readme_and_botfather_text(self):
        import os
        with open(os.path.join(self.tg.PROJECT, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        for c, d in self.ui.MENU:
            self.assertIn(f"{c} - {d}", readme)
        self.assertEqual(self.tg.botfather_text().splitlines()[0], "start - Hello and the command list")
        self.assertIn("setcommands` is not needed", readme.replace("/setcommands", "setcommands"))
        # every description fits Telegram's limits (1-32 chars command, 1-256 description)
        for c, d in self.ui.MENU:
            self.assertRegex(c, r"^[a-z0-9_]{1,32}$")
            self.assertTrue(3 <= len(d) <= 256)

    def test_no_owner_only_default_and_failure_never_raises(self):
        self.ts["owner"] = None
        self.assertEqual(self.ui.register_commands(self.conn.bot, self.ts, log=lambda *a: None), "default")

        class Bad:
            def call(self, *a, **k):
                raise RuntimeError("Bad Request")
        log = []
        self.assertEqual(self.ui.register_commands(Bad(), self.ts, log=log.append), "failed")
        self.assertIn("setMyCommands failed", log[0])
        self.assertEqual(self.ui.register_commands(Bad(), {"set_commands": False}), "off")

    def test_allowed_updates_include_buttons_and_inline(self):
        self.assertEqual(self.TG.ALLOWED_UPDATES, ["message", "edited_message", "callback_query", "inline_query"])
        self.conn.offset = 10
        self.calls.clear()
        self.conn.confirm()
        self.assertEqual(self.calls[0][1]["allowed_updates"], self.TG.ALLOWED_UPDATES)

    def test_run_registers_commands_on_start(self):
        import inspect
        src = inspect.getsource(self.TG.run)
        self.assertIn("tgui.register_commands(bot, t", src)


class Commands(Tg381):
    def test_model_view_for_anyone_switch_owner_only(self):
        with mock.patch.object(self.ui, "model_text", return_value="Exposed model: testbed"):
            out = self.say("/model", uid=self.OTHER)
            self.assertEqual(out, ["Exposed model: testbed"])
            self.assertIn("Switch: /model primary", self.say("/model")[0])
        self.assertEqual(self.say("/model primary x", uid=self.OTHER), ["Only the owner can switch the model."])
        self.ts["model_switch"] = False
        self.assertIn("is off", self.say("/model primary x")[0])

    def test_model_primary_confirm_then_switch(self):
        from nimlab import selfadmin
        with mock.patch.object(selfadmin, "check_role", return_value=(True, "")):
            out = self.say("/model primary meta/llama-3.3-70b-instruct")
        self.assertIn("Make meta/llama-3.3-70b-instruct the primary", out[0])
        b = self.buttons()
        self.assertEqual([t for t, _ in b], ["Switch", "Cancel"])
        with mock.patch.object(selfadmin, "set_role", return_value=(True, "Changed role persona: a -> b.")) as sr, \
                mock.patch.object(selfadmin, "snapshot") as snap, mock.patch.object(selfadmin, "audit") as aud:
            self.press(b[1][1], uid=self.OTHER)      # someone else's button
            sr.assert_not_called()
            self.assertIn("not yours", self.answered()[0]["text"])
            self.press(b[0][1])
            sr.assert_called_once_with("persona", "meta/llama-3.3-70b-instruct")
            snap.assert_called_once()
            aud.assert_called_once()
        self.assertIn("Changed role persona", self.edited()[0])
        self.press(b[0][1])                          # one-time: pressing again expires
        self.assertIn("expired", self.answered()[0]["text"])

    def test_model_primary_not_in_catalog(self):
        from nimlab import selfadmin
        with mock.patch.object(selfadmin, "check_role", return_value=(False, "'zz' is not in the catalog.")):
            self.assertEqual(self.say("/model primary zz"), ["'zz' is not in the catalog."])
        self.assertEqual(self.buttons(), [])

    def test_model_name_rename_and_cancel(self):
        from nimlab import server as S
        self.assertIn("letters, digits", self.say("/model name bad name!")[0])
        self.say("/model name quill-stack")
        yes, no = self.buttons()
        self.press(no[1])
        self.assertEqual(self.edited(), ["Cancelled. Nothing was changed."])
        self.assertEqual(S.main_model(S.load_settings()), "testbed")
        self.say("/model name quill-stack")
        self.press(self.buttons()[0][1])
        self.assertEqual(S.main_model(S.load_settings()), "quill-stack")
        self.assertIn("testbed -> quill-stack", self.edited()[0])

    def test_remember_runs_memory_add_scoped_to_the_user(self):
        self.assertIn("Usage", self.say("/remember")[0])
        out = self.say("/remember My name is SeVin", uid=self.OTHER)
        self.assertEqual(self.cli[-1], ["memory", "add", "--", "--user", f"telegram:{self.OTHER}",
                                        "My name is SeVin"])
        self.assertEqual(out[-1], "cli: memory add -- --user telegram:2222 My name is SeVin")
        self.assertIn("too long", self.say("/remember " + "x" * 2001)[0])

    def test_memory_add_cli_parses(self):
        from nimlab import cli
        a = cli.build_parser().parse_args(["memory", "add", "--", "--user", "telegram:1", "I like tea"])
        self.assertEqual(a.action, "add")
        self.assertEqual(a.values, ["--user", "telegram:1", "I like tea"])

    def test_voice_toggle_owner_only_and_saved(self):
        saved = []
        with mock.patch.object(self.TG, "save_keys", lambda **kw: saved.append(kw)):
            self.assertEqual(self.say("/voice", uid=self.OTHER), ["That command is for the owner only."])
            self.assertIn("Spoken replies are on", self.say("/voice")[0])
            self.assertTrue(self.ts["voice_replies"])
            self.assertIn("are off", self.say("/voice off")[0])
            self.assertIn("are off", self.say("/voice status")[0])
            self.assertIn("Usage", self.say("/voice loud")[0])
        self.assertEqual(saved, [{"voice_replies": True}, {"voice_replies": False}])

    def test_service_status_and_restart_with_confirm(self):
        self.assertEqual(self.say("/service", uid=self.OTHER), ["That command is for the owner only."])
        self.assertEqual(self.say("/service")[-1], "cli: service status")
        out = self.say("/service restart")
        self.assertIn("Restart the background service?", out[0])
        self.assertNotIn(["service", "restart"], self.cli)
        yes, no = self.buttons()
        self.assertEqual(yes[0], "Restart")
        self.press(yes[1])
        self.assertEqual(self.cli[-1], ["service", "restart"])
        self.assertEqual(self.answered()[0]["text"], "Restarting")
        self.assertIn("Usage", self.say("/service stop")[0])

    def test_cancel_with_nothing_in_progress(self):
        self.assertEqual(self.say("/cancel", uid=self.OTHER), ["Nothing to stop: no reply is in progress."])

    def test_cancel_drops_the_reply_in_progress(self):
        self.conn.threaded = True
        self.chat_gate = threading.Event()
        self.say("tell me a long story")
        for _ in range(100):
            if self.backend_calls:
                break
            time.sleep(0.01)
        self.assertTrue(self.backend_calls)               # Quill is thinking; the poller is free
        out = self.say("/cancel")
        self.assertEqual(out, ["Stopped. That reply won't be sent."])
        self.chat_gate.set()
        for _ in range(100):
            if self.OWNER not in self.conn.inflight:
                break
            time.sleep(0.01)
        time.sleep(0.05)
        self.assertNotIn("quill reply", self.sent)
        self.assertEqual(self.conn.history.get(self.OWNER, []), [])

    def test_unthreaded_reply_still_sends(self):
        self.assertIn("quill reply", self.say("hello"))
        self.assertNotIn(self.OWNER, self.conn.inflight)

    def test_help_lists_the_new_commands_owner_and_others(self):
        own = self.say("/help")[0]
        for c in ("/model", "/remember", "/voice", "/service", "/cancel", "Inline:"):
            self.assertIn(c, own)
        other = self.say("/help", uid=self.OTHER)[0]
        self.assertIn("/remember", other)
        self.assertNotIn("/service", other)


class Buttons(Tg381):
    def test_heartbeat_buttons_run_and_toggle(self):
        from nimlab import heartbeat as HB
        self.say("/heartbeat")
        b = self.buttons()
        self.assertEqual(b[0][0], "Run a heartbeat now")
        acts = sorted(HB.load_actions(), key=lambda x: (x.get("priority", 3), x["name"]))
        self.assertEqual(len(b), 1 + len(acts))
        name = acts[0]["name"]
        before = bool(HB.get_action(name).get("enabled"))
        self.press(b[1][1])
        self.assertEqual(bool(HB.get_action(name).get("enabled")), not before)
        self.assertIn("Heartbeat:", self.edited()[0])
        self.press(b[1][1])                             # toggles can be pressed again
        self.assertEqual(bool(HB.get_action(name).get("enabled")), before)
        self.press(b[0][1])
        self.assertEqual(self.cli[-1], ["heartbeat", "run-now"])

    def test_stranger_and_unknown_and_expired_buttons(self):
        self.say("/service restart")
        yes = self.buttons()[0][1]
        self.press(yes, uid=self.STRANGER)
        self.assertEqual(self.answered()[0]["text"], "This bot is private.")
        self.press("nl:doesnotexist")
        self.assertIn("expired", self.answered()[0]["text"])
        self.press("garbage")
        self.assertIn("expired", self.answered()[0]["text"])
        self.conn._buttons[yes[3:]]["exp"] = 0
        self.press(yes)
        self.assertIn("expired", self.answered()[0]["text"])
        self.assertNotIn(["service", "restart"], self.cli)

    def test_a_failing_button_action_never_raises(self):
        tok = self.ui.token(self.conn, self.OWNER, "hb_toggle", {"name": "nope"})
        with mock.patch.dict(self.ui.ACTIONS, {"hb_toggle": lambda *a: 1 / 0}):
            self.press(tok)
        self.assertIn("Failed", self.answered()[0]["text"])
        self.assertIn("ZeroDivisionError", self.sent[-1])

    def test_a_confirmation_ends_only_its_own_pair(self):
        self.say("/heartbeat")
        hb = self.buttons()
        self.say("/service restart")
        yes, no = self.buttons()
        self.press(no[1])
        self.press(yes[1])
        self.assertIn("expired", self.answered()[0]["text"])      # its partner went with it
        self.press(hb[0][1])                                       # other buttons still work
        self.assertEqual(self.cli[-1], ["heartbeat", "run-now"])

    def test_token_store_is_bounded(self):
        for i in range(self.ui.MAX_TOKENS + 50):
            self.ui.token(self.conn, self.OWNER, "dismiss")
        self.assertLessEqual(len(self.conn._buttons), self.ui.MAX_TOKENS)
        self.assertLessEqual(len(self.ui.token(self.conn, 1, "dismiss")), 64)   # Telegram's callback_data cap


class Inline(Tg381):
    def ask(self, q, uid=None, run=None):
        self.calls.clear()
        iq = {"id": "iq1", "from": {"id": uid or self.OWNER}, "query": q}
        if run:
            return self.ui.handle_inline(self.conn, iq, run=run)
        self.conn.handle({"update_id": 3, "inline_query": iq})
        return [p for m, p in self.calls if m == "answerInlineQuery"]

    def test_owner_gets_quills_answer(self):
        ans = self.ask("what is NIM?")
        self.assertEqual(len(ans), 1)
        r = ans[0]["results"][0]
        self.assertEqual(r["input_message_content"]["message_text"], "quill reply")
        self.assertTrue(ans[0]["is_personal"])
        self.assertEqual(self.backend_calls[-1], ("what is NIM?", f"telegram:{self.OWNER}", False))

    def test_others_refused_unless_allowlist(self):
        ans = self.ask("hi", uid=self.OTHER)
        self.assertEqual(ans[0]["results"], [])
        self.assertEqual(self.backend_calls, [])
        self.ts["inline"] = "allowlist"
        self.assertEqual(len(self.ask("hi", uid=self.OTHER)[0]["results"]), 1)
        self.assertEqual(self.ask("hi", uid=self.STRANGER)[0]["results"], [])
        self.ts["inline"] = "off"
        self.assertEqual(self.ask("hi")[0]["results"], [])

    def test_empty_query_offers_the_chat(self):
        ans = self.ask("")
        self.assertEqual(ans[0]["results"], [])
        self.assertEqual(ans[0]["button"]["start_parameter"], "inline")
        self.assertEqual(self.backend_calls, [])

    def test_slow_answer_falls_back_fast(self):
        res = self.ask("slow one", run=lambda fn, timeout: None)     # deadline passed, no answer
        self.assertEqual(res[0]["id"], "ask")
        self.assertEqual(res[0]["input_message_content"]["message_text"], "slow one")
        self.chat_gate = threading.Event()
        self.ts["inline_timeout"] = 0.05
        t0 = time.time()
        res = self.ui.handle_inline(self.conn, {"id": "x", "from": {"id": self.OWNER}, "query": "q"})
        self.assertLess(time.time() - t0, 2)
        self.assertEqual(res[0]["id"], "ask")
        self.chat_gate.set()

    def test_threaded_inline_does_not_block_the_poller(self):
        self.conn.threaded = True
        self.chat_gate = threading.Event()
        t0 = time.time()
        self.ask("x")
        self.assertLess(time.time() - t0, 1)
        self.chat_gate.set()


if __name__ == "__main__":
    unittest.main()
