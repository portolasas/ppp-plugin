"""The record of what ppp did against the tenant, per project (VERBUNDEN VB-14): exchange/tenant/imports.jsonl with
one entry per import, move, restore, creation, export mark and raised version, and exchange/tenant/times.jsonl with the
durations of exports; versions as numbers; whether an export is due after an import. Split from connected.py (review
14.11.)."""
from __future__ import annotations

import json
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

from . import tenant
from .project import ToolError, load_config


USUAL_OF = 5    # the median of the last five measurements of a kind counts


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def version_key(text: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", text or ""))


def next_version(version: str) -> str:
    parts = list(version_key(version))
    return ".".join(map(str, parts[:-1] + [parts[-1] + 1])) if parts else "<next>"


def entries(root: Path) -> list[dict]:
    path = root / "exchange" / "tenant" / "imports.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def record(root: Path, entry: dict) -> dict:
    entry = {**entry, "time": datetime.now().isoformat(timespec="seconds")}
    path = root / "exchange" / "tenant" / "imports.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def imported(root: Path, name: str, version: str | None, alias: str) -> bool:
    return any(e.get("status") == "done" and e.get("version") == version and e.get("environment") == alias
               and str(e.get("solution", "")).lower() == name.lower() for e in entries(root))


def of(entry: dict, name: str, alias: str) -> bool:
    return entry.get("environment") == alias and str(entry.get("solution", "")).lower() == name.lower()


def never_imported(root: Path, name: str, alias: str) -> bool:
    """No import of ppp from this project into the environment came to an end yet (a restore counts as one, a move into
    the environment too; the creation of an empty solution, ppp import --create, does not: it brought no content)."""
    return not any(e.get("status") == "done" and e.get("kind") != "create" and of(e, name, alias) for e in entries(root))


def export_due(root: Path, name: str) -> dict | None:
    """The last import (a restore too) into the project's environment when no ppp export of the solution came after it:
    until then the project's state is the package, not the tenant's, and the drift check of the next import would
    compare with the wrong base. None offline and without such an import. The mark of the export stands in
    imports.jsonl (status exported), beside the import it follows: one file to read, and written also when the export
    brings the same content and so no commit."""
    alias = load_config(root).get("environment")
    if not alias:
        return None
    due = None
    for entry in entries(root):
        if of(entry, name, alias) and entry.get("status") == "done":
            due = entry
        elif of(entry, name, alias) and entry.get("status") == "exported":
            due = None
    return due


def need_export(root: Path, name: str, command: str) -> None:
    due = export_due(root, name)
    if due:
        raise ToolError(f"{due['environment']} imported {name} {due['version']} at {str(due.get('time', '?'))[:16].replace('T', ' ')}; "
                        f"run ppp export first: it makes the tenant's state the base of the next package. Then {command} again.")


def mark_exported(root: Path, name: str, version: str, by: str, only_version: bool = False) -> bool:
    """After an export was taken into the project: the mark that ends export_due. only_version (ppp unpack of an export
    fetched by hand): only when the export has the version of that import."""
    due = export_due(root, name)
    if not due or (only_version and due.get("version") != version):
        return False
    record(root, {"solution": due["solution"], "version": version, "environment": due["environment"], "status": "exported",
                   "by": by})
    return True


def times(root: Path) -> list[dict]:
    path = root / "exchange" / "tenant" / "times.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def timed_export(root: Path, env: dict, arguments: list[str], wait: float) -> None:
    """One export through pac; its duration goes into times.jsonl once it came to an end (a failed one raises)."""
    began = time.monotonic()
    tenant.run(env["url"], arguments, timeout=wait)
    path = root / "exchange" / "tenant" / "times.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"kind": "export", "environment": env["alias"], "seconds": round(time.monotonic() - began, 1),
                            "time": datetime.now().isoformat(timespec="seconds")}) + "\n")


def usual(root: Path, alias: str, whole: bool = True) -> dict[str, float | None]:
    """The usual duration of an export and of an import in the environment, from the project's own measurements: the
    median of the last USUAL_OF that came to an end; None without one. An import is the whole call of ppp import up to
    IMPORTED, the checks and the backup included (seconds_call); an entry from before ppp measured it gives the time
    from the start of the import (seconds). whole=False: always the latter, how long an import runs once started. A move
    counts for its target (its environment), the creation of an empty solution not at all: it says nothing of how long a
    package takes."""
    done = [e for e in entries(root) if e.get("status") == "done" and e.get("environment") == alias and e.get("kind") != "create"]
    measured = {"export": [e.get("seconds") for e in times(root) if e.get("kind") == "export" and e.get("environment") == alias],
                "import": [e.get("seconds_call", e.get("seconds")) if whole else e.get("seconds") for e in done]}
    found = {}
    for kind, values in measured.items():
        values = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        found[kind] = statistics.median(values[-USUAL_OF:]) if values else None
    return found


def about(seconds: float | None) -> str:
    """A duration as a rough figure: seconds up to 90 s, minutes above."""
    if seconds is None:
        return "not measured yet"
    return f"about {max(round(seconds), 1)} s" if seconds <= 90 else f"about {round(seconds / 60)} min"


def usual_line(root: Path, alias: str) -> str:
    found = usual(root, alias)
    return (f"Usual here: export {about(found['export'])}, import {about(found['import'])}"
            + (" (a whole ppp import up to IMPORTED, checks and backup included)." if found["import"] is not None else "."))
