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
| section frame | `nFifHam5M` — **100vh** |
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
- The **approach** holds progress at 0 — the section rises as a plain dark band
  under ordinary scrolling and nothing animates. The reveal is a reward for
  arriving, not something the reader watches happen sideways. `index.html` still
  scrubs the approach when opened standalone; `__eviiveOwned` suppresses that in
  the embedded build
- One deliberate flick → 53.5 months, on **golden's own tween**:
  `bezierEasing(0.37, 0, 0.63, 1)` over `DUR` 2600ms. **Do not shorten it and do
  not re-curve it.** Golden documents why next to the constant: the move should
  feel like shifting something heavy, the curve was chosen off its measured
  speed profile, and its ease-in head reads as momentum at this length. Two
  agents replaced it (an exponential spring, then 900/1300ms) and every
  stiff/stuck/stutter complaint traced back to those. The odometer blur
  (0.84/0.16, 0.30, threshold 0.3) is tuned to this duration - golden's model at
  golden's length needs no compensation. `busy` covers only the page glide; the
  2.6s tween runs unlocked because `ours` swallows the gesture tail, `engaged`
  freezes the page, and a fresh flick retargets the tween mid-flight
  (`from = scroll.p`). The only wait is the at(1) exit gate leaving EVIIVE
- **No CSS scroll-snap at all.** It offers no control over duration or easing, so
  the module runs a discrete controller. The sequence: the section rises under
  ordinary scrolling with the scene held at `p = 0`; one flick glides it to fill
  the viewport and *then* plays the 6.4 reveal; one more flick goes to EVIIVE.
  `ARM_IN` 0.25, `RESCUE_IN` 0.75, `GESTURE_GAP` 140ms, `TOLERANCE` 24. One
  gate only, on the way out. A 6s watchdog releases if anything fails.

  **The entry glide is a critically damped spring seeded with the reader's own
  scroll velocity** (Ocean's pick from five options: "continue the hand").
  Closed form `x(t) = y + (d0 + (v0 + w·d0)t)e^(-wt)`, `OMEGA` 5/s (~1.2s
  settle), stiffness adapting up to `w = v0/|d0|` (cap 60) so a fast hand is
  absorbed by a stiffer catch instead of clamped - a clamp is a brake-slam,
  measured at 17,800px/s of discontinuity. Hand-off discontinuity is now 0.
  Velocity sampling attacks fast / releases smooth (symmetric EMAs lag a rising
  speed), ages out after 120ms of quiet, and the spring hard-lands at 0.5px
  because springs never arrive on their own. Integer pixels throughout.

  **Two capture triggers, and they are not the same.** `ARM_IN` is where a
  *deliberate* flick takes hold — one begun with the section already in view.
  `RESCUE_IN` is a backstop for a flick begun before the section existed on
  screen, which would otherwise carry three viewports past it. Collapsing them
  into one number breaks something either way: too low and the flick that
  reveals the section also swallows it, so the reader never gets the beat where
  they simply see it; too high and a hard throw sails by and the section never
  happens. Both failures were observed.

  **The odometer blur is duration-dependent.** It measures per-frame wheel
  displacement, so it scales inversely with the scene tween's length. Shortening
  DUR from 2600 to 900 tripled the blur and pinned it at its 9px ceiling — a
  smear that resolves only at the end, i.e. "the number stutters before it
  stays". At golden's 2600 the golden model is correct as written; the
  compensation added while DUR was short has been deleted with the short DUR.
  **If DUR ever changes, re-measure the blur against `golden/` first.**

  **A consumed gesture owns its tail** (`ours`). A flick's momentum outlasts the
  transition, and those leftovers used to reach the browser the instant `busy`
  cleared and scroll the page back out of the section — which read both as the
  section refusing to hold *and* as the reveal never playing.

  **Read the gesture, never the event.** One trackpad flick is 30–60 wheel
  events across ~1s — a finger burst plus an OS-synthesised momentum tail, and
  [there is no API to tell them apart](https://github.com/w3c/pointerevents/issues/553).
  Every cooldown short enough to feel responsive is shorter than that tail, so
  its leftovers fire a second step. A gesture therefore ends with SILENCE: an
  event opens a new one only after `GESTURE_GAP` of quiet, and the clock
  advances on swallowed events too. The decision is taken once, on a gesture's
  first event. Do not reintroduce a cooldown; it cannot work.

  **One writer for `p`.** The controller sets `window.__eviiveOwned` and the
  driver's `readScroll` bows out entirely. Two systems assigning one value on
  the same frame was the jitter — `scrollTo` dispatches its scroll event
  asynchronously, so the last one landed after the guard cleared
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

2. **Frame height: 100vh, and the section has NO pinned travel.** Both states
   live at one scroll position; a flick changes the scene and nothing else. It
   was 200vh, with sticky holding the composition still while the page moved a
   viewport underneath — which drifts, because a sticky element and a scripted
   `scrollTo` do not round to the same pixel on the same frame. Ocean's rule:
   *"scroll up from eviive to scene 1 and scroll down from scene 1 to eviive
   should only activate one thing: the scene change. the view should never
   change."* Measured view movement is now 0px in both directions.

   Removing the travel also removed the slack that hid two bugs, so do not
   reintroduce it casually: sub-tolerance wheel events used to leak to the page,
   and eight pixels was enough to flip the section from `inside` to `leaving`,
   after which every downward flick read as a request to exit. Nothing reaches
   the page now while `engaged` is set, and a release stays final (`spent`)
   until the section has genuinely left the viewport.

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
