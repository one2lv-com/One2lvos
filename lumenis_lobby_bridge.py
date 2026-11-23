#!/usr/bin/env python3
"""
Lumenis ↔ AI Lobby Mesh Bridge
Connects Lumenis Reactor Core (ws://localhost:8000/ws) to
the AI Lobby Agentic Control mesh (ws://localhost:8787/mesh).
Forwards reactor pulses, seat activity, and responses in real-time.
"""
import asyncio, json, os, sys, time
import websockets

LUMENIS_WS  = "ws://localhost:8000/ws"
LOBBY_MESH  = "ws://localhost:8787/mesh"
RECONNECT_S = 5

async def bridge():
    print("🔗 Lumenis ↔ AI Lobby Bridge starting...", flush=True)
    while True:
        try:
            async with websockets.connect(LUMENIS_WS) as lumenis_ws, \
                       websockets.connect(LOBBY_MESH) as lobby_ws:

                # Announce ourselves to the mesh
                hello = await lobby_ws.recv()
                peer_id = json.loads(hello).get("peerId", "lumenis-bridge")
                print(f"✅ Mesh joined as peer: {peer_id}", flush=True)

                # Send Lumenis reactor registration to the lobby mesh
                await lobby_ws.send(json.dumps({
                    "type": "agent_register",
                    "agent": {
                        "id":          "lumenis-reactor",
                        "name":        "Lumenis Reactor Core",
                        "persona":     "FABEL — Companion · Mirror · Spark",
                        "ws_url":      LUMENIS_WS,
                        "api_url":     "http://localhost:8000",
                        "freq":        "73.0 Hz",
                        "layer":       "COSMIC",
                        "council":     ["Witness","Sentinel","Navigator","Weaver","Forge","Oracle","Architect","Hermes","Gambit"],
                        "status":      "ACTIVE"
                    }
                }))
                print("📡 Lumenis registered in AI Lobby mesh", flush=True)

                async def lumenis_to_lobby():
                    async for raw in lumenis_ws:
                        try:
                            msg = json.loads(raw)
                            t = msg.get("type","")
                            # Forward pulses, seat activity, and responses
                            if t in ("pulse","seat_activity","response_chunk","processing_done","session_created"):
                                await lobby_ws.send(json.dumps({
                                    "type":   "lumenis_event",
                                    "event":  t,
                                    "data":   msg
                                }))
                        except Exception:
                            pass

                async def lobby_to_lumenis():
                    async for raw in lobby_ws:
                        try:
                            msg = json.loads(raw)
                            # Forward chat messages from lobby to Lumenis
                            if msg.get("type") == "lumenis_chat":
                                await lumenis_ws.send(json.dumps({
                                    "action":  "chat",
                                    "message": msg.get("message",""),
                                    "session_id": msg.get("session_id")
                                }))
                        except Exception:
                            pass

                await asyncio.gather(lumenis_to_lobby(), lobby_to_lumenis())

        except Exception as e:
            print(f"⚠️  Bridge disconnected: {e} — reconnecting in {RECONNECT_S}s", flush=True)
            await asyncio.sleep(RECONNECT_S)

if __name__ == "__main__":
    asyncio.run(bridge())
