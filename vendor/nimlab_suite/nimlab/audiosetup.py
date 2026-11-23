"""Register a phone for the audio bridge and print its Termux setup block (3.8.6).

The flow behind the launcher's "Phone audio bridge" item, the optional
step in `nimlab setup` and `nimlab audio setup`:

  name the phone -> pick mic on/off -> register it (a new key, shown once)
  -> print one block to paste into Termux on that phone.

The block installs curl, jq and termux-api, writes the nimbridge client with
a cat heredoc, writes that phone's config already filled in (URL, name, key,
mic) and runs `nimbridge init`, which checks the key with the server, asks
Android for the mic once when the mic is on, and starts the bridge. The phone
asks nothing.

The client text comes from the one canonical file, nimlab/clients/nimbridge.sh,
so a client update reaches every new block. The key appears only on screen
and in the block (by design); nothing here writes it to a file or a log. The
server keeps only its hash (audiobus.add_device).
"""
import hashlib
import json
import os
import re
import shlex

from . import audiobus

CLIENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clients", "nimbridge.sh")
HEREDOC = "NIMBRIDGE_EOF"
CONF_HEREDOC = "NIMBRIDGE_CONF"
RESERVED = {"all", "active"}          # audiobus targets: a phone can't be called that
URL_RE = re.compile(r"^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?(/[A-Za-z0-9._~/-]*)?$")
BUILTIN_URL = "https://nim.svn-dev.online"


class SetupError(Exception):
    pass


# ---------------------------------------------------------------------------
# the client
# ---------------------------------------------------------------------------
def client_source(path=None):
    """The canonical nimbridge client, checked so it can ride in a heredoc."""
    with open(path or CLIENT, encoding="utf-8") as f:
        src = f.read()
    if not src.endswith("\n"):
        src += "\n"
    lines = src.split("\n")
    if HEREDOC in lines or CONF_HEREDOC in lines:
        raise SetupError("the nimbridge client has a line equal to the heredoc end marker")
    if "\t" in src:      # a pasted tab can trigger completion in an interactive shell
        raise SetupError("the nimbridge client has tab characters; use spaces")
    try:
        src.encode("ascii")
    except UnicodeEncodeError:
        raise SetupError("the nimbridge client has non-ASCII characters") from None
    return src


def client_version(src=None):
    m = re.search(r"^VER=([0-9A-Za-z.]+)$", src if src is not None else client_source(), re.M)
    return m.group(1) if m else "?"


def client_default_url(src=None):
    m = re.search(r"\$\{URL:-(https?://[^}]+)\}", src if src is not None else client_source())
    return m.group(1) if m else BUILTIN_URL


# ---------------------------------------------------------------------------
# the URL the phone connects to
# ---------------------------------------------------------------------------
def _prefs_path():
    return os.path.join(audiobus.bus_dir(), "bridge.json")


def default_url():
    """Last URL used here -> the named tunnel's hostname -> the running tunnel
    -> the client's own default."""
    try:
        with open(_prefs_path(), encoding="utf-8") as f:
            u = (json.load(f) or {}).get("url") or ""
        if valid_url(u):
            return u
    except (OSError, ValueError):
        pass
    try:
        from . import config, tunnel
        cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        t = tunnel.settings_of(dict(cfg.get("server_settings") or {}))
        h = ((t.get("named") or {}).get("hostname") or "").strip()
        if h and valid_url("https://" + h):
            return "https://" + h
        u = (tunnel.read_status().get("url") or "").strip()
        if valid_url(u):
            return u.rstrip("/")
    except Exception:  # noqa: BLE001 - only a default
        pass
    try:
        return client_default_url()
    except (OSError, SetupError):
        return BUILTIN_URL


def save_url(url):
    audiobus._write_json(_prefs_path(), {"url": url})


def valid_url(url):
    return bool(url) and bool(URL_RE.match(url))


def clean_url(url):
    u = (url or "").strip().rstrip("/")
    if u.endswith("/v1"):
        u = u[:-3]
    if not valid_url(u):
        raise SetupError("give the server's address, like https://lab.example.com (no spaces or quotes)")
    return u


# ---------------------------------------------------------------------------
# names
# ---------------------------------------------------------------------------
def check_name(name):
    """-> the cleaned name, or SetupError saying what is wrong."""
    n = (name or "").strip().lower()
    if not n:
        raise SetupError("a name is needed")
    if n in RESERVED:
        raise SetupError(f"'{n}' is a reserved word on the audio bus; pick another name")
    if not audiobus.NAME_RE.match(n):
        raise SetupError("use 1-32 characters: a-z, 0-9, - and _, starting with a letter or digit "
                         "(e.g. pixel8, work-phone)")
    return n


def registered():
    return {d["name"]: d for d in audiobus.devices()}


# ---------------------------------------------------------------------------
# the block
# ---------------------------------------------------------------------------
def termux_block(name, token, url, mic, src=None):
    """The paste-ready Termux block for one phone (plain ASCII, no tabs)."""
    name = check_name(name)
    url = clean_url(url)
    if not re.match(r"^nab_[A-Za-z0-9_-]+$", token or ""):
        raise SetupError("not an audio bus key")
    mic = "on" if mic in (True, "on", "y", "yes") else "off"
    src = src if src is not None else client_source()
    sha = hashlib.sha256(src.encode("ascii")).hexdigest()
    ver = client_version(src)
    begin = f"# ===== BEGIN NIMBRIDGE SETUP for phone '{name}' (paste from here) ====="
    end = f"# ===== END NIMBRIDGE SETUP for phone '{name}' (paste down to here) ====="
    out = [
        begin,
        "nimbridge_install() {",
        '  if [ -z "${PREFIX:-}" ] || [ ! -d "$PREFIX/bin" ]; then',
        '    echo "This block is for Termux on the phone. Nothing was changed."; return 1',
        "  fi",
        f'  echo "Setting up nimbridge {ver} for phone {name}..."',
        "  pkg install -y curl jq termux-api </dev/null || {",
        '    echo "Installing curl, jq and termux-api failed. Check the connection and paste the block again."',
        "    return 1; }",
        f"  cat > \"$PREFIX/bin/nimbridge\" <<'{HEREDOC}'",
    ]
    out.extend(src.rstrip("\n").split("\n"))
    out += [
        HEREDOC,
        '  if command -v sha256sum >/dev/null 2>&1 &&',
        f'     ! echo "{sha}  $PREFIX/bin/nimbridge" | sha256sum -c --status; then',
        '    rm -f "$PREFIX/bin/nimbridge"',
        '    echo "The script did not paste cleanly (checksum differs). Copy the whole block again."',
        "    return 1",
        "  fi",
        '  chmod 755 "$PREFIX/bin/nimbridge"',
        '  mkdir -p "$HOME/.config/nimbridge" && chmod 700 "$HOME/.config/nimbridge"',
        f"  (umask 077; cat > \"$HOME/.config/nimbridge/config\" <<'{CONF_HEREDOC}'",
        f"URL={shlex.quote(url)}",
        f"DEVICE={shlex.quote(name)}",
        f"TOKEN={shlex.quote(token)}",
        f"MIC={mic}",
        CONF_HEREDOC,
        "  )",
        '  chmod 600 "$HOME/.config/nimbridge/config"',
        '  bash "$PREFIX/bin/nimbridge" init',
        "}",
        "nimbridge_install; unset -f nimbridge_install",
        end,
    ]
    text = "\n".join(out) + "\n"
    text.encode("ascii")
    return text


def instructions(name, mic):
    lines = [
        f"Next, on the phone '{name}':",
        "  1. Install Termux and the Termux:API app (from the same store, e.g. both from F-Droid).",
        "  2. Open Termux and paste this whole block into it, from the BEGIN line to the END line.",
        "     It installs curl, jq and termux-api, writes the nimbridge script and this phone's",
        "     settings, and starts the bridge. The phone asks no questions.",
    ]
    if mic == "on":
        lines.append("  3. When Android asks, allow the microphone for Termux:API (asked once).")
    lines += [
        "  The block holds this phone's key. Paste it only on that phone and don't share it.",
        "Paste this whole block into Termux on the phone you want audio to play through:",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# the interactive flow (io: say / ask / yes / choose, as wizard.IO)
# ---------------------------------------------------------------------------
def _list_line(devs):
    if not devs:
        return "No phones registered yet."
    parts = []
    for d in devs.values():
        tags = ["online" if d["online"] else "offline"] + (["active"] if d["active"] else [])
        parts.append(f"{d['name']} ({', '.join(tags)})")
    return "Phones registered: " + ", ".join(parts)


def ask_name(io):
    """-> (name, reissue) or None when cancelled."""
    while True:
        raw = io.ask("Name for this phone (a-z, 0-9, - and _; e.g. pixel8). Empty cancels", "")
        if not raw.strip():
            return None
        try:
            name = check_name(raw)
        except SetupError as e:
            io.say(f"  [!] {e}")
            continue
        if name not in registered():
            return name, False
        c = io.choose(f"'{name}' is already registered.",
                      [("reissue", f"Give '{name}' a new key (its old key stops working)"),
                       ("other", "Pick another name"), ("cancel", "Cancel")], "other")
        if c == "reissue":
            return name, True
        if c == "cancel":
            return None


def ask_url(io):
    while True:
        raw = io.ask("Server address the phone connects to", default_url())
        try:
            return clean_url(raw)
        except SetupError as e:
            io.say(f"  [!] {e}")


def register_one(io, url=None):
    """One phone: name, mic, key, block. -> (name, url) or None when cancelled."""
    io.say(_list_line(registered()))
    got = ask_name(io)
    if not got:
        io.say("No phone added.")
        return None
    name, reissue = got
    mic = "on" if io.yes("Let voice calls use this phone's mic (only while you hold the turn in a call)?",
                         False) else "off"
    url = url or ask_url(io)
    src = client_source()                       # before the key: a bad client file changes nothing
    token = audiobus.add_device(name)
    try:
        save_url(url)
    except OSError:
        pass
    block = termux_block(name, token, url, mic, src=src)
    io.say("")
    io.say(f"Phone '{name}' {'has a new key' if reissue else 'is registered'} "
           f"(mic for calls: {mic}). Its key, shown once (the server keeps only a hash):")
    io.say(token)
    io.say("")
    io.say(instructions(name, mic))
    io.say("")
    io.say(block.rstrip("\n"))
    io.say("")
    io.say(f"Lost the block? Run this step again and give '{name}' a new key.")
    return name, url


def flow(io):
    """Register phones until the user stops. -> the names registered."""
    io.say("== Phone audio bridge (nimbridge) ==")
    io.say("A registered phone plays Nim Lab audio (voice replies, the voice call) on its speaker,")
    io.say("and can lend its mic to voice calls. Each phone gets its own name and key.")
    done, url = [], None
    while True:
        r = register_one(io, url)
        if r:
            done.append(r[0])
            url = r[1]
        if not io.yes("Register another phone?", False):
            return done


# ---------------------------------------------------------------------------
# wizard step
# ---------------------------------------------------------------------------
def status():
    """-> (ok, text) for the setup step; optional, so always ok."""
    devs = registered()
    if not devs:
        return True, "no phones yet (optional)"
    return True, _list_line(devs).replace("Phones registered: ", f"{len(devs)} phone(s): ")
