#!/usr/bin/env python3
"""
Create a memory entry in Astra DB about the environment configuration setup.
Uses manual vector generation (random for now) since NVIDIA embedding model is deprecated.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from astrapy import DataAPIClient
import random

# Load environment variables
load_dotenv('.env.master')

# Configuration
ASTRA_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
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
- Embedding Model: nvidia/nv-embedqa-e5-v5 (deprecated - needs update)
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

ASTRA CLI INSTALLED:
- Version: 0.6
- Location: ~/.astra/cli
- Configured with token
- Database verified: one2lvOS ACTIVE

STATUS: Ready for deployment
NEXT STEP: Update embedding model to current NVIDIA model (nv-embed-v2 or similar)
"""

def create_placeholder_vector():
    """Create a placeholder vector for the memory"""
    # For now, create a normalized random vector
    # In production, use proper embedding model
    vector = [random.gauss(0, 0.3) for _ in range(1024)]
    # Normalize
    magnitude = sum(x**2 for x in vector) ** 0.5
    return [x / magnitude for x in vector]

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
        print(f"⚠️  Collection not found: {e}")
        return None

    # Generate placeholder vector
    print("🔄 Generating placeholder vector...")
    vector = create_placeholder_vector()
    print(f"✅ Generated {len(vector)}-dimensional vector")

    # Create memory document
    memory_doc = {
        "$vector": vector,
        "content": MEMORY_CONTENT,
        "type": "system_configuration",
        "category": "environment_setup",
        "timestamp": datetime.utcnow().isoformat(),
        "project": "One2lvOS",
        "version": "1.0.0",
        "embedding_note": "Placeholder vector - update with proper NVIDIA embedding when model is updated",
        "tags": [
            "configuration",
            "environment",
            "deployment",
            "security",
            "astra_db",
            "nvidia_ai",
            "sovereign_architecture",
            "astra_cli"
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
            "git_protected": True,
            "astra_cli_installed": True
        }
    }

    # Insert into Astra DB
    print("🔄 Inserting memory into Astra DB...")
    result = collection.insert_one(memory_doc)
    print(f"✅ Memory stored successfully!")
    print(f"   Document ID: {result.inserted_id}")

    # Count total memories
    print("\n🔍 Checking collection status...")
    # Note: count_documents may not be available in all versions
    try:
        count_result = collection.count_documents({})
        print(f"✅ Total memories in collection: {count_result}")
    except:
        print("   (Count not available)")

    return result

def main():
    """Main execution"""
    print("═══════════════════════════════════════════════════════════")
    print("   ONE2LVOS - Astra DB Memory Creation")
    print("═══════════════════════════════════════════════════════════")
    print()

    # Verify environment variables
    if not all([ASTRA_ENDPOINT, ASTRA_TOKEN]):
        print("❌ Missing required environment variables!")
        print("   Make sure .env.master exists and contains:")
        print("   - ASTRA_DB_API_ENDPOINT")
        print("   - ASTRA_DB_APPLICATION_TOKEN")
        sys.exit(1)

    print("✅ Environment variables loaded")
    print(f"   Astra DB: {ASTRA_ENDPOINT[:50]}...")
    print(f"   Collection: {COLLECTION}")
    print()
    print("⚠️  Note: Using placeholder vector (NVIDIA embedding model deprecated)")
    print("   Update to nvidia/nv-embed-v2 or similar in production")
    print()

    try:
        store_memory()
        print()
        print("═══════════════════════════════════════════════════════════")
        print("   ✅ Memory Creation Complete!")
        print("═══════════════════════════════════════════════════════════")
        print()
        print("The environment configuration has been stored in Astra DB.")
        print("It contains:")
        print("  • Complete .env.master configuration details")
        print("  • Security measures implemented")
        print("  • Deployment instructions")
        print("  • Documentation references")
        print("  • Astra CLI installation info")
        print()
        print("Note: Vector embedding is a placeholder. Update embedding")
        print("model in .env.master to nvidia/nv-embed-v2 for production.")
        print()
    except Exception as e:
        print()
        print("═══════════════════════════════════════════════════════════")
        print("   ❌ Error Creating Memory")
        print("═══════════════════════════════════════════════════════════")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
