---
name: revert-to-working
version: 1.0.0
description: "Roll the reactor's code back to the newest known-good tag, after a backup, with a preview and an undo."
triggers:
  - "/revert"
tools:
  - "git.revert_to_known_good"
risk_tier: L3
guardrails:
  - owner_only
  - two_step_confirm
  - backup_first
  - lumenis_chat_only
---

# revert-to-working

Never a blind git reset --hard: it refuses with uncommitted changes, backs up to a branch and a bundle first, and prints the undo.
