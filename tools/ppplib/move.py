"""The move into an environment of role test (entwurf/ERWEITERUNGEN.md, C; stage 1b): the fresh export of the main
solution from the project's environment, with the same version, imported into a move target with a settings file built
from environments/<target>.json. Always after a card; never from the target back into the project.

What a move leaves (ERWEITERUNGEN C.4): in exchange/tenant/<target>/<Main>/ the export that moved (source_<v>.zip), the
backup of the target before it (before_<v>.zip) and the settings file (settings_<v>.json); in imports.jsonl an entry of
kind move with the environment of the target and the alias of its source. project.json stays as it is.
"""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

from . import agent, cards, connected, gitutil, importlog, solution, structure, tenant
from . import compare as diffs     # move.compare is ppp export --compare --environment
from .project import ToolError, load_config, package_solution, solution_with_role
from .tenant import TenantError

# the values of the environment variables come from the settings file; after IMPORTED ppp compares them with the file
VALUES = "environmentvariabledefinitions/*/environmentvariablevalues.json"
SECTIONS = ("EnvironmentVariables", "ConnectionReferences")
# create-settings writes this section too (pac test round 1, X4); ppp fills no agents, tenant.check_settings refuses it
AGENTS = "CopilotAgents"
PORTAL = "Solutions › New solution › Publisher › New publisher, with the four values of ppp settings"
REFERENCE = re.compile(r"<connectionreference\b([^>]*?)(?:/>|>(.*?)</connectionreference>)", re.S)


# ------------------------------------------------------------------ helpers
def _main(root: Path) -> str:
    name = solution_with_role(load_config(root), "main")
    if not name:
        raise ToolError("project.json names no solution of role main: a move takes the main solution.")
    return name


def _file(env: dict) -> str:
    return f"environments/{env['alias']}.json"


def _section(env: dict, key: str) -> dict:
    value = env["data"].get(key)
    return value if isinstance(value, dict) else {}


def connectors(custom: str) -> dict[str, str]:
    """The connection references of a Customizations.xml by logical name, each with its connector: the last part of its
    connectorid (/providers/Microsoft.PowerApps/apis/<connector>); empty when the file names none."""
    found = {}
    for attributes, body in REFERENCE.findall(custom):
        name = re.search(r'connectionreferencelogicalname="([^"]+)"', attributes)
        if name:
            connector = re.search(r"<connectorid>\s*([^<\s]+)\s*</connectorid>", body or "", re.I)
            found[name.group(1)] = connector.group(1).rstrip("/").rsplit("/", 1)[-1] if connector else ""
    return found


def _committed_connectors(root: Path, name: str) -> dict[str, str]:
    path = root / "solution" / name / "Other" / "Customizations.xml"
    return connectors(path.read_bytes().decode("utf-8-sig", "replace")) if path.is_file() else {}


def _short(connection: str) -> str:
    return connection[:8] + "…" if len(connection) > 10 else connection


def _project_env(root: Path) -> dict:
    return tenant.environment(root)


def _address(url) -> str:
    """An environment's address as it counts for being the same: lower case, without the slash at the end."""
    return str(url or "").strip().rstrip("/").lower()


def _production_at(root: Path, url: str) -> str | None:
    """The alias of a file in environments/ that names this address with the role production, else None: whatever alias
    a move target has, ppp never moves into an environment that the project knows as production."""
    for path in sorted((root / "environments").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("role") == "production" and _address(data.get("environmentUrl")) == _address(url):
            return path.stem
    return None


def _never_production(root: Path, url: str, name: str) -> None:
    other = _production_at(root, url)
    if other:
        raise ToolError(f"environments/{other}.json names the address of {name} with the role production: ppp never moves there; "
                        "a move target is an environment of role test.")


def _values_in(package: Path) -> set[str]:
    """The environment variables whose current value travels in the package: those with
    environmentvariabledefinitions/<schema>/environmentvariablevalues.json in it (an export carries the value the
    environment has)."""
    with zipfile.ZipFile(package) as z:
        names = z.namelist()
    return {parts[1] for parts in (n.split("/") for n in names)
            if len(parts) == 3 and parts[0].lower() == "environmentvariabledefinitions" and parts[2].lower() == "environmentvariablevalues.json"}


# ------------------------------------------------------------------ ppp connect --target
def connect_target(root: Path, name: str, in_use: bool | None) -> list[str]:
    """ppp connect "<Name>" --role test --target [--in-use yes|no] (ERWEITERUNGEN C.1): find the environment by its
    display name and write only environments/<target>.json (name, environmentUrl, role test, inUse; other fields stay);
    project.json keeps its environment and confirmImport. Returns the lines: Connected as move target, the solutions of
    the project there, the publisher line (publisher.connect_lines), the connections per connector, Next. Refused: a file
    of this alias with the role production or with another address (its bindings and values belong to that environment),
    and any file in environments/ that names this address with the role production."""
    own = _project_env(root)       # a move needs the project's environment: its export is what moves
    found = tenant.find_environment(name)
    alias = structure.slug(found["name"])
    if alias == own["alias"] or _address(found["url"]) == _address(own["url"]):
        raise ToolError(f"{found['name']} is the project's environment ({own['alias']}): a move target is a second environment.")
    file = root / "environments" / f"{alias}.json"
    old = json.loads(file.read_text(encoding="utf-8-sig")) if file.is_file() else {}
    old = old if isinstance(old, dict) else {}
    if old.get("role") == "production":
        raise ToolError(f"environments/{alias}.json has the role production: ppp never moves there; a move target is an environment "
                        "of role test.")
    if old.get("environmentUrl") and _address(old["environmentUrl"]) != _address(found["url"]):
        raise ToolError(f"environments/{alias}.json names another address than {found['name']} has now: its bindings and values belong "
                        "to that environment and must be set anew. Check the file, or remove it, then ppp connect --target again.")
    _never_production(root, found["url"], found["name"])
    data = {"name": found["name"], "environmentUrl": found["url"], "role": "test", "type": found.get("type") or "",
            "inUse": bool(old.get("inUse", False)) if in_use is None else in_use,
            **{k: v for k, v in old.items() if k not in ("name", "environmentUrl", "role", "type", "inUse")}}
    before = file.read_bytes() if file.is_file() else None
    importlog.write_json(file, data)
    try:        # a read that fails leaves the file as it was, not half new (review 14.11.)
        return _target_lines(root, own, found, alias)
    except BaseException:
        if before is None:
            file.unlink(missing_ok=True)
        else:
            file.write_bytes(before)
        raise


def _target_lines(root: Path, own: dict, found: dict, alias: str) -> list[str]:
    from . import publisher
    # the type as pac env list gives it, a number: which number is production is not known yet (TEST_PAC, J1); the user
    # sees it on the cards of the move (review 14.11.)
    lines = [f"Connected as move target {found['name']}: environments/{alias}.json with its address, role test, type "
             f"{found.get('type') or '?'} in pac env list (check that it is no production environment); project.json keeps "
             f"{own['alias']}."]
    online = tenant.solutions(found["url"])
    for s in load_config(root).get("solutions") or []:
        there = online.get(str(s.get("uniqueName", "")).lower())
        lines.append(f"  {s.get('uniqueName')} ({s.get('role')}): " + (f"online {there['version']}" + (", managed" if there["managed"] else "")
                                                                    if there else "not in this environment yet"))
    env = tenant.environment(root, alias)
    lines += publisher.connect_lines(root, env)
    wanted = sorted({c for c in _committed_connectors(root, _main(root)).values() if c})
    if wanted:
        every = tenant.connections(env["url"])
        for connector in wanted:
            n = sum(1 for c in every.values() if c["connector"].lower() == connector.lower() and c["status"] == "Connected")
            lines.append(f"Connections there for {connector}: {n} connected" if n else
                         f"Connections there for {connector}: none: the user creates one in {found['name']} first.")
    lines.append(f"Next: write the bindings and values into environments/{alias}.json (ppp tenant --environment {alias} "
                 f"--connections lists the connections), then ppp import --environment {alias}.")
    return lines


# ------------------------------------------------------------------ ppp import --environment
def _target(root: Path, alias: str) -> tuple[dict, dict]:
    """C.2 point 1: the target and the project's environment; the target of role test, never the project's environment,
    and never an address that a file in environments/ names with the role production."""
    env = tenant.environment(root, alias)
    own = _project_env(root)
    if env["own"] or _address(env["url"]) == _address(own["url"]):
        raise ToolError(f"{alias} is the project's environment: ppp import without --environment imports there.")
    connected.need_role(env)
    if env["role"] != "test":
        raise ToolError(f"{alias} has the role {env['role']}: a move goes to an environment of role test only.")
    _never_production(root, env["url"], env["name"])
    return env, own


def _settings_skeleton(source: Path, path: Path) -> dict:
    """pac solution create-settings, local (pac test X4): the components of the package, empty values. The section of
    agents goes; one that names an agent, or any other section, is refused, so nothing of it goes unseen."""
    path.unlink(missing_ok=True)
    solution.run_pac("solution", "create-settings", "--solution-zip", str(source), "--settings-file", str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as ex:
        raise ToolError(f"pac solution create-settings wrote no readable {path.name} ({ex}).") from ex
    if not isinstance(data, dict):
        raise ToolError(f"pac solution create-settings wrote {path.name} not as a JSON object.")
    other = sorted(k for k in data if k not in (*SECTIONS, AGENTS))
    if other or data.get(AGENTS):
        raise ToolError(f"{source.name} needs settings ppp does not fill ({', '.join(other + ([AGENTS] if data.get(AGENTS) else []))}): "
                        "this move goes on a card.")
    for section, fields in tenant.SETTINGS_SECTIONS.items():
        entries = data.get(section) or []
        if not isinstance(entries, list) or not all(isinstance(e, dict) and isinstance(e.get(fields[0]), str) for e in entries):
            raise ToolError(f"pac solution create-settings wrote {section} in a form ppp does not know: this move goes on a card.")
    return {section: list(data.get(section) or []) for section in SECTIONS}


def _source(root: Path, own: dict, name: str, command: str) -> tuple[Path, str, dict]:
    """C.2 points 2 to 4: the main solution in the project's environment as committed, nothing imported there that waits
    for its export, no import running there. The folder, the project's version and the solution online."""
    # an import into the project's environment under way (of the main solution, or of the transfer solution, whose
    # components are the main solution's): its export comes first, then the move
    busy = f"an import into {own['alias']} is still running: ppp import waits for it, then ppp export, then the move."
    imported = {name.lower(), str(package_solution(load_config(root)) or name).lower()}
    last_of = {}
    for e in importlog.entries(root):
        if e.get("environment") == own["alias"] and str(e.get("solution", "")).lower() in imported and e.get("status") != "exported":
            last_of[str(e.get("solution", "")).lower()] = e.get("status")
    if "started" in last_of.values():
        raise ToolError(busy)
    importlog.need_export(root, name, command)                                         # 2
    work = root / "solution" / name
    if not work.is_dir():
        raise ToolError(f"solution/{name}/ does not exist: ppp export --solution {name} first; a move carries only a committed state.")
    if gitutil.git(root, "status", "--porcelain", "--", gitutil.rel(root, work)).strip():   # 3
        raise ToolError(f"Uncommitted changes in solution/{name}: commit them first; a move carries only a committed state.")
    mine = connected.project_version(work)
    online = tenant.solutions(own["url"]).get(name.lower())                            # 4
    if not online:
        raise ToolError(f"{name} is not in {own['alias']}: a move takes its export from there.")
    if online["managed"]:
        raise ToolError(f"{name} is managed in {own['alias']}; ppp moves unmanaged solutions only.")
    if online["version"] != mine:
        raise ToolError(f"{own['alias']} has {name} {online['version']}, the project {mine}: ppp export --solution {name} first.")
    if any(tenant.running_imports(own["url"], n) for n in sorted({name, package_solution(load_config(root)) or name})):
        raise ToolError(busy)
    return work, mine, online


def _used_up(root: Path, name: str, alias: str) -> list[str]:
    """The versions of the main solution that failed on a move into the target: used up for it (C.4)."""
    return [str(e["version"]) for e in importlog.entries(root) if e.get("kind") == "move" and e.get("status") == "failed"
            and e.get("version") and importlog.of(e, name, alias)]


def raise_version(root: Path, alias: str, confirmed: bool) -> int:
    """ppp import --environment <target> --raise-version [--confirmed] (VERBUNDEN VB-20, mode large; user, 13.11.): in
    mode large ppp packs only the transfer solution, so the version of the main solution never rises in the project's
    environment by itself. When the target has that version or a higher one, or it is used up there, this raises it
    above the highest of them with pac solution online-version, always after a card, and nothing else: the export into
    the project (ppp export --solution <main>) and the move follow, the move on its own card. pac test round 3, O1: pac
    solution list and the export carry the version set. Never in an environment of role production."""
    if load_config(root).get("mode") != "large":
        raise ToolError("--raise-version is for mode large: in the other modes ppp pack raises the version, and ppp import brings "
                        "it into the project's environment.")
    env, own = _target(root, alias)
    name = _main(root)
    if own["role"] == "production":
        raise ToolError(f"{own['alias']} has the role production: ppp raises no version there.")
    last = next((e for e in reversed(importlog.entries(root)) if e.get("kind") == "move" and importlog.of(e, name, env["alias"])), None)
    if last and last["status"] == "started":
        raise ToolError(f"A move into {env['alias']} is under way: ppp import --environment {env['alias']} waits for it first.")
    work, mine, online = _source(root, own, name, f"ppp import --environment {env['alias']} --raise-version")
    there = tenant.solutions(env["url"]).get(name.lower())
    if there and there["managed"]:
        raise ToolError(f"{name} is managed in {env['alias']}; an unmanaged package does not go on top of it, so a new version "
                        "would not help.")
    spent = _used_up(root, name, env["alias"])
    blocking = [v for v in [*(([there["version"]]) if there else []), *spent] if importlog.version_key(v) >= importlog.version_key(mine)]
    if not blocking:
        raise ToolError(f"No new version needed: {name} {mine} is above what {env['alias']} has "
                        f"({there['version'] if there else 'nothing yet'}) and is not used up there; ppp import --environment "
                        f"{env['alias']} moves it.")
    new = importlog.next_version(max([mine, *blocking], key=importlog.version_key))
    why = (f"{env['alias']} has {there['version']}" if there and there["version"] in blocking else "")
    used = sorted({v for v in spent if v in blocking}, key=importlog.version_key)
    why += ("; " if why and used else "") + (f"used up for {env['alias']}: {', '.join(used)}" if used else "")
    if not cards.confirm(
            f"CONFIRM FIRST (a new version of {name} in {own['alias']}, always on a card): show a tenant-step card with the "
              f"environment {own['name']} (role {own['role']}), the solution {name} {mine} -> {new} ({why}), set with pac solution "
              f"online-version: only the version number changes, nothing is imported; then ppp export --solution {name} takes "
              f"it into the project, and the move into {env['alias']} follows on its own card; and the answers \"Raise\" and "
              "\"Not now\". After \"Raise\": the same command with --confirmed.", confirmed):
        return 1
    tenant.set_online_version(own["url"], online["name"], new)
    after = tenant.solutions(own["url"]).get(name.lower())
    if not after or after["version"] != new:
        raise ToolError(f"pac solution online-version ended, but {own['alias']} shows {name} "
                        f"{after['version'] if after else 'no longer'}: the version is not {new}. This step goes to the user on a card "
                        f"(Solutions › {name} › settings of the solution, version {new}).")
    # the one change of the tenant that is no import: in imports.jsonl all the same (review 14.11.), status raised
    importlog.record(root, {"solution": name, "version": new, "environment": own["alias"], "status": "raised", "kind": "version",
                             "from": mine, "target": env["alias"]})
    print(f"RAISED: {name} {mine} -> {new} in {own['alias']}; nothing was imported.")
    print(f"Next: ppp export --solution {name} (it takes {new} into the project), then ppp import --environment {env['alias']}.")
    return 0


def move(root: Path, alias: str, confirmed: bool, accept_drift: bool, with_apps: bool, wait: float) -> int:
    """ppp import --environment <target> [--with-apps] [--accept-drift] [--confirmed] [--wait <s>] (ERWEITERUNGEN C.1,
    C.2, C.4, C.5): the move into the environment of environments/<alias>.json after the checks of C.2 in their order,
    always after a card (CONFIRM FIRST). The backup and the settings file lie in connected.backup_folder(root, env, name),
    the drift check is diffs.drift(..., skip=...), the entry in imports.jsonl has "kind": "move" and "source".
    A variable without a value in environments/<target>.json has no entry in the settings file. When the export carries
    its value file (environmentvariabledefinitions/<schema>/environmentvariablevalues.json: the value the project's
    environment has), that value travels with the package and, on an update, replaces the target's earlier one; this
    is known from the platform, proven at the tenant only by U6 (C.6). The card and the lines after IMPORTED name it,
    the entry holds it in values_from_source; without a value file it is in values_missing (the default applies, or
    the value the target has already). The settings file is checked (tenant.check_settings) before anything is
    recorded; whatever fails after the entry started and before pac took the package ends it as not_started
    (connected.hand_over)."""
    called = datetime.now().isoformat(timespec="seconds")
    env, own = _target(root, alias)                                                   # 1
    name = _main(root)
    folder = connected.backup_folder(root, env, name)
    last = next((e for e in reversed(importlog.entries(root)) if e.get("kind") == "move" and importlog.of(e, name, env["alias"])), None)
    if last and last["status"] == "started":     # a move under way is waited for, never started twice, no new export
        source = folder / last["zip"]
        parts = connected.package_parts(source) if source.is_file() else {"flows": {}, "refs": [], "apps": []}
        return connected.follow_import(root, env, last, parts, wait, resumed=True)
    work, mine, online = _source(root, own, name, f"ppp import --environment {env['alias']}")       # 2 to 4
    version = mine
    source = folder / f"source_{version}.zip"                                          # 5
    folder.mkdir(parents=True, exist_ok=True)
    importlog.timed_export(root, own, ["solution", "export", "--name", online["name"], "--path", str(source), "--overwrite", "--async"], 540)
    prefix = gitutil.rel(root, work) + "/"
    blobs = gitutil.read_blobs(root, "HEAD", [prefix + f for f in gitutil.tracked_files(root, "HEAD", work)])
    different = diffs.difference(diffs.unpacked(source, name), {k[len(prefix):]: v for k, v in blobs.items()})
    if different:
        raise ToolError(f"{own['alias']} differs from the project ({len(different)} files: " + ", ".join(different[:10])
                        + (" …" if len(different) > 10 else "") + f"): ppp export --solution {name} first; a move carries only a "
                        "committed state.")
    info, digest, parts = solution.zip_manifest(source), solution.sha256(source), connected.package_parts(source)
    if info["uniqueName"].lower() != name.lower() or info["managed"] or info["version"] != version:
        raise ToolError(f"The export {source.name} is not the unmanaged {name} {version}: nothing was imported.")
    if parts["apps"] and not with_apps:                                                # 6
        raise ToolError("The export contains apps: " + ", ".join(parts["apps"]) + "; a move with apps needs --with-apps.")
    there = tenant.solutions(env["url"]).get(name.lower())                             # 7
    if there and there["managed"]:
        raise ToolError(f"{name} is managed in {env['alias']}; an unmanaged package does not go on top of it.")
    if there and importlog.version_key(version) <= importlog.version_key(there["version"]):
        raise ToolError(f"Version {version} is not higher than in {env['alias']} ({there['version']}): "
                        + connected.new_version_step(root, name, own["alias"], version, there["version"], target=env["alias"]) + ".")
    running = tenant.running_imports(env["url"], name)
    if running:
        raise TenantError("BUSY", f"an import of {name} is running in {env['alias']} (progress {running[0]} %). Wait for it; "
                                  f"ppp tenant --environment {env['alias']} shows where it stands.")
    spent = next((e for e in importlog.entries(root) if e.get("kind") == "move" and e.get("status") == "failed"   # 8
                  and e.get("version") == version and importlog.of(e, name, env["alias"])), None)
    if spent:
        raise ToolError(f"Version {version} of {name} failed on a move into {env['alias']} and is used up for {env['alias']}: "
                        + connected.new_version_step(root, name, own["alias"], version, *([there["version"]] if there else []),
                                                     target=env["alias"]) + ".")
    settings = folder / f"settings_{version}.json"
    skeleton = _settings_skeleton(source, settings)
    bindings, values = _section(env, "connectionReferences"), _section(env, "environmentVariables")
    every = tenant.connections(env["url"]) if skeleton["ConnectionReferences"] else {}
    shown_refs = []
    for entry in skeleton["ConnectionReferences"]:                                     # 9
        ref, connector = entry["LogicalName"], str(entry.get("ConnectorId") or "").rstrip("/").rsplit("/", 1)[-1]
        bound = bindings.get(ref)
        if not (isinstance(bound, str) and bound.strip()):
            raise ToolError(f"{ref} ({connector}) has no binding in {_file(env)} › connectionReferences: ppp tenant --environment "
                            f"{env['alias']} --connections lists the connections there.")
        found = every.get(bound)
        why = (f"missing in {env['alias']}" if found is None else
               found["status"] or "without a status" if found["status"] != "Connected" else
               f"of the connector {found['connector']}" if found["connector"].lower() != connector.lower() else None)
        if why:
            raise ToolError(f"The connection of {ref} in {_file(env)} is {why}.")
        entry["ConnectionId"] = bound
        shown_refs.append(f"{ref}: {connector}, connection {_short(bound)} Connected")
    known = {e["SchemaName"] for e in skeleton["EnvironmentVariables"]}               # 10
    for schema, value in values.items():
        if schema not in known:
            raise ToolError(f"{_file(env)} › environmentVariables names {schema}, which {name} does not have.")
        if value is not None and not isinstance(value, str):
            raise ToolError(f"{_file(env)} › environmentVariables › {schema} must be a text, or null for the default.")
    # without a value in the target file: the settings file leaves the variable out. Its value file in the export (the
    # value the project's environment has) then travels with the package (from_source), else the default applies or the
    # value the target has already (missing)
    travels = _values_in(source)
    unset = sorted(s for s in known if values.get(s) is None)
    from_source, missing = [s for s in unset if s in travels], [s for s in unset if s not in travels]
    kept = []
    for entry in skeleton["EnvironmentVariables"]:
        if values.get(entry["SchemaName"]) is not None:
            kept.append({"SchemaName": entry["SchemaName"], "Value": values[entry["SchemaName"]]})
    publisher_line = _publisher(root, env, own, source)                                # 11
    drift, details = [], []                                                            # 12
    if there:      # the backup before the move is the export of the drift check (VB-12), in the target's own folder
        backup = folder / f"before_{version}.zip"
        importlog.timed_export(root, env, ["solution", "export", "--name", there["name"], "--path", str(backup), "--overwrite", "--async"], 540)
        drift, details = diffs.drift(root, work, backup, there["version"], skip=(VALUES,))
    if drift and not accept_drift:
        print(f"DRIFT: {env['alias']} differs from the version it got ({len(drift)}): " + ", ".join(drift[:30])
              + (f" … {len(drift) - 30} more" if len(drift) > 30 else ""))
        for line in details:
            print(line)
        print(f"Nothing was imported. Ask on a card: overwrite these changes in {env['alias']} (--accept-drift), or stop and build "
              f"the change in {own['alias']}.")
        return 1
    data = {"EnvironmentVariables": kept,
            "ConnectionReferences": [{"LogicalName": e["LogicalName"], "ConnectionId": e["ConnectionId"],
                                      "ConnectorId": str(e.get("ConnectorId") or "")} for e in skeleton["ConnectionReferences"]]}
    settings.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    settings_sha = solution.sha256(settings)
    # the checks of start_import, here before anything is recorded: a refused file leaves no entry started behind
    tenant.check_settings(source, settings, settings_sha)
    if confirmed is not True:
        variables = ([f"{s}: value from {_file(env)}" for s in sorted(known - set(unset))]
                     + [f"{s}: no value in {_file(env)}: the value of {own['alias']} travels with the export" if s in travels else
                        f"{s}: no value in {_file(env)}: the default applies, or the value {env['alias']} has already" for s in unset])
        # the run with --confirmed exports anew: its SHA-256 stands in the entry, the card names the content as committed
        card = (f"CONFIRM FIRST (a move into {env['alias']}, always on a card): show a tenant-step card with the source {own['alias']} "
              f"({name} {version}, its export as committed), the target {env['name']} (role test, type "
              f"{env['data'].get('type') or 'unknown: ppp connect --target reads it'} in pac env list; online there: "
              f"{there['version'] if there else 'nothing yet'}), {len(parts['flows'])} flows, apps: {', '.join(parts['apps']) or 'none'}, "
              f"the connection references ({'; '.join(shown_refs) or 'none'}), the environment variables "
              f"({'; '.join(variables) or 'none'}; values only on the user's request), {publisher_line}, without publishing "
              "(sharing and publishing the app stay by hand)"
              + (f", the drift it overwrites: {', '.join(drift[:30])}" if drift else "")
              + " and the answers \"Move\" and \"Not now\". After \"Move\": the same command with --confirmed.")
        # bound to the settings file (bindings and values) and the lines of the drift (cards)
        if not cards.confirm(card, confirmed, [settings_sha, *details]):
            return 1
    entry = importlog.record(root, {"solution": name, "version": version, "zip": source.name, "sha": digest,
                                     "environment": env["alias"], "status": "started", "kind": "move", "source": own["alias"],
                                     "settings": settings.name, "settings_sha": settings_sha, "values_missing": missing,
                                     "values_from_source": from_source,
                                     "called": called, "online_before": there["version"] if there else None,
                                     "flows_before": tenant.flows(env["url"], list(parts["flows"])) if there else {},
                                     "jobs_before": tenant.import_jobs(env["url"], name)})
    result = connected.hand_over(root, env, entry, source, wait, settings=settings, settings_sha=settings_sha)
    if result["state"] in ("failed", "skipped"):
        return connected.report_failed(root, env, entry, f"{result.get('kind', 'SKIPPED')}: {result['message']}", result=result)
    return connected.follow_import(root, env, entry, parts, max(wait - result["seconds"], 0), resumed=False)


def _publisher(root: Path, env: dict, own: dict, source: Path) -> str:
    """C.2 point 11: the publisher of the export (its solution.xml, with its four values) in the target; what goes in is
    the export, so its publisher is the one the server finds or creates, whatever the settings say. Refused: missing in
    the default environment (its creation goes on a card there, ERWEITERUNGEN A.2); there with other values; its prefix
    another publisher's there: ppp never changes a publisher. Missing elsewhere: the import creates it with the values of
    the export (N8, unproven for a move, C.6). Returns the part of the card on it, with a half-sentence when the export's
    publisher differs from the one of the settings."""
    from . import publisher
    with zipfile.ZipFile(source) as z:
        xml = next((z.read(n) for n in z.namelist() if n.lower() == "solution.xml"), b"")
    wanted = solution.publisher_of(xml)
    if not wanted or wanted["optionValuePrefix"] is None or not wanted["prefix"]:
        raise ToolError(f"The export {source.name} names no publisher with its four values in solution.xml: nothing was imported.")
    name, alias = wanted["uniqueName"], env["alias"]
    read = tenant.publisher(env["url"], name, wanted["prefix"], wanted["optionValuePrefix"])
    found = read["found"]
    if found is None and publisher._default(env):
        raise ToolError(f"The publisher {name} is missing in {alias}, the default environment: a card creates it "
                        f"in the portal ({PORTAL}).")
    if found is not None:
        different = publisher._differences(found, wanted)
        if different:
            raise ToolError(f"The publisher {name} in {alias} differs from the one of the export from {own['alias']}: "
                            + "; ".join(different).replace(" vs ", " there, the export ") + ". ppp never changes a publisher: "
                            "this move goes on a card.")
    if read["prefix_others"]:
        raise ToolError(f"The prefix {wanted['prefix'].lower()} of the publisher {name} belongs to the publisher "
                        f"{', '.join(read['prefix_others'])} in {alias}: ppp never changes a publisher; this move goes on a card.")
    settings = agent.publisher_of(agent.read_settings())
    different = publisher._differences(wanted, settings) if settings else []
    aside = ("; the export's publisher differs from the settings: "
             + ", ".join(d.replace(" vs ", " in the export, the settings ") for d in different)) if different else ""
    if found is not None:
        return f"the publisher {name} (there already{aside})"
    return f"the publisher {name} (missing there: the import creates it with the values of the export{aside})"


# ------------------------------------------------------------------ after IMPORTED
def after_import(root: Path, env: dict, entry: dict, parts: dict) -> list[str]:
    """The hook of connected.report_imported for an entry of kind move, after the lines of the record and the flows
    (ERWEITERUNGEN C.1): the switches against flowSwitches of environments/<target>.json, the line Values with a line per
    variable without a value (entry["values_missing"]: the default or the target's value applies) and a WARNING line per
    variable whose value came with the export (entry["values_from_source"]: the value of the project's environment;
    that the server takes it so is platform knowledge, proven at the tenant only by U6), the line Bindings, each
    deviation as a WARNING line. env is the
    target (tenant.environment(root, alias)), parts the parts of the package (connected.package_parts). Each line that starts
    with WARNING counts among ppp's warnings of the import; BY_HAND, the line on apps and Next print connected.report_imported.
    What is checked is the settings file that went in (entry["settings"]); without it environments/<target>.json."""
    lines = []
    switches = _section(env, "flowSwitches")
    meant = {state: set(switches.get(state) or []) if isinstance(switches.get(state), list) else set() for state in ("on", "off")}
    if meant["on"] or meant["off"]:
        states = tenant.flows(env["url"], list(parts["flows"]))
        unexpected = sorted(parts["flows"][i] for i, s in states.items()
                            if (s == "on" and parts["flows"][i] in meant["off"]) or (s == "off" and parts["flows"][i] in meant["on"]))
        if unexpected:
            lines.append(f"WARNING switches differ from flowSwitches in {_file(env)}: " + ", ".join(unexpected))
    path = connected.backup_folder(root, env, entry["solution"]) / str(entry.get("settings") or "")
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if entry.get("settings") and path.is_file() else None
    except ValueError:
        data = None
    if isinstance(data, dict):
        wanted_values = {e["SchemaName"]: e["Value"] for e in data.get("EnvironmentVariables") or []}
        wanted_refs = {e["LogicalName"]: e["ConnectionId"] for e in data.get("ConnectionReferences") or []}
    else:
        lines.append(f"WARNING the settings file {entry.get('settings') or '?'} is not in {gitutil.rel(root, path.parent)}: "
                     f"checked against {_file(env)}")
        wanted_values = {k: v for k, v in _section(env, "environmentVariables").items() if isinstance(v, str)}
        wanted_refs = {k: v for k, v in _section(env, "connectionReferences").items() if k in parts["refs"]}
    missing = [s for s in entry.get("values_missing") or [] if s not in wanted_values]
    from_source = [s for s in entry.get("values_from_source") or [] if s not in wanted_values and s not in missing]
    read = tenant.variables(env["url"], sorted(wanted_values) + missing + from_source)
    flat = lambda text: " ".join(str(text).split())
    wrong = []
    for schema, value in sorted(wanted_values.items()):
        got = read.get(schema) or {}
        if not got.get("exists"):
            wrong.append(f"WARNING {schema} is not in {env['alias']} after the move")
        elif got.get("value") is None or flat(got["value"]) != flat(value):
            wrong.append(f"WARNING {schema}: the value in {env['alias']} differs from {_file(env)}")
    lines += wrong or [f"Values: {len(wanted_values)} as in {_file(env)}"]
    for schema in missing:      # unproven (C.6, U6): whether the default applies, or an earlier value stays
        got = read.get(schema) or {}
        lines.append(f"WARNING {schema} is not in {env['alias']} after the move" if not got.get("exists") else
                     f"{schema}: no value in {_file(env)}; in {env['alias']} now: "
                     + ("no current value, the default applies" if got.get("value") is None else
                        f"a current value (ppp tenant --environment {env['alias']} --values shows it)"))  # values on request only
    # the export carried the value of the project's environment (its value file): the server takes it as the current value,
    # on an update over the target's earlier one; known from the platform, at the tenant proven only by U6 (C.6). The
    # value itself is not printed: ppp tenant --environment <target> --values shows it on the user's request
    source = entry.get("source", "?")
    for schema in from_source:
        got = read.get(schema) or {}
        lines.append(f"WARNING {schema} is not in {env['alias']} after the move" if not got.get("exists") else
                     f"WARNING {schema}: the value of {source} came with the export; in {env['alias']} now: "
                     + ("no current value, the default applies" if got.get("value") is None else
                        f"a current value (ppp tenant --environment {env['alias']} --values shows it)"))
    bound =tenant.connection_references(env["url"], sorted(wanted_refs))
    other = [f"WARNING {ref} is bound to another connection in {env['alias']}" for ref, connection in sorted(wanted_refs.items())
             if (bound.get(ref) or {}).get("connection") not in (None, connection)]
    lines += other or [f"Bindings: {len(wanted_refs)} as in {_file(env)}"]
    return lines


# ------------------------------------------------------------------ ppp tenant --environment, ppp export --compare --environment
def status(root: Path, alias: str | None, connections: bool, log: bool, values: bool, write: bool) -> int:
    """ppp tenant --environment <target> [--connections] [--values] [--write] [--log] (ERWEITERUNGEN C.1): what
    connected.status shows, against the environment of environments/<alias>.json (None or the project's alias: the
    project's environment). connections: only the line CONNECTIONS with the connections per connector of the main
    solution, read only. Returns the exit code as connected.status."""
    if not connections:
        return connected.status(root, log, values, write, environment=alias)
    env = tenant.environment(root, alias)
    wanted = _committed_connectors(root, _main(root))
    print(f"CONNECTIONS: {env['alias']}")
    if not wanted:
        print(f"  none: solution/{_main(root)}/ names no connection reference")
        return 0
    every = tenant.connections(env["url"])
    lacking = 0
    for connector in sorted({c for c in wanted.values()}):
        if not connector:
            print("  (no connector named): " + ", ".join(sorted(r for r, c in wanted.items() if not c)))
            continue
        mine = sorted((i, c["status"]) for i, c in every.items() if c["connector"].lower() == connector.lower())
        live = [i for i, s in mine if s == "Connected"]
        if not live:
            lacking += 1
        if not mine:
            print(f"  {connector}: none: the user creates one in {env['name']} first")
        for i, state in mine:
            print(f"  {connector}: {i} {state or 'without a status'}" + (" (the only one)" if live == [i] else ""))
    return 1 if lacking else 0


def compare(root: Path, alias: str, name: str | None, wait: float) -> int:
    """ppp export --compare --environment <target> [--solution <name>] (ERWEITERUNGEN C.1): the export of the solution
    (None: the main solution, the one a move brings there; the package solution in the project's environment) from the
    environment of environments/<alias>.json compared with the project, as ppp export --compare; changes nothing.
    Returns the exit code."""
    if name is None and not tenant.environment(root, alias)["own"]:
        name = _main(root)
    return connected.export(root, None, name, compare=True, wait=wait, environment=alias)
