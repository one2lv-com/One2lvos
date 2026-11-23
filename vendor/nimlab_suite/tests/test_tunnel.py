"""Cloudflare tunnel support against a fake cloudflared (a small script that
prints what the real one prints). No network, no real cloudflared."""

import io
import os
import stat
import sys
import threading
import time
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import server as S, servemenu, tunnel as TN
from tests.sandbox import all_text, lab

TOKEN = "eyJhIjoi" + "Z" * 70

FAKE = r'''#!{py}
import os, sys, time
mode = os.environ.get("FAKE_CF_MODE", "quick")
with open(os.environ["FAKE_CF_ARGS"], "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\n")
print("INF Starting tunnel tunnelID=abc", flush=True)
if os.environ.get("TUNNEL_TOKEN"):
    print("DBG token in use: " + os.environ["TUNNEL_TOKEN"], flush=True)
if mode == "quick":
    print("INF |  https://brave-fox-12.trycloudflare.com  |", flush=True)
elif mode == "named":
    print("INF Registered tunnel connection connIndex=0", flush=True)
elif mode == "fail":
    print("ERR failed to dial edge", flush=True)
    sys.exit(3)
if os.environ.get("FAKE_CF_DIE"):
    time.sleep(float(os.environ["FAKE_CF_DIE"]))
    print("ERR connection lost", flush=True)
    sys.exit(1)
time.sleep(30)
'''


class TunnelTests(unittest.TestCase):
    def setUp(self):
        self._lab = lab()
        self.lab = self._lab.__enter__()
        self.exe = os.path.join(self.lab.root, "bin", "cloudflared")
        os.makedirs(os.path.dirname(self.exe))
        with open(self.exe, "w") as f:
            f.write(FAKE.replace("{py}", sys.executable))
        os.chmod(self.exe, 0o755)
        self.args = os.path.join(self.lab.root, "cf_args.txt")
        os.environ["FAKE_CF_ARGS"] = self.args
        self.tunnels = []

    def tearDown(self):
        for t in self.tunnels:
            t.stop()
            th = getattr(t, "_thread", None)
            if th:
                th.join(5)      # no reader may write status after the temp data folder is gone
        self._lab.__exit__(None, None, None)

    def env(self, **extra):
        e = dict(os.environ, **extra)
        return e

    def make(self, tsettings, mode=None, **env):
        t = TN.CloudflaredTunnel(8765, tsettings, mode=mode, exe=self.exe, env=self.env(**env))
        self.tunnels.append(t)
        return t

    # -- quick -------------------------------------------------------------
    def test_quick_tunnel_reports_url_and_status(self):
        t = self.make({"mode": "quick"}, FAKE_CF_MODE="quick")
        url = t.start(wait=10)
        self.assertEqual(url, "https://brave-fox-12.trycloudflare.com")
        with open(self.args) as f:
            self.assertIn("tunnel --no-autoupdate --url http://127.0.0.1:8765", f.read())
        st = TN.read_status()
        self.assertEqual((st["state"], st["url"], st["mode"]), ("up", url, "quick"))
        self.assertIn("trycloudflare.com", TN.brief())
        t.stop()
        self.assertEqual(TN.read_status()["state"], "stopped")

    def test_cloudflared_failing_at_start(self):
        t = self.make({"mode": "quick"}, FAKE_CF_MODE="fail")
        with self.assertRaises(RuntimeError) as cm:
            t.start(wait=10)
        self.assertIn("failed to dial edge", str(cm.exception))

    def test_missing_cloudflared_explains_install(self):
        t = TN.CloudflaredTunnel(8765, {"mode": "quick"}, env={"PATH": "/nonexistent", "HOME": self.lab.home})
        with self.assertRaises(RuntimeError) as cm:
            t.start()
        self.assertIn("serve tunnel install", str(cm.exception))

    # -- named -------------------------------------------------------------
    def test_named_token_passed_by_env_and_scrubbed(self):
        TN.save_token(TOKEN)
        self.assertEqual(TN.file_mode(TN.token_path()), 0o600)
        t = self.make({"mode": "named", "named": {"method": "token", "hostname": "lab.example.com"}},
                      FAKE_CF_MODE="named")
        url = t.start(wait=10)
        self.assertEqual(url, "https://lab.example.com")
        with open(self.args) as f:
            argv = f.read()
        self.assertIn("tunnel --no-autoupdate run", argv)
        self.assertNotIn(TOKEN, argv)                       # never on the command line
        time.sleep(0.2)
        self.assertTrue(any("***" in ln for ln in t.output))  # cloudflared echoed it: scrubbed
        self.assertNotIn(TOKEN, "\n".join(t.output))
        self.assertNotIn(TOKEN, all_text(self.lab.data))

    def test_named_config_writes_yml(self):
        cred = os.path.join(self.lab.home, "abc.json")
        with open(cred, "w") as f:
            f.write("{}")
        named = {"method": "config", "tunnel": "abc", "credentials_file": cred, "hostname": "lab.example.com"}
        t = self.make({"mode": "named", "named": named}, FAKE_CF_MODE="named")
        t.start(wait=10)
        yml = TN.config_yml_path()
        with open(yml) as f:
            text = f.read()
        self.assertIn("tunnel: abc", text)
        self.assertIn("hostname: lab.example.com", text)
        self.assertIn("service: http://127.0.0.1:8765", text)
        self.assertIn("http_status:404", text)
        with open(self.args) as f:
            self.assertIn(f"--config {yml} run abc", f.read())

    def test_named_not_ready_lists_problems(self):
        t = self.make({"mode": "named", "named": {"method": "config", "hostname": "https://x"}})
        with self.assertRaises(RuntimeError) as cm:
            t.start()
        msg = str(cm.exception)
        for bit in ("no tunnel ID", "no credentials file", "is not a hostname"):
            self.assertIn(bit, msg)

    def test_token_validation(self):
        with self.assertRaises(ValueError):
            TN.save_token("short")
        with self.assertRaises(ValueError):
            TN.save_token("sudo cloudflared service install " + TOKEN)
        self.assertEqual(TN.save_token("--token " + TOKEN + "\n"), TOKEN)
        self.assertEqual(TN.mask(TOKEN), "..." + TOKEN[-4:])
        self.assertTrue(TN.delete_token())
        self.assertFalse(TN.delete_token())

    # -- keeper ------------------------------------------------------------
    def test_keeper_warns_and_retries_after_exit(self):
        warns, urls = [], []
        done = threading.Event()

        def on_url(u):
            urls.append(u)
            if len(urls) >= 3:
                done.set()
        os.environ["FAKE_CF_DIE"] = "0.3"
        k = TN.Keeper(8765, {"mode": "quick"}, warn=warns.append, sleep=lambda s: None, on_url=on_url,
                      factory=lambda cb: self._tracked(TN.CloudflaredTunnel(8765, {"mode": "quick"}, exe=self.exe,
                                                                           on_exit=cb, env=self.env())))
        self.assertEqual(k.start(), "https://brave-fox-12.trycloudflare.com")
        self.assertTrue(done.wait(15))
        k.stop()
        text = "\n".join(warns)
        self.assertIn("cloudflared exited (code 1)", text)
        self.assertIn("The server keeps running", text)
        self.assertIn("Trying the tunnel again in 10 s (1/5)", text)
        self.assertIn("[ok] Tunnel back up", text)
        self.assertEqual(urls[:3], ["https://brave-fox-12.trycloudflare.com", None,
                                    "https://brave-fox-12.trycloudflare.com"])

    def _tracked(self, t):
        self.tunnels.append(t)
        return t

    def test_keeper_backoff_and_gives_up(self):
        warns, sleeps = [], []

        class Dead:
            url = None

            def __init__(self, cb):
                pass

            def start(self):
                raise RuntimeError("cloudflared exited at once")

            def stop(self):
                pass
        k = TN.Keeper(8765, {"mode": "quick"}, warn=warns.append, sleep=sleeps.append, factory=Dead, tries=4)
        self.assertIsNone(k.start())
        self.assertIn("The server keeps running without it", warns[0])
        k._retry()
        self.assertEqual(sleeps, [10, 30, 60, 120])
        self.assertIn("Gave up on the tunnel", warns[-1])
        self.assertEqual(TN.read_status()["state"], "failed")

    # -- install -----------------------------------------------------------
    def test_install_on_termux_uses_pkg(self):
        calls = []
        env = {"TERMUX_VERSION": "1", "PATH": "/nonexistent", "HOME": self.lab.home}
        ok, msg = TN.install_cloudflared(env=env, run=lambda c: calls.append(c) or types.SimpleNamespace(returncode=1),
                                         log=lambda m: None)
        self.assertEqual(calls, [["pkg", "install", "-y", "cloudflared"]])
        self.assertFalse(ok)

    def test_install_linux_downloads_binary(self):
        env = {"PATH": "/nonexistent", "HOME": self.lab.home}
        urls = []
        ok, path = TN.install_cloudflared(env=env, machine="aarch64", log=lambda m: None,
                                          download=lambda u: urls.append(u) or b"\x7fELF" + b"0" * 1_100_000)
        self.assertTrue(ok)
        self.assertTrue(urls[0].endswith("cloudflared-linux-arm64"))
        self.assertTrue(os.access(path, os.X_OK))
        self.assertEqual(TN.find_cloudflared(env), path)
        bad = TN.install_cloudflared(env={"PATH": "/x", "HOME": os.path.join(self.lab.root, "h2")}, machine="x86_64",
                                     log=lambda m: None, download=lambda u: b"<html>")
        self.assertFalse(bad[0])
        self.assertFalse(TN.install_cloudflared(env={"PATH": "/x", "HOME": self.lab.home + "3"},
                                                machine="mips", log=lambda m: None)[0])

    # -- CLI ---------------------------------------------------------------
    def cli(self, values, token=False, credentials=None, hostname=None, auto=None, stdin=""):
        args = types.SimpleNamespace(values=values, token=token, credentials=credentials, hostname=hostname, auto=auto)
        out = io.StringIO()
        with redirect_stdout(out), mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                mock.patch.object(TN, "find_cloudflared", return_value=self.exe):
            code = servemenu.cmd_tunnel(args, S.load_settings())
        return code, out.getvalue()

    def test_cli_quick_auto_off_status(self):
        code, out = self.cli(["quick"], auto=True)
        self.assertEqual(code, 0)
        t = S.load_settings()["tunnel"]
        self.assertEqual((t["mode"], t["auto_start"]), ("quick", True))
        self.assertIn("API key is required", out)
        self.assertEqual(self.cli(["auto", "off"])[0], 0)
        self.assertFalse(S.load_settings()["tunnel"]["auto_start"])
        self.assertEqual(self.cli(["auto"])[0], 2)
        self.assertEqual(self.cli(["off"])[0], 0)
        self.assertEqual(S.load_settings()["tunnel"]["mode"], "off")
        self.assertEqual(self.cli(["status"])[0], 0)
        self.assertEqual(self.cli(["bogus"])[0], 2)

    def test_cli_named_token_from_stdin_never_printed(self):
        code, out = self.cli(["named"], token=True, hostname="https://lab.example.com/", stdin=TOKEN + "\n")
        self.assertEqual(code, 0)
        self.assertNotIn(TOKEN, out)
        self.assertEqual(TN.load_token(), TOKEN)
        n = S.load_settings()["tunnel"]["named"]
        self.assertEqual((n["method"], n["hostname"]), ("token", "lab.example.com"))
        self.assertNotIn(TOKEN, all_text(self.lab.data) + all_text(self.lab.proj))
        self.assertEqual(stat.S_IMODE(os.stat(TN.token_path()).st_mode), 0o600)
        self.assertEqual(self.cli(["named"], token=True, stdin="cloudflared service install x\n")[0], 2)
        self.assertEqual(self.cli(["token-delete"])[0], 0)

    def test_cli_named_config(self):
        cred = os.path.join(self.lab.home, "t.json")
        with open(cred, "w") as f:
            f.write("{}")
        code, out = self.cli(["named", "my-tunnel"], credentials=cred, hostname="lab.example.com")
        self.assertEqual(code, 0)
        self.assertIn("cloudflared config:", out)
        self.assertTrue(os.path.exists(TN.config_yml_path()))


if __name__ == "__main__":
    unittest.main()
