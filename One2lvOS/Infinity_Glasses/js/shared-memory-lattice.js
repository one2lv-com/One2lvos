/**
 * Shared Memory Lattice
 * SharedArrayBuffer-based state synchronization between reactor core and galaxy renderer
 * Allows AI Council consensus to alter star distribution and colors in real-time
 */

export class SharedMemoryLattice {
    constructor() {
        this.supportsSharedArrayBuffer = typeof SharedArrayBuffer !== 'undefined';
        this.useWorkerFallback = !this.supportsSharedArrayBuffer;

        // Memory layout (Int32Array indices)
        this.MEMORY_SIZE = 1024; // 4KB shared memory
        this.INDICES = {
            AI_CONSENSUS: 0,        // AI Council consensus value (-100 to 100)
            REACTOR_HEALTH: 1,      // Reactor core health (0-100)
            STAR_HUE_SHIFT: 2,      // Color shift for stars (-180 to 180)
            STAR_DENSITY: 3,        // Star density multiplier (0-200)
            GALAXY_ROTATION: 4,     // Galaxy rotation speed (-100 to 100)
            LATTICE_PULSE: 5,       // Memory lattice pulse rate (0-100)
            TELEMETRY_CPU: 6,       // CPU usage (0-100)
            TELEMETRY_MEM: 7,       // Memory usage (0-100)
            TELEMETRY_GPU: 8,       // GPU usage estimate (0-100)
            DELTA_TRANSFORM: 9,     // ∆ symbolic transformation state
            // Indices 10-19: Reserved for AI Council agent states
            AI_ALPHA: 10,
            AI_BETA: 11,
            AI_GAMMA: 12,
            AI_DELTA: 13,
            AI_EPSILON: 14,
            // Indices 20-99: Reserved for extended state
            LOCK: 100               // Spinlock for atomic operations
        };

        this.init();
    }

    init() {
        if (this.supportsSharedArrayBuffer) {
            this.initSharedArrayBuffer();
        } else {
            this.initWorkerFallback();
        }

        console.log(`[SharedMemoryLattice] Initialized (mode: ${this.supportsSharedArrayBuffer ? 'SharedArrayBuffer' : 'Worker fallback'})`);
    }

    initSharedArrayBuffer() {
        // Create shared memory buffer
        this.sharedBuffer = new SharedArrayBuffer(this.MEMORY_SIZE * Int32Array.BYTES_PER_ELEMENT);
        this.sharedArray = new Int32Array(this.sharedBuffer);

        // Initialize values
        Atomics.store(this.sharedArray, this.INDICES.AI_CONSENSUS, 0);
        Atomics.store(this.sharedArray, this.INDICES.REACTOR_HEALTH, 100);
        Atomics.store(this.sharedArray, this.INDICES.STAR_HUE_SHIFT, 0);
        Atomics.store(this.sharedArray, this.INDICES.STAR_DENSITY, 100);
        Atomics.store(this.sharedArray, this.INDICES.GALAXY_ROTATION, 50);
        Atomics.store(this.sharedArray, this.INDICES.LATTICE_PULSE, 60);
        Atomics.store(this.sharedArray, this.INDICES.LOCK, 0);
    }

    initWorkerFallback() {
        // Fallback: Use regular array with BroadcastChannel for sync
        this.localState = new Int32Array(this.MEMORY_SIZE);
        this.broadcastChannel = new BroadcastChannel('infinity-glass-state');

        // Listen for state updates from workers
        this.broadcastChannel.onmessage = (event) => {
            if (event.data.type === 'STATE_UPDATE') {
                const { index, value } = event.data;
                this.localState[index] = value;
                this.notifySubscribers(index, value);
            }
        };

        // Initialize values
        this.localState[this.INDICES.AI_CONSENSUS] = 0;
        this.localState[this.INDICES.REACTOR_HEALTH] = 100;
        this.localState[this.INDICES.STAR_HUE_SHIFT] = 0;
        this.localState[this.INDICES.STAR_DENSITY] = 100;
        this.localState[this.INDICES.GALAXY_ROTATION] = 50;
        this.localState[this.INDICES.LATTICE_PULSE] = 60;
    }

    // Atomic write with spinlock
    write(index, value) {
        if (this.supportsSharedArrayBuffer) {
            // Acquire lock
            while (Atomics.compareExchange(this.sharedArray, this.INDICES.LOCK, 0, 1) !== 0) {
                // Spin wait
            }

            // Write value
            Atomics.store(this.sharedArray, index, value);

            // Release lock
            Atomics.store(this.sharedArray, this.INDICES.LOCK, 0);

            // Notify waiting threads
            Atomics.notify(this.sharedArray, index, Infinity);
        } else {
            // Fallback: Write to local state and broadcast
            this.localState[index] = value;
            this.broadcastChannel.postMessage({
                type: 'STATE_UPDATE',
                index,
                value
            });
            this.notifySubscribers(index, value);
        }
    }

    // Atomic read
    read(index) {
        if (this.supportsSharedArrayBuffer) {
            return Atomics.load(this.sharedArray, index);
        } else {
            return this.localState[index];
        }
    }

    // Wait for value change (blocking in workers, polling in main thread)
    async waitForChange(index, expectedValue, timeout = 1000) {
        if (this.supportsSharedArrayBuffer) {
            const result = Atomics.wait(this.sharedArray, index, expectedValue, timeout);
            return result === 'ok';
        } else {
            // Fallback: Poll for change
            const startTime = Date.now();
            while (this.localState[index] === expectedValue) {
                if (Date.now() - startTime > timeout) {
                    return false;
                }
                await new Promise(resolve => setTimeout(resolve, 10));
            }
            return true;
        }
    }

    // Subscribe to state changes
    subscribers = new Map();

    subscribe(index, callback) {
        if (!this.subscribers.has(index)) {
            this.subscribers.set(index, new Set());
        }
        this.subscribers.get(index).add(callback);

        // Return unsubscribe function
        return () => {
            const callbacks = this.subscribers.get(index);
            if (callbacks) {
                callbacks.delete(callback);
            }
        };
    }

    notifySubscribers(index, value) {
        const callbacks = this.subscribers.get(index);
        if (callbacks) {
            callbacks.forEach(callback => callback(value));
        }
    }

    // High-level API for AI Council consensus
    setAIConsensus(value) {
        const clamped = Math.max(-100, Math.min(100, Math.round(value)));
        this.write(this.INDICES.AI_CONSENSUS, clamped);

        // Derive visual effects from consensus
        // Positive consensus: warmer colors, higher density
        // Negative consensus: cooler colors, lower density
        this.write(this.INDICES.STAR_HUE_SHIFT, Math.round(clamped * 1.8)); // -180 to 180
        this.write(this.INDICES.STAR_DENSITY, 100 + Math.round(clamped * 0.5)); // 50 to 150
    }

    getAIConsensus() {
        return this.read(this.INDICES.AI_CONSENSUS);
    }

    // Reactor health affects galaxy rotation speed
    setReactorHealth(value) {
        const clamped = Math.max(0, Math.min(100, Math.round(value)));
        this.write(this.INDICES.REACTOR_HEALTH, clamped);

        // Lower health = slower rotation
        this.write(this.INDICES.GALAXY_ROTATION, Math.round(clamped * 0.5));
    }

    getReactorHealth() {
        return this.read(this.INDICES.REACTOR_HEALTH);
    }

    // Telemetry updates
    updateTelemetry(cpu, mem, gpu) {
        this.write(this.INDICES.TELEMETRY_CPU, Math.round(cpu));
        this.write(this.INDICES.TELEMETRY_MEM, Math.round(mem));
        this.write(this.INDICES.TELEMETRY_GPU, Math.round(gpu));

        // Calculate ∆ transformation based on system load
        const avgLoad = (cpu + mem + gpu) / 3;
        const deltaState = this.calculateDeltaTransformation(avgLoad);
        this.write(this.INDICES.DELTA_TRANSFORM, deltaState);
    }

    // ∆ symbolic transformation: maps system load to visual state
    calculateDeltaTransformation(load) {
        // ∆ = change/transformation
        // Low load (0-33): Stable state (0)
        // Medium load (34-66): Active transformation (50)
        // High load (67-100): Critical transformation (100)

        if (load < 33) {
            return Math.round(load * 0.5); // 0-16
        } else if (load < 67) {
            return Math.round(25 + (load - 33) * 0.75); // 17-50
        } else {
            return Math.round(50 + (load - 67) * 1.5); // 51-100
        }
    }

    // Get all galaxy render parameters in one call (optimized)
    getGalaxyParameters() {
        return {
            hueShift: this.read(this.INDICES.STAR_HUE_SHIFT),
            density: this.read(this.INDICES.STAR_DENSITY),
            rotation: this.read(this.INDICES.GALAXY_ROTATION),
            pulse: this.read(this.INDICES.LATTICE_PULSE),
            deltaTransform: this.read(this.INDICES.DELTA_TRANSFORM),
            consensus: this.read(this.INDICES.AI_CONSENSUS)
        };
    }

    // Set AI agent state
    setAgentState(agentIndex, value) {
        const index = this.INDICES.AI_ALPHA + agentIndex;
        this.write(index, Math.round(value));
    }

    getAgentState(agentIndex) {
        const index = this.INDICES.AI_ALPHA + agentIndex;
        return this.read(index);
    }

    // Get shared buffer for workers (only works with SharedArrayBuffer)
    getSharedBuffer() {
        if (this.supportsSharedArrayBuffer) {
            return this.sharedBuffer;
        }
        return null;
    }

    // Export state snapshot
    exportSnapshot() {
        const snapshot = {};
        for (const [key, index] of Object.entries(this.INDICES)) {
            if (typeof index === 'number' && index < 100) {
                snapshot[key] = this.read(index);
            }
        }
        return snapshot;
    }

    // Import state snapshot
    importSnapshot(snapshot) {
        for (const [key, value] of Object.entries(snapshot)) {
            const index = this.INDICES[key];
            if (typeof index === 'number') {
                this.write(index, value);
            }
        }
    }

    // Debug: Log current state
    logState() {
        console.log('[SharedMemoryLattice] State:', {
            aiConsensus: this.getAIConsensus(),
            reactorHealth: this.getReactorHealth(),
            hueShift: this.read(this.INDICES.STAR_HUE_SHIFT),
            density: this.read(this.INDICES.STAR_DENSITY),
            rotation: this.read(this.INDICES.GALAXY_ROTATION),
            cpu: this.read(this.INDICES.TELEMETRY_CPU),
            mem: this.read(this.INDICES.TELEMETRY_MEM),
            gpu: this.read(this.INDICES.TELEMETRY_GPU),
            delta: this.read(this.INDICES.DELTA_TRANSFORM)
        });
    }
}

// Singleton instance
export const sharedMemoryLattice = new SharedMemoryLattice();