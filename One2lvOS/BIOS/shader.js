/**
 * Aurora Shader System
 * Provides the visual background using WebGL shaders
 */

class AuroraShader {
    constructor(canvas) {
        this.canvas = canvas;
        this.gl = window.One2lvOS_GL;

        if (!this.gl) {
            console.error('WebGL context not available');
            return;
        }

        this.resize();
        this.init();
        this.animate();

        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;

        if (this.gl) {
            this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
        }
    }

    init() {
        const vertexShaderSource = `
            attribute vec2 position;
            void main() {
                gl_Position = vec4(position, 0.0, 1.0);
            }
        `;

        const fragmentShaderSource = `
            precision highp float;
            uniform float time;
            uniform vec2 resolution;

            void main() {
                vec2 uv = gl_FragCoord.xy / resolution;
                vec3 color = vec3(0.0);

                // Aurora waves
                for (float i = 0.0; i < 5.0; i++) {
                    float freq = 2.0 + i * 0.5;
                    float amp = 0.1 / (i + 1.0);
                    float wave = sin(uv.x * freq + time * 0.5 + i) * amp;

                    float dist = abs(uv.y - 0.5 - wave);
                    float glow = 0.01 / dist;

                    color += vec3(
                        glow * 0.3 * (1.0 - i * 0.15),
                        glow * 0.6,
                        glow * 0.9
                    );
                }

                // Nebula background
                vec2 p = uv * 2.0 - 1.0;
                float nebula = 0.0;
                for (float i = 0.0; i < 3.0; i++) {
                    vec2 offset = vec2(sin(time * 0.1 + i), cos(time * 0.15 + i));
                    nebula += 0.02 / length(p - offset * 0.5);
                }

                color += vec3(nebula * 0.1, nebula * 0.05, nebula * 0.15);

                // Vignette
                float vignette = 1.0 - length(uv - 0.5) * 0.8;
                color *= vignette;

                gl_FragColor = vec4(color * 0.6, 1.0);
            }
        `;

        // Compile shaders
        const vertexShader = this.compileShader(vertexShaderSource, this.gl.VERTEX_SHADER);
        const fragmentShader = this.compileShader(fragmentShaderSource, this.gl.FRAGMENT_SHADER);

        // Create program
        this.program = this.gl.createProgram();
        this.gl.attachShader(this.program, vertexShader);
        this.gl.attachShader(this.program, fragmentShader);
        this.gl.linkProgram(this.program);

        if (!this.gl.getProgramParameter(this.program, this.gl.LINK_STATUS)) {
            console.error('Shader program link failed:', this.gl.getProgramInfoLog(this.program));
            return;
        }

        // Create geometry (full-screen quad)
        const vertices = new Float32Array([
            -1, -1,
             1, -1,
            -1,  1,
             1,  1
        ]);

        this.buffer = this.gl.createBuffer();
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.buffer);
        this.gl.bufferData(this.gl.ARRAY_BUFFER, vertices, this.gl.STATIC_DRAW);

        // Get attribute and uniform locations
        this.positionLocation = this.gl.getAttribLocation(this.program, 'position');
        this.timeLocation = this.gl.getUniformLocation(this.program, 'time');
        this.resolutionLocation = this.gl.getUniformLocation(this.program, 'resolution');

        this.startTime = Date.now();
    }

    compileShader(source, type) {
        const shader = this.gl.createShader(type);
        this.gl.shaderSource(shader, source);
        this.gl.compileShader(shader);

        if (!this.gl.getShaderParameter(shader, this.gl.COMPILE_STATUS)) {
            console.error('Shader compile failed:', this.gl.getShaderInfoLog(shader));
            this.gl.deleteShader(shader);
            return null;
        }

        return shader;
    }

    animate() {
        const render = () => {
            const time = (Date.now() - this.startTime) / 1000;

            this.gl.clear(this.gl.COLOR_BUFFER_BIT);
            this.gl.useProgram(this.program);

            // Set uniforms
            this.gl.uniform1f(this.timeLocation, time);
            this.gl.uniform2f(this.resolutionLocation, this.canvas.width, this.canvas.height);

            // Draw
            this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.buffer);
            this.gl.enableVertexAttribArray(this.positionLocation);
            this.gl.vertexAttribPointer(this.positionLocation, 2, this.gl.FLOAT, false, 0, 0);
            this.gl.drawArrays(this.gl.TRIANGLE_STRIP, 0, 4);

            requestAnimationFrame(render);
        };

        render();
    }
}

// Initialize shader when script loads
window.AuroraShader = new AuroraShader(document.getElementById('aurora-canvas'));
