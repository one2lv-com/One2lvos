"""Reasoning models' thinking never reaches the reply (v3.4.1)."""
import json
import unittest

from nimlab.api import NimClient, ThinkFilter, THINKING_ONLY_NOTE, strip_thinking
from nimlab.core import HttpClient
from tests.fakes import FakeResponse, RouteOpener


def sse(deltas):
    out = "".join("data: " + json.dumps({"choices": [{"delta": d}]}) + "\n\n" for d in deltas)
    return out + "data: [DONE]\n\n"


def client(handler):
    opener = RouteOpener([("/chat/completions", handler)])
    http = HttpClient(opener=opener, retries=0, sleep=lambda s: None)
    return NimClient(api_key="nvapi-TESTKEY000000000000000000000000000000000000000000", http=http, cluster={})


class StripThinking(unittest.TestCase):
    def test_blocks_and_variants(self):
        self.assertEqual(strip_thinking("<think>hmm</think>\n\nHello"), "Hello")
        self.assertEqual(strip_thinking("<THINKING>x</THINKING>Hi"), "Hi")
        self.assertEqual(strip_thinking("thinking with no open tag</think>Answer"), "Answer")
        self.assertEqual(strip_thinking("Answer<think>unfinished"), "Answer")
        self.assertEqual(strip_thinking("analysisWe need to reply.assistantfinalHi there"), "Hi there")

    def test_plain_text_untouched(self):
        for s in ("Plain answer", "a < b, and <b>bold</b>", "```\nx = 1\n```", ""):
            self.assertEqual(strip_thinking(s), s)


class StreamFilter(unittest.TestCase):
    def run_chunks(self, chunks):
        f = ThinkFilter()
        return "".join(f.feed(c) for c in chunks) + f.flush()

    def test_tags_split_across_chunks(self):
        self.assertEqual(self.run_chunks(["<th", "ink>We need", " to answer</thi", "nk>\n\nAh, ", "yes."]), "Ah, yes.")

    def test_angle_brackets_pass(self):
        self.assertEqual(self.run_chunks(["if a <", " b then ", "<b>ok</b>"]), "if a < b then <b>ok</b>")

    def test_unclosed_think_dropped(self):
        self.assertEqual(self.run_chunks(["Hi. ", "<think>never closes"]), "Hi. ")


class ChatCalls(unittest.TestCase):
    def test_stream_drops_reasoning_content(self):
        deltas = [{"reasoning_content": "We need answer latest. "}, {"reasoning_content": "Need maintain character."},
                  {"content": "Ah, "}, {"content": "yes."}]
        c = client(lambda req: FakeResponse(sse(deltas), headers={"Content-Type": "text/event-stream"}))
        seen = []
        r = c.chat_stream("openai/gpt-oss-120b", [{"role": "user", "content": "hi"}], on_token=seen.append)
        self.assertTrue(r.ok)
        self.assertEqual(r.text, "Ah, yes.")
        self.assertEqual("".join(seen), "Ah, yes.")

    def test_stream_reasoning_field_and_think_tags(self):
        deltas = [{"reasoning": "plan"}, {"content": "<think>more"}, {"content": "</think>Done."}]
        c = client(lambda req: FakeResponse(sse(deltas), headers={"Content-Type": "text/event-stream"}))
        self.assertEqual(c.chat_stream("x/y", [{"role": "user", "content": "hi"}]).text, "Done.")

    def test_stream_only_thinking_gives_note(self):
        deltas = [{"reasoning_content": "We need..."}]
        c = client(lambda req: FakeResponse(sse(deltas), headers={"Content-Type": "text/event-stream"}))
        self.assertEqual(c.chat_stream("x/y", [{"role": "user", "content": "hi"}]).text, THINKING_ONLY_NOTE)

    def test_non_stream_never_returns_reasoning(self):
        body = {"choices": [{"message": {"content": "", "reasoning_content": "We need..."},
                              "finish_reason": "length"}]}
        c = client(lambda req: FakeResponse(body))
        self.assertEqual(c.chat("x/y", [{"role": "user", "content": "hi"}]).text, THINKING_ONLY_NOTE)
        body = {"choices": [{"message": {"content": "<think>a</think>Hello", "reasoning_content": "b"}}]}
        c = client(lambda req: FakeResponse(body))
        self.assertEqual(c.chat("x/y", [{"role": "user", "content": "hi"}]).text, "Hello")


if __name__ == "__main__":
    unittest.main()
