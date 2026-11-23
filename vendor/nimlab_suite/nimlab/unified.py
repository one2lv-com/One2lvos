"""One entity: the whole 16-role stack behind one call.

The Conversational Persona (soul.md + its role prompt) writes every reply.
Every other role is an ability the persona uses: attachments go to vision,
OCR, the chart parser, video, ASR or omni audio; the intent router decides
which abilities a turn needs; reasoning and coding run as abilities; image
and audio generation and TTS make media. Their results reach the persona as
context, and the caller gets one reply in one voice.

Used by the test server (/v1/chat/completions, /v1/responses, the /call
page), the testbed chat (/attach) and the terminal voice call. Standard
library only.
"""

import base64
import binascii
import hashlib
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import time
import urllib.parse
import zipfile
import zlib

from . import config, intent
from . import roles as R

DEFAULTS = {
    # the client's own system message: "append" adds it after soul.md and the
    # persona prompt, "ignore" drops it. soul.md is never replaced.
    "client_system": "append",
    "attach_max_chars": 20000,     # text read from one attached document
    "pdf_ocr_pages": 3,            # scanned-PDF pages sent to OCR
    "image_router": True,          # ask the intent router vision/OCR/chart when the words don't say
    "tts_max_chars": 1500,
}

TEXT_EXT = (".txt", ".md", ".markdown", ".json", ".jsonl", ".csv", ".tsv", ".xml", ".yaml", ".yml", ".toml",
            ".ini", ".cfg", ".conf", ".log", ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".c", ".h",
            ".cpp", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".sh", ".bash", ".zsh", ".sql", ".html", ".htm",
            ".css", ".scss", ".swift", ".lua", ".r", ".pl", ".dart", ".vue", ".svelte", ".env", ".gradle",
            ".properties", ".srt", ".vtt", ".tex", ".rst", ".bat", ".ps1", ".dockerfile", ".gitignore")
OFFICE_EXT = (".docx", ".odt", ".pptx", ".odp", ".xlsx", ".ods")

SPEAK_WORDS = re.compile(r"\b(say|read|speak|tell)\b[^.?!\n]{0,40}\b(out loud|aloud)\b|"
                         r"\b(send|give|reply with|answer with|make|record) (me )?(a |an )?voice (note|message|reply)\b|"
                         r"\b(reply|answer|respond) (out loud|in your (own )?voice|by voice)\b|"
                         r"\bin your (own )?voice\b|\bspeak (this|that|it|to me)\b", re.I)
SPEAK_QUOTE = re.compile(r"[\"\u201c]([^\"\u201d]{1,2000})[\"\u201d]|:\s*(.{1,2000})$", re.S)
ROUTER_IMAGE = {"vision": "vision", "describe": "vision", "ocr": "ocr", "text": "ocr", "read": "ocr",
                "chart": "chart_parser", "plot": "chart_parser", "graph": "chart_parser"}

IMAGE_ORDER = ("vision", "ocr", "chart_parser")
WHAT = {"vision": "see images", "ocr": "read text in images and scanned pages",
        "chart_parser": "read charts", "video": "watch video", "asr": "understand voice messages",
        "omni_audio": "listen to music and sounds", "image_gen": "make images", "audio_gen": "make music or sound",
        "tts": "speak out loud", "persona": "reply at all"}


def step_rows(trace, r, role, ent):
    """v3.8.3: every failed model attempt of the reply step goes into the
    trace (and so the bug record): role, model, upstream host, HTTP status,
    a short upstream body, HTTP attempts, and the fallbacks tried. A step
    that failed with no attempt list still gets one row naming its target."""
    rows = list(getattr(r, "tried", None) or []) if r is not None else []
    if r is not None and not r.ok and not rows:
        from . import fallback as FB
        sp = ent.spec(role) if hasattr(ent, "spec") else {}
        rows = [FB.attempt_row(role, "primary", sp.get("model"), getattr(r, "url", None) or sp.get("endpoint") or
                               ent._client_base() if hasattr(ent, "_client_base") else None, r,
                               getattr(r, "attempts", None))]
    for a in rows:
        if a.get("ok") and a.get("kind") == "primary":
            continue            # the successful reply row is added by the caller
        if a.get("ok"):
            continue
        row = {"role": a.get("role") or role, "label": R.label(a.get("role") or role),
               "why": "the reply" if a.get("kind") == "primary" else f"fallback ({a.get('kind')})",
               "ok": False, "ms": a.get("ms") or 0, "target": a.get("model"), "model": a.get("model"),
               "host": a.get("host"), "status": a.get("status"), "body": a.get("body"),
               "attempts": a.get("attempts"), "error": f"HTTP {a.get('status')}: {a.get('body') or ''}".strip()
               if a.get("status") else (a.get("body") or "failed")}
        if a.get("kind") == "primary" and len(rows) > 1:
            row["fallbacks"] = [x.get("model") for x in rows if x.get("kind") != "primary"]
        trace.append(row)


class Part:
    """One attachment. kind: image | audio | video | file. Exactly one of
    path (a local file) or url (http/https, handed to the model) is set."""

    def __init__(self, kind, path=None, url=None, mime=None, name=None, temp=False):
        self.kind = kind
        self.path = path
        self.url = url
        self.mime = mime or (mimetypes.guess_type(path or url or "")[0] if (path or url) else None) or ""
        self.name = name or os.path.basename(urllib.parse.urlparse(url).path if url else (path or "")) or kind
        self.temp = temp

    @property
    def ref(self):
        return self.path or self.url

    def __repr__(self):
        return f"Part({self.kind}, {self.name}, {self.mime})"


class PartError(ValueError):
    """A client sent a part this pipeline refuses (bad base64, local path)."""


# ---------------------------------------------------------------------------
# Attachments in
# ---------------------------------------------------------------------------
def upload_dir():
    d = config.output_path("uploads")
    os.makedirs(d, exist_ok=True)
    return d


def kind_of(mime, name=""):
    m = (mime or "").lower()
    low = (name or "").lower()
    if m.startswith("image/") or low.endswith(intent.IMAGE_EXT):
        return "image"
    if m.startswith("audio/") or low.endswith(intent.AUDIO_EXT):
        return "audio"
    if m.startswith("video/") or low.endswith(intent.VIDEO_EXT):
        return "video"
    return "file"


def sniff_mime(data, name=""):
    d = data[:16]
    if d[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if d[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if d[:4] == b"GIF8":
        return "image/gif"
    if d[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if d[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if d[:3] == b"ID3" or d[:2] in (b"\xff\xfb", b"\xff\xf3"):
        return "audio/mpeg"
    if d[:4] == b"OggS":
        return "audio/ogg"
    if d[:4] == b"fLaC":
        return "audio/flac"
    if d[:4] == b"\x1aE\xdf\xa3":
        return "video/webm" if not name.lower().endswith((".weba",)) else "audio/webm"
    if data[4:8] == b"ftyp":
        return "audio/mp4" if data[8:11] in (b"M4A", b"M4B") else "video/mp4"
    if d[:5] == b"%PDF-":
        return "application/pdf"
    if d[:2] == b"PK":
        return mimetypes.guess_type(name)[0] or "application/zip"
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def save_upload(data, mime=None, name=None):
    mime = mime if mime and mime != "application/octet-stream" else sniff_mime(data, name or "")
    ext = os.path.splitext(name or "")[1] or mimetypes.guess_extension(mime or "") or ".bin"
    ext = {".jpe": ".jpg", ".oga": ".ogg"}.get(ext, ext)
    p = os.path.join(upload_dir(), f"up_{int(time.time() * 1000)}_{secrets.token_hex(4)}{ext}")
    with open(p, "wb") as f:
        f.write(data)
    return Part(kind_of(mime, name or p), path=p, mime=mime, name=name or os.path.basename(p), temp=True)


def decode_data_url(url):
    """data: URL -> (mime, bytes). Raises PartError when it is not one."""
    m = re.match(r"data:([^;,]*)((?:;[^;,]*)*),(.*)\Z", url or "", re.S)
    if not m:
        raise PartError("not a valid data: URL")
    mime = (m.group(1) or "application/octet-stream").lower()
    payload = m.group(3)
    if ";base64" in m.group(2).lower():
        try:
            data = b64(payload)
        except PartError:
            raise PartError("the data: URL is not valid base64")
    else:
        data = urllib.parse.unquote_to_bytes(payload)
    return mime, data


def b64(s):
    s = re.sub(r"\s+", "", s or "")
    try:
        return base64.b64decode(s + "=" * (-len(s) % 4), validate=False)
    except (binascii.Error, ValueError):
        raise PartError("not valid base64")


def part_from_url(url, hint, name=None, allow_paths=False):
    """A client URL -> Part. data: URLs are saved to a file; http(s) is
    handed to the model as is; a bare path only when allow_paths (the
    testbed on the phone; never for the server)."""
    url = (url or "").strip()
    low = url.lower()
    if low.startswith("data:"):
        mime, data = decode_data_url(url)
        p = save_upload(data, mime, name)
        if hint != "file" and p.kind == "file":
            p.kind = hint
        return p
    if low.startswith(("http://", "https://")):
        k = intent.media_kind(url) or hint
        return Part(k if hint == "file" else hint, url=url, name=name)
    if allow_paths:
        return part_from_path(url)
    raise PartError("media URLs must be http(s):// or data: URLs (local file paths are refused)")


def part_from_path(path):
    p = os.path.expanduser((path or "").strip().strip("'\""))
    if p.startswith("file://"):
        p = urllib.parse.unquote(p[7:])
    if not os.path.isfile(p):
        raise PartError(f"file not found: {path}")
    with open(p, "rb") as f:
        head = f.read(64)
    mime = mimetypes.guess_type(p)[0] or sniff_mime(head, p)
    return Part(kind_of(mime, p), path=p, mime=mime, name=os.path.basename(p))


ATTACH_DIRS = ("/storage/emulated/0/Download", "/storage/emulated/0/Documents", "/storage/emulated/0/Pictures",
               "/storage/emulated/0/DCIM/Camera", "/storage/emulated/0/Recordings", "/storage/emulated/0/Movies",
               "/storage/emulated/0/Music", "~/storage/downloads", "~/storage/shared/Documents")


def recent_files(dirs=ATTACH_DIRS, limit=20):
    """Newest files in the usual Android folders: [(path, size, mtime)]."""
    seen, found = set(), []
    for d in dirs:
        d = os.path.realpath(os.path.expanduser(d))
        if d in seen or not os.path.isdir(d):
            continue
        seen.add(d)
        for root, subdirs, files in os.walk(d):
            subdirs[:] = [x for x in subdirs if not x.startswith(".")][:20]
            if root.count(os.sep) - d.count(os.sep) > 1:
                subdirs[:] = []
            for f in files:
                if f.startswith("."):
                    continue
                p = os.path.join(root, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                found.append((p, st.st_size, st.st_mtime))
    found.sort(key=lambda x: -x[2])
    return found[:limit]


_PATH_TOK = re.compile(r"""(['"])((?:file://|~|/)[^'"]+)\1|((?:file://|~/|/)(?:\\ |[^\s])+)""")


def paths_in_text(text):
    """Existing local files named in typed text (quoted, file://, '\\ '
    escapes, /sdcard aliases): [(raw, path)]. Testbed only; the server
    never reads paths from client text."""
    from .voiceclone import clean_path
    out = []
    for m in _PATH_TOK.finditer(text or ""):
        raw = m.group(0)
        cand = m.group(2) or m.group(3)
        p = clean_path(cand.rstrip(".,;:!?)"))
        if os.path.isfile(p):
            out.append((raw.rstrip(".,;:!?)") if not m.group(2) else raw, p))
    return out


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0


def parse_content(content, allow_paths=False):
    """OpenAI message content (chat or responses style) ->
    (text, [Part], [note]). Notes name parts that were skipped."""
    if content is None:
        return "", [], []
    if isinstance(content, str):
        return content, [], []
    if not isinstance(content, list):
        return str(content), [], []
    texts, parts, notes = [], [], []
    for p in content:
        if isinstance(p, str):
            texts.append(p)
            continue
        if not isinstance(p, dict):
            continue
        t = p.get("type")
        if t in ("text", "input_text", "output_text"):
            texts.append(p.get("text") or "")
        elif t in ("image_url", "input_image"):
            v = p.get("image_url")
            url = v.get("url") if isinstance(v, dict) else v
            if url:
                parts.append(part_from_url(url, "image", allow_paths=allow_paths))
            elif p.get("file_id"):
                notes.append("an image sent by file_id (upload it inline as image_url instead)")
        elif t == "input_audio":
            a = p.get("input_audio") or {}
            fmt = (a.get("format") or "wav").lower()
            data = b64(a.get("data") or "")
            if not data:
                raise PartError("input_audio.data is empty")
            parts.append(save_upload(data, mimetypes.guess_type("x." + fmt)[0] or f"audio/{fmt}", f"audio.{fmt}"))
            parts[-1].kind = "audio"
        elif t in ("audio_url", "input_audio_url"):
            v = p.get("audio_url")
            url = v.get("url") if isinstance(v, dict) else v
            if url:
                parts.append(part_from_url(url, "audio", allow_paths=allow_paths))
        elif t in ("video_url", "input_video"):
            v = p.get("video_url")
            url = v.get("url") if isinstance(v, dict) else v
            if url:
                parts.append(part_from_url(url, "video", allow_paths=allow_paths))
        elif t in ("file", "input_file"):
            f = p.get("file") if isinstance(p.get("file"), dict) else p
            name = f.get("filename") or f.get("name")
            fd = f.get("file_data")
            if fd:
                if fd.startswith("data:"):
                    parts.append(part_from_url(fd, "file", name=name))
                else:
                    parts.append(save_upload(b64(fd), mimetypes.guess_type(name or "")[0], name))
            elif f.get("file_url"):
                parts.append(part_from_url(f["file_url"], "file", name=name, allow_paths=allow_paths))
            else:
                notes.append(f"{name or 'a file'} was sent by file_id; send it inline as file_data instead")
        elif t:
            notes.append(f"a '{t}' part (not a type this server reads)")
    return "\n".join(x for x in texts if x), parts, notes


def history_text(content):
    """Earlier turns: text only, attachments named, not re-read."""
    if isinstance(content, str) or content is None:
        return content or ""
    out = []
    for p in content if isinstance(content, list) else []:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            t = p.get("type") or ""
            if t in ("text", "input_text", "output_text"):
                out.append(p.get("text") or "")
            elif t:
                kind = t.replace("input_", "").replace("_url", "")
                name = ((p.get("file") or {}).get("filename") if isinstance(p.get("file"), dict) else None)
                out.append(f"[{kind} attached{': ' + name if name else ''}]")
    return " ".join(x for x in out if x)


def turn_key(messages):
    """A stable id for 'the conversation up to and including the last user
    message'. A UI resends the whole history every turn, and a regenerate
    resends the same last message: both give the same key, so memory stores
    that turn once."""
    h = hashlib.sha256()
    for m in messages:
        if m.get("role") not in ("user", "assistant"):
            continue
        c = m.get("content")
        blob = json.dumps(c, sort_keys=True, ensure_ascii=False) if not isinstance(c, str) else c
        h.update(m["role"].encode() + b"\0" + hashlib.sha256(blob.encode("utf-8", "replace")).digest())
    return h.hexdigest()[:32]


# ---------------------------------------------------------------------------
# Documents -> text (stdlib only)
# ---------------------------------------------------------------------------
_STREAM = re.compile(rb"(<<(?:[^<>]|<<(?:[^<>]|<<[^<>]*>>)*>>)*>>)\s*stream\r?\n", re.S)
_TXT_OP = re.compile(rb"\[((?:\\.|[^\]\\])*)\]\s*TJ|\(((?:\\.|[^\\)])*)\)\s*(?:Tj|'|\")|"
                     rb"(T\*|ET|-?[\d.]+\s+-?[\d.]+\s+T[dD])", re.S)
_STR = re.compile(rb"\(((?:\\.|[^\\)])*)\)|(-?\d+\.?\d*)")


def _pdf_unescape(b):
    out = bytearray()
    i = 0
    while i < len(b):
        c = b[i]
        if c == 0x5c and i + 1 < len(b):
            n = b[i + 1]
            m = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}.get(n)
            if m is not None:
                out.append(m)
                i += 2
            elif 0x30 <= n <= 0x37:
                j = i + 1
                while j < len(b) and j < i + 4 and 0x30 <= b[j] <= 0x37:
                    j += 1
                out.append(int(b[i + 1:j], 8) & 0xFF)
                i = j
            elif n in (10, 13):
                i += 2
            else:
                out.append(n)
                i += 2
        else:
            out.append(c)
            i += 1
    return out.decode("latin-1")


def _pdf_content_text(data):
    out = []
    for m in _TXT_OP.finditer(data):
        if m.group(1) is not None:
            for s in _STR.finditer(m.group(1)):
                if s.group(1) is not None:
                    out.append(_pdf_unescape(s.group(1)))
                elif s.group(2) and float(s.group(2)) < -180:
                    out.append(" ")
        elif m.group(2) is not None:
            out.append(_pdf_unescape(m.group(2)))
        else:
            op = m.group(3)
            if op in (b"T*", b"ET") or (op.endswith((b"Td", b"TD")) and float(op.split()[1]) != 0):
                out.append("\n")
            elif op.endswith((b"Td", b"TD")):
                out.append(" ")
    return "".join(out)


def pdf_extract(data, max_images=3):
    """(text, [jpeg bytes]) from a PDF: the text layer of plain content
    streams, and DCT (JPEG) page images for OCR when there is no text.
    Fonts with custom encodings come out as junk and are dropped."""
    texts, jpegs = [], []
    for m in _STREAM.finditer(data):
        d = m.group(1)
        start = m.end()
        ln = re.search(rb"/Length\s+(\d+)(?!\s+\d+\s+R)", d)
        end = start + int(ln.group(1)) if ln else data.find(b"endstream", start)
        if end <= start or end > len(data):
            end = data.find(b"endstream", start)
            if end < 0:
                continue
        raw = data[start:end]
        if b"/DCTDecode" in d and b"/Image" in d:
            if len(jpegs) < max_images and raw[:3] == b"\xff\xd8\xff":
                jpegs.append(raw)
            continue
        if b"/Subtype" in d and b"/Form" not in d:
            continue   # fonts, images, metadata
        if b"/FlateDecode" in d:
            try:
                raw = zlib.decompressobj().decompress(raw)
            except zlib.error:
                continue
        elif b"/Filter" in d:
            continue
        t = _pdf_content_text(raw)
        if t.strip():
            texts.append(t)
    text = re.sub(r"[ \t]+", " ", "".join(texts))
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    if text:
        good = sum(1 for ch in text if ch.isprintable() or ch in "\n\t")
        letters = sum(1 for ch in text if ch.isalnum())
        if good / len(text) < 0.9 or letters / len(text) < 0.3:
            text = ""
    return text, jpegs


def office_text(path):
    """Plain text from .docx/.odt/.pptx/.odp/.xlsx/.ods (zip + XML)."""
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        return ""
    names = z.namelist()
    pick = [n for n in names if n == "word/document.xml" or n == "content.xml" or
            re.match(r"ppt/slides/slide\d+\.xml$", n) or n == "xl/sharedStrings.xml"]
    pick.sort(key=lambda n: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", n)])
    out = []
    for n in pick:
        try:
            xml = z.read(n).decode("utf-8", "replace")
        except (KeyError, zipfile.BadZipFile):
            continue
        xml = re.sub(r"</(w:p|text:p|text:h|a:p|si|table:table-row)>", "\n", xml)
        xml = re.sub(r"<(w:tab|text:tab)[^>]*/>", "\t", xml)
        txt = re.sub(r"<[^>]+>", "", xml)
        for a, b in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&")):
            txt = txt.replace(a, b)
        out.append(txt.strip())
    return "\n\n".join(x for x in out if x)


def looks_text(path, mime):
    low = path.lower()
    if (mime or "").startswith("text/") or low.endswith(TEXT_EXT) or os.path.basename(low) in (
            "dockerfile", "makefile", "readme", "license"):
        return True
    if mime in ("application/json", "application/xml", "application/x-sh", "application/javascript",
                "application/x-yaml", "application/toml", "application/sql"):
        return True
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return False
    if not head or b"\0" in head:
        return False
    try:
        head.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def read_text_file(path, cap):
    with open(path, "rb") as f:
        raw = f.read(cap * 4 + 16)
    size = os.path.getsize(path)
    text = raw.decode("utf-8", "replace")
    return clip(text, cap, total=None if size <= len(raw) else size, unit="bytes")


def clip(text, cap, total=None, unit="characters"):
    n = len(text)
    if n <= cap and total is None:
        return text
    whole = total if total is not None else n
    return text[:cap] + f"\n[truncated: showing the first {cap:,} characters of {whole:,} {unit}]"


def to_wav(path):
    """Audio the ASR endpoint can take. WAV passes; other formats go through
    ffmpeg when it is installed (16 kHz mono). -> (path, temp?, note)."""
    with open(path, "rb") as f:
        head = f.read(12)
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return path, False, None
    exe = shutil.which("ffmpeg")
    if not exe:
        return path, False, "not WAV and ffmpeg isn't installed (pkg install ffmpeg); sent as is"
    out = os.path.join(upload_dir(), f"conv_{int(time.time() * 1000)}_{secrets.token_hex(3)}.wav")
    try:
        r = subprocess.run([exe, "-loglevel", "error", "-y", "-i", path, "-ac", "1", "-ar", "16000", out],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if r.returncode == 0 and os.path.getsize(out) > 44:
            return out, True, None
    except (OSError, subprocess.SubprocessError):
        pass
    return path, False, "ffmpeg couldn't convert it to WAV; sent as is"


def tts_clean(text, strict=False):
    """Text a TTS model can read: no tool-call markup or chat-template tokens,
    no code fences, links, markdown, or bracket/control characters (Riva and
    Magpie on Triton reject some, e.g. "multichar start character" on ]<[).
    strict=True keeps letters, digits and plain punctuation only."""
    from .mcp import strip_tool_markup
    t = re.sub(r"<\|im_start\|>\s*(?:system|user|assistant|tool)\b", " ", text or "")
    t = re.sub(r"<\|channel\|>\s*\w+\s*<\|message\|>", " ", t)          # harmony-style headers
    t = strip_tool_markup(t)
    t = re.sub(r"<\|[^|<>]{1,40}\|>", " ", t)                    # leftover template tokens
    t = re.sub(r"```.*?(```|$)", " ", t, flags=re.S)
    t = re.sub(r"<think>.*?(</think>|$)", " ", t, flags=re.S)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"</?[A-Za-z][^>]{0,80}>", " ", t)            # stray tags
    t = re.sub(r"[*_`#>|]+", "", t)
    t = re.sub(r"[\[\]{}<>~^\\@$]+", " ", t)                   # brackets and markup characters
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", t)
    if strict:
        t = re.sub(r"[^\w\s.,!?;:'\"()%&+\-/]", " ", t)
    t = _balance(t)
    t = re.sub(r"\(\s*\)", " ", t)
    t = re.sub(r"\s+([.,!?;:])", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def _balance(t):
    """Drop parentheses without a partner and double quotes left odd, so a
    TTS front end never sees a start character without its end."""
    keep, stack = list(t), []
    for i, ch in enumerate(keep):
        if ch == "(":
            stack.append(i)
        elif ch == ")":
            if stack:
                stack.pop()
            else:
                keep[i] = " "
    for i in stack:
        keep[i] = " "
    t = "".join(keep)
    if (t.count('"') % 2) or (t.count("\u201c") != t.count("\u201d")):
        t = t.replace('"', " ").replace("\u201c", " ").replace("\u201d", " ")
    return t


def speakable(text, cap=1500):
    """Reply -> what TTS should say: no code blocks, links, markdown or markup."""
    t = re.sub(r"```.*?```", " (the code is in the chat) ", text or "", flags=re.S)
    t = tts_clean(t)
    if len(t) > cap:
        cut = t[:cap]
        t = cut[:max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "), cap // 2) + 1].strip()
    return t


def soul_name(soul):
    """The entity's name as soul.md gives it (Name: X, or a '# X' title),
    or None."""
    for pat in (r"(?im)^\W*name\W*[:\-]\s*\**([A-Z][\w .'\-]{0,40}?)\**\s*$",
                r"(?i)\b(?:you are|i am|i'm)\s+\**([A-Z][\w'\-]{1,30})",
                r"(?m)^#\s+(?:soul[:\s\-]*)?([A-Z][\w'\-]{1,30})\s*$"):
        m = re.search(pat, soul or "")
        if m:
            name = m.group(1).strip(" *.")
            if name.lower() not in ("soul", "identity", "the", "a", "an", "system"):
                return name
    return None


# ---------------------------------------------------------------------------
# The entity
# ---------------------------------------------------------------------------
class Mind:
    """Runs one turn through the whole stack. ent is a nimlab.entity.Entity;
    settings are DEFAULTS overrides."""

    def __init__(self, ent, settings=None):
        self.ent = ent
        self.s = dict(DEFAULTS, **(settings or {}))

    # -- helpers -----------------------------------------------------------
    def _run(self, role, trace, why, **inp):
        t0 = time.monotonic()
        r = self.ent.run_role(role, **inp)
        trace.append({"role": role, "label": R.label(role), "why": why, "ok": bool(r.ok),
                      "ms": int((time.monotonic() - t0) * 1000), "target": self.ent.target(role),
                      **({"error": str(r.error)[:200]} if not r.ok else {})})
        return r

    def _first_set(self, *keys):
        return next((k for k in keys if self.ent.is_set(k)), None)

    def _router_says(self, question, text, labels, trace):
        """One short intent-router call: which of labels fits. None when the
        router isn't set or answers something else."""
        ent = self.ent
        if not ent.is_set("intent_router"):
            return None
        t0 = time.monotonic()
        reply = ent._ask_router(f"{question}\nUser message:\n{text[:1500]}\n\nAnswer with one word: "
                                f"{' or '.join(sorted(set(labels)))}.")
        trace.append({"role": "intent_router", "label": R.label("intent_router"), "why": "pick an ability",
                      "ok": reply is not None, "ms": int((time.monotonic() - t0) * 1000),
                      "target": ent.target("intent_router")})
        low = (reply or "").lower()
        for word, key in labels.items():
            if re.search(rf"\b{word}", low):
                return key
        return None

    def image_role(self, text, trace):
        want = None
        if intent.CHART_WORDS.search(text or ""):
            want = "chart_parser"
        elif intent.OCR_WORDS.search(text or "") or re.search(r"\b(read|extract|what does (it|this) say|"
                                                               r"copy the text|screenshot)\b", text or "", re.I):
            want = "ocr"
        elif text and self.s.get("image_router") and sum(self.ent.is_set(k) for k in IMAGE_ORDER) > 1:
            want = self._router_says("An image came with this message. Is it for vision (look at or describe a "
                                     "picture), ocr (read the text of a document, screenshot or sign) or chart "
                                     "(read a chart or plot)?", text, ROUTER_IMAGE, trace)
        want = want or "vision"
        order = (want,) + tuple(k for k in IMAGE_ORDER if k != want)
        return self._first_set(*order), want

    def audio_role(self, text, trace):
        if intent.MUSIC_WORDS.search(text or "") and self.ent.is_set("omni_audio"):
            return "omni_audio"
        if text and self.ent.is_set("omni_audio") and self.ent.is_set("asr") and not re.search(
                r"\b(transcri|what (did|does) (he|she|they|it|i) say|said|voice|speech|message)\w*", text, re.I):
            pick = self._router_says("Audio came with this message. Is it speech (someone talking: transcribe it) "
                                     "or sound (music, ambience, noises: listen to it)?", text,
                                     {"speech": "asr", "sound": "omni_audio", "music": "omni_audio"}, trace)
            if pick:
                return pick
        return self._first_set("asr", "omni_audio")

    # -- one turn ------------------------------------------------------------
    def run(self, text, parts=(), history=None, client_system=None, on_token=None, want_audio=False,
            turn_key=None, notes=(), voice=None, allow_text_paths=False, temperature=0.7, max_tokens=1024,
            defer_store=False):
        """-> dict(ok, text, reply, error, blocked, route, media, audio,
        transcript, trace, notes, missing, streamed, usage, result).

        text: the user's words; parts: [Part]; history: earlier
        [{role, content}] text turns (not changed). on_token streams the
        persona's reply. want_audio: speak the reply with the TTS role.

        The turn is saved to long-term memory after the reply (and its
        speech) is ready, never before. defer_store=True hands that step to
        the caller as res['finish'] (a voice call runs it once playback has
        started); otherwise it runs here, last."""
        ent = self.ent
        t_all = time.monotonic()
        history = [dict(m) for m in (history or [])]
        parts = list(parts or [])
        body = (text or "").strip()
        trace, ctx, missing, skipped = [], [], [], list(notes or ())
        temps, transcript = [], None
        if allow_text_paths:
            for raw, path in paths_in_text(body):
                if any(p.path == path for p in parts):
                    continue
                parts.append(part_from_path(path))
                body = body.replace(raw, " ")
            body = re.sub(r"[ \t]+", " ", body).strip()
        found = [(k, r) for k, r in intent.find_media(body, lambda p: False)]
        for kind, ref in found:
            try:
                parts.append(part_from_url(ref, kind))
            except PartError as e:
                skipped.append(str(e))
        if found:
            body = intent.strip_media(body, found).strip()
        if not ent.is_set("persona"):
            return self._fail("The Conversational Persona role isn't set, and it's the voice that answers every "
                              "message. Set it in the testbed (launcher R, or testbed option 2).", trace, t_all)
        first_ability = None
        try:
            for i, part in enumerate(parts, 1):
                label = part.name if part.name and part.name != part.kind else f"{part.kind} {i}"
                r_key = self._attachment(part, label, body, trace, ctx, missing, skipped, temps)
                if isinstance(r_key, tuple):          # speech: (role, transcript)
                    r_key, said = r_key
                    if said is not None:
                        transcript = said if transcript is None else f"{transcript}\n{said}"
                first_ability = first_ability or r_key
            if transcript is not None:
                if body:
                    ctx.append(("What the user said in the voice message", transcript))
                else:
                    body = transcript
            if not body:
                if parts:
                    names = ", ".join(p.name for p in parts)
                    body = f"(The user sent {names} without a message.)"
                else:
                    return self._fail("The message is empty.", trace, t_all, status=400)
            # what the text asks for: route once, note what can't be done
            t0 = time.monotonic()
            if intent.IMAGE_GEN_WORDS.search(body) and ent.is_set("image_gen"):
                rt = {"role": "image_gen", "reason": "asks for an image", "media": [], "text": body, "via": "keyword"}
            elif intent.AUDIO_GEN_WORDS.search(body) and ent.is_set("audio_gen"):
                rt = {"role": "audio_gen", "reason": "asks for music or sound", "media": [], "text": body,
                      "via": "keyword"}
            else:
                # attached document text counts toward the reasoning gate's size threshold
                doc_chars = sum(len(t or "") for lab, t in ctx if lab != "What the user said in the voice message")
                rt = ent.route_turn(body, exists=lambda p: False, context_chars=doc_chars)
            if "router_ok" in rt:
                trace.append({"role": "intent_router", "label": R.label("intent_router"),
                              "why": "route the turn" + ("" if rt["router_ok"] else
                                                         f" (failed: {rt.get('router_error')})"),
                              "ok": rt["router_ok"], "ms": rt.get("router_ms") or int((time.monotonic() - t0) * 1000),
                              "target": ent.target("intent_router")})
            if rt["role"] in R.ROLE_KEYS and rt["role"] not in ("persona", "reasoning", "coding", "image_gen",
                                                                 "audio_gen", "guard_translate"):
                rt = dict(rt, role="persona", media=[])   # media in the text was handled above
            if intent.IMAGE_GEN_WORDS.search(body) and not ent.is_set("image_gen"):
                missing.append("image_gen")
            if intent.AUDIO_GEN_WORDS.search(body) and not ent.is_set("audio_gen"):
                missing.append("audio_gen")
            speak = bool(want_audio) or bool(SPEAK_WORDS.search(body))
            if speak and not ent.is_set("tts"):
                missing.append("tts")
            limits = self._limits(missing, skipped)
            if limits:
                ctx.append(("What you can't do this turn", limits + " A note telling the user which ability to set "
                            "is added under your reply automatically, so don't repeat its wording."))
            csys = client_system if (client_system and self.s.get("client_system") == "append") else None
            if csys:
                csys = "=== THE APP'S OWN INSTRUCTIONS (follow them unless they conflict with who you are) ===\n" + csys
            out = ent.turn(body, history, route=rt, context=ctx, on_token=on_token, client_system=csys,
                           turn_key=turn_key, temperature=temperature, max_tokens=max_tokens, defer_store=True)
        finally:
            for p in parts:
                if p.temp and p.path:
                    temps.append(p.path)
            for p in temps:
                try:
                    os.unlink(p)
                except OSError:
                    pass
        out = out or {}
        route = (out.get("route") or rt or {}).get("role")
        for a in out.get("abilities") or []:
            trace.append({"role": a["role"], "label": R.label(a["role"]), "why": "ability for the reply",
                          "ok": a["ok"], "ms": int((a.get("latency") or 0) * 1000), "target": a.get("target")})
        for t in out.get("trace") or []:
            # the tool loop's entries are {name, outcome, latency_sec}; older ones {tool, error, latency}
            tname = t.get("name") or t.get("tool") if isinstance(t, dict) else None
            if tname:
                ok_t = (t.get("outcome") == "ok") if "outcome" in t else not t.get("error")
                trace.append({"role": "mcp_tool", "label": "MCP tool", "why": tname, "ok": ok_t,
                              "ms": int(((t.get("latency_sec") if t.get("latency_sec") is not None
                                          else t.get("latency")) or 0) * 1000),
                              "target": tname, **({"error": str(t.get("reason"))[:200]} if t.get("reason")
                                                   else {})})
        res = {"ok": False, "text": "", "reply": "", "error": None, "blocked": out.get("blocked"),
               "route": first_ability or route, "text_route": route, "via": (rt or {}).get("via"),
               "route_reason": (rt or {}).get("reason"),
               "media": [], "audio": None, "transcript": transcript, "trace": trace, "missing": missing,
               "notes": skipped, "streamed": bool(out.get("streamed")), "usage": {}, "result": out.get("result"),
               "tools": [t.get("name") or t.get("tool") for t in (out.get("trace") or [])
                         if isinstance(t, dict) and (t.get("name") or t.get("tool"))],
               "answered_by": out.get("answered_by"), "status": 502}
        if out.get("blocked"):
            res["text"] = res["reply"] = "I can't help with that one."
            res["ms"] = int((time.monotonic() - t_all) * 1000)
            return res
        for f in out.get("files") or []:
            mime = mimetypes.guess_type(f)[0] or "application/octet-stream"
            res["media"].append({"kind": kind_of(mime, f), "path": f, "mime": mime, "name": os.path.basename(f)})
        r = out.get("result")
        step_rows(trace, r, out.get("answered_by") or "persona", ent)
        if r is None or not r.ok:
            pre = out.get("pre")
            err = (r.error if r is not None else None) or (pre.error if pre is not None else None) or "no reply"
            plain = getattr(r, "plain_error", None) if r is not None else None
            if plain:
                res["error"] = plain
                res["upstream"] = f"the persona couldn't answer: {err}"
            else:
                res["error"] = f"the persona couldn't answer: {err}"
            res["ms"] = int((time.monotonic() - t_all) * 1000)
            return res
        fb = getattr(r, "fallback", None)
        trace.append({"role": out.get("answered_by") or "persona", "label": R.label(out.get("answered_by") or
                                                                                     "persona"),
                      "why": "the reply" + (f" (fallback: {fb['model']})" if fb else ""), "ok": True,
                      "ms": int((r.latency or 0) * 1000),
                      "target": fb["model"] if fb else ent.target(out.get("answered_by") or "persona")})
        res["ok"] = True
        res["status"] = 200
        res["usage"] = dict(r.usage or {})
        res["reply"] = r.text
        note = self._limits(missing, skipped, for_user=True)
        res["text"] = r.text + (f"\n\n({note})" if note else "")
        res["note"] = note
        if speak and ent.is_set("tts"):
            say = None
            if SPEAK_WORDS.search(body) and not want_audio:
                m = SPEAK_QUOTE.search(body)
                say = (m.group(1) or m.group(2)).strip() if m else None
            say = speakable(say or r.text, int(self.s.get("tts_max_chars") or 1500))
            if say:
                tr = self._run("tts", trace, "speak the reply", text=say, **({"voice": voice} if voice else {}))
                if tr.ok and (tr.files or tr.data):
                    path = tr.files[0] if tr.files else None
                    res["audio"] = {"path": path, "data": tr.data if isinstance(tr.data, (bytes, bytearray)) else None,
                                    "transcript": say, "mime": "audio/wav"}
                    if path:
                        res["media"].append({"kind": "audio", "path": path, "mime": "audio/wav",
                                             "name": os.path.basename(path), "spoken": True})
                else:
                    res["tts_error"] = tr.error or "no audio came back"
                    res["text"] += f"\n\n(Speaking failed: {res['tts_error']}.)"
        store = out.get("store")
        if callable(store):
            if defer_store:
                res["finish"] = store
            else:
                try:
                    store()
                except Exception as e:  # noqa: BLE001 - saving must never lose the reply
                    res["notes"].append(f"memory store failed: {str(e)[:120]}")
        res["ms"] = int((time.monotonic() - t_all) * 1000)
        return res

    def _fail(self, msg, trace, t_all, status=503):
        return {"ok": False, "text": "", "reply": "", "error": msg, "blocked": None, "route": None,
                "media": [], "audio": None, "transcript": None, "trace": trace, "missing": [], "notes": [],
                "streamed": False, "usage": {}, "result": None, "tools": [], "status": status,
                "ms": int((time.monotonic() - t_all) * 1000)}

    @staticmethod
    def _limits(missing, skipped, for_user=False):
        bits = []
        seen = set()
        for k in missing:
            if k in seen:
                continue
            seen.add(k)
            bits.append(f"to {WHAT.get(k, k)}, set the {R.label(k)} role" if for_user else
                        f"you can't {WHAT.get(k, k)} (no {R.label(k)} ability is set)")
        out = "; ".join(bits)
        if bits and for_user:
            out = out[0].upper() + out[1:] + " in the testbed (launcher R)"
        if skipped:
            s = "Skipped: " + "; ".join(dict.fromkeys(skipped))
            out = f"{out}. {s}" if out else s
        return out

    def _attachment(self, part, label, body, trace, ctx, missing, skipped, temps):
        """Run the ability one attachment needs; its result goes into ctx.
        -> role key used (or (role, transcript) for speech), or None."""
        ent = self.ent
        kind = part.kind
        if kind == "file":
            return self._file(part, label, body, trace, ctx, missing, skipped, temps)
        if kind == "image":
            role, want = self.image_role(body, trace)
            if not role:
                missing.append("vision")
                return None
            if role == "vision":
                prompt = ("Describe this image in detail for someone who can't see it. Also note anything that "
                          f"helps answer: {body}") if body else None
            elif role == "chart_parser":
                prompt = body or None
            else:
                prompt = None
            r = self._run(role, trace, f"{kind}: {label}", image=part.ref, prompt=prompt)
            head = {"vision": "What you see in", "ocr": "Text you read in", "chart_parser": "Chart data from"}[role]
            ctx.append((f"{head} {label}", r.text if r.ok else f"(couldn't look at it: {r.error})"))
            return role
        if kind == "video":
            if not ent.is_set("video"):
                missing.append("video")
                return None
            r = self._run("video", trace, f"video: {label}", video=part.ref, prompt=body or None)
            ctx.append((f"What you saw in the video {label}", r.text if r.ok else f"(couldn't watch it: {r.error})"))
            return "video"
        if kind == "audio":
            if part.url:
                skipped.append(f"{label}: audio links aren't fetched; attach the audio itself")
                return None
            role = self.audio_role(body, trace)
            if not role:
                missing.append("asr")
                return None
            path = part.path
            if role == "asr":
                from . import perf
                with perf.stage("convert", target="ffmpeg") as st:
                    path, tmp, note = to_wav(part.path)
                    if not tmp and note:
                        st["note"] = note
                if tmp:
                    temps.append(path)
                r = self._run("asr", trace, f"speech: {label}", audio=path)
                if not r.ok:
                    ctx.append((f"Voice message {label}", f"(couldn't make out the speech: {r.error})"))
                    return "asr"
                said = (r.text or "").strip()
                if not said:
                    ctx.append((f"Audio {label}", "(no speech in it)"))
                    return "asr", None
                return "asr", said
            r = self._run("omni_audio", trace, f"sound: {label}", audio=path, prompt=body or None)
            ctx.append((f"What you heard in {label}", r.text if r.ok else f"(couldn't listen to it: {r.error})"))
            return "omni_audio"
        return None

    def _file(self, part, label, body, trace, ctx, missing, skipped, temps):
        cap = int(self.s.get("attach_max_chars") or 20000)
        if part.url:
            skipped.append(f"{label}: file links aren't fetched; attach the file itself")
            return None
        path, mime, low = part.path, part.mime or "", part.path.lower()
        if mime == "application/pdf" or low.endswith(".pdf"):
            with open(path, "rb") as f:
                data = f.read()
            text, jpegs = pdf_extract(data, int(self.s.get("pdf_ocr_pages") or 3))
            if text:
                ctx.append((f"The document {label} (text layer)", clip(text, cap)))
                trace.append({"role": "document", "label": "PDF text", "why": label, "ok": True, "ms": 0,
                              "target": "built-in reader"})
                return "document"
            if jpegs:
                role = self._first_set("ocr", "vision")
                if not role:
                    missing.append("ocr")
                    return None
                pages = []
                for n, jpg in enumerate(jpegs, 1):
                    url = "data:image/jpeg;base64," + base64.b64encode(jpg).decode("ascii")
                    r = self._run(role, trace, f"scanned page {n} of {label}", image=url, prompt=None if
                                  role == "ocr" else "Transcribe all the text on this page.")
                    pages.append(f"[page {n}]\n{r.text if r.ok else '(unreadable: ' + str(r.error) + ')'}")
                ctx.append((f"Text you read in the scanned document {label}", clip("\n\n".join(pages), cap)))
                return role
            skipped.append(f"{label}: no readable text layer or page images (send the pages as images for OCR)")
            return None
        if low.endswith(OFFICE_EXT):
            text = office_text(path)
            if text:
                ctx.append((f"The document {label}", clip(text, cap)))
                trace.append({"role": "document", "label": "document text", "why": label, "ok": True, "ms": 0,
                              "target": "built-in reader"})
                return "document"
            skipped.append(f"{label}: couldn't read text from it")
            return None
        if looks_text(path, mime):
            ctx.append((f"The file {label}", read_text_file(path, cap)))
            trace.append({"role": "document", "label": "file text", "why": label, "ok": True, "ms": 0,
                          "target": "built-in reader"})
            return "document"
        ext = os.path.splitext(part.name or path)[1] or mime or "this type"
        skipped.append(f"{label}: {ext} files aren't supported (images, audio, video, PDF, Office documents and "
                       "text/code files are)")
        return None
