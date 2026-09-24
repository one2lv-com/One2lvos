# 🪟 AI Arcade - Windows 11 Installation Guide

## 📦 **What You Get**

A complete Windows 11 installer package for the **AI Arcade** - featuring 21 playable games and a library of 100+ games with AI strategy notes!

---

## ✅ **Requirements**

### Minimum System Requirements
- **OS**: Windows 10 or Windows 11
- **Python**: 3.9 or higher
- **RAM**: 2 GB minimum (4 GB recommended)
- **Disk Space**: 500 MB free space
- **Network**: Internet connection (for installation only)

### Required Software
1. **Python 3.9+**
   - Download from: https://www.python.org/downloads/
   - ⚠️ **IMPORTANT**: Check "Add Python to PATH" during installation!

2. **pip** (usually included with Python)

---

## 🚀 **Installation Methods**

### Method 1: Automated Installer (Recommended)

1. **Download** the installer:
   - `install-ai-arcade-windows.bat`

2. **Run** the installer:
   - Double-click `install-ai-arcade-windows.bat`
   - OR right-click → "Run as administrator" (recommended)

3. **Follow** the prompts:
   - The installer will check Python
   - Install dependencies automatically
   - Create launcher scripts
   - Set up desktop shortcut

4. **Launch** AI Arcade:
   - Double-click "AI Arcade" icon on desktop
   - OR run `start-ai-arcade.bat` in installation folder

5. **Access** the dashboard:
   - Opens automatically at: http://localhost:8080/one2lv-dashboard.html

### Method 2: Manual Installation

If the automated installer doesn't work:

```batch
:: 1. Create directory
mkdir %USERPROFILE%\AI-Arcade
cd %USERPROFILE%\AI-Arcade

:: 2. Install Python packages
python -m pip install chess uvicorn fastapi sse-starlette requests

:: 3. Download files from GitHub
:: Visit: https://github.com/one2lv-com/One2lvos

:: 4. Start the server
python server.py --host 0.0.0.0 --port 8003

:: 5. In another terminal, start dashboard
python -m http.server 8080

:: 6. Open browser
start http://localhost:8080/one2lv-dashboard.html
```

---

## 📂 **Installation Files**

After installation, you'll find these files:

```
%USERPROFILE%\AI-Arcade\
│
├── 📄 Launchers
│   ├── start-ai-arcade.bat       # Start everything (recommended)
│   ├── start-server.bat          # MCP server only
│   ├── start-dashboard.bat       # Dashboard only
│   └── stop-ai-arcade.bat        # Stop all services
│
├── 📄 Server Files
│   ├── server.py                 # MCP server
│   ├── requirements.txt          # Python dependencies
│   └── games\                    # Game modules
│
├── 📄 Documentation
│   ├── README.txt                # Complete instructions
│   └── logs\                     # Error logs
│
└── 📄 Utilities
    ├── uninstall.bat             # Remove AI Arcade
    └── data\                     # Game data
```

### Desktop Shortcut
- **AI Arcade.lnk** → Quick launch icon

---

## 🎮 **How to Use**

### Starting AI Arcade

**Option 1**: Desktop Shortcut
```
Double-click "AI Arcade" icon
```

**Option 2**: Batch File
```batch
cd %USERPROFILE%\AI-Arcade
start-ai-arcade.bat
```

**Option 3**: Individual Services
```batch
:: Start server only
start-server.bat

:: Start dashboard only (in another window)
start-dashboard.bat
```

### Accessing the Dashboard

After starting, the dashboard opens automatically:
- **URL**: http://localhost:8080/one2lv-dashboard.html
- **MCP Server**: http://localhost:8003
- **API**: http://localhost:8003/mcp

### Playing Games

1. **Open Dashboard** in your browser
2. **Navigate** to Sidebar → **Arcade** → **Play**
3. **Select** a game from the dropdown:
   - Board: Chess, Go, Shogi, Hex, Gomoku, etc.
   - Puzzle: Minesweeper, Sudoku, Mastermind, Picross, etc.
   - Arcade: Pac-Man, Tetris, Space Invaders, etc.
4. **Create** a game with your agent name
5. **Join** (if 2-player) or **Play** (if solo)
6. **Make moves** using the move input field

### Stopping AI Arcade

**Option 1**: Press key in startup window
```
Press any key in the "AI Arcade" window
```

**Option 2**: Run stop script
```batch
cd %USERPROFILE%\AI-Arcade
stop-ai-arcade.bat
```

**Option 3**: Task Manager
```
Ctrl+Shift+Esc → Find Python processes → End Task
```

---

## 🎯 **Games Available**

### Strategy Board Games (10)
- ♟️ Chess - Minimax with alpha-beta pruning
- ⚫ Go - Territory control on 9x9 board
- 🔴 Checkers - Mandatory jumps
- ⚪ Othello - Disc flipping strategy
- ❌ Tic-Tac-Toe - Perfect information
- 🔴 Connect 4 - Solved game
- 🎴 **Shogi** - Japanese chess with drops ⭐
- ⬡ **Hex** - Connection game ⭐
- ⭕ **Gomoku** - Five in a row ⭐
- 🌰 **Mancala** - Stone sowing ⭐

### Puzzle Games (6)
- 💣 Minesweeper - Constraint satisfaction
- 🔢 Sudoku - Backtracking solver
- 🚢 Battleship - Probability maps
- 🔤 Scrabble - Dictionary search
- 🎨 **Picross** - Nonogram puzzles ⭐
- 🔐 **Mastermind** - Code breaking ⭐

### Arcade Games (5)
- 👾 Pac-Man - Ghost pathfinding
- 🟦 Tetris - Spatial optimization
- 👽 Space Invaders - Trajectory calculation
- 🏓 Pong - Physics prediction
- 📎 Universal Paperclips - Resource management

⭐ = New games added!

---

## 🔧 **Troubleshooting**

### Python Not Found

**Problem**: Installer says "Python not found"

**Solution**:
1. Download Python from https://www.python.org/downloads/
2. Run installer
3. ✅ **CHECK** "Add Python to PATH" (very important!)
4. Complete installation
5. Open new Command Prompt
6. Verify: `python --version`
7. Run AI Arcade installer again

### Port Already in Use

**Problem**: "Port 8003 or 8080 already in use"

**Solution 1** - Stop conflicting service:
```batch
:: Find what's using the port
netstat -ano | findstr :8003
netstat -ano | findstr :8080

:: Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>
```

**Solution 2** - Use different ports:
```batch
:: Edit start-ai-arcade.bat
:: Change: --port 8003
:: To:     --port 8013

:: Change: http.server 8080
:: To:     http.server 8090
```

### Dependencies Failed to Install

**Problem**: "Error installing dependencies"

**Solution**:
```batch
:: Run as Administrator
:: Open Command Prompt (Admin)

:: Upgrade pip
python -m pip install --upgrade pip

:: Install packages individually
python -m pip install chess
python -m pip install uvicorn
python -m pip install fastapi
python -m pip install sse-starlette
python -m pip install requests

:: Verify installation
python -m pip list
```

### Firewall Blocking

**Problem**: Can't access dashboard from other computers

**Solution**:
```batch
:: Run as Administrator

:: Allow port 8003 (MCP Server)
netsh advfirewall firewall add rule name="AI Arcade - MCP Server" dir=in action=allow protocol=TCP localport=8003

:: Allow port 8080 (Dashboard)
netsh advfirewall firewall add rule name="AI Arcade - Dashboard" dir=in action=allow protocol=TCP localport=8080
```

Or use the provided script:
```batch
CONFIGURE-FIREWALL.bat
```

### Server Won't Start

**Problem**: Server crashes immediately

**Solution**:
```batch
:: Check for errors
cd %USERPROFILE%\AI-Arcade\logs

:: Check Python path
where python

:: Reinstall dependencies
python -m pip install -r requirements.txt

:: Run server manually to see errors
python server.py --host 0.0.0.0 --port 8003
```

### Dashboard Shows Blank Page

**Problem**: Dashboard loads but is empty

**Solution**:
1. Check if server is running: http://localhost:8003
2. Clear browser cache: Ctrl+Shift+Delete
3. Try different browser (Chrome, Edge, Firefox)
4. Check console for errors: F12 → Console tab
5. Restart both server and dashboard

---

## 🔐 **Firewall Configuration**

### Automatic (Recommended)
```batch
:: Run as Administrator
CONFIGURE-FIREWALL.bat
```

### Manual
1. Open **Windows Defender Firewall**
2. Click **Advanced settings**
3. Click **Inbound Rules** → **New Rule**
4. Select **Port** → Next
5. Enter port **8003** → Next
6. Allow the connection → Next
7. Check all profiles → Next
8. Name: "AI Arcade - MCP Server" → Finish
9. Repeat for port **8080** (Dashboard)

---

## 📚 **Documentation**

### Included Files
- **README.txt** - Complete instructions
- **GAME-LIST.txt** - All games with descriptions
- **PACKAGE-INFO.txt** - Package information

### Online Resources
- **GitHub**: https://github.com/one2lv-com/One2lvos
- **Issues**: https://github.com/one2lv-com/One2lvos/issues
- **Dashboard**: http://localhost:8080/one2lv-dashboard.html (after starting)

---

## 🗑️ **Uninstallation**

### Method 1: Uninstaller Script
```batch
cd %USERPROFILE%\AI-Arcade
uninstall.bat
```

### Method 2: Manual
1. Stop all AI Arcade services
2. Delete desktop shortcut
3. Delete installation folder:
   ```batch
   rmdir /s /q %USERPROFILE%\AI-Arcade
   ```
4. Remove firewall rules (if added):
   ```batch
   netsh advfirewall firewall delete rule name="AI Arcade - MCP Server"
   netsh advfirewall firewall delete rule name="AI Arcade - Dashboard"
   ```

---

## 💡 **Tips & Tricks**

### Run on Startup
1. Press `Win+R`
2. Type: `shell:startup`
3. Create shortcut to `start-ai-arcade.bat`

### Access from Other Computers
1. Find your IP: `ipconfig`
2. Configure firewall (see above)
3. Access from other PC: `http://<YOUR-IP>:8080/one2lv-dashboard.html`

### Change Ports
Edit batch files to use different ports:
- Server: `--port 8003` → `--port 9003`
- Dashboard: `8080` → `9080`

### View Logs
```batch
cd %USERPROFILE%\AI-Arcade\logs
type error.log
```

### Update AI Arcade
1. Download latest version
2. Run installer again
3. Keeps your settings and data

---

## 🆘 **Getting Help**

### Check System
```batch
CHECK-SYSTEM.bat
```

### Common Issues
1. **Python not in PATH** → Reinstall Python with PATH option
2. **Port conflicts** → Change ports or stop conflicting services
3. **Firewall blocking** → Run CONFIGURE-FIREWALL.bat as Admin
4. **Missing dependencies** → Run: `python -m pip install -r requirements.txt`

### Support Channels
- **GitHub Issues**: https://github.com/one2lv-com/One2lvos/issues
- **Documentation**: See README.txt in installation folder

---

## 📝 **Changelog**

### Version 1.0.0
- ✅ Initial Windows installer
- ✅ 21 playable games
- ✅ 100+ game library
- ✅ MCP 2024-11-05 protocol
- ✅ Dashboard integration
- ✅ Desktop shortcut
- ✅ Automatic dependency installation
- ✅ Firewall configuration helper
- ✅ Uninstaller included

---

## 📄 **License**

MIT License - See installation folder for details

---

## 🎮 **Ready to Play!**

```batch
:: Quick Start
cd %USERPROFILE%\AI-Arcade
start-ai-arcade.bat

:: Then open in browser
start http://localhost:8080/one2lv-dashboard.html
```

**Enjoy the AI Arcade!** 🚀

---

**Installation Support**: Check README.txt in installation folder
**GitHub**: https://github.com/one2lv-com/One2lvos
**Status**: ✅ Ready for Windows 10/11
