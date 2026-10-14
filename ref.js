/* The Crossing Time: link rastreável e código de indicação das vendedoras.
   Qualquer página aberta com ?ref=CODIGO (ou ?codigo=CODIGO) guarda o código neste aparelho por 180 dias.
   A página /silvania grava o código da Silvania sozinha. O registro vai para o app da equipe (TCT Apps),
   que confere se o código existe: código desconhecido é apagado. */
(function () {
  var API = "https://tct-apps.netlify.app/api/indicacao";
  var KEY = "tct_ref", DIAS = 180;
  function ler() {
    try { var o = JSON.parse(localStorage.getItem(KEY) || "null"); if (o && o.c && Date.now() - (o.em || 0) < DIAS * 864e5) return o; } catch (e) {}
    return null;
  }
  function gravar(c) { try { localStorage.setItem(KEY, JSON.stringify({ c: c, em: Date.now() })); } catch (e) {} }
  function apagar() { try { localStorage.removeItem(KEY); } catch (e) {} }
  function limpo(c) { return String(c || "").trim().replace(/[^A-Za-z0-9]/g, "").slice(0, 40); }
  function enviar(dados) {
    dados = dados || {};
    if (!dados.codigo) { var r = ler(); if (!r) return Promise.resolve({ ok: false }); dados.codigo = r.c; }
    dados.pagina = dados.pagina || location.pathname;
    return fetch(API, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(dados), keepalive: true })
      .then(function (x) { return x.json().then(function (j) { j.status = x.status; return j; }); })
      .catch(function () { return { ok: false, rede: true }; });
  }
  /* Define o código (link, página da vendedora ou digitado pelo cliente). Devolve uma promessa com {ok}. */
  function definir(c, origem) {
    c = limpo(c); if (!c) return Promise.resolve({ ok: false });
    var antes = ler(), novo = !antes || antes.c.toUpperCase() !== c.toUpperCase();
    gravar(c);
    var chave = "tct_ref_vis_" + c.toUpperCase(), ja = false;
    try { ja = sessionStorage.getItem(chave) === "1"; } catch (e) {}
    if (!novo && ja) return Promise.resolve({ ok: true });
    try { sessionStorage.setItem(chave, "1"); } catch (e) {}
    return enviar({ codigo: c, tipo: "visita", origem: origem || "link" }).then(function (j) {
      if (j && j.status === 404) { apagar(); if (antes && novo) gravar(antes.c); return { ok: false }; }
      return { ok: true };
    });
  }
  window.tctRef = {
    codigo: function () { var r = ler(); return r ? r.c : ""; },
    definir: definir,
    enviar: enviar,
    validar: function (c) {
      c = limpo(c); if (!c) return Promise.resolve(false);
      return fetch(API + "?codigo=" + encodeURIComponent(c)).then(function (x) { return x.json(); }).then(function (j) { return !!(j && j.ok); }).catch(function () { return false; });
    }
  };
  try {
    var p = new URLSearchParams(location.search), c = p.get("ref") || p.get("codigo");
    var fixo = document.currentScript && document.currentScript.getAttribute("data-codigo");
    if (c) definir(c, "link"); else if (fixo) definir(fixo, "pagina");
  } catch (e) {}
})();
