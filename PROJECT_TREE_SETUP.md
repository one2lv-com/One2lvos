# Project Tree Setup - Fixing Hardcoded Paths

## Problem

The One2lvOS repository contains **129 occurrences** of the hardcoded path `$HOME/` across **57 files**. This causes issues when:

- Cloning to different user accounts (`/home/john/`, `/home/alice/`)
- Running in Docker containers
- Deploying to production servers
- Testing in CI/CD pipelines
- Using on Windows with WSL

## Solution

Create a standardized directory structure that matches the expected path, regardless of where the repository is actually cloned.

## Quick Start

### Automatic Setup

Run the setup script from any clone location:

```bash
./setup-project-tree.sh
```

This will:
1. Create `$HOME/` directory (if needed)
2. Create a symlink: `/path/to/One2lvos → /actual/clone/location`
3. Make all hardcoded paths work transparently

### Verification

```bash
ls -la /path/to/One2lvos
# Should show: /path/to/One2lvos -> /your/actual/path/One2lvos
```

## Usage Options

### Option 1: Symlink (Recommended)

Clone anywhere, create symlink:

```bash
# Clone to your preferred location
git clone https://github.com/one2lv-com/One2lvos.git ~/projects/One2lvos
cd ~/projects/One2lvos

# Create symlink
./setup-project-tree.sh
```

Result:
- Repository at: `~/projects/One2lvos`
- Symlink at: `/path/to/One2lvos → ~/projects/One2lvos`
- All hardcoded paths work ✓

### Option 2: Clone Directly to Target

Clone directly to the expected location:

```bash
sudo mkdir -p the old sandbox home folder
sudo chown $USER:$USER the old sandbox home folder
git clone https://github.com/one2lv-com/One2lvos.git /path/to/One2lvos
cd /path/to/One2lvos
```

Result:
- Repository at: `/path/to/One2lvos`
- No symlink needed ✓

### Option 3: Docker/Container

Use bind mount or volume:

```dockerfile
# Dockerfile
FROM ubuntu:22.04
WORKDIR /app
COPY . /app

# Create expected directory structure
RUN ln -s /app /path/to/One2lvos
```

Or use docker-compose:

```yaml
version: '3.8'
services:
  one2lvos:
    image: one2lvos:latest
    volumes:
      - ./:/path/to/One2lvos
```

## Script Options

### Force Recreate

```bash
./setup-project-tree.sh --force
```

Removes existing target and recreates symlink.

### Link Only (No Copy)

```bash
./setup-project-tree.sh --link-only
```

Only creates symlink, never copies files.

## Files Affected

### Most Common Occurrences

**Documentation** (35 files):
- README.md, START_HERE.md, SETUP_COMPLETE.md
- Integration guides, deployment docs
- System status and complete files

**Python Scripts** (12 files):
- `lumenis_dream_state.py`
- `maton_security_monitor.py`
- `start_dream_session.py`
- `talk-to-lumenis.py`
- etc.

**Systemd Services** (2 files):
- `systemd/lumenis-security-heartbeat.service`
- `systemd/maton-security-monitor.service`

**HTML Interfaces** (2 files):
- `ACCESS_LINKS.html`
- `RECOVERY.html`

**Build Scripts** (6 files):
- Various setup and deployment scripts

### Path Patterns Found

```bash
# Most common patterns:
cd /path/to/One2lvos                    # 45 occurrences
/path/to/One2lvos/                      # 38 occurrences
/path/to/One2lvos/logs/                 # 12 occurrences
WorkingDirectory=/path/to/One2lvos      # 8 occurrences
ExecStart=/path/to/One2lvos/script.py   # 6 occurrences
```

## Integration with Build System

### Update build.sh

```bash
#!/bin/bash

# Run project tree setup first
./setup-project-tree.sh

# Continue with normal build
npm install
python3 -m pip install -r requirements.txt
# ... rest of build
```

### Update startos.sh

```bash
#!/bin/bash

# Ensure project tree is set up
./setup-project-tree.sh

# Start services
./start-all.sh
```

## Why This Works

1. **Symlinks are transparent**: Programs can't tell the difference between a symlink and a real directory
2. **No file duplication**: Symlink uses ~0 bytes of disk space
3. **Updates propagate**: Changes in real directory instantly visible via symlink
4. **Cross-platform**: Works on Linux, macOS, WSL
5. **Git-friendly**: Symlink itself is not tracked by git

## Advantages

✅ **No code changes needed** - All existing hardcoded paths work
✅ **Portable** - Clone anywhere, setup script handles the rest
✅ **Fast** - Symlink creation takes milliseconds
✅ **Safe** - No file copying or moving
✅ **Reversible** - Remove symlink to undo

## Disadvantages

⚠️ **Requires sudo** - Creating `the old sandbox home folder` directory (one-time)
⚠️ **Not on Windows** - Symlinks limited on Windows (use WSL)
⚠️ **Hardcoded paths still exist** - Not truly portable (but works)

## Future: VFS Migration

Long-term solution: Migrate to VFS (Virtual File System)

See `VFS_README.md` for portable path abstraction:

```python
from lumenis_vfs import get_vfs
vfs = get_vfs()  # Auto-detects project root
log_path = vfs.get_path("logs", "lumenis.log")
```

## Lumenis Reactor Core Integration

The project tree setup is integrated with Lumenis:

1. **Auto-detection**: Lumenis VFS checks for `/path/to/One2lvos` first
2. **Fallback**: If not found, VFS uses current directory
3. **Logging**: All operations log to VFS-managed paths
4. **Memory**: Conversations/dreams stored in VFS structure

## Troubleshooting

### Permission Denied

```bash
sudo chown -R $USER:$USER the old sandbox home folder
```

### Symlink Already Exists

```bash
./setup-project-tree.sh --force
```

### Broken Symlink

```bash
rm /path/to/One2lvos
./setup-project-tree.sh
```

### Docker Issues

Ensure volume mounts are correct:

```bash
docker run -v $(pwd):/path/to/One2lvos one2lvos:latest
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Setup Project Tree
  run: |
    sudo mkdir -p the old sandbox home folder
    sudo chown runner:runner the old sandbox home folder
    ln -s $GITHUB_WORKSPACE /path/to/One2lvos
```

### GitLab CI

```yaml
before_script:
  - mkdir -p the old sandbox home folder
  - ln -s $CI_PROJECT_DIR /path/to/One2lvos
```

## Statistics

- **Total occurrences**: 129
- **Files affected**: 57
- **File types**: .md (35), .py (12), .sh (6), .html (2), .service (2)
- **Setup time**: < 1 second
- **Disk space**: ~0 bytes (symlink)

## Related Documentation

- `VFS_README.md` - Virtual File System (long-term solution)
- `PORTABLE_SETUP.md` - Portable deployment guide
- `lumenis_reactor_core/terminal_utils/README.md` - Terminal utilities

---

**Run once, works everywhere.** 🌟
