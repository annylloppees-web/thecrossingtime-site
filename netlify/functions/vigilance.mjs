// The Crossing Time — proxy Vigilance Météo-France (nível nacional)
// Lê a API Key da variável de ambiente do Netlify: METEOFRANCE_APIKEY
// Endpoint público em: /.netlify/functions/vigilance
const API = "https://public-api.meteofrance.fr/public/DPVigilance/v1/cartevigilance/encours";
const COLORS = { 1: "vert", 2: "jaune", 3: "orange", 4: "rouge" };

export default async (req) => {
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "*",
    "cache-control": "public, max-age=1800", // 30 min
  };
  const key = process.env.METEOFRANCE_APIKEY;
  if (!key) return new Response(JSON.stringify({ error: "missing_key" }), { status: 500, headers });

  try {
    const r = await fetch(API, { headers: { apikey: key, accept: "application/json" } });
    if (!r.ok) return new Response(JSON.stringify({ error: "api_error", status: r.status }), { status: 502, headers });
    const j = await r.json();

    // modo debug: /.netlify/functions/vigilance?debug=1  -> devolve o JSON cru
    try { if (new URL(req.url).searchParams.get("debug")) return new Response(JSON.stringify(j), { headers }); } catch (_) {}

    const periods = (j && j.product && j.product.periods) || [];
    const period = periods.find(p => String(p.echeance).toUpperCase() === "J") || periods[0] || {};
    const domains = (period.timelaps && period.timelaps.domain_ids) || [];
    let level = 1;
    for (const d of domains) {
      const c = Number(d && d.max_color_id);
      if (Number.isFinite(c) && c > level) level = c;
    }
    return new Response(JSON.stringify({
      level,
      color: COLORS[level] || "vert",
      updated: (j && j.product && j.product.update_time) || null,
      echeance: period.echeance || null,
    }), { headers });
  } catch (e) {
    return new Response(JSON.stringify({ error: "exception", message: String(e) }), { status: 500, headers });
  }
};
