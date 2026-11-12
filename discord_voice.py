#!/usr/bin/env python3
"""
Discord voice for Lumenis (used by discord_listener.py).

What it does, only when the owner asks for it in the watched text channel:

  !lumenis join     join the voice channel the owner is in (joins deafened: hears nothing)
  !lumenis listen   undeafen and listen to the OWNER ONLY; each thing the owner says is
                    transcribed (NVIDIA Parakeet ASR), sent to the reactor in voice mode,
                    and the answer is spoken back (NVIDIA Magpie TTS) and posted as text
  !lumenis stop     stop listening (deafens again, stays in the channel)
  !lumenis say ...  speak the given text in the voice channel
  !lumenis voice    show voice status
  !lumenis leave    leave the voice channel

While he is in a voice channel, his replies to the owner's text messages are also spoken.

Privacy / safety:
  * Nothing joins, listens or speaks unless the owner typed the command.
  * Only the owner's audio is ever processed. Packets from anyone else are replaced with
    silence before decoding (and are never DAVE-decrypted); nothing is recorded to disk.
  * Every heard sentence is echoed in the text channel, so listening is never hidden.
  * He leaves when the owner leaves the voice channel, and after an idle timeout.

Technical notes:
  * Playback uses discord.py's own voice client (PyNaCl + libopus + davey for Discord's
    DAVE end-to-end encryption).
  * Receiving uses discord-ext-voice-recv, which does not know about DAVE. This module
    patches its reader so that, when DAVE is active, the owner's frames are decrypted with
    the voice connection's DAVE session (davey) before Opus decoding.
  * Speech keys come from .env (NVIDIA_SPEECH_API_KEY, else NVIDIA_API_KEY, ...). Never logged.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import threading
import time
from collections import deque

import numpy as np

log = logging.getLogger("discord_voice")

# ── Speech (NVIDIA Riva on NVCF) ─────────────────────────────────────────────
SPEECH_SERVER = os.environ.get("O2_SPEECH_SERVER", "grpc.nvcf.nvidia.com:443")
TTS_FUNCTION_ID = os.environ.get("O2_TTS_FUNCTION_ID", "877104f7-e885-42b9-8de8-f6e4c6303969")  # magpie-tts-multilingual
ASR_FUNCTION_ID = os.environ.get("O2_ASR_FUNCTION_ID", "d3fe9151-442b-4204-a70d-5fcc597fd610")  # parakeet-tdt-0.6b-v2 en-US
ASR_LANGUAGE = os.environ.get("O2_ASR_LANGUAGE", "en-US")
TTS_VOICE = os.environ.get("O2_TTS_VOICE", "Magpie-Multilingual.EN-US.Jason")
TTS_LANGUAGE = os.environ.get("O2_TTS_LANGUAGE", "en-US")
TTS_RATE = 22050
DISCORD_RATE = 48000            # Discord PCM: 48 kHz, 16-bit, stereo
ASR_RATE = 16000
KEY_ENVS = ("NVIDIA_SPEECH_API_KEY", "NVIDIA_API_KEY", "NVIDIA_API_KEY_2", "NVIDIA_API_KEY_3",
            "NVIDIA_API_KEY_SECONDARY", "NVIDIA_API_KEY_CLEAN_3")
# Names Parakeet should prefer ("Lumenis" is otherwise heard as "Luminous")
BOOST_WORDS = [w for w in os.environ.get("O2_ASR_BOOST_WORDS", "Lumenis,Pahrump").split(",") if w.strip()]
BOOST_SCORE = float(os.environ.get("O2_ASR_BOOST_SCORE", "6"))
TTS_CHUNK = 350                 # characters per TTS request
MAX_SPOKEN = int(os.environ.get("O2_VOICE_MAX_SPOKEN", "1200"))  # characters spoken per reply

# ── Listening / segmentation ─────────────────────────────────────────────────
VAD_RMS = int(os.environ.get("O2_VOICE_VAD_RMS", "350"))      # int16 RMS that counts as voice
END_SILENCE = float(os.environ.get("O2_VOICE_END_SILENCE", "1.2"))  # seconds of quiet that end a sentence
MIN_VOICED = 0.35               # seconds of voice needed for an utterance to count
MAX_UTTERANCE = 30.0            # seconds; force-finish longer speech
PREROLL_FRAMES = 15             # 20 ms frames kept before voice starts (300 ms)
IDLE_TIMEOUT = int(os.environ.get("O2_VOICE_IDLE_TIMEOUT", "1800"))  # leave after this many idle seconds

OPUS_SILENCE = b"\xf8\xff\xfe"
SPEECH_EMOJI = "\U0001F399\ufe0f"   # studio microphone


class SpeechError(RuntimeError):
    pass


def _keys():
    seen, out = set(), []
    for name in KEY_ENVS:
        v = (os.environ.get(name) or "").strip().strip('"').strip("'")
        if v.startswith("nvapi-") and v not in seen:
            seen.add(v)
            out.append((name, v))
    return out


_good_key = {"name": None}


def _short_err(e) -> str:
    code = getattr(e, "code", None)
    c = code().name if callable(code) else type(e).__name__
    det = getattr(e, "details", None)
    d = det() if callable(det) else str(e)
    return f"{c}: {re.sub(r'nvapi-[A-Za-z0-9_-]+', 'nvapi-***', d or '')[:160]}"


def _with_key(fid: str, fn):
    """Run fn(auth) with the first speech key that works; remember which one did."""
    import riva.client
    keys = _keys()
    if not keys:
        raise SpeechError("no NVIDIA speech key in .env")
    keys.sort(key=lambda kv: kv[0] != _good_key["name"])
    last = None
    for name, key in keys:
        auth = riva.client.Auth(None, True, SPEECH_SERVER,
                                [["function-id", fid], ["authorization", "Bearer " + key]])
        try:
            res = fn(auth)
            _good_key["name"] = name
            return res
        except Exception as e:  # grpc.RpcError and friends
            last = _short_err(e)
            code = getattr(e, "code", None)
            cname = code().name if callable(code) else ""
            if cname in ("PERMISSION_DENIED", "UNAUTHENTICATED", "RESOURCE_EXHAUSTED"):
                log.warning("speech key %s refused (%s); trying the next one", name, cname)
                continue
            raise SpeechError(last)
    raise SpeechError(f"every speech key was refused (last: {last})")


# ── Audio conversion ─────────────────────────────────────────────────────────
def resample_linear(x: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst or len(x) == 0:
        return x.astype(np.float32)
    n = int(round(len(x) * dst / src))
    t = np.arange(n, dtype=np.float64) * (src / dst)
    return np.interp(t, np.arange(len(x)), x.astype(np.float64)).astype(np.float32)


def mono_to_discord(pcm: bytes, rate: int) -> bytes:
    """16-bit mono PCM at `rate` -> 16-bit stereo 48 kHz PCM for discord.PCMAudio."""
    x = np.frombuffer(pcm, dtype="<i2")
    y = np.clip(np.round(resample_linear(x, rate, DISCORD_RATE)), -32768, 32767).astype("<i2")
    st = np.repeat(y, 2)
    pad = (-len(st)) % 1920  # whole 20 ms frames (960 samples x 2 channels)
    return np.concatenate([st, np.zeros(pad, dtype="<i2")]).tobytes()


_LP = None


def discord_to_asr(pcm: bytes) -> bytes:
    """16-bit stereo 48 kHz PCM -> 16-bit mono 16 kHz PCM (low-pass, then keep every 3rd sample)."""
    global _LP
    x = np.frombuffer(pcm[: len(pcm) - len(pcm) % 4], dtype="<i2").astype(np.float32)
    x = x.reshape(-1, 2).mean(axis=1)
    if _LP is None:
        n = np.arange(-31, 32)
        fc = 7000 / DISCORD_RATE
        h = 2 * fc * np.sinc(2 * fc * n) * np.hamming(len(n))
        _LP = (h / h.sum()).astype(np.float32)
    y = np.convolve(x, _LP, mode="same")[::3]
    return np.clip(np.round(y), -32768, 32767).astype("<i2").tobytes()


def rms16(pcm: bytes) -> float:
    x = np.frombuffer(pcm[: len(pcm) - len(pcm) % 2], dtype="<i2").astype(np.float32)
    return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0


# ── Text to speech / speech to text ──────────────────────────────────────────
def clean_for_speech(text: str) -> tuple[str, bool]:
    """Strip markdown/code/links so the reply reads aloud well. Returns (text, truncated)."""
    t = re.sub(r"```.*?```", " (code block in the text channel) ", text or "", flags=re.S)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", t)
    t = re.sub(r"<?https?://\S+>?", " link in the text channel ", t)
    t = re.sub(r"<a?:(\w+):\d+>", r"\1", t)          # custom emoji
    t = re.sub(r"<[@#][!&]?\d+>", "", t)               # mentions
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"^\s*[-*•]\s+", "", t, flags=re.M)
    t = re.sub(r"[*_~|>]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    truncated = False
    if len(t) > MAX_SPOKEN:
        cut = max(t.rfind(". ", 0, MAX_SPOKEN), t.rfind("? ", 0, MAX_SPOKEN), t.rfind("! ", 0, MAX_SPOKEN))
        t = t[: cut + 1 if cut > MAX_SPOKEN // 2 else MAX_SPOKEN].rstrip()
        truncated = True
    return t, truncated


def _chunks(t: str, limit: int = TTS_CHUNK):
    parts, cur = [], ""
    for s in re.split(r"(?<=[.!?])\s+", t):
        while len(s) > limit:
            cut = s.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(s[:cut])
            s = s[cut:].lstrip()
        if len(cur) + len(s) + 1 > limit and cur:
            parts.append(cur)
            cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        parts.append(cur)
    return [p for p in parts if p.strip()]


def tts_pcm(text: str) -> bytes:
    """Text -> 16-bit mono PCM at TTS_RATE (blocking)."""
    import riva.client

    def run(auth):
        svc = riva.client.SpeechSynthesisService(auth)
        out = []
        for part in _chunks(text):
            r = svc.synthesize(part, voice_name=TTS_VOICE, language_code=TTS_LANGUAGE, sample_rate_hz=TTS_RATE)
            out.append(r.audio)
            out.append(b"\x00\x00" * int(TTS_RATE * 0.15))  # short gap between chunks
        return b"".join(out)
    if not text.strip():
        return b""
    return _with_key(TTS_FUNCTION_ID, run)


def asr_text(pcm16k: bytes) -> str:
    """16-bit mono 16 kHz PCM -> transcript (blocking)."""
    import riva.client

    def run(auth):
        svc = riva.client.ASRService(auth)
        cfg = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM, sample_rate_hertz=ASR_RATE,
            language_code=ASR_LANGUAGE, max_alternatives=1, enable_automatic_punctuation=True,
            audio_channel_count=1)
        if BOOST_WORDS:
            riva.client.add_word_boosting_to_config(cfg, BOOST_WORDS, BOOST_SCORE)
        r = svc.offline_recognize(pcm16k, cfg)
        return " ".join(res.alternatives[0].transcript for res in r.results if res.alternatives).strip()
    if len(pcm16k) < ASR_RATE * 2 * 0.2:
        return ""
    return _with_key(ASR_FUNCTION_ID, run)


# ── Utterance segmentation (pure, testable) ──────────────────────────────────
class UtteranceSegmenter:
    """Collects 20 ms Discord PCM frames from one speaker and cuts them into utterances."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.pre = deque(maxlen=PREROLL_FRAMES)
        self.buf = []
        self.active = False
        self.voiced = 0.0
        self.started = 0.0
        self.last_voice = 0.0

    def feed(self, pcm: bytes, now: float):
        if not pcm:
            return
        loud = rms16(pcm) >= VAD_RMS
        dur = len(pcm) / (DISCORD_RATE * 4)
        with self.lock:
            if not self.active:
                if loud:
                    self.active = True
                    self.buf = list(self.pre)
                    self.pre.clear()
                    self.started = now
                    self.voiced = 0.0
                else:
                    self.pre.append(pcm)
                    return
            self.buf.append(pcm)
            if loud:
                self.voiced += dur
                self.last_voice = now

    def poll(self, now: float):
        """Return a finished utterance (bytes) or None."""
        with self.lock:
            if not self.active:
                return None
            if now - self.last_voice < END_SILENCE and now - self.started < MAX_UTTERANCE:
                return None
            pcm, voiced = b"".join(self.buf), self.voiced
            self.reset()
        return pcm if voiced >= MIN_VOICED else None


# ── DAVE-aware receive patch for discord-ext-voice-recv ──────────────────────
dave_stats = {"decrypted": 0, "failed": 0, "passthrough": 0, "dropped_other": 0}


def _post_decrypt(vc, ssrc: int, data: bytes) -> bytes:
    allowed = getattr(vc, "o2_hear_only", None) or set()
    uid = vc._ssrc_to_id.get(ssrc)
    if uid is None or uid not in allowed:
        dave_stats["dropped_other"] += 1
        return OPUS_SILENCE
    if data == OPUS_SILENCE:
        return data
    conn = getattr(vc, "_connection", None)
    ds = getattr(conn, "dave_session", None)
    if conn is not None and getattr(conn, "dave_protocol_version", 0) and ds is not None and ds.ready:
        try:
            import davey
            out = bytes(ds.decrypt(uid, davey.MediaType.audio, bytes(data)))
            dave_stats["decrypted"] += 1
            return out
        except Exception as e:
            dave_stats["failed"] += 1
            if dave_stats["failed"] in (1, 10, 100) or dave_stats["failed"] % 1000 == 0:
                log.warning("DAVE decrypt failed for the owner's audio (%s; %d failures so far)",
                            type(e).__name__, dave_stats["failed"])
            return OPUS_SILENCE
    dave_stats["passthrough"] += 1
    return data


def install_receive_patch():
    from discord.ext.voice_recv import reader
    if getattr(reader.AudioReader, "_o2_dave_patched", False):
        return
    orig_init = reader.AudioReader.__init__

    def __init__(self, sink, voice_client, *args, **kwargs):
        orig_init(self, sink, voice_client, *args, **kwargs)
        base = self.decryptor.decrypt_rtp

        def decrypt_rtp(packet):
            return _post_decrypt(voice_client, packet.ssrc, base(packet))
        self.decryptor.decrypt_rtp = decrypt_rtp

    reader.AudioReader.__init__ = __init__
    reader.AudioReader._o2_dave_patched = True


# ── Voice session manager (used by discord_listener.run_bot) ─────────────────
class VoiceManager:
    def __init__(self, client, owner_id: int, ask, post, write_state):
        """ask(text) -> awaitable reply str (voice-mode reactor call for the owner);
        post(text) -> awaitable, posts into the watched text channel."""
        self.client = client
        self.owner_id = owner_id
        self.ask = ask
        self.post = post
        self.write_state = write_state
        self.vc = None
        self.listening = False
        self.busy = False
        self.seg = UtteranceSegmenter()
        self.last_activity = time.time()
        self.watch_task = None
        self.speak_lock = asyncio.Lock()
        self.last_error = None
        self.heard = 0
        self.spoken = 0
        install_receive_patch()

    # state ------------------------------------------------------------------
    def connected(self) -> bool:
        return bool(self.vc and self.vc.is_connected())

    def _state(self, **extra):
        self.write_state(voice_connected=self.connected(),
                         voice_channel=(self.vc.channel.name if self.connected() else None),
                         voice_listening=self.listening and self.connected(), **extra)

    def status_text(self) -> str:
        if not self.connected():
            s = "Voice: not in a voice channel."
        else:
            conn = self.vc._connection
            dave = getattr(conn, "dave_protocol_version", 0)
            s = (f"Voice: in **{self.vc.channel.name}**, "
                 f"{'listening to the owner only' if self.listening else 'not listening (deafened)'}; "
                 f"DAVE encryption {'on (v%d)' % dave if dave else 'off'}; "
                 f"heard {self.heard}, spoke {self.spoken} this session; "
                 f"owner frames decrypted {dave_stats['decrypted']}, failed {dave_stats['failed']}.")
        if self.last_error:
            s += f" Last problem: {self.last_error}"
        return s

    # commands ---------------------------------------------------------------
    async def join(self, member) -> str:
        from discord.ext import voice_recv
        vs = getattr(member, "voice", None)
        if not vs or not vs.channel:
            return "Join a voice channel first, then type `!lumenis join`."
        ch = vs.channel
        if self.connected():
            if self.vc.channel.id == ch.id:
                return f"Already in **{ch.name}**."
            await self.vc.move_to(ch)
            if self.listening:
                await self._set_deaf(False)
            self._state()
            return f"Moved to **{ch.name}**."
        perms = ch.permissions_for(ch.guild.me)
        if not perms.connect or not perms.speak:
            return (f"I don't have permission to {'connect to' if not perms.connect else 'speak in'} "
                    f"**{ch.name}**. Give the bot Connect and Speak there.")
        self.vc = await ch.connect(cls=voice_recv.VoiceRecvClient, self_deaf=True, timeout=30, reconnect=True)
        self.vc.o2_hear_only = {self.owner_id}
        self.listening = False
        self.seg.reset()
        self.heard = self.spoken = 0
        self.last_activity = time.time()
        if not self.watch_task or self.watch_task.done():
            self.watch_task = asyncio.create_task(self._watch())
        self._state()
        log.info("joined voice channel %s (deafened)", ch.name)
        return (f"Joined **{ch.name}**. I'm deafened, so I can't hear anyone yet. "
                f"Type `!lumenis listen` and I'll listen to you only; `!lumenis stop` to stop, "
                f"`!lumenis leave` to leave.")

    async def leave(self, reason: str = "") -> str:
        if not self.connected():
            self.vc = None
            self.listening = False
            self._state()
            return "I'm not in a voice channel."
        name = self.vc.channel.name
        try:
            if self.vc.is_listening():
                self.vc.stop_listening()
        except Exception:
            pass
        await self.vc.disconnect(force=True)
        self.vc = None
        self.listening = False
        self.seg.reset()
        self._state()
        log.info("left voice channel %s %s", name, reason)
        return f"Left **{name}**." + (f" ({reason})" if reason else "")

    async def _set_deaf(self, deaf: bool):
        await self.vc.guild.change_voice_state(channel=self.vc.channel, self_deaf=deaf, self_mute=False)

    async def listen(self) -> str:
        from discord.ext import voice_recv
        if not self.connected():
            return "I'm not in a voice channel. Type `!lumenis join` first."
        if self.listening:
            return "Already listening (to you only)."
        self.seg.reset()
        self.vc.o2_hear_only = {self.owner_id}
        mgr = self

        class OwnerSink(voice_recv.AudioSink):
            def wants_opus(self):
                return False

            def write(self, user, data):
                if user is None or user.id != mgr.owner_id or not mgr.listening or mgr.busy:
                    return
                mgr.seg.feed(data.pcm, time.monotonic())

            def cleanup(self):
                pass

        await self._set_deaf(False)
        self.vc.listen(OwnerSink())
        self.listening = True
        self.last_activity = time.time()
        self._state()
        log.info("listening to the owner in %s", self.vc.channel.name)
        return (f"{SPEECH_EMOJI} Listening to you only in **{self.vc.channel.name}**. Talk, pause, and I'll answer "
                f"out loud. Everything I hear gets posted here. `!lumenis stop` to stop.")

    async def stop_listening(self) -> str:
        if not self.connected() or not self.listening:
            self.listening = False
            self._state()
            return "I'm not listening."
        self.listening = False
        try:
            self.vc.stop_listening()
        except Exception:
            pass
        self.seg.reset()
        await self._set_deaf(True)
        self._state()
        return "Stopped listening. I'm deafened again but still in the channel (`!lumenis leave` to go)."

    async def say(self, text: str) -> bool:
        """Speak text in the current voice channel. Returns True if audio was played."""
        if not self.connected():
            return False
        spoken, truncated = clean_for_speech(text)
        if truncated:
            spoken += " The rest is in the text channel."
        if not spoken:
            return False
        import discord
        async with self.speak_lock:
            try:
                pcm = await asyncio.to_thread(tts_pcm, spoken)
            except SpeechError as e:
                self.last_error = f"text to speech failed: {e}"
                log.warning("tts failed: %s", e)
                return False
            if not self.connected():
                return False
            audio = mono_to_discord(pcm, TTS_RATE)
            done = asyncio.Event()
            loop = asyncio.get_running_loop()
            err = {}

            def after(e):
                err["e"] = e
                loop.call_soon_threadsafe(done.set)
            if self.vc.is_playing():
                self.vc.stop()
            self.vc.play(discord.PCMAudio(io.BytesIO(audio)), after=after)
            try:
                await asyncio.wait_for(done.wait(), timeout=len(audio) / (DISCORD_RATE * 4) + 15)
            except asyncio.TimeoutError:
                self.vc.stop()
            if err.get("e"):
                self.last_error = f"playback failed: {type(err['e']).__name__}"
                return False
            self.spoken += 1
            self.last_activity = time.time()
            self._state(voice_last_spoke_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
            return True

    # background -------------------------------------------------------------
    async def on_voice_state_update(self, member, before, after):
        if not self.connected():
            return
        if member.id == self.owner_id and (after.channel is None or after.channel.id != self.vc.channel.id):
            msg = await self.leave("you left the voice channel")
            await self.post(msg)
        elif self.client.user and member.id == self.client.user.id and after.channel is None:
            self.vc = None
            self.listening = False
            self._state()

    async def _watch(self):
        while True:
            await asyncio.sleep(0.2)
            if not self.connected():
                if self.vc is not None and not self.vc.is_connected():
                    await asyncio.sleep(5)   # give reconnect a moment
                    if self.vc is not None and not self.vc.is_connected():
                        self.vc = None
                        self.listening = False
                        self._state()
                if self.vc is None:
                    return
                continue
            if time.time() - self.last_activity > IDLE_TIMEOUT:
                await self.post(await self.leave(f"idle for {IDLE_TIMEOUT // 60} minutes"))
                return
            if not self.listening or self.busy:
                continue
            pcm = self.seg.poll(time.monotonic())
            if pcm:
                self.busy = True
                asyncio.create_task(self._handle_utterance(pcm))

    async def _handle_utterance(self, pcm: bytes):
        try:
            self.last_activity = time.time()
            try:
                text = await asyncio.to_thread(asr_text, discord_to_asr(pcm))
            except SpeechError as e:
                self.last_error = f"speech to text failed: {e}"
                log.warning("asr failed: %s", e)
                await self.post(f"{SPEECH_EMOJI} I heard you but couldn't transcribe it ({e}).")
                return
            if len(re.sub(r"\W", "", text)) < 2:
                return
            self.heard += 1
            self._state(voice_last_heard_at=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
            log.info("heard owner (%.1f s): %r", len(pcm) / (DISCORD_RATE * 4), text[:200])
            await self.post(f"{SPEECH_EMOJI} **You said:** {text}")
            try:
                reply = await self.ask(text)
            except RuntimeError as e:
                await self.post(f"Lumenis couldn't answer this time: {e}.")
                await self.say("Sorry, I couldn't get an answer that time.")
                return
            await self.post(reply)
            await self.say(reply)
        except Exception:
            log.exception("voice turn failed")
        finally:
            self.seg.reset()
            self.busy = False
