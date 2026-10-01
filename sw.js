const CORE = 'yok-atlas-core-v3';
const datasetOf = url => new URL(url).pathname.includes('/data/dgs/') ? 'dgs' : 'yks';
const dataCache = request => `yok-atlas-data-${datasetOf(request.url)}-${new URL(request.url).searchParams.get('v') || 'pending'}`;
self.addEventListener('message', event => {
  const d = event.data || {};
  if (d.type === 'YOK_ATLAS_DATA_VERSION' || d.type === 'DGS_DATA_VERSION') pruneDataCaches(d.version, d.dataset);
});
async function pruneDataCaches(version, dataset) {
  const names = await caches.keys();
  // ayni veri setinin eski surumleri + surumsuz legacy cache'ler silinir;
  // diger veri setine dokunulmaz
  const stale = names.filter(name => {
    if (!name.startsWith('yok-atlas-data-')) return false;
    if (dataset) {
      if (name === `yok-atlas-data-${dataset}-${version}`) return false;
      if (name.startsWith(`yok-atlas-data-${dataset}-`)) return true;
      if (!/^yok-atlas-data-(yks|dgs)-/.test(name)) return true; // legacy
      return false;
    }
    return name !== `yok-atlas-data-${version}`;
  });
  await Promise.all(stale.map(name => caches.delete(name)));
}
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== location.origin) return;
  const path = new URL(request.url).pathname;
  if (path.includes('/data/static/') || path.includes('/data/dgs/')) {
    if (path.endsWith('/config.js')) {
      event.respondWith(fetch(request).then(async response => {
        const match = (await response.clone().text()).match(/"version":"([^"]+)"/);
        if (match) await pruneDataCaches(match[1], datasetOf(request.url));
        const cache = await caches.open(CORE); await cache.put(request, response.clone());
        return response;
      }).catch(() => caches.match(request)));
    } else event.respondWith(caches.match(request).then(hit => hit || fetch(request).then(async response => {
      const cache = await caches.open(dataCache(request)); await cache.put(request, response.clone()); return response;
    })));
  }
});
