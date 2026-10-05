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
        path = 'og/%s.jpg' % stem.lower()
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
        # --- normalizacao (roda em TODAS as paginas, inclusive as que ja tem og) ---
        # O Netlify serve tudo em minusculas e redireciona (301) enderecos com
        # maiusculas. Canonical, og:url, og:image e JSON-LD tem de apontar para a
        # URL final em minusculas, senao o Google ve "canonical para redirect".
        good = '%s/%s/%s' % (BASE, folder, fn.lower())
        def _fix(m):
            return m.group(1) + good + m.group(2)
        s2 = re.sub(r'(<link rel="canonical" href=")[^"]*(")', _fix, s)
        s2 = re.sub(r'(<meta property="og:url" content=")[^"]*(")', _fix, s2)
        s2 = re.sub(r'("mainEntityOfPage"\s*:\s*")https://thecrossingtime\.com/%s/[^"]*(")' % folder, _fix, s2)
        s2 = re.sub(r'((?:og:image|twitter:image)" content="https://thecrossingtime\.com/og/)([^"]+)(")',
                    lambda m: m.group(1) + m.group(2).lower().replace('%20(1)', '').replace('%20(2)', '') + m.group(3), s2)
        # og:image relativo ("../og/x.jpg", em qualquer ordem de atributos) nao e
        # lido por Facebook/WhatsApp: vira endereco absoluto em minusculas
        def _abs(m):
            return m.group(0).replace(m.group(1), BASE + '/og/' + m.group(2).lower())
        s2 = re.sub(r'<meta[^>]*(?:og:image|twitter:image)[^>]*>',
                    lambda t: re.sub(r'(\.\./og/([^"]+))', lambda m: _abs(m), t.group(0)), s2)
        # og:image apontando para og/<nome>.jpg que nao existe: gerar a imagem
        mi = re.search(r'og:image" content="https://thecrossingtime\.com/og/([^"]+)\.jpg"', s2) or \
             re.search(r'content="https://thecrossingtime\.com/og/([^"]+)\.jpg" property="og:image"', s2)
        if mi and not os.path.exists('og/%s.jpg' % mi.group(1)):
            get_image(s2, mi.group(1))
        if 'rel="canonical"' not in s2:
            s2 = s2.replace('</head>', '<link rel="canonical" href="%s">\n</head>' % good, 1)
        if '<meta name="description"' not in s2:
            d0 = clip(get_desc(s2))
            if d0:
                s2 = s2.replace('</head>', '<meta name="description" content="%s">\n</head>' % esc(d0), 1)
        if s2 != s:
            s = s2; dirty = True
        if 'og:title' in s:
            if dirty:
                open(p, 'w', encoding='utf-8').write(s)
                changed += 1
            else:
                skipped += 1
            continue
        stem = fn[:-5]
        url = '%s/%s/%s' % (BASE, folder, fn.lower())
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
