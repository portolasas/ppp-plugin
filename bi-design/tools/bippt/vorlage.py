"""Vorlage (BI-Master) öffnen, Layouts finden, Fußzeile/Foliennummer/Quelle setzen, Vorlage extrahieren."""
import copy
import re
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Emu

# Kurzname → Layoutname im BI-Master (englische Fassung). Weitere Vorlagen: Namen hier ergänzen.
LAYOUTS = {
    "titel": ["Title slide (bright)"],
    "titel_dunkel": ["Title slide (dark)"],
    "titel_bild": ["Title slide image (small)"],
    "agenda": ["Agenda"],
    "kapitel": ["Chapter divider (1)"],
    "kapitel_dunkel": ["Chapter divider (2)"],
    "inhalt": ["One content"],
    "inhalt_dunkel": ["One content dark"],
    "zwei_inhalte": ["Two contents"],
    "drei_inhalte": ["Three contents"],
    "inhalt_bild": ["Content and image"],
    "nur_titel": ["Only title"],
    "leer": ["Empty"],
    "abschluss": ["One content dark Outro"],
    "disclaimer": ["Disclaimer"],
    "kontakt": ["Contact"],
}
DUNKLE_LAYOUTS = {"titel_dunkel", "kapitel_dunkel", "inhalt_dunkel", "abschluss"}
THEMA = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}  # Farbzuordnung des Masters (Standard)


def oeffnen(pfad=None):
    """Vorlage/Basis öffnen. Ohne Pfad: leere 16:9-Präsentation (Notbetrieb ohne BI-Master)."""
    if pfad is None:
        prs = Presentation()
        prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
        return prs
    p = Path(pfad)
    if p.suffix.lower() in (".potx", ".pptm", ".potm"):
        return _als_pptx(p)
    return Presentation(str(p))


def _als_pptx(p):
    """.potx/.pptm lassen sich mit python-pptx nur über den Content-Type öffnen."""
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(p) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = re.sub(rb"application/vnd\.ms-powerpoint\.(template|presentation)\.macroEnabled\.main\+xml|"
                              rb"application/vnd\.openxmlformats-officedocument\.presentationml\.template\.main\+xml",
                              b"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml", data)
            zout.writestr(item, data)
    buf.seek(0)
    return Presentation(buf)


def themafarben(folie):
    """Designfarben des Masters der Folie: {"accent1": "08312A", "lt1": "FFFFFF", …}."""
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    try:
        x = etree.fromstring(folie.slide_layout.slide_master.part.part_related_by(RT.THEME).blob)
    except KeyError:
        return {}
    out = {}
    for el in x.iter(a + "clrScheme"):
        for c in el:
            f = c[0] if len(c) else None
            if f is not None:
                out[c.tag.split("}")[-1]] = (f.get("val") if f.tag == a + "srgbClr" else f.get("lastClr", "")).upper()
    return out


def ist_bi_master(prs):
    namen = {l.name for l in prs.slide_layouts}
    return "Only title" in namen and "Title slide (bright)" in namen


def layout(prs, kurz):
    namen = LAYOUTS.get(kurz, [kurz])
    for l in prs.slide_layouts:
        if l.name in namen:
            return l
    # Ersatz nach Struktur (fremde Vorlage / Notbetrieb)
    ersatz = {"titel": 0, "titel_dunkel": 0, "titel_bild": 0, "kapitel": 2, "kapitel_dunkel": 2, "agenda": 1,
              "inhalt": 1, "inhalt_dunkel": 1, "zwei_inhalte": 3, "drei_inhalte": 3, "inhalt_bild": 8,
              "nur_titel": 5, "leer": 6, "abschluss": 1, "disclaimer": 6, "kontakt": 1}
    i = ersatz.get(kurz, 5)
    return prs.slide_layouts[min(i, len(prs.slide_layouts) - 1)]


def platzhalter(folie, typ=None, idx=None):
    for ph in folie.placeholders:
        pf = ph.placeholder_format
        if idx is not None and pf.idx == idx:
            return ph
        if typ is not None and str(pf.type).split(".")[-1].split(" ")[0] in typ:
            return ph
    return None


def _layout_ph(folie, phtyp):
    for sp in folie.slide_layout.placeholders:
        el = sp._element.find(".//" + qn("p:ph"))
        if el is not None and el.get("type") == phtyp:
            return sp
    return None


def _hat_ph(folie, phtyp):
    for sp in folie.shapes._spTree.iter(qn("p:ph")):
        if sp.get("type") == phtyp:
            return True
    return False


def _ph_anlegen(folie, layout_sp, inhalt_xml):
    """Platzhalter vom Layout übernehmen (Position erbt), Text ersetzen."""
    sp = copy.deepcopy(layout_sp._element)
    spPr = sp.find(qn("p:spPr"))
    for ch in list(spPr):
        spPr.remove(ch)
    tx = sp.find(qn("p:txBody"))
    for p in tx.findall(qn("a:p")):
        tx.remove(p)
    lst = tx.find(qn("a:lstStyle"))
    if lst is not None:
        for ch in list(lst):
            lst.remove(ch)
    tx.append(etree.fromstring(inhalt_xml))
    ids = [int(x.get("id")) for x in folie.shapes._spTree.iter(qn("p:cNvPr")) if x.get("id", "").isdigit()]
    sp.find(".//" + qn("p:cNvPr")).set("id", str(max(ids + [1]) + 1))
    folie.shapes._spTree.append(sp)
    return sp


_A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def fusszeile(folie, text, nummer=True):
    """Fußzeile und Foliennummer wie im Master setzen (python-pptx legt sie bei neuen Folien nicht an)."""
    if text is not None:
        vorhanden = [ph for ph in folie.placeholders if ph._element.find(".//" + qn("p:ph")).get("type") == "ftr"]
        if vorhanden:
            tf = vorhanden[0].text_frame
            tf.text = text
        else:
            lsp = _layout_ph(folie, "ftr")
            if lsp is not None:
                t = (text.replace("&", "&amp;").replace("<", "&lt;"))
                _ph_anlegen(folie, lsp, f'<a:p {_A}><a:r><a:rPr lang="de-DE"/><a:t>{t}</a:t></a:r></a:p>')
    if nummer and not _hat_ph(folie, "sldNum"):
        lsp = _layout_ph(folie, "sldNum")
        if lsp is not None:
            _ph_anlegen(folie, lsp, f'<a:p {_A}><a:fld id="{{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}}" '
                                    f'type="slidenum"><a:rPr lang="de-DE"/><a:t>‹#›</a:t></a:fld></a:p>')


def quelle(folie, text):
    """Quellen-/Hinweiszeile (BI-Master: Textplatzhalter idx 13 unten)."""
    ph = platzhalter(folie, idx=13)
    if ph is not None and text:
        ph.text_frame.text = text
    return ph is not None


def _kette(ph):
    """Platzhalter der Folie, dann des Layouts und des Masters, von denen er erbt."""
    kette = [ph]
    while len(kette) < 3:
        try:
            basis = kette[-1]._base_placeholder
        except (AttributeError, KeyError, NotImplementedError, ValueError):
            basis = None
        if basis is None:
            break
        kette.append(basis)
    return kette


def _erster(werte, std):
    return next((w for w in werte if w is not None), std)


def titel_format(folie):
    """Titel mit Maßen für die Zeilenschätzung, geerbt wie in PowerPoint (Lauf → Platzhalter von Folie, Layout und
    Master → titleStyle des Masters), oder None ohne Titel. Längen in Zoll."""
    t = folie.shapes.title
    if t is None or not t.has_text_frame or not t.text_frame.text.strip() or t.width is None or t.top is None:
        return None
    kette = _kette(t)
    stil = folie.slide_layout.slide_master._element.find(f"{qn('p:txStyles')}/{qn('p:titleStyle')}")
    ebene1 = [ph._element.find(f"{qn('p:txBody')}/{qn('a:lstStyle')}/{qn('a:lvl1pPr')}") for ph in kette]
    ebene1 = [x for x in ebene1 + [stil.find(qn("a:lvl1pPr")) if stil is not None else None] if x is not None]
    absatz1 = t.text_frame.paragraphs[0]._p.find(qn("a:pPr"))
    zeichen = [r._r.find(qn("a:rPr")) for p in t.text_frame.paragraphs for r in p.runs]
    zeichen = [x for x in zeichen if x is not None] + [x.find(qn("a:defRPr")) for x in ebene1]
    zeichen = [x for x in zeichen if x is not None]
    abstand = [x.find(f"{qn('a:lnSpc')}/{qn('a:spcPct')}") for x in [absatz1] + ebene1 if x is not None]
    body = [ph._element.find(f"{qn('p:txBody')}/{qn('a:bodyPr')}") for ph in kette]
    body = [x for x in body if x is not None]
    passen = next((c.tag for x in body for c in x
                   if c.tag in (qn("a:noAutofit"), qn("a:normAutofit"), qn("a:spAutoFit"))), None)

    def rand(attr, std):
        return int(_erster([x.get(attr) for x in body], std)) / 914400

    return {"form": t, "absaetze": [p.text for p in t.text_frame.paragraphs], "links": t.left / 914400,
            "oben": t.top / 914400, "breite": t.width / 914400, "hoehe": t.height / 914400,
            "rand_l": rand("lIns", 91440), "rand_r": rand("rIns", 91440), "rand_o": rand("tIns", 45720),
            "rand_u": rand("bIns", 45720),
            "groesse": int(_erster([x.get("sz") for x in zeichen], 1800)) / 100,
            "fett": _erster([x.get("b") for x in zeichen], "0") in ("1", "true"),
            "zeile": int(_erster([x.get("val") for x in abstand if x is not None], 100000)) / 100000,
            "anker": _erster([x.get("anchor") for x in body], "t"), "verkleinern": passen == qn("a:normAutofit")}


def _ueber(folie, f):
    """(Oberkante, Unterkante) der Formen über dem Titelrahmen, die ihn waagrecht überlappen – auf der Folie, im Layout
    und im Master (z. B. das Logo der Titelfolie)."""
    from .formen import alle
    formen = [sh for sh in alle(folie.shapes, gruppen=True) if sh._element is not f["form"]._element
              and sh._element.getparent().tag != qn("p:grpSp")]
    formen += [sh for sh in folie.slide_layout.shapes if not sh.is_placeholder]
    if folie.slide_layout._element.get("showMasterSp") != "0":
        formen += [sh for sh in folie.slide_layout.slide_master.shapes if not sh.is_placeholder]
    out = []
    for sh in formen:
        if None in (sh.top, sh.left, sh.width, sh.height):
            continue
        y, x, w, h = (v / 914400 for v in (sh.top, sh.left, sh.width, sh.height))
        if y + h <= f["oben"] + 0.05 and x < f["links"] + f["breite"] and x + w > f["links"]:
            out.append((y, y + h))
    return out


def titel_pruefen(folie):
    """Warnung (Text), wenn der Titel mehr Zeilen braucht, als Platz ist, sonst None:
    - oben verankert (Inhaltsfolien): eine weitere Zeile ragt in den Inhalt darunter – die Typen auf „Only title“
      beginnen direkt unter der ersten Titelzeile. Inhalt = oberste Form unterhalb der ersten Zeile, die den Titel
      waagrecht überlappt (ohne Fußzeile, Foliennummer, Datum);
    - unten verankert (Titel- und Kapitelfolie): der Titel wächst über seinen Rahmen nach oben (Logo, Folienrand)."""
    from .bausteine import text_breite, umbrechen
    from .formen import alle
    f = titel_format(folie)
    if f is None or f["verkleinern"]:
        return None
    platz = f["breite"] - f["rand_l"] - f["rand_r"]
    zeilen = sum(umbrechen(a, platz, f["groesse"], f["fett"], kopf=True)[0] for a in f["absaetze"])
    if zeilen < 2:
        return None
    zh = f["groesse"] * 1.2 * f["zeile"] / 72
    text = " ".join(f["absaetze"])
    fasst = int(len(text) * platz / max(text_breite(text, f["groesse"], f["fett"], kopf=True), 0.01))
    kopf = f"Titel braucht {zeilen} Zeilen ({len(text)} Zeichen, eine Zeile fasst etwa {fasst})"
    if f["anker"] == "b":
        oben = f["oben"] + f["hoehe"] - f["rand_u"] - zeilen * zh
        grenze = max([0.0] + [u for _, u in _ueber(folie, f)])
        if oben >= grenze - 0.02:
            return None
        return (f"{kopf} – er wächst nach oben über {'das Logo' if grenze else 'den Folienrand'} (Text ab {oben:.2f} in, "
                f"frei ab {grenze:.2f} in). Titel kürzen, Rest in den Untertitel")
    oben = f["oben"] + (f["rand_o"] if f["anker"] != "ctr" else (f["hoehe"] - zeilen * zh) / 2)
    unten = oben + zeilen * zh
    inhalt = None
    for sh in alle(folie.shapes, gruppen=True):
        el = sh._element
        if el is f["form"]._element or el.getparent().tag == qn("p:grpSp") or None in (sh.top, sh.left, sh.width):
            continue
        ph = el.find(f".//{qn('p:nvPr')}/{qn('p:ph')}")
        if ph is not None and ph.get("type") in ("ftr", "sldNum", "dt"):
            continue
        y, x, w = sh.top / 914400, sh.left / 914400, sh.width / 914400
        if y >= oben + zh - 0.02 and x < f["links"] + f["breite"] and x + w > f["links"]:
            inhalt = y if inhalt is None else min(inhalt, y)
    if inhalt is None or unten <= inhalt + 0.02:
        return None
    return (f"{kopf} – Zeile {zeilen} ragt in den Inhalt darunter (Titel bis {unten:.2f} in, Inhalt ab {inhalt:.2f} in). "
            "Titel kürzen, Details ins Band oder in den Inhalt")


def leere_platzhalter_entfernen(folie, behalten=("ftr", "sldNum")):
    for ph in list(folie.placeholders):
        t = ph._element.find(".//" + qn("p:ph")).get("type")
        if t in behalten:
            continue
        if ph.has_text_frame and not ph.text_frame.text.strip():
            ph._element.getparent().remove(ph._element)


def alle_folien_entfernen(prs):
    lst = prs.slides._sldIdLst
    for el in list(lst):
        prs.part.drop_rel(el.rId)
        lst.remove(el)


def extrahieren(quelle_pptx, ziel):
    """Vorlage aus einer Präsentation im BI-Master erzeugen: alle Folien raus, Master/Layouts/Theme bleiben.
    Doppelte Layouts aus eingefügten Folien („1_…“, „2_…“) werden entfernt."""
    prs = oeffnen(quelle_pptx)
    if not ist_bi_master(prs):
        print("WARNUNG: Quelle hat keine BI-Master-Layouts ('Only title', 'Title slide (bright)').")
    alle_folien_entfernen(prs)
    for master in prs.slide_masters:
        namen = {l.name for l in master.slide_layouts}
        for l in list(master.slide_layouts):
            basis = re.sub(r"^\d+_", "", l.name)
            if basis != l.name and basis in namen:
                master.slide_layouts.remove(l)
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(ziel))
    return [l.name for l in prs.slide_layouts]
