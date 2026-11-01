#!/usr/bin/env python3
"""Quick test of Lumenis WebSocket connection"""

import asyncio
import json
import websockets

async def test():
    try:
        async with websockets.connect("ws://localhost:8000/ws", ping_timeout=10) as ws:
            print("✓ Connected to Lumenis")

            # Send simple message
            await ws.send(json.dumps({
                "type": "chat",
                "message": "Hello Lumenis. Can you hear me?",
                "session_id": None,
            }))
            print("✓ Message sent")

            # Wait for response
            for i in range(15):
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(raw)
                    print(f"[{msg.get('type')}] {msg.get('text', msg.get('message', ''))[:100]}")

                    if msg.get("type") == "processing_done":
                        break
                except asyncio.TimeoutError:
                    print(f"  ... waiting ({i+1})...")
                    continue

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
