"""Folienbeschreibung: Inhalt und Gestaltung jeder Folie als Markdown neben der Präsentation, damit andere Agenten und
Sitzungen das Deck lesen und gezielt ändern können, ohne die PPTX auszulesen.

`bippt bauen` schreibt sie bei jedem Bau: neue Folien aus der Spec (mit Ampeln, Terminen, Tabellen), Basisfolien aus dem
fertigen Deck. Ziel ist `"dokument"` der Spec, sonst `<ausgabe>.md`. bippt pflegt nur den Abschnitt zwischen den Marken
`<!-- bippt:folienbeschreibung … -->` und `<!-- /bippt:folienbeschreibung -->`; eine Vorlage ohne Marken (z. B. von ppp)
behält ihren Text, der Abschnitt kommt ans Ende.

Baustand: Die Startmarke trägt je Folie einen Fingerabdruck – `bau=` des zuletzt gebauten Decks, `stand=` der Folien, die
der Abschnitt beschreibt. Weicht das Deck von `bau=` ab, wurde es nach dem Bau geändert (z. B. in PowerPoint); `bippt bauen`
überschreibt es dann nicht. Über `stand=` übernimmt bippt die Beschreibung unveränderter Folien (auch aus der Beschreibung
der Basis), statt sie neu aus dem Deck zu lesen.
"""
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path

from . import vorlage
from .analyse import folie_lesen
from .formen import Unbekannt, meldung

START = "<!-- bippt:folienbeschreibung"
ENDE = "<!-- /bippt:folienbeschreibung -->"
AMPEL = {"G": "Grün", "Y": "Gelb", "R": "Rot", "YR": "Gelb–Rot", "N": "ohne Bewertung"}
STAND = {2: "fertig", 1: "aktiv", 0: "offen"}
FORMART = {"auto_shape": ("Form", "Formen"), "text_box": ("Textfeld", "Textfelder"), "picture": ("Bild", "Bilder"),
           "table": ("Tabelle", "Tabellen"), "chart": ("Diagramm", "Diagramme"), "line": ("Linie", "Linien"),
           "freeform": ("Freiform", "Freiformen"), "body": ("Textplatzhalter", "Textplatzhalter"),
           "object": ("Inhaltsplatzhalter", "Inhaltsplatzhalter"), "subtitle": ("Untertitel", "Untertitel"),
           "media": ("Medium", "Medien"), "embedded_ole_object": ("OLE-Objekt", "OLE-Objekte")}


# ----------------------------------------------------------------- Text aus der Spec
def _klar(x):
    """Spec-Text als eine Zeile ohne Markierungen (**fett**, ==hervor==)."""
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        return " ".join(t for t in (_klar(a) for a in x) if t)
    if isinstance(x, dict):
        return _klar(x.get("t", x.get("text", "")))
    return re.sub(r"\s+", " ", re.sub(r"\*\*|==", "", str(x))).strip()


def _absaetze(x):
    """Spec-Text als [(text, ebene)] – eine Liste ist je Eintrag ein Absatz."""
    if x is None:
        return []
    out = []
    for a in x if isinstance(x, (list, tuple)) else [x]:
        t = _klar(a)
        if t:
            out.append((t, int(a.get("ebene", 0)) if isinstance(a, dict) else 0))
    return out


def _punkte(z, x, tiefe=0):
    for t, e in _absaetze(x):
        z.append(f"{'  ' * (tiefe + e)}- {t}")


def _zelle(x):
    if isinstance(x, dict) and "ampel" in x:
        werte = x["ampel"] if isinstance(x["ampel"], list) else [x["ampel"]]
        labs = x.get("labels", [])
        a = ", ".join(AMPEL.get(w, w) + (f" ({labs[i]})" if i < len(labs) else "") for i, w in enumerate(werte))
        t = _klar(x.get("t"))
        x = f"Ampel {a}" + (f": {t}" if t else "")
    return _klar(x).replace("|", "\\|")


def _tabelle(z, kopf, zeilen):
    n = max([len(kopf)] + [len(r) for r in zeilen]) if (kopf or zeilen) else 0
    if not n:
        return
    z.append("| " + " | ".join(_zelle(c) for c in list(kopf) + [""] * (n - len(kopf))) + " |")
    z.append("|" + "---|" * n)
    for r in zeilen:
        z.append("| " + " | ".join(_zelle(c) for c in list(r) + [""] * (n - len(r))) + " |")


def _band(spec):
    if isinstance(spec, dict):
        return " ".join(t for t in (_klar(spec.get("label")), _klar(spec.get("text"))) if t)
    return _klar(spec)


def _hinweis(h):
    if isinstance(h, dict):
        return " ".join(t for t in ((_klar(h.get("titel")) + ":") if h.get("titel") else "", _klar(h.get("text"))) if t)
    return _klar(h)


def _bloecke(z, kar, tiefe):
    bl = kar.get("inhalt") or [{k: kar[k]} for k in ("phasen", "kennzahl", "von_nach", "bild", "punkte", "schritte",
                                                      "text") if kar.get(k) is not None]
    if kar.get("naechster"):
        bl = bl + [{"hinweis": {"titel": "Nächster Schritt", "text": kar["naechster"]}}]
    if kar.get("hinweis"):
        bl = bl + [{"hinweis": kar["hinweis"]}]
    ein = "  " * tiefe
    for b in bl:
        if "punkte" in b:
            _punkte(z, b["punkte"], tiefe)
        elif "text" in b:
            _punkte(z, b["text"], tiefe)
        elif "phasen" in b:
            ph = b["phasen"]
            z.append(f"{ein}- Phasen: " + ", ".join(f"{n} {STAND.get(s, '')}".strip()
                                                    for n, s in zip(ph.get("namen", []), ph.get("stand", []))))
        elif "schritte" in b:
            for i, st in enumerate(b["schritte"], 1):
                z.append(f"{ein}- {i}. {_klar(st.get('titel'))} ({st.get('status', 'offen')})"
                         + (f" – {_klar(st.get('text'))}" if st.get("text") else ""))
        elif "von_nach" in b:
            vn = b["von_nach"]
            seite = [" ".join(t for t in (_klar(vn.get(s, {}).get("klein")), _klar(vn.get(s, {}).get("gross"))) if t)
                     for s in ("von", "nach")]
            z.append(f"{ein}- Von {seite[0]} → nach {seite[1]}")
        elif "kennzahl" in b:
            z.append(f"{ein}- Kennzahl {_klar(b['kennzahl'].get('wert'))} {_klar(b['kennzahl'].get('label'))}".rstrip())
        elif "bild" in b:
            z.append(f"{ein}- Bild {_name(b['bild'])}")
        elif "hinweis" in b:
            z.append(f"{ein}- {_hinweis(b['hinweis'])}")


def _karte(z, kar, tiefe=0):
    zusatz = [f"Ampel {AMPEL.get(kar['ampel'], kar['ampel'])}"] if kar.get("ampel") else []
    if kar.get("hervor"):
        zusatz.append("hervorgehoben")
    titel = _klar(kar.get("titel")) or "(Karte ohne Titel)"
    z.append(f"{'  ' * tiefe}- **{titel}**" + (f" ({', '.join(zusatz)})" if zusatz else ""))
    _bloecke(z, kar, tiefe + 1)


def _kopf(z, kopf):
    if kopf:
        z.append(f"**{_klar(kopf.get('label'))}** {_klar(kopf.get('text'))}".strip() if isinstance(kopf, dict)
                 else _klar(kopf))
        z.append("")


def _anz(n, eins, mehr):
    return f"{n} {eins if n == 1 else mehr}"


def _name(bild):
    return Path(str(bild.get("datei") if isinstance(bild, dict) else bild)).name


# ----------------------------------------------------------------- Inhalt je Folientyp
def _titel(z, s):
    _punkte(z, s.get("untertitel"))


def _liste(z, s):
    _punkte(z, s.get("punkte"))


def _kernaussage(z, s):
    _punkte(z, s.get("text"))


def _status(z, s):
    if s.get("phasen"):
        z.append("Phasen: " + " → ".join(_klar(p) for p in s["phasen"]))
    for st in s.get("straenge", []):
        stand = ", ".join(f"{_klar(p)} {STAND.get(x, '')}".strip() for p, x in zip(s.get("phasen", []), st.get("stand", [])))
        a = f"Ampel {AMPEL.get(st['ampel'], st['ampel'])}" if st.get("ampel") else ""
        z.append(f"- **{_klar(st.get('titel'))}**" + (" – " + "; ".join(x for x in (a, stand) if x) if a or stand else ""))
        _punkte(z, st.get("punkte"), 1)
        if st.get("naechster"):
            z.append(f"  - Nächster Schritt: {_klar(st['naechster'])}")
    leg = s.get("legende", {"G": "im Plan", "Y": "beobachten / Freigabe ausstehend", "R": "Eskalation"})
    if leg:
        z.append("Legende: " + " · ".join(f"{AMPEL.get(w, w)} = {_klar(t)}" for w, t in leg.items()))


def _vergleich(z, s):
    _tabelle(z, s.get("spalten", ["Thema", "Vorher", "Jetzt"]), s.get("zeilen", []))


def _prozess(z, s):
    _kopf(z, s.get("kopf"))
    for i, st in enumerate(s.get("schritte", []), 1):
        zusatz = ", ".join(x for x in (_klar(st.get("ueber")), st.get("status", "")) if x)
        z.append(f"- **{i}. {_klar(st.get('titel'))}**" + (f" ({zusatz})" if zusatz else "")
                 + (f" – {_klar(st.get('text'))}" if st.get("text") else ""))
        _punkte(z, st.get("punkte"), 1)
    if s.get("hinweis"):
        z.append(f"Hinweis: {_hinweis(s['hinweis'])}")
    for kar in s.get("karten", []):
        _karte(z, kar)


def _karten(z, s):
    _kopf(z, s.get("kopf"))
    for kar in s.get("karten", []):
        _karte(z, kar)


def _timeline(z, s):
    if s.get("von") or s.get("bis"):
        z.append(f"Zeitraum: {s.get('von', '…')} – {s.get('bis', '…')}")
    for zl in s.get("zeilen", []):
        z.append(f"- **{_klar(zl.get('titel'))}**")
        for e in zl.get("elemente", []):
            art = e.get("art", "balken" if e.get("von") else "meilenstein")
            if art == "ueberbrueckung":
                z.append(f"  - {e.get('von')} – {e.get('bis')}: Überbrückung")
                continue
            wann = str(e.get("datum")) if art == "meilenstein" else f"{e.get('von')} – {e.get('bis')}"
            text = " ".join(t for t in ("Meilenstein" if art == "meilenstein" else "", _klar(e.get("text"))) if t)
            z.append(f"  - {wann}: {text or 'Balken'} ({e.get('status', 'plan')})")
    for mk in s.get("marker", []):
        z.append(f"- Marker {mk.get('datum')}: {_klar(mk.get('text'))}")
    for sch in s.get("schatten", []):
        z.append(f"- Graue Zone {sch.get('von')} – {sch.get('bis')}: {_klar(sch.get('text'))}")
    if s.get("fakten"):
        z.append(f"{_klar(s['fakten'].get('titel')) or 'Fakten'}:")
        _punkte(z, s["fakten"].get("punkte"))
    for b in s.get("boxen") or []:
        z.append(f"- {_hinweis(b)}")


def _massnahmen(z, s):
    zeilen = s.get("zeilen", [])
    tag = any(r.get("tag") for r in zeilen)
    _tabelle(z, ["Wann", "Was", "Worum es geht"] + (["Tag"] if tag else []),
             [[r.get("wann", ""), r.get("was", ""), r.get("details", "")] + ([r.get("tag", "")] if tag else [])
              for r in zeilen])


def _tabelle_folie(z, s):
    _tabelle(z, s.get("kopf", []), s.get("zeilen", []))


def _kennzahlen(z, s):
    for t in s.get("kacheln", []):
        a = f" (Ampel {AMPEL.get(t['ampel'], t['ampel'])})" if t.get("ampel") else ""
        z.append(f"- **{_klar(t.get('wert'))}** {_klar(t.get('label'))}{a}"
                 + (f" – {_klar(t.get('text'))}" if t.get("text") else ""))


def _diagramm(z, s):
    reihen = s.get("reihen", [])
    _tabelle(z, [""] + [r.get("name", "") for r in reihen],
             [[k] + [r.get("werte", [])[i] if i < len(r.get("werte", [])) else "" for r in reihen]
              for i, k in enumerate(s.get("kategorien", []))])
    if s.get("fazit"):
        z.append(f"{_klar(s['fazit'].get('titel')) or 'Fazit'}:")
        _punkte(z, s["fazit"].get("punkte"))


def _fluss(z, s):
    for sp in s.get("spalten", []):
        z.append(f"- **{_klar(sp.get('titel')) or 'Spalte'}**")
        for bx in sp.get("boxen", []):
            rest = " · ".join(t for t in (_klar(bx.get("text")), _klar(bx.get("klein"))) if t)
            z.append(f"  - {_klar(bx.get('titel'))}" + (f" – {rest}" if rest else ""))


def _bild_text(z, s):
    _punkte(z, s.get("punkte"))


def _frei(z, s):
    for el in s.get("elemente", []):
        f = el.get("form")
        if f == "karte":
            _karte(z, el)
        elif f == "band":
            z.append(f"- {_band(el)}")
        elif el.get("t"):
            _punkte(z, el["t"])


INHALT = {"titel": _titel, "kapitel": _titel, "agenda": _liste, "text": _liste, "kernaussage": _kernaussage,
          "abschluss": lambda z, s: None, "status": _status, "vergleich": _vergleich, "prozess": _prozess,
          "karten": _karten, "timeline": _timeline, "massnahmen": _massnahmen, "tabelle": _tabelle_folie,
          "kennzahlen": _kennzahlen, "diagramm": _diagramm, "fluss": _fluss, "bild_text": _bild_text, "frei": _frei}


# ----------------------------------------------------------------- Gestaltung je Folientyp
def _sammeln(x, schluessel):
    """Alle Werte zu den Schlüsseln (rekursiv), z. B. Icons und Bilder einer Folie."""
    out = []
    if isinstance(x, dict):
        for k, v in x.items():
            if k in schluessel and isinstance(v, (str, dict)):
                out.append(_name(v) if k in ("bild", "datei") else str(v))
            else:
                out += _sammeln(v, schluessel)
    elif isinstance(x, list):
        for v in x:
            out += _sammeln(v, schluessel)
    return list(dict.fromkeys(out))


def _art(s):
    """Aufbau der Folie in einem Satz – genug, um ohne Render zu wissen, wie sie aussieht."""
    typ = s.get("typ", "text")
    n = lambda k: len(s.get(k) or [])  # noqa: E731
    if typ == "status":
        return (f"{_anz(n('straenge'), 'Strangkarte', 'Strangkarten nebeneinander')} (Kopf mit Ampel, Phasenleiste, Punkte, Nächster Schritt), "
                "Ampellegende unten")
    if typ == "vergleich":
        return f"Tabelle alt → neu mit Pfeilspalte, {_anz(n('zeilen'), 'Zeile', 'Zeilen')}, neue Spalte fett"
    if typ == "prozess":
        sk = any(st.get("punkte") or st.get("ueber") for st in s.get("schritte", []))
        t = (f"{_anz(n('schritte'), 'Schrittkarte', 'Schrittkarten')} (Kopf in Statusfarbe, Pfeile zwischen den Köpfen)"
             if sk else f"Prozesskette mit {_anz(n('schritte'), 'Schritt', 'Schritten')} und Icons")
        return t + (", Kopfband" if s.get("kopf") else "") + (", gestrichelter Hinweis" if s.get("hinweis") else "") \
            + (f", {_anz(n('karten'), 'Karte', 'Karten')} darunter" if s.get("karten") else "")
    if typ == "karten":
        hervor = [_klar(k.get("titel")) for k in s.get("karten", []) if k.get("hervor")]
        return (f"{_anz(n('karten'), 'Karte', 'Karten nebeneinander')}, Höhe {s.get('hoehe', 'inhalt')}" + (", Kopfband" if s.get("kopf") else "")
                + (f", hervorgehoben (Accent Green): {'; '.join(hervor)}" if hervor else ""))
    if typ == "timeline":
        return (f"Gantt (Skala {s.get('skala', 'automatisch')}), {_anz(n('zeilen'), 'Zeile', 'Zeilen')}, Heute-Linie"
                + (f", {n('marker')} Marker" if s.get("marker") else "")
                + (f", {_anz(n('schatten'), 'graue Zone', 'graue Zonen')}" if s.get("schatten") else "")
                + (", Faktenleiste unten" if s.get("fakten") else "")
                + (f", {_anz(n('boxen'), 'Box', 'Boxen')} unten" if s.get("boxen") else ""))
    if typ == "massnahmen":
        return f"Terminliste mit {_anz(n('zeilen'), 'Zeile', 'Zeilen')}: Termin links in Dark Green, Was fett, Details rechts"
    if typ == "tabelle":
        return f"echte Tabelle, {_anz(n('kopf'), 'Spalte', 'Spalten')} × {_anz(n('zeilen'), 'Zeile', 'Zeilen')}, Kopf in Dark Green"
    if typ == "kennzahlen":
        return _anz(n("kacheln"), "Kennzahl-Kachel", "Kennzahl-Kacheln")
    if typ == "diagramm":
        return f"echtes Diagramm ({s.get('art', 'saeulen')}), {_anz(n('reihen'), 'Reihe', 'Reihen')}" + (", Fazitkarte rechts" if s.get("fazit") else "")
    if typ == "fluss":
        return f"Datenfluss in {_anz(n('spalten'), 'Spalte', 'Spalten')} mit Pfeilen"
    if typ == "frei":
        return f"{_anz(n('elemente'), 'freies Element', 'freie Elemente')} ({', '.join(dict.fromkeys(str(e.get('form')) for e in s.get('elemente', [])))})"
    if typ == "layout":
        return f"Layout des Masters mit {_anz(n('felder'), 'Textfeld', 'Textfeldern')}" + (f", {_anz(n('bilder'), 'Bild', 'Bildern')}" if s.get("bilder") else "")
    return {"titel": "Titelfolie", "kapitel": "Kapiteltrenner", "agenda": "Agenda", "text": "Aufzählung im Inhaltsplatzhalter",
            "bild_text": "Bild im Bildplatzhalter, Text daneben", "kernaussage": "dunkle Botschaftsfolie",
            "abschluss": "dunkle Abschlussfolie"}.get(typ, typ)


def _gestaltung_spec(s, f):
    teile = [f"Layout „{f['layout']}“", _art(s)]
    if s.get("band"):
        teile.append(f"Band {s['band'].get('stil', 'dunkel') if isinstance(s['band'], dict) else 'dunkel'} unten")
    icons = _sammeln(s, {"icon"})
    bilder = _sammeln(s, {"bild", "datei"})
    if icons:
        teile.append("Icons " + ", ".join(icons))
    if bilder:
        teile.append("Bilder " + ", ".join(bilder))
    return " · ".join(teile)


def _gestaltung_deck(f, fs=None):
    zahl = {}
    for fo in f.get("formen", []):
        if fo["name"] != "Kernaussage":
            zahl[fo["art"]] = zahl.get(fo["art"], 0) + 1
    teile = [f"Layout „{f['layout']}“"]
    if zahl:
        teile.append(", ".join(_anz(n, *FORMART.get(a, (a, a))) for a, n in sorted(zahl.items(), key=lambda x: -x[1])))
    if any(t["form"] == "Kernaussage" for t in f["texte"]):
        teile.append("Band unten")
    if "basis" in (fs or {}):
        teile.append(_basis_aenderung(fs))
    elif "bib" in (fs or {}):
        teile.append(_bib_fuellung(fs))
    return " · ".join(teile)


def _bib_fuellung(fs):
    gefuellt = [x for x in (_anz(len(fs["texte"]), "Text", "Texte") if fs.get("texte") else "",
                            _anz(len(fs["bilder"]), "Bild", "Bilder") if fs.get("bilder") else "",
                            "Diagrammdaten" if fs.get("daten") else "", "Tabelle" if fs.get("tabellen") else "",
                            _anz(len(fs["entfernen"]), "Form", "Formen") + " entfernt" if fs.get("entfernen") else "",
                            _anz(len(fs["aendern"]), "Form", "Formen") + " geändert" if fs.get("aendern") else "",
                            _anz(len(fs["elemente"]), "Form", "Formen") + " ergänzt" if fs.get("elemente") else "") if x]
    return f"aus der Folienbibliothek (Folie {fs['bib']})" + (", gefüllt: " + ", ".join(gefuellt) if gefuellt else "")


def _basis_aenderung(fs):
    geaendert = [x for x in (_anz(len(fs["ersetzen"]), "Ersetzung", "Ersetzungen") if fs.get("ersetzen") else "",
                             "Platzhalter" if fs.get("platzhalter") else "", "Titel" if fs.get("titel") else "",
                             _anz(len(fs["aendern"]), "Form", "Formen") + " geändert" if fs.get("aendern") else "",
                             _anz(len(fs["elemente"]), "Form", "Formen") + " ergänzt" if fs.get("elemente") else "",
                             "Farben angeglichen" if fs.get("farben_angleichen") else "") if x]
    return "beim Bau geändert: " + ", ".join(geaendert) if geaendert else "unverändert aus der Basis"


# ----------------------------------------------------------------- Inhalt aus dem Deck (Basisfolien, PPTX ohne Spec)
def _ein(t):
    return re.sub(r"\s+", " ", t).strip()


def _aus_deck(z, f):
    """Text der Formen in Dokumentreihenfolge; einzeilige Formen auf gleicher Höhe (Zeile einer Liste, Skala) als eine
    Zeile mit „|“ – so bleiben Terminlisten und Raster lesbar."""
    zeile, mitte = [], None
    for t in f["texte"]:
        if t["form"] == "Kernaussage":
            continue
        pos = t.get("pos") or [None] * 4
        m = pos[1] + pos[3] / 2 if pos[1] is not None and pos[3] is not None else None
        if len(t["absaetze"]) == 1 and not t["absaetze"][0]["ebene"] and m is not None:
            if not (zeile and abs(m - mitte) < 0.1):
                if zeile:
                    z.append("- " + " | ".join(zeile))
                zeile, mitte = [], m
            zeile.append(_ein(t["absaetze"][0]["t"]))
            continue
        if zeile:
            z.append("- " + " | ".join(zeile))
            zeile = []
        for p in t["absaetze"]:
            z.append("  " * p["ebene"] + "- " + _ein(p["t"]))
    if zeile:
        z.append("- " + " | ".join(zeile))
    for tb in f["tabellen"]:
        if tb["zeilen"]:
            _tabelle(z, tb["zeilen"][0], tb["zeilen"][1:])
    for d in f["diagramme"]:
        z.append(f"Diagramm ({d['art'].lower()}):")
        _tabelle(z, [""] + [r["name"] for r in d["reihen"]],
                 [[k] + [r["werte"][i] if i < len(r["werte"]) else "" for r in d["reihen"]]
                  for i, k in enumerate(d["kategorien"])])
    for b in f["bilder"]:
        z.append(f"- Bild „{b['form']}“")
    for u in f["unbekannt"]:
        z.append(f"- (nicht gelesen: {meldung(Unbekannt(**u))})")


def _spaltenweise(f):
    """Texte einer Bibliotheksfolie spaltenweise lesen (links nach rechts, je Spalte von oben nach unten); Formen mit
    einem Absatz ohne Einrückung – die Bibliothek setzt Kopfboxen auf Ebene 5."""
    def lage(t):
        pos = t.get("pos") or [0, 0, 0, 0]
        return round((pos[0] or 0) * 2) / 2, pos[1] or 0
    texte = []
    for t in sorted(f["texte"], key=lage):
        if len(t["absaetze"]) == 1:
            t = dict(t, absaetze=[dict(t["absaetze"][0], ebene=0)])
        texte.append(t)
    return dict(f, texte=texte)


def _kernaussage_deck(f):
    return next((_ein(" ".join(p["t"] for p in t["absaetze"])) for t in f["texte"] if t["form"] == "Kernaussage"), "")


# ----------------------------------------------------------------- Baustand
def fingerabdruck(sl, f=None):
    """Fingerabdruck einer Folie: Layout, Titel, Formen (Name, Lage, Text), Tabellen, Diagramme, Bilder und Notizen,
    Endung „~“ = ausgeblendet. Ändert sich mit Text, Lage, Bild oder Sichtbarkeit, nicht beim bloßen Speichern und nicht
    mit der Fußzeile."""
    f = f or folie_lesen(sl, 0, formen=True)
    teile = [f["layout"], f["titel"], f["notizen"], f["tabellen"], f["diagramme"],
             [(b["form"], b["bytes"]) for b in f["bilder"]],
             [(x["name"], x["pos"], ["".join(p) for p in x.get("absaetze", [])]) for x in f["formen"]]]
    h = hashlib.sha1(json.dumps(teile, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()[:10]
    return h + ("~" if f["ausgeblendet"] else "")


def fingerabdruecke(prs):
    return [fingerabdruck(sl) for sl in prs.slides]


def _ohne(fp):
    return fp.rstrip("~")


def _block(text):
    """Abschnitt einer Folienbeschreibung: (bau, stand, {Foliennummer: Zeilen unter der Überschrift})."""
    a, e = text.find(START), text.find(ENDE)
    if a < 0 or e < a:
        return None, None, {}
    werte = dict(re.findall(r"\b(bau|stand)=([0-9a-f~,]+)", text[a:text.find("\n", a)]))
    teile, nr = {}, None
    for zeile in text[a:e].splitlines()[1:]:
        m = re.match(r"#{2,3} Folie (\d+): ", zeile)
        if m:
            nr = int(m.group(1))
            teile[nr] = []
        elif nr is not None:
            teile[nr].append(zeile)
    for zeilen in teile.values():
        while zeilen and not zeilen[-1].strip():
            zeilen.pop()
    liste = lambda k: werte[k].split(",") if werte.get(k) else None  # noqa: E731
    return liste("bau"), liste("stand"), teile


def _lesen(doc):
    try:
        return Path(doc).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def baustand(doc):
    """Fingerabdrücke des letzten Baus aus der Folienbeschreibung, None ohne Baustand."""
    return _block(_lesen(doc))[0]


def frueher(*docs):
    """Beschreibungen früherer Stände je Fingerabdruck (ohne Sichtbarkeit): {fp: Zeilen}. Erste Datei hat Vorrang."""
    out = {}
    for doc in docs:
        bau, stand, teile = _block(_lesen(doc)) if doc else (None, None, {})
        fps = stand or bau or []
        for nr, zeilen in teile.items():
            if 0 < nr <= len(fps) and zeilen:
                out.setdefault(_ohne(fps[nr - 1]), zeilen)
    return out


def nachtraeglich(pptx, bau):
    """Folien, die sich seit dem Bau geändert haben (Nummern ab 1), oder [] wenn das Deck dem Baustand entspricht."""
    jetzt = fingerabdruecke(vorlage.oeffnen(pptx))
    out = [i for i, (a, b) in enumerate(zip(jetzt, bau), 1) if a != b]
    return out + list(range(min(len(jetzt), len(bau)) + 1, max(len(jetzt), len(bau)) + 1))


def aenderungen(alt, neu):
    """Vergleich zweier Baustände: (geänderte oder neue Folien, Zahl unveränderter, Zahl entfallener)."""
    rest = list(alt or [])
    geaendert = []
    for i, h in enumerate(neu, 1):
        if h in rest:
            rest.remove(h)
        else:
            geaendert.append(i)
    return geaendert, len(neu) - len(geaendert), max(0, len(rest) - len(geaendert))


# ----------------------------------------------------------------- Dokument
def _rel(pfad, ordner):
    try:
        return Path(os.path.relpath(pfad, ordner)).as_posix()
    except ValueError:  # anderes Laufwerk (Windows)
        return str(pfad)


def _uebernehmen(zeilen, fs, f, sichtbar):
    """Beschreibung einer unveränderten Folie aus einem früheren Stand übernehmen; Kopfzeile und Herkunft neu."""
    typ = next((t for t in zeilen[0].split(" · ") if t.startswith("Typ ")), "") if zeilen else ""
    herkunft = f"Basisfolie {fs['basis']}" if "basis" in fs else f"Bibliotheksfolie {fs['bib']}" if "bib" in fs else ""
    out = [" · ".join(x for x in (herkunft, typ, sichtbar) if x)]
    for zl in zeilen[1:]:
        if zl.startswith("Gestaltung: ") and "basis" in fs:
            zl = re.sub(r" · (unverändert aus der Basis|beim Bau geändert: .*)$", "", zl) + " · " + _basis_aenderung(fs)
        elif zl.startswith("Gestaltung: ") and "bib" in fs:
            zl = re.sub(r" · aus der Folienbibliothek .*$", "", zl) + " · " + _bib_fuellung(fs)
        elif zl.startswith("Beschreibung: ") and fs.get("beschreibung"):
            continue
        out.append(zl)
        if zl.startswith("Gestaltung: ") and fs.get("beschreibung"):
            out.append(f"Beschreibung: {_klar(fs['beschreibung'])}")
    return out


def abschnitt(prs, pptx, ziel, spec=None, spec_pfad=None, bau=None, ebene=1, alt=None):
    """Abschnitt der Folienbeschreibung (mit Marken) und die Fingerabdrücke des Decks. prs = fertiges Deck; spec
    (optional), Folien 1:1 zum Deck; bau = Baustand für die Startmarke; alt = frueher() für unveränderte Folien."""
    spec, alt = spec or {}, alt or {}
    ordner = Path(ziel).parent
    folien = spec.get("folien") or [None] * len(prs.slides)
    gelesen = [folie_lesen(sl, i, formen=True) for i, sl in enumerate(prs.slides, 1)]
    stand = [fingerabdruck(sl, f) for sl, f in zip(prs.slides, gelesen)]
    h = "#" * ebene
    titel = _klar(spec.get("fusszeile")) or next((f["titel"] for f in gelesen if f["titel"]), "") or Path(pptx).stem
    backup = sum(1 for f in gelesen if f["ausgeblendet"])
    weg = (f"Spec `{_rel(spec_pfad, ordner)}` ändern (nur die betroffenen Folien), dann `bippt bauen`" if spec_pfad
           else f"keine Spec – Deck ändern, dann `bippt beschreiben {Path(pptx).name}`")
    z = [f"{START}{' bau=' + ','.join(bau) if bau else ''} stand={','.join(stand)} – von bippt gepflegt bis zur Endmarke; "
         "Text außerhalb bleibt -->",
         f"{h} {titel}", "",
         f"Folienbeschreibung zu `{_rel(pptx, ordner)}` · Stand {dt.date.today().strftime('%d.%m.%Y')} · "
         f"{len(gelesen)} Folien, {len(gelesen) - backup} sichtbar" + (f", {backup} im Backup (ausgeblendet)" if backup else ""),
         f"Ändern: {weg}. Inhalt und Gestaltung je Folie stehen hier; das Deck nur für Einzelheiten ansehen "
         "(`bippt rendern --folien n`, `bippt analyse --formen --folien n`)."]
    if spec.get("zweck"):
        z.append(f"Zweck: {_klar(spec['zweck'])}")
    if spec.get("quellen"):
        q = spec["quellen"] if isinstance(spec["quellen"], list) else [spec["quellen"]]
        z.append("Quellen: " + ", ".join(f"`{x}`" for x in q))
    if spec.get("basis"):
        z.append(f"Basis: `{_name(spec['basis'])}` (unveränderte Basisfolien aus deren Folienbeschreibung, sonst aus dem Deck)")
    for f, fs, fp in zip(gelesen, folien, stand):
        neu = bool(fs) and "basis" not in fs and "bib" not in fs
        fs = fs or {}
        sichtbar = "Backup (ausgeblendet)" if f["ausgeblendet"] else "sichtbar"
        z += ["", f"{h}# Folie {f['nr']}: {f['titel'] or _klar(fs.get('titel')) or '(ohne Titel)'}"]
        if not neu and alt.get(_ohne(fp)):
            z += _uebernehmen(alt[_ohne(fp)], fs, f, sichtbar)
            continue
        art = (f"Basisfolie {fs['basis']}" if "basis" in fs else f"Bibliotheksfolie {fs['bib']}" if "bib" in fs
               else f"Typ `{fs.get('typ', 'text')}`" if neu else "")
        z.append(" · ".join(x for x in (art, sichtbar) if x))
        z.append(f"Gestaltung: {_gestaltung_spec(fs, f) if neu else _gestaltung_deck(f, fs)}")
        if fs.get("beschreibung"):
            z.append(f"Beschreibung: {_klar(fs['beschreibung'])}")
        z.append("")
        kern = _band(fs["band"]) if neu and fs.get("band") else _kernaussage_deck(f)
        if kern:
            z += [f"**Kernaussage:** {kern}", ""]
        n = len(z)
        if neu:
            INHALT.get(fs.get("typ", "text"), lambda zz, s: _aus_deck(zz, f))(z, fs)
            if fs.get("quelle"):
                z.append(f"Quelle: {_klar(fs['quelle'])}")
        else:
            _aus_deck(z, _spaltenweise(f) if "bib" in fs else f)
        if len(z) == n and z[-1] == "":
            z.pop()
        if f["notizen"]:
            z += ["", "Notizen: " + re.sub(r"\s*\n\s*", " / ", f["notizen"])]
    return "\n".join(z).rstrip() + "\n" + ENDE + "\n", stand


def schreiben(prs, pptx, ziel, spec=None, spec_pfad=None, bau=None, gebaut=False, weitere=()):
    """Abschnitt in die Folienbeschreibung schreiben: ersetzen, an eine Vorlage anhängen oder neue Datei.
    gebaut: prs ist das eben gebaute Deck (Baustand = Stand); weitere: Beschreibungen, aus denen unveränderte Folien
    übernommen werden (z. B. die der Basis). Rückgabe (Meldung, Fingerabdrücke)."""
    ziel = Path(ziel)
    alt = _lesen(ziel) if ziel.is_file() else ""
    a, e = alt.find(START), alt.find(ENDE)
    vorne, hinten = (alt[:a], alt[e + len(ENDE):].lstrip("\n")) if a >= 0 and e > a else (alt.rstrip() + "\n\n" * bool(alt.strip()), "")
    if gebaut:
        bau = fingerabdruecke(prs)
    text, stand = abschnitt(prs, pptx, ziel, spec, spec_pfad, bau, 2 if vorne.strip() else 1, frueher(ziel, *weitere))
    art = "aktualisiert" if a >= 0 and e > a else ("an die Vorlage angehängt" if alt.strip() else "neu")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(vorne + text + hinten, encoding="utf-8")
    return f"BESCHRIEBEN: {ziel} ({art})", stand


def ziel_fuer(spec, spec_pfad, pptx):
    """Pfad der Folienbeschreibung: "dokument" der Spec (relativ zur Spec, nur .md), sonst <ausgabe>.md."""
    d = spec.get("dokument")
    if isinstance(d, str) and d.lower().endswith(".md"):
        q = Path(d).expanduser()
        return (q if q.is_absolute() else Path(spec_pfad).parent / q), None
    warnung = f"dokument „{d}“ ist kein Pfad zu einer .md-Datei – Folienbeschreibung neben der PPTX" if d else None
    return Path(pptx).with_suffix(".md"), warnung


def beschreiben(pptx, ausgabe=None):
    """`bippt beschreiben <pptx> [-o md|-]`: Folienbeschreibung aus dem Deck (ohne Spec), z. B. für ein fremdes oder von
    Hand geändertes Deck. Unveränderte Folien behalten ihre Beschreibung; der Baustand bleibt stehen, damit
    `bippt bauen` Handänderungen weiter erkennt."""
    pptx = Path(pptx)
    if pptx.suffix.lower() == ".json":
        raise SystemExit("bippt beschreiben liest das Deck: Pfad der PPTX angeben (bippt bauen schreibt die "
                         "Beschreibung aus der Spec)")
    prs = vorlage.oeffnen(pptx)
    ziel = Path(ausgabe) if ausgabe and ausgabe != "-" else pptx.with_suffix(".md")
    if ausgabe == "-":
        print(abschnitt(prs, pptx, ziel, alt=frueher(ziel))[0], end="")
        return 0
    bau = baustand(ziel)
    meldung_, stand = schreiben(prs, pptx, ziel, bau=bau)
    print(meldung_)
    if bau and bau != stand:
        hand = [i for i, (x, y) in enumerate(zip(stand, bau), 1) if x != y] + list(range(len(bau) + 1, len(stand) + 1))
        print(f"  HINWEIS Seit dem letzten Bau geändert: Folie {', '.join(map(str, hand))} – aus dem Deck beschrieben; "
              "die Spec kennt diese Änderungen nicht")
    return 0
