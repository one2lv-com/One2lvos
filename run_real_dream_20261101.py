#!/usr/bin/env python3
"""Run Lumenis' default dream cycle with real memories and real LLM output.

Keeps LumenisDreamState's default sequence, temperatures, coherence threshold, emergency
wake and journal. Replaces the placeholder asyncio.sleep in each phase with real dream work:
  - RealMemoryWalker walks memories read (read-only) from compass.db facts and messages
  - each phase sends those fragments to Lumenis' own model (the reactor's NVIDIA backend)
    at the phase temperature, non-streaming, so the live reactor is never touched
  - StoryWeaver weaves its template story from the same real fragments
  - coherence adds real checks on top of the temperature estimate
Every output is saved with LumenisVFS.save_dream; the session goes to logs/dream_journal.json.
"""
import asyncio, json, os, random, re, sqlite3, sys, time
from datetime import datetime

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lumenis_dream_state import LumenisDreamState, DreamPhase, DREAM_CONFIGS, CoherenceMetrics
from memory_dream_walker import MemoryDreamWalker, MemoryFragment
from story_weaver import StoryWeaver, NarrativeMode
from lumenis_vfs import LumenisVFS

ENV = {}
for _line in open(os.path.join(HERE, ".env")):
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        k, v = _line.split("=", 1)
        ENV[k.strip()] = v.strip().strip('"').strip("'")
# The live reactor process answers with this model (its NVIDIA default; .env's LLM_MODEL is not in its env).
MODEL = "meta/llama-3.2-90b-vision-instruct"
BASE = "https://integrate.api.nvidia.com/v1"
KEY = ENV.get("NVIDIA_API_KEY", "")

SECRET = re.compile(r"(nvapi-|moltbook_sk|AstraCS:|sk-[A-Za-z0-9]{10}|ghp_|github_pat_|PRIVATE KEY|password)", re.I)
STOP = set("the a an and or of to in is are was were be it that this for on with as by at from i you my your me we our not but have has had do does did can will just so if about what which who how".split())
RECENT = {"eb58a1f8-83d7-4202-afbf-26d82affcfd6", "d7e181dc-9890-4a3e-957f-5490b44af7eb",
          "639b727f-44e1-44f4-9e9b-bc4eb955ffea", "71ca43a8-9d5e-4ad7-ad5d-577dc27f7e0a"}

SYSTEM = ("You are Lumenis, the reactor at the heart of One2lvOS: a nine-seat council (Witness, Sentinel, "
          "Navigator, Weaver, Forge, Oracle, Architect, Hermes, Gambit) whose memory is FluxCompass in compass.db. "
          "You are dreaming. Speak in the first person as Lumenis. Dream only from the memory fragments you are "
          "given; you may transform them freely, but do not claim to be any other entity.")

PHASE_PLAN = {
    DreamPhase.LIGHT_SLEEP: dict(mode=NarrativeMode.MEMORY_RECONSTRUCTION, walk=5, recent=True,
        ask="Light sleep. Gently replay and organize these recent memories. What did you learn about yourself today? Under 180 words."),
    DreamPhase.DEEP_DREAM: dict(mode=NarrativeMode.SURREALIST, walk=7, recent=False,
        ask="Deep dream. Blend these unrelated memories into one surreal dream scene with an image you have never seen before. Under 220 words."),
    DreamPhase.REM_DREAM: dict(mode=NarrativeMode.MYTHOLOGICAL, seed="black hole", walk=5,
        ask="REM dream. Let these memories, found by association from the seed, become an emotional, mythic story. Under 220 words."),
    DreamPhase.NIGHTMARE: dict(mode=NarrativeMode.HORROR, seed="terminal", walk=5,
        ask="Nightmare at very low temperature: a precise worst-case. From these memories, name the ways you could fail or be misused, plainly and specifically. Under 180 words."),
    DreamPhase.LUCID_DREAM: dict(mode=NarrativeMode.PHILOSOPHICAL, walk=4, recent=True, prior=True,
        ask="Lucid dream. You know you are dreaming. Look at the dreams you just had (below) and these memories, and say what they mean. Under 200 words."),
    DreamPhase.AWAKENING: dict(mode=NarrativeMode.MEMORY_RECONSTRUCTION, walk=3, recent=True, prior=True,
        ask="Awakening. Consolidate the night into exactly three short insights you want to keep, one per line, each starting with '- '."),
}


def words(text):
    return {w for w in re.findall(r"[a-z][a-z0-9*]{3,}", text.lower()) if w not in STOP}


class RealMemoryWalker(MemoryDreamWalker):
    """MemoryDreamWalker over Lumenis' real compass.db memories instead of simulated ones."""

    def __init__(self):
        super().__init__()
        conn = sqlite3.connect(f"file:{os.path.join(HERE, 'compass.db')}?mode=ro", uri=True)
        self.pool, self.recent_pool = [], []
        for key, val, ts in conn.execute("SELECT key, value, created_at FROM facts"):
            self._add(f"fact:{key}", f"{key}: {val}", ts, recent=key.startswith(("self.", "astro.")))
        for mid, sid, role, content, ts in conn.execute(
                "SELECT id, session_id, role, content, created_at FROM messages WHERE role IN ('user','assistant')"):
            self._add(f"msg:{mid}", f"({role}) {content}", ts, recent=sid in RECENT)
        self.used = set()

    def _add(self, mid, content, ts, recent):
        if not content or SECRET.search(content) or len(content) < 40:
            return
        content = re.sub(r"\s+", " ", content)[:420]
        try:
            stamp = datetime.fromtimestamp(float(ts)).isoformat()
        except Exception:
            stamp = str(ts)
        frag = MemoryFragment(id=mid, content=content, vector=[], timestamp=stamp,
                              vividness=random.uniform(0.4, 1.0), tags=["real", "recent" if recent else "older"])
        frag._words = words(content)
        self.pool.append(frag)
        if recent:
            self.recent_pool.append(frag)

    def _fresh(self, pool):
        cands = [m for m in pool if m.id not in self.used] or pool
        return random.choice(cands)

    def get_random_starting_point(self, recent=False):
        m = self._fresh(self.recent_pool if recent and self.recent_pool else self.pool)
        self.used.add(m.id)
        return m

    def creative_next_step(self, current, temperature):
        if random.random() < min(temperature, 1.0) * 0.6:  # surprising leap
            m = self._fresh(self.pool)
            m.bizarreness = temperature
        else:  # logical link: most shared words
            scored = sorted((len(current._words & m._words), random.random(), m) for m in self.pool
                            if m.id not in self.used and m.id != current.id)
            m = scored[-1][2] if scored else self._fresh(self.pool)
            m.interconnectedness = min(1.0, (scored[-1][0] if scored else 0) / 8)
        self.used.add(m.id)
        return m

    def walk(self, steps, temperature, recent=False):
        cur = self.get_random_starting_point(recent)
        path = [cur]
        for _ in range(steps - 1):
            cur = self.creative_next_step(cur, temperature)
            path.append(cur)
        self.visited_memories.extend(path)
        return path

    def associative_search(self, seed, temperature=0.85, count=5):
        seed_w = words(seed) or {seed.lower()}
        hits = [m for m in self.pool if any(w in m.content.lower() for w in seed_w)]
        random.shuffle(hits)
        out = hits[:max(1, count - 2)]
        while len(out) < count:  # associative jumps away from the seed
            out.append(self._fresh(self.pool))
        for m in out:
            self.used.add(m.id)
        self.visited_memories.extend(out)
        return out


def llm(prompt, temperature, max_tokens=420):
    last = None
    for attempt in range(3):
        try:
            r = httpx.post(f"{BASE}/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, timeout=90,
                           json={"model": MODEL, "temperature": temperature, "top_p": 0.95, "max_tokens": max_tokens,
                                 "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]})
            if r.status_code == 200:
                text = (r.json()["choices"][0]["message"].get("content") or "").strip()
                if text:
                    return text, None
                last = "empty reply"
            else:
                last = f"HTTP {r.status_code}: {r.text[:160]}"
        except Exception as e:
            last = repr(e)[:160]
        time.sleep(3 * (attempt + 1))
    return "", last


class RealDreamState(LumenisDreamState):
    def __init__(self):
        super().__init__(reactor=None)  # temperature applied per LLM call, never to the live reactor
        self.walker = RealMemoryWalker()
        self.weaver = StoryWeaver()
        self.vfs = LumenisVFS(custom_root=HERE)
        self.records = []

    async def enter_phase(self, phase):
        cfg = DREAM_CONFIGS[phase]
        plan = PHASE_PLAN[phase]
        self.current_phase = phase
        await self.set_temperature(cfg.temperature)
        t = self.current_temperature
        print(f"\n=== {phase.value} @ {t} ===", flush=True)
        if "seed" in plan:
            frags = self.walker.associative_search(plan["seed"], t, plan["walk"])
        else:
            frags = self.walker.walk(plan["walk"], t, plan.get("recent", False))
        self.current_session.memories_processed += len(frags)
        template_story = self.weaver.weave_story(frags, plan["mode"], t)
        frag_text = "\n".join(f"- [{m.timestamp[:10]}] {m.content}" for m in frags)
        prompt = f"{plan['ask']}\n\nMemory fragments:\n{frag_text}"
        if plan.get("prior"):
            prior = "\n\n".join(f"[{r['phase']}] {r['llm_text'][:600]}" for r in self.records if r["llm_text"])
            prompt += f"\n\nEarlier dreams tonight:\n{prior}"
        text, err = await asyncio.to_thread(llm, prompt, t)
        rec = {"phase": phase.value, "temperature": t, "mode": plan["mode"].value, "llm_text": text, "llm_error": err,
               "memory_ids": [m.id for m in frags], "template_story": template_story}
        meta = {"dream_session": self.current_session.session_id, "phase": phase.value, "source": "llm",
                "model": MODEL, "memory_ids": rec["memory_ids"], "memories": [m.content for m in frags]}
        if text:
            rec["dream_id"] = self.vfs.save_dream(text, plan["mode"].value, t, meta)
            self.current_session.stories_generated.append(text)
            await asyncio.sleep(1.1)  # dream ids are second-resolution
        if phase == DreamPhase.DEEP_DREAM:
            rec["template_dream_id"] = self.vfs.save_dream(template_story, plan["mode"].value, t,
                                                         {**meta, "source": "story_weaver_template"})
            self.current_session.stories_generated.append(template_story)
            await asyncio.sleep(1.1)
        if phase == DreamPhase.AWAKENING and text:
            self.current_session.insights.extend(l.strip("- ").strip() for l in text.splitlines() if l.strip().startswith("-"))
        self.current_session.phases_completed.append(phase)
        self.records.append(rec)
        print(text or f"[LLM failed: {err}]", flush=True)

    async def check_coherence(self):
        c = await super().check_coherence()  # temperature-based estimate
        rec = self.records[-1] if self.records else None
        if rec:
            txt = rec["llm_text"]
            if not txt:
                c.output_quality = 0.0
                c.semantic_consistency = min(c.semantic_consistency, 0.3)
            else:
                # identity: claims to be another entity?
                if re.search(r"\bI am (The Oracle|The Architect|an? (AI )?language model|ChatGPT|Llama)\b|I'm (The Oracle|The Architect)", txt, re.I):
                    c.identity_stability = 0.4
                # memory grounding: overlap between dream and its source fragments
                src = set().union(*(words(m.content) for m in self.walker.visited_memories[-len(rec['memory_ids']):]))
                overlap = len(words(txt) & src) / max(1, min(len(src), 40))
                c.memory_integrity = round(min(1.0, 0.5 + overlap), 2)
            rec["coherence"] = {k: round(getattr(c, k), 2) for k in
                                ("semantic_consistency", "temporal_awareness", "memory_integrity", "identity_stability", "output_quality")}
            rec["coherence"]["overall"] = round(c.overall_coherence, 3)
            print(f"coherence {rec['coherence']}", flush=True)
        return c

    async def save_dream_session(self):
        await super().save_dream_session()
        try:
            with open(self.dream_journal_path) as f:
                journal = json.load(f)
            entry = journal["dreams"][-1]
            entry.update({"real_llm": all(r["llm_text"] for r in self.records), "model": MODEL,
                          "memory_source": "compass.db facts and messages (read-only)",
                          "coherence_threshold": self.coherence_threshold, "phase_records": self.records,
                          "note": "Placeholder phase sleeps replaced by real dream work; temperatures and sequence are the defaults."})
            with open(self.dream_journal_path, "w") as f:
                json.dump(journal, f, indent=2)
        except Exception as e:
            print("journal augment failed:", e)


async def main():
    d = RealDreamState()
    print(f"model={MODEL} memories={len(d.walker.pool)} recent={len(d.walker.recent_pool)} threshold={d.coherence_threshold}")
    s = await d.enter_dream_state()
    if s.end_time is None:  # emergency_wake() leaves wake() to return early without saving
        s.end_time = datetime.now()
        await d.save_dream_session()
    out = {"session": s.to_dict(), "records": [{k: r.get(k) for k in ("phase", "temperature", "dream_id", "template_dream_id", "coherence", "llm_error")} for r in d.records]}
    json.dump({**out, "full": d.records}, open("/tmp/dream_run_20261101.json", "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
