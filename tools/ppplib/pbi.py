"""Power BI as PBIP (PLUGIN PL-22): list the semantic model (TMDL or model.bim) and the report (PBIR or PBIR-Legacy)
compactly, and check both before the user opens them in Power BI Desktop. Standard library only; reads no row data.

Findings: M1 indent, M2 unquoted name, M3 relationship column, M4 time function; R1 JSON, R2 BOM, R3 $schema, R4 name,
R5 pageBinding, R6 filter name, R7 field reference, R8 page order, R9 legacy format; G1 data files and git; P1 path length.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import gitutil
from .project import ToolError
from .report import Report

NAME = re.compile(r"^[\w-]+$")
AUTO_DATE = re.compile(r"^(LocalDateTable_|DateTableTemplate_)", re.I)
SOURCES = re.compile(r"\b(SharePoint\.\w+|Sql\.Databases?|Excel\.Workbook|Excel\.CurrentWorkbook|Csv\.Document|"
                     r"Json\.Document|Xml\.Tables|Web\.Contents|OData\.Feed|File\.Contents|Folder\.Files|Folder\.Contents|"
                     r"Odbc\.\w+|OleDb\.\w+|AnalysisServices\.\w+|PowerPlatform\.Dataflows|PowerBI\.Dataflows|"
                     r"Dataverse\.\w+|CommonDataService\.\w+|Lakehouse\.\w+|AzureStorage\.\w+|Salesforce\.\w+|"
                     r"Table\.FromRows)\b")
M_TIME = re.compile(r"\b(?:DateTime|DateTimeZone)\.(?:Fixed)?LocalNow\b|\bDateTimeZone\.ToLocal\b")
DAX_TIME = re.compile(r"(?<![\w.])(?:NOW|TODAY)\s*\(", re.I)
DECL = re.compile(r"^([A-Za-z]+)\b ?(.*)$")
DEPTH = {"table": 0, "relationship": 0, "expression": 0, "role": 0, "perspective": 0, "culture": 0, "model": 0,
         "function": 0, "column": 1, "measure": 1, "partition": 1, "hierarchy": 1, "calculationGroup": 1,
         "level": 2, "calculationItem": 2}
NAMED = {"table", "column", "measure", "partition", "hierarchy", "level", "expression", "calculationItem", "role",
         "perspective", "function"}
DATA_FILES = ("cache.abf", "localSettings.json")
TIME_HINT = "returns UTC-based values in the service; convert explicitly (skill ppp-power-bi, references/time.md)"


@dataclass
class Table:
    name: str
    where: str
    columns: dict = field(default_factory=dict)      # casefold -> name
    calculated: list = field(default_factory=list)
    measures: dict = field(default_factory=dict)
    hierarchies: dict = field(default_factory=dict)  # casefold -> (name, {casefold level})
    kind: str = ""
    sources: set = field(default_factory=set)


@dataclass
class Model:
    path: Path
    fmt: str = "TMDL"
    tables: dict = field(default_factory=dict)       # casefold -> Table
    relationships: list = field(default_factory=list)
    expressions: list = field(default_factory=list)  # (name, sources)
    texts: list = field(default_factory=list)        # (where, text) for the time rule, without auto date tables
    findings: list = field(default_factory=list)     # (level, message)


@dataclass
class Visual:
    name: str
    type: str
    title: str
    refs: list
    where: str


@dataclass
class Page:
    name: str
    display: str
    hidden: bool
    visuals: list
    filters: list


@dataclass
class ReportDef:
    path: Path
    fmt: str = "PBIR"
    model_path: Path | None = None
    connection: str = ""
    pages: list = field(default_factory=list)
    filters: list = field(default_factory=list)
    bookmarks: list = field(default_factory=list)    # (name, refs, where)
    extension: dict = field(default_factory=dict)    # casefold entity -> {casefold measure}
    findings: list = field(default_factory=list)


# ------------------------------------------------------------------ helpers
def tmdl_name(rest: str) -> tuple[str, str]:
    """Name at the start of rest ('quoted' with '' for a quote, or bare) and the remainder."""
    rest = rest.lstrip()
    if rest.startswith("'"):
        out, i = [], 1
        while i < len(rest):
            if rest[i] == "'":
                if rest[i + 1:i + 2] == "'":
                    out.append("'")
                    i += 2
                    continue
                return "".join(out), rest[i + 1:].lstrip()
            out.append(rest[i])
            i += 1
        return "".join(out), ""
    m = re.match(r"[^\s=:.']+", rest)
    return (m.group(0), rest[m.end():].lstrip()) if m else ("", rest)


def qualified(value: str) -> tuple[str, str]:
    table, rest = tmdl_name(value)
    if not rest.startswith("."):
        return table, ""
    return table, tmdl_name(rest[1:])[0]


def _json(path: Path, where: str, findings: list):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        findings.append(("ERROR", f"R2 {where}: UTF-8 with BOM; save without BOM"))
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as ex:
        findings.append(("ERROR", f"R1 {where}: not valid JSON ({ex})"))
        return None


def _entity(expr, aliases: dict) -> str | None:
    if isinstance(expr, dict) and isinstance(expr.get("SourceRef"), dict):
        ref = expr["SourceRef"]
        return ref.get("Entity") or aliases.get(ref.get("Source"))
    return None


def refs(obj, aliases: dict | None = None, out: list | None = None) -> list:
    """Field references (kind, entity, property, level) in a PBIR or legacy query, filter or bookmark."""
    out = [] if out is None else out
    aliases = aliases or {}
    if isinstance(obj, dict):
        frm = obj.get("From")
        if isinstance(frm, list):
            aliases = {**aliases, **{f.get("Name"): f.get("Entity") for f in frm if isinstance(f, dict) and f.get("Entity")}}
        for kind in ("Column", "Measure"):
            node = obj.get(kind)
            if isinstance(node, dict) and "Property" in node:
                ent = _entity(node.get("Expression"), aliases)
                if ent:
                    out.append((kind.lower(), ent, node["Property"], None))
        node = obj.get("HierarchyLevel")
        if isinstance(node, dict):
            h = (node.get("Expression") or {}).get("Hierarchy")
            if isinstance(h, dict):
                src = h.get("Expression") or {}
                variation = src.get("PropertyVariationSource") if isinstance(src, dict) else None
                if isinstance(variation, dict):  # auto date hierarchy on a date column
                    ent = _entity(variation.get("Expression"), aliases)
                    if ent and variation.get("Property"):
                        out.append(("column", ent, variation["Property"], None))
                else:
                    ent = _entity(src, aliases)
                    if ent:
                        out.append(("hierarchy", ent, h.get("Hierarchy") or "", node.get("Level") or ""))
        for v in obj.values():
            refs(v, aliases, out)
    elif isinstance(obj, list):
        for v in obj:
            refs(v, aliases, out)
    return out


def _unique(items: list) -> list:
    seen, out = set(), []
    for r in items:
        key = tuple(x.casefold() if isinstance(x, str) else x for x in r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def show(ref) -> str:
    kind, ent, prop, level = ref
    return f"{ent}.{prop}.{level}" if kind == "hierarchy" else f"{ent}.{prop}"


def _title(objects) -> str:
    try:
        value = objects["title"][0]["properties"]["text"]["expr"]["Literal"]["Value"]
        return value.strip("'")
    except (KeyError, IndexError, TypeError):
        return ""


def _loads(value):
    if isinstance(value, str) and value.strip()[:1] in "{[":
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


# ------------------------------------------------------------------ model
def read_model(path: Path) -> Model:
    model = Model(path)
    definition = path / "definition"
    if definition.is_dir():
        for f in sorted(definition.rglob("*.tmdl")):
            _tmdl(model, f, f.relative_to(path.parent).as_posix())
    elif (path / "model.bim").is_file():
        model.fmt = "TMSL"
        _bim(model, path / "model.bim", (path / "model.bim").relative_to(path.parent).as_posix())
    else:
        model.fmt = "?"
        model.findings.append(("ERROR", f"M0 {path.name}: neither definition/*.tmdl nor model.bim"))
    return model


def _tmdl(model: Model, f: Path, rel: str) -> None:
    table = obj = None  # depth-0 table, the depth-1/2 object properties belong to
    top = ""            # keyword of the current depth-0 object
    auto = fence = False
    for no, raw in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
        where = f"{rel}:{no}"
        if fence:
            if raw.strip().endswith("```"):
                fence = False
            if not auto:
                model.texts.append((where, raw))
            if top == "table" and table is not None and obj == "partition":
                table.sources.update(SOURCES.findall(raw))
            continue
        text = raw.strip()
        if not text or text.startswith("///"):
            continue
        lead = raw[:len(raw) - len(raw.lstrip(" \t"))]
        depth = len(lead) - len(lead.lstrip("\t"))  # spaces after the tabs belong to M or DAX text
        if lead.startswith(" "):
            model.findings.append(("ERROR", f"M1 {where}: indented with spaces; TMDL indents with tabs"))
        if text.count("```") == 1:
            fence = True
        if not auto:
            model.texts.append((where, raw))
        m = DECL.match(text)
        kw = m.group(1) if m else ""
        if m and DEPTH.get(kw) == depth and (depth == 0 or top == "table"):
            name, rest = tmdl_name(m.group(2))
            if kw in NAMED and rest and not rest.startswith("="):
                model.findings.append(("ERROR", f"M2 {where}: {kw} name with spaces or special characters needs single "
                                                f"quotes: {kw} '{name} {rest.split('=')[0].strip()}'"))
            if depth == 0:
                top, table, obj = kw, None, None
                auto = False
                if kw == "table":
                    table = model.tables.setdefault(name.casefold(), Table(name, where))
                    auto = bool(AUTO_DATE.match(name))
                    if auto:
                        model.texts.pop()
                elif kw == "relationship":
                    obj = {"id": name, "where": where}
                    model.relationships.append(obj)
                elif kw == "expression":
                    obj = (name, set())
                    model.expressions.append(obj)
                    obj[1].update(SOURCES.findall(rest))
                continue
            if kw == "column":
                table.columns[name.casefold()] = name
                if rest.startswith("="):
                    table.calculated.append(name)
            elif kw == "measure":
                table.measures[name.casefold()] = name
            elif kw == "partition":
                table.kind = rest.lstrip("=").strip() or table.kind
            elif kw == "hierarchy":
                obj = table.hierarchies.setdefault(name.casefold(), (name, set()))
                continue
            elif kw == "calculationGroup":
                table.kind = "calculationGroup"
            elif kw == "level" and isinstance(obj, tuple):
                obj[1].add(name.casefold())
                continue
            if depth == 1:
                obj = kw
            continue
        if top == "relationship" and isinstance(obj, dict) and depth == 1 and ":" in text:
            key, value = text.split(":", 1)
            obj[key.strip()] = value.strip()
        elif top == "expression" and isinstance(obj, tuple):
            obj[1].update(SOURCES.findall(text))
        elif top == "table" and table is not None and obj == "partition":
            table.sources.update(SOURCES.findall(text))


def _bim(model: Model, f: Path, rel: str) -> None:
    data = _json(f, rel, model.findings) or {}
    m = data.get("model") or {}

    def text(value) -> str:
        return "\n".join(value) if isinstance(value, list) else str(value or "")

    for t in m.get("tables") or []:
        name = t.get("name", "")
        table = model.tables.setdefault(name.casefold(), Table(name, f"{rel} table {name}"))
        auto = bool(AUTO_DATE.match(name))
        for c in t.get("columns") or []:
            if c.get("type") == "rowNumber":
                continue
            table.columns[c.get("name", "").casefold()] = c.get("name", "")
            if c.get("type") == "calculated":
                table.calculated.append(c.get("name", ""))
                if not auto:
                    model.texts.append((f"{rel} table {name} column {c.get('name')}", text(c.get("expression"))))
        for ms in t.get("measures") or []:
            table.measures[ms.get("name", "").casefold()] = ms.get("name", "")
            model.texts.append((f"{rel} table {name} measure {ms.get('name')}", text(ms.get("expression"))))
        for h in t.get("hierarchies") or []:
            table.hierarchies[h.get("name", "").casefold()] = (h.get("name", ""), {lv.get("name", "").casefold()
                                                                                    for lv in h.get("levels") or []})
        for p in t.get("partitions") or []:
            src = p.get("source") or {}
            table.kind = src.get("type") or table.kind
            body = text(src.get("expression"))
            table.sources.update(SOURCES.findall(body))
            if not auto:
                model.texts.append((f"{rel} table {name} partition {p.get('name')}", body))
        if t.get("calculationGroup"):
            table.kind = "calculationGroup"
    for r in m.get("relationships") or []:
        q = lambda t, c: f"'{t}'.'{c}'"
        model.relationships.append({"id": r.get("name", ""), "where": f"{rel} relationship {r.get('name', '')}",
                                    "fromColumn": q(r.get("fromTable", ""), r.get("fromColumn", "")),
                                    "toColumn": q(r.get("toTable", ""), r.get("toColumn", "")),
                                    **{k: str(r[k]).lower() if isinstance(r[k], bool) else r[k]
                                       for k in ("crossFilteringBehavior", "isActive", "fromCardinality", "toCardinality")
                                       if k in r}})
    for e in m.get("expressions") or []:
        body = text(e.get("expression"))
        model.expressions.append((e.get("name", ""), set(SOURCES.findall(body))))
        model.texts.append((f"{rel} expression {e.get('name')}", body))


# ------------------------------------------------------------------ report
def read_report(path: Path) -> ReportDef:
    rep = ReportDef(path)
    base = path.parent
    pbir = path / "definition.pbir"
    if pbir.is_file():
        data = _json(pbir, pbir.relative_to(base).as_posix(), rep.findings) or {}
        ref = data.get("datasetReference") or {}
        if (ref.get("byPath") or {}).get("path"):
            rep.model_path = (path / ref["byPath"]["path"]).resolve()
        elif ref.get("byConnection"):
            rep.connection = "live connection"
    definition = path / "definition"
    if definition.is_dir():
        _pbir(rep, definition, base)
    elif (path / "report.json").is_file():
        rep.fmt = "PBIR-Legacy"
        rep.findings.append(("WARN", f"R9 {path.name}: PBIR-Legacy (report.json) is not meant to be edited outside "
                                     "Desktop; open and save it in a current Desktop to convert it to PBIR first"))
        _legacy(rep, path / "report.json", base)
    else:
        rep.fmt = "?"
        rep.findings.append(("ERROR", f"R0 {path.name}: neither definition/ nor report.json"))
    for f in sorted(path.rglob("*.json")):
        rel = f.relative_to(base)
        if ".pbi" in rel.parts or (definition.is_dir() and definition in f.parents):
            continue
        _json(f, rel.as_posix(), rep.findings)
    return rep


def _filters(conf, where: str, findings: list) -> list:
    filters = (conf or {}).get("filters") or [] if isinstance(conf, dict) else []
    for i, flt in enumerate(filters):
        if isinstance(flt, dict) and not flt.get("name"):
            findings.append(("ERROR", f"R6 {where}: filter {i + 1} has no name; Desktop may refuse to open the report"))
    return _unique(refs(filters))


def _pbir(rep: ReportDef, definition: Path, base: Path) -> None:
    def load(f: Path):
        where = f.relative_to(base).as_posix()
        data = _json(f, where, rep.findings)
        if isinstance(data, dict) and "$schema" not in data:
            rep.findings.append(("WARN", f"R3 {where}: no $schema"))
        return data, where

    for f in sorted(definition.rglob("*.json")):
        if f.name in ("report.json", "pages.json", "page.json", "visual.json", "reportExtensions.json") \
                or f.name.endswith(".bookmark.json") or f.name == "bookmarks.json":
            continue
        load(f)
    data, where = load(definition / "report.json") if (definition / "report.json").is_file() else (None, "")
    if isinstance(data, dict):
        rep.filters = _filters(data.get("filterConfig"), where, rep.findings)
    ext = definition / "reportExtensions.json"
    if ext.is_file():
        data, _ = load(ext)
        for ent in (data or {}).get("entities") or []:
            rep.extension.setdefault(ent.get("name", "").casefold(), set()).update(
                m.get("name", "").casefold() for m in ent.get("measures") or [])
    pages_dir = definition / "pages"
    order = []
    if (pages_dir / "pages.json").is_file():
        data, where = load(pages_dir / "pages.json")
        order = (data or {}).get("pageOrder") or []
        existing = {p.name for p in pages_dir.iterdir() if p.is_dir()}
        for name in order:
            if name not in existing:
                rep.findings.append(("WARN", f"R8 {where}: pageOrder names {name}, which has no folder"))
        active = (data or {}).get("activePageName")
        if active and active not in existing:
            rep.findings.append(("WARN", f"R8 {where}: activePageName {active} has no folder"))
    folders = sorted((p for p in pages_dir.iterdir() if p.is_dir()), key=lambda p: (order.index(p.name) if p.name in order
                                                                                     else len(order), p.name)) \
        if pages_dir.is_dir() else []
    bindings: dict = {}
    for folder in folders:
        _name_check(folder, rep)
        page_file = folder / "page.json"
        if not page_file.is_file():
            rep.findings.append(("ERROR", f"R0 {folder.relative_to(base).as_posix()}: page.json missing"))
            continue
        data, where = load(page_file)
        data = data if isinstance(data, dict) else {}
        _same_name(folder, data, where, rep)
        binding = (data.get("pageBinding") or {}).get("name")
        if binding:
            bindings.setdefault(binding, []).append(folder.name)
        page = Page(folder.name, data.get("displayName", ""), data.get("visibility") == "HiddenInViewMode", [],
                    _filters(data.get("filterConfig"), where, rep.findings))
        for vf in sorted((folder / "visuals").iterdir()) if (folder / "visuals").is_dir() else []:
            if not vf.is_dir():
                continue
            _name_check(vf, rep)
            vfile = vf / "visual.json"
            if not vfile.is_file():
                rep.findings.append(("ERROR", f"R0 {vf.relative_to(base).as_posix()}: visual.json missing"))
                continue
            vdata, vwhere = load(vfile)
            vdata = vdata if isinstance(vdata, dict) else {}
            _same_name(vf, vdata, vwhere, rep)
            visual = vdata.get("visual") or {}
            kind = visual.get("visualType") or ("group" if "visualGroup" in vdata else "?")
            found = refs(visual.get("query")) + _filters(vdata.get("filterConfig"), vwhere, rep.findings)
            page.visuals.append(Visual(vf.name, kind, _title(visual.get("visualContainerObjects")), _unique(found), vwhere))
        rep.pages.append(page)
    for binding, pages in bindings.items():
        if len(pages) > 1:
            rep.findings.append(("ERROR", f"R5 pageBinding.name {binding} on {len(pages)} pages ({', '.join(pages)}); "
                                          "give each page its own"))
    bm = definition / "bookmarks"
    for f in sorted(bm.glob("*.bookmark.json")) if bm.is_dir() else []:
        name = f.name[:-len(".bookmark.json")]
        if not NAME.match(name):
            rep.findings.append(("ERROR", f"R4 {f.relative_to(base).as_posix()}: name {name} not of [A-Za-z0-9_-]"))
        data, where = load(f)
        rep.bookmarks.append((name, _unique(refs(data)), where))
    if (bm / "bookmarks.json").is_file():
        load(bm / "bookmarks.json")


def _name_check(folder: Path, rep: ReportDef) -> None:
    if not NAME.match(folder.name):
        rep.findings.append(("ERROR", f"R4 {folder.relative_to(rep.path.parent).as_posix()}: folder name not of "
                                      "[A-Za-z0-9_-]; Desktop ignores it"))


def _same_name(folder: Path, data: dict, where: str, rep: ReportDef) -> None:
    if data.get("name") and data["name"] != folder.name:
        rep.findings.append(("WARN", f"R4 {where}: name {data['name']} differs from its folder {folder.name}"))


def _legacy(rep: ReportDef, f: Path, base: Path) -> None:
    where = f.relative_to(base).as_posix()
    data = _json(f, where, rep.findings) or {}
    config = _loads(data.get("config")) or {}
    for ext in config.get("modelExtensions") or [] if isinstance(config, dict) else []:
        for ent in ext.get("entities") or []:
            rep.extension.setdefault(ent.get("name", "").casefold(), set()).update(
                m.get("name", "").casefold() for m in ent.get("measures") or [])
    rep.filters = _unique(refs(_loads(data.get("filters"))))
    for s in data.get("sections") or []:
        sconf = _loads(s.get("config")) or {}
        page = Page(s.get("name", ""), s.get("displayName", ""), isinstance(sconf, dict) and sconf.get("visibility") == 1,
                    [], _unique(refs(_loads(s.get("filters")))))
        for i, vc in enumerate(s.get("visualContainers") or [], 1):
            vconf = _loads(vc.get("config")) or {}
            single = vconf.get("singleVisual") or {} if isinstance(vconf, dict) else {}
            kind = single.get("visualType") or ("group" if isinstance(vconf, dict) and "singleVisualGroup" in vconf else "?")
            found = refs(vconf) + refs(_loads(vc.get("filters"))) + refs(_loads(vc.get("query")))
            page.visuals.append(Visual(vconf.get("name", str(i)) if isinstance(vconf, dict) else str(i), kind,
                                       _title(single.get("vcObjects")), _unique(found),
                                       f"{where} page {s.get('displayName') or s.get('name')} visual {i}"))
        rep.pages.append(page)


# ------------------------------------------------------------------ loading
def load(target: Path) -> tuple[dict, list]:
    """Models (path -> Model) and reports below target: a folder, a .pbip file or one item folder."""
    target = target.resolve()
    if target.is_file() and target.suffix.lower() == ".pbip":
        dirs = [d for d in (target.with_suffix(".SemanticModel"), target.with_suffix(".Report")) if d.is_dir()]
    elif target.is_dir() and target.suffix in (".SemanticModel", ".Report"):
        dirs = [target]
    elif target.is_dir():
        dirs = sorted(d for d in target.rglob("*") if d.is_dir() and d.suffix in (".SemanticModel", ".Report")
                      and ".pbi" not in d.relative_to(target).parts)
    else:
        dirs = []
    if not dirs:
        pbix = sorted(target.rglob("*.pbix")) if target.is_dir() else ([target] if target.suffix.lower() == ".pbix" else [])
        hint = (f" Found PBIX ({', '.join(p.name for p in pbix[:3])}); ppp reads PBIP only." if pbix else "")
        raise ToolError(f"No PBIP at {target}.{hint} Open the file in Power BI Desktop and save it with File › Save as › "
                        "Power BI project (.pbip), on a short path outside OneDrive and SharePoint.")
    models = {d: read_model(d) for d in dirs if d.suffix == ".SemanticModel"}
    reports = [read_report(d) for d in dirs if d.suffix == ".Report"]
    for r in reports:
        if r.model_path and r.model_path not in models and r.model_path.is_dir():
            models[r.model_path] = read_model(r.model_path)
    return models, reports


# ------------------------------------------------------------------ list
def _rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def listing(models: dict, reports: list, base: Path) -> list[str]:
    out = []
    for path, m in models.items():
        tables = [t for t in m.tables.values() if not AUTO_DATE.match(t.name)]
        auto = len(m.tables) - len(tables)
        rels = [r for r in m.relationships if not any(AUTO_DATE.match(qualified(r.get(k, ""))[0])
                                                      for k in ("fromColumn", "toColumn"))]
        out.append(f"model {_rel(path, base)} ({m.fmt}): {len(tables)} tables, "
                   f"{sum(len(t.measures) for t in tables)} measures, {len(rels)} relationships, "
                   f"{len(m.expressions)} expressions")
        for t in sorted(tables, key=lambda t: t.name.casefold()):
            src = f" [{t.kind}{': ' + ', '.join(sorted(t.sources)) if t.sources else ''}]" if t.kind or t.sources else ""
            plain = [c for c in t.columns.values() if c not in t.calculated]
            line = f"table {t.name}{src} columns({len(plain)}): {', '.join(plain)}"
            if t.calculated:
                line += f" | calculated({len(t.calculated)}): {', '.join(t.calculated)}"
            if t.measures:
                line += f" | measures({len(t.measures)}): {', '.join(t.measures.values())}"
            if t.hierarchies:
                line += " | hierarchies: " + ", ".join(n for n, _ in t.hierarchies.values())
            out.append(line)
        if auto:
            out.append(f"auto date tables: {auto} (LocalDateTable_*, not listed; Desktop option Auto date/time)")
        for r in rels:
            (ft, fc), (tt, tc) = qualified(r.get("fromColumn", "")), qualified(r.get("toColumn", ""))
            card = f"{r.get('fromCardinality', 'many')}:{r.get('toCardinality', 'one')}"
            extra = (", both" if r.get("crossFilteringBehavior") == "bothDirections" else "") + \
                    (", inactive" if str(r.get("isActive", "true")).lower() == "false" else "")
            out.append(f"rel {ft}.{fc} -> {tt}.{tc} {card}{extra}")
        for name, sources in m.expressions:
            out.append(f"expression {name}" + (f" [{', '.join(sorted(sources))}]" if sources else ""))
    for r in reports:
        target = _rel(r.model_path, base) if r.model_path else (r.connection or "no model reference")
        out.append(f"report {_rel(r.path, base)} ({r.fmt}) -> {target}: {len(r.pages)} pages, {len(r.bookmarks)} bookmarks"
                   + (f"; filters: {', '.join(map(show, r.filters))}" if r.filters else ""))
        for p in r.pages:
            out.append(f"page {p.name} \"{p.display}\"{' hidden' if p.hidden else ''}: {len(p.visuals)} visuals"
                       + (f"; filters: {', '.join(map(show, p.filters))}" if p.filters else ""))
            for v in p.visuals:
                title = f" \"{v.title}\"" if v.title else ""
                out.append(f"  {v.type} {v.name}{title}: {', '.join(map(show, v.refs)) or '-'}")
    return out


# ------------------------------------------------------------------ check
def _missing(ref, model: Model, extension: dict) -> str | None:
    kind, ent, prop, level = ref
    table = model.tables.get(ent.casefold())
    if table is None:
        return f"table {ent} is not in the model"
    p = prop.casefold()
    if kind == "column" and p not in table.columns:
        return f"{ent}.{prop} is a measure, referenced as a column" if p in table.measures else \
            f"column {ent}.{prop} is not in the model"
    if kind == "measure" and p not in table.measures and p not in extension.get(ent.casefold(), set()):
        return f"{ent}.{prop} is a column, referenced as a measure" if p in table.columns else \
            f"measure {ent}.{prop} is not in the model"
    if kind == "hierarchy":
        h = table.hierarchies.get(p)
        if h is None:
            return f"hierarchy {ent}.{prop} is not in the model"
        if level and level.casefold() not in h[1]:
            return f"level {level} is not in hierarchy {ent}.{prop}"
    return None


def check(models: dict, reports: list, rep: Report, base: Path) -> str:
    n_refs = 0
    for path, m in models.items():
        for level, msg in m.findings:
            rep.add(level, msg)
        for r in m.relationships:
            for key in ("fromColumn", "toColumn"):
                t, c = qualified(r.get(key, ""))
                table = m.tables.get(t.casefold())
                if not t or table is None or c.casefold() not in table.columns:
                    rep.error(f"M3 {r['where']}: {key} {t}.{c} is not a column of the model")
        for where, text in m.texts:
            for found in M_TIME.findall(text) + [x.strip(" (") for x in DAX_TIME.findall(text)]:
                rep.error(f"M4 {where}: {found} {TIME_HINT}")
    for r in reports:
        for level, msg in r.findings:
            rep.add(level, msg)
        model = models.get(r.model_path) if r.model_path else None
        if model is None:
            rep.info(f"R7 {r.path.name}: {r.connection or 'model not found'}; field references not checked")
            continue
        items = [(r.path.name + "/definition/report.json filters", r.filters)]
        items += [(f"page {p.name} filters", p.filters) for p in r.pages]
        items += [(v.where, v.refs) for p in r.pages for v in p.visuals]
        items += [(where, found) for _, found, where in r.bookmarks]
        for where, found in items:
            for ref in found:
                n_refs += 1
                problem = _missing(ref, model, r.extension)
                if problem:
                    rep.error(f"R7 {where}: {problem}")
    _paths(models, reports, rep, base)
    _git(models, reports, rep)
    n_vis = sum(len(p.visuals) for r in reports for p in r.pages)
    return (f"Checked: {len(models)} models ({sum(len(m.tables) for m in models.values())} tables), {len(reports)} reports "
            f"({sum(len(r.pages) for r in reports)} pages, {n_vis} visuals, {n_refs} field references)")


def _paths(models: dict, reports: list, rep: Report, base: Path) -> None:
    longest = None
    for d in [*models, *(r.path for r in reports)]:
        for f in d.rglob("*"):
            if ".pbi" in f.relative_to(d).parts:
                continue
            length = len(str(f)) if os.name == "nt" else len(_rel(f, base))
            if longest is None or length > longest[0]:
                longest = (length, f)
    if not longest:
        return
    if os.name == "nt" and longest[0] > 259:
        rep.error(f"P1 path of {longest[0]} characters ({longest[1].name}); Windows allows 259: move the project to a "
                  "shorter folder")
    elif os.name != "nt" and longest[0] > 200:
        rep.warn(f"P1 {_rel(longest[1], base)} has {longest[0]} characters; under Windows the project folder may then "
                 "use only 59 characters")


def _git(models: dict, reports: list, rep: Report) -> None:
    dirs = [*models, *(r.path for r in reports)]
    try:
        top = gitutil.git(dirs[0], "rev-parse", "--show-toplevel", check=False).decode("utf-8").strip()
    except ToolError:
        top = ""
    if not top:
        rep.info("G1 not in a git repository; .pbi/cache.abf and .pbi/localSettings.json not checked")
        return
    root = Path(top)
    for d in dirs:
        for name in DATA_FILES if d.suffix == ".SemanticModel" else DATA_FILES[1:]:
            rel = gitutil.rel(root, d / ".pbi") + "/" + name
            if gitutil.git(root, "ls-files", "--", rel, check=False).strip():
                rep.error(f"G1 {rel} is in git; it holds local {'data' if name == 'cache.abf' else 'settings'}: "
                          f"git rm --cached \"{rel}\"")
            elif not gitutil.git(root, "check-ignore", "--no-index", rel, check=False).strip():
                rep.error(f"G1 {rel} is not ignored; add **/.pbi/cache.abf and **/.pbi/localSettings.json to .gitignore")
