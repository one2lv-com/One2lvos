---
name: shell-execution
version: 1.0.0
description: "Run a terminal command through the reactor's L0-L3 approval levels and explain the output."
triggers:
  - "/shell-execution"
  - "run this command"
  - "in the terminal"
tools:
  - "local.supervisor_cmd_l0"
  - "local.supervisor_cmd_l1"
  - "local.supervisor_cmd_l2"
  - "local.supervisor_cmd_l3"
risk_tier: L3
guardrails:
  - owner_only
  - two_step_confirm
  - no_shell_syntax
  - keys_scrubbed
---

# shell-execution

Converted from the uploaded skills.md (`shell_execution`, 2026-11-16).

Every command is classified by lumenis_reactor_core/command_tiers.py and runs without a shell, in the repo
folder:
- L0 read-only looks run at once; L1 small repo-local changes run and are logged.
- L2 (installs, service restarts, repo scripts) is held for One2lv's approval.
- L3 (rm, mv, sudo, git push/reset, pipes, redirects, anything unknown) is held and needs the second
  confirmation code.
The same path is used by Autonomis for commands its AI adviser proposes.
