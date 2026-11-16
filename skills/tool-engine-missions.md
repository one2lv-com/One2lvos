---
name: tool-engine-missions
version: 1.0.0
description: "Open missions, post updates, save charts, export files into the artifact store, pull or roll back the SF Compute catalog."
triggers:
  - "open a mission"
  - "save a chart"
  - "export the file"
tools:
  - "local.open_mission"
  - "local.post_update"
  - "local.finish_mission"
  - "local.save_chart"
  - "local.export_file"
  - "engine.learn"
  - "engine.rollback_catalog"
  - "local.delete_chart"
risk_tier: L3
guardrails:
  - two_step_confirm
  - export_roots_only
---

# tool-engine-missions

Everything here runs at L1 except delete_chart, which is L3 and needs a second confirmation.
