"""
Shared files — read-only access for Lumenis to the One2lvOS WebDAV share.

The WebDAV server (webdav_server.py, port 8090) serves exactly one folder:
One2lvos/webdav_root (or $WEBDAV_ROOT). Anything One2lv uploads from the desktop
(Network Manager -> One2lvOS Files -> Browse -> Upload) lands there. This module lets
the council list that folder and read text files from it.

Rules:
  * Read-only. Nothing here writes, moves or deletes.
  * Confined to the share: absolute paths, '..', NUL bytes and anything that resolves
    outside the share are refused. Symlinks are never followed (not even ones that
    point inside the share) — same as the WebDAV server (follow_symlinks: False).
  * Text only for reading: UTF-8 (or UTF-16 with BOM) without NUL bytes. Binary files
    (images, PDFs, archives, ...) are listed with size and type but not read.
  * Bounded: listings stop at MAX_ENTRIES, reads return at most MAX_READ characters.
"""

from __future__ import annotations

import mimetypes
import os
import re
import stat
from datetime import datetime, timezone

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARE = os.path.realpath(os.environ.get("WEBDAV_ROOT", os.path.join(_ROOT_DIR, "webdav_root")))

MAX_ENTRIES = 200
MAX_DEPTH = 6
MAX_READ = 20000          # characters returned per read
MAX_FILE_BYTES = 5 * 1024 * 1024   # larger files are refused for text reading


class SharedFileError(Exception):
    pass


def _now_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _clean_rel(rel: str | None) -> str:
    rel = (rel or "").strip().replace("\\", "/")
    if "\x00" in rel:
        raise SharedFileError("invalid path")
    # accept paths written as /webdav_root/x, webdav_root/x or /x
    rel = re.sub(r"^/*(webdav_root/?)", "", rel).lstrip("/")
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise SharedFileError("path leaves the shared folder")
    return "/".join(parts)


def _resolve(rel: str | None) -> tuple[str, str]:
    """Return (clean_rel, absolute_path). Refuses symlinks in any component and
    anything outside SHARE."""
    clean = _clean_rel(rel)
    cur = SHARE
    for part in clean.split("/") if clean else []:
        cur = os.path.join(cur, part)
        try:
            st = os.lstat(cur)
        except FileNotFoundError:
            raise SharedFileError(f"not found: {clean}")
        if stat.S_ISLNK(st.st_mode):
            raise SharedFileError("symlinks are not followed")
    real = os.path.realpath(cur)
    if real != SHARE and not real.startswith(SHARE + os.sep):
        raise SharedFileError("path leaves the shared folder")
    return clean, real


def _kind(path: str, st: os.stat_result) -> str:
    if stat.S_ISLNK(st.st_mode):
        return "symlink"
    if stat.S_ISDIR(st.st_mode):
        return "dir"
    if stat.S_ISREG(st.st_mode):
        return "file"
    return "other"


def _sniff_text(path: str, size: int) -> bool:
    if size == 0:
        return True
    try:
        with open(path, "rb") as f:
            head = f.read(8192)
    except OSError:
        return False
    return _decode(head, partial=True) is not None


def _decode(data: bytes, partial: bool = False) -> str | None:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16", errors="strict" if not partial else "ignore")
        except UnicodeDecodeError:
            return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        # a multibyte char cut at the end of a partial read is fine
        if partial and e.start >= len(data) - 3:
            return data[: e.start].decode("utf-8-sig", errors="strict")
        return None


def list_dir(rel: str | None = "", recursive: bool = True) -> dict:
    """List the share (or a sub-folder). Symlinks are reported but not followed."""
    clean, base = _resolve(rel)
    if not os.path.isdir(base):
        raise SharedFileError(f"not a folder: {clean or '/'}")
    entries, truncated = [], False
    stack = [(base, clean, 0)]
    while stack:
        d, drel, depth = stack.pop(0)
        try:
            names = sorted(os.listdir(d), key=str.lower)
        except OSError as e:
            raise SharedFileError(f"cannot list {drel or '/'}: {e.strerror}")
        for name in names:
            p = os.path.join(d, name)
            r = f"{drel}/{name}" if drel else name
            try:
                st = os.lstat(p)
            except OSError:
                continue
            k = _kind(p, st)
            e = {"path": r, "type": k, "modified": _now_iso(st.st_mtime)}
            if k == "file":
                e["size"] = st.st_size
                e["mime"] = mimetypes.guess_type(name)[0] or "application/octet-stream"
                e["text"] = st.st_size <= MAX_FILE_BYTES and _sniff_text(p, st.st_size)
            if len(entries) >= MAX_ENTRIES:
                truncated = True
                break
            entries.append(e)
            if k == "dir" and recursive and depth + 1 < MAX_DEPTH:
                stack.append((p, r, depth + 1))
        if truncated:
            break
    return {"ok": True, "share": "webdav_root", "folder": clean or "/", "entries": entries,
            "count": len(entries), "truncated": truncated}


def read_file(rel: str, offset: int = 0, max_chars: int = MAX_READ) -> dict:
    """Read a text file from the share. Binary files are refused with their type and size."""
    clean, path = _resolve(rel)
    if not clean:
        raise SharedFileError("give a file path inside the shared folder")
    st = os.lstat(path)
    if not stat.S_ISREG(st.st_mode):
        raise SharedFileError(f"not a regular file: {clean}")
    mime = mimetypes.guess_type(clean)[0] or "application/octet-stream"
    base = {"path": clean, "size": st.st_size, "mime": mime, "modified": _now_iso(st.st_mtime)}
    if st.st_size > MAX_FILE_BYTES:
        return {"ok": False, **base, "error": f"file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB; not read"}
    with open(path, "rb") as f:
        data = f.read()
    text = _decode(data)
    if text is None:
        return {"ok": False, **base, "binary": True,
                "error": "binary file (not UTF-8/UTF-16 text); it can be listed and downloaded, not read as text"}
    max_chars = max(1, min(int(max_chars or MAX_READ), MAX_READ))
    offset = max(0, int(offset or 0))
    chunk = text[offset: offset + max_chars]
    return {"ok": True, **base, "binary": False, "offset": offset, "chars": len(chunk),
            "total_chars": len(text), "truncated": offset + len(chunk) < len(text), "content": chunk}


# ── Council integration helpers ─────────────────────────────────────────────

# Requests that should make the council look in the shared folder.
REQUEST_RE = re.compile(
    r"\b(web\s?dav(_root)?|shared\s+(folder|files?|drive|directory|storage)|share\s+folder|file\s+share|"
    r"one2lvos\s+files|uploaded\s+files?|files?\s+(i|we|miles|one2lv)\s+(uploaded|dropped|put|shared))\b",
    re.I,
)


def requested(text: str) -> bool:
    return bool(REQUEST_RE.search(text or ""))


def mentioned_files(text: str, listing: dict) -> list[str]:
    """Files from the listing whose path or name appears in the message."""
    low = (text or "").lower()
    hits = []
    for e in listing.get("entries", []):
        if e.get("type") != "file":
            continue
        p = e["path"].lower()
        name = p.rsplit("/", 1)[-1]
        if p in low or (len(name) >= 4 and name in low):
            hits.append(e["path"])
    return hits


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} B"


def council_context(user_message: str, extra_reads: list[str] | None = None, max_reads: int = 3,
                    chars_per_read: int = 8000) -> tuple[str, dict]:
    """Run the tool for a council request: list the share, read the files the message names
    (or that Hermes asked for). Returns (text for the Weaver, raw result)."""
    raw = {"listing": None, "reads": []}
    try:
        listing = list_dir("", recursive=True)
    except SharedFileError as e:
        return f"[Shared folder (webdav_root) — real tool output]\nListing failed: {e}", raw
    raw["listing"] = listing
    lines = ["[Shared folder (webdav_root) — real tool output, read-only]",
             f"{listing['count']} item(s){' (listing truncated)' if listing['truncated'] else ''}:"]
    for e in listing["entries"]:
        if e["type"] == "file":
            lines.append(f"- {e['path']} ({_fmt_size(e['size'])}, {e['mime']}, "
                         f"{'text' if e['text'] else 'binary - not readable as text'}, modified {e['modified']})")
        elif e["type"] == "dir":
            lines.append(f"- {e['path']}/ (folder)")
        else:
            lines.append(f"- {e['path']} ({e['type']}, not followed)")
    if not listing["entries"]:
        lines.append("(the shared folder is empty)")

    wanted = []
    for p in (extra_reads or []) + mentioned_files(user_message, listing):
        if p not in wanted:
            wanted.append(p)
    # If the user asks to read/open the shared files but names none, read the newest text file.
    if not wanted and re.search(r"\b(read|open|what('?s| is)\s+in|contents?|look\s+at|show)\b", user_message or "", re.I):
        texts = [e for e in listing["entries"] if e["type"] == "file" and e.get("text")]
        texts.sort(key=lambda e: e["modified"], reverse=True)
        wanted = [e["path"] for e in texts[:1]]

    for p in wanted[:max_reads]:
        try:
            r = read_file(p, 0, chars_per_read)
        except SharedFileError as e:
            r = {"ok": False, "path": p, "error": str(e)}
        raw["reads"].append({k: v for k, v in r.items() if k != "content"} | {"chars": r.get("chars")})
        if r.get("ok"):
            more = f" (first {r['chars']} of {r['total_chars']} characters)" if r["truncated"] else ""
            lines.append(f"\n--- contents of {r['path']}{more} ---\n{r['content']}\n--- end of {r['path']} ---")
        else:
            lines.append(f"\nCould not read {p}: {r.get('error')}")
    return "\n".join(lines), raw
