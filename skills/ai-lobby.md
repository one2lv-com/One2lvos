---
name: ai-lobby
version: 1.0.0
description: "Start the AI Lobby on port 8006 or report its status; list its agents and rooms; owner-only broadcast."
triggers:
  - "/ai-lobby"
  - "ai lobby status"
  - "start the lobby"
tools:
  - "lobby.status"
  - "lobby.start"
  - "lobby.broadcast"
risk_tier: L2
guardrails:
  - owner_only_broadcast
  - local_port_only
  - honest_agent_count
---

# ai-lobby

Status is L0. Start runs startos-style launch of ai_lobby.py (L2, owner-typed command counts as approval). Broadcast is owner-only.
