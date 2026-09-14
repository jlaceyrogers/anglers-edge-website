#!/usr/bin/env python3
"""Per-lake Open Graph images (1200x630): the lake outline with its top spots,
name and region, in the Fieldbook look. Renders each with headless Chrome into
assets/og/<id>.png. Run after tools/import_lakes.py."""
import json, pathlib, subprocess, tempfile, sys
root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
out = root / 'assets' / 'og'; out.mkdir(parents=True, exist_ok=True)
def svg_of(r, box_w, box_h):
    x0, y0, x1, y1 = r['bbox']; w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    s = min(box_w / w, box_h / h); W, H = w * s, h * s
    ox, oy = (box_w - W) / 2, (box_h - H) / 2
    tx = lambda x: ox + (x - x0) * s; ty = lambda y: oy + (y1 - y) * s
    d = ''.join('M' + ' L'.join(f'{tx(x):.1f} {ty(y):.1f}' for x, y in ring) + 'Z' for ring in r['rings'])
    coins = ''
    for sp in r['spots'][:6]:
        cx, cy = tx(sp['x']), ty(sp['y']); fill = '#217A4B' if sp['score'] >= 0.6 else '#C08A12'
        coins += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="15" fill="{fill}" stroke="#FFFDF6" stroke-width="3"/><text x="{cx:.1f}" y="{cy+5.5:.1f}" text-anchor="middle" font-family="New York,Georgia,serif" font-weight="700" font-size="15" fill="#FDF9EE">{sp["rank"]}</text>'
    return f'<svg viewBox="0 0 {box_w} {box_h}" width="{box_w}" height="{box_h}" xmlns="http://www.w3.org/2000/svg"><path d="{d}" fill="#9EBCCB" stroke="#5F7F8E" stroke-width="1.5" fill-rule="evenodd"/>{coins}</svg>'
tpl = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;width:1200px;height:630px;background:#F7F2E6;font-family:-apple-system,Helvetica,sans-serif;color:#22301F;overflow:hidden}
.l{position:absolute;left:64px;top:64px;width:520px}
.eye{font-size:18px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#D9480F}
h1{font-family:'New York',Georgia,serif;font-size:64px;line-height:1.02;margin:14px 0 18px;letter-spacing:-.01em}
p{font-size:22px;line-height:1.4;color:#5F6D5C;margin:0 0 26px}
.brand{position:absolute;left:64px;bottom:56px;display:flex;align-items:center;gap:14px;font-family:'New York',Georgia,serif;font-weight:700;font-size:26px}
.brand img{width:44px;height:44px;border-radius:11px}
.brand small{font:600 15px/1 -apple-system,Helvetica,sans-serif;color:#5F6D5C;letter-spacing:.08em;text-transform:uppercase;margin-left:6px}
.map{position:absolute;right:56px;top:56px;width:520px;height:518px;background:#F3ECDB;border-radius:24px;box-shadow:0 2px 8px rgba(40,40,20,.08)}
.map svg{position:absolute;left:30px;top:30px}
</style></head><body>
<div class="l"><div class="eye">%(region)s</div><h1>%(name)s</h1><p>%(sub)s</p></div>
<div class="brand"><img src="file://%(icon)s"> Anglers Edge <small>free · offline</small></div>
<div class="map">%(svg)s</div></body></html>"""
icon = root / 'assets' / 'icon.png'
n = 0
for f in sorted((root / 'data/lakes').glob('*.json')):
    r = json.load(open(f))
    reg = (r['region'].get('area') + ', ' if r['region'].get('area') else '') + r['region']['name']
    sub = f"Surveyed depth map and {len(r['spots'])} ranked fishing spots, with the reasons. Works with no signal."
    html = tpl % {'region': reg, 'name': r['name'], 'sub': sub, 'icon': icon, 'svg': svg_of(r, 460, 458)}
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as t: t.write(html); path = t.name
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--window-size=1200,630',
                    '--allow-file-access-from-files', f'--screenshot={out / (r["id"] + ".png")}', 'file://' + path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    n += 1
print(n, 'og images ->', out)
