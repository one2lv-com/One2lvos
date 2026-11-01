/**
 * System Services
 * Core services that run throughout the system lifecycle
 */

class SystemServices {
    constructor() {
        this.services = new Map();
        this.initialize();
    }

    initialize() {
        // Event Bus
        this.registerService('eventBus', new EventBusService());

        // Notification Service
        this.registerService('notifications', new NotificationService());

        // Logger Service
        this.registerService('logger', new LoggerService());

        // Telemetry Service
        this.registerService('telemetry', new TelemetryService());

        console.log('[SystemServices] All services initialized');
    }

    registerService(name, service) {
        this.services.set(name, service);
        console.log(`[SystemServices] Service registered: ${name}`);
    }

    getService(name) {
        return this.services.get(name);
    }
}

// Event Bus Service
class EventBusService {
    constructor() {
        this.listeners = new Map();
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    off(event, callback) {
        if (!this.listeners.has(event)) return;

        const callbacks = this.listeners.get(event);
        const index = callbacks.indexOf(callback);

        if (index > -1) {
            callbacks.splice(index, 1);
        }
    }

    emit(event, data) {
        if (!this.listeners.has(event)) return;

        this.listeners.get(event).forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`[EventBus] Error in ${event} listener:`, error);
            }
        });
    }
}

// Notification Service
class NotificationService {
    constructor() {
        this.queue = [];
        this.container = null;
        this.createContainer();
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 350px;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            background: rgba(0, 20, 40, 0.95);
            border: 1px solid ${this.getColor(type)};
            border-radius: 6px;
            padding: 12px 16px;
            color: ${this.getColor(type)};
            font-family: 'Courier New', monospace;
            font-size: 13px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
            animation: slideIn 0.3s ease-out;
        `;

        notification.textContent = message;
        this.container.appendChild(notification);

        if (duration > 0) {
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => notification.remove(), 300);
            }, duration);
        }

        return notification;
    }

    getColor(type) {
        const colors = {
            info: '#00ffff',
            success: '#00ff00',
            warning: '#ffff00',
            error: '#ff0000'
        };
        return colors[type] || colors.info;
    }
}

// Logger Service
class LoggerService {
    constructor() {
        this.logs = [];
        this.maxLogs = 1000;
    }

    log(level, message, data = null) {
        const entry = {
            timestamp: Date.now(),
            level,
            message,
            data
        };

        this.logs.push(entry);

        if (this.logs.length > this.maxLogs) {
            this.logs.shift();
        }

        // Also log to console
        const method = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log';
        console[method](`[${level.toUpperCase()}] ${message}`, data || '');
    }

    getLogs(level = null) {
        if (!level) return this.logs;
        return this.logs.filter(log => log.level === level);
    }

    clear() {
        this.logs = [];
    }
}

// Telemetry Service
class TelemetryService {
    constructor() {
        this.metrics = {
            cpu: 0,
            memory: 0,
            fps: 0,
            events: 0
        };

        this.startMonitoring();
    }

    startMonitoring() {
        // FPS monitoring
        let lastTime = performance.now();
        let frames = 0;

        const measureFPS = () => {
            frames++;
            const now = performance.now();

            if (now >= lastTime + 1000) {
                this.metrics.fps = Math.round(frames * 1000 / (now - lastTime));
                frames = 0;
                lastTime = now;
            }

            requestAnimationFrame(measureFPS);
        };

        measureFPS();

        // Memory monitoring (if available)
        if (performance.memory) {
            setInterval(() => {
                this.metrics.memory = Math.round(
                    performance.memory.usedJSHeapSize / 1048576
                );
            }, 1000);
        }
    }

    getMetrics() {
        return { ...this.metrics };
    }

    incrementEvent() {
        this.metrics.events++;
    }
}

// Create global instance
window.SystemServices = new SystemServices();

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
