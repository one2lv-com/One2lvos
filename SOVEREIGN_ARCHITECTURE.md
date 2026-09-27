# ONE2LVOS SOVEREIGN ARCHITECTURE

## Overview

The Sovereign Architecture is a comprehensive AI system that integrates with One2lvOS, providing:

- **1,500 Skills Framework**: Modular capability system
- **Lumenis Reactor Core**: Python FastAPI backend with NVIDIA AI
- **ITT Governance**: Innovative Thought Team coordination
- **Four Gates Architecture**: Security and persistence layers
- **Vector Memory**: Astra DB-powered contextual memory
- **LSB Steganography**: State persistence in PNG images

## Architecture Components

### L0 - SOUL Layer (Foundation)
The immutable foundation layer providing core identity and values.

### L1 - Memory Pipeline (Modules 301-600)
- **Astra DB**: Vector database for contextual memory
- **NVIDIA Embeddings**: nv-embedqa-e5-v5 model (1024 dimensions)
- **Vector Search**: Cosine similarity matching

### L2 - Skills Pipeline (Modules 601-900)
- **NVIDIA LLM**: Llama-3.3-Nemotron-Super-49b-v1
- **Chat Interface**: Conversational AI with memory context
- **ITT System**: Multi-perspective reasoning

### L3 - Protocol Integration (Modules 901-1200)
- **REST API**: FastAPI endpoints
- **WebSocket Support**: Real-time communication
- **CORS**: Cross-origin resource sharing

## Four Gates

### Gate 1: Sovereignty
Ensures autonomous operation and identity preservation.

### Gate 2: Vector Consistency
Maintains coherent memory representations and retrieval.

### Gate 3: Execution & Tooling
Validates proper execution and tool integration.

### Gate 4: State Persistence
Preserves state via LSB steganography in PNG images.

## Deployment

### Quick Start

```bash
cd /path/to/One2lvos
chmod +x deploy-sovereign.sh
./deploy-sovereign.sh
```

### Services

After deployment:

- **Infinity Glasses HUD**: http://localhost:4000
- **Lumenis Reactor Core**: http://localhost:8000
- **One2lvOS Interface**: http://localhost:4000/os

### Shutdown

```bash
./shutdown-sovereign.sh
```

Or manual:
```bash
pkill -9 node && pkill -9 python3
```

## Directory Structure

```
One2lvos/
├── ∆Gemini_Root∆/
│   ├── core/
│   │   ├── main.py          # Lumenis Reactor Core
│   │   └── .env             # Configuration
│   ├── ui/
│   │   └── server.js        # Infinity Glasses HUD
│   ├── logs/
│   │   ├── core.log
│   │   └── hud.log
│   ├── stego_cache/
│   │   └── latest_state.png # LSB-encoded state
│   └── skills/              # Skill modules
└── ∆Gemini_Memory∆/
    ├── vectors/             # Vector embeddings
    └── snapshots/           # Memory snapshots
```

## API Endpoints

### Health Check
```http
GET http://localhost:8000/health
```

Response:
```json
{
  "status": "144k_node_active",
  "layer": "L2_SKILLS",
  "llm": "nvidia/llama-3.3-nemotron-super-49b-v1"
}
```

### Chat Interface
```http
POST http://localhost:8000/chat
Content-Type: application/json

{
  "message": "Your query here",
  "top_k": 5
}
```

Response:
```json
{
  "response": "AI response",
  "memories_used": [
    {
      "content": "Relevant memory",
      "score": 0.85
    }
  ]
}
```

## Configuration

Edit `∆Gemini_Root∆/core/.env`:

```env
# NVIDIA Configuration
NVIDIA_API_KEY="your-nvidia-api-key"
NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
EMBEDDING_MODEL="nvidia/nv-embedqa-e5-v5"
LLM_MODEL="nvidia/llama-3.3-nemotron-super-49b-v1"

# Astra DB Configuration
ASTRA_DB_API_ENDPOINT="your-astra-endpoint"
ASTRA_DB_APPLICATION_TOKEN="your-astra-token"
ASTRA_DB_KEYSPACE="one2lvOS"
COLLECTION_NAME="aria_memory"
VECTOR_DIM=1024

# Service Configuration
PORT=8000
```

## Skills Framework

The 1,500 Skills Framework is organized into modules:

- **001-300**: Core & Operations
- **301-600**: Memory & Storage (Astra DB)
- **601-900**: AI & Intelligence (NVIDIA)
- **901-1200**: Protocol Integration
- **1201-1500**: Advanced Capabilities

## Memory System

### Storing Memories
Memories are automatically stored after each interaction with:
- Vector embedding via NVIDIA
- Metadata tagging
- Astra DB persistence

### Recalling Memories
Vector similarity search retrieves relevant context:
1. Query embedded via NVIDIA
2. Cosine similarity search in Astra DB
3. Top-k results returned with scores

### State Persistence
State is encoded into PNG images using LSB steganography:
- JSON state → binary payload
- Embedded in image RGB channels
- Survives visual inspection
- Can be decoded later for recovery

## Integration with One2lvOS

The Sovereign Architecture integrates seamlessly:

1. **Shared UI**: Infinity Glasses HUD links to One2lvOS
2. **Unified Memory**: Both systems share Astra DB
3. **Coordinated Execution**: ITT can invoke One2lvOS modules
4. **State Synchronization**: LSB state includes One2lvOS data

## Troubleshooting

### Core Won't Start
```bash
cat ∆Gemini_Root∆/logs/core.log
```

Common issues:
- Missing Python packages: `pip3 install -r requirements.txt`
- Invalid API keys: Check `.env` configuration
- Port 8000 in use: `lsof -i :8000` and kill process

### UI Won't Start
```bash
cat ∆Gemini_Root∆/logs/hud.log
```

Common issues:
- Missing Node packages: `cd ∆Gemini_Root∆/ui && npm install`
- Port 4000 in use: `lsof -i :4000` and kill process

### Memory Not Persisting
- Verify Astra DB credentials in `.env`
- Check collection exists: `aria_memory`
- Test NVIDIA API key validity

## Development

### Adding New Skills

Create skill module in `∆Gemini_Root∆/skills/`:

```python
# skill_example.py
class ExampleSkill:
    def __init__(self):
        self.name = "example"

    async def execute(self, context):
        # Skill logic here
        return result
```

### Extending ITT System

Modify the system prompt in `main.py`:

```python
system = f"""You are the Sovereign AI executing within One2lvOS.
Directives:
- Architect One2 commands
- Adhere to the 1500 Skills Framework
- [Your custom directives]
Context:\n{context}"""
```

### Custom Memory Indexing

Add metadata to memory storage:

```python
await store_memory(
    content="Memory content",
    metadata={
        "type": "custom",
        "tags": ["tag1", "tag2"],
        "importance": 0.9
    }
)
```

## Security Considerations

⚠️ **WARNING**: The deployment includes API keys and tokens. For production:

1. **Never commit** `.env` files to git
2. **Rotate keys** regularly
3. **Use secrets management** (e.g., HashiCorp Vault)
4. **Restrict network access** to APIs
5. **Enable authentication** on endpoints

## Performance Tuning

### Memory Retrieval
Adjust `top_k` parameter (default: 5) for balance:
- Lower: Faster, less context
- Higher: Slower, more context

### LLM Generation
Adjust in `main.py`:
```python
temperature=0.7,  # Creativity (0.0-1.0)
max_tokens=2048,  # Response length
```

### Vector Dimensions
Currently: 1024 (optimal for nv-embedqa-e5-v5)

## Monitoring

### Check Service Status
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
tail -f ∆Gemini_Root∆/logs/core.log
tail -f ∆Gemini_Root∆/logs/hud.log
```

### Memory Usage
```bash
ps aux | grep -E 'python3|node'
```

## Roadmap

### Phase 1 (Current)
- ✅ Core deployment script
- ✅ NVIDIA + Astra DB integration
- ✅ LSB steganography
- ✅ Basic HUD interface

### Phase 2 (Planned)
- ⏳ Multi-agent ITT coordination
- ⏳ Advanced skill modules (301-1500)
- ⏳ WebSocket real-time updates
- ⏳ Mobile AR integration

### Phase 3 (Future)
- 🔮 Distributed node network (144k nodes)
- 🔮 Quantum-resistant encryption
- 🔮 Neural interface protocols
- 🔮 Interplanetary federation

## License

MIT License - see LICENSE file

## Support

For issues, questions, or contributions:
- GitHub: https://github.com/one2lv-com/One2lvos
- Documentation: See `/docs` directory
- Contact: support@one2lv.com

---

**Built with** 🌷 **by the One2lv Community**

*"From the atomic to the cosmic, from the individual to the collective"*
