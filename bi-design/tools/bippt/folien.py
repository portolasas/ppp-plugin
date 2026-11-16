"""Folientypen (Register). Neuer Typ = Funktion mit @folientyp(name, layout) + Eintrag in reference/folientypen.md.

Jede Funktion bekommt (k, s): k = Kontext (Folie, Marke …), s = Folien-Spezifikation (dict).
Titel, Fußzeile, Band, Quelle, Notizen und Ausblenden erledigt bauen.py für alle Typen.
"""
import calendar
import datetime as dt
import math
import re

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.util import Pt

from . import vorlage
from .bausteine import (AMPEL, BAND_H, E, TOLERANZ, X0, XW, Y0, Y_ENDE, absaetze, ampel, band, bild_einpassen, bild_mass,
                        bild_pruefen,
                        flaeche, icon, inhaltsunterkante, kopfleiste, klartext, linie, pfeil, punkt, raute, text,
                        text_hoehe, textfeld, umbrechen, unterkante, wortbreiten)

TYPEN = {}


def folientyp(name, layout="nur_titel"):
    def deko(fn):
        TYPEN[name] = (fn, layout)
        return fn
    return deko


# Aufzählung im Inhaltsplatzhalter des BI-Masters, am Render gemessen (PowerPoint, 16 pt): Zeilenabstand 1,68 × Größe,
# Absatzabstand 0,09 in, Rand links mit Aufzählungszeichen 0,25 in, rechts 0,1 in. Ebenen 1–4 16 pt, ab Ebene 5 12 pt.
PH_ZEILE, PH_ABSATZ, PH_RAND = 1.68, 0.09, 0.35


def _ph_unterkante(ph, unten):
    """Platzhalter unten bis `unten` (in) kürzen, nie verlängern. Lage und Breite mitschreiben: Der Platzhalter erbt sie
    vom Layout, und nur height zu setzen legt <a:xfrm> mit Breite 0 und ohne Lage an (Text ein Buchstabe breit, bis 2.4.0)."""
    if ph is None:
        return
    links, oben, breite, hoehe = ph.left, ph.top, ph.width, ph.height
    neu = unten - oben / 914400
    if neu >= hoehe / 914400:
        return
    ph.left, ph.top, ph.width = links, oben, breite
    ph.height = E(max(neu, 0.3))


def _ph_ueberlauf(k, ph, punkte):
    """Warnung, wenn die Aufzählung über die Unterkante des Platzhalters läuft (Maße PH_*)."""
    if ph is None or not punkte or not ph.width or not ph.height:
        return
    breite = ph.width / 914400 - PH_RAND
    bedarf = 0.1 - PH_ABSATZ
    for a in absaetze(punkte):
        ebene = int(a.get("ebene", 0))
        g = 12 if ebene >= 4 else 16
        zeilen = umbrechen(re.sub(r"\*\*|==", "", str(a["t"])), breite - 0.25 * ebene, g)[0]
        bedarf += zeilen * g * PH_ZEILE / 72 + PH_ABSATZ
    platz = ph.height / 914400
    if bedarf > platz + 0.05:
        k.warn(f"Text braucht etwa {bedarf:.1f} in, Platz {platz:.1f} in – er läuft unten über (in PowerPoint unter "
               "Band bzw. Fußzeile); kürzen, weniger Punkte oder auf zwei Folien")
    elif platz >= 3 and len(absaetze(punkte)) >= 2 and bedarf < platz * 0.4:
        k.warn(f"Text füllt nur {bedarf / platz:.0%} der Fläche – die Folie wirkt leer; mehr Inhalt oder eine Bildform "
               "aus reference/bibliothek.md")


def _ph_text(ph, spec):
    """Platzhaltertext setzen, Formatierung der Vorlage bleibt (Zeilen = Absätze)."""
    if ph is None or spec is None:
        return
    zeilen = spec if isinstance(spec, list) else [spec]
    tf = ph.text_frame
    tf.text = re.sub(r"\*\*|==", "", str(zeilen[0]))
    for z in zeilen[1:]:
        p = tf.add_paragraph()
        p.text = re.sub(r"\*\*|==", "", str(z))


# ======================================================================= Titel, Kapitel, Agenda, Text
TITEL_UNTERTITEL_PLATZ = 1.85  # in, von der Oberkante des Untertitels bis zum Vertraulichkeitsvermerk
@folientyp("titel", layout="titel")
def titel(k, s):
    """Titelfolie: titel, untertitel [Zeilen]; die letzte Zeile ist „Autor | Datum | Ort“ (Ebene 2 des Masters, 16 pt).
    Fußzeile nur Vertraulichkeitsvermerk."""
    ph = vorlage.platzhalter(k.folie, idx=1)
    zeilen = s.get("untertitel")
    _ph_text(ph, zeilen)
    if ph is None or not isinstance(zeilen, list) or len(zeilen) < 2:
        return
    ph.text_frame.paragraphs[-1].level = 1
    breite = ph.width / 914400 if ph.width else 9.06
    bedarf = sum(umbrechen(re.sub(r"\*\*|==", "", str(z)), breite, 24)[0] * 24 * 1.2 / 72 + 24 / 72 for z in zeilen[:-1])
    bedarf += umbrechen(re.sub(r"\*\*|==", "", str(zeilen[-1])), breite, 16)[0] * 16 * 1.2 / 72
    if bedarf > TITEL_UNTERTITEL_PLATZ:
        k.warn(f"Untertitel braucht etwa {bedarf:.1f} in, Platz {TITEL_UNTERTITEL_PLATZ:.1f} in – er läuft in den Vertraulichkeitsvermerk; "
               "eine Zeile Untertitel und „Autor | Datum | Ort“ reichen")


@folientyp("kapitel", layout="kapitel")
def kapitel(k, s):
    """Kapiteltrenner: titel, untertitel; mit ab_hier_ausblenden als Backup-Start."""
    _ph_text(vorlage.platzhalter(k.folie, idx=14), s.get("untertitel"))


@folientyp("agenda", layout="agenda")
def agenda(k, s):
    """Agenda: punkte im Agenda-Layout des Masters."""
    ph = vorlage.platzhalter(k.folie, idx=15) or vorlage.platzhalter(k.folie, typ=("BODY", "OBJECT"))
    _ph_text(ph, s.get("punkte", []))


@folientyp("text", layout="inhalt")
def text_folie(k, s):
    """Fließtext/Aufzählung im Inhaltsplatzhalter der Vorlage (Ebenen über {"t":…, "ebene":1})."""
    ph = vorlage.platzhalter(k.folie, idx=1) or vorlage.platzhalter(k.folie, typ=("OBJECT", "BODY"))
    if ph is None:
        textfeld(k, X0, Y0, XW, inhaltsunterkante(s) - Y0, s.get("punkte", []), punkt=True, groesse=16)
        return
    if s.get("band"):
        _ph_unterkante(ph, inhaltsunterkante(s))
    _ph_ueberlauf(k, ph, s.get("punkte", []))
    tf = ph.text_frame
    erste = True
    for a in absaetze(s.get("punkte", [])):
        p = tf.paragraphs[0] if erste else tf.add_paragraph()
        erste = False
        p.text = re.sub(r"\*\*|==", "", str(a["t"]))
        p.level = int(a.get("ebene", 0))
        if "**" in str(a["t"]):
            for r in p.runs:
                r.font.bold = True
    n = sum(len(klartext(a)) for a in absaetze(s.get("punkte", [])))
    if n > 700:
        k.warn(f"{n} Zeichen Text – für eine Folie zu viel; kürzen oder aufteilen")


KERNAUSSAGE_PT = 28  # die Botschaft trägt die Folie, in 16 pt bliebe sie ein Satz auf leerer dunkler Fläche


@folientyp("kernaussage", layout="inhalt_dunkel")
def kernaussage(k, s):
    """Dunkle Botschaftsfolie: titel = Aussage, text = Unterzeile/Bitte."""
    k.dunkel = True
    ph = vorlage.platzhalter(k.folie, idx=1)
    if ph is not None:
        _ph_text(ph, s.get("text"))
        from .bausteine import _kein_punkt
        for p in ph.text_frame.paragraphs:
            _kein_punkt(p)
            for r in p.runs:
                r.font.size = Pt(KERNAUSSAGE_PT)
    elif s.get("text"):
        textfeld(k, X0, 2.2, XW, 3.5, s["text"], groesse=20, farbe="WH")


# ======================================================================= Karten (Baukasten)
STATUSFARBE = {"fertig": ("DG", "WH"), "plan": ("AG", "DG"), "aktiv": ("AG", "DG"), "klaerung": ("MYEL", "DG"),
               "offen": ("WH", "DG"), "extern": ("LG", "DG"), "kritisch": ("LRED", "DRED")}


def _blk_punkte(k, b, x, y, w, zeichnen, g):
    t = b["punkte"]
    gr = b.get("groesse", g)
    h = text_hoehe(t, w - 0.16, gr, nach=6, punkt=True) + 0.08
    if zeichnen:
        textfeld(k, x, y, w, h, [dict(a, nach=6) for a in absaetze(t, punkt=True)], groesse=gr, warn_ueberlauf=False)
    return h


def _blk_text(k, b, x, y, w, zeichnen, g):
    gr = b.get("groesse", g)
    h = text_hoehe(b["text"], w - 0.16, gr) + 0.08
    if zeichnen:
        textfeld(k, x, y, w, h, b["text"], groesse=gr, warn_ueberlauf=False)
    return h


def _blk_hinweis(k, b, x, y, w, zeichnen, g):
    hv = b["hinweis"]
    hv = hv if isinstance(hv, dict) else {"text": hv}
    t = []
    if hv.get("titel"):
        t.append({"t": hv["titel"], "fett": True, "groesse": g - 1.5, "nach": 2})
    t.append({"t": hv.get("text", ""), "groesse": g - 0.5, "fett": not hv.get("titel")})
    h = text_hoehe(t, w - 0.3, g - 0.5) + 0.2
    if zeichnen:
        flaeche(k, x, y, w, h, fill="WH", linie="DG" if hv.get("strich") else None, strich=bool(hv.get("strich")),
                t=t, anker="m", rand=(0.14, 0.06, 0.14, 0.06))
    return h


def _blk_phasen(k, b, x, y, w, zeichnen, g):
    ph = b["phasen"]
    namen, stand = ph.get("namen", []), ph.get("stand", [])
    if zeichnen and namen:
        n = len(namen)
        pw = (w - (n - 1) * 0.08) / n
        for i, nm in enumerate(namen):
            st = stand[i] if i < len(stand) else 0
            px = x + i * (pw + 0.08)
            flaeche(k, px, y + 0.04, pw, 0.08, fill={2: "DG", 1: "AG", 0: "WG"}.get(st, "WG"))
            textfeld(k, px - 0.05, y + 0.14, pw + 0.1, 0.22, {"t": nm, "ausr": "m", "fett": st == 1}, groesse=8,
                     rand=(0, 0, 0, 0), warn_ueberlauf=False)
    return 0.4


def _blk_schritte(k, b, x, y, w, zeichnen, g):
    schritte = b["schritte"]
    hs = []
    for st in schritte:
        hh = text_hoehe(st.get("titel", ""), w - 0.75, g + 0.5, nach=0) + text_hoehe(st.get("text", ""), w - 0.75, g - 1, nach=0)
        hs.append(max(0.5, hh + 0.14))
    if zeichnen:
        yy = y
        if len(schritte) > 1:
            linie(k, x + 0.2, y + 0.2, x + 0.2, y + sum(hs[:-1]) + 0.2, w=1.25)
        for i, (st, hh) in enumerate(zip(schritte, hs)):
            zustand = st.get("status", "offen")
            fill, col = {"fertig": ("DG", "AG"), "aktiv": ("AG", "DG")}.get(zustand, ("WH", "DG"))
            flaeche(k, x, yy, 0.4, 0.4, fill=fill, linie="DG", form=MSO_SHAPE.OVAL,
                    t={"t": "✓" if zustand == "fertig" else str(st.get("nr", i + 1)), "ausr": "m"},
                    groesse=12, fett=True, farbe=col, anker="m", rand=(0, 0, 0, 0))
            textfeld(k, x + 0.57, yy - 0.03, w - 0.6, 0.28, st.get("titel", ""), groesse=g + 0.5, fett=True,
                     rand=(0, 0, 0, 0), warn_ueberlauf=False)
            if st.get("text"):
                textfeld(k, x + 0.57, yy + 0.25, w - 0.6, hh - 0.25, st["text"], groesse=g - 1, rand=(0, 0, 0, 0),
                         warn_ueberlauf=False)
            yy += hh
    return sum(hs)


def _blk_von_nach(k, b, x, y, w, zeichnen, g):
    vn = b["von_nach"]
    h = vn.get("hoehe", 1.1)
    if zeichnen:
        tw = (w - 0.6) / 2
        for i, (seite, fill) in enumerate([(vn.get("von", {}), "WH"), (vn.get("nach", {}), "DG")]):
            seite = seite if isinstance(seite, dict) else {"gross": seite}
            dunkel = fill == "DG"
            t = []
            if seite.get("klein"):
                t.append({"t": seite["klein"], "groesse": 9, "ausr": "m", "farbe": "WH" if dunkel else "DG"})
            t.append({"t": seite.get("gross", ""), "groesse": 15, "fett": True, "kopf": True, "ausr": "m",
                      "farbe": "AG" if dunkel else "DG"})
            flaeche(k, x + i * (tw + 0.6), y, tw, h, fill=fill, t=t, anker="m")
        pfeil(k, x + tw + 0.13, y + h / 2 - 0.12, 0.34, 0.24)
    return h


def _blk_kennzahl(k, b, x, y, w, zeichnen, g):
    kz = b["kennzahl"]
    h = 0.95
    if zeichnen:
        textfeld(k, x, y, w, 0.55, {"t": str(kz.get("wert", "")), "kopf": True, "fett": True}, groesse=28,
                 rand=(0, 0, 0, 0), warn_ueberlauf=False)
        textfeld(k, x, y + 0.55, w, 0.35, kz.get("label", ""), groesse=g, rand=(0, 0, 0, 0), warn_ueberlauf=False)
    return h


def _blk_bild(k, b, x, y, w, zeichnen, g):
    """Bild über die Kartenbreite; Höhe nach Seitenverhältnis (höchstens 2,6 in) oder "hoehe"."""
    bl = b["bild"] if isinstance(b["bild"], dict) else {"datei": b["bild"]}
    pfad = k.pfad(bl.get("datei"))
    mass = bild_mass(pfad) if pfad else None
    if mass is None:
        if zeichnen:
            k.warn(f"Bild fehlt: {bl.get('datei')}")
        return 0
    h = bl.get("hoehe") or min(w * mass[1] / mass[0], 2.6)
    if zeichnen:
        bild_einpassen(k, pfad, x, y, w, h)
    return h


BLOECKE = {"punkte": _blk_punkte, "text": _blk_text, "hinweis": _blk_hinweis, "phasen": _blk_phasen,
           "schritte": _blk_schritte, "von_nach": _blk_von_nach, "kennzahl": _blk_kennzahl, "bild": _blk_bild}


def _bloecke(kar):
    if kar.get("inhalt"):
        return kar["inhalt"]
    out = []
    for key in ("phasen", "kennzahl", "von_nach", "bild", "punkte", "schritte", "text"):
        if kar.get(key) is not None:
            out.append({key: kar[key]})
    if kar.get("naechster"):
        out.append({"hinweis": {"titel": "Nächster Schritt", "text": kar["naechster"]}, "unten": True})
    if kar.get("hinweis"):
        out.append({"hinweis": kar["hinweis"], "unten": True})
    return out


def _blk(k, b, x, y, w, zeichnen, g):
    for key, fn in BLOECKE.items():
        if key in b:
            return fn(k, b, x, y, w, zeichnen, g)
    k.warn(f"Unbekannter Block {list(b)} – erlaubt: {', '.join(BLOECKE)}")
    return 0


def _kartenstil(kar):
    return kar.get("stil") or ("akzent" if kar.get("akzent") else ("ohne" if not kar.get("titel") else "leiste"))


def _kopf_h(stil):
    return {"leiste": 0.44 + 0.16, "akzent": 0.55}.get(stil, 0.15)


def karte_bedarf(k, kar, w, h, g=11):
    """Schriftgröße und benötigte Höhe einer Karte: Schrift wächst bis 12,5 pt, solange der Inhalt unter 60 % der
    verfügbaren Höhe h bleibt (wie bisher); Höhe = Kopf + Blöcke + Rand."""
    pad = 0.18
    iw = w - 2 * pad
    bl = _bloecke(kar)
    verfuegbar = h - _kopf_h(_kartenstil(kar)) - pad
    def summe(gg):
        return sum(_blk(k, b, 0, 0, iw, False, gg) + 0.1 for b in bl)
    while bl and g < 12.5 and summe(g + 0.5) < 0.6 * verfuegbar:
        g += 0.5
    return g, _kopf_h(_kartenstil(kar)) + summe(g) + pad


def karte(k, kar, x, y, w, h, g=11, wachsen=True):
    stil = _kartenstil(kar)
    flaeche(k, x, y, w, h, fill="WH" if kar.get("hell") else "LG", linie="WG" if kar.get("hell") else None)
    pad = 0.18
    if stil == "leiste":
        kopfleiste(k, x, y, w, kar.get("titel", ""), ampelwert=kar.get("ampel"),
                   fill="AG" if kar.get("hervor") else "DG")
        cy = y + 0.44 + 0.16
    elif stil == "akzent":
        flaeche(k, x, y, 0.07, h, fill=AMPEL.get(kar.get("akzent"), kar.get("akzent", "DG")))
        tx = x + 0.22
        if kar.get("icon"):
            icon(k, kar["icon"], x + 0.22, y + 0.15, 0.3)
            tx = x + 0.6
        textfeld(k, tx, y + 0.13, w - (tx - x) - 0.1, 0.34, kar.get("titel", ""), groesse=12, fett=True, anker="m",
                 rand=(0, 0, 0, 0))
        cy = y + 0.55
    else:
        cy = y + 0.15
    bl = _bloecke(kar)
    oben = [b for b in bl if not b.get("unten")]
    unten = [b for b in bl if b.get("unten")]
    iy, iw = x + pad, w - 2 * pad
    yb = y + h - pad + 0.02
    for b in reversed(unten):
        hh = _blk(k, b, iy, 0, iw, False, g)
        yb -= hh
        _blk(k, b, iy, yb, iw, True, g)
        yb -= 0.1
    verfuegbar = yb - cy
    while wachsen and oben and g < 12.5 and \
            sum(_blk(k, b, iy, 0, iw, False, g + 0.5) + 0.1 for b in oben) < 0.6 * verfuegbar:
        g += 0.5
    yy = cy
    for b in oben:
        hh = _blk(k, b, iy, yy, iw, False, g)
        if yy + hh > yb + 0.3:
            k.warn(f"Karte „{kar.get('titel', '')}“: Inhalt passt nicht ({yy + hh - yb:.2f} in zu hoch) – kürzen")
        _blk(k, b, iy, yy, iw, True, g)
        yy += hh + 0.1


def karten_reihe(k, karten, x, y, w, h, abstand=0.22, g=11, hoehe="voll"):
    """Karten nebeneinander. hoehe voll = bis zur Unterkante; inhalt = alle so hoch wie die vollste Karte
    (gleiche Höhe in der Reihe, Rest bleibt frei). Gibt die gezeichnete Höhe zurück."""
    n = max(1, len(karten))
    cw = (w - abstand * (n - 1)) / n
    bedarf = [karte_bedarf(k, kar, cw, h, kar.get("groesse", g)) for kar in karten]
    hh = h if hoehe == "voll" else min(h, max([b for _, b in bedarf] or [h]))
    for i, (kar, (gg, _)) in enumerate(zip(karten, bedarf)):
        karte(k, kar, x + i * (cw + abstand), y, cw, hh, g=gg, wachsen=False)
    return hh


@folientyp("karten")
def karten(k, s):
    """2–4 Karten nebeneinander (Kopfleiste mit Ampel oder Akzentstreifen mit Icon) mit Blöcken."""
    unten = inhaltsunterkante(s)
    y = Y0 - 0.25
    if s.get("kopf"):
        y += _kopfband(k, s["kopf"], y) + 0.18
    kk = s.get("karten", [])
    h = unten - y
    karten_reihe(k, kk, X0, y, XW, h, g=s.get("groesse", 11), hoehe=s.get("hoehe", "inhalt"))
    if kk and h >= 2:
        cw = (XW - 0.22 * (len(kk) - 1)) / len(kk)
        voll = max(karte_bedarf(k, kar, cw, h, kar.get("groesse", s.get("groesse", 11)))[1] for kar in kk) / h
        if voll < 0.4:
            k.warn(f"Karten füllen nur {voll:.0%} der Fläche – mehr Inhalt, Icons oder eine Folie mit Fazit-Band "
                   "(Bibliothek 36–38)")


def _kopfband(k, spec, y):
    """Band oben (z. B. „Zu entscheiden:“); gibt seine Höhe zurück."""
    from .bausteine import band, band_hoehe
    band(k, spec, y=y, groesse=11.5)
    return band_hoehe(spec, 11.5)


@folientyp("status")
def status(k, s):
    """Status je Strang: Ampel, Phasenfortschritt, Punkte, nächster Schritt + Legende."""
    phasen = s.get("phasen", [])
    kk = []
    for st in s.get("straenge", []):
        inhalt = []
        if phasen:
            inhalt.append({"phasen": {"namen": phasen, "stand": st.get("stand", [])}})
        if st.get("punkte"):
            inhalt.append({"punkte": st["punkte"]})
        if st.get("naechster"):
            inhalt.append({"hinweis": {"titel": "Nächster Schritt", "text": st["naechster"]}, "unten": True})
        kk.append({"titel": st.get("titel", ""), "ampel": st.get("ampel"), "inhalt": inhalt})
    unten = inhaltsunterkante(s)
    leg = s.get("legende", {"G": "im Plan", "Y": "beobachten / Freigabe ausstehend", "R": "Eskalation"})
    lh = 0.34 if leg else 0
    y = Y0 - 0.25
    karten_reihe(k, kk, X0, y, XW, unten - y - lh, g=s.get("groesse", 11))
    if leg:
        lx = X0 + 0.05
        for wert, lab in leg.items():
            ampel(k, lx, unten - 0.22, 0.14, wert, rand=None)
            textfeld(k, lx + 0.2, unten - 0.29, 3.0, 0.28, lab, groesse=9, rand=(0, 0, 0, 0), anker="m",
                     warn_ueberlauf=False)
            lx += 0.55 + len(lab) * 0.07


# ======================================================================= Vergleich
@folientyp("vergleich")
def vergleich(k, s):
    """Tabelle alt → neu mit Pfeilspalte. zeilen: [thema, alt, neu]; Ampelzelle: {"ampel": ["Y","G"], "labels": ["A","B"]}."""
    sp = s.get("spalten", ["Thema", "Vorher", "Jetzt"])
    zeilen = s.get("zeilen", [])
    unten = inhaltsunterkante(s)
    y = Y0 - 0.25
    w0 = XW * 0.19
    w1 = XW * 0.35
    wp = 0.4
    w2 = XW - w0 - w1 - wp
    xs = [X0, X0 + w0, X0 + w0 + w1, X0 + w0 + w1 + wp]
    kh = 0.38
    flaeche(k, X0, y, XW, kh, fill="DG")
    for x, w, lab, col in [(xs[0], w0, sp[0], "WH"), (xs[1], w1, sp[1], "WH"), (xs[3], w2, sp[2], "AG")]:
        textfeld(k, x, y, w, kh, lab, groesse=10.5, fett=True, farbe=col, anker="m", rand=(0.1, 0, 0.1, 0),
                 warn_ueberlauf=False)
    g = s.get("groesse", 10.5)
    while True:
        hs = []
        for z in zeilen:
            hh = 0.4
            for txt, ww, gg in [(z[0], w0, g), (z[1], w1, g - 0.5), (z[2] if len(z) > 2 else "", w2, g)]:
                if isinstance(txt, str):
                    hh = max(hh, text_hoehe(txt, ww - 0.2, gg, nach=0) + 0.14)
            hs.append(hh)
        if y + kh + sum(hs) <= unten - 0.05 or g <= 8.5:
            break
        g -= 0.5
    if y + kh + sum(hs) > unten:
        k.warn("Vergleich: zu viele/lange Zeilen – kürzen oder auf zwei Folien teilen")
    elif zeilen:
        frei_h = (unten - 0.05 - y - kh - sum(hs)) / len(zeilen)
        hs = [min(max(h, h + frei_h), 0.8) for h in hs]
        if min(hs) >= 0.6 and g < 11.5:
            g += 1
    yy = y + kh
    for i, (z, rh) in enumerate(zip(zeilen, hs)):
        if i % 2 == 0:
            flaeche(k, X0, yy, XW, rh, fill="LG")
        textfeld(k, xs[0], yy, w0, rh, z[0], groesse=g, fett=True, anker="m", rand=(0.1, 0, 0.05, 0),
                 warn_ueberlauf=False)
        for x, ww, zelle, fett, gg in [(xs[1], w1, z[1], False, g - 0.5), (xs[3], w2, z[2] if len(z) > 2 else "", True, g)]:
            if isinstance(zelle, dict) and "ampel" in zelle:
                labs = zelle.get("labels", [])
                for j, wert in enumerate(zelle["ampel"]):
                    cx = x + 0.12 + j * 0.5
                    ampel(k, cx, yy + rh / 2 - 0.08, 0.16, wert, rand=None)
                    if j < len(labs):
                        textfeld(k, cx + 0.18, yy, 0.3, rh, labs[j], groesse=9, anker="m", rand=(0.02, 0, 0, 0),
                                 warn_ueberlauf=False)
            else:
                textfeld(k, x, yy, ww, rh, zelle, groesse=gg, fett=fett, anker="m", rand=(0.1, 0, 0.1, 0),
                         warn_ueberlauf=False)
        pfeil(k, xs[2] + 0.09, yy + rh / 2 - 0.09, 0.22, 0.18)
        yy += rh


# ======================================================================= Prozess
@folientyp("prozess")
def prozess(k, s):
    """Prozesskette mit Icons; optional Kopfband, gestrichelter Hinweis und Karten darunter."""
    unten = inhaltsunterkante(s)
    y = Y0 - 0.25
    if s.get("kopf"):
        y += _kopfband(k, s["kopf"], y) + 0.2
    schritte = s.get("schritte", [])
    n = max(1, len(schritte))
    if any(st.get("punkte") or st.get("ueber") for st in schritte):
        gap = 0.3
        sw = (XW - gap * (n - 1)) / n
        _spalten_rat(k, sw, gap, [(st.get("ueber"), 9, False, 0.24) for st in schritte] +
                     [(st.get("titel"), s.get("kopf_groesse", 11.5), True, 0.24) for st in schritte] +
                     [(a["t"], a.get("groesse", s.get("groesse", 10.5)), a.get("fett", False), 0.57 + 0.17 * a.get("ebene", 0))
                      for st in schritte for a in absaetze(st.get("punkte"), punkt=True)] +
                     [(st.get("text"), s.get("groesse", 10.5), False, 0.4) for st in schritte if not st.get("punkte")])
        y += _schrittkarten(k, schritte, y, sw, gap, unten - y if not s.get("karten") else None,
                            g=s.get("groesse", 10.5), gk=s.get("kopf_groesse", 11.5)) + 0.22
    else:
        gap = 0.45
        sw = (XW - gap * (n - 1)) / n
        gt = s.get("groesse", 9.5)
        _spalten_rat(k, sw, gap, [(st.get("titel"), 11.5, True, 0.12) for st in schritte] +
                     [(st.get("text"), gt, False, 0.16) for st in schritte])
        th = max(text_hoehe(st.get("text", ""), sw - 0.16, gt, nach=0) for st in schritte) if schritte else 0.3
        sh = max(1.5, 1.0 + th + 0.1)
        for i, st in enumerate(schritte):
            x = X0 + i * (sw + gap)
            fill, farbe = STATUSFARBE.get(st.get("status"), ("LG", "DG"))
            flaeche(k, x, y, sw, sh, fill=fill)
            flaeche(k, x, y, sw, 0.06, fill="AG" if fill == "DG" else "DG")
            if st.get("icon"):
                icon(k, st["icon"], x + sw / 2 - 0.21, y + 0.18, 0.42, variante="white" if fill == "DG" else None)
            textfeld(k, x + 0.06, y + 0.66, sw - 0.12, 0.3, {"t": st.get("titel", ""), "ausr": "m"}, groesse=11.5,
                     fett=True, farbe=farbe, rand=(0, 0, 0, 0))
            if st.get("text"):
                textfeld(k, x + 0.08, y + 0.97, sw - 0.16, sh - 1.0, {"t": st["text"], "ausr": "m"}, groesse=gt,
                         farbe=farbe, rand=(0, 0, 0, 0))
            if i < n - 1:
                pfeil(k, x + sw + 0.085, y + sh / 2 - 0.11)
        y += sh + 0.14
    if s.get("hinweis"):
        ab = s.get("hinweis_ab", 0)
        hx = X0 + ab * (sw + gap)
        flaeche(k, hx, y, X0 + XW - hx, 0.46, fill="WH", linie="DG", strich=True, t=s["hinweis"], groesse=10,
                anker="m", rand=(0.15, 0, 0.15, 0))
        y += 0.46 + 0.2
    if s.get("karten"):
        karten_reihe(k, s["karten"], X0, y, XW, unten - y, abstand=0.2, g=10.5, hoehe=s.get("hoehe", "voll"))


def _spalten_rat(k, sw, gap, texte):
    """Rat zur Wortbreiten-Warnung (bausteine.Kontext.wortbreite_melden), wenn ein Wort nicht in die Spaltenbreite sw
    passt: wie viele Spalten nebeneinander gehen. texte = [(Text, Schriftgröße, fett, Rand + Einzug in der Spalte)]."""
    noetig = max([b + rand for t, g, fett, rand in texte if t for a in absaetze(t)
                  for _, b in wortbreiten(a.get("t", ""), g, fett)] or [0])
    if noetig > sw + TOLERANZ:
        n = max(1, int((XW + gap) / (noetig + gap)))
        k.tipp_wortbreite = (f"höchstens {n} Schritte nebeneinander (Spalte {sw:.2f} in, das breiteste Wort braucht "
                             f"{noetig:.2f} in), auf zwei Folien teilen oder kleinere Schrift (groesse, kopf_groesse)")


# Kopf der Schrittkarten je Status: (Füllung, Schrift); ohne Status Dunkelgrün wie im Referenzdeck
SCHRITTKOPF = {None: ("DG", "WH"), "fertig": ("DG", "WH"), "aktiv": ("AG", "DG"), "plan": ("WG", "DG"),
               "offen": ("WG", "DG"), "klaerung": ("MYEL", "DG"), "extern": ("LG", "DG"), "kritisch": ("RED", "DG")}


def _schrittkarten(k, schritte, y, sw, gap, voll_h=None, g=10.5, gk=11.5):
    """Schritte als Karten: Kopf (Überzeile klein, Titel fett) in Statusfarbe, darunter Punkte oder Text;
    Pfeile zwischen den Köpfen. voll_h = bis zur Unterkante strecken, sonst so hoch wie der vollste Schritt.
    g = Schriftgröße des Inhalts, gk = des Titels im Kopf."""
    ueber = 0.2 if any(st.get("ueber") for st in schritte) else 0
    kh = max(0.46, ueber + max(text_hoehe(st.get("titel", ""), sw - 0.26, gk, zeilenabstand=1.0, nach=0)
                               for st in schritte) + 0.14)
    inhalt = []
    for st in schritte:
        b = {"punkte": st["punkte"]} if st.get("punkte") else ({"text": st["text"]} if st.get("text") else None)
        inhalt.append(b)
    bh = max([_blk(k, b, 0, 0, sw - 0.3, False, g) for b in inhalt if b] or [0.3]) + 0.3
    if voll_h:
        bh = max(bh, voll_h - kh)
    for i, (st, b) in enumerate(zip(schritte, inhalt)):
        x = X0 + i * (sw + gap)
        fill, farbe = SCHRITTKOPF.get(st.get("status"), SCHRITTKOPF[None])
        flaeche(k, x, y + kh, sw, bh, fill="LG")
        t = []
        if st.get("ueber"):
            t.append({"t": st["ueber"], "groesse": 9, "nach": 1})
        t.append({"t": st.get("titel", ""), "groesse": gk, "fett": True})
        flaeche(k, x, y, sw, kh, fill=fill, t=t, farbe=farbe, anker="m", rand=(0.14, 0.04, 0.1, 0.04), nach=0)
        if b:
            _blk(k, b, x + 0.12, y + kh + 0.14, sw - 0.24, True, g)
        if i < len(schritte) - 1:
            pfeil(k, x + sw + (gap - 0.2) / 2, y + kh / 2 - 0.09, 0.2, 0.18)
    return kh + bh


# ======================================================================= Datenfluss
@folientyp("fluss")
def fluss(k, s):
    """Datenfluss in Spalten: spalten [{titel, boxen [{titel, text, klein, stil hell|weiss|dunkel|akzent}]}].
    Boxen einer Spalte liegen in Zeilen; eine Spalte mit einer Box spannt über alle Zeilen. Pfeile je Zeile."""
    spalten = s.get("spalten", [])
    if not spalten:
        k.warn("fluss: keine spalten")
        return
    unten = inhaltsunterkante(s)
    y = Y0 - 0.2
    n = len(spalten)
    gap = 0.42
    sw = (XW - gap * (n - 1)) / n
    zeilen = max(len(sp.get("boxen", [])) for sp in spalten)
    kopf = 0.32 if any(sp.get("titel") for sp in spalten) else 0
    oben = y + kopf
    zh_gap = 0.18
    zh = (unten - oben - zh_gap * (zeilen - 1)) / max(1, zeilen)
    stile = {"hell": ("LG", "DG"), "weiss": ("WH", "DG"), "dunkel": ("DG", "WH"), "akzent": ("AG", "DG")}
    lagen = []  # je Spalte: [(y, h)] der Boxen
    for i, sp in enumerate(spalten):
        x = X0 + i * (sw + gap)
        if sp.get("titel"):
            textfeld(k, x, y, sw, 0.28, sp["titel"], groesse=10.5, fett=True, farbe="G7", rand=(0, 0, 0, 0),
                     warn_ueberlauf=False)
        boxen = sp.get("boxen", [])
        if len(boxen) == 1 and zeilen > 1:
            pos = [(oben, unten - oben)]
        else:
            pos = [(oben + j * (zh + zh_gap), zh) for j in range(len(boxen))]
        lagen.append(pos)
        for bx, (by, bh) in zip(boxen, pos):
            fill, farbe = stile.get(bx.get("stil", "hell"), stile["hell"])
            t = [{"t": bx.get("titel", ""), "fett": True, "groesse": 12.5 if len(pos) == 1 else 11.5, "ausr": "m", "nach": 3}]
            if bx.get("text"):
                t.append({"t": bx["text"], "groesse": 11, "ausr": "m", "nach": 3})
            if bx.get("klein"):
                t.append({"t": bx["klein"], "groesse": 9.5, "kursiv": True, "ausr": "m"})
            flaeche(k, x, by, sw, bh, fill=fill, linie="WG" if fill == "WH" else None, t=t, farbe=farbe,
                    hervor="AG" if fill == "DG" else None, anker="m", rand=(0.12, 0.06, 0.12, 0.06))
            if text_hoehe(t, sw - 0.24, 11) > bh + 0.1:
                k.warn(f"fluss: Box „{bx.get('titel', '')}“ zu voll – kürzen")
    for i in range(n - 1):
        xa = X0 + i * (sw + gap) + sw
        links, rechts = lagen[i], lagen[i + 1]
        mitten = [by + bh / 2 for by, bh in (links if len(links) >= len(rechts) else rechts)]
        for cy in mitten:
            pfeil(k, xa + (gap - 0.26) / 2, cy - 0.1, 0.26, 0.2)


# ======================================================================= Timeline (Gantt)
def _datum(v, ende=False):
    if isinstance(v, dt.date):
        return v
    v = str(v).strip()
    m = re.fullmatch(r"(\d{4})-W(\d{1,2})", v) or re.fullmatch(r"KW\s*(\d{1,2})/(\d{4})", v)
    if m:
        a, b = m.groups()
        jahr, kw = (int(a), int(b)) if len(a) == 4 else (int(b), int(a))
        d = dt.date.fromisocalendar(jahr, kw, 1)
        return d + dt.timedelta(days=6) if ende else d
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", v)
    if m:
        j, mo = int(m.group(1)), int(m.group(2))
        return dt.date(j, mo, calendar.monthrange(j, mo)[1]) if ende else dt.date(j, mo, 1)
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", v)
    if m:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return dt.date.fromisoformat(v)


MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


class _Skala:
    def __init__(self, von, bis, art, x0, x1):
        self.art, self.x0, self.x1 = art, x0, x1
        self.spalten = []  # (start, ende, label, jahr)
        if art == "woche":
            d = von - dt.timedelta(days=von.weekday())
            while d <= bis:
                j, w, _ = d.isocalendar()
                self.spalten.append((d, d + dt.timedelta(days=7), f"KW {w}", j))
                d += dt.timedelta(days=7)
        elif art == "quartal":
            d = dt.date(von.year, 3 * ((von.month - 1) // 3) + 1, 1)
            while d <= bis:
                n = dt.date(d.year + (d.month + 2) // 12, (d.month + 2) % 12 + 1, 1)
                self.spalten.append((d, n, f"Q{(d.month - 1) // 3 + 1}", d.year))
                d = n
        else:
            d = dt.date(von.year, von.month, 1)
            while d <= bis:
                n = dt.date(d.year + d.month // 12, d.month % 12 + 1, 1)
                self.spalten.append((d, n, MONATE[d.month - 1], d.year))
                d = n
        self.sw = (x1 - x0) / len(self.spalten)

    def x(self, d):
        d = _datum(d)
        if d < self.spalten[0][0]:
            return self.x0
        for i, (a, b, _, _) in enumerate(self.spalten):
            if a <= d < b:
                return self.x0 + (i + (d - a).days / (b - a).days) * self.sw
        return self.x1


def _breite(txt, g, fett=True):
    return len(txt) * g * (0.56 if fett else 0.52) / 72 + 0.08


@folientyp("timeline")
def timeline(k, s):
    """Gantt in Kalenderwochen, Monaten oder Quartalen mit Balken, Meilensteinen, Heute-Linie, Markern, Legende, Fakten."""
    zeilen = s.get("zeilen", [])
    alle = [e for z in zeilen for e in z.get("elemente", [])]
    daten = [_datum(e[f]) for e in alle for f in ("von", "bis", "datum") if e.get(f)]
    von = _datum(s["von"]) if s.get("von") else min(daten)
    bis = _datum(s["bis"], ende=True) if s.get("bis") else max(daten)
    tage = (bis - von).days
    art = s.get("skala") or ("woche" if tage <= 190 else ("monat" if tage <= 548 else "quartal"))
    lx0 = X0
    cx0 = X0 + (s.get("beschriftung_breite") or (3.0 if art == "woche" else 2.1))
    cx1 = X0 + XW
    sk = _Skala(von, bis, art, cx0, cx1)
    unten = inhaltsunterkante(s)
    ty = Y0 - 0.2
    # Jahreskopf
    jahre = []
    for a, b, lab, j in sk.spalten:
        if not jahre or jahre[-1][0] != j:
            jahre.append([j, a, b])
        else:
            jahre[-1][2] = b
    for i, (j, a, b) in enumerate(jahre):
        xa = cx0 + [c[0] for c in sk.spalten].index(a) * sk.sw
        xb = cx0 + ([c[1] for c in sk.spalten].index(b) + 1) * sk.sw
        flaeche(k, xa, ty, xb - xa, 0.3, fill="DG", t={"t": str(j), "ausr": "m"}, groesse=10, fett=True, anker="m",
                rand=(0, 0, 0, 0))
        if i > 0:
            linie(k, xa, ty, xa, ty + 0.3, farbe="WH", w=1.5)
    for i, (a, b, lab, j) in enumerate(sk.spalten):
        flaeche(k, cx0 + i * sk.sw, ty + 0.3, sk.sw, 0.24, fill="LG" if i % 2 == 0 else "WG", t={"t": lab, "ausr": "m"},
                groesse=7.5 if art == "woche" else 8.5, anker="m", rand=(0, 0, 0, 0))
    grid_top = ty + 0.54
    rows_y = grid_top + 0.06
    # Platz für Legende und Fakten
    unten_raster = unten
    leg_h = 0.32 if s.get("legende", True) else 0
    fakten = s.get("fakten")
    boxen = s.get("boxen")
    f_h = 0
    if fakten:
        f_h = text_hoehe(fakten.get("punkte", []), XW - 0.4, 10, nach=2, punkt=True) + 0.45
    elif boxen:
        f_h = max(text_hoehe(b.get("text", ""), XW / len(boxen) - 0.4, 10) for b in boxen) + 0.55
    verf = unten_raster - leg_h - (f_h + 0.12 if f_h else 0) - rows_y
    rh = max(0.32, min(0.6, verf / max(1, len(zeilen))))
    if rh * len(zeilen) > verf + 0.01:
        k.warn("Timeline: zu viele Zeilen für den Platz – Zeilen zusammenfassen oder Fakten kürzen")
    grid_bot = rows_y + rh * len(zeilen)
    for i, z in enumerate(zeilen):
        yy = rows_y + i * rh
        flaeche(k, lx0, yy + 0.03, cx1 - lx0, rh - 0.06, fill="LG" if i % 2 == 0 else "WH")
        textfeld(k, lx0, yy, cx0 - lx0 - 0.05, rh, z.get("titel", ""), groesse=s.get("groesse", 10 if art == "woche" else 10.5),
                 fett=art != "woche", anker="m", rand=(0.08, 0, 0, 0), warn_ueberlauf=False)
    for sch in s.get("schatten", []):
        xa, xb = sk.x(_datum(sch["von"])), sk.x(_datum(sch["bis"], ende=True))
        flaeche(k, xa, grid_top, xb - xa, grid_bot - grid_top, fill="WG")
        if sch.get("text"):
            textfeld(k, xa - 0.3, grid_bot + 0.01, xb - xa + 0.6, 0.2, {"t": sch["text"], "ausr": "m"}, groesse=8,
                     rand=(0, 0, 0, 0), warn_ueberlauf=False)
    for i in range(len(sk.spalten) + 1):
        linie(k, cx0 + i * sk.sw, grid_top, cx0 + i * sk.sw, grid_bot, farbe="WG", w=0.5)
    # Hindernisse für Beschriftungen: Heute-/Markerlinien
    linien_x = []
    heute = s.get("heute", k.heute)
    if heute:
        linien_x.append(sk.x(_datum(heute)))
    for mk in s.get("marker", []):
        linien_x.append(sk.x(_datum(mk["datum"])))
    belegt = {}
    benutzt = set()

    def frei(row, x, w, yy, hh, linien=True):
        for r in (row - 1, row, row + 1):  # Beschriftungen über und unter dem Balken reichen in die Nachbarzeile
            for (a, b, c, d) in belegt.get(r, []):
                if x < b and x + w > a and yy < d and yy + hh > c:
                    return False
        if x < cx0 - 0.02 or x + w > cx1 + 0.02:
            return False
        return not linien or all(not (x + 0.02 < lx < x + w - 0.02) for lx in linien_x)

    def belegen(row, x, w, yy, hh):
        belegt.setdefault(row, []).append((x, x + w, yy, yy + hh))

    def label(row, x_anker_l, x_anker_r, cy, txt, pos, g=8.5):
        w = _breite(txt, g)
        # je Lage: x, Oberkante des Textfelds, Ausrichtung, Oberkante und Höhe des sichtbaren Textes
        mitte = (x_anker_l + x_anker_r) / 2 - w / 2
        kand = {"rechts": (x_anker_r + 0.06, cy - 0.12, "l", cy - 0.12, 0.24), "links": (x_anker_l - 0.06 - w, cy - 0.12, "r", cy - 0.12, 0.24),
                "oben": (mitte, cy - 0.32, "m", cy - 0.27, 0.14), "unten": (mitte, cy + 0.08, "m", cy + 0.13, 0.14)}
        reihenfolge = [pos] + [p for p in ("rechts", "links", "oben", "unten") if p != pos] if pos else \
            ["rechts", "links", "oben", "unten"]
        # 1. Durchgang: frei von Labels/Elementen und Linien; 2.: Linien (Heute/Marker) dürfen gekreuzt werden
        wahl = next((p for linien in (True, False) for p in reihenfolge
                     if frei(row, kand[p][0], w, kand[p][3], kand[p][4], linien)), None)
        if wahl is None:
            wahl = reihenfolge[0]
            k.warn(f"Timeline: Beschriftung „{txt}“ überlappt – pos setzen oder kürzen")
        lx, ly, au, sy, sh = kand[wahl]
        lx = max(X0, min(lx, X0 + XW - w))  # nie über den Folienrand
        belegen(row, lx, w, sy, sh)
        textfeld(k, lx, ly, w, 0.24, {"t": txt, "ausr": au}, groesse=g if wahl in ("rechts", "links") else 7.5,
                 fett=True, anker="m", rand=(0, 0, 0, 0), warn_ueberlauf=False, umbruch=False)

    # Erst alle Balken und Rauten belegen, dann beschriften: Sonst landet eine Beschriftung unter dem nächsten Balken derselben Zeile.
    for ri, z in enumerate(zeilen):
        cy = rows_y + ri * rh + rh / 2
        for e in z.get("elemente", []):
            art_e = e.get("art", "balken" if e.get("von") else "meilenstein")
            if art_e == "balken":
                xa, xb = sk.x(_datum(e["von"])), sk.x(_datum(e["bis"], ende=True))
                belegen(ri, xa, xb - xa, cy - 0.13, 0.26)
            elif art_e != "ueberbrueckung":
                xm = sk.x(_datum(e["datum"]))
                belegen(ri, xm - 0.1, 0.2, cy - 0.1, 0.2)
    for ri, z in enumerate(zeilen):
        cy = rows_y + ri * rh + rh / 2
        for e in z.get("elemente", []):
            art_e = e.get("art", "balken" if e.get("von") else "meilenstein")
            st = e.get("status", "plan")
            fill, tcol = STATUSFARBE.get(st, ("AG", "DG"))
            benutzt.add((art_e, st))
            if art_e == "balken":
                xa, xb = sk.x(_datum(e["von"])), sk.x(_datum(e["bis"], ende=True))
                bh = 0.26
                strich = st in ("extern", "offen")
                flaeche(k, xa, cy - bh / 2, max(xb - xa, 0.04), bh, fill=fill, linie="DG" if strich else None,
                        strich=st == "extern")
                txt = e.get("text", "")
                if txt:
                    passt = [g for g in (8.5, 7.5) if _breite(txt, g, fett=False) + 0.06 <= xb - xa]
                    if passt and not e.get("pos"):
                        textfeld(k, xa, cy - bh / 2, xb - xa, bh, {"t": txt, "ausr": "m"}, groesse=passt[0], farbe=tcol,
                                 anker="m", rand=(0.02, 0, 0.02, 0), warn_ueberlauf=False, umbruch=False)
                    else:
                        label(ri, xa, xb, cy, txt, e.get("pos") or "oben")
            elif art_e == "ueberbrueckung":
                xa, xb = sk.x(_datum(e["von"])), sk.x(_datum(e["bis"], ende=True))
                flaeche(k, xa, cy + rh / 2 - 0.1, xb - xa, 0.06, fill="MRED")
            else:  # meilenstein
                xm = sk.x(_datum(e["datum"]))
                raute(k, xm, cy, 0.2, fill)
                if e.get("text"):
                    label(ri, xm - 0.1, xm + 0.1, cy, e["text"], e.get("pos"))
    # Heute und Marker
    kopf_belegt = []
    for mk in s.get("marker", []):
        xm = sk.x(_datum(mk["datum"]))
        linie(k, xm, grid_top - 0.05, xm, grid_bot, w=1.75)
        if mk.get("text"):
            w = _breite(mk["text"], 8)
            textfeld(k, xm - w, ty - 0.24, w, 0.22, {"t": mk["text"], "ausr": "r"}, groesse=8, fett=True,
                     rand=(0, 0, 0.03, 0), warn_ueberlauf=False, umbruch=False)
            kopf_belegt.append((xm - w, xm))
    if heute:
        xh = sk.x(_datum(heute))
        linie(k, xh, grid_top - 0.05, xh, grid_bot, w=1.25, strich=True)
        lab = s.get("heute_text") or f"Heute {_datum(heute):%d.%m.}"
        w = _breite(lab, 8)
        x = xh - w / 2
        if any(x < b and x + w > a for a, b in kopf_belegt):
            x = xh + 0.03
        textfeld(k, x, ty - 0.24, w, 0.22, {"t": lab, "ausr": "m"}, groesse=8, fett=True, rand=(0, 0, 0, 0),
                 warn_ueberlauf=False, umbruch=False)
    # Legende
    y = grid_bot + 0.12
    if s.get("legende", True):
        namen = {"fertig": "abgeschlossen", "plan": "Arbeitspaket", "aktiv": "in Arbeit", "klaerung": "in Klärung / Freigabe",
                 "offen": "offen", "extern": "Abhängigkeit / out of scope", "kritisch": "kritisch"}
        eintr = []
        for st in ("fertig", "plan", "aktiv", "klaerung", "offen", "extern", "kritisch"):
            if ("balken", st) in benutzt:
                eintr.append(("balken", st, namen[st]))
        if any(a == "ueberbrueckung" for a, _ in benutzt):
            eintr.append(("ueberbrueckung", "kritisch", "Überbrückung"))
        if any(a == "meilenstein" for a, _ in benutzt):
            eintr.append(("meilenstein", "plan", "Meilenstein"))
        lx = cx0
        for art_e, st, lab in eintr:
            fill = STATUSFARBE[st][0]
            if art_e == "meilenstein":
                raute(k, lx + 0.12, y + 0.11, 0.16, fill)
            elif art_e == "ueberbrueckung":
                flaeche(k, lx, y + 0.08, 0.28, 0.06, fill="MRED")
            else:
                flaeche(k, lx, y + 0.03, 0.28, 0.16, fill=fill, linie="DG" if st in ("extern", "offen") else None,
                        strich=st == "extern")
            textfeld(k, lx + 0.34, y - 0.02, _breite(lab, 8.5, fett=False), 0.26, lab, groesse=8.5, anker="m",
                     rand=(0, 0, 0, 0), warn_ueberlauf=False, umbruch=False)
            lx += 0.55 + len(lab) * 0.068
        y += leg_h
    if fakten:
        t = [{"t": fakten.get("titel", "Key Facts"), "fett": True, "groesse": 11, "nach": 4}] + \
            [{"t": p, "punkt": True, "nach": 2} for p in fakten.get("punkte", [])]
        flaeche(k, X0, y, XW, unten - y, fill="LG", t=t, groesse=10, rand=(0.2, 0.08, 0.2, 0.05))
    elif boxen:
        bw = (XW - 0.2 * (len(boxen) - 1)) / len(boxen)
        for i, b in enumerate(boxen):
            t = [{"t": b.get("titel", ""), "fett": True, "groesse": 11, "nach": 4}, {"t": b.get("text", ""), "groesse": 10}]
            flaeche(k, X0 + i * (bw + 0.2), y, bw, unten - y, fill="LG", t=t, rand=(0.2, 0.1, 0.2, 0.05))


# ======================================================================= Maßnahmen, Tabelle, Kennzahlen
@folientyp("massnahmen")
def massnahmen(k, s):
    """Nächste Schritte: [{wann, was, details, tag}] – Termin links dunkel, Tag rechts als Chip."""
    unten = inhaltsunterkante(s)
    rows = s.get("zeilen", [])
    y0 = Y0 - 0.25
    ww, wa, wt = 2.3, 3.5, 0.8
    wd = XW - ww - wa - wt - 0.35
    g = s.get("groesse", 10.5)
    hs = [max(0.42, text_hoehe(r.get("details", ""), wd - 0.1, g, nach=0) + 0.18,
              text_hoehe(r.get("was", ""), wa - 0.1, g + 0.5, nach=0) + 0.18) for r in rows]
    gap = 0.06
    if y0 + sum(hs) + gap * len(rows) > unten:
        k.warn("Maßnahmen: zu viele Zeilen – max. ca. 8, Rest ins Backup")
    elif rows:
        frei_h = (unten - 0.1 - y0 - sum(hs) - gap * len(rows)) / len(rows)
        hs = [min(h + frei_h, 0.8) for h in hs]
    yy = y0
    for i, (r, rh) in enumerate(zip(rows, hs)):
        if i % 2 == 0:
            flaeche(k, X0, yy, XW, rh, fill="LG")
        flaeche(k, X0, yy, ww, rh, fill="DG", t=r.get("wann", ""), groesse=g, fett=True, anker="m",
                rand=(0.15, 0, 0.1, 0))
        textfeld(k, X0 + ww + 0.15, yy, wa, rh, r.get("was", ""), groesse=g + 0.5, fett=True, anker="m",
                 rand=(0.05, 0, 0.05, 0), warn_ueberlauf=False)
        textfeld(k, X0 + ww + wa + 0.2, yy, wd, rh, r.get("details", ""), groesse=g, anker="m",
                 rand=(0.05, 0, 0.05, 0), warn_ueberlauf=False)
        if r.get("tag"):
            flaeche(k, X0 + XW - wt - 0.1, yy + rh / 2 - 0.14, wt, 0.28, fill="WG", t={"t": r["tag"], "ausr": "m"},
                    groesse=9, fett=True, anker="m", rand=(0, 0, 0, 0))
        yy += rh + gap


def _rahmen(zelle, farbe, w=0.75):
    """Zellrahmen setzen – lnL/lnR/lnT/lnB müssen im Schema vor der Füllung stehen (sonst Reparaturmeldung)."""
    tcPr = zelle._tc.get_or_add_tcPr()
    for i, tag in enumerate(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):
        for el in tcPr.findall(qn(tag)):
            tcPr.remove(el)
        ln = tcPr.makeelement(qn(tag), {"w": str(int(w * 12700)), "cap": "flat", "cmpd": "sng", "algn": "ctr"})
        sf = ln.makeelement(qn("a:solidFill"), {})
        sf.append(sf.makeelement(qn("a:srgbClr"), {"val": farbe}))
        ln.append(sf)
        tcPr.insert(i, ln)


def _zelle_hoehe(wert, breite, g, fett):
    """Höhe (in), auf die PowerPoint eine Tabellenzelle wachsen lässt: Ränder 0,08 + Zeilen × 1,32 × g (Zeilenabstand
    1,1; die erste Zeile 0,05 × g weniger) + 3 pt je weiterem Absatz – am Render mit PowerPoint kalibriert (9–12 pt)."""
    if isinstance(wert, dict) and "ampel" in wert:
        wert = "● " + str(wert.get("t", ""))
    abs_ = absaetze(wert if wert is not None else "") or [{"t": ""}]
    zeilen = sum(umbrechen(a.get("t", ""), breite - 0.16 - (0.17 * (1 + a.get("ebene", 0)) if a.get("punkt") else 0),
                           a.get("groesse", g), a.get("fett", fett))[0] for a in abs_)
    return 0.08 + (1.32 * zeilen - 0.05) * g / 72 + 3 / 72 * (len(abs_) - 1)


@folientyp("tabelle")
def tabelle(k, s):
    """Echte PowerPoint-Tabelle: kopf, zeilen, breiten (relativ), groesse; Zelle {"ampel": "G", "t": "…"} möglich.
    Zeilenhöhen nach Inhalt: Ohne groesse wird die Schrift bis 9 pt kleiner, bis alle Zeilen über Band, Quelle bzw.
    Fußzeile passen; sonst eine Warnung mit Bedarf und Platz."""
    kopf, zeilen = s.get("kopf", []), s.get("zeilen", [])
    n_sp = max([len(kopf)] + [len(z) for z in zeilen]) if (kopf or zeilen) else 1
    unten = inhaltsunterkante(s)
    y = Y0 - 0.2
    platz = unten - y
    n_z = len(zeilen) + (1 if kopf else 0)
    br = s.get("breiten") or [1] * n_sp
    gesamt = sum(br)
    spalten = [XW * b / gesamt for b in br]
    alle = ([kopf] if kopf else []) + zeilen
    erste_fett = s.get("erste_spalte_fett", True)

    def bedarf(g):
        return [max(_zelle_hoehe(z[j] if j < len(z) else "", spalten[j], g, (bool(kopf) and i == 0) or (j == 0 and erste_fett))
                    for j in range(min(n_sp, len(spalten)))) for i, z in enumerate(alle)]

    fest = s.get("groesse")
    g = fest or (12 if n_z <= 6 else 11 if n_z <= 9 else 10 if n_z <= 12 else 9)
    hs = bedarf(g)
    while not fest and sum(hs) > platz and g > 9:
        g -= 0.5
        hs = bedarf(g)
    ziel = min(0.6, platz / max(1, n_z))  # Luft wie bisher, höchstens 0,6 in je Zeile
    rh = [max(h, ziel) for h in hs]
    if sum(rh) > platz:  # einzelne hohe Zeilen: übrigen Platz gleichmäßig verteilen
        rh = [h + max(0.0, platz - sum(hs)) / max(1, n_z) for h in hs]
    if sum(hs) > platz + 0.02:
        bis, unter = (("zum Band", "unter dem Band") if s.get("band") else
                      ("zur Quellenzeile", "auf der Quellenzeile") if s.get("quelle") else ("zur Fußzeile", "auf der Fußzeile"))
        passt = [x / 2 for x in range(int(g * 2) - 1, 17, -1) if sum(bedarf(x / 2)) <= platz] if fest else []
        rat = (f"groesse {passt[0]:g} (statt {g:g}) passt" if passt else
               "Zeilen kürzen oder zusammenfassen, Spalten breiter (breiten) oder auf zwei Folien teilen")
        k.warn(f"Tabelle: {n_z} Zeilen brauchen bei {g:g} pt ca. {sum(hs):.2f} in, Platz bis {bis} {platz:.2f} in – "
               f"die letzten Zeilen lägen {unter}. Abhilfe: {rat}")
    tbl_shape = k.folie.shapes.add_table(n_z, n_sp, E(X0), E(y), E(XW), E(sum(rh) if rh else 0.4))
    tbl = tbl_shape.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("bandRow", "0")
    tblPr.set("firstRow", "1" if kopf else "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is not None:
        sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # „Kein Stil, kein Raster“
    for j, b in enumerate(spalten):
        tbl.columns[j].width = E(b)
    for r, h in zip(tbl.rows, rh):
        r.height = E(h)
    from pptx.enum.text import MSO_ANCHOR
    for i, z in enumerate(alle):
        ist_kopf = bool(kopf) and i == 0
        for j in range(n_sp):
            zelle = tbl.cell(i, j)
            wert = z[j] if j < len(z) else ""
            zelle.fill.solid()
            zelle.fill.fore_color.rgb = RGBColor.from_string(k.c("DG") if ist_kopf else (k.c("LG") if (i % 2 == (0 if kopf else 1)) else k.c("WH")))
            zelle.margin_left = zelle.margin_right = E(0.08)
            zelle.margin_top = zelle.margin_bottom = E(0.04)
            zelle.vertical_anchor = MSO_ANCHOR.MIDDLE
            sb = spalten[j] if j < len(spalten) else None
            if isinstance(wert, dict) and "ampel" in wert:
                t = [{"t": [("● ", {}), (str(wert.get("t", "")), {})]}]
                text(k, zelle.text_frame, t, groesse=g, rand=(0.08, 0.04, 0.08, 0.04), breite=sb)
                zelle.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor.from_string(k.c(AMPEL.get(wert["ampel"], "WG")))
            else:
                fett = ist_kopf or (j == 0 and erste_fett)
                text(k, zelle.text_frame, wert if wert is not None else "", groesse=g, fett=fett,
                     farbe="WH" if ist_kopf else "DG", hervor="AG" if ist_kopf else None, rand=(0.08, 0.04, 0.08, 0.04),
                     breite=sb)
            _rahmen(zelle, k.c("WG"))


@folientyp("kennzahlen")
def kennzahlen(k, s):
    """Kacheln: [{wert, label, text, ampel, icon, bild}] – 2 bis 8 Stück, 2 bis 4 je Reihe."""
    kz = s.get("kacheln", [])
    n = len(kz)
    proReihe = s.get("spalten") or (n if n <= 4 else math.ceil(n / 2))
    reihen = math.ceil(n / max(1, proReihe))
    unten = inhaltsunterkante(s)
    y0 = Y0 - 0.2
    gap = 0.22
    kw = (XW - gap * (proReihe - 1)) / proReihe
    kh = min((unten - y0 - gap * (reihen - 1)) / reihen, s.get("kachel_hoehe", 2.6))
    for i, t in enumerate(kz):
        x = X0 + (i % proReihe) * (kw + gap)
        y = y0 + (i // proReihe) * (kh + gap)
        flaeche(k, x, y, kw, kh, fill="LG")
        flaeche(k, x, y, kw, 0.07, fill=AMPEL.get(t.get("ampel"), "DG"))
        if t.get("icon"):
            icon(k, t["icon"], x + kw - 0.55, y + 0.25, 0.32)
        textfeld(k, x + 0.2, y + 0.22, kw - 0.4, 0.7, {"t": str(t.get("wert", "")), "kopf": True}, groesse=s.get("wert_groesse", 32),
                 fett=True, rand=(0, 0, 0, 0), warn_ueberlauf=False)
        textfeld(k, x + 0.2, y + 0.95, kw - 0.4, 0.35, t.get("label", ""), groesse=12, fett=True, rand=(0, 0, 0, 0))
        ty = y + 1.32
        if t.get("text"):
            th = text_hoehe(t["text"], kw - 0.4, 10.5) + 0.05 if t.get("bild") else kh - 1.4
            textfeld(k, x + 0.2, ty, kw - 0.4, th, t["text"], groesse=10.5, rand=(0, 0, 0, 0))
            ty += th + 0.1
        if t.get("bild"):
            bild_einpassen(k, k.pfad(t["bild"]), x + 0.2, ty, kw - 0.4, y + kh - 0.18 - ty)


# ======================================================================= Bild, Diagramm, Frei
@folientyp("bild_text", layout="inhalt_bild")
def bild_text(k, s):
    """Bild im Bildplatzhalter + punkte im Textplatzhalter (bild = Pfad)."""
    # Mit Band oder Quelle enden Bild und Text darüber; das Layout reicht sonst bis 6,5 in (unter das Band)
    unten = inhaltsunterkante(s) if s.get("band") or s.get("quelle") else None
    ph = vorlage.platzhalter(k.folie, idx=10)
    tx = vorlage.platzhalter(k.folie, idx=1)
    if unten is not None:
        _ph_unterkante(ph, unten)  # vor insert_picture: der Zuschnitt richtet sich nach dem Rahmen
        _ph_unterkante(tx, unten)
    bild = k.pfad(s.get("bild"))
    if bild and bild.is_file():
        if ph is not None:
            lage = ph.left, ph.top, ph.width, ph.height
            pic = ph.insert_picture(str(bild))
            if unten is not None:  # das neue p:pic erbt sonst wieder die Lage aus dem Layout
                pic.left, pic.top, pic.width, pic.height = lage
            bild_pruefen(k, bild, pic)
        else:
            bild_pruefen(k, bild, k.folie.shapes.add_picture(str(bild), E(X0 + XW * 0.38), E(Y0), width=E(XW * 0.62)))
    else:
        k.warn(f"Bild fehlt: {s.get('bild')}")
    if tx is not None:
        _ph_text(tx, [klartext(a) for a in absaetze(s.get("punkte", []))] or [""])
        _ph_ueberlauf(k, tx, s.get("punkte", []))
    elif s.get("punkte"):
        textfeld(k, X0, Y0, XW * 0.35, 4.5, s["punkte"], punkt=True, groesse=14)


@folientyp("layout")
def layout_folie(k, s):
    """Beliebiges Layout des Masters (`layout`: Name aus `bippt layouts`): felder {idx: Text | [Absätze]}, bilder {idx: Pfad}."""
    k.dunkel = k.dunkel or "dark" in k.folie.slide_layout.name
    unten = inhaltsunterkante(s) if s.get("band") else None
    for idx, wert in (s.get("felder") or {}).items():
        ph = vorlage.platzhalter(k.folie, idx=int(idx))
        if ph is None or not getattr(ph, "has_text_frame", False):
            k.warn(f"Layout „{k.folie.slide_layout.name}“ hat kein Textfeld {idx} (bippt layouts)")
            continue
        if unten is not None:
            _ph_unterkante(ph, unten)
        punkte = wert if isinstance(wert, list) else [wert]
        erste = True
        for a in absaetze(punkte):
            p = ph.text_frame.paragraphs[0] if erste else ph.text_frame.add_paragraph()
            erste = False
            p.text = re.sub(r"\*\*|==", "", str(a["t"]))
            p.level = int(a.get("ebene", 0))
            if "**" in str(a["t"]):
                for r in p.runs:
                    r.font.bold = True
        if "OBJECT" in str(ph.placeholder_format.type):  # Fließtext des Masters; Key-Message-Felder haben andere Maße
            _ph_ueberlauf(k, ph, punkte)
    for idx, datei in (s.get("bilder") or {}).items():
        ph = vorlage.platzhalter(k.folie, idx=int(idx))
        bild = k.pfad(datei)
        if ph is None or not hasattr(ph, "insert_picture"):
            k.warn(f"Layout „{k.folie.slide_layout.name}“ hat keinen Bildplatzhalter {idx} (bippt layouts)")
        elif not bild or not bild.is_file():
            k.warn(f"Bild fehlt: {datei}")
        else:
            if unten is not None:
                _ph_unterkante(ph, unten)
            lage = ph.left, ph.top, ph.width, ph.height
            pic = ph.insert_picture(str(bild))
            if unten is not None:
                pic.left, pic.top, pic.width, pic.height = lage
            bild_pruefen(k, bild, pic)
    frei_bild = [str(ph.placeholder_format.idx) for ph in k.folie.placeholders if hasattr(ph, "insert_picture")]
    if frei_bild:
        k.warn(f"Bildplatzhalter {', '.join(frei_bild)} leer – Bild angeben oder ein Layout ohne Bild nehmen")


DIAGRAMM = {"saeulen": XL_CHART_TYPE.COLUMN_CLUSTERED, "gestapelt": XL_CHART_TYPE.COLUMN_STACKED,
            "balken": XL_CHART_TYPE.BAR_CLUSTERED, "linie": XL_CHART_TYPE.LINE_MARKERS, "torte": XL_CHART_TYPE.DOUGHNUT}
LINIEN_AUF_WEISS = ["DG", "DBLU", "DVIO", "DRED", "MRED", "DYEL"]
# „Automatic diagram color sequence“ des BI-Masters v2.1 (Designfarben Akzent 1–6), danach dunkle Custom Colors
DIAGRAMM_FOLGE = ["DG", "AG", "VIO", "YEL", "RED", "BLU", "DBLU", "DVIO", "DRED", "DYEL"]


@folientyp("diagramm")
def diagramm(k, s):
    """Echtes Diagramm (editierbar): art saeulen|gestapelt|balken|linie|torte, kategorien, reihen [{name, werte}]."""
    unten = inhaltsunterkante(s)
    y = Y0 - 0.15
    w = XW
    if s.get("fazit"):
        w = XW * 0.64
        fx = X0 + w + 0.25
        karte(k, {"titel": s["fazit"].get("titel", "Fazit"), "stil": "akzent", "akzent": "DG",
                  "icon": s["fazit"].get("icon"), "punkte": s["fazit"].get("punkte", [])},
              fx, y, X0 + XW - fx, unten - y, g=11)
    cd = CategoryChartData()
    cd.categories = s.get("kategorien", [])
    for r in s.get("reihen", []):
        cd.add_series(r.get("name", ""), r.get("werte", []))
    art = s.get("art", "saeulen")
    gf = k.folie.shapes.add_chart(DIAGRAMM.get(art, XL_CHART_TYPE.COLUMN_CLUSTERED), E(X0), E(y), E(w), E(unten - y), cd)
    ch = gf.chart
    ch.font.size = Pt(11)
    ch.font.name = k.text
    ch.font.color.rgb = RGBColor.from_string(k.c("DG"))
    n_r = len(s.get("reihen", []))
    ch.has_legend = n_r > 1 or art == "torte"
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.BOTTOM
        ch.legend.include_in_layout = False
    folge = [k.c(c) for c in (LINIEN_AUF_WEISS if art == "linie" else DIAGRAMM_FOLGE)]
    plot = ch.plots[0]
    if s.get("werte_anzeigen"):
        plot.has_data_labels = True
        plot.data_labels.font.size = Pt(10)
    if art == "torte":
        for i, pt in enumerate(plot.series[0].points):
            pt.format.fill.solid()
            pt.format.fill.fore_color.rgb = RGBColor.from_string(folge[i % len(folge)])
    else:
        for i, ser in enumerate(plot.series):
            col = RGBColor.from_string(folge[i % len(folge)])
            if art == "linie":
                ser.format.line.color.rgb = col
                ser.format.line.width = Pt(2.25)
                ser.smooth = False
            else:
                ser.format.fill.solid()
                ser.format.fill.fore_color.rgb = col
        try:
            va = ch.value_axis
            va.has_major_gridlines = True
            va.major_gridlines.format.line.color.rgb = RGBColor.from_string(k.c("WG"))
            va.format.line.fill.background()
            ch.category_axis.format.line.color.rgb = RGBColor.from_string(k.c("WG"))
        except (AttributeError, ValueError):
            pass


@folientyp("frei")
def frei(k, s):
    """Eigene Elemente ohne Code: elemente = [{form: flaeche|text|linie|icon|punkt|pfeil|karte|band|bild, …}]."""
    for el in s.get("elemente", []):
        f = el.get("form")
        if f == "flaeche":
            flaeche(k, el["x"], el["y"], el["w"], el["h"], fill=el.get("fill"), linie=el.get("linie"),
                    strich=el.get("strich", False), t=el.get("t"), groesse=el.get("groesse", 12),
                    fett=el.get("fett", False), anker=el.get("anker", "m"), ausr=el.get("ausr", "l"))
        elif f == "text":
            textfeld(k, el["x"], el["y"], el["w"], el["h"], el.get("t", ""), groesse=el.get("groesse", 12),
                     fett=el.get("fett", False), punkt=el.get("punkt", False), farbe=el.get("farbe", "DG"),
                     ausr=el.get("ausr", "l"), anker=el.get("anker", "o"))
        elif f == "linie":
            linie(k, el["x1"], el["y1"], el["x2"], el["y2"], farbe=el.get("farbe", "DG"), w=el.get("w", 1),
                  strich=el.get("strich", False))
        elif f == "icon":
            icon(k, el["name"], el["x"], el["y"], el.get("d", 0.4), variante=el.get("variante"))
        elif f == "punkt":
            punkt(k, el["x"], el["y"], el.get("d", 0.2), el.get("fill", "AG"), rand=el.get("rand"))
        elif f == "pfeil":
            pfeil(k, el["x"], el["y"], el.get("w", 0.28), el.get("h", 0.22), fill=el.get("fill", "DG"))
        elif f == "karte":
            karte(k, el, el["x"], el["y"], el["w"], el["h"], g=el.get("groesse", 11))
        elif f == "band":
            band(k, el, y=el.get("y"), h=el.get("h"), unten=unterkante(s))
        elif f == "bild":
            bild_einpassen(k, k.pfad(el.get("datei")), el["x"], el["y"], el["w"], el["h"], ausr=el.get("ausr", "m"))
        else:
            k.warn(f"frei: unbekannte Form {f}")


@folientyp("abschluss", layout="abschluss")
def abschluss(k, s):
    """Abschlussfolie (BI-Master „One content dark Outro“), z. B. „Vielen Dank“ – nur Titel."""
    k.dunkel = True
