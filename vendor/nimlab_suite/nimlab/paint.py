"""Colour for the screens added in 3.7.4 and 3.8.0 (v3.8.1).

The line builders in systests, jobscli, heartbeat, hostenv and commands
stay plain: their text also goes to Telegram, to memory and to Quill's
admin tools. These helpers colour a finished plain line for the terminal,
with the same colors.py palette as the older menus. With colour off
(not a terminal, NIMLAB_COLOR=0, NO_COLOR) every helper returns its input
unchanged, so plain output is exactly what it was.

Colouring happens after the padding, so columns line up either way.
"""

import re

from . import colors as C

# leading status tags: [PASS] [FAIL] [skip] [ok] [x] [!] [!!] [on ] [off] [BRK]
_TAG = re.compile(r"^(\s*)(\[(?:PASS|FAIL|SKIP|skip|ok|OK|x ?|!!|! ?|on ?|off|BRK)\])")
_TAG_TONE = {"PASS": "ok", "OK": "ok", "ON": "ok", "FAIL": "err", "X": "err", "!!": "err", "BRK": "err",
             "SKIP": "warn", "!": "warn", "OFF": "dim"}
# run states (scheduler) and verdict words inside a line
_WORD = re.compile(r"\b(SUCCEEDED|FAILED|TIMED_OUT|BROKEN|SKIPPED|MISSED|RUNNING|SCHEDULED|DISABLED|PASS|FAIL)\b")
_WORD_TONE = {"SUCCEEDED": "ok", "PASS": "ok", "RUNNING": "info", "SCHEDULED": "info", "FAILED": "err",
              "FAIL": "err", "TIMED_OUT": "err", "BROKEN": "err", "SKIPPED": "warn", "MISSED": "warn",
              "DISABLED": "dim"}
_BUG = re.compile(r"\bB-[0-9A-F]{6}\b")
_MS = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?\s?(?:ms|s))(?![\w])")
_CMD = re.compile(r"((?:nimlab|\./start\.sh|sv|pkg|apt|sudo|loginctl) [^;,()]*[^;,() .])")
# 'next:' / 'to enable:' / 'bug ID:' follow-up lines under a result
_FOLLOW = re.compile(r"^(\s+)(bug ID:|next:|to enable:|Note:)(\s.*)$")
# '  label        : value' and 'Label: value'
_KV = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9 _./()-]{0,26}?)(\s*:\s)(.*)$")


def on():
    return C.enabled()


def tone(word, t):
    return {"ok": C.ok, "err": C.err, "warn": C.warn, "dim": C.dim, "info": C.info}.get(t, C.value)(word)


def bug(text):
    """Bug IDs (B-1A2B3C) highlighted."""
    if not on():
        return text
    return _BUG.sub(lambda m: C.paint(m.group(0), "http4", "bold"), text)


def cmds(text):
    """Commands to run (nimlab ..., sv ...) highlighted as hints."""
    if not on():
        return text
    return _CMD.sub(lambda m: C.paint(m.group(1), "accent"), text)


def _words(text):
    return _WORD.sub(lambda m: tone(m.group(1), _WORD_TONE[m.group(1)]), text)


def status_line(line):
    """A result / job / check line: the leading tag in its colour, run
    states, times and bug IDs inside it highlighted."""
    if not on() or not line:
        return line
    m = _TAG.match(line)
    rest = line
    head = ""
    if m:
        word = m.group(2).strip("[] ").upper()
        head = m.group(1) + tone(m.group(2), _TAG_TONE.get(word, "dim"))
        rest = line[m.end():]
    rest = _MS.sub(lambda x: C.latency(x.group(1)), rest)
    rest = bug(_words(rest))
    return head + rest


def follow_line(line):
    """'       next: nimlab ...' and friends under a result."""
    if not on():
        return line
    m = _FOLLOW.match(line)
    if not m:
        return status_line(line)
    lab = m.group(2)
    body = m.group(3)
    if lab == "bug ID:":
        return m.group(1) + C.label(lab) + bug(cmds(body))
    return m.group(1) + C.label(lab) + C.hint(body) if lab != "next:" else \
        m.group(1) + C.label(lab) + cmds(body)


def kv_line(line):
    """'  label : value' with the label like the older settings screens."""
    if not on():
        return line
    m = _KV.match(line)
    if not m:
        return status_line(line)
    val = m.group(4)
    low = val.strip().lower()
    if low in ("yes", "on", "ok", "enabled"):
        val = C.ok(val)
    elif low in ("no", "off", "-", "none", "disabled"):
        val = C.dim(val)
    else:
        val = bug(cmds(_words(val)))
    return m.group(1) + C.label(m.group(2)) + C.dim(m.group(3)) + val


def result_lines(lines):
    """Colour a test result block (systests.result_lines and the rows)."""
    if not on():
        return list(lines)
    out = []
    for ln in lines:
        s = ln.lstrip()
        if s.startswith(("ok ", "x  ", "x ")) and ln.startswith("       "):
            mark, _, msg = s.partition(" ")
            out.append(ln[:len(ln) - len(s)] + (C.ok("ok") if mark == "ok" else C.err("x"))
                       + " " + msg)
        else:
            out.append(follow_line(ln))
    return out


def table_lines(lines):
    """systests.table: header row bold, rules as gradient rules, the
    result column coloured, the summary line in the verdict colour."""
    if not on():
        return list(lines)
    out = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s and set(s) == {"-"}:
            out.append(C.rule(len(s)))
        elif i == 0:
            out.append(C.label(ln))
        elif re.match(r"^\d+ passed, \d+ failed, \d+ skipped", s):
            failed = int(s.split(" failed")[0].split(", ")[-1])
            out.append((C.err if failed else C.ok)(ln))
        else:
            m = re.match(r"^(\S+\s+)(PASS|FAIL|skip)(\s+)(\d+ms)(.*)$", ln)
            if m:
                t = {"PASS": "ok", "FAIL": "err", "skip": "warn"}[m.group(2)]
                out.append(C.paint(m.group(1), "label") + tone(m.group(2), t) + m.group(3)
                           + C.latency(m.group(4)) + C.dim(m.group(5)))
            else:
                out.append(ln)
    return out


def summary(text):
    """'3 passed, 1 failed, 0 skipped' and run-history rows."""
    if not on():
        return text
    text = re.sub(r"\b(\d+) passed\b", lambda m: C.ok(m.group(0)), text)
    text = re.sub(r"\b(\d+) failed\b", lambda m: (C.err if m.group(1) != "0" else C.dim)(m.group(0)), text)
    text = re.sub(r"\b(\d+) skipped\b", lambda m: (C.warn if m.group(1) != "0" else C.dim)(m.group(0)), text)
    text = re.sub(r"\(failed: ([^)]*)\)", lambda m: "(failed: " + C.err(m.group(1)) + ")", text)
    return text


def heading(text):
    """A plain title line ('Jobs (3), times in ...:') as a section."""
    if not on():
        return text
    return C.section(text)


def heartbeat_lines(lines):
    """heartbeat.status_lines / report_text on a terminal."""
    if not on():
        return list(lines)
    out = []
    for ln in lines:
        m = re.match(r"^Heartbeat: (ON|off)(.*)$", ln)
        if m:
            out.append(C.section("Heartbeat:") + " " + C.onoff(m.group(1) == "ON", "ON", "off") + C.dim(m.group(2)))
            continue
        s = ln.lstrip()
        lead = ln[:len(ln) - len(s)]
        m = re.match(r"^(took \S+:)(\s)(ok|FAILED)(.*)$", s)
        if m:
            out.append(lead + C.label(m.group(1)) + m.group(2) + (C.ok if m.group(3) == "ok" else C.err)(m.group(3))
                       + m.group(4))
            continue
        m = re.match(r"^(skipped \S+:)(.*)$", s)
        if m:
            out.append(lead + C.warn(m.group(1)) + C.dim(m.group(2)))
            continue
        if s.startswith("heartbeat: took"):
            out.append(lead + C.info(s))
            continue
        out.append(kv_line(ln))
    return out


def job_line(line):
    """jobscli.job_line / action_line: state tag, name, next run, last status."""
    if not on():
        return line
    m = re.match(r"^(\s*(?:\d+\))?\s*)(\[(?:on |off|BRK)\])( (?:p\d )?)(\S+)(.*)$", line)
    if not m:
        return status_line(line)
    word = m.group(2).strip("[] ").upper()
    lead = m.group(1)
    num = re.match(r"^(\s*)(\d+\))(.*)$", lead)
    if num:
        n = int(num.group(2)[:-1])
        lead = num.group(1) + C.paint(num.group(2), C.menu_rgb(n), "bold") + num.group(3)
    rest = m.group(5)
    rest = re.sub(r"\b(next|last)\b", lambda x: C.dim(x.group(1)), rest)
    rest = re.sub(r"(->)", lambda x: C.dim(x.group(1)), rest)
    return (lead + tone(m.group(2), _TAG_TONE.get(word, "dim")) + C.dim(m.group(3)) + C.value(m.group(4))
            + bug(_words(rest)))


def platform_lines(lines):
    """hostenv.lines (nimlab platform): tags coloured, fix commands as hints."""
    if not on():
        return list(lines)
    out = []
    for ln in lines:
        if ln.startswith("       "):
            out.append(C.hint(ln))
        elif ln.startswith("    ") and not ln.startswith("["):
            out.append(C.info(ln))
        else:
            out.append(status_line(ln))
    return out


def keys(text):
    """A key strip like 'e) enable  d) disable  b) back: ' with each key in
    its menu colour (for the one-line action prompts)."""
    if not on():
        return text
    i = [0]

    def one(m):
        i[0] += 1
        return m.group(1) + C.paint(m.group(2), C.menu_rgb(i[0]), "bold") + C.paint(m.group(3), C.tint(C.menu_rgb(i[0]), 0.5))
    return re.sub(r"(^|\s)([a-z0-9]{1,3}\))( [a-z][a-z /]*?)(?=\s{2}|,|:|$)", one, text)


def ask(text):
    """A menu prompt in the standard prompt colour."""
    return C.ask(text) if on() else text


def auto(line):
    """Best-effort colour for one line of CLI output from the new commands
    (jobs, heartbeat, scheduler, platform): already-coloured lines and
    plain-mode lines come back untouched."""
    if not on() or not isinstance(line, str) or "\x1b[" in line or not line.strip():
        return line
    s = line.strip()
    if re.match(r"^\s*(?:\d+\))?\s*\[(?:on |off|BRK)\]", line):
        return job_line(line)
    if _TAG.match(line):
        return status_line(line)
    if s.startswith("Heartbeat: "):
        return heartbeat_lines([line])[0]
    m = re.match(r"^(\s*)(scheduler )(running|not running)(.*)$", line)
    if m:
        rest = re.sub(r"\b(\d+) failed runs\b", lambda x: (C.err if x.group(1) != "0" else C.dim)(x.group(0)),
                      m.group(4))
        rest = re.sub(r"\bheartbeat (on|off)\b", lambda x: "heartbeat " + C.onoff(x.group(1) == "on", "on", "off"),
                      rest)
        return (m.group(1) + C.section(m.group(2).strip()) + " "
                + (C.ok if m.group(3) == "running" else C.warn)(m.group(3)) + rest)
    if s.startswith("Scheduler: ") or s.startswith("scheduler: "):
        lab, _, rest = line.partition(": ")
        word = rest.split(" ", 1)[0].rstrip(",")
        good = word.lower() in ("running", "on")
        return C.section(lab + ":") + " " + (C.ok if good else C.warn)(word) + C.dim(rest[len(word):])
    if s.endswith(":") and len(s) < 80 and not s.startswith(("usage", "  ")) and line == s:
        return heading(line)
    if s.startswith("usage:"):
        return C.dim("usage:") + " " + cmds(s[6:].strip()) if line == s else line
    if re.match(r"^\s{2,}[A-Za-z]", line) and re.match(r"^\s*[A-Za-z][A-Za-z0-9 _./()-]{0,26}?\s*:\s", line):
        return kv_line(line)
    if re.match(r"^\s*\d{4}-\d\d-\d\d|^\s*\d\d-\d\d \d\d:\d\d", line):
        return status_line(line)
    return status_line(line)


def wrap_say(say):
    """A say() that colours each line with auto() (plain stays plain)."""
    def _say(text=""):
        if not isinstance(text, str) or "\n" not in text:
            return say(auto(text))
        return say("\n".join(auto(x) for x in text.split("\n")))
    return _say


def out(text=""):
    """print() with auto() colour."""
    wrap_say(print)(text)
