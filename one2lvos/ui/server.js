#!/usr/bin/env node
/**
 * ============================================================================
 * ONE2LVOS UI SERVER
 * ============================================================================
 * Express server for serving the One2lvOS web interface
 */

const express = require('express');
const path = require('path');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.UI_PORT || 4000;
const REACTOR_URL = process.env.REACTOR_URL || 'http://localhost:8100';

// CORS middleware
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    next();
});

// Proxy API requests to Reactor Core
app.use('/api', createProxyMiddleware({
    target: REACTOR_URL,
    changeOrigin: true,
    pathRewrite: {
        '^/api': ''
    },
    onError: (err, req, res) => {
        console.error('Proxy Error:', err);
        res.status(500).json({
            error: 'Reactor Core connection failed',
            message: err.message
        });
    }
}));

// Serve static files
app.use(express.static(path.join(__dirname)));

// SPA fallback
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    console.log('╔══════════════════════════════════════════════════════════════════════╗');
    console.log('║                                                                      ║');
    console.log('║       ONE2LVOS UI SERVER - ONLINE                                   ║');
    console.log('║                                                                      ║');
    console.log('╚══════════════════════════════════════════════════════════════════════╝');
    console.log('');
    console.log(`🌐 UI Server:        http://localhost:${PORT}`);
    console.log(`🔋 Reactor Core:     ${REACTOR_URL}`);
    console.log('');
    console.log('Available routes:');
    console.log(`  → http://localhost:${PORT}/          - Main UI`);
    console.log(`  → http://localhost:${PORT}/api/*     - Proxied to Reactor Core`);
    console.log('');
    console.log('Press Ctrl+C to stop');
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🔴 Shutting down UI server...');
    process.exit(0);
});
