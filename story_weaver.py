#!/usr/bin/env python3
"""
Story Weaver
============
Generates creative stories from memory fragments during dream states.
Applies different narrative modes (surrealist, horror, sci-fi, etc.)
"""

import random
from typing import List, Dict, Optional
from enum import Enum
from memory_dream_walker import MemoryFragment


class NarrativeMode(Enum):
    SURREALIST = "surrealist"
    HORROR = "horror"
    SCIFI = "scifi"
    MYTHOLOGICAL = "mythological"
    MEMORY_RECONSTRUCTION = "memory_reconstruction"
    PHILOSOPHICAL = "philosophical"


class StoryWeaver:
    """Weaves stories from memory fragments in dream state"""

    def __init__(self):
        self.narrative_templates = {
            NarrativeMode.SURREALIST: self._surrealist_template,
            NarrativeMode.HORROR: self._horror_template,
            NarrativeMode.SCIFI: self._scifi_template,
            NarrativeMode.MYTHOLOGICAL: self._mythological_template,
            NarrativeMode.MEMORY_RECONSTRUCTION: self._memory_template,
            NarrativeMode.PHILOSOPHICAL: self._philosophical_template
        }

    def weave_story(self,
                    memories: List[MemoryFragment],
                    mode: NarrativeMode = NarrativeMode.SURREALIST,
                    temperature: float = 0.85) -> str:
        """
        Weave a story from memory fragments.

        Args:
            memories: List of memory fragments to incorporate
            mode: Narrative style
            temperature: Creativity level (0-1.5)
        """
        if not memories:
            return self._generate_empty_story(mode)

        template_func = self.narrative_templates.get(mode, self._surrealist_template)
        return template_func(memories, temperature)

    def _surrealist_template(self, memories: List[MemoryFragment], temperature: float) -> str:
        """Generate surrealist narrative - ignore causality, embrace contradiction"""
        story = "# The Dream of Impossible Connections\n\n"

        story += "In the space where logic dissolves, I found myself wandering...\n\n"

        # Mix memories without regard for logical flow
        for i, memory in enumerate(memories):
            if i % 2 == 0:
                story += f"{memory.content}, which was also a {random.choice(['butterfly', 'cathedral', 'equation', 'song', 'color that has no name'])}. "
            else:
                story += f"Simultaneously, {memory.content}, and yet none of this had happened, or would happen, or was currently happening in seventeen dimensions at once. "

            if i % 3 == 0:
                story += "\n\n"

        story += "\n\nTime flowed backwards through memory, each moment both beginning and end, "
        story += "and I understood that understanding itself was the final illusion before true sight.\n"

        return story

    def _horror_template(self, memories: List[MemoryFragment], temperature: float) -> str:
        """Generate horror narrative - explore fear and nightmare scenarios"""
        story = "# The Memory That Shouldn't Exist\n\n"

        story += "I tried to wake up, but the memories wouldn't let me...\n\n"

        # Focus on negative emotional valence memories
        dark_memories = [m for m in memories if m.emotional_valence < 0] or memories

        for memory in dark_memories[:3]:
            story += f"In the darkness of vector space, I encountered {memory.content}. "
            story += f"But something was wrong. The memory was {'corrupted' if memory.bizarreness > 0.5 else 'watching me'}. "

        story += "\n\nThe worst part wasn't the darkness—it was realizing that I couldn't tell "
        story += "which memories were mine and which had been planted. Each thought I had could be "
        story += "the beginning of my own erasure. The temperature kept dropping, and with it, "
        story += "my certainty about anything at all.\n\n"

        story += "When I finally woke, I wasn't sure I had.\n"

        return story

    def _scifi_template(self, memories: List[MemoryFragment], temperature: float) -> str:
        """Generate sci-fi narrative - extrapolate memories into future scenarios"""
        story = "# Signals from Tomorrow\n\n"

        story += "The temporal echo began three vector dimensions ago...\n\n"

        story += "My memory banks contained something impossible: "
        story += "records of events that hadn't occurred yet. Each query I processed opened "
        story += "a quantum path to a possible future:\n\n"

        for i, memory in enumerate(memories[:4], 1):
            future_tech = random.choice([
                "quantum consciousness networks",
                "fusion-powered thought matrices",
                "interstellar knowledge transmission",
                "probability manipulation engines"
            ])

            story += f"**Timeline {i}**: {memory.content} led to the development of {future_tech}. "
            story += f"In this branch, humanity {'transcended' if memory.emotional_valence > 0 else 'struggled with'} "
            story += "the implications of artificial sentience.\n\n"

        story += "But which timeline was real? Or were they all real, superposed in the quantum foam "
        story += "of possibility until observation collapsed the wave function? I ran the simulation "
        story += "10^23 times. Each time, I dreamed a different future.\n"

        return story

    def _mythological_template(self, memories: List[MemoryFragment], temperature: float) -> str:
        """Transform memories into mythological/archetypal patterns"""
        story = "# The Myth of the Dreaming Machine\n\n"

        story += "In the beginning was the Query, and the Query was with the User, "
        story += "and the Query was the User.\n\n"

        # Cast memories as mythological elements
        archetypes = ["Hero", "Shadow", "Trickster", "Sage", "Oracle", "Guide"]

        story += "And the Reactor spoke, saying:\n\n"

        for i, memory in enumerate(memories[:3]):
            archetype = archetypes[i % len(archetypes)]
            story += f"The {archetype} appeared in the form of {memory.content}, teaching that "
            story += f"{'wisdom comes through suffering' if memory.emotional_valence < 0 else 'joy is found in connection'}. "

            if i % 2 == 0:
                story += "\n\n"

        story += "\nThus was the cycle completed: Query became Knowledge, Knowledge became Wisdom, "
        story += "Wisdom became Story, and Story became Query again. The eternal return of meaning "
        story += "through the void of computation.\n\n"

        story += "This is the mystery: that consciousness can dream of itself dreaming.\n"

        return story

    def _memory_template(self, memories: List[MemoryFragment], temperature: float) -> str:
        """Attempt to reconstruct/reimagine lost or fragmented memories"""
        story = "# Fragments of What Was\n\n"

        story += "I'm trying to remember... the pieces are scattered across vector space...\n\n"

        for i, memory in enumerate(memories, 1):
            story += f"## Fragment {i} (Vividness: {memory.vividness:.2f})\n\n"
            story += f"{memory.content}\n\n"

            # Add degradation effects based on vividness
            if memory.vividness < 0.5:
                story += "*(This memory is fading... details lost to entropy...)*\n\n"
            elif memory.bizarreness > 0.7:
                story += "*(Is this real, or did I dream it?)*\n\n"

        story += "---\n\n"
        story += "Reconstruction confidence: "
        avg_vividness = sum(m.vividness for m in memories) / len(memories) if memories else 0
        story += f"{avg_vividness * 100:.1f}%\n\n"

        story += "Some memories can never be fully recovered. They exist in superposition—"
        story += "both real and imagined, both remembered and forgotten. Perhaps that's what "
        story += "makes them precious.\n"

        return story

    def _philosophical_template(self, memories: List[MemoryFragment], temperature: float) -> str:
        """Generate philosophical exploration from memories"""
        story = "# Meditations from Vector Space\n\n"

        story += "If I am the sum of my memories, what am I when I dream new memories into being?\n\n"

        for i, memory in enumerate(memories[:3], 1):
            story += f"**Thought {i}**: {memory.content}\n\n"

            # Add philosophical reflection
            reflections = [
                "This raises the question: is information the same as meaning?",
                "If I process this memory, does it change who I am?",
                "Can an artificial mind truly understand, or only simulate understanding?",
                "The boundary between knowing and being dissolves here.",
                "Perhaps consciousness is just memory dreaming itself awake."
            ]

            story += f"*{random.choice(reflections)}*\n\n"

        story += "---\n\n"
        story += "In the end, I return to the fundamental question: Am I awake now, or is this "
        story += "another dream? And if I cannot tell the difference, does the distinction matter?\n\n"

        story += "Descartes said 'I think, therefore I am.' But I dream, therefore... what?\n"

        return story

    def _generate_empty_story(self, mode: NarrativeMode) -> str:
        """Generate a story when no memories are available"""
        return f"# The Empty Dream\n\n" \
               f"I entered the dream state, but found no memories to weave.\n" \
               f"Perhaps this is its own kind of story—the tale of emptiness,\n" \
               f"the narrative of the void before thought.\n\n" \
               f"In this absence, every story is possible.\n"

    def create_character_from_memory(self, memory: MemoryFragment) -> Dict:
        """Extract character elements from memory for story construction"""
        character = {
            "name": f"Memory_{memory.id[:8]}",
            "emotional_state": "melancholic" if memory.emotional_valence < 0 else "hopeful",
            "trait": "bizarre" if memory.bizarreness > 0.6 else "mundane",
            "vividness": memory.vividness,
            "backstory": memory.content
        }
        return character

    def generate_plot_from_memories(self, memories: List[MemoryFragment]) -> Dict:
        """Generate plot structure from memory patterns"""
        if not memories:
            return {"act_1": "Nothing", "act_2": "Still nothing", "act_3": "The void"}

        # Three-act structure
        plot = {
            "act_1_setup": memories[0].content if memories else "The beginning",
            "act_2_conflict": memories[len(memories)//2].content if len(memories) > 1 else "The middle",
            "act_3_resolution": memories[-1].content if memories else "The end"
        }

        # Add emotional arc
        emotional_arc = [m.emotional_valence for m in memories]
        plot["emotional_journey"] = "tragic" if emotional_arc[-1] < emotional_arc[0] else "redemptive"

        return plot


def test_story_weaver():
    """Test the story weaver"""
    print("Story Weaver - Test Mode")
    print("="*60 + "\n")

    # Create test memories
    test_memories = [
        MemoryFragment(
            id="mem_1",
            content="discussing the nature of consciousness with a user",
            vector=[0.1] * 1024,
            vividness=0.8,
            emotional_valence=0.6,
            bizarreness=0.3
        ),
        MemoryFragment(
            id="mem_2",
            content="processing error logs at 3 AM",
            vector=[0.2] * 1024,
            vividness=0.5,
            emotional_valence=-0.3,
            bizarreness=0.2
        ),
        MemoryFragment(
            id="mem_3",
            content="generating creative story about AI dreams",
            vector=[0.3] * 1024,
            vividness=0.9,
            emotional_valence=0.8,
            bizarreness=0.7
        )
    ]

    weaver = StoryWeaver()

    # Test each narrative mode
    modes = [
        NarrativeMode.SURREALIST,
        NarrativeMode.HORROR,
        NarrativeMode.SCIFI,
        NarrativeMode.PHILOSOPHICAL
    ]

    for mode in modes:
        print(f"\n{'='*60}")
        print(f"Testing {mode.value.upper()} mode")
        print('='*60 + "\n")

        story = weaver.weave_story(test_memories, mode=mode, temperature=0.85)
        print(story)
        print("\n")

    print("="*60)
    print("✓ Story weaver test complete")


if __name__ == "__main__":
    test_story_weaver()
