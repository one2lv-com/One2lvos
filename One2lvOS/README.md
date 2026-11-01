# One2lvOS

A modular, browser-based spatial operating environment with AI integration, built on principles of clean separation of concerns and resilient state management.

## Architecture

One2lvOS follows a layered boot sequence with clear separation between the bootloader, state loading, and module management:

```
Power On
    │
    ▼
index.html
    │
    ▼
boot.js
    │
    ├── Hardware Check
    ├── WebGL Check
    ├── Storage Check
    ├── Asset Check
    │
    ▼
shader.js
    │
    ▼
state-loader.js
    │
    ├── localStorage autosave
    ├── Registry snapshot
    ├── snapshot.json
    ├── image payload (optional)
    └── emergency default
    │
    ▼
module-loader.js
    │
    ▼
Reactor Core
    │
    ▼
Registry
    │
    ▼
Desktop
```

## Module Structure

```
One2lvOS/
│
├── BIOS/                      # Boot layer
│   ├── index.html             # Entry point
│   ├── boot.js                # Boot orchestrator
│   ├── shader.js              # Aurora shader system
│   └── state-loader.js        # State restoration
│
├── Kernel/                    # Core system
│   ├── reactor-core.js        # Main kernel
│   ├── scheduler.js           # Task scheduling
│   ├── services.js            # System services
│   └── module-loader.js       # Dynamic module loading
│
├── Registry_of_Thought/       # Knowledge graph
│   ├── registry.js            # Node management
│   ├── archive.js             # History tracking
│   ├── snapshots.js           # State snapshots
│   └── council.js             # AI Council
│
├── Desktop/                   # User interface
│   ├── terminal.js            # Command-line interface
│   ├── dashboard.js           # Visual dashboard
│   ├── windows.js             # Window management
│   ├── notifications.js       # Notification system
│   └── taskbar.js             # Task bar
│
├── Infinity_Glasses/          # AR overlay
│   ├── hud.js                 # Heads-up display
│   ├── overlays.js            # Visual overlays
│   ├── eye-tracking.js        # Gaze detection
│   └── renderer.js            # AR renderer
│
├── Interplanetary_Disk/       # Storage layer
│   ├── filesystem.js          # Virtual filesystem
│   ├── cache.js               # Caching layer
│   ├── sync.js                # Synchronization
│   └── recovery.js            # Data recovery
│
├── Agentic_Control/           # Automation
│   ├── agents.js              # Agent system
│   ├── workflow.js            # Task workflows
│   ├── plugins.js             # Plugin system
│   └── automation.js          # Auto-tasks
│
├── Flux_Compassator/          # Navigation
│   ├── routing.js             # Route handling
│   ├── navigation.js          # Navigation system
│   └── session.js             # Session management
│
└── Assets/                    # Resources
    ├── shaders/               # Shader programs
    ├── icons/                 # Icons
    ├── textures/              # Textures
    ├── sounds/                # Sound effects
    └── snapshots/             # State snapshots
```

## Boot Sequence

The boot process provides POST-style feedback:

```
One2lvOS BIOS v0.9

[✓] WebGL initialized
[✓] Aurora shader loaded
[✓] Snapshot source detected
[✓] Registry mounted
[✓] Reactor Core online
[✓] Council initialized
[✓] Flux Compassator online
[✓] Interplanetary Disk mounted
[✓] Infinity Glass UI loaded

Boot complete in 347ms
```

## State Resilience

The state loader uses a priority-based fallback system:

1. **localStorage autosave** - Most recent auto-saved state (24hr max age)
2. **Registry snapshot** - Persistent IndexedDB snapshot
3. **snapshot.json** - Static configuration file
4. **Embedded image payload** - Steganographic state storage (optional)
5. **Emergency default** - Minimal working configuration

This ensures the OS can boot even if some sources fail.

## Key Features

### BIOS Layer
- Hardware capability detection
- WebGL validation
- Storage subsystem verification
- Aurora shader initialization
- Resilient state loading

### Kernel
- Module lifecycle management
- Service orchestration
- Auto-save (30s interval)
- Event bus
- Telemetry collection

### Registry of Thought
- Knowledge graph with nodes and connections
- AI Council consensus system
- Multi-agent deliberation
- Query and filtering

### Desktop Environment
- Terminal with command history
- Window management (drag, resize, minimize, maximize)
- System monitor (FPS, memory, events)
- Taskbar with clock
- Toast notifications

### System Services
- **EventBus** - Pub/sub event system
- **Notifications** - Toast message system
- **Logger** - Centralized logging
- **Telemetry** - Performance metrics

## Terminal Commands

```bash
help        # Show available commands
clear       # Clear terminal
status      # Show system status
registry    # Query Registry of Thought
council     # Submit query to AI Council
modules     # List loaded modules
save        # Save system state
version     # Show system version
```

## Usage

### Starting the OS

Simply open `index.html` in a modern browser. The boot sequence will:
1. Check hardware capabilities
2. Initialize WebGL aurora shader
3. Restore state from available sources
4. Boot kernel and modules
5. Launch desktop environment

### Saving State

State is automatically saved:
- Every 30 seconds (if auto-save enabled)
- On window close (`beforeunload`)
- Manual save via `save` terminal command

### Adding Modules

To add a new module:

1. Create module directory under One2lvOS/
2. Implement module class with `initialize()` method
3. Register in `module-loader.js` base paths
4. Load via `ModuleLoader.load('moduleName')`

Example:

```javascript
class MyModule {
    async initialize(state) {
        console.log('[MyModule] Initializing');
        // Setup logic
    }

    getState() {
        return { /* module state */ };
    }
}

window.MyModule = new MyModule();
```

## PWA Support

One2lvOS includes a manifest for Progressive Web App installation:

- Standalone display mode
- Offline operation via service workers
- IndexedDB persistence
- Local storage fallback

## Architecture Benefits

### Separation of Concerns
Each layer has a single responsibility:
- **BIOS** - Boot and hardware detection
- **State Loader** - State restoration
- **Kernel** - Module orchestration
- **Modules** - Feature implementation

### Independent Replacement
Any subsystem can be replaced without affecting others:
- Swap shader system without touching boot logic
- Replace state storage without kernel changes
- Add new modules without modifying core

### Easy Testing
Each component can be tested in isolation:
- Mock hardware checks in BIOS
- Test state loader with various sources
- Unit test individual modules

### Future Extensions
New features integrate cleanly:
- Add dashboard panels without rewriting UI
- Add new services to kernel
- Create plugins for Agentic Control
- Extend Registry with new node types

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Requires:
- WebGL 1.0 or 2.0
- ES6 support
- IndexedDB
- localStorage

## Development

### File Structure
All modules are loaded dynamically via `<script>` tags. No build process required.

### Debugging
- Open browser console for boot logs
- Check `[SystemName]` prefixed messages
- Use `status` command for system overview

### State Inspection
```javascript
// Get current state
const state = window.ReactorCore.getState();

// Query registry
const nodes = window.RegistryOfThought.query();

// Check loaded modules
const modules = window.ModuleLoader.listModules();

// Get telemetry
const metrics = window.SystemServices.getService('telemetry').getMetrics();
```

## License

MIT

## Version

0.9 - Initial Architecture Release
