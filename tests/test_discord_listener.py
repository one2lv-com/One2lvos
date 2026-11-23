"""Offline tests for the Discord listener's reply shaping (posts nothing)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_env = dict(os.environ)
import discord_listener as dl  # noqa: E402  (loads .env into os.environ on import)
os.environ.clear()
os.environ.update(_env)   # keep the repo's .env out of the other test modules


def test_sources_footer_removed():
    r = "Hello. It's good to hear from you. How can I help today?\n\n\u2014 Sources: soul \u00b7 live status \u00b7 fuzzy memory"
    assert dl.clean_for_discord(r) == "Hello. It's good to hear from you. How can I help today?"


def test_think_blocks_and_blank_runs_removed():
    r = "<think>internal plan</think>\nAnswer line one.\n\n\n\nLine two."
    assert dl.clean_for_discord(r) == "Answer line one.\n\nLine two."


def test_body_mentioning_sources_is_kept():
    r = "Sources: I read the Astra docs.\nMore text."
    assert dl.clean_for_discord(r) == r


def test_split_under_limit_and_lossless_words():
    text = ("word " * 1200).strip()
    parts = dl.split_reply(text)
    assert len(parts) > 1
    assert all(len(p) <= 2000 for p in parts)
    assert " ".join(parts).split() == text.split()


def test_split_keeps_code_fences_balanced():
    code = "```python\n" + "\n".join(f"print({i})  # line {i}" for i in range(300)) + "\n```"
    parts = dl.split_reply("Here is the code:\n\n" + code)
    assert len(parts) > 1
    for p in parts:
        assert len(p) <= 2000
        assert p.count("```") % 2 == 0, p[:80]


def test_parse_request():
    assert dl.parse_request("!lumenis hello", None) == "hello"
    assert dl.parse_request("<@42> hi there", 42) == "hi there"
    assert dl.parse_request("just chatting", 42) is None
