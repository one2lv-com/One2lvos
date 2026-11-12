"""Roles backed by a tool on the connected MCP server.

A role stored as {"backend": "mcp", "tool": name, "arg_map": {...}} runs
that tool with tools/call instead of a model. arg_map maps the role's own
inputs (text, image, audio, prompt, query, passages, ...) to the tool's
argument names from its inputSchema. auto_arg_map() builds a sensible
default; an argument name may end in :path, :base64, :dataurl or :text to
force how a file input is sent.

Pure helpers plus call_role_tool(); no prompts here.
"""

import base64
import json
import mimetypes
import os
import re
import time

from . import config
from .mcp import MCPError, result_to_text, validate_arguments

# role key -> the inputs that role hands to its backend (first = primary)
ROLE_INPUTS = {
    "intent_router": ["text"],
    "persona": ["text"],
    "reasoning": ["text"],
    "coding": ["text"],
    "vision": ["image", "prompt"],
    "ocr": ["image", "prompt"],
    "chart_parser": ["image", "prompt"],
    "video": ["video", "prompt"],
    "asr": ["audio", "language"],
    "omni_audio": ["audio", "prompt"],
    "tts": ["text", "voice", "language", "reference_audio", "reference_text"],
    "image_gen": ["prompt"],
    "audio_gen": ["prompt", "duration"],
    "embedding": ["text"],
    "reranker": ["query", "passages"],
    "guard_translate": ["text", "target_language", "task"],
}
FILE_INPUTS = {"image", "video", "audio", "reference_audio"}

# role input -> argument names that usually mean it, best first
SYNONYMS = {
    "text": ["text", "input", "message", "content", "prompt", "query", "utterance", "sentence", "q", "input_text"],
    "prompt": ["prompt", "question", "instruction", "description", "text", "query", "input", "caption"],
    "image": ["image", "image_url", "image_data", "image_base64", "image_path", "img", "picture", "photo",
              "url", "file", "path", "data"],
    "video": ["video", "video_url", "video_path", "video_data", "clip", "url", "file", "path"],
    "audio": ["audio", "audio_url", "audio_data", "audio_base64", "audio_path", "audio_file", "sound", "file",
              "url", "path", "data"],
    "language": ["language", "lang", "language_code", "locale"],
    "voice": ["voice", "voice_name", "voice_id", "speaker", "speaker_id"],
    "reference_audio": ["reference_audio", "audio_prompt", "reference", "ref_audio", "speaker_wav", "voice_sample",
                        "prompt_audio", "clone_audio", "voice_clone", "sample_audio", "reference_wav", "sample"],
    "reference_text": ["reference_text", "audio_prompt_transcript", "transcript", "prompt_text", "ref_text",
                       "reference_transcript"],
    "duration": ["duration", "seconds", "length", "duration_sec", "duration_seconds"],
    "query": ["query", "q", "question", "search", "text"],
    "passages": ["passages", "documents", "docs", "texts", "candidates", "items", "chunks", "corpus"],
    "target_language": ["target_language", "target_lang", "target", "to", "to_language", "tgt_lang"],
    "task": ["task", "mode", "action", "operation"],
}
# words that make an argument a poor match for an input even if the name fits
AVOID = {"reference_audio": ("text", "transcript"), "audio": ("prompt", "reference"), "text": ("voice",)}


def _props(tool):
    schema = (tool or {}).get("inputSchema") or {}
    return schema.get("properties") or {}, list(schema.get("required") or [])


def _arg_name(spec):
    return (spec or "").split(":", 1)[0]


def auto_arg_map(role_key, tool):
    """{role_input: tool_arg} guessed from the tool's inputSchema."""
    props, required = _props(tool)
    inputs = ROLE_INPUTS.get(role_key, ["text"])
    used, out = set(), {}
    norm = {p: re.sub(r"[^a-z0-9]", "_", p.lower()) for p in props}
    for inp in inputs:                                   # exact synonym match, best first
        for syn in SYNONYMS.get(inp, [inp]):
            hit = next((p for p in props if norm[p] == syn and p not in used), None)
            if hit and not any(a in norm[hit] for a in AVOID.get(inp, ()) if a != syn):
                out[inp] = hit
                used.add(hit)
                break
    for inp in inputs:                                   # then a name that contains the input word
        if inp in out:
            continue
        key = inp.split("_")[0]
        hit = next((p for p in props if p not in used and key in norm[p]
                    and not any(a in norm[p] for a in AVOID.get(inp, ()))), None)
        if hit:
            out[inp] = hit
            used.add(hit)
    primary = inputs[0]
    if primary not in out:                               # last resort: first free required string arg
        for p in required + list(props):
            if p not in used and (props.get(p) or {}).get("type", "string") in ("string", None):
                out[primary] = p
                used.add(p)
                break
    return out


def unmapped_required(tool, arg_map):
    props, required = _props(tool)
    mapped = {_arg_name(v) for v in (arg_map or {}).values()}
    return [r for r in required if r not in mapped]


# ---------------------------------------------------------------------------
# Building arguments
# ---------------------------------------------------------------------------
def _encoding(spec, prop):
    if ":" in spec:
        return spec.split(":", 1)[1].lower()
    name = _arg_name(spec).lower()
    desc = str((prop or {}).get("description", "")).lower()
    fmt = str((prop or {}).get("format", "")).lower()
    if "path" in name or "local path" in desc or "file path" in desc:
        return "path"
    if "base64" in name or "b64" in name or ("base64" in desc and "data url" not in desc and "url" not in name):
        return "base64"
    if fmt == "uri" or "url" in name or "url" in desc or "uri" in name:
        return "dataurl"
    return "dataurl"


def _file_value(ref, enc, default_mime):
    ref = (ref or "").strip()
    if ref.startswith(("http://", "https://")):
        return ref if enc != "base64" else ref
    if ref.startswith("data:"):
        return ref.split(",", 1)[1] if enc == "base64" else ref
    if enc == "path":
        return ref
    if not os.path.isfile(ref):
        raise ValueError(f"file not found: {ref}")
    with open(ref, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("ascii")
    if enc == "base64":
        return b64
    mime = mimetypes.guess_type(ref)[0] or default_mime
    return f"data:{mime};base64,{b64}"


def _coerce(value, prop):
    t = (prop or {}).get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), None)
    if isinstance(value, list):
        if t == "string":
            return "\n\n".join(str(v) for v in value)
        if t == "array":
            item_t = ((prop or {}).get("items") or {}).get("type")
            if item_t == "object":
                return [{"text": str(v)} for v in value]
        return value
    if t == "integer":
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return value
    if t == "number":
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if t == "array" and isinstance(value, str):
        return [value]
    return value


DEFAULT_MIME = {"image": "image/png", "video": "video/mp4", "audio": "audio/wav", "reference_audio": "audio/wav"}


def build_arguments(tool, arg_map, inputs):
    """Role inputs -> tools/call arguments. Unmapped or empty inputs are
    skipped. Raises ValueError for a missing file."""
    props, _ = _props(tool)
    args = {}
    for inp, spec in (arg_map or {}).items():
        value = inputs.get(inp)
        if value is None or value == "" or value == []:
            continue
        name = _arg_name(spec)
        if not name:
            continue
        prop = props.get(name)
        if inp in FILE_INPUTS:
            value = _file_value(value, _encoding(spec, prop), DEFAULT_MIME[inp])
        args[name] = _coerce(value, prop)
    return args


# ---------------------------------------------------------------------------
# Reading results
# ---------------------------------------------------------------------------
EXT = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav", "audio/mpeg": "mp3", "audio/mp3": "mp3",
       "audio/ogg": "ogg", "audio/flac": "flac", "audio/mp4": "m4a", "image/png": "png", "image/jpeg": "jpg",
       "image/webp": "webp", "image/gif": "gif", "video/mp4": "mp4"}
MEDIA_URL = re.compile(r"https?://[^\s\"'<>)]+?\.(?:wav|mp3|ogg|flac|m4a|png|jpe?g|webp|gif|mp4)(?:\?[^\s\"'<>)]*)?",
                       re.I)


def _sniff(data):
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3"):
        return "mp3"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"fLaC":
        return "flac"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _b64(s):
    try:
        s = s.split(",", 1)[1] if s.startswith("data:") else s
        return base64.b64decode(s, validate=False)
    except (ValueError, TypeError):
        return None


def _media_in_json(obj, depth=0):
    """(bytes, ext) and URLs from JSON-ish text results."""
    blobs, urls = [], []
    if depth > 5:
        return blobs, urls
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if isinstance(v, str):
                if v.startswith("data:") and ";base64," in v[:80]:
                    data = _b64(v)
                    mime = v[5:v.index(";")]
                    if data:
                        blobs.append((data, EXT.get(mime) or _sniff(data) or "bin"))
                elif any(w in lk for w in ("base64", "b64", "audio", "image", "wav", "png", "data")) \
                        and len(v) > 200 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", v[:400]):
                    data = _b64(v)
                    if data and _sniff(data):
                        blobs.append((data, _sniff(data)))
                elif v.startswith(("http://", "https://")) and MEDIA_URL.fullmatch(v):
                    urls.append(v)
            else:
                b, u = _media_in_json(v, depth + 1)
                blobs += b
                urls += u
    elif isinstance(obj, list):
        for v in obj:
            b, u = _media_in_json(v, depth + 1)
            blobs += b
            urls += u
    return blobs, urls


def extract(result, fetch=None, prefix="mcp", max_fetch=20 * 1024 * 1024):
    """tools/call result -> (text, [saved file paths], notes).

    Image/audio content blocks, embedded resource blobs, data: URLs and
    base64 fields in JSON text are decoded and saved to output/. Media URLs
    are downloaded with fetch(url) -> bytes when given."""
    text = result_to_text(result)
    blobs, urls, notes = [], [], []
    for block in (result or {}).get("content") or []:
        if not isinstance(block, dict):
            continue
        bt = block.get("type")
        if bt in ("image", "audio") and block.get("data"):
            data = _b64(block["data"])
            if data:
                blobs.append((data, EXT.get(block.get("mimeType", "")) or _sniff(data) or "bin"))
        elif bt == "resource":
            res = block.get("resource") or {}
            if res.get("blob"):
                data = _b64(res["blob"])
                if data:
                    blobs.append((data, EXT.get(res.get("mimeType", "")) or _sniff(data) or "bin"))
            elif res.get("uri", "").startswith(("http://", "https://")):
                urls.append(res["uri"])
        elif bt == "resource_link" and str(block.get("uri", "")).startswith(("http://", "https://")):
            urls.append(block["uri"])
        elif bt == "text":
            t = str(block.get("text", "")).strip()
            if t[:1] in "{[":
                try:
                    b, u = _media_in_json(json.loads(t))
                    blobs += b
                    urls += u
                except ValueError:
                    pass
            elif t.startswith("data:") and ";base64," in t[:80]:
                data = _b64(t)
                if data:
                    blobs.append((data, EXT.get(t[5:t.index(";")]) or _sniff(data) or "bin"))
                    text = text.replace(t, "[media saved]")
            urls += MEDIA_URL.findall(t)
    if result and result.get("structuredContent") is not None:
        b, u = _media_in_json(result["structuredContent"])
        blobs += b
        urls += u
    files = []
    for i, (data, ext) in enumerate(blobs):
        path = config.output_path(f"{prefix}_{int(time.time() * 1000)}_{i}.{ext}")
        with open(path, "wb") as f:
            f.write(data)
        files.append(path)
    seen = set()
    for url in urls:
        if url in seen or not fetch:
            continue
        seen.add(url)
        try:
            data = fetch(url)
        except Exception as e:  # network errors are reported, not raised
            notes.append(f"could not download {url}: {e}")
            continue
        if not data or len(data) > max_fetch:
            notes.append(f"skipped {url}: empty or too large")
            continue
        ext = _sniff(data) or url.rsplit(".", 1)[-1].split("?")[0][:4] or "bin"
        path = config.output_path(f"{prefix}_{int(time.time() * 1000)}_{len(files)}.{ext}")
        with open(path, "wb") as f:
            f.write(data)
        files.append(path)
    if len(text) > 4000 and files:   # don't print a wall of base64 back
        text = text[:400] + f"... [{len(text)} chars; media saved]"
    return text, files, notes


def parse_vector(text):
    """Embedding tools: a JSON list of numbers, or {embedding|vector|data}."""
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None
    for _ in range(4):
        if isinstance(obj, list) and obj and all(isinstance(x, (int, float)) for x in obj):
            return [float(x) for x in obj]
        if isinstance(obj, list) and obj:
            obj = obj[0]
        elif isinstance(obj, dict):
            obj = obj.get("embedding") or obj.get("vector") or obj.get("data") or obj.get("embeddings")
        else:
            return None
    return None


def parse_rankings(text, n):
    """Rerank tools: [(index, score)] best first from rankings/results JSON,
    or a plain list of indices. None when it can't be read."""
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None
    if isinstance(obj, dict):
        obj = obj.get("rankings") or obj.get("results") or obj.get("data") or obj.get("ranking")
    if not isinstance(obj, list):
        return None
    out = []
    for pos, r in enumerate(obj):
        if isinstance(r, int) and 0 <= r < n:
            out.append((r, float(-pos)))
        elif isinstance(r, dict):
            idx = r.get("index", r.get("id", r.get("corpus_id")))
            score = r.get("logit", r.get("score", r.get("relevance_score", -pos)))
            try:
                if 0 <= int(idx) < n:
                    out.append((int(idx), float(score)))
            except (TypeError, ValueError):
                continue
    if not out:
        return None
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def call_role_tool(mcp, tool_name, arg_map, inputs, fetch=None, prefix="mcp"):
    """Run a role's MCP tool. Returns dict(ok, text, files, latency, error,
    notes, arguments). Never raises."""
    t0 = time.monotonic()
    out = {"ok": False, "text": "", "files": [], "latency": 0.0, "error": None, "notes": [], "arguments": {}}
    try:
        tools = mcp.tools or mcp.list_tools()
        tool = next((t for t in tools if t.get("name") == tool_name), None)
        if tool is None:
            tools = mcp.list_tools()
            tool = next((t for t in tools if t.get("name") == tool_name), None)
        if tool is None:
            out["error"] = f"the MCP server no longer lists the tool '{tool_name}'"
            return out
        args = build_arguments(tool, arg_map, inputs)
        out["arguments"] = {k: (v if not isinstance(v, str) or len(v) < 120 else v[:60] + f"...[{len(v)} chars]")
                            for k, v in args.items()}
        errs = validate_arguments(tool.get("inputSchema") or {}, args)
        if errs:
            out["error"] = "arguments don't match the tool's schema: " + "; ".join(errs[:4]) + \
                           " (edit the role's argument mapping)"
            return out
        result = mcp.call_tool(tool_name, args)
    except ValueError as e:
        out["error"] = str(e)
        return out
    except MCPError as e:
        out["error"] = f"MCP server: {e}"
        return out
    finally:
        out["latency"] = round(time.monotonic() - t0, 3)
    text, files, notes = extract(result, fetch=fetch, prefix=prefix)
    out.update(text=text, files=files, notes=notes, latency=round(time.monotonic() - t0, 3))
    if result.get("isError"):
        out["error"] = "tool reported an error: " + (text[:300] or "(no message)")
        return out
    out["ok"] = True
    return out
