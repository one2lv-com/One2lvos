"""Extract a model's API definition from its public build.nvidia.com page
(or its docs.api.nvidia.com reference page) and turn it into an exact
endpoint plan plus a minimal valid request.

build.nvidia.com is a Next.js app. Model pages stream their data as React
Server Component chunks: `self.__next_f.push([1,"..."])`. Joined and
unescaped, that stream contains a `"spec":{...}` object with:
  openAPISpec      full OpenAPI 3 document (servers, paths, schemas, examples)
  nvcfFunctionId   NVCF function id
  artifactName     the URL slug
  attributes       apiDocsUrl, deprecationNotice, playground options ...
Long strings are moved out of line as `"$8b"` references to `8b:T<hexlen>,`
text chunks; `usage` (the code samples) is one of those.

Every function tolerates missing pieces and returns None / empty values
instead of raising, because the page layout can change at any time.
"""

import base64
import io
import json
import re
import struct
import wave
import zlib

from .core import redact

INTEGRATE = "https://integrate.api.nvidia.com/v1"
AI_API = "https://ai.api.nvidia.com/v1"
NVCF_PEXEC = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/"
NVCF_GRPC = "grpc.nvcf.nvidia.com:443"

def _png(width=16, height=16, rgb=(128, 128, 128)):
    """A valid solid-colour PNG built with zlib (no image library needed)."""
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


# 16x16 grey PNG, enough for vision / OCR probes.
TINY_PNG_DATA_URI = "data:image/png;base64," + base64.b64encode(_png()).decode("ascii")

_NON_INFERENCE_PATH = re.compile(r"/(status|health|metrics|license|metadata|manifest|models)(/|$|\{)")
_DEPRECATION_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


# ---------------------------------------------------------------------------
# Slugs and model ids
# ---------------------------------------------------------------------------
def slug_to_api_id(publisher, slug):
    """Best guess of the API model id from a build.nvidia.com URL slug.
    The site writes dots as underscores: kimi-k3_1-pro -> kimi-k3.1-pro.
    The page's embedded spec is authoritative when available."""
    slug = (slug or "").strip("/")
    if "/" in slug:
        publisher, slug = slug.split("/", 1)
    return f"{(publisher or 'nvidia').lower()}/{slug.replace('_', '.')}"


def api_id_to_slug(api_id):
    """publisher/model.id -> (publisher, slug) with dots written as underscores."""
    api_id = (api_id or "").strip("/")
    publisher, _, name = api_id.partition("/") if "/" in api_id else ("nvidia", "", api_id)
    return publisher, name.replace(".", "_")


def slug_candidates(api_id):
    """Page slugs to try for an API id, most likely first."""
    publisher, slug = api_id_to_slug(api_id)
    name = api_id.split("/", 1)[-1]
    out = []
    for s in (slug, name.replace(".", "-"), name):
        if s and s not in out:
            out.append(s)
    return publisher, out


def match_key(model_id):
    """Loose key for matching ids across sources: case, '.', '_' and '-' ignored
    as separators (glm-5.3-flash, glm-5-3-flash and glm-5_3-flash all match)."""
    return re.sub(r"[._\-]+", "-", (model_id or "").strip().lower())


def build_page_url(publisher, slug):
    return f"https://build.nvidia.com/{publisher}/{slug}"


def docs_reference_slug(api_id):
    publisher, slug = api_id_to_slug(api_id)
    return f"{publisher}-{slug}"


# ---------------------------------------------------------------------------
# RSC stream helpers
# ---------------------------------------------------------------------------
_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)


def rsc_text(html):
    """Join and unescape the Next.js flight chunks of a page."""
    parts = []
    for chunk in _PUSH.findall(html or ""):
        try:
            parts.append(json.loads('"' + chunk + '"'))
        except ValueError:
            continue
    return "".join(parts)


def resolve_text_ref(stream, value):
    """'$8b' -> the text of chunk `8b:T<hexlen>,...`; other values unchanged."""
    if not isinstance(value, str) or not re.fullmatch(r"\$[0-9a-f]+", value):
        return value
    ref = value[1:]
    m = re.search(r"(?:^|\n|\})" + re.escape(ref) + r":T([0-9a-f]+),", stream)
    if not m:
        return None
    length = int(m.group(1), 16)
    # the length is in UTF-8 bytes
    raw = stream[m.end():m.end() + length * 2].encode("utf-8")[:length]
    return raw.decode("utf-8", errors="ignore")


def _decode_object_at(stream, start):
    try:
        obj, _ = json.JSONDecoder().raw_decode(stream, start)
        return obj
    except ValueError:
        return None


def _first_spec_object(stream):
    for m in re.finditer(r'"spec":\{', stream):
        obj = _decode_object_at(stream, m.end() - 1)
        if isinstance(obj, dict) and ("openAPISpec" in obj or "nvcfFunctionId" in obj or "artifactName" in obj):
            return obj
    return None


def _first_string_field(stream, name):
    m = re.search(r'"' + re.escape(name) + r'":"((?:[^"\\]|\\.)*)"', stream)
    if not m:
        return None
    try:
        return json.loads('"' + m.group(1) + '"')
    except ValueError:
        return m.group(1)


def _first_object_field(stream, name):
    m = re.search(r'"' + re.escape(name) + r'":\{', stream)
    return _decode_object_at(stream, m.end() - 1) if m else None


# ---------------------------------------------------------------------------
# Page extraction
# ---------------------------------------------------------------------------
def is_not_found_page(html):
    return "NEXT_HTTP_ERROR_FALLBACK;404" in (html or "") and '"spec":{' not in rsc_text(html)


def parse_deprecation(notice):
    """{'notice', 'deprecated_on', 'support_ends'} with ISO dates (or None)."""
    if not notice:
        return None
    text = re.sub(r"<[^>]+>", "", str(notice)).strip()
    dates = [f"{y}-{int(m):02d}-{int(d):02d}" for m, d, y in _DEPRECATION_DATE.findall(text)]
    return {"notice": text[:400], "deprecated_on": dates[0] if dates else None,
            "support_ends": dates[-1] if dates else None}


def extract_build_page(html):
    """Everything useful on a build.nvidia.com model page, or found=False."""
    info = {"found": False, "not_found": False, "openapi": None, "function_id": None,
            "artifact_name": None, "api_docs_url": None, "deprecation": None,
            "playground": None, "usage": "", "hosted_urls": [], "nvcf_http_paths": [],
            "grpc": False, "title": None}
    if not html:
        return info
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    info["title"] = m.group(1).strip() if m else None
    stream = rsc_text(html)
    if not stream:
        info["not_found"] = "404" in (info["title"] or "")
        return info
    spec = _first_spec_object(stream)
    attrs = {}
    if spec:
        info["found"] = True
        oa = spec.get("openAPISpec")
        info["openapi"] = oa if isinstance(oa, dict) and oa.get("paths") else None
        info["function_id"] = spec.get("nvcfFunctionId") or None
        info["artifact_name"] = spec.get("artifactName") or None
        attrs = spec.get("attributes") if isinstance(spec.get("attributes"), dict) else {}
    else:
        # model pages without an inline API spec (gRPC / download-only models)
        fid = _first_string_field(stream, "nvcfFunctionId")
        art = _first_string_field(stream, "artifactName")
        if fid or art:
            info["found"] = True
            info["function_id"] = fid
            info["artifact_name"] = art
            attrs = _first_object_field(stream, "attributes") or {}
            if not isinstance(attrs, dict) or "showUnavailableBanner" not in attrs and "apiDocsUrl" not in attrs:
                attrs = {}
        elif is_not_found_page(html):
            info["not_found"] = True
            return info
    info["api_docs_url"] = attrs.get("apiDocsUrl") if isinstance(attrs.get("apiDocsUrl"), str) else None
    notice = attrs.get("deprecationNotice") or _first_string_field(stream, "deprecationNotice")
    info["deprecation"] = parse_deprecation(notice)
    if isinstance(attrs.get("playground"), dict):
        pg = attrs["playground"]
        opts = pg.get("options") if isinstance(pg.get("options"), dict) else {}
        chat = opts.get("chat") if isinstance(opts.get("chat"), dict) else {}
        info["playground"] = {"type": pg.get("type"), "features": chat.get("features") or [],
                              "images": bool(opts.get("image"))}
    usage = resolve_text_ref(stream, attrs.get("usage")) if attrs.get("usage") else None
    if usage is None:
        usage = resolve_text_ref(stream, _first_string_field(stream, "usage") or "") or ""
    info["usage"] = usage if isinstance(usage, str) else ""
    hosted = re.findall(r"https://(?:ai\.api\.nvidia\.com|integrate\.api\.nvidia\.com)/v[12]/[A-Za-z0-9_./\-]+",
                        stream)
    info["hosted_urls"] = sorted({u.rstrip("/.") for u in hosted})
    info["nvcf_http_paths"] = sorted(set(re.findall(
        r"invocation\.api\.nvcf\.nvidia\.com(/v\d/[A-Za-z0-9_/\-]+)", info["usage"])))
    info["grpc"] = NVCF_GRPC.split(":")[0] in info["usage"] or "gRPC" in info["usage"]
    return info


NGC_SPEC_URL = "https://api.ngc.nvidia.com/v2/endpoints/{org}/{slug}/spec"


def ngc_spec_url(slug, org="qc69jvmznzxy"):
    return NGC_SPEC_URL.format(org=org, slug=slug)


def extract_ngc_spec(body):
    """Same fields as extract_build_page, from the NGC endpoint spec JSON
    (api.ngc.nvidia.com/v2/endpoints/<org>/<slug>/spec), the data the page
    itself is rendered from. openAPISpec and attributes arrive as JSON strings."""
    info = {"found": False, "not_found": False, "openapi": None, "function_id": None,
            "artifact_name": None, "api_docs_url": None, "deprecation": None,
            "playground": None, "usage": "", "hosted_urls": [], "nvcf_http_paths": [],
            "grpc": False, "title": None, "inference_path": None}
    if isinstance(body, (str, bytes)):
        try:
            body = json.loads(body)
        except ValueError:
            return info
    if not isinstance(body, dict):
        return info
    status = (body.get("requestStatus") or {}).get("statusCode")
    if status == "NOT_FOUND":
        info["not_found"] = True
        return info
    if not (body.get("artifactName") or body.get("nvcfFunctionId")):
        return info
    info["found"] = True
    info["artifact_name"] = body.get("artifactName")
    info["function_id"] = body.get("nvcfFunctionId") or None
    info["inference_path"] = body.get("nvcfInferencePath")
    oa = body.get("openAPISpec")
    if isinstance(oa, str):
        try:
            oa = json.loads(oa)
        except ValueError:
            oa = None
    info["openapi"] = oa if isinstance(oa, dict) and oa.get("paths") else None
    attrs = body.get("attributes")
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except ValueError:
            attrs = {}
    attrs = attrs if isinstance(attrs, dict) else {}
    info["api_docs_url"] = attrs.get("apiDocsUrl") if isinstance(attrs.get("apiDocsUrl"), str) else None
    info["deprecation"] = parse_deprecation(attrs.get("deprecationNotice"))
    pg = attrs.get("playground")
    if isinstance(pg, dict):
        opts = pg.get("options") if isinstance(pg.get("options"), dict) else {}
        chat = opts.get("chat") if isinstance(opts.get("chat"), dict) else {}
        info["playground"] = {"type": pg.get("type"), "features": chat.get("features") or [],
                              "images": bool(opts.get("image"))}
    usage = attrs.get("usage") if isinstance(attrs.get("usage"), str) else ""
    info["usage"] = usage
    blob = usage + json.dumps(oa or {})
    hosted = re.findall(r"https://(?:ai\.api\.nvidia\.com|integrate\.api\.nvidia\.com)/v[12]/[A-Za-z0-9_./\-]+", blob)
    info["hosted_urls"] = sorted({u.rstrip("/.") for u in hosted})
    info["nvcf_http_paths"] = sorted(set(re.findall(r"invocation\.api\.nvcf\.nvidia\.com(/v\d/[A-Za-z0-9_/\-]+)", usage)))
    info["grpc"] = info["inference_path"] == "/grpc" or NVCF_GRPC.split(":")[0] in usage
    return info


def extract_docs_page(html):
    """OpenAPI spec from a docs.api.nvidia.com reference page (ReadMe ssr-props)."""
    props = docs_ssr_props(html)
    if not props:
        return {"found": False, "not_found": False, "openapi": None, "title": None}
    doc = props.get("document") if isinstance(props.get("document"), dict) else {}
    api = doc.get("api") if isinstance(doc.get("api"), dict) else {}
    schema = api.get("schema") if isinstance(api.get("schema"), dict) else None
    title = (doc.get("title") or (props.get("meta") or {}).get("title")) if isinstance(doc, dict) else None
    return {"found": bool(schema and schema.get("paths")), "not_found": bool(props.get("is404")),
            "openapi": schema if schema and schema.get("paths") else None, "title": title}


def docs_ssr_props(html):
    m = re.search(r'<script id="ssr-props" type="application/x-ssr-props">(.*?)</script>', html or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# OpenAPI helpers
# ---------------------------------------------------------------------------
def _resolve(schema, root, depth=0):
    if depth > 12 or not isinstance(schema, dict):
        return schema if isinstance(schema, dict) else {}
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        node = root
        for part in ref[2:].split("/"):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        merged = dict(node)
        merged.update({k: v for k, v in schema.items() if k != "$ref"})
        return _resolve(merged, root, depth + 1)
    for key in ("anyOf", "oneOf"):
        if key in schema and isinstance(schema[key], list):
            options = [_resolve(o, root, depth + 1) for o in schema[key]]
            options = [o for o in options if o.get("type") != "null"] or options
            if options:
                merged = dict(options[0])
                merged.update({k: v for k, v in schema.items() if k not in (key,)})
                return merged
    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged = {k: v for k, v in schema.items() if k != "allOf"}
        props, req = dict(merged.get("properties") or {}), list(merged.get("required") or [])
        for part in schema["allOf"]:
            p = _resolve(part, root, depth + 1)
            props.update(p.get("properties") or {})
            req += [r for r in p.get("required") or [] if r not in req]
            for k, v in p.items():
                merged.setdefault(k, v)
        merged["properties"], merged["required"] = props, req
        return merged
    return schema


def inference_operations(openapi):
    """[(path, method, operation)] for inference calls, POST first."""
    ops = []
    for path, item in (openapi or {}).get("paths", {}).items():
        if not isinstance(item, dict) or _NON_INFERENCE_PATH.search(path):
            continue
        for method, op in item.items():
            if method.lower() in ("post", "put", "get") and isinstance(op, dict):
                ops.append((path, method.upper(), op))
    ops.sort(key=lambda t: (t[1] != "POST", len(t[0])))
    return ops


def normalize_server(url):
    """Hosted server URL from a spec's servers entry, or None. Adds a missing
    https:// (climate.api.nvidia.com) and drops self-host placeholders
    (http://localhost:8000) so the hosted route is looked up instead."""
    url = (url or "").strip()
    if not url:
        return None
    if "://" not in url:
        url = "https://" + url.lstrip("/")
    host = url.split("://", 1)[1].split("/", 1)[0].split(":")[0].lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or not host.endswith("nvidia.com"):
        return None
    return url.replace("http://", "https://", 1)


def join_url(base, path):
    base = (base or "").rstrip("/")
    path = "/" + (path or "").lstrip("/")
    if base.endswith("/v1") and path.startswith("/v1/"):
        path = path[3:]
    return base + path


def request_schema(op, root):
    content = ((op or {}).get("requestBody") or {}).get("content") or {}
    for ct in ("application/json", "multipart/form-data"):
        if ct in content:
            return ct, _resolve((content[ct] or {}).get("schema") or {}, root)
    for ct, c in content.items():
        return ct, _resolve((c or {}).get("schema") or {}, root)
    return None, {}


def model_id_from_spec(openapi):
    """The exact API model id: the request schema's model default/const/enum,
    else the spec title 'NVIDIA NIM API for publisher/model'."""
    if not openapi:
        return None
    for path, method, op in inference_operations(openapi):
        _, sch = request_schema(op, openapi)
        model = _resolve((sch.get("properties") or {}).get("model") or {}, openapi)
        for key in ("const", "default", "example"):
            if isinstance(model.get(key), str) and "/" in model[key]:
                return model[key]
        enum = model.get("enum")
        if isinstance(enum, list) and enum and isinstance(enum[0], str):
            return enum[0]
    title = ((openapi.get("info") or {}).get("title") or "")
    m = re.search(r"for ([\w.\-]+/[\w.\-]+)", title)
    return m.group(1) if m else None


def example_request(op):
    """First request example from x-nvai-meta, parsed, or None."""
    meta = (op or {}).get("x-nvai-meta") or {}
    for ex in meta.get("examples") or []:
        raw = ex.get("requestJson") if isinstance(ex, dict) else None
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            raw = re.sub(r'"?<%-\s*input\.image\s*%>"?', json.dumps(TINY_PNG_DATA_URI), raw)
            raw = re.sub(r"<%-\s*[^%]*%>", "test", raw)
            try:
                return json.loads(raw)
            except ValueError:
                continue
    content = ((op or {}).get("requestBody") or {}).get("content") or {}
    for c in content.values():
        if isinstance(c, dict) and isinstance(c.get("example"), dict):
            return c["example"]
        for ex in (c or {}).get("examples", {}).values() if isinstance((c or {}).get("examples"), dict) else []:
            if isinstance(ex, dict) and isinstance(ex.get("value"), dict):
                return ex["value"]
    return None


# ---------------------------------------------------------------------------
# Minimal requests
# ---------------------------------------------------------------------------
def _sample(schema, root, name="", depth=0):
    s = _resolve(schema, root)
    for key in ("const", "default", "example"):
        if key in s and s[key] is not None:
            return s[key]
    if isinstance(s.get("enum"), list) and s["enum"]:
        return s["enum"][0]
    if isinstance(s.get("examples"), list) and s["examples"]:
        return s["examples"][0]
    t = s.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), t[0] if t else None)
    if t is None:
        t = "object" if s.get("properties") else ("array" if s.get("items") else "string")
    if depth > 6:
        return None
    if t == "object":
        out = {}
        props = s.get("properties") or {}
        for req in s.get("required") or []:
            out[req] = _sample(props.get(req, {}), root, req, depth + 1)
        for name_, p in props.items():  # fixed discriminators such as type: image_url
            if name_ not in out and isinstance(p, dict) and "const" in p:
                out[name_] = p["const"]
        return out
    if t == "array":
        n = max(1, int(s.get("minItems") or 1))
        return [_sample(s.get("items") or {}, root, name, depth + 1) for _ in range(min(n, 2))]
    if t == "integer":
        return int(s.get("minimum", 1) if s.get("minimum", 1) is not None else 1)
    if t == "number":
        return s.get("minimum", 0.5) if s.get("minimum") is not None else 0.5
    if t == "boolean":
        return False
    fmt = (s.get("format") or "").lower()
    lname = name.lower()
    if fmt in ("uri", "url") or "image" in lname or lname == "url":
        return TINY_PNG_DATA_URI
    return "Hi" if lname in ("content", "text", "prompt", "input", "query") else "test"


def build_minimal_request(schema, root, kind, model_id):
    """Smallest request that satisfies the schema, tuned so probes are cheap."""
    s = _resolve(schema or {}, root or {})
    props = s.get("properties") or {}
    body = _sample(s, root or {}) if s else {}
    if not isinstance(body, dict):
        body = {}
    if "model" in props or kind in ("chat", "vision", "embeddings"):
        body["model"] = model_id or body.get("model")
    if kind in ("chat", "vision") or ("messages" in props and "messages" not in body):
        body["messages"] = [{"role": "user", "content": "Hi"}]
    if kind == "embeddings":
        body["input"] = ["probe"]
        if "input_type" in props:
            body["input_type"] = "query"
        if "encoding_format" in props:
            body["encoding_format"] = "float"
    if kind == "rerank" and "query" in props and "passages" in props:
        body["query"] = {"text": "probe"}
        body["passages"] = [{"text": "sample"}]
    for tok in ("max_tokens", "max_completion_tokens"):
        if tok in props:
            body[tok] = 8
    if "stream" in props:
        body["stream"] = False
    if kind == "image_gen":
        for k, v in (("steps", None), ("samples", 1)):
            if k in props:
                p = _resolve(props[k], root or {})
                body[k] = v if v is not None else int(p.get("minimum") or p.get("default") or 1)
    return body


def tighten_example(example, kind):
    """Make a page example cheap to send (short output, no streaming)."""
    if not isinstance(example, dict):
        return None
    ex = json.loads(json.dumps(example))
    for tok in ("max_tokens", "max_completion_tokens"):
        if tok in ex:
            ex[tok] = 8
    if ex.get("stream"):
        ex["stream"] = False
    ex.pop("stream_options", None)
    return ex


def silent_wav(seconds=0.5, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(seconds * rate))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Kinds
# ---------------------------------------------------------------------------
def kind_from_path(path, playground=None, model_id=""):
    p = (path or "").lower()
    m = (model_id or "").lower()
    if p.endswith("/chat/completions"):
        pg = playground or {}
        if pg.get("images") or "images" in (pg.get("features") or []):
            return "vision"
        return "chat"
    if p.endswith("/completions"):
        return "completions"
    if "embedding" in p:
        return "embeddings"
    if "rank" in p:
        return "rerank"
    if "/genai/" in p:
        return "image_gen"
    if "synthesize" in p or "/audio/speech" in p:
        return "tts"
    if "transcri" in p:
        return "asr"
    if "/cv/" in p or p.endswith("/infer"):
        if any(h in m for h in ("ocr", "parse", "table", "page-elements", "graphic-elements")):
            return "ocr"
        return "cv"
    return "other"


# ---------------------------------------------------------------------------
# Endpoint plans
# ---------------------------------------------------------------------------
def _hosted_cv_url(info, api_id):
    publisher, name = (api_id.split("/", 1) + [""])[:2] if "/" in api_id else ("nvidia", api_id)
    for u in info.get("hosted_urls") or []:
        if u.endswith(f"/{publisher}/{name}") or u.endswith(f"/{name}"):
            return u
    return None


def derive_plans(info, api_id=None, source="page"):
    """Ordered endpoint plans for one model from extracted page/doc info.

    Each plan: {url, method, content_type, kind, model, body, alt_body,
    transport ('rest'|'nvcf_http'), source, function_id, path}.
    Returns (plans, notes) where notes may contain 'grpc_only'.
    """
    plans, notes = [], {}
    oa = info.get("openapi")
    fid = info.get("function_id")
    model = model_id_from_spec(oa) or api_id
    if oa:
        servers = [normalize_server(s.get("url")) for s in oa.get("servers") or [] if isinstance(s, dict)]
        servers = [u for u in servers if u]
        for path, method, op in inference_operations(oa):
            ct, sch = request_schema(op, oa)
            kind = kind_from_path(path, info.get("playground"), model or "")
            body = build_minimal_request(sch, oa, kind, model) if ct != "multipart/form-data" else None
            alt = tighten_example(example_request(op), kind)
            base_urls = []
            if servers:
                base_urls = [join_url(servers[0], path)]
            else:
                # self-hostable NIM spec (paths like /v1/infer): find the hosted route
                hosted = _hosted_cv_url(info, model or api_id or "")
                if hosted:
                    base_urls.append(hosted)
                if fid:
                    base_urls.append(NVCF_PEXEC + fid)
            for url in base_urls:
                plans.append({"url": url, "method": method, "content_type": ct or "application/json",
                              "kind": kind, "model": model, "body": body, "alt_body": alt,
                              "transport": "nvcf_http" if "nvcf.nvidia.com" in url else "rest",
                              "source": source, "function_id": fid, "path": path})
            if plans:
                break  # first inference operation is the model's main call
    if not plans and fid and info.get("nvcf_http_paths"):
        # speech models document an HTTP API on the NVCF function host
        paths = info["nvcf_http_paths"]
        main = next((p for p in paths if "synthesize" in p or "transcri" in p), paths[0])
        kind = kind_from_path(main, None, model or "")
        probe_get = next((p for p in paths if "list_voices" in p), None)
        plans.append({"url": f"https://{fid}.invocation.api.nvcf.nvidia.com{main}", "method": "POST",
                      "content_type": "multipart/form-data", "kind": kind, "model": model, "body": None,
                      "alt_body": None, "transport": "nvcf_http", "source": source, "function_id": fid,
                      "path": main,
                      "probe_get": f"https://{fid}.invocation.api.nvcf.nvidia.com{probe_get}" if probe_get else None})
    if not plans and info.get("grpc"):
        notes["grpc_only"] = True
    if not plans and not info.get("grpc") and info.get("found") and not oa:
        notes["no_hosted_api"] = True
    return plans, notes


def multipart_fields(plan, voice="Magpie-Multilingual.EN-US.Aria"):
    """Form fields for NVCF speech HTTP probes."""
    if plan.get("kind") == "tts":
        return [("text", "Hi"), ("language", "en-US"), ("voice", voice)]
    if plan.get("kind") == "asr":
        return [("language", "en-US"), ("file", ("probe.wav", silent_wav(), "audio/wav"))]
    return [("input", "Hi")]


def error_hint(text, limit=240):
    """Short, key-free hint from an error body (detail / message / title)."""
    hint = text or ""
    try:
        body = json.loads(text)
        if isinstance(body, dict):
            for k in ("detail", "message", "error", "title"):
                v = body.get(k)
                if isinstance(v, dict):
                    v = v.get("message") or json.dumps(v)
                if isinstance(v, list):
                    v = json.dumps(v)
                if v:
                    hint = str(v)
                    break
    except ValueError:
        pass
    hint = re.sub(r"\s+", " ", hint).strip()
    return redact(hint[:limit])


def b64(data):
    return base64.b64encode(data).decode("ascii")
