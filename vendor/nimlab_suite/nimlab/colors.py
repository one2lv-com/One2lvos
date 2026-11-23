"""Terminal colours for everything the lab prints to a screen.

One module, one palette. Every helper returns the text unchanged when colour
is off, so the same code path prints plain text into pipes, files, logs and
tests.

When colour is on (first rule that matches wins):
  1. set_enabled(True/False) in this process (the --color / --no-color flags)
  2. NIMLAB_COLOR=0/off  -> off;  NIMLAB_COLOR=1/on -> on
  3. NO_COLOR set (any non-empty value) -> off   (https://no-color.org)
  4. FORCE_COLOR set (not 0/false) -> on
  5. config_cluster.json ui_settings.color: "on" / "off" ("auto" = next rule)
  6. TERM=dumb -> off, else on only when the stream is a terminal

Colour depth: truecolor in Termux (TERMUX_VERSION) or with
COLORTERM=truecolor/24bit, else 256 colours, else the 16 bright ANSI
colours. NIMLAB_COLOR_DEPTH=24|256|16 or ui_settings.color_depth overrides.
Colours are picked for a dark background: no dark blue, no black.

Widths: vlen()/ljust()/rjust() measure visible characters only, so tables
line up with or without escape codes. strip() removes them again.
"""

import os
import re
import shutil
import sys

RESET = "\033[0m"
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|[\x01\x02]")

_override = None          # set_enabled()
_cfg_cache = None         # (color, depth) from config_cluster.json


# ---------------------------------------------------------------------------
# On / off and depth
# ---------------------------------------------------------------------------
def set_enabled(value):
    """True / False forces colour for this process; None goes back to auto."""
    global _override
    _override = value


def reload_config():
    global _cfg_cache
    _cfg_cache = None


def _config():
    global _cfg_cache
    if _cfg_cache is None:
        color, depth = "auto", "auto"
        try:
            from . import config
            ui = (config.load_json(config.CLUSTER_CONFIG, {}) or {}).get("ui_settings") or {}
            color = str(ui.get("color", "auto")).strip().lower() or "auto"
            depth = str(ui.get("color_depth", "auto")).strip().lower() or "auto"
        except Exception:  # noqa: BLE001 - colour never breaks the program
            pass
        _cfg_cache = (color, depth)
    return _cfg_cache


_ON = ("1", "on", "yes", "true", "always", "force")
_OFF = ("0", "off", "no", "false", "never")


def policy(env=None):
    """'on', 'off' or 'auto' (= colour only on a terminal), from the flag,
    environment and config; the terminal check itself is not done here."""
    env = os.environ if env is None else env
    if _override is not None:
        return "on" if _override else "off"
    v = str(env.get("NIMLAB_COLOR", "")).strip().lower()
    if v in _OFF:
        return "off"
    if v in _ON:
        return "on"
    if env.get("NO_COLOR", "") != "":
        return "off"
    fc = env.get("FORCE_COLOR")
    if fc is not None:
        return "off" if fc.strip().lower() in ("0", "false", "no") else "on"
    c = _config()[0]
    if c in _OFF or c == "off":
        return "off"
    if c in _ON or c == "on":
        return "on"
    if env.get("TERM", "") == "dumb":
        return "off"
    return "auto"


_forcing = []   # colorize() for a stream known to want colour


def enabled(stream=None):
    if _forcing:
        return True
    p = policy()
    if p != "auto":
        return p == "on"
    stream = sys.stdout if stream is None else stream
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def depth(env=None):
    env = os.environ if env is None else env
    v = str(env.get("NIMLAB_COLOR_DEPTH", "") or _config()[1]).strip().lower()
    if v in ("24", "24bit", "truecolor", "true", "rgb"):
        return 24
    if v == "256":
        return 256
    if v in ("16", "8", "basic"):
        return 16
    if env.get("COLORTERM", "").lower() in ("truecolor", "24bit") or env.get("TERMUX_VERSION"):
        return 24
    term = env.get("TERM", "")
    if "256" in term or term.startswith(("xterm", "screen", "tmux", "rxvt", "alacritty", "kitty")):
        return 256
    return 16


# ---------------------------------------------------------------------------
# Text measuring
# ---------------------------------------------------------------------------
def strip(text):
    return ANSI_RE.sub("", text) if isinstance(text, str) else text


def vlen(text):
    return len(strip(str(text)))


def clip(text, width):
    """Cut a (possibly coloured) string to `width` visible characters,
    ending in '...' when cut, keeping colour codes balanced."""
    if width <= 0 or vlen(text) <= width:
        return text
    out, seen, i = [], 0, 0
    while i < len(text) and seen < width - 3:
        m = ANSI_RE.match(text, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        out.append(text[i])
        seen += 1
        i += 1
    return "".join(out) + (RESET if enabled() else "") + "..."


def ljust(text, width):
    text = str(text)
    return text + " " * max(0, width - vlen(text))


def rjust(text, width):
    text = str(text)
    return " " * max(0, width - vlen(text)) + text


def center(text, width):
    text = str(text)
    pad = max(0, width - vlen(text))
    return " " * (pad // 2) + text + " " * (pad - pad // 2)


# ---------------------------------------------------------------------------
# Colour codes
# ---------------------------------------------------------------------------
_CUBE = (0, 95, 135, 175, 215, 255)
# the 16-colour fallback: bright and normal colours readable on black only
_BASIC = {91: (255, 85, 85), 92: (85, 255, 85), 93: (255, 255, 85), 94: (110, 140, 255), 95: (255, 85, 255),
          96: (85, 255, 255), 97: (255, 255, 255), 31: (205, 49, 49), 32: (13, 188, 121), 33: (229, 229, 16),
          35: (188, 63, 188), 36: (17, 168, 205), 37: (229, 229, 229), 90: (128, 128, 128)}


def _dist(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def rgb_to_256(rgb):
    idx = [min(range(6), key=lambda i: abs(_CUBE[i] - c)) for c in rgb]
    cube = tuple(_CUBE[i] for i in idx)
    gray_level = max(0, min(23, round((sum(rgb) / 3 - 8) / 10)))
    gray = (8 + 10 * gray_level,) * 3
    if _dist(gray, rgb) < _dist(cube, rgb):
        return 232 + gray_level
    return 16 + 36 * idx[0] + 6 * idx[1] + idx[2]


def rgb_to_16(rgb):
    return min(_BASIC, key=lambda k: _dist(_BASIC[k], rgb))


def fg_code(rgb, d=None):
    d = d or depth()
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    if d == 24:
        return f"38;2;{r};{g};{b}"
    if d == 256:
        return f"38;5;{rgb_to_256((r, g, b))}"
    return str(rgb_to_16((r, g, b)))


_ATTR = {"bold": "1", "dim": "2", "italic": "3", "underline": "4"}


def sgr(*spec):
    """Escape sequence for a spec: RGB tuples, palette names, attributes."""
    parts = []
    for s in spec:
        if s is None:
            continue
        if isinstance(s, str) and s in _ATTR:
            parts.append(_ATTR[s])
        elif isinstance(s, str) and s in PALETTE:
            parts.append(fg_code(PALETTE[s]))
        elif isinstance(s, tuple):
            parts.append(fg_code(s))
    return "\033[" + ";".join(parts) + "m" if parts else ""


def paint(text, *spec, on=None):
    """text in the given colour/attributes, or unchanged when colour is off."""
    text = "" if text is None else str(text)
    if not text or not (enabled() if on is None else on):
        return text
    code = sgr(*spec)
    if not code:
        return text
    # keep the colour after any reset inside the text (nested paint)
    return code + text.replace(RESET, RESET + code) + RESET


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def tint(rgb, t=0.45):
    """A lighter version of a colour (towards white)."""
    return mix(rgb, (255, 255, 255), t)


# ---------------------------------------------------------------------------
# Palette (dark background)
# ---------------------------------------------------------------------------
PALETTE = {
    "ok": (80, 250, 123),
    "warn": (255, 210, 70),
    "err": (255, 85, 100),
    "dim": (140, 144, 160),
    "hint": (165, 160, 190),
    "model": (125, 215, 255),
    "value": (255, 236, 150),
    "url": (100, 200, 255),
    "key": (175, 175, 190),
    "path": (200, 190, 230),
    "label": (180, 195, 255),
    "number": (255, 170, 90),
    "you": (0, 255, 175),
    "you_text": (190, 255, 230),
    "reply": (238, 228, 255),
    "accent": (255, 120, 220),
    "info": (120, 230, 255),
    "http3": (120, 220, 255),
    "http4": (255, 170, 60),
    "lat_fast": (80, 250, 123),
    "lat_mid": (255, 230, 90),
    "lat_slow": (255, 150, 60),
    "lat_crawl": (255, 85, 100),
}

# one colour per role, everywhere the role appears
ROLE_RGB = {
    "intent_router": (255, 145, 0),      # orange
    "persona": (255, 95, 255),           # magenta
    "reasoning": (185, 145, 255),        # lavender
    "coding": (60, 255, 140),            # green
    "vision": (70, 175, 255),            # azure
    "ocr": (255, 222, 90),               # gold
    "chart_parser": (255, 175, 130),     # peach
    "video": (255, 95, 95),              # coral
    "asr": (110, 255, 255),              # aqua
    "omni_audio": (215, 120, 255),       # orchid
    "tts": (255, 150, 185),              # rose
    "image_gen": (195, 255, 80),         # lime
    "audio_gen": (0, 225, 190),          # teal
    "embedding": (150, 175, 255),        # periwinkle
    "reranker": (235, 230, 150),         # cream
    "guard_translate": (255, 120, 150),  # raspberry
    "compactor": (180, 180, 190),
}

# menu numbers cycle through a rainbow; labels use a lighter tint of the same hue
MENU_RGB = [(255, 95, 135), (255, 165, 40), (255, 230, 70), (110, 255, 120), (0, 235, 220), (100, 175, 255),
            (185, 135, 255), (255, 115, 245)]

BANNER = [(0, 255, 200), (70, 170, 255), (190, 110, 255), (255, 90, 190), (255, 175, 60)]
ENTITY = [(255, 95, 255), (255, 140, 160), (255, 190, 90)]
RULE_STOPS = [(0, 200, 255), (175, 110, 255), (255, 90, 180)]


# ---------------------------------------------------------------------------
# Semantic helpers
# ---------------------------------------------------------------------------
def ok(t):
    return paint(t, "ok", "bold")


def warn(t):
    return paint(t, "warn")


def err(t):
    return paint(t, "err", "bold")


def dim(t):
    return paint(t, "dim")


def hint(t):
    return paint(t, "hint", "italic")


def bold(t):
    return paint(t, "bold")


def model(t):
    return paint(t, "model")


def value(t):
    return paint(t, "value", "bold")


def url(t):
    return paint(t, "url", "underline")


def key(t):
    """A masked secret."""
    return paint(t, "key")


def path(t):
    return paint(t, "path", "italic")


def label(t):
    return paint(t, "label", "bold")


def info(t):
    return paint(t, "info")


def onoff(v, on_word=None, off_word=None):
    """A boolean setting: on in green, off in grey."""
    word = (on_word if v else off_word) or str(v)
    return paint(word, "ok", "bold") if v else paint(word, "dim")


def status(word):
    """PASS / FAIL / SKIP and friends."""
    w = str(word)
    u = strip(w).strip("[] ").upper()
    if u in ("PASS", "OK", "ALLOWED", "LIVE_200", "YES", "ON", "RUNNING", "SET", "DONE", "SAVED"):
        return ok(w)
    if u in ("FAIL", "FAILED", "ERROR", "BLOCKED", "X", "NO", "NOT SET", "DENIED", "REJECTED"):
        return err(w)
    if u in ("SKIP", "WARN", "WARNING", "!", "PARTIAL", "STOPPED", "STALE"):
        return warn(w)
    return dim(w)


def http(code):
    """An HTTP status coloured by class."""
    s = str(code)
    try:
        n = int(strip(s).strip())
    except ValueError:
        return dim(s)
    if 200 <= n < 300:
        return paint(s, "ok", "bold")
    if 300 <= n < 400:
        return paint(s, "http3")
    if 400 <= n < 500:
        return paint(s, "http4", "bold")
    if n >= 500:
        return paint(s, "err", "bold")
    return dim(s)


def latency(text, seconds=None):
    """A latency, green when quick, through yellow and orange to red."""
    s = str(text)
    if seconds is None:
        m = re.search(r"(\d+(?:\.\d+)?)\s?(ms|s)\b", strip(s))
        if not m:
            try:
                seconds = float(strip(s))
            except ValueError:
                return dim(s)
        else:
            seconds = float(m.group(1)) / (1000.0 if m.group(2) == "ms" else 1.0)
    name = ("lat_fast" if seconds < 1.5 else "lat_mid" if seconds < 4 else "lat_slow" if seconds < 10
            else "lat_crawl")
    return paint(s, name)


def role_key(name):
    """Role key for a key or a display label (any case), else None."""
    if not name:
        return None
    n = strip(str(name)).strip()
    if n in ROLE_RGB:
        return n
    k = n.lower().replace("-", "_")
    if k in ROLE_RGB:
        return k
    return _label_map().get(n.lower())


_LABELS = None


def _label_map():
    global _LABELS
    if _LABELS is None:
        try:
            from . import roles as R
            _LABELS = {d.name.lower(): d.key for d in R.ROLE_DEFS}
            _LABELS.update({v.lower(): k for k, v in R.EXTRA_ROLES.items()})
        except Exception:  # noqa: BLE001
            _LABELS = {}
    return _LABELS


def role_rgb(name):
    return ROLE_RGB.get(role_key(name) or "", PALETTE["label"])


def role(name, text=None, bold_=True):
    """A role (key or label) in its own colour; text defaults to name."""
    return paint(name if text is None else text, role_rgb(name), "bold" if bold_ else None)


def menu_rgb(i):
    return MENU_RGB[i % len(MENU_RGB)]


def item(num, text, i=None, extra=""):
    """One menu entry: '<num>. <text><extra>' with the number and label in
    their own colour (cycling by position i) and extra (a hint) dimmed.
    Plain text is exactly f'{num}. {text}{extra}'."""
    if not enabled():
        return f"{num}. {text}{extra}"
    if i is None:
        s = str(num).strip()
        i = int(s) if s.isdigit() else sum(map(ord, s))
    c = menu_rgb(i)
    lead = len(str(num)) - len(str(num).lstrip())
    return (" " * lead + paint(str(num).lstrip() + ".", c, "bold") + " " + paint(text, tint(c, 0.5)) +
            (hint(extra) if extra.strip() else extra))


def entry(num, name, extra="", pad=18):
    """One line of a grouped menu, laid out like the launcher's:
    '  <num right-aligned in 2>. <name padded> <hint>'. The hint is dropped
    when the line would be wider than the screen (a phone in Termux)."""
    extra = str(extra or "")
    if extra and 4 + 2 + pad + 2 + len(extra) > screen_width():
        extra = ""
    label = f"{name:<{pad}}" if extra else str(name)
    return "  " + item(f"{str(num):>2}", label, extra=("  " + extra) if extra else "")


def gradient(text, stops=None, bold_=True, on=None):
    """Each character in a colour along the stops (left to right)."""
    text = "" if text is None else str(text)
    if not text or not (enabled() if on is None else on):
        return text
    stops = stops or BANNER
    n = len(text)
    out = []
    last = None
    for i, ch in enumerate(text):
        if ch == " ":
            out.append(ch)
            continue
        t = i / max(1, n - 1) * (len(stops) - 1)
        j = min(int(t), len(stops) - 2) if len(stops) > 1 else 0
        rgb = mix(stops[j], stops[j + 1], t - j) if len(stops) > 1 else stops[0]
        code = sgr(rgb, "bold" if bold_ else None)
        if code != last:
            out.append(code)
            last = code
        out.append(ch)
    return "".join(out) + RESET


def screen_width(cap=70, floor=36):
    """Terminal columns, capped at 70 (the classic layout) so menus fit a
    phone screen in Termux without wrapping. Uses COLUMNS, then the
    terminal, else the cap."""
    try:
        cols = shutil.get_terminal_size((cap, 24)).columns
    except (OSError, ValueError):
        cols = cap
    return max(floor, min(cap, cols))


def rule(width=None, plain="-", fancy="─", stops=None):
    """A separator: plain characters when colour is off, a gradient line on.
    Default width: screen_width()."""
    width = screen_width() if width is None else width
    if not enabled():
        return plain * width
    return gradient(fancy * width, stops or RULE_STOPS, bold_=False)


def box(lines, width=None, stops=None):
    """A double-line box with a gradient frame around centred lines
    (lines may already be coloured). Only used when colour is on."""
    width = screen_width() if width is None else width
    stops = stops or BANNER
    inner = width - 2
    out = [gradient("╔" + "═" * inner + "╗", stops, bold_=False)]
    for ln in lines:
        out.append(paint("║", stops[0]) + center(ln, inner) + paint("║", stops[-1]))
    out.append(gradient("╚" + "═" * inner + "╝", stops, bold_=False))
    return out


def header(title, width=70):
    """A section title line: '▌ TITLE' in a gradient."""
    if not enabled():
        return title
    return paint("▌", BANNER[0], "bold") + " " + gradient(title, BANNER[1:], bold_=True)


def section(title):
    """A sub-heading inside a screen."""
    return paint(title, "accent", "bold")


def entity(name):
    """The entity's name in chat (a warm magenta-to-amber gradient)."""
    return gradient(name, ENTITY, bold_=True)


def reply(text):
    return paint(text, "reply")


def you(text="YOU"):
    return paint(text, "you", "bold")


def you_text(text):
    return paint(text, "you_text")


# ---------------------------------------------------------------------------
# Input prompts
# ---------------------------------------------------------------------------
def _rl(code):
    # readline must be told which characters take no space, or line editing
    # misplaces the cursor
    return f"\001{code}\002" if "readline" in sys.modules else code


def prompt(text, *spec, typed=None):
    """An input() prompt in colour; typed (a spec) colours what the user
    types until done_input() resets it. Plain text when colour is off."""
    if not enabled():
        return text
    lead = text[:len(text) - len(text.lstrip("\n"))]
    body = text[len(lead):]
    s = lead + _rl(sgr(*spec)) + body + _rl(RESET)
    if typed:
        s += _rl(sgr(*typed) if isinstance(typed, (tuple, list)) else sgr(typed))
    return s


def done_input():
    """Reset the typed-text colour after an input() with prompt(typed=...)."""
    if enabled():
        try:
            sys.stdout.write(RESET)
            sys.stdout.flush()
        except (OSError, ValueError):
            pass


def ask(text="Selection: "):
    """The standard menu prompt."""
    return prompt(text, "accent", "bold", typed="value")


def cinput(text=""):
    """input() with the prompt in the menu-prompt colour (drop-in)."""
    try:
        return input(ask(text) if text else "")
    finally:
        done_input()


def read(text="Selection: ", input_fn=None):
    """input() with the standard prompt and colour reset afterwards."""
    fn = input_fn or input
    try:
        return fn(ask(text))
    finally:
        done_input()


# ---------------------------------------------------------------------------
# Highlighter for text built elsewhere (server blocks, logs shown on screen,
# the older scripts' output)
# ---------------------------------------------------------------------------
_FILE_EXT = re.compile(r"\.(json|jsonl|md|py|sh|wav|png|jpe?g|mp3|m4a|ogg|txt|zip|html|csv|pdf|log|env)$", re.I)
_ROLE_ALT = None


def _role_alt():
    global _ROLE_ALT
    if _ROLE_ALT is None:
        try:
            from . import roles as R
            names = [d.name for d in R.ROLE_DEFS] + list(R.EXTRA_ROLES.values())
        except Exception:  # noqa: BLE001
            names = []
        names += [k for k in ROLE_RGB if "_" in k]
        labels = sorted(set(names), key=len, reverse=True)
        _ROLE_ALT = "|".join(re.escape(x) for x in labels) or r"(?!x)x"
    return _ROLE_ALT


_HL = None


def _hl_re():
    global _HL
    if _HL is None:
        _HL = re.compile("|".join([
            r"(?P<menu>^\s*(?:\d{1,2}|[A-Za-z])\.[ \t]+[^\n(\[:\x1b]*[^\s(\[:\x1b])",
            r"(?P<lab>^\s*[A-Z][A-Za-z0-9 ./()&'+-]{0,30}:)(?=\s)",
            r"(?P<bool>(?<=: )(?:True|False|None|on|off)(?=\s*(?:$|\(|,|;)))",
            r"(?P<url>\b(?:https?|wss?)://[^\s'\"<>)\]]+)",
            r"(?P<skey>\bsk-[A-Za-z0-9_-]{12,})",
            r"(?P<mask>(?:\b[A-Za-z]+-)?\.\.\.[A-Za-z0-9]{4}\b|\*{4,})",
            r"(?P<good>\[(?:ok|OK|PASS|pass|done)\]|\bPASS(?:ED)?\b|\bLIVE_200\b|\bALLOWED\b|\[running\]|\b200 OK\b)",
            r"(?P<bad>\[x\]|\[ERROR\]|\[error\]|\bFAIL(?:ED)?\b|\bERROR\b|\bBLOCKED\b|\[NOT SET\]|\bNOT SET\b|"
            r"\[failed\]|\bError:)",
            r"(?P<meh>\[!\]|\[SKIP\]|\bSKIP\b|\bWARN(?:ING)?\b|\bNOTICE\b|\[stopped\]|\bNote:|\bWarning:)",
            r"(?P<http>(?<=HTTP )\d{3}\b|(?<=status )\d{3}\b)",
            r"(?P<lat>\b\d+(?:\.\d+)?\s?(?:ms|s)\b)",
            r"(?P<role>\b(?:" + _role_alt() + r")(?![\w-]))",
            r"(?P<tb>\btestbed-[a-z_]+\b)",
            r"(?P<mid>(?<![/\w.:-])[a-z0-9][a-z0-9_.-]*/[A-Za-z0-9][\w.:+-]*[\w])",
        ]), re.M)
    return _HL


def _hl_sub(m):
    g = m.lastgroup
    t = m.group(0)
    if g == "menu":
        m2 = re.match(r"(\s*)(\S+)\.(\s+)(.*)$", t)
        n = m2.group(2)
        i = int(n) if n.isdigit() else sum(map(ord, n))
        c = menu_rgb(i)
        return m2.group(1) + paint(n + ".", c, "bold") + m2.group(3) + paint(m2.group(4), tint(c, 0.5))
    if g == "lab":
        return label(t)
    if g == "bool":
        return onoff(t in ("True", "on", "yes"), t, t)
    if g == "url":
        return url(t)
    if g == "skey":
        return paint(t, "value")
    if g == "mask":
        return key(t)
    if g == "good":
        return ok(t)
    if g == "bad":
        return err(t)
    if g == "meh":
        return warn(t)
    if g == "http":
        return http(t)
    if g == "lat":
        return latency(t)
    if g == "role":
        return role(t)
    if g == "tb":
        k = t[len("testbed-"):]
        return role(k, t) if role_key(k) else paint(t, "model", "bold")
    if g == "mid":
        return path(t) if _FILE_EXT.search(t) or t.startswith(("data/", "output/", "tests/")) else model(t)
    return t


def hl(text, on=None):
    """Colour the recognisable parts of plain text: labels, URLs, keys,
    statuses, HTTP codes, latencies, roles and model ids."""
    if not isinstance(text, str) or not text or not (enabled() if on is None else on):
        return text
    if "\x1b" in text:
        return text
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if s and len(s) >= 10 and set(s) <= set("=-_*#"):
            out.append(line[:len(line) - len(line.lstrip())] + rule(len(s), s[0], "═" if s[0] == "=" else "─"))
            continue
        done = _hl_re().sub(_hl_sub, line)
        m = _LABEL_LINE.match(line)
        if m:
            # the value after a 'Label:' in a soft colour, highlights kept
            lab_end = done.find(RESET) + len(RESET)
            rest = done[lab_end:]
            done = done[:lab_end] + _soft_value(rest)
        out.append(done)
    return "\n".join(out)


_LABEL_LINE = re.compile(r"^\s*[A-Z][A-Za-z0-9 ./()&'+-]{0,30}:\s")


def _soft_value(text):
    """Colour the plain stretches of text (outside escape codes) softly."""
    parts = re.split(r"(\x1b\[[0-9;]*m[^\x1b]*\x1b\[0m)", text)
    return "".join(p if p.startswith("\x1b") or not p.strip() else paint(p, "value", on=True) for p in parts)


_TONES = {
    "err": ("failed", "error", "blocked", "not stored", "no such", "unavailable", "denied", "refused",
            "invalid", "cannot", "can't", "unauthor", "forbidden", "not found"),
    "warn": ("warning", "skipped", "disabled", "no tools", "nothing", "not set", "cancel", "unchanged",
             "no memories", "timed out", "stale", "session only"),
    "ok": ("cleared", "stored", "deleted", "saved", "->", "done", "connected", "attached", "set to", "updated",
           "removed", "started", "stopped", " ok", "ready"),
}
_TONE_RGB = {"err": "err", "warn": "warn", "ok": "ok", "info": "info"}


def tone_of(text):
    low = strip(str(text)).lower()
    for tone in ("err", "warn", "ok"):
        if any(w in low for w in _TONES[tone]):
            return tone
    return "info"


def note(text, tone=None):
    """A status line ('[Stored as ...]', '[TTS failed: ...]') in a colour
    for its tone (err / warn / ok / info, guessed from the words when not
    given), with model ids, paths and latencies inside still highlighted."""
    text = str(text)
    if not text or not enabled():
        return text
    col = _TONE_RGB.get(tone or tone_of(text), "info")
    lead = text[:len(text) - len(text.lstrip("\n"))]
    return lead + paint(hl(text[len(lead):], on=True), col)


def hl_out(out, on=None):
    """Wrap an out(line) callable so each line is highlighted on screen."""
    if out is print:
        return lambda *a, **k: print(*(hl(str(x), on) for x in a), **k)
    return out


def _looks_json(text):
    s = text.lstrip()
    return s.startswith("{") or (s.startswith("[") and s[1:2] in ("{", "[", '"', "\n", "]")) or \
        (s[:1].isdigit() and s.strip().replace(".", "", 1).isdigit())


# a header: an ALL-CAPS title (at least two words, or a [ SECTION ]) at the
# start of a line, alone or followed by two spaces and more text
_HEAD = re.compile(r"^(\s*)(\[ [A-Z0-9 &/:+()-]+ \]|[A-Z][A-Z0-9&/+()'.,_-]*(?: [A-Z0-9&/+()'.,_-]+)+:?)(\s{2,}.*|\s*)$")


def colorize(text):
    """Colour a block of plain text for a terminal: ALL-CAPS header lines
    in a gradient, everything else through hl(). JSON stays plain. Only
    call it for output that goes to a screen with colour on."""
    if not text or "\x1b" in text or _looks_json(text):
        return text
    _forcing.append(1)
    try:
        return _colorize(text)
    finally:
        _forcing.pop()


def _colorize(text):
    lines = []
    for line in text.split("\n"):
        m = _HEAD.match(line)
        if m and not re.match(r"^\s*(?:\d{1,2}|[A-Za-z])\.\s", line):
            lines.append(m.group(1) + gradient(m.group(2), BANNER[1:]) + hl(m.group(3), on=True))
        else:
            lines.append(hl(line, on=True))
    return "\n".join(lines)


def cprint(*args, sep=" ", end="\n", file=None, flush=False):
    """print() that colours each line when the target is a terminal (with
    colour on). Files and pipes get exactly what print() would write."""
    stream = sys.stdout if file is None else file
    text = sep.join(str(a) for a in args)
    if enabled(stream) and not isinstance(stream, ColorStream):
        text = colorize(text)
    print(text, end=end, file=stream, flush=flush)


class ColorStream:
    """Wraps sys.stdout / sys.stderr on a terminal so plain print() output
    is coloured by colorize(). Text that already has colour codes, JSON and
    anything written elsewhere passes through untouched."""

    def __init__(self, stream):
        self._stream = stream

    def write(self, text):
        n = len(text) if isinstance(text, str) else 0
        if isinstance(text, str) and text.strip():
            text = colorize(text)
        self._stream.write(text)
        return n

    def __getattr__(self, name):
        return getattr(self._stream, name)


def install(*names):
    """Colour plain print() output on sys.stdout (and sys.stderr) when that
    stream is a terminal and colour is on. Returns the names wrapped."""
    done = []
    for name in names or ("stdout", "stderr"):
        s = getattr(sys, name, None)
        if s is None or isinstance(s, ColorStream) or not enabled(s):
            continue
        setattr(sys, name, ColorStream(s))
        done.append(name)
    return done


def apply_flags(argv):
    """Remove --no-color / --color from argv (in place) and apply them for
    this process and the programs it starts. Returns argv."""
    for flag, val in (("--no-color", "0"), ("--no-colour", "0"), ("--color", "1"), ("--colour", "1")):
        while flag in argv:
            argv.remove(flag)
            os.environ["NIMLAB_COLOR"] = val
            set_enabled(val == "1")
    return argv


def shell_line(env=None):
    """For start.sh: '<on|off|auto> <24|256|16>'."""
    return f"{policy(env)} {depth(env)}"
