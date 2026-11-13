"""The connected mode (entwurf/VERBUNDEN.md): ppp connect, export, import and tenant. A project is connected when
project.json names an environment. Then ppp fetches the export and imports the package itself, each import only after
its checks, and reads the result from the server instead of asking the user for it.

exchange/tenant/ (not in git, left alone by ppp tidy) holds what no commit can rebuild: per solution the backup
before_<version>.zip taken before an import, and imports.jsonl with every import and how it ended.
"""
from __future__ import annotations

import json
import re
import tempfile
import time
import zipfile
from datetime import date, datetime
from pathlib import Path

from . import gitutil, solution, structure, tenant
from .project import ToolError, load_config, package_solution
from .tenant import TenantError
from .verify import SOLUTION_XML, files_of, stable

DEFAULT_ENVIRONMENT = "Citizen Developments"  # the plugin knows its name only; the address comes from the tenant (VB-2)
BY_HAND = "Still by hand: open each changed flow in the designer and save it; then the critical scenarios."


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _version(text: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", text or ""))


def _next(version: str) -> str:
    parts = list(_version(version))
    return ".".join(map(str, parts[:-1] + [parts[-1] + 1])) if parts else "<next>"


def _project_version(folder: Path) -> str | None:
    path = folder / SOLUTION_XML
    return gitutil.version_of(path.read_bytes()) if path.is_file() else None


def _card(env: dict) -> str:
    return "always" if env["confirmImport"] or env["inUse"] else "only on a deviation in the tenant and on a first import"


# ------------------------------------------------------------------ record of imports
def _imports(root: Path) -> list[dict]:
    path = root / "exchange" / "tenant" / "imports.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def _record(root: Path, entry: dict) -> dict:
    entry = {**entry, "time": datetime.now().isoformat(timespec="seconds")}
    path = root / "exchange" / "tenant" / "imports.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _imported(root: Path, name: str, version: str | None, alias: str) -> bool:
    return any(e.get("status") == "done" and e.get("version") == version and e.get("environment") == alias
               and str(e.get("solution", "")).lower() == name.lower() for e in _imports(root))


# ------------------------------------------------------------------ ppp connect
def connect(root: Path, name: str | None = None, role: str | None = None, in_use: bool | None = None,
            confirm: bool | None = None, off: bool = False) -> list[str]:
    """Connect the project to an environment by its display name, or refresh the connection it has: find the
    environment in the tenant, write its address, role and use into environments/<alias>.json and the alias into
    project.json, and say which solutions of the project are online (VERBUNDEN VB-2, VB-3, VB-11)."""
    path = root / "project.json"
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    alias = config.get("environment")
    if off:
        if not alias:
            return ["The project is offline already."]
        _write(path, {k: v for k, v in config.items() if k not in ("environment", "confirmImport")})
        return [f"Offline again: the user exports and imports by hand, guided by cards. environments/{alias}.json stays as it is. "
                "Commit project.json."]
    known_file = root / "environments" / f"{alias}.json" if alias else None
    known = json.loads(known_file.read_text(encoding="utf-8-sig")) if known_file and known_file.is_file() else {}
    found = tenant.find_environment(name or known.get("name") or DEFAULT_ENVIRONMENT)
    if name or not alias:
        alias = structure.slug(found["name"])
    file = root / "environments" / f"{alias}.json"
    old = json.loads(file.read_text(encoding="utf-8-sig")) if file.is_file() else {}
    production = str(found.get("type") or "").strip().lower() == "production"
    source = "--role" if role else f"environments/{alias}.json" if old.get("role") else None
    # pac's type Production decides the role unless it is given: ppp import never imports into a production role
    role = role or old.get("role") or ("production" if production else "development")
    if role not in structure.ENVIRONMENT_ROLES:
        raise ToolError(f"role must be one of {', '.join(structure.ENVIRONMENT_ROLES)}")
    data = {"name": found["name"], "environmentUrl": found["url"], "role": role,
            "inUse": bool(old.get("inUse", False)) if in_use is None else in_use,
            **{k: v for k, v in old.items() if k not in ("name", "environmentUrl", "role", "inUse")}}
    _write(file, data)
    confirm = config.get("confirmImport", True) if confirm is None else confirm
    new = {}
    for key, value in config.items():
        if key not in ("environment", "confirmImport"):
            new[key] = value
        if key == "storage":
            new.update(environment=alias, confirmImport=confirm)
    new.setdefault("environment", alias)
    new.setdefault("confirmImport", confirm)
    _write(path, new)
    env = {"confirmImport": confirm, "inUse": data["inUse"]}
    lines = [f"Connected to {found['name']}: environments/{alias}.json with its address, role {role}, "
             + ("in productive use" if data["inUse"] else "not in productive use") + f"; card before each import: {_card(env)}."]
    if production and not source:
        lines.append(f"Role production because pac names {found['name']} an environment of type Production. Another role only "
                     f"explicitly: ppp connect \"{found['name']}\" --role development|test.")
    elif production and role != "production":
        lines.append(f"WARNING pac names {found['name']} an environment of type Production, and the role is {role} ({source}): "
                     "ppp import imports there. Keep it only if that is meant; else ppp connect --role production.")
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
    mine = _project_version(folder)
    # "imported" only silences the message below; work committed after the import is still work (VB-14)
    if not _imported(root, name, mine, alias) and _version(mine or "") > _version(online_version):
        return f"version {mine} is packed but not imported (online: {online_version})"
    try:
        base = gitutil.tenant_commit(root, folder)
    except ToolError:
        return None
    changed = gitutil.git(root, "diff", "--name-only", base, "HEAD", "--", where).decode().split()
    return f"{len(changed)} files changed since the last export" if changed else None


def export(root: Path, take, name: str | None = None, compare: bool = False, no_commit: bool = False, force: bool = False,
           wait: float = 540) -> int:
    """Fetch the solution from the tenant and take it into solution/<UniqueName>/ like ppp unpack: the diff against the
    last commit shows what was changed by hand in the tenant (VERBUNDEN VB-8). `take` is the one way an export enters
    the project (cli._take_export)."""
    env = tenant.environment(root)
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
        return _compare(env, online, folder, arguments, wait)
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
    tenant.run(env["url"], arguments, timeout=wait)
    print(f"Exported {online['name']} {online['version']} from {env['alias']} to exchange/{target.name}")
    return take(root, target, force=force, no_commit=no_commit)


def _unpacked(package: Path, name: str) -> dict[str, bytes]:
    with tempfile.TemporaryDirectory(prefix="ppp-tenant-") as tmp:
        folder = Path(tmp) / name
        solution.unpack(package, folder)
        return {f: (folder / f).read_bytes() for f in files_of(folder)}


def _difference(theirs: dict[str, bytes], ours: dict[str, bytes]) -> list[str]:
    """Files that differ between the tenant and a state of the project; values the server rewrites do not count."""
    return (sorted(f for f in theirs.keys() & ours.keys() if stable(f, theirs[f]) != stable(f, ours[f]))
            + sorted(f + " (only in the tenant)" for f in theirs.keys() - ours.keys())
            + sorted(f + " (not in the tenant)" for f in ours.keys() - theirs.keys()))


def _compare(env: dict, online: dict, folder: Path, arguments: list[str], wait: float) -> int:
    with tempfile.TemporaryDirectory(prefix="ppp-compare-") as tmp:
        arguments[5] = str(Path(tmp) / "tenant.zip")
        tenant.run(env["url"], arguments, timeout=wait)
        theirs = _unpacked(Path(arguments[5]), online["name"])
    ours = {f: (folder / f).read_bytes() for f in files_of(folder)} if folder.is_dir() else {}
    different = _difference(theirs, ours)
    print(f"Tenant {env['alias']}: {online['name']} {online['version']}; project: {_project_version(folder) or 'not exported yet'}")
    print(f"Different ({len(different)}): " + (", ".join(different[:40]) or "-") + (f" … {len(different) - 40} more" if len(different) > 40 else ""))
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
            found.append((_version(info["version"]), path))
    if not found:
        raise ToolError(f"No package of {name} in exchange/; ppp pack builds one.")
    return max(found)[1]


def _parts(package: Path) -> dict:
    """What a package holds: flows by ID with their names, connection references, apps."""
    with zipfile.ZipFile(package) as z:
        names = z.namelist()
        custom = next((z.read(n).decode("utf-8-sig", "replace") for n in names if n.lower() == "customizations.xml"), "")
    flows = {m.group(2).lower(): m.group(1) for n in names
             for m in [re.fullmatch(r"Workflows/(.+)-(" + tenant.GUID.pattern + r")\.json", n)] if m}
    return {"flows": flows, "refs": sorted(set(re.findall(r'connectionreferencelogicalname="([^"]+)"', custom))),
            "apps": sorted({n.split("/")[1] for n in names if n.startswith("CanvasApps/") and "/" in n})}


def _drift(root: Path, folder: Path, backup: Path, online_version: str) -> list[str]:
    """What the tenant has that the project did not build on: the export just taken against the commit that holds the
    tenant's state of the version online (VERBUNDEN VB-8)."""
    try:
        base = gitutil.tenant_commit(root, folder, online_version)
    except ToolError:
        return [f"the tenant has version {online_version}, which this project never saw"]
    prefix = gitutil.rel(root, folder) + "/"
    blobs = gitutil.read_blobs(root, base, [prefix + f for f in gitutil.tracked_files(root, base, folder)])
    return _difference(_unpacked(backup, folder.name), {k[len(prefix):]: v for k, v in blobs.items()})


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
    env = tenant.environment(root)
    if env["role"] == "production":
        raise ToolError(f"{env['alias']} has the role production: ppp import does not import there. Production goes the "
                        "governance way (ANFORDERUNGEN T8).")
    name = package_solution(load_config(root))
    if not name:
        raise ToolError("project.json names no solution to pack.")
    path = (Path(package) if Path(package).is_absolute() else root / package) if package else _newest_package(root, name)
    if not path.is_file():
        raise ToolError(f"Package not found: {path}")
    info, digest, parts = solution.zip_manifest(path), solution.sha256(path), _parts(path)
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
    last = next((e for e in reversed(_imports(root)) if e.get("sha") == digest and e.get("environment") == env["alias"]), None)
    if last and last["status"] == "failed":
        raise ToolError(f"{path.name} failed on import ({last.get('reason', 'see ppp tenant --log')}) and is used up: never import "
                        f"the same ZIP again. Fix the cause and pack a new version: ppp pack --version {_next(info['version'])}.")
    if last and last["status"] == "done":
        raise ToolError(f"{path.name} is imported already ({last['time']}). Next: ppp export.")
    if last and last["status"] == "started":
        return _follow(root, env, last, parts, wait, resumed=True)
    spent = next((e for e in _imports(root) if e.get("status") == "failed" and not e.get("restore") and e.get("version") == info["version"]
                  and e.get("environment") == env["alias"] and str(e.get("solution", "")).lower() == name.lower()), None)
    if spent:     # a repacked package with the version of a failed one (VB-14)
        raise ToolError(f"Version {info['version']} of {name} failed on import into {env['alias']} ({spent['zip']}) and is used up, "
                        f"also for a package packed again: ppp pack --version {_next(info['version'])}.")
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
                            f"{_next(_project_version(folder) or info['version'])}.")

    online = tenant.solutions(env["url"]).get(name.lower())
    if online and online["managed"]:
        raise ToolError(f"{name} is managed in {env['alias']}; an unmanaged package does not go on top of it.")
    if online and _version(info["version"]) <= _version(online["version"]):
        raise ToolError(f"Version {info['version']} is not higher than the version online ({online['version']}): pack again with "
                        f"ppp pack --version {_next(online['version'])}.")
    running = tenant.running_imports(env["url"], name)
    if running:
        raise TenantError("BUSY", f"an import of {name} is running in {env['alias']} (progress {running[0]} %). Wait for it; "
                                  "ppp tenant shows where it stands.")
    drift = []
    if online:      # the backup before the import is the export of the drift check (VB-12)
        backup = root / "exchange" / "tenant" / online["name"] / f"before_{info['version']}.zip"
        backup.parent.mkdir(parents=True, exist_ok=True)
        tenant.run(env["url"], ["solution", "export", "--name", online["name"], "--path", str(backup), "--overwrite", "--async"],
                   timeout=540)
        drift = _drift(root, root / "solution" / online["name"], backup, online["version"])
    if drift and not accept_drift:
        print(f"DRIFT: the tenant differs from the state this package was built on ({len(drift)}): " + ", ".join(drift[:30])
              + (f" … {len(drift) - 30} more" if len(drift) > 30 else ""))
        print("Nothing was imported. The import would overwrite these changes. Show them (ppp export --compare) and ask on a "
              "card: commit the work first, then ppp export --force, then rebuild the work on the tenant's state (it stays in git), "
              "then pack again; or import anyway (--accept-drift). ppp export never replaces uncommitted work.")
        return 1
    reasons = [text for needed, text in ((env["confirmImport"], "this project asks before each import"),
                                         (env["inUse"], "the solution is in productive use there"),
                                         (not online, "first import into this environment"),
                                         (bool(drift), "the tenant differs and the import overwrites it")) if needed]
    if reasons and not confirmed:
        print(f"CONFIRM FIRST ({'; '.join(reasons)}): show a tenant-step card with the package {path.name} ({name} {info['version']}, "
              f"SHA-256 {digest[:12]}…), the environment {env['name']} (role {env['role']}), what the import replaces "
              f"({len(parts['flows'])} flows, {len(parts['refs'])} connection references"
              + (f", apps: {', '.join(parts['apps'])}" if parts["apps"] else "") + f"; online now: "
              f"{online['version'] if online else 'nothing yet'}) and the answers \"Import\" and \"Not now\". After \"Import\": "
              "the same command with --confirmed.")
        return 1
    entry = _record(root, {"solution": name, "version": info["version"], "zip": path.name, "sha": digest,
                           "environment": env["alias"], "status": "started", "online_before": online["version"] if online else None,
                           "flows_before": tenant.flows(env["url"], list(parts["flows"])) if online else {},
                           "jobs_before": tenant.import_jobs(env["url"], name)})
    result = tenant.start_import(env["url"], path, wait)
    if result["state"] == "failed":
        return _failed(root, env, entry, f"{result['kind']}: {result['message']}", result=result)
    return _follow(root, env, entry, parts, max(wait - result["seconds"], 0), resumed=False)


def _follow(root: Path, env: dict, entry: dict, parts: dict, wait: float, resumed: bool) -> int:
    """Read from the server where the import stands: the version online is the proof that it arrived, the ended job of
    this import the proof that it did not (VB-10). Without that job the import stays RUNNING: a queue, a long upload or
    an aborted call can hold it back. FAILED without a job only when the server showed none NEVER_SHOWN after the start."""
    name, version, began = entry["solution"], entry["version"], time.monotonic()
    arrived = lambda: (tenant.solutions(env["url"]).get(name.lower()) or {}).get("version") == version
    while True:
        if arrived():
            return _done(root, env, entry, parts)
        running = tenant.running_imports(env["url"], name)
        if not running:
            log = _own_log(env, entry)
            if log and arrived():       # the job may end a moment before the version shows
                return _done(root, env, entry, parts)
            if log:
                return _failed(root, env, entry, "; ".join(log.get("texts") or [])
                               or "the import ended and the version online did not change", log)
            if _age(entry) > NEVER_SHOWN:
                return _failed(root, env, entry, f"the server never showed this import: no job of it within {NEVER_SHOWN // 60} "
                               "minutes of the start, and the version online did not change"
                               + ("" if isinstance(entry.get("jobs_before"), list) else
                                  " (an entry from before ppp held the jobs at the start: ppp tenant --log shows the newest job)"))
        if time.monotonic() - began >= wait:
            usual = next((e.get("seconds") for e in reversed(_imports(root))
                          if e.get("status") == "done" and e.get("environment") == env["alias"]), None)
            print(f"RUNNING: the import of {entry['zip']} into {env['alias']} is not finished"
                  + (f" (progress {running[0]} %)" if running else " (the server does not show it yet)")
                  + f", started {entry['time'][11:16]}."
                  + (f" The last import there took about {max(round(usual / 60), 1)} min." if usual is not None else ""))
            print("Run ppp import again to wait further; it starts no second import.")
            return 0
        time.sleep(10)


def _done(root: Path, env: dict, entry: dict, parts: dict) -> int:
    """After the import ppp confirms by itself what the user used to report (VERBUNDEN VB-16)."""
    name, seconds = entry["solution"], round(_age(entry))
    print(f"IMPORTED: {entry['zip']} is in {env['alias']}, {name} {entry['version']} is online (about {seconds} s).")
    warnings = 0
    log = _own_log(env, entry)      # only the job of this import, never the numbers of an earlier one
    if log:
        print(f"Import record: {log['success']} success, {log['warning']} warnings, {log['failure']} failures"
              + ("".join(f"\n  {t}" for t in log["texts"][:5]) if log["texts"] else ""))
        if log["failure"] > 0:
            warnings += 1
            print(f"WARNING the import record names {log['failure']} failures")
    else:
        print("Import record: not readable yet (ppp tenant --log)")
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
    _record(root, {**entry, "status": "done", "seconds": seconds, "warnings": warnings})
    folder = root / "exchange" / "tenant" / name
    for old in sorted(folder.glob("before_*.zip")) if folder.is_dir() else []:     # the backup of this import stays until the next one
        if old.name != f"before_{entry['version']}.zip":
            old.unlink()
    if warnings:
        print(f"{warnings} warnings above: show them to the user before going on.")
    print(BY_HAND)
    if entry.get("restore"):
        (folder / entry["zip"]).unlink(missing_ok=True)
        print(f"This was a restore of {entry['restore']}. Next: ppp export; it takes the restored state into the project and "
              "shows the changes of the later packages as reverted. They stay in git.")
    else:
        print("Next: ppp export; it commits the tenant's state as the base of the next package.")
    return 0


def _failed(root: Path, env: dict, entry: dict, reason: str, log: dict | None = None, result: dict | None = None) -> int:
    """A failed import uses the ZIP up; the work in the project stays (VERBUNDEN VB-14). When pac did not reach the server
    (AUTH, SYNTAX, BUSY) nothing is used up: the entry ends as not_started and the usual error with the next step is raised."""
    if result and result.get("kind") in ("AUTH", "SYNTAX", "BUSY"):
        _record(root, {**entry, "status": "not_started", "reason": reason[:400]})
        raise TenantError(result["kind"], result["message"])
    _record(root, {**entry, "status": "failed", "reason": reason[:400]})
    print(f"FAILED: {entry['zip']} was not imported into {env['alias']}: {reason}")
    if log and log.get("failure"):
        print(f"Import record: {log['success']} success, {log['warning']} warnings, {log['failure']} failures")
    if entry.get("restore"):
        print(f"The backup {entry['restore']} stays in exchange/tenant/. Find the cause (skill ppp-diagnose) before another restore.")
        return 1
    print(f"This ZIP is used up: never import it again. The work in the project stays as it is, and ppp export will not replace "
          f"it (ppp export --compare shows the tenant's state). Find the cause (skill ppp-diagnose), fix it, then pack a new "
          f"version: ppp pack --version {_next(entry['version'])}.")
    return 1


# ------------------------------------------------------------------ ppp import --restore
def restore(root: Path, backup: str | None = None, confirmed: bool = False, with_apps: bool = False, wait: float = 100) -> int:
    """Bring the tenant back to a backup taken before an import: the backup packed again with a version above the one
    online and imported like a package. It brings back the content of what the backup holds and removes nothing an
    import added since (pac test round 1, block R; VERBUNDEN VB-12). Always after a card."""
    env = tenant.environment(root)
    if env["role"] == "production":
        raise ToolError(f"{env['alias']} has the role production: ppp import does not import there.")
    name = package_solution(load_config(root))
    if not name:
        raise ToolError("project.json names no solution to pack.")
    folder = root / "exchange" / "tenant" / name
    last = next((e for e in reversed(_imports(root)) if e.get("restore") and e.get("environment") == env["alias"]
                 and str(e.get("solution", "")).lower() == name.lower()), None)
    if last and last["status"] == "started":    # a restore under way is waited for, never started twice
        built = folder / last["zip"]
        return _follow(root, env, last, _parts(built) if built.is_file() else {"flows": {}, "refs": [], "apps": []}, wait, resumed=True)
    backups = sorted(folder.glob("before_*.zip"), key=lambda p: _version(p.stem)) if folder.is_dir() else []
    path = (Path(backup) if Path(backup).is_absolute() else root / backup) if backup else (backups[-1] if backups else None)
    if not path or not path.is_file():
        raise ToolError(f"No backup of {name} in exchange/tenant/{name}/; ppp import leaves one there before each import.")
    info, parts = solution.zip_manifest(path), _parts(path)
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
    version = _next(online["version"])
    if path.name == f"before_{version}.zip":     # that name is taken by the backup this restore starts from
        version = _next(version)
    if not confirmed:
        print(f"CONFIRM FIRST (a restore overwrites what is online): show a tenant-step card with the backup {path.name} "
              f"({name} {info['version']}), the environment {env['name']} (role {env['role']}), what the restore does (the "
              f"{len(parts['flows'])} flows and the other components of the backup get their content of then"
              + (f", apps: {', '.join(parts['apps'])}" if parts["apps"] else "") + f", as version {version}; what an import added "
              f"since stays; online now: {online['version']}) and the answers \"Restore\" and \"Not now\". After \"Restore\": the "
              "same command with --confirmed.")
        return 1
    built = folder / f"restore_{version}.zip"
    built.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="ppp-restore-") as tmp:
        work = Path(tmp) / online["name"]
        solution.unpack(path, work)
        solution.set_version(work, version)
        solution.pack(work, built)
    # a restore is an import: the state it replaces stays as the backup (VB-12)
    tenant.run(env["url"], ["solution", "export", "--name", online["name"], "--path", str(folder / f"before_{version}.zip"),
                            "--overwrite", "--async"], timeout=540)
    entry = _record(root, {"solution": name, "version": version, "zip": built.name, "sha": solution.sha256(built),
                           "environment": env["alias"], "status": "started", "restore": path.name,
                           "online_before": online["version"], "flows_before": tenant.flows(env["url"], list(parts["flows"])),
                           "jobs_before": tenant.import_jobs(env["url"], name)})
    result = tenant.start_import(env["url"], built, wait)
    if result["state"] == "failed":
        return _failed(root, env, entry, f"{result['kind']}: {result['message']}", result=result)
    return _follow(root, env, entry, parts, max(wait - result["seconds"], 0), resumed=False)


# ------------------------------------------------------------------ ppp tenant
def status(root: Path, log: bool = False, values: bool = False, write: bool = False) -> int:
    """What the tenant holds of this project, in a few lines and without the account: versions, the switches of the flows,
    the bindings of the connection references; on request the record of the last import and the values of the
    environment variables. Returns 1 when something deviates."""
    env = tenant.environment(root)
    config = load_config(root)
    online = tenant.solutions(env["url"])
    print(f"Tenant {env['alias']}, role {env['role']}" + (", in productive use" if env["inUse"] else ""))
    deviations = 0
    for s in config.get("solutions") or []:
        name = str(s.get("uniqueName"))
        there, mine = online.get(name.lower()), _project_version(root / "solution" / name)
        if not there:
            note = "not in this environment"
        elif mine is None:
            note = f"online {there['version']}, not exported into the project yet"
        elif there["version"] == mine:
            note = f"{mine}, as in the project"
        else:
            deviations += 1
            ahead = _version(there["version"]) > _version(mine)
            note = (f"WARNING online {there['version']}, project {mine}: "
                    + ("take the tenant's state over with ppp export" if ahead else "the project's version is not imported yet"))
        print(f"  {name} ({s.get('role')}): {note}")
    name = package_solution(config)
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
        print("Last import: " + (f"{record['success']} success, {record['warning']} warnings, {record['failure']} failures"
                                 + "".join(f"\n  {t}" for t in record["texts"]) if record else "none ended within the last 12 hours"))
    if write:
        data = dict(env["data"])
        data["connectionReferences"] = {**(data.get("connectionReferences") if isinstance(data.get("connectionReferences"), dict) else {}),
                                        **{n: r["connection"] for n, r in references.items() if r["connection"]}}
        data["flowSwitches"] = {**switches, "on": sorted(flows[i] for i, s in states.items() if s == "on"), "off": off,
                                "readOn": date.today().isoformat()}
        _write(env["path"], data)
        print(f"Written to environments/{env['alias']}.json: the bindings and the switches as read; commit it.")
    return 1 if deviations else 0


def check_lines(root: Path) -> list[tuple[str, str]]:
    """For ppp check at the start of a session: one line when tenant and project differ, one when the tenant is out of
    reach on this computer. Nothing for an offline project."""
    try:
        env = tenant.environment(root)
    except ToolError:
        return []
    try:
        online = tenant.solutions(env["url"], timeout=40)
    except TenantError as ex:
        return [("INFO", f"S the tenant {env['alias']} is out of reach on this computer ({ex.kind}): its steps go to the user on "
                         "cards, as in an offline project")]
    except ToolError:
        return []
    lines = []
    for s in load_config(root).get("solutions") or []:
        name = str(s.get("uniqueName"))
        there, mine = online.get(name.lower()), _project_version(root / "solution" / name)
        if there and mine and there["version"] != mine:
            ahead = _version(there["version"]) > _version(mine)
            lines.append(("WARN", f"S the tenant {env['alias']} has {name} {there['version']}, the project {mine}: "
                                  + ("take it over with ppp export before the next package" if ahead
                                     else "this version is not imported yet")))
    return lines
