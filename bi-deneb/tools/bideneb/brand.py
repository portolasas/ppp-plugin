"""Brand profile: colours as tokens, roles for charts, contrast, the Vega config.

A profile has a name and two files: tokens.json (the colours; same format as the skill bi-designer of the plugin
bi-design) and charts.json (what a chart needs beyond the tokens: palettes, sizes, what must not be text). The
tokens.json of the corporate design is a copy of the one of the plugin bi-design beside this plugin in the repository
(skills/bi-designer/marken/<name>); a test keeps the two identical."""
import json
import os
import re
from pathlib import Path

BRANDS = Path(__file__).resolve().parent.parent.parent / "brands"
DEFAULT = "boehringer-ingelheim"     # the corporate design
FALLBACK = "neutral"                 # for a profile that cannot be loaded
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
CSS_NAMES = {"white": "#FFFFFF", "black": "#000000", "transparent": None, "none": None}


def norm(value: str) -> str | None:
    """#RRGGBB in upper case, or None for no colour, or '' if value is not a plain colour."""
    if not isinstance(value, str):
        return ""
    v = value.strip()
    if v.lower() in CSS_NAMES:
        return CSS_NAMES[v.lower()]
    if HEX.match(v):
        v = v[1:]
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        return "#" + v[:6].upper()
    m = re.match(r"^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)", v, re.I)
    if m:
        return "#" + "".join(f"{min(255, int(x)):02X}" for x in m.groups())
    return ""


def luminance(hexv: str) -> float:
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hexv[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def distance(a: str, b: str) -> float:
    return sum((int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) ** 2 for i in (1, 3, 5)) ** 0.5


class Brand:
    def __init__(self, folder: Path, tokens: Path | None = None):
        self.folder = folder
        self.name = folder.name
        self.tokens_file = tokens or folder / "tokens.json"
        self.tokens = json.loads(self.tokens_file.read_text(encoding="utf-8"))
        self.charts = json.loads((folder / "charts.json").read_text(encoding="utf-8"))
        self.colors = {k: norm(v["hex"]) for k, v in self.tokens["colors"].items()}
        self.by_hex = {}
        for k, v in self.colors.items():
            self.by_hex.setdefault(v, k)

    # ---- values
    def hex(self, token: str) -> str:
        if token not in self.colors:
            raise KeyError(f"brand {self.name}: no colour token '{token}'")
        return self.colors[token]

    def c(self, role: str) -> str:
        """Hex of a chart role (text, grid, focus, good ...)."""
        v = self.charts[role]
        if isinstance(v, dict):
            v = v["color"]
        return self.hex(v)

    def palette(self, kind: str) -> list[str]:
        v = self.charts[kind]
        if isinstance(v, dict):
            v = v["colors"]
        return [self.hex(t) for t in v]

    def status(self, key: str) -> tuple[str, str]:
        s = self.charts["status"][key]
        return self.hex(s["fill"]), self.hex(s["text"])

    def traffic(self) -> dict:
        return {k: self.hex(v) for k, v in self.charts["trafficLight"].items()}

    @property
    def font(self) -> str:
        return self.charts["font"]

    def size(self, key: str) -> int:
        return self.charts["size"][key]

    def token_of(self, hexv: str) -> str | None:
        return self.by_hex.get(hexv)

    def nearest(self, hexv: str) -> tuple[str, str]:
        token = min(self.colors, key=lambda t: distance(self.colors[t], hexv))
        return token, self.colors[token]

    def text_on(self, fill: str) -> str:
        """The text colour of the brand for a label on this fill."""
        for s in self.charts["status"].values():
            if self.hex(s["fill"]) == fill:
                return self.hex(s["text"])
        dark, light = self.c("text"), self.hex("white")
        return dark if contrast(dark, fill) >= contrast(light, fill) else light

    def is_token(self, hexv: str) -> bool:
        return hexv in self.by_hex

    def tokens_in(self, key: str) -> set[str]:
        return {self.hex(t) for t in self.charts.get(key, []) if t in self.colors}

    # ---- Vega / Vega-Lite config
    def config(self, provider: str = "vegaLite") -> dict:
        text, sec, grid = self.c("text"), self.c("textSecondary"), self.c("grid")
        label, title = self.size("label"), self.size("title")
        cfg = {
            "background": None if provider == "vega" else "transparent",
            "font": self.font,
            "title": {"color": text, "fontSize": title, "fontWeight": 600, "anchor": "start", "offset": 12,
                      "subtitleColor": sec, "subtitleFontSize": self.size("subtitle"), "subtitleFontWeight": 400,
                      "subtitlePadding": 4},
            "axis": {"labelColor": text, "titleColor": text, "labelFontSize": label, "titleFontSize": label,
                     "titleFontWeight": 400, "gridColor": grid, "domainColor": grid, "tickColor": grid,
                     "labelPadding": 6, "titlePadding": 8, "ticks": False, "domain": False, "grid": False,
                     "labelLimit": 220},
            "legend": {"labelColor": text, "titleColor": text, "labelFontSize": label, "titleFontSize": label,
                       "titleFontWeight": 400, "symbolType": "square", "symbolSize": 120, "orient": "top",
                       "direction": "horizontal", "labelLimit": 220},
            "text": {"font": self.font, "fontSize": label, "fill": text},
            "range": {"category": self.palette("category"), "ordinal": self.palette("sequential"),
                      "ramp": self.palette("sequential"), "heatmap": self.palette("sequential"),
                      "diverging": self.palette("diverging")},
        }
        if provider == "vega":
            cfg.pop("background")
            cfg["axis"]["grid"] = False
        else:
            cfg["view"] = {"stroke": None}
            cfg["line"] = {"strokeWidth": 2.5, "strokeCap": "round", "strokeJoin": "round"}
            cfg["point"] = {"size": 60, "filled": True}
            cfg["header"] = {"labelColor": text, "titleColor": text, "labelFontSize": label, "titleFontSize": label,
                             "labelFontWeight": 600, "labelAnchor": "start", "labelOrient": "top", "labelPadding": 6}
            cfg["axisX"] = {"labelAngle": 0}
            cfg["customFormatTypes"] = True
        return cfg


def folders() -> list[Path]:
    """Profile folders: BIDENEB_BRANDS (os.pathsep separated), then the ones of the plugin."""
    return [Path(p) for p in os.environ.get("BIDENEB_BRANDS", "").split(os.pathsep) if p] + [BRANDS]


def _files(name: str) -> tuple[Path | None, Path | None]:
    """(folder with charts.json, tokens.json) of a profile; None for the part that is missing."""
    charts = next((b / name for b in folders() if (b / name / "charts.json").is_file()), None)
    tokens = next((b / name / "tokens.json" for b in folders() if (b / name / "tokens.json").is_file()), None)
    return charts, tokens


def names() -> list[str]:
    """Every profile with a charts.json, complete or not."""
    out = []
    for base in folders():
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if (d / "charts.json").is_file() and d.name not in out:
                    out.append(d.name)
    return out


def available() -> list[str]:
    """The profiles that can be loaded here: charts.json and tokens.json found."""
    return [n for n in names() if None not in _files(n)]


def missing(name: str) -> str:
    """Why a profile cannot be loaded, with the way out; '' when it can."""
    charts, tokens = _files(name)
    if charts is None:
        return f"brand profile '{name}' not found; available: {', '.join(available()) or 'none'}"
    if tokens is None:
        return f"brand profile '{name}' has no tokens.json beside its charts.json ({charts})"
    return ""


def default() -> str:
    """The profile a new visual gets: the corporate design; the neutral one if its files are damaged."""
    return DEFAULT if not missing(DEFAULT) else FALLBACK


def load(name: str | None = None) -> Brand:
    name = name or default()
    p = Path(name)
    if (p.is_absolute() or len(p.parts) > 1) and (p / "charts.json").is_file():   # a profile given as its folder
        tokens = p / "tokens.json" if (p / "tokens.json").is_file() else _files(p.name)[1]
        if tokens is None:
            raise FileNotFoundError(missing(p.name) or f"{p}: tokens.json is missing")
        return Brand(p, tokens)
    why = missing(name)
    if why:
        raise FileNotFoundError(why)
    charts, tokens = _files(name)
    return Brand(charts, tokens)
