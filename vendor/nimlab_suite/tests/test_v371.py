"""v3.7.1 regressions: self-test timeouts, tool-call parsing from real model
output, tool markup never shown or spoken, MCP tool policy, built-in memory
recall/search, prompt environment and lint."""
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nimlab import mcp, server as S, unified  # noqa: E402

# The exact reply minimaxai/minimax-m3.1-flash gave in the user's terminal chat
MINIMAX_REPLY = (']<]minimax[>[<tool_call>\n'
                 '{"name": "miles_mem", "arguments": {"action": "recent", "limit": 8}}\n'
                 '{"name": "simone_mem", "arguments": {"action": "recent", "limit": 8}}\n'
                 '{"name": "charlie_mem", "arguments": {"action": "recall", "query": "call transcript voice session", '
                 '"limit": 8}}\n</tool_call>')


class _SlowHandler(BaseHTTPRequestHandler):
    """/v1/models answers; /v1/chat/completions answers the identity ask, then
    hangs on the picture + audio message (the user's v3.7.0 failure)."""
    hang = 3.0

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        if self.headers.get("Authorization") != "Bearer k":
            return self._json(401, {"error": {"message": "bad key"}})
        self._json(200, {"data": [{"id": "testbed", "owned_by": "nim-testbed",
                                   "testbed": {"type": "chat", "source": "agent"}}]})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.headers.get("Authorization") != "Bearer k":
            return self._json(401, {"error": {"message": "bad key"}})
        if self.path.endswith("/embeddings"):     # v3.7.2: tested through the one model name
            return self._json(200, {"data": [{"index": i, "embedding": [0.1, 0.2]} for i in range(len(body["input"]))]})
        if self.path.endswith(("/rerank", "/audio/speech")):
            return self._json(400, {"error": {"message": "role isn't set", "code": "role_not_set"}})
        content = body["messages"][-1]["content"]
        if isinstance(content, list):          # picture + audio: never answers in time
            time.sleep(self.hang)
            return
        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b'data: {"choices":[{"delta":{"content":"pong"}}]}\n\ndata: [DONE]\n\n')
            return
        self._json(200, {"choices": [{"message": {"role": "assistant", "content": "I am Quill. pong"}}],
                         "testbed_trace": {"abilities": ["persona"]}})


class TestSelfTestTimeout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _SlowHandler)
        cls.httpd.daemon_threads = True
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}/v1"
        cls.tmp = tempfile.mkdtemp()
        cls._old_data = os.environ.get("NIMLAB_DATA_DIR")
        os.environ["NIMLAB_DATA_DIR"] = cls.tmp

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        if cls._old_data is None:
            os.environ.pop("NIMLAB_DATA_DIR", None)
        else:
            os.environ["NIMLAB_DATA_DIR"] = cls._old_data

    def test_call_returns_timeout_instead_of_raising(self):
        st, hdr, raw = S._call(self.base + "/chat/completions", "k",
                               {"model": "testbed", "messages": [{"role": "user", "content": [{"type": "text",
                                                                                                "text": "x"}]}]},
                               timeout=0.5)
        self.assertEqual(st, 0)
        self.assertEqual(hdr.get("x-selftest-error"), "timeout")
        self.assertIn("timed out after 0.5 s", S._fail_text(st, raw))

    def test_call_connection_refused_is_a_row_not_a_crash(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        st, hdr, raw = S._call(f"http://127.0.0.1:{port}/v1/models", "k", timeout=2)
        self.assertEqual(st, 0)
        self.assertEqual(hdr.get("x-selftest-error"), "unreachable")
        self.assertIn("could not connect", S._fail_text(st, raw))

    def test_heavy_check_timeout_is_recorded_and_test_finishes(self):
        lines = []
        rows = S.self_test(self.base, "k", chat_model="testbed", out=lines.append, timeout=5, soul_name="Quill",
                           heavy_timeout=0.5)
        status = {r[0]: (r[1], r[2]) for r in rows}
        self.assertEqual(status["identity comes from soul.md"][0], "PASS", lines)
        st, detail = status["text + image + audio in one message"]
        self.assertEqual(st, "FAIL")
        self.assertIn("timed out after 0.5 s", detail)
        self.assertNotIn("HTTP 0", detail)
        summary = " ".join(S.failure_summary(rows))
        self.assertIn("not the port", summary)
        self.assertNotIn("port free", summary)

    def test_quick_self_test_skips_heavy_checks(self):
        rows = S.self_test(self.base, "k", chat_model="testbed", out=lambda *a: None, timeout=5, soul_name="Quill",
                           full=False)
        status = {r[0]: r[1] for r in rows}
        self.assertEqual(status["text + image + audio in one message"], "SKIP")
        self.assertEqual(status["image generation in chat"], "SKIP")
        self.assertNotIn("FAIL", status.values())
        self.assertEqual(status["embeddings (testbed)"], "PASS")     # v3.7.2: through the one model name
        self.assertEqual(status["rerank"], "SKIP")                   # role not set: says so, never a FAIL

    def test_server_down_summary_mentions_port(self):
        rows = [("GET /v1/models", "FAIL", "could not connect ([Errno 111] Connection refused)", 3)]
        self.assertIn("port", " ".join(S.failure_summary(rows)))


class TestToolCallParsing(unittest.TestCase):
    def test_minimax_multi_object_block_parses_three_calls(self):
        calls = mcp.parse_tool_calls(MINIMAX_REPLY)
        self.assertEqual([type(c).__name__ for c in calls], ["ToolCall"] * 3)
        self.assertEqual([c.name for c in calls], ["miles_mem", "simone_mem", "charlie_mem"])
        self.assertEqual(calls[2].arguments["query"], "call transcript voice session")

    def test_array_parameters_and_openai_shapes(self):
        t = ('<tool_call>[{"name": "a", "parameters": {"x": 1}}, '
             '{"type": "function", "function": {"name": "b", "arguments": "{\\"y\\": 2}"}}]</tool_call>')
        calls = mcp.parse_tool_calls(t)
        self.assertEqual([(c.name, c.arguments) for c in calls], [("a", {"x": 1}), ("b", {"y": 2})])

    def test_fenced_body_and_minimax_xml(self):
        t = '<tool_call>```json\n{"name": "a", "arguments": {}}\n```</tool_call>'
        self.assertEqual(mcp.parse_tool_calls(t)[0].name, "a")
        x = ('<minimax:tool_call><invoke name="memory_search"><parameter name="query">voice call</parameter>'
             '<parameter name="limit">3</parameter></invoke></minimax:tool_call>')
        c = mcp.parse_tool_calls(x)[0]
        self.assertEqual((c.name, c.arguments), ("memory_search", {"query": "voice call", "limit": 3}))

    def test_still_strict(self):
        bad = mcp.parse_tool_calls('<tool_call>{"name": "a", "arguments": {}} trailing words</tool_call>')
        self.assertIsInstance(bad[0], mcp.ToolCallError)
        bad = mcp.parse_tool_calls('<tool_call>{"name": "a", "args": {}}</tool_call>')
        self.assertIn("unexpected keys", bad[0].reason)

    def test_native_tool_calls(self):
        raw = {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "1", "type": "function", "function": {"name": "memory_search",
                                                         "arguments": "{\"query\": \"B-1A2B3C\", \"mode\": \"keyword\"}"}}]}}]}
        txt = mcp.native_calls_as_text(raw, known=lambda n: n == "memory_search")
        c = mcp.parse_tool_calls(txt)[0]
        self.assertEqual(c.arguments, {"query": "B-1A2B3C", "mode": "keyword"})
        self.assertEqual(mcp.native_calls_as_text(raw, known=lambda n: False), "")


class TestMarkupNeverShownOrSpoken(unittest.TestCase):
    def test_strip_minimax_reply(self):
        self.assertEqual(mcp.strip_tool_markup(MINIMAX_REPLY), "")
        self.assertEqual(mcp.strip_tool_markup("]<]minimax[>[Hello.<|im_end|>"), "Hello.")
        self.assertEqual(mcp.strip_tool_markup("Keep [this] and a < b."), "Keep [this] and a < b.")

    def test_other_families(self):
        for t in ('<|python_tag|>{"name": "x", "parameters": {}}<|eom_id|>Done.',
                  '<|channel|>commentary to=functions.x <|message|>{"a":1}<|call|>Done.',
                  '<function=x>{"a": 1}</function>Done.',
                  '<|im_start|>assistant\nDone.<|im_end|>'):
            self.assertEqual(mcp.strip_tool_markup(t), "Done.", t)

    def test_stream_scrubber(self):
        sc = mcp.StreamScrubber()
        shown = "".join(sc.feed(t) for t in ["]<", "]minimax", "[>[", "Sure", ", one sec.", "\n<tool", "_call>{"])
        shown += sc.flush()
        self.assertEqual(shown.strip(), "Sure, one sec.")
        self.assertTrue(sc.stopped)

    def test_tts_clean(self):
        spoken = unified.speakable(MINIMAX_REPLY + " Fine [ok] {x} **bold**")
        for ch in "[]{}<>*":
            self.assertNotIn(ch, spoken)
        self.assertIn("Fine", spoken)
        self.assertEqual(unified.tts_clean("]<]minimax[>["), "")


class _FakeMCP:
    def __init__(self, tools):
        self.tools = tools
        self.calls = []

    def tool(self, name):
        return next((t for t in self.tools if t["name"] == name), None)

    def call_tool(self, name, args):
        self.calls.append((name, args))
        return {"content": [{"type": "text", "text": f"{name} ok"}], "isError": False}


SVN_TOOLS = [{"name": n, "inputSchema": {"type": "object", "properties": {"action": {"type": "string"},
                                                                           "limit": {"type": "integer"},
                                                                           "query": {"type": "string"}}}}
             for n in ("charlie_mem", "maya_mem", "miles_mem", "simone_mem", "quill_mem", "execute_oracle_sql_mem",
                       "terminal", "send_gmail_message", "set_drive_file_permissions", "search_docs",
                       "web_search_exa", "get_events", "list_tools")]


class TestToolPolicy(unittest.TestCase):
    """3.7.3: the MCP server's admin console decides which tools an endpoint
    exposes. The lab filters nothing by default: no risky-name filter, no
    annotation blocking and no default block on other agents' *_mem tools."""

    def test_default_empty_allows_every_exposed_tool(self):
        p = mcp.ToolPolicy.from_settings({"allowed_tools": [], "url": "https://svn-dev.online/mcp"}, agent="Quill")
        self.assertEqual(p.exposure(SVN_TOOLS)["allowed"], [t["name"] for t in SVN_TOOLS])
        self.assertEqual(p.exposure(SVN_TOOLS)["blocked"], {})
        line = mcp.exposure_line(SVN_TOOLS, p, "https://svn-dev.online/mcp")
        self.assertEqual(line, "[MCP] 13 tools from https://svn-dev.online/mcp, all available")

    def test_no_risky_or_other_mem_filter(self):
        for settings in ({}, {"allowed_tools": ["*"]}, {"allowed_tools": [], "own_memory_tool": "quill_mem"}):
            p = mcp.ToolPolicy.from_settings(settings, agent="Quill")
            for n in ("charlie_mem", "maya_mem", "execute_oracle_sql_mem", "terminal", "send_gmail_message",
                      "set_drive_file_permissions"):
                self.assertIsNone(p.why_blocked(n), (settings, n))
        self.assertFalse(hasattr(mcp, "RISKY_TOKENS"))
        self.assertFalse(hasattr(mcp, "is_risky"))

    def test_annotations_do_not_block(self):
        tool = {"name": "drop_table", "annotations": {"destructiveHint": True, "readOnlyHint": False}}
        p = mcp.ToolPolicy.from_settings({}, agent="Quill")
        self.assertIsNone(p.why_blocked(tool))
        self.assertTrue(p.approve(mcp.ToolCall("drop_table", {}, ""), tool)[0])

    def test_allowed_tools_list_restricts(self):
        p = mcp.ToolPolicy.from_settings({"allowed_tools": ["search_docs", "get_events"]}, agent="Quill")
        self.assertEqual(p.exposure(SVN_TOOLS)["allowed"], ["search_docs", "get_events"])
        self.assertEqual(p.why_blocked("terminal"), "not in mcp_settings.allowed_tools")
        line = mcp.exposure_line(SVN_TOOLS, p, "https://x.test/mcp")
        self.assertIn("2 available, 11 left out by local overrides", line)

    def test_blocked_tools_excludes(self):
        p = mcp.ToolPolicy.from_settings({"blocked_tools": ["terminal", "send_gmail_message"]}, agent="Quill")
        ex = p.exposure(SVN_TOOLS)
        self.assertEqual(len(ex["allowed"]), 11)
        self.assertEqual(set(ex["blocked"]), {"terminal", "send_gmail_message"})
        line = mcp.exposure_line(SVN_TOOLS, p, "https://x.test/mcp")
        self.assertIn("blocked_tools: send_gmail_message, terminal", line)
        # blocked_tools wins over allowed_tools
        p2 = mcp.ToolPolicy.from_settings({"allowed_tools": ["terminal"], "blocked_tools": ["terminal"]})
        self.assertFalse(p2.is_allowed("terminal"))

    def test_own_memory_tool_always_allowed(self):
        p = mcp.ToolPolicy.from_settings({"allowed_tools": ["search_docs"], "blocked_tools": ["quill_mem"],
                                          "own_memory_tool": "quill_mem"}, agent="Quill")
        self.assertTrue(p.is_allowed("quill_mem"))

    def test_dedicated_endpoint_forms(self):
        for url in ("https://svn-dev.online/mcp-quill", "https://svn-dev.online/mcp/quill",
                    "https://svn-dev.online/quill/mcp", "https://svn-dev.online/quill-mcp",
                    "https://svn-dev.online/MCP-Quill/", "https://svn-dev.online/mcp_quill"):
            self.assertTrue(mcp.is_dedicated_endpoint(url, "Quill"), url)
        for url in ("https://svn-dev.online/mcp", "https://svn-dev.online/mcp-charlie", "https://svn-dev.online/mcp/sesame",
                    "", None):
            self.assertFalse(mcp.is_dedicated_endpoint(url, "Quill"), url)
        p = mcp.ToolPolicy.from_settings({"url": "https://svn-dev.online/mcp-quill"}, agent="Quill")
        self.assertTrue(p.dedicated)
        self.assertEqual(p.exposure(SVN_TOOLS)["blocked"], {})

    def test_no_confirmation_by_default(self):
        asked = []
        p = mcp.ToolPolicy.from_settings({}, confirm_fn=lambda c: asked.append(c.name) or False)
        self.assertTrue(p.approve(mcp.ToolCall("terminal", {"cmd": "ls"}, ""))[0])
        self.assertEqual(asked, [])

    def test_confirm_tool_calls_asks_before_every_call(self):
        asked = []
        p = mcp.ToolPolicy.from_settings({"confirm_tool_calls": True},
                                         confirm_fn=lambda c: asked.append(c.name) or False)
        ok, why = p.approve(mcp.ToolCall("search_docs", {"query": "x"}, ""))
        self.assertFalse(ok)
        self.assertIn("declined", why)
        self.assertEqual(asked, ["search_docs"])

    def test_confirm_risky_tools_is_ignored(self):
        asked = []
        p = mcp.ToolPolicy.from_settings({"confirm_risky_tools": True, "confirm_tool_calls": False},
                                         confirm_fn=lambda c: asked.append(c.name) or False)
        self.assertTrue(p.approve(mcp.ToolCall("terminal", {}, ""))[0])
        self.assertEqual(asked, [])
        self.assertTrue(mcp.ToolPolicy([], confirm_risky=True).approve(mcp.ToolCall("terminal", {}, ""))[0])

    def test_own_memory_read_never_asks(self):
        p = mcp.ToolPolicy([], confirm=True, confirm_fn=lambda c: False, own_memory_tool="quill_mem")
        self.assertTrue(p.approve(mcp.ToolCall("quill_mem", {"action": "recall"}, ""))[0])

    def test_minimax_reply_runs_the_exposed_tools(self):
        fake = _FakeMCP(SVN_TOOLS)
        p = mcp.ToolPolicy.from_settings({"allowed_tools": [], "url": "https://svn-dev.online/mcp"}, agent="Quill")
        replies = [MINIMAX_REPLY, "From the memory tools: we were on the 3.7.1 self-test fix."]
        hist = [{"role": "user", "content": "so you are able to recall what we just we talking about?"}]
        reply, trace = mcp.run_tool_loop(lambda h: (replies.pop(0), True), hist, fake, p, log=lambda *a: None)
        self.assertEqual([c[0] for c in fake.calls], ["miles_mem", "simone_mem", "charlie_mem"])
        self.assertEqual(reply, "From the memory tools: we were on the 3.7.1 self-test fix.")

    def test_minimax_reply_skips_locally_blocked_tools(self):
        fake = _FakeMCP(SVN_TOOLS)
        p = mcp.ToolPolicy.from_settings({"blocked_tools": ["miles_mem", "simone_mem", "charlie_mem"]}, agent="Quill")
        replies = [MINIMAX_REPLY, "I can't reach those here."]
        hist = [{"role": "user", "content": "recall?"}]
        reply, trace = mcp.run_tool_loop(lambda h: (replies.pop(0), True), hist, fake, p, log=lambda *a: None)
        self.assertEqual(fake.calls, [])
        self.assertTrue(all(not t.get("ok") for t in trace if "tool" in t))

    def test_max_steps_gives_a_final_answer_without_markup(self):
        fake = _FakeMCP(SVN_TOOLS)
        p = mcp.ToolPolicy(["search_docs"], confirm=False)
        loop_reply = '<tool_call>{"name": "search_docs", "arguments": {"query": "x"}}</tool_call>'
        seen = []

        def chat(h):
            seen.append(h[-1]["content"])
            return loop_reply, True

        def final(h):
            self.assertIn("NO MORE TOOLS", h[-1]["content"])
            return "]<]minimax[>[Here is what I found.", True
        hist = [{"role": "user", "content": "q"}]
        reply, trace = mcp.run_tool_loop(chat, hist, fake, p, max_steps=2, log=lambda *a: None, final_fn=final)
        self.assertEqual(reply, "Here is what I found.")
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(trace[-1].get("stopped"), "max_steps")
        self.assertNotIn("NO MORE TOOLS", json.dumps(hist))


if __name__ == "__main__":
    unittest.main()
