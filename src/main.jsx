import React, { useRef, useLayoutEffect, useMemo } from "react"
import { createRoot } from "react-dom/client"
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { EffectComposer, DepthOfField, Bloom, Noise, Vignette } from "@react-three/postprocessing"
import { BlendFunction } from "postprocessing"
import * as THREE from "three"

/* ============================================================================
   ONE WORLD UNIT = ONE MONTH.

   The unaligned cohort sits at month 6.4, EVIIVE's at month 53.5 — so the
   scene geometry IS the data, at the true 8.36x ratio with nothing compressed.
   Both bodies sit dead on the camera axis: you see the far one THROUGH the
   near one, because the near one is glass. That is the whole storytelling
   device, and it is only possible with real transmission.
   ========================================================================== */
const Z_A = -6.4
const Z_B = -53.5
const FRAME_D = 6.4                       // framing distance — B ends framed as A began
const CAM_END = Z_B + FRAME_D             // -47.1

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v)
const lerp = (a, b, t) => a + (b - a) * t
const smoothstep = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t) }

// Driven by the DOM scroll driver in index.html. Already eased there, so this
// is the final camera parameter — no second easing on top.
const scroll = (window.__eviiveScroll = window.__eviiveScroll || { p: 0 })

/* ---------------------------------------------------------------------------
   Backdrop. Not decoration — the glass needs something to refract. A flat
   clear colour gives transmission nothing to bend, which is exactly why the
   hand-written shader looked dull no matter how it was tuned.
   -------------------------------------------------------------------------*/
function Backdrop() {
  const mesh = useRef()
  const mat = useRef()
  const uniforms = useMemo(() => ({ uLift: { value: 0 }, uT: { value: 0 } }), [])

  useFrame(({ camera, clock }) => {
    if (mesh.current) mesh.current.position.copy(camera.position)
    // set through the ref: R3F may not preserve the identity of a uniforms prop
    const u = mat.current && mat.current.uniforms
    if (!u) return
    u.uLift.value = smoothstep(0.58, 0.96, scroll.p)
    u.uT.value = clock.elapsedTime
  })

  return (
    <mesh ref={mesh} scale={140} renderOrder={-1}>
      <sphereGeometry args={[1, 48, 32]} />
      <shaderMaterial
        ref={mat}
        side={THREE.BackSide}
        depthWrite={false}
        uniforms={uniforms}
        vertexShader={`
          varying vec3 vP;
          void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }
        `}
        fragmentShader={`
          precision highp float;
          varying vec3 vP;
          uniform float uLift;
          uniform float uT;
          float hash(vec2 p){
            p = fract(p * vec2(443.897, 441.423));
            p += dot(p, p + 19.19);
            return fract((p.x + p.y) * p.x);
          }

          /* R3F outputs sRGB, so raw values written here are treated as LINEAR
             and then encoded — which is why #022C3B authored directly came out
             grey and washed. Author in sRGB and convert. */
          vec3 s2l(vec3 c){
            return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
          }
          void main(){
            vec3 d = normalize(vP);
            /* Curved STRUCTURE, not noise. An fbm warp modulated the gradient
               at high frequency, which is what read as dirt — grain scattered
               over a clean field. This warps the domain with a handful of slow,
               detuned harmonics instead, so the gradient's isolines bend into
               broad ribbons and drift. Everything stays smooth by construction:
               there is no frequency here small enough to see as texture. */
            vec2 q = d.xy;
            float t1 = uT * 0.047, t2 = uT * 0.034;
            vec2 flow = vec2(
              sin(q.y * 1.70 + t1) + 0.50 * sin(q.y * 3.05 - t2 * 1.7),
              cos(q.x * 1.45 - t2) + 0.50 * cos(q.x * 2.60 + t1 * 1.3)
            ) * 0.185;
            vec2 ctr = vec2(sin(uT * 0.039) * 0.17, cos(uT * 0.029) * 0.13);
            float rad = clamp(length(q + flow - ctr) * 1.12, 0.0, 1.0);

            vec3 navy     = s2l(vec3(0.008, 0.173, 0.231));  // #022C3B exactly
            vec3 navyDeep = s2l(vec3(0.004, 0.110, 0.153));   // deepest at the centre
            vec3 dark = mix(navy, navyDeep, smoothstep(0.15, 1.0, rad));

            /* Back the right way round: a lightbox is BRIGHTEST at the centre
               and cools toward the edges. Swapping it put the weight in the
               wrong place — an x-ray plate is lit from behind the middle. */
            vec3 liteC = s2l(vec3(0.980, 0.995, 1.000));      // near-white core
            vec3 liteE = s2l(vec3(0.741, 0.869, 0.929));      // cooler, deeper out
            vec3 lite = mix(liteC, liteE, smoothstep(0.10, 1.0, rad));

            vec3 c = mix(dark, lite, uLift);
            c += (hash(gl_FragCoord.xy) - 0.5) * (1.5/255.0);   // dither kills banding
            gl_FragColor = vec4(c, 1.0);
          }
        `}
      />
    </mesh>
  )
}

/* ---------------------------------------------------------------------------
   The two bodies, as chosen from the studies.

   Dot 1  = B20 "ghost, no core" — flat shaded, dark centre, light rim, no
            lighting model at all. The deadest a form can look, which is
            exactly the point: these patients got 6.4 months.
   EVIIVE = A01 "vertical" — electric low, light blue lifting upward, a narrow
            deeper band at the sides, and a soft light trim.

   Both are ShaderMaterials, so the scene no longer needs the transmission
   render passes or the studio environment that fed them.
   -------------------------------------------------------------------------*/
const ORB_VERT = `
  varying vec3 vN; varying vec3 vV; varying vec3 vP;
  uniform float uT; uniform float uWobAmp; uniform float uOrganic; uniform float uChurn; uniform vec2 uPtr;
  float h31(vec3 p){ p=fract(p*0.3183099+vec3(.11,.17,.13)); p*=17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
  // quintic, not cubic: smoothstep leaves the SECOND derivative discontinuous
  // at every lattice boundary, which creases the reconstructed normal
  float n3(vec3 x){ vec3 i=floor(x),f=fract(x); f=f*f*f*(f*(f*6.0-15.0)+10.0);
    return mix(mix(mix(h31(i),h31(i+vec3(1,0,0)),f.x),mix(h31(i+vec3(0,1,0)),h31(i+vec3(1,1,0)),f.x),f.y),
               mix(mix(h31(i+vec3(0,0,1)),h31(i+vec3(1,0,1)),f.x),mix(h31(i+vec3(0,1,1)),h31(i+vec3(1,1,1)),f.x),f.y),f.z);}
  /* Displacement as a function of a point on the unit sphere. Written once so
     the normal can be reconstructed from the SAME field — the old version
     sampled a second field at a different time phase and called the difference
     a gradient, which is not a gradient at all, just two drifting noises
     subtracted. Amplified into the normal, that is what flickered. */
  float dispAt(vec3 pn){
    // Frequency, never time-speed — a modulated time coefficient multiplies
    // an unbounded uT and the surface would leap once the page has been open.
    float nz = n3(pn * 1.35 + vec3(uPtr * 0.34, uT * 0.19)) - 0.5;
    float lobes = sin(pn.y * 1.7 + uT * 0.72 + uPtr.y * 0.85)
                + sin(pn.x * 1.3 - uT * 0.55 + uPtr.x * 0.85);
    return nz * 1.6 * uOrganic + lobes * 0.5 * uWobAmp;
  }
  void main(){
    vP = position;
    /* Organic, not mechanical: a slow-drifting noise field displaces the
       surface, with two detuned sine lobes underneath so the silhouette keeps
       moving even where the noise is locally flat. The pointer leans on the
       field rather than steering it — it offsets the noise domain and phase-
       shifts the lobes, and arrives already smoothed, so nothing snaps. */
    vec3 pn = normalize(position);
    float d0 = dispAt(pn);
    vec3 pos = pn * (1.0 + d0);

    /* A true normal: two finite differences of the displaced surface along an
       orthonormal tangent frame, crossed. Continuous by construction, so the
       shading can no longer sparkle however hard the surface is pushed. */
    vec3 up = abs(pn.y) < 0.99 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
    vec3 t1 = normalize(cross(up, pn));
    vec3 t2 = cross(pn, t1);
    const float E = 0.045;
    vec3 pa = normalize(pn + t1 * E), pb = normalize(pn + t2 * E);
    vec3 va = pa * (1.0 + dispAt(pa)) - pos;
    vec3 vb = pb * (1.0 + dispAt(pb)) - pos;
    vec3 bumped = normalize(cross(va, vb));
    bumped *= sign(dot(bumped, pn));

    vN = normalize(normalMatrix * bumped);
    vec4 mv = modelViewMatrix * vec4(pos, 1.0);
    vV = -mv.xyz;
    gl_Position = projectionMatrix * mv;
  }`

const ORB_HEAD = `
  precision highp float;
  varying vec3 vN; varying vec3 vV; varying vec3 vP;
  uniform float uT; uniform float uAlpha; uniform vec2 uPtr;
  float ndv(){ return clamp(dot(normalize(vN), normalize(vV)), 0.0, 1.0); }
  float fres(float k){ return pow(clamp(1.0 - ndv(), 0.0, 1.0), k); }
  float band(float inner, float outer){
    float d = ndv();
    return smoothstep(outer, inner, d) * smoothstep(0.0, 0.10, d);
  }
  /* A cell has something inside it. The sphere's view-space normal doubles as
     a coordinate on its own disc, so a soft blob placed there reads as an
     organelle suspended in the body rather than a mark painted on the front.
     It drifts on two detuned periods so it never settles. */
  float nucleus(){
    vec3 nn = normalize(vN);
    vec2 off = vec2(sin(uT * 0.13) * 0.12, cos(uT * 0.105) * 0.09);
    float d = length(nn.xy - off);
    float k = 1.0 - smoothstep(0.02, 0.62, d);
    return k * k * k;                  // cubed: a soft core with no visible edge
  }
  const vec3 CORE = vec3(0.62,0.875,0.965);   // light blue, not a white blowout
  const vec3 MIDB = vec3(0.42,0.865,0.985);
  const vec3 EDGE = vec3(0.09,0.42,0.60);
`

const FRAG_MORPH = ORB_HEAD + `
  uniform float uMorph;

  /* ONE material whose PARAMETERS travel — not two materials cross-dissolved.
     mix(deadLook, eviiveLook, m) is a fade by construction: at m=0.5 you are
     looking at two complete shadings of the same body averaged together, which
     is exactly what a dissolve is, and no amount of tuning either side can make
     that read as a transformation. Here there is a single shading model
     throughout. Its palette travels from dead grey to EVIIVE blue, its light
     response opens from flat fresnel to a tilting directional gradient, and its
     glass terms — inner shell, specular pair, band, trim — come up from zero.
     Every pixel is always ONE surface, described by parameters in motion. */
  void main(){
    float m = uMorph;
    vec3  N = normalize(vN), V = normalize(vV);
    /* The key light tracks the BACKGROUND's own drift. These are the same two
       expressions the backdrop uses to wander its gradient centre, so the arc
       of the rim that brightens is always the arc facing the brightest part of
       the field. Before, the light drifted on its own unrelated period and the
       body and its ground looked like two separate things. */
    vec2  bgCtr = vec2(sin(uT * 0.039) * 0.17, cos(uT * 0.029) * 0.13);
    vec3  L = normalize(vec3(bgCtr.x * 3.6 - 0.22, bgCtr.y * 3.6 + 0.76, 0.52));
    float thick = pow(ndv(), 0.70);
    float nuc = nucleus();
    /* Where this point sits relative to the light, 0 (facing away) to 1
       (facing it). At the silhouette N lies in the screen plane, so this
       sweeps smoothly around the whole circumference with no seam. */
    float rimA = dot(N, L) * 0.5 + 0.5;
    float rimW = smoothstep(0.02, 0.98, rimA);


    // the palette itself moves; nothing is blended against anything else
    vec3 pDeep  = mix(vec3(0.22,0.26,0.30), EDGE, m);
    vec3 pMid   = mix(vec3(0.30,0.36,0.41), MIDB, m);
    vec3 pLight = mix(vec3(0.86,0.91,0.94), CORE, m);

    /* The light response OPENS. Dead, it has no directional term at all — only
       fresnel, which is what makes a body look unlit. As m rises the gradient
       axis appears and begins to tilt. */
    float tilt = sin(uT * 0.115) * 0.55 * m;
    float roll = cos(uT * 0.083) * 0.10 * m;
    float g = smoothstep(-0.85 + roll, 0.75 + roll, N.y + N.x * tilt);
    g = mix(fres(2.0), g, m);

    vec3 base = mix(pMid, pLight, g);
    base = mix(base, mix(pMid, pDeep, 0.55), (1.0 - thick) * mix(0.06, 0.22, m));

    vec3  Ni = normalize(N + L * 0.44 + vec3(0.0, -0.15, 0.0));
    float shell = smoothstep(0.05, 0.95, dot(Ni, L)) * thick;
    base = mix(base, pLight, shell * 0.30 * m);

    /* THIS is the continuous unvarying trim. It is a ring at a fixed ndv
       range, so it had the same weight at every point of the circumference —
       the thing that stopped it reading as refracted light. Widened for a
       gentler gradient into the fill, weakened, and now modulated by the light
       so it nearly disappears on the lit arc and carries the whole dark side.
       Adding a SECOND darkening term on top of this was why every attempt came
       out "too thin, too strong": two edges stacked at the same silhouette. */
    float bandDrift = 0.10 + sin(uT * 0.094) * 0.035;
    base = mix(base, pDeep,
               band(bandDrift, bandDrift + 0.52) * 0.62 * m * mix(0.22, 1.0, 1.0 - rimW));
    // a density INSIDE the body, not a mark on the front of it
    /* The inner core, readable again. Softened to kill a hard-edged stain I
       took it far too far — at 0.55x0.34 it could reach only 19% toward the
       deep tone, which is invisible. The cubed falloff keeps the edge soft;
       the strength is what makes it a core rather than a smudge. */
    base = mix(base, pDeep * 0.72, nuc * 0.62);

    vec3  Hv = normalize(L + V);
    float trim = (1.25 + sin(uT * 0.137) * 0.16) * m;

    /* The rim must not be ONE uniform ring. fres() is radially symmetric — it
       has no idea where the light is, so it returns the same value at every
       point on the circumference and the trim reads as a drawn outline rather
       than a refracted edge. Real glass gathers light on the side facing the
       source and accumulates material on the far side.
       At the silhouette N lies in the screen plane, so dot(N, L) sweeps
       smoothly from -1 to +1 around the circle — one continuous gradient from
       the bright arc to the dark one, no seam. And because L already drifts on
       sin(uT * 0.09), the bright arc travels slowly around the body. */
    vec3  c = base
            + vec3(0.80,0.95,1.00) * fres(3.0) * trim * mix(0.62, 1.0, rimW)
            + vec3(0.86,0.96,1.00) * pow(max(dot(N, Hv), 0.0),  5.0) * 0.14 * thick * m
            + vec3(1.00,1.00,1.00) * pow(max(dot(N, Hv), 0.0), 44.0) * 0.20 * m;


    // the alpha PROFILE travels too: a thin shell opening into a glass body
    float aThin  = mix(0.14, 0.60, fres(1.7));
    float aGlass = min(1.0, mix(1.0, 0.50, g) + fres(2.2) * 0.60);
    float a = mix(aThin, aGlass, m) * (1.0 + nuc * mix(0.60, 0.32, m));
    gl_FragColor = vec4(c, min(a, 1.0) * uAlpha);
  }`

/* ---------------------------------------------------------------------------
   ONE body, not two. The grey cohort is not deleted and replaced — it is
   carried forward and transformed, so the hand-over has nothing left to pop,
   flash or gap. Position, size, surface motion and material all cross-fade on
   the same progress. The orb's z LEADS the camera through the middle of the
   move, so there is real travel rather than an object that merely inflates.
   -------------------------------------------------------------------------*/
const R_A = 0.26, R_B = 1.0
const ease = t => t * t * (3 - 2 * t)
/* Apparent size is radius/distance, and the lead term makes the distance swell
   to 10.2 mid-move. Easing the RADIUS across that gave a size curve that dips
   for the first quarter of the move before climbing — read as a bounce. So the
   radius is now solved from the apparent size we want rather than set directly:
   the on-screen size grows strictly monotonically while the body still travels
   through real space, which is what the depth of field and parallax need. */
const ANG_A = R_A / 6.4, ANG_B = R_B / 6.4
const CAM_BACK = 14.0          // module scope: camZOf and Rig both need it
const camZOf = p => (p <= 0.5 ? lerp(CAM_BACK, 0, p / 0.5) : lerp(0, CAM_END, (p - 0.5) / 0.5))
function orbAt(p) {
  if (p <= 0.5) return { z: Z_A, r: R_A, m: 0 }
  const t = clamp((p - 0.5) / 0.5, 0, 1)
  const lead = t + 0.08 * Math.sin(Math.PI * t)
  const z = lerp(Z_A, Z_B, lead)
  const dist = Math.abs(lerp(0, CAM_END, t) - z)
  return {
    z,
    r: dist * lerp(ANG_A, ANG_B, ease(t)),
    m: smoothstep(0.10, 0.82, t),
  }
}

function Orb() {
  const mesh = useRef()
  const mat = useRef()
  const uni = useMemo(() => ({
    uT: { value: 0 }, uAlpha: { value: 1 }, uMorph: { value: 0 },
    uWobAmp: { value: 0.012 }, uOrganic: { value: 0.016 }, uChurn: { value: 0 },
    uPtr: { value: new THREE.Vector2() },
  }), [])
  const ptr = useRef({ x: 0, y: 0 })

  useFrame(({ clock }) => {
    // Write through the material ref, NOT the memoised object: R3F does not
    // preserve the identity of a `uniforms` prop, so writes to the original
    // land on an orphan and never reach the GPU.
    const u = mat.current && mat.current.uniforms
    if (!u || !mesh.current) return
    const o = orbAt(scroll.p)
    // ~0.5s time constant: the body trails the cursor instead of tracking it
    ptr.current.x += ((scroll.mx || 0) - ptr.current.x) * 0.035
    ptr.current.y += ((scroll.my || 0) - ptr.current.y) * 0.035
    u.uPtr.value.set(ptr.current.x, ptr.current.y)
    u.uT.value = clock.elapsedTime
    u.uMorph.value   = o.m
    /* No surge, no churn. The mid-morph "event" turned the sphere bacterial —
       doubled displacement over a tightened noise field reads as wrinkles, not
       metamorphosis. The journey is a plain blend of the two approved looks:
       the silhouette stays a circle the whole way, and the transformation is
       carried by the material, the light response and the travel itself. */
    u.uWobAmp.value  = lerp(0.100, 0.085, o.m)
    u.uOrganic.value = lerp(0.095, 0.105, o.m)
    u.uChurn.value   = 0.0
    mesh.current.position.z = o.z

    /* DECLARE BEFORE USE. `narrow` was read on the position line but declared
       further down the same scope — a temporal dead zone that threw on every
       frame, which is why the orb kept rendering dead centre with none of the
       fitting applied. */
    const narrow = !!scroll.stacked      // set by alignUnit; never recomputed here
    const HALF_TAN = Math.tan(38 * Math.PI / 360)      // half-angle of the field
    const fpxV = (innerHeight / 2) / HALF_TAN
    const dist = Math.abs(camZOf(scroll.p) - o.z)

    /* Both the position and the size come from the gap the DOM actually
       leaves between the headline and the rail's furniture, measured in
       alignUnit. Fixed fractions were chosen independently of where the rail
       lands, so nothing ever guaranteed they clear it. */
    /* Desktop used to hard-code dead centre. With a fixed nav overhead the
       usable stage is the viewport MINUS the nav, and the orb has to sit in the
       middle of that, not of the screen. It matters beyond looks: the rail is
       flush at both ends only when headY / H is exactly 0.5, and that fraction
       holds only if the rail's midpoint and the orb's centre are the same line.
       Leaving the orb at vh/2 while the rail started below the nav is what
       stopped the timeline reaching top and bottom. */
    const ORB_Y = scroll.orbY || (narrow ? 0.355 : 0.5)
    const lift  = (0.5 - ORB_Y) * 2 * HALF_TAN
    mesh.current.position.y = lift * dist
    /* Horizontal placement, same principle: the body sits in the middle of the
       room it has, not the middle of the screen. Half-width at a given depth
       is dist * tan(halfFov) * aspect. */
    const ORB_X = scroll.orbX || 0.5
    mesh.current.position.x = narrow ? 0
      : (ORB_X - 0.5) * 2 * HALF_TAN * (innerWidth / innerHeight) * dist

    /* Surface noise alone is invisible on a body this small on screen — the
       breath has to be in the silhouette. Slow and shallow while it is the
       dead cohort, tighter once it becomes EVIIVE. */
    const breath = 1 + Math.sin(clock.elapsedTime * 0.62) * lerp(0.062, 0.024, o.m)
    /* Stacked: fitted outright to the measured band. Desktop: fitted the same
       way but capped at 1, so it can only ever SHRINK to clear the type — the
       natural size is what carries the true 8.36x ratio against dot 1. */
    const fitted = scroll.orbDia ? (scroll.orbDia * 6.4) / (2 * fpxV) : null
    const fit = narrow
      ? (fitted !== null ? fitted : 0.52)
      : (fitted !== null ? Math.min(fitted, 1) : 1)
    /* Dot 1 ARRIVES, it does not appear. The section holds at p = 0 through
       the whole approach, so that state is genuinely on screen - and a scale
       gate there made the body pop from nothing to full in a single frame the
       moment the reveal began. Instead it fades in over the first stretch of
       the leg, during which the focus pull above still has the plane sitting
       well in front of the body: it enters as a soft unresolved presence and
       sharpens as the camera closes, which is the arrival the scene was
       designed around (see "0.0 arrival - dot 1 soft" in the Rig). At p = 0
       the alpha is zero, so the empty-field dead-pixel state cannot exist. */
    u.uAlpha.value = smoothstep(0, 0.12, scroll.p)
    mesh.current.scale.setScalar(o.r * breath * fit)
  })

  return (
    <mesh ref={mesh} position={[0, 0, Z_A]} scale={R_A}>
      <sphereGeometry args={[1, 112, 80]} />
      <shaderMaterial ref={mat} uniforms={uni} vertexShader={ORB_VERT} fragmentShader={FRAG_MORPH} transparent />
    </mesh>
  )
}

/* ---------------------------------------------------------------------------
   Camera + focus. A straight dolly down -Z; focus pulls from the near body to
   the far one. Depth of field is a post-process reading the real depth buffer,
   so blur is always consistent with geometry — the "orb changes size / turns
   into a different object" class of bug cannot happen here.
   -------------------------------------------------------------------------*/
function Fog() {
  const ref = useRef()
  const c = useMemo(() => new THREE.Color(), [])
  useFrame(() => {
    const lift = smoothstep(0.58, 0.96, scroll.p)
    c.setRGB(lerp(0.020, 0.930, lift), lerp(0.105, 0.960, lift), lerp(0.145, 0.962, lift))
    ref.current.color.copy(c)
  })
  return <fog ref={ref} attach="fog" args={["#0a2732", 14, 62]} />
}

function Probe() {
  const state = useThree()
  useFrame(() => { window.__three = state })
  return null
}

function Rig({ dof, vignette }) {
  const { camera } = useThree()
  useFrame(() => {
    const p = scroll.p

    /* Stacked layout: the orb sits ABOVE centre with the timeline beneath it,
       and it has to be smaller because the frame is narrow. A wider field of
       view shrinks the subject without touching the scene's month geometry —
       moving the camera back would corrupt the distances the whole section is
       built on. Camera y goes NEGATIVE to lift the subject in frame. */
    /* The camera does NOT shift vertically. A fixed camera offset projects to
       a screen offset of offset/distance, and the distance swells from 6.4 to
       10.2 through the middle of the move — so the orb visibly rose and fell
       as it travelled. The lift is applied to the ORB instead, proportional to
       its own distance, which cancels the division and holds it still. */
    camera.position.y = 0

    /* THREE states.
       0.0  arrival — camera held back, dot 1 soft, timeline not yet in
       0.5  dot 1 framed and sharp, ticker has run 0 -> 6.4
       1.0  dolly complete, EVIIVE framed, ticker 6.4 -> 53.5              */
    camera.position.z = p <= 0.5
      ? lerp(CAM_BACK, 0, p / 0.5)
      : lerp(0, CAM_END, (p - 0.5) / 0.5)
    camera.updateMatrixWorld()

    /* Focus is a PULL, not a slack range. At state 0 the plane sits well in
       front of the body, so it is present but unresolved; the first scroll
       brings the plane onto it. After that the plane simply rides the orb, so
       the transformation stays sharp all the way through. */
    const o = orbAt(p)
    const t1 = clamp(p / 0.5, 0, 1)
    const t2 = clamp((p - 0.5) / 0.5, 0, 1)
    /* Soft, not absent. At 5.2 out of a 1.5 range the body was blurred past
       the point of being legible on a dark ground — so it did not resolve, it
       APPEARED, and the leg read as a fade rather than a body coming into
       focus. Held closer and with a wider range, the silhouette is readable
       from the first frame and you can watch it deform as it sharpens. */
    const focusZ = p <= 0.5 ? o.z + lerp(2.8, 0, t1) : o.z
    if (dof.current) {
      /* Write through the CoC MATERIAL. DepthOfFieldEffect has no
         worldFocusDistance/worldFocusRange accessors — assigning them onto
         the effect just minted dead plain properties, so focus stayed parked
         at its constructor values (6.4/1.8) forever. Both endpoints happen to
         sit 6.4 from the camera, so the rest states looked perfect while the
         whole journey between them rendered as an out-of-focus smudge — the
         morph was never visible, which is why it kept reading as a fade. */
      const cm = dof.current.cocMaterial
      cm.worldFocusDistance = Math.max(Math.abs(camera.position.z - focusZ), 0.6)
      cm.worldFocusRange = p <= 0.5 ? lerp(2.4, 2.6, t1) : lerp(2.6, 3.6, t2)
    }
    if (vignette.current) {
      // barely there — a strong vignette was reading as the background's shape
      vignette.current.darkness = lerp(0.30, 0.26, smoothstep(0.58, 0.96, p))
    }
  })
  return null
}

function Scene() {
  const dof = useRef()
  const vignette = useRef()
  return (
    <>
      <Fog />
      <Probe />
      <Rig dof={dof} vignette={vignette} />
      <Backdrop />

      <Orb />

      <EffectComposer disableNormalPass multisampling={0}>
        <DepthOfField ref={dof} worldFocusDistance={6.4} worldFocusRange={1.8} bokehScale={5.5} height={640} />
        <Bloom mipmapBlur luminanceThreshold={0.95} luminanceSmoothing={0.3} intensity={0.55} />
        <Noise opacity={0.075} blendFunction={BlendFunction.OVERLAY} />
        <Vignette ref={vignette} eskil={false} offset={0.30} darkness={0.30} />
      </EffectComposer>
    </>
  )
}

createRoot(document.getElementById("scene")).render(
  <Canvas
    dpr={[1, 1.4]}
    gl={{ antialias: false, powerPreference: "high-performance" }}
    camera={{ fov: 38, near: 0.35, far: 200, position: [0, 0, 0] }}
  >
    <Scene />
  </Canvas>
)
