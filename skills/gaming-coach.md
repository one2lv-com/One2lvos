---
name: gaming-coach
version: 1.0.0
description: "Coach tips, broadcaster lines and post-match analysis from recorded matches and vision readings; sparring drills."
triggers:
  - "/coach"
  - "/match"
  - "coach me"
tools:
  - "gaming.coach"
  - "gaming.match"
  - "gaming.drill"
risk_tier: L1
guardrails:
  - vision_lag_no_live_play
  - raw_values
---

# gaming-coach

Vision runs 2 to 4 seconds behind, so the second player gives drills, not live inputs.
