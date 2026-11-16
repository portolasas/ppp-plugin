"""The Deneb visual inside a Power BI project (PBIR): write it, read it back, check it.

Format of visual.json as Power BI Desktop saved it for Deneb 2.0.1 (observed) and as the Deneb source reads it:
text literals in single quotes with ' doubled, booleans bare, numbers with the suffix D; the specification is one
text literal; fields are projections of the one data role "dataset"; report.json lists the visual in
publicCustomVisuals."""
import datetime as dt
import hashlib
import json
import re
import uuid
from pathlib import Path

from . import deneb
from . import expr as ex
from .checks import Finding, order

SCHEMA_BASE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
VISUAL_SCHEMA_FALLBACK = "2.4.0"
PAGE_SCHEMA_FALLBACK = "2.0.0"
TEMPLATE_SCHEMA = "https://deneb-viz.github.io/schema/deneb-template-usermeta-v2.json"


class PbirError(Exception):
    pass


# ---------------------------------------------------------------- literals
def literal(value) -> dict:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (int, float)):
        text = f"{value:g}D"
    else:
        text = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": text}}}


def unliteral(node):
    """The Python value of a PBIR literal, or None when the node is not a literal."""
    try:
        text = node["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return None
    if text in ("true", "false"):
        return text == "true"
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1].replace("''", "'")
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)[DLM]?", text)
    if m:
        f = float(m.group(1))
        return int(f) if f.is_integer() else f
    return text


def literal_problem(node, kind: str) -> str | None:
    """What is wrong with the form of a literal: kind is text, bool or number."""
    try:
        text = node["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return "is not a literal ({\"expr\": {\"Literal\": {\"Value\": …}}})"
    if not isinstance(text, str):
        return "Value must be a string"
    if kind == "text" and not (len(text) >= 2 and text[0] == "'" and text[-1] == "'"):
        return "text must stand in single quotes inside Value"
    if kind == "bool" and text not in ("true", "false"):
        return "a boolean is true or false without quotes"
    if kind == "number" and not re.fullmatch(r"-?\d+(\.\d+)?D", text):
        return "a number ends with D (50D)"
    return None


# ---------------------------------------------------------------- files
def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _newline(report: Path) -> str:
    try:
        raw = (report / "definition" / "report.json").read_bytes()
    except OSError:
        return "\n"
    return "\r\n" if b"\r\n" in raw else "\n"


def _write(path: Path, data, newline: str) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))


def definition(report: Path) -> Path:
    d = report / "definition"
    if not (d / "report.json").is_file():
        raise PbirError(f"{report}: no definition/report.json; the report must be saved in the PBIR format "
                        f"(Power BI project, enhanced report format)")
    return d


def pages(report: Path) -> list[dict]:
    """Pages in their order: {name, displayName, path, width, height}."""
    d = definition(report) / "pages"
    out = []
    order_ = []
    if (d / "pages.json").is_file():
        order_ = _read(d / "pages.json").get("pageOrder", [])
    found = {}
    for p in sorted(d.glob("*/page.json")):
        data = _read(p)
        found[data.get("name", p.parent.name)] = {"name": data.get("name", p.parent.name),
                                                  "displayName": data.get("displayName", ""), "path": p.parent,
                                                  "width": data.get("width", 1280), "height": data.get("height", 720)}
    for n in order_:
        if n in found:
            out.append(found.pop(n))
    return out + list(found.values())


def find_page(report: Path, wanted: str) -> dict:
    ps = pages(report)
    hits = [p for p in ps if wanted in (p["name"], p["displayName"])] or \
        [p for p in ps if p["displayName"].casefold() == wanted.casefold()]
    if len(hits) != 1:
        names = ", ".join(f"'{p['displayName']}'" for p in ps)
        raise PbirError(f"page '{wanted}' {'is ambiguous' if hits else 'not found'} in {report.name}; pages: {names}")
    return hits[0]


def _schema_of(report: Path, kind: str, fallback: str) -> str:
    pattern = "pages/*/visuals/*/visual.json" if kind == "visualContainer" else "pages/*/page.json"
    for p in sorted(definition(report).glob(pattern)):
        try:
            s = _read(p).get("$schema", "")
        except (OSError, json.JSONDecodeError):
            continue
        if f"/{kind}/" in s:
            return s
    return f"{SCHEMA_BASE}{kind}/{fallback}/schema.json"


def new_page(report: Path, display: str) -> dict:
    d = definition(report) / "pages"
    name = "p" + hashlib.sha1(display.encode("utf-8")).hexdigest()[:19]
    if (d / name).exists():
        raise PbirError(f"a page '{display}' was already created ({name})")
    nl = _newline(report)
    page = {"$schema": _schema_of(report, "page", PAGE_SCHEMA_FALLBACK), "name": name, "displayName": display,
            "displayOption": "FitToPage", "height": 720, "width": 1280}
    _write(d / name / "page.json", page, nl)
    meta_path = d / "pages.json"
    if meta_path.is_file():
        meta = _read(meta_path)
        meta.setdefault("pageOrder", []).append(name)
        _write(meta_path, meta, nl)
    return {"name": name, "displayName": display, "path": d / name, "width": 1280, "height": 720}


def visual_name(brief_name: str) -> str:
    return ("deneb_" + re.sub(r"[^A-Za-z0-9_-]", "", brief_name))[:50]


# ---------------------------------------------------------------- text of the specification
def spec_text(spec: dict) -> str:
    """The specification as it goes into the report: without $schema and usermeta, readable in the Deneb editor."""
    body = {k: v for k, v in spec.items() if k not in ("$schema", "usermeta")}
    return json.dumps(body, indent=2, ensure_ascii=False)


def same_spec(a: str, b: str) -> bool:
    try:
        x, y = ex.loads(a), ex.loads(b)
    except (json.JSONDecodeError, ValueError):
        return False
    strip = lambda d: {k: v for k, v in d.items() if k not in ("$schema", "usermeta")} if isinstance(d, dict) else d
    return strip(x) == strip(y)


def state_sha(spec, config) -> str:
    """One value for specification and config, to see whether the report or the files changed since the last sync."""
    strip = lambda d: {k: v for k, v in d.items() if k not in ("$schema", "usermeta")} if isinstance(d, dict) else d
    spec = strip(ex.loads(spec) if isinstance(spec, str) else spec)
    config = ex.loads(config) if isinstance(config, str) else (config or {})
    text = json.dumps([spec, config], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def plain(p: dict) -> bool:
    """Whether a projection is a column or a measure, the two kinds bideneb writes."""
    f = p.get("field", {})
    return isinstance(f, dict) and len(f) == 1 and ("Column" in f or "Measure" in f)


def boxes(page: dict, skip: str = "") -> list:
    out = []
    for other in sorted(page["path"].glob("visuals/*/visual.json")):
        try:
            data = _read(other)
        except (OSError, json.JSONDecodeError):
            continue
        pos = data.get("position", {})
        if data.get("name") != skip and pos.get("width") and pos.get("height") and not data.get("isHidden"):
            out.append((pos.get("x", 0), pos.get("y", 0), pos.get("x", 0) + pos["width"], pos.get("y", 0) + pos["height"],
                        data.get("name", other.parent.name)))
    return out


def dangling(page: dict) -> list:
    """References on a page that point at no visual of the page: a parentGroupName (Desktop drops such a visual when
    it saves, as happened to slicers copied from another page) and visualInteractions of page.json."""
    names, parents = set(), []
    for other in sorted(page["path"].glob("visuals/*/visual.json")):
        try:
            data = _read(other)
        except (OSError, json.JSONDecodeError):
            continue
        names.add(data.get("name", other.parent.name))
        if data.get("parentGroupName"):
            parents.append((data.get("name", other.parent.name), data["parentGroupName"]))
    out = [f"visual {n} belongs to group {g}, which is not on the page: Desktop removes the visual when it saves; "
           f"remove parentGroupName or copy the group with it" for n, g in parents if g not in names]
    try:
        inter = _read(page["path"] / "page.json").get("visualInteractions") or []
    except (OSError, json.JSONDecodeError):
        inter = []
    missing = sorted({x.get(k) for x in inter for k in ("source", "target") if x.get(k) and x.get(k) not in names})
    if missing:
        out.append(f"page.json visualInteractions name visual(s) that are not on the page ({', '.join(missing)}): "
                   f"rename them to the visual that replaced them, or remove the entries")
    return out


def overlapping(pos: dict, others: list) -> list:
    x0, y0, x1, y1 = pos.get("x", 0), pos.get("y", 0), pos.get("x", 0) + pos.get("width", 0), pos.get("y", 0) + pos.get("height", 0)
    return [o[4] for o in others if min(x1, o[2]) - max(x0, o[0]) > 8 and min(y1, o[3]) - max(y0, o[1]) > 8]


def free_spot(page: dict, w: int, h: int) -> tuple | None:
    """The first place on the page where a w by h visual touches no other visual."""
    others = boxes(page)
    for y in range(24, max(25, int(page["height"]) - h - 23), 24):
        for x in range(24, max(25, int(page["width"]) - w - 23), 24):
            if not overlapping({"x": x - 16, "y": y - 16, "width": w + 32, "height": h + 32}, others):
                return x, y      # with a margin of 8 px to its neighbours
    return None


def projection(f) -> dict:
    kind = "Measure" if f.kind == "measure" else "Column"
    p = {"field": {kind: {"Expression": {"SourceRef": {"Entity": f.table}}, "Property": f.name}},
         "queryRef": f"{f.table}.{f.name}", "nativeQueryRef": f.name}
    if f.display != f.name:
        p["displayName"] = f.display
    return p


def projection_key(p: dict) -> str:
    return deneb.encode(p.get("displayName") or p.get("nativeQueryRef") or "")


def vega_properties(provider: str, spec: dict, config: dict, interaction: dict, render_mode: str | None = None,
                    create: bool = True) -> dict:
    """The properties bideneb owns. On an update everything else in the visual stays as Desktop left it."""
    text = spec_text(spec)
    advanced = "pbiCrossFilterApply" in text
    props = {
        "provider": literal(provider),
        "jsonSpec": literal(text),
        "jsonConfig": literal(json.dumps(config or {}, indent=2, ensure_ascii=False)),
        "enableTooltips": literal(bool(interaction.get("tooltip", True))),
        "enableSelection": literal(bool(interaction.get("crossFilter"))),
        "enableHighlight": literal(bool(interaction.get("highlight"))),
    }
    if create:
        props["renderMode"] = literal(render_mode or "svg")
        props["enableContextMenu"] = literal(True)
    elif render_mode:
        props["renderMode"] = literal(render_mode)
    if interaction.get("crossFilter"):
        limit = max(1, min(int(interaction.get("maxDataPoints", 50)),
                           deneb.SELECTION_LIMIT_ADVANCED if advanced else deneb.SELECTION_LIMIT_SIMPLE))
        props["selectionMode"] = literal("advanced" if advanced else "simple")
        props["selectionMaxDataPoints"] = literal(limit)
    return props


# ---------------------------------------------------------------- embed
def embed(report: Path, page: dict, name: str, fields: list, provider: str, spec: dict, config: dict,
          interaction: dict, position: dict | None = None, size: tuple = (640, 360), render_mode: str | None = None,
          visual: str | None = None) -> dict:
    """Write or update the visual; returns {path, created, registered}. visual: the name of an adopted visual."""
    d = definition(report)
    nl = _newline(report)
    vname = visual or visual_name(name)
    folder = vname
    if visual:
        for v in visuals(report):
            if v["name"] == visual:
                folder = v["path"].parent.name
    path = page["path"] / "visuals" / folder / "visual.json"
    projections = [projection(f) for f in fields]
    created = not path.is_file()
    props = vega_properties(provider, spec, config, interaction, render_mode, created)
    if created:
        zs = []
        for other in page["path"].glob("visuals/*/visual.json"):
            try:
                zs.append(_read(other).get("position", {}).get("z", 0))
            except (OSError, json.JSONDecodeError):
                pass
        z = (max(zs) if zs else 0) + 1000
        w, h = min(size[0], page["width"] - 48), min(size[1], page["height"] - 48)
        spot = free_spot(page, w, h) if not position else None
        if spot is None and not position and boxes(page):
            raise PbirError(f"page '{page['displayName']}' has no free place for a {w}x{h} visual: pass --position "
                            f"x,y,width,height (it may lie over others), or --new-page <name>")
        pos = {"x": spot[0] if spot else 24, "y": spot[1] if spot else 24, "z": z, "height": h, "width": w,
               "tabOrder": z}
        pos.update({k: v for k, v in (position or {}).items() if k in ("x", "y", "width", "height")})
        visual = {"$schema": _schema_of(report, "visualContainer", VISUAL_SCHEMA_FALLBACK), "name": vname,
                  "position": pos,
                  "visual": {"visualType": deneb.GUID,
                             "query": {"queryState": {"dataset": {"projections": projections}}},
                             "objects": {"vega": [{"properties": props}],
                                         "stateManagement": [{"properties": {"denebMetaVersion": literal("2")}}]},
                             "drillFilterOtherVisuals": True}}
    else:
        visual = _read(path)
        v = visual.setdefault("visual", {})
        if v.get("visualType") != deneb.GUID:
            raise PbirError(f"{path}: holds a visual of type {v.get('visualType')}, not Deneb; choose another name")
        before = v.get("query", {}).get("queryState", {}).get("dataset", {}).get("projections", [])
        foreign = [p.get("queryRef") or p.get("nativeQueryRef") or "?" for p in before if not plain(p)]
        if foreign:
            raise PbirError(f"{path.parent.name}: the visual has field(s) bideneb cannot write ({', '.join(foreign)}: "
                            f"an implicit aggregation or a hierarchy); replace them by measures or columns in "
                            f"Desktop, then pull")
        old = [projection_key(p) for p in before]
        v.setdefault("query", {}).setdefault("queryState", {})["dataset"] = {"projections": projections}
        objects = v.setdefault("objects", {})
        vega = objects.setdefault("vega", [{"properties": {}}])
        vega[0]["properties"] = {**vega[0].get("properties", {}), **props}
        if not interaction.get("crossFilter"):
            for k in ("selectionMode", "selectionMaxDataPoints"):
                vega[0]["properties"].pop(k, None)
        state = objects.setdefault("stateManagement", [{"properties": {}}])[0].setdefault("properties", {})
        state["denebMetaVersion"] = literal("2")
        if old != [projection_key(p) for p in projections]:
            state.pop("supportFieldConfiguration", None)
        if position:
            visual.setdefault("position", {}).update(
                {k: val for k, val in position.items() if k in ("x", "y", "width", "height")})
    _write(path, visual, nl)
    rpath = d / "report.json"
    rep = _read(rpath)
    registered = False
    if deneb.GUID not in rep.get("publicCustomVisuals", []):
        rep.setdefault("publicCustomVisuals", []).append(deneb.GUID)
        _write(rpath, rep, nl)
        registered = True
    return {"path": path, "created": created, "registered": registered}


# ---------------------------------------------------------------- read back
def visuals(report: Path) -> list[dict]:
    """Every Deneb visual of the report: {page, pageName, name, path, provider, spec, config, keys, selection ...}."""
    out = []
    for pg in pages(report):
        for path in sorted(pg["path"].glob("visuals/*/visual.json")):
            try:
                data = _read(path)
            except (OSError, json.JSONDecodeError):
                continue
            v = data.get("visual", {})
            if not str(v.get("visualType", "")).endswith(deneb.GUID):
                continue
            props = (v.get("objects", {}).get("vega") or [{}])[0].get("properties", {})
            proj = v.get("query", {}).get("queryState", {}).get("dataset", {}).get("projections", [])
            out.append({"page": pg["displayName"], "pageName": pg["name"], "name": data.get("name", path.parent.name),
                        "path": path, "data": data, "properties": props,
                        "provider": unliteral(props.get("provider")) or "vegaLite",
                        "spec": unliteral(props.get("jsonSpec")) or "{}",
                        "config": unliteral(props.get("jsonConfig")) or "{}",
                        "keys": [projection_key(p) for p in proj], "projections": proj,
                        "selection": bool(unliteral(props.get("enableSelection"))),
                        "position": data.get("position", {})})
    return out


def find_visual(report: Path, name: str) -> dict | None:
    wanted = visual_name(name)
    for v in visuals(report):
        if v["name"] in (wanted, name):
            return v
    return None


# ---------------------------------------------------------------- check
def verify(report: Path, name: str, fields: list, spec: dict | None, config: dict | None, interaction: dict) -> list:
    """Findings about the visual as it stands in the report (codes R…)."""
    out = []
    add = lambda level, code, text: out.append(Finding(level, code, text))
    try:
        v = find_visual(report, name)
    except PbirError as err:
        return [Finding("ERROR", "R0", str(err))]
    if v is None:
        return [Finding("NOTE", "R0", f"not in the report {report.name} yet; `bideneb embed` writes it")]
    where = f"{v['page']} › {v['name']}"
    rep = _read(definition(report) / "report.json")
    if deneb.GUID not in rep.get("publicCustomVisuals", []):
        add("ERROR", "R1", f"report.json does not list {deneb.GUID} in publicCustomVisuals: Desktop shows \"Can't "
                           f"display this visual\"; `bideneb embed` adds it")
    props = v["properties"]
    forms = {"provider": "text", "jsonSpec": "text", "jsonConfig": "text", "renderMode": "text",
             "selectionMode": "text", "enableTooltips": "bool", "enableContextMenu": "bool", "enableSelection": "bool",
             "enableHighlight": "bool", "selectionMaxDataPoints": "number"}
    for key, kind in forms.items():
        if key in props:
            problem = literal_problem(props[key], kind)
            if problem:
                add("ERROR", "R2", f"{where}: vega.{key} {problem}; Deneb ignores a property in the wrong form")
    for key in ("provider", "jsonSpec"):
        if key not in props:
            add("ERROR", "R2", f"{where}: vega.{key} is missing")
    if v["provider"] not in ("vega", "vegaLite"):
        add("ERROR", "R2", f"{where}: provider '{v['provider']}' is neither vega nor vegaLite")
    try:
        embedded = ex.loads(v["spec"])
    except (json.JSONDecodeError, ValueError) as err:
        add("ERROR", "R3", f"{where}: jsonSpec is not valid JSON ({err})")
        embedded = None
    try:
        ex.loads(v["config"])
    except (json.JSONDecodeError, ValueError) as err:
        add("ERROR", "R3", f"{where}: jsonConfig is not valid JSON ({err})")
    state = (v["data"].get("visual", {}).get("objects", {}).get("stateManagement") or [{}])[0].get("properties", {})
    if unliteral(state.get("denebMetaVersion")) != "2":
        add("WARNING", "R4", f"{where}: stateManagement.denebMetaVersion is not '2': Deneb 2 treats the visual as a "
                             f"legacy one and adds __format and __formatted fields to every measure")
    want = [f.key for f in fields]
    have = v["keys"]
    for k in want:
        if k not in have:
            add("ERROR", "R5", f"{where}: the brief has the field '{k}' but the visual does not project it; "
                               f"`bideneb embed` writes the projections")
    for k in have:
        if k not in want:
            add("WARNING", "R5", f"{where}: the visual projects '{k}', which the brief does not know: it changes the "
                                 f"rows of the dataset; add it to the brief or remove it in Desktop")
    for p in v["projections"]:
        ref = p.get("queryRef", "")
        f = p.get("field", {})
        node = f.get("Column") or f.get("Measure") or {}
        ent = (node.get("Expression", {}).get("SourceRef", {}) or {}).get("Entity")
        if ent and node.get("Property") and ref != f"{ent}.{node['Property']}" and "Aggregation" not in f:
            add("WARNING", "R5", f"{where}: queryRef '{ref}' does not match {ent}.{node['Property']}")
    if spec is not None and embedded is not None and not same_spec(json.dumps(spec), v["spec"]):
        add("WARNING", "R6", f"{where}: the specification in the report differs from the file: `bideneb embed` "
                             f"writes the file into the report, `bideneb pull` takes the version of the report "
                             f"(after changes in the Deneb editor)")
    if config is not None:
        try:
            if ex.loads(v["config"]) != config:
                add("WARNING", "R6", f"{where}: the config in the report differs from the file (embed or pull)")
        except (json.JSONDecodeError, ValueError):
            pass
    if bool(interaction.get("crossFilter")) != v["selection"]:
        add("WARNING", "R7", f"{where}: enableSelection is {str(v['selection']).lower()} in the report, the brief says "
                             f"crossFilter {str(bool(interaction.get('crossFilter'))).lower()}")
    if embedded is not None and "pbiCrossFilterApply" in v["spec"] and unliteral(props.get("selectionMode")) != "advanced":
        add("ERROR", "R7", f"{where}: the specification calls pbiCrossFilterApply but selectionMode is not 'advanced'")
    pos = v["position"]
    if pos.get("width", 999) < 120 or pos.get("height", 999) < 60:
        add("WARNING", "R8", f"{where}: the visual is {pos.get('width')}×{pos.get('height')} px on the page")
    page = next((p for p in pages(report) if p["name"] == v["pageName"]), None)
    if page is not None:
        over = overlapping(pos, boxes(page, v["name"]))
        if over:
            add("WARNING", "R9", f"{where}: lies over {len(over)} other visual(s) of the page ({', '.join(over[:4])}): "
                                 f"move it in Desktop, or embed with --position x,y,width,height")
        for text in dangling(page):
            add("WARNING", "R10", f"page {page['displayName'] or page['name']}: {text}")
    odd = [p.get("queryRef") or "?" for p in v["projections"] if not plain(p)]
    if odd:
        add("WARNING", "R5", f"{where}: field(s) with an implicit aggregation or a hierarchy ({', '.join(odd)}): their "
                             f"name in the dataset depends on the language of Desktop, and bideneb cannot write "
                             f"them; use measures")
    return order(out)


# ---------------------------------------------------------------- Deneb template (import by hand)
def template(name: str, description: str, fields: list, provider: str, spec: dict, config: dict,
             interaction: dict) -> dict:
    """The specification as a Deneb template: fields become placeholders the user assigns when importing."""
    text = spec_text(spec)
    datasets = []
    for i, f in enumerate(sorted(fields, key=lambda f: -len(f.key))):
        ph = f"__dataset.{i}__"
        key = json.dumps(f.key, ensure_ascii=False)[1:-1]
        text = text.replace(f'"{key}"', f'"{ph}"')
        text = text.replace(f"['{key}']", f"['{ph}']").replace(f'[\\"{key}\\"]', f'[\\"{ph}\\"]')
        if f.key.isidentifier():
            text = re.sub(rf"\bdatum\.{re.escape(f.key)}\b", f"datum['{ph}']", text)
        datasets.append({"key": ph, "name": f.label, "description": f"{f.table}[{f.name}]",
                         "kind": "measure" if f.kind == "measure" else "column",
                         "type": {"quantitative": "numeric", "temporal": "dateTime"}.get(f.type, "text")})
    out = json.loads(text)
    out["usermeta"] = {
        "deneb": {"build": deneb.DENEB_VERSION, "metaVersion": 2, "provider": provider,
                  "providerVersion": deneb.VEGALITE_VERSION if provider == "vegaLite" else deneb.VEGA_VERSION},
        "information": {"name": name[:100], "description": (description or name)[:300], "author": "bideneb",
                        "uuid": str(uuid.uuid4()),
                        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")},
        "datasets": {"dataset": datasets},
        "interactivity": {"tooltip": bool(interaction.get("tooltip", True)), "contextMenu": True,
                          "selection": bool(interaction.get("crossFilter")), "highlight": bool(interaction.get("highlight")),
                          "dataPointLimit": int(interaction.get("maxDataPoints", 50))},
        "config": json.dumps(config or {}, indent=2, ensure_ascii=False)}
    return out
