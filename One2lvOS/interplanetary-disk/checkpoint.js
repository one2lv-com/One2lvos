// Checkpoint System

(function(window) {
    'use strict';

    class Checkpoint {
        constructor() {
            this.checkpoints = [];
        }

        async create(label = 'auto') {
            const checkpoint = {
                id: `checkpoint_${Date.now()}`,
                label,
                timestamp: Date.now(),
                state: await this.captureState()
            };

            this.checkpoints.push(checkpoint);

            // Keep only last 10 checkpoints
            if (this.checkpoints.length > 10) {
                this.checkpoints = this.checkpoints.slice(-10);
            }

            Logger.info('Checkpoint', `Checkpoint created: ${label}`);
            return checkpoint.id;
        }

        async captureState() {
            return {
                registry: await Registry.snapshot(),
                timestamp: Date.now()
            };
        }

        async restore(checkpointId) {
            const checkpoint = this.checkpoints.find(c => c.id === checkpointId);
            if (!checkpoint) {
                throw new Error(`Checkpoint not found: ${checkpointId}`);
            }

            await Registry.restore(checkpoint.state.registry);
            Logger.info('Checkpoint', `Restored checkpoint: ${checkpoint.label}`);
        }

        list() {
            return this.checkpoints;
        }
    }

    window.Checkpoint = new Checkpoint();

})(window);
