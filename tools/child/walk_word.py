"""Child process of ppp guide: builds a Word guide from walk files and their pictures. Argument: options as JSON."""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

from docx import Document
from docx.shared import Emu

from ppplib import walk as W

FIGURE = {"de": "Abbildung", "en": "Figure"}
ROLE = {"de": "Rolle", "en": "Role"}
EMU_PER_PIXEL = 9525


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


def picture(doc, file: Path) -> None:
    section = doc.sections[-1]
    usable = section.page_width - section.left_margin - section.right_margin
    pixels = struct.unpack(">I", file.read_bytes()[16:20])[0]  # width in the PNG header
    doc.add_picture(str(file), width=Emu(min(usable, pixels * EMU_PER_PIXEL)))


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


def chapter(doc, root: Path, path: Path, figure: str, count: int, role_word: str) -> int:
    walk = W.load(path)
    folder = W.out_dir(root, path, walk)
    proven(folder, path, walk)
    doc.add_heading(walk.get("title") or W.name_of(path), level=1)
    if W.role_name(walk):
        paragraph(doc, f"**{role_word}: {W.role_name(walk)}**")
    if walk.get("intro"):
        paragraph(doc, walk["intro"])
    number = 0
    for step in walk["steps"]:
        if step.get("text"):
            number += 1
            paragraph(doc, f"{number}. {step['text']}")
        if "shot" in step:
            file = folder / f"{step['shot']}.png"
            if not file.is_file():
                raise FileNotFoundError(f"{file} is missing; run ppp walk {path.name} first")
            picture(doc, file)
            count += 1
            caption = f"{figure} {count}" + (f": {step['caption']}" if step.get("caption") else "")
            paragraph(doc, caption, "Caption")
            for mark_number, mark in enumerate(step.get("marks", []), 1):
                label = W.mark_parts(mark)[2]
                if label:
                    paragraph(doc, f"({mark_number}) {label}")
    return count


def main(options: dict) -> int:
    root = Path(options["root"])
    doc = Document(options["template"]) if options.get("template") else Document()
    if options.get("title"):
        paragraph(doc, options["title"], "Title")
    figure = FIGURE.get(options.get("language", "en"), FIGURE["en"])
    role_word = ROLE.get(options.get("language", "en"), ROLE["en"])
    count = 0
    try:
        for name in options["walks"]:
            count = chapter(doc, root, Path(name), figure, count, role_word)
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
    print(f"{target}: {len(options['walks'])} chapters, {count} pictures")
    return 0


if __name__ == "__main__":
    sys.exit(main(json.loads(sys.argv[1])))
