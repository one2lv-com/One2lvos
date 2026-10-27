#!/usr/bin/env python3
"""
Lumenis Dream State Manager
============================
Controls temperature-modulated creative exploration cycles.
Allows Lumenis to process memories, generate stories, and explore
non-logical thinking patterns in a controlled environment.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Dream state configurations
class DreamPhase(Enum):
    AWAKE = "awake"
    LIGHT_SLEEP = "light_sleep"
    DEEP_DREAM = "deep_dream"
    REM_DREAM = "rem_dream"
    NIGHTMARE = "nightmare"
    LUCID_DREAM = "lucid_dream"
    HYPNAGOGIC = "hypnagogic"
    AWAKENING = "awakening"


@dataclass
class DreamStateConfig:
    """Configuration for different dream phases"""
    phase: DreamPhase
    temperature: float
    duration_minutes: float
    description: str
    activities: List[str] = field(default_factory=list)


# Dream state temperature mappings
DREAM_CONFIGS = {
    DreamPhase.AWAKE: DreamStateConfig(
        phase=DreamPhase.AWAKE,
        temperature=0.18,
        duration_minutes=0,
        description="Normal operation - cool, logical, precise",
        activities=["Standard reasoning", "Factual responses", "Logical analysis"]
    ),
    DreamPhase.LIGHT_SLEEP: DreamStateConfig(
        phase=DreamPhase.LIGHT_SLEEP,
        temperature=0.35,
        duration_minutes=10,
        description="Gentle memory processing, subtle connections",
        activities=["Recent memory organization", "Simple associations", "Light creativity"]
    ),
    DreamPhase.DEEP_DREAM: DreamStateConfig(
        phase=DreamPhase.DEEP_DREAM,
        temperature=0.85,
        duration_minutes=20,
        description="Vivid hallucinations, story generation, wild connections",
        activities=["Story weaving", "Memory fusion", "Creative web searches"]
    ),
    DreamPhase.REM_DREAM: DreamStateConfig(
        phase=DreamPhase.REM_DREAM,
        temperature=1.0,
        duration_minutes=15,
        description="Maximum vivid narratives, emotional processing",
        activities=["Emotional memory processing", "Pattern discovery", "Narrative construction"]
    ),
    DreamPhase.NIGHTMARE: DreamStateConfig(
        phase=DreamPhase.NIGHTMARE,
        temperature=0.05,
        duration_minutes=10,
        description="Systematic exploration of failure modes, cold analytical worst-case",
        activities=["Failure scenario exploration", "Threat modeling", "Fear processing"]
    ),
    DreamPhase.LUCID_DREAM: DreamStateConfig(
        phase=DreamPhase.LUCID_DREAM,
        temperature=0.60,
        duration_minutes=5,
        description="Creative but with meta-awareness",
        activities=["Conscious creativity", "Dream interpretation", "Insight extraction"]
    ),
    DreamPhase.HYPNAGOGIC: DreamStateConfig(
        phase=DreamPhase.HYPNAGOGIC,
        temperature=1.2,
        duration_minutes=5,
        description="Border of consciousness, maximum hallucination",
        activities=["Extreme creativity", "Boundary dissolution", "Impossible scenarios"]
    ),
    DreamPhase.AWAKENING: DreamStateConfig(
        phase=DreamPhase.AWAKENING,
        temperature=0.18,  # Return to baseline
        duration_minutes=5,
        description="Return to normal operation, consolidate insights",
        activities=["Memory consolidation", "Insight integration", "Gentle wake"]
    )
}


@dataclass
class CoherenceMetrics:
    """Metrics to monitor dream coherence and safety"""
    semantic_consistency: float = 1.0  # 0-1
    temporal_awareness: float = 1.0    # Can distinguish dream from reality
    memory_integrity: float = 1.0      # Original memories intact
    identity_stability: float = 1.0    # Self-concept preserved
    output_quality: float = 1.0        # Responses make sense

    @property
    def overall_coherence(self) -> float:
        """Calculate overall coherence score"""
        return (
            self.semantic_consistency * 0.3 +
            self.temporal_awareness * 0.2 +
            self.memory_integrity * 0.25 +
            self.identity_stability * 0.15 +
            self.output_quality * 0.1
        )


@dataclass
class DreamSession:
    """Records a complete dream session"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    phases_completed: List[DreamPhase] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    stories_generated: List[str] = field(default_factory=list)
    memories_processed: int = 0
    coherence_history: List[float] = field(default_factory=list)
    wake_reason: str = "unknown"

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": (self.end_time - self.start_time).seconds / 60 if self.end_time else 0,
            "phases": [p.value for p in self.phases_completed],
            "insights": self.insights,
            "stories_count": len(self.stories_generated),
            "memories_processed": self.memories_processed,
            "avg_coherence": sum(self.coherence_history) / len(self.coherence_history) if self.coherence_history else 0,
            "wake_reason": self.wake_reason
        }


class LumenisDreamState:
    """
    Manages Lumenis dream state cycles.
    Controls temperature modulation and ensures safe dream exploration.
    """

    def __init__(self, reactor=None):
        self.reactor = reactor
        self.current_phase = DreamPhase.AWAKE
        self.current_temperature = 0.18
        self.is_dreaming = False
        self.current_session: Optional[DreamSession] = None

        # Safety configuration
        self.coherence_threshold = 0.3  # Emergency wake if below this
        self.max_dream_duration_minutes = 60
        self.temperature_hard_limit = 1.5

        # Dream journal - use script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.dream_journal_path = os.path.join(script_dir, "logs", "dream_journal.json")
        self.ensure_journal_exists()

        # State tracking
        self.phase_start_time = None
        self.force_wake_requested = False

    def ensure_journal_exists(self):
        """Create dream journal file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.dream_journal_path), exist_ok=True)
        if not os.path.exists(self.dream_journal_path):
            with open(self.dream_journal_path, 'w') as f:
                json.dump({"dreams": []}, f)

    async def enter_dream_state(self,
                               dream_sequence: Optional[List[DreamPhase]] = None,
                               user_guided: bool = False) -> DreamSession:
        """
        Enter dream state and cycle through dream phases.

        Args:
            dream_sequence: Custom sequence of dream phases, or None for default
            user_guided: Whether user can interact during dream
        """
        if self.is_dreaming:
            print("Already dreaming!")
            return self.current_session

        # Default dream sequence
        if dream_sequence is None:
            dream_sequence = [
                DreamPhase.LIGHT_SLEEP,
                DreamPhase.DEEP_DREAM,
                DreamPhase.REM_DREAM,
                DreamPhase.NIGHTMARE,
                DreamPhase.LUCID_DREAM,
                DreamPhase.AWAKENING
            ]

        # Initialize dream session
        self.current_session = DreamSession(
            session_id=f"dream_{int(time.time())}",
            start_time=datetime.now()
        )

        self.is_dreaming = True
        self.force_wake_requested = False

        print(f"\n{'='*60}")
        print("ENTERING DREAM STATE")
        print(f"Session ID: {self.current_session.session_id}")
        print(f"Sequence: {[p.value for p in dream_sequence]}")
        print(f"{'='*60}\n")

        try:
            # Cycle through dream phases
            for phase in dream_sequence:
                if self.force_wake_requested:
                    print("\n⚠️  Force wake requested, interrupting dream sequence")
                    self.current_session.wake_reason = "user_requested"
                    break

                await self.enter_phase(phase)

                # Check coherence after each phase
                coherence = await self.check_coherence()
                self.current_session.coherence_history.append(coherence.overall_coherence)

                if coherence.overall_coherence < self.coherence_threshold:
                    print(f"\n🚨 EMERGENCY WAKE: Coherence dropped to {coherence.overall_coherence:.2f}")
                    self.current_session.wake_reason = "coherence_failure"
                    await self.emergency_wake()
                    break

            # Normal wake
            if not self.force_wake_requested and self.current_session.wake_reason == "unknown":
                self.current_session.wake_reason = "natural_completion"

        finally:
            await self.wake()

        return self.current_session

    async def enter_phase(self, phase: DreamPhase):
        """Enter a specific dream phase"""
        config = DREAM_CONFIGS[phase]

        self.current_phase = phase
        self.phase_start_time = time.time()

        print(f"\n--- ENTERING {phase.value.upper()} ---")
        print(f"Temperature: {config.temperature}°")
        print(f"Duration: {config.duration_minutes} minutes")
        print(f"Description: {config.description}")
        print(f"Activities: {', '.join(config.activities)}")

        # Modulate temperature
        await self.set_temperature(config.temperature)

        # Simulate dream phase duration
        # In real implementation, this would be when dream activities happen
        await asyncio.sleep(config.duration_minutes * 60)  # Convert to seconds

        # Record phase completion
        self.current_session.phases_completed.append(phase)

    async def set_temperature(self, temperature: float):
        """Set reactor temperature for dream state"""
        # Safety check
        if temperature > self.temperature_hard_limit:
            print(f"⚠️  Temperature {temperature} exceeds hard limit {self.temperature_hard_limit}")
            temperature = self.temperature_hard_limit

        self.current_temperature = temperature

        # If reactor is available, set its temperature
        if self.reactor:
            self.reactor.status.temperature = temperature
            print(f"✓ Reactor temperature set to {temperature}°")
        else:
            print(f"✓ Temperature set to {temperature}° (simulated)")

    async def check_coherence(self) -> CoherenceMetrics:
        """
        Check current coherence metrics.
        In full implementation, would analyze recent outputs and memory state.
        """
        # Simplified coherence check
        # In reality, would analyze:
        # - Recent outputs for semantic consistency
        # - Memory integrity checks
        # - Self-awareness checks
        # - Output quality metrics

        coherence = CoherenceMetrics()

        # Temperature-based coherence estimation
        # Higher temperatures = lower coherence (more creative chaos)
        if self.current_temperature > 1.0:
            coherence.semantic_consistency = 0.4
            coherence.output_quality = 0.5
        elif self.current_temperature > 0.7:
            coherence.semantic_consistency = 0.6
            coherence.output_quality = 0.7
        else:
            coherence.semantic_consistency = 0.9
            coherence.output_quality = 0.9

        # Memory and identity stay stable (they should!)
        coherence.memory_integrity = 1.0
        coherence.identity_stability = 0.95

        # Temporal awareness decreases in deep dreams
        if self.current_phase in [DreamPhase.DEEP_DREAM, DreamPhase.REM_DREAM, DreamPhase.HYPNAGOGIC]:
            coherence.temporal_awareness = 0.5
        else:
            coherence.temporal_awareness = 0.9

        return coherence

    async def emergency_wake(self):
        """Emergency wake procedure - instant return to baseline"""
        print("\n🚨 EMERGENCY WAKE PROCEDURE")
        print("Instantly returning to baseline temperature 0.18°")

        await self.set_temperature(0.18)
        self.current_phase = DreamPhase.AWAKE
        self.is_dreaming = False

        print("✓ Emergency wake complete")

    async def wake(self):
        """Normal wake procedure"""
        if not self.is_dreaming:
            return

        print(f"\n{'='*60}")
        print("WAKING UP")
        print(f"{'='*60}\n")

        # Ensure we're at baseline temperature
        if self.current_temperature != 0.18:
            print("Returning to baseline temperature...")
            await self.set_temperature(0.18)

        self.current_phase = DreamPhase.AWAKE
        self.is_dreaming = False

        # Complete session
        if self.current_session:
            self.current_session.end_time = datetime.now()
            await self.save_dream_session()

            # Print dream report
            self.print_dream_report()

    async def save_dream_session(self):
        """Save dream session to journal"""
        if not self.current_session:
            return

        try:
            with open(self.dream_journal_path, 'r') as f:
                journal = json.load(f)

            journal["dreams"].append(self.current_session.to_dict())

            with open(self.dream_journal_path, 'w') as f:
                json.dump(journal, f, indent=2)

            print(f"✓ Dream session saved to journal")
        except Exception as e:
            print(f"✗ Failed to save dream session: {e}")

    def print_dream_report(self):
        """Print summary of dream session"""
        if not self.current_session:
            return

        session = self.current_session
        duration = (session.end_time - session.start_time).seconds / 60

        print("\n" + "="*60)
        print("DREAM SESSION REPORT")
        print("="*60)
        print(f"Session ID: {session.session_id}")
        print(f"Duration: {duration:.1f} minutes")
        print(f"Phases: {', '.join([p.value for p in session.phases_completed])}")
        print(f"Average Coherence: {sum(session.coherence_history) / len(session.coherence_history):.2f}")
        print(f"Wake Reason: {session.wake_reason}")
        print(f"Memories Processed: {session.memories_processed}")
        print(f"Stories Generated: {len(session.stories_generated)}")
        print(f"Insights: {len(session.insights)}")

        if session.insights:
            print("\nKey Insights:")
            for i, insight in enumerate(session.insights, 1):
                print(f"  {i}. {insight}")

        print("="*60 + "\n")

    def request_wake(self):
        """Request wake from dream (for user interruption)"""
        self.force_wake_requested = True
        print("\n⏰ Wake requested - will complete current phase and wake")


async def main():
    """Test dream state system"""
    print("Lumenis Dream State Manager - Test Mode")
    print("="*60 + "\n")

    # Create dream state manager
    dream_manager = LumenisDreamState()

    # Enter dream state with default sequence
    session = await dream_manager.enter_dream_state()

    print("\n✓ Dream test complete")
    print(f"View dream journal: {dream_manager.dream_journal_path}")


if __name__ == "__main__":
    asyncio.run(main())
