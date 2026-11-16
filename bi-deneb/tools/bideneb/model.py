"""Read the semantic model of a Power BI project (TMDL): tables, columns, measures. Metadata only, never rows."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DECL = re.compile(r"^(table|column|measure|hierarchy|partition|calculationGroup)\b ?(.*)$")
AUTO_DATE = re.compile(r"^(LocalDateTable_|DateTableTemplate_)", re.I)
NUMERIC = {"int64", "double", "decimal", "currency"}
TEMPORAL = {"datetime", "date", "time"}


@dataclass
class Field:
    table: str
    name: str
    kind: str                 # column | measure
    data_type: str = ""       # string, int64, double, decimal, dateTime, boolean; measures: guessed from the format
    format: str = ""
    hidden: bool = False
    summarize: str = ""
    category: str = ""
    sort_by: str = ""
    description: str = ""

    @property
    def role(self) -> str:
        """quantitative | temporal | nominal: how a chart can use the field."""
        t = self.data_type.casefold()
        if self.kind == "measure":
            return "temporal" if t in TEMPORAL else "nominal" if t == "string" else "quantitative"
        if t in TEMPORAL:
            return "temporal"
        if t in NUMERIC and self.summarize.casefold() not in ("none", ""):
            return "quantitative"
        return "nominal"

    @property
    def numeric(self) -> bool:
        return self.data_type.casefold() in NUMERIC

    @property
    def ref(self) -> str:
        return f"{self.table}[{self.name}]"


@dataclass
class Table:
    name: str
    hidden: bool = False
    fields: dict = field(default_factory=dict)   # casefold name -> Field


@dataclass
class Model:
    path: Path
    tables: dict = field(default_factory=dict)   # casefold name -> Table
    culture: str = ""

    def find(self, table: str, name: str) -> Field | None:
        t = self.tables.get(table.casefold())
        return t.fields.get(name.casefold()) if t else None

    def search(self, name: str) -> list[Field]:
        return [f for t in self.tables.values() for f in t.fields.values() if f.name.casefold() == name.casefold()]


def tmdl_name(rest: str) -> tuple[str, str]:
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
    m = re.match(r"[^\s=:']+", rest)
    return (m.group(0), rest[m.end():].lstrip()) if m else ("", rest)


def _measure_type(fmt: str) -> str:
    f = fmt.casefold()
    if not f:
        return "double"
    if re.search(r"(?<![a-z])(yyyy|dd|mm/|hh:|h:mm|general date|short date|long date)", f):
        return "dateTime"
    return "double"


def read(path: Path) -> Model:
    """path: the <Name>.SemanticModel folder."""
    model = Model(path)
    definition = path / "definition"
    if not definition.is_dir():
        raise FileNotFoundError(f"{path}: no definition/ folder with TMDL files; save the report as Power BI project "
                                f"(.pbip) with the TMDL format")
    for f in sorted(definition.rglob("*.tmdl")):
        _tmdl(model, f)
    for t in model.tables.values():
        for fld in t.fields.values():
            if fld.kind == "measure" and not fld.data_type:
                fld.data_type = _measure_type(fld.format)
    return model


def _tmdl(model: Model, f: Path) -> None:
    table = cur = None
    fence = False
    doc = ""
    for raw in f.read_text(encoding="utf-8-sig").splitlines():
        text = raw.strip()
        if fence:
            if text.endswith("```"):
                fence = False
            continue
        if not text:
            continue
        if text.startswith("///"):
            doc = (doc + " " + text[3:].strip()).strip()
            continue
        depth = len(raw) - len(raw.lstrip("\t"))
        if text.count("```") == 1:
            fence = True
        m = DECL.match(text)
        if m and depth == 0:
            cur = None
            table = None
            if m.group(1) == "table":
                name, _ = tmdl_name(m.group(2))
                if not AUTO_DATE.match(name):
                    table = model.tables.setdefault(name.casefold(), Table(name))
            doc = ""
            continue
        if depth == 0:
            table = cur = None
            mm = re.match(r"^cultureInfo\s+(\S+)", text)
            if mm and not model.culture:
                model.culture = mm.group(1)
            doc = ""
            continue
        if table is None:
            mm = re.match(r"^culture:\s*(\S+)", text)
            if mm:
                model.culture = mm.group(1)
            continue
        if m and depth == 1:
            kw = m.group(1)
            name, _ = tmdl_name(m.group(2))
            cur = None
            if kw in ("column", "measure"):
                cur = Field(table.name, name, kw, description=doc)
                table.fields[name.casefold()] = cur
            doc = ""
            continue
        if depth == 1 and text == "isHidden":
            table.hidden = True
        if depth == 2 and cur is not None:
            if text == "isHidden":
                cur.hidden = True
            elif ":" in text:
                key, value = (x.strip() for x in text.split(":", 1))
                if key == "dataType":
                    cur.data_type = value
                elif key == "formatString":
                    cur.format = value
                elif key == "summarizeBy":
                    cur.summarize = value
                elif key == "dataCategory":
                    cur.category = value
                elif key == "sortByColumn":
                    cur.sort_by = tmdl_name(value)[0]
        doc = ""


# ---------------------------------------------------------------- project
@dataclass
class Project:
    report: Path | None       # <Name>.Report
    model: Path | None        # <Name>.SemanticModel


def locate(target: Path) -> list[Project]:
    """Reports and their models at or below target (a folder, a .pbip, a .Report or a .SemanticModel folder)."""
    target = target.resolve()
    if target.is_file() and target.suffix.casefold() == ".pbip":
        reports = [target.with_suffix("").parent / (target.stem + ".Report")]
    elif target.name.endswith(".Report"):
        reports = [target]
    elif target.name.endswith(".SemanticModel"):
        return [Project(None, target)]
    elif target.is_dir():
        reports = sorted(p for p in target.rglob("*.Report") if p.is_dir() and ".git" not in p.parts)
        if not reports:
            return [Project(None, m) for m in sorted(target.rglob("*.SemanticModel")) if m.is_dir()]
    else:
        raise FileNotFoundError(f"{target}: not a Power BI project (folder, .pbip, .Report or .SemanticModel)")
    out = []
    for r in reports:
        if not r.is_dir():
            raise FileNotFoundError(f"{r}: report folder missing")
        out.append(Project(r, model_of(r)))
    return out


def model_of(report: Path) -> Path | None:
    pbir = report / "definition.pbir"
    if pbir.is_file():
        try:
            ref = json.loads(pbir.read_text(encoding="utf-8-sig")).get("datasetReference", {})
            rel = (ref.get("byPath") or {}).get("path")
            if rel:
                p = (report / rel).resolve()
                if p.is_dir():
                    return p
        except (json.JSONDecodeError, OSError):
            pass
    guess = report.with_name(report.name[:-len(".Report")] + ".SemanticModel")
    return guess if guess.is_dir() else None


def listing(model: Model, show_hidden: bool = False) -> list[str]:
    lines = []
    for t in sorted(model.tables.values(), key=lambda t: t.name.casefold()):
        fields = [f for f in t.fields.values() if show_hidden or not f.hidden]
        if not fields or (t.hidden and not show_hidden):
            continue
        lines.append(f"{t.name}")
        for f in sorted(fields, key=lambda f: (f.kind != "measure", f.name.casefold())):
            extra = [f.kind, f.role + (" (a number: usable as value with one row per value)"
                                       if f.kind == "column" and f.numeric and f.role == "nominal" else ""),
                     f.data_type or "?"]
            if f.format:
                extra.append(f"format {f.format}")
            if f.sort_by:
                extra.append(f"sorted by {f.sort_by}")
            if f.hidden:
                extra.append("hidden")
            lines.append(f"  {f.name}  ({', '.join(extra)})")
    return lines
