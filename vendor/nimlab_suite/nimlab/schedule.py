"""Job schedules for the Nim Lab scheduler (v3.8.0).

Three ways to say when a job runs, modeled on Oracle DBMS_SCHEDULER:

  calendar   Oracle calendaring syntax, for example
                 FREQ=MINUTELY;INTERVAL=30
                 FREQ=DAILY;BYHOUR=7;BYMINUTE=30
                 FREQ=WEEKLY;BYDAY=MON,WED,FRI;BYHOUR=9
                 FREQ=MONTHLY;BYMONTHDAY=1,-1;BYHOUR=6
                 FREQ=MONTHLY;BYDAY=1MON;BYHOUR=8       (first Monday)
                 FREQ=YEARLY;BYMONTH=JAN;BYMONTHDAY=1
             Keys: FREQ (YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY),
             INTERVAL, BYMONTH, BYMONTHDAY, BYDAY, BYHOUR, BYMINUTE,
             BYSECOND (0 only: the scheduler works to the minute).
  cron       five fields: minute hour day-of-month month day-of-week, with
             *, lists, ranges, steps and names ("*/15 * * * *",
             "0 7 * * MON-FRI"), or @hourly @daily @weekly @monthly @yearly.
  once       one run at a local time: "at 2026-11-14 07:00" (also
             "once 2026-11-14T07:00" or a bare ISO date-time).

Times are local wall-clock times: the system's time zone, or the
scheduler_settings.timezone name when one is set. Like Oracle, a field the
calendar string leaves out comes from the job's start date (the anchor):
FREQ=DAILY with no BYHOUR runs at the start time's hour and minute, and
INTERVAL counts periods from the start date. One Nim Lab difference: BYHOUR
without BYMINUTE runs on the hour (Oracle would keep the start minute).

next_run(spec, after, anchor) -> the first run strictly after `after`, or
None when there is none (a one-off already past, or nothing matches within
five years). It works on epoch seconds so it is DST-safe; calendar maths
runs on local wall-clock times.
"""

import calendar as _cal
import re
import time
from datetime import datetime, timedelta

FREQS = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY", "HOURLY", "MINUTELY")
DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
CAL_KEYS = ("FREQ", "INTERVAL", "BYMONTH", "BYMONTHDAY", "BYDAY", "BYHOUR", "BYMINUTE", "BYSECOND")
HORIZON_DAYS = 5 * 366
MAX_STEPS = 200_000
CRON_MACROS = {"@hourly": "0 * * * *", "@daily": "0 0 * * *", "@midnight": "0 0 * * *",
               "@weekly": "0 0 * * 0", "@monthly": "0 0 1 * *", "@yearly": "0 0 1 1 *",
               "@annually": "0 0 1 1 *"}

_tz = None          # a zoneinfo.ZoneInfo when scheduler_settings.timezone names one


class ScheduleError(ValueError):
    """A schedule string that cannot be read; the message says why."""


# ---------------------------------------------------------------------------
# local time <-> epoch
# ---------------------------------------------------------------------------
def set_timezone(name):
    """Use an IANA zone (e.g. 'America/Los_Angeles') instead of the system
    zone. '' or None goes back to the system zone. -> the zone name in use,
    or raises ScheduleError when the zone is unknown."""
    global _tz
    if not name:
        _tz = None
        return "local"
    try:
        from zoneinfo import ZoneInfo
        _tz = ZoneInfo(str(name))
    except Exception as e:  # noqa: BLE001 - no tzdata on the box, or a typo
        _tz = None
        raise ScheduleError(f"unknown time zone {name!r} ({type(e).__name__}); using the system zone") from e
    return str(name)


def timezone_name():
    if _tz is not None:
        return str(_tz)
    return time.strftime("%Z") or "local"


def to_local(ts):
    """epoch -> naive local datetime (seconds dropped)."""
    if _tz is not None:
        d = datetime.fromtimestamp(ts, _tz).replace(tzinfo=None)
    else:
        d = datetime.fromtimestamp(ts)
    return d.replace(second=0, microsecond=0)


def to_epoch(d):
    """naive local datetime -> epoch. A wall-clock time that does not exist
    (the hour skipped when clocks go forward) lands just after the gap."""
    if _tz is not None:
        return d.replace(tzinfo=_tz).timestamp()
    return time.mktime(d.timetuple())


def parse_local(text):
    """'2026-11-14 07:00', '2026-11-14T07:00[:ss]', '2026-11-14' -> epoch.
    An ISO string with an offset is honoured as given."""
    t = str(text or "").strip()
    if not t:
        raise ScheduleError("empty date")
    t2 = t.replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(t2.replace(" ", "T", 1) if re.match(r"^\d{4}-\d\d-\d\d \d", t2) else t2)
    except ValueError as e:
        raise ScheduleError(f"can't read the date {t!r}; use YYYY-MM-DD HH:MM") from e
    if d.tzinfo is not None:
        return d.timestamp()
    return to_epoch(d.replace(second=0, microsecond=0))


def fmt(ts, with_zone=False):
    if ts is None:
        return "-"
    s = to_local(ts).strftime("%Y-%m-%d %H:%M")
    return f"{s} {timezone_name()}" if with_zone else s


def ago(ts, now=None):
    """'in 12 min' / '3 h ago' for a menu line."""
    if ts is None:
        return "-"
    now = time.time() if now is None else now
    d = ts - now
    n = abs(d)
    if n < 90:
        s = f"{int(n)} s"
    elif n < 5400:
        s = f"{int(round(n / 60))} min"
    elif n < 2 * 86400:
        s = f"{n / 3600:.1f} h"
    else:
        s = f"{int(n // 86400)} days"
    return f"in {s}" if d >= 0 else f"{s} ago"


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------
def _ints(val, lo, hi, key, names=None, allow_neg=False):
    out = []
    for part in str(val).split(","):
        p = part.strip().upper()
        if not p:
            continue
        if names and p in names:
            out.append(names.index(p) + lo)
            continue
        try:
            n = int(p)
        except ValueError:
            raise ScheduleError(f"{key}={val}: {part.strip()!r} is not a number") from None
        if allow_neg and -hi <= n <= -1:
            out.append(n)
        elif lo <= n <= hi:
            out.append(n)
        else:
            raise ScheduleError(f"{key}={val}: {n} is out of range {lo}..{hi}")
    if not out:
        raise ScheduleError(f"{key} is empty")
    return sorted(set(out))


def _bydays(val):
    """BYDAY=MON,1MON,-1FRI -> [(weekday 0-6, ordinal or 0)]."""
    out = []
    for part in str(val).split(","):
        p = part.strip().upper()
        if not p:
            continue
        m = re.fullmatch(r"([+-]?\d{1,2})?\s*([A-Z]{3})[A-Z]*", p)
        if not m or m.group(2) not in DAYS:
            raise ScheduleError(f"BYDAY={val}: {part.strip()!r} is not a day (MON..SUN, or 1MON / -1FRI)")
        n = int(m.group(1) or 0)
        if abs(n) > 53:
            raise ScheduleError(f"BYDAY={val}: ordinal {n} is out of range")
        out.append((DAYS.index(m.group(2)), n))
    if not out:
        raise ScheduleError("BYDAY is empty")
    return out


def parse_calendar(text):
    rule = {}
    for chunk in str(text).strip().rstrip(";").split(";"):
        if not chunk.strip():
            continue
        if "=" not in chunk:
            raise ScheduleError(f"{chunk.strip()!r}: expected KEY=VALUE (e.g. FREQ=DAILY;BYHOUR=7)")
        k, v = (x.strip() for x in chunk.split("=", 1))
        k = k.upper()
        if k not in CAL_KEYS:
            raise ScheduleError(f"{k} is not supported; use {', '.join(CAL_KEYS)}")
        if k in rule:
            raise ScheduleError(f"{k} is given twice")
        rule[k] = v
    freq = rule.get("FREQ", "").upper()
    if freq not in FREQS:
        raise ScheduleError(f"FREQ must be one of {', '.join(FREQS)}" + (f" (got {freq})" if freq else ""))
    out = {"kind": "calendar", "freq": freq, "interval": 1}
    if "INTERVAL" in rule:
        try:
            iv = int(rule["INTERVAL"])
        except ValueError:
            raise ScheduleError("INTERVAL must be a whole number") from None
        if not 1 <= iv <= 999:
            raise ScheduleError("INTERVAL must be between 1 and 999")
        out["interval"] = iv
    if "BYMONTH" in rule:
        out["bymonth"] = _ints(rule["BYMONTH"], 1, 12, "BYMONTH", MONTHS)
    if "BYMONTHDAY" in rule:
        md = _ints(rule["BYMONTHDAY"], 1, 31, "BYMONTHDAY", allow_neg=True)
        out["bymonthday"] = md
    if "BYDAY" in rule:
        out["byday"] = _bydays(rule["BYDAY"])
    if "BYHOUR" in rule:
        out["byhour"] = _ints(rule["BYHOUR"], 0, 23, "BYHOUR")
    if "BYMINUTE" in rule:
        out["byminute"] = _ints(rule["BYMINUTE"], 0, 59, "BYMINUTE")
    if "BYSECOND" in rule:
        if _ints(rule["BYSECOND"], 0, 59, "BYSECOND") != [0]:
            raise ScheduleError("BYSECOND: the scheduler works to the minute; use BYSECOND=0 or leave it out")
    if freq in ("MINUTELY", "HOURLY", "DAILY") and any(n for _, n in out.get("byday", [])):
        raise ScheduleError("BYDAY ordinals like 1MON only work with FREQ=MONTHLY or YEARLY")
    return out


def _cron_field(text, lo, hi, names=None, key=""):
    vals = set()
    for part in text.split(","):
        p = part.strip().upper()
        if not p:
            raise ScheduleError(f"cron {key}: empty item")
        step = 1
        if "/" in p:
            p, s = p.split("/", 1)
            try:
                step = int(s)
            except ValueError:
                raise ScheduleError(f"cron {key}: step {s!r} is not a number") from None
            if step < 1:
                raise ScheduleError(f"cron {key}: step must be 1 or more")

        def num(x):
            if names and x in names:
                return names.index(x) + (lo if key != "day-of-week" else 0)
            try:
                return int(x)
            except ValueError:
                raise ScheduleError(f"cron {key}: {x!r} is not a number or name") from None
        if p in ("*", "?"):
            a, b = lo, hi
        elif "-" in p:
            a, b = (num(x) for x in p.split("-", 1))
        else:
            a = num(p)
            b = hi if "/" in part else a
        if key == "day-of-week":
            a, b = (7 if a == 7 and b != 7 else a), b
        if not (lo <= a <= hi and lo <= b <= hi) or a > b:
            raise ScheduleError(f"cron {key}: {part.strip()} is out of range {lo}..{hi}")
        vals.update(range(a, b + 1, step))
    if key == "day-of-week" and 7 in vals:
        vals.discard(7)
        vals.add(0)
    return sorted(vals)


CRON_DAYS = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")


def parse_cron(text):
    t = str(text).strip()
    t = CRON_MACROS.get(t.lower(), t)
    f = t.split()
    if len(f) != 5:
        raise ScheduleError(f"cron needs 5 fields (minute hour day month weekday), got {len(f)}")
    return {"kind": "cron",
            "minute": _cron_field(f[0], 0, 59, key="minute"),
            "hour": _cron_field(f[1], 0, 23, key="hour"),
            "dom": _cron_field(f[2], 1, 31, key="day-of-month"),
            "month": _cron_field(f[3], 1, 12, MONTHS, key="month"),
            "dow": _cron_field(f[4], 0, 7, CRON_DAYS, key="day-of-week"),
            "dom_any": f[2] in ("*", "?"), "dow_any": f[4] in ("*", "?")}


_ONCE = re.compile(r"^(?:at|once|run once at|on)\s*[:=]?\s*(.+)$", re.I)


def parse(text):
    """Any schedule string -> a dict with 'kind' (calendar, cron or once).
    Raises ScheduleError with a plain reason."""
    t = str(text or "").strip()
    if not t:
        raise ScheduleError("no schedule given; e.g. FREQ=MINUTELY;INTERVAL=30, '*/30 * * * *' or 'at 2026-11-14 07:00'")
    if t.upper().startswith("FREQ=") or ";FREQ=" in t.upper() or t.upper().startswith(("INTERVAL=", "BY")):
        return parse_calendar(t)
    m = _ONCE.match(t)
    if m:
        return {"kind": "once", "at": parse_local(m.group(1))}
    if re.match(r"^\d{4}-\d\d-\d\d([ T]\d\d:\d\d(:\d\d)?)?([+-]\d\d:\d\d|Z)?$", t):
        return {"kind": "once", "at": parse_local(t)}
    if t.startswith("@") or len(t.split()) == 5:
        return parse_cron(t)
    raise ScheduleError(f"can't read the schedule {t!r}. Use an Oracle calendar string (FREQ=DAILY;BYHOUR=7), "
                        "a 5-field cron ('0 7 * * *') or 'at YYYY-MM-DD HH:MM'")


def kind_of(text):
    try:
        return parse(text)["kind"]
    except ScheduleError:
        return "invalid"


def validate(text):
    """-> '' when the schedule is fine, else the reason."""
    try:
        parse(text)
        return ""
    except ScheduleError as e:
        return str(e)


# ---------------------------------------------------------------------------
# next run
# ---------------------------------------------------------------------------
def _month_days(y, m):
    return _cal.monthrange(y, m)[1]


def _add_months(y, m, n):
    i = (y * 12 + (m - 1)) + n
    return i // 12, i % 12 + 1


def _day_ok(r, d):
    """Day-level filters for frequencies finer than the BY field."""
    if "bymonth" in r and d.month not in r["bymonth"]:
        return False
    if "bymonthday" in r:
        n = _month_days(d.year, d.month)
        if not any((x if x > 0 else n + 1 + x) == d.day for x in r["bymonthday"]):
            return False
    if "byday" in r and d.weekday() not in {w for w, _ in r["byday"]}:
        return False
    return True


def _days_in_month(r, y, m, anchor, year_level=False):
    n = _month_days(y, m)
    days = None
    if "bymonthday" in r:
        days = {x if x > 0 else n + 1 + x for x in r["bymonthday"]}
        days = {x for x in days if 1 <= x <= n}
    if "byday" in r and not year_level:
        wd = set()
        for w, k in r["byday"]:
            hits = [dd for dd in range(1, n + 1) if datetime(y, m, dd).weekday() == w]
            if k == 0:
                wd.update(hits)
            elif 1 <= abs(k) <= len(hits):
                wd.add(hits[k - 1] if k > 0 else hits[k])
        days = wd if days is None else days & wd
    if days is None:
        days = {anchor.day} if anchor.day <= n else set()
    return sorted(days)


def _year_bydays(r, y):
    out = set()
    first = datetime(y, 1, 1)
    total = 366 if _cal.isleap(y) else 365
    for w, k in r["byday"]:
        hits = [first + timedelta(days=i) for i in range(total) if (first + timedelta(days=i)).weekday() == w]
        if k == 0:
            out.update(hits)
        elif 1 <= abs(k) <= len(hits):
            out.add(hits[k - 1] if k > 0 else hits[k])
    return out


def _period_days(r, freq, pstart, anchor):
    """Candidate days inside one period that starts at pstart."""
    if freq in ("MINUTELY", "HOURLY", "DAILY"):
        d = pstart.replace(hour=0, minute=0)
        return [d] if _day_ok(r, d) else []
    if freq == "WEEKLY":
        mon = pstart - timedelta(days=pstart.weekday())
        mon = mon.replace(hour=0, minute=0)
        wds = {w for w, _ in r["byday"]} if "byday" in r else {anchor.weekday()}
        out = []
        for i in range(7):
            d = mon + timedelta(days=i)
            if d.weekday() not in wds:
                continue
            if "bymonth" in r and d.month not in r["bymonth"]:
                continue
            if "bymonthday" in r and not _day_ok({"bymonthday": r["bymonthday"]}, d):
                continue
            out.append(d)
        return out
    if freq == "MONTHLY":
        y, m = pstart.year, pstart.month
        if "bymonth" in r and m not in r["bymonth"]:
            return []
        return [datetime(y, m, dd) for dd in _days_in_month(r, y, m, anchor)]
    # YEARLY
    y = pstart.year
    if "byday" in r and "bymonth" not in r and "bymonthday" not in r:
        return sorted(_year_bydays(r, y))
    months = r.get("bymonth") or [anchor.month]
    out = []
    for m in months:
        if "bymonthday" not in r and "byday" not in r:
            if anchor.day <= _month_days(y, m):
                out.append(datetime(y, m, anchor.day))
            continue
        out += [datetime(y, m, dd) for dd in _days_in_month(r, y, m, anchor)]
    return sorted(out)


def _day_times(r, freq, day, pstart, anchor):
    if freq == "MINUTELY":
        t = pstart
        if "byhour" in r and t.hour not in r["byhour"]:
            return []
        if "byminute" in r and t.minute not in r["byminute"]:
            return []
        return [t]
    if freq == "HOURLY":
        if "byhour" in r and pstart.hour not in r["byhour"]:
            return []
        mins = r.get("byminute") or [anchor.minute]
        return [pstart.replace(minute=mi) for mi in mins]
    hours = r.get("byhour") or [anchor.hour]
    if "byminute" in r:
        mins = r["byminute"]
    elif "byhour" in r:
        mins = [0]
    else:
        mins = [anchor.minute]
    return [day.replace(hour=h, minute=mi) for h in hours for mi in mins]


def _period_start(freq, anchor, k):
    if freq == "MINUTELY":
        return anchor + timedelta(minutes=k)
    if freq == "HOURLY":
        return anchor.replace(minute=0) + timedelta(hours=k)
    if freq == "DAILY":
        return anchor.replace(hour=0, minute=0) + timedelta(days=k)
    if freq == "WEEKLY":
        mon = anchor.replace(hour=0, minute=0) - timedelta(days=anchor.weekday())
        return mon + timedelta(weeks=k)
    if freq == "MONTHLY":
        y, m = _add_months(anchor.year, anchor.month, k)
        return datetime(y, m, 1)
    return datetime(anchor.year + k, 1, 1)


def _periods_between(freq, anchor, d):
    """Whole periods from the anchor's period to d's period (can be < 0)."""
    if freq == "MINUTELY":
        return int((d - anchor).total_seconds() // 60)
    if freq == "HOURLY":
        return int((d.replace(minute=0) - anchor.replace(minute=0)).total_seconds() // 3600)
    if freq == "DAILY":
        return (d.date() - anchor.date()).days
    if freq == "WEEKLY":
        a = anchor.date() - timedelta(days=anchor.weekday())
        b = d.date() - timedelta(days=d.weekday())
        return (b - a).days // 7
    if freq == "MONTHLY":
        return (d.year - anchor.year) * 12 + d.month - anchor.month
    return d.year - anchor.year


def _next_calendar(r, after_ts, anchor_ts):
    freq, iv = r["freq"], r["interval"]
    anchor = to_local(anchor_ts)
    after = to_local(after_ts)
    limit = after + timedelta(days=HORIZON_DAYS)
    k = max(0, _periods_between(freq, anchor, max(after, anchor)))
    k -= k % iv
    steps = 0
    while steps < MAX_STEPS:
        steps += 1
        ps = _period_start(freq, anchor, k)
        if ps > limit:
            return None
        best = None
        for day in _period_days(r, freq, ps, anchor):
            for t in _day_times(r, freq, day, ps, anchor):
                if freq == "MINUTELY" and (t.date() != day.date()):
                    continue
                if t < anchor:
                    continue
                ts = to_epoch(t)
                if ts > after_ts and (best is None or ts < best):
                    best = ts
        if best is not None:
            return best
        if freq in ("MINUTELY", "HOURLY") and not _day_ok(r, ps.replace(hour=0, minute=0)):
            # the whole day is filtered out: jump to the first period of the next day
            nxt = ps.replace(hour=0, minute=0) + timedelta(days=1)
            k2 = _periods_between(freq, anchor, nxt)
            k2 += (-k2) % iv
            k = max(k + iv, k2)
            continue
        k += iv
    return None


def _next_cron(c, after_ts):
    d = to_local(after_ts) + timedelta(minutes=1)
    limit = d + timedelta(days=HORIZON_DAYS)
    minutes, hours = set(c["minute"]), set(c["hour"])
    months, doms, dows = set(c["month"]), set(c["dom"]), set(c["dow"])

    def day_ok(x):
        if x.month not in months:
            return False
        cron_dow = (x.weekday() + 1) % 7
        dom_hit, dow_hit = x.day in doms, cron_dow in dows
        if c["dom_any"] and c["dow_any"]:
            return True
        if c["dom_any"]:
            return dow_hit
        if c["dow_any"]:
            return dom_hit
        return dom_hit or dow_hit           # classic cron: either restricted field matches
    steps = 0
    while d <= limit and steps < MAX_STEPS:
        steps += 1
        if not day_ok(d):
            d = d.replace(hour=0, minute=0) + timedelta(days=1)
            continue
        if d.hour not in hours:
            nh = [h for h in sorted(hours) if h > d.hour]
            if not nh:
                d = d.replace(hour=0, minute=0) + timedelta(days=1)
                continue
            d = d.replace(hour=nh[0], minute=0)
        nm = [mi for mi in sorted(minutes) if mi >= d.minute]
        if not nm:
            d = d.replace(minute=0) + timedelta(hours=1)
            continue
        d = d.replace(minute=nm[0])
        ts = to_epoch(d)
        if ts > after_ts:
            return ts
        d += timedelta(minutes=1)
    return None


def next_run(spec, after=None, anchor=None, start=None, end=None):
    """The first run strictly after `after` (epoch, default now), or None.

    spec: a schedule string or a parse() result. anchor: the job's start
    date / creation time (epoch) that INTERVAL counts from. start / end:
    the job's start_date and end_date (epoch or None)."""
    s = parse(spec) if isinstance(spec, str) else spec
    after = time.time() if after is None else float(after)
    if start is not None and after < start - 60:
        after = start - 60          # nothing before the start date (a start on the minute itself counts)
    if s["kind"] == "once":
        at = s["at"]
        nxt = at if at > after else None
    elif s["kind"] == "cron":
        nxt = _next_cron(s, after)
    else:
        anc = anchor if anchor is not None else (start if start is not None else after)
        nxt = _next_calendar(s, after, anc)
    if nxt is not None and end is not None and nxt > end:
        return None
    return nxt


def upcoming(spec, count=5, after=None, anchor=None, start=None, end=None):
    out, t = [], (time.time() if after is None else after)
    for _ in range(max(1, int(count))):
        t = next_run(spec, t, anchor, start, end)
        if t is None:
            break
        out.append(t)
    return out


def runs_between(spec, since, until, anchor=None, start=None, end=None, cap=1000):
    """How many scheduled times fall in (since, until] (for catch-up)."""
    n, t = 0, since
    while n < cap:
        t = next_run(spec, t, anchor, start, end)
        if t is None or t > until:
            break
        n += 1
    return n


def describe(text):
    """A short plain-English line for a schedule (menus, list output)."""
    try:
        s = parse(text)
    except ScheduleError as e:
        return f"invalid: {e}"
    if s["kind"] == "once":
        return f"once at {fmt(s['at'])}"
    if s["kind"] == "cron":
        return f"cron {text.strip()}"
    unit = {"MINUTELY": "minute", "HOURLY": "hour", "DAILY": "day", "WEEKLY": "week", "MONTHLY": "month",
            "YEARLY": "year"}[s["freq"]]
    base = f"every {unit}" if s["interval"] == 1 else f"every {s['interval']} {unit}s"
    bits = []
    if "byday" in s:
        bits.append("on " + ",".join((f"{n}" if n else "") + DAYS[w] for w, n in s["byday"]))
    if "bymonthday" in s:
        md = sorted(s["bymonthday"], key=lambda x: (x < 0, abs(x)))
        bits.append("day " + ",".join("last" if x == -1 else str(x) for x in md))
    if "bymonth" in s:
        bits.append("in " + ",".join(MONTHS[m - 1] for m in s["bymonth"]))
    if "byhour" in s and s["freq"] in ("MINUTELY", "HOURLY"):
        bits.append("during hour " + ",".join(f"{h:02d}" for h in s["byhour"]))
        if "byminute" in s:
            bits.append("at minute " + ",".join(str(x) for x in s["byminute"]))
    elif "byhour" in s:
        mins = s.get("byminute") or [0]
        bits.append("at " + ",".join(f"{h:02d}:{mi:02d}" for h in s["byhour"] for mi in mins))
    elif "byminute" in s:
        bits.append("at minute " + ",".join(str(x) for x in s["byminute"]))
    return " ".join([base] + bits)
