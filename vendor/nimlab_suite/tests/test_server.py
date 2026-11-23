"""v3.3: the OpenAI-compatible test server. A real ThreadingHTTPServer on a
free localhost port, called over HTTP like an external UI; every NVIDIA
and MCP call behind it goes to a fake (tests/fakes.py)."""
import base64
import io
import json
import os
import stat
import struct
import time
import unittest
import urllib.error
import urllib.request
import wave
from unittest import mock

from nimlab import server as S
from nimlab.api import ModelResult
from nimlab.core import HttpClient
from nimlab.mcp import MCPClient
from nimlab import servemenu
from tests.fakes import FakeMCPServer, FakeResponse, RouteOpener, make_wav
from tests.helpers import fresh_store
from tests.test_roles import make_entity

PNG = b"\x89PNG\r\n\x1a\n" + b"1" * 40
ROLES = {
    "persona": "meta/persona-model",
    "coding": "qwen/coder-model",
    "vision": "meta/vision-model",
    "embedding": "nvidia/embed-model",
    "reranker": "nvidia/llama-nemotron-rerank-1b-v2",
    "tts": "nvidia/magpie-tts-multilingual",
    "asr": {"backend": "model", "model": "nvidia/parakeet-ctc-1.1b-asr", "function_id": "asr-fn-id",
            "transport": "http"},
    "image_gen": "black-forest-labs/flux.1-dev",
}


class Backend:
    """Fake NVIDIA: answers by URL and records what each model was sent."""

    def __init__(self, fail_chat=False):
        self.fail_chat = fail_chat
        self.chats = []
        self.opener = RouteOpener([
            ("/chat/completions", self.chat),
            ("/embeddings", self.embed),
            ("/reranking", lambda req: {"rankings": [{"index": 1, "logit": 5.0}, {"index": 0, "logit": -2.0}]}),
            ("/audio/synthesize", lambda req: FakeResponse(make_wav(0.5))),
            ("/genai/", lambda req: {"artifacts": [{"base64": base64.b64encode(PNG).decode()}]}),
            ("nvcf", self.asr),
        ])

    def chat(self, req):
        body = json.loads(req.data.decode())
        self.chats.append(body)
        if self.fail_chat:
            return FakeResponse({"error": "upstream exploded"}, status=500)
        return {"choices": [{"message": {"role": "assistant", "content": f"hello from {body['model']} there"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 4, "total_tokens": 11}}

    def embed(self, req):
        body = json.loads(req.data.decode())
        return {"data": [{"index": i, "embedding": [0.1 * (i + 1), 0.2, 0.3]} for i, _ in enumerate(body["input"])]}

    def asr(self, req):
        return {"text": "transcribed words"}


def wait_log(n, timeout=3.0):
    """The server writes the log line just after the reply goes out."""
    end = time.time() + timeout
    rows = S.read_log(0)
    while len(rows) < n and time.time() < end:
        time.sleep(0.02)
        rows = S.read_log(0)
    return rows


class ServerCase(unittest.TestCase):
    roles = ROLES
    # the v3.3 tests below exercise the per-role debug names, which v3.7.2
    # keeps only as a hand-set legacy server_settings.expose (no menu, no
    # setup question); the single-model tests use the default (no expose)
    expose = {"roles": "all"}

    def setUp(self):
        cm = fresh_store()
        cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        self.backend = Backend()
        self.ent, self.out = make_entity(self, dict(self.roles), self.backend.opener)
        self.settings = S.load_settings()
        self.settings["log_to_console"] = False
        if self.expose:
            self.settings.setdefault("expose", {}).update(self.expose)
        self.srv = S.TestServer(self.ent, self.settings, port=0, host="127.0.0.1",
                                verified=getattr(self, "verified", {})).start()
        self.addCleanup(self.srv.stop)
        self.base = self.srv.local_base()
        self.key = self.settings["api_key"]

    def call(self, path, body=None, key="default", method=None, headers=None, raw=None, ctype=None):
        h = {}
        k = self.key if key == "default" else key
        if k:
            h["Authorization"] = "Bearer " + k
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        if data is not None:
            h["Content-Type"] = ctype or "application/json"
        h.update(headers or {})
        req = urllib.request.Request(self.base + path, data=data, headers=h,
                                     method=method or ("POST" if data is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()

    def j(self, raw):
        return json.loads(raw.decode())

    def assertOpenAIError(self, status, raw, want_status, code=None):
        self.assertEqual(status, want_status, raw)
        err = self.j(raw)["error"]
        for f in ("message", "type", "param", "code"):
            self.assertIn(f, err)
        if code:
            self.assertEqual(err["code"], code)
        return err

    @staticmethod
    def sse(raw):
        events, done = [], False
        for line in raw.decode().splitlines():
            if line.startswith("data: "):
                p = line[6:]
                if p == "[DONE]":
                    done = True
                else:
                    events.append(json.loads(p))
        return events, done


# ---------------------------------------------------------------------------
class TestSettings(unittest.TestCase):
    def test_created_on_first_use_with_private_key(self):
        with fresh_store():
            s = S.load_settings()
            self.assertTrue(s["api_key"].startswith("sk-testbed-"))
            self.assertGreater(len(s["api_key"]), 30)
            self.assertEqual(s["bind"], "127.0.0.1")
            self.assertFalse(s["lan"])
            p = S.settings_path()
            self.assertTrue(os.path.exists(p))
            self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
            self.assertEqual(S.load_settings()["api_key"], s["api_key"])     # stable across loads
            self.assertFalse(s["api_key"].startswith("nvapi-"))

    def test_missing_fields_filled_and_regenerate(self):
        with fresh_store():
            S.config.save_json(S.settings_path(), {"port": 9100, "expose": {"verified": True}})
            s = S.load_settings()
            self.assertEqual(s["port"], 9100)
            self.assertTrue(s["expose"]["verified"])        # a hand-set legacy key is read, not dropped
            self.assertNotIn("expose", S.default_settings())  # v3.7.2: no default, no menu
            old = s["api_key"]
            S.regenerate_key(s)
            self.assertNotEqual(S.load_settings()["api_key"], old)

    def test_apply_setting(self):
        s = S.default_settings()
        servemenu.apply_setting(s, "lan", "on")
        self.assertEqual((s["lan"], s["bind"]), (True, "0.0.0.0"))
        servemenu.apply_setting(s, "port", "9001")
        self.assertEqual(s["port"], 9001)
        for gone in (("expose", "roles", "persona,vision"), ("roles", "all"), ("expose", "verified", "on")):
            with self.assertRaises(ValueError) as cm:        # v3.7.2: one endpoint, one model name
                servemenu.apply_setting(s, *gone)
            self.assertIn("one model name", str(cm.exception))
        self.assertNotIn("expose", s)
        self.assertNotIn("expose", servemenu.SETTING_HELP)
        servemenu.apply_setting(s, "tools", "allow")
        self.assertEqual(s["agent_tool_calls"], "allow")
        servemenu.apply_setting(s, "log", "off")
        self.assertFalse(s["log_requests"])
        for bad in (("port", "80"), ("expose", "roles", "nope"), ("lan", "maybe"), ("colour", "red")):
            with self.assertRaises(ValueError):
                servemenu.apply_setting(s, *bad)


class TestAuthAndModels(ServerCase):
    def test_missing_and_wrong_key_refused(self):
        st, hd, raw = self.call("/models", key=None)
        self.assertOpenAIError(st, raw, 401, "missing_api_key")
        self.assertEqual(hd.get("www-authenticate"), "Bearer")
        st, _, raw = self.call("/models", key="sk-testbed-wrong-wrong-wrong-wrong")
        err = self.assertOpenAIError(st, raw, 401, "invalid_api_key")
        self.assertNotIn("wrong-wrong-wrong", err["message"])      # masked
        st, _, raw = self.call("/chat/completions", {"model": "testbed-persona", "messages": []}, key=None)
        self.assertEqual(st, 401)
        self.assertEqual(self.backend.chats, [])

    def test_regenerated_key_applies_live(self):
        old = self.key
        S.regenerate_key(self.settings)
        self.assertEqual(self.call("/models", key=old)[0], 401)
        self.assertEqual(self.call("/models", key=self.settings["api_key"])[0], 200)

    def test_models_list_one_per_set_role_plus_agent(self):
        st, _, raw = self.call("/models")
        self.assertEqual(st, 200)
        body = self.j(raw)
        self.assertEqual(body["object"], "list")
        ids = {m["id"]: m for m in body["data"]}
        for name in ("testbed", "testbed-persona", "testbed-coding", "testbed-vision", "testbed-embedding",
                     "testbed-reranker", "testbed-tts", "testbed-asr", "testbed-image-gen"):
            self.assertIn(name, ids)
            self.assertEqual(ids[name]["object"], "model")
        self.assertNotIn("testbed-reasoning", ids)          # role not set
        self.assertEqual(ids["testbed-embedding"]["testbed"]["type"], "embedding")
        self.assertEqual(ids["testbed"]["testbed"]["source"], "agent")
        self.assertNotIn("testbed-agent", ids)              # v3.3 name: still accepted, not listed
        st, _, raw = self.call("/models/testbed-coding")
        self.assertEqual((st, self.j(raw)["id"]), (200, "testbed-coding"))
        self.assertOpenAIError(*self.call("/models/nope")[::2], 404, "model_not_found")

    def test_legacy_exposure_never_hides_the_one_model(self):
        self.settings["expose"] = {"agent": False, "roles": ["persona"], "verified": False}
        ids = [m["id"] for m in self.j(self.call("/models")[2])["data"]]
        self.assertEqual(ids, ["testbed", "testbed-persona"])     # legacy agent off is ignored
        st, _, raw = self.call("/chat/completions", {"model": "testbed-coding", "messages": [
            {"role": "user", "content": "hi"}]})
        self.assertOpenAIError(st, raw, 404, "model_not_found")

    def test_health_needs_no_key(self):
        req = urllib.request.Request(self.base[:-3] + "/health")
        with urllib.request.urlopen(req, timeout=10) as r:
            self.assertEqual(json.loads(r.read())["server"], "nim-testbed")


class TestChat(ServerCase):
    def test_role_chat_non_streaming(self):
        st, hd, raw = self.call("/chat/completions", {"model": "testbed-coding", "messages": [
            {"role": "system", "content": "Be terse."}, {"role": "user", "content": "write hello world"}],
            "temperature": 0.1, "max_tokens": 50})
        self.assertEqual(st, 200, raw)
        body = self.j(raw)
        self.assertEqual(body["object"], "chat.completion")
        self.assertTrue(body["id"].startswith("chatcmpl-"))
        self.assertEqual(body["model"], "testbed-coding")
        self.assertEqual(body["choices"][0]["message"], {"role": "assistant",
                                                         "content": "hello from qwen/coder-model there"})
        self.assertEqual(body["choices"][0]["finish_reason"], "stop")
        self.assertEqual(body["usage"]["total_tokens"], 11)
        sent = self.backend.chats[-1]
        self.assertEqual(sent["model"], "qwen/coder-model")
        self.assertEqual(sent["temperature"], 0.1)
        self.assertEqual(sent["messages"][0]["role"], "system")
        self.assertIn("Be terse.", sent["messages"][0]["content"])
        self.assertEqual(sent["messages"][-1], {"role": "user", "content": "write hello world"})
        self.assertIn("x-request-id", hd)

    def test_role_chat_streaming_sse(self):
        st, hd, raw = self.call("/chat/completions", {"model": "testbed-persona", "stream": True,
                                                      "stream_options": {"include_usage": True},
                                                      "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(st, 200)
        self.assertIn("text/event-stream", hd["content-type"])
        self.assertEqual(hd.get("access-control-allow-origin"), "*")
        events, done = self.sse(raw)
        self.assertTrue(done)
        self.assertTrue(raw.decode().rstrip().endswith("data: [DONE]"))
        self.assertEqual(events[0]["choices"][0]["delta"], {"role": "assistant", "content": ""})
        for ev in events:
            self.assertEqual(ev["object"], "chat.completion.chunk")
            self.assertEqual(ev["id"], events[0]["id"])
        text = "".join((c.get("delta") or {}).get("content") or "" for ev in events for c in ev["choices"])
        self.assertEqual(text, "hello from meta/persona-model there")
        finish = [c["finish_reason"] for ev in events for c in ev["choices"] if c["finish_reason"]]
        self.assertEqual(finish, ["stop"])
        self.assertEqual(events[-1]["choices"], [])
        self.assertEqual(events[-1]["usage"]["total_tokens"], 11)
        self.assertGreater(len(events), 3)       # split into several content chunks

    def test_agent_pipeline_routes_through_orchestrator(self):
        with mock.patch.object(self.ent, "turn", wraps=self.ent.turn) as turn:
            st, _, raw = self.call("/chat/completions", {"model": "testbed-agent", "messages": [
                {"role": "user", "content": "earlier question"}, {"role": "assistant", "content": "earlier answer"},
                {"role": "user", "content": "write a python function that adds two numbers"}]})
        self.assertEqual(st, 200, raw)
        turn.assert_called_once()
        text, history = turn.call_args[0][:2]
        self.assertEqual(text, "write a python function that adds two numbers")
        self.assertEqual(history[:2], [{"role": "user", "content": "earlier question"},
                                   {"role": "assistant", "content": "earlier answer"}])
        body = self.j(raw)
        self.assertEqual(body["testbed"]["route"], "coding")
        self.assertIn("hello from", body["choices"][0]["message"]["content"])

    def test_agent_pipeline_streaming(self):
        st, _, raw = self.call("/chat/completions", {"model": "testbed-agent", "stream": True,
                                                     "messages": [{"role": "user", "content": "hello"}]})
        events, done = self.sse(raw)
        self.assertTrue(done)
        text = "".join((c.get("delta") or {}).get("content") or "" for ev in events for c in ev["choices"])
        self.assertIn("hello from meta/persona-model", text)

    def test_agent_tool_confirmation_is_answered_by_setting(self):
        seen = []
        self.ent.confirm_fn = lambda call: "terminal-prompt"

        def fake_turn(text, history, **kw):
            seen.append(self.ent.confirm_fn({"tool": "x"}))
            return {"route": {"role": "persona"}, "result": ModelResult(True, text="ok"), "pre": None, "files": []}
        with mock.patch.object(self.ent, "turn", side_effect=fake_turn):
            msg = {"model": "testbed-agent", "messages": [{"role": "user", "content": "hi"}]}
            self.call("/chat/completions", msg)
            self.settings["agent_tool_calls"] = "allow"
            self.call("/chat/completions", msg)
        self.assertEqual(seen, [False, True])
        self.assertEqual(self.ent.confirm_fn({}), "terminal-prompt")     # restored

    def test_agent_guardrail_block_is_content_filter(self):
        with mock.patch.object(self.ent, "turn", return_value={"route": {"role": "persona"}, "blocked": "unsafe",
                                                                "result": None, "pre": None, "files": []}):
            body = self.j(self.call("/chat/completions", {"model": "testbed-agent", "messages": [
                {"role": "user", "content": "bad"}]})[2])
        self.assertEqual(body["choices"][0]["finish_reason"], "content_filter")

    def test_vision_image_part(self):
        url = "data:image/png;base64," + base64.b64encode(PNG).decode()
        st, _, raw = self.call("/chat/completions", {"model": "testbed-vision", "messages": [
            {"role": "user", "content": [{"type": "text", "text": "what is this?"},
                                         {"type": "image_url", "image_url": {"url": url}}]}]})
        self.assertEqual(st, 200, raw)
        sent = self.backend.chats[-1]
        self.assertEqual(sent["model"], "meta/vision-model")
        self.assertIn(url, json.dumps(sent))

    def test_vision_without_image_and_local_paths_refused(self):
        st, _, raw = self.call("/chat/completions", {"model": "testbed-vision", "messages": [
            {"role": "user", "content": "no picture"}]})
        self.assertOpenAIError(st, raw, 400)
        st, _, raw = self.call("/chat/completions", {"model": "testbed-vision", "messages": [
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "/etc/passwd"}}]}]})
        self.assertOpenAIError(st, raw, 400, "invalid_media_url")
        self.assertEqual(self.backend.chats, [])

    def test_agent_image_goes_to_vision_role(self):
        url = "data:image/png;base64," + base64.b64encode(PNG).decode()
        body = self.j(self.call("/chat/completions", {"model": "testbed-agent", "messages": [
            {"role": "user", "content": [{"type": "text", "text": "describe"},
                                         {"type": "image_url", "image_url": {"url": url}}]}]})[2])
        self.assertEqual(body["testbed"]["route"], "vision")
        self.assertEqual([c["model"] for c in self.backend.chats][:1], ["meta/vision-model"])

    def test_wrong_route_for_model_type(self):
        st, _, raw = self.call("/chat/completions", {"model": "testbed-embedding", "messages": [
            {"role": "user", "content": "hi"}]})
        err = self.assertOpenAIError(st, raw, 400, "model_not_supported")
        self.assertIn("/v1/embeddings", err["message"])


class TestErrors(ServerCase):
    def test_error_format(self):
        cases = [
            (self.call("/chat/completions", raw=b"{not json"), 400, None),
            (self.call("/chat/completions", {"messages": [{"role": "user", "content": "x"}]}), 400, "missing_model"),
            (self.call("/chat/completions", {"model": "testbed-persona", "messages": []}), 400, None),
            (self.call("/chat/completions", {"model": "gpt-4o", "messages": [{"role": "user", "content": "x"}]}),
             404, "model_not_found"),
            (self.call("/nope", {}), 404, "unknown_url"),
            (self.call("/completions", {"model": "x", "prompt": "y"}), 404, "unknown_url"),
        ]
        for (st, _, raw), want, code in cases:
            err = self.assertOpenAIError(st, raw, want, code)
            self.assertEqual(err["type"], "invalid_request_error")

    def test_upstream_failure_is_502_json_and_stream_error_event(self):
        self.backend.fail_chat = True
        st, _, raw = self.call("/chat/completions", {"model": "testbed-persona", "messages": [
            {"role": "user", "content": "hi"}]})
        err = self.assertOpenAIError(st, raw, 502)
        self.assertEqual(err["type"], "upstream_error")
        st, _, raw = self.call("/chat/completions", {"model": "testbed-persona", "stream": True, "messages": [
            {"role": "user", "content": "hi"}]})
        events, done = self.sse(raw)
        self.assertTrue(done)
        self.assertIn("error", events[-1])

    def test_stream_unknown_model_is_plain_404(self):
        st, hd, raw = self.call("/chat/completions", {"model": "nope", "stream": True, "messages": [
            {"role": "user", "content": "hi"}]})
        self.assertOpenAIError(st, raw, 404, "model_not_found")
        self.assertIn("application/json", hd["content-type"])


class TestCors(ServerCase):
    def test_preflight_without_key(self):
        st, hd, raw = self.call("/chat/completions", key=None, method="OPTIONS", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,x-stainless-os"})
        self.assertEqual(st, 204)
        self.assertEqual(hd["access-control-allow-origin"], "*")
        self.assertIn("POST", hd["access-control-allow-methods"])
        self.assertIn("authorization", hd["access-control-allow-headers"].lower())
        self.assertIn("x-stainless-os", hd["access-control-allow-headers"].lower())

    def test_cors_on_errors_and_custom_origin(self):
        st, hd, _ = self.call("/models", key=None)
        self.assertEqual((st, hd["access-control-allow-origin"]), (401, "*"))
        self.settings["cors_origin"] = "http://my-ui.local"
        _, hd, _ = self.call("/models")
        self.assertEqual(hd["access-control-allow-origin"], "http://my-ui.local")


class TestOtherRoutes(ServerCase):
    def test_embeddings_float_and_base64(self):
        st, _, raw = self.call("/embeddings", {"model": "testbed-embedding", "input": ["a", "b"]})
        self.assertEqual(st, 200, raw)
        body = self.j(raw)
        self.assertEqual(body["object"], "list")
        self.assertEqual([d["index"] for d in body["data"]], [0, 1])
        self.assertEqual(body["data"][0]["object"], "embedding")
        self.assertEqual(len(body["data"][0]["embedding"]), 3)
        self.assertIn("usage", body)
        body = self.j(self.call("/embeddings", {"model": "testbed-embedding", "input": "a",
                                                "encoding_format": "base64"})[2])
        vec = struct.unpack("<3f", base64.b64decode(body["data"][0]["embedding"]))
        self.assertAlmostEqual(vec[1], 0.2, places=5)
        self.assertOpenAIError(*self.call("/embeddings", {"model": "testbed-embedding", "input": [1, 2]})[::2], 400)

    def test_rerank(self):
        st, _, raw = self.call("/rerank", {"model": "testbed-reranker", "query": "q", "documents": ["a", "b"],
                                           "top_n": 1})
        self.assertEqual(st, 200, raw)
        res = self.j(raw)["results"]
        self.assertEqual(res, [{"index": 1, "relevance_score": 5.0, "document": {"text": "b"}}])

    def test_audio_speech_wav_and_pcm(self):
        st, hd, raw = self.call("/audio/speech", {"model": "testbed-tts", "input": "hello", "voice": "alloy",
                                                  "response_format": "wav"})
        self.assertEqual(st, 200, raw[:200])
        self.assertEqual(hd["content-type"], "audio/wav")
        self.assertEqual(raw[:4], b"RIFF")
        st, hd, raw = self.call("/audio/speech", {"model": "testbed-tts", "input": "hello", "response_format": "pcm"})
        self.assertEqual(hd["content-type"], "audio/pcm")
        self.assertNotEqual(raw[:4], b"RIFF")
        self.assertOpenAIError(*self.call("/audio/speech", {"model": "testbed-tts", "input": ""})[::2], 400)
        self.assertOpenAIError(*self.call("/audio/speech", {"model": "testbed-persona", "input": "x"})[::2], 400,
                               "model_not_supported")

    def test_audio_speech_uses_cloned_voice(self):
        clip = os.path.join(self.out, "sevin.wav")
        with open(clip, "wb") as f:
            f.write(make_wav(5.0))
        seen = {}

        def synth(req):
            seen["url"], seen["body"] = req.full_url, req.data
            return FakeResponse(make_wav(0.5))
        self.backend.opener.routes.insert(0, ("/audio/synthesize", synth))
        self.ent.cluster["roles"]["tts"] = {"backend": "model", "model": "nvidia/magpie-tts-zeroshot",
                                           "voice_clone": {"path": clip, "seconds": 5.0}}
        st, _, raw = self.call("/audio/speech", {"model": "testbed-tts", "input": "hello", "voice": "alloy"})
        self.assertEqual(st, 200, raw[:300])
        self.assertIn(b'name="audio_prompt"; filename="sevin.wav"', seen["body"])
        self.assertIn(b"Magpie-ZeroShot", seen["body"])

    def test_transcriptions_multipart(self):
        boundary = "----testbedboundary"
        wavb = make_wav(1.0)
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\ntestbed-asr\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"language\"\r\n\r\nen\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"clip.wav\"\r\n"
                f"Content-Type: audio/wav\r\n\r\n").encode() + wavb + f"\r\n--{boundary}--\r\n".encode()
        with mock.patch.object(self.ent.client, "asr", return_value=ModelResult(True, text="transcribed words")) as asr:
            st, _, raw = self.call("/audio/transcriptions", raw=body,
                                   ctype=f"multipart/form-data; boundary={boundary}")
        self.assertEqual(st, 200, raw)
        self.assertEqual(self.j(raw), {"text": "transcribed words"})
        args, kw = asr.call_args
        import io as _io
        import wave as _wave
        with _wave.open(_io.BytesIO(args[0])) as w:   # always 16 kHz mono 16-bit WAV for ASR (v3.6.1)
            self.assertEqual((w.getframerate(), w.getnchannels(), w.getsampwidth()), (16000, 1, 2))
        self.assertEqual(kw["language"], "en-US")

    def test_images_generations(self):
        st, _, raw = self.call("/images/generations", {"model": "testbed-image-gen", "prompt": "a cube"})
        self.assertEqual(st, 200, raw)
        self.assertEqual(base64.b64decode(self.j(raw)["data"][0]["b64_json"]), PNG)
        body = self.j(self.call("/images/generations", {"model": "testbed-image-gen", "prompt": "a cube",
                                                        "response_format": "url"})[2])
        url = body["data"][0]["url"]
        with urllib.request.urlopen(url, timeout=10) as r:
            self.assertEqual(r.read(), PNG)


class TestMcpRoleAndVerified(ServerCase):
    roles = {"persona": {"backend": "mcp", "tool": "talk", "arg_map": {"prompt": "text"}}}
    expose = {"verified": True, "roles": "all"}
    verified = {"meta/llama-3.3-70b-instruct": {"url": "https://integrate.api.nvidia.com/v1/chat/completions",
                                                "kind": "chat"},
                "nvidia/some-tts": {"url": "https://x.nvcf/v1/audio/synthesize", "kind": "tts"}}

    def setUp(self):
        self.mcp = FakeMCPServer([{"name": "talk", "inputSchema": {"type": "object", "properties": {
            "prompt": {"type": "string"}}}}], handlers={"talk": lambda a: {"content": [
                {"type": "text", "text": "tool says " + a.get("prompt", "")}]}})
        super().setUp()
        self.ent.role_mcp = MCPClient(self.ent.cluster["mcp_settings"], http=HttpClient(opener=self.mcp, retries=0),
                                      env={})

    def test_mcp_backed_role_and_verified_passthrough(self):
        ids = [m["id"] for m in self.j(self.call("/models")[2])["data"]]
        self.assertIn("testbed-persona", ids)
        self.assertIn("meta/llama-3.3-70b-instruct", ids)
        self.assertNotIn("nvidia/some-tts", ids)          # not a chat/embed/rerank endpoint
        body = self.j(self.call("/chat/completions", {"model": "testbed-persona", "messages": [
            {"role": "user", "content": "ping"}]})[2])
        self.assertIn("tool says", body["choices"][0]["message"]["content"])
        self.assertEqual(self.mcp.calls[-1][0], "talk")
        body = self.j(self.call("/chat/completions", {"model": "meta/llama-3.3-70b-instruct", "messages": [
            {"role": "user", "content": "ping"}]})[2])
        self.assertEqual(body["choices"][0]["message"]["content"], "hello from meta/llama-3.3-70b-instruct there")


class TestLogSelfTestAndInfo(ServerCase):
    def test_request_log_has_latency_and_no_keys(self):
        self.call("/models")
        self.call("/models", key="sk-testbed-wrongwrongwrongwrongwrong")
        self.call("/chat/completions", {"model": "testbed-persona", "messages": [{"role": "user", "content": "hi"}]})
        rows = wait_log(3)
        self.assertEqual([r["status"] for r in rows], [200, 401, 200])
        self.assertEqual(rows[2]["model"], "testbed-persona")
        self.assertTrue(all(isinstance(r["latency_ms"], int) for r in rows))
        with open(S.log_path()) as f:
            text = f.read()
        self.assertNotIn(self.key, text)
        self.assertNotIn("wrongwrongwrongwrong", text)
        self.assertNotIn("nvapi-test", text)
        self.assertIn("3 request(s), 2 OK", S.log_summary(rows))
        self.assertEqual(len(S.format_log(rows)), 3)

    def test_log_off(self):
        self.settings["log_requests"] = False
        self.call("/models")
        time.sleep(0.2)
        self.assertEqual(S.read_log(0), [])

    def test_self_test_passes_against_running_server(self):
        lines = []
        rows = S.self_test(self.base, self.key, out=lines.append)
        status = {r[0].split(" (")[0]: r[1] for r in rows}
        self.assertEqual(status["chat"], "PASS", lines)
        for k in ("GET /v1/models", "wrong key is refused", "CORS preflight", "one model for the whole stack",
                  "streamed chat", "embeddings", "identity comes from soul.md"):
            self.assertEqual(status[k], "PASS", (k, lines))
        self.assertIn("(testbed)", [r[0] for r in rows if r[0].startswith("chat")][0])
        self.assertNotIn("FAIL", status.values(), lines)

    def test_self_test_reports_failure(self):
        self.backend.fail_chat = True
        rows = S.self_test(self.base, self.key, out=lambda *_: None)
        self.assertEqual([r[1] for r in rows if r[0].startswith("chat")], ["FAIL"])

    def test_connection_block_and_ui_configs(self):
        models = self.srv.app.models()
        block = self.srv.block()
        self.assertIn(f"http://127.0.0.1:{self.srv.bound_port}/v1", block)
        self.assertIn(self.key, block)
        self.assertIn("Model:                   testbed", block)
        self.assertIn("/call?t=", block)
        self.assertIn("localhost only", block)
        cfg = S.ui_configs(self.settings, models, self.srv.bound_port)
        compact = json.loads(cfg.splitlines()[3])
        self.assertEqual(compact, {"base_url": f"http://127.0.0.1:{self.srv.bound_port}/v1", "api_key": self.key,
                                   "model": "testbed"})
        for ui in ("Open WebUI", "SillyTavern", "Chatbox", "LibreChat", "baseURL"):
            self.assertIn(ui, cfg)
        with mock.patch.object(S, "lan_ip", return_value="192.168.1.50"):
            S.set_lan(self.settings, True)
            self.assertIn("http://192.168.1.50:8765/v1", S.connection_block(self.settings, models, 8765))
            self.assertIn("192.168.1.50", S.ui_configs(self.settings, models, 8765))
            self.assertIn("https://abc.trycloudflare.com/v1",
                          S.connection_block(self.settings, models, 8765, "https://abc.trycloudflare.com"))


class TestHelpers(unittest.TestCase):
    def test_stream_pieces_keep_text(self):
        t = "Hello there,  world!\nLine two  here."
        self.assertEqual("".join(S.stream_pieces(t, 2)), t)
        self.assertEqual(S.stream_pieces("", 3), [])

    def test_split_content_parts(self):
        txt, media = S.split_content([{"type": "text", "text": "a"}, {"type": "image_url", "image_url": "https://x/y.png"},
                                      {"type": "input_audio", "input_audio": {"data": base64.b64encode(b"abc").decode(),
                                                                              "format": "wav"}}])
        self.assertEqual(txt, "a")
        self.assertEqual(media, [("image", "https://x/y.png"), ("audio", (b"abc", "wav"))])

    def test_tunnel_missing_explains_install(self):
        with mock.patch.object(S.shutil, "which", return_value=None):
            out = []
            srv = mock.Mock(running=True, bound_port=8765)
            self.assertIsNone(servemenu.start_tunnel(srv, lambda p: "y", out.append))
        self.assertIn("pkg install cloudflared", "\n".join(out))

    def test_tunnel_url_parsed(self):
        m = S.Tunnel.URL_RX.search("INF |  https://brave-fox-12.trycloudflare.com  |")
        self.assertEqual(m.group(0), "https://brave-fox-12.trycloudflare.com")

    def test_convert_audio_pcm(self):
        wavb = make_wav(0.1)
        data, mime, note = S.convert_audio(wavb, "pcm")
        with wave.open(io.BytesIO(wavb)) as w:
            self.assertEqual(data, w.readframes(w.getnframes()))
        self.assertEqual((mime, note), ("audio/pcm", None))


if __name__ == "__main__":
    unittest.main()
