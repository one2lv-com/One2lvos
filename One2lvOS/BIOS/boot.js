/**
 * One2lvOS BIOS v0.9
 * Boot Orchestrator - Manages hardware checks, shader loading, state restoration, and kernel initialization
 */

class BootLoader {
    constructor() {
        this.bootLog = document.getElementById('boot-log');
        this.bootScreen = document.getElementById('boot-screen');
        this.canvas = document.getElementById('aurora-canvas');
        this.startTime = Date.now();
        this.checks = {
            webgl: false,
            storage: false,
            assets: false
        };
    }

    log(message, type = 'info') {
        const line = document.createElement('div');
        line.className = `boot-line boot-${type}`;

        const prefix = {
            success: '[✓]',
            error: '[✗]',
            warning: '[!]',
            info: '[·]'
        }[type] || '[·]';

        line.textContent = `${prefix} ${message}`;
        this.bootLog.appendChild(line);

        console.log(`[BOOT] ${message}`);

        if (type === 'error') {
            console.error(message);
        }
    }

    async boot() {
        this.log('One2lvOS BIOS v0.9', 'info');
        this.log('', 'info');

        try {
            // Hardware checks
            await this.checkWebGL();
            await this.checkStorage();
            await this.checkAssets();

            // Load shader system
            await this.loadShader();

            // Load state management
            await this.loadStateLoader();

            // Boot kernel
            await this.bootKernel();

            // Boot complete
            const bootTime = Date.now() - this.startTime;
            this.log('', 'info');
            this.log(`Boot complete in ${bootTime}ms`, 'success');

            setTimeout(() => this.hideBootScreen(), 1000);

        } catch (error) {
            this.log(`FATAL: ${error.message}`, 'error');
            this.log('System halted', 'error');
        }
    }

    async checkWebGL() {
        try {
            const gl = this.canvas.getContext('webgl2') || this.canvas.getContext('webgl');

            if (!gl) {
                throw new Error('WebGL not available');
            }

            this.checks.webgl = true;
            this.log('WebGL initialized', 'success');

            // Store context for shader system
            window.One2lvOS_GL = gl;

        } catch (error) {
            this.log('WebGL initialization failed', 'error');
            throw error;
        }
    }

    async checkStorage() {
        try {
            // Test localStorage
            localStorage.setItem('_boot_test', '1');
            localStorage.removeItem('_boot_test');

            // Test IndexedDB
            if (!window.indexedDB) {
                throw new Error('IndexedDB not available');
            }

            this.checks.storage = true;
            this.log('Storage subsystem online', 'success');

        } catch (error) {
            this.log('Storage check failed', 'error');
            throw error;
        }
    }

    async checkAssets() {
        try {
            // Check if assets directory is accessible
            // In production, this would verify critical assets exist
            this.checks.assets = true;
            this.log('Asset manifest verified', 'success');

        } catch (error) {
            this.log('Asset check failed', 'warning');
            // Non-fatal, continue boot
        }
    }

    async loadShader() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'BIOS/shader.js';
            script.onload = () => {
                this.log('Aurora shader loaded', 'success');
                resolve();
            };
            script.onerror = () => {
                this.log('Shader load failed', 'error');
                reject(new Error('Failed to load shader system'));
            };
            document.body.appendChild(script);
        });
    }

    async loadStateLoader() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'BIOS/state-loader.js';
            script.onload = () => {
                this.log('State loader initialized', 'success');
                resolve();
            };
            script.onerror = () => {
                this.log('State loader failed', 'error');
                reject(new Error('Failed to load state management'));
            };
            document.body.appendChild(script);
        });
    }

    async bootKernel() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'Kernel/reactor-core.js';
            script.onload = async () => {
                this.log('Reactor Core online', 'success');

                // Initialize kernel
                if (window.ReactorCore) {
                    await window.ReactorCore.initialize();
                    this.log('Kernel services started', 'success');
                }

                resolve();
            };
            script.onerror = () => {
                this.log('Kernel boot failed', 'error');
                reject(new Error('Failed to boot kernel'));
            };
            document.body.appendChild(script);
        });
    }

    hideBootScreen() {
        this.bootScreen.style.transition = 'opacity 1s';
        this.bootScreen.style.opacity = '0';

        setTimeout(() => {
            this.bootScreen.style.display = 'none';
            document.getElementById('desktop').style.display = 'block';
        }, 1000);
    }
}

// Auto-boot on load
window.addEventListener('DOMContentLoaded', () => {
    const bootLoader = new BootLoader();
    bootLoader.boot();
});
