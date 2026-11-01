#!/usr/bin/env node
/**
 * One2lvOS Standalone Server
 * Uses only Node.js built-in modules (http, fs, path)
 * No npm packages required - runs offline
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const PORT = process.env.PORT || 9000;
const PYTHON_PORT = 3002;
const HOST = '0.0.0.0';

// MIME types
const mimeTypes = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
};

// Python backend process
let pythonProcess = null;

function startPythonBackend() {
    console.log('🔋 Starting Python Lumenis Reactor Core...');

    pythonProcess = spawn('python3', ['lumenis-main.py'], {
        cwd: __dirname,
        stdio: ['ignore', 'pipe', 'pipe']
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python] ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error] ${data.toString().trim()}`);
    });

    pythonProcess.on('error', (err) => {
        console.error('❌ Failed to start Python backend:', err.message);
    });

    pythonProcess.on('exit', (code) => {
        console.log(`⚠️  Python backend exited with code ${code}`);
    });
}

// Proxy requests to Python backend
function proxyToPython(req, res) {
    const options = {
        hostname: 'localhost',
        port: PYTHON_PORT,
        path: req.url,
        method: req.method,
        headers: req.headers
    };

    const proxyReq = http.request(options, (proxyRes) => {
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res);
    });

    proxyReq.on('error', (err) => {
        console.error('Proxy error:', err.message);
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            error: 'Backend unavailable',
            message: 'Python reactor core not responding'
        }));
    });

    if (req.method === 'POST' || req.method === 'PUT') {
        req.pipe(proxyReq);
    } else {
        proxyReq.end();
    }
}

// Serve static files
function serveStatic(req, res, filePath) {
    const ext = path.extname(filePath);
    const contentType = mimeTypes[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, data) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404, { 'Content-Type': 'text/html' });
                res.end('<h1>404 Not Found</h1>');
            } else {
                res.writeHead(500);
                res.end('Server Error');
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(data);
        }
    });
}

// Main HTTP server
const server = http.createServer((req, res) => {
    console.log(`${req.method} ${req.url}`);

    // Enable CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // Proxy API requests to Python backend
    if (req.url.startsWith('/api/') || req.url.startsWith('/ws')) {
        proxyToPython(req, res);
        return;
    }

    // Serve root as index.html
    if (req.url === '/' || req.url === '/index.html') {
        const indexPath = path.join(__dirname, 'static', 'index.html');
        if (fs.existsSync(indexPath)) {
            serveStatic(req, res, indexPath);
        } else {
            // Serve embedded demo if index.html doesn't exist
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(getEmbeddedDemo());
        }
        return;
    }

    // Serve static files
    const staticPath = path.join(__dirname, 'static', req.url);
    if (fs.existsSync(staticPath) && fs.statSync(staticPath).isFile()) {
        serveStatic(req, res, staticPath);
        return;
    }

    // 404
    res.writeHead(404, { 'Content-Type': 'text/html' });
    res.end('<h1>404 Not Found</h1>');
});

// Embedded demo HTML (fallback if static files missing)
function getEmbeddedDemo() {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>One2lvOS - Lumenis Reactor Core</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #0a0015 0%, #1a0030 100%);
            color: #00f0ff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .container {
            max-width: 900px;
            width: 90%;
            padding: 40px;
            background: rgba(10, 0, 30, 0.8);
            border: 2px solid #00f0ff;
            border-radius: 12px;
            box-shadow: 0 0 50px rgba(0, 240, 255, 0.3);
        }
        h1 {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 0 0 20px #00f0ff;
        }
        .subtitle {
            text-align: center;
            color: #ff00d4;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .status {
            background: rgba(0, 240, 255, 0.1);
            padding: 20px;
            border-left: 4px solid #00f0ff;
            margin: 20px 0;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(0, 240, 255, 0.2);
        }
        .pulse {
            animation: pulse 2s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #00f0ff, #ff00d4);
            color: #0a0015;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            margin: 10px 5px;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: scale(1.05);
        }
        .center {
            text-align: center;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌷 ONE2LVOS</h1>
        <div class="subtitle">Sovereign Agentic Core - Lumenis Reactor</div>

        <div class="status">
            <div class="status-item">
                <span>System Status:</span>
                <span class="pulse">⚡ ONLINE</span>
            </div>
            <div class="status-item">
                <span>Reactor Core:</span>
                <span>NVIDIA Nemotron-Super-49B</span>
            </div>
            <div class="status-item">
                <span>Temperature:</span>
                <span>0.18°C (Thermal Baseline)</span>
            </div>
            <div class="status-item">
                <span>Node Lattice:</span>
                <span>144,382 Vanguard Nodes</span>
            </div>
            <div class="status-item">
                <span>Gateway:</span>
                <span>Node.js Standalone (Port ${PORT})</span>
            </div>
        </div>

        <div class="center">
            <a href="/api/status" class="btn">📊 System Status</a>
            <a href="http://localhost:${PYTHON_PORT}" class="btn">🔋 Reactor API</a>
        </div>

        <div style="margin-top: 30px; text-align: center; color: #666;">
            <p>Standalone server running with Node.js built-in modules</p>
            <p>No external dependencies required</p>
        </div>
    </div>
</body>
</html>`;
}

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down One2lvOS...');
    if (pythonProcess) {
        pythonProcess.kill();
    }
    server.close(() => {
        console.log('✓ Server stopped');
        process.exit(0);
    });
});

// Start server
server.listen(PORT, HOST, () => {
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║           🌷 ONE2LVOS STANDALONE SERVER                       ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');
    console.log('');
    console.log(`✓ HTTP Server:     http://localhost:${PORT}`);
    console.log(`✓ Python Backend:  http://localhost:${PYTHON_PORT}`);
    console.log(`✓ Mode:            Standalone (no npm packages)`);
    console.log('');
    console.log('Press Ctrl+C to stop');
    console.log('═══════════════════════════════════════════════════════════════');

    // Start Python backend after server is ready
    setTimeout(startPythonBackend, 1000);
});
