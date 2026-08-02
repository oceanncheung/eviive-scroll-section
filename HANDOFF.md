# Handoff — EVIIVE therapy-alignment scroll section

Paste this whole file to a new agent as its first message.

---

You are picking up live work for Ocean Cheung, marketing/design lead at EVIIVE, a
Zurich precision-oncology company. Read this in full before acting.

## What the thing is

A scroll-driven WebGL section for eviive.ch that visualises one clinical finding:

> 124 first-line metastatic melanoma patients on anti-PD-1 mono or anti-PD-1 +
> anti-CTLA-4 combination therapy. 85 (69%) covered by the platform's cut-offs.
> Regimen aligned with the prediction: **53.5 months** median PFS.
> Not aligned: **6.4 months**.

Two states. It opens on 6.4 months; one deliberate scroll takes it to 53.5. The
orb morphs grey → blue glass, the ground lifts navy → near-white, an odometer
rolls, and a tick rail rescales. `1 world unit = 1 month`, so the geometry *is*
the data at the true 8.36x ratio.

The section is already placed on the **live Framer homepage**, between
"Biomarker Opportunity" and "Metrics". It is **not published** — Framer edits do
not reach eviive.ch until Ocean presses Publish. Do not publish.

## Repo

`/Users/oceancheung/Documents/Startup/MM.S/EVIIVE/eviive-scroll-section`
→ `https://github.com/oceanncheung/eviive-scroll-section` (public, GitHub Pages on)

| file | what it is |
|---|---|
| `index.html` | **source of truth** for CSS, DOM markup, and the scroll driver |
| `src/main.jsx` | **source of truth** for the R3F scene (orb + backdrop shaders) |
| `gen.py` | build: turns those two into `dist/eviive-section.js` |
| `dist/eviive-section.js` | generated. **Never hand-edit.** This is what ships |
| `mkharness.py` | builds a local browser harness for testing outside Framer |
| `golden/` | signed-off standalone builds; `v1.2-responsive.html` is the reference |
| `NOTES.md`, `ORB.md` | hard-won decisions. **Read both before touching the scene** |

## How it reaches Framer

Framer forbids npm imports beyond react / react-dom / framer / framer-motion, so
three.js cannot be installed there. The route around it:

1. `gen.py` emits `dist/eviive-section.js` — a plain ESM module exporting
   `mount(host)` and returning a teardown. **It contains no React**, so it cannot
   collide with Framer's instance.
2. GitHub Pages serves it at
   `https://oceanncheung.github.io/eviive-scroll-section/dist/eviive-section.js`
3. three / @react-three/fiber / postprocessing are fetched from **esm.sh at
   runtime**. Framer leaves such URLs untouched in its build — verified. It does
   **not** vendor them; static and dynamic imports behave identically.
4. The compiled scene is inlined as a string and loaded via a **blob URL**, so no
   second file needs hosting.
5. Framer holds two small code files that should never need changing again.

### Framer code files

- **`EviiveSection.tsx`** (id `LLlhJpB`) — the wrapper placed on the canvas.
  Carries the `RenderTarget` canvas guard, a `--vw`/`--vh` fallback, a
  `scroll-snap-type: proximity` override, and the nav fade.
- **`EviiveScrollSection.tsx`** (id `WZ8vDZf`) — should be a ~25-line stub that
  imports the hosted URL and calls `mount()`. **VERIFY THIS FIRST.** Ocean was
  asked to paste that stub in. If it still holds ~39KB of inlined strings, then
  nothing pushed to GitHub is reaching him and every "fix" will appear to do
  nothing.

### Framer node ids

| | |
|---|---|
| home page | `YKZNl8v67` |
| Desktop breakpoint | `xMTVnhBwP` |
| section frame | `nFifHam5M` |
| component instance | `DBnNXhgh4` |

## The loop

```bash
cd eviive-scroll-section
# edit index.html or src/main.jsx — never dist/
python3 gen.py
git add -A dist gen.py index.html src
git commit -m "..." && git push
```

Then Ocean hard-reloads Framer Preview (`Cmd+Shift+R`). Pages takes 30–60s.
GitHub caches ~10 min, so a soft reload can show stale code.

`gen.py` needs a scratch dir holding `node_modules/.bin/esbuild` and `scene.mjs`:

```bash
npm i esbuild
./node_modules/.bin/esbuild ../src/main.jsx --bundle --format=esm \
  --target=es2022 --minify --jsx=automatic \
  --external:react --external:react-dom --external:react/jsx-runtime \
  --external:three --external:@react-three/fiber \
  --external:@react-three/postprocessing --external:postprocessing \
  --outfile=scene.mjs
```

## VERIFICATION — read this twice

The largest source of wasted effort here was **claiming things were fixed without
confirming them.** Three traps, all real, all hit repeatedly:

1. **Framer's typecheck response describes the PREVIOUS upload.** It lags exactly
   one version, every time. A file that failed to compile reports the errors of
   the file before it, so a broken upload looks clean. Never trust it.

2. **The only reliable check is downloading the built artefact and grepping it:**
   ```bash
   curl -sL "https://oceanncheung.github.io/eviive-scroll-section/dist/eviive-section.js" \
     | grep -c "<something you just added>"
   ```
   For a Framer code file, resolve its module URL first:
   ```bash
   curl -sL "https://framer.com/m/EviiveScrollSection-4PZuiy.js" \
     | grep -o 'https://framerusercontent.com/modules/[^"]*' | head -1 | xargs curl -sL
   ```

3. **`gen.py` contains string patches against MINIFIED output.** When the source
   changes shape the pattern stops matching and `gen.py` aborts, leaving the old
   `dist` in place. Each is guarded by `sys.exit`, so **run `gen.py` bare and read
   all of its output.** Do not pipe it through a grep filter — that is exactly how
   a silent failure nearly shipped. Remaining patches: the stacked-mode toggle,
   the debug-HUD listener, and the driver kill-switch.

**Do not tell Ocean something works because it should.** He has been burned by
this repeatedly and is, reasonably, out of patience with it. If you cannot see it,
say so. Asking for a screenshot or a console error is far cheaper than a wrong
guess.

## Working now

- Section on the homepage, opens on 6.4 months
- The **approach** scrubs progress 0→0.5, finishing 75% of the way in, so the
  odometer counts up and the orb settles as the section rises into view
- One deliberate scroll → 53.5 months, on a 2.6s weighted tween
- Scroll-snap engages **only** while the section covers the viewport; entering and
  leaving are ordinary scrolling
- Background full-bleed behind the nav; headline and rail inset by `--nav-h`
- Orb centred; layout driven by measured element width, not the window
- Nav fades out over the dark state, returns white on the light one

## Open

1. **Nav variant.** Ocean is doing this himself. The site has a
   `DesktopTransparent` variant switched by a 1px "NavTrigger" layer in the Hero;
   that binding is a Framer *interaction*, which MCP cannot read or create. The
   current fade is a workaround — set `FADE_NAV = false` in `EviiveSection.tsx`
   once his version lands.

2. **SUSPECTED: dead 100vh tail.** The Framer section frame `nFifHam5M` is
   `height="300vh"`, but `.pin` is now `calc(var(--vh) * 2)` after the drop to two
   states. That likely leaves ~100vh of empty dark section below the pin.
   **Unverified — the Framer plugin was disconnected when this was written.**
   Check `nFifHam5M`; if still 300vh, set it to 200vh.

3. **Orb reads softer than `golden/eviive-section-v1.2-responsive.html`.** Raised
   twice, never confirmed either way by Ocean. Compare against the golden before
   changing anything — `ORB.md` documents which parameters are sensitive and which
   have already been tried and rejected.

4. **Docs are stale.** `README.md`, `NOTES.md`, `ORB.md` predate the whole Framer
   integration. What they say about the standalone prototype still holds; they say
   nothing about hosting, the wrapper, or the two-state change.

## Working with Ocean

- He is a designer and judges by eye. Numeric probes that "confirm" something he
  can see is broken are worthless — screenshot, or check in a real browser.
- He states requirements as principles ("last in first out, that simple").
  Turning those into per-case constants causes drift; write the whole matrix down
  and derive it from one variable. `NOTES.md` has a section on this.
- Batch fixes. Turnaround is push-and-reload, so four issues cost about the same
  as one.
- Never publish. Never make anything else public. Ask before anything
  outward-facing.
