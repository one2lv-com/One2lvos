/**
 * Persistence Layer
 * IndexedDB bridge for file system operations
 * Allows terminal changes to persist across PWA sessions
 */

export class PersistenceLayer {
    constructor() {
        this.dbName = 'InfinityGlassFS';
        this.dbVersion = 1;
        this.db = null;

        this.stores = {
            FILES: 'files',           // Virtual file system
            HISTORY: 'history',       // Command history
            STATE: 'state',           // Application state
            MODULES: 'modules',       // Reactor modules
            MEMORY: 'memory',         // Memory lattice nodes
            SETTINGS: 'settings'      // User preferences
        };

        this.init();
    }

    async init() {
        try {
            this.db = await this.openDatabase();
            console.log('[PersistenceLayer] Database opened successfully');
            return true;
        } catch (error) {
            console.error('[PersistenceLayer] Failed to open database:', error);
            return false;
        }
    }

    openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Files store: Virtual file system
                if (!db.objectStoreNames.contains(this.stores.FILES)) {
                    const filesStore = db.createObjectStore(this.stores.FILES, { keyPath: 'path' });
                    filesStore.createIndex('directory', 'directory', { unique: false });
                    filesStore.createIndex('modified', 'modified', { unique: false });
                    filesStore.createIndex('type', 'type', { unique: false });
                }

                // History store: Command history
                if (!db.objectStoreNames.contains(this.stores.HISTORY)) {
                    const historyStore = db.createObjectStore(this.stores.HISTORY, { keyPath: 'id', autoIncrement: true });
                    historyStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // State store: Application state snapshots
                if (!db.objectStoreNames.contains(this.stores.STATE)) {
                    const stateStore = db.createObjectStore(this.stores.STATE, { keyPath: 'key' });
                    stateStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // Modules store: Reactor modules
                if (!db.objectStoreNames.contains(this.stores.MODULES)) {
                    const modulesStore = db.createObjectStore(this.stores.MODULES, { keyPath: 'id' });
                    modulesStore.createIndex('name', 'name', { unique: true });
                    modulesStore.createIndex('status', 'status', { unique: false });
                }

                // Memory store: Memory lattice nodes
                if (!db.objectStoreNames.contains(this.stores.MEMORY)) {
                    const memoryStore = db.createObjectStore(this.stores.MEMORY, { keyPath: 'id', autoIncrement: true });
                    memoryStore.createIndex('timestamp', 'timestamp', { unique: false });
                    memoryStore.createIndex('type', 'type', { unique: false });
                }

                // Settings store: User preferences
                if (!db.objectStoreNames.contains(this.stores.SETTINGS)) {
                    db.createObjectStore(this.stores.SETTINGS, { keyPath: 'key' });
                }

                console.log('[PersistenceLayer] Database schema created');
            };
        });
    }

    // ============================================
    // FILE SYSTEM OPERATIONS
    // ============================================

    async writeFile(path, content, metadata = {}) {
        const directory = path.substring(0, path.lastIndexOf('/')) || '/';
        const filename = path.substring(path.lastIndexOf('/') + 1);

        const file = {
            path,
            directory,
            filename,
            content,
            type: metadata.type || this.getFileType(filename),
            size: content.length,
            modified: Date.now(),
            created: metadata.created || Date.now(),
            permissions: metadata.permissions || 'rw-r--r--',
            owner: metadata.owner || 'user',
            ...metadata
        };

        return this.putRecord(this.stores.FILES, file);
    }

    async readFile(path) {
        const file = await this.getRecord(this.stores.FILES, path);
        return file ? file.content : null;
    }

    async deleteFile(path) {
        return this.deleteRecord(this.stores.FILES, path);
    }

    async listFiles(directory = '/') {
        return this.queryRecords(this.stores.FILES, 'directory', directory);
    }

    async fileExists(path) {
        const file = await this.getRecord(this.stores.FILES, path);
        return file !== null;
    }

    async getFileMetadata(path) {
        const file = await this.getRecord(this.stores.FILES, path);
        if (!file) return null;

        const { content, ...metadata } = file;
        return metadata;
    }

    async moveFile(oldPath, newPath) {
        const file = await this.getRecord(this.stores.FILES, oldPath);
        if (!file) return false;

        await this.deleteFile(oldPath);

        const newDirectory = newPath.substring(0, newPath.lastIndexOf('/')) || '/';
        const newFilename = newPath.substring(newPath.lastIndexOf('/') + 1);

        file.path = newPath;
        file.directory = newDirectory;
        file.filename = newFilename;
        file.modified = Date.now();

        return this.putRecord(this.stores.FILES, file);
    }

    async copyFile(sourcePath, destPath) {
        const file = await this.getRecord(this.stores.FILES, sourcePath);
        if (!file) return false;

        const newDirectory = destPath.substring(0, destPath.lastIndexOf('/')) || '/';
        const newFilename = destPath.substring(destPath.lastIndexOf('/') + 1);

        const copiedFile = {
            ...file,
            path: destPath,
            directory: newDirectory,
            filename: newFilename,
            created: Date.now(),
            modified: Date.now()
        };

        return this.putRecord(this.stores.FILES, copiedFile);
    }

    getFileType(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const types = {
            txt: 'text/plain',
            js: 'text/javascript',
            json: 'application/json',
            html: 'text/html',
            css: 'text/css',
            md: 'text/markdown',
            sh: 'application/x-sh',
            py: 'text/x-python',
            log: 'text/plain'
        };
        return types[ext] || 'application/octet-stream';
    }

    // ============================================
    // COMMAND HISTORY
    // ============================================

    async addToHistory(command, output, exitCode = 0) {
        const entry = {
            command,
            output,
            exitCode,
            timestamp: Date.now(),
            cwd: await this.getSetting('cwd') || '/'
        };

        return this.putRecord(this.stores.HISTORY, entry);
    }

    async getHistory(limit = 100) {
        const transaction = this.db.transaction([this.stores.HISTORY], 'readonly');
        const store = transaction.objectStore(this.stores.HISTORY);
        const index = store.index('timestamp');

        return new Promise((resolve, reject) => {
            const request = index.openCursor(null, 'prev');
            const results = [];

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor && results.length < limit) {
                    results.push(cursor.value);
                    cursor.continue();
                } else {
                    resolve(results);
                }
            };

            request.onerror = () => reject(request.error);
        });
    }

    async clearHistory() {
        return this.clearStore(this.stores.HISTORY);
    }

    // ============================================
    // APPLICATION STATE
    // ============================================

    async saveState(key, state) {
        const stateRecord = {
            key,
            state,
            timestamp: Date.now()
        };

        return this.putRecord(this.stores.STATE, stateRecord);
    }

    async loadState(key) {
        const record = await this.getRecord(this.stores.STATE, key);
        return record ? record.state : null;
    }

    async saveReactorState(reactorState) {
        return this.saveState('reactor', reactorState);
    }

    async loadReactorState() {
        return this.loadState('reactor');
    }

    async saveMemoryLatticeState(latticeState) {
        return this.saveState('memoryLattice', latticeState);
    }

    async loadMemoryLatticeState() {
        return this.loadState('memoryLattice');
    }

    // ============================================
    // REACTOR MODULES
    // ============================================

    async saveModule(module) {
        return this.putRecord(this.stores.MODULES, module);
    }

    async loadModule(id) {
        return this.getRecord(this.stores.MODULES, id);
    }

    async loadAllModules() {
        return this.getAllRecords(this.stores.MODULES);
    }

    async deleteModule(id) {
        return this.deleteRecord(this.stores.MODULES, id);
    }

    async updateModuleStatus(id, status) {
        const module = await this.loadModule(id);
        if (!module) return false;

        module.status = status;
        module.lastUpdate = Date.now();

        return this.saveModule(module);
    }

    // ============================================
    // MEMORY LATTICE NODES
    // ============================================

    async addMemoryNode(data, type = 'general') {
        const node = {
            data,
            type,
            timestamp: Date.now()
        };

        return this.putRecord(this.stores.MEMORY, node);
    }

    async getMemoryNodes(type = null, limit = 50) {
        if (type) {
            return this.queryRecords(this.stores.MEMORY, 'type', type, limit);
        } else {
            return this.getAllRecords(this.stores.MEMORY, limit);
        }
    }

    async deleteMemoryNode(id) {
        return this.deleteRecord(this.stores.MEMORY, id);
    }

    async clearMemoryNodes() {
        return this.clearStore(this.stores.MEMORY);
    }

    // ============================================
    // SETTINGS
    // ============================================

    async setSetting(key, value) {
        return this.putRecord(this.stores.SETTINGS, { key, value });
    }

    async getSetting(key) {
        const record = await this.getRecord(this.stores.SETTINGS, key);
        return record ? record.value : null;
    }

    async deleteSetting(key) {
        return this.deleteRecord(this.stores.SETTINGS, key);
    }

    // ============================================
    // LOW-LEVEL DATABASE OPERATIONS
    // ============================================

    async putRecord(storeName, record) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.put(record);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async getRecord(storeName, key) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(key);

            request.onsuccess = () => resolve(request.result || null);
            request.onerror = () => reject(request.error);
        });
    }

    async deleteRecord(storeName, key) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.delete(key);

            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    async getAllRecords(storeName, limit = null) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll(limit);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async queryRecords(storeName, indexName, query, limit = null) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const index = store.index(indexName);
            const request = index.getAll(query, limit);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async clearStore(storeName) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.clear();

            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    // ============================================
    // UTILITY METHODS
    // ============================================

    async exportDatabase() {
        const exports = {};

        for (const storeName of Object.values(this.stores)) {
            exports[storeName] = await this.getAllRecords(storeName);
        }

        return exports;
    }

    async importDatabase(data) {
        for (const [storeName, records] of Object.entries(data)) {
            if (Object.values(this.stores).includes(storeName)) {
                await this.clearStore(storeName);

                for (const record of records) {
                    await this.putRecord(storeName, record);
                }
            }
        }

        return true;
    }

    async getDatabaseSize() {
        if (navigator.storage && navigator.storage.estimate) {
            const estimate = await navigator.storage.estimate();
            return {
                usage: estimate.usage,
                quota: estimate.quota,
                percentUsed: (estimate.usage / estimate.quota) * 100
            };
        }

        return null;
    }

    async clearAllData() {
        for (const storeName of Object.values(this.stores)) {
            await this.clearStore(storeName);
        }

        console.log('[PersistenceLayer] All data cleared');
        return true;
    }

    // Close database connection
    close() {
        if (this.db) {
            this.db.close();
            this.db = null;
            console.log('[PersistenceLayer] Database closed');
        }
    }
}

// Singleton instance
export const persistenceLayer = new PersistenceLayer();