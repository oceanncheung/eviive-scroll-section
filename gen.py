#!/usr/bin/env python3
"""
Generate a single Framer code component from the EVIIVE scroll-section prototype.

Run by hand:  python3 gen.py
Reads:   <repo>/index.html            CSS + markup + scroll driver
         <here>/scene.mjs             esbuild output of src/main.jsx, deps external
Writes:  <here>/EviiveScrollSection.tsx

Nothing imports this file. It is a one-shot build step whose product is pushed
into Framer with the MCP createCodeFile tool.

Four transforms make the prototype safe to drop into someone else's page:
  1. @font-face blocks are dropped - Framer already serves Inter.
  2. :root / html / body rules are rewritten onto the component's own wrapper
     class, so the type scale and ground colour cannot leak onto the live site.
  3. Every other selector is prefixed with that wrapper class, because names
     like .ui and .caption would otherwise collide with Framer's own classes.
  4. Bare import specifiers in the compiled scene become absolute esm.sh URLs,
     since a blob-URL module has no import map to resolve them against.
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/Users/oceancheung/Documents/Startup/MM.S/EVIIVE/eviive-scroll-section"
ESBUILD = os.path.join(HERE, "node_modules", ".bin", "esbuild")

ROOT_CLASS = "eviive-root"
# max-width breakpoints lifted out of @media into measured-width classes
widths = set()
SNAP_CLASS = "eviive-snap"

# Scroll snapping has to live on the real scroll container, which is the page -
# not the component's own box. Putting it on the page unconditionally would snap
# the entire site, so the component gates it behind a class it only adds while
# the section is on screen.
SNAP_PROPS = ("scroll-snap-type",)

# One React for the whole scene subtree: every specifier below resolves react to
# the identical esm.sh URL, so esm.sh serves a single instance.
REACT_V = "19.2.8"
THREE_V = "0.185.1"
DEPS = f"react@{REACT_V},react-dom@{REACT_V}"
CDN = {
    "react": f"https://esm.sh/react@{REACT_V}",
    "react/jsx-runtime": f"https://esm.sh/react@{REACT_V}/jsx-runtime",
    "react-dom": f"https://esm.sh/react-dom@{REACT_V}?deps={DEPS}",
    "react-dom/client": f"https://esm.sh/react-dom@{REACT_V}/client?deps={DEPS}",
    "three": f"https://esm.sh/three@{THREE_V}",
    "@react-three/fiber": f"https://esm.sh/@react-three/fiber@9.7.0?deps={DEPS},three@{THREE_V}",
    "@react-three/postprocessing": f"https://esm.sh/@react-three/postprocessing@3.0.4?deps={DEPS},three@{THREE_V},postprocessing@6.39.4",
    "postprocessing": f"https://esm.sh/postprocessing@6.39.4?deps=three@{THREE_V}",
}


def retarget_css_viewport(css):
    """Rewrite vh/vw units onto variables driven by the component's own box.

    In Framer the component lives inside a breakpoint artboard whose size has
    nothing to do with the browser window, but vh/vw always mean the window.
    That is why a desktop artboard in a shorter window rendered the stacked
    layout. --vh / --vw are published from a ResizeObserver on the host.
    """
    css = re.sub(
        r"(\d+(?:\.\d+)?)vh",
        lambda m: f"calc(var(--vh) * {float(m.group(1)) / 100:g})",
        css,
    )
    css = re.sub(
        r"(\d+(?:\.\d+)?)vw",
        lambda m: f"calc(var(--vw) * {float(m.group(1)) / 100:g})",
        css,
    )
    return css


def retarget_js_viewport(js, label):
    """Point innerWidth/innerHeight at the measured box instead of the window.

    Same reason as the CSS rewrite. Every layout decision in the driver and
    every camera/orb calculation in the scene reads these, so they must agree
    with the element the section is actually drawn into.
    """
    before = len(re.findall(r"\binnerWidth\b|\binnerHeight\b", js))
    js = re.sub(r"(?<![.\w$])innerWidth\b", "__eviiveVP.w", js)
    js = re.sub(r"(?<![.\w$])innerHeight\b", "__eviiveVP.h", js)
    js = re.sub(r"window\.__eviiveVP\.([wh])\b", r"__eviiveVP.\1", js)
    print(f"{label}: retargeted {before} viewport reads")
    return js


def run_esbuild(text, loader):
    """Minify a chunk of css or js through esbuild's stdin."""
    out = subprocess.run(
        [ESBUILD, f"--loader={loader}", "--minify"],
        input=text.encode(),
        capture_output=True,
    )
    if out.returncode != 0:
        sys.exit(f"esbuild {loader} failed:\n{out.stderr.decode()}")
    return out.stdout.decode()


def split_top_level(css):
    """Return [(prelude, body)] for each brace-delimited construct."""
    depth, buf, out, start, prelude = 0, "", [], 0, ""
    i = 0
    while i < len(css):
        ch = css[i]
        if ch == "{":
            if depth == 0:
                prelude, start = buf, i + 1
                buf = ""
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                out.append((prelude, css[start:i]))
                buf = ""
                i += 1
                continue
        elif depth == 0:
            buf += ch
        i += 1
    return out


def split_snap_decls(body):
    """Separate scroll-snap declarations from everything else in a rule body."""
    snap, rest = [], []
    for decl in body.split(";"):
        if not decl.strip():
            continue
        (snap if decl.split(":")[0].strip() in SNAP_PROPS else rest).append(decl.strip())
    return ";".join(snap), ";".join(rest)


def scope_selectors(sel):
    """Prefix each comma-separated selector with the wrapper class."""
    parts = []
    for one in sel.split(","):
        s = " ".join(one.split())
        if not s:
            continue
        if s == "*":
            # the bare universal selector must also cover the wrapper itself,
            # which `.wrapper *` would skip
            parts.append(f".{ROOT_CLASS}")
            parts.append(f".{ROOT_CLASS} *")
        elif s in (":root", "html", "body"):
            # the prototype puts the type scale on :root and the ground colour
            # on html; both belong on the component's own box instead.
            parts.append("." + ROOT_CLASS)
        elif s == ".stacked" or s.startswith(".stacked "):
            # `stacked` is toggled on <html> in the prototype. Here it lands on
            # the component root itself, so it must attach to the same element
            # as the wrapper class - no descendant space between them.
            parts.append(f".{ROOT_CLASS}{s}")
        elif s.startswith("." + ROOT_CLASS):
            parts.append(s)
        else:
            parts.append(f".{ROOT_CLASS} {s}")
    return ",".join(dict.fromkeys(parts))


def transform_css(css):
    widths.clear()
    # Comments must go first. A comment sitting above a rule is swept into that
    # rule's prelude, so the wrapper class gets prefixed onto the comment rather
    # than the selector - and a comma inside one would split the selector list
    # in the wrong place. Both fail silently.
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    dropped, out = [], []
    for prelude, body in split_top_level(css):
        head = " ".join(prelude.split())
        if head.startswith("@font-face"):
            dropped.append("@font-face")
            continue
        if head.startswith("@keyframes") or head.startswith("@-"):
            out.append(f"{head}{{{body}}}")
            continue
        if head.startswith("@media") or head.startswith("@supports"):
            # A max-width media query asks the WINDOW how wide it is, which is
            # the same mistake as innerWidth: a tablet artboard inside a wide
            # editor window would be given desktop type. Width breakpoints are
            # turned into classes the component sets from its measured box.
            mw = re.fullmatch(r"@media\s*\(\s*max-width\s*:\s*(\d+)px\s*\)", head)
            if mw:
                px = mw.group(1)
                widths.add(px)
                inner = "".join(
                    f"{scope_selectors(p).replace('.' + ROOT_CLASS, '.' + ROOT_CLASS + '.lte-' + px, 1)}{{{b}}}"
                    for p, b in split_top_level(body)
                )
                out.append(inner)
                continue
            inner = "".join(emit(p, b) for p, b in split_top_level(body))
            out.append(f"{head}{{{inner}}}")
            continue
        out.append(emit(prelude, body))
    return "".join(out), dropped


def emit(prelude, body):
    """Render one rule, lifting any scroll-snap declaration onto the page root."""
    head = " ".join(prelude.split())
    if head == "html":
        # scroll-snap-type is DROPPED, not relocated: CSS snapping offers no
        # control over duration or easing, so the module animates to the rest
        # states itself.
        _snap, rest = split_snap_decls(body)
        return f".{ROOT_CLASS}{{{rest}}}" if rest else ""
    return f"{scope_selectors(prelude)}{{{body}}}"


def main():
    html = open(os.path.join(REPO, "index.html"), encoding="utf-8").read()

    css_scoped, dropped = transform_css(
        re.search(r"<style[^>]*>(.*?)</style>", html, re.S).group(1)
    )
    # .pin stays 300vh for TWO states, deliberately. Travel is pinH - vh =
    # 200vh: state 1 at offset 0, state 2 at offset 100vh, and a further
    # 100vh of DWELL in which the section is still pinned. Without that
    # dwell the last snap point coincided exactly with the last pinned
    # position, so arriving at state 2 left zero headroom - any momentum
    # unpinned the section and slid it away while the 2.6s animation was
    # still running. The animation needs somewhere to happen.
    # The nav is opaque and fixed. The BACKGROUND runs full bleed behind it -
    # that is what makes the section own the screen - while only the CONTENT is
    # inset below it. .sticky therefore stays 100vh, and the two top-anchored
    # elements (headline, rail) are pushed down by the nav's height. --nav-h is
    # measured at runtime; 0px keeps the calc() valid until it is.
    css_scoped = css_scoped.replace(
        "--pad-t:48px", "--nav-h:0px;--pad-t:calc(48px + var(--nav-h))", 1
    )
    rail_top = "top:var(--pad-b);bottom:var(--pad-b)"
    if rail_top not in css_scoped:
        sys.exit("rail rule not found - shape changed")
    css_scoped = css_scoped.replace(
        rail_top, "top:calc(var(--pad-b) + var(--nav-h));bottom:var(--pad-b)", 1
    )
    css = run_esbuild(retarget_css_viewport(css_scoped), "css")

    body = re.search(r"<body[^>]*>(.*?)</body>", html, re.S).group(1)
    driver = re.search(r"<script[^>]*>(.*?)</script>", body, re.S).group(1)

    # The prototype owns the whole document, so it flags stacked mode on <html>.
    # Inside Framer the component owns only its own box, and the scoped CSS
    # expects the flag on that box - so retarget the toggle.
    # Must not begin with "(" or "[". The driver is written without semicolons,
    # so a leading paren is glued to the previous line by automatic semicolon
    # insertion - `scroll.stacked = HZ()` then becomes `HZ()(...)`, which throws
    # and takes the whole of alignUnit down with it.
    old_toggle = 'document.documentElement.classList.toggle("stacked", scroll.stacked)'
    new_toggle = (
        f'var __eviiveRoot = document.querySelector(".{ROOT_CLASS}") '
        f'|| document.documentElement; '
        f'__eviiveRoot.classList.toggle("stacked", scroll.stacked)'
    )
    if old_toggle not in driver:
        sys.exit("stacked toggle not found - the driver changed shape")
    driver = driver.replace(old_toggle, new_toggle)

    # The prototype's debug HUD is toggled by pressing D. On a public page any
    # visitor who types a "d" would summon a panel of internal numbers, so the
    # listener is removed. The HUD markup stays - the driver holds a reference
    # to it and calls .classList on it unguarded.
    hud_key = (
        'addEventListener("keydown", e => { if(e.key==="d"||e.key==="D")'
        " hud.classList.toggle(\"on\"); });"
    )
    if hud_key not in driver:
        sys.exit("hud keydown listener not found - the driver changed shape")
    driver = driver.replace(hud_key, "")

    # Framer Preview double-invokes effects. The first driver's rAF loop cannot
    # be stopped by removing its <script>, so it keeps running against DOM that
    # innerHTML="" already detached. getBoundingClientRect then returns zeros,
    # it computes progress as 0, and it writes p=0 every frame - fighting the
    # live driver. The overlay still looks right because the live driver writes
    # styles directly, but the WebGL samples the shared p and stays on scene 1.
    # So: each driver kills its predecessor and can be killed on unmount.
    driver = (
        "if(window.__eviiveStop)window.__eviiveStop();"
        "let __eviiveDead=false;"
        "window.__eviiveStop=function(){__eviiveDead=true};\n" + driver
    )
    old_raf = "function frame(now){"
    if old_raf not in driver:
        sys.exit("driver frame fn not found - shape changed")
    driver = driver.replace(old_raf, old_raf + " if(__eviiveDead)return;", 1)

    driver = retarget_js_viewport(driver, "driver")
    driver_min = run_esbuild(driver, "js")

    markup = re.sub(r"<script\b.*?</script>", "", body, flags=re.S)
    # prototype scaffolding with no place on the real page. #hud stays: the
    # driver holds a reference to it and calls .classList on it unguarded.
    markup = re.sub(r'<section class="next">.*?</section>', "", markup, flags=re.S)
    markup = markup.replace('<div class="snap c"></div>', "")
    markup = markup.strip()

    # Every id the driver looks up must exist, or it dies on a null reference
    # the moment that line runs - which may be many frames after load.
    wanted = set(re.findall(r'getElementById\("([^"]+)"\)', driver))
    present = set(re.findall(r'id="([^"]+)"', markup))
    missing = sorted(wanted - present)
    if missing:
        sys.exit(f"driver looks up ids absent from the markup: {missing}")

    scene = open(os.path.join(HERE, "scene.mjs"), encoding="utf-8").read()

    # esbuild strips JS comments but not the ones inside the GLSL template
    # literals, which are the single largest thing left in the bundle. The
    # documented shader source lives in the repo; this copy only has to run.
    # `//` is matched only when not preceded by ':' so esm.sh URLs survive.
    before = len(scene)
    scene = re.sub(r"/\*(?:[^*]|\*(?!/))*\*/", "", scene)
    scene = re.sub(r"(?<!:)//[^\n]*", "", scene)
    scene = re.sub(r"\n[ \t]*(?=\n)", "", scene)
    print(f"glsl comments stripped: {before - len(scene):,} bytes")
    unresolved = []
    for spec in sorted(set(re.findall(r'from"([^"]+)"', scene))):
        if spec in CDN:
            scene = scene.replace(f'from"{spec}"', f'from"{CDN[spec]}"')
        else:
            unresolved.append(spec)
    if unresolved:
        sys.exit(f"no CDN mapping for: {unresolved}")

    scene = retarget_js_viewport(scene, "scene")

    tsx = TEMPLATE.format(
        root_class=ROOT_CLASS,
        snap_class=SNAP_CLASS,
        widths=json.dumps(sorted(int(w) for w in widths)),
        css=json.dumps(css),
        markup=json.dumps(markup),
        driver=json.dumps(driver_min),
        scene=json.dumps(scene),
    )

    repo_dist = os.path.join(REPO, "dist")
    os.makedirs(repo_dist, exist_ok=True)
    dist = DIST_TEMPLATE.format(
        root_class=ROOT_CLASS,
        snap_class=SNAP_CLASS,
        widths=json.dumps(sorted(int(w) for w in widths)),
        css=json.dumps(css),
        markup=json.dumps(markup),
        driver=json.dumps(driver_min),
        scene=json.dumps(scene),
    )
    open(os.path.join(repo_dist, "eviive-section.js"), "w", encoding="utf-8").write(dist)
    print(f"DIST    {len(dist):>7,}  -> dist/eviive-section.js")

    dest = os.path.join(HERE, "EviiveScrollSection.tsx")
    open(dest, "w", encoding="utf-8").write(tsx)

    print(f"dropped from css : {dropped}")
    print(f"css     {len(css):>7,}")
    print(f"markup  {len(markup):>7,}")
    print(f"driver  {len(driver_min):>7,}  (was {len(driver):,})")
    print(f"scene   {len(scene):>7,}")
    print(f"TSX     {len(tsx):>7,}  -> {dest}")


TEMPLATE = '''\
// EVIIVE - therapy alignment scroll section.
//
// GENERATED FILE. The source of truth is the eviive-scroll-section repo
// (index.html + src/main.jsx), built by scratchpad/build/gen.py.
// Edit the repo and regenerate; do not hand-edit this file.
//
// Framer only permits npm imports of react / react-dom / framer / framer-motion,
// so the WebGL half arrives a different way:
//
//   - three, @react-three/fiber and postprocessing are fetched from esm.sh at
//     RUNTIME by dynamic import. Framer's build leaves dynamic import URLs
//     untouched, so nothing has to resolve at compile time.
//   - the compiled scene is inlined as a string and loaded through a blob URL,
//     so no file needs hosting anywhere.
//   - the scene mounts its own React root into #scene using esm.sh's react-dom.
//     That root is isolated from Framer's React, so the two instances never
//     interact and hooks cannot cross between them.
//   - all CSS is scoped to .{root_class}; the prototype's :root, html and body
//     rules are rewritten onto that class so nothing leaks onto the live site.

import {{ useEffect, useRef }} from "react"

// width breakpoints, applied from the measured box rather than the window
const BREAKPOINTS = {widths}

const CSS = {css}

const MARKUP = {markup}

const DRIVER = {driver}

const SCENE = {scene}

/**
 * @framerSupportedLayoutWidth any
 * @framerSupportedLayoutHeight any
 */
export default function EviiveScrollSection() {{
    const hostRef = useRef<HTMLDivElement>(null)

    useEffect(() => {{
        const host = hostRef.current
        if (!host) return

        let disposed = false
        let blobUrl = ""

        // WIDTH comes from the element, HEIGHT from the window.
        //
        // The prototype owned the whole document, so innerWidth was the section
        // width. In Framer the component sits in a breakpoint artboard - 1200px
        // on Desktop - while innerWidth reports the editor window, often wider.
        // Every layout decision keys off that number, including
        // `width/height < 1.15 || width < 900`, so a desktop artboard in a
        // shorter window resolved to the stacked layout and the whole
        // composition came out as the tablet one.
        //
        // Height is left on the window deliberately: the section is 300vh of
        // the real viewport, so window height is already the right answer and
        // deriving it from the box would just be circular.
        const vp = ((window as any).__eviiveVP =
            (window as any).__eviiveVP || {{ w: 0, h: 0 }})
        const syncVP = () => {{
            const w = Math.round(host.getBoundingClientRect().width) || innerWidth
            const h = innerHeight
            if (w === vp.w && h === vp.h) return
            vp.w = w
            vp.h = h
            host.style.setProperty("--vw", w + "px")
            host.style.setProperty("--vh", h + "px")
            for (const bp of BREAKPOINTS) {{
                host.classList.toggle("lte-" + bp, w <= bp)
            }}
            // the driver and the scene both re-measure on resize; the equality
            // guard above is what stops this re-entering forever
            dispatchEvent(new Event("resize"))
        }}
        syncVP()
        const ro = new ResizeObserver(syncVP)
        ro.observe(host)
        addEventListener("resize", syncVP, {{ passive: true }})

        const style = document.createElement("style")
        style.textContent = CSS
        document.head.appendChild(style)

        host.innerHTML = MARKUP
  const pinEl = host.querySelector("#pin")

        // The driver is the prototype's original classic script. It reads the
        // markup by id and publishes progress on window.__eviiveScroll, which
        // the scene polls every frame.
        const driverEl = document.createElement("script")
        driverEl.textContent = DRIVER
        document.body.appendChild(driverEl)

        // The fixed site nav overlaps the top of the section. The section stays
        // full bleed behind it - the headline is what has to clear it - so the
        // nav's real height is measured and published as --nav-h.
        const measureNav = () => {{
            let h = 0
            for (const el of document.body.querySelectorAll("*")) {{
                if (el === host || host.contains(el)) continue
                const cs = getComputedStyle(el)
                if (cs.position !== "fixed") continue
                const r = el.getBoundingClientRect()
                if (r.top <= 2 && r.width > innerWidth * 0.6 && r.height > 24 && r.height < 200) {{
                    h = Math.max(h, r.height)
                }}
            }}
            host.style.setProperty("--nav-h", h.toFixed(0) + "px")
        }}
        measureNav()
        addEventListener("resize", measureNav, {{ passive: true }})

        // Snapping belongs on the page, which is the real scroll container, but
        // must not apply to the rest of the site - so it is switched on only
        // while this section is actually on screen.
        //
        // `y mandatory` means the page MUST come to rest on a snap point. The
        // only snap points are the three inside this section, so with the
        // neighbouring sections offering none, the page can never rest outside
        // it - scroll in and you are trapped. The prototype did not have this
        // problem because its next section carried scroll-snap-align. The two
        // real neighbours are borrowed the same way here, and given back on
        // cleanup.
        const section = host.parentElement
        const neighbours = [
            section && section.previousElementSibling,
            section && section.nextElementSibling,
        ].filter(Boolean) as HTMLElement[]
        const priorAlign = neighbours.map((el) => el.style.scrollSnapAlign)
        neighbours.forEach((el) => {{
            el.style.scrollSnapAlign = "start"
        }})

        const io = new IntersectionObserver(
            ([e]) =>
                document.documentElement.classList.toggle(
                    "{snap_class}",
                    e.isIntersecting
                ),
            {{ threshold: 0 }}
        )
        io.observe(host)

        const boot = async () => {{
            try {{
                blobUrl = URL.createObjectURL(
                    new Blob([SCENE], {{ type: "text/javascript" }})
                )
                await import(/* @vite-ignore */ blobUrl)
            }} catch (err) {{
                if (disposed) return
                const note = document.createElement("pre")
                note.textContent = "EVIIVE scene failed to load:\\n" + String(err)
                note.style.cssText =
                    "position:absolute;inset:auto 16px 16px 16px;color:#9fd8ea;" +
                    "font:11px/1.5 ui-monospace,monospace;white-space:pre-wrap;opacity:.85"
                host.appendChild(note)
            }}
        }}
        boot()

        return () => {{
            disposed = true
            ro.disconnect()
            removeEventListener("resize", syncVP)
            removeEventListener("resize", measureNav)
            neighbours.forEach((el, n) => {{
                el.style.scrollSnapAlign = priorAlign[n] || ""
            }})
            io.disconnect()
                    style.remove()
            driverEl.remove()
            if (blobUrl) URL.revokeObjectURL(blobUrl)
            host.innerHTML = ""
        }}
    }}, [])

    // 100% of a 300vh section: .pin supplies the scroll travel and .sticky pins
    // one viewport of it. Set the Framer frame to 300vh, not 100vh, or there is
    // nothing to scroll through.
    return (
        <div
            ref={{hostRef}}
            className="{root_class}"
            style={{{{ width: "100%", height: "100%", position: "relative" }}}}
        />
    )
}}
'''



# Hosted build: a plain ESM module with NO React inside, so it cannot clash with
# Framer's React instance. The Framer stub imports it by URL and calls mount().
DIST_TEMPLATE = '''\
// EVIIVE therapy-alignment scroll section - hosted build.
// GENERATED by gen.py from index.html + src/main.jsx. Do not hand-edit.

const CSS = {css}
const MARKUP = {markup}
const DRIVER = {driver}
const SCENE = {scene}
const BREAKPOINTS = {widths}

/** Mount into `host`. Returns a teardown function. */
export default function mount(host) {{
  host.classList.add("{root_class}")
  host.style.position = "relative"

  const vp = (window.__eviiveVP = window.__eviiveVP || {{ w: 0, h: 0 }})
  const syncVP = () => {{
    const w = Math.round(host.getBoundingClientRect().width) || innerWidth
    const h = innerHeight
    if (w === vp.w && h === vp.h) return
    vp.w = w; vp.h = h
    host.style.setProperty("--vw", w + "px")
    host.style.setProperty("--vh", h + "px")
    for (const bp of BREAKPOINTS) host.classList.toggle("lte-" + bp, w <= bp)
    dispatchEvent(new Event("resize"))
  }}
  host.style.setProperty("--vw", "100%")
  host.style.setProperty("--vh", "100vh")
  syncVP()
  const ro = new ResizeObserver(syncVP); ro.observe(host)
  addEventListener("resize", syncVP, {{ passive: true }})

  // Measure the fixed site nav so the content can clear it. Bounded scan:
  // wide, pinned to the top, a plausible bar height.
  const measureNav = () => {{
    let h = 0
    // Framer nests its header well below body; a depth-limited selector never
    // found it and --nav-h stayed 0, so the title sat under the bar. This only
    // ever runs off-canvas, where the DOM is the real page rather than the
    // editor, and the poll stops as soon as a nav is found.
    // Hit-test the top of the screen rather than walking the document. The old
    // scan called getComputedStyle on every node of a Framer page - thousands of
    // forced style recalcs, repeated on a timer - which is the hitch felt while
    // approaching the section. elementsFromPoint returns only the stack under a
    // single pixel, so a fixed header is in it by construction.
    const list = document.elementsFromPoint(Math.round(innerWidth / 2), 4)
    for (let i = 0; i < list.length; i++) {{
      const el = list[i]
      if (el === host || el.contains(host) || host.contains(el)) continue
      const cs = getComputedStyle(el)
      if (cs.position !== "fixed" && cs.position !== "sticky") continue
      const r = el.getBoundingClientRect()
      if (r.top > 4 || r.width < innerWidth * 0.6) continue
      if (r.height < 24 || r.height > 220) continue
      if (r.height > h) h = r.height
    }}
    // Only write on change, and make the driver re-measure. alignUnit caches the
    // rail's geometry and refreshes it only on a viewport change, so moving the
    // rail via --nav-h without a resize left every tick positioned against stale
    // coordinates - which is why the timeline disappeared.
    const px = Math.round(h) + "px"
    if (px !== host.style.getPropertyValue("--nav-h")) {{
      host.style.setProperty("--nav-h", px)
      dispatchEvent(new Event("resize"))
    }}
    return h > 0
  }}
  let navFound = measureNav()
  const navTimer = setInterval(() => {{
    if (navFound) return clearInterval(navTimer)
    navFound = measureNav()
  }}, 250)                                        // the nav can mount later
  setTimeout(() => clearInterval(navTimer), 6000)

  const style = document.createElement("style")
  style.textContent = CSS
  document.head.appendChild(style)
  host.innerHTML = MARKUP
  const pinEl = host.querySelector("#pin")

  // the driver kills any predecessor: removing a <script> does not stop the rAF
  // loop it started, and an orphan holding detached DOM pins progress to 0
  const driverEl = document.createElement("script")
  driverEl.textContent = DRIVER
  document.body.appendChild(driverEl)

  const section = host.parentElement
  /* DISCRETE SCROLL CONTROLLER.
     The section behaves as two deliberate steps rather than a scrollable
     region: one gesture from the previous section lands on 6.4 months, one more
     goes to EVIIVE, and only when that transition has actually finished does
     ordinary scrolling resume. During a transition every input is swallowed —
     the animation is not something the reader can outrun.

     This is scroll-jacking and it is chosen, not accidental. It is confined to
     the moments the section owns the viewport, every listener is removed on
     unmount, and a watchdog releases the lock if anything ever fails, so the
     worst case is ordinary scrolling rather than a page that cannot move.

     A wheel gesture is dozens of events. Handling each one would fire every
     step at once, so after acting we swallow the rest of the burst until the
     reader has been still for COOL_MS. */
  const STEP_MS  = 620          // spring is home well before this
  const COOL_MS  = 160          // quiet time that ends one gesture
  const GUARD_MS = 6000         // watchdog: never stay locked forever

  /* A CRITICALLY DAMPED SPRING, not a bezier.
     Every fixed curve tried here read as stiff, and the reason is structural: a
     bezier is a shape imposed on a duration, so the motion starts and stops on
     the clock rather than on any physics. Ease-out is the worst of them, since
     it reaches maximum velocity at t=0 and therefore begins with a yank.
       x(t) = 1 - e^(-wt)(1 + wt)
     is the closed form of a spring damped exactly enough never to overshoot. It
     leaves from REST, builds quickly, and asymptotes into the target, so there
     is no instant at which the motion visibly stops. Measured against the
     alternatives at fractions of the duration:
       ease-out cubic   .39 .58 .87 .98    max speed at t=0, a yank
       material bezier  .07 .24 .78 .96    no yank, but a slow leave
       spring w=8       .34 .59 .91 .98    leaves from rest AND gets going
     w=8 is within 0.3% by the end; the last pixels are forced exactly. */
  const OMEGA = 8
  const easeOut = (t) => {{
    const w = OMEGA * t
    return 1 - Math.exp(-w) * (1 + w)
  }}

  let idx = null                // 0 = 6.4 months, 1 = EVIIVE, null = not engaged
  let locked = false            // transition in flight: swallow everything
  let cooling = false
  let raf = 0, coolT = 0, guardT = 0, touchY = 0

  const states = () => {{
    const top = pinEl.getBoundingClientRect().top + scrollY
    return [top, top + innerHeight]
  }}
  const progress = () => ((window.__eviiveScroll || {{}}).p) || 0
  /* How far the section must have arrived before a gesture belongs to it.
     At 1 it captured the moment its first pixel appeared, which made the
     previous section feel skipped: you would still be reading Our Platform,
     scroll once, and be pulled straight in. At 0.5 the section has to reach the
     middle of the screen first — until then scrolling is ordinary, and the
     hand-off reads as a decision rather than an ambush. Applied symmetrically
     so coming back up behaves the same way. */
  const CATCH_AT = 0.5

  const zone = () => {{
    const r = pinEl.getBoundingClientRect()
    if (r.top <= 0 && r.bottom >= innerHeight) return "inside"
    if (r.top > 0 && r.top < innerHeight * CATCH_AT) return "approach"
    if (r.bottom < innerHeight && r.bottom > innerHeight * (1 - CATCH_AT)) return "leaving"
    return "away"
  }}

  const unlock = () => {{ locked = false; clearTimeout(guardT) }}

  const glideTo = (y, targetP, hold) => {{
    const from = scrollY
    const t0 = performance.now()
    locked = true
    clearTimeout(guardT)
    guardT = setTimeout(unlock, GUARD_MS)          // never trap the reader
    if (raf) cancelAnimationFrame(raf)
    const step = (now) => {{
      const k = Math.min((now - t0) / STEP_MS, 1)
      if (k < 1) {{
        scrollTo(0, from + (y - from) * easeOut(k))
        raf = requestAnimationFrame(step)
        return
      }}
      scrollTo(0, y)                 // asymptotic curve: land it exactly
      raf = 0
      /* Only the EVIIVE transition is uninterruptible. Waiting on the scene for
         BOTH steps meant arriving at 6.4 swallowed every input for as long as
         the driver's 2.6s tween took to land - which is why scrolling back up
         felt impossible. Reaching the first state releases as soon as the
         scroll itself is done. */
      if (!hold) return unlock()
      const settle = () => {{
        if (Math.abs(progress() - targetP) < 0.005) return unlock()
        raf = requestAnimationFrame(settle)
      }}
      settle()
    }}
    raf = requestAnimationFrame(step)
  }}

  const goto = (i) => {{
    idx = i
    glideTo(states()[i], i === 0 ? 0.5 : 1, i === 1)
  }}

  const cool = () => {{
    cooling = true
    clearTimeout(coolT)
    coolT = setTimeout(() => {{ cooling = false }}, COOL_MS)
  }}

  /** @returns true if the gesture was consumed */
  const onStep = (dir) => {{
    const z = zone()
    if (z === "away") {{ idx = null; return false }}

    if (locked) {{ cool(); return true }}          // nothing gets through
    if (cooling) {{ cool(); return true }}         // still the same gesture

    if (z === "approach") {{
      if (dir > 0) {{ cool(); goto(0); return true }}
      return false                                  // going up, let them leave
    }}
    if (z === "leaving") {{
      if (dir < 0) {{ cool(); goto(1); return true }}   // re-enter from below
      return false
    }}
    // inside
    if (idx === null) idx = progress() >= 0.75 ? 1 : 0
    if (dir > 0) {{
      if (idx === 0) {{ cool(); goto(1); return true }}
      return false                                  // done — scroll on normally
    }}
    if (idx === 1) {{ cool(); goto(0); return true }}
    return false                                    // at the first state, go up
  }}

  const onWheel = (e) => {{
    if (Math.abs(e.deltaY) < 1) return
    if (onStep(e.deltaY > 0 ? 1 : -1)) e.preventDefault()
  }}
  const onTouchStart = (e) => {{ touchY = e.touches[0].clientY }}
  const onTouchMove = (e) => {{
    const dy = touchY - e.touches[0].clientY
    if (Math.abs(dy) < 6) return
    if (onStep(dy > 0 ? 1 : -1)) e.preventDefault()
  }}
  const KEYS = {{ ArrowDown: 1, PageDown: 1, " ": 1, ArrowUp: -1, PageUp: -1 }}
  const onKey = (e) => {{
    const d = KEYS[e.key]
    if (d && onStep(d)) e.preventDefault()
  }}

  addEventListener("wheel", onWheel, {{ passive: false }})
  addEventListener("touchstart", onTouchStart, {{ passive: true }})
  addEventListener("touchmove", onTouchMove, {{ passive: false }})
  addEventListener("keydown", onKey)

  let blobUrl = ""
  try {{
    blobUrl = URL.createObjectURL(new Blob([SCENE], {{ type: "text/javascript" }}))
    import(/* @vite-ignore */ blobUrl)
  }} catch (err) {{ console.error("[eviive] scene:", err) }}

  return () => {{
    if (window.__eviiveStop) window.__eviiveStop()
    ro.disconnect()
    removeEventListener("resize", syncVP)
    if (raf) cancelAnimationFrame(raf)
    clearTimeout(coolT)
    clearTimeout(guardT)
    removeEventListener("wheel", onWheel)
    removeEventListener("touchstart", onTouchStart)
    removeEventListener("touchmove", onTouchMove)
    removeEventListener("keydown", onKey)
    document.documentElement.classList.remove("{snap_class}")
    clearInterval(navTimer)
    style.remove(); driverEl.remove()
    if (blobUrl) URL.revokeObjectURL(blobUrl)
    host.innerHTML = ""
  }}
}}
'''


if __name__ == "__main__":
    main()
