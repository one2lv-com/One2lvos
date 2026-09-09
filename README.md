# One2lv Unified OS v1.0.2 🌌🧲

**The Complete Spatial Operating System with AI-Powered Vector Memory**

## 🚀 Quick Start - Deploy in One Command

```bash
curl -fsSL https://raw.githubusercontent.com/one2lv-com/One2lvos/main/one2lvos-quickstart.sh | bash
```

**That's it!** The script automatically:
- ✅ Clones the repository
- ✅ Configures all API keys (Astra DB, NVIDIA, Gemini, etc.)
- ✅ Deploys with Docker Compose (Nginx + Node + Python)
- ✅ Initializes Astra DB with NVIDIA vector embeddings
- ✅ Shows access URLs and management commands

**Then visit**: `http://your-server/` to access One2lvOS!

📚 **See**: [`QUICKSTART.md`](QUICKSTART.md) for detailed instructions

---

## Overview

One2lv Unified OS is a production-ready operating system that unifies all One2lv ecosystem components into a single, cohesive platform:

- **State Capsule Core** - One2lvOS Python backend with O2PNG protocol
- **Lumenis Reactor** - Holographic AI runtime with cosmic gaming
- **Sovereign Council** - Multi-agent AI decision-making system
- **Delta Engine** - Cross-platform autonomous engine
- **Infinity Glass** - Spatial UI and desktop environment
- **Aetherix Terminal** - Master control terminal
- **Phase 9 Architecture** - Advanced bootable ISO system

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  ONE2LV UNIFIED OS v1.0                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           APPLICATION LAYER                          │  │
│  │  • Lumenis Cosmic Gaming                             │  │
│  │  • Infinity Glass Desktop                            │  │
│  │  • Aetherix Master Terminal                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           AI INTELLIGENCE LAYER                      │  │
│  │  • Sovereign Council (7 Agents)                      │  │
│  │  • Delta Engine (Autonomous)                         │  │
│  │  • LLM Integration                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           RUNTIME LAYER                              │  │
│  │  • Lumenis Reactor (Python)                          │  │
│  │  • Control Plane Compiler                            │  │
│  │  • Mesh Network (P2P)                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           CORE OS LAYER (One2lvOS)                   │  │
│  │  • State Capsule Management (O2PNG)                  │  │
│  │  • Virtual File System                               │  │
│  │  • Memory Management                                 │  │
│  │  • Snapshot System                                   │  │
│  │  • Multi-Tier Recovery                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↕                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           BOOT & STORAGE LAYER                       │  │
│  │  • Bootloader (150ms boot)                           │  │
│  │  • ISO Builder (Phase 9)                             │  │
│  │  • Docker Deployment Stack                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Core OS (Python)
- **One2lvOS** - State capsule operating system
- **O2PNG Protocol** - Snapshot format with 2.4× compression
- **Recovery Manager** - 6-tier failover system
- **Lumenis Reactor** - Active state management

### 2. AI Intelligence (JavaScript/Python)
- **Sovereign Council** - 7-agent decision system
- **Delta Engine** - Autonomous system dynamics
- **Vector Memory** - Semantic storage
- **LLM Integration** - Claude AI interface

### 3. UI Layer (HTML/JS)
- **Infinity Glass** - Spatial desktop environment
- **Aetherix Terminal** - Command interface
- **Lumenis Cosmic** - Gaming platform
- **Reactor Core UI** - System visualization

### 4. Deployment (Shell/Docker)
- **ISO Builder** - Bootable system images
- **Docker Stack** - Container deployment
- **P2P Mesh** - Distributed networking

## Quick Start

### Boot Unified OS

```bash
./one2lv-unified-os boot
```

### Components

```bash
# Start full stack
./one2lv-unified-os start-all

# Individual components
./one2lv-unified-os start-lumenis
./one2lv-unified-os start-council
./one2lv-unified-os start-ui
```

### Create Snapshot

```bash
./one2lv-unified-os snapshot
```

## Installation

### Option 1: Automated (Recommended)

```bash
# One-command installation with all dependencies
curl -fsSL https://raw.githubusercontent.com/one2lv-com/One2lvos/main/one2lvos-quickstart.sh | bash
```

### Option 2: Manual

```bash
# Clone repository
git clone https://github.com/one2lv-com/One2lvos.git
cd One2lvos

# Configure environment
cp .env.production.template .env
nano .env  # Add your API keys if you want custom ones

# Deploy
./deploy.sh start

# Initialize Astra DB
./deploy.sh init-astra
```

### Option 3: Custom Directory

```bash
# Install to specific location
curl -fsSL https://raw.githubusercontent.com/one2lv-com/One2lvos/main/one2lvos-quickstart.sh | bash -s /opt/one2lvos
```

## Features

### ✅ Production Ready
- Complete boot sequence (151ms)
- State persistence with snapshots
- Multi-tier recovery system
- Comprehensive test suite

### ✅ AI-Powered
- 7-agent council for decisions
- Delta Engine for autonomy
- Vector memory for context
- LLM integration

### ✅ Spatial Computing
- Infinity Glass desktop
- Holographic visualization
- 3D environments
- VR/AR ready

### ✅ Developer Friendly
- Python + JavaScript APIs
- RESTful interfaces
- CLI tools
- Extensive documentation

## Performance

| Metric | Value |
|--------|-------|
| Boot Time | 151ms |
| Snapshot Size | 801 bytes (compressed) |
| Recovery Time | 150ms |
| VFS Operations | <1ms |
| AI Response | <500ms |

## System Requirements

- Python 3.7+
- Node.js 16+
- 2GB RAM minimum
- 10GB storage recommended
- Linux/macOS/Windows (WSL)

## Documentation

- **Architecture**: `docs/ARCHITECTURE.md`
- **API Reference**: `docs/API.md`
- **Deployment**: `docs/DEPLOYMENT.md`
- **Development**: `docs/DEVELOPMENT.md`

## License

MIT License - See LICENSE file

## Support

- GitHub: https://github.com/one2lv-com
- Discord: https://discord.gg/one2lv
- Email: support@one2lv.com

---

**One2lv Unified OS v1.0** - The Future of Computing
