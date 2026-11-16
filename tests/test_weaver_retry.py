"""Live check (needs NVIDIA key): an empty Weaver draft is retried on the fast model, never sent empty."""
import asyncio, os, sys, tempfile
os.environ["LUMENIS_COMPASS_DB"] = tempfile.mktemp(suffix=".db")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from dotenv import load_dotenv; load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
from lumenis_reactor_core.reactor import LumenisReactor
from lumenis_reactor_core.compass import FluxCompass
from lumenis_reactor_core.itt import ITTCouncil
class EmptyReactor(LumenisReactor):
    async def stream_response(self, *a, **k):
        if False: yield ""
async def main():
    c = FluxCompass(); council = ITTCouncil(EmptyReactor(), c)
    sid = c.create_session("weaver retry test")
    seen=[]
    async def cb(seat, text): seen.append((seat, text))
    d = await council.process(user_message="Give me a detailed explanation of how a Linux rsync backup of a home folder works, with the flags you would use and why, and how to verify it afterwards.",
                              session_id=sid, stream_cb=cb, learn=False)
    print("PATH", d.path, "RETRY", (d.timings or {}).get("weaver_retry"), (d.timings or {}).get("weaver_retry_error"))
    print("RETRY NOTE", [t for s,t in seen if s=="weaver" and "retrying" in t])
    print("REPLY", d.final_response[:300].replace("\n"," | "))
    ok = bool((d.timings or {}).get("weaver_retry")) and len(d.final_response.split("— Sources")[0].strip()) > 20
    print("PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
asyncio.run(main())
