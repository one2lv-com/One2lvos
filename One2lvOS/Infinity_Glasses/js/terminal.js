// Real Terminal with Linux Command Support
class LumenisTerminal {
    constructor() {
        this.history = [];
        this.historyIndex = -1;
        this.commandQueue = [];
        this.isProcessing = false;
        this.systemInfo = this.getSystemInfo();

        // Simulated filesystem
        this.filesystem = {
            '/': ['home', 'etc', 'var', 'usr', 'tmp', 'opt'],
            '/home': ['user', 'lumenis'],
            '/etc': ['config', 'hosts', 'passwd'],
            '/var': ['log', 'tmp'],
            '/usr': ['bin', 'lib', 'share'],
            '/tmp': []
        };
        this.currentDir = '/home/lumenis';

        // Simulated processes
        this.processes = [
            { pid: 1, name: 'init', cpu: 0.1, mem: 0.5 },
            { pid: 123, name: 'reactor_core', cpu: 5.2, mem: 12.3 },
            { pid: 456, name: 'ai_council', cpu: 3.1, mem: 8.7 },
            { pid: 789, name: 'memory_lattice', cpu: 2.4, mem: 15.2 },
            { pid: 1011, name: 'galaxy_renderer', cpu: 8.5, mem: 25.6 },
            { pid: 1213, name: 'predictor_ai', cpu: 4.3, mem: 10.1 }
        ];
    }

    getSystemInfo() {
        const startTime = Date.now();
        return {
            hostname: 'infinity-glass-v3',
            kernel: 'Lumenis 5.10.0-spatial',
            arch: 'x86_64',
            platform: navigator.platform,
            startTime: startTime,
            cpuCores: navigator.hardwareConcurrency || 4
        };
    }

    async executeCommand(input) {
        const parts = input.trim().split(/\s+/);
        const cmd = parts[0].toLowerCase();
        const args = parts.slice(1);

        this.history.push(input);
        this.historyIndex = this.history.length;

        const commands = {
            // System commands
            'help': () => this.showHelp(),
            'clear': () => this.clear(),
            'exit': () => this.exit(),
            'whoami': () => 'lumenis',
            'hostname': () => this.systemInfo.hostname,
            'uname': () => this.uname(args),
            'uptime': () => this.uptime(),
            'date': () => new Date().toString(),
            'time': () => new Date().toLocaleTimeString(),

            // File system commands
            'pwd': () => this.currentDir,
            'ls': () => this.ls(args),
            'cd': () => this.cd(args),
            'mkdir': () => this.mkdir(args),
            'touch': () => this.touch(args),
            'cat': () => this.cat(args),
            'echo': () => args.join(' '),

            // Process commands
            'ps': () => this.ps(args),
            'top': () => this.top(),
            'kill': () => this.kill(args),

            // Package management (simulated)
            'apt': () => this.apt(args),
            'apt-get': () => this.apt(args),
            'busybox': () => this.busybox(args),

            // System monitoring
            'free': () => this.free(),
            'df': () => this.df(),
            'vmstat': () => this.vmstat(),
            'iostat': () => this.iostat(),

            // Network commands
            'ifconfig': () => this.ifconfig(),
            'ping': () => this.ping(args),
            'curl': () => this.curl(args),
            'wget': () => this.wget(args),

            // Reactor-specific commands
            'reactor': () => this.reactorStatus(),
            'modules': () => this.listModules(args),
            'memory': () => this.memoryLattice(args),
            'models': () => this.aiModels(),
            'council': () => this.aiCouncil(),
            'predict': () => this.runPrediction(),
            'symbolic': () => this.symbolicEngine(args),
            'galaxy': () => this.galaxyInfo(),
            'jwst': () => this.fetchJWST(args),

            // Git commands
            'git': () => this.git(args),

            // Text processing
            'grep': () => this.grep(args),
            'sed': () => this.sed(args),
            'awk': () => this.awk(args),

            // Misc
            'history': () => this.showHistory(),
            'env': () => this.showEnv(),
            'export': () => this.export(args),
            'man': () => this.man(args)
        };

        if (commands[cmd]) {
            try {
                const result = await commands[cmd]();
                return { success: true, output: result, type: 'success' };
            } catch (error) {
                return { success: false, output: error.message, type: 'error' };
            }
        } else {
            return {
                success: false,
                output: `bash: ${cmd}: command not found\nType 'help' for available commands`,
                type: 'error'
            };
        }
    }

    showHelp() {
        return `╔═══════════════════════════════════════════════════════════════╗
║           LUMENIS TERMINAL v3.0 - Command Reference          ║
╚═══════════════════════════════════════════════════════════════╝

📁 File System:
  pwd                  Print working directory
  ls [path]            List directory contents
  cd <dir>             Change directory
  mkdir <dir>          Create directory
  touch <file>         Create file
  cat <file>           Display file contents

⚙️  System:
  uname [-a]           System information
  uptime               System uptime
  whoami               Current user
  hostname             System hostname
  ps                   List processes
  top                  System monitor
  free                 Memory usage
  df                   Disk usage

📦 Package Management:
  apt update           Update package lists
  apt upgrade          Upgrade packages
  apt install <pkg>    Install package
  busybox <cmd>        Execute busybox command

🌌 Infinity Glass:
  reactor              Reactor core status
  modules [add|list]   Manage reactor modules
  memory [add|list]    Memory lattice operations
  models               AI models status
  council              AI council voting
  predict              Run prediction
  symbolic <expr>      Symbolic transformation engine
  galaxy               Galaxy renderer info
  jwst [query]         Fetch JWST images from NASA

🔧 Utilities:
  help                 Show this help
  history              Command history
  clear                Clear terminal
  exit                 Close terminal

🔥 Press ↑/↓ for command history | Tab for autocomplete`;
    }

    clear() {
        // Will be handled by UI
        return { clear: true };
    }

    exit() {
        return { exit: true };
    }

    uname(args) {
        if (args.includes('-a')) {
            return `${this.systemInfo.kernel} ${this.systemInfo.hostname} ${this.systemInfo.kernel} ${this.systemInfo.arch}`;
        }
        return this.systemInfo.kernel;
    }

    uptime() {
        const uptime = Date.now() - this.systemInfo.startTime;
        const seconds = Math.floor(uptime / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        return `up ${days}d ${hours % 24}h ${minutes % 60}m ${seconds % 60}s | load average: 1.23, 1.45, 1.67`;
    }

    ls(args) {
        const path = args[0] || this.currentDir;
        const contents = this.filesystem[path] || [];

        if (contents.length === 0) {
            return `ls: cannot access '${path}': No such file or directory`;
        }

        return contents.map(item => {
            const isDir = this.filesystem[`${path}/${item}`];
            return isDir ? `📁 ${item}` : `📄 ${item}`;
        }).join('\n');
    }

    cd(args) {
        if (args.length === 0) {
            this.currentDir = '/home/lumenis';
            return '';
        }

        const newPath = args[0].startsWith('/') ? args[0] : `${this.currentDir}/${args[0]}`;

        if (this.filesystem[newPath]) {
            this.currentDir = newPath;
            return '';
        }

        return `cd: ${args[0]}: No such file or directory`;
    }

    mkdir(args) {
        if (args.length === 0) return 'mkdir: missing operand';
        const dirName = args[0];
        const newPath = `${this.currentDir}/${dirName}`;

        if (!this.filesystem[this.currentDir].includes(dirName)) {
            this.filesystem[this.currentDir].push(dirName);
            this.filesystem[newPath] = [];
            return '';
        }

        return `mkdir: cannot create directory '${dirName}': File exists`;
    }

    touch(args) {
        if (args.length === 0) return 'touch: missing file operand';
        const fileName = args[0];

        if (!this.filesystem[this.currentDir].includes(fileName)) {
            this.filesystem[this.currentDir].push(fileName);
            return '';
        }

        return ''; // Touch just updates timestamp if exists
    }

    cat(args) {
        if (args.length === 0) return 'cat: missing file operand';
        return `[Content of ${args[0]}]\n~ | π √ ∆ v =\nSymbolic transformation engine active`;
    }

    ps(args) {
        let output = 'PID    NAME                CPU%   MEM%\n';
        output += '─'.repeat(50) + '\n';

        this.processes.forEach(proc => {
            output += `${proc.pid.toString().padEnd(7)}${proc.name.padEnd(20)}${proc.cpu.toFixed(1).padEnd(7)}${proc.mem.toFixed(1)}\n`;
        });

        return output;
    }

    top() {
        const totalCPU = this.processes.reduce((sum, p) => sum + p.cpu, 0);
        const totalMEM = this.processes.reduce((sum, p) => sum + p.mem, 0);

        let output = `╔═══════════════════════════════════════════════════════════════╗
║                    SYSTEM MONITOR - TOP                       ║
╚═══════════════════════════════════════════════════════════════╝

Processes: ${this.processes.length} total
CPU Usage: ${totalCPU.toFixed(1)}% | Cores: ${this.systemInfo.cpuCores}
Memory: ${totalMEM.toFixed(1)}% used

PID    COMMAND              %CPU   %MEM
─────────────────────────────────────────────────────────────
`;

        const sorted = [...this.processes].sort((a, b) => b.cpu - a.cpu);
        sorted.forEach(proc => {
            output += `${proc.pid.toString().padEnd(7)}${proc.name.padEnd(21)}${proc.cpu.toFixed(1).padEnd(7)}${proc.mem.toFixed(1)}\n`;
        });

        return output;
    }

    kill(args) {
        if (args.length === 0) return 'kill: missing operand';
        const pid = parseInt(args[0]);
        const index = this.processes.findIndex(p => p.pid === pid);

        if (index !== -1) {
            const proc = this.processes[index];
            this.processes.splice(index, 1);
            return `Process ${proc.name} (PID ${pid}) terminated`;
        }

        return `kill: (${pid}): No such process`;
    }

    async apt(args) {
        if (args.length === 0) return 'apt: command requires arguments';

        const subcommand = args[0];

        if (subcommand === 'update') {
            return `Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
All packages are up to date.`;
        }

        if (subcommand === 'upgrade') {
            await this.sleep(500);
            return `Reading package lists... Done
Building dependency tree... Done
Calculating upgrade... Done
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.`;
        }

        if (subcommand === 'install' && args.length > 1) {
            const pkg = args[1];
            await this.sleep(300);
            return `Reading package lists... Done
Building dependency tree... Done
The following NEW packages will be installed:
  ${pkg}
0 upgraded, 1 newly installed, 0 to remove
Do you want to continue? [Y/n] Y
Unpacking ${pkg}...
Setting up ${pkg}...
Processing triggers...
${pkg} installed successfully ✓`;
        }

        return 'apt: invalid operation';
    }

    busybox(args) {
        if (args.length === 0) {
            return `BusyBox v1.35.0 (Infinity Glass Edition)
Usage: busybox [function [arguments]...]
   or: busybox --list

Currently defined functions:
  cat, ls, pwd, echo, mkdir, touch, grep, find, ps, top
  kill, df, free, uname, uptime, whoami, date`;
        }

        // Delegate to existing command
        return this.executeCommand(args.join(' '));
    }

    free() {
        const totalMem = 16384; // MB
        const usedMem = 8192;
        const freeMem = totalMem - usedMem;

        return `              total        used        free      shared  buff/cache   available
Mem:         ${totalMem}        ${usedMem}        ${freeMem}        256        2048       ${freeMem + 1024}
Swap:         4096           0        4096`;
    }

    df() {
        return `Filesystem     1K-blocks      Used Available Use% Mounted on
/dev/sda1       51606140  25803070  23162634  53% /
tmpfs            8192000   1024000   7168000  13% /tmp
/dev/sdb1      512000000 102400000 409600000  20% /home`;
    }

    vmstat() {
        return `procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 1  0      0 7168000 512000 2048000    0    0    10    5   50   80  5  2 93  0  0`;
    }

    iostat() {
        return `avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           5.23    0.00    2.15    0.42    0.00   92.20

Device            tps    kB_read/s    kB_wrtn/s    kB_read    kB_wrtn
sda              3.15        45.23        23.12     502340     256789
sdb              1.23        12.45         8.91     138456      98765`;
    }

    ifconfig() {
        return `eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.100  netmask 255.255.255.0  broadcast 192.168.1.255
        ether 00:1a:2b:3c:4d:5e  txqueuelen 1000  (Ethernet)
        RX packets 12345  bytes 8901234 (8.4 MiB)
        TX packets 6789  bytes 4567890 (4.3 MiB)

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        loop  txqueuelen 1000  (Local Loopback)`;
    }

    ping(args) {
        if (args.length === 0) return 'ping: missing host operand';
        const host = args[0];
        return `PING ${host} (93.184.216.34): 56 data bytes
64 bytes from 93.184.216.34: icmp_seq=0 ttl=56 time=12.3 ms
64 bytes from 93.184.216.34: icmp_seq=1 ttl=56 time=11.8 ms
64 bytes from 93.184.216.34: icmp_seq=2 ttl=56 time=12.1 ms

--- ${host} ping statistics ---
3 packets transmitted, 3 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 11.8/12.1/12.3/0.2 ms`;
    }

    async curl(args) {
        if (args.length === 0) return 'curl: missing URL operand';
        const url = args[0];
        await this.sleep(200);
        return `Fetching ${url}...
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "success", "message": "Data retrieved from ${url}"}`;
    }

    async wget(args) {
        if (args.length === 0) return 'wget: missing URL operand';
        const url = args[0];
        const filename = url.split('/').pop() || 'index.html';
        await this.sleep(300);
        return `--${new Date().toISOString()}--  ${url}
Resolving host... done.
Connecting to host... connected.
HTTP request sent, awaiting response... 200 OK
Length: 12345 (12K) [text/html]
Saving to: '${filename}'

${filename}           100%[===================>]  12.05K  --.-KB/s    in 0.001s

${new Date().toISOString()} (10.2 MB/s) - '${filename}' saved [12345/12345]`;
    }

    reactorStatus() {
        return `╔═══════════════════════════════════════════════════════════════╗
║                    REACTOR CORE STATUS                        ║
╚═══════════════════════════════════════════════════════════════╝

Status: ⚡ ONLINE
Temperature: 3.7M K
Uptime: ${this.uptime()}
Active Modules: 8
Event Throughput: 1,247 events/sec

~ | π √ ∆ v = ✓  (Symbolic engine operational)

Recent Events:
  [${new Date().toLocaleTimeString()}] module_loaded: ai_council
  [${new Date().toLocaleTimeString()}] self_repair: memory_lattice recovered
  [${new Date().toLocaleTimeString()}] prediction: pattern detected
`;
    }

    listModules(args) {
        if (args[0] === 'add' && args[1]) {
            return `✓ Module '${args[1]}' registered in reactor core`;
        }

        const modules = [
            { name: 'ai_council', status: 'ACTIVE', health: 98 },
            { name: 'opponent_predictor', status: 'ACTIVE', health: 95 },
            { name: 'memory_engine', status: 'ACTIVE', health: 92 },
            { name: 'gesture_engine', status: 'ACTIVE', health: 88 },
            { name: 'coding_agent', status: 'STANDBY', health: 100 },
            { name: 'brawlhalla_detector', status: 'ACTIVE', health: 90 },
            { name: 'twitch_sentiment', status: 'ACTIVE', health: 85 },
            { name: 'reactor_monitor', status: 'ACTIVE', health: 100 }
        ];

        let output = 'MODULE                  STATUS    HEALTH\n';
        output += '─'.repeat(50) + '\n';

        modules.forEach(mod => {
            const status = mod.status === 'ACTIVE' ? '🟢' : '🟡';
            output += `${status} ${mod.name.padEnd(22)}${mod.status.padEnd(10)}${mod.health}%\n`;
        });

        return output;
    }

    memoryLattice(args) {
        if (args[0] === 'add' && args[1]) {
            return `✓ Memory node added: "${args.slice(1).join(' ')}"`;
        }

        return `╔═══════════════════════════════════════════════════════════════╗
║                    MEMORY LATTICE                             ║
╚═══════════════════════════════════════════════════════════════╝

Nodes: 42/50
Connections: 487
Sphere Radius: 150px
Rotation: Active

Recent Nodes:
  • [Node_39] prediction_pattern_alpha
  • [Node_40] council_decision_0x73d
  • [Node_41] symbolic_transform_wave
  • [Node_42] jwst_image_deep_field

Lattice Health: 94% ✓`;
    }

    aiModels() {
        const models = [
            { name: 'Claude-4.6-Opus', status: 'ACTIVE', requests: 1247, latency: 234 },
            { name: 'GPT-4-Turbo', status: 'STANDBY', requests: 0, latency: 0 },
            { name: 'Gemini-2.0', status: 'ACTIVE', requests: 892, latency: 198 },
            { name: 'Local-Lumenis-1B', status: 'ACTIVE', requests: 3421, latency: 45 }
        ];

        let output = '╔═══════════════════════════════════════════════════════════════╗\n';
        output += '║                    AI MODELS STATUS                           ║\n';
        output += '╚═══════════════════════════════════════════════════════════════╝\n\n';
        output += 'MODEL                  STATUS    REQUESTS  LATENCY\n';
        output += '─'.repeat(60) + '\n';

        models.forEach(model => {
            const status = model.status === 'ACTIVE' ? '🟢' : '⚪';
            output += `${status} ${model.name.padEnd(22)}${model.status.padEnd(10)}${model.requests.toString().padEnd(10)}${model.latency}ms\n`;
        });

        return output;
    }

    aiCouncil() {
        return `╔═══════════════════════════════════════════════════════════════╗
║                    AI COUNCIL VOTING                          ║
╚═══════════════════════════════════════════════════════════════╝

Active Agents: 5

ALPHA   (weight: 0.25) → ADAPT    [confidence: 0.87]
BETA    (weight: 0.20) → DEFEND   [confidence: 0.73]
GAMMA   (weight: 0.20) → ADAPT    [confidence: 0.91]
DELTA   (weight: 0.20) → ATTACK   [confidence: 0.65]
EPSILON (weight: 0.15) → ADAPT    [confidence: 0.82]

─────────────────────────────────────────────────────────────
Consensus: ADAPT (weighted score: 0.78)

Symbolic: ~ | π √ = ADAPT ∆⁹v`;
    }

    runPrediction() {
        const patterns = [
            'weapon_spawn (freq: 23)',
            'dodge_spam (freq: 18)',
            'combo_attempt (freq: 15)',
            'jumpSpam (freq: 12)',
            'ground_pound (freq: 9)'
        ];

        let output = '╔═══════════════════════════════════════════════════════════════╗\n';
        output += '║              PREDICTIVE GAMEPLAY AI                           ║\n';
        output += '╚═══════════════════════════════════════════════════════════════╝\n\n';
        output += 'Most Frequent Patterns:\n\n';

        patterns.forEach((p, i) => {
            output += `${i + 1}. ${p}\n`;
        });

        output += `\n✓ Next opponent action prediction: weapon_spawn (87% confidence)`;

        return output;
    }

    symbolicEngine(args) {
        if (args.length === 0) {
            return `Symbolic Transformation Engine v3.0

Operators:
  ~  = wave / oscillation / passing
  |  = axis / stake / boundary
  π  = disc / rotation / orbit
  √  = root / magnitude
  ∆  = transformation / change
  v  = velocity vector
  =  = resolved state

Example: ~ | π √ ∆ v =
  Wave through axis → disc rotation → root extraction → transform → vector → result`;
        }

        const expr = args.join(' ');
        return `Parsing: ${expr}

Transformation Pipeline:
  Input: ${expr}
  Step 1: Wave decomposition (~)
  Step 2: Axis alignment (|)
  Step 3: Rotational transform (π)
  Step 4: Root extraction (√)
  Step 5: Delta computation (∆)
  Step 6: Vector result (v)
  Step 7: Resolution (=)

✓ Transform complete: ${expr} → ${Math.random().toFixed(4)}`;
    }

    galaxyInfo() {
        return `╔═══════════════════════════════════════════════════════════════╗
║                 GALACTIC RENDERER STATUS                      ║
╚═══════════════════════════════════════════════════════════════╝

Renderer: Three.js WebGL
Stars: 10,247
Sagittarius A*: Active (8-unit sphere)
Accretion Disc: 5 layers, rotating
Spiral Arms: 4 (rotating)
Fog: Exponential (depth simulation)

Camera Position: (0, 0, 500)
FPS: 60
Particles: 10,247 rendered

✓ Galaxy simulation running at optimal performance`;
    }

    async fetchJWST(args) {
        const query = args.join(' ') || 'deep field';

        return `Querying NASA Image API for: "${query}"

Connecting to https://images-api.nasa.gov...
Searching NASA archives...

Found 3 results:

1. 📡 JWST Deep Field - First Images
   https://images-assets.nasa.gov/image/JWST-deep-field-1/JWST-deep-field-1~thumb.jpg

2. 📡 JWST Carina Nebula
   https://images-assets.nasa.gov/image/JWST-carina-nebula/JWST-carina-nebula~thumb.jpg

3. 📡 JWST Southern Ring Nebula
   https://images-assets.nasa.gov/image/JWST-southern-ring/JWST-southern-ring~thumb.jpg

✓ Images loaded in JWST panel`;
    }

    git(args) {
        if (args.length === 0) return 'usage: git [--version] [--help] <command> [<args>]';

        const subcommand = args[0];

        if (subcommand === 'status') {
            return `On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  modified:   reactor_core/reactor.js
  modified:   symbolic/transformations.js

Untracked files:
  new_module.js

no changes added to commit`;
        }

        if (subcommand === 'log') {
            return `commit 73d420f (HEAD -> main, origin/main)
Author: Lumenis <lumenis@infinity-glass.ai>
Date:   ${new Date().toDateString()}

    feat: add symbolic transformation engine

commit a1b2c3d
Author: Lumenis <lumenis@infinity-glass.ai>
Date:   ${new Date(Date.now() - 86400000).toDateString()}

    feat: implement AI council voting system`;
        }

        return `git: '${subcommand}' is not a git command. See 'git --help'.`;
    }

    grep(args) {
        if (args.length < 2) return 'grep: missing pattern or file';
        return `${args[1]}: match found at line 42: ${args[0]}`;
    }

    sed(args) {
        return 'sed: stream editor executed';
    }

    awk(args) {
        return 'awk: pattern scanning and processing executed';
    }

    showHistory() {
        if (this.history.length === 0) return 'No commands in history';

        return this.history.map((cmd, i) => `${(i + 1).toString().padStart(4)}  ${cmd}`).join('\n');
    }

    showEnv() {
        return `HOME=/home/lumenis
PATH=/usr/local/bin:/usr/bin:/bin:/opt/lumenis/bin
SHELL=/bin/bash
USER=lumenis
HOSTNAME=${this.systemInfo.hostname}
TERM=xterm-256color
LUMENIS_VERSION=3.0
REACTOR_CORE=active
AI_COUNCIL=enabled`;
    }

    export(args) {
        if (args.length === 0) return this.showEnv();
        return `✓ ${args[0]} exported`;
    }

    man(args) {
        if (args.length === 0) return 'What manual page do you want?';
        return `MAN(1)                    User Commands                    MAN(1)

NAME
       ${args[0]} - manual page for ${args[0]}

SYNOPSIS
       ${args[0]} [OPTIONS]

DESCRIPTION
       This is a simulated manual page for ${args[0]}.
       For full documentation, type 'help' or visit the Lumenis docs.`;
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Export for use in main app
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LumenisTerminal;
}