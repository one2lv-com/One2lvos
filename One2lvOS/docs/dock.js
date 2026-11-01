// Desktop Dock

(function(window) {
    'use strict';

    class Dock {
        constructor() {
            this.items = [];
            this.element = null;
            this.running = new Map(); // appId -> windowId
        }

        async init() {
            this.element = document.getElementById('dock');
            if (!this.element) {
                throw new Error('Dock: missing #dock element');
            }
            const itemsContainer = this.element.querySelector('.dock-items');
            if (!itemsContainer) {
                throw new Error('Dock: missing .dock-items container');
            }

            const apps = [
                { id: 'terminal', icon: '⌨', label: 'Terminal' },
                { id: 'dashboard', icon: '◈', label: 'Dashboard' },
                { id: 'explorer', icon: '📁', label: 'Explorer' },
                { id: 'settings', icon: '⚙', label: 'Settings' }
            ];

            apps.forEach(app => this.addItem(app, itemsContainer));

            // Listen for window closes to clear running state
            EventBus.on('window:closed', ({ id }) => {
                for (const [appId, winId] of this.running.entries()) {
                    if (winId === id) {
                        this.running.delete(appId);
                        this.setIndicator(appId, false);
                        break;
                    }
                }
            });

            Logger.info('Dock', 'Dock initialized');
        }

        addItem(app, container) {
            const item = document.createElement('div');
            item.className = 'dock-item';
            item.dataset.appId = app.id;
            item.innerHTML = `
                <span class="dock-icon">${app.icon}</span>
                <span class="dock-indicator"></span>
            `;
            item.title = app.label;

            item.addEventListener('click', () => this.launchApp(app.id));

            container.appendChild(item);
            this.items.push({ ...app, element: item });
        }

        setIndicator(appId, active) {
            const item = this.items.find(i => i.id === appId);
            if (item) {
                item.element.classList.toggle('running', active);
            }
        }

        launchApp(appId) {
            EventBus.emit('app:launch', { appId });
            Logger.info('Dock', `Launching app: ${appId}`);

            if (this.running.has(appId)) {
                const winId = this.running.get(appId);
                const win = window.WindowManager?.getWindow(winId);
                if (win) {
                    if (win.minimized) {
                        window.WindowManager.restore(winId);
                    } else {
                        window.WindowManager.bringToFront(winId);
                    }
                    return;
                }
                // Stale entry, fall through to recreate
                this.running.delete(appId);
            }

            if (window.WindowManager) {
                const winId = window.WindowManager.create({
                    title: appId.charAt(0).toUpperCase() + appId.slice(1),
                    width: 800,
                    height: 600
                });
                this.running.set(appId, winId);
                this.setIndicator(appId, true);
            }
        }
    }

    window.Dock = new Dock();

})(window);
