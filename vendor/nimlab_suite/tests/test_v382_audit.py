"""v3.8.2 audit items (the 4-AI review of 3.8.1): Telegram concurrency on
captured getUpdates fixtures, stale poller-lock reclaim, Alex's
cross-process memory contract, packaging, interrupt-mid-stream-then-restart,
and the doctor's lock / identity-pin checks."""
import json
import os
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
import zipfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nimlab import telegram as TG  # noqa: E402
from tests.sandbox import lab  # noqa: E402
from tests.test_telegram import FRIEND, OWNER, TOKEN, FakeBackend, FakeTelegram  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "telegram_getupdates.json")


def fixture():
    with open(FIXTURE) as f:
        return json.load(f)


class ReplayTelegram(FakeTelegram):
    """Answers getUpdates with the captured batches in order, ignoring the
    offset (Telegram re-sends what a restarted poller never confirmed)."""

    def __init__(self, batches, conflict=0):
        super().__init__()
        self.batches = [b["result"] for b in batches]
        self.conflict = conflict
        self.offsets = []

    def __call__(self, url, data, headers, timeout):
        if url.endswith("/getUpdates"):
            params = json.loads(data)
            self.calls.append(("getUpdates", params))
            self.offsets.append(params.get("offset"))
            if self.conflict:
                self.conflict -= 1
                return 409, json.dumps(fixture()["conflict"]).encode()
            res = self.batches.pop(0) if self.batches else []
            return 200, json.dumps({"ok": True, "result": res}).encode()
        return super().__call__(url, data, headers, timeout)


class TelegramFixtureTests(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self._lab.__enter__()
        self.addCleanup(self._lab.__exit__, None, None, None)
        self.logs = []

    def conn(self, api, backend):
        ts = {"allow": [str(OWNER), str(FRIEND)], "owner": str(OWNER), "mode": "polling", "refusal": "polite",
              "voice_replies": False, "username": "nimlab_bot", "admin_for_owner": True}
        return TG.Connector(TG.Bot(TOKEN, http=api), backend, ts, save=lambda: None,
                            convert=mock.Mock(return_value=b"x"), log=self.logs.append)

    @staticmethod
    def asked(backend):
        out = []
        for messages, _user, _admin in backend.chats:
            c = messages[-1]["content"]
            out.append(c if isinstance(c, str) else json.dumps(c))
        return out

    def expected(self):
        seen, out = set(), []
        f = fixture()
        for b in (f["batch_1"], f["batch_2"]):
            for u in b["result"]:
                if u["update_id"] not in seen:
                    seen.add(u["update_id"])
                    out.append(u["message"]["text"])
        return out

    def test_redelivered_updates_are_answered_once(self):
        f = fixture()
        api, be = ReplayTelegram([f["batch_1"], f["batch_2"]]), FakeBackend(reply="ok")
        c = self.conn(api, be)
        self.assertEqual(c.poll(once=True, sleep=lambda s: None), 0)
        self.assertEqual(c.poll(once=True, sleep=lambda s: None), 0)
        self.assertEqual(self.asked(be), self.expected())
        self.assertEqual(len(api.texts()), len(self.expected()))      # one reply per update
        self.assertEqual(c.offset, 815001206)

    def test_two_pollers_at_once_never_answer_an_update_twice(self):
        """Two pollers (a restart overlap, or setup's capture plus the bot) get
        the same captured batches at the same time: the shared ledger lets
        exactly one of them answer each update."""
        f = fixture()
        bes = [FakeBackend(reply="ok"), FakeBackend(reply="ok")]
        conns = [self.conn(ReplayTelegram([f["batch_1"], f["batch_2"]]), be) for be in bes]
        start = threading.Barrier(2)

        def run(c):
            start.wait()
            c.poll(once=True, sleep=lambda s: None)
            c.poll(once=True, sleep=lambda s: None)
        ts = [threading.Thread(target=run, args=(c,)) for c in conns]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        answered = self.asked(bes[0]) + self.asked(bes[1])
        self.assertEqual(sorted(answered), sorted(self.expected()))

    def test_a_restarted_poller_resumes_after_the_last_handled_update(self):
        f = fixture()
        c = self.conn(ReplayTelegram([f["batch_1"]]), FakeBackend(reply="ok"))
        c.poll(once=True, sleep=lambda s: None)
        api2 = ReplayTelegram([f["batch_2"]])
        be2 = FakeBackend(reply="ok")
        c2 = self.conn(api2, be2)                  # the new process after a restart
        c2.poll(once=True, sleep=lambda s: None)
        self.assertEqual(api2.offsets[0], 815001204)
        self.assertEqual(self.asked(be2), ["check the scheduler later", "how many tests passed last time"])

    def test_sustained_409_stops_instead_of_looping(self):
        api = ReplayTelegram([], conflict=50)
        sleeps = []
        c = self.conn(api, FakeBackend())
        rc = c.poll(sleep=sleeps.append, conflict_limit=TG.CONFLICT_LIMIT)
        self.assertEqual(rc, TG.EXIT_CONFIG)
        self.assertEqual(len(api.offsets), TG.CONFLICT_LIMIT)
        self.assertEqual(len(sleeps), TG.CONFLICT_LIMIT - 1)
        self.assertTrue(all(s <= 60 for s in sleeps))
        self.assertTrue(any("409" in ln for ln in self.logs))

    def test_a_single_409_recovers(self):
        f = fixture()
        api, be = ReplayTelegram([f["batch_1"]], conflict=1), FakeBackend(reply="ok")
        c = self.conn(api, be)
        stop = threading.Event()
        orig = be.chat

        def chat(*a, **k):
            r = orig(*a, **k)
            if len(be.chats) >= 3:
                stop.set()
            return r
        be.chat = chat
        self.assertEqual(c.poll(stop=stop, sleep=lambda s: None), 0)
        self.assertEqual(len(be.chats), 3)


# ---------------------------------------------------------------------------
# the poller lock: stale-lock reclaim, interrupt and restart
# ---------------------------------------------------------------------------
HOLDER = textwrap.dedent("""
    import os, sys, time
    sys.path.insert(0, {root!r})
    from nimlab import telegram as TG
    lock = TG.PollerLock({path!r})
    assert lock.acquire()
    if {fork!r}:
        pid = os.fork()
        if pid == 0:            # the leftover that inherited the lock
            time.sleep(60)
            os._exit(0)
        print(pid, flush=True)
        os._exit(0)             # the owner dies without releasing
    print(os.getpid(), flush=True)
    time.sleep(60)
""")

POLLER = textwrap.dedent("""
    import json, os, sys, threading, time, signal
    sys.path.insert(0, {root!r})
    os.environ["NIMLAB_DATA_DIR"] = {data!r}
    from nimlab import telegram as TG
    lock = TG.PollerLock({path!r})
    if not lock.acquire() and not lock.reclaim(log=print):
        print("busy", flush=True)
        sys.exit(3)

    def http(url, data, headers, timeout):
        if url.endswith("/getUpdates"):
            time.sleep(0.3)          # a long poll in progress
            return 200, json.dumps({{"ok": True, "result": []}}).encode()
        return 200, json.dumps({{"ok": True, "result": True}}).encode()

    class B:
        def chat(self, *a, **k):
            return "ok"
    conn = TG.Connector(TG.Bot("1:x", http=http), B(), {{"allow": []}}, save=lambda: None, log=lambda *a: None)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *a: stop.set())
    print("ready", os.getpid(), flush=True)
    try:
        conn.poll(stop=stop, timeout=1, sleep=time.sleep)
    except KeyboardInterrupt:
        pass
    finally:
        lock.release()
    print("stopped", flush=True)
""")


def _alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


@unittest.skipUnless(os.path.isdir("/proc/self/fd"), "needs /proc")
class PollerLockTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nimlab-lock-")
        self.path = os.path.join(self.dir, "poller.lock")
        self.kill = []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for pid in self.kill:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        import shutil
        shutil.rmtree(self.dir, True)

    def holder(self, fork, tag):
        code = HOLDER.format(root=ROOT, path=self.path, fork=fork)
        p = subprocess.Popen([sys.executable, "-c", code] + tag.split(), stdout=subprocess.PIPE, text=True)
        pid = int(p.stdout.readline())
        self.kill.append(pid)
        if fork:
            p.wait(10)
        else:
            self.kill.append(p.pid)
            self.proc = p
        return pid

    def test_dead_owner_with_no_leftover_is_just_free(self):
        with open(self.path, "w") as f:
            f.write("999999")                            # a crashed poller's pid
        lock = TG.PollerLock(self.path)
        self.assertEqual(lock.state()[0], "free")
        self.assertTrue(lock.reclaim(log=lambda *a: None))
        self.assertEqual(lock.named(), os.getpid())
        lock.release()

    def test_stale_lock_held_by_a_leftover_is_reclaimed(self):
        left = self.holder(True, "nimlab telegram run")
        lock = TG.PollerLock(self.path)
        st, owner, holders = lock.state()
        self.assertEqual(st, "stale")
        self.assertNotEqual(owner, left)
        self.assertIn(left, [p for p, _c in holders])
        logs = []
        self.assertTrue(lock.reclaim(log=logs.append, wait=5))
        self.assertIn("reclaimed a stale poller lock", " ".join(logs))
        self.assertEqual(lock.named(), os.getpid())
        time.sleep(0.3)
        self.assertFalse(_alive(left))
        lock.release()

    def test_a_live_poller_is_never_taken_over(self):
        pid = self.holder(False, "nimlab telegram run")
        lock = TG.PollerLock(self.path)
        self.assertEqual(lock.state()[:2], ("held", pid))
        self.assertFalse(lock.reclaim(log=lambda *a: None))
        self.assertTrue(_alive(pid))

    def test_a_leftover_that_is_not_nimlab_is_not_killed(self):
        left = self.holder(True, "some-other-tool")
        lock = TG.PollerLock(self.path)
        self.assertEqual(lock.state()[0], "stale")
        logs = []
        self.assertFalse(lock.reclaim(log=logs.append, wait=1))
        self.assertIn("won't stop", " ".join(logs))
        self.assertTrue(_alive(left))

    def test_doctor_reports_each_lock_state(self):
        from nimlab import doctor as D
        with mock.patch.object(TG, "lock_path", return_value=self.path), \
                mock.patch.object(TG, "load_token", return_value=""):
            self.assertEqual(D.telegram_checks()[0][0], True)            # free, no bot set up
            self.holder(True, "nimlab telegram run")
            st, msg = D.telegram_checks()[0]
            self.assertEqual(st, "warn")
            self.assertIn("stale", msg)
            for pid in list(self.kill):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            time.sleep(0.3)
            pid = self.holder(False, "nimlab telegram run")
            st, msg = D.telegram_checks()[0]
            self.assertEqual(st, True)
            self.assertIn(f"pid {pid}", msg)

    def test_interrupt_mid_poll_then_restart_leaves_one_poller(self):
        data = os.path.join(self.dir, "data")
        code = POLLER.format(root=ROOT, path=self.path, data=data)

        def start():
            p = subprocess.Popen([sys.executable, "-c", code, "nimlab", "telegram", "run"],
                                 stdout=subprocess.PIPE, text=True)
            self.kill.append(p.pid)
            line = p.stdout.readline().split()
            return p, line
        p1, line = start()
        self.assertEqual(line[0], "ready")
        p2, line2 = start()                                  # a second copy is refused
        self.assertEqual(line2, ["busy"])
        self.assertEqual(p2.wait(10), 3)
        time.sleep(0.4)                                      # inside a long poll
        p1.send_signal(signal.SIGINT)
        self.assertEqual(p1.wait(10), 0)
        self.assertEqual(p1.stdout.read().split(), ["stopped"])
        lock = TG.PollerLock(self.path)
        self.assertEqual(lock.state()[0], "free")             # released
        p3, line3 = start()                                  # the restart
        self.assertEqual(line3[0], "ready")
        st, pid, holders = lock.state()
        self.assertEqual((st, pid), ("held", p3.pid))
        self.assertEqual([p for p, _c in holders], [p3.pid])  # one poller
        p3.terminate()
        self.assertEqual(p3.wait(10), 0)


class InterruptStreamRestartTests(unittest.TestCase):
    """A client that hangs up in the middle of a streamed reply, then a
    server restart on the same port: one server, nothing left behind."""

    def setUp(self):
        from tests import test_server as TS
        from nimlab import server as S
        self.TS, self.S = TS, S
        cm = TS.fresh_store()
        cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        self.backend = TS.Backend()
        self.ent, _ = TS.make_entity(self, dict(TS.ROLES), self.backend.opener)
        self.settings = S.load_settings()
        self.settings["log_to_console"] = False

    def start(self, port=0):
        srv = self.S.TestServer(self.ent, self.settings, port=port, host="127.0.0.1").start()
        self.addCleanup(srv.stop)
        return srv

    def hang_up_mid_stream(self, port):
        body = json.dumps({"model": self.settings.get("agent_name") or "testbed", "stream": True,
                           "messages": [{"role": "user", "content": "tell me a long story " * 20}]}).encode()
        s = socket.create_connection(("127.0.0.1", port), timeout=10)
        s.sendall(b"POST /v1/chat/completions HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
                  + f"Authorization: Bearer {self.settings['api_key']}\r\nContent-Length: {len(body)}\r\n\r\n".encode()
                  + body)
        first = s.recv(64)
        s.close()                                            # gone before the stream ends
        return first

    def ok(self, base):
        import urllib.request
        req = urllib.request.Request(base + "/models", headers={"Authorization": "Bearer " + self.settings["api_key"]})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status

    def test_hang_up_then_restart(self):
        base_threads = threading.active_count()
        srv = self.start()
        port = srv.bound_port
        self.assertTrue(self.hang_up_mid_stream(port).startswith(b"HTTP/1."))
        self.assertEqual(self.ok(srv.local_base()), 200)     # still serving after the hang-up
        srv.stop()
        deadline = time.time() + 5
        while threading.active_count() > base_threads and time.time() < deadline:
            time.sleep(0.05)
        self.assertLessEqual(threading.active_count(), base_threads)     # no handler left running
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=1).close()   # the port is free
        srv2 = self.start(port)                              # restart on the same port
        self.assertEqual(srv2.bound_port, port)
        self.assertEqual(self.ok(srv2.local_base()), 200)
        with self.assertRaises(OSError):                     # and only one server can hold it
            self.start(port)


# ---------------------------------------------------------------------------
# Alex's cross-process memory contract
# ---------------------------------------------------------------------------
BOT = textwrap.dedent("""
    import sys, threading
    sys.path.insert(0, {root!r})
    from nimlab.memory import MemoryCore
    from nimlab import environment as ENV
    from tests.test_ltm import FnEmbedder
    from tests.test_v382_audit import vec64
    from tests.test_v380_recall import LIVE_ROWS
    m = MemoryCore(None, 'x', settings={settings!r}, embedder=FnEmbedder(fn=vec64), path={path!r})
    for t in LIVE_ROWS[:7]:
        m.store(t, dedupe='off')

    def reply_then_save():      # the bot saves after the reply, off the poller thread
        with ENV.channel('telegram'):
            m.remember({intro!r}, 'Nice to meet you!')
            m.remember('I keep my bike in the garage downstairs', 'Noted, the garage.')
    t = threading.Thread(target=reply_then_save)
    t.start(); t.join()
    print('saved')
""")


def vec64(text):
    """bag_vec with room enough that unrelated words rarely collide."""
    from tests.test_ltm import bag_vec
    return bag_vec(text, 64)


class MemoryContract:
    """An identity fact and an ordinary memory written by the Telegram bot's
    background save in another process; read by the terminal path, which
    opened the store first. Presence, ranking and the pin."""

    def settings_path(self):
        raise NotImplementedError

    def bot(self, intro="My name is SeVin."):
        settings, path = self.settings_path()
        r = subprocess.run([sys.executable, "-c", BOT.format(root=ROOT, settings=settings, path=path, intro=intro)],
                           cwd=ROOT, capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split()[-1], "saved")

    def terminal(self):
        from nimlab.memory import MemoryCore
        from tests.test_ltm import FnEmbedder
        settings, path = self.settings_path()
        return MemoryCore(None, "x", settings=settings, embedder=FnEmbedder(fn=vec64), path=path)

    def test_contract(self):
        term = self.terminal()
        self.assertEqual(term.count(), 0)              # opened before the bot wrote
        self.bot()
        # presence: the pinned fact and the ordinary memory are both there
        self.assertEqual(term.identity_facts(), {"name": "SeVin"})
        self.assertIn("Name: SeVin", term.identity_block())
        # ranking: the garage memory comes first for a question about it
        hits = term.recall("where do I keep my bike", 6, 0.0)
        self.assertTrue(hits)
        self.assertIn("garage", hits[0][1])
        # the pin is not left to ranking: it is there for an unrelated question
        self.assertIn("Name: SeVin", term.identity_block())
        hits = term.recall("what about the tunnel on my phone", 6, 0.0)
        self.assertIn("tunnel", hits[0][1])

    def test_a_new_name_from_the_bot_replaces_the_pin(self):
        term = self.terminal()
        self.bot()
        self.assertEqual(term.identity_facts(), {"name": "SeVin"})
        self.bot("Call me Vin from now on. My name is Vin.")
        self.assertEqual(term.identity_facts(), {"name": "Vin"})   # one name, the newest


class TestJsonContract(MemoryContract, unittest.TestCase):
    def settings_path(self):
        from tests.test_ltm import lt, tmpdir
        if not hasattr(self, "_sp"):
            self._sp = (lt(backend="json"), os.path.join(tmpdir(self), "memory.json"))
        return self._sp


class TestLocalContract(MemoryContract, unittest.TestCase):
    def settings_path(self):
        from tests.test_ltm import lt, tmpdir
        if not hasattr(self, "_sp"):
            self._sp = (lt(backend="local", local={"directory": os.path.join(tmpdir(self), "mem")}), None)
        return self._sp


class DoctorMemoryTests(unittest.TestCase):
    def test_identity_pin_round_trip_cleans_up(self):
        from tests.test_ltm import FnEmbedder, bag_vec, lt, tmpdir
        from nimlab.memory import MemoryCore
        m = MemoryCore(None, "x", settings=lt(backend="local", local={"directory": os.path.join(tmpdir(self), "m")}),
                       embedder=FnEmbedder(fn=bag_vec))
        m.pin_identity("name", "SeVin")
        before = m.count()
        res = m.roundtrip_identity()
        self.assertEqual(res[0][0], True, res)
        self.assertEqual(m.count(), before)                   # the test fact is gone again
        self.assertEqual(m.identity_facts(), {"name": "SeVin"})   # the real one is untouched

    def test_doctor_quick_covers_lock_pin_and_scheduler(self):
        from nimlab import doctor as D
        for s in ("identity", "telegram", "scheduler", "processes"):
            self.assertIn(s, D.QUICK)
        self.assertIn("memory", [k for k, *_ in D.SECTIONS])


# ---------------------------------------------------------------------------
# packaging
# ---------------------------------------------------------------------------
class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import build_zip
        cls.bz = build_zip
        cls.tmp = tempfile.mkdtemp(prefix="nimlab-zip-")
        cls.zip, cls.n = build_zip.build(os.path.join(cls.tmp, "nimlab.zip"))

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, True)

    def names(self):
        with zipfile.ZipFile(self.zip) as z:
            return z.namelist()

    def test_scripts_are_executable_in_the_tree_and_the_zip(self):
        for name in ("start.sh", "update.sh"):
            self.assertTrue(os.stat(os.path.join(ROOT, name)).st_mode & stat.S_IXUSR, name)
        with zipfile.ZipFile(self.zip) as z:
            for name in ("start.sh", "update.sh"):
                mode = (z.getinfo("nvidia_nim_test_lab/" + name).external_attr >> 16) & 0o777
                self.assertEqual(mode, 0o755, name)

    def test_no_runtime_data_or_dev_leftovers(self):
        for n in self.names():
            self.assertTrue(n.startswith("nvidia_nim_test_lab/"), n)
            rel = n.split("/", 1)[1]
            top = rel.split("/")[0]
            self.assertNotIn(top, ("data", "output", ".git", "logs", "backups"), n)
            for bad in ("__pycache__", ".pytest_cache", ".venv"):
                self.assertNotIn(bad, n.split("/"), n)
            self.assertFalse(n.endswith((".pyc", ".pyo", ".orig", ".rej", ".zip")), n)
            self.assertNotIn("secrets.json", n)
            self.assertNotIn("{marker}", n)

    def test_has_what_a_fresh_install_needs(self):
        names = set(self.names())
        for rel in ("start.sh", "update.sh", "README.md", "CHANGES.md", "requirements.txt", "soul.md",
                    "nimlab/__init__.py", "nimlab/__main__.py", "nimlab/updater.py", "nimlab/endpoints.py",
                    "tests/fixtures/telegram_getupdates.json"):
            self.assertIn("nvidia_nim_test_lab/" + rel, names)

    def test_no_real_keys_inside(self):
        import re
        pat = re.compile(rb"nvapi-[A-Za-z0-9_-]{50,}|\d{8,10}:AA[A-Za-z0-9_-]{33}")
        with zipfile.ZipFile(self.zip) as z:
            for n in z.namelist():
                data = z.read(n)
                for m in pat.findall(data):
                    self.assertRegex(m.decode(errors="replace"), r"(x{20,}|X{20,}|0{20,}|A{30,})", n)

    @unittest.skipUnless(__import__("shutil").which("unzip"), "unzip not installed")
    def test_unzip_keeps_the_mode(self):
        out = os.path.join(self.tmp, "x")
        subprocess.run(["unzip", "-q", self.zip, "-d", out], check=True)
        for name in ("start.sh", "update.sh"):
            self.assertTrue(os.access(os.path.join(out, "nvidia_nim_test_lab", name), os.X_OK), name)


if __name__ == "__main__":
    unittest.main()
