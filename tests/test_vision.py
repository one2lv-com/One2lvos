"""Unit tests for lumenis_reactor_core/vision.py. No network: the vision model is replaced by a stub.

Run: .venv/bin/python tests/test_vision.py
"""
import asyncio
import io
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NVIDIA_API_KEY", "test-key-not-real")
os.environ["LUMENIS_VISION_MIN_INTERVAL_S"] = "0.2"
os.environ["LUMENIS_VISION_MAX_PER_MIN"] = "5"
os.environ["LUMENIS_VISION_IDLE_S"] = "1"

from PIL import Image  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from lumenis_reactor_core import vision as v  # noqa: E402

v.DATA_DIR = v.DATA_DIR.parent / "vision_test_tmp"
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))


def img(fmt="JPEG", size=(640, 360)):
    b = io.BytesIO()
    Image.new("RGB", size, (30, 90, 160)).save(b, fmt)
    return b.getvalue()


calls = []


async def fake_vlm(client, jpeg, game, model):
    calls.append((time.time(), len(jpeg), model))
    await asyncio.sleep(0.3)
    return ({"scene": "gameplay", "game": "Brawlhalla", "summary": "stub", "players": [{"pos": "left", "x": "red"}],
             "hud": {"timer": "2:31"}, "events": ["bomb"], "callout": "bomb left", "confidence": "SUPER",
             "cannot_tell": ["hitboxes"]}, {"total_tokens": 10})


def test_frames():
    j, w, h = v.normalize_frame(img())
    check("jpeg accepted and re-encoded", j[:3] == b"\xff\xd8\xff" and (w, h) == (640, 360))
    j, w, h = v.normalize_frame(img("PNG", (2560, 1440)))
    check("large png downscaled to 1280", max(w, h) == 1280)
    for name, raw in [("empty", b""), ("text", b"hello world" * 10), ("svg", b"<svg></svg>"),
                      ("truncated jpeg", img()[:200]), ("tiny", img(size=(8, 8))),
                      ("oversize", b"\xff\xd8\xff" + b"0" * (v.MAX_FRAME_BYTES + 1))]:
        try:
            v.normalize_frame(raw)
            check(f"reject {name}", False, "accepted")
        except ValueError:
            check(f"reject {name}", True)
    poly = img() + b"<script>alert(1)</script>"
    j, _, _ = v.normalize_frame(poly)
    check("trailing payload stripped by re-encode", b"<script>" not in j)


def test_urls():
    for bad in ["file:///etc/passwd", "concat:a|b", "-i x", "rtsp://127.0.0.1/live", "http://169.254.169.254/x",
                "http://localhost:8000/x", "http://10.0.0.5/s", "gopher://x", "", "http:// spaced.com",
                "https://no-such-host.invalid/x.m3u8"]:
        try:
            v.validate_stream_url(bad)
            check(f"block url {bad!r}", False, "allowed")
        except ValueError:
            check(f"block url {bad!r}", True)
    check("allow public https", v.validate_stream_url("https://example.com/live.m3u8"))
    v.ALLOW_LOCAL_STREAMS = True
    check("allow local only when opted in", v.validate_stream_url("rtsp://127.0.0.1:8554/live"))
    try:
        v.validate_stream_url("http://169.254.169.254/latest")
        check("metadata address blocked even with opt-in", False)
    except ValueError:
        check("metadata address blocked even with opt-in", True)
    v.ALLOW_LOCAL_STREAMS = False


async def test_pipeline():
    v._call_vlm = fake_vlm
    check("prompt block says OFF with no session", "Live vision: OFF" in v.prompt_block())
    try:
        await v.submit_frame("nope", img(), None)
        check("frame without session refused", False)
    except HTTPException as e:
        check("frame without session refused", e.status_code == 409)

    s = await v.start_session("browser", label="<b>Brawl</b>", game="Brawlhalla; rm -rf", interval_s=0.01)
    check("interval clamped to floor", s.interval_s == v.MIN_INTERVAL_S, s.interval_s)
    check("label/game sanitised", "<" not in s.label and ";" not in (s.game or ""), (s.label, s.game))
    try:
        await v.submit_frame("wrong-id", img(), None)
        check("wrong session id refused", False)
    except HTTPException as e:
        check("wrong session id refused", e.status_code == 409)
    try:
        await v.submit_frame(s.id, b"junk", None)
        check("junk frame -> 400", False)
    except HTTPException as e:
        check("junk frame -> 400", e.status_code == 400 and s.frames_rejected == 1)

    # backpressure: 10 frames in a burst while one model call is in flight -> only newest survives
    calls.clear()
    for i in range(10):
        await v.submit_frame(s.id, img(size=(640 + i * 8, 360)), time.time() * 1000)
    await asyncio.sleep(1.2)
    check("burst of 10 frames -> at most 2 model calls", 1 <= len(calls) <= 2, len(calls))
    check("stale frames counted as dropped", s.frames_dropped >= 8, s.frames_dropped)
    obs = v.latest()
    check("observation published", len(obs) >= 1)
    o = obs[-1]
    check("observation marked unverified visual", o["kind"] == "visual_observation" and o["verified"] is False)
    check("confidence normalised", o["confidence"] == "low")
    check("dict player entries flattened", o["players"] == ["left: red"], o["players"])
    check("timestamps present", all(o.get(k) for k in ("captured_at", "received_at", "analyzed_at")))
    check("freshness reported", isinstance(o["fresh_s"], float) and o["end_to_end_s"] >= 0)
    pb = v.prompt_block()
    check("prompt block labels readings as not facts", "NOT verified facts" in pb and "hitboxes" in pb)

    # client clock in the future / far past is clamped to server time
    await v.submit_frame(s.id, img(), (time.time() + 3600) * 1000)
    check("future capture time clamped", v._S.pending is None or v._S.pending.captured_ts <= time.time() + 0.1)

    # SSE subscriber gets new observations; slow subscriber never blocks
    sub = v.subscribe()
    nxt = asyncio.ensure_future(sub.__anext__())
    v._S.call_times.clear()
    await v.submit_frame(s.id, img(), None)
    got = await asyncio.wait_for(nxt, timeout=5)
    check("subscriber receives observation", got["kind"] == "visual_observation")
    await sub.aclose()

    # per-minute cap: 5 per minute in this test config
    calls.clear()
    v._S.call_times.clear()
    t0 = time.time()
    for _ in range(8):
        await v.submit_frame(s.id, img(), None)
        await asyncio.sleep(0.6)
    check("per-minute cap holds", len(calls) <= 5, len(calls))

    # idle timeout (1 s in test) ends a browser session
    await asyncio.sleep(8)    # even while parked by the per-minute cap, idle stop is seen within ~1 s
    check("idle browser session auto-stops", s.ended_ts is not None, s.end_reason)
    check("prompt block OFF after stop", "Live vision: OFF" in v.prompt_block())
    try:
        await v.submit_frame(s.id, img(), None)
        check("frames refused after stop", False)
    except HTTPException:
        check("frames refused after stop", True)

    s2 = await v.start_session("browser")
    s3 = await v.start_session("browser")
    check("new session replaces old", s2.ended_ts is not None and s3.ended_ts is None)
    await v.stop_session()
    try:
        await v.start_session("stream", url="file:///etc/passwd")
        check("stream session rejects file url", False)
    except HTTPException as e:
        check("stream session rejects file url", e.status_code == 400)


if __name__ == "__main__":
    test_frames()
    test_urls()
    asyncio.run(test_pipeline())
    import shutil
    shutil.rmtree(v.DATA_DIR, ignore_errors=True)
    ok = sum(1 for _, p in RESULTS if p)
    print(f"\n{ok}/{len(RESULTS)} passed")
    sys.exit(0 if ok == len(RESULTS) else 1)
