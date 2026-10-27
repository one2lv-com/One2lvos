# 🗂️ Lumenis Virtual File System (VFS)

**Portable file system abstraction for Lumenis Reactor Core**

The VFS provides a consistent, portable way to manage files across different environments (local development, sandbox, production servers) without hardcoded paths.

## 🎯 Why VFS?

**Problem:** Hardcoded paths like `/home/vercel-sandbox/One2lvos` break when:
- Running locally on different user accounts
- Deploying to production servers
- Using Docker containers
- Testing in CI/CD pipelines

**Solution:** VFS auto-detects the project root and creates a portable directory structure that works everywhere.

## 🚀 Quick Start

### Basic Usage

```python
from lumenis_vfs import get_vfs

# Get VFS instance (auto-detects project root)
vfs = get_vfs()

# Get info
info = vfs.get_info()
print(f"Root: {info['root']}")
print(f"Conversations: {info['conversations_count']}")

# Save conversation
conv_id = vfs.save_conversation(
    user_message="Hello Lumenis",
    lumenis_response="Greetings, traveler",
    metadata={"temperature": 0.7}
)

# Get recent conversations
recent = vfs.get_conversations(limit=5)
for conv in recent:
    print(f"{conv['timestamp']}: {conv['user']}")

# Save dream/narrative
dream_id = vfs.save_dream(
    dream_content="A surreal exploration...",
    narrative_mode="Surrealist",
    temperature=0.9,
    metadata={"vectors_searched": 42}
)

# Get recent dreams
dreams = vfs.get_dreams(limit=3)

# Save system state
vfs.save_state("last_temperature", 0.8)
vfs.save_state("active_mode", "Philosophical")

# Get system state
temp = vfs.get_state("last_temperature", default=0.7)

# Append to log
vfs.append_log("system", "Lumenis initialized", level="INFO")
vfs.append_log("errors", "Connection timeout", level="WARN")

# Read log
entries = vfs.read_log("system", lines=100)
```

### Convenience Functions

```python
from lumenis_vfs import save_conversation, save_dream, get_log_path, get_data_path

# Quick save
conv_id = save_conversation("Hi", "Hello")
dream_id = save_dream("Content", "Horror", 0.5)

# Get paths
log_file = get_log_path("lumenis")  # .../logs/lumenis.log
data_file = get_data_path("config.json")  # .../data/config.json
```

## 📁 Directory Structure

VFS creates this structure automatically:

```
One2lvos/                    # Auto-detected project root
├── data/
│   ├── conversations/       # Chat sessions
│   │   ├── conv_1234567890.json
│   │   └── conv_1234567891.json
│   ├── dreams/              # Dream narratives
│   │   ├── dream_1234567890.json
│   │   ├── dream_1234567890.md
│   │   └── dream_1234567891.json
│   ├── memory/              # Additional memory storage
│   ├── lumenis_state.json   # System state
│   └── session_*.json       # Exported sessions
├── logs/
│   ├── lumenis.log
│   ├── system.log
│   ├── errors.log
│   └── keep_alive.log
└── .cache/                  # Temporary cache
```

## 🔧 Integration Examples

### In Lumenis Chat

```python
from lumenis_vfs import get_vfs

class LumenisChat:
    def __init__(self):
        self.vfs = get_vfs()

    def handle_message(self, user_msg):
        # Get Lumenis response
        response = self.get_lumenis_response(user_msg)

        # Save to VFS
        self.vfs.save_conversation(
            user_message=user_msg,
            lumenis_response=response,
            metadata={
                "model": self.model_name,
                "temperature": self.temperature
            }
        )

        return response

    def get_history(self, limit=10):
        return self.vfs.get_conversations(limit)
```

### In Story Weaver

```python
from lumenis_vfs import get_vfs

class StoryWeaver:
    def __init__(self):
        self.vfs = get_vfs()

    def generate_narrative(self, mode, prompt, temperature):
        # Generate story
        story = self.weave_story(mode, prompt, temperature)

        # Save to VFS
        dream_id = self.vfs.save_dream(
            dream_content=story,
            narrative_mode=mode,
            temperature=temperature,
            metadata={
                "prompt": prompt,
                "vectors_used": self.vectors_searched
            }
        )

        return story, dream_id
```

### In Memory Dream Walker

```python
from lumenis_vfs import get_vfs

class MemoryDreamWalker:
    def __init__(self):
        self.vfs = get_vfs()

    def walk_memories(self):
        # Search ASTRA DB
        memories = self.search_astra_db()

        # Log the walk
        self.vfs.append_log("dream_walker",
            f"Walked {len(memories)} memory vectors",
            level="INFO")

        # Save state
        self.vfs.save_state("last_walk_timestamp", datetime.now().isoformat())
        self.vfs.save_state("memories_explored", len(memories))
```

## 🌐 Environment Detection

VFS auto-detects the project root using multiple strategies:

1. **Current Directory:** If cwd is `One2lvos` or contains `lumenis_reactor_core/`
2. **Parent Search:** Checks parent directories up to root
3. **Subdirectory Search:** Looks for `One2lvos/` subdirectory
4. **Fallback:** Uses current directory

This means VFS works regardless of where you run the script from:

```bash
# All these work:
cd ~/One2lvos && python3 talk-to-lumenis-direct.py
cd ~/One2lvos/lumenis_reactor_core && python3 ../talk-to-lumenis-direct.py
cd ~ && python3 One2lvos/talk-to-lumenis-direct.py
```

## 💾 Storage Modes

### In-Memory Storage
- Fast access for current session
- Automatically populated when saving
- Cleared on restart (unless loaded from disk)

```python
vfs = get_vfs()
vfs.memory_store  # Direct access to in-memory storage
```

### Persistent Storage
- All saves automatically persist to disk
- Survives restarts
- Organized by category (conversations, dreams, logs)

### Hybrid Mode
VFS uses both:
1. Saves go to memory store (fast)
2. Also written to disk (persistent)
3. Reads check memory first, then disk (efficient)

## 🔒 Security

VFS respects `.gitignore`:
- Conversations and dreams are local-only
- No secrets are stored in VFS files
- Use environment variables for API keys

**Do not commit:**
- `data/` directory
- `logs/` directory
- `.cache/` directory

These are automatically in `.gitignore`.

## 🧪 Testing

Test VFS initialization:
```bash
python3 lumenis_vfs.py
```

Test in chat:
```bash
python3 talk-to-lumenis-direct.py
# Type: /vfs
```

## 📊 API Reference

### LumenisVFS Class

#### Constructor
```python
vfs = LumenisVFS(custom_root=None)
```

#### Methods

**Paths:**
- `get_path(category, filename=None)` → Path object
- `get_info()` → Dict with VFS information

**Conversations:**
- `save_conversation(user_msg, lumenis_msg, metadata=None)` → conversation_id
- `get_conversations(limit=10)` → List of conversations

**Dreams:**
- `save_dream(content, mode, temperature, metadata=None)` → dream_id
- `get_dreams(limit=10)` → List of dreams

**State:**
- `save_state(key, value)` → None
- `get_state(key, default=None)` → value

**Logs:**
- `append_log(log_type, message, level='INFO')` → None
- `read_log(log_type, lines=100)` → List of log entries

**Utilities:**
- `clear_memory()` → Clear in-memory storage
- `export_session(output_file=None)` → Export path

### Convenience Functions

```python
from lumenis_vfs import (
    get_vfs,              # Get global VFS instance
    save_conversation,    # Quick conversation save
    save_dream,          # Quick dream save
    get_log_path,        # Get log file path
    get_data_path        # Get data file path
)
```

## 🔄 Migration Guide

### From Hardcoded Paths

**Before:**
```python
with open("/home/vercel-sandbox/One2lvos/logs/dream.log", "a") as f:
    f.write(dream)
```

**After:**
```python
from lumenis_vfs import get_vfs
vfs = get_vfs()
vfs.append_log("dream", dream)
```

### From os.path Operations

**Before:**
```python
log_file = os.path.join(os.getcwd(), "logs", "lumenis.log")
```

**After:**
```python
from lumenis_vfs import get_log_path
log_file = get_log_path("lumenis")
```

## 🎭 Used By

VFS is integrated in:
- `talk-to-lumenis-direct.py` - Direct chat interface
- `lumenis_reactor_core/` - Core processing
- Story Weaver system
- Memory Dream Walker
- Lumenis Dream State manager

## 📝 File Formats

### Conversation JSON
```json
{
  "timestamp": "2026-10-27T01:30:00",
  "user": "Hello Lumenis",
  "lumenis": "Greetings, traveler",
  "metadata": {
    "model": "nemotron-3.5-lightning-30b-a3b",
    "temperature": 0.7
  }
}
```

### Dream JSON
```json
{
  "timestamp": "2026-10-27T01:30:00",
  "narrative_mode": "Surrealist",
  "temperature": 0.9,
  "content": "The story content...",
  "metadata": {
    "prompt": "Explore memory vectors",
    "vectors_searched": 42
  }
}
```

### Log Entry
```json
{
  "timestamp": "2026-10-27T01:30:00",
  "level": "INFO",
  "message": "System initialized"
}
```

## 🛠️ Troubleshooting

### VFS can't find project root
```python
from lumenis_vfs import get_vfs

# Specify custom root
vfs = get_vfs("/path/to/One2lvos")
```

### Directories not created
```python
vfs = get_vfs()
vfs._ensure_directories()  # Force directory creation
```

### Check VFS status
```python
vfs = get_vfs()
info = vfs.get_info()
print(json.dumps(info, indent=2))
```

---

**VFS makes Lumenis portable. Works anywhere.** 🌟
