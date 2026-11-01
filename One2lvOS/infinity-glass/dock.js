// Desktop Dock

(function(window) {
    'use strict';

    class Dock {
        constructor() {
            this.items = [];
            this.element = null;
        }

        async init() {
            this.element = document.getElementById('dock');
            const itemsContainer = this.element.querySelector('.dock-items');

            // Add default apps
            const apps = [
                { id: 'terminal', icon: '⌨', label: 'Terminal' },
                { id: 'dashboard', icon: '◈', label: 'Dashboard' },
                { id: 'explorer', icon: '📁', label: 'Explorer' },
                { id: 'settings', icon: '⚙', label: 'Settings' }
            ];

            apps.forEach(app => this.addItem(app, itemsContainer));

            Logger.info('Dock', 'Dock initialized');
        }

        addItem(app, container) {
            const item = document.createElement('div');
            item.className = 'dock-item';
            item.dataset.appId = app.id;
            item.textContent = app.icon;
            item.title = app.label;

            item.addEventListener('click', () => this.launchApp(app.id));

            container.appendChild(item);
            this.items.push(app);
        }

        launchApp(appId) {
            EventBus.emit('app:launch', { appId });
            Logger.info('Dock', `Launching app: ${appId}`);

            // Create window for app
            if (window.WindowManager) {
                WindowManager.create({
                    title: appId.charAt(0).toUpperCase() + appId.slice(1),
                    width: 800,
                    height: 600
                });
            }
        }
    }

    window.Dock = new Dock();

})(window);
