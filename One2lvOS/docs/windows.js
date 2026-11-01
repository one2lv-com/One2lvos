// Window Manager

(function(window) {
    'use strict';

    class WindowManager {
        constructor() {
            this.windows = new Map();
            this.nextId = 1;
            this.activeWindow = null;
            this.container = null;
            this.zIndex = 100;
            this.dragState = {
                active: false,
                winId: null,
                offsetX: 0,
                offsetY: 0
            };
        }

        async init() {
            this.container = document.getElementById('windows');
            if (!this.container) {
                throw new Error('WindowManager: missing #windows container');
            }
            Logger.info('WindowManager', 'Window Manager initialized');
        }

        create(options = {}) {
            const id = `window_${this.nextId++}`;
            const win = {
                id,
                title: options.title || 'Window',
                x: options.x ?? (50 + (this.windows.size * 30)),
                y: options.y ?? (50 + (this.windows.size * 30)),
                width: options.width || 600,
                height: options.height || 400,
                minimized: false,
                maximized: false,
                prevBounds: null,
                element: null
            };

            win.element = this.createWindowElement(win);
            this.container.appendChild(win.element);
            this.windows.set(id, win);

            this.bringToFront(id);
            EventBus.emit('window:created', { id });
            return id;
        }

        createWindowElement(win) {
            const el = document.createElement('div');
            el.className = 'window';
            el.dataset.winId = win.id;
            el.style.left = `${win.x}px`;
            el.style.top = `${win.y}px`;
            el.style.width = `${win.width}px`;
            el.style.height = `${win.height}px`;

            el.innerHTML = `
                <div class="window-titlebar">
                    <div class="window-title">${win.title}</div>
                    <div class="window-controls">
                        <div class="window-control minimize" title="Minimize">–</div>
                        <div class="window-control maximize" title="Maximize">□</div>
                        <div class="window-control close" title="Close">×</div>
                    </div>
                </div>
                <div class="window-content">
                    <p>Window content goes here</p>
                </div>
            `;

            const titlebar = el.querySelector('.window-titlebar');
            titlebar.addEventListener('mousedown', (e) => this.startDrag(win.id, e));

            el.querySelector('.window-control.minimize')
              .addEventListener('click', (e) => { e.stopPropagation(); this.minimize(win.id); });
            el.querySelector('.window-control.maximize')
              .addEventListener('click', (e) => { e.stopPropagation(); this.toggleMaximize(win.id); });
            el.querySelector('.window-control.close')
              .addEventListener('click', (e) => { e.stopPropagation(); this.close(win.id); });

            el.addEventListener('mousedown', () => this.bringToFront(win.id));

            return el;
        }

        bringToFront(id) {
            if (!this.windows.has(id)) return;
            this.zIndex++;
            const win = this.windows.get(id);
            win.element.style.zIndex = this.zIndex;
            this.focus(id);
        }

        focus(id) {
            if (!this.windows.has(id)) return;
            this.windows.forEach(w => w.element.classList.remove('focused'));
            const win = this.windows.get(id);
            win.element.classList.add('focused');
            this.activeWindow = id;
            EventBus.emit('window:focused', { id });
        }

        minimize(id) {
            if (!this.windows.has(id)) return;
            const win = this.windows.get(id);
            win.minimized = true;
            win.element.classList.add('minimized');
            EventBus.emit('window:minimized', { id });
        }

        restore(id) {
            if (!this.windows.has(id)) return;
            const win = this.windows.get(id);
            win.minimized = false;
            win.element.classList.remove('minimized');
            this.bringToFront(id);
            EventBus.emit('window:restored', { id });
        }

        toggleMaximize(id) {
            if (!this.windows.has(id)) return;
            const win = this.windows.get(id);

            if (win.maximized) {
                const prev = win.prevBounds;
                win.element.style.left = `${prev.x}px`;
                win.element.style.top = `${prev.y}px`;
                win.element.style.width = `${prev.width}px`;
                win.element.style.height = `${prev.height}px`;
                win.element.classList.remove('maximized');
                win.maximized = false;
            } else {
                win.prevBounds = {
                    x: win.element.offsetLeft,
                    y: win.element.offsetTop,
                    width: win.element.offsetWidth,
                    height: win.element.offsetHeight
                };
                win.element.style.left = '0px';
                win.element.style.top = '0px';
                win.element.style.width = '100vw';
                win.element.style.height = '100vh';
                win.element.classList.add('maximized');
                win.maximized = true;
                this.bringToFront(id);
            }
            EventBus.emit(win.maximized ? 'window:maximized' : 'window:restored', { id });
        }

        close(id) {
            if (!this.windows.has(id)) return;
            const win = this.windows.get(id);
            win.element.remove();
            this.windows.delete(id);
            if (this.activeWindow === id) this.activeWindow = null;
            EventBus.emit('window:closed', { id });
        }

        startDrag(id, event) {
            if (event.button !== 0) return;
            const win = this.windows.get(id);
            if (!win || win.maximized) return;

            this.dragState = {
                active: true,
                winId: id,
                offsetX: event.clientX - win.element.offsetLeft,
                offsetY: event.clientY - win.element.offsetTop
            };

            document.addEventListener('mousemove', this.onDragMove);
            document.addEventListener('mouseup', this.onDragEnd);
        }

        onDragMove = (e) => {
            if (!this.dragState.active) return;
            const win = this.windows.get(this.dragState.winId);
            if (!win) return;

            let nx = e.clientX - this.dragState.offsetX;
            let ny = e.clientY - this.dragState.offsetY;

            // Edge snapping (8px threshold)
            const snap = 8;
            if (nx < snap) nx = 0;
            if (ny < snap) ny = 0;
            const maxX = window.innerWidth - win.element.offsetWidth;
            const maxY = window.innerHeight - win.element.offsetHeight;
            if (nx > maxX - snap) nx = maxX;
            if (ny > maxY - snap) ny = maxY;

            win.element.style.left = `${nx}px`;
            win.element.style.top = `${ny}px`;
        };

        onDragEnd = () => {
            this.dragState.active = false;
            this.dragState.winId = null;
            document.removeEventListener('mousemove', this.onDragMove);
            document.removeEventListener('mouseup', this.onDragEnd);
        };

        getWindow(id) {
            return this.windows.get(id) || null;
        }

        list() {
            return Array.from(this.windows.values());
        }
    }

    window.WindowManager = new WindowManager();

})(window);
