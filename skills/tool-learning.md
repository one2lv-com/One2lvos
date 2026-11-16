---
name: tool-learning
version: 1.0.0
description: "Planned: let Lumenis draft a new tool implementation for tools/ for One2lv to approve."
triggers:
  - "/tool-learning"
  - "add a tool"
  - "i need a tool that"
tools:
  - "tools.write"
risk_tier: L3
guardrails:
  - not_built_yet
  - owner_only
  - two_step_confirm
  - backup_first
---

# tool-learning

Converted from the uploaded skills.md (`tool_learning`, 2026-11-16).

**Not built yet.** No reactor code writes tool implementations. New code that the reactor would run is the
highest risk tier: when built it is L3 (held, plus the second confirmation), backed up first, and tested
before it is registered with the tool engine.
