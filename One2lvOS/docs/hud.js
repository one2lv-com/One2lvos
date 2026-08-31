// Desktop HUD

(function(window) {
    'use strict';

    class HUD {
        constructor() {
            this.element = null;
            this.clock = null;
            this.clockTimer = null;
            this.statusEl = null;
        }

        async init() {
            this.element = document.getElementById('hud');
            if (!this.element) {
                throw new Error('HUD: missing #hud element');
            }

            this.clock = this.element.querySelector('.hud-clock');
            this.statusEl = this.element.querySelector('.hud-status');

            this.updateClock();
            this.clockTimer = setInterval(() => this.updateClock(), 1000);

            EventBus.on('system:heartbeat', (data) => this.updateStatus(data));

            Logger.info('HUD', 'HUD initialized');
        }

        updateClock() {
            if (!this.clock) return;
            const now = new Date();
            this.clock.textContent = now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        }

        updateStatus(data) {
            if (!this.statusEl || !data?.uptime) return;
            const uptime = Math.floor(data.uptime / 1000);
            const hours = Math.floor(uptime / 3600);
            const minutes = Math.floor((uptime % 3600) / 60);
            this.statusEl.textContent = `Uptime: ${hours}h ${minutes}m`;
        }

        destroy() {
            if (this.clockTimer) {
                clearInterval(this.clockTimer);
                this.clockTimer = null;
            }
        }
    }

    window.HUD = new HUD();

})(window);
