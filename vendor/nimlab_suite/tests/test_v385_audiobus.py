"""v3.8.5: the lab-wide audio bus. Phones (nimbridge on Termux) play the
lab's audio and lend their mic to the SSH voice call; the VPS never plays
anything itself. Offline: a fake app behind the real HTTP handler."""

import base64
import json
import os
import shutil
import stat
import struct
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from nimlab import audiobus as AB, server as S, tgcmds, voicecall


def pcm(n=1600):
    return b"".join(struct.pack("<h", (i * 37) % 2000 - 1000) for i in range(n))


class Bus(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="bus")
        self.addCleanup(shutil.rmtree, self.dir, True)
        p = mock.patch.dict(os.environ, {"NIMLAB_AUDIO_BUS_DIR": os.path.join(self.dir, "bus"),
                                         "NIMLAB_DATA_DIR": self.dir, "NIMLAB_COLOR": "0"})
        p.start()
        self.addCleanup(p.stop)


class TestDevices(Bus):
    def test_token_shown_once_and_only_hash_kept(self):
        tok = AB.add_device("pixel")
        self.assertTrue(tok.startswith("nab_"))
        raw = open(os.path.join(AB.bus_dir(), "devices.json")).read()
        self.assertNotIn(tok, raw)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(AB.bus_dir(), "devices.json")).st_mode), 0o600)
        self.assertEqual(AB.auth_device(tok), "pixel")
        self.assertIsNone(AB.auth_device(tok + "x"))
        self.assertIsNone(AB.auth_device(""))

    def test_bad_names_refused(self):
        for bad in ("", "Has Space", "../x", "a" * 40):
            with self.assertRaises(AB.BusError):
                AB.add_device(bad)

    def test_readding_rotates_token(self):
        old = AB.add_device("pixel")
        new = AB.add_device("pixel")
        self.assertIsNone(AB.auth_device(old))
        self.assertEqual(AB.auth_device(new), "pixel")


class TestRouting(Bus):
    def setUp(self):
        super().setUp()
        AB.add_device("pixel")
        AB.add_device("galaxy")

    def test_no_active_phone_means_no_audio(self):
        with self.assertRaises(AB.BusError) as c:
            AB.publish(pcm())
        self.assertEqual(c.exception.status, 409)

    def test_only_the_active_phone_gets_it(self):
        AB.set_active("pixel")
        h = AB.head()
        AB.publish(pcm(), source="t")
        self.assertEqual(len(AB.events_for("pixel", h)[0]), 1)
        self.assertEqual(AB.events_for("galaxy", h)[0], [])
        AB.set_active("galaxy")
        AB.publish(pcm())
        self.assertEqual(len(AB.events_for("pixel", h)[0]), 1)
        self.assertEqual(len(AB.events_for("galaxy", h)[0]), 1)

    def test_all_is_explicit_broadcast(self):
        h = AB.head()
        ev = AB.publish(pcm(), target="all")
        self.assertEqual(ev["target"], "*")
        for d in ("pixel", "galaxy"):
            self.assertEqual(len(AB.events_for(d, h)[0]), 1)
            AB.clip(d, ev["clip"])

    def test_clip_private_to_its_phone(self):
        ev = AB.publish(pcm(), target="pixel")
        data, mime = AB.clip("pixel", ev["clip"])
        self.assertEqual(mime, "audio/wav")
        with self.assertRaises(AB.BusError):
            AB.clip("galaxy", ev["clip"])
        with self.assertRaises(AB.BusError):
            AB.clip("pixel", "../devices")

    def test_first_poll_never_replays_and_stale_play_skipped(self):
        AB.publish(pcm(), target="pixel")
        evs, h = AB.events_for("pixel", -1)
        self.assertEqual(evs, [])
        self.assertEqual(h, AB.head())
        AB.publish(pcm(), target="pixel")
        self.assertEqual(AB.events_for("pixel", h, now=time.time() + AB.PLAY_TTL + 5)[0], [])

    def test_long_poll_returns_on_publish(self):
        h = AB.head()
        threading.Timer(0.4, lambda: AB.publish(pcm(), target="pixel")).start()
        t = time.monotonic()
        r = AB.wait_events("pixel", h, wait=5, caps={"mic": True})
        self.assertLess(time.monotonic() - t, 3)
        self.assertEqual(len(r["events"]), 1)
        self.assertTrue(AB.device_state("pixel")["online"])
        self.assertTrue(AB.device_state("pixel")["mic"])


class TestFormats(Bus):
    def test_sniff(self):
        self.assertEqual(AB.sniff(b"RIFF\0\0\0\0WAVEfmt "), "wav")
        self.assertEqual(AB.sniff(b"OggS\0\2" + b"\0" * 10), "ogg")
        self.assertEqual(AB.sniff(b"ID3\4" + b"\0" * 10), "mp3")
        self.assertEqual(AB.sniff(b"\0\0\0\x20ftypM4A "), "m4a")
        self.assertEqual(AB.sniff(b"fLaC\0\0\0\x22"), "flac")
        self.assertIsNone(AB.sniff(pcm(8)))

    def test_raw_pcm_wrapped_as_wav_with_right_length(self):
        data, ext = AB.normalize(pcm(22050), "pcm", 22050)
        self.assertEqual(ext, "wav")
        self.assertEqual(AB.duration_ms(data, ext), 1000)
        import wave, io
        w = wave.open(io.BytesIO(data))
        self.assertEqual((w.getnchannels(), w.getframerate(), w.getsampwidth()), (1, 22050, 2))

    def test_container_kept_as_is(self):
        ogg = b"OggS" + b"\0" * 60
        self.assertEqual(AB.normalize(ogg, "wav"), (ogg, "ogg"))
        with self.assertRaises(AB.BusError):
            AB.normalize(b"")


class FakePhone(threading.Thread):
    """What nimbridge does with mic events, minus Termux."""

    def __init__(self, name, mic_ok=True):
        super().__init__(daemon=True)
        self.name_, self.mic_ok, self.played, self.stops = name, mic_ok, [], 0
        self.halt = False

    def run(self):
        since = AB.head()
        while not self.halt:
            r = AB.wait_events(self.name_, since, wait=1, caps={"mic": True})
            since = r["head"]
            for ev in r["events"]:
                t = ev["type"]
                if t == "record_start":
                    AB.ack(self.name_, ev["req"], "recording" if self.mic_ok else "error",
                           "" if self.mic_ok else "mic disabled on this phone")
                elif t == "record_stop":
                    AB.upload(self.name_, ev["req"], b"\0\0\0\x20ftypM4A fake-aac")
                elif t == "play":
                    self.played.append(AB.clip(self.name_, ev["clip"])[0])
                elif t == "stop":
                    self.stops += 1


class TestRemoteVoiceCall(Bus):
    def setUp(self):
        super().setUp()
        AB.add_device("pixel")
        AB.set_active("pixel")

    def phone(self, **kw):
        p = FakePhone("pixel", **kw)
        p.start()
        self.addCleanup(setattr, p, "halt", True)
        time.sleep(0.3)
        return p

    def test_check_needs_online_phone(self):
        ok, problems, _ = AB.RemoteDevice().check()
        self.assertFalse(ok)
        self.assertIn("isn't connected", problems[0])

    def test_record_and_play_round_trip(self):
        p = self.phone()
        dev = AB.RemoteDevice()
        self.assertTrue(dev.check()[0])
        path = os.path.join(self.dir, "turn.m4a")
        dev.record_start(path)
        self.assertTrue(dev.record_stop(path))
        self.assertEqual(AB.sniff(open(path, "rb").read()), "m4a")
        reply = os.path.join(self.dir, "reply.wav")
        open(reply, "wb").write(AB.wav_from_pcm(pcm()))
        dev.play(reply)
        dev.stop()
        time.sleep(1.5)
        self.assertEqual(len(p.played), 1)
        self.assertEqual(p.stops, 1)

    def test_phone_refusing_mic_is_an_error_not_a_hang(self):
        self.phone(mic_ok=False)
        with self.assertRaises(RuntimeError) as c:
            AB.RemoteDevice().record_start(os.path.join(self.dir, "x.m4a"))
        self.assertIn("mic disabled", str(c.exception))

    def test_no_bridge_running_times_out_cleanly(self):
        with self.assertRaises(RuntimeError) as c:
            AB.RemoteDevice(ack_timeout=0.5).record_start(os.path.join(self.dir, "x.m4a"))
        self.assertIn("nimbridge", str(c.exception))

    def test_run_call_off_termux_uses_the_phone(self):
        lines = []
        with mock.patch.object(voicecall, "on_termux", return_value=False):
            n = voicecall.run_call(mock.Mock(), input_fn=lambda p="": "q", out=lines.append)
        self.assertEqual(n, 0)
        self.assertTrue(any("pixel" in str(l) for l in lines), lines)


class TestTelegramAutoplay(Bus):
    def test_relayed_to_active_phone_off_termux(self):
        AB.add_device("pixel")
        AB.set_active("pixel")
        h, logs = AB.head(), []
        with mock.patch.object(tgcmds, "autoplay_on", return_value=True), \
                mock.patch.object(tgcmds, "_termux", return_value=False):
            self.assertEqual(tgcmds.autoplay(AB.wav_from_pcm(pcm()), ".wav", logs.append), "relayed")
        evs = AB.events_for("pixel", h)[0]
        self.assertEqual(evs[0]["source"], "telegram")

    def test_no_phone_is_logged_never_raised(self):
        logs = []
        with mock.patch.object(tgcmds, "autoplay_on", return_value=True), \
                mock.patch.object(tgcmds, "_termux", return_value=False):
            self.assertEqual(tgcmds.autoplay(b"RIFF....", ".wav", logs.append), "no device")
        self.assertIn("no phone took it", logs[0])


class FakeApp:
    settings = {"api_key": "lab-key-123", "log_requests": False, "log_to_console": False,
                "model_name": "svn-dev/quill", "max_body_mb": 25}
    quiet = True
    log_path = None
    check_key = S.TestbedApp.check_key
    chats = []

    def entity_settings(self):
        return {}

    def chat(self, body, base):
        FakeApp.chats.append(body)
        wav = AB.wav_from_pcm(pcm(16000), 16000)
        return S.Reply("Hi SeVin.", {}, info={"transcript": "hello quill"},
                       audio={"id": "a", "data": base64.b64encode(wav).decode(), "transcript": "Hi SeVin."})

    def speech(self, body):
        return AB.wav_from_pcm(pcm(8000), 16000), "audio/wav", {}


class TestHTTP(Bus):
    def setUp(self):
        super().setUp()
        self.tok = AB.add_device("pixel")
        self.tok2 = AB.add_device("galaxy")
        h = type("H", (S.Handler,), {"app": FakeApp()})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), h)
        self.srv.daemon_threads = True
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}/v1/audio/bus"

    def call(self, method, sub, token, body=None, ctype="application/json"):
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        req = urllib.request.Request(self.base + sub, data=data, method=method,
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if r.headers.get("Content-Type") == "application/json" else raw)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_auth(self):
        self.assertEqual(self.call("GET", "/events?since=-1&wait=0", "nope")[0], 401)
        self.assertEqual(self.call("GET", "/devices", self.tok)[0], 401)      # a phone token isn't the lab key
        self.assertEqual(self.call("GET", "/events?wait=0", "lab-key-123")[0], 401)  # nor the other way
        st, body = self.call("GET", "/devices", "lab-key-123")
        self.assertEqual(st, 200)
        self.assertEqual({d["name"] for d in body["devices"]}, {"pixel", "galaxy"})

    def test_activate_publish_poll_fetch(self):
        self.assertEqual(self.call("POST", "/activate", self.tok)[1]["active"], "pixel")
        h = self.call("GET", "/events?since=-1&wait=0&mic=1", self.tok)[1]["head"]
        st, ev = self.call("POST", "/publish", "lab-key-123",
                           {"audio": base64.b64encode(pcm(2205)).decode(), "format": "pcm", "pcm_rate": 22050,
                            "agent": "quill"})
        self.assertEqual((st, ev["ext"], ev["target"], ev["duration_ms"]), (200, "wav", "pixel", 100))
        evs = self.call("GET", f"/events?since={h}&wait=2", self.tok)[1]["events"]
        self.assertEqual([e["clip"] for e in evs], [ev["clip"]])
        st, data = self.call("GET", f"/clips/{ev['clip']}", self.tok)
        self.assertEqual((st, data[:4]), (200, b"RIFF"))
        self.assertEqual(self.call("GET", f"/clips/{ev['clip']}", self.tok2)[0], 404)
        self.assertEqual(self.call("GET", f"/events?since={h}&wait=0", self.tok2)[1]["events"], [])
        # the other phone takes over
        self.call("POST", "/activate", self.tok2)
        st, ev2 = self.call("POST", "/publish?format=ogg", "lab-key-123", b"OggS" + b"\0" * 40, "audio/ogg")
        self.assertEqual((st, ev2["target"], ev2["mime"]), (200, "galaxy", "audio/ogg"))

    def test_say(self):
        self.call("POST", "/activate", self.tok)
        st, ev = self.call("POST", "/say", "lab-key-123", {"text": "testing"})
        self.assertEqual((st, ev["target"], ev["duration_ms"]), (200, "pixel", 500))

    def test_talk_reply_waits_for_that_phone_only(self):
        st, out = self.call("POST", "/talk", self.tok, b"\0\0\0\x20ftypM4A rec", "audio/mp4")
        self.assertEqual(st, 200, out)
        self.assertEqual((out["transcript"], out["text"], out["duration_ms"]), ("hello quill", "Hi SeVin.", 1000))
        part = FakeApp.chats[-1]["messages"][0]["content"][0]
        self.assertEqual(part["input_audio"]["format"], "m4a")
        self.assertEqual(FakeApp.chats[-1]["modalities"], ["text", "audio"])
        self.assertEqual(self.call("GET", f"/clips/{out['clip']}", self.tok)[0], 200)
        self.assertEqual(self.call("GET", f"/clips/{out['clip']}", self.tok2)[0], 404)

    def test_mic_upload_only_for_the_asked_phone(self):
        AB.set_active("pixel")
        dev = AB.RemoteDevice(ack_timeout=0.3)
        with self.assertRaises(RuntimeError):
            dev.record_start(os.path.join(self.dir, "a.m4a"))   # nobody acks; but the request file exists
        req = [f[:-4] for f in os.listdir(os.path.join(AB.bus_dir(), "uploads")) if f.endswith(".req")][0]
        self.assertEqual(self.call("POST", f"/upload?req={req}", self.tok2, b"x", "audio/mp4")[0], 404)
        self.assertEqual(self.call("POST", f"/upload?req={req}", self.tok, b"x", "audio/mp4")[0], 200)


if __name__ == "__main__":
    unittest.main()
