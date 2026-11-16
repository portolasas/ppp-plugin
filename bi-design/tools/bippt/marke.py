"""Markenprofil laden – Quelle ist der Skill bi-designer im selben Plugin (marken/<profil>/tokens.json, icons.txt).

Suchreihenfolge: $BIPPT_MARKE_DIR, <plugin>/skills/bi-designer/marken, <plugin>/marken (Skill-Paket für Copilot,
Repo portolasas/Agents). Fehlt das Profil, greift ein eingebauter Notstand mit den Kernfarben (Warnung). Neue Marken =
neuer Ordner in bi-designer, hier ist nichts zu ändern.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

from . import PLUGIN, konfig


def _suchpfade():
    env = os.environ.get("BIPPT_MARKE_DIR")
    return ([Path(env)] if env else []) + [PLUGIN / "skills" / "bi-designer" / "marken", PLUGIN / "marken"]


# Notstand, nur wenn das Profil fehlt (Werte = tokens.json 2026-10)
_NOTSTAND = {
    "darkGreen": "08312A", "accentGreen": "00E47C", "white": "FFFFFF", "lightGray": "F6F5F3", "warmGray": "E5E3DE",
    "yellow": "FFE667", "mediumYellow": "FFD03D", "darkYellow": "E18600", "lightBlue": "D2F2F7", "blue": "A3E5EE",
    "mediumBlue": "6AD2E2", "darkBlue": "076D7E", "lightRed": "F5CDB9", "red": "F58A68", "mediumRed": "EE6541",
    "darkRed": "86251B", "lightViolet": "E0E1F6", "violet": "C5C3EE", "mediumViolet": "928BDE",
    "darkViolet": "5D4495", "black": "000000", "lightYellow": "FBF9AA",
    "signalRed": "F62B2B", "signalYellow": "FF8413", "signalGreen": "1EAD1B",
    "gray1": "FAF9F8", "gray3": "EFEEEB", "gray5": "B7B6B2", "gray6": "898885", "gray7": "5C5B59", "gray8": "2E2D2C",
}


ICON_PAKET = PLUGIN / "icons" / "bi_icons.json"  # Skill-Paket für Copilot: 350 Dateien reichen nicht für einzelne Icons
_PAKET = {}


def icon_paket_bauen(root, ziel, groesse=192):
    """Alle Icons aus dem BrandDesign-Ordner in eine JSON-Datei: Die Varianten unterscheiden sich nur in der Farbe, darum
    je Icon eine Alpha-Maske als PNG (Base64) und die Farben der Varianten. Gleiche Quelle ergibt gleiche Bytes."""
    import base64
    import io
    from PIL import Image
    root, icons = Path(root), {}
    farben = {"darkgreen": "08312A", "white": "FFFFFF", "accentgreen": "00E47C", "black": "000000"}
    for datei in sorted((root / "Icons_darkgreen").glob("*.png")):
        maske = Image.open(datei).convert("RGBA").getchannel("A")
        if maske.tobytes() != Image.open(root / "Icons_white" / datei.name).convert("RGBA").getchannel("A").tobytes():
            raise SystemExit(f"Icon {datei.stem}: Varianten unterscheiden sich nicht nur in der Farbe")
        puffer = io.BytesIO()
        maske.resize((groesse, groesse), Image.LANCZOS).save(puffer, "PNG", optimize=True)
        icons[datei.stem] = base64.b64encode(puffer.getvalue()).decode("ascii")
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    Path(ziel).write_text(json.dumps({"farben": farben, "icons": icons}, sort_keys=True), encoding="utf-8")
    return len(icons)


def _aus_paket(name, variante):
    """Icon aus dem Paket als PNG im Temp-Ordner oder None."""
    if not ICON_PAKET.is_file():
        return None
    if not _PAKET:
        _PAKET.update(json.loads(ICON_PAKET.read_text(encoding="utf-8")))
    maske, farbe = _PAKET["icons"].get(name), _PAKET["farben"].get(variante)
    if not maske or not farbe:
        return None
    ziel = Path(tempfile.gettempdir()) / "bippt_icons" / variante / f"{name}.png"
    if not ziel.is_file():
        import base64
        import io
        from PIL import Image
        alpha = Image.open(io.BytesIO(base64.b64decode(maske))).convert("L")
        bild = Image.new("RGBA", alpha.size, tuple(bytes.fromhex(farbe)) + (255,))
        bild.putalpha(alpha)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        bild.save(ziel)
    return ziel


def icons_im_paket():
    """Zahl der Icons im Paket (ohne die Masken im Speicher zu halten, falls schon geladen: aus dem Speicher)."""
    if not ICON_PAKET.is_file():
        return 0
    if not _PAKET:
        _PAKET.update(json.loads(ICON_PAKET.read_text(encoding="utf-8")))
    return len(_PAKET["icons"])


class Marke:
    def __init__(self, profil=None):
        cfg = konfig.laden()
        self.profil = profil or cfg.get("marke") or "boehringer-ingelheim"
        self.ordner = None
        for p in _suchpfade():
            if (p / self.profil / "tokens.json").is_file():
                self.ordner = p / self.profil
                break
        if self.ordner:
            t = json.loads((self.ordner / "tokens.json").read_text(encoding="utf-8"))
            self.farben = {k: v["hex"].lstrip("#").upper() for k, v in t["colors"].items()}
            self.rollen = t.get("roles", {})
            typo = t.get("typography", {})
            self.schrift_kopf = typo.get("brandFonts", {}).get("head", "Segoe UI")
            self.schrift_text = typo.get("brandFonts", {}).get("text", "Segoe UI")
            self.schrift_ersatz = typo.get("fallback", "Segoe UI")
            self.assets = t.get("assets", {})
            ic = self.ordner / "icons.txt"
            self.icons = [z.strip() for z in ic.read_text(encoding="utf-8").splitlines() if z.strip()] if ic.is_file() else []
        else:
            print(f"WARNUNG: bi-designer-Profil '{self.profil}' nicht gefunden – Notstand-Farben. "
                  "Profil in skills/bi-designer/marken/ anlegen.", file=sys.stderr)
            self.farben = dict(_NOTSTAND)
            self.rollen = {"chartSequence": ["darkGreen", "accentGreen", "darkBlue", "mediumBlue", "darkYellow",
                                             "mediumRed", "darkViolet", "mediumViolet", "darkRed", "mediumYellow"]}
            self.schrift_kopf = self.schrift_text = "Boehringer Forward Text"
            self.schrift_ersatz = "Segoe UI"
            self.assets = {"icons": "Icons_<darkgreen|accentgreen|black|white>/<name>.png"}
            self.icons = []
        for k_, v in _NOTSTAND.items():
            if k_.startswith(("signal", "gray")):
                self.farben.setdefault(k_, v)
        self.asset_root = konfig.asset_root(cfg)

    # Kurzformen für den Folienbau
    def c(self, name):
        """Farbe per Token-Name (darkGreen) oder Kürzel (DG) oder Hex."""
        k = KUERZEL.get(name, name)
        if k in self.farben:
            return self.farben[k]
        h = str(name).lstrip("#").upper()
        if len(h) == 6 and all(ch in "0123456789ABCDEF" for ch in h):
            return h
        raise KeyError(f"Unbekannte Farbe '{name}' – nur Token-Namen aus tokens.json")

    @property
    def diagramm_folge(self):
        return [self.farben[n] for n in self.rollen.get("chartSequence", []) if n in self.farben]

    def icon_pfad(self, name, variante="darkgreen"):
        for n in (name, name + " "):  # im Icon-Paket der Marke heißt eine Datei „heart-wave .png“
            if self.asset_root:
                muster = self.assets.get("icons", "Icons_<v>/<name>.png")
                rel = muster.split("<")[0] + variante + "/" + n + ".png"  # "Icons_" + variante + "/" + name
                p = self.asset_root / rel
                if p.is_file():
                    return p
            p = _aus_paket(n, variante)
            if p:
                return p
        return None

    def icon_suchen(self, *begriffe):
        b = [x.lower() for x in begriffe]
        return [i for i in self.icons if all(x in i.lower() for x in b)]

    def erlaubte_farben(self):
        return set(self.farben.values())

    def aus_vorlage(self, prs):
        """Custom Colors des Masters (z. B. Gray 1–8, Signal Red/Yellow/Green) als Tokens ergänzen:
        „Signal Red“ → signalRed. Die Marke bleibt Quelle, die Vorlage ergänzt nur."""
        from lxml import etree
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        for master in prs.slide_masters:
            try:
                x = etree.fromstring(master.part.part_related_by(RT.THEME).blob)
            except KeyError:
                continue
            for cc in x.iter(a + "custClr"):
                name, rgb = cc.get("name"), cc.find(a + "srgbClr")
                if name and rgb is not None:
                    teile = name.split()
                    key = teile[0].lower() + "".join(t.capitalize() for t in teile[1:])
                    self.farben.setdefault(key, rgb.get("val").upper())
        return self


KUERZEL = {
    "DG": "darkGreen", "AG": "accentGreen", "WH": "white", "LG": "lightGray", "WG": "warmGray", "BK": "black",
    "YEL": "yellow", "MYEL": "mediumYellow", "DYEL": "darkYellow", "LYEL": "lightYellow",
    "LBLU": "lightBlue", "BLU": "blue", "MBLU": "mediumBlue", "DBLU": "darkBlue",
    "LRED": "lightRed", "RED": "red", "MRED": "mediumRed", "DRED": "darkRed",
    "LVIO": "lightViolet", "VIO": "violet", "MVIO": "mediumViolet", "DVIO": "darkViolet",
    # aus dem BI-Master v2.1 (Custom Colors); Notstand-Werte, falls die Vorlage fehlt
    "SRED": "signalRed", "SYEL": "signalYellow", "SGRN": "signalGreen",
    "G1": "gray1", "G3": "gray3", "G5": "gray5", "G6": "gray6", "G7": "gray7", "G8": "gray8",
}
