#!/usr/bin/env python3
"""
Aether-Lumenis OS - Automated Test Suite
Tests all subsystems without interactive REPL
"""

import asyncio
import sys
from aether_lumenis_os import (
    AetherLumenisOS,
    O2PNGProtocol,
    PNGBootCarrier,
    VectorFS,
    Logger
)

async def run_tests():
    print("\n" + "="*70)
    print("  AETHER-LUMENIS OS - AUTOMATED TEST SUITE")
    print("="*70 + "\n")

    results = []

    # Test 1: Boot System
    print("[TEST 1] Booting Aether-Lumenis OS...")
    try:
        kernel = AetherLumenisOS()
        boot_time = await kernel.boot()
        assert kernel.system_status == "ONLINE"
        assert boot_time > 0
        results.append(("Boot System", "PASS", f"{boot_time}ms"))
        print(f"✓ Boot successful in {boot_time}ms")
    except Exception as e:
        results.append(("Boot System", "FAIL", str(e)))
        print(f"✗ Boot failed: {e}")
        return results

    # Test 2: VFS Operations
    print("\n[TEST 2] Testing Virtual File System...")
    try:
        kernel.vfs.write_file("/home/test.txt", "Hello Aether-Lumenis")
        content = kernel.vfs.read_file("/home/test.txt")
        assert content == "Hello Aether-Lumenis"
        files = kernel.vfs.list_dir("/home")
        assert "test.txt" in files
        results.append(("VFS Operations", "PASS", f"{len(files)} files"))
        print(f"✓ VFS working - {len(files)} files in /home")
    except Exception as e:
        results.append(("VFS Operations", "FAIL", str(e)))
        print(f"✗ VFS test failed: {e}")

    # Test 3: VectorFS Semantic Search
    print("\n[TEST 3] Testing VectorFS Semantic Search...")
    try:
        kernel.vector_fs.store("test.vector", [0.5, 0.5, 0.8, 0.2] + [0.0]*12, {"desc": "Test vector"})
        query = [0.6, 0.4, 0.7, 0.3] + [0.0]*12
        results_vec = kernel.vector_fs.search(query, limit=3)
        assert len(results_vec) > 0
        assert results_vec[0]["similarity"] > 0.0
        results.append(("VectorFS Search", "PASS", f"{len(results_vec)} matches"))
        print(f"✓ VectorFS working - {len(results_vec)} semantic matches")
    except Exception as e:
        results.append(("VectorFS Search", "FAIL", str(e)))
        print(f"✗ VectorFS test failed: {e}")

    # Test 4: Lumenis Reactor Task Execution
    print("\n[TEST 4] Testing Lumenis Reactor...")
    try:
        task_id = kernel.reactor.push_task("Test Task", 1, lambda: "Task completed")
        await kernel.execute_cycle()
        assert len(kernel.reactor.itt_journal) > 0
        latest_entry = kernel.reactor.itt_journal[-1]
        assert latest_entry["status"] == "SUCCESS"
        results.append(("Reactor Execution", "PASS", f"{len(kernel.reactor.itt_journal)} cycles"))
        print(f"✓ Reactor working - {len(kernel.reactor.itt_journal)} ITT cycles logged")
    except Exception as e:
        results.append(("Reactor Execution", "FAIL", str(e)))
        print(f"✗ Reactor test failed: {e}")

    # Test 5: Sovereign Council Deliberation
    print("\n[TEST 5] Testing Sovereign Council...")
    try:
        context = {
            "generation": kernel.generation,
            "last_committed_generation": 0,
            "itt_history": kernel.reactor.itt_journal,
            "metrics": {"active_tasks": 0}
        }
        decision = await kernel.council.deliberate("Test Deliberation", context)
        assert "verdict" in decision
        assert decision["verdict"] in ["APPROVED", "REJECTED"]
        results.append(("Council Deliberation", "PASS", decision["verdict"]))
        print(f"✓ Council working - Verdict: {decision['verdict']}")
    except Exception as e:
        results.append(("Council Deliberation", "FAIL", str(e)))
        print(f"✗ Council test failed: {e}")

    # Test 6: O2PNG State Snapshot & Rehydration
    print("\n[TEST 6] Testing O2PNG State Persistence...")
    try:
        # Capture snapshot
        png_carrier = kernel.capture_snapshot()
        assert len(png_carrier) > 0

        # Verify PNG header
        assert png_carrier[:8] == b'\x89PNG\r\n\x1a\n'

        # Create new OS instance and restore
        new_kernel = AetherLumenisOS(device_id=kernel.device_id)
        await new_kernel.boot(png_carrier)

        # Verify state was restored
        restored_content = new_kernel.vfs.read_file("/home/test.txt")
        assert restored_content == "Hello Aether-Lumenis"
        assert new_kernel.generation == kernel.generation + 1

        results.append(("O2PNG Persistence", "PASS", f"Gen {new_kernel.generation}"))
        print(f"✓ O2PNG working - State rehydrated to generation {new_kernel.generation}")
    except Exception as e:
        results.append(("O2PNG Persistence", "FAIL", str(e)))
        print(f"✗ O2PNG test failed: {e}")

    # Print Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")

    for test_name, status, detail in results:
        status_icon = "✓" if status == "PASS" else "✗"
        status_color = "\033[0;32m" if status == "PASS" else "\033[0;31m"
        print(f"{status_icon} {test_name:<25} {status_color}{status}\033[0m - {detail}")

    print("="*70)
    print(f"TOTAL: {passed} passed, {failed} failed out of {len(results)} tests")
    print("="*70 + "\n")

    return results

if __name__ == "__main__":
    results = asyncio.run(run_tests())

    # Exit with error code if any test failed
    failed = sum(1 for _, status, _ in results if status == "FAIL")
    sys.exit(1 if failed > 0 else 0)
