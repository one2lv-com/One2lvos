#!/usr/bin/env python3
"""
Local checks for Discord voice (discord_voice.py). Joins no voice channel and posts nothing.

  1. voice dependencies load (PyNaCl, libopus, davey, discord-ext-voice-recv, riva)
  2. Magpie TTS -> Discord PCM (48 kHz stereo, whole 20 ms frames), read back through discord.PCMAudio
  3. Opus encode -> decode round trip (what travels over Discord voice)
  4. utterance segmenter cuts the decoded speech + trailing silence into one utterance
  5. Parakeet ASR transcribes that utterance (word overlap with the spoken text)
  6. receive patch: owner-only filter and DAVE decrypt hook (with stand-in sessions)
  7. reactor voice mode: one owner turn with mode=voice through the listener's ask_lumenis

Usage: .venv/bin/python3 tests/voice_test.py [--no-reactor]
"""
import asyncio
import io
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

results = {}


def rec(name, ok, detail):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


def words(s):
    return set(re.findall(r"[a-z']+", s.lower()))


def main():
    import numpy as np
    import discord
    import discord.opus as dop
    import nacl
    import davey
    from discord.ext import voice_recv
    import riva.client  # noqa: F401
    import discord_voice as dv

    if not dop.is_loaded():
        dop._load_default()
    rec("deps", dop.is_loaded(), f"discord.py {discord.__version__}, PyNaCl {nacl.__version__}, libopus "
        f"{'loaded' if dop.is_loaded() else 'MISSING'}, davey (DAVE v{davey.DAVE_PROTOCOL_VERSION}), voice_recv ok")

    phrase = "Hey Lumenis, the quick brown fox jumps over the lazy dog near the river bank"
    t0 = time.time()
    mono = dv.tts_pcm(phrase)
    tts_s = time.time() - t0
    pcm48 = dv.mono_to_discord(mono, dv.TTS_RATE)
    src = discord.PCMAudio(io.BytesIO(pcm48))
    frames = []
    while True:
        f = src.read()
        if not f:
            break
        frames.append(f)
    full = all(len(f) == 3840 for f in frames)
    rec("tts", len(frames) > 50 and full,
        f"{tts_s:.2f} s to synthesize, {len(mono) / 2 / dv.TTS_RATE:.2f} s of audio -> {len(frames)} Discord "
        f"20 ms frames (all 3840 bytes: {full}); voice {dv.TTS_VOICE}; key {dv._good_key['name']}")

    enc, dec = dop.Encoder(), voice_recv.opus.Decoder()
    decoded, opus_bytes = [], 0
    for f in frames:
        pkt = enc.encode(f, enc.SAMPLES_PER_FRAME)
        opus_bytes += len(pkt)
        decoded.append(dec.decode(pkt, fec=False))
    rec("opus_roundtrip", len(decoded) == len(frames) and all(len(d) == 3840 for d in decoded),
        f"{len(frames)} frames -> {opus_bytes} bytes of Opus -> {len(decoded)} decoded frames")

    seg = dv.UtteranceSegmenter()
    silence = b"\x00" * 3840
    now, got = 1000.0, []
    for f in [silence] * 10 + decoded + [silence] * 60:
        seg.feed(f, now)
        now += 0.02
        u = seg.poll(now)
        if u:
            got.append(u)
    # two sentences with a 2 s pause between them must come out as two utterances
    seg2, now2, got2 = dv.UtteranceSegmenter(), 0.0, []
    for f in decoded + [silence] * 100 + decoded + [silence] * 100:
        seg2.feed(f, now2)
        now2 += 0.02
        u = seg2.poll(now2)
        if u:
            got2.append(u)
    rec("segmenter", len(got) == 1 and len(got2) == 2,
        (f"one sentence -> {len(got)} utterance ({len(got[0]) / (48000 * 4):.2f} s); "
         f"two sentences 2 s apart -> {len(got2)} utterances") if got else "no utterance")

    if got:
        t0 = time.time()
        text = dv.asr_text(dv.discord_to_asr(got[0]))
        import difflib
        norm = lambda x: re.sub(r"[^a-z]", "", x.lower())  # noqa: E731
        sim = difflib.SequenceMatcher(None, norm(phrase), norm(text)).ratio()
        rec("asr", sim >= 0.85, f"{time.time() - t0:.2f} s, heard {text!r} ({sim:.0%} letter similarity to "
            f"{phrase!r})")

    # receive patch: owner-only filter + DAVE hook
    class FakeDave:
        def __init__(self, ok=True):
            self.ready, self.ok, self.calls = True, ok, []

        def decrypt(self, uid, media, data):
            self.calls.append((uid, media))
            if not self.ok:
                raise ValueError("bad frame")
            return data[::-1]

    class Conn:
        dave_protocol_version = 0
        dave_session = None

    class VC:
        _ssrc_to_id = {11: 42, 22: 99}
        o2_hear_only = {42}
        _connection = Conn()

    vc = VC()
    frame = b"\x01\x02\x03\x04"
    a = dv._post_decrypt(vc, 11, frame) == frame                 # owner, no DAVE -> unchanged
    b = dv._post_decrypt(vc, 22, frame) == dv.OPUS_SILENCE       # someone else -> silence
    c = dv._post_decrypt(vc, 33, frame) == dv.OPUS_SILENCE       # unknown ssrc -> silence
    vc._connection.dave_protocol_version, vc._connection.dave_session = 1, FakeDave()
    d = dv._post_decrypt(vc, 11, frame) == frame[::-1] and vc._connection.dave_session.calls[0][0] == 42
    e = dv._post_decrypt(vc, 22, frame) == dv.OPUS_SILENCE and len(vc._connection.dave_session.calls) == 1
    vc._connection.dave_session = FakeDave(ok=False)
    f_ = dv._post_decrypt(vc, 11, frame) == dv.OPUS_SILENCE
    real = davey.DaveSession(1, 42, 7)
    vc._connection.dave_session = real                           # real davey session, not in a group yet
    g = dv._post_decrypt(vc, 11, frame) == frame                 # not ready -> passthrough, no crash
    dv.install_receive_patch()
    from discord.ext.voice_recv import reader
    rec("receive_patch", all([a, b, c, d, e, f_, g, reader.AudioReader._o2_dave_patched]),
        f"owner passthrough {a}, others silenced {b}, unknown silenced {c}, DAVE decrypt used for owner {d}, "
        f"others never DAVE-decrypted {e}, failed decrypt -> silence {f_}, real davey session not ready -> "
        f"passthrough {g} (ready={real.ready}), AudioReader patched {reader.AudioReader._o2_dave_patched}")

    if "--no-reactor" not in sys.argv:
        import discord_listener as dl
        t0 = time.time()
        try:
            reply, meta = asyncio.run(dl.ask_lumenis(dl.OWNER_ID, "voice-test", "Voice test: say hi in one short "
                                                     "sentence.", False, key_prefix="voicetest:", mode="voice"))
            rec("reactor_voice_mode", bool(reply), f"{time.time() - t0:.1f} s, seats={meta.get('seats_activated')}, "
                f"reply {reply[:160]!r}")
            spoken, trunc = dv.clean_for_speech(reply)
            t0 = time.time()
            pcm = dv.tts_pcm(spoken)
            rec("reply_to_speech", len(pcm) > 0, f"{time.time() - t0:.2f} s, {len(pcm) / 2 / dv.TTS_RATE:.1f} s of "
                f"audio (truncated={trunc})")
        except RuntimeError as e:
            rec("reactor_voice_mode", False, str(e))

    out = ROOT / "tests" / "voice_results.json"
    out.write_text(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "results": results},
                              indent=1))
    bad = [k for k, v in results.items() if not v["ok"]]
    print(f"\n{len(results) - len(bad)}/{len(results)} passed" + (f"; failed: {', '.join(bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
