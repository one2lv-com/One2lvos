# 🌐 One2lvOS DNS Gateway & Reactor Core

## Overview

The **One2lvOS DNS Gateway** is a sovereign domain name resolution system integrated into the Reactor Core. It provides:

- **Local DNS Resolution** - `.one2lv.local` domain resolution for all services
- **Service Discovery** - Automatic registration and discovery of microservices
- **Dynamic Registration** - Register new services on-the-fly
- **HTTP API** - Full REST API for DNS operations
- **Unified Gateway** - Single entry point for all One2lvOS services

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   ONE2LVOS REACTOR CORE                      │
│                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │  DNS Gateway    │  │  Memory System   │  │ AI Engine  │ │
│  │  Port: 5353     │  │  (Astra DB)      │  │ (NVIDIA)   │ │
│  └─────────────────┘  └──────────────────┘  └────────────┘ │
│                                                               │
│  HTTP API: localhost:8000                                    │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
  reactor.one2lv.local  ui.one2lv.local   api.one2lv.local
     (Port 8000)         (Port 4000)        (Port 3002)
```

## Registered Domains

All services are accessible via `.one2lv.local` domains:

| Domain | Service | Port | Description |
|--------|---------|------|-------------|
| `reactor.one2lv.local` | Reactor Core | 8000 | Main API & DNS Gateway |
| `ui.one2lv.local` | Infinity Glasses | 4000 | HUD Interface |
| `memory.one2lv.local` | Astra Memory | 8001 | Vector Memory System |
| `ai.one2lv.local` | AI Lobby | 8787 | Neural Bridge |
| `gateway.one2lv.local` | DNS Gateway | 5353 | Service Discovery |
| `minimax.one2lv.local` | Minimax Engine | 8080 | AI Engine |
| `api.one2lv.local` | Python Core | 3002 | Backend API |
| `dashboard.one2lv.local` | Dashboard | 9000 | Control Panel |
| `bios.one2lv.local` | BIOS Recovery | 9001 | Boot System |

## Quick Start

### 1. Start Reactor Core with DNS Gateway

```bash
./start-reactor.sh
```

This will:
- Start the Reactor Core on port 8000
- Initialize DNS Gateway with all core services
- Enable AI and Memory systems
- Display all available endpoints

### 2. Use DNS CLI

```bash
# List all domains
./dns-cli.sh list

# Resolve a domain
./dns-cli.sh resolve reactor

# Register a new service
./dns-cli.sh register myapp 8888 custom

# Check gateway status
./dns-cli.sh status

# Export hosts file
./dns-cli.sh hosts
```

## API Endpoints

### DNS Gateway Operations

#### List All Domains
```bash
GET http://localhost:8000/dns/list
```

Response:
```json
{
  "success": true,
  "domains": [
    {
      "domain": "reactor.one2lv.local",
      "ip": "127.0.0.1",
      "port": 8000,
      "service": "reactor_core",
      "url": "http://127.0.0.1:8000"
    }
  ],
  "count": 9
}
```

#### Resolve a Domain
```bash
GET http://localhost:8000/dns/resolve/reactor
```

Response:
```json
{
  "success": true,
  "domain": "reactor.one2lv.local",
  "ip": "127.0.0.1",
  "port": 8000,
  "url": "http://127.0.0.1:8000",
  "service": "reactor_core"
}
```

#### Register New Service
```bash
POST http://localhost:8000/dns/register
Content-Type: application/json

{
  "name": "myservice",
  "port": 8888,
  "service_type": "custom",
  "description": "My custom service"
}
```

Response:
```json
{
  "success": true,
  "domain": "myservice.one2lv.local",
  "url": "http://127.0.0.1:8888",
  "message": "Service registered successfully"
}
```

#### DNS Gateway Status
```bash
GET http://localhost:8000/dns/status
```

Response:
```json
{
  "success": true,
  "status": {
    "status": "ONLINE",
    "host": "0.0.0.0",
    "port": 5353,
    "domain_suffix": ".one2lv.local",
    "total_domains": 9,
    "services": ["reactor_core", "infinity_glasses", "ai_lobby"]
  }
}
```

#### Export Hosts File
```bash
GET http://localhost:8000/dns/hosts
```

Returns a `/etc/hosts` compatible format for all domains.

### Service Discovery

#### List All Services
```bash
GET http://localhost:8000/services
```

Groups all domains by service type.

### AI & Memory Integration

#### Chat with AI (with Memory Recall)
```bash
POST http://localhost:8000/chat
Content-Type: application/json

{
  "message": "What services are running?",
  "top_k": 5
}
```

#### Store Memory
```bash
POST http://localhost:8000/memory/store?content=Important information&metadata={}
```

#### Recall Memory
```bash
POST http://localhost:8000/memory/recall?query=services&top_k=5
```

## Python Integration

```python
import httpx

# Resolve a domain
response = httpx.get("http://localhost:8000/dns/resolve/reactor")
domain_info = response.json()
print(f"Service URL: {domain_info['url']}")

# Register a service
httpx.post("http://localhost:8000/dns/register", json={
    "name": "worker",
    "port": 9999,
    "service_type": "worker"
})

# List all services
services = httpx.get("http://localhost:8000/services").json()
```

## JavaScript Integration

```javascript
// Resolve domain
const response = await fetch('http://localhost:8000/dns/resolve/reactor');
const domain = await response.json();
console.log(`Service: ${domain.url}`);

// Register service
await fetch('http://localhost:8000/dns/register', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    name: 'frontend',
    port: 3000,
    service_type: 'ui'
  })
});
```

## Configuration

### Environment Variables (.env)

```bash
# DNS Gateway
DNS_PORT=5353
DOMAIN_SUFFIX=.one2lv.local

# Reactor Core
PORT=8000

# Memory System
ASTRA_DB_API_ENDPOINT=https://...
ASTRA_DB_APPLICATION_TOKEN=AstraCS:...
COLLECTION_NAME=aria_memory_v2
VECTOR_DIM=2048

# AI Engine
NVIDIA_API_KEY=nvapi-...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1
```

### DNS Configuration (dns_config.json)

Edit `core/dns_config.json` to modify domain settings and routing rules.

## Advanced Usage

### Direct DNS Gateway Access

```python
from core.dns_gateway import get_dns_gateway

gateway = get_dns_gateway()

# Register domain
gateway.register_domain("test.one2lv.local", "127.0.0.1", 7777, "test")

# Resolve domain
record = gateway.resolve_domain("test")
print(f"URL: {gateway.get_service_url('test')}")

# List all domains
domains = gateway.list_domains()
```

### Export Hosts File

```bash
./dns-cli.sh hosts > /tmp/one2lv_hosts
cat /tmp/one2lv_hosts

# To use system-wide (requires root):
# sudo cat /tmp/one2lv_hosts >> /etc/hosts
```

## Troubleshooting

### Reactor Core won't start
```bash
# Check if port is in use
lsof -i :8000

# View logs
tail -f logs/reactor_core.log
```

### Domain not resolving
```bash
# Verify domain is registered
./dns-cli.sh list

# Check service is running
curl http://localhost:8000/health
```

### DNS Gateway offline
```bash
# Restart reactor core
./start-reactor.sh

# Check DNS status
./dns-cli.sh status
```

## Features

✅ **Dynamic Service Registration** - Add services without restart
✅ **Automatic Discovery** - Services auto-register on startup
✅ **Memory Integration** - AI remembers all interactions
✅ **Health Monitoring** - Real-time service status
✅ **HTTP Gateway** - REST API for all operations
✅ **Export Capabilities** - Generate hosts files
✅ **Multi-Service** - Support for unlimited services

## Next Steps

1. **Deploy to Production** - Configure external domains (`.one2lv.io`)
2. **Add SSL/TLS** - Secure all service connections
3. **Load Balancing** - Multiple instances per service
4. **Monitoring** - Integrate with observability stack
5. **Service Mesh** - Full microservices coordination

---

**Status:** ✅ OPERATIONAL
**Version:** 2.0.0
**License:** One2lv Sovereign Architecture
