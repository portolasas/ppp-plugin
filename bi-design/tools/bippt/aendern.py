"""Bestehende Folien ändern (Modus V): Texte ersetzen, Platzhalter füllen und mit `aendern` einzelne Formen bearbeiten.

Spec je Basisfolie: "aendern": [{…}, …]. Jede Änderung spricht Formen an über
  "form": "Name" (mit "nr": n die n-te Form dieses Namens) · "id": 12 · "formen": ["Name", …] (mehrere, z. B. eine Reihe)
und macht damit in dieser Reihenfolge:
  "x", "y", "w", "h" (Zoll) · "dx", "dy" (Zoll, relativ)                     Lage und Größe
  "bild": "pfad.png", "ausschnitt": "oben" | {"oben_px": 586}                Bild tauschen; Rahmen bleibt, Zuschnitt passt
  "absaetze": ["…", null, {"t": "…", "wie": 2}]                              alle Absätze setzen
  "anhaengen": ["…"]                                                         Absätze anhängen
  "absatz": 2, "text": "…"  bzw.  "laeufe": ["…", null, {"t": "…", "wie": 1}]  einen Absatz bzw. seine Läufe setzen
  "absatz": 2 | [2, 3], "entfernen": true                                    Absätze entfernen
  "name": "Neu" · "entfernen": true                                          umbenennen, Form entfernen
Texte: ohne Markierung bekommt der Absatz das Format seines ersten Laufs; mit `**fett**` (oder `==…==`) bekommen die
markierten Teile das Format eines fetten Laufs im Absatz und der Rest das eines normalen – gemischte Formatierung bleibt.
null = Absatz bzw. Lauf bleibt, wie er ist. Neue Absätze und Läufe kopieren den letzten vorhandenen oder den mit "wie"
(ab 1) genannten. Pfade relativ zur Spec.
"""
import copy
import re
from pathlib import Path

from pptx.oxml.ns import qn
from pptx.text.text import _Paragraph, _Run

from .bausteine import E, _laeufe, bild_pruefen
from .formen import alle, finden

MARKIERT = re.compile(r"\*\*.+?\*\*|==.+?==")
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
SVG = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"  # a:ext mit asvg:svgBlip (SVG-Fassung eines Bildes)
FELDER = {"form", "id", "nr", "formen", "x", "y", "w", "h", "dx", "dy", "bild", "ausschnitt", "absaetze", "anhaengen",
          "absatz", "text", "laeufe", "name", "entfernen"}


# ---------------------------------------------------------------- Text
def _lauf_vorlage(p, fett):
    for r in p.runs:
        if bool(r.font.bold) == fett:
            return r._r
    return p.runs[0]._r


def _absatz_setzen(p, text):
    """Text eines Absatzes ersetzen; Format siehe Modulkopf (erster Lauf bzw. fette/normale Läufe bei **…**)."""
    text = str(text)
    if not p.runs:
        p.add_run()
    for br in p._p.findall(qn("a:br")):
        p._p.remove(br)
    alte = p.runs
    if not MARKIERT.search(text):
        alte[0].text = text
        for r in alte[1:]:
            r._r.getparent().remove(r._r)
        return
    vorlage = {f: _lauf_vorlage(p, f) for f in (True, False)}
    for t, fmt in _laeufe(text):
        fett = bool(fmt.get("fett") or fmt.get("hervor"))
        r = copy.deepcopy(vorlage[fett])
        alte[0]._r.addprevious(r)
        lauf = _Run(r, p)
        lauf.text = t
        if bool(lauf.font.bold) != fett:
            lauf.font.bold = fett
    for r in alte:
        r._r.getparent().remove(r._r)


def _plan(alte, eintraege, was):
    """[(Element, Eintrag)]: vorhandenes Element an Position i oder Kopie (letztes bzw. "wie")."""
    plan = []
    for i, e in enumerate(eintraege):
        wie = e.get("wie") if isinstance(e, dict) else None
        if wie is None and i < len(alte):
            plan.append((alte[i], e))
            continue
        if e is None:
            raise ValueError(f"{was} {i + 1} fehlt (es gibt {len(alte)}) – null geht nur für vorhandene")
        j = wie - 1 if wie else len(alte) - 1
        if not 0 <= j < len(alte):
            raise ValueError(f"wie {wie}: {was} fehlt (es gibt {len(alte)})")
        plan.append((copy.deepcopy(alte[j]), e))
    return plan


def _neu_anordnen(alte, plan):
    eltern = alte[0].getparent()
    pos = eltern.index(alte[0])
    for el in alte:
        eltern.remove(el)
    for n, (el, _) in enumerate(plan):
        eltern.insert(pos + n, el)


def absaetze_setzen(tf, zeilen):
    """Absätze eines Textrahmens setzen (Liste wie im Modulkopf); überzählige alte Absätze entfallen."""
    zeilen = zeilen if isinstance(zeilen, list) else [zeilen]
    if not zeilen:
        zeilen = [""]
    alte = [p._p for p in tf.paragraphs]
    plan = _plan(alte, zeilen, "Absatz")
    _neu_anordnen(alte, plan)
    for el, z in plan:
        if z is not None:
            _absatz_setzen(_Paragraph(el, tf), z.get("t", "") if isinstance(z, dict) else z)


def platzhalter_zeilen(ph, zeilen):
    """Zeilen in einen vorhandenen Platzhalter schreiben, Absatzformate bleiben erhalten."""
    absaetze_setzen(ph.text_frame, zeilen)


def laeufe_setzen(p, eintraege):
    """Läufe eines Absatzes einzeln setzen (Text ohne Markierung, Format des jeweiligen Laufs bleibt)."""
    if not p.runs:
        p.add_run()
    alte = [r._r for r in p.runs]
    plan = _plan(alte, eintraege, "Lauf")
    _neu_anordnen(alte, plan)
    for el, e in plan:
        if e is not None:
            _Run(el, p).text = e.get("t", "") if isinstance(e, dict) else str(e)


def _naechster_treffer(text, such, ab):
    """(Position, Suchtext) des ersten Treffers ab `ab`; bei gleicher Position gewinnt der längere Suchtext."""
    best = None
    for a in such:
        i = text.find(a, ab)
        if i >= 0 and (best is None or i < best[0] or (i == best[0] and len(a) > len(best[1]))):
            best = (i, a)
    return best


def _ersetzen_absatz(p, alt, neu=None):
    """alt → neu in einem Absatz, auch über Läufe hinweg; alt darf auch eine Zuordnung {alt: neu, …} sein (neu dann
    None). Alle Suchtexte in einem Durchgang von links nach rechts: eingesetzter Text wird nie noch einmal ersetzt, auch
    wenn er einen Suchtext enthält („GBS“ → „GBS United“). Läufe außerhalb des Treffers behalten Text und Format, der
    Treffer bekommt das Format seines ersten Laufs. Rückgabe: {Suchtext: Anzahl Treffer}."""
    zuordnung = alt if neu is None else {alt: neu}
    such = [a for a in zuordnung if a]
    treffer, ab = {}, 0
    while such:
        runs = p.runs
        best = _naechster_treffer("".join(r.text for r in runs), such, ab)
        if best is None:
            return treffer
        i, alt = best
        neu = str(zuordnung[alt])
        j, pos, erster = i + len(alt), 0, None
        for k, r in enumerate(runs):
            ende = pos + len(r.text)
            if erster is None and i < ende:
                erster, a = k, i - pos
            if erster is not None and j <= ende:
                letzter, b = k, j - pos
                break
            pos = ende
        if erster == letzter:
            t = runs[erster].text
            runs[erster].text = t[:a] + neu + t[b:]
        else:
            runs[erster].text = runs[erster].text[:a] + neu
            runs[letzter].text = runs[letzter].text[b:]
            for r in runs[erster + 1:letzter]:
                r._r.getparent().remove(r._r)
        treffer[alt] = treffer.get(alt, 0) + 1
        ab = i + len(neu)
    return treffer


def _textrahmen(folie):
    for sh in alle(folie.shapes):
        if sh.has_text_frame:
            yield sh.text_frame
        if getattr(sh, "has_table", False) and sh.has_table:
            for row in sh.table.rows:
                for c in row.cells:
                    yield c.text_frame


def ersetzen(folie, zuordnung):
    """Textstellen ersetzen (auch über Läufe hinweg, in Gruppen und Tabellen); Formatierung außerhalb der Treffer bleibt.
    Je Absatz ein Durchgang über alle Suchtexte (siehe _ersetzen_absatz) – darum je Folie genau EINMAL aufrufen: ein
    zweiter Aufruf ersetzt erneut, wenn der neue Text den alten enthält. Rückgabe: Menge der gefundenen Suchtexte."""
    gefunden = set()
    for tf in _textrahmen(folie):
        for p in tf.paragraphs:
            gefunden |= set(_ersetzen_absatz(p, zuordnung))
    return gefunden


# ---------------------------------------------------------------- Bild
def _benutzt(folie, rid):
    return any(k.startswith(R) and v == rid for el in folie._element.iter() for k, v in el.attrib.items())


def _zuschneiden(sh, bw, bh, ausschnitt, vorher=None):
    """Zuschnitt, damit ein Bild von bw × bh Pixeln den Rahmen ohne Verzerrung füllt. vorher = ((w, h), Zuschnitt) des
    alten Bildes: ohne ausschnitt gleicher Zuschnitt bei gleichem Seitenverhältnis, sonst dieselbe Kante."""
    rw, rh = sh.width, sh.height
    if not rw or not rh or not bw or not bh:
        return
    waagrecht, senkrecht, px = "mitte", "mitte", {}
    if isinstance(ausschnitt, dict):
        px = ausschnitt
    elif ausschnitt in ("links", "rechts"):
        waagrecht = ausschnitt
    elif ausschnitt in ("oben", "unten", "mitte"):
        senkrecht = ausschnitt
    elif ausschnitt is not None:
        raise ValueError(f"ausschnitt '{ausschnitt}' – erlaubt: oben, mitte, unten, links, rechts, {{oben_px, links_px}}")
    elif vorher:
        (aw, ah), (cl, ct, cr, cb) = vorher
        if aw and ah and abs(aw / ah - bw / bh) < 0.01 * bw / bh:
            sh.crop_left, sh.crop_top, sh.crop_right, sh.crop_bottom = cl, ct, cr, cb
            return
        waagrecht = "links" if cl < 0.005 < cr else ("rechts" if cr < 0.005 < cl else "mitte")
        senkrecht = "oben" if ct < 0.005 < cb else ("unten" if cb < 0.005 < ct else "mitte")
    bild, rahmen = bw / bh, rw / rh
    l = t = r = b = 0.0
    if bild > rahmen:  # breiter als der Rahmen: links/rechts beschneiden
        rest = 1 - rahmen / bild
        if "links_px" in px:
            l = min(max(px["links_px"] / bw, 0), rest)
        else:
            l = {"links": 0, "rechts": rest}.get(waagrecht, rest / 2)
        r = rest - l
    else:
        rest = 1 - bild / rahmen
        if "oben_px" in px:
            t = min(max(px["oben_px"] / bh, 0), rest)
        else:
            t = {"oben": 0, "unten": rest}.get(senkrecht, rest / 2)
        b = rest - t
    sh.crop_left, sh.crop_top, sh.crop_right, sh.crop_bottom = l, t, r, b


def bild_tauschen(folie, sh, datei, ausschnitt=None):
    """Bild einer Bildform oder eines Bildplatzhalters tauschen; Rahmen bleibt, Zuschnitt nach _zuschneiden.
    Eine SVG-Fassung des alten Bildes entfällt (sonst zeigt PowerPoint weiter das alte)."""
    from PIL import Image
    datei = Path(datei)
    if not datei.is_file():
        raise ValueError(f"Bild fehlt: {datei}")
    with Image.open(datei) as im:
        bw, bh = im.size
    if sh._element.tag != qn("p:pic"):
        if not hasattr(sh, "insert_picture"):
            raise ValueError("keine Bildform und kein Bildplatzhalter")
        neu = sh.insert_picture(str(datei))
        if ausschnitt is not None:
            _zuschneiden(neu, bw, bh, ausschnitt)
        return neu
    try:
        vorher = (sh.image.size, (sh.crop_left, sh.crop_top, sh.crop_right, sh.crop_bottom))
    except (AttributeError, KeyError, ValueError, OSError):
        vorher = None
    blip = sh._element.find(".//" + qn("a:blip"))
    alte = {blip.get(qn("r:embed"))}
    _, rid = folie.part.get_or_add_image_part(str(datei))
    blip.set(qn("r:embed"), rid)
    ext = blip.find(qn("a:extLst"))
    if ext is not None:
        for e in list(ext):
            if e.get("uri") == SVG:
                alte |= {c.get(R + "embed") for c in e}
                ext.remove(e)
        if not len(ext):
            blip.remove(ext)
    for r in alte - {rid, None}:
        if not _benutzt(folie, r):
            folie.part.drop_rel(r)
    _zuschneiden(sh, bw, bh, ausschnitt, vorher)
    return sh


# ---------------------------------------------------------------- Änderungen anwenden
def _ziele(k, op, wo):
    if "id" in op:
        t = finden(k.folie, sid=op["id"])
        if not t:
            k.warn(f"{wo}: keine Form mit id {op['id']} (bippt analyse --formen)")
        return t
    namen = op.get("formen") or ([op["form"]] if op.get("form") else [])
    if not namen:
        k.warn(f"{wo}: form, formen oder id fehlt")
    out = []
    for nm in namen:
        t = finden(k.folie, nm, nr=op.get("nr"))
        if len(t) == 1:
            out.append(t[0])
        elif t:
            k.warn(f"{wo}: „{nm}“ gibt es {len(t)}× – nr oder id angeben (bippt analyse --formen)")
        else:
            da = ", ".join(f"„{s.name}“" for s in alle(k.folie.shapes))
            k.warn(f"{wo}: Form „{nm}“{' Nr. ' + str(op['nr']) if op.get('nr') else ''} nicht gefunden – "
                   f"vorhanden: {da[:400]}")
    return out


def _anwenden(k, sh, op, ordner):
    if any(op.get(x) is not None for x in ("x", "y", "w", "h", "dx", "dy")):
        lage = [sh.left, sh.top, sh.width, sh.height]  # alle vier setzen: Platzhalter erben sie sonst nur teilweise
        for i, key in enumerate(("x", "y", "w", "h")):
            if op.get(key) is not None:
                lage[i] = E(op[key])
        lage[0] += E(op.get("dx") or 0)
        lage[1] += E(op.get("dy") or 0)
        sh.left, sh.top, sh.width, sh.height = lage
    if op.get("bild"):
        q = Path(op["bild"]).expanduser()
        q = q if q.is_absolute() else Path(ordner) / q
        sh = bild_tauschen(k.folie, sh, q, op.get("ausschnitt"))
        bild_pruefen(k, q, sh)
    absatz = "absatz" in op or op.get("text") is not None or op.get("laeufe") is not None
    if absatz or op.get("absaetze") is not None or op.get("anhaengen"):
        if not sh.has_text_frame:
            raise ValueError("Form hat keinen Textrahmen")
        tf = sh.text_frame
        if op.get("absaetze") is not None:
            absaetze_setzen(tf, op["absaetze"])
        if op.get("anhaengen"):
            absaetze_setzen(tf, [None] * len(tf.paragraphs) + list(op["anhaengen"]))
        if absatz:
            nrn = op.get("absatz", 1)
            nrn = nrn if isinstance(nrn, list) else [nrn]
            ps = tf.paragraphs
            for n in nrn:
                if not 1 <= n <= len(ps):
                    raise ValueError(f"Absatz {n} fehlt (die Form hat {len(ps)})")
            if op.get("entfernen"):
                if len(set(nrn)) >= len(ps):
                    raise ValueError("alle Absätze entfernen geht nicht – Form entfernen (ohne absatz)")
                for n in sorted(set(nrn), reverse=True):
                    ps[n - 1]._p.getparent().remove(ps[n - 1]._p)
            elif op.get("laeufe") is not None:
                laeufe_setzen(ps[nrn[0] - 1], op["laeufe"])
            elif op.get("text") is not None:
                _absatz_setzen(ps[nrn[0] - 1], op["text"])
    if op.get("name"):
        sh.name = op["name"]
    if op.get("entfernen") and not absatz:
        sh._element.getparent().remove(sh._element)


def aendern(k, aenderungen, ordner):
    """Änderungen an Formen der Folie im Kontext k; Probleme werden Warnungen, der Bau läuft weiter."""
    for i, op in enumerate(aenderungen, 1):
        wo = f"aendern {i}"
        fremd = set(op) - FELDER
        if fremd:
            k.warn(f"{wo}: unbekannte Felder {', '.join(sorted(fremd))} – erlaubt: {', '.join(sorted(FELDER))}")
        for sh in _ziele(k, op, wo):
            try:
                _anwenden(k, sh, op, ordner)
            except (ValueError, OSError) as e:
                k.warn(f"{wo} („{sh.name}“): {e}")
