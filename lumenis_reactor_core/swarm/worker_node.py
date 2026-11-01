#!/usr/bin/env python3
"""
🧠 SWARM WORKER NODE
===================
Autonomous task processing node with heartbeat and state management.
Part of the Lumenis Reactor distributed execution layer.
"""

import os
import json
import time
import uuid
import random
from pathlib import Path
from typing import Dict, Any


class WorkerNode:
    """Individual worker node in the swarm execution layer."""

    def __init__(self, node_id: str = None, root_dir: Path = None):
        self.node_id = node_id or f"worker-{uuid.uuid4().hex[:6]}"
        self.root = root_dir or Path(__file__).resolve().parent
        self.state_file = self.root / "runtime" / "swarm_state.json"
        self.task_dir = self.root / "tasks"
        self.running = False
        self.processed_count = 0

        # Ensure directories exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.task_dir.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> Dict[str, Any]:
        """Load current swarm state from disk."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                pass

        return {
            "active_nodes": {},
            "processed_tasks": 0,
            "heartbeat": {},
            "queue_depth": 0,
            "last_update": time.time(),
        }

    def save_state(self, state: Dict[str, Any]):
        """Persist swarm state to disk."""
        state["last_update"] = time.time()
        self.state_file.write_text(json.dumps(state, indent=2))

    def process_task(self, task_file: Path) -> bool:
        """Process a single task from the queue."""
        try:
            data = json.loads(task_file.read_text())
            task_type = data.get("type", "unknown")

            print(f"⚡ {self.node_id} processing: {task_type}")

            # Simulate processing time
            time.sleep(random.uniform(0.2, 1.5))

            # Task completed - remove from queue
            task_file.unlink()
            self.processed_count += 1

            return True

        except Exception as e:
            print(f"❌ {self.node_id} task error: {e}")
            return False

    def heartbeat(self):
        """Send heartbeat to swarm state."""
        state = self.load_state()

        # Update this node's heartbeat
        state["active_nodes"][self.node_id] = {
            "last_seen": time.time(),
            "status": "online",
            "processed": self.processed_count,
        }

        # Update global processed count
        state["processed_tasks"] = sum(
            node.get("processed", 0)
            for node in state["active_nodes"].values()
        )

        # Update queue depth
        state["queue_depth"] = len(list(self.task_dir.glob("*.json")))

        self.save_state(state)

    def run(self, max_iterations: int = None):
        """Main worker loop - process tasks and send heartbeats."""
        self.running = True
        print(f"🧠 WORKER ONLINE: {self.node_id}")

        iteration = 0
        while self.running:
            if max_iterations and iteration >= max_iterations:
                break

            # Send heartbeat
            self.heartbeat()

            # Process tasks
            tasks = list(self.task_dir.glob("*.json"))
            if tasks:
                self.process_task(tasks[0])

            # Sleep before next cycle
            time.sleep(1.0)
            iteration += 1

    def stop(self):
        """Gracefully stop the worker."""
        self.running = False
        print(f"🛑 WORKER OFFLINE: {self.node_id}")

    def get_status(self) -> Dict[str, Any]:
        """Get current worker status."""
        return {
            "node_id": self.node_id,
            "processed": self.processed_count,
            "running": self.running,
        }


def main():
    """Standalone worker node execution."""
    node = WorkerNode()
    try:
        node.run()
    except KeyboardInterrupt:
        node.stop()


if __name__ == "__main__":
    main()
