// Inference Transition Table

(function(window) {
    'use strict';

    class ITT {
        constructor() {
            this.transitions = new Map();
            this.initialized = false;
        }

        async init() {
            if (this.initialized) return;

            // Load transitions from storage
            try {
                const stored = await Storage.get('cache', 'itt_transitions');
                if (stored) {
                    this.transitions = new Map(stored.data);
                }
            } catch (error) {
                Logger.error('ITT', 'Failed to load transitions', error);
            }

            this.initialized = true;
            Logger.info('ITT', `Initialized with ${this.transitions.size} transitions`);
        }

        record(from, to, context = {}) {
            const key = `${from}→${to}`;

            if (!this.transitions.has(key)) {
                this.transitions.set(key, {
                    from,
                    to,
                    count: 0,
                    contexts: []
                });
            }

            const transition = this.transitions.get(key);
            transition.count++;
            transition.contexts.push({
                ...context,
                timestamp: Date.now()
            });

            // Keep only recent contexts
            if (transition.contexts.length > 100) {
                transition.contexts = transition.contexts.slice(-100);
            }

            this.persist();
        }

        predict(from) {
            const candidates = [];

            for (const [key, transition] of this.transitions) {
                if (transition.from === from) {
                    candidates.push({
                        to: transition.to,
                        probability: transition.count,
                        confidence: Math.min(transition.count / 100, 1)
                    });
                }
            }

            // Sort by probability
            candidates.sort((a, b) => b.probability - a.probability);

            // Normalize probabilities
            const total = candidates.reduce((sum, c) => sum + c.probability, 0);
            candidates.forEach(c => {
                c.probability = total > 0 ? c.probability / total : 0;
            });

            return candidates;
        }

        async persist() {
            try {
                await Storage.set('cache', {
                    key: 'itt_transitions',
                    data: Array.from(this.transitions.entries()),
                    timestamp: Date.now()
                });
            } catch (error) {
                Logger.error('ITT', 'Failed to persist transitions', error);
            }
        }
    }

    window.ITT = new ITT();

})(window);
