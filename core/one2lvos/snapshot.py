"""
Snapshot Manager
================

Handles snapshot creation, persistence, and rotation.
"""

import json
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from .protocol import O2PNGEncoder, SnapshotIdentity
from .reactor import LumenisReactor


class SnapshotManager:
    """
    Manages snapshot lifecycle:
    - Create snapshots from reactor state
    - Persist to multiple destinations (local, cloud, raw)
    - Rotation policy
    - Snapshot history
    """

    def __init__(
        self,
        reactor: LumenisReactor,
        base_dir: str = "/tmp/one2lvos",
        device_id: Optional[bytes] = None
    ):
        self.reactor = reactor
        self.base_dir = Path(base_dir)
        self.snapshots_dir = self.base_dir / "snapshots"
        self.history_dir = self.snapshots_dir / "history"

        # Ensure directories exist
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self.device_id = device_id or self._load_device_id()
        self.current_generation = self._load_generation()
        self.parent_snapshot_id = None

    def _load_device_id(self) -> bytes:
        """Load device ID"""
        device_id_file = self.base_dir / "device_id"

        if device_id_file.exists():
            return device_id_file.read_bytes()

        # Create new
        import uuid
        device_id = uuid.uuid4().bytes
        device_id_file.write_bytes(device_id)
        return device_id

    def _load_generation(self) -> int:
        """Load current generation number"""
        gen_file = self.base_dir / "generation"

        if gen_file.exists():
            return int(gen_file.read_text())

        return 0

    def _save_generation(self, generation: int):
        """Save current generation number"""
        gen_file = self.base_dir / "generation"
        gen_file.write_text(str(generation))

    def create_snapshot(self, compress: bool = True) -> SnapshotIdentity:
        """
        Create snapshot from current reactor state.

        Returns snapshot identity.
        """
        # Get persistent state (no runtime hints)
        state = self.reactor.get_persistent_state()

        # Increment generation
        self.current_generation += 1

        # Create encoder
        encoder = O2PNGEncoder(
            state=state,
            device_id=self.device_id,
            parent_snapshot_id=self.parent_snapshot_id,
            generation=self.current_generation,
            compress=compress
        )

        # Encode envelope
        envelope = encoder.encode()

        # Save to multiple destinations
        self._save_local_primary(envelope)
        self._save_local_history(envelope, encoder.snapshot_id)
        self._save_raw_json(state)

        # Update metadata
        self.parent_snapshot_id = encoder.snapshot_id
        self._save_generation(self.current_generation)

        # Mark snapshot taken
        self.reactor.mark_snapshot_taken()

        # Return identity
        return SnapshotIdentity(
            snapshot_id=encoder.snapshot_id,
            generation=self.current_generation,
            parent_snapshot_id=encoder.parent_snapshot_id or bytes(16),
            created_at=encoder.created_at,
            source_device_id=encoder.device_id,
            schema_version=encoder.schema_version,
            runtime_version=encoder.runtime_version
        )

    def _save_local_primary(self, envelope: bytes):
        """Save as primary boot snapshot"""
        primary_path = self.snapshots_dir / "boot.o2png"
        backup_path = self.snapshots_dir / "boot.o2png.backup"

        # Backup existing primary
        if primary_path.exists():
            primary_path.rename(backup_path)

        # Write new primary
        primary_path.write_bytes(envelope)

    def _save_local_history(self, envelope: bytes, snapshot_id: bytes):
        """Save to snapshot history"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        snapshot_name = f"{timestamp}-{snapshot_id.hex()[:8]}.o2png"
        history_path = self.history_dir / snapshot_name

        history_path.write_bytes(envelope)

        # Rotate old snapshots
        self._rotate_history()

    def _save_raw_json(self, state: dict):
        """Save raw JSON for debugging"""
        state_path = self.snapshots_dir / "state.json"
        state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True)
        )

    def _rotate_history(self):
        """Rotate old snapshots (keep last 24)"""
        snapshots = sorted(self.history_dir.glob("*.o2png"))

        # Keep last 24 snapshots
        max_snapshots = 24

        if len(snapshots) > max_snapshots:
            # Remove oldest
            for snapshot in snapshots[:-max_snapshots]:
                snapshot.unlink()

    def auto_snapshot_loop(self, interval_seconds: int = 300):
        """
        Automatic snapshot creation loop.

        Runs in background and creates snapshots at regular intervals.
        """
        import threading

        def snapshot_worker():
            while True:
                try:
                    if self.reactor.needs_snapshot(interval_seconds):
                        self.create_snapshot()
                        print(f"[SNAPSHOT] Auto-snapshot created (gen={self.current_generation})")

                    time.sleep(interval_seconds)
                except Exception as e:
                    print(f"[SNAPSHOT] Error: {e}")
                    time.sleep(interval_seconds)

        thread = threading.Thread(target=snapshot_worker, daemon=True)
        thread.start()
        return thread

    def get_snapshot_list(self) -> list:
        """Get list of available snapshots"""
        snapshots = []

        # Primary
        primary_path = self.snapshots_dir / "boot.o2png"
        if primary_path.exists():
            snapshots.append({
                "type": "primary",
                "path": str(primary_path),
                "size": primary_path.stat().st_size,
                "mtime": primary_path.stat().st_mtime
            })

        # Backup
        backup_path = self.snapshots_dir / "boot.o2png.backup"
        if backup_path.exists():
            snapshots.append({
                "type": "backup",
                "path": str(backup_path),
                "size": backup_path.stat().st_size,
                "mtime": backup_path.stat().st_mtime
            })

        # History
        for history_file in sorted(self.history_dir.glob("*.o2png"), reverse=True):
            snapshots.append({
                "type": "history",
                "path": str(history_file),
                "size": history_file.stat().st_size,
                "mtime": history_file.stat().st_mtime
            })

        return snapshots

    def export_snapshot(self, output_path: str) -> str:
        """Export current snapshot to file"""
        state = self.reactor.get_persistent_state()

        encoder = O2PNGEncoder(
            state=state,
            device_id=self.device_id,
            parent_snapshot_id=self.parent_snapshot_id,
            generation=self.current_generation,
            compress=True
        )

        envelope = encoder.encode()

        output = Path(output_path)
        output.write_bytes(envelope)

        return str(output)
