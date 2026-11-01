// Interplanetary Disk Main Module

(function(window) {
    'use strict';

    class InterplanetaryDisk {
        constructor() {
            this.mounted = false;
        }

        async mount() {
            if (this.mounted) return;

            Logger.info('InterplanetaryDisk', 'Mounting Interplanetary Disk');

            // Initialize components
            if (window.FileSystem) {
                Logger.info('InterplanetaryDisk', 'FileSystem ready');
            }

            if (window.Snapshot) {
                Logger.info('InterplanetaryDisk', 'Snapshot system ready');
            }

            if (window.Checkpoint) {
                Logger.info('InterplanetaryDisk', 'Checkpoint system ready');
            }

            if (window.Recovery) {
                await Recovery.init();
            }

            this.mounted = true;
            EventBus.emit('disk:mounted');
            Logger.info('InterplanetaryDisk', 'Interplanetary Disk mounted');
        }
    }

    window.InterplanetaryDisk = new InterplanetaryDisk();

})(window);
