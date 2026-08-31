// Recovery System

(function(window) {
    'use strict';

    class Recovery {
        async init() {
            const needsRecovery = Storage.getLocal('system_crashed', false);

            if (needsRecovery) {
                Logger.warn('Recovery', 'System crash detected, initiating recovery');
                await this.recover();
            }
        }

        async recover() {
            try {
                // Try latest snapshot first
                let snapshot = await Snapshot.load();
                if (snapshot) {
                    const valid = await Snapshot.verify(snapshot);
                    if (valid) {
                        await Snapshot.restore(snapshot);
                        Logger.info('Recovery', 'System recovered from latest snapshot');
                        Storage.setLocal('system_crashed', false);
                        return;
                    } else {
                        Logger.warn('Recovery', 'Latest snapshot corrupt, trying fallback');
                    }
                }

                // Fallback to checkpoints
                if (window.Checkpoint && Checkpoint.list().length > 0) {
                    const checkpoints = Checkpoint.list();
                    const fallback = checkpoints[checkpoints.length - 1];
                    await Checkpoint.restore(fallback.id);
                    Logger.info('Recovery', 'System recovered from checkpoint fallback');
                    Storage.setLocal('system_crashed', false);
                    return;
                }

                Logger.warn('Recovery', 'No valid snapshot or checkpoint found. Starting fresh.');
                Storage.setLocal('system_crashed', false);
            } catch (error) {
                Logger.error('Recovery', 'Recovery failed', error);
                Storage.setLocal('system_crashed', false);
            }
        }

        markCrashed() {
            Storage.setLocal('system_crashed', true);
        }
    }

    window.Recovery = new Recovery();

})(window);
