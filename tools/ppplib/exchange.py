"""Tidying exchange/ when a package closes (user, 2026-10-24): the imported package goes to exchange/archive/,
the other packages built with ppp pack and the older exports of each solution are deleted, everything else is listed.

Deleting is safe for these files only: every package can be rebuilt from its commit and every unpacked export is in
git (PROJEKTSTRUKTUR S-3). exchange/archive/ itself is never touched.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import zipfile
from pathlib import Path

from .project import ToolError, load_config, solution_with_role
from .solution import zip_manifest

PACKAGE = re.compile(r"^(?P<stem>.+)_IMPORTABLE\.zip$", re.I)
REPORT = re.compile(r"^(?P<stem>.+)_REPORT\.md$", re.I)


def _version(text: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", text))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _size(paths) -> int:
    total = 0
    for p in paths:
        if p.is_file():
            total += p.stat().st_size
        elif p.is_dir():
            total += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return total


def _mb(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB"


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError:  # read-only file, e.g. in a OneDrive folder
        os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
        path.unlink()


def tidy(root: Path, keep: list[str] | None = None, dry_run: bool = False) -> list[str]:
    exchange = root / "exchange"
    archive = exchange / "archive"
    if not exchange.is_dir():
        raise ToolError(f"No exchange/ in {root}.")
    entries = sorted(p for p in exchange.iterdir() if not p.name.startswith(".") and p.name != "archive")
    packages, exports, reports, other = {}, {}, {}, []
    for p in entries:
        m = REPORT.match(p.name)
        if p.is_file() and m:
            reports[m.group("stem")] = p
            continue
        if not (p.is_file() and p.suffix.lower() == ".zip"):
            other.append(p)
            continue
        try:
            info = zip_manifest(p)
        except (ToolError, zipfile.BadZipFile, OSError):
            other.append(p)
            continue
        m = PACKAGE.match(p.name)
        if m:
            packages[m.group("stem")] = (info["uniqueName"], _version(info["version"]), p)
        else:
            exports.setdefault((info["uniqueName"], info["managed"]), []).append((_version(info["version"]), p))

    if keep:
        wanted = {Path(k).name for k in keep}
        kept = [stem for stem, (_, _, p) in packages.items() if p.name in wanted]
        missing = wanted - {packages[s][2].name for s in kept}
        if missing:
            raise ToolError("Not a package in exchange/: " + ", ".join(sorted(missing)))
    else:
        config = load_config(root)
        name = solution_with_role(config, "transfer") or solution_with_role(config, "main")
        own = [(version, stem) for stem, (unique, version, _) in packages.items() if unique == name]
        if not own:
            raise ToolError(f"No package of {name or 'the package solution'} in exchange/; name the imported one with --keep.")
        kept = [max(own)[1]]

    moves = []
    for stem in kept:
        moves.append(packages[stem][2])
        if stem in reports:
            moves.append(reports[stem])
    deletions = [p for stem, (_, _, p) in packages.items() if stem not in kept]
    deletions += [p for stem, p in reports.items() if stem not in kept]
    newest = []
    for found in exports.values():
        found.sort()
        newest.append(found[-1][1])
        deletions += [p for _, p in found[:-1]]

    before, moved, deleted = _size(entries), _size(moves), _size(deletions)
    out = [("Plan, nothing changed yet. " if dry_run else "") + f"exchange/ {_mb(before)} before"]
    if not dry_run:
        archive.mkdir(exist_ok=True)
        for p in moves:
            target = archive / p.name
            if target.exists():
                if _sha(target) != _sha(p):
                    raise ToolError(f"exchange/archive/{p.name} exists with other content; not overwritten.")
                _remove(p)
            else:
                p.rename(target)
        for p in deletions:
            _remove(p)
    out.append("To exchange/archive/: " + ", ".join(p.name for p in moves))
    out.append(f"Deleted ({len(deletions)}, {_mb(deleted)}): " + (", ".join(sorted(p.name for p in deletions)) or "-"))
    out.append("Newest export of each solution, kept: " + (", ".join(sorted(p.name for p in newest)) or "-"))
    if other:
        out.append("Other files, untouched; ask the user on a card which may go: "
                   + ", ".join(p.name + ("/" if p.is_dir() else "") for p in other))
    out.append(f"exchange/ {_mb(before - moved - deleted)} after, exchange/archive/ "
               + _mb(_size(archive.iterdir()) if archive.is_dir() else 0) + (" before the move" if dry_run else ""))
    return out
