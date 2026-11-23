"""ORDS backend for the testbed's long-term memory (v3.7.1).

The same MEM tables, vector search, keyword search and pending queue as the
wallet backend (nimlab.ltm_oracle), reached over HTTPS through Oracle REST
Data Services instead of a SQL*Net connection, so nothing but Python's own
urllib is needed on the phone (no oracledb, no wallet).

It talks to ORDS REST-Enabled SQL on the REST-enabled schema:

    POST {base_url}/_/sql      {"statementText": ..., "binds": [...]}

base_url is the schema's ORDS root, for example
https://xxxx.adb.us-ashburn-1.oraclecloudapps.com/ords/mem

Two ways to sign in:
  basic   the database user (the REST-enabled schema) and its password
  oauth   an ORDS OAuth client (client credentials): the client id and
          secret get a bearer token from {base_url}/oauth/token, renewed
          before it expires

The password or client secret comes from an env var or a credentials file
outside the project (~/.config/nimlab/ords_mem.json, mode 600); it is never
written to config_cluster.json, printed, or put in a bug report.

Every SQL statement is the wallet backend's own (OracleBackend), so both
backends keep exactly the same tables, profile guard and recall; only the
vector binds differ: a vector goes over HTTPS as JSON text and the SQL wraps
it in TO_VECTOR().
"""

import array
import base64
import json
import os
import stat
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .ltm import MemoryOffline
from .ltm_oracle import OracleBackend

ENV = {"base_url": "NIMLAB_ORDS_URL", "auth": "NIMLAB_ORDS_AUTH", "user": "NIMLAB_ORDS_USER",
       "password": "NIMLAB_ORDS_PASSWORD", "client_id": "NIMLAB_ORDS_CLIENT_ID",
       "client_secret": "NIMLAB_ORDS_CLIENT_SECRET"}
SECRETS = ("password", "client_secret")
AUTHS = ("basic", "oauth")
DEFAULT_CREDENTIALS = "~/.config/nimlab/ords_mem.json"
FETCH_LIMIT = 10000


class OrdsError(Exception):
    """One statement failed; args[0].code is the ORA- number, like oracledb."""

    class _Code:
        def __init__(self, code, message):
            self.code = code
            self.message = message

        def __str__(self):
            return self.message

    def __init__(self, code, message):
        super().__init__(OrdsError._Code(code, message))
        self.code = code
        self.message = message

    def __str__(self):
        return self.message


def load_credentials(o, environ=None):
    """base_url, auth, user, client_id: settings, then the credentials file,
    then env (env wins). password and client_secret: file or env only.
    -> (creds, notes)."""
    env = os.environ if environ is None else environ
    creds, notes = {}, []
    for k in ("base_url", "auth", "user", "client_id"):
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
            if data.get(k):
                creds[k] = data[k]
        try:
            if os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                notes.append(f"{path} is readable by other users: chmod 600 it")
        except OSError:
            pass
    for k, var in ENV.items():
        if env.get(var):
            creds[k] = env[var]
    creds["auth"] = str(creds.get("auth") or "basic").lower()
    if creds.get("base_url"):
        creds["base_url"] = str(creds["base_url"]).rstrip("/")
        if creds["base_url"].endswith("/_/sql"):
            creds["base_url"] = creds["base_url"][:-len("/_/sql")]
    return creds, notes


def missing_credentials(creds):
    need = ["base_url"] + (["client_id", "client_secret"] if creds.get("auth") == "oauth" else ["user", "password"])
    return [k for k in need if not creds.get(k)]


def check_url(url):
    """HTTPS only; plain http just for localhost (a test ORDS on the phone)."""
    u = urllib.parse.urlparse(url or "")
    if u.scheme == "https" and u.netloc:
        return None
    if u.scheme == "http" and (u.hostname or "") in ("127.0.0.1", "localhost", "::1"):
        return None
    return f"ORDS base_url must be an https:// URL (got {url!r})"


def save_credentials(path, values):
    """Write (merge) the credentials file with mode 600, outside the project.
    -> the path."""
    path = os.path.expanduser(path or DEFAULT_CREDENTIALS)
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f) or {}
        except (OSError, ValueError):
            data = {}
    data.update({k: v for k, v in values.items() if v not in (None, "") and k in ENV})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return path


def _bind(name, v):
    if isinstance(v, (array.array, list, tuple)):
        return {"name": name, "data_type": "CLOB", "value": json.dumps([float(x) for x in v])}
    if isinstance(v, bool):
        return {"name": name, "data_type": "NUMBER", "value": int(v)}
    if isinstance(v, (int, float)):
        return {"name": name, "data_type": "NUMBER", "value": v}
    if v is None:
        return {"name": name, "data_type": "VARCHAR2", "value": None}
    s = str(v)
    return {"name": name, "data_type": "CLOB" if len(s) > 4000 else "VARCHAR2", "value": s}


class OrdsSession:
    """Sends statements to {base_url}/_/sql over HTTPS. Thread-safe."""

    def __init__(self, creds, timeout=20, opener=None, clock=time.monotonic):
        self.creds = dict(creds)
        self.timeout = float(timeout or 20)
        self.opener = opener or urllib.request.urlopen
        self.clock = clock
        self._token = None
        self._token_until = 0.0
        self._lock = threading.Lock()
        bad = check_url(self.creds.get("base_url"))
        if bad:
            raise MemoryOffline(bad)
        if self.creds.get("auth") not in AUTHS:
            raise MemoryOffline(f"ORDS auth must be basic or oauth (got {self.creds.get('auth')!r})")

    @property
    def sql_url(self):
        return self.creds["base_url"] + "/_/sql"

    def clean(self, text):
        msg = str(text or "")
        for k in SECRETS + ("token",):
            v = self.creds.get(k) if k != "token" else self._token
            if v:
                msg = msg.replace(v, "***")
        return msg[:300]

    def _basic(self, a, b):
        return "Basic " + base64.b64encode(f"{a}:{b}".encode("utf-8")).decode("ascii")

    def token(self, force=False):
        """OAuth client credentials: a bearer token, renewed a minute early."""
        with self._lock:
            if self._token and not force and self.clock() < self._token_until:
                return self._token
            req = urllib.request.Request(
                self.creds["base_url"] + "/oauth/token", data=b"grant_type=client_credentials", method="POST",
                headers={"Authorization": self._basic(self.creds["client_id"], self.creds["client_secret"]),
                         "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
            try:
                with self.opener(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode("utf-8") or "{}")
            except urllib.error.HTTPError as e:
                raise MemoryOffline(f"ORDS OAuth token: HTTP {e.code}" + (
                    " (check the client id and secret)" if e.code in (400, 401) else ""))
            except (urllib.error.URLError, OSError, ValueError) as e:
                raise MemoryOffline("ORDS OAuth token: " + self.clean(getattr(e, "reason", e)))
            tok = data.get("access_token")
            if not tok:
                raise MemoryOffline("ORDS OAuth token: no access_token in the reply")
            self._token = tok
            self._token_until = self.clock() + max(30.0, float(data.get("expires_in") or 3600) - 60)
            return tok

    def _auth_header(self, force=False):
        if self.creds.get("auth") == "oauth":
            return "Bearer " + self.token(force)
        return self._basic(self.creds["user"], self.creds["password"])

    def run(self, sql, binds=None, fetch=False):
        """One statement -> (rows or None, rowcount). Raises OrdsError for an
        ORA- error, MemoryOffline for transport and sign-in problems."""
        body = {"statementText": sql, "binds": [_bind(k, v) for k, v in (binds or {}).items()]}
        if fetch:
            body.update({"offset": 0, "limit": FETCH_LIMIT})
        data = json.dumps(body).encode("utf-8")
        for attempt in (0, 1):
            req = urllib.request.Request(self.sql_url, data=data, method="POST", headers={
                "Authorization": self._auth_header(force=attempt == 1), "Content-Type": "application/json",
                "Accept": "application/json"})
            try:
                with self.opener(req, timeout=self.timeout) as r:
                    reply = json.loads(r.read().decode("utf-8") or "{}")
                break
            except urllib.error.HTTPError as e:
                if e.code == 401 and self.creds.get("auth") == "oauth" and attempt == 0:
                    continue        # token expired early: get a new one once
                hint = {401: " (sign-in refused: check the user and password, or the OAuth client)",
                        403: " (not allowed: REST-enable the schema and allow REST-Enabled SQL)",
                        404: " (no REST-Enabled SQL here: check base_url, it ends with /ords/<schema alias>)"}
                raise MemoryOffline(f"ORDS HTTP {e.code}{hint.get(e.code, '')}")
            except (urllib.error.URLError, OSError, ValueError) as e:
                raise MemoryOffline("ORDS: " + self.clean(getattr(e, "reason", e) or type(e).__name__))
        items = reply.get("items") or []
        if not items:
            raise MemoryOffline("ORDS: empty reply from REST-Enabled SQL")
        it = items[0]
        if it.get("errorCode") or it.get("errorMessage"):
            raise OrdsError(int(it.get("errorCode") or 0), self.clean(
                f"ORA-{int(it.get('errorCode') or 0):05d}: " + str(it.get("errorMessage") or "").strip()))
        rs = it.get("resultSet")
        if rs is not None:
            cols = [m.get("jsonColumnName") or str(m.get("columnName", "")).lower() for m in rs.get("metadata") or []]
            rows = [tuple(row.get(c) for c in cols) for row in rs.get("items") or []]
            return rows, len(rows)
        n = it.get("result")
        return (None if not fetch else []), int(n) if isinstance(n, (int, float)) else 0


def is_query(sql):
    """SELECT / WITH after any leading /* comments */."""
    t = sql.lstrip()
    while t.startswith("/*") and "*/" in t:
        t = t[t.index("*/") + 2:].lstrip()
    return t[:6].upper() == "SELECT" or t[:4].upper() == "WITH"


class _Cursor:
    def __init__(self, session):
        self.s = session
        self.rows = None
        self.rowcount = 0

    def execute(self, sql, binds=None):
        rows, self.rowcount = self.s.run(sql, binds, fetch=is_query(sql))
        self.rows = rows

    def executemany(self, sql, many):
        n = 0
        for b in many:
            self.execute(sql, b)
            n += self.rowcount
        self.rowcount = n

    def fetchall(self):
        return list(self.rows or [])

    def close(self):
        pass


class OrdsConnection:
    """Just enough of a DB-API connection for OracleBackend._x. Every
    REST-Enabled SQL request commits on its own, so commit() does nothing."""

    def __init__(self, session):
        self.session = session

    def cursor(self):
        return _Cursor(self.session)

    def commit(self):
        pass

    def close(self):
        pass


class OrdsBackend(OracleBackend):
    """OracleBackend over ORDS: o = long_term.oracle (schema, table prefix,
    profile, index, distance...), ords = long_term.ords (base_url, auth,
    credentials_file, timeout_sec)."""

    name = "ords"

    def __init__(self, o, ords=None, embed_model=None, opener=None, environ=None, log=None):
        self.ords = dict(ords or {})
        self._opener = opener
        self._environ = environ
        super().__init__(o, embed_model=embed_model, connect_fn=self._open, environ=environ, log=log)

    # the wallet backend's credential lookup is replaced by the ORDS one
    def connect(self):
        if not getattr(self, "_ords_loaded", False):
            self.creds, self.notes = load_credentials(self.ords, self._environ)
            self._ords_loaded = True
        miss = missing_credentials(self.creds)
        if miss:
            raise MemoryOffline("ORDS: missing " + ", ".join(miss) + ": set " + ", ".join(ENV[m] for m in miss)
                                + f" or run `nimlab memory ords login` (saves {self.ords.get('credentials_file') or DEFAULT_CREDENTIALS},"
                                  " mode 600)")
        with self._lock:
            if self._conn is None:
                self._conn = self._connect_fn(self.creds, self.ords.get("timeout_sec") or 20)
        return self._conn

    def _open(self, creds, timeout):
        # one session per backend: a reconnect after an ORA- error keeps the
        # OAuth token instead of asking for a new one
        ses = getattr(self, "_session", None)
        if ses is None or ses.creds != dict(creds):
            ses = self._session = OrdsSession(creds, timeout=timeout, opener=self._opener)
        return OrdsConnection(ses)

    def _vsql(self, name):
        return f"TO_VECTOR(:{name})"

    def where(self):
        return f"{self.t_mem} via ORDS (profile {self.profile})"

    def _dsn_label(self):
        u = urllib.parse.urlparse(self.creds.get("base_url") or "")
        return f"{u.netloc}{u.path} over HTTPS ({self.creds.get('auth')})"

    def test(self):
        rows = self._x("/* ltm:ords_ping */ SELECT USER FROM dual", fetch=True)
        who = rows[0][0] if rows else "?"
        out = super().test()
        out[0] = (True, f"ORDS REST-Enabled SQL at {self._dsn_label()}: signed in as {who}")
        return out

    def load_onnx_cloud(self, model_name, uri, credential=None):
        return super().load_onnx_cloud(model_name, uri, credential)
