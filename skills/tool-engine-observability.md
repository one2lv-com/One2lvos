---
name: tool-engine-observability
version: 1.0.0
description: "Read this machine's logs, metrics, call traces and audit events, and the engine's own catalog."
triggers:
  - "check the logs"
  - "machine metrics"
  - "tool calls"
tools:
  - "engine.status"
  - "engine.list"
  - "engine.describe"
  - "engine.validate"
  - "engine.catalog_versions"
  - "local.query_logs"
  - "local.query_metrics"
  - "local.search_traces"
  - "local.get_trace"
  - "local.list_audit_events"
  - "local.list_artifacts"
  - "local.get_artifact"
  - "local.list_missions"
  - "local.get_mission"
  - "local.list_updates"
risk_tier: L0
guardrails:
  - raw_values
  - read_only
  - keys_scrubbed
---

# tool-engine-observability

Tool output goes to the council raw, labelled real tool output.
