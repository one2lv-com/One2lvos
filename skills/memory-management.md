---
name: memory-management
version: 1.0.0
description: "Store and recall facts, preferences and conversation context in Lumenis's scope-tagged memory."
triggers:
  - "/memory-management"
  - "remember that"
  - "what did i say about"
  - "forget that"
tools:
  - "compass.recall_facts"
  - "compass.store_fact"
risk_tier: L1
guardrails:
  - no_canonical_without_owner
  - dreams_stay_dreams
  - temporary_never_promoted
---

# memory-management

Converted from the uploaded skills.md (`memory_management`, 2026-11-16). The existing `memory` skill covers
the compile loop; this one is the everyday remember/recall path.

Facts are stored with their source and confidence. Dream material stays in dream storage and is never
recalled as fact. "Forget" is not automatic: removing a stored fact is an owner action.
