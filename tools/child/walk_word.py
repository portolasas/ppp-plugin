"""Child process of ppp guide: builds a Word guide from a handbook in Markdown or from walk files, with the walks'
pictures. Argument: options as JSON."""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu

from ppplib import walk as W

FIGURE = {"de": "Abbildung", "en": "Figure"}
ROLE = {"de": "Rolle", "en": "Role"}
EMU_PER_PIXEL = 9525
WALK = re.compile(r"^<!--\s*walk:\s*(\S+)\s*-->$")
TOC = re.compile(r"^<!--\s*toc\s*-->$")
IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)$")
HEADINGS = {"#": "Title", "##": 1, "###": 2, "####": 3}


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


def plain(text: str) -> str:
    """Markdown inline marks Word does not need: code ticks and links, which keep their text."""
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text.replace("`", ""))


def picture(doc, file: Path) -> None:
    section = doc.sections[-1]
    usable = section.page_width - section.left_margin - section.right_margin
    pixels = struct.unpack(">I", file.read_bytes()[16:20])[0]  # width in the PNG header
    doc.add_picture(str(file), width=Emu(min(usable, pixels * EMU_PER_PIXEL)))


def figure(doc, file: Path, state: dict, caption: str = "") -> None:
    picture(doc, file)
    state["count"] += 1
    paragraph(doc, f"{state['figure']} {state['count']}" + (f": {caption}" if caption else ""), "Caption")


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


def steps(doc, root: Path, path: Path, walk: dict, state: dict) -> None:
    """The walk's numbered texts, pictures with caption and the legend of the frames."""
    folder = W.out_dir(root, path, walk)
    proven(folder, path, walk)
    number = 0
    for step in walk["steps"]:
        if step.get("text"):
            number += 1
            paragraph(doc, f"{number}. {step['text']}")
        if "shot" in step:
            file = folder / f"{step['shot']}.png"
            if not file.is_file():
                raise FileNotFoundError(f"{file} is missing; run ppp walk {path.name} first")
            figure(doc, file, state, step.get("caption", ""))
            for mark_number, mark in enumerate(step.get("marks", []), 1):
                label = W.mark_parts(mark)[2]
                if label:
                    paragraph(doc, f"({mark_number}) {label}")


def chapter(doc, root: Path, path: Path, state: dict) -> None:
    walk = W.load(path)
    doc.add_heading(walk.get("title") or W.name_of(path), level=1)
    if W.role_name(walk):
        paragraph(doc, f"**{state['role']}: {W.role_name(walk)}**")
    if walk.get("intro"):
        paragraph(doc, walk["intro"])
    steps(doc, root, path, walk, state)
    state["walks"] += 1


def table(doc, rows: list[str]) -> None:
    cells = [[plain(c.strip()) for c in row.strip().strip("|").split("|")] for row in rows
             if not re.fullmatch(r"\|?[\s:|-]+\|?", row.strip())]
    width = max(len(r) for r in cells)
    grid = doc.add_table(rows=len(cells), cols=width)
    try:
        grid.style = "Table Grid"
    except (KeyError, ValueError):
        pass
    for r, row in enumerate(cells):
        for c, text in enumerate(row):
            cell = grid.cell(r, c)
            cell.text = ""
            for number, part in enumerate(re.split(r"\*\*", text)):
                if part:
                    cell.paragraphs[0].add_run(part).bold = r == 0 or number % 2 == 1


def markdown(doc, root: Path, source: Path, state: dict) -> None:
    """Headings, paragraphs, lists and tables become Word; a line <!-- walk: <name> --> takes the steps and pictures of
    walks/<name>.json beside the handbook, a line ![caption](file) a picture of its own, <!-- toc --> a table of contents
    that Word fills on F9."""
    lines = source.read_text(encoding="utf-8").splitlines()
    text: list[str] = []
    item = {"style": None, "open": False}  # a list item goes on in indented lines
    chapter = {"title": "", "numbered": False, "walk": False}

    def close_chapter() -> None:
        """The clicks come from the walk alone; numbered steps beside it say the same twice and drift apart."""
        if chapter["numbered"] and chapter["walk"]:
            state["warnings"].append(f"chapter '{chapter['title']}' has numbered steps beside its walk line; "
                                     "keep the clicks in the walk and purpose, prerequisites, result and help in the text")
        chapter.update(numbered=False, walk=False)

    def flush() -> None:
        if text:
            paragraph(doc, plain(" ".join(text)), item["style"])
            text.clear()
        item.update(style=None, open=False)

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
            steps(doc, root, path, W.load(path), state)
            state["walks"] += 1
            chapter["walk"] = True
        elif TOC.match(line):
            flush()
            field = OxmlElement("w:fldSimple")
            field.set(qn("w:instr"), 'TOC \\o "1-3" \\h \\z \\u')
            doc.add_paragraph()._p.append(field)
        elif line.startswith("<!--"):
            flush()
            comment = "-->" not in line
        elif not line:
            flush()
        elif line.split(" ", 1)[0] in HEADINGS and " " in line:
            flush()
            close_chapter()
            mark, title = line.split(" ", 1)
            chapter["title"] = plain(title)
            if HEADINGS[mark] == "Title":
                paragraph(doc, plain(title), "Title")
            else:
                doc.add_heading(plain(title), level=HEADINGS[mark])
                state["sections"] += 1
        elif line.startswith("|"):
            flush()
            rows = [line]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            table(doc, rows)
        elif IMAGE.match(line):
            flush()
            caption, name = IMAGE.match(line).groups()
            figure(doc, source.parent / name, state, caption)
        elif re.match(r"^([-*]|\d+\.) ", line):
            flush()
            bullet = line[0] in "-*"
            text.append(line[2:] if bullet else line)
            item.update(style="List Bullet" if bullet else None, open=True)
            chapter["numbered"] = chapter["numbered"] or not bullet
        elif item["open"] and raw[:1].isspace():
            text.append(line)
        else:
            if item["open"]:
                flush()
            text.append(line)
    flush()
    close_chapter()


def main(options: dict) -> int:
    root = Path(options["root"])
    doc = Document(options["template"]) if options.get("template") else Document()
    if options.get("title"):
        paragraph(doc, options["title"], "Title")
    language = options.get("language", "en")
    state = {"count": 0, "walks": 0, "sections": 0, "warnings": [],
             "figure": FIGURE.get(language, FIGURE["en"]), "role": ROLE.get(language, ROLE["en"])}
    try:
        if options.get("markdown"):
            markdown(doc, root, Path(options["markdown"]), state)
        else:
            for name in options["walks"]:
                chapter(doc, root, Path(name), state)
    except FileNotFoundError as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 2
    target = Path(options["out"])
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        doc.save(str(target))
    except PermissionError:
        print(f"ERROR: {target} cannot be written; is it open in Word?", file=sys.stderr)
        return 2
    if options.get("markdown"):
        print(f"{target}: {state['sections']} sections, {state['walks']} walks, {state['count']} pictures")
        for warning in state["warnings"]:
            print(f"WARN: {warning}")
    else:
        print(f"{target}: {state['walks']} chapters, {state['count']} pictures")
    return 0


if __name__ == "__main__":
    sys.exit(main(json.loads(sys.argv[1])))
