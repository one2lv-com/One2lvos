// One2lvOS Boot Sequence

(async function(window) {
    'use strict';

    const BOOT_STEPS = [
        { id: 'bios', label: 'Boot BIOS', handler: bootBIOS },
        { id: 'shader', label: 'Aurora Shader', handler: initShader },
        { id: 'png', label: 'Load boot.png', handler: loadBootPNG },
        { id: 'snapshot', label: 'Extract Snapshot', handler: extractSnapshot },
        { id: 'registry', label: 'Restore Registry', handler: restoreRegistry },
        { id: 'reactor', label: 'Initialize Reactor', handler: initReactor },
        { id: 'eventbus', label: 'Start Event Bus', handler: startEventBus },
        { id: 'council', label: 'Load Council', handler: loadCouncil },
        { id: 'itt', label: 'Load ITT', handler: loadITT },
        { id: 'disk', label: 'Mount Interplanetary Disk', handler: mountDisk },
        { id: 'glass', label: 'Initialize Infinity Glass', handler: initGlass },
        { id: 'ready', label: 'Desktop Ready', handler: desktopReady }
    ];

    let currentStep = 0;

    // Boot BIOS
    async function bootBIOS() {
        await Config.load();
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    // Initialize Aurora Shader
    async function initShader() {
        const canvas = document.getElementById('aurora-canvas');
        if (canvas && window.AuroraShader) {
            await AuroraShader.init(canvas);
        }
        await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Load boot.png
    async function loadBootPNG() {
        const img = new Image();
        const loaded = new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = () => resolve(); // Don't fail if image missing
        });
        img.src = '/assets/boot.png';
        await loaded;
        await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Extract Snapshot
    async function extractSnapshot() {
        if (window.PNGBoot) {
            try {
                const snapshot = await PNGBoot.extract('/assets/boot.png');
                if (snapshot) {
                    Logger.info('Boot', 'Snapshot extracted from boot.png');
                    window.bootSnapshot = snapshot;
                }
            } catch (error) {
                Logger.warn('Boot', 'No snapshot found in boot.png', error);
            }
        }
        await new Promise(resolve => setTimeout(resolve, 400));
    }

    // Restore Registry
    async function restoreRegistry() {
        await Storage.init();

        if (window.bootSnapshot && window.bootSnapshot.registry) {
            try {
                await Registry.restore(window.bootSnapshot.registry);
                Logger.info('Boot', 'Registry restored from snapshot');
            } catch (error) {
                Logger.error('Boot', 'Failed to restore registry', error);
            }
        }

        await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Initialize Lumenis Reactor
    async function initReactor() {
        if (window.Lumenis) {
            await Lumenis.init();
            Logger.info('Boot', 'Lumenis Reactor initialized');
        }
        await new Promise(resolve => setTimeout(resolve, 400));
    }

    // Start Event Bus
    async function startEventBus() {
        EventBus.emit('system:booting', { step: 'eventbus' });
        Logger.info('Boot', 'Event Bus started');
        await new Promise(resolve => setTimeout(resolve, 200));
    }

    // Load Council
    async function loadCouncil() {
        if (window.Council) {
            await Council.init();
            Logger.info('Boot', 'Council initialized');
        }
        await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Load ITT
    async function loadITT() {
        if (window.ITT) {
            await ITT.init();
            Logger.info('Boot', 'ITT initialized');
        }
        await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Mount Interplanetary Disk
    async function mountDisk() {
        if (window.InterplanetaryDisk) {
            await InterplanetaryDisk.mount();
            Logger.info('Boot', 'Interplanetary Disk mounted');
        }
        await new Promise(resolve => setTimeout(resolve, 400));
    }

    // Initialize Infinity Glass
    async function initGlass() {
        if (window.InfinityGlass) {
            await InfinityGlass.init();
            Logger.info('Boot', 'Infinity Glass initialized');
        }
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    // Desktop Ready
    async function desktopReady() {
        // Hide BIOS screen
        const biosScreen = document.getElementById('bios');
        if (biosScreen) {
            biosScreen.classList.add('hidden');
        }

        // Show desktop
        const desktop = document.getElementById('desktop');
        if (desktop) {
            desktop.classList.remove('hidden');
        }

        // Remove booting class
        document.body.classList.remove('booting');

        EventBus.emit('system:ready');
        Logger.info('Boot', 'Desktop ready');

        await new Promise(resolve => setTimeout(resolve, 300));
    }

    // Update UI for boot step
    function updateBootUI(stepIndex, status) {
        const step = BOOT_STEPS[stepIndex];
        const stepElement = document.querySelector(`[data-step="${step.id}"]`);
        const statusElement = stepElement?.querySelector('.boot-status');

        if (stepElement) {
            stepElement.className = `boot-step ${status}`;
        }

        if (statusElement) {
            statusElement.className = `boot-status ${status}`;
            switch (status) {
                case 'active':
                    statusElement.textContent = '⟳';
                    break;
                case 'complete':
                    statusElement.textContent = '✓';
                    break;
                case 'error':
                    statusElement.textContent = '✗';
                    break;
            }
        }

        // Update progress bar
        const progress = ((stepIndex + (status === 'complete' ? 1 : 0.5)) / BOOT_STEPS.length) * 100;
        const progressFill = document.querySelector('.progress-fill');
        const progressText = document.querySelector('.progress-text');

        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }

        if (progressText) {
            if (status === 'complete' && stepIndex === BOOT_STEPS.length - 1) {
                progressText.textContent = 'System ready!';
            } else {
                progressText.textContent = step.label + '...';
            }
        }
    }

    // Run boot sequence
    async function runBootSequence() {
        Logger.info('Boot', 'Starting boot sequence');
        EventBus.emit('system:boot:start');

        for (let i = 0; i < BOOT_STEPS.length; i++) {
            const step = BOOT_STEPS[i];

            try {
                // Mark as active
                updateBootUI(i, 'active');
                currentStep = i;

                // Run handler
                await step.handler();

                // Mark as complete
                updateBootUI(i, 'complete');

                EventBus.emit('system:boot:step', { step: step.id, status: 'complete' });
            } catch (error) {
                // Mark as error
                updateBootUI(i, 'error');

                Logger.error('Boot', `Boot step failed: ${step.label}`, error);
                EventBus.emit('system:boot:step', { step: step.id, status: 'error', error });

                // Decide whether to continue or halt
                const critical = ['bios', 'storage', 'eventbus'];
                if (critical.includes(step.id)) {
                    Logger.error('Boot', 'Critical boot step failed. Halting.');
                    EventBus.emit('system:boot:failed', { step: step.id, error });
                    return;
                }

                // Non-critical errors - continue booting
                Logger.warn('Boot', `Non-critical error in ${step.label}. Continuing...`);
            }
        }

        Logger.info('Boot', 'Boot sequence complete');
        EventBus.emit('system:boot:complete');
    }

    // Start boot when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', runBootSequence);
    } else {
        runBootSequence();
    }

    // Handle F12 for system console
    document.addEventListener('keydown', (e) => {
        if (e.key === 'F12') {
            e.preventDefault();
            console.log('=== One2lvOS System Console ===');
            console.log('Config:', Config.toJSON());
            console.log('Logger History:', Logger.getHistory());
            console.log('EventBus History:', EventBus.getHistory());
            console.log('Loaded Modules:', ModuleLoader.getLoaded());
            console.log('Current Boot Step:', currentStep, BOOT_STEPS[currentStep]?.label);
        }
    });

})(window);
