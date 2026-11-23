#!/usr/bin/env python3
"""Build the release zip (3.8.2): everything tracked or new in the project
folder except run-time data and developer leftovers. The zip unpacks to
nvidia_nim_test_lab/, and start.sh / update.sh keep mode 0755 so they run
right after unzip.

usage: python3 tools/build_zip.py OUT.zip
"""
import os
import stat
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP = "nvidia_nim_test_lab"

# folders that are never shipped, anywhere in the tree
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv",
             "node_modules"}
# top-level folders that hold this machine's run-time data
SKIP_TOP = {"data", "output", "logs", "backups"}
SKIP_FILES = {".DS_Store", ".nimlab_env", "secrets.json"}
SKIP_SUFFIX = (".pyc", ".pyo", ".orig", ".rej", "~", ".swp", ".log", ".zip")
SKIP_PREFIX = ("NOTES_",)
EXECUTABLE = {"start.sh", "update.sh"}


def wanted(rel):
    parts = rel.split("/")
    if parts[0] in SKIP_TOP or any(p in SKIP_DIRS for p in parts):
        return False
    name = parts[-1]
    if name in SKIP_FILES or name.endswith(SKIP_SUFFIX) or (len(parts) == 1 and name.startswith(SKIP_PREFIX)):
        return False
    return True


def files(root=ROOT):
    out = []
    for d, dirs, names in os.walk(root):
        rel_d = os.path.relpath(d, root).replace(os.sep, "/")
        rel_d = "" if rel_d == "." else rel_d + "/"
        dirs[:] = sorted(x for x in dirs if wanted(rel_d + x))
        for n in sorted(names):
            rel = rel_d + n
            if wanted(rel) and not os.path.islink(os.path.join(d, n)):
                out.append(rel)
    return out


def build(out_path, root=ROOT):
    out_path = os.path.abspath(out_path)
    if os.path.exists(out_path):
        os.remove(out_path)
    names = files(root)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in names:
            src = os.path.join(root, rel)
            info = zipfile.ZipInfo(f"{TOP}/{rel}", time.localtime(os.path.getmtime(src))[:6])
            mode = 0o755 if rel in EXECUTABLE else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(src, "rb") as f:
                z.writestr(info, f.read())
    return out_path, len(names)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: build_zip.py OUT.zip")
    path, n = build(sys.argv[1])
    print(f"built {path}: {n} files")
