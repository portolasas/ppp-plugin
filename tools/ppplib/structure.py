"""Project structure: create the core (init), report deviations (check), bring projects to a new version (migrate),
create files from templates (new) and archive packages (archive). Rules: entwurf/PROJEKTSTRUKTUR.md.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
from datetime import date
from pathlib import Path

from . import gitutil, solution, storage
from . import walk as walkfile
from .project import ToolError, check_publisher_name
from .report import Report

STRUCTURE_VERSION = 2  # 2 since 09.11.: storage in project.json (ABLAGE AB-9)
TEMPLATES = Path(__file__).resolve().parent.parent.parent / "templates"
MODULES = ("power-automate", "power-apps", "sharepoint", "power-bi", "copilot-studio")
MODES = ("small", "medium", "large")
TRAINING_FORMATS = ("word", "powerpoint", "both")  # optional; ppp-docs asks before the documents for users are built
ROLES = ("main", "transfer", "read-only")
# A connected project (VERBUNDEN VB-1, VB-2, VB-11): project.json names its environment by an alias, and
# environments/<alias>.json says where it is, what it is for and whether the solution is in productive use there
ENVIRONMENT_ROLES = ("development", "test", "production")
ALIAS = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
ENVIRONMENT_URL = re.compile(r"https://[A-Za-z0-9.-]+/?")
CORE_FILES =("README.md", "AGENTS.md", "CLAUDE.md", "STATE.md", "ROADMAP.md", "project.json")
CORE_DIRS = ("specs", "changes", "changes/archive", "decisions", "components", "solution")
OPTIONAL_DIRS = ("exchange", "inputs", "environments", "tests", "prototype", "lessons", "docs", "legacy")
DOCS_DIRS = ("handbook", "training", "six-sigma", "project")
STATE_SECTIONS = ("Mode", "Active package", "Next step", "Open questions and assumptions to confirm",
                  "Manual changes in the tenant", "Last export")
# STATE.md holds the current state only; the session start passes about 3,000 characters of it in Claude Code and 9,000
# in VS Code, the sections that matter first (ppp_hook). Above this a warning (review 07.11.: projects with 9 and 22 KB).
STATE_BUDGET = 6_000
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
         solution: str | None, kind: str = "github", environment: str | None = None, confirm_import: bool = True,
         publisher: str | None = None) -> list[str]:
    """Create the missing core of a project with its storage (ABLAGE AB-1); existing files stay untouched. With the
    display name of an environment the project is connected to it (VERBUNDEN VB-1 to VB-3); without one it is offline.
    With the unique name of the Publisher project.json names it (the four values are in ~/.ppp/settings.json).
    Returns the lines to print."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", prefix):
        raise ToolError(f"Prefix must be letters and digits, starting with a letter: {prefix}")
    if publisher:
        check_publisher_name(publisher)
    unknown = [m for m in modules if m not in MODULES]
    if unknown:
        raise ToolError(f"Unknown modules {unknown}; known: {', '.join(MODULES)}")
    if mode not in MODES:
        raise ToolError(f"Mode must be one of {', '.join(MODES)}")
    if kind == "bitbucket":
        raise ToolError(storage.BITBUCKET_LATER)
    if kind not in storage.STORAGES:
        raise ToolError("Storage must be github or local")
    root.mkdir(parents=True, exist_ok=True)
    if (root / "project.json").exists():
        raise ToolError(f"{root / 'project.json'} exists already; this is a ppp project. Use ppp check.")
    alias = slug(environment) if environment else None
    config = {"structureVersion": STRUCTURE_VERSION, "name": name, "prefix": prefix,
              **({"publisher": publisher} if publisher else {}), "mode": mode, "storage": kind,
              **({"environment": alias, "confirmImport": confirm_import} if alias else {}), "modules": modules,
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
    if alias:  # the environment the work starts in; its address comes from the tenant, the plugin holds none
        write(f"environments/{alias}.json", json.dumps({"name": environment, "role": "development", "inUse": False},
                                                       indent=2, ensure_ascii=False) + "\n")
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
    if kind == "github":
        out.append("Storage github: set the remote origin (gh repo create --private --source . --remote origin, or "
                   "ppp storage github --remote <url>), then commit and push.")
    else:
        out.append("Storage local: git without a remote; commit after each step, never push. Back up on request with "
                   "ppp backup" + ("." if storage.backup_folder(config) else
                                   "; no backup folder yet: ask for one on a card, ppp settings --backup <folder>."))
    if alias:
        out.append(f"Connected to the environment {environment}: environments/{alias}.json with role development, not in use; "
                   "its address (environmentUrl) is still missing. Card before each import: "
                   + ("always." if confirm_import else "only on a deviation in the tenant."))
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
    if config.get("structureVersion", 0) >= 2 or "storage" in config:
        if need("storage", str) and config["storage"] not in storage.STORAGES:
            rep.error(f"S project.json: storage {config['storage']!r} is not one of {', '.join(storage.STORAGES)}")
    if "trainingFormat" in config and config["trainingFormat"] not in TRAINING_FORMATS:
        rep.error(f"S project.json: trainingFormat {config['trainingFormat']!r} is not one of {', '.join(TRAINING_FORMATS)}")
    # optional, without a new structure version (like trainingFormat): a project without environment is offline
    if "environment" in config and not (isinstance(config["environment"], str) and ALIAS.fullmatch(config["environment"])):
        rep.error(f"S project.json: environment {config['environment']!r} is not an alias of lower-case letters, digits and "
                  "hyphens (the name of its file in environments/)")
    # optional, without a new structure version: the unique name of the Publisher of the solutions (its four values are
    # kept once per computer in ~/.ppp/settings.json); the prefix above is the project's own, not the Publisher's
    if "publisher" in config:
        try:
            check_publisher_name(config["publisher"])
        except ToolError:
            rep.error(f"S project.json: publisher {config['publisher']!r} is not the unique name of a Publisher: a text of "
                      "letters, digits and underscores, not starting with a digit")
    if "confirmImport" in config:
        if not isinstance(config["confirmImport"], bool):
            rep.error("S project.json: confirmImport must be true or false")
        elif "environment" not in config:
            rep.error("S project.json: confirmImport needs environment; a project without environment is offline")
    extra = set(config) - {"structureVersion", "name", "prefix", "mode", "storage", "modules", "solutions",
                           "handbookLanguage", "trainingFormat", "environment", "confirmImport", "publisher"}
    if extra:
        rep.error("S project.json: unknown fields " + ", ".join(sorted(extra)))


def _environments(root: Path, config: dict, rep: Report) -> None:
    """environments/<alias>.json holds the IDs of an environment as the project needs them. Three keys have a fixed
    meaning: environmentUrl, role and inUse. The file of the environment a connected project names must have role
    and inUse; its address may still be missing."""
    alias = config.get("environment") if isinstance(config.get("environment"), str) else None
    folder = root / "environments"
    files = {p.stem: p for p in sorted(folder.glob("*.json"))} if folder.is_dir() else {}
    if alias and alias not in files:
        rep.error(f"S environments/{alias}.json missing: project.json names {alias} as the environment of this project")
    for name, path in files.items():
        where = f"S environments/{path.name}"
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except ValueError as ex:
            rep.error(f"{where} is not valid JSON: {ex}")
            continue
        if not isinstance(data, dict):
            rep.error(f"{where} must be a JSON object")
            continue
        own, before = name == alias, rep.errors
        if ("role" in data or own) and data.get("role") not in ENVIRONMENT_ROLES:
            rep.error(f"{where}: role must be one of {', '.join(ENVIRONMENT_ROLES)}")
        if ("inUse" in data or own) and not isinstance(data.get("inUse"), bool):
            rep.error(f"{where}: inUse must be true or false (true: the solution is in productive use there)")
        url = data.get("environmentUrl")
        if url is not None and not (isinstance(url, str) and ENVIRONMENT_URL.fullmatch(url)):
            rep.error(f"{where}: environmentUrl must be the address of the environment, https://<name>.crm<n>.dynamics.com")
        elif url is None and own:
            rep.warn(f"{where}: environmentUrl missing; nothing reaches the tenant until the address of the environment is known")
        if own and rep.errors == before:
            confirm = config.get("confirmImport", True) or data["inUse"]
            rep.info(f"S connected project: environment {alias}, role {data['role']}" + (", in productive use" if data["inUse"] else "")
                     + f"; card before each import: {'always' if confirm else 'only on a deviation in the tenant'}. Never call pac "
                       "against the tenant yourself: only ppp connect, export, import and tenant reach it.")


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


def _outside(root: Path) -> list[tuple[Path, bool]]:
    """Top-level entries outside the structure, each with True when git does not track it."""
    allowed = set(CORE_FILES) | {d.split("/")[0] for d in CORE_DIRS} | set(OPTIONAL_DIRS)
    repo = gitutil.is_repo(root)
    # a leftover outside git stays on one computer only, e.g. after a transition done on the other one
    return [(p, repo and not gitutil.git(root, "ls-files", "--", p.name).strip())
            for p in sorted(root.iterdir()) if not p.name.startswith(".") and p.name not in allowed]


def _is_link(path: Path) -> bool:
    return path.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(path)


def _empty_tree(path: Path) -> int | None:
    """Number of folders of a tree without files and links, hidden entries included; None otherwise."""
    if _is_link(path):
        return None
    folders = 0
    for top, dirs, files in os.walk(path, followlinks=False):
        if files or any(_is_link(Path(top, d)) for d in dirs):
            return None
        folders += 1
    return folders


def remove_leftovers(root: Path, dry_run: bool = False) -> list[str]:
    """Remove local leftover trees outside git that hold no files; GEN-20261025-WIN-01."""
    removed, kept = [], []
    for p, local in _outside(root):
        if not (local and p.is_dir()):
            continue
        count = _empty_tree(p)
        if count is None:
            kept.append(p.name + "/")
            continue
        removed.append(f"{p.name}/ ({count} folders)")
        if dry_run:
            continue
        for top, _, _ in os.walk(p, topdown=False):
            try:
                os.rmdir(top)
            except PermissionError:
                # OneDrive folders on Windows carry the read-only attribute; clear only that, never the access rights
                os.chmod(top, os.stat(top).st_mode | stat.S_IWRITE)
                os.rmdir(top)
    out = [("Plan, nothing changed yet. " if dry_run else "") + "Local leftovers without files "
           + ("to remove" if dry_run else "removed") + ": " + (", ".join(removed) or "-")]
    if kept:
        out.append("Leftovers with files or links, untouched; move what is still needed to legacy/, inputs/ or exchange/: "
                   + ", ".join(kept))
    return out


def _publisher(root: Path, config: dict, in_settings: str | None, rep: Report) -> None:
    """The Publisher in project.json against the unpacked solutions of the project and against the settings of this
    computer; at most one line for each. Silent when the settings have none (the session start says so)."""
    named = config.get("publisher") if isinstance(config.get("publisher"), str) and config.get("publisher") else None
    found = []  # (solution, unique name of its Publisher), in the order of project.json
    for entry in config.get("solutions") or []:
        name = entry.get("uniqueName") if isinstance(entry, dict) else None
        if isinstance(name, str) and name and (root / "solution" / name / solution.SOLUTION_XML).is_file():
            try:
                publisher = solution.read_publisher(root / "solution" / name)
            except (ToolError, OSError):
                continue
            if publisher:
                found.append((name, publisher["uniqueName"]))
    if "publisher" not in config and found:
        rep.info(f"S solution/{found[0][0]} has the Publisher {found[0][1]}, project.json names none: add "
                 f'"publisher": "{found[0][1]}" to project.json')
    elif named:
        other = [(n, p) for n, p in found if p != named]
        if other:
            rep.warn(f"S solution/{other[0][0]} has the Publisher {other[0][1]}, project.json names {named}"
                     + (f" (and {len(other) - 1} more solutions with another Publisher)" if len(other) > 1 else "")
                     + ": fix the publisher in project.json, or the solution was created under the wrong Publisher")
        if in_settings and in_settings != named:
            rep.info(f"S project.json names the Publisher {named}, the settings of this computer {in_settings}: the project's "
                     "publisher stands for this project (ppp settings --publisher-name changes the settings)")


def check(root: Path, *notes: str | None, settings_publisher: str | None = None) -> Report:
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
    repo = gitutil.is_repo(root)
    copies = gitutil.conflict_copies(root) if repo else []
    for copy, original, missing in copies:
        # a project in OneDrive or iCloud Drive: two computers changed the same file before it synced
        text = f"S {copy}: conflict copy of a sync service (OneDrive, iCloud) beside {original}"
        if missing:
            rep.error(f"{text}, and {original} is missing: restore it with git checkout -- {original}, compare it with "
                      f"the copy, keep the right content in {original}, delete the copy after a card")
        else:
            rep.warn(f"{text}: compare both, keep the right content in {original}, delete the copy after a card")
    for p, local in _outside(root):
        if p.name in {c for c, _, _ in copies}:
            continue
        empty = _empty_tree(p) if local and p.is_dir() else None
        if empty is not None:
            rep.error(f"S not part of the structure: {p.name}/ (not in git: a local leftover without files, {empty} folders; "
                      "remove it with ppp tidy --leftovers after a card)")
        else:
            rep.error(f"S not part of the structure: {p.name}{'/' if p.is_dir() else ''}"
                      + (" (not in git: a local leftover; move what is still needed to legacy/, inputs/ or exchange/, "
                         "then delete it)" if local else ""))
    for name in OPTIONAL_DIRS:
        if (root / name).exists() and not (root / name).is_dir():
            rep.error(f"S {name} must be a folder")
    if config:
        _environments(root, config, rep)

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

    if config:
        _publisher(root, config, settings_publisher, rep)

    # docs/
    docs = root / "docs"
    if docs.is_dir():
        for p in sorted(docs.iterdir()):
            if not p.name.startswith(".") and p.name not in DOCS_DIRS:
                rep.error(f"S docs/{p.name}: docs/ holds only {', '.join(DOCS_DIRS)}")

    handbook = root / "docs" / "handbook" / "walks"
    for p in sorted(handbook.glob("*.json")) if handbook.is_dir() else []:
        try:
            changed = walkfile.stale_screens(root, p)
        except (ToolError, ValueError):
            continue
        if changed:
            rep.warn(f"S handbook walk {p.stem}: {', '.join(changed)} changed since its pictures; run ppp walk "
                     f"{gitutil.rel(root, p)} again and rebuild the Word files with ppp guide")

    # STATE.md, CLAUDE.md
    state = root / "STATE.md"
    if state.is_file():
        text = state.read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+?)\s*$", text, re.M)
        for s in STATE_SECTIONS:
            if s not in headings:
                rep.error(f"S STATE.md: section '## {s}' missing (keep the headings of the template)")
        if len(text) > STATE_BUDGET:
            extra = [h for h in headings if h not in STATE_SECTIONS]
            rep.warn(f"S STATE.md: {len(text):,} characters, more than {STATE_BUDGET:,}: keep only the current state, "
                     "move evidence and history to the package's tasks.md, to decisions/ or leave them to git"
                     + (f"; sections beyond the template: {', '.join(extra[:4])}" if extra else ""))
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
        data = [t for t in tracked if t.endswith((".pbi/cache.abf", ".pbi/localSettings.json"))]
        if data:
            rep.error(f"S Power BI data files in git ({len(data)}), e.g. {data[0]}; remove them with git rm --cached")
        probe = "components/power-bi/x.SemanticModel/.pbi/"
        if "power-bi" in modules and not all(gitutil.git(root, "check-ignore", "--no-index", probe + n, check=False).strip()
                                             for n in ("cache.abf", "localSettings.json")):
            rep.error("S .gitignore needs the lines **/.pbi/cache.abf and **/.pbi/localSettings.json "
                      "(Power BI Desktop keeps the imported data and local settings there)")
        if config:
            storage.check(root, config, rep)
    else:
        rep.error("S not a git repository (P7)")

    for note in notes:
        if note:
            rep.warn(note)
    if not rep.errors:
        rep.ok("S structure as in PROJEKTSTRUKTUR, version " + str(STRUCTURE_VERSION))
    return rep


# ------------------------------------------------------------------ migrate
def _storage_from_remote(root: Path, config: dict) -> list[str]:
    """1 -> 2: storage from the remote origin (ABLAGE AB-9); a value written by hand stays."""
    if config.get("storage") in storage.STORAGES:
        return [f"storage {config['storage']} kept"]
    url = storage.remote_url(root)
    kind = storage.kind_of(url) if url else "local"
    if kind is None:
        raise ToolError(f"The remote origin {url} is neither on GitHub nor on Bitbucket: write \"storage\" into "
                        "project.json by hand (github, bitbucket or local), then run ppp migrate again.")
    items = list(config.items())
    config.clear()
    for key, value in items:
        config[key] = value
        if key == "mode":
            config["storage"] = kind
    config.setdefault("storage", kind)
    return [f"storage {kind}: " + (f"from the remote origin {url}" if url else
                                   "no remote, so a local folder; if it belongs on GitHub: ppp storage github --remote <url>")]


MIGRATIONS: dict = {1: _storage_from_remote}  # from version n to n + 1: function(root, config) -> list of lines


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
        roadmap = root / "ROADMAP.md"
        if roadmap.is_file():  # numbers planned in the roadmap are taken too (GEN-20261102-WIN-01)
            names += [f"{n}-" for n in re.findall(r"^\|\s*(\d{3})\s*\|", roadmap.read_text(encoding="utf-8"), re.M)]
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
        names = [p.name for p in folder.glob(f"{code}-*.md")]
        if gitutil.is_repo(root):  # a learning session removes answered proposals; their IDs stay taken, and so do the
            # IDs it archived them as, which only its commit message names (PAPPS-20261103-WIN-05 twice)
            history = gitutil.git(root, "log", "--all", "--format=%B", "--name-only", "--", "lessons/",
                                  check=False).decode("utf-8", "replace")
            names += [f"{found}.md" for found in re.findall(rf"\b{re.escape(code)}-\d+\b", history)]
        n = 1 + max((int(Path(name).stem.rsplit("-", 1)[1]) for name in names
                     if Path(name).name.startswith(f"{code}-") and name.endswith(".md")), default=0)
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
