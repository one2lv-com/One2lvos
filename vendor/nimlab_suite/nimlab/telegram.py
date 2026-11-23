"""Telegram connector: a BotFather bot that talks to the testbed entity.

The bot token (from @BotFather) is kept in ~/.config/nimlab/telegram_token
(mode 600) and only ever shown masked. Messages go to the running test
server's /v1/chat/completions (model `testbed`), so they use the same
pipeline as every other client: long-term memory (with scope `user`, the
user id is telegram:<user id>), MCP tools, routing and guards. Voice notes
are converted with ffmpeg and sent to /v1/audio/transcriptions (the ASR
role); photos go in as images (the vision role); replies can also be sent as
voice notes through /v1/audio/speech (the TTS role).

Only the IDs on the allowlist get answers; others get a polite refusal (or
nothing, with refusal 'ignore'). `nimlab telegram allow --capture` waits for
the first /start and makes that person the owner. The owner's messages use
the endpoint's admin key when there is one, so they may use the self-admin
tools.

Polling (getUpdates) is the default and needs no public URL. Webhook mode
uses the Cloudflare tunnel: the server answers POST /telegram/webhook and
checks Telegram's secret-token header.
"""

import base64
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

from . import config, store

API = "https://api.telegram.org"
LIMIT = 4096
TOKEN_RX = re.compile(r"^\d{5,16}:[A-Za-z0-9_-]{30,}$")
MDV2_SPECIAL = r"_*[]()~`>#+-=|{}.!\\"
HISTORY_TURNS = 10


# ---------------------------------------------------------------------------
# settings and private files
# ---------------------------------------------------------------------------
def settings(cluster=None):
    c = config.load_cluster_config() if cluster is None else cluster
    t = c.setdefault("telegram_settings", {})
    for k, v in {"allow": [], "owner": None, "mode": "polling", "refusal": "polite", "voice_replies": False,
                 "username": "", "admin_for_owner": True,
                 # 3.8.1: inline mode (owner | allowlist | off), /model switches, the command menu
                 "inline": "owner", "inline_timeout": 8, "model_switch": True, "set_commands": True}.items():
        t.setdefault(k, v)
    return t


def save_settings(t):
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    cfg["telegram_settings"] = t
    config.save_json(config.CLUSTER_CONFIG, cfg)


def save_keys(**kw):
    """Write only these telegram_settings keys, on top of what the file holds
    NOW (3.7.1: a long-running bot saving its whole startup copy could wipe a
    username or an allowlist that setup had just written)."""
    cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
    t = cfg.setdefault("telegram_settings", {})
    t.update(kw)
    config.save_json(config.CLUSTER_CONFIG, cfg)
    return t


# exit codes the service understands (3.7.1): 78 = configuration problem,
# do not restart; 75 = another copy already does this job, check again later
EXIT_CONFIG = 78
EXIT_WAIT = 75
CONFLICT_LIMIT = 4     # consecutive 409 answers before the poller gives up


def lock_path():
    return os.path.join(os.path.dirname(pid_path()), "poller.lock")


def capture_path():
    return os.path.join(os.path.dirname(pid_path()), "capture.json")


class PollerLock:
    """One Telegram poller per data folder: `telegram run` (the service
    child or `telegram start`) and setup's ID capture all take this lock.
    Telegram itself allows only one getUpdates caller per bot (409)."""

    def __init__(self, path=None):
        self.path = path or lock_path()
        self.f = None

    def acquire(self):
        import fcntl
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        f = open(self.path, "a+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.close()
            return False
        f.seek(0)
        f.truncate()
        f.write(str(os.getpid()))
        f.flush()
        self.f = f
        return True

    def release(self):
        if self.f:
            import fcntl
            try:
                fcntl.flock(self.f, fcntl.LOCK_UN)
            finally:
                self.f.close()
                self.f = None

    # -- stale-lock reclaim (3.8.2) ---------------------------------------
    def named(self):
        """The pid written in the lock file (the last owner), or None."""
        try:
            return int(open(self.path).read().strip() or 0) or None
        except (OSError, ValueError):
            return None

    def state(self):
        """-> (state, pid, holders). 'free': nobody holds the lock. 'held': its
        owner (the pid the lock file names: a poller, or setup's ID capture)
        is alive. 'stale': the lock is busy but its owner is gone, so a
        process that inherited the lock (a fork of a dead poller) keeps it
        and nobody polls; it can be reclaimed. holders: [(pid, cmd)] other
        processes that have the lock file open."""
        if self.f:
            return "held", os.getpid(), []
        named = self.named()
        if self.acquire():
            self.release()
            return "free", None, []
        holders = [(p, c) for p, c in lock_holders(self.path) if p != os.getpid()]
        if named and _alive(named) and named != os.getpid():
            return "held", named, holders
        if not named:
            for p, c in holders:
                if _proc_kind(c) == "telegram":
                    return "held", p, holders
        return "stale", named, holders

    def reclaim(self, log=print, wait=5.0, sleep=time.sleep):
        """Take the lock when it is free or stale. A stale lock is freed by
        stopping the Nim Lab processes of this user that still hold it (never
        a live poller, never another program, never this process or its
        parents). -> True when this process now holds the lock."""
        if self.f or self.acquire():
            return True
        st, pid, holders = self.state()
        if st == "free":
            return self.acquire()
        if st == "held":
            return False
        mine = os.getuid()
        skip = _ancestors(os.getpid())
        # only a recognised Nim Lab process (poller, server, supervisor,
        # scheduler) of this user that inherited the lock may be stopped
        bad = [(p, c) for p, c in holders
               if p in skip or _uid_of(p) != mine or _proc_kind(c) is None]
        if bad or not holders:
            who = ", ".join(f"pid {p} ({c[:60]})" for p, c in bad) or f"pid {pid or '?'}"
            log(f"[!] The Telegram poller lock is stale (the owner, pid {pid or '?'}, is not a poller), "
                f"but it is held by {who}, which Nim Lab won't stop. Stop it yourself, then start the bot.")
            return False
        for p, _c in holders:
            try:
                os.kill(p, signal.SIGTERM)
            except OSError:
                pass
        waited = 0.0
        while waited < wait:
            if self.acquire():
                break
            sleep(0.2)
            waited += 0.2
        else:
            for p, _c in holders:
                try:
                    os.kill(p, signal.SIGKILL)
                except OSError:
                    pass
            for _ in range(10):
                if self.acquire():
                    break
                sleep(0.2)
        if self.f:
            log(f"[telegram] reclaimed a stale poller lock (owner pid {pid or '?'} was gone; stopped "
                + ", ".join(f"pid {p}" for p, _c in holders) + ")")
            return True
        log("[!] Could not reclaim the stale Telegram poller lock.")
        return False

    def holder(self):
        """pid of the process holding the lock, or None when it is free."""
        if self.f:
            return os.getpid()
        if self.acquire():
            self.release()
            return None
        try:
            return int(open(self.path).read().strip() or 0) or -1
        except (OSError, ValueError):
            return -1


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _cmdline(pid):
    try:
        with open(f"/proc/{int(pid)}/cmdline", "rb") as f:
            return f.read().replace(b"\0", b" ").decode("utf-8", "replace").strip()
    except (OSError, ValueError):
        return ""


def _uid_of(pid):
    try:
        return os.stat(f"/proc/{int(pid)}").st_uid
    except (OSError, ValueError):
        return None


def _proc_kind(cmd):
    from .updater import kind_of
    return kind_of(cmd or "")


def _ancestors(pid):
    out, cur = {pid}, pid
    for _ in range(64):
        try:
            with open(f"/proc/{cur}/stat") as f:
                cur = int(f.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
        if cur <= 1 or cur in out:
            break
        out.add(cur)
    return out


def lock_holders(path):
    """[(pid, cmd)] processes that have the lock file open (Linux /proc)."""
    rp = os.path.realpath(path)
    out = []
    try:
        names = os.listdir("/proc")
    except OSError:
        return out
    for d in names:
        if not d.isdigit():
            continue
        try:
            fds = os.listdir(f"/proc/{d}/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                if os.readlink(f"/proc/{d}/fd/{fd}") == rp:
                    out.append((int(d), _cmdline(d)))
                    break
            except OSError:
                continue
    return out


def _cfg_dir():
    from .tunnel import config_dir
    return config_dir()


def token_path():
    return os.environ.get("NIMLAB_TELEGRAM_TOKEN_FILE") or os.path.join(_cfg_dir(), "telegram_token")


def secret_path():
    return os.path.join(_cfg_dir(), "telegram_webhook_secret")


def load_token():
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        return os.environ["TELEGRAM_BOT_TOKEN"].strip()
    try:
        with open(token_path(), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def clean_token(tok):
    tok = re.sub(r"\s+", "", tok or "")
    m = re.search(r"\d{5,16}:[A-Za-z0-9_-]{30,}", tok)
    return m.group(0) if m else tok


def save_token(tok):
    from .tunnel import write_private
    tok = clean_token(tok)
    if not TOKEN_RX.match(tok):
        raise ValueError("That is not a bot token. BotFather's token looks like 123456789:AAE... "
                         "(digits, a colon, then about 35 letters).")
    write_private(token_path(), tok + "\n")
    return tok


def webhook_secret():
    from .tunnel import write_private
    try:
        with open(secret_path(), encoding="utf-8") as f:
            s = f.read().strip()
        if s:
            return s
    except OSError:
        pass
    s = secrets.token_urlsafe(32)
    write_private(secret_path(), s + "\n")
    return s


def mask(tok):
    if not tok:
        return "(none)"
    bot_id = tok.split(":", 1)[0]
    return f"{bot_id}:***{tok[-4:]}"


# ---------------------------------------------------------------------------
# Telegram Bot API
# ---------------------------------------------------------------------------
class TelegramError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


def _http(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _multipart(fields, files):
    b = uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out += [f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n".encode(), str(v).encode(), b"\r\n"]
    for k, (name, data, mime) in files.items():
        out += [f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{name}\"\r\n"
                f"Content-Type: {mime}\r\n\r\n".encode(), data, b"\r\n"]
    out.append(f"--{b}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={b}"


class Bot:
    """The Bot API over HTTPS. `http(url, data, headers, timeout)` returns
    (status, bytes); tests pass a fake. The token never appears in errors."""

    def __init__(self, token, http=_http, base=API):
        self.token, self.http, self.base = token, http, base

    def _url(self, method):
        return f"{self.base}/bot{self.token}/{method}"

    def call(self, method, http_timeout=60, files=None, **params):
        params = {k: v for k, v in params.items() if v is not None}
        if files:
            data, ctype = _multipart(params, files)
        else:
            data, ctype = json.dumps(params).encode(), "application/json"
        try:
            status, raw = self.http(self._url(method), data, {"Content-Type": ctype}, http_timeout)
        except (OSError, urllib.error.URLError) as e:
            raise TelegramError(f"cannot reach Telegram ({str(e).replace(self.token, '***')})") from None
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            raise TelegramError(f"Telegram answered {status} with something that is not JSON", status) from None
        if not body.get("ok"):
            raise TelegramError(body.get("description") or f"HTTP {status}", body.get("error_code") or status)
        return body.get("result")

    def download(self, file_id, timeout=60):
        info = self.call("getFile", file_id=file_id)
        url = f"{self.base}/file/bot{self.token}/{info['file_path']}"
        status, raw = self.http(url, None, {}, timeout)
        if status != 200:
            raise TelegramError(f"could not download the file (HTTP {status})", status)
        return raw


# ---------------------------------------------------------------------------
# formatting
# ---------------------------------------------------------------------------
def escape_mdv2(text):
    return re.sub(r"([" + re.escape(MDV2_SPECIAL) + r"])", r"\\\1", text)


def to_mdv2(text):
    """The entity's Markdown as Telegram MarkdownV2: code blocks and inline
    code kept, **bold** -> *bold*, everything else escaped."""
    out = []
    parts = re.split(r"(```[\s\S]*?```|`[^`\n]+`)", text)
    for p in parts:
        if p.startswith("```") and p.endswith("```") and len(p) >= 6:
            inner = p[3:-3]
            out.append("```" + re.sub(r"([`\\])", r"\\\1", inner) + "```")
        elif p.startswith("`") and p.endswith("`") and len(p) >= 2:
            out.append("`" + re.sub(r"([`\\])", r"\\\1", p[1:-1]) + "`")
        else:
            segs = re.split(r"\*\*(.+?)\*\*", p)
            for i, s in enumerate(segs):
                out.append(("*" + escape_mdv2(s) + "*") if i % 2 else escape_mdv2(s))
    return "".join(out)


def split_text(text, limit=LIMIT):
    """Pieces of at most `limit` characters, cut at a paragraph, line or
    space when possible, never inside a ``` block when it can be helped."""
    text = text.strip() or "(empty reply)"
    pieces = []
    room = limit - 4                       # room for a closing "\n```" when a cut lands inside a code block
    while len(text) > limit:
        cut = -1
        for sep in ("\n\n", "\n", " "):
            cut = text.rfind(sep, int(room * 0.5), room)
            if cut > 0:
                break
        if cut <= 0:
            cut = limit if text[:limit].count("```") % 2 == 0 else room
        head = text[:cut]
        if head.count("```") % 2:          # close an open code block and reopen it
            head += "\n```"
            text = "```\n" + text[cut:].lstrip("\n")
        else:
            text = text[cut:].lstrip()
        pieces.append(head.rstrip())
    if text:
        pieces.append(text)
    return pieces


# ---------------------------------------------------------------------------
# the backend: the running test server
# ---------------------------------------------------------------------------
class Backend:
    def __init__(self, http=_http, base=None, key=None, admin_key=None, model=None):
        from . import server as S
        from . import selfadmin
        s = S.load_settings()
        self.http = http
        self.base = base or f"http://127.0.0.1:{s.get('port', 8765)}/v1"
        self.key = key if key is not None else s.get("api_key", "")
        self.admin_key = admin_key if admin_key is not None else selfadmin.load_admin_key()
        self.model = model or s.get("model_name") or "testbed"

    def _post(self, path, data, ctype, user, admin, timeout=300):
        headers = {"Content-Type": ctype, "Authorization": "Bearer " + (self.admin_key if admin and self.admin_key
                                                                          else self.key),
                   "X-Testbed-User": user}
        status, raw = self.http(self.base + path, data, headers, timeout)
        if status != 200:
            try:
                msg = json.loads(raw)["error"]["message"]
            except (ValueError, KeyError, TypeError):
                msg = (raw or b"")[:200].decode("utf-8", "replace")
            raise RuntimeError(f"server {status}: {msg}")
        return raw

    def chat(self, messages, user, admin=False):
        body = {"model": self.model, "messages": messages, "user": user}
        raw = self._post("/chat/completions", json.dumps(body).encode(), "application/json", user, admin)
        return json.loads(raw)["choices"][0]["message"]["content"] or ""

    def transcribe(self, wav, user):
        data, ctype = _multipart({"model": self.model}, {"file": ("voice.wav", wav, "audio/wav")})
        raw = self._post("/audio/transcriptions", data, ctype, user, False)
        try:
            return json.loads(raw).get("text", "")
        except ValueError:
            return raw.decode("utf-8", "replace")

    def speech(self, text, user):
        body = {"model": self.model, "input": text[:1500], "response_format": "wav"}
        return self._post("/audio/speech", json.dumps(body).encode(), "application/json", user, False)


def ffmpeg(data, args, suffix_in, suffix_out, run=subprocess.run):
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg is not installed (pkg install ffmpeg)")
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in" + suffix_in), os.path.join(d, "out" + suffix_out)
        with open(src, "wb") as f:
            f.write(data)
        r = run([exe, "-y", "-loglevel", "error", "-i", src, *args, dst], capture_output=True, timeout=120)
        if r.returncode != 0 or not os.path.exists(dst):
            raise RuntimeError("ffmpeg could not convert the audio")
        with open(dst, "rb") as f:
            return f.read()


# ---------------------------------------------------------------------------
# the connector
# ---------------------------------------------------------------------------
class Connector:
    def __init__(self, bot, backend, tsettings=None, save=None, convert=ffmpeg, log=print, capture_file=None):
        self.bot, self.backend = bot, backend
        self.t = tsettings if tsettings is not None else settings()
        self.save = save or (lambda: save_keys(allow=list(self.t.get("allow") or []), owner=self.t.get("owner")))
        self.capture_file = capture_file
        self.convert, self.log = convert, log
        self.history = {}
        self.inflight = {}          # chat_id -> threading.Event (set by /cancel)
        self._chat_locks = {}
        self.threaded = False       # run() turns it on: replies off the poller thread
        self._buttons = {}
        self.capture = False
        self.lock = threading.Lock()
        self.offset = None      # kept across poll() calls: capture polls once at a time
        self._ledger = None
        self.skipped = 0

    @property
    def ledger(self):
        if self._ledger is None:
            self._ledger = UpdateLedger(bot_id_of(self.bot))
        return self._ledger

    def claim(self, update):
        """True when this update is new here; duplicates are skipped and
        counted (at most one reply per update_id, however many pollers)."""
        uid = update.get("update_id")
        if uid is None:
            return True
        try:
            ok = self.ledger.claim(uid)
        except OSError as e:          # the ledger is a guard: a disk error never stops the bot
            self.log(f"[telegram] update ledger: {e}")
            return True
        if not ok:
            self.skipped += 1
            self.log(f"[telegram] skipped update {uid}: already handled")
        return ok

    def confirm(self):
        """Tell Telegram the updates below self.offset are done, so they
        are not delivered again (getUpdates with offset confirms them)."""
        if self.offset is None:
            return
        try:
            self.bot.call("getUpdates", http_timeout=15, offset=self.offset, timeout=0, limit=1,
                          allowed_updates=ALLOWED_UPDATES)
        except TelegramError as e:
            self.log(f"[telegram] could not confirm offset {self.offset}: {e}")

    # -- access ---------------------------------------------------------
    def allowed(self, uid, chat_id):
        allow = {str(x) for x in self.t.get("allow") or []}
        return str(uid) in allow or str(chat_id) in allow

    def is_owner(self, uid):
        return self.t.get("owner") is not None and str(uid) == str(self.t["owner"])

    def add_allowed(self, uid, owner=False):
        allow = [str(x) for x in self.t.get("allow") or []]
        if str(uid) not in allow:
            allow.append(str(uid))
        self.t["allow"] = allow
        if owner or not self.t.get("owner"):
            self.t["owner"] = str(uid)
        self.save()

    def _capture_requested(self):
        """Setup asks the RUNNING bot to capture (a flag file), instead of
        starting a second poller that Telegram would refuse with 409."""
        if not self.capture_file:
            return False
        try:
            d = json.load(open(self.capture_file))
            return float(d.get("until", 0)) > time.time()
        except (OSError, ValueError):
            return False

    def _end_capture_request(self, uid):
        if self.capture_file:
            try:
                with open(self.capture_file, "w") as f:
                    json.dump({"until": 0, "owner": str(uid)}, f)
            except OSError:
                pass

    def refresh(self):
        """Pick up allowlist/owner changes another process saved."""
        try:
            fresh = (config.load_json(config.CLUSTER_CONFIG, {}) or {}).get("telegram_settings") or {}
        except Exception:  # noqa: BLE001
            return
        for k in ("allow", "owner", "username", "refusal", "voice_replies", "inline", "model_switch",
                  "inline_timeout"):
            if k in fresh:
                self.t[k] = fresh[k]

    # -- sending --------------------------------------------------------
    def send(self, chat_id, text, reply_to=None, markup=None):
        pieces = split_text(text)
        for i, piece in enumerate(pieces):
            kb = markup if i == len(pieces) - 1 else None    # buttons ride the last piece
            try:
                self.bot.call("sendMessage", chat_id=chat_id, text=to_mdv2(piece), parse_mode="MarkdownV2",
                              reply_to_message_id=reply_to, allow_sending_without_reply=True, reply_markup=kb)
            except TelegramError as e:
                if e.code == 400:   # the Markdown did not parse: send it plain
                    self.bot.call("sendMessage", chat_id=chat_id, text=piece, reply_to_message_id=reply_to,
                                  allow_sending_without_reply=True, reply_markup=kb)
                else:
                    raise
            reply_to = None

    def _typing(self, chat_id, action, stop):
        while not stop.is_set():
            try:
                self.bot.call("sendChatAction", chat_id=chat_id, action=action, http_timeout=10)
            except TelegramError:
                pass
            stop.wait(4.5)

    # -- one update -----------------------------------------------------
    def handle(self, update):
        if update.get("callback_query") or update.get("inline_query"):
            from . import tgui                    # 3.8.1: buttons and inline mode
            try:
                if update.get("callback_query"):
                    return tgui.handle_callback(self, update["callback_query"])
                if self.threaded:                 # an inline answer may wait for Quill: off the poller
                    threading.Thread(target=tgui.handle_inline, args=(self, update["inline_query"]),
                                     daemon=True, name="tg-inline").start()
                    return None
                return tgui.handle_inline(self, update["inline_query"])
            except Exception as e:  # noqa: BLE001 - never stops the poller
                self.log(f"[telegram] update failed: {type(e).__name__}: {e}")
                return None
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return
        chat_id = msg["chat"]["id"]
        uid = (msg.get("from") or {}).get("id", chat_id)
        text = (msg.get("text") or msg.get("caption") or "").strip()
        cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
        if cmd == "/id":
            return self.send(chat_id, f"Your Telegram user ID is {uid}; this chat is {chat_id}.")
        if not self.allowed(uid, chat_id):
            if (self.capture or self._capture_requested()) and cmd == "/start":
                self.add_allowed(uid, owner=True)
                self.capture = False
                self._end_capture_request(uid)
                self.log(f"[ok] Owner captured: {uid} (saved to the allowlist)")
                return self.send(chat_id, "You're connected as the owner of this testbed. Say hello!")
            self.log(f"[telegram] ignored a message from {uid} (not on the allowlist)")
            if self.t.get("refusal", "polite") == "polite" and msg["chat"].get("type") == "private":
                self.send(chat_id, f"Sorry, this bot is private. (Your ID is {uid}, if the owner wants to add you.)")
            return
        if cmd:
            try:                                  # 3.8.0: slash commands (nimlab.tgcmds)
                from . import tgcmds
                if tgcmds.handle(self, chat_id, uid, cmd, text):
                    return None
            except Exception as e:  # noqa: BLE001 - a broken command never stops the poller
                self.log(f"[telegram] command {cmd} failed: {type(e).__name__}: {e}")
        if cmd in ("/start", "/help"):
            return self.send(chat_id, "Hi! Send text, a photo or a voice note. /reset clears this chat's "
                                      "short-term history; /id shows your ID.")
        if cmd == "/reset":
            self.history.pop(chat_id, None)
            return self.send(chat_id, "Cleared this chat's history (long-term memory is kept).")
        cancel = threading.Event()
        old = self.inflight.get(chat_id)
        if old is not None:
            old.set()                             # a newer message replaces a reply still in progress
        self.inflight[chat_id] = cancel
        if self.threaded:                         # 3.8.1: the poller stays free for /cancel
            threading.Thread(target=self._reply, args=(msg, chat_id, uid, text, cancel), daemon=True,
                             name=f"tg-reply-{chat_id}").start()
            return None
        return self._reply(msg, chat_id, uid, text, cancel)

    def _reply(self, msg, chat_id, uid, text, cancel=None):
        cancel = cancel or threading.Event()
        lock = self._chat_locks.setdefault(chat_id, threading.Lock())
        with lock:
            try:
                return self._reply_locked(msg, chat_id, uid, text, cancel)
            finally:
                if self.inflight.get(chat_id) is cancel:
                    self.inflight.pop(chat_id, None)

    def _reply_locked(self, msg, chat_id, uid, text, cancel):
        if cancel.is_set():
            return None
        stop = threading.Event()
        action = "record_voice" if (msg.get("voice") or msg.get("audio")) and self.t.get("voice_replies") \
            else "typing"
        threading.Thread(target=self._typing, args=(chat_id, action, stop), daemon=True).start()
        user = f"telegram:{uid}"
        try:
            content, heard = self._content(msg, text, user)
            if content is None:
                return self.send(chat_id, "I can read text, photos and voice notes.")
            hist = self.history.setdefault(chat_id, [])
            msgs = hist[-HISTORY_TURNS * 2:] + [{"role": "user", "content": content}]
            reply = self.backend.chat(msgs, user, admin=self.is_owner(uid) and self.t.get("admin_for_owner", True))
            if cancel.is_set():                   # /cancel (or a newer message) while Quill was thinking
                stop.set()
                self.log(f"[telegram] reply for chat {chat_id} dropped (cancelled)")
                return None
            hist += [{"role": "user", "content": heard or (text or "[photo]")}, {"role": "assistant",
                                                                                "content": reply}]
            del hist[:-HISTORY_TURNS * 2]
            if heard:
                # plain text: to_mdv2 escapes underscores, so _italics_ would show literally
                reply_txt = f"Heard: \"{heard}\"\n\n{reply}" if len(heard) < 300 else reply
            else:
                reply_txt = reply
            stop.set()
            if (msg.get("voice") or msg.get("audio")) and self.t.get("voice_replies"):
                if self._voice_reply(chat_id, reply, user):
                    return
            self.send(chat_id, reply_txt, reply_to=msg.get("message_id"))
        except Exception as e:  # noqa: BLE001 - one bad message never stops the bot
            stop.set()
            self.log(f"[telegram] error for {uid}: {type(e).__name__}: {e}")
            try:
                self.send(chat_id, error_text(e))
            except Exception:  # noqa: BLE001
                pass
        finally:
            stop.set()

    def _content(self, msg, text, user):
        if msg.get("photo"):
            ph = max(msg["photo"], key=lambda p: p.get("file_size") or p.get("width", 0))
            data = self.bot.download(ph["file_id"])
            url = "data:image/jpeg;base64," + base64.b64encode(data).decode()
            return [{"type": "text", "text": text or "What is in this picture?"},
                    {"type": "image_url", "image_url": {"url": url}}], None
        if msg.get("voice") or msg.get("audio"):
            f = msg.get("voice") or msg.get("audio")
            data = self.bot.download(f["file_id"])
            wav = self.convert(data, ["-ar", "16000", "-ac", "1"], ".ogg", ".wav")
            heard = (self.backend.transcribe(wav, user) or "").strip()
            if not heard:
                raise RuntimeError("I couldn't make out any words in that voice note")
            return heard, heard
        if text:
            return text, None
        return None, None

    def _autoplay(self, wav):
        """/autoplay: also play the reply on the phone speaker. Never fails the reply."""
        try:
            from . import tgcmds
            tgcmds.autoplay(wav, ".wav", self.log)
        except Exception as e:  # noqa: BLE001
            self.log(f"[telegram] autoplay failed: {e}")

    def _voice_reply(self, chat_id, reply, user):
        try:
            wav = self.backend.speech(reply, user)
            ogg = self.convert(wav, ["-c:a", "libopus", "-b:a", "32k"], ".wav", ".ogg")
            self.bot.call("sendVoice", chat_id=chat_id, files={"voice": ("reply.ogg", ogg, "audio/ogg")})
            self._autoplay(wav)
            if len(reply) > 200:
                self.send(chat_id, reply)
            return True
        except Exception as e:  # noqa: BLE001 - fall back to text
            self.log(f"[telegram] voice reply failed: {e}")
            return False

    # -- polling --------------------------------------------------------
    def poll(self, stop=None, once=False, timeout=30, sleep=time.sleep, conflict_limit=CONFLICT_LIMIT,
             refresh_every=30):
        """Long-poll getUpdates. Returns 0 when stopped, 1 on a wrong token,
        EXIT_CONFIG when Telegram keeps answering 409 (another copy of this
        bot polls somewhere else: it never fixes itself, so retrying forever
        only fills the log)."""
        stop = stop or threading.Event()
        if self.offset is None:   # resume after the last update handled here (shared ledger)
            try:
                last = self.ledger.last()
            except OSError:
                last = None
            if last is not None:
                self.offset = last + 1
        if not getattr(self, "_webhook_deleted", False):
            try:
                self.bot.call("deleteWebhook", drop_pending_updates=False)
                self._webhook_deleted = True
            except TelegramError as e:
                self.log(f"[telegram] deleteWebhook: {e}")
        delay = 1
        conflicts = 0
        last_refresh = time.time()
        while not stop.is_set():
            try:
                ups = self.bot.call("getUpdates", http_timeout=timeout + 15, offset=self.offset, timeout=timeout,
                                    allowed_updates=ALLOWED_UPDATES) or []
                delay = 1
                conflicts = 0
            except TelegramError as e:
                if e.code == 401:
                    self.log("[x] Telegram says the bot token is wrong (401). Set it again: telegram set-token")
                    return 1
                if e.code == 409:
                    conflicts += 1
                    self.last_conflict = True
                    self.log("[!] Another copy of this bot is polling (409). Stop it, or use one place only.")
                    if conflict_limit and conflicts >= conflict_limit:
                        self.log(CONFLICT_HELP)
                        return EXIT_CONFIG
                self.log(f"[telegram] {e}; retrying in {delay} s")
                sleep(delay)
                delay = min(60, delay * 2)
                if once:
                    return 1
                continue
            for u in ups:
                # offset first: an update that fails is never fetched again
                self.offset = max(self.offset or 0, u["update_id"] + 1)
                if self.claim(u):
                    self.handle(u)
            if once:
                return 0
            if refresh_every and time.time() - last_refresh > refresh_every:
                self.refresh()
                last_refresh = time.time()
        return 0


def _short(e):
    s = str(e)
    if "401" in s and not PLAIN_FAIL.search(s):
        return "the server refused the key."
    if "Connection refused" in s or "urlopen" in s:
        return "the testbed server is not running."
    s = re.sub(r"^server 5\d\d: ", "", s)          # v3.8.3: no raw "server 502:" in the chat
    if PLAIN_FAIL.search(s):
        return (s[:500] + "...") if len(s) > 500 else s
    return (s[:160] + "...") if len(s) > 160 else s


PLAIN_FAIL = re.compile(r"^(NVIDIA's model|The model at) ")


def error_text(e):
    """What the chat shows when a reply failed. When every model failed the
    server already says why in plain words, so no 'went wrong on my side'."""
    s = _short(e)
    return s if PLAIN_FAIL.search(s) else "Sorry, something went wrong on my side: " + s


# ---------------------------------------------------------------------------
# webhook (the server calls handle_webhook)
# ---------------------------------------------------------------------------
_hook = {"conn": None}


ALLOWED_UPDATES = ["message", "edited_message", "callback_query", "inline_query"]   # 3.8.1


def handle_webhook(headers, raw):
    """POST /telegram/webhook on the test server. Returns an HTTP status."""
    import hmac
    given = headers.get("X-Telegram-Bot-Api-Secret-Token") or ""
    try:
        with open(secret_path(), encoding="utf-8") as f:
            want = f.read().strip()
    except OSError:
        want = ""
    if not want or not hmac.compare_digest(given.encode(), want.encode()):
        return 403
    try:
        update = json.loads(raw or b"{}")
    except ValueError:
        return 400
    if _hook["conn"] is None:
        tok = load_token()
        if not tok:
            return 503
        _hook["conn"] = Connector(Bot(tok), Backend())
        _hook["conn"].threaded = True
    if not _hook["conn"].claim(update):   # Telegram retries webhooks: answer each update once
        return 200
    threading.Thread(target=_hook["conn"].handle, args=(update,), daemon=True).start()
    return 200


def set_webhook(bot, public_url):
    url = public_url.rstrip("/") + "/telegram/webhook"
    bot.call("setWebhook", url=url, secret_token=webhook_secret(), allowed_updates=ALLOWED_UPDATES,
             drop_pending_updates=False)
    return url


# ---------------------------------------------------------------------------
# status, run, CLI
# ---------------------------------------------------------------------------
def pid_path():
    d = os.path.join(store.data_dir(), "telegram")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "bot.pid")


LEDGER_STALE_SEC = 7 * 24 * 3600   # Telegram may restart update_ids after a week without updates


def ledger_path():
    return os.path.join(os.path.dirname(pid_path()), "last_update.json")


class UpdateLedger:
    """The last handled update_id per bot, in one shared file under an
    exclusive lock (3.7.1). Every poller and the webhook claim an update
    here before answering it, so even duplicate pollers (or a poller that
    has not confirmed its offset yet) never answer one update twice."""

    def __init__(self, bot_id, path=None, clock=time.time):
        self.bot_id = str(bot_id or "bot")
        self.path = path or ledger_path()
        self.clock = clock

    def _open(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        return open(self.path, "a+", encoding="utf-8")

    @staticmethod
    def _read(f):
        f.seek(0)
        try:
            d = json.loads(f.read() or "{}")
        except ValueError:
            d = {}
        return d if isinstance(d, dict) else {}

    def last(self):
        """The last handled update_id, or None (none yet, or stale)."""
        import fcntl
        with self._open() as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                e = self._read(f).get(self.bot_id) or {}
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        if not e or self.clock() - float(e.get("at") or 0) > LEDGER_STALE_SEC:
            return None
        return int(e.get("id", 0))

    def claim(self, update_id):
        """True when this caller may handle update_id (it is newer than the
        last one handled); records it. False for a duplicate."""
        import fcntl
        update_id = int(update_id)
        with self._open() as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                d = self._read(f)
                e = d.get(self.bot_id) or {}
                fresh = e and self.clock() - float(e.get("at") or 0) <= LEDGER_STALE_SEC
                if fresh and update_id <= int(e.get("id", 0)):
                    return False
                d[self.bot_id] = {"id": update_id, "at": self.clock()}
                f.seek(0)
                f.truncate()
                f.write(json.dumps(d))
                f.flush()
                os.fsync(f.fileno())
                return True
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)


def bot_id_of(bot):
    tok = getattr(bot, "token", "") or ""
    return tok.split(":", 1)[0] if ":" in tok else (tok[:12] or "bot")


def status_path():
    return os.path.join(os.path.dirname(pid_path()), "status.json")


def running_pid():
    try:
        pid = int(open(pid_path()).read().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def brief():
    t = settings()
    if not load_token():
        return "not set up"
    from . import service
    st = config.load_json(status_path(), {}) or {}
    up = bool(running_pid()) or (service.settings().get("telegram") and service.read_state().get("running"))
    n = len(t.get("allow") or [])
    name = f"@{t['username']}" if t.get("username") else "@? (run: nimlab telegram test)"
    out = (f"{name} {t.get('mode', 'polling')}, {'running' if up else 'stopped'}, "
           f"{n} allowed" + (" (config: nobody can chat; nimlab telegram allow --capture)" if not n else "")
           + (f", last error: {st['error'][:60]}" if st.get("error") and not up else ""))
    return out


CONFLICT_HELP = ("[x] Telegram keeps answering 409 Conflict: another program is polling this same bot token. "
                 "Usually that is an older Nim Lab still running (a second service or supervisor, a stray "
                 "`telegram run`, or an install in another folder), another phone or PC, or a webhook tool. "
                 "Stop it (nimlab service status lists stray copies; nimlab service cleanup stops them), "
                 "or make a new token with @BotFather /revoke. Not retrying (config error).")


def run(stop=None, log=print, bot=None, lock=None):
    """`telegram run`: the bot in the foreground (the service runs this).
    Exit codes: 2 no token, EXIT_CONFIG wrong token / sustained 409,
    EXIT_WAIT another poller already runs from this folder."""
    tok = load_token()
    if not tok:
        log("[x] No bot token: nimlab telegram set-token")
        return EXIT_CONFIG
    t = settings()
    bot = bot or Bot(tok)
    stop = stop or threading.Event()
    lock = lock or PollerLock()
    if not lock.acquire() and not lock.reclaim(log):
        log(f"[!] Another Nim Lab Telegram poller already runs from this folder (pid {lock.holder()}). Only "
            "one may poll a bot. Not starting a second one.")
        return EXIT_WAIT
    try:
        with open(pid_path(), "w") as f:
            f.write(str(os.getpid()))
        config.save_json(status_path(), {"started_at": config.timestamp(), "mode": t["mode"]})
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, lambda *_: stop.set())
            except ValueError:
                pass
        try:   # resolve and save the bot's @name (the header said @? forever)
            me = bot.call("getMe")
            if me.get("username") and me.get("username") != t.get("username"):
                t["username"] = me["username"]
                save_keys(username=me["username"])
        except TelegramError as e:
            if e.code == 401:
                log("[x] Telegram says the bot token is wrong (401). Set it again: nimlab telegram set-token")
                _status_error("token refused (401)")
                return EXIT_CONFIG
            log(f"[telegram] getMe: {e}")
        from . import tgui                        # 3.8.1: the bot sets its own command menu
        tgui.register_commands(bot, t, log=log)
        if not t.get("allow"):
            log("[!] Nobody is on the allowlist yet, so the bot answers only /id. Add yourself: "
                "nimlab telegram allow --capture (send /start) or nimlab telegram allow <your id>")
        if t["mode"] == "webhook":
            from . import tunnel
            current = None
            while not stop.is_set():
                st = tunnel.read_status()
                url = st.get("url") if st.get("state") == "up" else None
                if url and url != current:
                    try:
                        log(f"[ok] Webhook set: {set_webhook(bot, url)}")
                        current = url
                    except TelegramError as e:
                        log(f"[telegram] setWebhook failed: {e}")
                elif not url and current is None:
                    log("[!] Webhook mode needs the tunnel up (serve tunnel quick|named, auto on); waiting.")
                stop.wait(60)
            return 0
        log(f"[ok] Telegram bot @{t.get('username') or '?'} polling; Ctrl-C stops.")
        conn = Connector(bot, Backend(), t, log=log, capture_file=capture_path())
        conn.threaded = True
        code = conn.poll(stop)
        if code != EXIT_CONFIG:
            conn.confirm()
        if code == EXIT_CONFIG:
            _status_error("409 conflict: another copy polls this bot")
        return code
    finally:
        try:
            os.unlink(pid_path())
        except OSError:
            pass
        lock.release()


def _status_error(msg):
    try:
        st = config.load_json(status_path(), {}) or {}
        st.update(error=msg, error_at=config.timestamp())
        config.save_json(status_path(), st)
    except OSError:
        pass


def capture_owner(conn, seconds=120, log=print, lock=None, sleep=time.sleep, clock=time.time):
    """Wait for /start and make its sender the owner. 3.7.1:
    - when a Nim Lab bot already polls from this folder (the service), it is
      asked to capture (a flag file) and this waits for the saved allowlist,
      instead of a second poller that Telegram answers with 409 for minutes;
    - a 409 from a poller elsewhere ends the wait at once, with the reason;
    - progress every 10 s; the result is read back from config_cluster.json."""
    lock = lock or PollerLock()
    who = conn.t.get("username")
    end = clock() + seconds
    if not lock.acquire():
        pid = lock.holder()
        log(f"The bot is already running here (pid {pid}, the service); asking it to capture.")
        log(f"Send /start to @{who or 'your bot'} in Telegram now (waiting up to {seconds} s; Ctrl+C stops)...")
        try:
            with open(capture_path(), "w") as f:
                json.dump({"until": end}, f)
        except OSError as e:
            log(f"[x] Could not ask the running bot: {e}")
            return None
        nxt = clock() + 10
        try:
            while clock() < end:
                fresh = settings()
                if fresh.get("owner") and fresh.get("allow"):
                    conn.t.update(owner=fresh["owner"], allow=fresh["allow"])
                    log(f"[ok] Owner captured by the running bot: {fresh['owner']}")
                    return str(fresh["owner"])
                if clock() >= nxt:
                    log(f"  ... still waiting for /start ({int(end - clock())} s left)")
                    nxt = clock() + 10
                sleep(1)
        finally:
            try:
                with open(capture_path(), "w") as f:
                    json.dump({"until": 0}, f)
            except OSError:
                pass
        return None
    try:
        conn.capture = True
        conn.last_conflict = False
        log(f"Send /start to @{who or 'your bot'} in Telegram now (waiting up to {seconds} s; Ctrl+C stops)...")
        stop = threading.Event()
        nxt = clock() + 10
        while conn.capture and clock() < end:
            conn.poll(stop, once=True, timeout=min(10, max(1, int(end - clock()))), sleep=lambda _s: None)
            if getattr(conn, "last_conflict", False):
                log(CONFLICT_HELP.replace(" Not retrying (config error).", ""))
                log("Or type your ID by hand: send /id to the bot wherever it does answer, then: "
                    "nimlab telegram allow <id>")
                break
            if conn.capture and clock() >= nxt:
                log(f"  ... still waiting for /start ({int(end - clock())} s left)")
                nxt = clock() + 10
        conn.capture = False
        if not getattr(conn, "last_conflict", False):
            conn.confirm()      # 3.7.0 never confirmed: the next poll got the same /start again
        owner = conn.t.get("owner")
        if owner:   # read back what was really saved
            saved = settings()
            if str(saved.get("owner")) != str(owner) or str(owner) not in [str(x) for x in saved.get("allow") or []]:
                save_keys(owner=str(owner), allow=sorted({*map(str, saved.get("allow") or []), str(owner)}))
        return owner
    finally:
        lock.release()


def cmd_telegram(args):
    from getpass import getpass
    import sys
    act, v = args.action, list(args.values or [])
    t = settings()
    if act == "run":
        return run()
    if act == "set-token":
        tok = getpass("Bot token from @BotFather (hidden): ") if sys.stdin.isatty() else sys.stdin.readline()
        try:
            tok = save_token(tok)
        except ValueError as e:
            print(f"[x] {e}")
            return 2
        print(f"[ok] Saved {mask(tok)} to {token_path()} (mode 600).")
        act = "test"
    tok = load_token()
    if act == "status":
        print(f"token     : {mask(tok)}")
        print(f"bot       : @{t.get('username') or '?'}")
        print(f"mode      : {t['mode']}   voice replies: {'on' if t['voice_replies'] else 'off'}   "
              f"refusal: {t['refusal']}")
        print(f"allowlist : {', '.join(map(str, t['allow'])) or '(empty: nobody gets answers)'}"
              + (f"   owner {t['owner']}" if t.get("owner") else ""))
        print(f"running   : {brief()}")
        return 0
    if not tok:
        print("[x] No bot token yet: nimlab telegram set-token")
        return 2
    bot = Bot(tok)
    if act == "test":
        try:
            me = bot.call("getMe")
        except TelegramError as e:
            print(f"[x] Telegram did not accept the token: {e}" if e.code == 401 else f"[x] {e}")
            return 1
        t["username"] = me.get("username", "")
        save_settings(t)
        print(f"[ok] Connected: @{t['username']} ({me.get('first_name', '')}), bot id {me.get('id')}")
        return 0
    if act == "allow":
        conn = Connector(bot, None, t, log=print)
        if args.capture or not v:
            if not t.get("username"):
                try:
                    t["username"] = bot.call("getMe").get("username", "")
                    if t["username"]:
                        save_keys(username=t["username"])
                except TelegramError:
                    pass
            secs = int(v[0]) if v and v[0].isdigit() else 120
            owner = capture_owner(conn, seconds=secs)
            saved = settings()
            if owner:
                print(f"[ok] Owner: {owner}. Saved: allowlist {', '.join(map(str, saved['allow'])) or '(empty)'}, "
                      f"bot @{saved.get('username') or '?'}")
            else:
                print("[!] No /start arrived. Add your ID by hand: send /id to the bot, then "
                      "nimlab telegram allow <id>")
            return 0 if owner else 1
        for x in v:
            if args.remove:
                t["allow"] = [a for a in t["allow"] if str(a) != x]
            elif re.fullmatch(r"-?\d{3,20}", x):
                conn.add_allowed(x)   # the first ID added also becomes the owner
            else:
                print(f"[!] '{x}' is not a numeric Telegram ID (ask them to send /id to the bot)")
        save_settings(t)
        print(f"[ok] Allowlist: {', '.join(map(str, t['allow'])) or '(empty)'}")
        return 0
    if act in ("mode", "voice", "refusal"):
        val = v[0] if v else ""
        ok = {"mode": ("polling", "webhook"), "voice": ("on", "off"), "refusal": ("polite", "ignore")}[act]
        if val not in ok:
            print(f"usage: telegram {act} {'|'.join(ok)}")
            return 2
        if act == "voice":
            t["voice_replies"] = val == "on"
        else:
            t[act] = val
        save_settings(t)
        print(f"[ok] telegram {act}: {val}")
        return 0
    if act == "start":
        holder = PollerLock().holder()
        if running_pid() or holder:
            print(f"Already running (pid {running_pid() or holder}). Only one poller per bot.")
            return 0
        logf = open(os.path.join(os.path.dirname(pid_path()), "bot.log"), "a")
        p = subprocess.Popen([sys.executable, "-m", "nimlab", "telegram", "run"], stdout=logf,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True,
                             cwd=config.PROJECT_DIR, env=dict(os.environ, NIMLAB_COLOR="0"))
        print(f"[ok] Bot started in the background (pid {p.pid}). For auto-restart, run it with the "
              "service instead: nimlab service telegram on")
        return 0
    if act == "stop":
        pid = running_pid()
        if not pid:
            print("Not running here" + (" (it runs with the service: nimlab service telegram off)"
                                        if __import__("nimlab.service", fromlist=["x"]).settings().get("telegram")
                                        else "."))
            return 0
        os.kill(pid, signal.SIGTERM)
        print(f"[ok] Stopped (pid {pid}).")
        return 0
    print("usage: telegram set-token|test|allow|status|start|stop|run|mode|voice|refusal")
    return 2
