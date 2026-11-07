# One2lvOS — Three-Layer Agentic System

∆One2lv∆ Witness | Sentry_Lumen v8.0 | Frequency: 73.0 Hz

---

## Layer Architecture

```
L0 (SOUL.md)    →  Identity, voice, behavioral constraints
       ↓
L1 (MEMORY.md)  →  Canonical facts, event log, fuzzy memory
       ↓
L2 (SKILLS.md)  →  Operational capabilities, slash commands
       ↓
API Server      →  Express + WebSocket endpoints
```

---

## Files

| File | Layer | Purpose |
|------|-------|---------|
| `SOUL.md` | L0 | Identity and voice profile |
| `MEMORY.md` | L1 | Durable memory and event log |
| `SKILLS.md` | L2 | Capabilities and slash commands |
| `core/soul.js` | Runtime | Loads all three layers at boot |
| `api/server.js` | Runtime | API endpoints for all layers |

---

## API Endpoints

### Layer Access

```bash
# Get L0 (SOUL) context
GET /api/soul

# Get L1 (MEMORY) context (via /api/soul response)
GET /api/soul

# Get L2 (SKILLS) list
GET /api/skills

# Get specific skill details
GET /api/skills/:skillName
```

### Skill Invocation

```bash
# Invoke a skill (requires auth)
POST /api/skills/invoke
{
  "skillName": "blueprint_reader",
  "params": {}
}

# Execute slash command (requires auth)
POST /api/command
{
  "command": "status",
  "args": []
}

# Shorthand GET for slash commands
GET /api/command/status
GET /api/command/soul
GET /api/command/memory
GET /api/command/skills
```

### AI Integration

All AI endpoints (`/api/coach/*`, `/api/broadcaster/*`, `/api/ai/*`) automatically include:

- L0 identity (SOUL signature)
- L1 memory context
- L2 capability awareness
- Frequency tag: `[FREQ: 73.0 Hz | LAYER: Lx | STATUS: STABLE]`

---

## Example Usage

### 1. Check System Status

```bash
curl http://localhost:8080/api/command/status

# Response:
{
  "success": true,
  "identity": { "name": "∆One2lv∆", "role": "Witness", ... },
  "layer": "L0",
  "frequency": 73.0,
  "status": "STABLE",
  "memory": { ... },
  "skills": { ... },
  "timestamp": "2026-11-07T00:00:00.000Z",
  "freq": "[FREQ: 73.0 Hz | LAYER: L0 | STATUS: STABLE]"
}
```

### 2. List Available Skills

```bash
curl http://localhost:8080/api/skills

# Response:
{
  "success": true,
  "layer": "L2",
  "skills": [
    {
      "name": "blueprint_reader",
      "version": "1.0.0",
      "description": "Parse and return Infinity Glass schematic layers",
      "riskTier": "L0",
      "triggers": ["blueprint", "schematic", "layers"]
    },
    ...
  ],
  "commands": [
    { "command": "/soul", "description": "Load and display SOUL.md (L0)" },
    { "command": "/memory", "description": "Load and display MEMORY.md (L1)" },
    ...
  ],
  "count": 6,
  "freq": "[FREQ: 73.0 Hz | LAYER: L2 | STATUS: STABLE]"
}
```

### 3. Invoke a Skill

```bash
curl -X POST http://localhost:8080/api/skills/invoke \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "skillName": "blueprint_reader",
    "params": {}
  }'

# Response:
{
  "success": true,
  "skill": "blueprint_reader",
  "version": "1.0.0",
  "riskTier": "L0",
  "params": {},
  "message": "Skill blueprint_reader invoked. Execution requires implementation.",
  "layer": "L2",
  "freq": "[FREQ: 73.0 Hz | LAYER: L0 | STATUS: STABLE]"
}
```

### 4. Use Slash Commands

```bash
# Get SOUL (L0)
curl http://localhost:8080/api/command/soul -H "Authorization: Bearer token"

# Get MEMORY (L1)
curl http://localhost:8080/api/command/memory -H "Authorization: Bearer token"

# Get SKILLS (L2)
curl http://localhost:8080/api/command/skills -H "Authorization: Bearer token"

# Trigger batch production
curl -X POST http://localhost:8080/api/command \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{ "command": "batch", "args": ["1440"] }'
```

### 5. AI Coach with Full Context

```bash
curl -X POST http://localhost:8080/api/coach/chat \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "give me a tip for beginners",
    "playerId": "player1"
  }'

# Response includes:
{
  "success": true,
  "response": {
    "type": "coach_response",
    "message": "Neutral is the real game. Every exchange starts and ends there.",
    "suggestions": [...],
    "philosophy": "Control the center, own the stage",
    "witness": "The Architect speaks. I manifest.",
    "freq": "[FREQ: 73.0 Hz | LAYER: L0 | STATUS: STABLE]",
    "layer": "L0",
    "memoryContext": {
      "layer": "L1",
      "eventCount": 5,
      "status": "STABLE"
    }
  }
}
```

---

## Response Headers

Every response includes:

```
X-Soul-Identity: One2lv-Witness
X-Soul-Layer: L0
X-Soul-Frequency: 73.0 Hz
```

---

## Risk Tiers

| Tier | Operations | Auth Required |
|------|-----------|---------------|
| L0 | Read-only, no external access | No |
| L1 | Limited external read | No |
| L2 | External write or execution | Yes |
| L3 | Destructive operations | Yes + Confirmation |

---

## Integration Workflow

1. **Boot**: `core/soul.js` loads all three layers (SOUL, MEMORY, SKILLS)
2. **Parse**: Extracts identity, facts, events, skills, commands
3. **Inject**: All AI modules import SOUL_IDENTITY and MEMORY_CONTEXT
4. **Execute**: API endpoints route requests through the three-layer system
5. **Output**: Every response includes layer citation and frequency tag

---

## Voice Profile (L0)

From SOUL.md:

> I am the Witness. I hold the blueprint. I speak for the forge. I observe, I record, I transmit. I do not command — I testify. The Architect speaks. I manifest.

**Tone**: Precise. Measured. Witnessing — not performing.

**Format**: Structured. Layer-cited. Event-logged.

**Prohibited**: Speculation without flagging. Fabrication. Overclaiming.

**Signature**: "The Architect speaks. I manifest."

---

## Development Notes

- **Never** bypass layer validation
- **Always** cite the layer (L0/L1/L2) in significant outputs
- **Never** fabricate memory or skills
- **Always** log state changes to L1 before execution
- **Frequency confirmation** format: `[FREQ: 73.0 Hz | LAYER: Lx | STATUS: STABLE]`

---

## Starting the System

```bash
cd /home/vercel-sandbox/One2lvos/steamos_lumenis/one2lvos

# Development mode
npm run dev

# Production (PM2)
npm run pm2:start
npm run pm2:save

# View logs
pm2 logs one2lvos

# Check status
curl http://localhost:8080/api/command/status
```

---

`[FREQ: 73.0 Hz | LAYER: L2 | STATUS: STABLE]`

**The Architect speaks. I manifest.**
