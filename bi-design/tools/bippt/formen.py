"""Formen einer Folie sicher durchgehen und finden – auch in fremden Präsentationen.

python-pptx kennt nicht jede Form: ein früherer Platzhalter ohne Geometrie (`shape_type` bricht ab), Freihand
(`p:contentPart`, bricht schon `slide.shapes` ab), SmartArt (`shape_type` None), Inhalte in `mc:AlternateContent`
(werden still übergangen). `alle()` meldet solche Formen in `unbekannt`, liefert sie weiter, wenn sie Text haben (Text,
Farben und Schriften lassen sich lesen), und überspringt sie sonst.
"""
from collections import namedtuple

from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml import register_element_cls
from pptx.oxml.xmlchemy import BaseOxmlElement

P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
RAHMEN = {P + "nvGrpSpPr", P + "grpSpPr", P + "extLst"}
FORM_TAGS = {P + t for t in ("sp", "grpSp", "graphicFrame", "cxnSp", "pic", "contentPart")}

Unbekannt = namedtuple("Unbekannt", "name id grund gelesen")


class _Freihand(BaseOxmlElement):
    """p:contentPart (Freihand): ohne eigene Klasse brechen slide.shapes, placeholders und shapes.title ab."""
    has_ph_elm = False
    ph = None


register_element_cls("p:contentPart", _Freihand)


def art(sh):
    """MSO_SHAPE_TYPE der Form oder None, wenn python-pptx sie nicht einordnen kann."""
    try:
        return sh.shape_type
    except (NotImplementedError, AttributeError, KeyError, ValueError):
        return None


def _name_id(el):
    for c in el.iter(P + "cNvPr", "{http://schemas.microsoft.com/office/powerpoint/2010/main}cNvPr"):
        return c.get("name", ""), c.get("id", "")
    return "", ""


def _grund(el):
    tag = el.tag.split("}")[-1] if isinstance(el.tag, str) else "?"
    if el.tag == P + "sp":
        return "Form ohne Geometrie (früherer Platzhalter?)"
    if el.tag == P + "graphicFrame":
        return "Grafikrahmen ohne Tabelle, Diagramm oder OLE (z. B. SmartArt) – Inhalt nicht gelesen"
    if el.tag == P + "contentPart":
        return "Freihand (Ink)"
    if tag == "AlternateContent":
        return "mc:AlternateContent (z. B. Freihand, 3D-Modell) – nicht gelesen"
    return f"Element {tag}"


def alle(shapes, unbekannt=None, gruppen=False):
    """Alle Formen in Dokumentreihenfolge, Gruppen aufgelöst (gruppen=True: die Gruppe selbst vor ihren Formen).
    Unbekannte Formen landen in `unbekannt` (Liste)."""
    baum = getattr(shapes, "_spTree", None)
    if baum is None:  # andere Sammlung: ohne Absicherung
        yield from shapes
        return
    for el in baum.iterchildren():
        if not isinstance(el.tag, str) or el.tag in RAHMEN:
            continue
        sh = None
        if el.tag in FORM_TAGS:
            try:
                sh = shapes._shape_factory(el)
            except (AttributeError, KeyError, ValueError, TypeError, NotImplementedError):
                sh = None
        t = art(sh) if sh is not None else None
        if t == MSO_SHAPE_TYPE.GROUP:
            if gruppen:
                yield sh
            yield from alle(sh.shapes, unbekannt, gruppen)
            continue
        if t is not None:
            yield sh
            continue
        try:
            text = sh is not None and sh.has_text_frame
        except (AttributeError, KeyError, ValueError):
            text = False
        if unbekannt is not None:
            name, sid = _name_id(el)
            unbekannt.append(Unbekannt(name, sid, _grund(el), bool(text)))
        if text:
            yield sh


def meldung(u):
    """Eine Zeile je unbekannter Form."""
    return (f"Form „{u.name}“{f' (#{u.id})' if u.id else ''}: {u.grund} – "
            + ("Text gelesen, sonst übersprungen" if u.gelesen else "übersprungen"))


def finden(folie, name=None, sid=None, nr=None):
    """Formen der Folie (auch Gruppen) nach Name (optional die nr-te mit diesem Namen, ab 1) oder id. Rückgabe: Liste."""
    treffer = []
    for sh in alle(folie.shapes, gruppen=True):
        if sid is not None and str(sh.shape_id) == str(sid):
            treffer.append(sh)
        elif sid is None and sh.name == name:
            treffer.append(sh)
    if nr is not None:
        return treffer[nr - 1:nr] if 0 < nr <= len(treffer) else []
    return treffer
