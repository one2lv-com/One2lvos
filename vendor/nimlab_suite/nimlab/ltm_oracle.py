"""Oracle 26ai backend for the testbed's long-term memory.

Default setup: its own isolated corner of the MEM schema.

  MEM.TESTBED_MEMORIES   one row per memory: text, kind, a VECTOR(dims,
                         FLOAT32) column, embed label, JSON metadata, hits,
                         created/last-seen timestamps; every row carries
                         PROFILE_ID 'TESTBED' and every query filters on it
  MEM.TESTBED_META       the setup's dimensions, embedding label, format
  TESTBED_MEMORIES_VIDX  a vector index (IVF neighbor partitions by default,
                         or HNSW in-memory graph), COSINE distance
  MEM.AGENT_PROFILES     one row, AGENT_ID 'TESTBED', so the testbed shows up
                         beside the other agents' profiles

It never reads or writes MEM.MEMORIES, ENTITIES, MEMORY_SESSIONS,
MEMORY_ENTITY_LINKS or MEM_GUIDES (the other agents' records), refuses the
SVN schema, and refuses a profile id that belongs to another agent.

Similarity search is VECTOR_DISTANCE(embedding, :q, COSINE) with
FETCH APPROX FIRST k ROWS ONLY WITH TARGET ACCURACY n, so the vector index
is used. Vectors come either from the embedding provider in settings (bound
as array('f')) or from an ONNX model inside the database with
VECTOR_EMBEDDING(model USING :text AS data).

Connects with python-oracledb in thin mode (no Instant Client): a TLS DSN,
or a wallet directory for mTLS. The password comes from an env var or a
credentials file; it is never stored in config_cluster.json or printed.
"""

import array
import json
import os
import re
import stat
import threading

from .ltm import MemoryOffline

ENV = {"user": "NIMLAB_ORACLE_USER", "password": "NIMLAB_ORACLE_PASSWORD", "dsn": "NIMLAB_ORACLE_DSN",
       "config_dir": "NIMLAB_ORACLE_CONFIG_DIR", "wallet_dir": "NIMLAB_ORACLE_WALLET_DIR",
       "wallet_password": "NIMLAB_ORACLE_WALLET_PASSWORD"}
FORMAT = "nimlab-ltm-oracle-1"
IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,29}$")
# the other agents' MEM objects: never a target
RESERVED_TABLES = {"MEMORIES", "ENTITIES", "MEMORY_SESSIONS", "MEMORY_ENTITY_LINKS", "MEM_GUIDES", "AGENT_PROFILES"}
FORBIDDEN_SCHEMAS = {"SVN", "SYS", "SYSTEM", "ADMIN"}
INDEXES = ("ivf", "hnsw", "none")
DISTANCES = ("COSINE", "DOT", "EUCLIDEAN")


def load_credentials(o, environ=None):
    """user, dsn, config_dir, wallet_dir: settings, then credentials file,
    then env (env wins). password and wallet_password: credentials file or
    env only. Returns (creds, notes)."""
    env = os.environ if environ is None else environ
    creds, notes = {}, []
    for k in ("user", "dsn", "config_dir", "wallet_dir"):
        if o.get(k):
            creds[k] = o[k]
    path = os.path.expanduser(o.get("credentials_file") or "")
    if path and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise MemoryOffline(f"credentials file {path}: {e}")
        for k in ENV:
            v = data.get(k) or (data.get("wallet_location") if k == "wallet_dir" else None)
            if v:
                creds[k] = v
        try:
            if os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                notes.append(f"{path} is readable by other users: chmod 600 it")
        except OSError:
            pass
    for k, var in ENV.items():
        if env.get(var):
            creds[k] = env[var]
    for k in ("config_dir", "wallet_dir"):
        if creds.get(k):
            creds[k] = os.path.expanduser(creds[k])
    if not creds.get("config_dir") and env.get("TNS_ADMIN"):
        creds["config_dir"] = env["TNS_ADMIN"]
    return creds, notes


def missing_credentials(creds):
    return [k for k in ("user", "password", "dsn") if not creds.get(k)]


def default_connect(creds, timeout=15):
    try:
        import oracledb
    except ImportError:
        raise MemoryOffline("python-oracledb is not installed (pip install oracledb)")
    kw = {"user": creds["user"], "password": creds["password"], "dsn": creds["dsn"],
          "tcp_connect_timeout": float(timeout or 15)}
    if creds.get("config_dir"):
        kw["config_dir"] = creds["config_dir"]
    if creds.get("wallet_dir"):
        kw["wallet_location"] = creds["wallet_dir"]
        kw.setdefault("config_dir", creds["wallet_dir"])
    if creds.get("wallet_password"):
        kw["wallet_password"] = creds["wallet_password"]
    try:
        return oracledb.connect(**kw)   # thin mode unless init_oracle_client() was called
    except Exception as e:  # noqa: BLE001 - oracledb.Error and network errors
        raise MemoryOffline("could not connect: " + _clean(e, creds))


def _clean(e, creds=None):
    msg = str(e).splitlines()[0] if str(e) else type(e).__name__
    for k in ("password", "wallet_password"):
        if creds and creds.get(k):
            msg = msg.replace(creds[k], "***")
    return msg[:300]


def _lob(v):
    return v.read() if hasattr(v, "read") else v


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v is not None else None)


class OracleBackend:
    name = "oracle"

    def __init__(self, o, embed_model=None, connect_fn=None, environ=None, log=None):
        self.o = dict(o or {})
        self.schema = (self.o.get("schema") or "MEM").upper()
        self.prefix = (self.o.get("table_prefix") or "TESTBED").upper()
        self.profile = (self.o.get("profile_id") or "TESTBED").upper()
        self.index = (self.o.get("index") or "ivf").lower()
        self.distance = (self.o.get("distance") or "COSINE").upper()
        self.accuracy = int(self.o.get("target_accuracy") or 90)
        self.onnx = embed_model or ""
        # in-database models trained with a query instruction (bge: "Represent this sentence for searching
        # relevant passages: ") get it on search queries only; stored passages are embedded as-is.
        self.query_prefix = str(self.o.get("query_prefix") or "")
        self.log = log
        self._check_names()
        self.t_mem = f"{self.schema}.{self.prefix}_MEMORIES"
        self.t_meta = f"{self.schema}.{self.prefix}_META"
        self.vidx = f"{self.prefix}_MEMORIES_VIDX"
        self.tidx = f"{self.prefix}_MEM_TEXT_IX"     # v3.7.1: Oracle Text index for keyword search
        self._has_tidx = None
        self.creds, self.notes = load_credentials(self.o, environ)
        self._connect_fn = connect_fn or default_connect
        self._conn = None
        self._lock = threading.RLock()
        self.dims = 0
        self.ready = False
        self.connect()
        self.ready = self._tables_exist()
        if self.ready:
            self.dims = int(self._meta().get("dims") or 0)

    # -- names and guards ---------------------------------------------------
    def _check_names(self):
        for what, v in (("schema", self.schema), ("table prefix", self.prefix), ("profile id", self.profile)):
            if not IDENT.match(v):
                raise MemoryOffline(f"{what} {v!r} is not a plain Oracle name (letters, digits, _)")
        if self.onnx and not IDENT.match(self.onnx):
            raise MemoryOffline(f"ONNX model name {self.onnx!r} is not a plain Oracle name")
        if self.schema in FORBIDDEN_SCHEMAS:
            raise MemoryOffline(f"the {self.schema} schema is off limits for testbed memory; use MEM or your own schema")
        for t in (f"{self.prefix}_MEMORIES", f"{self.prefix}_META"):
            if t in RESERVED_TABLES or self.prefix in RESERVED_TABLES or self.prefix.startswith("MEM_"):
                raise MemoryOffline(f"table prefix {self.prefix} would collide with the shared MEM tables")
        if self.index not in INDEXES:
            raise MemoryOffline(f"index must be one of {', '.join(INDEXES)}")
        if self.distance not in DISTANCES:
            raise MemoryOffline(f"distance must be one of {', '.join(DISTANCES)}")

    def where(self):
        return f"{self.t_mem} (profile {self.profile})"

    def _vsql(self, name):
        """How a vector bind appears in SQL (ORDS wraps it in TO_VECTOR)."""
        return f":{name}"

    # -- connection ---------------------------------------------------------
    def connect(self):
        miss = missing_credentials(self.creds)
        if miss:
            raise MemoryOffline("missing " + ", ".join(miss) + ": set " + ", ".join(ENV[m] for m in miss)
                                + f" or put them in {self.o.get('credentials_file') or 'a credentials file'}")
        with self._lock:
            if self._conn is None:
                self._conn = self._connect_fn(self.creds, self.o.get("connect_timeout_sec") or 15)
        return self._conn

    def close(self):
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:  # noqa: BLE001
                    pass
                self._conn = None

    def _x(self, sql, binds=None, fetch=False, commit=False, many=None):
        with self._lock:
            conn = self.connect()
            try:
                cur = conn.cursor()
                try:
                    if many is not None:
                        cur.executemany(sql, many)
                    else:
                        cur.execute(sql, binds or {})
                    rows = cur.fetchall() if fetch else None
                    n = cur.rowcount
                finally:
                    try:
                        cur.close()
                    except Exception:  # noqa: BLE001
                        pass
                if commit:
                    conn.commit()
                return rows if fetch else n
            except MemoryOffline:
                raise
            except Exception as e:  # noqa: BLE001 - oracledb.Error
                code = getattr(getattr(e, "args", [None])[0], "code", None) if getattr(e, "args", None) else None
                if code in (942,):   # table or view does not exist
                    self.ready = False
                else:
                    self.close()   # reconnect next time
                raise MemoryOffline("database: " + _clean(e, self.creds))

    # -- setup --------------------------------------------------------------
    def _tables_exist(self):
        rows = self._x("/* ltm:tables */ SELECT table_name FROM all_tables WHERE owner = :o AND table_name IN (:t1, :t2)",
                       {"o": self.schema, "t1": f"{self.prefix}_MEMORIES", "t2": f"{self.prefix}_META"}, fetch=True)
        return len(rows or []) == 2

    def _meta(self):
        rows = self._x(f"/* ltm:meta_get */ SELECT k, v FROM {self.t_meta} WHERE profile_id = :p",
                       {"p": self.profile}, fetch=True)
        return {k: _lob(v) for k, v in rows or []}

    def _meta_put(self, k, v):
        self._x(f"/* ltm:meta_put */ MERGE INTO {self.t_meta} t USING (SELECT :p profile_id, :k k FROM dual) s "
                "ON (t.profile_id = s.profile_id AND t.k = s.k) WHEN MATCHED THEN UPDATE SET t.v = :v "
                "WHEN NOT MATCHED THEN INSERT (profile_id, k, v) VALUES (:p, :k, :v)",
                {"p": self.profile, "k": k, "v": str(v)}, commit=True)

    def in_db_dims(self):
        rows = self._x(f"/* ltm:onnx_dims */ SELECT VECTOR_DIMENSION_COUNT(VECTOR_EMBEDDING({self.onnx} USING "
                       "'dimension probe' AS data)) FROM dual", fetch=True)
        return int(rows[0][0])

    def onnx_models(self):
        rows = self._x("/* ltm:onnx_models */ SELECT model_name FROM all_mining_models WHERE owner = :o "
                       "AND algorithm = 'ONNX'", {"o": self.schema}, fetch=True)
        return [r[0] for r in rows or []]

    def ddl(self, dims):
        """The statements setup runs, in order (shown by `memory oracle sql`)."""
        out = [
            f"/* ltm:create_mem */ CREATE TABLE {self.t_mem} ("
            "id VARCHAR2(64) PRIMARY KEY, profile_id VARCHAR2(64) NOT NULL, kind VARCHAR2(16) DEFAULT 'turn' NOT NULL, "
            "text CLOB NOT NULL, text_hash VARCHAR2(64) NOT NULL, turn_key VARCHAR2(128), "
            "embed_label VARCHAR2(256) NOT NULL, dims NUMBER(6) NOT NULL, "
            f"embedding VECTOR({int(dims)}, FLOAT32) NOT NULL, metadata JSON, hits NUMBER DEFAULT 1 NOT NULL, "
            "scope VARCHAR2(128), "
            "created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL, "
            "last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL)",
            f"/* ltm:create_idx */ CREATE INDEX {self.schema}.{self.prefix}_MEM_HASH_IX ON {self.t_mem} (profile_id, text_hash)",
            f"/* ltm:create_idx */ CREATE INDEX {self.schema}.{self.prefix}_MEM_TURN_IX ON {self.t_mem} (profile_id, turn_key)",
            f"/* ltm:create_idx */ CREATE INDEX {self.schema}.{self.prefix}_MEM_SEEN_IX ON {self.t_mem} (profile_id, last_seen_at)",
            f"/* ltm:create_meta */ CREATE TABLE {self.t_meta} (profile_id VARCHAR2(64) NOT NULL, "
            "k VARCHAR2(64) NOT NULL, v VARCHAR2(4000), PRIMARY KEY (profile_id, k))",
        ]
        vi = self.vector_index_sql()
        if vi:
            out.append(vi)
        return out

    def vector_index_sql(self):
        if self.index == "none":
            return None
        org = "INMEMORY NEIGHBOR GRAPH" if self.index == "hnsw" else "NEIGHBOR PARTITIONS"
        return (f"/* ltm:create_vidx */ CREATE VECTOR INDEX {self.schema}.{self.vidx} ON {self.t_mem} (embedding) "
                f"ORGANIZATION {org} DISTANCE {self.distance} WITH TARGET ACCURACY {self.accuracy}")

    def text_index_sql(self):
        return (f"/* ltm:create_tidx */ CREATE INDEX {self.schema}.{self.tidx} ON {self.t_mem} (text) "
                "INDEXTYPE IS CTXSYS.CONTEXT PARAMETERS ('SYNC (ON COMMIT)')")

    def has_text_index(self):
        if self._has_tidx is None:
            try:
                self._has_tidx = bool(self._x(
                    "/* ltm:tidx_exists */ SELECT index_name FROM all_indexes WHERE owner = :o AND index_name = :i "
                    "AND status = 'VALID'", {"o": self.schema, "i": self.tidx}, fetch=True))
            except MemoryOffline:
                self._has_tidx = False
        return self._has_tidx

    def ensure_text_index(self):
        """Best effort: Oracle Text may not be granted. -> message."""
        if self.has_text_index():
            return f"Oracle Text index {self.tidx} already there"
        try:
            self._x(self.text_index_sql())
            self._has_tidx = True
            return f"created Oracle Text index {self.tidx} (keyword search uses CONTAINS)"
        except MemoryOffline as e:
            self._has_tidx = False
            return f"no Oracle Text index ({str(e)[:160]}); keyword search uses INSTR instead"

    def keyword_mode(self):
        return "Oracle Text CONTAINS" if self.has_text_index() else "INSTR scan"

    def keyword_search(self, terms, k, scope=None, phrase=None):
        """CONTAINS on the Oracle Text index when it exists, else INSTR on the
        lowered text. Each term is escaped ({...}) so words like AND/NEAR are
        plain text. [(score, text, ts, id)]."""
        if not self.ready or not terms:
            return []
        b = {"p": self.profile}
        sc = self._scope_sql(b, scope)
        lim = int(k) * 3
        rows = None
        if self.has_text_index():
            b["q"] = " OR ".join("{" + t.replace("}", "") + "}" for t in terms)
            try:
                rows = self._x(f"/* ltm:keyword_ctx */ SELECT id, text, created_at FROM {self.t_mem} WHERE "
                               f"profile_id = :p AND CONTAINS(text, :q, 1) > 0{sc} ORDER BY SCORE(1) DESC "
                               f"FETCH FIRST {lim} ROWS ONLY", b, fetch=True)
            except MemoryOffline:
                rows, self._has_tidx = None, False
                b.pop("q", None)
        if rows is None:
            conds = []
            for i, t in enumerate(terms):
                b[f"t{i}"] = t
                conds.append(f"DBMS_LOB.INSTR(LOWER(text), :t{i}) > 0")
            rows = self._x(f"/* ltm:keyword_instr */ SELECT id, text, created_at FROM {self.t_mem} WHERE "
                           f"profile_id = :p AND ({' OR '.join(conds)}){sc} ORDER BY last_seen_at DESC "
                           f"FETCH FIRST {lim} ROWS ONLY", b, fetch=True)
        from .ltm import keyword_rank
        out = []
        for rid, text, ts in rows or []:
            t = _lob(text)
            n = keyword_rank(t, terms) + (1 if phrase and phrase in t.lower() else 0)
            out.append((max(n, 1) / (len(terms) + (1 if phrase else 0)), t, _iso(ts), rid))
        out.sort(key=lambda x: x[0], reverse=True)
        return out[:k]

    def profile_status(self):
        """'mine', 'free', 'taken' (another agent's id) or 'no-table'."""
        try:
            rows = self._x(f"/* ltm:profile_get */ SELECT platform, tool_name FROM {self.schema}.AGENT_PROFILES "
                           "WHERE agent_id = :a", {"a": self.profile}, fetch=True)
        except MemoryOffline:
            return "no-table"
        if not rows:
            return "free"
        platform, tool = rows[0]
        return "mine" if (platform or "").startswith("NIM testbed") and not tool else "taken"

    def register_profile(self):
        st = self.profile_status()
        if st == "taken":
            raise MemoryOffline(f"profile id {self.profile} already belongs to another agent in "
                                f"{self.schema}.AGENT_PROFILES; pick another (memory set oracle.profile_id ...)")
        if st == "free":
            self._x(f"/* ltm:profile_add */ INSERT INTO {self.schema}.AGENT_PROFILES (agent_id, display_name, platform, "
                    "description, tool_name, active, created_at) VALUES (:a, :d, :p, :ds, NULL, 'Y', SYSTIMESTAMP)",
                    {"a": self.profile, "d": "NIM Testbed", "p": "NIM testbed (nimlab)",
                     "ds": f"The NIM testbed entity's long-term memory, kept in {self.t_mem} with a vector index; "
                           "separate from the other agents' MEM records."}, commit=True)
        return st

    def setup(self, dims=0, label="", recreate=False):
        """Create the tables, indexes and profile when missing. Returns a list
        of what happened. dims comes from the embedder (or the ONNX model)."""
        done = []
        if self.onnx:
            dims = self.in_db_dims()
        if recreate and self._tables_exist():
            for t in (self.t_mem, self.t_meta):
                self._x(f"/* ltm:drop */ DROP TABLE {t} PURGE")
            done.append(f"dropped {self.t_mem} and {self.t_meta}")
            self.ready = False
        if not self._tables_exist():
            if not dims:
                raise MemoryOffline("setup needs the vector dimensions: run `memory test` with a working embedding "
                                    "provider, or set oracle.dims")
            for stmt in self.ddl(dims):
                self._x(stmt)
            done.append(f"created {self.t_mem} (VECTOR({dims}, FLOAT32)), {self.t_meta}"
                        + (f" and {self.index.upper()} vector index {self.vidx}" if self.index != "none" else ""))
            self._meta_put("format", FORMAT)
            self._meta_put("dims", dims)
            self._meta_put("distance", self.distance)
            if label:
                self._meta_put("embed_label", label)
            self.dims = int(dims)
        else:
            have = int(self._meta().get("dims") or 0)
            if dims and have and int(dims) != have:
                raise MemoryOffline(f"{self.t_mem} holds {have}-dimension vectors but the embedder gives {dims}: "
                                    "use an embedder with the same size, a new table_prefix, or `memory setup "
                                    "--recreate` (drops this testbed's memories)")
            self.dims = have or int(dims or 0)
            done.append(f"{self.t_mem} already set up ({self.dims} dimensions)")
            if self.index != "none" and not self._x(
                    "/* ltm:vidx_exists */ SELECT index_name FROM all_indexes WHERE owner = :o AND index_name = :i",
                    {"o": self.schema, "i": self.vidx}, fetch=True):
                self._x(self.vector_index_sql())
                done.append(f"created vector index {self.vidx}")
        if self.o.get("text_index", True):
            done.append(self.ensure_text_index())
        if self.o.get("register_profile", True):
            st = self.register_profile()
            done.append({"free": f"registered profile {self.profile} in {self.schema}.AGENT_PROFILES",
                         "mine": f"profile {self.profile} already registered",
                         "no-table": f"no {self.schema}.AGENT_PROFILES table: profile not registered"}[st])
        self.ready = True
        return done

    # -- records ------------------------------------------------------------
    def _ensure(self, vec=None, label=""):
        if not self.ready:
            self.setup(dims=len(vec) if vec else int(self.o.get("dims") or 0), label=label)

    def add(self, rec):
        vec = rec.get("vector")
        self._ensure(vec, rec["embed_model"])
        md = json.dumps(rec.get("metadata") or {}, ensure_ascii=False)
        b = {"id": rec["id"], "p": self.profile, "k": rec.get("kind") or "turn", "t": rec["text"],
             "h": rec["text_hash"], "tk": rec.get("turn_key"), "l": rec["embed_model"], "md": md,
             "sc": rec.get("scope")}
        if self.onnx:
            emb = f"VECTOR_EMBEDDING({self.onnx} USING :t AS data)"
            dims = f"VECTOR_DIMENSION_COUNT({emb})"
        else:
            if self.dims and len(vec) != self.dims:
                raise MemoryOffline(f"vector has {len(vec)} dimensions, {self.t_mem} holds {self.dims}")
            b["v"] = array.array("f", vec)
            b["d"] = len(vec)
            emb, dims = self._vsql("v"), ":d"
        self._x(f"/* ltm:insert */ INSERT INTO {self.t_mem} (id, profile_id, kind, text, text_hash, turn_key, "
                f"embed_label, dims, embedding, metadata, scope) VALUES (:id, :p, :k, :t, :h, :tk, :l, {dims}, {emb}, "
                "JSON(:md), :sc)", b, commit=True)
        return rec["id"]

    def update_vector(self, rid, vec, label):
        """Replace one memory's embedding in place (memory reembed)."""
        if self.dims and len(vec) != self.dims:
            raise MemoryOffline(f"vector has {len(vec)} dimensions, {self.t_mem} holds {self.dims}")
        self._x(f"/* ltm:reembed */ UPDATE {self.t_mem} SET embedding = {self._vsql('v')}, dims = :d, embed_label = :l "
                "WHERE id = :id AND profile_id = :p",
                {"v": array.array("f", vec), "d": len(vec), "l": label, "id": rid, "p": self.profile}, commit=True)

    @staticmethod
    def _scope_sql(b, scope):
        if scope is None:
            return ""
        b["sc"] = scope
        return " AND (scope IS NULL OR scope = :sc)"

    def search(self, vec, label, k, threshold, query_text=None, scope=None):
        if not self.ready:
            return []
        b = {"p": self.profile, "l": label}
        sc = self._scope_sql(b, scope)
        if self.onnx:
            q = f"VECTOR_EMBEDDING({self.onnx} USING :q AS data)"
            b["q"] = (self.query_prefix + query_text) if query_text else ""
        else:
            if self.dims and len(vec) != self.dims:
                return []
            q = self._vsql("q")
            b["q"] = array.array("f", vec)
        rows = self._x(f"/* ltm:search */ SELECT id, text, created_at, VECTOR_DISTANCE(embedding, {q}, {self.distance}) "
                       f"AS dist FROM {self.t_mem} WHERE profile_id = :p AND embed_label = :l{sc} ORDER BY dist "
                       f"FETCH APPROX FIRST {int(k)} ROWS ONLY WITH TARGET ACCURACY {self.accuracy}", b, fetch=True)
        out = []
        for rid, text, ts, dist in rows or []:
            sim = self.similarity(float(dist))
            if sim >= threshold:
                out.append((sim, _lob(text), _iso(ts), rid))
        return out

    def similarity(self, dist):
        if self.distance == "COSINE":
            return 1.0 - dist
        if self.distance == "DOT":
            return -dist          # VECTOR_DISTANCE DOT is the negated dot product
        return 1.0 / (1.0 + dist)

    def find(self, turn_key=None, text_hash=None, scope=None):
        if not self.ready:
            return None
        if turn_key:
            b = {"p": self.profile, "tk": turn_key}
            sc = self._scope_sql(b, scope)
            r = self._x(f"/* ltm:find_turn */ SELECT id FROM {self.t_mem} WHERE profile_id = :p AND turn_key = :tk{sc} "
                        "FETCH FIRST 1 ROWS ONLY", b, fetch=True)
            if r:
                return r[0][0]
        if text_hash:
            b = {"p": self.profile, "h": text_hash}
            sc = self._scope_sql(b, scope)
            r = self._x(f"/* ltm:find_hash */ SELECT id FROM {self.t_mem} WHERE profile_id = :p AND text_hash = :h{sc} "
                        "FETCH FIRST 1 ROWS ONLY", b, fetch=True)
            if r:
                return r[0][0]
        return None

    def touch(self, rid):
        return self._x(f"/* ltm:touch */ UPDATE {self.t_mem} SET hits = hits + 1, last_seen_at = SYSTIMESTAMP "
                       "WHERE profile_id = :p AND id = :id", {"p": self.profile, "id": rid}, commit=True) > 0

    def delete(self, rid):
        return self._x(f"/* ltm:delete */ DELETE FROM {self.t_mem} WHERE profile_id = :p AND id = :id",
                       {"p": self.profile, "id": rid}, commit=True) > 0

    def count(self):
        if not self.ready:
            return 0
        return int(self._x(f"/* ltm:count */ SELECT COUNT(*) FROM {self.t_mem} WHERE profile_id = :p",
                           {"p": self.profile}, fetch=True)[0][0])

    def incompatible(self, label):
        if not self.ready:
            return 0
        return int(self._x(f"/* ltm:incompatible */ SELECT COUNT(*) FROM {self.t_mem} WHERE profile_id = :p "
                           "AND embed_label <> :l", {"p": self.profile, "l": label}, fetch=True)[0][0])

    def prune(self, days=0, max_records=0):
        if not self.ready:
            return 0
        n = 0
        if days and float(days) > 0:
            n += self._x(f"/* ltm:prune_age */ DELETE FROM {self.t_mem} WHERE profile_id = :p AND last_seen_at < "
                         "SYSTIMESTAMP - NUMTODSINTERVAL(:d, 'DAY')", {"p": self.profile, "d": float(days)},
                         commit=True)
        if max_records:
            n += self._x(f"/* ltm:prune_max */ DELETE FROM {self.t_mem} WHERE profile_id = :p AND id NOT IN (SELECT id "
                         f"FROM (SELECT id FROM {self.t_mem} WHERE profile_id = :p ORDER BY last_seen_at DESC "
                         f"FETCH FIRST {int(max_records)} ROWS ONLY))", {"p": self.profile}, commit=True)
        return max(0, n)

    def by_kind(self, kind, limit=20, scope=None):
        """v3.8.0: records of one kind (pinned identity facts), newest first.
        Plain SQL on the kind column."""
        if not self.ready:
            return []
        b = {"p": self.profile, "k": kind}
        sc = self._scope_sql(b, scope)
        rows = self._x(f"/* ltm:by_kind */ SELECT id, created_at, text, scope FROM {self.t_mem} WHERE profile_id = :p "
                       f"AND kind = :k{sc} ORDER BY created_at DESC FETCH FIRST {int(limit)} ROWS ONLY", b, fetch=True)
        return [{"id": r[0], "timestamp": _iso(r[1]), "text": _lob(r[2]), "kind": kind,
                 "scope": r[3] if len(r) > 3 else None} for r in rows or []]

    def records(self, limit=50):
        if not self.ready:
            return []
        lim = f" FETCH FIRST {int(limit)} ROWS ONLY" if limit else ""
        rows = self._x(f"/* ltm:records */ SELECT id, created_at, text, embed_label, dims, kind, scope FROM {self.t_mem} "
                       f"WHERE profile_id = :p ORDER BY created_at DESC{lim}", {"p": self.profile}, fetch=True)
        return [{"id": r[0], "timestamp": _iso(r[1]), "text": _lob(r[2]), "embed_model": r[3], "dims": r[4],
                 "kind": r[5], "scope": r[6] if len(r) > 6 else None, "metadata": {}}
                for r in reversed(rows or [])]

    def test(self):
        out = [(True, f"connected as {self.creds.get('user')} to {self._dsn_label()}")]
        out += [(False, n) for n in self.notes]
        if self.ready:
            out.append((True, f"{self.t_mem}: {self.count()} memories, VECTOR({self.dims}, FLOAT32)"))
            has_idx = self._x("/* ltm:vidx_exists */ SELECT index_name FROM all_indexes WHERE owner = :o "
                              "AND index_name = :i", {"o": self.schema, "i": self.vidx}, fetch=True)
            out.append((bool(has_idx) or self.index == "none",
                        f"vector index {self.vidx}: " + ("present" if has_idx else
                                                          "none (off in settings)" if self.index == "none" else
                                                          "MISSING: run `memory setup`")))
        else:
            out.append((True, f"{self.t_mem} not created yet: `memory setup` (or the first stored turn) creates it"))
        if self.onnx:
            models = self.onnx_models()
            ok = self.onnx.upper() in [m.upper() for m in models]
            out.append((ok, f"in-database model {self.onnx}: " + ("loaded" if ok else
                        "NOT FOUND in " + self.schema + (" (have: " + ", ".join(models) + ")" if models else
                                                          "; load one with `memory oracle load-onnx`"))))
        st = self.profile_status() if self.o.get("register_profile", True) else "off"
        out.append((st != "taken", {"mine": f"profile {self.profile} registered",
                                    "free": f"profile {self.profile} not registered yet (setup does it)",
                                    "taken": f"profile id {self.profile} belongs to another agent: pick another",
                                    "no-table": "no AGENT_PROFILES table visible (profile skipped)",
                                    "off": "profile registration off"}[st]))
        return out

    def _dsn_label(self):
        d = str(self.creds.get("dsn") or "")
        m = re.search(r"service_name\s*=\s*([^)\s]+)", d, re.I)
        return m.group(1) if m else (d if len(d) < 80 else d[:77] + "...")

    def load_onnx_cloud(self, model_name, uri, credential=None):
        """DBMS_VECTOR.LOAD_ONNX_MODEL_CLOUD: load an augmented ONNX embedding
        model (e.g. Oracle's prebuilt all_MiniLM_L12_v2) from object storage."""
        if not IDENT.match(model_name or ""):
            raise MemoryOffline("model name must be a plain Oracle name")
        self._x("/* ltm:load_onnx */ BEGIN DBMS_VECTOR.LOAD_ONNX_MODEL_CLOUD(model_name => :m, credential => :c, "
                "uri => :u, metadata => JSON('{\"function\":\"embedding\",\"embeddingOutput\":\"embedding\","
                "\"input\":{\"input\":[\"DATA\"]}}')); END;",
                {"m": model_name.upper(), "c": credential, "u": uri}, commit=True)
        return model_name.upper()
