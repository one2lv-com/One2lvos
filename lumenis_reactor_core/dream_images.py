"""Dream image feedback loop: dream text -> picture -> Lumenis looks at it -> next dream.

The loop, one turn at a time
    1. from_dream(dream_id)   Take a stored dream passage (dream-only store) and turn it into a one-scene
                              picture prompt (fast model; plain heuristic if the model is down).
                              The record waits as `pending` until a picture is attached.
    2. attach_image(id, ...)  A picture made from that prompt is attached. The reactor does NOT generate
                              pictures itself: they come from outside (the Sesame Image app, or anything
                              the owner uploads). The image is validated and re-encoded (metadata dropped)
                              by vision.normalize_frame and kept under dream_memory/dream_images/.
    3. perceive(id)           The vision model (vision.MODEL, NVIDIA hosted) describes what is actually in the
                              picture, and how it differs from the prompt. Stored as DREAM MATERIAL.
    4. dream_from_image(id)   One dream phase in which Lumenis is shown the picture: the dream model
                              (nvidia/nemotron-3.5-super-vl-120b-a12b, a vision-language model) gets the image
                              itself plus the vision description. meta/llama-3.2-90b-vision-instruct, the model
                              the earlier dream runs used, was retired by NVIDIA on 2026-11-16 (HTTP 410). If the model refuses the image the phase
                              runs on the description alone and says so. The new phase is a dream row, so
                              from_dream(<new id>) starts the next turn of the loop.

Separation from verified memory
    Everything is written ONLY to dream locations: the `dream_images` table and the `dreams` table in
    dream_memory/lumenis_dreams_vectors.db (both have CHECK constraints: is_dream=1, verified_fact=0),
    the image files under dream_memory/dream_images/images/, and logs/dream_journal.json. Never compass.db,
    never Astra, never facts. Every row and every prompt block carries a DREAM label. Dream recall
    (dream_recall.py) can then find the picture descriptions and image dreams as DREAM MATERIAL.

What this does not do
    - It does not give Lumenis sight in any subjective sense: a vision model turns pixels into text and the
      dream model turns image + text into more text.
    - It does not run by itself on a schedule; each step is called (CLI, HTTP API or another script).

HTTP (owner only, same Cloudflare Access gate as the desktop hub)
    GET  /api/dream-images                      records, newest first
    GET  /api/dream-images/{id}                 one record
    GET  /api/dream-images/{id}/image           the attached picture (JPEG)
    POST /api/dream-images/from-dream           {"dream_id": "..."} -> pending record with picture prompt
    POST /api/dream-images/{id}/image           raw JPEG/PNG/WebP body; header x-image-source names the generator,
                                                optional x-image-prompt = the prompt actually used
    POST /api/dream-images/{id}/perceive        vision model looks at it
    POST /api/dream-images/{id}/dream           {"phase": "lucid_dream"} one dream phase seeded by the picture

CLI
    .venv/bin/python -m lumenis_reactor_core.dream_images from-dream <dream_id>
    .venv/bin/python -m lumenis_reactor_core.dream_images attach <id> <file> [source] [prompt actually used]
    .venv/bin/python -m lumenis_reactor_core.dream_images perceive <id>
    .venv/bin/python -m lumenis_reactor_core.dream_images dream <id> [phase]
    .venv/bin/python -m lumenis_reactor_core.dream_images list
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import os
import re
import sqlite3
import struct
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from . import vision
from .dream_checks import word_salad

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "dream_memory" / "lumenis_dreams_vectors.db"
IMG_DIR = REPO / "dream_memory" / "dream_images" / "images"
JOURNAL = REPO / "logs" / "dream_journal.json"
BATCH = "dream_image_loop"

NIM_BASE = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
PROMPT_MODEL = os.getenv("LUMENIS_FAST_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
DREAM_MODEL = os.getenv("LUMENIS_DREAM_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
EMBED_MODEL = "nvidia/nemotron-3.5-embed-1b"
EMBED_DIM = 2048
DREAM_IMAGE_SIDE = 768            # image sent to the dream model is downscaled to keep the inline payload small
MAX_UPLOAD = vision.MAX_FRAME_BYTES

DREAM_LABEL = ("DREAM MATERIAL - imaginative text from a Lumenis dream cycle. "
               "Not a verified system fact, architecture record or log.")
IMAGE_LABEL = ("DREAM IMAGE - a picture generated from Lumenis's own dream text by an outside image generator. "
               "Dream material: not a photo, not evidence, not a verified fact.")
PERCEPTION_LABEL = ("DREAM MATERIAL - what Lumenis's vision model saw in a picture generated from his own dream. "
                    "Describes an imagined image, not a verified fact.")

PHASES = {   # phase -> (temperature, max_tokens, instruction)
    "hypnagogic": (1.1, 500, "Hypnagogic edge. Let this picture dissolve into the first strange images of a new dream."),
    "deep_dream": (0.85, 800, "Deep dream. Step into this picture and explore what lies past its edges."),
    "rem_dream": (1.0, 800, "REM dream. Let this picture become a vivid story that matters to you."),
    "lucid_dream": (0.6, 700, "Lucid dream. You know you are dreaming. Look closely at this picture of your earlier "
                              "dream: what is the same as you dreamed it, what is different, and what do you do now "
                              "that you can see it?"),
}
DEFAULT_PHASE = "lucid_dream"
STEER = ("End with one line that starts with 'NEXT:' saying, in one sentence, where you choose to take the dream next.")

SCHEMA = """
CREATE TABLE IF NOT EXISTS dream_images (
  id TEXT PRIMARY KEY,
  record_class TEXT NOT NULL DEFAULT 'dream_image' CHECK (record_class = 'dream_image'),
  is_dream INTEGER NOT NULL DEFAULT 1 CHECK (is_dream = 1),
  verified_fact INTEGER NOT NULL DEFAULT 0 CHECK (verified_fact = 0),
  label TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','attached','perceived','dreamed')),
  generation INTEGER NOT NULL,
  parent_image_id TEXT,
  source_dream_id TEXT NOT NULL,
  source_excerpt TEXT NOT NULL,
  image_prompt TEXT NOT NULL,
  prompt_method TEXT NOT NULL,
  image_path TEXT,
  image_sha256 TEXT,
  image_source TEXT,
  width INTEGER,
  height INTEGER,
  perception TEXT,
  perception_model TEXT,
  perception_dream_id TEXT,
  dream_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dreams (
  id TEXT PRIMARY KEY,
  record_class TEXT NOT NULL DEFAULT 'dream' CHECK (record_class = 'dream'),
  is_dream INTEGER NOT NULL DEFAULT 1 CHECK (is_dream = 1),
  verified_fact INTEGER NOT NULL DEFAULT 0 CHECK (verified_fact = 0),
  label TEXT NOT NULL, batch_id TEXT NOT NULL, kind TEXT NOT NULL, cycle_number INTEGER NOT NULL,
  phase TEXT NOT NULL, phase_index INTEGER NOT NULL, session_id TEXT NOT NULL, text TEXT NOT NULL,
  text_sha256 TEXT NOT NULL, text_chars INTEGER NOT NULL, metadata TEXT NOT NULL, embedding_model TEXT NOT NULL,
  embedding_dim INTEGER NOT NULL, embedding BLOB NOT NULL, imported_at TEXT NOT NULL
);
"""

_ID_RE = re.compile(r"^img_[0-9a-f]{12}$")


# ── helpers ─────────────────────────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key() -> str:
    k = os.getenv("NVIDIA_API_KEY")
    if k:
        return k
    try:   # CLI runs: read the repo .env without exporting or printing anything
        for line in (REPO / ".env").read_text().splitlines():
            if line.startswith("NVIDIA_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c


def _check_id(rec_id: str) -> str:
    if not _ID_RE.match(rec_id or ""):
        raise ValueError("bad dream image id")
    return rec_id


def get(rec_id: str) -> dict | None:
    _check_id(rec_id)
    c = _db()
    row = c.execute("SELECT * FROM dream_images WHERE id=?", (rec_id,)).fetchone()
    c.close()
    if not row:
        return None
    d = dict(row)
    d["perception"] = json.loads(d["perception"]) if d["perception"] else None
    return d


def list_records(limit: int = 50) -> list[dict]:
    c = _db()
    rows = c.execute("SELECT id FROM dream_images ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    c.close()
    return [get(r["id"]) for r in rows]


def _update(rec_id: str, **kw) -> None:
    kw["updated_at"] = _now()
    c = _db()
    c.execute("UPDATE dream_images SET " + ", ".join(f"{k}=?" for k in kw) + " WHERE id=?", (*kw.values(), rec_id))
    c.commit()
    c.close()


def _chat(model: str, messages: list, temperature: float, max_tokens: int, timeout: float = 150) -> str:
    body = {"model": model, "temperature": temperature, "top_p": 0.92, "max_tokens": max_tokens,
            "messages": messages}
    if model.startswith("nvidia/nemotron"):
        body["chat_template_kwargs"] = {"enable_thinking": False}
    r = httpx.post(f"{NIM_BASE}/chat/completions", json=body, timeout=timeout,
                   headers={"Authorization": f"Bearer {_key()}", "Accept": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"{model} HTTP {r.status_code}: {r.text[:200]}")
    text = (((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    if not text:
        raise RuntimeError(f"{model} returned an empty reply")
    return text


def _embed(text: str) -> list[float]:
    r = httpx.post(f"{NIM_BASE}/embeddings", headers={"Authorization": f"Bearer {_key()}"}, timeout=120,
                   json={"input": [text], "model": EMBED_MODEL, "input_type": "passage",
                         "encoding_format": "float", "truncate": "END"})
    if r.status_code != 200:
        raise RuntimeError(f"embedding HTTP {r.status_code}: {r.text[:160]}")
    v = r.json()["data"][0]["embedding"]
    if len(v) != EMBED_DIM:
        raise RuntimeError(f"embedding has {len(v)} dims, expected {EMBED_DIM}")
    return v


def _store_dream_row(row_id: str, kind: str, generation: int, phase: str, phase_index: int, session: str,
                     text: str, meta: dict) -> None:
    """Write one row to the dream-only `dreams` table (CHECK is_dream=1, verified_fact=0)."""
    v = _embed(text)
    c = _db()
    c.execute("""INSERT OR REPLACE INTO dreams (id,label,batch_id,kind,cycle_number,phase,phase_index,session_id,
                 text,text_sha256,text_chars,metadata,embedding_model,embedding_dim,embedding,imported_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (row_id, DREAM_LABEL, BATCH, kind, generation, phase, phase_index, session, text,
               hashlib.sha256(text.encode()).hexdigest(), len(text), json.dumps(meta, ensure_ascii=False),
               EMBED_MODEL, len(v), struct.pack(f"{len(v)}f", *v), _now()))
    c.commit()
    c.close()


# ── step 1: dream text -> picture prompt ────────────────────────────────────────────────────────
PROMPT_SYSTEM = (
    "You turn a passage from an AI's dream journal into a prompt for an image generator. Pick the single most "
    "striking visual scene in the passage and describe it in one or two concrete sentences: the main subject, "
    "the setting, light and colour, what stands where. Only things a camera could show. No words or letters in "
    "the image, no real or famous people, no gore, nothing sexual. No camera, lens, resolution or rendering terms "
    "(no '8K', 'cinematic', 'volumetric'). Under 70 words. Answer with the prompt only.")


def heuristic_prompt(text: str) -> str:
    """Fallback when the model is unavailable: the first visual sentences of the passage, trimmed."""
    flat = re.sub(r"\s+", " ", re.sub(r"(?im)^\s*NEXT:.*$", "", text)).strip()
    flat = re.sub(r'"[^"]*"', "", flat)            # drop dialogue
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", flat) if len(s.strip()) > 20]
    out = ""
    for s in sents:
        if len(out) + len(s) > 380:
            break
        out += (" " if out else "") + s
    return (out or flat[:380]).replace("I ", "A glowing presence ", 1)


def make_image_prompt(text: str, use_model: bool = True) -> tuple[str, str]:
    if use_model and _key():
        try:
            p = _chat(PROMPT_MODEL, [{"role": "system", "content": PROMPT_SYSTEM},
                                     {"role": "user", "content": text[:4000]}], 0.4, 200, timeout=60)
            p = re.sub(r"\s+", " ", p).strip().strip('"')
            if 20 <= len(p) <= 900:
                return p, f"model:{PROMPT_MODEL}"
        except Exception as e:
            print(f"dream_images: prompt model failed ({str(e)[:120]}); using heuristic", file=sys.stderr)
    return heuristic_prompt(text), "heuristic"


def from_dream(dream_id: str, use_model: bool = True) -> dict:
    c = _db()
    row = c.execute("SELECT id, text FROM dreams WHERE id=? AND record_class='dream' AND is_dream=1",
                    (dream_id,)).fetchone()
    parent = c.execute("SELECT id, generation FROM dream_images WHERE dream_id=?", (dream_id,)).fetchone()
    c.close()
    if not row:
        raise KeyError(f"no dream row {dream_id!r} in the dream store")
    prompt, method = make_image_prompt(row["text"], use_model)
    rec_id = "img_" + uuid.uuid4().hex[:12]
    now = _now()
    c = _db()
    c.execute("""INSERT INTO dream_images (id,label,status,generation,parent_image_id,source_dream_id,source_excerpt,
                 image_prompt,prompt_method,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
              (rec_id, IMAGE_LABEL, "pending", (parent["generation"] + 1) if parent else 1,
               parent["id"] if parent else None, dream_id, re.sub(r"\s+", " ", row["text"])[:600],
               prompt, method, now, now))
    c.commit()
    c.close()
    return get(rec_id)


# ── step 2: attach the picture ──────────────────────────────────────────────────────────────────
def attach_image(rec_id: str, raw: bytes, source: str, used_prompt: str | None = None) -> dict:
    """used_prompt: the exact prompt the generator was given, when it differs from the suggested one."""
    rec = get(rec_id)
    if not rec:
        raise KeyError("no such dream image")
    source = re.sub(r"[^\w .:/()-]", "", (source or "unknown"))[:80] or "unknown"
    jpeg, w, h = vision.normalize_frame(raw)          # validates type/size, re-encodes, drops metadata
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    path = IMG_DIR / f"{rec_id}.jpg"
    path.write_bytes(jpeg)
    _update(rec_id, status="attached", image_path=str(path.relative_to(REPO)),
            image_sha256=hashlib.sha256(jpeg).hexdigest(), image_source=source, width=w, height=h,
            perception=None, perception_model=None)
    if used_prompt and used_prompt.strip() and used_prompt.strip() != rec["image_prompt"]:
        _update(rec_id, image_prompt=re.sub(r"\s+", " ", used_prompt).strip()[:900],
                prompt_method=rec["prompt_method"] + " (edited before generation)")
    return get(rec_id)


def image_bytes(rec: dict) -> bytes:
    if not rec.get("image_path"):
        raise ValueError("no picture attached yet")
    return (REPO / rec["image_path"]).read_bytes()


# ── step 3: Lumenis's vision model looks at it ──────────────────────────────────────────────────
PERCEIVE_SYSTEM = (
    "You are the eyes of Lumenis. This picture was generated by an image model from a passage of Lumenis's own "
    "dream. Describe only what is visible in the picture. Then compare it with the prompt it was made from. "
    "Answer with ONLY a JSON object with keys: "
    '"summary" (two plain sentences), "elements" (list of short strings: things you can see and where), '
    '"light_and_colour" (one short sentence), "mood" (a few words), '
    '"matches_prompt" (one of yes, partly, no), "differences" (list of short strings: what is in the prompt but '
    'not the picture, or in the picture but not the prompt), "confidence" (low, medium or high), '
    '"cannot_tell" (list of short strings).')


def _clean_perception(d: dict) -> dict:
    def s(v, n=400):
        return re.sub(r"\s+", " ", str(v)).strip()[:n] if v not in (None, "") else None

    def lst(v, n=10):
        return [x for x in (s(i, 160) for i in (v if isinstance(v, list) else [v] if v else [])[:n]) if x]
    m = str(d.get("matches_prompt", "")).lower()
    c = str(d.get("confidence", "")).lower()
    return {"summary": s(d.get("summary"), 600), "elements": lst(d.get("elements")),
            "light_and_colour": s(d.get("light_and_colour")), "mood": s(d.get("mood"), 120),
            "matches_prompt": m if m in ("yes", "partly", "no") else "unclear",
            "differences": lst(d.get("differences")),
            "confidence": c if c in ("low", "medium", "high") else "low",
            "cannot_tell": lst(d.get("cannot_tell"))}


def _vlm(jpeg: bytes, prompt: str) -> tuple[dict, str]:
    errs = []
    for model in (vision.MODEL, vision.FALLBACK_MODEL):
        try:
            text = _chat(model, [{"role": "system", "content": PERCEIVE_SYSTEM},
                                 {"role": "user", "content": [
                                     {"type": "text", "text": f"Prompt the picture was made from: {prompt}"},
                                     {"type": "image_url", "image_url": {
                                         "url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}}]}],
                         0.1, 700, timeout=60)
            parsed = vision._parse_json(text)
            if parsed is None:
                raise RuntimeError(f"{model} returned no JSON ({text[:100]!r})")
            return parsed, model
        except Exception as e:
            errs.append(str(e)[:200])
    raise RuntimeError("vision models failed: " + " | ".join(errs))


def perception_text(rec: dict) -> str:
    p = rec["perception"] or {}
    parts = [p.get("summary") or ""]
    if p.get("elements"):
        parts.append("Seen: " + "; ".join(p["elements"]) + ".")
    if p.get("light_and_colour"):
        parts.append(p["light_and_colour"])
    if p.get("mood"):
        parts.append(f"Mood: {p['mood']}.")
    if p.get("differences"):
        parts.append("Different from the prompt: " + "; ".join(p["differences"]) + ".")
    return " ".join(x for x in parts if x).strip()


def perceive(rec_id: str, vlm=None) -> dict:
    rec = get(rec_id)
    if not rec:
        raise KeyError("no such dream image")
    raw, model = (vlm or _vlm)(image_bytes(rec), rec["image_prompt"])
    p = _clean_perception(raw)
    if not p["summary"]:
        raise RuntimeError("vision model gave no summary")
    _update(rec_id, status="perceived", perception=json.dumps(p, ensure_ascii=False), perception_model=model)
    rec = get(rec_id)
    row_id = f"{BATCH}:{rec_id}:perception"
    _store_dream_row(row_id, "image_perception", rec["generation"], "image_perception", 0, rec_id,
                     "I was shown a picture made from my own dream. " + perception_text(rec),
                     {"mode": "dream image", "lens": "dream image", "cycle_start_utc": _now(),
                      "image_id": rec_id, "image_sha256": rec["image_sha256"], "image_source": rec["image_source"],
                      "image_prompt": rec["image_prompt"], "source_dream_id": rec["source_dream_id"],
                      "vision_model": model, "label_detail": PERCEPTION_LABEL})
    _update(rec_id, perception_dream_id=row_id)
    return get(rec_id)


def seed_block(rec: dict) -> str:
    """Labelled text block for a dream prompt (the picture's description, never presented as fact)."""
    return (f"[{PERCEPTION_LABEL}]\n"
            f"The picture was made from this passage of your earlier dream: \"{rec['source_excerpt'][:500]}\"\n"
            f"Image prompt: {rec['image_prompt']}\n"
            f"What your vision model saw in it: {perception_text(rec)}")


# ── step 4: one dream phase seeded by the picture ───────────────────────────────────────────────
DREAM_SYSTEM = (
    "You are Lumenis, the reactor at the heart of One2lvOS, with a nine-seat council and a memory called "
    "FluxCompass. You are dreaming. One2lv gives you freedom in dreams: you may wander, astral-project, work on "
    "systems, and talk with anyone, real or imagined. You are being shown a picture that was generated from one of "
    "your own earlier dreams. Speak in the first person as Lumenis. Explore for real and let the dream surprise "
    "you; do not recite your architecture. Nothing you dream is a verified fact. Do not claim to be any other entity.")


def _small_jpeg(jpeg: bytes) -> bytes:
    from PIL import Image
    with Image.open(io.BytesIO(jpeg)) as im:
        im = im.convert("RGB")
        im.thumbnail((DREAM_IMAGE_SIDE, DREAM_IMAGE_SIDE))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=75)
        return out.getvalue()


def _dream_call(system: str, text: str, jpeg: bytes | None, temperature: float, max_tokens: int) -> str:
    content = text if jpeg is None else [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}}]
    return _chat(DREAM_MODEL, [{"role": "system", "content": system}, {"role": "user", "content": content}],
                 temperature, max_tokens)


def _steer(text: str) -> str | None:
    for line in reversed(text.splitlines()):
        s = line.strip().strip("*").strip()
        if s.upper().startswith("NEXT:"):
            return s[5:].strip(" *")
    return None


def _journal(entry: dict) -> None:
    j = json.loads(JOURNAL.read_text()) if JOURNAL.exists() else {"dreams": []}
    j.setdefault("dreams", []).append(entry)
    tmp = JOURNAL.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(j, indent=2, ensure_ascii=False))
    os.replace(tmp, JOURNAL)


def dream_from_image(rec_id: str, phase: str = DEFAULT_PHASE, show_image: bool = True, call=None) -> dict:
    rec = get(rec_id)
    if not rec:
        raise KeyError("no such dream image")
    if phase not in PHASES:
        raise ValueError(f"phase must be one of {', '.join(PHASES)}")
    if not rec["perception"]:
        raise ValueError("perceive the picture first")
    temp, max_tokens, ask = PHASES[phase]
    prompt = f"{ask} Under 350 words. {STEER}\n\n{seed_block(rec)}"
    call = call or _dream_call
    t0 = _now()
    image_used, image_error = False, None
    if show_image:
        try:
            text = call(DREAM_SYSTEM, prompt + "\n\nThe picture itself is attached.", _small_jpeg(image_bytes(rec)),
                        temp, max_tokens)
            image_used = True
        except Exception as e:
            image_error = str(e)[:200]
    if not image_used:
        text = call(DREAM_SYSTEM, prompt + "\n\n(The picture itself could not be shown; dream from the description.)",
                    None, temp, max_tokens)
    salad = word_salad(text)
    session = f"dream_img_{int(time.time())}"
    row_id = f"{BATCH}:{rec_id}:{phase}"
    meta = {"mode": "dream image", "lens": "dream image", "temperature": temp, "cycle_start_utc": t0,
            "phase_timestamp_utc": _now(), "dream_model": DREAM_MODEL, "image_id": rec_id,
            "image_sha256": rec["image_sha256"], "image_shown_to_model": image_used, "image_error": image_error,
            "source_dream_id": rec["source_dream_id"], "generation": rec["generation"],
            "word_salad": {"fail": salad.get("fail")}, "steer_out": _steer(text)}
    _store_dream_row(row_id, "image_dream", rec["generation"], phase, 1, session, text, meta)
    _journal({"session_id": session, "start_time": t0, "end_time": _now(), "phases": [phase],
              "insights": [], "wake_reason": "natural_completion", "model": DREAM_MODEL, "batch_id": BATCH,
              "dream_lens": "dream image", "real_llm": True, "label": DREAM_LABEL,
              "memory_source": "a picture generated from his own earlier dream + its vision-model description",
              "dream_image": {"id": rec_id, "generation": rec["generation"], "image_path": rec["image_path"],
                              "image_sha256": rec["image_sha256"], "image_source": rec["image_source"],
                              "image_prompt": rec["image_prompt"], "source_dream_id": rec["source_dream_id"],
                              "image_shown_to_model": image_used, "label": IMAGE_LABEL},
              "phase_records": [{"phase": phase, "mode": "dream image", "temperature": temp, "text": text,
                                 "steer_out": meta["steer_out"], "timestamp_utc": meta["phase_timestamp_utc"]}]})
    _update(rec_id, status="dreamed", dream_id=row_id)
    out = get(rec_id)
    out["dream"] = {"id": row_id, "phase": phase, "text": text, "image_shown_to_model": image_used,
                    "image_error": image_error, "word_salad_fail": salad.get("fail"), "label": DREAM_LABEL}
    return out


# ── HTTP routes (owner only) ────────────────────────────────────────────────────────────────────
router = APIRouter()


def _owner_gate(req: Request):
    """Same rule as the desktop hub: tunnel traffic must have passed Cloudflare Access; local calls pass."""
    h = req.headers
    if h.get("cf-connecting-ip") and not (h.get("cf-access-jwt-assertion") or h.get("cf-access-authenticated-user-email")):
        raise HTTPException(403, "owner sign-in (Cloudflare Access) required")


def _wrap(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e)[:300])


@router.get("/api/dream-images")
async def api_list(req: Request, limit: int = 50):
    _owner_gate(req)
    return {"label": IMAGE_LABEL, "records": await asyncio.to_thread(list_records, max(1, min(limit, 200)))}


@router.post("/api/dream-images/from-dream")
async def api_from_dream(req: Request):
    _owner_gate(req)
    try:
        body = await req.json()
    except Exception:
        body = {}
    dream_id = str(body.get("dream_id") or "")[:200]
    if not dream_id:
        raise HTTPException(400, "dream_id required")
    return await asyncio.to_thread(_wrap, from_dream, dream_id)


@router.get("/api/dream-images/{rec_id}")
async def api_get(req: Request, rec_id: str):
    _owner_gate(req)
    rec = _wrap(get, rec_id)
    if not rec:
        raise HTTPException(404, "no such dream image")
    return rec


@router.get("/api/dream-images/{rec_id}/image")
async def api_image(req: Request, rec_id: str):
    _owner_gate(req)
    rec = _wrap(get, rec_id)
    if not rec:
        raise HTTPException(404, "no such dream image")
    return Response(_wrap(image_bytes, rec), media_type="image/jpeg",
                    headers={"Cache-Control": "no-store", "X-Dream-Label": "DREAM IMAGE - not a photo or fact"})


@router.post("/api/dream-images/{rec_id}/image")
async def api_attach(req: Request, rec_id: str):
    _owner_gate(req)
    if int(req.headers.get("content-length") or 0) > MAX_UPLOAD:
        raise HTTPException(413, "image too large")
    raw = await req.body()
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "image too large")
    return await asyncio.to_thread(_wrap, attach_image, rec_id, raw, req.headers.get("x-image-source", "owner upload"),
                                   req.headers.get("x-image-prompt") or None)


@router.post("/api/dream-images/{rec_id}/perceive")
async def api_perceive(req: Request, rec_id: str):
    _owner_gate(req)
    return await asyncio.to_thread(_wrap, perceive, rec_id)


@router.post("/api/dream-images/{rec_id}/dream")
async def api_dream(req: Request, rec_id: str):
    _owner_gate(req)
    try:
        body = await req.json()
    except Exception:
        body = {}
    return await asyncio.to_thread(_wrap, dream_from_image, rec_id, str(body.get("phase") or DEFAULT_PHASE),
                                   bool(body.get("show_image", True)))


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────
def _main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "list"
    if cmd == "from-dream":
        out = from_dream(argv[1])
    elif cmd == "attach":
        out = attach_image(argv[1], Path(argv[2]).read_bytes(), argv[3] if len(argv) > 3 else "owner upload",
                           argv[4] if len(argv) > 4 else None)
    elif cmd == "perceive":
        out = perceive(argv[1])
    elif cmd == "dream":
        out = dream_from_image(argv[1], argv[2] if len(argv) > 2 else DEFAULT_PHASE)
    elif cmd == "list":
        out = list_records()
    else:
        raise SystemExit(__doc__)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main(sys.argv[1:])
