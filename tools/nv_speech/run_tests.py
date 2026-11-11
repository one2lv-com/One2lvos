import time, wave, json
import riva.client
from common import *

ASR_FID = "2b940e91-a70e-4483-a958-d50408b96589"  # ai-parakeet-tdt-0_6b -> parakeet-tdt-0.6b-multi (25 EU langs)
ASR_V2_FID = "d3fe9151-442b-4204-a70d-5fcc597fd610"  # parakeet-tdt-0.6b-v2 (en-US)
TEXT = "Lumenis online."
SR = 22050
OUT = "/home/sprite/nv_speech_test"


def save_wav(path, pcm, sr):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)


def tts_call(key, voice):
    a = auth(key, TTS_FID)
    s = riva.client.SpeechSynthesisService(a)
    t = time.time()
    r = s.synthesize(TEXT, voice_name=voice, language_code="en-US", sample_rate_hz=SR)
    return r.audio, time.time() - t


def asr_call(key, fid, wav_path, lang):
    a = auth(key, fid)
    s = riva.client.ASRService(a)
    cfg = riva.client.RecognitionConfig(language_code=lang, max_alternatives=1, enable_automatic_punctuation=True, audio_channel_count=1)
    data = open(wav_path, "rb").read()
    riva.client.add_audio_file_specs_to_config(cfg, wav_path)
    t = time.time()
    r = s.offline_recognize(data, cfg)
    txt = " ".join(res.alternatives[0].transcript for res in r.results if res.alternatives)
    return txt.strip(), time.time() - t


results = []
ref_wav = None
keys = load_keys()
for i, (h, names, key) in enumerate(keys):
    row = {"keys": names}
    voice = "Magpie-Multilingual.EN-US.Aria"
    try:
        pcm, lat = tts_call(key, voice)
        p = f"{OUT}/tts_key{i+1}_aria.wav"
        save_wav(p, pcm, SR)
        row["tts"] = f"OK {lat:.2f}s, {len(pcm)/2/SR:.2f}s audio"
        ref_wav = ref_wav or p
        wav_for_asr = p
    except Exception as e:
        row["tts"] = "ERR " + short_err(e)
        wav_for_asr = ref_wav
    if i == 0 and ref_wav:
        try:
            pcm, lat = tts_call(key, "Magpie-Multilingual.EN-US.Jason")
            save_wav(f"{OUT}/tts_jason.wav", pcm, SR)
            row["tts_jason"] = f"OK {lat:.2f}s"
        except Exception as e:
            row["tts_jason"] = "ERR " + short_err(e)
    if wav_for_asr:
        try:
            txt, lat = asr_call(key, ASR_FID, wav_for_asr, "multi")
            row["asr_multi"] = f"OK {lat:.2f}s: {txt!r}"
        except Exception as e:
            row["asr_multi"] = "ERR " + short_err(e)
        if i == 0:
            try:
                txt, lat = asr_call(key, ASR_V2_FID, wav_for_asr, "en-US")
                row["asr_v2"] = f"OK {lat:.2f}s: {txt!r}"
            except Exception as e:
                row["asr_v2"] = "ERR " + short_err(e)
    print(json.dumps(row), flush=True)
    results.append(row)
json.dump(results, open(f"{OUT}/results.json", "w"), indent=1)
