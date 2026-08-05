const CACHE_NAME = 'nearme-v11';
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/icon.svg',
    '/icon-256.png',
    '/favicon.png',
];

const API_CACHE = 'nearme-api-v1';
const API_URLS = [
    '/api/types',
    '/api/ratings',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((names) => {
            return Promise.all(
                names.filter((n) => n !== CACHE_NAME && n !== API_CACHE).map((n) => caches.delete(n))
            );
        })
    );
    self.clients.claim();
});

const NO_CACHE_PREFIXES = ['/api/nearby', '/api/status', '/admin'];

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    const path = url.pathname;

    if (NO_CACHE_PREFIXES.some(p => path.startsWith(p))) {
        event.respondWith(fetch(event.request).catch(function() {
            return new Response(JSON.stringify({ error: 'Offline' }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' },
            });
        }));
        return;
    }

    if (path.startsWith('/api/')) {
        event.respondWith(networkFirst(event.request));
        return;
    }

    event.respondWith(cacheFirst(event.request));
});

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        if (response && response.status === 200) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return new Response('Offline', { status: 503 });
    }
}

async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response && response.status === 200) {
            const cache = await caches.open(API_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response(JSON.stringify({ error: 'Offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
        });
    }
}


// ---------- Web Push ----------
self.addEventListener('push', (event) => {
    let data = { title: 'NearMe OSINT', body: '', url: '/' };
    try {
        const d = event.data ? event.data.json() : {};
        if (d.title) data.title = d.title;
        if (d.body) data.body = d.body;
        if (d.url) data.url = d.url;
    } catch (e) {}
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/icon-256.png',
            badge: '/icon-256.png',
            data: { url: data.url },
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = (event.notification.data && event.notification.data.url) || '/';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if ('focus' in client) {
                    client.navigate(url).catch(() => {});
                    return client.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});

