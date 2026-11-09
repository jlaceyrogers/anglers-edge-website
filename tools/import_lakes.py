#!/usr/bin/env python3
"""Turn lake packs into compact page records: data/lakes/<id>.json

Sources: the app's bundled lakes (web/data/lakes/<id>/) and unzipped catalog
packs (a folder per pack id holding lake_outline.geojson, hotspots_default
.geojson, manifest.json, place_names.geojson, config/species_profiles.json).

    python3 tools/import_lakes.py <app web/data dir> <unzipped packs dir>
"""
import json, math, os, sys, pathlib
APP = pathlib.Path(sys.argv[1]); PACKS = pathlib.Path(sys.argv[2])
STOCK = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None   # stocking/<id>.json sidecars (optional)
OUT = pathlib.Path(__file__).resolve().parent.parent / 'data' / 'lakes'
OUT.mkdir(parents=True, exist_ok=True)

ADMINS = {'CA-ON': ('Ontario', 'ON', 'Canada'), 'CA-MB': ('Manitoba', 'MB', 'Canada'),
  'CA-QC': ('Quebec', 'QC', 'Canada'), 'CA-SK': ('Saskatchewan', 'SK', 'Canada'),
  'CA-AB': ('Alberta', 'AB', 'Canada'), 'CA-BC': ('British Columbia', 'BC', 'Canada'),
  'US-MN': ('Minnesota', 'MN', 'United States'), 'US-MI': ('Michigan', 'MI', 'United States'),
  'US-WI': ('Wisconsin', 'WI', 'United States'), 'US-NY': ('New York', 'NY', 'United States'),
  'US-NH': ('New Hampshire', 'NH', 'United States'), 'US-CT': ('Connecticut', 'CT', 'United States'), 'US-OH': ('Ohio', 'OH', 'United States')}
PREFIX = {'qc': 'CA-QC', 'mb': 'CA-MB', 'sk': 'CA-SK', 'ab': 'CA-AB', 'bc': 'CA-BC',
  'mn': 'US-MN', 'mi': 'US-MI', 'wi': 'US-WI', 'ny': 'US-NY', 'nh': 'US-NH', 'ct': 'US-CT', 'oh': 'US-OH'}
AREAS = {**{k: 'Muskoka' for k in 'muskoka rosseau joseph bays bigwind fairy mary muldrew peninsula skeleton vernon lakeofbays'.split()},
  **{k: 'Haliburton' for k in 'kawagama kushog drag kashagawigamog kennisis boshkung head mountain twelvemile'.split()},
  **{k: 'Kawarthas' for k in 'rice scugog balsam chemong pigeon buckhorn lowerbuckhorn cameron stony sturgeon'.split()},
  **{k: 'Eastern Ontario' for k in 'charleston haybay biggull bigrideau bobs newboro sharbot white'.split()},
  **{k: 'Sudbury' for k in 'ramsey vermilion long mcfarlane wanapitei'.split()},
  **{k: 'Northwest' for k in 'blacksturgeon dryberry kakagi wabigoon minnitaki pelican abram pakwash lacdesmillelacs perrault wabaskang pickerel'.split()},
  'bernard': 'Almaguin', 'blackstone': 'Parry Sound', 'crane': 'Parry Sound', 'manitou': 'Manitoulin',
  'mindemoya': 'Manitoulin', 'temagami': 'Temagami', 'trout': 'North Bay',
  'qc-brome': 'Eastern Townships', 'qc-massawippi': 'Eastern Townships', 'qc-memphremagog': 'Eastern Townships',
  'qc-tremblant': 'Laurentians', 'qc-iles': 'Laurentians', 'qc-ouareau': 'Lanaudière',
  'qc-nemiscachingue': 'Lanaudière', 'qc-tourbis': 'Lanaudière'}

# single source of truth for local area names: the app's regions.js AREAS table
# (the catalog carries no region field; the app and this site must agree)
_APP_REGIONS = APP.parent / 'js' / 'regions.js'
if _APP_REGIONS.exists():
    import re as _re
    _m = _re.search(r'var AREAS = \{(.*?)\};', _APP_REGIONS.read_text(encoding='utf-8'), _re.S)
    AREAS.update({k: v for k, v in _re.findall(r"'?([a-z0-9-]+)'?\s*:\s*'([^']+)'", _m.group(1))})

def region(l):
    r = l.get('region') or {}
    admin = r.get('admin') if r.get('admin') in ADMINS else None
    if not admin:
        p = l['id'].split('-')[0]
        admin = PREFIX.get(p, 'CA-ON')
    name, short, country = ADMINS[admin]
    return {'admin': admin, 'name': name, 'short': short, 'country': country,
            'area': r.get('area') or AREAS.get(l['id'])}

def badge(l):
    b = (l.get('badge') or '').lower()
    if b: return l['badge']
    if l.get('cv'): return 'survey-grade'
    n = (l.get('_notes') or '').lower()
    if 'hybrid' in n: return 'hybrid survey'
    if l.get('vintage') or 'contour' in n: return 'contour-derived'
    return 'sounding survey'

def rdp(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / L
        if d > dmax: dmax, idx = d, i
    if dmax > eps:
        return rdp(pts[:idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]

def project(lon, lat, lon0, lat0):
    k = 111320.0
    return ((lon - lon0) * k * math.cos(math.radians(lat0)), (lat - lat0) * k)

def rings_of(geom):
    if geom['type'] == 'Polygon': return geom['coordinates']
    if geom['type'] == 'MultiPolygon': return [r for poly in geom['coordinates'] for r in poly]
    return []

def stocking_of(lake_id, d):
    """Compact stocking summary from the pack's config/stocking.json or the sidecar dir."""
    for cand in [d / 'config' / 'stocking.json'] + ([STOCK / (lake_id + '.json')] if STOCK else []):
        if cand.exists():
            try: st = json.load(open(cand))
            except Exception: return None
            sm = st.get('summary') or {}
            return {'events': sm.get('events', 0), 'first': sm.get('first_year'), 'last': sm.get('last_year'),
                    'species': [{'species': x['species'], 'events': x['events'], 'first': x['first'], 'last': x['last']} for x in (st.get('species') or [])[:6]],
                    'note': st.get('note'), 'by_name': 'name + distance' in (st.get('join') or '')}
    return None

def build(l, d):
    outline = json.load(open(d / 'lake_outline.geojson'))
    rings = [r for f in outline['features'] for r in rings_of(f['geometry'])]
    lon0, lat0 = l['center'][0], l['center'][1]
    proj = [[project(x, y, lon0, lat0) for x, y in ring] for ring in rings]
    # simplify to ~12 m, drop specks, cap total points
    def rdp_ring(r):                       # closed ring: split so RDP has a real baseline
        mid = len(r) // 2
        return rdp(r[:mid + 1], 12.0)[:-1] + rdp(r[mid:], 12.0)
    simp = [rdp_ring(r) for r in proj]
    simp = [r for r in simp if len(r) >= 4 and abs(sum(r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1] for i in range(len(r)-1)))/2 > 1500]
    xs = [p[0] for r in simp for p in r]; ys = [p[1] for r in simp for p in r]
    bbox = [min(xs), min(ys), max(xs), max(ys)]
    hs = json.load(open(d / 'hotspots_default.geojson'))['features']
    # the default file carries every species x season: keep ONE ranking
    from collections import Counter
    combos = Counter((f['properties'].get('species'), f['properties'].get('season')) for f in hs)
    lead = next(((sp, se) for (sp, se), _ in combos.most_common() if sp == 'smallmouth_bass' and se == 'summer'), combos.most_common(1)[0][0])
    hs = [f for f in hs if (f['properties'].get('species'), f['properties'].get('season')) == lead]
    hs.sort(key=lambda f: f['properties'].get('rank', 999))
    spots = []
    lead_species, lead_season = lead
    for f in hs[:8]:
        p = f['properties']; x, y = project(f['geometry']['coordinates'][0], f['geometry']['coordinates'][1], lon0, lat0)
        reasons = eval(p['reasons']) if isinstance(p['reasons'], str) else p['reasons']
        reasons = [r for r in reasons if not r.startswith(('oxycline gate', 'thermocline'))][:3]
        spots.append({'rank': p['rank'], 'score': round(p['score'], 2), 'depth_m': p.get('depth_m'),
                      'x': round(x), 'y': round(y), 'reasons': [r[0].upper() + r[1:] for r in reasons]})
    m = json.load(open(d / 'manifest.json'))
    sp = []
    try:
        s = json.load(open(d / 'config' / 'species_profiles.json'))
        sp = [v.get('common_name') for v in s['species'].values() if v.get('common_name')]
    except Exception: pass
    extra = l.get('species_extra')
    if isinstance(extra, str): sp += [e.strip() for e in extra.split('·') if e.strip()]
    elif isinstance(extra, list): sp += extra
    seen = set(); sp = [x for x in sp if not (x in seen or seen.add(x))]
    names = []
    try:
        pn = json.load(open(d / 'place_names.geojson'))['features']
        pn.sort(key=lambda f: f['properties'].get('label_rank', 9))
        names = [f['properties']['name'] for f in pn[:6]]
    except Exception: pass
    cv = m.get('cv') or l.get('cv') or {}
    rng = m.get('sounding_depth_range_m')
    return {'id': l['id'], 'name': l['name'], 'center': [lon0, lat0], 'area_km2': l.get('area_km2'),
            'region': region(l), 'badge': badge(l), 'bundled': bool(l.get('dataPath')),
            'size_mb': round((l.get('size_bytes') or 0) / 1e6, 1) or None,
            'survey_year': m.get('survey_year'), 'survey_method': m.get('survey_method'),
            'soundings': m.get('soundings_inside_lake'), 'mae_m': cv.get('mae_m') if isinstance(cv, dict) else None,
            'max_depth_m': (rng[1] if isinstance(rng, list) and len(rng) == 2 else None),
            'species': sp, 'places': names, 'blurb': l.get('blurb') or '',
            'lead_species': lead_species, 'lead_season': lead_season,
            'rings': [[[round(x), round(y)] for x, y in r] for r in simp], 'bbox': [round(v) for v in bbox],
            'spots': spots, 'stocking': stocking_of(l['id'], d)}

bundled = json.load(open(APP / 'lakes.json'))['lakes']
catalog = json.load(open(PACKS / 'catalog.json'))['packs']
names = {l['name'] for l in bundled}
n = 0
for l in bundled:
    rec = build(l, APP / 'lakes' / l['id']); json.dump(rec, open(OUT / (l['id'] + '.json'), 'w'), separators=(',', ':')); n += 1
import math as _m
bcenter = {l['name']: l.get('center') for l in bundled}
def _far(a, b):   # same name, different water: more than 25 km apart is its own lake
    if not a or not b: return False
    dy = (a[1] - b[1]) * 111; dx = (a[0] - b[0]) * 111 * _m.cos(_m.radians((a[1] + b[1]) / 2))
    return (dx * dx + dy * dy) ** 0.5 > 25
for p in catalog:
    if p['id'] in {l['id'] for l in bundled} or (p['name'] in names and not _far(p.get('center'), bcenter.get(p['name']))):
        print('skip duplicate of a bundled lake:', p['id'], p['name']); continue
    d = PACKS / p['id']
    if not (d / 'manifest.json').exists(): print('missing pack dir', p['id']); continue
    try:
        rec = build(p, d); json.dump(rec, open(OUT / (p['id'] + '.json'), 'w'), separators=(',', ':')); n += 1
    except Exception as e: print('FAIL', p['id'], e)
print(n, 'lake records written to', OUT)
