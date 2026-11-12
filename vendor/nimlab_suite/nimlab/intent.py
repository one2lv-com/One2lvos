"""Turn routing: which role handles a chat turn.

Rules first (attached media decide most turns), then the Intent Router
role when it is set, then keyword fallbacks. Only roles that are set are
ever chosen; anything else lands on the persona. Pure functions; the
router-model call is passed in as ask_fn.
"""

import os
import re

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".3gp")
AUDIO_EXT = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".amr")
VIDEO_HOSTS = re.compile(r"(youtube\.com/watch|youtu\.be/|vimeo\.com/)", re.I)

CHART_WORDS = re.compile(r"\b(chart|plot|graph|histogram|bar ?chart|pie|axis|axes|trend ?line|scatter|"
                         r"data points?|series|legend|infographic)\b", re.I)
OCR_WORDS = re.compile(r"\b(ocr|read (the )?text|extract (the )?text|transcribe|receipt|invoice|document|"
                       r"scan(ned)?|form|table|pdf|page)\b", re.I)
MUSIC_WORDS = re.compile(r"\b(music|song|melody|tempo|bpm|key of|chord|genre|instrument|beat|mix|"
                         r"ambient|ambience|background|noise|sound(s|scape)?|environment|bird|rain|"
                         r"what('?s| is) (this|that) (sound|noise)|vibe|mood)\b", re.I)
CODE_WORDS = re.compile(r"(```|\b(code|function|script|bug|debug|stack ?trace|traceback|compile|regex|sql|"
                        r"python|javascript|typescript|bash|shell|refactor|unit tests?|api call|json schema|"
                        r"class|def |import )\b)", re.I)
REASON_WORDS = re.compile(r"\b(step[- ]by[- ]step|prove|proof|derive|analy[sz]e|reason|plan( out)?|"
                          r"architecture|trade-?offs?|compare in depth|long document|summari[sz]e this|"
                          r"think (hard|carefully)|puzzle|math)\b", re.I)
IMAGE_GEN_WORDS = re.compile(r"\b(draw|generate|create|make|paint|render)\b.{0,40}\b(image|picture|photo|"
                             r"illustration|logo|art|wallpaper|portrait)\b", re.I)
AUDIO_GEN_WORDS = re.compile(r"\b(compose|generate|create|make|produce)\b.{0,40}\b(music|song|beat|track|"
                             r"melody|jingle|sound effect|sfx|loop)\b", re.I)
TRANSLATE_WORDS = re.compile(r"\btranslat(e|ion)\b|\bin (spanish|french|german|japanese|chinese|korean|"
                             r"italian|portuguese|russian|arabic|hindi)\b", re.I)

# labels the router model may answer with -> role key
ROUTER_LABELS = {
    "persona": ("persona", "normal conversation, questions, small talk"),
    "reasoning": ("reasoning", "hard multi-step reasoning, planning, long documents, math"),
    "coding": ("coding", "writing or fixing code, or a task that needs tools"),
    "image_gen": ("image_gen", "the user asks to create an image"),
    "audio_gen": ("audio_gen", "the user asks to create music or sound"),
    "translate": ("guard_translate", "the user asks for a translation"),
}


def _strip_punct(tok):
    return tok.strip("\"'()[]{}<>,;")


def media_kind(ref):
    low = ref.lower().split("?")[0]
    if low.startswith("data:image/") or low.endswith(IMAGE_EXT):
        return "image"
    if low.startswith("data:video/") or low.endswith(VIDEO_EXT) or VIDEO_HOSTS.search(ref):
        return "video"
    if low.startswith("data:audio/") or low.endswith(AUDIO_EXT):
        return "audio"
    return None


def find_media(text, exists=os.path.isfile):
    """[(kind, ref)] for media files or URLs mentioned in the text. Local
    paths count only when the file exists; URLs need a media extension
    (or a known video host)."""
    found = []
    for tok in (text or "").split():
        ref = _strip_punct(tok)
        if not ref:
            continue
        kind = media_kind(ref)
        if not kind:
            continue
        if ref.startswith(("http://", "https://", "data:")) or exists(os.path.expanduser(ref)):
            found.append((kind, os.path.expanduser(ref) if ref.startswith("~") else ref))
    return found


def strip_media(text, media):
    out = text
    for _, ref in media:
        out = out.replace(ref, " ")
    return re.sub(r"\s+", " ", out).strip()


def media_route(text, media, is_set):
    """Role for a turn with attached media, or None."""
    if not media:
        return None, ""
    kind = media[0][0]
    if kind == "image":
        if CHART_WORDS.search(text) and is_set("chart_parser"):
            return "chart_parser", "image + chart/plot words"
        if OCR_WORDS.search(text) and is_set("ocr"):
            return "ocr", "image + document/text words"
        for k in ("vision", "ocr", "chart_parser"):
            if is_set(k):
                return k, "image attached"
    if kind == "video":
        for k in ("video", "vision"):
            if is_set(k):
                return k, "video attached" if k == "video" else "video attached (no video role set; vision)"
    if kind == "audio":
        if MUSIC_WORDS.search(text) and is_set("omni_audio"):
            return "omni_audio", "audio + music/ambient words"
        if is_set("asr"):
            return "asr", "audio attached"
        if is_set("omni_audio"):
            return "omni_audio", "audio attached (no ASR role set)"
    return None, f"{kind} attached but no role for it is set"


def keyword_route(text, is_set):
    if IMAGE_GEN_WORDS.search(text) and is_set("image_gen"):
        return "image_gen", "keywords: image request"
    if AUDIO_GEN_WORDS.search(text) and is_set("audio_gen"):
        return "audio_gen", "keywords: music/sound request"
    if TRANSLATE_WORDS.search(text) and is_set("guard_translate"):
        return "guard_translate", "keywords: translation"
    if CODE_WORDS.search(text) and is_set("coding"):
        return "coding", "keywords: code"
    if REASON_WORDS.search(text) and is_set("reasoning"):
        return "reasoning", "keywords: reasoning"
    return "persona", "default"


def router_prompt(text, allowed):
    lines = [f"- {lab}: {ROUTER_LABELS[lab][1]}" for lab in allowed]
    return ("Pick the one label that best fits the user's message.\nLabels:\n" + "\n".join(lines) +
            f"\n\nUser message:\n{text[:2000]}\n\nAnswer with the label only.")


def parse_label(reply, allowed):
    """First allowed label in the router's reply (exact word), else None."""
    low = (reply or "").lower()
    best = None
    for lab in allowed:
        m = re.search(r"(?<![a-z_])" + re.escape(lab) + r"(?![a-z_])", low)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), lab)
    return best[1] if best else None


def route(text, is_set, ask_fn=None, exists=os.path.isfile):
    """-> dict(role, reason, media, text, via). via: media | router | rules.

    is_set(role_key) says whether a role has a backend; ask_fn(prompt) ->
    reply text or None runs the Intent Router role (None = not set)."""
    media = find_media(text, exists)
    rest = strip_media(text, media) if media else text
    role, why = media_route(rest, media, is_set)
    if role:
        return {"role": role, "reason": why, "media": media, "text": rest, "via": "media"}
    if ask_fn is not None:
        allowed = [lab for lab, (rk, _) in ROUTER_LABELS.items() if rk == "persona" or is_set(rk)]
        if len(allowed) > 1:
            reply = ask_fn(router_prompt(rest, allowed))
            lab = parse_label(reply, allowed) if reply else None
            if lab:
                return {"role": ROUTER_LABELS[lab][0], "reason": f"intent router said '{lab}'", "media": media,
                        "text": rest, "via": "router"}
    role, why2 = keyword_route(rest, is_set)
    reason = why2 if not why else f"{why}; {why2}"
    return {"role": role, "reason": reason, "media": media, "text": rest, "via": "rules"}
