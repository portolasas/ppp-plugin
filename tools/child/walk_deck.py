"""Child process of ppp guide --kind deck: a compact training deck of one role in the corporate design, from the same
handbook in Markdown as the Word files. It writes the spec of the generator bippt (plugin bi-design) beside the deck and
builds and checks it with bippt when bippt is found; otherwise the spec is the result and bi-ppt builds it.

Rules, the same for every project (ppp-docs, step 9):
- the handbook chapters of the role, then the quick guide as a chapter of its own, then the exercises; the solutions on
  hidden slides after the closing slide;
- a chapter gives a divider with the first sentence of its lead text; a section with a walk gives one task slide: the
  walk picture with the most labelled marks uncropped on the left, on the right the section's lead-ins (**Label:** text),
  the picture's caption, text and legend, and what follows the walk while it fits; a '> **Label:** text' box becomes the
  band below; every step text of the walk, the lists and what did not fit go into the speaker notes;
- a table whose first column holds the roles of the handbook gives one card per role, the reader's own highlighted; any
  other table a table slide, with tiles instead when the section says <!-- deck: tiles -->; three list items a designed
  slide with icons (BI Slide Library 28), two or four items cards, more a text slide; <!-- deck: steps --> makes a list a
  process; paragraphs after a list or table become its band;
- an exercise gives cards from its lead-ins and its boxes to tick, its solution a process of its numbered steps.

Lines <!-- deck: … --> below a heading (after <!-- for: … -->) steer one section or chapter: skip, title <text> ({role}
is replaced), heads <a> | <b> | …, icons <name>, <name>, … (brand icons, bippt icons <term>), ampel G, -, Y, R, … (tiles; - keeps the neutral bar),
steps, tiles, shot <picture id>. Word ignores them. Argument: options as JSON."""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

from ppplib import walk as W
from walk_word import KIND_LINE, LEVEL, SOLUTIONS, proven, select

DECK = re.compile(r"^<!--\s*deck:\s*([a-z]+)\s*(.*?)\s*-->$")
WALK = re.compile(r"^<!--\s*walk:\s*(\S+)\s*-->$")
LABEL = re.compile(r"^\*\*([^*]+?):\*\*\s*(.*)$")
TEXT = {
    "de": {"training": "Schulung für die Rolle {role}", "footer": "Schulung {role}", "your_role": "Ihre Rolle",
           "done_when": "Geschafft, wenn …", "solution": "Lösung zu {title}",
           "solutions": "Lösungen für die Schulungsleitung",
           "solutions_sub": "Ausgeblendet: Sie erscheinen nicht in der Bildschirmpräsentation", "end": "Viel Erfolg",
           "agenda": "Agenda", "steps": "So geht's (alle Schritte der Bildfolge):", "step": "Schritt {n}",
           "left_out": "Nicht auf der Folie:"},
    "en": {"training": "Training for the role {role}", "footer": "Training {role}", "your_role": "your role",
           "done_when": "Done when …", "solution": "Solution to {title}", "solutions": "Solutions for the trainer",
           "solutions_sub": "Hidden: they do not appear in the slide show", "end": "Good luck", "agenda": "Agenda",
           "steps": "How to (all steps of the walk):", "step": "Step {n}", "left_out": "Not on the slide:"},
}
ICONS = ["check-circle", "exclamation-mark-circle", "clock-exclamation-mark", "shield-checkmark", "people", "gears"]
# BI-Master 16:9 in inches: content from x 0.52 to 12.81 and from y 1.45 to 6.45
X0, XW, Y0, Y_END = 0.52, 12.29, 1.45, 6.45
PIC_W, GAP = 8.0, 0.3
COL_X = X0 + PIC_W + GAP
COL_W = X0 + XW - COL_X
AGENDA_NUMBERS, AGENDA_TEXTS = [5, 7, 8, 9, 10, 11, 12, 13], [6, 14, 15, 16, 17, 18, 19, 20]  # library slide 10


# ------------------------------------------------------------------ Markdown -> chapters, sections, blocks
def parse(lines: list[str]) -> list[dict]:
    chapters: list[dict] = []
    target: dict | None = None

    def new_chapter(title: str) -> dict:
        chapters.append({"title": title, "blocks": [], "deck": {}, "sections": []})
        return chapters[-1]

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        mark = line.split(" ", 1)[0]
        if mark in LEVEL and " " in line:
            level, title = LEVEL[mark], line.split(" ", 1)[1].strip()
            if level == 1:
                target = new_chapter(title)
            elif level >= 2:
                chapter = chapters[-1] if chapters else new_chapter("")
                chapter["sections"].append({"title": title, "blocks": [], "deck": {}})
                target = chapter["sections"][-1]
            continue
        if target is None or not line:
            continue
        blocks = target["blocks"]
        if line.startswith("|"):
            rows = [line]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            blocks.append(("table", [[c.strip() for c in r.strip("|").split("|")] for r in rows
                                     if not re.fullmatch(r"\|?[\s:|-]+\|?", r)]))
        elif DECK.match(line):
            key, value = DECK.match(line).groups()
            target["deck"][key] = value or True
        elif WALK.match(line):
            blocks.append(("walk", WALK.match(line).group(1)))
        elif line.startswith("<!--"):
            continue
        elif line.startswith(">"):
            blocks.append(("quote", line.lstrip("> ").strip()))
        elif re.match(r"^[-*] \[[ xX]\] ", line):
            _item(blocks, "check", line[6:])
        elif re.match(r"^[-*] ", line):
            _item(blocks, "ul", line[2:])
        elif re.match(r"^\d+\. ", line):
            _item(blocks, "ol", line.split(" ", 1)[1])
        elif blocks and blocks[-1][0] in ("ul", "ol", "check") and lines[i - 1][:1].isspace():
            blocks[-1][1][-1] += " " + line  # an indented line goes on with its item
        elif line.startswith("!["):
            continue  # a picture of its own stays in Word
        else:
            blocks.append(("p", line))
    return chapters


def _item(blocks: list, kind: str, text: str) -> None:
    if blocks and blocks[-1][0] == kind:
        blocks[-1][1].append(text)
    else:
        blocks.append((kind, [text]))


def of(sec: dict, kind: str) -> list:
    return [value for k, value in sec["blocks"] if k == kind]


def paragraphs(sec: dict) -> list[str]:
    """Paragraphs with text; a bare lead-in such as '**If something goes wrong:**' belongs to its list."""
    return [v for k, v in sec["blocks"] if k == "p" and not (LABEL.match(v) and not LABEL.match(v).group(2))]


def bare(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text.replace("`", ""))


def plain(text: str) -> str:
    return bare(text).replace("**", "")


def first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s", plain(text), maxsplit=1)[0]


def listed(values: object) -> list[str]:
    return [v.strip() for v in re.split(r"\s*[|,]\s*", str(values)) if v.strip()] if values and values is not True else []


def text_height(paras: list[dict], width: float) -> float:
    """Rough height in inches as bippt estimates it (Boehringer Forward, 0.46 em per character)."""
    h = 0.0
    for a in paras:
        g = a.get("groesse", 11)
        n = len(plain(a.get("t", "")))
        h += max(1, math.ceil(n * g * 0.46 / 72 / max(width, 0.3))) * g * 1.12 * 1.2 / 72 + 3 / 72
    return h


def column_widths(rows: list[list[str]]) -> list[float]:
    """As the Word tables: a short column stays narrow, a long one does not take all."""
    width = max(len(r) for r in rows)
    longest = [max((len(plain(r[c])) if c < len(r) else 0) for r in rows) for c in range(width)]
    weights = [min(max(n, 8), 70) for n in longest]
    return [round(XW * w / sum(weights), 2) for w in weights]


def band(texts: list[str], quote: str = "", style: str = "hell") -> dict | None:
    """A '> **Label:** text' box or the paragraphs that close a section, as the band below the slide."""
    if quote:
        m = LABEL.match(quote)
        return {"label": m.group(1) + ":", "text": bare(m.group(2)), "stil": style} if m else {"text": bare(quote), "stil": style}
    if texts:
        joined = " ".join(bare(t) for t in texts)
        m = LABEL.match(joined)
        return {"label": m.group(1) + ":", "text": m.group(2), "stil": style} if m else {"text": joined, "stil": style}
    return None


# ------------------------------------------------------------------ slides
class Deck:
    def __init__(self, root: Path, source: Path, out: Path, role: str, roles: set[str], language: str):
        self.root, self.source, self.out, self.role, self.roles = root, source, out, role, roles
        self.t = TEXT.get(language, TEXT["en"])
        self.warnings: list[str] = []
        self.pictures = 0

    def title(self, sec: dict) -> str:
        own = sec["deck"].get("title")
        return own.replace("{role}", self.role or "") if isinstance(own, str) else plain(sec["title"])

    def slide(self, sec: dict) -> dict:
        if of(sec, "walk"):
            return self.task(sec)
        tables, lists = of(sec, "table"), of(sec, "ul") + of(sec, "ol")
        if tables:
            rows = tables[0]
            names = {plain(r[0]) for r in rows[1:]}
            if self.roles and len(names) >= 2 and names <= self.roles:
                return self.role_cards(sec, rows)
            if sec["deck"].get("tiles"):
                return self.tiles(sec, rows)
            return self.table(sec, rows)
        if lists:
            items = lists[0]
            if sec["deck"].get("steps"):
                return self.process(sec, items)
            if len(items) == 3:
                return self.three(sec, items)
            if 2 <= len(items) <= 4:
                return self.cards(sec, items)
        points = [bare(v) for k, v in sec["blocks"] if k == "p"] + [bare(i) for items in lists for i in items]
        return {"typ": "text", "titel": self.title(sec), "punkte": points or [plain(sec["title"])]}

    def _around(self, sec: dict, kind: str) -> tuple[list[str], list[str]]:
        """Paragraphs before and after the first block of a kind."""
        before, after, seen = [], [], False
        for k, v in sec["blocks"]:
            if k == kind:
                seen = True
            elif k == "p" and not (LABEL.match(v) and not LABEL.match(v).group(2)):
                (after if seen else before).append(v)
        return before, after

    def task(self, sec: dict) -> dict:
        name = of(sec, "walk")[0]
        path = self.source.parent / "walks" / f"{name}.json"
        walk = W.load(path)
        proven(W.out_dir(self.root, path, walk), path, walk)  # the same pictures as in Word: a full run as that role
        shots, steps, last = [], [], ""
        for step in walk["steps"]:
            if step.get("text"):
                steps.append(step["text"])
                last = step["text"]
            if "shot" in step:
                labels = [W.mark_parts(m)[2] for m in step.get("marks", [])]
                shots.append({"id": step["shot"], "caption": step.get("caption", ""), "text": step.get("text") or last,
                              "legend": [(n, lab) for n, lab in enumerate(labels, 1) if lab]})
        if not shots:
            raise FileNotFoundError(f"walk {name} has no picture for its task slide")
        chosen = sec["deck"].get("shot")
        shot = next((s for s in shots if s["id"] == chosen), None) or max(shots, key=lambda s: len(s["legend"]))
        picture = W.out_dir(self.root, path, walk) / f"{shot['id']}.png"
        if not picture.is_file():
            raise FileNotFoundError(f"{picture} is missing; run ppp walk {path.name} first")
        self.pictures += 1
        width, height = _png_size(picture)
        pic_h = min(PIC_W * height / width, Y_END - Y0)

        before, after, notes, lists, boxes, seen, lead = [], [], [], [], [], False, ""
        for kind, value in sec["blocks"]:
            if kind == "walk":
                seen = True
            elif kind == "p":
                m = LABEL.match(value)
                if m and not m.group(2):
                    lead = plain(value)
                    continue
                (after if seen else before).append(value)
            elif kind in ("ul", "ol"):
                lists += [lead or "", *[f"- {plain(v)}" for v in value]]
                lead = ""
            elif kind == "quote":
                boxes.append(value)
            elif kind == "table":
                lists += [" | ".join(plain(c) for c in row) for row in value]
        caution = boxes[0] if boxes else ""

        def column(size: float, keep: int) -> list[dict]:
            paras = [{"t": bare(p), "groesse": size} for p in before]
            paras.append({"t": bare(shot["caption"]), "fett": True, "groesse": size + 1})
            paras.append({"t": bare(shot["text"]), "groesse": size})
            paras += [{"t": f"**{n}**   {bare(lab)}", "groesse": size} for n, lab in shot["legend"]]
            paras += [{"t": bare(p), "groesse": size} for p in after[:keep]]
            return paras

        room = (pic_h if caution else Y_END - Y0) + 0.05
        paras, keep = column(11, len(after)), len(after)
        for keep in range(len(after), -1, -1):
            fitted = next((column(size, keep) for size in (11, 10.5, 10)
                           if text_height(column(size, keep), COL_W - 0.16) <= room), None)
            if fitted:
                paras = fitted
                break
        else:
            paras = column(10, 0)
            self.warnings.append(f"slide '{plain(sec['title'])}': purpose and picture text do not fit beside the picture")
        rel = Path(_relative(picture, self.out.parent))
        slide = {"typ": "frei", "titel": self.title(sec),
                 "elemente": [{"form": "bild", "datei": rel.as_posix(), "x": X0, "y": Y0, "w": PIC_W, "h": pic_h, "ausr": "l"},
                              {"form": "text", "x": COL_X, "y": Y0 - 0.04, "w": COL_W, "h": room, "t": paras,
                               "groesse": paras[0]["groesse"]}],
                 "beschreibung": f"Picture '{plain(shot['caption'])}' of walk {name} on the left; beside it the lead-ins, "
                                 "picture text, legend of the numbers in the picture and what fits of the result"}
        if caution:
            slide["band"] = band([], caution)
        note = [self.t["steps"]] + [f"{i}. {plain(s)}" for i, s in enumerate(steps, 1)]
        rest = [plain(p) for p in after[keep:]] + [plain(b) for b in boxes[1:]] + [l for l in lists if l]
        if rest:
            note += ["", self.t["left_out"], *rest]
        slide["notizen"] = "\n".join(note)
        return slide

    def role_cards(self, sec: dict, rows: list[list[str]]) -> dict:
        head, cards = rows[0], []
        for row in rows[1:]:
            name = plain(row[0])
            card = {"titel": name + (f" ({self.t['your_role']})" if name == self.role else ""),
                    "punkte": [f"**{plain(h)}:** {bare(v)}" for h, v in zip(head[1:], row[1:]) if v]}
            if name == self.role:
                card["hervor"] = True
            cards.append(card)
        slide = {"typ": "karten", "titel": self.title(sec), "karten": cards, "groesse": 12.5,
                 "beschreibung": "One card per role, the reader's own highlighted"}
        if (b := band(self._around(sec, "table")[1])):
            slide["band"] = b
        return slide

    def table(self, sec: dict, rows: list[list[str]]) -> dict:
        before, after = self._around(sec, "table")
        slide = {"typ": "tabelle", "titel": self.title(sec), "kopf": [bare(c) for c in rows[0]],
                 "zeilen": [[bare(c) for c in r] for r in rows[1:]], "breiten": column_widths(rows),
                 "erste_spalte_fett": True}
        boxes = of(sec, "quote")
        if (b := band(before + after, boxes[0] if boxes else "", "dunkel" if before and not after else "hell")):
            slide["band"] = b
        return slide

    def tiles(self, sec: dict, rows: list[list[str]]) -> dict:
        """A small table as tiles with a signal colour bar (<!-- deck: ampel G, -, Y, R -->, - keeps Dark Green), the
        section's paragraphs below them and the caution box as band; drawn as a free slide, because bippt places extra
        shapes on library slides only."""
        lights = listed(sec["deck"].get("ampel"))
        data = rows[1:]
        n = len(data)
        per_row = n if n <= 5 else math.ceil(n / 2)
        lines = math.ceil(n / per_row)
        gap = 0.22
        w = (XW - gap * (per_row - 1)) / per_row
        h = 1.9 if lines == 1 else 1.55
        widest = max(len(plain(r[0])) for r in data)
        size = 22 if widest * 22 * 0.55 / 72 <= w - 0.4 else 18 if widest * 18 * 0.55 / 72 <= w - 0.4 else 15
        elements = []
        for i, row in enumerate(data):
            x, y = X0 + (i % per_row) * (w + gap), Y0 - 0.1 + (i // per_row) * (h + gap)
            light = lights[i] if i < len(lights) else "-"
            elements += [{"form": "flaeche", "x": x, "y": y, "w": w, "h": h, "fill": "LG"},
                         {"form": "flaeche", "x": x, "y": y, "w": w, "h": 0.07,
                          "fill": {"G": "SGRN", "Y": "SYEL", "R": "SRED"}.get(light, "DG")},
                         {"form": "text", "x": x + 0.15, "y": y + 0.2, "w": w - 0.3, "h": 0.5, "t": plain(row[0]),
                          "groesse": size, "fett": True},
                         {"form": "text", "x": x + 0.15, "y": y + 0.72, "w": w - 0.3, "h": 0.3,
                          "t": plain(row[1]) if len(row) > 1 else "", "groesse": 12, "fett": True},
                         {"form": "text", "x": x + 0.15, "y": y + 1.02, "w": w - 0.3, "h": h - 1.07,
                          "t": " · ".join(plain(c) for c in row[2:] if c), "groesse": 10.5}]
        boxes = of(sec, "quote")
        before, after = self._around(sec, "table")
        top = Y0 - 0.1 + lines * (h + gap) + 0.1
        bottom = Y_END - (0.44 + 0.15 if boxes or after else 0)
        shown, rest = [], []
        for t in before + (after if boxes else []):
            para = {"t": bare(t), "groesse": 13}
            (shown if not rest and text_height(shown + [para], XW - 0.16) <= bottom - top else rest).append(para)
        if shown:
            elements.append({"form": "text", "x": X0, "y": top, "w": XW, "h": bottom - top, "t": shown, "groesse": 13})
        slide = {"typ": "frei", "titel": self.title(sec), "elemente": elements,
                 "beschreibung": f"{n} tiles with a signal colour bar, the explanation below"}
        if (b := band([], boxes[0]) if boxes else band(after)):
            slide["band"] = b
        if rest:
            slide["notizen"] = "\n".join(plain(p["t"]) for p in rest)
        return slide

    def process(self, sec: dict, items: list[str]) -> dict:
        heads = listed(sec["deck"].get("heads"))
        before, after = self._around(sec, "ul" if of(sec, "ul") else "ol")
        steps = [{"ueber": self.t["step"].format(n=n), "titel": heads[n - 1] if n <= len(heads) else "", "punkte": [bare(item)]}
                 for n, item in enumerate(items, 1)]
        slide = {"typ": "prozess", "titel": self.title(sec), "schritte": steps, "groesse": 13, "kopf_groesse": 14}
        if before:
            m = LABEL.match(before[0])
            slide["kopf"] = {"label": m.group(1) + ":", "text": bare(m.group(2))} if m else {"label": "", "text": bare(before[0])}
        if (b := band(after)):
            slide["band"] = b
        return slide

    def three(self, sec: dict, items: list[str]) -> dict:
        heads, icons = listed(sec["deck"].get("heads")), listed(sec["deck"].get("icons")) or ICONS[:3]
        texts, pictures = {}, {}
        for n, (item, tid, iid) in enumerate(zip(items, (5, 6, 7), (4, 2, 3))):
            texts[str(tid)] = ([f"**{heads[n]}**"] if n < len(heads) else []) + [bare(item)]
            pictures[str(iid)] = f"icon:{icons[n % len(icons)]}"
        before, after = self._around(sec, "ul" if of(sec, "ul") else "ol")
        slide = {"bib": 28, "titel": self.title(sec), "texte": texts, "bilder": pictures,
                 "beschreibung": "Three columns with brand icons (BI Slide Library 28)"}
        if (b := band(after, style="dunkel")):
            slide["elemente"] = [{"form": "band", **b}]
        if before:
            slide["notizen"] = "\n".join(plain(p) for p in before)
        return slide

    def cards(self, sec: dict, items: list[str]) -> dict:
        heads, icons = listed(sec["deck"].get("heads")), listed(sec["deck"].get("icons")) or ICONS
        split = all(":" in plain(i)[:40] for i in items) and not heads
        cards = []
        for n, item in enumerate(items):
            title, text = (plain(item).split(":", 1) if split else (heads[n] if n < len(heads) else "", item))
            cards.append({"titel": title.strip(), "akzent": "DG", "icon": icons[n % len(icons)], "text": bare(text).strip()})
        before, after = self._around(sec, "ul" if of(sec, "ul") else "ol")
        slide = {"typ": "karten", "titel": self.title(sec), "karten": cards, "groesse": 14}
        if before:
            slide["kopf"] = {"label": "", "text": " ".join(bare(p) for p in before)}
        if (b := band(after, style="dunkel")):
            slide["band"] = b
        return slide

    def exercise(self, sec: dict) -> dict:
        cards = []
        for kind, value in sec["blocks"]:
            m = LABEL.match(value) if kind == "p" else None
            if m and m.group(2):
                cards.append({"titel": m.group(1), "akzent": "DG", "text": bare(m.group(2))})
            elif kind == "check":
                cards.append({"titel": self.t["done_when"], "akzent": "DG", "icon": "clipboard-checkmarks",
                              "punkte": [bare(v) for v in value]})
        if len(cards) >= 2:
            cards[1].pop("akzent")
            cards[1]["hervor"] = True  # the task itself
        if cards:
            cards[0]["icon"] = "flag"
        return {"typ": "karten", "titel": plain(sec["title"]), "karten": cards, "groesse": 13}

    def solution(self, sec: dict) -> dict:
        title = self.t["solution"].format(title=plain(sec["title"]))
        steps = of(sec, "ol")
        if steps and len(steps[0]) <= 6:
            return {"typ": "prozess", "titel": title, "groesse": 13, "kopf_groesse": 13,
                    "schritte": [{"titel": self.t["step"].format(n=n), "punkte": [bare(s)]} for n, s in enumerate(steps[0], 1)]}
        points = [bare(v) for k, v in sec["blocks"] if k == "p"] + [bare(i) for items in of(sec, "ol") + of(sec, "ul") for i in items]
        return {"typ": "text", "titel": title, "punkte": points}


def _relative(path: Path, start: Path) -> str:
    import os
    return os.path.relpath(path, start)


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def kind_title(lines: list[str], kind: str) -> str:
    """The heading of the chapter marked <!-- kind: <kind> -->; select() leaves it out of its document."""
    for i, line in enumerate(lines):
        if line.strip().startswith("## "):
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("<!--")):
                m = KIND_LINE.match(lines[j].strip())
                if m and m.group(1) == kind:
                    return line.strip()[3:].strip()
                j += 1
    return ""


def build(options: dict) -> tuple[dict, Deck]:
    root, source, out = Path(options["root"]), Path(options["markdown"]), Path(options["out"])
    role, language = options.get("role", ""), options.get("language", "en")
    text = source.read_text(encoding="utf-8").splitlines()
    handbook, found = select(text, role, "handbook", language)
    deck = Deck(root, source, out, role, set(found["roles"]), language)
    t = deck.t

    preamble = []
    for line in handbook[1:]:
        if line.strip().startswith("## "):
            break
        if line.strip() and not line.strip().startswith(("<!--", "#")):
            preamble.append(plain(line.strip()))
    title = options.get("title") or plain(next((l.strip()[2:] for l in handbook if l.strip().startswith("# ")), source.stem))
    sub = [t["training"].format(role=role)] if role else []
    if preamble and len(preamble[0]) <= 80:
        sub.append(preamble[0].replace(" · ", " | "))

    agenda: list[str] = []
    body: list[dict] = []

    def chapter(name: str, sub_title: str, notes: str, slides: list[dict]) -> None:
        if slides:
            agenda.append(name)
            divider = {"typ": "kapitel", "titel": name}
            if sub_title:
                divider["untertitel"] = sub_title
            if notes:
                divider["notizen"] = notes
            body.append(divider)
            body.extend(slides)

    for chap in parse(handbook):
        if chap["deck"].get("skip"):
            continue
        slides = [deck.slide(sec) for sec in chap["sections"] if not sec["deck"].get("skip")]
        if not chap["sections"] and chap["blocks"]:
            slides = [deck.slide(chap)]
        intro = paragraphs(chap) if chap["sections"] else []
        chapter(deck.title(chap), first_sentence(intro[0]) if intro else "", " ".join(plain(p) for p in intro), slides)

    quick = select(text, role, "quick", language)[0] if "quick" in found["kinds"] else []
    quick_chapters = parse(quick)
    if quick_chapters:
        sections = [s for c in quick_chapters for s in c["sections"] if not s["deck"].get("skip")]
        chapter(kind_title(text, "quick") or "Quick guide", "", "", [deck.slide(s) for s in sections])

    exercises, solutions = [], []
    if "exercises" in found["kinds"]:
        for chap in parse(select(text, role, "exercises", language)[0]):
            for sec in chap["sections"]:
                if chap["title"] == SOLUTIONS.get(language, SOLUTIONS["en"]):
                    solutions.append(deck.solution(sec))
                elif of(sec, "check"):
                    exercises.append(deck.exercise(sec))
                elif not sec["deck"].get("skip"):
                    exercises.append(deck.slide(sec))
        chapter(kind_title(text, "exercises") or "Exercises", "", "", exercises)

    slides = [{"typ": "titel", "titel": title, "untertitel": sub}]
    if len(agenda) <= len(AGENDA_NUMBERS):
        fill = {str(n): f"{i:02d}" for i, n in enumerate(AGENDA_NUMBERS[:len(agenda)], 1)}
        fill.update({str(tid): item for tid, item in zip(AGENDA_TEXTS, agenda)})
        slides.append({"bib": 10, "titel": t["agenda"], "texte": fill,
                       "entfernen": AGENDA_NUMBERS[len(agenda):] + AGENDA_TEXTS[len(agenda):]})
    else:
        slides.append({"typ": "agenda", "punkte": agenda})
    slides += body
    slides.append({"typ": "abschluss", "titel": t["end"]})
    if solutions:
        slides.append({"typ": "kapitel", "titel": t["solutions"], "untertitel": t["solutions_sub"], "ab_hier_ausblenden": True})
        slides += solutions

    spec = {"ausgabe": out.name, "fusszeile": f"{title} | {t['footer'].format(role=role)}" if role else title,
            "zweck": f"{t['training'].format(role=role) if role else title}, built by ppp guide --kind deck from "
                     f"{source.name}",
            "quellen": [_relative(source, out.parent).replace("\\", "/"), "walks/*.json"],
            "folien": slides}
    return spec, deck


def main(options: dict) -> int:
    out = Path(options["out"])
    try:
        spec, deck = build(options)
    except FileNotFoundError as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 2
    role = options.get("role", "")
    if role and role not in deck.roles:
        print(f"ERROR: no section names role {role}; roles in the handbook: {', '.join(sorted(deck.roles)) or 'none'}",
              file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    spec_path = out.with_name(out.stem + ".spec.json")
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{spec_path}: {len(spec['folien'])} slides, {deck.pictures} pictures" + (f" for role {role}" if role else ""))
    for warning in deck.warnings:
        print(f"WARN: {warning}")
    bippt = options.get("bippt", "")
    if not bippt:
        print("NOTE: bippt (plugin bi-design) not found; the spec is the result: build it with bi-ppt or "
              "ppp guide --bippt <path to bippt.py>")
        return 0
    code = 0
    for args in (["bauen", str(spec_path)], ["pruefen", str(out)]):
        proc = subprocess.run([sys.executable, bippt, *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        code = code or proc.returncode
    return code


if __name__ == "__main__":
    sys.exit(main(json.loads(sys.argv[1])))
