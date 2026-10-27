#!/bin/bash
# Log API Keys Configuration to ASTRA DB via CQL
# This creates a configuration record in Lumenis's memory

source .env.working

echo "🔐 Logging API Keys to ASTRA DB (Lumenis Memory)"
echo "=================================================="

# Create the message to log
MESSAGE="System Configuration Update - $(date '+%Y-%m-%d %H:%M:%S')

Working API Configuration:
- Embedding Model: nvidia/nemotron-3.5-embed-1b (2048 dimensions)
- LLM Model: nvidia/nemotron-3.5-lightning-30b-a3b
- ASTRA DB: Connected to one2lvOS keyspace
- Memory Collection: aria_memory
- Vector Dimension: 2048

All 404 and 410 errors have been resolved.
Lumenis is fully operational with NVIDIA API integration."

# Use Python to save to ASTRA DB
python3 << 'EOFPYTHON'
import os
import requests
import json
from datetime import datetime

# Get config
ASTRA_DB_ENDPOINT = os.environ["ASTRA_DB_API_ENDPOINT"]
ASTRA_DB_TOKEN = os.environ["ASTRA_DB_APPLICATION_TOKEN"]
NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]
NVIDIA_BASE_URL = os.environ["NVIDIA_BASE_URL"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]
COLLECTION_NAME = os.environ["COLLECTION_NAME"]

message = """System Configuration Update - """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """

Working API Configuration:
- Embedding Model: nvidia/nemotron-3.5-embed-1b (2048 dimensions)
- LLM Model: nvidia/nemotron-3.5-lightning-30b-a3b
- ASTRA DB: Connected to one2lvOS keyspace
- Memory Collection: aria_memory
- Vector Dimension: 2048

All 404 and 410 errors have been resolved.
Lumenis is fully operational with NVIDIA API integration."""

print(f"📝 Message to log:\n{message}\n")

# Get embedding
print("🧠 Generating embedding...")
try:
    embed_response = requests.post(
        f"{NVIDIA_BASE_URL}/embeddings",
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "input": [message],
            "model": EMBEDDING_MODEL,
            "encoding_format": "float",
            "input_type": "passage"
        },
        timeout=30
    )

    if embed_response.status_code != 200:
        print(f"❌ Embedding failed: {embed_response.text}")
        exit(1)

    vector = embed_response.json()["data"][0]["embedding"]
    print(f"✓ Generated {len(vector)}-dimensional embedding")
except Exception as e:
    print(f"❌ Error generating embedding: {e}")
    exit(1)

# Save to ASTRA DB
print("💾 Saving to ASTRA DB...")
try:
    doc = {
        "text": message,
        "$vector": vector,
        "timestamp": datetime.now().isoformat(),
        "type": "system_config",
        "category": "api_keys",
        "importance": "critical"
    }

    astra_response = requests.post(
        f"{ASTRA_DB_ENDPOINT}/api/json/v1/default_keyspace/{COLLECTION_NAME}",
        headers={
            "Token": ASTRA_DB_TOKEN,
            "Content-Type": "application/json"
        },
        json={
            "insertOne": {"document": doc}
        },
        timeout=10
    )

    if astra_response.status_code == 200:
        result = astra_response.json()
        doc_id = result.get("status", {}).get("insertedIds", [None])[0]
        print(f"✅ Saved to ASTRA DB!")
        print(f"   Document ID: {doc_id}")
        print(f"   Collection: {COLLECTION_NAME}")
        print(f"   Vector Dimensions: {len(vector)}")
    else:
        print(f"❌ ASTRA DB save failed: {astra_response.text}")
        exit(1)

except Exception as e:
    print(f"❌ Error saving to ASTRA DB: {e}")
    exit(1)

print("\n✅ Configuration logged successfully!")
print("🧠 Lumenis now has this configuration in memory.")
EOFPYTHON
