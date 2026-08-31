// Reactor Memory Module

(function(window) {
    'use strict';

    class ReactorMemory {
        constructor() {
            this.shortTerm = new Map();
            this.longTerm = new Map();
        }

        store(key, value, retention = 'shortTerm') {
            const entry = {
                key,
                value,
                retention,
                timestamp: Date.now()
            };

            if (retention === 'shortTerm') {
                this.shortTerm.set(key, entry);
            } else {
                this.longTerm.set(key, entry);
            }

            EventBus.emit('memory:store', { key, retention });
        }

        recall(key) {
            return this.shortTerm.get(key)?.value || this.longTerm.get(key)?.value || null;
        }

        forget(key) {
            this.shortTerm.delete(key);
            this.longTerm.delete(key);
        }

        prune() {
            const now = Date.now();
            const ttl = 3600000; // 1 hour

            for (const [key, entry] of this.shortTerm) {
                if (now - entry.timestamp > ttl) {
                    this.shortTerm.delete(key);
                }
            }

            Logger.debug('ReactorMemory', 'Pruned old short-term memories');
        }
    }

    window.ReactorMemory = new ReactorMemory();

})(window);
