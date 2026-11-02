"""Walks through a running canvas app: the walk file, its offline check and the layout findings. Standard library only;
the browser and Word parts run as child processes (tools/child/), because python -I hides packages installed with --user."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .project import ToolError
from .report import Report

ACTIONS = ("click", "type", "wait", "hover", "key", "scroll", "shot", "expect")
EXPECTATIONS = ("equals", "contains", "count", "absent")
TOP_KEYS = {"title", "intro", "url", "viewports", "ready", "mask", "ignore", "markColor", "testData", "out", "steps"}
STEP_KEYS = set(ACTIONS) | set(EXPECTATIONS) | {"value", "nth", "writes", "text", "by", "marks", "crop", "check", "caption",
                                                "within", "scenario"}
DEFAULT_VIEWPORT = [1366, 800]
WRITING = re.compile(r"\b(Patch|SubmitForm|Remove|RemoveIf|UpdateIf|Update)\s*\(|\.Run\s*\(")


def load(path: Path) -> dict:
    try:
        walk = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        raise ToolError(f"Walk file {path}: {ex}")
    if not isinstance(walk, dict):
        raise ToolError(f"Walk file {path}: expected an object")
    return walk


def name_of(path: Path) -> str:
    return path.name[:-5] if path.name.endswith(".json") else path.name


def out_dir(root: Path, path: Path, walk: dict) -> Path:
    return root / walk["out"] if walk.get("out") else root / "exchange" / "walks" / name_of(path)


def viewports(walk: dict) -> list[list[int]]:
    return walk.get("viewports") or [DEFAULT_VIEWPORT]


def action_of(step: dict) -> str:
    return next((a for a in ACTIONS if a in step), "")


def writes(walk: dict) -> bool:
    return any(s.get("writes") for s in walk.get("steps", []) if isinstance(s, dict))


def mark_parts(mark) -> tuple[str, int, str]:
    """A mark is a control name or {control, nth, label}."""
    if isinstance(mark, str):
        return mark, 0, ""
    return mark.get("control", ""), mark.get("nth", 0), mark.get("label", "")


def _screens_text(root: Path) -> str:
    folder = root / "components" / "power-apps" / "screens"
    if not folder.is_dir():
        return ""
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sorted(folder.glob("*.y*ml")))


def on_select(screens: str, control: str) -> str:
    """The OnSelect formula of a control in the screen YAML, found by indentation; empty when there is none."""
    lines = screens.splitlines()
    for i, line in enumerate(lines):
        if not re.fullmatch(rf"\s*(- )?{re.escape(control)}:\s*", line):
            continue
        own = len(line) - len(line.lstrip(" -"))
        for j in range(i + 1, len(lines)):
            text = lines[j]
            if text.strip() and len(text) - len(text.lstrip()) <= own and not text.lstrip().startswith("Control"):
                break
            if text.strip().startswith("OnSelect:"):
                prop = len(text) - len(text.lstrip())
                block = [text]
                for rest in lines[j + 1:]:
                    if rest.strip() and len(rest) - len(rest.lstrip()) <= prop:
                        break
                    block.append(rest)
                return "\n".join(block)
    return ""


def check(walk: dict, screens: str = "") -> Report:
    """Offline check of a walk file. screens: the text of the screen YAML, to catch wrong names and writing clicks."""
    rep = Report("ppp walk: walk file")
    for key in sorted(set(walk) - TOP_KEYS):
        rep.error(f"unknown key {key}")
    if not str(walk.get("url", "")).startswith(("https://", "http://", "file:")):
        rep.error("url: the play URL of the app is missing")
    ready = walk.get("ready")
    if not (isinstance(ready, dict) and ready.get("control")):
        rep.error("ready: {control, refresh} is missing; a walk starts by waiting for content, a fixed time is unreliable")
    steps = walk.get("steps")
    if not isinstance(steps, list) or not steps:
        rep.error("steps: missing or empty")
        steps = []
    for size in walk.get("viewports", []):
        if not (isinstance(size, list) and len(size) == 2 and all(isinstance(n, int) and n > 0 for n in size)):
            rep.error(f"viewports: {size} is not [width, height]")

    names: list[str] = [str(n) for n in walk.get("mask", [])]
    if isinstance(ready, dict):
        names += [str(ready[k]) for k in ("control", "refresh") if ready.get(k)]
    ids: set[str] = set()
    for number, step in enumerate(steps, 1):
        where = f"step {number}"
        if not isinstance(step, dict):
            rep.error(f"{where}: expected an object")
            continue
        for key in sorted(set(step) - STEP_KEYS):
            rep.error(f"{where}: unknown key {key}")
        found = [a for a in ACTIONS if a in step]
        if len(found) != 1:
            rep.error(f"{where}: exactly one of {', '.join(ACTIONS)}, found {found or 'none'}")
            continue
        action = found[0]
        if action == "type" and "value" not in step:
            rep.error(f"{where}: type needs a value")
        if action == "expect":
            wanted = [k for k in EXPECTATIONS if k in step]
            if len(wanted) != 1:
                rep.error(f"{where}: expect needs exactly one of {', '.join(EXPECTATIONS)}")
            elif wanted[0] == "count" and not (isinstance(step["count"], int) and step["count"] >= 0):
                rep.error(f"{where}: count must be a whole number")
            elif wanted[0] == "absent" and step["absent"] is not True:
                rep.error(f"{where}: absent can only be true")
        if action == "shot":
            shot = str(step["shot"])
            if not re.fullmatch(r"[A-Za-z0-9_-]+", shot):
                rep.error(f"{where}: shot id {shot!r} may hold letters, digits, _ and - only")
            if shot in ids:
                rep.error(f"{where}: shot id {shot} is used twice")
            ids.add(shot)
            names += [mark_parts(m)[0] for m in step.get("marks", [])]
            if step.get("crop"):
                names.append(str(step["crop"]))
        elif action != "key":
            control = str(step[action])
            names.append(control)
            if action == "click" and not step.get("writes") and WRITING.search(on_select(screens, control)):
                rep.error(f"{where}: OnSelect of {control} writes data; mark the step with \"writes\": true")

    if writes(walk):
        data = walk.get("testData") or {}
        mark, cleanup = str(data.get("mark", "")).strip(), str(data.get("cleanup", "")).strip()
        if not mark or not cleanup:
            rep.error("testData: a walk that writes needs {mark, cleanup}: clearly identifiable test data and how it is removed")
        elif not any(mark in str(s.get("value", "")) for s in steps if isinstance(s, dict) and "type" in s):
            rep.error(f"testData: no typed value carries the mark {mark}, so the created data cannot be identified")
    if screens:
        for name in sorted({n for n in names if n}):
            if not re.search(rf"(^|\s){re.escape(name)}:", screens, re.M):
                rep.warn(f"control {name} is not in components/power-apps/screens/")
    if not rep.lines:
        rep.ok(f"{len(steps)} steps, {len(ids)} pictures")
    return rep


def check_file(root: Path, path: Path) -> Report:
    return check(load(path), _screens_text(root))


def expectation(step: dict, values: list[str]) -> tuple[bool, str]:
    """Compare the shown texts of all visible instances of a control with a step's expectation; (met, what was found).
    Without nth any instance may match, so a value in some gallery row counts."""
    shown = [" ".join(v.split()) for v in values]
    found = f"found {shown[:3]!r}" + (f" and {len(shown) - 3} more" if len(shown) > 3 else "")
    if "count" in step:
        return len(shown) == step["count"], f"found {len(shown)}"
    if "absent" in step:
        return not shown, found
    if "nth" in step:
        shown = shown[step["nth"]:step["nth"] + 1]
    if "equals" in step:
        want = " ".join(str(step["equals"]).split())
        return want in shown, found
    want = " ".join(str(step["contains"]).split())
    return any(want in v for v in shown), found


def layout_findings(controls: list[dict], viewport: list[int], ignore: list[str] | tuple = ()) -> list[str]:
    """Findings from the measured controls of one state. Each control: name, x, y, w, h, id, parent (id or None), px, py,
    pw, ph (box of the parent), scroller, transparent, truncated, text, broken. Rows of a gallery repeat, so equal
    messages count once. The result is a hint for the look at the picture, not a verdict."""
    width, height = viewport
    seen = [c for c in controls if c["w"] > 0 and c["h"] > 0 and c["name"] not in ignore]
    out: list[str] = []

    def add(message: str) -> None:
        if message not in out:
            out.append(message)

    for c in seen:
        name = c["name"]
        if not c.get("scroller"):
            if c["x"] < -1 or c["y"] < -1 or c["x"] + c["w"] > width + 1 or c["y"] + c["h"] > height + 1:
                add(f"L1 {name}: reaches outside the window ({width}x{height})")
            if c.get("parent") is not None and (
                    c["x"] < c["px"] - 1 or c["y"] < c["py"] - 1 or c["x"] + c["w"] > c["px"] + c["pw"] + 1
                    or c["y"] + c["h"] > c["py"] + c["ph"] + 1):
                add(f"L2 {name}: reaches outside its parent {c.get('parentName', '')}".rstrip())
        if c.get("truncated"):
            add(f"L3 {name}: text is cut off: {c.get('text', '')!r}")
        if c.get("broken"):
            add(f"L5 {name}: image does not load")

    families: dict = {}
    for c in seen:
        if c.get("parent") is not None and not c.get("transparent"):
            families.setdefault(c["parent"], []).append(c)
    for family in families.values():
        for i, a in enumerate(family):
            for b in family[i + 1:]:
                overlap_w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
                overlap_h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
                if overlap_w > 1 and overlap_h > 1:
                    first, second = sorted((a["name"], b["name"]))
                    add(f"L4 {first} and {second}: overlap by {round(overlap_w)}x{round(overlap_h)} px")
    return sorted(out)
