/**
 * Desktop Environment & Terminal Subsystem
 * One2lvOS v0.9 - Virtual Terminal, Package Manager, BusyBox, & AI Lobby Panel
 */
class DesktopEnvironment {
    constructor() {
        this.container = document.getElementById('desktop');
        this.windows = [];
        this.terminal = null;
        this.aiLobbyPanel = null;
        this.initialized = false;
    }

    async initialize(state = {}) {
        console.log('[Desktop] Initializing desktop environment');

        // Create desktop UI, terminal, & taskbar
        this.createDesktopUI();
        this.createTerminal();
        this.createAILobbyPanel();
        this.createTaskbar();
        this.createSystemMonitor();

        // Restore saved windows if present
        if (state.windows) {
            state.windows.forEach(winState => {
                this.restoreWindow(winState);
            });
        }

        this.initialized = true;
        console.log('[Desktop] Desktop environment ready');

        // Initial welcome message
        this.terminal.writeLine('One2lvOS v0.9 [Kernel 0.9.4-generic x86_64]', '#00ffff');
        this.terminal.writeLine('BusyBox v1.36.1 multi-call binary installed.', '#ffaa00');
        this.terminal.writeLine('Type "help", "apt", "busybox", or "wget" for available commands.\n', '#00ff00');
        this.terminal.prompt();
    }

    createDesktopUI() {
        this.container.innerHTML = '';
        this.container.style.cssText = `
            width: 100%;
            height: 100%;
            position: relative;
            overflow: hidden;
        `;
    }

    createTerminal() {
        const terminalWindow = document.createElement('div');
        terminalWindow.className = 'window terminal-window';
        terminalWindow.style.cssText = `
            position: absolute;
            left: 50px;
            top: 50px;
            width: 750px;
            height: 480px;
            background: rgba(0, 0, 0, 0.85);
            border: 2px solid #00ffff;
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(0, 255, 255, 0.3);
            backdrop-filter: blur(10px);
            display: flex;
            flex-direction: column;
            z-index: 100;
        `;

        const titleBar = document.createElement('div');
        titleBar.className = 'window-title';
        titleBar.style.cssText = `
            height: 32px;
            background: linear-gradient(135deg, #001a33, #003366);
            border-bottom: 1px solid #00ffff;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            cursor: move;
            user-select: none;
        `;

        titleBar.innerHTML = `
            <span style="color: #00ffff; font-family: 'Courier New', monospace; font-size: 13px;">Terminal - One2lvOS</span>
            <div style="display: flex; gap: 8px;">
                <button class="window-btn minimize" style="width: 20px; height: 20px; background: #ffaa00; border: none; border-radius: 3px; cursor: pointer;"></button>
                <button class="window-btn maximize" style="width: 20px; height: 20px; background: #00ff00; border: none; border-radius: 3px; cursor: pointer;"></button>
                <button class="window-btn close" style="width: 20px; height: 20px; background: #ff0000; border: none; border-radius: 3px; cursor: pointer;"></button>
            </div>
        `;

        const terminalContent = document.createElement('div');
        terminalContent.className = 'terminal-content';
        terminalContent.style.cssText = `
            flex: 1;
            padding: 12px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            color: #00ff00;
        `;

        terminalWindow.appendChild(titleBar);
        terminalWindow.appendChild(terminalContent);
        this.container.appendChild(terminalWindow);

        this.terminal = new Terminal(terminalContent);
        this.makeWindowDraggable(terminalWindow, titleBar);

        titleBar.querySelector('.minimize').addEventListener('click', () => {
            terminalWindow.style.display = 'none';
        });

        titleBar.querySelector('.maximize').addEventListener('click', () => {
            if (terminalWindow.style.width === '100%') {
                terminalWindow.style.cssText = terminalWindow.getAttribute('data-original-style');
            } else {
                terminalWindow.setAttribute('data-original-style', terminalWindow.style.cssText);
                terminalWindow.style.width = '100%';
                terminalWindow.style.height = '100%';
                terminalWindow.style.left = '0';
                terminalWindow.style.top = '0';
            }
        });

        titleBar.querySelector('.close').addEventListener('click', () => {
            terminalWindow.style.display = 'none';
        });
    }

    createAILobbyPanel() {
        const lobbyWindow = document.createElement('div');
        lobbyWindow.className = 'window ai-lobby-window';
        lobbyWindow.style.cssText = `
            position: absolute;
            right: 40px;
            top: 50px;
            width: 420px;
            height: 520px;
            background: rgba(10, 15, 30, 0.9);
            border: 2px solid #ff00ff;
            border-radius: 8px;
            box-shadow: 0 8px 32px rgba(255, 0, 255, 0.35);
            backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            z-index: 101;
            font-family: 'Courier New', monospace;
        `;

        const titleBar = document.createElement('div');
        titleBar.style.cssText = `
            height: 32px;
            background: linear-gradient(135deg, #330033, #660066);
            border-bottom: 1px solid #ff00ff;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            cursor: move;
            user-select: none;
        `;

        titleBar.innerHTML = `
            <span style="color: #ff00ff; font-weight: bold; font-size: 13px;">❖ AI Council Lobby</span>
            <div style="display: flex; gap: 8px;">
                <button class="window-btn close-lobby" style="width: 20px; height: 20px; background: #ff0000; border: none; border-radius: 3px; cursor: pointer;"></button>
            </div>
        `;

        const body = document.createElement('div');
        body.style.cssText = `
            flex: 1;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            overflow-y: auto;
            color: #e0e0e0;
            font-size: 12px;
        `;

        body.innerHTML = `
            <div style="background: rgba(255, 255, 255, 0.05); padding: 8px; border-radius: 4px; border: 1px solid rgba(255, 0, 255, 0.3);">
                <div style="color: #ff00ff; margin-bottom: 4px; font-weight: bold;">[ ACTIVE MODEL HUB ]</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <label>Council Preset:</label>
                    <select id="lobby-model-select" style="background: #111; color: #00ffff; border: 1px solid #00ffff; border-radius: 3px; padding: 2px 4px;">
                        <option value="multi-agent">Multi-Agent Consensus</option>
                        <option value="sentinel">Sentinel Prime</option>
                        <option value="synthesis">Synthesis Core</option>
                    </select>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <label>Temperature:</label>
                    <input type="range" id="lobby-temp" min="0" max="1" step="0.1" value="0.7" style="width: 120px;">
                    <span id="lobby-temp-val" style="color: #00ff00;">0.7</span>
                </div>
            </div>

            <div style="background: rgba(0, 0, 0, 0.4); padding: 8px; border-radius: 4px; border: 1px solid #333;">
                <div style="color: #00ffff; margin-bottom: 6px; font-weight: bold;">[ COUNCIL REASONING NODES ]</div>
                <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                    <span>Sentinel (Health & Autosave)</span>
                    <span style="color: #00ff00;">● ONLINE</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                    <span>Synthesis (Query Processing)</span>
                    <span style="color: #00ff00;">● ONLINE</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                    <span>Agentic Orchestrator</span>
                    <span style="color: #ffaa00;">● STANDBY</span>
                </div>
            </div>

            <div id="lobby-feed" style="
                flex: 1;
                min-height: 140px;
                background: #05050d;
                border: 1px solid #ff00ff;
                border-radius: 4px;
                padding: 8px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 11px;
                color: #ff88ff;
            ">
                <div>[Lobby initialized. Council agents standing by.]</div>
            </div>

            <div style="display: flex; gap: 6px;">
                <input type="text" id="lobby-input" placeholder="Submit query to Council..." style="
                    flex: 1;
                    background: #111;
                    border: 1px solid #ff00ff;
                    color: #fff;
                    padding: 6px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                ">
                <button id="lobby-send" style="
                    background: #660066;
                    color: #fff;
                    border: 1px solid #ff00ff;
                    padding: 0 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: bold;
                ">SEND</button>
            </div>
        `;

        lobbyWindow.appendChild(titleBar);
        lobbyWindow.appendChild(body);
        this.container.appendChild(lobbyWindow);
        this.aiLobbyPanel = lobbyWindow;

        this.makeWindowDraggable(lobbyWindow, titleBar);

        const tempSlider = body.querySelector('#lobby-temp');
        const tempVal = body.querySelector('#lobby-temp-val');
        tempSlider.addEventListener('input', (e) => tempVal.textContent = e.target.value);

        const feed = body.querySelector('#lobby-feed');
        const input = body.querySelector('#lobby-input');
        const sendBtn = body.querySelector('#lobby-send');

        const dispatchQuery = () => {
            const query = input.value.trim();
            if (!query) return;

            const userMsg = document.createElement('div');
            userMsg.style.color = '#00ffff';
            userMsg.textContent = `> ${query}`;
            feed.appendChild(userMsg);

            input.value = '';

            setTimeout(() => {
                const responseMsg = document.createElement('div');
                responseMsg.style.color = '#ff88ff';
                responseMsg.textContent = `[Council] Processing "${query}" across models... Consensus reached.`;
                feed.appendChild(responseMsg);
                feed.scrollTop = feed.scrollHeight;
            }, 600);

            feed.scrollTop = feed.scrollHeight;
        };

        sendBtn.addEventListener('click', dispatchQuery);
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') dispatchQuery(); });

        titleBar.querySelector('.close-lobby').addEventListener('click', () => {
            lobbyWindow.style.display = 'none';
        });
    }

    toggleAILobby() {
        if (!this.aiLobbyPanel) return;
        const currentDisplay = this.aiLobbyPanel.style.display;
        this.aiLobbyPanel.style.display = (currentDisplay === 'none') ? 'flex' : 'none';
    }

    createTaskbar() {
        const taskbar = document.createElement('div');
        taskbar.className = 'taskbar';
        taskbar.style.cssText = `
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 48px;
            background: rgba(0, 0, 0, 0.9);
            border-top: 2px solid #00ffff;
            display: flex;
            align-items: center;
            padding: 0 12px;
            gap: 8px;
            z-index: 1000;
        `;

        taskbar.innerHTML = `
            <div style="color: #00ffff; font-family: 'Courier New', monospace; font-size: 16px; font-weight: bold; padding-right: 12px;">One2lvOS</div>
            <button id="taskbar-lobby-btn" style="
                background: linear-gradient(135deg, #330033, #660066);
                color: #ff00ff;
                border: 1px solid #ff00ff;
                border-radius: 4px;
                padding: 4px 10px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                cursor: pointer;
            ">❖ AI Lobby</button>
            <div style="flex: 1;"></div>
            <div id="system-stats" style="color: #00ffff; font-family: 'Courier New', monospace; font-size: 12px;"></div>
            <div id="clock" style="color: #00ffff; font-family: 'Courier New', monospace; font-size: 13px; padding: 0 16px;"></div>
        `;

        this.container.appendChild(taskbar);

        taskbar.querySelector('#taskbar-lobby-btn').addEventListener('click', () => {
            this.toggleAILobby();
        });

        setInterval(() => {
            const now = new Date();
            const clockEl = document.getElementById('clock');
            if (clockEl) clockEl.textContent = now.toLocaleTimeString();
        }, 1000);
    }

    createSystemMonitor() {
        setInterval(() => {
            if (window.SystemServices && window.SystemServices.getService('telemetry')) {
                const stats = window.SystemServices.getService('telemetry').getMetrics();
                const statsEl = document.getElementById('system-stats');
                if (statsEl) {
                    statsEl.textContent = `FPS: ${stats.fps || 60} | MEM: ${stats.memory || 128}MB | Events: ${stats.events || 0}`;
                }
            }
        }, 1000);
    }

    makeWindowDraggable(windowEl, handleEl) {
        let isDragging = false;
        let startX, startY, initialX, initialY;

        handleEl.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            initialX = windowEl.offsetLeft;
            initialY = windowEl.offsetTop;
            windowEl.style.cursor = 'move';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            windowEl.style.left = (initialX + dx) + 'px';
            windowEl.style.top = (initialY + dy) + 'px';
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
            handleEl.style.cursor = 'default';
        });
    }

    getState() {
        return {
            windows: this.windows.map(win => ({
                type: win.type,
                position: win.position,
                size: win.size
            }))
        };
    }

    restoreWindow(state) {
        console.log('[Desktop] Restoring window:', state);
    }
}


/**
 * Terminal Class - Subsystem Engine & Command Interpreter
 */
class Terminal {
    constructor(container) {
        this.container = container;
        this.history = [];
        this.historyIndex = -1;
        this.isProcessing = false;
        
        // Virtual File System State
        this.vfs = new Map([
            ['index.html', '<!DOCTYPE html><html><head><title>One2lvOS</title></head><body></body></html>'],
            ['manifest.json', '{\n  "name": "One2lvOS",\n  "short_name": "One2lvOS",\n  "start_url": "/",\n  "display": "standalone"\n}'],
            ['README.md', '# One2lvOS Virtual Workspace']
        ]);

        this.repos = [
            'http://repo.one2lvos.org/core/main',
            'http://repo.one2lvos.org/kernel/stable',
            'http://repo.one2lvos.org/thought/registry',
            'http://ftp.us.debian.org/debian/ bookworm main contrib non-free non-free-firmware',
            'http://ftp.us.debian.org/debian/ bookworm main contrib non-free non-free-firmware [src]',
            'http://security.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware',
            'http://security.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware [src]',
            'http://ftp.us.debian.org/debian/ bookworm-updates main contrib non-free non-free-firmware',
            'http://ftp.us.debian.org/debian/ bookworm-updates main contrib non-free non-free-firmware [src]',
            'http://ftp.us.debian.org/debian/ trixie main contrib non-free non-free-firmware',
            'http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware',
            'http://ftp.us.debian.org/debian/ trixie-updates main contrib non-free non-free-firmware',
            'http://repo.steampowered.com/steamos brewmaster main contrib non-free'
        ];
        
        this.installedPackages = new Set(['base-system', 'reactor-core', 'bios-shader', 'busybox']);
        this.availableUpdates = new Map([
            ['reactor-core', { oldVer: '0.9.0', newVer: '0.9.5-rc1', size: '2.4 MB' }],
            ['bios-shader', { oldVer: '1.0.1', newVer: '1.2.0', size: '1.1 MB' }],
            ['agentic-control', { oldVer: '0.8.0', newVer: '1.0.0', size: '4.8 MB' }]
        ]);

        this.repoCatalog = new Map([
            ['cmatrix', { ver: '2.0-1', size: '142 kB', desc: 'Simulated Matrix terminal screen saver' }],
            ['htop', { ver: '3.2.2-1', size: '1.2 MB', desc: 'Interactive process viewer' }],
            ['neofetch', { ver: '7.1.0-2', size: '320 kB', desc: 'System information tool' }],
            ['curl', { ver: '8.1.2-1', size: '890 kB', desc: 'Command line tool for transferring data' }],
            ['steam', { ver: '1.0.0.79-1', size: '3.2 MB', desc: 'Valve Steam gaming platform' }],
            ['gamemode', { ver: '1.7-1', size: '64 kB', desc: 'Optimize Linux system performance for games' }],
            ['mangohud', { ver: '0.7.0-1', size: '1.8 MB', desc: 'Vulkan and OpenGL overlay for monitoring FPS and hardware' }],
            ['proton', { ver: '8.0-3', size: '12.4 MB', desc: 'Windows game compatibility layer based on Wine' }],
            ['wine', { ver: '9.0-1', size: '25.6 MB', desc: 'Run Windows applications on Linux' }],
            ['lutris', { ver: '0.5.17-1', size: '4.5 MB', desc: 'Open gaming platform for managing games' }],
            ['discord', { ver: '0.0.40-1', size: '98 MB', desc: 'Voice and text chat platform for gamers' }]
        ]);

        this.registerCommands();
        this.createInputLine();
    }

    createInputLine() {
        const inputLine = document.createElement('div');
        inputLine.className = 'terminal-input-wrapper';
        inputLine.style.cssText = 'display: flex; align-items: center; margin-top: 4px;';
        inputLine.innerHTML = `
            <span style="color: #00ffff; margin-right: 8px;">root@One2lvOS:~$</span>
            <input type="text" class="terminal-input" style="
                flex: 1;
                background: transparent;
                border: none;
                outline: none;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                font-size: 14px;
            " autofocus>
        `;

        this.container.appendChild(inputLine);
        this.input = inputLine.querySelector('.terminal-input');
        this.input.focus();
        this.input.addEventListener('keydown', (e) => this.handleKeyDown(e));
        
        this.container.addEventListener('click', () => this.input.focus());
    }

    handleKeyDown(e) {
        if (this.isProcessing) {
            e.preventDefault();
            return;
        }

        if (e.key === 'Enter') {
            const command = this.input.value.trim();
            if (command) {
                this.history.push(command);
                this.historyIndex = this.history.length;
                this.executeCommand(command);
            } else {
                this.writeLine('root@One2lvOS:~$', '#00ffff');
            }
            this.input.value = '';
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (this.historyIndex > 0) {
                this.historyIndex--;
                this.input.value = this.history[this.historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (this.historyIndex < this.history.length - 1) {
                this.historyIndex++;
                this.input.value = this.history[this.historyIndex];
            } else {
                this.historyIndex = this.history.length;
                this.input.value = '';
            }
        }
    }

    registerCommands() {
        this.commands = {
            help: () => {
                return `One2lvOS Terminal System Commands:
  help                - Show this help system
  clear               - Clear terminal output
  busybox [applet]    - BusyBox multi-call binary suite
  wget <url>          - Retrieve file from Web or simulate download
  apt <action>        - Package manager (update, upgrade, install <pkg>, add-repo, list)
  lobby / ai-lobby    - Toggle AI Council Lobby Panel
  status              - Check kernel & memory state
  registry            - Query Registry of Thought graph
  council <query>     - Query AI Council subsystem directly
  modules             - List active kernel modules
  save                - Commit system state snapshot
  uname -a            - Print OS kernel information
  ls                  - List directory contents
  cat <file>          - Display file content
  version             - Display One2lvOS build signature`;
            },

            clear: () => {
                this.container.innerHTML = '';
                this.createInputLine();
                return null;
            },

            busybox: (args) => {
                const applets = ['cat', 'chmod', 'cp', 'date', 'echo', 'grep', 'ls', 'mkdir', 'mv', 'ps', 'rm', 'uname', 'wget', 'whoami'];
                if (!args.length) {
                    return `BusyBox v1.36.1 (2026-08-02 00:00:00 UTC) multi-call binary.
Usage: busybox [function] [arguments]...

Currently defined functions:
  ${applets.join(', ')}`;
                }

                const subCmd = args[0].toLowerCase();
                if (applets.includes(subCmd)) {
                    if (subCmd === 'whoami') return 'root';
                    if (subCmd === 'date') return new Date().toUTCString();
                    if (this.commands[subCmd]) {
                        return this.commands[subCmd](args.slice(1));
                    }
                    return `BusyBox: Executed applet '${subCmd}' successfully.`;
                }
                return `busybox: applet not found: ${subCmd}`;
            },

            wget: (args) => {
                if (!args[0]) return 'wget: missing URL\nUsage: wget <URL>';
                this.executeWget(args[0]);
                return null;
            },

            lobby: () => {
                window.DesktopEnvironment.toggleAILobby();
                return '[Desktop] Toggled AI Lobby panel.';
            },

            'ai-lobby': () => {
                window.DesktopEnvironment.toggleAILobby();
                return '[Desktop] Toggled AI Lobby panel.';
            },

            apt: (args) => {
                const subCommand = args[0] ? args[0].toLowerCase() : null;

                if (!subCommand) {
                    return `apt - One2lvOS Advanced Package Tool
Usage:
  apt update           - Synchronize remote package index repositories
  apt upgrade          - Upgrade installed system packages
  apt install <pkg>    - Install a new package from repositories
  apt add-repo <url>   - Append new repository URL to sources list
  apt list             - List available packages and status`;
                }

                if (subCommand === 'update') {
                    this.executeAptUpdate();
                    return null;
                }

                if (subCommand === 'upgrade') {
                    this.executeAptUpgrade();
                    return null;
                }

                if (subCommand === 'install') {
                    const pkgName = args[1] ? args[1].toLowerCase() : null;
                    if (!pkgName) return 'apt install: missing package name. Usage: apt install <package>';
                    this.executeAptInstall(pkgName);
                    return null;
                }

                if (subCommand === 'add-repo') {
                    const repoUrl = args[1];
                    if (!repoUrl) return 'Error: Missing repository URL. Usage: apt add-repo <url>';
                    this.repos.push(repoUrl);
                    return `Added repo: ${repoUrl}\nRepository list updated. Run 'apt update' to sync.`;
                }

                if (subCommand === 'list') {
                    let out = 'Configured Repositories:\n';
                    this.repos.forEach(r => out += `  [src] ${r}\n`);
                    out += '\nAvailable Packages in Repositories:\n';
                    this.repoCatalog.forEach((val, pkg) => {
                        const status = this.installedPackages.has(pkg) ? '[installed]' : '[available]';
                        out += `  ${pkg} (${val.ver}) ${status} - ${val.desc}\n`;
                    });
                    return out;
                }

                return `apt: unknown operation '${subCommand}'. See 'apt --help'.`;
            },

            status: () => {
                const state = window.ReactorCore ? window.ReactorCore.getState() : { timestamp: Date.now(), modules: {} };
                const activeModules = Object.keys(state.modules || {}).filter(k => state.modules[k].enabled).length;
                return `System Status:
  Uptime          : ${Math.floor((Date.now() - (state.timestamp || Date.now())) / 1000)}s
  Active Modules  : ${activeModules} loaded
  Registry Nodes  : ${window.RegistryOfThought?.nodes?.size || 0} mounted
  Memory Usage    : ~142MB / 512MB Virtual Heap`;
            },

            registry: () => {
                const nodes = window.RegistryOfThought?.query() || [];
                return `Registry of Thought: ${nodes.length} nodes connected.`;
            },

            council: (args) => {
                if (!args.length) return 'Usage: council <query message>';
                return `[AI Council] Processing query: "${args.join(' ')}"\nConsensus: System operational. Query logged.`;
            },

            modules: () => {
                const modules = window.ModuleLoader?.listModules() || [];
                return `Loaded Kernel Modules:\n  ${modules.join('\n  ') || 'Base Modules Active'}`;
            },

            save: () => {
                if (window.ReactorCore && window.ReactorCore.saveState) {
                    window.ReactorCore.saveState();
                    return '[Kernel] Snapshot committed to IndexedDB/localStorage.';
                }
                return '[Kernel] Manual save initiated.';
            },

            uname: (args) => {
                if (args[0] === '-a') {
                    return 'One2lvOS 0.9.4-generic #1 SMP PREEMPT Sun Aug 2 00:00:00 UTC 2026 x86_64 Browser/WebGL';
                }
                return 'One2lvOS';
            },

            ls: () => {
                const sysDirs = 'BIOS/  Kernel/  Registry_of_Thought/  Desktop/  Infinity_Glasses/  Interplanetary_Disk/  Agentic_Control/  Flux_Compassator/  Assets/';
                const files = Array.from(this.vfs.keys()).join('  ');
                return `${sysDirs}\n${files}`;
            },

            cat: (args) => {
                if (!args[0]) return 'cat: missing file operand';
                const filename = args[0];
                if (this.vfs.has(filename)) {
                    return this.vfs.get(filename);
                }
                return `cat: ${filename}: No such file or directory`;
            },

            version: () => 'One2lvOS v0.9 (Spatial Aurora Engine)',
        };
    }

    async executeWget(url) {
        this.isProcessing = true;
        this.input.disabled = true;

        const filename = url.split('/').pop() || 'index.html';
        const displayUrl = url.startsWith('http') ? url : `http://${url}`;

        this.writeLine(`--2026-08-02 00:00:00--  ${displayUrl}`, '#aaaaaa');
        this.writeLine(`Resolving ${displayUrl.replace(/https?:\/\//, '').split('/')[0]}... 127.0.0.1`, '#aaaaaa');
        this.writeLine(`Connecting to 127.0.0.1:80... connected.`, '#aaaaaa');
        this.writeLine('HTTP request sent, awaiting response... 200 OK', '#00ff00');
        this.writeLine('Length: 4096 (4.0K) [text/plain]', '#aaaaaa');
        this.writeLine(`Saving to: ‘${filename}’\n`, '#ffffff');

        await this.delay(500);
        this.writeLine(`${filename}        100%[===================>]   4.00K  --.-KB/s    in 0.002s`, '#00ffff');
        await this.delay(300);

        // Commit file to Virtual File System
        this.vfs.set(filename, `/* Downloaded from ${displayUrl} on 2026-08-02 */\nconsole.log("Loaded dynamic payload: ${filename}");`);

        this.writeLine(`\n2026-08-02 00:00:00 (2.00 MB/s) - ‘${filename}’ saved [4096/4096]`, '#00ff00');

        this.isProcessing = false;
        this.input.disabled = false;
        this.prompt();
    }

    async executeAptInstall(pkgName) {
        this.isProcessing = true;
        this.input.disabled = true;

        if (this.installedPackages.has(pkgName)) {
            this.writeLine(`Reading package lists... Done`, '#00ff00');
            this.writeLine(`${pkgName} is already the newest version.`, '#00ff00');
            this.isProcessing = false;
            this.input.disabled = false;
            this.prompt();
            return;
        }

        const pkgInfo = this.repoCatalog.get(pkgName);

        if (!pkgInfo) {
            this.writeLine(`Reading package lists... Done`, '#00ff00');
            this.writeLine(`E: Unable to locate package ${pkgName}`, '#ff0000');
            this.isProcessing = false;
            this.input.disabled = false;
            this.prompt();
            return;
        }

        this.writeLine('Reading package lists... Done', '#00ff00');
        this.writeLine('Building dependency tree... Done', '#00ff00');
        this.writeLine(`The following NEW packages will be installed:\n  ${pkgName}`, '#ffffff');
        this.writeLine(`0 upgraded, 1 newly installed, 0 to remove.`, '#aaaaaa');
        this.writeLine(`Need to get ${pkgInfo.size} of archives.`, '#aaaaaa');

        await this.delay(400);
        this.writeLine(`Get:1 http://repo.one2lvos.org/core/main ${pkgName} ${pkgInfo.ver} [${pkgInfo.size}]...`, '#00ffff');
        await this.delay(500);

        this.writeLine(`Selecting previously unselected package ${pkgName}.`, '#aaaaaa');
        this.writeLine(`(Reading database ... 14201 files and directories currently installed.)`, '#aaaaaa');
        this.writeLine(`Preparing to unpack .../${pkgName}_${pkgInfo.ver}_x86_64.deb ...`, '#aaaaaa');
        await this.delay(300);
        this.writeLine(`Unpacking ${pkgName} (${pkgInfo.ver}) ...`, '#aaaaaa');
        await this.delay(400);
        this.writeLine(`Setting up ${pkgName} (${pkgInfo.ver}) ...`, '#00ff00');
	
	// Mark as installed and dynamically expose as a terminal command
        this.installedPackages.add(pkgName);
        this.commands[pkgName] = () => `[${pkgName}] Application active (${pkgInfo.desc}).`;

        this.writeLine(`\n[✓] Package ${pkgName} installed successfully. Run '${pkgName}' to execute.`, '#00ff00');

        this.isProcessing = false;
        this.input.disabled = false;
        this.prompt();
    }

    async executeAptUpdate() {
        this.isProcessing = true;
        this.input.disabled = true;

        this.writeLine('Hit:1 http://repo.one2lvos.org/core/main Stable InRelease', '#aaaaaa');
        await this.delay(300);

        for (let i = 0; i < this.repos.length; i++) {
            this.writeLine(`Get:${i + 1} ${this.repos[i]} Packages [${(Math.random() * 500 + 100).toFixed(0)} kB]...`, '#00ffff');
            await this.delay(400);
        }

        this.writeLine('Fetched 1,248 kB in 1s (812 kB/s)', '#aaaaaa');
        this.writeLine('Reading package lists... Done', '#00ff00');
        this.writeLine('Building dependency tree... Done', '#00ff00');
        this.writeLine('3 packages can be upgraded. Run \'apt upgrade\' to see them.', '#ffaa00');

        this.isProcessing = false;
        this.input.disabled = false;
        this.prompt();
    }

    async executeAptUpgrade() {
        if (this.availableUpdates.size === 0) {
            this.writeLine('Reading package lists... Done', '#00ff00');
            this.writeLine('0 upgraded, 0 newly installed, 0 to remove.', '#00ff00');
            return;
        }

        this.isProcessing = true;
        this.input.disabled = true;

        this.writeLine('Reading package lists... Done', '#00ff00');
        this.writeLine('Building dependency tree... Done', '#00ff00');
        this.writeLine('The following packages will be upgraded:', '#ffffff');
        
        let pkgList = '';
        this.availableUpdates.forEach((_, pkg) => pkgList += `  ${pkg}`);
        this.writeLine(pkgList, '#00ffff');

        this.writeLine('Need to get 8.3 MB of archives.', '#aaaaaa');
        this.writeLine('Unpacking updates...', '#aaaaaa');
        await this.delay(600);

        for (const [pkg, details] of this.availableUpdates.entries()) {
            this.writeLine(`Preparing to unpack .../${pkg}_${details.newVer}_all.deb ...`, '#aaaaaa');
            await this.delay(300);
            this.writeLine(`Unpacking ${pkg} (${details.newVer}) over (${details.oldVer}) ...`, '#aaaaaa');
            await this.delay(400);
            this.writeLine(`Setting up ${pkg} (${details.newVer}) ...`, '#00ff00');
            this.installedPackages.add(pkg);
        }

        this.availableUpdates.clear();
        this.writeLine('\n[✓] Upgrade complete. Kernel subsystems refreshed.', '#00ff00');

        this.isProcessing = false;
        this.input.disabled = false;
        this.prompt();
    }

    async executeCommand(command) {
        this.writeLine(`root@One2lvOS:~$ ${command}`, '#00ffff');

        const [cmd, ...args] = command.split(' ');
        const handler = this.commands[cmd.toLowerCase()];

        if (handler) {
            const result = handler(args);
            if (result) {
                this.writeLine(result);
            }
        } else {
            this.writeLine(`bash: ${cmd}: command not found`, '#ff0000');
        }

        if (!this.isProcessing) {
            this.prompt();
        }
    }

    writeLine(text, color = '#00ff00') {
        const line = document.createElement('div');
        line.style.color = color;
        line.style.whiteSpace = 'pre-wrap';
        line.textContent = text;

        const inputLineWrapper = this.container.querySelector('.terminal-input-wrapper');
        if (inputLineWrapper) {
            this.container.insertBefore(line, inputLineWrapper);
        } else {
            this.container.appendChild(line);
        }

        this.container.scrollTop = this.container.scrollHeight;
    }

    prompt() {
        if (this.input) {
            this.input.focus();
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Instantiate global desktop instance
window.DesktopEnvironment = new DesktopEnvironment();
