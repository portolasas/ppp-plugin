#!/usr/bin/env python3
"""bippt – Werkzeug des Agenten BI-PPT im Plugin bi-design. Aufruf mit dem Python, das die Pakete hat:
  macOS:   python3 "<plugin>/tools/bippt.py" <befehl> …
  Windows: python "<plugin>\\tools\\bippt.py" <befehl> …
`bippt umgebung` nennt den Aufruf mit vollem Pfad.

Befehle
  umgebung                     Python, Pakete, Vorlage, Marke, Icons, Renderweg, alte Kopien prüfen
  einrichten                   Python-Pakete installieren (pip --user, kein venv)
  aufraeumen [--ja]            alte Kopien von BI-PPT 1.x und PPP 0.17 im Benutzerordner zeigen bzw. löschen
  konfig [--setze k=v …]       Einstellungen zeigen/setzen (~/.bi-ppt/config.json)
  lesen <datei…> [-o md]       Quellen als Text (vtt, docx, pptx, pdf, xlsx, md)
  analyse <pptx> [--json] [--formen] [--folien 2,5]   Deck knapp beschreiben; --formen: id, Name, Absätze, Läufe für aendern
  typen                        Folientypen auflisten
  icons <begriff…>             Brand-Icons suchen
  katalog [pptx] --folien n,m [-o md]   Formen der Folienbibliothek zum Füllen (id, Art, Lage, Platz, Beispieltext)
  layouts                      Layouts des Masters mit ihren Feldern (Typ layout)
  iconpaket <BrandDesign> -o <json>   alle Icons in eine Datei packen (Skill-Paket für Copilot)
  wordvorlage <BrandDesign> -o <docx> Word-Vorlage im BI-Design (Stile, A4 quer, Logo, Fußzeile) für Handbücher
  bauen <spec.json> [-o pptx] [--erzwingen]   Präsentation bauen, dazu die Folienbeschreibung <ausgabe>.md; bricht ab,
                               wenn das Deck nach dem letzten Bau geändert wurde (--erzwingen: trotzdem überschreiben)
  beschreiben <pptx> [-o md|-] Folienbeschreibung aus dem Deck (ohne Spec, z. B. fremdes oder von Hand geändertes Deck)
  pruefen <pptx> [--woerter N] Brand-Prüfung (Farben, Abstufungen, Schriften, Kontrast, Überlauf, Master)
  rendern <pptx> [--alle] [--dpi N] [--folien 2,5] [--erzwingen]   PDF/PNG/Kontaktbogen zur Sichtprüfung
  umwandeln entwurf|stil <pptx> [-o ziel]            fremdes Deck ins BI-Design
  vorlage <bi-deck.pptx> [-o ziel]                   BI-Vorlage aus einem Deck im BI-Master erzeugen
  neu <ordner> [--name N]      Startgerüst: Spezifikation mit Beispielfolien anlegen
"""
import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass


TOOL = Path(__file__).resolve()
ALTE_KOPIEN = [  # (Pfad im Benutzerordner, Datei darin, Merkmal im Inhalt): Installer von BI-PPT 1.x, PPP 0.17
    (".copilot/agents/bi-ppt.agent.md", "", "BI-PPT"),
    (".copilot/agents/bi-designer.agent.md", "", "BI-Designer"),
    (".copilot/skills/bi-ppt", "SKILL.md", "BI-PPT"),
    (".copilot/skills/bi-ppt-update", "SKILL.md", "BI-PPT"),
    (".copilot/skills/bi-designer", "SKILL.md", "BI-Designer"),
    (".claude/skills/bi-ppt", "SKILL.md", "BI-PPT"),
    (".claude/skills/bi-ppt-update", "SKILL.md", "BI-PPT"),
    (".claude/skills/bi-designer", "SKILL.md", "BI-Designer"),
    (".claude/agents/bi-ppt.md", "", "BI-PPT"),
    (".bi-ppt", "tools/bippt.py", "bippt"),
]


def _aufruf():
    return f'"{sys.executable}" "{TOOL}"'


def _alte_kopien():
    """Kopien im Benutzerordner, die Agent und Skills des Plugins verdecken."""
    from bippt import konfig
    heim = Path(os.environ.get("BIPPT_BENUTZER") or konfig.HEIM)
    treffer = []
    for rel, datei, merkmal in ALTE_KOPIEN:
        ziel = heim / rel
        probe = ziel / datei if datei else ziel
        try:
            if probe.is_file() and merkmal in probe.read_text(encoding="utf-8", errors="replace"):
                treffer.append(ziel)
        except OSError:
            pass
    return treffer


def _umgebung(_):
    import importlib
    from bippt import __version__, konfig
    print(f"bi-design {__version__} · {konfig.rechner()}")
    print(f"  Aufruf  {_aufruf()}")
    ok = sys.version_info >= (3, 9)
    if not ok:
        print(f"  FEHLT   Python ≥ 3.9 (gefunden {sys.version.split()[0]}) – anderes Python nutzen")
    for mod, pflicht in (("pptx", True), ("lxml", True), ("docx", False), ("pymupdf", False), ("PIL", False), ("openpyxl", False)):
        try:
            importlib.import_module(mod)
            print(f"  ok      Paket {mod}")
        except ImportError:
            print(f"  {'FEHLT' if pflicht else 'optional'}  Paket {mod}")
            ok = ok and not pflicht
    if not ok:
        print("          Pakete installieren (nach Zustimmung des Nutzers): bippt einrichten")
    cfg = konfig.laden()
    vl = konfig.vorlage_pfad(cfg)
    print(f"  {'ok' if vl else 'FEHLT':7} Vorlage {vl or '(Plugin neu installieren oder bippt vorlage <BI-Deck>)'}")
    ok = ok and bool(vl)
    bib = konfig.bibliothek_pfad(cfg)
    print(f"  {'ok' if bib else 'WARN':7} Bibliothek {bib or '(fehlt: bippt konfig --setze bibliothek=<Slide Library>)'}")
    from bippt.marke import Marke
    m = Marke()
    print(f"  {'ok' if m.ordner else 'WARN':7} Marke {m.profil} aus {m.ordner or 'Notstand (bi-designer fehlt)'}")
    ar = konfig.asset_root(cfg)
    n_ic = len(list((ar / 'Icons_darkgreen').glob('*.png'))) if ar and (ar / 'Icons_darkgreen').is_dir() else 0
    if not n_ic:
        from bippt.marke import ICON_PAKET, icons_im_paket
        n_ic, ar = icons_im_paket(), ICON_PAKET if ICON_PAKET.is_file() else ar
    print(f"  {'ok' if n_ic else 'WARN':7} Icons {n_ic} in {ar or '(asset_root nicht gesetzt: bippt konfig --setze asset_root=<BrandDesign>)'}")
    from bippt.rendern import wege
    w = wege()
    print(f"  {'ok' if w else 'WARN':7} Rendern über {', '.join(w) or 'nichts (PowerPoint/LibreOffice fehlt) – nur pruefen möglich'}")
    if "powerpoint" in w and konfig.IST_MAC:
        print(f"          render_dir {cfg['render_dir']} (einmalig in PowerPoint freigeben)")
    for p in _alte_kopien():
        print(f"  ALT     {p} (alte Kopie: bippt aufraeumen)")
        ok = False
    print("ERGEBNIS: " + ("OK" if ok else "UNVOLLSTÄNDIG"))
    return 0 if ok else 1


def _einrichten(_):
    befehl = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-U",
              "-r", str(TOOL.parent / "requirements.txt")]
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        befehl.insert(4, "--user")  # kein venv: Gruppenrichtlinien sperren es oft
    print("Ausführen: " + " ".join(f'"{x}"' if " " in x else x for x in befehl), flush=True)
    if subprocess.run(befehl).returncode:
        print("FEHLER: pip gescheitert. Hinter einem Proxy: pip config set global.proxy http://<proxy>:<port>, "
              "dann erneut.")
        return 1
    return _umgebung(None)


def _weg(p):
    def schreibbar(fn, pfad, _):
        os.chmod(pfad, stat.S_IWRITE)
        fn(pfad)
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p, onerror=schreibbar)
    else:
        p.unlink()


def _aufraeumen(a):
    from bippt import konfig
    treffer = _alte_kopien()
    if not treffer:
        print("Keine alten Kopien gefunden.")
        return 0
    if not a.ja:
        for p in treffer:
            print(f"  gefunden  {p}")
        print("Diese Kopien verdecken Agent und Skills des Plugins. Löschen mit: bippt aufraeumen --ja")
        return 1
    if konfig.ALT and konfig.ALT.is_file() and not konfig.DATEI.is_file():
        konfig.speichern(konfig.laden())
        print(f"  übernommen  {konfig.ALT} → {konfig.DATEI}")
    for p in treffer:
        _weg(p)
        print(f"  gelöscht  {p}")
    print("Fertig. VS Code: Developer: Reload Window; Claude Code: neue Sitzung.")
    return 0


def _konfig(a):
    from bippt import konfig
    cfg = konfig.laden()
    for kv in a.setze or []:
        k, _, v = kv.partition("=")
        cfg[k.strip()] = v.strip()
    if a.setze:
        konfig.speichern(cfg)
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
    return 0


def _lesen(a):
    from bippt.lesen import lesen
    teile = []
    for d in a.dateien:
        teile.append(f"# Quelle: {Path(d).name}\n\n{lesen(d)}")
    txt = "\n\n".join(teile)
    if a.o:
        Path(a.o).write_text(txt, encoding="utf-8")
        print(f"{a.o}: {len(txt)} Zeichen")
    else:
        print(txt)
    return 0


def _analyse(a):
    from bippt import analyse
    folien = [int(x) for x in a.folien.split(",")] if a.folien else None
    r = analyse.analyse(a.pptx, formen=a.formen, folien=folien)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=str) if a.json else analyse.als_markdown(r, notizen=not a.ohne_notizen))
    return 0


def _typen(_):
    from bippt.folien import TYPEN
    for n, (fn, lay) in sorted(TYPEN.items()):
        print(f"{n:12} [{lay}]  {(fn.__doc__ or '').strip().splitlines()[0] if fn.__doc__ else ''}")
    return 0


def _icons(a):
    from bippt.marke import Marke
    m = Marke()
    treffer = m.icon_suchen(*a.begriffe)
    print(", ".join(treffer[:60]) or "keine Treffer")
    if len(treffer) > 60:
        print(f"… {len(treffer)} Treffer")
    return 0


def _katalog(a):
    from bippt import bibliothek, konfig
    pptx = a.pptx or konfig.bibliothek_pfad()
    if not pptx:
        print("FEHLT Folienbibliothek: bippt konfig --setze bibliothek=<Slide Library>")
        return 1
    txt = bibliothek.katalog(pptx, [int(x) for x in a.folien.split(",")] if a.folien else None)
    if a.o:
        Path(a.o).write_text(txt, encoding="utf-8")
        print(f"{a.o}: {len(txt)} Zeichen")
    else:
        print(txt)
    return 0


def _layouts(_):
    from bippt import bibliothek, konfig
    print(bibliothek.layouts(konfig.vorlage_pfad()))
    return 0


def _iconpaket(a):
    from bippt.marke import icon_paket_bauen
    print(f"ICONPAKET: {a.o} – {icon_paket_bauen(a.ordner, a.o)} Icons")
    return 0


def _wordvorlage(a):
    from bippt.word import word_vorlage
    print(f"WORDVORLAGE: {word_vorlage(a.ordner, a.o)}")
    return 0


def _bauen(a):
    from bippt.bauen import bauen
    _, w = bauen(a.spec, a.o, erzwingen=a.erzwingen)
    return 0


def _beschreiben(a):
    from bippt.beschreiben import beschreiben
    return beschreiben(a.pptx, a.o)


def _pruefen(a):
    from bippt.pruefen import bericht
    return 1 if bericht(a.pptx, woerter=a.woerter) else 0


def _rendern(a):
    from bippt.rendern import rendern
    folien = [int(x) for x in a.folien.split(",")] if a.folien else None
    rendern(a.pptx, a.o, dpi=a.dpi, alle=a.alle, weg=a.weg, folien=folien, erzwingen=a.erzwingen)
    return 0


def _sichten(a):
    from bippt.sichten import sichten
    folien = [int(x) for x in a.folien.split(",")] if a.folien else None
    return 1 if sichten(a.pptx, a.o, weg=a.weg, folien=folien) else 0


def _umwandeln(a):
    from bippt import umwandeln
    if a.weg == "marke":
        from bippt.designer import marke
        marke(a.pptx, a.o, icons=a.icons, fusszeile=a.fusszeile)
        return 0
    (umwandeln.entwurf if a.weg == "entwurf" else umwandeln.stil)(a.pptx, a.o)
    return 0


def _vorlage(a):
    from bippt import konfig, vorlage
    ziel = Path(a.o) if a.o else konfig.HOME / "vorlagen" / konfig.VORLAGE_NAME
    namen = vorlage.extrahieren(a.pptx, ziel)
    print(f"VORLAGE: {ziel} – {len(namen)} Layouts")
    return 0


def _neu(a):
    ziel = Path(a.ordner)
    ziel.mkdir(parents=True, exist_ok=True)
    beispiel = TOOL.parent.parent / "skills" / "bi-ppt" / "beispiele" / "beispiel.spec.json"
    if not beispiel.is_file():  # Skill-Paket für Copilot: beispiele/ neben tools/
        beispiel = TOOL.parent.parent / "beispiele" / "beispiel.spec.json"
    spec = json.loads(beispiel.read_text(encoding="utf-8"))
    spec["ausgabe"] = f"{a.name}.pptx"
    p = ziel / f"{a.name}.spec.json"
    if p.exists():
        raise SystemExit(f"{p} existiert schon")
    p.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"NEU: {p}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bippt", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("umgebung").set_defaults(fn=_umgebung)
    sub.add_parser("einrichten").set_defaults(fn=_einrichten)
    p = sub.add_parser("aufraeumen"); p.add_argument("--ja", action="store_true"); p.set_defaults(fn=_aufraeumen)
    p = sub.add_parser("konfig"); p.add_argument("--setze", nargs="*"); p.set_defaults(fn=_konfig)
    p = sub.add_parser("lesen"); p.add_argument("dateien", nargs="+"); p.add_argument("-o"); p.set_defaults(fn=_lesen)
    p = sub.add_parser("analyse"); p.add_argument("pptx"); p.add_argument("--json", action="store_true")
    p.add_argument("--ohne-notizen", action="store_true"); p.add_argument("--formen", action="store_true")
    p.add_argument("--folien", help="nur diese Folien, z. B. 3,7")
    p.set_defaults(fn=_analyse)
    sub.add_parser("typen").set_defaults(fn=_typen)
    p = sub.add_parser("icons"); p.add_argument("begriffe", nargs="+"); p.set_defaults(fn=_icons)
    p = sub.add_parser("katalog"); p.add_argument("pptx", nargs="?"); p.add_argument("--folien"); p.add_argument("-o")
    p.set_defaults(fn=_katalog)
    sub.add_parser("layouts").set_defaults(fn=_layouts)
    p = sub.add_parser("iconpaket"); p.add_argument("ordner"); p.add_argument("-o", required=True); p.set_defaults(fn=_iconpaket)
    p = sub.add_parser("wordvorlage"); p.add_argument("ordner"); p.add_argument("-o", required=True); p.set_defaults(fn=_wordvorlage)
    p = sub.add_parser("bauen"); p.add_argument("spec"); p.add_argument("-o")
    p.add_argument("--erzwingen", action="store_true", help="auch ein nach dem Bau geändertes Deck überschreiben")
    p.set_defaults(fn=_bauen)
    p = sub.add_parser("beschreiben"); p.add_argument("pptx"); p.add_argument("-o"); p.set_defaults(fn=_beschreiben)
    p = sub.add_parser("pruefen"); p.add_argument("pptx")
    p.add_argument("--woerter", type=int, default=170, help="Wortgrenze je Folie (Steering 120, Projektteam 200)")
    p.set_defaults(fn=_pruefen)
    p = sub.add_parser("rendern"); p.add_argument("pptx"); p.add_argument("-o"); p.add_argument("--dpi", type=int, default=80)
    p.add_argument("--alle", action="store_true"); p.add_argument("--weg", choices=["powerpoint", "libreoffice"])
    p.add_argument("--folien"); p.add_argument("--erzwingen", action="store_true"); p.set_defaults(fn=_rendern)
    p = sub.add_parser("sichten"); p.add_argument("pptx"); p.add_argument("-o"); p.add_argument("--folien")
    p.add_argument("--weg", choices=["powerpoint", "libreoffice"]); p.set_defaults(fn=_sichten)
    p = sub.add_parser("umwandeln"); p.add_argument("weg", choices=["entwurf", "stil", "marke"]); p.add_argument("pptx")
    p.add_argument("-o"); p.add_argument("--icons", help="marke: JSON {Folie: {id: Brand-Icon}}"); p.add_argument("--fusszeile")
    p.set_defaults(fn=_umwandeln)
    p = sub.add_parser("vorlage"); p.add_argument("pptx"); p.add_argument("-o"); p.set_defaults(fn=_vorlage)
    p = sub.add_parser("neu"); p.add_argument("ordner"); p.add_argument("--name", default="Praesentation"); p.set_defaults(fn=_neu)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
