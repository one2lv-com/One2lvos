---
name: sfcompute
version: 1.0.0
description: "SF Compute's MCP server: read-only calls; anything that spends money or touches secrets is refused."
triggers:
  - "sf compute"
  - "gpu prices"
tools:
  - "sfcompute.*"
risk_tier: L3
guardrails:
  - cost_limited
  - refused_tools_stay_refused
  - no_canonical_without_owner
---

# sfcompute

Remote writes stay refused unless One2lv names them in SFCOMPUTE_MCP_ALLOW_TOOLS.
