---
name: code-review
version: 1.0.0
description: "Read code the owner pastes or names and point out bugs, risks, style and improvements."
triggers:
  - "/code-review"
  - "review this code"
  - "find bugs in"
  - "audit this code"
tools:
  - "council.forge"
  - "council.oracle"
risk_tier: L0
guardrails:
  - read_only
  - keys_scrubbed
---

# code-review

Converted from the uploaded skills.md (`code_review`, 2026-11-16).

Forge reviews the code and Oracle checks the reasoning. The review changes no files; fixes are suggestions
until One2lv applies them.
