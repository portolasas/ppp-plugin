"""Word-Vorlage im BI-Design: Stile, Seite, Logo und Fußzeile, ohne Inhalt. Für Handbücher und Anleitungen mit
Bildschirmfotos (ppp guide --template) und andere generierte Word-Dokumente (reference/office.md › Word)."""
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .marke import Marke

THEMA = [qn(f"w:{a}") for a in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme")]


def _feld(absatz, anweisung: str) -> None:
    feld = OxmlElement("w:fldSimple")
    feld.set(qn("w:instr"), anweisung)
    absatz._p.append(feld)


def _ohne_themenschrift(doc) -> None:
    """Word nimmt eine Themenschrift (asciiTheme …) vor dem Schriftnamen; die Standardvorlage setzt sie für Überschriften
    und Grundtext, sonst erschiene Calibri statt der Markenschrift."""
    for rfonts in doc.styles.element.iter(qn("w:rFonts")):
        for a in THEMA:
            rfonts.attrib.pop(a, None)


def word_vorlage(brand_ordner, ziel) -> Path:
    m = Marke()
    farbe = lambda name: RGBColor.from_string(m.c(name))
    doc = Document()
    for stil in doc.styles:
        if getattr(stil, "font", None) is not None:
            stil.font.name = m.schrift_text
    doc.styles["Normal"].font.size = Pt(11)
    doc.styles["Normal"].font.color.rgb = farbe("black")
    for name, groesse in (("Title", 28), ("Heading 1", 22), ("Heading 2", 18), ("Heading 3", 14)):
        f = doc.styles[name].font
        f.name, f.size, f.color.rgb = m.schrift_kopf, Pt(groesse), farbe("darkGreen")
    titel = doc.styles["Title"].element.find(qn("w:pPr"))
    if titel is not None and titel.find(qn("w:pBdr")) is not None:
        titel.remove(titel.find(qn("w:pBdr")))  # blaue Linie der Standardvorlage
    doc.styles["Caption"].font.size = Pt(9)
    doc.styles["Caption"].font.color.rgb = farbe("gray7")
    rahmen = OxmlElement("w:tblBorders")
    for seite in ("top", "left", "bottom", "right", "insideH", "insideV"):
        linie = OxmlElement(f"w:{seite}")
        for k, v in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", m.c("warmGray"))):
            linie.set(qn(f"w:{k}"), v)
        rahmen.append(linie)
    stil = doc.styles["Table Grid"].element
    tabelle = stil.find(qn("w:tblPr"))
    if tabelle is None:
        tabelle = OxmlElement("w:tblPr")
        stil.append(tabelle)
    for alt in tabelle.findall(qn("w:tblBorders")):
        tabelle.remove(alt)
    tabelle.append(rahmen)
    _ohne_themenschrift(doc)

    seite = doc.sections[0]  # quer, damit Bildschirmfotos lesbar bleiben
    seite.orientation = WD_ORIENT.LANDSCAPE
    seite.page_width, seite.page_height = Cm(29.7), Cm(21)
    seite.left_margin = seite.right_margin = seite.top_margin = seite.bottom_margin = Cm(1.5)
    logo = Path(brand_ordner) / "Boehringer Ingelheim Logo" / "Digital_RGB" / "Boehringer_Logo_RGB_Dark_Green.png"
    if not logo.is_file():
        raise SystemExit(f"Logo fehlt: {logo} (BrandDesign-Ordner angeben)")
    kopf = seite.header.paragraphs[0]
    kopf.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    kopf.add_run().add_picture(str(logo), height=Cm(1.0))
    fuss = seite.footer.paragraphs[0]
    _feld(fuss, "TITLE")  # Titel aus den Dokumenteigenschaften: STYLEREF "Title" fand das deutsche Word nicht (ppp GEN-20261104-WIN-02)
    fuss.add_run(" | ONLY FOR INTERNAL USE | ")
    _feld(fuss, "PAGE")
    for r in fuss.runs:
        r.font.size = Pt(9)
        r.font.color.rgb = farbe("gray7")

    for element in list(doc.element.body):
        if element.tag != qn("w:sectPr"):
            doc.element.body.remove(element)
    doc.core_properties.title = doc.core_properties.author = ""
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    doc.save(ziel)
    return ziel
