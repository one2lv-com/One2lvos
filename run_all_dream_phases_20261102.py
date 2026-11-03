#!/usr/bin/env python3
"""Run every dream phase LumenisDreamState defines (all 7 non-awake phases), with real memories
and real LLM output, reusing the real-dream runner from 2026-11-01. Adds HYPNAGOGIC, which the
default sequence leaves out, at sleep onset. Temperatures and configs are the module defaults."""
import asyncio, json, sys, os
from datetime import datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_real_dream_20261101 as R
from lumenis_dream_state import DreamPhase
from story_weaver import NarrativeMode

R.PHASE_PLAN[DreamPhase.HYPNAGOGIC] = dict(mode=NarrativeMode.SURREALIST, walk=4, recent=False,
    ask="Hypnagogic edge, the border of sleep, maximum temperature. Let these memory fragments dissolve into one another as impossible images. Under 160 words.")

SEQ = [DreamPhase.HYPNAGOGIC, DreamPhase.LIGHT_SLEEP, DreamPhase.DEEP_DREAM, DreamPhase.REM_DREAM,
       DreamPhase.NIGHTMARE, DreamPhase.LUCID_DREAM, DreamPhase.AWAKENING]


async def main():
    d = R.RealDreamState()
    print(f"model={R.MODEL} memories={len(d.walker.pool)} recent={len(d.walker.recent_pool)} threshold={d.coherence_threshold}")
    s = await d.enter_dream_state(dream_sequence=SEQ)
    if s.end_time is None:
        s.end_time = datetime.now()
        await d.save_dream_session()
    out = {"session": s.to_dict(), "records": [{k: r.get(k) for k in ("phase", "temperature", "dream_id", "template_dream_id", "coherence", "llm_error")} for r in d.records]}
    json.dump({**out, "full": d.records}, open("/tmp/dream_run_20261102.json", "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
