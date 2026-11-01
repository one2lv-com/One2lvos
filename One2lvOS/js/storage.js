// One2lvOS Storage Module

(function(window) {
    'use strict';

    class Storage {
        constructor() {
            this.db = null;
            this.dbName = 'One2lvOS';
            this.dbVersion = 1;
        }

        async init() {
            return new Promise((resolve, reject) => {
                const request = indexedDB.open(this.dbName, this.dbVersion);

                request.onerror = () => {
                    Logger.error('Storage', 'Failed to open IndexedDB', request.error);
                    reject(request.error);
                };

                request.onsuccess = () => {
                    this.db = request.result;
                    Logger.info('Storage', 'IndexedDB initialized');
                    resolve();
                };

                request.onupgradeneeded = (event) => {
                    const db = event.target.result;

                    // Create object stores
                    if (!db.objectStoreNames.contains('registry')) {
                        db.createObjectStore('registry', { keyPath: 'key' });
                    }

                    if (!db.objectStoreNames.contains('snapshots')) {
                        db.createObjectStore('snapshots', { keyPath: 'id' });
                    }

                    if (!db.objectStoreNames.contains('files')) {
                        db.createObjectStore('files', { keyPath: 'path' });
                    }

                    if (!db.objectStoreNames.contains('cache')) {
                        db.createObjectStore('cache', { keyPath: 'key' });
                    }

                    Logger.info('Storage', 'Database schema updated');
                };
            });
        }

        async get(storeName, key) {
            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([storeName], 'readonly');
                const store = transaction.objectStore(storeName);
                const request = store.get(key);

                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        }

        async set(storeName, value) {
            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([storeName], 'readwrite');
                const store = transaction.objectStore(storeName);
                const request = store.put(value);

                request.onsuccess = () => resolve();
                request.onerror = () => reject(request.error);
            });
        }

        async delete(storeName, key) {
            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([storeName], 'readwrite');
                const store = transaction.objectStore(storeName);
                const request = store.delete(key);

                request.onsuccess = () => resolve();
                request.onerror = () => reject(request.error);
            });
        }

        async getAll(storeName) {
            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([storeName], 'readonly');
                const store = transaction.objectStore(storeName);
                const request = store.getAll();

                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        }

        async clear(storeName) {
            return new Promise((resolve, reject) => {
                const transaction = this.db.transaction([storeName], 'readwrite');
                const store = transaction.objectStore(storeName);
                const request = store.clear();

                request.onsuccess = () => resolve();
                request.onerror = () => reject(request.error);
            });
        }

        // LocalStorage helpers
        setLocal(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (error) {
                Logger.error('Storage', 'Failed to set localStorage', error);
                return false;
            }
        }

        getLocal(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (error) {
                Logger.error('Storage', 'Failed to get localStorage', error);
                return defaultValue;
            }
        }

        removeLocal(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (error) {
                Logger.error('Storage', 'Failed to remove localStorage', error);
                return false;
            }
        }

        // SessionStorage helpers
        setSession(key, value) {
            try {
                sessionStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (error) {
                Logger.error('Storage', 'Failed to set sessionStorage', error);
                return false;
            }
        }

        getSession(key, defaultValue = null) {
            try {
                const item = sessionStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (error) {
                Logger.error('Storage', 'Failed to get sessionStorage', error);
                return defaultValue;
            }
        }

        removeSession(key) {
            try {
                sessionStorage.removeItem(key);
                return true;
            } catch (error) {
                Logger.error('Storage', 'Failed to remove sessionStorage', error);
                return false;
            }
        }
    }

    // Export to global
    window.Storage = new Storage();

})(window);
