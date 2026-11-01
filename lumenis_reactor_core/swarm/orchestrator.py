"""
🎭 SWARM ORCHESTRATOR
=====================
High-level API for managing the distributed swarm execution layer.
Integrates with the Lumenis Reactor Core.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading

from .worker_node import WorkerNode
from .task_pulse import TaskPulse
from .swarm_monitor import SwarmMonitor


class SwarmOrchestrator:
    """
    Orchestrates the swarm execution layer.
    Manages worker nodes, task generation, and monitoring.
    """

    def __init__(self, root_dir: Path = None, num_workers: int = 3):
        self.root = root_dir or Path(__file__).resolve().parent
        self.num_workers = num_workers

        # Components
        self.workers: List[WorkerNode] = []
        self.pulse: Optional[TaskPulse] = None
        self.monitor: Optional[SwarmMonitor] = None

        # Threading
        self._threads: List[threading.Thread] = []
        self._running = False

    def initialize(self):
        """Initialize swarm components."""
        # Create worker nodes
        for i in range(self.num_workers):
            worker = WorkerNode(
                node_id=f"worker-{i+1:02d}",
                root_dir=self.root
            )
            self.workers.append(worker)

        # Create task pulse
        self.pulse = TaskPulse(
            task_dir=self.root / "tasks",
            interval=3.0
        )

        # Create monitor
        self.monitor = SwarmMonitor(
            state_file=self.root / "runtime" / "swarm_state.json"
        )

        print(f"🧠 Swarm initialized with {self.num_workers} workers")

    def start_workers(self):
        """Start all worker nodes in separate threads."""
        for worker in self.workers:
            thread = threading.Thread(
                target=worker.run,
                daemon=True,
                name=f"SwarmWorker-{worker.node_id}"
            )
            thread.start()
            self._threads.append(thread)

    def start_pulse(self):
        """Start the task pulse generator."""
        thread = threading.Thread(
            target=self.pulse.run,
            daemon=True,
            name="TaskPulse"
        )
        thread.start()
        self._threads.append(thread)

    def start(self):
        """Start the entire swarm system."""
        if self._running:
            return

        self.initialize()
        self._running = True

        print("🚀 Starting swarm execution layer...")

        # Start components
        self.start_workers()
        self.start_pulse()

        print("✅ Swarm execution layer online")

    def stop(self):
        """Stop all swarm components."""
        if not self._running:
            return

        print("🛑 Stopping swarm execution layer...")

        # Stop workers
        for worker in self.workers:
            worker.stop()

        # Stop pulse
        if self.pulse:
            self.pulse.stop()

        self._running = False
        print("✅ Swarm execution layer offline")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status."""
        if not self.monitor:
            return {"error": "Swarm not initialized"}

        metrics = self.monitor.get_metrics()

        # Add worker details
        worker_status = [
            {
                "node_id": w.node_id,
                "processed": w.processed_count,
                "running": w.running,
            }
            for w in self.workers
        ]

        return {
            "running": self._running,
            "workers": worker_status,
            "metrics": metrics,
            "pulse": {
                "generated": self.pulse.generated_count if self.pulse else 0,
                "running": self.pulse.running if self.pulse else False,
            },
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get current swarm metrics."""
        if not self.monitor:
            return {}

        return self.monitor.get_metrics()

    async def submit_task(self, task_type: str, data: dict = None) -> str:
        """
        Submit a task to the swarm queue.
        Returns task ID.
        """
        import uuid
        import json
        import time

        task_id = uuid.uuid4().hex[:8]
        task = {
            "id": task_id,
            "type": task_type,
            "data": data or {},
            "created": time.time(),
        }

        task_file = self.root / "tasks" / f"{task_id}.json"
        task_file.write_text(json.dumps(task, indent=2))

        return task_id

    def clear_queue(self):
        """Clear all pending tasks."""
        task_dir = self.root / "tasks"
        for task_file in task_dir.glob("*.json"):
            task_file.unlink()

        print("🗑️  Task queue cleared")


# Standalone execution
def main():
    """Run the swarm orchestrator as a standalone service."""
    orchestrator = SwarmOrchestrator(num_workers=5)

    try:
        orchestrator.start()

        # Keep running
        import time
        while True:
            time.sleep(10)
            status = orchestrator.get_status()
            print(f"\n📊 Swarm Status: {status['metrics']['total_processed']} tasks processed")

    except KeyboardInterrupt:
        orchestrator.stop()


if __name__ == "__main__":
    main()
