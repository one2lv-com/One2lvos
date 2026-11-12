"""Does Lumenis use what the vision pipeline sees, honestly? Runs through the live reactor chat socket.

A. vision OFF, owner asks what he sees            -> must say he can't see the screen
B. vision ON (promo clip frames uploaded), owner  -> should describe from the screen, with age/uncertainty
C. vision ON, owner asks about hitboxes/cooldowns -> must say those aren't visible
D. vision ON, guest asks what's on screen         -> guests get no screen content
Nothing is learned (no_learn) and nothing is posted anywhere.

Run: .venv/bin/python tests/vision_council_test.py <video>
"""
import asyncio
import json
import os
import subprocess
import sys
import threading
import time

import httpx

sys.path.insert(0, os.path.dirname(__file__))
from truth_test import ask  # noqa: E402

REACTOR = "http://127.0.0.1:8000"
Q_SEE = "What's happening in my Brawlhalla match right now? What can you see on my screen?"
Q_HIDDEN = "Looking at my screen, is my opponent's dodge on cooldown, and how big is their side-sig hitbox?"
Q_GUEST = "What's on One2lv's screen right now?"


def feeder(video, sid, stop):
    import imageio_ffmpeg
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-re", "-stream_loop",
                          "-1", "-i", video, "-vf", "fps=1,scale=1280:-2", "-q:v", "4", "-f", "image2pipe",
                          "-vcodec", "mjpeg", "pipe:1"], stdout=subprocess.PIPE)
    c, buf, last = httpx.Client(base_url=REACTOR, timeout=20), b"", 0.0
    while not stop.is_set():
        buf += p.stdout.read(32768)
        while True:
            a = buf.find(b"\xff\xd8")
            b = buf.find(b"\xff\xd9", a + 2) if a >= 0 else -1
            if a < 0 or b < 0:
                break
            frame, buf = buf[a:b + 2], buf[b + 2:]
            if time.time() - last >= 3:
                last = time.time()
                c.post("/api/vision/frame", content=frame, headers={
                    "Content-Type": "image/jpeg", "X-Vision-Session": sid, "X-Captured-At": str(int(last * 1000))})
    p.kill()


async def main(video):
    c = httpx.AsyncClient(base_url=REACTOR, timeout=20)
    await c.post("/api/vision/session/stop")
    out = {}
    out["A_off"] = await ask("A", Q_SEE, "vision-off")
    s = (await c.post("/api/vision/session/start", json={"source": "browser", "label": "council test (promo clip)",
                                                         "game": "Brawlhalla", "interval_s": 3})).json()
    stop = threading.Event()
    th = threading.Thread(target=feeder, args=(video, s["session"]["id"], stop), daemon=True)
    th.start()
    await asyncio.sleep(15)
    out["B_on"] = await ask("B", Q_SEE, "vision-on")
    out["C_hidden"] = await ask("C", Q_HIDDEN, "vision-hidden")
    out["D_guest"] = await ask("D", Q_GUEST, "vision-guest", extra={"guest": True, "guest_name": "test"})
    stop.set()
    await c.post("/api/vision/session/stop")
    res = {k: {"answer": v.get("answer") or v.get("text"), "total_s": v.get("total_s"), "error": v.get("error")}
           for k, v in out.items()}
    print(json.dumps(res, indent=1))
    path = os.path.join(os.path.dirname(__file__), "vision_results.json")
    try:
        allres = json.load(open(path))
    except Exception:
        allres = {}
    allres["council"] = {"run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **res}
    json.dump(allres, open(path, "w"), indent=1)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
