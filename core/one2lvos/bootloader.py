"""
One2lvOS Bootloader
===================

Simulates the complete boot sequence:
POWER ON → Bootloader → Boot Kernel → Recovery Manager → Lumenis Reactor → ONLINE
"""

import time
from pathlib import Path
from typing import Optional

from .recovery import RecoveryManager, RecoverySource
from .reactor import LumenisReactor
from .snapshot import SnapshotManager


class BootSequence:
    """
    Complete One2lvOS boot sequence.
    """

    def __init__(self, base_dir: str = "/tmp/one2lvos", verbose: bool = True):
        self.base_dir = base_dir
        self.verbose = verbose
        self.boot_start = time.time()

    def log(self, message: str, component: str = "BOOT"):
        """Log boot message"""
        if self.verbose:
            elapsed = int((time.time() - self.boot_start) * 1000)
            print(f"[{elapsed:04d}ms] [{component:12s}] {message}")

    def boot(self) -> tuple:
        """
        Execute complete boot sequence.

        Returns: (reactor, snapshot_manager, recovery_result)
        """
        self.log("=" * 60, "")
        self.log("ONE2LVOS BOOT SEQUENCE", "")
        self.log("=" * 60, "")

        # Stage 1: Bootloader
        self.log("Bootloader initialized", "BOOTLOADER")
        self.log("Verifying boot kernel...", "BOOTLOADER")
        time.sleep(0.1)  # Simulate verification
        self.log("Boot kernel verified ✓", "BOOTLOADER")

        # Stage 2: Boot Kernel
        self.log("Boot kernel loading...", "KERNEL")
        time.sleep(0.05)
        self.log("Filesystem mounted", "KERNEL")
        self.log("Network stack initialized", "KERNEL")
        self.log("Minimal runtime ready", "KERNEL")

        # Stage 3: Recovery Manager
        self.log("Recovery Manager starting...", "RECOVERY")
        recovery = RecoveryManager(self.base_dir)

        self.log("Searching for recovery sources...", "RECOVERY")
        recovery_result = recovery.recover(allow_cross_device=False)

        if recovery_result.success:
            self.log(
                f"Recovery successful from {recovery_result.source.value}",
                "RECOVERY"
            )

            if recovery_result.identity:
                self.log(
                    f"Snapshot ID: {recovery_result.identity.snapshot_id.hex()[:16]}...",
                    "RECOVERY"
                )
                self.log(
                    f"Generation: {recovery_result.identity.generation}",
                    "RECOVERY"
                )
        else:
            self.log(
                f"Recovery failed: {recovery_result.error}",
                "RECOVERY"
            )
            self.log("Using default state", "RECOVERY")

        # Stage 4: Lumenis Reactor
        self.log("Lumenis Reactor initializing...", "REACTOR")
        reactor = LumenisReactor(recovery_result.state)

        # Update identity
        reactor.update_identity(
            boot_time=time.time(),
            boot_source=recovery_result.source.value
        )

        self.log("State loaded and validated", "REACTOR")
        self.log("Runtime components initialized", "REACTOR")

        # Stage 5: Snapshot Manager
        self.log("Snapshot Manager initializing...", "SNAPSHOT")
        snapshot_manager = SnapshotManager(reactor, self.base_dir)
        self.log("Snapshot Manager ready", "SNAPSHOT")

        # Stage 6: System Online
        boot_time = (time.time() - self.boot_start) * 1000
        self.log("=" * 60, "")
        self.log(f"ONE2LVOS ONLINE ({boot_time:.0f}ms)", "SYSTEM")
        self.log("=" * 60, "")

        # Print stats
        stats = reactor.get_stats()
        self.log(f"VFS files: {stats['vfs_files']}", "STATS")
        self.log(f"Memory entries: {stats['memory_entries']}", "STATS")
        self.log(f"Pending tasks: {stats['pending_tasks']}", "STATS")

        return reactor, snapshot_manager, recovery_result


class One2lvOS:
    """
    One2lvOS main class - complete operating system.
    """

    def __init__(self, base_dir: str = "/tmp/one2lvos", auto_snapshot: bool = True):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.reactor: Optional[LumenisReactor] = None
        self.snapshot_manager: Optional[SnapshotManager] = None
        self.recovery_result = None
        self.boot_sequence = None

        # Boot
        self._boot()

        # Start auto-snapshot if requested
        if auto_snapshot:
            self.snapshot_manager.auto_snapshot_loop(interval_seconds=300)

    def _boot(self):
        """Execute boot sequence"""
        boot = BootSequence(str(self.base_dir), verbose=True)
        self.reactor, self.snapshot_manager, self.recovery_result = boot.boot()
        self.boot_sequence = boot

    def reboot(self):
        """Reboot the system"""
        print("\n[REBOOT] Rebooting One2lvOS...\n")

        # Create final snapshot before reboot
        self.snapshot_manager.create_snapshot()

        # Re-execute boot sequence
        self._boot()

    def shutdown(self):
        """Shutdown the system"""
        print("\n[SHUTDOWN] Shutting down One2lvOS...")

        # Create final snapshot
        identity = self.snapshot_manager.create_snapshot()
        print(f"[SHUTDOWN] Final snapshot created (gen={identity.generation})")

        print("[SHUTDOWN] One2lvOS powered off")

    def create_snapshot(self):
        """Manually create snapshot"""
        identity = self.snapshot_manager.create_snapshot()
        print(f"[SNAPSHOT] Created snapshot {identity.snapshot_id.hex()[:16]}...")
        print(f"[SNAPSHOT] Generation: {identity.generation}")
        return identity

    def export_snapshot(self, output_path: str) -> str:
        """Export snapshot to file"""
        path = self.snapshot_manager.export_snapshot(output_path)
        print(f"[EXPORT] Snapshot exported to {path}")
        return path

    def get_state(self) -> dict:
        """Get current state"""
        return self.reactor.get_state()

    def get_stats(self) -> dict:
        """Get system statistics"""
        return self.reactor.get_stats()

    # Convenience methods for common operations

    def write_file(self, path: str, content: str):
        """Write file to VFS"""
        self.reactor.vfs_create_file(path, content)
        print(f"[VFS] Created {path}")

    def read_file(self, path: str) -> Optional[str]:
        """Read file from VFS"""
        content = self.reactor.vfs_read_file(path)
        if content is None:
            print(f"[VFS] File not found: {path}")
        return content

    def list_dir(self, path: str = "/") -> list:
        """List directory"""
        files = self.reactor.vfs_list_dir(path)
        print(f"[VFS] {path}: {', '.join(files) if files else '(empty)'}")
        return files

    def set_config(self, section: str, config: dict):
        """Set configuration"""
        self.reactor.update_configuration(section, config)
        print(f"[CONFIG] Updated {section}")

    def add_memory(self, key: str, value):
        """Add to key-value memory"""
        self.reactor.memory_add(key, value)
        print(f"[MEMORY] Added {key}")

    def get_memory(self, key: str):
        """Get from key-value memory"""
        return self.reactor.memory_get(key)

    def add_task(self, description: str, priority: int = 0):
        """Add task"""
        task = {
            "description": description,
            "priority": priority
        }
        self.reactor.task_add(task)
        print(f"[TASK] Added: {description}")

    def status(self):
        """Print system status"""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print("ONE2LVOS STATUS")
        print("=" * 60)
        print(f"Uptime:          {stats['uptime']:.1f}s")
        print(f"Mutations:       {stats['mutations']}")
        print(f"Last snapshot:   {stats['last_snapshot']:.1f}s ago")
        print(f"VFS files:       {stats['vfs_files']}")
        print(f"Memory entries:  {stats['memory_entries']}")
        print(f"Pending tasks:   {stats['pending_tasks']}")
        print(f"Generation:      {self.snapshot_manager.current_generation}")
        print("=" * 60)

    def shell(self):
        """Interactive shell"""
        print("\nOne2lvOS Interactive Shell")
        print("Commands: write, read, ls, config, memory, task, snapshot, status, reboot, exit")

        while True:
            try:
                cmd = input("\none2lvos> ").strip()

                if not cmd:
                    continue

                parts = cmd.split(maxsplit=1)
                command = parts[0].lower()

                if command == "exit":
                    break

                elif command == "write":
                    if len(parts) < 2:
                        print("Usage: write <path> <content>")
                        continue
                    path_content = parts[1].split(maxsplit=1)
                    if len(path_content) < 2:
                        print("Usage: write <path> <content>")
                        continue
                    self.write_file(path_content[0], path_content[1])

                elif command == "read":
                    if len(parts) < 2:
                        print("Usage: read <path>")
                        continue
                    content = self.read_file(parts[1])
                    if content:
                        print(content)

                elif command == "ls":
                    path = parts[1] if len(parts) > 1 else "/"
                    self.list_dir(path)

                elif command == "snapshot":
                    self.create_snapshot()

                elif command == "status":
                    self.status()

                elif command == "reboot":
                    self.reboot()
                    print("\nSystem rebooted. Type 'exit' to quit shell.")

                elif command == "help":
                    print("""
Available commands:
  write <path> <content>  - Write file
  read <path>             - Read file
  ls [path]               - List directory
  snapshot                - Create snapshot
  status                  - Show system status
  reboot                  - Reboot system
  exit                    - Exit shell
""")

                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"Error: {e}")

        self.shutdown()
