#!/usr/bin/env python3
"""
🌊 TASK PULSE GENERATOR
=======================
Continuous task generation for the swarm execution layer.
Creates synthetic workload for testing and demonstration.
"""

import json
import time
import uuid
import random
from pathlib import Path
from typing import List


TASK_TYPES = [
    "reasoning",
    "memory",
    "routing",
    "analysis",
    "synthesis",
    "oracle",
    "forge",
    "navigator",
]


class TaskPulse:
    """Generates tasks for the swarm to process."""

    def __init__(self, task_dir: Path = None, interval: float = 3.0):
        self.task_dir = task_dir or Path(__file__).resolve().parent / "tasks"
        self.interval = interval
        self.running = False
        self.generated_count = 0

        # Ensure task directory exists
        self.task_dir.mkdir(parents=True, exist_ok=True)

    def generate_task(self) -> dict:
        """Generate a random task."""
        task_id = uuid.uuid4().hex[:8]
        task = {
            "id": task_id,
            "type": random.choice(TASK_TYPES),
            "created": time.time(),
            "priority": random.randint(1, 5),
            "complexity": random.choice(["low", "medium", "high"]),
        }
        return task

    def emit_task(self, task: dict):
        """Write task to queue."""
        task_file = self.task_dir / f"{task['id']}.json"
        task_file.write_text(json.dumps(task, indent=2))
        print(f"📨 task queued: {task['type']} (priority: {task['priority']})")
        self.generated_count += 1

    def run(self, max_tasks: int = None):
        """Run the task generator."""
        self.running = True
        print("🌊 TASK PULSE ONLINE")

        while self.running:
            if max_tasks and self.generated_count >= max_tasks:
                break

            task = self.generate_task()
            self.emit_task(task)

            time.sleep(self.interval)

    def stop(self):
        """Stop the task generator."""
        self.running = False
        print(f"🛑 TASK PULSE OFFLINE (generated {self.generated_count} tasks)")

    def get_status(self) -> dict:
        """Get current pulse status."""
        return {
            "generated": self.generated_count,
            "running": self.running,
            "interval": self.interval,
        }


def main():
    """Standalone task pulse execution."""
    pulse = TaskPulse()
    try:
        pulse.run()
    except KeyboardInterrupt:
        pulse.stop()


if __name__ == "__main__":
    main()
