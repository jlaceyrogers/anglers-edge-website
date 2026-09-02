#!/usr/bin/env python3
"""Assemble src/ into index.html (assets as files — fast, cacheable, SEO-friendly)
and artifact.html (everything inlined, for the claude.ai preview)."""
import base64, pathlib, mimetypes, re
root = pathlib.Path(__file__).parent
APPSTORE = 'https://apps.apple.com/app/anglers-edge/id0000000000'   # replace with the real listing URL
PRIVACY = 'privacy.html'
def data_uri(name):
    p = root / 'assets' / name
    return f"data:{mimetypes.guess_type(str(p))[0]};base64," + base64.b64encode(p.read_bytes()).decode()
page = (root / 'src/page.html').read_text()
css = (root / 'src/style.css').read_text()
js = (root / 'src/game.js').read_text()
imgs = {n: [f.name for f in (root / 'assets').iterdir() if f.name.startswith(n + '-')][0]
        for n in ['01', '02', '03', '04', '05', '06']}
def render(inline):
    html = page.replace('{{CSS}}', css)
    html = html.replace('{{APPSTORE}}', APPSTORE).replace('{{PRIVACY}}', PRIVACY)
    for n, name in imgs.items():
        html = html.replace('{{IMG_' + n + '}}', data_uri(name) if inline else 'assets/' + name)
    html = html.replace('{{ICON}}', data_uri('icon.png') if inline else 'assets/icon.png')
    html = html.replace('{{GAME_SCRIPT}}',
        '<script>' + js + '</script>' if inline else '<script src="game.js" defer></script>')
    return html
(root / 'index.html').write_text(render(False))
(root / 'game.js').write_text(js)
full = render(True)
body = re.search(r'<body>(.*)</body>', full, re.S).group(1)
head = re.search(r'<head>(.*)</head>', full, re.S).group(1)
keep = re.findall(r'<title>.*?</title>|<link rel="stylesheet"[^>]*>|<link rel="preconnect"[^>]*>|<style>.*?</style>', head, re.S)
(root / 'artifact.html').write_text('\n'.join(keep) + '\n' + body)
print('index.html', len(render(False)) // 1024, 'KB · artifact.html', len(full) // 1024, 'KB')
