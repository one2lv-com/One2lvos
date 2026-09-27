#!/usr/bin/env python3
"""
Create a memory entry in Astra DB about the environment configuration setup.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from astrapy import DataAPIClient
from openai import OpenAI

# Load environment variables
load_dotenv('.env.master')

# Configuration
ASTRA_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
NVIDIA_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE = os.getenv("NVIDIA_BASE_URL")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/nv-embed-v2")
COLLECTION = os.getenv("COLLECTION_NAME", "aria_memory")

# Memory content
MEMORY_CONTENT = """ONE2LVOS Environment Configuration Setup - 2026-09-27

PROJECT SETUP:
- Repository: github.com/one2lv-com/One2lvos
- Master environment file created: .env.master (34 variables)
- Git protection enabled: All .env files excluded from version control
- Deployment script configured to use .env.master automatically

ENVIRONMENT CONFIGURATION:
L1 Memory (Astra DB):
- Database: one2lvOS (9b5b1939-fd21-477d-95b8-a1aecc5f90b9)
- Region: AWS us-east-2
- Keyspace: one2lvOS
- Collection: aria_memory (1024-dim vectors)
- Status: ACTIVE

L2 Skills (NVIDIA AI):
- Primary API configured with 6 different API keys
- Embedding Model: nvidia/nv-embedqa-e5-v5
- LLM Model: nvidia/llama-3.3-nemotron-super-49b-v1
- Base URL: https://integrate.api.nvidia.com/v1

External Gateways:
- Discord bot configured (Channel ID: 719260428836012032)
- Twitch integration (Channel: one2lv)
- Supabase database connected
- Maton API integration
- GitHub token configured

SECURITY MEASURES:
✓ .env.master protected in .gitignore
✓ No hardcoded credentials in deployment scripts
✓ Runtime directories excluded from git
✓ Automatic credential copying during deployment
✓ Separation of configuration and code

DEPLOYMENT:
- Script: deploy-sovereign.sh
- Automatically uses .env.master if present
- Creates ∆Gemini_Root∆ and ∆Gemini_Memory∆ directories
- Starts Lumenis Reactor Core (Python FastAPI) on port 8000
- Starts Infinity Glasses HUD (Node.js Express) on port 4000
- Integrates with One2lvOS browser interface

DOCUMENTATION CREATED:
- SOVEREIGN_ARCHITECTURE.md - System architecture
- DEPLOYMENT_GUIDE.md - Production deployment
- QUICKSTART_SOVEREIGN.md - 5-minute quick start
- ENV_SETUP.md - Environment configuration guide
- ASTRA_CLI_GUIDE.md - Database CLI reference
- SETUP_COMPLETE.md - Setup verification
- INTEGRATION_SUMMARY.md - Integration overview

STATUS: Ready for deployment
"""

def create_embedding(text):
    """Generate embedding using NVIDIA API"""
    client = OpenAI(api_key=NVIDIA_KEY, base_url=NVIDIA_BASE)
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding

def store_memory():
    """Store memory in Astra DB"""
    print("🔄 Connecting to Astra DB...")

    # Initialize Astra DB client
    client = DataAPIClient(ASTRA_TOKEN)
    db = client.get_database_by_api_endpoint(ASTRA_ENDPOINT)

    # Get or create collection
    try:
        collection = db.get_collection(COLLECTION)
        print(f"✅ Connected to collection: {COLLECTION}")
    except Exception as e:
        print(f"⚠️  Collection not found, creating...")
        collection = db.create_collection(
            COLLECTION,
            dimension=1024,
            metric="cosine"
        )
        print(f"✅ Created collection: {COLLECTION}")

    # Generate embedding
    print("🔄 Generating vector embedding...")
    vector = create_embedding(MEMORY_CONTENT)
    print(f"✅ Generated {len(vector)}-dimensional embedding")

    # Create memory document
    memory_doc = {
        "$vector": vector,
        "content": MEMORY_CONTENT,
        "type": "system_configuration",
        "category": "environment_setup",
        "timestamp": datetime.utcnow().isoformat(),
        "project": "One2lvOS",
        "version": "1.0.0",
        "tags": [
            "configuration",
            "environment",
            "deployment",
            "security",
            "astra_db",
            "nvidia_ai",
            "sovereign_architecture"
        ],
        "metadata": {
            "credentials_count": 34,
            "services": [
                "Astra DB",
                "NVIDIA AI",
                "Discord",
                "Twitch",
                "Supabase",
                "Maton",
                "GitHub"
            ],
            "deployment_ready": True,
            "git_protected": True
        }
    }

    # Insert into Astra DB
    print("🔄 Inserting memory into Astra DB...")
    result = collection.insert_one(memory_doc)
    print(f"✅ Memory stored successfully!")
    print(f"   Document ID: {result.inserted_id}")

    # Verify insertion
    print("\n🔍 Verifying memory storage...")
    test_query = "ONE2LVOS environment configuration"
    test_vector = create_embedding(test_query)

    results = list(collection.find(
        {},
        sort={"$vector": test_vector},
        limit=1,
        projection={"content": 1, "$similarity": 1}
    ))

    if results:
        print(f"✅ Verification successful!")
        print(f"   Similarity score: {results[0].get('$similarity', 0):.4f}")
        print(f"   Content preview: {results[0]['content'][:100]}...")
    else:
        print("⚠️  Verification failed - no results returned")

    return result

def main():
    """Main execution"""
    print("═══════════════════════════════════════════════════════════")
    print("   ONE2LVOS - Astra DB Memory Creation")
    print("═══════════════════════════════════════════════════════════")
    print()

    # Verify environment variables
    if not all([ASTRA_ENDPOINT, ASTRA_TOKEN, NVIDIA_KEY]):
        print("❌ Missing required environment variables!")
        print("   Make sure .env.master exists and contains:")
        print("   - ASTRA_DB_API_ENDPOINT")
        print("   - ASTRA_DB_APPLICATION_TOKEN")
        print("   - NVIDIA_API_KEY")
        sys.exit(1)

    print("✅ Environment variables loaded")
    print(f"   Astra DB: {ASTRA_ENDPOINT[:50]}...")
    print(f"   Collection: {COLLECTION}")
    print(f"   Embedding Model: {EMBED_MODEL}")
    print()

    try:
        store_memory()
        print()
        print("═══════════════════════════════════════════════════════════")
        print("   ✅ Memory Creation Complete!")
        print("═══════════════════════════════════════════════════════════")
        print()
        print("The environment configuration has been stored in Astra DB")
        print("and can now be recalled through vector similarity search.")
        print()
    except Exception as e:
        print()
        print("═══════════════════════════════════════════════════════════")
        print("   ❌ Error Creating Memory")
        print("═══════════════════════════════════════════════════════════")
        print(f"Error: {str(e)}")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
