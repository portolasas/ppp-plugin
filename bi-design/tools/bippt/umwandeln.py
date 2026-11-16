"""Fremde Präsentation ins BI-Design bringen.

Weg 1 (empfohlen) „entwurf“: Inhalt → Spezifikation (analyse.entwurf) → Agent verdichtet → bauen auf der BI-Vorlage.
Weg 2 (schnell) „stil“: Folien bleiben wie sie sind, nur Farben → nächste Markenfarbe, Schriften → Theme-Schriften,
Theme-Farben/-Schriften des Masters → BI. Gut für viele Folien mit Diagrammen/Bildern, die neu zu bauen zu teuer wäre.
Ergebnis von Weg 2 nutzt weiterhin den alten Master (Layouts/Logo) – im Bericht steht das als Befund.
"""
import json
import re
from pathlib import Path

from lxml import etree
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

from . import analyse, konfig, vorlage
from .marke import Marke

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _naechste(h, palette):
    r, g, b = _rgb(h)
    # Helligkeit stärker gewichten, damit dunkle Texte dunkel und helle Flächen hell bleiben
    def dist(p):
        pr, pg, pb = _rgb(p)
        return 2 * (r - pr) ** 2 + 4 * (g - pg) ** 2 + 3 * (b - pb) ** 2
    return min(palette, key=dist)


def entwurf(pfad, ziel=None):
    """Spec-Entwurf neben die Quelle bzw. nach ziel; Bilder in <Quelle>_medien/ neben der Spec."""
    ziel = Path(ziel) if ziel else Path(pfad).with_name(Path(pfad).stem + "_BI.spec.json")
    spec = analyse.entwurf(pfad, ziel.with_name(Path(pfad).stem + "_medien"))
    ziel.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ENTWURF: {ziel} – {len(spec['folien'])} Folien. Jetzt Typen verdichten, dann: bippt bauen {ziel.name}")
    return ziel


def stil(pfad, ziel=None):
    prs = vorlage.oeffnen(pfad)
    m = Marke()
    vl = konfig.vorlage_pfad()
    if vl:
        m.aus_vorlage(vorlage.oeffnen(vl))
    palette = sorted(m.erlaubte_farben())
    ersetzt, schriften = {}, 0
    teile = list(prs.slides) + list(prs.slide_layouts) + list(prs.slide_masters)
    for t in teile:
        for el in t._element.iter(A + "srgbClr"):
            v = el.get("val", "").upper()
            if v not in palette:
                n = _naechste(v, palette)
                ersetzt[v] = n
                el.set("val", n)
        for tag in ("latin", "ea", "cs"):
            for el in t._element.iter(A + tag):
                tf = el.get("typeface", "")
                if tf and not tf.startswith("+") and not re.match(r"Boehringer Forward|Segoe UI|Arial|Symbol|Wingdings", tf):
                    el.set("typeface", "+mj-lt" if "Head" in tf or "Light" in tf else "+mn-lt")
                    schriften += 1
    # Theme: Farbschema und Schriftschema der BI-Vorlage übernehmen
    if vl:
        bi = vorlage.oeffnen(vl)
        bi_theme = etree.fromstring(bi.slide_masters[0].part.part_related_by(RT.THEME).blob)
        for master in prs.slide_masters:
            part = master.part.part_related_by(RT.THEME)
            x = etree.fromstring(part.blob)
            for tag in ("clrScheme", "fontScheme"):
                alt, neu = x.find(".//" + A + tag), bi_theme.find(".//" + A + tag)
                if alt is not None and neu is not None:
                    alt.getparent().replace(alt, neu.__copy__())
            part._blob = etree.tostring(x, xml_declaration=True, encoding="UTF-8", standalone=True)
    ziel = Path(ziel) if ziel else Path(pfad).with_name(Path(pfad).stem + "_BI-Stil.pptx")
    prs.save(str(ziel))
    print(f"STIL: {ziel}")
    print(f"  Farben ersetzt: {len(ersetzt)} ({', '.join(f'#{a}→#{b}' for a, b in list(ersetzt.items())[:10])}{' …' if len(ersetzt) > 10 else ''})")
    print(f"  Schriften auf Theme-Schrift gesetzt: {schriften}")
    if not vorlage.ist_bi_master(prs):
        print("  HINWEIS: Layouts/Logo stammen weiter aus dem alten Master – für volle Konformität Weg „entwurf“.")
    return ziel
