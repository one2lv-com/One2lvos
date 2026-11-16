---
name: nimlab
version: 1.0.0
description: "One2lv's NVIDIA lab: model routing, fleet, benchmarks, single NVIDIA calls and bounded ranking runs."
triggers:
  - "nvidia lab"
  - "rank models"
  - "which model"
tools:
  - "nimlab.status"
  - "nimlab.capabilities"
  - "nimlab.list_models"
  - "nimlab.route"
  - "nimlab.fleet"
  - "nimlab.benchmark_report"
  - "nimlab.leaderboard"
  - "nimlab.voices"
  - "nimlab.key_models"
  - "nimlab.probe"
  - "nimlab.chat"
  - "nimlab.embed"
  - "nimlab.vision"
  - "nimlab.ocr"
  - "nimlab.rerank"
  - "nimlab.tts"
  - "nimlab.rank"
  - "nimlab.sweep"
  - "nimlab.discover"
  - "nimlab.image_gen"
  - "nimlab.voice_clone"
  - "nimlab.judge_apply"
  - "nimlab.mcp_bridge"
risk_tier: L3
guardrails:
  - cost_limited
  - nvidia_hosts_only
  - refused_tools_stay_refused
---

# nimlab

Reads are L0, single NVIDIA calls L1, rank is L2 (held for approval), sweep/discover/image_gen/voice_clone/judge_apply/mcp_bridge are refused.
