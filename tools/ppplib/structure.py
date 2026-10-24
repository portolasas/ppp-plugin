"""Project structure: create the core (init), report deviations (check), bring projects to a new version (migrate),
create files from templates (new) and archive packages (archive). Rules: entwurf/PROJEKTSTRUKTUR.md.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

from . import gitutil
from .project import ToolError
from .report import Report

STRUCTURE_VERSION = 1
TEMPLATES = Path(__file__).resolve().parent.parent.parent / "templates"
MODULES = ("power-automate", "power-apps", "sharepoint", "power-bi", "copilot-studio")
MODES = ("small", "medium", "large")
ROLES = ("main", "transfer", "read-only")
CORE_FILES = ("README.md", "AGENTS.md", "CLAUDE.md", "STATE.md", "ROADMAP.md", "project.json")
CORE_DIRS = ("specs", "changes", "changes/archive", "decisions", "components", "solution")
OPTIONAL_DIRS = ("exchange", "inputs", "environments", "tests", "prototype", "lessons", "docs", "legacy")
DOCS_DIRS = ("handbook", "training", "six-sigma", "project")
STATE_SECTIONS = ("Mode", "Active package", "Next step", "Open questions and assumptions to confirm",
                  "Manual changes in the tenant", "Last export")
MODULE_PARTS = {
    "power-automate": {"README.md", "templates", "generator"},
    "power-apps": {"README.md", "screens", "theme", "assets", "generator"},
    "sharepoint": {"README.md", "schema.json", "generator"},
}
NUMBERED = re.compile(r"^(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*$")
AREAS = {"power-automate": "PA", "power-apps": "PAPPS", "sharepoint": "SP", "power-bi": "PBI", "copilot-studio": "CS",
         "solutions": "SOL", "vscode": "VSC", "general": "GEN"}


def fill(text: str, values: dict) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def slug(title: str) -> str:
    s = title.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if not s:
        raise ToolError(f"No usable name in {title!r}")
    return s[:50].rstrip("-")


# ------------------------------------------------------------------ init
def init(root: Path, name: str, prefix: str, modules: list[str], mode: str, language: str,
         solution: str | None) -> list[str]:
    """Create the missing core of a project; existing files stay untouched. Returns the lines to print."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", prefix):
        raise ToolError(f"Prefix must be letters and digits, starting with a letter: {prefix}")
    unknown = [m for m in modules if m not in MODULES]
    if unknown:
        raise ToolError(f"Unknown modules {unknown}; known: {', '.join(MODULES)}")
    if mode not in MODES:
        raise ToolError(f"Mode must be one of {', '.join(MODES)}")
    root.mkdir(parents=True, exist_ok=True)
    if (root / "project.json").exists():
        raise ToolError(f"{root / 'project.json'} exists already; this is a ppp project. Use ppp check.")
    config = {"structureVersion": STRUCTURE_VERSION, "name": name, "prefix": prefix, "mode": mode, "modules": modules,
              "solutions": [{"uniqueName": solution, "role": "main"}] if solution else [], "handbookLanguage": language}
    module_lines = "\n".join(f"  - {m}: [components/{m}/README.md](components/{m}/README.md)" for m in modules) or "  - none yet"
    values = {"name": name, "mode": mode, "module_lines": module_lines}
    created, kept = [], []

    def write(rel: str, text: str):
        path = root / rel
        if path.exists():
            kept.append(rel)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        created.append(rel)

    write("project.json", json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    for tpl in sorted((TEMPLATES / "project").iterdir()):
        target = {"gitignore": ".gitignore", "gitattributes": ".gitattributes"}.get(tpl.name, tpl.name)
        write(target, fill(tpl.read_text(encoding="utf-8"), values))
    for d in ("specs", "changes/archive", "decisions", "solution") + (() if modules else ("components",)):
        if not any((root / d).glob("*")):
            write(f"{d}/.gitkeep", "")
    for m in modules:
        write(f"components/{m}/README.md", (TEMPLATES / "components" / m / "README.md").read_text(encoding="utf-8"))
    (root / "exchange").mkdir(exist_ok=True)
    out = [f"Created ({len(created)}): " + ", ".join(created)]
    if kept:
        out.append(f"Kept as they are ({len(kept)}): " + ", ".join(kept))
    if not gitutil.is_repo(root):
        gitutil.git(root, "init", "-q", "-b", "main")
        out.append("Initialized a git repository on main.")
    return out


# ------------------------------------------------------------------ check
def _validate_config(config: dict, rep: Report) -> None:
    def need(key, kind):
        if not isinstance(config.get(key), kind):
            rep.error(f"S project.json: {key} missing or not {kind.__name__}")
            return False
        return True

    if need("structureVersion", int):
        v = config["structureVersion"]
        if v < STRUCTURE_VERSION:
            rep.error(f"S project.json: structureVersion {v} is outdated; run ppp migrate")
        elif v > STRUCTURE_VERSION:
            rep.error(f"S project.json: structureVersion {v} is newer than this ppp ({STRUCTURE_VERSION}); update ppp")
    need("name", str)
    if need("prefix", str) and not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", config["prefix"]):
        rep.error(f"S project.json: prefix {config['prefix']!r} is not letters and digits")
    if need("mode", str) and config["mode"] not in MODES:
        rep.error(f"S project.json: mode {config['mode']!r} is not one of {', '.join(MODES)}")
    if need("modules", list):
        for m in config["modules"]:
            if m not in MODULES:
                rep.error(f"S project.json: unknown module {m!r}")
    if need("solutions", list):
        roles = [s.get("role") for s in config["solutions"] if isinstance(s, dict)]
        if len(roles) != len(config["solutions"]) or any(not s.get("uniqueName") for s in config["solutions"]):
            rep.error("S project.json: each solution needs uniqueName and role")
        if any(r not in ROLES for r in roles):
            rep.error(f"S project.json: role must be one of {', '.join(ROLES)}")
        for role in ("main", "transfer"):
            if roles.count(role) > 1:
                rep.error(f"S project.json: more than one solution with role {role}")
        if "transfer" in roles and "main" not in roles:
            rep.error("S project.json: a transfer solution needs a main solution")
    need("handbookLanguage", str)
    extra = set(config) - {"structureVersion", "name", "prefix", "mode", "modules", "solutions", "handbookLanguage"}
    if extra:
        rep.error("S project.json: unknown fields " + ", ".join(sorted(extra)))


def _numbered(entries: list[str], where: str, rep: Report, suffix: str = "") -> None:
    numbers: dict[str, str] = {}
    for e in entries:
        stem = e[:-len(suffix)] if suffix and e.endswith(suffix) else e
        m = NUMBERED.match(stem) if (not suffix or e.endswith(suffix)) else None
        if not m:
            rep.error(f"S {where}/{e}: name must be NNN-name{suffix} (three digits, lower case, hyphens)")
            continue
        if m.group(1) in numbers:
            rep.error(f"S {where}: number {m.group(1)} used twice ({numbers[m.group(1)]}, {e})")
        numbers[m.group(1)] = e


def check(root: Path, *notes: str | None) -> Report:
    rep = Report(f"ppp check | {root.name} | structure version {STRUCTURE_VERSION}")
    try:
        config = json.loads((root / "project.json").read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        rep.error("S project.json missing")
        config = {}
    except json.JSONDecodeError as ex:
        rep.error(f"S project.json is not valid JSON: {ex}")
        config = {}
    if config:
        _validate_config(config, rep)

    for f in CORE_FILES:
        if not (root / f).is_file():
            rep.error(f"S core file missing: {f}")
    for d in CORE_DIRS:
        if not (root / d).is_dir():
            rep.error(f"S core folder missing: {d}/")
    if not (root / "exchange").exists():  # not in git, so a fresh clone lacks it
        (root / "exchange").mkdir()
        rep.info("S exchange/ was missing and is created (not in git)")
    allowed = set(CORE_FILES) | {d.split("/")[0] for d in CORE_DIRS} | set(OPTIONAL_DIRS)
    repo = gitutil.is_repo(root)
    for p in sorted(root.iterdir()):
        if p.name.startswith("."):
            continue
        if p.name not in allowed:
            # a leftover outside git stays on one computer only, e.g. after a transition done on the other one
            local = repo and not gitutil.git(root, "ls-files", "--", p.name).strip()
            rep.error(f"S not part of the structure: {p.name}{'/' if p.is_dir() else ''}"
                      + (" (not in git: a local leftover; move what is still needed to legacy/, inputs/ or exchange/, "
                         "then delete it)" if local else ""))
        elif p.name in OPTIONAL_DIRS and not p.is_dir():
            rep.error(f"S {p.name} must be a folder")

    # components/
    modules = [m for m in config.get("modules") or [] if m in MODULES]
    comp = root / "components"
    if comp.is_dir():
        for p in sorted(comp.iterdir()):
            if p.name.startswith("."):
                continue
            if p.name not in modules:
                rep.error(f"S components/{p.name}: not an active module in project.json")
        for m in modules:
            folder = comp / m
            if not (folder / "README.md").is_file():
                rep.error(f"S components/{m}/README.md missing (inventory of the module)")
            parts = MODULE_PARTS.get(m)
            if parts and folder.is_dir():
                for p in sorted(folder.iterdir()):
                    if p.name.startswith(".") or p.name in parts:
                        continue
                    if m == "power-automate" and p.is_file() and p.suffix == ".md":
                        continue  # <flow>.md
                    rep.error(f"S components/{m}/{p.name}: not part of the module structure")

    # changes/, decisions/, specs/
    changes = root / "changes"
    if changes.is_dir():
        entries = [p.name for p in changes.iterdir() if not p.name.startswith(".") and p.name != "archive"]
        archived = [p.name for p in (changes / "archive").iterdir() if not p.name.startswith(".")] if (changes / "archive").is_dir() else []
        _numbered(entries + archived, "changes", rep)
        for name in entries + archived:
            folder = changes / name if name in entries else changes / "archive" / name
            if not folder.is_dir():
                rep.error(f"S changes/{name}: a package is a folder")
                continue
            for f in ("proposal.md", "tasks.md"):
                if not (folder / f).is_file():
                    rep.error(f"S {gitutil.rel(root, folder)}/{f} missing")
    decisions = root / "decisions"
    if decisions.is_dir():
        _numbered([p.name for p in decisions.iterdir() if not p.name.startswith(".")], "decisions", rep, ".md")
    specs = root / "specs"
    if specs.is_dir():
        for p in sorted(specs.iterdir()):
            if not p.name.startswith(".") and not (p.is_file() and p.suffix == ".md"):
                rep.error(f"S specs/{p.name}: specs/ holds one .md file per capability")

    # solution/
    names = [s.get("uniqueName") for s in config.get("solutions") or [] if isinstance(s, dict)]
    sol = root / "solution"
    if sol.is_dir():
        for p in sorted(sol.iterdir()):
            if not p.name.startswith(".") and p.name not in names:
                rep.error(f"S solution/{p.name}: not a solution in project.json")
        for n in names:
            if n and not (sol / n).is_dir():
                rep.info(f"S solution/{n}: not exported yet")

    # docs/
    docs = root / "docs"
    if docs.is_dir():
        for p in sorted(docs.iterdir()):
            if not p.name.startswith(".") and p.name not in DOCS_DIRS:
                rep.error(f"S docs/{p.name}: docs/ holds only {', '.join(DOCS_DIRS)}")

    # STATE.md, CLAUDE.md
    state = root / "STATE.md"
    if state.is_file():
        text = state.read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+?)\s*$", text, re.M)
        for s in STATE_SECTIONS:
            if s not in headings:
                rep.error(f"S STATE.md: section '## {s}' missing (keep the headings of the template)")
        m = re.search(r"^## Mode\s*\n+(\w+)", text, re.M)
        if m and config.get("mode") and m.group(1) != config["mode"]:
            rep.error(f"S STATE.md: mode {m.group(1)} differs from project.json ({config['mode']})")
    claude = root / "CLAUDE.md"
    if claude.is_file() and "AGENTS.md" not in claude.read_text(encoding="utf-8"):
        rep.error("S CLAUDE.md must refer to AGENTS.md")

    # git: settings and no ZIPs
    if repo:
        attrs = (root / ".gitattributes").read_text(encoding="utf-8") if (root / ".gitattributes").is_file() else ""
        if not re.search(r"^\*\s+-text\s*$", attrs, re.M):
            rep.error("S .gitattributes needs '* -text' (exported files must stay byte-identical)")
        if not gitutil.git(root, "check-ignore", "exchange/x.zip", check=False).strip():
            rep.error("S exchange/ must be in .gitignore")
        tracked = gitutil.git(root, "ls-files", "-z").decode("utf-8").split("\0")
        zips = [t for t in tracked if t.lower().endswith(".zip")]
        if zips:
            rep.error(f"S ZIPs in git ({len(zips)}), e.g. {zips[0]}; ZIPs belong in exchange/")
    else:
        rep.error("S not a git repository (P7)")

    for note in notes:
        if note:
            rep.warn(note)
    if not rep.errors:
        rep.ok("S structure as in PROJEKTSTRUKTUR, version " + str(STRUCTURE_VERSION))
    return rep


# ------------------------------------------------------------------ migrate
MIGRATIONS: dict = {}  # from version n to n + 1: function(root, config) -> list of lines


def migrate(root: Path) -> list[str]:
    path = root / "project.json"
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    version = config.get("structureVersion")
    if not isinstance(version, int):
        raise ToolError("project.json has no structureVersion")
    if version == STRUCTURE_VERSION:
        return [f"Structure version {version} is current; nothing to migrate."]
    if version > STRUCTURE_VERSION:
        raise ToolError(f"structureVersion {version} is newer than this ppp ({STRUCTURE_VERSION}); update ppp")
    out = []
    while version < STRUCTURE_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            raise ToolError(f"No migration from structure version {version}")
        out += step(root, config)
        version += 1
        config["structureVersion"] = version
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        out.append(f"Now at structure version {version}.")
    return out


def register_solution(root: Path, unique_name: str) -> str | None:
    """Add a newly unpacked solution to project.json: the first as main, <prefix>Transfer as transfer, further ones
    read-only (S-10)."""
    path = root / "project.json"
    if not path.is_file():
        return None
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    solutions = config.setdefault("solutions", [])
    if any(s.get("uniqueName") == unique_name for s in solutions):
        return None
    roles = [s.get("role") for s in solutions]
    if "main" not in roles:
        role = "main"
    elif unique_name == f"{config.get('prefix')}Transfer" and "transfer" not in roles:
        role = "transfer"
    else:
        role = "read-only"
    solutions.append({"uniqueName": unique_name, "role": role})
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    note = {"main": "",
            "transfer": " (packages are built from it; the main solution stays the complete reference)",
            "read-only": " (there is a main solution already; change the role there if this one is the main solution)"}
    return f"Added to project.json as {role} solution: {unique_name}" + note[role]


# ------------------------------------------------------------------ new, archive
def _next_number(names: list[str]) -> str:
    used = [int(n[:3]) for n in names if re.match(r"^\d{3}-", n)]
    return f"{max(used, default=0) + 1:03d}"


def new(root: Path, kind: str, title: str, machine: str = "MAC") -> Path:
    today = date.today().isoformat()
    if kind == "package":
        changes = root / "changes"
        names = [p.name for p in changes.iterdir()] + [p.name for p in (changes / "archive").iterdir()]
        number = _next_number(names)
        folder = changes / f"{number}-{slug(title)}"
        folder.mkdir(parents=True)
        for f in ("proposal.md", "tasks.md"):
            (folder / f).write_bytes(fill((TEMPLATES / "files" / f).read_text(encoding="utf-8"),
                                          {"number": number, "title": title}).encode("utf-8"))
        return folder
    if kind == "design":
        folder = _package(root, title)
        path = folder / "design.md"
        number = folder.name[:3]
        text = fill((TEMPLATES / "files" / "design.md").read_text(encoding="utf-8"), {"number": number, "title": folder.name[4:]})
    elif kind == "decision":
        number = _next_number([p.name for p in (root / "decisions").iterdir()])
        path = root / "decisions" / f"{number}-{slug(title)}.md"
        text = fill((TEMPLATES / "files" / "decision.md").read_text(encoding="utf-8"), {"number": number, "title": title, "date": today})
    elif kind == "spec":
        path = root / "specs" / f"{slug(title)}.md"
        text = fill((TEMPLATES / "files" / "spec.md").read_text(encoding="utf-8"), {"title": title})
    elif kind == "lesson":
        area, _, rest = title.partition(":")
        if area.strip() not in AREAS or not rest.strip():
            raise ToolError("Lesson title as '<area>: <title>' with area one of " + ", ".join(AREAS))
        code = f"{AREAS[area.strip()]}-{today.replace('-', '')}-{machine}"
        folder = root / "lessons"
        folder.mkdir(exist_ok=True)
        n = 1 + max((int(p.stem.rsplit("-", 1)[1]) for p in folder.glob(f"{code}-*.md")), default=0)
        lesson_id = f"{code}-{n:02d}"
        path = folder / f"{lesson_id}.md"
        text = fill((TEMPLATES / "files" / "lesson.md").read_text(encoding="utf-8"),
                    {"id": lesson_id, "title": rest.strip(), "date": today}).replace(
            "area: <power-automate | power-apps | sharepoint | power-bi | copilot-studio | solutions | vscode | general>",
            f"area: {area.strip()}")
    else:
        raise ToolError(f"Unknown kind {kind}")
    if path.exists():
        raise ToolError(f"Exists already: {gitutil.rel(root, path)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    _drop_placeholder(path.parent)
    return path


def _drop_placeholder(folder: Path) -> None:
    """.gitkeep only keeps an empty core folder in git."""
    keep = folder / ".gitkeep"
    if keep.exists() and any(p.name != ".gitkeep" for p in folder.iterdir()):
        keep.unlink()


def spec_delta(root: Path, package: str, capability: str) -> Path:
    folder = _package(root, package)
    path = folder / "specs" / f"{slug(capability)}.md"
    if path.exists():
        raise ToolError(f"Exists already: {gitutil.rel(root, path)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fill((TEMPLATES / "files" / "spec-delta.md").read_text(encoding="utf-8"),
                          {"title": capability, "capability": slug(capability)}).encode("utf-8"))
    return path


def _package(root: Path, ref: str) -> Path:
    """An active package by number (003) or folder name."""
    hits = [p for p in (root / "changes").iterdir() if p.is_dir() and p.name != "archive" and (p.name == ref or p.name[:3] == ref.zfill(3))]
    if len(hits) != 1:
        raise ToolError(f"No unique active package {ref!r} in changes/")
    return hits[0]


def archive(root: Path, ref: str) -> list[str]:
    folder = _package(root, ref)
    tasks = (folder / "tasks.md").read_text(encoding="utf-8") if (folder / "tasks.md").is_file() else ""
    open_tasks = re.findall(r"^\s*- \[ \] (.+)$", tasks, re.M)
    if open_tasks:
        raise ToolError(f"{len(open_tasks)} open tasks in {folder.name}/tasks.md, e.g. {open_tasks[0]!r}")
    deltas = sorted((folder / "specs").glob("*.md")) if (folder / "specs").is_dir() else []
    target = root / "changes" / "archive" / folder.name
    if target.exists():
        raise ToolError(f"{gitutil.rel(root, target)} exists already; not overwritten.")
    if gitutil.is_repo(root) and gitutil.git(root, "ls-files", gitutil.rel(root, folder)).strip():
        old, new = gitutil.rel(root, folder), gitutil.rel(root, target)
        try:
            gitutil.git(root, "mv", old, new)
        except ToolError as ex:
            # in OneDrive folders on Windows git mv was denied while a plain move worked (SOL-20261024-WIN-01)
            try:
                shutil.move(str(folder), str(target))
            except OSError as move_error:
                raise ToolError(f"{ex}; a plain move failed too ({move_error}). Ask the user.") from move_error
            gitutil.git(root, "add", "-A", "--", old, new)
    else:
        shutil.move(str(folder), str(target))
    keep = root / "changes" / "archive" / ".gitkeep"
    if keep.exists():
        keep.unlink()
    out = [f"Archived {folder.name} to changes/archive/."]
    if deltas:
        out.append("Spec changes to merge into specs/ (if not done yet): " + ", ".join(d.name for d in deltas))
    out.append("Set the package to done in ROADMAP.md.")
    return out
