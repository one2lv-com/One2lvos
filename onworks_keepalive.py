#!/usr/bin/env python3
"""
Lumenis OnWorks Keepalive Daemon
Pings OnWorks session URLs on rotation to prevent live-boot timeout.
OnWorks strict timeout: ~3-5 min idle. We ping every 90s.
"""
import time, requests, datetime, sys, os

URLS = [
    "https://www.onworks.net/",
    "https://www.onworks.net/runos/create-os.html?os=ubuntu-22.04.3-desktop-amd64&home=init",
    "https://www.onworks.net/playonline/index.php?os=ubuntu-22.04.3-desktop-amd64",
    "https://www.onworks.net/os-app/ubuntu-22.04.3-desktop-amd64",
]

INTERVAL   = 90   # seconds between pings
TIMEOUT    = 10   # request timeout
LOG_FILE   = "/tmp/onworks_keepalive.log"
LUMENIS    = "http://localhost:8000"

def log(msg):
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def ping(url):
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (LumenisKeepAlive/1.0)"})
        return r.status_code, round(r.elapsed.total_seconds(), 2)
    except Exception as e:
        return 0, str(e)

def report_to_lumenis(ping_num, results):
    try:
        import json, urllib.request
        payload = json.dumps({
            "key": f"onworks_keepalive_ping_{ping_num}",
            "text": f"Ping #{ping_num} @ {datetime.datetime.now().isoformat()} | " +
                    " | ".join(f"{u.split('/')[-1][:20]}={s}" for u,s,_ in results)
        }).encode()
        req = urllib.request.Request(
            f"{LUMENIS}/api/tools/memory/store", data=payload, method="POST"
        )
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def main():
    log("=== Lumenis OnWorks Keepalive Daemon started ===")
    log(f"Interval: {INTERVAL}s | URLs: {len(URLS)} | Log: {LOG_FILE}")
    url_idx   = 0
    ping_num  = 0
    consecutive_fails = 0

    while True:
        url    = URLS[url_idx % len(URLS)]
        status, elapsed = ping(url)
        ping_num += 1

        if status in (200, 301, 302, 307, 308):
            log(f"PING #{ping_num} OK  [{status}] {url} ({elapsed}s)")
            consecutive_fails = 0
        else:
            consecutive_fails += 1
            log(f"PING #{ping_num} FAIL [{status}] {url} — fail #{consecutive_fails}")
            if consecutive_fails >= 5:
                log("WARNING: 5 consecutive failures — OnWorks may be down or session expired")
                consecutive_fails = 0

        # Report to Lumenis every 5 pings
        if ping_num % 5 == 0:
            report_to_lumenis(ping_num, [(url, status, elapsed)])

        url_idx += 1
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
