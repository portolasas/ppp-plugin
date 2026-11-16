"""Brand-Prüfung einer PPTX (ohne PowerPoint): Farben, Schriften, Kontrast, Überlauf, Titelzeilen, Ränder, Textmenge,
Vorlage.

Stufen: FEHLER (muss weg) · WARNUNG (prüfen) · HINWEIS. Ausgabe endet mit „ERGEBNIS: OK“ oder „ERGEBNIS: n Fehler“.
Farben nach dem BI-Master v2.1 (How-to slides, Folie 6): nur Theme Colors und Custom Colors, keine Abstufungen darunter
(lumMod/lumOff/tint/shade) und keine Standardfarben. Formstile (p:style) zählen nicht, sie füllen nichts sichtbar.
"""
import re

from lxml import etree
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Emu

from . import vorlage
from .bausteine import text_hoehe
from .formen import alle, meldung
from .marke import Marke

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
HELL = {"FFFFFF", "F6F5F3", "E5E3DE", "FBF9AA", "FFE667", "D2F2F7", "A3E5EE", "F5CDB9", "E0E1F6", "C5C3EE"}
SCHRIFT_OK = re.compile(r"^(Boehringer Forward.*|Segoe UI.*|\+mj-.*|\+mn-.*|Arial|Symbol|Wingdings.*)$")


def _theme_farben(prs):
    farben = set()
    try:
        for m in prs.slide_masters:
            th = m.part.part_related_by(RT.THEME)
            x = etree.fromstring(th.blob)
            for el in x.iter(A + "srgbClr"):
                farben.add(el.get("val").upper())
            for el in x.iter(A + "sysClr"):
                farben.add((el.get("lastClr") or "").upper())
    except KeyError:
        pass
    return farben


def _fuellung(sh):
    try:
        if sh.fill.type == 1:  # solid
            return str(sh.fill.fore_color.rgb)
    except (AttributeError, TypeError, ValueError):
        pass
    return None


def _untergrund(formen, i):
    """Füllung der obersten gefüllten Form unter dem Mittelpunkt von formen[i] (transparente Textfelder)."""
    sh = formen[i]
    if sh.left is None or sh.width is None:
        return None
    cx, cy = sh.left + sh.width / 2, sh.top + sh.height / 2
    for u in reversed(formen[:i]):
        if u.left is None or u.width is None:
            continue
        if u.left <= cx <= u.left + u.width and u.top <= cy <= u.top + u.height:
            f = _fuellung(u)
            if f:
                return f
    return None


def _hintergrund(sl):
    """Einfarbiger Hintergrund der Folie (sonst des Layouts, sonst des Masters) als RGB, None wenn unbekannt."""
    for teil in (sl, sl.slide_layout, sl.slide_layout.slide_master):
        bg = teil._element.find(f"{P}cSld/{P}bg")
        if bg is None:
            continue
        el = bg.find(f"{P}bgPr/{A}solidFill/*")
        if el is None or len(el):  # Verlauf, Bild, Formstil oder abgestuft: nicht sicher
            return None
        if el.tag == A + "srgbClr":
            return el.get("val", "").upper()
        if el.tag == A + "schemeClr":
            return vorlage.themafarben(sl).get(vorlage.THEMA.get(el.get("val"), el.get("val")))
        return None
    return None


ABSTUFUNG = {A + t for t in ("lumMod", "lumOff", "tint", "shade")}
GRAU_BASIS = {"bg1", "tx1", "lt1", "dk1"}  # Weiß/Schwarz abgestuft = Grau: nur Hinweis auf Gray 1–8


def _abstufungen(el):
    """(Designfarbe, grau?) je abgestufter Farbe außerhalb von Formstilen."""
    out = []
    for c in el.iter(A + "schemeClr", A + "srgbClr"):
        if any(ch.tag in ABSTUFUNG for ch in c):
            anc = c.getparent()
            while anc is not None and anc.tag.split("}")[-1] != "style":
                anc = anc.getparent()
            if anc is None:
                out.append((c.get("val", ""), c.get("val", "") in GRAU_BASIS))
    return out


def pruefen(pfad, profil=None, theme_farben_erlauben=True, woerter=170):
    prs = vorlage.oeffnen(pfad)
    m = Marke(profil)
    erlaubt = m.erlaubte_farben() | ({"000000", "FFFFFF"})
    theme = _theme_farben(prs)
    befunde = []

    def b(stufe, nr, text):
        befunde.append((stufe, nr, text))

    if not vorlage.ist_bi_master(prs):
        b("FEHLER", 0, "Präsentation nutzt nicht den BI-Master – umwandeln (bippt umwandeln)")
    sw, sh_ = Emu(prs.slide_width).inches, Emu(prs.slide_height).inches
    if abs(sw / sh_ - 16 / 9) > 0.02:
        b("WARNUNG", 0, f"Format {sw:.2f}×{sh_:.2f} in ist nicht 16:9")
    for nr, sl in enumerate(prs.slides, 1):
        if sl._element.get("show") == "0":
            sichtbar = False
        else:
            sichtbar = True
        fremd, schriften, worte, stufen = {}, set(), 0, {}
        hat_titel = sl.shapes.title is not None and sl.shapes.title.has_text_frame and sl.shapes.title.text_frame.text.strip()
        if not hat_titel and sl.slide_layout.name not in ("Title slide (bright)", "Title slide (dark)", "Empty"):
            b("HINWEIS", nr, "keine Titelzeile (Navigation/Barrierefreiheit)")
        if hat_titel:
            try:
                zu_lang = vorlage.titel_pruefen(sl)
            except (AttributeError, KeyError, ValueError, TypeError):  # fremde Decks: Prüfung nie abbrechen
                zu_lang = None
            if zu_lang:
                b("WARNUNG", nr, zu_lang)
        grund = _hintergrund(sl)
        unbekannt = []
        formen = list(alle(sl.shapes, unbekannt))
        for u in unbekannt:
            b("HINWEIS", nr, meldung(u))
        for i_sh, sh in enumerate(formen):
            x = sh._element
            for el in x.iter(A + "srgbClr"):
                v = el.get("val", "").upper()
                if v not in erlaubt and not (theme_farben_erlauben and v in theme):
                    fremd[v] = fremd.get(v, 0) + 1
            for val, grau in _abstufungen(x):
                stufen[(val, grau)] = stufen.get((val, grau), 0) + 1
            for el in x.iter(A + "latin"):
                tf = el.get("typeface", "")
                if tf and not SCHRIFT_OK.match(tf):
                    schriften.add(tf)
            if sh.left is not None and sh.width is not None:
                l, t, w, h = (Emu(v).inches for v in (sh.left, sh.top, sh.width, sh.height))
                if l < -0.05 or t < -0.05 or l + w > sw + 0.05 or t + h > sh_ + 0.05:
                    b("WARNUNG", nr, f"„{sh.name}“ ragt über den Folienrand")
            if not sh.has_text_frame or not sh.text_frame.text.strip():
                continue
            kp = sh._element.find(".//" + A + "bodyPr")
            ziffer = kp is not None and kp.get("wrap") == "none" and len(sh.text_frame.text.strip()) <= 4  # Ziffer im Kreis
            if sh.width is not None and Emu(sh.width).inches < 0.3 and not ziffer:  # z. B. Breite 0 aus bippt bis 2.4.0
                b("FEHLER", nr, f"Textfeld „{sh.name}“ ist {Emu(sh.width).inches:.2f} in breit – Text steht einen "
                                "Buchstaben je Zeile")
            fill = _fuellung(sh) or _untergrund(formen, i_sh) or grund
            gr_max = 0
            for p in sh.text_frame.paragraphs:
                for r in p.runs:
                    worte += len(r.text.split())
                    g = r.font.size.pt if r.font.size else None
                    if g:
                        gr_max = max(gr_max, g)
                        if g < 7.5 and r.text.strip():
                            b("WARNUNG", nr, f"Schrift {g:g} pt zu klein: „{r.text.strip()[:30]}“")
                    try:
                        col = str(r.font.color.rgb) if r.font.color and r.font.color.type is not None else None
                    except AttributeError:
                        col = None
                    if col == m.c("AG") and (fill is None or fill in HELL):
                        b("FEHLER", nr, f"Akzentgrün-Text auf hellem Grund (1,7:1): „{r.text.strip()[:30]}“")
                    if col in ("E18600",) and (fill is None or fill in HELL):
                        b("WARNUNG", nr, f"Dunkelgelb-Text auf Weiß (2,8:1): „{r.text.strip()[:30]}“")
            # Überlaufschätzung nur für Formen mit fester Größe und gesetzten Schriftgrößen
            if not sh.is_placeholder and gr_max and sh.width and sh.height and sh.text_frame.auto_size in (None, 0):
                tf = sh.text_frame
                def _m(v, std):
                    return Emu(std if v is None else v).inches
                ml = _m(tf.margin_left, 91440) + _m(tf.margin_right, 91440)
                mt = _m(tf.margin_top, 45720) + _m(tf.margin_bottom, 45720)
                abs_ = [{"t": "".join(r.text for r in p.runs), "groesse": (p.runs[0].font.size.pt if p.runs and p.runs[0].font.size else gr_max),
                         "nach": (p.space_after.pt if p.space_after is not None else 0)} for p in tf.paragraphs]
                bedarf = text_hoehe(abs_, Emu(sh.width).inches - ml, gr_max, nach=0) + mt
                if bedarf > Emu(sh.height).inches * 1.25 + 0.1:
                    b("WARNUNG", nr, f"Text in „{sh.name}“ läuft vermutlich über ({bedarf:.2f} > {Emu(sh.height).inches:.2f} in)")
        if fremd:
            liste = ", ".join(f"#{k} ({v}×)" for k, v in sorted(fremd.items(), key=lambda kv: -kv[1])[:6])
            b("FEHLER", nr, f"Farben außerhalb der Marke: {liste}")
        farbig = {v: n for (v, g), n in stufen.items() if not g}
        if farbig:
            b("FEHLER", nr, "Abstufungen von Designfarben (im Master nicht erlaubt, nur Theme/Custom Colors): "
              + ", ".join(f"{v} ({n}×)" for v, n in sorted(farbig.items())))
        grau = sum(n for (v, g), n in stufen.items() if g)
        if grau:
            b("HINWEIS", nr, f"{grau}× Weiß/Schwarz abgestuft – besser Gray 1–8 aus den Custom Colors")
        if schriften:
            b("FEHLER", nr, f"Fremde Schriften: {', '.join(sorted(schriften))}")
        if sichtbar and worte > woerter:
            b("WARNUNG", nr, f"{worte} Wörter – überladen? (Grenze {woerter}; Steering ≤ 120, Projektteam ≤ 200; "
              "Details ins Backup)")
    return befunde


def bericht(pfad, profil=None, woerter=170):
    befunde = pruefen(pfad, profil, woerter=woerter)
    fehler = sum(1 for s, _, _ in befunde if s == "FEHLER")
    print(f"PRÜFUNG {pfad}")
    for s, nr, t in sorted(befunde, key=lambda x: (x[1], x[0])):
        print(f"  {s:8} {'Deck' if nr == 0 else 'Folie ' + str(nr)}: {t}")
    w = sum(1 for s, _, _ in befunde if s == "WARNUNG")
    print(f"ERGEBNIS: {'OK' if not fehler else str(fehler) + ' Fehler'}{f' · {w} Warnung(en)' if w else ''}")
    return fehler
