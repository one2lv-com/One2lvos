"""Menus first (3.8.2): Health & repair, Scheduler, Service & update, and
Custom endpoints, as short numbered screens.

Every result screen ends with the next steps you can pick right there (a
failed check offers its repair, the heartbeat status offers Turn on / Turn
off, a new job offers Run it now), so nothing tells you to go and type a
command. The launcher opens these with `nimlab ui <screen>`.
"""

import re

from . import commands as CMD


class Back(Exception):
    pass


class UI:
    def __init__(self, ask=input, say=print, runner=None, secret=None):
        self._ask, self.say, self.runner = ask, say, runner
        self._secret = secret

    # -- basics ---------------------------------------------------------
    def ask(self, prompt, default=""):
        try:
            v = self._ask(prompt)
        except (EOFError, KeyboardInterrupt):
            raise Back() from None
        v = (v or "").strip()
        return v or default

    def secret(self, prompt):
        if self._secret:
            return self._secret(prompt)
        if self._ask is input:
            import getpass
            try:
                return getpass.getpass(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                raise Back() from None
        return self.ask(prompt)

    def yes(self, prompt):
        return self.ask(prompt + " [y/N]: ").lower() in ("y", "yes")

    def title(self, text):
        from . import colors as C
        self.say("")
        self.say(C.section(text) if C.enabled() else f"== {text} ==")

    def cli(self, *argv):
        """Run `nimlab <argv>` with the terminal attached. -> exit code."""
        return CMD.run_cli([str(a) for a in argv], self.runner)

    def pick(self, items, prompt="Choose: "):
        """items: [(key, label, fn)]. Shows them, runs the chosen fn. -> its
        result, or Back on 0/Enter."""
        from . import colors as C
        for key, label, _fn in items:
            self.say(f"  {C.paint(key, 'accent', 'bold') if C.enabled() else key}) {label}")
        self.say(f"  {'0'}) Back")
        c = self.ask(prompt).lower()
        if c in ("", "0", "q", "b"):
            raise Back()
        for key, _label, fn in items:
            if c == key.lower():
                return fn()
        self.say("Not an option.")
        return None

    def menu(self, title, build):
        """A screen that redraws until Back. build() -> (header_lines, items)."""
        while True:
            self.title(title)
            header, items = build()
            for ln in header:
                self.say("  " + ln)
            try:
                nxt = self.pick(items)
            except Back:
                return
            self.next_steps(nxt)

    def next_steps(self, nxt):
        """After a result: offer its follow-up actions, chain them."""
        while nxt:
            self.say("")
            self.say("Next:")
            try:
                nxt = self.pick(nxt, "Choose (0 = back): ")
            except Back:
                return

    # ======================================================================
    # Health & repair
    # ======================================================================
    def health(self):
        def build():
            from . import doctor as D
            n = len(D.planned_repairs())
            return (["Checks change nothing. Repair runs only safe fixes, after a yes."], [
                ("1", "Quick health check", self.quick_check),
                ("2", "Full check (adds memory round trip and MCP)", self.full_check),
                ("3", f"Repair ({n} safe fix{'es' if n != 1 else ''} available)" if n else "Repair (nothing to fix)",
                 self.repair),
                ("4", "Service: status, start, stop, logs", lambda: self.service() or None),
                ("5", "Clean restart (stop every copy, start once, check)", self.clean_restart),
                ("6", "Recent errors (bug IDs)", lambda: (self.cli("bugs"), None)[1]),
            ])
        self.menu("Health & repair", build)

    def quick_check(self):
        from . import doctor as D
        rep = D.collect(only=D.QUICK, mcp=False, memory=False)
        D.print_report(rep, self.say)
        self.say("")
        s = rep["summary"]
        self.say(f"{s['ok']} ok, {s['warn']} warnings, {s['fail']} problems.")
        return self.followups(rep)

    def full_check(self):
        self.cli("doctor")
        from . import doctor as D
        return self.followups(D.collect(only=D.QUICK, mcp=False, memory=False))

    def followups(self, rep):
        """The actions a report suggests, as menu items."""
        items, seen = [], set()

        def add(key, label, fn):
            if key not in seen:
                seen.add(key)
                items.append((key, label, fn))
        if rep.get("repairs_available"):
            add("r", f"Repair now ({rep['repairs_available']} safe fixes)", self.repair)
        for c in rep.get("checks", []):
            if c["status"] == "ok":
                continue
            sec, text = c["section"], (c["message"] + " " + (c.get("fix") or "")).lower()
            if sec == "processes" and "duplicate" in text:
                add("c", "Clean restart", self.clean_restart)
            elif sec == "scheduler":
                add("w", "Open the scheduler menu", lambda: self.scheduler() or None)
            elif sec == "telegram":
                add("s", "Start the service (runs the bot)", lambda: (self.cli("service", "start"), None)[1])
            elif sec == "endpoints":
                add("e", "Custom endpoints", lambda: self.endpoints() or None)
            elif sec == "identity" and "off" in text:
                add("i", "Turn the identity pin on", self.pin_on)
            elif sec == "update":
                add("l", "Service log", lambda: (self.cli("service", "logs"), None)[1])
            elif sec == "config":
                add("b", "Show the backups folder", self.show_backups)
        return items

    def repair(self):
        from . import doctor as D
        todo = D.planned_repairs()
        if not todo:
            self.say("Nothing to repair: no stale pid files, wrong file modes or settings that can never work.")
            return None
        self.say("Safe repairs (your settings are backed up first):")
        for _id, desc, _fn in todo:
            self.say("  - " + desc)
        if not self.yes(f"Run these {len(todo)} repair(s)?"):
            self.say("Nothing changed.")
            return None
        res = D.fix(out=self.say)
        return self.followups(res["after"]) if res.get("after") else None

    def pin_on(self):
        from . import config
        cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        cfg.setdefault("memory_settings", {})["pin_identity"] = True
        config.save_json(config.CLUSTER_CONFIG, cfg)
        self.say("[ok] Identity pin is on.")

    def show_backups(self):
        import os
        from . import store
        d = os.path.join(store.data_dir(), "backups")
        names = sorted(os.listdir(d))[-8:] if os.path.isdir(d) else []
        self.say(f"Backups in {d}:" if names else "No backups yet.")
        for n in names:
            self.say("  " + n)

    def clean_restart(self):
        self.say("This stops auto-restart, stops every Nim Lab copy (server, bot, scheduler), starts the service "
                 "once and checks it. Your keys, settings and memory are not touched.")
        if not self.yes("Clean restart now?"):
            return None
        code = self.cli("update")
        if code != 0:
            return [("l", "Service log", lambda: (self.cli("service", "logs"), None)[1]),
                    ("h", "Quick health check", self.quick_check)]
        return None

    # ======================================================================
    # Service & update
    # ======================================================================
    def service(self):
        def build():
            from . import service as SV
            try:
                head = ["Now: " + SV.brief()]
            except Exception as e:  # noqa: BLE001
                head = [f"Now: unknown ({type(e).__name__})"]
            sv = SV.settings()
            tg = bool(sv.get("telegram"))
            return (head, [
                ("1", "Status (details)", lambda: (self.cli("service", "status"), None)[1]),
                ("2", "Start", lambda: (self.cli("service", "start"), None)[1]),
                ("3", "Restart", lambda: (self.cli("service", "restart"), None)[1]),
                ("4", "Stop", lambda: self.yes("Stop the service (server and bot stop too)?") and
                 (self.cli("service", "stop"), None)[1]),
                ("5", "Clean restart / after an update", self.clean_restart),
                ("6", "Log (last lines)", lambda: (self.cli("service", "logs"), None)[1]),
                ("7", f"Telegram bot in the service: {'on' if tg else 'off'} (turn {'off' if tg else 'on'})",
                 lambda: (self.cli("service", "telegram", "off" if tg else "on"), None)[1]),
                ("8", "Install (start at boot, restart on crash)", lambda: (self.cli("service", "install"), None)[1]),
                ("9", "Remove the service files", lambda: self.yes("Stop and remove the service?") and
                 (self.cli("service", "remove"), None)[1]),
            ])
        self.menu("Service & update", build)

    # ======================================================================
    # Scheduler
    # ======================================================================
    def scheduler(self):
        def build():
            from . import scheduler as SC
            on = self.sched_on()
            s = SC.summary()
            head = [SC.status_line()]
            hint = SC.not_running_hint() if on else ""
            if hint:
                head.append(hint)
            return (head, [
                ("1", "Scheduler: on (turn off)" if on else "Scheduler: off (turn on)", self.sched_toggle),
                ("2", "Add a job (step by step)", self.add_job),
                ("3", f"Jobs ({s['jobs']}): run, edit, turn on/off, delete", self.jobs),
                ("4", f"Heartbeat: {'on' if s['heartbeat'] else 'off'}", lambda: self.heartbeat() or None),
                ("5", "Run history", lambda: (self.cli("jobs", "history"), None)[1]),
            ])
        self.menu("Scheduler & heartbeat", build)

    def sched_on(self):
        from . import scheduler as SC, service as SV
        return bool(SC.settings().get("enabled", True)) and bool(SV.settings().get("scheduler", True))

    def sched_toggle(self):
        from . import config, scheduler as SC, service as SV
        on = not self.sched_on()
        cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        cfg.setdefault("scheduler_settings", {})["enabled"] = on
        config.save_json(config.CLUSTER_CONFIG, cfg)
        sv = SV.settings()
        sv["scheduler"] = on
        SV.save_settings(sv)
        if not on:
            self.say("[ok] Scheduler off. The service stops it within a minute; jobs keep their settings.")
            return None
        self.say("[ok] Scheduler on.")
        if SC.lock_holder():
            return None
        if self.service_running():
            self.say("The service starts the scheduler within a minute.")
            return [("r", "Restart the service now (starts it at once)",
                     lambda: (self.cli("service", "restart"), None)[1])]
        self.say("The scheduler runs inside the background service, which is not running.")
        return [("s", "Start the service now", lambda: (self.cli("service", "start"), None)[1]),
                ("i", "Install the service (also starts at boot)", lambda: (self.cli("service", "install"), None)[1])]

    def service_running(self):
        from . import updater
        try:
            return any(k == "supervisor" for _p, _pp, k, _c in updater.nimlab_procs(updater.Host()))
        except Exception:  # noqa: BLE001
            return False

    # -- job wizard -----------------------------------------------------
    WHAT = [("1", "Ask Quill something (a prompt)", "quill_prompt", "What should Quill do? "),
            ("2", "Run a Nim Lab command (like: doctor --quick)", "nimlab_command", "Command after 'nimlab': "),
            ("3", "Run a test (like: memory)", "test", "Test name: "),
            ("4", "Run a shell command", "shell", "Shell command: ")]
    DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    def ask_what(self):
        from . import scheduler as SC
        self.say("What should the job do?")
        chosen = {}

        def mk(at, prompt):
            def f():
                if at == "shell" and not SC._shell_on():
                    self.say("Shell jobs are off (Tools menu > shell access). Pick another kind.")
                    return None
                text = self.ask(prompt)
                if text:
                    chosen.update(action_type=at, action=text)
            return f
        while not chosen:
            self.pick([(k, label, mk(at, p)) for k, label, at, p in self.WHAT])
        return chosen

    def hhmm(self, prompt="Time (HH:MM, 24-hour): "):
        while True:
            t = self.ask(prompt)
            m = re.match(r"^(\d{1,2})(?::(\d\d))?$", t)
            if m and int(m.group(1)) < 24 and int(m.group(2) or 0) < 60:
                return int(m.group(1)), int(m.group(2) or 0)
            if not t:
                raise Back()
            self.say("Type a time like 8:00 or 18:30.")

    def ask_when(self):
        from . import schedule as S
        self.say("When should it run?")
        out = {}

        def minutes():
            n = self.ask("Every how many minutes? ", "30")
            if n.isdigit() and int(n) > 0:
                out["s"] = f"FREQ=MINUTELY;INTERVAL={int(n)}"

        def daily(byday=None):
            h, m = self.hhmm()
            out["s"] = "FREQ=" + ("WEEKLY;BYDAY=" + byday if byday else "DAILY") + f";BYHOUR={h};BYMINUTE={m}"

        def weekly():
            d = self.ask("Which day? (" + " ".join(x.title() for x in self.DAYS) + "): ").upper()[:3]
            if d in self.DAYS:
                daily(d)
            else:
                self.say("Not a day.")

        def once():
            t = self.ask("Date and time (YYYY-MM-DD HH:MM): ")
            if t:
                out["s"] = "at " + t

        def typed():
            t = self.ask("Schedule (cron like '*/30 * * * *', or FREQ=...; BYDAY uses MON..SUN): ")
            if t:
                out["s"] = t
        while "s" not in out:
            self.pick([("1", "Every few minutes", minutes), ("2", "Every hour",
                                                            lambda: out.update(s="FREQ=HOURLY;INTERVAL=1")),
                       ("3", "Every day at a time", daily), ("4", "Weekdays at a time",
                                                              lambda: daily("MON,TUE,WED,THU,FRI")),
                       ("5", "Once a week", weekly), ("6", "Once, at a date and time", once),
                       ("7", "Type a schedule", typed)])
            if "s" in out:
                err = S.validate(out["s"])
                if err:
                    self.say(f"That schedule doesn't work: {err}")
                    out.pop("s")
        return out["s"]

    def ask_result(self):
        self.say("Where should the result go?")
        r = {}
        self.pick([("1", "Just the log (see Run history)", lambda: r.update(dest="log", when="always")),
                   ("2", "Telegram, every time", lambda: r.update(dest="telegram", when="always")),
                   ("3", "Telegram, only when it fails", lambda: r.update(dest="telegram", when="only_on_failure"))])
        return r or {"dest": "log", "when": "always"}

    def add_job(self):
        from . import scheduler as SC, schedule as S
        self.title("Add a job")
        try:
            what = self.ask_what()
            when = self.ask_when()
            res = self.ask_result()
            default = re.sub(r"[^a-z0-9]+", "-", what["action"].lower()).strip("-")[:24] or "job"
            name = self.ask(f"Name (Enter for {default}): ", default)
        except Back:
            self.say("Not saved.")
            return None
        self.say("")
        self.say(f"  {name}: {what['action_type']} \"{what['action']}\"")
        self.say(f"  when: {S.describe(when)}; result: {res['dest']} ({res['when'].replace('_', ' ')})")
        if not self.yes("Save this job?"):
            self.say("Not saved.")
            return None
        try:
            j = SC.create_job({"name": name, "schedule": when, "result_to": res, **what}, who="menu", source="menu")
        except Exception as e:  # noqa: BLE001 - JobError, ScheduleError: say why and stay in the menu
            self.say(f"[x] Not saved: {e}")
            return None
        self.say(f"[ok] Saved {j['name']}; next run {S.fmt(j['state'].get('next_run'))}")
        nxt = [("r", "Run it now (a test run)", lambda: (self.cli("jobs", "run", j["name"]), None)[1])]
        hint = SC.not_running_hint()
        if hint:
            self.say(hint)
            nxt.append(("o", "Turn the scheduler on / start it", self.sched_toggle if not self.sched_on()
                        else lambda: (self.cli("service", "start"), None)[1]))
        return nxt

    def jobs(self):
        from . import scheduler as SC
        jobs = SC.load_jobs()
        if not jobs:
            self.say("No jobs yet.")
            return [("a", "Add a job", self.add_job)]
        names = sorted(jobs)
        items = []
        for i, n in enumerate(names, 1):
            j = jobs[n]
            items.append((str(i), f"[{'on ' if j.get('enabled') else 'off'}] {n}", lambda n=n: self.job(n) or None))
        self.pick(items)
        return None

    def job(self, name):
        from . import scheduler as SC, schedule as S

        def build():
            j = SC.get_job(name)
            if not j:
                raise Back()
            st = j.get("state") or {}
            on = j.get("enabled")
            head = [f"{j.get('action_type')}: {str(j.get('action') or j.get('description') or '')[:80]}",
                    f"when: {S.describe(j['schedule'])}; next: {S.fmt(st.get('next_run')) if on else '-'}; "
                    f"last: {st.get('last_status') or '-'}"]
            items = [("1", "Run it now", lambda: (self.cli("jobs", "run", name), None)[1]),
                     ("2", "Turn off" if on else "Turn on", lambda: self.set_job(name, not on)),
                     ("3", "Change when it runs", lambda: self.edit_job(name, "when")),
                     ("4", "Next run times", lambda: (self.cli("jobs", "next", name), None)[1]),
                     ("5", "Its history", lambda: (self.cli("jobs", "history", name), None)[1]),
                     ("6", "Details", lambda: (self.cli("jobs", "show", name), None)[1])]
            if not j.get("builtin"):
                items[3:3] = [("7", "Change what it does", lambda: self.edit_job(name, "what")),
                              ("8", "Delete", lambda: self.delete_job(name))]
            return head, items
        self.menu(f"Job: {name}", build)

    def set_job(self, name, on):
        from . import scheduler as SC
        SC.set_enabled(name, on, who="menu", source="menu")
        self.say(f"[ok] {name} turned {'on' if on else 'off'}.")
        hint = SC.not_running_hint() if on else ""
        if hint:
            self.say(hint)
            return [("o", "Turn the scheduler on / start it", self.sched_toggle if not self.sched_on()
                     else lambda: (self.cli("service", "start"), None)[1])]
        return None

    def edit_job(self, name, part):
        from . import scheduler as SC, schedule as S
        try:
            ch = {"schedule": self.ask_when()} if part == "when" else self.ask_what()
            j = SC.update_job(name, ch, who="menu", source="menu")
        except Back:
            self.say("Not changed.")
            return None
        except Exception as e:  # noqa: BLE001
            self.say(f"[x] Not changed: {e}")
            return None
        self.say(f"[ok] {name} changed; next run {S.fmt(j['state'].get('next_run'))}")
        return None

    def delete_job(self, name):
        from . import scheduler as SC
        if self.yes(f"Delete {name}? Its history stays in the log."):
            SC.delete_job(name, who="menu", source="menu")
            self.say(f"[ok] Deleted {name}.")
            raise Back()
        return None

    # -- heartbeat ------------------------------------------------------
    def heartbeat(self):
        def build():
            from . import heartbeat as HB, scheduler as SC
            j = SC.load_jobs().get(SC.HEARTBEAT) or {}
            on = bool(j.get("enabled"))
            head = [ln.strip() for ln in HB.status_lines()[:6]]
            return (head, [
                ("1", "Turn off" if on else "Turn on", lambda: self.set_job(SC.HEARTBEAT, not on)),
                ("2", "Try it now (one heartbeat)", lambda: (self.cli("heartbeat", "run-now"), None)[1]),
                ("3", "How often", lambda: self.edit_job(SC.HEARTBEAT, "when")),
                ("4", "Last reports", lambda: (self.cli("heartbeat", "reports"), None)[1]),
                ("5", "Suggested actions", lambda: (self.cli("heartbeat", "actions"), None)[1]),
            ])
        self.menu("Heartbeat", build)

    # ======================================================================
    # Custom endpoints
    # ======================================================================
    def endpoints(self):
        def build():
            from . import endpoints as EP
            eps = EP.all_endpoints()
            items = [("a", "Add an endpoint (your own gateway)", self.add_endpoint)]
            for i, e in enumerate(eps, 1):
                items.append((str(i), f"{e['name']}  ({len(e.get('models', []))} models)",
                              lambda n=e["name"]: self.endpoint(n) or None))
            return (["Your own OpenAI-compatible servers. Their models can go on any role.",
                     "Keys stay in ~/.config/nimlab, never in the project folder."]
                    + ([] if eps else ["None yet."]), items)
        self.menu("Custom endpoints", build)

    def add_endpoint(self):
        from . import endpoints as EP
        try:
            name = self.ask("Name (like: my-gateway): ")
            url = self.ask("Base URL (like: https://example.com or https://example.com/v1): ")
            if not name or not url:
                raise Back()
            key = self.secret("API key (Enter if it needs none): ")
            e = EP.add(name, url, key)
        except Back:
            self.say("Not added.")
            return None
        except ValueError as ex:
            self.say(f"[x] {ex}")
            return None
        self.say(f"[ok] Added {e['name']}: {e['base_url']}")
        return [("i", "Import its models now (from /models)", lambda: self.import_models(e["name"])),
                ("m", "Add a model by hand", lambda: self.add_model(e["name"]))]

    def endpoint(self, name):
        from . import endpoints as EP

        def build():
            e = EP.get(name)
            if not e:
                raise Back()
            head = [f"{e['base_url']}   key: {'set' if EP.key_for(name) else 'none'}"]
            for m in e.get("models", []):
                head.append(f"  {m['id']}  ({m['kind']}{', ' + m['path'] if m.get('path') else ''})")
            if not e.get("models"):
                head.append("  no models yet")
            return head, [
                ("1", "Import models (from /models)", lambda: self.import_models(name)),
                ("2", "Add a model by hand", lambda: self.add_model(name)),
                ("3", "Put a model on a role", lambda: self.use_on_role(name)),
                ("4", "Change a model's kind", lambda: self.change_kind(name)),
                ("5", "Remove a model", lambda: self.drop_model(name)),
                ("6", "Set or change the API key", lambda: self.set_key(name)),
                ("7", "Change the URL", lambda: self.set_url(name)),
                ("8", "Remove this endpoint", lambda: self.drop_endpoint(name)),
            ]
        self.menu(f"Endpoint: {name}", build)

    def import_models(self, name):
        from . import endpoints as EP
        ok, res = EP.import_models(name)
        if not ok:
            self.say(f"[x] {res}")
            return [("k", "Set or change the API key", lambda: self.set_key(name)),
                    ("m", "Add a model by hand", lambda: self.add_model(name))]
        self.say(f"[ok] {len(res)} new model(s)" + (": " + ", ".join(res) if res else " (all were there)"))
        self.say("Kinds are guessed from the names; change one with 'Change a model's kind'.")
        return [("r", "Put a model on a role", lambda: self.use_on_role(name))]

    def choose_kind(self, default="chat"):
        from . import endpoints as EP
        got = {}
        self.say("What kind of model is it?")
        try:
            self.pick([(str(i), k + (" (default)" if k == default else ""), lambda k=k: got.update(k=k))
                       for i, k in enumerate(EP.KINDS, 1)], f"Choose (Enter = {default}): ")
        except Back:
            pass
        return got.get("k", default)

    def add_model(self, name):
        from . import endpoints as EP
        try:
            mid = self.ask("Model id (exactly as the gateway expects it): ")
            if not mid:
                raise Back()
            kind = self.choose_kind(EP.guess_kind(mid))
            path = self.ask(f"Request path (Enter for {EP.PATHS[kind]}): ")
            m = EP.add_model(name, mid, kind, path or None)
        except Back:
            self.say("Not added.")
            return None
        except (ValueError, KeyError) as ex:
            self.say(f"[x] {ex}")
            return None
        self.say(f"[ok] {m['id']} ({m['kind']}) added.")
        return [("r", "Put it on a role", lambda: self.use_on_role(name, m["id"]))]

    def pick_model(self, name, prompt="Which model? "):
        from . import endpoints as EP
        ms = (EP.get(name) or {}).get("models", [])
        if not ms:
            self.say("No models yet.")
            raise Back()
        got = {}
        self.pick([(str(i), f"{m['id']} ({m['kind']})", lambda m=m: got.update(m=m)) for i, m in enumerate(ms, 1)],
                  prompt)
        if "m" not in got:
            raise Back()
        return got["m"]

    def change_kind(self, name):
        from . import endpoints as EP
        try:
            m = self.pick_model(name)
            kind = self.choose_kind(m["kind"])
        except Back:
            return None
        EP.add_model(name, m["id"], kind, m.get("path"), source=m.get("source", "manual"))
        self.say(f"[ok] {m['id']} is now {kind}.")
        return None

    def drop_model(self, name):
        from . import endpoints as EP
        try:
            m = self.pick_model(name)
        except Back:
            return None
        EP.remove_model(name, m["id"])
        self.say(f"[ok] Removed {m['id']}.")
        return None

    def set_key(self, name):
        from . import endpoints as EP
        try:
            key = self.secret("API key (Enter to remove it): ")
        except Back:
            return None
        EP.set_key(name, key)
        self.say("[ok] Key saved." if key else "[ok] Key removed.")
        return None

    def set_url(self, name):
        from . import endpoints as EP
        try:
            url = self.ask("New base URL: ")
            if not url:
                raise Back()
            e = EP.set_url(name, url)
        except Back:
            return None
        except ValueError as ex:
            self.say(f"[x] {ex}")
            return None
        self.say(f"[ok] {e['base_url']}")
        return None

    def drop_endpoint(self, name):
        from . import endpoints as EP
        if self.yes(f"Remove {name} and its key? Roles that use its models go back to NVIDIA routing."):
            EP.remove(name)
            self.say(f"[ok] Removed {name}.")
            raise Back()
        return None

    def use_on_role(self, name, model_id=None):
        from . import config, endpoints as EP, roles as R
        try:
            m = None
            if model_id:
                m = next((x for x in (EP.get(name) or {}).get("models", []) if x["id"] == model_id), None)
            m = m or self.pick_model(name)
            want = {"vision": ("vision", "chat")}.get(m["kind"], (m["kind"],))
            fits = [d for d in R.ROLE_DEFS if set(d.kinds) & set(want)]
            if not fits:
                self.say(f"No role takes a {m['kind']} model.")
                return None
            got = {}
            self.pick([(str(i), f"{d.key}: {d.name}", lambda d=d: got.update(d=d)) for i, d in enumerate(fits, 1)],
                      "Which role? ")
            d = got.get("d")
            if not d:
                return None
        except Back:
            return None
        cfg = config.load_json(config.CLUSTER_CONFIG, {}) or {}
        roles = cfg.setdefault("roles", {})
        R.set_model(roles, d.key, f"{name}:{m['id']}", endpoint=EP.model_url(EP.get(name), m))
        config.save_json(config.CLUSTER_CONFIG, cfg)
        self.say(f"[ok] {d.key} now uses {m['id']} on {name}. The running server picks it up on its next restart.")
        return [("s", "Restart the service now", lambda: (self.cli("service", "restart"), None)[1])]


def cmd_ui(args):
    ui = UI()
    screen = getattr(args, "screen", "health")
    try:
        {"health": ui.health, "scheduler": ui.scheduler, "service": ui.service,
         "endpoints": ui.endpoints}[screen]()
    except Back:
        pass
    return 0


def add_parser(sub):
    p = sub.add_parser("ui", help="Open a menu: health, scheduler, service or endpoints")
    p.add_argument("screen", nargs="?", default="health", choices=["health", "scheduler", "service", "endpoints"])
    p.set_defaults(fn=cmd_ui)
    return p
