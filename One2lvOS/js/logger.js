// One2lvOS Logger Module

(function(window) {
    'use strict';

    const LOG_LEVELS = {
        DEBUG: 0,
        INFO: 1,
        WARN: 2,
        ERROR: 3
    };

    class Logger {
        constructor() {
            this.level = LOG_LEVELS.INFO;
            this.history = [];
            this.maxHistory = 1000;
            this.listeners = [];
        }

        setLevel(level) {
            if (typeof level === 'string') {
                this.level = LOG_LEVELS[level.toUpperCase()] || LOG_LEVELS.INFO;
            } else {
                this.level = level;
            }
        }

        addListener(callback) {
            this.listeners.push(callback);
        }

        removeListener(callback) {
            const index = this.listeners.indexOf(callback);
            if (index > -1) {
                this.listeners.splice(index, 1);
            }
        }

        log(level, module, message, data = null) {
            if (LOG_LEVELS[level] < this.level) {
                return;
            }

            const entry = {
                timestamp: Date.now(),
                level,
                module,
                message,
                data
            };

            // Add to history
            this.history.push(entry);
            if (this.history.length > this.maxHistory) {
                this.history.shift();
            }

            // Notify listeners
            this.listeners.forEach(listener => {
                try {
                    listener(entry);
                } catch (error) {
                    console.error('[Logger] Listener error:', error);
                }
            });

            // Console output
            const timestamp = new Date(entry.timestamp).toISOString();
            const prefix = `[${timestamp}] [${module}]`;

            switch (level) {
                case 'DEBUG':
                    console.debug(prefix, message, data || '');
                    break;
                case 'INFO':
                    console.info(prefix, message, data || '');
                    break;
                case 'WARN':
                    console.warn(prefix, message, data || '');
                    break;
                case 'ERROR':
                    console.error(prefix, message, data || '');
                    break;
            }
        }

        debug(module, message, data) {
            this.log('DEBUG', module, message, data);
        }

        info(module, message, data) {
            this.log('INFO', module, message, data);
        }

        warn(module, message, data) {
            this.log('WARN', module, data);
        }

        error(module, message, data) {
            this.log('ERROR', module, message, data);
        }

        getHistory(filter = {}) {
            let result = this.history;

            if (filter.level) {
                result = result.filter(entry => entry.level === filter.level);
            }

            if (filter.module) {
                result = result.filter(entry => entry.module === filter.module);
            }

            if (filter.since) {
                result = result.filter(entry => entry.timestamp >= filter.since);
            }

            return result;
        }

        clear() {
            this.history = [];
        }

        export() {
            return JSON.stringify(this.history, null, 2);
        }
    }

    // Export to global
    window.Logger = new Logger();

    // Capture unhandled errors
    window.addEventListener('error', (event) => {
        Logger.error('Global', 'Unhandled error', {
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            error: event.error
        });
    });

    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
        Logger.error('Global', 'Unhandled promise rejection', {
            reason: event.reason
        });
    });

})(window);
