"""Attachments in the testbed chat: /attach, the recent-files picker, and
messages that carry files, all answered by the one entity (nimlab.unified)."""

import os
import time

from . import colors as C, roles as R
from . import unified

ATTACH_HELP = """Attachments (any number per message; each file goes to the ability it needs, the persona answers):
  /attach                  -> pick from recent files (Download, Documents, Pictures, Recordings...)
  /attach <path> [path...] -> attach files by path        /attached -> list   /detach -> clear
  or just paste a file path in your message, as before
  Images, PDFs, Office docs, audio, video, text/code/JSON/CSV (read as text, capped).
  /call                    -> live voice call (Termux:API mic and speaker)"""


class Pending:
    """Files waiting to go with the next message."""

    def __init__(self):
        self.parts = []

    def add_path(self, path):
        p = unified.part_from_path(path)
        if any(x.path == p.path for x in self.parts):
            return None
        self.parts.append(p)
        return p

    def take(self):
        out, self.parts = self.parts, []
        return out

    def lines(self):
        return [f"  {i}. {p.name} ({p.kind}, {unified.human_size(os.path.getsize(p.path))})"
                for i, p in enumerate(self.parts, 1) if p.path and os.path.exists(p.path)]


def split_paths(rest):
    """'/attach a.png "b c.pdf" d\\ e.txt' -> paths."""
    import shlex
    try:
        return shlex.split(rest)
    except ValueError:
        return rest.split()


def attach_command(pending, rest, input_fn=input, out=print, recent=None):
    """/attach [paths]: with paths attach them; without, show the picker."""
    if rest.strip():
        for raw in split_paths(rest):
            try:
                p = pending.add_path(raw)
                out(f"[attached {p.name} ({p.kind})]" if p else f"[already attached: {raw}]")
            except unified.PartError as e:
                out(f"[{e}]")
        return
    files = recent if recent is not None else unified.recent_files()
    if not files:
        out("[No recent files found in Download, Documents, Pictures or Recordings. Type /attach <path>; "
            "run termux-setup-storage once if Termux can't see your storage.]")
        return
    out("Recent files:")
    for i, (p, size, mtime) in enumerate(files, 1):
        age = time.strftime("%b %d %H:%M", time.localtime(mtime))
        out(f"  {i:>2}. {os.path.basename(p)[:44]:<44} {unified.human_size(size):>8}  {age}")
    pick = input_fn("Numbers to attach (e.g. 1,3), or a path, Enter to cancel: ").strip()
    if not pick:
        return
    if not pick.replace(",", " ").replace(" ", "").isdigit():
        return attach_command(pending, pick, input_fn, out, recent)
    for tok in pick.replace(",", " ").split():
        n = int(tok)
        if 1 <= n <= len(files):
            p = pending.add_path(files[n - 1][0])
            if p:
                out(f"[attached {p.name} ({p.kind})]")
        else:
            out(f"[no file {n}]")


def has_files(text):
    return bool(unified.paths_in_text(text))


def abilities_line(trace):
    """'[abilities: Vision 1.2s -> Persona 0.8s]', each role in its colour."""
    def one(t):
        name = R.label(t["role"]) if t["role"] in R.BY_KEY else t["label"]
        secs = f"{t['ms'] / 1000:.1f}s"
        if not C.enabled():
            return f"{name} {secs}{'' if t['ok'] else ' FAILED'}"
        return f"{C.role(t['role'], name)} {C.latency(secs)}{'' if t['ok'] else ' ' + C.err('FAILED')}"
    arrow = C.dim(" -> ")
    return C.dim("[abilities: ") + arrow.join(one(t) for t in trace) + C.dim("]")


def run_with_files(ent, text, parts, history, out=print, name="QUILL"):
    """One chat turn with attachments through the one entity. Appends to
    history on success. Returns the Mind result."""
    names = ", ".join(p.name for p in parts)
    if names:
        out(f"[sending {names}]")
    res = unified.Mind(ent).run(text, parts, history, allow_text_paths=True)
    show = ent.cluster.get("routing_settings", {}).get("show_route", True)
    if show and res["trace"]:
        out(abilities_line(res["trace"]))
    if res.get("transcript"):
        out(f"{C.role('asr', '[heard]')} {C.you_text(res['transcript'])}")
    if res.get("blocked"):
        out(f"{C.err('[BLOCKED]')} {C.warn(res['blocked'])}")
        return res
    if not res["ok"]:
        out(f"\n{C.err('[ERROR]')} {C.paint(res['error'], 'err')}")
        return res
    r = res["result"]
    out(f"\n{C.entity(name)} {C.dim('(')}{C.latency(str(r.latency) + 's')}{C.dim(' | ')}"
        f"{C.paint(str(r.usage.get('completion_tokens', 'N/A')), 'number')}{C.dim(' tokens):')}\n{C.reply(res['text'])}")
    for m in res["media"]:
        out(f"  {C.ok('saved:')} {C.path(m['path'])}")
    said = text.strip() or res.get("transcript") or ""
    if names:
        said = f"{said} [attached: {names}]".strip()
    history.append({"role": "user", "content": said})
    history.append({"role": "assistant", "content": res["reply"]})
    return res
