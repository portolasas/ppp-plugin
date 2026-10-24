"""Locate the project and its solutions."""
from __future__ import annotations

import json
from pathlib import Path


class ToolError(Exception):
    """Expected failure with a message for the agent; the command exits with code 2."""


def find_root(start: Path | None = None) -> Path:
    """The nearest folder upwards with project.json; otherwise the start folder if it has solution/."""
    start = (start or Path.cwd()).resolve()
    for folder in (start, *start.parents):
        if (folder / "project.json").is_file():
            return folder
    if (start / "solution").is_dir():
        return start
    raise ToolError(f"Not a ppp project (no project.json in {start} or above). Use --project <folder>.")


def load_config(root: Path) -> dict:
    path = root / "project.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as ex:
        raise ToolError(f"project.json is not valid JSON: {ex}") from ex


def solution_with_role(config: dict, role: str) -> str | None:
    for sol in config.get("solutions") or []:
        if sol.get("role") == role:
            return sol.get("uniqueName")
    return None


def solution_dir(root: Path, name: str | None = None) -> Path:
    """solution/<name>; without a name the package solution from project.json (the transfer solution, else the main
    solution) or the only folder in solution/."""
    base = root / "solution"
    if name:
        path = base / name
        if not path.is_dir():
            raise ToolError(f"Solution folder not found: {path}")
        return path
    config = load_config(root)
    for role in ("transfer", "main"):
        default = solution_with_role(config, role)
        if default:
            path = base / default
            if not path.is_dir():
                raise ToolError(f"The {role} solution {default} from project.json has no folder {path}. Run ppp unpack first.")
            return path
    folders = sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
    if len(folders) == 1:
        return folders[0]
    if not folders:
        raise ToolError(f"No solution in {base}. Run ppp unpack <export.zip> first.")
    raise ToolError("Several solutions in solution/: " + ", ".join(p.name for p in folders) + ". Use --solution <name>.")
