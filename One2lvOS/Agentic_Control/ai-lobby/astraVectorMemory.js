/**
 * Astra DB Vector Memory Integration for One2lvOS
 * Node.js client for managing vector embeddings using NVIDIA embedding provider
 */

const axios = require('axios');

class AstraVectorMemory {
    constructor() {
        this.apiEndpoint = process.env.ASTRA_DB_API_ENDPOINT;
        this.token = process.env.ASTRA_DB_APPLICATION_TOKEN;
        this.keyspace = process.env.ASTRA_DB_KEYSPACE || 'sovereign_memory';
        this.model = process.env.ASTRA_NVIDIA_MODEL || 'nvidia/nv-embedqa-e5-v5';

        if (!this.apiEndpoint || !this.token) {
            throw new Error('ASTRA_DB credentials required');
        }

        this.headers = {
            'Token': this.token,
            'Content-Type': 'application/json'
        };

        this.collections = {
            agentMemory: 'agent_memory',
            council: 'sovereign_council',
            delta: 'delta_engine_state',
            snapshots: 'system_snapshots',
            interactions: 'user_interactions'
        };
    }

    /**
     * Make API call to Astra DB
     */
    async _apiCall(collection, payload) {
        const url = `${this.apiEndpoint}/api/json/v1/${this.keyspace}/${collection}`;
        const response = await axios.post(url, payload, { headers: this.headers });
        return response.data;
    }

    /**
     * Store agent memory with automatic NVIDIA embedding
     */
    async storeAgentMemory(agentName, content, metadata = {}) {
        const document = {
            agent: agentName,
            content: content,
            timestamp: new Date().toISOString(),
            $vectorize: content, // Automatic NVIDIA embedding
            ...metadata
        };

        const payload = {
            insertOne: {
                document: document
            }
        };

        const result = await this._apiCall(this.collections.agentMemory, payload);
        return result.status?.insertedIds?.[0];
    }

    /**
     * Search agent memories using vector similarity
     */
    async searchAgentMemory(query, agentName = null, limit = 5) {
        const payload = {
            find: {
                sort: {
                    $vectorize: query
                },
                options: {
                    limit: limit,
                    includeSimilarity: true
                }
            }
        };

        if (agentName) {
            payload.find.filter = { agent: agentName };
        }

        const result = await this._apiCall(this.collections.agentMemory, payload);
        return result.data?.documents || [];
    }

    /**
     * Store Sovereign Council deliberation
     */
    async storeCouncilDeliberation(decisionId, agents, topic, deliberation, consensus, votes) {
        const document = {
            decision_id: decisionId,
            agents: agents,
            topic: topic,
            deliberation: deliberation,
            consensus: consensus,
            votes: votes,
            timestamp: new Date().toISOString(),
            $vectorize: `${topic}: ${deliberation}`
        };

        const payload = {
            insertOne: {
                document: document
            }
        };

        const result = await this._apiCall(this.collections.council, payload);
        return result.status?.insertedIds?.[0];
    }

    /**
     * Search past council decisions
     */
    async searchCouncilDecisions(query, minConsensus = null, limit = 5) {
        const payload = {
            find: {
                sort: {
                    $vectorize: query
                },
                options: {
                    limit: limit,
                    includeSimilarity: true
                }
            }
        };

        if (minConsensus !== null) {
            payload.find.filter = {
                consensus: { $gte: minConsensus }
            };
        }

        const result = await this._apiCall(this.collections.council, payload);
        return result.data?.documents || [];
    }

    /**
     * Store Delta Engine state snapshot
     */
    async storeDeltaState(cycle, energy, stability, momentum, stateDescription, fullState) {
        const document = {
            cycle: cycle,
            energy: energy,
            stability: stability,
            momentum: momentum,
            state_description: stateDescription,
            full_state: fullState,
            timestamp: new Date().toISOString(),
            $vectorize: `Cycle ${cycle}: ${stateDescription}`
        };

        const payload = {
            insertOne: {
                document: document
            }
        };

        const result = await this._apiCall(this.collections.delta, payload);
        return result.status?.insertedIds?.[0];
    }

    /**
     * Store O2PNG snapshot metadata
     */
    async storeO2PNGSnapshot(snapshotId, generation, description, snapshotPath, metadata) {
        const document = {
            snapshot_id: snapshotId,
            generation: generation,
            description: description,
            snapshot_path: snapshotPath,
            metadata: metadata,
            timestamp: new Date().toISOString(),
            $vectorize: `Snapshot ${generation}: ${description}`
        };

        const payload = {
            insertOne: {
                document: document
            }
        };

        const result = await this._apiCall(this.collections.snapshots, payload);
        return result.status?.insertedIds?.[0];
    }

    /**
     * Search O2PNG snapshots by description
     */
    async searchSnapshots(query, limit = 5) {
        const payload = {
            find: {
                sort: {
                    $vectorize: query
                },
                options: {
                    limit: limit,
                    includeSimilarity: true
                }
            }
        };

        const result = await this._apiCall(this.collections.snapshots, payload);
        return result.data?.documents || [];
    }

    /**
     * Store user interaction
     */
    async storeUserInteraction(userId, command, response, context = {}) {
        const document = {
            user_id: userId,
            command: command,
            response: response,
            context: context,
            timestamp: new Date().toISOString(),
            $vectorize: `User: ${command}\nAssistant: ${response}`
        };

        const payload = {
            insertOne: {
                document: document
            }
        };

        const result = await this._apiCall(this.collections.interactions, payload);
        return result.status?.insertedIds?.[0];
    }

    /**
     * Get relevant context from all collections
     */
    async getRelevantContext(query, limit = 10) {
        const context = {};

        for (const [name, collection] of Object.entries(this.collections)) {
            try {
                const payload = {
                    find: {
                        sort: {
                            $vectorize: query
                        },
                        options: {
                            limit: limit,
                            includeSimilarity: true
                        }
                    }
                };

                const result = await this._apiCall(collection, payload);
                context[name] = result.data?.documents || [];
            } catch (error) {
                console.error(`Error fetching context from ${name}:`, error.message);
                context[name] = [];
            }
        }

        return context;
    }

    /**
     * Store AI model response with embeddings
     */
    async storeModelResponse(modelName, prompt, response, metadata = {}) {
        return this.storeAgentMemory(
            modelName,
            `Prompt: ${prompt}\nResponse: ${response}`,
            {
                type: 'model_response',
                model: modelName,
                prompt: prompt,
                response: response,
                ...metadata
            }
        );
    }

    /**
     * Search similar conversations
     */
    async searchSimilarConversations(query, modelName = null, limit = 5) {
        const memories = await this.searchAgentMemory(query, modelName, limit);
        return memories.filter(m => m.type === 'model_response');
    }
}

// Singleton instance
let astraMemoryInstance = null;

function getAstraMemory() {
    if (!astraMemoryInstance) {
        astraMemoryInstance = new AstraVectorMemory();
    }
    return astraMemoryInstance;
}

module.exports = {
    AstraVectorMemory,
    getAstraMemory
};
