// AI Council - Multi-agent voting system with weighted consensus
class AICouncil {
    constructor() {
        this.agents = [
            { name: 'ALPHA', weight: 0.25, bias: 'analytical' },
            { name: 'BETA', weight: 0.20, bias: 'conservative' },
            { name: 'GAMMA', weight: 0.20, bias: 'adaptive' },
            { name: 'DELTA', weight: 0.20, bias: 'aggressive' },
            { name: 'EPSILON', weight: 0.15, bias: 'exploratory' }
        ];

        this.voteHistory = [];
        this.decisionTypes = ['ATTACK', 'DEFEND', 'ADAPT', 'WAIT', 'RETREAT'];
    }

    onEvent(event) {
        // Council responds to certain events
        if (event.type === 'prediction_request' || event.type === 'decision_needed') {
            this.holdVote(event.data);
        }
    }

    holdVote(context = {}) {
        const votes = [];

        // Each agent votes based on their bias and the context
        this.agents.forEach(agent => {
            const decision = this.agentDecide(agent, context);
            const confidence = 0.5 + Math.random() * 0.5; // 0.5 to 1.0

            votes.push({
                agent: agent.name,
                weight: agent.weight,
                decision: decision,
                confidence: confidence,
                timestamp: Date.now()
            });
        });

        // Calculate weighted consensus
        const consensus = this.calculateConsensus(votes);

        // Store in history
        const voteRecord = {
            votes: votes,
            consensus: consensus,
            context: context,
            timestamp: Date.now()
        };

        this.voteHistory.push(voteRecord);

        // Trim history
        if (this.voteHistory.length > 100) {
            this.voteHistory = this.voteHistory.slice(-100);
        }

        return voteRecord;
    }

    agentDecide(agent, context) {
        // Agent decision logic based on bias
        const rand = Math.random();

        switch (agent.bias) {
            case 'analytical':
                return rand > 0.4 ? 'ADAPT' : 'WAIT';

            case 'conservative':
                return rand > 0.5 ? 'DEFEND' : 'WAIT';

            case 'adaptive':
                return rand > 0.3 ? 'ADAPT' : 'ATTACK';

            case 'aggressive':
                return rand > 0.6 ? 'ATTACK' : 'ADAPT';

            case 'exploratory':
                // Random exploration
                return this.decisionTypes[Math.floor(Math.random() * this.decisionTypes.length)];

            default:
                return 'WAIT';
        }
    }

    calculateConsensus(votes) {
        const tally = {};

        // Weighted voting
        votes.forEach(vote => {
            const score = vote.weight * vote.confidence;

            if (!tally[vote.decision]) {
                tally[vote.decision] = 0;
            }

            tally[vote.decision] += score;
        });

        // Find winner
        let winner = null;
        let maxScore = 0;

        Object.entries(tally).forEach(([decision, score]) => {
            if (score > maxScore) {
                maxScore = score;
                winner = decision;
            }
        });

        return {
            decision: winner,
            score: maxScore,
            tally: tally,
            symbolic: this.toSymbolic(winner)
        };
    }

    toSymbolic(decision) {
        // Map decision to symbolic notation
        const mapping = {
            'ATTACK': '~ | π → ∆⁹v',
            'DEFEND': '~ | √ = π',
            'ADAPT': '~ | π √ ∆ v =',
            'WAIT': '~ | π √',
            'RETREAT': '∆ v ← √ |'
        };

        return mapping[decision] || '~ | π √ =';
    }

    getLastVote() {
        return this.voteHistory[this.voteHistory.length - 1] || null;
    }

    getVoteHistory(limit = 10) {
        return this.voteHistory.slice(-limit);
    }

    getAgentStats(agentName) {
        const agentVotes = this.voteHistory.flatMap(record =>
            record.votes.filter(v => v.agent === agentName)
        );

        if (agentVotes.length === 0) return null;

        const decisionCounts = {};
        agentVotes.forEach(vote => {
            decisionCounts[vote.decision] = (decisionCounts[vote.decision] || 0) + 1;
        });

        const avgConfidence = agentVotes.reduce((sum, v) => sum + v.confidence, 0) / agentVotes.length;

        return {
            agent: agentName,
            totalVotes: agentVotes.length,
            avgConfidence: avgConfidence,
            decisionCounts: decisionCounts
        };
    }

    getAllStats() {
        return this.agents.map(agent => this.getAgentStats(agent.name));
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AICouncil;
}