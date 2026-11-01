#!/usr/bin/env python3
"""Quick test of Lumenis with new API key"""
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri, ping_interval=20) as ws:
        print("✓ Connected to Lumenis\n")

        # Get init
        init = await ws.recv()
        init_data = json.loads(init)
        print(f"Reactor: {init_data.get('data', {}).get('reactor', {})}\n")

        # Send simple test
        print("Sending test message...\n")
        await ws.send("Hello Lumenis! Can you hear me with the new NVIDIA API key? Just say hi!")

        print("Response:\n")
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(msg)

                if data.get("type") == "delta":
                    print(data.get("data", {}).get("token", ""), end="", flush=True)
                elif data.get("type") == "done":
                    print(f"\n\n✓ Done ({data.get('data', {}).get('tokens', 0)} tokens)")
                    break
                elif data.get("type") == "error":
                    print(f"\n✗ Error: {data.get('data', {}).get('error', 'Unknown')}")
                    break
        except asyncio.TimeoutError:
            print("\n⏱️  Timeout")

asyncio.run(test())
