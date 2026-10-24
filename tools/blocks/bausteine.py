"""Building blocks for canvas controls and YAML output (source code schema, formulas in en-US).

Central building block of ppp (origin: project ReiRue). Project generators import it through `ppp run`; they do not
copy it. Control versions come from `versionen.py`: the central one, or a project's own next to its generator.

Each block returns a dict {name, Control, Variant?, Properties, Children}. Colours only through the theme records
BIRole/BIColor (App.Formulas, brand skill bi-designer). Formulas are passed without the leading "="; the output adds it.
The API stays German so that project generators switch over by changing paths only (Ü-8).
"""
import re

from versionen import VERSIONEN


CONTAINER_ECKEN = ("RadiusTopLeft", "RadiusTopRight", "RadiusBottomLeft", "RadiusBottomRight")


def ctl(name, typ, props=None, children=None, variant=None):
    d = {"name": name, "Control": VERSIONEN[typ], "Properties": dict(props or {})}
    if typ == "Container":
        # otherwise Studio gives containers rounding and a border; flush buttons at the edge get clipped (PAPPS-20260930-MAC-04)
        for ecke in CONTAINER_ECKEN:
            d["Properties"].setdefault(ecke, "0")
        d["Properties"].setdefault("BorderThickness", "0")
    if variant:
        d["Variant"] = variant
    if children:
        d["Children"] = children
    return d


# ---------- basic blocks ----------
def label(name, text, **p):
    base = {"Text": text, "Color": "BIRole.Text", "Font": "BIFont.Text", "Size": "BISize.Body",
            "VerticalAlign": "VerticalAlign.Middle", "PaddingLeft": "0", "PaddingRight": "0",
            "PaddingTop": "0", "PaddingBottom": "0"}
    base.update(p)
    return ctl(name, "Label", base)


def rect(name, fill, **p):
    base = {"Fill": fill}
    base.update(p)
    return ctl(name, "Rectangle", base)


def bild(name, image, **p):
    base = {"Image": image, "ImagePosition": "ImagePosition.Fit"}
    base.update(p)
    return ctl(name, "Image", base)


def knopf(name, text, onselect, primaer=False, **p):
    """Primary: dark green on white text; secondary: white with dark green text and border (brand rules)."""
    fill, color = ("BIRole.PrimaryFill", "BIRole.PrimaryText") if primaer else ("BIRole.Surface", "BIRole.Text")
    base = {
        "Text": text, "OnSelect": onselect, "Fill": fill, "Color": color,
        "BorderColor": "BIRole.Text", "BorderThickness": "1",
        "HoverFill": fill, "HoverColor": color, "HoverBorderColor": "BIColor.AccentGreen",
        "PressedFill": "BIRole.PrimaryPressedFill", "PressedColor": "BIRole.PrimaryPressedText",
        "DisabledFill": "BIRole.Page", "DisabledColor": "BIRole.Text", "DisabledBorderColor": "BIRole.Border",
        "FocusedBorderColor": "BIRole.FocusLight", "FocusedBorderThickness": "2",
        "RadiusTopLeft": "2", "RadiusTopRight": "2", "RadiusBottomLeft": "2", "RadiusBottomRight": "2",
        "Font": "BIFont.Text", "FontWeight": "FontWeight.Semibold", "Size": "BISize.Body",
    }
    base.update(p)
    return ctl(name, "Button", base)


def box(name, richtung, children, **p):
    """Auto-layout container (GroupContainer, variant AutoLayout, without LayoutMode).

    Children get explicit minimum sizes 0: without them Studio adds its own minimum sizes on paste
    (PAPPS-20260929-MAC-01), and controls stick out of their row or push neighbours out of view (PAPPS-20260930-MAC-06).
    Children without FillPortions get 0, so that their Height or Width applies; without it they fill proportionally
    (PAPPS-20261009-MAC-01). Filling children pass FillPortions="1".
    """
    base = {"LayoutDirection": f"LayoutDirection.{richtung}", "LayoutGap": "0", "Fill": "RGBA(0, 0, 0, 0)",
            "DropShadow": "DropShadow.None", "PaddingTop": "0", "PaddingBottom": "0", "PaddingLeft": "0",
            "PaddingRight": "0", "LayoutAlignItems": "LayoutAlignItems.Stretch"}
    base.update(p)
    for kind in children:
        props = kind["Properties"]
        if "X" not in props and "Y" not in props:
            props.setdefault("LayoutMinWidth", "0")
            props.setdefault("LayoutMinHeight", "0")
            props.setdefault("FillPortions", "0")
    return ctl(name, "Container", base, children, variant="AutoLayout")


def frei(name, children, **p):
    """Container with manual layout, for cards and rows."""
    base = {"Fill": "RGBA(0, 0, 0, 0)", "DropShadow": "DropShadow.None"}
    base.update(p)
    return ctl(name, "Container", base, children, variant="ManualLayout")


def galerie(name, items, template_size, children, horizontal=False, **p):
    base = {"Items": items, "TemplateSize": str(template_size), "TemplatePadding": "0",
            "ShowScrollbar": "true", "Fill": "RGBA(0, 0, 0, 0)", "BorderThickness": "0"}
    base.update(p)
    return ctl(name, "Gallery", base, children, variant="Horizontal" if horizontal else "Vertical")


FARBEN_AUSWAHL = {  # classic selection controls bring their own blue tones (skill ppp-power-apps)
    "Color": "BIRole.Text", "Fill": "BIRole.Surface", "BorderColor": "BIRole.Border",
    "ChevronBackground": "BIRole.Surface", "ChevronFill": "BIRole.Text",
    "ChevronHoverBackground": "BIRole.Page", "ChevronHoverFill": "BIRole.Text",
    "SelectionFill": "BIRole.PrimaryFill", "SelectionColor": "BIRole.PrimaryText",
    "HoverFill": "BIRole.Page", "HoverColor": "BIRole.Text", "PressedFill": "BIRole.PrimaryFill",
    "PressedColor": "BIRole.PrimaryText", "FocusedBorderColor": "BIRole.FocusLight", "Font": "BIFont.Text",
    "Size": "BISize.Body",
}


def auswahl(name, items, default, onchange=None, **p):
    base = {"Items": items, "Default": default, "OnChange": onchange, **FARBEN_AUSWAHL}
    if onchange is None:  # pure filter dropdowns act through .Selected and need no OnChange
        del base["OnChange"]
    base.update(p)
    return ctl(name, "DropDown", base)


def eingabe(name, default, hinweis, **p):
    """Classic text input; only properties seen in a Studio serialization."""
    base = {"Default": default, "HintText": hinweis, "Color": "BIRole.Text", "Fill": "BIRole.Surface",
            "BorderColor": "BIRole.Border", "Font": "BIFont.Text", "Size": "BISize.Body", "PaddingLeft": "8"}
    base.update(p)
    return ctl(name, "TextInput", base)


def kombi(name, items, anzeige, default_items, onchange, **p):
    base = {"Items": items, "DisplayFields": f'["{anzeige}"]', "SearchFields": f'["{anzeige}"]',
            "SelectMultiple": "false", "IsSearchable": "false", "DefaultSelectedItems": default_items,
            "OnChange": onchange, **{k: v for k, v in FARBEN_AUSWAHL.items() if k not in ("HoverColor", "PressedColor")}}
    base.update(p)
    return ctl(name, "ComboBox", base)


def datum(name, default, onchange, **p):
    """Input neutral like the dropdowns (icon without green fill), week starts on Monday.

    The opened calendar cannot be coloured: Classic/DatePicker@2.6.0 has no properties
    CalendarHeaderFill/SelectedDateFill/HoverDateFill (PAPPS-20260930-MAC-05).
    """
    base = {"DefaultDate": default, "OnChange": onchange, "Format": "DateTimeFormat.ShortDate", "Language": '"de-DE"',
            "StartOfWeek": "StartOfWeek.Monday",
            "Color": "BIRole.Text", "Fill": "BIRole.Surface", "BorderColor": "BIRole.Border",
            "IconBackground": "BIRole.Surface", "IconFill": "BIRole.Text",
            "FocusedBorderColor": "BIRole.FocusLight", "Font": "BIFont.Text", "Size": "BISize.Body"}
    base.update(p)
    return ctl(name, "DatePicker", base)


def uhr(name, onende, sekunden=30):
    """Invisible timer that repeats itself (Timer@2.1.0, properties as seen in an existing app)."""
    return ctl(name, "Timer", {"Duration": str(sekunden * 1000), "Repeat": "true", "AutoStart": "true",
                               "OnTimerEnd": onende, "Visible": "false", "X": "0", "Y": "0", "Width": "1", "Height": "1"})


def chip(name, text, fill, color, **p):
    """Status chip (label with fill, small, semibold)."""
    werte = {"Size": "BISize.Small", "FontWeight": "FontWeight.Semibold", "Align": "Align.Center"}
    # chips without X/Y sit in an auto layout: Studio must not raise their minimum height to 100 px
    if "X" not in p and "Y" not in p:
        werte.update(LayoutMinHeight="0", LayoutMinWidth="0", AlignInContainer="AlignInContainer.Center")
    werte.update(p)
    return label(name, text, Fill=fill, Color=color, **werte)


# ---------- YAML output ----------
_EINFACH = re.compile(r"^[A-Za-z0-9_.() +\-*/<>]+$")


def _wert(formel: str, einzug: int) -> str:
    f = "=" + formel
    if "\n" not in f and _EINFACH.match(formel):
        return f
    zeilen = f.split("\n")
    return "|-\n" + "\n".join((" " * (einzug + 2) + z) if z else "" for z in zeilen)


def _control(d: dict, einzug: int) -> list[str]:
    e = " " * einzug
    out = [f"{e}- {d['name']}:", f"{e}    Control: {d['Control']}"]
    if d.get("Variant"):
        out.append(f"{e}    Variant: {d['Variant']}")
    if d.get("Properties"):
        out.append(f"{e}    Properties:")
        for k, v in d["Properties"].items():
            out.append(f"{e}      {k}: {_wert(v, einzug + 6)}")
    if d.get("Children"):
        out.append(f"{e}    Children:")
        for c in d["Children"]:
            out.extend(_control(c, einzug + 6))
    return out


def screen_yaml(name: str, props: dict, children: list) -> str:
    out = ["Screens:", f"  {name}:", "    Properties:"]
    for k, v in props.items():
        out.append(f"      {k}: {_wert(v, 6)}")
    out.append("    Children:")
    for c in children:
        out.extend(_control(c, 6))
    return "\n".join(out) + "\n"


def alle_formeln(d: dict):
    """(control, property, formula) for checks."""
    for k, v in d.get("Properties", {}).items():
        yield d["name"], k, v
    for c in d.get("Children", []):
        yield from alle_formeln(c)


def alle_namen(d: dict):
    yield d["name"]
    for c in d.get("Children", []):
        yield from alle_namen(c)
