"""v3.4: the whole stack as ONE model at ONE endpoint, the persona as the only
voice, attachments, generated media, audio output, streaming, the /call page,
the terminal call loop and testbed attachments. Real HTTP server on
localhost; every NVIDIA call goes to a fake."""
import base64
import io
import json
import os
import re
import time
import unittest
import urllib.error
import urllib.request
import zipfile
import zlib
from unittest import mock

from nimlab import attach, server as S, unified, voicecall
from tests.fakes import FakeResponse, RouteOpener, make_wav
from tests.helpers import fresh_store
from tests.test_roles import make_entity

PNG = S.test_png()
SOUL = '# SOUL.md - Entity: "Quill"\nYou are **Quill**, a dry-witted lab assistant.'
ROLES = {
    "persona": "meta/persona-model",
    "intent_router": "meta/router-model",
    "reasoning": "deepseek/reason-model",
    "coding": "qwen/coder-model",
    "vision": "meta/vision-model",
    "ocr": "acme/ocr-model",
    "chart_parser": "acme/chart-model",
    "video": "acme/video-model",
    "omni_audio": "acme/omni-model",
    "embedding": "nvidia/embed-model",
    "reranker": "nvidia/llama-nemotron-rerank-1b-v2",
    "tts": "nvidia/magpie-tts-multilingual",
    "asr": {"backend": "model", "model": "nvidia/parakeet-ctc-1.1b-asr", "function_id": "asr-fn-id",
            "transport": "http"},
    "image_gen": "black-forest-labs/flux.1-dev",
}
REPLIES = {
    "meta/vision-model": "VISION: a white square with a dark bar",
    "acme/ocr-model": "OCR: INVOICE 42 TOTAL $19.99",
    "acme/chart-model": "CHART: | year | sales |\n| 2024 | 7 |",
    "acme/video-model": "VIDEO: a cat jumps onto a table",
    "acme/omni-model": "OMNI: lo-fi hip hop, 80 bpm",
    "deepseek/reason-model": "REASONING: 17 is prime because no number from 2 to 4 divides it",
    "qwen/coder-model": "CODER:\n```python\nprint('hi')\n```",
}


def sse(text):
    out = ""
    for w in re.findall(r"\S+\s*", text):
        out += "data: " + json.dumps({"choices": [{"delta": {"content": w}}]}) + "\n\n"
    return out + "data: [DONE]\n\n"


class Backend:
    """Fake NVIDIA. Records every chat body; the router answers
    self.route; the persona answers from its system prompt so tests can
    see soul.md reached it."""

    def __init__(self):
        self.chats = []
        self.route = "persona"
        self.stream_ok = True
        self.asr_text = "please remind me to water the plants"
        self.opener = RouteOpener([
            ("/chat/completions", self.chat),
            ("/embeddings", self.embed),
            ("/reranking", lambda req: {"rankings": [{"index": 0, "logit": 5.0}]}),
            ("/audio/synthesize", lambda req: FakeResponse(make_wav(0.5))),
            ("/genai/", lambda req: {"artifacts": [{"base64": base64.b64encode(PNG).decode()}]}),
            ("nvcf", lambda req: {"text": self.asr_text}),
        ])

    def by(self, model):
        return [c for c in self.chats if c["model"] == model]

    def models(self):
        return [c["model"] for c in self.chats]

    def embed(self, req):
        body = json.loads(req.data.decode())
        n = len(body["input"]) if isinstance(body["input"], list) else 1
        return {"data": [{"embedding": [0.1 * (i + 1), 0.2, 0.3], "index": i} for i in range(n)]}

    def chat(self, req):
        body = json.loads(req.data.decode())
        self.chats.append(body)
        m = body["model"]
        if m == "meta/router-model":
            text = self.route
        elif m == "meta/persona-model":
            sys = body["messages"][0]["content"] if body["messages"][0]["role"] == "system" else ""
            text = ("I'm Quill, your lab assistant." if "Quill" in sys else "I am a generic model.") + " Here you go."
            if body.get("stream") and self.stream_ok:
                return FakeResponse(sse(text), headers={"Content-Type": "text/event-stream"})
        else:
            text = REPLIES.get(m, f"hello from {m}")
        return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


def make_pdf(text=None, jpeg=None):
    """A minimal one-page PDF with a Flate text stream or a DCT image."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>"]
    if text is not None:
        content = b"BT /F1 12 Tf 72 720 Td (" + text.encode() + b") Tj 0 -14 Td (Second line here) Tj ET"
        z = zlib.compress(content)
        objs.append(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(z) + z + b"\nendstream")
    else:
        objs.append(b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /Filter /DCTDecode /Length %d >>\n"
                    b"stream\n" % len(jpeg) + jpeg + b"\nendstream")
    out = b"%PDF-1.4\n"
    for i, o in enumerate(objs, 1):
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    return out + b"trailer << /Root 1 0 R >>\n%%EOF"


def data_url(mime, data):
    return f"data:{mime};base64," + base64.b64encode(data).decode()


class EntityCase(unittest.TestCase):
    roles = ROLES
    settings = None

    def setUp(self):
        cm = fresh_store()
        self.tmp = cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        self.backend = Backend()
        self.ent, _ = make_entity(self, dict(self.roles), self.backend.opener)
        self.ent.soul = SOUL
        s = S.load_settings()
        s["log_to_console"] = False
        for k, v in (self.settings or {}).items():
            if isinstance(v, dict):
                s.setdefault(k, {}).update(v)
            else:
                s[k] = v
        self.srv = S.TestServer(self.ent, s, port=0, host="127.0.0.1", quiet=True)
        self.srv.start()
        self.addCleanup(self.srv.stop)
        self.base = self.srv.local_base()[:-3]
        self.key = s["api_key"]

    def call(self, path, body=None, key="default", method=None, headers=None):
        k = self.key if key == "default" else key
        h = {"Content-Type": "application/json"}
        if k:
            h["Authorization"] = f"Bearer {k}"
        h.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=h,
                                     method=method or ("POST" if data else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def ask(self, content, history=(), **extra):
        body = {"model": "testbed", "messages": list(history) + [{"role": "user", "content": content}]}
        body.update(extra)
        st, _, raw = self.call("/v1/chat/completions", body)
        j = json.loads(raw)
        self.assertEqual(st, 200, j)
        return j

    def persona_msgs(self):
        p = self.backend.by("meta/persona-model")
        self.assertTrue(p, "the persona never ran")
        return p[-1]["messages"]

    def trace_roles(self, j):
        return [t["role"] for t in j["testbed_trace"]]


class TestOneModel(EntityCase):
    def test_models_lists_only_the_one_model(self):
        st, _, raw = self.call("/v1/models")
        ids = [m["id"] for m in json.loads(raw)["data"]]
        self.assertEqual(ids, ["testbed"])

    def test_model_name_is_configurable_and_roles_are_a_legacy_debug_option(self):
        self.srv.app.settings["model_name"] = "quill"
        ids = [m["id"] for m in json.loads(self.call("/v1/models")[2])["data"]]
        self.assertEqual(ids, ["quill"])
        self.srv.app.settings["expose"] = {"roles": "all"}      # hand-set legacy key, still read
        ids = [m["id"] for m in json.loads(self.call("/v1/models")[2])["data"]]
        self.assertEqual(ids[0], "quill")
        self.assertIn("testbed-vision", ids)

    def test_old_agent_name_still_works(self):
        st, _, raw = self.call("/v1/chat/completions", {"model": "testbed-agent",
                                                        "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(st, 200)

    def test_one_model_on_compat_routes(self):
        st, _, raw = self.call("/v1/embeddings", {"model": "testbed", "input": "hi"})
        self.assertEqual(st, 200, raw)

    def test_settings_migrate_legacy_expose(self):
        # v3.7.2: an old expose block that only says the defaults is dropped,
        # a broken one never crashes, a hand-set debug option is kept
        s = S.default_settings()
        s["expose"] = {"agent": True, "roles": "off", "verified": False}
        S.save_settings(s)
        self.assertNotIn("expose", S.load_settings())
        s["expose"] = "all"
        S.save_settings(s)
        self.assertNotIn("expose", S.load_settings())
        s["expose"] = {"roles": ["vision"]}
        S.save_settings(s)
        self.assertEqual(S.load_settings()["expose"]["roles"], ["vision"])

    def test_default_install_serves_exactly_one_name_for_every_route(self):
        # v3.7.2: one endpoint, one model name wrapping every role
        st, _, raw = self.call("/v1/models")
        data = json.loads(raw)["data"]
        self.assertEqual(len(data), 1)
        name = data[0]["id"]
        self.assertEqual(name, "testbed")
        st, _, raw = self.call("/v1/chat/completions", {"model": name,
                                                        "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(st, 200, raw)
        self.assertTrue(json.loads(raw)["choices"][0]["message"]["content"])
        st, _, raw = self.call("/v1/embeddings", {"model": name, "input": ["a", "b"]})
        self.assertEqual(st, 200, raw)
        self.assertEqual(len(json.loads(raw)["data"]), 2)
        self.assertTrue(json.loads(raw)["data"][0]["embedding"])

    def test_self_test_uses_the_one_name_and_never_skips_for_exposure(self):
        lines = []
        rows = S.self_test(self.base + "/v1", self.key, out=lines.append, full=False)
        status = {r[0].split(" (")[0]: (r[1], r[0], r[2]) for r in rows}
        self.assertEqual(status["embeddings"][0], "PASS", lines)
        self.assertIn("(testbed)", status["embeddings"][1])          # through the agent name
        self.assertEqual(status["one model for the whole stack"][0], "PASS")
        text = "\n".join(lines)
        self.assertNotIn("not exposed", text)
        self.assertNotIn("expose roles", text)
        self.ent.roles.pop("embedding", None)
        lines = []
        rows = S.self_test(self.base + "/v1", self.key, out=lines.append, full=False)
        emb = [r for r in rows if r[0].startswith("embeddings")][0]
        self.assertEqual(emb[1], "SKIP")
        self.assertIn("role isn't set", emb[2])
        self.assertIn("nimlab setup roles", emb[2])

    def test_unset_role_through_the_one_name_says_which_role(self):
        self.ent.roles.pop("reranker", None)
        st, _, raw = self.call("/v1/rerank", {"model": "testbed", "query": "q", "documents": ["a"]})
        err = json.loads(raw)["error"]
        self.assertEqual((st, err["code"]), (400, "role_not_set"))
        self.assertIn("Reranker Model role isn't set", err["message"])
        self.assertIn("nimlab setup roles", err["message"])


class TestSingleEntity(EntityCase):
    def test_persona_speaks_with_soul_and_persona_prompt(self):
        self.ent.prompts["persona"] = "PERSONA-PROMPT-MARK"
        j = self.ask("Who are you?")
        self.assertIn("Quill", j["choices"][0]["message"]["content"])
        sys = self.persona_msgs()[0]["content"]
        self.assertIn("You are **Quill**", sys)
        self.assertIn("PERSONA-PROMPT-MARK", sys)
        self.assertEqual(j["testbed"]["answered_by"], "persona")
        # no role names leak into the visible reply
        self.assertNotIn("testbed_trace", j["choices"][0]["message"]["content"])

    def test_client_system_message_is_added_not_replacing(self):
        self.ask("hi", history=[{"role": "system", "content": "APP-SYSTEM-MARK"}])
        sys = self.persona_msgs()[0]["content"]
        self.assertIn("APP-SYSTEM-MARK", sys)
        self.assertIn("You are **Quill**", sys)
        self.assertLess(sys.index("Quill"), sys.index("APP-SYSTEM-MARK"))
        self.srv.app.settings["entity"]["client_system"] = "ignore"
        self.ask("hi again", history=[{"role": "system", "content": "APP-SYSTEM-MARK"}])
        self.assertNotIn("APP-SYSTEM-MARK", self.persona_msgs()[0]["content"])

    def test_reasoning_route_ends_with_persona(self):
        self.backend.route = "reasoning"
        self.ent.prompts["reasoning"] = "REASON-PROMPT-MARK"
        j = self.ask("Is 17 prime? Think it through.")
        models = self.backend.models()
        self.assertEqual(models[-1], "meta/persona-model")
        self.assertIn("deepseek/reason-model", models)
        self.assertLess(models.index("deepseek/reason-model"), models.index("meta/persona-model"))
        self.assertIn("Quill", j["choices"][0]["message"]["content"])
        user = self.persona_msgs()[-1]["content"]
        self.assertIn("17 is prime because", user)          # the ability's output reached the persona
        rsys = self.backend.by("deepseek/reason-model")[0]["messages"][0]["content"]
        self.assertIn("REASON-PROMPT-MARK", rsys)            # the ability used its own prompt
        self.assertNotIn("Quill", rsys)                      # and not the persona's identity
        self.assertEqual(j["testbed"]["answered_by"], "persona")

    def test_coding_route_ends_with_persona_and_keeps_code(self):
        self.backend.route = "coding"
        j = self.ask("write a hello world")
        self.assertEqual(self.backend.models()[-1], "meta/persona-model")
        self.assertIn("```python\nprint('hi')\n```", self.persona_msgs()[-1]["content"])
        self.assertIn("keep code", self.persona_msgs()[-1]["content"].lower())
        self.assertEqual(self.trace_roles(j)[-1], "persona")

    def test_memory_stores_each_turn_once(self):
        mem = self.ent.memory
        n0 = len(mem.memories)
        hist = [{"role": "user", "content": "my cat is called Miso"}]
        body = {"model": "testbed", "messages": hist}
        self.call("/v1/chat/completions", body)
        self.assertEqual(len(mem.memories), n0 + 1)
        self.call("/v1/chat/completions", body)              # regenerate: same turn
        self.assertEqual(len(mem.memories), n0 + 1)
        hist2 = hist + [{"role": "assistant", "content": "Nice."}, {"role": "user", "content": "and a dog, Rex"}]
        self.call("/v1/chat/completions", {"model": "testbed", "messages": hist2})
        self.assertEqual(len(mem.memories), n0 + 2)          # only the new turn
        self.assertIn("Rex", mem.memories[-1]["text"])
        self.assertNotIn("Miso", mem.memories[-1]["text"])

    def test_persona_missing_is_explained(self):
        self.ent.roles.pop("persona", None)
        with mock.patch.object(type(self.ent), "is_set", lambda e, k: k != "persona" and k in ROLES):
            st, _, raw = self.call("/v1/chat/completions", {"model": "testbed",
                                                            "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(st, 503)
        err = json.loads(raw)["error"]
        self.assertEqual(err["code"], "role_not_set")
        self.assertIn("Conversational Persona", err["message"])


class TestModalities(EntityCase):
    def img(self, text):
        return self.ask([{"type": "text", "text": text},
                         {"type": "image_url", "image_url": {"url": data_url("image/png", PNG)}}])

    def test_image_goes_to_vision(self):
        j = self.img("what is this?")
        self.assertIn("vision", self.trace_roles(j))
        self.assertIn("VISION: a white square", self.persona_msgs()[-1]["content"])
        self.assertEqual(self.trace_roles(j)[-1], "persona")

    def test_image_with_read_words_goes_to_ocr(self):
        j = self.img("read the text on this receipt")
        self.assertIn("ocr", self.trace_roles(j))
        self.assertNotIn("vision", self.trace_roles(j))
        self.assertIn("INVOICE 42", self.persona_msgs()[-1]["content"])

    def test_image_with_chart_words_goes_to_chart_parser(self):
        j = self.img("what does this chart show?")
        self.assertIn("chart_parser", self.trace_roles(j))
        self.assertIn("| 2024 | 7 |", self.persona_msgs()[-1]["content"])

    def test_router_picks_image_ability_when_words_dont(self):
        self.backend.route = "ocr"
        j = self.img("thoughts?")
        self.assertIn("ocr", self.trace_roles(j))

    def test_http_image_url_is_passed_through(self):
        j = self.ask([{"type": "text", "text": "describe"},
                      {"type": "image_url", "image_url": {"url": "https://example.com/cat.png"}}])
        self.assertIn("vision", self.trace_roles(j))
        sent = json.dumps(self.backend.by("meta/vision-model")[-1])
        self.assertIn("https://example.com/cat.png", sent)

    def test_local_path_is_refused(self):
        st, _, raw = self.call("/v1/chat/completions", {"model": "testbed", "messages": [
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "/etc/passwd"}}]}]})
        self.assertEqual(st, 400)
        # and paths typed in text are never read on the server
        j = self.ask("look at /etc/hostname please")
        self.assertFalse(set(self.trace_roles(j)) & {"vision", "ocr", "document", "video", "asr"})

    def test_speech_is_transcribed_then_answered(self):
        j = self.ask([{"type": "input_audio", "input_audio": {"data": base64.b64encode(make_wav(1.0)).decode(),
                                                              "format": "wav"}}])
        self.assertIn("asr", self.trace_roles(j))
        self.assertEqual(j["testbed"]["transcript"], self.backend.asr_text)
        self.assertIn("water the plants", self.persona_msgs()[-1]["content"])

    def test_music_question_goes_to_omni_audio(self):
        j = self.ask([{"type": "text", "text": "what genre is this music?"},
                      {"type": "input_audio", "input_audio": {"data": base64.b64encode(make_wav(1.0)).decode(),
                                                              "format": "wav"}}])
        self.assertIn("omni_audio", self.trace_roles(j))
        self.assertNotIn("asr", self.trace_roles(j))
        self.assertIn("lo-fi hip hop", self.persona_msgs()[-1]["content"])

    def test_audio_data_url_part(self):
        j = self.ask([{"type": "file", "file": {"filename": "memo.wav",
                                                "file_data": data_url("audio/wav", make_wav(1.0))}}])
        self.assertIn("asr", self.trace_roles(j))

    def test_video_goes_to_video_model(self):
        j = self.ask([{"type": "text", "text": "what happens?"},
                      {"type": "video_url", "video_url": {"url": data_url("video/mp4", b"\x00\x00\x00\x18ftypmp42" +
                                                                        b"0" * 50)}}])
        self.assertIn("video", self.trace_roles(j))
        self.assertIn("a cat jumps", self.persona_msgs()[-1]["content"])

    def test_pdf_text_layer(self):
        j = self.ask([{"type": "text", "text": "summarize"},
                      {"type": "file", "file": {"filename": "report.pdf",
                                                "file_data": data_url("application/pdf",
                                                                      make_pdf("Quarterly revenue rose 12%"))}}])
        self.assertIn("document", self.trace_roles(j))
        user = self.persona_msgs()[-1]["content"]
        self.assertIn("Quarterly revenue rose 12%", user)
        self.assertIn("Second line here", user)

    def test_scanned_pdf_goes_to_ocr(self):
        jpeg = b"\xff\xd8\xff\xe0" + b"J" * 60 + b"\xff\xd9"
        j = self.ask([{"type": "file", "file": {"filename": "scan.pdf",
                                                "file_data": data_url("application/pdf", make_pdf(jpeg=jpeg))}}])
        self.assertIn("ocr", self.trace_roles(j))
        self.assertIn("INVOICE 42", self.persona_msgs()[-1]["content"])

    def test_text_file_and_unsupported_file(self):
        j = self.ask([{"type": "text", "text": "check these"},
                      {"type": "file", "file": {"filename": "data.csv",
                                                "file_data": base64.b64encode(b"a,b\n1,2\n").decode()}},
                      {"type": "file", "file": {"filename": "blob.bin",
                                                "file_data": base64.b64encode(b"\x00\x01\x02\xff" * 10).decode()}}])
        self.assertIn("a,b\n1,2", self.persona_msgs()[-1]["content"])
        content = j["choices"][0]["message"]["content"]
        self.assertIn("blob.bin: .bin files aren't supported", content)

    def test_docx_is_read(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w:document><w:body><w:p><w:r><w:t>Lease ends in May</w:t></w:r>"
                                            "</w:p></w:body></w:document>")
        self.ask([{"type": "file", "file": {"filename": "lease.docx",
                                           "file_data": base64.b64encode(buf.getvalue()).decode()}}])
        self.assertIn("Lease ends in May", self.persona_msgs()[-1]["content"])

    def test_mixed_parts_one_reply(self):
        j = self.ask([{"type": "text", "text": "here's a photo, a voice note and notes"},
                      {"type": "image_url", "image_url": {"url": data_url("image/png", PNG)}},
                      {"type": "input_audio", "input_audio": {"data": base64.b64encode(make_wav(1.0)).decode(),
                                                              "format": "wav"}},
                      {"type": "file", "file": {"filename": "notes.md",
                                                "file_data": base64.b64encode(b"# todo\nbuy milk").decode()}}])
        roles = self.trace_roles(j)
        for r in ("vision", "asr", "document"):
            self.assertIn(r, roles)
        self.assertEqual(roles[-1], "persona")
        self.assertEqual(len(self.backend.by("meta/persona-model")), 1)
        user = self.persona_msgs()[-1]["content"]
        for bit in ("VISION:", "water the plants", "buy milk", "User Input: here's a photo"):
            self.assertIn(bit, user)

    def test_missing_role_is_named(self):
        with mock.patch.object(type(self.ent), "is_set", lambda e, k: k in ROLES and k != "video"):
            j = self.ask([{"type": "text", "text": "what happens?"},
                          {"type": "video_url", "video_url": {"url": "https://example.com/v.mp4"}}])
        content = j["choices"][0]["message"]["content"]
        self.assertIn("set the Video", content)
        self.assertIn("video", j["testbed"]["missing_roles"])
        self.assertIn("Quill", content)                       # the persona still answered

    def test_responses_endpoint(self):
        st, _, raw = self.call("/v1/responses", {"model": "testbed", "input": [
            {"role": "user", "content": [{"type": "input_text", "text": "what is it?"},
                                         {"type": "input_image", "image_url": data_url("image/png", PNG)}]}]})
        j = json.loads(raw)
        self.assertEqual(st, 200, j)
        self.assertEqual(j["object"], "response")
        self.assertIn("Quill", j["output_text"])
        self.assertIn("vision", [t["role"] for t in j["testbed_trace"]])


class TestGeneratedMedia(EntityCase):
    def test_generated_image_hosted_url(self):
        j = self.ask("draw an image of a red fox")
        content = j["choices"][0]["message"]["content"]
        m = re.search(r"!\[[^\]]*\]\((http://127\.0\.0\.1:\d+/v1/files/[^)]+)\)", content)
        self.assertTrue(m, content)
        self.assertIn("image_gen", self.trace_roles(j))
        self.assertEqual(self.trace_roles(j)[-1], "persona")
        st, hd, data = self.call(m.group(1)[len(self.base):], key=None)   # link mode: id is the password
        self.assertEqual(st, 200)
        self.assertTrue(hd["Content-Type"].startswith("image/png"))
        self.assertEqual(data, PNG)
        self.assertEqual(self.call("/v1/files/not-a-real-id.png", key=None)[0], 404)

    def test_hosted_media_key_mode(self):
        self.srv.app.settings["entity"]["media_auth"] = "key"
        j = self.ask("generate an image of a boat")
        url = re.search(r"\((http[^)]+/v1/files/[^)]+)\)", j["choices"][0]["message"]["content"]).group(1)
        path = url[len(self.base):]
        self.assertEqual(self.call(path, key=None)[0], 401)
        self.assertEqual(self.call(path, key="wrong-key-wrong-key-wrong")[0], 401)
        self.assertEqual(self.call(path)[0], 200)
        self.assertEqual(self.call(path + "?key=" + self.key, key=None)[0], 200)

    def test_media_as_data_urls(self):
        self.srv.app.settings["entity"]["media"] = "data"
        j = self.ask("draw a picture of a tree")
        self.assertIn("](data:image/png;base64,", j["choices"][0]["message"]["content"])

    def test_audio_output_modality(self):
        j = self.ask("hello there", modalities=["text", "audio"], audio={"voice": "alloy", "format": "wav"})
        a = j["choices"][0]["message"]["audio"]
        self.assertTrue(a["id"].startswith("audio_"))
        self.assertEqual(base64.b64decode(a["data"])[:4], b"RIFF")
        self.assertIn("Quill", a["transcript"])
        self.assertGreater(a["expires_at"], time.time())
        self.assertIn("tts", self.trace_roles(j))

    def test_say_out_loud_returns_audio_link(self):
        j = self.ask('say "good morning SeVin" out loud')
        content = j["choices"][0]["message"]["content"]
        m = re.search(r"\[Listen: [^\]]+\]\((http[^)]+)\)", content)
        self.assertTrue(m, content)
        st, hd, data = self.call(m.group(1)[len(self.base):], key=None)
        self.assertEqual(st, 200)
        self.assertEqual(data[:4], b"RIFF")

    def test_missing_image_gen_is_named(self):
        with mock.patch.object(type(self.ent), "is_set", lambda e, k: k in ROLES and k != "image_gen"):
            j = self.ask("draw an image of a fox")
        self.assertIn("set the Text-to-Image", j["choices"][0]["message"]["content"])


class TestStreaming(EntityCase):
    def stream(self, content):
        st, hd, raw = self.call("/v1/chat/completions", {"model": "testbed", "stream": True,
                                                         "messages": [{"role": "user", "content": content}]})
        self.assertEqual(st, 200)
        events = [json.loads(l[6:]) for l in raw.decode().splitlines()
                  if l.startswith("data: ") and l[6:] != "[DONE]"]
        self.assertTrue(raw.decode().rstrip().endswith("data: [DONE]"))
        text = "".join((e["choices"][0].get("delta") or {}).get("content") or "" for e in events)
        return events, text

    def test_true_token_streaming_from_persona(self):
        events, text = self.stream("hi")
        self.assertEqual(text, "I'm Quill, your lab assistant. Here you go.")
        self.assertTrue(self.backend.by("meta/persona-model")[-1].get("stream"))
        self.assertGreaterEqual(len([e for e in events if (e["choices"][0].get("delta") or {}).get("content")]), 6)
        self.assertIn("testbed_trace", events[-1])

    def test_stream_falls_back_when_backend_doesnt(self):
        self.backend.stream_ok = False
        events, text = self.stream("hi")
        self.assertEqual(text, "I'm Quill, your lab assistant. Here you go.")

    def test_streaming_with_generated_media(self):
        events, text = self.stream("draw an image of a lighthouse")
        self.assertTrue(text.startswith("I'm Quill"))
        self.assertRegex(text, r"!\[generated image\]\(http://127\.0\.0\.1:\d+/v1/files/")


class TestCallPage(EntityCase):
    def test_call_page_auth(self):
        tok = S.call_token(self.srv.app.settings)
        self.assertEqual(self.call("/call", key=None)[0], 401)
        self.assertEqual(self.call("/call?t=wrong", key=None)[0], 401)
        st, hd, raw = self.call(f"/call?t={tok}", key=None)
        self.assertEqual(st, 200)
        self.assertIn("text/html", hd["Content-Type"])
        page = raw.decode()
        self.assertIn(tok, page)
        self.assertIn('"model": "testbed"', page)
        self.assertIn("getUserMedia", page)
        self.assertNotIn(self.key, page)                       # the real key never goes in the page
        self.assertNotRegex(page, r"<script[^>]+src=|https?://(?!\$)[a-z]")  # no CDN

    def test_call_token_works_on_chat_only(self):
        tok = S.call_token(self.srv.app.settings)
        st, _, _ = self.call("/v1/chat/completions", {"model": "testbed", "messages": [
            {"role": "user", "content": "hi"}]}, key=tok)
        self.assertEqual(st, 200)
        self.assertEqual(self.call("/v1/models", key=tok)[0], 401)

    def test_new_key_retires_call_links(self):
        old = S.call_token(self.srv.app.settings)
        self.srv.app.settings["api_key"] = S.KEY_PREFIX + "x" * 32
        self.assertEqual(self.call(f"/call?t={old}", key=None)[0], 401)

    def test_call_page_can_be_turned_off(self):
        self.srv.app.settings["entity"]["call_page"] = False
        self.assertEqual(self.call(f"/call?t={S.call_token(self.srv.app.settings)}", key=None)[0], 404)


class TestSelfTestAndInfo(EntityCase):
    def test_self_test_full_stack(self):
        lines = []
        rows = S.self_test(self.base + "/v1", self.key, out=lines.append, soul_name="Quill")
        status = {r[0].split(" (")[0]: r[1] for r in rows}
        for k in ("one model for the whole stack", "chat", "streamed chat", "identity comes from soul.md",
                  "text + image + audio in one message", "image generation in chat"):
            self.assertEqual(status.get(k), "PASS", (k, lines))
        self.assertNotIn("FAIL", status.values(), lines)

    def test_self_test_catches_wrong_identity(self):
        rows = S.self_test(self.base + "/v1", self.key, out=lambda *a: None, soul_name="Vega")
        self.assertEqual({r[0]: r[1] for r in rows}["identity comes from soul.md"], "FAIL")

    def test_info_and_ui_show_one_model_first(self):
        block = S.connection_block(self.srv.app.settings, self.srv.app.models(), port=self.srv.bound_port)
        self.assertIn("Model:                   testbed", block)
        self.assertIn("POST http://127.0.0.1:", block)
        self.assertNotIn("Debug names", block)
        ui = S.ui_configs(self.srv.app.settings, self.srv.app.models(), port=self.srv.bound_port)
        self.assertIn("One model, one endpoint: model = testbed", ui)

    def test_server_log_has_trace(self):
        self.srv.app.settings["log_requests"] = True
        self.ask([{"type": "text", "text": "what is this?"},
                  {"type": "image_url", "image_url": {"url": data_url("image/png", PNG)}}])
        from tests.test_server import wait_log
        log = wait_log(1)
        self.assertTrue(any("vision" in " ".join(e.get("trace") or []) for e in log), log)


class TestUnifiedUnits(unittest.TestCase):
    def test_soul_name(self):
        self.assertEqual(unified.soul_name(SOUL), "Quill")
        self.assertEqual(unified.soul_name("Name: Vega\nrest"), "Vega")
        self.assertIsNone(unified.soul_name("no name here"))

    def test_turn_key_ignores_system_and_is_stable(self):
        a = [{"role": "system", "content": "x"}, {"role": "user", "content": "hi"}]
        b = [{"role": "system", "content": "y"}, {"role": "user", "content": "hi"}]
        self.assertEqual(unified.turn_key(a), unified.turn_key(b))
        self.assertNotEqual(unified.turn_key(a), unified.turn_key(a + [{"role": "user", "content": "more"}]))

    def test_speakable_drops_code_and_links(self):
        t = unified.speakable("Here **you** go:\n```py\nx=1\n```\n![img](http://a/b.png) [docs](http://x)")
        self.assertNotIn("x=1", t)
        self.assertNotIn("http", t)
        self.assertIn("docs", t)

    def test_bad_base64_is_a_client_error(self):
        with self.assertRaises(unified.PartError):
            unified.parse_content([{"type": "image_url", "image_url": {"url": "data:image/png;base64,@@@"}},
                                   {"type": "input_audio", "input_audio": {"data": "", "format": "wav"}}])

    def test_large_text_file_is_truncated_with_note(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "big.log")
        with open(p, "w") as f:
            f.write("line\n" * 10000)
        t = unified.read_text_file(p, 1000)
        self.assertIn("[truncated: showing the first 1,000 characters of 50,000 bytes]", t)


class FakeDevice:
    def __init__(self, ok=True):
        self.ok = ok
        self.played = []
        self.stops = 0
        self.recorded = []

    def check(self):
        return (self.ok, [] if self.ok else ["termux-microphone-record not found"], [])

    def record_start(self, path):
        self.recorded.append(path)
        self.path = path

    def record_stop(self, path):
        with open(path, "wb") as f:
            f.write(make_wav(1.0))
        return True

    def play(self, path):
        self.played.append(path)

    def stop(self):
        self.stops += 1


class TestVoiceCall(EntityCase):
    def test_call_loop(self):
        dev = FakeDevice()
        keys = iter(["", "", "", "", "q"])
        lines = []
        n = voicecall.run_call(self.ent, input_fn=lambda p="": next(keys), out=lines.append, device=dev)
        self.assertEqual(n, 2)
        self.assertEqual(len(dev.played), 2)
        text = "\n".join(lines)
        self.assertIn("YOU  > please remind me to water the plants", text)
        self.assertIn("QUILL > I'm Quill", text)
        self.assertRegex(text, r"\[record \d+\.\ds \| convert \d+\.\ds \| ASR \d+\.\ds \| router skipped \| recall \d+\.\ds \| persona \d+\.\ds \| TTS \d+\.\ds \| play \d+\.\ds \| store \d+\.\ds \| total \d+\.\ds\]")
        self.assertGreaterEqual(dev.stops, 2)                  # barge-in stop before each turn
        # the second turn carried the first as history
        self.assertIn("water the plants", json.dumps(self.backend.by("meta/persona-model")[-1]["messages"][1:-1]))
        self.assertFalse(any(os.path.exists(p) for p in dev.recorded))   # recordings cleaned up

    def test_missing_termux_api_explains_install(self):
        lines = []
        n = voicecall.run_call(self.ent, input_fn=lambda p="": "q", out=lines.append, device=FakeDevice(ok=False))
        self.assertEqual(n, 0)
        self.assertIn("pkg install termux-api", "\n".join(lines))

    def test_termux_check_finds_tools(self):
        t = voicecall.Termux(which=lambda n: None)
        ok, problems, warnings = t.check()
        self.assertFalse(ok)
        self.assertEqual(len(problems), 2)
        t = voicecall.Termux(which=lambda n: "/x/" + n)
        self.assertTrue(t.check()[0])


class TestTestbedAttachments(EntityCase):
    def setUp(self):
        super().setUp()
        d = os.path.join(self.tmp, "Download")
        os.makedirs(d)
        self.files = {}
        for name, data in (("photo.png", PNG), ("notes.txt", b"call the vet at 3"),
                           ("report.pdf", make_pdf("Budget is 4000 dollars")), ("memo.wav", make_wav(1.0)),
                           ("clip.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 40)):
            p = os.path.join(d, name)
            with open(p, "wb") as f:
                f.write(data)
            self.files[name] = p

    def test_picker_and_send(self):
        pend = attach.Pending()
        recent = unified.recent_files(dirs=(os.path.join(self.tmp, "Download"),))
        self.assertEqual(len(recent), 5)
        names = [os.path.basename(r[0]) for r in recent]
        pick = ",".join(str(names.index(n) + 1) for n in ("photo.png", "notes.txt", "report.pdf"))
        lines = []
        attach.attach_command(pend, "", input_fn=lambda p="": pick, out=lines.append, recent=recent)
        self.assertEqual(sorted(p.name for p in pend.parts), ["notes.txt", "photo.png", "report.pdf"])
        hist = []
        res = attach.run_with_files(self.ent, "what's in these?", pend.take(), hist, out=lines.append)
        self.assertTrue(res["ok"], res)
        roles = [t["role"] for t in res["trace"]]
        self.assertIn("vision", roles)
        self.assertEqual(roles.count("document"), 2)
        user = self.persona_msgs()[-1]["content"]
        for bit in ("call the vet at 3", "Budget is 4000 dollars", "VISION:"):
            self.assertIn(bit, user)
        self.assertEqual(len(hist), 2)
        self.assertIn("[attached: ", hist[0]["content"])
        self.assertTrue(os.path.exists(self.files["photo.png"]))    # the user's own files are never deleted

    def test_attach_by_path_and_paths_in_text(self):
        pend = attach.Pending()
        out = []
        attach.attach_command(pend, f'{self.files["memo.wav"]} "{self.files["clip.mp4"]}" /nope.png', out=out.append)
        self.assertEqual([p.kind for p in pend.parts], ["audio", "video"])
        self.assertIn("file not found", "\n".join(out))
        res = attach.run_with_files(self.ent, "", pend.take(), [], out=out.append)
        roles = [t["role"] for t in res["trace"]]
        self.assertIn("asr", roles)
        self.assertIn("video", roles)
        # a pasted path still works, as before
        self.assertTrue(attach.has_files(f"look at {self.files['photo.png']}"))
        res = attach.run_with_files(self.ent, f"look at {self.files['photo.png']}", [], [], out=out.append)
        self.assertIn("vision", [t["role"] for t in res["trace"]])
        self.assertNotIn(self.files["photo.png"], self.persona_msgs()[-1]["content"])


if __name__ == "__main__":
    unittest.main()
