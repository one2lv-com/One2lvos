// Three.js Galaxy Renderer with 10K+ Stars
class GalaxyRenderer {
    constructor(containerElement) {
        this.container = containerElement;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.stars = [];
        this.spiralArms = [];
        this.blackHole = null;
        this.accretionDisc = null;
        this.animationId = null;
        this.isRotating = true;
        this.rotationSpeed = 0.0002;

        this.init();
    }

    init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x000000, 0.00015);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            75,
            this.container.clientWidth / this.container.clientHeight,
            0.1,
            2000
        );
        this.camera.position.set(0, 200, 500);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Create galaxy components
        this.createSagittariusA();
        this.createAccretionDisc();
        this.createStarfield();
        this.createSpiralArms();

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0x00ffcc, 2, 500);
        pointLight.position.set(0, 0, 0);
        this.scene.add(pointLight);

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());

        // Mouse interaction
        this.setupMouseControls();

        // Start animation
        this.animate();

        console.log('Galaxy renderer initialized with', this.stars.length, 'stars');
    }

    createSagittariusA() {
        // Central black hole
        const geometry = new THREE.SphereGeometry(8, 32, 32);
        const material = new THREE.MeshBasicMaterial({
            color: 0x000000,
            transparent: true,
            opacity: 0.95
        });

        this.blackHole = new THREE.Mesh(geometry, material);
        this.scene.add(this.blackHole);

        // Event horizon glow
        const glowGeometry = new THREE.SphereGeometry(10, 32, 32);
        const glowMaterial = new THREE.ShaderMaterial({
            uniforms: {
                c: { type: 'f', value: 0.5 },
                p: { type: 'f', value: 4.5 },
                glowColor: { type: 'c', value: new THREE.Color(0x00ffcc) },
                viewVector: { type: 'v3', value: this.camera.position }
            },
            vertexShader: `
                uniform vec3 viewVector;
                uniform float c;
                uniform float p;
                varying float intensity;
                void main() {
                    vec3 vNormal = normalize(normalMatrix * normal);
                    vec3 vNormel = normalize(normalMatrix * viewVector);
                    intensity = pow(c - dot(vNormal, vNormel), p);
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform vec3 glowColor;
                varying float intensity;
                void main() {
                    vec3 glow = glowColor * intensity;
                    gl_FragColor = vec4(glow, 1.0);
                }
            `,
            side: THREE.FrontSide,
            blending: THREE.AdditiveBlending,
            transparent: true
        });

        const glow = new THREE.Mesh(glowGeometry, glowMaterial);
        this.scene.add(glow);
    }

    createAccretionDisc() {
        const rings = [];

        // Create multiple rings for depth
        for (let i = 0; i < 5; i++) {
            const innerRadius = 15 + i * 5;
            const outerRadius = innerRadius + 8;

            const geometry = new THREE.RingGeometry(innerRadius, outerRadius, 64);
            const material = new THREE.MeshBasicMaterial({
                color: new THREE.Color().setHSL(0.55 + i * 0.05, 1.0, 0.5),
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.6 - i * 0.1
            });

            const ring = new THREE.Mesh(geometry, material);
            ring.rotation.x = Math.PI / 2 + (Math.random() - 0.5) * 0.1;
            rings.push(ring);
            this.scene.add(ring);
        }

        this.accretionDisc = rings;
    }

    createStarfield() {
        const starCount = 10247;

        // Create star geometry
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(starCount * 3);
        const colors = new Float32Array(starCount * 3);
        const sizes = new Float32Array(starCount);

        for (let i = 0; i < starCount; i++) {
            const i3 = i * 3;

            // Position - spherical distribution with galaxy shape
            const radius = Math.random() * 800 + 100;
            const theta = Math.random() * Math.PI * 2;
            const phi = (Math.random() - 0.5) * Math.PI * 0.3; // Flatten to disc

            positions[i3] = radius * Math.cos(theta) * Math.cos(phi);
            positions[i3 + 1] = radius * Math.sin(phi) * 0.2; // Flatten Y axis
            positions[i3 + 2] = radius * Math.sin(theta) * Math.cos(phi);

            // Color based on distance from center
            const dist = radius / 900;
            if (dist < 0.3) {
                // Core - cyan/white
                colors[i3] = 0.5 + Math.random() * 0.5;
                colors[i3 + 1] = 0.8 + Math.random() * 0.2;
                colors[i3 + 2] = 1.0;
            } else if (dist < 0.7) {
                // Mid - blue/purple
                colors[i3] = 0.3 + Math.random() * 0.4;
                colors[i3 + 1] = 0.3 + Math.random() * 0.4;
                colors[i3 + 2] = 0.8 + Math.random() * 0.2;
            } else {
                // Outer - dimmer, redder
                colors[i3] = 0.6 + Math.random() * 0.4;
                colors[i3 + 1] = 0.4 + Math.random() * 0.3;
                colors[i3 + 2] = 0.5 + Math.random() * 0.3;
            }

            // Size variation
            sizes[i] = Math.random() * 2 + 0.5;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        // Star material
        const material = new THREE.PointsMaterial({
            size: 2,
            sizeAttenuation: true,
            vertexColors: true,
            transparent: true,
            opacity: 0.9,
            blending: THREE.AdditiveBlending
        });

        const starField = new THREE.Points(geometry, material);
        this.stars.push(starField);
        this.scene.add(starField);
    }

    createSpiralArms() {
        const armCount = 4;
        const particlesPerArm = 1500;

        for (let arm = 0; arm < armCount; arm++) {
            const geometry = new THREE.BufferGeometry();
            const positions = new Float32Array(particlesPerArm * 3);
            const colors = new Float32Array(particlesPerArm * 3);

            for (let i = 0; i < particlesPerArm; i++) {
                const i3 = i * 3;

                const radius = (i / particlesPerArm) * 600 + 100;
                const spinAngle = (i / particlesPerArm) * Math.PI * 4;
                const armAngle = (arm / armCount) * Math.PI * 2;
                const totalAngle = armAngle + spinAngle;

                // Add some randomness for natural look
                const randomRadius = radius + (Math.random() - 0.5) * 50;
                const randomAngle = totalAngle + (Math.random() - 0.5) * 0.3;
                const randomHeight = (Math.random() - 0.5) * 20;

                positions[i3] = randomRadius * Math.cos(randomAngle);
                positions[i3 + 1] = randomHeight;
                positions[i3 + 2] = randomRadius * Math.sin(randomAngle);

                // Gradient color along arm
                const t = i / particlesPerArm;
                const hue = 0.5 + arm * 0.1 + t * 0.1;
                const color = new THREE.Color().setHSL(hue, 1.0, 0.5);

                colors[i3] = color.r;
                colors[i3 + 1] = color.g;
                colors[i3 + 2] = color.b;
            }

            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

            const material = new THREE.PointsMaterial({
                size: 3,
                vertexColors: true,
                transparent: true,
                opacity: 0.8,
                blending: THREE.AdditiveBlending
            });

            const spiralArm = new THREE.Points(geometry, material);
            this.spiralArms.push(spiralArm);
            this.scene.add(spiralArm);
        }
    }

    setupMouseControls() {
        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };

        this.renderer.domElement.addEventListener('mousedown', (e) => {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        this.renderer.domElement.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;

            this.camera.position.x += deltaX * 0.5;
            this.camera.position.y -= deltaY * 0.5;

            this.camera.lookAt(0, 0, 0);

            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        this.renderer.domElement.addEventListener('mouseup', () => {
            isDragging = false;
        });

        this.renderer.domElement.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY * 0.5;
            const distance = Math.sqrt(
                this.camera.position.x ** 2 +
                this.camera.position.y ** 2 +
                this.camera.position.z ** 2
            );

            const newDistance = Math.max(100, Math.min(1000, distance + delta));
            const scale = newDistance / distance;

            this.camera.position.multiplyScalar(scale);
        });
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        if (this.isRotating) {
            // Rotate galaxy
            this.stars.forEach(star => {
                star.rotation.y += this.rotationSpeed;
            });

            this.spiralArms.forEach(arm => {
                arm.rotation.y += this.rotationSpeed * 1.5;
            });

            // Rotate accretion disc
            this.accretionDisc.forEach((ring, index) => {
                ring.rotation.z += this.rotationSpeed * (5 - index) * 0.5;
            });

            // Pulse black hole
            if (this.blackHole) {
                const scale = 1 + Math.sin(Date.now() * 0.001) * 0.05;
                this.blackHole.scale.set(scale, scale, scale);
            }
        }

        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }

    toggleRotation() {
        this.isRotating = !this.isRotating;
    }

    setRotationSpeed(speed) {
        this.rotationSpeed = speed;
    }

    resetCamera() {
        this.camera.position.set(0, 200, 500);
        this.camera.lookAt(0, 0, 0);
    }

    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }

        // Dispose geometries and materials
        this.scene.traverse((object) => {
            if (object.geometry) {
                object.geometry.dispose();
            }
            if (object.material) {
                if (Array.isArray(object.material)) {
                    object.material.forEach(material => material.dispose());
                } else {
                    object.material.dispose();
                }
            }
        });

        this.renderer.dispose();
        this.container.removeChild(this.renderer.domElement);
    }

    getStats() {
        return {
            stars: this.stars.reduce((sum, field) => sum + field.geometry.attributes.position.count, 0),
            spiralArms: this.spiralArms.length,
            accretionRings: this.accretionDisc.length,
            fps: this.renderer.info.render.fps || 60,
            triangles: this.renderer.info.render.triangles,
            calls: this.renderer.info.render.calls
        };
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GalaxyRenderer;
}