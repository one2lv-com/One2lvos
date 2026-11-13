"""
Dream checks (items 23 and 24).

word_salad(text)  -> {"fail": bool, "leaked_tokens": [...], "flagged_windows": [...], "min_function_ratio": x}
    Any leaked model/chat-template token (<|start_header_id|>, <|eot_id|>, [INST], </s> ...) is an automatic
    failure. Every 40-word stretch (sliding by 10) whose small linking words (the, of, and, I, to ...) make up
    less than 15% of the words is flagged; one flagged stretch fails the phase. Bullet lists of short
    sentences still pass because they keep their linking words.

leak_check(dream_text, memories) -> [{"kind", "match", "source"}]
    Flags a real memory showing up inside a dream, so dream and memory can be told apart:
      - ids: game ids (FA421911), commit hashes, other CODE1234-style ids present in real memory
      - chess: a piece on a square ("bishop on g7", "Bg7") that also appears in a real game record
      - phrases: a 5-word run shared with a real memory that is not itself about dreams. Reported as an
        "echo" only: in a test on the Nov 12 run most were stock wording, so they do not set the leak label.
    It flags; it does not delete or block. The dream stays a dream, with the leak noted on it.

load_memory_corpus(db_path, days) -> list of (source, text) from the reactor's real memory: chat messages
    (not dream sessions) and facts that are not dream/plan rows.
"""
from __future__ import annotations

import re
import sqlite3
import time
from typing import Dict, Iterable, List, Tuple

LEAK_TOKEN_RE = re.compile(
    r"<\|[a-z_]{2,40}\|>|\[/?INST\]|</?s>|<<SYS>>|<</SYS>>|<\|im_(?:start|end)\|>|<start_of_turn>|<end_of_turn>"
    r"|\bassistant<\||<\|endoftext\|>", re.I)
FUNCTION_WORDS = set("""
a an the of to in on at by for from with into onto through over under about above below between among
and or but nor so yet if then than because while as like though although unless until since
i me my mine myself we us our ours you your yours he him his she her hers it its they them their theirs
this that these those who whom whose which what where when why how there here
is am are was were be been being have has had do does did can could will would shall should may might must
not no all any each every some one up down out off again just only also very too own same such
""".split())
WINDOW, STEP, MIN_RATIO = 40, 10, 0.15
_WORD = re.compile(r"[A-Za-z']+")


def word_salad(text: str) -> Dict:
    text = text or ""
    leaked = sorted(set(m.group(0) for m in LEAK_TOKEN_RE.finditer(text)))
    words = [w.lower().strip("'") for w in _WORD.findall(text)]
    flagged, worst = [], 1.0
    if len(words) >= WINDOW:
        for i in range(0, len(words) - WINDOW + 1, STEP):
            win = words[i:i + WINDOW]
            ratio = sum(1 for w in win if w in FUNCTION_WORDS) / WINDOW
            worst = min(worst, ratio)
            if ratio < MIN_RATIO:
                flagged.append({"start_word": i, "function_ratio": round(ratio, 3), "text": " ".join(win)[:240]})
    elif words:
        worst = sum(1 for w in words if w in FUNCTION_WORDS) / len(words)
    # merge overlapping windows into stretches for reporting
    stretches = []
    for f in flagged:
        if stretches and f["start_word"] <= stretches[-1]["end_word"]:
            stretches[-1]["end_word"] = f["start_word"] + WINDOW
            stretches[-1]["function_ratio"] = min(stretches[-1]["function_ratio"], f["function_ratio"])
        else:
            stretches.append({"start_word": f["start_word"], "end_word": f["start_word"] + WINDOW,
                              "function_ratio": f["function_ratio"], "sample": f["text"]})
    return {"fail": bool(leaked or flagged), "leaked_tokens": leaked, "flagged_stretches": stretches,
            "min_function_ratio": round(worst, 3), "words": len(words),
            "reason": ("leaked model token" if leaked else "") + (" + " if leaked and flagged else "")
            + (f"{len(stretches)} stretch(es) under {int(MIN_RATIO * 100)}% linking words" if flagged else "")}


# ── leak check ────────────────────────────────────────────────────────────────
ID_RE = re.compile(r"\b(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{2,}\d{3,}[A-Z0-9]*\b")
HASH_RE = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")
PIECES = {"king": "K", "queen": "Q", "rook": "R", "bishop": "B", "knight": "N", "pawn": "P"}
PIECE_SQ_RE = re.compile(r"\b(king|queen|rook|bishop|knight|pawn)s?\b[^.\n]{0,24}?\b([a-h][1-8])\b", re.I)
SAN_RE = re.compile(r"\b([KQRBN])x?([a-h][1-8])\b")
GAME_HINT = re.compile(r"\b(chess|game [A-Z]{2}\d{4,}|board|move|white|black)\b", re.I)
_STOP_PHRASE = FUNCTION_WORDS | {"lumenis", "dream", "memory", "memories"}


def _chess_marks(text: str) -> set:
    marks = set()
    for m in PIECE_SQ_RE.finditer(text):
        marks.add(PIECES[m.group(1).lower()] + m.group(2).lower())
    for m in SAN_RE.finditer(text):
        marks.add(m.group(1) + m.group(2))
    return marks


def _phrases(text: str, n: int = 5) -> set:
    w = [x.lower() for x in _WORD.findall(text)]
    out = set()
    for i in range(len(w) - n + 1):
        g = w[i:i + n]
        content = [x for x in g if x not in _STOP_PHRASE]
        if len(content) >= 3 and any(len(x) >= 6 for x in content):
            out.add(" ".join(g))
    return out


_DREAMY = re.compile(r"\b(dream|dreams|dreaming|nightmare|hypnagogic|lucid|rem phase|deep sleep|light sleep|"
                     r"awakening|dream cycle|astral|world tree)\b", re.I)


def leak_check(dream_text: str, memories: Iterable[Tuple[str, str]], max_hits: int = 12,
               max_phrases: int = 4) -> List[Dict]:
    """Concrete markers (ids, chess positions) first; copied phrases only from memories that are not
    themselves about dreams (chats where dreams were discussed would otherwise match everything)."""
    dream_text = dream_text or ""
    d_ids = set(ID_RE.findall(dream_text)) | set(HASH_RE.findall(dream_text))
    d_chess = _chess_marks(dream_text)
    d_phr = _phrases(dream_text)
    hard, soft, seen = [], [], set()
    for source, text in memories:
        if not text:
            continue
        for i in d_ids:
            if i in text and ("id", i) not in seen:
                seen.add(("id", i))
                hard.append({"kind": "id", "match": i, "source": source})
        if d_chess and GAME_HINT.search(text):
            for c in d_chess & _chess_marks(text):
                if ("chess", c) not in seen:
                    seen.add(("chess", c))
                    g = re.search(r"\b([A-Z]{2}\d{6})\b", text)
                    hard.append({"kind": "chess", "match": c, "source": source + (f" (game {g.group(1)})" if g else "")})
        if d_phr and len(soft) < max_phrases and not _DREAMY.search(text):
            for ph in sorted(d_phr & _phrases(text)):
                if ("phrase", ph) not in seen and len(soft) < max_phrases:
                    seen.add(("phrase", ph))
                    soft.append({"kind": "phrase", "match": ph, "source": source})
    return (hard + soft)[:max_hits]


def load_memory_corpus(db_path: str, days: int = 21, limit: int = 4000) -> List[Tuple[str, str]]:
    """Real (non-dream) memory from compass.db: chat messages and facts."""
    since = time.time() - days * 86400
    out: List[Tuple[str, str]] = []
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    try:
        cols = {r[1] for r in c.execute("PRAGMA table_info(messages)")}
        tcol = "created_at" if "created_at" in cols else ("timestamp" if "timestamp" in cols else None)
        q = ("SELECT session_id, content FROM messages WHERE COALESCE(session_id,'') NOT LIKE 'dream%'"
             + (f" AND {tcol} >= ?" if tcol else "") + " ORDER BY rowid DESC LIMIT ?")
        for sid, content in c.execute(q, ((since, limit) if tcol else (limit,))):
            out.append((f"chat {sid}", content or ""))
        for key, val in c.execute("SELECT key, value FROM facts WHERE COALESCE(verification,'') NOT IN "
                                  "('dream','plan') AND created_at >= ? ORDER BY created_at DESC LIMIT ?",
                                  (since, limit)):
            out.append((f"fact {key}", f"{key}: {val}"))
    finally:
        c.close()
    return out


def check_phase(text: str, memories) -> Dict:
    ws = word_salad(text)
    found = leak_check(text, memories)
    leaks = [h for h in found if h["kind"] in ("id", "chess")]
    echoes = [h for h in found if h["kind"] == "phrase"]
    # Only concrete markers (ids, chess positions) count as a leak. Shared phrases are often stock wording
    # ("the vast expanse of space"), so they are listed as echoes to look at, not labelled.
    return {"word_salad": ws, "memory_leaks": leaks, "phrase_echoes": echoes,
            "labels": (["WORD_SALAD"] if ws["fail"] else []) + (["REAL_MEMORY_IN_DREAM"] if leaks else [])}
