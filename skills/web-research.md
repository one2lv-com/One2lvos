---
name: web-research
version: 1.0.0
description: "Look things up through the apps Hermes can reach (Maton bridge) and summarise the results."
triggers:
  - "/web-research"
  - "look it up online"
  - "find online"
tools:
  - "hermes.maton_bridge"
  - "council.oracle"
risk_tier: L2
guardrails:
  - keys_scrubbed
  - no_canonical_without_owner
  - raw_values
---

# web-research

Converted from the uploaded skills.md (`web_research`, 2026-11-16).

The reactor has no general web search of its own. Hermes reaches outside services through the Maton bridge
(the apps connected there), and Oracle summarises what comes back. Outside results are labelled as outside
information and never go straight into canonical memory. Tier L2 because bridge apps can include write actions.
