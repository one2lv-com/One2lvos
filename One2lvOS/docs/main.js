// Interplanetary Disk Main Module

(function(window) {
    'use strict';

    class InterplanetaryDisk {
        constructor() {
            this.mounted = false;
            this.dependencies = ['Storage', 'EventBus', 'Logger'];
        }

        async mount() {
            if (this.mounted) return;

            Logger.info('InterplanetaryDisk', 'Mounting Interplanetary Disk');

            // Verify required services
            for (const dep of this.dependencies) {
                if (!window[dep]) {
                    throw new Error(`InterplanetaryDisk: missing required dependency: ${dep}`);
                }
            }

            // Initialize storage
            if (window.Storage && typeof Storage.init === 'function') {
                await Storage.init();
            }

            // Initialize components
            if (window.FileSystem) {
                Logger.info('InterplanetaryDisk', 'FileSystem ready');
            }

            if (window.Snapshot) {
                Logger.info('InterplanetaryDisk', 'Snapshot system ready');
            }

            if (window.Checkpoint) {
                if (typeof Checkpoint.init === 'function') {
                    await Checkpoint.init();
                }
                Logger.info('InterplanetaryDisk', 'Checkpoint system ready');
            }

            if (window.Recovery) {
                await Recovery.init();
            }

            if (window.VectorFS) {
                Logger.info('InterplanetaryDisk', 'VectorFS ready');
            }

            this.mounted = true;
            EventBus.emit('disk:mounted');
            Logger.info('InterplanetaryDisk', 'Interplanetary Disk mounted');
        }

        async unmount() {
            if (!this.mounted) return;
            Logger.info('InterplanetaryDisk', 'Unmounting Interplanetary Disk');
            this.mounted = false;
            EventBus.emit('disk:unmounted');
        }

        status() {
            return {
                mounted: this.mounted,
                files: window.FileSystem ? FileSystem.list('/', { recursive: true }).length : 0,
                checkpoints: window.Checkpoint ? Checkpoint.list().length : 0
            };
        }
    }

    window.InterplanetaryDisk = new InterplanetaryDisk();

})(window);
