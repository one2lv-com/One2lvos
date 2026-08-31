// Aurora Shader

(function(window) {
    'use strict';

    class AuroraShader {
        constructor() {
            this.canvas = null;
            this.ctx = null;
            this.time = 0;
            this.animationId = null;
            this._onResize = this.resize.bind(this);
        }

        async init(canvas) {
            if (!canvas) throw new Error('AuroraShader: canvas required');
            this.canvas = canvas;
            this.ctx = canvas.getContext('2d');

            this.resize();
            window.addEventListener('resize', this._onResize);

            this.start();
            Logger.info('AuroraShader', 'Shader initialized');
        }

        resize() {
            if (!this.canvas) return;
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
        }

        start() {
            this.canvas.classList.add('active');
            this.animate();
        }

        animate() {
            this.time += 0.01;
            const width = this.canvas.width;
            const height = this.canvas.height;

            const gradient = this.ctx.createLinearGradient(0, 0, width, height);
            gradient.addColorStop(0, `rgba(0, 217, 255, ${0.1 + Math.sin(this.time) * 0.05})`);
            gradient.addColorStop(0.5, `rgba(138, 43, 226, ${0.1 + Math.cos(this.time * 0.7) * 0.05})`);
            gradient.addColorStop(1, `rgba(0, 217, 255, ${0.1 + Math.sin(this.time * 1.2) * 0.05})`);

            this.ctx.fillStyle = gradient;
            this.ctx.fillRect(0, 0, width, height);

            this.animationId = requestAnimationFrame(() => this.animate());
        }

        stop() {
            if (this.animationId) {
                cancelAnimationFrame(this.animationId);
                this.animationId = null;
            }
            window.removeEventListener('resize', this._onResize);
            if (this.canvas) this.canvas.classList.remove('active');
        }

        destroy() {
            this.stop();
            this.canvas = null;
            this.ctx = null;
        }
    }

    window.AuroraShader = new AuroraShader();

})(window);
