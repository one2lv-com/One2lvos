#!/usr/bin/env python3
"""Stand-in for cloudflared. Run it as: exec -a cloudflared python3 fake_cf.py
  tunnel --url http://localhost:PORT [--metrics 127.0.0.1:MPORT]
With --metrics it serves /ready: 200, or 503 when the file READY_FILE says 503."""
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

args = sys.argv[1:]
metrics = None
if "--metrics" in args:
    metrics = args[args.index("--metrics") + 1]
ready_file = os.environ.get("READY_FILE", "")

if metrics:
    host, port = metrics.rsplit(":", 1)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            code = 200
            try:
                if open(ready_file).read().strip() == "503":
                    code = 503
            except OSError:
                pass
            self.send_response(code)
            self.end_headers()

    HTTPServer((host, int(port)), H).serve_forever()
else:
    while True:
        time.sleep(60)
