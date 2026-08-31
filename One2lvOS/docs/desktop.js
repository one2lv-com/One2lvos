// Infinity Glass Desktop

(function(window) {
    'use strict';

    class InfinityGlass {
        constructor() {
            this.initialized = false;
        }

        async init() {
            if (this.initialized) return;

            if (window.WindowManager) await WindowManager.init();
            if (window.Dock) await Dock.init();
            if (window.HUD) await HUD.init();
            if (window.Gestures) Gestures.init();
            if (window.Renderer) Renderer.start();

            this.initialized = true;
            EventBus.emit('infinityglass:initialized');
            Logger.info('InfinityGlass', 'Desktop environment initialized');
        }

        createWindow(options) {
            return window.WindowManager ? WindowManager.create(options) : null;
        }

        get activeWindow() {
            return window.WindowManager ? WindowManager.activeWindow : null;
        }

        get windows() {
            return window.WindowManager ? WindowManager.list() : [];
        }
    }

    window.InfinityGlass = new InfinityGlass();

})(window);
