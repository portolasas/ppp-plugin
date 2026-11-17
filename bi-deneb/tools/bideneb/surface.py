"""Backgrounds of a Power BI report in PBIR: the colour a page shows, the box of a visual on it, the theme colours.

The same file lies in the plugin ppp (tools/ppplib/surface.py) and in the plugin bi-deneb (tools/bideneb/surface.py);
a test keeps the two identical. Standard library only.

Defaults of Power BI (Microsoft Learn, "Use visual elements to enhance Power BI reports"): the page background (the
canvas) is white with transparency 100 %, so the wallpaper shows through it; the wallpaper is white and opaque. A
visual without its own background takes the one of the theme (visualStyles: the custom theme over the base theme,
property by property, the visual type over "*"); the base themes of Desktop show a white, opaque box for every visual
except shapes, images, groups, buttons and navigators. A theme colour (ThemeDataColor) is 0 the background, 1 the
foreground, from 2 on the data colours of the theme; Percent lightens (above 0) or darkens (below 0)."""
from __future__ import annotations

import json
import re
from pathlib import Path

WHITE = "#FFFFFF"
DARK = 0.2                   # relative luminance below which a background counts as dark
HEX = re.compile(r"^#([0-9A-Fa-f]{6})$")


# ------------------------------------------------------------------ colours
def norm(value) -> str | None:
    if isinstance(value, str):
        v = value.strip().strip("'")
        if HEX.match(v):
            return v.upper()
    return None


def luminance(hexv: str) -> float:
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hexv[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def is_dark(hexv: str) -> bool:
    return luminance(hexv) < DARK


def kind(hexv: str) -> str:
    return "dark" if is_dark(hexv) else "light"


def mix(front: str, back: str, transparency: float) -> str:
    """front over back; transparency 0 shows front, 100 shows back."""
    t = min(100.0, max(0.0, float(transparency))) / 100
    parts = [round(int(front[i:i + 2], 16) * (1 - t) + int(back[i:i + 2], 16) * t) for i in (1, 3, 5)]
    return "#" + "".join(f"{p:02X}" for p in parts)


def shade(hexv: str, percent: float) -> str:
    p = float(percent or 0)
    out = []
    for i in (1, 3, 5):
        c = int(hexv[i:i + 2], 16)
        out.append(round(c + (255 - c) * p) if p > 0 else round(c * (1 + p)))
    return "#" + "".join(f"{min(255, max(0, c)):02X}" for c in out)


# ------------------------------------------------------------------ literals
def literal(node):
    """The value of a PBIR literal ({"expr": {"Literal": {"Value": "'#08312A'"}}}): text, number or bool; theme JSON
    values pass through."""
    if isinstance(node, dict) and "expr" in node:
        text = ((node.get("expr") or {}).get("Literal") or {}).get("Value")
        if not isinstance(text, str):
            return None
        if text in ("true", "false"):
            return text == "true"
        if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
            return text[1:-1].replace("''", "'")
        m = re.fullmatch(r"(-?\d+(?:\.\d+)?)[DLM]?", text)
        return float(m.group(1)) if m else None
    return node


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ theme
class Theme:
    """Base theme and custom theme of a report, the custom one over the base one."""

    def __init__(self, report: Path):
        self.data: dict = {}
        self.names: list = []
        rep = _read(report / "definition" / "report.json") or {}
        coll = rep.get("themeCollection") or {}
        for key in ("baseTheme", "customTheme"):
            t = coll.get(key)
            if not isinstance(t, dict) or not t.get("name"):
                continue
            name = str(t["name"])
            folders = ["RegisteredResources", "SharedResources/BaseThemes"]
            if t.get("type") == "SharedResources" or key == "baseTheme":
                folders.reverse()
            found = next((p for f in folders for p in (report / "StaticResources" / f / name,
                                                       report / "StaticResources" / f / f"{name}.json") if p.is_file()),
                         None)
            data = _read(found) if found else None
            if isinstance(data, dict):
                self.names.append(name)
                self._merge(data)

    def _merge(self, data: dict) -> None:
        for k, v in data.items():
            if k == "visualStyles" and isinstance(v, dict):
                vs = self.data.setdefault("visualStyles", {})
                for visual, sel in v.items():
                    if isinstance(sel, dict):
                        for s, objs in sel.items():
                            if isinstance(objs, dict):
                                have = vs.setdefault(visual, {}).setdefault(s, {})
                                for obj, entries in objs.items():
                                    have[obj] = _merged(have.get(obj), entries)
            else:
                self.data[k] = v

    def theme_color(self, color_id: int, percent: float = 0) -> str | None:
        if color_id == 0:
            base = norm(self.data.get("background")) or WHITE
        elif color_id == 1:
            base = norm(self.data.get("foreground")) or "#252423"
        else:
            colors = self.data.get("dataColors") or []
            base = norm(colors[color_id - 2]) if 0 <= color_id - 2 < len(colors) else None
        return shade(base, percent) if base else None

    def color(self, node) -> str | None:
        """Hex of a colour node: {"solid": {"color": …}}, a literal, a ThemeDataColor or a plain hex; None for a
        measure or anything else that is decided only when the report runs."""
        if isinstance(node, dict) and "solid" in node:
            node = (node.get("solid") or {}).get("color")
        if isinstance(node, str):
            return norm(node)
        if not isinstance(node, dict):
            return None
        expr = node.get("expr") or {}
        if "Literal" in expr:
            return norm(literal(node))
        if "ThemeDataColor" in expr:
            t = expr["ThemeDataColor"] or {}
            try:
                return self.theme_color(int(t.get("ColorId", -1)), float(t.get("Percent") or 0))
            except (TypeError, ValueError):
                return None
        return None

    def style(self, visual_type: str, obj: str) -> dict:
        """Properties of an object as the theme sets them for this visual type, or for every visual ("*")."""
        vs = self.data.get("visualStyles") or {}
        out = {}
        for v in ("*", visual_type):
            entry = ((vs.get(v) or {}).get("*") or {}).get(obj)
            if isinstance(entry, list) and entry and isinstance(entry[0], dict):
                out.update(entry[0])
        return out


def _merged(old, new):
    """Entries of one object of a theme over those of another: the first entry property by property."""
    if isinstance(old, list) and old and isinstance(old[0], dict) and isinstance(new, list) and new \
            and isinstance(new[0], dict):
        return [{**old[0], **new[0]}] + new[1:]
    return new


def _props(objects: dict, obj: str) -> dict:
    entries = (objects or {}).get(obj)
    if isinstance(entries, list):
        for e in entries:
            if isinstance(e, dict) and not e.get("selector"):
                return e.get("properties") or {}
    return {}


def _value(props: dict, key: str, default):
    v = literal(props.get(key)) if key in props else None
    return default if v is None else v


# ------------------------------------------------------------------ page and box
def page_background(page: dict, theme: Theme) -> str:
    """The colour a page shows behind its visuals: the canvas over the wallpaper, each with its transparency."""
    page_style = theme.style("page", "background")
    canvas = _props(page.get("objects"), "background")
    c_color = theme.color(canvas.get("color")) if "color" in canvas else theme.color(page_style.get("color"))
    c_trans = _value(canvas, "transparency", page_style.get("transparency", 100))
    wall_style = theme.style("page", "outspace")
    wall = _props(page.get("objects"), "outspace")
    w_color = theme.color(wall.get("color")) if "color" in wall else theme.color(wall_style.get("color"))
    w_trans = _value(wall, "transparency", wall_style.get("transparency", 0))
    behind = mix(w_color or WHITE, WHITE, w_trans)
    return mix(c_color or WHITE, behind, c_trans)


def box(visual: dict, page_color: str, theme: Theme, default_shown: bool = False) -> tuple[str, bool]:
    """(colour of the visual's box, whether the visual sets it): its background over the page. Without its own
    background the theme decides; default_shown says whether the box is drawn then (a custom visual such as Deneb:
    yes, observed in Seqonis 17.11.)."""
    v = visual.get("visual") or {}
    own = _props(v.get("visualContainerObjects"), "background")
    style = theme.style(v.get("visualType", ""), "background")
    explicit = bool(own)
    shown = _value(own, "show", style.get("show", True if explicit or default_shown else False))
    if not shown:
        return page_color, explicit
    color = theme.color(own.get("color")) if "color" in own else theme.color(style.get("color"))
    trans = _value(own, "transparency", style.get("transparency", 0))
    return mix(color or WHITE, page_color, trans), explicit


# text that a visual writes: (object, colour property, object and property of its own fill or None for the box)
TEXTS = [("categoryAxis", "labelColor", None), ("categoryAxis", "titleColor", None), ("valueAxis", "labelColor", None),
         ("valueAxis", "titleColor", None), ("legend", "labelColor", None),
         ("items", "fontColor", ("items", "background")), ("header", "fontColor", None),
         ("categoryLabels", "color", ("card", "cardBackground")), ("dataLabels", "color", ("card", "cardBackground")),
         ("cardTitle", "color", ("card", "cardBackground")),
         ("label", "fontColor", ("cardCalloutArea", "backgroundFillColor")),
         ("value", "fontColor", ("cardCalloutArea", "backgroundFillColor")),
         ("values", "fontColor", ("values", "backColor")), ("columnHeaders", "fontColor", ("columnHeaders", "backColor"))]


def text_colors(visual: dict, theme: Theme) -> list:
    """(where, colour, own fill or None) of text a visual writes in its default state: title and subtitle, axes,
    legend, slicer items and header, card labels, table values and headers, text box runs. None: the text stands on
    the box of the visual. States behind a selector (selected, hover) are left out."""
    v = visual.get("visual") or {}
    out = []
    vco, objs = v.get("visualContainerObjects") or {}, v.get("objects") or {}
    for obj, key in (("title", "fontColor"), ("subTitle", "fontColor")):
        p = _props(vco, obj)
        if key in p and _value(p, "show", True):
            c = theme.color(p[key])
            if c:
                out.append((f"{obj}.{key}", c, None))
    for obj, key, fill in TEXTS:
        p = _props(objs, obj)
        c = theme.color(p.get(key)) if key in p and _value(p, "show", True) else None
        if not c:
            continue
        own = None
        if fill:
            fp = _props(objs, fill[0])
            own = theme.color(fp.get(fill[1])) if fill[1] in fp else None
        out.append((f"{obj}.{key}", c, own))
    if v.get("visualType") == "textbox":
        for entry in objs.get("general") or []:
            for para in ((entry or {}).get("properties") or {}).get("paragraphs") or []:
                for run in (para or {}).get("textRuns") or []:
                    c = norm(((run or {}).get("textStyle") or {}).get("color"))
                    if c and str(run.get("value", "")).strip():
                        out.append((f"text '{str(run.get('value'))[:20]}'", c, None))
    return out
