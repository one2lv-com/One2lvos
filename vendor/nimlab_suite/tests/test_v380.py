"""v3.8.0: the scheduler (jobs like Oracle DBMS_SCHEDULER), the heartbeat,
suggested actions, result routing, Quill managing jobs, and the service's
scheduler child. Everything runs in a temp lab against fakes: no model, no
Telegram, no MCP server, no subprocess."""

import io
import json
import os
import re
import shutil
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from unittest import mock

from nimlab import config
from nimlab import heartbeat as HB
from nimlab import routing
from nimlab import schedule as S
from nimlab import scheduler as SC
from nimlab import selfadmin as SA
from tests.sandbox import lab


def L(text):
    return S.parse_local(text)


def F(ts):
    return S.fmt(ts)


class TZCase(unittest.TestCase):
    """Fixed zone so the calendar maths is the same on every box."""

    def setUp(self):
        try:
            S.set_timezone("America/Los_Angeles")
        except S.ScheduleError:
            self.skipTest("no tz database on this box")
        self.addCleanup(S.set_timezone, "")


# ---------------------------------------------------------------------------
# schedules
# ---------------------------------------------------------------------------
class ScheduleParsing(TZCase):
    A = "2026-11-12 22:47"         # a Thursday

    def nxt(self, spec, n=3, after=None, anchor=None):
        a = L(after or self.A)
        return [F(t) for t in S.upcoming(spec, n, after=a, anchor=L(anchor) if anchor else a)]

    def test_minutely_interval_counts_from_the_anchor(self):
        self.assertEqual(self.nxt("FREQ=MINUTELY;INTERVAL=30", anchor="2026-11-12 22:00"),
                         ["2026-11-12 23:00", "2026-11-12 23:30", "2026-11-13 00:00"])

    def test_daily_byhour_byminute(self):
        self.assertEqual(self.nxt("FREQ=DAILY;BYHOUR=7;BYMINUTE=30", 2), ["2026-11-13 07:30", "2026-11-14 07:30"])
        self.assertEqual(self.nxt("FREQ=DAILY;BYHOUR=7", 1), ["2026-11-13 07:00"])

    def test_daily_without_byhour_keeps_the_start_time(self):
        self.assertEqual(self.nxt("FREQ=DAILY", 2, anchor="2026-11-10 06:15"),
                         ["2026-11-13 06:15", "2026-11-14 06:15"])

    def test_weekly_byday(self):
        self.assertEqual(self.nxt("FREQ=WEEKLY;BYDAY=MON,WED,FRI;BYHOUR=9"),
                         ["2026-11-13 09:00", "2026-11-16 09:00", "2026-11-18 09:00"])

    def test_monthly_first_and_last_day(self):
        self.assertEqual(self.nxt("FREQ=MONTHLY;BYMONTHDAY=1,-1;BYHOUR=6"),
                         ["2026-11-30 06:00", "2026-12-01 06:00", "2026-12-31 06:00"])

    def test_monthly_nth_weekday(self):
        self.assertEqual(self.nxt("FREQ=MONTHLY;BYDAY=1MON;BYHOUR=8", 2), ["2026-12-07 08:00", "2027-01-04 08:00"])
        self.assertEqual(self.nxt("FREQ=MONTHLY;BYDAY=-1FRI;BYHOUR=8", 1), ["2026-11-27 08:00"])

    def test_monthly_31st_skips_short_months(self):
        self.assertEqual(self.nxt("FREQ=MONTHLY;BYMONTHDAY=31", 2, anchor="2026-10-31 00:00"),
                         ["2026-12-31 00:00", "2027-01-31 00:00"])

    def test_yearly_bymonth(self):
        self.assertEqual(self.nxt("FREQ=YEARLY;BYMONTH=JAN;BYMONTHDAY=1", 1, anchor="2026-01-01 00:00"),
                         ["2027-01-01 00:00"])

    def test_hourly_interval_and_byhour_filter(self):
        self.assertEqual(self.nxt("FREQ=HOURLY;INTERVAL=2", 2, anchor="2026-11-12 20:00"),
                         ["2026-11-13 00:00", "2026-11-13 02:00"])
        self.assertEqual(self.nxt("FREQ=MINUTELY;INTERVAL=15;BYHOUR=9", 5)[-1], "2026-11-14 09:02")  # 15 min steps from 22:47

    def test_cron(self):
        self.assertEqual(self.nxt("*/15 * * * *", 2), ["2026-11-12 23:00", "2026-11-12 23:15"])
        self.assertEqual(self.nxt("0 7 * * MON-FRI", 2), ["2026-11-13 07:00", "2026-11-16 07:00"])
        self.assertEqual(self.nxt("@daily", 1), ["2026-11-13 00:00"])
        # classic cron: day-of-month OR day-of-week when both are set
        self.assertEqual(self.nxt("0 0 13 * FRI", 2), ["2026-11-13 00:00", "2026-11-20 00:00"])

    def test_one_off(self):
        self.assertEqual(self.nxt("at 2026-11-14 07:00"), ["2026-11-14 07:00"])
        self.assertEqual(S.parse("2026-11-14 07:00")["kind"], "once")
        self.assertIsNone(S.next_run("at 2026-11-01 07:00", after=L(self.A)))

    def test_start_and_end_dates(self):
        a = L(self.A)
        t = S.next_run("FREQ=DAILY;BYHOUR=7", after=a, anchor=a, start=L("2026-11-20 00:00"))
        self.assertEqual(F(t), "2026-11-20 07:00")
        self.assertIsNone(S.next_run("FREQ=DAILY;BYHOUR=7", after=a, anchor=a, end=L("2026-11-13 06:00")))

    def test_dst_fall_back_keeps_wall_clock(self):
        b = L("2026-10-31 23:00")
        self.assertEqual([F(t) for t in S.upcoming("FREQ=DAILY;BYHOUR=9", 3, after=b, anchor=b)],
                         ["2026-11-01 09:00", "2026-11-02 09:00", "2026-11-03 09:00"])

    def test_invalid_schedules_say_why(self):
        for bad, word in (("FREQ=SECONDLY", "FREQ"), ("FREQ=DAILY;BYHOUR=25", "BYHOUR"), ("* * *", "5-field"),
                          ("hello", "can't read"), ("FREQ=DAILY;BYDAY=1MON", "ordinals"),
                          ("FREQ=DAILY;COLOR=RED", "not supported"), ("", "no schedule")):
            self.assertIn(word, S.validate(bad), bad)

    def test_describe(self):
        self.assertEqual(S.describe("FREQ=MINUTELY;INTERVAL=30"), "every 30 minutes")
        self.assertEqual(S.describe("FREQ=DAILY;BYHOUR=7;BYMINUTE=30"), "every day at 07:30")
        self.assertIn("last", S.describe("FREQ=MONTHLY;BYMONTHDAY=1,-1"))

    def test_impossible_rule_returns_none_quickly(self):
        t0 = time.time()
        self.assertIsNone(S.next_run("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=30", after=L(self.A), anchor=L(self.A)))
        self.assertLess(time.time() - t0, 5)


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------
class FakeCtx:
    def __init__(self):
        self.quill_calls, self.cli_calls, self.mcp_calls, self.tg, self.mem, self.bugs = [], [], [], [], [], []
        self.quill_fn = lambda prompt: (True, "ok from quill")
        self.cli_fn = lambda argv: (True, "ran " + " ".join(argv))
        self.test_rows = {"service": ("PASS", "up"), "tunnel": ("PASS", "up")}
        self.tg_ok = True
        self.context = {"tests": {"failed": []}}

    def quill(self, prompt, who="scheduler", max_tokens=1024, timeout=None, use_tools=True):
        self.quill_calls.append((who, prompt))
        return self.quill_fn(prompt)

    def cli(self, argv, timeout=600):
        self.cli_calls.append(list(argv))
        return self.cli_fn(argv)

    def shell(self, command, timeout=60):
        return True, "exit 0\n" + command

    def mcp_call(self, tool, args):
        self.mcp_calls.append((tool, args))
        return True, f"{tool} done"

    def tests(self, names):
        return [(n, *self.test_rows.get(n, ("PASS", "ok")), None) for n in names]

    def telegram(self, text):
        self.tg.append(text)
        return (True, "sent") if self.tg_ok else (False, "no owner")

    def memory_store(self, text, meta=None):
        self.mem.append(text)
        return True, "stored"

    def bug(self, kind, message, where):
        self.bugs.append(message)
        return f"B{len(self.bugs):04d}"

    def hb_context(self, since):
        return self.context


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class LabCase(TZCase):
    def setUp(self):
        super().setUp()
        self._lab = lab()
        self.lab = self._lab.__enter__()
        self.addCleanup(self._lab.__exit__, None, None, None)
        self.ctx = FakeCtx()
        self.t0 = L("2026-11-12 22:00")
        self.clock = Clock(self.t0)
        self.cluster = {"scheduler_settings": {}}
        tm = mock.patch.object(SC, "now", self.clock)
        tm.start()
        self.addCleanup(tm.stop)
        doc = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        doc.setdefault("scheduler_settings", {})["timezone"] = "America/Los_Angeles"
        config.save_json(config.CLUSTER_CONFIG, doc)

    def sched(self, threaded=False):
        return SC.Scheduler(ctx=self.ctx, cluster=self.cluster, clock=self.clock, threaded=threaded)

    def job(self, name, **kw):
        spec = {"name": name, "schedule": "FREQ=MINUTELY;INTERVAL=30", "action_type": "quill_prompt",
                "action": "say hi", "result_to": "log"}
        spec.update(kw)
        return SC.create_job(spec, sa_shell=kw.pop("sa_shell", None))

    def runs(self, name=None):
        return SC.history(name, 100)


# ---------------------------------------------------------------------------
# jobs, the lock, retries, timeouts, overlap, catch-up
# ---------------------------------------------------------------------------
class JobStore(LabCase):
    def test_heartbeat_is_built_in_and_disabled(self):
        jobs = SC.load_jobs()
        hb = jobs["heartbeat"]
        self.assertFalse(hb["enabled"])
        self.assertEqual(hb["schedule"], "FREQ=MINUTELY;INTERVAL=30")
        with self.assertRaises(SC.JobError):
            SC.delete_job("heartbeat")

    def test_create_validates_and_plans_next_run(self):
        j = self.job("tunnel-check", action_type="test", action="tunnel,service")
        self.assertEqual(j["action"], ["tunnel", "service"])
        self.assertEqual(F(j["state"]["next_run"]), "2026-11-12 22:30")
        self.assertEqual(j["result_to"], {"dest": "log", "when": "always"})
        for bad in ({"schedule": "FREQ=NEVER"}, {"action_type": "test", "action": "nosuchtest"},
                    {"action_type": "nimlab_command", "action": "service stop"},
                    {"action_type": "shell", "action": "ls", "sa_shell": False},
                    {"action_type": "mcp_tool", "action": "tool {not json"}, {"name": "bad name!"},
                    {"result_to": "pigeon"}, {"overlap": "maybe"}):
            with self.assertRaises(SC.JobError, msg=str(bad)):
                self.job(bad.pop("name", "x"), **bad)
        with self.assertRaises(SC.JobError):
            self.job("tunnel-check")          # duplicate

    def test_edit_disable_delete_are_audited_with_before_and_after(self):
        self.job("a")
        SC.update_job("a", {"schedule": "FREQ=HOURLY"}, who="vin", source="telegram")
        SC.set_enabled("a", False)
        SC.delete_job("a")
        rows = SC.audit_tail(10, "a")
        self.assertEqual([r["op"] for r in rows], ["create", "edit", "disable", "delete"])
        self.assertEqual(rows[1]["before"], {"schedule": "FREQ=MINUTELY;INTERVAL=30"})
        self.assertEqual(rows[1]["after"], {"schedule": "FREQ=HOURLY"})
        self.assertEqual((rows[1]["who"], rows[1]["source"]), ("vin", "telegram"))

    def test_damaged_jobs_file_is_kept_aside(self):
        self.job("a")
        with open(SC._p("jobs.json"), "w") as f:
            f.write("{broken")
        self.assertIn("heartbeat", SC.load_jobs())
        self.assertTrue(any(n.startswith("jobs.json.bad-") for n in os.listdir(SC.sched_dir())))


class Running(LabCase):
    def test_due_job_runs_once_and_records_history(self):
        self.job("a")
        s = self.sched()
        self.assertEqual(s.tick(), [])
        self.clock.t = L("2026-11-12 22:30")
        self.assertEqual(len(s.tick()), 1)
        self.assertEqual(len(s.tick()), 0)              # not again in the same slot
        r = self.runs("a")[-1]
        self.assertEqual((r["status"], r["trigger"], r["output"]), ("SUCCEEDED", "schedule", "ok from quill"))
        st = SC.get_job("a")["state"]
        self.assertEqual((st["run_count"], F(st["next_run"])), (1, "2026-11-12 23:00"))
        self.assertEqual(r["routed"], ["log: ok"])

    def test_two_schedulers_never_run_the_same_slot(self):
        self.job("a")
        self.clock.t = L("2026-11-12 22:30")
        a, b = self.sched(), self.sched()
        out = []
        ths = [threading.Thread(target=lambda s=s: out.append(len(s.tick()))) for s in (a, b)]
        for th in ths:
            th.start()
        for th in ths:
            th.join()
        self.assertEqual(sum(out), 1)
        self.assertEqual(len(self.runs("a")), 1)

    def test_process_lock_lets_one_scheduler_run(self):
        l1, l2 = SC.Lock(), SC.Lock()
        self.assertTrue(l1.acquire())
        try:
            self.assertFalse(l2.acquire())
            self.assertEqual(SC.lock_holder(), os.getpid())
            buf = io.StringIO()
            self.assertEqual(SC.run_forever(log=buf.write, ctx=self.ctx), SC.EXIT_WAIT)
            self.assertIn("another scheduler", buf.getvalue())
        finally:
            l1.release()
        self.assertIsNone(SC.lock_holder())

    def test_loop_runs_ticks_and_stops(self):
        self.cluster["scheduler_settings"]["tick_sec"] = 1
        stop = threading.Event()
        stop.set()
        self.assertEqual(self.sched().loop(stop), 0)
        self.assertEqual(self.sched().loop(threading.Event(), max_ticks=1), 1)

    def test_retries_back_off_and_then_give_up(self):
        self.ctx.quill_fn = lambda p: (False, "model down")
        self.job("a", retry_count=2, retry_backoff_sec=30, result_to="telegram:only_on_failure")
        s = self.sched()
        self.clock.t = L("2026-11-12 22:30")
        s.tick()
        st = SC.get_job("a")["state"]
        self.assertEqual(st["retry_at"], self.clock.t + 30)
        self.assertEqual(self.ctx.tg, [])                  # no message while retries are left
        self.clock.t += 31
        s.tick()
        self.assertEqual(SC.get_job("a")["state"]["retry_at"], self.clock.t + 60)    # doubled
        self.clock.t += 61
        s.tick()
        rows = self.runs("a")
        self.assertEqual([r["attempt"] for r in rows], [1, 2, 3])
        self.assertTrue(all(r["status"] == "FAILED" and r["bug"] for r in rows))
        self.assertEqual(len(self.ctx.tg), 1)
        self.assertIn("FAILED", self.ctx.tg[0])
        self.assertIsNone(SC.get_job("a")["state"]["retry_at"])

    def test_timeout_is_timed_out(self):
        ev = threading.Event()
        self.addCleanup(ev.set)
        self.ctx.quill_fn = lambda p: (ev.wait(5), "late")
        self.job("slow", timeout_sec=1)
        r = self.sched().run_now("slow")
        self.assertEqual(r["status"], "TIMED_OUT")
        self.assertIn("within 1 s", r["output"])

    def test_overlap_skip_records_a_skipped_run(self):
        ev = threading.Event()
        self.addCleanup(ev.set)
        self.ctx.quill_fn = lambda p: (ev.wait(10), "done")
        self.job("a", schedule="* * * * *")
        s = self.sched(threaded=True)
        self.clock.t = L("2026-11-12 22:01")
        self.assertEqual(len(s.tick()), 1)
        self.clock.t = L("2026-11-12 22:02")
        self.assertEqual(s.tick(), [])
        self.assertEqual(self.runs("a")[-1]["status"], "SKIPPED")
        ev.set()
        for _, th in list(s.running.values()):
            th.join(5)
        self.assertEqual(self.runs("a")[-1]["status"], "SUCCEEDED")

    def test_overlap_queue_runs_after_the_current_one(self):
        ev = threading.Event()
        self.addCleanup(ev.set)
        self.ctx.quill_fn = lambda p: (ev.wait(10), "done")
        self.job("a", schedule="* * * * *", overlap="queue")
        s = self.sched(threaded=True)
        self.clock.t = L("2026-11-12 22:01")
        s.tick()
        self.clock.t = L("2026-11-12 22:02")
        s.tick()
        self.assertEqual(SC.get_job("a")["state"]["queued"], 1)
        ev.set()
        for _, th in list(s.running.values()):
            th.join(5)
        self.clock.t += 5
        self.assertEqual(len(s.tick()), 1)
        for _, th in list(s.running.values()):
            th.join(5)
        self.assertEqual([r["trigger"] for r in self.runs("a")], ["schedule", "queued"])

    def test_max_concurrent_two_allows_two(self):
        ev = threading.Event()
        self.addCleanup(ev.set)
        self.ctx.quill_fn = lambda p: (ev.wait(10), "done")
        self.job("a", schedule="* * * * *", max_concurrent=2)
        s = self.sched(threaded=True)
        for m in (1, 2, 3):
            self.clock.t = L(f"2026-11-12 22:0{m}")
            s.tick()
        self.assertEqual(sum(1 for _, th in s.running.values() if th.is_alive()), 2)
        self.assertEqual(self.runs("a")[-1]["status"], "SKIPPED")
        ev.set()

    def test_catchup_one_by_default(self):
        self.job("a")
        self.clock.t = L("2026-11-13 01:10")          # down for about 3 hours: 6 slots missed
        self.assertEqual(len(self.sched().tick()), 1)
        r = self.runs("a")
        self.assertEqual((len(r), r[0]["trigger"]), (1, "catchup"))
        self.assertEqual(F(SC.get_job("a")["state"]["next_run"]), "2026-11-13 01:30")

    def test_catchup_none_and_all(self):
        self.job("n", catchup="none")
        self.job("all", catchup="all")
        self.cluster["scheduler_settings"].update(catchup_max=3, max_parallel=5)
        self.clock.t = L("2026-11-13 01:10")
        s = self.sched()
        s.tick()
        self.assertEqual([r["status"] for r in self.runs("n")], ["MISSED"])
        for _ in range(4):
            self.clock.t += 1
            s.tick()
        self.assertEqual(len(self.runs("all")), 3)       # capped by catchup_max

    def test_max_runs_and_max_failures(self):
        self.job("twice", schedule="* * * * *", max_runs=2)
        self.ctx.quill_fn = lambda p: (False, "nope")
        s = self.sched()
        for m in (1, 2, 3):
            self.clock.t = L(f"2026-11-12 22:0{m}")
            s.tick()
        st = SC.get_job("twice")
        self.assertEqual((st["enabled"], st["state"]["state"], st["state"]["run_count"]), (False, "COMPLETED", 2))
        self.job("flaky", schedule="* * * * *", max_failures=2)
        for m in (4, 5, 6):
            self.clock.t = L(f"2026-11-12 22:0{m}")
            s.tick()
        st = SC.get_job("flaky")
        self.assertEqual((st["enabled"], st["state"]["state"]), (False, "BROKEN"))
        self.assertIn("broken jobs", " ".join(m for _, m in SC.doctor_lines()))

    def test_one_off_completes(self):
        self.job("once", schedule="at 2026-11-12 22:05")
        s = self.sched()
        self.clock.t = L("2026-11-12 22:05")
        s.tick()
        self.clock.t = L("2026-11-12 23:05")
        s.tick()
        self.assertEqual(len(self.runs("once")), 1)
        self.assertEqual(SC.get_job("once")["state"]["state"], "COMPLETED")

    def test_history_retention(self):
        self.cluster["scheduler_settings"].update(history_days=1, history_max=3)
        for i in range(5):
            SC._record_run({"run_id": str(i), "job": "a", "start": self.t0 - 86400 * (2 if i == 0 else 0) + i,
                            "status": "SUCCEEDED"})
        self.assertEqual(SC.prune_history(self.cluster, self.t0), 2)
        self.assertEqual([r["run_id"] for r in self.runs()], ["2", "3", "4"])


# ---------------------------------------------------------------------------
# action types and chains
# ---------------------------------------------------------------------------
class Actions(LabCase):
    def act(self, at, action):
        return SC.run_action(at, action, self.ctx, {"name": "t"}, timeout=10)

    def test_quill_prompt_goes_through_quill(self):
        r = self.act("quill_prompt", "how is the lab?")
        self.assertTrue(r.ok)
        self.assertEqual(self.ctx.quill_calls[-1], ("scheduler:t", "how is the lab?"))

    def test_nimlab_command(self):
        r = self.act("nimlab_command", "nimlab test service")
        self.assertTrue(r.ok)
        self.assertEqual(self.ctx.cli_calls[-1], ["test", "service"])
        self.ctx.cli_fn = lambda argv: (None, "timed out after 5 s")
        self.assertTrue(self.act("nimlab_command", "doctor").timed_out)

    def test_test_action_reports_failures_as_notable(self):
        self.ctx.test_rows["tunnel"] = ("FAIL", "no answer")
        r = self.act("test", ["service", "tunnel"])
        self.assertFalse(r.ok)
        self.assertTrue(r.notable)
        self.assertIn("1 of 2 tests failed", r.output)

    def test_mcp_tool(self):
        r = self.act("mcp_tool", SC.check_action("mcp_tool", 'charlie_mail {"to": "vin"}'))
        self.assertTrue(r.ok)
        self.assertEqual(self.ctx.mcp_calls[-1], ("charlie_mail", {"to": "vin"}))

    def test_shell_needs_shell_on(self):
        with self.assertRaises(SC.JobError):
            SC.check_action("shell", "uptime", sa_shell=False)
        self.assertEqual(SC.check_action("shell", "uptime", sa_shell=True), "uptime")
        self.assertTrue(self.act("shell", "uptime").ok)

    def test_an_action_error_is_a_failed_run_not_a_crash(self):
        def boom(p):
            raise RuntimeError("kaput")
        self.ctx.quill_fn = boom
        r = self.act("quill_prompt", "x")
        self.assertFalse(r.ok)
        self.assertIn("kaput", r.output)

    def chain(self, steps):
        return SC.check_chain({"steps": steps}, sa_shell=False)

    def test_chain_follows_on_success_and_on_failure(self):
        self.ctx.cli_fn = lambda argv: (argv[0] != "bad", "out " + argv[0])
        c = self.chain([{"name": "first", "type": "nimlab_command", "action": "bad", "on_failure": "fix"},
                        {"name": "skipme", "type": "nimlab_command", "action": "never"},
                        {"name": "fix", "type": "nimlab_command", "action": "good"}])
        r = self.act("chain", c)
        self.assertTrue(r.ok, r.output)
        self.assertEqual([s["step"] for s in r.data["steps"]], ["first", "fix"])
        self.assertNotIn("never", [a[0] for a in self.ctx.cli_calls])

    def test_chain_fails_on_an_unhandled_failure(self):
        self.ctx.cli_fn = lambda argv: (argv[0] != "bad", "x")
        c = self.chain([{"name": "a", "type": "nimlab_command", "action": "good"},
                        {"name": "b", "type": "nimlab_command", "action": "bad"},
                        {"name": "c", "type": "nimlab_command", "action": "good"}])
        r = self.act("chain", c)
        self.assertFalse(r.ok)
        self.assertEqual([s["step"] for s in r.data["steps"]], ["a", "b"])

    def test_chain_validation(self):
        for bad in ([], [{"name": "a", "type": "nope", "action": "x"}],
                    [{"name": "a", "type": "nimlab_command", "action": "x", "on_success": "zzz"}],
                    [{"name": "a", "type": "nimlab_command", "action": "x"},
                     {"name": "a", "type": "nimlab_command", "action": "y"}]):
            with self.assertRaises(SC.JobError):
                self.chain(bad)

    def test_chain_loop_is_stopped(self):
        c = self.chain([{"name": "a", "type": "nimlab_command", "action": "x", "on_success": "a"}])
        r = self.act("chain", c)
        self.assertFalse(r.ok)
        self.assertIn("loop", r.output)


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------
class Routing(LabCase):
    def test_short_forms(self):
        self.assertEqual(routing.normalize("telegram:only_on_failure"), {"dest": "telegram", "when": "only_on_failure"})
        self.assertEqual(routing.normalize("mcp_tool:charlie_mail")["tool"], "charlie_mail")
        self.assertEqual(routing.normalize(None, routing.default_for("test"))["dest"], "telegram")
        with self.assertRaises(SC.JobError):
            routing.normalize("mcp_tool")

    def test_when_rules(self):
        self.assertFalse(routing.should_send("only_on_failure", True, True))
        self.assertTrue(routing.should_send("only_on_failure", False, False))
        self.assertFalse(routing.should_send("only_if_notable", True, False))
        self.assertTrue(routing.should_send("only_if_notable", True, True))

    def test_each_destination(self):
        job = {"name": "j"}
        self.assertEqual(routing.deliver({"dest": "telegram", "when": "always"}, job, "SUCCEEDED", "hi", False,
                                         None, self.ctx), ["telegram: ok"])
        self.assertEqual(routing.deliver({"dest": "memory", "when": "always"}, job, "SUCCEEDED", "hi", False,
                                         None, self.ctx), ["memory: ok"])
        r = routing.normalize({"dest": "mcp_tool", "tool": "charlie_mail", "args": {"subject": "{subject}",
                                                                                   "body": "{text}"}})
        routing.deliver(r, job, "FAILED", "down", True, "B0001", self.ctx)
        tool, args = self.ctx.mcp_calls[-1]
        self.assertEqual(tool, "charlie_mail")
        self.assertIn("j: FAILED (bug B0001)", args["subject"])
        self.assertIn("down", args["body"])
        self.assertEqual(routing.deliver({"dest": "none", "when": "always"}, job, "SUCCEEDED", "x", 1, None,
                                         self.ctx), ["none"])
        with open(SC._p("results.log")) if os.path.exists(SC._p("results.log")) else io.StringIO() as f:
            self.assertEqual(f.read(), "")

    def test_failed_delivery_falls_back_to_the_log_and_escalation(self):
        self.ctx.tg_ok = False
        out = routing.deliver({"dest": "telegram", "when": "always"}, {"name": "j"}, "SUCCEEDED", "x", 0, None,
                              self.ctx)
        self.assertEqual(out[0], "telegram: failed (no owner)")
        self.assertEqual(out[1], "log: ok")
        self.ctx.tg_ok = True
        out = routing.deliver({"dest": "memory", "when": "always", "escalate_on_failure": "telegram"},
                              {"name": "j"}, "FAILED", "down", 1, "B9", self.ctx)
        self.assertEqual(out, ["memory: ok", "escalated telegram: ok"])

    def test_only_if_notable_compares_with_the_last_good_output(self):
        outs = iter(["tunnel up in 12 ms", "tunnel up in 15 ms", "tunnel DOWN"])
        self.ctx.quill_fn = lambda p: (True, next(outs))
        self.job("t", schedule="* * * * *", result_to="telegram:only_if_notable")
        s = self.sched()
        for m in (1, 2, 3):
            self.clock.t = L(f"2026-11-12 22:0{m}")
            s.tick()
        self.assertEqual(len(self.ctx.tg), 2)       # the first, then only the real change
        self.assertIn("DOWN", self.ctx.tg[-1])


# ---------------------------------------------------------------------------
# the heartbeat
# ---------------------------------------------------------------------------
class Heartbeat(LabCase):
    def decide(self, decisions, summary="ok"):
        answer = json.dumps({"decisions": decisions, "summary": summary})
        replies = {}

        def fn(prompt):
            if prompt.startswith("HEARTBEAT."):
                return True, "Sure.\n```json\n" + answer + "\n```"
            name = prompt.split("'")[1]
            return replies.get(name, (True, f"did {name}"))
        self.ctx.quill_fn = fn
        return replies

    def test_default_actions_exist(self):
        names = [a["name"] for a in HB.load_actions()]
        self.assertIn("health-check", names)
        self.assertEqual(HB.get_action("health-check")["run"]["type"], "test")

    def test_quill_decides_takes_and_reports(self):
        self.decide([{"name": "health-check", "decision": "take", "reason": "tests are old"},
                     {"name": "bug-review", "decision": "skip", "reason": "no new bugs"},
                     {"name": "memory-digest", "decision": "take", "reason": "8 new memories"}])
        self.ctx.context = {"bugs_since_last": [{"id": "B1"}]}
        r = SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        self.assertTrue(r.ok, r.output)
        prompt = self.ctx.quill_calls[0][1]
        for part in ("SUGGESTED ACTIONS", "health-check", "Worth doing", "FRESH CONTEXT", '"B1"'):
            self.assertIn(part, prompt)
        rep = HB.last_report()
        d = {x["name"]: x for x in rep["decisions"]}
        self.assertEqual(d["health-check"]["decision"], "take")
        self.assertEqual(d["bug-review"], {**d["bug-review"], "decision": "skip", "reason": "no new bugs"})
        self.assertEqual(d["tunnel-recover"]["reason"], "Quill did not mention it")
        self.assertEqual(d["memory-digest"]["routed"], ["memory: ok"])
        self.assertEqual(self.ctx.mem[-1].splitlines()[-1], "did memory-digest")
        self.assertIn("took 2, skipped 2", r.output)
        # the next heartbeat sees this one's decisions
        SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        self.assertIn("PREVIOUS HEARTBEAT", self.ctx.quill_calls[-1][1] if self.ctx.quill_calls[-1][1].startswith(
            "HEARTBEAT.") else [c for w, c in self.ctx.quill_calls if c.startswith("HEARTBEAT.")][-1])

    def test_max_actions_limit(self):
        HB.edit_action("tunnel-recover", {"priority": 1})
        with mock.patch.object(HB, "settings", return_value={**HB.DEFAULTS, "max_actions": 1}):
            self.decide([{"name": n, "decision": "take"} for n in
                         ("health-check", "bug-review", "tunnel-recover", "memory-digest")])
            SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        d = {x["name"]: x for x in HB.last_report()["decisions"]}
        took = [n for n, x in d.items() if x["decision"] == "take"]
        self.assertEqual(took, ["health-check"])           # priority 1, then by name
        self.assertIn("over the limit", d["tunnel-recover"]["reason"])

    def test_token_budget_limit(self):
        with mock.patch.object(HB, "settings", return_value={**HB.DEFAULTS, "token_budget": 10}):
            self.decide([{"name": "bug-review", "decision": "take"}])
            SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        d = {x["name"]: x for x in HB.last_report()["decisions"]}
        self.assertIn("out of tokens", d["bug-review"]["reason"])

    def test_quill_can_pick_another_destination_and_failures_escalate(self):
        replies = self.decide([{"name": "tunnel-recover", "decision": "take", "reason": "tunnel down"},
                               {"name": "bug-review", "decision": "take", "result_to": "telegram"}])
        replies["tunnel-recover"] = (False, "could not start the tunnel")
        self.ctx.test_rows = {}
        SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        d = {x["name"]: x for x in HB.last_report()["decisions"]}
        self.assertEqual(d["bug-review"]["dest_changed"], "Quill chose telegram instead of memory")
        self.assertEqual(d["bug-review"]["routed"], ["telegram: ok"])
        # tunnel-recover already goes to telegram, so a failure has nothing to escalate to
        self.assertFalse(d["tunnel-recover"]["ok"])
        HB.edit_action("tunnel-recover", {"result_to": "log"})
        SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        d = {x["name"]: x for x in HB.last_report()["decisions"]}
        self.assertEqual(d["tunnel-recover"]["escalated"], "failed, so also sent to telegram")
        self.assertIn("escalated telegram: ok", d["tunnel-recover"]["routed"])
        self.assertIn("also sent to telegram", HB.report_text(HB.last_report()))

    def test_route_line_in_the_result(self):
        replies = self.decide([{"name": "memory-digest", "decision": "take"}])
        replies["memory-digest"] = (True, "Owner left a deploy half done.\nROUTE: telegram")
        SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        d = {x["name"]: x for x in HB.last_report()["decisions"]}
        self.assertEqual(d["memory-digest"]["dest"], "telegram")
        self.assertNotIn("ROUTE:", self.ctx.tg[-1])

    def test_unreadable_decision_fails_the_run_with_a_report(self):
        self.ctx.quill_fn = lambda p: (True, "I think all is fine!")
        r = SC.run_action("heartbeat", "", self.ctx, {"name": "heartbeat"}, timeout=60)
        self.assertFalse(r.ok)
        self.assertIn("could not be read", HB.last_report()["summary"])

    def test_heartbeat_job_runs_from_the_scheduler(self):
        self.decide([{"name": "health-check", "decision": "take"}])
        SC.set_enabled("heartbeat", True)
        self.assertEqual(F(SC.get_job("heartbeat")["state"]["next_run"]), "2026-11-12 22:30")
        self.clock.t = L("2026-11-12 22:30")
        self.sched().tick()
        r = self.runs("heartbeat")[-1]
        self.assertEqual(r["status"], "SUCCEEDED")
        self.assertTrue(r["report_id"].startswith("hb-"))

    def test_actions_add_edit_remove_are_audited(self):
        HB.add_action({"name": "disk", "instruction": "Check free disk", "condition": "daily",
                       "result_to": "telegram:only_if_notable"}, who="vin")
        HB.edit_action("disk", {"priority": 1})
        HB.add_action({"name": "svc", "run": "test service"})
        self.assertEqual(HB.get_action("svc")["run"], {"type": "test", "action": ["service"]})
        HB.remove_action("disk")
        self.assertEqual([r["op"] for r in SC.audit_tail(10, "disk")], ["create", "edit", "delete"])
        with self.assertRaises(SC.JobError):
            HB.add_action({"name": "x"})


# ---------------------------------------------------------------------------
# Quill manages jobs (self-admin)
# ---------------------------------------------------------------------------
class FakeEntity:
    def __init__(self):
        self.cluster = config.load_cluster_config()

    def reload(self):
        self.cluster = config.load_cluster_config()


def text(res):
    return res["content"][0]["text"]


class QuillManagesJobs(LabCase):
    def setUp(self):
        super().setUp()
        SA.clear_request()
        SA._pending.clear()
        self.addCleanup(SA.clear_request)
        self.ent = FakeEntity()

    def box(self, admin=True, who="vin", source="telegram"):
        SA.set_request(admin, who, source)
        return SA.ToolBox(self.ent)

    def test_tools_are_offered_to_admins_only(self):
        self.assertIn("self_jobs", self.box().admin_names)
        self.assertNotIn("self_jobs", self.box(admin=False).admin_names)
        res = self.box(admin=False).call_tool("self_jobs", {"action": "list"})
        self.assertTrue(res.get("isError"))

    def test_check_the_tunnel_every_30_minutes(self):
        res = self.box().call_tool("self_jobs", {"action": "create", "name": "tunnel-check",
                                                 "schedule": "FREQ=MINUTELY;INTERVAL=30", "action_type": "test",
                                                 "job_action": "tunnel", "result_to": "telegram:only_on_failure"})
        self.assertFalse(res.get("isError"), text(res))
        self.assertIn("next run 2026-11-12 22:30", text(res))
        j = SC.get_job("tunnel-check")
        self.assertEqual((j["action"], j["created_by"]), (["tunnel"], "quill (asked by vin)"))
        res = self.box().call_tool("self_jobs", {"action": "edit", "name": "tunnel-check",
                                                 "schedule": "FREQ=MINUTELY;INTERVAL=15"})
        self.assertFalse(res.get("isError"), text(res))
        self.box().call_tool("self_jobs", {"action": "disable", "name": "tunnel-check"})
        rows = SC.audit_tail(10, "tunnel-check")
        self.assertEqual([r["op"] for r in rows], ["create", "edit", "disable"])
        self.assertEqual(rows[1]["before"], {"schedule": "FREQ=MINUTELY;INTERVAL=30"})
        self.assertEqual(rows[1]["after"], {"schedule": "FREQ=MINUTELY;INTERVAL=15"})
        self.assertTrue(all(r["who"] == "quill (asked by vin)" and r["source"] == "telegram" for r in rows))

    def test_delete_needs_a_confirmation_in_a_later_message(self):
        self.job("a")
        res = self.box().call_tool("self_jobs", {"action": "delete", "name": "a"})
        self.assertIn("a", SC.load_jobs())
        code = json.dumps(res)
        self.assertIn("confirm", code.lower())

    def test_a_bad_request_is_explained(self):
        res = self.box().call_tool("self_jobs", {"action": "create", "name": "x", "schedule": "whenever"})
        self.assertTrue(res.get("isError"))
        self.assertIn("can't read the schedule", text(res))

    def test_scheduled_turns_cannot_change_jobs(self):
        res = self.box(source="scheduler").call_tool("self_jobs", {"action": "create", "name": "sneaky",
                                                                   "schedule": "@daily", "job_action": "x"})
        self.assertTrue(res.get("isError"))
        self.assertNotIn("sneaky", SC.load_jobs())
        res = self.box(source="scheduler").call_tool("self_jobs", {"action": "list"})
        self.assertFalse(res.get("isError"))

    def test_quill_manages_suggested_actions(self):
        res = self.box().call_tool("self_heartbeat_actions", {"action": "add", "name": "disk",
                                                              "instruction": "Check free disk space",
                                                              "condition": "once a day", "result_to": "telegram"})
        self.assertFalse(res.get("isError"), text(res))
        self.box().call_tool("self_heartbeat_actions", {"action": "disable", "name": "disk"})
        self.assertFalse(HB.get_action("disk")["enabled"])
        self.assertEqual([r["who"] for r in SC.audit_tail(5, "disk")], ["quill (asked by vin)"] * 2)


# ---------------------------------------------------------------------------
# the service, the CLI, doctor, the Tests menu
# ---------------------------------------------------------------------------
class ServiceAndCli(LabCase):
    def test_service_runs_the_scheduler_child(self):
        from nimlab import service as SV
        cmds = SV.child_commands({"service_settings": {}})
        self.assertEqual(cmds["scheduler"][-3:], ["nimlab", "scheduler", "run"])
        self.assertNotIn("scheduler", SV.child_commands({"service_settings": {"scheduler": False}}))
        self.assertIn(("scheduler", ("nimlab", "scheduler", "run")), SV.STRAY_PATTERNS)

    def test_supervisor_restarts_a_crashed_scheduler(self):
        from nimlab import service as SV

        class P:
            n = 0

            def __init__(self):
                P.n += 1
                self.pid, self.rc, self.stdout = 5000 + P.n, None, io.StringIO("")

            def poll(self):
                return self.rc

            def terminate(self):
                self.rc = 0

            kill = terminate

            def wait(self, timeout=None):
                return self.rc
        procs = []

        def popen(cmd, **_kw):
            procs.append(P())
            return procs[-1]
        clock = Clock(1000.0)
        sup = SV.Supervisor(commands_fn=lambda: {"scheduler": ["scheduler"]}, config_mtime=lambda: 0, popen=popen,
                            clock=clock, sleep=lambda s: None)
        sup.step()
        self.assertEqual(len(procs), 1)
        procs[0].rc = 1                                   # crash
        for _ in range(40):
            clock.t += 120
            sup.step()
            if len(procs) > 1:
                break
        self.assertGreaterEqual(len(procs), 2)

    def run_cli(self, *argv):
        from nimlab import cli
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(list(argv))
        return rc, buf.getvalue()

    def test_cli_jobs_and_heartbeat(self):
        rc, out = self.run_cli("jobs", "create", "tc", "--schedule", "*/30 * * * *", "--type", "test", "--do",
                               "tunnel", "--result-to", "telegram:only_on_failure")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("jobs", "list")
        self.assertIn("tc", out)
        self.assertIn("heartbeat", out)
        rc, out = self.run_cli("jobs", "next", "tc", "-n", "2")
        self.assertIn("2026-11-12 22:30, 2026-11-12 23:00", out)
        rc, out = self.run_cli("jobs", "edit", "tc", "--schedule", "nonsense")
        self.assertEqual(rc, 2)
        rc, out = self.run_cli("heartbeat", "enable")
        self.assertEqual(rc, 0, out)
        self.assertTrue(SC.get_job("heartbeat")["enabled"])
        rc, out = self.run_cli("heartbeat", "schedule", "FREQ=HOURLY")
        self.assertEqual(SC.get_job("heartbeat")["schedule"], "FREQ=HOURLY")
        rc, out = self.run_cli("heartbeat", "actions", "add", "disk", "--instruction", "check disk", "--priority",
                               "2")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_cli("heartbeat", "status")
        self.assertIn("Heartbeat: ON", out)
        rc, out = self.run_cli("jobs", "delete", "tc", "--yes")
        self.assertEqual(rc, 0)
        rc, out = self.run_cli("jobs", "audit")
        self.assertIn("delete job tc", out)

    def test_scheduler_menu_walks(self):
        from nimlab import jobscli
        answers = iter(["5", "m1", "@daily", "1", "hello", "", "3", "e", "b", "1", "b", "b"])
        out = []
        jobscli.menu(ask=lambda p: next(answers), say=out.append)
        self.assertIn("m1", SC.load_jobs())
        self.assertTrue(SC.get_job("heartbeat")["enabled"])

    def test_doctor_and_tests_menu(self):
        from nimlab import doctor, systests
        self.job("a")
        lines = SC.doctor_lines()
        self.assertTrue(any("not running" in m for _, m in lines))
        self.assertIn("scheduler_checks", dir(doctor))
        t = systests.find("scheduler")
        self.assertIsNotNone(t)
        r = t.fn(type("C", (), {"scheduler": lambda self: {"jobs": SC.load_jobs(), "holder": 4242}})())
        self.assertEqual(r.status, "pass", r.detail)

    def test_settings_have_defaults(self):
        s = SC.settings({})
        self.assertEqual((s["tick_sec"], s["catchup"], s["max_parallel"]), (20, "one", 2))
        h = HB.settings({})
        self.assertEqual((h["max_actions"], h["escalate_failures_to"]), (3, "telegram"))


# ---------------------------------------------------------------------------
# Telegram slash commands (nimlab.tgcmds, carried over from the interim patch)
# ---------------------------------------------------------------------------
class TgBase(LabCase):
    OWNER, OTHER = 1111, 2222

    def setUp(self):
        super().setUp()
        from nimlab import telegram as TG, tgcmds
        self.TG, self.tg = TG, tgcmds
        self.sent, self.cli = [], []

        class Api:
            def __call__(api, url, data, headers, timeout):
                method = url.rsplit("/", 1)[1]
                params = json.loads(data) if data else {}
                if method == "sendMessage":
                    # Connector.send escapes for MarkdownV2; compare the plain text
                    self.sent.append(re.sub(r"\\(.)", r"\1", params.get("text", "")))
                    return 200, json.dumps({"ok": True, "result": {"message_id": 1}}).encode()
                return 200, json.dumps({"ok": True, "result": True}).encode()

        class Backend:
            def chat(b, messages, user, admin=False):
                self.sent.append("QUILL")
                return "quill reply"
        ts = {"allow": [self.OWNER, self.OTHER], "owner": self.OWNER}
        self.conn = TG.Connector(TG.Bot("123456789:AAE" + "x" * 32, http=Api()), Backend(), ts, save=lambda: None,
                                 log=lambda *a: None)
        for name, fn in (("_spawn", lambda f: f()),
                         ("run_cli", lambda args, timeout: self.cli.append(list(args)) or "cli: " + " ".join(args))):
            pm = mock.patch.object(tgcmds, name, fn)
            pm.start()
            self.addCleanup(pm.stop)

    def say(self, text, uid=None):
        uid = uid or self.OWNER
        self.sent.clear()
        self.conn.handle({"update_id": 1, "message": {"message_id": 5, "from": {"id": uid},
                                                       "chat": {"id": uid, "type": "private"}, "text": text}})
        return self.sent


class TelegramCommands(TgBase):
    def test_greeting_and_help(self):
        out = self.say("/start")
        self.assertTrue(out[0].startswith("Hi! Send text, a photo or a voice note."))
        for c in ("/jobs", "/heartbeat", "/status", "/new", "/id"):
            self.assertIn(c, out[0])
        self.assertIn("/model - Exposed model", out[0])        # 3.8.1: real, no "(3.8.1)" marker
        self.assertNotIn("(3.8.0)", out[0])
        self.assertNotIn("(3.8.1)", out[0])

    def test_jobs_lists_jobs(self):
        self.job("tunnel-check", action_type="test", action="tunnel")
        out = self.say("/jobs")[0]
        self.assertIn("[on] tunnel-check: every 30 minutes; next 2026-11-12 22:30", out)
        self.assertIn("[off] heartbeat", out)
        self.assertEqual(self.cli, [])

    def test_heartbeat_status_and_run(self):
        out = self.say("/heartbeat")[0]
        self.assertIn("Heartbeat: off", out)
        out = self.say("/heartbeat run")
        self.assertIn("Running a heartbeat", out[0])
        self.assertEqual(self.cli[-1], ["heartbeat", "run-now"])
        self.assertEqual(out[-1], "cli: heartbeat run-now")
        self.assertIn("Usage", self.say("/heartbeat bogus")[0])

    def test_owner_only(self):
        self.assertEqual(self.say("/jobs", uid=self.OTHER), ["That command is for the owner only."])
        self.assertEqual(self.say("/heartbeat run", uid=self.OTHER), ["That command is for the owner only."])
        self.assertTrue(self.say("/help", uid=self.OTHER)[0].startswith("Hi!"))

    def test_planned_commands_are_real_in_381(self):
        for c in ("/model", "/remember", "/voice", "/service", "/cancel"):
            self.assertNotIn(f"{c} arrives in 3.8.1.", self.say(c))

    def test_cli_commands_and_fall_through(self):
        self.assertEqual(self.say("/roles")[-1], "cli: roles")
        self.assertEqual(self.say("/recall tunnel url")[-1], "cli: memory recall tunnel url")
        self.assertIn("Usage", self.say("/recall")[0])
        self.assertIn("Cleared", self.say("/new")[0])
        self.assertIn("Cleared", self.say("/reset")[0])          # still telegram.py's own
        self.assertIn("QUILL", self.say("/whatever"))             # unknown: goes to Quill as chat
        self.assertIn("QUILL", self.say("hello"))

    def test_every_cli_command_parses(self):
        from nimlab import cli
        p = cli.build_parser()
        for c, (_d, build, _t) in self.tg.COMMANDS.items():
            if build:
                p.parse_args(build("x"))
        for argv in (["heartbeat", "run-now"], ["service", "status"], ["serve", "tunnel", "status"]):
            p.parse_args(argv)

    def test_a_broken_command_does_not_stop_the_poller(self):
        with mock.patch.object(self.tg, "handle", side_effect=RuntimeError("boom")):
            out = self.say("/start")
        self.assertTrue(out[0].startswith("Hi! Send text, a photo or a voice note."))


class Autoplay(TgBase):
    """/autoplay (3.8.0, folded in from the phone's interim patch): owner-only,
    no argument toggles, state in data/tg_autoplay.json, plays on the phone
    speaker after sendVoice and never breaks the voice reply."""

    def setUp(self):
        super().setUp()
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.state = os.path.join(tmp, "tg_autoplay.json")
        self.audio = os.path.join(tmp, "tg_autoplay_last")
        self.which = {"termux-media-player": "/usr/bin/termux-media-player"}
        self.termux = True
        self.ran, self.logs = [], []
        for name, val in (("AUTOPLAY_FILE", self.state), ("AUTOPLAY_AUDIO", self.audio),
                          ("_termux", lambda: self.termux)):
            pm = mock.patch.object(self.tg, name, val)
            pm.start()
            self.addCleanup(pm.stop)
        pm = mock.patch.object(self.tg.shutil, "which", lambda n: self.which.get(n))
        pm.start()
        self.addCleanup(pm.stop)

    def play(self, data=b"RIFFwav"):
        return self.tg.autoplay(data, ".wav", self.logs.append, spawn=lambda f: f(),
                                run=lambda cmd, timeout: self.ran.append(cmd))

    def test_toggle_on_off_status_and_state_file(self):
        self.conn.t["voice_replies"] = True
        out = self.say("/autoplay")[0]
        self.assertIn("Autoplay is on.", out)
        self.assertIn("termux-media-player", out)
        with open(self.state) as f:
            self.assertEqual(json.load(f), {"on": True})
        self.assertIn("Autoplay is off.", self.say("/autoplay")[0])            # toggles back
        self.assertIn("Autoplay is on.", self.say("/autoplay on")[0])
        self.assertIn("Autoplay is on.", self.say("/autoplay status")[0])      # status changes nothing
        self.assertIn("Autoplay is off.", self.say("/autoplay OFF")[0])
        self.assertIn("Usage: /autoplay [on|off|status]", self.say("/autoplay loud")[0])
        self.assertFalse(self.tg.autoplay_on())

    def test_owner_only_and_listed(self):
        self.assertEqual(self.say("/autoplay on", uid=self.OTHER), ["That command is for the owner only."])
        self.assertFalse(os.path.exists(self.state))
        self.assertIn("/autoplay - Play voice replies on the phone speaker", self.say("/help")[0])
        self.assertIn("autoplay - Play voice replies on the phone speaker", self.tg.botfather_text())
        with open(os.path.join(self.tg.PROJECT, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        for line in self.tg.botfather_text().splitlines():
            self.assertIn(line, readme)

    def test_warnings(self):
        self.which = {}
        out = self.say("/autoplay on")[0]
        self.assertIn("No player found: pkg install termux-api", out)
        self.assertIn("Voice replies are off", out)
        self.termux = False
        import tempfile
        with mock.patch.dict(os.environ, {"NIMLAB_AUDIO_BUS_DIR": tempfile.mkdtemp(prefix="bus")}):
            out = self.say("/autoplay status")[0]
            # 3.8.5: off Termux the reply goes to the active phone on the audio bus
            self.assertIn("No phone is active on the audio bus", out)
            self.assertEqual(self.play(), "no device")
        self.assertEqual(self.ran, [])

    def test_plays_with_termux_media_player_then_play_audio(self):
        self.assertEqual(self.play(), "off")
        self.tg.set_autoplay(True)
        self.assertEqual(self.play(b"WAVDATA"), "playing")
        path = self.audio + ".wav"
        self.assertEqual(self.ran, [["termux-media-player", "stop"], ["termux-media-player", "play", path]])
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"WAVDATA")
        self.ran.clear()
        self.which = {"play-audio": "/usr/bin/play-audio"}
        self.play()
        self.assertEqual(self.ran, [["play-audio", path]])
        self.which = {}
        self.assertEqual(self.play(), "no player")
        self.assertIn("no player", self.logs[-1])
        self.assertEqual(self.play(b""), "empty")

    def test_never_raises(self):
        self.tg.set_autoplay(True)

        def boom(cmd, timeout):
            raise OSError("speaker busy")
        self.assertEqual(self.tg.autoplay(b"x", ".wav", self.logs.append, spawn=lambda f: f(), run=boom), "playing")
        self.assertIn("speaker busy", self.logs[-1])
        with mock.patch.object(self.tg, "player", side_effect=RuntimeError("bad")):
            self.assertEqual(self.play(), "error")
        with open(self.state, "w") as f:
            f.write("{not json")
        self.assertFalse(self.tg.autoplay_on())

    def test_hook_runs_after_send_voice_and_a_failure_keeps_the_reply(self):
        calls = []
        conn = self.conn
        conn.backend.speech = lambda text, user: b"WAV"
        conn.convert = lambda data, args, a, b: b"OGG"
        conn.bot.call = lambda method, **kw: calls.append(method) or {"message_id": 1}
        with mock.patch.object(self.tg, "autoplay", side_effect=lambda *a, **k: calls.append("autoplay")):
            self.assertTrue(conn._voice_reply(self.OWNER, "short", "telegram:1"))
        self.assertEqual(calls, ["sendVoice", "autoplay"])
        calls.clear()
        with mock.patch.object(self.tg, "autoplay", side_effect=RuntimeError("player exploded")):
            self.assertTrue(conn._voice_reply(self.OWNER, "short", "telegram:1"))
        self.assertEqual(calls, ["sendVoice"])

if __name__ == "__main__":
    unittest.main()
