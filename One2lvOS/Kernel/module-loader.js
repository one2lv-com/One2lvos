/**
 * Kernel Subsystem - Dynamic Module Loader
 * Instantiates and hydrates OS modules dynamically.
 */
class ModuleLoader {
    constructor() {
        this.registry = {
            'agenticControl': 'Agentic_Control/agents.js',
            'fluxCompassator': 'Flux_Compassator/navigation.js',
            'aiChat': 'Kernel/ai-chat-module.js',
            'aiChat': 'Kernel/ai-chat-module.js'
        };
        this.loadedModules = new Map();
    }

    async load(moduleKey, initialState = {}) {
        if (this.loadedModules.has(moduleKey)) {
            return this.loadedModules.get(moduleKey);
        }

        const scriptPath = this.registry[moduleKey];
        if (!scriptPath) {
            throw new Error(`[ModuleLoader] Module key '${moduleKey}' not recognized.`);
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = scriptPath;
            script.onload = async () => {
                let instance = null;
                
                if (moduleKey === 'agenticControl') instance = window.AgentManager;
                if (moduleKey === 'fluxCompassator') instance = window.FluxCompassator;
                if (moduleKey === 'aiChat') instance = window.AIChatModule;

                if (instance && typeof instance.initialize === 'function') {
                    await instance.initialize(initialState);
                }

                this.loadedModules.set(moduleKey, instance);
                console.log(`[ModuleLoader] Successfully booted: ${moduleKey}`);
                resolve(instance);
            };
            script.onerror = (err) => reject(new Error(`Failed to load script: ${scriptPath}`));
            document.head.appendChild(script);
        });
    }

    listModules() {
        return Array.from(this.loadedModules.keys());
    }
}

window.ModuleLoader = new ModuleLoader();

// Inside module-loader.js registry dictionary:
this.registry = {
    'agenticControl': 'Agentic_Control/agents.js',
    'fluxCompassator': 'Flux_Compassator/navigation.js',
    'aiChat': 'Kernel/ai-chat-module.js'
};

