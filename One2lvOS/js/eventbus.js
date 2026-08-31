// One2lvOS Event Bus Module

(function(window) {
    'use strict';

    class EventBus {
        constructor() {
            this.events = new Map();
            this.history = [];
            this.maxHistory = 1000;
        }

        on(event, callback, options = {}) {
            if (!this.events.has(event)) {
                this.events.set(event, []);
            }

            const listener = {
                callback,
                once: options.once || false,
                priority: options.priority || 0
            };

            this.events.get(event).push(listener);

            // Sort by priority (higher first)
            this.events.get(event).sort((a, b) => b.priority - a.priority);

            Logger.debug('EventBus', `Listener registered for event: ${event}`);

            // Return unsubscribe function
            return () => this.off(event, callback);
        }

        once(event, callback, options = {}) {
            return this.on(event, callback, { ...options, once: true });
        }

        off(event, callback) {
            if (!this.events.has(event)) {
                return;
            }

            const listeners = this.events.get(event);
            const index = listeners.findIndex(l => l.callback === callback);

            if (index > -1) {
                listeners.splice(index, 1);
                Logger.debug('EventBus', `Listener removed for event: ${event}`);
            }

            // Clean up empty event arrays
            if (listeners.length === 0) {
                this.events.delete(event);
            }
        }

        emit(event, data = null) {
            // Log event
            const entry = {
                timestamp: Date.now(),
                event,
                data
            };

            this.history.push(entry);
            if (this.history.length > this.maxHistory) {
                this.history.shift();
            }

            Logger.debug('EventBus', `Event emitted: ${event}`, data);

            // No listeners
            if (!this.events.has(event)) {
                return;
            }

            // Call listeners
            const listeners = this.events.get(event).slice(); // Clone array
            const toRemove = [];

            for (const listener of listeners) {
                try {
                    listener.callback(data);

                    if (listener.once) {
                        toRemove.push(listener);
                    }
                } catch (error) {
                    Logger.error('EventBus', `Error in event listener for ${event}`, error);
                }
            }

            // Remove once listeners
            if (toRemove.length > 0) {
                const remaining = this.events.get(event).filter(l => !toRemove.includes(l));
                if (remaining.length === 0) {
                    this.events.delete(event);
                } else {
                    this.events.set(event, remaining);
                }
            }
        }

        async emitAsync(event, data = null) {
            // Log event
            const entry = {
                timestamp: Date.now(),
                event,
                data
            };

            this.history.push(entry);
            if (this.history.length > this.maxHistory) {
                this.history.shift();
            }

            Logger.debug('EventBus', `Async event emitted: ${event}`, data);

            // No listeners
            if (!this.events.has(event)) {
                return;
            }

            // Call listeners
            const listeners = this.events.get(event).slice();
            const toRemove = [];

            for (const listener of listeners) {
                try {
                    await listener.callback(data);

                    if (listener.once) {
                        toRemove.push(listener);
                    }
                } catch (error) {
                    Logger.error('EventBus', `Error in async event listener for ${event}`, error);
                }
            }

            // Remove once listeners
            if (toRemove.length > 0) {
                const remaining = this.events.get(event).filter(l => !toRemove.includes(l));
                if (remaining.length === 0) {
                    this.events.delete(event);
                } else {
                    this.events.set(event, remaining);
                }
            }
        }

        getListenerCount(event) {
            return this.events.has(event) ? this.events.get(event).length : 0;
        }

        getEvents() {
            return Array.from(this.events.keys());
        }

        getHistory(filter = {}) {
            let result = this.history;

            if (filter.event) {
                result = result.filter(entry => entry.event === filter.event);
            }

            if (filter.since) {
                result = result.filter(entry => entry.timestamp >= filter.since);
            }

            return result;
        }

        clear() {
            this.events.clear();
            this.history = [];
            Logger.info('EventBus', 'Event bus cleared');
        }
    }

    // Export to global
    window.EventBus = new EventBus();

})(window);
