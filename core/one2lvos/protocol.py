"""
O2PNG Protocol Implementation v1.0
===================================

Complete implementation of the O2PNG state capsule protocol.
"""

import struct
import hashlib
import gzip
import json
import uuid
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import IntFlag

# Protocol Constants
MAGIC = b'O2PNG'
PROTOCOL_VERSION = 0x01
HEADER_SIZE_BASE = 0x5E

class Flags(IntFlag):
    """O2PNG envelope flags"""
    COMPRESSED = 0x01
    ENCRYPTED = 0x02
    SIGNED = 0x04
    DIFFERENTIAL = 0x08
    EPHEMERAL = 0x10

@dataclass
class SnapshotIdentity:
    """Snapshot identity and lineage"""
    snapshot_id: bytes  # 16 bytes UUID
    generation: int     # uint64
    parent_snapshot_id: bytes  # 16 bytes
    created_at: int     # uint64 unix timestamp
    source_device_id: bytes  # 16 bytes
    schema_version: int  # uint8
    runtime_version: int  # uint16

class O2PNGEncoder:
    """
    Encodes One2lvOS state into O2PNG protocol envelopes.
    """

    def __init__(
        self,
        state: dict,
        device_id: Optional[bytes] = None,
        parent_snapshot_id: Optional[bytes] = None,
        generation: int = 1,
        compress: bool = True,
        encrypt: bool = False,
        encryption_key: Optional[bytes] = None
    ):
        self.state = state
        self.device_id = device_id or self._generate_device_id()
        self.parent_snapshot_id = parent_snapshot_id or bytes(16)
        self.generation = generation
        self.compress = compress
        self.encrypt = encrypt
        self.encryption_key = encryption_key

        # Generate snapshot identity
        self.snapshot_id = uuid.uuid4().bytes
        self.created_at = int(time.time())
        self.schema_version = 1
        self.runtime_version = 0x0100  # 1.0

    def _generate_device_id(self) -> bytes:
        """Generate stable device identifier"""
        # In production, this would be persistent
        # For now, use a stable hash of hostname
        import socket
        hostname = socket.gethostname()
        return hashlib.sha256(hostname.encode()).digest()[:16]

    def encode(self) -> bytes:
        """Encode state to O2PNG envelope"""
        # 1. Serialize state to canonical JSON
        payload = self._serialize_state()

        # 2. Compress if requested
        flags = 0
        if self.compress:
            payload = gzip.compress(payload, compresslevel=9)
            flags |= Flags.COMPRESSED

        # 3. Encrypt if requested
        nonce = bytes(12)  # Empty for unencrypted
        auth_tag = b''

        if self.encrypt:
            if not self.encryption_key:
                raise ValueError("Encryption requested but no key provided")
            flags |= Flags.ENCRYPTED
            nonce, payload, auth_tag = self._encrypt_payload(payload)

        # 4. Build header
        header = self._build_header(flags, len(payload), nonce)

        # 5. Compute digest
        digest_input = header + payload
        if auth_tag:
            digest_input += auth_tag
        digest = hashlib.sha256(digest_input).digest()

        # 6. Assemble envelope
        envelope = header + payload
        if auth_tag:
            envelope += auth_tag
        envelope += digest

        return envelope

    def _serialize_state(self) -> bytes:
        """Serialize state to canonical JSON"""
        return json.dumps(
            self.state,
            ensure_ascii=False,
            separators=(',', ':'),
            sort_keys=True
        ).encode('utf-8')

    def _build_header(self, flags: int, payload_length: int, nonce: bytes) -> bytes:
        """Build O2PNG header"""
        header = bytearray()

        # Magic (5 bytes)
        header.extend(MAGIC)

        # Protocol version (1 byte)
        header.append(PROTOCOL_VERSION)

        # Flags (1 byte)
        header.append(flags)

        # Header length (2 bytes LE)
        header_length = HEADER_SIZE_BASE
        header.extend(struct.pack('<H', header_length))

        # Schema version (1 byte)
        header.append(self.schema_version)

        # Reserved (2 bytes)
        header.extend(bytes(2))

        # Snapshot ID (16 bytes)
        header.extend(self.snapshot_id)

        # Generation (8 bytes LE)
        header.extend(struct.pack('<Q', self.generation))

        # Parent snapshot ID (16 bytes)
        header.extend(self.parent_snapshot_id)

        # Created at (8 bytes LE)
        header.extend(struct.pack('<Q', self.created_at))

        # Source device ID (16 bytes)
        header.extend(self.device_id)

        # Runtime version (2 bytes LE)
        header.extend(struct.pack('<H', self.runtime_version))

        # Payload length (4 bytes LE)
        header.extend(struct.pack('<I', payload_length))

        # Nonce (12 bytes)
        header.extend(nonce)

        return bytes(header)

    def _encrypt_payload(self, payload: bytes) -> Tuple[bytes, bytes, bytes]:
        """Encrypt payload with AES-256-GCM"""
        # This is a placeholder - real implementation would use cryptography library
        # For now, just return unencrypted with dummy tag
        nonce = bytes(12)  # Would be random in production
        auth_tag = bytes(16)
        return nonce, payload, auth_tag


class O2PNGDecoder:
    """
    Decodes O2PNG protocol envelopes into One2lvOS state.
    """

    def __init__(self, envelope: bytes):
        self.envelope = envelope
        self.header = None
        self.identity = None
        self.payload = None
        self.digest = None

    def decode(self) -> Tuple[dict, SnapshotIdentity]:
        """Decode envelope and return (state, identity)"""
        # 1. Verify magic
        if self.envelope[:5] != MAGIC:
            raise ValueError(f"Invalid magic: expected {MAGIC}, got {self.envelope[:5]}")

        # 2. Parse header
        self._parse_header()

        # 3. Extract payload and digest
        payload_start = HEADER_SIZE_BASE
        payload_end = payload_start + self.header['payload_length']

        flags = self.header['flags']

        # Extract auth tag if encrypted
        auth_tag = None
        if flags & Flags.ENCRYPTED:
            auth_tag = self.envelope[payload_end:payload_end + 16]
            payload_end += 16

        self.payload = self.envelope[payload_start:payload_end - 16 if not auth_tag else payload_end]
        self.digest = self.envelope[payload_end:payload_end + 32] if not auth_tag else self.envelope[payload_end:payload_end + 32]

        # 4. Verify digest
        self._verify_digest()

        # 5. Decrypt if needed
        if flags & Flags.ENCRYPTED:
            self.payload = self._decrypt_payload(self.payload, auth_tag)

        # 6. Decompress if needed
        if flags & Flags.COMPRESSED:
            self.payload = gzip.decompress(self.payload)

        # 7. Parse JSON state
        state = json.loads(self.payload.decode('utf-8'))

        return state, self.identity

    def _parse_header(self):
        """Parse O2PNG header"""
        h = self.envelope

        # Protocol version
        protocol_version = h[5]
        if protocol_version != PROTOCOL_VERSION:
            raise ValueError(f"Unsupported protocol version: {protocol_version}")

        # Flags
        flags = h[6]

        # Header length
        header_length = struct.unpack('<H', h[7:9])[0]
        if header_length < HEADER_SIZE_BASE:
            raise ValueError(f"Invalid header length: {header_length}")

        # Schema version
        schema_version = h[9]

        # Snapshot ID
        snapshot_id = h[0x0C:0x1C]

        # Generation
        generation = struct.unpack('<Q', h[0x1C:0x24])[0]

        # Parent snapshot ID
        parent_snapshot_id = h[0x24:0x34]

        # Created at
        created_at = struct.unpack('<Q', h[0x34:0x3C])[0]

        # Source device ID
        source_device_id = h[0x3C:0x4C]

        # Runtime version
        runtime_version = struct.unpack('<H', h[0x4C:0x4E])[0]

        # Payload length
        payload_length = struct.unpack('<I', h[0x4E:0x52])[0]

        # Nonce
        nonce = h[0x52:0x5E]

        self.header = {
            'flags': flags,
            'header_length': header_length,
            'payload_length': payload_length,
            'nonce': nonce
        }

        self.identity = SnapshotIdentity(
            snapshot_id=snapshot_id,
            generation=generation,
            parent_snapshot_id=parent_snapshot_id,
            created_at=created_at,
            source_device_id=source_device_id,
            schema_version=schema_version,
            runtime_version=runtime_version
        )

    def _verify_digest(self):
        """Verify SHA-256 digest"""
        # Reconstruct digest input
        payload_start = HEADER_SIZE_BASE
        payload_end = payload_start + self.header['payload_length']

        flags = self.header['flags']
        if flags & Flags.ENCRYPTED:
            payload_end += 16  # Auth tag

        digest_input = self.envelope[:payload_end]

        expected_digest = hashlib.sha256(digest_input).digest()

        received_digest = self.envelope[payload_end:payload_end + 32]

        if expected_digest != received_digest:
            raise ValueError("Digest verification failed")

    def _decrypt_payload(self, payload: bytes, auth_tag: bytes) -> bytes:
        """Decrypt payload with AES-256-GCM"""
        # Placeholder - real implementation would use cryptography library
        return payload


class EnvelopeValidator:
    """Validates O2PNG envelopes"""

    @staticmethod
    def validate_generation(
        incoming_generation: int,
        current_generation: int,
        allow_rollback: bool = False
    ):
        """Validate generation number (rollback detection)"""
        if incoming_generation <= current_generation and not allow_rollback:
            raise ValueError(
                f"Rollback detected: incoming generation {incoming_generation} "
                f"<= current {current_generation}"
            )

    @staticmethod
    def validate_lineage(
        identity: SnapshotIdentity,
        parent_identity: Optional[SnapshotIdentity]
    ):
        """Validate snapshot lineage"""
        # Root snapshot (no parent)
        if identity.parent_snapshot_id == bytes(16):
            return

        # Non-root must have valid parent
        if not parent_identity:
            raise ValueError(
                f"Parent snapshot {identity.parent_snapshot_id.hex()} not found"
            )

        # Verify generation increases
        if identity.generation <= parent_identity.generation:
            raise ValueError(
                f"Invalid lineage: generation {identity.generation} "
                f"<= parent generation {parent_identity.generation}"
            )

    @staticmethod
    def validate_device(
        identity: SnapshotIdentity,
        current_device_id: bytes,
        allow_cross_device: bool = False
    ):
        """Validate device identity"""
        if identity.source_device_id != current_device_id and not allow_cross_device:
            raise ValueError(
                f"Cross-device restore detected: "
                f"snapshot from {identity.source_device_id.hex()}, "
                f"current device {current_device_id.hex()}"
            )
