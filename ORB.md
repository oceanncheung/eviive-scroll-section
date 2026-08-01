# The EVIIVE orb — how dot 2 is made

One sphere carries both bodies. There is no second object and no cross-fade:
a single shading model whose **parameters** travel from the dead cohort to
EVIIVE, driven by `uMorph` (0 → 1).

Source: `src/main.jsx`, `ORB_HEAD` + `FRAG_MORPH`.

---

## Provenance

The look was not designed in one pass. Roughly forty variants were rejected
before A01 was chosen:

1. **30 material studies** on a draft page, each a different technique
   (transmission, hand-shaded, fresnel-layered, sub-surface).
   Shortlisted **19** and **25** — "light trim good, middle too dark".
2. **20 studies for dot 1** on navy — "greyer, matte, duller, deader".
   Chose **B20**, "ghost, no core".
3. **10 refinements** from 19/25 → rejected, drifted too far.
4. Restart from **1, 2, 5** → then 02/07/09/11 → refined to 5 → **A01 chosen.**

A01's identity is the tilting vertical gradient plus the narrow dark band. It
survived because it reads as lit and organic without a hard rim. **Do not
redesign it casually** — two later attempts to "improve" the material were
reverted on sight.

---

## Palette

```glsl
const vec3 CORE = vec3(0.62,0.875,0.965);   // light blue, NOT white
const vec3 MIDB = vec3(0.42,0.865,0.985);
const vec3 EDGE = vec3(0.09,0.42,0.60);
```

`CORE` was originally `(0.80,0.955,1.00)` — effectively white, and read as a
blowout. It is deliberately a blue now.

Each is the destination of a travelling pair; the dead cohort's greys are the
origins:

| | dead (m=0) | EVIIVE (m=1) |
|---|---|---|
| `pDeep` | `0.22,0.26,0.30` | `EDGE` |
| `pMid` | `0.30,0.36,0.41` | `MIDB` |
| `pLight` | `0.86,0.91,0.94` | `CORE` |

---

## The shading model, layer by layer

Every glass term is multiplied by `m`, so at m=0 they vanish entirely and the
body is unlit grey. Nothing is blended against a second material.

**1. Light response opens.** Dead matter has no directional term at all — only
fresnel, which is exactly what makes something look unlit. As `m` rises a
gradient axis appears and starts to tilt:

```glsl
float tilt = sin(uT * 0.115) * 0.55 * m;
float roll = cos(uT * 0.083) * 0.10 * m;
float g = smoothstep(-0.85 + roll, 0.75 + roll, N.y + N.x * tilt);
g = mix(fres(2.0), g, m);          // fresnel -> directional
```

The axis drifts on two detuned periods so the form is continually *relit*
rather than statically shaded. A fixed axis is why earlier versions read as a
still image no matter how much the surface moved underneath.

**2. Absorption toward the silhouette.** `thick = pow(ndv(), 0.70)` is how much
material lies along the view ray. Colour deepens where there is less of it.

**3. Inner shell — the term that makes it a volume.** A second surface, lit by
the same key and attenuated by thickness, seen *through* the first:

```glsl
vec3  Ni = normalize(N + L * 0.44 + vec3(0.0, -0.15, 0.0));
float shell = smoothstep(0.05, 0.95, dot(Ni, L)) * thick;
```

This is the single most important term for reading as glass. A body with one
boundary is a skin; two boundaries is a volume.

**4. The dark band.** A narrow ring near the silhouette, drifting:
`band(0.13 ± 0.035, +0.29) * 0.85 * m`. Part of A01's identity. It is specified
against `ndv()`, not screen radius — an earlier version used `1 - dot(N,V)` and
was invisible, because that only exceeds 0.42 in the outer 17% of the disc.

**5. Nucleus.** A soft core suspended inside, drifting on two detuned periods:

```glsl
float k = 1.0 - smoothstep(0.02, 0.62, d);
return k * k * k;                  // cubed: soft, no visible edge
```

Applied at `mix(base, pDeep * 0.72, nuc * 0.62)`. The cubing keeps the edge
soft; the **strength** is what makes it a core rather than a smudge. Both
extremes have been rejected: a squared falloff at 0.78 read as a dirty stain,
and `0.55 x 0.34` reached only 19% toward the deep tone — invisible.

**6. Specular pair.** A broad frosted scatter lobe under a small tight
highlight, from a real half-vector — only a curved surface produces that
pairing:

```glsl
pow(dot(N,Hv),  5.0) * 0.14 * thick * m      // frosted scatter
pow(dot(N,Hv), 44.0) * 0.20 * m              // glassy point
```

**7. Rim trim.** `fres(3.0) * (1.25 + sin(uT*0.137)*0.16) * m`.
**Sensitive.** A stronger trim has been rejected twice. Leave it.

**8. Alpha profile travels too** — a thin shell opening into a glass body:

```glsl
float aThin  = mix(0.14, 0.60, fres(1.7));              // dead: see-through
float aGlass = min(1.0, mix(1.0, 0.50, g) + fres(2.2) * 0.60);
```

Note `aGlass` rides `g`, **not** the fresnel. The white region is the top of the
lighting gradient, not the centre of the disc — hanging transparency off the
fresnel thins the wrong area entirely, which is why "the white still looks
filled" survived several attempts.

---

## Surface motion

Displacement is noise plus two detuned sine lobes, in `ORB_VERT`. Amplitudes
move only slightly across the morph (`wob 0.100 → 0.085`, `organic 0.095 →
0.105`) — the dead cohort deforms as much as EVIIVE does, it simply has no
colour. Peak radial deviation stays flat at **~17%** the whole way.

**No mid-morph surge.** An earlier version multiplied amplitude by
`1 + 1.15*sin(pi*m)` over a noise field tightened 55%, to make the change an
"event". It read as bacterial wrinkles. Removed.

**Normals are reconstructed by tangent finite differences** of the same field.
The earlier `normalize(normal + k * normalize(position))` is parallel to
`position` for any k > -1 — a no-op. The surface displaced and the shading never
followed, which silently defeated several rounds of work.

**Noise interpolation is quintic**, not smoothstep — cubic leaves the second
derivative discontinuous at every lattice boundary, which creases a
reconstructed normal.

**Pointer influence.** The cursor offsets the noise domain and phase-shifts the
lobes, smoothed at ~0.5s. It leans on the field rather than steering it.

---

## Tuning dials

| want | change |
|---|---|
| nucleus more/less visible | `nuc * 0.62` in `FRAG_MORPH` |
| rim trim strength | `1.25` in `trim` — **rejected twice when raised** |
| white less filled | `mix(1.0, 0.50, g)` in `aGlass` |
| more/less surface motion | `uWobAmp` / `uOrganic` in `Orb`'s `useFrame` |
| glass terms arrive sooner | `smoothstep(0.10, 0.82, t)` in `orbAt` |
