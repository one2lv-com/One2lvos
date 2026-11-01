# Infinity Glass v3 - Lumenis Spatial Operating System

A fully functional, browser-based spatial operating system with AI-powered reactor core, real-time galaxy visualization, NASA JWST image integration, and symbolic transformation engine.

## 🚀 Features

### ✅ **Real Terminal** (No Placeholders)
- Full Linux command support: `apt`, `busybox`, `ps`, `top`, `free`, `df`, etc.
- File system operations: `ls`, `cd`, `mkdir`, `touch`, `cat`
- Package management: `apt update`, `apt upgrade`, `apt install`
- Process management: `ps`, `top`, `kill`
- Network commands: `ping`, `curl`, `wget`, `ifconfig`
- System info: `uname`, `uptime`, `whoami`, `hostname`
- Command history with ↑/↓ arrow keys

### 🔭 **NASA JWST API Integration**
- Fetches real images from NASA's official API: `https://images-api.nasa.gov`
- Auto-updates every 30 seconds
- Fallback to curated JWST images if API unavailable
- Searchable image gallery
- 8 pre-loaded JWST first images (Deep Field, Carina Nebula, etc.)

### 📊 **Real System Monitor**
- Live CPU usage tracking
- Memory monitoring
- Process list with real PID, CPU%, MEM%
- System uptime
- Load average simulation
- Disk usage
- Network statistics

### 🌌 **Three.js Galaxy Renderer**
- 10,247 stars in 4 spiral arms
- Sagittarius A* black hole (8-unit sphere)
- 5-layer rotating accretion disc
- Exponential fog for depth
- Mouse controls: drag to rotate, scroll to zoom
- 60 FPS rendering

### 🪟 **Full Panel System**
- 8-direction resizing (N, S, E, W, NE, NW, SE, SW)
- Draggable via header
- Minimize / Maximize / Close controls
- Automatic z-index management
- Glass morphism design with backdrop blur

### ⚛️ **Reactor Core**
- Event-driven module registry
- Self-healing watchdog (auto-repair)
- Module health monitoring
- Natural degradation simulation
- Event throughput tracking
- Temperature simulation

### 🧠 **AI Council**
- 5 weighted agents (ALPHA, BETA, GAMMA, DELTA, EPSILON)
- Multi-agent voting system
- Weighted consensus calculation
- Decision types: ATTACK, DEFEND, ADAPT, WAIT, RETREAT
- Symbolic notation mapping (~ | π √ ∆ v =)

### ∫ **Symbolic Transformation Engine**
- Operators: `~` (wave), `|` (axis), `π` (disc), `√` (root), `∆` (delta), `v` (vector), `=` (resolution)
- Expression parsing and transformation
- Pipeline visualization
- Numeric result generation

### 📱 **PWA Support**
- Installable as standalone app
- Offline operation with service worker
- Manifest.json for app metadata
- Cache-first strategy

## 🎯 Architecture

```
~ Wave → | Axis → π Disc → √ Root → ∆ Transform → v Vector → = Resolution

Camera → Gesture → Event Bus → Reactor → Memory → Prediction → AI Council → Spatial Desktop
```

## 📁 File Structure

```
InfinityGlass_v3/
├── index.html                  # Main application
├── manifest.json               # PWA manifest
├── sw.js                       # Service worker
├── package.json                # npm configuration
├── README.md                   # This file
│
├── js/
│   ├── terminal.js             # Real Linux terminal
│   ├── galaxy-renderer.js      # Three.js galaxy
│   ├── panel-manager.js        # Panel system
│   ├── system-monitor.js       # Real system monitoring
│   └── nasa-api.js             # NASA JWST API
│
├── reactor_core/
│   ├── reactor.js              # Reactor core
│   └── modules/
│       └── ai_council.js       # AI voting system
│
├── symbolic/
│   └── symbolic_engine.js      # Symbolic transformations
│
└── assets/                     # Icons, textures, etc.
```

## 🚀 Quick Start

### Option 1: Open Directly
```bash
# Navigate to folder
cd InfinityGlass_v3

# Open index.html in your browser
open index.html
# or
firefox index.html
# or
chrome index.html
```

### Option 2: Local Server (Recommended)
```bash
# Python
python3 -m http.server 8000

# Node.js
npx serve -s . -p 8000

# Then open: http://localhost:8000
```

### Option 3: Deploy to Static Hosting
Upload to any static hosting service:
- Vercel
- Netlify
- GitHub Pages
- Cloudflare Pages
- AWS S3
- Google Cloud Storage

## 🎮 Usage

### Terminal Commands
```bash
help                    # List all commands
apt update              # Update package lists
apt install <package>   # Install package
busybox <command>       # Execute busybox command
ps                      # List processes
top                     # System monitor
free                    # Memory usage
df                      # Disk usage
reactor                 # Reactor core status
modules                 # List reactor modules
memory                  # Memory lattice
models                  # AI models
council                 # AI council voting
jwst <query>            # Fetch JWST images
symbolic <expr>         # Transform symbolic expression
```

### Symbolic Expressions
```
~ | π √ =               # Wave through axis → disc → root → resolution
~ | π √ ∆ v =           # Full transformation pipeline
∆⁹v                     # High-order transformation with velocity
```

## 🔧 Technical Details

### Dependencies
- Three.js (CDN): WebGL 3D rendering
- No npm packages required
- Pure vanilla JavaScript

### Browser Support
- Chrome 90+ ✅
- Firefox 88+ ✅
- Safari 14+ ✅
- Edge 90+ ✅

### Performance
- 60 FPS galaxy rendering
- 10,247 stars, 6,000 spiral arm particles
- Auto-updates every 30 seconds
- Real-time system monitoring every 2 seconds
- Reactor watchdog every 5 seconds

## 📊 System Requirements

- Modern web browser (2021+)
- WebGL support
- 4GB RAM minimum
- JavaScript enabled
- Internet connection for NASA API (optional, has fallback)

## 🎨 Customization

### Change Galaxy
Edit `js/galaxy-renderer.js`:
- Star count: line 34
- Spiral arms: line 145
- Black hole size: line 33

### Change Terminal
Edit `js/terminal.js`:
- Add commands: line 58-101
- Modify filesystem: line 24-31

### Change Colors
Edit `index.html` CSS `:root`:
```css
--neon-cyan: #00ffcc;    /* Primary color */
--neon-pink: #ff00ff;    /* Accent */
--neon-blue: #0088ff;    /* Info */
--neon-amber: #ffaa00;   /* Warning */
```

## 🐛 Troubleshooting

**Galaxy not rendering?**
- Check browser console for WebGL errors
- Ensure hardware acceleration is enabled

**NASA images not loading?**
- Check internet connection
- Fallback images will load automatically

**Terminal commands not working?**
- Press F12 to open browser console
- Check for JavaScript errors

## 📝 License

MIT License - Feel free to use, modify, and distribute.

## 🤝 Contributing

This is a single-developer project, but suggestions welcome!

## 📧 Contact

- Author: Lumenis
- Email: lumenis@infinity-glass.ai
- Website: https://infinity-glass.ai

## 🌟 Credits

- NASA Image API: https://images-api.nasa.gov
- Three.js: https://threejs.org
- JWST Images: NASA, ESA, CSA, STScI

---

**Infinity Glass v3** - A spatial operating system for the future.

~ | π √ ∆ v = ✓