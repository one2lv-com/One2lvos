---
name: memory
version: 1.0.0
description: "Recall and store Lumenis's scope-tagged memory (stable, fuzzy, temporary) and run the compile loop."
triggers:
  - "/memory"
  - "what do you remember"
  - "recall"
tools:
  - "compass.recall_facts"
  - "compass.store_fact"
  - "memory_hub.compile"
risk_tier: L1
guardrails:
  - no_canonical_without_owner
  - dreams_stay_dreams
  - temporary_never_promoted
---

# memory

Outside results (web, Hermes, Maton, pasted files) are stored as fuzzy and only One2lv can mark a fact stable.
