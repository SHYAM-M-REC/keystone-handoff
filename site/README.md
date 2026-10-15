# KEYSTONE site (React)

A one-page showcase: hero with the simulated temple in 3D, the problem, how it works, an interactive temple lab
(month slider, crack gaps, what KEYSTONE says), season-vs-damage chart, head-to-head table, a sample inspection order,
and an honest "proven / not proven" page. All data is SIMULATED and the page says so.

## Just open it
Double-click `keystone-site.html` in the project root (one self-contained file, works offline).

## Edit and run it
Needs Node 18+.
```
cd site
npm install
npm run dev        # live preview at http://localhost:5173
npm run build      # writes dist/index.html (single file); copy it over ../keystone-site.html
```

## Put your links in
Edit `src/config.js` (repository and video links). Empty links are hidden.

## Regenerate the data
The 3D temple and every number come from the project's Python code:
```
python tools/export_site_data.py site/src/data/temple.json
```
Run it from the project root with the venv active. Then `npm run build` again.

## Where things are
`src/components/` Hero, Problem, Pipeline, Lab (3D + controls), Season (chart), Compare, Order, Proof, Footer.
`src/components/Scene.jsx` the three.js point cloud. `src/styles.css` all styling.
Fonts (Bricolage Grotesque, IBM Plex Sans, SIL OFL) are bundled in `src/assets/fonts/`.
