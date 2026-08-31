/**
 * Telemetry Pipeline
 * Collects system metrics and feeds them into ∆ (delta) symbolic transformation
 * Allows AI to "feel" hardware load as a variable in decision-making
 */

import { sharedMemoryLattice } from './shared-memory-lattice.js';

export class TelemetryPipeline {
    constructor() {
        this.metrics = {
            cpu: 0,
            memory: 0,
            gpu: 0,
            fps: 60,
            latency: 0,
            batteryLevel: 100,
            thermalState: 'nominal'
        };

        this.history = {
            cpu: [],
            memory: [],
            gpu: [],
            fps: []
        };

        this.historyLength = 60; // Keep 60 samples
        this.updateInterval = 1000; // Update every second
        this.isRunning = false;

        // Symbolic transformation states
        this.symbolicStates = {
            wave: 0,        // ~ oscillation (0-100)
            axis: 50,       // | stability (0-100)
            disc: 50,       // π rotation (0-100)
            root: 100,      // √ base magnitude (0-100)
            delta: 0,       // ∆ transformation (0-100)
            vector: 50      // v velocity (0-100)
        };

        // Performance observer for detailed metrics
        this.setupPerformanceObserver();
    }

    setupPerformanceObserver() {
        if ('PerformanceObserver' in window) {
            try {
                // Observe long tasks (> 50ms)
                const longTaskObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        // Long task detected - affects ∆ transformation
                        this.onLongTask(entry.duration);
                    }
                });
                longTaskObserver.observe({ entryTypes: ['longtask'] });

                // Observe memory pressure
                const measureObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.name === 'memory-pressure') {
                            this.onMemoryPressure(entry.detail);
                        }
                    }
                });
                measureObserver.observe({ entryTypes: ['measure'] });
            } catch (e) {
                console.warn('[TelemetryPipeline] Performance Observer not fully supported', e);
            }
        }
    }

    start() {
        if (this.isRunning) return;

        this.isRunning = true;
        this.updateLoop();

        // Setup FPS monitoring
        this.setupFPSMonitoring();

        // Setup Battery API
        this.setupBatteryMonitoring();

        console.log('[TelemetryPipeline] Started');
    }

    stop() {
        this.isRunning = false;
        if (this.fpsRAF) {
            cancelAnimationFrame(this.fpsRAF);
        }
        console.log('[TelemetryPipeline] Stopped');
    }

    async updateLoop() {
        while (this.isRunning) {
            await this.collectMetrics();
            await this.processSymbolicTransformations();
            await this.updateSharedMemory();

            await new Promise(resolve => setTimeout(resolve, this.updateInterval));
        }
    }

    async collectMetrics() {
        // CPU usage (estimate from performance timing)
        this.metrics.cpu = await this.estimateCPUUsage();

        // Memory usage
        if (performance.memory) {
            const used = performance.memory.usedJSHeapSize;
            const total = performance.memory.jsHeapSizeLimit;
            this.metrics.memory = (used / total) * 100;
        } else {
            // Fallback: estimate from long tasks
            this.metrics.memory = Math.min(this.metrics.cpu * 1.2, 100);
        }

        // GPU usage (estimate from FPS and rendering time)
        this.metrics.gpu = this.estimateGPUUsage();

        // Add to history
        this.addToHistory('cpu', this.metrics.cpu);
        this.addToHistory('memory', this.metrics.memory);
        this.addToHistory('gpu', this.metrics.gpu);
        this.addToHistory('fps', this.metrics.fps);
    }

    async estimateCPUUsage() {
        // Use navigation timing and task duration to estimate CPU
        const timing = performance.timing;
        const loadTime = timing.loadEventEnd - timing.navigationStart;

        // Get recent long tasks
        const longTasks = performance.getEntriesByType('longtask') || [];
        const recentTasks = longTasks.filter(task =>
            performance.now() - task.startTime < 5000
        );

        const taskDuration = recentTasks.reduce((sum, task) => sum + task.duration, 0);

        // Estimate: longer tasks = higher CPU usage
        const baseLoad = Math.min((taskDuration / 5000) * 100, 100);

        // Add noise from FPS (lower FPS = higher CPU)
        const fpsLoad = Math.max(0, 100 - (this.metrics.fps / 60) * 100) * 0.3;

        const cpuEstimate = Math.min(baseLoad + fpsLoad, 100);

        // Smooth using exponential moving average
        return this.metrics.cpu * 0.7 + cpuEstimate * 0.3;
    }

    estimateGPUUsage() {
        // GPU estimate: based on FPS and frame time
        const targetFPS = 60;
        const actualFPS = this.metrics.fps;

        if (actualFPS < targetFPS * 0.5) {
            // Severe performance issues
            return 90 + Math.random() * 10;
        } else if (actualFPS < targetFPS * 0.8) {
            // Moderate load
            return 60 + (1 - actualFPS / targetFPS) * 30;
        } else {
            // Normal operation
            return 20 + Math.random() * 20;
        }
    }

    setupFPSMonitoring() {
        let lastTime = performance.now();
        let frames = 0;

        const measureFPS = (currentTime) => {
            frames++;

            if (currentTime >= lastTime + 1000) {
                this.metrics.fps = Math.round((frames * 1000) / (currentTime - lastTime));
                frames = 0;
                lastTime = currentTime;
            }

            this.fpsRAF = requestAnimationFrame(measureFPS);
        };

        this.fpsRAF = requestAnimationFrame(measureFPS);
    }

    async setupBatteryMonitoring() {
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();

                this.metrics.batteryLevel = battery.level * 100;
                this.metrics.charging = battery.charging;

                battery.addEventListener('levelchange', () => {
                    this.metrics.batteryLevel = battery.level * 100;
                });

                battery.addEventListener('chargingchange', () => {
                    this.metrics.charging = battery.charging;
                });
            } catch (e) {
                console.warn('[TelemetryPipeline] Battery API not available', e);
            }
        }
    }

    addToHistory(metric, value) {
        if (!this.history[metric]) {
            this.history[metric] = [];
        }

        this.history[metric].push(value);

        if (this.history[metric].length > this.historyLength) {
            this.history[metric].shift();
        }
    }

    // Process symbolic transformations based on telemetry
    async processSymbolicTransformations() {
        const { cpu, memory, gpu, fps } = this.metrics;

        // ~ (wave): Oscillation - represents variability in load
        const cpuVariance = this.calculateVariance(this.history.cpu);
        this.symbolicStates.wave = Math.min(cpuVariance * 10, 100);

        // | (axis): Stability - inverse of load variance
        const stability = 100 - this.symbolicStates.wave;
        this.symbolicStates.axis = stability;

        // π (disc): Rotation - represents sustained activity
        const avgLoad = (cpu + memory + gpu) / 3;
        this.symbolicStates.disc = avgLoad;

        // √ (root): Base magnitude - fundamental system health
        const baseHealth = Math.min(
            (this.metrics.batteryLevel / 100) * 50 +
            (fps / 60) * 50,
            100
        );
        this.symbolicStates.root = baseHealth;

        // ∆ (delta): Transformation - rate of change in system state
        const cpuDelta = this.calculateDelta(this.history.cpu);
        const memDelta = this.calculateDelta(this.history.memory);
        const deltaIntensity = Math.abs(cpuDelta) + Math.abs(memDelta);
        this.symbolicStates.delta = Math.min(deltaIntensity * 50, 100);

        // v (vector): Velocity - direction and magnitude of change
        const trend = this.calculateTrend(this.history.cpu);
        this.symbolicStates.vector = 50 + trend * 50; // -50 to +50 = 0 to 100
    }

    calculateVariance(data) {
        if (data.length < 2) return 0;

        const mean = data.reduce((sum, val) => sum + val, 0) / data.length;
        const squaredDiffs = data.map(val => Math.pow(val - mean, 2));
        const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / data.length;

        return Math.sqrt(variance); // Standard deviation
    }

    calculateDelta(data) {
        if (data.length < 2) return 0;

        const recent = data.slice(-5); // Last 5 samples
        const older = data.slice(-10, -5); // Previous 5 samples

        if (older.length === 0) return 0;

        const recentAvg = recent.reduce((sum, val) => sum + val, 0) / recent.length;
        const olderAvg = older.reduce((sum, val) => sum + val, 0) / older.length;

        return (recentAvg - olderAvg) / 100; // Normalized delta
    }

    calculateTrend(data) {
        if (data.length < 3) return 0;

        // Simple linear regression
        const n = data.length;
        let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;

        data.forEach((y, x) => {
            sumX += x;
            sumY += y;
            sumXY += x * y;
            sumXX += x * x;
        });

        const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);

        // Normalize slope to -1 to 1
        return Math.max(-1, Math.min(1, slope / 10));
    }

    async updateSharedMemory() {
        // Update shared memory lattice with telemetry
        sharedMemoryLattice.updateTelemetry(
            this.metrics.cpu,
            this.metrics.memory,
            this.metrics.gpu
        );

        // Update lattice pulse based on system activity
        const pulseRate = 30 + (this.symbolicStates.delta * 0.7); // 30-100
        sharedMemoryLattice.write(
            sharedMemoryLattice.INDICES.LATTICE_PULSE,
            Math.round(pulseRate)
        );
    }

    // Event handlers
    onLongTask(duration) {
        // Long task detected - increase ∆ transformation
        const deltaBoost = Math.min(duration / 10, 20);
        this.symbolicStates.delta = Math.min(this.symbolicStates.delta + deltaBoost, 100);
    }

    onMemoryPressure(level) {
        // Memory pressure detected
        console.warn('[TelemetryPipeline] Memory pressure:', level);
        this.metrics.memory = Math.max(this.metrics.memory, 75);
    }

    // Public API
    getMetrics() {
        return { ...this.metrics };
    }

    getSymbolicStates() {
        return { ...this.symbolicStates };
    }

    getHistory(metric) {
        return [...(this.history[metric] || [])];
    }

    // AI decision-making helper: Should we throttle based on load?
    shouldThrottle() {
        const avgLoad = (this.metrics.cpu + this.metrics.memory + this.metrics.gpu) / 3;
        const highVariability = this.symbolicStates.wave > 70;
        const lowHealth = this.symbolicStates.root < 40;

        return avgLoad > 80 || highVariability || lowHealth;
    }

    // Get load level for AI decision-making
    getLoadLevel() {
        const avgLoad = (this.metrics.cpu + this.metrics.memory + this.metrics.gpu) / 3;

        if (avgLoad < 33) return 'LOW';
        if (avgLoad < 67) return 'MEDIUM';
        return 'HIGH';
    }

    // Export telemetry for logging/analysis
    exportTelemetry() {
        return {
            timestamp: Date.now(),
            metrics: this.getMetrics(),
            symbolic: this.getSymbolicStates(),
            history: {
                cpu: this.getHistory('cpu'),
                memory: this.getHistory('memory'),
                gpu: this.getHistory('gpu'),
                fps: this.getHistory('fps')
            }
        };
    }
}

// Singleton instance
export const telemetryPipeline = new TelemetryPipeline();