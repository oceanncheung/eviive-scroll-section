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

- **`EviiveSection.tsx`** (id `LLlhJpB`) — **this is the one on the canvas.**
  Loads the hosted bundle, guards the editor canvas via `RenderTarget`, and
  publishes `{active, theme, progress}` for the nav overrides. It does not touch
  the nav itself.
- **`EviiveScrollSection.tsx`** (id `WZ8vDZf`) — a leftover stub, not referenced
  by the homepage. Harmless; safe to delete.
- **`EviiveNavOverrides.tsx`** — Ocean's. Crossfades the two fixed headers off
  the `eviive-nav-theme` event. Leave it alone.

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

2. **`readCodeFile` is the authority for Framer file contents.** The
   *unversioned* `framer.com/m/<name>.js` URL is pinned to an old snapshot and
   will misreport current state — it wrongly convinced me twice that Framer was
   stale. For the hosted bundle, download and grep it:
   ```bash
   curl -sL "https://oceanncheung.github.io/eviive-scroll-section/dist/eviive-section.js" \
     | grep -c "<something you just added>"
   ```
   For a Framer code file, resolve its module URL first:
   ```bash
   curl -sL "https://framer.com/m/EviiveScrollSection-4PZuiy.js" \
     | grep -o 'https://framerusercontent.com/modules/[^"]*' | head -1 | xargs curl -sL
   ```

3. **A throw in the wheel handler looks like nothing at all.** If `onWheel`
   raises before `preventDefault()`, the event simply passes through and the
   section reads as unresponsive — no red console text unless you go looking.
   Two undefined identifiers hid there for hours this way. The handler now
   try/catches and reports once, but **when a gesture "does nothing", check the
   console before changing any logic.** The same trap applies to anything that
   waits on the scene's progress: its spring is asymptotic, so `p` only reaches
   its target because `EASE` is explicitly clamped at `t >= 1`. Remove that clamp
   and the exit gate never opens.

4. **`gen.py` contains string patches against MINIFIED output.** When the source
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
- **No CSS scroll-snap at all.** It offers no control over duration or easing, so
  the module runs a discrete controller: one gesture from the previous section
  lands on 6.4 months, one more goes to EVIIVE. `CATCH_WHEN_IN` 0.8 (the section
  must be 80% into the viewport, measured predictively from wheel velocity,
  before it captures), `STEP_MS` 620, cooldown bounded 420–850ms, `OMEGA` 8.
  Page motion is a critically damped spring seeded with the gesture's own
  velocity, so it continues the reader's movement rather than restarting it.
  There is **one** gate, on the way out of EVIIVE only: input is swallowed until
  `settled()`. Nothing is locked on scene 1 or on the way in. A 6s watchdog
  releases if anything fails
- Background full-bleed behind the nav; headline and rail inset by `--nav-h`
- Orb centred; layout driven by measured element width, not the window
- Nav crossfades between the two headers, driven by the published theme

## Open

1. **Nav — DONE, and owned elsewhere. Do not touch it.** Ocean built it: the
   homepage carries two fixed headers, `NavSiteNav` and
   `CustomSectionLightPhaseNavigation`, and `EviiveNavOverrides.tsx` crossfades
   between them. `EviiveSection.tsx` only *reports* state — it publishes
   `{active, theme, progress}` on `window.__eviiveNavTheme` and an
   `eviive-nav-theme` event, on transitions only, and touches no nav element.
   An earlier version also grabbed "the tallest fixed header" and set opacity on
   it; with two headers that could hide the light-phase nav at the very moment
   the override was revealing it. Removed. There was also a `FADE_NAV` flag that
   gated the publish loop as well as the fade, so turning it off silently killed
   the overrides' event stream. Also removed.

2. **Frame height: 200vh, and it must equal `.pin`.** Two states, travel
   `pinH - vh` = 100vh, state 2 at the last pinned pixel. There is deliberately
   NO dwell: the controller's exit gate holds the reader at EVIIVE until the
   transition lands, so a spare viewport of pinned scrolling would only mean the
   section sitting still while the page moved. Both mismatches were hit in one
   day — frame shorter than `.pin` overflows into Metrics, frame longer leaves a
   dead dark band.

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
