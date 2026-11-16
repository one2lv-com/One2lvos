#!/usr/bin/env python3
"""Shared restart lock between watchdog.py and autonomis-agent.py (service_lock.py). Offline, temp dir only."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="svclock_"))
os.environ["ONE2LV_LOCK_DIR"] = str(TMP)
sys.path.insert(0, str(ROOT))
import service_lock as sl  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def hold(service, holder, secs):
    code = ("import sys,time; sys.path.insert(0, %r); import service_lock as s\n"
            "with s.restart_lock(%r, holder=%r) as got:\n"
            "    print('got' if got else 'no', flush=True); time.sleep(%s)\n") % (str(ROOT), service, holder, secs)
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True, env=dict(os.environ))
    return p, p.stdout.readline().strip()


def main():
    # 1. basic: free lock is taken, and writes a stamp
    with sl.restart_lock("svc", holder="watchdog") as got:
        check("free lock is taken", got)
    st = sl.last_restart("svc")
    check("stamp written after restart", st.get("holder") == "watchdog", json.dumps(st))
    # 2. same holder may restart again at once; the other one waits out the grace window
    with sl.restart_lock("svc", holder="watchdog") as got:
        check("same supervisor is not blocked by its own stamp", got)
    with sl.restart_lock("svc", holder="autonomis") as got:
        check("other supervisor keeps away inside the grace window", not got)
    with sl.restart_lock("svc", holder="autonomis", grace_s=0) as got:
        check("other supervisor may restart once the grace window is over", got)
    # 3. concurrent: a lock held by another process refuses without blocking
    p, first = hold("svc2", "autonomis", 3)
    check("child process holds svc2", first == "got", first)
    t0 = time.monotonic()
    with sl.restart_lock("svc2", holder="watchdog") as got:
        check("held lock refuses at once (no wait)", not got and time.monotonic() - t0 < 0.5)
    p.wait(timeout=10)
    # 4. a crashed holder never leaves the lock stuck (stamp aside)
    p, first = hold("svc3", "autonomis", 30)
    p.kill(); p.wait()
    (TMP / "restart-svc3.last.json").unlink(missing_ok=True)
    with sl.restart_lock("svc3", holder="watchdog") as got:
        check("lock is free after the holder was killed", got)

    # 5. watchdog.locked_restart uses the lock
    spec = importlib.util.spec_from_file_location("watchdog_mod", ROOT / "watchdog.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    wd.LOG_FILE = TMP / "watchdog.log"
    calls = []
    wd.restart = lambda reason, count: calls.append((reason, count)) or True
    wd.stop_hung_reactor = lambda: calls.append("stop") or True
    (TMP / f"restart-{sl.REACTOR_SERVICE}.last.json").unlink(missing_ok=True)
    p, first = hold(sl.REACTOR_SERVICE, "autonomis", 3)
    r = wd.locked_restart("hung", 1, hung=True)
    check("watchdog skips the reactor restart while Autonomis holds the lock", r is None and not calls,
          f"r={r} calls={calls}")
    p.wait(timeout=10)
    (TMP / f"restart-{sl.REACTOR_SERVICE}.last.json").unlink(missing_ok=True)
    r = wd.locked_restart("hung", 2, hung=True)
    check("watchdog stops then restarts the hung reactor once the lock is free",
          r is True and calls == ["stop", ("hung", 2)], f"r={r} calls={calls}")
    check("watchdog's restart is stamped", sl.last_restart(sl.REACTOR_SERVICE).get("holder") == "watchdog")

    # 6. watchdog_running() follows logs/watchdog.lock
    check("watchdog_running() False with no lock holder", not sl.watchdog_running())
    p = subprocess.Popen([sys.executable, "-c", (
        "import fcntl,time; f=open(%r,'a+'); fcntl.flock(f, fcntl.LOCK_EX); print('x', flush=True); time.sleep(3)")
        % str(TMP / "watchdog.lock")], stdout=subprocess.PIPE, text=True)
    p.stdout.readline()
    check("watchdog_running() True while watchdog.lock is held", sl.watchdog_running())
    p.wait(timeout=10)

    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
