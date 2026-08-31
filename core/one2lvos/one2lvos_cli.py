#!/usr/bin/env python3
"""
One2lvOS Command-Line Interface
================================

Usage:
    python one2lvos_cli.py [command] [options]

Commands:
    boot        - Boot One2lvOS
    shell       - Start interactive shell
    demo        - Run complete demonstration
    snapshot    - Create snapshot
    status      - Show system status
    export      - Export snapshot
"""

import sys
import argparse
from one2lvos.bootloader import One2lvOS


def cmd_boot(args):
    """Boot One2lvOS"""
    os = One2lvOS(base_dir=args.base_dir, auto_snapshot=args.auto_snapshot)
    print("\nOne2lvOS booted successfully")
    print("System is running...")
    return os


def cmd_shell(args):
    """Start interactive shell"""
    os = One2lvOS(base_dir=args.base_dir, auto_snapshot=False)
    os.shell()


def cmd_demo(args):
    """Run demonstration"""
    from one2lvos_demo import main as demo_main
    demo_main()


def cmd_snapshot(args):
    """Create snapshot"""
    os = One2lvOS(base_dir=args.base_dir, auto_snapshot=False)
    identity = os.create_snapshot()
    print(f"\nSnapshot created:")
    print(f"  ID: {identity.snapshot_id.hex()}")
    print(f"  Generation: {identity.generation}")
    print(f"  Created: {identity.created_at}")
    os.shutdown()


def cmd_status(args):
    """Show status"""
    os = One2lvOS(base_dir=args.base_dir, auto_snapshot=False)
    os.status()
    os.shutdown()


def cmd_export(args):
    """Export snapshot"""
    if not args.output:
        print("Error: --output required")
        return

    os = One2lvOS(base_dir=args.base_dir, auto_snapshot=False)
    path = os.export_snapshot(args.output)
    print(f"Snapshot exported to: {path}")
    os.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description="One2lvOS - Production-grade state capsule OS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python one2lvos_cli.py boot
  python one2lvos_cli.py shell
  python one2lvos_cli.py demo
  python one2lvos_cli.py snapshot
  python one2lvos_cli.py export --output snapshot.o2png
        """
    )

    parser.add_argument(
        "command",
        choices=["boot", "shell", "demo", "snapshot", "status", "export"],
        help="Command to execute"
    )

    parser.add_argument(
        "--base-dir",
        default="/tmp/one2lvos",
        help="Base directory for One2lvOS (default: /tmp/one2lvos)"
    )

    parser.add_argument(
        "--auto-snapshot",
        action="store_true",
        help="Enable automatic snapshot creation"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output path for export command"
    )

    args = parser.parse_args()

    # Command dispatch
    commands = {
        "boot": cmd_boot,
        "shell": cmd_shell,
        "demo": cmd_demo,
        "snapshot": cmd_snapshot,
        "status": cmd_status,
        "export": cmd_export,
    }

    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
