/**
 * AI Council
 * Multi-agent decision system with shared memory integration
 * Agents vote on actions based on telemetry and symbolic transformations
 */

import { sharedMemoryLattice } from './shared-memory-lattice.js';
import { telemetryPipeline } from './telemetry-pipeline.js';

export class AICouncil {
    constructor() {
        this.agents = [
            { name: 'Alpha', role: 'Security', weight: 1.2, bias: 'conservative' },
            { name: 'Beta', role: 'Performance', weight: 1.0, bias: 'aggressive' },
            { name: 'Gamma', role: 'Balance', weight: 1.5, bias: 'neutral' },
            { name: 'Delta', role: 'Innovation', weight: 0.8, bias: 'experimental' },
            { name: 'Epsilon', role: 'Stability', weight: 1.3, bias: 'cautious' }
        ];

        this.votingHistory = [];
        this.decisionThreshold = 0.6;
    }

    // Main decision-making function
    async makeDecision(situation, options) {
        const votes = [];
        const telemetry = telemetryPipeline.getMetrics();
        const symbolic = telemetryPipeline.getSymbolicStates();

        // Each agent votes based on its role and current system state
        for (let i = 0; i < this.agents.length; i++) {
            const agent = this.agents[i];
            const vote = await this.agentVote(agent, situation, options, telemetry, symbolic);

            votes.push({
                agent: agent.name,
                option: vote.option,
                confidence: vote.confidence,
                reasoning: vote.reasoning
            });

            // Update shared memory with agent state
            sharedMemoryLattice.setAgentState(i, Math.round(vote.confidence * 100));
        }

        // Calculate weighted consensus
        const consensus = this.calculateConsensus(votes, options);

        // Update shared memory with consensus
        const consensusValue = (consensus.confidence * 100) * (consensus.positive ? 1 : -1);
        sharedMemoryLattice.setAIConsensus(consensusValue);

        // Store in history
        this.votingHistory.push({
            timestamp: Date.now(),
            situation,
            votes,
            consensus,
            telemetry: { ...telemetry },
            symbolic: { ...symbolic }
        });

        // Keep only last 100 decisions
        if (this.votingHistory.length > 100) {
            this.votingHistory.shift();
        }

        return consensus;
    }

    async agentVote(agent, situation, options, telemetry, symbolic) {
        // Agent decision-making based on role and system state

        switch (agent.role) {
            case 'Security':
                return this.securityAgentVote(agent, situation, options, telemetry, symbolic);

            case 'Performance':
                return this.performanceAgentVote(agent, situation, options, telemetry, symbolic);

            case 'Balance':
                return this.balanceAgentVote(agent, situation, options, telemetry, symbolic);

            case 'Innovation':
                return this.innovationAgentVote(agent, situation, options, telemetry, symbolic);

            case 'Stability':
                return this.stabilityAgentVote(agent, situation, options, telemetry, symbolic);

            default:
                return { option: options[0], confidence: 0.5, reasoning: 'Default vote' };
        }
    }

    securityAgentVote(agent, situation, options, telemetry, symbolic) {
        // Security agent prioritizes safe, proven options
        // Influenced by system stability (|) and root (√)

        const stability = symbolic.axis / 100;  // | axis stability
        const baseHealth = symbolic.root / 100;  // √ base magnitude

        let preference = options[0];  // Default to first option
        let confidence = 0.5;

        // If system is unstable, prefer conservative options
        if (stability < 0.4 || baseHealth < 0.4) {
            preference = this.findConservativeOption(options);
            confidence = 0.8;
        } else {
            // System stable, can consider riskier options
            confidence = 0.6;
        }

        return {
            option: preference,
            confidence: confidence * agent.weight,
            reasoning: `Security: stability=${stability.toFixed(2)}, health=${baseHealth.toFixed(2)}`
        };
    }

    performanceAgentVote(agent, situation, options, telemetry, symbolic) {
        // Performance agent prioritizes speed and efficiency
        // Influenced by ∆ (transformation) and v (velocity)

        const load = (telemetry.cpu + telemetry.memory + telemetry.gpu) / 3;
        const delta = symbolic.delta / 100;  // ∆ transformation intensity
        const velocity = (symbolic.vector - 50) / 50;  // v normalized to -1 to 1

        let preference = options[0];
        let confidence = 0.5;

        // If load is high, throttle or optimize
        if (load > 70) {
            preference = this.findOptimizationOption(options);
            confidence = 0.9;
        } else if (velocity > 0.5) {
            // System trending up, can push harder
            preference = this.findAggressiveOption(options);
            confidence = 0.7;
        }

        return {
            option: preference,
            confidence: confidence * agent.weight,
            reasoning: `Performance: load=${load.toFixed(1)}%, delta=${delta.toFixed(2)}`
        };
    }

    balanceAgentVote(agent, situation, options, telemetry, symbolic) {
        // Balance agent seeks equilibrium
        // Influenced by ~ (wave) and π (disc/rotation)

        const wave = symbolic.wave / 100;  // ~ oscillation
        const disc = symbolic.disc / 100;  // π rotation/activity

        let preference = this.findMiddleGroundOption(options);
        let confidence = 0.7;

        // High variability? Seek stability
        if (wave > 0.7) {
            preference = this.findStabilizingOption(options);
            confidence = 0.85;
        }

        return {
            option: preference,
            confidence: confidence * agent.weight,
            reasoning: `Balance: wave=${wave.toFixed(2)}, disc=${disc.toFixed(2)}`
        };
    }

    innovationAgentVote(agent, situation, options, telemetry, symbolic) {
        // Innovation agent explores new possibilities
        // Less weight, but can suggest creative solutions

        const delta = symbolic.delta / 100;
        const stability = symbolic.axis / 100;

        let preference = this.findInnovativeOption(options);
        let confidence = 0.6;

        // High transformation rate? Time for innovation
        if (delta > 0.6 && stability > 0.5) {
            confidence = 0.8;
        }

        return {
            option: preference,
            confidence: confidence * agent.weight,
            reasoning: `Innovation: exploring new approaches`
        };
    }

    stabilityAgentVote(agent, situation, options, telemetry, symbolic) {
        // Stability agent resists change unless necessary
        // High weight, conservative approach

        const stability = symbolic.axis / 100;
        const wave = symbolic.wave / 100;

        let preference = this.findStableOption(options);
        let confidence = 0.75;

        // System unstable? Strongly advocate for stability
        if (stability < 0.5 || wave > 0.7) {
            confidence = 0.95;
        }

        return {
            option: preference,
            confidence: confidence * agent.weight,
            reasoning: `Stability: maintaining system integrity`
        };
    }

    calculateConsensus(votes, options) {
        // Weighted voting system
        const scores = {};

        // Initialize scores
        options.forEach(option => {
            scores[option] = 0;
        });

        // Accumulate weighted votes
        votes.forEach(vote => {
            scores[vote.option] += vote.confidence;
        });

        // Find winner
        let winner = null;
        let maxScore = 0;
        let totalScore = 0;

        for (const [option, score] of Object.entries(scores)) {
            totalScore += score;
            if (score > maxScore) {
                maxScore = score;
                winner = option;
            }
        }

        // Calculate confidence as percentage of total
        const confidence = maxScore / totalScore;

        // Determine if consensus is positive or negative
        const positive = winner && !winner.toLowerCase().includes('reject');

        return {
            decision: winner,
            confidence,
            positive,
            votes,
            scores,
            notation: this.generateSymbolicNotation(confidence, positive)
        };
    }

    // Option selection helpers
    findConservativeOption(options) {
        const keywords = ['safe', 'maintain', 'stable', 'continue', 'keep'];
        return this.findOptionByKeywords(options, keywords) || options[0];
    }

    findAggressiveOption(options) {
        const keywords = ['increase', 'accelerate', 'push', 'maximize', 'boost'];
        return this.findOptionByKeywords(options, keywords) || options[options.length - 1];
    }

    findOptimizationOption(options) {
        const keywords = ['optimize', 'reduce', 'throttle', 'limit', 'conserve'];
        return this.findOptionByKeywords(options, keywords) || options[0];
    }

    findMiddleGroundOption(options) {
        return options[Math.floor(options.length / 2)];
    }

    findStabilizingOption(options) {
        const keywords = ['stabilize', 'normalize', 'balance', 'regulate'];
        return this.findOptionByKeywords(options, keywords) || this.findMiddleGroundOption(options);
    }

    findInnovativeOption(options) {
        const keywords = ['new', 'experimental', 'try', 'test', 'explore'];
        return this.findOptionByKeywords(options, keywords) || options[Math.floor(Math.random() * options.length)];
    }

    findStableOption(options) {
        const keywords = ['maintain', 'hold', 'wait', 'stable', 'current'];
        return this.findOptionByKeywords(options, keywords) || options[0];
    }

    findOptionByKeywords(options, keywords) {
        for (const option of options) {
            const optionLower = option.toLowerCase();
            for (const keyword of keywords) {
                if (optionLower.includes(keyword)) {
                    return option;
                }
            }
        }
        return null;
    }

    // Generate symbolic notation for consensus
    generateSymbolicNotation(confidence, positive) {
        // Map consensus to symbolic transformation
        // ~|π√∆v=

        const symbols = [];

        // ~ (wave): confidence variability
        if (confidence < 0.5) {
            symbols.push('~');  // High oscillation/uncertainty
        }

        // | (axis): strong conviction
        if (confidence > 0.8) {
            symbols.push('|');  // Stable axis
        }

        // π (disc): rotation/activity
        symbols.push('π');

        // √ (root): fundamental decision
        if (positive) {
            symbols.push('√');
        }

        // ∆ (transformation): change direction
        symbols.push('∆');

        // v (vector): direction
        symbols.push(positive ? 'v↑' : 'v↓');

        // = (result)
        symbols.push('=');

        // Final state
        symbols.push(confidence > this.decisionThreshold ? '✓' : '?');

        return symbols.join('');
    }

    // Get consensus status for display
    getConsensusStatus() {
        if (this.votingHistory.length === 0) {
            return {
                consensus: 0,
                confidence: 0,
                lastDecision: 'None',
                agentStates: this.agents.map(a => ({ name: a.name, state: 50 }))
            };
        }

        const latest = this.votingHistory[this.votingHistory.length - 1];
        const consensusValue = (latest.consensus.confidence * 100) * (latest.consensus.positive ? 1 : -1);

        return {
            consensus: Math.round(consensusValue),
            confidence: Math.round(latest.consensus.confidence * 100),
            lastDecision: latest.consensus.decision,
            notation: latest.consensus.notation,
            agentStates: latest.votes.map((v, i) => ({
                name: v.agent,
                state: Math.round(v.confidence * 100),
                vote: v.option,
                reasoning: v.reasoning
            }))
        };
    }

    // Get voting history
    getHistory(limit = 10) {
        return this.votingHistory.slice(-limit);
    }

    // Clear history
    clearHistory() {
        this.votingHistory = [];
    }
}

// Singleton instance
export const aiCouncil = new AICouncil();