#!/usr/bin/env python3
"""
Tell Lumenis - Send a single message and get response
"""

import asyncio
import json
import sys
import websockets

LUMENIS_WS = "ws://localhost:8000/ws"

async def tell_lumenis(message: str):
    """Send a message to Lumenis and wait for complete response"""
    print(f"\n{'='*70}")
    print("SENDING TO LUMENIS:")
    print(f"{'='*70}")
    print(f"{message}\n")
    print(f"{'='*70}")
    print("LUMENIS RESPONSE:")
    print(f"{'='*70}\n")

    async with websockets.connect(LUMENIS_WS) as ws:
        # Send message
        await ws.send(json.dumps({
            "type": "chat",
            "message": message,
            "session_id": None,
        }))

        # Collect response
        response_text = ""

        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            event = msg.get("type")

            if event == "response_chunk":
                chunk = msg.get("text", "")
                response_text += chunk
                print(chunk, end="", flush=True)

            elif event == "processing_done":
                meta = msg.get("meta", {})
                print(f"\n\n{'='*70}")
                print(f"Intent: {meta.get('intent', 'unknown')}")
                print(f"Risk Level: {meta.get('risk_level', 'unknown')}")
                print(f"Seats Activated: {', '.join(meta.get('seats_activated', []))}")
                print(f"{'='*70}\n")
                break

            elif event == "error":
                print(f"\nERROR: {msg.get('message')}\n")
                break

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tell_lumenis.py \"your message here\"")
        sys.exit(1)

    message = " ".join(sys.argv[1:])

    # Check if server is running
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:8000/api/status", timeout=3)
    except Exception:
        print("[ERROR] Lumenis server is not running on port 8000")
        sys.exit(1)

    await tell_lumenis(message)

if __name__ == "__main__":
    asyncio.run(main())
