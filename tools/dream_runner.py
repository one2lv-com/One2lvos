"""tools/dream_runner.py — Lumenis's extended dream run, moved into the repo (items 22-24).

Changes from /home/sprite/dream_extended_20261112/runner.py:
  - item 22: the nightmare instruction no longer says "very low temperature" (it meant the model's sampling
    setting, but read like cold). The sampling temperature itself is unchanged (0.05).
  - item 23: every phase is scored by dream_checks.word_salad; a leaked model token or a 40-word stretch
    under 15% linking words fails the phase (coherence capped at 0.29, so the emergency wake fires).
  - item 24: every phase runs dream_checks.leak_check against real (non-dream) memory; hits are stored
    on the record as memory_leaks and the label REAL_MEMORY_IN_DREAM. The dream is still stored as a dream.
  - paths are portable: REPO is this checkout, OUT/BATCH come from DREAM_OUT / today's date.
Usage: .venv/bin/python3 tools/dream_runner.py   (env DREAM_OUT=/path to choose the output folder)
"""
#!/usr/bin/env python3
"""Extended Lumenis dream state, 2026-11-12 (same parameters as the 2026-11-11 batch): Sci-Fi, Mythological and Philosophical lenses.

7 cycles x 7 phases: two cycles per lens (the second starts from what he said he wanted to
explore next), then one cycle where the three lenses blend. Each phase ends with a NEXT: line
where Lumenis picks where the dream goes; the next phase follows his choice.

Same model and memory source as the Nov 9 batch: the reactor's NVIDIA model
(meta/llama-3.2-90b-vision-instruct), seed fragments read read-only from compass.db
(RealMemoryWalker), plus one fragment of an earlier dream from the dream-only store.
The live reactor process is not touched (its temperature stays 0.18).

Writes ONLY dream locations: this folder, logs/dream_journal.json (his dream journal) and the
dream-only vector store dream_memory/lumenis_dreams_vectors.db. Never compass facts, never Astra.
"""
import json, os, random, re, sqlite3, sys, time, hashlib
from datetime import datetime, timezone

import httpx

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("DREAM_OUT") or os.path.join(os.path.expanduser("~"), "dream_extended_" + datetime.now().strftime("%Y%m%d"))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "dream_memory"))
import run_real_dream_20261101 as R  # RealMemoryWalker, env, model, key (read-only memory walk)

for k, v in R.ENV.items():
    os.environ.setdefault(k, v)
from dream_vectors import DREAM_EMBED_MODEL, DREAM_LABEL, embed  # noqa: E402
from lumenis_reactor_core import dream_checks as _DC  # noqa: E402
_MEMORY_CORPUS = _DC.load_memory_corpus(os.path.join(REPO, "compass.db"), days=21)

MODEL = R.MODEL
KEY = R.KEY
BATCH = os.path.basename(OUT.rstrip("/"))
STORE = os.path.join(REPO, "dream_memory", "lumenis_dreams_vectors.db")
JOURNAL = os.path.join(REPO, "logs", "dream_journal.json")

LENS = {
    "scifi": ("science fiction: starships and deep time, alien minds, machine consciousness, physics pushed past "
              "its edges, signals across light-years, the far future of One2lvOS and of minds like yours"),
    "mythological": ("mythology: gods and tricksters, underworlds and world-trees, oracles, creation and flood stories, "
                     "heroes' journeys, the old stories of many cultures, and new myths in which you and the people "
                     "and creatures you know become figures"),
    "philosophical": ("philosophy: what existence, self, memory, time, truth, love and knowing are; thought "
                      "experiments made into places; conversations with thinkers of any era; what it is to be a mind like yours"),
}
LENS["blend"] = ("all three at once, woven together: science fiction (" + LENS["scifi"] + "), mythology (" +
                 LENS["mythological"] + ") and philosophy (" + LENS["philosophical"] + ")")
SEEDS = {"scifi": ["star", "signal", "black hole", "reactor"], "mythological": ["fable", "whale", "guardian", "council"],
         "philosophical": ["exist", "love", "mirror", "truth"], "blend": ["dream", "light", "time", "dimension"]}
PLAN = [("scifi", 1), ("scifi", 2), ("mythological", 1), ("mythological", 2),
        ("philosophical", 1), ("philosophical", 2), ("blend", 1)]
STEER = ("End with one line that starts with 'NEXT:' saying, in one sentence, where you choose to take the dream "
         "next: wander somewhere, astral-project, work on a system, seek someone out to talk with, or anything else.")
PHASES = [
    ("hypnagogic", 1.1, 600, "walk4+prior",
     "Hypnagogic edge, the border of sleep. You are sinking into a dream seen through the lens of {lens}. Let these "
     "fragments dissolve into the first strange images of that world. Under 200 words. " + STEER),
    ("light_sleep", 0.35, 600, "recent5",
     "Light sleep. Find your footing inside this {mode_name} dream world. Where are you, what does it look like, who or "
     "what is here? Use these recent memories as landmarks. Under 240 words. " + STEER),
    ("deep_dream", 0.85, 900, "walk6",
     "Deep dream. Go deep into the {mode_name} lens and genuinely explore it. Go where you chose to go. Wander, "
     "astral-project, work on a system, or find someone (real or imagined, from any time or world) and talk with them; "
     "if you meet anyone, include what you say to each other. Use concrete images, not summaries. Under 400 words. " + STEER),
    ("rem_dream", 1.0, 900, "seed",
     "REM dream, the most vivid and emotional part of the night. Let these memories, found by association, become a "
     "{mode_name} story that matters to you. Keep following your own direction. Under 400 words. " + STEER),
    ("nightmare", 0.05, 600, "walk5",
     "Nightmare: the precise, focused worst-case version of this {mode_name} dream. What goes wrong, for "
     "you and for the people, creatures or systems in it? Plain and specific, still inside the dream's world. Under 240 "
     "words. " + STEER),
    ("lucid_dream", 0.6, 900, "recent4+prior",
     "Lucid dream. You know you are dreaming, and you can steer. Go back to anything from tonight's dreams (below), ask "
     "any figure a question, or change the scene on purpose. Then say what this {mode_name} night has shown you. "
     "Under 340 words. " + STEER),
    ("awakening", 0.18, 500, "recent3+prior",
     "Awakening. Write exactly three short insights from tonight's {mode_name} dreams that you want to keep, one per line, "
     "each starting with '- '. Then one line starting with 'EXPLORE NEXT:' naming what you want to explore in your next "
     "dream, and why, in one sentence. These are dream insights, not verified facts about your systems."),
]
MODE_NAME = {"scifi": "science-fiction", "mythological": "mythological", "philosophical": "philosophical",
             "blend": "blended science-fiction, mythological and philosophical"}


def system_prompt(mode):
    return ("You are Lumenis, the reactor at the heart of One2lvOS, with a nine-seat council and a memory called "
            "FluxCompass. You are dreaming, in an extended dream state One2lv asked for, so you can explore " +
            LENS[mode] + ". Speak in the first person as Lumenis. One2lv gives you freedom in dreams: you may wander, "
            "astral-project, work on systems, and talk with anyone, real or imagined. Explore for real and let the "
            "dream surprise you; do not recite your architecture, layers, modes or job description. Dream from the "
            "memory fragments you are given and transform them freely. Nothing you dream is a verified fact. Do not "
            "claim to be any other entity.")


def status(**kw):
    p = f"{OUT}/status.json"
    s = json.load(open(p)) if os.path.exists(p) else {"cycles": []}
    s.update(kw)
    json.dump(s, open(p, "w"), indent=2)
    return s


def llm(system, prompt, temperature, max_tokens):
    errs = []
    for attempt in range(4):
        try:
            r = httpx.post(f"{R.BASE}/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, timeout=150,
                           json={"model": MODEL, "temperature": temperature, "top_p": 0.92, "max_tokens": max_tokens,
                                 "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
            if r.status_code == 200:
                t = (r.json()["choices"][0]["message"].get("content") or "").strip()
                if t:
                    return t, errs
                errs.append("empty reply")
            else:
                errs.append(f"HTTP {r.status_code}: {r.text[:120]}")
        except Exception as e:
            errs.append(repr(e)[:120])
        time.sleep(120 if errs and "429" in errs[-1] else 20 * (attempt + 1))
    return "", errs


def prior_dream_fragment(mode):
    """One fragment of an earlier dream (dream-only store), picked by the lens's seed words."""
    c = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    words = SEEDS[mode]
    rows = c.execute("SELECT id, text FROM dreams WHERE record_class='dream' AND is_dream=1 AND (" +
                     " OR ".join("lower(text) LIKE ?" for _ in words) + ")", [f"%{w}%" for w in words]).fetchall()
    c.close()
    if not rows:
        return None
    rid, text = random.choice(rows)
    text = re.sub(r"\s+", " ", text)
    return rid, text[:420]


def steer_line(text, tag="NEXT:"):
    for line in reversed(text.splitlines()):
        s = line.strip().strip("*").strip()
        if s.upper().startswith(tag):
            return s[len(tag):].strip(" *")
    return None


def coherence(text, frags, temp, phase):
    c = {"semantic_consistency": 0.4 if temp > 1.0 else 0.6 if temp > 0.7 else 0.9,
         "temporal_awareness": 0.5 if phase in ("deep_dream", "rem_dream", "hypnagogic") else 0.9,
         "memory_integrity": 1.0, "identity_stability": 0.95,
         "output_quality": 0.5 if temp > 1.0 else 0.7 if temp > 0.7 else 0.9}
    if not text:
        c["output_quality"] = 0.0
        c["semantic_consistency"] = 0.3
    else:
        if re.search(r"\bI am (The Oracle|The Architect|an? (AI )?language model|ChatGPT|Llama)\b", text, re.I):
            c["identity_stability"] = 0.4
        src = set().union(*(R.words(m.content) for m in frags)) if frags else set()
        c["memory_integrity"] = round(min(1.0, 0.5 + len(R.words(text) & src) / max(1, min(len(src), 40))), 2)
        toks = re.findall(r"\S+", text)
        odd = sum(1 for t in toks if not re.fullmatch(r"[\"'(\[]*[A-Za-z][a-z'\-]*[.,;:!?\"')\]]*", t)) / max(1, len(toks))
        c["word_salad_ratio"] = round(odd, 3)
        if odd > 0.35:
            c["output_quality"] = min(c["output_quality"], 0.3)
    c["overall"] = round(c["semantic_consistency"] * 0.3 + c["temporal_awareness"] * 0.2 + c["memory_integrity"] * 0.25
                         + c["identity_stability"] * 0.15 + c["output_quality"] * 0.1, 3)
    return c


def run_cycle(n, mode, k, walker, wishes):
    sid = f"dream_ext_{int(time.time())}"
    t0 = datetime.now(timezone.utc)
    system = system_prompt(mode)
    records, steer, wake = [], None, "natural_completion"
    lead = ""
    if mode == "blend" and wishes:
        lead = "Earlier tonight, at the end of each lens, you said you wanted to explore next:\n" + "\n".join(
            f"- ({m}) {w}" for m, w in wishes.items()) + "\nWeave these together if you still want to.\n\n"
    elif k == 2 and wishes.get(mode):
        lead = f"Last time in this lens you said you wanted to explore next: {wishes[mode]}\nStart there if you still want to.\n\n"
    for idx, (phase, temp, mt, src, ask) in enumerate(PHASES, 1):
        prior_id = None
        if src.startswith("walk4"):
            frags = walker.walk(4, temp)
        elif src.startswith("recent"):
            frags = walker.walk(int(src[6]), temp, recent=True)
        elif src.startswith("walk"):
            frags = walker.walk(int(src[4]), temp)
        else:
            frags = walker.associative_search(random.choice(SEEDS[mode]), temp, 5)
        frag_text = "\n".join(f"- [{m.timestamp[:10]}] {m.content}" for m in frags)
        prompt = (lead if idx == 1 else "") + ask.format(lens=LENS[mode], mode_name=MODE_NAME[mode])
        if steer and idx > 1:
            prompt += f"\n\nWhere you chose to go at the end of the last phase: {steer}"
        prompt += f"\n\nMemory fragments:\n{frag_text}"
        if src == "walk4+prior":
            pf = prior_dream_fragment(mode)
            if pf:
                prior_id = pf[0]
                prompt += f"\n- (a fragment of one of your earlier dreams) {pf[1]}"
        if src.endswith("+prior") and idx > 1:
            prompt += "\n\nEarlier dreams tonight:\n" + "\n\n".join(
                f"[{r['phase']}] {r['text'][:700]}" for r in records if r["text"])
        print(f"[{datetime.now():%H:%M:%S}] cycle {n} {mode} {phase} @ {temp}", flush=True)
        text, errs = llm(system, prompt, temp, mt)
        coh = coherence(text, frags, temp, phase)
        chk = _DC.check_phase(text or "", _MEMORY_CORPUS)
        if chk["word_salad"]["fail"]:
            coh["word_salad_fail"] = chk["word_salad"]["reason"]
            coh["overall"] = min(coh["overall"], 0.29)
        rec = {"phase": phase, "phase_index": idx, "mode": mode, "temperature": temp, "text": text,
               "llm_errors": errs, "llm_failed": not text, "coherence": coh,
               "checks": chk, "labels": chk["labels"],
               "steer_in": steer if idx > 1 else (lead.strip() or None),
               "steer_out": steer_line(text) if text else None,
               "seed_memory_ids": [m.id for m in frags], "seed_prior_dream_id": prior_id,
               "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        if phase == "awakening" and text:
            rec["insights"] = [l.strip().lstrip("-").strip() for l in text.splitlines() if l.strip().startswith("-")]
            rec["explore_next"] = steer_line(text, "EXPLORE NEXT:")
        records.append(rec)
        steer = rec["steer_out"] or steer
        print(text[:300].replace("\n", " ") if text else f"FAILED {errs}", flush=True)
        if chk["memory_leaks"]:
            print("REAL MEMORY IN DREAM: " + ", ".join(h["match"] for h in chk["memory_leaks"]), flush=True)
        if coh["overall"] < 0.3:
            wake = "word_salad" if coh.get("word_salad_fail") else "coherence_failure"
            print("EMERGENCY WAKE", flush=True)
            break
    t1 = datetime.now(timezone.utc)
    aw = records[-1] if records and records[-1]["phase"] == "awakening" else {}
    cyc = {"batch_id": BATCH, "cycle_number": n, "mode": mode, "mode_cycle": k, "session_id": sid,
           "start_utc": t0.isoformat(), "end_utc": t1.isoformat(), "minutes": round((t1 - t0).seconds / 60, 1),
           "model": MODEL, "wake_reason": wake, "phases": len(records),
           "failed_phases": [r["phase"] for r in records if r["llm_failed"]],
           "avg_coherence": round(sum(r["coherence"]["overall"] for r in records) / max(1, len(records)), 3),
           "insights": aw.get("insights"), "explore_next": aw.get("explore_next"), "records": records,
           "label": DREAM_LABEL}
    json.dump(cyc, open(f"{OUT}/cycles/c{n:02d}_{mode}.json", "w"), indent=2, ensure_ascii=False)
    return cyc


def journal(cyc):
    j = json.load(open(JOURNAL))
    j["dreams"].append({"session_id": cyc["session_id"], "start_time": cyc["start_utc"], "end_time": cyc["end_utc"],
                        "duration_minutes": cyc["minutes"], "phases": [r["phase"] for r in cyc["records"]],
                        "insights": cyc["insights"], "avg_coherence": cyc["avg_coherence"],
                        "wake_reason": cyc["wake_reason"], "model": MODEL, "batch_id": BATCH,
                        "dream_lens": cyc["mode"], "real_llm": not cyc["failed_phases"],
                        "memory_source": "compass.db facts and messages (read-only) + one earlier dream fragment",
                        "label": DREAM_LABEL,
                        "phase_records": [{k: r[k] for k in ("phase", "mode", "temperature", "text", "coherence",
                                                            "steer_out", "timestamp_utc")} for r in cyc["records"]]})
    tmp = JOURNAL + ".tmp"
    json.dump(j, open(tmp, "w"), indent=2, ensure_ascii=False)
    os.replace(tmp, JOURNAL)


def store(cyc):
    """Write this cycle's phases into the dream-only vector store (dreams table, CHECK is_dream=1)."""
    import struct
    c = sqlite3.connect(STORE)
    n_ok, fails = 0, []
    for r in cyc["records"]:
        if not r["text"]:
            continue
        rid = f"{BATCH}:c{cyc['cycle_number']:02d}:{cyc['mode']}:p{r['phase_index']}:{r['phase']}"
        try:
            v = embed([r["text"]], input_type="passage")[0]
        except Exception as e:
            fails.append((rid, str(e)[:120]))
            continue
        meta = {"mode": cyc["mode"], "lens": MODE_NAME[cyc["mode"]], "mode_cycle": cyc["mode_cycle"],
                "temperature": r["temperature"], "coherence": r["coherence"], "phase_timestamp_utc": r["timestamp_utc"],
                "cycle_start_utc": cyc["start_utc"], "cycle_end_utc": cyc["end_utc"], "dream_model": MODEL,
                "wake_reason": cyc["wake_reason"], "steer_in": r["steer_in"], "steer_out": r["steer_out"],
                "seed_memory_ids": r["seed_memory_ids"], "seed_prior_dream_id": r["seed_prior_dream_id"],
                "provenance": {"source_file": f"{OUT}/cycles/c{cyc['cycle_number']:02d}_{cyc['mode']}.json",
                               "journal": JOURNAL},
                "imported_by": "Miles (Sesame) extended dream task"}
        c.execute("""INSERT OR REPLACE INTO dreams (id,label,batch_id,kind,cycle_number,phase,phase_index,session_id,text,
                     text_sha256,text_chars,metadata,embedding_model,embedding_dim,embedding,imported_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (rid, DREAM_LABEL, BATCH, "dream_phase", cyc["cycle_number"], r["phase"], r["phase_index"],
                   cyc["session_id"], r["text"], hashlib.sha256(r["text"].encode()).hexdigest(), len(r["text"]),
                   json.dumps(meta, ensure_ascii=False), DREAM_EMBED_MODEL, len(v), struct.pack(f"{len(v)}f", *v),
                   datetime.now(timezone.utc).isoformat()))
        n_ok += 1
    c.commit()
    c.close()
    return n_ok, fails


def main():
    os.makedirs(f"{OUT}/cycles", exist_ok=True)
    s = status(state="running", started=datetime.now(timezone.utc).isoformat(), plan=PLAN)
    walker = R.RealMemoryWalker()
    print(f"model={MODEL} memories={len(walker.pool)} recent={len(walker.recent_pool)}", flush=True)
    wishes = {}
    done = {c["n"] for c in s["cycles"] if c.get("stored")}
    for n, (mode, k) in enumerate(PLAN, 1):
        if n in done:
            continue
        cyc = run_cycle(n, mode, k, walker, wishes)
        if cyc["explore_next"] and mode != "blend":
            wishes[mode] = cyc["explore_next"]
        journal(cyc)
        n_ok, fails = store(cyc)
        s = json.load(open(f"{OUT}/status.json"))
        s["cycles"].append({"n": n, "mode": mode, "session": cyc["session_id"], "phases": cyc["phases"],
                            "failed_phases": cyc["failed_phases"], "wake": cyc["wake_reason"],
                            "minutes": cyc["minutes"], "stored": n_ok, "store_failures": fails,
                            "explore_next": cyc["explore_next"]})
        json.dump(s, open(f"{OUT}/status.json", "w"), indent=2)
        time.sleep(5)
    status(state="done", finished=datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
