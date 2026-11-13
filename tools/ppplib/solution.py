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
from xml.sax.saxutils import escape

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


# The commands of pac that ppp runs locally, without an environment, each with the options it may carry, in lower case.
# A call against the tenant goes only through tenant.run, which names the environment itself; here --environment is
# refused, as every command and option not in this list.
LOCAL = {("solution", "pack"): {"--zipfile", "--folder", "--packagetype"},
         ("solution", "unpack"): {"--zipfile", "--folder", "--packagetype"},
         ("solution", "create-settings"): {"--solution-zip", "--settings-file"}}


def check_local(args: tuple[str, ...] | list[str]) -> None:
    """Refuse a local call of pac that is not on LOCAL, before pac starts: an unknown command or option, an option twice,
    an option without a value or with a value that begins with --, and every --environment."""
    verb = tuple(args[:2])
    if verb not in LOCAL:
        raise ToolError(f"pac {' '.join(args[:2])} is not a command ppp runs locally.")
    seen, i = set(), 2
    while i < len(args):
        option = str(args[i]).lower()
        if option.startswith("--env") or option in ("-env", "-e"):
            raise ToolError(f"pac {' '.join(verb)} runs locally: {args[i]} goes only through tenant.run, which names the environment.")
        if not option.startswith("--") or option not in LOCAL[verb] or option in seen:
            raise ToolError(f"pac {' '.join(verb)}: {args[i]} is not an option ppp uses locally, or it stands twice.")
        if i + 1 >= len(args) or str(args[i + 1]).startswith("--"):
            raise ToolError(f"pac {' '.join(verb)}: {args[i]} needs a value.")
        seen.add(option)
        i += 2


def run_pac(*args: str) -> str:
    """A local call of pac (pack, unpack, create-settings), after check_local."""
    check_local(args)
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


EMPTY_TEMPLATE = Path(__file__).resolve().parent.parent.parent / "templates" / "solution"
EMPTY_VERSION = "1.0.0.1"
EMPTY_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def empty_solution(folder: Path, name: str, publisher: dict) -> Path:
    """An unpacked solution without components (ERWEITERUNGEN A.4): the template plugin/templates/solution/ with the
    unique name, version EMPTY_VERSION and the four values of the publisher (uniqueName, displayName, prefix,
    optionValuePrefix, as agent.publisher_of gives them) in Other/Solution.xml, XML-escaped; Other/Customizations.xml
    byte for byte the template's. The template has the form of a pac unpack (BOM, CRLF), which pac packs as it is."""
    if not (isinstance(name, str) and EMPTY_NAME.fullmatch(name)):
        raise ToolError(f"{name!r} is not the unique name of a solution: letters, digits and underscores, no digit first.")
    values = {"solution": name, "version": EMPTY_VERSION, "publisher": publisher["uniqueName"],
              "publisherDisplay": publisher["displayName"], "prefix": publisher["prefix"],
              "optionValuePrefix": str(publisher["optionValuePrefix"])}
    text = (EMPTY_TEMPLATE / "Other" / "Solution.xml").read_bytes().decode("utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", escape(str(value), {'"': "&quot;"}))
    if "{{" in text:
        raise ToolError(f"The template {EMPTY_TEMPLATE / 'Other' / 'Solution.xml'} has a placeholder ppp does not fill.")
    if folder.exists() and any(folder.iterdir()):
        raise ToolError(f"Target exists, not overwritten: {folder}")
    (folder / "Other").mkdir(parents=True, exist_ok=True)
    (folder / SOLUTION_XML).write_bytes(text.encode("utf-8"))
    (folder / "Other" / "Customizations.xml").write_bytes((EMPTY_TEMPLATE / "Other" / "Customizations.xml").read_bytes())
    return folder


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
