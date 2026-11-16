---
name: skill-learning
version: 1.0.0
description: "Planned: let Lumenis draft a new skill file for skills/ for One2lv to approve."
triggers:
  - "/skill-learning"
  - "learn a new skill"
  - "add a skill"
tools:
  - "skills.write"
risk_tier: L2
guardrails:
  - not_built_yet
  - owner_only
  - backup_first
---

# skill-learning

Converted from the uploaded skills.md (`skill_learning`, 2026-11-16).

**Not built yet.** The reactor has no tool that writes skill files. Until one exists, new skills are added
by One2lv or by a reviewed commit, in this front-matter format; skills.load_all() validates them and refuses
any whose risk tier is lower than its tools' real tier. When built, writing a skill is L2 (held for approval)
and backs up the folder first.
