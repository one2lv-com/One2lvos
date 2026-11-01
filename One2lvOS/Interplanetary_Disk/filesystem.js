/**
 * Interplanetary Disk
 * Virtual filesystem with IndexedDB persistence
 */

class InterplanetaryDisk {
    constructor() {
        this.fs = new Map();
        this.dbName = 'One2lvOS_Filesystem';
        this.initialized = false;
    }

    async initialize() {
        console.log('[InterplanetaryDisk] Initializing virtual filesystem');

        await this.openDatabase();
        await this.loadFromIndexedDB();

        this.initialized = true;
        console.log('[InterplanetaryDisk] Filesystem mounted');
    }

    async openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 1);

            request.onerror = () => reject(new Error('Database open failed'));

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                if (!db.objectStoreNames.contains('files')) {
                    db.createObjectStore('files', { keyPath: 'path' });
                }
            };
        });
    }

    async loadFromIndexedDB() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['files'], 'readonly');
            const store = transaction.objectStore('files');
            const request = store.getAll();

            request.onsuccess = () => {
                const files = request.result || [];
                files.forEach(file => {
                    this.fs.set(file.path, file);
                });
                console.log(`[InterplanetaryDisk] Loaded ${files.length} files from storage`);
                resolve();
            };

            request.onerror = () => resolve(); // Non-fatal
        });
    }

    async writeFile(path, content) {
        const file = {
            path,
            content,
            timestamp: Date.now(),
            size: new Blob([content]).size
        };

        this.fs.set(path, file);

        // Persist to IndexedDB
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['files'], 'readwrite');
            const store = transaction.objectStore('files');

            store.put(file);

            transaction.oncomplete = () => resolve(file);
            transaction.onerror = () => reject(new Error('Write failed'));
        });
    }

    async readFile(path) {
        const file = this.fs.get(path);

        if (!file) {
            throw new Error(`File not found: ${path}`);
        }

        return file.content;
    }

    async deleteFile(path) {
        this.fs.delete(path);

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['files'], 'readwrite');
            const store = transaction.objectStore('files');

            store.delete(path);

            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(new Error('Delete failed'));
        });
    }

    listFiles(directory = '/') {
        const files = Array.from(this.fs.values());

        return files
            .filter(f => f.path.startsWith(directory))
            .map(f => ({
                path: f.path,
                size: f.size,
                timestamp: f.timestamp
            }));
    }

    getStats() {
        const files = Array.from(this.fs.values());
        const totalSize = files.reduce((sum, f) => sum + f.size, 0);

        return {
            files: files.length,
            size: totalSize,
            formatted: `${(totalSize / 1024).toFixed(2)} KB`
        };
    }
}

window.InterplanetaryDisk = new InterplanetaryDisk();
