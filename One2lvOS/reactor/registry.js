// Registry Module

(function(window) {
    'use strict';

    class Registry {
        constructor() {
            this.entries = new Map();
            this.initialized = false;
        }

        async init() {
            if (this.initialized) return;

            // Load from storage
            try {
                const stored = await Storage.getAll('registry');
                stored.forEach(entry => {
                    this.entries.set(entry.key, entry);
                });
                Logger.info('Registry', `Loaded ${stored.length} entries from storage`);
            } catch (error) {
                Logger.error('Registry', 'Failed to load from storage', error);
            }

            this.initialized = true;
        }

        async set(key, value, metadata = {}) {
            const entry = {
                key,
                value,
                metadata: {
                    ...metadata,
                    created: metadata.created || Date.now(),
                    updated: Date.now()
                }
            };

            this.entries.set(key, entry);

            // Persist to storage
            try {
                await Storage.set('registry', entry);
            } catch (error) {
                Logger.error('Registry', 'Failed to persist entry', error);
            }

            EventBus.emit('registry:set', { key });
        }

        get(key, defaultValue = null) {
            const entry = this.entries.get(key);
            return entry ? entry.value : defaultValue;
        }

        has(key) {
            return this.entries.has(key);
        }

        async delete(key) {
            this.entries.delete(key);

            try {
                await Storage.delete('registry', key);
            } catch (error) {
                Logger.error('Registry', 'Failed to delete entry', error);
            }

            EventBus.emit('registry:delete', { key });
        }

        getAll() {
            return Array.from(this.entries.values());
        }

        search(query) {
            const results = [];
            for (const [key, entry] of this.entries) {
                if (key.includes(query) || JSON.stringify(entry.value).includes(query)) {
                    results.push(entry);
                }
            }
            return results;
        }

        async snapshot() {
            return {
                entries: Array.from(this.entries.entries()),
                timestamp: Date.now()
            };
        }

        async restore(snapshot) {
            this.entries.clear();
            for (const [key, entry] of snapshot.entries) {
                this.entries.set(key, entry);
                await Storage.set('registry', entry);
            }
            Logger.info('Registry', `Restored ${snapshot.entries.length} entries`);
        }
    }

    window.Registry = new Registry();

})(window);
