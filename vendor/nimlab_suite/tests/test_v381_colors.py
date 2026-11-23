"""3.8.1: the menus added in 3.7.4 / 3.8.0 use colors.py like the older ones.

Walks every new screen twice: with colour forced on (ANSI codes present,
the colors.py header / entry look) and with colour off (NIMLAB_COLOR=0,
NO_COLOR, not a terminal: no ANSI codes at all, same words).
"""

import contextlib
import io
import os
import re
import unittest
from unittest import mock

from nimlab import colors as C, commands, systests, paint, hostenv, jobscli, heartbeat as HB
from tests.test_v374 import FakeCtx
from tests.test_v380 import LabCase

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def strip(s):
    return ANSI.sub("", s)


def colour_env(on, extra=None):
    e = {k: v for k, v in os.environ.items()
         if k not in ("NIMLAB_COLOR", "NO_COLOR", "FORCE_COLOR", "COLUMNS")}
    e["NIMLAB_COLOR"] = "1" if on else "0"
    e["COLUMNS"] = "50"
    e.update(extra or {})
    return mock.patch.dict(os.environ, e, clear=True)


def feed(answers):
    it = iter(answers)
    return lambda prompt="": next(it, "b")


class Walk:
    """Collects everything a menu says and every prompt it asks."""

    def __init__(self, answers):
        self.said = []
        self.prompts = []
        self.it = iter(answers)

    def ask(self, prompt=""):
        self.prompts.append(prompt)
        return next(self.it, "b")

    def say(self, text=""):
        self.said.append(str(text))

    def text(self):
        return "\n".join(self.said + self.prompts)


class ColourWalkBase:
    def walk_commands(self):
        w = Walk(["1", "b", "t", "1", "b", "b", "b"])
        commands.menu(ask=w.ask, say=w.say, runner=lambda argv: 0)
        return w

    def walk_tests(self):
        w = Walk(["platform", "", "h", "", "b"])
        with mock.patch.object(systests, "save_history"), \
                mock.patch.object(systests, "load_history",
                                  return_value=[{"at": "2026-11-13 00:30",
                                                 "results": {"mcp": {"status": systests.FAIL},
                                                             "key": {"status": systests.PASS}}}]):
            systests.menu(ask=w.ask, say=w.say, ctx=FakeCtx())
        return w

    def walk_run_all(self):
        out = []
        with mock.patch.object(systests, "save_history"):
            systests.run_all(FakeCtx(config_problems=["speech URL is a homepage"]), out.append,
                             names=["platform", "key", "config"], color=True)
        return "\n".join(out)

    def cli(self, fn, *a):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fn(*a)
        return buf.getvalue()


class NewMenusInColour(LabCase, ColourWalkBase):
    def test_commands_menu_is_coloured(self):
        with colour_env(True):
            t = self.walk_commands().text()
        self.assertTrue(ANSI.search(t))
        plain = strip(t)
        self.assertIn("COMMANDS & TROUBLESHOOTING", plain)
        self.assertIn("TROUBLESHOOTING", plain)
        self.assertRegex(plain, r"\n\s+1\. Setup")
        self.assertNotIn("== ", plain)

    def test_tests_menu_colours_pass_fail_skip(self):
        with colour_env(True):
            t = self.walk_tests().text()
            all_ = self.walk_run_all()
        self.assertTrue(ANSI.search(t))
        self.assertIn(C.ok("[PASS]") if "[PASS]" in strip(t) else C.warn("[skip]"), t + all_)
        self.assertIn(C.err("1 failed"), t)              # the history row
        self.assertIn(C.err("FAIL"), all_)               # the table's result column
        self.assertIn(C.warn("*"), t)                    # the live marker

    def test_failure_lines_highlight_bug_id_and_next_step(self):
        r = systests.Result(systests.FAIL, "refused", fix="nimlab mcp test")
        r.bug = "B-1A2B3C"
        with colour_env(True):
            lines = paint.result_lines(systests.result_lines(systests.find("mcp"), r))
        joined = "\n".join(lines)
        self.assertIn(C.err("[FAIL]"), joined)
        self.assertIn(C.paint("B-1A2B3C", "http4", "bold"), joined)
        self.assertIn(C.paint("nimlab mcp test", "accent"), joined)

    def test_scheduler_menus_are_coloured(self):
        w = Walk(["1", "b", "3", "b", "4", "b", "b"])
        with colour_env(True):
            jobscli.menu(ask=w.ask, say=w.say)
        t = w.text()
        self.assertTrue(ANSI.search(t))
        plain = strip(t)
        for title in ("SCHEDULER", "JOBS", "HEARTBEAT", "SUGGESTED ACTIONS"):
            self.assertIn(title, plain)
        self.assertIn("heartbeat", plain)

    def test_jobs_heartbeat_platform_cli_are_coloured(self):
        ns = type("A", (), {"action": "list", "name": None, "n": None, "status": None})()
        hb = type("A", (), {"action": "status", "rest": [], "n": None})()
        with colour_env(True):
            jobs = self.cli(jobscli.cmd_jobs, ns)
            status = self.cli(jobscli.cmd_heartbeat, hb)
            plat = self.cli(hostenv.cmd_platform, None)
            sheet = self.cli(commands.cmd_commands, type("A", (), {"area": "mcp", "markdown": False,
                                                                   "menu": False})())
        for out in (jobs, status, plat, sheet):
            self.assertTrue(ANSI.search(out), out[:200])
        self.assertIn("Heartbeat:", strip(status))
        self.assertIn("PLATFORM", strip(plat))

    def test_new_menus_fit_a_phone(self):
        with colour_env(True):
            w = self.walk_commands()
            s = Walk(["b"])
            systests.menu(ask=s.ask, say=s.say, ctx=FakeCtx())
            j = Walk(["b"])
            jobscli.menu(ask=j.ask, say=j.say)
            width = C.screen_width()
        self.assertEqual(width, 50)
        for line in w.said + s.said + j.said:
            self.assertLessEqual(len(strip(line)), width + 4, strip(line))


class NewMenusPlain(LabCase, ColourWalkBase):
    def check_plain(self, extra=None):
        with colour_env(False, extra):
            texts = [self.walk_commands().text(), self.walk_tests().text(), self.walk_run_all()]
            w = Walk(["1", "b", "3", "b", "4", "b", "b"])
            jobscli.menu(ask=w.ask, say=w.say)
            texts.append(w.text())
            texts.append(self.cli(hostenv.cmd_platform, None))
            texts.append("\n".join(paint.heartbeat_lines(HB.status_lines())))
        for t in texts:
            self.assertIsNone(ANSI.search(t), t[:300])
        return texts

    def test_nimlab_color_0_has_no_ansi(self):
        texts = self.check_plain()
        self.assertIn("COMMANDS & TROUBLESHOOTING", texts[0])
        self.assertIn("[PASS]", texts[1] + texts[2])

    def test_no_color_has_no_ansi(self):
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            e = {k: v for k, v in os.environ.items() if k != "NIMLAB_COLOR"}
        with mock.patch.dict(os.environ, e, clear=True):
            self.assertFalse(C.enabled())
        self.check_plain({"NO_COLOR": "1"})

    def test_plain_line_builders_unchanged(self):
        """Telegram, memory and Quill's tools read these: never coloured."""
        with colour_env(True):
            r = systests.Result(systests.PASS, "fine")
            line = systests.result_lines(systests.find("key"), r)[0]
            jobs = HB.status_lines()
        self.assertTrue(line.startswith("[PASS] key"))
        for t in [line] + jobs:
            self.assertIsNone(ANSI.search(t))

    def test_paint_helpers_are_identity_when_off(self):
        samples = ["[FAIL] mcp   12 ms  refused", "       next: nimlab mcp test", "Heartbeat: off, every 30",
                   "  [on ] heartbeat  quill_prompt  next -  last SUCCEEDED", "3 passed, 1 failed, 0 skipped"]
        with colour_env(False):
            for s in samples:
                self.assertEqual(paint.auto(s), s)
                self.assertEqual(paint.status_line(s), s)
                self.assertEqual(paint.summary(s), s)
            self.assertEqual(paint.result_lines(samples), samples)
            self.assertEqual(paint.table_lines(samples), samples)


if __name__ == "__main__":
    unittest.main()
