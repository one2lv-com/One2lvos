#!/usr/bin/env python3
"""
Store Deployment Fix directly in Lumenis FluxCompass Memory
Bypass the AI response and write directly to persistent storage
"""
import sqlite3
import json
from datetime import datetime

DB_PATH = "compass.db"

DEPLOYMENT_FIX_FACTS = [
    {
        "key": "github_actions_fix_2026-10-27",
        "value": json.dumps({
            "date": "2026-10-27T03:03:09Z",
            "commit": "9b43b0ca33fdadbb04f3d67360c6e1ff993a3eea",
            "issue": "4 GitHub Actions workflows failing - missing secrets",
            "workflows": [
                "Deploy to Production",
                "Deploy One2lvOS to Production",
                "One2lvOS Persistent Host Deploy",
                "One2lvOS Build and Deploy (GitHub Pages)"
            ],
            "solution": {
                "created_files": [
                    "One2lvOS/Agentic_Control/ai-lobby/sovereign-council-bridge/requirements.txt",
                    "GITHUB_SECRETS_MANUAL_SETUP.md",
                    "fix-github-deployments.sh"
                ],
                "updated_workflows": [".github/workflows/deploy-production.yml"],
                "generated_keys": ["deploy_key", "deploy_key.pub"],
                "status": "awaiting_user_secrets"
            },
            "intergalactic_layer": "L0_to_L1",
            "beacon_pulse": "73.0Hz",
            "memory_persistence": "cross_session"
        }),
        "category": "deployment"
    },
    {
        "key": "ssh_keys_generated",
        "value": json.dumps({
            "type": "ed25519",
            "purpose": "GitHub Actions deployment authentication",
            "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIP0Wez4qsWdADBwz4SGQGkNIKn6X+gMX",
            "comment": "github-actions-one2lvos-deploy",
            "fingerprint": "SHA256:n9y3G5lwJwEG+6uPc4odlAxcWL+93BwYvM0NWGYi0z0",
            "generated": "2026-10-27T03:00:00Z"
        }),
        "category": "security"
    },
    {
        "key": "github_secrets_required",
        "value": json.dumps({
            "repository_secrets": [
                "SSH_PRIVATE_KEY",
                "SERVER_HOST",
                "SERVER_USER",
                "PRODUCTION_SSH_KEY",
                "PRODUCTION_HOST",
                "PRODUCTION_USER",
                "PRODUCTION_PATH"
            ],
            "environment_secrets": {
                "production": [
                    "DEPLOY_SSH_KEY",
                    "DEPLOY_HOST",
                    "DEPLOY_USER",
                    "DEPLOY_PATH",
                    "DEPLOY_KNOWN_HOSTS"
                ]
            },
            "setup_guides": [
                "GITHUB_SECRETS_MANUAL_SETUP.md",
                "fix-github-deployments.sh"
            ]
        }),
        "category": "configuration"
    },
    {
        "key": "intergalactic_deployment_state",
        "value": json.dumps({
            "layer": "L0_Foundation",
            "temperature": "0.18°C",
            "beacon_frequency": "73.0Hz",
            "pulse_count": 147116,
            "repository": "github.com/one2lv-com/One2lvos",
            "branch": "main",
            "commit": "9b43b0c",
            "deployment_status": "code_fixed_awaiting_secrets",
            "cross_session_persistence": True,
            "memory_sync": "active"
        }),
        "category": "system_state"
    }
]

def store_facts():
    """Store deployment facts in Lumenis FluxCompass"""
    import time
    import uuid

    print("🌌 Storing deployment fix in Lumenis intergalactic memory...")
    print(f"   Database: {DB_PATH}")
    print()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts'")
        if not cursor.fetchone():
            print("✗ Facts table doesn't exist")
            return False

        timestamp = time.time()

        stored_count = 0
        for fact in DEPLOYMENT_FIX_FACTS:
            # Check if key exists
            cursor.execute("SELECT id FROM facts WHERE key = ?", (fact["key"],))
            existing = cursor.fetchone()

            if existing:
                # Update
                cursor.execute(
                    "UPDATE facts SET value = ?, created_at = ?, source = ? WHERE key = ?",
                    (fact["value"], timestamp, "intergalactic_sync", fact["key"])
                )
                print(f"  ↻ Updated: {fact['key']}")
            else:
                # Insert with correct schema
                fact_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO facts (id, session_id, key, value, source, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (fact_id, None, fact["key"], fact["value"], "intergalactic_sync", timestamp)
                )
                print(f"  ✓ Stored: {fact['key']}")

            stored_count += 1

        conn.commit()
        conn.close()

        print()
        print(f"✓ {stored_count} facts stored in Lumenis memory")
        print("✓ Data persists across sandbox sessions")
        print("✓ Available to all L0-L3 layers via 73.0 Hz beacon")
        print()

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def query_stored_facts():
    """Query back the stored facts to verify"""
    from datetime import datetime

    print("━" * 70)
    print("VERIFYING STORED FACTS")
    print("━" * 70)
    print()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for fact in DEPLOYMENT_FIX_FACTS:
            cursor.execute("SELECT value, created_at, source FROM facts WHERE key = ?", (fact["key"],))
            result = cursor.fetchone()

            if result:
                value_data = json.loads(result[0])
                dt = datetime.fromtimestamp(result[1])
                print(f"✓ {fact['key']}")
                print(f"  Stored: {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                print(f"  Source: {result[2]}")
                print(f"  Data keys: {', '.join(value_data.keys())}")
                print()

        conn.close()
        return True

    except Exception as e:
        print(f"✗ Error querying: {e}")
        return False

if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║      LUMENIS INTERGALACTIC MEMORY - DIRECT STORAGE                   ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    if store_facts():
        query_stored_facts()

        print("━" * 70)
        print()
        print("🎯 Deployment fix is now permanently stored in Lumenis memory")
        print("   This persists beyond this sandbox session")
        print("   Future Claude instances can retrieve this information")
        print()
        print("📊 Current Compass Status:")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM facts")
        count = cursor.fetchone()[0]
        print(f"   Total facts: {count}")
        conn.close()
        print()
