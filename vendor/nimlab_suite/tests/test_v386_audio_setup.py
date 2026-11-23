"""v3.8.6: register a phone for the audio bridge from the launcher / setup and
print a ready-to-paste Termux block (nimlab/audiosetup.py).

The block is run for real: by bash in a fake Termux (PREFIX/HOME in a temp
dir, stubbed pkg and termux-* commands, real curl and jq) against the real
audio bus HTTP handler, and once more pasted into an interactive bash on a
pty with history expansion on, as a paste from a phone's SSH app would be.
"""
import contextlib
import hashlib
import io
import os
import pty
import re
import select
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

import nimlab
from nimlab import audiobus as AB, audiosetup as AS, server as S, wizard
from test_v385_audiobus import Bus, FakeApp

HAVE_TOOLS = all(shutil.which(c) for c in ("bash", "curl", "jq", "sha256sum"))


class FakeIO:
    """wizard.IO with scripted answers (in order); records everything said."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.out = []

    def say(self, text=""):
        self.out.append(str(text))

    def ask(self, prompt, default=""):
        self.out.append(f"? {prompt} [{default}]")
        if not self.answers:
            raise AssertionError(f"unexpected question: {prompt}")
        v = self.answers.pop(0)
        return v if v != "" else str(default or "")

    def choose(self, prompt, options, default=None):
        self.out.append(f"? {prompt}")
        self.out.extend(f"  {k}) {label}" for k, label in options)
        v = self.ask("Choose", default)
        return v

    def yes(self, prompt, default=True):
        return self.ask(prompt + " (y/n)", "y" if default else "n").lower().startswith("y")

    def text(self):
        return "\n".join(self.out)


def block_of(text):
    m = re.search(r"^# ===== BEGIN NIMBRIDGE SETUP.*?^# ===== END NIMBRIDGE SETUP[^\n]*\n", text + "\n",
                  re.S | re.M)
    return m.group(0) if m else None


class Setup(Bus):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(AS, "default_url", lambda: "https://lab.example.com")
        p.start()
        self.addCleanup(p.stop)


class TestNamesAndClient(Setup):
    def test_names(self):
        self.assertEqual(AS.check_name(" Pixel8 "), "pixel8")
        for bad in ("", "all", "active", "has space", "../x", "-x", "a" * 40, "t\u00e9l"):
            with self.assertRaises(AS.SetupError, msg=bad):
                AS.check_name(bad)

    def test_urls(self):
        self.assertEqual(AS.clean_url(" https://lab.example.com/ "), "https://lab.example.com")
        self.assertEqual(AS.clean_url("https://lab.example.com/v1"), "https://lab.example.com")
        self.assertEqual(AS.clean_url("http://127.0.0.1:8765"), "http://127.0.0.1:8765")
        for bad in ("", "lab.example.com", "https://x.com/a b", "https://x.com/'$(id)'", "ftp://x"):
            with self.assertRaises(AS.SetupError, msg=bad):
                AS.clean_url(bad)

    def test_one_canonical_client(self):
        src = AS.client_source()
        self.assertTrue(src.startswith("#!/data/data/com.termux/files/usr/bin/bash\n"))
        self.assertEqual(AS.client_version(src), "1.1")
        self.assertIn("init) cmd_init ;;", src)
        tok = "nab_" + "x" * 40
        block = AS.termux_block("pixel", tok, "https://lab.example.com", "off")
        body = block.split("<<'NIMBRIDGE_EOF'\n", 1)[1].split("\nNIMBRIDGE_EOF\n", 1)[0] + "\n"
        self.assertEqual(body, src)                       # the block carries the file as it is
        self.assertIn(hashlib.sha256(src.encode()).hexdigest(), block)

    def test_client_checks(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        for bad in ("echo hi\nNIMBRIDGE_EOF\n", "echo\thi\n", "echo h\u00e9\n"):
            p = os.path.join(d, "c.sh")
            with open(p, "w", encoding="utf-8") as f:
                f.write(bad)
            with self.assertRaises(AS.SetupError):
                AS.client_source(p)

    def test_block_is_paste_safe(self):
        tok = AB.add_device("pixel")
        block = AS.termux_block("pixel", tok, "https://lab.example.com", "on")
        block.encode("ascii")
        self.assertNotIn("\t", block)
        self.assertNotIn("\r", block)
        self.assertNotIn("\x1b", block)
        lines = block.splitlines()
        self.assertTrue(lines[0].startswith("# ===== BEGIN NIMBRIDGE SETUP for phone 'pixel'"))
        self.assertTrue(lines[-1].startswith("# ===== END NIMBRIDGE SETUP for phone 'pixel'"))
        for want in ("pkg install -y curl jq termux-api </dev/null", "URL=https://lab.example.com",
                     "DEVICE=pixel", f"TOKEN={tok}", "MIC=on", 'chmod 600 "$HOME/.config/nimbridge/config"',
                     'chmod 755 "$PREFIX/bin/nimbridge"', 'bash "$PREFIX/bin/nimbridge" init'):
            self.assertIn(want, block)
        self.assertEqual(block.count(tok), 1)
        self.assertIn("MIC=off", AS.termux_block("pixel", tok, "https://lab.example.com", "off"))
        with self.assertRaises(AS.SetupError):
            AS.termux_block("pixel", "not-a-key", "https://lab.example.com", "off")


class TestFlow(Setup):
    def no_token_on_disk(self, tok):
        for root, _dirs, files in os.walk(self.dir):
            for f in files:
                with open(os.path.join(root, f), "rb") as fh:
                    self.assertNotIn(tok.encode(), fh.read(), f"token found in {f}")

    def test_new_phone(self):
        fio = FakeIO(["Pixel8", "y", "", "n"])   # name, mic, url (default), another?
        self.assertEqual(AS.flow(fio), ["pixel8"])
        out = fio.text()
        tok = re.search(r"^(nab_\S+)$", out, re.M).group(1)
        self.assertEqual(AB.auth_device(tok), "pixel8")
        block = block_of(out)
        self.assertIsNotNone(block)
        self.assertIn(f"TOKEN={tok}", block)
        self.assertIn("MIC=on", block)
        self.assertIn("URL=https://lab.example.com", block)
        self.assertIn("Paste this whole block into Termux on the phone you want audio to play through", out)
        self.assertIn("The block holds this phone's key", out)
        self.assertIn("allow the microphone", out)
        self.no_token_on_disk(tok)
        with open(os.path.join(AB.bus_dir(), "bridge.json")) as f:
            self.assertIn("lab.example.com", f.read())

    def test_bad_name_then_two_phones(self):
        fio = FakeIO(["all", "bad name", "pixel", "n", "", "y", "galaxy", "n", "n"])
        self.assertEqual(AS.flow(fio), ["pixel", "galaxy"])
        out = fio.text()
        self.assertIn("reserved word", out)
        self.assertIn("use 1-32 characters", out)
        self.assertEqual(len(re.findall(r"^# ===== BEGIN NIMBRIDGE SETUP", out, re.M)), 2)
        self.assertEqual(out.count("? Server address"), 1)     # asked once, reused for the next phone
        self.assertEqual({d["name"] for d in AB.devices()}, {"pixel", "galaxy"})

    def test_existing_name(self):
        old = AB.add_device("pixel", "Pixel 8")
        # reissue: the old key stops working, the label stays
        fio = FakeIO(["pixel", "reissue", "n", "", "n"])
        AS.flow(fio)
        self.assertIsNone(AB.auth_device(old))
        new = re.search(r"^(nab_\S+)$", fio.text(), re.M).group(1)
        self.assertEqual(AB.auth_device(new), "pixel")
        self.assertEqual(AB.devices()[0]["label"], "Pixel 8")
        self.assertIn("has a new key", fio.text())
        # pick another name
        fio = FakeIO(["pixel", "other", "tablet", "n", "", "n"])
        self.assertEqual(AS.flow(fio), ["tablet"])
        self.assertEqual(AB.auth_device(new), "pixel")
        # cancel: nothing changes
        fio = FakeIO(["pixel", "cancel", "n"])
        self.assertEqual(AS.flow(fio), [])
        self.assertEqual(AB.auth_device(new), "pixel")
        self.assertIn("No phone added.", fio.text())

    def test_empty_name_cancels(self):
        fio = FakeIO(["", "n"])
        self.assertEqual(AS.flow(fio), [])
        self.assertEqual(AB.devices(), [])

    def test_broken_client_registers_nothing(self):
        with mock.patch.object(AS, "client_source", side_effect=AS.SetupError("tabs")):
            with self.assertRaises(AS.SetupError):
                AS.register_one(FakeIO(["pixel", "n", ""]))
        self.assertEqual(AB.devices(), [])


class TestWizardAndCli(Setup):
    def test_wizard_step(self):
        w = wizard.Wizard(io=FakeIO([]), cli=lambda *a, **k: 0, sh=lambda *a, **k: 0)
        self.assertEqual(w.step_keys()[-1], "audio")
        self.assertEqual(w.step_keys()[:11], ["key", "discover", "functions", "sweep", "mcp", "roles", "grpc",
                                              "memory", "server", "telegram", "selfadmin"])
        self.assertEqual(wizard.ALIASES["phone"], "audio")
        self.assertEqual(w.st_audio(), (True, "no phones yet (optional)"))
        # default is skip: setup never pushes a phone on anyone
        fio = FakeIO([""])
        w.io = fio
        self.assertTrue(w.run_step(12, 12, "audio", "Phone audio bridge (optional)", w.st_audio, w.do_audio))
        self.assertEqual(AB.devices(), [])
        self.assertIn("Set up a phone for audio now", fio.text())
        # run: the flow loops by itself, no "Run this step again?" after it
        fio = FakeIO(["run", "pixel", "n", "", "n"])
        w.io = fio
        self.assertTrue(w.run_step(12, 12, "audio", "Phone audio bridge (optional)", w.st_audio, w.do_audio))
        self.assertNotIn("? Run this step again?", fio.text())
        self.assertIn("1 phone(s): pixel", fio.text())

    def test_cli_add_still_prints_token(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = AB.cmd_audio(type("A", (), {"action": "add", "name": "pixel", "label": "", "termux": False})())
        self.assertEqual(rc, 0)
        tok = re.search(r"^(nab_\S+)$", out.getvalue(), re.M).group(1)
        self.assertEqual(AB.auth_device(tok), "pixel")

    def test_cli_termux_flag(self):
        out, err = io.StringIO(), io.StringIO()
        args = type("A", (), {"action": "add", "name": "Pixel", "label": "", "termux": True, "mic": "on",
                              "url": "https://lab.example.com/"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(AB.cmd_audio(args), 0)
        self.assertEqual(block_of(out.getvalue()), out.getvalue())     # stdout is the block, nothing else
        tok = re.search(r"^TOKEN=(nab_\S+)$", out.getvalue(), re.M).group(1)
        self.assertEqual(AB.auth_device(tok), "pixel")
        self.assertIn("holds the phone's key", err.getvalue())
        args.name = "all"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(AB.cmd_audio(args), 1)

    def test_parser(self):
        import argparse
        p = argparse.ArgumentParser()
        AB.add_parser(p.add_subparsers(dest="cmd"))
        a = p.parse_args(["audio", "add", "pixel", "--termux", "--mic", "on"])
        self.assertTrue(a.termux)
        self.assertEqual(a.mic, "on")
        self.assertEqual(p.parse_args(["audio", "setup"]).action, "setup")
        self.assertFalse(p.parse_args(["audio", "add", "pixel"]).termux)

    def test_version_banner(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(nimlab.__file__)))
        with open(os.path.join(root, "start.sh")) as f:
            sh = f.read()
        self.assertIn('banner "NVIDIA NIM TEST LAB v$(nimlab_version)"', sh)
        fn = re.search(r"^nimlab_version\(\) \{.*?^\}", sh, re.S | re.M).group(0)
        r = subprocess.run(["bash", "-c", f'SCRIPT_DIR="{root}"\n{fn}\nnimlab_version'],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.stdout, nimlab.__version__)
        self.assertIn("nimlab audio setup", sh)


STUBS = {
    "pkg": 'echo "pkg $*" >> "$STUBLOG"\n',
    "nohup": 'exec bash "$@"\n',     # the client's shebang is Termux's bash; run it with this one
    "termux-media-player": 'echo "termux-media-player $*" >> "$STUBLOG"\necho "No track currently!"\n',
    "termux-microphone-record": 'echo "termux-microphone-record $*" >> "$STUBLOG"\n',
}
for _c in ("termux-wake-lock", "termux-wake-unlock", "termux-notification", "termux-notification-remove",
           "termux-toast"):
    STUBS[_c] = f'echo "{_c} $*" >> "$STUBLOG"\n'


@unittest.skipUnless(HAVE_TOOLS, "needs bash, curl, jq and sha256sum")
class TestBlockInFakeTermux(Bus):
    """The printed block, run in a fake Termux against the real bus handler."""

    def setUp(self):
        super().setUp()
        h = type("H", (S.Handler,), {"app": FakeApp()})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), h)
        self.srv.daemon_threads = True
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.prefix = os.path.join(self.dir, "usr")
        self.home = os.path.join(self.dir, "home")
        stub = os.path.join(self.dir, "stub")
        for d in (self.prefix + "/bin", self.home, stub):
            os.makedirs(d)
        for name, body in STUBS.items():
            p = os.path.join(stub, name)
            with open(p, "w") as f:
                f.write("#!/bin/bash\n" + body)
            os.chmod(p, 0o755)
        self.log = os.path.join(self.dir, "calls.log")
        self.env = {"PATH": f"{stub}:{self.prefix}/bin:/usr/bin:/bin", "PREFIX": self.prefix, "HOME": self.home,
                    "STUBLOG": self.log, "TERM": "dumb", "LANG": "C.UTF-8"}
        self.addCleanup(self.stop_bridge)

    def stop_bridge(self):
        nb = os.path.join(self.prefix, "bin", "nimbridge")
        if os.path.exists(nb):
            subprocess.run(["bash", nb, "stop"], env=self.env, capture_output=True, timeout=30)

    def check_result(self, tok, mic):
        nb = os.path.join(self.prefix, "bin", "nimbridge")
        with open(nb) as f:
            self.assertEqual(f.read(), AS.client_source())
        self.assertEqual(stat.S_IMODE(os.stat(nb).st_mode), 0o755)
        conf = os.path.join(self.home, ".config", "nimbridge", "config")
        self.assertEqual(stat.S_IMODE(os.stat(conf).st_mode), 0o600)
        with open(conf) as f:
            self.assertEqual(f.read(), f"URL={self.url}\nDEVICE=pixel\nTOKEN={tok}\nMIC={mic}\n")
        with open(self.log) as f:
            calls = f.read()
        self.assertIn("pkg install -y curl jq termux-api", calls)
        self.assertEqual("termux-microphone-record -f" in calls, mic == "on")   # Android's one-time ask
        for _ in range(50):
            if AB.device_state("pixel")["online"]:
                break
            time.sleep(0.1)
        self.assertTrue(AB.device_state("pixel")["online"], "the bus never saw the phone")
        self.assertEqual(AB.active(), "pixel")
        self.assertEqual(AB.device_state("pixel")["mic"], mic == "on")

    def test_block_by_bash(self):
        tok = AB.add_device("pixel")
        block = AS.termux_block("pixel", tok, self.url, "on")
        r = subprocess.run(["bash"], input=block, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Server knows this phone as 'pixel'", r.stdout)
        self.assertIn("Bridge started on 'pixel'", r.stdout)
        self.check_result(tok, "on")

    def test_block_pasted_into_interactive_bash(self):
        """As pasted from a phone's SSH app: line by line into an interactive
        shell, history expansion on, no bracketed paste."""
        tok = AB.add_device("pixel")
        block = AS.termux_block("pixel", tok, self.url, "off")
        pid, fd = pty.fork()
        if pid == 0:   # pragma: no cover - child
            env = dict(self.env, PS1="$ ", PS2="> ", TERM="xterm")
            os.execvpe("bash", ["bash", "--norc", "--noprofile", "-i"], env)
        out = b""

        def read(sec, until=None):
            nonlocal out
            end = time.time() + sec
            while time.time() < end:
                if until and until in out:
                    return
                r, _w, _x = select.select([fd], [], [], 0.1)
                if r:
                    try:
                        out += os.read(fd, 65536)
                    except OSError:
                        return
        try:
            read(1)
            os.write(fd, b"bind 'set enable-bracketed-paste off' 2>/dev/null; set -o history -H; echo READY\n")
            read(5, b"READY\r\n")
            data = block.encode()
            for i in range(0, len(data), 256):
                os.write(fd, data[i:i + 256])
                time.sleep(0.005)
            os.write(fd, b"echo PASTE_DONE_$((6*7))\n")
            read(60, b"PASTE_DONE_42")
            os.write(fd, b"exit\n")
            read(2)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
            os.waitpid(pid, 0)
        text = out.decode(errors="replace")
        self.assertIn("PASTE_DONE_42", text)
        self.assertNotIn("event not found", text)
        ran = text.split("nimbridge_install; unset -f nimbridge_install\r\n")[-1]   # what it printed
        self.assertIn("Setting up nimbridge 1.1 for phone pixel...", ran)
        self.assertNotIn("checksum differs", ran)
        self.assertIn("Bridge started on 'pixel'", ran)
        self.check_result(tok, "off")

    def test_bad_paste_is_caught(self):
        tok = AB.add_device("pixel")
        block = AS.termux_block("pixel", tok, self.url, "off").replace("set -u\n", "set -u \n", 1)
        r = subprocess.run(["bash"], input=block, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertIn("did not paste cleanly", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.prefix, "bin", "nimbridge")))
        self.assertFalse(os.path.exists(os.path.join(self.home, ".config", "nimbridge", "config")))
        self.assertFalse(AB.device_state("pixel")["online"])

    def test_wrong_key_says_so(self):
        AB.add_device("pixel")
        block = AS.termux_block("pixel", "nab_wrongwrongwrong", self.url, "off")
        r = subprocess.run(["bash"], input=block, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertIn("the server refused that token", r.stderr)
        self.assertFalse(AB.device_state("pixel")["online"])

    def test_not_termux(self):
        tok = AB.add_device("pixel")
        env = dict(self.env)
        env.pop("PREFIX")
        r = subprocess.run(["bash"], input=AS.termux_block("pixel", tok, self.url, "off"), env=env,
                           capture_output=True, text=True, timeout=30)
        self.assertIn("This block is for Termux on the phone. Nothing was changed.", r.stdout)
        self.assertFalse(os.path.exists(self.log))


if __name__ == "__main__":
    unittest.main()
