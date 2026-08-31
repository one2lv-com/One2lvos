// Glass Renderer

(function(window) {
    'use strict';

    class Renderer {
        constructor() {
            this.animationFrame = null;
            this.renderables = new Map();
            this.running = false;
        }

        register(name, fn, options = {}) {
            this.renderables.set(name, { fn, options });
            Logger.info('Renderer', `Registered renderable: ${name}`);
        }

        unregister(name) {
            const removed = this.renderables.delete(name);
            if (removed) Logger.info('Renderer', `Unregistered renderable: ${name}`);
        }

        start() {
            if (this.running) return;
            this.running = true;
            this.render();
            Logger.info('Renderer', 'Render loop started');
        }

        render() {
            if (!this.running) return;
            for (const [name, { fn }] of this.renderables) {
                try {
                    fn();
                } catch (e) {
                    Logger.error('Renderer', `Renderable "${name}" threw:`, e);
                }
            }
            this.animationFrame = requestAnimationFrame(() => this.render());
        }

        stop() {
            this.running = false;
            if (this.animationFrame) {
                cancelAnimationFrame(this.animationFrame);
                this.animationFrame = null;
            }
            Logger.info('Renderer', 'Render loop stopped');
        }
    }

    window.Renderer = new Renderer();

})(window);
