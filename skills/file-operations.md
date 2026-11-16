---
name: file-operations
version: 1.0.0
description: "List, read and search files inside the One2lvOS repo folder, and export allowed files."
triggers:
  - "/file-operations"
  - "read the file"
  - "list files in"
  - "search the files for"
tools:
  - "local.supervisor_cmd_l0"
  - "local.export_file"
risk_tier: L1
guardrails:
  - keys_scrubbed
  - export_roots_only
  - no_shell_syntax
  - owner_only
---

# file-operations

Converted from the uploaded skills.md (`file_operations`, 2026-11-16).

Reading uses the L0 command tool (`ls`, `cat`, `head`, `tail`, `grep`, `wc`, `stat`), limited to the repo
folder; secret files (.env, keys, tokens, vault) are classed L3 and refused at L0. Export uses
`local.export_file`, which reads only from its allowed folders. Writing, moving or deleting files is not part
of this skill: those are L2/L3 commands held for One2lv's approval.
