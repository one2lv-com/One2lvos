#!/usr/bin/env python3
"""
📡 SWARM MONITOR
================
Real-time monitoring and visualization of swarm execution state.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any


class SwarmMonitor:
    """Monitor and report on swarm execution metrics."""

    def __init__(self, state_file: Path = None):
        self.state_file = state_file or (
            Path(__file__).resolve().parent / "runtime" / "swarm_state.json"
        )
        self.running = False

    def load_state(self) -> Dict[str, Any]:
        """Load current swarm state."""
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
        }

    def format_node_info(self, node_id: str, node_data: dict) -> str:
        """Format node information for display."""
        last_seen = node_data.get("last_seen", 0)
        age = time.time() - last_seen
        status = node_data.get("status", "unknown")
        processed = node_data.get("processed", 0)

        if age > 5:
            status = "stale"
        elif age > 10:
            status = "offline"

        return f"  • {node_id:20} | {status:8} | processed: {processed:4} | age: {age:.1f}s"

    def display_status(self):
        """Display current swarm status."""
        state = self.load_state()

        print("\n" + "="*70)
        print("📡 SWARM EXECUTION MONITOR")
        print("="*70)

        # Overall metrics
        print(f"\n🎯 METRICS:")
        print(f"  Total Tasks Processed: {state.get('processed_tasks', 0)}")
        print(f"  Queue Depth: {state.get('queue_depth', 0)}")
        print(f"  Active Nodes: {len(state.get('active_nodes', {}))}")

        # Node details
        nodes = state.get("active_nodes", {})
        if nodes:
            print(f"\n🧠 WORKER NODES:")
            for node_id, node_data in sorted(nodes.items()):
                print(self.format_node_info(node_id, node_data))
        else:
            print(f"\n🧠 WORKER NODES: None active")

        print("\n" + "="*70 + "\n")

    def run(self, interval: float = 2.0, max_iterations: int = None):
        """Run the monitor in a loop."""
        self.running = True
        print("📡 SWARM MONITOR ONLINE")

        iteration = 0
        while self.running:
            if max_iterations and iteration >= max_iterations:
                break

            self.display_status()
            time.sleep(interval)
            iteration += 1

    def stop(self):
        """Stop the monitor."""
        self.running = False
        print("🛑 SWARM MONITOR OFFLINE")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics as a dict."""
        state = self.load_state()

        nodes = state.get("active_nodes", {})
        active_count = sum(
            1 for node in nodes.values()
            if time.time() - node.get("last_seen", 0) < 5
        )

        return {
            "total_processed": state.get("processed_tasks", 0),
            "queue_depth": state.get("queue_depth", 0),
            "active_nodes": active_count,
            "total_nodes": len(nodes),
            "last_update": state.get("last_update", 0),
        }


def main():
    """Standalone monitor execution."""
    monitor = SwarmMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == "__main__":
    main()
