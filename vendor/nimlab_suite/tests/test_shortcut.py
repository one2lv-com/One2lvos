"""`./start.sh shortcut`: the nimlab wrapper (offline, temp HOME / PREFIX)."""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nimlab import shortcut as S  # noqa: E402


def read(path):
    with open(path) as f:
        return f.read()

START = os.path.join(ROOT, "start.sh")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nimlab-sc-")
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def linux_env(self, on_path=True):
        b = os.path.join(self.home, ".local", "bin")
        path = (b + os.pathsep if on_path else "") + "/usr/bin:/bin"
        return {"HOME": self.home, "PATH": path}

    def termux_env(self):
        prefix = os.path.join(self.tmp, "data", "data", "com.termux", "files", "usr")
        os.makedirs(os.path.join(prefix, "bin"))
        return {"HOME": self.home, "PREFIX": prefix, "TERMUX_VERSION": "0.118",
                "PATH": os.path.join(prefix, "bin") + ":/usr/bin:/bin"}

    def fake_project(self, name="lab"):
        """A copy of the lab whose start.sh echoes its folder and arguments."""
        d = os.path.join(self.tmp, name)
        os.makedirs(d)
        with open(os.path.join(d, "start.sh"), "w") as f:
            f.write('#!/usr/bin/env bash\nSCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
                    'echo "DIR=$SCRIPT_DIR"\nfor a in "$@"; do echo "ARG=$a"; done\n')
        return d


class PlatformTests(Base):
    def test_linux_goes_to_local_bin_with_env_shebang(self):
        env = self.linux_env()
        self.assertEqual(S.bin_dir(env), os.path.join(self.home, ".local", "bin"))
        self.assertEqual(S.shebang(env), "#!/usr/bin/env bash")
        self.assertFalse(S.is_termux(env))

    def test_termux_goes_to_prefix_bin_with_termux_bash(self):
        env = self.termux_env()
        self.assertTrue(S.is_termux(env))
        self.assertEqual(S.bin_dir(env), os.path.join(env["PREFIX"], "bin"))
        self.assertEqual(S.shebang(env), "#!" + os.path.join(env["PREFIX"], "bin", "bash"))

    def test_termux_detected_from_prefix_alone(self):
        env = self.termux_env()
        del env["TERMUX_VERSION"]
        self.assertTrue(S.is_termux(env))

    def test_bad_names_refused(self):
        for bad in ("", "a/b", "../x", "-rf", "a b"):
            with self.assertRaises(ValueError):
                S.check_name(bad)
        self.assertEqual(S.check_name("nim-lab_2"), "nim-lab_2")


class InstallTests(Base):
    def test_install_creates_executable_wrapper_not_symlink(self):
        env = self.linux_env()
        root = self.fake_project()
        ok, lines = S.install(env=env, root=root)
        self.assertTrue(ok, lines)
        dest = os.path.join(self.home, ".local", "bin", "nimlab")
        self.assertTrue(os.path.isfile(dest))
        self.assertFalse(os.path.islink(dest))
        self.assertTrue(os.stat(dest).st_mode & stat.S_IXUSR)
        text = read(dest)
        self.assertTrue(text.startswith("#!/usr/bin/env bash\n"))
        self.assertIn('exec bash "$NIMLAB_START" "$@"', text)
        self.assertEqual(S.target_of(dest), os.path.join(os.path.realpath(root), "start.sh"))
        self.assertTrue(any("Installed 'nimlab'" in ln for ln in lines))

    def test_wrapper_passes_args_and_keeps_script_dir(self):
        env = self.linux_env()
        root = self.fake_project("lab with space")
        S.install(env=env, root=root)
        dest = os.path.join(self.home, ".local", "bin", "nimlab")
        r = subprocess.run([dest, "grpc", "check", "two words", "$HOME"], capture_output=True, text=True,
                           cwd=self.tmp, env=dict(os.environ, **env), timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("DIR=" + os.path.realpath(root), r.stdout)
        self.assertEqual([ln[4:] for ln in r.stdout.splitlines() if ln.startswith("ARG=")],
                         ["grpc", "check", "two words", "$HOME"])

    def test_creates_local_bin_and_warns_when_not_on_path(self):
        env = self.linux_env(on_path=False)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".local", "bin")))
        ok, lines = S.install(env=env, root=self.fake_project())
        self.assertTrue(ok)
        self.assertTrue(os.path.isdir(os.path.join(self.home, ".local", "bin")))
        joined = "\n".join(lines)
        self.assertIn("not on your PATH", joined)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', joined)

    def test_termux_install_uses_prefix_and_shebang(self):
        env = self.termux_env()
        ok, lines = S.install(env=env, root=self.fake_project())
        self.assertTrue(ok, lines)
        dest = os.path.join(env["PREFIX"], "bin", "nimlab")
        self.assertTrue(read(dest).startswith("#!" + os.path.join(env["PREFIX"], "bin", "bash") + "\n"))
        self.assertNotIn("not on your PATH", "\n".join(lines))

    def test_rerun_after_move_updates_path(self):
        env = self.linux_env()
        old = self.fake_project("old")
        S.install(env=env, root=old)
        new = os.path.join(self.tmp, "new")
        shutil.move(old, new)
        dest = os.path.join(self.home, ".local", "bin", "nimlab")
        healthy, lines = S.status(env=env, root=new)
        self.assertFalse(healthy)
        self.assertIn("MISSING", "\n".join(lines))
        r = subprocess.run([dest], capture_output=True, text=True, env=dict(os.environ, **env), timeout=30)
        self.assertEqual(r.returncode, 127)
        self.assertIn("is gone", r.stderr)
        ok, lines = S.install(env=env, root=new)
        self.assertTrue(ok)
        self.assertIn("Updated 'nimlab'", "\n".join(lines))
        self.assertEqual(S.target_of(dest), os.path.join(os.path.realpath(new), "start.sh"))

    def test_rerun_same_place_is_a_no_op(self):
        env = self.linux_env()
        root = self.fake_project()
        S.install(env=env, root=root)
        ok, lines = S.install(env=env, root=root)
        self.assertTrue(ok)
        self.assertIn("already set up", "\n".join(lines))

    def test_unrelated_command_not_overwritten_without_force(self):
        env = self.linux_env()
        b = os.path.join(self.home, ".local", "bin")
        os.makedirs(b)
        other = os.path.join(b, "nimlab")
        with open(other, "w") as f:
            f.write("#!/bin/sh\necho mine\n")
        ok, lines = S.install(env=env, root=self.fake_project())
        self.assertFalse(ok)
        self.assertIn("--force", "\n".join(lines))
        self.assertEqual(read(other), "#!/bin/sh\necho mine\n")
        ok, lines = S.install(env=env, root=self.fake_project("lab2"), force=True)
        self.assertTrue(ok)
        self.assertIn("Replacing", "\n".join(lines))
        self.assertTrue(S.is_ours(other))

    def test_symlink_of_same_name_needs_force(self):
        env = self.linux_env()
        b = os.path.join(self.home, ".local", "bin")
        os.makedirs(b)
        os.symlink("/bin/true", os.path.join(b, "nimlab"))
        ok, lines = S.install(env=env, root=self.fake_project())
        self.assertFalse(ok)
        self.assertIn("symlink", "\n".join(lines))
        ok, _ = S.install(env=env, root=self.fake_project("l2"), force=True)
        self.assertTrue(ok)
        self.assertFalse(os.path.islink(os.path.join(b, "nimlab")))

    def test_custom_name(self):
        env = self.linux_env()
        ok, lines = S.install("nim", env=env, root=self.fake_project())
        self.assertTrue(ok)
        dest = os.path.join(self.home, ".local", "bin", "nim")
        self.assertTrue(S.is_ours(dest))
        self.assertIn("shortcut remove nim", read(dest))
        self.assertFalse(os.path.exists(os.path.join(self.home, ".local", "bin", "nimlab")))

    def test_warns_when_another_command_shadows_it(self):
        env = self.linux_env()
        first = os.path.join(self.tmp, "first")
        os.makedirs(first)
        with open(os.path.join(first, "nimlab"), "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(os.path.join(first, "nimlab"), 0o755)
        env["PATH"] = first + os.pathsep + env["PATH"]
        ok, lines = S.install(env=env, root=self.fake_project())
        self.assertTrue(ok)
        self.assertIn("comes first on your PATH", "\n".join(lines))


class RemoveStatusTests(Base):
    def test_remove_only_own_wrapper(self):
        env = self.linux_env()
        S.install(env=env, root=self.fake_project())
        dest = os.path.join(self.home, ".local", "bin", "nimlab")
        ok, lines = S.remove(env=env)
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(dest))
        ok, lines = S.remove(env=env)
        self.assertTrue(ok)
        self.assertIn("nothing to remove", lines[0])
        with open(dest, "w") as f:
            f.write("#!/bin/sh\n")
        ok, lines = S.remove(env=env)
        self.assertFalse(ok)
        self.assertTrue(os.path.exists(dest))

    def test_status_reports_target_and_health(self):
        env = self.linux_env()
        healthy, lines = S.status(env=env, root=self.fake_project())
        self.assertFalse(healthy)
        self.assertIn("not installed", lines[0])
        root = os.path.join(self.tmp, "lab")
        S.install(env=env, root=root)
        healthy, lines = S.status(env=env, root=root)
        self.assertTrue(healthy, lines)
        joined = "\n".join(lines)
        self.assertIn("runs    : " + os.path.join(os.path.realpath(root), "start.sh"), joined)
        self.assertIn("Ready", joined)

    def test_status_flags_another_copy(self):
        env = self.linux_env()
        a, b = self.fake_project("a"), self.fake_project("b")
        S.install(env=env, root=a)
        healthy, lines = S.status(env=env, root=b)
        self.assertIn("another copy", "\n".join(lines))


class StartShTests(Base):
    """Through the real start.sh, with a temp HOME and PREFIX."""

    def run_start(self, *args, env=None):
        e = {k: v for k, v in os.environ.items() if k not in ("PREFIX", "TERMUX_VERSION")}
        e.update(env or {})
        e.update(NIMLAB_DATA_DIR=os.path.join(self.tmp, "data"), NIMLAB_OUTPUT_DIR=os.path.join(self.tmp, "out"))
        e["NIMLAB_COLOR"] = "0"
        return subprocess.run(["bash", START, *args], capture_output=True, text=True, timeout=60, env=e, cwd=self.tmp)

    def test_install_status_remove_cycle_termux(self):
        env = self.termux_env()
        env["PATH"] += os.pathsep + os.environ.get("PATH", "")
        r = self.run_start("shortcut", env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = os.path.join(env["PREFIX"], "bin", "nimlab")
        self.assertTrue(S.is_ours(dest))
        self.assertEqual(S.target_of(dest), os.path.join(os.path.realpath(ROOT), "start.sh"))
        r = self.run_start("shortcut", "status", env=env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Ready", r.stdout)
        # the wrapper really runs the lab from another folder, args passed through
        r = subprocess.run(["bash", dest, "shortcut", "status"], capture_output=True, text=True, timeout=60,
                           cwd=self.home, env=dict(os.environ, **env, NIMLAB_COLOR="0",
                                                   NIMLAB_DATA_DIR=os.path.join(self.tmp, "data")))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("command : nimlab", r.stdout)
        r = self.run_start("shortcut", "remove", env=env)
        self.assertEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(dest))

    def test_custom_name_and_refusal_exit_codes(self):
        env = self.linux_env()
        env["PATH"] += os.pathsep + os.environ.get("PATH", "")
        b = os.path.join(self.home, ".local", "bin")
        os.makedirs(b)
        with open(os.path.join(b, "nimlab"), "w") as f:
            f.write("#!/bin/sh\n")
        r = self.run_start("shortcut", env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("--force", r.stdout)
        r = self.run_start("shortcut", "install", "nim", env=env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(S.is_ours(os.path.join(b, "nim")))
        r = self.run_start("shortcut", "install", "bad/name", env=env)
        self.assertEqual(r.returncode, 2)

    def test_launcher_tools_menu_installs(self):
        env = self.linux_env()
        env["PATH"] += os.pathsep + os.environ.get("PATH", "")
        env["TERM"] = "dumb"
        e = {k: v for k, v in os.environ.items() if k not in ("PREFIX", "TERMUX_VERSION")}
        e.update(env, NIMLAB_COLOR="0", NIMLAB_DATA_DIR=os.path.join(self.tmp, "data"),
                 NIMLAB_OUTPUT_DIR=os.path.join(self.tmp, "out"))
        r = subprocess.run(["bash", START], input="9\n2\n\n0\n0\n", capture_output=True, text=True, timeout=60,
                           env=e, cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(S.is_ours(os.path.join(self.home, ".local", "bin", "nimlab")))


if __name__ == "__main__":
    unittest.main()
