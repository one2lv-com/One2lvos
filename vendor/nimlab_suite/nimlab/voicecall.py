"""Live voice call test in the terminal (Termux on Android).

Press Enter to start talking and Enter again to send. Each turn goes
microphone -> ASR ability -> the persona (soul.md voice, memory, tools) ->
TTS ability (the cloned voice when one is set) -> the phone speaker, and
the transcript and the time each step took are printed. Talking again
while a reply plays stops it.

Recording and playback use Termux:API: the Termux:API Android app plus
`pkg install termux-api`. Recordings are AAC (.m4a); NVIDIA ASR wants WAV,
so ffmpeg (`pkg install ffmpeg`) converts them.
"""

import os
import shutil
import subprocess
import time

from . import perf, colors as C
from . import config
from . import roles as R
from . import unified

INSTALL_HELP = """The voice call needs Termux:API:
  1. Install the Termux:API app (F-Droid or GitHub, the same source as your Termux app;
     the Play Store build doesn't match the F-Droid Termux).
  2. In Termux:  pkg install termux-api
  3. The first recording asks Android for microphone permission: allow it
     (or Settings > Apps > Termux:API > Permissions > Microphone)."""


class Termux:
    """Microphone and speaker through Termux:API. Swap in a fake for tests."""

    def __init__(self, run=subprocess.run, popen=subprocess.Popen, which=shutil.which):
        self._run = run
        self._popen = popen
        self._which = which
        self._player = None

    def check(self):
        """-> (ok, problems, warnings)."""
        problems, warnings = [], []
        if not self._which("termux-microphone-record"):
            problems.append("termux-microphone-record not found")
        if not (self._which("termux-media-player") or self._which("play-audio")):
            problems.append("no player found (termux-media-player from termux-api, or pkg install play-audio)")
        if not self._which("ffmpeg"):
            warnings.append("ffmpeg isn't installed, so recordings go to ASR as .m4a, which NVIDIA ASR may refuse "
                            "(pkg install ffmpeg)")
        return not problems, problems, warnings

    def record_start(self, path):
        r = self._run(["termux-microphone-record", "-f", path, "-e", "aac", "-r", "16000", "-c", "1", "-l", "0"],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        msg = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace").strip()
        if r.returncode != 0 or "error" in msg.lower() or "denied" in msg.lower():
            raise RuntimeError(msg or f"termux-microphone-record exited {r.returncode}")

    def record_stop(self, path, settle=2.0):
        self._run(["termux-microphone-record", "-q"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        # the file is finished a moment after -q returns: wait for its size to settle
        end, last = time.monotonic() + settle, -1
        while time.monotonic() < end:
            size = os.path.getsize(path) if os.path.exists(path) else -1
            if size > 0 and size == last:
                break
            last = size
            time.sleep(0.2)
        return os.path.exists(path) and os.path.getsize(path) > 0

    def play(self, path):
        self.stop()
        if self._which("termux-media-player"):
            self._run(["termux-media-player", "play", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                      timeout=15)
            self._player = "termux"
        else:
            self._player = self._popen(["play-audio", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        if self._player == "termux":
            self._run(["termux-media-player", "stop"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        elif self._player is not None:
            try:
                self._player.terminate()
            except OSError:
                pass
        self._player = None


def step_times(trace):
    """ASR, persona and TTS milliseconds from a Mind trace."""
    out = {"asr": 0, "abilities": 0, "persona": 0, "tts": 0}
    for t in trace or []:
        r = t.get("role")
        if r == "asr":
            out["asr"] += t.get("ms") or 0
        elif r == "tts":
            out["tts"] += t.get("ms") or 0
        elif r == "persona" and t.get("why") == "the reply":
            out["persona"] += t.get("ms") or 0
        else:
            out["abilities"] += t.get("ms") or 0
    return out


def ability_times(trace):
    """[(role, label, ms, ok)] for every step that isn't ASR, the persona's
    reply or TTS, in order, merged per role: so a slow or failed step shows
    by name (e.g. 'Reasoning 61.0s FAILED'), not as 'other abilities'."""
    seen = {}
    for t in trace or []:
        r = t.get("role")
        if r in ("asr", "tts") or (r == "persona" and t.get("why") == "the reply"):
            continue
        cur = seen.setdefault(r, [r, t.get("label") or r, 0, True])
        cur[2] += t.get("ms") or 0
        cur[3] = cur[3] and bool(t.get("ok", True))
    return [tuple(v) for v in seen.values()]


def latency_line(trace, total_ms):
    st = step_times(trace)
    parts = [("asr", "ASR", st["asr"])]
    for role, label, ms, ok in ability_times(trace):
        parts.append((role, label + ("" if ok else " FAILED"), ms))
    parts += [("persona", "persona", st["persona"]), ("tts", "TTS", st["tts"]), (None, "total", total_ms)]
    if not C.enabled():
        return "[" + " | ".join(f"{name} {ms / 1000:.1f}s" for _, name, ms in parts) + "]"
    bits = [(C.role(k, name, bold_=False) if k else C.bold(name)) + " " + C.latency(f"{ms / 1000:.1f}s")
            for k, name, ms in parts]
    return C.dim("[") + C.dim(" | ").join(bits) + C.dim("]")


STAGE_LABELS = {"record": "record", "convert": "convert", "asr": "ASR", "intent_router": "router",
                "memory_recall": "recall", "persona": "persona", "reasoning": "reasoning", "coding": "coding",
                "tts": "TTS", "play": "play", "memory_store": "store"}
NESTED = ("embedding", "reranker")    # run inside recall/store: shown as part of them


def voice_settings(ent):
    vs = dict(config.DEFAULT_CLUSTER.get("voice_settings", {}))
    vs.update((getattr(ent, "cluster", {}) or {}).get("voice_settings", {}) or {})
    return vs


def merged_stages(stages):
    """[(stage, label, ms, ok)] in first-seen order, one row per stage."""
    names = {r["stage"] for r in stages or []}
    hide = set(NESTED) if names & {"memory_recall", "memory_store"} else set()
    seen = {}
    for r in stages or []:
        k = r["stage"]
        if k in hide:
            continue
        label = STAGE_LABELS.get(k) or (R.label(k) if k in R.BY_KEY else k)
        cur = seen.setdefault(k, [k, label, 0, True])
        cur[2] += int(r.get("ms") or 0)
        cur[3] = cur[3] and bool(r.get("ok", True))
    return [tuple(v) for v in seen.values()]


def stage_line(stages, total_ms, skipped=()):
    """'[record 0.4s | convert 0.2s | ASR 1.1s | router skipped | recall 0.3s | persona 2.0s | TTS 0.9s |
    play 0.1s | store 0.5s | total 5.5s]': where each voice turn's time went."""
    rows = [(k, label + ("" if ok else " FAILED"), f"{ms / 1000:.1f}s") for k, label, ms, ok in merged_stages(stages)]
    for k in skipped:
        rows.append((k, STAGE_LABELS.get(k, k), "skipped"))
    order = list(STAGE_LABELS)
    rows.sort(key=lambda r: order.index(r[0]) if r[0] in order else order.index("persona"))
    rows.append((None, "total", f"{total_ms / 1000:.1f}s"))
    if not C.enabled():
        return "[" + " | ".join(f"{name} {v}" for _, name, v in rows) + "]"
    bits = [(C.role(k, name, bold_=False) if k in R.BY_KEY else C.bold(name) if not k else name) + " " +
            C.latency(v) for k, name, v in rows]
    return C.dim("[") + C.dim(" | ").join(bits) + C.dim("]")


OFF_TERMUX = ("The terminal voice call needs Termux (termux-microphone-record and termux-media-player), "
              "so it is off on this machine. Telegram voice notes still work.")


def on_termux(env=None):
    e = os.environ if env is None else env
    return bool(e.get("TERMUX_VERSION")) or "com.termux" in e.get("PREFIX", "")


def run_call(ent, input_fn=input, out=print, device=None, max_turns=None, name=None):
    """The call loop. Returns the number of turns. device is a Termux-like
    object (check, record_start, record_stop, play, stop)."""
    if device is None and not on_termux():
        # 3.8.5: on the VPS the active phone (nimbridge) lends its mic and speaker
        from . import audiobus
        if audiobus.active():
            device = audiobus.RemoteDevice()
            out(C.dim(f"Using phone '{audiobus.active()}' for the mic and speaker (audio bus)."))
        else:
            out(C.warn(OFF_TERMUX))
            out(C.dim("Or connect a phone: nimlab audio add NAME here, then nimbridge setup on the phone."))
            return 0
    dev = device or Termux()
    ok, problems, warnings = dev.check()
    if not ok:
        out(C.err("Can't start the call: ") + C.warn("; ".join(problems) + "."))
        out(INSTALL_HELP)
        return 0
    for w in warnings:
        out(C.warn(f"Note: {w}."))
    missing = [k for k in ("persona", "asr", "tts") if not ent.is_set(k)]
    if "persona" in missing or "asr" in missing:
        out("The call needs the " + " and ".join(R.label(k) for k in missing if k != "tts") +
            " role(s) set (main menu 2). TTS is needed to hear replies.")
        return 0
    if "tts" in missing:
        out(C.warn("Note: the Neural TTS role isn't set, so replies are shown, not spoken."))
    clone = (ent.spec("tts") or {}).get("voice_clone") if ent.is_set("tts") else None
    who = name or unified.soul_name(ent.soul) or "Persona"
    out(C.section("Voice call with ") + C.entity(who) + (C.role("tts", f" (cloned voice: {os.path.basename(clone.get('path', ''))})", bold_=False)
                                    if isinstance(clone, dict) and clone.get("path") else ""))
    out("Enter: start talking, Enter again: send.  q + Enter: end the call.")
    mind = unified.Mind(ent)
    vs = voice_settings(ent)
    history, turns = [], 0
    rec_dir = config.output_path("call")
    os.makedirs(rec_dir, exist_ok=True)
    try:
        while max_turns is None or turns < max_turns:
            try:
                c = input_fn(C.prompt("\n[Enter] talk  [q] end > ", "you", "bold")).strip().lower()
            except EOFError:
                break
            if c in ("q", "quit", "exit", "/exit", "end"):
                break
            dev.stop()   # barge-in: talking cuts the reply off
            path = os.path.join(rec_dir, f"turn_{int(time.time() * 1000)}.m4a")
            try:
                dev.record_start(path)
            except (OSError, RuntimeError, subprocess.SubprocessError) as e:
                out(C.err(f"Recording failed: {e}"))
                out("Check that Termux:API has microphone permission.")
                continue
            t_rec = time.monotonic()
            try:
                input_fn(C.prompt("  recording... [Enter] send ", "err", "bold"))
            except EOFError:
                pass
            spoke = time.monotonic() - t_rec
            with perf.track("voice call turn") as tr, perf.time_cap(vs.get("turn_timeout_sec")):
                res = _one_turn(ent, mind, dev, path, spoke, history, rec_dir, who, vs, tr, out)
            if res is not None:
                turns += 1
    finally:
        dev.stop()
    out(C.ok("Call ended") + C.dim(f" after {turns} turn(s)."))
    return turns


def _one_turn(ent, mind, dev, path, spoke, history, rec_dir, who, vs, tr, out):
    """Send one recording, show and play the reply, then save the turn to
    memory. Every step is timed on tr; the line under the reply says where
    the time went, and a slow or failed turn goes to the bug log with it.
    -> the Mind result, or None when nothing was recorded."""
    from . import environment as ENV
    from . import interrupts
    interrupts.mark(interrupts.USER, "voice call")   # v3.8.4: SeVin talking ends a running Free time
    with perf.stage("record", target="termux-microphone-record") as st:
        got = dev.record_stop(path)
        st["ok"] = bool(got)
    if not got:
        out(C.warn("  (nothing was recorded)"))
        return None
    out(C.dim(f"  ({spoke:.1f}s recorded, thinking...)"))
    part = unified.Part("audio", path=path, mime="audio/mp4", name="your voice", temp=True)
    with ENV.channel("voice"):
        res = mind.run("", [part], history, want_audio=ent.is_set("tts"), defer_store=True)
    if res.get("transcript"):
        out(f"{C.you('YOU  >')} {C.you_text(res['transcript'])}")
    skipped = ["intent_router"] if res.get("via") in ("voice", "fast") else []
    if not res["ok"]:
        out(f"{C.err('[error]')} {C.paint(res.get('error') or res.get('blocked'), 'err')}")
        _report(tr, res, vs, skipped, out, failed=True)
        return res
    out(f"{C.entity(who.upper() + ' >')} {C.reply(res['text'])}")
    if res.get("route_reason") and os.environ.get("NIMLAB_SHOW_ROUTE", "1") != "0":
        out(C.dim(f"  route: {res.get('text_route')} via {res.get('via')}: {res['route_reason']}"))
    history.append({"role": "user", "content": res.get("transcript") or "(voice)"})
    history.append({"role": "assistant", "content": res["reply"]})
    audio = res.get("audio") or {}
    apath = audio.get("path")
    if not apath and audio.get("data"):
        apath = os.path.join(rec_dir, f"reply_{int(time.time() * 1000)}.wav")
        with open(apath, "wb") as f:
            f.write(audio["data"])
    if apath:
        with perf.stage("play") as st:
            try:
                dev.play(apath)
            except (OSError, subprocess.SubprocessError) as e:
                st["ok"] = False
                out(C.warn(f"  (couldn't play the reply: {e}; saved at ") + C.path(apath) + C.warn(")"))
    elif res.get("tts_error"):
        out(C.warn(f"  (the reply couldn't be spoken: {str(res['tts_error'])[:160]}; it is shown as text above)"))
    finish = res.get("finish")
    if callable(finish):
        try:
            finish()              # memory store, after the reply is out
        except Exception as e:  # noqa: BLE001 - a failed save never ends the call
            out(C.warn(f"  (memory store failed: {str(e)[:120]})"))
    _report(tr, res, vs, skipped, out)
    return res


def _report(tr, res, vs, skipped, out, failed=False):
    total = tr.elapsed_ms()
    if vs.get("show_stages", True):
        out("  " + stage_line(tr.stages, total, skipped))
    slow = float(vs.get("slow_turn_sec") or 0)
    if failed or (slow and total >= slow * 1000):
        try:
            from . import bugs
            name, ms = tr.slowest()
            bid = bugs.record("voice_failed" if failed else "voice_slow",
                              (res.get("error") or res.get("blocked") or "voice turn failed") if failed else
                              f"voice turn took {total / 1000:.1f}s (slowest: {name} {ms / 1000:.1f}s)",
                              where="voicecall.turn", trace=res.get("trace"), stages=tr.summary())
            if bid:
                out(C.dim(f"  (logged as {bid}: nimlab bugs show {bid})"))
        except Exception:  # noqa: BLE001 - logging never breaks the call
            pass
