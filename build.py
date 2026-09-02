#!/usr/bin/env python3
"""Assemble src/ + assets/ into a single self-contained index.html."""
import base64, pathlib, mimetypes
root = pathlib.Path(__file__).parent
def data_uri(p):
    p = root / 'assets' / p
    mt = mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
    return f"data:{mt};base64," + base64.b64encode(p.read_bytes()).decode()
html = (root / 'src/page.html').read_text()
html = html.replace('{{CSS}}', (root / 'src/style.css').read_text())
html = html.replace('{{JS}}', (root / 'src/game.js').read_text())
html = html.replace('{{ICON}}', data_uri('icon.png'))
for n in ['01', '02', '03', '04', '05', '06']:
    name = [f for f in (root / 'assets').iterdir() if f.name.startswith(n + '-')][0].name
    html = html.replace('{{IMG_' + n + '}}', data_uri(name))
cfg = {'{{APPSTORE}}': 'https://apps.apple.com/app/anglers-edge/id0000000000',   # replace with the real listing URL
       '{{PRIVACY}}': 'privacy.html'}
for k, v in cfg.items(): html = html.replace(k, v)
(root / 'index.html').write_text(html)
print('wrote index.html', len(html) // 1024, 'KB')
