"""Lazy tool definitions: index in the prompt, schemas via load_tools."""
import json
from nimlab import mcp as M


class Box:
    def __init__(self):
        self.tools = [
            {"name": "quill_gmail", "description": "Read and reply to Quill's Gmail. Long text here.",
             "inputSchema": {"type": "object", "properties": {"action": {"type": "string"}},
                             "required": ["action"]}},
            {"name": "get_system_stats", "description": "System stats.", "inputSchema": {"type": "object"}},
        ]
        self.calls = []

    def tool(self, name):
        return next((t for t in self.tools if t["name"] == name), None)

    def call_tool(self, name, args):
        self.calls.append((name, args))
        return {"content": [{"type": "text", "text": "ok:" + json.dumps(args)}]}


class Allow:
    def approve(self, call, tool=None):
        return True, ""


def test_small_toolsets_keep_full_schemas():
    one = M.tools_prompt(Box().tools[:1], ["*"], lazy=True)
    assert "inputSchema:" in one and "load_tools" not in one


def test_index_has_no_schemas():
    many = Box().tools * 2 + [{"name": f"t{i}", "description": "d"} for i in range(3)]
    s = M.tools_prompt(many, ["*"], lazy=True)
    assert "quill_gmail" in s and "inputSchema:" not in s and "load_tools" in s
    full = M.tools_prompt(Box().tools, ["*"])
    assert "inputSchema:" in full


def test_load_then_call_does_not_use_a_step():
    box = Box()
    replies = iter([
        '<tool_call>{"name": "load_tools", "arguments": {"names": ["quill_gmail", "nope_tool"]}}</tool_call>',
        '<tool_call>{"name": "quill_gmail", "arguments": {"action": "list_unread"}}</tool_call>',
        "Done.",
    ])
    seen = []

    def chat(hist):
        seen.append(hist[-1]["content"] if hist else "")
        return next(replies), True
    reply, trace = M.run_tool_loop(chat, [{"role": "user", "content": "check mail"}], box, Allow(), max_steps=1)
    assert reply == "Done."
    assert box.calls == [("quill_gmail", {"action": "list_unread"})]
    assert "inputSchema" in seen[1] and "Unknown tool 'nope_tool'" in seen[1]
    assert trace[0]["loaded"] == ["quill_gmail"]


def test_bad_args_return_definition():
    box = Box()
    replies = iter(['<tool_call>{"name": "quill_gmail", "arguments": {}}</tool_call>', "ok"])
    seen = []

    def chat(hist):
        seen.append(hist[-1]["content"])
        return next(replies), True
    M.run_tool_loop(chat, [{"role": "user", "content": "x"}], box, Allow())
    assert "inputSchema" in seen[1] and box.calls == []


def test_load_names_string_forms():
    assert M._load_names({"names": "a, b"}) == ["a", "b"]
    assert M._load_names({"names": '["a"]'}) == ["a"]
    assert M._load_names({"name": "a"}) == ["a"]


def test_embed_cooldown_skips_provider():
    from nimlab.memory import MemoryCore as Memory
    calls = []

    class E:
        label = "x"

        def embed(self, t, it):
            calls.append(t)
            raise TimeoutError("timed out")
    m = Memory.__new__(Memory)
    m.settings = {"embedding": {"cooldown_sec": 60}}
    m._embedder_given = E()
    m.warn = lambda *a: None
    assert m.embed("a", "query") is None and m.embed("b", "query") is None
    assert calls == ["a"]
    m2 = Memory.__new__(Memory)
    m2.settings = {"embedding": {}}
    m2._embedder_given = E()
    m2.warn = lambda *a: None
    m2.embed("a", "query"); m2.embed("b", "query")
    assert calls == ["a", "a", "b"]


def test_glm_style_calls_parse():
    calls = M.parse_tool_calls('x<tool_call>get_system_stats<arg_key>include_processes</arg_key>'
                               '<arg_value>false</arg_value></tool_call>')
    assert calls[0].name == "get_system_stats"
    assert M.coerce_kv_arguments({"properties": {"include_processes": {"type": "boolean"}}},
                                 calls[0].arguments) == {"include_processes": False}
    assert M.coerce_kv_arguments({"properties": {"uid": {"type": "string"}, "n": {"type": "integer"}}},
                                 {"uid": "123", "n": "5", "x": "[1]"}) == {"uid": "123", "n": 5, "x": [1]}
    calls = M.parse_tool_calls('<tool_call>terminal<arg_key>command</arg_key><arg_value>free -m</arg_value></tool_call>')
    assert calls[0].arguments == {"command": "free -m"}
    calls = M.parse_tool_calls('<tool_call>get_me</tool_call>')
    assert calls[0].name == "get_me" and calls[0].arguments == {}
    bad = M.parse_tool_calls('<tool_call>get_me<arg_key>a</arg_value>1</arg_value></tool_call>')
    assert isinstance(bad[0], M.ToolCallError)


def test_model_params_merge():
    from nimlab.api import NimClient
    sent = []

    class H:
        def request(self, *a, **k):
            raise AssertionError

    c = NimClient.__new__(NimClient)
    c.cluster = {"model_params": {"m/x": {"reasoning_effort": "low"}}}
    assert c.model_params("m/x") == {"reasoning_effort": "low"} and c.model_params("m/y") == {}
    c.cluster = {}
    assert c.model_params("m/x") == {}


def test_load_tools_alone_does_not_satisfy_require_tool():
    from nimlab import scheduler as S

    class Ctx:
        def quill_task(self, a, who=None, timeout=None):
            return {"ok": True, "text": "played", "present": ["beat_lab"], "missing": [],
                    "trace": [{"name": "load_tools", "outcome": "ok"}]}
    a = {"prompt": "p", "tools": ["beat_lab"], "only": True, "require_tool": True}
    r = S.run_task(a, Ctx(), name="free-time", timeout=30)
    assert r.ok is False

