// Desktop HUD

(function(window) {
    'use strict';

    class HUD {
        constructor() {
            this.element = null;
            this.clock = null;
        }

        async init() {
            this.element = document.getElementById('hud');
            this.clock = this.element.querySelector('.hud-clock');

            this.updateClock();
            setInterval(() => this.updateClock(), 1000);

            // Listen to system events
            EventBus.on('system:heartbeat', (data) => this.updateStatus(data));

            Logger.info('HUD', 'HUD initialized');
        }

        updateClock() {
            const now = new Date();
            const time = now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
            if (this.clock) {
                this.clock.textContent = time;
            }
        }

        updateStatus(data) {
            const statusEl = this.element.querySelector('.hud-status');
            if (statusEl && data.uptime) {
                const uptime = Math.floor(data.uptime / 1000);
                const hours = Math.floor(uptime / 3600);
                const minutes = Math.floor((uptime % 3600) / 60);
                statusEl.textContent = `Uptime: ${hours}h ${minutes}m`;
            }
        }
    }

    window.HUD = new HUD();

})(window);
