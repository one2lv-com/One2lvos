"""v3.5: terminal colours. On/off rules, depth, visible width, the
highlighter, and that nothing outside the screen (server replies, the
request log, saved config, piped output) ever gets an escape code."""
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from nimlab import colors as C
from nimlab import roles as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESC = "\x1b"


class TTY(io.StringIO):
    def isatty(self):
        return True


class Pipe(io.StringIO):
    def isatty(self):
        return False


def env(**kw):
    """A clean colour environment for one test."""
    base = {k: v for k, v in os.environ.items()
            if k not in ("NIMLAB_COLOR", "NO_COLOR", "FORCE_COLOR", "NIMLAB_COLOR_DEPTH", "COLORTERM",
                         "TERMUX_VERSION", "TERM")}
    base.update(kw)
    return mock.patch.dict(os.environ, base, clear=True)


class ColorCase(unittest.TestCase):
    def setUp(self):
        C.set_enabled(None)
        C.reload_config()
        p = mock.patch.object(C, "_config", lambda: ("auto", "auto"))
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(C.set_enabled, None)


class TestOnOffRules(ColorCase):
    def test_auto_follows_the_terminal(self):
        with env(TERM="xterm-256color"):
            self.assertTrue(C.enabled(TTY()))
            self.assertFalse(C.enabled(Pipe()))
            self.assertFalse(C.enabled(object()))   # no isatty at all

    def test_no_color_turns_it_off_even_on_a_terminal(self):
        with env(NO_COLOR="1", TERM="xterm"):
            self.assertFalse(C.enabled(TTY()))
        with env(NO_COLOR="", TERM="xterm"):       # empty NO_COLOR is ignored (no-color.org)
            self.assertTrue(C.enabled(TTY()))

    def test_nimlab_color_wins_over_everything_but_the_flag(self):
        with env(NIMLAB_COLOR="0", FORCE_COLOR="1"):
            self.assertFalse(C.enabled(TTY()))
        with env(NIMLAB_COLOR="1", NO_COLOR="1"):
            self.assertTrue(C.enabled(Pipe()))
        with env(NIMLAB_COLOR="off"):
            C.set_enabled(True)
            self.assertTrue(C.enabled(Pipe()))

    def test_force_color_turns_it_on_for_pipes(self):
        with env(FORCE_COLOR="1"):
            self.assertTrue(C.enabled(Pipe()))
        with env(FORCE_COLOR="0"):
            self.assertFalse(C.enabled(TTY()))

    def test_term_dumb_is_off(self):
        with env(TERM="dumb"):
            self.assertFalse(C.enabled(TTY()))

    def test_config_setting(self):
        for value, tty, want in (("off", TTY(), False), ("on", Pipe(), True), ("auto", TTY(), True)):
            with env(TERM="xterm"), mock.patch.object(C, "_config", lambda v=value: (v, "auto")):
                self.assertEqual(C.enabled(tty), want, value)
        # NO_COLOR still beats ui_settings.color=on
        with env(NO_COLOR="1"), mock.patch.object(C, "_config", lambda: ("on", "auto")):
            self.assertFalse(C.enabled(TTY()))

    def test_flags_are_removed_and_applied(self):
        with env():
            argv = ["serve", "--no-color", "info"]
            C.apply_flags(argv)
            self.assertEqual(argv, ["serve", "info"])
            self.assertEqual(os.environ["NIMLAB_COLOR"], "0")
            self.assertFalse(C.enabled(TTY()))
            argv = ["--color"]
            C.apply_flags(argv)
            self.assertEqual(argv, [])
            self.assertTrue(C.enabled(Pipe()))

    def test_helpers_return_plain_text_when_off(self):
        C.set_enabled(False)
        for fn in (C.ok, C.warn, C.err, C.dim, C.model, C.value, C.url, C.key, C.path, C.entity, C.reply,
                   C.you, C.status, C.http, C.latency, C.role, C.header, C.gradient):
            self.assertEqual(fn("200"), "200", fn.__name__)
        self.assertEqual(C.item(3, "Label", extra="  (hint)"), "3. Label  (hint)")
        self.assertEqual(C.rule(10), "-" * 10)
        self.assertEqual(C.prompt("YOU > ", "you"), "YOU > ")
        self.assertEqual(C.hl("Base URL: http://x/v1 PASS 1.2s"), "Base URL: http://x/v1 PASS 1.2s")
        self.assertEqual(C.note("[Stored as m1]"), "[Stored as m1]")


class TestDepth(ColorCase):
    def test_depth_detection(self):
        with env(TERMUX_VERSION="0.118"):
            self.assertEqual(C.depth(), 24)
        with env(COLORTERM="truecolor"):
            self.assertEqual(C.depth(), 24)
        with env(TERM="xterm-256color"):
            self.assertEqual(C.depth(), 256)
        with env(TERM="vt100"):
            self.assertEqual(C.depth(), 16)
        with env(TERMUX_VERSION="1", NIMLAB_COLOR_DEPTH="256"):
            self.assertEqual(C.depth(), 256)

    def test_codes_per_depth(self):
        self.assertEqual(C.fg_code((255, 85, 100), 24), "38;2;255;85;100")
        self.assertTrue(C.fg_code((255, 85, 100), 256).startswith("38;5;"))
        self.assertIn(C.fg_code((255, 85, 100), 16), ("91", "31"))
        self.assertEqual(C.rgb_to_256((255, 0, 0)), 196)
        self.assertEqual(C.rgb_to_256((0, 0, 0)), 16)

    def test_palette_is_readable_on_black(self):
        # no colour of the palette, the roles, the menu or the banners is
        # too dark for a black background (relative luminance)
        def lum(rgb):
            def ch(c):
                c = c / 255
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            r, g, b = (ch(c) for c in rgb)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        colours = list(C.PALETTE.values()) + list(C.ROLE_RGB.values()) + C.MENU_RGB + C.BANNER + C.ENTITY
        for rgb in colours:
            contrast = (lum(rgb) + 0.05) / 0.05
            self.assertGreaterEqual(contrast, 4.5, rgb)

    def test_every_role_has_its_own_colour(self):
        keys = [d.key for d in R.ROLE_DEFS]
        self.assertEqual(len(keys), 16)
        cols = [C.ROLE_RGB[k] for k in keys]
        self.assertEqual(len(set(cols)), 16)
        # a role is found by key and by its label
        for d in R.ROLE_DEFS:
            self.assertEqual(C.role_key(d.key), d.key)
            self.assertEqual(C.role_key(d.name), d.key)


class TestWidth(ColorCase):
    def setUp(self):
        super().setUp()
        C.set_enabled(True)

    def test_strip_and_visible_length(self):
        s = C.ok("PASS") + " " + C.gradient("HELLO") + C.role("persona", "Persona")
        self.assertIn(ESC, s)
        self.assertEqual(C.strip(s), "PASS HELLOPersona")
        self.assertEqual(C.vlen(s), len("PASS HELLOPersona"))
        self.assertEqual(C.vlen(C.ljust(C.model("a/b"), 10)), 10)
        self.assertEqual(C.vlen(C.rjust(C.http(404), 6)), 6)
        self.assertEqual(C.vlen(C.center(C.value("x"), 5)), 5)
        self.assertEqual(C.strip(C.prompt("YOU > ", "you", typed="you_text")), "YOU > ")

    def test_menu_items_line_up(self):
        items = [C.item(f"{n:>2}", f"{'Label ' + str(n):<20}") + " : x" for n in range(1, 18)]
        self.assertEqual(len({C.vlen(i) for i in items}), 1)
        self.assertEqual({i.index(":") for i in map(C.strip, items)}, {25})
        self.assertEqual(C.strip(C.item(3, "Label", extra="  (hint)")), "3. Label  (hint)")

    def test_role_lines_line_up_with_colour(self):
        from nimlab import rolemenu
        roles = {"persona": "meta/llama-3.3-70b-instruct", "vision": {"backend": "mcp", "tool": "describe"}}
        coloured = rolemenu.role_lines(roles)
        C.set_enabled(False)
        plain = rolemenu.role_lines(roles)
        self.assertEqual([C.strip(x) for x in coloured], plain)
        self.assertTrue(any(ESC in x for x in coloured))

    def test_nested_paint_keeps_the_outer_colour(self):
        inner = C.model("a/b")
        outer = C.paint("x " + inner + " y", "warn")
        self.assertEqual(C.strip(outer), "x a/b y")
        # after the inner reset, the outer colour comes back
        self.assertIn(C.RESET + C.sgr("warn"), outer)


class TestSemanticColours(ColorCase):
    def setUp(self):
        super().setUp()
        C.set_enabled(True)
        self.d = mock.patch.dict(os.environ, {"NIMLAB_COLOR_DEPTH": "24"})
        self.d.start()
        self.addCleanup(self.d.stop)

    def code(self, name):
        return C.fg_code(C.PALETTE[name])

    def test_http_by_class(self):
        self.assertIn(self.code("ok"), C.http(200))
        self.assertIn(self.code("http3"), C.http(302))
        self.assertIn(self.code("http4"), C.http(404))
        self.assertIn(self.code("err"), C.http(503))

    def test_status_and_latency(self):
        self.assertIn(self.code("ok"), C.status("PASS"))
        self.assertIn(self.code("err"), C.status("FAIL"))
        self.assertIn(self.code("warn"), C.status("SKIP"))
        self.assertIn(self.code("lat_fast"), C.latency("340 ms"))
        self.assertIn(self.code("lat_mid"), C.latency("2.5s"))
        self.assertIn(self.code("lat_crawl"), C.latency("12.1s"))

    def test_roles_have_their_colour_everywhere(self):
        want = C.fg_code(C.ROLE_RGB["vision"])
        self.assertIn(want, C.role("vision"))
        self.assertIn(want, C.role("Multimodal Vision-Language Model (VLM)"))
        self.assertIn(want, C.hl("[route -> Multimodal Vision-Language Model (VLM) | a/b | image]"))
        self.assertIn(C.fg_code(C.ROLE_RGB["tts"]), C.hl("testbed-tts"))

    def test_you_and_entity_differ(self):
        self.assertNotEqual(C.sgr("you"), C.sgr("reply"))
        self.assertNotIn(C.fg_code(C.PALETTE["you"]), C.entity("QUILL"))

    def test_highlighter(self):
        line = C.hl("Base URL: http://127.0.0.1:8765/v1  key ...abcd  meta/llama-3.1-8b  [PASS] HTTP 404 1.2s")
        self.assertEqual(C.strip(line),
                         "Base URL: http://127.0.0.1:8765/v1  key ...abcd  meta/llama-3.1-8b  [PASS] HTTP 404 1.2s")
        for name in ("label", "url", "key", "model", "ok", "http4"):
            self.assertIn(self.code(name), line, name)
        # menus: number and label coloured, text unchanged
        m = C.hl(" 2. Set MCP Server URL          : http://x")
        self.assertEqual(C.strip(m), " 2. Set MCP Server URL          : http://x")
        self.assertIn(C.fg_code(C.menu_rgb(2)), m)
        # plain words are left alone
        self.assertEqual(C.hl("just a sentence."), "just a sentence.")

    def test_colorize_leaves_json_alone(self):
        doc = json.dumps({"url": "http://x/v1", "status": "PASS"}, indent=2)
        self.assertEqual(C.colorize(doc), doc)
        self.assertEqual(C.colorize("[1, 2]"), "[1, 2]")
        self.assertEqual(C.colorize("42"), "42")
        self.assertIn(ESC, C.colorize("OPENAI-COMPATIBLE TEST SERVER  [stopped]"))


class TestStreams(ColorCase):
    def test_cprint_only_colours_terminals(self):
        with env(TERM="xterm"):
            tty, pipe = TTY(), Pipe()
            C.cprint("[PASS] chat 1.2s", file=tty)
            C.cprint("[PASS] chat 1.2s", file=pipe)
            self.assertIn(ESC, tty.getvalue())
            self.assertEqual(pipe.getvalue(), "[PASS] chat 1.2s\n")

    def test_install_wraps_only_terminals(self):
        with env(TERM="xterm"), mock.patch.object(sys, "stdout", Pipe()):
            self.assertEqual(C.install("stdout"), [])
            print("[PASS] x")
            self.assertEqual(sys.stdout.getvalue(), "[PASS] x\n")
        tty = TTY()
        with env(TERM="xterm"), mock.patch.object(sys, "stdout", tty):
            self.assertEqual(C.install("stdout"), ["stdout"])
            print("[PASS] x")
            print(json.dumps({"a": "PASS"}))
        out = tty.getvalue().splitlines()
        self.assertIn(ESC, out[0])
        self.assertEqual(out[1], '{"a": "PASS"}')

    def test_cli_output_piped_has_no_escape_codes(self):
        e = {k: v for k, v in os.environ.items() if k not in ("NIMLAB_COLOR", "FORCE_COLOR")}
        e["TERMUX_VERSION"] = "1"
        for args in (["colors"], ["status", "roles"], ["mcp", "show"], ["serve", "settings"]):
            r = subprocess.run([sys.executable, "-m", "nimlab"] + args, cwd=ROOT, env=e, capture_output=True,
                               text=True, timeout=60)
            self.assertEqual(r.returncode, 0, (args, r.stderr))
            self.assertNotIn(ESC, r.stdout + r.stderr, args)

    def test_cli_forced_colour_and_no_color_flag(self):
        e = dict(os.environ, NIMLAB_COLOR="1", NIMLAB_COLOR_DEPTH="256")
        r = subprocess.run([sys.executable, "-m", "nimlab", "colors"], cwd=ROOT, env=e, capture_output=True,
                           text=True, timeout=60)
        self.assertIn("\x1b[38;5;", r.stdout)
        e.pop("NIMLAB_COLOR")
        e["FORCE_COLOR"] = "1"
        r = subprocess.run([sys.executable, "-m", "nimlab", "--no-color", "colors"], cwd=ROOT, env=e,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(ESC, r.stdout)


class TestNothingLeaksOffScreen(ColorCase):
    """With colour forced on, server replies, the request log and saved
    files stay plain."""

    def test_server_replies_and_log_are_plain(self):
        from tests.test_server import ServerCase, wait_log
        from nimlab import server as S

        class Case(ServerCase):
            def runTest(self):
                pass
        case = Case()
        C.set_enabled(True)
        with mock.patch.dict(os.environ, {"NIMLAB_COLOR": "1", "FORCE_COLOR": "1"}):
            case.setUp()
            try:
                case.settings["log_to_console"] = True
                err = io.StringIO()
                with mock.patch.object(sys, "stderr", err):
                    bodies = [case.call("/models")[2],
                              case.call("/chat/completions", {"model": "testbed",
                                                              "messages": [{"role": "user", "content": "hi"}]})[2],
                              case.call("/chat/completions", {"model": "testbed", "stream": True,
                                                              "messages": [{"role": "user", "content": "hi"}]})[2],
                              case.call("/models", key="sk-testbed-wrongwrongwrongwrong")[2],
                              case.call("/call?t=nope")[2]]
                    wait_log(5)
                for b in bodies:
                    self.assertNotIn(b"\x1b", b)
                with open(S.log_path(), encoding="utf-8") as f:
                    self.assertNotIn(ESC, f.read())
                # the console line (the screen, forced on here) is coloured but
                # says the same as the saved log
                self.assertIn("[serve]", C.strip(err.getvalue()))
                self.assertIn(ESC, err.getvalue())
            finally:
                for fn, args, kw in reversed(case._cleanups):
                    fn(*args, **kw)
                case._cleanups.clear()

    def test_coloured_log_lines_strip_to_the_plain_ones(self):
        from nimlab import server as S
        C.set_enabled(True)
        rows = [{"ts": "2026-11-12T10:00:00", "status": 200, "method": "POST", "path": "/v1/chat/completions",
                 "model": "testbed", "latency_ms": 340},
                {"ts": "2026-11-12T10:00:01", "status": 503, "method": "GET", "path": "/v1/models",
                 "model": None, "latency_ms": 12000, "error": "boom"}]
        plain = S.format_log(rows)
        coloured = S.format_log(rows, color=True)
        self.assertTrue(all(ESC not in x for x in plain))
        self.assertTrue(all(ESC in x for x in coloured))
        self.assertEqual([C.strip(x) for x in coloured], plain)

    def test_saved_config_is_plain(self):
        import tempfile
        from nimlab import config
        C.set_enabled(True)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.json")
            config.save_json(path, {"label": C.strip(C.role("persona", "Persona")), "ui_settings": {"color": "on"}})
            with open(path, encoding="utf-8") as f:
                self.assertNotIn(ESC, f.read())


class TestStartShColours(unittest.TestCase):
    def run_sh(self, extra_env, *args):
        e = {k: v for k, v in os.environ.items() if k not in ("NIMLAB_COLOR", "NO_COLOR", "FORCE_COLOR")}
        e.update(extra_env)
        e["NIMLAB_DATA_DIR"] = os.environ.get("NIMLAB_DATA_DIR") or os.path.join(ROOT, "data")
        return subprocess.run(["bash", os.path.join(ROOT, "start.sh")] + list(args), input="0\n", cwd=ROOT,
                              env=e, capture_output=True, text=True, timeout=60)

    def test_dashboard_plain_when_piped_and_with_no_color(self):
        from tests.helpers import fresh_store
        with fresh_store():
            for extra, args in (({}, ()), ({"NO_COLOR": "1", "FORCE_COLOR": "1"}, ()),
                                ({"FORCE_COLOR": "1"}, ("--no-color",))):
                r = self.run_sh(extra, *args)
                body = r.stdout.replace("\x1b[H\x1b[2J\x1b[3J", "").replace("\x1b[H\x1b[2J", "")
                self.assertIn("NVIDIA NIM TEST LAB", body, r.stderr)
                self.assertNotIn("\x1b[38", body, (extra, args))
                self.assertIn("   7. Keys & MCP", body)

    def test_dashboard_coloured_when_forced(self):
        from tests.helpers import fresh_store
        with fresh_store():
            r = self.run_sh({"NIMLAB_COLOR": "1", "NIMLAB_COLOR_DEPTH": "256"})
            self.assertIn("\x1b[38;5;", r.stdout)
            self.assertIn("Keys & MCP", C.strip(r.stdout))


if __name__ == "__main__":
    unittest.main()
