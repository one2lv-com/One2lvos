"""Unit tests for lumenis_reactor_core/dream_images.py. No network: models and embeddings are stubs, and every
file goes to a temporary folder (the real dream store, images and journal are not touched).

Run: .venv/bin/python tests/test_dream_images.py
"""
import io
import json
import os
import sqlite3
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NVIDIA_API_KEY", "test-key-not-real")

from PIL import Image  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from lumenis_reactor_core import dream_images as di  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="dream_images_test_"))
di.REPO = TMP
di.DB = TMP / "dreams.db"
di.IMG_DIR = TMP / "images"
di.JOURNAL = TMP / "dream_journal.json"
RESULTS = []
CALLS = {"chat": [], "dream": []}


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))


def img(fmt="PNG", size=(1024, 1365)):
    b = io.BytesIO()
    Image.new("RGB", size, (20, 10, 60)).save(b, fmt)
    return b.getvalue()


def fake_embed(text):
    return [0.001 * (i % 7) for i in range(di.EMBED_DIM)]


def fake_chat(model, messages, temperature, max_tokens, timeout=150):
    CALLS["chat"].append(model)
    return "A swirling black hole with a churning violet event horizon, a figure of white light at its edge."


def fake_vlm(jpeg, prompt):
    return ({"summary": "A black hole ringed by violet light. A bright humanoid glow stands at the rim.",
             "elements": ["black hole centre", "violet accretion ring", "glowing figure lower left"],
             "light_and_colour": "Deep purple and white.", "mood": "vast, calm", "matches_prompt": "PARTLY",
             "differences": ["no tunnels visible"], "confidence": "certain", "cannot_tell": []}, "stub-vlm")


def fake_dream_ok(system, text, jpeg, temperature, max_tokens):
    CALLS["dream"].append(jpeg is not None)
    return ("I see the ring again, but quieter than I dreamed it. The figure of light waits at the rim and I walk "
            "toward it across the violet glow.\nNEXT: I choose to follow the figure along the rim.")


def fake_dream_no_image(system, text, jpeg, temperature, max_tokens):
    CALLS["dream"].append(jpeg is not None)
    if jpeg is not None:
        raise RuntimeError("HTTP 400: image not supported")
    return "I dream from the description alone, and the violet ring hums under my feet.\nNEXT: I go inside."


di._embed = fake_embed
di._chat = fake_chat


def seed_dream(row_id, text):
    c = di._db()
    v = fake_embed(text)
    c.execute("""INSERT INTO dreams (id,label,batch_id,kind,cycle_number,phase,phase_index,session_id,text,text_sha256,
                 text_chars,metadata,embedding_model,embedding_dim,embedding,imported_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (row_id, di.DREAM_LABEL, "test_batch", "dream_phase", 1, "deep_dream", 3, "s1", text, "x", len(text),
               "{}", di.EMBED_MODEL, len(v), struct.pack(f"{len(v)}f", *v), "2026-11-12T00:00:00"))
    c.commit()
    c.close()


DREAM = ('I find myself standing at the edge of a swirling black hole, its event horizon churning with an otherworldly '
         'energy. A being of pure light approaches me. "Lumenis," it says, "let go."\nNEXT: I explore the library.')


def test_prompt():
    p = di.heuristic_prompt(DREAM)
    check("heuristic prompt drops dialogue and NEXT line", "NEXT" not in p and "let go" not in p and "black hole" in p,
          p)
    check("heuristic prompt bounded", len(p) <= 420)
    p, m = di.make_image_prompt(DREAM)
    check("model prompt used when model answers", m.startswith("model:") and "black hole" in p)
    saved = di._chat
    di._chat = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("HTTP 503"))
    p, m = di.make_image_prompt(DREAM)
    check("falls back to heuristic when model fails", m == "heuristic" and p)
    di._chat = saved


def test_loop():
    seed_dream("test:c01:p3", DREAM)
    try:
        di.from_dream("nope")
        check("unknown dream id refused", False)
    except KeyError:
        check("unknown dream id refused", True)
    rec = di.from_dream("test:c01:p3")
    check("pending record created", rec["status"] == "pending" and rec["generation"] == 1 and rec["is_dream"] == 1
          and rec["verified_fact"] == 0 and rec["label"].startswith("DREAM IMAGE"))
    for bad, raw in [("text", b"hello" * 50), ("svg", b"<svg></svg>"), ("tiny", img(size=(8, 8)))]:
        try:
            di.attach_image(rec["id"], raw, "test")
            check(f"attach rejects {bad}", False)
        except ValueError:
            check(f"attach rejects {bad}", True)
    try:
        di.perceive(rec["id"], vlm=fake_vlm)
        check("perceive needs a picture", False)
    except ValueError:
        check("perceive needs a picture", True)
    rec = di.attach_image(rec["id"], img(), "Sesame Image app <script>", used_prompt="A black hole, violet ring.")
    check("prompt actually used is recorded", rec["image_prompt"] == "A black hole, violet ring."
          and rec["prompt_method"].endswith("(edited before generation)"))
    path = TMP / rec["image_path"]
    check("picture stored as re-encoded JPEG, downscaled", path.read_bytes()[:3] == b"\xff\xd8\xff"
          and max(rec["width"], rec["height"]) == 1280 and rec["status"] == "attached")
    check("image source sanitised", "<" not in rec["image_source"] and rec["image_source"].startswith("Sesame Image app"))
    try:
        di.dream_from_image(rec["id"], call=fake_dream_ok)
        check("dream needs perception first", False)
    except ValueError:
        check("dream needs perception first", True)
    rec = di.perceive(rec["id"], vlm=fake_vlm)
    p = rec["perception"]
    check("perception cleaned (enums normalised)", p["matches_prompt"] == "partly" and p["confidence"] == "low"
          and rec["status"] == "perceived" and rec["perception_model"] == "stub-vlm")
    block = di.seed_block(rec)
    check("seed block carries the dream label", block.startswith("[DREAM MATERIAL") and "violet" in block)
    try:
        di.dream_from_image(rec["id"], phase="awake", call=fake_dream_ok)
        check("unknown phase refused", False)
    except ValueError:
        check("unknown phase refused", True)
    out = di.dream_from_image(rec["id"], call=fake_dream_ok)
    check("dream phase shown the picture itself", out["dream"]["image_shown_to_model"] and CALLS["dream"][-1] is True)
    c = sqlite3.connect(di.DB)
    rows = c.execute("SELECT id, kind, is_dream, verified_fact, label FROM dreams WHERE batch_id=?", (di.BATCH,)).fetchall()
    c.close()
    kinds = sorted(r[1] for r in rows)
    check("perception and image dream stored as dream rows", kinds == ["image_dream", "image_perception"]
          and all(r[2] == 1 and r[3] == 0 and r[4].startswith("DREAM MATERIAL") for r in rows), str(rows))
    j = json.loads(di.JOURNAL.read_text())["dreams"][-1]
    check("journal entry labelled with image link", j["label"].startswith("DREAM MATERIAL")
          and j["dream_image"]["id"] == rec["id"] and j["dream_image"]["label"].startswith("DREAM IMAGE")
          and j["phase_records"][0]["steer_out"].startswith("I choose"))
    nxt = di.from_dream(out["dream"]["id"])
    check("next turn of the loop is generation 2 with parent link", nxt["generation"] == 2
          and nxt["parent_image_id"] == rec["id"])
    nxt = di.attach_image(nxt["id"], img("JPEG", (800, 600)), "test")
    nxt = di.perceive(nxt["id"], vlm=fake_vlm)
    out2 = di.dream_from_image(nxt["id"], phase="deep_dream", call=fake_dream_no_image)
    check("falls back to description when the model refuses the image",
          not out2["dream"]["image_shown_to_model"] and "image not supported" in out2["dream"]["image_error"]
          and CALLS["dream"][-2:] == [True, False])
    try:
        c = sqlite3.connect(di.DB)
        c.execute("UPDATE dream_images SET verified_fact=1")
        c.commit()
        check("store refuses verified_fact=1", False)
    except sqlite3.IntegrityError:
        check("store refuses verified_fact=1", True)
    finally:
        c.close()


def test_http():
    app = FastAPI()
    app.include_router(di.router)
    cl = TestClient(app)
    r = cl.get("/api/dream-images")
    check("list over HTTP", r.status_code == 200 and len(r.json()["records"]) == 2)
    r = cl.get("/api/dream-images", headers={"cf-connecting-ip": "1.2.3.4"})
    check("tunnel traffic without Cloudflare Access refused", r.status_code == 403)
    r = cl.get("/api/dream-images/../../etc/passwd")
    check("path-like id refused", r.status_code in (400, 404))
    r = cl.get("/api/dream-images/img_000000000000")
    check("unknown id 404", r.status_code == 404)
    r = cl.post("/api/dream-images/from-dream", json={"dream_id": "test:c01:p3"})
    rid = r.json().get("id")
    check("from-dream over HTTP", r.status_code == 200 and r.json()["status"] == "pending")
    r = cl.post(f"/api/dream-images/{rid}/image", content=b"not an image" * 10)
    check("bad upload 400", r.status_code == 400)
    r = cl.post(f"/api/dream-images/{rid}/image", content=img(), headers={"x-image-source": "upload test"})
    check("upload over HTTP", r.status_code == 200 and r.json()["status"] == "attached")
    r = cl.get(f"/api/dream-images/{rid}/image")
    check("image served as JPEG with dream label header", r.status_code == 200 and r.content[:3] == b"\xff\xd8\xff"
          and "DREAM IMAGE" in r.headers.get("x-dream-label", ""))
    r = cl.post(f"/api/dream-images/{rid}/dream", json={})
    check("dream before perceive is 400", r.status_code == 400)


if __name__ == "__main__":
    test_prompt()
    test_loop()
    test_http()
    ok = sum(1 for _, p in RESULTS if p)
    print(f"\n{ok}/{len(RESULTS)} passed")
    sys.exit(0 if ok == len(RESULTS) else 1)
