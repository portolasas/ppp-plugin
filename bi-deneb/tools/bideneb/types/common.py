"""What all visual types share: fields of a brief, the registry, building blocks for Vega-Lite."""
from dataclasses import dataclass, field

from .. import deneb

VL_SCHEMA = "https://vega.github.io/schema/vega-lite/v6.json"
VEGA_SCHEMA = "https://vega.github.io/schema/vega/v6.json"
VL_TYPE = {"quantitative": "quantitative", "temporal": "temporal", "nominal": "nominal", "ordinal": "ordinal"}
DIM = 0.3   # opacity of rows another selection leaves out

LOCALE_DE = {
    "number": {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["", " €"]},
    "time": {"dateTime": "%A, %e. %B %Y, %X", "date": "%d.%m.%Y", "time": "%H:%M:%S", "periods": ["AM", "PM"],
             "days": ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"],
             "shortDays": ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"],
             "months": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                        "November", "Dezember"],
             "shortMonths": ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]},
}


TIME_DE = {"year": "%Y", "quarter": "Q%q %Y", "month": "%b %y", "week": "%d.%m.", "date": "%a %d.%m.",
           "day": "%a %d.%m.", "hours": "%H:%M", "minutes": "%H:%M", "seconds": "%H:%M:%S"}


class BriefError(Exception):
    pass


@dataclass
class F:
    """One field of the dataset."""
    role: str
    table: str
    name: str                # name in the model
    kind: str                # column | measure
    type: str                # quantitative | temporal | nominal
    format: str = ""         # Power BI format string
    label: str = ""          # text for people (axis, tooltip, legend); default: the display name
    display: str = ""        # display name in the Values well when it differs from the model name
    key: str = ""            # key in the dataset
    numeric: bool = False    # a numeric column that the model does not summarise: may serve as a value

    def __post_init__(self):
        self.display = self.display or self.name
        self.key = deneb.encode(self.display)
        self.label = self.label or self.display

    @property
    def percent(self) -> bool:
        return "%" in self.format

    @property
    def fmt(self) -> str:
        if self.format:
            return self.format
        return "dd.MM.yyyy" if self.type == "temporal" else "#,0.##" if self.type == "quantitative" else ""


@dataclass
class Role:
    name: str
    kinds: tuple = ("nominal",)
    required: bool = True
    multiple: bool = False
    help: str = ""
    only: str = ""           # column | measure when the role takes only one of them


@dataclass
class Option:
    name: str
    default: object
    help: str
    choices: tuple = ()


class Ctx:
    """A brief resolved against the brand: what a type needs to build its specification."""

    def __init__(self, brief: dict, brand, fields: dict, selection: bool = True):
        self.brief = brief
        self.brand = brand
        self.fields = fields            # role -> F or [F]
        self.options = brief.get("options", {}) or {}
        self.interaction = {"tooltip": True, "crossFilter": selection, "highlight": False,
                            **(brief.get("interaction") or {})}
        self.locale = brief.get("locale") or "de-DE"
        self.background = "#FFFFFF"     # the page colour the visual is drawn for (brief.resolve sets it)
        self.page_background = None     # the colour of its page in the report, when known

    def f(self, role: str) -> F | None:
        v = self.fields.get(role)
        return v[0] if isinstance(v, list) and v else (v if isinstance(v, F) else None)

    def fs(self, role: str) -> list:
        v = self.fields.get(role)
        return v if isinstance(v, list) else [v] if v else []

    def all(self) -> list:
        out = []
        for v in self.fields.values():
            for f in (v if isinstance(v, list) else [v]):
                if f.key not in [o.key for o in out]:
                    out.append(f)
        return out

    def opt(self, name: str, default=None):
        return self.options.get(name, default)

    @property
    def select(self) -> bool:
        return bool(self.interaction.get("crossFilter"))


class VisualType:
    id = ""
    title = ""
    use = ""                 # when this type is the right one
    avoid = ""               # when it is not
    provider = "vegaLite"
    roles: list = []
    options: list = []
    selection = True         # rows stay rows, so a click can cross-filter
    min_size = (240, 160)
    default_size = (640, 360)

    def build(self, c: Ctx) -> dict:
        raise NotImplementedError

    def sample(self, c: Ctx, scenario: str, rng) -> list | None:
        """Rows for the preview; None takes the generic generator."""
        return None

    def config(self, c: Ctx) -> dict:
        return base_config(c, self.provider)

    def option(self, c: Ctx, name: str):
        for o in self.options:
            if o.name == name:
                return c.opt(name, o.default)
        raise KeyError(name)


TYPES: dict = {}


def register(cls):
    TYPES[cls.id] = cls()
    return cls


# ---------------------------------------------------------------- Vega-Lite building blocks
def base_config(c: Ctx, provider: str = "vegaLite") -> dict:
    cfg = c.brand.config(provider)
    if c.locale.casefold().startswith("de"):
        cfg["locale"] = LOCALE_DE
        if provider == "vegaLite":
            cfg["axisTemporal"] = {"format": TIME_DE}
    return cfg


def vl(c: Ctx, **body) -> dict:
    spec = {"$schema": VL_SCHEMA, "description": c.brief.get("description") or c.brief.get("title") or c.brief["name"],
            "data": {"name": "dataset"}}
    t = title(c)
    if t:
        spec["title"] = t
    spec.update(body)
    return spec


def title(c: Ctx):
    if not c.brief.get("title"):
        return None
    t = {"text": c.brief["title"]}
    if c.brief.get("subtitle"):
        t["subtitle"] = c.brief["subtitle"]
    return t


def enc(f: F, **extra) -> dict:
    return {"field": fk(f.key), "type": VL_TYPE[f.type], **extra}


def num(f: F) -> dict:
    """Format of a value the way the report formats it."""
    return {"format": f.fmt, "formatType": "pbiFormat"}


def text_enc(f: F) -> dict:
    return {"field": fk(f.key), "type": "quantitative" if f.type == "quantitative" else VL_TYPE[f.type], **num(f)} \
        if f.type != "nominal" else {"field": fk(f.key), "type": "nominal"}


def tooltip(c: Ctx, *fields) -> list:
    out, seen = [], set()
    for f in fields:
        if f is None or f.key in seen:
            continue
        seen.add(f.key)
        t = {"field": fk(f.key), "type": VL_TYPE[f.type], "title": f.label}
        if f.type != "nominal":
            t.update(num(f))
        out.append(t)
    return out


def dim(c: Ctx, base: float = 1) -> dict:
    """Opacity that fades the rows a cross-filter selection leaves out."""
    if not c.select:
        return {"value": base}
    return {"condition": {"test": {"field": "__selected__", "equal": "off"}, "value": round(base * DIM, 2)},
            "value": base}


def legend(**extra) -> dict:
    """A legend above the plot that wraps to the width of the container."""
    return {"title": None, "orient": "top", "direction": "horizontal", "labelLimit": 110,
            "columns": {"expr": "max(1, floor(denebContainer.width * 0.7 / 135))"}, **extra}


def axis_q(f: F, **extra) -> dict:
    return {"title": None, "grid": True, "tickCount": 5, **num(f), **extra}


def d(key: str) -> str:
    """A dataset field inside an expression: datum['key'], with \\ and ' escaped."""
    return "datum[" + q(key) + "]"


def fk(key: str) -> str:
    """A dataset field as a field name of Vega or Vega-Lite, where ' and \\ start an access path."""
    return str(key).replace("\\", "\\\\").replace("'", "\\'")


def q(text: str) -> str:
    return "'" + str(text).replace("\\", "\\\\").replace("'", "\\'") + "'"
