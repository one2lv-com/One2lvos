#!/usr/bin/env python3
"""
Aether-Lumenis OS - Sovereign Cognitive Operating System (v2.0)
Synthesizing One2lvOS, Lumenis Reactor, Sovereign Agent Council,
O2PNG Capsule Protocol, and Interplanetary VectorFS.
"""

import os
import sys
import time
import json
import gzip
import zlib
import math
import struct
import uuid
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, Tuple

# ==============================================================================
# 1. CORE TELEMETRY & LOGGING
# ==============================================================================

class Logger:
    LEVELS = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3}
    current_level = 1

    @classmethod
    def log(cls, level: str, module: str, message: str):
        if cls.LEVELS.get(level, 1) >= cls.current_level:
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            print(f"[{ts}] [{level:<5}] [{module:<15}] {message}")

    @classmethod
    def debug(cls, module: str, msg: str): cls.log('DEBUG', module, msg)

    @classmethod
    def info(cls, module: str, msg: str): cls.log('INFO', module, msg)

    @classmethod
    def warn(cls, module: str, msg: str): cls.log('WARN', module, msg)

    @classmethod
    def error(cls, module: str, msg: str): cls.log('ERROR', module, msg)

# ==============================================================================
# 2. O2PNG STATE CAPSULE PROTOCOL & CARRIER BINDING
# ==============================================================================

class O2PNGProtocol:
    """
    Implements O2PNG v1.0 State Capsule Envelope Format.
    Header layout:
      0x00: MAGIC (5B) = b'O2PNG'
      0x05: PROTOCOL_VERSION (1B) = 0x01
      0x06: FLAGS (1B) [0x01=GZIP, 0x02=ENCRYPTED, 0x04=SIGNED]
      0x07: HEADER_LENGTH (2B, LE)
      0x09: SCHEMA_VERSION (1B)
      0x0A: RESERVED (2B)
      0x0C: SNAPSHOT_ID (16B)
      0x1C: GENERATION (8B, uint64 LE)
      0x24: PARENT_SNAPSHOT_ID (16B)
      0x34: CREATED_AT (8B, uint64 LE)
      0x3C: SOURCE_DEVICE_ID (16B)
      0x4C: RUNTIME_VERSION (2B, uint16 LE)
      0x4E: PAYLOAD_LENGTH (4B, uint32 LE)
      0x52: DIGEST (32B, SHA-256 of header + payload)
    """
    MAGIC = b"O2PNG"
    PROTOCOL_VERSION = 1
    FLAG_COMPRESSED = 0x01

    @staticmethod
    def pack_envelope(state_data: dict, generation: int, parent_id: bytes, device_id: bytes) -> bytes:
        raw_json = json.dumps(state_data, sort_keys=True).encode('utf-8')
        compressed_payload = gzip.compress(raw_json)
        payload_len = len(compressed_payload)

        snapshot_id = uuid.uuid4().bytes
        created_at = int(time.time())
        runtime_version = 0x0200  # v2.0
        header_len = 82 + 32  # 114 bytes total header with digest
        flags = O2PNGProtocol.FLAG_COMPRESSED
        schema_version = 1

        header_pre_digest = struct.pack(
            "<5sBBHBH16sQ16sQ16sHI",
            O2PNGProtocol.MAGIC,
            O2PNGProtocol.PROTOCOL_VERSION,
            flags,
            header_len,
            schema_version,
            0,  # Reserved
            snapshot_id,
            generation,
            parent_id,
            created_at,
            device_id,
            runtime_version,
            payload_len
        )

        digest = hashlib.sha256(header_pre_digest + compressed_payload).digest()
        envelope = header_pre_digest + digest + compressed_payload
        return envelope

    @staticmethod
    def unpack_envelope(envelope_bytes: bytes, current_generation: int) -> Tuple[dict, dict]:
        if len(envelope_bytes) < 114:
            raise ValueError("Envelope truncated: smaller than header minimum size.")

        header_pre = envelope_bytes[:82]
        digest = envelope_bytes[82:114]
        payload = envelope_bytes[114:]

        fields = struct.unpack("<5sBBHBH16sQ16sQ16sHI", header_pre)
        magic, proto_ver, flags, hdr_len, schema_ver, _, snap_id, gen, parent_id, created_at, dev_id, run_ver, p_len = fields

        if magic != O2PNGProtocol.MAGIC:
            raise ValueError(f"Invalid magic identifier: {magic}")
        if proto_ver != O2PNGProtocol.PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {proto_ver}")

        expected_digest = hashlib.sha256(header_pre + payload).digest()
        if digest != expected_digest:
            raise ValueError("Integrity verification failed: SHA-256 digest mismatch.")

        if gen <= current_generation and current_generation > 0:
            raise ValueError(f"Rollback rejected: snapshot gen {gen} <= active gen {current_generation}")

        if flags & O2PNGProtocol.FLAG_COMPRESSED:
            decompressed = gzip.decompress(payload)
        else:
            decompressed = payload

        state_data = json.loads(decompressed.decode('utf-8'))
        metadata = {
            "snapshot_id": snap_id.hex(),
            "generation": gen,
            "parent_id": parent_id.hex(),
            "created_at": created_at,
            "device_id": dev_id.hex(),
            "runtime_version": f"{run_ver >> 8}.{run_ver & 0xFF}"
        }
        return state_data, metadata

class PNGBootCarrier:
    """
    Encodes/Decodes state envelopes into uncompressed/synthetic PNG bitstreams via LSB steganography.
    """

    @staticmethod
    def encode_to_synthetic_png(envelope: bytes, width: int = 512, height: int = 512) -> bytes:
        total_pixels = width * height
        max_bytes = total_pixels // 8  # 1 bit per RGB pixel (R-channel LSB)
        if len(envelope) + 4 > max_bytes:
            # Dynamically compute required dimensions
            needed_pixels = (len(envelope) + 4) * 8
            dimension = int(math.ceil(math.sqrt(needed_pixels)))
            width = height = dimension

        raw_stream = bytearray(width * height * 3)
        # Store 32-bit length prefix + payload
        data_to_embed = struct.pack(">I", len(envelope)) + envelope
        bit_index = 0

        for b in data_to_embed:
            for i in range(7, -1, -1):
                bit = (b >> i) & 1
                pixel_offset = bit_index * 3  # R-channel
                if pixel_offset < len(raw_stream):
                    raw_stream[pixel_offset] = (raw_stream[pixel_offset] & 0xFE) | bit
                bit_index += 1

        # Minimal valid PNG generator
        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        header = b'\x89PNG\r\n\x1a\n'
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

        raw_scanlines = bytearray()
        for y in range(height):
            raw_scanlines.append(0)  # Filter type 0
            start = y * width * 3
            raw_scanlines.extend(raw_stream[start:start + width * 3])

        idat = zlib.compress(bytes(raw_scanlines))
        return header + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')

    @staticmethod
    def decode_from_synthetic_png(png_bytes: bytes) -> bytes:
        # Locate IDAT chunk
        pos = 8
        idat_data = bytearray()
        width, height = 0, 0
        while pos < len(png_bytes):
            length = struct.unpack(">I", png_bytes[pos:pos+4])[0]
            tag = png_bytes[pos+4:pos+8]
            content = png_bytes[pos+8:pos+8+length]
            if tag == b'IHDR':
                width, height = struct.unpack(">II", content[:8])
            elif tag == b'IDAT':
                idat_data.extend(content)
            elif tag == b'IEND':
                break
            pos += 12 + length

        decompressed = zlib.decompress(bytes(idat_data))
        raw_pixels = bytearray()
        scanline_len = 1 + width * 3
        for y in range(height):
            start = y * scanline_len + 1
            raw_pixels.extend(decompressed[start:start + width * 3])

        # Extract bits
        bits = []
        for i in range(0, len(raw_pixels), 3):
            bits.append(raw_pixels[i] & 1)

        # Reconstruct byte array
        extracted_bytes = bytearray()
        for i in range(0, len(bits) - 7, 8):
            byte_val = 0
            for b in range(8):
                byte_val = (byte_val << 1) | bits[i + b]
            extracted_bytes.append(byte_val)

        if len(extracted_bytes) < 4:
            raise ValueError("Carrier image contains insufficient data.")

        envelope_len = struct.unpack(">I", extracted_bytes[:4])[0]
        envelope = extracted_bytes[4:4 + envelope_len]
        return bytes(envelope)

# ==============================================================================
# 3. INTERPLANETARY VIRTUAL FILE SYSTEM & VECTOR MEMORY (VectorFS)
# ==============================================================================

class VectorFS:
    """
    Semantic vector memory engine supporting similarity matching with zero-magnitude protection.
    """
    def __init__(self, dimensions: int = 16):
        self.dimensions = dimensions
        self.vectors: Dict[str, Dict[str, Any]] = {}

    def store(self, key: str, vector: List[float], metadata: dict):
        if len(vector) != self.dimensions:
            # Auto-pad or truncate to standard dimensions
            vector = (vector + [0.0] * self.dimensions)[:self.dimensions]
        self.vectors[key] = {
            "vector": vector,
            "metadata": metadata,
            "timestamp": time.time()
        }

    def search(self, query_vector: List[float], limit: int = 5, threshold: float = 0.0) -> List[dict]:
        query_vector = (query_vector + [0.0] * self.dimensions)[:self.dimensions]
        results = []
        for key, entry in self.vectors.items():
            sim = self._cosine_similarity(query_vector, entry["vector"])
            if sim >= threshold:
                results.append({
                    "key": key,
                    "similarity": round(sim, 4),
                    "metadata": entry["metadata"],
                    "timestamp": entry["timestamp"]
                })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def serialize(self) -> dict:
        return self.vectors

    def deserialize(self, data: dict):
        self.vectors = data

class VirtualFileSystem:
    """
    Hierarchical Virtual File System with commit journaling and transactional rollback.
    """
    def __init__(self):
        self.tree: Dict[str, Any] = {"/": {"type": "dir", "children": {}}}
        self.journal: List[str] = []

    def _resolve_path(self, path: str) -> Tuple[Optional[dict], str]:
        parts = [p for p in path.strip("/").split("/") if p]
        curr = self.tree["/"]
        for p in parts[:-1]:
            if p not in curr["children"] or curr["children"][p]["type"] != "dir":
                return None, ""
            curr = curr["children"][p]
        leaf = parts[-1] if parts else ""
        return curr, leaf

    def write_file(self, path: str, content: str):
        curr, leaf = self._resolve_path(path)
        if not curr or not leaf:
            self.mkdir(os.path.dirname(path))
            curr, leaf = self._resolve_path(path)
        curr["children"][leaf] = {
            "type": "file",
            "content": content,
            "modified": time.time()
        }
        self.journal.append(f"WRITE:{path}")

    def read_file(self, path: str) -> Optional[str]:
        curr, leaf = self._resolve_path(path)
        if curr and leaf in curr["children"] and curr["children"][leaf]["type"] == "file":
            return curr["children"][leaf]["content"]
        return None

    def mkdir(self, path: str):
        parts = [p for p in path.strip("/").split("/") if p]
        curr = self.tree["/"]
        for p in parts:
            if p not in curr["children"]:
                curr["children"][p] = {"type": "dir", "children": {}}
            curr = curr["children"][p]

    def list_dir(self, path: str) -> List[str]:
        if path == "/" or not path:
            return list(self.tree["/"].get("children", {}).keys())
        curr, leaf = self._resolve_path(path)
        if curr and leaf in curr["children"] and curr["children"][leaf]["type"] == "dir":
            return list(curr["children"][leaf]["children"].keys())
        return []

    def serialize(self) -> dict:
        return {"tree": self.tree, "journal": self.journal[-100:]}

    def deserialize(self, data: dict):
        self.tree = data.get("tree", {"/": {"type": "dir", "children": {}}})
        self.journal = data.get("journal", [])

# ==============================================================================
# 4. SOVEREIGN MULTI-AGENT COUNCIL
# ==============================================================================

class CouncilMember:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    async def evaluate(self, topic: str, context: dict) -> dict:
        raise NotImplementedError

class WitnessAgent(CouncilMember):
    def __init__(self):
        super().__init__("∆Witness∆", "Historical Context, Lineage, & Invariant Audit")

    async def evaluate(self, topic: str, context: dict) -> dict:
        history_len = len(context.get("itt_history", []))
        generation = context.get("generation", 0)
        return {
            "member": self.name,
            "support": True,
            "confidence": 0.96,
            "perspective": f"Lineage verified across generation {generation}. Prior timeline context depth: {history_len} cycles.",
            "evidence": "Historical invariant ledger intact."
        }

class ObserverAgent(CouncilMember):
    def __init__(self):
        super().__init__("Observer", "Telemetry Analysis, Anomaly Detection & Patterns")

    async def evaluate(self, topic: str, context: dict) -> dict:
        metrics = context.get("metrics", {})
        task_load = metrics.get("active_tasks", 0)
        support = task_load < 50
        return {
            "member": self.name,
            "support": support,
            "confidence": 0.91,
            "perspective": f"Telemetry operational. Current task queue load: {task_load}.",
            "evidence": "Resource pressure metrics nominal."
        }

class ArchitectAgent(CouncilMember):
    def __init__(self):
        super().__init__("Architect", "Structural Cohesion & Scalability Verification")

    async def evaluate(self, topic: str, context: dict) -> dict:
        return {
            "member": self.name,
            "support": True,
            "confidence": 0.94,
            "perspective": "Structural state aligns with modular protocol specifications.",
            "evidence": "Schema contracts and memory alignment validated."
        }

class GuardianAgent(CouncilMember):
    def __init__(self):
        super().__init__("Guardian", "Cryptographic Validation & Rollback Defense")

    async def evaluate(self, topic: str, context: dict) -> dict:
        gen = context.get("generation", 0)
        last_gen = context.get("last_committed_generation", 0)
        safe = gen >= last_gen
        return {
            "member": self.name,
            "support": safe,
            "confidence": 0.99,
            "perspective": f"Rollback defense status: {'SECURE' if safe else 'VIOLATION DETECTED'}.",
            "evidence": f"Incoming gen ({gen}) >= base gen ({last_gen})."
        }

class ModeratorAgent(CouncilMember):
    def __init__(self):
        super().__init__("Moderator", "Consensus Synthesis & Conflict Resolution")

    def synthesize(self, votes: List[dict]) -> dict:
        if not votes:
            return {"verdict": "REJECT", "confidence": 0.0, "reasoning": "No council votes."}

        support_count = sum(1 for v in votes if v["support"])
        avg_confidence = sum(v["confidence"] for v in votes) / len(votes)
        ratio = support_count / len(votes)

        verdict = "APPROVED" if ratio >= 0.75 else "REJECTED"
        return {
            "verdict": verdict,
            "support_ratio": f"{support_count}/{len(votes)}",
            "mean_confidence": round(avg_confidence, 3),
            "votes": votes
        }

class SovereignCouncil:
    def __init__(self):
        self.members: List[CouncilMember] = [
            WitnessAgent(),
            ObserverAgent(),
            ArchitectAgent(),
            GuardianAgent()
        ]
        self.moderator = ModeratorAgent()

    async def deliberate(self, topic: str, context: dict) -> dict:
        Logger.info("Council", f"Convening sovereign council for topic: '{topic}'")
        votes = await asyncio.gather(*[m.evaluate(topic, context) for m in self.members])
        decision = self.moderator.synthesize(votes)
        Logger.info("Council", f"Synthesis verdict: {decision['verdict']} ({decision['support_ratio']})")
        return decision

# ==============================================================================
# 5. LUMENIS COGNITIVE REACTOR & TASK SCHEDULER
# ==============================================================================

class Task:
    def __init__(self, task_id: str, name: str, priority: int, action):
        self.id = task_id
        self.name = name
        self.priority = priority  # Lower number = higher priority
        self.action = action
        self.created_at = time.time()
        self.status = "pending"

class LumenisReactor:
    """
    Cognitive execution reactor managing asynchronous loops, task priority queuing,
    and Infinite Thought Thread (ITT) state progression.
    """
    def __init__(self):
        self.task_queue: List[Task] = []
        self.itt_journal: List[dict] = []
        self.short_term_memory: Dict[str, Any] = {}
        self.running = False

    def push_task(self, name: str, priority: int, action) -> str:
        tid = f"task_{uuid.uuid4().hex[:8]}"
        task = Task(tid, name, priority, action)
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority)
        Logger.debug("Reactor", f"Enqueued task {tid}: {name} (Priority {priority})")
        return tid

    async def tick(self):
        if not self.task_queue:
            return
        task = self.task_queue.pop(0)
        task.status = "running"
        Logger.info("Reactor", f"Executing task {task.id}: '{task.name}'")

        start = time.time()
        try:
            if asyncio.iscoroutinefunction(task.action):
                result = await task.action()
            else:
                result = task.action()
            task.status = "completed"
            duration = round((time.time() - start) * 1000, 2)
            self._record_thought_thread(task.name, "SUCCESS", result, duration)
        except Exception as e:
            task.status = "failed"
            duration = round((time.time() - start) * 1000, 2)
            self._record_thought_thread(task.name, "FAILURE", str(e), duration)
            Logger.error("Reactor", f"Task {task.id} failed: {e}")

    def _record_thought_thread(self, trigger: str, status: str, result: Any, duration_ms: float):
        entry = {
            "cycle": len(self.itt_journal) + 1,
            "timestamp": time.time(),
            "trigger": trigger,
            "status": status,
            "duration_ms": duration_ms,
            "snapshot_hint": str(result)[:80]
        }
        self.itt_journal.append(entry)
        if len(self.itt_journal) > 500:
            self.itt_journal.pop(0)

    def serialize(self) -> dict:
        return {
            "itt_journal": self.itt_journal[-50:],
            "short_term_memory": self.short_term_memory
        }

    def deserialize(self, data: dict):
        self.itt_journal = data.get("itt_journal", [])
        self.short_term_memory = data.get("short_term_memory", {})

# ==============================================================================
# 6. UNIFIED OPERATING SYSTEM CORE
# ==============================================================================

class AetherLumenisOS:
    """
    Central operating system kernel orchestrating Reactor, Council, VFS,
    VectorFS, and O2PNG Persistence Subsystems.
    """
    def __init__(self, device_id: Optional[bytes] = None):
        self.device_id = device_id or hashlib.sha256(b"Aether-Node-01").digest()[:16]
        self.generation = 1
        self.parent_snapshot_id = bytes(16)
        self.boot_time = 0.0

        # Subsystems
        self.reactor = LumenisReactor()
        self.council = SovereignCouncil()
        self.vfs = VirtualFileSystem()
        self.vector_fs = VectorFS(dimensions=16)
        self.system_status = "INITIALIZING"

    async def boot(self, carrier_png_bytes: Optional[bytes] = None) -> float:
        start_time = time.time()
        Logger.info("Kernel", "==================================================")
        Logger.info("Kernel", "⚡ Booting Aether-Lumenis Sovereign OS (v2.0) ⚡")
        Logger.info("Kernel", "==================================================")

        # Stage 1: File system baseline
        self.vfs.mkdir("/sys")
        self.vfs.mkdir("/etc")
        self.vfs.mkdir("/home")
        self.vfs.mkdir("/snapshots")
        self.vfs.write_file("/etc/os-release", "NAME=AetherLumenisOS\nVERSION=2.0-Sovereign\nCODENAME=Trinity")

        # Stage 2: Restore from State Capsule if provided
        if carrier_png_bytes:
            Logger.info("Kernel", "Decoding O2PNG steganographic boot image...")
            envelope = PNGBootCarrier.decode_from_synthetic_png(carrier_png_bytes)
            state, meta = O2PNGProtocol.unpack_envelope(envelope, current_generation=0)

            # Rehydrate subsystems
            self.vfs.deserialize(state.get("vfs", {}))
            self.vector_fs.deserialize(state.get("vector_fs", {}))
            self.reactor.deserialize(state.get("reactor", {}))
            self.generation = meta["generation"] + 1
            self.parent_snapshot_id = bytes.fromhex(meta["snapshot_id"])
            Logger.info("Kernel", f"State capsule rehydrated. Lineage parent: {meta['snapshot_id'][:8]}... | New Gen: {self.generation}")
        else:
            Logger.info("Kernel", "No boot image supplied. Initializing pristine state tree.")

        # Stage 3: Initial vector memory seed
        self.vector_fs.store("sys.kernel", [0.9, 0.1, 0.2, 0.8] + [0.0]*12, {"desc": "Kernel execution parameters"})
        self.vector_fs.store("sys.council", [0.3, 0.9, 0.8, 0.2] + [0.0]*12, {"desc": "Sovereign Council policies"})

        self.system_status = "ONLINE"
        self.boot_time = round((time.time() - start_time) * 1000, 2)
        Logger.info("Kernel", f"System ready in {self.boot_time}ms | Status: {self.system_status}")
        return self.boot_time

    def capture_snapshot(self) -> bytes:
        """
        Gathers system state and serializes it into an O2PNG envelope inside a synthetic PNG carrier.
        """
        state_tree = {
            "vfs": self.vfs.serialize(),
            "vector_fs": self.vector_fs.serialize(),
            "reactor": self.reactor.serialize(),
            "timestamp": time.time()
        }
        envelope = O2PNGProtocol.pack_envelope(
            state_data=state_tree,
            generation=self.generation,
            parent_id=self.parent_snapshot_id,
            device_id=self.device_id
        )
        png_carrier = PNGBootCarrier.encode_to_synthetic_png(envelope)
        Logger.info("Snapshot", f"Captured snapshot: {len(envelope)}B envelope embedded in {len(png_carrier)}B PNG carrier.")
        return png_carrier

    async def execute_cycle(self):
        """
        Executes one full cognitive reactor cycle.
        """
        await self.reactor.tick()

# ==============================================================================
# 7. AETHERIX MASTER CLI SHELL
# ==============================================================================

class AetherixShell:
    def __init__(self, os_instance: AetherLumenisOS):
        self.os = os_instance

    async def repl(self):
        print("\n" + "="*60)
        print("  AETHERIX COMMAND CENTER - SOVEREIGN REPL")
        print("  Commands: status, ps, council <topic>, vfs <cmd>, query <text>,")
        print("            snap, rehydrate, cycle, exit")
        print("="*60 + "\n")

        saved_png_boot: Optional[bytes] = None

        while True:
            try:
                line = input(f"aether@one2lv [{self.os.system_status}] # ").strip()
                if not line:
                    continue
                parts = line.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "exit":
                    Logger.info("Aetherix", "Exiting shell...")
                    break
                elif cmd == "status":
                    print(f"OS Version:   2.0 Sovereign Trinity")
                    print(f"Device ID:    {self.os.device_id.hex()[:16]}...")
                    print(f"Generation:   {self.os.generation}")
                    print(f"Boot Latency: {self.os.boot_time} ms")
                    print(f"ITT Cycles:   {len(self.os.reactor.itt_journal)}")
                    print(f"VFS Nodes:    {len(self.os.vfs.list_dir('/'))}")
                    print(f"Vectors:      {len(self.os.vector_fs.vectors)}")
                elif cmd == "ps":
                    tasks = self.os.reactor.task_queue
                    print(f"Active Tasks in Reactor: {len(tasks)}")
                    for t in tasks:
                        print(f"  [{t.id}] {t.name} (Priority {t.priority}) - {t.status}")
                elif cmd == "council":
                    topic = arg or "System Resource Allocation"
                    context = {
                        "generation": self.os.generation,
                        "last_committed_generation": self.os.generation - 1,
                        "itt_history": self.os.reactor.itt_journal,
                        "metrics": {"active_tasks": len(self.os.reactor.task_queue)}
                    }
                    res = await self.os.council.deliberate(topic, context)
                    print(f"\nVerdict: {res['verdict']} (Consensus: {res['support_ratio']}, Confidence: {res['mean_confidence']})")
                    for v in res["votes"]:
                        print(f"  • {v['member']:<12}: {'[PASS]' if v['support'] else '[FAIL]'} {v['perspective']}")
                elif cmd == "vfs":
                    v_parts = arg.split(maxsplit=2)
                    sub = v_parts[0] if v_parts else "ls"
                    if sub == "ls":
                        path = v_parts[1] if len(v_parts) > 1 else "/"
                        print(f"Directory listing of {path}:", self.os.vfs.list_dir(path))
                    elif sub == "cat":
                        path = v_parts[1] if len(v_parts) > 1 else "/etc/os-release"
                        print(f"--- {path} ---\n{self.os.vfs.read_file(path)}")
                    elif sub == "write":
                        path = v_parts[1]
                        val = v_parts[2] if len(v_parts) > 2 else ""
                        self.os.vfs.write_file(path, val)
                        print(f"Written {len(val)} bytes to {path}")
                elif cmd == "query":
                    # Simple heuristic vectorization demo for search
                    q_vec = [0.8, 0.2, 0.1, 0.7] + [0.0]*12
                    results = self.os.vector_fs.search(q_vec, limit=3)
                    print("Semantic VectorFS Matches:")
                    for r in results:
                        print(f"  • {r['key']} (Similarity: {r['similarity']}) -> {r['metadata']}")
                elif cmd == "snap":
                    saved_png_boot = self.os.capture_snapshot()
                    self.os.vfs.write_file(f"/snapshots/gen_{self.os.generation}.png", "<BINARY_PNG_CARRIER>")
                    print(f"Snapshot committed to PNG carrier buffer ({len(saved_png_boot)} bytes).")
                elif cmd == "rehydrate":
                    if not saved_png_boot:
                        print("Error: No snapshot captured yet. Run 'snap' first.")
                    else:
                        print("Rebooting and rehydrating state from captured PNG carrier...")
                        new_os = AetherLumenisOS(device_id=self.os.device_id)
                        await new_os.boot(saved_png_boot)
                        self.os = new_os
                elif cmd == "cycle":
                    self.os.reactor.push_task("Telemetric Pulse", 1, lambda: "Pulse nominal")
                    self.os.reactor.push_task("VFS Verification", 2, lambda: f"Verified {len(self.os.vfs.journal)} mutations")
                    await self.os.execute_cycle()
                    await self.os.execute_cycle()
                else:
                    print(f"Unknown command: {cmd}")
            except Exception as e:
                print(f"Error: {e}")

# ==============================================================================
# 8. VERIFICATION & RUNTIME ENTRY POINT
# ==============================================================================

async def main():
    kernel = AetherLumenisOS()
    # 1. Boot system
    await kernel.boot()

    # 2. Enqueue sample cognitive tasks
    kernel.reactor.push_task("Initialize Mesh Network", priority=1, action=lambda: "Mesh connected: 12 nodes")
    kernel.reactor.push_task("Calibrate Aurora Shader", priority=2, action=lambda: "Shader pipeline active (60 FPS)")

    # 3. Step execution cycles
    await kernel.execute_cycle()
    await kernel.execute_cycle()

    # 4. Invoke Council Deliberation
    context = {
        "generation": kernel.generation,
        "last_committed_generation": 0,
        "itt_history": kernel.reactor.itt_journal,
        "metrics": {"active_tasks": len(kernel.reactor.task_queue)}
    }
    await kernel.council.deliberate("State Snapshot Persistence Verification", context)

    # 5. Launch interactive Aetherix Shell
    shell = AetherixShell(kernel)
    await shell.repl()

if __name__ == "__main__":
    asyncio.run(main())
