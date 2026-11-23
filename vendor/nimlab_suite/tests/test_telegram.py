"""The Telegram connector against a fake Bot API and a fake testbed server.
No request leaves the machine."""

import io
import json
import os
import stat
import sys
import threading
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import telegram as TG
from tests.sandbox import all_text, lab

TOKEN = "123456789:AAE" + "x" * 32
OWNER, FRIEND, STRANGER = 1111, 2222, 9999


class FakeTelegram:
    """The Bot API: records calls, answers getMe/getUpdates/getFile/send*."""

    def __init__(self, updates=None, fail=None, md_fails=False):
        self.calls = []
        self.updates = list(updates or [])
        self.fail = fail or {}           # method -> (status, description, code) or an exception
        self.md_fails = md_fails
        self.files = {"VOICE1": b"OggS-voice", "PHOTO_BIG": b"\xff\xd8big", "PHOTO_SMALL": b"\xff\xd8small"}

    def __call__(self, url, data, headers, timeout):
        if "/file/bot" in url:
            name = url.rsplit("/", 1)[1]
            return (200, self.files[name]) if name in self.files else (404, b"")
        method = url.rsplit("/", 1)[1]
        assert url.startswith(f"{TG.API}/bot{TOKEN}/"), url
        ctype = headers.get("Content-Type", "")
        params = json.loads(data) if ctype == "application/json" else {"_multipart": data}
        self.calls.append((method, params))
        f = self.fail.get(method)
        if isinstance(f, Exception):
            raise f
        if f:
            status, desc, code = f
            return status, json.dumps({"ok": False, "description": desc, "error_code": code}).encode()
        if method == "sendMessage" and self.md_fails and params.get("parse_mode"):
            return 400, json.dumps({"ok": False, "description": "Bad Request: can't parse entities",
                                    "error_code": 400}).encode()
        result = True
        if method == "getMe":
            result = {"id": 123456789, "is_bot": True, "first_name": "Lab", "username": "nimlab_bot"}
        elif method == "getUpdates":
            off = params.get("offset") or 0
            result = [u for u in self.updates if u["update_id"] >= off]
            self.updates = []
        elif method == "getFile":
            result = {"file_id": params["file_id"], "file_path": params["file_id"]}
        return 200, json.dumps({"ok": True, "result": result}).encode()

    def sent(self, method="sendMessage"):
        return [p for m, p in self.calls if m == method]

    def texts(self):
        return [p["text"] for p in self.sent()]


class FakeBackend:
    def __init__(self, reply="Hello **there**!", heard="what time is it", fail=None):
        self.reply, self.heard, self.fail = reply, heard, fail
        self.chats, self.wavs, self.spoken = [], [], []

    def chat(self, messages, user, admin=False):
        if self.fail:
            raise self.fail
        self.chats.append((messages, user, admin))
        return self.reply

    def transcribe(self, wav, user):
        self.wavs.append((wav, user))
        return self.heard

    def speech(self, text, user):
        self.spoken.append(text)
        return b"RIFFwav"


def msg(uid, text=None, chat_type="private", update_id=1, **extra):
    m = {"message_id": 50 + update_id, "from": {"id": uid}, "chat": {"id": uid, "type": chat_type}}
    if text is not None:
        m["text"] = text
    m.update(extra)
    return {"update_id": update_id, "message": m}


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        self.saved = 0
        self.logs = []

    def tearDown(self):
        self._lab.__exit__(None, None, None)

    def conn(self, api=None, backend=None, **t):
        ts = {"allow": [str(OWNER), str(FRIEND)], "owner": str(OWNER), "mode": "polling", "refusal": "polite",
              "voice_replies": False, "username": "nimlab_bot", "admin_for_owner": True}
        ts.update(t)
        self.api = api or FakeTelegram()
        self.backend = backend or FakeBackend()
        convert = mock.Mock(side_effect=lambda data, args, a, b: b"WAV16k" if b == ".wav" else b"OGGopus")
        self.convert = convert

        def save():
            self.saved += 1
        return TG.Connector(TG.Bot(TOKEN, http=self.api), self.backend, ts, save=save, convert=convert,
                            log=self.logs.append)

    # -- getMe / tokens --------------------------------------------------
    def test_get_me_and_errors_hide_token(self):
        bot = TG.Bot(TOKEN, http=FakeTelegram())
        self.assertEqual(bot.call("getMe")["username"], "nimlab_bot")
        bad = TG.Bot(TOKEN, http=FakeTelegram(fail={"getMe": (401, "Unauthorized", 401)}))
        with self.assertRaises(TG.TelegramError) as cm:
            bad.call("getMe")
        self.assertEqual(cm.exception.code, 401)
        down = TG.Bot(TOKEN, http=FakeTelegram(fail={"getMe": OSError(f"timed out {TOKEN}")}))
        with self.assertRaises(TG.TelegramError) as cm:
            down.call("getMe")
        self.assertNotIn(TOKEN, str(cm.exception))
        self.assertIn("cannot reach Telegram", str(cm.exception))

    def test_token_saved_private_and_masked(self):
        with self.assertRaises(ValueError):
            TG.save_token("not-a-token")
        self.assertEqual(TG.save_token(f"  https://t.me/x {TOKEN} \n"), TOKEN)
        self.assertEqual(TG.load_token(), TOKEN)
        self.assertEqual(stat.S_IMODE(os.stat(TG.token_path()).st_mode), 0o600)
        self.assertEqual(TG.mask(TOKEN), "123456789:***" + TOKEN[-4:])
        self.assertNotIn(TOKEN, all_text(self.lab.data) + all_text(self.lab.proj))

    # -- allowlist -------------------------------------------------------
    def test_allowed_user_gets_reply_as_telegram_user(self):
        c = self.conn()
        c.handle(msg(FRIEND, "hi"))
        msgs, user, admin = self.backend.chats[0]
        self.assertEqual((msgs[-1], user, admin), ({"role": "user", "content": "hi"}, f"telegram:{FRIEND}", False))
        sent = self.api.sent()[-1]
        self.assertEqual(sent["text"], "Hello *there*\\!")
        self.assertEqual(sent["parse_mode"], "MarkdownV2")
        self.assertEqual(sent["reply_to_message_id"], 51)

    def test_owner_messages_are_admin(self):
        c = self.conn()
        c.handle(msg(OWNER, "restart please"))
        self.assertTrue(self.backend.chats[0][2])
        c2 = self.conn(admin_for_owner=False)
        c2.handle(msg(OWNER, "hi"))
        self.assertFalse(self.backend.chats[0][2])

    def test_stranger_refused_politely_or_ignored(self):
        c = self.conn()
        c.handle(msg(STRANGER, "hi"))
        self.assertEqual(self.backend.chats, [])
        self.assertIn("this bot is private", self.api.texts()[0].replace("\\", ""))
        self.assertIn(str(STRANGER), self.api.texts()[0])
        c = self.conn(refusal="ignore")
        c.handle(msg(STRANGER, "hi"))
        self.assertEqual(self.api.sent(), [])
        c = self.conn()
        c.handle(msg(STRANGER, "hi", chat_type="group"))   # never answers strangers in groups
        self.assertEqual(self.api.sent(), [])

    def test_id_command_works_for_anyone(self):
        c = self.conn()
        c.handle(msg(STRANGER, "/id"))
        self.assertIn(f"Your Telegram user ID is {STRANGER}", self.api.texts()[0])

    def test_capture_makes_first_start_the_owner(self):
        c = self.conn(allow=[], owner=None)
        c.capture = True
        c.handle(msg(STRANGER, "/start@nimlab_bot"))
        self.assertEqual((c.t["owner"], c.t["allow"]), (str(STRANGER), [str(STRANGER)]))
        self.assertFalse(c.capture)
        self.assertEqual(self.saved, 1)
        self.assertIn("owner of this testbed", self.api.texts()[0])
        c.handle(msg(4444, "/start"))               # capture is over: the next stranger is refused
        self.assertEqual(c.t["allow"], [str(STRANGER)])

    def test_capture_owner_polls_until_start(self):
        api = FakeTelegram(updates=[msg(OWNER, "/start", update_id=7)])
        c = self.conn(api=api, allow=[], owner=None)
        self.assertEqual(TG.capture_owner(c, seconds=5, log=self.logs.append), str(OWNER))

    def test_reset_and_history(self):
        c = self.conn()
        for i in range(12):
            c.handle(msg(FRIEND, f"m{i}", update_id=i + 1))
        self.assertEqual(len(c.history[FRIEND]), TG.HISTORY_TURNS * 2)
        last_msgs = self.backend.chats[-1][0]
        self.assertEqual(len(last_msgs), TG.HISTORY_TURNS * 2 + 1)
        c.handle(msg(FRIEND, "/reset"))
        self.assertNotIn(FRIEND, c.history)

    # -- polling ---------------------------------------------------------
    def test_polling_handles_updates_and_advances_offset(self):
        api = FakeTelegram(updates=[msg(FRIEND, "one", update_id=10), msg(FRIEND, "two", update_id=11)])
        c = self.conn(api=api)
        self.assertEqual(c.poll(once=True, timeout=0), 0)
        self.assertEqual([m[-1]["content"] for m, _, _ in self.backend.chats], ["one", "two"])
        names = [m for m, _ in api.calls]
        self.assertEqual(names[0], "deleteWebhook")
        stop = threading.Event()
        calls = []

        def http(url, data, headers, timeout):
            if url.endswith("getUpdates"):
                calls.append(json.loads(data).get("offset"))
                if len(calls) == 2:
                    stop.set()
                return 200, json.dumps({"ok": True, "result": [msg(FRIEND, "x", update_id=20)] if len(calls) == 1
                                        else []}).encode()
            return api(url, data, headers, timeout)
        c.bot.http = http
        c.poll(stop=stop, timeout=0)
        self.assertEqual(calls, [12, 21])   # 3.7.1: the offset is kept across poll() calls

    def test_polling_errors(self):
        c = self.conn(api=FakeTelegram(fail={"getUpdates": (401, "Unauthorized", 401)}))
        self.assertEqual(c.poll(once=True), 1)
        self.assertIn("bot token is wrong", "\n".join(self.logs))
        sleeps = []
        c = self.conn(api=FakeTelegram(fail={"getUpdates": (409, "Conflict: terminated by other getUpdates", 409)}))
        self.assertEqual(c.poll(once=True, sleep=sleeps.append), 1)
        self.assertIn("Another copy of this bot is polling", "\n".join(self.logs))
        self.assertEqual(sleeps, [1])

    def test_polling_backoff_on_network_errors(self):
        stop = threading.Event()
        sleeps = []

        def sleep(s):
            sleeps.append(s)
            if len(sleeps) == 4:
                stop.set()
        c = self.conn(api=FakeTelegram(fail={"getUpdates": OSError("network down")}))
        c.poll(stop=stop, sleep=sleep)
        self.assertEqual(sleeps, [1, 2, 4, 8])

    # -- splitting / formatting -----------------------------------------
    def test_long_reply_split_under_4096(self):
        long = ("word " * 300 + "\n\n") * 6
        c = self.conn(backend=FakeBackend(reply=long))
        c.handle(msg(FRIEND, "tell me a lot"))
        sent = self.api.sent()
        self.assertGreater(len(sent), 1)
        self.assertTrue(all(len(p["text"]) <= TG.LIMIT for p in sent))
        self.assertEqual(sent[0]["reply_to_message_id"], 51)
        self.assertIsNone(sent[1].get("reply_to_message_id"))

    def test_split_keeps_code_blocks_closed(self):
        text = "intro\n```\n" + "\n".join(f"line {i}" for i in range(900)) + "\n```\nend"
        pieces = TG.split_text(text)
        self.assertGreater(len(pieces), 1)
        for p in pieces:
            self.assertLessEqual(len(p), TG.LIMIT)
            self.assertEqual(p.count("```") % 2, 0)
        self.assertEqual(TG.split_text("  "), ["(empty reply)"])
        self.assertEqual(TG.split_text("x" * 5000)[0], "x" * 4096)

    def test_markdown_escaping(self):
        self.assertEqual(TG.to_mdv2("1. a_b (c) **bold** `x_y`"), "1\\. a\\_b \\(c\\) *bold* `x_y`")
        self.assertEqual(TG.to_mdv2("```py\nprint(1)\n```"), "```py\nprint(1)\n```")

    def test_markdown_rejected_falls_back_to_plain(self):
        c = self.conn(api=FakeTelegram(md_fails=True))
        c.handle(msg(FRIEND, "hi"))
        plain = [p for p in self.api.sent() if not p.get("parse_mode")]
        self.assertEqual(plain[-1]["text"], "Hello **there**!")

    # -- voice / photo ---------------------------------------------------
    def test_voice_note_goes_to_asr_then_chat(self):
        c = self.conn()
        c.handle(msg(FRIEND, voice={"file_id": "VOICE1", "duration": 2}))
        self.convert.assert_any_call(b"OggS-voice", ["-ar", "16000", "-ac", "1"], ".ogg", ".wav")
        self.assertEqual(self.backend.wavs, [(b"WAV16k", f"telegram:{FRIEND}")])
        self.assertEqual(self.backend.chats[0][0][-1]["content"], "what time is it")
        self.assertIn('Heard: "what time is it"', self.api.texts()[-1])
        self.assertEqual(self.api.sent("sendVoice"), [])

    def test_voice_reply_when_on(self):
        c = self.conn(voice_replies=True)
        c.handle(msg(FRIEND, voice={"file_id": "VOICE1"}))
        self.assertEqual(len(self.api.sent("sendVoice")), 1)
        self.assertIn(b"OGGopus", self.api.sent("sendVoice")[0]["_multipart"])
        self.assertEqual(self.backend.spoken, ["Hello **there**!"])

    def test_empty_transcript_explained(self):
        c = self.conn(backend=FakeBackend(heard="  "))
        c.handle(msg(FRIEND, voice={"file_id": "VOICE1"}))
        self.assertIn("couldn't make out any words", self.api.texts()[-1].replace("\\", ""))
        self.assertEqual(self.backend.chats, [])

    def test_photo_goes_to_vision_as_data_url(self):
        c = self.conn()
        photos = [{"file_id": "PHOTO_SMALL", "file_size": 10}, {"file_id": "PHOTO_BIG", "file_size": 900}]
        c.handle(msg(FRIEND, photo=photos, caption="what is this?"))
        content = self.backend.chats[0][0][-1]["content"]
        self.assertEqual(content[0], {"type": "text", "text": "what is this?"})
        import base64
        self.assertEqual(content[1]["image_url"]["url"],
                         "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8big").decode())
        self.assertEqual(c.history[FRIEND][0]["content"], "what is this?")

    def test_sticker_explained(self):
        c = self.conn()
        c.handle(msg(FRIEND, sticker={"file_id": "S"}))
        self.assertIn("text, photos and voice notes", self.api.texts()[-1])

    # -- errors ----------------------------------------------------------
    def test_backend_error_becomes_short_message(self):
        c = self.conn(backend=FakeBackend(fail=RuntimeError("server 401: bad key")))
        c.handle(msg(FRIEND, "hi"))
        self.assertIn("the server refused the key", self.api.texts()[-1])
        self.assertIn("RuntimeError", "\n".join(self.logs))
        c = self.conn(backend=FakeBackend(fail=OSError("[Errno 111] Connection refused")))
        c.handle(msg(FRIEND, "hi"))
        self.assertIn("server is not running", self.api.texts()[-1])

    def test_send_failure_never_raises_out_of_handle(self):
        c = self.conn(api=FakeTelegram(fail={"sendMessage": (403, "Forbidden: bot was blocked by the user", 403)}))
        c.handle(msg(FRIEND, "hi"))       # must not raise
        self.assertIn("bot was blocked", "\n".join(self.logs))

    # -- backend + webhook ----------------------------------------------
    def test_backend_posts_to_local_server(self):
        seen = []

        def http(url, data, headers, timeout):
            seen.append((url, headers))
            return 200, json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()
        b = TG.Backend(http=http, base="http://127.0.0.1:8765/v1", key="user-key", admin_key="admin-key",
                       model="testbed")
        self.assertEqual(b.chat([{"role": "user", "content": "x"}], "telegram:1"), "ok")
        self.assertEqual(seen[0][1]["Authorization"], "Bearer user-key")
        self.assertEqual(seen[0][1]["X-Testbed-User"], "telegram:1")
        b.chat([], "telegram:1", admin=True)
        self.assertEqual(seen[1][1]["Authorization"], "Bearer admin-key")
        b2 = TG.Backend(http=lambda *a: (401, b'{"error": {"message": "bad key"}}'), base="http://x/v1", key="k",
                        admin_key="", model="m")
        with self.assertRaises(RuntimeError) as cm:
            b2.chat([], "u")
        self.assertEqual(str(cm.exception), "server 401: bad key")

    def test_webhook_needs_secret_header(self):
        api = FakeTelegram()
        url = TG.set_webhook(TG.Bot(TOKEN, http=api), "https://lab.example.com/")
        self.assertEqual(url, "https://lab.example.com/telegram/webhook")
        secret = api.sent("setWebhook")[0]["secret_token"]
        self.assertEqual(stat.S_IMODE(os.stat(TG.secret_path()).st_mode), 0o600)
        self.assertEqual(TG.handle_webhook({}, b"{}"), 403)
        self.assertEqual(TG.handle_webhook({"X-Telegram-Bot-Api-Secret-Token": "wrong"}, b"{}"), 403)
        self.assertEqual(TG.handle_webhook({"X-Telegram-Bot-Api-Secret-Token": secret}, b"not json"), 400)
        fake = mock.Mock()
        with mock.patch.dict(TG._hook, {"conn": fake}):
            self.assertEqual(TG.handle_webhook({"X-Telegram-Bot-Api-Secret-Token": secret}, b'{"update_id": 1}'),
                             200)

    # -- CLI -------------------------------------------------------------
    def cli(self, action, values=None, stdin="", api=None, capture=False, remove=False):
        args = types.SimpleNamespace(action=action, values=values or [], capture=capture, remove=remove)
        api = api or FakeTelegram()
        out = io.StringIO()
        real_bot = TG.Bot
        with redirect_stdout(out), mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                mock.patch.object(TG, "Bot", lambda tok: real_bot(tok, http=api)):
            code = TG.cmd_telegram(args)
        return code, out.getvalue()

    def test_cli_set_token_tests_with_get_me(self):
        code, out = self.cli("set-token", stdin=TOKEN + "\n")
        self.assertEqual(code, 0)
        self.assertIn("[ok] Connected: @nimlab_bot", out)
        self.assertNotIn(TOKEN, out)
        self.assertEqual(TG.settings()["username"], "nimlab_bot")
        code, out = self.cli("test", api=FakeTelegram(fail={"getMe": (401, "Unauthorized", 401)}))
        self.assertEqual(code, 1)
        self.assertIn("did not accept the token", out)
        self.assertEqual(self.cli("set-token", stdin="garbage\n")[0], 2)

    def test_cli_allow_mode_voice_refusal_status(self):
        self.assertEqual(self.cli("mode", ["webhook"])[0], 2)   # no token yet
        TG.save_token(TOKEN)
        code, out = self.cli("allow", ["2222", "bob"])
        self.assertIn("not a numeric Telegram ID", out)
        self.assertEqual(TG.settings()["allow"], ["2222"])
        self.cli("allow", ["2222"], remove=True)
        self.assertEqual(TG.settings()["allow"], [])
        self.assertEqual(self.cli("mode", ["webhook"])[0], 0)
        self.assertEqual(self.cli("voice", ["on"])[0], 0)
        self.assertEqual(self.cli("refusal", ["ignore"])[0], 0)
        self.assertEqual(self.cli("refusal", ["rude"])[0], 2)
        t = TG.settings()
        self.assertEqual((t["mode"], t["voice_replies"], t["refusal"]), ("webhook", True, "ignore"))
        code, out = self.cli("status")
        self.assertIn("123456789:***", out)
        self.assertNotIn(TOKEN, out)
        self.assertNotIn(TOKEN, all_text(self.lab.proj) + all_text(self.lab.data))

    def test_cli_allow_capture(self):
        TG.save_token(TOKEN)
        api = FakeTelegram(updates=[msg(OWNER, "/start", update_id=3)])
        code, out = self.cli("allow", capture=True, api=api)
        self.assertEqual(code, 0)
        self.assertIn(f"[ok] Owner: {OWNER}", out)
        self.assertEqual(TG.settings()["owner"], str(OWNER))


if __name__ == "__main__":
    unittest.main()
