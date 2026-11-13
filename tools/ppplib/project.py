"""Locate the project and its solutions."""
from __future__ import annotations

import json
import re
from pathlib import Path


class ToolError(Exception):
    """Expected failure with a message for the agent; the command exits with code 2."""


# The Publisher of a solution (Dataverse): the developer's, the same in all his projects. ~/.ppp/settings.json holds the
# four values once per computer, project.json only the unique name.
PUBLISHER_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
PUBLISHER_PREFIX = re.compile(r"[A-Za-z][A-Za-z0-9]{1,7}")


def check_publisher_name(name: object) -> str:
    """The unique name of a Publisher, or a ToolError: letters, digits and underscores, no digit first, at most 256."""
    if not (isinstance(name, str) and PUBLISHER_NAME.fullmatch(name) and len(name) <= 256):
        raise ToolError("Publisher name must be letters, digits and underscores, not starting with a digit, "
                        f"at most 256 characters: {name!r}")
    return name


def check_publisher_prefix(prefix: object) -> str:
    """The customization prefix of a Publisher, or a ToolError: 2 to 8 letters and digits, a letter first, not mscrm."""
    if not (isinstance(prefix, str) and PUBLISHER_PREFIX.fullmatch(prefix) and not prefix.lower().startswith("mscrm")):
        raise ToolError("Publisher prefix must be 2 to 8 letters and digits, starting with a letter, and not starting "
                        f"with mscrm: {prefix!r}")
    return prefix


def check_option_prefix(value: object) -> int:
    """The option value prefix of a Publisher as a number, or a ToolError: a whole number from 10000 to 99999."""
    text = value.strip() if isinstance(value, str) else value
    number = int(text) if isinstance(text, str) and re.fullmatch(r"\d{1,9}", text) else text
    if isinstance(number, bool) or not isinstance(number, int) or not 10000 <= number <= 99999:
        raise ToolError(f"Publisher option value prefix must be a whole number from 10000 to 99999: {value!r}")
    return number


def check_publisher_display(text: object) -> str:
    if not (isinstance(text, str) and text.strip()):
        raise ToolError("Publisher display name must not be empty")
    return text.strip()


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


def package_solution(config: dict) -> str | None:
    """The solution a package is built from, as project.json names it: the transfer solution, else the main solution.
    It needs no folder: before the first export there is none."""
    return solution_with_role(config, "transfer") or solution_with_role(config, "main")


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
    default = package_solution(config)
    if default:
        path = base / default
        if not path.is_dir():
            role = "transfer" if default == solution_with_role(config, "transfer") else "main"
            raise ToolError(f"The {role} solution {default} from project.json has no folder {path}. Run ppp unpack first.")
        return path
    folders = sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
    if len(folders) == 1:
        return folders[0]
    if not folders:
        raise ToolError(f"No solution in {base}. Run ppp unpack <export.zip> first.")
    raise ToolError("Several solutions in solution/: " + ", ".join(p.name for p in folders) + ". Use --solution <name>.")
