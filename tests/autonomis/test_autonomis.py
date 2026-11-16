#!/usr/bin/env python3
"""Focused tests for the Autonomis reliability changes.

Everything runs in a throwaway repo under /tmp on ports 18000-18200, so the
real One2lvOS services on this machine (8000, 8095, ...) are never touched:
the test replaces service_registry() and BRIDGE_PORT before any cycle runs.
"""
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent.parent / "autonomis-agent.py"
REPO = Path("/tmp/autonomis_test_repo")
PY = sys.executable

RESULTS = []


def check(name, cond, info=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  [{info}]" if info else ""), flush=True)


# ── fake repo ──────────────────────────────────────────────────────────────────────
def build_repo():
    if REPO.exists():
        shutil.rmtree(REPO)
    (REPO / "logs").mkdir(parents=True)
    (REPO / "aria").mkdir()
    shutil.copy(AGENT, REPO / "autonomis-agent.py")
    # Shared modules the merged agent imports (restart lock, L0-L3 command tiers).
    shutil.copy(AGENT.parent / "service_lock.py", REPO / "service_lock.py")
    (REPO / "lumenis_reactor_core").mkdir()
    shutil.copy(AGENT.parent / "lumenis_reactor_core" / "command_tiers.py",
                REPO / "lumenis_reactor_core" / "command_tiers.py")
    for name in ("svc_a.py", "public_bridge.py"):
        shutil.copy(HERE / "fake_svc.py", REPO / name)
    shutil.copy(HERE / "fake_cf.py", REPO / "fake_cf.py")
    (REPO / "crash.py").write_text("import sys; print('crashing'); sys.exit(1)\n")
    (REPO / "aria" / "main.py").write_text("import time\nwhile True: time.sleep(60)\n")
    # No start-aria.sh: the agent starts aria/main.py itself now (the real repo never had that script).
    (REPO / "bridge_tunnel.sh").write_text(
        "#!/bin/bash\ncd \"$(dirname \"$0\")\"\n"
        "echo started >> logs/tunnel_starts.txt\n"
        f"READY_FILE=$PWD/ready.txt nohup bash -c 'exec -a cloudflared {PY} \"$0\" tunnel "
        "--url http://localhost:18095 --metrics 127.0.0.1:18200' \"$PWD/fake_cf.py\" "
        "> logs/bridge_tunnel.log 2>&1 &\n"
        "echo $! > logs/bridge_tunnel.pid\n"
        "echo http://127.0.0.1:18095 > logs/bridge_tunnel.url\n"
        "sleep 1\n")
    (REPO / "mode_a.txt").write_text("ok")
    (REPO / "mode_bridge.txt").write_text("ok")
    (REPO / "ready.txt").write_text("200")
    config = {
        "agent_name": "Autonomis", "version": "test",
        "monitoring": {"enabled": True, "check_interval_seconds": 1,
                       "max_restart_attempts": 3,
                       "ai_consultation_cooldown_seconds": 300,
                       "failure_threshold_before_ai": 3},
        "services": {"auto_restart": True, "health_check_timeout": 1,
                     "restart_backoff_seconds": 0.5, "max_backoff_seconds": 2,
                     "give_up_seconds": 4, "startup_grace_seconds": 1.5,
                     "stable_after_seconds": 2, "failed_checks_before_restart": 2,
                     "stop_timeout_seconds": 3},
        "tunnel": {"public_check": True, "public_check_timeout": 2,
                   "failed_checks_before_restart": 2},
        "installation": {"auto_install_dependencies": False},
        "mcp_integration": {"tools_directory": "tools"},
        "ai_consultation": {"enabled": False},
        "notifications": {"discord_enabled": False},
        "aria": {"monitor": True},
    }
    (REPO / "autonomis-config.json").write_text(json.dumps(config))


def load_module():
    spec = importlib.util.spec_from_file_location("autonomis_agent", REPO / "autonomis-agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.BRIDGE_PORT = 18095
    return mod


def svc(name, script, port, path, mode=None, health=None):
    cmd = [PY, str(REPO / script)]
    if port:
        cmd += [str(port), str(REPO / (mode or "mode_a.txt"))]
    return {"name": name, "port": port, "path": path, "cmd": cmd, "cwd": REPO,
            "log": f"{name}.log", "host": "127.0.0.1",
            "match": {"script": REPO / script},
            "health": health or {"expect_status": "lt500"}}


SVC_A = lambda: svc("svc-a", "svc_a.py", 18000, "/api/status",
                    health={"expect_status": "2xx", "json": {"reactor": None}})
BRIDGE = lambda: svc("public-bridge", "public_bridge.py", 18095, "/v1/health",
                     mode="mode_bridge.txt",
                     health={"expect_status": "2xx", "json": {"bridge": "ok"}})
CRASHY = lambda: svc("crashy", "crash.py", 18010, "/")


def start_external(script, port, mode):
    """Start a copy the way startos.sh would - not a child the agent knows."""
    return subprocess.Popen([PY, str(REPO / script), str(port), str(REPO / mode)],
                            cwd=str(REPO), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)


def start_fake_cf(url_port, metrics=None, extra=None):
    args = f"tunnel --url http://localhost:{url_port}"
    if metrics:
        args += f" --metrics {metrics}"
    if extra:
        args = extra
    return subprocess.Popen(
        ["bash", "-c", f"exec -a cloudflared {PY} {REPO / 'fake_cf.py'} {args}"],
        env=dict(os.environ, READY_FILE=str(REPO / "ready.txt")),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def wait_port(mod, port, up=True, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        if mod.port_open("127.0.0.1", port, 0.5) == up:
            return True
        time.sleep(0.1)
    return False


def kill_all():
    """Kill test processes only: an argument that is a path inside the test
    repo, or a working directory inside it. (A shell whose -c string merely
    mentions the path is not matched.)"""
    me = os.getpid()
    root = str(REPO)
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        try:
            args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            args = [a.decode(errors="replace") for a in args if a]
            cwd = os.readlink(f"/proc/{pid}/cwd")
        except OSError:
            continue
        if cwd.endswith(" (deleted)"):  # repo removed by an earlier run
            cwd = cwd[: -len(" (deleted)")]
        ours = any(a == root or a.startswith(root + "/") for a in args) or \
            cwd == root or cwd.startswith(root + "/")
        if ours and pid != me:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    time.sleep(0.5)


# ── tests ────────────────────────────────────────────────────────────────────────────
def test_evaluate(mod):
    ev = mod.evaluate_response
    check("eval: 200 JSON with key passes 2xx+json", ev(200, b'{"reactor":{}}', {"expect_status": "2xx", "json": {"reactor": None}})[0])
    check("eval: 500 fails lt500", not ev(500, b"", {"expect_status": "lt500"})[0])
    check("eval: 404 passes lt500 (listening, speaks HTTP)", ev(404, b"", {"expect_status": "lt500"})[0])
    check("eval: 404 fails 2xx", not ev(404, b"", {"expect_status": "2xx"})[0])
    check("eval: non-JSON body fails json spec", not ev(200, b"hello", {"expect_status": "2xx", "json": {"a": None}})[0])
    check("eval: wrong value fails", not ev(200, b'{"bridge":"down"}', {"expect_status": "2xx", "json": {"bridge": "ok"}})[0])
    check("eval: missing key fails", not ev(200, b'{"x":1}', {"expect_status": "2xx", "json": {"bridge": "ok"}})[0])


def test_check_service(mod):
    s = SVC_A()
    check("check: nothing listening -> down", mod.check_service(s, 1)["state"] == "down")
    p = start_external("svc_a.py", 18000, "mode_a.txt")
    wait_port(mod, 18000)
    for mode, want in (("ok", "ok"), ("500", "bad"), ("text", "bad"), ("404", "bad"), ("hang", "bad")):
        (REPO / "mode_a.txt").write_text(mode)
        r = mod.check_service(s, 1)
        check(f"check: svc-a mode {mode} -> {want}", r["state"] == want, r["detail"])
    lt = dict(s, health={"expect_status": "lt500"})
    (REPO / "mode_a.txt").write_text("404")
    check("check: 404 on a lt500 service -> ok", mod.check_service(lt, 1)["state"] == "ok")
    (REPO / "mode_a.txt").write_text("500")
    check("check: old http_ok() no longer calls a 500 healthy", mod.http_ok(18000, "/", 1) is False)
    (REPO / "mode_a.txt").write_text("ok")
    p.kill(); p.wait()


def test_policy(mod):
    cfg = json.loads((REPO / "autonomis-config.json").read_text())
    pol = mod.RestartPolicy(cfg)
    t = 1000.0
    ok, why, _ = pol.allow("x", "bad", now=t)
    check("policy: first 'bad' check does not restart", not ok, why)
    ok, why, _ = pol.allow("x", "bad", now=t + 1)
    check("policy: second 'bad' check restarts", ok, why)
    ok, why, _ = pol.allow("y", "down", now=t)
    check("policy: 'down' restarts on the first check", ok, why)
    # backoff: record with a live pid -> grace applies first
    pol.record_restart("y", os.getpid(), True, now=t)
    ok, why, _ = pol.allow("y", "down", now=t + 1)
    check("policy: grace while the started pid is alive", not ok and why.startswith("starting"), why)
    # backoff grows: 0.5, 1, 2 (cap 2)
    pol2 = mod.RestartPolicy(cfg)
    pol2.record_restart("z", None, False, now=t)
    d1 = pol2.state["z"]["next_at"] - t
    pol2.record_restart("z", None, False, now=t)
    d2 = pol2.state["z"]["next_at"] - t
    check("policy: backoff doubles", (d1, d2) == (0.5, 1.0), f"{d1}, {d2}")
    ok, why, _ = pol2.allow("z", "down", now=t + 0.5)
    check("policy: blocked inside backoff", not ok and why.startswith("backoff"), why)
    pol2.record_restart("z", None, False, now=t + 2)
    # 3rd attempt at t+2 -> paused until t+2+give_up(4) = t+6
    ok, why, gave = pol2.allow("z", "down", now=t + 4)
    check("policy: limit reached after max attempts", not ok and "limit" in why and gave, why)
    ok, why, gave = pol2.allow("z", "down", now=t + 5)
    check("policy: give-up is reported only once", not ok and not gave, why)
    ok, why, _ = pol2.allow("z", "down", now=t + 2 + 4 + 0.1)
    check("policy: new round after the cool-off", ok and pol2.attempts("z") == 0, why)
    pol2.record_restart("z", None, True, now=t + 20)
    pol2.healthy("z", now=t + 30)
    check("policy: healthy but not yet stable keeps the count", pol2.attempts("z") == 1)
    pol2.healthy("z", now=t + 32.5)
    check("policy: stable for stable_after resets the count", pol2.attempts("z") == 0)


def test_no_duplicates(mod):
    (REPO / "mode_a.txt").write_text("500")
    old = start_external("svc_a.py", 18000, "mode_a.txt")
    stray = start_external("svc_a.py", 18100, "mode_a.txt")   # same command, other port
    bridge = start_external("public_bridge.py", 18095, "mode_bridge.txt")
    wait_port(mod, 18000); wait_port(mod, 18100); wait_port(mod, 18095)
    mod.service_registry = lambda: [SVC_A(), BRIDGE()]
    agent = mod.Autonomis()
    r1 = agent.cycle()
    check("dup: 1st bad check -> no restart of svc-a",
          not any(x["service"] == "svc-a" for x in r1["restarts"]), json.dumps(r1["skipped"]))
    r2 = agent.cycle()
    restarted = [x for x in r2["restarts"] if x["service"] == "svc-a"]
    check("dup: 2nd bad check -> svc-a restarted once", len(restarted) == 1, json.dumps(r2["restarts"]))
    old.wait(timeout=5); stray.wait(timeout=5)
    check("dup: old copy on the port was stopped", old.returncode is not None, f"rc={old.returncode}")
    check("dup: stray copy running the same command was stopped", stray.returncode is not None, f"rc={stray.returncode}")
    wait_port(mod, 18000)
    new_pid = restarted[0]["pid"] if restarted else None
    holders = mod.pids_listening_on(18000)
    copies = [p for p in mod._iter_pids() if mod.process_matches(p, SVC_A()) and mod.pid_alive(p)]
    check("dup: exactly one process on :18000, the new one", holders == {new_pid}, f"{holders} vs {new_pid}")
    check("dup: exactly one copy of svc_a.py running", copies == [new_pid], str(copies))
    check("dup: public-bridge (healthy) untouched", bridge.poll() is None)
    r3 = agent.cycle()
    check("dup: next cycle inside grace does not spawn again",
          not any(x["service"] == "svc-a" for x in r3["restarts"]),
          json.dumps([s for s in r3["skipped"] if s["service"] == "svc-a"]))
    (REPO / "mode_a.txt").write_text("ok")
    r4 = agent.cycle()
    check("dup: svc-a healthy after fix", "svc-a" not in r4["unhealthy"])
    state = json.loads((REPO / "logs" / "autonomis_state.json").read_text())
    check("dup: state file written with restart info", state.get("svc-a", {}).get("attempts") == 1, json.dumps(state.get("svc-a")))
    # aria and the tunnel were down in this repo: restarted by the same cycle
    check("aria: restarted without start-aria.sh and detected by cwd", mod.aria_running())
    starts = (REPO / "logs" / "tunnel_starts.txt").read_text().count("started")
    check("tunnel: started once (no duplicate starts over 4 cycles)", starts == 1, f"starts={starts}")
    return agent


def test_crash_loop(mod):
    mod.service_registry = lambda: [CRASHY(), BRIDGE()]
    agent = mod.Autonomis()
    spawns, skipped_limit, t0 = [], 0, time.time()
    pids = []
    while time.time() - t0 < 13:
        r = agent.cycle()
        for x in r["restarts"]:
            if x["service"] == "crashy":
                spawns.append(round(time.time() - t0, 1)); pids.append(x["pid"])
        skipped_limit += sum(1 for s in r["skipped"]
                             if s["service"] == "crashy" and "limit" in s["reason"])
        time.sleep(0.6)
    check("crash: first round is capped at 3 restarts", len(spawns) >= 3 and (len(spawns) == 3 or spawns[3] - spawns[2] >= 3.5), str(spawns))
    gaps = [round(b - a, 1) for a, b in zip(spawns, spawns[1:3])]
    check("crash: gaps grow inside the round (backoff)", len(gaps) == 2 and gaps[1] >= gaps[0], str(gaps))
    check("crash: restarts skipped with 'limit reached' while paused", skipped_limit >= 3, f"skips={skipped_limit}")
    check("crash: a new round starts after the cool-off", len(spawns) >= 4, str(spawns))
    log = (REPO / "logs" / "autonomis.log").read_text()
    # A slow machine can fit two full rounds into the 13 s window; the rule is one give-up line per full round.
    rounds = len(spawns) // 3
    check("crash: give-up logged once per round", log.count("crashy: still down after 3 restarts") == rounds,
          f"lines={log.count('crashy: still down after 3 restarts')} rounds={rounds} spawns={len(spawns)}")
    mod.reap_children()
    zombies = [p for p in pids if p and mod._proc_stat_fields(p)[:1] == ["Z"]]
    check("crash: crashed children are reaped (no zombies)", not zombies, str(zombies))
    check("crash: pid_alive() is False for the dead child", not any(mod.pid_alive(p) for p in pids if p))


def test_tunnel(mod):
    kill_all()
    logs = REPO / "logs"
    bridge = start_external("public_bridge.py", 18095, "mode_bridge.txt")
    wait_port(mod, 18095)
    for f in ("bridge_tunnel.pid", "bridge_tunnel.url"):
        (logs / f).unlink(missing_ok=True)

    th = mod.tunnel_health(check_public=False)
    check("tunnel: no pid file, no process -> down", th["state"] == "down", th["detail"])

    sleeper = subprocess.Popen(["sleep", "300"])
    (logs / "bridge_tunnel.pid").write_text(str(sleeper.pid))
    th = mod.tunnel_health(check_public=False)
    check("tunnel: pid file -> live non-cloudflared pid (reused pid) -> down",
          th["state"] == "down" and "stale" in th["detail"], th["detail"])
    check("tunnel: old tunnel_running() was fooled by this; new one is not",
          mod.tunnel_running() is False)

    sleeper.kill(); sleeper.wait()
    th = mod.tunnel_health(check_public=False)
    check("tunnel: pid file -> dead pid -> down", th["state"] == "down", th["detail"])

    zombie = subprocess.Popen(["true"]); time.sleep(0.3)   # exited, not reaped
    (logs / "bridge_tunnel.pid").write_text(str(zombie.pid))
    th = mod.tunnel_health(check_public=False)
    check("tunnel: pid file -> zombie -> down", th["state"] == "down", th["detail"])
    zombie.wait()

    unrelated = start_fake_cf(None, extra="tunnel run main-named-tunnel")
    other = start_fake_cf(9999)
    time.sleep(0.5)
    th = mod.tunnel_health(check_public=False)
    check("tunnel: cloudflared for other tunnels is not mistaken for the bridge",
          th["state"] == "down", th["detail"])

    cf = start_fake_cf(18095, metrics="127.0.0.1:18200")
    wait_port(mod, 18200)
    th = mod.tunnel_health(check_public=False)
    check("tunnel: stale pid file but cloudflared publishing :18095 found -> ok",
          th["state"] == "ok" and th["pid"] == cf.pid, th["detail"])

    (REPO / "ready.txt").write_text("503")
    th = mod.tunnel_health(check_public=False)
    check("tunnel: metrics /ready 503 -> bad", th["state"] == "bad", th["detail"])
    (REPO / "ready.txt").write_text("200")

    (logs / "bridge_tunnel.url").write_text("http://127.0.0.1:18095")
    th = mod.tunnel_health(check_public=True, timeout=2)
    check("tunnel: published URL answers /v1/health -> ok", th["state"] == "ok", th["detail"])
    (logs / "bridge_tunnel.url").write_text("http://127.0.0.1:18199")
    th = mod.tunnel_health(check_public=True, timeout=2)
    check("tunnel: published URL dead -> bad", th["state"] == "bad", th["detail"])
    th = mod.tunnel_health(check_public=True, timeout=2, bridge_ok=False)
    check("tunnel: URL not blamed when the local bridge is down", th["state"] == "ok", th["detail"])
    (logs / "bridge_tunnel.url").write_text("http://127.0.0.1:18095")

    # A cycle adopts the found process into the pid file and stops a duplicate.
    dup = start_fake_cf(18095)
    time.sleep(0.5)
    mod.service_registry = lambda: [BRIDGE()]
    agent = mod.Autonomis()
    r = agent.cycle()
    dup.wait(timeout=5)
    check("tunnel: cycle rewrote the stale pid file",
          (logs / "bridge_tunnel.pid").read_text().strip() == str(cf.pid))
    check("tunnel: duplicate bridge cloudflared stopped", dup.returncode is not None)
    check("tunnel: the kept cloudflared still runs", cf.poll() is None)
    check("tunnel: no restart when healthy", not any(x["service"] == "bridge-tunnel" for x in r["restarts"]))

    # Kill it: the next cycle stops leftovers and runs bridge_tunnel.sh once.
    (logs / "tunnel_starts.txt").unlink(missing_ok=True)
    cf.kill(); cf.wait()
    r = agent.cycle()
    starts = (logs / "tunnel_starts.txt").read_text().count("started") if (logs / "tunnel_starts.txt").exists() else 0
    check("tunnel: dead cloudflared -> bridge_tunnel.sh run once", starts == 1, f"starts={starts}")
    th = mod.tunnel_health(check_public=False)
    new_pid = int((logs / "bridge_tunnel.pid").read_text())
    check("tunnel: new cloudflared live and matches pid file", th["state"] == "ok" and th["pid"] == new_pid, th["detail"])

    # Tunnel process alive but published URL failing: restart only after 2 checks,
    # and the old process is stopped before the new one starts.
    (logs / "tunnel_starts.txt").unlink(missing_ok=True)
    agent.policy.state.pop("bridge-tunnel", None)
    (REPO / "ready.txt").write_text("503")
    r1 = agent.cycle()
    first = (logs / "tunnel_starts.txt").exists()
    check("tunnel: 1st 'bad' check (no edge connection) -> no restart yet", not first)
    # the restarted tunnel will be ready again
    old_pid = new_pid
    (REPO / "ready.txt").write_text("503")
    r2 = agent.cycle()
    (REPO / "ready.txt").write_text("200")
    starts = (logs / "tunnel_starts.txt").read_text().count("started") if (logs / "tunnel_starts.txt").exists() else 0
    check("tunnel: 2nd 'bad' check -> restarted once", starts == 1, f"starts={starts}")
    check("tunnel: old cloudflared stopped before restart", not mod.pid_alive(old_pid))
    live = mod.bridge_tunnel_pids()
    check("tunnel: exactly one bridge cloudflared afterwards", len(live) == 1, str(live))
    check("tunnel: unrelated cloudflared processes never stopped",
          unrelated.poll() is None and other.poll() is None)
    unrelated.kill(); other.kill(); bridge.kill()


def test_lock(mod):
    code = ("import importlib.util,time;"
            f"s=importlib.util.spec_from_file_location('a','{REPO / 'autonomis-agent.py'}');"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
            "fh=m.acquire_single_instance_lock();print('got' if fh else 'none',flush=True);time.sleep(3)")
    holder = subprocess.Popen([PY, "-c", code], stdout=subprocess.PIPE, text=True)
    first = holder.stdout.readline().strip()
    second = mod.acquire_single_instance_lock()
    check("lock: first agent gets the lock", first == "got", first)
    check("lock: second agent is refused while the first runs", second is None)
    holder.wait()
    third = mod.acquire_single_instance_lock()
    check("lock: free again once the first exits (no stale lock)", third is not None)
    if third:
        third.close()


def test_merge_rules(mod):
    """The 2026-11-16 merge: shared restart lock, watchdog owns the reactor, installs once, L0-L3 commands."""
    # 1. Restart lock: while another supervisor holds it, Autonomis skips the restart.
    mod.service_registry = lambda: [SVC_A(), BRIDGE()]
    (REPO / "mode_a.txt").write_text("ok")
    kill_all()
    for f in (REPO / "logs").glob("restart-*.last.json"):  # earlier tests' restart stamps
        f.unlink()
    agent = mod.Autonomis()
    agent.policy.healthy = lambda *a, **k: None
    holder = subprocess.Popen([PY, "-c", (
        "import sys,time; sys.path.insert(0, %r); import service_lock as s\n"
        "with s.restart_lock('svc-a', holder='watchdog') as got:\n"
        "    print('got' if got else 'no', flush=True); time.sleep(6)\n") % str(REPO)],
        stdout=subprocess.PIPE, text=True, env={**os.environ, "ONE2LV_LOCK_DIR": str(REPO / "logs")})
    first = holder.stdout.readline().strip()
    check("lock: test holder took the svc-a restart lock", first == "got", first)
    r = agent.cycle()
    check("lock: svc-a down but lock held elsewhere -> no restart",
          not any(x["service"] == "svc-a" for x in r["restarts"]), json.dumps(r["restarts"]))
    check("lock: skip reason recorded", any(s.get("reason", "").startswith("another supervisor")
                                            for s in r["skipped"]), json.dumps(r["skipped"]))
    holder.wait(timeout=10)
    # The holder wrote a restart stamp: inside the grace window Autonomis still keeps away.
    stamp = json.loads((REPO / "logs" / "restart-svc-a.last.json").read_text())
    check("lock: restart stamp written by the holder", stamp.get("holder") == "watchdog", json.dumps(stamp))
    r = agent.cycle()
    check("lock: inside the other supervisor's grace window -> still no restart",
          not any(x["service"] == "svc-a" for x in r["restarts"]), json.dumps(r["restarts"]))
    (REPO / "logs" / "restart-svc-a.last.json").unlink()
    agent.policy.allow = lambda *a, **k: (True, "", False)
    r = agent.cycle()
    check("lock: once free, Autonomis restarts svc-a", any(x["service"] == "svc-a" for x in r["restarts"]),
          json.dumps(r["restarts"]))
    kill_all()

    # 2. Watchdog owns the reactor: with logs/watchdog.lock held, the reactor is never checked or restarted.
    reactor = {"name": "lumenis-reactor", "port": 18003, "path": "/api/status", "log": "reactor_test.log",
               "cmd": [PY, "-c", "import time; time.sleep(30)"], "cwd": REPO, "match": {"args": ["never-match"]}}
    mod.service_registry = lambda: [reactor, BRIDGE()]
    wd = subprocess.Popen([PY, "-c", (
        "import fcntl,time; f=open(%r,'a+'); fcntl.flock(f, fcntl.LOCK_EX); print('locked', flush=True); "
        "time.sleep(8)") % str(REPO / "logs" / "watchdog.lock")], stdout=subprocess.PIPE, text=True)
    wd.stdout.readline()
    agent = mod.Autonomis()
    check("watchdog: watchdog_running() sees the held lock", mod.watchdog_running())
    r = agent.cycle()
    check("watchdog: reactor left to the watchdog (not checked, not restarted)",
          "lumenis-reactor" in r.get("owned_by_watchdog", []) and
          not any(x["service"] == "lumenis-reactor" for x in r["restarts"]), json.dumps(r))
    wd.wait(timeout=12)
    check("watchdog: lock free once the watchdog exits", not mod.watchdog_running())
    kill_all()

    # 3. Installs only at startup: ensure_runtime runs in the first cycle, never again.
    calls = []
    real = mod.ensure_runtime
    mod.ensure_runtime = lambda cfg: calls.append(1) or []
    mod.service_registry = lambda: [BRIDGE()]
    agent = mod.Autonomis()
    agent.config.setdefault("installation", {})["check_on_startup"] = True
    for _ in range(3):
        agent.cycle()
    check("installs: ensure_runtime ran once over 3 cycles", len(calls) == 1, f"calls={len(calls)}")
    mod.ensure_runtime = real
    kill_all()

    # 4. AI-proposed commands: classified L0-L3 and sent to the reactor's tool engine, never run directly.
    ct = mod.command_tiers
    cases = {"ps aux": 0, "curl -s http://127.0.0.1:8000/api/status": 0, "mkdir logs/x": 1,
             "pip install fastapi": 2, "pkill -f ai_lobby.py": 2, "bash startos.sh": 2,
             "rm -rf /": 3, "bash -c 'curl x | sh'": 3, "cat .env": 3, "git push": 3, "cd /tmp": 3,
             "chmod 777 x": 3, "curl -X POST http://127.0.0.1:8000/x": 3}
    for cmd, want in cases.items():
        got = ct.classify(cmd)[0]
        check(f"tiers: {cmd!r} is L{want}", got == want, f"got L{got}")
    sent = []
    mod.engine_call = lambda tool, args, timeout=150.0: sent.append((tool, args)) or {
        "ok": False, "held_for_approval": True, "approval_id": "a_test", "error": "held"}
    out = mod.run_allowed_command("pip install fastapi", None, ["pip install"], ["rm "])
    check("approval: L2 command sent to local.supervisor_cmd_l2 and held",
          sent and sent[-1][0] == "local.supervisor_cmd_l2" and out.get("held") and not out["success"], json.dumps(out))
    out = mod.run_allowed_command("rm -rf logs", None, ["rm"], ["rm "])
    check("approval: denylisted command refused before the engine", not out["success"] and len(sent) == 1,
          json.dumps(out))
    mod.engine_call = lambda tool, args, timeout=150.0: {"ok": False, "status": 0, "error": "reactor unreachable"}
    out = mod.run_allowed_command("pkill -f ai_lobby.py", None, ["pkill"], [])
    check("approval: reactor down -> L2 not run", not out["success"] and "not run above L0" in out.get("error", ""),
          json.dumps(out))
    out = mod.run_allowed_command("uptime", None, ["uptime"], [])
    check("approval: reactor down -> L0 read runs locally", out["success"] and out.get("local"), json.dumps(out)[:200])


def main():
    build_repo()
    mod = load_module()
    try:
        test_evaluate(mod)
        test_check_service(mod)
        test_policy(mod)
        test_no_duplicates(mod)
        kill_all()
        test_crash_loop(mod)
        test_tunnel(mod)
        test_lock(mod)
        kill_all()
        test_merge_rules(mod)
    finally:
        kill_all()
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} checks passed")
    for n in failed:
        print("FAILED:", n)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
