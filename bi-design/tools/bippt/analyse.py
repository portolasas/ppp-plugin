"""Bestehende Präsentation knapp beschreiben (token-sparsam): Vorlage, Layouts, je Folie Titel/Text/Tabellen/Bilder."""
import json
import re
from pathlib import Path

from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu

from . import vorlage
from .formen import Unbekannt as _U, alle, art, meldung


def _ph_typ(sh):
    if not sh.is_placeholder:
        return None
    return str(sh.placeholder_format.type).split(".")[-1].split(" ")[0]


def folie_lesen(sl, nr, formen=False):
    d = {"nr": nr, "layout": sl.slide_layout.name, "ausgeblendet": sl._element.get("show") == "0",
         "titel": "", "texte": [], "tabellen": [], "bilder": [], "diagramme": [], "notizen": "", "unbekannt": []}
    if formen:
        d["formen"] = []
    if sl.shapes.title is not None and sl.shapes.title.has_text_frame:
        d["titel"] = sl.shapes.title.text_frame.text.strip()
    unbekannt = []
    for sh in alle(sl.shapes, unbekannt):
        pt = _ph_typ(sh)
        if pt in ("FOOTER", "SLIDE_NUMBER", "DATE") or (sl.shapes.title is not None and sh.shape_id == sl.shapes.title.shape_id):
            continue
        pos = [round(Emu(v).inches, 2) if v is not None else None for v in (sh.left, sh.top, sh.width, sh.height)]
        if sh.has_text_frame and sh.text_frame.text.strip():
            absaetze = []
            for p in sh.text_frame.paragraphs:
                t = "".join(r.text for r in p.runs).strip()
                if t:
                    absaetze.append({"t": t, "ebene": p.level, "fett": any(r.font.bold for r in p.runs)})
            d["texte"].append({"form": sh.name, "id": sh.shape_id, "ph": pt, "pos": pos, "absaetze": absaetze})
        if getattr(sh, "has_table", False) and sh.has_table:
            d["tabellen"].append({"pos": pos, "zeilen": [[c.text.strip() for c in r.cells] for r in sh.table.rows]})
        if art(sh) == MSO_SHAPE_TYPE.PICTURE or (pt == "PICTURE" and hasattr(sh, "image")):
            try:
                d["bilder"].append({"form": sh.name, "id": sh.shape_id, "pos": pos, "typ": sh.image.ext,
                                    "bytes": len(sh.image.blob), "zuschnitt": _zuschnitt(sh)})
            except (AttributeError, ValueError):
                pass
        if getattr(sh, "has_chart", False) and sh.has_chart:
            ch = sh.chart
            try:
                kat = list(ch.plots[0].categories)
                reihen = [{"name": s.name, "werte": list(s.values)} for s in ch.plots[0].series]
            except (IndexError, ValueError, AttributeError):
                kat, reihen = [], []
            d["diagramme"].append({"pos": pos, "art": str(ch.chart_type).split(".")[-1].split(" ")[0],
                                   "kategorien": [str(x) for x in kat], "reihen": reihen})
        if formen:
            d["formen"].append(_form(sh, pt, pos))
    d["unbekannt"] = [u._asdict() for u in unbekannt]
    if sl.has_notes_slide and sl.notes_slide.notes_text_frame is not None:
        d["notizen"] = sl.notes_slide.notes_text_frame.text.strip()
    return d


def _zuschnitt(sh):
    """Zuschnitt in % (links, oben, rechts, unten), None ohne Zuschnitt."""
    try:
        z = [round(100 * v, 1) for v in (sh.crop_left, sh.crop_top, sh.crop_right, sh.crop_bottom)]
    except (AttributeError, ValueError):
        return None
    return z if any(z) else None


def _form(sh, pt, pos):
    """Eine Form für `aendern`: id, Name, Art, Lage; Absätze als Liste der Lauftexte (gemischte Formatierung sichtbar)."""
    t = art(sh)
    typ = pt or (str(t).split(".")[-1].split(" ")[0] if t is not None else "unbekannt")
    f = {"id": sh.shape_id, "name": sh.name, "art": typ.lower(), "pos": pos}
    if sh.has_text_frame and sh.text_frame.text.strip():
        f["absaetze"] = [[r.text for r in p.runs] for p in sh.text_frame.paragraphs]
    return f


def analyse(pfad, formen=False, folien=None):
    """folien: nur diese Nummern (ab 1) lesen, z. B. die zu ändernden Folien."""
    prs = vorlage.oeffnen(pfad)
    return {
        "datei": str(pfad),
        "format": f"{Emu(prs.slide_width).inches:.2f} x {Emu(prs.slide_height).inches:.2f} in",
        "bi_master": vorlage.ist_bi_master(prs),
        "layouts": [l.name for l in prs.slide_layouts],
        "anzahl": len(prs.slides),
        "folien": [folie_lesen(s, i, formen) for i, s in enumerate(prs.slides, 1) if not folien or i in folien],
    }


def als_markdown(a, notizen=True):
    gelesen = "" if len(a["folien"]) == a.get("anzahl", len(a["folien"])) else f", gelesen: {len(a['folien'])}"
    z = [f"# {Path(a['datei']).name}", f"Format {a['format']} · BI-Master: {'ja' if a['bi_master'] else 'NEIN'} · "
         f"{a.get('anzahl', len(a['folien']))} Folien{gelesen} "
         f"({sum(1 for f in a['folien'] if f['ausgeblendet'])} ausgeblendet)", ""]
    for f in a["folien"]:
        z.append(f"## {f['nr']}. {f['titel'] or '(ohne Titel)'}  [{f['layout']}]{' (ausgeblendet)' if f['ausgeblendet'] else ''}")
        for t in f["texte"]:
            for p in t["absaetze"]:
                z.append(f"{'  ' * p['ebene']}- {p['t']}")
        for tb in f["tabellen"]:
            for r in tb["zeilen"]:
                z.append("| " + " | ".join(c.replace("\n", " / ") for c in r) + " |")
        for b in f["bilder"]:
            zs = f" Zuschnitt {b['zuschnitt']} %" if b.get("zuschnitt") else ""
            z.append(f"[Bild {b['form']} {b['typ']} @ {b['pos']}{zs}]")
        for d in f["diagramme"]:
            z.append(f"[Diagramm {d['art']}: {', '.join(d['kategorien'][:8])} | Reihen: {', '.join(r['name'] for r in d['reihen'])}]")
        for u in f["unbekannt"]:
            z.append(f"[Unbekannt: {meldung(_U(**u))}]")
        if f.get("formen"):
            z.append("Formen (für aendern; Läufe mit ‖ getrennt):")
            for fo in f["formen"]:
                z.append(f"  #{fo['id']} „{fo['name']}“ {fo['art']} @ {fo['pos']}")
                for i, p in enumerate(fo.get("absaetze", []), 1):
                    z.append(f"      {i}) " + "‖".join(p))
        if notizen and f["notizen"]:
            z.append(f"> Notizen: {f['notizen'][:400]}")
        z.append("")
    return "\n".join(z)


# ----------------------------------------------------------------- Entwurf für das Umwandeln
def entwurf(pfad, medien_ordner=None):
    """Spezifikation aus einer fremden Präsentation ableiten (Ausgangspunkt – der Agent verfeinert Typen/Texte)."""
    prs = vorlage.oeffnen(pfad)
    pfad = Path(pfad)
    medien = Path(medien_ordner) if medien_ordner else pfad.with_name(pfad.stem + "_medien")
    folien = []
    for i, sl in enumerate(prs.slides, 1):
        f = folie_lesen(sl, i)
        texte = [t for t in f["texte"] if t["absaetze"]]
        alle = [p for t in texte for p in t["absaetze"]]
        if i == 1 and len(alle) <= 4 and not f["tabellen"]:
            folien.append({"typ": "titel", "titel": f["titel"] or (alle[0]["t"] if alle else ""),
                           "untertitel": [p["t"] for p in alle if p["t"] != f["titel"]][:3]})
            continue
        spec = {"titel": f["titel"] or "TITEL FEHLT", "_quelle_folie": i}
        if f["ausgeblendet"]:
            spec["ausblenden"] = True
        if f["notizen"]:
            spec["notizen"] = f["notizen"]
        if f["diagramme"]:
            d = f["diagramme"][0]
            art = {"BAR": "balken", "LINE": "linie", "PIE": "torte", "DOUGHNUT": "torte"}
            spec.update({"typ": "diagramm", "art": next((v for k_, v in art.items() if k_ in d["art"]), "saeulen"),
                         "kategorien": d["kategorien"], "reihen": d["reihen"]})
            if alle:
                spec["fazit"] = {"titel": "Fazit", "punkte": [p["t"] for p in alle][:5]}
        elif f["tabellen"]:
            t = f["tabellen"][0]["zeilen"]
            spec.update({"typ": "tabelle", "kopf": t[0], "zeilen": t[1:]})
        elif f["bilder"] and alle:
            bild = _bild_sichern(sl, medien, i)
            spec.update({"typ": "bild_text", "bild": bild, "punkte": [p["t"] for p in alle]})
        elif len(texte) >= 2 and len(texte) <= 4 and all(len(t["absaetze"]) >= 2 for t in texte):
            texte = sorted(texte, key=lambda t: (t["pos"][0] or 0))
            spec.update({"typ": "karten", "karten": [{"titel": t["absaetze"][0]["t"] if t["absaetze"][0]["fett"] else "",
                                                       "punkte": [p["t"] for p in t["absaetze"][1 if t["absaetze"][0]["fett"] else 0:]]}
                                                      for t in texte]})
        else:
            spec.update({"typ": "text", "punkte": [{"t": p["t"], "ebene": p["ebene"]} if p["ebene"] else p["t"] for p in alle]})
        folien.append(spec)
    return {"ausgabe": pfad.stem + "_BI.pptx", "fusszeile": "", "folien": folien,
            "_hinweis": "Entwurf aus bippt umwandeln – Typen/Texte verdichten (status, vergleich, prozess, timeline, "
                        "massnahmen, kennzahlen), Band je Folie mit Kernaussage, dann bippt bauen."}


def _bild_sichern(sl, medien, nr):
    """Größtes eingebettetes Bild der Folie nach medien/folieNN.<ext>; verknüpfte Bilder zählen nicht."""
    groesstes = None
    for sh in alle(sl.shapes):
        if art(sh) == MSO_SHAPE_TYPE.PICTURE:
            try:
                sh.image
            except (ValueError, KeyError, AttributeError):
                continue
            if groesstes is None or sh.width * sh.height > groesstes.width * groesstes.height:
                groesstes = sh
    if groesstes is None:
        return None
    medien.mkdir(parents=True, exist_ok=True)
    ziel = medien / f"folie{nr:02d}.{groesstes.image.ext}"
    ziel.write_bytes(groesstes.image.blob)
    return str(ziel)


def main_json(pfad):
    print(json.dumps(analyse(pfad), ensure_ascii=False, indent=1, default=str))
