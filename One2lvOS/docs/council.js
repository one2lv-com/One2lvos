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
                const className = name.charAt(0).toUpperCase() + name.slice(1);
                if (window[className]) {
                    this.members.push({
                        name,
                        instance: window[className]
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

            // Moderator reconciles if present
            const moderatorVote = session.votes.find(v => v.member === 'moderator');
            if (moderatorVote && session.votes.length > 1) {
                session.decision = this.moderatedDecision(session.votes, moderatorVote);
            } else {
                session.decision = this.calculateDecision(session.votes);
            }

            this.decisions.push(session);

            EventBus.emit('council:decision', session);
            Logger.info('Council', `Decision: ${session.decision.outcome}`);

            return session;
        }

        async getMemberVote(member, topic, context) {
            if (member.instance && typeof member.instance.analyze === 'function') {
                const analysis = await member.instance.analyze(topic, context);
                return {
                    support: analysis.confidence >= 0.5,
                    confidence: analysis.confidence,
                    reasoning: analysis.recommendation,
                    perspective: analysis.perspective
                };
            }

            // Fallback if analyze is unavailable
            return {
                support: Math.random() > 0.3,
                confidence: Math.random(),
                reasoning: `${member.name} perspective on ${topic}`
            };
        }

        calculateDecision(votes) {
            if (votes.length === 0) {
                return { outcome: 'undecided', support: 0, confidence: 0, votes: 0 };
            }
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

        moderatedDecision(votes, moderatorVote) {
            const base = this.calculateDecision(votes);
            // Moderator can tip a tie or reinforce consensus
            if (base.support === 0.5 && votes.length % 2 === 0) {
                base.outcome = moderatorVote.vote.support ? 'approved' : 'rejected';
                base.confidence = moderatorVote.vote.confidence;
            }
            base.moderated = true;
            return base;
        }

        getHistory() {
            return this.decisions;
        }
    }

    window.Council = new Council();

})(window);
