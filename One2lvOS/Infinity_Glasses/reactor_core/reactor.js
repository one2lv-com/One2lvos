// Reactor Core - Event-driven module registry with self-healing
class ReactorCore {
    constructor() {
        this.modules = new Map();
        this.events = [];
        this.maxEvents = 1000;
        this.isRunning = false;
        this.health = 100;
        this.temperature = 0;
        this.throughput = 0;
        this.startTime = Date.now();
        this.repairQueue = [];
        this.watchdogInterval = null;
    }

    register(moduleName, moduleInstance) {
        if (this.modules.has(moduleName)) {
            console.warn(`Module ${moduleName} already registered`);
            return false;
        }

        const moduleData = {
            name: moduleName,
            instance: moduleInstance,
            health: 100,
            status: 'active',
            events: 0,
            errors: 0,
            lastActivity: Date.now(),
            registeredAt: Date.now()
        };

        this.modules.set(moduleName, moduleData);
        this.emitEvent('module_registered', { module: moduleName });

        console.log(`✓ Module registered: ${moduleName}`);
        return true;
    }

    unregister(moduleName) {
        if (!this.modules.has(moduleName)) {
            return false;
        }

        this.modules.delete(moduleName);
        this.emitEvent('module_unregistered', { module: moduleName });

        console.log(`✗ Module unregistered: ${moduleName}`);
        return true;
    }

    emitEvent(eventType, data = {}) {
        const event = {
            type: eventType,
            data: data,
            timestamp: Date.now(),
            id: this.generateEventId()
        };

        this.events.push(event);

        // Trim old events
        if (this.events.length > this.maxEvents) {
            this.events = this.events.slice(-this.maxEvents);
        }

        // Update throughput
        this.throughput++;

        // Notify modules
        this.modules.forEach((moduleData, moduleName) => {
            try {
                if (moduleData.instance && typeof moduleData.instance.onEvent === 'function') {
                    moduleData.instance.onEvent(event);
                    moduleData.events++;
                    moduleData.lastActivity = Date.now();
                }
            } catch (error) {
                console.error(`Module ${moduleName} error:`, error);
                moduleData.errors++;
                this.degradeModuleHealth(moduleName, 5);
            }
        });

        return event;
    }

    getEvents(filter = null) {
        if (!filter) {
            return this.events;
        }

        return this.events.filter(event => {
            if (filter.type && event.type !== filter.type) return false;
            if (filter.since && event.timestamp < filter.since) return false;
            if (filter.until && event.timestamp > filter.until) return false;
            return true;
        });
    }

    getModule(moduleName) {
        return this.modules.get(moduleName);
    }

    getAllModules() {
        return Array.from(this.modules.values());
    }

    getModuleStatus(moduleName) {
        const module = this.modules.get(moduleName);
        if (!module) return null;

        return {
            name: module.name,
            health: module.health,
            status: module.status,
            events: module.events,
            errors: module.errors,
            uptime: Date.now() - module.registeredAt,
            lastActivity: module.lastActivity
        };
    }

    degradeModuleHealth(moduleName, amount = 1) {
        const module = this.modules.get(moduleName);
        if (!module) return;

        module.health = Math.max(0, module.health - amount);

        if (module.health < 50 && module.status !== 'warning') {
            module.status = 'warning';
            this.emitEvent('module_warning', { module: moduleName, health: module.health });
        }

        if (module.health < 20 && module.status !== 'error') {
            module.status = 'error';
            this.emitEvent('module_error', { module: moduleName, health: module.health });
            this.queueRepair(moduleName);
        }

        if (module.health === 0) {
            module.status = 'offline';
            this.emitEvent('module_offline', { module: moduleName });
        }
    }

    repairModule(moduleName) {
        const module = this.modules.get(moduleName);
        if (!module) return false;

        const repairAmount = 30 + Math.random() * 20;
        module.health = Math.min(100, module.health + repairAmount);

        if (module.health > 50) {
            module.status = 'active';
        }

        this.emitEvent('module_repaired', { module: moduleName, health: module.health });

        console.log(`🔧 Module ${moduleName} repaired: ${module.health.toFixed(0)}% health`);
        return true;
    }

    queueRepair(moduleName) {
        if (!this.repairQueue.includes(moduleName)) {
            this.repairQueue.push(moduleName);
            console.log(`📋 Repair queued: ${moduleName}`);
        }
    }

    processRepairQueue() {
        if (this.repairQueue.length === 0) return;

        const moduleName = this.repairQueue.shift();
        this.repairModule(moduleName);
    }

    // Self-healing watchdog
    startWatchdog(interval = 5000) {
        if (this.watchdogInterval) {
            clearInterval(this.watchdogInterval);
        }

        this.watchdogInterval = setInterval(() => {
            // Check module health
            this.modules.forEach((module, name) => {
                // Natural degradation
                if (Math.random() > 0.7) {
                    this.degradeModuleHealth(name, 1);
                }

                // Check for inactive modules
                const timeSinceActivity = Date.now() - module.lastActivity;
                if (timeSinceActivity > 30000 && module.status === 'active') {
                    module.status = 'idle';
                }
            });

            // Process repair queue
            this.processRepairQueue();

            // Update reactor health
            this.updateReactorHealth();

            // Update temperature
            this.updateTemperature();

            // Reset throughput counter
            this.throughput = 0;

        }, interval);

        console.log(`🐕 Watchdog started (interval: ${interval}ms)`);
    }

    stopWatchdog() {
        if (this.watchdogInterval) {
            clearInterval(this.watchdogInterval);
            this.watchdogInterval = null;
            console.log('🐕 Watchdog stopped');
        }
    }

    updateReactorHealth() {
        const modules = Array.from(this.modules.values());
        if (modules.length === 0) {
            this.health = 100;
            return;
        }

        const avgHealth = modules.reduce((sum, m) => sum + m.health, 0) / modules.length;
        this.health = avgHealth;
    }

    updateTemperature() {
        // Temperature based on throughput and module count
        const targetTemp = (this.throughput * 0.1) + (this.modules.size * 0.5);
        this.temperature += (targetTemp - this.temperature) * 0.1;
    }

    getStatus() {
        const uptime = Date.now() - this.startTime;

        return {
            isRunning: this.isRunning,
            health: this.health,
            temperature: this.temperature,
            uptime: uptime,
            moduleCount: this.modules.size,
            activeModules: Array.from(this.modules.values()).filter(m => m.status === 'active').length,
            eventCount: this.events.length,
            throughput: this.throughput,
            repairQueueLength: this.repairQueue.length
        };
    }

    start() {
        if (this.isRunning) {
            console.warn('Reactor already running');
            return;
        }

        this.isRunning = true;
        this.startWatchdog();
        this.emitEvent('reactor_started', {});

        console.log('⚡ Reactor Core ONLINE');
    }

    stop() {
        if (!this.isRunning) {
            return;
        }

        this.isRunning = false;
        this.stopWatchdog();
        this.emitEvent('reactor_stopped', {});

        console.log('⚡ Reactor Core OFFLINE');
    }

    generateEventId() {
        return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    getUptime() {
        const uptime = Date.now() - this.startTime;
        const seconds = Math.floor(uptime / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        return {
            ms: uptime,
            seconds: seconds,
            formatted: `${days}d ${hours % 24}h ${minutes % 60}m`
        };
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ReactorCore;
}