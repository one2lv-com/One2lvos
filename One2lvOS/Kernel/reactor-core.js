/**
 * Reactor Core - One2lvOS Kernel
 * Orchestrates module loading, service management, and system scheduling
 */

class ReactorCore {
    constructor() {
        this.state = null;
        this.modules = new Map();
        this.services = new Map();
        this.initialized = false;
    }

    async initialize() {
        console.log('[ReactorCore] Initializing kernel...');

        // Restore system state
        this.state = await window.StateLoader.restore();
        console.log('[ReactorCore] State restored:', this.state);

        // Load core services
        await this.loadServices();

        // Load module loader
        await this.loadModuleSystem();

        // Load registry
        await this.loadRegistry();

        // Load desktop
        await this.loadDesktop();

        // Initialize auto-save
        this.initializeAutoSave();

        this.initialized = true;
        console.log('[ReactorCore] Kernel initialization complete');

        // Dispatch boot complete event
        window.dispatchEvent(new CustomEvent('One2lvOS:boot-complete', {
            detail: { state: this.state }
        }));
    }

    async loadServices() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'Kernel/services.js';
            script.onload = () => {
                console.log('[ReactorCore] Services loaded');
                resolve();
            };
            script.onerror = () => reject(new Error('Services load failed'));
            document.body.appendChild(script);
        });
    }

    async loadModuleSystem() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'Kernel/module-loader.js';
            script.onload = () => {
                console.log('[ReactorCore] Module loader ready');
                resolve();
            };
            script.onerror = () => reject(new Error('Module loader failed'));
            document.body.appendChild(script);
        });
    }

    async loadRegistry() {
        if (!this.state.modules.registry?.enabled) {
            console.log('[ReactorCore] Registry disabled, skipping');
            return;
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'Registry_of_Thought/registry.js';
            script.onload = () => {
                console.log('[ReactorCore] Registry of Thought mounted');
                if (window.RegistryOfThought) {
                    window.RegistryOfThought.initialize(this.state.registry);
                }
                resolve();
            };
            script.onerror = () => {
                console.warn('[ReactorCore] Registry load failed (non-fatal)');
                resolve(); // Non-fatal
            };
            document.body.appendChild(script);
        });
    }

    async loadDesktop() {
        if (!this.state.modules.desktop?.enabled) {
            console.log('[ReactorCore] Desktop disabled, skipping');
            return;
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'Desktop/terminal.js';
            script.onload = async () => {
                console.log('[ReactorCore] Desktop environment loaded');

                // Initialize desktop modules
                if (window.DesktopEnvironment) {
                    await window.DesktopEnvironment.initialize(this.state.desktop);
                }

                resolve();
            };
            script.onerror = () => reject(new Error('Desktop load failed'));
            document.body.appendChild(script);
        });
    }

    initializeAutoSave() {
        if (!this.state.user?.preferences?.autoSave) {
            console.log('[ReactorCore] Auto-save disabled');
            return;
        }

        // Save state every 30 seconds
        setInterval(() => {
            this.saveState();
        }, 30000);

        // Save on beforeunload
        window.addEventListener('beforeunload', () => {
            this.saveState();
        });

        console.log('[ReactorCore] Auto-save enabled (30s interval)');
    }

    saveState() {
        try {
            // Collect current state from all modules
            const currentState = {
                ...this.state,
                timestamp: Date.now(),
                registry: window.RegistryOfThought?.getState() || this.state.registry,
                desktop: window.DesktopEnvironment?.getState() || this.state.desktop
            };

            window.StateLoader.save(currentState);
        } catch (error) {
            console.error('[ReactorCore] State save failed:', error);
        }
    }

    getState() {
        return this.state;
    }

    setState(newState) {
        this.state = { ...this.state, ...newState };
    }

    registerModule(name, module) {
        this.modules.set(name, module);
        console.log(`[ReactorCore] Module registered: ${name}`);
    }

    getModule(name) {
        return this.modules.get(name);
    }
}

// Create global instance
window.ReactorCore = new ReactorCore();
