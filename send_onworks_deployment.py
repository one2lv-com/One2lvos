#!/usr/bin/env python3
"""
Send OnWorks deployment message to Lumenis
"""

import asyncio
import websockets
import json

async def send_message():
    uri = "ws://localhost:8000/ws"

    message = """Boot OnWorks and deploy the semantic layer:

1. Launch OnWorks Ubuntu instance (use saved image if available)
2. Set admin password with: sudo passwd admin
3. Open terminal in OnWorks
4. Run this deployment command:
   bash <(curl -s https://raw.githubusercontent.com/one2lv-com/One2lvos/main/semantic_layer/deploy_to_onworks.sh)
5. Then configure .env with Astra DB credentials
6. Load ontologies: cd semantic_layer && python3 semantic_cli.py load
7. Verify deployment: python3 semantic_cli.py list agents

The semantic layer includes:
- RDF/OWL ontologies (46 triples)
- Knowledge graph in Astra DB
- Lumenis design system
- CSS analyzer
- Web technology ontology

Please proceed with the deployment!"""

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to Lumenis")
            print(f"Sending: {message[:100]}...")

            await websocket.send(json.dumps({"message": message}))

            print("\nWaiting for response...")
            async for response in websocket:
                data = json.loads(response)

                if data.get("type") == "message":
                    print(f"\nLumenis: {data.get('content', '')}")

                elif data.get("type") == "done":
                    print("\n✓ Response complete")
                    break

    except Exception as e:
        print(f"Error: {e}")
        print("\nAlternative: Deploy manually to OnWorks")
        print("Run in OnWorks terminal:")
        print("  bash <(curl -s https://raw.githubusercontent.com/one2lv-com/One2lvos/main/semantic_layer/deploy_to_onworks.sh)")

if __name__ == "__main__":
    asyncio.run(send_message())
