#!/usr/bin/env python3
"""One2lvOS WebDAV file server.

Serves ONE folder (default webdav_root/ next to this script) over WebDAV on 127.0.0.1:8090.
It is the server the desktop Network Manager connects to (built-in "One2lvOS Files"
connection), and any WebDAV client on this machine can use it too.

Security
  * Bound to 127.0.0.1 only. It is NOT published on the Cloudflare tunnel.
  * Every request needs HTTP Basic auth with the One2lvOS AI Lobby admin login
    (ai-lobby/data/config.json). The login is read fresh on each check and compared in
    constant time; nothing is copied to another file.
  * 5 wrong logins from one address lock it out for 10 minutes.
  * Only the share folder is reachable: no shell, no other paths, symlinks out of the
    share are not followed.

Usage:  .venv/bin/python3 webdav_server.py      (env: WEBDAV_PORT, WEBDAV_ROOT, WEBDAV_HOST)
"""
import hmac
import json
import os
import sys
import threading
import time
from collections import defaultdict, deque

from cheroot import wsgi
from wsgidav.dc.base_dc import BaseDomainController
from wsgidav.wsgidav_app import WsgiDAVApp

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "ai-lobby", "data", "config.json")
SHARE = os.path.realpath(os.environ.get("WEBDAV_ROOT", os.path.join(ROOT, "webdav_root")))
HOST = os.environ.get("WEBDAV_HOST", "127.0.0.1")
PORT = int(os.environ.get("WEBDAV_PORT", "8090"))
MAX_FAILS, LOCK_SECS = 5, 600

_fails = defaultdict(deque)
_lock = threading.Lock()


def _admin():
    with open(CONFIG) as f:
        a = json.load(f)["admin"]
    return str(a["username"]), str(a["password"])


class LobbyAdminDC(BaseDomainController):
    """Basic-auth only; accepts the AI Lobby admin login."""

    def __init__(self, wsgidav_app, config):
        super().__init__(wsgidav_app, config)

    def __str__(self):
        return "LobbyAdminDC"

    def get_domain_realm(self, path_info, environ):
        return "One2lvOS Files"

    def require_authentication(self, realm, environ):
        return True

    def supports_http_digest_auth(self):
        return False

    def basic_auth_user(self, realm, user_name, password, environ):
        ip = environ.get("REMOTE_ADDR", "?")  # localhost-only server: no proxy headers trusted
        now = time.time()
        with _lock:
            q = _fails[ip]
            while q and q[0] < now - LOCK_SECS:
                q.popleft()
            if len(q) >= MAX_FAILS:
                return False
        try:
            u, p = _admin()
        except Exception:
            return False
        ok = hmac.compare_digest(str(user_name or "").encode(), u.encode()) & \
            hmac.compare_digest(str(password or "").encode(), p.encode())
        if not ok:
            with _lock:
                _fails[ip].append(now)
        return bool(ok)


def main():
    os.makedirs(SHARE, exist_ok=True)
    welcome = os.path.join(SHARE, "WELCOME.txt")
    if not os.listdir(SHARE):
        with open(welcome, "w") as f:
            f.write("ONE2LVOS WEBDAV SERVER\n======================\nSovereign distributed filesystem. Welcome.\n")
    config = {
        "host": HOST,
        "port": PORT,
        "provider_mapping": {"/": {"root": SHARE, "readonly": False, "follow_symlinks": False}},
        "http_authenticator": {
            "domain_controller": LobbyAdminDC,
            "accept_basic": True,
            "accept_digest": False,
            "default_to_digest": False,
            "trusted_auth_header": None,
        },
        "simple_dc": {"user_mapping": {}},
        "verbose": 2,
        "logging": {"enable_loggers": []},
        "property_manager": True,
        "lock_storage": True,
        "dir_browser": {"enable": True, "show_user": False, "davmount": False, "ms_sharepoint_support": False},
        "hotfixes": {"emulate_win32_lastmod": True},
    }
    app = WsgiDAVApp(config)
    server = wsgi.Server((HOST, PORT), app, numthreads=8)
    print(f"[WebDAV] serving {SHARE} on http://{HOST}:{PORT}/ (Basic auth: AI Lobby admin)", flush=True)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    sys.exit(main())
