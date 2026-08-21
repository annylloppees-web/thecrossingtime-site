// Gera sitemap.xml com a data REAL de cada página (data do último commit no git).
// Sem dependências. Corre na raiz do repositório: `node scripts/gen-sitemap.mjs`
import { execSync } from 'node:child_process';
import { readdirSync, writeFileSync, statSync, readFileSync, existsSync } from 'node:fs';

const BASE = 'https://thecrossingtime.com';
const TODAY = new Date().toISOString().slice(0, 10);

// Secções do site a incluir. Cada pasta é varrida automaticamente,
// por isso matérias NOVAS entram sozinhas no sitemap.
const SECTIONS = [
  { file: 'index.html', loc: '/',            priority: '1.0', changefreq: 'daily'  },
  { dir:  'materias',   base: '/materias/',  priority: '0.8', changefreq: 'weekly' },
  { dir:  'colunas',    base: '/colunas/',   priority: '0.6', changefreq: 'monthly'},
];

const MESES = { janeiro:'01', fevereiro:'02', 'março':'03', marco:'03', abril:'04',
  maio:'05', junho:'06', julho:'07', agosto:'08', setembro:'09',
  outubro:'10', novembro:'11', dezembro:'12' };

function gitDate(file){
  try{ const d = execSync(`git log -1 --format=%cs -- "${file}"`, {encoding:'utf8'}).trim();
       if(/^\d{4}-\d{2}-\d{2}$/.test(d)) return d; }catch(e){}
  return null;
}
function innerDate(file){ // fallback: data escrita dentro da matéria ("21 de agosto de 2026")
  try{ const h = readFileSync(file,'utf8');
       const m = h.match(/(\d{1,2})\s+de\s+([A-Za-zçÇ]+)\s+de\s+(20\d{2})/);
       if(m){ const mm = MESES[m[2].toLowerCase()]; if(mm)
         return `${m[3]}-${mm}-${String(m[1]).padStart(2,'0')}`; } }catch(e){}
  return null;
}
function mtime(file){ try{ return statSync(file).mtime.toISOString().slice(0,10); }catch(e){ return TODAY; } }
function lastmod(file){ return gitDate(file) || innerDate(file) || mtime(file); }
function xmlEscape(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function listHtml(dir){ try{ return readdirSync(dir).filter(f=>f.endsWith('.html')).sort(); }catch(e){ return []; } }

const urls = [];
for(const s of SECTIONS){
  if(s.file){
    if(existsSync(s.file)) urls.push({ loc: BASE + s.loc, file: s.file, priority: s.priority, changefreq: s.changefreq });
  } else {
    for(const name of listHtml(s.dir)){
      const file = `${s.dir}/${name}`;
      urls.push({ loc: BASE + s.base + name, file, priority: s.priority, changefreq: s.changefreq });
    }
  }
}

const body = urls.map(u =>
`  <url>
    <loc>${xmlEscape(u.loc)}</loc>
    <lastmod>${lastmod(u.file)}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`).join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${body}
</urlset>
`;
writeFileSync('sitemap.xml', xml);
console.log(`sitemap.xml gerado com ${urls.length} URLs.`);
