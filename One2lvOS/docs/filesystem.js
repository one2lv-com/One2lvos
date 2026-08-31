// Interplanetary Disk Filesystem

(function(window) {
    'use strict';

    class FileSystem {
        constructor() {
            this.files = new Map();
            this.dirs = new Set(['/']);
            this.currentPath = '/';
        }

        _ensureDir(path) {
            const parts = path.split('/').filter(Boolean);
            let acc = '';
            for (const p of parts) {
                acc += '/' + p;
                this.dirs.add(acc);
            }
        }

        _getSize(content) {
            if (typeof content === 'string') return new Blob([content]).size;
            if (content instanceof Blob) return content.size;
            if (content instanceof ArrayBuffer) return content.byteLength;
            if (content instanceof Uint8Array) return content.byteLength;
            return new Blob([JSON.stringify(content)]).size;
        }

        async read(path) {
            if (this.files.has(path)) return this.files.get(path);
            try {
                const file = await Storage.get('files', path);
                if (file) {
                    this.files.set(path, file);
                    return file;
                }
            } catch (error) {
                Logger.error('FileSystem', `Failed to read file: ${path}`, error);
            }
            return null;
        }

        async write(path, content, meta = {}) {
            const parent = path.substring(0, path.lastIndexOf('/')) || '/';
            this._ensureDir(parent);

            const file = {
                path,
                content,
                modified: Date.now(),
                created: meta.created || Date.now(),
                size: this._getSize(content),
                type: meta.type || 'text/plain',
                owner: meta.owner || 'system',
                permissions: meta.permissions || 0o644,
                ...meta
            };

            this.files.set(path, file);
            try { await Storage.set('files', file); } catch (e) {
                Logger.error('FileSystem', `Failed to write file: ${path}`, e);
            }
            EventBus.emit('fs:write', { path });
        }

        async delete(path) {
            this.files.delete(path);
            try { await Storage.delete('files', path); } catch (e) {
                Logger.error('FileSystem', `Failed to delete file: ${path}`, e);
            }
            EventBus.emit('fs:delete', { path });
        }

        async move(oldPath, newPath) {
            const file = await this.read(oldPath);
            if (!file) throw new Error(`File not found: ${oldPath}`);
            const parent = newPath.substring(0, newPath.lastIndexOf('/')) || '/';
            this._ensureDir(parent);
            file.path = newPath;
            file.modified = Date.now();
            await this.write(newPath, file.content, file);
            await this.delete(oldPath);
            EventBus.emit('fs:move', { oldPath, newPath });
        }

        async copy(src, dest) {
            const file = await this.read(src);
            if (!file) throw new Error(`File not found: ${src}`);
            const parent = dest.substring(0, dest.lastIndexOf('/')) || '/';
            this._ensureDir(parent);
            await this.write(dest, file.content, file);
            EventBus.emit('fs:copy', { src, dest });
        }

        list(path = '/', { recursive = false, pattern = null } = {}) {
            const results = [];
            const prefix = path.endsWith('/') ? path : path + '/';

            for (const [filePath, file] of this.files) {
                if (recursive) {
                    if (!filePath.startsWith(prefix) && filePath !== path) continue;
                } else {
                    const relative = filePath.slice(prefix.length);
                    if (filePath.startsWith(prefix) && relative && !relative.includes('/')) {
                        results.push(file);
                    }
                    continue;
                }
                if (!pattern || new RegExp(pattern.replace(/\*/g, '.*')).test(filePath)) {
                    results.push(file);
                }
            }
            return results;
        }

        mkdir(path) {
            const normalized = path.endsWith('/') ? path : path + '/';
            this._ensureDir(normalized.slice(0, -1));
            this.dirs.add(normalized.slice(0, -1));
            EventBus.emit('fs:mkdir', { path });
        }

        rmdir(path) {
            const normalized = path.endsWith('/') ? path : path + '/';
            this.dirs.delete(normalized.slice(0, -1));
            EventBus.emit('fs:rmdir', { path });
        }

        exists(path) {
            return this.files.has(path) || this.dirs.has(path);
        }
    }

    window.FileSystem = new FileSystem();

})(window);
