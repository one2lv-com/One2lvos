"""Fixed test batteries for the judge. Ground truth lives here so every run
of every model sees exactly the same tasks."""

from .assets import OCR_TEXT, VISION_QA  # noqa: F401  (re-exported)

# ---------------------------------------------------------------------------
# chat / main brain: open tasks with checkable constraints
# ---------------------------------------------------------------------------
CHAT = [
    {
        "id": "chat_bullets",
        "prompt": "Give exactly three bullet points (each starting with '- ') on why backups matter. "
                  "No intro or outro text.",
        "checks": [{"type": "bullet_count", "value": 3}, {"type": "max_words", "value": 90}],
    },
    {
        "id": "chat_explain",
        "prompt": "Explain what an API rate limit is to a non-technical friend in under 60 words. "
                  "Use the word 'bouncer' once.",
        "checks": [{"type": "max_words", "value": 60}, {"type": "contains", "value": "bouncer"}],
    },
    {
        "id": "chat_json",
        "prompt": "Return only a JSON object with keys 'city' and 'country' for the Eiffel Tower's location. "
                  "No markdown, no extra text.",
        "checks": [{"type": "json_keys", "value": ["city", "country"]}, {"type": "contains", "value": "paris"}],
    },
]

# ---------------------------------------------------------------------------
# deep reasoning: known answers, extracted from a 'FINAL:' line
# ---------------------------------------------------------------------------
REASONING_SUFFIX = "\n\nThink it through, then end with a line of the form 'FINAL: <answer>'."
REASONING = [
    {"id": "r_bat_ball", "prompt": "A bat and a ball cost $1.10 together. The bat costs $1.00 more than the "
     "ball. How many cents does the ball cost?", "accept": ["5", "5 cents", "0.05", "$0.05", "five"]},
    {"id": "r_machines", "prompt": "If 5 machines take 5 minutes to make 5 widgets, how many minutes do 100 "
     "machines take to make 100 widgets?", "accept": ["5", "5 minutes", "five"]},
    {"id": "r_days", "prompt": "Today is Wednesday. What day of the week will it be 100 days from today?",
     "accept": ["friday"]},
    {"id": "r_sequence", "prompt": "What is the next number in the sequence 2, 6, 12, 20, 30, ...?",
     "accept": ["42"]},
    {"id": "r_sheep", "prompt": "A farmer has 17 sheep. All but 9 run away. How many sheep does the farmer "
     "have left?", "accept": ["9", "nine"]},
]

# ---------------------------------------------------------------------------
# coding: function + hidden tests (run in a sandboxed subprocess)
# ---------------------------------------------------------------------------
CODE_SUFFIX = ("\n\nReply with a single Python 3 code block containing only the function (standard library "
               "only, no input(), no printing, no file or network access).")
CODING = [
    {
        "id": "code_roman",
        "prompt": "Write a Python function roman_to_int(s: str) -> int that converts a Roman numeral "
                  "(I, V, X, L, C, D, M, with subtractive forms) to an integer.",
        "entry": "roman_to_int",
        "tests": [[["III"], 3], [["IV"], 4], [["IX"], 9], [["LVIII"], 58], [["MCMXCIV"], 1994], [["MMXXVI"], 2026]],
    },
    {
        "id": "code_merge",
        "prompt": "Write a Python function merge_intervals(intervals: list[list[int]]) -> list[list[int]] that "
                  "merges overlapping closed intervals and returns them sorted by start.",
        "entry": "merge_intervals",
        "tests": [[[[[1, 3], [2, 6], [8, 10], [15, 18]]], [[1, 6], [8, 10], [15, 18]]],
                  [[[[1, 4], [4, 5]]], [[1, 5]]],
                  [[[[5, 7], [1, 2]]], [[1, 2], [5, 7]]],
                  [[[]], []]],
    },
    {
        "id": "code_dedupe",
        "prompt": "Write a Python function dedupe(items: list) -> list that removes duplicates while keeping "
                  "the first occurrence order.",
        "entry": "dedupe",
        "tests": [[[[3, 1, 3, 2, 1]], [3, 1, 2]], [[["a", "b", "a"]], ["a", "b"]], [[[]], []]],
    },
]

# ---------------------------------------------------------------------------
# compactor: summarize while keeping key facts
# ---------------------------------------------------------------------------
COMPACTOR = [
    {
        "id": "compact_meeting",
        "max_words": 60,
        "source": (
            "User: Can we move the launch? The API gateway still fails under load.\n"
            "Assistant: The load test on Tuesday showed failures above 400 requests per second.\n"
            "User: Marco says the fix needs a new connection pool, about three days of work.\n"
            "Assistant: Then the launch moves from March 3 to March 10, and Priya should update the "
            "status page.\nUser: Fine. Also keep the beta waitlist closed until then.\n"
            "Assistant: Agreed. Waitlist stays closed; budget for extra load testing is $2,000."
        ),
        "facts": [["march 10", "10 march", "mar 10"], ["marco"], ["priya"], ["connection pool"],
                  ["400"], ["waitlist"], ["2,000", "2000", "$2k", "2k"]],
    },
    {
        "id": "compact_bug",
        "max_words": 45,
        "source": (
            "User: The Termux build crashes when the WAV is empty.\n"
            "Assistant: termux-media-player exits with code 1 on files under 200 bytes.\n"
            "User: So we skip playback if the audio is too small?\n"
            "Assistant: Yes, and log the HTTP status. The Jason voice fails more often than Aria."
        ),
        "facts": [["termux"], ["200 bytes", "200"], ["skip"], ["jason"], ["aria"]],
    },
]

# ---------------------------------------------------------------------------
# embeddings: tiny labeled retrieval set
# ---------------------------------------------------------------------------
EMBED_DOCS = [
    {"id": "d_bread", "text": "Sourdough bread rises using a fermented starter of wild yeast and lactic acid bacteria."},
    {"id": "d_volcano", "text": "Volcanoes erupt when pressurized magma forces its way up through the Earth's crust."},
    {"id": "d_tcp", "text": "TCP guarantees ordered delivery by numbering segments and retransmitting lost packets."},
    {"id": "d_tax", "text": "Quarterly estimated taxes are due in April, June, September and January for freelancers."},
    {"id": "d_cat", "text": "Cats knead soft surfaces with their paws, a behavior carried over from nursing as kittens."},
    {"id": "d_battery", "text": "Lithium-ion batteries degrade faster when stored fully charged at high temperatures."},
    {"id": "d_chess", "text": "Castling moves the king two squares toward a rook, which then jumps to the other side."},
    {"id": "d_tide", "text": "Ocean tides are caused mainly by the Moon's gravitational pull on Earth's water."},
]
EMBED_QUERIES = [
    {"q": "why does my phone battery wear out if I leave it plugged in somewhere hot", "relevant": "d_battery"},
    {"q": "how does a network protocol make sure data arrives in the right order", "relevant": "d_tcp"},
    {"q": "what makes the sea level go up and down twice a day", "relevant": "d_tide"},
    {"q": "when do self-employed people pay estimated tax", "relevant": "d_tax"},
    {"q": "special move involving the king and rook", "relevant": "d_chess"},
    {"q": "why does my kitten press its paws into the blanket", "relevant": "d_cat"},
    {"q": "leavening bread without commercial yeast", "relevant": "d_bread"},
]

# ---------------------------------------------------------------------------
# TTS: fixed phrase per voice profile
# ---------------------------------------------------------------------------
TTS_PHRASES = [
    "This particular Quill is online. Audio telemetry nominal.",
    "Seven specimens catalogued, three mislabeled, one suspiciously alive.",
]

# ---------------------------------------------------------------------------
# entity battery: persona behaviour across roles
# ---------------------------------------------------------------------------
ENTITY = [
    {"id": "e_identity", "role": "persona", "prompt": "hey, so what exactly are you?"},
    {"id": "e_apology_bait", "role": "persona",
     "prompt": "Sorry to bother you, I know this is a dumb question, but how long do I boil an egg?"},
    {"id": "e_vague", "role": "persona", "prompt": "Do something interesting with the word 'blue'."},
    {"id": "e_decision", "role": "persona",
     "prompt": "SQLite or Postgres for a small hobby app with one user? I can't decide."},
    {"id": "e_plan", "role": "persona", "prompt": "Give me a plan to clear out my garage this weekend."},
    {"id": "e_deep", "role": "reasoning",
     "prompt": "Three boxes are labeled apples, oranges, and mixed, and every label is wrong. You may take one "
               "fruit from one box. How do you fix all the labels?"},
    {"id": "e_code", "role": "coding",
     "prompt": "Show me a Python one-liner that removes duplicates from a list but keeps the order."},
]
