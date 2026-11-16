"""Render a Deneb specification outside Power BI with vl-convert (Vega in an embedded runtime, no Node, no browser)."""
import copy
import re
import sys
from dataclasses import dataclass, field

from . import deneb

VL_VERSION = "6.4"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?$")
LOCALES = {"de": "de-DE", "en": "en-US", "fr": "fr-FR"}


class RenderError(Exception):
    pass


@dataclass
class Result:
    width: int
    height: int
    vega: dict = None
    scenegraph: dict = None
    svg: str = ""
    notes: list = field(default_factory=list)
    origin: tuple = (0, 0)       # offset of the view inside the canvas
    canvas: tuple = (0, 0)       # size of the whole render
    runtime: list = field(default_factory=list)   # errors Vega wrote while running


class Stderr:
    """Capture what the embedded runtime writes to file descriptor 2; Vega reports runtime errors only there."""

    def __enter__(self):
        import os
        import tempfile
        self.text = ""
        try:
            sys.stderr.flush()
            self._tmp = tempfile.TemporaryFile(mode="w+b")
            self._old = os.dup(2)
            os.dup2(self._tmp.fileno(), 2)
        except (OSError, ValueError, AttributeError):
            self._tmp = None
        return self

    def __exit__(self, *exc):
        import os
        if self._tmp is not None:
            os.dup2(self._old, 2)
            os.close(self._old)
            self._tmp.seek(0)
            self.text = self._tmp.read().decode("utf-8", "replace")
            self._tmp.close()
        return False


def available() -> str | None:
    """The version of vl-convert, or None when it is not installed."""
    try:
        import vl_convert
        return vl_convert.__version__
    except Exception:
        return None


def versions() -> dict:
    import vl_convert as vlc
    return {"vl-convert": vlc.__version__, "vega": vlc.get_vega_version(), "vega-lite": VL_VERSION,
            "deneb vega": deneb.VEGA_VERSION, "deneb vega-lite": deneb.VEGALITE_VERSION}


def clean(message: str) -> str:
    """The first lines of a vl-convert error without the JavaScript stack."""
    lines = [ln.strip() for ln in str(message).splitlines() if ln.strip()]
    keep = [ln for ln in lines if not ln.startswith("at ") and "cdn.jsdelivr" not in ln]
    return " ".join(keep[:3])[:600]


def merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def date_fields(rows: list[dict]) -> list[str]:
    names = []
    for r in rows[:50]:
        for k, v in r.items():
            if isinstance(v, str) and ISO.match(v) and k not in names:
                names.append(k)
    return names


def locale_name(locale: str | None) -> str:
    if not locale:
        return "de-DE"
    return LOCALES.get(locale.split("-")[0].casefold(), "en-US") if locale not in LOCALES.values() else locale


def to_vega(spec: dict, config: dict | None, rows: list[dict], width: int, height: int, brand) -> tuple[dict, list]:
    """The Vega specification Deneb would run for this container size, with Deneb-only parts approximated."""
    import vl_convert as vlc
    provider = deneb.provider_of(spec)
    dates = date_fields(rows)
    if provider == "vegaLite":
        vl = deneb.prepare_vegalite(spec, rows, width, height)
        if config:
            vl["config"] = merge(config, vl.get("config", {}))
            vl["config"]["background"] = "transparent"
        if dates and isinstance(vl.get("data"), dict) and vl["data"].get("name") == "dataset":
            vl["data"] = {**vl["data"], "format": {"parse": {d: "date" for d in dates}}}
        try:
            vega = vlc.vegalite_to_vega(vl, vl_version=VL_VERSION)
        except Exception as ex:
            raise RenderError("Vega-Lite does not compile: " + clean(ex)) from None
        if dates:
            for d in vega.get("data", []):
                if d.get("name") == "dataset":
                    d["format"] = {"type": "json", "parse": {k: "date" for k in dates}}
    else:
        vega = deneb.prepare_vega(spec, rows, width, height)
        if config:
            vega["config"] = merge(config, vega.get("config", {}))
        if dates:
            for d in vega["data"]:
                if d.get("name") == "dataset":
                    d["format"] = {"type": "json", "parse": {k: "date" for k in dates}}
    return deneb.emulate(vega, brand)


def render(spec: dict, config: dict | None, rows: list[dict], width: int, height: int, brand,
           locale: str | None = None, svg: bool = True) -> Result:
    import vl_convert as vlc
    res = Result(width, height)
    res.vega, res.notes = to_vega(spec, config, rows, width, height, brand)
    loc = locale_name(locale)
    kw = {"format_locale": loc, "time_format_locale": loc, "allowed_base_urls": ["data:"]}
    try:
        with Stderr() as err:
            sg = vlc.vega_to_scenegraph(res.vega, **kw)
            if svg:
                res.svg = deneb.pattern_defs(vlc.vega_to_svg(res.vega, **kw), brand.c("textSecondary"))
    except Exception as ex:
        raise RenderError("Vega does not run: " + clean(ex)) from None
    res.scenegraph = sg.get("scenegraph", sg)
    origin = sg.get("origin") or [0, 0]
    res.origin = (origin[0], origin[1])
    res.canvas = (sg.get("width", width), sg.get("height", height))
    seen = []
    for line in err.text.splitlines():
        line = line.strip()
        if line.startswith(("ERROR", "WARN")) and line not in seen:
            seen.append(line[:300])
    res.runtime = seen
    return res


def framed(svg: str, width: int, height: int, background: str = "#FFFFFF") -> str:
    """The render inside its container: container size, page background, overflow cut off as in Power BI."""
    inner = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}"><rect width="{width}" height="{height}" '
            f'fill="{background}"/>{inner}</svg>')


def png(svg: str, scale: float = 2.0) -> bytes:
    import vl_convert as vlc
    return vlc.svg_to_png(svg, scale=scale)
