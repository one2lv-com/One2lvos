// Gesture Recognition

(function(window) {
    'use strict';

    class Gestures {
        constructor() {
            this.startX = 0;
            this.startY = 0;
            this.startTime = 0;
            this.lastTap = 0;
            this.touchId = null;
            this.threshold = 50; // px for swipe
            this.tapTimeout = 300; // ms
            this.longPressTimer = null;
            this.longPressFired = false;
        }

        init() {
            document.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
            document.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: true });
            document.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });
            document.addEventListener('touchcancel', (e) => this.handleTouchCancel(e), { passive: true });
        }

        handleTouchStart(e) {
            if (e.touches.length !== 1) return;
            const t = e.touches[0];
            this.startX = t.clientX;
            this.startY = t.clientY;
            this.startTime = Date.now();
            this.touchId = t.identifier;
            this.longPressFired = false;

            // Long press detection
            this.longPressTimer = setTimeout(() => {
                this.longPressFired = true;
                EventBus.emit('gesture:long-press', { x: this.startX, y: this.startY });
            }, 500);
        }

        handleTouchMove(e) {
            if (this.longPressTimer && e.touches.length === 1) {
                const t = e.touches[0];
                const dx = Math.abs(t.clientX - this.startX);
                const dy = Math.abs(t.clientY - this.startY);
                if (dx > 10 || dy > 10) {
                    clearTimeout(this.longPressTimer);
                    this.longPressTimer = null;
                }
            }
        }

        handleTouchEnd(e) {
            const t = e.changedTouches[0];
            if (t.identifier !== this.touchId) return;

            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }

            // If long press already fired, don't process as tap/swipe
            if (this.longPressFired) {
                this.touchId = null;
                return;
            }

            const dx = t.clientX - this.startX;
            const dy = t.clientY - this.startY;
            const dt = Date.now() - this.startTime;
            const absDx = Math.abs(dx);
            const absDy = Math.abs(dy);

            // Swipe
            if (Math.max(absDx, absDy) > this.threshold && dt < 600) {
                if (absDx > absDy) {
                    const dir = dx > 0 ? 'right' : 'left';
                    EventBus.emit('gesture:swipe', { direction: dir, axis: 'x', delta: dx });
                    EventBus.emit(`gesture:swipe-${dir}`, { delta: dx });
                } else {
                    const dir = dy > 0 ? 'down' : 'up';
                    EventBus.emit('gesture:swipe', { direction: dir, axis: 'y', delta: dy });
                    EventBus.emit(`gesture:swipe-${dir}`, { delta: dy });
                }
                this.touchId = null;
                return;
            }

            // Tap / Double-tap
            if (absDx < 10 && absDy < 10 && dt < this.tapTimeout) {
                const now = Date.now();
                if (now - this.lastTap < 300) {
                    EventBus.emit('gesture:double-tap', { x: t.clientX, y: t.clientY });
                    this.lastTap = 0;
                } else {
                    EventBus.emit('gesture:tap', { x: t.clientX, y: t.clientY });
                    this.lastTap = now;
                }
            }

            this.touchId = null;
        }

        handleTouchCancel(e) {
            if (this.longPressTimer) {
                clearTimeout(this.longPressTimer);
                this.longPressTimer = null;
            }
            this.touchId = null;
        }
    }

    window.Gestures = new Gestures();

})(window);
