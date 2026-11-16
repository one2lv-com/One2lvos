---
name: status
version: 1.0.0
description: "Live status from real checks (services, identity, keys present)."
triggers:
  - "/status"
tools:
  - "live_status.snapshot"
risk_tier: L0
guardrails:
  - owner_only
  - raw_values
  - read_only
---

# status

Guests never see system status.
