"""What Deneb 2.0 does to a specification, rebuilt for a render outside Power BI.

Facts from the Deneb source (deneb-viz/deneb 2.0.1): field names are display names with \\ " . [ ] replaced by _;
every row gets __row__ (and __selected__ when cross-filtering is on); the signal denebContainer carries the size;
Vega-Lite gets width and height "container" when they are missing; pbi* expression functions and pattern fills
exist only inside Deneb and are approximated here."""
import copy
import re

from . import expr as ex

GUID = "deneb7E15AEF80B9E4D4F8E12924291ECE89A"
DENEB_VERSION = "2.0.1.0"
VEGA_VERSION = "6.4.0"
VEGALITE_VERSION = "6.4.3"
ROW_LIMIT = 30000
SELECTION_LIMIT_SIMPLE = 250
SELECTION_LIMIT_ADVANCED = 2500
PBI_FUNCTIONS = {"pbiColor", "pbiFormat", "pbiFormatAutoUnit", "pbiPatternSVG", "pbiCrossFilterApply",
                 "pbiCrossFilterClear"}
PBI_SCHEMES = {"pbiColorNominal": "category", "pbiColorOrdinal": "sequential", "pbiColorLinear": "sequential",
               "pbiColorDivergent": "diverging"}
ROW_FIELDS = {"__row__", "__selected__"}
SUPPORT_SUFFIXES = ("__highlight", "__highlightStatus", "__highlightComparator", "__format", "__formatted", "__names")
REMOVED_FIELDS = {"__identity__", "__key__"}
LEGACY_SIGNALS = {"pbiContainerWidth": "denebContainer.width", "pbiContainerHeight": "denebContainer.height"}
PATTERN = re.compile(r"url\(#((?:diagonal-stripe|horizontal-stripe|vertical-stripe|dots|circles)-\d|crosshatch|"
                     r"houndstooth)(?:-(\d{2}))?\)")


def encode(name: str) -> str:
    """The key of a field in the dataset: its display name with \\ " . [ ] replaced."""
    return re.sub(r'[\\".\[\]]', "_", name)


def provider_of(spec: dict) -> str:
    schema = str(spec.get("$schema", ""))
    if "vega-lite" in schema:
        return "vegaLite"
    if "/vega/" in schema:
        return "vega"
    if any(k in spec for k in ("mark", "layer", "encoding", "facet", "concat", "hconcat", "vconcat", "repeat")):
        return "vegaLite"
    return "vega"


# ---------------------------------------------------------------- Power BI formats
NAMED_DATES = {"general date": "%d.%m.%Y %H:%M:%S", "short date": "%d.%m.%Y", "long date": "%A, %-d. %B %Y",
               "medium date": "%d. %b %Y", "long time": "%H:%M:%S", "short time": "%H:%M", "medium time": "%H:%M"}
DATE_PARTS = [("yyyy", "%Y"), ("yy", "%y"), ("MMMM", "%B"), ("MMM", "%b"), ("MM", "%m"), ("M", "%-m"),
              ("dddd", "%A"), ("ddd", "%a"), ("dd", "%d"), ("d", "%-d"), ("HH", "%H"), ("H", "%-H"), ("hh", "%I"),
              ("h", "%-I"), ("mm", "%M"), ("m", "%-M"), ("ss", "%S"), ("s", "%-S"), ("tt", "%p")]


def pbi_format(fmt: str) -> dict:
    """A Power BI format string as {kind: number|date, d3, prefix, suffix}; an approximation for the local render."""
    fmt = (fmt or "").split(";")[0].strip()
    low = fmt.casefold()
    if low in NAMED_DATES:
        return {"kind": "date", "d3": NAMED_DATES[low], "prefix": "", "suffix": ""}
    bare = re.sub(r'"[^"]*"|\\.', "", fmt)
    if re.search(r"[yMdHhs]", bare) and not re.search(r"[0#]", bare):
        out, i = "", 0
        while i < len(fmt):
            for src, dst in DATE_PARTS:
                if fmt.startswith(src, i):
                    if src in ("mm", "m") and not re.search(r"[Hh]", fmt[:i]) and not fmt[i + len(src):].startswith(":s"):
                        dst = "%m" if src == "mm" else "%-m"   # month when no hour precedes
                    out += dst
                    i += len(src)
                    break
            else:
                out += fmt[i].replace("%", "%%")
                i += 1
        return {"kind": "date", "d3": out, "prefix": "", "suffix": ""}
    m = re.search(r"[#0][#0,.]*", bare)
    if not m:
        return {"kind": "number", "d3": ",.2~f", "prefix": "", "suffix": ""}
    core = m.group()
    literal = lambda s: re.sub(r'"([^"]*)"', r"\1", s).replace("\\", "")
    head, tail = fmt.split(core, 1) if core in fmt else ("", "")
    prefix, suffix = literal(head), literal(tail)
    whole, _, frac = core.partition(".")
    fixed, optional = frac.count("0"), frac.count("#")
    comma = "," if "," in whole else ""
    if "%" in suffix or "%" in prefix:
        d3 = f"{comma}.{fixed + optional}%"
        suffix = suffix.replace("%", "", 1)
        prefix = prefix.replace("%", "", 1)
    elif optional:
        d3 = f"{comma}.{fixed + optional}~f"
    else:
        d3 = f"{comma}.{fixed}f"
    return {"kind": "number", "d3": d3, "prefix": prefix, "suffix": suffix}


def _string_literal(src: str) -> str | None:
    src = src.strip()
    if len(src) >= 2 and src[0] in "'\"" and src[-1] == src[0]:
        return ex.unquote(src)
    return None


class Emulation:
    """Replaces what only exists inside Deneb. notes lists every approximation that was applied."""

    def __init__(self, brand):
        self.brand = brand
        self.notes = []

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def call(self, name: str, args: list[str]) -> str:
        b = self.brand
        if name in ("pbiCrossFilterApply", "pbiCrossFilterClear"):
            self.note(f"{name}: replaced by a constant; cross-filtering runs only in Power BI")
            return "0"
        if name == "pbiPatternSVG":
            self.note("pbiPatternSVG: drawn as its foreground colour")
            return args[1] if len(args) > 1 else ex.quote(b.c("grid"))
        if name == "pbiColor":
            self.note("pbiColor: colours of the brand profile stand in for the report theme")
            cat = b.palette("category")
            lit = _string_literal(args[0]) if args else None
            named = {"min": b.palette("sequential")[0], "middle": b.palette("sequential")[len(b.palette("sequential")) // 2],
                     "max": b.palette("sequential")[-1], "negative": b.c("bad"), "bad": b.c("bad"),
                     "positive": b.c("good"), "good": b.c("good"), "neutral": b.c("context")}
            if lit is not None:
                return ex.quote(named.get(lit, cat[0]))
            if args and re.fullmatch(r"\d+", args[0].strip()):
                return ex.quote(cat[int(args[0]) % len(cat)])
            arr = "[" + ", ".join(ex.quote(c) for c in cat) + "]"
            return f"{arr}[({args[0] if args else 0}) % {len(cat)}]"
        if name in ("pbiFormat", "pbiFormatAutoUnit"):
            value = args[0] if args else "null"
            lit = _string_literal(args[1]) if len(args) > 1 else None
            if name == "pbiFormatAutoUnit":
                self.note("pbiFormatAutoUnit: approximated with SI units (k, M); Power BI writes Tsd., Mio.")
                return f"(isValid({value}) ? format({value}, '.3~s') : '')"
            if lit is None:
                self.note("pbiFormat without a literal format string: shown with two optional decimals")
                return f"(isValid({value}) ? format({value}, ',.2~f') : '')"
            self.note("pbiFormat: approximated with d3 formats; check the number and date texts in Power BI")
            sections = lit.split(";")
            if len(sections) > 1 and pbi_format(sections[0])["kind"] == "number":
                pos, neg = self._one(value, sections[0]), self._one(f"abs({value})", sections[1])
                return f"(isValid({value}) ? ({value} < 0 ? {neg} : {pos}) : '')"
            return f"(isValid({value}) ? {self._one(value, lit)} : '')"
        return None

    @staticmethod
    def _one(value: str, fmt: str) -> str:
        f = pbi_format(fmt)
        body = f"{'timeFormat' if f['kind'] == 'date' else 'format'}({value}, {ex.quote(f['d3'])})"
        if f["prefix"]:
            body = f"{ex.quote(f['prefix'])} + {body}"
        if f["suffix"]:
            body = f"{body} + {ex.quote(f['suffix'])}"
        return f"({body})"

    def expression(self, text: str) -> str:
        for old, new in LEGACY_SIGNALS.items():
            text = re.sub(rf"\b{old}\b", new, text)
        text = re.sub(r"\bpbiContainer\b", "denebContainer", text)
        if not any(fn in text for fn in PBI_FUNCTIONS):
            return text
        return ex.rewrite_calls(text, PBI_FUNCTIONS, self.call)

    def schemes(self, node):
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                if k == "scheme":
                    name = v.get("name") if isinstance(v, dict) else v
                    if isinstance(name, str) and name in PBI_SCHEMES:
                        self.note(f"{name}: the palette of the brand profile stands in for the report theme")
                        colors = self.brand.palette(PBI_SCHEMES[name])
                        out[k] = colors
                        continue
                out[k] = self.schemes(v)
            return out
        if isinstance(node, list):
            return [self.schemes(v) for v in node]
        return node


# ---------------------------------------------------------------- preparing a spec for the local render
def rows_for_deneb(rows: list[dict], selection: bool = True, selected: set | None = None) -> list[dict]:
    out = []
    for i, r in enumerate(rows):
        row = {encode(k): v for k, v in r.items()}
        row["__row__"] = i
        if selection:
            row["__selected__"] = "neutral" if not selected else ("on" if i in selected else "off")
        out.append(row)
    return out


def prepare_vegalite(spec: dict, rows: list[dict], width: int, height: int) -> dict:
    """Vega-Lite as Deneb hands it to the compiler: dataset, container size, denebContainer as parameter."""
    spec = copy.deepcopy(spec)
    spec.pop("usermeta", None)
    spec.setdefault("datasets", {})["dataset"] = rows
    container = {"width": width, "height": height, "scrollWidth": width, "scrollHeight": height,
                 "scrollTop": 0, "scrollLeft": 0}
    params = [p for p in spec.get("params", []) if p.get("name") != "denebContainer"]
    spec["params"] = [{"name": "denebContainer", "value": container}] + params
    composed = any(k in spec for k in ("concat", "hconcat", "vconcat", "facet"))
    if not composed:
        fitted = []
        for key, value in (("width", width), ("height", height)):
            if spec.get(key) in (None, "container"):   # Deneb sets "container"; Vega-Lite then fits this dimension
                spec[key] = value
                fitted.append(key)
        if "autosize" not in spec and fitted:
            kind = "fit" if len(fitted) == 2 else "fit-x" if fitted == ["width"] else "fit-y"
            spec["autosize"] = {"type": kind, "contains": "padding"}
    spec.setdefault("config", {})
    spec["config"].setdefault("customFormatTypes", True)
    spec["config"]["background"] = "transparent"
    return spec


def prepare_vega(spec: dict, rows: list[dict] | None, width: int, height: int) -> dict:
    """Vega as Deneb runs it: dataset values, denebContainer signal, width and height when the spec has none."""
    spec = copy.deepcopy(spec)
    spec.pop("usermeta", None)
    container = {"width": width, "height": height, "scrollWidth": width, "scrollHeight": height,
                 "scrollTop": 0, "scrollLeft": 0}
    signals = [s for s in spec.get("signals", []) if s.get("name") != "denebContainer"]
    names = {s.get("name") for s in signals}
    spec["signals"] = [{"name": "denebContainer", "value": container}] + signals
    if rows is not None:
        data = spec.setdefault("data", [])
        for d in data:
            if d.get("name") == "dataset":
                d.pop("url", None)
                d["values"] = rows
                break
        else:
            data.insert(0, {"name": "dataset", "values": rows})
    for key, value in (("width", width), ("height", height)):
        if key not in spec and key not in names:
            spec[key] = value
    return spec


def emulate(vega: dict, brand) -> tuple[dict, list[str]]:
    """A Vega spec without Deneb-only functions and schemes, and the notes on what was approximated."""
    em = Emulation(brand)
    out = ex.map_expressions(em.schemes(vega), em.expression)
    return out, em.notes


# ---------------------------------------------------------------- pattern fills
def pattern_defs(svg: str, fg: str = "#666666") -> str:
    """Add simple <pattern> definitions for the Deneb pattern ids an SVG refers to."""
    ids = {m.group(0)[5:-1]: m.group(1) for m in PATTERN.finditer(svg)}
    if not ids:
        return svg
    defs = []
    for full, base in sorted(ids.items()):
        kind = base.rsplit("-", 1)[0] if base[-1].isdigit() else base
        weight = int(base[-1]) if base[-1].isdigit() else 2
        w = max(0.6, weight * 0.6)
        if kind == "diagonal-stripe":
            body = (f'<path d="M-2,2 l4,-4 M0,10 l10,-10 M8,12 l4,-4" stroke="{fg}" stroke-width="{w}"/>')
        elif kind == "horizontal-stripe":
            body = f'<rect x="0" y="0" width="10" height="{w}" fill="{fg}"/>'
        elif kind == "vertical-stripe":
            body = f'<rect x="0" y="0" width="{w}" height="10" fill="{fg}"/>'
        elif kind in ("dots", "circles"):
            fill = fg if kind == "dots" else "none"
            body = f'<circle cx="5" cy="5" r="{min(4, weight * 0.5 + 0.5)}" fill="{fill}" stroke="{fg}"/>'
        else:
            body = f'<path d="M0,0 l10,10 M10,0 l-10,10" stroke="{fg}" stroke-width="1"/>'
        defs.append(f'<pattern id="{full}" patternUnits="userSpaceOnUse" width="10" height="10">{body}</pattern>')
    block = "<defs>" + "".join(defs) + "</defs>"
    i = svg.find(">", svg.find("<svg")) + 1
    return svg[:i] + block + svg[i:]
