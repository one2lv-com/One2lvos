# One2lvOS Desktop Environment

A standalone desktop environment with window management, terminal, file system, AI assistant, and system monitoring.

## Features

### 🖥️ Window Management
- Draggable, resizable windows
- Minimize, maximize, close controls
- Multiple window support with z-index management
- Glassmorphism design with aurora background

### ⌨️ Terminal Emulator
- Built-in commands: help, clear, ls, pwd, date, whoami, neofetch, agents
- Command history
- Agent status integration
- Extensible command system

### 📁 File Manager
- Virtual file system browser
- File/folder operations
- Context menu support
- Modern UI with icon support

### 🤖 AI Assistant
- Chat-based interface
- Real-time message handling
- Integration with AgentManager
- Expandable AI capabilities

### 📊 System Monitor
- Real-time CPU/RAM monitoring
- Network statistics
- Process tracking
- Active window count
- Visual stat bars with animations

### 🎭 Agent Control Panel
- View all registered agents
- Agent status monitoring
- Task dispatch interface
- Integration with One2lvOS AgentManager

## Quick Start

### Option 1: Standalone Server
```bash
cd /home/vercel-sandbox/One2lvos/One2lvOS/Desktop
python3 -m http.server 8900
```

Then open: **http://localhost:8900/desktop.html**

### Option 2: Integrate with Main System
Add to One2lvOS/index.html or serve via nginx.

## Architecture

```
desktop.html
├── Aurora Canvas (animated background)
├── Desktop Grid (icon layout)
│   ├── Desktop Icons (Terminal, Files, AI, System, Agents)
│   └── Windows Container
│       ├── Terminal Window
│       ├── File Manager Window
│       ├── AI Assistant Window
│       ├── System Monitor Window
│       └── Agent Panel Window
└── Taskbar
    ├── Quick Launch Buttons
    └── System Stats (CPU, RAM, Clock)
```

## Modules

**agent.js** - Agent lifecycle management
- AgentManager class
- Task delegation
- Event bus integration

**terminal.js** - Terminal subsystem (36KB)
- Full terminal emulator
- BusyBox commands
- Package manager (apt)
- Wget/curl support

**desktop.html** - Main desktop environment (30KB)
- Window management
- UI components
- System integration

## Customization

### Add Desktop Icons
```javascript
const icons = [
    { name: 'MyApp', icon: '🚀', action: () => this.openMyApp() }
];
```

### Add Terminal Commands
```javascript
const commands = {
    mycommand: () => 'Command output here'
};
```

### Style Themes
Modify CSS variables in `<style>` section:
- Background gradient
- Border colors (#00ffff)
- Window transparency
- Aurora animation colors

## Integration

### With One2lvOS Main System
```html
<iframe src="Desktop/desktop.html" style="width:100%;height:100vh;border:none;"></iframe>
```

### With AgentManager
The Desktop automatically initializes AgentManager if available:
```javascript
if (window.AgentManager) {
    window.AgentManager.initialize();
}
```

## Performance

- Lightweight: ~30KB HTML + 39KB JS
- 60 FPS aurora animation
- Efficient window management
- Low memory footprint

## Browser Support

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile: ⚠️ Limited (desktop-oriented UI)

## Future Enhancements

- [ ] Persistent window state
- [ ] File system API integration
- [ ] Real network monitoring
- [ ] Plugin system
- [ ] Multi-desktop support
- [ ] Keyboard shortcuts
- [ ] Theme system
- [ ] Widget support

## License

MIT License - Part of One2lvOS
