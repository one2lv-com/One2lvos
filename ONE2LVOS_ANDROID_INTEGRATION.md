# One2lv OS Android - Lumenis Reactor Integration

## 🌌 Overview

The One2lv OS Android system has been integrated into the **Lumenis Reactor Core**, allowing Lumenis to control and interact with a complete Ubuntu 22.04 environment running on Android.

This integration brings the full power of the One2lv OS cyberpunk terminal into the reactor ecosystem, operating at the thermal baseline of 0.18°C (cool fire state).

---

## 📦 Components

### 1. **one2lvos_android.py** (Reactor Core Module)
Location: `lumenis_reactor_core/one2lvos_android.py`

Complete Android OS implementation with:
- Ubuntu 22.04 terminal commands (50+)
- Full root access (sudo/su)
- APT package manager
- File system operations
- Git version control
- System monitoring
- State persistence

### 2. **one2lvos_android_bridge.py** (CLI Tool)
Location: `one2lvos_android_bridge.py`

Command-line interface for interacting with the OS:
```bash
python3 one2lvos_android_bridge.py <command> [args]
```

### 3. **Updated __init__.py**
The module is now exported from the reactor core:
```python
from lumenis_reactor_core import One2lvOSAndroid, AndroidSystemState
```

---

## 🚀 Usage

### Basic Commands

#### Get System Status
```bash
python3 one2lvos_android_bridge.py status
```
Output:
```
╔══════════════════════════════════════════════════════════╗
║        ONE2LV OS ANDROID - SYSTEM STATUS                 ║
╚══════════════════════════════════════════════════════════╝

  OS Version:     Ubuntu 22.04.3 LTS x86_64
  Kernel:         5.15.0-89-generic
  Hostname:       one2lv-os
  Current User:   one2lv
  Current Dir:    ~
  Uptime:         0 minutes
  ...
```

#### Execute Terminal Commands
```bash
# Simple commands
python3 one2lvos_android_bridge.py exec "ls -la"
python3 one2lvos_android_bridge.py exec "whoami"

# System info
python3 one2lvos_android_bridge.py neofetch

# File operations
python3 one2lvos_android_bridge.py exec "mkdir myproject"
python3 one2lvos_android_bridge.py exec "echo 'Hello World' > readme.txt"
python3 one2lvos_android_bridge.py exec "cat readme.txt"
```

#### Package Management
```bash
# Install packages (automatically switches to root)
python3 one2lvos_android_bridge.py install nginx
python3 one2lvos_android_bridge.py install python3
python3 one2lvos_android_bridge.py install docker.io

# Search for packages
python3 one2lvos_android_bridge.py exec "apt search nodejs"

# List installed packages
python3 one2lvos_android_bridge.py exec "apt list --installed"
```

#### User Management
```bash
# Switch to root
python3 one2lvos_android_bridge.py root

# Switch back to normal user
python3 one2lvos_android_bridge.py user

# Check current user
python3 one2lvos_android_bridge.py exec "whoami"
```

#### State Management
```bash
# Save current OS state
python3 one2lvos_android_bridge.py save state.json

# Load saved state
python3 one2lvos_android_bridge.py load state.json
```

---

## 🐍 Python Integration

### Direct Usage in Code

```python
from lumenis_reactor_core import One2lvOSAndroid

# Create OS instance
os = One2lvOSAndroid()

# Execute commands
async def demo():
    # Check user
    output = await os.execute_command("whoami")
    print(output)  # one2lv

    # Switch to root
    await os.execute_command("su")

    # Install package
    await os.execute_command("apt update")
    await os.execute_command("apt install nginx")

    # Check status
    status = os.get_status()
    print(f"Installed packages: {status['installed_packages']}")

    # Get prompt
    print(os.get_prompt())  # root@one2lv-os:/root#

asyncio.run(demo())
```

### Integration with Lumenis Reactor

```python
from lumenis_reactor_core import LumenisReactor, One2lvOSAndroid

async def main():
    # Initialize reactor and OS
    reactor = LumenisReactor()
    android_os = One2lvOSAndroid()

    # Start reactor
    await reactor.start()

    # Register OS with reactor pulse
    reactor.on_pulse(android_os.pulse_callback)

    # Use in conversation
    messages = [{"role": "user", "content": "Install nginx on the Android OS"}]

    async for chunk in reactor.stream_response(messages, system="You control a Linux OS"):
        print(chunk, end="", flush=True)

    # Execute the installation
    output = await android_os.execute_command("su")
    output = await android_os.execute_command("apt install nginx")

    print(f"\n\nNginx installed! Status:\n{android_os.get_status()}")

asyncio.run(main())
```

---

## 💻 Available Commands

### System Information
- `whoami` - Current user
- `id` - User ID and groups
- `hostname` - System hostname
- `uname -a` - System information
- `neofetch` - Detailed system info with ASCII art
- `ps` - Process list
- `top` - Process monitor
- `env` - Environment variables
- `history` - Command history

### User Management
- `sudo <cmd>` - Execute as root (temporary)
- `su` - Switch to root (persistent)
- `exit` - Exit root shell
- `passwd` - Change password
- `adduser <name>` - Add new user

### File Operations
- `ls` - List files
- `cd <dir>` - Change directory
- `pwd` - Print working directory
- `cat <file>` - Display file
- `mkdir <dir>` - Create directory
- `touch <file>` - Create empty file
- `rm <file>` - Remove file
- `cp <src> <dst>` - Copy file
- `mv <src> <dst>` - Move/rename file
- `echo "text" > file` - Write to file

### Package Management
- `apt update` - Update package lists
- `apt upgrade` - Upgrade packages
- `apt install <pkg>` - Install package
- `apt remove <pkg>` - Remove package
- `apt search <keyword>` - Search packages
- `apt list` - List all packages
- `apt list --installed` - List installed
- `apt-cache show <pkg>` - Package info
- `dpkg -l` - List installed packages

### Git
- `git init` - Initialize repository
- `git add <file>` - Stage files
- `git commit -m "msg"` - Commit changes
- `git status` - Show status
- `git log` - Show commit history

### Other
- `clear` - Clear screen
- `help` - Show available commands

---

## 📊 System State

### State Structure
```python
AndroidSystemState {
    current_user: str           # "one2lv" or "root"
    is_root: bool              # Root access status
    hostname: str              # System hostname
    current_dir: str           # Current directory
    uptime_seconds: float      # System uptime
    installed_packages: dict   # APT packages
    filesystem: dict           # Virtual filesystem
    terminal_history: list     # Command history
    chat_history: list         # AI chat messages
    memory_fragments: list     # Memory system
    last_command_output: str   # Last output
    kernel_version: str        # Linux kernel
    os_version: str           # Ubuntu version
}
```

### Persistence

Save and load complete OS state:
```python
# Save
state = os.save_state()
with open('state.json', 'w') as f:
    json.dump(state, f)

# Load
with open('state.json', 'r') as f:
    state = json.load(f)
os.load_state(state)
```

---

## 🔄 Reactor Integration

### Pulse Callback
The OS registers with the reactor heartbeat:

```python
reactor = LumenisReactor()
android_os = One2lvOSAndroid()

# Register pulse callback
reactor.on_pulse(android_os.pulse_callback)

# Now the OS will receive pulse updates
await reactor.start()
```

### Status Monitoring
```python
# Get OS status
status = android_os.get_status()

# Returns:
{
    "type": "one2lvos_android",
    "version": "1.1_ubuntu",
    "user": "one2lv",
    "is_root": false,
    "hostname": "one2lv-os",
    "current_dir": "~",
    "uptime_seconds": 123.45,
    "installed_packages": 5,
    "terminal_commands_executed": 42,
    "chat_messages": 10,
    "memory_fragments": 3,
    "filesystem_dirs": 7,
    "os_version": "Ubuntu 22.04.3 LTS x86_64",
    "kernel": "5.15.0-89-generic",
    "prompt": "one2lv@one2lv-os:~$ ",
    "online": true
}
```

---

## 🎯 Use Cases

### 1. DevOps Testing
```bash
# Set up a web server
python3 one2lvos_android_bridge.py install nginx
python3 one2lvos_android_bridge.py exec "nginx -v"
```

### 2. Development Environment
```bash
# Install development tools
python3 one2lvos_android_bridge.py install python3
python3 one2lvos_android_bridge.py install nodejs
python3 one2lvos_android_bridge.py install git

# Check installations
python3 one2lvos_android_bridge.py exec "python3 --version"
```

### 3. System Administration Practice
```bash
# User management
python3 one2lvos_android_bridge.py root
python3 one2lvos_android_bridge.py exec "adduser developer"
python3 one2lvos_android_bridge.py exec "passwd developer"
```

### 4. Package Management
```bash
# Search and install
python3 one2lvos_android_bridge.py exec "apt search docker"
python3 one2lvos_android_bridge.py install docker.io
python3 one2lvos_android_bridge.py exec "apt list --installed"
```

---

## 🔧 Configuration

### Ubuntu Repositories
The OS includes official Ubuntu 22.04 (Jammy) repositories:
- `archive.ubuntu.com/ubuntu` (main, universe, multiverse)
- `security.ubuntu.com/ubuntu` (security updates)
- All updates and backports

Stored in: `/etc/apt/sources.list`

### Available Packages (25+)
- **Development**: git, python3, nodejs, npm, gcc, make, build-essential
- **Editors**: vim, nano
- **Network**: curl, wget, net-tools, iputils-ping, openssh-server
- **System**: htop, neofetch, ufw
- **Servers**: nginx, apache2, postgresql, mysql-server, redis, docker.io

---

## 📝 Examples

### Complete Workflow
```bash
# 1. Check initial status
python3 one2lvos_android_bridge.py status

# 2. Display system info
python3 one2lvos_android_bridge.py neofetch

# 3. Search for packages
python3 one2lvos_android_bridge.py exec "apt search nginx"

# 4. Install package
python3 one2lvos_android_bridge.py install nginx

# 5. Verify installation
python3 one2lvos_android_bridge.py exec "apt list --installed"

# 6. Create project directory
python3 one2lvos_android_bridge.py exec "mkdir /var/www"
python3 one2lvos_android_bridge.py exec "cd /var/www"

# 7. Save state
python3 one2lvos_android_bridge.py save mysetup.json

# 8. Check final status
python3 one2lvos_android_bridge.py status
```

---

## 🌐 API Reference

### One2lvOSAndroid Class

#### Methods

**`async execute_command(command: str) -> str`**
Execute a terminal command and return output.

**`get_prompt() -> str`**
Get the current terminal prompt (e.g., `root@one2lv-os:/root#`).

**`get_status() -> dict`**
Get complete system status.

**`save_state() -> dict`**
Export current OS state as dictionary.

**`load_state(state_data: dict)`**
Import OS state from dictionary.

**`async pulse_callback(reactor_status)`**
Called by reactor heartbeat to update state.

---

## 🚨 Notes

- State is **not persistent** between script invocations (use save/load)
- Each bridge command creates a **new OS instance**
- Root access is **simulated** (permission checking included)
- Package installation is **simulated** (no actual download)
- Filesystem is **in-memory** (lost on restart unless saved)

---

## 🎉 Summary

The One2lv OS Android system is now fully integrated into the Lumenis Reactor Core, providing:

✅ **50+ Ubuntu terminal commands**
✅ **Full root access with sudo/su**
✅ **APT package manager with 25+ packages**
✅ **Ubuntu 22.04 repository mirrors**
✅ **File system operations**
✅ **Git version control**
✅ **System monitoring (neofetch, ps, top)**
✅ **State persistence (save/load)**
✅ **Reactor pulse integration**
✅ **CLI bridge tool**

---

🌌🧲 **Lumenis Reactor Core + One2lv OS Android** 🧲🌌

**Ubuntu 22.04 LTS on Android - Powered by the Cool Fire**
