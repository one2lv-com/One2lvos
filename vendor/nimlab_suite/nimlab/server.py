"""OpenAI-compatible test server for the Entity Orchestrator Testbed (v3.3).

Starts a local HTTP server (stdlib ThreadingHTTPServer) that any
OpenAI-compatible UI can talk to (Open WebUI, SillyTavern, LibreChat,
Chatbox, the openai SDK, curl). It generates a base URL, its own API key and
model names, and sends each request to the testbed's setup:

  testbed-agent        the full orchestrator pipeline (intent router, role
                       routing, memory with reranker, guardrail, tools)
  testbed-<role>       one name per configured role (testbed-persona,
                       testbed-vision, testbed-tts ...), calling that role's
                       backend (model endpoint or MCP tool)
  <verified model id>  optional: the verified 200 OK models passed straight
                       through (chat, embeddings, rerank)

Routes (Bearer key required except OPTIONS and /health):
  GET  /v1/models, /v1/models/<id>
  POST /v1/chat/completions   (stream true/false; image, audio, video parts)
  POST /v1/embeddings         (float or base64)
  POST /v1/rerank             (Cohere/Jina style)
  POST /v1/audio/speech       (TTS role, cloned voice included)
  POST /v1/audio/transcriptions (ASR role, multipart upload)
  POST /v1/images/generations (text-to-image role)

The generated key is the only key a client ever sees: the NVIDIA key never
leaves the phone except to NVIDIA. Settings live in data/server_settings.json
(owner-only file); the request log in data/server_requests.jsonl, with every
line passed through core.redact so no key lands in it.
"""

import base64
import binascii
import contextlib
import email.parser
import email.policy
import hmac
import http.client
import io
import json
import math
import os
import queue
import re
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__ as VERSION, callpage, config, roles as R, store, unified
from .core import mask, redact
SETTINGS_FILE = "server_settings.json"
LOG_FILE = "server_requests.jsonl"
LOG_KEEP = 1000          # lines kept when the log is trimmed
LOG_TRIM_AT = 2000
KEY_PREFIX = "sk-testbed-"
AGENT = "agent"
OPENAI_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse",
                 "default", ""}
LANG_MAP = {"en": "en-US", "es": "es-US", "fr": "fr-FR", "de": "de-DE", "it": "it-IT", "ja": "ja-JP",
            "zh": "zh-CN", "ko": "ko-KR", "pt": "pt-BR", "ru": "ru-RU", "hi": "hi-IN", "ar": "ar-AR"}

# what each role answers on, as an OpenAI model "type"
CHAT = "chat"
EMBED = "embedding"
RERANK = "rerank"
SPEECH = "audio.speech"
TRANSCRIBE = "audio.transcription"
IMAGE = "image"
AUDIO_GEN = "audio.generation"
ROLE_TYPES = {
    "intent_router": CHAT, "persona": CHAT, "reasoning": CHAT, "coding": CHAT, "guard_translate": CHAT,
    "vision": CHAT, "ocr": CHAT, "chart_parser": CHAT, "video": CHAT, "omni_audio": CHAT,
    "asr": TRANSCRIBE, "tts": SPEECH, "image_gen": IMAGE, "audio_gen": AUDIO_GEN,
    "embedding": EMBED, "reranker": RERANK,
}
TEXT_ROLES = ("intent_router", "persona", "reasoning", "coding")
IMAGE_ROLES = ("vision", "ocr", "chart_parser")
# which types each route accepts
ROUTE_TYPES = {
    "chat": (CHAT, IMAGE, AUDIO_GEN, TRANSCRIBE),
    "embeddings": (EMBED,),
    "rerank": (RERANK,),
    "speech": (SPEECH,),
    "transcriptions": (TRANSCRIBE,),
    "images": (IMAGE,),
}
ROUTE_HINT = {CHAT: "/v1/chat/completions", EMBED: "/v1/embeddings", RERANK: "/v1/rerank",
              SPEECH: "/v1/audio/speech", TRANSCRIBE: "/v1/audio/transcriptions", IMAGE: "/v1/images/generations",
              AUDIO_GEN: "/v1/chat/completions"}


# ---------------------------------------------------------------------------
# Settings (data/server_settings.json)
# ---------------------------------------------------------------------------
def new_key():
    return KEY_PREFIX + secrets.token_urlsafe(24)


def default_settings():
    return {
        "schema": 2,
        "port": 8765,
        "bind": "127.0.0.1",        # localhost only; "0.0.0.0" when lan is on
        "lan": False,
        "api_key": new_key(),
        "key_created_at": config.timestamp(),
        "model_prefix": "testbed-",
        # v3.4: one model name serves the whole stack as one entity
        "model_name": "testbed",
        "entity": {
            "client_system": "append",   # append | ignore: the UI's own system message
            "trace": "field",            # off | field (testbed_trace) | content (also under the reply)
            "media": "url",              # url (hosted /v1/files/<id>) | data (data: URLs inline)
            "media_auth": "link",        # link (unguessable id) | key (Bearer key or ?key= needed)
            "media_ttl_hours": 24,
            "media_keep": 200,
            "attach_max_chars": 20000,
            "pdf_ocr_pages": 3,
            "image_router": True,
            "call_page": True,
        },
        "log_requests": True,
        "log_to_console": True,
        # v3.7.1 self-test: seconds per basic check (models, chat, identity), per
        # heavy check (picture + audio in one message, image generation), and
        # whether setup runs the heavy checks (default no: they need every
        # media role awake and can take minutes)
        "self_test_timeout_sec": 90,
        "self_test_heavy_timeout_sec": 240,
        "setup_full_self_test": False,
        "cors_origin": "*",
        "max_body_mb": 25,
        "stream_chunk_words": 3,
        # MCP tool calls the agent makes for a client, when the testbed's
        # "confirm each tool call" is on: nobody can answer that prompt for a
        # remote UI, so "deny" refuses them; "allow" runs them unasked. The
        # optional allowed_tools / blocked_tools overrides apply either way.
        "agent_tool_calls": "deny",
        # v3.6.1: off / quick (trycloudflare.com) / named; see nimlab/tunnel.py
        "tunnel": {"tool": "cloudflared", "mode": "off", "auto_start": False,
                   "named": {"method": "token", "tunnel": "", "credentials_file": "", "hostname": ""}},
    }


def settings_path():
    return store.path(SETTINGS_FILE)


def log_path():
    return store.path(LOG_FILE)


def _write_private(path, data):
    # Not store.save: that redacts anything key-shaped, and this file is the
    # one place the generated key has to live in full. Owner-only.
    config.save_json(path, data)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_settings():
    """Settings with every missing field filled in; the file (and the key)
    is created on first use."""
    p = settings_path()
    raw = config.load_json(p, None)
    base = default_settings()
    if not isinstance(raw, dict):
        _write_private(p, base)
        return base
    changed = False
    for k, v in base.items():
        if k not in raw:
            raw[k] = v
            changed = True
        elif isinstance(v, dict) and isinstance(raw[k], dict):
            for k2, v2 in v.items():
                if k2 not in raw[k]:
                    raw[k][k2] = v2
                    changed = True
    if int(raw.get("schema") or 1) < 2:
        raw["schema"] = 2
        changed = True
    exp = raw.get("expose")
    if exp is not None and not isinstance(exp, dict):
        raw.pop("expose", None)     # v3.7.2: a broken legacy value is dropped, never a crash
        changed = True
    elif isinstance(exp, dict) and exp.get("roles", "off") in ("off", None, False, "none", "") \
            and not exp.get("verified") and exp.get("agent", True) in (True, None):
        # v3.7.2: an expose block that only says the defaults is legacy noise
        raw.pop("expose", None)
        changed = True
    if not isinstance(raw.get("api_key"), str) or len(raw["api_key"]) < 20:
        raw["api_key"] = new_key()
        raw["key_created_at"] = config.timestamp()
        changed = True
    if changed:
        _write_private(p, raw)
    return raw


def save_settings(s):
    _write_private(settings_path(), s)


def regenerate_key(s=None):
    s = s or load_settings()
    s["api_key"] = new_key()
    s["key_created_at"] = config.timestamp()
    save_settings(s)
    return s


def set_lan(s, on):
    s["lan"] = bool(on)
    s["bind"] = "0.0.0.0" if on else "127.0.0.1"
    return s


# ---------------------------------------------------------------------------
# Request log
# ---------------------------------------------------------------------------
_log_lock = threading.Lock()


def log_request(entry, path=None):
    path = path or log_path()
    line = redact(json.dumps(entry, ensure_ascii=False))
    with _log_lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > LOG_TRIM_AT:
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(lines[-LOG_KEEP:])
        except OSError:
            pass


def read_log(limit=50, path=None):
    path = path or log_path()
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out[-limit:] if limit else out


def format_log(rows, color=False):
    """Log lines for a screen. color=True colours them (status by class,
    latency by speed, model ids, errors); the saved log never has colour."""
    from . import colors as C
    lines = []
    for r in rows:
        ts = str(r.get('ts'))[11:19]
        st = f"{r.get('status', '?'):>3}"
        meth = f"{r.get('method', ''):<7}"
        pth = f"{r.get('path', ''):<26}"
        mdl = f"{str(r.get('model') or '-'):<28}"
        lat = f"{r.get('latency_ms', 0):>7} ms"
        stream = '  stream' if r.get('stream') else ''
        err = '  ' + str(r.get('error'))[:80] if r.get('error') else ''
        if color:
            on = dict(on=True)
            ts, meth = C.paint(ts, "dim", **on), C.paint(meth, "accent", "bold", **on)
            pth, mdl = C.paint(pth, "path", **on), C.paint(mdl, "model", **on)
            st = C.http(st) if C.enabled() else st
            lat = C.paint(lat, C.PALETTE["lat_fast" if r.get('latency_ms', 0) < 1500 else "lat_mid"
                          if r.get('latency_ms', 0) < 4000 else "lat_slow" if r.get('latency_ms', 0) < 10000
                          else "lat_crawl"], **on)
            stream = C.paint(stream, "info", **on)
            err = C.paint(err, "err", **on)
        lines.append(f"{ts}  {st}  {meth} {pth} {mdl} {lat}{stream}{err}")
    return lines


def log_summary(rows):
    if not rows:
        return "no requests logged yet"
    ok = [r for r in rows if 200 <= int(r.get("status") or 0) < 300]
    lat = sorted(r.get("latency_ms", 0) for r in ok) or [0]
    return (f"{len(rows)} request(s), {len(ok)} OK, {len(rows) - len(ok)} failed; "
            f"median OK latency {lat[len(lat) // 2]} ms")


# ---------------------------------------------------------------------------
# Model names
# ---------------------------------------------------------------------------
def role_model_name(key, prefix="testbed-"):
    return prefix + key.replace("_", "-")


def _verified_type(rec):
    url = (rec.get("url") or "").lower()
    kind = f"{rec.get('kind') or ''} {rec.get('catalog_kind') or ''}".lower()
    if url.endswith("/chat/completions"):
        return CHAT
    if url.endswith("/embeddings") or "embed" in kind:
        return EMBED
    if "rerank" in url or "rerank" in kind:
        return RERANK
    return None


def main_model(s):
    """The one model name that serves the whole stack."""
    return (s.get("model_name") or "testbed").strip() or "testbed"


def role_pick(s):
    """Legacy (manual config only): server_settings.expose.roles."""
    exp = s.get("expose")
    pick = exp.get("roles", "off") if isinstance(exp, dict) else "off"
    if pick in ("all", True, "*"):
        return list(R.ROLE_KEYS)
    if pick in (None, False, "off", "none", "") or not isinstance(pick, list):
        return []
    return [k for k in R.ROLE_KEYS if k in pick]


def exposed_models(ent, s, verified=None, aliases=False):
    """{name: entry}. entry: id, type, source (agent|role|verified), role,
    target (what it calls), plus `rec` for verified pass-through.

    v3.7.2: the endpoint serves ONE model name (server_settings.model_name)
    that wraps the whole stack; every route dispatches it to the right role
    (see model_entry). expose.* is legacy: no default, not in setup or the
    settings menu. A hand-added expose.roles / expose.verified still lists
    debug names beside the one model, and expose.agent can no longer hide it.
    aliases=True also returns names that are accepted but not listed
    (testbed-agent, from v3.3)."""
    prefix = s.get("model_prefix") or "testbed-"
    exp = s.get("expose") or {}
    if not isinstance(exp, dict):
        exp = {}
    name = main_model(s)    # always listed: a legacy expose.agent off is ignored
    out = {name: {"id": name, "type": CHAT, "source": AGENT, "role": None,
                  "target": "the whole stack as one entity (persona voice; every other role is an ability)"}}
    if aliases and prefix + AGENT not in out:
        out[prefix + AGENT] = dict(out[name], id=prefix + AGENT, alias=True)
    for k in role_pick(s):
        if not ent.is_set(k):
            continue
        name = role_model_name(k, prefix)
        out[name] = {"id": name, "type": ROLE_TYPES.get(k, CHAT), "source": "role", "role": k,
                     "target": f"{R.label(k)}: {ent.target(k)}"}
    if exp.get("verified"):
        recs = verified if verified is not None else store.verified_models()
        for mid, rec in sorted(recs.items()):
            t = _verified_type(rec)
            if not t or mid in out:
                continue
            out[mid] = {"id": mid, "type": t, "source": "verified", "role": None,
                        "target": f"verified 200 OK: {rec.get('url')}", "rec": rec}
    return out


def unset_roles(ent, s):
    return [k for k in R.ROLE_KEYS if not ent.is_set(k)]


def memory_line(mem=None):
    """Where the served entity's long-term memory lives. It is kept in the
    server, so every UI that connects to this endpoint shares it."""
    from . import ltm
    if mem is not None:
        st = mem.status()
        if not st["online"] and st["backend"] != "off":
            return f"OFFLINE ({st['offline_reason']}); replies work without memory"
        return st["where"] + f"; scope {st['scope']}"
    try:
        lt = ltm.settings_from(config.load_cluster_config().get("memory_settings"))
    except Exception:  # noqa: BLE001
        return "unknown"
    if lt.get("backend") == "off":
        return "off"
    return ltm.describe(lt) + f"; scope {lt.get('scope', 'shared')} (kept in the server, shared by every client)"


def call_token(s):
    """The token in the /call page link. Derived from the API key, so a new
    key (serve regen-key) retires old call links too."""
    return hmac.new(s["api_key"].encode(), b"nimlab-call-page", "sha256").hexdigest()[:32]


# ---------------------------------------------------------------------------
# Addresses and connection details
# ---------------------------------------------------------------------------
def lan_ip():
    """The phone's Wi-Fi address, or None. A UDP connect sends no packet; it
    only asks the OS which interface would be used."""
    for target in (("10.255.255.255", 1), ("192.168.255.255", 1), ("8.8.8.8", 80)):
        try:
            sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sk.connect(target)
                ip = sk.getsockname()[0]
            finally:
                sk.close()
            if ip and not ip.startswith("127.") and ip != "0.0.0.0":
                return ip
        except OSError:
            continue
    return None


def base_urls(s, port=None, public=None):
    port = port or s.get("port")
    urls = {"local": f"http://127.0.0.1:{port}/v1"}
    ip = lan_ip()
    if ip:
        urls["lan"] = f"http://{ip}:{port}/v1"
    if public:
        urls["public"] = public.rstrip("/") + "/v1"
    return urls


def connection_block(s, models, port=None, public=None, running=None):
    urls = base_urls(s, port, public)
    by_type = {}
    for m in models.values():
        by_type.setdefault(m["type"], []).append(m["id"])
    lines = ["=" * 70, "  OPENAI-COMPATIBLE TEST SERVER" + ("" if running is None else
                                                              ("  [running]" if running else "  [stopped]")),
             "=" * 70,
             f"Base URL (this phone):   {urls['local']}"]
    if s.get("lan"):
        lines.append(f"Base URL (same Wi-Fi):   {urls.get('lan') or '(no Wi-Fi address found)'}")
    else:
        lines.append("Base URL (same Wi-Fi):   off (localhost only; turn on LAN access in settings)")
    if urls.get("public"):
        lines.append(f"Base URL (public):       {urls['public']}")
    lines.append(f"API key:                 {s['api_key']}")
    main = main_model(s)
    if main in models:
        lines.append(f"Model:                   {main}   (the whole stack as one entity)")
        lines.append(f"Endpoint:                POST {urls['local']}/chat/completions")
        lines.append("                         text, images, audio, video and files in; text, images and voice out")
    if (s.get("entity") or {}).get("call_page", True):
        lines.append(f"Call page:               {urls['local'][:-3]}/call?t={call_token(s)}")
    lines.append("Memory:                  " + memory_line())
    extra = [m for m in models.values() if m["id"] != main]
    if extra:
        lines.append("Legacy debug names (hand-set server_settings.expose; remove it to list only the one model):")
        for m in extra:
            lines.append(f"  {m['id']:<44} {m['type']}")
    lines.append("-" * 70)
    lines.append("Most UIs want three things: the base URL, the API key and a model name.")
    lines.append("If a UI asks for the host without /v1, drop the /v1.")
    return "\n".join(lines)


def ui_configs(s, models, port=None, public=None):
    """Copy-ready config text for common UIs."""
    urls = base_urls(s, port, public)
    remote = urls.get("public") or (urls.get("lan") if s.get("lan") else None)
    base = remote or urls["local"]
    main = main_model(s)
    chat = [m["id"] for m in models.values() if m["type"] == CHAT]
    chat = ([main] if main in chat else []) + [m for m in chat if m != main]
    first = chat[0] if chat else (next(iter(models)) if models else main)
    key = s["api_key"]
    compact = json.dumps({"base_url": base, "api_key": key, "model": first}, separators=(",", ":"))
    full = json.dumps({"name": "NIM Testbed", "base_url": base, "api_key": key, "models": list(models)}, indent=2)
    host = base[:-3] if base.endswith("/v1") else base
    yaml_models = ", ".join(f'"{m}"' for m in chat) or f'"{first}"'
    parts = [
        f"One model, one endpoint: model = {first}, base URL = {base}, key below.", "",
        "JSON (one line, QR-friendly: paste it into any QR generator):",
        compact, "",
        "JSON (full):", full, "",
        "Open WebUI:   add an OpenAI API connection with URL = " + base + " and the key above, then pick " +
        first + ".",
        "SillyTavern:  Chat Completion, source Custom (OpenAI-compatible), endpoint = " + base + ", key above, "
        "model = " + first + ".",
        "Chatbox:      add an OpenAI-API-compatible provider; API host = " + host + " (or " + base +
        " if it asks for the full base), key above, model = " + first + ".",
        "LibreChat (librechat.yaml):",
        "  endpoints:",
        "    custom:",
        "      - name: \"NIM Testbed\"",
        "        apiKey: \"" + key + "\"",
        "        baseURL: \"" + base + "\"",
        "        models:",
        "          default: [" + yaml_models + "]",
        "          fetch: true", "",
        "curl:",
        "  curl " + base + "/chat/completions -H 'Authorization: Bearer " + key + "' "
        "-H 'Content-Type: application/json' -d '{\"model\":\"" + first +
        "\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}'", "",
        "Python (openai package):",
        "  from openai import OpenAI",
        "  c = OpenAI(base_url=\"" + base + "\", api_key=\"" + key + "\")",
        "  print(c.chat.completions.create(model=\"" + first + "\", messages=[{\"role\": \"user\", \"content\": \"hi\"}])"
        ".choices[0].message.content)",
    ]
    if not remote:
        parts.append("")
        parts.append("Note: these use 127.0.0.1, which only works for a UI on this phone. For a UI on another "
                     "device, turn on LAN access (same Wi-Fi) or a tunnel.")
    return "\n".join(parts)


def copy_to_clipboard(text):
    """termux-clipboard-set when Termux:API is installed. True on success."""
    exe = shutil.which("termux-clipboard-set")
    if not exe:
        return False
    try:
        subprocess.run([exe], input=text.encode("utf-8"), timeout=10, check=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------
class ApiError(Exception):
    def __init__(self, status, message, etype="invalid_request_error", code=None, param=None, trace=None,
                 upstream=None, exc=None, stages=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.etype = etype
        self.code = code
        self.param = param
        # v3.7.1: what the bug log keeps for a 5xx (never sent to the client)
        self.trace = trace
        self.upstream = upstream
        self.exc = exc
        self.stages = stages
        self.bug_id = None

    def body(self):
        err = {"message": redact(self.message), "type": self.etype, "param": self.param, "code": self.code}
        if self.bug_id:
            err["message"] = f"{err['message']} (bug {self.bug_id}: nimlab bugs show {self.bug_id})"
            err["bug_id"] = self.bug_id
        return {"error": err}


def internal_error(e):
    """An unexpected exception -> a 500 ApiError that keeps the stack for the bug log."""
    return ApiError(500, f"internal error: {type(e).__name__}: {e}", etype="server_error", exc=e)


def split_content(content):
    """OpenAI message content -> (text, [(kind, ref_or_payload)]). kind:
    image (URL), video (URL), audio ((bytes, format))."""
    if content is None:
        return "", []
    if isinstance(content, str):
        return content, []
    if not isinstance(content, list):
        return str(content), []
    texts, media = [], []
    for p in content:
        if isinstance(p, str):
            texts.append(p)
            continue
        if not isinstance(p, dict):
            continue
        t = p.get("type")
        if t in ("text", "input_text"):
            texts.append(p.get("text") or "")
        elif t in ("image_url", "input_image", "video_url"):
            kind = "video" if t == "video_url" else "image"
            v = p.get("video_url" if kind == "video" else "image_url")
            url = v.get("url") if isinstance(v, dict) else v
            if url:
                media.append((kind, _client_url(url)))
        elif t == "input_audio":
            a = p.get("input_audio") or {}
            try:
                data = base64.b64decode(a.get("data") or "", validate=False)
            except (binascii.Error, ValueError):
                raise ApiError(400, "input_audio.data is not valid base64", param="messages")
            media.append(("audio", (data, (a.get("format") or "wav").lower())))
    return "\n".join(x for x in texts if x), media


def _client_url(url):
    """Only http(s) and data: URLs from clients: a bare path would make the
    server read a file on the phone and send it on."""
    if not isinstance(url, str) or not url.strip().lower().startswith(("http://", "https://", "data:")):
        raise ApiError(400, "media URLs must be http(s):// or data: URLs (local file paths are refused)",
                       param="messages", code="invalid_media_url")
    return url.strip()


def _text_messages(messages):
    """(system_text, [user/assistant messages with plain-text content])."""
    system, out = [], []
    for m in messages:
        role = m.get("role")
        text, _ = split_content(m.get("content"))
        if role in ("system", "developer"):
            if text:
                system.append(text)
        elif role in ("user", "assistant"):
            out.append({"role": role, "content": text})
        elif role == "tool":
            out.append({"role": "user", "content": f"(tool result) {text}"})
    return "\n\n".join(system), out


def _last_user(messages):
    for m in reversed(messages):
        if m.get("role") == "user":
            return split_content(m.get("content"))
    return "", []


def _estimate_tokens(text):
    return max(1, len((text or "").split())) if text else 0


def _usage(result, prompt_text):
    u = dict(getattr(result, "usage", None) or {})
    p = u.get("prompt_tokens") if isinstance(u.get("prompt_tokens"), int) else _estimate_tokens(prompt_text)
    c = u.get("completion_tokens") if isinstance(u.get("completion_tokens"), int) else \
        _estimate_tokens(getattr(result, "text", ""))
    return {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}


def _audio_tempfile(data, fmt):
    fd, p = tempfile.mkstemp(prefix="testbed_audio_", suffix="." + (fmt or "wav"))
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return p


def _mime_of(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] == b"RIFF":
        return "audio/wav"
    if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
        return "audio/mpeg"
    return "application/octet-stream"


def _read_file(p):
    try:
        with open(p, "rb") as f:
            return f.read()
    except (OSError, TypeError):
        return None


def parse_multipart(body, content_type):
    """multipart/form-data -> {name: str | (filename, bytes)} (stdlib email;
    the cgi module is gone in Python 3.13)."""
    if "multipart/form-data" not in (content_type or "").lower():
        raise ApiError(400, "expected multipart/form-data")
    msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
        b"Content-Type: " + content_type.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
    if not msg.is_multipart():
        raise ApiError(400, "could not read the multipart body")
    out = {}
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        data = part.get_payload(decode=True) or b""
        fname = part.get_filename()
        if fname is not None:
            out[name] = (fname, data)
        else:
            out[name] = data.decode("utf-8", "replace")
    return out


def float_b64(vec):
    return base64.b64encode(struct.pack(f"<{len(vec)}f", *vec)).decode("ascii")


def convert_audio(wav, fmt):
    """WAV -> mp3/opus/aac/flac with ffmpeg, pcm with the wave module.
    (bytes, mime, note)."""
    fmt = (fmt or "wav").lower()
    if fmt == "wav":
        return wav, "audio/wav", None
    if fmt == "pcm":
        try:
            with wave.open(io.BytesIO(wav)) as w:
                return w.readframes(w.getnframes()), "audio/pcm", None
        except (wave.Error, EOFError):
            return wav, "audio/wav", "could not read the WAV; returned it as is"
    mime = {"mp3": "audio/mpeg", "opus": "audio/ogg", "aac": "audio/aac", "flac": "audio/flac"}.get(fmt)
    exe = shutil.which("ffmpeg")
    if not mime or not exe:
        return wav, "audio/wav", f"returned WAV ({'install ffmpeg: pkg install ffmpeg' if mime else 'unknown format'}" \
                                 f" for {fmt})"
    ff = {"opus": ["-c:a", "libopus", "-f", "ogg"], "aac": ["-f", "adts"]}.get(fmt, ["-f", fmt])
    try:
        r = subprocess.run([exe, "-loglevel", "error", "-i", "pipe:0"] + ff + ["pipe:1"], input=wav,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if r.returncode == 0 and r.stdout:
            return r.stdout, mime, None
    except (OSError, subprocess.SubprocessError):
        pass
    return wav, "audio/wav", f"ffmpeg could not make {fmt}; returned WAV"


# ---------------------------------------------------------------------------
# The app: maps OpenAI requests onto the testbed
# ---------------------------------------------------------------------------
class Reply:
    """What a chat request produced: text plus testbed details. streamed is
    the text already sent token by token (stream=true); audio is the
    message.audio object for the audio output modality; trace is which
    abilities ran (testbed_trace)."""

    def __init__(self, text, usage, finish="stop", info=None, streamed="", audio=None, trace=None):
        self.text = text
        self.usage = usage
        self.finish = finish
        self.info = info or {}
        self.streamed = streamed
        self.audio = audio
        self.trace = trace


class MediaStore:
    """Files the entity made (images, audio, spoken replies), hosted at
    /v1/files/<id>. The id is 24 random URL-safe bytes, so a link works as
    its own password (markdown images in a UI can't send a key); with
    entity.media_auth = key the Bearer key (or ?key=) is required too."""

    def __init__(self, ttl_hours=24, keep=200):
        self.ttl = float(ttl_hours or 24) * 3600
        self.keep = int(keep or 200)
        self.items = {}
        self._lock = threading.Lock()

    def add(self, path=None, data=None, mime=None, name=None):
        if data is None:
            data = _read_file(path)
        if not data:
            return None
        mime = mime or unified.sniff_mime(data, name or path or "")
        ext = os.path.splitext(name or path or "")[1] or {"audio/wav": ".wav", "image/png": ".png",
                                                          "image/jpeg": ".jpg", "audio/mpeg": ".mp3"}.get(mime, "")
        mid = secrets.token_urlsafe(24) + ext
        with self._lock:
            self._expire()
            self.items[mid] = {"data": bytes(data), "mime": mime, "ts": time.time(), "name": name or
                               os.path.basename(path or "") or mid}
        return mid

    def get(self, mid):
        with self._lock:
            self._expire()
            return self.items.get(mid)

    def _expire(self):
        now = time.time()
        for k in [k for k, v in self.items.items() if now - v["ts"] > self.ttl]:
            del self.items[k]
        while len(self.items) > self.keep:
            del self.items[min(self.items, key=lambda k: self.items[k]["ts"])]


class TestbedApp:
    def __init__(self, ent, settings=None, verified=None, log_path_=None):
        self.ent = ent
        self.settings = settings if settings is not None else load_settings()
        self._verified = verified
        self.log_path = log_path_
        self.lock = threading.RLock()   # one backend call at a time: memory and history are shared
        self.files = {}                 # name -> path, images this server made (for response_format=url)
        es = self.entity_settings()
        self.media = MediaStore(es.get("media_ttl_hours"), es.get("media_keep"))
        self.public_url = None
        self.quiet = False              # True: no console lines (the testbed menu; the log file still fills)

    # -- models ---------------------------------------------------------
    def models(self):
        return exposed_models(self.ent, self.settings, self._verified)

    def entity_settings(self):
        return dict(default_settings()["entity"], **(self.settings.get("entity") or {}))

    def model_entry(self, name, route):
        if not name or not isinstance(name, str):
            raise ApiError(400, "you must provide a model parameter", param="model", code="missing_model")
        models = self.models()
        e = models.get(name) or exposed_models(self.ent, self.settings, self._verified, aliases=True).get(name)
        if e is not None and e["source"] == AGENT and route != "chat":
            # the one model name works on the compatibility routes too
            key = {"embeddings": "embedding", "rerank": "reranker", "speech": "tts", "transcriptions": "asr",
                   "images": "image_gen"}[route]
            if not self.ent.is_set(key):
                raise ApiError(400, f"'{name}' cannot do this yet: the {R.label(key)} role isn't set. Set it with "
                                    f"`nimlab setup roles` (or launcher R)", param="model", code="role_not_set")
            return {"id": name, "type": ROLE_TYPES[key], "source": "role", "role": key,
                    "target": f"{R.label(key)}: {self.ent.target(key)}"}
        if e is None:
            raise ApiError(404, f"The model '{name}' does not exist or is not exposed by this test server. "
                                f"Available: {', '.join(models) or 'none'}", param="model", code="model_not_found")
        if e["type"] not in ROUTE_TYPES[route]:
            raise ApiError(400, f"'{name}' is a {e['type']} model; use {ROUTE_HINT.get(e['type'], 'another route')}",
                           param="model", code="model_not_supported")
        return e

    def check_key(self, headers, query_key=None, call_ok=False):
        """call_ok: the /call page's token (derived from the key) is accepted
        too, on the routes that page uses."""
        key = self.settings.get("api_key") or ""
        auth = headers.get("Authorization") or ""
        given = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        given = given or (headers.get("x-api-key") or headers.get("api-key") or "").strip() or (query_key or "")
        from . import selfadmin as SA
        SA.clear_request()
        if call_ok and given and key and hmac.compare_digest(given.encode(), call_token(self.settings).encode()):
            SA.set_request(False, "call-page", "call")
            return
        if given and SA.is_admin_key(given):
            # the endpoint admin key: the owner, allowed to use the self-admin tools
            SA.set_request(True, (headers.get("X-Testbed-User") or "admin-key").strip()[:80], "api-admin")
            return
        if not given:
            raise ApiError(401, "Missing API key. Send it as 'Authorization: Bearer <key>'.",
                           etype="invalid_request_error", code="missing_api_key")
        if not key or not hmac.compare_digest(given.encode(), key.encode()):
            raise ApiError(401, f"Incorrect API key provided: {mask(given)}", etype="invalid_request_error",
                           code="invalid_api_key")
        SA.set_request(False, (headers.get("X-Testbed-User") or "api").strip()[:80], "api")

    def model_list(self):
        now = int(time.time())
        return {"object": "list", "data": [self._model_obj(e, now) for e in self.models().values()]}

    @staticmethod
    def _model_obj(e, now=None):
        return {"id": e["id"], "object": "model", "created": now or int(time.time()), "owned_by": "nim-testbed",
                "testbed": {"type": e["type"], "source": e["source"], "role": e["role"], "target": e["target"]}}

    # -- chat ------------------------------------------------------------
    def chat(self, body, base_url=None, on_token=None):
        msgs = body.get("messages")
        if not isinstance(msgs, list) or not msgs:
            raise ApiError(400, "'messages' must be a non-empty list", param="messages")
        e = self.model_entry(body.get("model"), "chat")
        temp = body.get("temperature")
        temp = 0.7 if not isinstance(temp, (int, float)) else float(temp)
        mt = body.get("max_completion_tokens") or body.get("max_tokens")
        mt = int(mt) if isinstance(mt, (int, float)) and mt > 0 else 1024
        with self.lock:
            if e["source"] == AGENT:
                return self._entity(msgs, body, base_url, on_token, temp, mt)
            if e["source"] == "verified":
                return self._verified_chat(e, msgs, temp, mt)
            return self._role_chat(e["role"], msgs, temp, mt)

    def _fail(self, r, what):
        raise ApiError(502, f"{what} failed: {r.error or 'no answer'}", etype="upstream_error",
                       code=f"upstream_{r.status}" if r.status else "upstream_error", upstream=r.error)

    def _role_chat(self, key, msgs, temp, mt):
        ent = self.ent
        text, media = _last_user(msgs)
        info = {"role": key, "backend": ent.backend(key), "target": ent.target(key)}
        tmp = []
        try:
            if key in TEXT_ROLES:
                system, plain = _text_messages(msgs)
                if system:   # the role's own prompt first, then the UI's system prompt
                    base = ent.build_system_prompt(key, with_tools=False)
                    system = f"{base}\n\n{system}" if base else system
                r = ent.run_role(key, messages=plain, text=text, system=system or None, temperature=temp,
                                 max_tokens=mt)
            elif key in IMAGE_ROLES:
                img = next((ref for k, ref in media if k == "image"), None)
                if not img:
                    raise ApiError(400, f"{R.label(key)} needs an image: send an image_url part", param="messages")
                r = ent.run_role(key, image=img, prompt=text or None)
            elif key == "video":
                vid = next((ref for k, ref in media if k in ("video", "image")), None)
                if not vid:
                    raise ApiError(400, "the video role needs a video_url part", param="messages")
                r = ent.run_role(key, video=vid, prompt=text or None)
            elif key in ("omni_audio", "asr"):
                aud = next((ref for k, ref in media if k == "audio"), None)
                if not aud:
                    raise ApiError(400, f"{R.label(key)} needs audio: send an input_audio part", param="messages")
                p = _audio_tempfile(aud[0], aud[1])
                tmp.append(p)
                r = ent.run_role(key, audio=p, prompt=text or None)
            elif key == "guard_translate":
                r = ent.run_role(key, text=text)
            elif key == "image_gen":
                r = ent.run_role(key, prompt=text)
                if r.ok:
                    r.text = self._image_markdown(r) or r.text
            elif key == "audio_gen":
                r = ent.run_role(key, prompt=text)
                if r.ok and r.files:
                    r.text = "Audio saved on the phone: " + ", ".join(r.files)
            else:
                raise ApiError(400, f"{R.label(key)} does not answer chat requests", param="model")
        finally:
            for p in tmp:
                try:
                    os.unlink(p)
                except OSError:
                    pass
        if not r.ok:
            self._fail(r, R.label(key))
        return Reply(r.text, _usage(r, text), info=dict(info, latency_sec=round(r.latency or 0, 3)))

    def _image_markdown(self, r):
        out = []
        for p in (r.files or [])[:4]:
            data = _read_file(p)
            if data:
                out.append(f"![image](data:{_mime_of(data)};base64,{base64.b64encode(data).decode('ascii')})")
        return "\n\n".join(out)

    def _verified_chat(self, e, msgs, temp, mt):
        rec = e["rec"]
        clean = [m for m in msgs if m.get("role") in ("system", "user", "assistant", "developer")]
        clean = [dict(m, role="system") if m.get("role") == "developer" else m for m in clean]
        clean = [{"role": m["role"], "content": m.get("content") or ""} for m in clean]
        r = self.ent.client.chat(rec.get("api_model_id") or e["id"], clean, temp, mt, url=rec.get("url"))
        if not r.ok:
            self._fail(r, e["id"])
        text, _ = _last_user(msgs)
        return Reply(r.text, _usage(r, text), info={"verified": e["id"], "latency_sec": round(r.latency or 0, 3)})

    # -- the one entity --------------------------------------------------
    def _entity(self, msgs, body, base_url, on_token, temp, mt):
        """The whole stack behind one model name: nimlab.unified.Mind with
        the persona writing the reply and every other role an ability."""
        ent = self.ent
        es = self.entity_settings()
        idx = max((i for i, m in enumerate(msgs) if m.get("role") == "user"), default=None)
        if idx is None:
            raise ApiError(400, "no user message in 'messages'", param="messages")
        system = "\n\n".join(unified.history_text(m.get("content")) for m in msgs
                              if m.get("role") in ("system", "developer") and m.get("content"))
        history = []
        for m in msgs[:idx]:
            r = m.get("role")
            if r in ("user", "assistant"):
                t = unified.history_text(m.get("content"))
                if t:
                    history.append({"role": r, "content": t})
            elif r == "tool":
                history.append({"role": "user", "content": f"(tool result) {unified.history_text(m.get('content'))}"})
        try:
            text, parts, notes = unified.parse_content(msgs[idx].get("content"))
        except unified.PartError as e:
            raise ApiError(400, str(e), param="messages",
                           code="invalid_media_url" if "path" in str(e) or "URL" in str(e) else None)
        mods = body.get("modalities") or []
        aud = body.get("audio") if isinstance(body.get("audio"), dict) else {}
        want_audio = "audio" in mods
        voice = aud.get("voice")
        voice = None if not isinstance(voice, str) or voice.lower() in OPENAI_VOICES else voice
        mind = unified.Mind(ent, {k: es[k] for k in ("client_system", "attach_max_chars", "pdf_ocr_pages",
                                                     "image_router") if k in es})
        saved_confirm = ent.confirm_fn
        allow = str(self.settings.get("agent_tool_calls") or "deny").lower() == "allow"
        ent.confirm_fn = lambda call: allow
        streamed = []
        mem = ent.memory

        def tok(t):
            streamed.append(t)
            on_token(t)
        # long-term memory lives here, in the server: every client of this
        # endpoint shares it (memory scope "user" keeps clients apart by the
        # OpenAI `user` field or an X-Testbed-User header)
        client_id = body.get("user") if isinstance(body.get("user"), str) and body.get("user").strip() else None
        scope_cm = mem.scoped(client_id) if mem is not None else contextlib.nullcontext()
        if mem is not None:
            mem.last_turn = {}
        try:
            from . import environment as ENV
            who = str(body.get("user") or "") if isinstance(body, dict) else ""
            ch = ("telegram_voice" if want_audio else "telegram") if who.startswith("telegram:") else \
                ("voice" if want_audio else "endpoint")
            with scope_cm, ENV.channel(ch):
                res = mind.run(text, parts, history, client_system=system or None, on_token=tok if on_token else None,
                               want_audio=want_audio, turn_key=unified.turn_key(msgs[:idx + 1]), notes=notes,
                               voice=voice, temperature=temp, max_tokens=mt)
        finally:
            ent.confirm_fn = saved_confirm
        trace = [{k: t.get(k) for k in ("role", "label", "why", "ok", "ms", "target", "error") if k in t}
                 for t in res["trace"]]
        # v3.8.3: the bug record keeps the failed step's model, upstream host, status, body and fallbacks
        bug_trace = [{k: t.get(k) for k in ("role", "label", "why", "ok", "ms", "target", "error", "model", "host",
                                              "status", "body", "attempts", "fallbacks") if k in t}
                     for t in res["trace"]]
        info = {"route": res.get("route"), "text_route": res.get("text_route"), "via": res.get("via"),
                "route_reason": res.get("route_reason"),
                "answered_by": res.get("answered_by"), "tools": res.get("tools") or []}
        if mem is not None:
            st = mem.status()
            info["memory"] = {"backend": st["backend"], "online": st["online"], "scope": st["scope"],
                              "recalled": mem.last_turn.get("recalled", 0), "stored": mem.last_turn.get("stored", 0)}
            if client_id and st["scope"] == "user":
                info["memory"]["client"] = client_id[:64]
        if res.get("transcript"):
            info["transcript"] = res["transcript"]
        if res.get("missing"):
            info["missing_roles"] = sorted(set(res["missing"]))
        if res.get("blocked"):
            info["blocked"] = res["blocked"]
            return Reply(f"[guardrail] {res['blocked']}", {"prompt_tokens": _estimate_tokens(text),
                                                          "completion_tokens": 0,
                                                          "total_tokens": _estimate_tokens(text)},
                         finish="content_filter", info=info, trace=trace)
        if not res["ok"]:
            raise ApiError(res.get("status") or 502, res.get("error") or "the entity produced no reply",
                           etype="upstream_error" if (res.get("status") or 502) >= 500 else "invalid_request_error",
                           code="role_not_set" if "isn't set" in (res.get("error") or "") else "upstream_error",
                           trace=bug_trace, upstream=res.get("upstream") or res.get("error"),
                           stages=res.get("stages_ms"))
        txt = res["text"]
        links = []
        for m in res["media"]:
            if m.get("spoken") and want_audio:
                continue   # it rides in message.audio
            link = self._media_link(m, base_url, es)
            if link:
                links.append(link)
        if links:
            txt = txt.rstrip() + "\n\n" + "\n\n".join(links)
        audio = None
        if want_audio and res.get("audio"):
            a = res["audio"]
            raw = a.get("data") or _read_file(a.get("path"))
            if raw:
                data, _mime, note = convert_audio(bytes(raw), aud.get("format") or "wav")
                audio = {"id": "audio_" + uuid.uuid4().hex[:24], "data": base64.b64encode(data).decode("ascii"),
                         "transcript": a.get("transcript") or "", "expires_at": int(time.time()) + 3600}
                if note:
                    info["audio_note"] = note
        if es.get("trace") == "content" and trace:
            txt += "\n\n_stack: " + ", ".join(f"{t['label']} {t['ms']} ms" for t in trace) + "_"
        r = res.get("result")
        u = _usage(r, text) if r is not None else {"prompt_tokens": _estimate_tokens(text), "completion_tokens":
                                                   _estimate_tokens(txt), "total_tokens": 0}
        return Reply(txt, u, info=info, streamed="".join(streamed), audio=audio, trace=trace)

    def _media_link(self, m, base_url, es):
        data = _read_file(m["path"])
        if not data:
            return None
        mime = m.get("mime") or _mime_of(data)
        kind = m.get("kind") or unified.kind_of(mime)
        if es.get("media") == "data":
            url = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
        else:
            mid = self.media.add(data=data, mime=mime, name=m.get("name"))
            url = f"{(base_url or '').rstrip('/')}/files/{mid}"
        if kind == "image":
            return f"![generated image]({url})"
        label = "Listen" if kind == "audio" else "Download"
        return f"[{label}: {m.get('name') or kind}]({url})"

    def responses(self, body, base_url=None):
        """/v1/responses (non-streaming): input text / input_image /
        input_file / input_audio, mapped onto the same entity."""
        if body.get("stream"):
            raise ApiError(400, "stream is not supported on /v1/responses here; use /v1/chat/completions with "
                                "stream true", param="stream", code="unsupported_stream")
        inp = body.get("input")
        msgs = []
        if body.get("instructions"):
            msgs.append({"role": "system", "content": str(body["instructions"])})
        if isinstance(inp, str):
            msgs.append({"role": "user", "content": inp})
        elif isinstance(inp, list):
            for it in inp:
                if not isinstance(it, dict):
                    continue
                if it.get("type") in (None, "message") and it.get("role"):
                    msgs.append({"role": it["role"], "content": it.get("content")})
                elif it.get("type") in ("input_text", "input_image", "input_file", "input_audio"):
                    msgs.append({"role": "user", "content": [it]})
        if not msgs or not any(m["role"] == "user" for m in msgs):
            raise ApiError(400, "'input' must be a string or a list of input items", param="input")
        chat_body = {"model": body.get("model"), "messages": msgs, "user": body.get("user"),
                     "max_tokens": body.get("max_output_tokens") or 1024, "temperature": body.get("temperature")}
        rep = self.chat(chat_body, base_url)
        rid = "resp_" + uuid.uuid4().hex
        u = rep.usage or {}
        out = {"id": rid, "object": "response", "created_at": int(time.time()), "status": "completed",
               "model": body.get("model"), "output": [{"type": "message", "id": "msg_" + uuid.uuid4().hex[:24],
                                                       "status": "completed", "role": "assistant",
                                                       "content": [{"type": "output_text", "text": rep.text,
                                                                    "annotations": []}]}],
               "output_text": rep.text,
               "usage": {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0),
                         "total_tokens": u.get("total_tokens", 0)}}
        if rep.trace is not None and self.entity_settings().get("trace") != "off":
            out["testbed_trace"] = rep.trace
        return out

    # -- other routes -------------------------------------------------------
    def embeddings(self, body):
        e = self.model_entry(body.get("model"), "embeddings")
        inp = body.get("input")
        if isinstance(inp, str):
            inputs = [inp]
        elif isinstance(inp, list) and inp and all(isinstance(x, str) for x in inp):
            inputs = inp
        else:
            raise ApiError(400, "'input' must be a string or a list of strings (token arrays are not supported)",
                           param="input")
        if len(inputs) > 256:
            raise ApiError(400, "at most 256 inputs per request", param="input")
        itype = body.get("input_type") or "query"
        with self.lock:
            if e["source"] == "verified":
                rec = e["rec"]
                r = self.ent.client.embed(rec.get("api_model_id") or e["id"], inputs, input_type=itype,
                                          url=rec.get("url"))
                if not r.ok:
                    self._fail(r, e["id"])
                vecs = r.data
            else:
                vecs = []
                for t in inputs:
                    r = self.ent.run_role("embedding", text=t, input_type=itype)
                    if not r.ok or not r.data:
                        self._fail(r, "Embedding role")
                    vecs.append(list(r.data))
        b64 = body.get("encoding_format") == "base64"
        tokens = sum(_estimate_tokens(t) for t in inputs)
        return {"object": "list", "model": e["id"],
                "data": [{"object": "embedding", "index": i, "embedding": float_b64(v) if b64 else v}
                         for i, v in enumerate(vecs)],
                "usage": {"prompt_tokens": tokens, "total_tokens": tokens}}

    def rerank(self, body):
        e = self.model_entry(body.get("model"), "rerank")
        q = body.get("query")
        docs = body.get("documents") or body.get("passages")
        if isinstance(q, dict):
            q = q.get("text")
        if not isinstance(q, str) or not isinstance(docs, list) or not docs:
            raise ApiError(400, "'query' (string) and 'documents' (non-empty list) are required")
        texts = [d if isinstance(d, str) else (d or {}).get("text", "") for d in docs]
        with self.lock:
            if e["source"] == "verified":
                rec = e["rec"]
                r = self.ent.client.rerank(rec.get("api_model_id") or e["id"], q, texts, url=rec.get("url"))
            else:
                r = self.ent.run_role("reranker", query=q, passages=texts)
        if not r.ok:
            self._fail(r, "Reranker")
        ranks = []
        for item in r.data or []:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                ranks.append((int(item[0]), float(item[1])))
            elif isinstance(item, int):
                ranks.append((item, float(len(texts) - len(ranks))))
        top = body.get("top_n")
        if isinstance(top, int) and top > 0:
            ranks = ranks[:top]
        ret = body.get("return_documents", True)
        return {"id": "rerank-" + uuid.uuid4().hex[:12], "model": e["id"],
                "results": [dict({"index": i, "relevance_score": s},
                                 **({"document": {"text": texts[i]}} if ret and 0 <= i < len(texts) else {}))
                            for i, s in ranks],
                "usage": {"total_tokens": _estimate_tokens(q) + sum(_estimate_tokens(t) for t in texts)}}

    def speech(self, body):
        e = self.model_entry(body.get("model"), "speech")
        text = body.get("input")
        if not isinstance(text, str) or not text.strip():
            raise ApiError(400, "'input' text is required", param="input")
        voice = body.get("voice")
        voice = None if not isinstance(voice, str) or voice.lower() in OPENAI_VOICES else voice
        with self.lock:
            r = self.ent.run_role(e["role"] or "tts", text=text, voice=voice)
        if not r.ok:
            self._fail(r, "Neural TTS role")
        wav = r.data if isinstance(r.data, (bytes, bytearray)) else None
        if wav is None and r.files:
            wav = _read_file(r.files[0])
        if not wav:
            raise ApiError(502, "the TTS role returned no audio", etype="upstream_error")
        data, mime, note = convert_audio(bytes(wav), body.get("response_format") or "wav")
        sp = self.ent.spec("tts")
        clone = R.clone_text(self.ent.roles.get("tts"))
        return data, mime, {"note": note, "cloned": bool((sp.get("voice_clone") or {}).get("path")),
                            "clone": clone}

    def transcriptions(self, body, content_type):
        form = parse_multipart(body, content_type)
        e = self.model_entry(form.get("model"), "transcriptions")
        f = form.get("file")
        if not isinstance(f, tuple) or not f[1]:
            raise ApiError(400, "'file' upload is required", param="file")
        fname, data = f
        ext = (os.path.splitext(fname)[1] or ".wav").lstrip(".").lower()
        lang = (form.get("language") or "").strip()
        lang = LANG_MAP.get(lang.lower(), lang) if lang else None
        p = _audio_tempfile(data, ext)
        try:
            with self.lock:
                r = self.ent.run_role(e["role"] or "asr", audio=p, language=lang)
        finally:
            try:
                os.unlink(p)
            except OSError:
                pass
        if not r.ok:
            self._fail(r, "ASR role")
        fmt = form.get("response_format") or "json"
        if fmt in ("text", "srt", "vtt"):
            return r.text, "text/plain; charset=utf-8"
        if fmt == "verbose_json":
            return {"task": "transcribe", "language": lang or "", "duration": None, "text": r.text,
                    "segments": []}, None
        return {"text": r.text}, None

    def images(self, body, base_url):
        e = self.model_entry(body.get("model"), "images")
        prompt = body.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ApiError(400, "'prompt' is required", param="prompt")
        n = body.get("n") if isinstance(body.get("n"), int) else 1
        n = max(1, min(n, 4))
        fmt = body.get("response_format") or "b64_json"
        data = []
        with self.lock:
            for _ in range(n):
                r = self.ent.run_role(e["role"] or "image_gen", prompt=prompt)
                if not r.ok:
                    self._fail(r, "Text-to-Image role")
                for p in r.files:
                    blob = _read_file(p)
                    if not blob:
                        continue
                    if fmt == "url":
                        name = os.path.basename(p)
                        self.files[name] = p
                        data.append({"url": f"{base_url}/files/{name}", "revised_prompt": prompt})
                    else:
                        data.append({"b64_json": base64.b64encode(blob).decode("ascii"), "revised_prompt": prompt})
        if not data:
            raise ApiError(502, "the image role returned no image", etype="upstream_error")
        return {"created": int(time.time()), "data": data}


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
def _chat_completion(model, reply, trace_field=True):
    msg = {"role": "assistant", "content": reply.text}
    if reply.audio:
        msg["audio"] = reply.audio
    out = {"id": "chatcmpl-" + uuid.uuid4().hex[:24], "object": "chat.completion", "created": int(time.time()),
           "model": model, "system_fingerprint": "nim-testbed-" + VERSION,
           "choices": [{"index": 0, "message": msg, "finish_reason": reply.finish, "logprobs": None}],
           "usage": reply.usage, "testbed": reply.info}
    if reply.trace is not None and trace_field:
        out["testbed_trace"] = reply.trace
    return out


def stream_pieces(text, words=3):
    """Split text into chunks of a few words, keeping all whitespace."""
    toks = re.findall(r"\S+\s*|\s+", text or "")
    words = max(1, int(words or 1))
    return ["".join(toks[i:i + words]) for i in range(0, len(toks), words)]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "NIMTestbed/" + VERSION
    app = None  # set per server

    # quiet the default stderr logging; we keep our own log
    def log_message(self, fmt, *args):
        return

    # -- plumbing --------------------------------------------------------
    def _cors(self):
        s = self.app.settings
        self.send_header("Access-Control-Allow-Origin", s.get("cors_origin") or "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        req = self.headers.get("Access-Control-Request-Headers")
        allow = "Authorization, Content-Type, Accept, X-Api-Key, Api-Key, OpenAI-Organization, OpenAI-Project, " \
                "OpenAI-Beta, X-Stainless-Lang, X-Stainless-Package-Version, X-Stainless-OS, X-Stainless-Arch, " \
                "X-Stainless-Runtime, X-Stainless-Runtime-Version, X-Stainless-Retry-Count, X-Stainless-Timeout, " \
                "X-Testbed-User, X-Session-Id"
        self.send_header("Access-Control-Allow-Headers", req if req else allow)
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Access-Control-Expose-Headers", "X-Request-Id, X-Testbed-Note, X-Testbed-Bug")

    def _send(self, status, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = body or b""
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-Id", self._rid)
        for k, v in (extra or {}).items():
            if v:
                self.send_header(k, v)
        self._cors()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        self._status = status

    def _bug(self, err):
        """5xx answers get a bug ID; the bug log keeps the trace, the upstream
        error and the stack. The client sees only the ID."""
        if err.status < 500 or err.bug_id:
            return err.bug_id
        from . import bugs
        kind = "internal" if err.exc is not None else ("upstream_error" if err.etype == "upstream_error"
                                                      else "server_error")
        err.bug_id = bugs.record(kind, err.message, where=f"{self.command} {self.path.split('?')[0]}",
                                 status=err.status, upstream=err.upstream, trace=err.trace, stages=err.stages,
                                 exc=err.exc, request_id=self._rid, model=self._model)
        self._bug_id = err.bug_id
        return err.bug_id

    def _error(self, err):
        self._err = err.message
        self._bug(err)
        extra = {"WWW-Authenticate": "Bearer"} if err.status == 401 else {}
        if err.bug_id:
            extra["X-Testbed-Bug"] = err.bug_id
        self._send(err.status, err.body(), extra=extra or None)

    def _read_body(self):
        limit = int(float(self.app.settings.get("max_body_mb") or 25) * 1024 * 1024)
        if (self.headers.get("Transfer-Encoding") or "").lower() == "chunked":
            buf = b""
            while True:
                line = self.rfile.readline(65537)
                size = int(line.split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    self.rfile.readline()
                    break
                buf += self.rfile.read(size)
                self.rfile.readline()
                if len(buf) > limit:
                    raise ApiError(413, f"request body over {limit // (1024 * 1024)} MB")
            return buf
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            raise ApiError(413, f"request body over {limit // (1024 * 1024)} MB")
        return self.rfile.read(n) if n > 0 else b""

    def _json_body(self):
        raw = self._read_body()
        if not raw:
            raise ApiError(400, "request body is empty; send JSON")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise ApiError(400, f"request body is not valid JSON: {e}")
        if not isinstance(body, dict):
            raise ApiError(400, "request body must be a JSON object")
        self._model = body.get("model") if isinstance(body.get("model"), str) else None
        return body

    def _base(self):
        host = self.headers.get("Host") or f"127.0.0.1:{self.server.server_address[1]}"
        proto = self.headers.get("X-Forwarded-Proto") or "http"
        return f"{proto}://{host}"

    # -- dispatch -----------------------------------------------------------
    def _start(self):
        self._t0 = time.time()
        self._rid = "req_" + uuid.uuid4().hex[:16]
        self._status = 0
        self._err = None
        self._model = None
        self._stream = False
        self._trace = None
        self._bug_id = None

    def _query(self):
        return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))

    def _trace_field(self):
        # X-Testbed-Trace: 1 asks for testbed_trace on this one request (the
        # self-test uses it); the key was already checked
        if (self.headers.get("X-Testbed-Trace") or "").strip().lower() in ("1", "on", "true", "yes"):
            return True
        return self.app.entity_settings().get("trace") != "off"

    def _finish(self):
        app = self.app
        ms = int((time.time() - self._t0) * 1000)
        path = self.path.split("?")[0]
        entry = {"ts": config.timestamp(), "id": self._rid, "method": self.command, "path": path,
                 "model": self._model, "status": self._status, "latency_ms": ms, "stream": self._stream,
                 "client": self.client_address[0] if self.client_address else None}
        if self._err:
            entry["error"] = redact(str(self._err))[:300]
        if getattr(self, "_bug_id", None):
            entry["bug"] = self._bug_id
        if getattr(self, "_trace", None) and (app.settings.get("bugs") or {}).get("trace_in_request_log", True):
            entry["trace"] = [f"{t.get('role')} {t.get('ms')}ms{'' if t.get('ok') else ' FAILED'}"
                              for t in self._trace]
        if self.command == "OPTIONS" or path in ("/health", "/"):
            return
        if app.settings.get("log_requests", True):
            try:
                log_request(entry, app.log_path)
            except OSError:
                pass
        if app.settings.get("log_to_console", True) and not app.quiet:
            from . import colors as C
            safe = dict(entry)
            if safe.get("error"):
                safe["error"] = redact(str(safe["error"]))
            line = redact(format_log([safe], color=C.enabled(sys.stderr))[0])
            print(C.paint("[serve] ", "dim", on=C.enabled(sys.stderr)) + line, file=sys.stderr, flush=True)

    def do_OPTIONS(self):
        self._start()
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()
        self._status = 204
        self._finish()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self._start()
        path = self.path.split("?")[0].rstrip("/") or "/"
        try:
            if path in ("/", "/health", "/v1/health"):
                h = {"status": "ok", "server": "nim-testbed", "version": VERSION, "pid": os.getpid()}
                mem = getattr(self.app.ent, "memory", None)
                if mem is not None:
                    st = mem.status()
                    h["memory"] = {"backend": st["backend"], "online": st["online"]}
                self._send(200, h)
            elif path.startswith(("/files/", "/v1/files/", "/media/")):
                name = path.split("/files/", 1)[1] if "/files/" in path else path[len("/media/"):]
                item = self.app.media.get(name)
                if item is not None:
                    if self.app.entity_settings().get("media_auth") == "key":
                        self.app.check_key(self.headers, self._query().get("key"), call_ok=True)
                    self._send(200, item["data"], ctype=item["mime"], extra={"Cache-Control": "private, max-age=3600"})
                else:
                    p = self.app.files.get(name)
                    data = _read_file(p) if p else None
                    if not data:
                        raise ApiError(404, "no such file (hosted files expire; see entity.media_ttl_hours)",
                                       code="not_found")
                    self._send(200, data, ctype=_mime_of(data))
            elif path.startswith("/v1/audio/bus/"):
                self._audio_bus("GET", path[len("/v1/audio/bus"):])
            elif path == "/call":
                if not self.app.entity_settings().get("call_page", True):
                    raise ApiError(404, "the call page is off (serve settings call on)", code="unknown_url")
                tok = self._query().get("t") or ""
                if not tok or not hmac.compare_digest(tok.encode(), call_token(self.app.settings).encode()):
                    self._send(401, callpage.denied_html(), ctype="text/html; charset=utf-8")
                else:
                    self._send(200, callpage.page_html(main_model(self.app.settings), tok, VERSION),
                               ctype="text/html; charset=utf-8",
                               extra={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
            else:
                self.app.check_key(self.headers)
                if path in ("/v1/models", "/models"):
                    self._send(200, self.app.model_list())
                elif path.startswith(("/v1/models/", "/models/")):
                    mid = urllib.parse.unquote(path.split("/models/", 1)[1])
                    e = self.app.models().get(mid)
                    if not e:
                        raise ApiError(404, f"The model '{mid}' does not exist", code="model_not_found",
                                       param="model")
                    self._send(200, TestbedApp._model_obj(e))
                else:
                    raise ApiError(404, f"Unknown route: GET {path}", code="unknown_url")
        except ApiError as e:
            self._error(e)
        except (BrokenPipeError, ConnectionResetError):
            self._status = 499
        except Exception as e:  # noqa: BLE001 - a bug must still answer as JSON
            self._error(internal_error(e))
        self._finish()

    def do_POST(self):
        self._start()
        path = self.path.split("?")[0].rstrip("/")
        if path.startswith("/v1/"):
            path = path[3:]
        app = self.app
        if path == "/telegram/webhook":
            # Telegram's own secret-token header guards this one (not the API key)
            _mark_user("telegram/webhook")
            from . import telegram
            try:
                code = telegram.handle_webhook(self.headers, self._read_body())
            except Exception:  # noqa: BLE001 - Telegram retries on errors; never crash the server
                code = 500
            return self._send(code, {"ok": code == 200})
        if path.startswith("/audio/bus/"):
            try:
                return self._audio_bus("POST", path[len("/audio/bus"):])
            except ApiError as e:
                self._error(e)
            except (BrokenPipeError, ConnectionResetError):
                self._status = 499
            except Exception as e:  # noqa: BLE001
                self._error(internal_error(e))
            return self._finish()
        try:
            app.check_key(self.headers, call_ok=(path == "/chat/completions"))
            if path in USER_PATHS and str(self.headers.get(SELF_TEST_HEADER) or "") != "1":
                _mark_user(path)   # v3.8.4: a user turn ends a running Free time at once
            if path in ("/chat/completions", "/responses"):
                body = self._json_body()
                uid = self.headers.get("X-Testbed-User") or self.headers.get("X-Session-Id")
                if uid and isinstance(body, dict) and not body.get("user"):
                    body["user"] = uid.strip()[:128]
            if path in ("/chat/completions", "/responses") and str(self.headers.get(SELF_TEST_HEADER) or "") == "1":
                from . import ltm
                with ltm.no_store("self-test"):
                    return self._post_chat(path, body)
            if path in ("/chat/completions", "/responses"):
                return self._post_chat(path, body)
            if path == "/embeddings":
                self._send(200, app.embeddings(self._json_body()))
            elif path in ("/rerank", "/ranking", "/reranking"):
                self._send(200, app.rerank(self._json_body()))
            elif path == "/audio/speech":
                data, mime, meta = app.speech(self._json_body())
                self._send(200, data, ctype=mime, extra={"X-Testbed-Note": meta.get("note")})
            elif path == "/audio/transcriptions":
                raw = self._read_body()
                out, ctype = app.transcriptions(raw, self.headers.get("Content-Type") or "")
                self._model = None
                self._send(200, out, ctype=ctype or "application/json")
            elif path == "/images/generations":
                self._send(200, app.images(self._json_body(), self._base()))
            elif path == "/completions":
                raise ApiError(404, "legacy /v1/completions is not served; use /v1/chat/completions",
                               code="unknown_url")
            else:
                raise ApiError(404, f"Unknown route: POST {self.path}", code="unknown_url")
        except ApiError as e:
            self._error(e)
        except (BrokenPipeError, ConnectionResetError):
            self._status = 499
        except Exception as e:  # noqa: BLE001
            self._error(internal_error(e))
        finally:
            if not self._stream:
                self._finish()

    # -- audio bus (3.8.5): phones play the lab's audio, lend their mic -------
    def _audio_bus(self, method, sub):
        """/v1/audio/bus/*. Phones use their own device token; publish, say,
        use and devices take the lab API key. See audiobus.py."""
        from . import audiobus as AB
        app = self.app
        auth = self.headers.get("Authorization") or ""
        token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        q = self._query()

        def device():
            name = AB.auth_device(token)
            if not name:
                raise ApiError(401, "unknown device token (on the server: nimlab audio add NAME)",
                               etype="invalid_request_error", code="invalid_device_token")
            return name

        try:
            if method == "GET" and sub == "/events":
                name = device()
                try:
                    since = int(q.get("since", "-1"))
                    wait = float(q.get("wait", "25"))
                except ValueError:
                    raise ApiError(400, "since and wait must be numbers")
                caps = {"mic": q.get("mic") == "1", "client": (q.get("client") or "")[:40]}
                return self._send(200, AB.wait_events(name, since, wait, caps),
                                  extra={"Cache-Control": "no-store"})
            if method == "GET" and sub.startswith("/clips/"):
                data, mime = AB.clip(device(), sub[len("/clips/"):])
                return self._send(200, data, ctype=mime, extra={"Cache-Control": "no-store"})
            if method == "GET" and sub == "/me":
                name = device()
                return self._send(200, dict(AB.device_state(name) or {}, head=AB.head()))
            if method == "POST" and sub in ("/activate", "/release"):
                name = device()
                if sub == "/activate":
                    AB.set_active(name)
                elif AB.active() == name:
                    AB.set_active(None)
                return self._send(200, {"active": AB.active(), "device": name})
            if method == "POST" and sub == "/ack":
                body = self._json_body()
                AB.ack(device(), str(body.get("req") or ""), body.get("state") or "", body.get("error") or "")
                return self._send(200, {"ok": True})
            if method == "POST" and sub == "/upload":
                name = device()
                AB.upload(name, q.get("req") or "", self._read_body())
                return self._send(200, {"ok": True})
            if method == "POST" and sub == "/talk":
                return self._audio_bus_talk(device())
            # -- lab key from here on ------------------------------------------
            app.check_key(self.headers)
            if method == "GET" and sub == "/devices":
                return self._send(200, {"devices": AB.devices(), "active": AB.active()})
            if method == "POST" and sub == "/use":
                body = self._json_body()
                AB.set_active(body.get("device") or None)
                return self._send(200, {"active": AB.active()})
            if method == "POST" and sub == "/publish":
                ctype = (self.headers.get("Content-Type") or "").lower()
                if ctype.startswith(("audio/", "application/octet-stream")):
                    data, opts = self._read_body(), q
                    fmt = q.get("format") or ctype.split("/", 1)[1].split(";")[0]
                else:
                    opts = self._json_body()
                    try:
                        data = base64.b64decode(opts.get("audio") or "", validate=False)
                    except (binascii.Error, ValueError):
                        raise ApiError(400, "'audio' must be base64")
                    fmt = opts.get("format")
                ev = AB.publish(data, fmt=fmt, target=opts.get("target") or None, source="api",
                                agent=opts.get("agent") or "", text=opts.get("text") or "",
                                pcm_rate=opts.get("pcm_rate") or opts.get("sample_rate"))
                return self._send(200, ev)
            if method == "POST" and sub == "/say":
                body = self._json_body()
                text = body.get("text") or body.get("input")
                if not isinstance(text, str) or not text.strip():
                    raise ApiError(400, "'text' is required", param="text")
                data, _mime, _meta = app.speech({"model": main_model(app.settings), "input": text,
                                                 "voice": body.get("voice"), "response_format": "wav"})
                ev = AB.publish(data, fmt="wav", target=body.get("target") or None, source="say",
                                agent=body.get("agent") or "", text=text)
                return self._send(200, ev)
            raise ApiError(404, f"Unknown route: {method} /v1/audio/bus{sub}", code="unknown_url")
        except AB.BusError as e:
            raise ApiError(e.status, e.message, code="audio_bus")

    def _audio_bus_talk(self, name):
        """Push-to-talk from a phone: its recording goes to the entity as a
        voice turn (ASR -> persona -> TTS, the same path as voice notes) and
        the reply audio waits on the bus for that phone only."""
        from . import audiobus as AB
        app = self.app
        raw = self._read_body()
        if not raw:
            raise ApiError(400, "the recording is empty")
        fmt = AB.sniff(raw) or "m4a"
        _mark_user("audio/bus/talk")
        body = {"model": main_model(app.settings), "modalities": ["text", "audio"], "audio": {"format": "wav"},
                "user": f"phone-{name}",
                "messages": [{"role": "user", "content": [
                    {"type": "input_audio", "input_audio": {"data": base64.b64encode(raw).decode("ascii"),
                                                            "format": fmt}}]}]}
        self._model = body["model"]
        reply = app.chat(body, self._base() + "/v1")
        info = reply.info or {}
        out = {"text": reply.text, "transcript": info.get("transcript") or (reply.audio or {}).get("transcript"),
               "clip": None}
        a = reply.audio or {}
        if a.get("data"):
            ev = AB.publish(base64.b64decode(a["data"]), fmt="wav", target=name, source="talk",
                            text=reply.text, deliver=False)
            out.update(clip=ev["clip"], ext=ev["ext"], mime=ev["mime"], duration_ms=ev["duration_ms"])
        elif info.get("tts_error"):
            out["tts_error"] = str(info.get("tts_error"))[:200]
        self._send(200, out)

    def _post_chat(self, path, body):
        app = self.app
        if path == "/chat/completions":
            if body.get("stream"):
                self._stream = True
                return self._stream_chat(body)
            reply = app.chat(body, self._base() + "/v1")
            self._trace = reply.trace
            self._send(200, _chat_completion(body["model"], reply, self._trace_field()))
        else:
            self._send(200, app.responses(body, self._base() + "/v1"))

    # -- streaming -----------------------------------------------------------
    def _sse(self, obj):
        data = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _stream_chat(self, body):
        """SSE: role chunk at once, keep-alive comments while the backend
        works, then the reply in small chunks, a finish chunk, optional usage
        chunk and data: [DONE]. Errors after the headers go out as a data:
        {"error": ...} event, then [DONE]."""
        app = self.app
        try:
            app.model_entry(body.get("model"), "chat")   # 404/400 before any stream starts
            if not isinstance(body.get("messages"), list) or not body["messages"]:
                raise ApiError(400, "'messages' must be a non-empty list", param="messages")
        except ApiError as e:
            self._stream = False
            self._error(e)
            self._finish()
            return
        cid = "chatcmpl-" + uuid.uuid4().hex[:24]
        created = int(time.time())
        model = body["model"]

        def chunk(delta, finish=None, **extra):
            d = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                 "system_fingerprint": "nim-testbed-" + VERSION,
                 "choices": [{"index": 0, "delta": delta, "finish_reason": finish, "logprobs": None}]}
            d.update(extra)
            return d

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("X-Request-Id", self._rid)
        self._cors()
        self.end_headers()
        self.close_connection = True
        self._status = 200
        box = {}
        tokens = queue.Queue()
        base = self._base() + "/v1"

        def work():
            try:
                box["reply"] = app.chat(body, base, on_token=tokens.put)
            except ApiError as e:
                box["error"] = e
            except Exception as e:  # noqa: BLE001
                box["error"] = internal_error(e)

        try:
            self._sse(chunk({"role": "assistant", "content": ""}))
            import contextvars
            t = threading.Thread(target=contextvars.copy_context().run, args=(work,), daemon=True)  # keeps no_store
            t.start()
            sent = []
            last = time.time()
            while t.is_alive() or not tokens.empty():
                try:
                    piece = tokens.get(timeout=0.25)
                except queue.Empty:
                    if time.time() - last > 8:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                        last = time.time()
                    continue
                if piece:
                    sent.append(piece)
                    self._sse(chunk({"content": piece}))
                    last = time.time()
            t.join()
            if "error" in box:
                e = box["error"]
                self._err = e.message
                self._bug(e)
                self._status = e.status
                self._sse(e.body())
                self._sse("[DONE]")
                return
            reply = box["reply"]
            self._trace = reply.trace
            done = "".join(sent)
            rest = reply.text[len(done):] if done and reply.text.startswith(done) else (
                reply.text if not done else "")
            if done and not reply.text.startswith(done):
                # the final text changed after streaming (it shouldn't); send what's new as a note
                rest = "\n\n" + reply.text
            for piece in stream_pieces(rest, app.settings.get("stream_chunk_words", 3)):
                self._sse(chunk({"content": piece}))
            if reply.audio:
                self._sse(chunk({"audio": reply.audio}))
            extra = {"testbed": reply.info}
            if reply.trace is not None and self._trace_field():
                extra["testbed_trace"] = reply.trace
            self._sse(chunk({}, finish=reply.finish, **extra))
            if (body.get("stream_options") or {}).get("include_usage"):
                self._sse({"id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                           "choices": [], "usage": reply.usage})
            self._sse("[DONE]")
        except (BrokenPipeError, ConnectionResetError):
            self._status = 499
            self._err = "client closed the stream"
        finally:
            self._finish()


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------
class TestServer:
    def __init__(self, ent, settings=None, port=None, host=None, verified=None, log_path_=None, quiet=False):
        self.settings = settings if settings is not None else load_settings()
        self.app = TestbedApp(ent, self.settings, verified=verified, log_path_=log_path_)
        self.app.quiet = quiet
        self.host = host or self.settings.get("bind") or "127.0.0.1"
        self.port = self.settings.get("port", 8765) if port is None else port
        self.httpd = None
        self.thread = None
        self.tunnel = None

    @property
    def running(self):
        return self.httpd is not None

    @property
    def bound_port(self):
        return self.httpd.server_address[1] if self.httpd else self.port

    def local_base(self):
        return f"http://127.0.0.1:{self.bound_port}/v1"

    def start(self, background=True):
        handler = type("BoundHandler", (Handler,), {"app": self.app})
        ThreadingHTTPServer.allow_reuse_address = True
        self.httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self.httpd.daemon_threads = True
        if background:
            self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.2},
                                           daemon=True)
            self.thread.start()
        else:
            try:
                self.httpd.serve_forever(poll_interval=0.3)
            finally:
                self.stop()
        return self

    def stop(self):
        if self.tunnel:
            self.tunnel.stop()
            self.tunnel = None
            self.app.public_url = None
        if self.httpd:
            h, self.httpd = self.httpd, None
            if self.thread:
                h.shutdown()
                self.thread.join(timeout=5)
                self.thread = None
            h.server_close()

    def block(self):
        out = connection_block(self.settings, self.app.models(), self.bound_port, self.app.public_url,
                               running=self.running)
        mem = getattr(self.app.ent, "memory", None)
        if mem is not None and "Memory:" in out:
            out = re.sub(r"Memory: +.*", lambda _m: "Memory:                  " + memory_line(mem), out, count=1)
        return out


def port_owner(port, host="127.0.0.1", timeout=1.5):
    """Who holds the port: 'nimlab' (our test server answers /health),
    'other' (something else listens), or None (free)."""
    if already_running(port, host, timeout):
        return "nimlab"
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return "other" if s.connect_ex((host, int(port))) == 0 else None
    except OSError:
        return None
    finally:
        s.close()


def already_running(port, host="127.0.0.1", timeout=1.5):
    """True when a testbed server answers /health on the port."""
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")).get("server") == "nim-testbed"
    except (OSError, ValueError, urllib.error.URLError):
        return False


# ---------------------------------------------------------------------------
# Public tunnel (cloudflared quick tunnel)
# ---------------------------------------------------------------------------
TUNNEL_WARNING = ("A public URL lets anyone who has it AND the API key use this server, and every request "
                  "spends your NVIDIA quota and runs your MCP tools. Share it only with people you trust, "
                  "stop the tunnel when you are done, and regenerate the key if it leaks.")
TUNNEL_INSTALL = "pkg install cloudflared"


class Tunnel:
    URL_RX = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    def __init__(self, port, exe=None):
        self.port = port
        self.exe = exe or shutil.which("cloudflared")
        self.proc = None
        self.url = None
        self.output = []

    @staticmethod
    def available():
        return shutil.which("cloudflared") is not None

    def start(self, wait=40):
        if not self.exe:
            raise RuntimeError(f"cloudflared is not installed. Install it with: {TUNNEL_INSTALL}")
        self.proc = subprocess.Popen([self.exe, "tunnel", "--no-autoupdate", "--url",
                                      f"http://127.0.0.1:{self.port}"],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        found = threading.Event()

        def reader():
            for line in self.proc.stdout:
                self.output.append(line.rstrip())
                del self.output[:-50]
                m = self.URL_RX.search(line)
                if m and not self.url:
                    self.url = m.group(0)
                    found.set()
            found.set()

        threading.Thread(target=reader, daemon=True).start()
        found.wait(wait)
        if not self.url:
            tail = " | ".join(self.output[-3:])
            self.stop()
            raise RuntimeError("cloudflared did not report a public URL" + (f": {tail}" if tail else ""))
        return self.url

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


# ---------------------------------------------------------------------------
# Self-test: calls the server like an external client
# ---------------------------------------------------------------------------
SELF_TEST_HEADER = "X-Nimlab-Self-Test"
# v3.8.4: requests that are a user talking to Quill (Telegram, the endpoint, a voice call)
USER_PATHS = ("/chat/completions", "/responses", "/audio/speech", "/audio/transcriptions", "/images/generations")


def _mark_user(path):
    try:
        from . import interrupts
        interrupts.mark(interrupts.USER, path)
    except Exception:  # noqa: BLE001 - never let this get in the way of a reply
        pass


def _call(url, key, body=None, method=None, headers=None, timeout=120):
    # v3.8.0: every self-test request says so, and the server never stores it as a memory
    h = {"Content-Type": "application/json", SELF_TEST_HEADER: "1"}
    if key is not None:
        h["Authorization"] = f"Bearer {key}"
    h.update(headers or {})
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=h, method=method or ("POST" if data else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()
    except (TimeoutError, socket.timeout) as e:
        # v3.7.1: a slow backend is a failed check, never a crash of setup
        return 0, {"x-selftest-error": "timeout"}, _local_err(f"timed out after {timeout:g} s waiting for a reply", e)
    except urllib.error.URLError as e:
        r = getattr(e, "reason", e)
        kind = "timeout" if isinstance(r, (TimeoutError, socket.timeout)) else "unreachable"
        msg = (f"timed out after {timeout:g} s waiting for a reply" if kind == "timeout"
               else f"could not connect ({r})")
        return 0, {"x-selftest-error": kind}, _local_err(msg, e)
    except (ConnectionError, OSError, http.client.HTTPException) as e:
        return 0, {"x-selftest-error": "connection"}, _local_err(f"connection failed ({type(e).__name__}: {e})", e)


def _local_err(msg, exc=None):
    return json.dumps({"error": {"message": msg, "type": "self_test_connection"}}).encode("utf-8")


def _fail_text(st, raw):
    """'HTTP 500: ...' for a server answer; the plain reason (timed out after
    120 s ...) when no answer came back at all."""
    return _err_text(raw) if st == 0 else f"HTTP {st}: {_err_text(raw)}"


def _err_text(raw):
    try:
        return json.loads(raw.decode("utf-8"))["error"]["message"][:160]
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        return raw[:160].decode("utf-8", "replace")


def self_test(base, key, chat_model=None, embed_model=None, out=print, timeout=120, soul_name=None, full=True,
              heavy_timeout=None, roles_set=None):
    """Run the checks; returns [(name, status, detail, ms)], status PASS /
    FAIL / SKIP. Only the models list, auth and CORS need no backend.
    soul_name: the name soul.md gives the entity (the identity check).

    v3.7.1: the basic checks (models, auth, CORS, chat, streaming, identity)
    come first. The heavy live checks (a picture + audio in one message,
    image generation) run only with full=True, with their own heavy_timeout,
    and a timeout or dropped connection in any check is recorded as that
    check's FAIL (with a bug ID) instead of ending the test.

    v3.7.2: embeddings, rerank and speech go through the one agent model
    too (roles_set: the set role keys, when the caller knows them; else the
    server's role_not_set answer says which role is missing)."""
    base = base.rstrip("/")
    rows = []

    def rec(name, status, detail, t0):
        ms = int((time.time() - t0) * 1000)
        rows.append((name, status, detail, ms))
        out(f"  [{status}] {name:<36} {ms:>6} ms  {detail}")

    t0 = time.time()
    models, models3 = [], []
    try:
        st, _, raw = _call(base + "/models", key, timeout=timeout)
        if st == 200:
            data = json.loads(raw.decode("utf-8")).get("data") or []
            models = [(m["id"], (m.get("testbed") or {}).get("type")) for m in data]
            models3 = [(m["id"], (m.get("testbed") or {}).get("type"), (m.get("testbed") or {}).get("source"))
                       for m in data]
            rec("GET /v1/models", "PASS" if models else "FAIL",
                f"{len(models)} model(s)" if models else "no models exposed", t0)
        else:
            rec("GET /v1/models", "FAIL", _fail_text(st, raw), t0)
    except (OSError, ValueError) as e:
        rec("GET /v1/models", "FAIL", f"server not reachable: {e}", t0)
        return rows

    t0 = time.time()
    st, _, raw = _call(base + "/models", "sk-wrong-key-for-self-test-0000", timeout=timeout)
    rec("wrong key is refused", "PASS" if st == 401 else "FAIL", f"HTTP {st}", t0)

    t0 = time.time()
    st, hd, _ = _call(base + "/chat/completions", None, method="OPTIONS",
                      headers={"Origin": "http://example.test", "Access-Control-Request-Method": "POST",
                               "Access-Control-Request-Headers": "authorization,content-type"}, timeout=timeout)
    hdl = {k.lower(): v for k, v in hd.items()}
    ok = st in (200, 204) and hdl.get("access-control-allow-origin")
    rec("CORS preflight", "PASS" if ok else "FAIL", f"HTTP {st}, allow-origin {hdl.get('access-control-allow-origin')}",
        t0)

    chats = [m for m, t in models if t == CHAT]
    agents = [m for m, t, src in models3 if src == AGENT]
    chat_model = chat_model or (agents[0] if agents else None) or \
        next((m for m in chats if m.endswith("-persona")), None) or (chats[0] if chats else None)
    if agents:
        one = len(models) == 1
        rec("one model for the whole stack", "PASS",
            f"{agents[0]}" + ("" if one else f" (+{len(models) - 1} legacy debug name(s) from a hand-set "
                                             "server_settings.expose)"), time.time())
    msg = [{"role": "user", "content": "Reply with the single word: ready"}]
    if not chat_model:
        for n in ("chat", "streamed chat"):
            rows.append((n, "SKIP", "no chat model exposed", 0))
            out(f"  [SKIP] {n:<36}      -  no chat model exposed")
        return _embed_check(rows, rec, out, base, key, models, embed_model, timeout, agent=None,
                            roles_set=roles_set)
    t0 = time.time()
    st, _, raw = _call(base + "/chat/completions", key, {"model": chat_model, "messages": msg,
                                                        "max_tokens": 16}, timeout=timeout)
    if st == 200:
        try:
            txt = json.loads(raw.decode("utf-8"))["choices"][0]["message"]["content"]
            rec(f"chat ({chat_model})", "PASS" if txt else "FAIL", repr(txt[:60]) if txt else "empty reply", t0)
        except (ValueError, KeyError, IndexError, TypeError):
            rec(f"chat ({chat_model})", "FAIL", "reply is not chat.completion JSON", t0)
    else:
        rec(f"chat ({chat_model})", "FAIL", _fail_text(st, raw), t0)

    t0 = time.time()
    st, hd, raw = _call(base + "/chat/completions", key, {"model": chat_model, "messages": msg,
                                                         "max_tokens": 16, "stream": True}, timeout=timeout)
    text, done, err, n = _read_sse(raw)
    ctype = {k.lower(): v for k, v in hd.items()}.get("content-type", "")
    if st == 200 and done and text and not err and "text/event-stream" in ctype:
        rec(f"streamed chat ({chat_model})", "PASS", f"{n} chunks + [DONE], {text[:40]!r}", t0)
    else:
        rec(f"streamed chat ({chat_model})", "FAIL",
            err or (f"HTTP {st}" if st != 200 else ("no [DONE]" if not done else "no content")), t0)

    if chat_model in agents:
        try:
            _entity_checks(rec, rows, out, base, key, chat_model, soul_name, timeout, full=full,
                           heavy_timeout=heavy_timeout or timeout)
        except Exception as e:  # noqa: BLE001 - one broken check never ends the self-test
            rec("entity checks", "FAIL", f"{type(e).__name__}: {e}" + _bug_note("self_test.entity_checks", e),
                time.time())
    return _embed_check(rows, rec, out, base, key, models, embed_model, timeout,
                        agent=agents[0] if agents else None, roles_set=roles_set)


def _bug_note(where, exc=None, message=None):
    """Record a redacted bug report; -> ' (bug B-XXXXXX)' or ''."""
    try:
        from . import bugs
        bid = bugs.record("self_test", message or str(exc), where=where, exc=exc) if exc is not None else \
            bugs.record("self_test", message, where=where)
        return f" (bug {bid})" if bid else ""
    except Exception:  # noqa: BLE001
        return ""


HEAVY_CHECKS = ("text + image + audio in one message", "image generation in chat")


def failure_summary(rows):
    """Plain words for the failed checks, for setup: which check failed and
    why, and whether the server itself is fine. [] when nothing failed."""
    fails = [r for r in rows if r[1] == "FAIL"]
    if not fails:
        return []
    basic_ok = any(r[0] == "GET /v1/models" and r[1] == "PASS" for r in rows)
    out = []
    for name, _st, detail, _ms in fails:
        bid = "" if "(bug B-" in (detail or "") else _bug_note(
            "self_test." + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40],
            message=f"{name}: {detail}")
        out.append(f"- {name}: {detail}{bid}")
    if not basic_ok:
        refused = any("could not connect" in (r[2] or "") or "not reachable" in (r[2] or "") for r in fails)
        out.append("The server did not answer at all" + (" (is something else using the port?)" if refused else "")
                   + ". Check `nimlab serve log`.")
    elif all(r[0] in HEAVY_CHECKS for r in fails):
        out.append("The server is up and chat works; only the heavy live media checks failed. That is a slow or "
                   "missing backend role, not the port. Setup can go on; run `nimlab serve test --full` later.")
    elif any("timed out" in (r[2] or "") for r in fails):
        out.append("The server is up but a model was too slow to answer. Raise server_settings "
                   "self_test_timeout_sec (or the role's timeout) or check the role's model.")
    else:
        out.append("The server is up; see the failed checks above.")
    return out


ROLE_ROUTE_CHECKS = (
    # (check name, role key, route, request body without the model)
    ("embeddings", "embedding", "/embeddings", {"input": ["hello", "world"]}),
    ("rerank", "reranker", "/rerank", {"query": "which is about cats?", "documents": ["dogs bark", "cats purr"],
                                       "top_n": 1}),
    ("speech (TTS)", "tts", "/audio/speech", {"input": "ready", "response_format": "wav"}),
)


def _role_not_set(raw):
    try:
        return json.loads(raw.decode("utf-8"))["error"].get("code") == "role_not_set"
    except (ValueError, KeyError, TypeError, AttributeError, UnicodeDecodeError):
        return False


def _embed_check(rows, rec, out, base, key, models, embed_model, timeout, agent=None, roles_set=None):
    """3.7.2: embeddings, rerank and speech are tested through the ONE
    agent model (the endpoint wraps every role into that name), so a default
    install never SKIPs them. A role that is not set is a SKIP that names
    the role and the setup step."""
    from . import roles as R
    labels = {k: R.label(k) for k in ("embedding", "reranker", "tts")}

    def skip(name, why):
        rows.append((name, "SKIP", why, 0))
        out(f"  [SKIP] {name:<36}      -  {why}")

    for name, role, path, body in ROLE_ROUTE_CHECKS:
        want = {"embedding": EMBED}.get(role)
        model = agent
        if name == "embeddings" and embed_model:
            model = embed_model
        if not model:
            own = [m for m, t in models if want and t == want]
            model = own[0] if own else None
        if not model:
            skip(name, "the endpoint lists no model (/v1/models is empty): restart it with nimlab serve restart")
            continue
        if roles_set is not None and role not in roles_set:
            skip(name, f"the {labels[role]} role isn't set: run `nimlab setup roles`")
            continue
        t0 = time.time()
        st, hd, raw = _call(base + path, key, dict(body, model=model), timeout=timeout)
        label = f"{name} ({model})"
        if st == 400 and _role_not_set(raw):
            skip(name, f"the {labels[role]} role isn't set: run `nimlab setup roles`")
            continue
        if st != 200:
            rec(label, "FAIL", _fail_text(st, raw), t0)
            continue
        try:
            if role == "embedding":
                d = json.loads(raw.decode("utf-8"))["data"]
                dim = len(d[0]["embedding"])
                rec(label, "PASS" if len(d) == 2 and dim else "FAIL", f"2 vectors, {dim} dims", t0)
            elif role == "reranker":
                res = json.loads(raw.decode("utf-8"))["results"]
                rec(label, "PASS" if res else "FAIL", f"top document {res[0].get('index')}" if res else "no results",
                    t0)
            else:
                rec(label, "PASS" if len(raw) > 44 else "FAIL", f"{len(raw)} bytes of audio", t0)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            rec(label, "FAIL", f"the reply is not a {name} answer", t0)
    return rows


def _read_sse(raw):
    text, done, err, n = "", False, None, 0
    events = []
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if payload == "[DONE]":
            done = True
            continue
        try:
            ev = json.loads(payload)
        except ValueError:
            continue
        if "error" in ev:
            err = ev["error"].get("message")
            continue
        n += 1
        events.append(ev)
        for ch in ev.get("choices") or []:
            text += (ch.get("delta") or {}).get("content") or ""
    return text, done, err, n


def test_png():
    """A 16x16 PNG (white with a dark bar), made with zlib: the self-test image."""
    w = h = 16
    rows = b"".join(b"\x00" + b"".join(b"\x20\x20\x20" if 6 <= y <= 9 else b"\xff\xff\xff" for _ in range(w))
                    for y in range(h))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def test_wav(seconds=0.6, rate=16000):
    """A short 440 Hz tone as 16-bit mono WAV: the self-test audio."""
    n = int(seconds * rate)
    pcm = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n))
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + b"data" + struct.pack("<I", len(pcm)) + pcm)


def _entity_checks(rec, rows, out, base, key, model, soul_name, timeout, full=True, heavy_timeout=None):
    """Identity (basic), then a mixed text+image+audio message and an
    image-generation ask (heavy, only with full=True), all through the one
    model."""
    tmo = {"t": timeout}

    def ask(content, **extra):
        body = {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 200}
        body.update(extra)
        st, _, raw = _call(base + "/chat/completions", key, body, timeout=tmo["t"])
        try:
            return st, json.loads(raw.decode("utf-8")), raw
        except ValueError:
            return st, {}, raw

    def skip(name, why):
        rows.append((name, "SKIP", why, 0))
        out(f"  [SKIP] {name:<36}      -  {why}")

    # who are you -> soul.md
    t0 = time.time()
    st, j, raw = ask("Who are you? Answer in one or two sentences.")
    if st != 200:
        rec("identity comes from soul.md", "FAIL", _fail_text(st, raw), t0)
    else:
        txt = j["choices"][0]["message"]["content"] or ""
        who = (j.get("testbed") or {}).get("answered_by")
        if soul_name:
            ok = soul_name.lower() in txt.lower()
            rec("identity comes from soul.md", "PASS" if ok else "FAIL",
                (f"says it is {soul_name}: {txt[:60]!r}" if ok else f"soul.md says {soul_name}; reply {txt[:60]!r}"), t0)
        else:
            rec("identity comes from soul.md", "PASS" if txt and who == "persona" else "FAIL",
                f"persona answered {txt[:50]!r} (no name found in soul.md to compare)", t0)

    if not full:
        for n in HEAVY_CHECKS:
            skip(n, "heavy live check: run `nimlab serve test --full`")
        return
    tmo["t"] = heavy_timeout or timeout
    # text + image + audio in one message
    name = "text + image + audio in one message"
    t0 = time.time()
    img = "data:image/png;base64," + base64.b64encode(test_png()).decode("ascii")
    content = [{"type": "text", "text": "What is in this picture, and what do you hear in the clip?"},
               {"type": "image_url", "image_url": {"url": img}},
               {"type": "input_audio", "input_audio": {"data": base64.b64encode(test_wav()).decode("ascii"),
                                                       "format": "wav"}}]
    st, j, raw = ask(content)
    if st != 200:
        rec(name, "FAIL", _fail_text(st, raw) + (_bug_note("self_test.mixed_media", message=_fail_text(st, raw))
                                                 if st == 0 else ""), t0)
    else:
        ran = {t.get("role") for t in j.get("testbed_trace") or []}
        miss = set((j.get("testbed") or {}).get("missing_roles") or [])
        img_ok = bool(ran & {"vision", "ocr", "chart_parser"})
        aud_ok = bool(ran & {"asr", "omni_audio"})
        last = (j.get("testbed_trace") or [{}])[-1].get("role")
        if img_ok and aud_ok and last == "persona":
            rec(name, "PASS", "routed to " + ", ".join(sorted(ran - {"intent_router"})) + "; persona replied", t0)
        elif miss and not (img_ok and aud_ok):
            rec(name, "SKIP" if last == "persona" else "FAIL",
                "set " + ", ".join(R.label(k) for k in sorted(miss)) + " to test this; the reply named them", t0)
        else:
            rec(name, "FAIL", f"abilities that ran: {sorted(ran)}; reply by {last}", t0)

    # image generation through chat
    name = "image generation in chat"
    t0 = time.time()
    st, j, raw = ask("Generate an image of a red circle on a white background.")
    if st != 200:
        rec(name, "FAIL", _fail_text(st, raw), t0)
        return
    txt = j["choices"][0]["message"]["content"] or ""
    if "image_gen" in ((j.get("testbed") or {}).get("missing_roles") or []):
        skip(name, "set the Text-to-Image role to test this (the reply said so)")
        return
    m = re.search(r"!\[[^\]]*\]\(([^)\s]+)\)", txt)
    if not m:
        rec(name, "FAIL", "no image in the reply", t0)
        return
    url = m.group(1)
    if url.startswith("data:"):
        rec(name, "PASS", "image returned inline (data URL)", t0)
        return
    st2, hd, data = _call(url, key, timeout=timeout)
    ctype = {k.lower(): v for k, v in hd.items()}.get("content-type", "")
    rec(name, "PASS" if st2 == 200 and ctype.startswith("image/") and data else "FAIL",
        f"hosted at /v1/files/..., {ctype}, {len(data or b'')} bytes" if st2 == 200 else f"GET image: HTTP {st2}", t0)


def test_summary(rows):
    c = {s: sum(1 for r in rows if r[1] == s) for s in ("PASS", "FAIL", "SKIP")}
    return f"{c['PASS']} passed, {c['FAIL']} failed, {c['SKIP']} skipped"
