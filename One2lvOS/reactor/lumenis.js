// Lumenis Cognitive Reactor

(function(window) {
    'use strict';

    class Lumenis {
        constructor() {
            this.initialized = false;
            this.tasks = [];
            this.running = false;
            this.scheduler = null;
            this.registry = null;
        }

        async init() {
            if (this.initialized) return;

            Logger.info('Lumenis', 'Initializing Cognitive Reactor');

            // Initialize scheduler
            if (window.Scheduler) {
                this.scheduler = new Scheduler();
                await this.scheduler.init();
            }

            // Initialize registry
            if (window.Registry) {
                this.registry = window.Registry;
            }

            this.running = true;
            this.initialized = true;

            EventBus.emit('reactor:initialized');
            Logger.info('Lumenis', 'Cognitive Reactor initialized');
        }

        async submit(task) {
            if (!this.initialized) {
                throw new Error('Reactor not initialized');
            }

            const taskId = `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            const reactorTask = {
                id: taskId,
                ...task,
                status: 'pending',
                created: Date.now(),
                updated: Date.now()
            };

            this.tasks.push(reactorTask);

            if (this.scheduler) {
                await this.scheduler.schedule(reactorTask);
            }

            EventBus.emit('reactor:task:submitted', { taskId });
            Logger.debug('Lumenis', `Task submitted: ${taskId}`);

            return taskId;
        }

        async getTask(taskId) {
            return this.tasks.find(t => t.id === taskId);
        }

        async getTasks(filter = {}) {
            let result = this.tasks;

            if (filter.status) {
                result = result.filter(t => t.status === filter.status);
            }

            return result;
        }

        async stop() {
            this.running = false;
            if (this.scheduler) {
                await this.scheduler.stop();
            }
            Logger.info('Lumenis', 'Reactor stopped');
        }
    }

    // Export to global
    window.Lumenis = new Lumenis();

})(window);
