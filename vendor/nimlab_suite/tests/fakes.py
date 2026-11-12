"""Test doubles: a fake urlopen that serves scripted responses."""

import io
import json
import socket
import urllib.error


class FakeHeaders(dict):
    def items(self):
        return list(super().items())


class FakeResponse(io.BytesIO):
    def __init__(self, body=b"", status=200, headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        super().__init__(body)
        self.status = status
        self.headers = FakeHeaders(headers or {"Content-Type": "application/json"})

    def getcode(self):
        return self.status


def http_error(code, body=b"", headers=None):
    return urllib.error.HTTPError("http://x", code, "err", FakeHeaders(headers or {}), io.BytesIO(body))


class FakeOpener:
    """Callable replacing urllib.request.urlopen.

    script: list of items, each a FakeResponse, an Exception instance, or a
    callable(request) -> FakeResponse. Requests are recorded in .requests.
    """

    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append({"url": req.full_url, "method": req.get_method(), "headers": dict(req.header_items()),
                              "data": req.data, "timeout": timeout})
        if not self.script:
            raise AssertionError("unexpected extra request to " + req.full_url)
        item = self.script.pop(0)
        if callable(item) and not isinstance(item, FakeResponse):
            item = item(req)
        if isinstance(item, BaseException):
            raise item
        return item

    def header(self, i, name):
        h = {k.lower(): v for k, v in self.requests[i]["headers"].items()}
        return h.get(name.lower())

    def body(self, i):
        return json.loads(self.requests[i]["data"].decode())


def timeout_error():
    return socket.timeout("The read operation timed out")


def chat_body(text, usage=None):
    return {"choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": usage or {"completion_tokens": 10}}


class FakeMCPServer:
    """A fake streamable-HTTP MCP server (a urlopen replacement).

    tools: list of tool dicts (name, description, inputSchema).
    handlers: {tool_name: callable(arguments) -> MCP result dict}.
    Answers initialize, notifications/initialized, tools/list and
    tools/call; every tools/call is recorded in .calls.
    down=True makes every request fail like an unreachable host.
    """

    def __init__(self, tools, handlers=None, down=False):
        self.tools = tools
        self.handlers = handlers or {}
        self.down = down
        self.calls = []
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req.full_url)
        if self.down:
            raise urllib.error.URLError("[Errno 111] Connection refused")
        msg = json.loads(req.data.decode())
        method, rid = msg.get("method"), msg.get("id")
        if rid is None:
            return FakeResponse(b"", status=202)
        if method == "initialize":
            result = {"protocolVersion": "2025-03-26", "serverInfo": {"name": "fake-mcp"}, "capabilities": {}}
        elif method == "tools/list":
            result = {"tools": self.tools}
        elif method == "tools/call":
            name = msg["params"]["name"]
            args = msg["params"].get("arguments") or {}
            self.calls.append((name, args))
            fn = self.handlers.get(name)
            result = fn(args) if fn else {"content": [{"type": "text", "text": "ok"}]}
        else:
            return FakeResponse({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "no method"}})
        return FakeResponse({"jsonrpc": "2.0", "id": rid, "result": result})


class RouteOpener:
    """A urlopen replacement that answers by URL substring.

    routes: list of (substring, callable(request) -> FakeResponse | dict).
    The first matching route answers; requests are kept in .requests.
    """

    def __init__(self, routes):
        self.routes = list(routes)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append({"url": req.full_url, "method": req.get_method(), "headers": dict(req.header_items()),
                              "data": req.data})
        for sub, fn in self.routes:
            if sub in req.full_url:
                out = fn(req)
                if isinstance(out, BaseException):
                    raise out
                return out if isinstance(out, FakeResponse) else FakeResponse(out)
        raise AssertionError("no fake route for " + req.full_url)


def make_wav(seconds=4.0, rate=22050, channels=1, width=2):
    """A small sine-wave WAV in memory."""
    import math
    import struct
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(int(seconds * rate)):
            v = int(8000 * math.sin(2 * math.pi * 220 * i / rate))
            for _ in range(channels):
                if width == 2:
                    frames += struct.pack("<h", v)
                else:
                    frames += struct.pack("<B", (v >> 8) + 128)
        w.writeframes(bytes(frames))
    return buf.getvalue()
