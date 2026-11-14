"""The projects of this computer (entwurf/HOME.md HO-3, HO-4): ~/.ppp/projects.json.

ppp finds a project only from the folder a command runs in. The register notes every project a command or the session
start saw: path, prefix, name, storage, mode, modules, remote, structure version, team ID and the day it was last seen.
It fills by itself (ppp check, ppp init, the SessionStart hook) and never leaves the computer. The key is the resolved
path; two entries with the same prefix and remote are clones of one project. `note` never raises: the register is a
convenience, and a check or a hook must not fail on it.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from . import agent, gitutil, storage
from .project import ToolError

FIELDS = ("prefix", "name", "storage", "mode", "modules", "remote", "structureVersion", "teamId")
FRESH = timedelta(days=1)


def path() -> Path:
    return agent.PPP_HOME / "projects.json"


def read() -> dict:
    """{resolved path: entry}; a missing or broken file is an empty register."""
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    projects = data.get("projects") if isinstance(data, dict) else None
    return {k: v for k, v in projects.items() if isinstance(v, dict)} if isinstance(projects, dict) else {}


def _write(projects: dict) -> None:
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + f".{os.getpid()}.tmp")
    partial.write_text(json.dumps({"projects": dict(sorted(projects.items()))}, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    os.replace(partial, target)  # two sessions at once: the last whole file wins, never half a file


def is_project(config: object) -> bool:
    """A project.json of ppp, as the hook tells it: structureVersion (int) and prefix (str)."""
    return (isinstance(config, dict) and isinstance(config.get("structureVersion"), int)
            and not isinstance(config.get("structureVersion"), bool) and isinstance(config.get("prefix"), str))


def _config(root: Path) -> dict | None:
    try:
        config = json.loads((root / "project.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return config if is_project(config) else None


def entry_of(root: Path, config: dict) -> dict:
    entry = {key: config.get(key) for key in FIELDS if config.get(key) is not None}
    entry["storage"] = storage.of(config)
    try:
        remote = storage.remote_url(root)
    except ToolError:
        remote = None
    if remote:
        entry["remote"] = remote
    return entry


def note(root: Path, config: dict | None = None, now: datetime | None = None) -> bool:
    """Note the project in the register; True when the file was written. Written only for a new entry, a changed one or
    one last seen more than a day ago. Never raises."""
    try:
        root = root.resolve()
        config = config if is_project(config) else _config(root)
        if config is None:
            return False
        now = now or datetime.now()
        projects = read()
        entry, old = entry_of(root, config), projects.get(str(root)) or {}
        same = all(old.get(key) == entry.get(key) for key in FIELDS)
        try:
            fresh = now - datetime.fromisoformat(old.get("seen", "")) < FRESH
        except (ValueError, TypeError):
            fresh = False
        if same and fresh:
            return False
        projects[str(root)] = {**entry, "seen": now.isoformat(timespec="minutes")}
        _write(projects)
        return True
    except Exception:  # noqa: BLE001 - see the module text
        return False


def forget(folder: str) -> list[str]:
    projects = read()
    key = str(Path(folder).expanduser().resolve())
    hits = [k for k in projects if k == key or k.casefold() == key.casefold()]
    if not hits:
        raise ToolError(f"Not in the register: {key}. ppp projects lists the entries.")
    for k in hits:
        del projects[k]
    _write(projects)
    return [f"Removed from the register: {', '.join(hits)}. The folder itself is untouched."]


def scan(home: Path) -> list[str]:
    """Add the projects the Copilot sessions of this computer worked in (their working folders with a project.json)."""
    from . import sessions
    found, before = set(), set(read())
    for events in (home / ".copilot" / "session-state").glob("*/events.jsonl"):
        for place in sessions.places(events.parent):
            if (Path(place) / "project.json").is_file():
                found.add(Path(place).resolve())
    added = sorted(str(root) for root in found if str(root) not in before and note(root))
    return [f"Scanned the sessions in {home / '.copilot'}: {len(found)} project folders, {len(added)} new in the register"
            + (": " + ", ".join(added) if added else ".")]


def clones(projects: dict) -> dict:
    """{path: number of entries with the same prefix and remote} for entries that are clones of one project."""
    groups: dict = {}
    for key, e in projects.items():
        if e.get("remote") and e.get("prefix"):
            groups.setdefault((e["prefix"], e["remote"].rstrip("/").removesuffix(".git").casefold()), []).append(key)
    return {key: len(keys) for keys in groups.values() if len(keys) > 1 for key in keys}


def _active(root: Path) -> str:
    try:
        text = (root / "STATE.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "no STATE.md"
    m = re.search(r"^## Active package\s*\n+(.+)$", text, re.M)
    return m.group(1).strip()[:100] if m else "no active package"


def _live(root: Path) -> str:
    from . import structure
    parts = ["active: " + _active(root)]
    config = _config(root) or {}
    if gitutil.is_repo(root):
        last = gitutil.git(root, "log", "-1", "--format=%cs %s", check=False).decode("utf-8", "replace").strip()
        parts.append("last commit " + (last[:80] or "none"))
        if storage.of(config) == "local":
            try:
                folder = storage.backup_folder(config)
            except ToolError:
                folder = None
            items = storage.backups(folder, config.get("prefix")) if folder else []
            parts.append(f"last backup {items[0].time:%Y-%m-%d}" if items else "no backup")
    else:
        parts.append("no git repository")
    version = config.get("structureVersion")
    if isinstance(version, int) and version < structure.STRUCTURE_VERSION:
        parts.append(f"structure version {version}: needs ppp migrate")
    return " | ".join(parts)


def table(live: bool = False) -> list[str]:
    projects = read()
    if not projects:
        return [f"No projects in {path()} yet. It fills when ppp check or ppp init runs in a project; "
                "ppp projects --scan adds the projects of earlier sessions."]
    twins = clones(projects)
    out = [f"Projects on this computer ({len(projects)}), {path()}:"]
    for key, e in sorted(projects.items(), key=lambda item: (str(item[1].get("prefix", "")).casefold(), item[0])):
        root = Path(key)
        there = (root / "project.json").is_file()
        marks = ([] if there else ["missing: ppp projects --forget removes it"]) \
            + ([f"one of {twins[key]} clones"] if key in twins else []) + (["shared with the team"] if e.get("teamId") else [])
        out.append(f"  {e.get('prefix', '?')}  {e.get('name', '?')}  [{e.get('storage', '?')}, {e.get('mode', '?')}, "
                   f"{', '.join(e.get('modules') or []) or 'no modules'}]  seen {str(e.get('seen', '?'))[:10]}"
                   + (f"  ({'; '.join(marks)})" if marks else ""))
        out.append(f"      {key}")
        if live and there:
            out.append("      " + _live(root))
    return out
