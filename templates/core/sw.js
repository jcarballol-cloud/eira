// SPDX-License-Identifier: EUPL-1.2
// Service worker de Eira: caché de lectura para as vistas clave e páxina sen conexión.
const VERSION = "{{ version }}";
const STATIC = "eira-static-" + VERSION;
const PAGES = "eira-pages-" + VERSION;
const PRECACHE = ["/offline/", "/static/css/eira.css", "/static/js/eira.js", "/static/vendor/htmx/htmx.min.js",
  "/static/img/eira.svg", "/static/img/icons.svg", "/static/js/health.js", "/saude/"];
// Vistas que se gardan ao visitalas para consultalas sen rede
const READ_CACHE = [/^\/c\/[^/]+\/reservas\//, /^\/c\/[^/]+\/operario\//, /^\/c\/[^/]+\/instalacions\/\d+\/$/,
  /^\/c\/[^/]+\/$/, /^\/saude\/$/, /^\/c\/[^/]+\/monitor\//];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(STATIC).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((k) => ![STATIC, PAGES].includes(k)).map((k) => caches.delete(k))
  )).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((resp) => {
      const copy = resp.clone();
      caches.open(STATIC).then((c) => c.put(req, copy));
      return resp;
    })));
    return;
  }
  if (req.mode === "navigate" || (req.headers.get("accept") || "").includes("text/html")) {
    const cacheable = READ_CACHE.some((re) => re.test(url.pathname));
    event.respondWith(fetch(req).then((resp) => {
      if (cacheable && resp.ok) {
        const copy = resp.clone();
        caches.open(PAGES).then((c) => c.put(req, copy));
      }
      return resp;
    }).catch(() => caches.match(req).then((hit) => hit || caches.match("/offline/"))));
  }
});

self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = { title: "Eira", body: event.data && event.data.text() }; }
  event.waitUntil(self.registration.showNotification(data.title || "Eira", {
    body: data.body || "", icon: "/static/img/eira-192.png", data: { url: data.url || "/" },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow(event.notification.data.url));
});
