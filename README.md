# Anglers Edge — website

Single-file marketing site with the "Out-fish the model" interactive lake
(Three.js). Everything is inlined into `index.html` (images, CSS, JS), so
hosting is: upload `index.html` and `privacy.html` anywhere.

## Deploy (free, 5 minutes)
- **GitHub Pages:** create a repo, add `index.html` + `privacy.html`, Settings →
  Pages → deploy from `main`. Point your domain at it if you have one.
- Any static host works the same (Netlify, Cloudflare Pages, Vercel: drag the
  folder in).

## Before launch
1. Put the real App Store URL in `build.py` (`{{APPSTORE}}`) and run
   `python3 build.py` — the "Get it on the App Store" buttons update.
2. Add your domain to the Open Graph tags in `src/page.html` if you want
   link previews with an image.

## Editing
- Copy and layout: `src/page.html`
- Styles: `src/style.css`  (colours are the app's Fieldbook palette)
- The lake game: `src/game.js`
- Screenshots / icon: `assets/` (regenerate from the app's
  `resources/app-store-screenshots` when the app changes)
- Rebuild after any edit: `python3 build.py`

## Preview locally
`node serve.mjs 8140` then open http://localhost:8140

The game scores casts with a small copy of the app's model (depth band,
break proximity, hump proximity — smallmouth in summer) on a procedurally
generated lake, then reveals the model's own top spots after three casts.
