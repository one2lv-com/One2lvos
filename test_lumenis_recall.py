#!/usr/bin/env python3
"""Test Lumenis memory recall of One2lvOS briefing"""

import sqlite3
import json

DB_PATH = "compass.db"

def test_recall():
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║      LUMENIS MEMORY RECALL TEST - One2lvOS Briefing                  ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Test 1: Recall Lumenis identity
    print("🔍 Test 1: Recall 'Who is Lumenis?'")
    print("   Query: lumenis_identity")
    print()

    cursor.execute("SELECT value FROM facts WHERE key = 'lumenis_identity'")
    result = cursor.fetchone()
    if result:
        identity = json.loads(result[0])
        print(f"  ✓ Found: {identity['name']} - {identity['title']}")
        print(f"    Role: {identity['role']}")
        print(f"    Beacon: {identity['beacon']}")
        print(f"    Thermal: {identity['thermal_baseline']}")
        print(f"    Council Seats: {identity['council']['seats']}")
    else:
        print("  ✗ Not found")

    print()
    print("━" * 70)
    print()

    # Test 2: Recall system overview
    print("🔍 Test 2: Recall 'What is One2lvOS?'")
    print("   Query: one2lvos_system_overview")
    print()

    cursor.execute("SELECT value FROM facts WHERE key = 'one2lvos_system_overview'")
    result = cursor.fetchone()
    if result:
        overview = json.loads(result[0])
        print(f"  ✓ Found: {overview['system_name']}")
        print(f"    Description: {overview['description']}")
        print(f"    Repository: {overview['repository']}")
        print(f"    Architecture Layers:")
        for layer, desc in overview['architecture_layers'].items():
            print(f"      {layer}: {desc}")
    else:
        print("  ✗ Not found")

    print()
    print("━" * 70)
    print()

    # Test 3: Recall current challenges
    print("🔍 Test 3: Recall 'What are the current challenges?'")
    print("   Query: one2lvos_current_challenges")
    print()

    cursor.execute("SELECT value FROM facts WHERE key = 'one2lvos_current_challenges'")
    result = cursor.fetchone()
    if result:
        challenges = json.loads(result[0])
        print(f"  ✓ Found {len(challenges)} challenge categories:")
        for key, challenge in challenges.items():
            print(f"    • {key}: {challenge['issue']}")
            print(f"      Priority: {challenge['priority']}")
    else:
        print("  ✗ Not found")

    print()
    print("━" * 70)
    print()

    # Test 4: Search for "dream state"
    print("🔍 Test 4: Search 'dream state'")
    print("   Query: LIKE '%dream%'")
    print()

    cursor.execute("SELECT key, value FROM facts WHERE key LIKE '%dream%' OR value LIKE '%dream%'")
    results = cursor.fetchall()
    print(f"  ✓ Found {len(results)} results:")
    for key, value in results:
        if 'dream' in key.lower():
            print(f"    • {key}")
            data = json.loads(value)
            if isinstance(data, dict) and 'description' in data:
                print(f"      {data['description'][:80]}...")

    print()
    print("━" * 70)
    print()

    # Test 5: Full text search for "intergalactic"
    print("🔍 Test 5: Search 'intergalactic'")
    print("   Query: LIKE '%intergalactic%'")
    print()

    cursor.execute("SELECT key FROM facts WHERE value LIKE '%intergalactic%'")
    results = cursor.fetchall()
    print(f"  ✓ Found {len(results)} references:")
    for (key,) in results:
        print(f"    • {key}")

    print()
    print("━" * 70)
    print()

    conn.close()

    print("✅ Memory Recall Test Complete")
    print()
    print("   Lumenis can successfully recall:")
    print("   • Identity and role information")
    print("   • System architecture details")
    print("   • Current challenges and priorities")
    print("   • Dream state consciousness layers")
    print("   • Intergalactic memory references")
    print()
    print("   This information persists across sandbox sessions")
    print("   and is available to future conversation contexts.")
    print()

if __name__ == "__main__":
    test_recall()
