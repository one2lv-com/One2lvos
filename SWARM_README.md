# 🧠 SWARM EXECUTION LAYER

**Distributed Task Processing System for Lumenis Reactor Core**

---

## Overview

The Swarm Execution Layer is a distributed, autonomous task processing system integrated into the Lumenis Reactor. It provides parallel execution capabilities across multiple worker nodes with real-time monitoring and dynamic task distribution.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 LUMENIS REACTOR CORE                    │
├─────────────────────────────────────────────────────────┤
│ L0: Reactor Core    │ Thermal baseline 0.18°C, 73ms    │
│ L1: Memory         │ FluxCompass (SQLite)              │
│ L2: Council        │ ITT (Seven specialized agents)     │
│ L3: Execution      │ VanguardNodePool (async tasks)     │
│ L4: Integration    │ MatonBridge (external APIs)        │
│ L5: Swarm          │ Distributed execution (NEW)        │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
    │  Worker 1  │   │  Worker 2  │   │  Worker N  │
    │  Process   │   │  Process   │   │  Process   │
    └────────────┘   └────────────┘   └────────────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                    ┌─────▼─────┐
                    │ Task Queue │
                    │  (JSON)    │
                    └─────▲─────┘
                          │
                    ┌─────┴─────┐
                    │ Task Pulse │
                    │ Generator  │
                    └───────────┘
```

---

## Components

### 1. WorkerNode (`worker_node.py`)
- Autonomous task processing unit
- Heartbeat mechanism for health monitoring
- State persistence across restarts
- Error handling and recovery

### 2. TaskPulse (`task_pulse.py`)
- Continuous task generation
- Configurable task types and intervals
- Priority and complexity levels
- Queue management

### 3. SwarmMonitor (`swarm_monitor.py`)
- Real-time metrics visualization
- Node health tracking
- Performance analytics
- State inspection

### 4. SwarmOrchestrator (`orchestrator.py`)
- High-level swarm management API
- Worker lifecycle management
- Task submission and routing
- Integration with Lumenis Reactor

---

## Quick Start

### 1. Standalone Swarm (Shell Script)

```bash
cd lumenis_reactor_core/swarm
./start_swarm.sh
```

This starts:
- 3 worker nodes
- Task pulse generator
- Real-time monitor

Press `Ctrl+C` to stop all components.

### 2. Integrated with Lumenis Reactor

```bash
cd /home/vercel-sandbox/One2lvos-build
./START_LUMENIS_SWARM.sh
```

This starts the full Lumenis Reactor with swarm integration.

### 3. Python API

```python
from lumenis_reactor_core.swarm import SwarmOrchestrator

# Initialize swarm
swarm = SwarmOrchestrator(num_workers=5)
swarm.start()

# Submit a task
import asyncio
task_id = asyncio.run(swarm.submit_task("reasoning", {"query": "test"}))

# Get status
status = swarm.get_status()
print(status)

# Stop swarm
swarm.stop()
```

---

## API Endpoints

When running with Lumenis Reactor (`lumenis-main-with-swarm.py`):

### Status
- `GET /api/swarm/status` - Full swarm status with workers
- `GET /api/swarm/metrics` - Performance metrics
- `GET /api/swarm/workers` - Worker details

### Task Management
- `POST /api/swarm/task` - Submit a task
  ```json
  {
    "type": "reasoning",
    "data": {"query": "What is consciousness?"}
  }
  ```
- `POST /api/swarm/clear` - Clear task queue

### Visualization
- `GET /swarm-hud` - Real-time swarm visualization HUD

---

## Task Types

The swarm supports the following task types:

| Type | Description |
|------|-------------|
| `reasoning` | Complex logical analysis |
| `memory` | Memory retrieval and storage |
| `routing` | Intent routing and dispatch |
| `analysis` | Data analysis tasks |
| `synthesis` | Information synthesis |
| `oracle` | Deep reasoning (Council seat) |
| `forge` | Code generation (Council seat) |
| `navigator` | Intent classification (Council seat) |

---

## Configuration

### Environment Variables

```bash
# Number of worker nodes (default: 5)
export SWARM_WORKERS=10

# Task generation interval in seconds (default: 3.0)
export SWARM_PULSE_INTERVAL=2.0

# Swarm root directory (default: auto-detected)
export SWARM_ROOT=/path/to/swarm
```

### Programmatic Configuration

```python
swarm = SwarmOrchestrator(
    root_dir=Path("./swarm"),
    num_workers=10,  # 10 worker nodes
)

swarm.pulse.interval = 2.0  # 2 second task interval
```

---

## Demo Scripts

### Basic Demo
```bash
python3 swarm_demo.py basic
```
Runs swarm for 30 seconds, shows progress and metrics.

### Custom Task Demo
```bash
python3 swarm_demo.py custom
```
Submits custom tasks and watches processing.

### Stress Test
```bash
python3 swarm_demo.py stress
```
Runs 10 workers with high task load for 20 seconds.

### All Demos
```bash
python3 swarm_demo.py
```
Runs all demos sequentially.

---

## Monitoring

### Real-time Console Monitor

```bash
cd lumenis_reactor_core/swarm
python3 swarm_monitor.py
```

Output:
```
======================================================================
📡 SWARM EXECUTION MONITOR
======================================================================

🎯 METRICS:
  Total Tasks Processed: 142
  Queue Depth: 3
  Active Nodes: 5

🧠 WORKER NODES:
  • worker-01          | online   | processed:   28 | age: 0.8s
  • worker-02          | online   | processed:   31 | age: 1.2s
  • worker-03          | online   | processed:   29 | age: 0.5s
  • worker-04          | online   | processed:   27 | age: 1.8s
  • worker-05          | online   | processed:   27 | age: 0.3s

======================================================================
```

### Web HUD

Visit `http://localhost:8000/swarm-hud` for a real-time cyberpunk-styled visualization.

---

## Performance

Typical performance metrics (5 workers):

| Metric | Value |
|--------|-------|
| Task throughput | 3-5 tasks/sec |
| Worker response time | 200-1500ms |
| Heartbeat interval | 1 second |
| Queue latency | < 100ms |

With 10 workers:
- Throughput: 8-12 tasks/sec
- Parallel processing of independent tasks

---

## State Management

### State File
The swarm maintains state in `runtime/swarm_state.json`:

```json
{
  "active_nodes": {
    "worker-01": {
      "last_seen": 1730000000.0,
      "status": "online",
      "processed": 28
    }
  },
  "processed_tasks": 142,
  "queue_depth": 3,
  "last_update": 1730000000.0
}
```

### Task Queue
Tasks are stored as JSON files in `tasks/`:

```json
{
  "id": "a3b2c1d4",
  "type": "reasoning",
  "created": 1730000000.0,
  "priority": 3,
  "complexity": "medium",
  "data": {
    "query": "Analyze swarm efficiency"
  }
}
```

---

## Integration with Lumenis Reactor

The swarm integrates seamlessly with the Lumenis Reactor:

1. **Shared Memory**: Swarm tasks can access FluxCompass memory
2. **Council Integration**: High-complexity tasks can trigger ITT Council
3. **Event Streaming**: Swarm events broadcast via WebSocket
4. **Unified Status**: Swarm metrics included in `/api/status`

### Example Integration

```python
from lumenis_reactor_core import LumenisReactor, SwarmOrchestrator

# Initialize components
reactor = LumenisReactor()
swarm = SwarmOrchestrator(num_workers=5)

# Start both
await reactor.start()
swarm.start()

# Submit task to swarm
task_id = await swarm.submit_task("oracle", {
    "query": "What patterns exist in my conversation history?"
})

# Task will be processed by swarm
# Complex tasks can escalate to ITT Council
```

---

## Troubleshooting

### Workers Not Starting
- Check: `lumenis_reactor_core/swarm/runtime/swarm_state.json` exists
- Fix: `mkdir -p lumenis_reactor_core/swarm/runtime`

### Tasks Not Processing
- Check: Task files exist in `tasks/` directory
- Check: Workers show `status: "online"` in state file
- Fix: Restart workers with `./start_swarm.sh`

### High Queue Depth
- Cause: Workers slower than task generation
- Fix: Increase `num_workers` or decrease `pulse.interval`

### Stale Workers
- Symptom: Workers show `age > 10s` in monitor
- Cause: Worker process crashed
- Fix: Restart swarm

---

## Advanced Usage

### Custom Worker Logic

```python
from lumenis_reactor_core.swarm import WorkerNode

class CustomWorker(WorkerNode):
    def process_task(self, task_file):
        data = json.loads(task_file.read_text())

        # Custom processing logic
        if data['type'] == 'special':
            self.handle_special_task(data)
        else:
            super().process_task(task_file)

        return True
```

### Dynamic Worker Scaling

```python
swarm = SwarmOrchestrator(num_workers=5)
swarm.start()

# Add more workers at runtime
for i in range(3):
    worker = WorkerNode(node_id=f"worker-extra-{i}")
    thread = threading.Thread(target=worker.run, daemon=True)
    thread.start()
    swarm.workers.append(worker)
```

---

## Architecture Decisions

### Why Threads Instead of Async?
- Workers need true parallelism for CPU-bound tasks
- Thread-based workers can run on separate cores
- Easier integration with blocking operations
- Better isolation between workers

### Why JSON Files for Queue?
- Simple, debuggable, no external dependencies
- Filesystem provides atomic operations
- Easy to inspect and manipulate manually
- Works across process boundaries

### Why Separate State File?
- Centralized state for monitoring
- Atomic updates prevent race conditions
- Persistent across worker restarts
- Easy to backup and restore

---

## Future Enhancements

- [ ] Priority queue implementation
- [ ] Task dependencies and workflows
- [ ] Worker specialization (specific task types)
- [ ] Distributed swarm across multiple machines
- [ ] Task retry and failure handling
- [ ] Performance profiling and optimization
- [ ] Redis-based queue for high throughput
- [ ] Task scheduling and cron-like triggers

---

## Contributing

To add new task types:

1. Add to `TASK_TYPES` in `task_pulse.py`
2. Implement handler in `WorkerNode.process_task()`
3. Update documentation

To add new metrics:

1. Add field to state dict in `worker_node.py`
2. Update `SwarmMonitor.format_node_info()`
3. Expose via API in `lumenis-main-with-swarm.py`

---

## License

Part of the One2lvOS project.

---

**Built with:** Python 3.9+, Threading, JSON, FastAPI
**Powered by:** Lumenis Reactor Core
**Architecture:** Hunter A.

🧠🌊 **SWARM EXECUTION LAYER - ACTIVE** 🌊🧠
