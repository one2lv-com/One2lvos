/**
 * Agentic Control Subsystem - Agent Manager
 * Handles local agent lifecycles, task delegation, and execution logs.
 */
class AgentManager {
    constructor() {
        this.name = 'AgentManager';
        this.agents = new Map();
        this.activeWorkflows = [];
        this.isInitialized = false;
    }

    async initialize(state = {}) {
        console.log(`[${this.name}] Initializing Agentic Control...`);
        
        // Register default system agents
        this.registerAgent('Sentinel', 'Monitoring', 'System health & auto-save integrity');
        this.registerAgent('Synthesis', 'Reasoning', 'Query processing & Council integration');

        if (state.agents) {
            state.agents.forEach(a => this.registerAgent(a.name, a.role, a.description));
        }

        // Connect to System EventBus if available
        if (window.SystemServices && window.SystemServices.getService('eventBus')) {
            const eventBus = window.SystemServices.getService('eventBus');
            eventBus.subscribe('SYSTEM_TICK', (data) => this.onSystemTick(data));
        }

        this.isInitialized = true;
        console.log(`[${this.name}] Active with ${this.agents.size} agents online.`);
    }

    registerAgent(name, role, description) {
        const agent = {
            id: `agent_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
            name,
            role,
            description,
            status: 'IDLE',
            lastActive: Date.now()
        };
        this.agents.set(name, agent);
        return agent;
    }

    dispatchTask(agentName, taskPayload) {
        const agent = this.agents.get(agentName);
        if (!agent) {
            console.warn(`[${this.name}] Agent '${agentName}' not found.`);
            return false;
        }

        agent.status = 'BUSY';
        agent.lastActive = Date.now();
        console.log(`[${this.name}] Agent '${agentName}' executing task:`, taskPayload);

        // Simulate asynchronous task resolution
        setTimeout(() => {
            agent.status = 'IDLE';
            if (window.SystemServices && window.SystemServices.getService('notifications')) {
                window.SystemServices.getService('notifications').notify(
                    `Agent ${agentName} completed task.`, 'info'
                );
            }
        }, 1200);

        return true;
    }

    onSystemTick(data) {
        // Periodic background cleanup or execution checks
    }

    getState() {
        return {
            agents: Array.from(this.agents.values())
        };
    }
}

// Mount to global window for dynamic loading
window.AgentManager = new AgentManager();

