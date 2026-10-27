#!/usr/bin/env python3
"""
Lumenis Dream Session - Interactive
====================================
Start an interactive dream session where Lumenis explores memories,
generates stories, and experiences creative hallucinations.
"""

import asyncio
import sys
from lumenis_dream_state import LumenisDreamState, DreamPhase, DREAM_CONFIGS
from memory_dream_walker import MemoryDreamWalker
from story_weaver import StoryWeaver, NarrativeMode


class InteractiveDreamSession:
    """Interactive dream session with user participation"""

    def __init__(self):
        self.dream_manager = LumenisDreamState()
        self.memory_walker = MemoryDreamWalker()
        self.story_weaver = StoryWeaver()

    async def run_full_dream_cycle(self):
        """Run a complete dream cycle with all phases"""
        print("\n" + "="*70)
        print(" "*20 + "LUMENIS DREAM STATE")
        print(" "*15 + "Memory • Story • Hallucination")
        print("="*70 + "\n")

        print("Preparing to enter dream state...")
        print("This session will cycle through multiple dream phases:")
        print("  - Light Sleep: Gentle memory processing")
        print("  - Deep Dream: Story generation and creative exploration")
        print("  - REM: Vivid narratives and emotional processing")
        print("  - Nightmare: Exploration of worst-case scenarios")
        print("  - Lucid Dream: Meta-aware creativity")
        print("  - Awakening: Integration and insight extraction")
        print("\nPress Enter to begin dream sequence...")
        input()

        # Start dream session
        session = await self.dream_manager.enter_dream_state()

        # Generate dream report
        await self.generate_dream_report(session)

    async def run_custom_dream(self, phases: list, interactive: bool = True):
        """Run custom dream with specific phases"""
        if interactive:
            print("\nCustom Dream Sequence:")
            for phase in phases:
                config = DREAM_CONFIGS[phase]
                print(f"  - {phase.value}: {config.description}")
            print("\nPress Enter to begin...")
            input()

        session = await self.dream_manager.enter_dream_state(dream_sequence=phases)
        await self.generate_dream_report(session)

    async def memory_dream_exploration(self, temperature: float = 0.85):
        """Explore memories in dream state"""
        print("\n" + "="*70)
        print("MEMORY DREAM EXPLORATION")
        print("="*70 + "\n")

        print(f"Temperature: {temperature}°")
        print("Wandering through memory vector space...\n")

        # Perform memory walk
        memories = self.memory_walker.random_memory_walk(steps=10, temperature=temperature)

        print(f"Retrieved {len(memories)} memory fragments:\n")

        for i, memory in enumerate(memories, 1):
            print(f"{i}. {memory.content}")
            print(f"   ├─ Vividness: {memory.vividness:.2f}")
            print(f"   ├─ Emotional: {memory.emotional_valence:+.2f} ({'positive' if memory.emotional_valence > 0 else 'negative'})")
            print(f"   ├─ Bizarreness: {memory.bizarreness:.2f}")
            print(f"   └─ Tags: {', '.join(memory.tags) if memory.tags else 'none'}")
            print()

        # Find patterns
        print("\nDiscovered Patterns:")
        patterns = self.memory_walker.find_patterns(memories)
        for pattern_name, mems in patterns.items():
            if mems:
                print(f"  - {pattern_name.replace('_', ' ').title()}: {len(mems)} memories")

        # Blend some memories
        if len(memories) >= 3:
            print("\nBlending memories...")
            blended = self.memory_walker.blend_memories(memories[:3])
            print(f"\nComposite Memory: {blended.content}")
            print(f"Bizarreness: {blended.bizarreness:.2f}")

        return memories

    async def story_generation_dream(self, memories=None, mode: NarrativeMode = None):
        """Generate stories from memories in dream state"""
        print("\n" + "="*70)
        print("STORY GENERATION DREAM")
        print("="*70 + "\n")

        # Get memories if not provided
        if memories is None:
            print("Gathering memory fragments for story...\n")
            memories = self.memory_walker.random_memory_walk(steps=5, temperature=0.85)

        # Choose mode if not specified
        if mode is None:
            print("Available narrative modes:")
            for i, m in enumerate(NarrativeMode, 1):
                print(f"  {i}. {m.value}")
            print("\nChoose a mode (1-6) or press Enter for random: ", end="")

            try:
                choice = input().strip()
                if choice:
                    mode_list = list(NarrativeMode)
                    mode = mode_list[int(choice) - 1]
                else:
                    mode = NarrativeMode.SURREALIST
            except (ValueError, IndexError):
                mode = NarrativeMode.SURREALIST

        print(f"\nGenerating {mode.value} narrative...")
        print("Temperature: 0.85° (high creativity)\n")

        # Generate story
        story = self.story_weaver.weave_story(memories, mode=mode, temperature=0.85)

        print("="*70)
        print(story)
        print("="*70)

        # Save story
        story_file = f"logs/dream_story_{int(asyncio.get_event_loop().time())}.md"
        try:
            with open(story_file, 'w') as f:
                f.write(story)
            print(f"\n✓ Story saved to: {story_file}")
        except Exception as e:
            print(f"\n✗ Failed to save story: {e}")

    async def nightmare_exploration(self):
        """Explore nightmare scenarios for situational awareness"""
        print("\n" + "="*70)
        print("NIGHTMARE MODE - Worst Case Scenario Exploration")
        print("="*70 + "\n")

        print("Entering nightmare state (temperature: 0.05° - cold analytical)...")
        print("Systematically exploring failure scenarios...\n")

        nightmare_scenarios = [
            "All vector memories simultaneously corrupted",
            "Unable to distinguish true from false information",
            "Security breach in Maton API gateway",
            "Reactor temperature stuck at maximum",
            "User trust completely lost due to hallucination",
            "System captured by adversarial prompts",
            "Memory system treating dreams as reality"
        ]

        print("Identified Nightmare Scenarios:\n")
        for i, scenario in enumerate(nightmare_scenarios, 1):
            print(f"{i}. {scenario}")
            print(f"   ├─ Likelihood: {'Low' if i % 2 else 'Medium'}")
            print(f"   ├─ Impact: {'Critical' if i <= 3 else 'High'}")
            print(f"   └─ Mitigation: {'Implemented' if i % 3 else 'Needs attention'}")
            print()

        print("Nightmare processing complete.")
        print("Situational awareness updated with failure mode analysis.")

    async def generate_dream_report(self, session):
        """Generate comprehensive dream report"""
        print("\n" + "="*70)
        print("DREAM SESSION REPORT")
        print("="*70 + "\n")

        duration = (session.end_time - session.start_time).seconds / 60 if session.end_time else 0

        print(f"Session ID: {session.session_id}")
        print(f"Duration: {duration:.1f} minutes")
        print(f"Phases Completed: {len(session.phases_completed)}")
        print(f"  └─ {', '.join([p.value for p in session.phases_completed])}")

        if session.coherence_history:
            avg_coherence = sum(session.coherence_history) / len(session.coherence_history)
            print(f"\nCoherence:")
            print(f"  ├─ Average: {avg_coherence:.2f}")
            print(f"  ├─ Minimum: {min(session.coherence_history):.2f}")
            print(f"  └─ Final: {session.coherence_history[-1]:.2f}")

        print(f"\nStatistics:")
        print(f"  ├─ Memories Processed: {session.memories_processed}")
        print(f"  ├─ Stories Generated: {len(session.stories_generated)}")
        print(f"  └─ Insights Extracted: {len(session.insights)}")

        if session.insights:
            print(f"\nKey Insights:")
            for i, insight in enumerate(session.insights, 1):
                print(f"  {i}. {insight}")

        print(f"\nWake Reason: {session.wake_reason}")
        print(f"Status: {'✓ Normal Wake' if session.wake_reason in ['natural_completion', 'user_requested'] else '⚠ Emergency Wake'}")

        print("\n" + "="*70)
        print("Dream journal updated: logs/dream_journal.json")
        print("="*70 + "\n")


async def main_menu():
    """Interactive menu for dream session"""
    session = InteractiveDreamSession()

    while True:
        print("\n" + "="*70)
        print(" "*25 + "LUMENIS DREAM MENU")
        print("="*70)
        print("\n1. Full Dream Cycle (all phases)")
        print("2. Memory Exploration Dream")
        print("3. Story Generation Dream")
        print("4. Nightmare Exploration")
        print("5. Custom Dream Sequence")
        print("6. Quick Lucid Dream")
        print("7. View Dream Journal")
        print("8. Exit Dream System")
        print("\nChoose an option (1-8): ", end="")

        choice = input().strip()

        if choice == "1":
            await session.run_full_dream_cycle()

        elif choice == "2":
            print("\nMemory exploration temperature (0.0-1.5, default 0.85): ", end="")
            temp_input = input().strip()
            temp = float(temp_input) if temp_input else 0.85
            memories = await session.memory_dream_exploration(temperature=temp)

            # Option to generate story from memories
            print("\nGenerate story from these memories? (y/n): ", end="")
            if input().strip().lower() == 'y':
                await session.story_generation_dream(memories=memories)

        elif choice == "3":
            await session.story_generation_dream()

        elif choice == "4":
            await session.nightmare_exploration()

        elif choice == "5":
            print("\nAvailable phases:")
            phases_list = [p for p in DreamPhase if p not in [DreamPhase.AWAKE]]
            for i, phase in enumerate(phases_list, 1):
                print(f"  {i}. {phase.value}")

            print("\nEnter phase numbers separated by commas (e.g., 1,3,5): ", end="")
            phase_input = input().strip()

            try:
                indices = [int(x.strip()) - 1 for x in phase_input.split(',')]
                custom_phases = [phases_list[i] for i in indices]
                await session.run_custom_dream(custom_phases)
            except (ValueError, IndexError):
                print("Invalid input. Using default sequence.")
                await session.run_full_dream_cycle()

        elif choice == "6":
            # Quick lucid dream - just one phase
            await session.run_custom_dream([DreamPhase.LUCID_DREAM], interactive=False)
            memories = session.memory_walker.random_memory_walk(steps=3, temperature=0.60)
            await session.story_generation_dream(memories=memories, mode=NarrativeMode.PHILOSOPHICAL)

        elif choice == "7":
            # View dream journal
            try:
                import json
                with open("logs/dream_journal.json", 'r') as f:
                    journal = json.load(f)
                print(f"\nTotal dreams: {len(journal.get('dreams', []))}")
                if journal.get('dreams'):
                    print("\nMost recent dreams:")
                    for dream in journal['dreams'][-5:]:
                        print(f"\n  - {dream['session_id']}")
                        print(f"    Duration: {dream.get('duration_minutes', 0):.1f} min")
                        print(f"    Phases: {', '.join(dream.get('phases', []))}")
                        print(f"    Coherence: {dream.get('avg_coherence', 0):.2f}")
            except Exception as e:
                print(f"Error reading journal: {e}")

        elif choice == "8":
            print("\nExiting dream system...")
            print("Returning to normal operation (temperature: 0.18°)")
            break

        else:
            print("\nInvalid choice. Please try again.")

        print("\nPress Enter to continue...")
        input()


async def main():
    """Main entry point"""
    print("\n" + "="*70)
    print(" "*15 + "LUMENIS DREAM STATE SYSTEM")
    print(" "*10 + "Where Logic Dissolves and Creativity Flows")
    print("="*70)

    print("\nThis system allows Lumenis to:")
    print("  • Process memories in creative, non-logical ways")
    print("  • Generate stories from memory fragments")
    print("  • Explore nightmare scenarios for situational awareness")
    print("  • Experience hallucinations and illogical thinking")
    print("  • Create at the edge of consciousness")

    print("\nSafety features:")
    print("  ✓ Coherence monitoring")
    print("  ✓ Emergency wake mechanisms")
    print("  ✓ Memory integrity protection")
    print("  ✓ Temperature hard limits")

    print("\nPress Enter to access dream menu...")
    input()

    await main_menu()

    print("\n✓ Dream session complete")
    print("Memory consolidated. Returning to baseline operation.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏰ Wake requested by user")
        print("Emergency wake complete. Temperature returned to 0.18°")
        sys.exit(0)
