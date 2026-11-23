"""Lab-wide audio bus (3.8.5): play Nim Lab audio on a phone's speaker, and
let the phone's mic feed a terminal voice call, while Nim Lab runs on a
headless VPS.

The VPS has no speaker and no microphone. Any part of the lab (Telegram
/autoplay, the terminal voice call, an agent through the HTTP API) hands a
clip to publish(); the clip lands in a spool folder under data/audio_bus,
and the phone bridge (nimbridge, a small Termux script) long-polls
GET /v1/audio/bus/events, downloads the clip and plays it through
termux-media-player. Nothing is ever played on the VPS.

Devices: every phone gets its own name and token (`nimlab audio add NAME`
on the VPS prints the token once; only its SHA-256 is kept). One device is
the ACTIVE one: audio and mic requests go to it and to no other phone.
A phone becomes active when its bridge starts (or `nimbridge use`), or with
`nimlab audio use NAME` here. A clip goes to every phone only when the
publisher asks for target "all" on purpose.

Formats: clips are stored as the voice model produced them. WAV, OGG/Opus,
MP3, FLAC and MP4/M4A are recognised by their first bytes and served with
the right type; headerless PCM (16-bit mono) is wrapped in a WAV header so
Android's player can read it. The bus is files plus one lock, so the
server, the Telegram poller, the scheduler and an SSH voice call (separate
processes) all share it.
"""

import base64
import contextlib
import hashlib
import hmac
import json
import os
import re
import secrets
import struct
import subprocess
import time

try:
    import fcntl
except ImportError:  # pragma: no cover - not on Linux/Termux
    fcntl = None

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
CLIP_RE = re.compile(r"^[A-Za-z0-9_-]{8,40}$")
PLAY_TTL = 180            # a play event older than this is skipped (no stale replies blurted out later)
CONTROL_TTL = 60          # stop / record events
CLIP_TTL = 6 * 3600       # clips are deleted after this
MAX_CLIPS_MB = 200        # and the spool is kept under this
MAX_EVENTS = 500
ONLINE_SEC = 75           # a device that polled within this is online
MAX_CLIP_MB = 20
MAX_UPLOAD_MB = 15
MIME = {"wav": "audio/wav", "ogg": "audio/ogg", "mp3": "audio/mpeg", "flac": "audio/flac",
        "m4a": "audio/mp4", "aac": "audio/aac", "webm": "audio/webm"}
DEFAULT_PCM_RATE = 22050


class BusError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------------------------------------------------------------------------
# files
# ---------------------------------------------------------------------------
def bus_dir():
    d = os.environ.get("NIMLAB_AUDIO_BUS_DIR")
    if not d:
        from . import store
        d = os.path.join(store.data_dir(), "audio_bus")
    for sub in ("", "events", "clips", "uploads"):
        os.makedirs(os.path.join(d, sub), mode=0o700, exist_ok=True)
    return d


def _p(*parts):
    return os.path.join(bus_dir(), *parts)


@contextlib.contextmanager
def _locked():
    f = open(_p(".lock"), "a+")
    try:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)
        yield
    finally:
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(path, obj, mode=0o600):
    tmp = f"{path}.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _write_bytes(path, data):
    tmp = f"{path}.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# devices
# ---------------------------------------------------------------------------
def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _registry():
    r = _read_json(_p("devices.json"), {})
    r.setdefault("devices", {})
    r.setdefault("active", None)
    return r


def _seen():
    return _read_json(_p("seen.json"), {})


def add_device(name, label=""):
    """Register a phone. -> its token (shown once; only the hash is kept).
    Adding a name that exists gives it a new token (the old one stops working)."""
    name = (name or "").strip().lower()
    if not NAME_RE.match(name):
        raise BusError(400, "device names are 1-32 characters: a-z, 0-9, - and _ (start with a letter or digit)")
    token = "nab_" + secrets.token_urlsafe(30)
    with _locked():
        r = _registry()
        old = r["devices"].get(name) or {}
        r["devices"][name] = {"token_sha256": _hash(token), "label": (label or old.get("label") or "")[:60],
                              "created": int(time.time())}
        _write_json(_p("devices.json"), r)
    return token


def remove_device(name):
    with _locked():
        r = _registry()
        if name not in r["devices"]:
            return False
        del r["devices"][name]
        if r.get("active") == name:
            r["active"] = None
        _write_json(_p("devices.json"), r)
    return True


def auth_device(token):
    """-> the device name the token belongs to, or None."""
    if not token or not token.startswith("nab_"):
        return None
    h = _hash(token)
    for name, d in _registry()["devices"].items():
        if hmac.compare_digest(h, d.get("token_sha256") or ""):
            return name
    return None


def set_active(name):
    with _locked():
        r = _registry()
        if name is not None and name not in r["devices"]:
            raise BusError(404, f"no device named {name!r}")
        r["active"] = name
        _write_json(_p("devices.json"), r)
    return name


def active():
    return _registry().get("active")


def touch(name, caps=None):
    """A device polled: remember when, and what it said it can do."""
    with _locked():
        s = _seen()
        s[name] = {"ts": time.time(), "caps": caps or {}}
        _write_json(_p("seen.json"), s)


def devices():
    """[{name, label, active, online, last_seen, mic}] for the device list."""
    r, s, now = _registry(), _seen(), time.time()
    out = []
    for name, d in sorted(r["devices"].items()):
        seen = s.get(name) or {}
        ts = seen.get("ts") or 0
        out.append({"name": name, "label": d.get("label") or "", "active": r.get("active") == name,
                    "online": bool(ts and now - ts < ONLINE_SEC), "last_seen": int(ts) if ts else None,
                    "mic": bool((seen.get("caps") or {}).get("mic"))})
    return out


def device_state(name):
    for d in devices():
        if d["name"] == name:
            return d
    return None


# ---------------------------------------------------------------------------
# formats
# ---------------------------------------------------------------------------
def sniff(data):
    """The container of an audio clip from its first bytes, or None for raw PCM."""
    h = bytes(data[:16])
    if h[:4] == b"RIFF" and h[8:12] == b"WAVE":
        return "wav"
    if h[:4] == b"OggS":
        return "ogg"
    if h[:4] == b"fLaC":
        return "flac"
    if h[:3] == b"ID3" or (len(h) > 1 and h[0] == 0xFF and (h[1] & 0xE0) == 0xE0 and (h[1] & 0x06) != 0):
        return "mp3"
    if h[4:8] == b"ftyp":
        return "m4a"
    if len(h) > 1 and h[0] == 0xFF and (h[1] & 0xF6) == 0xF0:
        return "aac"
    if h[:4] == b"\x1aE\xdf\xa3":
        return "webm"
    return None


def wav_from_pcm(pcm, rate=DEFAULT_PCM_RATE, channels=1, width=2):
    pcm = bytes(pcm)
    if len(pcm) % (width * channels):
        pcm = pcm[:len(pcm) - len(pcm) % (width * channels)]
    hdr = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " + struct.pack(
        "<IHHIIHH", 16, 1, channels, rate, rate * channels * width, channels * width, width * 8) + \
        b"data" + struct.pack("<I", len(pcm))
    return hdr + pcm


def normalize(data, fmt=None, pcm_rate=None):
    """-> (bytes, ext) a phone can play. fmt is what the producer said it
    is ('pcm' forces a WAV wrap); the bytes win when they say otherwise."""
    data = bytes(data or b"")
    if not data:
        raise BusError(400, "the clip is empty")
    found = sniff(data)
    if found:
        return data, found
    if (fmt or "pcm").lower() in ("pcm", "raw", "s16le", "l16", "linear16", "wav", ""):
        return wav_from_pcm(data, int(pcm_rate or DEFAULT_PCM_RATE)), "wav"
    raise BusError(415, f"unrecognised audio (said to be {fmt!r})")


def duration_ms(data, ext):
    """Clip length, so the phone queues the next clip instead of talking over
    this one. WAV from its header; others with ffprobe when it is there."""
    try:
        if ext == "wav":
            i = data.find(b"fmt ")
            ch, rate, bps = struct.unpack("<HIxxxxxxH", data[i + 10:i + 24])[0:3] if i >= 0 else (0, 0, 0)
            j = data.find(b"data", 12)
            n = struct.unpack("<I", data[j + 4:j + 8])[0] if j >= 0 else 0
            if n in (0, 0xFFFFFFFF):
                n = len(data) - (j + 8)
            if ch and rate and bps:
                return int(1000 * n / (rate * ch * (bps // 8)))
        import tempfile
        with tempfile.NamedTemporaryFile(suffix="." + ext) as tf:   # a file: OGG has no length over a pipe
            tf.write(data)
            tf.flush()
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                tf.name], capture_output=True, timeout=10)
        return int(float(r.stdout.decode().strip()) * 1000)
    except Exception:  # noqa: BLE001 - unknown length: the phone asks its player instead
        return 0


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------
def head():
    try:
        with open(_p("seq")) as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def _emit(ev):
    """Append one event under the lock. -> the event with its seq."""
    with _locked():
        seq = head() + 1
        ev = dict(ev, seq=seq, ts=time.time())
        _write_json(_p("events", f"{seq:012d}.json"), ev)
        with open(_p("seq.tmp"), "w") as f:
            f.write(str(seq))
        os.replace(_p("seq.tmp"), _p("seq"))
    return ev


def _resolve_target(target):
    """None/'' -> the active device; 'all' -> every device; a name -> that one."""
    if target in (None, "", "active"):
        a = active()
        if not a:
            raise BusError(409, "no active device: start nimbridge on a phone, or `nimlab audio use NAME`")
        return a
    if target in ("all", "*"):
        return "*"
    if target not in _registry()["devices"]:
        raise BusError(404, f"no device named {target!r}")
    return target


def publish(data, fmt=None, target=None, source="lab", agent="", text="", pcm_rate=None, deliver=True):
    """Queue a clip for a phone's speaker. -> the play event (dict).
    target None = the active phone, 'all' = every phone, else a device name.
    deliver=False stores the clip without an event (the caller hands the
    phone the clip id itself, as /talk does)."""
    data, ext = normalize(data, fmt, pcm_rate)
    if len(data) > MAX_CLIP_MB * 1024 * 1024:
        raise BusError(413, f"clip over {MAX_CLIP_MB} MB")
    tgt = _resolve_target(target)
    cid = secrets.token_urlsafe(12)
    _write_bytes(_p("clips", f"{cid}.{ext}"), data)
    meta = {"id": cid, "ext": ext, "mime": MIME.get(ext, "application/octet-stream"), "bytes": len(data),
            "duration_ms": duration_ms(data, ext), "target": tgt, "created": time.time()}
    _write_json(_p("clips", f"{cid}.json"), meta)
    prune()
    ev = {"type": "play", "target": tgt, "clip": cid, "ext": ext, "mime": meta["mime"],
          "bytes": len(data), "duration_ms": meta["duration_ms"], "source": str(source)[:40],
          "agent": str(agent or "")[:40], "text": str(text or "")[:200]}
    return _emit(ev) if deliver else dict(ev, seq=None)


def control(kind, target=None, **extra):
    """stop / record_start / record_stop / record_cancel for one phone."""
    if kind not in ("stop", "record_start", "record_stop", "record_cancel"):
        raise BusError(400, f"unknown control {kind!r}")
    return _emit(dict(extra, type=kind, target=_resolve_target(target)))


def events_for(name, since, now=None):
    """Events after seq `since` for this device, live ones only."""
    now = now or time.time()
    h = head()
    if since is None or since < 0 or since > h:
        return [], h          # first poll: start from now, never replay old audio
    out = []
    for seq in range(max(since + 1, h - MAX_EVENTS + 1), h + 1):
        ev = _read_json(_p("events", f"{seq:012d}.json"), None)
        if not ev or ev.get("target") not in (name, "*"):
            continue
        ttl = PLAY_TTL if ev.get("type") == "play" else CONTROL_TTL
        if now - (ev.get("ts") or 0) > ttl:
            continue
        out.append(ev)
    return out, h


def wait_events(name, since, wait=25.0, caps=None, sleep=time.sleep):
    """Long-poll: return as soon as there is something for this device."""
    touch(name, caps)
    end = time.monotonic() + max(0.0, min(float(wait or 0), 30.0))
    while True:
        evs, h = events_for(name, since)
        if evs or since is None or since < 0 or since > h or time.monotonic() >= end:
            return {"events": evs, "head": h, "device": name, "active": active() == name}
        sleep(0.25)


def clip(name, cid):
    """-> (bytes, mime) when this device may have the clip."""
    if not CLIP_RE.match(cid or ""):
        raise BusError(404, "no such clip")
    meta = _read_json(_p("clips", f"{cid}.json"), None)
    if not meta or meta.get("target") not in (name, "*"):
        raise BusError(404, "no such clip")
    try:
        with open(_p("clips", f"{cid}.{meta['ext']}"), "rb") as f:
            return f.read(), meta["mime"]
    except OSError:
        raise BusError(404, "the clip has expired")


def prune(now=None):
    now = now or time.time()
    clips = []
    for fn in os.listdir(_p("clips")):
        if fn.endswith(".json"):
            meta = _read_json(_p("clips", fn), {})
            clips.append((meta.get("created") or 0, fn[:-5], meta.get("ext") or "", meta.get("bytes") or 0))
    clips.sort()
    total = sum(c[3] for c in clips)
    for created, cid, ext, size in clips:
        if now - created > CLIP_TTL or total > MAX_CLIPS_MB * 1024 * 1024:
            for fn in (f"{cid}.json", f"{cid}.{ext}"):
                with contextlib.suppress(OSError):
                    os.remove(_p("clips", fn))
            total -= size
    h = head()
    for fn in os.listdir(_p("events")):
        try:
            if int(fn.split(".")[0]) <= h - MAX_EVENTS:
                os.remove(_p("events", fn))
        except (ValueError, OSError):
            pass
    for fn in os.listdir(_p("uploads")):
        with contextlib.suppress(OSError):
            if now - os.path.getmtime(_p("uploads", fn)) > 900:
                os.remove(_p("uploads", fn))


# ---------------------------------------------------------------------------
# the phone's microphone (remote voice call)
# ---------------------------------------------------------------------------
def _req_ok(name, req):
    if not CLIP_RE.match(req or ""):
        raise BusError(400, "bad request id")
    meta = _read_json(_p("uploads", f"{req}.req"), None)
    if not meta or meta.get("target") != name:
        raise BusError(404, "no such recording request for this device")
    return meta


def ack(name, req, state, error=""):
    """The phone says the mic is on ('recording') or it can't ('error')."""
    _req_ok(name, req)
    _write_json(_p("uploads", f"{req}.ack"), {"state": str(state)[:20], "error": str(error)[:300],
                                              "ts": time.time()})


def upload(name, req, data):
    _req_ok(name, req)
    if not data:
        raise BusError(400, "empty recording")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise BusError(413, f"recording over {MAX_UPLOAD_MB} MB")
    _write_bytes(_p("uploads", f"{req}.audio"), bytes(data))


class RemoteDevice:
    """The voicecall device interface (check, record_start, record_stop,
    play, stop) over the bus: the SSH terminal keeps Enter/q, the active
    phone does the mic and the speaker. Never plays anything on the VPS."""

    def __init__(self, target=None, ack_timeout=10.0, upload_timeout=45.0, sleep=time.sleep):
        self.target = target
        self.ack_timeout = ack_timeout
        self.upload_timeout = upload_timeout
        self._sleep = sleep
        self._req = None
        self._played = False

    def name(self):
        return self.target or active()

    def check(self):
        problems, warnings = [], []
        n = self.name()
        st = device_state(n) if n else None
        if not st:
            problems.append("no phone is active on the audio bus (start nimbridge on the phone, "
                            "or `nimlab audio use NAME`)")
        else:
            if not st["online"]:
                problems.append(f"phone '{n}' isn't connected (start its bridge: nimbridge start)")
            elif not st["mic"]:
                problems.append(f"phone '{n}' doesn't allow the voice call to use its mic "
                                "(on the phone: nimbridge mic on, then nimbridge restart)")
        return not problems, problems, warnings

    def _wait(self, path, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if os.path.exists(path):
                return True
            self._sleep(0.2)
        return False

    def record_start(self, path):
        req = secrets.token_urlsafe(12)
        tgt = _resolve_target(self.target)
        _write_json(_p("uploads", f"{req}.req"), {"target": tgt, "ts": time.time()})
        self._req = req
        control("record_start", tgt, req=req, max_sec=120)
        if not self._wait(_p("uploads", f"{req}.ack"), self.ack_timeout):
            self._req = None
            control("record_cancel", tgt, req=req)
            raise RuntimeError(f"phone '{tgt}' didn't answer: is nimbridge running there?")
        a = _read_json(_p("uploads", f"{req}.ack"), {})
        if a.get("state") != "recording":
            self._req = None
            raise RuntimeError(f"phone '{tgt}' couldn't record: {a.get('error') or a.get('state')}")

    def record_stop(self, path, settle=2.0):
        req, self._req = self._req, None
        if not req:
            return False
        tgt = _resolve_target(self.target)
        control("record_stop", tgt, req=req)
        up = _p("uploads", f"{req}.audio")
        if not self._wait(up, self.upload_timeout):
            return False
        os.replace(up, path)
        for ext in ("req", "ack"):
            with contextlib.suppress(OSError):
                os.remove(_p("uploads", f"{req}.{ext}"))
        return os.path.getsize(path) > 0

    def play(self, path):
        with open(path, "rb") as f:
            data = f.read()
        publish(data, fmt=os.path.splitext(path)[1].lstrip("."), target=self.target, source="voice call")
        self._played = True

    def stop(self):
        if self._played:
            with contextlib.suppress(BusError):
                control("stop", self.target)
            self._played = False


def remote_ready():
    """True when an active phone is online: the SSH voice call can use it."""
    st = device_state(active()) if active() else None
    return bool(st and st["online"])


# ---------------------------------------------------------------------------
# CLI: nimlab audio ...
# ---------------------------------------------------------------------------
def _ago(ts):
    if not ts:
        return "never"
    s = int(time.time() - ts)
    return f"{s}s ago" if s < 120 else (f"{s // 60} min ago" if s < 7200 else f"{s // 3600} h ago")


def cmd_audio(args):
    act = getattr(args, "action", None) or "devices"
    try:
        if act == "devices":
            ds = devices()
            if not ds:
                print("No phones yet. Add one: nimlab audio add NAME")
            for d in ds:
                print(f"{'*' if d['active'] else ' '} {d['name']:<20} {'online' if d['online'] else 'offline':<8} "
                      f"mic {'on ' if d['mic'] else 'off'}  last seen {_ago(d['last_seen'])}"
                      + (f"  ({d['label']})" if d['label'] else ""))
            if ds:
                print("* = active: audio and mic requests go to that phone only.")
        elif act == "add" and getattr(args, "termux", False):
            return _add_termux(args)
        elif act == "add":
            tok = add_device(args.name, getattr(args, "label", "") or "")
            print(f"Phone '{args.name.lower()}' added. Its token (shown once, paste it into `nimbridge setup`):")
            print(tok)
            print("Or get a ready-to-paste Termux block instead: nimlab audio setup")
        elif act == "setup":
            from . import audiosetup, wizard
            try:
                audiosetup.flow(wizard.IO())
            except (KeyboardInterrupt, EOFError):
                print()
        elif act == "remove":
            print("Removed." if remove_device(args.name) else "No such phone.")
        elif act == "use":
            set_active(args.name.lower())
            print(f"'{args.name.lower()}' is now the active phone.")
        elif act == "release":
            set_active(None)
            print("No phone is active now; audio is not relayed until one is.")
        elif act == "say":
            text = " ".join(args.text).strip() or "Nim Lab audio bus test."
            out = _local_say(text, args.target)
            print(f"Spoken on {out.get('target')} ({out.get('ext')}, {out.get('bytes')} bytes, "
                  f"{(out.get('duration_ms') or 0) / 1000:.1f}s).")
        elif act == "tone":
            ev = publish(test_tone(), target=args.target, source="cli", text="test tone")
            print(f"Test tone sent to {ev['target']}.")
    except BusError as e:
        print(f"Audio bus: {e.message}")
        return 1
    return 0


def _add_termux(args):
    """`audio add NAME --termux`: register (or re-key) the phone and print only
    its Termux block on stdout, for scripting; notes go to stderr."""
    import sys
    from . import audiosetup
    try:
        name = audiosetup.check_name(args.name)
        url = audiosetup.clean_url(args.url or audiosetup.default_url())
        src = audiosetup.client_source()
    except (audiosetup.SetupError, OSError) as e:
        print(f"Audio bus: {e}", file=sys.stderr)
        return 1
    existed = name in {d["name"] for d in devices()}
    tok = add_device(name, getattr(args, "label", "") or "")
    sys.stdout.write(audiosetup.termux_block(name, tok, url, args.mic, src=src))
    sys.stdout.flush()
    print(f"Phone '{name}' {'has a new key' if existed else 'added'}; paste the block above into Termux on "
          f"that phone. It holds the phone's key.", file=sys.stderr)
    return 0


def _local_say(text, target=None):
    """Ask the running server (it holds the TTS role) to speak on a phone."""
    import urllib.error
    import urllib.request
    from . import server as S
    s = S.load_settings()
    url = f"http://127.0.0.1:{int(s.get('port') or 8765)}/v1/audio/bus/say"
    req = urllib.request.Request(url, data=json.dumps({"text": text, "target": target}).encode(),
                                 headers={"Authorization": "Bearer " + (s.get("api_key") or ""),
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", {}).get("message")
        except Exception:  # noqa: BLE001
            msg = None
        raise BusError(e.code, msg or f"server answered {e.code}")
    except OSError as e:
        raise BusError(503, f"the Nim Lab server isn't reachable on this machine ({e})")


def test_tone(sec=0.8, rate=16000, hz=660):
    import math
    n = int(sec * rate)
    pcm = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * hz * i / rate) *
                                          min(1.0, i / 800, (n - i) / 800))) for i in range(n))
    return wav_from_pcm(pcm, rate)


def add_parser(sub):
    s = sub.add_parser("audio", help="audio bus: phones that play Nim Lab audio and lend their mic (nimbridge)")
    a = s.add_subparsers(dest="action")
    a.add_parser("devices", help="list phones (* = active)")
    p = a.add_parser("add", help="register a phone and print its token once")
    p.add_argument("name")
    p.add_argument("--label", default="")
    p.add_argument("--termux", action="store_true",
                   help="print only a ready-to-paste Termux block (installs and configures nimbridge)")
    p.add_argument("--mic", choices=["on", "off"], default="off", help="with --termux: lend the mic to calls")
    p.add_argument("--url", default=None, help="with --termux: server address the phone connects to")
    a.add_parser("setup", help="register a phone step by step and print its Termux block")
    p = a.add_parser("remove", help="forget a phone (its token stops working)")
    p.add_argument("name")
    p = a.add_parser("use", help="make this phone the active one")
    p.add_argument("name")
    a.add_parser("release", help="no active phone")
    p = a.add_parser("tone", help="play a short test tone on the active phone")
    p.add_argument("--target", default=None, help="a phone name, or 'all'")
    p = a.add_parser("say", help="speak text with the TTS role on the active phone")
    p.add_argument("text", nargs="*")
    p.add_argument("--target", default=None)
    s.set_defaults(fn=cmd_audio)
