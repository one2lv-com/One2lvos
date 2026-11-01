#!/usr/bin/env python3
"""
Verify and display memories from Astra DB
"""
import os
from dotenv import load_dotenv
from astrapy import DataAPIClient

load_dotenv('.env.master')

ASTRA_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
COLLECTION = os.getenv("COLLECTION_NAME", "aria_memory")

client = DataAPIClient(ASTRA_TOKEN)
db = client.get_database_by_api_endpoint(ASTRA_ENDPOINT)
collection = db.get_collection(COLLECTION)

print("═══════════════════════════════════════════════════════════")
print("   Astra DB Memory Verification")
print("═══════════════════════════════════════════════════════════")
print()

# Find recent memories
results = list(collection.find(
    {"type": "system_configuration"},
    projection={"content": 1, "timestamp": 1, "tags": 1, "metadata": 1},
    limit=5
))

if results:
    print(f"✅ Found {len(results)} system configuration memor{'y' if len(results) == 1 else 'ies'}")
    print()

    for i, mem in enumerate(results, 1):
        print(f"Memory #{i}:")
        print(f"  ID: {mem.get('_id', 'N/A')}")
        print(f"  Timestamp: {mem.get('timestamp', 'N/A')}")
        print(f"  Tags: {', '.join(mem.get('tags', []))}")
        print(f"  Content preview: {mem.get('content', '')[:150]}...")

        metadata = mem.get('metadata', {})
        if metadata:
            print(f"  Metadata:")
            for key, value in metadata.items():
                print(f"    - {key}: {value}")
        print()
else:
    print("⚠️  No system configuration memories found")

print("═══════════════════════════════════════════════════════════")
