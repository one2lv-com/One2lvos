"""
Safe revert-to-working (items 16 and 17). Replaces the old open endpoint that ran `git reset --hard`.

  known_good()        tags named working-YYYYMMDD[-N], newest first (made by tools/tag_known_good.sh only
                      after every test suite passes)
  preview(target)     what would change: commits undone, files changed. Refuses when there are uncommitted
                      changes. Returns a one-time confirmation code (10 minutes).
  run(code)           re-checks HEAD and a clean tree, then:
                        1. backs up: branch revert-backup-<ts> at HEAD + a git bundle in data/revert_backups/
                        2. restores the tracked files to the tag's tree with `git restore --source=<tag>`
                        3. commits that as a NEW commit ("Revert to working-..."), so history is kept
                      Ignored files (.env, data/, compass.db, backups/) are never touched.
  undo(backup)        restores the tree from the backup branch the same way, as another new commit.
The running reactor keeps the old code in memory until it is restarted; the result says so.
"""
from __future__ import annotations

import secrets
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

REPO = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO / "data" / "revert_backups"
TAG_GLOB = "working-*"
CODE_TTL = 600
_pending: Dict[str, dict] = {}


def _git(*args, check=True, timeout=60) -> str:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def head() -> str:
    return _git("rev-parse", "HEAD")


def dirty() -> list:
    out = _git("status", "--porcelain", "--untracked-files=no")
    return [l for l in out.splitlines() if l.strip()]


def known_good() -> list:
    out = _git("for-each-ref", "--sort=-creatordate", "--format=%(refname:short) %(objectname:short) "
               "%(creatordate:iso)", f"refs/tags/{TAG_GLOB}")
    rows = []
    for l in out.splitlines():
        p = l.split(" ", 2)
        if len(p) == 3:
            rows.append({"tag": p[0], "commit": p[1], "date": p[2]})
    return rows


def preview(target: Optional[str] = None) -> dict:
    tags = known_good()
    if target is None:
        h = _git("rev-parse", "--short", "HEAD")
        target = next((t["tag"] for t in tags if t["commit"] != h), None)
        if target is None:
            return {"ok": False, "error": "no known-good tag to go back to (tags are made by "
                    "tools/tag_known_good.sh after every test passes)" if not tags else
                    "the newest known-good tag is the current commit; nothing to revert", "tags": tags}
    elif target not in [t["tag"] for t in tags]:
        return {"ok": False, "error": f"{target!r} is not a known-good tag", "tags": tags}
    d = dirty()
    if d:
        return {"ok": False, "error": "there are uncommitted changes; commit or stash them first, nothing was "
                "changed", "uncommitted": d[:30]}
    undone = _git("log", "--oneline", f"{target}..HEAD").splitlines()
    files = _git("diff", "--stat", "HEAD", target).splitlines()
    code = secrets.token_hex(3)
    _pending.clear()
    _pending[code] = {"target": target, "head": head(), "at": time.time()}
    return {"ok": True, "target": target, "current": _git("rev-parse", "--short", "HEAD"),
            "commits_undone": undone[:50], "commits_undone_count": len(undone), "files": files[-40:],
            "confirm_code": code, "expires_in_s": CODE_TTL,
            "how": "backup branch + bundle first, then the tag's files are restored as a new commit (no reset --hard); "
                   "ignored files such as .env and data/ are not touched; restart the reactor afterwards"}


def _restore_as_commit(source: str, message: str) -> str:
    _git("restore", f"--source={source}", "--staged", "--worktree", ":/")
    if not _git("status", "--porcelain", "--untracked-files=no"):
        return _git("rev-parse", "--short", "HEAD")
    _git("commit", "-q", "-m", message)
    return _git("rev-parse", "--short", "HEAD")


def run(code: str) -> dict:
    p = _pending.get((code or "").strip())
    if not p or time.time() - p["at"] > CODE_TTL:
        return {"ok": False, "error": "no matching preview, or it expired; ask for a new preview"}
    if head() != p["head"]:
        return {"ok": False, "error": "the code changed since the preview; nothing was changed"}
    if dirty():
        return {"ok": False, "error": "uncommitted changes appeared since the preview; nothing was changed"}
    _pending.clear()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch = f"revert-backup-{ts}"
    _git("branch", branch, p["head"])
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bundle = BACKUP_DIR / f"{branch}.bundle"
    _git("bundle", "create", str(bundle), branch, timeout=300)
    new = _restore_as_commit(p["target"], f"Revert to {p['target']} (safe revert; backup branch {branch})")
    return {"ok": True, "reverted_to": p["target"], "new_commit": new, "backup_branch": branch,
            "backup_bundle": str(bundle.relative_to(REPO)), "restart_needed": True,
            "undo": f"/revert undo {branch}  (or: git restore --source={branch} --staged --worktree :/ && git commit)"}


def undo(branch: str) -> dict:
    if not branch.startswith("revert-backup-") or branch not in _git("branch", "--list", branch):
        return {"ok": False, "error": f"no backup branch {branch!r}"}
    if dirty():
        return {"ok": False, "error": "there are uncommitted changes; nothing was changed"}
    new = _restore_as_commit(branch, f"Undo safe revert: restore {branch}")
    return {"ok": True, "restored_from": branch, "new_commit": new, "restart_needed": True}
