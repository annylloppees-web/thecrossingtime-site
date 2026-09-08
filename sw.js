/* The Crossing Time — Service Worker de DESATIVAÇÃO (kill-switch)
   A app em cache antiga prendia o site numa versão velha. Este ficheiro
   substitui-a: não guarda nada em cache, apaga os caches existentes,
   desregista-se e recarrega as páginas abertas. Depois disto o site
   funciona como um site normal, carregando sempre a versão mais recente.
   Nada de novo passa a ser registado (ver index.html). */

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil((async function () {
    // 1) apagar todos os caches
    try {
      if (self.caches && caches.keys) {
        var keys = await caches.keys();
        await Promise.all(keys.map(function (k) { return caches.delete(k); }));
      }
    } catch (e) {}
    // 2) desregistar este Service Worker
    try { await self.registration.unregister(); } catch (e) {}
    // 3) recarregar as janelas abertas para saírem já da versão em cache
    try {
      var wins = await self.clients.matchAll({ type: 'window' });
      wins.forEach(function (c) { try { c.navigate(c.url); } catch (e) {} });
    } catch (e) {}
  })());
});

/* Sem handler de 'fetch' — todos os pedidos vão direto à rede. */
