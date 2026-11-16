"""Quellen token-sparsam als Text lesen: .vtt (Teams-Transkript), .docx, .pptx, .pdf, .xlsx, .md/.txt."""
import html
import re
from pathlib import Path


def vtt(pfad):
    t = Path(pfad).read_text(encoding="utf-8", errors="replace")
    teile = re.findall(r"<v ([^>]*)>(.*?)</v>", t, re.S)
    if not teile:  # VTT ohne Sprecher
        zeilen = [z for z in t.splitlines() if z.strip() and "-->" not in z and not z.startswith(("WEBVTT", "NOTE"))
                  and not re.fullmatch(r"[0-9a-f-]{36}(/\d+-\d+)?|\d+", z.strip())]
        return html.unescape(" ".join(zeilen))
    out, letzter = [], None
    for sprecher, txt in teile:
        sprecher = re.sub(r"\s*\(.*?\)|\s+BI[A-Z-]+.*$", "", html.unescape(sprecher)).strip()
        txt = html.unescape(" ".join(txt.split()))
        if sprecher == letzter:
            out[-1] += " " + txt
        else:
            out.append(f"**{sprecher}:** {txt}")
            letzter = sprecher
    return "\n\n".join(out)


def docx(pfad):
    import docx as _docx
    from docx.oxml.ns import qn
    d = _docx.Document(str(pfad))
    out = []
    for el in d.element.body.iterchildren():
        if el.tag == qn("w:p"):
            t = "".join(x.text or "" for x in el.iter(qn("w:t"))).strip()
            if t:
                st = el.find(".//" + qn("w:pStyle"))
                stil = st.get(qn("w:val")) if st is not None else ""
                m = re.search(r"(\d)$", stil or "")
                out.append(("#" * int(m.group(1)) + " " if stil.lower().startswith(("heading", "berschrift")) and m else "") + t)
        elif el.tag == qn("w:tbl"):
            for row in el.iter(qn("w:tr")):
                zellen = [" / ".join("".join(x.text or "" for x in p.iter(qn("w:t"))).strip()
                                     for p in c.iter(qn("w:p")) if "".join(x.text or "" for x in p.iter(qn("w:t"))).strip())
                          for c in row.iter(qn("w:tc"))]
                out.append("| " + " | ".join(zellen) + " |")
    return "\n".join(out)


def pptx(pfad):
    from .analyse import als_markdown, analyse
    return als_markdown(analyse(pfad))


def pdf(pfad):
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    d = pymupdf.open(str(pfad))
    return "\n\n".join(f"--- Seite {i} ---\n{p.get_text().strip()}" for i, p in enumerate(d, 1))


def xlsx(pfad):
    import openpyxl
    wb = openpyxl.load_workbook(str(pfad), data_only=True, read_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"## {ws.title}")
        for row in ws.iter_rows(values_only=True, max_row=200):
            if any(v is not None for v in row):
                out.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    return "\n".join(out)


def lesen(pfad):
    p = Path(pfad)
    fn = {".vtt": vtt, ".docx": docx, ".pptx": pptx, ".potx": pptx, ".pdf": pdf, ".xlsx": xlsx}.get(p.suffix.lower())
    if fn is None:
        return p.read_text(encoding="utf-8", errors="replace")
    return fn(p)
