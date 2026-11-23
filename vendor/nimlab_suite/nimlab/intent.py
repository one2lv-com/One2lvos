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

# v3.7.0 reasoning gate: the reasoning role is slow (a 1T-parameter model can
# take a minute), so it only runs when a turn really needs long-context or
# multi-step reasoning. Everything else (conversation, small talk, quick
# questions, "is this working?") goes straight to the persona.
DEEP_WORDS = re.compile(
    r"\b(think (it through|deeply|hard|carefully|step by step)|reason (it|this|that) (out|through)|"
    r"step[- ]by[- ]step|in[- ]depth|deep (dive|analysis)|thorough(ly)?|"
    r"analy[sz]e|analysis|evaluate|assess|critique|"
    r"plan (out|for|my|the|a|how)|make a plan|(project|study|business|migration|test|release) plan|roadmap|"
    r"strategy|design (a|an|the)\b.{0,30}\b(system|architecture|schema|api|pipeline|service|database)|"
    r"architecture|trade-?offs?|pros and cons|compare\b.{0,40}\b(in depth|in detail|thoroughly)|"
    r"prove|proof|derive|derivation|solve\b.{0,30}\b(equation|problem|puzzle)|puzzle|"
    r"long document|whole (document|file|report|paper)|summari[sz]e (this|the) (document|report|paper|file|pdf)|"
    r"root cause|debug(ging)? strategy)\b", re.I)
REASONING_DEFAULTS = {
    "reasoning_gate": True,          # off: the router / keywords may pick reasoning for any turn (pre-3.7)
    "reasoning_min_chars": 4000,     # message + attached text at least this long may use reasoning
    "reasoning_keywords": True,      # explicit asks (analyze, plan, step by step, think deeply, ...) may use it
    "chat_fast_path": True,          # short everyday turns skip the router call and go to the persona
    "chat_max_words": 16,            # "short" for the fast path
    "router_timeout_sec": 8,         # the intent router is a quick label; don't wait longer than this
}


# voice turns (v3.7.1): a spoken turn is conversation unless it clearly asks
# for code, a picture, music, a translation or deep reasoning, so the router
# call (and reasoning) is skipped and the persona answers at once.
VOICE_DEFAULTS = {
    "fast_route": True,              # casual voice turns skip the router and reasoning
    "fast_route_max_words": 60,      # longer transcripts still go through the router
}


def voice_settings(vs=None):
    out = dict(VOICE_DEFAULTS)
    out.update({k: v for k, v in (vs or {}).items() if k in VOICE_DEFAULTS})
    return out


def is_voice_casual(text, vs=None):
    """(bool, why): can the persona answer this spoken turn directly?"""
    v = voice_settings(vs)
    if not v["fast_route"]:
        return False, "voice fast route off"
    words = len((text or "").split())
    if words == 0:
        return False, "empty"
    if words > int(v["fast_route_max_words"] or 0):
        return False, f"long voice turn ({words} words > fast_route_max_words {v['fast_route_max_words']})"
    for name, rx in (("code", CODE_WORDS), ("image", IMAGE_GEN_WORDS), ("audio", AUDIO_GEN_WORDS),
                     ("translation", TRANSLATE_WORDS), ("deep reasoning", DEEP_WORDS)):
        m = rx.search(text)
        if m:
            return False, f"asks for {name} ('{m.group(0).strip()[:30]}')"
    return True, f"casual voice turn ({words} words)"


def gate_settings(rs=None):
    out = dict(REASONING_DEFAULTS)
    out.update({k: v for k, v in (rs or {}).items() if k in REASONING_DEFAULTS})
    return out


def needs_reasoning(text, context_chars=0, rs=None):
    """(bool, why): does this turn need the reasoning role?"""
    g = gate_settings(rs)
    if not g["reasoning_gate"]:
        return True, "reasoning gate off"
    total = len(text or "") + int(context_chars or 0)
    if total >= int(g["reasoning_min_chars"] or 0) > 0:
        return True, f"long input ({total} chars >= reasoning_min_chars {g['reasoning_min_chars']})"
    if g["reasoning_keywords"]:
        m = DEEP_WORDS.search(text or "")
        if m:
            return True, f"asks for deep reasoning ('{m.group(0)}')"
    return False, (f"normal conversation ({total} chars, no planning/analysis ask)")


# a turn with one of these asks for work, so the router still looks at it
TASK_WORDS = re.compile(
    r"\b(write|make|create|build|generate|draft|compose|draw|paint|render|design|code|program|script|"
    r"implement|fix|debug|refactor|translate|summari[sz]e|explain|describe|list|outline|calculate|compute|"
    r"convert|transcribe|read|look at|check (this|my|the)|review|help|show|find|search|compare|rewrite|"
    r"edit|plan|analy[sz]e|solve|prove|sing|speak|say)\b", re.I)


def is_quick_chat(text, context_chars=0, rs=None):
    """A short everyday turn the persona answers alone, with no router call:
    small talk, a quick question, "is this working?". Anything that asks
    for work (write, fix, translate, ...) still goes to the router."""
    g = gate_settings(rs)
    if not g["chat_fast_path"] or context_chars:
        return False
    words = len((text or "").split())
    if words == 0 or words > int(g["chat_max_words"] or 0):
        return False
    if TASK_WORDS.search(text):
        return False
    for rx in (CODE_WORDS, IMAGE_GEN_WORDS, AUDIO_GEN_WORDS, TRANSLATE_WORDS):
        if rx.search(text):
            return False
    return not needs_reasoning(text, 0, rs)[0] if g["reasoning_gate"] else not REASON_WORDS.search(text)


# labels the router model may answer with -> role key
ROUTER_LABELS = {
    "persona": ("persona", "normal conversation, questions, small talk, quick checks (the usual answer)"),
    "reasoning": ("reasoning", "ONLY long documents or explicit multi-step analysis, planning or proofs"),
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


def _gate(res, context_chars, rs, is_set):
    """Apply the reasoning gate to a decided route: reasoning only when the
    turn needs it. Adds res['gate'] with the decision for the trace. A
    persona route is upgraded to reasoning when the turn clearly needs it
    (long input or an explicit ask such as 'think it through')."""
    if res["role"] == "persona" and gate_settings(rs)["reasoning_gate"] and is_set("reasoning"):
        need, why = needs_reasoning(res["text"], context_chars, rs)
        if need:
            res.update(role="reasoning", reason=f"{res['reason']}; {why}: reasoning role", gate=why)
        return res
    if res["role"] != "reasoning":
        return res
    need, why = needs_reasoning(res["text"], context_chars, rs)
    if need:
        res["reason"] = f"{res['reason']}; {why}"
        res["gate"] = why
        return res
    res.update(role="persona", reason=f"{res['reason']}, but {why}: persona answers (no reasoning call)",
               gate=why)
    return res


def route(text, is_set, ask_fn=None, exists=os.path.isfile, context_chars=0, rs=None, voice=None):
    """-> dict(role, reason, media, text, via). via: media | fast | voice | router | rules.

    voice: the voice_settings when the turn was spoken (a voice call or a
    Telegram voice note): casual spoken turns go straight to the persona.

    is_set(role_key) says whether a role has a backend; ask_fn(prompt) ->
    reply text or None runs the Intent Router role (None = not set).
    context_chars: size of attached document text for this turn. rs: the
    routing_settings (the reasoning gate and fast path read it)."""
    media = find_media(text, exists)
    rest = strip_media(text, media) if media else text
    role, why = media_route(rest, media, is_set)
    if role:
        return {"role": role, "reason": why, "media": media, "text": rest, "via": "media"}
    if not media and voice is not None and not context_chars:
        casual, vwhy = is_voice_casual(rest, voice)
        if casual:
            return {"role": "persona", "reason": f"{vwhy}: persona answers directly (no router or reasoning call)",
                    "media": media, "text": rest, "via": "voice"}
    if not media and is_quick_chat(rest, context_chars, rs):
        return {"role": "persona", "reason": "quick conversation: persona answers directly (no router or "
                "reasoning call)", "media": media, "text": rest, "via": "fast"}
    if ask_fn is not None:
        allowed = [lab for lab, (rk, _) in ROUTER_LABELS.items() if rk == "persona" or is_set(rk)]
        if len(allowed) > 1:
            reply = ask_fn(router_prompt(rest, allowed))
            lab = parse_label(reply, allowed) if reply else None
            if lab:
                res = {"role": ROUTER_LABELS[lab][0], "reason": f"intent router said '{lab}'", "media": media,
                       "text": rest, "via": "router"}
                return _gate(res, context_chars, rs, is_set)
            why = (why + "; " if why else "") + ("intent router gave no usable label" if reply
                                                 else "intent router failed or timed out")
    role, why2 = keyword_route(rest, is_set)
    reason = why2 if not why else f"{why}; {why2}"
    res = {"role": role, "reason": reason, "media": media, "text": rest, "via": "rules"}
    return _gate(res, context_chars, rs, is_set)
