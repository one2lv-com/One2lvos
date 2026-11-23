"""The interactive menus after the v3.6.1 tidy-up: grouped, numbered 1-9
with 0 to go back, short enough for a phone, and every screen reachable."""

import contextlib
import io
import os
import re
import subprocess
import sys
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = os.path.join(ROOT, "start.sh")
sys.path.insert(0, ROOT)

from nimlab import colors as C, store  # noqa: E402

# Every test here works in a throwaway data and output folder, never the
# project's own data/ (a launcher run there would migrate the user's files).
_TMP = None
_OLD = {}


def setUpModule():
    global _TMP
    import tempfile
    _OLD.update({k: os.environ.get(k) for k in ("NIMLAB_DATA_DIR", "NIMLAB_OUTPUT_DIR")})
    _TMP = tempfile.TemporaryDirectory(prefix="nimlab-menus-")
    os.environ["NIMLAB_DATA_DIR"] = os.path.join(_TMP.name, "data")
    os.environ["NIMLAB_OUTPUT_DIR"] = os.path.join(_TMP.name, "output")
    store.reset()


def tearDownModule():
    # restore the suite-wide throwaway folders (tests/__init__.py); popping
    # them sent later tests to the project's own data/ folder
    for k, v in _OLD.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    store.reset()
    _TMP.cleanup()


def run_launcher(stdin, columns=None, extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ("NVIDIA_API_KEY", "NGC_API_KEY", "MCP_API_KEY", "COLUMNS", "FORCE_COLOR")}
    env.update({"TERM": "dumb", "NIMLAB_COLOR": "0"})
    if columns:
        env["COLUMNS"] = str(columns)
    env.update(extra or {})
    r = subprocess.run(["bash", START], input=stdin, capture_output=True, text=True, timeout=90, env=env, cwd=ROOT)
    return r, r.stdout.replace("\x1b[H\x1b[2J\x1b[3J", "").replace("\x1b[H\x1b[2J", "")


def menu_keys(text):
    return re.findall(r"^\s+([0-9A-Z])\. ", text, re.M)


class LauncherMenuTests(unittest.TestCase):
    def test_main_menu_grouped_and_numbered(self):
        r, out = run_launcher("0\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        for head in ("Run", "Models", "Setup"):
            self.assertRegex(out, rf"(?m)^{head}$")
        # 3.8.2: Scheduler, Health & repair, Service & update, Custom endpoints,
        # Tests and Commands are on the menu now (letters), not hidden keys.
        self.assertEqual(menu_keys(out), ["1", "2", "3", "4", "5", "6", "A", "U", "W", "H",
                                          "7", "8", "9", "S", "F", "E", "X", "0"])   # 3.8.6: F phone audio bridge
        for name in ("Testbed", "Playground", "Test server", "Discover & sweep", "Benchmark & judge",
                     "Roles & data", "Keys & MCP", "Memory", "Tools", "Scheduler", "Health & repair",
                     "Service & update", "Custom endpoints"):
            self.assertIn(name, out)
        # short: header + menu fit one phone screen (3.8.6: 33 menu lines + the exit message,
        # one more for F Phone audio bridge)
        self.assertLess(len(out.splitlines()), 37)

    def test_every_submenu_opens_and_goes_back(self):
        screens = {"3": "TEST SERVER", "4": "DISCOVER & SWEEP", "5": "BENCHMARK & JUDGE", "6": "ROLES & DATA",
                   "7": "KEYS & MCP", "9": "TOOLS"}
        for key, title in screens.items():
            r, out = run_launcher(f"{key}\n0\n0\n")
            self.assertEqual(r.returncode, 0, (key, r.stderr))
            self.assertIn(title, out, key)
            sub = out.split(title, 1)[1]
            keys = menu_keys(sub.split("NVIDIA NIM TEST LAB")[0])
            self.assertEqual(keys[-1], "0", key)
            # numbers 1..n first; letter keys (extra screens such as A, G) may follow
            nums = [int(k) for k in keys[:-1] if k.isdigit()]
            letters = [k for k in keys[:-1] if not k.isdigit()]
            self.assertEqual(keys[:-1], [str(n) for n in nums] + letters, (key, keys))
            self.assertEqual(nums, list(range(1, len(nums) + 1)), (key, keys))  # 1..n, no gaps
            self.assertLessEqual(len(nums), 13, key)
            self.assertIn("Exiting", out)

    def test_memory_opens_the_one_memory_menu(self):
        r, out = run_launcher("8\n0\n0\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        for head in ("Storage", "Behaviour", "Check"):
            self.assertIn(head, out)
        self.assertIn("Test connection", out)

    def test_old_letter_keys_still_work(self):
        # v3.7.0: S is now the guided setup (shown in the menu); D still opens Discover & sweep.
        for key, title in (("M", "KEYS & MCP"), ("O", "TEST SERVER"), ("D", "DISCOVER & SWEEP"),
                           ("S", "Step 1/12"), ("R", "ROLES & DATA"), ("L", "DATA STORES & LISTS"),
                           ("J", "BENCHMARK & JUDGE")):
            r, out = run_launcher(f"{key.lower()}\n0\n0\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(title, out, key)
        r, out = run_launcher("c\n\n0\n")
        self.assertIn("TERMINAL COLOURS", out)

    def test_no_duplicate_entries_in_a_screen(self):
        for key in ("", "3\n", "4\n", "5\n", "6\n", "7\n", "9\n"):
            r, out = run_launcher(f"{key}0\n0\n")
            screen = out.split("NVIDIA NIM TEST LAB")[0] if not key else \
                out.split("=" * 20)[4] if out.count("=" * 20) > 4 else out
            labels = re.findall(r"^\s+\d+\. (\S.*?)(?:\s{2,}|$)", screen, re.M)
            self.assertEqual(len(labels), len(set(labels)), (key, labels))

    def test_narrow_phone_screen_does_not_wrap(self):
        for cols in (40, 52):
            for key in ("", "4\n", "5\n", "7\n", "9\n", "6\n4\n"):
                r, out = run_launcher(f"{key}0\n0\n0\n", columns=cols)
                self.assertEqual(r.returncode, 0, r.stderr)
                for line in out.splitlines():
                    if line.startswith(" ") and ". " in line[:6] or set(line) <= set("=-") or "NIM TEST LAB" in line:
                        self.assertLessEqual(len(line), cols, (cols, key, line))

    def test_hints_shown_on_a_wide_screen(self):
        r, out = run_launcher("0\n", columns=70)
        self.assertIn("chat, voice, roles", out)
        r, out = run_launcher("0\n", columns=40)
        self.assertNotIn("chat, voice, roles", out)
        self.assertIn("Testbed", out)

    def test_help_mentions_shortcut(self):
        r = subprocess.run(["bash", START, "--help"], capture_output=True, text=True, timeout=60, cwd=ROOT)
        self.assertIn("./start.sh shortcut", r.stdout)
        self.assertIn("shortcut", r.stdout.split("positional", 1)[-1] if "positional" in r.stdout else r.stdout)


class FakeMemory:
    def count(self):
        return 4


def fake_orch():
    import copy
    from nimlab import config
    cluster = copy.deepcopy(config.load_cluster_config())
    cluster.setdefault("guard_settings", {})
    cluster.setdefault("routing_settings", {})
    return types.SimpleNamespace(cluster=cluster, mcp_settings=cluster["mcp_settings"],
                                 roles=cluster.get("roles", {}), memory=FakeMemory(),
                                 target=lambda k: "some/model", _build_mcp=lambda: None, prompts={}, soul="")


class TestbedMenuTests(unittest.TestCase):
    def drive(self, fn, answers, columns=70):
        import orchestrator_testbed as ot
        it = iter(answers)
        nxt = lambda *a, **k: next(it)  # noqa: E731
        buf = io.StringIO()
        with mock.patch.object(ot.C, "read", nxt), mock.patch.object(ot.C, "cinput", nxt), \
                mock.patch.object(ot, "save_cluster", lambda o: None), mock.patch.object(ot.os, "system"), \
                mock.patch.dict(os.environ, {"COLUMNS": str(columns), "NIMLAB_COLOR": "0"}), \
                contextlib.redirect_stdout(buf):
            C.reload_config()
            fn()
        C.reload_config()
        return buf.getvalue()

    def test_main_menu_most_used_first_and_grouped(self):
        import orchestrator_testbed as ot
        out = self.drive(lambda: ot._main_loop(fake_orch(), {}), ["0"])
        self.assertEqual(menu_keys(out), [str(n) for n in range(1, 10)] + ["0"])
        self.assertLess(out.index("Chat session"), out.index("Settings"))
        for head in ("Chat", "Roles & models", "Setup"):
            self.assertRegex(out, rf"(?m)^{re.escape(head)}$")
        self.assertIn("Roles:", out)
        self.assertLess(len(out.splitlines()), 26)

    def test_settings_top_level_is_six_groups(self):
        import orchestrator_testbed as ot
        out = self.drive(lambda: ot.settings_menu(fake_orch()), ["0"])
        self.assertEqual(menu_keys(out), ["1", "2", "3", "4", "5", "6", "0"])
        for name in ("MCP server & tools", "Voice", "Memory", "Guard & translate", "Routing", "Terminal colours"):
            self.assertIn(name, out)
        self.assertNotIn("17", menu_keys(out))

    def test_settings_groups_change_values(self):
        import orchestrator_testbed as ot
        orch = fake_orch()
        before = bool(orch.cluster["mcp_settings"].get("confirm_tool_calls"))
        # MCP group: 5 toggles confirm, 6 sets max steps (4 is blocked_tools since 3.7.3);
        # Guard: 3 sets target; Routing: 2 toggles show route
        show = orch.cluster["routing_settings"].get("show_route", True)
        self.drive(lambda: ot.settings_menu(orch),
                   ["1", "5", "6", "7", "0", "4", "3", "Spanish", "0", "5", "2", "0", "0"])
        self.assertEqual(bool(orch.cluster["mcp_settings"]["confirm_tool_calls"]), not before)
        self.assertEqual(orch.cluster["mcp_settings"]["max_tool_steps"], 7)
        self.assertEqual(orch.cluster["guard_settings"]["translate_target"], "Spanish")
        self.assertEqual(orch.cluster["routing_settings"]["show_route"], not show)

    def test_colour_key_c_still_cycles(self):
        import orchestrator_testbed as ot
        orch = fake_orch()
        orch.cluster.setdefault("ui_settings", {})["color"] = "auto"
        self.drive(lambda: ot.settings_menu(orch), ["c", "6", "0"])
        self.assertEqual(orch.cluster["ui_settings"]["color"], "off")

    def test_testbed_fits_a_narrow_screen(self):
        import orchestrator_testbed as ot
        out = self.drive(lambda: ot._main_loop(fake_orch(), {}), ["0"], columns=40)
        for line in out.splitlines():
            if re.match(r"^\s+\d+\. ", line) or set(line) <= set("=-"):
                self.assertLessEqual(len(line), 40, line)
        self.assertIn("NIM ORCHESTRATOR TESTBED", out)


class SubMenuTests(unittest.TestCase):
    def test_grpc_menu_grouped(self):
        from nimlab import grpcmenu
        lines = []
        with mock.patch.dict(os.environ, {"NIMLAB_COLOR": "0", "COLUMNS": "70"}):
            C.reload_config()
            with mock.patch.object(grpcmenu.nvcf_grpc, "seed_from_spec_cache", return_value=0):
                grpcmenu.run_menu(lambda *a: "0", lines.append)
        C.reload_config()
        out = "\n".join(lines)
        for head in ("Function IDs", "Per model", "Try it"):
            self.assertIn(head, out)
        menu = out.split("Function IDs", 1)[1]  # the model list above is numbered too
        self.assertEqual(menu_keys(menu), [str(n) for n in range(1, 9)] + ["0"])

    def test_memory_menu_numbers_are_sequential(self):
        from nimlab import memmenu
        keys = [k for _t, rows in memmenu.MENU for k, _n, _e in rows]
        nums = [int(k) for k in keys if k.isdigit()]
        self.assertEqual(nums, list(range(1, len(nums) + 1)))
        # 3.7.1: a sub-item (3o ORDS) sits right after its parent (3 Oracle)
        for i, k in enumerate(keys):
            if not k.isdigit():
                self.assertRegex(k, r"^\d+[a-z]$")
                self.assertEqual(keys[i - 1], k[:-1])

    def test_memory_menu_old_letters_still_work(self):
        from nimlab import memmenu
        cluster = fake_orch().cluster
        lines = []
        answers = iter(["t", "", "0"])
        with mock.patch.object(memmenu, "test_lines", lambda *a, **k: ["TESTED-OK"], create=True):
            try:
                memmenu.run_menu(cluster, lambda *a: next(answers), lines.append, save_fn=lambda: None)
            except StopIteration:
                pass
        self.assertTrue(any("Test connection" in ln for ln in lines))


if __name__ == "__main__":
    unittest.main()
