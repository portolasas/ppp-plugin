# Office – PowerPoint, Word, Excel

Legend: [B] confirmed · [D] library/platform documentation · [O] open (check the Brand Hub)

## 0. Template first
An official BI template (`.potx`/`.dotx`, Brand Hub or company template gallery) always wins: open it
(`Presentation(<template>)`, `Document(<template>)`) and only fill content. Build styling yourself only
when no template exists or the output is generated (reports, exports). Fonts: Boehringer Forward is
usually installed on company PCs – name it first with Segoe UI as fallback in the theme; generated files
from other machines use Segoe UI.

## 1. Values (from tokens.json)
```python
BI = {"DarkGreen": "08312A", "AccentGreen": "00E47C", "White": "FFFFFF", "LightGray": "F6F5F3",
      "WarmGray": "E5E3DE", "Black": "000000", "DarkBlue": "076D7E", "LightBlue": "D2F2F7",
      "MediumYellow": "FFD03D", "DarkRed": "86251B", "LightRed": "F5CDB9", "DarkViolet": "5D4495",
      "Gray5": "B7B6B2", "Gray7": "5C5B59", "SignalGreen": "1EAD1B", "SignalYellow": "FF8413", "SignalRed": "F62B2B"}
CHART = ["08312A", "00E47C", "076D7E", "6AD2E2", "E18600", "EE6541", "5D4495", "928BDE", "86251B", "FFD03D"]
LINES_ON_WHITE = ["08312A", "076D7E", "5D4495", "86251B", "EE6541", "E18600"]  # no Accent Green as thin line
```

## 2. PowerPoint (python-pptx) [D]
Whole decks (new, new version of an existing deck, conversion into the BI design): agent/skill **bi-ppt**
(same plugin – generator `bippt` on the BI master v2.1 with status, timeline, process … slide types). The rules
below are for single slides or other generators. Traffic lights = signal colors with a legend.
Master v2.1 (binding): only theme and custom colors, **no tints/shades** (lighter/darker x %) and no standard colors.
Chart series in PowerPoint follow the master's automatic sequence, theme accents 1–6:
`PPT_CHART = ["08312A", "00E47C", "C5C3EE", "FFE667", "F58A68", "A3E5EE"]`; lines on white use `LINES_ON_WHITE`.
- 16:9 (`prs.slide_width = Inches(13.333)`, `prs.slide_height = Inches(7.5)`); margins ≥ 0.5 in.
- Title slide: full Dark Green area, title White, one Accent Green highlight (line or keyword) on the
  Dark Green; logo Accent Green or White variant.
- Content slide: White or Light Gray background, title Dark Green 28 pt, body Dark Green/Black 14–18 pt,
  Dark Green band (≤ 1.1 in) optional; logo Dark Green variant on light areas.
- One message per slide; tables with Dark Green header row and White text, rows White/Light Gray.
```python
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt
def rgb(h): return RGBColor.from_string(h)
band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.1))
band.fill.solid(); band.fill.fore_color.rgb = rgb(BI["DarkGreen"]); band.line.fill.background()
run = band.text_frame.paragraphs[0].add_run(); run.text = "Titel"
run.font.size = Pt(28); run.font.color.rgb = rgb(BI["White"]); run.font.name = "Segoe UI"
# chart series: bars → fill, lines → line colour
for i, s in enumerate(chart.plots[0].series):
    s.format.fill.solid(); s.format.fill.fore_color.rgb = rgb(PPT_CHART[i % len(PPT_CHART)])
```

## 3. Word (python-docx) [D]
- Template for handbooks, guides and other generated documents: [BI_Vorlage_Handbuch.docx](../../../vorlagen/BI_Vorlage_Handbuch.docx)
  – the styles below, A4 landscape so that screenshots stay legible, logo Dark Green top right, footer
  `<title> | ONLY FOR INTERNAL USE | <page>`, the title from the field `TITLE`: set `core_properties.title`. German Word
  found no style "Title" behind `STYLEREF "Title"` and printed an error in the footer. Open it with `Document(<template>)` and
  only fill content; a ppp project copies it to `docs/handbook/template.docx` for `ppp guide --template`.
  `bippt wordvorlage <BrandDesign> -o vorlagen/BI_Vorlage_Handbuch.docx` builds it anew.
- python-docx's default template gives headings and body theme fonts (`asciiTheme`), which Word takes before the font
  name: remove them, as `bippt wordvorlage` does, or Calibri shows instead of Boehringer Forward.
- Headings Dark Green (H1 22 pt, H2 18 pt, H3 14 pt), body Black 11 pt, links Dark Blue.
- Tables: header row Dark Green fill + White bold text, body rows alternate White/Light Gray, borders Warm Gray.
- Info boxes: Light Gray fill; warnings Medium Yellow fill with Dark Green text.
```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor
doc.styles["Heading 1"].font.color.rgb = RGBColor.from_string(BI["DarkGreen"])
def shade(cell, hexcolor):
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), hexcolor)
    cell._tc.get_or_add_tcPr().append(shd)
```

## 4. Excel (openpyxl) [D]
- Header row: Dark Green fill, White bold Segoe UI; freeze panes below the header; filters on.
- Body: no fills except status columns; thin Warm Gray borders; numbers right-aligned with fixed formats.
- Status colors via conditional formatting with the role pairs (fill + text): success Accent Green +
  Dark Green, info Light Blue + Dark Blue, warning Medium Yellow + Dark Green, error Light Red + Dark Red.
```python
from openpyxl.styles import Border, Font, PatternFill, Side
head_fill = PatternFill(fill_type="solid", fgColor=BI["DarkGreen"])
head_font = Font(name="Segoe UI", bold=True, color=BI["White"])
thin = Side(style="thin", color=BI["WarmGray"]); border = Border(bottom=thin, top=thin, left=thin, right=thin)
for c in ws[1]: c.fill, c.font = head_fill, head_font
ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
for i, s in enumerate(chart.series): s.graphicalProperties.solidFill = CHART[i % len(CHART)]
```

## 5. Check before handing over
Template used where it exists · fonts Boehringer Forward/Segoe UI · no Accent Green text on light
backgrounds · chart colors in order · logo variant fits the background · file opens without repair prompt.
