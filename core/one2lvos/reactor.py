"""
Lumenis Reactor
===============

Active state management for One2lvOS.
"""

import time
import json
from typing import Dict, Any, Optional
from pathlib import Path


class LumenisReactor:
    """
    The Lumenis Reactor manages active runtime state.

    Responsibilities:
    - Maintain live state
    - Handle state mutations
    - Trigger snapshot creation
    - Provide state query API
    - Manage runtime components
    """

    def __init__(self, initial_state: Optional[dict] = None):
        self.state = initial_state or self._default_state()
        self.start_time = time.time()
        self.mutation_count = 0
        self.last_snapshot_time = time.time()

    def _default_state(self) -> dict:
        """Create default empty state"""
        return {
            "identity": {
                "install_uuid": None,
                "device_name": "one2lvos",
                "boot_time": time.time()
            },
            "configuration": {
                "system": {},
                "user": {}
            },
            "vfs": {
                "root": {
                    "home": {},
                    "var": {},
                    "etc": {}
                }
            },
            "persistent_memory": {
                "vector_memory": [],
                "key_value_store": {},
                "event_journal": []
            },
            "task_state": {
                "pending_tasks": [],
                "scheduled_jobs": []
            },
            "runtime_hints": {
                "services_to_restart": [],
                "windows_to_restore": [],
                "subscriptions": []
            }
        }

    def get_state(self) -> dict:
        """Get current state (read-only)"""
        return self.state.copy()

    def get_persistent_state(self) -> dict:
        """
        Get persistent state (without runtime hints).

        This is what gets serialized to snapshots.
        """
        persistent = self.state.copy()

        # Runtime hints are guidance, not persistent data
        if "runtime_hints" in persistent:
            del persistent["runtime_hints"]

        return persistent

    def update_identity(self, **kwargs):
        """Update identity information"""
        self.state["identity"].update(kwargs)
        self.mutation_count += 1

    def update_configuration(self, section: str, config: dict):
        """Update configuration section"""
        if section not in self.state["configuration"]:
            self.state["configuration"][section] = {}

        self.state["configuration"][section].update(config)
        self.mutation_count += 1

    def vfs_create_file(self, path: str, content: str):
        """Create or update file in VFS"""
        parts = path.strip('/').split('/')
        current = self.state["vfs"]["root"]

        # Navigate to parent directory
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Create file
        filename = parts[-1]
        current[filename] = content
        self.mutation_count += 1

    def vfs_read_file(self, path: str) -> Optional[str]:
        """Read file from VFS"""
        parts = path.strip('/').split('/')
        current = self.state["vfs"]["root"]

        try:
            for part in parts:
                current = current[part]
            return current if isinstance(current, str) else None
        except (KeyError, TypeError):
            return None

    def vfs_list_dir(self, path: str = "/") -> list:
        """List directory contents"""
        if path == "/":
            current = self.state["vfs"]["root"]
        else:
            parts = path.strip('/').split('/')
            current = self.state["vfs"]["root"]

            try:
                for part in parts:
                    current = current[part]
            except (KeyError, TypeError):
                return []

        if isinstance(current, dict):
            return list(current.keys())
        return []

    def memory_add(self, key: str, value: Any):
        """Add to key-value store"""
        self.state["persistent_memory"]["key_value_store"][key] = value
        self.mutation_count += 1

    def memory_get(self, key: str) -> Any:
        """Get from key-value store"""
        return self.state["persistent_memory"]["key_value_store"].get(key)

    def memory_add_vector(self, text: str, vector: list):
        """Add to vector memory"""
        self.state["persistent_memory"]["vector_memory"].append({
            "id": len(self.state["persistent_memory"]["vector_memory"]) + 1,
            "text": text,
            "vector": vector,
            "timestamp": time.time()
        })
        self.mutation_count += 1

    def journal_append(self, event: dict):
        """Append to event journal"""
        event["timestamp"] = time.time()
        self.state["persistent_memory"]["event_journal"].append(event)
        self.mutation_count += 1

    def task_add(self, task: dict):
        """Add pending task"""
        task["id"] = len(self.state["task_state"]["pending_tasks"]) + 1
        task["created_at"] = time.time()
        self.state["task_state"]["pending_tasks"].append(task)
        self.mutation_count += 1

    def task_complete(self, task_id: int):
        """Mark task as complete"""
        self.state["task_state"]["pending_tasks"] = [
            t for t in self.state["task_state"]["pending_tasks"]
            if t.get("id") != task_id
        ]
        self.mutation_count += 1

    def runtime_hint_service(self, name: str, config: dict):
        """Add service restart hint"""
        self.state["runtime_hints"]["services_to_restart"].append({
            "name": name,
            "config": config
        })

    def runtime_hint_window(self, title: str, geometry: str):
        """Add window restore hint"""
        self.state["runtime_hints"]["windows_to_restore"].append({
            "title": title,
            "geometry": geometry
        })

    def needs_snapshot(self, interval_seconds: int = 300) -> bool:
        """Check if snapshot is needed"""
        time_since_last = time.time() - self.last_snapshot_time
        return time_since_last >= interval_seconds

    def mark_snapshot_taken(self):
        """Mark that snapshot was taken"""
        self.last_snapshot_time = time.time()

    def get_stats(self) -> dict:
        """Get reactor statistics"""
        return {
            "uptime": time.time() - self.start_time,
            "mutations": self.mutation_count,
            "last_snapshot": time.time() - self.last_snapshot_time,
            "vfs_files": self._count_vfs_files(),
            "memory_entries": len(self.state["persistent_memory"]["key_value_store"]),
            "pending_tasks": len(self.state["task_state"]["pending_tasks"])
        }

    def _count_vfs_files(self) -> int:
        """Count total files in VFS"""
        def count_recursive(node):
            if isinstance(node, str):
                return 1
            elif isinstance(node, dict):
                return sum(count_recursive(v) for v in node.values())
            return 0

        return count_recursive(self.state["vfs"]["root"])
