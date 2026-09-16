// The Crossing Time — lista de vídeos (Entrevistas) a partir do YouTube (RSS, sem chave)
// Por defeito lê os últimos vídeos do CANAL. Para filtrar só a playlist "Entrevistas",
// preenche PLAYLIST_ID com o id da playlist (começa por "PL...") e ela passa a mandar.
const CHANNEL_ID  = "UCDn72xKhv4mRJTAmJDEv_BQ";
const PLAYLIST_ID = ""; // ex.: "PLxxxxxxxx"  (deixa vazio para usar o canal)

const FEED = PLAYLIST_ID
  ? "https://www.youtube.com/feeds/videos.xml?playlist_id=" + PLAYLIST_ID
  : "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL_ID;

function decode(s){
  return (s||"")
    .replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">")
    .replace(/&quot;/g,'"').replace(/&#39;/g,"'")
    .replace(/&#(\d+);/g,function(_,n){return String.fromCharCode(+n);});
}

export default async () => {
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "*",
    "cache-control": "public, max-age=900", // 15 min
  };
  try {
    const r = await fetch(FEED, { headers: { accept: "application/atom+xml" } });
    if (!r.ok) return new Response(JSON.stringify({ error: "feed_error", status: r.status }), { status: 502, headers });
    const xml = await r.text();
    const parts = xml.split("<entry>").slice(1);
    const items = parts.map(function(e){
      const g = function(re){ const m = e.match(re); return m ? m[1] : ""; };
      const id = g(/<yt:videoId>([^<]+)<\/yt:videoId>/);
      const title = decode(g(/<title>([^<]*)<\/title>/));
      const published = g(/<published>([^<]+)<\/published>/);
      let desc = decode(g(/<media:description>([\s\S]*?)<\/media:description>/)).replace(/\s+/g," ").trim();
      if (desc.length > 170) desc = desc.slice(0,170).trim() + "…";
      return {
        id: id,
        title: title,
        published: published,
        thumb: id ? ("https://i.ytimg.com/vi/" + id + "/hqdefault.jpg") : "",
        desc: desc
      };
    }).filter(function(x){ return x.id; });
    return new Response(JSON.stringify({ items: items, source: PLAYLIST_ID ? "playlist" : "channel" }), { headers });
  } catch (err) {
    return new Response(JSON.stringify({ error: "exception", message: String(err) }), { status: 500, headers });
  }
};
