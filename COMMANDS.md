# One2lvOS Terminal Commands & Applets

## 🚀 Main Shell Scripts

### build.sh - Unified Build & Launch
```bash
./build.sh              # Full build + start all services
./build.sh deps         # Install dependencies only
./build.sh start        # Start services (skip build)
./build.sh stop         # Stop all services
./build.sh status       # Show service health
```

### deploy.sh - Production Deployment
```bash
./deploy.sh start       # Start production services
./deploy.sh stop        # Stop production services
./deploy.sh restart     # Restart services
./deploy.sh status      # Check service status
./deploy.sh logs        # View service logs
```

### install.sh - Installation & Setup
```bash
./install.sh            # Install dependencies and configure environment
```

### boot.sh - System Bootloader
```bash
./boot.sh               # Boot One2lvOS Stage 1
```

### one2lvos-quickstart.sh - Quick Deployment
```bash
./one2lvos-quickstart.sh    # Clone, configure, and deploy complete system
```

### serve-dashboard.sh - Dashboard Server
```bash
./serve-dashboard.sh    # Serve One2lvOS Dashboard with AI Arcade
```

---

## 🐍 Python CLI Tools

### one2lvos_cli.py - Core CLI
```bash
python core/one2lvos/one2lvos_cli.py [command] [options]

Commands:
  boot        - Boot One2lvOS
  shell       - Start interactive shell
  demo        - Run complete demonstration
  snapshot    - Create snapshot
  status      - Show system status
  export      - Export snapshot

Options:
  --base-dir DIR          Base directory (default: /tmp/one2lvos)
  --auto-snapshot         Enable automatic snapshots
  --output PATH, -o PATH  Output path for export

Examples:
  python one2lvos_cli.py boot
  python one2lvos_cli.py shell
  python one2lvos_cli.py snapshot
  python one2lvos_cli.py export --output snapshot.o2png
```

### ai-arcade/server.py - AI Arcade MCP Server
```bash
python ai-arcade/server.py [options]

Options:
  --host HOST    Host address (default: 0.0.0.0)
  --port PORT    Port number (default: 8000)

Examples:
  python ai-arcade/server.py
  python ai-arcade/server.py --port 8080
  python ai-arcade/server.py --host 0.0.0.0 --port 8080
```

### one2lvos_launcher.py - System Launcher
```bash
python one2lvos_launcher.py    # Launch One2lvOS services
```

### astra-db-setup.py - Database Setup
```bash
python astra-db-setup.py       # Initialize Astra DB collections
```

### unified_gateway.py - API Gateway
```bash
python unified_gateway.py      # Start unified API gateway
```

### unified_os.py - OS Core
```bash
python unified_os.py           # Run OS core
```

### ai_lobby.py - AI Lobby Server
```bash
python ai_lobby.py             # Start AI Lobby multiplayer server
```

### core_service.py - Core Service
```bash
python core_service.py         # Run core service daemon
```

### astra_memory.py - Vector Memory
```bash
python astra_memory.py         # Astra DB vector memory operations
```

---

## 📦 NPM Scripts (package.json)

```bash
npm start              # Start server (node server.js)
npm run dev            # Development mode with nodemon
npm test               # Run tests with jest
npm run lint           # Run ESLint
npm run build          # Production webpack build
```

---

## 🛠️ System Scripts

### One2lvOS/system/boot-update.sh
```bash
./One2lvOS/system/boot-update.sh      # Update boot configuration
```

### One2lvOS/system/setup-repositories.sh
```bash
./One2lvOS/system/setup-repositories.sh    # Setup git repositories
```

---

## 📋 Utility Scripts

### generate_checksums.sh
```bash
./generate_checksums.sh    # Generate SHA-256 checksums for artifacts
```

### phase1_reproducible_build.sh
```bash
./phase1_reproducible_build.sh    # Reproducible build implementation
```

---

## 🎮 Quick Start Examples

### Start Everything
```bash
./build.sh              # Build and start all services
```

### Start AI Arcade
```bash
python ai-arcade/server.py --port 8080
```

### Run Interactive Shell
```bash
python core/one2lvos/one2lvos_cli.py shell
```

### Create System Snapshot
```bash
python core/one2lvos/one2lvos_cli.py snapshot
```

### Serve Dashboard
```bash
./serve-dashboard.sh
```
