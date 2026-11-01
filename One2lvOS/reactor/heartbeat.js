// Reactor Heartbeat

(function(window) {
    'use strict';

    class Heartbeat {
        constructor() {
            this.interval = null;
            this.beats = 0;
            this.started = null;
        }

        start() {
            if (this.interval) return;

            this.started = Date.now();
            this.interval = setInterval(() => this.beat(), 1000);

            Logger.info('Heartbeat', 'Heartbeat started');
        }

        beat() {
            this.beats++;

            EventBus.emit('system:heartbeat', {
                beat: this.beats,
                uptime: Date.now() - this.started
            });

            // Periodic maintenance
            if (this.beats % 60 === 0) {
                this.maintenance();
            }
        }

        async maintenance() {
            // Prune memory
            if (window.ReactorMemory) {
                ReactorMemory.prune();
            }

            // Clean old logs
            if (Logger.history.length > 1000) {
                Logger.history = Logger.history.slice(-500);
            }

            Logger.debug('Heartbeat', 'Maintenance complete');
        }

        stop() {
            if (this.interval) {
                clearInterval(this.interval);
                this.interval = null;
                Logger.info('Heartbeat', 'Heartbeat stopped');
            }
        }

        getUptime() {
            return this.started ? Date.now() - this.started : 0;
        }
    }

    window.Heartbeat = new Heartbeat();

    // Start heartbeat when reactor initializes
    EventBus.on('reactor:initialized', () => {
        Heartbeat.start();
    });

})(window);
