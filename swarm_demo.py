#!/usr/bin/env python3
"""
🧠 SWARM EXECUTION LAYER DEMO
=============================
Demonstrates the distributed swarm execution system
integrated with the Lumenis Reactor.
"""

import asyncio
import time
from pathlib import Path

from lumenis_reactor_core.swarm import SwarmOrchestrator


async def demo_basic():
    """Basic swarm demonstration."""
    print("\n" + "="*70)
    print("🧠 SWARM EXECUTION LAYER DEMO")
    print("="*70)

    # Initialize swarm
    root = Path(__file__).parent / "One2lvos-build" / "lumenis_reactor_core" / "swarm"
    swarm = SwarmOrchestrator(root_dir=root, num_workers=5)

    # Start the swarm
    swarm.start()

    print("\n⏳ Letting swarm process tasks for 30 seconds...")

    # Let it run for a bit
    for i in range(30):
        await asyncio.sleep(1)

        if i % 5 == 0:
            status = swarm.get_status()
            metrics = status['metrics']
            print(f"\n📊 Progress: {metrics['total_processed']} tasks processed, {metrics['queue_depth']} in queue")

    # Final status
    print("\n" + "="*70)
    print("📊 FINAL SWARM STATUS")
    print("="*70)

    status = swarm.get_status()
    metrics = status['metrics']

    print(f"\n🎯 METRICS:")
    print(f"  Total Tasks Processed: {metrics['total_processed']}")
    print(f"  Queue Depth: {metrics['queue_depth']}")
    print(f"  Active Nodes: {metrics['active_nodes']}")

    print(f"\n🧠 WORKERS:")
    for worker in status['workers']:
        print(f"  • {worker['node_id']:15} | Processed: {worker['processed']:4} | Running: {worker['running']}")

    # Stop the swarm
    print("\n🛑 Stopping swarm...")
    swarm.stop()

    print("\n✅ Demo complete!")


async def demo_custom_tasks():
    """Demonstrate custom task submission."""
    print("\n" + "="*70)
    print("🎯 CUSTOM TASK SUBMISSION DEMO")
    print("="*70)

    root = Path(__file__).parent / "One2lvos-build" / "lumenis_reactor_core" / "swarm"
    swarm = SwarmOrchestrator(root_dir=root, num_workers=3)

    swarm.start()
    await asyncio.sleep(2)

    # Submit custom tasks
    print("\n📨 Submitting custom tasks...")

    tasks = [
        ("oracle", {"query": "What is the meaning of consciousness?"}),
        ("forge", {"action": "compile", "target": "module.py"}),
        ("navigator", {"destination": "memory_lane"}),
        ("reasoning", {"prompt": "Analyze the swarm efficiency"}),
        ("synthesis", {"inputs": ["A", "B", "C"]}),
    ]

    for task_type, data in tasks:
        task_id = await swarm.submit_task(task_type, data)
        print(f"  ✓ Submitted {task_type} task (ID: {task_id})")

    # Let workers process
    print("\n⏳ Processing custom tasks...")
    await asyncio.sleep(10)

    # Status
    status = swarm.get_status()
    print(f"\n📊 Processed: {status['metrics']['total_processed']} tasks")

    swarm.stop()
    print("\n✅ Demo complete!")


async def demo_stress_test():
    """Stress test the swarm with many workers and tasks."""
    print("\n" + "="*70)
    print("⚡ SWARM STRESS TEST")
    print("="*70)

    root = Path(__file__).parent / "One2lvos-build" / "lumenis_reactor_core" / "swarm"
    swarm = SwarmOrchestrator(root_dir=root, num_workers=10)

    swarm.start()
    await asyncio.sleep(2)

    print("\n⏳ Running stress test for 20 seconds...")

    start_time = time.time()
    last_count = 0

    for i in range(20):
        await asyncio.sleep(1)

        if i % 5 == 0:
            status = swarm.get_status()
            metrics = status['metrics']
            current_count = metrics['total_processed']
            rate = (current_count - last_count) / 5 if i > 0 else 0

            print(f"\n📊 T+{i}s: {current_count} tasks | Rate: {rate:.1f} tasks/sec | Queue: {metrics['queue_depth']}")
            last_count = current_count

    # Final metrics
    elapsed = time.time() - start_time
    status = swarm.get_status()
    total = status['metrics']['total_processed']
    avg_rate = total / elapsed

    print("\n" + "="*70)
    print("📊 STRESS TEST RESULTS")
    print("="*70)
    print(f"  Duration: {elapsed:.1f}s")
    print(f"  Total Tasks: {total}")
    print(f"  Average Rate: {avg_rate:.2f} tasks/sec")
    print(f"  Workers: {len(status['workers'])}")

    swarm.stop()
    print("\n✅ Stress test complete!")


def main():
    """Run all demos."""
    import sys

    demos = {
        "basic": demo_basic,
        "custom": demo_custom_tasks,
        "stress": demo_stress_test,
    }

    if len(sys.argv) > 1:
        demo_name = sys.argv[1]
        if demo_name in demos:
            asyncio.run(demos[demo_name]())
        else:
            print(f"Unknown demo: {demo_name}")
            print(f"Available: {', '.join(demos.keys())}")
    else:
        # Run all demos
        print("\n🚀 Running all swarm demos...\n")
        for name, demo in demos.items():
            asyncio.run(demo())
            time.sleep(2)


if __name__ == "__main__":
    main()
