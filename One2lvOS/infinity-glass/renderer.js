// Glass Renderer

(function(window) {
    'use strict';

    class Renderer {
        constructor() {
            this.animationFrame = null;
        }

        render() {
            // Render loop for animations
            this.animationFrame = requestAnimationFrame(() => this.render());
        }

        stop() {
            if (this.animationFrame) {
                cancelAnimationFrame(this.animationFrame);
            }
        }
    }

    window.Renderer = new Renderer();

})(window);
