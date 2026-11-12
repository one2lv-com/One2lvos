"""Polite fetching of public NVIDIA catalog pages.

Used by `discover` and the spec sweep. Everything here is public and
unauthenticated: no API key is ever sent to, or stored from, these hosts.

- browser-like User-Agent (build.nvidia.com answers plain clients too, but
  the RSC payload is only complete for browser-like agents)
- one request at a time per host, with a minimum gap per host
  (build.nvidia.com asks for Crawl-delay: 10 in robots.txt)
- an on-disk cache with a TTL, so repeated runs do not refetch pages
"""

import hashlib
import json
import os
import threading
import time
import urllib.parse

from . import config
from .core import HttpClient

BROWSER_UA = ("Mozilla/5.0 (Linux; Android 14; Termux) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36")

# Minimum seconds between two requests to the same host.
DEFAULT_HOST_DELAYS = {
    "build.nvidia.com": 10.0,      # robots.txt Crawl-delay: 10
    "docs.api.nvidia.com": 3.0,
    "api.ngc.nvidia.com": 1.0,
}
DEFAULT_DELAY = 2.0
DEFAULT_TTL_SEC = 3 * 24 * 3600


def default_cache_dir():
    return config.output_path(os.path.join("cache", "pages"))


class FetchResult:
    __slots__ = ("url", "status", "text", "from_cache", "error", "fetched_at")

    def __init__(self, url, status=None, text="", from_cache=False, error=None, fetched_at=None):
        self.url = url
        self.status = status
        self.text = text or ""
        self.from_cache = from_cache
        self.error = error
        self.fetched_at = fetched_at

    @property
    def ok(self):
        return self.status is not None and 200 <= self.status < 300 and not self.error

    def json(self):
        try:
            return json.loads(self.text)
        except ValueError:
            return None


class PoliteFetcher:
    """GET public pages with per-host pacing and a TTL cache.

    cache_dir: None for the default (output/cache/pages), "" for no cache.

    http: a nimlab HttpClient (injectable for tests).
    sleep / clock: injectable so tests do not wait.
    """

    def __init__(self, http=None, cache_dir=None, ttl_sec=DEFAULT_TTL_SEC, host_delays=None,
                 user_agent=BROWSER_UA, sleep=time.sleep, clock=time.monotonic, offline=False,
                 log=None):
        self.http = http or HttpClient(timeout=30, retries=2, backoff=2.0, max_bytes=8 * 1024 * 1024)
        self.cache_dir = cache_dir if cache_dir is not None else default_cache_dir()
        self.ttl = ttl_sec
        self.delays = dict(DEFAULT_HOST_DELAYS)
        self.delays.update(host_delays or {})
        self.ua = user_agent
        self._sleep = sleep
        self._clock = clock
        self.offline = offline
        self.log = log or (lambda msg: None)
        self._host_locks = {}
        self._last = {}
        self._guard = threading.Lock()
        self.network_requests = 0

    # -- cache --------------------------------------------------------------
    def _cache_path(self, url):
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        return os.path.join(self.cache_dir, h + ".json")

    def _read_cache(self, url, allow_stale=False):
        if not self.cache_dir:
            return None
        path = self._cache_path(url)
        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)
        except (OSError, ValueError):
            return None
        if entry.get("url") != url:
            return None
        age = time.time() - float(entry.get("fetched_at", 0))
        if age > self.ttl and not allow_stale:
            return None
        return FetchResult(url, entry.get("status"), entry.get("text", ""), True, None, entry.get("fetched_at"))

    def _write_cache(self, res):
        if not self.cache_dir or not res.ok:
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        tmp = self._cache_path(res.url) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"url": res.url, "status": res.status, "fetched_at": res.fetched_at,
                       "text": res.text}, f)
        os.replace(tmp, self._cache_path(res.url))

    # -- pacing -------------------------------------------------------------
    def _host_lock(self, host):
        with self._guard:
            if host not in self._host_locks:
                self._host_locks[host] = threading.Lock()
            return self._host_locks[host]

    def _delay_for(self, host):
        return float(self.delays.get(host, DEFAULT_DELAY))

    # -- public -------------------------------------------------------------
    def get(self, url, use_cache=True, accept="text/html,application/json;q=0.9,*/*;q=0.8", store=True):
        """store=False: do not write the body to the page cache (model pages
        are large; the sweep caches the extracted spec instead)."""
        if use_cache and store:
            cached = self._read_cache(url)
            if cached is not None:
                return cached
        if self.offline:
            stale = self._read_cache(url, allow_stale=True)
            return stale or FetchResult(url, None, "", False, "offline and not cached")
        host = urllib.parse.urlsplit(url).hostname or ""
        with self._host_lock(host):
            wait = self._delay_for(host) - (self._clock() - self._last.get(host, -1e9))
            if wait > 0:
                self._sleep(wait)
            res = self.http.request("GET", url, None, {"User-Agent": self.ua, "Accept": accept,
                                                     "Accept-Language": "en-US,en;q=0.8"})
            self._last[host] = self._clock()
            self.network_requests += 1
        out = FetchResult(url, res.status, res.text if res.status is not None else "",
                          False, None if res.ok else res.describe(), time.time())
        if out.ok and store:
            self._write_cache(out)
        else:
            self.log(f"fetch failed {url}: {out.error}")
            stale = self._read_cache(url, allow_stale=True) if store else None
            if stale is not None:  # keep working from the last good copy
                return stale
        return out
