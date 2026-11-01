#!/usr/bin/env python3
"""
Quick test script to verify swarm installation and basic functionality.
"""

import time
from pathlib import Path

def test_imports():
    """Test that all swarm modules can be imported."""
    print("🧪 Testing imports...")
    try:
        from lumenis_reactor_core.swarm import (
            WorkerNode,
            TaskPulse,
            SwarmMonitor,
            SwarmOrchestrator,
        )
        print("  ✓ All imports successful")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_worker_creation():
    """Test worker node creation."""
    print("\n🧪 Testing worker creation...")
    try:
        from lumenis_reactor_core.swarm import WorkerNode
        worker = WorkerNode(node_id="test-worker")
        print(f"  ✓ Worker created: {worker.node_id}")
        return True
    except Exception as e:
        print(f"  ✗ Worker creation failed: {e}")
        return False


def test_task_pulse():
    """Test task pulse generator."""
    print("\n🧪 Testing task pulse...")
    try:
        from lumenis_reactor_core.swarm import TaskPulse
        pulse = TaskPulse(interval=1.0)

        # Generate a few tasks
        for _ in range(3):
            task = pulse.generate_task()
            print(f"  ✓ Task generated: {task['type']} (id: {task['id']})")

        return True
    except Exception as e:
        print(f"  ✗ Task pulse failed: {e}")
        return False


def test_monitor():
    """Test swarm monitor."""
    print("\n🧪 Testing swarm monitor...")
    try:
        from lumenis_reactor_core.swarm import SwarmMonitor
        monitor = SwarmMonitor()
        metrics = monitor.get_metrics()
        print(f"  ✓ Monitor created")
        print(f"  ✓ Metrics: {metrics}")
        return True
    except Exception as e:
        print(f"  ✗ Monitor failed: {e}")
        return False


def test_orchestrator():
    """Test swarm orchestrator initialization."""
    print("\n🧪 Testing orchestrator...")
    try:
        from lumenis_reactor_core.swarm import SwarmOrchestrator
        swarm = SwarmOrchestrator(num_workers=2)
        swarm.initialize()
        print(f"  ✓ Orchestrator initialized with {len(swarm.workers)} workers")
        return True
    except Exception as e:
        print(f"  ✗ Orchestrator failed: {e}")
        return False


def test_full_cycle():
    """Test a full swarm execution cycle."""
    print("\n🧪 Testing full execution cycle...")
    try:
        from lumenis_reactor_core.swarm import SwarmOrchestrator
        import asyncio

        swarm = SwarmOrchestrator(num_workers=2)
        swarm.start()

        print("  ✓ Swarm started")

        # Submit a task
        async def submit():
            return await swarm.submit_task("test", {"data": "test"})

        task_id = asyncio.run(submit())
        print(f"  ✓ Task submitted: {task_id}")

        # Let it process
        time.sleep(3)

        # Check status
        status = swarm.get_status()
        print(f"  ✓ Status retrieved: {status['metrics']['total_processed']} tasks processed")

        # Stop
        swarm.stop()
        print("  ✓ Swarm stopped")

        return True
    except Exception as e:
        print(f"  ✗ Full cycle failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*70)
    print("🧠 SWARM EXECUTION LAYER - TEST SUITE")
    print("="*70)

    tests = [
        test_imports,
        test_worker_creation,
        test_task_pulse,
        test_monitor,
        test_orchestrator,
        test_full_cycle,
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)
        time.sleep(0.5)

    print("\n" + "="*70)
    print("📊 TEST RESULTS")
    print("="*70)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    print("\n" + "="*70)

    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
