/**
 * One2lvOS Network Service
 * Manages static connections and mesh routing with WebDAV/FTP integration
 */

const MeshRouter = require('./mesh-routing');
const WebDAVHandler = require('./protocols/webdav-handler');
const FTPHandler = require('./protocols/ftp-handler');
const fs = require('fs').promises;
const path = require('path');
const fsSync = require('fs');

// Built-in connection to this machine's own WebDAV server (webdav_server.py, :8090).
// Its login is the AI Lobby admin login, read at connect time and never saved here.
const LOBBY_CONFIG = path.join(__dirname, '../ai-lobby/data/config.json');
const BUILTIN_ID = 'one2lv-files';
const BUILTIN = {
    id: BUILTIN_ID,
    name: 'One2lvOS Files (this server)',
    protocol: 'webdav',
    host: '127.0.0.1',
    port: parseInt(process.env.WEBDAV_PORT || '8090', 10),
    path: '/',
    builtin: true,
    persistent: false,
    autoReconnect: true
};
function lobbyAdminCredentials() {
    const a = JSON.parse(fsSync.readFileSync(LOBBY_CONFIG, 'utf8')).admin;
    return { username: String(a.username), password: String(a.password) };
}

// What the API may show: never passwords, handles or timers.
function publicView(c) {
    if (!c) return c;
    return {
        id: c.id, name: c.name || null, protocol: c.protocol, host: c.host, port: c.port,
        path: c.path || '/', secure: !!c.secure, builtin: !!c.builtin, status: c.status,
        lastError: c.lastError || null, lastConnected: c.lastConnected || null, created: c.created,
        username: c.builtin ? '(AI Lobby admin)' : ((c.credentials && c.credentials.username) || null),
        persistent: !!c.persistent, autoReconnect: !!c.autoReconnect
    };
}

class NetworkService {
    constructor() {
        this.router = new MeshRouter();
        this.configFile = path.join(__dirname, '../config/connections.json');
        this.initialized = false;
    }

    /**
     * Initialize network service
     */
    async initialize() {
        if (this.initialized) return;

        // Register protocol handlers
        this.router.registerProtocol('webdav', new WebDAVHandler());
        this.router.registerProtocol('ftp', new FTPHandler());

        // Register local node
        this.router.registerNode('local', {
            name: 'One2lvOS Local Node',
            type: 'host',
            capabilities: ['webdav', 'ftp', 'routing']
        });

        // Load saved connections
        await this.loadConnections();

        // Built-in connection to the local WebDAV server
        await this.ensureBuiltin();

        this.initialized = true;
        console.log('[NetworkService] Initialized successfully');
    }

    /**
     * Load connections from config file
     */
    async loadConnections() {
        try {
            const data = await fs.readFile(this.configFile, 'utf8');
            const config = JSON.parse(data);

            for (const conn of config.connections || []) {
                if (conn.builtin || conn.id === BUILTIN_ID) continue;
                try {
                    await this.createConnection(conn);
                } catch (error) {
                    console.error(`[NetworkService] Failed to restore connection ${conn.id}:`, error.message);
                }
            }

            console.log(`[NetworkService] Loaded ${config.connections?.length || 0} connections`);
        } catch (error) {
            if (error.code === 'ENOENT') {
                console.log('[NetworkService] No saved connections found');
                await this.saveConnections();
            } else {
                console.error('[NetworkService] Error loading connections:', error);
            }
        }
    }

    /**
     * Save connections to config file
     */
    async saveConnections() {
        try {
            const connections = this.router.getConnections().filter(c => !c.builtin && !String(c.id).startsWith('test_')).map(conn => ({
                id: conn.id,
                name: conn.name || null,
                secure: !!conn.secure,
                protocol: conn.protocol,
                host: conn.host,
                port: conn.port,
                path: conn.path,
                credentials: conn.credentials,
                persistent: conn.persistent,
                autoReconnect: conn.autoReconnect
            }));

            const config = { connections };

            // Ensure config directory exists
            await fs.mkdir(path.dirname(this.configFile), { recursive: true });
            // Saved logins for other servers live here, so keep the file private.
            await fs.writeFile(this.configFile, JSON.stringify(config, null, 2), { mode: 0o600 });
            await fs.chmod(this.configFile, 0o600).catch(() => {});

            console.log('[NetworkService] Connections saved');
        } catch (error) {
            console.error('[NetworkService] Error saving connections:', error);
        }
    }

    /**
     * Create a new connection
     */
    async createConnection(config) {
        const cfg = { ...(config || {}) };
        delete cfg.builtin;
        if (cfg.id === BUILTIN_ID) delete cfg.id;
        const connection = this.router.createStaticConnection(cfg);
        await this.saveConnections();
        return connection;
    }

    async ensureBuiltin() {
        if (this.router.getConnection(BUILTIN_ID)) return;
        const c = this.router.createStaticConnection({ ...BUILTIN });
        c.resolveCredentials = lobbyAdminCredentials;
        c.persistent = true;
        await this.router.connect(BUILTIN_ID).catch(e =>
            console.error('[NetworkService] Built-in WebDAV not reachable yet:', e.message));
    }

    /**
     * Connect to a connection
     */
    async connect(connectionId) {
        return this.router.connect(connectionId);
    }

    /**
     * Disconnect from a connection
     */
    async disconnect(connectionId) {
        await this.router.disconnect(connectionId);
        await this.saveConnections();
    }

    /**
     * Remove a connection
     */
    async removeConnection(connectionId) {
        if (connectionId === BUILTIN_ID) throw new Error('The built-in One2lvOS Files connection cannot be removed');
        await this.router.removeConnection(connectionId);
        await this.saveConnections();
    }

    /**
     * Get all connections
     */
    getConnections() {
        return this.router.getConnections().filter(c => !String(c.id).startsWith('test_')).map(publicView);
    }

    /**
     * Get connection by ID
     */
    getConnection(connectionId) {
        return publicView(this.router.getConnection(connectionId));
    }

    /**
     * Get network statistics
     */
    getStats() {
        return this.router.getStats();
    }

    /**
     * Execute operation on a connection
     */
    async executeOperation(connectionId, operation, ...args) {
        const connection = this.router.getConnection(connectionId);
        if (!connection) {
            throw new Error(`Connection ${connectionId} not found`);
        }

        if (connection.status !== 'connected') {
            // Connect on demand (e.g. after a restart) instead of failing outright.
            await this.router.connect(connectionId);
        }

        const handler = this.router.protocols.get(connection.protocol);
        if (!handler || typeof handler[operation] !== 'function') {
            throw new Error(`Operation ${operation} not supported for protocol ${connection.protocol}`);
        }

        return handler[operation](connection.handle, ...args);
    }

    /**
     * WebDAV operations
     */
    async webdavList(connectionId, remotePath = '/') {
        const result = await this.executeOperation(connectionId, 'propfind', remotePath, 1);
        const handler = this.router.protocols.get('webdav');
        const conn = this.router.getConnection(connectionId);
        return handler.parseXmlResponse(result.body, conn.handle, remotePath);
    }

    async webdavMove(connectionId, fromPath, toPath) {
        return this.executeOperation(connectionId, 'move', fromPath, toPath);
    }

    async webdavGet(connectionId, remotePath) {
        return this.executeOperation(connectionId, 'get', remotePath);
    }

    async webdavPut(connectionId, remotePath, data) {
        return this.executeOperation(connectionId, 'put', remotePath, data);
    }

    async webdavDelete(connectionId, remotePath) {
        return this.executeOperation(connectionId, 'delete', remotePath);
    }

    async webdavMkdir(connectionId, remotePath) {
        return this.executeOperation(connectionId, 'mkcol', remotePath);
    }

    /**
     * FTP operations
     */
    async ftpList(connectionId, remotePath = '.') {
        return this.executeOperation(connectionId, 'list', remotePath);
    }

    async ftpGet(connectionId, remotePath) {
        return this.executeOperation(connectionId, 'get', remotePath);
    }

    async ftpPut(connectionId, data, remotePath) {
        return this.executeOperation(connectionId, 'put', data, remotePath);
    }

    async ftpDelete(connectionId, remotePath) {
        return this.executeOperation(connectionId, 'delete', remotePath);
    }

    async ftpMkdir(connectionId, remotePath) {
        return this.executeOperation(connectionId, 'mkdir', remotePath);
    }

    async ftpCwd(connectionId, remotePath) {
        return this.executeOperation(connectionId, 'cwd', remotePath);
    }

    async ftpPwd(connectionId) {
        return this.executeOperation(connectionId, 'pwd');
    }

    /**
     * Test connection
     */
    async testConnection(config) {
        const testId = `test_${Date.now()}`;
        try {
            const cfg = { ...(config || {}) };
            delete cfg.builtin;
            const connection = this.router.createStaticConnection({
                ...cfg,
                id: testId,
                persistent: false,
                autoReconnect: false
            });

            await this.router.connect(testId);
            await this.router.disconnect(testId);
            await this.router.removeConnection(testId);

            return { success: true, message: 'Connection successful' };
        } catch (error) {
            await this.router.removeConnection(testId).catch(() => {});
            return { success: false, message: error.message };
        }
    }
}

// Singleton instance
let instance = null;

function getNetworkService() {
    if (!instance) {
        instance = new NetworkService();
    }
    return instance;
}

module.exports = { NetworkService, getNetworkService };
