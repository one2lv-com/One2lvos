#!/usr/bin/env python3
"""
One2lvOS Complete Demo
======================

Demonstrates the complete One2lvOS system with:
- Full boot sequence
- State management
- Snapshot creation
- Recovery from snapshots
- Transactional restoration
"""

import time
from one2lvos.bootloader import One2lvOS


def demo_basic_operations():
    """Demo: Basic OS operations"""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Operations")
    print("=" * 70)

    # Boot system
    os = One2lvOS(base_dir="/tmp/one2lvos-demo1")

    # Write some files
    print("\n--- Creating Files ---")
    os.write_file("/home/test.txt", "Hello from One2lvOS!")
    os.write_file("/home/data.json", '{"status": "active"}')
    os.write_file("/var/log.txt", "System initialized")

    # List directory
    print("\n--- Directory Listing ---")
    os.list_dir("/home")

    # Read file
    print("\n--- Reading File ---")
    content = os.read_file("/home/test.txt")
    print(f"Content: {content}")

    # Add memory
    print("\n--- Memory Operations ---")
    os.add_memory("api_key", "secret-key-123")
    os.add_memory("counter", 42)

    # Add task
    print("\n--- Task Management ---")
    os.add_task("Process data files", priority=1)
    os.add_task("Generate report", priority=2)

    # Show status
    print("\n--- System Status ---")
    os.status()

    # Create snapshot
    print("\n--- Creating Snapshot ---")
    os.create_snapshot()

    # Shutdown
    os.shutdown()


def demo_snapshot_recovery():
    """Demo: Snapshot and recovery"""
    print("\n" + "=" * 70)
    print("DEMO 2: Snapshot and Recovery")
    print("=" * 70)

    # Boot first instance
    print("\n--- First Boot ---")
    os1 = One2lvOS(base_dir="/tmp/one2lvos-demo2", auto_snapshot=False)

    # Create state
    print("\n--- Creating State ---")
    os1.write_file("/important.txt", "Critical data v1")
    os1.add_memory("version", "1.0")
    os1.add_task("Important task")

    # Create snapshot
    print("\n--- Creating Snapshot ---")
    snapshot1 = os1.create_snapshot()

    # Modify state
    print("\n--- Modifying State ---")
    os1.write_file("/important.txt", "Critical data v2")
    os1.add_memory("version", "2.0")

    # Create second snapshot
    print("\n--- Creating Second Snapshot ---")
    snapshot2 = os1.create_snapshot()

    print(f"\nSnapshot 1: gen={snapshot1.generation}")
    print(f"Snapshot 2: gen={snapshot2.generation}")

    # Shutdown
    os1.shutdown()

    # Boot second instance (recovery)
    print("\n--- Second Boot (Recovery) ---")
    os2 = One2lvOS(base_dir="/tmp/one2lvos-demo2", auto_snapshot=False)

    # Verify recovered state
    print("\n--- Verifying Recovered State ---")
    content = os2.read_file("/important.txt")
    version = os2.get_memory("version")

    print(f"Recovered file: {content}")
    print(f"Recovered version: {version}")

    os2.status()
    os2.shutdown()


def demo_transactional_restoration():
    """Demo: Transactional restoration with rollback"""
    print("\n" + "=" * 70)
    print("DEMO 3: Transactional Restoration")
    print("=" * 70)

    # Boot and create state
    print("\n--- Creating Initial State ---")
    os1 = One2lvOS(base_dir="/tmp/one2lvos-demo3", auto_snapshot=False)

    for i in range(5):
        os1.write_file(f"/data/file{i}.txt", f"Data {i}")

    os1.add_memory("initialized", True)

    # Create snapshots with generation tracking
    print("\n--- Creating Snapshot Chain ---")
    snap1 = os1.create_snapshot()
    print(f"Snapshot 1: gen={snap1.generation}, id={snap1.snapshot_id.hex()[:8]}")

    os1.write_file("/data/new_file.txt", "New data")
    snap2 = os1.create_snapshot()
    print(f"Snapshot 2: gen={snap2.generation}, id={snap2.snapshot_id.hex()[:8]}")

    os1.write_file("/data/another_file.txt", "Another data")
    snap3 = os1.create_snapshot()
    print(f"Snapshot 3: gen={snap3.generation}, id={snap3.snapshot_id.hex()[:8]}")

    print("\n--- Snapshot Lineage ---")
    print(f"Snapshot 1 (root)")
    print(f"  ↓ parent: {snap1.parent_snapshot_id.hex()}")
    print(f"Snapshot 2")
    print(f"  ↓ parent: {snap2.parent_snapshot_id.hex()[:8]}")
    print(f"Snapshot 3")
    print(f"  ↓ parent: {snap3.parent_snapshot_id.hex()[:8]}")

    os1.status()
    os1.shutdown()

    # Recover
    print("\n--- Recovery with Generation Validation ---")
    os2 = One2lvOS(base_dir="/tmp/one2lvos-demo3", auto_snapshot=False)

    print(f"Recovered generation: {os2.snapshot_manager.current_generation}")
    os2.status()
    os2.shutdown()


def demo_export_import():
    """Demo: Export and import snapshots"""
    print("\n" + "=" * 70)
    print("DEMO 4: Export and Import")
    print("=" * 70)

    # Create system with state
    print("\n--- Creating System with State ---")
    os1 = One2lvOS(base_dir="/tmp/one2lvos-export", auto_snapshot=False)

    os1.write_file("/export-test.txt", "This will be exported")
    os1.add_memory("export_test", True)

    # Export snapshot
    print("\n--- Exporting Snapshot ---")
    export_path = os1.export_snapshot("/tmp/exported_snapshot.o2png")
    print(f"Exported to: {export_path}")

    os1.shutdown()

    # Import in new system
    print("\n--- Importing to New System ---")
    import shutil
    shutil.copy(export_path, "/tmp/one2lvos-import/snapshots/boot.o2png")

    os2 = One2lvOS(base_dir="/tmp/one2lvos-import", auto_snapshot=False)

    # Verify imported state
    print("\n--- Verifying Imported State ---")
    content = os2.read_file("/export-test.txt")
    print(f"Imported file: {content}")

    test_flag = os2.get_memory("export_test")
    print(f"Imported memory: {test_flag}")

    os2.status()
    os2.shutdown()


def demo_auto_snapshots():
    """Demo: Automatic snapshot creation"""
    print("\n" + "=" * 70)
    print("DEMO 5: Auto-Snapshot System")
    print("=" * 70)

    # Boot with auto-snapshots (every 5 seconds for demo)
    print("\n--- Booting with Auto-Snapshot (5s interval) ---")
    os = One2lvOS(base_dir="/tmp/one2lvos-auto", auto_snapshot=False)

    # Start manual auto-snapshot with short interval
    os.snapshot_manager.auto_snapshot_loop(interval_seconds=5)

    # Simulate activity
    print("\n--- Simulating Activity ---")
    for i in range(3):
        print(f"\nActivity cycle {i+1}")
        os.write_file(f"/activity/log{i}.txt", f"Activity {i}")
        os.add_memory(f"cycle_{i}", time.time())

        print("Waiting for auto-snapshot...")
        time.sleep(6)  # Wait for auto-snapshot

        # Check snapshot count
        snapshots = os.snapshot_manager.get_snapshot_list()
        print(f"Total snapshots: {len(snapshots)}")

    os.status()
    os.shutdown()


def main():
    """Run all demos"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              ONE2LVOS COMPLETE DEMONSTRATION                  ║
║                                                               ║
║  Production-grade state capsule operating system              ║
║  Built on O2PNG Protocol v1.0                                 ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    demos = [
        ("Basic Operations", demo_basic_operations),
        ("Snapshot and Recovery", demo_snapshot_recovery),
        ("Transactional Restoration", demo_transactional_restoration),
        ("Export and Import", demo_export_import),
        ("Auto-Snapshot System", demo_auto_snapshots),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n{'=' * 70}")
        print(f"Running Demo {i}/{len(demos)}: {name}")
        print(f"{'=' * 70}")

        try:
            demo_func()
        except Exception as e:
            print(f"\n[ERROR] Demo failed: {e}")
            import traceback
            traceback.print_exc()

        if i < len(demos):
            print("\n[Press Enter to continue to next demo...]")
            input()

    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    DEMONSTRATION COMPLETE                     ║
║                                                               ║
║  One2lvOS is ready for production deployment                  ║
╚═══════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
