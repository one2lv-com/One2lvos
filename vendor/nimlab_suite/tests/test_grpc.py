"""v3.5: NVCF gRPC transport for the gRPC-only Riva models. Offline: the
riva client is replaced by a fake module (FakeRiva) that records every
call, so nothing here touches grpc.nvcf.nvidia.com or needs a key."""

import io
import json
import os
import tempfile
import types
import unittest
import wave
from contextlib import redirect_stdout
from unittest import mock

from nimlab import nvcf_grpc as G, spec, store
from tests.fakes import make_wav
from tests.test_roles import make_entity

FID_CANARY = "b0e8b4a5-217c-40b7-9b96-17d84e666317"
FID_ZS = "55cf67bf-600f-4b04-8eac-12ed39537a08"
FID_NMT = "0778f2eb-b64d-45e7-acae-7dd9b9b35b4d"


# ---------------------------------------------------------------------------
# fake riva.client
# ---------------------------------------------------------------------------
class FakeRpcError(Exception):
    def __init__(self, code, details):
        super().__init__(details)
        self._code, self._details = code, details

    def code(self):
        return types.SimpleNamespace(name=self._code)

    def details(self):
        return self._details


class Obj(types.SimpleNamespace):
    pass


def _asr_resp(*texts, final=True):
    return Obj(results=[Obj(is_final=final, alternatives=[Obj(transcript=t)]) for t in texts])


class FakeRiva:
    """Stands in for the riva.client module."""

    def __init__(self, transcript="hello there", offline_error=None, stream_error=None, tts_error=None,
                 tts_audio=None):
        self.calls = []
        self.transcript = transcript
        self.offline_error, self.stream_error, self.tts_error = offline_error, stream_error, tts_error
        self.tts_audio = tts_audio
        fake = self

        class AudioEncoding:
            LINEAR_PCM = 1

        class RecognitionConfig(Obj):
            pass

        class StreamingRecognitionConfig(Obj):
            pass

        class Auth:
            def __init__(self, ssl_cert, use_ssl, uri, metadata_args):
                fake.calls.append(("auth", {"ssl_cert": ssl_cert, "use_ssl": use_ssl, "uri": uri,
                                            "metadata": metadata_args}))
                self.metadata = metadata_args

            def get_auth_metadata(self):
                return [tuple(m) for m in self.metadata]

        class Stub:
            def GetRivaSpeechRecognitionConfig(self, req, metadata=None):
                fake.calls.append(("asr_config", metadata))
                return Obj(model_config=[Obj(parameters={})])

            def GetRivaSynthesisConfig(self, req, metadata=None):
                fake.calls.append(("tts_config", metadata))
                return Obj(model_config=[Obj(parameters={"voice_name": "Magpie-Multilingual.EN-US",
                                                         "subvoices": "Aria:0,Leo:1"})])

        class ASRService:
            def __init__(self, auth):
                self.auth, self.stub = auth, Stub()

            def offline_recognize(self, audio_bytes, config):
                fake.calls.append(("offline", {"audio": audio_bytes, "config": config}))
                if fake.offline_error:
                    raise fake.offline_error
                return _asr_resp(*fake.transcript.split("|"))

            def streaming_response_generator(self, audio_chunks, streaming_config):
                chunks = list(audio_chunks)
                fake.calls.append(("streaming", {"chunks": chunks, "config": streaming_config}))
                if fake.stream_error:
                    raise fake.stream_error
                yield _asr_resp("interim junk", final=False)
                for t in fake.transcript.split("|"):
                    yield _asr_resp(t)

        class SpeechSynthesisService:
            def __init__(self, auth):
                self.auth, self.stub = auth, Stub()

            def synthesize(self, text, voice_name=None, language_code="en-US", encoding=None,
                           sample_rate_hz=44100, audio_prompt_encoding=None, zero_shot_audio_prompt_file=None,
                           zero_shot_quality=20, future=False, custom_dictionary=None, zero_shot_transcript=None):
                prompt = None
                if zero_shot_audio_prompt_file is not None:
                    with zero_shot_audio_prompt_file.open("rb") as f:  # what riva does with the Path
                        prompt = f.read()
                fake.calls.append(("tts", {"text": text, "voice": voice_name, "language": language_code,
                                           "rate": sample_rate_hz, "prompt": prompt, "quality": zero_shot_quality,
                                           "transcript": zero_shot_transcript, "encoding": encoding}))
                if fake.tts_error:
                    raise fake.tts_error
                return Obj(audio=fake.tts_audio if fake.tts_audio is not None else b"\x01\x00" * 2205)

        class NeuralMachineTranslationClient:
            def __init__(self, auth):
                self.auth = auth

            def translate(self, texts, model, source_language, target_language):
                fake.calls.append(("nmt", {"texts": texts, "model": model, "src": source_language,
                                           "tgt": target_language}))
                return Obj(translations=[Obj(text="hola " + t) for t in texts])

            def get_config(self, model):
                return Obj(languages={"en-es": 1})

        def add_custom_configuration_to_config(config, s):
            config.custom = s

        self.Auth, self.ASRService, self.SpeechSynthesisService = Auth, ASRService, SpeechSynthesisService
        self.NeuralMachineTranslationClient = NeuralMachineTranslationClient
        self.AudioEncoding, self.RecognitionConfig = AudioEncoding, RecognitionConfig
        self.StreamingRecognitionConfig = StreamingRecognitionConfig
        self.add_custom_configuration_to_config = add_custom_configuration_to_config
        self.proto = types.SimpleNamespace(
            riva_asr_pb2=types.SimpleNamespace(RivaSpeechRecognitionConfigRequest=Obj),
            riva_tts_pb2=types.SimpleNamespace(RivaSynthesisConfigRequest=Obj))
        self.__version__ = "fake"

    def of(self, name):
        return [c[1] for c in self.calls if c[0] == name]


class GrpcCase(unittest.TestCase):
    """Fresh data dir and a fake riva module for every test."""

    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.addCleanup(self._d.cleanup)
        p = mock.patch.dict(os.environ, {"NIMLAB_DATA_DIR": os.path.join(self._d.name, "data"),
                                         "NVIDIA_API_KEY": "nvapi-test-key", "NIMLAB_GRPC_AUTOFETCH": "0"})
        p.start()
        self.addCleanup(p.stop)
        store.reset()
        self.addCleanup(store.reset)
        self.riva = FakeRiva()
        self.use_riva(self.riva)
        G._shared.clear()
        self.addCleanup(G._shared.clear)

    def use_riva(self, fake):
        self.riva = fake
        p = mock.patch.object(G, "_riva", lambda: fake)
        p.start()
        self.addCleanup(p.stop)

    def wav_file(self, **kw):
        path = os.path.join(self._d.name, "in.wav")
        with open(path, "wb") as f:
            f.write(make_wav(**kw))
        return path


# ---------------------------------------------------------------------------
class TestStore(GrpcCase):
    def test_set_and_read_function_id_in_endpoints_json(self):
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY, source="user", kind="asr")
        rec = store.grpc_function("nvidia/canary-1b-asr")
        self.assertEqual(rec["function_id"], FID_CANARY)
        self.assertEqual(rec["source"], "user")
        doc = json.load(open(store.path(store.ENDPOINTS)))
        self.assertEqual(doc["grpc_functions"]["nvidia/canary-1b-asr"]["function_id"], FID_CANARY)
        ep = doc["endpoints"][store.endpoint_key(G.URI, "GRPC")]
        self.assertEqual(ep["function_ids"]["nvidia/canary-1b-asr"], FID_CANARY)
        self.assertTrue(store.is_grpc_model("nvidia/canary-1b-asr"))
        self.assertFalse(store.is_grpc_model("nvidia/magpie-tts-multilingual"))

    def test_rejects_a_value_that_is_not_a_function_id(self):
        for bad in ("", "abc", "nvapi-123", FID_CANARY + "x"):
            with self.assertRaises(ValueError):
                store.set_grpc_function("nvidia/canary-1b-asr", bad)
        self.assertIsNone(store.grpc_function("nvidia/canary-1b-asr"))

    def test_replacing_keeps_previous_and_clear_forgets(self):
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY, source="spec")
        store.note_grpc_check("nvidia/canary-1b-asr", True, "ok")
        store.set_grpc_function("nvidia/canary-1b-asr", FID_ZS, source="user")
        rec = store.grpc_function("nvidia/canary-1b-asr")
        self.assertEqual(rec["function_id"], FID_ZS)
        self.assertEqual(rec["previous"][0]["function_id"], FID_CANARY)
        self.assertNotIn("last_check", rec)  # the check was for the old id
        self.assertTrue(store.clear_grpc_function("nvidia/canary-1b-asr"))
        rec = store.grpc_function("nvidia/canary-1b-asr")
        self.assertIsNone(rec["function_id"])
        self.assertTrue(store.is_grpc_model("nvidia/canary-1b-asr"))  # still gRPC-only
        doc = json.load(open(store.path(store.ENDPOINTS)))
        self.assertNotIn("nvidia/canary-1b-asr", doc["endpoints"][store.endpoint_key(G.URI, "GRPC")]["function_ids"])

    def test_sweep_results_store_ids_but_keep_a_pasted_one(self):
        res = {"results": {
            "nvidia/canary-1b-asr": {"status": "GRPC_NVCF_ONLY", "function_id": FID_CANARY, "url": G.URI,
                                     "method": "GRPC", "grpc_sample": {"kind": "asr", "mode": "offline",
                                                                       "language_code": "en-US"}},
            "nvidia/conformer-ctc-asr": {"status": "GRPC_NVCF_ONLY", "url": G.URI, "method": "GRPC"}}}
        store.set_grpc_function("nvidia/canary-1b-asr", FID_ZS, source="user")
        store.apply_results(res["results"])
        canary = store.grpc_function("nvidia/canary-1b-asr")
        self.assertEqual(canary["function_id"], FID_ZS)          # the user's id wins
        self.assertEqual(canary["spec_function_id"], FID_CANARY)  # the spec's is noted beside it
        conf = store.grpc_function("nvidia/conformer-ctc-asr")
        self.assertIsNone(conf["function_id"])
        self.assertEqual(conf["kind"], "asr")
        self.assertIn("nvidia/conformer-ctc-asr", store.grpc_model_ids())

    def test_sweep_fills_ids_when_none_pasted(self):
        store.apply_results({"nvidia/canary-1b-asr": {
            "status": "GRPC_NVCF_ONLY", "function_id": FID_CANARY,
            "grpc_sample": {"kind": "asr", "mode": "offline"}}})
        rec = store.grpc_function("nvidia/canary-1b-asr")
        self.assertEqual((rec["function_id"], rec["source"]), (FID_CANARY, "spec"))
        self.assertEqual(rec["sample"]["mode"], "offline")

    def test_no_function_ids_hardcoded_in_code(self):
        import re
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uuid = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
        for name in ("nvcf_grpc.py", "store.py", "entity.py", "grpcmenu.py", "sweep.py", "router.py"):
            with open(os.path.join(root, "nimlab", name), encoding="utf-8") as f:
                hits = [u for u in uuid.findall(f.read()) if u != "b0e8b4a5-217c-40b7-9b96-17d84e666317"]
            self.assertEqual(hits, [], name)  # the one allowed UUID is an example in an error message


# ---------------------------------------------------------------------------
class TestSpecParsing(GrpcCase):
    USAGE_ASR = ("```bash\npython python-clients/scripts/asr/transcribe_file_offline.py \\\n"
                 "    --server grpc.nvcf.nvidia.com:443 --use-ssl \\\n    --metadata function-id \"" + FID_CANARY +
                 "\" \\\n    --metadata \"authorization\" \"Bearer $API_KEY_REQUIRED_IF_EXECUTING_OUTSIDE_NGC\" \\\n"
                 "    --language-code es-US \\\n    --input-file <path_to_audio_file>\n```")
    USAGE_TTS = ("```bash\npython python-clients/scripts/tts/talk.py --server grpc.nvcf.nvidia.com:443 --use-ssl "
                 "--metadata function-id \"" + FID_ZS + "\" --metadata authorization \"Bearer $KEY\" "
                 "--language-code en-US --text \"hi\" --voice \"Magpie-Multilingual.EN-US.Aria\" --output a.wav\n```")

    def test_sample_from_usage(self):
        s = G.sample_from_usage(self.USAGE_ASR)
        self.assertEqual(s, {"script": "asr/transcribe_file_offline.py", "kind": "asr", "mode": "offline",
                             "language_code": "es-US"})
        t = G.sample_from_usage(self.USAGE_TTS)
        self.assertEqual((t["kind"], t["voice"], t["language_code"]), ("tts", "Magpie-Multilingual.EN-US.Aria", "en-US"))
        self.assertEqual(G.sample_from_usage("curl https://ai.api.nvidia.com/v1/x"), {})
        st = G.sample_from_usage("python scripts/asr/transcribe_file.py --language-code multi")
        self.assertEqual(st["mode"], "streaming")

    def test_plans_from_spec_note_the_sample(self):
        body = json.dumps({"nvcfFunctionId": FID_CANARY, "attributes": {"usage": self.USAGE_ASR}})
        info = spec.extract_ngc_spec(body)
        self.assertEqual(info["function_id"], FID_CANARY)
        self.assertTrue(info["grpc"])

    def test_kind_of(self):
        self.assertEqual(G.kind_of("nvidia/canary-1b-asr"), "asr")
        self.assertEqual(G.kind_of("openai/whisper-large-v3"), "asr")
        self.assertEqual(G.kind_of("nvidia/magpie-tts-zeroshot"), "tts")
        self.assertEqual(G.kind_of("resembleai/chatterbox-multilingual-tts"), "tts")
        self.assertEqual(G.kind_of("nvidia/riva-translate-1.6b"), "nmt")
        self.assertEqual(G.kind_of("nvidia/megatron-1b-nmt"), "nmt")
        self.assertEqual(G.kind_of("nvidia/studiovoice"), "other")

    def test_refresh_fetches_and_stores_and_reports_a_change(self):
        class Res:
            def __init__(self, ok, text):
                self.ok, self.text = ok, text

        class Fetcher:
            def __init__(self, fid):
                self.fid, self.urls = fid, []

            def get(self, url, store=False, accept=None):
                self.urls.append(url)
                if "canary-1b-asr" in url:
                    usage = TestSpecParsing.USAGE_ASR.replace(FID_CANARY, self.fid)
                    return Res(True, json.dumps({"nvcfFunctionId": self.fid, "attributes": {"usage": usage}}))
                return Res(False, "")

        ok, msg = G.refresh("nvidia/canary-1b-asr", fetcher=Fetcher(FID_CANARY))
        self.assertTrue(ok, msg)
        self.assertIn("(new)", msg)
        rec = store.grpc_function("nvidia/canary-1b-asr")
        self.assertEqual((rec["function_id"], rec["source"], rec["kind"]), (FID_CANARY, "ngc_spec", "asr"))
        self.assertEqual(rec["sample"]["language_code"], "es-US")
        self.assertIn("build.nvidia.com/nvidia/canary-1b-asr", rec["page_url"])
        ok, msg = G.refresh("nvidia/canary-1b-asr", fetcher=Fetcher(FID_ZS))
        self.assertIn("changed", msg)
        self.assertEqual(store.grpc_function("nvidia/canary-1b-asr")["function_id"], FID_ZS)
        ok, msg = G.refresh("nvidia/nothing-here", fetcher=Fetcher(FID_ZS))
        self.assertFalse(ok)
        self.assertIn("grpc set", msg)

    def test_seed_from_spec_cache(self):
        d = os.path.join(self._d.name, "specs")
        os.makedirs(d)
        json.dump({"model_id": "nvidia/canary-1b-asr", "function_id": FID_CANARY, "plans": [],
                   "notes": {"grpc_only": True, "grpc_sample": {"kind": "asr"}}},
                  open(os.path.join(d, "nvidia__canary-1b-asr.json"), "w"))
        json.dump({"model_id": "x/http", "function_id": FID_ZS, "plans": [{}], "notes": {}},
                  open(os.path.join(d, "x__http.json"), "w"))
        self.assertEqual(G.seed_from_spec_cache(d), 1)
        self.assertEqual(store.grpc_function("nvidia/canary-1b-asr")["source"], "spec_cache")
        self.assertIsNone(store.grpc_function("x/http"))
        self.assertEqual(G.seed_from_spec_cache(d), 0)  # already stored


# ---------------------------------------------------------------------------
class TestScanReportsUsable(GrpcCase):
    def test_sweep_evaluate_marks_grpc_usable(self):
        from nimlab import sweep
        doc = {"model_id": "nvidia/canary-1b-asr", "plans": [], "function_id": FID_CANARY,
               "notes": {"grpc_only": True, "grpc_sample": {"kind": "asr", "mode": "offline"}}}
        e = sweep.evaluate(doc, probe=False)
        self.assertEqual(e["status"], "GRPC_NVCF_ONLY")
        self.assertIn("USABLE via NVCF gRPC", e["reason"])
        self.assertEqual((e["url"], e["method"], e["grpc_function_id"]), (G.URI, "GRPC", FID_CANARY))
        doc2 = {"model_id": "nvidia/conformer-ctc-asr", "plans": [], "notes": {"grpc_only": True}}
        e2 = sweep.evaluate(doc2, probe=False)
        self.assertIn("USABLE via NVCF gRPC (ASR) once a function ID is set", e2["reason"])

    def test_router_hint_says_how_to_use_it(self):
        from nimlab import router
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY, source="user")
        cls = next(getattr(router, n) for n in dir(router) if isinstance(getattr(router, n), type)
                   and hasattr(getattr(router, n), "resolve"))
        route = cls().resolve("nvidia/canary-1b-asr", kind="audio_asr")
        self.assertEqual(route.get("transport"), "nvcf_grpc")
        self.assertEqual(route.get("function_id"), FID_CANARY)
        self.assertIn("runs over NVCF gRPC", route["hint"])

    def test_role_candidates_include_grpc_models(self):
        from nimlab import rolemenu
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY, source="user", kind="asr")
        store.apply_results({"nvidia/conformer-ctc-asr": {"status": "GRPC_NVCF_ONLY"}})
        usable, _all = rolemenu.model_lists()
        self.assertIn("nvidia/canary-1b-asr", usable)
        self.assertIn("nvidia/conformer-ctc-asr", usable)
        self.assertEqual(rolemenu.grpc_flag("nvidia/canary-1b-asr"), "NVCF gRPC")
        self.assertIn("no function ID", rolemenu.grpc_flag("nvidia/conformer-ctc-asr"))
        self.assertEqual(rolemenu.grpc_flag("nvidia/magpie-tts-multilingual"), "")


# ---------------------------------------------------------------------------
class TestAudio(GrpcCase):
    def _info(self, wav):
        with wave.open(io.BytesIO(wav)) as w:
            return w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()

    def test_16k_mono_passes_through(self):
        data = make_wav(seconds=1.0, rate=16000)
        wav, pcm, notes = G.to_wav16k(data=data)
        self.assertEqual(wav, data)
        self.assertEqual(notes, [])
        self.assertEqual(len(pcm), 16000 * 2)

    def test_stereo_44k_becomes_16k_mono(self):
        wav, pcm, notes = G.to_wav16k(data=make_wav(seconds=1.0, rate=44100, channels=2))
        ch, width, rate, n = self._info(wav)
        self.assertEqual((ch, width, rate), (1, 2, 16000))
        self.assertAlmostEqual(n, 16000, delta=5)
        self.assertEqual(len(pcm), n * 2)
        self.assertTrue(any("resampled" in x for x in notes))
        self.assertTrue(any("mono" in x for x in notes))

    def test_8bit_8k_becomes_16bit_16k(self):
        ch, width, rate, _ = self._info(G.to_wav16k(data=make_wav(seconds=0.5, rate=8000, width=1))[0])
        self.assertEqual((ch, width, rate), (1, 2, 16000))

    def test_non_wav_without_ffmpeg_says_so(self):
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(G.GrpcError) as cm:
                G.to_wav16k(data=b"ID3" + b"\x00" * 500)
        self.assertIn("pkg install ffmpeg", str(cm.exception))

    def test_missing_and_empty(self):
        with self.assertRaises(G.GrpcError):
            G.to_wav16k(path="/nope.wav")
        with self.assertRaises(G.GrpcError):
            G.to_wav16k(data=b"")


# ---------------------------------------------------------------------------
class TestClient(GrpcCase):
    def test_auth_uses_nvcf_uri_ssl_and_metadata(self):
        c = G.GrpcClient(api_key="nvapi-abc")
        c.auth(FID_CANARY)
        a = self.riva.of("auth")[0]
        self.assertEqual(a["uri"], "grpc.nvcf.nvidia.com:443")
        self.assertTrue(a["use_ssl"])
        self.assertIsNone(a["ssl_cert"])
        self.assertEqual(a["metadata"], [["function-id", FID_CANARY], ["authorization", "Bearer nvapi-abc"]])
        c.auth(FID_CANARY)
        self.assertEqual(len(self.riva.of("auth")), 1)  # channel reused

    def test_auth_refuses_bad_id_and_missing_key(self):
        with self.assertRaises(G.GrpcError):
            G.GrpcClient(api_key="k").auth("not-an-id")
        with mock.patch.dict(os.environ, {"NVIDIA_API_KEY": ""}), \
                mock.patch("nimlab.core.load_api_key", return_value=None):
            with self.assertRaises(G.GrpcError):
                G.GrpcClient().auth(FID_CANARY)

    def test_offline_asr_sends_whole_wav_with_config(self):
        wav, pcm, _ = G.to_wav16k(data=make_wav(seconds=1.0, rate=16000))
        self.riva.transcript = "hola|mundo"
        text, mode = G.GrpcClient(api_key="k").asr(FID_CANARY, wav, pcm, language_code="es-US")
        self.assertEqual((text, mode), ("hola mundo", "offline"))
        call = self.riva.of("offline")[0]
        self.assertEqual(call["audio"], wav)
        cfg = call["config"]
        self.assertEqual((cfg.language_code, cfg.sample_rate_hertz, cfg.audio_channel_count), ("es-US", 16000, 1))
        self.assertTrue(cfg.enable_automatic_punctuation)

    def test_streaming_asr_sends_chunks_and_keeps_final_results(self):
        wav, pcm, _ = G.to_wav16k(data=make_wav(seconds=0.35, rate=16000))
        text, mode = G.GrpcClient(api_key="k").asr(FID_CANARY, wav, pcm, mode="streaming")
        self.assertEqual((text, mode), ("hello there", "streaming"))
        call = self.riva.of("streaming")[0]
        self.assertEqual(b"".join(call["chunks"]), pcm)
        self.assertEqual(len(call["chunks"][0]), G.CHUNK_FRAMES * 2)
        self.assertFalse(call["config"].interim_results)

    def test_falls_back_to_the_other_mode_when_unimplemented(self):
        self.use_riva(FakeRiva(offline_error=FakeRpcError("UNIMPLEMENTED", "offline not supported")))
        wav, pcm, _ = G.to_wav16k(data=make_wav(seconds=0.3, rate=16000))
        text, mode = G.GrpcClient(api_key="k").asr(FID_CANARY, wav, pcm, mode="offline")
        self.assertEqual(mode, "streaming")
        self.assertEqual(text, "hello there")

    def test_tts_wraps_pcm_in_wav(self):
        wav = G.GrpcClient(api_key="k").tts(FID_ZS, "Hi", voice="Magpie-Multilingual.EN-US.Aria")
        self.assertEqual(wav[:4], b"RIFF")
        with wave.open(io.BytesIO(wav)) as w:
            self.assertEqual((w.getnchannels(), w.getframerate()), (1, G.TTS_RATE))
        call = self.riva.of("tts")[0]
        self.assertEqual((call["voice"], call["rate"], call["prompt"], call["encoding"]),
                         ("Magpie-Multilingual.EN-US.Aria", 22050, None, 1))

    def test_tts_zero_shot_sends_prompt_file_and_cleans_up(self):
        clip = make_wav(seconds=4.0)
        made = []
        real = tempfile.mkstemp
        with mock.patch("tempfile.mkstemp", side_effect=lambda **kw: made.append(real(**kw)) or made[-1]):
            G.GrpcClient(api_key="k").tts(FID_ZS, "Hi", prompt_wav=clip, prompt_transcript="my words")
        call = self.riva.of("tts")[0]
        self.assertEqual(call["prompt"], clip)
        self.assertEqual((call["transcript"], call["quality"]), ("my words", 20))
        self.assertFalse(os.path.exists(made[0][1]))

    def test_voices_list(self):
        self.assertEqual(G.GrpcClient(api_key="k").voices(FID_ZS),
                         ["Magpie-Multilingual.EN-US.Aria", "Magpie-Multilingual.EN-US.Leo"])

    def test_check_uses_config_rpc(self):
        ok, lat, detail = G.GrpcClient(api_key="k").check(FID_CANARY, "asr")
        self.assertTrue(ok)
        self.assertIn("ASR model config", detail)
        md = self.riva.of("asr_config")[0]
        self.assertIn(("function-id", FID_CANARY), md)
        ok, _, detail = G.GrpcClient(api_key="k").check(FID_CANARY, "other")
        self.assertFalse(ok)

    def test_missing_library_is_a_clear_error(self):
        def boom():
            raise G.Unavailable("nvidia-riva-client isn't installed: " + G.INSTALL_HINT)
        with mock.patch.object(G, "_riva", boom):
            ok, detail = G.available()
            self.assertFalse(ok)
            self.assertIn("pip install nvidia-riva-client", detail)
            store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY)
            r = G.run_asr({"model": "nvidia/canary-1b-asr"}, data=make_wav(seconds=0.2, rate=16000), api_key="k")
            self.assertFalse(r.ok)
            self.assertIn("start.sh install", r.error)


# ---------------------------------------------------------------------------
class TestRoleCalls(GrpcCase):
    def test_run_asr_language_order(self):
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY, sample={"kind": "asr", "language_code": "en-US"})
        audio = make_wav(seconds=0.2, rate=16000)
        G.run_asr({"model": "nvidia/canary-1b-asr"}, data=audio, api_key="k")
        store.update_grpc_settings("nvidia/canary-1b-asr", language_code="de-DE")
        G.run_asr({"model": "nvidia/canary-1b-asr"}, data=audio, api_key="k")
        G.run_asr({"model": "nvidia/canary-1b-asr", "language_code": "fr-FR"}, data=audio, api_key="k")
        r = G.run_asr({"model": "nvidia/canary-1b-asr", "language_code": "fr-FR"}, data=audio, language="es-US",
                      api_key="k")
        langs = [c["config"].language_code for c in self.riva.of("offline")]
        self.assertEqual(langs, ["en-US", "de-DE", "fr-FR", "es-US"])
        self.assertTrue(r.ok)
        self.assertEqual(r.raw["transport"], "nvcf_grpc")
        chk = store.grpc_function("nvidia/canary-1b-asr")["last_check"]
        self.assertTrue(chk["ok"])

    def test_no_function_id_tells_how_to_set_it(self):
        store.apply_results({"nvidia/conformer-ctc-asr": {"status": "GRPC_NVCF_ONLY"}})
        r = G.run_asr({"model": "nvidia/conformer-ctc-asr"}, data=make_wav(seconds=0.2, rate=16000), api_key="k")
        self.assertFalse(r.ok)
        self.assertIn("grpc set nvidia/conformer-ctc-asr", r.error)
        self.assertIn("grpc refresh", r.error)
        self.assertEqual(self.riva.calls, [])

    def test_missing_id_is_fetched_once_automatically(self):
        store.apply_results({"nvidia/canary-1b-asr": {"status": "GRPC_NVCF_ONLY"}})
        calls = []

        def fake_refresh(model, fetcher=None, log=None):
            calls.append(model)
            store.set_grpc_function(model, FID_CANARY, source="ngc_spec")
            return True, "ok"
        G._auto_tried.clear()
        self.addCleanup(G._auto_tried.clear)
        with mock.patch.dict(os.environ, {"NIMLAB_GRPC_AUTOFETCH": "1"}), mock.patch.object(G, "refresh", fake_refresh):
            r = G.run_asr({"model": "nvidia/canary-1b-asr"}, data=make_wav(seconds=0.2, rate=16000), api_key="k")
            G.run_asr({"model": "nvidia/canary-1b-asr"}, data=make_wav(seconds=0.2, rate=16000), api_key="k")
        self.assertTrue(r.ok, r.error)
        self.assertEqual(calls, ["nvidia/canary-1b-asr"])
        self.assertEqual(self.riva.of("auth")[0]["metadata"][0], ["function-id", FID_CANARY])

    def test_stale_id_error_says_refresh_and_is_remembered(self):
        self.use_riva(FakeRiva(offline_error=FakeRpcError("NOT_FOUND", "Function not found: abc")))
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY)
        r = G.run_asr({"model": "nvidia/canary-1b-asr"}, data=make_wav(seconds=0.2, rate=16000), api_key="k")
        self.assertFalse(r.ok)
        self.assertIn("NOT_FOUND", r.error)
        self.assertIn("grpc refresh nvidia/canary-1b-asr", r.error)
        self.assertFalse(store.grpc_function("nvidia/canary-1b-asr")["last_check"]["ok"])

    def test_permission_denied_points_at_key_and_refresh(self):
        self.use_riva(FakeRiva(tts_error=FakeRpcError("PERMISSION_DENIED", "Authorization failed")))
        store.set_grpc_function("nvidia/magpie-tts-zeroshot", FID_ZS)
        r = G.run_tts({"model": "nvidia/magpie-tts-zeroshot"}, "hi", api_key="k")
        self.assertIn("check NVIDIA_API_KEY", r.error)
        self.assertIn("grpc refresh nvidia/magpie-tts-zeroshot", r.error)

    def test_key_never_in_errors(self):
        self.use_riva(FakeRiva(offline_error=FakeRpcError("UNAUTHENTICATED", "bad Bearer nvapi-secret-123456789")))
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY)
        r = G.run_asr({"model": "nvidia/canary-1b-asr"}, data=make_wav(seconds=0.2, rate=16000),
                      api_key="nvapi-secret-123456789")
        self.assertNotIn("nvapi-secret-123456789", r.error)

    def test_translate(self):
        store.set_grpc_function("nvidia/riva-translate-1.6b", FID_NMT, kind="nmt")
        r = G.run_translate({"model": "nvidia/riva-translate-1.6b"}, "hello", target="Spanish", api_key="k")
        self.assertTrue(r.ok)
        self.assertEqual(r.text, "hola hello")
        self.assertEqual(self.riva.of("nmt")[0]["tgt"], "es")

    def test_use_grpc_rules(self):
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY)
        self.assertTrue(G.use_grpc({"model": "nvidia/canary-1b-asr"}))
        self.assertFalse(G.use_grpc({"model": "nvidia/canary-1b-asr", "endpoint": "http://x/v1"}))
        self.assertFalse(G.use_grpc({"model": "nvidia/canary-1b-asr", "transport": "http"}))
        self.assertTrue(G.use_grpc({"model": "nvidia/magpie-tts-multilingual", "transport": "grpc"}))
        self.assertFalse(G.use_grpc({"model": "nvidia/magpie-tts-multilingual"}))
        self.assertEqual(G.function_id("nvidia/canary-1b-asr", {"grpc_function_id": FID_ZS}), FID_ZS)


# ---------------------------------------------------------------------------
class TestEntityRouting(GrpcCase):
    """The ASR / TTS roles go over gRPC by themselves when the model is
    gRPC-only, so the single testbed entity and the call page just work."""

    def test_asr_role_goes_over_grpc(self):
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY, kind="asr")
        ent, _ = make_entity(self, {"asr": {"backend": "model", "model": "nvidia/canary-1b-asr",
                                            "language_code": "es-US"}})
        r = ent.run_role("asr", audio=self.wav_file(seconds=0.5, rate=48000, channels=2))
        self.assertTrue(r.ok, r.error)
        self.assertEqual(r.text, "hello there")
        cfg = self.riva.of("offline")[0]["config"]
        self.assertEqual((cfg.language_code, cfg.sample_rate_hertz), ("es-US", 16000))
        a = self.riva.of("auth")[0]
        self.assertEqual(a["metadata"][1], ["authorization", "Bearer nvapi-test"])  # the entity's key

    def test_tts_role_with_cloned_voice_goes_over_grpc(self):
        store.set_grpc_function("nvidia/magpie-tts-zeroshot", FID_ZS, kind="tts")
        clip = self.wav_file(seconds=4.0)
        ent, out = make_entity(self, {"tts": {"backend": "model", "model": "nvidia/magpie-tts-zeroshot",
                                              "voice_clone": {"path": clip, "transcript": "this is me"}}})
        r = ent.run_role("tts", text="Hello world")
        self.assertTrue(r.ok, r.error)
        self.assertTrue(r.files and os.path.isfile(r.files[0]))
        call = self.riva.of("tts")[0]
        self.assertEqual(call["text"], "Hello world")
        self.assertEqual(call["prompt"][:4], b"RIFF")
        self.assertEqual(call["transcript"], "this is me")
        self.assertIsNone(call["voice"])  # zero-shot: the clip is the voice

    def test_http_tts_model_does_not_touch_grpc(self):
        from tests.fakes import FakeResponse, RouteOpener
        opener = RouteOpener([("", lambda req: FakeResponse(make_wav(seconds=0.2), 200,
                                                              {"Content-Type": "audio/wav"}))])
        ent, _ = make_entity(self, {"tts": "nvidia/magpie-tts-multilingual"}, opener=opener)
        ent.run_role("tts", text="hi")
        self.assertEqual(self.riva.calls, [])

    def test_translate_role_over_grpc(self):
        store.set_grpc_function("nvidia/riva-translate-1.6b", FID_NMT, kind="nmt")
        ent, _ = make_entity(self, {"guard_translate": "nvidia/riva-translate-1.6b"})
        r = ent.run_role("guard_translate", text="hello", task="translate", target_language="German")
        self.assertTrue(r.ok, r.error)
        self.assertEqual(self.riva.of("nmt")[0]["tgt"], "de")


# ---------------------------------------------------------------------------
class TestCli(GrpcCase):
    def run_cli(self, *argv):
        from nimlab import cli
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(list(argv))
        return rc, buf.getvalue()

    def test_set_list_lang_clear(self):
        rc, out = self.run_cli("grpc", "set", "nvidia/canary-1b-asr", FID_CANARY)
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("grpc", "lang", "canary", "es-US")
        self.assertEqual(rc, 0, out)
        self.assertEqual(store.grpc_function("nvidia/canary-1b-asr")["language_code"], "es-US")
        with mock.patch.object(G, "seed_from_spec_cache", return_value=0):
            rc, out = self.run_cli("grpc", "list")
        self.assertIn("nvidia/canary-1b-asr", out)
        self.assertIn(FID_CANARY, out)
        self.assertIn("es-US", out)
        self.assertIn("nvidia-riva-client fake", out)
        rc, out = self.run_cli("grpc", "set", "nvidia/canary-1b-asr", "junk")
        self.assertEqual(rc, 2)
        rc, out = self.run_cli("grpc", "clear", "1")
        self.assertEqual(rc, 0)
        self.assertIsNone(store.grpc_function("nvidia/canary-1b-asr")["function_id"])

    def test_check_and_asr(self):
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY, kind="asr")
        rc, out = self.run_cli("grpc", "check", "nvidia/canary-1b-asr")
        self.assertEqual(rc, 0, out)
        self.assertIn("[ok]", out)
        rc, out = self.run_cli("grpc", "asr", "nvidia/canary-1b-asr", self.wav_file(seconds=0.3, rate=16000),
                               "--lang", "es-US")
        self.assertEqual(rc, 0, out)
        self.assertIn("hello there", out)
        self.assertIn("es-US", out)

    def test_refresh_keeps_pasted_ids_unless_forced(self):
        store.set_grpc_function("nvidia/canary-1b-asr", FID_CANARY, source="user")
        with mock.patch.object(G, "refresh", return_value=(True, "x")) as ref:
            rc, out = self.run_cli("grpc", "refresh")
            self.assertIn("kept your pasted ID", out)
            ref.assert_not_called()
            self.run_cli("grpc", "refresh", "--force")
            ref.assert_called_once()


class TestMenu(GrpcCase):
    def test_menu_paste_and_try_tts(self):
        from nimlab import grpcmenu
        store.apply_results({"nvidia/magpie-tts-zeroshot": {"status": "GRPC_NVCF_ONLY"}})
        answers = iter(["1", "1", FID_ZS, "8", "1", "Hi there", "0"])
        out = []
        with mock.patch.object(G, "seed_from_spec_cache", return_value=0), \
                mock.patch("nimlab.api.play_audio"), mock.patch("nimlab.api.save_wav", return_value="/tmp/x.wav"):
            grpcmenu.run_menu(lambda p: next(answers), out.append)
        self.assertEqual(store.grpc_function("nvidia/magpie-tts-zeroshot")["function_id"], FID_ZS)
        self.assertEqual(self.riva.of("tts")[0]["text"], "Hi there")
        self.assertTrue(any("[ok] /tmp/x.wav" in str(o) for o in out))


if __name__ == "__main__":
    unittest.main()
