# Aether-Lumenis OS Integration Examples

## Complete Integration Guide for One2lvos Ecosystem

---

## Option 1: Standalone Aether-Lumenis OS

Run the complete operating system independently:

```bash
cd /home/vercel-sandbox/One2lvos
./start-aether-lumenis.sh

# Or directly:
python3 aether_lumenis_os.py
```

**Use Cases**:
- State persistence with O2PNG snapshots
- Multi-agent sovereign decision making
- Semantic vector memory search
- Virtual filesystem operations

---

## Option 2: Import Sovereign Council into Existing Lumenis Reactor

Enhance your existing Lumenis Reactor with the Sovereign Council:

```python
# In lumenis-main.py
from aether_lumenis_os import SovereignCouncil

# Initialize council
council = SovereignCouncil()

# Use in WebSocket handler
async def handle_chat(ws: WebSocket, msg: dict):
    user_text = msg.get("message", "").strip()
    session_id = msg.get("session_id")

    # Before processing, check with council
    context = {
        "generation": generation_counter,
        "last_committed_generation": last_gen,
        "itt_history": reactor.itt_journal,
        "metrics": {
            "active_tasks": len(node_pool.tasks),
            "memory_usage": get_memory_usage()
        }
    }

    decision = await council.deliberate("Process User Request", context)

    if decision["verdict"] == "APPROVED":
        # Process message through ITT Council
        response = await council_process(user_text, session_id)
        await ws.send_json({"type": "response", "data": response})
    else:
        # Reject or defer
        await ws.send_json({
            "type": "warning",
            "message": "System load high, request deferred",
            "council_verdict": decision
        })
```

---

## Option 3: Add O2PNG State Persistence to Existing System

Enable state snapshots with rollback protection:

```python
# In lumenis-main.py or your main script
from aether_lumenis_os import O2PNGProtocol, PNGBootCarrier
import hashlib
import time

# Device ID (persistent identifier for your instance)
DEVICE_ID = hashlib.sha256(b"One2lvos-Production-001").digest()[:16]

# Generation tracking
current_generation = 1
parent_snapshot_id = bytes(16)

def capture_system_snapshot():
    """Capture complete system state"""
    global current_generation, parent_snapshot_id

    state_tree = {
        "vfs": vfs.serialize() if hasattr(vfs, 'serialize') else {},
        "compass": compass.get_stats(),
        "reactor": {
            "itt_journal": reactor.itt_journal[-50:],
            "uptime": time.time() - reactor.start_time
        },
        "sessions": compass.list_sessions(limit=100),
        "facts": compass.get_all_facts()
    }

    # Pack into O2PNG envelope
    envelope = O2PNGProtocol.pack_envelope(
        state_data=state_tree,
        generation=current_generation,
        parent_id=parent_snapshot_id,
        device_id=DEVICE_ID
    )

    # Encode into PNG carrier
    png_carrier = PNGBootCarrier.encode_to_synthetic_png(envelope)

    # Save to disk
    snapshot_path = f"/snapshots/state_gen_{current_generation}.png"
    with open(snapshot_path, 'wb') as f:
        f.write(png_carrier)

    print(f"✓ Snapshot saved: {len(png_carrier)} bytes -> {snapshot_path}")

    # Update for next snapshot
    current_generation += 1

    return png_carrier

# Add FastAPI endpoint
@app.post("/api/snapshot")
async def create_snapshot():
    png_carrier = capture_system_snapshot()
    return {
        "success": True,
        "generation": current_generation - 1,
        "size_bytes": len(png_carrier)
    }

# Restore from snapshot on boot
def restore_from_snapshot(png_path: str):
    """Restore system state from O2PNG snapshot"""
    with open(png_path, 'rb') as f:
        png_carrier = f.read()

    # Decode envelope
    envelope = PNGBootCarrier.decode_from_synthetic_png(png_carrier)

    # Unpack and verify
    state_data, metadata = O2PNGProtocol.unpack_envelope(
        envelope,
        current_generation=current_generation
    )

    # Restore subsystems
    if hasattr(vfs, 'deserialize'):
        vfs.deserialize(state_data.get("vfs", {}))

    print(f"✓ State restored from generation {metadata['generation']}")
    return metadata
```

---

## Option 4: Add VectorFS Semantic Memory

Enhance memory with semantic search:

```python
# In lumenis-main.py
from aether_lumenis_os import VectorFS

# Initialize
vector_fs = VectorFS(dimensions=16)

# Store embeddings (simplified example - use real embeddings from NVIDIA)
async def store_conversation_embedding(session_id: str, message: str, response: str):
    """Store conversation in vector memory"""

    # Generate simple hash-based vector (replace with real embeddings)
    import hashlib
    msg_hash = hashlib.sha256(message.encode()).digest()
    vec = [float(b) / 255.0 for b in msg_hash[:16]]

    metadata = {
        "session_id": session_id,
        "message": message[:100],
        "response": response[:100],
        "timestamp": time.time()
    }

    vector_fs.store(f"conv_{session_id}_{int(time.time())}", vec, metadata)

# Search similar conversations
async def find_similar_conversations(query: str, limit: int = 5):
    """Find semantically similar past conversations"""

    # Generate query vector
    import hashlib
    query_hash = hashlib.sha256(query.encode()).digest()
    query_vec = [float(b) / 255.0 for b in query_hash[:16]]

    # Search
    results = vector_fs.search(query_vec, limit=limit, threshold=0.3)

    return [
        {
            "similarity": r["similarity"],
            "message": r["metadata"]["message"],
            "response": r["metadata"]["response"]
        }
        for r in results
    ]

# Add to chat handler
async def handle_chat_with_memory(ws: WebSocket, msg: dict):
    user_message = msg["message"]
    session_id = msg["session_id"]

    # Find similar past conversations for context
    similar = await find_similar_conversations(user_message, limit=3)

    if similar:
        await ws.send_json({
            "type": "memory_recall",
            "similar_conversations": similar
        })

    # Process message...
    response = await process_message(user_message, session_id)

    # Store in vector memory
    await store_conversation_embedding(session_id, user_message, response)

    return response
```

---

## Option 5: Full Integration Example

Complete integration of all Aether-Lumenis components:

```python
#!/usr/bin/env python3
"""
Enhanced One2lvos with Aether-Lumenis Integration
Combines existing Lumenis Reactor with Aether-Lumenis OS components
"""

import asyncio
from fastapi import FastAPI, WebSocket
from aether_lumenis_os import (
    SovereignCouncil,
    O2PNGProtocol,
    PNGBootCarrier,
    VectorFS,
    VirtualFileSystem
)

# Import existing components
from lumenis_reactor_core import (
    LumenisReactor,
    FluxCompass,
    ITTCouncil,
    VanguardNodePool
)

class EnhancedOne2lvOS:
    def __init__(self):
        # Existing components
        self.reactor = LumenisReactor()
        self.compass = FluxCompass()
        self.itt_council = ITTCouncil(self.reactor, self.compass)
        self.node_pool = VanguardNodePool()

        # Aether-Lumenis enhancements
        self.sovereign_council = SovereignCouncil()
        self.vector_fs = VectorFS(dimensions=16)
        self.vfs = VirtualFileSystem()

        # State management
        self.generation = 1
        self.device_id = hashlib.sha256(b"One2lvos-Enhanced").digest()[:16]

    async def boot(self, restore_from: Optional[bytes] = None):
        """Boot system with optional state restoration"""
        await self.reactor.start()

        if restore_from:
            # Restore from O2PNG snapshot
            envelope = PNGBootCarrier.decode_from_synthetic_png(restore_from)
            state_data, meta = O2PNGProtocol.unpack_envelope(envelope, self.generation)

            self.vfs.deserialize(state_data.get("vfs", {}))
            self.vector_fs.deserialize(state_data.get("vector_fs", {}))
            self.generation = meta["generation"] + 1

        print(f"✓ Enhanced One2lvOS booted (Generation {self.generation})")

    async def process_with_governance(self, message: str, session_id: str):
        """Process message with sovereign council governance"""

        # Step 1: Council deliberation
        context = {
            "generation": self.generation,
            "last_committed_generation": self.generation - 1,
            "itt_history": self.reactor.get_status()["tokens_streamed"],
            "metrics": {
                "active_tasks": len(self.node_pool.tasks),
                "session_active": True
            }
        }

        decision = await self.sovereign_council.deliberate(
            f"Process: {message[:50]}",
            context
        )

        if decision["verdict"] != "APPROVED":
            return {
                "error": "Request rejected by sovereign council",
                "reason": decision
            }

        # Step 2: Process through existing ITT Council
        response = await self.itt_council.process(
            user_message=message,
            session_id=session_id
        )

        # Step 3: Store in vector memory
        # (simplified - use real embeddings)
        vec = [hash(message) % 100 / 100.0] + [0.0] * 15
        self.vector_fs.store(
            f"msg_{session_id}_{int(time.time())}",
            vec,
            {"message": message, "response": response.final_response}
        )

        return {
            "response": response.final_response,
            "council_verdict": decision,
            "generation": self.generation
        }

    def capture_snapshot(self) -> bytes:
        """Capture complete system state"""
        state = {
            "vfs": self.vfs.serialize(),
            "vector_fs": self.vector_fs.serialize(),
            "compass_stats": self.compass.get_stats(),
            "reactor_status": self.reactor.get_status()
        }

        envelope = O2PNGProtocol.pack_envelope(
            state,
            self.generation,
            bytes(16),
            self.device_id
        )

        png = PNGBootCarrier.encode_to_synthetic_png(envelope)
        self.generation += 1

        return png

# Usage
app = FastAPI()
os = EnhancedOne2lvOS()

@app.on_event("startup")
async def startup():
    await os.boot()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    async for data in ws.iter_json():
        if data["action"] == "chat":
            result = await os.process_with_governance(
                data["message"],
                data["session_id"]
            )
            await ws.send_json(result)

@app.post("/api/snapshot")
async def snapshot():
    png = os.capture_snapshot()
    # Save or return
    return {"success": True, "size": len(png)}
```

---

## Quick Start Commands

```bash
# Test Aether-Lumenis OS
cd /home/vercel-sandbox/One2lvos
python3 test-aether-lumenis.py

# Run standalone OS
python3 aether_lumenis_os.py

# Launch with convenience script
./start-aether-lumenis.sh

# Run automated tests
python3 test-aether-lumenis.py
```

---

## Integration Checklist

### For Existing Lumenis Reactor:
- [ ] Import `SovereignCouncil` for governance
- [ ] Add `O2PNGProtocol` for state snapshots
- [ ] Integrate `VectorFS` for semantic memory
- [ ] Create snapshot endpoints
- [ ] Add council deliberation before critical operations

### For New Projects:
- [ ] Use `AetherLumenisOS` as base kernel
- [ ] Extend council with custom agents
- [ ] Configure O2PNG generation tracking
- [ ] Set up periodic snapshots
- [ ] Implement VectorFS search

---

## Summary

| Component | Standalone | Integrated | Benefit |
|-----------|------------|------------|---------|
| Sovereign Council | ✅ | ✅ | Multi-agent governance |
| O2PNG Protocol | ✅ | ✅ | State persistence + rollback protection |
| VectorFS | ✅ | ✅ | Semantic memory search |
| VirtualFS | ✅ | ⚠️ Optional | Hierarchical file operations |
| Aetherix Shell | ✅ | ❌ | Interactive CLI (standalone only) |

---

🌷 **Choose your integration path and enhance One2lvos with Aether-Lumenis components!**
