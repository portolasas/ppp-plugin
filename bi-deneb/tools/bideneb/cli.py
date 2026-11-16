"""Command line of bideneb. Every command prints what it did, what it found and what comes next."""
import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from . import __version__, brand as br, brief as bf, checks, deneb, expr as ex, model as md, pbir, render, sample
from .types import TYPES
from .types.common import VEGA_SCHEMA, VL_SCHEMA, BriefError, base_config

FIELD = re.compile(r"^(?:(?P<kind>[cmdn]):)?(?P<table>.+?)\[(?P<name>.+)\]$")
SIZE = re.compile(r"^(\d{2,4})x(\d{2,4})$")
UNPROVEN = [
    "the render uses Vega {vega} and Vega-Lite {vl}; Deneb {deneb} runs Vega {dvega} and Vega-Lite {dvl}",
    "numbers and dates of pbiFormat are approximated; Power BI formats them with the format string and locale of the report",
    "rows are invented: real row counts, empty values, long names and the grain of the dataset show only in Power BI",
    "tooltips, cross-filtering, highlighting and the context menu run only in Power BI",
    "whether Desktop accepts the visual and how the measures evaluate in the filter context",
]


class Fail(Exception):
    pass


def say(text: str = "") -> None:
    print(text)


# ---------------------------------------------------------------- loading
def brief_path(arg: str) -> Path:
    p = Path(arg)
    if p.is_dir():
        found = sorted(p.glob("*.brief.json"))
        if len(found) != 1:
            raise Fail(f"{p}: {'no' if not found else 'several'} *.brief.json; name the brief")
        return found[0]
    if p.is_file():
        return p
    for cand in (p.with_name(p.name + ".brief.json"), Path("deneb") / f"{p.name}.brief.json"):
        if cand.is_file():
            return cand
    if p.parent == Path("."):
        found = [f for pattern in ("*/deneb", "*/*/deneb", "*/*/*/deneb") for f in Path(".").glob(f"{pattern}/{p.name}.brief.json")]
        if len(found) == 1:
            return found[0]
        if found:
            raise Fail(f"{arg}: several briefs with that name; give the path: " + ", ".join(map(str, found)))
    raise Fail(f"{arg}: brief not found. Give the path to <name>.brief.json or its folder, or call bideneb from "
               f"the folder that holds deneb/ (the folder of the .pbip)")


def load(arg: str):
    path = brief_path(arg)
    brief = bf.read(path)
    ctx, vtype, problems = bf.resolve(brief, path)
    if problems:
        raise Fail("the brief has problems:\n  " + "\n  ".join(problems))
    return path, brief, ctx, vtype, bf.files(path, brief)


def sha(spec: dict) -> str:
    body = {k: v for k, v in spec.items() if k != "usermeta"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def read_spec(files: dict) -> tuple[dict, dict]:
    if not files["spec"].is_file():
        raise Fail(f"{files['spec'].name} is missing; `bideneb build` writes it")
    try:
        spec = ex.loads(files["spec"].read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, ValueError) as err:
        raise Fail(f"{files['spec'].name}: not valid JSON ({err})") from None
    config = {}
    if files["config"].is_file():
        try:
            config = ex.loads(files["config"].read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, ValueError) as err:
            raise Fail(f"{files['config'].name}: not valid JSON ({err})") from None
    return spec, config


def edited(spec: dict) -> bool:
    """Whether a generated specification was changed by hand since bideneb wrote it."""
    meta = (spec.get("usermeta") or {}).get("bideneb") or {}
    return bool(meta.get("sha")) and meta["sha"] != sha(spec)


def report_of(path: Path, brief: dict, arg: str | None = None) -> Path | None:
    rel = arg or (brief.get("report") or {}).get("path")
    if rel:
        p = Path(rel) if arg else (path.parent / rel)
        p = p.resolve()
        if p.suffix.casefold() == ".pbip":
            p = p.with_suffix("").parent / (p.stem + ".Report")
        if not p.is_dir():
            raise Fail(f"report {p} not found")
        return p
    return None


def nearby_reports(folder: Path) -> list[Path]:
    out = []
    for base in (folder, folder.parent, folder.parent.parent):
        if base.is_dir():
            out += [p for p in sorted(base.glob("*.Report")) if p.is_dir() and p not in out]
        if out:
            break
    return out


def rows_for(ctx, vtype, files: dict, scenario: str) -> list[dict]:
    if files["data"].is_file():   # own invented rows: a list (typical) or {"typical": [...], "stress": [...]}
        data = json.loads(files["data"].read_text(encoding="utf-8-sig"))
        if isinstance(data, dict) and isinstance(data.get(scenario), list):
            return data[scenario]
        if isinstance(data, list) and scenario == "typical":
            return data
    if vtype is not None:
        return sample.rows(ctx, vtype, scenario)
    import random
    return sample.generic(ctx, scenario, random.Random(f"{ctx.brief['name']}|{scenario}"))


# ---------------------------------------------------------------- check and render
def examine(ctx, vtype, spec, config, files, sizes, scenarios, pictures=True, background="#FFFFFF"):
    """Static findings, picture findings, written pictures and emulation notes."""
    keys = [f.key for f in ctx.all()]
    static = checks.static(spec, config, ctx.brand, keys, ctx.interaction,
                           render_mode=ctx.brief.get("renderMode", "svg"),
                           generated=vtype is not None and not edited(spec))
    groups, written, notes, frames = [], [], [], []
    if not pictures or checks.worst(static) == "ERROR" and any(f.code in ("D1",) for f in static):
        return static, [], written, notes
    if render.available() is None:
        return static + [checks.Finding("WARNING", "P0", "not rendered: vl-convert-python is not installed "
                                                        "(`bideneb setup`); only the static rules ran")], [], written, notes
    files["preview"].mkdir(parents=True, exist_ok=True)
    name = ctx.brief["name"]
    for sc in scenarios:
        rows = deneb.rows_for_deneb(rows_for(ctx, vtype, files, sc), ctx.select)
        for (w, h) in sizes:
            label = f"{sc} {w}x{h}"
            try:
                res = render.render(spec, config, rows, w, h, ctx.brand, ctx.locale)
            except render.RenderError as err:
                groups.append((label, [checks.Finding("ERROR", "P1", str(err))]))
                continue
            for n in res.notes:
                if n not in notes:
                    notes.append(n)
            groups.append((label, checks.picture(res, ctx.brand, len(rows), (w, h), background)))
            framed = render.framed(res.svg, w, h, background)
            frames.append((label, framed, w, h))
    if frames:
        first = frames[0]
        main = files["preview"] / f"{name}.png"
        main.write_bytes(render.png(first[1], 2.0))
        written.append(main)
        sheet = contact_sheet(frames, files["preview"] / f"{name}_sheet.png")
        if sheet:
            written.append(sheet)
        else:
            for label, svg, w, h in frames[1:]:
                p = files["preview"] / f"{name}_{label.replace(' ', '_')}.png"
                p.write_bytes(render.png(svg, 1.0))
                written.append(p)
    merged = checks.merge(groups)
    written_colours = " ".join(f.text for f in static if f.code == "B1")
    merged = [f for f in merged if not (f.code == "B1" and re.search(r"#[0-9A-F]{6}", f.text)
                                        and re.search(r"#[0-9A-F]{6}", f.text).group() in written_colours)]
    return static, merged, written, notes


def contact_sheet(frames: list, path: Path) -> Path | None:
    """All renders in one picture, one row per scenario; needs Pillow."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    rows = {}
    for label, svg, w, h in frames:
        img = Image.open(io.BytesIO(render.png(svg, 1.0))).convert("RGB")
        rows.setdefault(label.split(" ")[0], []).append((label, img))
    gap, head = 12, 16
    width = max(sum(i.width for _, i in r) + gap * (len(r) + 1) for r in rows.values())
    height = sum(max(i.height for _, i in r) + head + gap for r in rows.values()) + gap
    sheet = Image.new("RGB", (width, height), "#C9C9C9")
    draw = ImageDraw.Draw(sheet)
    y = gap
    for r in rows.values():
        x = gap
        for label, img in r:
            draw.text((x, y), label, fill="#222222")
            sheet.paste(img, (x, y + head))
            x += img.width + gap
        y += max(i.height for _, i in r) + head + gap
    sheet.save(path)
    return path


def report_findings(static: list, picture: list, extra: list = ()) -> int:
    allf = checks.order(list(static) + list(extra)) + list(picture)
    if allf:
        say("FINDINGS")
        for f in allf:
            say("  " + f.line())
    n = {lv: sum(1 for f in allf if f.level == lv) for lv in checks.LEVELS}
    say(f"RESULT: {n['ERROR']} error(s), {n['WARNING']} warning(s), {n['NOTE']} note(s)")
    return 1 if n["ERROR"] else 0


def unproven(notes: list) -> None:
    say("NOT PROVEN BY THE LOCAL RENDER")
    v = render.versions() if render.available() else {"vega": "?", "vega-lite": "?"}
    for line in UNPROVEN:
        say("  - " + line.format(vega=v["vega"], vl=v["vega-lite"], deneb=deneb.DENEB_VERSION,
                                 dvega=deneb.VEGA_VERSION, dvl=deneb.VEGALITE_VERSION))
    for n in notes:
        if not n.startswith("pbiFormat:"):
            say("  - " + n)


def parse_sizes(args, brief, vtype) -> list:
    if getattr(args, "size", None):
        out = []
        for s in args.size:
            m = SIZE.match(s)
            if not m:
                raise Fail(f"--size {s}: write WIDTHxHEIGHT, for example 640x360")
            out.append((int(m.group(1)), int(m.group(2))))
        return out
    return bf.sizes(brief, vtype)


# ---------------------------------------------------------------- commands
def cmd_env(args) -> int:
    say(f"bideneb {__version__}")
    say(f"python      {sys.version.split()[0]} ({sys.executable})")
    v = render.available()
    if v:
        vs = render.versions()
        say(f"renderer    vl-convert-python {v} (Vega {vs['vega']}, Vega-Lite {vs['vega-lite']}); "
            f"Deneb {deneb.DENEB_VERSION} runs Vega {deneb.VEGA_VERSION}, Vega-Lite {deneb.VEGALITE_VERSION}")
    else:
        say("renderer    MISSING: vl-convert-python; without it only the static rules run. `bideneb setup` installs it")
    from . import scene
    try:
        import PIL
        say(f"pillow      {PIL.__version__}; text widths are {'measured with the font files' if scene.measured() else 'estimated (font file not found)'}")
    except ImportError:
        say("pillow      missing: text widths are estimated and there is no contact sheet. `bideneb setup` installs it")
    say(f"brands      {', '.join(br.available())} (a new visual gets {br.default()})")
    if br.missing(br.DEFAULT):
        say(f"brand       MISSING: {br.missing(br.DEFAULT)}")
    else:
        say(f"brand       {br.DEFAULT} (corporate design): colours from {br.load(br.DEFAULT).tokens_file}")
    say(f"types       {len(TYPES)}: {', '.join(TYPES)}")
    tool = Path(__file__).resolve().parent.parent / "bideneb.py"
    say(f"call        \"{sys.executable}\" \"{tool}\" <command>")
    return 0 if v else 1


def cmd_setup(args) -> int:
    packages = ["vl-convert-python", "pillow"]
    say(f"installing {', '.join(packages)} with pip --user (no virtual environment)")
    code = subprocess.call([sys.executable, "-m", "pip", "install", "--user", "--disable-pip-version-check", *packages])
    if code:
        say("pip failed. Without vl-convert-python bideneb still builds and checks statically; it cannot render.")
    return code


def cmd_brand(args) -> int:
    b = br.load(args.name)
    say(f"brand {b.name} ({b.tokens.get('brand', '')}); font {b.font}; sizes {b.charts['fontSizesPx']} px")
    for role in ("text", "textSecondary", "grid", "background", "focus", "context", "reference", "good", "bad",
                 "goodText", "badText"):
        hexv = b.c(role)
        say(f"  {role:<14} {b.token_of(hexv):<14} {hexv}")
    for pal in ("category", "line", "sequential", "diverging"):
        say(f"  {pal:<14} " + " ".join(f"{b.token_of(h)} {h}" for h in b.palette(pal)))
    say("  trafficLight   " + " ".join(f"{k} {v}" for k, v in b.traffic().items()))
    say("  never as text  " + ", ".join(b.charts["neverAsText"]))
    say("  never as thin line or small marker on light: " + ", ".join(b.charts["neverAsThinMarkOnLight"]))
    return 0


def cmd_fields(args) -> int:
    projects = md.locate(Path(args.project))
    if not projects:
        raise Fail(f"{args.project}: no .Report or .SemanticModel found")
    seen = set()
    for p in projects:
        if not p.model or p.model in seen:
            continue
        seen.add(p.model)
        m = md.read(p.model)
        say(f"MODEL {p.model.name}" + (f"  (report {p.report.name})" if p.report else ""))
        lines = md.listing(m, args.hidden)
        if args.table:
            keep, on = [], False
            for ln in lines:
                if not ln.startswith(" "):
                    on = ln.casefold() == args.table.casefold()
                if on:
                    keep.append(ln)
            lines = keep
        for ln in lines:
            say("  " + ln)
    say("Roles: quantitative = a number to plot, temporal = a date, nominal = a category. Write a field as "
        "Table[Field].")
    return 0


def cmd_types(args) -> int:
    if args.type:
        t = TYPES.get(args.type)
        if t is None:
            raise Fail(f"type {args.type!r} unknown; types: {', '.join(TYPES)}")
        say(f"{t.id}: {t.title} ({'Vega-Lite' if t.provider == 'vegaLite' else 'Vega'})")
        say(f"  use    {t.use}")
        say(f"  avoid  {t.avoid}")
        say("  fields")
        for r in t.roles:
            say(f"    {r.name:<10} {'required' if r.required else 'optional'}, {' or '.join(r.kinds)}: {r.help}")
        say("  options")
        for o in t.options:
            choice = f" ({' | '.join(map(str, o.choices))})" if o.choices else ""
            say(f"    {o.name:<15} default {json.dumps(o.default, ensure_ascii=False)}{choice}: {o.help}")
        say(f"  cross-filter by click: {'yes' if t.selection else 'no (marks are aggregated or lines)'}; "
            f"default size {t.default_size[0]}x{t.default_size[1]}")
        return 0
    for t in TYPES.values():
        roles = ", ".join(r.name + ("" if r.required else "?") for r in t.roles)
        say(f"{t.id:<10} {t.title:<26} fields: {roles}")
        say(f"{'':<10} {t.use}")
    say("custom     a specification written by hand (Vega or Vega-Lite); `bideneb new custom …` writes the scaffold")
    say("`bideneb types <id>` shows fields and options; `bideneb suggest` proposes types for chosen fields.")
    return 0


def parse_field(text: str, model) -> dict:
    m = FIELD.match(text.strip())
    if not m:
        raise Fail(f"field {text!r}: write Table[Field]; without a model put the kind in front: m: measure, "
                   f"c: text column, d: date column, n: number column (m:Sales[Umsatz])")
    table, name, kind = m.group("table").strip().strip("'"), m.group("name").strip(), m.group("kind")
    out = {"table": table}
    if model is not None:
        f = model.find(table, name)
        if f is None:
            near = ", ".join(x.ref for x in model.search(name)) or "none with that name"
            raise Fail(f"{table}[{name}] is not in the model (found: {near}); `bideneb fields` lists the model")
        out["measure" if f.kind == "measure" else "column"] = f.name
        out["table"] = model.tables[table.casefold()].name
        out["_role"] = f.role
        out["_also"] = "quantitative" if f.kind == "column" and f.numeric else ""
        return out
    if kind is None:
        raise Fail(f"{text}: no model found to look the field up; give --report, or put the kind in front: "
                   f"m:{text} measure, c:{text} text column, d:{text} date column, n:{text} number column")
    out["measure" if kind == "m" else "column"] = name
    out["_role"] = {"m": "quantitative", "c": "nominal", "d": "temporal", "n": "quantitative"}[kind]
    return out


def model_for(args, folder: Path):
    rep = None
    if getattr(args, "report", None):
        rep = report_of(folder, {}, args.report)
    else:
        near = nearby_reports(folder)
        if len(near) == 1:
            rep = near[0]
        elif len(near) > 1:
            raise Fail("several reports here; name one with --report: " + ", ".join(p.name for p in near))
    if rep is None:
        return None, None
    mp = md.model_of(rep)
    return rep, (md.read(mp) if mp else None)


def assign(vtype, fields: list) -> dict | None:
    """Give each field a role of the type by its kind; None when the fields do not fit."""
    left = list(fields)
    out = {}
    for r in sorted(vtype.roles, key=lambda r: not r.required):
        fits = lambda f: not r.only or (r.only == "measure") == bool(f.get("measure"))
        pick = next((f for f in left if f["_role"] in r.kinds and fits(f)), None) or \
            next((f for f in left if f.get("_also") in r.kinds and fits(f)), None)
        if pick is None:
            if r.required:
                return None
            continue
        out[r.name] = pick
        left.remove(pick)
    return None if left else out


def cmd_suggest(args) -> int:
    folder = Path(args.dir or ".").resolve()
    rep, model = model_for(args, folder)
    fields = [parse_field(f, model) for f in args.field]
    say("fields: " + ", ".join(f"{f['table']}[{f.get('measure') or f.get('column')}] = {f['_role']}" for f in fields))
    hits = []
    for t in TYPES.values():
        a = assign(t, fields)
        if a and not (t.id == "line" and a["x"]["_role"] != "temporal"):
            hits.append((t, a))
    if not hits:
        say("no type takes exactly these fields. `bideneb types` lists what each type needs; a type may need a "
            "field more or less, or the kind of a column must be set (a number used as category).")
        return 1
    for t, a in hits:
        say(f"{t.id:<10} {t.title}: {t.use}")
        flags = " ".join(f"--field {role}=\"{f['table']}[{f.get('measure') or f.get('column')}]\"" for role, f in a.items())
        say(f"{'':<10} bideneb new {t.id} <name> {flags}")
    say("Pick by what the reader should see, not by what fits; ask the user when two types answer different questions.")
    return 0


def scaffold(ctx, provider: str) -> dict:
    """Starting point of a hand-written specification."""
    b = ctx.brand
    name = ctx.brief.get("title") or ctx.brief["name"]
    if provider == "vega":
        return {"$schema": VEGA_SCHEMA, "description": name, "padding": 0, "autosize": "none",
                "signals": [{"name": "W", "update": "max(240, width)"}, {"name": "H", "update": "max(120, height)"},
                            {"name": "pad", "value": 12}],
                "data": [{"name": "dataset"},
                         {"name": "rows", "source": "dataset", "transform": []}],
                "scales": [],
                "marks": [{"type": "text", "encode": {"update": {
                    "x": {"signal": "pad"}, "y": {"signal": "pad"}, "baseline": {"value": "top"},
                    "text": {"signal": f"'{name}: ' + length(data('rows')) + ' rows'"},
                    "fill": {"value": b.c("text")}, "fontSize": {"value": b.size("title")},
                    "fontWeight": {"value": 600}}}}]}
    fields = ctx.all()
    cat = next((f for f in fields if f.type != "quantitative"), None)
    val = next((f for f in fields if f.type == "quantitative"), None)
    spec = {"$schema": VL_SCHEMA, "description": name, "data": {"name": "dataset"}}
    if ctx.brief.get("title"):
        spec["title"] = {"text": ctx.brief["title"]}
    if cat and val:
        spec["mark"] = {"type": "bar", "tooltip": True, "color": b.c("focus")}
        spec["encoding"] = {"y": {"field": cat.key, "type": "nominal", "axis": {"title": None}},
                            "x": {"field": val.key, "type": "quantitative",
                                  "axis": {"title": None, "format": val.fmt, "formatType": "pbiFormat"}}}
    else:
        spec["mark"] = {"type": "text", "color": b.c("text")}
        spec["encoding"] = {"text": {"field": fields[0].key}} if fields else {}
    return spec


def cmd_new(args) -> int:
    folder = Path(args.dir or "deneb").resolve()
    if args.type != "custom" and args.type not in TYPES:
        raise Fail(f"type {args.type!r} unknown; types: {', '.join(TYPES)}, custom")
    path = folder / f"{args.name}.brief.json"
    if path.exists() and not args.overwrite:
        raise Fail(f"{path} exists; choose another name or pass --overwrite")
    rep, model = model_for(args, folder)
    fields = {}
    for item in args.field or []:
        if "=" not in item:
            raise Fail(f"--field {item}: write role=Table[Field]")
        role, ref = item.split("=", 1)
        f = parse_field(ref, model)
        entry = {k: v for k, v in f.items() if not k.startswith("_")}
        if model is None:
            entry["type"] = f["_role"]
        if role in fields:
            fields[role] = (fields[role] if isinstance(fields[role], list) else [fields[role]]) + [entry]
        else:
            fields[role] = entry
    brief = {"name": args.name, "type": args.type}
    if args.title:
        brief["title"] = args.title
    if args.subtitle:
        brief["subtitle"] = args.subtitle
    brief["brand"] = args.brand or br.default()
    brief["locale"] = args.locale or (model.culture if model is not None and model.culture else "de-DE")
    brief["fields"] = fields
    options = {}
    for item in args.option or []:
        if "=" not in item:
            raise Fail(f"--option {item}: write key=value")
        k, v = item.split("=", 1)
        try:
            options[k] = json.loads(v)
        except json.JSONDecodeError:
            options[k] = v
    if options:
        brief["options"] = options
    samples = {}
    for item in args.sample or []:
        if "=" not in item:
            raise Fail(f"--sample {item}: write Field=value|value|value")
        k, v = item.split("=", 1)
        samples[k] = [x.strip() for x in v.split("|") if x.strip()]
    if samples:
        brief["sample"] = samples
    if rep is not None:
        import os
        brief["report"] = {"path": Path(os.path.relpath(rep, folder)).as_posix()}
        if args.page:
            brief["report"]["page"] = args.page
    ctx, vtype, problems = bf.resolve(brief, path, model)
    if problems:
        raise Fail("the brief would have problems:\n  " + "\n  ".join(problems)
                   + (f"\n`bideneb types {args.type}` shows the fields and options of the type" if vtype else ""))
    write_json(path, brief)
    say(f"wrote {path}")
    if args.type == "custom":
        spec_file = bf.files(path, brief)["spec"]
        if not spec_file.exists():
            write_json(spec_file, scaffold(ctx, args.provider or "vegaLite"))
            write_json(bf.files(path, brief)["config"], base_config(ctx, args.provider or "vegaLite"))
            say(f"wrote {spec_file.name} (scaffold) and the config in the brand design; write the specification, "
                f"then `bideneb check {args.name}`")
        return 0
    args.brief, args.size, args.overwrite, args.no_render = str(path), None, False, False
    return cmd_build(args)


def cmd_build(args) -> int:
    path, brief, ctx, vtype, files = load(args.brief)
    if vtype is None:
        say(f"{brief['name']} is a custom specification: nothing to generate; running the checks")
        args.size = getattr(args, "size", None)
        return cmd_check(args)
    if files["spec"].is_file() and not args.overwrite:
        try:
            old = ex.loads(files["spec"].read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, ValueError):
            old = None
        if old is not None and edited(old):
            raise Fail(f"{files['spec'].name} was changed by hand after the last build. Keep the changes: set "
                       f"\"type\": \"custom\" in the brief (the file is then yours). Discard them: --overwrite")
    spec = vtype.build(ctx)
    config = vtype.config(ctx)
    spec["usermeta"] = {"bideneb": {"version": __version__, "type": vtype.id, "sha": sha(spec)}}
    write_json(files["spec"], spec)
    write_json(files["config"], config)
    say(f"{brief['name']}: type {vtype.id} ({vtype.title}), {'Vega-Lite' if vtype.provider == 'vegaLite' else 'Vega'}, "
        f"brand {ctx.brand.name}, {len(ctx.all())} field(s): {', '.join(f.key for f in ctx.all())}")
    say(f"wrote {files['spec'].name}, {files['config'].name}")
    if ctx.brand.name == br.FALLBACK and br.missing(br.DEFAULT):
        say(f"NOTE brand: drawn in the neutral design. {br.missing(br.DEFAULT)[0].upper()}{br.missing(br.DEFAULT)[1:]}")
    return finish(args, path, brief, ctx, vtype, files, spec, config)


def cmd_check(args) -> int:
    path, brief, ctx, vtype, files = load(args.brief)
    spec, config = read_spec(files)
    return finish(args, path, brief, ctx, vtype, files, spec, config)


def finish(args, path, brief, ctx, vtype, files, spec, config) -> int:
    sizes = parse_sizes(args, brief, vtype)
    scenarios = [args.scenario] if getattr(args, "scenario", None) else ["typical", "stress"]
    static, picture, written, notes = examine(ctx, vtype, spec, config, files, sizes, scenarios,
                                              pictures=not getattr(args, "no_render", False),
                                              background=brief.get("background", "#FFFFFF"))
    extra = []
    rep = report_of(path, brief)
    if rep is not None:
        try:
            extra = pbir.verify(rep, vname(brief), ctx.all(), spec, config, ctx.interaction)
        except pbir.PbirError as err:
            extra = [checks.Finding("ERROR", "R0", str(err))]
    if written:
        say(f"rendered {len(scenarios) * len(sizes)} picture(s) ({', '.join(scenarios)}; "
            f"{', '.join(f'{w}x{h}' for w, h in sizes)}):")
        for p in written:
            say(f"  {p}")
    code = report_findings(static, picture, extra)
    if written:
        unproven(notes)
        say("NEXT: look at the contact sheet. Fix errors and warnings (brief options, or the specification for a "
            "custom type), build again; at most three rounds, then tell the user what stays open.")
    return code


def cmd_render(args) -> int:
    path, brief, ctx, vtype, files = load(args.brief)
    spec, config = read_spec(files)
    if render.available() is None:
        raise Fail("vl-convert-python is not installed; `bideneb setup`")
    sizes = parse_sizes(args, brief, vtype)[:1] if not args.size else parse_sizes(args, brief, vtype)
    scenario = args.scenario or "typical"
    if args.data:
        rows = json.loads(Path(args.data).read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list):
            raise Fail(f"{args.data}: a JSON list of rows is needed")
    else:
        rows = rows_for(ctx, vtype, files, scenario)
    try:
        selected = {int(x) for x in args.selected.split(",")} if args.selected else None
    except ValueError:
        raise Fail(f"--selected {args.selected}: row numbers separated by commas, for example 0,3") from None
    rows = deneb.rows_for_deneb(rows, ctx.select or bool(selected), selected)
    files["preview"].mkdir(parents=True, exist_ok=True)
    for (w, h) in sizes:
        try:
            res = render.render(spec, config, rows, w, h, ctx.brand, ctx.locale)
        except render.RenderError as err:
            raise Fail(str(err)) from None
        tag = f"{brief['name']}_{scenario}_{w}x{h}" + ("_selected" if selected else "")
        out = files["preview"] / f"{tag}.png"
        out.write_bytes(render.png(render.framed(res.svg, w, h, args.background or brief.get("background", "#FFFFFF")),
                                   args.scale))
        say(f"wrote {out} ({len(rows)} rows)")
        if args.svg:
            (files["preview"] / f"{tag}.svg").write_text(res.svg, encoding="utf-8")
            say(f"wrote {files['preview'] / (tag + '.svg')}")
        if args.vega:
            write_json(files["preview"] / f"{tag}.vega.json", res.vega)
            say(f"wrote {files['preview'] / (tag + '.vega.json')} (compiled Vega with the approximations)")
        for line in res.runtime:
            say(f"  Vega reported: {line}")
    return 0


def cmd_embed(args) -> int:
    path, brief, ctx, vtype, files = load(args.brief)
    spec, config = read_spec(files)
    rep = report_of(path, brief, args.report)
    if rep is None:
        near = nearby_reports(files["folder"])
        if len(near) != 1:
            raise Fail("which report? pass --report <path to .Report or .pbip>"
                       + (": " + ", ".join(p.name for p in near) if near else ""))
        rep = near[0]
    static = checks.static(spec, config, ctx.brand, [f.key for f in ctx.all()], ctx.interaction,
                           render_mode=brief.get("renderMode", "svg"), generated=vtype is not None and not edited(spec))
    errors = [f for f in static if f.level == "ERROR"]
    if errors and not args.force:
        for f in errors:
            say("  " + f.line())
        raise Fail("the specification has errors; fix them (`bideneb check`) before embedding, or pass --force")
    if render.available() is not None and not args.force:
        w, h = bf.sizes(brief, vtype)[0]
        rows = deneb.rows_for_deneb(rows_for(ctx, vtype, files, "typical"), ctx.select)
        try:
            res = render.render(spec, config, rows, w, h, ctx.brand, ctx.locale, svg=False)
        except render.RenderError as err:
            raise Fail(f"the specification does not run: {err}. Fix it (`bideneb check`) before embedding, or pass "
                       f"--force") from None
        broken = [f for f in checks.picture(res, ctx.brand, len(rows), (w, h)) if f.code in ("P1", "P2")]
        if broken:
            for f in broken:
                say("  " + f.line())
            raise Fail("the specification draws nothing or reports errors with the preview rows; fix it "
                       "(`bideneb check`) before embedding, or pass --force")
    model_path = md.model_of(rep)
    if model_path:
        model = md.read(model_path)
        missing = [f"{f.table}[{f.name}]" for f in ctx.all() if model.find(f.table, f.name) is None]
        if missing:
            raise Fail(f"not in the model of {rep.name}: {', '.join(missing)}; `bideneb fields` lists the model")
    try:
        existing = pbir.find_visual(rep, vname(brief))
    except pbir.PbirError as err:
        raise Fail(str(err)) from None
    if existing is not None and not args.force:
        in_report = pbir.state_sha(existing["spec"], existing["config"])
        if in_report != pbir.state_sha(spec, config) and in_report != (brief.get("report") or {}).get("sha"):
            raise Fail(f"the visual in the report was changed since bideneb last wrote or read it (in the Deneb "
                       f"editor?). Keep that version: `bideneb pull {brief['name']}`. Overwrite it with the file: "
                       f"--force")
    if existing is not None and args.new_page:
        raise Fail(f"the visual already stands on page '{existing['page']}'; --new-page applies to a first embed. "
                   f"Move a visual in Desktop")
    page_name = args.page or (brief.get("report") or {}).get("page")
    try:
        if existing is not None:
            page = next(p for p in pbir.pages(rep) if p["name"] == existing["pageName"])
            if page_name and page_name not in (page["name"], page["displayName"]):
                raise Fail(f"the visual already stands on page '{page['displayName']}'; move it in Desktop")
        elif args.new_page:
            page = pbir.new_page(rep, args.new_page)
            say(f"created page '{args.new_page}'")
        elif page_name:
            page = pbir.find_page(rep, page_name)
        else:
            names = ", ".join(f"'{p['displayName']}'" for p in pbir.pages(rep))
            raise Fail(f"which page? pass --page <name> or --new-page <name>; pages: {names}")
        position = None
        if args.position:
            try:
                parts = [int(x) for x in args.position.split(",")]
            except ValueError:
                parts = []
            if len(parts) != 4:
                raise Fail("--position takes four whole numbers: x,y,width,height (for example 24,120,600,320)")
            position = dict(zip(("x", "y", "width", "height"), parts))
        elif (brief.get("report") or {}).get("position") and existing is None:
            position = brief["report"]["position"]
        size = vtype.default_size if vtype is not None else (640, 360)
        result = pbir.embed(rep, page, brief["name"], ctx.all(), deneb.provider_of(spec), spec, config,
                            ctx.interaction, position, size, brief.get("renderMode"),
                            (brief.get("report") or {}).get("visual"))
    except pbir.PbirError as err:
        raise Fail(str(err)) from None
    import os
    brief.setdefault("report", {})
    brief["report"]["path"] = Path(os.path.relpath(rep, files["folder"])).as_posix()
    brief["report"]["page"] = page["displayName"]
    brief["report"]["sha"] = pbir.state_sha(spec, config)
    write_json(path, brief)
    say(f"{'created' if result['created'] else 'updated'} {result['path']}")
    if result["registered"]:
        say("added Deneb to publicCustomVisuals in report.json")
    findings = pbir.verify(rep, vname(brief), ctx.all(), spec, config, ctx.interaction)
    code = report_findings([], [], findings)
    say("Desktop does not see the change while the project is open there, and saving from Desktop writes its own "
        "state over it: the user closes the project first, or reopens it without saving.")
    say("NEXT (the user, in Power BI Desktop): open or reload the project; Deneb loads from AppSource. Check on the "
        "page: the visual draws, numbers and dates read right, the tooltip shows, a click filters the other "
        "visuals (if cross-filter is on). After changes in the Deneb editor: save, then `bideneb pull`.")
    return code


def cmd_pull(args) -> int:
    path, brief, ctx, vtype, files = load(args.brief)
    rep = report_of(path, brief, args.report)
    if rep is None:
        raise Fail("the brief names no report; pass --report")
    try:
        v = pbir.find_visual(rep, vname(brief))
    except pbir.PbirError as err:
        raise Fail(str(err)) from None
    if v is None:
        raise Fail(f"no Deneb visual {vname(brief)} in {rep.name}; `bideneb list` shows what is there")
    try:
        spec = ex.loads(v["spec"])
        config = ex.loads(v["config"])
    except (json.JSONDecodeError, ValueError) as err:
        raise Fail(f"the specification in the report is not valid JSON ({err})") from None
    old = None
    if files["spec"].is_file():
        old = ex.loads(files["spec"].read_text(encoding="utf-8-sig"))
        old_config = ex.loads(files["config"].read_text(encoding="utf-8-sig")) if files["config"].is_file() else {}
        mine, theirs = pbir.state_sha(old, old_config), pbir.state_sha(spec, config)
        known = (brief.get("report") or {}).get("sha")
        if mine != theirs and known and mine != known and not args.force:
            raise Fail(f"{files['spec'].name} was changed since bideneb last wrote it into the report or read it "
                       f"from there, and the report differs too. Keep the file: `bideneb embed {brief['name']} "
                       f"--force`. Keep the report: `bideneb pull {brief['name']} --force`")
    if old is not None and pbir.same_spec(json.dumps(old), v["spec"]) and \
            (not files["config"].is_file() or ex.loads(files["config"].read_text(encoding="utf-8-sig")) == config):
        say("the report and the files hold the same specification and config; nothing to pull")
        return 0
    out = {"$schema": VEGA_SCHEMA if v["provider"] == "vega" else VL_SCHEMA}
    out.update({k: val for k, val in spec.items() if k not in ("$schema", "usermeta")})
    write_json(files["spec"], out)
    write_json(files["config"], config)
    say(f"wrote {files['spec'].name} and {files['config'].name} from {v['page']} › {v['name']}")
    brief.setdefault("report", {})["sha"] = pbir.state_sha(spec, config)
    write_json(path, brief)
    if brief.get("type") != "custom":
        brief["generatedAs"] = brief["type"]
        brief["type"] = "custom"
        write_json(path, brief)
        say(f"the brief is now type custom (was {brief['generatedAs']}): the file holds the version of the report "
            f"and `bideneb build` no longer overwrites it")
    drift = [k for k in v["keys"] if k not in [f.key for f in ctx.all()]]
    if drift:
        say(f"fields in the report that the brief does not know: {', '.join(drift)}; add them to the brief")
    say(f"NEXT: `bideneb check {brief['name']}`")
    return 0


def cmd_template(args) -> int:
    path, brief, ctx, vtype, files = load(args.brief)
    spec, config = read_spec(files)
    t = pbir.template(brief.get("title") or brief["name"], brief.get("description", ""), ctx.all(),
                      deneb.provider_of(spec), spec, config, ctx.interaction)
    write_json(files["template"], t)
    say(f"wrote {files['template']}")
    say("Import by hand: add a Deneb visual, put the fields into Values, open the editor, New specification › "
        "Import template, choose this file and assign each placeholder its field:")
    for d in t["usermeta"]["datasets"]["dataset"]:
        say(f"  {d['name']}  ←  {d['description']} ({d['kind']})")
    return 0


def vname(brief: dict) -> str:
    """Name of the visual in the report: the adopted one, or deneb_<name>."""
    return (brief.get("report") or {}).get("visual") or pbir.visual_name(brief["name"])


def cmd_adopt(args) -> int:
    rep = report_of(Path("."), {}, args.report)
    try:
        vs = pbir.visuals(rep)
    except pbir.PbirError as err:
        raise Fail(str(err)) from None
    hits = [v for v in vs if args.visual in (v["name"], f"{v['page']} › {v['name']}")] or \
        [v for v in vs if v["page"] == args.visual]
    if len(hits) != 1:
        raise Fail(f"visual {args.visual!r} {'is ambiguous' if hits else 'not found'}; Deneb visuals: "
                   + ", ".join(f"{v['page']} › {v['name']}" for v in vs))
    v = hits[0]
    name = args.name or re.sub(r"[^a-z0-9_-]", "", v["name"].lower())[:40] or "visual"
    folder = Path(args.dir or "deneb").resolve()
    for other in sorted(folder.glob("*.brief.json")):
        try:
            if vname(json.loads(other.read_text(encoding="utf-8-sig"))) == v["name"]:
                raise Fail(f"{other.name} already describes this visual; use it (`bideneb pull`, `bideneb check`)")
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    path = folder / f"{name}.brief.json"
    if path.exists():
        raise Fail(f"{path} exists; choose another --name")
    mp = md.model_of(rep)
    model = md.read(mp) if mp else None
    fields = {}
    for p in v["projections"]:
        f = p.get("field", {})
        kind = "measure" if "Measure" in f else "column" if "Column" in f else None
        node = f.get("Measure") or f.get("Column") or {}
        ent = (node.get("Expression", {}).get("SourceRef", {}) or {}).get("Entity")
        if not kind or not ent:
            say(f"  NOT TAKEN: {p.get('queryRef')} is an implicit aggregation or a hierarchy. Its name in the "
                f"dataset depends on the language of Desktop, and `bideneb embed` refuses to write this visual "
                f"until it is replaced by a measure or a column")
            continue
        entry = {"table": ent, kind: node["Property"]}
        mf = model.find(ent, node["Property"]) if model else None
        if mf is None:
            entry["type"] = "quantitative" if kind == "measure" else "nominal"
        if p.get("displayName"):
            entry["as"] = p["displayName"]
        role = re.sub(r"\W", "_", pbir.projection_key(p)) or f"field{len(fields)}"
        fields[role] = entry
    try:
        spec, config = ex.loads(v["spec"]), ex.loads(v["config"])
    except (json.JSONDecodeError, ValueError) as err:
        raise Fail(f"the specification in the report is not valid JSON ({err})") from None
    import os
    brief = {"name": name, "type": "custom", "brand": args.brand or br.default(),
             "locale": model.culture if model is not None and model.culture else "de-DE", "fields": fields,
             "interaction": {"tooltip": bool(pbir.unliteral(v["properties"].get("enableTooltips")) is not False),
                             "crossFilter": v["selection"],
                             "highlight": bool(pbir.unliteral(v["properties"].get("enableHighlight")))},
             "report": {"path": Path(os.path.relpath(rep, folder)).as_posix(), "page": v["page"], "visual": v["name"],
                        "sha": pbir.state_sha(v["spec"], v["config"])}}
    limit = pbir.unliteral(v["properties"].get("selectionMaxDataPoints"))
    if limit:
        brief["interaction"]["maxDataPoints"] = limit
    mode = pbir.unliteral(v["properties"].get("renderMode"))
    if mode and mode != "svg":
        brief["renderMode"] = mode
    w, h = v["position"].get("width"), v["position"].get("height")
    if w and h:
        brief["sizes"] = [[int(w), int(h)], [max(240, int(w * 0.6)), max(160, int(h * 0.75))]]
    write_json(path, brief)
    out = {"$schema": VEGA_SCHEMA if v["provider"] == "vega" else VL_SCHEMA}
    out.update({k: val for k, val in spec.items() if k not in ("$schema", "usermeta")})
    files = bf.files(path, brief)
    write_json(files["spec"], out)
    write_json(files["config"], config)
    say(f"adopted {v['page']} › {v['name']} ({v['provider']}, {len(fields)} fields)")
    say(f"wrote {path.name}, {files['spec'].name}, {files['config'].name} in {folder}")
    say(f"NEXT: `bideneb check {name}` renders it with invented rows and checks it. The rows are generic: a "
        f"specification that needs certain values (status words, start before end) needs own rows in "
        f"{files['data'].name} ({{\"typical\": [...], \"stress\": [...]}}).")
    return 0


def cmd_list(args) -> int:
    target = Path(args.project).resolve()
    reports = [p.report for p in md.locate(target) if p.report]
    if not reports:
        raise Fail(f"{target}: no report found")
    briefs = {}
    for b in target.rglob("*.brief.json") if target.is_dir() else []:
        try:
            briefs[vname(json.loads(b.read_text(encoding="utf-8-sig")))] = b
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    total = 0
    for rep in reports:
        try:
            vs = pbir.visuals(rep)
        except pbir.PbirError as err:
            say(f"{rep.name}: {err}")
            continue
        say(f"REPORT {rep.name}: {len(vs)} Deneb visual(s)")
        for v in vs:
            total += 1
            b = briefs.get(v["name"])
            say(f"  {v['page']} › {v['name']}: {v['provider']}, {len(v['spec'])} characters, fields "
                f"{', '.join(v['keys']) or 'none'}; " + (f"brief {b}" if b else "no brief (made outside bideneb)"))
    if not total:
        say("no Deneb visuals yet")
    return 0


# ---------------------------------------------------------------- main
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bideneb", description="Build, check and improve Deneb visuals for Power BI "
                                                            "in a brand design.")
    p.add_argument("--version", action="version", version=f"bideneb {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    def add(name, fn, text):
        sp = sub.add_parser(name, help=text, description=text)
        sp.set_defaults(fn=fn)
        return sp

    add("env", cmd_env, "Python, renderer, fonts, brands; the first command of a session")
    add("setup", cmd_setup, "install the renderer (vl-convert-python) and Pillow with pip --user")
    s = add("brand", cmd_brand, "colours, palettes and rules of a brand profile")
    s.add_argument("name", nargs="?")
    s = add("fields", cmd_fields, "tables, columns and measures of the model of a Power BI project (metadata only)")
    s.add_argument("project")
    s.add_argument("--table")
    s.add_argument("--hidden", action="store_true", help="also hidden tables and fields")
    s = add("types", cmd_types, "the visual types; with an id: its fields and options")
    s.add_argument("type", nargs="?")
    s = add("suggest", cmd_suggest, "which types take the given fields")
    s.add_argument("field", nargs="+", help="Table[Field]")
    s.add_argument("--report")
    s.add_argument("--dir", help="folder of the briefs (default: current folder)")
    s = add("new", cmd_new, "write a brief and build the visual")
    s.add_argument("type")
    s.add_argument("name")
    s.add_argument("--field", action="append", metavar="role=Table[Field]")
    s.add_argument("--title")
    s.add_argument("--subtitle")
    s.add_argument("--option", action="append", metavar="key=value")
    s.add_argument("--sample", action="append", metavar="Field=a|b|c", help="invented category names for the preview")
    s.add_argument("--dir", help="folder for the files (default: ./deneb)")
    s.add_argument("--report", help="the .Report folder or .pbip (default: the one report next to the folder)")
    s.add_argument("--page")
    s.add_argument("--brand")
    s.add_argument("--locale")
    s.add_argument("--provider", choices=("vegaLite", "vega"), help="for type custom")
    s.add_argument("--overwrite", action="store_true")
    for name, fn, text in (("build", cmd_build, "generate specification and config from the brief, render and check"),
                           ("check", cmd_check, "render and check the specification as it is in the file")):
        s = add(name, fn, text)
        s.add_argument("brief")
        s.add_argument("--size", action="append", metavar="WxH")
        s.add_argument("--scenario", choices=sample.SCENARIOS)
        s.add_argument("--no-render", action="store_true")
        if name == "build":
            s.add_argument("--overwrite", action="store_true", help="discard changes made by hand")
    s = add("render", cmd_render, "one picture: a size, a scenario, own rows, a selection")
    s.add_argument("brief")
    s.add_argument("--size", action="append", metavar="WxH")
    s.add_argument("--scenario", choices=sample.SCENARIOS)
    s.add_argument("--data", help="JSON file with a list of rows (invented, never real data)")
    s.add_argument("--selected", help="row numbers that are selected, e.g. 0,3: shows the cross-filter state")
    s.add_argument("--background", help="page background, default #FFFFFF")
    s.add_argument("--scale", type=float, default=2.0)
    s.add_argument("--svg", action="store_true")
    s.add_argument("--vega", action="store_true", help="also the compiled Vega specification")
    s = add("embed", cmd_embed, "write the visual into the report (PBIR) and check it there")
    s.add_argument("brief")
    s.add_argument("--report")
    s.add_argument("--page")
    s.add_argument("--new-page", metavar="NAME")
    s.add_argument("--position", metavar="x,y,width,height")
    s.add_argument("--force", action="store_true")
    s = add("pull", cmd_pull, "take the specification from the report into the file (after changes in the Deneb editor)")
    s.add_argument("brief")
    s.add_argument("--report")
    s.add_argument("--force", action="store_true", help="discard changes of the file")
    s = add("template", cmd_template, "a Deneb template for import by hand, when the report cannot be written")
    s.add_argument("brief")
    s = add("adopt", cmd_adopt, "take a Deneb visual that already stands in a report under bideneb: brief, "
                                "specification and config as files")
    s.add_argument("report", help="the .Report folder or .pbip")
    s.add_argument("visual", help="name of the visual, or its page when the page holds one Deneb visual")
    s.add_argument("--name", help="name of the brief (default: from the visual)")
    s.add_argument("--dir", help="folder for the files (default: ./deneb)")
    s.add_argument("--brand")
    s = add("list", cmd_list, "the Deneb visuals of the reports of a project")
    s.add_argument("project")
    return p


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    args = parser().parse_args(argv)
    if not getattr(args, "fn", None):
        parser().print_help()
        return 2
    try:
        return args.fn(args)
    except (Fail, BriefError, FileNotFoundError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
