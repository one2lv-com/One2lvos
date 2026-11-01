# tools.md — Sovereign AI Tool & Infrastructure Reference

**Version:** 1.1.0
**Last updated:** 2026-10-27 (written by Lumenis via Council)

---

## Tool Usage Rules

1. All tools are called via HTTP against `http://localhost:8000`
2. POST endpoints accept `application/json`
3. All responses are JSON
4. Lumenis may register new tools by appending to this file and calling PUT /api/tools-manifest

---

## Conflict Priority Matrix

When autonomous tasks conflict with user intents, apply this matrix:

| Priority | Type | Rule |
|---|---|---|
| 1 (highest) | Safety / governance boundary | Always enforced; never overridden |
| 2 | Active user session | User message in last 60s beats any auto-task |
| 3 | Scheduled checkpoint | Runs unless pre-empted by P1/P2 |
| 4 | Service-watch alert | Dispatched after P1-P3 complete |
| 5 (lowest) | Background self-heal | Runs only when system is idle |

*High-stakes conflicts (ambiguous, value-laden, irreversible) escalate to human via broadcast.*

---

## Infrastructure Change Authorization (GRANT)

Lumenis may execute the following infra changes autonomously (logged to compass.db):

- Restart a watched service via `POST /api/infra/change` with `action: restart`
- Add/remove a service from SERVICE-WATCHER
- Write to Soul.md, Memory.md, skills.md, tools.md
- Create/delete compass.db tables (schema management only)

Lumenis may NOT execute without human approval:
- git push to remote
- DNS changes
- Port changes on running processes
- Deleting data from compass.db (only marking inactive)

---

## 1. LLM Inference Backend

| Provider | Model | Status | Auth |
|----------|-------|--------|------|
| **AWS Bedrock** | `us.anthropic.claude-sonnet-4-6` | ✅ ACTIVE | `AWS_BEARER_TOKEN_BEDROCK` (env, network-injected) |
| NVIDIA API | `integrate.api.nvidia.com` | ❌ INACTIVE — 403 Forbidden (keys revoked) | `NVIDIA_API_KEY` (dead) |

**Rewired endpoints:**
- `POST /api/tools/nvidia/infer` → Bedrock
- Autonomous cycle (lumenis-main.py) → Bedrock
- LumenisReactor, NvidiaReactor, ReasoningReactor → all unified on Bedrock

---

## 2. Astra DB Collections

**Keyspace:** `default_keyspace` (corrected from: `one2lvOS`)
**Provider:** DataStax Astra DB

| # | Collection | Vector? | Notes |
|---|------------|---------|-------|
| 1 | `aria_memory` | maybe | Legacy memory store (v1) |
| 2 | `aria_memory_v2` | maybe | Memory store — second generation |
| 3 | `aria_memory_v3` | **yes** | Active memory R/W (current) |
| 4 | `commits` | no | Version/commit tracking |
| 5 | `conversations` | maybe | Session/thread history |
| 6 | `files` | no | File metadata and content refs |
| 7 | `messages` | maybe | Individual message units |
| 8 | `vector_memories` | **yes** | Semantic search / RAG target |

---

## 3. Active Local Services

| Port | Service | Entry Point | Runtime | Health |
|------|---------|-------------|---------|--------|
| `8000` | **Lumenis Reactor Core** | `lumenis-main.py` | uvicorn | `GET /health` |
| `8080` | **Minimax AI** | `minimax/index.js` | node | `GET /health` |
| `3002` | **Core Service** | `core_service.py` | flask | `GET /health` |
| `8888` | **Unified Gateway** | `unified_gateway.py` | uvicorn | `GET /health` |

### Service Dependency Map

```
External Clients
      │
      ▼
┌─────────────────────┐
│  Unified Gateway    │  :8888  (routing, orchestration)
└────────┬────────────┘
         ├──────────────────────┐
         ▼                      ▼
┌───────────────┐     ┌─────────────────┐
│ Lumenis Core  │     │   Minimax AI    │
│  :8000        │     │   :8080         │
│ (WS + REST)   │     │ (agent hub)     │
└───────┬───────┘     └────────┬────────┘
        └──────────┬───────────┘
                   ▼
         ┌─────────────────┐
         │  Core Service   │
         │  :3002 (Flask)  │
         └────────┬────────┘
                  ▼
         ┌─────────────────┐
         │   Astra DB      │
         │ default_keyspace│
         │  (8 collections)│
         └─────────────────┘
```

---

## Registered External Tools

<!-- entries appended by Lumenis autonomously -->
