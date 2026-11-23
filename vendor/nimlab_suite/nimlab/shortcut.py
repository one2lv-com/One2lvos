"""`./start.sh shortcut`: a `nimlab` command that runs start.sh from anywhere.

The command is a small wrapper script, not a symlink: start.sh finds its
folder from dirname(BASH_SOURCE), which a symlink would point at the bin
directory instead. The wrapper holds the absolute path of start.sh and
execs it with every argument passed through:

    nimlab                 the dashboard
    nimlab grpc check      same as ./start.sh grpc check

Where it goes:
    Termux        $PREFIX/bin/<name>   (shebang $PREFIX/bin/bash)
    other Linux   ~/.local/bin/<name>  (shebang /usr/bin/env bash; created
                                        if missing, PATH checked)

Running it again rewrites the path (after the folder moved). A file of the
same name that this module did not write is never replaced without
--force, and `remove` only deletes wrappers it wrote.
"""

import os
import re
import shlex
import shutil
import tempfile

from . import __version__

DEFAULT_NAME = "nimlab"
MARKER = "# nimlab-shortcut: made by ./start.sh shortcut"
NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._+-]*$")
PATH_LINE = re.compile(r"^NIMLAB_START=(.*)$", re.M)


def project_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def start_script(root=None):
    return os.path.join(os.path.realpath(root or project_dir()), "start.sh")


def is_termux(env=None):
    env = os.environ if env is None else env
    return bool(env.get("TERMUX_VERSION")) or "com.termux" in env.get("PREFIX", "")


def bin_dir(env=None):
    """Where the wrapper goes: $PREFIX/bin on Termux, else ~/.local/bin."""
    env = os.environ if env is None else env
    if is_termux(env) and env.get("PREFIX"):
        return os.path.join(env["PREFIX"], "bin")
    home = env.get("HOME") or os.path.expanduser("~")
    return os.path.join(home, ".local", "bin")


def shebang(env=None):
    env = os.environ if env is None else env
    if is_termux(env) and env.get("PREFIX"):
        return "#!" + os.path.join(env["PREFIX"], "bin", "bash")
    return "#!/usr/bin/env bash"


def check_name(name):
    if not name or not NAME_RE.match(name) or len(name) > 64:
        raise ValueError(f"'{name}' is not a usable command name (letters, digits, . _ + -; no slashes).")
    return name


def wrapper_text(start, env=None, name=DEFAULT_NAME):
    q = shlex.quote(start)
    return (f"{shebang(env)}\n"
            f"{MARKER} (NIM test lab v{__version__})\n"
            f"# Runs the NVIDIA NIM test lab from any folder: '{name}' = ./start.sh, '{name} grpc check' =\n"
            f"# ./start.sh grpc check. Moved the folder? Run ./start.sh shortcut there again.\n"
            f"# Remove: ./start.sh shortcut remove{'' if name == DEFAULT_NAME else ' ' + name}\n"
            f"NIMLAB_START={q}\n"
            f"if [ ! -f \"$NIMLAB_START\" ]; then\n"
            f"    echo \"{name}: $NIMLAB_START is gone. Run ./start.sh shortcut in the lab's new folder.\" >&2\n"
            f"    exit 127\n"
            f"fi\n"
            f"exec bash \"$NIMLAB_START\" \"$@\"\n")


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(8192)
    except OSError:
        return ""


def is_ours(path):
    return os.path.isfile(path) and not os.path.islink(path) and MARKER in _read(path)


def target_of(path):
    """The start.sh path a wrapper we wrote points to (None if not ours)."""
    if not is_ours(path):
        return None
    m = PATH_LINE.search(_read(path))
    if not m:
        return None
    try:
        parts = shlex.split(m.group(1))
    except ValueError:
        return None
    return parts[0] if parts else None


def on_path(directory, env=None):
    env = os.environ if env is None else env
    want = os.path.realpath(directory)
    return any(p and os.path.realpath(p) == want for p in env.get("PATH", "").split(os.pathsep))


def resolves_to(name, env=None):
    env = os.environ if env is None else env
    return shutil.which(name, path=env.get("PATH", ""))


def path_hint(directory, env=None):
    env = os.environ if env is None else env
    home = env.get("HOME") or os.path.expanduser("~")
    shown = "$HOME" + directory[len(home):] if home and directory.startswith(home + os.sep) else directory
    return [f"{directory} is not on your PATH yet. Add it once:",
            f"  echo 'export PATH=\"{shown}:$PATH\"' >> ~/.bashrc && . ~/.bashrc"]


def install(name=DEFAULT_NAME, force=False, directory=None, env=None, root=None):
    """Write or update the wrapper. Returns (ok, lines)."""
    env = os.environ if env is None else env
    name = check_name(name)
    start = start_script(root)
    if not os.path.isfile(start):
        return False, [f"start.sh not found at {start}."]
    d = os.path.abspath(directory or bin_dir(env))
    dest = os.path.join(d, name)
    lines = []
    if os.path.isdir(dest) and not os.path.islink(dest):
        return False, [f"{dest} is a folder; pick another name: ./start.sh shortcut install <name>."]
    old = None
    if os.path.lexists(dest):
        if is_ours(dest):
            old = target_of(dest)
        elif not force:
            what = "a symlink to " + os.readlink(dest) if os.path.islink(dest) else "a command this lab did not make"
            return False, [f"[!] {dest} already exists and is {what}.",
                           f"    Left it alone. Use another name (./start.sh shortcut install <name>)",
                           f"    or replace it with: ./start.sh shortcut install {name} --force"]
        else:
            lines.append(f"[!] Replacing {dest} (it was not made by this lab; --force).")
    other = resolves_to(name, env)
    os.makedirs(d, exist_ok=True)
    text = wrapper_text(start, env, name)
    if old is not None and _read(dest) == text:
        lines.append(f"[ok] '{name}' is already set up: {dest} -> {start}")
    else:
        fd, tmp = tempfile.mkstemp(prefix="." + name + ".", dir=d)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.chmod(tmp, 0o755)
            if os.path.islink(dest):
                os.unlink(dest)
            os.replace(tmp, dest)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        if old is not None and old != start:
            lines.append(f"[ok] Updated '{name}': it pointed to {old}, now {start}")
        elif old is not None:
            lines.append(f"[ok] Rewrote '{name}': {dest} -> {start}")
        else:
            lines.append(f"[ok] Installed '{name}': {dest} -> {start}")
    if not on_path(d, env):
        lines += path_hint(d, env)
    else:
        if other and os.path.realpath(other) != os.path.realpath(dest):
            lines.append(f"[!] Another '{name}' comes first on your PATH: {other}. Typing '{name}' runs that "
                         f"one; use another name or move {d} earlier in PATH.")
        lines.append(f"Try it from any folder: {name}   (or: {name} grpc check, {name} memory test)")
        if other is None:
            lines.append("If your shell says 'command not found', run: hash -r")
    return True, lines


def remove(name=DEFAULT_NAME, directory=None, env=None):
    env = os.environ if env is None else env
    name = check_name(name)
    dest = os.path.join(os.path.abspath(directory or bin_dir(env)), name)
    if not os.path.lexists(dest):
        return True, [f"No '{name}' shortcut at {dest}; nothing to remove."]
    if not is_ours(dest):
        return False, [f"[!] {dest} was not made by this lab; left it alone."]
    os.unlink(dest)
    return True, [f"[ok] Removed '{name}' ({dest})."]


def status(name=DEFAULT_NAME, directory=None, env=None, root=None):
    """(healthy, lines): where the wrapper is, where it points, and whether
    that path still exists and is this folder."""
    env = os.environ if env is None else env
    name = check_name(name)
    d = os.path.abspath(directory or bin_dir(env))
    dest = os.path.join(d, name)
    here = start_script(root)
    if not os.path.lexists(dest):
        return False, [f"'{name}' is not installed (would go in {dest}).", "Set it up: ./start.sh shortcut"]
    if not is_ours(dest):
        return False, [f"{dest} exists but was not made by this lab."]
    tgt = target_of(dest)
    exists = bool(tgt) and os.path.isfile(tgt)
    lines = [f"command : {name}", f"file    : {dest}",
             f"runs    : {tgt or '?'}" + ("" if exists else "   [MISSING: that path no longer exists]")]
    healthy = exists
    if exists and os.path.realpath(tgt) != os.path.realpath(here):
        lines.append(f"[!] That is another copy of the lab; this one is {here}. "
                     "Run ./start.sh shortcut here to switch.")
    elif not exists:
        lines.append("Run ./start.sh shortcut in the lab's current folder to fix it.")
    if not on_path(d, env):
        healthy = False
        lines += path_hint(d, env)
    else:
        other = resolves_to(name, env)
        if other and os.path.realpath(other) != os.path.realpath(dest):
            healthy = False
            lines.append(f"[!] '{name}' on your PATH resolves to {other} first, not this shortcut.")
        elif exists:
            lines.append("[ok] Ready: type '" + name + "' from any folder.")
    return healthy, lines


def cmd_shortcut(args):
    from . import colors as C
    act = args.action or "install"
    name = args.name or DEFAULT_NAME
    try:
        if act == "install":
            ok, lines = install(name, force=args.force, directory=args.dir)
        elif act == "remove":
            ok, lines = remove(name, directory=args.dir)
        else:
            ok, lines = status(name, directory=args.dir)
    except (ValueError, OSError) as e:
        print(C.err(str(e)))
        return 2
    for ln in lines:
        if ln.startswith("[ok]"):
            print(C.ok(ln))
        elif ln.startswith("[!]") or "MISSING" in ln or "not on your PATH" in ln:
            print(C.warn(ln))
        else:
            print(ln)
    return 0 if ok else 1
