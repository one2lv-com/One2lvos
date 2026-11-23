"""Long-term memory (v3.6): backends, embedding providers, settings, the
automatic store/recall step, and the no-crash fallback. All offline: the
embedding servers are local fake HTTP servers, sentence-transformers is a
fake module, and Oracle is a fake python-oracledb connection that runs the
backend's tagged SQL against Python dicts."""

import array
import http.server
import json
import math
import os
import re
import sys
import tempfile
import threading
import types
import unittest
import shutil
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

from nimlab import config, ltm, ltm_oracle, memmenu, store
from nimlab.api import ModelResult
from nimlab.memory import MemoryCore
from tests.helpers import fresh_store


def tmpdir(test):
    d = tempfile.TemporaryDirectory()
    test.addCleanup(d.cleanup)
    return d.name


def bag_vec(text, dims=8):
    """A deterministic bag-of-words vector: texts sharing words are close."""
    v = [0.0] * dims
    for w in re.findall(r"[a-z]+", text.lower()):
        if w in ("user", "assistant", "the", "a", "is", "my", "and"):
            continue
        v[sum(map(ord, w)) % dims] += 1.0
    if not any(v):
        v[0] = 1e-3
    return v


class FnEmbedder:
    in_db = False

    def __init__(self, label="fake:bag", fn=bag_vec, fail=False):
        self.label, self.fn, self.fail, self.calls = label, fn, fail, []

    def embed(self, text, input_type):
        self.calls.append((text, input_type))
        if self.fail:
            raise ltm.EmbedError("embedder down")
        return self.fn(text)


def lt(**kw):
    s = {"long_term": config.deep_merge(ltm.settings_from({}), kw)}
    return s


# ---------------------------------------------------------------------------
class TestSettingsAndQualify(unittest.TestCase):
    def test_defaults_keep_the_classic_json_store_and_mem_schema_for_oracle(self):
        s = ltm.settings_from({})
        self.assertEqual(s["backend"], "auto")
        self.assertEqual(s["scope"], "shared")
        self.assertEqual(ltm.resolve_backend(dict(s, oracle=dict(s["oracle"], credentials_file="")), environ={}),
                         "json")
        self.assertEqual(ltm.resolve_backend(dict(s, oracle=dict(s["oracle"], credentials_file="")),
                                             environ=CREDS), "oracle")
        self.assertEqual(s["embedding"]["provider"], "role")
        self.assertEqual(s["oracle"]["schema"], "MEM")
        self.assertEqual(s["oracle"]["table_prefix"], "TESTBED")
        self.assertEqual(s["oracle"]["profile_id"], "TESTBED")
        self.assertTrue(s["auto_store"] and s["auto_recall"])

    def test_secrets_are_stripped(self):
        s = ltm.settings_from({"long_term": {"oracle": {"password": "hunter2", "user": "MEM"},
                                             "embedding": {"api_key": "sk-x"}}})
        self.assertNotIn("password", s["oracle"])
        self.assertNotIn("api_key", s["embedding"])
        self.assertEqual(s["oracle"]["user"], "MEM")

    def test_salient_mode(self):
        s = ltm.settings_from({})
        self.assertFalse(ltm.qualifies("thanks!", s)[0])
        self.assertFalse(ltm.qualifies("ok", s)[0])
        self.assertFalse(ltm.qualifies("why?", s)[0])          # too short
        self.assertTrue(ltm.qualifies("I'm allergic", s)[0])  # short but a memory cue
        self.assertTrue(ltm.qualifies("explain how vector indexes work in Oracle", s)[0])
        self.assertFalse(ltm.qualifies("don't remember this: my pin is 1234", s)[0])

    def test_all_and_facts_modes(self):
        self.assertTrue(ltm.qualifies("ok", dict(ltm.settings_from({}), store_mode="all"))[0])
        f = dict(ltm.settings_from({}), store_mode="facts")
        self.assertFalse(ltm.qualifies("what is the weather like today", f)[0])
        self.assertTrue(ltm.qualifies("My dog is called Rex. What should I feed him?", f)[0])
        self.assertEqual(ltm.extract_facts("My dog is called Rex. What should I feed him? I live in Pahrump."),
                         ["My dog is called Rex.", "I live in Pahrump."])


# ---------------------------------------------------------------------------
class BackendContract:
    """The same behaviour for every backend (mixed into a TestCase)."""

    def make(self, **settings):
        raise NotImplementedError

    def test_store_recall_and_label_isolation(self):
        m = self.make()
        a = m.store("User: my cat is called Miso | Assistant: cute")
        m.store("User: tell me about oracle vector search | Assistant: ...")
        self.assertTrue(a)
        hits = m.recall("cat Miso", top_k=2, threshold=0.1)
        self.assertTrue(hits)
        self.assertIn("Miso", hits[0][1])
        self.assertEqual(hits[0][3], a)
        self.assertEqual(m.count(), 2)
        # vectors from another embedder are never compared
        m._embedder_given = FnEmbedder(label="other:model")
        self.assertEqual(m.recall("cat Miso", 2, 0.1), [])
        self.assertEqual(m.incompatible_count(), 2)

    def test_threshold_and_k(self):
        m = self.make()
        for t in ("cat Miso", "cat Luna", "cat Tom", "dog Rex"):
            m.store(f"User: {t} likes fish | Assistant: ok", dedupe="off")
        self.assertEqual(len(m.recall("cat", top_k=2, threshold=0.0)), 2)
        self.assertEqual(m.recall("zzzz qqqq", top_k=3, threshold=0.99), [])

    def test_dedupe_exact_and_turn_key(self):
        m = self.make()
        self.assertTrue(m.store("User: I live in Pahrump | Assistant: nice"))
        self.assertIsNone(m.store("User: I live in Pahrump | Assistant: nice"))
        self.assertTrue(m.store("User: a | Assistant: b", turn_key="k1", dedupe="off"))
        self.assertIsNone(m.store("User: a different reply | Assistant: c", turn_key="k1", dedupe="off"))
        self.assertEqual(m.count(), 2)

    def test_dedupe_semantic(self):
        m = self.make()
        m.settings["dedupe"] = "semantic"
        m.settings["dedupe_threshold"] = 0.95
        self.assertTrue(m.store("User: my cat is Miso | Assistant: ok"))
        self.assertIsNone(m.store("User: Miso, my cat | Assistant: ok"))   # same words: near duplicate
        self.assertTrue(m.store("User: my dog is Rex | Assistant: ok"))
        self.assertEqual(m.count(), 2)

    def test_delete_and_max_records(self):
        m = self.make()
        ids = [m.store(f"User: fact number {w} | Assistant: ok") for w in ("one", "two", "three", "four")]
        self.assertTrue(m.delete(ids[0]))
        self.assertFalse(m.delete("nope"))
        m.settings["max_records"] = 2
        self.assertEqual(m.prune(), 1)
        self.assertEqual(m.count(), 2)

    def test_remember_follows_settings(self):
        m = self.make()
        self.assertEqual(m.remember("thanks", "you're welcome"), [])
        self.assertEqual(len(m.remember("I work night shifts at the casino", "Got it.", turn_key="t1")), 1)
        self.assertEqual(m.remember("I work night shifts at the casino", "Got it.", turn_key="t1"), [])
        m.settings["auto_store"] = False
        self.assertEqual(m.remember("I have two cats named Miso and Luna", "ok"), [])
        m.settings.update(auto_store=True, store_mode="facts")
        ids = m.remember("My sister is called Ana. I live in Pahrump. Any tips?", "Sure", turn_key="t2")
        self.assertEqual(len(ids), 3)   # two facts + the pinned identity fact "Lives in: Pahrump" (3.8.0)
        self.assertEqual(m.identity_facts(), {"location": "Pahrump"})
        texts = [r["text"] for r in m.backend.records(0)]
        self.assertIn("My sister is called Ana.", texts)
        self.assertIn("I live in Pahrump.", texts)

    def test_error_replies_are_not_stored(self):
        m = self.make()
        self.assertEqual(m.remember("I like jazz a lot", "[ERROR] model failed"), [])


class TestJsonBackend(BackendContract, unittest.TestCase):
    def make(self, **kw):
        self.path = os.path.join(tmpdir(self), "memory.json")
        return MemoryCore(None, "x", settings=lt(backend="json", **kw), embedder=FnEmbedder(), path=self.path)

    def test_file_format_unchanged(self):
        m = self.make()
        m.store("User: I like jazz | Assistant: ok", turn_key="tk")
        data = json.load(open(self.path))
        self.assertEqual(set(data[0]), {"id", "timestamp", "text", "embed_model", "dims", "vector", "metadata"})
        self.assertEqual(data[0]["metadata"]["turn_key"], "tk")

    def test_classic_constructor_still_works(self):
        class C:
            def embed(self, model, texts, input_type=None, url=None, timeout=None):
                return ModelResult(True, data=[bag_vec(texts[0])])
        m = MemoryCore(C(), "nvidia/embed", path=os.path.join(tmpdir(self), "m.json"))
        self.assertTrue(m.store("User: hello there friend | Assistant: hi"))
        self.assertEqual(m.memories[0]["embed_model"], "nvidia/embed")


class TestLocalBackend(BackendContract, unittest.TestCase):
    def make(self, **kw):
        self.dir = getattr(self, "dir", None) or os.path.join(tmpdir(self), "my mem")
        return MemoryCore(None, "x", settings=lt(backend="local", local={"directory": self.dir}, **kw),
                          embedder=FnEmbedder())

    def test_persists_across_sessions(self):
        m = self.make()
        m.store("User: my cat is called Miso | Assistant: ok")
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "memories.sqlite")))
        m2 = self.make()                                  # a new session, same directory
        self.assertEqual(m2.count(), 1)
        self.assertIn("Miso", m2.recall("cat Miso", 1, 0.1)[0][1])

    def test_default_directory_is_under_data(self):
        with fresh_store():
            m = MemoryCore(None, "x", settings=lt(backend="local"), embedder=FnEmbedder())
            self.assertEqual(os.path.dirname(m.backend.where()), os.path.join(store.data_dir(), "ltm"))

    def test_retention_days(self):
        m = self.make()
        rid = m.store("User: an old fact about boats | Assistant: ok")
        m.store("User: a fresh fact about trains | Assistant: ok")
        m.backend._run("UPDATE memories SET last_seen_at = '2001-01-01T00:00:00+00:00' WHERE id = ?", (rid,),
                       commit=True)
        m.settings["retention_days"] = 30
        self.assertEqual(m.prune(), 1)
        self.assertEqual([r["text"][:20] for r in m.backend.records(0)], ["User: a fresh fact a"])

    def test_recall_touches_nothing_but_duplicates_refresh_last_seen(self):
        m = self.make()
        rid = m.store("User: I like jazz | Assistant: ok")
        m.store("User: I like jazz | Assistant: ok")
        hits = m.backend._run("SELECT hits FROM memories WHERE id = ?", (rid,))[0][0][0]
        self.assertEqual(hits, 2)

    def test_unwritable_directory_degrades(self):
        f = os.path.join(tmpdir(self), "file")
        open(f, "w").close()
        m = MemoryCore(None, "x", settings=lt(backend="local", local={"directory": f}), embedder=FnEmbedder())
        self.assertIsNone(m.backend)
        self.assertTrue(m.offline)
        self.assertEqual(m.recall("anything"), [])
        self.assertIsNone(m.store("User: x y z w | Assistant: ok"))
        self.assertIn("OFFLINE", m.status_line())


# ---------------------------------------------------------------------------
class FakeEmbedServer:
    """A local HTTP server speaking OpenAI /v1/embeddings and Ollama
    /api/embed (+ the old /api/embeddings)."""

    def __init__(self, dims=8, new_ollama=True, need_key=None):
        self.requests = []
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                outer.requests.append((self.path, body, dict(self.headers)))
                if need_key and self.headers.get("Authorization") != f"Bearer {need_key}":
                    return self._send(401, {"error": "bad key"})
                if self.path == "/v1/embeddings":
                    data = [{"index": i, "embedding": bag_vec(t, dims)} for i, t in enumerate(body["input"])]
                    return self._send(200, {"data": data, "model": body["model"]})
                if self.path == "/api/embed" and new_ollama:
                    return self._send(200, {"embeddings": [bag_vec(body["input"], dims)]})
                if self.path == "/api/embeddings":
                    return self._send(200, {"embedding": bag_vec(body["prompt"], dims)})
                return self._send(404, {"error": "not found"})

            def _send(self, code, obj):
                raw = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class TestEmbeddingProviders(unittest.TestCase):
    def server(self, **kw):
        s = FakeEmbedServer(**kw)
        self.addCleanup(s.close)
        return s

    def test_openai_compatible_local_server(self):
        srv = self.server(dims=8)
        es = dict(ltm.DEFAULTS["embedding"], provider="openai", url=srv.url + "/v1", model="nomic-embed-text",
                  dimensions=8, query_prefix="search_query: ", passage_prefix="search_document: ")
        e = ltm.make_embedder({"embedding": es, "backend": "local"})
        v = e.embed("hello cat", "query")
        self.assertEqual(len(v), 8)
        path, body, _ = srv.requests[-1]
        self.assertEqual(path, "/v1/embeddings")
        self.assertEqual(body["model"], "nomic-embed-text")
        self.assertEqual(body["input"], ["search_query: hello cat"])
        self.assertNotIn("dimensions", body)
        self.assertEqual(e.label, "openai:nomic-embed-text")

    def test_openai_compatible_key_from_env_and_dimension_check(self):
        srv = self.server(dims=8, need_key="sk-local")
        es = dict(ltm.DEFAULTS["embedding"], provider="openai", url=srv.url + "/v1/embeddings", model="m",
                  api_key_env="MY_EMBED_KEY", dimensions=16)
        e = ltm.make_embedder({"embedding": es})
        with mock.patch.dict(os.environ, {"MY_EMBED_KEY": "sk-local"}):
            with self.assertRaisesRegex(ltm.EmbedError, "returned 8 dimensions, settings say 16"):
                e.embed("x", "passage")
        with self.assertRaisesRegex(ltm.EmbedError, "401"):
            e.embed("x", "passage")                       # no key in env

    def test_ollama_native_and_old_api(self):
        for new in (True, False):
            srv = self.server(dims=6, new_ollama=new)
            es = dict(ltm.DEFAULTS["embedding"], provider="ollama", url=srv.url, model="nomic-embed-text")
            v = ltm.make_embedder({"embedding": es}).embed("cat", "query")
            self.assertEqual(len(v), 6)
            self.assertEqual(srv.requests[-1][0], "/api/embed" if new else "/api/embeddings")

    def test_unreachable_server_is_an_embed_error(self):
        es = dict(ltm.DEFAULTS["embedding"], provider="openai", url="http://127.0.0.1:9/v1", model="m",
                  timeout_sec=2)
        with self.assertRaises(ltm.EmbedError):
            ltm.make_embedder({"embedding": es}).embed("x", "query")

    def test_nvidia_hosted_uses_the_lab_client(self):
        calls = []

        class C:
            def embed(self, model, texts, input_type=None, url=None, timeout=None):
                calls.append((model, texts, input_type))
                return ModelResult(True, data=[[0.1, 0.2, 0.3]])
        e = ltm.make_embedder({"embedding": dict(ltm.DEFAULTS["embedding"], provider="nvidia")}, client=C())
        self.assertEqual(e.embed("hi", "query"), [0.1, 0.2, 0.3])
        self.assertEqual(calls[0], (ltm.DEFAULT_NV_EMBED, ["hi"], "query"))

    def test_sentence_transformers_in_process(self):
        loaded = []

        class Vec(list):
            def tolist(self):
                return list(self)

        class ST:
            def __init__(self, name, **kw):
                loaded.append((name, kw))

            def encode(self, texts, normalize_embeddings=False):
                return [Vec(bag_vec(texts[0], 4))]
        fake = types.ModuleType("sentence_transformers")
        fake.SentenceTransformer = ST
        with mock.patch.dict(sys.modules, {"sentence_transformers": fake}):
            e = ltm.make_embedder({"embedding": dict(ltm.DEFAULTS["embedding"], provider="sentence_transformers",
                                                     device="cpu")})
            self.assertEqual(len(e.embed("cat", "query")), 4)
            e.embed("dog", "query")
        self.assertEqual(loaded, [(ltm.DEFAULT_ST_MODEL, {"device": "cpu"})])   # loaded once

    def test_sentence_transformers_missing_is_reported(self):
        with mock.patch.dict(sys.modules, {"sentence_transformers": None}):
            e = ltm.make_embedder({"embedding": dict(ltm.DEFAULTS["embedding"], provider="sentence_transformers")})
            with self.assertRaisesRegex(ltm.EmbedError, "pip install sentence-transformers"):
                e.embed("x", "query")

    def test_local_backend_with_openai_server_end_to_end(self):
        srv = self.server(dims=8)
        d = tmpdir(self)
        m = MemoryCore(None, "", settings=lt(backend="local", local={"directory": d},
                                             embedding={"provider": "openai", "url": srv.url + "/v1",
                                                        "model": "bge"}))
        self.assertTrue(m.store("User: my cat is called Miso | Assistant: ok"))
        self.assertIn("Miso", m.recall("cat Miso", 1, 0.1)[0][1])
        self.assertEqual([r["embed_model"] for r in m.backend.records(0)], ["openai:bge"])
        ok = m.test()
        self.assertTrue(all(r[0] for r in ok), ok)
        self.assertTrue(any("8 dimensions" in r[1] for r in ok))

    def test_embedder_down_degrades_without_crash(self):
        m = MemoryCore(None, "", settings=lt(backend="local", local={"directory": tmpdir(self)}),
                       embedder=FnEmbedder(fail=True))
        self.assertIsNone(m.store("User: I like jazz | Assistant: ok"))
        self.assertEqual(m.recall("jazz"), [])
        self.assertTrue(any("embedding failed" in w for w in m.warnings))
        self.assertFalse(m.test()[-1][0])


# ---------------------------------------------------------------------------
class FakeOracleDB:
    """Python-dict stand-in for the database. Understands exactly the
    statements OracleBackend sends (tagged /* ltm:... */), checks the binds,
    and records every statement so tests can check what touched what."""

    def __init__(self, profiles=None, onnx_models=(), onnx_dims=4, existing_tables=()):
        self.tables = set(existing_tables)     # "MEM.TESTBED_MEMORIES"
        self.indexes = set()
        self.rows = {}                          # id -> dict
        self.meta = {}
        self.profiles = dict(profiles or {})    # agent_id -> (platform, tool_name)
        self.onnx_models = list(onnx_models)
        self.onnx_dims = onnx_dims
        self.sql = []
        self.commits = 0
        self.connects = []
        self.down = False
        self.oracle_text = False                # v3.7.1: is CTXSYS (Oracle Text) available?
        self.text_indexes = set()
        self.keyword_calls = []

    def connect(self, creds, timeout):
        if self.down:
            raise ltm.MemoryOffline("could not connect: DPY-6005: cannot connect to database")
        self.connects.append(dict(creds))
        return FakeConn(self)

    def onnx_embed(self, text):
        return bag_vec(text, self.onnx_dims)


class FakeConn:
    def __init__(self, db):
        self.db = db

    def cursor(self):
        return FakeCursor(self.db)

    def commit(self):
        self.db.commits += 1

    def close(self):
        pass


class OraErr:
    """Like oracledb's _Error: args[0] of the exception, with .code."""

    def __init__(self, code, message):
        self.code, self.message = code, message

    def __str__(self):
        return self.message


class OraError(Exception):
    pass


class FakeCursor:
    def __init__(self, db):
        self.db, self.rows, self.rowcount = db, [], 0

    def close(self):
        pass

    def fetchall(self):
        return self.rows

    def _vec(self, sql, binds, key):
        if "VECTOR_EMBEDDING(" in sql and not isinstance(binds.get(key), array.array):
            return self.db.onnx_embed(binds[key])
        v = binds[key]
        assert isinstance(v, array.array) and v.typecode == "f", "vectors must be bound as array('f')"
        return list(v)

    def execute(self, sql, binds=None):
        db, b = self.db, binds or {}
        db.sql.append((sql, dict(b)))
        tag = re.match(r"/\* ltm:(\w+) \*/", sql)
        assert tag, f"untagged SQL: {sql}"
        t = tag.group(1)
        tbl = re.search(r"(?:FROM|INTO|UPDATE|TABLE|ON) ([A-Z0-9_$#]+\.[A-Z0-9_$#]+)", sql)
        tbl = tbl.group(1) if tbl else None
        if t in ("insert", "search", "find_turn", "find_hash", "touch", "delete", "count", "incompatible",
                 "prune_age", "prune_max", "records", "meta_get", "meta_put", "by_kind") and tbl not in db.tables:
            raise OraError(OraErr(942, "ORA-00942: table or view does not exist"))
        if t == "tables":
            self.rows = [(n.split(".")[1],) for n in sorted(db.tables)
                         if n.split(".")[0] == b["o"] and n.split(".")[1] in (b["t1"], b["t2"])]
        elif t in ("create_mem", "create_meta"):
            assert tbl not in db.tables
            db.tables.add(tbl)
            if t == "create_mem":
                db.dims = int(re.search(r"VECTOR\((\d+), FLOAT32\)", sql).group(1))
        elif t == "create_idx":
            pass
        elif t == "create_vidx":
            db.indexes.add(re.search(r"VECTOR INDEX [A-Z0-9_]+\.([A-Z0-9_]+)", sql).group(1))
        elif t == "vidx_exists":
            self.rows = [(b["i"],)] if b["i"] in db.indexes else []
        elif t == "drop":
            db.tables.discard(tbl)
            if tbl.endswith("_MEMORIES"):
                db.rows.clear()
            else:
                db.meta.clear()
        elif t == "meta_get":
            self.rows = [(k, v) for (p, k), v in db.meta.items() if p == b["p"]]
        elif t == "meta_put":
            db.meta[(b["p"], b["k"])] = b["v"]
        elif t == "onnx_dims":
            self.rows = [(db.onnx_dims,)]
        elif t == "onnx_models":
            self.rows = [(m,) for m in db.onnx_models]
        elif t == "profile_get":
            assert tbl.endswith(".AGENT_PROFILES")
            self.rows = [db.profiles[b["a"]]] if b["a"] in db.profiles else []
        elif t == "profile_add":
            assert b["a"] not in db.profiles
            db.profiles[b["a"]] = (b["p"], None)
        elif t == "insert":
            vec = self._vec(sql, b, "v" if "v" in b else "t")
            assert len(vec) == db.dims, f"ORA-51803: vector dimension count {len(vec)} != {db.dims}"
            assert b["id"] not in db.rows
            json.loads(b["md"])
            db.rows[b["id"]] = {"id": b["id"], "p": b["p"], "kind": b["k"], "text": b["t"], "hash": b["h"],
                                "tk": b["tk"], "label": b["l"], "vec": vec, "hits": 1,
                                "created": len(db.sql), "seen": len(db.sql)}
        elif t == "search":
            assert "VECTOR_DISTANCE(embedding," in sql and "FETCH APPROX FIRST" in sql
            q = self._vec(sql, b, "q")
            k = int(re.search(r"FIRST (\d+) ROWS", sql).group(1))
            hits = []
            for r in db.rows.values():
                if r["p"] == b["p"] and r["label"] == b["l"]:
                    dot = sum(x * y for x, y in zip(q, r["vec"]))
                    n = math.sqrt(sum(x * x for x in q)) * math.sqrt(sum(y * y for y in r["vec"]))
                    hits.append((r["id"], r["text"], "2026-11-12T00:00:00", 1 - (dot / n if n else 0)))
            self.rows = sorted(hits, key=lambda h: h[3])[:k]
        elif t == "find_turn":
            self.rows = [(r["id"],) for r in db.rows.values() if r["p"] == b["p"] and r["tk"] == b["tk"]][:1]
        elif t == "find_hash":
            self.rows = [(r["id"],) for r in db.rows.values() if r["p"] == b["p"] and r["hash"] == b["h"]][:1]
        elif t == "touch":
            r = db.rows.get(b["id"])
            self.rowcount = 0
            if r and r["p"] == b["p"]:
                r["hits"] += 1
                r["seen"] = len(db.sql)
                self.rowcount = 1
        elif t == "delete":
            r = db.rows.get(b["id"])
            self.rowcount = 1 if r and r["p"] == b["p"] else 0
            if self.rowcount:
                del db.rows[b["id"]]
        elif t == "count":
            self.rows = [(sum(1 for r in db.rows.values() if r["p"] == b["p"]),)]
        elif t == "incompatible":
            self.rows = [(sum(1 for r in db.rows.values() if r["p"] == b["p"] and r["label"] != b["l"]),)]
        elif t == "prune_age":
            old = [i for i, r in db.rows.items() if r["p"] == b["p"] and r.get("old")]
            for i in old:
                del db.rows[i]
            self.rowcount = len(old)
        elif t == "prune_max":
            n = int(re.search(r"FIRST (\d+) ROWS", sql).group(1))
            mine = sorted((r for r in db.rows.values() if r["p"] == b["p"]), key=lambda r: r["seen"], reverse=True)
            for r in mine[n:]:
                del db.rows[r["id"]]
            self.rowcount = max(0, len(mine) - n)
        elif t == "records":
            mine = sorted((r for r in db.rows.values() if r["p"] == b["p"]), key=lambda r: r["created"],
                          reverse=True)
            self.rows = [(r["id"], "2026-11-12", r["text"], r["label"], len(r["vec"]), r["kind"]) for r in mine]
        elif t == "by_kind":
            mine = sorted((r for r in db.rows.values() if r["p"] == b["p"] and r["kind"] == b["k"]),
                          key=lambda r: r["created"], reverse=True)
            self.rows = [(r["id"], "2026-11-12", r["text"], None) for r in mine]
        elif t == "load_onnx":
            db.onnx_models.append(b["m"])
        elif t == "tidx_exists":
            self.rows = [(b["i"],)] if b["i"] in db.text_indexes else []
        elif t == "create_tidx":
            assert "INDEXTYPE IS CTXSYS.CONTEXT" in sql
            if not db.oracle_text:
                raise OraError(OraErr(29833, "ORA-29833: indextype does not exist"))
            db.text_indexes.add(re.search(r"INDEX [A-Z0-9_]+\.([A-Z0-9_]+)", sql).group(1))
        elif t in ("keyword_ctx", "keyword_instr"):
            if t == "keyword_ctx":
                assert "CONTAINS(text, :q, 1) > 0" in sql and db.text_indexes
                terms = [x.strip("{}") for x in b["q"].split(" OR ")]
            else:
                assert "DBMS_LOB.INSTR(LOWER(text)" in sql
                terms = [v for k2, v in b.items() if re.fullmatch(r"t\d+", k2)]
            db.keyword_calls.append(t)
            self.rows = [(r["id"], r["text"], "2026-11-12") for r in db.rows.values()
                         if r["p"] == b["p"] and any(x.lower() in r["text"].lower() for x in terms)]
        else:
            raise AssertionError(f"unexpected statement {t}")


CREDS = {"NIMLAB_ORACLE_USER": "MEM", "NIMLAB_ORACLE_PASSWORD": "s3cret-pw",
         "NIMLAB_ORACLE_DSN": "(description=(address=(protocol=tcps)(port=1522)(host=adb.us-phoenix-1.oraclecloud.com))"
                              "(connect_data=(service_name=g4f_svnbraindb_low.adb.oraclecloud.com)))"}


class OracleCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p = mock.patch.dict(os.environ, {"NIMLAB_DATA_DIR": d})
        p.start()
        self.addCleanup(p.stop)

    def backend(self, db=None, onnx=None, environ=None, **o):
        self.db = db or FakeOracleDB()
        oo = config.deep_merge(dict(ltm.DEFAULTS["oracle"]), o)
        oo["credentials_file"] = o.get("credentials_file", "")
        return ltm_oracle.OracleBackend(oo, embed_model=onnx, connect_fn=self.db.connect,
                                        environ=CREDS if environ is None else environ)

    def core(self, db=None, embedder=None, onnx=None, **o):
        b = self.backend(db, onnx=onnx, **o)
        s = lt(backend="oracle", embedding={"provider": "oracle" if onnx else "role"},
               oracle=dict(o, onnx_model=onnx or ""))
        emb = ltm.InDatabaseEmbedder(onnx) if onnx else (embedder or FnEmbedder())
        return MemoryCore(None, "x", settings=s, backend=b, embedder=emb)


class TestOracleBackend(BackendContract, OracleCase):
    def make(self, **kw):
        return self.core()

    def test_setup_creates_own_tables_vector_index_and_profile_in_mem(self):
        db = FakeOracleDB(profiles={"CHARLIE": ("Sesame", "charlie_mem"), "MAYA": ("Sesame", "maya_mem")})
        m = self.core(db)
        done = m.setup()
        self.assertEqual(db.tables, {"MEM.TESTBED_MEMORIES", "MEM.TESTBED_META"})
        self.assertEqual(db.indexes, {"TESTBED_MEMORIES_VIDX"})
        self.assertEqual(db.dims, 8)
        ddl = " ".join(s for s, _ in db.sql)
        self.assertIn("embedding VECTOR(8, FLOAT32) NOT NULL", ddl)
        self.assertIn("CREATE VECTOR INDEX MEM.TESTBED_MEMORIES_VIDX ON MEM.TESTBED_MEMORIES (embedding) "
                      "ORGANIZATION NEIGHBOR PARTITIONS DISTANCE COSINE WITH TARGET ACCURACY 90", ddl)
        self.assertEqual(db.profiles["TESTBED"], ("NIM testbed (nimlab)", None))
        self.assertEqual(db.profiles["CHARLIE"], ("Sesame", "charlie_mem"))
        self.assertTrue(any("registered profile TESTBED" in d for d in done))
        # a second setup changes nothing
        n = len(db.profiles)
        self.assertTrue(any("already set up" in d for d in m.setup()))
        self.assertEqual(len(db.profiles), n)

    def test_never_touches_the_other_agents_tables(self):
        m = self.core()
        m.store("User: my cat is Miso | Assistant: ok", turn_key="t")
        m.recall("cat")
        m.delete("x")
        m.settings["retention_days"] = 5
        m.prune()
        m.backend.test()
        for sql, _ in self.db.sql:
            for shared in ("MEM.MEMORIES", "MEM.ENTITIES", "MEM.MEMORY_SESSIONS", "MEM.MEMORY_ENTITY_LINKS",
                           "MEM.MEM_GUIDES", "SVN."):
                self.assertNotIn(shared + " ", sql + " ")
            if "AGENT_PROFILES" in sql:
                self.assertRegex(sql, r"ltm:profile_(get|add)")
        for sql, b in self.db.sql:
            if re.search(r"ltm:(search|count|records|find_\w+|touch|delete|prune_\w+|incompatible)", sql):
                self.assertIn("profile_id = :p", sql)
                self.assertEqual(b["p"], "TESTBED")

    def test_hnsw_and_no_index_options(self):
        m = self.core(index="hnsw", distance="DOT", target_accuracy=95)
        m.setup()
        ddl = " ".join(s for s, _ in self.db.sql)
        self.assertIn("ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE DOT WITH TARGET ACCURACY 95", ddl)
        m2 = self.core(index="none")
        m2.setup()
        self.assertEqual(self.db.indexes, set())

    def test_refuses_svn_reserved_prefixes_and_taken_profile(self):
        for o in ({"schema": "SVN"}, {"schema": "ADMIN"}, {"table_prefix": "MEM_GUIDES"},
                  {"table_prefix": "MEMORIES"}, {"profile_id": "x; drop table"}):
            with self.assertRaises(ltm.MemoryOffline, msg=o):
                self.backend(**o)
        db = FakeOracleDB(profiles={"CHARLIE": ("Sesame", "charlie_mem")})
        m = self.core(db, profile_id="CHARLIE")
        with self.assertRaisesRegex(ltm.MemoryOffline, "belongs to another agent"):
            m.setup()
        self.assertEqual(db.profiles["CHARLIE"], ("Sesame", "charlie_mem"))

    def test_own_schema_option(self):
        m = self.core(schema="NIMLAB", table_prefix="LAB", register_profile=False)
        m.setup()
        self.assertEqual(self.db.tables, {"NIMLAB.LAB_MEMORIES", "NIMLAB.LAB_META"})
        self.assertEqual(self.db.profiles, {})

    def test_vectors_bound_as_float32_arrays_and_search_uses_vector_distance(self):
        m = self.core()
        m.store("User: my cat is called Miso | Assistant: ok")
        ins = [(s, b) for s, b in self.db.sql if "ltm:insert" in s][0]
        self.assertIsInstance(ins[1]["v"], array.array)
        self.assertIn("JSON(:md)", ins[0])
        m.recall("cat Miso", top_k=3, threshold=0.2)
        q = [s for s, _ in self.db.sql if "ltm:search" in s][0]
        self.assertIn("VECTOR_DISTANCE(embedding, :q, COSINE)", q)
        self.assertIn("FETCH APPROX FIRST 3 ROWS ONLY WITH TARGET ACCURACY 90", q)

    def test_dimension_mismatch_is_refused_not_crashed(self):
        db = FakeOracleDB()
        self.core(db).setup()
        m = self.core(db, embedder=FnEmbedder(label="fake:bag", fn=lambda t: bag_vec(t, 16)))
        with self.assertRaisesRegex(ltm.MemoryOffline, "8-dimension vectors but the embedder gives 16"):
            m.setup()
        self.assertIsNone(m.store("User: hello there pal | Assistant: ok"))
        self.assertEqual(m.recall("hello"), [])

    def test_in_database_embedding_with_onnx_model(self):
        db = FakeOracleDB(onnx_models=["ALL_MINILM_L12_V2"], onnx_dims=8)
        m = self.core(db, onnx="ALL_MINILM_L12_V2")
        rid = m.store("User: my cat is called Miso | Assistant: ok")
        self.assertTrue(rid)
        ins = [(s, b) for s, b in db.sql if "ltm:insert" in s][0]
        self.assertIn("VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :t AS data)", ins[0])
        self.assertNotIn("v", ins[1])                     # no vector left this process
        hits = m.recall("cat Miso", 1, 0.1)
        self.assertEqual(hits[0][3], rid)
        q = [s for s, _ in db.sql if "ltm:search" in s][-1]
        self.assertIn("VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING(ALL_MINILM_L12_V2 USING :q AS data), COSINE)", q)
        res = m.test()
        self.assertTrue(all(ok for ok, _ in res), res)
        self.assertTrue(any("loaded" in msg for _, msg in res))

    def test_missing_onnx_model_reported_by_test(self):
        db = FakeOracleDB(onnx_models=[])
        res = self.core(db, onnx="NOPE").test()
        self.assertTrue(any(not ok and "NOT FOUND" in msg for ok, msg in res))

    def test_load_onnx_from_object_storage(self):
        b = self.backend()
        self.assertEqual(b.load_onnx_cloud("all_minilm_l12_v2", "https://objectstorage/x.onnx"), "ALL_MINILM_L12_V2")
        s = [s for s, _ in self.db.sql if "ltm:load_onnx" in s][0]
        self.assertIn("DBMS_VECTOR.LOAD_ONNX_MODEL_CLOUD", s)

    def test_retention_days_sql(self):
        m = self.core()
        m.store("User: old boats fact | Assistant: ok")
        list(self.db.rows.values())[0]["old"] = True
        m.store("User: new trains fact | Assistant: ok")
        m.settings["retention_days"] = 30
        self.assertEqual(m.prune(), 1)
        s, b = [(s, b) for s, b in self.db.sql if "ltm:prune_age" in s][0]
        self.assertIn("NUMTODSINTERVAL(:d, 'DAY')", s)
        self.assertEqual(b["d"], 30.0)


class TestOracleConnection(OracleCase):
    def test_missing_credentials_degrade_to_no_memory(self):
        s = lt(backend="oracle", oracle={"credentials_file": ""})
        with mock.patch.dict(os.environ, {}, clear=True):
            m = MemoryCore(None, "x", settings=s, embedder=FnEmbedder())
        self.assertIsNone(m.backend)
        self.assertIn("NIMLAB_ORACLE_PASSWORD", m.offline)
        self.assertEqual(m.recall("x"), [])
        self.assertIsNone(m.store("User: I like jazz | Assistant: ok"))

    def test_credentials_file_env_override_and_permissions_note(self):
        d = tmpdir(self)
        p = os.path.join(d, "oracle_mem.json")
        json.dump({"user": "MEM", "password": "from-file", "dsn": "svnbraindb_low", "wallet_dir": "~/wallet"},
                  open(p, "w"))
        os.chmod(p, 0o644)
        creds, notes = ltm_oracle.load_credentials({"credentials_file": p}, environ={"NIMLAB_ORACLE_DSN": "envdsn"})
        self.assertEqual(creds["password"], "from-file")
        self.assertEqual(creds["dsn"], "envdsn")
        self.assertEqual(creds["wallet_dir"], os.path.expanduser("~/wallet"))
        self.assertTrue(notes and "chmod 600" in notes[0])
        os.chmod(p, 0o600)
        self.assertEqual(ltm_oracle.load_credentials({"credentials_file": p}, environ={})[1], [])

    def test_thin_mode_connect_args_and_password_never_in_errors(self):
        seen = {}

        class FakeOracledb(types.ModuleType):
            def connect(self, **kw):
                seen.update(kw)
                raise RuntimeError("DPY-4011: password s3cret-pw rejected")
        mod = FakeOracledb("oracledb")
        creds = {"user": "MEM", "password": "s3cret-pw", "dsn": "svnbraindb_low", "wallet_dir": "/w",
                 "wallet_password": "wpw"}
        with mock.patch.dict(sys.modules, {"oracledb": mod}):
            with self.assertRaises(ltm.MemoryOffline) as cm:
                ltm_oracle.default_connect(creds, timeout=7)
        self.assertNotIn("s3cret-pw", str(cm.exception))
        self.assertIn("***", str(cm.exception))
        self.assertEqual(seen["wallet_location"], "/w")
        self.assertEqual(seen["config_dir"], "/w")
        self.assertEqual(seen["tcp_connect_timeout"], 7.0)
        self.assertEqual(seen["wallet_password"], "wpw")

    def test_unreachable_database_degrades_and_retries_later(self):
        db = FakeOracleDB()
        db.down = True
        s = lt(backend="oracle", retry_after_sec=60)
        with mock.patch.object(ltm_oracle, "default_connect", db.connect), \
                mock.patch.dict(os.environ, CREDS), mock.patch.object(ltm, "now_monotonic", return_value=0.0) as clock:
            m = MemoryCore(None, "x", settings=dict(s, long_term=dict(s["long_term"], oracle=dict(
                s["long_term"]["oracle"], credentials_file=""))), embedder=FnEmbedder())
            self.assertIsNone(m.backend)
            self.assertEqual(m.recall("cat"), [])
            self.assertEqual(len([w for w in m.warnings if "unavailable" in w]), 1)   # warned once
            db.down = False
            clock.return_value = 30.0
            self.assertEqual(m.recall("cat"), [])
            self.assertIsNone(m.backend)                                           # not yet retried
            clock.return_value = 61.0
            self.assertTrue(m.store("User: my cat is called Miso | Assistant: ok"))  # reconnected
            self.assertIsNotNone(m.backend)
            self.assertEqual(db.tables, {"MEM.TESTBED_MEMORIES", "MEM.TESTBED_META"})  # set up on first store

    def test_database_error_mid_session_degrades(self):
        m = self.core()
        m.store("User: my cat is called Miso | Assistant: ok")
        self.db.tables.clear()                             # someone dropped the tables
        self.assertEqual(m.recall("cat Miso", 1, 0.1), [])
        self.assertIsNone(m.backend)
        self.assertIn("ORA-00942", m.offline)


# ---------------------------------------------------------------------------
class TestSettingsCommands(unittest.TestCase):
    def setUp(self):
        d = tmpdir(self)
        self.cfg = os.path.join(d, "config_cluster.json")
        json.dump({"memory_settings": {"recall_top_k": 3}}, open(self.cfg, "w"))
        p = mock.patch.object(config, "CLUSTER_CONFIG", self.cfg)
        p.start()
        self.addCleanup(p.stop)

    def run_cli(self, action, *values):
        buf = StringIO()
        with redirect_stdout(buf), mock.patch.object(config, "load_cluster_config",
                                                     lambda path=None: json.load(open(self.cfg))):
            rc = memmenu.cmd_memory(Namespace(action=action, values=list(values)))
        return rc, buf.getvalue()

    def saved(self):
        return json.load(open(self.cfg))["memory_settings"]

    def test_use_backends_and_embedders(self):
        self.assertEqual(self.run_cli("use", "local", "/sdcard/nim-mem")[0], 0)
        lt_ = self.saved()["long_term"]
        self.assertEqual((lt_["backend"], lt_["local"]["directory"]), ("local", "/sdcard/nim-mem"))
        self.run_cli("embed", "openai", "http://127.0.0.1:11434/v1", "nomic-embed-text", "768")
        e = self.saved()["long_term"]["embedding"]
        self.assertEqual((e["provider"], e["url"], e["model"], e["dimensions"]),
                         ("openai", "http://127.0.0.1:11434/v1", "nomic-embed-text", 768))
        self.run_cli("use", "oracle")
        o = self.saved()["long_term"]["oracle"]
        self.assertEqual((o["schema"], o["table_prefix"], o["profile_id"]), ("MEM", "TESTBED", "TESTBED"))
        self.run_cli("embed", "oracle", "all_minilm_l12_v2")
        self.assertEqual(self.saved()["long_term"]["oracle"]["onnx_model"], "ALL_MINILM_L12_V2")
        self.assertEqual(self.saved()["recall_top_k"], 3)            # other memory settings kept

    def test_set_values_ranges_and_refusals(self):
        self.assertEqual(self.run_cli("set", "k", "5")[0], 0)
        self.assertEqual(self.saved()["recall_top_k"], 5)
        self.run_cli("set", "threshold", "0.6")
        self.assertEqual(self.saved()["similarity_threshold"], 0.6)
        self.run_cli("set", "retention_days", "90")
        self.run_cli("set", "auto_store", "off")
        self.run_cli("set", "dedupe", "semantic")
        lt_ = self.saved()["long_term"]
        self.assertEqual((lt_["retention_days"], lt_["auto_store"], lt_["dedupe"]), (90.0, False, "semantic"))
        for bad in (("oracle.password", "x"), ("oracle.schema", "SVN"), ("backend", "mongo"), ("nope", "1"),
                    ("oracle.dsn", "user/password@host")):
            rc, out = self.run_cli("set", *bad)
            self.assertEqual(rc, 2, bad)
            self.assertIn("Not changed", out)
        self.assertNotIn("password", json.dumps(self.saved()))

    def test_serve_settings_memory_key(self):
        from nimlab import servemenu
        buf = StringIO()
        with redirect_stdout(buf), mock.patch.object(config, "load_cluster_config",
                                                     lambda path=None: json.load(open(self.cfg))), \
                mock.patch.object(servemenu.S, "load_settings", lambda: {}):
            rc = servemenu.cmd_serve(Namespace(action="settings", values=["memory.backend", "local"], port=None, lan=None,
                                                     no_log=False, save=False))
            rc2 = servemenu.cmd_serve(Namespace(action="settings", values=["memory", "k", "4"], port=None, lan=None,
                                                      no_log=False, save=False))
        self.assertEqual((rc, rc2), (0, 0))
        self.assertEqual(self.saved()["long_term"]["backend"], "local")
        self.assertEqual(self.saved()["recall_top_k"], 4)

    def test_sql_preview_and_creds_init(self):
        rc, out = self.run_cli("sql", "384")
        self.assertEqual(rc, 0)
        self.assertIn("CREATE TABLE MEM.TESTBED_MEMORIES", out)
        self.assertIn("VECTOR(384, FLOAT32)", out)
        self.assertIn("CREATE VECTOR INDEX MEM.TESTBED_MEMORIES_VIDX", out)
        p = os.path.join(tmpdir(self), "sub", "oracle_mem.json")
        self.run_cli("set", "oracle.credentials_file", p)
        rc, out = self.run_cli("creds", "init")
        self.assertTrue(os.path.isfile(p))
        self.assertEqual(os.stat(p).st_mode & 0o777, 0o600)
        self.assertIn("already exists", self.run_cli("creds", "init")[1])

    def test_local_test_and_list_via_cli(self):
        d = tmpdir(self)
        self.run_cli("use", "local", d)
        with mock.patch.object(memmenu, "_mem", lambda cl, ms: MemoryCore(None, "x", settings=ms,
                                                                          embedder=FnEmbedder())):
            rc, out = self.run_cli("test")
            self.assertEqual(rc, 0, out)
            self.assertIn("[ok]", out)
            self.assertIn("8 dimensions", out)
            rc, out = self.run_cli("setup")
            self.assertIn("needs no setup", out)

    def test_menu_changes_settings(self):
        cluster = {"memory_settings": {"recall_top_k": 3}}
        answers = iter(["1", "local", "2", "/tmp/mem-dir", "5", "off", "7", "facts", "9", "6", "0.5", "12", "10", "30",
                        "500", "4", "ollama", "mxbai-embed-large", "", "0"])
        saves = []
        memmenu.run_menu(cluster, input_fn=lambda p="": next(answers), out=lambda *a: None,
                         save_fn=lambda: saves.append(1))
        ms = cluster["memory_settings"]
        lt_ = ms["long_term"]
        self.assertEqual(lt_["backend"], "local")
        self.assertEqual(lt_["local"]["directory"], "/tmp/mem-dir")
        self.assertFalse(lt_["auto_store"])
        self.assertEqual(lt_["store_mode"], "facts")
        self.assertEqual((ms["recall_top_k"], ms["similarity_threshold"]), (6, 0.5))
        self.assertEqual(ms["rerank_candidates"], 12)
        self.assertEqual((lt_["retention_days"], lt_["max_records"]), (30.0, 500))
        self.assertEqual((lt_["embedding"]["provider"], lt_["embedding"]["model"]), ("ollama", "mxbai-embed-large"))
        self.assertTrue(saves)


# ---------------------------------------------------------------------------
class TestEntityAcrossSessions(unittest.TestCase):
    """The unified entity stores after an exchange and recalls in a later
    session, through the settings in memory_settings.long_term."""

    def test_entity_remembers_across_sessions_with_local_backend(self):
        from nimlab.entity import Entity
        d = tmpdir(self)
        ms = {"recall_top_k": 3, "similarity_threshold": 0.2, "long_term": {"backend": "local",
                                                                             "local": {"directory": d}}}
        cluster = config.deep_merge(config.DEFAULT_CLUSTER, {"memory_settings": ms})

        def session():
            ent = Entity(cluster=cluster, prompts={}, soul="soul", client=None, memory=False, log=lambda *a: None)
            ent.memory = MemoryCore(None, "", settings=cluster["memory_settings"], embedder=FnEmbedder())
            return ent
        e1 = session()
        self.assertEqual(e1.memory.remember("my cat is called Miso", "Lovely name.", turn_key="t1").__len__(), 1)
        e2 = session()                                     # a new process later
        hits, _info = e2._recall("what is my cat called, Miso?") if hasattr(e2, "_recall") else (
            e2.memory.recall("cat Miso", 3, 0.2), {})
        self.assertTrue(hits)
        self.assertIn("Miso", hits[0][1])

    def test_auto_recall_off(self):
        from nimlab.entity import Entity
        cluster = config.deep_merge(config.DEFAULT_CLUSTER, {"memory_settings": {"long_term": {
            "backend": "local", "local": {"directory": tmpdir(self)}, "auto_recall": False}}})
        ent = Entity(cluster=cluster, prompts={}, soul="soul", client=None, memory=False, log=lambda *a: None)
        ent.memory = MemoryCore(None, "", settings=cluster["memory_settings"], embedder=FnEmbedder())
        ent.memory.store("User: my cat is called Miso | Assistant: ok")
        if hasattr(ent, "_recall"):
            self.assertEqual(ent._recall("cat Miso")[0], [])


class TestScope(unittest.TestCase):
    def test_user_scope_keeps_clients_apart_shared_does_not(self):
        for backend in ("json", "local"):
            d = tmpdir(self)
            kw = {"path": os.path.join(d, "m.json")} if backend == "json" else {}
            m = MemoryCore(None, "x", settings=lt(backend=backend, local={"directory": d}, scope="user"),
                           embedder=FnEmbedder(), **kw)
            with m.scoped("alice"):
                m.store("User: my cat is called Miso | Assistant: ok", turn_key="t1")
            with m.scoped("bob"):
                self.assertEqual(m.recall("cat Miso", 3, 0.1), [], backend)
                self.assertTrue(m.store("User: my cat is called Miso | Assistant: ok", turn_key="t1"))
            with m.scoped("alice"):
                self.assertEqual(len(m.recall("cat Miso", 3, 0.1)), 1)
            m.settings["scope"] = "shared"
            with m.scoped("bob"):
                self.assertEqual(len(m.recall("cat Miso", 3, 0.1)), 2, backend)

    def test_user_scope_sql_in_oracle(self):
        db = FakeOracleDB()
        b = ltm_oracle.OracleBackend(dict(ltm.DEFAULTS["oracle"], credentials_file=""), connect_fn=db.connect,
                                     environ=CREDS)
        m = MemoryCore(None, "x", settings=lt(backend="oracle", scope="user"), backend=b, embedder=FnEmbedder())
        with m.scoped("alice"):
            m.store("User: my cat is called Miso | Assistant: ok")
            m.recall("cat")
        ins = [b for s_, b in db.sql if "ltm:insert" in s_][0]
        self.assertEqual(ins["sc"], "alice")
        q = [s_ for s_, _ in db.sql if "ltm:search" in s_][-1]
        self.assertIn("AND (scope IS NULL OR scope = :sc)", q)
        self.assertIn("scope VARCHAR2(128)", " ".join(s_ for s_, _ in db.sql if "create_mem" in s_))


class TestServedEndpointMemory(unittest.TestCase):
    """Memory lives in the served endpoint: any client that connects gets
    the same memory, streaming or not, and it survives a server restart."""

    def setUp(self):
        from tests import test_entity as TE
        self.TE = TE
        self.case = TE.EntityCase("run")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.dir = tmpdir(self)
        self.case.ent.cluster.setdefault("memory_settings", {})["similarity_threshold"] = 0.2
        self.case.ent.memory = self.mem()

    def mem(self, **kw):
        return MemoryCore(None, "", settings=lt(backend="local", local={"directory": self.dir}, **kw),
                          embedder=FnEmbedder())

    def persona_prompt(self):
        return json.dumps(self.case.persona_msgs())

    def test_store_in_one_client_recall_in_another_streaming_and_after_restart(self):
        c = self.case
        j = c.ask("Remember that my cat is called Miso and she loves tuna")   # client A, plain request
        self.assertEqual(j["testbed"]["memory"]["stored"], 1)
        self.assertEqual(j["testbed"]["memory"]["backend"], "local")
        self.assertEqual(c.ent.memory.count(), 1)
        # client B, a streaming request with no history at all
        st, _, raw = c.call("/v1/chat/completions", {"model": "testbed", "stream": True, "messages": [
            {"role": "user", "content": "what does my cat Miso love to eat?"}]})
        self.assertEqual(st, 200)
        self.assertIn("Miso and she loves tuna", self.persona_prompt())
        events = [json.loads(l[6:]) for l in raw.decode().splitlines() if l.startswith("data: ") and l[6:] != "[DONE]"]
        mem_info = [e["testbed"]["memory"] for e in events if "testbed" in e]
        self.assertTrue(mem_info and mem_info[-1]["recalled"] >= 1, events[-2:])
        # restart: a new server process with the same settings
        c.srv.stop()
        c.ent.memory = self.mem()
        from nimlab import server as S
        s = S.load_settings()
        s["log_to_console"] = False
        c.srv = S.TestServer(c.ent, s, port=0, host="127.0.0.1", quiet=True)
        c.srv.start()
        c.base = c.srv.local_base()[:-3]
        c.key = s["api_key"]
        c.ask("tell me again what my cat Miso loves")
        self.assertIn("Miso and she loves tuna", self.persona_prompt())
        st, _, raw = c.call("/health")
        self.assertEqual(json.loads(raw)["memory"], {"backend": "local", "online": True})
        c.srv.stop()

    def test_responses_endpoint_shares_the_memory(self):
        c = self.case
        st, _, raw = c.call("/v1/responses", {"model": "testbed", "input": "I live in Pahrump, Nevada"})
        self.assertEqual(st, 200, raw)
        self.assertEqual(c.ent.memory.count(), 2)   # the turn + the pinned "Lives in" fact (3.8.0)
        c.ask("where do I live, Pahrump?")
        self.assertIn("I live in Pahrump, Nevada", self.persona_prompt())

    def test_user_field_and_header_separate_clients_when_scope_is_user(self):
        c = self.case
        c.ent.memory = self.mem(scope="user")
        j = c.ask("My favourite colour is teal", user="phone")
        self.assertEqual(j["testbed"]["memory"]["client"], "phone")
        st, _, raw = c.call("/v1/chat/completions", {"model": "testbed", "messages": [
            {"role": "user", "content": "what is my favourite colour teal?"}]}, headers={"X-Testbed-User": "laptop"})
        self.assertEqual(st, 200)
        self.assertNotIn("favourite colour is teal", self.persona_prompt())
        st, _, raw = c.call("/v1/chat/completions", {"model": "testbed", "messages": [
            {"role": "user", "content": "what is my favourite colour teal?"}]}, headers={"X-Testbed-User": "phone"})
        self.assertIn("favourite colour is teal", self.persona_prompt())

    def test_backend_down_still_answers(self):
        c = self.case
        f = os.path.join(self.dir, "not-a-dir")
        open(f, "w").close()
        c.ent.memory = MemoryCore(None, "", settings=lt(backend="local", local={"directory": f}),
                                  embedder=FnEmbedder())
        j = c.ask("Remember my cat is called Miso")
        self.assertTrue(j["choices"][0]["message"]["content"])
        self.assertFalse(j["testbed"]["memory"]["online"])
        self.assertIn("OFFLINE", c.srv.block())


if __name__ == "__main__":
    unittest.main()
