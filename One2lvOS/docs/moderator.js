// Council Moderator

(function(window) {
    'use strict';

    class Moderator {
        constructor() {
            this.name = 'Moderator';
            this.role = 'Balance perspectives and facilitate decisions';
        }

        async analyze(topic, context = {}) {
            let confidence = 0.9;
            let recommendation = 'Consensus-based analysis';
            let evidence = [];

            // Check ITT for transition patterns on this topic
            if (window.ITT) {
                const predictions = ITT.predict(topic) || [];
                if (predictions.length > 0) {
                    confidence = Math.min(0.95, confidence + 0.03);
                    evidence.push(`Historical transition confidence: ${predictions[0]?.confidence?.toFixed(2) || 'unknown'}`);
                }
            }

            // Check memory for prior consensus outcomes
            if (window.ReactorMemory) {
                const prior = ReactorMemory.recall(`consensus:${topic}`);
                if (prior) {
                    confidence = Math.min(0.97, confidence + 0.02);
                    evidence.push('Prior consensus record found');
                }
            }

            return {
                perspective: 'balanced',
                recommendation: evidence.length > 0
                    ? `${recommendation} (${evidence.join('; ')})`
                    : recommendation,
                confidence,
                evidence
            };
        }
    }

    window.Moderator = new Moderator();

})(window);
