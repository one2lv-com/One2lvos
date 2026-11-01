# ⚡ Quick Start - One2lvOS

**4 commands. Works anywhere. Talk to Lumenis.**

## 🚀 Setup (30 seconds)

```bash
git clone https://github.com/one2lv-com/One2lvos.git
cd One2lvos
./setup_lumenis.sh
python3 talk-to-lumenis-direct.py
```

That's it! 🎉

## ✅ What Happens

### 1. Clone Repository
```bash
git clone https://github.com/one2lv-com/One2lvos.git
```
Downloads the complete One2lvOS system with:
- Virtual File System (VFS)
- NVIDIA API integration
- ASTRA DB memory
- Story Weaver (6 narrative modes)
- Direct Lumenis communication

### 2. Enter Directory
```bash
cd One2lvos
```
Enter the project. VFS will auto-detect this as the root.

### 3. Run Setup
```bash
./setup_lumenis.sh
```

The script automatically:
- ✅ Detects your environment (Linux/Mac/WSL/Docker)
- ✅ Checks Python 3.6+
- ✅ Installs dependencies (dotenv, requests, pynacl)
- ✅ Creates VFS directory structure
- ✅ Tests NVIDIA API connection
- ✅ Verifies everything works

Output:
```
🧠 Lumenis Reactor Core - Portable Setup
========================================

📁 Project Root: /your/path/One2lvos

✓ Python 3.9.25 found
✓ Dependencies installed
✓ .env.working found
✓ VFS initialized
✓ NVIDIA API connection successful

✅ Setup Complete!
```

### 4. Talk to Lumenis
```bash
python3 talk-to-lumenis-direct.py
```

Interactive mode starts:
```
╔══════════════════════════════════════════════════════════════╗
║        🧠 LUMENIS REACTOR - DIRECT MODE (NVIDIA API)        ║
╚══════════════════════════════════════════════════════════════╝

📡 Model: nvidia/nemotron-3.5-lightning-30b-a3b
🧠 Embedding: nvidia/nemotron-3.5-embed-1b (2048D)
💾 Memory: ASTRA DB (aria_memory)
🗂️  VFS Root: /your/path/One2lvos
💬 Conversations: 0

Commands:
  /exit    - Exit
  /config  - Show configuration
  /vfs     - Show VFS info

You > 
```

Ask Lumenis anything!

## 🧪 Verify Installation

Run automated tests:
```bash
./test_portable_setup.sh
```

Should show:
```
✅ All tests passed!
🎉 Portable setup is working perfectly!
```

## 🔧 First Time Setup

If you don't have API keys configured, you'll see:
```
⚠️ NVIDIA_API_KEY not set in .env.working
Run: python3 nvidia_api_config.py
```

### Get API Keys

**NVIDIA API Key:**
1. Visit https://build.nvidia.com
2. Sign up/login
3. Copy API key

**ASTRA DB Credentials:**
1. Visit https://astra.datastax.com
2. Create database (free tier available)
3. Get API Endpoint and Token

### Configure

Option 1 - Auto-discover (recommended):
```bash
export NVIDIA_API_KEY="your_key_here"
export ASTRA_DB_API_ENDPOINT="your_endpoint"
export ASTRA_DB_APPLICATION_TOKEN="your_token"
python3 nvidia_api_config.py
```

Option 2 - Manual:
```bash
cp env.working.template .env.working
nano .env.working  # Add your keys
```

Then re-run setup:
```bash
./setup_lumenis.sh
```

## 💬 Usage Examples

### Interactive Chat
```bash
python3 talk-to-lumenis-direct.py
```

### Single Message
```bash
python3 talk-to-lumenis-direct.py "Explain consciousness"
```

### Keep Connection Alive
```bash
nohup python3 keep_alive.py > keep_alive.log 2>&1 &
```

### Check VFS
```bash
python3 lumenis_vfs.py
```

### Auto-Configure Models
```bash
python3 nvidia_api_config.py
```

## 🗂️ What You Get

After setup, your directory structure:

```
One2lvos/
├── data/
│   ├── conversations/    # Your chats with Lumenis
│   ├── dreams/          # Generated narratives
│   └── memory/          # Additional storage
├── logs/                # System logs
├── .cache/              # Temp cache
└── .env.working         # Your API keys (gitignored)
```

## 🌐 Works On

- ✅ Linux (Ubuntu, Debian, Fedora, Arch, etc.)
- ✅ macOS (Intel & Apple Silicon)
- ✅ WSL (Windows Subsystem for Linux)
- ✅ Docker containers
- ✅ Cloud VMs (AWS, GCP, Azure, DigitalOcean, etc.)
- ✅ GitHub Actions / CI/CD
- ✅ Any system with Python 3.6+

## 📚 Learn More

| Doc | Purpose |
|-----|---------|
| `PORTABLE_SETUP.md` | Complete setup guide |
| `VFS_README.md` | Virtual File System API |
| `LUMENIS_LIVE_FIX.md` | API fixes & networking |
| `STORY_WEAVER_SUMMARY.md` | 6 narrative modes |

## 🎯 What Lumenis Can Do

- 💬 **Converse** - Direct NVIDIA API communication
- 🧠 **Remember** - ASTRA DB vector memory (2048D)
- 📖 **Dream** - 6 narrative modes (Surrealist, Horror, Sci-Fi, Mythological, Memory Reconstruction, Philosophical)
- 🗂️ **Store** - VFS for conversations, dreams, logs
- 🔄 **Self-Monitor** - Keep-alive & health checks

## ⚡ Commands Summary

```bash
# Setup
git clone https://github.com/one2lv-com/One2lvos.git
cd One2lvos
./setup_lumenis.sh

# Talk to Lumenis
python3 talk-to-lumenis-direct.py

# Test everything
./test_portable_setup.sh

# Configure models (if needed)
python3 nvidia_api_config.py

# Keep alive (optional)
nohup python3 keep_alive.py > keep_alive.log 2>&1 &

# Check VFS
python3 lumenis_vfs.py
```

## 🔗 Links

- **Repository:** https://github.com/one2lv-com/One2lvos
- **Issues:** https://github.com/one2lv-com/One2lvos/issues
- **NVIDIA API:** https://build.nvidia.com
- **ASTRA DB:** https://astra.datastax.com

---

**4 commands. Zero configuration. Universal compatibility.** 🌟

Ready to talk to Lumenis? → `python3 talk-to-lumenis-direct.py`
