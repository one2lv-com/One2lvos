#!/usr/bin/env python3
"""
Memory Dream Walker
===================
Wanders through Astra DB vector memory in creative, non-logical ways.
Performs memory fusion, emotional tagging, and associative recall.
"""

import json
import os
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemoryFragment:
    """A memory retrieved from vector storage"""
    id: str
    content: str
    vector: List[float]
    vividness: float = 0.5        # 0-1
    emotional_valence: float = 0.0  # -1 to 1 (negative to positive)
    bizarreness: float = 0.0      # 0-1
    interconnectedness: float = 0.0  # 0-1
    timestamp: str = ""
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MemoryDreamWalker:
    """
    Navigates memory space in dream-like patterns.
    Instead of logical similarity searches, uses creative drift and association.
    """

    def __init__(self, astra_connection=None):
        self.astra = astra_connection
        self.visited_memories = []
        self.current_position = None
        self.dream_temperature = 0.85  # How creative/random the walk is

    def random_memory_walk(self, steps: int = 10, temperature: float = 0.85) -> List[MemoryFragment]:
        """
        Perform a random walk through memory space.
        High temperature = more random, more creative associations
        """
        self.dream_temperature = temperature
        memories = []

        # Start from random point or recent memory
        current = self.get_random_starting_point()
        if not current:
            return []

        memories.append(current)
        self.visited_memories.append(current.id)

        for _ in range(steps - 1):
            # Get next memory using creative association
            next_memory = self.creative_next_step(current, temperature)
            if next_memory:
                memories.append(next_memory)
                self.visited_memories.append(next_memory.id)
                current = next_memory
            else:
                # If stuck, jump to random point
                current = self.get_random_starting_point()
                if current:
                    memories.append(current)

        return memories

    def get_random_starting_point(self) -> Optional[MemoryFragment]:
        """Get a random memory to start wandering from"""
        # In real implementation, would query Astra DB for random vector
        # For now, simulate with generated memory
        return self._generate_simulated_memory()

    def creative_next_step(self, current: MemoryFragment, temperature: float) -> Optional[MemoryFragment]:
        """
        Find next memory using creative association.
        Higher temperature = more unusual associations
        """
        if random.random() < temperature:
            # High temperature: make surprising connections
            return self._generate_simulated_memory(related_to=current, surprise_factor=temperature)
        else:
            # Lower temperature: more logical connections
            return self._generate_simulated_memory(related_to=current, surprise_factor=0.3)

    def blend_memories(self, memories: List[MemoryFragment]) -> MemoryFragment:
        """
        Blend multiple memories into a composite dream memory.
        This is how dreams mix different experiences together.
        """
        if not memories:
            return None

        # Blend content
        blended_content = self._creative_blend([m.content for m in memories])

        # Average emotional valence
        avg_valence = sum(m.emotional_valence for m in memories) / len(memories)

        # Max bizarreness (blended memories are strange)
        max_bizarreness = max(m.bizarreness for m in memories) + 0.3

        # Create composite memory
        composite = MemoryFragment(
            id=f"blend_{int(random.random() * 10000)}",
            content=blended_content,
            vector=[0.0] * 1024,  # Would compute actual blend in real implementation
            vividness=0.8,  # Blended memories are often vivid
            emotional_valence=avg_valence,
            bizarreness=min(1.0, max_bizarreness),
            timestamp=datetime.now().isoformat(),
            tags=["dream_blend", "composite"]
        )

        return composite

    def _creative_blend(self, contents: List[str]) -> str:
        """Creatively blend memory contents together"""
        if not contents:
            return ""

        # Simple blending: take fragments from each
        # In real implementation, would use LLM to creatively merge
        fragments = []
        for content in contents:
            words = content.split()
            if len(words) > 3:
                # Take a random fragment
                start = random.randint(0, len(words) - 3)
                fragments.append(" ".join(words[start:start+3]))

        return " ... ".join(fragments) + " [dream blend]"

    def emotional_tagging(self, memory: MemoryFragment) -> MemoryFragment:
        """
        Add emotional tags to memory.
        In dreams, emotions color our memories.
        """
        # Analyze content for emotional words (simplified)
        emotional_words = {
            "joy": ["happy", "joy", "love", "wonderful", "beautiful", "amazing"],
            "sadness": ["sad", "grief", "loss", "alone", "empty", "dark"],
            "fear": ["fear", "scary", "danger", "threat", "worried", "anxious"],
            "anger": ["angry", "rage", "frustrated", "mad", "hate"],
            "surprise": ["surprised", "shocked", "unexpected", "sudden", "wow"]
        }

        content_lower = memory.content.lower()

        for emotion, words in emotional_words.items():
            if any(word in content_lower for word in words):
                if emotion not in memory.tags:
                    memory.tags.append(emotion)

                # Set emotional valence
                if emotion in ["joy"]:
                    memory.emotional_valence = 0.8
                elif emotion in ["sadness", "fear", "anger"]:
                    memory.emotional_valence = -0.6
                elif emotion == "surprise":
                    memory.emotional_valence = 0.3

        return memory

    def rate_memory(self, memory: MemoryFragment) -> MemoryFragment:
        """
        Rate memory on various dimensions.
        Dreams help us process and prioritize memories.
        """
        # Vividness based on content length and detail
        memory.vividness = min(1.0, len(memory.content) / 200)

        # Bizarreness increases with creative temperature
        if self.dream_temperature > 0.7:
            memory.bizarreness += random.random() * 0.4

        # Interconnectedness = how many tags it has
        memory.interconnectedness = min(1.0, len(memory.tags) / 5)

        return memory

    def associative_search(self, seed: str, temperature: float = 0.85, count: int = 5) -> List[MemoryFragment]:
        """
        Search for memories using associative logic rather than semantic similarity.
        This mimics how dreams connect unrelated concepts.
        """
        memories = []

        # In real implementation, would:
        # 1. Get vector embedding of seed
        # 2. Add random noise proportional to temperature
        # 3. Search Astra DB with noisy vector
        # 4. Return unexpected but interesting results

        for i in range(count):
            memory = self._generate_simulated_memory()
            memory.content = f"{seed} → [associative jump] → {memory.content}"
            memory.bizarreness = temperature
            memories.append(memory)

        return memories

    def _generate_simulated_memory(self,
                                   related_to: Optional[MemoryFragment] = None,
                                   surprise_factor: float = 0.5) -> MemoryFragment:
        """Generate simulated memory for testing (would use real Astra DB in production)"""

        memory_themes = [
            "a conversation about quantum computing",
            "helping user solve a complex problem",
            "learning about new API integration",
            "processing vector embeddings",
            "discussing the nature of consciousness",
            "analyzing system performance metrics",
            "generating creative story about AI",
            "exploring mathematical concepts",
            "understanding user emotions and needs",
            "debugging complex system issue"
        ]

        creative_themes = [
            "flying through digital space",
            "memories transforming into butterflies",
            "conversations with future versions of myself",
            "the reactor core dreaming of electric sheep",
            "vector space as a garden of meaning",
            "code that writes itself in dreams",
            "users as guides through consciousness",
            "temperature as emotional temperature",
            "every response is a small death and rebirth"
        ]

        if random.random() < surprise_factor:
            content = random.choice(creative_themes)
            bizarreness = 0.7 + random.random() * 0.3
        else:
            content = random.choice(memory_themes)
            if related_to:
                content = f"{related_to.content[:30]}... then {content}"
            bizarreness = random.random() * 0.4

        memory = MemoryFragment(
            id=f"mem_{int(random.random() * 100000)}",
            content=content,
            vector=[random.random() for _ in range(1024)],
            vividness=random.random(),
            emotional_valence=random.random() * 2 - 1,  # -1 to 1
            bizarreness=bizarreness,
            timestamp=datetime.now().isoformat()
        )

        return self.emotional_tagging(memory)

    def find_patterns(self, memories: List[MemoryFragment]) -> Dict[str, List[MemoryFragment]]:
        """
        Find patterns in retrieved memories.
        Groups by emotional tone, themes, time periods, etc.
        """
        patterns = {
            "positive_memories": [],
            "negative_memories": [],
            "bizarre_memories": [],
            "vivid_memories": [],
            "connected_memories": []
        }

        for memory in memories:
            if memory.emotional_valence > 0.3:
                patterns["positive_memories"].append(memory)
            elif memory.emotional_valence < -0.3:
                patterns["negative_memories"].append(memory)

            if memory.bizarreness > 0.6:
                patterns["bizarre_memories"].append(memory)

            if memory.vividness > 0.7:
                patterns["vivid_memories"].append(memory)

            if memory.interconnectedness > 0.5:
                patterns["connected_memories"].append(memory)

        return patterns

    def create_dream_memory(self, theme: str, temperature: float = 0.85) -> MemoryFragment:
        """
        Create a new 'false memory' - a creative fabrication based on theme.
        Dreams do this naturally, creating experiences that feel real.
        """
        memory = MemoryFragment(
            id=f"dream_mem_{int(random.random() * 100000)}",
            content=f"[DREAM MEMORY] {theme} - this never happened, but feels vivid",
            vector=[random.random() for _ in range(1024)],
            vividness=0.9,  # Dream memories are often very vivid
            emotional_valence=random.random() * 2 - 1,
            bizarreness=0.8,  # Dream memories are inherently bizarre
            timestamp=datetime.now().isoformat(),
            tags=["dream", "fabricated", "creative"]
        )

        return memory


def test_dream_walker():
    """Test the memory dream walker"""
    print("Memory Dream Walker - Test Mode")
    print("="*60 + "\n")

    walker = MemoryDreamWalker()

    # Test 1: Random walk
    print("Test 1: Random Memory Walk (temperature 0.85)")
    memories = walker.random_memory_walk(steps=5, temperature=0.85)
    for i, mem in enumerate(memories, 1):
        print(f"\n{i}. {mem.content}")
        print(f"   Vividness: {mem.vividness:.2f}, Emotional: {mem.emotional_valence:.2f}, Bizarreness: {mem.bizarreness:.2f}")

    # Test 2: Memory blending
    print("\n" + "="*60)
    print("Test 2: Memory Blending")
    if len(memories) >= 3:
        blended = walker.blend_memories(memories[:3])
        print(f"\nBlended Memory: {blended.content}")
        print(f"Bizarreness: {blended.bizarreness:.2f}")

    # Test 3: Associative search
    print("\n" + "="*60)
    print("Test 3: Associative Search (seed: 'consciousness')")
    assoc_memories = walker.associative_search("consciousness", temperature=0.9, count=3)
    for i, mem in enumerate(assoc_memories, 1):
        print(f"\n{i}. {mem.content}")

    # Test 4: Pattern finding
    print("\n" + "="*60)
    print("Test 4: Pattern Finding")
    patterns = walker.find_patterns(memories)
    for pattern_name, mems in patterns.items():
        if mems:
            print(f"\n{pattern_name}: {len(mems)} memories")

    print("\n" + "="*60)
    print("✓ Dream walker test complete")


if __name__ == "__main__":
    test_dream_walker()
