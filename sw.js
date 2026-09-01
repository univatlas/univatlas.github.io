const CORE = 'yok-atlas-core-v2';
const dataCache = request => `yok-atlas-data-${new URL(request.url).searchParams.get('v') || 'pending'}`;
self.addEventListener('message', event => { if (event.data?.type === 'YOK_ATLAS_DATA_VERSION') pruneDataCaches(event.data.version); });
async function pruneDataCaches(version) {
  const keep = `yok-atlas-data-${version}`;
  const names = await caches.keys();
  await Promise.all(names.filter(name => name.startsWith('yok-atlas-data-') && name !== keep).map(name => caches.delete(name)));
}
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== location.origin) return;
  const path = new URL(request.url).pathname;
  if (path.includes('/data/static/')) {
    if (path.endsWith('/config.js')) {
      event.respondWith(fetch(request).then(async response => {
        const match = (await response.clone().text()).match(/"version":"([^"]+)"/);
        if (match) await pruneDataCaches(match[1]);
        const cache = await caches.open(CORE); await cache.put(request, response.clone());
        return response;
      }).catch(() => caches.match(request)));
    } else event.respondWith(caches.match(request).then(hit => hit || fetch(request).then(async response => {
      const cache = await caches.open(dataCache(request)); await cache.put(request, response.clone()); return response;
    })));
  }
});
