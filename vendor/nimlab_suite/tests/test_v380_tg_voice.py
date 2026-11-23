"""v3.8.0 live bug: voice notes to Quill on Telegram failed with "server 404:
The model 'asr' does not exist or is not exposed by this test server.
Available: svn-dev/quill". Since 3.7.2 the endpoint exposes only the agent
model name, but telegram.Backend sent model "asr" to /audio/transcriptions
and "tts" to /audio/speech. Now both send the exposed agent name, which the
server maps to the ASR and TTS roles.

The regression test runs a real Telegram voice note in and a voice reply out
through telegram.Backend against a running test server that exposes only
the agent name (no legacy expose block)."""

import json
import os
import re
import unittest
from unittest import mock

from nimlab import telegram as TG
from nimlab import tgcmds
from nimlab.api import ModelResult
from tests.fakes import make_wav
from tests.test_server import ServerCase
from tests.test_telegram import FRIEND, OWNER, TOKEN, FakeTelegram, msg

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TelegramVoiceSingleModel(ServerCase):
    expose = None    # the default since 3.7.2: only the agent model name is listed

    def setUp(self):
        super().setUp()
        st, _, raw = self.call("/models")
        self.assertEqual(st, 200, raw)
        self.names = [m["id"] for m in json.loads(raw)["data"]]
        self.assertEqual(len(self.names), 1, self.names)       # one exposed name, as on the phone
        self.assertNotIn("asr", self.names)
        self.agent = self.names[0]
        self.seen = []
        real_run = self.ent.run_role

        def run_role(role, **kw):
            if role == "tts":
                self.seen.append(("tts", kw.get("text")))
                return ModelResult(True, data=make_wav(0.3))
            return real_run(role, **kw)
        for p in (mock.patch.object(self.ent.client, "asr",
                                    side_effect=lambda *a, **k: self.seen.append(("asr",)) or
                                    ModelResult(True, text="what time is it")),
                  mock.patch.object(self.ent, "run_role", side_effect=run_role)):
            p.start()
            self.addCleanup(p.stop)
        self.api = FakeTelegram()
        self.backend = TG.Backend(base=self.base, key=self.key, admin_key="", model=self.agent)
        convert = mock.Mock(side_effect=lambda data, args, a, b: make_wav(0.5) if b == ".wav" else b"OGGopus")
        ts = {"allow": [str(OWNER), str(FRIEND)], "owner": str(OWNER), "mode": "polling", "refusal": "polite",
              "voice_replies": True, "username": "nimlab_bot", "admin_for_owner": True}
        self.logs = []
        self.conn = TG.Connector(TG.Bot(TOKEN, http=self.api), self.backend, ts, save=lambda: None,
                                 convert=convert, log=self.logs.append)

    def test_voice_in_voice_out_with_only_the_agent_name(self):
        with mock.patch.object(tgcmds, "autoplay_on", return_value=False):
            self.conn.handle(msg(FRIEND, voice={"file_id": "VOICE1", "duration": 2}))
        texts = " ".join(self.api.texts())
        self.assertNotIn("404", texts)
        self.assertNotIn("does not exist", texts)
        self.assertEqual([c[0] for c in self.api.calls], ["sendChatAction", "getFile", "sendVoice"])
        self.assertEqual(self.seen[0], ("asr",))
        self.assertTrue(any(s[0] == "tts" for s in self.seen), self.seen)
        self.assertEqual(len(self.api.sent("sendVoice")), 1)
        self.assertIn(b"OGGopus", self.api.sent("sendVoice")[0]["_multipart"])
        self.assertFalse([l for l in self.logs if "server 404" in l], self.logs)

    def test_backend_sends_the_agent_name_on_both_routes(self):
        sent = []

        def http(url, data, headers, timeout):
            sent.append((url, data))
            if url.endswith("/audio/transcriptions"):
                return 200, b'{"text": "hi"}'
            return 200, b"RIFF"
        b = TG.Backend(http=http, base="http://x/v1", key="k", admin_key="", model="svn-dev/quill")
        b.transcribe(make_wav(0.2), "telegram:1")
        b.speech("hello", "telegram:1")
        self.assertIn(b'name="model"\r\n\r\nsvn-dev/quill', sent[0][1])
        self.assertEqual(json.loads(sent[1][1])["model"], "svn-dev/quill")

    def test_role_names_are_refused_as_models(self):
        st, _, raw = self.call("/audio/speech", {"model": "tts", "input": "hi"})
        self.assertEqual(st, 404, raw)
        st, _, raw = self.call("/audio/speech", {"model": self.agent, "input": "hi", "response_format": "wav"})
        self.assertEqual(st, 200, raw)


class NoRoleNamesAsModels(unittest.TestCase):
    """No internal client sends a role name as the model to the local server."""

    ROLE_NAMES = ("asr", "tts", "embedding", "embed", "reranker", "rerank", "vision", "image_gen", "image",
                  "agent", "stt")

    def test_grep(self):
        rx = re.compile(r"[\"']model[\"']\s*[:,]\s*[\"'](" + "|".join(self.ROLE_NAMES) + r")[\"']")
        bad = []
        for root, _dirs, files in os.walk(os.path.join(PROJECT, "nimlab")):
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(root, f)
                    with open(p, encoding="utf-8") as fh:
                        for n, line in enumerate(fh, 1):
                            if rx.search(line):
                                bad.append(f"{os.path.relpath(p, PROJECT)}:{n}: {line.strip()}")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
