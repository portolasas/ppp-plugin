"""The brief: one JSON file that says what a visual shows. Everything else is generated from it.

{
  "name": "umsatz_je_region",              file stem of all generated files
  "type": "bar",                           a type of `bideneb types`, or "custom" for a hand-written specification
  "title": "...", "subtitle": "...",       optional, drawn inside the visual
  "brand": "boehringer-ingelheim",         brand profile
  "locale": "de-DE",
  "fields": {"<role>": {"table": "T", "column": "C" | "measure": "M", "type": "...", "format": "...",
                        "label": "...", "as": "display name in the Values well"}, ...},
  "options": {...},                        per type
  "interaction": {"tooltip": true, "crossFilter": true, "highlight": false},
  "sample": {"<display name>": ["value", ...]},   invented category names for the preview
  "sizes": [[640, 360], ...],              container sizes of the preview
  "report": {"path": "../X.Report", "page": "Page name", "position": {"x":..,"y":..,"width":..,"height":..}},
  "background": "#08312A",                 optional; without it the colour of report.page, else white. A dark page
                                           draws with the dark roles of the brand (charts.json "dark")
  "colours": {"#1FBB3E": "..."}            colours outside the brand the user decided on
}"""
import json
import re
from pathlib import Path

from . import brand as br
from . import model as md
from .types import TYPES
from .types.common import BriefError, Ctx, F

NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{1,59}$")
KINDS = ("quantitative", "temporal", "nominal")
SIZES = [[640, 360], [420, 300], [1100, 520]]


def read(path: Path) -> dict:
    try:
        brief = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise BriefError(f"{path}: brief not found") from None
    except json.JSONDecodeError as ex:
        raise BriefError(f"{path}: not valid JSON ({ex})") from None
    if not isinstance(brief, dict):
        raise BriefError(f"{path}: a brief is a JSON object")
    return brief


def files(path: Path, brief: dict) -> dict:
    base = Path(path).resolve().parent
    n = brief["name"]
    return {"brief": Path(path).resolve(), "spec": base / f"{n}.json", "config": base / f"{n}.config.json",
            "data": base / f"{n}.data.json", "template": base / f"{n}.template.json",
            "preview": base / "_preview", "folder": base}


def find_model(path: Path | None, brief: dict) -> md.Model | None:
    """The semantic model the brief points to through report.path, if it can be read."""
    rep = (brief.get("report") or {}).get("path") or brief.get("project")
    if not rep or path is None:
        return None
    target = (Path(path).resolve().parent / rep).resolve()
    try:
        for p in md.locate(target):
            if p.model:
                return md.read(p.model)
    except (FileNotFoundError, OSError):
        return None
    return None


def _field(role: str, raw: dict, model: md.Model | None, problems: list) -> F | None:
    if not isinstance(raw, dict) or not raw.get("table") or not (raw.get("column") or raw.get("measure")):
        problems.append(f"fields.{role}: needs table and column or measure")
        return None
    kind = "measure" if raw.get("measure") else "column"
    name = raw.get("measure") or raw.get("column")
    ftype, fmt = raw.get("type"), raw.get("format", "")
    if model is not None:
        mf = model.find(raw["table"], name)
        if mf is None:
            near = [f.ref for f in model.search(name)]
            problems.append(f"fields.{role}: {raw['table']}[{name}] is not in the model"
                            + (f"; did you mean {', '.join(near)}?" if near else ""))
        else:
            if mf.kind != kind:
                problems.append(f"fields.{role}: {mf.ref} is a {mf.kind} in the model, the brief says {kind}")
            ftype = ftype or (mf.role if not (kind == "column" and mf.role == "quantitative" and not raw.get("type"))
                              else "quantitative")
            fmt = fmt or mf.format
    ftype = ftype or ("quantitative" if kind == "measure" else "nominal")
    if ftype not in KINDS:
        problems.append(f"fields.{role}: type {ftype!r} is not one of {', '.join(KINDS)}")
        ftype = "nominal"
    out = F(role, raw["table"], name, kind, ftype, fmt, raw.get("label", ""), raw.get("as", ""))
    out.numeric = bool(model is not None and model.find(raw["table"], name) is not None
                       and model.find(raw["table"], name).numeric)
    return out


def resolve(brief: dict, path: Path | None = None, model: md.Model | None = None) -> tuple[Ctx, object, list]:
    """Ctx, the visual type (None for custom) and the problems of the brief."""
    problems = []
    name = brief.get("name", "")
    if not NAME.match(str(name)):
        problems.append("name: lower-case letters, digits, _ and -, 2 to 60 characters (it names the files)")
    tid = brief.get("type", "")
    vtype = TYPES.get(tid)
    if vtype is None and tid != "custom":
        problems.append(f"type: {tid!r} is unknown; `bideneb types` lists the types, \"custom\" is a hand-written spec")
    try:
        brand = br.load(brief.get("brand"))
    except FileNotFoundError as ex:
        problems.append(f"brand: {ex}")
        brand = br.load("neutral")
    background, page_bg = background_of(brief, path)
    brand = brand.on(background)
    if brand.surface == "dark-missing":
        problems.append(f"brand: the profile {brand.name} has no colours for a dark page ({background}); use the "
                        f"corporate design, or a light page")
    if model is None:
        model = find_model(path, brief)
    raw_fields = brief.get("fields") or {}
    if not isinstance(raw_fields, dict) or not raw_fields:
        problems.append("fields: at least one field is needed")
        raw_fields = {}
    fields = {}
    for role, raw in raw_fields.items():
        if isinstance(raw, list):
            got = [f for f in (_field(f"{role}[{i}]", r, model, problems) for i, r in enumerate(raw)) if f]
            for f in got:
                f.role = role
            if got:
                fields[role] = got
        else:
            f = _field(role, raw, model, problems)
            if f:
                fields[role] = f
    keys = {}
    for role, v in fields.items():
        for f in (v if isinstance(v, list) else [v]):
            if "'" in f.key:
                problems.append(f"fields.{role}: the display name '{f.display}' holds an apostrophe, which Vega-Lite "
                                f"cannot address in every transform; set \"as\" to a name without it (the visual "
                                f"then shows the field under that name)")
            other = keys.setdefault(f.key, f)
            if other is not f and (other.table, other.name) != (f.table, f.name):
                problems.append(f"fields.{role}: display name '{f.display}' is used twice in the dataset "
                                f"({other.table}[{other.name}] and {f.table}[{f.name}]); set \"as\" on one of them")
    if vtype is not None:
        known = {r.name: r for r in vtype.roles}
        for r in vtype.roles:
            v = fields.get(r.name)
            if v is None:
                if r.required:
                    problems.append(f"fields.{r.name}: required by type {tid} ({r.help})")
                continue
            items = v if isinstance(v, list) else [v]
            if len(items) > 1 and not r.multiple:
                problems.append(f"fields.{r.name}: type {tid} takes one field here")
            for f in items:
                if r.only and f.kind != r.only:
                    problems.append(f"fields.{r.name}: type {tid} needs a {r.only} here, {f.table}[{f.name}] is a "
                                    f"{f.kind}")
                if f.type not in r.kinds and f.numeric and "quantitative" in r.kinds:
                    f.type = "quantitative"
                if f.type not in r.kinds:
                    problems.append(f"fields.{r.name}: {f.table}[{f.name}] is {f.type}, type {tid} needs "
                                    f"{' or '.join(r.kinds)} here")
        for role in fields:
            if role not in known:
                problems.append(f"fields.{role}: type {tid} has no such role; roles: {', '.join(known)}")
        names = {o.name: o for o in vtype.options}
        for k, v in (brief.get("options") or {}).items():
            if k not in names:
                problems.append(f"options.{k}: type {tid} has no such option; options: {', '.join(names) or 'none'}")
            elif names[k].choices and v not in names[k].choices:
                problems.append(f"options.{k}: {v!r} is not one of {', '.join(map(str, names[k].choices))}")
    ctx = Ctx(brief, brand, fields, vtype.selection if vtype is not None else True)
    ctx.background, ctx.page_background = background, page_bg
    return ctx, vtype, problems


def background_of(brief: dict, path: Path | None) -> tuple[str, str | None]:
    """(the background the visual is drawn for, the colour of its page in the report or None). The brief's
    "background" wins; without it the page of report.page decides; without both white."""
    page_bg = None
    rep = brief.get("report") or {}
    if path is not None and rep.get("path") and rep.get("page"):
        p = (Path(path).resolve().parent / rep["path"]).resolve()
        if p.suffix.casefold() == ".pbip":
            p = p.with_suffix("").parent / (p.stem + ".Report")
        if p.is_dir():
            from . import pbir
            page_bg = pbir.page_color(p, rep["page"])
    own = br.norm(brief.get("background") or "") or None
    return own or page_bg or "#FFFFFF", page_bg


def sizes(brief: dict, vtype) -> list:
    got = brief.get("sizes")
    if got:
        return [(int(w), int(h)) for w, h in got]
    if vtype is not None:
        w, h = vtype.default_size
        mw, mh = vtype.min_size
        return [(w, h), (max(mw, round(w * 0.62)), max(mh, round(h * 0.75))), (round(w * 1.75), round(h * 1.4))]
    return [tuple(s) for s in SIZES]
