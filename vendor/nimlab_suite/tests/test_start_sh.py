"""Offline checks of start.sh and the CLI it calls."""

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = os.path.join(ROOT, "start.sh")
KEY = "nvapi-FAKEKEY_abcdefghijklmnop_0123"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run(args, env_extra=None, stdin="", cwd=None):
    env = {k: v for k, v in os.environ.items() if k not in ("NVIDIA_API_KEY", "NGC_API_KEY", "MCP_API_KEY")}
    env.update(env_extra or {})
    return subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=60, env=env, cwd=cwd or ROOT)


class StartShTests(unittest.TestCase):
    def test_syntax(self):
        self.assertEqual(run(["bash", "-n", START]).returncode, 0)

    def test_no_inline_python_or_interpolation(self):
        src = read(START)
        self.assertNotIn("python3 -c", src)
        self.assertNotIn("<<", src)  # no heredocs feeding code
        self.assertNotRegex(src, r"'''\$\{")
        self.assertNotRegex(src, r"'\$\{NVIDIA_API_KEY\}'")

    @unittest.skipUnless(shutil.which("shellcheck"), "shellcheck not installed")
    def test_shellcheck_clean(self):
        r = run(["shellcheck", START])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_status_key_masked(self):
        r = run([START, "status", "key"], {"NVIDIA_API_KEY": KEY})
        self.assertEqual(r.returncode, 0)
        self.assertIn("...0123", r.stdout)
        self.assertNotIn(KEY, r.stdout + r.stderr)

    def test_ngc_key_accepted(self):
        r = run([START, "status", "key"], {"NGC_API_KEY": KEY})
        self.assertIn("...0123", r.stdout)

    def test_status_without_key(self):
        r = run([START, "status", "key"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("NOT SET", r.stdout)

    def test_fleet_and_help(self):
        with tempfile.TemporaryDirectory() as d:
            env = {"NIMLAB_DATA_DIR": os.path.join(d, "data")}
            r = run([START, "fleet"], env)  # empty store: a clean message, not a crash
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("No verified 200 OK models yet", r.stdout)
            with open(os.path.join(d, "data", "models_verified.json"), "w", encoding="utf-8") as f:
                f.write('{"schema": 1, "models": {"meta/llama-x": {"status": "LIVE_200", "kind": "chat", '
                        '"url": "https://integrate.api.nvidia.com/v1/chat/completions", "latency_sec": 0.4}}, '
                        '"dropped": {}}')
            r = run([START, "fleet"], env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Total Live Models: 1", r.stdout)
        self.assertEqual(run([START, "--help"]).returncode, 0)

    def test_tui_menu_and_exit(self):
        r = run(["bash", START], stdin="5\n\n0\n", env_extra={"TERM": "dumb"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("VERIFIED 200 ENDPOINTS FLEET", r.stdout)
        self.assertIn("Exiting", r.stdout)

    def test_tui_runs_from_another_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run(["bash", START], stdin="0\n", env_extra={"TERM": "dumb"}, cwd=tmp)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_tts_injection_text_never_executes(self):
        """Hostile phrase goes to the TTS command via stdin; with no key the
        command refuses before any network call, and nothing is executed."""
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "pwned")
            phrase = f"''' ; import os; os.system('touch {marker}') ; ''' $(touch {marker}) `touch {marker}`"
            r = run(["bash", START], stdin=f"7\n{phrase}\n1\n\n0\n", env_extra={"TERM": "dumb"})
            self.assertFalse(os.path.exists(marker))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_persist_key_file_is_private_and_quoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file, bashrc = os.path.join(tmp, "env"), os.path.join(tmp, "bashrc")
            with open(bashrc, "w") as f:
                f.write("alias ll='ls -l'\nexport NVIDIA_API_KEY='old-plaintext'\n")
            weird = "nvapi-a'b\"c$(id)`x`;d"
            r = run([sys.executable, "-m", "nimlab", "persist-key", "--env-file", env_file, "--bashrc", bashrc],
                    {"NVIDIA_API_KEY": weird})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn(weird, r.stdout)
            self.assertEqual(stat.S_IMODE(os.stat(env_file).st_mode), 0o600)
            out = subprocess.run(["bash", "-c", f'. "{env_file}"; printf %s "$NVIDIA_API_KEY"'],
                                 capture_output=True, text=True).stdout
            self.assertEqual(out, weird)
            rc = read(bashrc)
            self.assertNotIn("old-plaintext", rc)
            self.assertIn("alias ll", rc)
            self.assertEqual(rc.count("# nimlab"), 1)
            run([sys.executable, "-m", "nimlab", "forget-key", "--env-file", env_file, "--bashrc", bashrc])
            self.assertFalse(os.path.exists(env_file))
            self.assertNotIn("nimlab_env", read(bashrc))

    def test_judge_show_without_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run([START, "judge", "show"], {"NIMLAB_OUTPUT_DIR": tmp})
        self.assertEqual(r.returncode, 1)
        self.assertIn("No judge results", r.stdout)


class PythonEntryPointTests(unittest.TestCase):
    def test_scripts_import_without_network(self):
        for mod in ("nvidia_playground", "nvidia_benchmark_suite", "orchestrator_testbed", "nvidia_router"):
            r = run([sys.executable, "-c", f"import {mod}"])
            self.assertEqual(r.returncode, 0, (mod, r.stderr))

    def test_no_direct_urllib_outside_core(self):
        for name in os.listdir(ROOT):
            if name.endswith(".py"):
                src = read(os.path.join(ROOT, name))
                self.assertIsNone(re.search(r"urllib\.request\.urlopen|import urllib", src), name)


if __name__ == "__main__":
    unittest.main()
