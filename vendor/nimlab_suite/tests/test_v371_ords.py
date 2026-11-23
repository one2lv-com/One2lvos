"""v3.7.1 ORDS backend: the MEM tables over HTTPS (ORDS REST-Enabled SQL),
basic or OAuth client-credentials sign-in, the same recall, keyword search
and pending queue as the wallet backend. The fake ORDS server below turns
each REST-Enabled SQL request back into a statement for the fake Oracle
database the wallet backend's tests use, so both backends are checked
against the same database behaviour."""

import array
import base64
import io
import json
import os
import re
import shutil
import stat
import tempfile
import unittest
import urllib.error
from unittest import mock

from nimlab import config, ltm, ltm_ords, memmenu
from nimlab.memory import MemoryCore
from tests.test_ltm import BackendContract, FakeOracleDB, FnEmbedder, OraError, lt


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class FakeORDS:
    """POST /_/sql and /oauth/token for one REST-enabled schema."""

    def __init__(self, db=None, base="https://adb.example.com/ords/mem", user="MEM", password="pw-S3cret!",
                 client=("cid-123", "csecret-XYZ"), token_ttl=3600):
        self.db = db or FakeOracleDB()
        self.base = base
        self.user, self.password = user, password
        self.client = client
        self.token_ttl = token_ttl
        self.tokens = []
        self.requests = []
        self.down = False
        self.revoke = False

    def _http(self, url, code, body=b"{}"):
        return urllib.error.HTTPError(url, code, "err", {}, io.BytesIO(body))

    def __call__(self, req, timeout=None):
        url = req.full_url
        self.requests.append((url, dict(req.header_items()), req.data, timeout))
        if self.down:
            raise urllib.error.URLError("[Errno 111] Connection refused")
        auth = req.get_header("Authorization") or ""
        if url == self.base + "/oauth/token":
            want = "Basic " + base64.b64encode(f"{self.client[0]}:{self.client[1]}".encode()).decode()
            if auth != want:
                raise self._http(url, 401)
            tok = f"tok{len(self.tokens) + 1}"
            self.tokens.append(tok)
            return Resp(json.dumps({"access_token": tok, "token_type": "bearer",
                                    "expires_in": self.token_ttl}).encode())
        if url != self.base + "/_/sql":
            raise self._http(url, 404)
        if auth.startswith("Bearer "):
            if self.revoke or auth[7:] not in self.tokens:
                self.revoke = False
                raise self._http(url, 401)
        elif auth != "Basic " + base64.b64encode(f"{self.user}:{self.password}".encode()).decode():
            raise self._http(url, 401)
        body = json.loads(req.data.decode())
        sql = body["statementText"]
        binds = {}
        for b in body.get("binds") or []:
            v = b["value"]
            if re.search(r"TO_VECTOR\(:" + re.escape(b["name"]) + r"\)", sql):
                v = array.array("f", json.loads(v))
            binds[b["name"]] = v
        sql = re.sub(r"TO_VECTOR\(:(\w+)\)", r":\1", sql)
        if "ltm:ords_ping" in sql:
            return Resp(json.dumps({"items": [{"statementId": 1, "resultSet": {
                "metadata": [{"columnName": "USER", "jsonColumnName": "user"}],
                "items": [{"user": self.user}]}}]}).encode())
        cur = self.db.connect({}, timeout).cursor()
        try:
            cur.execute(sql, binds)
        except OraError as e:
            err = e.args[0]
            return Resp(json.dumps({"items": [{"statementId": 1, "errorCode": err.code,
                                               "errorMessage": err.message.split(": ", 1)[-1]}]}).encode())
        if ltm_ords.is_query(sql):
            rows = cur.fetchall()
            n = len(rows[0]) if rows else 0
            meta = [{"columnName": f"C{i}", "jsonColumnName": f"c{i}"} for i in range(n)]
            items = [{f"c{i}": (list(v) if isinstance(v, array.array) else
                                 v.isoformat() if hasattr(v, "isoformat") else v) for i, v in enumerate(r)}
                     for r in rows]
            return Resp(json.dumps({"items": [{"statementId": 1, "resultSet": {"metadata": meta,
                                                                               "items": items}}]}).encode())
        return Resp(json.dumps({"items": [{"statementId": 1, "result": cur.rowcount}]}).encode())


class OrdsCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = mock.patch.dict(os.environ, {"NIMLAB_DATA_DIR": self.tmp})
        p.start()
        self.addCleanup(p.stop)
        self.server = FakeORDS()

    def env_basic(self):
        return {"NIMLAB_ORDS_URL": self.server.base, "NIMLAB_ORDS_USER": "MEM",
                "NIMLAB_ORDS_PASSWORD": self.server.password}

    def backend(self, environ=None, **ords):
        oo = dict(ltm.DEFAULTS["oracle"])
        od = config.deep_merge(dict(ltm.DEFAULTS["ords"]), ords)
        od.setdefault("credentials_file", "")
        if "credentials_file" not in ords:
            od["credentials_file"] = ""
        return ltm_ords.OrdsBackend(oo, od, opener=self.server,
                                    environ=self.env_basic() if environ is None else environ)

    def core(self, embedder=None, **kw):
        b = self.backend(**kw)
        s = lt(backend="ords", embedding={"provider": "role"})
        return MemoryCore(None, "x", settings=s, backend=b, embedder=embedder or FnEmbedder())


class TestOrdsBackendContract(BackendContract, OrdsCase):
    def make(self, **kw):
        return self.core()


class TestOrdsBackend(OrdsCase):
    def test_basic_auth_store_and_vector_recall_over_https(self):
        m = self.core()
        m.store("User: my cat is called Miso | Assistant: noted", turn_key="t1")
        hits = m.recall("what is my cat called", threshold=-1)
        self.assertTrue(hits)
        self.assertIn("Miso", hits[0][1])
        sent = [r for r in self.server.requests if r[0].endswith("/_/sql")]
        self.assertTrue(sent)
        for url, headers, data, timeout in sent:
            self.assertTrue(url.startswith("https://"))
            self.assertTrue(headers["Authorization"].startswith("Basic "))
            self.assertEqual(timeout, 20.0)
        # vectors go as JSON text wrapped in TO_VECTOR, never as a raw bind
        ins = [json.loads(d) for _, _, d, _ in sent if b"ltm:insert" in d][0]
        self.assertIn("TO_VECTOR(:v)", ins["statementText"])
        v = [b for b in ins["binds"] if b["name"] == "v"][0]
        self.assertEqual(v["data_type"], "CLOB")
        self.assertIsInstance(json.loads(v["value"]), list)
        # same tables and profile as the wallet backend
        self.assertIn("MEM.TESTBED_MEMORIES", self.server.db.tables)
        self.assertEqual({r["p"] for r in self.server.db.rows.values()}, {"TESTBED"})

    def test_keyword_search_and_pending_queue(self):
        emb = FnEmbedder()
        m = self.core(embedder=emb)
        emb.fail = True
        m.store("User: the bug id is B-7Q2K9X | Assistant: logged", turn_key="t2")
        self.assertEqual(len(m.pending()), 1)
        kw = m.keyword("B-7Q2K9X")
        self.assertTrue(any("B-7Q2K9X" in h[1] for h in kw))
        emb.fail = False
        self.assertEqual(m.embed_pending(), (1, 0))
        self.assertEqual(m.pending(), [])
        self.assertTrue(any("B-7Q2K9X" in r["text"] for r in self.server.db.rows.values()))

    def test_oauth_client_credentials_token_cached_and_renewed(self):
        env = {"NIMLAB_ORDS_URL": self.server.base, "NIMLAB_ORDS_AUTH": "oauth",
               "NIMLAB_ORDS_CLIENT_ID": "cid-123", "NIMLAB_ORDS_CLIENT_SECRET": "csecret-XYZ"}
        m = self.core(environ=env)
        m.store("User: I like green tea | Assistant: ok", turn_key="t3")
        m.recall("tea")
        self.assertEqual(self.server.tokens, ["tok1"])           # one token for many statements
        self.server.revoke = True                                  # server drops the token
        m.recall("tea")
        self.assertEqual(self.server.tokens, ["tok1", "tok2"])    # renewed once, statement retried
        sql = [h for u, h, _, _ in self.server.requests if u.endswith("/_/sql")]
        self.assertTrue(all(h["Authorization"].startswith("Bearer ") for h in sql))

    def test_oauth_expiry_renews_before_use(self):
        now = [0.0]
        s = ltm_ords.OrdsSession({"base_url": self.server.base, "auth": "oauth", "client_id": "cid-123",
                                  "client_secret": "csecret-XYZ"}, opener=self.server, clock=lambda: now[0])
        s.token()
        now[0] = 3000
        s.token()
        self.assertEqual(len(self.server.tokens), 1)
        now[0] = 3600
        s.token()
        self.assertEqual(len(self.server.tokens), 2)

    def test_bad_login_is_offline_with_a_hint_and_no_secret(self):
        env = dict(self.env_basic(), NIMLAB_ORDS_PASSWORD="wrong-pass-123")
        with self.assertRaises(ltm.MemoryOffline) as cm:
            self.core(environ=env)
        self.assertIn("HTTP 401", str(cm.exception))
        self.assertNotIn("wrong-pass-123", str(cm.exception))
        bad = ltm_ords.OrdsSession({"base_url": self.server.base, "auth": "oauth", "client_id": "x",
                                    "client_secret": "nope"}, opener=self.server)
        with self.assertRaises(ltm.MemoryOffline) as cm:
            bad.run("SELECT 1 FROM dual", fetch=True)
        self.assertIn("check the client id and secret", str(cm.exception))

    def test_transport_error_and_wrong_url(self):
        self.server.down = True
        with self.assertRaises(ltm.MemoryOffline) as cm:
            self.backend()
        self.assertIn("Connection refused", str(cm.exception))
        self.server.down = False
        env = dict(self.env_basic(), NIMLAB_ORDS_URL="https://adb.example.com/ords/other")
        with self.assertRaises(ltm.MemoryOffline) as cm:
            self.backend(environ=env)
        self.assertIn("HTTP 404", str(cm.exception))
        self.assertIn("base_url", str(cm.exception))

    def test_ora_errors_keep_their_code(self):
        s = ltm_ords.OrdsSession(dict(base_url=self.server.base, auth="basic", user="MEM",
                                      password=self.server.password), opener=self.server)
        with self.assertRaises(ltm_ords.OrdsError) as cm:
            s.run("/* ltm:count */ SELECT COUNT(*) FROM MEM.TESTBED_MEMORIES WHERE agent_id = :p", {"p": "X"},
                  fetch=True)
        self.assertEqual(cm.exception.args[0].code, 942)
        self.assertIn("ORA-00942", str(cm.exception))

    def test_https_only(self):
        for url in ("http://adb.example.com/ords/mem", "ftp://x/ords", "adb.example.com/ords/mem"):
            with self.assertRaises(ltm.MemoryOffline):
                ltm_ords.OrdsSession({"base_url": url, "auth": "basic", "user": "u", "password": "p"})
        ltm_ords.OrdsSession({"base_url": "http://127.0.0.1:8080/ords/mem", "auth": "basic", "user": "u",
                              "password": "p"})

    def test_missing_login_names_env_and_login_command(self):
        with self.assertRaises(ltm.MemoryOffline) as cm:
            self.backend(environ={"NIMLAB_ORDS_URL": self.server.base})
        self.assertIn("NIMLAB_ORDS_USER", str(cm.exception))
        self.assertIn("memory ords login", str(cm.exception))

    def test_bind_types(self):
        self.assertEqual(ltm_ords._bind("n", 5), {"name": "n", "data_type": "NUMBER", "value": 5})
        self.assertEqual(ltm_ords._bind("s", "x" * 5000)["data_type"], "CLOB")
        self.assertEqual(ltm_ords._bind("s", "abc")["data_type"], "VARCHAR2")
        self.assertEqual(json.loads(ltm_ords._bind("v", array.array("f", [1, 2]))["value"]), [1.0, 2.0])
        self.assertTrue(ltm_ords.is_query("/* ltm:x */ SELECT 1 FROM dual"))
        self.assertTrue(ltm_ords.is_query("  WITH a AS (SELECT 1 FROM dual) SELECT * FROM a"))
        self.assertFalse(ltm_ords.is_query("/* ltm:insert */ INSERT INTO t VALUES (1)"))


class TestOrdsCredentials(OrdsCase):
    def test_login_saves_outside_project_hidden_mode_600(self):
        path = os.path.join(self.tmp, "cfg", "ords_mem.json")
        ms = {"long_term": ltm.settings_from({})}
        ms["long_term"]["ords"]["credentials_file"] = path
        answers = iter([self.server.base + "/_/sql", "basic", "MEM"])
        hidden = []
        out = []
        memmenu.ords_login(ms, input_fn=lambda p="": next(answers),
                           getpass_fn=lambda p="": (hidden.append(p), self.server.password)[1], out=out.append)
        self.assertEqual(len(hidden), 1)                       # password typed hidden
        data = json.load(open(path))
        self.assertEqual(data["password"], self.server.password)
        self.assertEqual(data["base_url"], self.server.base)   # /_/sql trimmed
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        od = ms["long_term"]["ords"]
        self.assertEqual((od["base_url"], od["auth"], od["user"]), (self.server.base, "basic", "MEM"))
        self.assertNotIn(self.server.password, json.dumps(ms))  # never in config_cluster.json
        self.assertNotIn(self.server.password, "\n".join(out))
        # the backend finds it from the file alone
        b = self.backend(environ={}, credentials_file=path, base_url="")
        ok, msg = b.test()[0]
        self.assertTrue(ok, msg)
        self.assertIn("signed in as MEM", msg)

    def test_oauth_login(self):
        path = os.path.join(self.tmp, "o.json")
        ms = {"long_term": ltm.settings_from({})}
        ms["long_term"]["ords"]["credentials_file"] = path
        answers = iter([self.server.base, "oauth", "cid-123"])
        memmenu.ords_login(ms, input_fn=lambda p="": next(answers), getpass_fn=lambda p="": "csecret-XYZ",
                           out=lambda *a: None)
        b = self.backend(environ={}, credentials_file=path)
        self.assertTrue(b.test()[0][0])
        self.assertEqual(self.server.tokens, ["tok1"])

    def test_secret_settings_refused_and_url_checked(self):
        ms = {"long_term": ltm.settings_from({})}
        with self.assertRaises(ValueError):
            memmenu.apply_setting(ms, "ords.password", "x")
        with self.assertRaises(ValueError):
            memmenu.apply_setting(ms, "ords.base_url", "http://example.com/ords/mem")
        with self.assertRaises(ValueError):
            memmenu.apply_setting(ms, "ords.base_url", "https://MEM:pw@example.com/ords/mem")
        memmenu.apply_setting(ms, "ords.base_url", "https://example.com/ords/mem/")
        self.assertEqual(ms["long_term"]["ords"]["base_url"], "https://example.com/ords/mem")
        memmenu.apply_setting(ms, "ords.auth", "oauth")
        with self.assertRaises(ValueError):
            memmenu.apply_setting(ms, "ords.auth", "kerberos")

    def test_world_readable_file_is_flagged(self):
        path = os.path.join(self.tmp, "open.json")
        with open(path, "w") as f:
            json.dump({"base_url": self.server.base, "user": "MEM", "password": "p"}, f)
        os.chmod(path, 0o644)
        creds, notes = ltm_ords.load_credentials({"credentials_file": path}, {})
        self.assertTrue(any("chmod 600" in n for n in notes))

    def test_auto_picks_ords_when_only_ords_is_configured(self):
        s = ltm.settings_from({})
        s["ords"]["credentials_file"] = ""
        s["oracle"]["credentials_file"] = ""
        self.assertEqual(ltm.resolve_backend(s, {}), "json")
        self.assertEqual(ltm.resolve_backend(s, self.env_basic()), "ords")
        self.assertEqual(ltm.resolve_backend(dict(s, backend="ords"), {}), "ords")

    def test_use_backend_and_menu(self):
        ms = {"long_term": ltm.settings_from({})}
        memmenu.use_backend(ms, "ords", "https://example.com/ords/mem")
        self.assertEqual(ms["long_term"]["backend"], "ords")
        self.assertEqual(ms["long_term"]["ords"]["base_url"], "https://example.com/ords/mem")
        path = os.path.join(self.tmp, "m.json")
        cluster = {"memory_settings": {"long_term": ltm.settings_from({})}}
        cluster["memory_settings"]["long_term"]["ords"]["credentials_file"] = path
        keys = iter(["3o", self.server.base, "basic", "MEM", "y", "0"])
        saved = []
        memmenu.run_menu(cluster, input_fn=lambda p="": next(keys), out=lambda *a: None,
                         save_fn=lambda *a: saved.append(1),
                         getpass_fn=lambda p="": self.server.password)
        lt_ = cluster["memory_settings"]["long_term"]
        self.assertEqual(lt_["backend"], "ords")
        self.assertTrue(os.path.isfile(path))
        self.assertNotIn(self.server.password, json.dumps(cluster))

    def test_make_backend_builds_ords(self):
        s = ltm.settings_from({"long_term": {"backend": "ords"}})
        s["ords"]["credentials_file"] = ""
        with mock.patch.dict(os.environ, self.env_basic()), \
                mock.patch.object(ltm_ords.urllib.request, "urlopen", self.server):
            b = ltm.make_backend(s)
        self.assertIsInstance(b, ltm_ords.OrdsBackend)
        self.assertIn("via ORDS", ltm.describe(s))


if __name__ == "__main__":
    unittest.main()
