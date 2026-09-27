#!/usr/bin/env python3
"""
Setup new Astra DB collection for Nemotron embeddings (2048 dimensions)
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from astrapy import DataAPIClient

load_dotenv('.env.master')

ASTRA_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
NEW_COLLECTION = os.getenv("COLLECTION_NAME", "aria_memory_v2")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "2048"))

def main():
    print("═══════════════════════════════════════════════════════════")
    print("   Setup Nemotron Collection")
    print("═══════════════════════════════════════════════════════════")
    print()
    print(f"Collection: {NEW_COLLECTION}")
    print(f"Dimensions: {VECTOR_DIM}")
    print()

    if not all([ASTRA_ENDPOINT, ASTRA_TOKEN]):
        print("❌ Missing environment variables!")
        sys.exit(1)

    try:
        client = DataAPIClient(ASTRA_TOKEN)
        db = client.get_database_by_api_endpoint(ASTRA_ENDPOINT)
        print("✅ Connected to Astra DB")

        # Check if collection exists
        try:
            collection = db.get_collection(NEW_COLLECTION)
            print(f"✅ Collection '{NEW_COLLECTION}' already exists")
            print(f"   Dimensions: {VECTOR_DIM}")
        except Exception:
            # Create new collection
            print(f"🔧 Creating collection '{NEW_COLLECTION}'...")
            collection = db.create_collection(
                NEW_COLLECTION,
                dimension=VECTOR_DIM,
                metric="cosine"
            )
            print(f"✅ Collection created successfully!")

        print()
        print("═══════════════════════════════════════════════════════════")
        print("   ✅ Setup Complete!")
        print("═══════════════════════════════════════════════════════════")
        print()
        print(f"Collection: {NEW_COLLECTION}")
        print(f"Dimensions: {VECTOR_DIM}")
        print(f"Metric: cosine")
        print(f"Embedding Model: nvidia/nemotron-3-embed-1b")
        print()
        print("Next: Deploy system with ./deploy-sovereign.sh")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
