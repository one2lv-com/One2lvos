#!/usr/bin/env python3
"""
One2lvOS Development Server
Simple HTTP server for local development
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).parent

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        # Enable CORS for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        # Cache control
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    print(f"""
╔═══════════════════════════════════════════╗
║         One2lvOS Development Server       ║
╚═══════════════════════════════════════════╝

Starting server at http://localhost:{PORT}

Press Ctrl+C to stop
""")

    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        print(f"→ Server running at: http://localhost:{PORT}")
        print(f"→ Serving from: {DIRECTORY}")
        print()

        # Open browser automatically
        try:
            webbrowser.open(f'http://localhost:{PORT}')
            print("✓ Browser opened automatically")
        except Exception as e:
            print(f"! Could not open browser: {e}")
            print(f"  Please open http://localhost:{PORT} manually")

        print()
        print("=" * 50)
        print()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✓ Server stopped")
            print("Thank you for using One2lvOS!\n")

if __name__ == "__main__":
    main()
