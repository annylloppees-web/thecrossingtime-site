# -*- coding: utf-8 -*-
"""Injeta Open Graph, Twitter Card, canonical e meta description em todas as
materias e colunas do The Crossing Time. Extrai a primeira foto (base64) de
cada pagina para og/<nome>.jpg e a usa como og:image. Idempotente: pula
paginas que ja tem og:title. Corre na raiz do repositorio."""
import re, os, io, sys, json, base64, html

BASE = 'https://thecrossingtime.com'

try:
    from PIL import Image
except ImportError:
    print('ERRO: pillow nao instalado'); sys.exit(1)

os.makedirs('og', exist_ok=True)

def text_of(h):
    h = re.sub(r'<span class="ng-fr"[^>]*>.*?</span>', '', h, flags=re.S)
    h = re.sub(r'<span class="ng-en"[^>]*>.*?</span>', '', h, flags=re.S)
    h = re.sub(r'<[^>]+>', ' ', h)
    h = html.unescape(h)
    return re.sub(r'\s+', ' ', h).strip()

def get_desc(s):
    m = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', s)
    if m:
        try:
            return json.loads('"' + m.group(1) + '"').strip()
        except Exception:
            pass
    m = re.search(r'<meta name="description" content="([^"]{20,})"', s)
    if m:
        return html.unescape(m.group(1)).strip()
    for m in re.finditer(r'<p[^>]*class="[^"]*lead[^"]*"[^>]*>(.*?)</p>', s, re.S):
        t = text_of(m.group(1))
        if len(t) > 40:
            return t
    for m in re.finditer(r'<p[^>]*>(.*?)</p>', s, re.S):
        t = text_of(m.group(1))
        if len(t) > 60:
            return t
    return ''

def clip(t, n=200):
    t = t.strip()
    if len(t) <= n:
        return t
    t = t[:n]
    return t[:t.rfind(' ')].rstrip(' ,;:') + '…'

def get_image(s, stem):
    best = None
    for m in re.finditer(r'data:image/jpeg;base64,([A-Za-z0-9+/=]{5000,})', s):
        b = m.group(1)
        if best is None or len(b) > len(best):
            best = b
        if len(m.group(1)) > 60000:
            best = m.group(1); break
    if not best:
        return None, None, None
    try:
        raw = base64.b64decode(best)
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        if im.width > 1200:
            im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        path = 'og/%s.jpg' % stem
        im.save(path, 'JPEG', quality=80, optimize=True)
        return path, im.width, im.height
    except Exception as e:
        print('  aviso: imagem invalida em', stem, e)
        return None, None, None

def esc(t):
    return html.escape(t, quote=True)

changed = skipped = noimg = 0
for folder in ['materias', 'colunas']:
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith('.html'):
            continue
        p = os.path.join(folder, fn)
        s = open(p, encoding='utf-8').read()
        if '</head>' not in s:
            skipped += 1
            continue
        dirty = False
        FOCUS = ('<style id="tct-a11y-focus">a:focus-visible,button:focus-visible,'
                 'input:focus-visible,textarea:focus-visible,select:focus-visible,'
                 '[tabindex]:focus-visible{outline:2px solid #C6A15B!important;'
                 'outline-offset:3px!important;border-radius:2px}</style>')
        if 'tct-a11y-focus' not in s:
            s = s.replace('</head>', FOCUS + '\n</head>', 1)
            dirty = True
        if 'og:title' in s:
            if dirty:
                open(p, 'w', encoding='utf-8').write(s)
                changed += 1
            else:
                skipped += 1
            continue
        stem = fn[:-5]
        url = '%s/%s/%s' % (BASE, folder, fn.replace(' ', '%20'))
        mt = re.search(r'<title>(.*?)</title>', s, re.S)
        title = text_of(mt.group(1)) if mt else stem
        title = re.sub(r'\s*[—–-]\s*The Crossing Time\s*$', '', title).strip() or stem
        desc = clip(get_desc(s)) or title
        img, w, h = get_image(s, stem)
        if img:
            imgurl = '%s/%s' % (BASE, img.replace(' ', '%20'))
            card = 'summary_large_image'
        else:
            imgurl = BASE + '/logo.png'; w = h = 1024
            card = 'summary'; noimg += 1
        tags = []
        if 'rel="canonical"' not in s:
            tags.append('<link rel="canonical" href="%s">' % url)
        if '<meta name="description"' not in s:
            tags.append('<meta name="description" content="%s">' % esc(desc))
        tags += [
            '<meta property="og:type" content="article">',
            '<meta property="og:site_name" content="The Crossing Time">',
            '<meta property="og:title" content="%s">' % esc(title),
            '<meta property="og:description" content="%s">' % esc(desc),
            '<meta property="og:url" content="%s">' % url,
            '<meta property="og:image" content="%s">' % imgurl,
            '<meta property="og:image:width" content="%d">' % w,
            '<meta property="og:image:height" content="%d">' % h,
            '<meta property="og:locale" content="pt_BR">',
            '<meta name="twitter:card" content="%s">' % card,
            '<meta name="twitter:title" content="%s">' % esc(title),
            '<meta name="twitter:description" content="%s">' % esc(desc),
            '<meta name="twitter:image" content="%s">' % imgurl,
        ]
        block = '\n' + '\n'.join(tags) + '\n'
        s = s.replace('</head>', block + '</head>', 1)
        open(p, 'w', encoding='utf-8').write(s)
        changed += 1

print('alteradas: %d | puladas (ja tinham og): %d | sem imagem propria: %d' % (changed, skipped, noimg))
