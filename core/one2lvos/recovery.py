"""
Recovery Manager
================

Handles snapshot recovery with staging, quarantine, and transactional restoration.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

from .protocol import O2PNGDecoder, EnvelopeValidator, SnapshotIdentity


class RecoverySource(Enum):
    """Recovery source types"""
    LOCAL_PRIMARY = "local_primary"
    LOCAL_BACKUP = "local_backup"
    LOCAL_HISTORY = "local_history"
    CLOUD = "cloud"
    RAW_JSON = "raw_json"
    DEFAULT = "default"


@dataclass
class RecoveryResult:
    """Result of recovery attempt"""
    success: bool
    source: RecoverySource
    identity: Optional[SnapshotIdentity]
    error: Optional[str]
    state: Optional[dict]


class RecoveryManager:
    """
    Manages snapshot recovery with:
    - Multiple recovery sources
    - Quarantine for untrusted sources
    - Staged restoration
    - Transactional commit
    - Rollback on failure
    """

    def __init__(self, base_dir: str = "/tmp/one2lvos"):
        self.base_dir = Path(base_dir)
        self.snapshots_dir = self.base_dir / "snapshots"
        self.staging_dir = self.base_dir / "staging"
        self.quarantine_dir = self.base_dir / "quarantine"

        # Ensure directories exist
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        self.current_generation = 0
        self.current_device_id = self._load_or_create_device_id()

    def _load_or_create_device_id(self) -> bytes:
        """Load or create persistent device ID"""
        device_id_file = self.base_dir / "device_id"

        if device_id_file.exists():
            return device_id_file.read_bytes()

        # Create new device ID
        import uuid
        device_id = uuid.uuid4().bytes
        device_id_file.write_bytes(device_id)
        return device_id

    def recover(self, allow_cross_device: bool = False) -> RecoveryResult:
        """
        Attempt recovery from multiple sources in priority order.

        Recovery priority:
        1. Local primary snapshot
        2. Local backup snapshot
        3. Local snapshot history
        4. Cloud snapshot (if configured)
        5. Raw JSON state
        6. Default state
        """

        sources = [
            (RecoverySource.LOCAL_PRIMARY, self._try_local_primary),
            (RecoverySource.LOCAL_BACKUP, self._try_local_backup),
            (RecoverySource.LOCAL_HISTORY, self._try_local_history),
            (RecoverySource.RAW_JSON, self._try_raw_json),
            (RecoverySource.DEFAULT, self._try_default),
        ]

        for source_type, recovery_fn in sources:
            try:
                result = recovery_fn(allow_cross_device)
                if result.success:
                    return result
            except Exception as e:
                print(f"[RECOVERY] {source_type.value} failed: {e}")
                continue

        # All sources exhausted
        return RecoveryResult(
            success=False,
            source=RecoverySource.DEFAULT,
            identity=None,
            error="All recovery sources exhausted",
            state=None
        )

    def _try_local_primary(self, allow_cross_device: bool) -> RecoveryResult:
        """Try local primary snapshot"""
        snapshot_path = self.snapshots_dir / "boot.o2png"

        if not snapshot_path.exists():
            raise FileNotFoundError("Primary snapshot not found")

        return self._restore_from_local(
            snapshot_path,
            RecoverySource.LOCAL_PRIMARY,
            allow_cross_device
        )

    def _try_local_backup(self, allow_cross_device: bool) -> RecoveryResult:
        """Try local backup snapshot"""
        snapshot_path = self.snapshots_dir / "boot.o2png.backup"

        if not snapshot_path.exists():
            raise FileNotFoundError("Backup snapshot not found")

        return self._restore_from_local(
            snapshot_path,
            RecoverySource.LOCAL_BACKUP,
            allow_cross_device
        )

    def _try_local_history(self, allow_cross_device: bool) -> RecoveryResult:
        """Try local snapshot history"""
        history_dir = self.snapshots_dir / "history"

        if not history_dir.exists():
            raise FileNotFoundError("Snapshot history not found")

        # Find most recent valid snapshot
        snapshots = sorted(history_dir.glob("*.o2png"), reverse=True)

        for snapshot_path in snapshots:
            try:
                return self._restore_from_local(
                    snapshot_path,
                    RecoverySource.LOCAL_HISTORY,
                    allow_cross_device
                )
            except Exception:
                continue

        raise FileNotFoundError("No valid snapshots in history")

    def _try_raw_json(self, allow_cross_device: bool) -> RecoveryResult:
        """Try raw JSON state file"""
        state_path = self.snapshots_dir / "state.json"

        if not state_path.exists():
            raise FileNotFoundError("Raw JSON state not found")

        state = json.loads(state_path.read_text())

        return RecoveryResult(
            success=True,
            source=RecoverySource.RAW_JSON,
            identity=None,
            error=None,
            state=state
        )

    def _try_default(self, allow_cross_device: bool) -> RecoveryResult:
        """Create default state"""
        state = {
            "identity": {
                "install_uuid": str(self.current_device_id.hex()),
                "device_name": "one2lvos-default"
            },
            "configuration": {},
            "vfs": {
                "root": {
                    "home": {}
                }
            },
            "persistent_memory": {
                "vector_memory": [],
                "key_value_store": {}
            },
            "task_state": {
                "pending_tasks": []
            },
            "runtime_hints": {
                "services_to_restart": []
            }
        }

        return RecoveryResult(
            success=True,
            source=RecoverySource.DEFAULT,
            identity=None,
            error=None,
            state=state
        )

    def _restore_from_local(
        self,
        snapshot_path: Path,
        source: RecoverySource,
        allow_cross_device: bool
    ) -> RecoveryResult:
        """
        Restore from local snapshot with transactional staging.

        Process:
        1. Validate envelope
        2. Check generation (rollback detection)
        3. Stage snapshot
        4. Rehydrate to staging
        5. Verify restored state
        6. Commit (atomic)
        """

        # 1. Load and decode envelope
        envelope = snapshot_path.read_bytes()
        decoder = O2PNGDecoder(envelope)

        try:
            state, identity = decoder.decode()
        except Exception as e:
            raise ValueError(f"Envelope decode failed: {e}")

        # 2. Validate generation (rollback detection)
        try:
            EnvelopeValidator.validate_generation(
                identity.generation,
                self.current_generation,
                allow_rollback=False
            )
        except ValueError as e:
            raise ValueError(f"Generation validation failed: {e}")

        # 3. Validate device
        try:
            EnvelopeValidator.validate_device(
                identity,
                self.current_device_id,
                allow_cross_device=allow_cross_device
            )
        except ValueError as e:
            if not allow_cross_device:
                raise ValueError(f"Device validation failed: {e}")
            print(f"[WARN] Cross-device restore: {e}")

        # 4. Stage restoration
        staging_path = self._create_staging_area()

        try:
            # Write staged state
            staged_state_path = staging_path / "state.json"
            staged_state_path.write_text(
                json.dumps(state, indent=2)
            )

            # Write staging metadata
            staging_meta = {
                "snapshot_id": identity.snapshot_id.hex(),
                "generation": identity.generation,
                "created_at": identity.created_at,
                "source": source.value
            }
            (staging_path / "metadata.json").write_text(
                json.dumps(staging_meta, indent=2)
            )

            # 5. Verify staged state
            self._verify_staged_state(state)

            # 6. Commit (atomic)
            self._commit_staged_state(staging_path)

            # Update current generation
            self.current_generation = identity.generation

            return RecoveryResult(
                success=True,
                source=source,
                identity=identity,
                error=None,
                state=state
            )

        except Exception as e:
            # Rollback on failure
            self._discard_staging(staging_path)
            raise ValueError(f"Staged restoration failed: {e}")

    def _create_staging_area(self) -> Path:
        """Create isolated staging area"""
        # Clear existing staging
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir)

        self.staging_dir.mkdir(parents=True, exist_ok=True)
        return self.staging_dir

    def _verify_staged_state(self, state: dict):
        """Verify staged state validity"""
        # Schema validation
        required_keys = ["identity", "configuration", "vfs", "persistent_memory"]

        for key in required_keys:
            if key not in state:
                raise ValueError(f"Missing required state key: {key}")

        # VFS validation
        if "root" not in state["vfs"]:
            raise ValueError("VFS missing root")

    def _commit_staged_state(self, staging_path: Path):
        """Commit staged state (atomic operation)"""
        # In production, this would use atomic filesystem operations
        # For now, just mark as committed
        commit_flag = staging_path / "commit.flag"
        commit_flag.touch()

    def _discard_staging(self, staging_path: Path):
        """Discard staged state on failure"""
        if staging_path.exists():
            shutil.rmtree(staging_path)

    def quarantine_network_snapshot(self, data: bytes, source_url: str) -> Path:
        """
        Quarantine network snapshot before validation.

        Network sources are UNTRUSTED until verified.
        """
        import uuid
        quarantine_id = uuid.uuid4().hex[:8]
        quarantine_path = self.quarantine_dir / f"download-{quarantine_id}.temp"

        # Write to quarantine
        quarantine_path.write_bytes(data)

        # Create quarantine log
        log_path = self.quarantine_dir / f"download-{quarantine_id}.log"
        log_data = {
            "source_url": source_url,
            "size": len(data),
            "quarantine_time": int(time.time())
        }
        log_path.write_text(json.dumps(log_data, indent=2))

        return quarantine_path

    def validate_quarantined(self, quarantine_path: Path) -> bool:
        """
        Validate quarantined snapshot before moving to trusted zone.

        Checks:
        1. Size limits
        2. Format validity
        3. Envelope structure
        4. Digest verification
        """
        # Size check
        size = quarantine_path.stat().st_size
        if size > 100 * 1024 * 1024:  # 100 MB limit
            raise ValueError(f"Snapshot exceeds size limit: {size} bytes")

        # Load envelope
        envelope = quarantine_path.read_bytes()

        # Validate envelope structure
        try:
            decoder = O2PNGDecoder(envelope)
            decoder._parse_header()
            decoder._verify_digest()
        except Exception as e:
            raise ValueError(f"Envelope validation failed: {e}")

        return True

    def move_to_trusted(self, quarantine_path: Path) -> Path:
        """Move quarantined snapshot to trusted zone after validation"""
        trusted_path = self.snapshots_dir / quarantine_path.name.replace(".temp", ".o2png")
        shutil.move(str(quarantine_path), str(trusted_path))

        # Cleanup quarantine log
        log_path = quarantine_path.with_suffix(".log")
        if log_path.exists():
            log_path.unlink()

        return trusted_path
