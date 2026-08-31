// Full Panel System - Drag, 8-Direction Resize, Minimize, Maximize
class PanelManager {
    constructor() {
        this.panels = new Map();
        this.zIndexCounter = 1000;
        this.activePanel = null;
    }

    createPanel(id, options = {}) {
        const defaultOptions = {
            title: 'Panel',
            x: 100,
            y: 100,
            width: 600,
            height: 400,
            minWidth: 300,
            minHeight: 200,
            resizable: true,
            draggable: true,
            closeable: true,
            maximizable: true,
            minimizable: true,
            content: '',
            onClose: null,
            onMaximize: null,
            onMinimize: null,
            onResize: null
        };

        const config = { ...defaultOptions, ...options };

        // Create panel element
        const panel = document.createElement('div');
        panel.className = 'infinity-panel';
        panel.id = id;
        panel.style.cssText = `
            position: fixed;
            left: ${config.x}px;
            top: ${config.y}px;
            width: ${config.width}px;
            height: ${config.height}px;
            z-index: ${this.zIndexCounter++};
            background: rgba(10, 12, 20, 0.95);
            border: 1px solid rgba(0, 255, 204, 0.3);
            border-radius: 8px;
            backdrop-filter: blur(20px);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 0 40px rgba(0, 255, 204, 0.2);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        `;

        // Header
        const header = document.createElement('div');
        header.className = 'panel-header';
        header.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 15px;
            background: rgba(0, 255, 204, 0.1);
            border-bottom: 1px solid rgba(0, 255, 204, 0.2);
            cursor: ${config.draggable ? 'move' : 'default'};
            user-select: none;
        `;

        const title = document.createElement('div');
        title.className = 'panel-title';
        title.textContent = config.title;
        title.style.cssText = `
            color: #00ffcc;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: bold;
        `;

        const controls = document.createElement('div');
        controls.className = 'panel-controls';
        controls.style.cssText = `
            display: flex;
            gap: 8px;
        `;

        // Control buttons
        if (config.minimizable) {
            const minBtn = this.createControlButton('−', '#ffaa00', () => this.minimizePanel(id));
            controls.appendChild(minBtn);
        }

        if (config.maximizable) {
            const maxBtn = this.createControlButton('□', '#0088ff', () => this.maximizePanel(id));
            controls.appendChild(maxBtn);
        }

        if (config.closeable) {
            const closeBtn = this.createControlButton('×', '#ff00ff', () => this.closePanel(id));
            controls.appendChild(closeBtn);
        }

        header.appendChild(title);
        header.appendChild(controls);

        // Content
        const content = document.createElement('div');
        content.className = 'panel-content';
        content.style.cssText = `
            flex: 1;
            overflow: auto;
            padding: 15px;
            color: #00ffcc;
            font-size: 12px;
        `;

        if (typeof config.content === 'string') {
            content.innerHTML = config.content;
        } else if (config.content instanceof HTMLElement) {
            content.appendChild(config.content);
        }

        // Resize handles
        const resizeHandles = [];
        if (config.resizable) {
            const directions = [
                { name: 'n', cursor: 'ns-resize', pos: 'top: 0; left: 0; right: 0; height: 5px;' },
                { name: 's', cursor: 'ns-resize', pos: 'bottom: 0; left: 0; right: 0; height: 5px;' },
                { name: 'e', cursor: 'ew-resize', pos: 'right: 0; top: 0; bottom: 0; width: 5px;' },
                { name: 'w', cursor: 'ew-resize', pos: 'left: 0; top: 0; bottom: 0; width: 5px;' },
                { name: 'ne', cursor: 'nesw-resize', pos: 'top: 0; right: 0; width: 10px; height: 10px;' },
                { name: 'nw', cursor: 'nwse-resize', pos: 'top: 0; left: 0; width: 10px; height: 10px;' },
                { name: 'se', cursor: 'nwse-resize', pos: 'bottom: 0; right: 0; width: 10px; height: 10px;' },
                { name: 'sw', cursor: 'nesw-resize', pos: 'bottom: 0; left: 0; width: 10px; height: 10px;' }
            ];

            directions.forEach(dir => {
                const handle = document.createElement('div');
                handle.className = `resize-handle resize-${dir.name}`;
                handle.style.cssText = `
                    position: absolute;
                    ${dir.pos}
                    cursor: ${dir.cursor};
                    z-index: 10;
                `;
                handle.dataset.direction = dir.name;
                resizeHandles.push(handle);
                panel.appendChild(handle);
            });
        }

        // Assemble panel
        panel.appendChild(header);
        panel.appendChild(content);
        document.body.appendChild(panel);

        // Store panel data
        const panelData = {
            element: panel,
            header: header,
            content: content,
            config: config,
            isMaximized: false,
            isMinimized: false,
            savedState: null,
            resizeHandles: resizeHandles
        };

        this.panels.set(id, panelData);

        // Setup interactions
        if (config.draggable) {
            this.setupDrag(id, header);
        }

        if (config.resizable) {
            resizeHandles.forEach(handle => {
                this.setupResize(id, handle);
            });
        }

        // Bring to front on click
        panel.addEventListener('mousedown', () => this.bringToFront(id));

        return panelData;
    }

    createControlButton(text, color, onClick) {
        const btn = document.createElement('button');
        btn.textContent = text;
        btn.style.cssText = `
            width: 20px;
            height: 20px;
            border: none;
            background: ${color};
            color: #000;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            padding: 0;
            line-height: 1;
        `;

        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'scale(1.1)';
            btn.style.boxShadow = `0 0 10px ${color}`;
        });

        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
            btn.style.boxShadow = 'none';
        });

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            onClick();
        });

        return btn;
    }

    setupDrag(id, handle) {
        let isDragging = false;
        let startX, startY, initialX, initialY;

        const onMouseDown = (e) => {
            const panel = this.panels.get(id);
            if (panel.isMaximized) return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;

            const rect = panel.element.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;

            e.preventDefault();
        };

        const onMouseMove = (e) => {
            if (!isDragging) return;

            const panel = this.panels.get(id);
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            panel.element.style.left = `${initialX + deltaX}px`;
            panel.element.style.top = `${initialY + deltaY}px`;
        };

        const onMouseUp = () => {
            isDragging = false;
        };

        handle.addEventListener('mousedown', onMouseDown);
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    setupResize(id, handle) {
        let isResizing = false;
        let startX, startY, startWidth, startHeight, startLeft, startTop;
        const direction = handle.dataset.direction;

        const onMouseDown = (e) => {
            const panel = this.panels.get(id);
            if (panel.isMaximized) return;

            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;

            const rect = panel.element.getBoundingClientRect();
            startWidth = rect.width;
            startHeight = rect.height;
            startLeft = rect.left;
            startTop = rect.top;

            e.preventDefault();
            e.stopPropagation();
        };

        const onMouseMove = (e) => {
            if (!isResizing) return;

            const panel = this.panels.get(id);
            const config = panel.config;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            let newWidth = startWidth;
            let newHeight = startHeight;
            let newLeft = startLeft;
            let newTop = startTop;

            // Calculate new dimensions based on direction
            if (direction.includes('e')) {
                newWidth = Math.max(config.minWidth, startWidth + deltaX);
            }
            if (direction.includes('w')) {
                newWidth = Math.max(config.minWidth, startWidth - deltaX);
                newLeft = startLeft + (startWidth - newWidth);
            }
            if (direction.includes('s')) {
                newHeight = Math.max(config.minHeight, startHeight + deltaY);
            }
            if (direction.includes('n')) {
                newHeight = Math.max(config.minHeight, startHeight - deltaY);
                newTop = startTop + (startHeight - newHeight);
            }

            // Apply new dimensions
            panel.element.style.width = `${newWidth}px`;
            panel.element.style.height = `${newHeight}px`;
            panel.element.style.left = `${newLeft}px`;
            panel.element.style.top = `${newTop}px`;

            if (config.onResize) {
                config.onResize(newWidth, newHeight);
            }
        };

        const onMouseUp = () => {
            isResizing = false;
        };

        handle.addEventListener('mousedown', onMouseDown);
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    bringToFront(id) {
        const panel = this.panels.get(id);
        if (!panel) return;

        panel.element.style.zIndex = this.zIndexCounter++;
        this.activePanel = id;
    }

    minimizePanel(id) {
        const panel = this.panels.get(id);
        if (!panel || panel.isMinimized) return;

        panel.isMinimized = true;
        panel.element.style.height = `${panel.header.offsetHeight}px`;
        panel.content.style.display = 'none';
        panel.resizeHandles.forEach(h => h.style.display = 'none');

        if (panel.config.onMinimize) {
            panel.config.onMinimize();
        }
    }

    restorePanel(id) {
        const panel = this.panels.get(id);
        if (!panel) return;

        if (panel.isMinimized) {
            panel.isMinimized = false;
            panel.element.style.height = `${panel.config.height}px`;
            panel.content.style.display = 'block';
            panel.resizeHandles.forEach(h => h.style.display = 'block');
        }

        if (panel.isMaximized) {
            panel.isMaximized = false;
            if (panel.savedState) {
                panel.element.style.left = `${panel.savedState.left}px`;
                panel.element.style.top = `${panel.savedState.top}px`;
                panel.element.style.width = `${panel.savedState.width}px`;
                panel.element.style.height = `${panel.savedState.height}px`;
            }
        }
    }

    maximizePanel(id) {
        const panel = this.panels.get(id);
        if (!panel) return;

        if (panel.isMaximized) {
            this.restorePanel(id);
            return;
        }

        // Save current state
        const rect = panel.element.getBoundingClientRect();
        panel.savedState = {
            left: rect.left,
            top: rect.top,
            width: rect.width,
            height: rect.height
        };

        // Maximize
        panel.isMaximized = true;
        panel.element.style.left = '0';
        panel.element.style.top = '0';
        panel.element.style.width = '100vw';
        panel.element.style.height = '100vh';
        panel.element.style.borderRadius = '0';

        if (panel.config.onMaximize) {
            panel.config.onMaximize();
        }
    }

    closePanel(id) {
        const panel = this.panels.get(id);
        if (!panel) return;

        if (panel.config.onClose) {
            panel.config.onClose();
        }

        panel.element.style.opacity = '0';
        panel.element.style.transform = 'scale(0.8)';

        setTimeout(() => {
            panel.element.remove();
            this.panels.delete(id);
        }, 300);
    }

    getPanel(id) {
        return this.panels.get(id);
    }

    updateContent(id, content) {
        const panel = this.panels.get(id);
        if (!panel) return;

        if (typeof content === 'string') {
            panel.content.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            panel.content.innerHTML = '';
            panel.content.appendChild(content);
        }
    }

    setTitle(id, title) {
        const panel = this.panels.get(id);
        if (!panel) return;

        const titleElement = panel.header.querySelector('.panel-title');
        if (titleElement) {
            titleElement.textContent = title;
        }
    }

    getAllPanels() {
        return Array.from(this.panels.keys());
    }

    closeAll() {
        this.panels.forEach((_, id) => this.closePanel(id));
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PanelManager;
}