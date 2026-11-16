"""Council swarm: parsing, eligibility, parallel run, and the fallback when a seat returns no answer.
Run: python3 tests/test_council_swarm.py"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lumenis_reactor_core.swarm import council_swarm as sw  # noqa: E402

PASSED = FAILED = 0


def check(name, cond):
    global PASSED, FAILED
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        print("FAIL:", name)


MODELS = {"oracle": "nvidia/lightning", "forge": "nvidia/lightning", "weaver": "nvidia/super-vl", "architect": "nvidia/super-vl"}


async def notify(seat, text):
    pass


def make_call(replies, delay=0.2):
    calls = []

    async def call_seat(seat, task, extra, complexity):
        calls.append((seat, complexity))
        await asyncio.sleep(delay)
        r = replies.get(seat, "answer from " + seat)
        if isinstance(r, Exception):
            raise r
        return r
    return call_seat, calls


async def main():
    # parse_parts
    p = sw.parse_parts('{"parts":[{"task":"a","seat":"oracle"},{"task":"b","seat":"bogus"}]}')
    check("parse two parts", len(p) == 2 and p[1]["seat"] == "oracle")
    check("parse junk = no split", sw.parse_parts("not json") == [])
    check("guest cannot use architect", sw.parse_parts('{"parts":[{"task":"a","seat":"architect"}]}', guest=True)[0]["seat"] == "oracle")
    check("max 4 parts", len(sw.parse_parts('{"parts":[' + ",".join(['{"task":"x","seat":"forge"}'] * 6) + "]}")) == 4)
    # worth_trying
    check("short message skips swarm", not sw.worth_trying("hey lumenis how are you"))
    check("long multi-ask tries swarm", sw.worth_trying("Give me three things: a tip for Queen Nai, a poem about stars, and a backup checklist for Linux please"))

    parts = [{"task": "tip", "seat": "oracle"}, {"task": "poem", "seat": "weaver"}, {"task": "checklist", "seat": "forge"}]

    # parallel: three 0.2 s parts finish in well under 0.6 s
    call, calls = make_call({})
    t = time.monotonic()
    out = await sw.run(parts, "msg", call, MODELS.get, notify)
    el = time.monotonic() - t
    check("parts run in parallel", el < 0.45)
    check("all ok", all(r["ok"] for r in out["results"]))
    check("reasoning seats get the complex budget", all(c == "complex" for s, c in calls))
    check("attributed in order", out["text"].index("**Oracle**") < out["text"].index("**Weaver**") < out["text"].index("**Forge**"))

    # empty-answer marker from a reasoning seat -> handed to Weaver, marker never shown
    marker = "[Reasoning complete — no final answer emitted. Increase max_tokens.]"
    call, calls = make_call({"oracle": marker})
    out = await sw.run(parts, "msg", call, MODELS.get, notify)
    r1 = out["results"][0]
    check("marker part retried on weaver", r1["ok"] and r1["seat"] == "weaver" and r1["assigned_seat"] == "oracle")
    check("marker not in reply", "Reasoning complete" not in out["text"])
    check("fallback model recorded", r1["model"] == "nvidia/super-vl")

    # backend error text and exceptions are also retried
    call, _ = make_call({"forge": "[ReasoningReactor error: boom]"})
    out = await sw.run(parts, "msg", call, MODELS.get, notify)
    check("error text retried", out["results"][2]["ok"] and out["results"][2]["seat"] == "weaver")
    call, _ = make_call({"forge": RuntimeError("x")})
    out = await sw.run(parts, "msg", call, MODELS.get, notify)
    check("exception retried", out["results"][2]["ok"] and "[ReasoningReactor" not in out["text"])

    # fallback also fails -> plain note, no raw marker
    call, _ = make_call({"oracle": marker, "weaver": ""})
    out = await sw.run([{"task": "tip", "seat": "oracle"}], "msg", call, MODELS.get, notify)
    check("double failure gives plain note", not out["results"][0]["ok"] and "returned no answer" in out["text"]
          and "Reasoning complete" not in out["text"])

    # timeout: no retry (would only add more wait)
    old = sw.PART_TIMEOUT_S
    sw.PART_TIMEOUT_S = 0.1
    call, calls = make_call({}, delay=0.5)
    out = await sw.run([{"task": "tip", "seat": "oracle"}], "msg", call, MODELS.get, notify)
    sw.PART_TIMEOUT_S = old
    check("timeout reported, not retried", not out["results"][0]["ok"] and len(calls) == 1)

    check("LUMENIS_SWARM=0 disables", (os.environ.__setitem__("LUMENIS_SWARM", "0") or not sw.enabled()))
    os.environ.pop("LUMENIS_SWARM", None)
    check("enabled by default", sw.enabled())


asyncio.run(main())
print(f"{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
