#!/usr/bin/env python3
"""
One2lv OS Android Bridge for Lumenis
=====================================
Allows Lumenis to control and interact with the One2lv OS Android system.

Usage:
    python3 one2lvos_android_bridge.py <command> [args]

Commands:
    exec <cmd>       - Execute terminal command
    status          - Get system status
    install <pkg>   - Install Ubuntu package (requires root)
    root            - Switch to root user
    user            - Switch to normal user
    neofetch        - Display system info
    save            - Save OS state
    load <file>     - Load OS state

Examples:
    python3 one2lvos_android_bridge.py exec "ls -la"
    python3 one2lvos_android_bridge.py install nginx
    python3 one2lvos_android_bridge.py root
    python3 one2lvos_android_bridge.py status
"""

import asyncio
import json
import sys
from pathlib import Path

# Add reactor core to path
sys.path.insert(0, str(Path(__file__).parent / "lumenis_reactor_core"))

from one2lvos_android import One2lvOSAndroid


class One2lvOSBridge:
    """Bridge between Lumenis and One2lv OS Android"""

    def __init__(self):
        self.os = One2lvOSAndroid()

    async def execute_command(self, command: str):
        """Execute a terminal command"""
        print(f"\n{self.os.get_prompt()}{command}")
        output = await self.os.execute_command(command)
        if output:
            print(output)
        print()

    async def get_status(self):
        """Get system status"""
        status = self.os.get_status()
        print("\n╔══════════════════════════════════════════════════════════╗")
        print("║        ONE2LV OS ANDROID - SYSTEM STATUS                 ║")
        print("╚══════════════════════════════════════════════════════════╝\n")

        print(f"  OS Version:     {status['os_version']}")
        print(f"  Kernel:         {status['kernel']}")
        print(f"  Hostname:       {status['hostname']}")
        print(f"  Current User:   {status['user']} {'(root)' if status['is_root'] else ''}")
        print(f"  Current Dir:    {status['current_dir']}")
        print(f"  Uptime:         {int(status['uptime_seconds'] / 60)} minutes")
        print(f"\n  Packages:       {status['installed_packages']} installed")
        print(f"  Commands:       {status['terminal_commands_executed']} executed")
        print(f"  Filesystem:     {status['filesystem_dirs']} directories")
        print(f"  Memory Frags:   {status['memory_fragments']}")
        print(f"\n  Prompt:         {status['prompt']}")
        print(f"  Status:         {'🟢 ONLINE' if status['online'] else '🔴 OFFLINE'}")
        print()

    async def install_package(self, package: str):
        """Install an Ubuntu package"""
        print(f"\nInstalling package: {package}")

        # Switch to root if not already
        if not self.os.state.is_root:
            print("Elevating to root...")
            await self.execute_command("su")

        # Install package
        await self.execute_command(f"apt install {package}")

    async def switch_to_root(self):
        """Switch to root user"""
        print("\nSwitching to root user...")
        await self.execute_command("su")
        print(f"Current prompt: {self.os.get_prompt()}")

    async def switch_to_user(self):
        """Switch to normal user"""
        print("\nExiting root shell...")
        await self.execute_command("exit")
        print(f"Current prompt: {self.os.get_prompt()}")

    async def display_neofetch(self):
        """Display system info with neofetch"""
        await self.execute_command("neofetch")

    async def save_state(self, filename: str = "one2lvos_state.json"):
        """Save OS state to file"""
        state = self.os.save_state()
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"\n✓ State saved to {filename}")
        print(f"  Size: {len(json.dumps(state))} bytes")
        print(f"  Packages: {len(state['installed_packages'])}")
        print(f"  Commands: {len(state['terminal_history'])}")
        print()

    async def load_state(self, filename: str):
        """Load OS state from file"""
        with open(filename, 'r') as f:
            state = json.load(f)
        self.os.load_state(state)
        print(f"\n✓ State loaded from {filename}")
        print(f"  User: {self.os.state.current_user}")
        print(f"  Packages: {len(self.os.state.installed_packages)}")
        print(f"  Commands: {len(self.os.state.terminal_history)}")
        print()


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    bridge = One2lvOSBridge()
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    try:
        if command == "exec":
            if not args:
                print("Error: exec requires a command")
                sys.exit(1)
            await bridge.execute_command(" ".join(args))

        elif command == "status":
            await bridge.get_status()

        elif command == "install":
            if not args:
                print("Error: install requires a package name")
                sys.exit(1)
            await bridge.install_package(args[0])

        elif command == "root":
            await bridge.switch_to_root()

        elif command == "user":
            await bridge.switch_to_user()

        elif command == "neofetch":
            await bridge.display_neofetch()

        elif command == "save":
            filename = args[0] if args else "one2lvos_state.json"
            await bridge.save_state(filename)

        elif command == "load":
            if not args:
                print("Error: load requires a filename")
                sys.exit(1)
            await bridge.load_state(args[0])

        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
