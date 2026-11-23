"""MemoryCore: small JSON vector store for the orchestrator testbed.

Fixes over the original:
  * error replies are never stored (and old error records are dropped on load)
  * record ids are random UUIDs, so deletions can never cause collisions
  * vectors carry the embedding model + dimension; recall skips records from a
    different model instead of silently comparing mismatched vectors
  * writes are atomic
"""

import json
import math
import os
import re
import uuid

from . import config

MEMORY_FILE = "memory.json"  # data/memory.json, path owned by nimlab.store
_ERROR_RE = re.compile(r"\[(?:[A-Z ]+ )?ERROR\b[^\]]*\]", re.IGNORECASE)


def is_error_text(text):
    """True for failed replies like '[ERROR None]: ...' or '[VISION ERROR 500]: ...'."""
    if not isinstance(text, str):
        return True
    t = text.strip()
    if not t:
        return True
    if _ERROR_RE.match(t):
        return True
    # turn records look like 'User: ... | Assistant: <reply>'
    _, sep, reply = t.partition("| Assistant:")
    return bool(sep) and bool(_ERROR_RE.match(reply.strip()))


def cosine_similarity(v1, v2):
    if len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def new_id():
    return "mem_" + uuid.uuid4().hex


def clean_records(records):
    """Drop error records and give every record a safe unique id."""
    out, seen = [], set()
    for r in records or []:
        if not isinstance(r, dict) or is_error_text(r.get("text", "")) or not r.get("vector"):
            continue
        rid = r.get("id")
        if not isinstance(rid, str) or rid in seen:
            r = dict(r, id=new_id())
        seen.add(r["id"])
        out.append(r)
    return out


class MemoryCore:
    """The entity's long-term memory. The storage backend and the embedding
    provider are picked in memory_settings.long_term (see nimlab.ltm);
    without settings this is the classic data/memory.json store embedded by
    the Embedding role, exactly as before v3.6.

    Never raises into a chat turn: when the backend or the embedder cannot be
    reached it warns once, works with no memory, and tries again after
    retry_after_sec."""

    def __init__(self, client, embed_model, path=None, embed_fn=None, settings=None, log=None,
                 backend=None, embedder=None, http=None):
        from . import ltm
        self.client = client
        self.embed_model = embed_model          # the Embedding role's label
        # embed_fn(text, input_type) -> vector or None; set when the embedding
        # role is backed by an MCP tool (embed_model is then "mcp:<tool>")
        self.embed_fn = embed_fn
        self.log = log
        self.settings = ltm.settings_from(settings)
        if path is not None and settings is None:
            self.settings["backend"] = "json"
        self.path = path
        self._http = http
        self._embedder_given = embedder
        self._backend_given = backend
        self.backend = None
        self.offline = None        # reason the store is unreachable, or None
        self.last_error = None
        self.warnings = []
        self._retry_at = 0.0
        self._stores = 0
        self.scope = None          # the client id for this request (scope "user"), set by the server
        self.last_turn = {}        # what the last exchange recalled and stored (for the server trace)
        self.last_near_miss = []   # best hits just under the recall threshold (trace only)
        self._pending_count = 0
        self._ident_cache = {}     # scope -> (monotonic time, {key: value}) for remote stores
        self._backfilled = set()   # scopes already scanned for pre-3.8.0 self-introductions
        self._connect(first=True)
        self._pending_count = len(self.pending())

    # -- wiring ---------------------------------------------------------------
    def _scope(self):
        if self.settings.get("scope") == "user":
            # the terminal chat, voice calls and requests without a `user` field
            # share the owner's key (long_term.owner_user), so they recall the same memories
            who = self.scope or (self.settings.get("owner_user") or "").strip()
            if who:
                return str(who)[:128]
        return None

    def scoped(self, client_id):
        """with mem.scoped(id): ... -- the server sets the client id for one
        request. Ignored unless memory scope is "user"."""
        import contextlib

        @contextlib.contextmanager
        def cm():
            old, self.scope = self.scope, client_id
            try:
                yield self
            finally:
                self.scope = old
        return cm()

    @property
    def backend_name(self):
        from . import ltm
        return ltm.resolve_backend(self.settings)

    def _connect(self, first=False):
        from . import ltm
        self._retry_at = 0.0
        if self.settings.get("backend") == "off":
            self.backend, self.offline = None, None
            return
        try:
            if self._backend_given is not None:
                self.backend = self._backend_given
            else:
                self.backend = ltm.make_backend(self.settings, json_path=self.path, log=self.log)
            self.offline = None
            if first:
                self.prune()
        except Exception as e:  # noqa: BLE001 - any backend failure degrades to no memory
            self._go_offline(e)

    def _go_offline(self, e):
        from . import ltm
        reason = str(e) or type(e).__name__
        if self.offline != reason:
            self.warn(f"long-term memory unavailable ({self.backend_name}): {reason}; "
                      "continuing without memory")
        self.offline = reason
        self.backend = None
        self._retry_at = ltm.now_monotonic() + float(self.settings.get("retry_after_sec") or 60)

    def warn(self, msg):
        self.warnings = (self.warnings + [msg])[-20:]
        if self.log is not None:
            try:
                self.log.warning(msg) if hasattr(self.log, "warning") else self.log(msg)
            except Exception:  # noqa: BLE001
                pass

    def where(self):
        """Where the memories live, for trace lines: a table, file or path."""
        b = self.backend
        try:
            return b.where() if b is not None else ""
        except Exception:  # noqa: BLE001
            return ""

    def _live(self):
        """The backend, reconnecting after retry_after_sec when offline."""
        from . import ltm
        if self.backend is None and self.offline and ltm.now_monotonic() >= self._retry_at:
            self._connect()
        return self.backend

    def reconfigure(self, settings):
        from . import ltm
        old = self.backend
        self.settings = ltm.settings_from(settings)
        self._backend_given = None
        if old is not None and hasattr(old, "close"):
            try:
                old.close()
            except Exception:  # noqa: BLE001
                pass
        self.backend = None
        self.offline = None
        self._connect(first=True)

    @property
    def embedder(self):
        from . import ltm
        if self._embedder_given is not None:
            return self._embedder_given
        import json as _json
        key = (_json.dumps(self.settings.get("embedding"), sort_keys=True), self.settings.get("backend"),
               _json.dumps(self.settings.get("oracle"), sort_keys=True), self.embed_model, id(self.embed_fn),
               id(self.client))
        if getattr(self, "_emb_key", None) != key:
            self._emb = ltm.make_embedder(self.settings, client=self.client, role_label=self.embed_model,
                                          role_fn=self.embed_fn, http=self._http)
            self._emb_key = key
        return self._emb

    @property
    def label(self):
        """What vectors are tagged with: only vectors with the same label are
        ever compared."""
        try:
            return self.embedder.label
        except Exception:  # noqa: BLE001
            return "?"

    @property
    def memories(self):
        """The records (the live list for the json backend)."""
        b = self.backend
        if b is None:
            return []
        if hasattr(b, "list"):
            return b.list
        try:
            return b.records(0)
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return []

    def save(self):
        if self.backend is not None and hasattr(self.backend, "save"):
            self.backend.save()

    def embed(self, text, input_type):
        # Quill latency fix (3.8.4 candidate): after a failed embedding call, skip the provider for
        # embedding.cooldown_sec (0 = off, the 3.8.3 behaviour) so every turn does not wait out the
        # same timeout again. Recall falls back to keyword search; stores go to the pending queue.
        import time as _time
        now = _time.monotonic()
        if now < getattr(self, "_embed_down_until", 0.0):
            return None
        try:
            emb = self.embedder
            return emb.embed(text, input_type)
        except Exception as e:  # noqa: BLE001 - provider down: nothing stored or recalled
            self.last_error = str(e)
            try:
                cool = float((self.settings.get("embedding") or {}).get("cooldown_sec", 0) or 0)
            except (TypeError, ValueError):
                cool = 0.0
            if cool > 0:
                self._embed_down_until = _time.monotonic() + cool
                self.warn(f"embedding failed: {e} (skipping embeddings for {cool:g} s)")
            else:
                self.warn(f"embedding failed: {e}")
            return None

    # -- dimensions and the pending queue (v3.7.1) ---------------------------
    def table_dims(self):
        """The vector size the store holds (Oracle: the table's VECTOR(n)), 0
        when it takes any size."""
        b = self.backend
        try:
            return int(getattr(b, "dims", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def dims_problem(self, got, want):
        where = self.where() or self.backend_name
        return (f"the embedder {self.label} returns {got} dimensions but {where} holds VECTOR({want}): pick an "
                f"embedding model with {want} dimensions (nimlab memory embed models), or re-embed the stored "
                f"memories at the new size (nimlab memory reembed --recreate: backs up, recreates the table, re-adds)")

    def pending_path(self):
        """Next to the json/local store; the data dir for Oracle (one per profile)."""
        from . import store
        if self.settings.get("pending_path"):
            return os.path.expanduser(self.settings["pending_path"])
        be = self.settings.get("backend")
        b = self.backend if self.backend is not None else self._backend_given
        bp = getattr(b, "path", None) if b is not None else None
        if be in ("json", "local") or (bp and getattr(b, "name", "") in ("json", "local")):
            if isinstance(bp, str) and bp:
                return bp + ".pending.jsonl"
            d = (self.settings.get("local") or {}).get("directory") or self.path
            if d:
                return os.path.expanduser(d) + (".pending.jsonl" if str(d).endswith(".json") else "/pending.jsonl")
        pid = ((self.settings.get("oracle") or {}).get("profile_id") or "TESTBED").upper()
        mem_schema = be in ("oracle", "ords") or (be == "auto" and self.backend_name in ("oracle", "ords"))
        return os.path.join(store.data_dir(), f"ltm_pending_{pid if mem_schema else be or 'mem'}.jsonl")

    def pending(self):
        """Turns waiting for an embedding: [dict] oldest first."""
        p = self.pending_path()
        out = []
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            out.append(json.loads(line))
                        except ValueError:
                            continue
        except OSError:
            pass
        return out

    def _write_pending(self, items):
        p = self.pending_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        os.replace(tmp, p)
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
        self._pending_count = len(items)

    def queue_pending(self, text, kind="turn", metadata=None, turn_key=None, text_hash=None, scope=None,
                      reason=""):
        from . import ltm
        items = self.pending()
        h = text_hash or ltm.text_hash(text)
        if any(it.get("text_hash") == h and it.get("scope") == scope for it in items):
            return len(items)
        cap = int(self.settings.get("pending_max") or 500)
        items.append({"id": new_id(), "timestamp": config.timestamp(), "text": text, "kind": kind,
                      "metadata": metadata or {}, "turn_key": turn_key, "text_hash": h, "scope": scope,
                      "reason": str(reason)[:300]})
        items = items[-cap:]
        self._write_pending(items)
        self.warn(f"[memory] store: not embedded ({str(reason)[:160]}); turn queued, {len(items)} waiting for an "
                  "embedding (keyword search still finds them)")
        return len(items)

    def embed_pending(self, limit=50):
        """Embed and store the queued turns. -> (stored, left)."""
        items = self.pending()
        if not items:
            return 0, 0
        b = self._live()
        if b is None:
            return 0, len(items)
        stored, left, want = 0, [], self.table_dims()
        for i, it in enumerate(items):
            if i >= limit:
                left.extend(items[i:])
                break
            emb = self.embedder
            vec = None if emb.in_db else self.embed(it["text"], "passage")
            if (not emb.in_db and not vec) or (vec and want and len(vec) != want):
                left.extend(items[i:])       # still failing: stop, keep the rest
                break
            rec = {"id": it.get("id") or new_id(), "timestamp": it.get("timestamp") or config.timestamp(),
                   "text": it["text"], "kind": it.get("kind", "turn"), "embed_model": self.label,
                   "dims": len(vec) if vec else 0, "vector": vec, "metadata": it.get("metadata") or {},
                   "turn_key": it.get("turn_key"), "text_hash": it.get("text_hash"), "scope": it.get("scope")}
            try:
                if not b.find(turn_key=rec["turn_key"], text_hash=rec["text_hash"], scope=rec["scope"]):
                    b.add(rec)
                stored += 1
            except Exception as e:  # noqa: BLE001
                self.last_error = str(e)
                left.extend(items[i:])
                break
        self._write_pending(left)
        if stored:
            self.warn(f"[memory] embedded {stored} queued turn(s); {len(left)} still waiting")
        return stored, len(left)

    def reembed(self, recs, readd=False):
        """Embed stored records again with the current embedder (3.7.1,
        `nimlab memory reembed`). readd: the table was recreated, add every
        record back. -> (done, failed)."""
        from . import ltm
        b = self._live()
        if b is None:
            return 0, len(recs)
        done = failed = 0
        for r in recs:
            vec = self.embed(r.get("text") or "", "passage")
            if not vec:
                failed += 1
                continue
            rec = {"id": r.get("id") or new_id(), "timestamp": r.get("timestamp") or config.timestamp(),
                   "text": r.get("text") or "", "kind": r.get("kind") or "turn", "embed_model": self.label,
                   "dims": len(vec), "vector": vec, "metadata": r.get("metadata") or {},
                   "turn_key": r.get("turn_key"), "text_hash": r.get("text_hash") or ltm.text_hash(r.get("text") or ""),
                   "scope": r.get("scope")}
            try:
                if not readd and hasattr(b, "update_vector"):
                    b.update_vector(rec["id"], vec, self.label)
                else:
                    if not readd:
                        b.delete(rec["id"])
                    b.add(rec)
                done += 1
            except Exception as e:  # noqa: BLE001
                self.last_error = str(e)
                failed += 1
        return done, failed

    def pending_keyword(self, terms, top_k=5, phrase=None):
        """Keyword hits in the pending queue: [(score, text, ts, id)]."""
        sc = self._scope()
        out = []
        for it in self.pending():
            if sc and it.get("scope") not in (None, sc):
                continue
            low = it.get("text", "").lower()
            if phrase and phrase.lower() not in low:
                continue
            n = sum(1 for t in terms if t.lower() in low)
            if n:
                out.append((n / max(1, len(terms)), it["text"], it.get("timestamp"), it.get("id")))
        out.sort(key=lambda r: -r[0])
        return out[:top_k]

    # -- storing ------------------------------------------------------------
    def store(self, text, metadata=None, kind="turn", turn_key=None, dedupe=None):
        """Store one memory. Returns the new record id, or None when nothing
        was stored (error text, no vector, duplicate, store offline)."""
        from . import ltm
        if not text or not text.strip() or is_error_text(text):
            return None
        b = self._live()
        if b is None:
            return None
        text = text.strip()
        limit = int(self.settings.get("max_chars") or 0)
        if limit and len(text) > limit:
            text = text[:limit].rstrip() + " ..."
        dd = self.settings.get("dedupe", "exact") if dedupe is None else dedupe
        h = ltm.text_hash(text)
        try:
            # the same turn_key (a UI resending history, a regenerated reply)
            # is never stored twice; dedupe settings add hash/semantic checks
            sc = self._scope()
            if sc and turn_key:
                turn_key = f"{sc}:{turn_key}"[:128]
            dup = b.find(turn_key=turn_key, text_hash=h if dd != "off" else None, scope=sc)
            if dup:
                b.touch(dup)
                return None
            emb = self.embedder
            vec = None if emb.in_db else self.embed(text, "passage")
            if not emb.in_db and not vec:
                # v3.7.1: the turn is not lost; it waits in the pending queue
                # (keyword search finds it) and is embedded when the embedder works
                self.queue_pending(text, kind, metadata, turn_key, h, sc, self.last_error or "no vector")
                return None
            want = self.table_dims()
            if vec and want and len(vec) != want:
                self.last_error = self.dims_problem(len(vec), want)
                self.queue_pending(text, kind, metadata, turn_key, h, sc, self.last_error)
                return None
            label = self.label
            if dd == "semantic" and not emb.in_db:
                near = b.search(vec, label, 1, float(self.settings.get("dedupe_threshold") or 0.95), scope=sc)
                if near:
                    b.touch(near[0][3])
                    return None
            rec = {"id": new_id(), "timestamp": config.timestamp(), "text": text, "kind": kind,
                   "embed_model": label, "dims": len(vec) if vec else 0, "vector": vec,
                   "metadata": metadata or {}, "turn_key": turn_key, "text_hash": h, "scope": sc}
            rid = b.add(rec)
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return None
        self._stores += 1
        if self._stores % 25 == 0:
            self.prune()
        if self._pending_count:
            self.embed_pending(limit=5)
        return rid

    def remember(self, user_text, reply, metadata=None, turn_key=None):
        """The automatic step after each exchange: store what qualifies under
        the settings (auto_store, store_mode, min_chars, dedupe). Returns the
        list of new record ids."""
        from . import ltm
        s = self.settings
        self.last_turn["stored"] = 0
        if not s.get("auto_store", True) or s.get("backend") == "off":
            return []
        if is_error_text(reply or "x"):
            return []
        # v3.8.0: self-test requests, the setup self-test's fixed prompts and the
        # assistant's own "I don't know who you are" answers are never memories
        blocked = ltm.store_blocked()
        if blocked or ltm.is_self_test(user_text):
            self.last_turn["skipped"] = blocked or "self-test prompt"
            return []
        md = dict(metadata or {})
        pinned = self.pin_identity_from(user_text, metadata=md) if s.get("pin_identity", True) else []
        if ltm.is_denial(reply):
            self.last_turn["skipped"] = "reply says it does not remember"
            self.last_turn["stored"] = len(pinned)
            return pinned
        ok, _why = ltm.qualifies(user_text, s)
        if not ok:
            self.last_turn["stored"] = len(pinned)
            return pinned
        if s.get("store_mode") == "facts":
            out = []
            for i, fact in enumerate(ltm.extract_facts(user_text)):
                rid = self.store(fact, metadata=dict(md, source="facts"), kind="fact",
                                 turn_key=f"{turn_key}:{i}" if turn_key else None)
                if rid:
                    out.append(rid)
            out = pinned + out
            self.last_turn["stored"] = len(out)
            return out
        rid = self.store(f"User: {user_text} | Assistant: {reply}", metadata=md, kind="turn", turn_key=turn_key)
        out = pinned + ([rid] if rid else [])
        self.last_turn["stored"] = len(out)
        return out

    # -- v3.8.0: pinned identity facts ----------------------------------------
    def pin_identity_from(self, user_text, metadata=None):
        """Pin every self-introduction / identity fact in the user's words
        ("My name is SeVin") for this user. -> new record ids."""
        from . import ltm
        out = []
        for key, value in ltm.extract_identity(user_text).items():
            rid = self.pin_identity(key, value, metadata=metadata)
            if rid:
                out.append(rid)
        return out

    def pin_identity(self, key, value, metadata=None):
        """Store one identity fact as kind "identity" in this user's scope.
        A new value replaces the old one for the same key; the same value is
        only touched. -> the new record id, or None."""
        from . import ltm
        b = self._live()
        if b is None or not value:
            return None
        text = ltm.identity_text(key, value)
        old = [f for f in self._identity_records() if (ltm.parse_identity(f["text"]) or ("", ""))[0] == key]
        if any(ltm.parse_identity(f["text"])[1] == value for f in old):
            self._ident_cache.pop(self._scope(), None)
            return None
        md = dict(metadata or {}, source="identity", key=key)
        rid = self.store(text, metadata=md, kind="identity", dedupe="exact")
        if rid:
            for f in old:
                if f.get("id") and not f.get("pending"):
                    self.delete(f["id"])
            if old and self._pending_count:
                self._write_pending([it for it in self.pending() if not (
                    it.get("kind") == "identity" and (ltm.parse_identity(it.get("text")) or ("", ""))[0] == key
                    and it.get("scope") == self._scope())])
        self._ident_cache.pop(self._scope(), None)
        return rid

    def _identity_records(self):
        from . import ltm
        b = self._live()
        sc = self._scope()
        recs = []
        if b is not None and hasattr(b, "by_kind"):
            try:
                recs = list(b.by_kind("identity", 40, scope=sc))
            except Exception as e:  # noqa: BLE001 - a turn never fails on this; real outages show elsewhere
                self.last_error = f"identity facts: {str(e)[:200]}"
                recs = []
        if self._pending_count:
            recs += [dict(it, pending=True) for it in reversed(self.pending())
                     if it.get("kind") == "identity" and ltm.in_scope(it.get("scope"), sc)]
        return recs

    def identity_facts(self):
        """{key: value} pinned for this user (newest value per key). The first
        call per scope with nothing pinned scans the stored turns once for
        self-introductions saved before v3.8.0 and pins them."""
        from . import ltm
        sc = self._scope()
        ttl = float(self.settings.get("identity_cache_sec", 15) or 0)
        hit = self._ident_cache.get(sc)
        if hit and ttl and ltm.now_monotonic() - hit[0] < ttl:
            return dict(hit[1])
        facts = {}
        for r in self._identity_records():
            kv = ltm.parse_identity(r.get("text"))
            if kv and kv[0] not in facts:
                facts[kv[0]] = kv[1]
        if not facts and sc not in self._backfilled and self.settings.get("pin_identity", True):
            self._backfilled.add(sc)
            facts = self._backfill_identity()
        if self.backend is not None and self.backend_name in ("oracle", "ords"):
            self._ident_cache[sc] = (ltm.now_monotonic(), dict(facts))
        return facts

    def _backfill_identity(self):
        from . import ltm
        b = self._live()
        if b is None:
            return {}
        try:
            recs = b.records(int(self.settings.get("identity_backfill_scan", 300) or 300))
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return {}
        sc = self._scope()
        found = {}
        for r in recs:   # oldest first: the newest statement wins
            if not ltm.in_scope(r.get("scope") or (r.get("metadata") or {}).get("scope"), sc):
                continue
            u, _a = ltm.split_turn(r.get("text"))
            if (r.get("kind") or (r.get("metadata") or {}).get("kind") or "turn") in ("turn", "fact"):
                found.update(ltm.extract_identity(u))
        for key, value in found.items():
            self.pin_identity(key, value, metadata={"source": "identity", "backfill": True})
        if found:
            self.warn(f"[memory] pinned {len(found)} identity fact(s) found in earlier memories: "
                      + ", ".join(sorted(found)))
        return found

    def identity_block(self):
        """The pinned facts as lines for the prompt ('' when none)."""
        from . import ltm
        facts = self.identity_facts()
        if not facts:
            return ""
        return "\n".join(f"- {ltm.IDENTITY_LABELS.get(k, k)}: {v}" for k, v in facts.items())

    def delete(self, record_id):
        b = self._live()
        if b is None:
            return False
        try:
            return b.delete(record_id)
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return False

    def prune(self):
        """Retention: drop memories not seen for retention_days, and keep at
        most max_records. Returns how many were dropped."""
        days = float(self.settings.get("retention_days") or 0)
        cap = int(self.settings.get("max_records") or 0)
        if self.backend is None or (not days and not cap):
            return 0
        try:
            return self.backend.prune(days=days, max_records=cap)
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return 0

    # -- recalling ----------------------------------------------------------
    def recall(self, query, top_k=3, threshold=0.4):
        """[(similarity, text, timestamp, id)] best first."""
        b = self._live()
        if b is None or not (query or "").strip():
            return []
        try:
            if hasattr(b, "refresh"):
                b.refresh()    # v3.8.0: rows another process wrote since we last looked
            if hasattr(b, "list") and not b.list:
                return []
            emb = self.embedder
            q = None if emb.in_db else self.embed(query, "query")
            if not emb.in_db and not q:
                return []
            hits = b.search(q, self.label, int(top_k), float(threshold), query_text=query, scope=self._scope())
            # 3.7.1: when the threshold cut the list short, look once more with
            # no threshold so the trace can show what was just below it (a
            # threshold too high for this embedding model shows up here)
            self.last_near_miss = []
            if len(hits) < int(top_k) and float(threshold) > 0 and self.settings.get("diagnose_recall", True):
                try:
                    seen = {h[3] for h in hits}
                    more = b.search(q, self.label, int(top_k) + len(hits), -1.0, query_text=query,
                                    scope=self._scope())
                    self.last_near_miss = [h for h in more if h[3] not in seen][:3]
                except Exception:  # noqa: BLE001 - diagnostics only
                    self.last_near_miss = []
            return hits
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return []

    def recall_reranked(self, query, top_k=3, threshold=0.4, rerank_fn=None, candidates=10):
        """Embedding recall widened to `candidates` hits, then reordered by
        rerank_fn(query, [texts]) -> [(index, score)] best first, and cut to
        top_k. Returns (hits, info) where info says whether the rerank ran.
        Without rerank_fn (or when it fails) this is plain recall()."""
        if rerank_fn is None:
            return self.recall(query, top_k, threshold), {"reranked": False}
        pool = self.recall(query, max(top_k, int(candidates or top_k)), threshold)
        if len(pool) <= 1:
            return pool[:top_k], {"reranked": False, "reason": "nothing to rerank"}
        try:
            order = rerank_fn(query, [h[1] for h in pool])
        except Exception as e:  # a reranker failure falls back to cosine order
            order, err = None, str(e)
        else:
            err = None
        if not order:
            return pool[:top_k], {"reranked": False, "reason": err or "reranker returned nothing"}
        seen, out = set(), []
        for idx, _score in order:
            if 0 <= idx < len(pool) and idx not in seen:
                seen.add(idx)
                out.append(pool[idx])
        return out[:top_k], {"reranked": True, "pool": len(pool)}

    def recall_hybrid(self, query, top_k=6, threshold=0.4, rerank_fn=None, candidates=12, exclude=None,
                      keyword_weight=None, extra_terms=None, hybrid=True):
        """v3.8.0 automatic recall: vector similarity and keyword search (Oracle
        Text CONTAINS / sqlite FTS5 / substring scan, plus the pending queue)
        run side by side and are ranked together by reciprocal rank fusion,
        then reranked by rerank_fn when set, and cut to top_k.

        exclude(text) -> True drops a hit (turns already in the conversation's
        short-term context). Self-test turns, the assistant's own "I don't
        know who you are" answers and pinned identity facts (injected on their
        own) are dropped as well. Returns (hits, info); each hit is
        (score, text, ts, id) with score the cosine similarity when the vector
        search found it, else the fused score."""
        from . import ltm
        info = {"reranked": False, "vector": 0, "keyword": 0, "excluded": 0, "dropped": 0}
        top_k = max(1, int(top_k or 1))
        pool_n = max(top_k * 2, int(candidates or top_k))
        sem = self.recall(query, pool_n, threshold)
        terms = ltm.keyword_terms(query)
        for t in (extra_terms or []):
            if t not in terms:
                terms.append(t)
        kw = []
        if terms and hybrid:
            kw = self._keyword_terms(terms, pool_n, ltm.quoted_phrase(query))
        info["vector"], info["keyword"] = len(sem), len(kw)

        def keep(h):
            t = h[1] or ""
            if t.startswith("[identity:") or not ltm.usable_memory(t):
                info["dropped"] += 1
                return False
            if exclude is not None and exclude(t):
                info["excluded"] += 1
                return False
            return True
        sem = [h for h in sem if keep(h)]
        kw = [h for h in kw if keep(h)]
        w = float(0.6 if keyword_weight is None else keyword_weight)
        fused = ltm.fuse([sem, kw], weights=[1.0, max(0.0, w)])
        sims = {h[3] if h[3] is not None else (h[1] or "").strip(): h[0] for h in sem}
        pool = []
        for f in fused:
            key = f[3] if f[3] is not None else (f[1] or "").strip()
            pool.append((round(float(sims.get(key, f[0])), 4), f[1], f[2], f[3]))
        info["pool"] = len(pool)
        if rerank_fn is not None and len(pool) > 1:
            try:
                order = rerank_fn(query, [h[1] for h in pool])
            except Exception as e:  # noqa: BLE001 - reranker down: keep the fused order
                order, info["rerank_error"] = None, str(e)
            if order:
                out, used = [], set()
                for idx, _sc in order:
                    if 0 <= idx < len(pool) and idx not in used:
                        used.add(idx)
                        out.append(pool[idx])
                pool, info["reranked"] = out + [h for i, h in enumerate(pool) if i not in used], True
        return pool[:top_k], info

    def _keyword_terms(self, terms, top_k, phrase=None):
        b = self._live()
        hits = []
        if b is not None and hasattr(b, "keyword_search"):
            try:
                hits = list(b.keyword_search(terms, int(top_k), scope=self._scope(), phrase=phrase))
            except Exception as e:  # noqa: BLE001
                self._go_offline(e)
                hits = []
        if self._pending_count:
            seen = {h[1] for h in hits}
            hits += [h for h in self.pending_keyword(terms, int(top_k), phrase) if h[1] not in seen]
        return hits[:int(top_k)]

    # -- v3.7.1: keyword search, recent, the memory_search tool, round trip ----
    def keyword(self, query, top_k=5):
        """Exact / keyword search for a name, ID, number or phrase the vector
        hits missed. [(score, text, timestamp, id)] best first. Oracle uses
        Oracle Text CONTAINS when the text index exists (memory setup makes
        it), else INSTR on the lowered text; local/json use LIKE / substring."""
        from . import ltm
        b = self._live()
        terms = ltm.keyword_terms(query)
        if not terms:
            return []
        if b is None or not hasattr(b, "keyword_search"):
            return self.pending_keyword(terms, int(top_k), ltm.quoted_phrase(query)) if self._pending_count else []
        try:
            hits = b.keyword_search(terms, int(top_k), scope=self._scope(), phrase=ltm.quoted_phrase(query))
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            hits = []
        if self._pending_count:
            seen = {h[1] for h in hits}
            hits = list(hits) + [h for h in self.pending_keyword(terms, int(top_k), ltm.quoted_phrase(query))
                                 if h[1] not in seen]
        return hits[:int(top_k)]

    def recent(self, limit=5):
        """The newest memories in this scope (oldest first): [(1.0, text, ts, id)]."""
        from . import ltm
        b = self._live()
        if b is None or not limit:
            return []
        try:
            recs = b.records(int(limit) * 4)
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return []
        sc = self._scope()
        recs = [r for r in recs if ltm.in_scope(r.get("scope") or (r.get("metadata") or {}).get("scope"), sc)]
        return [(1.0, r.get("text") or "", r.get("timestamp"), r.get("id")) for r in recs[-int(limit):]]

    def search(self, query, mode="both", top_k=5, threshold=None, rerank_fn=None):
        """The memory_search tool: semantic, keyword or both, merged, de-duplicated
        by record id (and text), reranked when rerank_fn is given.
        -> (hits, info) with info = {mode, semantic, keyword, reranked, ms}."""
        from . import ltm
        t0 = ltm.now_monotonic()
        mode = mode if mode in ("semantic", "keyword", "both") else "both"
        thr = float(threshold if threshold is not None else 0.3)
        sem = self.recall(query, max(top_k, 10), thr) if mode in ("semantic", "both") else []
        kw = self.keyword(query, max(top_k, 10)) if mode in ("keyword", "both") else []
        merged, seen = [], set()
        for h in sem + kw:
            key = h[3] if h[3] is not None else h[1]
            if key in seen or (h[1] or "").strip() in seen:
                continue
            seen.add(key)
            seen.add((h[1] or "").strip())
            merged.append(h)
        info = {"mode": mode, "semantic": len(sem), "keyword": len(kw), "reranked": False}
        if rerank_fn is not None and len(merged) > 1:
            try:
                order = rerank_fn(query, [h[1] for h in merged])
            except Exception as e:  # noqa: BLE001 - reranker down: keep the merged order
                order, info["rerank_error"] = None, str(e)
            if order:
                out, used = [], set()
                for idx, _sc in order:
                    if 0 <= idx < len(merged) and idx not in used:
                        used.add(idx)
                        out.append(merged[idx])
                out += [h for i, h in enumerate(merged) if i not in used]
                merged, info["reranked"] = out, True
        info["ms"] = int((ltm.now_monotonic() - t0) * 1000)
        return merged[:int(top_k)], info

    def roundtrip(self):
        """Doctor check: write one marked memory through the live connection,
        find it by vector recall and by keyword search, then delete it.
        [(ok, message)]."""
        from . import ltm
        import uuid
        b = self._live()
        if b is None:
            return [(False, f"memory store {self.backend_name} is not connected: {self.offline or 'off'}")]
        mark = "nimlabcheck" + uuid.uuid4().hex[:10]
        text = f"Doctor round trip {mark}: the testbed wrote this memory to check write and recall."
        out = []
        t0 = ltm.now_monotonic()
        rid = self.store(text, metadata={"source": "doctor"}, kind="check", dedupe="off")
        if not rid:
            return [(False, f"write to {b.where()} failed: {self.offline or self.last_error or 'nothing stored'}")]
        out.append((True, f"wrote a test memory to {b.where()} in {int((ltm.now_monotonic() - t0) * 1000)} ms"))
        try:
            t1 = ltm.now_monotonic()
            hits = self.recall(text, 3, 0.0)
            ok = any(h[3] == rid or mark in (h[1] or "") for h in hits)
            out.append((ok, f"semantic recall (vector search) {'found' if ok else 'did NOT find'} it in "
                            f"{int((ltm.now_monotonic() - t1) * 1000)} ms"))
            t2 = ltm.now_monotonic()
            kh = self.keyword(mark, 3)
            ok = any(mark in (h[1] or "") for h in kh)
            how = getattr(b, "keyword_mode", lambda: "substring")()
            out.append((ok, f"keyword search ({how}) {'found' if ok else 'did NOT find'} it in "
                            f"{int((ltm.now_monotonic() - t2) * 1000)} ms"))
        finally:
            try:
                b.delete(rid)
                out.append((True, "removed the test memory"))
            except Exception as e:  # noqa: BLE001
                out.append((False, f"could not remove the test memory {rid}: {e}"))
        return out

    def roundtrip_identity(self):
        """Doctor check (3.8.2): pin a throwaway identity fact under its own
        key (never "name", so the user's real facts are untouched), read it
        back through identity_facts(), then delete it. [(ok, message)]."""
        import uuid
        if not self.settings.get("pin_identity", True):
            return [("warn", "identity pin is off, so the pin round trip was skipped")]
        if self._live() is None:
            return [(False, "identity pin round trip: the memory store is not connected")]
        mark = "check" + uuid.uuid4().hex[:8]
        rid = self.pin_identity("doctorcheck", mark, metadata={"source": "doctor"})
        if not rid:
            return [(False, f"identity pin round trip: the write failed ({self.last_error or 'nothing stored'})")]
        try:
            self._ident_cache.pop(self._scope(), None)
            got = self.identity_facts().get("doctorcheck")
            return [(got == mark, "identity pin round trip: pinned a test fact and "
                     + ("read it back" if got == mark else "did NOT read it back"))]
        finally:
            self.delete(rid)
            self._ident_cache.pop(self._scope(), None)

    # -- status -------------------------------------------------------------
    def count(self):
        b = self.backend
        if b is None:
            return 0
        try:
            return b.count()
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return 0

    def incompatible_count(self):
        b = self.backend
        if b is None:
            return 0
        try:
            return b.incompatible(self.label)
        except Exception as e:  # noqa: BLE001
            self._go_offline(e)
            return 0

    def status(self):
        """For /health and serve info: where memory lives, whether it is up."""
        from . import ltm
        return {"backend": self.backend_name, "configured": self.settings.get("backend"),
                "online": self.backend is not None, "offline_reason": self.offline,
                "scope": self.settings.get("scope", "shared"), "auto_store": bool(self.settings.get("auto_store")),
                "auto_recall": bool(self.settings.get("auto_recall")), "where": ltm.describe(self.settings)}

    def status_line(self):
        from . import ltm
        if self.settings.get("backend") == "off":
            return "long-term memory off"
        if self.offline:
            return f"long-term memory OFFLINE ({self.offline}); chatting without memory"
        return f"{self.count()} memories in " + ltm.describe(self.settings)

    def test(self):
        """[(ok, message)]: the backend's own checks plus a live embed."""
        from . import ltm
        out = []
        if self.settings.get("backend") == "off":
            return [(True, "long-term memory is off")]
        if self.backend is None:
            self._connect()
        if self.backend is None:
            return [(False, f"backend {self.settings.get('backend')}: {self.offline}")]
        if self.settings.get("backend") == "auto":
            out.append((True, f"backend auto -> {self.backend_name}" + (
                "" if self.backend_name in ("oracle", "ords") else
                " (no Oracle or ORDS login found; set NIMLAB_ORACLE_USER/PASSWORD/DSN, or `nimlab memory ords "
                "login`, to use the testbed's own setup in MEM)")))
        try:
            out += self.backend.test()
        except Exception as e:  # noqa: BLE001
            out.append((False, f"backend check failed: {e}"))
        try:
            emb = self.embedder
        except Exception as e:  # noqa: BLE001
            return out + [(False, f"embedding provider: {e}")]
        if emb.in_db:
            try:
                d = self.backend.in_db_dims()
                out.append((True, f"in-database embedding {emb.model}: {d} dimensions"))
            except Exception as e:  # noqa: BLE001
                out.append((False, f"in-database embedding {emb.model}: {e}"))
            return out
        t0 = ltm.now_monotonic()
        vecs = {}
        for it in ("query", "passage"):            # recall sends query, store sends passage
            try:
                vecs[it] = emb.embed("connection test", it)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                lbl = self.label or "(Embedding role not set)"
                return out + [(False, f"embedding {lbl} (input_type={it}): "
                                      f"{msg if msg.startswith(lbl) is False else msg[len(lbl) + 2:]}")] \
                    + self._pending_line()
            if not vecs[it]:
                return out + [(False, f"embedding {self.label or '(Embedding role not set)'} (input_type={it}): "
                                      "no vector (the provider gave no error text)")] + self._pending_line()
        vec = vecs["query"]
        out.append((True, f"embedding {self.label}: {len(vec)} dimensions (query + passage) in "
                          f"{ltm.now_monotonic() - t0:.2f}s"))
        want = self.table_dims()
        if want and len(vec) != want:
            out.append((False, self.dims_problem(len(vec), want)))
        bad = self.incompatible_count()
        if bad:
            out.append((False, f"{bad} stored memories come from another embedder and are skipped by recall"))
        return out + self._pending_line()

    def _pending_line(self):
        n = len(self.pending())
        return [(False, f"{n} turn(s) wait for an embedding (nimlab memory embed-pending stores them once the embedder works)")] if n else []

    def setup(self, recreate=False):
        """Oracle: create the tables, vector index and profile now."""
        if self.backend is None:
            self._connect()
        b = self.backend
        if b is None:
            raise RuntimeError(self.offline or "no backend")
        if not hasattr(b, "setup"):
            return [f"{self.backend_name} needs no setup ({b.where()})"]
        emb = self.embedder
        dims = 0
        if not emb.in_db:
            vec = emb.embed("dimension probe", "passage")
            if not vec:
                raise RuntimeError(f"the embedder {self.label} returned no vector")
            dims = len(vec)
        return b.setup(dims=dims, label=self.label, recreate=recreate)
