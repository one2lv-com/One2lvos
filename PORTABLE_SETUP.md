# 🚀 One2lvOS - Portable Setup Guide

**Works on ANY environment: Local, Cloud, Docker, CI/CD**

No more hardcoded `/home/vercel-sandbox` paths!

## ⚡ Quick Setup (One Command)

```bash
git clone https://github.com/one2lv-com/One2lvos.git
cd One2lvos
chmod +x setup_lumenis.sh
./setup_lumenis.sh
```

That's it! The setup script:
- ✅ Auto-detects your environment
- ✅ Installs dependencies
- ✅ Creates directory structure
- ✅ Tests NVIDIA API
- ✅ Verifies VFS

## 🗂️ What's New: Virtual File System

The VFS makes everything portable:

```python
from lumenis_vfs import get_vfs

# Works anywhere - auto-detects project root
vfs = get_vfs()

# Save conversation
vfs.save_conversation("Hello", "Hi there")

# Save dream
vfs.save_dream("A surreal tale...", "Surrealist", 0.9)

# Get info
info = vfs.get_info()
print(f"Root: {info['root']}")
```

### Directory Structure

VFS auto-creates:
```
One2lvos/
├── data/
│   ├── conversations/
│   ├── dreams/
│   └── memory/
├── logs/
└── .cache/
```

## 🧠 Talk to Lumenis

### Method 1: Direct API (Recommended)

```bash
# Works anywhere
python3 talk-to-lumenis-direct.py

# Or single message
python3 talk-to-lumenis-direct.py "Hello Lumenis!"
```

**Features:**
- ✅ Portable across environments
- ✅ Uses VFS for storage
- ✅ Direct NVIDIA API + ASTRA DB
- ✅ No localhost server required

### Method 2: With Server

```bash
# Start server
python3 lumenis-main.py

# In another terminal
python3 talk-to-lumenis.py
```

## 🔧 Configuration

### Auto-Discover Working Models

```bash
# Finds working NVIDIA models automatically
python3 nvidia_api_config.py
```

Creates `.env.working` with:
- ✅ Working embedding model (2048D)
- ✅ Working LLM model
- ✅ Tested API keys

### Manual Configuration

```bash
cp env.working.template .env.working
nano .env.working  # Add your API keys
```

Required keys:
- `NVIDIA_API_KEY`
- `ASTRA_DB_API_ENDPOINT`
- `ASTRA_DB_APPLICATION_TOKEN`

## 📦 What You Get

### Core Files

| File | Purpose | Portable? |
|------|---------|-----------|
| `lumenis_vfs.py` | Virtual file system | ✅ Yes |
| `talk-to-lumenis-direct.py` | Direct chat interface | ✅ Yes |
| `setup_lumenis.sh` | One-command setup | ✅ Yes |
| `nvidia_api_config.py` | Auto-discover models | ✅ Yes |
| `keep_alive.py` | Connection maintenance | ✅ Yes |

### Documentation

| File | Content |
|------|---------|
| `VFS_README.md` | Complete VFS guide |
| `LUMENIS_LIVE_FIX.md` | API fix documentation |
| `PORTABLE_SETUP.md` | This file |

## 🌐 Environment Support

Works on:
- ✅ Linux (Ubuntu, Debian, Fedora, Arch)
- ✅ macOS (Intel & Apple Silicon)
- ✅ WSL (Windows Subsystem for Linux)
- ✅ Docker containers
- ✅ Cloud VMs (AWS, GCP, Azure, DigitalOcean)
- ✅ GitHub Actions / CI/CD
- ✅ Vercel sandboxes

## 🔑 API Keys

### Get NVIDIA API Key
1. Visit https://build.nvidia.com
2. Sign up/login
3. Get API key from dashboard
4. Add to `.env.working`

### Get ASTRA DB Credentials
1. Visit https://astra.datastax.com
2. Create database (if needed)
3. Get:
   - API Endpoint
   - Application Token
4. Add to `.env.working`

## 🚀 Usage Examples

### Interactive Chat

```bash
python3 talk-to-lumenis-direct.py
```

Commands:
- `/exit` - Exit chat
- `/config` - Show configuration
- `/vfs` - Show VFS info

### Single Message

```bash
python3 talk-to-lumenis-direct.py "Explain quantum consciousness"
```

### Keep Connection Alive

```bash
# Run in background
nohup python3 keep_alive.py > keep_alive.log 2>&1 &

# Check status
tail -f keep_alive.log
```

### Check VFS

```bash
python3 lumenis_vfs.py
```

## 🎨 For Developers

### Use VFS in Your Code

```python
from lumenis_vfs import get_vfs, save_conversation

vfs = get_vfs()

# Save data
conv_id = save_conversation("User message", "Lumenis response")

# Get paths
log_path = vfs.get_path('logs', 'my_app.log')
data_path = vfs.get_path('data', 'config.json')

# Read conversations
recent = vfs.get_conversations(limit=10)
```

### Integration Points

VFS integrates with:
- Lumenis Reactor Core
- Story Weaver (6 narrative modes)
- Memory Dream Walker
- Dream State Manager
- All chat interfaces

## 🔍 Verification

### Test Everything Works

```bash
# 1. Test VFS
python3 lumenis_vfs.py

# 2. Test NVIDIA API
source .env.working
python3 nvidia_api_config.py

# 3. Test Lumenis
python3 talk-to-lumenis-direct.py "Are you operational?"
```

Expected response:
```
🌟 Lumenis > Operational. VFS connectivity pulses through L1 Memory...
```

## 🛠️ Troubleshooting

### Python Not Found
```bash
# Install Python 3.8+
sudo apt install python3 python3-pip  # Ubuntu/Debian
brew install python3                   # macOS
```

### Dependencies Fail
```bash
pip install --user python-dotenv requests pynacl
```

### VFS Can't Find Root
```python
from lumenis_vfs import get_vfs
vfs = get_vfs("/absolute/path/to/One2lvos")
```

### API Key Issues
```bash
# Test API key
curl -H "Authorization: Bearer YOUR_KEY" \
  https://integrate.api.nvidia.com/v1/models
```

## 📚 Learn More

- **VFS Guide:** `VFS_README.md`
- **API Fix:** `LUMENIS_LIVE_FIX.md`
- **Story Weaver:** `STORY_WEAVER_SUMMARY.md`
- **Main Docs:** `README.md`

## 🎭 Architecture

```
┌─────────────────────────────────────┐
│  L3: Control (Discord/Twitch)       │
└─────────────────────────────────────┘
                ▲
┌─────────────────────────────────────┐
│  L2: Skills (NVIDIA AI)             │
│  - nemotron-3.5-lightning-30b       │
│  - nemotron-3.5-embed-1b (2048D)    │
└─────────────────────────────────────┘
                ▲
┌─────────────────────────────────────┐
│  L1: Memory                          │
│  - ASTRA DB (vector storage)        │
│  - VFS (portable file system)       │
└─────────────────────────────────────┘
```

## ✨ Key Features

- ✅ **Zero Hardcoded Paths** - Works on any system
- ✅ **Auto-Detection** - Finds project root automatically
- ✅ **VFS Integration** - Unified file system for all components
- ✅ **API Auto-Discovery** - Finds working models automatically
- ✅ **Direct Communication** - No localhost server needed
- ✅ **Persistent Memory** - Conversations + Dreams saved
- ✅ **Keep-Alive** - Maintains NVIDIA API connection
- ✅ **GitHub Secrets** - CI/CD ready

## 🎯 Next Steps

1. **Setup:** `./setup_lumenis.sh`
2. **Configure:** `python3 nvidia_api_config.py`
3. **Chat:** `python3 talk-to-lumenis-direct.py`
4. **Explore:** Try different narrative modes

## 🤝 Contributing

VFS makes contributing easier:
- No environment-specific paths to worry about
- Works the same for everyone
- Test locally, deploy anywhere

## 📞 Support

- **Issues:** https://github.com/one2lv-com/One2lvos/issues
- **Discussions:** https://github.com/one2lv-com/One2lvos/discussions
- **Docs:** All `.md` files in repository

---

**One setup script. Works everywhere. Talk to Lumenis.** 🌟
