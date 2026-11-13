"""Unpack and pack solutions with pac, set the version, summarize the content."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .gitutil import read_blobs, rel, tracked_files
from .project import ToolError
from .verify import SOLUTION_XML, canvas_apps, files_of, stable

PAC_EXTENSION = "microsoft-isvexptools.powerplatform-vscode"


def pac_candidates(home: Path, appdata: str | None) -> list[Path]:
    """Where pac lies when it is not in PATH: the VS Code extension Power Platform Tools
    (Windows: pac/tools/pac.exe, Mac: pac/pac) and the dotnet tool."""
    exe = "pac.exe" if sys.platform == "win32" else "pac"
    storages = []
    for app in ("Code", "Code - Insiders"):
        if appdata:
            storages.append(Path(appdata) / app / "User" / "globalStorage")
        storages += [home / "Library" / "Application Support" / app / "User" / "globalStorage",
                     home / ".config" / app / "User" / "globalStorage"]
    found = [s / PAC_EXTENSION / "pac" / sub for s in storages for sub in (Path("tools") / exe, Path(exe))]
    return found + [home / ".dotnet" / "tools" / exe]


def pac() -> str:
    exe = shutil.which("pac")
    if exe:
        return exe
    for candidate in pac_candidates(Path.home(), os.environ.get("APPDATA")):
        if candidate.is_file():
            return str(candidate)
    raise ToolError("pac (Power Platform CLI) not found: not in PATH, not in the VS Code extension Power Platform "
                    "Tools and not in ~/.dotnet/tools. Install the extension or the dotnet tool.")


def remove_tree(path: Path) -> None:
    """Remove a folder also when parts of it are read-only (OneDrive marks folders read-only on Windows)."""
    def writable(func, name, _exc):
        for p in (name, os.path.dirname(name)):
            try:
                os.chmod(p, os.stat(p).st_mode | stat.S_IWRITE)
            except OSError:
                pass
        func(name)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=writable)
    else:
        shutil.rmtree(path, onerror=writable)


def run_pac(*args: str) -> str:
    proc = subprocess.run([pac(), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0 or re.search(r"^Error:", out, re.M):
        raise ToolError(f"pac {' '.join(args[:2])} failed:\n{out[-2000:]}")
    return out


def manifest(xml: bytes) -> dict:
    get = lambda tag: (re.search(rb"<" + tag + rb">([^<]*)</" + tag + rb">", xml) or [None, b""])[1].decode()
    return {"uniqueName": get(b"UniqueName"), "version": get(b"Version"), "managed": get(b"Managed") == "1"}


def publisher_of(xml: bytes | str) -> dict | None:
    """The <Publisher> block of a Solution.xml: uniqueName, displayName (description of its first LocalizedName, empty
    when there is none), prefix (CustomizationPrefix) and optionValuePrefix (CustomizationOptionValuePrefix as a number,
    None when it is not one). None when there is no block with a unique name, or the text is not XML."""
    data = xml.encode("utf-8") if isinstance(xml, str) else xml
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return None
    block = next(iter(root.findall("./SolutionManifest/Publisher")), None)
    if block is None:
        return None
    text = lambda path: (block.findtext(path) or "").strip()
    name = text("UniqueName")
    if not name:
        return None
    named = block.find("./LocalizedNames/LocalizedName")
    option = text("CustomizationOptionValuePrefix")
    return {"uniqueName": name, "displayName": (named.get("description") or "").strip() if named is not None else "",
            "prefix": text("CustomizationPrefix"), "optionValuePrefix": int(option) if re.fullmatch(r"\d{1,9}", option) else None}


def read_publisher(source: Path) -> dict | None:
    """publisher_of for the Solution.xml of an unpacked solution: source is its folder or the file itself.
    A missing file is an error; no Publisher block gives None."""
    path = source / SOLUTION_XML if source.is_dir() else source
    if not path.is_file():
        raise ToolError(f"No {SOLUTION_XML} in {source}: give the folder of an unpacked solution or the path to {SOLUTION_XML}.")
    return publisher_of(path.read_bytes())


def zip_manifest(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        name = next((n for n in z.namelist() if n.lower() == "solution.xml"), None)
        if not name:
            raise ToolError(f"No solution.xml in {path.name}; not a solution export.")
        return manifest(z.read(name))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def set_version(folder: Path, version: str) -> str:
    """Set <Version> in Other/Solution.xml; every other byte stays as it is."""
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ToolError(f"Version must have four parts: {version}")
    path = folder / SOLUTION_XML
    data = path.read_bytes()
    found = list(re.finditer(rb"<Version>([^<]*)</Version>", data))
    if len(found) != 1:
        raise ToolError(f"Expected exactly one <Version> in {SOLUTION_XML}, found {len(found)}")
    m = found[0]
    path.write_bytes(data[:m.start(1)] + version.encode() + data[m.end(1):])
    return m.group(1).decode()


def summary(folder: Path) -> list[str]:
    """Components of an unpacked solution in a few lines."""
    info = manifest((folder / SOLUTION_XML).read_bytes())
    files = files_of(folder)
    flows = sorted(f.split("/")[-1] for f in files if f.startswith("Workflows/") and f.endswith(".json"))
    envvars = sorted({f.split("/")[1] for f in files if f.startswith("environmentvariabledefinitions/")})
    custom = (folder / "Other" / "Customizations.xml").read_bytes().decode("utf-8-sig", "replace")
    connrefs = re.findall(r'connectionreferencelogicalname="([^"]+)"', custom)
    bots = sorted({f.split("/")[1] for f in files if f.lower().startswith("botcomponents/")})
    names = [re.sub(r"-[0-9A-Fa-f-]{36}\.json$", "", f) for f in flows]
    out = [f"Solution {info['uniqueName']} {info['version']}" + (" (managed)" if info["managed"] else ""),
           f"  Flows ({len(flows)}): " + ", ".join(names)]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        out.append("  WARNING duplicate flow names (scaffold created twice? SOL-20261009-MAC-01): " + ", ".join(duplicates))
    apps = canvas_apps(folder)
    if apps:
        names = []
        for app in apps:
            meta = (folder / "CanvasApps" / f"{app}.meta.xml").read_bytes()
            display = (re.search(rb"<DisplayName>([^<]*)</DisplayName>", meta) or [None, b""])[1].decode()
            names.append(f"{display} ({app})" if display else app)
        out.append(f"  Apps ({len(apps)}): " + ", ".join(names))
    if envvars:
        out.append(f"  Environment variables ({len(envvars)}): " + ", ".join(envvars))
    if connrefs:
        out.append(f"  Connection references ({len(connrefs)}): " + ", ".join(connrefs))
    if bots:
        out.append(f"  Bot components ({len(bots)}): " + ", ".join(bots))
    other = sorted({f.split("/")[0] for f in files} - {"Other", "Workflows", "CanvasApps", "environmentvariabledefinitions", "botcomponents"})
    if other:
        out.append("  Other folders: " + ", ".join(other))
    return out


def unpack(zip_path: Path, target: Path) -> None:
    """Replace target with the content of the export; deleted components disappear.
    pac unpacks into a temporary folder first, so a failing pac leaves target as it was."""
    pac()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    try:
        fresh = temp / target.name
        run_pac("solution", "unpack", "--zipfile", str(zip_path), "--folder", str(fresh), "--packagetype", "Unmanaged")
        if target.exists():
            try:
                remove_tree(target)
            except OSError as ex:
                raise ToolError(f"{target.name} could not be replaced ({ex}). Restore it with "
                                f"git restore --source=HEAD -- solution/{target.name} and run ppp unpack again.") from ex
        fresh.rename(target)
    finally:
        if temp.exists():
            remove_tree(temp)


def keep_volatile(root: Path, folder: Path) -> list[str]:
    """After unpacking an export: the metadata file of an app that differs from the committed one only in the values the
    server rewrites on every export (verify.stable) gets its committed bytes back, if every other file of the app is
    as committed. So an app nobody changed is no change in git and no commit. Returns the files put back."""
    apps = folder / "CanvasApps"
    tracked = [f for f in tracked_files(root, "HEAD", folder, missing_ok=True) if f.startswith("CanvasApps/")] if apps.is_dir() else []
    if not tracked:
        return []
    prefix = rel(root, folder) + "/"
    committed = {k[len(prefix):]: v for k, v in read_blobs(root, "HEAD", [prefix + f for f in tracked]).items()}
    kept = []
    for meta in sorted(apps.glob("*.meta.xml")):
        name, app = f"CanvasApps/{meta.name}", meta.name[:-len(".meta.xml")] + "_"
        old, new = committed.get(name), meta.read_bytes()
        if old is None or old == new or stable(name, old) != stable(name, new):
            continue
        now = {f"CanvasApps/{p.name}": p.read_bytes() for p in apps.iterdir() if p.is_file() and p.name.startswith(app)}
        if now == {f: data for f, data in committed.items() if f.startswith("CanvasApps/" + app)}:
            meta.write_bytes(old)
            kept.append(name)
    return kept


def pack(folder: Path, out: Path) -> None:
    if out.exists():
        raise ToolError(f"Target exists, not overwritten: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    run_pac("solution", "pack", "--zipfile", str(out), "--folder", str(folder), "--packagetype", "Unmanaged")
    # pac must take the flows over byte for byte
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        for f in files_of(folder):
            if f.startswith("Workflows/") and f.endswith(".json"):
                if f not in names:
                    raise ToolError(f"pac left out {f}")
                if z.read(f) != (folder / f).read_bytes():
                    raise ToolError(f"pac changed {f} while packing")
