// Reactor Scheduler

(function(window) {
    'use strict';

    class Scheduler {
        constructor() {
            this.queue = [];
            this.running = new Map();
            this.maxConcurrency = 4;
            this.interval = null;
        }

        async init() {
            this.maxConcurrency = Config.get('reactor.maxConcurrency', 4);
            this.startScheduler();
            Logger.info('Scheduler', 'Scheduler initialized');
        }

        startScheduler() {
            this.interval = setInterval(() => this.tick(), 100);
        }

        async schedule(task) {
            task.priority = task.priority || 'normal';
            task.status = 'queued';

            const priorityValues = { critical: 4, high: 3, normal: 2, low: 1 };
            task.priorityValue = priorityValues[task.priority] || 2;

            this.queue.push(task);
            this.queue.sort((a, b) => b.priorityValue - a.priorityValue);

            Logger.debug('Scheduler', `Task queued: ${task.id}`);
        }

        async tick() {
            if (this.running.size >= this.maxConcurrency) return;
            if (this.queue.length === 0) return;

            const task = this.queue.shift();
            await this.executeTask(task);
        }

        async executeTask(task) {
            task.status = 'running';
            task.started = Date.now();
            this.running.set(task.id, task);

            EventBus.emit('scheduler:task:start', { taskId: task.id });

            try {
                const result = await task.handler(task.params);
                task.status = 'completed';
                task.result = result;
                task.completed = Date.now();

                EventBus.emit('scheduler:task:complete', { taskId: task.id, result });
            } catch (error) {
                task.status = 'failed';
                task.error = error;
                task.completed = Date.now();

                EventBus.emit('scheduler:task:failed', { taskId: task.id, error });
                Logger.error('Scheduler', `Task failed: ${task.id}`, error);
            } finally {
                this.running.delete(task.id);
            }
        }

        async stop() {
            if (this.interval) {
                clearInterval(this.interval);
                this.interval = null;
            }
        }
    }

    window.Scheduler = Scheduler;

})(window);
