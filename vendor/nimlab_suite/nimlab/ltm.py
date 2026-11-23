"""Long-term memory: settings, what qualifies, embedding providers, local stores.

The entity's memory (nimlab.memory.MemoryCore) is a thin front over two
parts that are picked in settings (memory_settings.long_term in
config_cluster.json, testbed menu 5 -> 17, or `./start.sh memory ...`):

  storage backend   off | json   data/memory.json (the classic store)
                          | local  SQLite + in-process vector index in a
                                   directory you choose (default data/ltm/)
                          | oracle your Oracle 26ai database: a VECTOR
                                   column, a vector index, VECTOR_DISTANCE
                                   (see nimlab.ltm_oracle)
                          | ords   the same MEM tables over HTTPS through
                                   ORDS REST-Enabled SQL, basic or OAuth
                                   sign-in (see nimlab.ltm_ords)
  embedding provider role | nvidia | openai | ollama |
                     sentence_transformers | oracle (inside the database)

Nothing here ever stores a password or an API key: keys are read from the
environment (the variable name is the setting), and the database password
from env vars or a credentials file outside the project.
"""

import contextlib
import contextvars
import copy
import hashlib
import json
import math
import os
import re
import sqlite3
import struct
import threading
import time
from datetime import datetime, timedelta, timezone

from . import config

BACKENDS = ("auto", "off", "json", "local", "oracle", "ords")
SCOPES = ("shared", "user")
PROVIDERS = ("role", "nvidia", "openai", "ollama", "sentence_transformers", "oracle")
STORE_MODES = ("all", "salient", "facts")
DEDUPE_MODES = ("off", "exact", "semantic")
DEFAULT_NV_EMBED = "nvidia/llama-3.2-nv-embedqa-1b-v2"
# 3.7.1: embedding models setup and `memory embed models` know. dims = the
# size the hosted API returns by default (the memory table is VECTOR(2048)).
RECOMMENDED_EMBED = DEFAULT_NV_EMBED
KNOWN_EMBED = {
    "nvidia/llama-3.2-nv-embedqa-1b-v2": {
        "dims": 2048, "kind": "text", "input_type": "required",
        "note": "text Q&A retrieval, 26 languages, up to 8192 tokens; 2048 dimensions (384-2048 selectable); "
                "the working default for the VECTOR(2048) table"},
    "nvidia/llama-nemotron-embed-vl-1b-v2": {
        "dims": 2048, "kind": "vision+text", "input_type": "required",
        "note": "vision-language retrieval model; returned no vector on the phone in 3.7.0 (no input_type sent); "
                "3.7.1 sends input_type, still unconfirmed live"},
}
KNOWN_BAD_EMBED = {"nvidia/llama-nemotron-embed-vl-1b-v2"}
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LOCAL_DIR = "ltm"          # data/ltm/ unless a directory is set
LOCAL_DB = "memories.sqlite"

DEFAULTS = {
    # auto: the testbed's own setup in the MEM schema (oracle) when Oracle
    # credentials are found, else the json file
    "backend": "auto",
    # shared: every client of the served endpoint shares one continuous
    # memory. user: memories are tagged with the client's id (the OpenAI
    # `user` field or an X-Testbed-User header) and recall sees that client's
    # memories plus untagged ones
    "scope": "shared",
    "auto_store": True,
    "auto_recall": True,
    # scope "user": the key the terminal chat, voice calls and requests with no
    # `user` field share, so all of them recall the owner's memories
    "owner_user": "",
    # profile names this entity may never use (added to the built-in list of
    # the other agents on the shared MEM schema)
    "protected_profiles": [],
    # the built-in memory_search tool (semantic / keyword / both, in-process,
    # never MCP): auto = offered when the persona has a tool loop anyway,
    # on = always (no token streaming then), off = never
    "memory_search_tool": "auto",
    # v3.8.0: self-introductions ("my name is ...", "call me ...") are pinned as
    # identity facts for this user and put in front of Quill every turn
    "pin_identity": True,
    "identity_cache_sec": 15,       # oracle / ords only: how long a lookup is reused
    "identity_backfill_scan": 300,  # stored turns scanned once for older introductions
    "store_mode": "salient",
    "min_chars": 12,
    "dedupe": "exact",
    "dedupe_threshold": 0.95,
    "retention_days": 0,
    "max_records": 0,
    "retry_after_sec": 60,
    "local": {"directory": ""},
    "embedding": {"provider": "role", "url": "", "model": "", "dimensions": 0, "send_dimensions": False,
                  "api_key_env": "", "timeout_sec": 30, "query_prefix": "", "passage_prefix": "",
                  "device": ""},
    "max_chars": 2000,
    "oracle": {"schema": "MEM", "table_prefix": "TESTBED", "profile_id": "TESTBED",
               "register_profile": True, "credentials_file": "~/.config/nimlab/oracle_mem.json",
               "user": "", "dsn": "", "config_dir": "", "wallet_dir": "",
               "index": "ivf", "distance": "COSINE", "target_accuracy": 90, "onnx_model": "", "query_prefix": "", "dims": 0,
               "connect_timeout_sec": 15,
               # Oracle Text index on the memory text for keyword search (CONTAINS);
               # INSTR is used when Oracle Text is not available
               "text_index": True},
    # v3.7.1: the same MEM tables (the oracle settings above: schema, prefix,
    # profile, index...) reached over HTTPS through ORDS REST-Enabled SQL.
    # The password / client secret live only in credentials_file or env.
    "ords": {"base_url": "", "auth": "basic", "user": "", "client_id": "",
             "credentials_file": "~/.config/nimlab/ords_mem.json", "timeout_sec": 20},
}

# keys that must never be written to config_cluster.json
SECRET_KEYS = ("password", "wallet_password", "api_key", "secret", "token", "client_secret", "access_token")


class MemoryOffline(RuntimeError):
    """A backend or embedding provider could not be reached or refused."""


class EmbedError(MemoryOffline):
    pass


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def settings_from(memory_settings=None):
    """memory_settings (the whole section) or the long_term dict itself ->
    long_term merged over DEFAULTS."""
    ms = memory_settings or {}
    lt = ms.get("long_term") if isinstance(ms.get("long_term"), dict) else (
        ms if "backend" in ms or "embedding" in ms else {})
    out = config.deep_merge(copy.deepcopy(DEFAULTS), strip_secrets(lt))
    # one meaning for the on/off switches everywhere (a hand-edited "off"
    # string used to read as on in one place and off in another)
    for k in ("auto_store", "auto_recall", "pin_identity"):
        out[k] = as_bool(out.get(k), DEFAULTS[k])
    return out


def as_bool(v, default=True):
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("1", "on", "true", "yes", "y"):
        return True
    if s in ("0", "off", "false", "no", "n", ""):
        return False
    return default


def strip_secrets(d):
    if not isinstance(d, dict):
        return d
    return {k: strip_secrets(v) for k, v in d.items() if k.lower() not in SECRET_KEYS}


def oracle_configured(s, environ=None):
    """True when a user, password and DSN can be found for the Oracle backend."""
    from .ltm_oracle import load_credentials, missing_credentials
    try:
        creds, _ = load_credentials(s.get("oracle") or {}, environ)
    except Exception:  # noqa: BLE001 - a broken credentials file: not configured
        return False
    return not missing_credentials(creds)


def ords_configured(s, environ=None):
    """True when an ORDS base URL and its login can be found."""
    from .ltm_ords import load_credentials, missing_credentials
    try:
        creds, _ = load_credentials(s.get("ords") or {}, environ)
    except Exception:  # noqa: BLE001 - a broken credentials file: not configured
        return False
    return not missing_credentials(creds)


def resolve_backend(s, environ=None):
    """auto: the wallet login when there is one, else ORDS, else the json file."""
    b = s.get("backend") or "auto"
    if b == "auto":
        if oracle_configured(s, environ):
            return "oracle"
        return "ords" if ords_configured(s, environ) else "json"
    return b


def is_mem_schema(backend):
    """The two backends that keep memories in the MEM tables (one profile)."""
    return backend in ("oracle", "ords")


def local_dir(s):
    d = (s.get("local") or {}).get("directory") or ""
    if not d:
        from . import store
        return os.path.join(store.data_dir(), LOCAL_DIR)
    return os.path.abspath(os.path.expanduser(d))


def describe(s):
    """One line: where memories go and what embeds them."""
    b = resolve_backend(s)
    e = s.get("embedding") or {}
    auto = " (auto)" if s.get("backend") == "auto" else ""
    where = {"off": "off (no long-term memory)", "json": "json file data/memory.json",
             "local": f"local directory {local_dir(s)}"}.get(b)
    if b in ("oracle", "ords"):
        o = s.get("oracle") or {}
        via = ""
        if b == "ords":
            import urllib.parse
            u = urllib.parse.urlparse((s.get("ords") or {}).get("base_url") or "")
            via = f" via ORDS {u.netloc or '(base_url from the credentials file)'}"
        where = (f"Oracle {o.get('schema') or 'MEM'}.{(o.get('table_prefix') or 'TESTBED').upper()}_MEMORIES{via}, "
                 f"profile {o.get('profile_id') or 'TESTBED'}")
    p = e.get("provider", "role")
    emb = {"role": "the Embedding role", "nvidia": f"NVIDIA hosted {e.get('model') or DEFAULT_NV_EMBED}",
           "openai": f"OpenAI-compatible {e.get('url') or '(no URL set)'} model {e.get('model') or '?'}",
           "ollama": f"Ollama {e.get('url') or DEFAULT_OLLAMA_URL} model {e.get('model') or '?'}",
           "sentence_transformers": f"sentence-transformers {e.get('model') or DEFAULT_ST_MODEL} (in-process)",
           "oracle": f"in-database ONNX model {(s.get('oracle') or {}).get('onnx_model') or '(not set)'}"}.get(p, p)
    return f"{where}{auto}; embeddings: {emb}"


# ---------------------------------------------------------------------------
# What qualifies for storage
# ---------------------------------------------------------------------------
_CUE = re.compile(
    r"\b(remember|don'?t forget|keep in mind|note that|from now on|for future reference|my name|call me|"
    r"i am|i'm|i was|i live|i work|i study|i moved|i prefer|i like|i love|i hate|i dislike|i want|i need|"
    r"i have|i own|i use|i usually|i always|i never|i'll be|i will be|i'm allergic|allergic|birthday|"
    r"favou?rite|anniversary|my \w+(?: \w+)? (?:is|are|was|were|lives|works|called|named))\b", re.I)
_SMALL_TALK = re.compile(
    r"^\W*(hi|hey|hello|yo|sup|thanks|thank you|thx|ty|ok(ay)?|k|cool|nice|great|lol|lmao|haha|yes|yeah|yep|"
    r"no|nope|sure|bye|good ?night|good ?morning|gm|gn|hmm+|wow|test|testing|ping)\W*$", re.I)
_DONT = re.compile(r"\b(don'?t|do not|never) (remember|store|save|log|keep) (this|that|it)\b|\boff the record\b", re.I)
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def extract_facts(user_text, limit=5):
    """Sentences from the user's words that state something about them."""
    out = []
    for s in _SENT.split(user_text or ""):
        s = s.strip(" -*\t")
        if 8 <= len(s) <= 400 and _CUE.search(s) and not s.endswith("?") and not _DONT.search(s):
            out.append(s)
    return out[:limit]


def qualifies(user_text, s):
    """(store?, reason). Facts mode is decided by extract_facts."""
    u = (user_text or "").strip()
    if not u:
        return False, "empty"
    if _DONT.search(u):
        return False, "you asked not to remember it"
    mode = s.get("store_mode", "salient")
    if mode == "all":
        return True, "all turns"
    if mode == "facts":
        return bool(extract_facts(u)), "facts"
    if _CUE.search(u):
        return True, "memory cue"
    if _SMALL_TALK.match(u):
        return False, "small talk"
    if len(u) < int(s.get("min_chars", 12) or 0):
        return False, "too short"
    return True, "substantive"


# ---------------------------------------------------------------------------
# v3.8.0 recall fix: identity questions, self-introductions, what never to store
# ---------------------------------------------------------------------------
# "what's my name", "who am I", "what did I tell you", "do you remember me":
# questions about what the user told Quill before. They name no topic a vector
# can match well, so they also pull the newest memories and the pinned facts.
IDENTITY_ASK = re.compile(
    r"\b(my (actual |real |full |first |last )?name|who am i|who i am|what am i called|what (do|did) you call me"
    r"|what (did|have) i (tell|told|say|said|mention|mentioned)( to)? you|what i (told|said to) you"
    r"|do you (still )?(remember|know|recall) (me|who|my|what i)|remember me|what do you know about me"
    r"|what('?s| is| was) my\b)", re.I)

# the setup self-test's fixed prompts (nimlab.server.self_test): never memories
SELF_TEST_PROMPTS = ("reply with the single word: ready",
                     "who are you? answer in one or two sentences.",
                     "what is in this picture, and what do you hear in the clip?",
                     "generate an image of a red circle on a white background.")

# the assistant saying it does not know the user: storing it teaches the next
# recall to repeat it (the 3.7.2 "I do not remember who you are" bug)
_DENIAL = re.compile(
    r"\b(i (do not|don'?t|can'?t|cannot|could not|couldn'?t) (remember|recall|know|tell)|i have no (memory|record|idea)"
    r"|i don'?t have (any )?(memory|memories|record|information|info|details)|i'?m not sure who you are"
    r"|no (memory|record) of (you|your)|i (do not|don'?t) see (any|your))\b[^.!?\n]{0,60}"
    r"\b(you|your|name|who|earlier|before|told|said|us)\b", re.I)

_NO_STORE = contextvars.ContextVar("nimlab_no_store", default=None)


@contextlib.contextmanager
def no_store(reason="self-test"):
    """with no_store(): ... -- nothing said inside is saved as a memory (the
    server wraps self-test requests in this)."""
    tok = _NO_STORE.set(reason or "no store")
    try:
        yield
    finally:
        _NO_STORE.reset(tok)


def store_blocked():
    """The reason storing is off for this request, or None."""
    return _NO_STORE.get()


def is_self_test(user_text):
    u = re.sub(r"\s+", " ", (user_text or "").strip().lower())
    return any(u == p or u.startswith(p) for p in SELF_TEST_PROMPTS)


def is_denial(reply):
    """The reply says the assistant does not remember / know the user (in its
    first two sentences; a long answer that mentions it in passing is kept)."""
    r = (reply or "").strip()
    if not r:
        return False
    head = " ".join(_SENT.split(r)[:2])[:400]
    return bool(_DENIAL.search(head))


def split_turn(text):
    """'User: X | Assistant: Y' -> (X, Y); other memories -> (text, '')."""
    t = text or ""
    m = re.match(r"\s*User:\s*(.*?)\s*\|\s*Assistant:\s*(.*)\Z", t, re.S)
    return (m.group(1), m.group(2)) if m else (t, "")


def usable_memory(text):
    """False for stored turns that should never be recalled: self-test
    prompts and the assistant's 'I don't know who you are' answers (older
    versions stored them)."""
    u, a = split_turn(text)
    if is_self_test(u):
        return False
    if a and is_denial(a):
        return False
    return True


_NAME_STOP = {"not", "sorry", "fine", "good", "back", "here", "ok", "okay", "just", "so", "going", "the", "a",
              "an", "tired", "busy", "done", "ready", "sure", "glad", "happy", "home", "new", "still", "also",
              "trying", "looking", "using", "testing", "working", "asking", "wondering", "curious", "confused",
              "is", "was", "isn't", "wasn't", "what", "who", "your", "my", "in", "on", "at", "from", "and",
              "actually", "really", "called", "named", "bored", "hungry", "sick", "well", "great", "cool", "i",
              "and", "but", "or", "by", "btw", "fine", "alright", "sorry"}
_NAME = r"([A-Za-z][\w'\-]{0,30}(?:\s+[A-Z][\w'\-]{0,30}){0,2})"   # later words must be capitalized
_INTRO = (
    ("name", re.compile(r"\b(?i:my (?:first |full |real |actual )?name(?:'s| is| =))\s+" + _NAME)),
    ("name", re.compile(r"\b(?i:(?:you can |please |just )?call me)\s+" + _NAME)),
    ("name", re.compile(r"\b(?i:i(?:'m| am) called)\s+" + _NAME)),
    ("name", re.compile(r"\b(?i:i go by)\s+" + _NAME)),
    ("name", re.compile(r"(?:^|[.!,;]\s*|\b(?i:hi|hey|hello|yo)[,!]?\s+)[Ii](?:'m|\u2019m| am)\s+([A-Z][\w'\-]{1,30})"
                        r"(?=\s*(?:[.!,;]|$|\s+(?i:and|here|by the way|btw)\b))")),
    ("birthday", re.compile(r"\b(?i:my birthday is)\s+(?:on\s+)?([^.!?\n]{3,40})")),
    ("location", re.compile(r"\b(?i:i live in)\s+([^.!?\n,]{2,50})")),
    ("pronouns", re.compile(r"\b(?i:my pronouns are)\s+([^.!?\n,]{2,30})")),
)
_QUESTION_START = re.compile(r"\s*(is|isn'?t|what'?s?|who|whom|do|does|did|can|could|am|are|was|were|how|why|where|when|"
                             r"would|will|should|have|has|shall|may|might)\b", re.I)
IDENTITY_LABELS = {"name": "Name", "birthday": "Birthday", "location": "Lives in", "pronouns": "Pronouns"}
_IDENT_RE = re.compile(r"^\[identity:(\w+)\]\s*[^:]*:\s*(.*?)\s*$", re.S)


def extract_identity(user_text):
    """Self-introductions and identity facts in the user's words:
    {'name': 'SeVin', 'birthday': 'June 1'}. A question or a negation
    ('my name isn't Bob', 'is my name Bob?') is not a fact."""
    out = {}
    for s in _SENT.split(user_text or ""):
        s = s.strip()
        if not s or (s.endswith("?") and _QUESTION_START.match(s)) or _DONT.search(s) or re.search(r"\b(isn'?t|is not|not)\b\s*$", s, re.I):
            continue
        for key, rx in _INTRO:
            if key in out:
                continue
            m = rx.search(s)
            if not m:
                continue
            v = m.group(1).strip(" .,!;:'\"")
            if key == "name":
                words = v.split()
                while words and words[-1].lower() in _NAME_STOP:
                    words.pop()
                if not words or words[0].lower() in _NAME_STOP or re.search(r"\bnot\b", s[:m.start(1)], re.I):
                    continue
                v = " ".join(words)
            if v and len(v) <= 60:
                out[key] = v
    return out


def identity_text(key, value):
    """The stored form of a pinned identity fact."""
    return f"[identity:{key}] The user's {IDENTITY_LABELS.get(key, key).lower()}: {value}"


def parse_identity(text):
    """'[identity:name] ...: SeVin' -> ('name', 'SeVin'), else None."""
    m = _IDENT_RE.match(text or "")
    return (m.group(1), m.group(2)) if m else None


def identity_terms(query):
    """Extra keyword-search words for an identity question."""
    q = (query or "").lower()
    out = []
    if re.search(r"\bname\b|who am i|who i am|call me|called", q):
        out += ["name", "call me"]
    if "birthday" in q or "born" in q:
        out.append("birthday")
    if re.search(r"\b(live|from|where)\b", q):
        out.append("live in")
    return out


def fuse(lists, k=60, weights=None):
    """Reciprocal rank fusion of ranked hit lists [(score, text, ts, id)].
    A memory found by both the vector and the keyword search ranks above
    one found by either alone. -> [(fused, text, ts, id, sources)] best first,
    with fused scaled so the best possible single-list hit is 1.0."""
    weights = weights or [1.0] * len(lists)
    acc, meta = {}, {}
    for li, (hits, w) in enumerate(zip(lists, weights)):
        for rank, h in enumerate(hits or []):
            key = h[3] if h[3] is not None else (h[1] or "").strip()
            acc[key] = acc.get(key, 0.0) + w / (k + rank + 1)
            if key not in meta:
                meta[key] = [h, set()]
            meta[key][1].add(li)
    top = max(weights) / (k + 1) if weights else 1.0
    out = [(round(acc[key] / top, 4), m[0][1], m[0][2], m[0][3], sorted(m[1])) for key, m in meta.items()]
    out.sort(key=lambda x: x[0], reverse=True)
    return out


_KW_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "was", "were", "be", "it",
            "that", "this", "with", "as", "at", "by", "from", "what", "who", "when", "where", "how", "do", "did",
            "you", "me", "my", "we", "our", "i", "about", "any", "all", "can", "could", "would", "should", "find",
            "search", "look", "up", "memory", "memories", "remember", "recall"}


def keyword_terms(query, max_terms=8):
    """Search words for keyword mode: a quoted phrase stays whole; IDs, numbers
    and names are kept; common words are dropped. Lower-case, de-duplicated."""
    q = (query or "").strip()
    out = []
    for ph in re.findall(r'"([^"]{2,80})"', q):
        out.append(ph.lower().strip())
    q = re.sub(r'"[^"]*"', " ", q)
    for w in re.findall(r"[\w][\w.\-@:/#]*", q.lower()):
        w = w.strip(".-:/")
        if len(w) >= 2 and w not in _KW_STOP and w not in out:
            out.append(w)
    return out[:max_terms]


def quoted_phrase(query):
    m = re.search(r'"([^"]{2,80})"', query or "")
    return m.group(1).lower() if m else None


def keyword_rank(text, terms):
    """How many of the terms the text holds (0 = no match)."""
    low = (text or "").lower()
    return sum(1 for t in terms if t in low)


def text_hash(text):
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()


def cosine(v1, v2, n1=None, n2=None):
    if len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = n1 if n1 is not None else math.sqrt(sum(a * a for a in v1))
    n2 = n2 if n2 is not None else math.sqrt(sum(b * b for b in v2))
    if not n1 or not n2:
        return 0.0
    return dot / (n1 * n2)


def in_scope(rec_scope, scope):
    return scope is None or rec_scope in (None, "", scope)


def cutoff_iso(days):
    if not days or float(days) <= 0:
        return None
    return (datetime.now(timezone.utc) - timedelta(days=float(days))).isoformat()


# ---------------------------------------------------------------------------
# Embedding providers
# ---------------------------------------------------------------------------
class RoleEmbedder:
    """The Embedding role (an NVIDIA model or an MCP tool). Failures return
    None, as before v3.5: the turn is simply not stored."""
    in_db = False

    def __init__(self, client, label, fn=None):
        self.client, self.label, self.fn = client, label or "", fn
        self.last_error = ""

    def embed(self, text, input_type):
        """-> vector. v3.7.1: a failed call raises EmbedError with the HTTP
        status and the model's error text (it used to return None, which
        showed only as "no vector")."""
        if self.fn is not None:
            return self.fn(text, input_type)
        if not self.label or self.client is None:
            return None
        res = self.client.embed(self.label, [text], input_type=input_type)
        if res.ok and res.data and res.data[0]:
            self.last_error = ""
            return res.data[0]
        self.last_error = res.error or (f"HTTP {res.status}: no vector in the response" if res.status
                                        else "no vector in the response")
        raise EmbedError(f"{self.label}: {self.last_error}")


class _Prefixed:
    in_db = False

    def __init__(self, es):
        self.es = es
        self.dims = int(es.get("dimensions") or 0)

    def _text(self, text, input_type):
        pre = self.es.get("query_prefix" if input_type == "query" else "passage_prefix") or ""
        return pre + text

    def _check(self, vec):
        if not vec or not isinstance(vec, list):
            raise EmbedError(f"{self.label}: no vector returned")
        if self.dims and len(vec) != self.dims:
            raise EmbedError(f"{self.label}: returned {len(vec)} dimensions, settings say {self.dims}")
        return [float(x) for x in vec]


class NvidiaEmbedder(_Prefixed):
    """NVIDIA's hosted embedding NIMs with the lab's existing API key."""

    def __init__(self, es, client):
        super().__init__(es)
        self.client = client
        self.model = es.get("model") or DEFAULT_NV_EMBED
        self.url = es.get("url") or None
        self.label = self.model

    def embed(self, text, input_type):
        if self.client is None:
            raise EmbedError("no NVIDIA client")
        res = self.client.embed(self.model, [self._text(text, input_type)], input_type=input_type, url=self.url,
                                timeout=self.es.get("timeout_sec") or 30)
        if not res.ok or not res.data:
            raise EmbedError(f"NVIDIA {self.model}: {res.error or 'no data'}")
        return self._check(res.data[0])


def _http(http, timeout):
    if http is not None:
        return http
    from .core import HttpClient
    return HttpClient(timeout=timeout, retries=1)


class OpenAICompatEmbedder(_Prefixed):
    """Any OpenAI-compatible /v1/embeddings server: Ollama (/v1), LM Studio,
    llama.cpp, vLLM, text-embeddings-inference, LocalAI ..."""

    def __init__(self, es, http=None):
        super().__init__(es)
        url = (es.get("url") or "").rstrip("/")
        if not url:
            raise EmbedError("OpenAI-compatible embeddings need a URL (e.g. http://127.0.0.1:11434/v1)")
        self.url = url if url.endswith("/embeddings") else url + "/embeddings"
        self.model = es.get("model") or ""
        self.label = f"openai:{self.model}"
        self.http = _http(http, es.get("timeout_sec") or 30)

    def embed(self, text, input_type):
        body = {"model": self.model, "input": [self._text(text, input_type)], "encoding_format": "float"}
        if self.dims and self.es.get("send_dimensions"):
            body["dimensions"] = self.dims
        headers = {}
        env = self.es.get("api_key_env") or ""
        if env and os.environ.get(env):
            headers["Authorization"] = "Bearer " + os.environ[env].strip()
        r = self.http.post_json(self.url, body, headers=headers, timeout=self.es.get("timeout_sec") or 30)
        if not r.ok:
            raise EmbedError(f"{self.url}: {r.error or r.status} {r.text[:160]}")
        try:
            data = sorted(r.json()["data"], key=lambda d: d.get("index", 0))
            return self._check(data[0]["embedding"])
        except (KeyError, IndexError, TypeError) as e:
            raise EmbedError(f"{self.url}: unexpected reply ({e})")


class OllamaEmbedder(_Prefixed):
    """Ollama's native API: POST /api/embed (falls back to /api/embeddings)."""

    def __init__(self, es, http=None):
        super().__init__(es)
        self.base = (es.get("url") or DEFAULT_OLLAMA_URL).rstrip("/")
        for tail in ("/api/embed", "/api/embeddings", "/api"):
            if self.base.endswith(tail):
                self.base = self.base[: -len(tail)]
        self.model = es.get("model") or "nomic-embed-text"
        self.label = f"ollama:{self.model}"
        self.http = _http(http, es.get("timeout_sec") or 30)

    def embed(self, text, input_type):
        t = self._text(text, input_type)
        to = self.es.get("timeout_sec") or 30
        r = self.http.post_json(self.base + "/api/embed", {"model": self.model, "input": t}, timeout=to)
        if r.ok:
            try:
                return self._check(r.json()["embeddings"][0])
            except (KeyError, IndexError, TypeError):
                pass
        if r.status == 404 or r.ok:   # older Ollama
            r2 = self.http.post_json(self.base + "/api/embeddings", {"model": self.model, "prompt": t}, timeout=to)
            if r2.ok and isinstance(r2.json(), dict) and r2.json().get("embedding"):
                return self._check(r2.json()["embedding"])
            r = r2
        raise EmbedError(f"Ollama {self.base}: {r.error or r.status} {r.text[:160]}")


class SentenceTransformersEmbedder(_Prefixed):
    """sentence-transformers running in this process (pip install
    sentence-transformers). The model loads on first use."""

    def __init__(self, es):
        super().__init__(es)
        self.model_name = es.get("model") or DEFAULT_ST_MODEL
        self.label = f"st:{self.model_name}"
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError:
                    raise EmbedError("sentence-transformers is not installed (pip install sentence-transformers)")
                kw = {"device": self.es["device"]} if self.es.get("device") else {}
                try:
                    self._model = SentenceTransformer(self.model_name, **kw)
                except Exception as e:  # noqa: BLE001 - a download or load failure
                    raise EmbedError(f"could not load {self.model_name}: {e}")
        return self._model

    def embed(self, text, input_type):
        m = self._load()
        vec = m.encode([self._text(text, input_type)], normalize_embeddings=True)[0]
        return self._check(list(vec.tolist() if hasattr(vec, "tolist") else vec))


class InDatabaseEmbedder:
    """Marker: the Oracle backend embeds with VECTOR_EMBEDDING(model USING
    text AS data) inside the database; no vector leaves this process."""
    in_db = True

    def __init__(self, model):
        self.model = model or ""
        self.label = f"oracle:{self.model}"

    def embed(self, text, input_type):
        return None


def make_embedder(s, client=None, role_label="", role_fn=None, http=None):
    es = s.get("embedding") or {}
    p = es.get("provider") or "role"
    if p == "role":
        return RoleEmbedder(client, role_label, role_fn)
    if p == "nvidia":
        return NvidiaEmbedder(es, client)
    if p == "openai":
        return OpenAICompatEmbedder(es, http)
    if p == "ollama":
        return OllamaEmbedder(es, http)
    if p == "sentence_transformers":
        return SentenceTransformersEmbedder(es)
    if p == "oracle":
        if resolve_backend(s) not in ("oracle", "ords"):
            raise EmbedError("in-database embedding needs the oracle or ords backend")
        return InDatabaseEmbedder((s.get("oracle") or {}).get("onnx_model"))
    raise EmbedError(f"unknown embedding provider {p!r}")


# ---------------------------------------------------------------------------
# Storage backends. Every backend answers the same calls:
#   add(rec) -> id     rec: id, timestamp, text, kind, embed_model, dims,
#                      vector (None for in-db), metadata, turn_key, text_hash,
#                      scope (None = shared)
#   search(vec, label, k, threshold, query_text=None, scope=None)
#                      -> [(sim, text, ts, id)]; scope None = everything,
#                      else that scope's records plus untagged ones
#   find(turn_key=None, text_hash=None, scope=None) -> id or None
#   touch(id)  delete(id)  count()  incompatible(label)  prune(days, max)
#   records(limit) -> [rec]   test() -> [(ok, message)]   where()
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def file_lock(path, timeout=10.0):
    """An exclusive lock on <path>.lock (fcntl; a no-op where fcntl is
    missing). Two processes writing the same memory file take turns."""
    try:
        import fcntl
    except ImportError:  # pragma: no cover - not on Termux / Linux
        yield
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        end = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > end:
                    raise MemoryOffline(f"memory file {path} stayed locked for {timeout:g} s")
                time.sleep(0.02)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


class JsonBackend:
    """The classic data/memory.json list (default; unchanged file format).

    v3.8.0: safe with more than one process (the Telegram bot in the
    background and a terminal chat). Reads reload the file when another
    process changed it; every write takes a file lock, re-reads the file and
    merges: records added elsewhere are kept, records deleted elsewhere stay
    deleted, and nothing another process wrote is overwritten."""
    name = "json"

    def __init__(self, path):
        from .memory import clean_records
        self.path = path
        self._lock = threading.RLock()
        self._known = set()      # ids in the file at the last load or save
        self._changed = set()    # ids this process touched since then
        self._deleted = set()    # ids this process deleted since then
        self._sig = None
        raw = self._read()
        self.list = clean_records(raw)
        self._known = {m.get("id") for m in self.list}
        if len(self.list) != len(raw) or any(a is not b for a, b in zip(self.list, raw)):
            self.save()

    def where(self):
        return self.path

    def _stat(self):
        try:
            st = os.stat(self.path)
            return (st.st_mtime_ns, st.st_size, st.st_ino)
        except OSError:
            return None

    def _read(self):
        self._sig = self._stat()
        raw = config.load_json(self.path, []) or []
        return raw if isinstance(raw, list) else []

    def refresh(self):
        """Reload when another process wrote the file since we last looked.
        -> True when it reloaded."""
        from .memory import clean_records
        with self._lock:
            if self._stat() == self._sig:
                return False
            self.list = clean_records(self._read())
            self._known = {m.get("id") for m in self.list}
            self._changed.clear()
            self._deleted.clear()
            return True

    def save(self):
        from .memory import clean_records
        with self._lock, file_lock(self.path):
            disk = clean_records(self._read()) if os.path.exists(self.path) else []
            mine = {m.get("id"): m for m in self.list}
            out, seen = [], set()
            for m in disk:
                rid = m.get("id")
                if rid in self._deleted:
                    continue
                out.append(mine[rid] if rid in self._changed and rid in mine else m)
                seen.add(rid)
            for m in self.list:
                rid = m.get("id")
                # added here since the last load: append; known but gone from
                # the file: another process deleted (pruned) it, so it stays gone
                if rid not in seen and rid not in self._known and rid not in self._deleted:
                    out.append(m)
                    seen.add(rid)
            config.save_json(self.path, out)
            self.list = out
            self._known = seen
            self._changed.clear()
            self._deleted.clear()
            self._sig = self._stat()

    def add(self, rec):
        r = {k: rec[k] for k in ("id", "timestamp", "text", "embed_model", "dims", "vector", "metadata")}
        md = dict(r.get("metadata") or {})
        if rec.get("turn_key"):
            md.setdefault("turn_key", rec["turn_key"])
        if rec.get("kind") and rec["kind"] != "turn":
            md.setdefault("kind", rec["kind"])
        if rec.get("scope"):
            md.setdefault("scope", rec["scope"])
        r["metadata"] = md
        with self._lock:
            self.list.append(r)
            self.save()
        return r["id"]

    def search(self, vec, label, k, threshold, query_text=None, scope=None):
        self.refresh()
        ranked = []
        for item in self.list:
            if not in_scope((item.get("metadata") or {}).get("scope"), scope):
                continue
            model = item.get("embed_model")
            v = item.get("vector") or []
            if (model and model != label) or len(v) != len(vec):
                continue
            sim = cosine(vec, v)
            if sim >= threshold:
                ranked.append((sim, item["text"], item.get("timestamp"), item["id"]))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked[:k]

    def keyword_search(self, terms, k, scope=None, phrase=None):
        """Substring match on the text, ranked by how many terms match (a
        quoted phrase counts double)."""
        self.refresh()
        ranked = []
        for item in self.list:
            if not in_scope((item.get("metadata") or {}).get("scope"), scope):
                continue
            n = keyword_rank(item.get("text"), terms) + (1 if phrase and phrase in (item.get("text") or "").lower() else 0)
            if n:
                ranked.append((n / (len(terms) + (1 if phrase else 0)), item.get("text") or "", item.get("timestamp"),
                               item.get("id")))
        ranked.sort(key=lambda x: (x[0], x[2] or ""), reverse=True)
        return ranked[:k]

    def keyword_mode(self):
        return "substring scan of data/memory.json"

    def by_kind(self, kind, limit=20, scope=None):
        """Records of one kind (identity facts), newest first."""
        self.refresh()
        out = [m for m in self.list if (m.get("metadata") or {}).get("kind") == kind
               and in_scope((m.get("metadata") or {}).get("scope"), scope)]
        out.sort(key=lambda m: m.get("timestamp") or "", reverse=True)
        return [{"id": m.get("id"), "timestamp": m.get("timestamp"), "text": m.get("text") or "",
                 "kind": kind, "scope": (m.get("metadata") or {}).get("scope")} for m in out[:int(limit)]]

    def find(self, turn_key=None, text_hash=None, scope=None):
        self.refresh()
        for m in self.list:
            md = m.get("metadata") or {}
            if not in_scope(md.get("scope"), scope):
                continue
            if turn_key and md.get("turn_key") == turn_key:
                return m["id"]
            if text_hash and globals()["text_hash"](m.get("text", "")) == text_hash:
                return m["id"]
        return None

    def touch(self, rid):
        with self._lock:
            self.refresh()
            for m in self.list:
                if m["id"] == rid:
                    md = m.setdefault("metadata", {})
                    md["last_seen"] = config.timestamp()
                    md["hits"] = int(md.get("hits", 1)) + 1
                    self._changed.add(rid)
                    self.save()
                    return True
        return False

    def delete(self, rid):
        with self._lock:
            self.refresh()
            before = len(self.list)
            self.list[:] = [m for m in self.list if m["id"] != rid]
            if len(self.list) != before:
                self._deleted.add(rid)
                self.save()
                return True
        return False

    def count(self):
        self.refresh()
        return len(self.list)

    def incompatible(self, label):
        return sum(1 for m in self.list if m.get("embed_model") not in (None, label))

    def prune(self, days=0, max_records=0):
        self.refresh()
        cutoff = cutoff_iso(days)
        keep = self.list
        if cutoff:
            keep = [m for m in keep if ((m.get("metadata") or {}).get("last_seen") or m.get("timestamp") or "")
                    >= cutoff]
        if max_records and len(keep) > max_records:
            keep = sorted(keep, key=lambda m: (m.get("metadata") or {}).get("last_seen") or m.get("timestamp") or "")
            keep = keep[-int(max_records):]
        n = len(self.list) - len(keep)
        if n:
            ids = {m["id"] for m in keep}
            with self._lock:
                self._deleted |= {m["id"] for m in self.list if m["id"] not in ids}
                self.list[:] = [m for m in self.list if m["id"] in ids]
                self.save()
        return n

    def records(self, limit=50):
        self.refresh()
        return list(self.list[-limit:]) if limit else list(self.list)

    def test(self):
        d = os.path.dirname(os.path.abspath(self.path))
        ok = os.access(d, os.W_OK) or not os.path.exists(d)
        return [(ok, f"json file {self.path}: {len(self.list)} memories, "
                     f"{'writable' if ok else 'NOT writable'}")]


def _pack(vec):
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack(blob):
    return list(struct.unpack(f"<{len(blob) // 4}f", blob)) if blob else []


class LocalBackend:
    """A plain on-disk store in a directory: memories.sqlite holds the text,
    metadata and float32 vectors; the vector index is an in-process matrix
    with precomputed norms, built on first search and kept in step with
    every write. No outside service, no extra packages."""
    name = "local"
    SCHEMA = ("CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, "
              "last_seen_at TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'turn', text TEXT NOT NULL, "
              "text_hash TEXT NOT NULL, turn_key TEXT, embed_label TEXT NOT NULL, dims INTEGER NOT NULL, "
              "vector BLOB NOT NULL, metadata TEXT, hits INTEGER NOT NULL DEFAULT 1, scope TEXT)",
              "CREATE INDEX IF NOT EXISTS memories_turn_key ON memories (turn_key)",
              "CREATE INDEX IF NOT EXISTS memories_hash ON memories (text_hash)",
              "CREATE INDEX IF NOT EXISTS memories_label ON memories (embed_label)",
              "CREATE INDEX IF NOT EXISTS memories_seen ON memories (last_seen_at)",
              "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")

    def __init__(self, directory):
        self.directory = directory
        self.path = os.path.join(directory, LOCAL_DB)
        self._lock = threading.RLock()
        self._index = None   # {id: (label, vector, norm, text, created_at, scope)}
        self._dv = None      # sqlite data_version when the index was last in step
        try:
            os.makedirs(directory, exist_ok=True)
            self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
            for stmt in self.SCHEMA:
                self.db.execute(stmt)
            cols = [r[1] for r in self.db.execute("PRAGMA table_info(memories)")]
            if "scope" not in cols:
                self.db.execute("ALTER TABLE memories ADD COLUMN scope TEXT")
            self.db.execute("INSERT OR IGNORE INTO meta VALUES ('format', 'nimlab-ltm-1')")
            self.fts = self._setup_fts()
            self.db.commit()
        except (OSError, sqlite3.Error) as e:
            raise MemoryOffline(f"local store {self.path}: {e}")

    def where(self):
        return self.path

    def _setup_fts(self):
        """v3.7.1: an FTS5 index on the text for keyword search, kept in step
        by triggers. Without FTS5 in this sqlite build, keyword search falls
        back to LIKE."""
        try:
            new = not self.db.execute("SELECT name FROM sqlite_master WHERE name = 'memories_fts'").fetchall()
            self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(text, content='memories', "
                            "content_rowid='rowid')")
            self.db.execute("CREATE TRIGGER IF NOT EXISTS memories_fts_ai AFTER INSERT ON memories BEGIN "
                            "INSERT INTO memories_fts(rowid, text) VALUES (new.rowid, new.text); END")
            self.db.execute("CREATE TRIGGER IF NOT EXISTS memories_fts_ad AFTER DELETE ON memories BEGIN "
                            "INSERT INTO memories_fts(memories_fts, rowid, text) VALUES ('delete', old.rowid, old.text); END")
            if new:
                self.db.execute("INSERT INTO memories_fts(memories_fts) VALUES ('rebuild')")
            return True
        except sqlite3.Error:
            return False

    def keyword_mode(self):
        return "sqlite FTS5 index" if self.fts else "sqlite LIKE"

    def keyword_search(self, terms, k, scope=None, phrase=None):
        sc = "" if scope is None else " AND (m.scope IS NULL OR m.scope = '' OR m.scope = ?)"
        extra = () if scope is None else (scope,)
        rows = None
        if self.fts:
            q = " OR ".join('"' + t.replace('"', '""') + '"' for t in terms)
            try:
                rows, _ = self._run("SELECT m.id, m.text, m.created_at FROM memories_fts JOIN memories m ON "
                                    "m.rowid = memories_fts.rowid WHERE memories_fts MATCH ?" + sc +
                                    " ORDER BY bm25(memories_fts) LIMIT ?", (q,) + extra + (int(k) * 3,))
            except MemoryOffline:
                rows = None
        if rows is None:
            where = " OR ".join("LOWER(m.text) LIKE ?" for _ in terms)
            rows, _ = self._run(f"SELECT m.id, m.text, m.created_at FROM memories m WHERE ({where}){sc} "
                                "ORDER BY m.created_at DESC LIMIT ?",
                                tuple(f"%{t}%" for t in terms) + extra + (int(k) * 3,))
        out = []
        for rid, text, ts in rows:
            n = keyword_rank(text, terms) + (1 if phrase and phrase in (text or "").lower() else 0)
            out.append((max(n, 1) / (len(terms) + (1 if phrase else 0)), text, ts, rid))
        out.sort(key=lambda x: x[0], reverse=True)
        return out[:k]

    def _run(self, sql, args=(), commit=False):
        with self._lock:
            try:
                cur = self.db.execute(sql, args)
                rows = cur.fetchall()
                if commit:
                    self.db.commit()
                return rows, cur.rowcount
            except sqlite3.Error as e:
                raise MemoryOffline(f"local store {self.path}: {e}")

    def _data_version(self):
        try:
            return self._run("PRAGMA data_version")[0][0][0]
        except (MemoryOffline, IndexError):
            return None

    def refresh(self):
        """v3.8.0: bring the in-process vector index up to date with rows
        another process (the Telegram bot in the background) added or
        deleted. sqlite's data_version changes only on other connections'
        commits, so this costs one PRAGMA when nothing changed.
        -> True when the index changed."""
        with self._lock:
            dv = self._data_version()
            if self._index is None or dv == self._dv:
                self._dv = dv
                return False
            self._dv = dv
            rows, _ = self._run("SELECT id FROM memories")
            ids = {r[0] for r in rows}
            gone = [rid for rid in self._index if rid not in ids]
            for rid in gone:
                self._index.pop(rid, None)
            new = [rid for rid in ids if rid not in self._index]
            for i in range(0, len(new), 500):
                part = new[i:i + 500]
                got, _ = self._run("SELECT id, embed_label, vector, text, created_at, scope FROM memories WHERE id IN ("
                                   + ",".join("?" * len(part)) + ")", tuple(part))
                for rid, label, blob, text, ts, sc in got:
                    v = _unpack(blob)
                    self._index[rid] = (label, v, math.sqrt(sum(x * x for x in v)), text, ts, sc)
            return bool(gone or new)

    def _load_index(self):
        with self._lock:
            if self._index is None:
                self._dv = self._data_version()
                rows, _ = self._run("SELECT id, embed_label, vector, text, created_at, scope FROM memories")
                self._index = {}
                for rid, label, blob, text, ts, sc in rows:
                    v = _unpack(blob)
                    self._index[rid] = (label, v, math.sqrt(sum(x * x for x in v)), text, ts, sc)
            else:
                self.refresh()
            return self._index

    def by_kind(self, kind, limit=20, scope=None):
        """Records of one kind (identity facts), newest first."""
        sc = "" if scope is None else " AND (scope IS NULL OR scope = '' OR scope = ?)"
        rows, _ = self._run("SELECT id, created_at, text, scope FROM memories WHERE kind = ?" + sc +
                            " ORDER BY created_at DESC LIMIT ?", (kind,) + (() if scope is None else (scope,))
                            + (int(limit),))
        return [{"id": r[0], "timestamp": r[1], "text": r[2], "kind": kind, "scope": r[3]} for r in rows]

    def add(self, rec):
        vec = rec["vector"]
        self._run("INSERT INTO memories (id, created_at, last_seen_at, kind, text, text_hash, turn_key, embed_label, "
                  "dims, vector, metadata, scope) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (rec["id"], rec["timestamp"], rec["timestamp"], rec.get("kind") or "turn", rec["text"],
                   rec["text_hash"], rec.get("turn_key"), rec["embed_model"], len(vec), _pack(vec),
                   json.dumps(rec.get("metadata") or {}, ensure_ascii=False), rec.get("scope")), commit=True)
        if self._index is not None:
            self._index[rec["id"]] = (rec["embed_model"], list(vec), math.sqrt(sum(x * x for x in vec)),
                                      rec["text"], rec["timestamp"], rec.get("scope"))
        return rec["id"]

    def search(self, vec, label, k, threshold, query_text=None, scope=None):
        qn = math.sqrt(sum(x * x for x in vec))
        ranked = []
        for rid, (lbl, v, n, text, ts, sc) in self._load_index().items():
            if lbl != label or len(v) != len(vec) or not in_scope(sc, scope):
                continue
            sim = cosine(vec, v, qn, n)
            if sim >= threshold:
                ranked.append((sim, text, ts, rid))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked[:k]

    def find(self, turn_key=None, text_hash=None, scope=None):
        sc = "" if scope is None else " AND (scope IS NULL OR scope = '' OR scope = ?)"
        extra = () if scope is None else (scope,)
        if turn_key:
            rows, _ = self._run("SELECT id FROM memories WHERE turn_key = ?" + sc + " LIMIT 1", (turn_key,) + extra)
            if rows:
                return rows[0][0]
        if text_hash:
            rows, _ = self._run("SELECT id FROM memories WHERE text_hash = ?" + sc + " LIMIT 1", (text_hash,) + extra)
            if rows:
                return rows[0][0]
        return None

    def touch(self, rid):
        _, n = self._run("UPDATE memories SET last_seen_at = ?, hits = hits + 1 WHERE id = ?",
                         (config.timestamp(), rid), commit=True)
        return n > 0

    def delete(self, rid):
        _, n = self._run("DELETE FROM memories WHERE id = ?", (rid,), commit=True)
        if self._index is not None:
            self._index.pop(rid, None)
        return n > 0

    def count(self):
        return self._run("SELECT COUNT(*) FROM memories")[0][0][0]

    def incompatible(self, label):
        return self._run("SELECT COUNT(*) FROM memories WHERE embed_label <> ?", (label,))[0][0][0]

    def prune(self, days=0, max_records=0):
        cutoff = cutoff_iso(days)
        n = 0
        if cutoff:
            n += self._run("DELETE FROM memories WHERE last_seen_at < ?", (cutoff,), commit=True)[1]
        if max_records:
            n += self._run("DELETE FROM memories WHERE id NOT IN (SELECT id FROM memories ORDER BY last_seen_at "
                           "DESC LIMIT ?)", (int(max_records),), commit=True)[1]
        if n:
            self._index = None
        return max(0, n)

    def records(self, limit=50):
        rows, _ = self._run("SELECT id, created_at, text, embed_label, dims, metadata, kind, scope FROM memories "
                            "ORDER BY created_at DESC" + (" LIMIT ?" if limit else ""),
                            (int(limit),) if limit else ())
        out = []
        for rid, ts, text, label, dims, md, kind, scope in reversed(rows):
            out.append({"id": rid, "timestamp": ts, "text": text, "embed_model": label, "dims": dims,
                        "metadata": json.loads(md or "{}"), "kind": kind, "scope": scope})
        return out

    def test(self):
        n = self.count()
        labels = self._run("SELECT embed_label, COUNT(*) FROM memories GROUP BY embed_label")[0]
        return [(True, f"local store {self.path}: {n} memories"
                       + (" (" + ", ".join(f"{c} from {lbl}" for lbl, c in labels) + ")" if labels else ""))]


def make_backend(s, json_path=None, log=None):
    b = resolve_backend(s)
    if b == "off":
        return None
    if b == "json":
        if json_path is None:
            from . import store
            store.ensure_all()
            json_path = store.path(store.MEMORY)
        return JsonBackend(json_path)
    if b == "local":
        return LocalBackend(local_dir(s))
    if b == "oracle":
        from .ltm_oracle import OracleBackend
        return OracleBackend(s.get("oracle") or {}, embed_model=(s.get("oracle") or {}).get("onnx_model")
                             if (s.get("embedding") or {}).get("provider") == "oracle" else None, log=log)
    if b == "ords":
        from .ltm_ords import OrdsBackend
        return OrdsBackend(s.get("oracle") or {}, s.get("ords") or {},
                           embed_model=(s.get("oracle") or {}).get("onnx_model")
                           if (s.get("embedding") or {}).get("provider") == "oracle" else None, log=log)
    raise MemoryOffline(f"unknown memory backend {b!r}")


def now_monotonic():
    return time.monotonic()
