// One2lvOS Service Worker

const CACHE_NAME = 'one2lvos-v1.0.0';
const RUNTIME_CACHE = 'one2lvos-runtime';

const PRECACHE_URLS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/css/boot.css',
    '/css/desktop.css',
    '/css/glass.css',
    '/css/widgets.css',
    '/js/boot.js',
    '/js/config.js',
    '/js/eventbus.js',
    '/js/logger.js',
    '/js/storage.js',
    '/js/module-loader.js',
    '/reactor/lumenis.js',
    '/reactor/scheduler.js',
    '/reactor/registry.js',
    '/reactor/council.js',
    '/reactor/itt.js',
    '/reactor/memory.js',
    '/reactor/heartbeat.js',
    '/infinity-glass/desktop.js',
    '/infinity-glass/windows.js',
    '/infinity-glass/dock.js',
    '/infinity-glass/shader.js',
    '/infinity-glass/hud.js',
    '/infinity-glass/gestures.js',
    '/infinity-glass/renderer.js',
    '/interplanetary-disk/filesystem.js',
    '/interplanetary-disk/checkpoint.js',
    '/interplanetary-disk/snapshot.js',
    '/interplanetary-disk/pngboot.js',
    '/interplanetary-disk/recovery.js',
    '/interplanetary-disk/vectorfs.js',
    '/interplanetary-disk/main.js',
    '/assets/boot.png'
];

// Install event
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// Activate event
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME && name !== RUNTIME_CACHE)
                    .map((name) => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event
self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }

            return caches.open(RUNTIME_CACHE).then((cache) => {
                return fetch(event.request).then((response) => {
                    if (!response || response.status !== 200 || response.type === 'error') {
                        return response;
                    }

                    const responseToCache = response.clone();
                    cache.put(event.request, responseToCache);
                    return response;
                });
            });
        })
    );
});

// Message handling
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then((names) => {
                return Promise.all(names.map((name) => caches.delete(name)));
            })
        );
    }
});
