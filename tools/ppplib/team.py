"""The team folder (entwurf/HOME.md HO-8 to HO-14): a synced folder a team shares, e.g. a SharePoint library.

    <team folder>/README.md
    <team folder>/projects/<prefix>-<teamId>/<person>.json   what this person last had: seen, commit, active package
    <team folder>/projects/<prefix>-<teamId>/<person>/       the backups of this person (local projects only)
    <team folder>/projects/<prefix>-<teamId>/catalog.json    the proven building blocks of the project
    <team folder>/knowledge/, material/                      what the team keeps for all projects

`teamHome` and `person` are personal settings (~/.ppp/settings.json). Nobody works inside the team folder: a sync client
moves files one by one and late, which can break a git history (HO-9). A project takes part only after ppp team share
wrote `teamId` into its project.json (HO-10). A local project then backs up into the folder of its person, so the
retention never removes a colleague's backups (HO-11); a project with a remote writes only the person file and the
catalog (HO-12). The project is held by the person with the newest backup (HO-13). There is no lock and ppp merges
nothing: two people working at once get two histories, which ppp check reports (HO-14).
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from . import agent, cards, catalog, gitutil, storage
from .project import ToolError, load_config

PERSON = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,38}[A-Za-z0-9]|[A-Za-z0-9]")
TEAM_ID = re.compile(r"[0-9a-f]{8}")
RESERVED = {"catalog", "con", "prn", "aux", "nul"}
FRESH = timedelta(hours=1)
README = """# Team folder of ppp

Shared by the team through the sync of this library. ppp writes `projects/`; `knowledge/` and `material/` are yours.

- `projects/<prefix>-<id>/`: one folder per shared project: a file per person (what they last had), the proven
  building blocks (`catalog.json`) and, for projects without a git server, the backups of each person.
- `knowledge/`: rules, templates and the environment profile of the team; lesson proposals for ppp.
- `material/`: presentations, guides, training.

Work in a folder outside this one: `ppp restore <project folder here> <new folder>` takes a project over.
"""


def check_person(name: object) -> str:
    if not (isinstance(name, str) and PERSON.fullmatch(name.strip()) and name.strip().casefold() not in RESERVED):
        raise ToolError(f"person {name!r}: 1 to 40 letters, digits, spaces, hyphens and underscores, a letter or digit "
                        "first and last; it names your file and folder in the team folder.")
    return name.strip()


def settings() -> tuple[Path | None, str | None]:
    """(team folder, person) of this computer; (None, None) without both."""
    current = agent.read_settings() or {}
    folder, person = current.get("teamHome"), current.get("person")
    if not (isinstance(folder, str) and folder and isinstance(person, str) and person):
        return None, None
    return Path(folder).expanduser(), person


def prepare(folder: str) -> Path:
    """The team folder for the settings: an empty folder gets the layout, one in use must have projects/."""
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        raise ToolError(f"Folder not found: {path}")
    if not any(path.iterdir()):
        (path / "README.md").write_text(README, encoding="utf-8", newline="\n")
        for name in ("projects", "knowledge", "material"):
            (path / name).mkdir()
    elif not (path / "projects").is_dir():
        raise ToolError(f"{path} is not empty and has no projects/: not a team folder of ppp. Name the team folder "
                        "itself, or an empty folder to start one.")
    return path


def project_folder(config: dict) -> Path | None:
    """projects/<prefix>-<teamId> of a shared project; None when the project is not shared or no team folder is set."""
    home, _ = settings()
    team_id, prefix = config.get("teamId"), config.get("prefix")
    if home is None or not (isinstance(team_id, str) and TEAM_ID.fullmatch(team_id) and prefix):
        return None
    return home / "projects" / f"{prefix}-{team_id}"


def backup_folder(config: dict) -> Path | None:
    """Where a shared local project backs up: the folder of this person in the team folder (HO-11, HO-12)."""
    folder = project_folder(config)
    if folder is None or storage.of(config) != "local":
        return None
    return folder / settings()[1]


def inside(root: Path) -> Path | None:
    """The team folder when the project lies in it."""
    home, _ = settings()
    if home is None:
        return None
    home, root = home.resolve(), root.resolve()
    return home if home == root or home in root.parents else None


def _head(root: Path) -> str:
    return gitutil.git(root, "rev-parse", "--verify", "-q", "HEAD", check=False).decode().strip()


def _active(root: Path) -> str:
    from . import registry
    return registry._active(root)


def write_status(root: Path, config: dict, now: datetime | None = None) -> bool:
    """<person>.json and catalog.json of a shared project; True when the folder was reached. Written only when
    something changed or the last note is older than an hour: every write is one more file for the sync."""
    folder = project_folder(config)
    if folder is None or not folder.parent.is_dir():
        return False
    _, person = settings()
    now = now or datetime.now()
    folder.mkdir(exist_ok=True)
    head = _head(root)
    status = {"person": person, "prefix": config.get("prefix"), "name": config.get("name"), "storage": storage.of(config),
              "commit": head[:12], "activePackage": _active(root)}
    remote = storage.remote_url(root)
    if remote:
        status["remote"] = remote
    path = folder / f"{person}.json"
    old = _read(path)
    try:
        fresh = now - datetime.fromisoformat(old.get("seen", "")) < FRESH
    except (ValueError, TypeError):
        fresh = False
    if not (fresh and all(old.get(k) == v for k, v in status.items())):
        path.write_text(json.dumps({**status, "seen": now.isoformat(timespec="minutes")}, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    text = catalog.dump(config, remote)
    target = folder / "catalog.json"
    if not target.is_file() or target.read_text(encoding="utf-8") != text:
        target.write_text(text, encoding="utf-8", newline="\n")
    return True


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def people(folder: Path) -> list[dict]:
    """The person files of a project folder, newest first."""
    found = [d for p in sorted(folder.glob("*.json")) if p.name != "catalog.json" and (d := _read(p)).get("person")]
    return sorted(found, key=lambda d: str(d.get("seen", "")), reverse=True)


def newest_backup(folder: Path) -> tuple[str, storage.Backup] | None:
    """(person, backup) of the newest backup over all persons of a project folder."""
    found = [(sub.name, b) for sub in folder.iterdir() if sub.is_dir() for b in storage.backups(sub, None)] \
        if folder.is_dir() else []
    return max(found, key=lambda item: (item[1].time, item[1].path.stat().st_mtime_ns)) if found else None


def catalogs() -> list[dict]:
    """catalog.json of every project in the team folder."""
    home, _ = settings()
    base = home / "projects" if home else None
    return [d for p in sorted(base.glob("*/catalog.json")) if (d := _read(p))] if base and base.is_dir() else []


def check_lines(root: Path) -> list[tuple[str, str]]:
    """The lines of ppp check for the team folder; writes the person file of a shared project on the way."""
    try:
        config = load_config(root)
    except ToolError:
        return []
    home, person = settings()
    if home is None:
        if config.get("teamId"):
            return [("INFO", "S team: the project is shared (teamId in project.json), but this computer has no team folder: "
                             "ppp settings --team <folder> --person <name>")]
        return []
    if inside(root):
        return [("ERROR", f"S team: the project lies inside the team folder {home}; its sync can break the git history. "
                          "Work in a folder outside it: ppp restore <project folder in the team folder> <new folder>")]
    folder = project_folder(config)
    if folder is None:
        return []
    if not gitutil.is_repo(root) or not write_status(root, config):
        return [("INFO", f"S team: {folder.parent} not reachable; nothing noted in the team folder")]
    out = []
    others = [p for p in people(folder) if p["person"] != person]
    if others:
        out.append(("INFO", "S team: also on this project: " + ", ".join(
            f"{p['person']} (seen {str(p.get('seen', '?'))[:10]}, commit {p.get('commit') or 'none'})" for p in others)))
    if storage.of(config) == "local":
        newest = newest_backup(folder)
        if newest and newest[0] != person and storage._since(root, newest[1].commit) is None:
            who, backup = newest
            out.append(("ERROR", f"S team: {who} backed up a state this folder does not have ({backup.path.name}, "
                                 f"{backup.time:%Y-%m-%d %H:%M}); {who} holds the project. Show a card: take it over with "
                                 f"ppp restore \"{folder}\" <new folder>, or, when commits were made here since, the user "
                                 f"brings both histories together by hand (git fetch \"{backup.path}\" main, then merge); "
                                 "ppp merges nothing"))
    else:
        ahead = [p for p in others if p.get("commit") and storage._since(root, p["commit"]) is None]
        if ahead:
            out.append(("INFO", "S team: " + ", ".join(p["person"] for p in ahead) + " noted a commit this folder does "
                                "not have: git pull"))
    return out


def share(root: Path, confirmed: bool | str | None) -> int:
    """Share the project with the team: after a card write teamId into project.json and create its folder."""
    home, person = settings()
    if home is None:
        raise ToolError("No team folder set. Ask the user for the synced team folder and a name, then "
                        "ppp settings --team <folder> --person <name>.")
    if not (home / "projects").is_dir():
        raise ToolError(f"Team folder not reachable: {home} (is the library synced on this computer?)")
    if inside(root):
        raise ToolError(f"The project lies inside the team folder {home}: move it to a folder outside the sync first.")
    config = load_config(root)
    if not gitutil.is_repo(root) or not _head(root):
        raise ToolError("Nothing committed yet: commit first, then share.")
    if project_folder(config) is not None:
        write_status(root, config)
        print(f"Already shared: {project_folder(config)}. Person file and catalog are up to date.")
        return 0
    kind, prefix = storage.of(config), config.get("prefix")
    tracked = gitutil.git(root, "ls-files", "-z").decode("utf-8", "replace").split("\0")
    tops = sorted({t.split("/")[0] for t in tracked if "/" in t})
    if kind == "local":
        commits = gitutil.git(root, "rev-list", "--count", "HEAD").decode().strip()
        goes = (f"every ppp backup then writes the whole git history ({commits} commits; folders {', '.join(tops)}) as a "
                f"bundle into the team folder, under {person}/. Whoever may read the library reads all of it, inputs/ and "
                "environments/ included")
    else:
        goes = (f"storage {kind}: no project files go there, only {person}.json (commit, active package, remote) and the "
                "proven building blocks; colleagues take the project over by cloning its remote")
    card = (f"CONFIRM FIRST (sharing a project, always on a card): show a decision card: share {config.get('name')} ({prefix}) "
            f"with the team folder {home} as {person}; {goes}. Not shared, the project stays as it is. After the answer "
            f"'Share': {cards.ASK}.")
    if not cards.confirm(card, confirmed, (str(root.resolve()), str(home), person, kind, _head(root))):
        return 1
    taken = {p.name.rpartition("-")[2] for p in (home / "projects").iterdir() if p.is_dir()}
    team_id = next(i for i in iter(lambda: uuid.uuid4().hex[:8], None) if i not in taken)
    config["teamId"] = team_id
    storage._write_config(root, config)
    write_status(root, config)
    print(f"Shared: {project_folder(config)} (teamId {team_id} in project.json). Commit project.json."
          + (" Then ppp backup writes the first backup there." if kind == "local" else ""))
    return 0


def table() -> list[str]:
    """Who works on what, from the team folder."""
    home, person = settings()
    if home is None:
        raise ToolError("No team folder set: ppp settings --team <folder> --person <name>.")
    base = home / "projects"
    if not base.is_dir():
        raise ToolError(f"Team folder not reachable: {home}")
    folders = sorted(p for p in base.iterdir() if p.is_dir())
    out = [f"Team folder {home}, you are {person}: {len(folders)} shared project{'' if len(folders) == 1 else 's'}"]
    for folder in folders:
        info = _read(folder / "catalog.json")
        proven = len(info.get("proven") or [])
        out.append(f"  {info.get('prefix', folder.name)}  {info.get('name', '?')}  [storage {info.get('storage', '?')}, "
                   f"{proven} proven]  {folder.name}")
        newest = newest_backup(folder)
        for p in people(folder):
            holds = "  <- holds the project (newest backup " + newest[1].time.strftime("%Y-%m-%d %H:%M") + ")" \
                if newest and newest[0] == p["person"] else ""
            out.append(f"      {p['person']}: seen {str(p.get('seen', '?'))[:16]}, commit {p.get('commit') or 'none'}, "
                       f"{p.get('activePackage', '')}{holds}")
        if info.get("remote"):
            out.append(f"      take over: git clone {info['remote']}")
        elif newest:
            out.append(f"      take over: ppp restore \"{folder}\" <new folder>")
    return out
