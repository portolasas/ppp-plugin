"""Upload of the Copilot session logs of ppp projects to the user's private sessions repository (PLUGIN PL-20).

A learning session on another computer reads them from a clone of that repository like a home folder (--home).
Copilot keeps each session in ~/.copilot/session-state/<id>/. `ppp sessions` copies the sessions whose working folder
holds a project.json and that changed since the last upload of this computer to <repository>/.copilot/session-state/<id>/,
commits and pushes. Lock files and the agent's scratch folder files/ stay behind; a file over 95 MB is stored gzipped as
<name>.gz, because GitHub refuses files over 100 MB. The repository folder is `sessionsRepo` in ~/.ppp/settings.json,
the time of the last upload ~/.ppp/sessions.json; it advances only after a push.
"""
from __future__ import annotations

import gzip
import itertools
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

from . import gitutil
from .agent import PPP_HOME
from .project import ToolError
from .usage import _project

MARKER = PPP_HOME / "sessions.json"
SKIP_DIRS = {"files"}
SKIP_SUFFIXES = (".lock", ".hold")
LIMIT = 95 * 1024 * 1024


def places(folder: Path) -> list[str]:
    """Working folder and git root of a session, from session.start and workspace.yaml."""
    out = []
    try:
        with open(folder / "events.jsonl", encoding="utf-8", errors="replace") as f:
            for line in itertools.islice(f, 50):
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("type") == "session.start":
                    out.append(((e.get("data") or {}).get("context") or {}).get("cwd") or "")
                    break
    except OSError:
        pass
    ws = folder / "workspace.yaml"
    if ws.is_file():
        for line in ws.read_text(encoding="utf-8", errors="replace").splitlines():
            key, _, value = line.partition(":")
            if key in ("cwd", "git_root"):
                out.append(value.strip())
    return [p for p in out if p]


def pick(home: Path, since: float) -> list[tuple[float, Path, str]]:
    """Sessions of ppp projects whose log changed at or after since: (time, folder, project), oldest first."""
    picked = []
    for events in (home / ".copilot" / "session-state").glob("*/events.jsonl"):
        mtime = events.stat().st_mtime
        if mtime < since:
            continue
        where = [p for p in places(events.parent) if (Path(p) / "project.json").is_file()]
        if where:
            picked.append((mtime, events.parent, _project(where[0])))
    return sorted(picked)


def copy_session(src: Path, dst: Path) -> int:
    """Copy one session folder without lock files and files/; returns the bytes written."""
    size = 0
    for root, dirs, names in os.walk(src):
        if Path(root) == src:
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            if name.endswith(SKIP_SUFFIXES):
                continue
            f = Path(root) / name
            out = dst / f.relative_to(src)
            out.parent.mkdir(parents=True, exist_ok=True)
            if f.stat().st_size > LIMIT:
                with open(f, "rb") as i, gzip.open(out.with_name(name + ".gz"), "wb") as o:
                    shutil.copyfileobj(i, o)
                out.unlink(missing_ok=True)
                out = out.with_name(name + ".gz")
            else:
                shutil.copyfile(f, out)
            size += out.stat().st_size
    return size


def _count(n: int) -> str:
    return f"{n} session" + ("" if n == 1 else "s")


def last_upload() -> float:
    try:
        return datetime.fromisoformat(json.loads(MARKER.read_text(encoding="utf-8"))["lastUpload"]).timestamp()
    except (OSError, ValueError, KeyError, TypeError):
        return 0.0


def _mark(when: float) -> None:
    PPP_HOME.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromtimestamp(when).astimezone().isoformat(timespec="seconds")
    MARKER.write_text(json.dumps({"lastUpload": stamp}) + "\n", encoding="utf-8", newline="\n")


def upload(repo: Path, home: Path, since: float | None = None, dry_run: bool = False) -> list[str]:
    """Copy, commit and push the picked sessions; since None means since the last upload of this computer."""
    if not gitutil.is_repo(repo):
        raise ToolError(f"Not a git clone: {repo}. Clone the sessions repository and save its folder with "
                        "ppp settings --sessions <folder>.")
    started = time.time()
    since = last_upload() if since is None else since
    picked = pick(home, since)
    after = datetime.fromtimestamp(since).strftime("%Y-%m-%d %H:%M") if since else "the start"
    out = [f"  {datetime.fromtimestamp(m):%Y-%m-%d %H:%M}  {folder.name}  {project}" for m, folder, project in picked]
    out.append(f"{_count(len(picked))} of ppp projects changed since {after}" + (" (dry run: nothing copied)" if dry_run else ""))
    if dry_run:
        return out
    if picked:
        gitutil.git(repo, "pull", "-q", "--rebase", "--autostash")
        target = repo / ".copilot" / "session-state"
        size = sum(copy_session(folder, target / folder.name) for _, folder, _ in picked)
        gitutil.git(repo, "add", "-A", ".copilot")
        if not gitutil.git(repo, "diff", "--cached", "--name-only", "--", ".copilot").strip():
            out.append("nothing new to push")
        else:
            projects = ", ".join(sorted({p for _, _, p in picked}))
            day = datetime.fromtimestamp(since).date().isoformat() if since else "start"
            gitutil.git(repo, "commit", "-q", "-m", f"{_count(len(picked))}, {projects}, since {day}")
            gitutil.git(repo, "push", "-q")
            out.append(f"pushed to {repo} ({size / 1e6:.1f} MB in the copied files)")
    _mark(started)
    return out
