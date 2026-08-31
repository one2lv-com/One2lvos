// Snapshot System

(function(window) {
    'use strict';

    class Snapshot {
        constructor() {
            this.version = '1.0.0';
        }

        async create() {
            const snapshot = {
                version: this.version,
                timestamp: Date.now(),
                registry: await Registry.snapshot(),
                config: Config.toJSON(),
                filesystem: await this.captureFilesystem(),
                memory: this.captureMemory(),
                itt: this.captureITT(),
                desktop: this.captureDesktop(),
                checksum: null
            };

            // Compute simple checksum for integrity
            snapshot.checksum = await this.computeChecksum(snapshot);

            try {
                await Storage.set('snapshots', {
                    id: 'latest',
                    data: snapshot,
                    timestamp: Date.now()
                });

                Logger.info('Snapshot', 'Snapshot created');
                return snapshot;
            } catch (error) {
                Logger.error('Snapshot', 'Failed to create snapshot', error);
                throw error;
            }
        }

        async captureFilesystem() {
            if (!window.FileSystem) return { files: [], dirs: [] };
            return {
                files: FileSystem.list('/', { recursive: true }),
                dirs: Array.from(FileSystem.dirs || [])
            };
        }

        captureMemory() {
            if (!window.ReactorMemory) return { shortTerm: [], longTerm: [] };
            return {
                shortTerm: Array.from(ReactorMemory.shortTerm?.entries() || []),
                longTerm: Array.from(ReactorMemory.longTerm?.entries() || [])
            };
        }

        captureITT() {
            if (!window.ITT) return { transitions: [] };
            return {
                transitions: Array.from(ITT.transitions?.entries() || [])
            };
        }

        captureDesktop() {
            const desktop = {
                windows: [],
                theme: Config.get('infinityGlass.theme', 'dark'),
                dock: []
            };

            if (window.WindowManager) {
                desktop.windows = WindowManager.list().map(w => ({
                    id: w.id,
                    title: w.title,
                    x: w.x,
                    y: w.y,
                    width: w.width,
                    height: w.height,
                    minimized: w.minimized,
                    maximized: w.maximized
                }));
            }

            return desktop;
        }

        async computeChecksum(snapshot) {
            // Simple hash of core data for integrity verification
            const str = JSON.stringify({
                registry: snapshot.registry,
                config: snapshot.config,
                timestamp: snapshot.timestamp,
                version: snapshot.version
            });
            let hash = 0;
            for (let i = 0; i < str.length; i++) {
                const char = str.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash |= 0;
            }
            return hash.toString(16);
        }

        async load() {
            try {
                const stored = await Storage.get('snapshots', 'latest');
                if (stored) {
                    Logger.info('Snapshot', 'Snapshot loaded');
                    return stored.data;
                }
            } catch (error) {
                Logger.error('Snapshot', 'Failed to load snapshot', error);
            }
            return null;
        }

        async verify(snapshot) {
            if (!snapshot) return false;
            if (!snapshot.checksum) return false;
            const expected = await this.computeChecksum(snapshot);
            return snapshot.checksum === expected;
        }

        async restore(snapshot) {
            if (!snapshot) throw new Error('No snapshot provided');

            const valid = await this.verify(snapshot);
            if (!valid) {
                Logger.warn('Snapshot', 'Checksum mismatch — snapshot may be corrupt');
                // Continue anyway but warn
            }

            // Version compatibility check
            if (snapshot.version && snapshot.version !== this.version) {
                Logger.warn('Snapshot', `Version mismatch: ${snapshot.version} vs ${this.version}`);
            }

            try {
                await Registry.restore(snapshot.registry);
                Logger.info('Snapshot', 'Snapshot restored');
            } catch (error) {
                Logger.error('Snapshot', 'Failed to restore snapshot', error);
                throw error;
            }
        }
    }

    window.Snapshot = new Snapshot();

})(window);
