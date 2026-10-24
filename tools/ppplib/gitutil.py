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


def base_commit(root: Path, folder: Path) -> str:
    """The commit that brought the version now committed in Other/Solution.xml: last export or last package."""
    path = rel(root, folder) + "/Other/Solution.xml"
    head = read_blobs(root, "HEAD", [path]).get(path) if git(root, "rev-parse", "--verify", "-q", "HEAD", check=False) else None
    if head is None:
        raise ToolError(f"{path} is not committed. Commit the export first (ppp unpack does it).")
    tag = f"<Version>{version_of(head)}</Version>"
    for commit in git(root, "log", "--format=%H", "-S", tag, "--", path).decode().split():
        blob = read_blobs(root, commit, [path]).get(path) or b""
        if tag.encode() in blob:
            return commit
    raise ToolError(f"No commit found that introduced {tag} in {path}. Use --base <ref>.")


def describe(root: Path, ref: str) -> str:
    return git(root, "log", "-1", "--format=%h %s", ref).decode("utf-8", "replace").strip()
