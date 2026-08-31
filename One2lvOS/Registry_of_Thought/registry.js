/**
 * Registry of Thought
 * Knowledge graph and AI council consensus system
 */

class RegistryOfThought {
    constructor() {
        this.nodes = new Map();
        this.connections = [];
        this.council = null;
        this.initialized = false;
    }

    initialize(state = {}) {
        console.log('[Registry] Initializing Registry of Thought');

        // Restore state
        if (state.nodes) {
            state.nodes.forEach(node => {
                this.nodes.set(node.id, node);
            });
        }

        if (state.connections) {
            this.connections = state.connections;
        }

        // Initialize AI Council
        this.council = new AICouncil();

        this.initialized = true;
        console.log('[Registry] Registry of Thought online');

        // Emit ready event
        window.dispatchEvent(new CustomEvent('Registry:ready'));
    }

    addNode(type, data) {
        const node = {
            id: this.generateId(),
            type,
            data,
            timestamp: Date.now(),
            connections: []
        };

        this.nodes.set(node.id, node);
        console.log(`[Registry] Node added: ${node.id} (${type})`);

        return node;
    }

    connect(nodeAId, nodeBId, weight = 1.0) {
        const connection = {
            from: nodeAId,
            to: nodeBId,
            weight,
            timestamp: Date.now()
        };

        this.connections.push(connection);

        // Update node connections
        const nodeA = this.nodes.get(nodeAId);
        const nodeB = this.nodes.get(nodeBId);

        if (nodeA) nodeA.connections.push(nodeBId);
        if (nodeB) nodeB.connections.push(nodeAId);

        console.log(`[Registry] Connected: ${nodeAId} -> ${nodeBId}`);
    }

    query(filters = {}) {
        let results = Array.from(this.nodes.values());

        if (filters.type) {
            results = results.filter(node => node.type === filters.type);
        }

        if (filters.since) {
            results = results.filter(node => node.timestamp >= filters.since);
        }

        return results;
    }

    getNode(id) {
        return this.nodes.get(id);
    }

    getConnections(nodeId) {
        return this.connections.filter(
            conn => conn.from === nodeId || conn.to === nodeId
        );
    }

    getState() {
        return {
            nodes: Array.from(this.nodes.values()),
            connections: this.connections
        };
    }

    generateId() {
        return `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    // AI Council integration
    async submitToCouncil(query) {
        if (!this.council) {
            throw new Error('AI Council not initialized');
        }

        return await this.council.deliberate(query);
    }
}

/**
 * AI Council
 * Multi-agent consensus system
 */
class AICouncil {
    constructor() {
        this.agents = [
            { name: 'Analyzer', role: 'analysis', weight: 1.0 },
            { name: 'Synthesizer', role: 'synthesis', weight: 1.0 },
            { name: 'Validator', role: 'validation', weight: 1.0 },
            { name: 'Optimizer', role: 'optimization', weight: 0.8 }
        ];

        this.consensusThreshold = 0.7;
    }

    async deliberate(query) {
        console.log('[AICouncil] Deliberating:', query);

        // Simulate agent responses
        const responses = this.agents.map(agent => ({
            agent: agent.name,
            response: this.generateResponse(agent, query),
            confidence: Math.random() * 0.4 + 0.6,
            weight: agent.weight
        }));

        // Calculate consensus
        const consensus = this.calculateConsensus(responses);

        console.log('[AICouncil] Consensus reached:', consensus.score);

        return {
            query,
            responses,
            consensus,
            timestamp: Date.now()
        };
    }

    generateResponse(agent, query) {
        // Placeholder for actual AI agent logic
        return {
            suggestion: `${agent.name} suggests: Process query with ${agent.role}`,
            reasoning: `Based on ${agent.role} principles`,
            data: {}
        };
    }

    calculateConsensus(responses) {
        let totalWeight = 0;
        let weightedScore = 0;

        responses.forEach(r => {
            totalWeight += r.weight;
            weightedScore += r.confidence * r.weight;
        });

        const score = weightedScore / totalWeight;
        const reached = score >= this.consensusThreshold;

        return {
            score,
            reached,
            threshold: this.consensusThreshold
        };
    }
}

// Create global instance
window.RegistryOfThought = new RegistryOfThought();
