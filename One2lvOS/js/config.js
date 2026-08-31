// One2lvOS Configuration Module

(function(window) {
    'use strict';

    class Config {
        constructor() {
            this.data = null;
            this.loaded = false;
        }

        async load() {
            try {
                const response = await fetch('/system/Config.json');
                this.data = await response.json();
                this.loaded = true;
                console.log('[Config] Configuration loaded successfully');
                return this.data;
            } catch (error) {
                console.error('[Config] Failed to load configuration:', error);
                this.data = this.getDefaults();
                this.loaded = true;
                return this.data;
            }
        }

        get(path, defaultValue = null) {
            if (!this.loaded) {
                console.warn('[Config] Configuration not loaded yet');
                return defaultValue;
            }

            const keys = path.split('.');
            let value = this.data;

            for (const key of keys) {
                if (value && typeof value === 'object' && key in value) {
                    value = value[key];
                } else {
                    return defaultValue;
                }
            }

            return value;
        }

        set(path, value) {
            if (!this.loaded) {
                console.warn('[Config] Configuration not loaded yet');
                return false;
            }

            const keys = path.split('.');
            const lastKey = keys.pop();
            let obj = this.data;

            for (const key of keys) {
                if (!(key in obj)) {
                    obj[key] = {};
                }
                obj = obj[key];
            }

            obj[lastKey] = value;
            return true;
        }

        getDefaults() {
            return {
                system: {
                    name: 'One2lvOS',
                    version: '1.0.0-alpha',
                    environment: 'production'
                },
                boot: {
                    autoStart: true,
                    restoreSession: true
                },
                reactor: {
                    enabled: true,
                    maxConcurrency: 4
                },
                infinityGlass: {
                    enabled: true,
                    theme: 'dark'
                }
            };
        }

        toJSON() {
            return this.data;
        }
    }

    // Export to global
    window.Config = new Config();

})(window);
