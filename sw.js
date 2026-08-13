/*  The Crossing Time — service worker
 *  ESTRATEGIA: rede primeiro para paginas e materias. NUNCA servir
 *  jornalismo desactualizado a partir da cache. A cache existe apenas
 *  para o caso de o leitor ficar sem ligacao.
 */
var CACHE = 'tct-v1';
var ESSENCIAIS = [
  '/favicon.ico',
  '/favicon-32x32.png',
  '/apple-touch-icon.png',
  '/icon-192.png',
  '/icon-512.png',
  '/site.webmanifest'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(ESSENCIAIS).catch(function () { return null; });
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (ks) {
      return Promise.all(ks.map(function (k) {
        if (k !== CACHE) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

var OFFLINE = '<!DOCTYPE html><html lang="pt"><head><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width,initial-scale=1">' +
  '<title>Sem ligacao — The Crossing Time</title><style>' +
  'body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;' +
  'background:#0E1A2B;color:#F4F2ED;font-family:Georgia,serif;text-align:center;padding:2rem}' +
  'h1{font-size:1.6rem;font-weight:400;margin:0 0 .8rem;color:#C6A15B}' +
  'p{font-size:.95rem;line-height:1.7;opacity:.8;margin:0}' +
  '</style></head><body><div><h1>Sem ligacao a internet</h1>' +
  '<p>Nao foi possivel carregar esta pagina.<br>Verifique a ligacao e tente novamente.<br><br>' +
  'Pas de connexion — verifiez votre reseau.</p></div></body></html>';

self.addEventListener('fetch', function (e) {
  var r = e.request;
  if (r.method !== 'GET') return;

  var url;
  try { url = new URL(r.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;   // fontes, CDN: nao mexer

  // Paginas e materias: rede primeiro, sempre.
  if (r.mode === 'navigate' || (r.headers.get('accept') || '').indexOf('text/html') !== -1) {
    e.respondWith(
      fetch(r).then(function (resp) {
        var copia = resp.clone();
        caches.open(CACHE).then(function (c) { c.put(r, copia); });
        return resp;
      }).catch(function () {
        return caches.match(r).then(function (hit) {
          return hit || new Response(OFFLINE, {
            headers: { 'Content-Type': 'text/html; charset=utf-8' }
          });
        });
      })
    );
    return;
  }

  // Icones e manifesto: cache primeiro (nao mudam).
  e.respondWith(
    caches.match(r).then(function (hit) {
      return hit || fetch(r).then(function (resp) {
        if (resp && resp.status === 200) {
          var copia = resp.clone();
          caches.open(CACHE).then(function (c) { c.put(r, copia); });
        }
        return resp;
      });
    }).catch(function () { return fetch(r); })
  );
});
