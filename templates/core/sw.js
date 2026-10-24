// SPDX-License-Identifier: EUPL-1.2
// Service worker de Eira: caché de lectura para as vistas clave e páxina sen conexión.
// v4.1: a versión depende do hash dos estáticos. Cada cambio de CSS/JS crea cachés novas, e no
// «activate» bórranse todas as demais (tamén as de versións anteriores). Só se busca nas cachés
// propias desta versión: nunca se serve un CSS vello doutra caché.
const VERSION = "{{ version }}";
const DEV = {{ dev|yesno:"true,false" }};
const STATIC = "eira-static-" + VERSION;
const PAGES = "eira-pages-" + VERSION;
const PRECACHE = {{ precache|safe }};
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

function fromCache(name, req) {
  return caches.open(name).then((c) => c.match(req));
}

function networkFirst(name, req, store) {
  return fetch(req).then((resp) => {
    if (store && resp.ok) {
      const copy = resp.clone();
      caches.open(name).then((c) => c.put(req, copy));
    }
    return resp;
  }).catch(() => fromCache(name, req).then((hit) => hit || (req.mode === "navigate" ? fromCache(STATIC, "/offline/") : Response.error())));
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/static/")) {
    // Desenvolvemento: rede primeiro (o CSS que se está a editar vese ao momento).
    // Produción: os nomes levan hash, así que a caché nunca queda vella.
    if (DEV || url.pathname.endsWith(".css")) {
      event.respondWith(networkFirst(STATIC, req, true));
    } else {
      event.respondWith(fromCache(STATIC, req).then((hit) => hit || networkFirst(STATIC, req, true)));
    }
    return;
  }
  if (req.mode === "navigate" || (req.headers.get("accept") || "").includes("text/html")) {
    const cacheable = READ_CACHE.some((re) => re.test(url.pathname));
    event.respondWith(networkFirst(PAGES, req, cacheable));
  }
});

self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = { title: "Eira", body: event.data && event.data.text() }; }
  event.waitUntil(self.registration.showNotification(data.title || "Eira", {
    body: data.body || "", icon: "{{ icon }}", data: { url: data.url || "/" },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow(event.notification.data.url));
});
