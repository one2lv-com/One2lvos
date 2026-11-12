"""Reference clips for zero-shot voice cloning (TTS role).

NVIDIA's TTS NIM HTTP reference asks for the audio_prompt clip as a 16-bit
mono WAV at 22.05 kHz or higher, 3 to 10 seconds long. This module takes
whatever path the user typed on the phone, checks it, and returns WAV bytes
in that shape: stdlib only, with ffmpeg used for non-WAV formats when it
is installed (pkg install ffmpeg on Termux).
"""

import array
import io
import os
import shutil
import subprocess
import sys
import wave

MAX_BYTES = 25 * 1024 * 1024        # refuse anything bigger before reading it
MIN_SEC, MAX_SEC = 3.0, 10.0
MIN_RATE = 22050
AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".amr", ".3gp", ".webm")

# Termux and Android expose shared storage under several names
STORAGE_ALIASES = (("/sdcard/", "/storage/emulated/0/"), ("~/storage/shared/", "/storage/emulated/0/"),
                   ("/storage/self/primary/", "/storage/emulated/0/"))


class CloneError(Exception):
    pass


def clean_path(raw):
    """Typed or pasted path -> a real path. Strips quotes, file://, shell
    escapes ('\\ '), stray spaces and tabs, expands ~, and tries the other
    names for Android shared storage when the typed one doesn't exist."""
    p = (raw or "").strip().strip("\t").strip()
    if len(p) >= 2 and p[0] == p[-1] and p[0] in "'\"":
        p = p[1:-1].strip()
    if p.startswith("file://"):
        p = p[7:]
    p = p.replace("\\ ", " ").replace("\t", "")
    try:
        from urllib.parse import unquote
        if "%20" in p:
            p = unquote(p)
    except ImportError:  # pragma: no cover
        pass
    p = os.path.expanduser(p)
    if os.path.exists(p):
        return p
    expanded = [(os.path.expanduser(a), b) for a, b in STORAGE_ALIASES]
    for a, b in expanded + [(b, a) for a, b in expanded]:
        if p.startswith(a) and os.path.exists(b + p[len(a):]):
            return b + p[len(a):]
    return p


def _pcm_to_mono16(frames, width, channels):
    """Raw PCM -> array('h') mono 16-bit (stdlib, no audioop)."""
    if width == 2:
        a = array.array("h")
        a.frombytes(frames[: len(frames) - len(frames) % 2])
        if sys.byteorder == "big":
            a.byteswap()
        samples = a
    elif width == 1:
        samples = array.array("h", ((b - 128) << 8 for b in frames))
    elif width in (3, 4):
        samples = array.array("h")
        for i in range(0, len(frames) - width + 1, width):
            v = int.from_bytes(frames[i:i + width], "little", signed=True)
            samples.append(v >> (8 * width - 16))
    else:
        raise CloneError(f"unsupported WAV sample width: {width * 8}-bit")
    if channels > 1:
        mono = array.array("h")
        for i in range(0, len(samples) - channels + 1, channels):
            mono.append(int(sum(samples[i:i + channels]) / channels))
        samples = mono
    return samples


def _resample(samples, src, dst):
    """Linear-interpolation resample (only used to go up to 22.05 kHz)."""
    if src == dst or not samples:
        return samples
    n = int(len(samples) * dst / src)
    out = array.array("h")
    step = src / dst
    last = len(samples) - 1
    for i in range(n):
        x = i * step
        j = int(x)
        f = x - j
        a = samples[min(j, last)]
        b = samples[min(j + 1, last)]
        out.append(int(a + (b - a) * f))
    return out


def _wav_bytes(samples, rate):
    buf = io.BytesIO()
    s = array.array("h", samples)
    if sys.byteorder == "big":
        s.byteswap()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(s.tobytes())
    return buf.getvalue()


def _ffmpeg_to_wav(path):
    ff = shutil.which("ffmpeg")
    if not ff:
        raise CloneError(f"{os.path.splitext(path)[1] or 'this'} files need ffmpeg to convert "
                         "(Termux: pkg install ffmpeg), or convert the clip to WAV yourself")
    try:
        p = subprocess.run([ff, "-v", "error", "-i", path, "-t", str(MAX_SEC), "-ac", "1", "-ar", "22050",
                            "-sample_fmt", "s16", "-f", "wav", "-"], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise CloneError(f"ffmpeg failed: {e}")
    if p.returncode != 0 or len(p.stdout) < 100:
        raise CloneError("ffmpeg could not read the clip: " + p.stderr.decode("utf-8", "replace")[:200])
    return p.stdout


def prepare(raw_path):
    """Check and normalise a reference clip.

    Returns (path, wav_bytes, info) where info has seconds, rate, notes
    (list of what was changed or what to watch out for). Raises CloneError
    with a plain reason when the clip can't be used."""
    path = clean_path(raw_path)
    if not path:
        raise CloneError("no path given")
    if not os.path.isfile(path):
        hint = ""
        if path.startswith("/storage/") or path.startswith("/sdcard"):
            hint = " (if the file is there, run termux-setup-storage once so Termux can read shared storage)"
        raise CloneError(f"file not found: {path}{hint}")
    size = os.path.getsize(path)
    if size == 0:
        raise CloneError("the file is empty")
    if size > MAX_BYTES:
        raise CloneError(f"the file is {size // (1024 * 1024)} MB; use a clip of 10 seconds or less")
    ext = os.path.splitext(path)[1].lower()
    if ext and ext not in AUDIO_EXTS:
        raise CloneError(f"{ext} is not an audio format this lab handles ({', '.join(AUDIO_EXTS)})")
    notes = []
    with open(path, "rb") as f:
        head = f.read(12)
    is_wav = head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if not is_wav:
        data = _ffmpeg_to_wav(path)
        notes.append("converted to 16-bit mono 22.05 kHz WAV with ffmpeg")
    else:
        with open(path, "rb") as f:
            data = f.read()
    try:
        with wave.open(io.BytesIO(data)) as w:
            ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            comp = w.getcomptype()
            frames = w.readframes(min(n, int(rate * MAX_SEC)) if rate else n)
    except (wave.Error, EOFError) as e:
        if is_wav:   # e.g. float or ADPCM WAV: let ffmpeg try
            data = _ffmpeg_to_wav(path)
            notes.append("converted to 16-bit mono 22.05 kHz WAV with ffmpeg")
            with wave.open(io.BytesIO(data)) as w:
                ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
                comp = w.getcomptype()
                frames = w.readframes(n)
        else:
            raise CloneError(f"unreadable WAV: {e}")
    if comp != "NONE":
        raise CloneError(f"compressed WAV ({comp}) is not supported; convert it to PCM WAV")
    if not rate:
        raise CloneError("the WAV has no sample rate")
    seconds = n / float(rate)
    if seconds < MIN_SEC:
        raise CloneError(f"the clip is {seconds:.1f} s; the model needs at least {MIN_SEC:.0f} s of speech")
    changed = False
    samples = _pcm_to_mono16(frames, width, ch)
    if ch != 1 or width != 2:
        notes.append(f"converted {ch}-channel {width * 8}-bit audio to 16-bit mono")
        changed = True
    if rate < MIN_RATE:
        samples = _resample(samples, rate, MIN_RATE)
        notes.append(f"resampled {rate} Hz to {MIN_RATE} Hz (a clip recorded at 22.05 kHz or higher clones better)")
        rate = MIN_RATE
        changed = True
    if seconds > MAX_SEC:
        notes.append(f"trimmed {seconds:.1f} s to the first {MAX_SEC:.0f} s")
        seconds = MAX_SEC
        changed = True
    if changed:
        data = _wav_bytes(samples, rate)
    return path, data, {"seconds": round(min(seconds, MAX_SEC), 2), "rate": rate, "notes": notes,
                        "bytes": len(data)}
