// Interplanetary Disk Filesystem

(function(window) {
    'use strict';

    class FileSystem {
        constructor() {
            this.files = new Map();
            this.currentPath = '/';
        }

        async read(path) {
            if (this.files.has(path)) {
                return this.files.get(path);
            }

            // Try to load from storage
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

        async write(path, content) {
            const file = {
                path,
                content,
                modified: Date.now(),
                size: content.length
            };

            this.files.set(path, file);

            try {
                await Storage.set('files', file);
            } catch (error) {
                Logger.error('FileSystem', `Failed to write file: ${path}`, error);
            }

            EventBus.emit('fs:write', { path });
        }

        async delete(path) {
            this.files.delete(path);

            try {
                await Storage.delete('files', path);
            } catch (error) {
                Logger.error('FileSystem', `Failed to delete file: ${path}`, error);
            }

            EventBus.emit('fs:delete', { path });
        }

        list(path = '/') {
            const files = [];
            for (const [filePath, file] of this.files) {
                if (filePath.startsWith(path)) {
                    files.push(file);
                }
            }
            return files;
        }
    }

    window.FileSystem = new FileSystem();

})(window);
