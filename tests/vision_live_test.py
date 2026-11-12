"""Real-inference tests for Lumenis vision (calls NVIDIA; no paid services).

browser  - plays a video in real time and POSTs frames to the running reactor exactly like /vision does
           (JPEG + X-Vision-Session + X-Captured-At), then reads the observations back.
stream   - serves the video as a live MPEG-TS stream with ffmpeg and lets vision.py's own ffmpeg puller
           read it in-process (local streams allowed for this test only).

Both are stand-ins: the video is Brawlhalla's own promo clip from brawlhalla.com, not a real match feed
from Steam or Discord, and it has no in-match HUD.

Run: .venv/bin/python tests/vision_live_test.py browser|stream <video> [seconds]
"""
import asyncio
import json
import os
import statistics
import subprocess
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
REACTOR = os.getenv("REACTOR", "http://127.0.0.1:8000")


def ffmpeg():
    import imageio_ffmpeg
    import shutil
    return shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()


def summarize(obs, label):
    e2e = [o["end_to_end_s"] for o in obs]
    inf = [o["inference_s"] for o in obs]
    out = {
        "test": label, "observations": len(obs),
        "end_to_end_s": {"median": round(statistics.median(e2e), 2), "min": min(e2e), "max": max(e2e)} if e2e else None,
        "inference_s": {"median": round(statistics.median(inf), 2), "min": min(inf), "max": max(inf)} if inf else None,
        "models": sorted({o["model"] for o in obs}),
        "scenes": {s: sum(1 for o in obs if o["scene"] == s) for s in {o["scene"] for o in obs}},
        "game_named": sum(1 for o in obs if (o.get("game") or "").lower().startswith("brawlhalla")),
        "confidence": {c: sum(1 for o in obs if o["confidence"] == c) for c in {o["confidence"] for o in obs}},
        "with_callout": sum(1 for o in obs if o.get("callout")),
        "samples": [{k: o.get(k) for k in ("summary", "callout", "confidence", "cannot_tell", "end_to_end_s")}
                    for o in obs[:4]],
    }
    return out


def browser(video, seconds):
    c = httpx.Client(base_url=REACTOR, timeout=30)
    s = c.post("/api/vision/session/start", json={"source": "browser", "label": "live test (promo clip)",
                                                  "game": "Brawlhalla", "interval_s": 3, "max_minutes": 5}).json()
    sid = s["session"]["id"]
    since = max([o["id"] for o in c.get("/api/vision/latest").json()["observations"]] or [0])
    # real-time playback, one JPEG per second on stdout (like a canvas grab of a playing <video>)
    p = subprocess.Popen([ffmpeg(), "-nostdin", "-loglevel", "error", "-re", "-stream_loop", "-1", "-i", video,
                          "-vf", "fps=1,scale=1280:-2", "-q:v", "4", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"],
                         stdout=subprocess.PIPE)
    buf, sent, last_send, t0, upload = b"", 0, 0.0, time.time(), []
    while time.time() - t0 < seconds:
        buf += p.stdout.read(32768)
        while True:
            a = buf.find(b"\xff\xd8")
            b = buf.find(b"\xff\xd9", a + 2) if a >= 0 else -1
            if a < 0 or b < 0:
                break
            frame, buf = buf[a:b + 2], buf[b + 2:]
            if time.time() - last_send >= 3:          # the page's timer: one frame per interval
                ts = time.time()
                r = c.post("/api/vision/frame", content=frame, headers={
                    "Content-Type": "image/jpeg", "X-Vision-Session": sid, "X-Captured-At": str(int(ts * 1000))})
                upload.append(time.time() - ts)
                if r.status_code != 200:
                    print("frame refused:", r.status_code, r.text[:200])
                sent += 1
                last_send = ts
    p.kill()
    time.sleep(8)
    st = c.get("/api/vision/status").json()
    obs = [o for o in c.get(f"/api/vision/latest?since={since}&limit=100").json()["observations"] if o["session"] == sid]
    c.post("/api/vision/session/stop")
    out = summarize(obs, "browser-path (HTTP frame upload to running reactor)")
    out.update({"frames_sent": sent, "upload_s_median": round(statistics.median(upload), 3) if upload else None,
                "session": {k: st["session"][k] for k in ("frames_in", "frames_dropped", "frames_rejected",
                                                            "analyzed", "errors", "last_error")}})
    return out


async def stream(video, seconds):
    os.environ["LUMENIS_VISION_ALLOW_LOCAL"] = "1"
    from lumenis_reactor_core import vision as v
    v.ALLOW_LOCAL_STREAMS = True
    v.DATA_DIR = v.DATA_DIR.parent / "vision_test_tmp"
    port = 18093
    srv = subprocess.Popen([ffmpeg(), "-nostdin", "-loglevel", "error", "-re", "-stream_loop", "-1", "-i", video,
                            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency", "-g", "30", "-an",
                            "-f", "mpegts", "-listen", "1", f"http://127.0.0.1:{port}/live.ts"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=open("/tmp/vision_stream_srv.log", "w"))
    await asyncio.sleep(1.5)
    s = await v.start_session("stream", label="live test stream", game="Brawlhalla", interval_s=3, max_minutes=5,
                              url=f"http://127.0.0.1:{port}/live.ts")
    await asyncio.sleep(seconds)
    pub = s.public()
    await v.stop_session("test done")
    srv.kill()
    obs = [o for o in v.latest(limit=100) if o["session"] == s.id]
    out = summarize(obs, "stream-path (vision.py ffmpeg puller on a live MPEG-TS stream)")
    out["session"] = {k: pub[k] for k in ("frames_in", "frames_dropped", "frames_rejected", "analyzed", "errors",
                                          "last_error")}
    import shutil
    shutil.rmtree(v.DATA_DIR, ignore_errors=True)
    return out


if __name__ == "__main__":
    mode, video = sys.argv[1], sys.argv[2]
    secs = int(sys.argv[3]) if len(sys.argv) > 3 else 45
    res = browser(video, secs) if mode == "browser" else asyncio.run(stream(video, secs))
    print(json.dumps(res, indent=1))
    path = os.path.join(os.path.dirname(__file__), "vision_results.json")
    try:
        allres = json.load(open(path))
    except Exception:
        allres = {}
    allres[mode] = {"run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **res}
    json.dump(allres, open(path, "w"), indent=1)
