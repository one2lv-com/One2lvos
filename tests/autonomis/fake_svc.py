#!/usr/bin/env python3
"""Fake HTTP service for the Autonomis tests.

usage: fake_svc.py PORT MODEFILE
MODEFILE holds: ok | 500 | text | hang | 404
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
MODEFILE = sys.argv[2]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        try:
            mode = open(MODEFILE).read().strip()
        except OSError:
            mode = "ok"
        if mode == "hang":
            time.sleep(30)
            return
        if mode == "500":
            code, body, ctype = 500, b"boom", "text/plain"
        elif mode == "404":
            code, body, ctype = 404, b"nope", "text/plain"
        elif mode == "text":
            code, body, ctype = 200, b"hello", "text/plain"
        else:
            code = 200
            body = json.dumps({"status": "ok", "bridge": "ok", "reactor": {}}).encode()
            ctype = "application/json"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
