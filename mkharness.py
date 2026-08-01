#!/usr/bin/env python3
"""
Build harness.html from the generated Framer component.

Run by hand:  python3 mkharness.py      (after gen.py)
Nothing imports this file.

The harness reproduces Framer's environment rather than the prototype's: the
PAGE is the scroll container, the component sits in a 300vh section, and there
are neighbouring sections above and below so the IntersectionObserver that gates
scroll snapping has something real to switch against.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TSX = os.path.join(HERE, "EviiveScrollSection.tsx")


def const(name, src):
    return json.loads(
        re.search(rf'^const {name} = (".*?")\n', src, re.S | re.M).group(1)
    )


def main():
    src = open(TSX, encoding="utf-8").read()
    css, markup, driver, scene = (
        const(n, src) for n in ("CSS", "MARKUP", "DRIVER", "SCENE")
    )

    page = f"""<!doctype html><meta charset="utf-8">
<title>EVIIVE component harness</title>
<style>
  html,body{{margin:0;background:#f5fcff}}
  .neighbour{{height:60vh;display:grid;place-items:center;background:#f5fcff;
    color:#022c3b;font:500 24px/1.3 Inter,system-ui,sans-serif}}
  /* the Framer section: 300vh of travel, component fills it */
  #section{{height:300vh;position:relative;background:#022c3b}}
  #root{{width:100%;height:100%;position:relative}}
  #err{{position:fixed;left:8px;top:8px;z-index:99;color:#ff6;font:11px/1.4 monospace;
    white-space:pre-wrap;max-width:44vw;pointer-events:none;text-shadow:0 0 4px #000}}
</style>

<div class="neighbour">Biomarker Opportunity (above)</div>
<div id="section"><div id="root" class="eviive-root"></div></div>
<div class="neighbour">Metrics (below)</div>
<pre id="err"></pre>

<script type="module">
const CSS={json.dumps(css)}, MARKUP={json.dumps(markup)},
      DRIVER={json.dumps(driver)}, SCENE={json.dumps(scene)};
const log=m=>{{document.getElementById("err").textContent+=m+"\\n"}};
addEventListener("error",e=>log("ERROR: "+e.message));
addEventListener("unhandledrejection",e=>log("REJECT: "+e.reason));

const host=document.getElementById("root");
// mirror the component wrapper: measured width, window height, bp classes
const vp=(window.__eviiveVP=window.__eviiveVP||{{w:0,h:0}});
const BREAKPOINTS=[809,1199];
const syncVP=()=>{{
  const w=Math.round(host.getBoundingClientRect().width)||innerWidth, h=innerHeight;
  if(w===vp.w&&h===vp.h) return;
  vp.w=w; vp.h=h;
  host.style.setProperty("--vw",w+"px"); host.style.setProperty("--vh",h+"px");
  for(const bp of BREAKPOINTS) host.classList.toggle("lte-"+bp, w<=bp);
  dispatchEvent(new Event("resize"));
}};
syncVP(); new ResizeObserver(syncVP).observe(host);
addEventListener("resize",syncVP,{{passive:true}});
const s=document.createElement("style"); s.textContent=CSS; document.head.appendChild(s);
host.innerHTML=MARKUP;
const d=document.createElement("script"); d.textContent=DRIVER; document.body.appendChild(d);

new IntersectionObserver(
  ([e])=>document.documentElement.classList.toggle("eviive-snap", e.isIntersecting),
  {{threshold:0}}
).observe(host);

try{{
  const u=URL.createObjectURL(new Blob([SCENE],{{type:"text/javascript"}}));
  await import(u); log("scene imported OK");
}}catch(e){{ log("SCENE FAIL: "+(e.stack||e)); }}
</script>
"""
    dest = os.path.join(HERE, "harness.html")
    open(dest, "w", encoding="utf-8").write(page)
    print(f"harness.html {len(page):,} bytes")
    write_framer_harness()


def write_framer_harness():
    """Harness that runs FRAMER'S OWN compiled build, not the local copy.

    This is the stronger test: it proves Framer's compiler preserved the blob
    loader and the esm.sh URLs, and that the component mounts and paints. The
    module statically imports the bare specifiers `react` and
    `react/jsx-runtime`, which Framer resolves with its own import map - so one
    is supplied here.
    """
    url_file = os.path.join(HERE, "module-url.txt")
    if not os.path.exists(url_file):
        print("module-url.txt missing - skipping framer harness")
        return
    url = open(url_file, encoding="utf-8").read().strip()
    r = "https://esm.sh/react@19.2.8"
    page = f"""<!doctype html><meta charset="utf-8">
<title>EVIIVE - Framer build harness</title>
<script type="importmap">
{{"imports":{{
  "react":"{r}",
  "react/jsx-runtime":"{r}/jsx-runtime",
  "react-dom":"https://esm.sh/react-dom@19.2.8?deps=react@19.2.8",
  "react-dom/client":"https://esm.sh/react-dom@19.2.8/client?deps=react@19.2.8"
}}}}
</script>
<style>
  html,body{{margin:0;background:#f5fcff}}
  .neighbour{{height:60vh;display:grid;place-items:center;background:#f5fcff;
    color:#022c3b;font:500 24px/1.3 Inter,system-ui,sans-serif}}
  #section{{height:300vh;position:relative;background:#022c3b}}
  #err{{position:fixed;left:8px;top:8px;z-index:99;color:#ff6;font:11px/1.4 monospace;
    white-space:pre-wrap;max-width:44vw;pointer-events:none;text-shadow:0 0 4px #000}}
</style>
<div class="neighbour">Biomarker Opportunity (above)</div>
<div id="section"></div>
<div class="neighbour">Metrics (below)</div>
<pre id="err"></pre>
<script type="module">
const log=m=>{{document.getElementById("err").textContent+=m+"\\n"}};
addEventListener("error",e=>log("ERROR: "+e.message));
addEventListener("unhandledrejection",e=>log("REJECT: "+e.reason));
try{{
  const React=(await import("react")).default;
  const {{createRoot}}=await import("react-dom/client");
  const mod=await import("{url}");
  log("framer module loaded, default="+typeof mod.default);
  createRoot(document.getElementById("section"))
    .render(React.createElement(mod.default));
  log("mounted");
}}catch(e){{ log("FAIL: "+(e.stack||e)); }}
</script>
"""
    dest = os.path.join(HERE, "framer-harness.html")
    open(dest, "w", encoding="utf-8").write(page)
    print(f"framer-harness.html {len(page):,} bytes -> {url.rsplit('/',2)[1]}")


if __name__ == "__main__":
    main()
