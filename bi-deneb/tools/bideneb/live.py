"""A test page that runs a specification in the Vega version of Deneb, in a browser, with data changes.

The local render (vl-convert) draws one state with an older Vega. Power BI changes the data of a running view: a
slicer, a cross-filter, a refresh. A specification that keeps state in signals (a page, an offset, a sort) can then
draw nothing although rows are there. This page embeds the specification fresh for every scenario and also changes
the data of a running view from one scenario to the next; both must draw the same. It loads Vega from jsDelivr in
the version Deneb runs and writes its result into the page (element #result, `window.bidenebLive`)."""
import copy
import json
import re

from . import deneb, expr as ex, render

SEQUENCE = ["typical", "few", "empty", "stress", "typical", "empty", "few"]
VEGA_CDN = "https://cdn.jsdelivr.net/npm/vega@{v}/build/vega.min.js"


def data_marks(spec: dict) -> list[str]:
    """Names the marks get in the test page; marks without a name get bd_m<n>. Returns the names of marks that draw
    from data derived from the dataset (directly or through a chain of `source`)."""
    derived = {"dataset"}
    changed = True
    datas = [d for d in spec.get("data", []) if isinstance(d, dict)]
    while changed:
        changed = False
        for d in datas:
            src = d.get("source")
            srcs = src if isinstance(src, list) else [src]
            if d.get("name") not in derived and any(s in derived for s in srcs if s):
                derived.add(d["name"])
                changed = True
    out, n = [], 0

    def visit(marks):
        nonlocal n
        for m in marks or []:
            if not isinstance(m, dict):
                continue
            if not m.get("name"):
                m["name"] = f"bd_m{n}"
                n += 1
            frm = m.get("from") or {}
            facet = frm.get("facet") or {}
            if facet.get("data") in derived and facet.get("name"):
                derived.add(facet["name"])
                out.append(m["name"])
            elif frm.get("data") in derived:
                out.append(m["name"])
            visit(m.get("marks"))

    visit(spec.get("marks"))
    return out


def reachable_states(spec: dict) -> list[dict]:
    """States a user reaches by clicking: every top-level signal with event handlers and a literal start value gets
    other values (a number +1 and +2, the other string literals of its handlers, the other boolean). The test page sets
    each before the rows get fewer; a page or offset that a data change does not bring back shows up there (L3)."""
    out = []
    for sig in spec.get("signals", []):
        if not isinstance(sig, dict) or not sig.get("on") or "value" not in sig or sig.get("name") == "denebContainer":
            continue
        v, name = sig["value"], sig["name"]
        if isinstance(v, bool):
            out.append({name: not v})
        elif isinstance(v, (int, float)):
            out += [{name: v + 1}, {name: v + 2}]
        elif isinstance(v, str):
            lits = []
            for h in sig["on"]:
                if isinstance(h, dict) and isinstance(h.get("update"), str):
                    lits += [x for x in ex.analyse(h["update"])["strings"] if x != v and x not in lits]
            out += [{name: x} for x in lits[:3]]
    return out


def page(name: str, specs: dict, scenarios: dict, dates: list[str], states: list[dict], marks: list[str],
         vega_version: str = deneb.VEGA_VERSION) -> str:
    payload = json.dumps({"name": name, "specs": specs, "scenarios": scenarios, "dates": dates, "states": states,
                          "marks": marks, "sequence": [s for s in SEQUENCE if s in scenarios]},
                         ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>bideneb live {name}</title>
<script src="{VEGA_CDN.format(v=vega_version)}"></script>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:16px;background:#F6F5F3}}pre{{white-space:pre-wrap;background:#fff;padding:8px}}
.v{{display:inline-block;margin:6px;background:#fff;border:1px solid #ccc;vertical-align:top}}.v b{{display:block;font-size:12px;padding:2px 4px}}</style>
</head><body><h3>bideneb live: {name} (Vega {vega_version}, as in Deneb {deneb.DENEB_VERSION})</h3>
<pre id="result">running …</pre><div id="views"></div>
<script>
const P = {payload};
function rowsOf(name) {{
  return (P.scenarios[name] || []).map(r => {{
    const o = Object.assign({{}}, r);
    for (const d of P.dates) if (typeof o[d] === 'string')                       // Deneb hands over local dates
      o[d] = new Date(/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(o[d]) ? o[d] + 'T00:00:00' : o[d]);
    return o;
  }});
}}
function withRows(spec, rows) {{
  const s = JSON.parse(JSON.stringify(spec));
  for (const d of s.data) if (d.name === 'dataset') {{ d.values = rows; delete d.format; }}
  return s;
}}
function count(view) {{
  const out = {{}};
  (function walk(item) {{
    if (!item) return;
    if (item.marktype !== undefined && item.items) {{          // a mark
      if (item.name) out[item.name] = (out[item.name] || 0) + item.items.length;
      for (const it of item.items) walk(it);
    }} else if (item.items) {{ for (const it of item.items) walk(it); }}
  }})(view.scenegraph().root);
  return out;
}}
function drawn(counts) {{ return P.marks.reduce((a, m) => a + (counts[m] || 0), 0); }}
async function make(spec, label, log) {{
  const div = document.createElement('div'); div.className = 'v';
  div.innerHTML = '<b>' + label + '</b>'; const host = document.createElement('div'); div.appendChild(host);
  document.getElementById('views').appendChild(div);
  const logger = {{ _l: 2, level(l) {{ if (l !== undefined) this._l = l; return this._l; }},
    error(...a) {{ log.push(['ERROR', label, a.map(String).join(' ')]); }},
    warn(...a) {{ log.push(['WARNING', label, a.map(String).join(' ')]); }}, info() {{}}, debug() {{}} }};
  const view = new vega.View(vega.parse(spec), {{ renderer: 'svg', container: host, hover: true, logger }});
  view.logLevel(vega.Warn);
  await view.runAsync();
  return view;
}}
function diff(a, b) {{
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]); const out = [];
  for (const k of keys) if ((a[k] || 0) !== (b[k] || 0)) out.push(k + ' ' + (a[k] || 0) + ' instead of ' + (b[k] || 0));
  return out;
}}
(async () => {{
  const findings = [], log = [];
  try {{
    if (typeof vega === 'undefined') throw new Error('no Vega');
    for (const size of Object.keys(P.specs)) {{
      const spec = P.specs[size];
      const fresh = {{}};
      for (const sc of new Set(P.sequence)) {{
        const v = await make(withRows(spec, rowsOf(sc)), size + ' ' + sc + ' (fresh)', log);
        fresh[sc] = count(v);
        if (P.scenarios[sc].length && !drawn(fresh[sc]))
          findings.push(['ERROR', 'L2', size + ' ' + sc + ': nothing drawn from ' + P.scenarios[sc].length + ' rows']);
        if (sc !== P.sequence[0]) v.finalize();
      }}
      // one running view, the data changes as a slicer would change it
      const live = await make(withRows(spec, rowsOf(P.sequence[0])), size + ' live', log);
      let prev = P.sequence[0];
      for (const sc of P.sequence.slice(1)) {{
        live.change('dataset', vega.changeset().remove(() => true).insert(rowsOf(sc)));
        await live.runAsync();
        const d = diff(count(live), fresh[sc]);
        if (d.length) findings.push(['ERROR', 'L1', size + ' ' + prev + ' -> ' + sc + ': the running view draws ' +
          d.slice(0, 4).join(', ') + ' (fresh embed in brackets): state in signals survived the data change']);
        prev = sc;
      }}
      // states the user can reach (a page, a sort), then fewer rows
      for (const st of P.states) {{
        const v = await make(withRows(spec, rowsOf('stress')), size + ' state ' + JSON.stringify(st), log);
        try {{ for (const [k, val] of Object.entries(st)) v.signal(k, val); await v.runAsync(); }}
        catch (e) {{ findings.push(['WARNING', 'L3', size + ' state ' + JSON.stringify(st) + ' not set: ' + e]); v.finalize(); continue; }}
        for (const sc of ['few', 'typical']) {{
          if (!P.scenarios[sc] || !P.scenarios[sc].length) continue;
          v.change('dataset', vega.changeset().remove(() => true).insert(rowsOf(sc)));
          await v.runAsync();
          if (!drawn(count(v))) findings.push(['ERROR', 'L3', size + ' state ' + JSON.stringify(st) + ' then ' + sc +
            ': nothing drawn from ' + P.scenarios[sc].length + ' rows; derive the state from the data (clamp it) '
            + 'instead of resetting it on a signal event']);
        }}
        v.finalize();
      }}
    }}
  }} catch (e) {{ if (typeof vega !== 'undefined') findings.push(['ERROR', 'L0', 'the page failed: ' + e]); }}
  for (const [lv, where, text] of log) findings.push([lv, 'L4', where + ': Vega reported ' + text.slice(0, 300)]);
  const n = l => findings.filter(f => f[0] === l).length;
  if (typeof vega === 'undefined') findings.push(['ERROR', 'L0', 'Vega did not load from jsDelivr (offline or blocked)']);
  const lines = findings.map(f => f[0].padEnd(8) + f[1] + ' ' + f[2]);
  lines.push('RESULT: ' + n('ERROR') + ' error(s), ' + n('WARNING') + ' warning(s); Vega ' +
             (typeof vega !== 'undefined' ? vega.version : 'not loaded') +
             '; sizes ' + Object.keys(P.specs).join(', ') + '; sequence ' + P.sequence.join(' > '));
  document.getElementById('result').textContent = lines.join('\\n');
  window.bidenebLive = {{ findings, done: true }};
}})();
</script></body></html>
"""


def build(name: str, spec: dict, config: dict | None, scenarios: dict, sizes: list, brand,
          states: list[dict] | None = None) -> str:
    """The HTML of the test page. scenarios: name -> rows as the dataset gets them (rows_for_deneb).
    The specification is prepared as for the local render (Deneb's patches, pbi functions approximated)."""
    specs, dates, marks = {}, [], []
    for rows in scenarios.values():
        for d in render.date_fields(rows):
            if d not in dates:
                dates.append(d)
    sample = next((r for r in scenarios.values() if r), [])
    for (w, h) in sizes:
        vega, _ = render.to_vega(spec, config, sample, w, h, brand)
        vega = copy.deepcopy(vega)
        marks = data_marks(vega)
        specs[f"{w}x{h}"] = vega
    found = list(states or [])
    for st in reachable_states(next(iter(specs.values()), {})):
        if st not in found:
            found.append(st)
    return page(name, specs, scenarios, dates, found, marks)
