// Infinity Glass Desktop

(function(window) {
    'use strict';

    class InfinityGlass {
        constructor() {
            this.initialized = false;
            this.windows = [];
            this.activeWindow = null;
        }

        async init() {
            if (this.initialized) return;

            // Initialize components
            if (window.WindowManager) {
                await WindowManager.init();
            }

            if (window.Dock) {
                await Dock.init();
            }

            if (window.HUD) {
                await HUD.init();
            }

            this.initialized = true;
            EventBus.emit('infinityglass:initialized');
            Logger.info('InfinityGlass', 'Desktop environment initialized');
        }

        createWindow(options) {
            if (window.WindowManager) {
                return WindowManager.create(options);
            }
            return null;
        }
    }

    window.InfinityGlass = new InfinityGlass();

})(window);
