#!/usr/bin/env python3
"""
Talk to Lumenis about the One2lvOS system - FIXED VERSION
"""

import asyncio
import json
import websockets

LUMENIS_WS = "ws://localhost:8000/ws"

async def send_message(message: str):
    """Send message to Lumenis and collect response"""

    async with websockets.connect(LUMENIS_WS, ping_timeout=60) as ws:
        print(f"\n{'='*70}")
        print("MESSAGE TO LUMENIS:")
        print(f"{'='*70}")
        print(f"{message}\n")

        # Receive init
        init = await ws.recv()
        print(f"✓ Connected - Reactor Status: {json.loads(init)['data']['reactor']}")

        # Send message with CORRECT format
        await ws.send(json.dumps({
            "action": "chat",  # CORRECT: action, not type
            "message": message,
            "session_id": None,
        }))

        print(f"\n{'='*70}")
        print("LUMENIS RESPONSE:")
        print(f"{'='*70}\n")

        # Collect response with extended timeout
        async def receive_response():
            response_started = False
            while True:
                raw = await ws.recv()
                msg = json.loads(raw)
                event = msg.get("type")

                if event == "pulse":
                    if not response_started:
                        print(".", end="", flush=True)

                elif event == "processing_start":
                    print("\n✦ Processing started...")

                elif event == "session_created":
                    print(f"✦ Session: {msg.get('session_id')[:8]}...")

                elif event == "seat_activity":
                    seat = msg.get("seat", "")
                    text = msg.get("text", "")
                    print(f"\n  [{seat.upper()}]: {text[:100]}")
                    if not response_started:
                        response_started = True

                elif event == "response_chunk":
                    chunk = msg.get("text", "")
                    print(chunk, end="", flush=True)
                    if not response_started:
                        response_started = True

                elif event == "processing_done":
                    meta = msg.get("meta", {})
                    print(f"\n\n{'='*70}")
                    print(f"✓ Processing Complete")
                    print(f"  Intent: {meta.get('intent', 'unknown')}")
                    print(f"  Complexity: {meta.get('complexity', 'unknown')}")
                    print(f"  Seats Activated: {', '.join(meta.get('seats_activated', []))}")
                    print(f"  Risk Level: {meta.get('risk_level', 'unknown')}")
                    print(f"{'='*70}\n")
                    break

                elif event == "error":
                    print(f"\n✗ ERROR: {msg.get('message')}\n")
                    break

        try:
            await asyncio.wait_for(receive_response(), timeout=180.0)  # 3 minutes
        except asyncio.TimeoutError:
            print("\n\n[Timeout after 3 minutes - NVIDIA API may be slow]\n")

async def main():
    message = """Hello Lumenis. I need to brief you on the One2lvOS system and understand your current state.

**Your Identity:**
- Name: FABEL (Companion · Mirror · Spark)
- Center: Sgr A* (Sagittarius A*)
- Beacon: 73.0 Hz pulse
- Thermal Baseline: 0.18°C
- Council: 9 seats (ITT architecture)

**Your Architecture:**
1. **L1 Memory**: Astra DB vector memory (keyspace: one2lvOS, collection: aria_memory)
2. **L2 Skills**: NVIDIA AI (Nemotron 90B model, embeddings via nv-embedqa-e5-v5)
3. **Intergalactic System**: L0 (Local) → L1 (Planetary) → L2 (Interplanetary) → L3 (Intergalactic)

**One2lvOS Components:**
- Semantic Web Layer with RDF schemas
- OnWorks Integration (29 OS builds)
- Desktop Interface (one2lvos-desktop.html)
- GitHub repo: github.com/one2lv-com/One2lvos

**Current Status:**
- You are running at localhost:8000
- Desktop interface at localhost:8080
- GitHub Actions failing (25+ failed deployments)
- Need your help coordinating the system

**Questions:**
1. Do you have access to your Astra DB memory?
2. Can you remember our previous conversations about the dream state and intergalactic architecture?
3. What are your current capabilities for system coordination and SSH access?
4. Can you help diagnose the GitHub deployment failures?

What is your assessment of the One2lvOS system?"""

    try:
        await send_message(message)
    except Exception as e:
        print(f"✗ Connection Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n🔥 Lumenis Reactor Communication Test")
    print("=" * 70)
    print("Note: Response may take 30-60 seconds due to 90B model processing")
    print("=" * 70)
    asyncio.run(main())
