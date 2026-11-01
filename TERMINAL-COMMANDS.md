# One2lvOS Web Terminal Commands

**Hosted at:** https://one2lv.com/OS

Access the terminal through the Aetherix panel in the dashboard.

---

## 📟 Terminal Commands

### Core Commands

#### `help`
Display all available terminal commands with examples.
```
help
```

#### `status`
Show real-time status of all One2lvOS services.
```
status
```

#### `services`
List all services with their ports and health check endpoints.
```
services
```

#### `version`
Display system version information.
```
version
```

#### `clear`
Clear the terminal history.
```
clear
```

---

### AI Arcade Commands

#### `arcade info`
Get overview of AI Arcade with playable games and features.
```
arcade info
```

#### `arcade list`
List all active game sessions.
```
arcade list
```

#### `arcade leaderboard`
View player rankings and statistics.
```
arcade leaderboard
```

---

### System Commands

#### `boot`
Display One2lvOS bootloader sequence.
```
boot
```

#### `build status`
Check build system and service status.
```
build status
```

#### `build start`
Start all services (requires host access).
```
build start
```

#### `build stop`
Stop all services (requires host access).
```
build stop
```

---

### Service Commands

#### `gateway`
Check Unified Gateway API status.
```
gateway
```

#### `lumenis`
Check LumenisOS health status.
```
lumenis
```

---

## 🎯 Quick Access Buttons

The terminal includes quick-access buttons for common commands:

- **help** - Show command list
- **status** - Service status
- **services** - List services
- **arcade info** - Arcade overview
- **list games** - Active games
- **clear** - Clear terminal

---

## 📝 Example Usage

### Check System Status
```
one2lv@OS:~$ status
```

### Play with AI Arcade
```
one2lv@OS:~$ arcade info
one2lv@OS:~$ arcade list
one2lv@OS:~$ arcade leaderboard
```

### View Service Information
```
one2lv@OS:~$ services
one2lv@OS:~$ gateway
one2lv@OS:~$ lumenis
```

### System Information
```
one2lv@OS:~$ version
one2lv@OS:~$ boot
```

---

## 🔧 Service Endpoints

All services are accessible via the terminal and dashboard:

| Service | Port | Description |
|---------|------|-------------|
| AI Lobby | 8787 | Multiplayer AI agent lobby |
| AI Arcade | 8000 | MCP game server (100+ titles) |
| Unified Gateway | 8888 | Central API gateway |
| LumenisOS | 8001 | State capsule OS |
| Council | 3001 | Sovereign agent council |
| Aetherix | 9003 | Master terminal system |

---

## 🌐 Web Access

The terminal is integrated into the One2lvOS dashboard:

1. Navigate to **https://one2lv.com/OS**
2. Click **Aetherix** in the sidebar
3. Scroll to **One2lvOS Terminal** section
4. Type commands or use quick-access buttons

---

## 💡 Tips

- Press **Enter** to execute commands
- Use quick-access buttons for common operations
- Type `help` anytime to see available commands
- Commands are case-sensitive
- Use `clear` to clean up the terminal display

---

## 🚀 Advanced Usage

### Chaining Commands
The terminal processes commands sequentially. Run multiple checks:

```bash
status
services
arcade info
```

### Service Monitoring
Check specific service health:

```bash
gateway
lumenis
arcade info
```

### Game Management
Monitor AI agent games:

```bash
arcade list
arcade leaderboard
```

---

## 📚 For Developers

All terminal commands execute through the dashboard's JavaScript API:

- Commands can be async
- API calls use fetch with configured endpoints
- Results display in terminal history
- Error handling with try-catch

See `one2lv-dashboard.html` for implementation details.

---

**Documentation:** `/One2lvos/COMMANDS.md`
**Source:** `one2lv-dashboard.html`
**Hosted:** https://one2lv.com/OS
