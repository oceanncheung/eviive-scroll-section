# EVIIVE — Therapy Alignment Scroll Section

Scroll-driven WebGL section visualising the clinical finding:

> 124 first-line metastatic melanoma patients on anti-PD-1 mono or anti-PD-1 +
> anti-CTLA-4 combination therapy. 85 (69%) covered by the platform's cut-offs.
> Regimen aligned with the prediction: **53.5 months** median PFS.
> Not aligned: **6.4 months**.

## Status
`golden/eviive-section-v1.0-desktop.html` — desktop, signed off.
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

## Non-obvious decisions
See `NOTES.md` — several of these look wrong until you know why.
