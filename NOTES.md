# Non-obvious decisions

Everything here looks wrong until you know why. Each cost real debugging time.

## Rail geometry

**The rail box is 96/96 while the type is 48/96.** Three things must hold at
once: month zero flush at the top, the head on the orb's centre line, and a
flush foot. They can only all hold when `headY / H` is a clean fraction. Framer's
48/96 section padding gives `402/756 = 0.5317` and no whole number of ticks ever
reaches the foot. At 96/96 it is exactly `0.5`.

**`pxPerMonth = headY / months`, divided exactly.** Month zero lands on `y = 0`
only with `months` itself as the divisor. A "soft floor" of
`sqrt(months² + 1.6²)` pushes it to y=12 and leaves 153px hanging at the foot.
The old `Math.max(months, 1.6)` clamp was worse — month zero slid up and then
stopped dead the moment months crossed 1.6, which reads as a hard landing.

**Rail months are rounded: 0 → 6 → 54.** The ticker keeps the real 6.4 / 53.5.
Rounding puts both marks exactly on the 3-month grid, so each mark IS a tick
rather than a second rule floating beside the rail.

**Fixed 3-month step, deliberately.** A sparse rail at 6 months and a dense one
at 53 is the whole point. Holding the pitch constant (adaptive step) makes both
scenes read as the same object and throws the comparison away.

**Scale interpolates geometrically**, `exp(lerp(log 6, log 54, t))`. Spacing is
`span/months`, a 1/x curve, so stepping the month count linearly compresses
violently at the start and barely at the end. No easing can fix that — the
unevenness is in the mapping, not the timing.

**Ticks are transform-only** (`translate3d` + `scaleX`), never `top`/`width`.
Writing layout properties on 80 elements per frame dirties layout inside a
`scroll-snap: mandatory` container; Chrome then re-evaluates snapping every
frame and the page emits scroll events and drifts with no user input.

**`contain: layout style` on `.rail` — never `paint`.** Paint containment clips
descendants to the 120px box and erases the leader labels entirely.

**No opacity fade inside the frame.** Both terminal ticks sit exactly on the
boundary, so any edge ramp erases them. The fade lives entirely in 12px of
overscan outside.

**Mark and grid tick crossfade.** Suppressing the tick while the mark is live
makes the line blink out and return in the other colour when the mark fades.
Opacities are complementary instead.

## Headline

**Values read off eviive.ch itself**, not approximated — 105 identical instances:
`blur(10px)→0`, `translateY(10px)→0`, `opacity 0→1`, duration `0.85s`,
ease `cubic-bezier(0.44, 0, 0.56, 1)`, stagger `0.1s`.

**Time-based, not scroll-scrubbed.** Framer runs a text effect on its own clock;
scroll only decides *whether* a group is in. Mapping words onto scroll progress
makes their speed the derivative of the scroll tween, which already has its own
easing — the two compound and read as stutter.

**One direction rule, not per-line constants:**

| | scroll down | scroll up |
|---|---|---|
| entering | first word first, from below | last word first, from below |
| leaving | first word first, **up** | last word first, **up** |

Encoding this as `exitY` on one line and `enterReverse` on another is what made
every fix break a neighbouring case — each line only ever had two of the four
combinations written down.

**`armAt` must be `=== 0.5`, not `>= 0.5`.** `>=` is also true at scene 3, so
arming never switches off on the way out and never switches back on coming home;
the code that flags a return as a return never runs.

**`g.x` must be snapped to 0 on arrival.** Otherwise the exit progress is still
1 and decays over ~470ms, so the code stays in the leaving branch and plays the
exit backwards instead of running the entry.

**Read `wasOut` before anything clears `g.x`.** Presence and arming flip on the
same frame when returning, so the presence reset wipes the evidence the arm test
needs.

## Scene / camera

**One material whose parameters travel — not two cross-dissolved.**
`mix(deadLook, eviiveLook, m)` is a fade by construction: at m=0.5 you are
looking at two complete shadings averaged together. Palette, light response and
glass terms all interpolate within a single model instead.

**Depth of field writes go through `dof.cocMaterial`,** not the effect.
`DepthOfFieldEffect` has no `worldFocusDistance` accessor — writing to the
effect mints dead properties and focus silently stays at its constructor value.
This made the entire mid-journey render permanently out of focus at bokeh 5.5,
which invisibly defeated several rounds of deformation work.

**Vertex normals are reconstructed by tangent finite differences.** The previous
`normalize(normal + k * normalize(position))` is parallel to `position` for any
k > -1 — i.e. a no-op. The surface displaced but the shading never followed.

**No displacement "surge" mid-morph.** Doubling amplitude over a tightened noise
field reads as bacterial wrinkles, not metamorphosis. Peak radial deviation is
held flat at ~17% across the whole journey.

**Apparent size is solved for, not set.** `r = distance * angularSize`, because
the orb's z leads the camera and the distance swells to 10.2 mid-move; easing
the radius directly makes on-screen size dip for the first quarter.

**Scroll easing `cubic-bezier(0.37, 0, 0.63, 1)` at 2600ms**, chosen by measuring
the *speed* profile rather than the position curve. Weight is sustained travel:
peak/mean 1.59x, near full speed for 65% of the move, still visibly travelling
at 85%. Front-loaded curves spike to 3x their own average, then die.

## Testing traps

**`scroll-snap-stop: always` forbids skipping a snap point.** `scrollTo(0,1800)`
from 0 is silently yanked back to 900 by Chrome. Always step one snap point at a
time (0 -> 900 -> 1800) and allow ~5s to settle — the browser's own snap
animation delays when the tween even *starts*.

**`__eviive.seek(p)` is overridden by any real scroll event.** Do not trust it
while the page can scroll.

**`style.transform` normalises to `translate3d(0px, ...)`.** A regex expecting
`translate3d(0,` matches nothing and silently reports every offset as 0.


## Responsive (added v1.2)

**Layout is chosen by ASPECT RATIO, type by width.** Two different questions.
The desktop composition needs horizontal room BESIDE the orb — rail down the
right, label in the gap — so what decides it is the shape of the frame, not its
width. `stacked` when `width/height < 1.15 || width < 900`.

- 1.15 rather than 1.0: a barely-landscape frame still has no usable gap.
- The 900 floor keeps a landscape PHONE (844x390) stacked — very wide ratio,
  far too short for a vertical rail with padding at both ends.
- Type stays on Framer's own width breakpoints (809 / 1199), because that is
  what Framer does. A landscape iPad gets desktop layout with tablet type.

**ONE source of truth for the mode.** `alignUnit` publishes `scroll.stacked`;
the scene reads it. It used to run its own `innerWidth <= 1199` test, which
disagreed the moment the rule became ratio-based — the DOM laid out for desktop
while the orb still believed it was stacked, and every fix appeared to do
nothing. Never recompute the mode anywhere else.

**The orb is FITTED to measured space, never to a fraction.** Position and size
both come from the gap the DOM actually leaves. Fixed fractions were chosen
independently of where the rail lands, so nothing guaranteed they would not
collide — and on a 390x844 phone they overlapped by 50px.

**Desktop re-centres ONLY on a collision.** Screen-centred is the default;
the gap is used to rescue a frame that cannot hold the orb. Recentring
unconditionally moved it 121px right on a 1512 desktop and changed an approved
composition. On desktop the fit is also capped at 1 so it can only SHRINK —
the natural size carries the true 8.36x ratio against dot 1.

**Stacked-layout constants move together.** Three of them, or the guarantees
break:
- `MARK_MIN_H` must exceed `RAIL_W_H + RAIL_BUMP_H`, or the mark stops being
  the tallest thing on the rail and no longer reads as the anchor.
- `RESERVE` must track `MARK_MIN_H + MARK_SPAN_H + MARK_GAP_H` minus the rail's
  own height. It is measured from the rail's TOP, not its foot — getting that
  wrong reserved 67px that nothing occupied and pushed the orb into the title.
- The orb's diameter is capped by the COLUMN as well as the band, or it runs
  past the gutters once the band grows.

**`railGeom` is self-healing.** Everything `setRail` needs is measured in
`alignUnit`; if that has not run since the viewport changed, the rail runs on a
stale width of 1 and collapses to a single tick. `frame()` compares the current
viewport against the last measured one and re-measures at most once per change.

**Clear inline placement between breakpoints.** `alignUnit` wipes the inline
`bottom`/`right`/`text-align` it sets before applying whichever layout is
current — otherwise resizing tablet to desktop carries the stacked layout's
positioning across and corrupts the composition.

## Two bugs of the same shape, both silent

**Declare before use.** `narrow` was read on the orb's position line but
declared further down the same scope — a temporal dead zone throwing every
frame, so the orb rendered dead centre with no fitting. Earlier, `const spin`
in the odometer shadowed an existing binding and killed the DOM frame loop
outright. Neither surfaced as a visible error; both just stopped a loop.

**A failed assertion discards the whole edit.** The scripts used to build this
write only at the end, so one bad pattern silently reverted every change in the
batch while the build still reported success. Confirm each edit applied.
