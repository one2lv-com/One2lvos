"""3.7.1: one reply per Telegram update, however many pollers run and
whether or not the offset was confirmed (the phone got five identical
/start greetings in one minute)."""

import json
import threading
import unittest

from nimlab import telegram as TG
from tests.sandbox import lab

TOKEN = "123456789:AAE" + "x" * 32
OWNER = 1111
GREETING = "Hi! Send text, a photo or a voice note."


def start(uid, update_id):
    return {"update_id": update_id,
            "message": {"message_id": 50 + update_id, "from": {"id": uid}, "chat": {"id": uid, "type": "private"},
                        "text": "/start"}}


class StickyTelegram:
    """The real Bot API rule: getUpdates returns every update with
    update_id >= offset again and again until a call passes a higher
    offset (that confirms it). Shared by several pollers, like one bot."""

    def __init__(self, updates):
        self.pending = list(updates)
        self.offsets = []
        self.sent = []
        self.lock = threading.Lock()

    def __call__(self, url, data, headers, timeout):
        method = url.rsplit("/", 1)[1]
        params = json.loads(data) if data else {}
        result = True
        with self.lock:
            if method == "getUpdates":
                off = params.get("offset")
                self.offsets.append(off)
                if off is not None:
                    self.pending = [u for u in self.pending if u["update_id"] >= off]
                result = list(self.pending)
            elif method == "sendMessage":
                self.sent.append(params["text"])
            elif method == "getMe":
                result = {"id": 123456789, "is_bot": True, "username": "nimlab_bot"}
        return 200, json.dumps({"ok": True, "result": result}).encode()

    def greetings(self):
        return [t for t in self.sent if GREETING.split("!")[0] in t and "Send text" in t]


class Backend:
    def chat(self, messages, user, admin=False):
        return "hello"


class Base(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        self.logs = []

    def tearDown(self):
        self._lab.__exit__(None, None, None)

    def conn(self, api, **t):
        ts = {"allow": [str(OWNER)], "owner": str(OWNER), "mode": "polling", "refusal": "polite",
              "voice_replies": False, "username": "nimlab_bot"}
        ts.update(t)
        return TG.Connector(TG.Bot(TOKEN, http=api), Backend(), ts, save=lambda: None, log=self.logs.append)


class OneReplyPerUpdate(Base):
    def test_two_pollers_same_update_answer_once(self):
        api = StickyTelegram([start(OWNER, 500)])
        a, b = self.conn(api), self.conn(api)
        # both fetch before either confirms: Telegram hands both the same update
        self.assertEqual(a.poll(once=True, timeout=0), 0)
        b.offset = 1      # b's last getUpdates was sent before a's answer: its offset is behind
        self.assertEqual(b.poll(once=True, timeout=0), 0)
        self.assertEqual(len(api.greetings()), 1, api.sent)
        self.assertEqual(b.skipped, 1)
        self.assertIn("skipped update 500", "\n".join(self.logs))

    def test_two_pollers_in_threads_answer_once(self):
        api = StickyTelegram([start(OWNER, 600)])
        conns = [self.conn(api) for _ in range(4)]
        ts = [threading.Thread(target=c.poll, kwargs={"once": True, "timeout": 0}) for c in conns]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        self.assertEqual(len(api.greetings()), 1, api.sent)

    def test_repeated_polls_of_unconfirmed_update_answer_once(self):
        # the fake keeps returning /start until an offset above it is sent
        api = StickyTelegram([start(OWNER, 700)])
        c = self.conn(api)
        for _ in range(5):
            c.poll(once=True, timeout=0)
        self.assertEqual(len(api.greetings()), 1, api.sent)
        self.assertEqual(api.offsets[0], None)
        self.assertEqual(api.offsets[1:], [701] * 4)   # offset kept across poll() calls and confirmed
        self.assertEqual(api.pending, [])

    def test_new_poller_resumes_after_last_handled(self):
        api = StickyTelegram([start(OWNER, 800)])
        self.conn(api).poll(once=True, timeout=0)
        later = self.conn(api)          # e.g. the service restarts before the offset was confirmed
        later.poll(once=True, timeout=0)
        self.assertEqual(api.offsets[-1], 801)
        self.assertEqual(len(api.greetings()), 1)

    def test_newer_update_still_answered(self):
        api = StickyTelegram([start(OWNER, 900)])
        c = self.conn(api)
        c.poll(once=True, timeout=0)
        api.pending.append(start(OWNER, 901))
        c.poll(once=True, timeout=0)
        self.assertEqual(len(api.greetings()), 2)

    def test_stale_ledger_accepts_restarted_ids(self):
        # Telegram may restart update_ids after a week without updates
        now = [1_000_000.0]
        led = TG.UpdateLedger("123456789", clock=lambda: now[0])
        self.assertTrue(led.claim(5000))
        self.assertFalse(led.claim(5000))
        self.assertFalse(led.claim(10))
        now[0] += TG.LEDGER_STALE_SEC + 1
        self.assertIsNone(led.last())
        self.assertTrue(led.claim(10))

    def test_ledger_is_per_bot(self):
        self.assertTrue(TG.UpdateLedger("111").claim(5))
        self.assertTrue(TG.UpdateLedger("222").claim(5))
        self.assertFalse(TG.UpdateLedger("111").claim(5))


class CaptureConfirms(Base):
    def test_capture_answers_once_confirms_and_stops(self):
        api = StickyTelegram([start(OWNER, 42)])
        c = self.conn(api, allow=[], owner=None)
        owner = TG.capture_owner(c, seconds=30, log=self.logs.append, sleep=lambda s: None)
        self.assertEqual(owner, str(OWNER))
        welcomes = [t for t in api.sent if "owner of this testbed" in t]
        self.assertEqual(len(welcomes), 1, api.sent)
        self.assertEqual(api.offsets[-1], 43)        # confirmed before capture returned
        self.assertEqual(api.pending, [])
        polls = len(api.offsets)
        self.assertLessEqual(polls, 2)               # one fetch, one confirm: the loop stopped at once
        # the service bot that starts next does not greet the same /start again
        svc = self.conn(api, allow=[str(OWNER)], owner=str(OWNER))
        svc.poll(once=True, timeout=0)
        self.assertEqual(len(api.greetings()), 0, api.sent)

    def test_webhook_retry_handled_once(self):
        c = self.conn(StickyTelegram([]))
        self.assertTrue(c.claim(start(OWNER, 77)))
        self.assertFalse(c.claim(start(OWNER, 77)))


if __name__ == "__main__":
    unittest.main()
