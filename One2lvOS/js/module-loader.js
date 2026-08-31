// One2lvOS Module Loader

(function(window) {
    'use strict';

    class ModuleLoader {
        constructor() {
            this.modules = new Map();
            this.loading = new Map();
        }

        async load(moduleName, modulePath) {
            // Already loaded
            if (this.modules.has(moduleName)) {
                return this.modules.get(moduleName);
            }

            // Currently loading
            if (this.loading.has(moduleName)) {
                return this.loading.get(moduleName);
            }

            // Start loading
            Logger.info('ModuleLoader', `Loading module: ${moduleName}`);

            const promise = this._loadModule(moduleName, modulePath);
            this.loading.set(moduleName, promise);

            try {
                const module = await promise;
                this.modules.set(moduleName, module);
                this.loading.delete(moduleName);

                EventBus.emit('module:loaded', { name: moduleName });
                Logger.info('ModuleLoader', `Module loaded: ${moduleName}`);

                return module;
            } catch (error) {
                this.loading.delete(moduleName);
                Logger.error('ModuleLoader', `Failed to load module: ${moduleName}`, error);
                throw error;
            }
        }

        async _loadModule(moduleName, modulePath) {
            try {
                // Load script
                await this._loadScript(modulePath);

                // Get module from global
                if (window[moduleName]) {
                    return window[moduleName];
                }

                // Try alternative names
                const alternatives = [
                    moduleName.charAt(0).toUpperCase() + moduleName.slice(1),
                    moduleName.toLowerCase()
                ];

                for (const alt of alternatives) {
                    if (window[alt]) {
                        return window[alt];
                    }
                }

                throw new Error(`Module ${moduleName} not found in global scope`);
            } catch (error) {
                throw new Error(`Failed to load module ${moduleName}: ${error.message}`);
            }
        }

        _loadScript(src) {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = src;
                script.async = true;

                script.onload = () => resolve();
                script.onerror = () => reject(new Error(`Failed to load script: ${src}`));

                document.head.appendChild(script);
            });
        }

        async loadBatch(modules) {
            const promises = modules.map(({ name, path }) => this.load(name, path));
            return Promise.allSettled(promises);
        }

        get(moduleName) {
            return this.modules.get(moduleName) || null;
        }

        has(moduleName) {
            return this.modules.has(moduleName);
        }

        unload(moduleName) {
            if (this.modules.has(moduleName)) {
                this.modules.delete(moduleName);
                EventBus.emit('module:unloaded', { name: moduleName });
                Logger.info('ModuleLoader', `Module unloaded: ${moduleName}`);
                return true;
            }
            return false;
        }

        getLoaded() {
            return Array.from(this.modules.keys());
        }

        getLoading() {
            return Array.from(this.loading.keys());
        }
    }

    // Export to global
    window.ModuleLoader = new ModuleLoader();

})(window);
