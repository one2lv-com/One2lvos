// Checkpoint System

(function(window) {
    'use strict';

    class Checkpoint {
        constructor() {
            this.checkpoints = [];
            this.maxCheckpoints = 10;
            this.storeKey = 'checkpoints';
        }

        async init() {
            // Load persisted checkpoints
            try {
                const stored = await Storage.get('cache', this.storeKey);
                if (stored && Array.isArray(stored.data)) {
                    this.checkpoints = stored.data;
                    Logger.info('Checkpoint', `Loaded ${this.checkpoints.length} persisted checkpoints`);
                }
            } catch (error) {
                Logger.warn('Checkpoint', 'Failed to load persisted checkpoints', error);
            }
        }

        async create(label = 'auto') {
            const checkpoint = {
                id: `checkpoint_${Date.now()}`,
                label,
                timestamp: Date.now(),
                state: await this.captureState()
            };

            this.checkpoints.push(checkpoint);

            // Keep only last N checkpoints
            if (this.checkpoints.length > this.maxCheckpoints) {
                this.checkpoints = this.checkpoints.slice(-this.maxCheckpoints);
            }

            // Persist
            await this.persist();

            Logger.info('Checkpoint', `Checkpoint created: ${label}`);
            return checkpoint.id;
        }

        async captureState() {
            return {
                registry: await Registry.snapshot(),
                filesystem: await FileSystem?.list('/', { recursive: true }) || [],
                timestamp: Date.now()
            };
        }

        async persist() {
            try {
                await Storage.set('cache', {
                    key: this.storeKey,
                    data: this.checkpoints,
                    timestamp: Date.now()
                });
            } catch (error) {
                Logger.error('Checkpoint', 'Failed to persist checkpoints', error);
            }
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

        async clear() {
            this.checkpoints = [];
            try {
                await Storage.delete('cache', this.storeKey);
            } catch (e) {
                Logger.error('Checkpoint', 'Failed to clear persisted checkpoints', e);
            }
        }
    }

    window.Checkpoint = new Checkpoint();

})(window);
