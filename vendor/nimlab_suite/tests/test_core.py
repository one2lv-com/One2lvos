import json
import os
import unittest
import urllib.error
from unittest import mock

from nimlab import api
from nimlab.api import NimClient
from nimlab.core import HttpClient, build_multipart, iter_sse, load_api_key, mask, redact
from tests.fakes import FakeOpener, FakeResponse, chat_body, http_error, timeout_error

KEY = "nvapi-TESTKEY0123456789abcdefWXYZ"


def client(script, retries=2, **kw):
    opener = FakeOpener(script)
    return HttpClient(timeout=5, retries=retries, backoff=0.01, opener=opener, sleep=lambda s: None, **kw), opener


class KeyTests(unittest.TestCase):
    def test_load_prefers_nvidia_then_ngc_and_sanitizes(self):
        self.assertEqual(load_api_key({"NVIDIA_API_KEY": ' "abc"\r\n', "NGC_API_KEY": "zzz"}), "abc")
        self.assertEqual(load_api_key({"NGC_API_KEY": "zzz"}), "zzz")
        self.assertEqual(load_api_key({}), "")

    def test_mask_never_reveals_body(self):
        m = mask(KEY)
        self.assertEqual(m, "nvapi-...WXYZ")
        self.assertNotIn("TESTKEY", m)
        self.assertEqual(mask("short"), "****")
        self.assertEqual(mask(""), "[NOT SET]")

    def test_redact_removes_env_keys(self):
        with mock.patch.dict(os.environ, {"NVIDIA_API_KEY": KEY, "MCP_API_KEY": "mcp-secret-123456"}):
            out = redact(f"auth failed for {KEY} and mcp-secret-123456")
        self.assertNotIn(KEY, out)
        self.assertNotIn("mcp-secret-123456", out)


class HttpClientTests(unittest.TestCase):
    def test_success(self):
        c, op = client([FakeResponse({"ok": 1})])
        r = c.post_json("https://x/api", {"a": 1}, {"Authorization": "Bearer k"})
        self.assertTrue(r.ok)
        self.assertEqual(r.json(), {"ok": 1})
        self.assertEqual(op.body(0), {"a": 1})
        self.assertEqual(op.requests[0]["timeout"], 5)

    def test_retries_on_503_then_succeeds(self):
        c, op = client([http_error(503), http_error(429, headers={"Retry-After": "0"}), FakeResponse({"ok": 1})])
        r = c.get("https://x")
        self.assertTrue(r.ok)
        self.assertEqual(r.attempts, 3)
        self.assertEqual(len(op.requests), 3)

    def test_gives_up_after_retries(self):
        c, op = client([http_error(500, b"boom") for _ in range(3)])
        r = c.get("https://x")
        self.assertFalse(r.ok)
        self.assertEqual((r.status, r.error_kind), (500, "http"))
        self.assertEqual(len(op.requests), 3)
        self.assertIn("boom", r.describe())

    def test_no_retry_on_4xx(self):
        c, op = client([http_error(401, b"bad key")])
        r = c.get("https://x")
        self.assertEqual(r.status, 401)
        self.assertEqual(len(op.requests), 1)

    def test_timeout_is_an_error_object_not_an_exception(self):
        c, op = client([timeout_error()])
        r = c.get("https://x")
        self.assertFalse(r.ok)
        self.assertEqual(r.error_kind, "timeout")
        self.assertEqual(len(op.requests), 1)  # timeouts are not retried by default

    def test_network_error_retried(self):
        c, op = client([urllib.error.URLError("dns"), FakeResponse({"ok": 1})])
        self.assertTrue(c.get("https://x").ok)

    def test_response_size_cap(self):
        c, _ = client([FakeResponse(b"x" * 100)], max_bytes=10)
        r = c.get("https://x")
        self.assertEqual(r.error_kind, "too_large")
        self.assertFalse(r.ok)

    def test_error_text_is_redacted(self):
        with mock.patch.dict(os.environ, {"NVIDIA_API_KEY": KEY}):
            c, _ = client([http_error(400, f"invalid key {KEY}".encode())])
            r = c.get("https://x")
            self.assertNotIn(KEY, r.describe())


class WireFormatTests(unittest.TestCase):
    def test_multipart_is_safe_for_any_text(self):
        nasty = "'''; import os; os.system('rm -rf ~') #\r\n--boundary\""
        body, ctype = build_multipart({"text": nasty, "voice": "Aria"})
        boundary = ctype.split("boundary=")[1]
        self.assertIn(nasty.encode(), body)
        self.assertNotIn(boundary, nasty)
        self.assertTrue(body.endswith(f"--{boundary}--\r\n".encode()))
        self.assertEqual(body.count(f"--{boundary}\r\n".encode()), 2)

    def test_sse_parser(self):
        lines = [b": comment\n", b"event: message\n", b"data: {\"a\":\n", b"data: 1}\n", b"\n", b"data: [DONE]\n", b"\n"]
        events = list(iter_sse(lines))
        self.assertEqual(json.loads(events[0]["data"]), {"a": 1})
        self.assertEqual(events[1]["data"], "[DONE]")


class NimClientTests(unittest.TestCase):
    def make(self, script):
        http, op = client(script, retries=0)
        cluster = {"voice_settings": {"voice_name": "V", "language": "en-US", "tts_url": "https://tts/x"}}
        return NimClient(api_key=KEY, http=http, router=mock.Mock(gateway=lambda *a: "https://int/v1"),
                         cluster=cluster), op

    def test_chat_ok(self):
        c, op = self.make([FakeResponse(chat_body("hello", {"completion_tokens": 4}))])
        r = c.chat("m", [{"role": "user", "content": "hi"}])
        self.assertTrue(r.ok)
        self.assertEqual(r.text, "hello")
        self.assertEqual(op.header(0, "Authorization"), f"Bearer {KEY}")
        self.assertEqual(op.requests[0]["url"], "https://int/v1/chat/completions")

    def test_chat_timeout_returns_failed_result(self):
        c, _ = self.make([timeout_error()])
        r = c.chat("m", [])
        self.assertFalse(r.ok)
        self.assertEqual(r.text, "")
        self.assertIn("timeout", r.error)

    def test_chat_bad_shape(self):
        c, _ = self.make([FakeResponse({"nope": 1})])
        self.assertFalse(c.chat("m", []).ok)

    def test_parse_model_tool_call_output(self):
        body = {"choices": [{"message": {"content": None, "tool_calls": [
            {"function": {"name": "markdown", "arguments": json.dumps([{"text": "LINE ONE"}, {"text": "LINE TWO"}])}}]}}]}
        c, _ = self.make([FakeResponse(body)])
        self.assertEqual(c.chat("m", []).text, "LINE ONE\nLINE TWO")

    def test_embed_retries_without_input_type(self):
        ok = {"data": [{"index": 1, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]}]}
        c, op = self.make([http_error(400, b"input_type not allowed"), FakeResponse(ok)])
        r = c.embed("e", ["a", "b"], input_type="query")
        self.assertTrue(r.ok)
        self.assertEqual(r.data, [[1, 0], [0, 1]])  # sorted by index
        self.assertIn("input_type", op.body(0))
        self.assertNotIn("input_type", op.body(1))

    def test_tts_multipart(self):
        wav = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 400
        c, op = self.make([FakeResponse(wav, headers={"Content-Type": "audio/wav"})])
        r = c.tts("it's \"quoted\" '''text'''", voice="Magpie-Multilingual.EN-US.Jason")
        self.assertTrue(r.ok)
        self.assertEqual(op.requests[0]["url"], "https://tts/x")
        self.assertIn("multipart/form-data", op.header(0, "Content-Type"))
        self.assertIn(b"'''text'''", op.requests[0]["data"])
        self.assertIn(b"EN-US.Jason", op.requests[0]["data"])

    def test_tts_rejects_tiny_audio(self):
        c, _ = self.make([FakeResponse(b"{}")])
        self.assertFalse(c.tts("x").ok)

    def test_wav_duration_reads_header(self):
        import io
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"\x00\x00" * 44100)
        self.assertAlmostEqual(api.wav_duration(buf.getvalue()), 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
