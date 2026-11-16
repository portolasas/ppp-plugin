"""Präsentation aus einer Spezifikation (JSON) bauen.

Spezifikation (Auszug, vollständig in reference/folientypen.md):
{
  "ausgabe": "Projekt_Update_07.10.2026.pptx",   relativ zur Spec
  "vorlage": "…/BI_Vorlage_16x9.pptx",            optional; Standard aus ~/.bi-design/config.json
  "basis":   "Altes_Deck.pptx",                   optional; dann ist das alte Deck Vorlage UND Folienquelle
  "fusszeile": "Projekt | Anlass | 07.10.2026",
  "heute": "2026-10-07",
  "zweck": "…", "quellen": ["…"],                 optional; Kopf der Folienbeschreibung
  "dokument": "Konzept.md",                       optional; vorhandene Vorlage, sonst <ausgabe>.md (beschreiben.py)
  "bibliothek": "…/BI_Slide_Library.pptx",        optional; Standard aus den Einstellungen bzw. dem Plugin
  "folien": [ {"typ": "titel", …}, {"basis": 7, "ausblenden": true, "ersetzen": {"alt": "neu"}},
              {"bib": 25, "texte": {"5": "…"}}, … ]
}
Folien aus der Basis, die nicht in "folien" stehen, werden entfernt. Basisfolien ändern: ersetzen, platzhalter, titel,
aendern (einzelne Formen, siehe aendern.py), elemente (neue Formen wie im Typ frei). Bibliotheksfolien (bib) werden aus
der Folienbibliothek kopiert und gefüllt (bibliothek.py), danach wie Basisfolien geändert.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

from lxml import etree
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn

from . import beschreiben, bibliothek, konfig, vorlage
from .aendern import _absatz_setzen, aendern, ersetzen, platzhalter_zeilen
from .bausteine import Kontext, band, unterkante
from .folien import TYPEN, frei
from .marke import Marke


def _theme_schriften(prs):
    try:
        th = prs.slide_masters[0].part.part_related_by(RT.THEME)
        x = etree.fromstring(th.blob)
        ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
        kopf = x.find(".//a:majorFont/a:latin", ns).get("typeface")
        txt = x.find(".//a:minorFont/a:latin", ns).get("typeface")
        return kopf, txt
    except (KeyError, AttributeError, etree.XMLSyntaxError):
        return "", ""


def _fusszeile_basis(folie, text):
    for ph in folie.placeholders:
        if ph._element.find(".//" + qn("p:ph")).get("type") == "ftr" and ph.text_frame.paragraphs:
            _absatz_setzen(ph.text_frame.paragraphs[0], text)


def _abgestuft(basis, mods):
    """Näherung einer Abstufung (lumMod/lumOff/tint/shade) in RGB – reicht, um die nächste Markenfarbe zu finden."""
    r, g, b = (int(basis[i:i + 2], 16) for i in (0, 2, 4))
    for name, wert in mods:
        f = wert / 100000
        if name in ("lumMod", "shade"):
            r, g, b = r * f, g * f, b * f
        elif name == "lumOff":
            r, g, b = r + 255 * f, g + 255 * f, b + 255 * f
        elif name == "tint":
            r, g, b = (255 - (255 - v) * f for v in (r, g, b))
    return "".join(f"{max(0, min(255, round(v))):02X}" for v in (r, g, b))


def farben_angleichen(folie, marke):
    """Farben außerhalb von Marke + Vorlage und Abstufungen von Designfarben (Master: nicht CD-konform) auf die
    nächste Markenfarbe setzen (nur diese Folie; Formstile bleiben, sie füllen nichts sichtbar)."""
    from lxml import etree
    from .umwandeln import _naechste
    a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    palette = sorted(marke.erlaubte_farben() | {"000000", "FFFFFF"})
    stufen = {"lumMod", "lumOff", "tint", "shade"}
    thema = None
    n = 0
    for el in list(folie._element.iter(a + "srgbClr", a + "schemeClr")):
        anc = el.getparent()
        while anc is not None and anc.tag.split("}")[-1] != "style":
            anc = anc.getparent()
        if anc is not None:
            continue
        mods = [(c.tag.split("}")[-1], int(c.get("val", "100000"))) for c in el if c.tag.split("}")[-1] in stufen]
        if el.tag == a + "srgbClr" and not mods:
            v = el.get("val", "").upper()
            if v not in palette:
                el.set("val", _naechste(v, palette))
                n += 1
        elif mods:
            if el.tag == a + "schemeClr":
                thema = thema if thema is not None else vorlage.themafarben(folie)
                basis = thema.get(vorlage.THEMA.get(el.get("val"), el.get("val")), "")
            else:
                basis = el.get("val", "").upper()
            if len(basis) != 6:
                continue
            neu = etree.Element(a + "srgbClr", val=_naechste(_abgestuft(basis, mods), palette))
            for c in el:
                if c.tag.split("}")[-1] == "alpha":
                    neu.append(c)
            el.getparent().replace(el, neu)
            n += 1
    return n


def _pfad(basisordner, p):
    if not p:
        return None
    q = Path(p).expanduser()
    return q if q.is_absolute() else (basisordner / q)


def _vor_dem_bau(ziel, basis, doc, erzwingen):
    """Nie die eigene Basis und nie ein Deck überschreiben, das nach dem letzten Bau geändert wurde (z. B. in PowerPoint)."""
    if basis is not None and basis.resolve() == ziel.resolve():
        raise SystemExit(f"ABBRUCH: basis und ausgabe sind dieselbe Datei ({ziel.name}) – jeder weitere Bau wendet ersetzen "
                         "und aendern erneut an. ausgabe als neue Datei angeben (z. B. neues Datum im Namen).")
    if erzwingen or not ziel.is_file():
        return None
    bau = beschreiben.baustand(doc)
    rat = (f"Änderungen behalten (Empfehlung): neue Spec mit \"basis\": \"{ziel.name}\", alle Folien als {{\"basis\": n}}, "
           "nur die zu ändernden anpassen, ausgabe als neue Datei. Verwerfen nur nach Rückfrage beim Nutzer: "
           "bippt bauen <spec> --erzwingen.")
    if bau is None:
        raise SystemExit(f"ABBRUCH: {ziel.name} gibt es schon, aber ohne Baustand in {doc.name} (vor bi-design 2.3 oder "
                         f"nicht mit dieser Spec gebaut) – ein Neubau überschriebe Änderungen, die nicht in der Spec stehen. "
                         + rat)
    hand = beschreiben.nachtraeglich(ziel, bau)
    if hand:
        raise SystemExit(f"ABBRUCH: {ziel.name} wurde nach dem letzten Bau geändert (Folie {', '.join(map(str, hand))}) – "
                         f"ein Neubau aus der Spec überschriebe das. Jetzigen Stand beschreiben: bippt beschreiben "
                         f"{ziel.name}. " + rat)
    return bau


def _messen(k):
    """Nach dem Bau einer Folie: Titel, der in den Inhalt umbricht, und Wörter, die breiter als ihr Textfeld sind."""
    try:
        w = vorlage.titel_pruefen(k.folie)
    except (AttributeError, KeyError, ValueError, TypeError):  # fremde Basisfolien: Bau nie abbrechen
        w = None
    if w:
        k.warn(w)
    k.wortbreite_melden()


def bauen(spec_pfad, ausgabe=None, still=False, erzwingen=False):
    spec_pfad = Path(spec_pfad)
    spec = json.loads(spec_pfad.read_text(encoding="utf-8"))
    ordner = spec_pfad.parent
    warnungen = []
    m = Marke(spec.get("marke"))
    basis = _pfad(ordner, spec.get("basis"))
    ziel = Path(ausgabe) if ausgabe else _pfad(ordner, spec.get("ausgabe") or spec_pfad.with_suffix(".pptx").name)
    doc, w_doc = beschreiben.ziel_fuer(spec, spec_pfad, ziel)
    warnungen += [w_doc] if w_doc else []
    bau_alt = _vor_dem_bau(ziel, basis, doc, erzwingen)
    quelle = basis or _pfad(ordner, spec.get("vorlage")) or konfig.vorlage_pfad()
    if quelle is None:
        warnungen.append("Keine BI-Vorlage gefunden – Notbetrieb ohne Master/Logo. "
                         "`bippt vorlage <BI-Deck.pptx>` ausführen oder vorlage in der Spec angeben.")
    elif not Path(quelle).is_file():
        raise SystemExit(f"Vorlage/Basis nicht gefunden: {quelle}")
    prs = vorlage.oeffnen(quelle)
    if quelle is not None and not vorlage.ist_bi_master(prs):
        warnungen.append(f"{Path(quelle).name}: kein BI-Master – erst umwandeln (bippt umwandeln) oder BI-Vorlage nutzen")
    m.aus_vorlage(prs)
    alte = list(prs.slides)
    if not basis and alte:
        vorlage.alle_folien_entfernen(prs)
        alte = []
    kopf, txt = _theme_schriften(prs)
    schriften = ("+mj-lt", "+mn-lt") if "Boehringer" in kopf + txt else (m.schrift_kopf, m.schrift_text)
    heute = spec.get("heute") or dt.date.today().isoformat()
    cfg = konfig.laden()
    vermerk = spec.get("vertraulichkeit", cfg.get("vertraulichkeit", "ONLY FOR INTERNAL USE"))
    trenner = "     |     "  # wie im BI-Master v2.1
    fuss = trenner.join(x for x in (spec.get("fusszeile"), vermerk) if x) or None
    reihenfolge, ausblenden_ab, bib = [], False, None

    def bestehende_folie(sl, fs, nr, wo, bib_nr=None):
        """Basis- oder Bibliotheksfolie: füllen (bib) und ändern wie in der Spec, Fußzeile setzen, messen."""
        k = Kontext(prs, sl, m, schriften, warnungen, nr)
        k.ordner = ordner
        k.dunkel = any(sl.slide_layout.name in vorlage.LAYOUTS[kurz] for kurz in vorlage.DUNKLE_LAYOUTS)
        if fs.get("ersetzen"):
            gefunden = ersetzen(sl, fs["ersetzen"])  # genau einmal je Folie (sonst doppelt ersetzt)
            fehlt = [a for a in fs["ersetzen"] if a not in gefunden]
            if fehlt:
                warnungen.append(f"Folie {nr} ({wo}): {len(fehlt)} von {len(fs['ersetzen'])} Ersetzungen "
                                 "nicht gefunden: " + "; ".join(f"„{a[:40]}“" for a in fehlt))
        for idx, zeilen in (fs.get("platzhalter") or {}).items():
            ph = vorlage.platzhalter(sl, idx=int(idx))
            if ph is None:
                warnungen.append(f"Folie {nr}: Platzhalter {idx} fehlt")
            else:
                platzhalter_zeilen(ph, zeilen)
        if fs.get("titel") and sl.shapes.title is not None:
            platzhalter_zeilen(sl.shapes.title, fs["titel"])
        if bib_nr is not None:
            if fs.get("titel") and sl.shapes.title is None:
                k.warn(f"Bibliotheksfolie {bib_nr} hat keine Titelzeile – titel entfällt; Text über texte setzen")
            bibliothek.fuellen(k, fs, ordner)
        if fs.get("aendern"):
            aendern(k, fs["aendern"], ordner)
        if fs.get("elemente"):
            frei(k, fs)
        if fs.get("farben_angleichen", spec.get("basis_farben_angleichen")):
            n = farben_angleichen(sl, m)
            if n:
                warnungen.append(f"Folie {nr} ({wo}): {n} Nicht-Markenfarben angeglichen – im Render prüfen")
        if fuss and fs.get("fusszeile", True):
            _fusszeile_basis(sl, vermerk if sl.slide_layout.name.startswith("Title slide") else fuss)
        if bib_nr is not None:
            rest = bibliothek.blindtext(sl)
            if rest:
                k.warn("Blindtext der Bibliothek übrig – füllen (texte) oder entfernen: "
                       + "; ".join(f"id {i} „{t}“" for i, _, t in rest[:6]) + (" …" if len(rest) > 6 else ""))
        if bib_nr is not None or any(fs.get(x) for x in ("ersetzen", "platzhalter", "titel", "aendern", "elemente")):
            _messen(k)

    for nr, fs in enumerate(spec.get("folien", []), 1):
        if "basis" in fs:
            i = int(fs["basis"]) - 1
            if not 0 <= i < len(alte):
                raise SystemExit(f"Folie {nr}: basis {fs['basis']} existiert nicht (Basis hat {len(alte)} Folien)")
            sl = alte[i]
            bestehende_folie(sl, fs, nr, f"Basis {i + 1}")
        elif "bib" in fs:
            if bib is None:
                bp = bibliothek.pfad(spec, ordner)
                if bp is None or not bp.is_file():
                    raise SystemExit(f"Folie {nr}: Folienbibliothek nicht gefunden ({bp or 'nicht eingerichtet'}) – "
                                     "\"bibliothek\" in der Spec oder bippt konfig --setze bibliothek=<pptx>")
                bib = vorlage.oeffnen(bp)
            sl, w = bibliothek.kopieren(prs, bib, int(fs["bib"]))
            if w:
                warnungen.append(f"Folie {nr}: {w}")
            bestehende_folie(sl, fs, nr, f"Bibliothek {fs['bib']}", bib_nr=int(fs["bib"]))
        else:
            typ = fs.get("typ", "text")
            if typ not in TYPEN:
                raise SystemExit(f"Folie {nr}: unbekannter typ '{typ}' – vorhanden: {', '.join(sorted(TYPEN))}")
            fn, lay = TYPEN[typ]
            if fs.get("dunkel") and lay + "_dunkel" in vorlage.LAYOUTS:
                lay += "_dunkel"
            lay = fs.get("layout", lay)
            sl = prs.slides.add_slide(vorlage.layout(prs, lay))
            k = Kontext(prs, sl, m, schriften, warnungen, nr)
            k.ordner = ordner
            k.heute = fs.get("heute", heute)
            k.dunkel = lay in vorlage.DUNKLE_LAYOUTS
            titel = fs.get("titel", "Agenda" if typ == "agenda" else None)
            if titel is not None and sl.shapes.title is not None:
                sl.shapes.title.text = re.sub(r"\*\*|==", "", titel)
            fn(k, fs)
            if fs.get("band") and typ not in ("titel", "kapitel", "kernaussage"):
                band(k, fs["band"], unten=unterkante(fs))
            if fs.get("quelle"):
                if not vorlage.quelle(sl, fs["quelle"]):
                    warnungen.append(f"Folie {nr}: Layout ohne Quellenzeile")
            vorlage.leere_platzhalter_entfernen(sl)
            # Titelfolien: nur der Vertraulichkeitsvermerk (How-to slides, BI-Master v2.1)
            text_fuss = (vermerk or None) if typ == "titel" else fuss
            vorlage.fusszeile(sl, text_fuss if fs.get("fusszeile", True) else None, nummer=typ != "titel")
            _messen(k)
        if fs.get("notizen"):
            sl.notes_slide.notes_text_frame.text = fs["notizen"]
        if fs.get("ab_hier_ausblenden"):
            ausblenden_ab = True
        if fs.get("ausblenden") or ausblenden_ab:
            sl._element.set("show", "0")
        elif "basis" in fs and "ausblenden" not in fs:
            pass  # Basisfolie behält ihren Zustand (sichtbar/ausgeblendet)
        elif sl._element.get("show") is not None:
            del sl._element.attrib["show"]
        reihenfolge.append(sl)
    warnungen += bibliothek.abwechslung(spec.get("folien", []))
    warnungen += bibliothek.schreibweise(spec.get("folien", []))
    warnungen += bibliothek.offene_punkte(spec.get("folien", []))
    # Reihenfolge herstellen, nicht verwendete Basisfolien entfernen
    lst = prs.slides._sldIdLst
    nach_part = {id(prs.part.related_part(e.rId)): e for e in lst}
    neu = [nach_part[id(s.part)] for s in reihenfolge]
    for e in list(lst):
        lst.remove(e)
        if e not in neu:
            prs.part.drop_rel(e.rId)
    for e in neu:
        lst.append(e)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(ziel))
    # Folienbeschreibung mit Baustand – aus der gespeicherten Datei, wie bei der Prüfung vor dem nächsten Bau
    meldung, bau = beschreiben.schreiben(vorlage.oeffnen(ziel), ziel, doc, spec, spec_pfad, gebaut=True,
                                         weitere=[basis.with_suffix(".md")] if basis else [])
    if not still:
        sichtbar = sum(1 for s in reihenfolge if s._element.get("show") != "0")
        print(f"GEBAUT: {ziel} – {len(reihenfolge)} Folien ({sichtbar} sichtbar)")
        print(meldung)
        if bau_alt is None:
            print("ÄNDERUNGEN: erster Bau dieser Datei")
        else:
            geaendert, gleich, weg = beschreiben.aenderungen(bau_alt, bau)
            print(f"ÄNDERUNGEN: {'Folie ' + ', '.join(map(str, geaendert)) if geaendert else 'keine Folie'} geändert oder "
                  f"neu · {gleich} unverändert" + (f" · {weg} entfallen" if weg else ""))
        for w in warnungen:
            print(f"  WARNUNG {w}")
        print(f"ERGEBNIS: {'OK' if not warnungen else str(len(warnungen)) + ' Warnung(en)'}")
    return ziel, warnungen


if __name__ == "__main__":
    bauen(sys.argv[1])
