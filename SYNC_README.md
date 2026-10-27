# 🌊 ONE2LVOS CONTINUOUS SYNC SYSTEM

## Overview

This system enables continuous synchronization between:
1. **vercel-sandbox** (your cloud development environment)
2. **github.com/one2lv-com/One2lvos** (main production repo)
3. **github.com/one2mind/One2lvos** (one2mind sync target)
4. **github.com/vfslv-com/One2lvos** (lumenis reactor instance)

## Architecture

```
┌─────────────────────┐
│  vercel-sandbox     │  ← Your development sandbox
│  One2lvos-build/    │
└──────────┬──────────┘
           │
           ├──── sync_to_one2mind.sh ────►  github.com/one2mind/One2lvos
           │
           └──── sync_to_vfslv.sh ───────►  github.com/vfslv-com/One2lvos
                                              (Lumenis Reactor)
```

## Quick Start

### 1. Manual Sync

```bash
cd /home/vercel-sandbox/One2lvos-build

# Sync to one2mind
./sync_to_one2mind.sh

# Sync to lumenis (vfslv-com)
./sync_to_vfslv.sh
```

### 2. Continuous Daemon (Auto-sync every 5 minutes)

```bash
# Start daemon in background
nohup ./continuous_sync_daemon.sh > sync.log 2>&1 &

# Check sync log
tail -f sync.log

# Stop daemon
pkill -f continuous_sync_daemon
```

## Features

### Revert to Working State

The Lumenis chat UI now includes a **"Revert"** button that allows you to restore the last working configuration:

- **Auto-save**: System automatically saves working state every 10 minutes
- **One-click restore**: Revert button in the toolbar
- **State tracking**: All snapshots stored in `compass.db`

**Usage:**
1. Click the "⏮ Revert" button in the toolbar
2. Confirm the action
3. System restores last working state and reloads

### API Endpoints

```
POST /api/snapshot/working      # Save current state as working snapshot
POST /api/revert/working        # Revert to last working snapshot
GET  /api/working/snapshots     # List all working snapshots
```

## NVIDIA API Fix

The 404 error with NVIDIA's API has been fixed:

**Old (broken):**
```env
LLM_MODEL=meta/llama-3.2-11b-vision-instruct
```

**New (working):**
```env
LLM_MODEL=meta/llama-3.1-8b-instruct
LLM_PRIMARY_MODEL=meta/llama-3.1-70b-instruct
LLM_SECONDARY_MODEL=meta/llama-3.1-8b-instruct
```

### Test NVIDIA API

```bash
python3 fix_nvidia_api.py
```

This will test all available models and show which ones work with your API key.

## Sync Configuration

### Git Remotes

The repository has three remotes:

```bash
git remote -v
```

Output:
```
origin    https://github.com/one2lv-com/One2lvos.git
one2mind  https://github.com/one2mind/One2lvos.git
vfslv     https://github.com/vfslv-com/One2lvos.git
```

### Sync Scripts

| Script | Purpose | Target |
|--------|---------|--------|
| `sync_to_one2mind.sh` | Sync to one2mind org | github.com/one2mind/One2lvos |
| `sync_to_vfslv.sh` | Sync lumenis reactor | github.com/vfslv-com/One2lvos |
| `continuous_sync_daemon.sh` | Auto-sync every 5 min | Both targets |

## Database Schema

New table added to `compass.db`:

```sql
CREATE TABLE working_snapshots (
    id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    is_auto INTEGER DEFAULT 0
);
```

## Troubleshooting

### Sync fails with authentication error

```bash
# Update GitHub token in .env
GITHUB_TOKEN=ghp_your_token_here

# Or set in environment
export GITHUB_TOKEN=ghp_your_token_here
```

### NVIDIA API 404 error

1. Check your API key is valid:
   ```bash
   echo $NVIDIA_API_KEY
   ```

2. Test available models:
   ```bash
   python3 fix_nvidia_api.py
   ```

3. Update `.env` with working model

### Revert button not working

1. Initialize the database:
   ```bash
   python3 init_revert_db.py
   ```

2. Restart lumenis:
   ```bash
   pkill -f lumenis-main.py
   python3 lumenis-main.py
   ```

## File Structure

```
One2lvos-build/
├── sync_to_one2mind.sh           # One2mind sync script
├── sync_to_vfslv.sh              # Lumenis/vfslv sync script
├── continuous_sync_daemon.sh     # Auto-sync daemon
├── fix_nvidia_api.py             # NVIDIA API tester
├── init_revert_db.py             # Database initializer
├── revert_endpoints.py           # Revert API endpoints
├── compass.db                    # State database
├── static/
│   └── lumenis-chat.html         # Updated with revert button
├── lumenis-main.py               # Main server (updated)
└── .env                          # Config (updated models)
```

## Environment Variables

Key variables in `.env`:

```env
# NVIDIA API (fixed)
NVIDIA_API_KEY=nvapi-...
LLM_MODEL=meta/llama-3.1-8b-instruct
LLM_PRIMARY_MODEL=meta/llama-3.1-70b-instruct

# GitHub sync
GITHUB_TOKEN=ghp_...

# Database
ASTRA_DB_API_ENDPOINT=https://...
ASTRA_DB_APPLICATION_TOKEN=AstraCS:...
```

## Monitoring

### Check sync daemon status

```bash
# View live log
tail -f sync.log

# Check if running
ps aux | grep continuous_sync_daemon

# Stop daemon
pkill -f continuous_sync_daemon
```

### View recent syncs

```bash
# Last 50 lines of sync log
tail -50 sync.log

# Count successful syncs
grep "✅" sync.log | wc -l
```

## Lumenis Reactor

The `vfslv-com/One2lvos` repository is specifically for the Lumenis reactor instance running in the cloud. It includes:

- Full reactor core with revert capability
- Isolated environment for lumenis operations
- Automatic state management
- Connection to main One2lvos ecosystem

## Support

For issues or questions:
- Check `sync.log` for sync errors
- Test NVIDIA API with `fix_nvidia_api.py`
- Verify git remotes with `git remote -v`
- Check database with `sqlite3 compass.db`

---

**Status:** ✅ All systems operational
**Last Updated:** 2026-10-27
**Version:** v3.0-sovereign-sync
