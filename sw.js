/* The Crossing Time — Service Worker
   Estratégia: "network-first" para páginas (HTML) → carrega SEMPRE a versão
   mais recente quando há ligação; usa o cache só como reserva offline.
   Ativa-se de imediato (skipWaiting + clients.claim) e apaga caches antigos,
   corrigindo o problema de "fica na versão antiga" após publicar.
*/
var VERSION = 'tct-2026-09-08-v71';
var CACHE = 'tct-cache-' + VERSION;

self.addEventListener('install', function (e) {
  // novo SW assume o controlo sem esperar
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== CACHE) { return caches.delete(k); } // limpa caches antigos
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

// permite forçar atualização a partir da página, se preciso
self.addEventListener('message', function (e) {
  if (e.data === 'skipWaiting') { self.skipWaiting(); }
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') { return; }            // POST/etc: deixa passar
  var url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) { return; }        // externo: não mexe
  if (url.pathname.indexOf('/.netlify/') === 0) { return; }   // funções: não mexe

  var isDoc = req.mode === 'navigate'
           || req.destination === 'document'
           || url.pathname === '/'
           || url.pathname.slice(-5) === '.html';

  if (isDoc) {
    // PÁGINAS: rede primeiro (sempre o mais novo), cache como reserva offline
    e.respondWith(
      fetch(req).then(function (res) {
        if (res && res.status === 200) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        return caches.match(req).then(function (m) {
          return m || caches.match('/index.html') || caches.match('index.html');
        });
      })
    );
    return;
  }

  // OUTROS ficheiros (ícones, media): usa cache e atualiza em segundo plano
  e.respondWith(
    caches.match(req).then(function (cached) {
      var net = fetch(req).then(function (res) {
        if (res && res.status === 200) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () { return cached; });
      return cached || net;
    })
  );
});
