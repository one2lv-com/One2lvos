"""
Lumenis Reactor Core
====================
Sovereign agentic intelligence powered by NVIDIA.

Layers:
  L0: Reactor Core - Thermal baseline 0.18°C, 73ms heartbeat
  L1: Memory - FluxCompass (SQLite vector memory)
  L2: Council - ITT (Seven specialized agent seats)
  L3: Execution - VanguardNodePool (async parallel tasks)
  L4: Integration - MatonBridge (external API gateway)
  L5: Swarm - Distributed execution layer
"""

from .reactor import LumenisReactor, NvidiaReactor, ReasoningReactor
from .compass import FluxCompass
from .itt import ITTCouncil
from .nodes import VanguardNodePool
from .maton import MatonBridge
from .swarm import SwarmOrchestrator, WorkerNode, TaskPulse, SwarmMonitor

__all__ = [
    "LumenisReactor",
    "NvidiaReactor",
    "ReasoningReactor",
    "FluxCompass",
    "ITTCouncil",
    "VanguardNodePool",
    "MatonBridge",
    "SwarmOrchestrator",
    "WorkerNode",
    "TaskPulse",
    "SwarmMonitor",
]
