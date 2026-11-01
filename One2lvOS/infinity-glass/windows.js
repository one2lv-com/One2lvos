// Window Manager

(function(window) {
    'use strict';

    class WindowManager {
        constructor() {
            this.windows = new Map();
            this.nextId = 1;
            this.activeWindow = null;
            this.container = null;
        }

        async init() {
            this.container = document.getElementById('windows');
            Logger.info('WindowManager', 'Window Manager initialized');
        }

        create(options = {}) {
            const id = `window_${this.nextId++}`;
            const win = {
                id,
                title: options.title || 'Window',
                x: options.x || 100,
                y: options.y || 100,
                width: options.width || 600,
                height: options.height || 400,
                minimized: false,
                maximized: false,
                element: null
            };

            win.element = this.createWindowElement(win);
            this.container.appendChild(win.element);
            this.windows.set(id, win);

            this.focus(id);
            EventBus.emit('window:created', { id });

            return id;
        }

        createWindowElement(win) {
            const el = document.createElement('div');
            el.className = 'window';
            el.style.left = `${win.x}px`;
            el.style.top = `${win.y}px`;
            el.style.width = `${win.width}px`;
            el.style.height = `${win.height}px`;

            el.innerHTML = `
                <div class="window-titlebar">
                    <div class="window-title">${win.title}</div>
                    <div class="window-controls">
                        <div class="window-control minimize"></div>
                        <div class="window-control maximize"></div>
                        <div class="window-control close"></div>
                    </div>
                </div>
                <div class="window-content">
                    <p>Window content goes here</p>
                </div>
            `;

            // Add event listeners
            const titlebar = el.querySelector('.window-titlebar');
            titlebar.addEventListener('mousedown', (e) => this.startDrag(win.id, e));

            const closeBtn = el.querySelector('.window-control.close');
            closeBtn.addEventListener('click', () => this.close(win.id));

            return el;
        }

        focus(id) {
            if (!this.windows.has(id)) return;

            // Unfocus others
            this.windows.forEach(win => {
                win.element.classList.remove('focused');
            });

            const win = this.windows.get(id);
            win.element.classList.add('focused');
            this.activeWindow = id;

            EventBus.emit('window:focused', { id });
        }

        close(id) {
            if (!this.windows.has(id)) return;

            const win = this.windows.get(id);
            win.element.remove();
            this.windows.delete(id);

            EventBus.emit('window:closed', { id });
        }

        startDrag(id, event) {
            // Simple drag implementation
            Logger.debug('WindowManager', `Dragging window: ${id}`);
        }
    }

    window.WindowManager = new WindowManager();

})(window);
