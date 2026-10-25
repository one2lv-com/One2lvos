# One2lvOS Offline Setup Guide

## 🚨 Environment Constraints

Your environment has the following limitations:
- ❌ No internet access for pip install / npm install
- ❌ Cannot install packages from PyPI or npm registry
- ✅ Python 3.9.25 with pre-installed packages available
- ✅ Node.js v24.14.1 with built-in modules available

## ✅ Available Python Packages

```python
✓ fastapi
✓ uvicorn
✓ aiohttp      # Can replace httpx
✓ openai
✓ sqlite3      # Built-in
✓ asyncio      # Built-in
✓ json         # Built-in
✓ dataclasses  # Built-in
```

## ❌ Missing Package: httpx

The original `lumenis_reactor_core/reactor.py` uses `httpx` for async HTTP streaming, but **httpx is not installed**.

**Solution**: I've created `reactor_aiohttp.py` that uses `aiohttp` instead (which IS installed).

---

## 🎯 Three Options to Run One2lvOS

### Option 1: Self-Contained Interactive Demo (NO SERVER NEEDED) ⭐ EASIEST

**File**: `demo-standalone.html`

**Features**:
- Opens directly in any browser
- No server required
- No network access needed
- Interactive UI with simulated responses
- Demonstrates the full interface

**How to Use**:
```bash
# Method 1: Open in browser directly
open demo-standalone.html

# Method 2: Use Python's built-in server
cd /home/vercel-sandbox/One2lvos
python3 -m http.server 8080
# Then visit: http://localhost:8080/demo-standalone.html
```

**Best For**:
- Quick UI preview
- Testing the interface design
- Offline demonstration
- No AI connectivity needed

---

### Option 2: Standalone Node.js Server (Built-in Modules Only)

**File**: `standalone-server.js`

**Features**:
- Uses ONLY Node.js built-in modules (http, fs, path)
- No npm packages required
- Serves static files
- Proxies to Python backend
- Embedded fallback demo

**How to Use**:
```bash
cd /home/vercel-sandbox/One2lvos

# Start the server
node standalone-server.js

# Access at:
# http://localhost:9000
```

**Best For**:
- Running without npm dependencies
- Offline development
- Testing backend integration
- Production-like environment

---

### Option 3: Full System with Modified Reactor (aiohttp)

**Files**:
- `lumenis-main.py` (needs modification)
- `lumenis_reactor_core/reactor_aiohttp.py` (new)

**Features**:
- Full AI-powered responses (requires NVIDIA API key + internet)
- Uses aiohttp instead of httpx
- Real Lumenis Reactor Core
- ITT Council with 7 specialized agents
- SQLite-based Flux Compass memory

**Setup Steps**:

1. **Modify lumenis-main.py to use aiohttp reactor**:
```python
# Change line 21 from:
from lumenis_reactor_core import LumenisReactor, NvidiaReactor, ...

# To:
from lumenis_reactor_core.reactor_aiohttp import LumenisReactor, NvidiaReactor
from lumenis_reactor_core import FluxCompass, ITTCouncil, MatonBridge, VanguardNodePool
```

2. **Start the system**:
```bash
cd /home/vercel-sandbox/One2lvos

# Terminal 1: Start Python backend
python3 lumenis-main.py

# Terminal 2: Start Node.js gateway
node standalone-server.js
```

3. **Access**:
```
Frontend UI:     http://localhost:9000
Backend API:     http://localhost:3002
API Docs:        http://localhost:3002/docs
```

**Best For**:
- Full AI capabilities (requires internet for NVIDIA API)
- Real memory persistence
- Production deployment
- Complete feature set

---

## 🔧 Quick Fix for httpx Issue

If you want to use the existing code, here's the minimal change needed:

### Replace httpx with aiohttp in reactor.py:

```python
# OLD (line 21):
import httpx

# NEW:
import aiohttp

# OLD (lines 111-130):
async with httpx.AsyncClient(timeout=120) as client:
    async with client.stream("POST", NVIDIA_API_URL, headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            # process lines

# NEW:
timeout = aiohttp.ClientTimeout(total=120)
async with aiohttp.ClientSession(timeout=timeout) as session:
    async with session.post(NVIDIA_API_URL, headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.content:
            line_str = line.decode('utf-8').strip()
            # process line_str
```

---

## 📊 Comparison Table

| Feature | Option 1<br/>(demo-standalone.html) | Option 2<br/>(standalone-server.js) | Option 3<br/>(Full System) |
|---------|-------------------------------------|-------------------------------------|----------------------------|
| **Setup Time** | < 1 min | < 2 min | 5-10 min |
| **Dependencies** | None | Node.js only | Python + Node.js |
| **Internet Required** | No | No | Yes (for AI) |
| **AI Responses** | Simulated | No (unless backend running) | Real (NVIDIA) |
| **Memory Persistence** | No | No | Yes (SQLite) |
| **Server Needed** | No | Yes | Yes (2 servers) |
| **Best Use** | Quick preview | Dev environment | Production |

---

## 🚀 Recommended Workflow

### For Quick Testing:
```bash
# Just open in browser
open demo-standalone.html
```

### For Development:
```bash
# Use standalone server
node standalone-server.js
# Visit http://localhost:9000
```

### For Full Features (with internet):
```bash
# Terminal 1
python3 lumenis-main.py

# Terminal 2
node standalone-server.js
```

---

## 🐛 Troubleshooting

### "Module 'httpx' not found"
✅ **Solution**: Use `reactor_aiohttp.py` instead of `reactor.py`

### "Cannot install packages"
✅ **Solution**: Use Option 1 or Option 2 (no installation needed)

### "Port already in use"
```bash
# Find process using port
lsof -i :9000  # or :3002

# Kill process
kill -9 <PID>
```

### "Python backend not responding"
```bash
# Check if it's running
ps aux | grep python | grep lumenis

# Check logs
tail -f logs/lumenis-reactor.log
```

---

## 📁 Files Created for You

```
/home/vercel-sandbox/One2lvos/
├── demo-standalone.html                    # Option 1: Self-contained demo
├── standalone-server.js                    # Option 2: Node.js server (built-ins only)
├── lumenis_reactor_core/
│   └── reactor_aiohttp.py                 # Option 3: aiohttp version
├── system-status.sh                        # Check system health
├── start-one2lvos.sh                       # Auto-start script
├── stop-one2lvos.sh                        # Shutdown script
├── OFFLINE_SETUP_GUIDE.md                  # This file
├── ISSUES_RESOLVED.md                      # Environment analysis
└── ENVIRONMENT_STATUS.md                   # Detailed status
```

---

## 🎯 Next Steps

### 1. Try the Demo First
```bash
open demo-standalone.html
```

### 2. Start Standalone Server
```bash
node standalone-server.js
```

### 3. (Optional) Set Up Full System
```bash
# Modify lumenis-main.py to use reactor_aiohttp
# Then start both servers
```

---

## 💡 Key Takeaways

1. **httpx is missing** but **aiohttp is available** ✅
2. **No npm/pip install works** but **built-in modules work** ✅
3. **Three options provided** from simplest to most powerful ✅
4. **demo-standalone.html** requires nothing (open in browser) ⭐
5. **standalone-server.js** uses only Node.js built-ins ⭐

---

## 🆘 Need Help?

Check the status anytime:
```bash
cd /home/vercel-sandbox/One2lvos
./system-status.sh
```

View this guide:
```bash
cat OFFLINE_SETUP_GUIDE.md
```

---

**🌷 One2lvOS - Sovereign Agentic Core**
*Designed to run anywhere, even offline*
