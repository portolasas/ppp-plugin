"""Deck aus der Erstellen-Funktion von Copilot (oder einem anderen Designer) in die Marke übertragen: `bippt umwandeln marke`.

Die Gestaltung bleibt, wie sie ist: Lage, Karten, Abläufe, Organigramm, Gantt, Fotos. Getauscht wird, was die Marke festlegt: Farben
nach ihrer Rolle (nicht die nächste Farbe, sonst wird aus Blau Petrol), Schriften, Icons, Logo und Fußzeile aus dem BI-Master.
Entscheidung des Nutzers (30.10.2026): Das Deck muss nicht in die Layouts des Masters passen, wenn die Elemente markenkonform sind.

Farben: Das Deck hat eine Hausfarbe und meist weitere Farbgruppen. Die Hausfarbe wird dunkel zu Dark Green, ihre mittleren Töne und die
anderen Gruppen teilen sich nach Häufigkeit Accent Green, Medium Blue und Dark Blue (neben Weiß und Dunkelgrün eine Variante, Regel aus
reference/bibliothek.md). Diagramme nehmen die Chart order der Marke, damit Kategorien unterscheidbar bleiben. Signalfarben gibt es nur,
wenn das Deck wirklich eine Ampel hat: Orange ist kein Alarm, und ein einzelnes Grün ist keine Statusfarbe.

Icons: Bekannte Formen des Designers tauscht bippt selbst gegen Brand-Icons (designer_icons.py); so bleibt die Bedeutung erhalten. Unbekannte werden
umgefärbt und mit Schlüssel, Text daneben und einem Bild aller offenen Formen gemeldet. Die Zuordnung {"<Schlüssel>": "<Brand-Icon>"} oder
{"<Folie>": {"<id>": "<Brand-Icon>"}} in einer JSON-Datei (--icons) geht vor. Das Modell neigt zu wenigen Allzweck-Icons (Test 30.10.: 18 verschiedene
für 82 Formen), darum die Tabelle und die Warnung bei Einförmigkeit.
"""
import colorsys
import hashlib
import io
import json
import re
from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn

from . import bibliothek, konfig, vorlage
from .bausteine import umbrechen
from .designer_icons import GLYPHEN
from .marke import Marke

ZOLL = 914400
DG, AG, WH = "08312A", "00E47C", "FFFFFF"
MITTELBLAU, DUNKELBLAU = "6AD2E2", "076D7E"
SEITE, FEIN, WARM = "F6F5F3", "EFEEEB", "E5E3DE"  # Light Gray für die Seite, Gray 3 für Flächen darauf, Warm Gray
GRAU_TEXT, GRAU_LINIE, GRAU_FLAECHE = "5C5B59", "B7B6B2", "5C5B59"  # Gray 7, Gray 5
SIGNAL = {"gruen": ("1EAD1B", DG), "gelb": ("FF8413", "E18600"), "rot": ("F62B2B", "86251B")}  # Fläche, Text auf Hell
AKZENTE = (AG, MITTELBLAU, DUNKELBLAU)  # Plätze für Farbgruppen, in dieser Reihenfolge nach Häufigkeit
CHART_ORDER = (DG, AG, DUNKELBLAU, MITTELBLAU, "E18600", "EE6541", "5D4495", "928BDE", "86251B", "FFD03D")  # MARKE.md
UNTEN = 6.62  # Unterkante des Inhalts (in): darunter liegen Logo und Fußzeile des Masters
FUSS_OBEN = 6.85  # ab hier beginnt die Fußzeile eines Designer-Decks
NOTIZ_X, NOTIZ_Y, NOTIZ_ENDE = 2.05, 6.93, 7.6  # freie Zone zwischen Logo und Fußzeile für Stand- und Quellenzeilen
ICON_MAX = 1.2  # in; größere Bilder sind keine Icons
EINFOERMIG_AB = 4  # so viele verschiedene Formen auf demselben Brand-Icon gelten als Einfallslosigkeit, nicht als Absicht
ICON_KLEIN = 0.135  # in; kleiner sind es Häkchen und Punkte vor Listen, sie werden nur umgefärbt
MIN_PT = 9  # Mindestgröße der Marke im Inhalt; nur wenn der Text dadurch nicht umbricht, denn der Designer misst seine Felder knapp
UNTERGRENZE_PT = 7  # kleiner macht bippt keine Schrift, auch wenn ein Wort sonst getrennt würde
EIGENE_LAGE = (qn("p:sp"), qn("p:pic"), qn("p:cxnSp"), qn("p:graphicFrame"))
SEITENZAHL = re.compile(r"^(folie|seite|slide)?\s*0*(\d+)\b", re.I)


# ----------------------------------------------------------------- Farben nach Rolle
def _rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hsl(h):
    r, g, b = _rgb(h)
    t, l, s = colorsys.rgb_to_hls(r, g, b)
    return t * 360, s, l


def _lum(h):
    def k(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * k(r) + 0.7152 * k(g) + 0.0722 * k(b)


def _kontrast(a, b):
    x, y = sorted((_lum(a), _lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def _bunt(h):
    _, s, l = _hsl(h)
    return s >= 0.3 and 0.08 <= l < 0.9


def _abstand(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _ampelton(h):
    t, s, l = _hsl(h)
    if s < 0.3 or not 0.2 <= l <= 0.7:
        return None
    return "rot" if t < 10 or t >= 345 else "gelb" if 30 <= t < 56 else "gruen" if 75 <= t < 170 else None


class Palette:
    """Farbregeln für ein Deck. farben: alle Vorkommen; seite: häufigster Seitenhintergrund der Quelle."""

    def __init__(self, farben, seite):
        self.seite = seite
        zahl = {}
        for f in farben:
            if _bunt(f):
                zahl[f] = zahl.get(f, 0) + 1
        self.zentren = []  # Farbgruppen: Zentrum (Farbton), größte zuerst, die erste ist die Hausfarbe
        for f in sorted(zahl, key=zahl.get, reverse=True):
            t = _hsl(f)[0]
            if not any(_abstand(t, z) <= 15 for z in self.zentren):
                self.zentren.append(t)
        anzahl = {}
        for f, n in zahl.items():
            g = self.gruppe(f)
            schluessel = "haus" if g == 0 and _lum(f) >= 0.09 else None if g == 0 else g
            if schluessel is not None:
                anzahl[schluessel] = anzahl.get(schluessel, 0) + n
        mitte = anzahl.pop("haus", 0)
        reihe = sorted(anzahl, key=lambda k: (-anzahl[k], k))
        self.haus_akzent = not reihe or anzahl[reihe[0]] < 0.6 * mitte  # keine andere Farbgruppe trägt das Deck: Accent Green für die Hausfarbe
        plaetze = AKZENTE[1:] if self.haus_akzent else AKZENTE
        self.plaetze = {k: plaetze[min(i, len(plaetze) - 1)] for i, k in enumerate(reihe)}
        toene = {_ampelton(f) for f in zahl if self.gruppe(f) != 0}
        self.ampel = {"rot", "gruen"} <= toene  # Gelb und Grün reicht nicht: ein goldener Pokal macht noch keine Ampel

    def gruppe(self, h):
        if not self.zentren:
            return 0
        t = _hsl(h)[0]
        return min(range(len(self.zentren)), key=lambda i: _abstand(t, self.zentren[i]))

    def signal(self, h):
        return _ampelton(h) if self.ampel and self.gruppe(h) != 0 else None

    def flaeche(self, h):
        s = self.signal(h)
        if s:
            return SIGNAL[s][0]
        _, sat, l = _hsl(h)
        if h == WH or l >= 0.985:
            return WH
        if self.seite and all(abs(a - b) <= 8 / 255 for a, b in zip(_rgb(h), _rgb(self.seite))):
            return SEITE  # auch Bilder in fast der Seitenfarbe: im Original unsichtbar, sie sollen es bleiben
        if l >= 0.9:
            return FEIN
        if l >= 0.7:
            return WARM
        if sat < 0.3:
            return GRAU_FLAECHE if _lum(h) > 0.02 else DG
        g = self.gruppe(h)
        if g == 0:
            if _lum(h) < 0.09:
                return DG
            return AG if self.haus_akzent else DUNKELBLAU if _lum(h) < 0.2 else MITTELBLAU
        return DG if _lum(h) < 0.02 else self.plaetze.get(g, AG)

    def linie(self, h, grund):
        _, sat, l = _hsl(h)
        if _lum(grund) < 0.25:
            return AG if sat >= 0.3 and l < 0.7 else WARM
        if l >= 0.7:
            return WARM
        return GRAU_LINIE if sat < 0.3 else DG

    def text(self, h, grund):
        s = self.signal(h)
        t_sat, t_l = _hsl(h)[1:]
        if _lum(grund) < 0.25:
            neu = WH if t_l > 0.9 or t_sat < 0.3 else WARM if t_l >= 0.7 else AG
        elif s:
            neu = SIGNAL[s][1]
        else:
            neu = GRAU_TEXT if t_sat < 0.35 and 0.3 < t_l < 0.75 else DG
        return neu if _kontrast(neu, grund) >= 3 else max((DG, WH), key=lambda c: _kontrast(c, grund))

    def reihe(self, farben):
        """Kategorien eines Diagramms: jede Farbe eine eigene aus der Chart order; die Rollenfarbe, wenn sie noch frei ist."""
        ergebnis, frei = {}, list(CHART_ORDER)
        for f in farben:
            if f not in ergebnis:
                ziel = self.flaeche(f)
                if ziel in frei:
                    ergebnis[f] = ziel
                    frei.remove(ziel)
        for f in farben:
            if f not in ergebnis:
                ergebnis[f] = frei.pop(0) if frei else CHART_ORDER[-1]
        return ergebnis


# ----------------------------------------------------------------- Lesen
def _xfrm(el):
    return el.find(qn("p:xfrm")) if el.tag == qn("p:graphicFrame") else el.find(".//" + qn("a:xfrm"))


def _box(el):
    """Lage (in) einer Form auf der Folie; None ohne eigene Lage (Platzhalter erben sie)."""
    xf = _xfrm(el)
    if xf is None or xf.find(qn("a:off")) is None:
        return None
    o, e = xf.find(qn("a:off")), xf.find(qn("a:ext"))
    return tuple(int(v) / ZOLL for v in (o.get("x"), o.get("y"), e.get("cx"), e.get("cy")))


def _setze(el, y=None, h=None, x=None, w=None):
    xf = _xfrm(el)
    o, e = xf.find(qn("a:off")), xf.find(qn("a:ext"))
    for knoten, name, wert in ((o, "x", x), (o, "y", y), (e, "cx", w), (e, "cy", h)):
        if wert is not None:
            knoten.set(name, str(int(wert * ZOLL)))


def _text(el):
    return " ".join("".join(t.text or "" for t in p.iter(qn("a:t"))) for p in el.iter(qn("a:p"))).strip()


def _groesse(el):
    gr = [int(r.get("sz")) / 100 for r in el.iter(qn("a:rPr")) if r.get("sz") and r.getparent().find(qn("a:t")) is not None]
    return max(gr) if gr else 0


def _formen(folie):
    """Formen der Folie in Zeichenreihenfolge; Gruppen aufgelöst, sofern sie nicht skaliert sind."""
    def gehen(baum):
        for el in baum:
            if el.tag == qn("p:grpSp"):
                yield from gehen(el)
            elif el.tag in EIGENE_LAGE:
                yield el
    return list(gehen(folie.shapes._spTree))


def _sid(el):
    return el.find(".//" + qn("p:cNvPr")).get("id")


def _hintergrund(folie):
    bg = folie._element.find(".//" + qn("p:bg"))
    if bg is None:
        return None, False
    f = bg.find(".//" + qn("a:srgbClr"))
    return (f.get("val").upper() if f is not None else None), bg.find(".//" + qn("a:blip")) is not None


def _deck_farben(prs):
    farben = []
    for s in prs.slides:
        farben += [el.get("val", "").upper() for el in s._element.iter(qn("a:srgbClr"))]
    return farben


def _kopfschrift(prs):
    """Schrift des größten Textes im Deck: Sie wird zur Kopfschrift der Marke, alle anderen zur Textschrift."""
    beste, gr = None, 0
    for s in prs.slides:
        for r in s._element.iter(qn("a:rPr")):
            lat = r.find(qn("a:latin"))
            if lat is not None and int(r.get("sz") or 0) > gr:
                beste, gr = lat.get("typeface"), int(r.get("sz"))
    return beste


def _gefuellt(el):
    sp = el.find(qn("p:spPr"))
    return sp is not None and (sp.find(qn("a:solidFill")) is not None or sp.find(qn("a:gradFill")) is not None)


def _ist_panel(el, b):
    """Fläche oder Foto über die ganze Höhe bis zum unteren Rand: Sie ist Teil der Gestaltung und wird nicht gestaucht, nur gekürzt."""
    if b is None or b[3] < 5 or b[1] + b[3] < 7.2 or b[2] >= 12.9:
        return False
    return el.tag == qn("p:pic") or (el.tag == qn("p:sp") and not _text(el))


# ----------------------------------------------------------------- Fußzeilen und Titel
def _gleicher_anfang(a, b):
    n = 0
    for x, y in zip(a.lower(), b.lower()):
        if x != y:
            break
        n += 1
    return n


def _fusstexte(prs, decktitel):
    """Ids der Fußtexte je Folie: Seitenzahl (auch „04“, „Folie 15“), Text am unteren Rand, der auf anderen Folien oder im Decktitel
    wiederkehrt. Inhalt am unteren Rand („Gesamtlaufzeit: …“) kehrt nicht wieder und bleibt."""
    unten = {}
    for nr, s in enumerate(prs.slides, 1):
        unten[nr] = [(el, _text(el), _box(el)) for el in _formen(s) if _box(el) and _box(el)[1] >= 5.5 and _text(el)]
    weg = {}
    for nr, liste in unten.items():
        for el, t, b in liste:
            andere = [t2 for n2, l2 in unten.items() if n2 != nr for _, t2, b2 in l2 if b2[1] >= FUSS_OBEN]
            zahl = SEITENZAHL.match(t)
            seitenzahl = zahl and int(zahl.group(2)) == nr and (t.isdigit() or zahl.group(1))
            wiederkehr = b[1] >= FUSS_OBEN and any(_gleicher_anfang(t, x) >= 20 for x in andere + [decktitel])
            if seitenzahl or wiederkehr:
                weg.setdefault(nr, []).append(_sid(el))
    return weg


def _hat_durchsicht(el):
    sp = el.find(qn("p:spPr"))
    verlauf = sp.find(qn("a:gradFill")) if sp is not None else None
    return verlauf is not None and verlauf.find(".//" + qn("a:alpha")) is not None


def _unsichtbar(folie, el):
    """Ganz durchsichtiges Bild: Der Designer legt so Karten an, die nicht gelingen. Es zeigt nichts, läge aber über dem Logo."""
    from PIL import Image
    try:
        blob = folie.part.related_part(el.find(".//" + qn("a:blip")).get(qn("r:embed"))).blob
        return Image.open(io.BytesIO(blob)).convert("RGBA").getchannel("A").getextrema()[1] == 0
    except (OSError, ValueError, KeyError):
        return False


def _aufraeumen(folie, fuss_ids):
    """Fremdes Beiwerk weg: Vollbilder, Vollflächen, Fußbänder, Fußtexte, Farbschleier über Fotos, unsichtbare Bilder. Rückgabe: Zahl der Formen."""
    weg = []
    for el in _formen(folie):
        b = _box(el)
        if _sid(el) in fuss_ids:
            weg.append(el)
        elif b is None:
            continue
        elif el.tag == qn("p:pic") and ((b[2] >= 13 and b[3] >= 7) or _unsichtbar(folie, el)):
            weg.append(el)
        elif el.tag == qn("p:sp") and not _text(el) and (
                (b[2] >= 12 and b[1] >= FUSS_OBEN) or (b[2] >= 13 and b[3] >= 7) or _hat_durchsicht(el)):
            weg.append(el)
    for el in weg:
        el.getparent().remove(el)
    return len(weg)


def _titel_setzen(folie):
    """Größter Text oben wird echter Titel: Er behält Lage und Format. Navigation und Prüfung kennen ihn dann."""
    texte = [el for el in _formen(folie) if el.tag == qn("p:sp") and _box(el) and _text(el)]
    oben = [el for el in texte if _box(el)[1] < 1.1] or [el for el in texte if _box(el)[1] < 3.5 and _groesse(el) >= 14]
    if not oben:
        return None
    el = max(oben, key=_groesse)
    nv = el.find(qn("p:nvSpPr"))
    c = nv.find(qn("p:cNvSpPr"))
    if c is not None and c.get("txBox"):
        del c.attrib["txBox"]
    pr = nv.find(qn("p:nvPr"))
    if pr.find(qn("p:ph")) is None:
        pr.insert(0, pr.makeelement(qn("p:ph"), {"type": "title"}))
    return _text(el)


def _panels_kuerzen(folie):
    """Panels enden über Logo und Fußzeile. Fotos werden unten beschnitten, nicht verzerrt."""
    for el in _formen(folie):
        b = _box(el)
        if not _ist_panel(el, b):
            continue
        neu = UNTEN - b[1]
        if el.tag == qn("p:pic"):
            bf = el.find(qn("p:blipFill"))
            src = bf.find(qn("a:srcRect"))
            if src is None:
                src = bf.makeelement(qn("a:srcRect"), {})
                bf.find(qn("a:blip")).addnext(src)
            t, u = int(src.get("t") or 0), int(src.get("b") or 0)
            src.set("b", str(int(u + (100000 - t - u) * (1 - neu / b[3]))))
        _setze(el, h=neu)


def _notizen_verlegen(folie):
    """Stand- und Quellenzeilen vom unteren Rand in die freie Zone zwischen Logo und Fußzeile, statt ihretwegen den Inhalt zu stauchen.
    Text auf einer Fläche (Chip, Band) gehört zur Gestaltung und bleibt. Rückgabe: Ids der verlegten Formen."""
    x, verlegt = NOTIZ_X, set()
    flaechen = [(el, _box(el)) for el in _formen(folie) if el.tag == qn("p:sp") and not _text(el) and _gefuellt(el) and _box(el)]
    for el in _formen(folie):
        b = _box(el)
        if b is None or b[1] < FUSS_OBEN or not _text(el) or _groesse(el) > 10 or _gefuellt(el) or _kleinster(flaechen, b):
            continue
        breite = len(_text(el)) * _groesse(el) * 0.0075 + 0.1
        if x + breite > NOTIZ_ENDE:
            continue
        _setze(el, x=x, y=NOTIZ_Y, w=breite)
        bp = el.find(".//" + qn("a:bodyPr"))
        if bp is not None:
            bp.set("wrap", "none")
        x += breite + 0.2
        verlegt.add(_sid(el))
    return verlegt


def _kleinster(behaelter, b):
    """Kleinster Behälter, in dem b ganz liegt."""
    passend = [c for c in behaelter if c[1][2] * c[1][3] > b[2] * b[3] and c[1][0] - 0.02 <= b[0] and c[1][1] - 0.02 <= b[1]
               and b[0] + b[2] <= c[1][0] + c[1][2] + 0.02 and b[1] + b[3] <= c[1][1] + c[1][3] + 0.02]
    return min(passend, key=lambda c: c[1][2] * c[1][3]) if passend else None


def _inhalt_einpassen(liste, oben, h_alt, y0, h0):
    """Neue Lage der Inhalte einer Karte, die von oben auf y0 und in der Höhe auf h0 geht. Passt alles, behalten sie den Abstand zur
    Oberkante. Sonst rückt, was unter der größten Lücke liegt, geschlossen hoch (unten verankerte Listen); nur wenn keine Lücke reicht,
    rücken alle zusammen."""
    liste = sorted(liste, key=lambda x: x[1][1])
    ende = max(b[1] + b[3] - oben for _, b in liste)
    ueber = ende + max(h_alt - ende, 0) - h0  # der Abstand zur Unterkante bleibt erhalten
    if ueber <= 0:
        return [(el, y0 + b[1] - oben) for el, b in liste]
    beste, ab, bisher = 0, None, liste[0][1][1] + liste[0][1][3]
    for i, (_, b) in enumerate(liste[1:], 1):
        if b[1] - bisher > beste:
            beste, ab = b[1] - bisher, i
        bisher = max(bisher, b[1] + b[3])
    if ab is not None and beste >= ueber + 0.02:
        return [(el, y0 + b[1] - oben - (ueber if i >= ab else 0)) for i, (el, b) in enumerate(liste)]
    return [(el, y0 + (b[1] - oben) * min(h0 / max(ende, 0.01), 1)) for el, b in liste]


def _einpassen(folie, verlegt=()):
    """Reicht der Inhalt in Logo und Fußzeile, staucht bippt ihn in der Höhe. Karten werden flacher; ihr Inhalt behält die Größe. Panels und
    verlegte Notizen zählen nicht mit. Rückgabe: Faktor oder None."""
    alle = [(el, _box(el)) for el in _formen(folie) if _box(el)]
    formen = [(el, b) for el, b in alle if not _ist_panel(el, b) and _sid(el) not in verlegt and not (b[1] + b[3] <= UNTEN and b[3] >= 5)]
    if not formen:
        return None
    tief = max(b[1] + b[3] for _, b in formen)
    if tief <= UNTEN:
        return None
    start = min((b[1] for _, b in formen if b[1] >= 1.25), default=1.25)
    f = (UNTEN - start) / (tief - start)
    flaechen = [(el, b) for el, b in formen if el.tag == qn("p:sp") and not _text(el) and _gefuellt(el) and b[1] >= start
                and b[2] >= 0.3 and b[3] >= 0.15]
    karten = [c for c in flaechen if c[1][3] >= 0.6 or _kleinster(flaechen, c[1]) is None]
    neu = {id(el): (start + (b[1] - start) * f, b[3] * f if b[3] >= 0.6 else b[3]) for el, b in karten}
    gruppen = {}
    for el, b in formen:
        if b[1] + b[3] <= start or b[1] < start:
            continue
        if id(el) in neu:
            _setze(el, y=neu[id(el)][0], h=neu[id(el)][1])
            continue
        eltern = _kleinster(karten, b)
        if eltern is not None:
            gruppen.setdefault(id(eltern[0]), (eltern, []))[1].append((el, b))
        else:
            _setze(el, y=start + (b[1] - start) * f, h=b[3] * f if el.tag in (qn("p:graphicFrame"), qn("p:cxnSp")) else None)
    for eltern, liste in gruppen.values():
        y0, h0 = neu[id(eltern[0])]
        for el, y in _inhalt_einpassen(liste, eltern[1][1], eltern[1][3], y0, h0):
            _setze(el, y=y)
    return f


def _chips_freistellen(folie):
    """Chip über dem Anfang eines Textes (Datum auf dem Zeitstrahl): Der Designer legt ihn oft über die erste Zeile. Der Text rückt darunter."""
    formen = [(el, _box(el)) for el in _formen(folie) if el.tag == qn("p:sp") and _box(el) and _text(el)]
    chips = [(el, b) for el, b in formen if _gefuellt(el) and b[3] < 0.5]
    for el, b in formen:
        if _gefuellt(el):
            continue
        for _, c in chips:
            ueberlappt = c[0] < b[0] + b[2] and c[0] + c[2] > b[0]
            if ueberlappt and c[1] <= b[1] < c[1] + c[3] < b[1] + 0.25:
                _setze(el, y=c[1] + c[3] + 0.03)
                break


# ----------------------------------------------------------------- Schrift
def _lauf_groessen(p):
    return [r.find(qn("a:rPr")) for r in p.findall(qn("a:r")) if r.find(qn("a:rPr")) is not None and r.find(qn("a:rPr")).get("sz")]


def _absaetze_mit_platz(el, b):
    """(Absatz, Läufe, Größe, Text, fett, Platz, ohne Umbruch) je Absatz mit fester Größe."""
    bp = el.find(".//" + qn("a:bodyPr"))
    if bp is None:
        return
    ohne_umbruch = bp.get("wrap") == "none"
    breite = b[2] - int(bp.get("lIns", 91440)) / ZOLL - int(bp.get("rIns", 91440)) / ZOLL
    for p in el.iter(qn("a:p")):
        laeufe = _lauf_groessen(p)
        if not laeufe:
            continue
        pr = p.find(qn("a:pPr"))
        einzug = int(pr.get("marL", 0)) / ZOLL if pr is not None else 0
        yield (laeufe, max(int(r.get("sz")) for r in laeufe) / 100, "".join(x.text or "" for x in p.iter(qn("a:t"))),
               any(r.get("b") == "1" for r in laeufe), max(breite - einzug, 0.05), ohne_umbruch)


def _passt_groesser(t, platz, g, fett):
    """Passt der Text in Mindestgröße ohne zusätzliche Zeile? Mit Reserve: Die Schätzung liegt bis 2 % daneben, eine neue Zeile fällt sofort auf."""
    zeilen, zu_breit = umbrechen(t, platz * 0.9, MIN_PT, fett=fett)
    return zeilen <= umbrechen(t, platz, g, fett=fett)[0] and not zu_breit


def _feste_groessen(formen):
    """Schriftgrößen unter dem Minimum, die auf dieser Folie nicht überall wachsen können. Sie bleiben ganz: Gleich gebaute Texte sollen gleich
    groß sein, ein Kärtchen mit 9 pt neben Kärtchen mit 7,3 pt sieht wie ein Fehler aus."""
    fest = set()
    for el in formen:
        b = _box(el)
        if b is None or not _text(el):
            continue
        for _, g, t, fett, platz, ohne_umbruch in _absaetze_mit_platz(el, b):
            if g < MIN_PT and not ohne_umbruch and not _passt_groesser(t, platz, g, fett):
                fest.add(g)
    return fest


def _schriftgroessen(el, b, fest):
    """Mindestgröße, außer die Größe steht in fest; kleiner, wo die Markenschrift ein Wort sonst trennen würde."""
    for laeufe, g, t, fett, platz, ohne_umbruch in _absaetze_mit_platz(el, b):
        ziel = g if g in fest else max(g, MIN_PT)
        if not ohne_umbruch:
            while ziel > UNTERGRENZE_PT and umbrechen(t, platz * 0.94, ziel, fett=fett)[1]:
                ziel -= 0.25
        for r in laeufe:
            alt = int(r.get("sz"))
            r.set("sz", str(int(ziel * 100) if alt < MIN_PT * 100 or ziel < g else alt))


def _schriften(el, kopf):
    for tag in ("a:rPr", "a:endParaRPr", "a:defRPr"):
        for r in el.iter(qn(tag)):
            for lat in r.findall(qn("a:latin")):
                lat.set("typeface", "+mj-lt" if lat.get("typeface") == kopf else "+mn-lt")
            for art in ("a:ea", "a:cs", "a:sym"):
                for x in r.findall(qn(art)):
                    r.remove(x)


# ----------------------------------------------------------------- Farben setzen
def _farbe_setzen(kette, neu):
    """Füllfarbe tauschen; Durchsicht (a:alpha) bleibt."""
    f = kette.find(qn("a:solidFill"))
    if f is None:
        return
    alpha = f.find(".//" + qn("a:alpha"))
    for k in list(f):
        f.remove(k)
    x = f.makeelement(qn("a:srgbClr"), {"val": neu})
    if alpha is not None:
        x.append(alpha)
    f.append(x)


def _eigene_farbe(kette):
    s = kette.find(qn("a:solidFill")) if kette is not None else None
    x = s.find(qn("a:srgbClr")) if s is not None else None
    return x.get("val").upper() if x is not None else None


def _behaelter(gemalt, b):
    """Oberste gemalte Fläche unter dem Mittelpunkt von b; None auf der Seite."""
    cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
    for f in reversed(gemalt):
        if f[0] <= cx <= f[0] + f[2] and f[1] <= cy <= f[1] + f[3]:
            return f
    return None


def _unter(gemalt, b, standard):
    f = _behaelter(gemalt, b)
    return f[4] if f else standard


def _icon_kante(b, gemalt):
    """Kantenlänge des Brand-Icons. Die Brand-Icons sind feine Linien und brauchen mehr Platz als die vollen Icons des
    Designers: In einem kleinen Kreis füllen sie ihn zu 70 %, sonst wachsen sie um ein Drittel."""
    kante = max(b[2], b[3])
    f = _behaelter(gemalt, b)
    if f and max(f[2], f[3]) < 0.7:
        return 0.7 * min(f[2], f[3])
    return kante * 1.33


def _mittig(el, b, gemalt):
    """Der Designer misst Textfelder auf seine Schrift. Sitzt ein Feld ohne Umbruch mittig in seiner Karte, soll es dort auch mit
    der schmaleren Markenschrift bleiben."""
    bp = el.find(".//" + qn("a:bodyPr"))
    f = _behaelter(gemalt, b)
    if bp is None or bp.get("wrap") != "none" or f is None or b[2] > f[2] * 0.95:
        return
    if abs((b[0] + b[2] / 2) - (f[0] + f[2] / 2)) < 0.04:
        for p in el.iter(qn("a:p")):
            pr = p.find(qn("a:pPr"))
            if pr is None:
                pr = p.makeelement(qn("a:pPr"), {})
                p.insert(0, pr)
            pr.set("algn", "ctr")


def _textfarben(el, pal, grund):
    for tag in ("a:rPr", "a:endParaRPr"):
        for r in el.iter(qn(tag)):
            alt = _eigene_farbe(r)
            if alt:
                _farbe_setzen(r, pal.text(alt, grund))
            elif r.getparent().find(qn("a:t")) is not None and r.find(qn("a:hlinkClick")) is None:
                f = r.makeelement(qn("a:solidFill"), {})
                f.append(f.makeelement(qn("a:srgbClr"), {"val": pal.text(DG, grund)}))
                r.insert(1 if r.find(qn("a:ln")) is not None else 0, f)
    for bu in el.iter(qn("a:buClr")):
        x = bu.find(qn("a:srgbClr"))
        if x is not None:
            x.set("val", pal.text(x.get("val").upper(), grund))


# ----------------------------------------------------------------- Bilder
def _hex(rgb):
    return "%02X%02X%02X" % tuple(rgb[:3])


def _bildart(blob):
    """(Bild, Art, Hauptfarben, häufigste Farbe). Art: icon (eine Farbe, durchsichtiger Grund), grafik (wenige flache Farben), foto.
    Gezählt wird auf einem kleinen Abzug, in Stufen von 16: Kanten glätten die Farben nur scheinbar in viele Töne."""
    from PIL import Image
    im = Image.open(io.BytesIO(blob)).convert("RGBA")
    klein = im.copy()
    klein.thumbnail((200, 200), Image.NEAREST)
    roh = klein.tobytes()
    stufen, gesamt, durchsichtig = {}, 0, 0
    for i in range(0, len(roh), 4):
        if roh[i + 3] > 200:
            k = (roh[i] // 16, roh[i + 1] // 16, roh[i + 2] // 16)
            s = stufen.setdefault(k, [0, roh[i:i + 3]])
            s[0] += 1
            gesamt += 1
        elif roh[i + 3] < 50:
            durchsichtig += 1
    if not gesamt:
        return im, "foto", [], None
    reihe = sorted(stufen.values(), key=lambda s: -s[0])
    haupt = [s for s in reihe if s[0] / gesamt >= 0.02]
    haeufig = reihe[0][1].hex().upper()
    if len(reihe) <= 4 and durchsichtig:
        return im, "icon", [haeufig], haeufig
    if (sum(s[0] for s in haupt) / gesamt >= 0.85 and len(haupt) <= 12) or len(blob) / (im.size[0] * im.size[1]) < 0.05:
        return im, "grafik", [s[1].hex().upper() for s in (haupt or reihe)[:12]], haeufig  # wenige Bytes je Pixel: nie ein Foto
    return im, "foto", [], haeufig


def _grafik_farben(im, haupt, regel):
    """Jedes Pixel zur nächsten Hauptfarbe, dann deren neue Farbe; Transparenz bleibt. Ohne den ersten Schritt würden die geglätteten
    Kanten zwischen den Farben bunt."""
    from PIL import Image
    ziele = {h: bytes.fromhex(regel(h)) for h in haupt}
    punkte = [(tuple(bytes.fromhex(h)), ziele[h]) for h in haupt]
    roh, aus, cache = im.tobytes(), bytearray(), {}
    for i in range(0, len(roh), 4):
        k = roh[i:i + 3]
        if k not in cache:
            r, g, b = k
            cache[k] = min(punkte, key=lambda p: (p[0][0] - r) ** 2 + (p[0][1] - g) ** 2 + (p[0][2] - b) ** 2)[1]
        aus += cache[k] + roh[i + 3:i + 4]
    neu = Image.frombytes("RGBA", im.size, bytes(aus))
    datei = io.BytesIO()
    neu.save(datei, "PNG")
    datei.seek(0)
    return datei, neu


def _umgefaerbt(im, farbe):
    from PIL import Image
    flaeche = Image.new("RGBA", im.size, tuple(bytes.fromhex(farbe)) + (255,))
    flaeche.putalpha(im.getchannel("A"))
    aus = io.BytesIO()
    flaeche.save(aus, "PNG")
    aus.seek(0)
    return aus


def _icon_schluessel(im):
    """Gleiche Form, gleicher Schlüssel: unabhängig von Farbe und Bildgröße."""
    maske = im.getchannel("A").resize((24, 24)).point(lambda v: 255 if v > 127 else 0)
    return hashlib.sha1(maske.tobytes()).hexdigest()[:6]


def _svg_schluessel(blob):
    """Schlüssel einer Form aus viewBox und Pfaden des SVG: unabhängig von Farbe, Größe und dem Stil-Abzug des Browsers."""
    x = blob.decode("utf-8", "ignore")
    vb = re.search(r'viewBox="([^"]+)"', x)
    return hashlib.sha1(((vb.group(1) if vb else "") + "|".join(re.findall(r'\sd="([^"]+)"', x))).encode()).hexdigest()[:8]


def _svg_von(folie, el):
    for x in el.iter():
        if x.tag.endswith("}svgBlip"):
            try:
                return _svg_schluessel(folie.part.related_part(x.get(qn("r:embed"))).blob)
            except (KeyError, AttributeError):
                return None
    return None


def _bild_einsetzen(folie, el, datei):
    """Bild der Form tauschen; die SVG-Fassung des Designers fällt weg, sonst zeigt PowerPoint weiter das fremde Icon."""
    _, rid = folie.part.get_or_add_image_part(datei)
    blip = el.find(".//" + qn("a:blip"))
    blip.set(qn("r:embed"), rid)
    for ext in blip.findall(qn("a:extLst")):
        blip.remove(ext)


def _icon_name(zuordnung, schluessel, maske, nr, sid):
    """Brand-Icon und Herkunft: Zuordnung des Agenten vor der festen Tabelle."""
    je_folie = zuordnung.get(str(nr))
    name = (je_folie.get(sid) if isinstance(je_folie, dict) else None) or zuordnung.get(schluessel) or zuordnung.get(maske)
    if name:
        return name, "agent"
    return (GLYPHEN[schluessel], "tabelle") if schluessel in GLYPHEN else (None, None)


def _bild(folie, el, b, pal, grund, gemalt, nr, m, zuordnung, liste, naechster):
    """Icons tauschen oder umfärben, Schmuck und flache Grafik in Markenfarben; nur Fotos bleiben. Malt sich in gemalt ein, damit Text
    darüber die richtige Farbe bekommt."""
    rid = el.find(".//" + qn("a:blip")).get(qn("r:embed"))
    blob = folie.part.related_part(rid).blob
    sid = _sid(el)
    w, h = b[2], b[3]
    try:
        im, art, haupt, farbe = _bildart(blob)
    except (OSError, ValueError):  # z. B. EMF: Pillow kann es nicht lesen
        liste["bilder"].append((nr, sid))
        return
    if art == "foto":
        liste["bilder"].append((nr, sid))
        if farbe:
            gemalt.append(b + (farbe, "bild"))
        return
    schmal = min(w, h) < 0.1 or max(w, h) / max(min(w, h), 0.01) > 2
    if art == "grafik" or schmal or w > ICON_MAX or h > ICON_MAX:
        haupt = haupt or [farbe]
        bunt = [x for x in haupt if _bunt(x)]
        if schmal and min(w, h) < 0.1:
            regel = lambda x: pal.linie(x, grund)  # noqa: E731
        elif len(bunt) >= 3:  # Torte als Bild: Kategorien bleiben unterscheidbar
            zuteilung = pal.reihe(bunt)
            regel = lambda x: zuteilung.get(x) or pal.flaeche(x)  # noqa: E731
        else:
            regel = pal.flaeche
        datei, neu = _grafik_farben(im, haupt, regel)
        _bild_einsetzen(folie, el, datei)
        mitte = neu.getpixel((neu.size[0] // 2, neu.size[1] // 2))
        if mitte[3] > 200:
            gemalt.append(b + (_hex(mitte), "bild"))
        return
    maske = _icon_schluessel(im)
    schluessel = _svg_von(folie, el) or maske
    name, herkunft = _icon_name(zuordnung, schluessel, maske, nr, sid)
    if name and max(w, h) >= ICON_KLEIN:
        datei = m.icon_pfad(name, "white" if _lum(grund) < 0.25 else "darkgreen")
        if datei is None:
            liste["fehlt"].append((nr, sid, name))
        else:
            _bild_einsetzen(folie, el, str(datei))
            kante = _icon_kante(b, gemalt)
            _setze(el, x=b[0] + w / 2 - kante / 2, y=b[1] + h / 2 - kante / 2, w=kante, h=kante)
            for src in el.findall(".//" + qn("a:srcRect")):
                src.getparent().remove(src)
            liste["getauscht"] += 1
            if herkunft == "agent":
                liste["gewaehlt"].setdefault(name, set()).add(schluessel)
            return
    s = pal.signal(farbe)
    ziel = SIGNAL[s][0] if s and _kontrast(SIGNAL[s][0], grund) >= 2 else max((DG, WH), key=lambda c: _kontrast(c, grund))
    _bild_einsetzen(folie, el, _umgefaerbt(im, ziel))
    if max(w, h) >= ICON_KLEIN:  # Häkchen und Punkte vor Listen sind Zeichen, kein Icon
        eintrag = liste["offen"].setdefault(schluessel, {"text": naechster, "folien": [], "bild": im})
        eintrag["folien"].append(nr)


def _naechster_text(b, texte):
    if not texte:
        return ""
    cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2

    def abstand(t):
        x, y, w, h = t[1]
        return max(x - cx, 0, cx - x - w) + max(y - cy, 0, cy - y - h)
    return min(texte, key=abstand)[2][:40]


def _bogen_offener_icons(offen, ziel):
    """Bild aller offenen Formen mit Schlüssel: Kann der Agent Bilder sehen, wählt er nach der Form statt nur nach dem Text daneben."""
    from PIL import Image, ImageDraw
    spalten = 10
    reihen = (len(offen) + spalten - 1) // spalten
    bogen = Image.new("RGB", (spalten * 110, reihen * 100), "white")
    stift = ImageDraw.Draw(bogen)
    for i, (k, v) in enumerate(offen.items()):
        x, y = (i % spalten) * 110, (i // spalten) * 100
        bogen.paste(tuple(bytes.fromhex(DG)), (x + 25, y + 6), v["bild"].getchannel("A").resize((60, 60), Image.LANCZOS))
        stift.text((x + 25, y + 72), k, fill="black")
    bogen.save(str(ziel))
    return ziel


# ----------------------------------------------------------------- Formen umstellen
def _umstellen(folie, nr, pal, seite, kopf, m, zuordnung, liste):
    """Farben, Schriften, Ecken, Schatten und Bilder einer Folie, in Zeichenreihenfolge: Was unten liegt, bestimmt die Farbe darüber."""
    gemalt = []
    formen = _formen(folie)
    texte = [(el, _box(el), _text(el)) for el in formen if _box(el) and _text(el)]
    fest = _feste_groessen(formen)
    for el in formen:
        b = _box(el)
        sp = el.find(qn("p:spPr"))
        if el.tag == qn("p:pic"):
            if b:
                _bild(folie, el, b, pal, _unter(gemalt, b, seite), gemalt, nr, m, zuordnung, liste, _naechster_text(b, texte))
            continue
        grund_form = None
        if sp is not None:
            for fx in sp.findall(qn("a:effectLst")):
                for k in list(fx):
                    fx.remove(k)
            geo = sp.find(qn("a:prstGeom"))
            if geo is not None and geo.get("prst") == "roundRect":  # die Marke kennt keine runden Ecken an Karten
                geo.set("prst", "rect")
                av = geo.find(qn("a:avLst"))
                if av is not None:
                    for k in list(av):
                        av.remove(k)
            verlauf = sp.find(qn("a:gradFill"))
            if verlauf is not None:
                erster = verlauf.find(".//" + qn("a:srgbClr"))
                voll = sp.makeelement(qn("a:solidFill"), {})
                voll.append(voll.makeelement(qn("a:srgbClr"), {"val": erster.get("val") if erster is not None else DG}))
                sp.replace(verlauf, voll)
            alt = _eigene_farbe(sp)
            if alt and b:
                unter = _unter(gemalt, b, seite)
                duenn = min(b[2], b[3]) < 0.08
                neu = pal.linie(alt, unter) if duenn else pal.flaeche(alt)
                if neu == WH and unter == WH and not duenn and b[2] * b[3] > 1:
                    neu = FEIN  # weiße Karte auf weißer Seite wäre unsichtbar
                _farbe_setzen(sp, neu)
                grund_form = neu
                if not duenn:
                    gemalt.append(b + (neu,))
            ln = sp.find(qn("a:ln"))
            alt_l = _eigene_farbe(ln)
            if alt_l and b:
                _farbe_setzen(ln, pal.linie(alt_l, grund_form or _unter(gemalt, b, seite)))
        if el.tag == qn("p:graphicFrame"):
            _tabelle(el, pal, seite)
        elif b or _text(el):
            grund = grund_form or (_unter(gemalt, b, seite) if b else seite)
            _textfarben(el, pal, grund)
            if b and not grund_form:
                _mittig(el, b, gemalt)
                f = _behaelter(gemalt, b)
                if f and len(f) > 5:  # auf einem Bild: Weiß statt Akzentgrün, die Prüfung kennt den Grund dort nicht
                    for r in el.iter(qn("a:rPr")):
                        if _eigene_farbe(r) == AG:
                            _farbe_setzen(r, WH)
            bp = el.find(".//" + qn("a:bodyPr"))
            if b and b[2] < 0.3 and bp is not None and len(_text(el)) <= 4:  # Ziffer in Kreis oder Seitenangabe
                bp.set("wrap", "none")
            if b:
                _schriftgroessen(el, b, fest)
        _schriften(el, kopf)
    _diagramme(folie, pal, seite)


def _tabelle(el, pal, seite):
    for zelle in el.iter(qn("a:tc")):
        pr = zelle.find(qn("a:tcPr"))
        alt = _eigene_farbe(pr)
        grund = seite
        if alt:
            grund = pal.flaeche(alt)
            _farbe_setzen(pr, grund)
        _textfarben(zelle, pal, grund)


def _diagramme(folie, pal, seite):
    """Kategorien in der Chart order der Marke, Kanten weiß, Text und Achsen nach ihrer Rolle."""
    for rel in list(folie.part.rels.values()):
        if rel.reltype != RT.CHART:
            continue
        wurzel = rel.target_part._element
        reihen = []
        for tag in ("c:ser", "c:dPt"):
            for k in wurzel.iter(qn(tag)):
                sp = k.find(qn("c:spPr"))
                if sp is not None:
                    reihen.append(sp)
        quelle = []
        for sp in reihen:
            c = _eigene_farbe(sp) or _eigene_farbe(sp.find(qn("a:ln")))
            if c:
                quelle.append(c)
        zuteilung = pal.reihe(quelle)
        for sp in reihen:
            fuell, ln = _eigene_farbe(sp), sp.find(qn("a:ln"))
            if fuell:
                _farbe_setzen(sp, zuteilung[fuell])
                if _eigene_farbe(ln):
                    _farbe_setzen(ln, WH)
            elif _eigene_farbe(ln):
                _farbe_setzen(ln, zuteilung[_eigene_farbe(ln)])
        for tag in ("a:rPr", "a:defRPr"):
            for r in wurzel.iter(qn(tag)):
                if _eigene_farbe(r):
                    _farbe_setzen(r, pal.text(_eigene_farbe(r), seite))
        for x in wurzel.iter(qn("a:srgbClr")):
            vorfahren = list(x.iterancestors())
            if any(v.tag in (qn("a:rPr"), qn("a:defRPr")) for v in vorfahren):
                continue
            kette = next((v for v in vorfahren if v.tag == qn("c:spPr")), None)
            if kette is not None and kette.getparent().tag in (qn("c:ser"), qn("c:dPt")):
                continue
            x.set("val", pal.linie(x.get("val").upper(), seite))
        for lat in wurzel.iter(qn("a:latin")):
            lat.set("typeface", "+mn-lt")
        for art in ("a:ea", "a:cs"):
            for x in list(wurzel.iter(qn(art))):
                x.getparent().remove(x)


def _reste_entfernen(folie):
    """Bilder ohne Verweis (entfernte Vollbilder, SVG-Fassungen) nicht mitspeichern."""
    xml = folie.part.blob.decode("utf-8") if isinstance(folie.part.blob, bytes) else folie.part.blob
    for rid, rel in list(folie.part.rels.items()):
        if rel.reltype == RT.IMAGE and f'"{rid}"' not in xml:
            folie.part.rels._rels.pop(rid)


# ----------------------------------------------------------------- Titelfolie
def _ist_titelfolie(folie, nr):
    if nr != 1:
        return False
    bg, bild = _hintergrund(folie)
    voll = any(el.tag == qn("p:pic") and _box(el) and _box(el)[2] >= 13 and _box(el)[3] >= 7 for el in _formen(folie))
    return voll or bild or (bg is not None and _lum(bg) < 0.25) or "title" in folie.slide_layout.name.lower()


def _titelfolie(prs, quelle, vermerk):
    """Titelfolie des Masters mit den Texten des Designers; kein Text geht verloren: größter = Titel, die Zeile darunter = Untertitel,
    alles andere als eine Zeile auf Ebene 2. Mehr passt nicht über den Vermerk."""
    texte = [(el, _box(el), _text(el)) for el in _formen(quelle) if _box(el) and _text(el)]
    texte.sort(key=lambda t: t[1][1])
    sl = prs.slides.add_slide(vorlage.layout(prs, "titel"))
    if texte:
        gross = max(texte, key=lambda t: _groesse(t[0]))
        rest = [t for t in texte if t is not gross]
        darunter = [t for t in rest if gross[1][1] < t[1][1] < FUSS_OBEN and t[1][0] < 6.67]
        erste = darunter[0] if darunter else None
        weitere = [t[2] for t in rest if t is not erste]
        sl.shapes.title.text = gross[2]
        ph = vorlage.platzhalter(sl, idx=1)
        zeilen = ([(erste[2], 0)] if erste else []) + ([(" | ".join(weitere), 1)] if weitere else [])
        if ph is not None and zeilen:
            tf = ph.text_frame
            for i, (t, stufe) in enumerate(zeilen):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = t
                p.level = stufe
    vorlage.leere_platzhalter_entfernen(sl)
    vorlage.fusszeile(sl, vermerk, nummer=False)
    return sl


# ----------------------------------------------------------------- Ablauf
def marke(pfad, ziel=None, icons=None, fusszeile=None):
    """Überträgt das Deck pfad in die Marke. Rückgabe: (Zieldatei, Ergebnisse)."""
    quelle = vorlage.oeffnen(pfad)
    vl = konfig.vorlage_pfad()
    if vl is None:
        raise SystemExit("Keine BI-Vorlage gefunden")
    prs = vorlage.oeffnen(vl)
    vorlage.alle_folien_entfernen(prs)
    m = Marke()
    m.aus_vorlage(prs)
    zuordnung = json.loads(Path(icons).read_text(encoding="utf-8")) if icons else {}
    seiten = [_hintergrund(s)[0] for s in quelle.slides]
    haeufig = max(set(x for x in seiten if x) or {WH}, key=seiten.count)
    pal = Palette(_deck_farben(quelle), haeufig)
    kopf = _kopfschrift(quelle)
    vermerk = konfig.laden().get("vertraulichkeit", "ONLY FOR INTERNAL USE")
    trenner = "     |     "

    decktitel, titelnr = "", None
    if len(quelle.slides) and _ist_titelfolie(quelle.slides[0], 1):
        titelnr = 1
        kand = [el for el in _formen(quelle.slides[0]) if _text(el)]
        decktitel = _text(max(kand, key=_groesse)) if kand else ""
    fuss = _fusstexte(quelle, decktitel)
    liste = {"getauscht": 0, "offen": {}, "fehlt": [], "bilder": [], "gewaehlt": {}}
    gestaucht, entfernt = [], 0
    fuss_text = trenner.join(x for x in (fusszeile or decktitel, vermerk) if x)
    for nr, q in enumerate(quelle.slides, 1):
        if nr == titelnr:
            _titelfolie(prs, q, vermerk)
            continue
        bg, _ = _hintergrund(q)
        dunkel = bg is not None and _lum(bg) < 0.25
        sl, _ = bibliothek.kopieren(prs, quelle, nr, layout="One content dark" if dunkel else "Only title")
        entfernt += _aufraeumen(sl, set(fuss.get(nr, [])))
        csld = sl._element.find(qn("p:cSld"))
        for alt in csld.findall(qn("p:bg")):
            csld.remove(alt)
        seite = DG if dunkel else WH
        if not dunkel and bg is not None and bg != WH:
            seite = SEITE
            sl.background.fill.solid()
            sl.background.fill.fore_color.rgb = RGBColor.from_string(SEITE)
        _titel_setzen(sl)
        _panels_kuerzen(sl)
        _chips_freistellen(sl)
        f = _einpassen(sl, _notizen_verlegen(sl))
        if f:
            gestaucht.append(f"{nr} ({f:.0%})")
        _umstellen(sl, nr, pal, seite, kopf, m, zuordnung, liste)
        vorlage.fusszeile(sl, fuss_text)
        _reste_entfernen(sl)
    ziel = Path(ziel) if ziel else Path(pfad).with_name(Path(pfad).stem + "_BI.pptx")
    prs.save(str(ziel))
    n_offen = sum(len(v["folien"]) for v in liste["offen"].values())
    print(f"MARKE: {ziel} – {len(prs.slides)} Folien, Gestaltung übernommen")
    print(f"  Fremdes Beiwerk entfernt: {entfernt} Formen · in der Höhe eingepasst: {', '.join(gestaucht) or 'keine Folie'}")
    print(f"  Icons: {liste['getauscht']} durch Brand-Icons ersetzt, {n_offen} nur umgefärbt")
    for nr, sid, name in liste["fehlt"]:
        print(f"  WARNUNG Folie {nr} #{sid}: Brand-Icon „{name}“ nicht gefunden (bippt icons <Begriff>)")
    for nr, sid in liste["bilder"]:
        print(f"  HINWEIS Folie {nr} #{sid}: Foto bleibt wie es ist, Farben prüfen")
    einfoermig = {n: len(k) for n, k in liste["gewaehlt"].items() if len(k) >= EINFOERMIG_AB}
    liste["einfoermig"] = einfoermig
    for n, zahl in einfoermig.items():
        print(f"  WARNUNG Einförmig: „{n}“ steht für {zahl} verschiedene Formen – je Form das Icon nehmen, das sie zeigt")
    if liste["offen"]:
        bogen = _bogen_offener_icons(liste["offen"], ziel.with_name(ziel.stem + "_icons_offen.png"))
        print(f"  OFFENE ICONS – Bild aller Formen: {bogen.name}. Schlüssel, Anzahl, Text daneben. Datei {{\"<Schlüssel>\": \"<Brand-Icon>\"}}, dann erneut mit --icons:")
        for k, v in liste["offen"].items():
            print(f"    {k} {len(v['folien'])}× „{v['text']}“ F{','.join(map(str, sorted(set(v['folien']))))}")
    offen = len(liste["offen"]) + len(liste["fehlt"])
    print("ERGEBNIS: " + ("OK" if not offen and not einfoermig else
                          ", ".join(x for x in (f"{offen} Icon(s) offen" if offen else "", f"{len(einfoermig)} Icon(s) einförmig" if einfoermig else "") if x)))
    return ziel, liste
