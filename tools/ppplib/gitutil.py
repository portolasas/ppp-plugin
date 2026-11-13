"""Git as the comparison base: the committed state of a solution folder."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .project import ToolError


def git(root: Path, *args: str, check: bool = True, data: bytes | None = None) -> bytes:
    exe = shutil.which("git")
    if not exe:
        raise ToolError("git not found in PATH.")
    proc = subprocess.run([exe, "-c", "core.quotepath=off", *args], cwd=root, input=data,
                          capture_output=True)
    if check and proc.returncode != 0:
        raise ToolError(f"git {' '.join(args)} failed: {proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout


def is_repo(root: Path) -> bool:
    try:
        return git(root, "rev-parse", "--is-inside-work-tree", check=False).strip() == b"true"
    except ToolError:
        return False


# Copies a sync service writes when two computers change a file at once: iCloud "name(1).ext" or "name 2.ext",
# OneDrive "name-COMPUTER.ext", Dropbox "name (conflicted copy ...).ext"
CONFLICT_COPY = re.compile(r"^(?P<stem>.+?)(?: ?\(\d+\)| \d+|-[A-Z0-9][A-Z0-9-]{4,}| \([^)]*conflicted copy[^)]*\))"
                           r"(?P<ext>\.[^.]+)?$")


def conflict_copies(root: Path) -> list[tuple[str, str, bool]]:
    """Untracked files named like a sync service's copy of a tracked file: (copy, original, original missing)."""
    def files(*args: str) -> list[str]:
        return [f for f in git(root, "ls-files", "-z", *args).decode("utf-8", "replace").split("\0") if f]

    tracked = set(files())
    found = []
    for path in files("--others", "--exclude-standard"):
        folder, _, name = path.rpartition("/")
        m = CONFLICT_COPY.match(name)
        original = (folder + "/" if folder else "") + m["stem"] + (m["ext"] or "") if m else None
        if original in tracked:
            found.append((path, original, not (root / original).exists()))
    return sorted(found)


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def tracked_files(root: Path, ref: str, folder: Path, missing_ok: bool = False) -> list[str]:
    """Paths relative to the folder, as stored at ref."""
    prefix = rel(root, folder) + "/"
    try:
        out = git(root, "ls-tree", "-r", "-z", "--name-only", ref, "--", prefix)
    except ToolError:
        if missing_ok:
            return []
        raise
    return sorted(p[len(prefix):] for p in out.decode("utf-8").split("\0") if p)


def read_blobs(root: Path, ref: str, paths: list[str]) -> dict[str, bytes]:
    """Contents of several files at ref (repo-relative paths) in one git call."""
    if not paths:
        return {}
    request = "".join(f"{ref}:{p}\n" for p in paths).encode("utf-8")
    out = git(root, "cat-file", "--batch", data=request)
    blobs, pos = {}, 0
    for p in paths:
        end = out.index(b"\n", pos)
        header = out[pos:end].decode("utf-8")
        pos = end + 1
        if header.endswith(" missing"):
            continue
        size = int(header.split()[2])
        blobs[p] = out[pos:pos + size]
        pos += size + 1
    return blobs


def version_of(solution_xml: bytes) -> str | None:
    m = re.search(rb"<Version>([^<]+)</Version>", solution_xml)
    return m.group(1).decode() if m else None


def tenant_commit(root: Path, folder: Path, version: str | None = None) -> str:
    """The commit that holds the tenant's state of a version (default: the version committed now): the commit that
    brought the version into Other/Solution.xml, or the latest one after it with the subject 'Export <name> <version>'
    that still has this version. An export from the portal raises the version; an export with pac keeps it. Taken
    after an import, it holds what the server rewrote, and without this rule it would never become the base
    (VERBUNDEN VB-8). A commit of work in between has another subject and stays out."""
    path = rel(root, folder) + "/Other/Solution.xml"
    if version is None:
        head = read_blobs(root, "HEAD", [path]).get(path) if git(root, "rev-parse", "--verify", "-q", "HEAD", check=False) else None
        if head is None:
            raise ToolError(f"{path} is not committed. Commit the export first (ppp unpack does it).")
        version = version_of(head)
    tag = f"<Version>{version}</Version>"

    def has_version(commit: str) -> bool:
        return tag.encode() in (read_blobs(root, commit, [path]).get(path) or b"")

    introduced = next((c for c in git(root, "log", "--format=%H", "-S", tag, "--", path).decode().split() if has_version(c)), None)
    if introduced is None:
        raise ToolError(f"No commit found that introduced {tag} in {path}. Use --base <ref>.")
    later = git(root, "log", "--format=%H%x09%s", f"{introduced}..HEAD", "--", rel(root, folder)).decode("utf-8", "replace")
    for line in later.splitlines():  # newest first
        commit, _, subject = line.partition("\t")
        if subject == f"Export {folder.name} {version}" and has_version(commit):
            return commit
    return introduced


def base_commit(root: Path, folder: Path) -> str:
    """The comparison base of the solution folder: the tenant's state of the version committed now (tenant_commit)."""
    return tenant_commit(root, folder)


def describe(root: Path, ref: str) -> str:
    return git(root, "log", "-1", "--format=%h %s", ref).decode("utf-8", "replace").strip()
