"""PPTX → PDF → PNG (+ Kontaktbogen) zur Sichtprüfung.

Wege (der erste verfügbare gewinnt, oder --weg):
- Windows: PowerPoint per COM (PowerShell inline, ohne Fenster, keine Dialoge)
- macOS:   PowerPoint per AppleScript. PowerPoint ist sandboxed: es arbeitet NUR im festen render_dir
           (Standard ~/Documents/BI-PPT-Render). Beim allerersten Mal fragt PowerPoint „Dateizugriff erteilen“ →
           „Auswählen…“ → Ordner bestätigen. Danach nie wieder. Nie andere Ordner an PowerPoint geben.
- LibreOffice (soffice --headless), falls installiert – Schriften/Effekte weichen leicht ab.
PNG braucht pymupdf; ohne pymupdf bleibt es beim PDF.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from . import konfig


def _ps_quote(s):
    return "'" + str(s).replace("'", "''") + "'"


def _win_powerpoint(pptx, pdf):
    ps = (
        "$ErrorActionPreference='Stop';"
        "$pp=New-Object -ComObject PowerPoint.Application;"
        f"$p=$pp.Presentations.Open({_ps_quote(pptx)},$true,$false,$false);"
        f"$p.SaveAs({_ps_quote(pdf)},32);$p.Close();"
        "if($pp.Presentations.Count -eq 0){$pp.Quit()};"
        "[void][Runtime.InteropServices.Marshal]::ReleaseComObject($pp)"
    )
    exe = shutil.which("powershell") or shutil.which("pwsh")
    r = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not Path(pdf).is_file():
        raise RuntimeError("PowerPoint (COM): " + (r.stderr or r.stdout).strip()[:400])


def _pp_laeuft():
    r = subprocess.run(["pgrep", "-x", "Microsoft PowerPoint"], capture_output=True)
    return r.returncode == 0


def _pp_fremde_praesentationen():
    r = subprocess.run(["osascript", "-e", 'with timeout of 20 seconds', "-e",
                        'tell application "Microsoft PowerPoint" to get name of every presentation', "-e", "end timeout"],
                       capture_output=True, text=True)
    namen = [n.strip() for n in r.stdout.strip().split(",") if n.strip() and n.strip() != "missing value"]
    return [n for n in namen if not n.startswith("r_")]


def _pp_beenden():
    """quit kann direkt nach close verloren gehen – bis zu 3 Versuche, je bis 10 s warten."""
    for _ in range(3):
        time.sleep(1)
        subprocess.run(["osascript", "-e", 'tell application "Microsoft PowerPoint" to quit'], capture_output=True, timeout=60)
        for _ in range(20):
            if not _pp_laeuft():
                return True
            time.sleep(0.5)
    print("Hinweis: PowerPoint ließ sich nicht beenden – vor dem nächsten Render von Hand schließen.")
    return False


def _mac_powerpoint(pptx, pdf, render_dir, neustart=True):
    """PowerPoint für Mac (16.x) bettet die Boehringer-Schriften nur beim ERSTEN PDF-Export einer Sitzung korrekt ein;
    ab dem zweiten fehlen Buchstaben in Titeln (getestet 2026-10-08). Darum je Export frischer Start und danach
    beenden. Sind eigene Präsentationen offen, wird nicht neu gestartet und der Render abgebrochen (--erzwingen)."""
    if _pp_laeuft():
        fremd = _pp_fremde_praesentationen()
        if fremd and neustart:
            raise RuntimeError("PowerPoint hat offene Präsentationen (" + ", ".join(fremd) + "). Ein zweiter PDF-Export "
                               "in derselben Sitzung verstümmelt Schriften. Präsentationen schließen und erneut rendern "
                               "oder --erzwingen (Ergebnis dann auf fehlende Buchstaben prüfen).")
        if not fremd:
            _pp_beenden()
    rd = Path(render_dir).expanduser()
    rd.mkdir(parents=True, exist_ok=True)
    for alt in list(rd.glob("r_*.p*")) + list(rd.glob("~$r_*")):  # Reste abgebrochener Läufe
        if time.time() - alt.stat().st_mtime > 600:
            alt.unlink(missing_ok=True)
    tag = uuid.uuid4().hex[:8]
    ein, aus = rd / f"r_{tag}.pptx", rd / f"r_{tag}.pdf"
    shutil.copy2(pptx, ein)
    skript = f'''
with timeout of 600 seconds
  tell application "Microsoft PowerPoint"
    repeat with alt in (get every presentation)
      if name of alt starts with "r_" then close alt saving no
    end repeat
    open POSIX file "{ein}"
    set p to presentation "{ein.name}"
    save p in POSIX file "{aus}" as save as PDF
    close p saving no
  end tell
end timeout'''
    try:
        r = subprocess.run(["osascript", "-e", skript], capture_output=True, text=True, timeout=660)
        if r.returncode != 0 or not aus.is_file():
            msg = (r.stderr or r.stdout).strip()
            if "-50" in msg or "Parameterfehler" in msg or "nicht lesen" in msg:
                msg += (f"\nPowerPoint hat keinen Zugriff auf {rd}. Einmalig: Dialog „Dateizugriff erteilen“ › "
                        "„Auswählen…“ › Ordner bestätigen. Dann erneut rendern.")
            raise RuntimeError("PowerPoint (AppleScript): " + msg[:600])
        shutil.move(str(aus), pdf)
    finally:
        ein.unlink(missing_ok=True)
        if not _pp_fremde_praesentationen():
            _pp_beenden()


SCHRIFT_ERSATZ = "Liberation Sans"  # im Sandbox von Copilot vorhanden, 4 % schmaler als Boehringer Forward; sonst nähme LibreOffice DejaVu, gut 10 % breiter


def schrift_konfig(ziel, einbinden="/etc/fonts/fonts.conf"):
    """Fontconfig-Datei: Fehlen die Boehringer-Schriften, gilt Liberation Sans. accept, nicht prefer: Sind sie installiert, bleiben sie.
    Die Schriften selbst stecken in der Vorlage MTX-komprimiert; LibreOffice 25.2 liest sie nicht."""
    familien = ("Boehringer Forward Head", "Boehringer Forward Text", "Boehringer Forward Head Md", "Boehringer Forward Text Md",
                "Boehringer Headline", "Boehringer Text")
    alias = "".join(f'<alias binding="same"><family>{f}</family><accept><family>{SCHRIFT_ERSATZ}</family></accept></alias>' for f in familien)
    Path(ziel).write_text(f'<?xml version="1.0"?><fontconfig><include ignore_missing="yes">{einbinden}</include>{alias}</fontconfig>',
                          encoding="utf-8")
    return ziel


def _libreoffice(pptx, pdf):
    exe = shutil.which("soffice") or shutil.which("libreoffice") or \
        ("/Applications/LibreOffice.app/Contents/MacOS/soffice" if Path("/Applications/LibreOffice.app").exists() else None)
    if not exe:
        raise RuntimeError("LibreOffice nicht installiert")
    with tempfile.TemporaryDirectory() as td:
        # eigenes Profil: im Sandbox von Copilot ist das Benutzerverzeichnis nicht sicher beschreibbar
        r = subprocess.run([exe, f"-env:UserInstallation=file://{td}/profil", "--headless", "--convert-to", "pdf",
                            "--outdir", td, str(pptx)],
                           capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, FONTCONFIG_FILE=schrift_konfig(Path(td) / "schriften.conf")))
        erg = Path(td) / (Path(pptx).stem + ".pdf")
        if r.returncode != 0 or not erg.is_file():
            raise RuntimeError("LibreOffice: " + (r.stderr or r.stdout)[:300])
        shutil.move(str(erg), pdf)


def wege():
    w = []
    if konfig.IST_WIN:
        w.append("powerpoint")
    if konfig.IST_MAC and Path("/Applications/Microsoft PowerPoint.app").exists():
        w.append("powerpoint")
    if shutil.which("soffice") or shutil.which("libreoffice") or Path("/Applications/LibreOffice.app").exists():
        w.append("libreoffice")
    return w


def _alle_einblenden(pptx, ziel):
    from pptx import Presentation
    p = Presentation(str(pptx))
    for s in p.slides:
        if s._element.get("show") is not None:
            del s._element.attrib["show"]
    p.save(str(ziel))


def rendern(pptx, ausgabe=None, dpi=80, alle=False, weg=None, folien=None, blatt=True, erzwingen=False):
    """Gibt (pdf, [png…], kontaktbogen) zurück. alle=True rendert auch ausgeblendete Folien."""
    pptx = Path(pptx).resolve()
    cfg = konfig.laden()
    aus = Path(ausgabe) if ausgabe else pptx.parent / ("_render_" + pptx.stem)
    aus.mkdir(parents=True, exist_ok=True)
    pdf = aus / (pptx.stem + ".pdf")
    quelle = pptx
    tmp = None
    if alle:
        tmp = Path(tempfile.mkdtemp()) / pptx.name
        _alle_einblenden(pptx, tmp)
        quelle = tmp
    fehler = []
    for w in ([weg] if weg else wege()):
        try:
            t0 = time.time()
            if w == "powerpoint" and konfig.IST_WIN:
                _win_powerpoint(quelle, pdf)
            elif w == "powerpoint":
                _mac_powerpoint(quelle, pdf, cfg["render_dir"], neustart=not erzwingen)
            else:
                _libreoffice(quelle, pdf)
            print(f"PDF ({w}, {time.time() - t0:.0f}s): {pdf}")
            break
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
            fehler.append(f"{w}: {e}")
    else:
        raise SystemExit("Rendern nicht möglich:\n  " + "\n  ".join(fehler or ["kein Renderweg (PowerPoint/LibreOffice) gefunden"]))
    if tmp:
        shutil.rmtree(tmp.parent, ignore_errors=True)
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            print("Hinweis: pymupdf fehlt – nur PDF")
            return pdf, [], None
    doc = pymupdf.open(str(pdf))
    pngs = []
    for i, page in enumerate(doc, 1):
        if folien and i not in folien:
            continue
        ziel = aus / f"folie_{i:02d}.png"
        page.get_pixmap(dpi=dpi).save(str(ziel))
        pngs.append(ziel)
    print(f"PNG: {len(pngs)} Folien in {aus}")
    bogen = None
    if blatt and len(pngs) > 1:
        try:
            from PIL import Image
            ims = [Image.open(p) for p in pngs]
            w, h = ims[0].size
            sp = 2 if len(ims) <= 8 else 3
            fak = 0.5 if sp == 2 else 0.4
            tw, th = int(w * fak * 1.6), int(h * fak * 1.6)
            reihen = (len(ims) + sp - 1) // sp
            bild = Image.new("RGB", (tw * sp + 8 * (sp - 1), th * reihen + 8 * (reihen - 1)), "white")
            for k, im in enumerate(ims):
                bild.paste(im.resize((tw, th)), ((k % sp) * (tw + 8), (k // sp) * (th + 8)))
            bogen = aus / "kontaktbogen.png"
            bild.save(str(bogen))
            print(f"Kontaktbogen: {bogen}")
        except ImportError:
            pass
    return pdf, pngs, bogen
