"""What differs between a state of the tenant and a state of the project (VERBUNDEN VB-8, VB-12): the files, the lines
that differ (changed lines first, those that only moved last) and the drift against the commit of the version online.
Values the server rewrites never count (verify.stable). Split from connected.py (review 14.11.)."""
from __future__ import annotations

import difflib
import fnmatch
import re
import tempfile
from collections import Counter
from pathlib import Path

from . import gitutil, solution
from .project import ToolError
from .verify import files_of, stable


# What a deviation shows beside the names: the lines of the first text files, each cut to about one terminal line
SHOWN_FILES, SHOWN_LINES, SHOWN_WIDTH = 5, 6, 160


BINARY = re.compile(r"\.(msapp|png|jpe?g|gif|bmp|ico|webp|tiff?|zip|dll|wasm)$", re.I)


def unpacked(package: Path, name: str) -> dict[str, bytes]:
    with tempfile.TemporaryDirectory(prefix="ppp-tenant-") as tmp:
        folder = Path(tmp) / name
        solution.unpack(package, folder)
        return {f: (folder / f).read_bytes() for f in files_of(folder)}


def difference(theirs: dict[str, bytes], ours: dict[str, bytes]) -> list[str]:
    """Files that differ between the tenant and a state of the project; values the server rewrites do not count."""
    return (sorted(f for f in theirs.keys() & ours.keys() if stable(f, theirs[f]) != stable(f, ours[f]))
            + sorted(f + " (only in the tenant)" for f in theirs.keys() - ours.keys())
            + sorted(f + " (not in the tenant)" for f in ours.keys() - theirs.keys()))


def _text_lines(name: str, data: bytes) -> list[str] | None:
    """The lines of a file as they count (verify.stable), or None for a binary file."""
    if BINARY.search(name) or b"\0" in data:
        return None
    try:
        return stable(name, data).decode("utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return None


def _cut(line: str, other: str | None) -> str:
    """A line cut to about SHOWN_WIDTH characters; a long line from shortly before where it parts from its counterpart,
    so a change in a long line of JSON or XML stays in view."""
    if len(line) <= SHOWN_WIDTH:
        return line
    start = 0
    if other is not None:
        same = next((i for i, (a, b) in enumerate(zip(line, other)) if a != b), min(len(line), len(other)))
        start = max(same - 40, 0)
    part = line[start:start + SHOWN_WIDTH]
    return ("…" if start else "") + part + ("…" if start + SHOWN_WIDTH < len(line) else "")


def details(theirs: dict[str, bytes], ours: dict[str, bytes], different: list[str], label: str = "project") -> list[str]:
    """What differs in the first SHOWN_FILES files that both sides have: up to SHOWN_LINES lines as a short diff,
    - the project (`label` names which state of it), + the tenant, with the number of differing lines and a note when
    only their order differs; a binary file by its name only."""
    both = [f for f in different if f in theirs and f in ours]
    lines = []
    for name in both[:SHOWN_FILES]:
        mine, tenants = _text_lines(name, ours[name]), _text_lines(name, theirs[name])
        if mine is None or tenants is None:
            lines.append(f"  {name}: binary, no lines shown")
            continue
        shown = []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, mine, tenants, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            old, new = mine[i1:i2], tenants[j1:j2]
            shown += [("-", line, new[k] if k < len(new) else None) for k, line in enumerate(old)]
            shown += [("+", line, old[k] if k < len(old) else None) for k, line in enumerate(new)]
        order = sorted(mine) == sorted(tenants)
        # a line the other side has too, maybe elsewhere or without its comma, only moved: the designer sorts parameters
        # anew on saving, and the changed text came after the first lines shown (Erprobung 13.11., C9). Changed lines first.
        # Counted, not as a set: lines such as "type": "string" or }, repeat in a flow, and one that changed into another
        # that exists elsewhere is still a change (review 14.11.). Per line, without its comma: as many lines as one side
        # has more than the other changed, the rest only moved.
        key = lambda line: line.strip().rstrip(",")
        counts = {"-": Counter(map(key, mine)), "+": Counter(map(key, tenants))}
        surplus = {sign: {k: max(0, n - counts["+" if sign == "-" else "-"][k]) for k, n in counts[sign].items()} for sign in counts}
        changed_lines, moved = [], []
        for s in shown:
            k = key(s[1])
            if surplus[s[0]].get(k, 0) > 0:
                surplus[s[0]][k] -= 1
                changed_lines.append(s)
            else:
                moved.append(s)
        if moved and not order:
            shown = changed_lines + moved
        lines.append(f"  {name}: {len(shown)} lines differ (- {label}, + tenant)" + ("; only the order of lines differs" if order else "")
                     + (f"; {len(moved)} of them only moved, shown last" if moved and not order else ""))
        lines += [f"    {sign} {_cut(line, other)}" for sign, line, other in shown[:SHOWN_LINES]]
        if len(shown) > SHOWN_LINES:
            lines.append(f"    … {len(shown) - SHOWN_LINES} more lines")
    if len(both) > SHOWN_FILES:
        lines.append(f"  … {len(both) - SHOWN_FILES} more files, without their lines")
    return lines


def drift(root: Path, folder: Path, backup: Path, online_version: str, skip: tuple[str, ...] | list[str] = ()) -> tuple[list[str], list[str]]:
    """What the tenant has that the project did not build on: the export just taken against the commit that holds the
    tenant's state of the version online (VERBUNDEN VB-8). The names, and the lines that differ (details). skip: files
    left out on both sides, as paths in the solution folder or patterns of fnmatch (a move: the values of the
    environment variables, ERWEITERUNGEN C.4)."""
    try:
        base = gitutil.tenant_commit(root, folder, online_version)
    except ToolError:
        return [f"the tenant has version {online_version}, which this project never saw"], []
    prefix = gitutil.rel(root, folder) + "/"
    blobs = gitutil.read_blobs(root, base, [prefix + f for f in gitutil.tracked_files(root, base, folder)])
    theirs, ours = unpacked(backup, folder.name), {k[len(prefix):]: v for k, v in blobs.items()}
    if skip:
        kept = lambda files: {f: v for f, v in files.items() if not any(fnmatch.fnmatchcase(f, s) for s in skip)}
        theirs, ours = kept(theirs), kept(ours)
    different = difference(theirs, ours)
    return different, details(theirs, ours, different, "project's base")
