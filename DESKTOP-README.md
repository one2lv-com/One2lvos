# One2lvOS Desktop Environment

**File:** `one2lvos-desktop.html`
**Production URL:** https://one2lv.com/OS
**Local Test:** http://localhost:9000/one2lvos-desktop.html

---

## 🎨 Features

### Modern Glassmorphic UI
- Windows 11-style desktop environment
- Draggable, resizable windows
- Glassmorphism backdrop blur effects
- Smooth animations and transitions
- Touch and mouse support

### Integrated Applications

#### 1. **About One2lvOS**
- System information
- Version details
- Links to repository

#### 2. **One2lvOS Terminal** 🖥️
- Full command-line interface
- All One2lvOS commands integrated
- Real-time service status
- AI Arcade integration

**Available Commands:**
```bash
help              # Show all commands
status            # Service status check
services          # List all services
version           # System version
arcade [cmd]      # AI Arcade commands (info, list, leaderboard)
clear             # Clear terminal
date              # Current date/time
whoami            # Current user
```

#### 3. **AI Arcade** 🎮
- Interactive game interface
- Connect to MCP server on port 8080
- Browse 21 playable games + 100 game library
- View leaderboards
- Create and join games

**Quick Actions:**
- Arcade Info
- List Games
- Leaderboard
- Game Library

#### 4. **Service Monitor** 📊
- Real-time service health checks
- Visual status indicators
- Auto-refresh capability

**Monitored Services:**
- AI Lobby (8787)
- AI Arcade (8080)
- Unified Gateway (8888)
- LumenisOS (8001)
- Council (3001)
- Aetherix (9003)

#### 5. **Calculator** 🔢
- Full-featured calculator
- Modern UI with history
- Keyboard and click support

#### 6. **Notepad** 📝
- Simple text editor
- Clean monospace interface
- Menu bar (File, Edit, Format, View)

#### 7. **Settings** ⚙️
- Personalization options
- Wallpaper selection
- 4 beautiful backgrounds included
- Easy customization

---

## 🚀 Deployment

### Local Testing
```bash
cd One2lvos
python -m http.server 9000
# Open: http://localhost:9000/one2lvos-desktop.html
```

### Production Deployment
1. Upload `one2lvos-desktop.html` to https://one2lv.com/OS
2. Update API endpoints if needed (currently localhost)
3. Ensure all services are running
4. Test all functionality

### Service Requirements
- **AI Arcade:** Port 8080
- **Gateway:** Port 8888
- Other services optional but recommended

---

## 🖱️ Usage Guide

### Desktop
- **Double-click icons** to open applications
- **Click Start button** for start menu
- **Drag window headers** to move windows
- **Click traffic lights** (yellow/green/red) to minimize/maximize/close

### Start Menu
- **Search bar** for quick access
- **Grid layout** of all applications
- **User profile** and power options at bottom
- **Click outside** or press Start to close

### Windows
- **Minimize** (yellow button) - Hide to taskbar
- **Maximize** (green button) - Full screen
- **Close** (red button) - Close application
- **Drag** title bar to move
- **Click** anywhere to bring to front

### Taskbar
- **Start button** - Opens start menu
- **App indicators** - Click to restore/focus
- **System tray** - Network, sound, battery indicators
- **Clock** - Current time and date
- **Notifications** - Bell icon

---

## 💻 Technical Details

### Architecture
```
one2lvos-desktop.html
├── Tailwind CSS (CDN)
├── Font Awesome Icons
├── Google Fonts (Inter)
└── Vanilla JavaScript
    ├── Window Management
    ├── App State
    ├── API Integration
    └── Event Handlers
```

### API Endpoints
```javascript
const ARCADE = 'http://localhost:8080';  // AI Arcade MCP
const GW = 'http://localhost:8888';      // Unified Gateway
```

### Window System
- **Z-index management** for window stacking
- **Pointer events** for drag support
- **Touch-friendly** for mobile devices
- **Responsive** animations

### State Management
```javascript
let highestZ = 10;        // Window z-index tracker
let openApps = {};        // Currently open applications
```

---

## 🎨 Customization

### Adding New Apps

```javascript
apps['my-app'] = {
    name: 'My App',
    icon: 'fas fa-star',
    color: 'text-blue-500',
    width: 600,
    height: 400,
    content: `<div>App HTML here</div>`,
    onOpen: (appId) => {
        // Initialization code
    },
    onClose: (appId, win) => {
        // Cleanup code
    }
};
```

### Changing Wallpapers
1. Open **Settings** app
2. Click **Personalization**
3. Select from 4 pre-configured wallpapers
4. Or add custom URLs in the settings code

### Modifying Colors
Update Tailwind classes in the HTML:
- `bg-blue-500` → `bg-purple-500`
- `text-gray-800` → `text-gray-900`
- Backdrop blur: `backdrop-blur-2xl`

---

## 🔧 Troubleshooting

### Terminal Commands Not Working
- Ensure AI Arcade is running on port 8080
- Check Gateway service on port 8888
- Open browser console for errors

### Services Show OFFLINE
- Start services: `./build.sh start`
- Check port availability
- Verify .env configuration

### Windows Not Dragging
- Check if pointer events are supported
- Disable browser extensions
- Try different browser

### Blank Screen
- Check browser console for errors
- Verify all CDN resources loaded
- Clear browser cache

---

## 📚 Related Documentation

- **COMMANDS.md** - System CLI commands
- **TERMINAL-COMMANDS.md** - Web terminal reference
- **DEPLOYMENT-NOTES.md** - Deployment guide
- **README.md** - Main project documentation

---

## 🌐 Live Demo

**URL:** https://one2lv.com/OS

### Quick Test
1. Click **One2lvOS Terminal** icon
2. Type `help` and press Enter
3. Try `status` to check services
4. Run `arcade info` for AI Arcade

---

## 🎯 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Enter** | Execute terminal command |
| **Escape** | Close start menu (planned) |
| **Click outside** | Close start menu |

---

## 🔐 Security Notes

- Terminal runs in sandboxed environment
- API calls use CORS
- No shell access to host system
- Read-only status commands only
- Services checked via health endpoints

---

## 🚧 Roadmap

### Planned Features
- [ ] Drag-and-drop file management
- [ ] Right-click context menus
- [ ] Keyboard shortcuts system
- [ ] Multi-monitor support (simulated)
- [ ] Themes and color schemes
- [ ] App store for new applications
- [ ] Cloud save/load state
- [ ] Screen recording
- [ ] Screenshot capture

### Improvements
- [ ] Touch gestures for mobile
- [ ] Accessibility features
- [ ] Performance optimizations
- [ ] Offline mode support
- [ ] PWA capabilities

---

**Version:** 2.0.0
**Last Updated:** 2026-10-03
**License:** MIT
**Repository:** https://github.com/one2lv-com/One2lvos
