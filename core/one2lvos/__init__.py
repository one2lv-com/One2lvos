"""
One2lvOS - Lumenis Operating System
====================================

A portable state-capsule operating system built on the O2PNG protocol.

Core Components:
- Lumenis Reactor: Active state management
- Recovery Manager: Boot and restoration
- O2PNG Protocol: State capsule format
- Snapshot Manager: Persistence layer
"""

__version__ = "1.0.0"
__protocol_version__ = "O2PNG-1.0"

from .reactor import LumenisReactor
from .recovery import RecoveryManager
from .snapshot import SnapshotManager
from .protocol import O2PNGEncoder, O2PNGDecoder

__all__ = [
    'LumenisReactor',
    'RecoveryManager',
    'SnapshotManager',
    'O2PNGEncoder',
    'O2PNGDecoder',
]
