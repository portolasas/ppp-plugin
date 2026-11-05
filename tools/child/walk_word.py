"""Child process of ppp guide: builds a Word guide from a handbook in Markdown or from walk files, with the walks'
pictures. From one handbook in Markdown it builds the whole handbook, the handbook of one role, a quick guide or an
exercise sheet (options role and kind). Argument: options as JSON."""
from __future__ import annotations

import copy
import json
import re
import struct
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Pt, RGBColor

from ppplib import walk as W

FIGURE = {"de": "Abbildung", "en": "Figure"}
ROLE = {"de": "Rolle", "en": "Role"}
FOR = {"de": "Für", "en": "For"}
SOLUTIONS = {"de": "Lösungen", "en": "Solutions"}
EMU_PER_PIXEL = 9525
PICTURE_SHARE = 0.5  # a picture takes at most this share of the page height, so its step and caption fit beside it
QUICK_CHARS = 3500  # about one page of text; a quick guide above it is no quick guide any more
KEEP_ROWS = 15  # tables up to this many rows stay on one page
SILENT_ACTIONS = 3  # more clicks in a row without a text leave the reader without the way
WALK = re.compile(r"^<!--\s*walk:\s*(\S+)\s*-->$")
TOC = re.compile(r"^<!--\s*toc\s*-->$")
FOR_LINE = re.compile(r"^<!--\s*for:\s*(.+?)\s*-->$")
FOR_END = re.compile(r"^<!--\s*/for\s*-->$")
KIND_LINE = re.compile(r"^<!--\s*kind:\s*(handbook|quick|exercises)\s*-->$")
AVOID_LINE = re.compile(r"^<!--\s*avoid:\s*(.+?)\s*-->$")
SOLUTION_LINE = re.compile(r"^<!--\s*solution\s*-->$")
PAGEBREAK = re.compile(r"^<!--\s*pagebreak\s*-->$")
IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)$")
HEADINGS = {"#": "Title", "##": 1, "###": 2, "####": 3}
LEVEL = {"#": 0, "##": 1, "###": 2, "####": 3}
TITLE_FIELD = re.compile(r'^\s*(STYLEREF\s+"?(Title|Titel)"?|TITLE)\s*$', re.I)
GREY = RGBColor(0x5C, 0x5B, 0x59)


def paragraph(doc, text: str, style: str | None = None):
    """A paragraph with **bold** parts; a style the template lacks falls back to the normal one."""
    try:
        par = doc.add_paragraph(style=style)
    except KeyError:
        par = doc.add_paragraph()
    for number, part in enumerate(re.split(r"\*\*", text)):
        if part:
            par.add_run(part).bold = number % 2 == 1
    return par


def keep_with_next(par) -> None:
    par.paragraph_format.keep_with_next = True


def step_paragraph(doc, number: int, text: str):
    """A numbered step with a hanging indent: the number stands out, the text lines up beside it."""
    par = paragraph(doc, f"{number}. {text}")
    par.paragraph_format.left_indent = Cm(0.75)
    par.paragraph_format.first_line_indent = Cm(-0.75)
    par.paragraph_format.space_before = Pt(6)
    return par


def legend_paragraph(doc, labels: list[tuple[int, str]]):
    """The legend of a picture's frames in one line, set apart from the steps: smaller, grey and indented."""
    par = paragraph(doc, " · ".join(f"({number}) {label}" for number, label in labels))
    par.paragraph_format.left_indent = Cm(0.75)
    par.paragraph_format.space_after = Pt(0)
    for run in par.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = GREY
    return par


def note_paragraph(doc, text: str):
    """A line '> text' as a box: shaded, with a bar on the left, for a note or a warning."""
    par = paragraph(doc, text)
    ppr = par._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    for key, value in (("w:val", "single"), ("w:sz", "24"), ("w:space", "8"), ("w:color", "8C8C8C")):
        left.set(qn(key), value)
    borders.append(left)
    ppr.append(borders)
    shading = OxmlElement("w:shd")
    for key, value in (("w:val", "clear"), ("w:color", "auto"), ("w:fill", "F2F2F2")):
        shading.set(qn(key), value)
    ppr.append(shading)
    par.paragraph_format.left_indent = Cm(0.3)
    return par


def title_fields(doc, title: str) -> None:
    """The title as a document property and in a TITLE field in headers and footers: behind STYLEREF "Title" German Word
    looked for a style "Titel" and printed an error in the footer (GEN-20261104-WIN-02)."""
    doc.core_properties.title = title
    for section in doc.sections:
        for part in (section.header, section.footer, section.first_page_header, section.first_page_footer,
                     section.even_page_header, section.even_page_footer):
            if part.is_linked_to_previous:
                continue  # reading it would add a definition
            for field in part._element.iter(qn("w:fldSimple")):
                if not TITLE_FIELD.match(field.get(qn("w:instr"), "")):
                    continue
                field.set(qn("w:instr"), "TITLE")
                after = field.getnext()
                style = after.find(qn("w:rPr")) if after is not None and after.tag == qn("w:r") else None
                for child in list(field):
                    field.remove(child)
                run, text = OxmlElement("w:r"), OxmlElement("w:t")
                if style is not None:
                    run.append(copy.deepcopy(style))
                text.text = title
                run.append(text)
                field.append(run)
            for instruction in part._element.iter(qn("w:instrText")):
                if TITLE_FIELD.match(instruction.text or ""):
                    instruction.text = " TITLE "


def plain(text: str) -> str:
    """Markdown inline marks Word does not need: code ticks and links, which keep their text."""
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text.replace("`", ""))


def picture(doc, file: Path):
    """The picture as wide as the page allows, but at most PICTURE_SHARE of its height, so it stays beside its step."""
    section = doc.sections[-1]
    usable = section.page_width - section.left_margin - section.right_margin
    high = section.page_height - section.top_margin - section.bottom_margin
    head = file.read_bytes()[16:24]
    pixels, rows = struct.unpack(">II", head)  # width and height in the PNG header
    width = min(usable, pixels * EMU_PER_PIXEL)
    if rows and width * rows / pixels > high * PICTURE_SHARE:
        width = int(high * PICTURE_SHARE * pixels / rows)
    doc.add_picture(str(file), width=Emu(width))
    par = doc.paragraphs[-1]
    keep_with_next(par)
    return par


def figure(doc, file: Path, state: dict, caption: str = "", more: bool = False):
    """Picture and caption on one page; more: a legend follows and stays with them."""
    picture(doc, file)
    state["count"] += 1
    par = paragraph(doc, f"{state['figure']} {state['count']}" + (f": {caption}" if caption else ""), "Caption")
    if more:
        keep_with_next(par)
    return par


def proven(folder: Path, path: Path, walk: dict) -> None:
    """Pictures only from a complete run, for a role only from a session proven as that role."""
    try:
        report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise FileNotFoundError(f"no run of {path.name}; run ppp walk {path.name} first")
    if not report.get("complete"):
        raise FileNotFoundError(f"the last run of {path.name} did not finish; run ppp walk {path.name} again")
    if W.role_name(walk) and report.get("role") != W.role_name(walk):
        raise FileNotFoundError(f"the pictures of {path.name} are not proven as role {W.role_name(walk)}; run ppp walk {path.name} again")


def silent_runs(walk: dict) -> list[tuple[int, int]]:
    """Runs of more than SILENT_ACTIONS clicks or entries without a text: the guide would skip part of the way. Clicks
    on the same control in a row, such as Next in a help, are one action for the reader."""
    runs, start, count, previous = [], 0, 0, None
    for index, step in enumerate(walk["steps"], 1):
        if step.get("text"):
            if count > SILENT_ACTIONS:
                runs.append((start, count))
            count, previous = 0, None
        elif "click" in step or "type" in step:
            target = (step.get("click") or step.get("type"), step.get("nth", 0))
            if target == previous:
                continue
            previous = target
            start = index if count == 0 else start
            count += 1
    if count > SILENT_ACTIONS:
        runs.append((start, count))
    return runs


def steps(doc, root: Path, path: Path, walk: dict, state: dict, pictures: bool = True) -> None:
    """The walk's numbered texts, pictures with caption and the legend of the frames; without pictures for a quick
    guide."""
    folder = W.out_dir(root, path, walk)
    if pictures:
        proven(folder, path, walk)
    for start, count in silent_runs(walk):
        state["warnings"].append(f"walk {path.name}: {count} clicks or entries from step {start} on have no text; "
                                 "the reader cannot follow that part of the way")
    state["texts"].extend(t for s in walk["steps"] for t in [s.get("text", ""), s.get("caption", "")] +
                          [W.mark_parts(m)[2] for m in s.get("marks", [])] if t)
    number, last = 0, None
    for step in walk["steps"]:
        if step.get("text"):
            number += 1
            last = step_paragraph(doc, number, step["text"])
        if "shot" in step and pictures:
            file = folder / f"{step['shot']}.png"
            if not file.is_file():
                raise FileNotFoundError(f"{file} is missing; run ppp walk {path.name} first")
            if last is not None:
                keep_with_next(last)  # the step and the picture of its result on one page
            labels = [W.mark_parts(mark)[2] for mark in step.get("marks", [])]
            figure(doc, file, state, step.get("caption", ""), more=any(labels))
            shown = [(n, label) for n, label in enumerate(labels, 1) if label]
            if shown:
                legend_paragraph(doc, shown)
            last = None


def chapter(doc, root: Path, path: Path, state: dict) -> None:
    walk = W.load(path)
    doc.add_heading(walk.get("title") or W.name_of(path), level=1)
    if W.role_name(walk):
        paragraph(doc, f"**{state['role']}: {W.role_name(walk)}**")
    if walk.get("intro"):
        paragraph(doc, walk["intro"])
    steps(doc, root, path, walk, state)
    state["walks"] += 1


def table(doc, rows: list[str], state: dict | None = None) -> None:
    cells = [[plain(c.strip()) for c in row.strip().strip("|").split("|")] for row in rows
             if not re.fullmatch(r"\|?[\s:|-]+\|?", row.strip())]
    if state is not None:
        state["texts"].extend(" | ".join(row) for row in cells)  # tables count for the checks too
    width = max(len(r) for r in cells)
    body = doc.element.body
    last = body[-2] if len(body) > 1 and body[-1].tag == qn("w:sectPr") else body[-1]
    if last.tag == qn("w:tbl"):
        doc.add_paragraph()  # Word joins two tables that touch into one when it saves
    grid = doc.add_table(rows=len(cells), cols=width)
    grid.autofit = False
    section = doc.sections[-1]
    usable = section.page_width - section.left_margin - section.right_margin
    longest = [max((len(r[c]) if c < len(r) else 0) for r in cells) for c in range(width)]
    weights = [min(max(n, 8), 70) for n in longest]  # a short column stays narrow, a long one does not take all
    shares = [w / sum(weights) for w in weights]
    for c, column in enumerate(grid.columns):
        column.width = Emu(int(usable * shares[c]))
    try:
        grid.style = "Table Grid"
    except (KeyError, ValueError):
        pass
    for r, row in enumerate(cells):
        trpr = grid.rows[r]._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))  # a row stays on one page
        if r == 0:
            trpr.append(OxmlElement("w:tblHeader"))  # the head row repeats on every page
        for c in range(width):
            grid.cell(r, c).width = Emu(int(usable * shares[c]))
        for c, text in enumerate(row):
            cell = grid.cell(r, c)
            cell.text = ""
            for number, part in enumerate(re.split(r"\*\*", text)):
                if part:
                    cell.paragraphs[0].add_run(part).bold = r == 0 or number % 2 == 1
            if len(cells) <= KEEP_ROWS and r < len(cells) - 1:
                cell.paragraphs[0].paragraph_format.keep_with_next = True  # a short table stays on one page


def _roles(text: str) -> list[str]:
    return [r.strip() for r in text.split(",") if r.strip()]


def select(lines: list[str], role: str, kind: str, language: str) -> tuple[list[str], dict]:
    """The lines for one role and one kind of document.

    A line <!-- for: A, B --> right below a heading limits that section with its subsections to these roles; elsewhere it
    opens a block up to <!-- /for -->. A line <!-- kind: quick|exercises --> below a chapter heading (##) puts the chapter
    into the quick guide or the exercise sheet instead of the handbook. In an exercise, <!-- solution --> moves the rest
    of it to the solutions at the end. Without these lines a section is for every role and in the handbook; what comes
    before the first chapter belongs to the handbook. The whole handbook (no role) names the roles below each heading."""
    found = {"roles": set(), "avoid": [], "kinds": set()}
    out: list[str] = []
    solutions: list[str] = []
    stack: list[dict] = []  # open sections: level, roles, kind
    block: set[str] | None = None
    solution = False
    i = 0

    def current() -> dict:
        return stack[-1] if stack else {"level": -1, "roles": None, "kind": "handbook", "chapter": False}

    def wanted() -> bool:
        section = current()
        if section["kind"] != kind:
            return False
        if role and section["roles"] is not None and role not in section["roles"]:
            return False
        return not (role and block is not None and role not in block)

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1
        avoid = AVOID_LINE.match(line)
        if avoid:
            found["avoid"].extend(_roles(avoid.group(1)))
            continue
        mark = line.split(" ", 1)[0]
        if mark in LEVEL and " " in line:
            level = LEVEL[mark]
            solution = False
            block = None
            while stack and stack[-1]["level"] >= level:
                stack.pop()
            parent = current()
            section = {"level": level, "roles": parent["roles"], "kind": parent["kind"], "own": None}
            if level == 1:
                section["kind"] = "handbook"
            j = i
            while j < len(lines) and (not lines[j].strip() or FOR_LINE.match(lines[j].strip()) or KIND_LINE.match(lines[j].strip())):
                attribute = lines[j].strip()
                if FOR_LINE.match(attribute):
                    section["own"] = _roles(FOR_LINE.match(attribute).group(1))
                    found["roles"] |= set(section["own"])
                    own = set(section["own"])
                    section["roles"] = own if parent["roles"] is None else own & parent["roles"]
                elif KIND_LINE.match(attribute) and level <= 1:
                    section["kind"] = KIND_LINE.match(attribute).group(1)
                j += 1
            i = j
            found["kinds"].add(section["kind"])
            if level == 0:
                out.append(raw)  # the title belongs to every document
                continue
            stack.append(section)
            if wanted() and level == 1 and kind != "handbook":
                continue  # the chapter heading of a quick guide or exercise sheet repeats the document title
            if wanted():
                out.append(raw)
                if not role and section["own"]:
                    out.extend(["", f"**{FOR[language]}: {', '.join(section['own'])}**", ""])
            continue
        if FOR_END.match(line):
            block = None
            out.append("")  # a table before and one after stay two tables
            continue
        if FOR_LINE.match(line):
            block = set(_roles(FOR_LINE.match(line).group(1)))
            found["roles"] |= block
            out.append("")
            continue
        if KIND_LINE.match(line):
            continue
        if SOLUTION_LINE.match(line):
            solution = True
            if wanted():
                title = next((l for l in reversed(out) if l.strip().split(" ", 1)[0] in LEVEL), "")
                solutions.extend(["", title.strip() if title else ""])
            continue
        if not wanted():
            continue
        (solutions if solution else out).append(raw)
    out = prune(out)
    if solutions:
        out.extend(["", "<!-- pagebreak -->", f"## {SOLUTIONS[language]}"])
        out.extend("###" + l.strip()[l.strip().index(" "):] if l.strip().split(" ", 1)[0] in LEVEL else l for l in solutions)
    return out, found


def prune(lines: list[str]) -> list[str]:
    """Headings with nothing below them for this role fall away, the title stays."""
    kept: list[str] = []
    seen = [False] * 4  # content since the next heading of each level
    for raw in reversed(lines):
        line = raw.strip()
        mark = line.split(" ", 1)[0]
        if mark in LEVEL and " " in line and LEVEL[mark] > 0:
            level = LEVEL[mark]
            keep = seen[level]
            for deeper in range(level, 4):
                seen[deeper] = False
            for higher in range(1, level):
                seen[higher] = seen[higher] or keep
            if keep:
                kept.append(raw)
            continue
        if line:
            seen = [True] * 4
        kept.append(raw)
    return list(reversed(kept))


def markdown(doc, root: Path, source: Path, state: dict, role: str = "", kind: str = "handbook") -> None:
    """Headings, paragraphs, lists and tables become Word; a line <!-- walk: <name> --> takes the steps and pictures of
    walks/<name>.json beside the handbook, a line ![caption](file) a picture of its own, <!-- toc --> a table of contents
    that Word fills on F9, <!-- pagebreak --> a new page, a line '> text' a shaded box, '- [ ] text' a box to tick."""
    lines, found = select(source.read_text(encoding="utf-8").splitlines(), role, kind, state["language"])
    state["found"] = found
    text: list[str] = []
    item = {"style": None, "open": False, "note": False}  # a list item goes on in indented lines
    chapter = {"title": "", "numbered": False, "walk": False}

    def close_chapter() -> None:
        """The clicks come from the walk alone; numbered steps beside it say the same twice and drift apart."""
        if chapter["numbered"] and chapter["walk"]:
            state["warnings"].append(f"chapter '{chapter['title']}' has numbered steps beside its walk line; "
                                     "keep the clicks in the walk and purpose, prerequisites, result and help in the text")
        chapter.update(numbered=False, walk=False)

    together = {"last": None}  # in an exercise sheet each exercise stays on one page

    def flush() -> None:
        if text:
            joined = plain(" ".join(text))
            state["texts"].append(joined)
            if item["note"]:
                par = note_paragraph(doc, joined)
            else:
                par = paragraph(doc, joined, item["style"])
            if joined.rstrip().rstrip("*").endswith(":") or kind == "exercises":
                keep_with_next(par)  # a lead-in such as "If something goes wrong:" stays with its list
            together["last"] = par
            text.clear()
        item.update(style=None, open=False, note=False)

    i, comment = 0, False
    while i < len(lines):
        raw, line = lines[i], lines[i].strip()
        i += 1
        if comment:
            comment = "-->" not in line
            continue
        include = WALK.match(line)
        if include:
            flush()
            name = include.group(1)
            path = source.parent / name if name.endswith(".json") else source.parent / "walks" / f"{name}.json"
            if not path.is_file():
                raise FileNotFoundError(f"{source.name}: walk {path} not found")
            walk = W.load(path)
            if role and W.role_name(walk) and W.role_name(walk) != role:
                state["notes"].append(f"chapter '{chapter['title']}' shows walk {path.stem} of role {W.role_name(walk)} "
                                      f"in the guide for role {role}")
            steps(doc, root, path, walk, state, pictures=kind != "quick")
            state["walks"] += 1
            chapter["walk"] = True
        elif TOC.match(line):
            flush()
            field = OxmlElement("w:fldSimple")
            field.set(qn("w:instr"), 'TOC \\o "1-3" \\h \\z \\u')
            doc.add_paragraph()._p.append(field)
        elif PAGEBREAK.match(line):
            flush()
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif line.startswith("<!--"):
            flush()
            comment = "-->" not in line
        elif not line:
            flush()
        elif line.split(" ", 1)[0] in HEADINGS and " " in line:
            flush()
            close_chapter()
            if kind == "exercises" and together["last"] is not None:
                together["last"].paragraph_format.keep_with_next = False
            mark, title = line.split(" ", 1)
            chapter["title"] = plain(title)
            if HEADINGS[mark] == "Title":
                if not state.get("title"):  # a --title replaces the handbook's own
                    state["title"] = plain(title) + (f" – {role}" if role else "")
                    paragraph(doc, state["title"], "Title")
            else:
                keep_with_next(doc.add_heading(plain(title), level=HEADINGS[mark]))
                state["sections"] += 1
        elif line.startswith("|"):
            flush()
            rows = [line]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            table(doc, rows, state)
        elif IMAGE.match(line):
            flush()
            caption, name = IMAGE.match(line).groups()
            figure(doc, source.parent / name, state, caption)
        elif line.startswith(">"):
            if not item["note"]:
                flush()
            item.update(note=True, open=False)
            text.append(line[1:].strip())
        elif re.match(r"^([-*]|\d+\.) ", line):
            flush()
            bullet = line[0] in "-*"
            body = line[2:] if bullet else line
            if bullet and re.match(r"^\[[ xX]\] ", body):
                body, bullet = "☐ " + body[4:], False  # a box to tick, as a plain line
            text.append(body)
            item.update(style="List Bullet" if bullet else None, open=True)
            chapter["numbered"] = chapter["numbered"] or bool(re.match(r"^\d+\. ", line))
        elif item["open"] and raw[:1].isspace():
            text.append(line)
        else:
            if item["open"] or item["note"]:
                flush()
            text.append(line)
    flush()
    close_chapter()


def lint(state: dict) -> None:
    """Words the handbook wants to avoid (<!-- avoid: ... -->), in its text and the texts of its walks."""
    terms = state.get("found", {}).get("avoid", [])
    for term in terms:
        pattern = re.compile(rf"(?<!\w){re.escape(term)}", re.I)
        hits = [t for t in state["texts"] if pattern.search(t)]
        if hits:
            sample = re.sub(r"\s+", " ", hits[0])[:80]
            state["warnings"].append(f"'{term}' appears {len(hits)} times, e.g. \"{sample}\"")


def orient(doc, orientation: str) -> None:
    """Portrait or landscape for every section, whatever the template has; margins, header and footer stay."""
    want = WD_ORIENT.PORTRAIT if orientation == "portrait" else WD_ORIENT.LANDSCAPE
    for section in doc.sections:
        width, height = section.page_width, section.page_height
        if (want == WD_ORIENT.PORTRAIT) == (width > height):
            section.page_width, section.page_height = height, width
        section.orientation = want


def main(options: dict) -> int:
    root = Path(options["root"])
    doc = Document(options["template"]) if options.get("template") else Document()
    if options.get("orientation"):
        orient(doc, options["orientation"])
    language = options.get("language", "en")
    role, kind = options.get("role", ""), options.get("kind", "handbook")
    state = {"count": 0, "walks": 0, "sections": 0, "warnings": [], "notes": [], "texts": [], "language": language,
             "figure": FIGURE.get(language, FIGURE["en"]), "role": ROLE.get(language, ROLE["en"])}
    if options.get("title"):
        paragraph(doc, options["title"], "Title")
        state["title"] = options["title"]
    try:
        if options.get("markdown"):
            markdown(doc, root, Path(options["markdown"]), state, role, kind)
        else:
            for name in options["walks"]:
                chapter(doc, root, Path(name), state)
    except FileNotFoundError as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 2
    found = state.get("found")
    if found and role and role not in found["roles"]:
        print(f"ERROR: no section names role {role}; roles in the handbook: {', '.join(sorted(found['roles'])) or 'none'}",
              file=sys.stderr)
        return 2
    if found and kind != "handbook" and kind not in found["kinds"]:
        print(f"ERROR: no chapter has <!-- kind: {kind} -->", file=sys.stderr)
        return 2
    if found and state["sections"] == 0 and not state["texts"]:
        print(f"ERROR: nothing in the handbook for role {role or 'all'} and kind {kind}", file=sys.stderr)
        return 2
    if kind == "quick" and sum(len(t) for t in state["texts"]) > QUICK_CHARS:
        state["warnings"].append(f"the quick guide has {sum(len(t) for t in state['texts'])} characters, more than about "
                                 f"one page ({QUICK_CHARS}); keep the few tasks the role needs at work")
    lint(state)
    if state.get("title"):
        title_fields(doc, state["title"])
    target = Path(options["out"])
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc.save(str(target))
    except PermissionError:
        print(f"ERROR: {target} cannot be written; is it open in Word?", file=sys.stderr)
        return 2
    if options.get("markdown"):
        scope = (f" for role {role}" if role else "") + (f", {kind}" if kind != "handbook" else "")
        print(f"{target}: {state['sections']} sections, {state['walks']} walks, {state['count']} pictures{scope}")
        for note in state["notes"]:
            print(f"NOTE: {note}")
        for warning in state["warnings"]:
            print(f"WARN: {warning}")
    else:
        print(f"{target}: {state['walks']} chapters, {state['count']} pictures")
    return 0


if __name__ == "__main__":
    sys.exit(main(json.loads(sys.argv[1])))
