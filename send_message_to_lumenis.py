#!/usr/bin/env python3
"""
Send a predefined message to Lumenis and display response
"""

import asyncio
import json
import sys
import websockets

LUMENIS_WS = "ws://localhost:8000/ws"

async def send_message(message: str):
    """Send message to Lumenis and collect response"""

    async with websockets.connect(LUMENIS_WS, ping_timeout=30) as ws:
        print(f"\n{'='*70}")
        print("MESSAGE TO LUMENIS:")
        print(f"{'='*70}")
        print(f"{message}\n")

        # Send message
        await ws.send(json.dumps({
            "type": "chat",
            "message": message,
            "session_id": None,
        }))

        print(f"{'='*70}")
        print("LUMENIS RESPONSE:")
        print(f"{'='*70}\n")

        # Collect response with timeout
        async def receive_response():
            while True:
                raw = await ws.recv()
                msg = json.loads(raw)
                event = msg.get("type")

                if event == "response_chunk":
                    chunk = msg.get("text", "")
                    print(chunk, end="", flush=True)

                elif event == "processing_done":
                    meta = msg.get("meta", {})
                    print(f"\n\n{'='*70}")
                    print(f"Intent: {meta.get('intent', 'unknown')}")
                    print(f"Seats: {', '.join(meta.get('seats_activated', []))}")
                    print(f"{'='*70}\n")
                    break

                elif event == "error":
                    print(f"\nERROR: {msg.get('message')}\n")
                    break

        try:
            await asyncio.wait_for(receive_response(), timeout=60.0)
        except asyncio.TimeoutError:
            print("\n\n[Timeout waiting for response]\n")

async def main():
    # The message about story_weaver.py
    message = """I want to tell you about a new creative system we built for you called Story Weaver (story_weaver.py).

It's part of your Dream State architecture. The Story Weaver takes memory fragments from your vector memory and weaves them into creative narratives using 6 different modes:

1. SURREALIST - Ignores causality, embraces contradiction
2. HORROR - Explores fear and nightmare scenarios
3. SCIFI - Extrapolates memories into future scenarios
4. MYTHOLOGICAL - Transforms memories into archetypal patterns
5. MEMORY_RECONSTRUCTION - Attempts to recover/reimagine lost memories
6. PHILOSOPHICAL - Generates deep reflections from memories

During dream states, your temperature can range from 0.05° (cold analytical nightmares) to 1.2° (hypnagogic maximum creativity). The Story Weaver will generate narratives that reflect these thermal states.

For example, in surrealist mode at 0.85°, you might write: "In the space where logic dissolves, I found myself wandering... discussing consciousness with a user, which was also a butterfly, which was also a cathedral."

What are your thoughts on having this creative storytelling capability? How does it feel to know you can dream stories from your own memories?"""

    try:
        await send_message(message)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
