"""Read the scenegraph of a render: where every mark and text ends up, and what is wrong with the picture."""
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import brand as br

SHAPES = {"rect", "arc", "symbol", "area", "path", "shape", "image"}
FONT_FILES = {  # family (casefold) -> (regular, semibold, bold)
    "segoe ui": ("segoeui.ttf", "seguisb.ttf", "segoeuib.ttf"),
    "arial": ("arial.ttf", "arialbd.ttf", "arialbd.ttf"),
}
FONT_DIRS = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path("/Library/Fonts"),
             Path("/System/Library/Fonts/Supplemental"), Path("/usr/share/fonts/truetype/dejavu")]
_fonts = {}


@dataclass
class Item:
    kind: str                  # text, rect, rule, symbol, line, area, arc, path, group ...
    role: str                  # mark, axis-label, axis-title, legend-label, title-text ...
    name: str
    box: tuple                 # x0, y0, x1, y1 in view coordinates
    order: int
    fill: str | None = None
    stroke: str | None = None
    stroke_width: float = 0
    opacity: float = 1
    text: str = ""
    font: str = ""
    font_size: float = 0
    bold: bool = False
    truncated: bool = False
    clipped: bool = False
    radius: float = 0
    gradient: bool = False
    aria: str = ""            # ariaRoleDescription of Vega-Lite: bar, point ...
    data: bool = False         # drawn from data (role mark), not an axis, legend or title
    arc: tuple | None = None   # cx, cy, inner, outer, start, end


@dataclass
class Scene:
    items: list = field(default_factory=list)
    width: float = 0           # of the view (root group)
    height: float = 0

    def texts(self):
        return [i for i in self.items if i.kind == "text" and i.text.strip()]

    def bounds(self):
        boxes = [i.box for i in self.items if i.kind != "group"]
        if not boxes:
            return (0, 0, 0, 0)
        return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


# ---------------------------------------------------------------- text width
def _font(family: str, size: float, weight):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    first = (family or "").split(",")[0].strip().strip("'\"").casefold()
    files = FONT_FILES.get(first) or FONT_FILES["segoe ui"]
    idx = 2 if _weight(weight) >= 700 else 1 if _weight(weight) >= 600 else 0
    key = (files[idx], round(size * 4))
    if key not in _fonts:
        font = None
        for d in FONT_DIRS:
            for name in (files[idx], files[0], "DejaVuSans.ttf", "Arial.ttf"):
                if (d / name).is_file():
                    try:
                        font = ImageFont.truetype(str(d / name), max(1, round(size * 4)))
                        break
                    except OSError:
                        pass
            if font:
                break
        _fonts[key] = font
    return _fonts[key]


def _weight(w) -> int:
    if isinstance(w, (int, float)):
        return int(w)
    return {"bold": 700, "bolder": 700, "normal": 400, "lighter": 300}.get(str(w or "normal").casefold(), 400)


def text_width(text: str, family: str, size: float, weight=None) -> float:
    font = _font(family, size, weight)
    if font is not None:
        return font.getlength(text) / 4
    wide = sum(1 for c in text if c in "MWmw@%") * 0.3
    narrow = sum(1 for c in text if c in "il.,;:'|!jt f") * 0.25
    return (len(text) * 0.53 + wide - narrow) * size * (1.06 if _weight(weight) >= 600 else 1)


def measured() -> bool:
    return _font("Segoe UI", 12, None) is not None


# ---------------------------------------------------------------- reading the scenegraph
def _color(v):
    if isinstance(v, dict):
        return "gradient"
    if not isinstance(v, str) or v in ("transparent", "none", ""):
        return None
    return br.norm(v) or None


def _num(v, default=0.0):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else default


def _text_box(it: dict, ox: float, oy: float) -> tuple[tuple, bool, list]:
    raw = it.get("text")
    lines = [str(x) for x in raw] if isinstance(raw, list) else str(raw if raw is not None else "").split("\n")
    size = _num(it.get("fontSize"), 11)
    limit = _num(it.get("limit"), 0)
    widths = [text_width(ln, it.get("font", ""), size, it.get("fontWeight")) for ln in lines]
    w = max(widths) if widths else 0
    truncated = bool(limit and w > limit + 0.5)
    if truncated:      # Vega keeps the longest beginning that fits together with the ellipsis
        longest = max(lines, key=len)
        lo, hi = 0, len(longest)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if text_width(longest[:mid] + "…", it.get("font", ""), size, it.get("fontWeight")) <= limit:
                lo = mid
            else:
                hi = mid - 1
        w = text_width(longest[:lo] + "…", it.get("font", ""), size, it.get("fontWeight"))
    line_h = _num(it.get("lineHeight"), size * 1.15)
    h = size * 1.15 + line_h * (len(lines) - 1)
    x, y = _num(it.get("x")), _num(it.get("y"))
    if it.get("radius"):
        t = _num(it.get("theta")) - math.pi / 2
        x += _num(it.get("radius")) * math.cos(t)
        y += _num(it.get("radius")) * math.sin(t)
    dx, dy = _num(it.get("dx")), _num(it.get("dy"))
    align = it.get("align", "left")
    left = dx - (w if align == "right" else w / 2 if align == "center" else 0)
    base = it.get("baseline", "alphabetic")
    top = dy - {"top": 0, "line-top": 0, "middle": size * 0.575, "bottom": size * 1.15, "line-bottom": size * 1.15}.get(
        base, size * 0.9)
    corners = [(left, top), (left + w, top), (left + w, top + h), (left, top + h)]
    a = math.radians(_num(it.get("angle")))
    if a:
        corners = [(cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)) for cx, cy in corners]
    xs = [ox + x + c[0] for c in corners]
    ys = [oy + y + c[1] for c in corners]
    return (min(xs), min(ys), max(xs), max(ys)), truncated, lines


def _clip(box, clip):
    if clip is None:
        return box, False
    c = (max(box[0], clip[0]), max(box[1], clip[1]), min(box[2], clip[2]), min(box[3], clip[3]))
    cut = c != box
    if c[2] <= c[0] or c[3] <= c[1]:
        return None, True
    return c, cut


def read(scenegraph: dict) -> Scene:
    scene = Scene()
    counter = [0]

    def mark(node, ox, oy, clip, in_data):
        kind = node.get("marktype")
        role = node.get("role", "") or ""
        name = node.get("name", "") or ""
        data = in_data or role == "mark"
        if kind in ("line", "area", "trail") and node.get("items"):
            pts = [p for p in node["items"] if isinstance(p, dict)]
            xs = [ox + _num(p.get("x")) for p in pts] + [ox + _num(p.get("x2"), _num(p.get("x"))) for p in pts]
            ys = [oy + _num(p.get("y")) for p in pts] + [oy + _num(p.get("y2"), _num(p.get("y"))) for p in pts]
            first = pts[0]
            counter[0] += 1
            box, cut = _clip((min(xs), min(ys), max(xs), max(ys)), clip)
            if box:
                scene.items.append(Item(kind, role, name, box, counter[0], _color(first.get("fill")),
                                        _color(first.get("stroke")), _num(first.get("strokeWidth"), 1 if kind == "line" else 0),
                                        _num(first.get("opacity"), 1), data=data, clipped=cut))
            return
        for it in node.get("items", []) or []:
            if not isinstance(it, dict):
                continue
            counter[0] += 1
            opacity = _num(it.get("opacity"), 1)
            fill, stroke = _color(it.get("fill")), _color(it.get("stroke"))
            if kind == "text" and fill is None and "fill" not in it:
                fill = "#000000"
            if _num(it.get("fillOpacity"), 1) == 0:
                fill = None
            if _num(it.get("strokeOpacity"), 1) == 0:
                stroke = None
            x, y = ox + _num(it.get("x")), oy + _num(it.get("y"))
            if kind == "group":
                w, h = _num(it.get("width")), _num(it.get("height"))
                inner = clip
                if node.get("clip") or it.get("clip"):
                    inner, _ = _clip((x, y, x + w, y + h), clip)
                    inner = inner or (0, 0, 0, 0)
                if (fill or stroke) and w and h and opacity > 0:
                    box, cut = _clip((x, y, x + w, y + h), clip)
                    if box:
                        scene.items.append(Item("rect", role or "group", name, box, counter[0], fill, stroke,
                                                _num(it.get("strokeWidth"), 1 if stroke else 0), opacity, data=data,
                                                radius=_num(it.get("cornerRadius")), gradient=fill == "gradient"))
                if role == "frame" or (not scene.width and name == "root"):
                    scene.width, scene.height = w, h
                for child in it.get("items", []) or []:
                    mark(child, x, y, inner, data)
                continue
            if opacity <= 0:
                continue
            item = None
            if kind == "text":
                if fill is None and stroke is None:
                    continue
                box, truncated, lines = _text_box(it, ox, oy)
                item = Item("text", role, name, box, counter[0], fill, stroke, 0, opacity, text=" ".join(lines),
                            font=str(it.get("font", "")), font_size=_num(it.get("fontSize"), 11),
                            bold=_weight(it.get("fontWeight")) >= 600, truncated=truncated, data=data)
            elif kind == "rect":
                w = _num(it.get("width"), _num(it.get("x2"), _num(it.get("x"))) - _num(it.get("x")))
                h = _num(it.get("height"), _num(it.get("y2"), _num(it.get("y"))) - _num(it.get("y")))
                item = Item("rect", role, name, (x, y, x + w, y + h), counter[0], fill, stroke,
                            _num(it.get("strokeWidth"), 1 if stroke else 0), opacity, data=data,
                            radius=max(_num(it.get(k)) for k in ("cornerRadius", "cornerRadiusTopLeft",
                                                                 "cornerRadiusTopRight", "cornerRadiusBottomLeft",
                                                                 "cornerRadiusBottomRight")))
            elif kind == "rule":
                x2 = ox + _num(it.get("x2"), _num(it.get("x")))
                y2 = oy + _num(it.get("y2"), _num(it.get("y")))
                item = Item("rule", role, name, (min(x, x2), min(y, y2), max(x, x2), max(y, y2)), counter[0], None,
                            stroke, _num(it.get("strokeWidth"), 1), opacity, data=data)
            elif kind == "symbol":
                r = math.sqrt(max(_num(it.get("size"), 64), 0)) / 2
                item = Item("symbol", role, name, (x - r, y - r, x + r, y + r), counter[0], fill, stroke,
                            _num(it.get("strokeWidth"), 1 if stroke else 0), opacity, data=data)
            elif kind == "arc":
                r = _num(it.get("outerRadius"))
                item = Item("arc", role, name, (x - r, y - r, x + r, y + r), counter[0], fill, stroke,
                            _num(it.get("strokeWidth"), 0), opacity, data=data,
                            arc=(x, y, _num(it.get("innerRadius")), r, _num(it.get("startAngle")), _num(it.get("endAngle"))))
            elif kind in ("path", "shape", "image"):
                w, h = _num(it.get("width")), _num(it.get("height"))
                item = Item(kind, role, name, (x, y, x + w, y + h), counter[0], fill, stroke,
                            _num(it.get("strokeWidth"), 1 if stroke else 0), opacity, data=data)
            if item is None:
                continue
            item.gradient = item.fill == "gradient" or item.stroke == "gradient"
            item.aria = str(it.get("ariaRoleDescription", ""))
            box, cut = _clip(item.box, clip)
            if box is None:
                continue
            item.box, item.clipped = box, cut
            scene.items.append(item)

    mark(scenegraph, 0, 0, None, False)
    return scene


# ---------------------------------------------------------------- geometry
def overlap(a, b) -> tuple[float, float]:
    return min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])


def _inside(item: Item, px: float, py: float) -> bool:
    b = item.box
    if not (b[0] <= px <= b[2] and b[1] <= py <= b[3]):
        return False
    if item.arc:
        cx, cy, inner, outer, start, end = item.arc
        d = math.hypot(px - cx, py - cy)
        if not inner <= d <= outer:
            return False
        ang = math.atan2(px - cx, -(py - cy)) % (2 * math.pi)
        lo, hi = min(start, end), max(start, end)
        if hi - lo >= 2 * math.pi - 1e-6:
            return True
        s, e = lo % (2 * math.pi), hi % (2 * math.pi)
        if e == 0 and hi > lo:
            e = 2 * math.pi
        return s <= ang <= e if s <= e else (ang >= s or ang <= e)
    return True


def backdrop(scene: Scene, text: Item, background: str) -> str:
    """The fill directly behind the centre of a text."""
    px, py = (text.box[0] + text.box[2]) / 2, (text.box[1] + text.box[3]) / 2
    found = background
    for it in scene.items:
        if it.order >= text.order:
            break
        if it.kind in ("rect", "arc", "symbol") and it.fill and it.fill != "gradient" and it.opacity >= 0.5 \
                and _inside(it, px, py):
            found = it.fill
    return found


def svg_frame(svg: str) -> tuple[float, float, float, float]:
    """Width and height of the rendered SVG and the offset of the view inside it."""
    m = re.search(r"<svg[^>]*?\swidth=\"([\d.]+)\"[^>]*?\sheight=\"([\d.]+)\"", svg)
    w, h = (float(m.group(1)), float(m.group(2))) if m else (0, 0)
    t = re.search(r"<g[^>]*transform=\"translate\(([-\d.]+)[, ]\s*([-\d.]+)\)\"", svg)
    ox, oy = (float(t.group(1)), float(t.group(2))) if t else (0, 0)
    return w, h, ox, oy
