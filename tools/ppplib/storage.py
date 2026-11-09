"""Where a project lives and how a local one is backed up (entwurf/ABLAGE.md).

`storage` in project.json (structure version 2): github or bitbucket is git with the remote origin, pushed after each
step; local is git without a remote: commits only, backed up on request with ppp backup (AB-2, AB-3). Bitbucket is
prepared: a new project starts local and switches with ppp storage bitbucket --remote <url> (AB-6).

A backup is a git bundle with the whole history, <prefix>_<YYYYMMDD-hhmmss>_<commit>.bundle in <backupFolder>/<prefix>/
(backupFolder in ~/.ppp/settings.json, AB-5). It is checked with git bundle verify before it gets its name; the newest
10 stay (AB-4). ppp check reminds when the last backup is older than 7 days and commits came after it. ppp restore clones
a bundle into a new folder and never overwrites (AB-8). Git prints localized messages, so only exit codes are read.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple

from . import gitutil
from .project import ToolError, load_config
from .report import Report

STORAGES = ("github", "bitbucket", "local")
NAMES = {"github": "GitHub", "bitbucket": "Bitbucket"}
KEEP = 10
REMIND_DAYS = 7
STAMP = "%Y%m%d-%H%M%S"
BUNDLE = re.compile(r"^(?P<prefix>[A-Za-z][A-Za-z0-9]*)_(?P<stamp>\d{8}-\d{6})_(?P<commit>[0-9a-f]{7,40})\.bundle$")
# folder names of sync services; a git history inside one can break, and in a local project it is the only one
SYNC = (("onedrive", "OneDrive"), ("mobile documents", "iCloud Drive"), ("iclouddrive", "iCloud Drive"),
        ("dropbox", "Dropbox"), ("googledrive", "Google Drive"), ("google drive", "Google Drive"))
BITBUCKET_LATER = ("Bitbucket is prepared, not connected yet (ABLAGE AB-6): start with --storage local and note "
                   "Bitbucket as the target in STATE.md; once it is connected, ppp storage bitbucket --remote <url> "
                   "switches and the first push takes the whole history.")
NO_FOLDER = ("No backup folder set. Ask the user on a card for a folder outside this computer's disk (OneDrive, a "
             "network drive) and save it with ppp settings --backup <folder>.")


class Backup(NamedTuple):
    path: Path
    time: datetime
    commit: str


def of(config: dict) -> str:
    """The storage of a project; one without the field (structure version 1) lies on GitHub (AB-7, AB-9)."""
    return config.get("storage") or "github"


def remote_url(root: Path) -> str | None:
    if not gitutil.is_repo(root):
        return None
    return gitutil.git(root, "remote", "get-url", "origin", check=False).decode("utf-8", "replace").strip() or None


def kind_of(url: str) -> str | None:
    """github or bitbucket from a remote address; None for another server."""
    low = url.casefold()
    if "github.com" in low:
        return "github"
    if "bitbucket" in low:
        return "bitbucket"
    return None


def sync_service(root: Path) -> str | None:
    """The sync service whose folder holds the project, unless its git folder is kept out of the sync (.git.nosync)."""
    git_dir = root / ".git"
    if git_dir.is_symlink() and git_dir.resolve().name.endswith(".nosync"):
        return None
    path = root.resolve()
    for key in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
        if os.environ.get(key):
            base = Path(os.environ[key]).resolve()
            if base == path or base in path.parents:
                return "OneDrive"
    for part in path.parts:
        low = part.casefold()
        for start, name in SYNC:
            if low.startswith(start):
                return name
    return None


def backup_folder(config: dict) -> Path | None:
    from . import agent
    base = (agent.read_settings() or {}).get("backupFolder")
    if not base:
        return None
    prefix = config.get("prefix")
    if not prefix:
        raise ToolError("project.json has no prefix")
    return Path(base).expanduser() / prefix


def backups(folder: Path, prefix: str | None) -> list[Backup]:
    """The backups of a project (of every project with prefix None), newest first; within one second by file time."""
    found = []
    for p in folder.iterdir() if folder.is_dir() else []:
        m = BUNDLE.match(p.name)
        if m and prefix in (None, m["prefix"]) and p.is_file():
            found.append(Backup(p, datetime.strptime(m["stamp"], STAMP), m["commit"]))
    return sorted(found, key=lambda b: (b.time, b.path.stat().st_mtime_ns), reverse=True)


def _out(root: Path, *args: str) -> str:
    return gitutil.git(root, *args, check=False).decode("utf-8", "replace").strip()


def _head(root: Path) -> str | None:
    return _out(root, "rev-parse", "--verify", "-q", "HEAD") or None


def _since(root: Path, commit: str) -> int | None:
    """Commits after commit up to HEAD; None when commit is unknown here."""
    full = _out(root, "rev-parse", "--verify", "-q", commit + "^{commit}")
    count = _out(root, "rev-list", "--count", f"{full}..HEAD") if full else ""
    return int(count) if count.isdigit() else None


def _first_commit(root: Path) -> datetime:
    times = [int(t) for t in _out(root, "log", "--max-parents=0", "--format=%ct", "HEAD").split() if t.isdigit()]
    return datetime.fromtimestamp(min(times)) if times else datetime.now()


def _commits(n: int | str) -> str:
    return f"{n} commit" + ("" if str(n) == "1" else "s")


def _mb(size: int) -> str:
    return f"{size / 1e6:.1f} MB"


def _write_config(root: Path, config: dict) -> None:
    (root / "project.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                                       newline="\n")


# ------------------------------------------------------------------ backup, list, restore
def backup(root: Path, keep: int = KEEP) -> list[str]:
    config = load_config(root)
    prefix = config.get("prefix")
    if not prefix:
        raise ToolError("project.json has no prefix")
    if not gitutil.is_repo(root):
        raise ToolError("Not a git repository: nothing to back up (P7).")
    head = _head(root)
    if not head:
        raise ToolError("Nothing committed yet. A backup holds commits only: commit first.")
    dirty = [line for line in _out(root, "status", "--porcelain", "--untracked-files=all").splitlines() if line.strip()]
    if dirty:
        raise ToolError(f"{len(dirty)} uncommitted changes, e.g. {dirty[0].strip()}. A backup holds commits only: "
                        "commit them first.")
    folder = backup_folder(config)
    if folder is None:
        raise ToolError(NO_FOLDER)
    if not folder.parent.is_dir():
        raise ToolError(f"Backup folder not reachable: {folder.parent} (is the drive connected?)")
    if root.resolve() in (folder.resolve(), *folder.resolve().parents):
        raise ToolError(f"The backup folder {folder.parent} lies inside the project; choose one outside it.")
    folder.mkdir(exist_ok=True)
    existing = backups(folder, prefix)
    if existing and head.startswith(existing[0].commit):
        return [f"Nothing new since the last backup {existing[0].path.name}; no backup written."]
    target = folder / f"{prefix}_{datetime.now().strftime(STAMP)}_{head[:12]}.bundle"
    partial = target.with_name(target.name + ".partial")
    partial.unlink(missing_ok=True)
    try:
        gitutil.git(root, "bundle", "create", "-q", str(partial), "--all")
        gitutil.git(root, "bundle", "verify", "-q", str(partial))
        os.replace(partial, target)
    except (ToolError, OSError):
        partial.unlink(missing_ok=True)
        raise
    removed = []
    for old in backups(folder, prefix)[keep:]:
        old.path.unlink()
        removed.append(old.path.name)
    out = [f"Backup: {target} ({_mb(target.stat().st_size)}, {_commits(_out(root, 'rev-list', '--count', 'HEAD'))}, "
           f"HEAD {gitutil.describe(root, 'HEAD')})",
           "Checked with git bundle verify; ppp restore brings back every committed state."]
    if removed:
        out.append(f"Removed {len(removed)} older backups beyond the newest {keep}: " + ", ".join(removed))
    return out


def listing(root: Path) -> list[str]:
    config = load_config(root)
    folder = backup_folder(config)
    if folder is None:
        raise ToolError(NO_FOLDER)
    items = backups(folder, config["prefix"])
    if not items:
        return [f"No backups of {config['prefix']} in {folder}."]
    out = [f"Backups of {config['prefix']} in {folder}, newest first ({len(items)}, the newest {KEEP} stay):"]
    for b in items:
        subject = _out(root, "log", "-1", "--format=%h %s", b.commit) or f"{b.commit} (commit unknown here)"
        out.append(f"  {b.time:%Y-%m-%d %H:%M}  {_mb(b.path.stat().st_size):>9}  {subject}  ({b.path.name})")
    since = _since(root, items[0].commit)
    out.append("Since the newest: " + (_commits(since) if since is not None else "its commit is unknown here"))
    return out


def restore(source: Path, target: Path) -> list[str]:
    """Clone a bundle, or the newest bundle in a folder, into a new folder."""
    source = source.expanduser().resolve()
    if source.is_dir():
        found = backups(source, None)
        if not found:
            raise ToolError(f"No backup <prefix>_<time>_<commit>.bundle in {source}; give the project's folder "
                            "inside the backup folder or one .bundle file.")
        prefixes = sorted({BUNDLE.match(b.path.name)["prefix"] for b in found})
        if len(prefixes) > 1:
            raise ToolError(f"Backups of several projects in {source} ({', '.join(prefixes)}); give one .bundle file.")
        bundle = found[0].path
    elif source.is_file():
        bundle = source
    else:
        raise ToolError(f"Not found: {source}")
    target = target.expanduser().resolve()
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ToolError(f"{target} exists and is not empty. ppp restore never overwrites: name a new folder.")
    target.parent.mkdir(parents=True, exist_ok=True)
    gitutil.git(target.parent, "clone", "-q", str(bundle), str(target))
    gitutil.git(target, "remote", "remove", "origin")  # it points to the bundle file
    (target / "exchange").mkdir(exist_ok=True)
    kind = of(load_config(target))
    out = [f"Restored {bundle.name} to {target}: {_commits(_out(target, 'rev-list', '--count', 'HEAD'))}, "
           f"HEAD {gitutil.describe(target, 'HEAD')}. exchange/ is empty: it was never in git."]
    if kind != "local":
        out.append(f"storage {kind}: set the remote again with ppp storage {kind} --remote <url>, or ppp storage local.")
    out.append("Next: open the new folder as the workspace and run ppp check there. Keep working in one folder only; "
               "the old one stays as it is (ABLAGE AB-8).")
    return out


# ------------------------------------------------------------------ check and switch
def check(root: Path, config: dict, rep: Report, now: datetime | None = None) -> None:
    """Storage, remote and, for a local project, sync folder and backup reminder; part of ppp check."""
    kind = config.get("storage")
    if kind not in STORAGES:
        return  # reported by the validation of project.json
    url = remote_url(root)
    if kind != "local":
        if not url:
            rep.warn(f"S storage {kind}, but no remote origin: commits cannot be pushed; set it with "
                     f"ppp storage {kind} --remote <url>")
        elif kind == "github" and kind_of(url) != "github":
            rep.warn(f"S storage github, but the remote origin {url} is not on GitHub; correct it with ppp storage")
        elif kind == "bitbucket" and kind_of(url) == "github":
            rep.warn(f"S storage bitbucket, but the remote origin {url} is on GitHub; correct it with ppp storage")
        if kind == "bitbucket":
            rep.info("S storage bitbucket is prepared, not tested yet (ABLAGE AB-6)")
        return
    if url:
        rep.error(f"S storage local, but remote origin {url}: a push would put the project data on a server; "
                  "after a card remove it with ppp storage local, or switch with ppp storage github --remote <url>")
    service = sync_service(root)
    if service:
        rep.warn(f"S storage local in a {service} folder: the sync can break the git history, which is the only one "
                 "of a local project; keep the project outside the sync folder and the backup folder inside it")
    _reminder(root, config, rep, now or datetime.now())


def _reminder(root: Path, config: dict, rep: Report, now: datetime) -> None:
    if not _head(root):
        return  # nothing committed, nothing to back up
    due = timedelta(days=REMIND_DAYS)
    folder = backup_folder(config)
    if folder is not None and not folder.parent.is_dir():
        rep.info(f"S storage local: backup folder {folder.parent} not reachable; the last backup is unknown")
        return
    items = backups(folder, config["prefix"]) if folder is not None else []
    if not items:
        first = _first_commit(root)
        if now - first <= due:
            rep.info("S storage local: no backup yet" + ("" if folder else "; no backup folder set (ppp settings --backup)"))
        elif folder is None:
            rep.warn(f"S storage local: no backup since the first commit on {first:%Y-%m-%d} and no backup folder. "
                     + NO_FOLDER + " Then offer ppp backup on the same card.")
        else:
            rep.warn(f"S storage local: no backup since the first commit on {first:%Y-%m-%d}; offer ppp backup on a "
                     "card (backups only on request, ABLAGE AB-3)")
        return
    newest = items[0]
    since = _since(root, newest.commit)
    if since is None:
        rep.warn(f"S storage local: the newest backup {newest.path.name} holds a commit unknown here; compare the "
                 "backup folder with this project, then offer ppp backup on a card")
        return
    text = f"last backup {newest.time:%Y-%m-%d %H:%M}, {_commits(since)} since"
    if since and now - newest.time > due:
        rep.warn(f"S storage local: {text}; offer ppp backup on a card (backups only on request, ABLAGE AB-3)")
    else:
        rep.info(f"S storage local: {text}")


def switch(root: Path, kind: str | None, remote: str | None) -> list[str]:
    """Show the storage, or switch it and set or remove the remote origin; never pushes."""
    config = load_config(root)
    if not isinstance(config.get("structureVersion"), int) or config["structureVersion"] < 2:
        raise ToolError("project.json is older than structure version 2: run ppp migrate first.")
    if not gitutil.is_repo(root):
        raise ToolError("Not a git repository (P7).")
    url = remote_url(root)
    if kind is None:
        rep = Report("")
        check(root, config, rep)
        return [f"storage {config.get('storage')}, remote origin {url or 'none'}"] + [m for _, m in rep.lines]
    if kind not in STORAGES:
        raise ToolError(f"storage must be one of {', '.join(STORAGES)}")
    out = []
    if kind == "local":
        if remote:
            raise ToolError("A local project has no remote; leave out --remote.")
        if url:
            gitutil.git(root, "remote", "remove", "origin")
            out.append(f"Removed the remote origin {url}. What was pushed stays on the server: delete the repository "
                       "there if the project data must go.")
        out.append("From now on: commit after each step, never pull or push; back up on request with ppp backup "
                   "(once per computer: ppp settings --backup <folder>).")
    else:
        if remote:
            found = kind_of(remote)
            if kind == "github" and found != "github":
                raise ToolError(f"{remote} is not a GitHub address (github.com).")
            if kind == "bitbucket" and found == "github":
                raise ToolError(f"{remote} is a GitHub address; use ppp storage github.")
            gitutil.git(root, "remote", "set-url" if url else "add", "origin", remote)
            out.append(f"Remote origin: {remote}")
        elif not url:
            raise ToolError(f"storage {kind} needs a remote: create the empty repository on {NAMES[kind]}, then "
                            f"ppp storage {kind} --remote <url>.")
        out.append(f"Push the whole history after a card with git push -u origin main; from then on the project data "
                   f"lies on {NAMES[kind]}.")
        if kind == "bitbucket":
            out.append("Bitbucket is prepared, not tested yet (ABLAGE AB-6).")
    old = config.get("storage")
    if old != kind:
        config["storage"] = kind
        _write_config(root, config)
        out.append("Commit project.json.")
    return [f"storage {old} -> {kind}" if old != kind else f"storage {kind} (unchanged)"] + out
