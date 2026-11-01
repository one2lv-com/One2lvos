# One2lvOS Quick Start

## Getting Started in 3 Steps

### 1. Open the OS
```bash
# Start a local server (required for ES6 modules)
python3 -m http.server 8000

# Or using Node.js
npx serve

# Then open: http://localhost:8000
```

### 2. Watch the Boot Sequence

You'll see:
```
One2lvOS BIOS v0.9

[✓] WebGL initialized
[✓] Aurora shader loaded
[✓] Storage subsystem online
[✓] Asset manifest verified
[✓] Aurora shader loaded
[✓] State loader initialized
[✓] Reactor Core online
[✓] Kernel services started

Boot complete in ~300ms
```

### 3. Use the Terminal

The terminal window will appear with commands ready:

```bash
❯ help
Available commands:
  help        - Show this help message
  clear       - Clear terminal
  status      - Show system status
  registry    - Query Registry of Thought
  council     - Submit query to AI Council
  modules     - List loaded modules
  save        - Save system state
  version     - Show system version

❯ status
System Status:
  Uptime: 42s
  Modules: 4 enabled
  Registry Nodes: 0

❯ version
One2lvOS v0.9
```

## Features at a Glance

### Aurora Background
- Animated WebGL shader with cyan/pink gradient waves
- Nebula effect with dynamic movement
- Vignette and glow effects

### Terminal Window
- Full command history (↑/↓ arrow keys)
- Draggable title bar
- Minimize/maximize/close buttons
- Auto-scrolling output

### Taskbar
- System branding
- Real-time stats (FPS, memory, event count)
- Live clock

### State Persistence
- Auto-saves every 30 seconds
- Saves on browser close
- Restores on next boot
- Multiple fallback sources

## Customization

### Change Theme Colors

Edit the CSS variables in `index.html`:
```css
--primary-color: #00ffff;    /* Cyan */
--secondary-color: #ff00ff;  /* Pink */
--background: #0a0a0a;       /* Dark */
```

### Add Custom Commands

Edit `Desktop/terminal.js`:
```javascript
registerCommands() {
    this.commands = {
        // Add your command here
        mycommand: () => {
            return 'Hello from my command!';
        },
        // ... existing commands
    };
}
```

### Create New Module

1. Create folder: `One2lvOS/MyModule/`
2. Create file: `mymodule.js`
3. Define class:

```javascript
class MyModule {
    async initialize(state = {}) {
        console.log('[MyModule] Starting');
        // Your init logic
    }

    getState() {
        return { /* your state */ };
    }
}

window.MyModule = new MyModule();
```

4. Register in `Kernel/module-loader.js`:
```javascript
this.basePaths = {
    'mymodule': 'MyModule',
    // ... existing modules
};
```

5. Load it:
```javascript
await window.ModuleLoader.load('mymodule');
```

## Troubleshooting

### Boot Fails
- Check browser console for errors
- Verify WebGL support: `chrome://gpu`
- Clear localStorage: `localStorage.clear()`
- Hard refresh: Ctrl+Shift+R

### Terminal Not Responding
- Click inside terminal window to focus
- Check input element is visible
- Reload page to restart

### State Not Saving
- Check browser storage quota
- Verify localStorage permissions
- Check console for save errors

### Performance Issues
- Check FPS in taskbar stats
- Lower shader complexity in `BIOS/shader.js`
- Disable auto-save in state

## Next Steps

1. **Explore the Registry** - Add nodes and connections
2. **Try the AI Council** - Submit queries for consensus
3. **Create Custom Modules** - Extend functionality
4. **Build Workflows** - Use Agentic Control
5. **Design Overlays** - Create AR HUD elements

## Support

- Check `README.md` for full documentation
- Inspect browser console for debugging
- Review module source for implementation details

---

**Ready to explore?** Open `index.html` and watch One2lvOS come to life.
