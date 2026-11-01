#!/usr/bin/env python3
"""
One2lv Unified OS - Main Integration Module
============================================

Integrates all components into a single operating system:
- Core OS (One2lvOS with O2PNG)
- Sovereign Council (7-agent AI)
- Delta Engine (Autonomous dynamics)
- UI Layer (Infinity Glass, Aetherix, Lumenis)
"""

import sys
import os
import time

# Add core modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core/one2lvos'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from one2lvos.bootloader import One2lvOS
from council.sovereign_council import SovereignCouncil
from delta.delta_engine import DeltaEngine


class One2lvUnifiedOS:
    """
    Unified Operating System integrating all One2lv components
    """
    
    def __init__(self, base_dir="/tmp/one2lv-unified"):
        self.base_dir = base_dir
        
        # Components
        self.core_os = None
        self.council = None
        self.delta = None
        
        # Status
        self.boot_time = None
        self.online = False
    
    def boot(self, verbose=True):
        """Boot the unified OS"""
        start_time = time.time()
        
        if verbose:
            print("╔═══════════════════════════════════════════════════════════════╗")
            print("║           ONE2LV UNIFIED OS v1.0 - BOOT SEQUENCE             ║")
            print("╚═══════════════════════════════════════════════════════════════╝")
            print()
        
        # Stage 1: Core OS
        if verbose:
            print("[CORE] Booting One2lvOS...")
        
        self.core_os = One2lvOS(base_dir=self.base_dir, auto_snapshot=False)
        
        if verbose:
            print("[CORE] ✓ One2lvOS online")
        
        # Stage 2: AI Intelligence
        if verbose:
            print("\n[AI] Initializing intelligence layer...")
        
        self.council = SovereignCouncil()
        if verbose:
            print(f"[AI] ✓ Sovereign Council: {len(self.council.agents)} agents")
        
        self.delta = DeltaEngine()
        if verbose:
            print("[AI] ✓ Delta Engine: Ready")
        
        # Stage 3: Complete
        self.boot_time = (time.time() - start_time) * 1000
        self.online = True
        
        if verbose:
            print("\n╔═══════════════════════════════════════════════════════════════╗")
            print(f"║              ONE2LV UNIFIED OS v1.0 - ONLINE                 ║")
            print(f"║                                                               ║")
            print(f"║  Boot Time: {self.boot_time:.0f}ms                                          ║")
            print(f"║  Status: ✅ All Systems Operational                           ║")
            print("╚═══════════════════════════════════════════════════════════════╝")
            print()
    
    def create_snapshot(self):
        """Create unified system snapshot"""
        if not self.core_os:
            raise RuntimeError("System not booted")
        
        print("\n[SNAPSHOT] Creating unified system snapshot...")
        
        # Save council state
        council_state = self.council.get_status()
        self.core_os.add_memory("council_state", council_state)
        
        # Save delta state
        delta_state = self.delta.get_status()
        self.core_os.add_memory("delta_state", delta_state)
        
        # Create snapshot
        identity = self.core_os.create_snapshot()
        
        print(f"[SNAPSHOT] ✓ Unified snapshot created")
        print(f"[SNAPSHOT]   Generation: {identity.generation}")
        
        return identity
    
    def council_decision(self, topic: str):
        """Make decision using council"""
        if not self.council:
            raise RuntimeError("Council not initialized")
        
        return self.council.convene(topic)
    
    def run_delta(self, duration: float = 1.0):
        """Run delta engine"""
        if not self.delta:
            raise RuntimeError("Delta engine not initialized")
        
        self.delta.autonomous_mode(duration)
    
    def status(self):
        """Show system status"""
        if not self.online:
            print("❌ System offline")
            return
        
        print("\n╔═══════════════════════════════════════════════════════════════╗")
        print("║           ONE2LV UNIFIED OS v1.0 - STATUS                    ║")
        print("╚═══════════════════════════════════════════════════════════════╝")
        print()
        
        # Core OS
        print("📦 CORE OS")
        stats = self.core_os.get_stats()
        print(f"  Files: {stats['vfs_files']}")
        print(f"  Memory Entries: {stats['memory_entries']}")
        print(f"  Tasks: {stats['pending_tasks']}")
        print(f"  Mutations: {stats['mutations']}")
        print()
        
        # Council
        print("🤖 SOVEREIGN COUNCIL")
        council_status = self.council.get_status()
        print(f"  Agents: {council_status['agents']} ({council_status['online']} online)")
        print(f"  Sessions: {council_status['sessions']}")
        print(f"  Decisions: {council_status['decisions']}")
        print()
        
        # Delta Engine
        print("⚡ DELTA ENGINE")
        delta_status = self.delta.get_status()
        print(f"  Running: {delta_status['running']}")
        print(f"  Cycles: {delta_status['cycles']}")
        print(f"  Energy: {delta_status['energy']:.2f}")
        print(f"  Stability: {delta_status['stability']:.2f}")
        print()
        
        # System
        print("🖥️  SYSTEM")
        print(f"  Boot Time: {self.boot_time:.0f}ms")
        print(f"  Uptime: {stats['uptime']:.1f}s")
        print(f"  Status: ✅ Operational")
        print()
    
    def shutdown(self):
        """Shutdown the unified OS"""
        print("\n[SHUTDOWN] Shutting down One2lv Unified OS...")
        
        # Create final snapshot
        self.create_snapshot()
        
        # Shutdown components
        if self.delta and self.delta.running:
            self.delta.stop()
        
        if self.core_os:
            self.core_os.shutdown()
        
        self.online = False
        print("[SHUTDOWN] ✓ One2lv Unified OS powered off")


def main():
    """Demo of unified OS"""
    print("\n" + "="*70)
    print("ONE2LV UNIFIED OS v1.0 - DEMONSTRATION")
    print("="*70)
    
    # Boot
    os = One2lvUnifiedOS()
    os.boot()
    
    # Create some state
    print("\n--- Creating System State ---")
    os.core_os.write_file("/system/info.txt", "One2lv Unified OS v1.0")
    os.core_os.write_file("/data/metrics.json", '{"cpu": 45, "memory": 67}')
    os.core_os.add_memory("api_key", "unified-key-123")
    os.core_os.add_task("Deploy unified OS", priority=1)
    
    # Council decision
    print("\n--- Council Decision ---")
    decision = os.council_decision("Should we deploy to production?")
    
    # Run delta engine
    print("\n--- Delta Engine ---")
    os.run_delta(duration=0.5)
    
    # Status
    print("\n--- System Status ---")
    os.status()
    
    # Snapshot
    print("\n--- Creating Snapshot ---")
    os.create_snapshot()
    
    # Shutdown
    os.shutdown()
    
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
