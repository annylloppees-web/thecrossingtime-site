# -*- coding: utf-8 -*-
"""Gera a pagina "Todas as materias" (todas-as-materias.html) e injeta, no fim
de cada materia, um bloco de navegacao com links rastreaveis (anterior,
proxima, todas as materias, inicio).

Corre na raiz do repositorio: python3 scripts/gen_materias_index.py
Sem dependencias externas. Idempotente: o bloco de navegacao fica entre
<!-- tct-relnav --> e <!-- /tct-relnav --> e e substituido a cada execucao.
"""
import html
import json
import os
import re
import subprocess

DIR = 'materias'
OUT = 'todas-as-materias.html'
BASE = 'https://thecrossingtime.com'

MES_PT = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
          'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
MES_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
          'août', 'septembre', 'octobre', 'novembre', 'décembre']
MES_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
MES_IDX = {m: i + 1 for i, m in enumerate(MES_PT)}
MES_IDX['marco'] = 3

RELNAV_RE = re.compile(r'\n?<!-- tct-relnav -->.*?<!-- /tct-relnav -->\n?', re.S)


def strip_tags(t):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t))).strip()


def no_dash(t):
    """a revista nao usa travessao: troca por virgula"""
    t = re.sub(r'\s*[\u2014\u2013]\s*', ', ', t)
    return re.sub(r',\s*,', ',', t).strip(' ,')


def git_added_dates():
    """data do primeiro commit de cada arquivo em materias/ (AAAA-MM-DD)."""
    out = {}
    try:
        log = subprocess.run(['git', 'log', '--diff-filter=A', '--name-only',
                              '--format=@%cs', '--', DIR],
                             capture_output=True, text=True, check=True).stdout
    except Exception:
        return out
    cur = None
    for line in log.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('@'):
            cur = line[1:]
        elif cur:
            out[os.path.basename(line)] = cur  # o log vem do mais novo ao mais antigo: fica o mais antigo
    return out


def inner_date(s):
    m = re.search(r'(\d{1,2})\s+de\s+([A-Za-zçÇ]+)\s+de\s+(20\d{2})', s)
    if m and m.group(2).lower() in MES_IDX:
        return '%s-%02d-%02d' % (m.group(3), MES_IDX[m.group(2).lower()], int(m.group(1)))
    return None


def jsonld_date(s):
    m = re.search(r'"datePublished"\s*:\s*"(20\d{2}-\d{2}-\d{2})', s)
    return m.group(1) if m else None


def title_of(s, fname):
    m = re.search(r'<title[^>]*>(.*?)</title>', s, re.S | re.I)
    t = strip_tags(m.group(1)) if m else ''
    t = re.split(r'\s+[·|\-]\s+The Crossing Time.*$', t)[0].strip()
    if not t or t.lower() == 'the crossing time':
        m = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S | re.I)
        if m:
            pt = re.search(r'class="ng-pt"[^>]*>(.*?)</span>', m.group(1), re.S)
            t = strip_tags(pt.group(1) if pt else m.group(1))
    return t or fname


def desc_of(s):
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)', s, re.I)
    d = html.unescape(m.group(1)).strip() if m else ''
    if len(d) > 170:
        d = d[:167].rsplit(' ', 1)[0] + '…'
    return d


def langs_of(s):
    css = s[:60000]
    return {'fr': '.ng-fr' in css, 'en': '.ng-en' in css}


def collect():
    added = git_added_dates()
    items = []
    for name in sorted(os.listdir(DIR)):
        if not name.endswith('.html') or re.search(r' \(\d+\)\.html$', name):
            continue
        path = os.path.join(DIR, name)
        s = open(path, encoding='utf-8', errors='replace').read()
        if re.search(r'<meta[^>]+name=["\']robots["\'][^>]*noindex', s[:6000], re.I):
            continue
        body = RELNAV_RE.sub('', s)
        g = added.get(name)
        bstart = body.lower().find('<body')
        inner = inner_date(body[bstart:bstart + 20000] if bstart >= 0 else body[:20000])
        # a data escrita na materia so vale se for plausivel (a revista existe desde 2026
        # e a materia nao pode ser posterior ao seu primeiro commit)
        if inner and not ('2026-04-01' <= inner <= (g or '9999')):
            inner = None
        date = jsonld_date(body) or inner or g or '2026-01-01'
        items.append(dict(name=name, path=path, src=s, date=date,
                          title=no_dash(title_of(body, name)), desc=no_dash(desc_of(body)), langs=langs_of(body)))
    items.sort(key=lambda x: (x['date'], x['name']), reverse=True)
    return items


def lab(pt, fr, en, langs):
    out = '<span class="ng-pt">%s</span>' % pt
    if langs['fr']:
        out += '<span class="ng-fr">%s</span>' % fr
    if langs['en']:
        out += '<span class="ng-en">%s</span>' % en
    return out


def relnav(item, newer, older):
    L = item['langs']
    st = ('style="max-width:760px;margin:40px auto 24px;padding:18px 20px;border-top:1px solid rgba(0,0,0,.12);'
          'font:15px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;"')
    a = 'style="color:inherit;text-decoration:underline;text-underline-offset:3px;" target="_top"'
    parts = []
    if older:
        parts.append('<p style="margin:0 0 10px;">%s: <a href="%s" %s>%s</a></p>'
                     % (lab('Matéria anterior', 'Article précédent', 'Previous article', L), html.escape(older['name']), a,
                        html.escape(older['title'])))
    if newer:
        parts.append('<p style="margin:0 0 10px;">%s: <a href="%s" %s>%s</a></p>'
                     % (lab('Próxima matéria', 'Article suivant', 'Next article', L), html.escape(newer['name']), a,
                        html.escape(newer['title'])))
    parts.append('<p style="margin:14px 0 0;"><a href="../todas-as-materias.html" %s>%s</a> · '
                 '<a href="../" %s>%s</a> · <a href="../mentions-legales.html" %s>%s</a> · '
                 '<a href="../politique-confidentialite.html" %s>%s</a></p>'
                 % (a, lab('Todas as matérias', 'Tous les articles', 'All articles', L),
                    a, lab('Página inicial', 'Accueil', 'Home', L),
                    a, lab('Menções legais', 'Mentions légales', 'Legal notice', L),
                    a, lab('Privacidade', 'Confidentialité', 'Privacy', L)))
    return ('\n<!-- tct-relnav --><nav class="tct-relnav" aria-label="The Crossing Time" %s>%s</nav><!-- /tct-relnav -->\n'
            % (st, ''.join(parts)))


def inject(items):
    changed = 0
    for i, it in enumerate(items):
        newer = items[i - 1] if i > 0 else None
        older = items[i + 1] if i + 1 < len(items) else None
        s = it['src']
        base = RELNAV_RE.sub('\n', s) if '<!-- tct-relnav -->' in s else s
        k = base.lower().rfind('</body>')
        if k < 0:
            continue
        new = base[:k].rstrip('\n') + relnav(it, newer, older) + base[k:]
        if new != s:
            open(it['path'], 'w', encoding='utf-8').write(new)
            changed += 1
    return changed


PAGE_HEAD = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Todas as matérias · The Crossing Time</title>
<meta name="description" content="Arquivo completo das matérias da The Crossing Time: imigração, direitos, trabalho, moradia, saúde, economia e cultura para brasileiros e lusófonos na França e na Europa.">
<link rel="canonical" href="https://thecrossingtime.com/todas-as-materias.html">
<meta property="og:title" content="Todas as matérias · The Crossing Time">
<meta property="og:url" content="https://thecrossingtime.com/todas-as-materias.html">
<meta property="og:type" content="website">
<style>
  :root{--navy:#0E1A2B;--gold:#C6A15B;--paper:#FBFAF7;--ink:#2a2f38;--muted:#5b6470;--line:#e6e2d8;}
  *{box-sizing:border-box;}
  body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 -apple-system,Segoe UI,Roboto,Arial,sans-serif;}
  .wrap{max-width:820px;margin:0 auto;padding:40px 22px 90px;}
  .top{display:flex;align-items:center;justify-content:space-between;gap:16px;border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:8px;flex-wrap:wrap;}
  .brand{font-family:Georgia,'Times New Roman',serif;font-weight:700;color:var(--navy);font-size:19px;text-decoration:none;}
  .brand small{display:block;font:800 10px Arial,sans-serif;letter-spacing:.22em;color:var(--gold);text-transform:uppercase;margin-top:4px;}
  .langbar{display:flex;gap:4px;background:#eee9df;padding:4px;border-radius:8px;}
  .langbar button{border:0;background:none;padding:7px 13px;border-radius:6px;font:700 13px Arial,sans-serif;color:var(--muted);cursor:pointer;}
  .langbar button.on{background:#fff;color:var(--navy);box-shadow:0 1px 3px rgba(0,0,0,.12);}
  .eyebrow{font:800 12px Arial,sans-serif;letter-spacing:.18em;color:var(--gold);text-transform:uppercase;margin:26px 0 8px;}
  h1{font-family:Georgia,serif;font-size:32px;line-height:1.18;color:var(--navy);margin:0 0 6px;}
  h2{font-family:Georgia,serif;font-size:20px;color:var(--navy);margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line);}
  .count{font-size:14px;color:var(--muted);margin:0 0 8px;}
  ul.lst{list-style:none;margin:0;padding:0;}
  ul.lst li{padding:10px 0;border-bottom:1px solid #efece4;}
  ul.lst a{color:var(--navy);font-weight:600;text-decoration:none;}
  ul.lst a:hover{text-decoration:underline;}
  ul.lst .d{display:block;font-size:14px;color:var(--muted);margin-top:2px;}
  ul.lst time{font-size:12px;color:var(--gold);font-weight:700;letter-spacing:.06em;margin-right:8px;}
  .foot{margin-top:44px;padding-top:20px;border-top:1px solid var(--line);font-size:13px;color:var(--muted);}
  .foot a{color:var(--navy);}
  [data-lang="pt"] .fr,[data-lang="pt"] .en,[data-lang="fr"] .pt,[data-lang="fr"] .en,[data-lang="en"] .pt,[data-lang="en"] .fr{display:none;}
</style>
</head>
<body data-lang="pt">
<div class="wrap">
  <div class="top">
    <a class="brand" href="./">The Crossing Time<small>By Porta-Voz do Imigrante</small></a>
    <div class="langbar">
      <button type="button" id="l-pt" class="on" onclick="setL('pt')">PT</button>
      <button type="button" id="l-fr" onclick="setL('fr')">FR</button>
      <button type="button" id="l-en" onclick="setL('en')">EN</button>
    </div>
  </div>
  <p class="eyebrow"><span class="pt">Arquivo</span><span class="fr">Archives</span><span class="en">Archive</span></p>
  <h1><span class="pt">Todas as matérias</span><span class="fr">Tous les articles</span><span class="en">All articles</span></h1>
'''

PAGE_TAIL = '''
  <div class="foot">
    © The Crossing Time · <a href="./"><span class="pt">Página inicial</span><span class="fr">Accueil</span><span class="en">Home</span></a>
    · <a href="mentions-legales.html"><span class="pt">Menções legais</span><span class="fr">Mentions légales</span><span class="en">Legal notice</span></a>
    · <a href="politique-confidentialite.html"><span class="pt">Privacidade</span><span class="fr">Confidentialité</span><span class="en">Privacy</span></a>
    · <a href="conseil-juridique.html"><span class="pt">Assessoria jurídica</span><span class="fr">Conseil juridique</span><span class="en">Legal counsel</span></a>
  </div>
</div>
<script>
  function setL(l){
    document.body.setAttribute('data-lang',l);
    document.documentElement.lang=l;
    ['pt','fr','en'].forEach(function(x){var b=document.getElementById('l-'+x);if(b)b.className=(x===l)?'on':'';});
    try{localStorage.setItem('tct-lang',l);}catch(e){}
  }
  (function(){
    var q=(location.search.match(/[?&]lang=(pt|fr|en)/)||[])[1];
    if(q){ setL(q); return; }
    var s=null; try{s=localStorage.getItem('tct-lang');}catch(e){}
    if(s==='fr'||s==='en'){ setL(s); }
  })();
</script>
</body>
</html>
'''


def page(items):
    out = [PAGE_HEAD]
    n = len(items)
    out.append('  <p class="count"><span class="pt">%d matérias publicadas, da mais recente à mais antiga.</span>'
               '<span class="fr">%d articles publiés, du plus récent au plus ancien.</span>'
               '<span class="en">%d published articles, newest first.</span></p>\n' % (n, n, n))
    cur = None
    for it in items:
        y, m, d = it['date'].split('-')
        ym = (y, int(m))
        if ym != cur:
            if cur is not None:
                out.append('  </ul>\n')
            mi = int(m) - 1
            out.append('  <h2><span class="pt">%s de %s</span><span class="fr">%s %s</span><span class="en">%s %s</span></h2>\n'
                       '  <ul class="lst">\n' % (MES_PT[mi].capitalize(), y, MES_FR[mi].capitalize(), y, MES_EN[mi], y))
            cur = ym
        out.append('    <li><time datetime="%s">%s/%s</time><a href="materias/%s">%s</a>%s</li>\n'
                   % (it['date'], d, m, html.escape(it['name']), html.escape(it['title']),
                      ('<span class="d">%s</span>' % html.escape(it['desc'])) if it['desc'] else ''))
    if cur is not None:
        out.append('  </ul>\n')
    out.append(PAGE_TAIL)
    return ''.join(out)


def main():
    items = collect()
    changed = inject(items)
    open(OUT, 'w', encoding='utf-8').write(page(items))
    print('todas-as-materias.html: %d materias | navegacao atualizada em %d arquivos' % (len(items), changed))


if __name__ == '__main__':
    main()
