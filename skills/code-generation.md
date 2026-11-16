---
name: code-generation
version: 1.0.0
description: "Write and explain code in any language, answered by the Forge seat."
triggers:
  - "/code-generation"
  - "write code"
  - "generate a function"
  - "write a script"
tools:
  - "council.forge"
risk_tier: L0
guardrails:
  - read_only
  - keys_scrubbed
---

# code-generation

Converted from the uploaded skills.md (`code_generation`, 2026-11-16).

The council routes code requests to Forge, which answers with its own model (LUMENIS_FORGE_MODEL, default
nvidia/nemotron-3.5-lightning-30b-a3b). The upload named step-3.5-flash and kimi-k2; neither is configured in
the reactor, so they are not used. Writing code is text only: nothing is saved or run by this skill.
