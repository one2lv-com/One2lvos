"""v3.6.1 regression: Parakeet in a voice call went over HTTP and got a 400.

Riva ASR models (parakeet*, canary*, conformer*) now default to NVCF gRPC
even before a scan marks them, fetch their function ID on first use, get
16 kHz mono WAV, and a failed HTTP ASR shows NVIDIA's own error text.
"""

import io
import json
import os
import unittest
import wave
from unittest import mock

from nimlab import core, nvcf_grpc, store, voicecall
from tests.test_entity import EntityCase, FakeDevice, ROLES, make_wav


class FakeRiva:
    def __init__(self):
        self.calls = []

    def asr(self, fid, wav, pcm, language_code=None, mode=None, custom=None):
        self.calls.append((fid, wav, language_code))
        return "please remind me to water the plants", mode or "offline"


FID = "1598d209-5e27-4d3c-8079-4751568b1081"
PARAKEET = {"backend": "model", "model": "nvidia/parakeet-ctc-1.1b-asr"}   # no transport, not scanned


class TestUseGrpc(unittest.TestCase):
    def test_riva_asr_defaults_to_grpc(self):
        for m in ("nvidia/parakeet-ctc-1.1b-asr", "nvidia/parakeet-tdt-0.6b-v2", "nvidia/canary-1b-asr",
                  "nvidia/conformer-ctc-en", "parakeet-rnnt-1.1b"):
            with mock.patch.object(nvcf_grpc, "is_grpc_model", return_value=False):
                self.assertTrue(nvcf_grpc.use_grpc({"model": m}), m)

    def test_hosted_nvidia_endpoint_still_grpc(self):
        sp = dict(PARAKEET, endpoint="https://ai.api.nvidia.com/v1/audio/transcriptions")
        self.assertTrue(nvcf_grpc.use_grpc(sp))

    def test_own_endpoint_and_explicit_transport_win(self):
        self.assertFalse(nvcf_grpc.use_grpc(dict(PARAKEET, endpoint="http://192.168.1.5:9000/v1/asr")))
        self.assertFalse(nvcf_grpc.use_grpc(dict(PARAKEET, transport="http")))
        self.assertTrue(nvcf_grpc.use_grpc({"model": "meta/llama-3.1-8b-instruct", "transport": "grpc"}))

    def test_other_models_unchanged(self):
        with mock.patch.object(nvcf_grpc, "is_grpc_model", return_value=False):
            self.assertFalse(nvcf_grpc.use_grpc({"model": "openai/whisper-large-v3"}))
        with mock.patch.object(nvcf_grpc, "is_grpc_model", return_value=True):
            self.assertTrue(nvcf_grpc.use_grpc({"model": "nvidia/some-new-grpc-model"}))


class TestErrorDetail(unittest.TestCase):
    def test_nvidia_bodies(self):
        self.assertEqual(core.error_detail(json.dumps({"title": "Bad Request", "detail": "Invalid audio"})),
                         "Bad Request - Invalid audio")
        self.assertEqual(core.error_detail(json.dumps({"error": {"message": "model not found"}})),
                         "model not found")
        self.assertEqual(core.error_detail("plain text body"), "plain text body")
        self.assertEqual(core.error_detail(""), "(empty body)")


class TestParakeetVoiceCall(EntityCase):
    roles = dict(ROLES, asr=dict(PARAKEET))

    def setUp(self):
        super().setUp()
        self.riva = FakeRiva()
        self.fetched = []

        def fake_refresh(model):
            self.fetched.append(model)
            store.set_grpc_function(model, FID, source="ngc")
            return True, "ok"
        nvcf_grpc._auto_tried.clear()
        for p in (mock.patch.object(nvcf_grpc, "client", return_value=self.riva),
                  mock.patch.object(nvcf_grpc, "refresh", side_effect=fake_refresh),
                  mock.patch.dict(os.environ, {"NIMLAB_GRPC_AUTOFETCH": "1"})):
            p.start()
            self.addCleanup(p.stop)

    def test_parakeet_call_uses_grpc_and_fetches_the_id(self):
        dev = FakeDevice()
        keys = iter(["", "", "q"])
        lines = []
        n = voicecall.run_call(self.ent, input_fn=lambda p="": next(keys), out=lines.append, device=dev)
        text = "\n".join(lines)
        self.assertEqual(n, 1, text)
        self.assertIn("YOU  > please remind me to water the plants", text)
        self.assertEqual(self.fetched, ["nvidia/parakeet-ctc-1.1b-asr"])        # fetched once, on first use
        self.assertEqual(self.riva.calls[0][0], FID)
        with wave.open(io.BytesIO(self.riva.calls[0][1])) as w:
            self.assertEqual((w.getframerate(), w.getnchannels()), (16000, 1))
        self.assertFalse(self.backend.by("nvidia/parakeet-ctc-1.1b-asr"))   # nothing went over HTTP

    def test_call_page_webm_needs_ffmpeg_clear_error(self):
        store.set_grpc_function(PARAKEET["model"], FID, source="ngc")
        with mock.patch("shutil.which", return_value=None):
            r = self.ent.run_role("asr", audio=self._webm())
        self.assertFalse(r.ok)
        self.assertIn("ffmpeg", r.error)
        self.assertIn("pkg install ffmpeg", r.error)

    def _webm(self):
        p = os.path.join(self.tmp, "clip.webm")
        with open(p, "wb") as f:
            f.write(b"\x1aE\xdf\xa3" + b"\x00" * 200)    # EBML header: webm/opus from the call page
        return p


class TestHttpAsrError(EntityCase):
    roles = dict(ROLES, asr=dict(PARAKEET, transport="http", function_id="asr-fn-id"))

    def test_nvidia_error_body_is_shown(self):
        body = json.dumps({"type": "about:blank", "status": 400, "title": "Bad Request",
                           "detail": "Inference error: audio is not 16-bit PCM"})
        p = os.path.join(self.tmp, "a.wav")
        with open(p, "wb") as f:
            f.write(make_wav(0.5))
        with mock.patch.object(self.ent.client, "asr",
                               wraps=self.ent.client.asr) as asr, \
                mock.patch.object(self.ent.client.http, "request",
                                  return_value=core.HttpResult(400, body, error_kind="http")):
            r = self.ent.run_role("asr", audio=p)
        self.assertFalse(r.ok)
        self.assertTrue(asr.called)
        self.assertIn("audio is not 16-bit PCM", r.error)
        self.assertIn("gRPC", r.error)


if __name__ == "__main__":
    unittest.main()
