/* Dix Mille Escales – carnet hors connexion.
   Les fiches mises dans le carnet (page, données, lieux) sont gardées dans le navigateur ; sans réseau, on les relit depuis ce cache.
   Tout le reste passe par le réseau, comme d'habitude (aucune autre page n'est gardée : quelques Mo au plus). */
var CARNET = 'dme-carnet-v1', STATIQUE = 'dme-statique-v1';
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('message', function (e) {
  var m = e.data || {};
  if (m.garder) e.waitUntil(caches.open(CARNET).then(function (c) {
    return Promise.all(m.garder.map(function (u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (r.ok) return c.put(u, r); }).catch(function () {}); }));
  }));
  if (m.oublier) e.waitUntil(caches.open(CARNET).then(function (c) {
    return c.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k.url.indexOf('/villes/' + m.oublier + '/') > -1; }).map(function (k) { return c.delete(k); })); });
  }));
});
self.addEventListener('fetch', function (e) {
  var r = e.request;
  if (r.method !== 'GET' || new URL(r.url).origin !== location.origin) return;
  var statique = /\/static\/[^?]+\.(js|css|svg|png|webmanifest)$/.test(r.url);
  e.respondWith(fetch(r).then(function (rep) {
    if (statique && rep.ok) { var copie = rep.clone(); caches.open(STATIQUE).then(function (c) { c.put(r, copie); }); }
    return rep;
  }).catch(function () {
    return caches.match(r, { ignoreSearch: true }).then(function (x) {
      if (x) return x;
      if (r.mode === 'navigate') return caches.match(r.url.replace(/index\.html$/, '').replace(/\/?$/, '/'), { ignoreSearch: true }).then(function (y) {
        return y || new Response('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Hors connexion</title><body style="font-family:system-ui;padding:2em;max-width:34em"><h1>Pas de connexion</h1><p>Cette page n’est pas dans votre carnet. Les villes que vous avez gardées dans « Mon carnet » restent lisibles sans réseau.</p>', { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      });
      return Response.error();
    });
  }));
});
