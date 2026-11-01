#!/usr/bin/env python3
"""Quick test of Lumenis WebSocket connection - FIXED"""

import asyncio
import json
import websockets

async def test():
    try:
        async with websockets.connect("ws://localhost:8000/ws", ping_timeout=30) as ws:
            print("✓ Connected to Lumenis")

            # Receive init message
            init = await ws.recv()
            print(f"✓ Received init: {json.loads(init)['type']}")

            # Send simple message with CORRECT format (action, not type)
            await ws.send(json.dumps({
                "action": "chat",  # FIXED: was "type"
                "message": "Hello Lumenis. This is a test message about One2lvOS.",
                "session_id": None,
            }))
            print("✓ Message sent")

            # Wait for response
            timeout_count = 0
            while timeout_count < 60:  # 120 second total timeout
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(raw)
                    msg_type = msg.get('type')

                    if msg_type == "pulse":
                        print(".", end="", flush=True)
                    elif msg_type == "response_chunk":
                        print(msg.get('text', ''), end="", flush=True)
                    elif msg_type == "processing_done":
                        print(f"\n\n✓ Processing complete!")
                        print(f"  Intent: {msg.get('meta', {}).get('intent')}")
                        print(f"  Seats: {msg.get('meta', {}).get('seats_activated')}")
                        break
                    elif msg_type == "error":
                        print(f"\n✗ Error: {msg.get('message')}")
                        break
                    elif msg_type == "processing_start":
                        print("\n✓ Processing started...")
                    elif msg_type == "session_created":
                        print(f"✓ Session created: {msg.get('session_id')}")
                    elif msg_type == "seat_activity":
                        print(f"\n  [{msg.get('seat')}]: {msg.get('text', '')[:80]}")
                    else:
                        print(f"\n  [{msg_type}]")

                except asyncio.TimeoutError:
                    timeout_count += 1
                    if timeout_count % 10 == 0:
                        print(f"\n  ... waiting ({timeout_count*2}s)...")
                    continue

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
