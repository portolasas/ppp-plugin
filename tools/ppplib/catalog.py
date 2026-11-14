"""What proved itself in a project, for the next one (entwurf/HOME.md HO-5 to HO-7).

project.json may name proven building blocks: `proven`, a list of {path, note, since}; path is a file or folder under
components/, note one sentence. Only the user marks something as proven, on a card; ppp catalog --add writes it.
ppp catalog lists the proven building blocks of the other projects in the register of this computer and of the team
folder; ppp catalog --show prints one, so the agent need not read outside its workspace.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from . import registry, storage
from .project import ToolError, load_config
from .report import Report

NOTE_MAX = 200
SHOW_MAX = 12_000
LIST_MAX = 40
# a note travels to other projects and to the team folder: no address, mail or ID in it
PRIVATE = re.compile(r"https?://|\b[\w.+-]+@[\w-]+\.[\w.]+|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)


def _path_error(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "path must be a text"
    parts = value.replace("\\", "/").split("/")
    if parts[0] != "components" or len(parts) < 2 or ".." in parts or value.startswith("/"):
        return f"path {value!r} must lie under components/"
    return None


def problems(config: dict) -> list[str]:
    """What is wrong with `proven` in project.json, without looking at the files."""
    given = config.get("proven")
    if given is None:
        return []
    if not isinstance(given, list):
        return ["proven must be a list of objects with path, note and since"]
    out = []
    for item in given:
        if not isinstance(item, dict):
            out.append("proven: each entry is an object with path, note and since")
            continue
        error = _path_error(item.get("path"))
        if error:
            out.append("proven: " + error)
        if not (isinstance(item.get("note"), str) and item["note"].strip()):
            out.append(f"proven: {item.get('path')!r} needs a note (one sentence)")
    return out


def check(root: Path, config: dict, rep: Report) -> None:
    for item in config.get("proven") or []:
        if isinstance(item, dict) and not _path_error(item.get("path")) and not (root / item["path"]).exists():
            rep.error(f"S project.json: proven names {item['path']}, which does not exist; correct the path or remove "
                      "the entry")


def entries(config: dict) -> list[dict]:
    return [item for item in config.get("proven") or []
            if isinstance(item, dict) and not _path_error(item.get("path")) and isinstance(item.get("note"), str)]


def add(root: Path, given: str, note: str) -> list[str]:
    """Mark a file or folder under components/ as proven; an entry with the same path is replaced."""
    target = (root / given).resolve() if not Path(given).is_absolute() else Path(given).resolve()
    try:
        rel = target.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise ToolError(f"{given} lies outside the project {root}.") from None
    error = _path_error(rel)
    if error:
        raise ToolError(f"proven: {error}.")
    if not target.exists():
        raise ToolError(f"Not found: {rel}")
    note = " ".join(note.split())
    if not note:
        raise ToolError("--note needs one sentence: what the building block does and why it proved itself.")
    if len(note) > NOTE_MAX:
        raise ToolError(f"--note has {len(note)} characters; one sentence of at most {NOTE_MAX}.")
    if PRIVATE.search(note):
        raise ToolError("--note names an address, a mail address or an ID; other projects and the team read it: say it "
                        "without.")
    config = load_config(root)
    kept = [item for item in config.get("proven") or [] if not (isinstance(item, dict) and item.get("path") == rel)]
    config["proven"] = kept + [{"path": rel, "note": note, "since": date.today().isoformat()}]
    storage._write_config(root, config)
    return [f"Proven: {rel} ({len(config['proven'])} in project.json). Commit project.json."]


def collect(current: Path | None) -> list[dict]:
    """The proven building blocks of the other projects: of the register of this computer, then of the team folder for
    projects that are not on this computer. Sorted by prefix and path."""
    from . import team
    found, seen_ids, seen_projects = [], set(), set()
    own = current.resolve() if current else None
    own_config = load_config(own) if own else {}
    for key, entry in registry.read().items():
        root = Path(key)
        if root == own or not (root / "project.json").is_file():
            continue
        try:
            config = load_config(root)
        except ToolError:
            continue
        if config.get("teamId"):
            seen_ids.add(config["teamId"])
        same = (config.get("prefix"), entry.get("remote"))
        if entry.get("remote") and same in seen_projects:
            continue  # a second clone of the same project
        seen_projects.add(same)
        for item in entries(config):
            found.append({**item, "prefix": config.get("prefix", "?"), "name": config.get("name", "?"),
                          "storage": storage.of(config), "root": root, "where": "this computer"})
    if own_config.get("teamId"):
        seen_ids.add(own_config["teamId"])
    for shared in team.catalogs():
        if shared.get("teamId") in seen_ids:
            continue
        for item in entries(shared):
            found.append({**item, "prefix": shared.get("prefix", "?"), "name": shared.get("name", "?"),
                          "storage": shared.get("storage", "?"), "root": None, "remote": shared.get("remote"),
                          "where": "team folder"})
    return sorted(found, key=lambda i: (str(i["prefix"]).casefold(), i["path"]))


def _module(path: str) -> str:
    return path.split("/")[1] if path.count("/") else ""


def _pick(items: list[dict], module: str, word: str) -> list[tuple[int, dict]]:
    word = word.casefold()
    return [(n, i) for n, i in enumerate(items, 1)
            if (not module or _module(i["path"]) == module)
            and (not word or word in " ".join((i["path"], i["note"], i["name"], i["prefix"])).casefold())]


def listing(current: Path | None, module: str = "", word: str = "") -> list[str]:
    items = collect(current)
    if not items:
        return ["No proven building blocks in other projects yet (ppp projects lists the projects this computer knows). "
                "Go on without."]
    picked = _pick(items, module, word)
    if not picked:
        return [f"No proven building block matches ({len(items)} in all; ppp catalog without a filter lists them)."]
    out = [f"Proven building blocks of other projects ({len(picked)} of {len(items)}); ppp catalog --show <number> prints one:"]
    for n, i in picked[:LIST_MAX]:
        out.append(f"  {n:>3}  {i['prefix']}  {i['path']}  [storage {i['storage']}, {i['where']}, since {i.get('since', '?')}]")
        out.append(f"       {i['note']}")
    if len(picked) > LIST_MAX:
        out.append(f"  ... {len(picked) - LIST_MAX} more: narrow with --module <module> or a search word.")
    return out


def show(current: Path | None, number: int) -> list[str]:
    items = collect(current)
    if not 1 <= number <= len(items):
        raise ToolError(f"No building block {number}; ppp catalog lists 1 to {len(items)}.")
    i = items[number - 1]
    out = [f"{i['prefix']} ({i['name']}): {i['path']}", f"Proven since {i.get('since', '?')}: {i['note']}"]
    here = storage.of(load_config(current)) if current else None
    if i["storage"] != "github" and here == "github":
        out.append(f"Its project has storage {i['storage']} and this one github: before anything of it goes into this "
                   "project, ask on a card (project data of a local project stays out of GitHub).")
    out.append("Exports and inputs of another project may hold personal data: take the structure, not the data.")
    if i["root"] is None:
        out.append("The project is not on this computer. "
                   + (f"Its remote: {i['remote']}." if i.get("remote") else
                      "It is a local project of a colleague: ppp projects --team names who holds it."))
        return out
    target = i["root"] / i["path"]
    if not target.exists():
        return out + [f"Not found any more: {target}"]
    if target.is_dir():
        files = sorted(p for p in target.rglob("*") if p.is_file())
        out.append(f"Folder {target} ({len(files)} files):")
        out += [f"  {p.relative_to(target).as_posix()}  ({p.stat().st_size} bytes)" for p in files[:60]]
        target = target / "README.md"
        if not target.is_file():
            return out
    text = target.read_text(encoding="utf-8-sig", errors="replace")
    out += [f"--- {target} ({len(text)} characters) ---", text[:SHOW_MAX]]
    if len(text) > SHOW_MAX:
        out.append(f"--- cut after {SHOW_MAX} characters ---")
    return out


def dump(config: dict, remote: str | None) -> str:
    """catalog.json of a shared project in the team folder."""
    data = {"prefix": config.get("prefix"), "name": config.get("name"), "teamId": config.get("teamId"),
            "storage": storage.of(config), **({"remote": remote} if remote else {}), "proven": entries(config)}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
