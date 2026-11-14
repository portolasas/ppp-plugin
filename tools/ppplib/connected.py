"""The connected mode (entwurf/VERBUNDEN.md): ppp connect, export, import and tenant. A project is connected when
project.json names an environment. Then ppp fetches the export and imports the package itself, each import only after
its checks, and reads the result from the server instead of asking the user for it.

exchange/tenant/ (not in git, left alone by ppp tidy) holds what no commit can rebuild: per solution the backup
before_<version>.zip taken before an import, imports.jsonl with every import and how it ended (and, after an import,
the mark of the ppp export that took the tenant's state over), and times.jsonl with the duration of every export that
came to an end (an import's duration stands in imports.jsonl).
"""
from __future__ import annotations

import json
import re
import tempfile
import time
import zipfile
from datetime import date, datetime
from pathlib import Path

from . import cards, compare, gitutil, importlog, solution, structure, tenant
from .project import ToolError, load_config, package_solution, solution_with_role
from .tenant import TenantError
from .verify import SOLUTION_XML, files_of, stable

DEFAULT_ENVIRONMENT = "Citizen Developments"  # the plugin knows its name only; the address comes from the tenant (VB-2)
BY_HAND = "Still by hand: open each changed flow in the designer and save it; then the critical scenarios."
FIRST_IMPORT = "first import by ppp from this project into this environment"

# What an environment is for. pac does not say it: EnvironmentIdentifier.Type is the same number for every environment
# (pac test, re-run of round 1, 2026-11-13, J), so the role is given once on the first ppp connect.
ROLES_EXPLAINED = ("development (the work is built and imported here), test (a package moves here for the user test; "
                   "ppp imports after a card) or production (ppp only reads; an import goes the governance way)")


def new_version_step(root: Path, name: str, alias: str, *versions: str, target: str = "<target>") -> str:
    """What the next move into a target needs once a version is not usable: in mode large ppp packs and imports only the
    transfer solution, so the version of the main solution never rises in the project's environment by itself;
    ppp import --environment <target> --raise-version raises it there after a card, above the highest of `versions`
    (user, 13.11., after pac test round 3, O1). In the other modes a new version is wanted."""
    if load_config(root).get("mode") != "large":
        return f"the next move needs a new version in {alias}"
    return (f"in mode large the version of {name} does not rise by itself: ppp import --environment {target} --raise-version "
            f"raises it in {alias} to {importlog.next_version(max(versions, key=importlog.version_key))} after a card, then ppp export --solution {name}, "
            f"then the move again")


REPLACED = "The original workflow definition has been deactivated and replaced."


def record_line(log: dict, texts: int = 5) -> str:
    """The numbers of an import record and its texts. The server writes REPLACED for each flow an import replaces; that is
    normal when a flow was edited and imported again (user, 13.11.), so it is named as usual and not listed."""
    usual = [t for t in log["texts"] if t.strip().rstrip(".").lower() == REPLACED.rstrip(".").lower()]
    rest = [t for t in log["texts"] if t not in usual]
    return (f"{log['success']} success, {log['warning']} warnings, {log['failure']} failures"
            + (f"; \"{REPLACED}\" is the usual line per replaced flow: nothing to do" if usual else "")
            + "".join(f"\n  {t}" for t in rest[:texts]))


def _resume_command(root: Path, entry: dict) -> str:
    """The command that continues the import of an entry still under way: a move needs its target, a creation its own
    command (with --solution unless the solution is the main one), a restore --restore; else the plain ppp import."""
    if entry.get("kind") == "move":
        return f"ppp import --environment {entry['environment']}"
    if entry.get("kind") == "create":
        main = solution_with_role(load_config(root), "main")
        named = str(entry.get("solution", ""))
        return "ppp import --create" + ("" if main and named.lower() == main.lower() else f" --solution {named}")
    return "ppp import --restore" if entry.get("restore") else "ppp import"


def project_version(folder: Path) -> str | None:
    path = folder / SOLUTION_XML
    return gitutil.version_of(path.read_bytes()) if path.is_file() else None


def backup_folder(root: Path, env: dict, name: str) -> Path:
    """The folder of the backups of a solution in an environment: exchange/tenant/<name>/ for the project's environment,
    exchange/tenant/<alias>/<name>/ for any other, a move target (ERWEITERUNGEN C.4): report_imported removes the older backups of
    its folder, which must never be those of another environment with the same version."""
    if env["alias"] == load_config(root).get("environment"):
        return root / "exchange" / "tenant" / name
    return root / "exchange" / "tenant" / env["alias"] / name


def _card(env: dict) -> str:
    if env.get("role") == "test":       # the role promises it (ROLES_EXPLAINED), whatever confirmImport says
        return "always (role test)"
    return "always" if env["confirmImport"] or env["inUse"] else f"only on a deviation in the tenant and on the {FIRST_IMPORT}"


# ------------------------------------------------------------------ the start of an import
def hand_over(root: Path, env: dict, entry: dict, package: Path, wait: float, **settings) -> dict:
    """tenant.start_import for an entry just recorded as started. Whatever fails before pac has handed the package to
    the server (a refused settings file or call, pac not found, pac not started, no hand-over within its time) ends the
    entry as not_started with its reason and is raised again: nothing is used up, and the same command later runs
    through every check anew instead of waiting for an import that never began."""
    try:
        return tenant.start_import(env["url"], package, wait, **settings)
    except Exception as ex:
        why = "not started: " + str(ex).splitlines()[0] if str(ex) else f"not started: {type(ex).__name__}"
        importlog.record(root, {**entry, "status": "not_started", "reason": why[:400]})
        raise


def need_role(env: dict) -> None:
    if env["role"] not in structure.ENVIRONMENT_ROLES:
        raise ToolError(f"environments/{env['alias']}.json names no role yet; pac does not name it. Set it with ppp connect "
                        f"--role: {ROLES_EXPLAINED}.")


# ------------------------------------------------------------------ ppp connect
def connect(root: Path, name: str | None = None, role: str | None = None, in_use: bool | None = None,
            confirm: bool | None = None, off: bool = False) -> list[str]:
    """Connect the project to an environment by its display name, or refresh the connection it has: find the
    environment in the tenant, write its address, role and use into environments/<alias>.json and the alias into
    project.json, and say which solutions of the project are online (VERBUNDEN VB-2, VB-3, VB-11). The role comes from
    --role or from the file; without either nothing is written. Names the usual durations there. The default
    environment is the default; working in a development environment of one's own is the user's free choice."""
    path = root / "project.json"
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    alias = config.get("environment")
    if off:
        if not alias:
            return ["The project is offline already."]
        importlog.write_json(path, {k: v for k, v in config.items() if k not in ("environment", "confirmImport")})
        return [f"Offline again: the user exports and imports by hand, guided by cards. environments/{alias}.json stays as it is. "
                "Commit project.json."]
    known_file = root / "environments" / f"{alias}.json" if alias else None
    known = json.loads(known_file.read_text(encoding="utf-8-sig")) if known_file and known_file.is_file() else {}
    found = tenant.find_environment(name or known.get("name") or DEFAULT_ENVIRONMENT)
    if name or not alias:
        alias = structure.slug(found["name"])
    file = root / "environments" / f"{alias}.json"
    old = json.loads(file.read_text(encoding="utf-8-sig")) if file.is_file() else {}
    # pac does not name what an environment is for: the role is given, else it stands in the file (VB-11)
    role = role or (old.get("role") if old.get("role") in structure.ENVIRONMENT_ROLES else None)
    if not role:
        raise ToolError(f"ppp connect needs the role of {found['name']} once; pac does not name it. Give it with --role: "
                        f"{ROLES_EXPLAINED}. Example: ppp connect \"{found['name']}\" --role development.")
    if role not in structure.ENVIRONMENT_ROLES:
        raise ToolError(f"role must be one of {', '.join(structure.ENVIRONMENT_ROLES)}")
    data = {"name": found["name"], "environmentUrl": found["url"], "role": role,
            "inUse": bool(old.get("inUse", False)) if in_use is None else in_use,
            **{k: v for k, v in old.items() if k not in ("name", "environmentUrl", "role", "inUse")}}
    importlog.write_json(file, data)
    confirm = config.get("confirmImport", True) if confirm is None else confirm
    new = {}
    for key, value in config.items():
        if key not in ("environment", "confirmImport"):
            new[key] = value
        if key == "storage":
            new.update(environment=alias, confirmImport=confirm)
    new.setdefault("environment", alias)
    new.setdefault("confirmImport", confirm)
    importlog.write_json(path, new)
    env = {"confirmImport": confirm, "inUse": data["inUse"], "role": role}
    lines = [f"Connected to {found['name']}: environments/{alias}.json with its address, role {role}, "
             + ("in productive use" if data["inUse"] else "not in productive use") + f"; card before each import: {_card(env)}.",
             importlog.usual_line(root, alias)]
    online = tenant.solutions(found["url"])
    for s in config.get("solutions") or []:
        there = online.get(str(s.get("uniqueName", "")).lower())
        lines.append(f"  {s.get('uniqueName')} ({s.get('role')}): " + (f"online {there['version']}" + (", managed" if there["managed"] else "")
                                                                    if there else "not in this environment yet"))
    if role == "production":
        lines.append("Role production: ppp reads there; ppp import does not import, production goes the governance way.")
    lines.append(f"Commit project.json and environments/{alias}.json.")
    return lines


# ------------------------------------------------------------------ ppp export
def _unimported(root: Path, folder: Path, name: str, online_version: str, alias: str) -> str | None:
    """Work in the solution folder that the tenant does not have yet; an export would replace it (VERBUNDEN VB-14)."""
    where = gitutil.rel(root, folder)
    if gitutil.git(root, "status", "--porcelain", "--", where).strip():
        return "uncommitted changes"
    mine = project_version(folder)
    # "imported" only silences the message below; work committed after the import is still work (VB-14)
    if not importlog.imported(root, name, mine, alias) and importlog.version_key(mine or "") > importlog.version_key(online_version):
        return f"version {mine} is packed but not imported (online: {online_version})"
    try:
        base = gitutil.tenant_commit(root, folder)
    except ToolError:
        return None
    changed = gitutil.git(root, "diff", "--name-only", base, "HEAD", "--", where).decode().split()
    return f"{len(changed)} files changed since the last export" if changed else None


def export(root: Path, take, name: str | None = None, compare: bool = False, no_commit: bool = False, force: bool = False,
           wait: float = 540, environment: str | None = None) -> int:
    """Fetch the solution from the tenant and take it into solution/<UniqueName>/ like ppp unpack: the diff against the
    last commit shows what was changed by hand in the tenant (VERBUNDEN VB-8). `take` is the one way an export enters
    the project (cli._take_export). environment: the alias of another environment, a move target; from there only a
    comparison, the project's base comes from its own environment (ERWEITERUNGEN C.1)."""
    env = tenant.environment(root, environment)
    if not env["own"] and not compare:
        raise ToolError(f"the project's base comes from {load_config(root).get('environment')}; ppp export --compare --environment "
                        f"{env['alias']} shows the difference.")
    name = name or package_solution(load_config(root))
    if not name:
        raise ToolError("project.json names no solution yet: ppp export --solution <UniqueName>.")
    online = tenant.solutions(env["url"]).get(name.lower())
    if not online:
        raise ToolError(f"The solution {name} is not in the environment {env['alias']}.")
    if online["managed"]:
        raise ToolError(f"{online['name']} is managed in {env['alias']}; ppp works on unmanaged solutions.")
    folder = root / "solution" / online["name"]
    arguments = ["solution", "export", "--name", online["name"], "--path", "", "--overwrite", "--async"]
    if compare:
        return _compare(root, env, online, folder, arguments, wait)
    if folder.is_dir() and gitutil.is_repo(root):
        work = _unimported(root, folder, online["name"], online["version"], env["alias"])
        if work == "uncommitted changes":     # never replaced, --force or not: it is in no commit (VB-14)
            raise ToolError(f"Uncommitted changes in {gitutil.rel(root, folder)}: commit them (after ppp pack the raised version is "
                            "one), then run ppp export again. --force does not replace uncommitted work.")
        if work and not force:
            raise ToolError(f"{gitutil.rel(root, folder)} holds work the tenant does not have ({work}); ppp export would replace it "
                            "with the tenant's state. See the tenant's state without changing anything: ppp export --compare. "
                            "Replace the work anyway: --force.")
    target = root / "exchange" / f"{online['name']}_{online['version'].replace('.', '_')}.zip"
    target.parent.mkdir(exist_ok=True)
    arguments[5] = str(target)
    importlog.timed_export(root, env, arguments, wait)
    print(f"Exported {online['name']} {online['version']} from {env['alias']} to exchange/{target.name}")
    code = take(root, target, force=force, no_commit=no_commit)
    # the mark ends the wait of ppp pack after an import, also when nothing was committed for the same content;
    # with --no-commit the tenant's state is not committed yet: ppp export again does it
    if code == 0 and not no_commit:
        importlog.mark_exported(root, online["name"], online["version"], "export")
    return code


def _compare(root: Path, env: dict, online: dict, folder: Path, arguments: list[str], wait: float) -> int:
    with tempfile.TemporaryDirectory(prefix="ppp-compare-") as tmp:
        arguments[5] = str(Path(tmp) / "tenant.zip")
        importlog.timed_export(root, env, arguments, wait)
        theirs = compare.unpacked(Path(arguments[5]), online["name"])
    ours = {f: (folder / f).read_bytes() for f in files_of(folder)} if folder.is_dir() else {}
    different = compare.difference(theirs, ours)
    print(f"Tenant {env['alias']}: {online['name']} {online['version']}; project: {project_version(folder) or 'not exported yet'}")
    print(f"Different ({len(different)}): " + (", ".join(different[:40]) or "-") + (f" … {len(different) - 40} more" if len(different) > 40 else ""))
    for line in compare.details(theirs, ours, different):
        print(line)
    print("Nothing was changed in the project.")
    return 0


# ------------------------------------------------------------------ ppp import
def _newest_package(root: Path, name: str) -> Path:
    found = []
    for path in sorted((root / "exchange").glob("*_IMPORTABLE.zip")):
        try:
            info = solution.zip_manifest(path)
        except (ToolError, zipfile.BadZipFile, OSError):
            continue
        if info["uniqueName"].lower() == name.lower():
            found.append((importlog.version_key(info["version"]), path))
    if not found:
        raise ToolError(f"No package of {name} in exchange/; ppp pack builds one.")
    return max(found)[1]


APP_FILE = re.compile(r"_(?:DocumentUri\.msapp|BackgroundImageUri|AdditionalUris\d*.*)$")   # files of an app beside its .meta.xml


def _apps(names: list[str]) -> list[str]:
    """The apps under CanvasApps/, one name each: as verify.canvas_apps, the stem of its <app>.meta.xml; a file of no
    such app by its name without the part that names the kind of file."""
    files = {n.split("/")[1] for n in names if n.startswith("CanvasApps/") and n.split("/")[1]}
    stems = {f[:-len(".meta.xml")] for f in files if f.endswith(".meta.xml")}
    rest = {APP_FILE.sub("", f) for f in files if not f.endswith(".meta.xml") and not any(f.startswith(s + "_") for s in stems)}
    return sorted(stems | rest)


def package_parts(package: Path) -> dict:
    """What a package holds: flows by ID with their names, connection references, apps (one name per app)."""
    with zipfile.ZipFile(package) as z:
        names = z.namelist()
        custom = next((z.read(n).decode("utf-8-sig", "replace") for n in names if n.lower() == "customizations.xml"), "")
    flows = {m.group(2).lower(): m.group(1) for n in names
             for m in [re.fullmatch(r"Workflows/(.+)-(" + tenant.GUID.pattern + r")\.json", n)] if m}
    return {"flows": flows, "refs": sorted(set(re.findall(r'connectionreferencelogicalname="([^"]+)"', custom))),
            "apps": _apps(names)}


def _older_than_export(root: Path, folder: Path, report: str) -> str | None:
    """Why a package is older than the last export of its solution in the project, or None (VERBUNDEN VB-8). ppp pack
    writes the commit it packed on into the report; the last commit "Export <name> ..." of the folder must be in its
    history. A package packed before that export would overwrite what it took over from the tenant, unseen by the
    drift check, whose base that export is now. Git history, not file times: the project may lie in a sync folder."""
    log = gitutil.git(root, "log", "--format=%H%x09%s", "--", gitutil.rel(root, folder), check=False).decode("utf-8", "replace")
    export = next((c for c, _, s in (line.partition("\t") for line in log.splitlines()) if s.startswith(f"Export {folder.name} ")), None)
    if export is None:
        return None
    packed = re.search(r"^Packed on: ([0-9a-f]{40})\s*$", report, re.M)
    if not packed:
        return f"has a report that names no commit it was packed on (packed before ppp wrote one), so it may be older than the " \
               f"last export ({gitutil.describe(root, export)})"
    if gitutil.git(root, "merge-base", export, packed.group(1), check=False).decode().strip() != export:
        return f"was packed before the last export ({gitutil.describe(root, export)}) and would overwrite what that export took " \
               "over from the tenant"
    return None


def _age(entry: dict) -> float:
    return (datetime.now() - datetime.fromisoformat(entry["time"])).total_seconds()


NEVER_SHOWN = 30 * 60   # seconds after the start without any job of the import: only then the server never took it (VB-10)


def _own_log(env: dict, entry: dict) -> dict | None:
    """The record of this import's job: a finished job of the solution not among those read at the start (jobs_before),
    so a job of an earlier import is never taken for it, whatever zone the server's times are in (VB-10). None while it
    runs or has not shown yet, and for an entry from before ppp held the jobs at the start."""
    before = entry.get("jobs_before")
    if not isinstance(before, list):
        return None
    # never further back than the read at the start: a job created before its 12 hours is in no list
    hours = 12 + max(int(_age(entry) // 3600) - 1, 0)
    return tenant.import_log(env["url"], entry["solution"], hours, exclude=before)


def import_package(root: Path, package: str | None = None, confirmed: bool = False, accept_drift: bool = False,
                   with_apps: bool = False, wait: float = 100) -> int:
    """Import a package built by ppp pack into the project's environment, after the checks of VERBUNDEN VB-6. Returns
    within about `wait` seconds: a long import goes on at the server, and the same command again waits further and
    never starts a second import (VB-10)."""
    called = datetime.now().isoformat(timespec="seconds")      # the whole call counts, checks and backup included
    env = tenant.environment(root)
    need_role(env)
    if env["role"] == "production":
        raise ToolError(f"{env['alias']} has the role production: ppp import does not import there. Production goes the "
                        "governance way (ANFORDERUNGEN T8).")
    name = package_solution(load_config(root))
    if not name:
        raise ToolError("project.json names no solution to pack.")
    path = (Path(package) if Path(package).is_absolute() else root / package) if package else _newest_package(root, name)
    if not path.is_file():
        raise ToolError(f"Package not found: {path}")
    info, digest, parts = solution.zip_manifest(path), solution.sha256(path), package_parts(path)
    if info["uniqueName"].lower() != name.lower():
        raise ToolError(f"{path.name} is a package of {info['uniqueName']}; this project packs {name} (the transfer solution, "
                        "else the main solution).")
    if info["managed"]:
        raise ToolError(f"{path.name} is managed; ppp imports unmanaged packages only.")
    report = path.with_name(re.sub(r"_IMPORTABLE\.zip$", "_REPORT.md", path.name, flags=re.I))
    if report == path or not report.is_file() or digest not in report.read_text(encoding="utf-8", errors="replace"):
        raise ToolError(f"{path.name} is not the file its report names (SHA-256): only a package built by ppp pack is imported.")
    if parts["apps"] and not with_apps:
        raise ToolError("The package contains apps: " + ", ".join(parts["apps"]) + ". A package excludes apps (A-7); only a move "
                        "to test packs them: --with-apps.")
    last = next((e for e in reversed(importlog.entries(root)) if e.get("sha") == digest and e.get("environment") == env["alias"]), None)
    if last and last["status"] == "failed":
        raise ToolError(f"{path.name} failed on import ({last.get('reason', 'see ppp tenant --log')}) and is used up: never import "
                        f"the same ZIP again. Fix the cause and pack a new version: ppp pack --version {importlog.next_version(info['version'])}.")
    if last and last["status"] == "done":
        raise ToolError(f"{path.name} is imported already ({last['time']}). Next: ppp export.")
    if last and last["status"] == "started":
        return follow_import(root, env, last, parts, wait, resumed=True)
    # a failed create (ppp import --create) uses nothing up: nothing went online (ERWEITERUNGEN A)
    spent = next((e for e in importlog.entries(root) if e.get("status") == "failed" and not e.get("restore") and e.get("kind") != "create"
                  and e.get("version") == info["version"] and e.get("environment") == env["alias"]
                  and str(e.get("solution", "")).lower() == name.lower()), None)
    if spent:     # a repacked package with the version of a failed one (VB-14)
        raise ToolError(f"Version {info['version']} of {name} failed on import into {env['alias']} ({spent['zip']}) and is used up, "
                        f"also for a package packed again: ppp pack --version {importlog.next_version(info['version'])}.")
    # a package packed before the export after the last import was built on the package, not on the tenant's state
    importlog.need_export(root, name, "ppp pack and ppp import")
    folder = root / "solution" / info["uniqueName"]
    if gitutil.is_repo(root):
        where = gitutil.rel(root, folder)
        if folder.is_dir() and gitutil.git(root, "status", "--porcelain", "--", where).strip():
            # the check of the next import finds its base by the committed version (gitutil.tenant_commit)
            raise ToolError(f"Uncommitted changes in {where}: commit first (after ppp pack the raised version is one), then "
                            "ppp import again.")
        stale = _older_than_export(root, folder, report.read_text(encoding="utf-8", errors="replace"))
        if stale:
            raise ToolError(f"{path.name} {stale}. Pack again on the state now: ppp pack --version "
                            f"{importlog.next_version(project_version(folder) or info['version'])}.")

    online = tenant.solutions(env["url"]).get(name.lower())
    if online and online["managed"]:
        raise ToolError(f"{name} is managed in {env['alias']}; an unmanaged package does not go on top of it.")
    if online and importlog.version_key(info["version"]) <= importlog.version_key(online["version"]):
        raise ToolError(f"Version {info['version']} is not higher than the version online ({online['version']}): pack again with "
                        f"ppp pack --version {importlog.next_version(online['version'])}.")
    running = tenant.running_imports(env["url"], name)
    if running:
        raise TenantError("BUSY", f"an import of {name} is running in {env['alias']} (progress {running[0]} %). Wait for it; "
                                  "ppp tenant shows where it stands.")
    drift, details = [], []
    if online:      # the backup before the import is the export of the drift check (VB-12)
        backup = backup_folder(root, env, online["name"]) / f"before_{info['version']}.zip"
        backup.parent.mkdir(parents=True, exist_ok=True)
        importlog.timed_export(root, env, ["solution", "export", "--name", online["name"], "--path", str(backup), "--overwrite", "--async"], 540)
        drift, details = compare.drift(root, root / "solution" / online["name"], backup, online["version"])
    if drift and not accept_drift:
        print(f"DRIFT: the tenant differs from the state this package was built on ({len(drift)}): " + ", ".join(drift[:30])
              + (f" … {len(drift) - 30} more" if len(drift) > 30 else ""))
        for line in details:
            print(line)
        print("Nothing was imported. The import would overwrite these changes. Show them (ppp export --compare) and ask on a "
              "card: commit the work first, then ppp export --force, then rebuild the work on the tenant's state (it stays in git), "
              "then pack again; or import anyway (--accept-drift). ppp export never replaces uncommitted work.")
        return 1
    first = importlog.never_imported(root, name, env["alias"])
    reasons = [text for needed, text in ((env["confirmImport"], "this project asks before each import"),
                                         (env["inUse"], "the solution is in productive use there"),
                                         (env["role"] == "test", "the environment has the role test"),
                                         (first, FIRST_IMPORT),
                                         (not online and not first, "the solution is not in this environment"),
                                         (bool(drift), "the tenant differs and the import overwrites it")) if needed]
    if reasons:     # the code binds the answer to this card and to the lines of the drift it overwrites (cards)
        card = (f"CONFIRM FIRST ({'; '.join(reasons)}): show a tenant-step card with the package {path.name} ({name} {info['version']}, "
                f"SHA-256 {digest[:12]}…), the environment {env['name']} (role {env['role']}), what the import replaces "
                f"({len(parts['flows'])} flows, {len(parts['refs'])} connection references"
                + (f", apps: {', '.join(parts['apps'])}" if parts["apps"] else "") + f"; online now: "
                f"{online['version'] if online else 'nothing yet'})"
                + (f", the drift it overwrites: {', '.join(drift[:30])}" if drift else "")
                + " and the answers \"Import\" and \"Not now\". After \"Import\": the same command with --confirmed.")
        if not cards.confirm(card, confirmed, details):
            return 1
    entry = importlog.record(root, {"solution": name, "version": info["version"], "zip": path.name, "sha": digest,
                           "environment": env["alias"], "status": "started", "called": called,
                           "online_before": online["version"] if online else None,
                           "flows_before": tenant.flows(env["url"], list(parts["flows"])) if online else {},
                           "jobs_before": tenant.import_jobs(env["url"], name)})
    result = hand_over(root, env, entry, path, wait)
    if result["state"] in ("failed", "skipped"):
        return report_failed(root, env, entry, f"{result.get('kind', 'SKIPPED')}: {result['message']}", result=result)
    return follow_import(root, env, entry, parts, max(wait - result["seconds"], 0), resumed=False)


def follow_import(root: Path, env: dict, entry: dict, parts: dict, wait: float, resumed: bool) -> int:
    """Read from the server where the import stands: the version online is the proof that it arrived, the ended job of
    this import the proof that it did not (VB-10). Without that job the import stays RUNNING: a queue, a long upload or
    an aborted call can hold it back. FAILED without a job only when the server showed none NEVER_SHOWN after the start.
    IMPORTED only once the job has ended too: the version shows while the job still runs, its record and the switches of
    the flows are not final then (pac test 2026-11-13, V3). Ended means this import's job is readable as ended, or no job
    of the solution runs any more; the latter also for an entry without jobs_before, and when the ended job is not
    readable yet (then "not readable yet", so nothing waits for ever on a record)."""
    name, version, began = entry["solution"], entry["version"], time.monotonic()
    arrived = lambda: (tenant.solutions(env["url"]).get(name.lower()) or {}).get("version") == version
    while True:
        online = arrived()
        running = tenant.running_imports(env["url"], name)
        if online:
            log = _own_log(env, entry) if running else None     # a job left without an end must not hold it for ever
            if not running or log:
                return report_imported(root, env, entry, parts, log)
        elif not running:
            log = _own_log(env, entry)
            if log and arrived():       # the job may end a moment before the version shows
                return report_imported(root, env, entry, parts, log)
            if log:
                return report_failed(root, env, entry, "; ".join(t for t in log.get("texts") or [] if t.strip() != REPLACED)
                               or "the import ended and the version online did not change", log)
            if _age(entry) > NEVER_SHOWN:
                return report_failed(root, env, entry, f"the server never showed this import: no job of it within {NEVER_SHOWN // 60} "
                               "minutes of the start, and the version online did not change"
                               + ("" if isinstance(entry.get("jobs_before"), list) else
                                  " (an entry from before ppp held the jobs at the start: ppp tenant --log shows the newest job)"),
                               never_shown=True)
        if time.monotonic() - began >= wait:
            usual_import = importlog.usual(root, env["alias"], whole=False)["import"]    # how long to wait from the start named here
            print(f"RUNNING: the import of {entry['zip']} into {env['alias']} is not finished"
                  + (f" (progress {running[0]} %" + (f"; {version} is online already, the job has not ended" if online else "")
                     + ")" if running else " (the server does not show it yet)")
                  + f", started {entry['time'][11:16]}."
                  + (f" Usual here: {importlog.about(usual_import)} from the start of an import to IMPORTED." if usual_import is not None else ""))
            print(f"Run {_resume_command(root, entry)} again to wait further; it starts no second import.")
            return 0
        time.sleep(10)


def report_imported(root: Path, env: dict, entry: dict, parts: dict, log: dict | None = None) -> int:
    """After the import ppp confirms by itself what the user used to report (VERBUNDEN VB-16). log: the record of this
    import's job when follow_import has read it already. The lines after the record follow the kind of the entry
    (ERWEITERUNGEN A.1, C.1): create (an empty first solution: no flows and bindings, the line CREATED, the hook
    publisher.after_import), move (into a move target: the hook move.after_import, no export after it), else a package or
    a restore. The hooks return lines; each that starts with WARNING counts among ppp's warnings."""
    name, seconds, kind = entry["solution"], round(_age(entry)), entry.get("kind")
    print(f"IMPORTED: {entry['zip']} is in {env['alias']}, {name} {entry['version']} is online (about {seconds} s).")
    warnings = 0       # ppp's own WARNING lines below; the server's warnings stand in the record
    log = log or _own_log(env, entry)      # only the job of this import, never the numbers of an earlier one
    record = {k: log[k] for k in ("success", "warning", "failure")} if log else None
    if log:
        print(f"Import record: {record_line(log)}")
        if log["failure"] > 0:
            warnings += 1
            print(f"WARNING the import record names {log['failure']} failures")
    else:
        print("Import record: not readable yet (ppp tenant --log)")
    if kind != "create":        # an empty first solution has no flows and no references
        after = tenant.flows(env["url"], list(parts["flows"]))
        before = entry.get("flows_before") or {}
        switched = sorted(parts["flows"][i] for i, state in after.items() if before.get(i) not in (None, state))
        off = sorted(parts["flows"][i] for i, state in after.items() if state != "on")
        print(f"Flows: {sum(1 for s in after.values() if s == 'on')} on, {len(off)} not on" + (": " + ", ".join(off) if off else ""))
        if switched:
            warnings += 1
            print("WARNING the import changed the switch of: " + ", ".join(switched))
        unbound = sorted(n for n, r in tenant.connection_references(env["url"], parts["refs"]).items() if not r["connection"])
        if unbound:
            warnings += 1
            print("WARNING connection references without a connection: " + ", ".join(unbound))
    if kind == "create":
        print(f"CREATED solution {name} {entry['version']} in {env['alias']}, publisher {entry.get('publisher', '?')} "
              f"({'new' if entry.get('publisher_new') else 'existing'}), its values as in the settings.")
    for line in _after_import(root, env, entry, parts, kind):
        warnings += line.startswith("WARNING")
        print(line)
    timing = {"seconds": seconds}
    if entry.get("called"):     # the whole call up to here, from the first ppp import of it (an entry from before: none)
        timing["seconds_call"] = round((datetime.now() - datetime.fromisoformat(entry["called"])).total_seconds())
    importlog.record(root, {**entry, "status": "done", **timing, "ppp_warnings": warnings, "record": record})
    folder = backup_folder(root, env, name)
    for old in sorted(folder.glob("before_*.zip")) if folder.is_dir() else []:     # the backup of this import stays until the next one
        if old.name != f"before_{entry['version']}.zip":
            old.unlink()
    if warnings:
        print(f"{warnings} warnings above: show them to the user before going on.")
    if kind == "create":
        print(f"Next: ppp export --solution {name}; it commits the first base.")
        return 0
    print(BY_HAND)
    if kind == "move":
        if parts.get("apps"):
            print(f"Share and publish the app in {env['alias']} by hand.")
        print(f"Next: the user test in {env['alias']}; ppp tenant --environment {env['alias']} shows its state. No ppp export "
              f"from there: the project's base stays {entry.get('source', '?')}.")
    elif entry.get("restore"):
        (folder / entry["zip"]).unlink(missing_ok=True)
        print(f"This was a restore of {entry['restore']}. Next: ppp export; it takes the restored state into the project and "
              "shows the changes of the later packages as reverted. They stay in git.")
    else:
        print("Next: ppp export; it commits the tenant's state as the base of the next package.")
    return 0


def _after_import(root: Path, env: dict, entry: dict, parts: dict, kind: str | None) -> list[str]:
    """The lines of the hook of an entry's kind after IMPORTED: publisher.after_import for create, move.after_import for
    move (ERWEITERUNGEN A.1, C.1), none for a package or a restore. Imported here: both modules build on this one."""
    if kind == "create":
        from . import publisher
        return publisher.after_import(root, env, entry)
    if kind == "move":
        from . import move
        return move.after_import(root, env, entry, parts)
    return []


def report_failed(root: Path, env: dict, entry: dict, reason: str, log: dict | None = None, result: dict | None = None,
            never_shown: bool = False) -> int:
    """A failed import uses the ZIP up; the work in the project stays (VERBUNDEN VB-14). When pac did not reach the server
    (AUTH, DENIED, SYNTAX, BUSY), when pac failed before it handed the package over, or when the server never showed a
    job of it (never_shown), nothing is used up: the entry ends as not_started and an error with the next step is raised.
    The same when pac skipped the import because the version online is not lower (--skip-lower-version): nothing was
    handed over, and the refusal names a higher version, as the check before the import does."""
    if result and result.get("state") == "skipped":
        importlog.record(root, {**entry, "status": "not_started", "reason": reason[:400]})
        found = re.search(r"'(\d+(?:\.\d+)+)'", result["message"])
        online = found.group(1) if found else entry["version"]
        if entry.get("restore"):
            raise ToolError(f"pac skipped the import of {entry['zip']}: the version online is not lower than {entry['version']} "
                            f"({result['message']}). Nothing was imported; another import came first. ppp import --restore again "
                            "builds a version above the one online.")
        if entry.get("kind") == "move":
            step = new_version_step(root, entry["solution"], entry.get("source", "?"), entry["version"], online, target=env["alias"])
            raise ToolError(f"pac skipped the import of {entry['zip']}: the version in {env['alias']} is not lower than "
                            f"{entry['version']} ({result['message']}). Nothing was imported and nothing is used up; another import "
                            f"came first. {step[0].upper()}{step[1:]}.")
        raise ToolError(f"pac skipped the import of {entry['zip']}: the version online is not lower than {entry['version']} "
                        f"({result['message']}). Nothing was imported and nothing is used up; another import came first. Pack again "
                        f"with a higher version: ppp pack --version {importlog.next_version(online)}.")
    if result and result.get("kind") in ("AUTH", "DENIED", "SYNTAX", "BUSY"):
        importlog.record(root, {**entry, "status": "not_started", "reason": reason[:400]})
        raise TenantError(result["kind"], result["message"])
    if (result and result.get("state") == "failed" and result.get("handed_over") is False) or never_shown:
        # nothing reached the server: pac never named the asynchronous operation, or the server showed no job of it
        # NEVER_SHOWN after the start; nothing is used up (review 14.11.)
        importlog.record(root, {**entry, "status": "not_started", "reason": reason[:400]})
        raise ToolError(f"{entry['zip']} did not reach {env['alias']}: {reason}. Nothing was imported and nothing is used up: "
                        f"{_resume_command(root, entry)} again; if it ends the same way, the step goes to the user on a card.")
    importlog.record(root, {**entry, "status": "failed", "reason": reason[:400]})
    print(f"FAILED: {entry['zip']} was not imported into {env['alias']}: {reason}")
    if log and log.get("failure"):
        print(f"Import record: {log['success']} success, {log['warning']} warnings, {log['failure']} failures")
    if entry.get("restore"):
        print(f"The backup {entry['restore']} stays in exchange/tenant/. Find the cause (skill ppp-diagnose) before another restore.")
        return 1
    if entry.get("kind") == "create":   # an empty first solution: nothing is online, no version is used up (ERWEITERUNGEN A)
        print("Nothing is online; find the cause (skill ppp-diagnose), then ppp import --create again.")
        return 1
    if entry.get("kind") == "move":     # used up for this target only; the project's environment is not touched (C.4)
        source = entry.get("source", "?")
        step = (new_version_step(root, entry["solution"], source, entry["version"], target=env["alias"])
                if load_config(root).get("mode") == "large" else f"the next move needs a new version in {source} (a package imported there)")
        print(f"This ZIP and version {entry['version']} are used up for {env['alias']}: {step}.")
        return 1
    print(f"This ZIP is used up: never import it again. The work in the project stays as it is, and ppp export will not replace "
          f"it (ppp export --compare shows the tenant's state). Find the cause (skill ppp-diagnose), fix it, then pack a new "
          f"version: ppp pack --version {importlog.next_version(entry['version'])}.")
    return 1


# ------------------------------------------------------------------ ppp import --restore
def restore(root: Path, backup: str | None = None, confirmed: bool = False, with_apps: bool = False, wait: float = 100) -> int:
    """Bring the tenant back to a backup taken before an import: the backup packed again with a version above the one
    online and imported like a package. It brings back the content of what the backup holds and removes nothing an
    import added since (pac test round 1, block R; VERBUNDEN VB-12). Always after a card."""
    called = datetime.now().isoformat(timespec="seconds")
    env = tenant.environment(root)
    need_role(env)
    if env["role"] == "production":
        raise ToolError(f"{env['alias']} has the role production: ppp import does not import there.")
    name = package_solution(load_config(root))
    if not name:
        raise ToolError("project.json names no solution to pack.")
    folder = backup_folder(root, env, name)
    last = next((e for e in reversed(importlog.entries(root)) if e.get("restore") and e.get("environment") == env["alias"]
                 and str(e.get("solution", "")).lower() == name.lower()), None)
    if last and last["status"] == "started":    # a restore under way is waited for, never started twice
        built = folder / last["zip"]
        return follow_import(root, env, last, package_parts(built) if built.is_file() else {"flows": {}, "refs": [], "apps": []}, wait, resumed=True)
    backups = sorted(folder.glob("before_*.zip"), key=lambda p: importlog.version_key(p.stem)) if folder.is_dir() else []
    path = (Path(backup) if Path(backup).is_absolute() else root / backup) if backup else (backups[-1] if backups else None)
    if not path or not path.is_file():
        raise ToolError(f"No backup of {name} in {folder.relative_to(root).as_posix()}/; ppp import leaves one there before each import.")
    info, parts = solution.zip_manifest(path), package_parts(path)
    if info["uniqueName"].lower() != name.lower() or info["managed"]:
        raise ToolError(f"{path.name} is not an unmanaged export of {name}.")
    if parts["apps"] and not with_apps:
        raise ToolError("The backup contains apps: " + ", ".join(parts["apps"]) + ". A restore puts their state of then over what "
                        "was changed in Studio since; only with --with-apps.")
    online = tenant.solutions(env["url"]).get(name.lower())
    if not online:
        raise ToolError(f"The solution {name} is not in the environment {env['alias']}; a restore goes on top of it.")
    if online["managed"]:
        raise ToolError(f"{name} is managed in {env['alias']}; an unmanaged package does not go on top of it.")
    running = tenant.running_imports(env["url"], name)
    if running:
        raise TenantError("BUSY", f"an import of {name} is running in {env['alias']} (progress {running[0]} %). Wait for it; "
                                  "ppp tenant shows where it stands.")
    version = importlog.next_version(online["version"])
    if path.name == f"before_{version}.zip":     # that name is taken by the backup this restore starts from
        version = importlog.next_version(version)
    if not cards.confirm(
            f"CONFIRM FIRST (a restore overwrites what is online): show a tenant-step card with the backup {path.name} "
              f"({name} {info['version']}), the environment {env['name']} (role {env['role']}), what the restore does (the "
              f"{len(parts['flows'])} flows and the other components of the backup get their content of then"
              + (f", apps: {', '.join(parts['apps'])}" if parts["apps"] else "") + f", as version {version}; what an import added "
              f"since stays; online now: {online['version']}) and the answers \"Restore\" and \"Not now\". After \"Restore\": the "
              "same command with --confirmed.", confirmed):
        return 1
    built = folder / f"restore_{version}.zip"
    built.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="ppp-restore-") as tmp:
        work = Path(tmp) / online["name"]
        solution.unpack(path, work)
        solution.set_version(work, version)
        solution.pack(work, built)
    # a restore is an import: the state it replaces stays as the backup (VB-12)
    importlog.timed_export(root, env, ["solution", "export", "--name", online["name"], "--path", str(folder / f"before_{version}.zip"),
                        "--overwrite", "--async"], 540)
    entry = importlog.record(root, {"solution": name, "version": version, "zip": built.name, "sha": solution.sha256(built),
                           "environment": env["alias"], "status": "started", "restore": path.name, "called": called,
                           "online_before": online["version"], "flows_before": tenant.flows(env["url"], list(parts["flows"])),
                           "jobs_before": tenant.import_jobs(env["url"], name)})
    result = hand_over(root, env, entry, built, wait)
    if result["state"] in ("failed", "skipped"):
        return report_failed(root, env, entry, f"{result.get('kind', 'SKIPPED')}: {result['message']}", result=result)
    return follow_import(root, env, entry, parts, max(wait - result["seconds"], 0), resumed=False)


# ------------------------------------------------------------------ ppp tenant
def status(root: Path, log: bool = False, values: bool = False, write: bool = False, environment: str | None = None) -> int:
    """What the tenant holds of this project, in a few lines and without the account: versions, the switches of the flows,
    the bindings of the connection references; on request the record of the last import and the values of the
    environment variables. Returns 1 when something deviates. environment: the alias of another environment, a move
    target (ERWEITERUNGEN C.1); --write then writes into its file."""
    env = tenant.environment(root, environment)
    config = load_config(root)
    online = tenant.solutions(env["url"])
    print(f"Tenant {env['alias']}, role {env['role'] or 'not set yet (ppp connect --role)'}"
          + (", in productive use" if env["inUse"] else ""))
    print(importlog.usual_line(root, env["alias"]))
    deviations = 0
    for s in config.get("solutions") or []:
        name = str(s.get("uniqueName"))
        there, mine = online.get(name.lower()), project_version(root / "solution" / name)
        if not there:
            note = "not in this environment"
        elif mine is None:
            note = f"online {there['version']}, not exported into the project yet"
        elif there["version"] == mine:
            note = f"{mine}, as in the project"
        else:
            deviations += 1
            ahead = importlog.version_key(there["version"]) > importlog.version_key(mine)
            if not env["own"]:      # a move target: its state never comes into the project (ERWEITERUNGEN C.4)
                note = (f"WARNING online {there['version']}, project {mine}: "
                        + ("a version the project's base never had" if ahead
                           else f"the project's version has not moved there yet (ppp import --environment {env['alias']})"))
            else:
                note = (f"WARNING online {there['version']}, project {mine}: "
                        + ("take the tenant's state over with ppp export" if ahead else "the project's version is not imported yet"))
        print(f"  {name} ({s.get('role')}): {note}")
    # a move target gets the main solution (ERWEITERUNGEN C), the project's environment the package solution
    name = package_solution(config) if env["own"] else solution_with_role(config, "main")
    folder = root / "solution" / name if name else None
    if not folder or not folder.is_dir():
        return 1 if deviations else 0
    flows = {m.group(2).lower(): m.group(1) for p in sorted((folder / "Workflows").glob("*.json"))
             for m in [re.fullmatch(r"(.+)-(" + tenant.GUID.pattern + r")\.json", p.name)] if m}
    states = tenant.flows(env["url"], list(flows))
    switches = env["data"].get("flowSwitches") if isinstance(env["data"].get("flowSwitches"), dict) else {}
    meant_off = set(switches.get("off") or []) if isinstance(switches.get("off"), list) else set()
    off = sorted(flows[i] for i, s in states.items() if s == "off")
    unknown = sorted(flows[i] for i, s in states.items() if s == "unknown")
    unexpected = [n for n in off if n not in meant_off] + [n for n in sorted(meant_off) if n in flows.values() and n not in off]
    print(f"Flows of {name}: {sum(1 for s in states.values() if s == 'on')} on, {len(off)} off"
          + (": " + ", ".join(off) if off else "") + (f"; not in the tenant: {', '.join(unknown)}" if unknown else ""))
    if meant_off and unexpected:
        deviations += 1
        print("WARNING switches differ from flowSwitches in the environment file: " + ", ".join(unexpected))
    custom = (folder / "Other" / "Customizations.xml").read_bytes().decode("utf-8-sig", "replace")
    references = tenant.connection_references(env["url"], sorted(set(re.findall(r'connectionreferencelogicalname="([^"]+)"', custom))))
    unbound = sorted(n for n, r in references.items() if not r["connection"])
    broken = {}
    if any(r["connection"] for r in references.values()):
        every = tenant.connections(env["url"])
        broken = {n: every[r["connection"]]["status"] for n, r in references.items()
                  if r["connection"] in every and every[r["connection"]]["status"] not in ("Connected", "")}
    print(f"Connection references: {len(references) - len(unbound)} bound, {len(unbound)} without a connection"
          + (": " + ", ".join(unbound) if unbound else ""))
    if unbound or broken:
        deviations += 1
    for n, state in sorted(broken.items()):
        print(f"WARNING the connection of {n} has the status {state}: the user repairs it in the portal")
    if values:
        names = sorted(p.name for p in (folder / "environmentvariabledefinitions").iterdir() if p.is_dir()) \
            if (folder / "environmentvariabledefinitions").is_dir() else []
        for n, v in tenant.variables(env["url"], names).items():
            print(f"  {n}: " + ("not in the tenant" if not v["exists"] else "no current value, the default applies" if v["value"] is None
                                else v["value"]))
    if log:
        record = tenant.import_log(env["url"], name)
        print("Last import: " + (record_line(record, 8) if record else "none ended within the last 12 hours"))
    if write:
        data = dict(env["data"])
        data["connectionReferences"] = {**(data.get("connectionReferences") if isinstance(data.get("connectionReferences"), dict) else {}),
                                        **{n: r["connection"] for n, r in references.items() if r["connection"]}}
        data["flowSwitches"] = {**switches, "on": sorted(flows[i] for i, s in states.items() if s == "on"), "off": off,
                                "readOn": date.today().isoformat()}
        importlog.write_json(env["path"], data)
        print(f"Written to environments/{env['alias']}.json: the bindings and the switches as read; commit it.")
    return 1 if deviations else 0


CHECK_WAIT = 120    # seconds for the one call of ppp check


def check_lines(root: Path) -> list[tuple[str, str]]:
    """For ppp check at the start of a session: one line when tenant and project differ, one when the tenant is out of
    reach on this computer or gave no answer in time. Nothing for an offline project. The first call of pac in a session
    can take well over a minute (pac test 2026-11-13, G4: 102 s), hence CHECK_WAIT."""
    try:
        env = tenant.environment(root)
    except ToolError:
        return []
    try:
        online = tenant.solutions(env["url"], timeout=CHECK_WAIT)
    except TenantError as ex:
        if ex.kind == "TIMEOUT":
            return [("INFO", f"S the tenant {env['alias']} gave no answer within {CHECK_WAIT} seconds (TIMEOUT), which the first call "
                             "of pac in a session can take: ppp check again names the state; ppp export and ppp import wait longer")]
        return [("INFO", f"S the tenant {env['alias']} is out of reach on this computer ({ex.kind}): its steps go to the user on "
                         "cards, as in an offline project")]
    except ToolError:
        return []
    lines = []
    for s in load_config(root).get("solutions") or []:
        name = str(s.get("uniqueName"))
        there, mine = online.get(name.lower()), project_version(root / "solution" / name)
        if there and mine and there["version"] != mine:
            ahead = importlog.version_key(there["version"]) > importlog.version_key(mine)
            lines.append(("WARN", f"S the tenant {env['alias']} has {name} {there['version']}, the project {mine}: "
                                  + ("take it over with ppp export before the next package" if ahead
                                     else "this version is not imported yet")))
    return lines
