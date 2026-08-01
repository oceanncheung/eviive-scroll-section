# EVIIVE — Therapy Alignment Scroll Section

Scroll-driven WebGL section visualising the clinical finding:

> 124 first-line metastatic melanoma patients on anti-PD-1 mono or anti-PD-1 +
> anti-CTLA-4 combination therapy. 85 (69%) covered by the platform's cut-offs.
> Regimen aligned with the prediction: **53.5 months** median PFS.
> Not aligned: **6.4 months**.

## Status
`golden/eviive-section-v1.2-responsive.html` — desktop + tablet + phone (current).
`golden/eviive-section-v1.1-desktop.html` — desktop only.
`golden/eviive-section-v1.0-desktop.html` — first signed-off desktop.

## Breakpoints
Layout by aspect ratio: stacked when `width/height < 1.15 || width < 900`.
Type by Framer's width bands: phone <=809, tablet 810-1199, desktop >=1200.
These are deliberately different axes — see `NOTES.md`.
Self-contained: bundle + fonts inlined, opens with a double-click.

## Build
```
npm install
npm run build          # → dist/
node ../package.js     # inline bundle + fonts → single html
```

## Architecture
- `src/main.jsx` — React Three Fiber scene: backdrop shader, ONE morphing orb,
  camera rig, depth-of-field / bloom post.
- `index.html` — DOM overlay + scroll driver: headline reveal, odometer,
  tick rail, captions. Plain JS, no framework.
- 1 world unit = 1 month, so the geometry *is* the data at the true 8.36x ratio.

## Documentation
- `ORB.md` — how the EVIIVE orb is made: provenance, palette, every shading
  layer, and which parameters are sensitive. Read before touching the material.
- `NOTES.md` — non-obvious decisions across the whole section. Several look
  wrong until you know why.
