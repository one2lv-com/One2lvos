// Council Decision System

(function(window) {
    'use strict';

    class Council {
        constructor() {
            this.members = [];
            this.decisions = [];
            this.initialized = false;
        }

        async init() {
            if (this.initialized) return;

            const memberNames = Config.get('council.members', ['architect', 'witness', 'observer', 'moderator']);

            for (const name of memberNames) {
                if (window[name.charAt(0).toUpperCase() + name.slice(1)]) {
                    this.members.push({
                        name,
                        instance: window[name.charAt(0).toUpperCase() + name.slice(1)]
                    });
                }
            }

            this.initialized = true;
            Logger.info('Council', `Initialized with ${this.members.length} members`);
        }

        async deliberate(topic, context = {}) {
            Logger.info('Council', `Deliberating: ${topic}`);

            const session = {
                id: `session_${Date.now()}`,
                topic,
                context,
                votes: [],
                decision: null,
                timestamp: Date.now()
            };

            // Collect votes from members
            for (const member of this.members) {
                try {
                    const vote = await this.getMemberVote(member, topic, context);
                    session.votes.push({
                        member: member.name,
                        vote,
                        timestamp: Date.now()
                    });
                } catch (error) {
                    Logger.error('Council', `Member ${member.name} failed to vote`, error);
                }
            }

            // Calculate decision
            session.decision = this.calculateDecision(session.votes);
            this.decisions.push(session);

            EventBus.emit('council:decision', session);
            Logger.info('Council', `Decision: ${session.decision.outcome}`);

            return session;
        }

        async getMemberVote(member, topic, context) {
            // Default vote logic
            return {
                support: Math.random() > 0.3,
                confidence: Math.random(),
                reasoning: `${member.name} perspective on ${topic}`
            };
        }

        calculateDecision(votes) {
            const support = votes.filter(v => v.vote.support).length;
            const total = votes.length;
            const confidence = votes.reduce((sum, v) => sum + v.vote.confidence, 0) / total;

            return {
                outcome: support / total >= 0.5 ? 'approved' : 'rejected',
                support: support / total,
                confidence,
                votes: total
            };
        }

        getHistory() {
            return this.decisions;
        }
    }

    window.Council = new Council();

})(window);
