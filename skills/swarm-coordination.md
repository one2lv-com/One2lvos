---
name: swarm-coordination
version: 1.0.0
description: "Split a multi-part chat message into independent parts and let the council seats answer them in parallel."
triggers:
  - "/swarm-coordination"
  - "in parallel"
  - "swarm"
  - "several tasks at once"
tools:
  - "council.swarm"
  - "council.oracle"
  - "council.forge"
risk_tier: L0
guardrails:
  - read_only
  - seats_attributed
  - keys_scrubbed
---

# swarm-coordination

Converted from the uploaded skills.md (`swarm_coordination`, 2026-11-16). Code:
lumenis_reactor_core/swarm/council_swarm.py, wired into the council's chat path (itt.py).

- Runs automatically in lumenis-chat; LUMENIS_SWARM=0 turns it off.
- Short or single-ask messages skip it and take the fast path.
- Longer messages are split by the routing model while Sentinel and Navigator run, so splitting adds no wait.
- Two or more parts: each goes to its seat (Oracle, Forge, Weaver, Architect) at the same time, each with
  its own model and time limit; the reply lists each part under the seat and model that wrote it.
- Messages that need tools, memory, dreams, identity or system status keep the full council path.
- No sub-agents are spawned as processes; the parts are concurrent model calls.
