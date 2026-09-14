#!/usr/bin/env python3
"""Assemble src/ into index.html (assets as files — fast, cacheable, SEO-friendly)
and artifact.html (everything inlined, for the claude.ai preview)."""
import hashlib
import base64, pathlib, mimetypes, re
root = pathlib.Path(__file__).parent
APPSTORE = 'https://apps.apple.com/app/anglers-edge/id6798728175'   # replace with the real listing URL
PRIVACY = 'privacy.html'
def stamped(name):
    # assets are served immutable for a year (vercel.json); a content hash in
    # the URL makes every browser and the CDN fetch a changed file immediately
    h = hashlib.sha1(open('assets/' + name, 'rb').read()).hexdigest()[:8]
    return 'assets/' + name + '?v=' + h


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
        html = html.replace('{{IMG_' + n + '}}', data_uri(name) if inline else stamped(name))
    html = html.replace('{{ICON}}', data_uri('icon.png') if inline else stamped('icon.png'))
    html = html.replace('{{GAME_SCRIPT}}',
        '<script>' + js + '</script>' if inline else '<script src="game.js" defer></script>')
    return html

# ---------------- lake pages ----------------
import json, html as _html
SITE = 'https://anglersedge.fishing'
lake_tpl = (root / 'src/lake.html').read_text()
LAKES = sorted([json.load(open(f)) for f in (root / 'data/lakes').glob('*.json')], key=lambda r: r['name'])
NAV = re.search(r'<nav class="nav">.*?</nav>', page, re.S).group(0).replace('href="#', 'href="/#').replace('{{ICON}}', '/' + stamped('icon.png')).replace('{{APPSTORE}}', APPSTORE)
FOOTER = re.search(r'<footer>.*?</footer>', page, re.S).group(0).replace('href="#', 'href="/#').replace('{{PRIVACY}}', '/' + PRIVACY)
def esc(x): return _html.escape(str(x), quote=True)
def tier(sc): return 'good' if sc >= 0.6 else 'fair'
def badge_of(r):
    if r.get('mae_m') and r.get('soundings'): return 'survey-grade'
    return r['badge']
def svg_of(r):
    x0, y0, x1, y1 = r['bbox']; w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    s = 640.0 / max(w, h); W, H = round(w * s) + 48, round(h * s) + 48
    tx = lambda x: 24 + (x - x0) * s; ty = lambda y: 24 + (y1 - y) * s
    d = ''.join('M' + ' L'.join(f'{tx(x):.1f} {ty(y):.1f}' for x, y in ring) + 'Z' for ring in r['rings'])
    coins = ''
    for sp in r['spots']:
        cx, cy = tx(sp['x']), ty(sp['y']); fill = '#217A4B' if tier(sp['score']) == 'good' else '#C08A12'
        coins += (f'<g><circle cx="{cx:.1f}" cy="{cy:.1f}" r="13" fill="{fill}" stroke="#FFFDF6" stroke-width="2.5"/>'
                  f'<text x="{cx:.1f}" y="{cy + 4.5:.1f}" text-anchor="middle" font-family="Source Serif 4,Georgia,serif" font-weight="700" font-size="13" fill="#FDF9EE">{sp["rank"]}</text></g>')
    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Outline of {esc(r["name"])} with its top ranked fishing spots">'
            f'<rect width="{W}" height="{H}" fill="#F3ECDB" rx="14"/>'
            f'<path d="{d}" fill="#9EBCCB" stroke="#5F7F8E" stroke-width="1.2" fill-rule="evenodd"/>{coins}</svg>')
def facts_of(r):
    f = []
    if r.get('area_km2'): f.append(('Water area', f"{r['area_km2']:g} km²", ''))
    if r.get('max_depth_m'): f.append(('Deepest sounding', f"{r['max_depth_m']:g} m", ''))
    if r.get('survey_year'): f.append(('Survey', str(r['survey_year']), esc(r.get('survey_method') or '')))
    if r.get('soundings'): f.append(('Soundings', f"{r['soundings']:,}", 'measured depth points'))
    if r.get('mae_m'): f.append(('Model accuracy', f"±{r['mae_m']:g} m", 'cross-validated'))
    f.append(('Data', badge_of(r).replace('-', ' ').title(), 'built in, free' if r['bundled'] else f"free download · {r['size_mb'] or ''} MB".rstrip(' ·')))
    return ''.join(f'<div><dt>{k}</dt><dd>{v}{"<small>" + sub + "</small>" if sub else ""}</dd></div>' for k, v, sub in f)
def spots_of(r):
    out = ''
    for sp in r['spots']:
        depth = f"<b>{sp['depth_m']:g} m</b> deep · " if sp.get('depth_m') is not None else ''
        out += (f'<li><div class="rank {tier(sp["score"])}">{sp["rank"]}</div><div><div class="meta">{depth}score <b>{sp["score"]:.2f}</b> · {"good" if tier(sp["score"]) == "good" else "fair"}</div>'
                f'<ul>{"".join("<li>" + esc(x) + "</li>" for x in sp["reasons"])}</ul></div></li>')
    return out
def region_label(r): return (r['region']['area'] + ', ' if r['region'].get('area') else '') + r['region']['name']
def render_lake(r):
    reg = r['region']; name = r['name']
    title = f"{name} Fishing Map — Depth, Structure & Ranked Spots | Anglers Edge"
    desc = (f"Free offline fishing map for {name} ({region_label(r)}): surveyed depth, humps, breaklines and {len(r['spots'])} ranked spots with reasons, "
            f"for {', '.join(r['species'][:3]) or 'your species'}. Analysis only, not for navigation.")
    lead = r['spots'][0] if r['spots'] else None
    inapp_h2 = f"{name} is built into Anglers Edge." if r['bundled'] else f"{name} is a free download inside Anglers Edge."
    inapp_p = ("Open the app and it's already there — no download, no signal needed." if r['bundled'] else
               f"One tap in the lake picker fetches the {r['size_mb'] or ''} MB pack on Wi-Fi; after that it works fully offline, forever.".replace('the  MB pack', 'the pack'))
    same = [o for o in LAKES if o['id'] != r['id'] and o['region'].get('area') == reg.get('area') and reg.get('area')]
    if len(same) < 3: same += [o for o in LAKES if o['id'] != r['id'] and o not in same and o['region']['admin'] == reg['admin']][:6 - len(same)]
    same.sort(key=lambda o: (o['center'][0] - r['center'][0]) ** 2 + (o['center'][1] - r['center'][1]) ** 2)
    nearby = ' '.join(f'<a href="/lakes/{o["id"]}">{esc(o["name"])}</a>' for o in same[:6])
    honest = (f"Bathymetry for {name} comes from a {r['survey_year']} {esc(r.get('survey_method') or 'survey')} with {r['soundings']:,} measured soundings; the depth model cross-validates to ±{r['mae_m']:g} m on held-out points."
              if r.get('survey_year') and r.get('soundings') and r.get('mae_m') else
              f"Bathymetry for {name} is built from the provincial open-data survey record; where soundings are sparse the app marks cells unsurveyed rather than guessing.")
    if reg['admin'] == 'CA-ON': honest += ' Source: Land Information Ontario (Open Government Licence – Ontario).'
    elif reg['admin'] == 'CA-QC': honest += ' Source: Gouvernement du Québec bathymetric survey data (Données Québec).'
    places = ''.join(f'<span>{esc(pn)}</span>' for pn in r['places'] if pn != name)
    jsonld = json.dumps([
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Anglers Edge", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Lakes", "item": SITE + "/lakes"},
            {"@type": "ListItem", "position": 3, "name": name, "item": f"{SITE}/lakes/{r['id']}"}]},
        {"@context": "https://schema.org", "@type": "LakeBodyOfWater", "name": name,
         "geo": {"@type": "GeoCoordinates", "latitude": round(r['center'][1], 4), "longitude": round(r['center'][0], 4)},
         "containedInPlace": {"@type": "AdministrativeArea", "name": reg['name']},
         "subjectOf": {"@type": "WebPage", "url": f"{SITE}/lakes/{r['id']}", "name": title}}], ensure_ascii=False)
    out = lake_tpl
    for k, v in {'TITLE': esc(title), 'DESC': esc(desc), 'URL': f"{SITE}/lakes/{r['id']}", 'CSS': css, 'NAV': NAV, 'FOOTER': FOOTER,
                 'ADMIN': reg['admin'], 'ADMIN_NAME': esc(reg['name']), 'EYEBROW': esc(region_label(r)), 'H1': esc(name) + ' fishing map',
                 'LEDE': esc(f"Surveyed depth, structure and ranked fishing spots for {name} — scored for your species and the day's conditions, and it all works with no signal. Free."),
                 'APPSTORE': APPSTORE, 'SVG': svg_of(r), 'N_SPOTS': str(len(r['spots'])),
                 'LEAD_SPECIES': esc((r.get('lead_species') or 'smallmouth_bass').replace('_', ' ').title()), 'LEAD_SEASON': esc(r.get('lead_season') or 'summer'),
                 'FACTS': facts_of(r), 'NAME': esc(name), 'SPOTS': spots_of(r), 'INAPP_H2': esc(inapp_h2), 'INAPP_P': esc(inapp_p),
                 'SPECIES': ''.join(f'<span>{esc(x)}</span>' for x in r['species']) or '<span>Default profiles</span>',
                 'PLACES_BLOCK': (f'<h3>Named water</h3><p class="tags">{places}</p>' if places else ''),
                 'NEARBY': nearby, 'HONEST': honest, 'JSONLD': jsonld}.items():
        out = out.replace('{{' + k + '}}', v)
    return out
(root / 'lakes').mkdir(exist_ok=True)
for r in LAKES: (root / 'lakes' / (r['id'] + '.html')).write_text(render_lake(r))
# lakes index
def index_page():
    groups = {}
    for r in LAKES: groups.setdefault((r['region']['country'], r['region']['admin'], r['region']['name']), []).append(r)
    body = ''
    for (country, admin, aname), rs in sorted(groups.items(), key=lambda kv: (['Canada', 'United States'].index(kv[0][0]) if kv[0][0] in ('Canada', 'United States') else 9, kv[0][2])):
        body += f'<h2 id="{admin}">{esc(aname)} <span class="dim" style="font-weight:500;font-size:16px">· {len(rs)} lakes</span></h2>'
        areas = {}
        for r in rs: areas.setdefault(r['region'].get('area') or 'Other', []).append(r)
        for area, ars in sorted(areas.items()):
            body += f'<h3>{esc(area)}</h3><ul class="lakes">' + ''.join(
                f'<li><a href="/lakes/{r["id"]}">{esc(r["name"])}</a><small>{(str(r["area_km2"]) + " km²") if r.get("area_km2") else ""}</small></li>' for r in sorted(ars, key=lambda x: x['name'])) + '</ul>'
    title = f"Fishing Maps for {len(LAKES)} Lakes Across Canada & the US | Anglers Edge"
    desc = f"Every lake in Anglers Edge by province, state and area: {len(LAKES)} lakes across Canada and the United States with surveyed depth maps, structure layers and ranked fishing spots, all offline and free."
    out = lake_tpl.split('<main>')[0] + f'<main class="wrap lakes-index" style="padding:120px 20px 60px"><div class="eyebrow">Lakes we cover</div><h1>{len(LAKES)} lakes, each with its own map and ranked spots.</h1><p class="lede">Tap a lake for its depth map, top spots and data sources. Every one is free in the app.</p>{body}</main>' + FOOTER + '</body></html>'
    for k, v in {'TITLE': esc(title), 'DESC': esc(desc), 'URL': SITE + '/lakes', 'CSS': css, 'NAV': NAV,
                 'JSONLD': json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "url": SITE + "/lakes"})}.items():
        out = out.replace('{{' + k + '}}', v)
    return out
(root / 'lakes.html').write_text(index_page())
# sitemap
urls = [(SITE + '/', 'weekly', '1.0'), (SITE + '/lakes', 'weekly', '0.8'), (SITE + '/privacy.html', 'yearly', '0.2')] + [(f"{SITE}/lakes/{r['id']}", 'monthly', '0.7') for r in LAKES]
(root / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{u}</loc><changefreq>{c}</changefreq><priority>{p}</priority></url>\n' for u, c, p in urls) + '</urlset>\n')
# home page lake list + counts
LAKE_LIST = '<ul class="lakes">' + ''.join(f'<li><a href="/lakes/{r["id"]}">{esc(r["name"])}</a></li>' for r in LAKES) + '</ul>'
def with_lakes(h): return h.replace('{{LAKE_LIST}}', LAKE_LIST).replace('{{N_LAKES}}', str(len(LAKES))).replace('{{N_DL}}', str(len([r for r in LAKES if not r['bundled']])))
(root / 'index.html').write_text(with_lakes(render(False)))
(root / 'game.js').write_text(js)
full = with_lakes(render(True))
body = re.search(r'<body>(.*)</body>', full, re.S).group(1)
head = re.search(r'<head>(.*)</head>', full, re.S).group(1)
keep = re.findall(r'<title>.*?</title>|<link rel="stylesheet"[^>]*>|<link rel="preconnect"[^>]*>|<style>.*?</style>', head, re.S)
(root / 'artifact.html').write_text('\n'.join(keep) + '\n' + body)
print('index.html', len(render(False)) // 1024, 'KB · artifact.html', len(full) // 1024, 'KB')
