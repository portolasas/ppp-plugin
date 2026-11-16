"""The rules. Static ones read the specification, picture ones read a render. Each finding names its fix.

Codes: D = Deneb and Power BI, F = fields, B = brand, P = picture, X = interaction."""
import re
from dataclasses import dataclass

from . import brand as br
from . import deneb
from . import expr as ex
from . import scene as sc

LEVELS = ("ERROR", "WARNING", "NOTE")
AGGREGATING = {"aggregate", "bin", "fold", "pivot", "flatten", "density", "regression", "loess", "quantile",
               "countpattern", "kde", "nest", "stratify", "pack", "treemap", "partition"}
DERIVED_DEFAULTS = {"aggregate": ["count"], "stack": ["y0", "y1"], "bin": ["bin0", "bin1"], "fold": ["key", "value"],
                    "sequence": ["data"], "pie": ["startAngle", "endAngle"], "flatten": [], "window": [],
                    "countpattern": ["text", "count"], "density": ["value", "density"], "extent": [],
                    "timeunit": ["unit0", "unit1"], "linkpath": ["path"], "impute": [], "force": ["x", "y", "vx", "vy"],
                    "wordcloud": ["x", "y", "font", "fontSize", "fontStyle", "fontWeight", "angle"],
                    "voronoi": ["path"], "geopoint": ["x", "y"], "geopath": ["path"], "label": ["x", "y", "opacity", "align", "baseline"],
                    "treemap": ["x0", "y0", "x1", "y1", "depth", "children"], "partition": ["x0", "y0", "x1", "y1", "depth", "children"],
                    "tree": ["x", "y", "depth", "children"], "pack": ["x", "y", "r", "depth", "children"],
                    "regression": [], "loess": [], "quantile": ["prob", "value"], "kde": ["value", "density"],
                    "identifier": [], "cross": ["a", "b"], "dotbin": ["bin"]}
UTC = re.compile(r"\butc(?:Format|Parse|year|quarter|month|date|day|dayofyear|week|hours|minutes|seconds|milliseconds|Offset|Sequence)?\b|\butc\(")
OPS = ("count", "valid", "missing", "distinct", "sum", "product", "mean", "average", "variance", "variancep", "stdev",
       "stdevp", "stderr", "median", "q1", "q3", "ci0", "ci1", "min", "max", "argmin", "argmax", "values")


COLOR_KEYS = {"fill", "stroke", "color", "background", "labelColor", "titleColor", "gridColor", "domainColor",
              "tickColor", "subtitleColor", "symbolFillColor", "symbolStrokeColor"}
CSS_COLORS = {"red": "#FF0000", "green": "#008000", "blue": "#0000FF", "yellow": "#FFFF00", "orange": "#FFA500",
              "purple": "#800080", "pink": "#FFC0CB", "brown": "#A52A2A", "gray": "#808080", "grey": "#808080",
              "lightgray": "#D3D3D3", "lightgrey": "#D3D3D3", "darkgray": "#A9A9A9", "darkgrey": "#A9A9A9",
              "silver": "#C0C0C0", "gold": "#FFD700", "navy": "#000080", "teal": "#008080", "cyan": "#00FFFF",
              "aqua": "#00FFFF", "magenta": "#FF00FF", "fuchsia": "#FF00FF", "lime": "#00FF00", "maroon": "#800000",
              "olive": "#808000", "steelblue": "#4682B4", "tomato": "#FF6347", "crimson": "#DC143C",
              "firebrick": "#B22222", "darkred": "#8B0000", "darkgreen": "#006400", "darkblue": "#00008B",
              "lightblue": "#ADD8E6", "lightgreen": "#90EE90", "skyblue": "#87CEEB", "royalblue": "#4169E1",
              "dodgerblue": "#1E90FF", "salmon": "#FA8072", "coral": "#FF7F50", "indigo": "#4B0082",
              "violet": "#EE82EE", "khaki": "#F0E68C", "beige": "#F5F5DC", "tan": "#D2B48C", "turquoise": "#40E0D0",
              "slategray": "#708090", "dimgray": "#696969", "gainsboro": "#DCDCDC", "whitesmoke": "#F5F5F5",
              "black": "#000000", "white": "#FFFFFF"}


@dataclass
class Finding:
    level: str
    code: str
    text: str

    def line(self) -> str:
        return f"{self.level:<7} {self.code} {self.text}"


def order(findings: list) -> list:
    seen, out = set(), []
    for f in sorted(findings, key=lambda f: (LEVELS.index(f.level), f.code)):
        if (f.code, f.text) not in seen:
            seen.add((f.code, f.text))
            out.append(f)
    return out


def worst(findings: list) -> str:
    return min((f.level for f in findings), key=LEVELS.index, default="OK")


# ================================================================== static
def _transforms(spec):
    for path, key, value in ex.walk(spec):
        if key == "transform" and isinstance(value, list):
            for t in value:
                if isinstance(t, dict):
                    yield path, t


def _vl_transform_kind(t: dict) -> str:
    for k in ("aggregate", "bin", "calculate", "filter", "fold", "pivot", "flatten", "window", "joinaggregate",
              "stack", "timeUnit", "lookup", "impute", "density", "regression", "loess", "quantile", "sample", "extent"):
        if k in t:
            return k
    return t.get("type", "")


def derived_fields(spec: dict) -> set:
    """Names that transforms and encodings add to the rows."""
    out = set()

    def add(v):
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, list):
            for x in v:
                add(x)

    for _, t in _transforms(spec):
        kind = _vl_transform_kind(t)
        add(t.get("as"))
        for sub in ("aggregate", "window", "joinaggregate"):
            if isinstance(t.get(sub), list):
                for a in t[sub]:
                    if isinstance(a, dict):
                        add(a.get("as"))
        if isinstance(t.get("lookup"), str) and isinstance(t.get("from"), dict):
            add(t["from"].get("fields"))
        if kind == "pivot":
            out.add("*pivot*")
        if isinstance(t.get("type"), str):
            ttype = t["type"]
            if t.get("as") is None:
                for d in DERIVED_DEFAULTS.get(ttype, []):
                    out.add(d)
            if ttype in ("aggregate", "joinaggregate", "window") and t.get("as") is None:
                ops, fields = t.get("ops") or ["count"], t.get("fields") or [None]
                for op, fld in zip(ops, fields):
                    out.add(op if not fld else f"{op}_{fld if isinstance(fld, str) else ''}")
            if ttype == "lookup":
                add(t.get("values"))
            if ttype == "pivot":
                out.add("*pivot*")
        if kind == "bin" and isinstance(t.get("as"), str):
            out.add(t["as"] + "_end")
    for path, key, value in ex.walk(spec):
        if key in ("values",) and isinstance(value, list) and value and isinstance(value[0], dict):
            for row in value[:50]:
                out.update(row.keys())
        if key == "encoding" and isinstance(value, dict):
            for ch in value.values():
                for d in (ch if isinstance(ch, list) else [ch]):
                    if isinstance(d, dict) and d.get("field") and (d.get("aggregate") or d.get("bin") or d.get("timeUnit")):
                        out.add("*encoding*")
    out.update({"__count", "count"})
    return out


def field_uses(spec: dict) -> dict:
    """Field name -> first place it is read (expressions and field properties)."""
    uses = {}
    for path, text in ex.expressions(spec):
        if path[-1] == "labelExpr" or "axis" in path or "legend" in path or "axes" in path or "legends" in path:
            continue   # datum is the tick or legend entry there, not a row
        for f in ex.analyse(text)["fields"]:
            uses.setdefault(f, ex.show(path))
    for path, key, value in ex.walk(spec):
        if key in ("field", "groupby", "fields", "sort", "key", "x", "y", "x2", "y2", "detail") and "encode" not in path:
            for v in (value if isinstance(value, list) else [value]):
                if isinstance(v, str) and key not in ("sort", "x", "y", "x2", "y2", "detail"):
                    uses.setdefault(_plain(v), ex.show(path + (key,)))
                elif isinstance(v, dict) and isinstance(v.get("field"), str) and key in ("sort", "fields"):
                    uses.setdefault(_plain(v["field"]), ex.show(path + (key,)))
        elif key == "field" and isinstance(value, str):
            uses.setdefault(_plain(value), ex.show(path + (key,)))
    return uses


def _plain(name: str) -> str:
    m = re.fullmatch(r"datum\[['\"](.+)['\"]\]|datum\.(.+)", name)
    if m:
        return m.group(1) or m.group(2)
    for esc in (".", "[", "]", "'", "\\"):
        name = name.replace("\\" + esc, esc)
    return name


def static(spec: dict, config: dict | None, brand, dataset: list[str] | None, interaction: dict,
           render_mode: str = "svg", generated: bool = False) -> list:
    """Findings from reading the specification. dataset: keys of the fields the visual gets, None if unknown."""
    out = []
    add = lambda level, code, text: out.append(Finding(level, code, text))
    provider = deneb.provider_of(spec)
    texts = [(path, key, v) for path, key, v in ex.walk({"spec": spec, "config": config or {}}) if isinstance(v, str)]
    exprs = ex.expressions(spec)
    calls, strings = set(), []
    for _, text in exprs:
        a = ex.analyse(text)
        calls.update(a["calls"])
        strings += a["strings"]

    # ---- D: Deneb and Power BI
    named = [d.get("name") for d in spec.get("data", [])] if provider == "vega" and isinstance(spec.get("data"), list) else []
    if provider == "vega" and "dataset" not in named:
        add("ERROR", "D1", "no data source named \"dataset\": Deneb puts the rows of the visual into data[name=dataset]")
    if provider == "vegaLite":
        d = spec.get("data")
        if not (isinstance(d, dict) and d.get("name") == "dataset"):
            add("ERROR", "D1", "top-level data must be {\"name\": \"dataset\"}: Deneb puts the rows of the visual there")
    for path, key, v in ex.walk(spec):
        if key == "url" and isinstance(v, str) and not v.startswith("data:"):
            add("ERROR", "D2", f"{ex.show(path)}.url: Deneb loads nothing from outside ({v[:60]}); the certified visual "
                               f"allows only data: URIs; bring the data in through the dataset")
    for name in deneb.REMOVED_FIELDS:
        if any(name in v for _, _, v in texts):
            add("ERROR", "D3", f"{name} was removed in Deneb 1.9; use __row__")
    for old, new in deneb.LEGACY_SIGNALS.items():
        if any(re.search(rf"\b{old}\b", v) for _, _, v in texts):
            add("WARNING", "D4", f"{old} is deprecated since Deneb 2.0; use {new}")
    if any(re.search(r"\bpbiContainer\b", v) for _, _, v in texts):
        add("WARNING", "D4", "pbiContainer is deprecated since Deneb 2.0; use denebContainer")
    if provider == "vegaLite":
        for key in ("width", "height"):
            if isinstance(spec.get(key), (int, float)):
                add("WARNING", "D5", f"{key}: {spec[key]} is a fixed size; leave it out so that Deneb fits the visual "
                                     f"to its container (or derive it from denebContainer.{key})")
    elif not any("denebContainer" in v for _, _, v in texts) and not generated:
        if any(isinstance(spec.get(k), (int, float)) for k in ("width", "height")):
            add("WARNING", "D5", "fixed width or height and no use of denebContainer: the visual does not follow the "
                                 "size of its container")
    if UTC.search(" ".join(t for _, t in exprs)) or any(
            key == "timeUnit" and isinstance(v, str) and v.startswith("utc") for _, key, v in ex.walk(spec)):
        add("WARNING", "D6", "utc… functions or time units: Deneb passes dates as local time, so utc… shifts every "
                             "value by the time-zone offset; use the local functions")
    if render_mode == "canvas" and any("url(#" in v for _, _, v in texts):
        add("ERROR", "D7", "pattern fills (url(#…)) need the SVG renderer; renderMode is canvas")
    if config:
        for key in ("width", "height", "autosize"):
            if key in config:
                add("NOTE", "D8", f"config.{key}: size and autosize belong into the specification; Deneb drops "
                                  f"\"container\" sizes and autosize.resize from the config")
    unknown_pbi = sorted(c for c in calls if c.startswith("pbi") and c not in deneb.PBI_FUNCTIONS)
    if unknown_pbi:
        add("ERROR", "D9", f"unknown Deneb function {', '.join(unknown_pbi)}; Deneb has {', '.join(sorted(deneb.PBI_FUNCTIONS))}")
    plain_format = [p for p, t in exprs if re.search(r"(?<![\w.])format\(", t)]
    if provider == "vegaLite":
        for path, key, v in ex.walk(spec):
            if key == "format" and isinstance(v, str) and isinstance(_at(spec, path), dict) \
                    and _at(spec, path).get("formatType") is None and _at(spec, path).get("type") != "temporal" \
                    and "timeUnit" not in _at(spec, path) and re.search(r"[,.]\d|[df%s]$", v):
                plain_format.append(path)
    if plain_format and not generated:
        add("NOTE", "D10", f"{len(plain_format)} number format(s) in d3 notation (first: {ex.show(plain_format[0])}): "
                           f"they ignore the format of the measure and the locale of the report; prefer "
                           f"formatType \"pbiFormat\" or pbiFormat()")
    if any("pbiColor" in c for c in calls) or any(v in deneb.PBI_SCHEMES for _, _, v in texts):
        add("NOTE", "D11", "pbiColor or a pbiColor… scheme takes the colours of the report theme; they are brand "
                           "colours only while the brand theme is applied to the report")
    if "$schema" not in spec:
        add("NOTE", "D12", "no $schema: add it to the file so that editors and this tool know Vega from Vega-Lite "
                           "(the embedded copy leaves it out)")

    # ---- F: fields
    if dataset is not None:
        known = set(dataset) | deneb.ROW_FIELDS
        for k in dataset:
            known.update(k + s for s in deneb.SUPPORT_SUFFIXES)
        derived = derived_fields(spec)
        uses = field_uses(spec)
        loose = "*pivot*" in derived
        for name, where in sorted(uses.items()):
            if name in known or name in derived or loose or name.startswith(("bd_", "_")):
                continue
            base = re.sub(r"^(?:%s)_" % "|".join(OPS), "", name)
            base = re.sub(r"_(?:start|end|bin_maxbins_\d+|range)$", "", base)
            if base in known or base in derived or re.sub(r"^(?:year|quarter|month|week|day|date|hours|minutes|seconds|yearmonth|yearquarter|yearmonthdate|monthdate)+_", "", base) in known:
                continue
            near = [k for k in dataset if k.casefold() == name.casefold() or deneb.encode(name) == k]
            add("ERROR", "F1", f"field '{name}' ({where}) is not in the dataset and no transform creates it"
                               + (f"; the dataset key is '{near[0]}'" if near else f"; dataset: {', '.join(dataset)}"))
        text_blob = "\n".join(v for _, _, v in texts)
        for k in dataset:
            named = re.search(r"[\"'.]" + re.escape(k) + r"(?![\w])", text_blob)
            if k not in uses and not named:
                add("WARNING", "F2", f"dataset field '{k}' is never used: a grouping column that is not shown still "
                                     f"splits the rows, a measure costs a query; remove it from the visual")

    # ---- X: interaction
    selection, tooltip = interaction.get("crossFilter"), interaction.get("tooltip", True)
    uses_selected = any("__selected__" in v for _, _, v in texts)
    advanced = "pbiCrossFilterApply" in calls
    if selection:
        if not uses_selected:
            add("WARNING", "X1", "cross-filtering is on but nothing reads __selected__: a click gives no feedback; fade "
                                 "rows with __selected__ == 'off' (opacity 0.3)")
        if advanced and "pbiCrossFilterClear" not in calls:
            add("WARNING", "X2", "pbiCrossFilterApply without pbiCrossFilterClear: add a click on the empty area that "
                                 "clears the selection")
        if not advanced:
            agg = sorted({_vl_transform_kind(t) for path, t in _transforms(spec)
                          if _vl_transform_kind(t) in AGGREGATING and (provider == "vega" or not path)})
            if provider == "vegaLite":
                for path, key, value in ex.walk(spec):
                    if key == "encoding" and isinstance(value, dict):
                        for ch, d in value.items():
                            for one in (d if isinstance(d, list) else [d]):
                                if isinstance(one, dict) and (one.get("aggregate") or one.get("bin")) and ch not in ("tooltip",):
                                    agg.append(f"encoding.{ch}")
            if agg:
                add("NOTE", "X3", f"cross-filtering is on and marks are built from aggregated rows ({', '.join(sorted(set(agg)))}): "
                                  f"they carry no __row__, so Deneb matches a click by the values of the fields the "
                                  f"mark still has and selects every row with them; a mark that keeps no dataset "
                                  f"field selects nothing, and __selected__ is not on aggregated rows")
    elif uses_selected and not generated:
        add("NOTE", "X4", "the specification reads __selected__ but cross-filtering is off in the brief")
    composite = any(key == "type" and v in ("boxplot", "errorbar", "errorband") for _, key, v in ex.walk(spec)) \
        or spec.get("mark") in ("boxplot", "errorbar", "errorband")
    if tooltip and not composite and not any(key == "tooltip" for _, key, _ in ex.walk(spec)):
        add("WARNING", "X5", "no tooltip anywhere: set mark.tooltip (Vega-Lite) or a tooltip in encode (Vega) so that "
                             "people can read exact values")

    # ---- B: brand, read from the text
    foreign = {}
    for path, key, v in texts:
        if key in COLOR_KEYS or (key == "value" and any(p in COLOR_KEYS for p in path)):
            word = v.strip().casefold()
            if word in CSS_COLORS and not brand.is_token(CSS_COLORS[word]):
                foreign.setdefault(CSS_COLORS[word], []).append(f"{ex.show(path[1:])}.{key} ('{v}')")
            elif word.startswith(("hsl(", "hsla(")):
                add("WARNING", "B1", f"{v} ({ex.show(path[1:])}.{key}): write colours as the hex values of the "
                                     f"brand tokens")
        if key in ex.EXPR_KEYS:
            candidates = [s for s in ex.analyse(v)["strings"]]
        else:
            candidates = [v]
        for cand in candidates:
            for raw in ([cand] if br.norm(cand) else ex.colors_in(cand)):
                hexv = br.norm(raw)
                if hexv and not brand.is_token(hexv):
                    foreign.setdefault(hexv, []).append(f"{ex.show(path[1:])}.{key}")
        if key in ("font", "labelFont", "titleFont", "subtitleFont") and not _font_ok(v, brand):
            add("WARNING", "B2", f"font '{v}' ({ex.show(path[1:])}.{key}): the brand sets {brand.font}")
    for hexv, places in foreign.items():
        token, near = brand.nearest(hexv)
        add("WARNING", "B1", f"{hexv} is written at {len(places)} place(s) (first: {places[0]}) and is not a colour "
                             f"of the brand {brand.name}; nearest token: {token} {near}. A colour with a meaning of "
                             f"its own (a status of the business) is the user's decision: ask")
    for path, key, v in ex.walk({"spec": spec, "config": config or {}}):
        if key in ("fontSize", "labelFontSize", "titleFontSize", "subtitleFontSize") and isinstance(v, (int, float)) \
                and v not in brand.charts["fontSizesPx"]:
            add("WARNING", "B3", f"{key} {v} ({ex.show(path[1:])}): the brand scale is "
                                 f"{', '.join(map(str, brand.charts['fontSizesPx']))} px")
        if key in ("cornerRadius", "cornerRadiusEnd", "cornerRadiusTopLeft", "cornerRadiusTopRight") \
                and isinstance(v, (int, float)) and v > brand.charts["cornerRadiusMaxPx"]:
            add("WARNING", "B4", f"{key} {v} ({ex.show(path[1:])}): the brand allows at most "
                                 f"{brand.charts['cornerRadiusMaxPx']} px")
        if key == "gradient" and v in ("linear", "radial") and brand.charts["rules"].get("noGradients"):
            add("WARNING", "B5", f"gradient ({ex.show(path[1:])}): the brand uses flat colours")
        if key in ("shadowBlur", "shadowColor") and brand.charts["rules"].get("noShadows"):
            add("WARNING", "B5", f"{key} ({ex.show(path[1:])}): the brand uses no shadows")
    return order(out)


def _at(tree, path):
    node = tree
    for p in path:
        node = node[p]
    return node


def _font_ok(value: str, brand) -> bool:
    first = value.split(",")[0].strip().strip("'\"").casefold()
    allowed = {brand.font.casefold()}
    t = brand.tokens.get("typography", {})
    for v in (t.get("brandFonts") or {}).values():
        if isinstance(v, str):
            allowed.add(v.casefold())
    return first in allowed


# ================================================================== picture
def merge(groups: list) -> list:
    """Findings of several renders as one list: [(label, findings)] -> each finding once, with where it occurred."""
    seen = {}
    for label, findings in groups:
        for f in findings:
            key = (f.level, f.code, re.sub(r"\d+(?:[.,]\d+)?", "#", f.text))
            seen.setdefault(key, (f, []))[1].append(label)
    total = len(groups)
    out = []
    for (level, code, _), (f, labels) in seen.items():
        where = "all renders" if len(labels) == total and total > 1 else ", ".join(labels)
        hint = " (stress rows are extreme on purpose: judge whether the real data can get there)" \
            if all(lb.startswith("stress") for lb in labels) else ""
        out.append(Finding(level, code, f"[{where}] {f.text}{hint}"))
    return order(out)


def picture(result, brand, rows: int, size: tuple, background: str = "#FFFFFF") -> list:
    """Findings from one render (a render.Result)."""
    out = []
    add = lambda level, code, text: out.append(Finding(level, code, text))
    scene = sc.read(result.scenegraph)
    w, h = size
    ox, oy = result.origin
    texts = scene.texts()
    data_items = [i for i in scene.items if i.data and i.kind != "group"]
    visible_data = [i for i in data_items if (i.box[2] - i.box[0] > 0.5 or i.box[3] - i.box[1] > 0.5) or i.kind == "text"]

    for line in result.runtime:
        add("ERROR", "P1", f"Vega reported while running: {line}")
    if rows and not visible_data:
        add("ERROR", "P2", f"nothing is drawn from {rows} rows: check field names, filters and scales")
        return order(out)

    # ---- size
    cw, ch = result.canvas
    if cw > w + 1.5 or ch > h + 1.5:
        add("WARNING", "P3", f"the visual needs {round(cw)}×{round(ch)} px but the container has {w}×{h}: Power BI "
                             f"shows scroll bars or cuts it off; derive sizes from denebContainer or use autosize fit")
    cut = []
    for it in scene.items:
        if it.kind == "group":
            continue
        x0, y0, x1, y1 = it.box[0] + ox, it.box[1] + oy, it.box[2] + ox, it.box[3] + oy
        over = max(-x0, -y0, x1 - w, y1 - h)
        if over > 2 and it.kind == "text":
            cut.append((over, it))
    if cut:
        cut.sort(key=lambda c: -c[0])
        ex_ = "; ".join(f"'{_short(it.text)}' by {round(o)} px" for o, it in cut[:3])
        add("WARNING", "P4", f"{len(cut)} text(s) reach outside the container ({ex_}): shorten or wrap them, reserve "
                             f"room (padding, label limit) or place them inside")

    # ---- texts
    trunc = [t for t in texts if t.truncated]
    if trunc:
        roles = sorted({t.role for t in trunc})
        add("WARNING" if len(trunc) > len(texts) * 0.25 else "NOTE", "P5",
            f"{len(trunc)} text(s) are cut with an ellipsis ({', '.join(roles)}; e.g. '{_short(trunc[0].text, 40)}'): "
            f"raise the label limit, give the labels more room or shorten the names in the model")
    pairs = _overlaps(texts)
    if pairs:
        exs = "; ".join(f"'{_short(a.text)}' / '{_short(b.text)}'" for a, b in pairs[:3])
        add("WARNING", "P6", f"{len(pairs)} pair(s) of texts overlap ({exs}): fewer labels, more room, rotate or drop "
                             f"labels that do not fit")
    small = sorted({t.font_size for t in texts if t.font_size < min(brand.charts["fontSizesPx"])})
    if small:
        add("WARNING", "B3", f"text in {', '.join(f'{s:g}' for s in small)} px is drawn: below the smallest size of "
                             f"the brand scale ({min(brand.charts['fontSizesPx'])} px); set the font sizes in the config")
    off = sorted({t.font_size for t in texts if t.font_size >= min(brand.charts["fontSizesPx"])
                  and t.font_size not in brand.charts["fontSizesPx"]})
    if off:
        add("NOTE", "B3", f"text in {', '.join(f'{s:g}' for s in off)} px is drawn: not on the brand scale "
                          f"({', '.join(map(str, brand.charts['fontSizesPx']))} px)")
    fonts = sorted({t.font for t in texts if t.font and not _font_ok(t.font, brand)})
    if fonts:
        add("WARNING", "B2", f"text is drawn in {', '.join(fonts)}: the brand sets {brand.font}; set config.font")

    # ---- contrast and brand colours as drawn
    never_text = brand.tokens_in("neverAsText")
    large_only = brand.tokens_in("largeTextOnly")
    low, forbidden = {}, {}
    for t in texts:
        if not t.fill or t.fill == "gradient" or t.opacity < 0.5:
            continue
        back = sc.backdrop(scene, t, background)
        ratio = br.contrast(t.fill, back)
        large = t.font_size >= 24 or (t.font_size >= 18.5 and t.bold)
        need = 3.0 if large else 4.5
        if ratio < need:
            low.setdefault((t.fill, back), []).append((ratio, t))
        if t.fill in never_text or (t.fill in large_only and not large):
            forbidden.setdefault(t.fill, []).append(t)
    for (fill, back), items in low.items():
        ratio, t = items[0]
        better = brand.text_on(back)
        add("ERROR" if ratio < 3 else "WARNING", "P7",
            f"{len(items)} text(s) in {_name(brand, fill)} on {_name(brand, back)} have contrast {ratio:.1f}:1 "
            f"(needed {3.0 if t.font_size >= 24 or (t.font_size >= 18.5 and t.bold) else 4.5}; e.g. '{_short(t.text)}'): use {_name(brand, better)} there")
    for fill, items in forbidden.items():
        add("ERROR", "B6", f"{len(items)} text(s) in {_name(brand, fill)} (e.g. '{_short(items[0].text)}'): the brand "
                           f"does not allow this colour for text; text is {_name(brand, brand.c('text'))} or "
                           f"{_name(brand, brand.c('textSecondary'))}")
    thin = brand.tokens_in("neverAsThinMarkOnLight")
    thin_hits = {}
    for it in scene.items:
        if not it.data:
            continue      # axes, grids and legends may be weak
        if it.kind in ("line", "rule") and it.stroke in thin and it.stroke_width < 4 and br.luminance(background) > 0.6:
            thin_hits.setdefault(it.stroke, 0)
            thin_hits[it.stroke] += 1
        if it.kind == "symbol" and not it.role.startswith("legend") and (it.fill in thin or (not it.fill and it.stroke in thin)) \
                and (it.box[2] - it.box[0]) < 14 and br.luminance(sc.backdrop(scene, it, background)) > 0.6:
            key = it.fill or it.stroke
            thin_hits[key] = thin_hits.get(key, 0) + 1
    for color, n in thin_hits.items():
        add("WARNING", "B7", f"{n} thin line(s) or small marker(s) in {_name(brand, color)} on a light background: too "
                             f"weak to see; the brand keeps this colour for fills; lines take "
                             f"{', '.join(_name(brand, c) for c in brand.palette('line')[:3])}")
    signal = brand.tokens_in("signalOnly")
    area = w * h
    for it in scene.items:
        if it.kind == "rect" and it.fill in signal and (it.box[2] - it.box[0]) * (it.box[3] - it.box[1]) > area * 0.02:
            add("WARNING", "B8", f"a large area in {_name(brand, it.fill)}: signal colours are for traffic-light dots "
                                 f"and markers; fill areas with the status colours "
                                 f"({', '.join(_name(brand, brand.status(k)[0]) for k in ('success', 'warning', 'error'))})")
            break
    strange = {}
    for it in scene.items:
        for col in (it.fill, it.stroke):
            if col and col != "gradient" and not brand.is_token(col):
                strange[col] = strange.get(col, 0) + 1
    for col, n in sorted(strange.items(), key=lambda kv: -kv[1])[:6]:
        token, near = brand.nearest(col)
        add("WARNING", "B1", f"{col} is drawn {n} time(s) and is not a colour of the brand {brand.name}; nearest "
                             f"token: {token} {near} (defaults of Vega count too: set them in the config)")
    if any(it.gradient for it in scene.items) and brand.charts["rules"].get("noGradients"):
        add("WARNING", "B5", "a gradient is drawn: the brand uses flat colours")
    radius = max((it.radius for it in scene.items), default=0)
    if radius > brand.charts["cornerRadiusMaxPx"]:
        add("WARNING", "B4", f"corner radius {radius:g} px is drawn: the brand allows at most "
                             f"{brand.charts['cornerRadiusMaxPx']} px")
    legend = [i for i in scene.items if i.role == "legend-label"]
    if len(legend) > len(brand.palette("category")):
        add("WARNING", "P8", f"{len(legend)} legend entries but {len(brand.palette('category'))} category colours: "
                             f"colours repeat; group small categories or use small multiples")
    elif len(legend) > 7:
        add("NOTE", "P8", f"{len(legend)} legend entries: more than about seven colours are hard to tell apart")
    n = len([i for i in scene.items if i.kind != "group"])
    if n > 4000:
        add("WARNING", "P9", f"{n} marks are drawn: slow in the SVG renderer; reduce rows, or set renderMode canvas "
                             f"(no pattern fills there)")
    rects = [i for i in data_items if i.kind == "rect" and i.fill and i.aria == "bar"]
    tiny = [i for i in rects if min(i.box[2] - i.box[0], i.box[3] - i.box[1]) < 1.5]
    if rects and len(tiny) > len(rects) * 0.5 and len(rects) > 3:
        add("WARNING", "P10", f"{len(tiny)} of {len(rects)} bars are thinner than 1.5 px: too many rows for this size; "
                              f"filter, aggregate in a measure or make the visual larger")
    return order(out)


def _name(brand, hexv: str) -> str:
    token = brand.token_of(hexv)
    return f"{token} {hexv}" if token else hexv


def _short(text: str, n: int = 24) -> str:
    return text if len(text) <= n else text[:n - 1] + "…"


def _overlaps(texts: list) -> list:
    out = []
    items = sorted(texts, key=lambda t: t.box[0])[:3000]
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if b.box[0] >= a.box[2]:
                break
            ow, oh = sc.overlap(a.box, b.box)
            if ow > 1.5 and oh > 2.5:
                cut = [t for t in (a, b) if t.truncated]   # the width of a cut text is only known roughly
                if cut and min(ow, oh) < max(12, 0.15 * max(max(t.box[2] - t.box[0], t.box[3] - t.box[1]) for t in cut)):
                    continue
                if a.text == b.text and abs(a.box[0] - b.box[0]) < 1 and abs(a.box[1] - b.box[1]) < 1:
                    continue   # the same text twice in one place: an outline behind the text
                if a.opacity < 0.2 or b.opacity < 0.2:
                    continue
                out.append((a, b))
    return out
